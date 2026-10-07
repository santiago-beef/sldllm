#!/usr/bin/env python3
"""synth.py - synthetic PSC streams for the decoder tests (Stage 3 'Decoder').

Built from the record format (psc_format.py, the mirror of psc_format.h) and an
independent model of the joypad thread (joypad_psp.c:453-659), the watchdog
(psp.c:372-392), the collector's files and flushes (DESIGN 4.3, 4.4, 10.2) and
the operator script (RUNBOOK B4-B6, C0, C1, D0-D8).  It does not import the
decoder.

Shapes: healthy, H1, H2, H3, H4, H5, H6, H7, H8, H9, H10, none.

  python3 synth.py SHAPE OUTDIR [--seed N] [--run N] [--nonce HEX] [--rx2alt]
                   [--flush-fail] [--image] [--prior-run DIR] [--te7 DIR]

OUTDIR receives PSCLOG/T<rrr><nnn>.BIN, build/{System.map,epcmap.txt,regmap.txt,
build_id.txt}, times.txt (operator stopwatch times), truth.json (shape, onset,
chunk ledger for the truncation test) and, with --image, stick.img.
"""

import argparse
import json
import hashlib
import os
import random
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import psc_format as F   # noqa: E402

CPT = F.CPT
TPS = 250
SEG = F.SEG_SIZE

# ----------------------------------------------------------------- build artefacts
SYS_BASE = 0x80108000
STEP_LABELS = ["S%d" % i for i in range(1, 24)]
EPC = {"ENTRY": (SYS_BASE, SYS_BASE + 0x40)}
for _i, _l in enumerate(STEP_LABELS):
    EPC[_l] = (SYS_BASE + 0x40 + 0x40 * _i, SYS_BASE + 0x80 + 0x40 * _i)
EPC["REC"] = (SYS_BASE + 0x640, SYS_BASE + 0x680)
EPC["EXIT"] = (SYS_BASE + 0x680, SYS_BASE + 0x6a0)
FUNCS = {"_pspSysconGetCtrl2": (0x80108800, 0x80108880), "psp_led_ctrl": (0x80109000, 0x80109040),
         "LEDRMW": (0x80109040, 0x80109050), "psp_led_ctrl_end": (0x80109050, 0x80109100),
         "cpu_idle": (0x80020000, 0x80020100), "mousedev_read": (0x80150000, 0x80150400),
         "ms_wait_ready": (0x80160000, 0x80160100), "psc_sc_exit": (0x8010a000, 0x8010a400)}
ADDR_SYSCON, ADDR_EXIT, ADDR_GETC2 = SYS_BASE, 0x8010a000, 0x80108800
SYNTH_BANNER = b"Linux version 2.6.22 (psc synth)\n"
BUILD_ID = zlib.crc32(SYNTH_BANNER) & 0xFFFFFFFF   # R-4: CRC-32 of /proc/version (= linux_banner)
WRK_PID, SUP_PID, JP_PID, OSK_PID, MD_PID, PDF_PID = 77, 76, 25, 30, 31, 9


def epc_of(label, off=8):
    a = EPC.get(label) or FUNCS.get(label)
    return a[0] + off


def write_build(d):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "System.map"), "w") as f:
        f.write("%08x T Syscon_cmd\n%08x T psc_sc_exit\n%08x T _pspSysconGetCtrl2\n%08x T cpu_idle\n"
                % (ADDR_SYSCON, ADDR_EXIT, ADDR_GETC2, 0x80020000))
    # the grammar of psc_maps.py (the one mkmaps.py writes, G2 attempt 1 F3)
    with open(os.path.join(d, "epcmap.txt"), "w") as f:
        f.write("# PSC-EPCMAP 2\n")
        for lab, (a, b) in sorted(list(EPC.items()) + list(FUNCS.items()), key=lambda x: x[1]):
            f.write("%08x %08x %s\n" % (a, b, lab))
    with open(os.path.join(d, "regmap.txt"), "w") as f:
        f.write("# PSC-REGMAP 2\n"
                "all      rx_buf     r[15]       2 -\n"
                "S11      i          r[6]        0 -\n"
                "S16-S18  i          r[6]        2 -\n"
                "S16-S18  ptr        r[5]        2 -\n"
                "S16-S18  pending    zero        0 -\n"
                "LEDRMW   loaded     r[0]        0 -\n")
    with open(os.path.join(d, "build_id.txt"), "w") as f:
        f.write("0x%08x\n" % BUILD_ID)
    write_sums(d)


# the synthetic image's sha256 (10.1, K3): the tests decode with --expect-image SYNTH_IMAGE_SHA256
SYNTH_IMAGE_SHA256 = hashlib.sha256(b"psc synth image").hexdigest()


def write_sums(d, image_sha=None):
    """IMAGE.sha256 and SHA256SUMS of a BUILD directory, as mkmaps.py writes them."""
    with open(os.path.join(d, "IMAGE.sha256"), "w") as f:
        f.write("%s  vmlinux-0.22.bin\n" % (image_sha or SYNTH_IMAGE_SHA256))
    lines = []
    for name in sorted(os.listdir(d)):
        if name == "SHA256SUMS" or not os.path.isfile(os.path.join(d, name)):
            continue
        with open(os.path.join(d, name), "rb") as f:
            lines.append("%s  %s\n" % (hashlib.sha256(f.read()).hexdigest(), name))
    with open(os.path.join(d, "SHA256SUMS"), "w") as f:
        f.writelines(lines)


# ----------------------------------------------------------------- packing
def pack(fields, d):
    vals = []
    for (n, c, k) in fields:
        v = d.get(n, b"" if c == "s" else (0 if k == 1 else [0] * k))
        if c == "s":
            vals.append(bytes(v).ljust(k, b"\0")[:k])
        elif k == 1:
            vals.append(v)
        else:
            v = list(v) + [0] * (k - len(v))
            vals.extend(v[:k])
    return struct.pack(F.fields_fmt(fields), *vals)


def pack_w(sc, ext):
    d = {"sc." + k: v for k, v in sc.items()}
    d.update({"ext." + k: v for k, v in ext.items()})
    return pack(F.W_FIELDS, d)


def chunk(ctype, payload, fseq, nonce):
    crc = F.chunk_crc(ctype, payload, nonce)
    return struct.pack(F.CHUNK_HDR_FMT, F.CHUNK_MAGIC, ctype, F.FORMAT_VERSION, len(payload), fseq, crc) + \
        payload + b"\0" * (F.pad4(len(payload)) - len(payload))


# ----------------------------------------------------------------- replies
def reply(cmd, codes, payload=b"", status=0x24):
    body = bytes([status, 3 + len(payload), codes[cmd]]) + payload
    cks = (~sum(body)) & 0xFF
    rx = body + bytes([cks])
    nw = (len(rx) + 1) // 2
    return rx.ljust(16, b"\xff"), nw


def tadd(tick, c, dc):
    c += dc
    return tick + c // CPT, c % CPT


# ----------------------------------------------------------------- operator
class Operator(object):
    """Button and stick state per tick (RUNBOOK B4, B6, C0, C1, D0-D8)."""

    def __init__(self, onset_s, healthy=False):
        self.ev = []        # (t0_s, t1_s, what)
        self.ev.append((36.0, 38.0, "TRI"))                  # B4
        self.ev.append((45.0, 45.15, "SELECT"))              # B6
        self.c0 = 50.0
        t = self._script(self.c0, with_d7a=False)           # C0 = D1..D7
        self.c0_end = t
        # C1 normal use: L clicks 4/s, stick right 0.5 s every 7 s
        x = t + 1.0
        while x < onset_s - 0.3:
            self.ev.append((x, x + 0.1, "L"))
            if int(x * 4) % 28 == 0:
                self.ev.append((x, x + 0.5, "STICK_R"))
            x += 0.25
        self.d0 = onset_s + 3.0
        self.d_end = self._script(self.d0 + 2.0, with_d7a=True)
        self.pull = self.d_end + 30.0 + 6.0                  # D8 30 s hands-off, check, D9

    def _script(self, t, with_d7a):
        x = t
        while x < t + 10.0:                                  # D1 L clicks 4/s 10 s
            self.ev.append((x, x + 0.1, "L"))
            x += 0.25
        t += 10.0 + 5.0                                      # D2 release 5 s
        for _ in range(2):                                   # D3 TRIANGLE 3 s / 3 s twice
            self.ev.append((t, t + 3.0, "TRI"))
            t += 6.0
        self.ev.append((t, t + 3.0, "RIGHT")); t += 6.0      # D4
        self.ev.append((t, t + 3.0, "VOLUP")); t += 6.0      # D5
        self.ev.append((t, t + 3.0, "STICK_R")); t += 6.0    # D6
        self.ev.append((t, t + 3.0, "STICK_U")); t += 6.0
        self.ev.append((t, t + 5.0, "HOLD")); t += 10.0      # D7
        if with_d7a:                                         # D7a
            self.ev.append((t, t + 0.15, "SELECT"))
            x = t + 0.5
            for _ in range(5):
                self.ev.append((x, x + 0.1, "L"))
                x += 1.0
            t += 6.0
        return t

    def at(self, s):
        on = set(w for (a, b, w) in self.ev if a <= s < b)
        b3, b4, b5, b6 = 0xFF, 0xFF, 0xFF, 0xFF
        if "TRI" in on: b3 &= ~0x10
        if "RIGHT" in on: b3 &= ~0x02
        if "SELECT" in on: b4 &= ~0x01           # 0x100 = rx[4] b0
        if "L" in on: b4 &= ~0x02                # LTRG rx[4] b1
        if "HOLD" in on: b4 &= ~0x20             # HOLD rx[4] b5
        if "VOLUP" in on: b5 &= ~0x01            # VOL_UP rx[5] b0
        x = 0xF8 if "STICK_R" in on else 0x80
        y = 0x05 if "STICK_U" in on else 0x80
        return bytes([b3 & 0xFF, b4 & 0xFF, b5 & 0xFF, b6]), x, y


def conv(v):
    n = (v >> 4) & 0xF
    return {0: -16, 1: -4, 2: -2, 3: -2, 4: -1, 5: -1, 0xA: 1, 0xB: 1, 0xC: 2, 0xD: 2, 0xE: 4, 0xF: 16}.get(n, 0)


# ----------------------------------------------------------------- the run
class Synth(object):
    def __init__(self, shape, seed=1, run_no=1, nonce=0x1234ABCD, rx2alt=False, duration_cap=None,
                 flush_fail=False, nop7=False):
        self.shape = shape
        self.nop7 = nop7        # Stage 3 (N3, A-5): a straddling Nop's own reply is 7 words, flagged nw7or8
        self.rng = random.Random(seed)
        self.run_no, self.nonce = run_no, nonce
        self.codes = ({0x08: 0x28, 0x33: 0x53, 0x00: 0x20, 0x34: 0x54} if rx2alt else
                      {0x08: 0x08, 0x33: 0x33, 0x00: 0x00, 0x34: 0x34})
        self.flush_fail = flush_fail
        self.onset_s = 130.0 if shape == "H4" else 131.3
        self.onset = int(self.onset_s * TPS)
        self.healthy = shape == "healthy"
        self.op = Operator(self.onset_s, self.healthy)
        self.end_tick = int(self.op.pull * TPS) if duration_cap is None else int(duration_cap * TPS)
        self.P, self.POLL, self.W, self.M, self.S = [], [], [], [], []
        self.snap = []          # (avail_t, counters) after each poll
        self.cnt = dict(jp_loop=0, jp_r3=0, jp_r4=0, jp_r5=0, jp_proc_calls=0, jp_dedupe=0, jp_changed=0,
                        jp_lcd_unblank=0, jp_mode_toggles=0, jp_listsem_fail=0, jp_push_ok=0, jp_push_full=0,
                        jp_push_eintr=0, jp_wake=0, jp_mouse_calls=0, jp_mouse_noop=0, jp_mouse_reports=0,
                        fop_read_enter=0, fop_read_ret=0, vcs_putchar=0, vcs_updscr=0, md_event_syn=0,
                        md_notify_calls=0, md_read_ret=0, mouse_pkts=0, mouse_press=0, jp_keys=0,
                        oc08=[0] * 7, oc33=[0] * 7, ocw=[0] * 7, p_nested=0, p_ticked=0, pre_count=0,
                        jp_stage=17, t_busy=0, wk_count=0)
        self.stopped_at = None

    # ---------------------------------------------------------- SC records
    def sc(self, seq, cmd, t_in, dur, ret, nwords, rx, origin, **kw):
        tick_out, c_out = tadd(t_in[0], t_in[1], dur)
        d = dict(seq=seq, tick_in=t_in[0], c_in=t_in[1], c_out=c_out, dtick=min(0xFFFF, tick_out - t_in[0]),
                 cmd=cmd, txlen=3 if cmd in (0x33, 0x34) else 2, ret=ret, nwords=nwords, retries=0,
                 ack_polls=self.rng.randint(120, 260), drain=0, drain_last=0, gpio_in=0x0012, spi_st9=0x0005,
                 spi_sttx=0x0002, ctx={0: 0x14, 1: 0x05, 2: 0x02, 3: 0x03}[origin], wn=0, w_head_lo=0,
                 pre_wrk=0, pre_cls=0, ms_delta=0, pre_flags=0, preempt_delta=0, rx=rx, lc_epc=0,
                 lc_dtick=0xFFFF, lc_n=0, lc_flags=0, led_or=0, led_pid=0, pre_tot=0)
        d.update(kw)
        d["_t1"] = (tick_out, c_out)
        return d

    def oc(self, arr, ret, nwords):
        i = (0 if ret > 0 else 1 if (ret == 0 and nwords > 0) else 2 if ret == 0 else
             {-2: 3, -3: 4, -4: 5, -5: 6}[ret])
        arr[i] += 1

    def failed33(self, rx_t, t_in):
        return None

    # ---------------------------------------------------------- thread
    def run_thread(self):
        sh = self.shape
        L = 747                                  # thread start; puts a poll at tick 32499 (H4)
        last_keys, mouse_mode, s_keys = 0, False, 0
        btn = (False, False, False)
        prev_L = None
        frozen = None
        oc = self.cnt
        while L < self.end_tick:
            if sh == "H9" and L >= self.onset:
                self.stopped_at = L
                oc["jp_stage"] = 11
                break
            post = (not self.healthy) and (L >= self.onset or (sh == "H4" and L == 32499))
            s = L / float(TPS)
            raw, x, y = self.op.at(s)
            c0 = 3000 + self.rng.randint(0, 4000)
            wk = dict(wk_delay=c0 >> 8, wk_wrk=0, wk_cls0=6, wk_cls1=6, wk_nsw=1)
            if sh == "H4" and L == 32499:
                c0 = CPT - 29000
                wk = dict(wk_delay=min(0xFFFF, c0 >> 8), wk_wrk=min(0xFFFF, (c0 - 4000) >> 8), wk_cls0=6,
                          wk_cls1=1, wk_nsw=2)
            t = (L, c0)
            # ---- 0x33
            pseq = len(self.P)
            t33 = tadd(t[0], t[1], 500)
            rx33, nw33 = reply(0x33, self.codes)
            r33 = self.sc(pseq, 0x33, t33, 8800 + self.rng.randint(-300, 300), rx33[0], nw33, rx33, 0)
            if post and sh == "H1":
                r33.update(self.fail4(t33))
            if post and sh == "H8":
                r33.update(gpio_in=0x0002, ack_polls=0)
            self.P.append(r33)
            self.oc(oc["oc33"], r33["ret"], r33["nwords"])
            # ---- 0x08
            t08 = tadd(r33["_t1"][0], r33["_t1"][1], 400)
            payload = raw + bytes([x, y])
            rx08, nw08 = reply(0x08, self.codes, payload)
            r08 = self.sc(pseq + 1, 0x08, t08, 15500 + self.rng.randint(-400, 400), rx08[0], nw08, rx08, 0)
            if post:
                self.post08(r08, t08, frozen)
                if frozen is None and sh in ("H6", "none"):
                    frozen = r08["rx"]
            elif sh in ("H6", "none"):
                pass
            self.P.append(r08)
            self.oc(oc["oc08"], r08["ret"], r08["nwords"])
            # ---- read_input (joypad_psp.c:474-496)
            stage_max = 4
            pi = 0
            nq = push_ok = push_fail = 0
            mf = 0
            dx = dy = 0
            ret = r08["ret"]
            rxx = r08["rx"]
            key = rxx[3] | rxx[4] << 8 | rxx[5] << 16 | rxx[6] << 24
            keys = (~key) & 0xFFFFFFFF
            if ret < 0:
                br = 3
                oc["jp_r3"] += 1
            elif keys & 0x2000:
                br = 4
                oc["jp_r4"] += 1
            else:
                br = 5
                oc["jp_r5"] += 1
            if br == 5:
                xx, yy = rxx[7], rxx[8]
                kk = keys | ((xx & 0xF0) << 20) | ((yy & 0xF0) << 24)
                pi |= F.PI_F_CALLED
                oc["jp_proc_calls"] += 1
                stage_max = 6
                if kk == last_keys:
                    pi |= F.PI_F_DEDUPE
                    oc["jp_dedupe"] += 1
                else:
                    last_keys = kk
                    oc["jp_changed"] += 1
                    oc["jp_lcd_unblank"] += 1
                    if kk & 0x100:
                        mouse_mode = not mouse_mode
                        pi |= F.PI_F_SELECT_TOGGLE
                        oc["jp_mode_toggles"] += 1
                    if mouse_mode:
                        pi |= F.PI_F_MOUSEMODE
                    s_keys = kk | (0x00800000 if mouse_mode else 0)
                    oc["jp_keys"] = s_keys
                    pi |= F.PI_F_LISTSEM | F.PI_F_WAKE
                    nq, push_ok = 1, 1
                    oc["jp_push_ok"] += 1
                    oc["jp_wake"] += 1
                    stage_max = 14
                    if not (post and sh == "H7"):
                        oc["fop_read_enter"] += 1
                        oc["fop_read_ret"] += 1
                        oc["vcs_putchar"] += 1
                if s_keys & 0x00800000:
                    mf |= F.MOUSE_F_CALLED
                    oc["jp_mouse_calls"] += 1
                    stage_max = 16
                    dx, dy = conv(xx), conv(yy)
                    left = bool(keys & 0x200) and not keys & 0x400
                    right = bool(keys & 0x400) and not keys & 0x200
                    mid = bool(keys & 0x200) and bool(keys & 0x400)
                    dx += (-2 if keys & 0x8 else 0) + (2 if keys & 0x2 else 0)
                    dy += (-2 if keys & 0x1 else 0) + (2 if keys & 0x4 else 0)
                    if dx == 0 and dy == 0 and (left, mid, right) == btn:
                        mf |= F.MOUSE_F_NOOP
                        oc["jp_mouse_noop"] += 1
                    else:
                        if (left or mid or right) and not any(btn):
                            oc["mouse_press"] += 1
                        btn = (left, mid, right)
                        mf |= F.MOUSE_F_REPORTED | (0x10 if left else 0) | (0x20 if mid else 0) | (0x40 if right else 0)
                        oc["jp_mouse_reports"] += 1
                        oc["md_event_syn"] += 1
                        oc["md_notify_calls"] += 1
                        oc["md_read_ret"] += 2          # pspmd + the collector's client
                        oc["mouse_pkts"] += 1
                else:
                    dx = dy = 0
            oc["jp_loop"] += 1
            end08 = r08["_t1"]
            c_end = end08[1] + 3000
            body = end08[0] - L + (c_end // CPT)
            period = 0 if prev_L is None else min(255, L - prev_L)
            pr = dict(seq=len(self.POLL), tick_start=L, c_start=c0, c_end=c_end % CPT, sc_seq_lo=pseq & 0xFFFF,
                      body_ticks=min(255, body), ri_branch=br, pi_flags=pi, nqueues=nq, push_ok=push_ok,
                      push_fail=push_fail, mouse_flags=mf, dx=max(-128, min(127, dx)), dy=max(-128, min(127, dy)),
                      sig=0, period=period, preempt_delta=0, stage_max=stage_max, nsc=2, **wk)
            oc["wk_count"] += 1
            self.POLL.append(pr)
            self.snap.append(((end08[0], end08[1]), self.copy_cnt()))
            prev_L = L
            L = end08[0] + 14

    def copy_cnt(self):
        d = dict(self.cnt)
        for k in ("oc08", "oc33", "ocw"):
            d[k] = list(self.cnt[k])
        return d

    def fail4(self, t_in, lc_ticks=12):
        dur = 13 * CPT - 1000
        tick_out, c_out = tadd(t_in[0], t_in[1], dur)
        return dict(ret=-4, nwords=0, ack_polls=F.ACK_POLLS_TIMEOUT, rx=b"\xff" * 16, c_out=c_out,
                    dtick=tick_out - t_in[0], _t1=(tick_out, c_out), lc_epc=epc_of("S14"), lc_dtick=lc_ticks,
                    lc_n=lc_ticks, lc_flags=F.LC_F_VALID | F.LC_F_IN_SYSCON)

    def post08(self, r, t08, frozen):
        sh = self.shape
        ff = b"\xff" * 16
        if sh in ("H1", "H4"):
            r.update(self.fail4(t08))
            if sh == "H4" and t08[0] == 32499:
                r["_h4"] = True
        elif sh == "H10":
            r.update(self.fail4(t08))
            if not getattr(self, "_h10_done", False):
                self._h10_done = True
                r.update(preempt_delta=1, lc_epc=epc_of("S14"), lc_dtick=1, lc_n=2,
                         lc_flags=F.LC_F_VALID | F.LC_F_IN_SYSCON, ms_delta=4, led_or=0x48, led_pid=WRK_PID,
                         pre_cls=0x11, pre_flags=F.PRE_F_VALID, pre_tot=2600, pre_wrk=2600)
                r["_h10"] = True
        elif sh == "H2":
            r.update(ret=0, nwords=5, rx=b"\0" * 10 + b"\xff" * 6)
        elif sh in ("H3", "H8"):
            r.update(ret=0, nwords=0, rx=ff, ack_polls=140)
            if sh == "H8":
                r.update(gpio_in=0x0002, ack_polls=0)
        elif sh == "H5":
            rx = bytes([0x24, 3, 0x80]); rx = rx + bytes([(~sum(rx)) & 0xFF])
            dur = 16 * 15000
            tick_out, c_out = tadd(t08[0], t08[1], dur)
            r.update(ret=-5, retries=16, nwords=2, rx=rx.ljust(16, b"\xff"), c_out=c_out,
                     dtick=tick_out - t08[0], _t1=(tick_out, c_out))
        elif sh == "H6":
            if frozen is not None:
                r.update(rx=frozen)
        elif sh == "none":
            src = frozen if frozen is not None else r["rx"]
            body = bytes([src[0], src[1], 0x42]) + bytes(src[3:9])
            rx = body + bytes([(~sum(body)) & 0xFF])
            r.update(rx=rx.ljust(16, b"\xff"), ret=rx[0])

    # ---------------------------------------------------------- watchdog (WB, WT), M
    def run_watchdog(self):
        self._index()
        rxn, nwn = reply(0x00, self.codes)
        wb = self.sc(0, 0x00, (0, 100), 12000, rxn[0], nwn, rxn, 2)
        self.W.append((wb, {}))
        rxm, nwm = reply(0x34, self.codes)
        self.M.append(self.sc(0, 0x34, (60, 5000), 9000, rxm[0], nwm, rxm, 1))
        k = 1
        pi = 0
        while k * F.WD_CYCLE < self.end_tick:
            T = k * F.WD_CYCLE
            w = self.sc(k, 0x00, (T, 1500), 12000, rxn[0], nwn, rxn, 3)
            while pi < len(self.P) and self.P[pi]["_t1"] < (T, 0):
                pi += 1
            busy = None
            if pi < len(self.P) and (self.P[pi]["tick_in"], self.P[pi]["c_in"]) < (T, 0) <= self.P[pi]["_t1"]:
                busy = self.P[pi]
            ext = dict(epc=epc_of("cpu_idle"), cause=0, status=0x1000FF01, ra=epc_of("cpu_idle", 0x20), sp=0x81F00000,
                       r=[0] * 16, pid=0, p_head=self.p_head_at((T, 0)), jp_loop=self.loop_at((T, 0)),
                       t_entry_tick=0, t_entry_c=0, t_busy=0, jp_stage=17, ext_flags=0x05, cur_pcnt=0,
                       c_pre=CPT + self.rng.randint(0, 200), lc_tick=0, lc_c_pre=0, lc_cmd_id=0, lc_epc=0,
                       lc_cause=0, lc_ra=0, lc_sp=0, lc_r=[0] * 16, lc_n=0, rsv=0)
            if self.stopped_at is not None and T > self.stopped_at:
                ext.update(jp_stage=11, epc=epc_of("cpu_idle"))
            if busy is not None:
                ext.update(t_busy=1, p_head=busy["seq"], pid=JP_PID, epc=epc_of("S14"),
                           ext_flags=0x01 | 0x04 | 0x08 | 0x10, jp_stage=3 if busy["cmd"] == 0x08 else 2,
                           t_entry_tick=busy["tick_in"], t_entry_c=busy["c_in"])
                ext["r"][F.REGS_ORDER.index(8)] = 4
                w["ack_polls"] = 60
                if self.nop7:
                    body = bytes([0x24, 13, 0x00]) + bytes(range(1, 11))
                    rx7 = body + bytes([(~sum(body)) & 0xFF])
                    w.update(rx=rx7.ljust(16, b"\xff"), nwords=7, ret=rx7[0])
                busy["wn"] = min(255, busy["wn"] + 1)
                busy["_wseq"] = k
            self.W.append((w, ext))
            k += 1
        # w_head_lo of every SC record: W head at record time
        wends = [x[0]["_t1"] for x in self.W]
        import bisect
        for r in self.P + self.M:
            h = bisect.bisect_right(wends, r["_t1"])
            r["w_head_lo"] = h & 0xFFFF

    def _index(self):
        import bisect
        self._p_ends = [r["_t1"] for r in self.P]
        self._poll_starts = [(p["tick_start"], p["c_start"]) for p in self.POLL]
        self._snap_t = [a for (a, _c) in self.snap]
        self._w_ends = [w["_t1"] for (w, _e) in self.W] if self.W else []
        self._bis = bisect

    def p_head_at(self, t):
        # records are published at their end time; P ends are monotonic in seq
        return self._bis.bisect_right(self._p_ends, t)

    def loop_at(self, t):
        return self._bis.bisect_right(self._poll_starts, t)

    # ---------------------------------------------------------- collector
    def run_collector(self, out_dir):
        rng = self.rng
        ws = 5000                                   # worker start (20 s)
        rings = {F.RING_W: [], F.RING_P: [], F.RING_POLL: [], F.RING_S: [], F.RING_M: []}
        avail = {}
        rings[F.RING_P] = [(r["_t1"], pack(F.SC_FIELDS, r), r) for r in self.P]
        rings[F.RING_POLL] = [(((p["tick_start"] + p["body_ticks"]), p["c_end"]), pack(F.POLL_FIELDS, p), p)
                              for p in self.POLL]
        rings[F.RING_W] = [(w["_t1"], pack_w(w, e), w) for (w, e) in self.W]
        rings[F.RING_M] = [(r["_t1"], pack(F.SC_FIELDS, r), r) for r in self.M]
        pos = {r: 0 for r in rings}
        files = []                                  # dicts: nnn, data bytearray, conf, complete
        ledger = []
        events = []
        ev_q = []
        kmsg_sent = False
        flushes = 0
        seg_end = None
        active = None
        tick = ws
        n = 0
        durable_tick = 0
        mouse_pkts_seen = 0
        part_start, data_start = 63, 8192
        self.geom = dict(ms_part_start=part_start, fat_start=32, fat_length=4000, fats=2, fsinfo_sector=1,
                         data_start=data_start, sec_per_clus_bits=64 | (9 << 16))

        s_list = []                                 # the S ring: (avail, packed, dict), seq = index
        s_clock = {"tick": -1, "c": 0}
        pending_shape = sorted(getattr(self, "shape_s", []), key=lambda d: (d["tick_on"], d["c_on"]))

        def push_s(d):
            d = dict(d)
            d["seq"] = len(s_list)
            s_list.append((d["_t1"], pack(F.S_FIELDS, d), d))
            self._s_head = len(s_list)

        def add_s(t, nsect, sector, meta, pid=WRK_PID, flags_extra=0, set_or=0x40, clr_or=0x40):
            if s_clock["tick"] != t:
                s_clock["tick"], s_clock["c"] = t, 5000
            c_on = s_clock["c"]
            dur = 25000 * nsect
            to, co = tadd(t, c_on, dur)
            s_clock["c"] = c_on + dur + 2000
            push_s(dict(tick_on=t, c_on=c_on, c_off=co, sector=sector, dtick=to - t, pid=pid, nsect=nsect,
                        flags=0x01 | (0x80 if meta else 0) | flags_extra,
                        p_head_lo=self.p_head_at((t, c_on)) & 0xFFFF, led_ops=2 * nsect, rsv29=0, rsv30=0,
                        rd_set_or=set_or, rd_clr_or=clr_or, _t1=(to, co)))

        def file_sector(f, off):
            return part_start + data_start + (f["index"] * (SEG // 512)) + off // 512

        def write_data_s(f, off, length, t):
            o = off
            while o < off + length:
                ns = min(8, (off + length - o + 511) // 512)
                add_s(t, ns, file_sector(f, o), False)
                o += ns * 512
            add_s(t, 1, part_start + data_start - 64, True)        # directory entry
            add_s(t, 1, part_start + 1, True)                      # FSINFO

        pad_sector = chunk(F.CHUNK_PAD, bytes(F.PAD_SECTOR_LEN), F.FSEQ_PREALLOC, self.nonce)
        creating = None

        def new_file(t):
            nnn = len(files) + 1
            f = dict(nnn=nnn, index=len(files), data=bytearray(), conf=0, complete=False, fseq=0, active=False,
                     name="T%03d%03d.BIN" % (self.run_no, nnn))
            st = self.stats_block(t, durable_tick, None)
            fh = struct.pack(F.FILEHDR_FMT, F.FILEHDR_MAGIC, F.FORMAT_VERSION, self.run_no, nnn, 1, WRK_PID,
                             SUP_PID, t, (t - 75000) & 0xFFFFFFFF, self.nonce)
            ver = SYNTH_BANNER.ljust(256, b"\0")
            c1 = chunk(F.CHUNK_FILEHDR, fh + st + ver, 0, self.nonce)
            off = len(c1)
            c2 = chunk(F.CHUNK_PAD, bytes(F.pad_len_at(off)), 1, self.nonce)
            f["data"] += c1 + c2
            assert len(f["data"]) == F.FILEHDR_AREA
            f["fseq"] = 2
            f["conf"] = F.FILEHDR_AREA
            write_data_s(f, 0, F.FILEHDR_AREA, t)
            files.append(f)
            ev_q.append("%d segment create %s" % (t, f["name"]))
            return f

        while tick < self.end_tick:
            # ---- 1-2 snapshot and capped drain
            m = 4 if n == 0 else 1
            now = (tick, 200000)
            while pending_shape and pending_shape[0]["tick_on"] <= tick:
                push_s(pending_shape.pop(0))
            drained = {}
            for ring in (F.RING_W, F.RING_P, F.RING_POLL, F.RING_S, F.RING_M):
                if ring == F.RING_S:
                    src = s_list
                else:
                    src = rings[ring]
                cap = F.CAP[ring] * m
                got = []
                while pos[ring] < len(src) and len(got) < cap and src[pos[ring]][0] <= now:
                    got.append(src[pos[ring]])
                    pos[ring] += 1
                drained[ring] = got
            # ---- 7 flush
            recs = b""
            for ring in (F.RING_W, F.RING_P, F.RING_POLL, F.RING_S, F.RING_M):
                g = drained[ring]
                recs += struct.pack(F.BLK_HDR_FMT, ring, F.RING_DIV4[ring], len(g), 0) + b"".join(x[1] for x in g)
            resend = getattr(self, "_resend", None)
            if resend is not None and flushes > 0 and n == self._resend_at:
                rb = b""
                for ring in (F.RING_W, F.RING_P, F.RING_POLL, F.RING_S, F.RING_M):
                    g = resend.get(ring, [])
                    if g:
                        rb += struct.pack(F.BLK_HDR_FMT, ring | F.BLK_RESEND, F.RING_DIV4[ring], len(g), 0) + \
                            b"".join(x[1] for x in g)
                recs = rb + recs
            if active is not None and seg_end + F.FLUSH_MAX <= active["conf"]:
                f = active
                cur = self.uhb(tick, files, active, creating, durable_tick, n)
                parts = [(F.CHUNK_RECS, recs), (F.CHUNK_UHB, cur)]
                if flushes % 8 == 0:
                    parts.append((F.CHUNK_STATS, self.stats_block(tick, durable_tick, pos)))
                if flushes % 40 == 0:
                    parts.append((F.CHUNK_PROCS, self.procs(tick).encode()))
                if not kmsg_sent:
                    parts.append((F.CHUNK_KMSG, b"<4>PSC5 P4096 POLL2048 W256 S4096 M64 bootnop ret=%d nw=%d "
                                                b"rx2=%02x\n" % (self.W[0][0]["ret"], self.W[0][0]["nwords"],
                                                                 self.W[0][0]["rx"][2])))
                    kmsg_sent = True
                if self.flush_fail and flushes == 30:
                    ev_q.append("%d flush fail %d %d 5" % (tick, seg_end, 2048))
                    self._resend = {r: drained[r] for r in drained}
                    self._resend_at = n + 2
                if ev_q:
                    parts.append((F.CHUNK_EVENT, ("\n".join(ev_q) + "\n").encode()))
                    events.extend(ev_q)
                    ev_q = []
                buf = b""
                rec_ids = []
                for (ct, pl) in parts:
                    off = seg_end + len(buf)
                    c = chunk(ct, pl, f["fseq"], self.nonce)
                    f["fseq"] += 1
                    if ct == F.CHUNK_RECS:
                        ids = []
                        ends = []
                        pp = 0
                        while pp < len(pl):
                            ring_b, _d, cnt, _l = struct.unpack_from(F.BLK_HDR_FMT, pl, pp)
                            pp += 8
                            sz = F.RING_RECSIZE[ring_b & 0x7F]
                            for k in range(cnt):
                                ids.append((ring_b & 0x7F, struct.unpack_from("<I", pl, pp)[0]))
                                pp += sz
                                ends.append(off + 20 + pp)
                        ledger.append(dict(file=f["name"], off=off, payload_end=off + 20 + len(pl), recs=ids,
                                           rec_ends=ends))
                    buf += c
                off = seg_end + len(buf)
                buf += chunk(F.CHUNK_PAD, bytes(F.pad_len_at(off)), f["fseq"], self.nonce)
                f["fseq"] += 1
                assert len(buf) % 512 == 0 and len(buf) <= F.FLUSH_MAX, len(buf)
                f["data"][seg_end:seg_end + len(buf)] = buf
                write_data_s(f, seg_end, len(buf), tick)
                seg_end += len(buf)
                flushes += 1
                durable_tick = tick
            else:
                # no flush this tick (start-up): rewind the drain (records stay in the ring)
                for ring in drained:
                    pos[ring] -= len(drained[ring])
            # ---- 8 creation
            complete_ahead = sum(1 for f in files if f["complete"] and f is not active)
            if creating is None and complete_ahead < 2 and len(files) < 3:
                creating = new_file(tick)
                if active is None:
                    active = creating
                    active["active"] = True
                    seg_end = F.FILEHDR_AREA
            elif creating is not None:
                f = creating
                room = (f["conf"] - seg_end) if f is active else 10 ** 9
                k = F.STEP_LARGE if room < F.ROOM_LARGE_BELOW else F.STEP_SMALL
                k = min(k, SEG - f["conf"])
                f["data"] += pad_sector * (k // 512)
                write_data_s(f, f["conf"], k, tick)
                f["conf"] += k
                if f["conf"] >= SEG:
                    f["complete"] = True
                    ev_q.append("%d segment ready %s" % (tick, f["name"]))
                    creating = None
            n += 1
            tick += 57 if n % 3 else 58
        # files out
        os.makedirs(out_dir, exist_ok=True)
        for f in files:
            with open(os.path.join(out_dir, f["name"]), "wb") as fo:
                fo.write(bytes(f["data"]))
        self.files = files
        self.ledger = ledger
        self.events = events

    # ---------------------------------------------------------- side chunks
    def counters_at(self, t):
        i = self._bis.bisect_right(self._snap_t, t)
        return self.snap[i - 1][1] if i else self.copy_cnt_zero()

    def copy_cnt_zero(self):
        d = {k: (0 if not isinstance(v, list) else [0] * 7) for k, v in self.cnt.items()}
        d["jp_stage"] = 0
        return d

    def stats_block(self, tick, durable_tick, pos):
        c = self.counters_at((tick, 100000))
        st = {n: (0 if k == 1 else [0] * k) for (n, _c, k) in F.STATS_FIELDS}
        heads = [self.p_head_at((tick, 100000)), self.loop_at((tick, 100000)),
                 self._bis.bisect_right(self._w_ends, (tick, 100000)), getattr(self, "_s_head", 0), len(self.M)]
        st.update(magic=F.STATS_MAGIC, version_size=F.STATS_VERSION_SIZE, build_id=BUILD_ID, hz=250,
                  counts_per_tick=CPT, last_reader_tick=tick, initial_jiffies=(-75000) & 0xFFFFFFFF, now_tick=tick,
                  now_count=100000, now_jiffies=(tick - 75000) & 0xFFFFFFFF, total_counts_lo=(tick * CPT) & 0xFFFFFFFF,
                  total_counts_hi=(tick * CPT) >> 32, c_pre_max=CPT + 400, head=heads,
                  addr_syscon_cmd=ADDR_SYSCON, addr_psc_sc_exit=ADDR_EXIT, addr_getctrl2=ADDR_GETC2, proc_opens=6,
                  wd_calls=tick // F.WD_CYCLE, wd_last_tick=(tick // F.WD_CYCLE) * F.WD_CYCLE,
                  oc_p08=c["oc08"], oc_p33=c["oc33"], oc_w=[tick // F.WD_CYCLE, 0, 0, 0, 0, 0, 0],
                  jp_pid=JP_PID, jp_loop=c["jp_loop"], jp_stage=c["jp_stage"], jp_state=1,
                  jp_keys=c["jp_keys"], console_sem_count=1, list_sem_count=1, t_busy=0,
                  jp_r3=c["jp_r3"], jp_r4=c["jp_r4"], jp_r5=c["jp_r5"], jp_proc_calls=c["jp_proc_calls"],
                  jp_dedupe=c["jp_dedupe"], jp_changed=c["jp_changed"], jp_lcd_unblank=c["jp_lcd_unblank"],
                  jp_mode_toggles=c["jp_mode_toggles"], jp_listsem_fail=0, jp_push_ok=c["jp_push_ok"],
                  jp_push_full=0, jp_push_eintr=0, jp_wake=c["jp_wake"], jp_mouse_calls=c["jp_mouse_calls"],
                  jp_mouse_noop=c["jp_mouse_noop"], jp_mouse_reports=c["jp_mouse_reports"], fop_open=1,
                  fop_read_enter=c["fop_read_enter"], fop_read_ret=c["fop_read_ret"], vcs_putchar=c["vcs_putchar"],
                  vcs_updscr=tick // 50, md_event_syn=c["md_event_syn"], md_notify_calls=c["md_notify_calls"],
                  md_read_ret=c["md_read_ret"], led_calls=0, led_or_set_run=0x40, led_or_clr_run=0x40,
                  kupd_count=tick // 1250, kupd_last_tick=max(0, (tick - 600) // 1250 * 1250 + 600),
                  durable_tick=durable_tick, wk_count=c["wk_count"],
                  pid_class=[WRK_PID | (1 << 24), SUP_PID | (2 << 24), OSK_PID | (3 << 24), MD_PID | (4 << 24),
                             PDF_PID | (5 << 24), 0, 0, 0], **getattr(self, "geom", {}))
        if self.shape == "H9" and self.stopped_at is not None and tick > self.stopped_at:
            st.update(jp_stage=11, jp_stage_arg=0x81234560, qfree_stage=2, qfree_queue=0x81234560,
                      qfree_pid=OSK_PID, fop_release=1)
        return pack(F.STATS_FIELDS, st)

    def uhb(self, tick, files, active, creating, durable_tick, n):
        c = self.counters_at((tick, 100000))
        flags = (1 << 9) | (1 << 11)
        if tick >= 40 * TPS:
            flags |= 0x1FE          # self-test b1..b8 passed
        seg = (active["nnn"] if active else 0)
        if creating is not None:
            v = 256 if creating["conf"] >= SEG else creating["conf"] // 8192
            seg |= (creating["nnn"] << 10) | (v << 20) | (1 << 31)
            flags |= 1 << 18
        ahead = sum(1 for f in files if f["complete"] and f is not active)
        seg |= min(ahead, 2) << 29
        u = dict(tickno=n, stats_now_tick=tick, gtod_sec=1700000000 + tick // 250, gtod_usec=0,
                 uptime_cs=tick * 2 // 5, memfree_kb=20800, mouse_pkts_total=c["mouse_pkts"],
                 mouse_press_total=c["mouse_press"], bytes_synced_total=0, last_write_ms=2, last_fsync_ms=20,
                 max_fsync_ms_60s=40, max_tick_ms_60s=260, write_errs=1 if (self.flush_fail and n > 40) else 0,
                 last_errno=0, flags=flags, durable_tick=durable_tick, lag_max=60, seg=seg, drain_stuck=0,
                 nonce=self.nonce)
        return pack(F.UHB_FIELDS, u)

    def procs(self, tick):
        osk = "" if (self.shape == "H9" and self.stopped_at and tick > self.stopped_at) else \
            "OSK %d %d (psposk2) S 1 1 1\n" % (OSK_PID, OSK_PID)
        return ("JP %d %d (kjoypad) S 1 1 1\n%sMD %d %d (pspmd) S 1 1 1\nWRK %d %d (pscol) R 1 1 1\n"
                "JPSTATUS State: S (sleeping) SigPnd: 0000000000000000 ShdPnd: 0000000000000000\n"
                "MEM MemFree: 20800 kB\n" % (JP_PID, JP_PID, osk, MD_PID, MD_PID, WRK_PID, WRK_PID))

    # ---------------------------------------------------------- shape S records
    def shape_extras(self):
        self.shape_s = []
        if self.shape == "H10":
            r = next(r for r in self.P if r.get("_h10"))
            t1 = r["tick_in"] + 1
            to, co = tadd(t1, 2000, 60000)
            self.shape_s.append(dict(tick_on=t1, c_on=2000, c_off=co, sector=63 + 8192 + 9000, dtick=to - t1,
                                     pid=WRK_PID, nsect=2, flags=0x01 | 0x10 | 0x20, p_head_lo=r["seq"] & 0xFFFF,
                                     led_ops=4, rsv29=0, rsv30=0, rd_set_or=0x48, rd_clr_or=0x40, _t1=(to, co)))

    def generate(self, out):
        self.run_thread()
        self.run_watchdog()
        self.shape_extras()
        self.run_collector(os.path.join(out, "PSCLOG"))
        write_build(os.path.join(out, "build"))
        sw = lambda s: "%d:%05.2f" % (int((s + 10) // 60), (s + 10) % 60)    # stopwatch = uptime + 10 s
        with open(os.path.join(out, "times.txt"), "w") as f:
            f.write("uptime_offset=10\nselftest_pass=%s\nc0_start=%s\nc0_end=%s\n" %
                    (sw(40.0), sw(self.op.c0), sw(self.op.c0_end)))
            if not self.healthy:
                f.write("t_death=%s\n" % sw(self.onset_s + 1))
            f.write("d0_start=%s\npull=%s\n" % (sw(self.op.d0), sw(self.op.pull)))
        truth = dict(shape=self.shape, onset_tick=self.onset, run=self.run_no, nonce=self.nonce,
                     files=[dict(name=f["name"], size=len(f["data"]), nnn=f["nnn"]) for f in self.files],
                     ledger=self.ledger, n_records={"P": len(self.P), "POLL": len(self.POLL), "W": len(self.W)},
                     events=self.events)
        with open(os.path.join(out, "truth.json"), "w") as fo:
            json.dump(truth, fo)
        return truth


def make_image(out, extra_nonce=0x0BADF00D, seed=5):
    """A whole-stick image: junk, a stale chunk of another boot, then each file
    at a 32 KB-aligned offset (contiguous clusters), then junk."""
    rng = random.Random(seed)
    img = bytearray(rng.getrandbits(8) for _ in range(300000))
    stale = chunk(F.CHUNK_RECS, struct.pack(F.BLK_HDR_FMT, 0, 20, 0, 0), 3, extra_nonce)
    img[4096:4096 + len(stale)] = stale
    while len(img) % 32768:
        img.append(0)
    with open(os.path.join(out, "truth.json")) as fi:
        truth = json.load(fi)
    for f in truth["files"]:
        with open(os.path.join(out, "PSCLOG", f["name"]), "rb") as fi:
            data = fi.read()
        img += data
        while len(img) % 32768:
            img.append(0)
    img += bytes(65536)
    with open(os.path.join(out, "stick.img"), "wb") as fo:
        fo.write(bytes(img))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shape", choices=["healthy", "H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "H10", "none"])
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--run", type=int, default=1)
    ap.add_argument("--nonce", type=lambda s: int(s, 16), default=0x1234ABCD)
    ap.add_argument("--rx2alt", action="store_true", help="healthy rx[2] codes other than the command (N-4)")
    ap.add_argument("--flush-fail", action="store_true")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--image", action="store_true")
    a = ap.parse_args()
    s = Synth(a.shape, a.seed, a.run, a.nonce, a.rx2alt, a.duration, a.flush_fail)
    t = s.generate(a.out)
    if a.image:
        make_image(a.out)
    print("%s: %d files, %d P records, onset tick %d" % (a.shape, len(t["files"]), t["n_records"]["P"],
                                                         t["onset_tick"]))


if __name__ == "__main__":
    main()
