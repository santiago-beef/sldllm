#!/usr/bin/env python3
"""pscgen.py - independent PSC stick-dump generator for the Stage 3 DECODER test.

Written for Stage 3 from the design text only; it does not import or copy the
analyst's synth.py / psc_format.py, nor the ring test agent's generator.

Sources (cited inline as D:<section>):
  handoff/design/DESIGN.md 1.0-1.8 (record formats, ctx/flag bits, stats words),
  2.x (capture semantics), 4.3-4.4 (drain caps, flush layout, segment files),
  6 / 6.1 (row signatures), 10.2 (chunks, CRC with the boot nonce, FILEHDR,
  UHB, EVENT), 10.3 (struct strings).
  Frame semantics from the ORIGINAL tree (read-only):
  arch/mips/psp/ipl_sdk/syscon.c:61-258 (prefill, result = rx[0], checksum,
  0x80/0x81 retry), :355-366 (GetCtrl2 unpack), drivers/input/joypad_psp.c
  :36-58 (key bits), :474-496 (read_input), :498-540 (process_input),
  :593-695 (mouse).
  EPC addresses: the RELEASE build's BUILD/epcmap.txt (checked at start).

Usage: pscgen.py CASE OUTDIR      (CASE in CASES below; 'all' writes every case)
Each case writes OUTDIR/<case>/PSCLOG/T001nnn.BIN (2,097,152 B each),
OUTDIR/<case>/times.txt (decoder --times) and OUTDIR/<case>/EXPECTED.json.

Simplifications (documented in REPORT.md): segment files are created
instantly at worker start (no creation-step S records); collector cadence is a
fixed 57/58 ticks; S transfers never overlap a thread command (shifted);
the pure-H1 Nop's 50 ms interrupts-off spin does not delay later ticks.
"""
import json
import os
import random
import struct
import sys
import zlib

# ---------------------------------------------------------------- constants (D:1.1, 5, 10.5)
CPT = 883651                 # Count per tick, psp.c:39
HZ = 250
WD = 1250                    # watchdog cycle (ticks)
COUNT_HZ = 220912896
SEG = 2097152                # D:4.4 segment size
FILEHDR_AREA = 1536          # FILEHDR + PAD (D:4.4 step 2, 10.2)
FLUSH_MAX = 40960            # D:4.3 step 7
INITIAL_JIFFIES = (-300 * HZ) & 0xFFFFFFFF
SPIN_MAX = 1000000           # syscon.c:12 (timeout patch)
ACK_TIMEOUT = SPIN_MAX + 1   # D:1.2 offset 24 (-4 sentinel)

# ---------------------------------------------------------------- struct strings (D:10.3)
SC_FMT = '<IIIIHBBhBBIHHHHHBBHHBBBB16sIHBBIHH'
WEXT_FMT = '<5I16I5IBBBB4I4I16IHH'
POLL_FMT = '<IIIIH7B2b5BHHBBBB'
S_FMT = '<IIIIIHHBBHBBHII'
STATS_FMT = '<192I'
CHUNK_FMT = '<4sHHIII'
BLK_FMT = '<BBHI'
FILEHDR_FMT = '<8sIIIIIIIII'
UHB_FMT = '<21I'
for fmt, size in ((SC_FMT, 80), (WEXT_FMT, 208), (POLL_FMT, 40), (S_FMT, 40), (STATS_FMT, 768),
                  (CHUNK_FMT, 20), (BLK_FMT, 8), (FILEHDR_FMT, 44), (UHB_FMT, 84)):
    assert struct.calcsize(fmt) == size, (fmt, struct.calcsize(fmt), size)

RING_P, RING_POLL, RING_W, RING_S, RING_M = 0, 1, 2, 3, 4          # D:10.2 RECS
RECSIZE = {RING_P: 80, RING_POLL: 40, RING_W: 288, RING_S: 40, RING_M: 80}
RINGLEN = {RING_P: 4096, RING_POLL: 2048, RING_W: 256, RING_S: 4096, RING_M: 64}   # D:3.1
CAP = {RING_W: 2, RING_P: 48, RING_POLL: 24, RING_S: 64, RING_M: 8}                # D:4.3 step 2
DRAIN_ORDER = (RING_W, RING_P, RING_POLL, RING_S, RING_M)

CH_PAD, CH_FILEHDR, CH_RECS, CH_STATS, CH_KMSG, CH_PROCS, CH_UHB, CH_EVENT = range(8)

# ctx (D:1.2 offset 38)
ORIG_P, ORIG_M, ORIG_WB, ORIG_WT = 0, 1, 2, 3
CTX_IE, CTX_INIRQ, CTX_JP, CTX_PCNT, CTX_SIG = 0x04, 0x08, 0x10, 0x20, 0x40
# lc_flags (D:1.2 offset 71)
LC_VALID, LC_BD, LC_INSC, LC_WDTICK, LC_NEST, LC_PANEL = 1, 2, 4, 8, 16, 32
# ext_flags (D:1.3 offset 186)
EXT_REGS, EXT_KMODE, EXT_INSC, EXT_JP, EXT_LC, EXT_MS, EXT_NEST = 1, 4, 8, 16, 32, 64, 128
# POLL (D:1.4)
RI_R1, RI_R3, RI_R4, RI_R5 = 1, 3, 4, 5
PI_CALLED, PI_DEDUPE, PI_BLANK, PI_SELECT, PI_MOUSEMODE, PI_LISTSEM, PI_LSFAIL, PI_WAKE = (1, 2, 4, 8, 16, 32,
                                                                                         64, 128)
MF_CALLED, MF_NODEV, MF_NOOP, MF_REPORTED, MF_L, MF_M, MF_R = 1, 2, 4, 8, 16, 32, 64
# S flags (D:1.5)
SF_WRITE, SF_ERR, SF_SETB3, SF_CLRB3, SF_PENTRY, SF_PEXIT, SF_M, SF_META = 1, 2, 4, 8, 16, 32, 64, 128

# joypad key bits, joypad_psp.c:36-58 (raw word: pressed = 0 bit)
K_UP, K_RT, K_DN, K_LT, K_TRI = 0x1, 0x2, 0x4, 0x8, 0x10
K_SELECT, K_LTRG, K_RTRG, K_HOLD, K_VOLUP = 0x100, 0x200, 0x400, 0x2000, 0x10000
K_MOUSE = 0x00800000
IDLE_RAW = 0xFFDFFFFF        # all buttons up; bit 21 (UNKNOWN, syscon.h:33) reads 0 (a constant status bit)

STS = 0x12                   # rx[0] status byte of healthy replies (ret = rx[0] > 0, syscon.c:211)
PIDS = {"jp": 12, "osk": 31, "md": 33, "sup": 46, "wrk": 47, "pdf1": 9, "pdf2": 10}
NONCE = 0x6C3A91E5

BUILD = "/home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD"
RELEASE_BANNER = open(os.path.join(BUILD, "banner.txt"), "rb").read()      # == /proc/version (D:1.7 word 2)
OTHER_BANNER = RELEASE_BANNER.replace(b"05:32:47", b"05:57:06")            # G2-attempt-2 verifier rebuild

# ---------------------------------------------------------------- EPCs from the release epcmap
def _epcmap():
    rows = []
    for line in open(os.path.join(BUILD, "epcmap.txt")):
        p = line.split()
        if len(p) >= 3 and not line.startswith("#"):
            try:
                rows.append((int(p[0], 16), int(p[1], 16), p[2]))
            except ValueError:
                pass
    return rows


EPC = {}
for _s, _e, _l in _epcmap():
    EPC.setdefault(_l, []).append((_s, _e))
SYMS = {}
for line in open(os.path.join(BUILD, "System.map")):
    p = line.split()
    if len(p) == 3:
        SYMS[p[2]] = int(p[0], 16)


def epc_in(label, addr):
    return any(s <= addr < e for (s, e) in EPC.get(label, []))


A_S14 = 0x880cf0a4           # ACK wait loop (S14); checked below
A_S18_PEND = 0x880cf230      # S18, status loaded, data load not yet run (regmap 'pending' range)
A_IDLE = SYMS["r4k_wait"] + 8
assert epc_in("S14", A_S14) and epc_in("S18", A_S18_PEND), "release epcmap changed"
ADDR_SYSCON = SYMS["Syscon_cmd"]
ADDR_SCEXIT = SYMS["psc_sc_exit"]
ADDR_GETCTRL2 = SYMS["_pspSysconGetCtrl2"]
JP_STACK = 0x81fe2000        # the joypad thread's 8 KB stack (illustrative)
RX_BUF = JP_STACK + 0x1d58
TX_BUF = JP_STACK + 0x1d48
IDLE_SP = SYMS["init_thread_union"] + 0x1f00


def crc(data, init=0):
    return zlib.crc32(data, init) & 0xFFFFFFFF


def fine(tick, c):
    return tick * CPT + c


def split(t):
    return t // CPT, t % CPT


def us(x):
    return int(x * COUNT_HZ / 1e6)


# ---------------------------------------------------------------- syscon frames (syscon.c:226-246)
def frame(code, payload=b"", sts=STS, length=None):
    """A reply: rx[0] status, rx[1] = bytes before the checksum, rx[2] response
    code, payload, checksum = ~sum, padded to whole 16-bit words."""
    body = bytearray([sts, 0, code]) + bytearray(payload)
    body[1] = len(body) if length is None else length
    ck = (sum(body) & 0xFF) ^ 0xFF
    full = bytes(body) + bytes([ck])
    if len(full) & 1:
        full += b"\x00"
    return full


def rx16(words_bytes):
    return (bytes(words_bytes) + b"\xff" * 16)[:16]


def checksum_valid(rx):
    n = rx[1]
    return 3 <= n < 16 and ((sum(rx[:n]) & 0xFF) ^ 0xFF) == rx[n]


def getctrl_reply(raw, x, y, code=0x08, sts=STS):
    return frame(code, struct.pack('<I', raw) + bytes([x, y]), sts)


# ---------------------------------------------------------------- operator script (RUNBOOK B-D)
class Operator(object):
    """Physical button/stick state against uptime seconds."""

    def __init__(self, case, rnd):
        self.rnd = rnd
        self.idle = case.get("idle_raw", IDLE_RAW)
        self.ev = []          # (t0, t1, bits) raw bits held low
        self.stick = []       # (t0, t1, x, y)
        self.t_onset = case["onset_s"]
        if case.get("early"):
            # early death (RUNBOOK B abort-rule exception): three TRIANGLE holds for BTN, no B6,
            # no C0, no C1; the post-death script D at d0 (around the 3:00 decision)
            for k in range(3):
                self.ev.append((55.0 + 4 * k, 57.0 + 4 * k, K_TRI))
            d0 = case["d0_s"]
            self.script(d0 + 2.0)
            self.ev.append((d0 + 64.0, d0 + 64.15, K_SELECT))
            for i in range(5):
                self.ev.append((d0 + 65.0 + i, d0 + 65.1 + i, K_LTRG))
            return
        # B4: TRIANGLE held 2 s for BTN
        self.ev.append((55.0, 57.0, K_TRI))
        # B6: one SELECT tap -> mouse mode on
        self.ev.append((65.0, 65.15, K_SELECT))
        self.script(case["c0_s"] + 2.0)                           # C0 = D1..D7, healthy
        # C1: L clicks 4/s, a 5 s rest every 30 s, a stick nudge every 20 s
        t = case["c0_end_s"] + 1.0
        while t < case["death_seen_s"]:
            if int((t - case["c0_end_s"]) // 30) != int((t + 0.25 - case["c0_end_s"]) // 30):
                t += 5.0
                continue
            self.ev.append((t, t + 0.10, K_LTRG))
            t += 0.25
        tt = case["c0_end_s"] + 10.0
        while tt < case["death_seen_s"] - 2:
            self.stick.append((tt, tt + 0.6, 0xF0, 0x81))
            tt += 20.0
        d0 = case["d0_s"]
        self.script(d0 + 2.0)                                     # D1..D7
        self.ev.append((d0 + 64.0, d0 + 64.15, K_SELECT))         # D7a
        for i in range(5):
            self.ev.append((d0 + 65.0 + i, d0 + 65.1 + i, K_LTRG))

    def script(self, s0):
        t = s0
        for i in range(40):                                       # D1: 10 s of L clicks
            self.ev.append((t + 0.25 * i, t + 0.25 * i + 0.10, K_LTRG))
        t += 15.0                                                 # + D2 5 s release
        for k in range(2):                                        # D3
            self.ev.append((t, t + 3.0, K_TRI))
            t += 6.0
        self.ev.append((t, t + 3.0, K_RT)); t += 6.0              # D4
        self.ev.append((t, t + 3.0, K_VOLUP)); t += 6.0           # D5
        self.stick.append((t, t + 3.0, 0xFF, 0x81)); t += 6.0     # D6 right
        self.stick.append((t, t + 3.0, 0x81, 0x00)); t += 6.0     # D6 up
        self.ev.append((t, t + 5.0, K_HOLD)); t += 10.0           # D7

    def state(self, s):
        raw = self.idle
        for (a, b, bits) in self.ev:
            if a <= s < b:
                raw &= ~bits & 0xFFFFFFFF
        x, y = 0x80 + self.rnd.randint(0, 3), 0x80 + self.rnd.randint(0, 3)    # jitter inside one nibble
        for (a, b, sx, sy) in self.stick:
            if a <= s < b:
                x, y = sx, sy
        return raw, x, y


def mouse_rel(v):            # joypad_psp.c:661-695
    n = (v >> 4) & 0xF
    return {0: -16, 1: -4, 2: -2, 3: -2, 4: -1, 5: -1, 0xa: 1, 0xb: 1, 0xc: 2, 0xd: 2, 0xe: 4, 0xf: 16}.get(n, 0)


# ---------------------------------------------------------------- the generator
class Gen(object):
    def __init__(self, name, case):
        self.name, self.case = name, case
        self.rnd = random.Random(case.get("seed", 1))
        self.op = Operator(case, self.rnd)
        self.recs = {r: [] for r in range(5)}          # ring -> [(publish_t, bytes, info)]
        self.cnt_ev = []                               # (t, key, delta)
        self.cmd_spans = []                            # (t0, t1) of every thread command
        self.cmd_id = 0
        self.w_seq = 0
        self.p_seq = 0
        self.wd_calls = 0
        self.expect = {}
        self.pending = None                            # reply-lag model (N2b)
        self.straddles = []
        self.word2 = crc(case.get("banner", RELEASE_BANNER))
        self.onset_tick = int(round(case["onset_s"] * HZ))
        self.kupd_ticks = []
        self.jp_keys = 0
        self.jp_loop = 0
        self.frozen = None

    # -- counters
    def inc(self, t, key, d=1):
        self.cnt_ev.append((t, key, d))

    # -- SC record (D:1.2)
    def sc_bytes(self, seq, t0, t1, cmd, txlen, o, ctx, wn=0, w_head=0, lc=None):
        tk0, c0 = split(t0)
        tk1, c1 = split(t1)
        lc = lc or {}
        return struct.pack(SC_FMT, seq, tk0, c0, c1, min(tk1 - tk0, 0xFFFF), cmd, txlen, o["ret"], o["nwords"],
                           o.get("retries", 0), o.get("ack", 20), o.get("drain", 0), o.get("drain_last", 0),
                           o.get("gpio", 0x0008), o.get("st9", 0x0005), o.get("sttx", 0x0007), ctx, wn,
                           w_head & 0xFFFF, 0, 0, 0, 0, 0, o["rx"], lc.get("epc", 0), lc.get("dtick", 0xFFFF),
                           lc.get("n", 0), lc.get("flags", 0), 0, 0, 0)

    # -- syscon outcome per command (the case's model)
    def healthy(self, cmd, raw=IDLE_RAW, x=0x80, y=0x80):
        code = self.case.get("rx2", {}).get(cmd, cmd)
        if cmd == 0x08:
            fr = getctrl_reply(raw, x, y, code)
        else:
            fr = frame(code)
        return {"ret": fr[0], "nwords": len(fr) // 2, "rx": rx16(fr), "ack": self.rnd.randint(15, 30),
                "frame": fr}

    def outcome(self, cmd, origin, t, phys, post, extra=None):
        """Received frame and capture fields for one command (D:6 rows)."""
        raw, x, y = phys
        h = self.healthy(cmd, raw, x, y)
        mode = self.case["mode"] if post else "healthy"
        thread = origin == ORIG_P
        if mode == "healthy" or mode == "h7":
            return h
        if mode in ("h1", "h1pure", "h4p4"):
            if thread or mode == "h1pure":
                return {"ret": -4, "nwords": 0, "rx": b"\xff" * 16, "ack": ACK_TIMEOUT, "dur": us(50000)}
            return h
        if mode == "h2" and cmd == 0x08:
            fr = b"\x00" * 10                                       # all-zero 5-word frame, result 0, no checksum
            return {"ret": 0, "nwords": 5, "rx": rx16(fr), "ack": h["ack"]}
        if mode == "h3" and cmd == 0x08:
            return {"ret": 0, "nwords": 0, "rx": b"\xff" * 16, "ack": h["ack"]}   # RX FIFO empty after ACK
        if mode == "h5busy" and thread:
            fr = frame(0x81)                                        # SYSCON_RES_81 on all 16 tries
            return {"ret": -5, "nwords": len(fr) // 2, "rx": rx16(fr), "retries": 16, "ack": h["ack"],
                    "dur": 16 * us(110)}
        if mode == "h5cks" and cmd == 0x08:
            fr = bytearray(h["frame"])
            fr[9] ^= 0x5A                                           # checksum byte wrong
            return {"ret": -2, "nwords": 5, "rx": rx16(fr), "ack": h["ack"]}
        if mode in ("h6", "h6rx2") and cmd == 0x08:
            fr = self.frozen                                         # stale: same bytes whatever is pressed
            return {"ret": fr[0], "nwords": len(fr) // 2, "rx": rx16(fr), "ack": h["ack"]}
        if mode == "h8":
            # ACK latch stuck set: no wait (ack_polls 0), FIFO not yet filled: E3; GPIO/SPI values changed
            return {"ret": 0, "nwords": 0, "rx": b"\xff" * 16, "ack": 0, "gpio": 0x0018, "st9": 0x0001}
        if mode == "lag":
            got = self.pending
            self.pending = h["frame"]
            return {"ret": got[0], "nwords": len(got) // 2, "rx": rx16(got), "ack": h["ack"]}
        if mode == "none" and cmd == 0x08:
            k = extra % 4                       # a mixture: no row reaches 90 % (D:6 preamble)
            if k == 0:
                fr = self.frozen
                return {"ret": fr[0], "nwords": len(fr) // 2, "rx": rx16(fr), "ack": h["ack"]}
            if k == 1:
                return {"ret": -4, "nwords": 0, "rx": b"\xff" * 16, "ack": ACK_TIMEOUT, "dur": us(50000)}
            if k == 2:
                fr = bytearray(h["frame"])
                fr[9] ^= 0x33
                return {"ret": -2, "nwords": 5, "rx": rx16(fr), "ack": h["ack"]}
            fr = frame(0x81)
            return {"ret": -5, "nwords": len(fr) // 2, "rx": rx16(fr), "retries": 16, "ack": h["ack"],
                    "dur": 16 * us(110)}
        if mode == "nw7" and cmd == 0x08:
            long_fr = frame(0x08, struct.pack('<I', raw) + bytes([x, y]) + b"\x11\x22\x33\x44\x55")  # rx[1] = 14
            if long_fr[14] == 0xFF:
                long_fr = frame(0x08, struct.pack('<I', raw) + bytes([x, y]) + b"\x11\x22\x33\x44\x56")
            if extra % 10 == 9:
                fr = bytearray(long_fr)
                fr[14] ^= 0x0F                                      # 8 words, last not 0xFFFF: exact 8
                return {"ret": -2, "nwords": 8, "rx": rx16(fr), "ack": h["ack"], "n8": 1}
            cut = long_fr[:14]                                      # 7 words, then FIFO empty
            return {"ret": -2, "nwords": 7, "rx": rx16(cut), "ack": h["ack"], "n7": 1}
        return h

    # -- W record (D:1.3)
    def emit_w(self, tick, origin, o, ext=None, t_in=None):
        t0 = t_in if t_in is not None else fine(tick, 2600 + self.rnd.randint(0, 400))
        dur = o.get("dur", us(110) + self.rnd.randint(0, 3000))
        t1 = t0 + dur
        seq = self.w_seq
        self.w_seq += 1
        ctx = origin | (CTX_JP if ext and ext.get("ext_flags", 0) & EXT_JP else 0)
        sc = bytearray(self.sc_bytes(seq, t0, t1, 0x00, 2, o, ctx, 0, self.w_seq))
        if dur > CPT:
            # interrupts off for the whole Nop (pure H1): no tick in between, c_out > CPT, dtick 0
            struct.pack_into('<IH', sc, 12, split(t0)[1] + dur, 0)
        e = ext or {}
        regs = e.get("r", [0] * 16)
        lcr = e.get("lc_r", [0] * 16)
        wx = struct.pack(WEXT_FMT, e.get("epc", 0), e.get("cause", 0), e.get("status", 0x10000001),
                         e.get("ra", 0), e.get("sp", 0), *regs, e.get("pid", 0), e.get("p_head", self.p_seq),
                         e.get("jp_loop", 0), e.get("t_entry_tick", 0), e.get("t_entry_c", 0), e.get("t_busy", 0),
                         e.get("jp_stage", 17), e.get("ext_flags", 0), e.get("cur_pcnt", 0),
                         e.get("c_pre", CPT + self.rnd.randint(-40, 40)), e.get("lc_tick", 0),
                         e.get("lc_c_pre", 0), e.get("lc_cmd_id", 0), e.get("lc_epc", 0), e.get("lc_cause", 0),
                         e.get("lc_ra", 0), e.get("lc_sp", 0), *lcr, e.get("lc_n", 0), 0)
        if origin == ORIG_WB:
            wx = b"\x00" * 208
        self.recs[RING_W].append((t1, bytes(sc) + wx, {"tick": tick, "origin": origin}))
        self.wd_calls += 1
        self.inc(t1, "wd_calls")
        self._outcome_counter(t1, "oc_w", o)
        return seq, t0, t1

    def _outcome_counter(self, t, base, o):
        r = o["ret"]
        k = (0 if r > 0 else 1 if (r == 0 and o["nwords"] > 0) else 2 if r == 0 else
             {-2: 3, -3: 4, -4: 5, -5: 6}[r])
        self.inc(t, "%s%d" % (base, k))

    def idle_ext(self):
        return {"epc": A_IDLE, "sp": IDLE_SP, "ra": SYMS["cpu_idle"] + 0x40, "pid": 0,
                "ext_flags": EXT_REGS | EXT_KMODE, "jp_stage": 17, "jp_loop": self.jp_loop}

    # -- phase A: kernel records
    def nop_at(self, tick, ext=None):
        post = tick >= self.onset_tick
        o = self.outcome(0x00, ORIG_WT, fine(tick, 0), (IDLE_RAW, 0x80, 0x80), post, 0) if post else self.healthy(0x00)
        if ext and ext.get("w_outcome"):
            o = ext["w_outcome"]
        return self.emit_w(tick, ORIG_WT, o, ext or self.idle_ext())

    def phase_a(self):
        case = self.case
        rnd = self.rnd
        # WB boot Nop (prom_init, psp.c:557): W seq 0, origin WB, extension zero (D:1.3)
        self.emit_w(0, ORIG_WB, self.healthy(0x00), t_in=fine(0, 1200))
        # M: pspSysconCtrlHRPower at serial init (serial_psp.c:352), fill-once M ring (D:1.6)
        hm = self.healthy(0x34)
        t0 = fine(250, 400000)
        self.recs[RING_M].append((t0 + us(120), self.sc_bytes(0, t0, t0 + us(120), 0x34, 3, hm, ORIG_M | CTX_IE),
                                  {}))
        next_nop = WD
        # thread start near 2 s; the cadence is 14 ticks (msleep(50), dossier 9.1), aligned so that a
        # straddle case's poll lands on tick onset-1 without a jump
        tick = 500 + ((self.onset_tick - 1 - 500) % 14)
        last_keys, mouse_mode, s_keys = 0, False, 0
        btn = (False, False, False)
        prev_tick_start = None
        qlen = 0                                # psposk2's queue (PSP_JOYPAD_MAX_QUEUE 16, joypad_psp.c:63)
        end_tick = int(case["end_s"] * HZ)
        onset_done = False
        post_i = 0
        while tick < end_tick:
            s = tick / float(HZ)
            post = tick >= self.onset_tick
            straddle_poll = bool(case.get("straddle")) and not onset_done and tick == self.onset_tick - 1
            if straddle_poll:
                c_start = case["straddle_c_start"]
                wk = (c_start // 256, (c_start - 900) // 256, 1, 1, 1)    # the collector held the CPU (D:2.11)
            else:
                c_start = rnd.randint(2500, 9000)
                wk = (c_start // 256, 0, 6, 6, 1)
            t_start = fine(tick, c_start)
            self.jp_loop += 1
            self.inc(t_start, "jp_loop")
            phys = self.op.state(s)
            if post and self.frozen is None and case["mode"] in ("h6", "h6rx2", "none"):
                self.frozen = getctrl_reply(self.op.idle, 0x81, 0x82, case.get("rx2", {}).get(0x08, 0x08))
            t = t_start + 300
            p_first = self.p_seq
            results = {}
            for (cmd, txlen) in ((0x33, 3), (0x08, 2)):
                tk_in = split(t)[0]
                while next_nop <= tk_in:                    # Nops of earlier ticks come first
                    self.nop_at(next_nop)
                    next_nop += WD
                ext_w = None
                if straddle_poll and cmd == 0x08:
                    o, ext_w = self.straddle(cmd, t, phys)
                    onset_done = True
                else:
                    o = self.outcome(cmd, ORIG_P, t, phys, post, post_i)
                    o["dur"] = o.get("dur", (us(105) if cmd == 0x33 else us(165)) + rnd.randint(0, 4000))
                self.cmd_id += 1
                t_in, t_out = t, t + o["dur"]
                tk_out = split(t_out)[0]
                wn, w_head, lc = 0, self.w_seq, {}
                if tk_out > tk_in:
                    # every tick crossing a command counts in dtick; T2a records the thread running (D:2.3)
                    while next_nop <= tk_out:
                        e = ext_w or self.generic_straddle_ext(next_nop, tk_in, t_in, cmd)
                        wseq, _a, _b = self.nop_at(next_nop, e)
                        self.straddles.append((wseq, self.p_seq, next_nop))
                        next_nop += WD
                        wn += 1
                        ext_w = None
                    w_head = self.w_seq
                    lc = {"epc": o.get("lc_epc", A_S14), "dtick": tk_out - tk_in, "n": min(255, tk_out - tk_in),
                          "flags": LC_VALID | LC_INSC | (LC_WDTICK if tk_out % WD == 0 else 0)}
                rec = self.sc_bytes(self.p_seq, t_in, t_out, cmd, txlen, o, ORIG_P | CTX_IE | CTX_JP, wn, w_head, lc)
                self.recs[RING_P].append((t_out, rec, {"cmd": cmd, "ret": o["ret"], "nwords": o["nwords"],
                                                       "wn": wn}))
                self.cmd_spans.append((t_in, t_out))
                self._outcome_counter(t_out, "oc_p08" if cmd == 0x08 else "oc_p33", o)
                if wn:
                    self.inc(t_out, "p_nested")
                if tk_out > tk_in:
                    self.inc(t_out, "p_ticked")
                results[cmd] = o
                self.p_seq += 1
                t = t_out + rnd.randint(1800, 2600)
            # read_input / process_input / mouse (joypad_psp.c:474-659)
            o08 = results[0x08]
            pi, nq, pok, pfail, mf, dx, dy, stage = 0, 0, 0, 0, 0, 0, 0, 4
            if o08["ret"] < 0:
                br = RI_R3
                self.inc(t, "jp_r3")
            else:
                rx = o08["rx"]
                key = rx[3] | rx[4] << 8 | rx[5] << 16 | rx[6] << 24
                keys = (~key) & 0xFFFFFFFF
                if keys & K_HOLD:
                    br = RI_R4
                    self.inc(t, "jp_r4")
                else:
                    br = RI_R5
                    self.inc(t, "jp_r5")
                    self.inc(t, "jp_proc_calls")
                    x, y = rx[7], rx[8]
                    kk = keys | ((x & 0xF0) << 20) | ((y & 0xF0) << 24)
                    pi |= PI_CALLED
                    stage = 5
                    if kk == last_keys:
                        pi |= PI_DEDUPE
                        stage = 6
                        self.inc(t, "jp_dedupe")
                    else:
                        last_keys = kk
                        self.inc(t, "jp_changed")
                        self.inc(t, "jp_lcd_unblank")
                        if kk & K_SELECT:
                            mouse_mode = not mouse_mode
                            pi |= PI_SELECT
                            self.inc(t, "jp_mode_toggles")
                        if mouse_mode:
                            kk |= K_MOUSE
                        s_keys = kk
                        self.jp_keys = kk
                        pi |= PI_LISTSEM | PI_WAKE
                        nq = 1
                        consumer_alive = not (post and case["mode"] == "h7")
                        if qlen < 16:
                            pok = 1
                            qlen += 1
                            self.inc(t, "jp_push_ok")
                            if consumer_alive:
                                qlen -= 1
                                self.inc(t + 5000, "fop_read_ret")
                                self.inc(t + 5000, "fop_read_enter")
                        else:
                            pfail = 1                                  # low nibble: queue full (:395-399)
                            self.inc(t, "jp_push_full")
                        self.inc(t, "jp_wake")
                        stage = 14
                    if mouse_mode:
                        pi |= PI_MOUSEMODE
                    if s_keys & K_MOUSE:
                        mf |= MF_CALLED
                        stage = max(stage, 15)
                        self.inc(t, "jp_mouse_calls")
                        dx, dy = mouse_rel(x), mouse_rel(y)
                        left = bool(keys & K_LTRG) and not keys & K_RTRG
                        right = bool(keys & K_RTRG) and not keys & K_LTRG
                        mid = bool(keys & K_LTRG) and bool(keys & K_RTRG)
                        dx += (-2 if keys & K_LT else 0) + (2 if keys & K_RT else 0)
                        dy += (-2 if keys & K_UP else 0) + (2 if keys & K_DN else 0)
                        if dx == 0 and dy == 0 and (left, mid, right) == btn:
                            mf |= MF_NOOP
                            self.inc(t, "jp_mouse_noop")
                        else:
                            press = left and not btn[0]
                            btn = (left, mid, right)
                            mf |= MF_REPORTED | (MF_L if left else 0) | (MF_M if mid else 0) | (MF_R if right else 0)
                            stage = 16
                            self.inc(t, "jp_mouse_reports")
                            self.inc(t, "md_event_syn")
                            self.inc(t, "md_notify_calls")
                            self.inc(t + 9000, "md_read_ret")             # the collector's own mice client
                            self.inc(t + 9000, "coll_pkts")
                            if press:
                                self.inc(t + 9000, "coll_press")
                            if not (post and case["mode"] == "h7"):
                                self.inc(t + 7000, "md_read_ret")         # pspmd
                        dx, dy = max(-128, min(127, dx)), max(-128, min(127, dy))
            c_end_t = t + 900
            tk_end, c_end = split(c_end_t)
            period = (tick - prev_tick_start) if prev_tick_start is not None else 14
            pol = struct.pack(POLL_FMT, self.jp_loop - 1, tick, c_start, c_end, p_first & 0xFFFF,
                              min(255, tk_end - tick), br, pi, nq, pok, pfail, mf, dx, dy, 0, min(255, period), 0,
                              stage, 2, min(wk[0], 0xFFFF), max(0, min(wk[1], 0xFFFF)), wk[2], wk[3], wk[4], 0)
            self.recs[RING_POLL].append((c_end_t, pol, {}))
            self.inc(c_end_t, "wk_count")
            prev_tick_start = tick
            if post:
                post_i += 1
            tick = tk_end + 14                    # msleep(50) = 14 jiffies
        while next_nop < end_tick:
            self.nop_at(next_nop)
            next_nop += WD
        k = 600                                   # wb_kupdate every 5 s at watchdog phase 600 (D:2.7)
        while k < end_tick:
            self.inc(fine(k, 1000), "kupd_count")
            self.kupd_ticks.append(k)
            k += WD
        for r in self.recs:
            self.recs[r].sort(key=lambda x: x[0])
        seqs = [struct.unpack_from('<I', x[1], 0)[0] for x in self.recs[RING_P]]
        assert seqs == list(range(len(seqs))), "P seq order"
        seqs = [struct.unpack_from('<I', x[1], 0)[0] for x in self.recs[RING_W]]
        assert seqs == list(range(len(seqs))), "W seq order"

    def generic_straddle_ext(self, b, tk_in, t_in, cmd):
        """A Nop at tick b while the thread spins at S14 in a long command (H1 shapes)."""
        regs = [0] * 16
        regs[5] = RX_BUF if cmd == 0x08 else RX_BUF
        regs[11] = TX_BUF
        regs[15] = RX_BUF + 2
        e = {"epc": A_S14, "sp": JP_STACK + 0x1d00, "ra": ADDR_SYSCON + 0x30, "pid": PIDS["jp"], "r": regs,
             "p_head": self.p_seq, "jp_loop": self.jp_loop, "t_entry_tick": tk_in, "t_entry_c": split(t_in)[1],
             "t_busy": 1, "jp_stage": 3 if cmd == 0x08 else 2,
             "ext_flags": EXT_REGS | EXT_KMODE | EXT_INSC | EXT_JP}
        if b - 1 > tk_in:
            e["ext_flags"] |= EXT_LC
            e.update(lc_tick=b - 1, lc_c_pre=CPT, lc_cmd_id=self.cmd_id, lc_epc=A_S14, lc_n=b - 1 - tk_in,
                     lc_sp=JP_STACK + 0x1d00, lc_r=regs)
        return e

    def straddle(self, cmd, t, phys):
        """The H4 onset: a Nop at tick 1250k while the thread's 0x08 is in flight (D:6 row H4)."""
        case = self.case
        raw, x, y = phys
        mode = case["mode"]
        h = self.healthy(0x08, raw, x, y)
        regs = [0] * 16
        regs[11] = TX_BUF
        regs[15] = RX_BUF + 2
        regs[9] = STS
        regs[14] = 0
        ext = {"sp": JP_STACK + 0x1d00, "ra": ADDR_SYSCON + 0x30, "pid": PIDS["jp"], "p_head": self.p_seq,
               "jp_loop": self.jp_loop, "t_entry_tick": split(t)[0], "t_entry_c": split(t)[1], "t_busy": 1,
               "jp_stage": 3, "ext_flags": EXT_REGS | EXT_KMODE | EXT_INSC | EXT_JP}
        B = self.onset_tick
        if mode == "lag":
            # P5a: the thread's reply is in the FIFO, latch set; the Nop pre-drains it (drain 5, reply-shaped
            # drain_last), its ACK poll exits at once (ack_polls 0), its RX read finds nothing (E3); the thread
            # resumes and reads an empty FIFO (E3, allowed at P5a); the syscon is one reply behind from now on.
            fr = h["frame"]
            wo = {"ret": 0, "nwords": 0, "rx": b"\xff" * 16, "ack": 0, "drain": 5,
                  "drain_last": fr[8] << 8 | fr[9]}
            ext.update(epc=A_S14, r=regs, w_outcome=wo)
            self.pending = frame(self.case.get("rx2", {}).get(0x00, 0x00))   # the Nop's own reply, delivered late
            o = {"ret": 0, "nwords": 0, "rx": b"\xff" * 16, "ack": 3, "dur": fine(B, 38000) - t}
            self.expect["h4_ppoint"] = "P5a"
        elif mode == "h4p4":
            # P4: the Nop finds the FIFO empty (drain 0), waits for an ACK (ack_polls > 0) and reads the
            # thread's reply (foreign for the Nop); the thread then waits for the ACK the Nop consumed: -4
            wo = {"ret": h["ret"], "nwords": h["nwords"], "rx": h["rx"], "ack": 27, "drain": 0}
            ext.update(epc=A_S14, r=regs, w_outcome=wo)
            o = {"ret": -4, "nwords": 0, "rx": b"\xff" * 16, "ack": ACK_TIMEOUT, "dur": us(50000)}
            self.expect["h4_ppoint"] = "P4"
        elif mode == "nw7":
            # P6 at j = 7: the Nop lands between the 8th status load and the data load (regmap 'pending'),
            # pre-drains word 8 (drain 1); the thread pops an empty FIFO (0xFFFF, UNVERIFIED value)
            long_fr = frame(0x08, struct.pack('<I', raw) + bytes([x, y]) + b"\x11\x22\x33\x44\x55")
            regs[6] = 16                         # t0 = i + 2 with i = 14
            regs[5] = RX_BUF + 16                # a3 = rx_buf + i + 2
            regs[0] = 0x0007                     # v0: status with bit 2 (RX not empty)
            wo = dict(self.healthy(0x00))
            wo.update(drain=1, drain_last=long_fr[14] << 8 | long_fr[15])
            ext.update(epc=A_S18_PEND, r=regs, w_outcome=wo)
            o = {"ret": -2, "nwords": 7, "rx": rx16(long_fr[:14]), "ack": 22, "dur": fine(B, 41000) - t,
                 "lc_epc": A_S18_PEND, "n7": 1}
            self.expect["h4_ppoint"] = "P6"
        else:
            raise ValueError(mode)
        return o, ext

    # -- phase B: the collector (D:4.2-4.4, 10.2)
    def phase_b(self, outdir):
        import bisect
        case = self.case
        rnd = self.rnd
        os.makedirs(outdir, exist_ok=True)
        cnt = sorted(self.cnt_ev, key=lambda e: e[0])
        ci = 0
        totals = {}
        ptimes = {r: [x[0] for x in self.recs[r]] for r in range(5)}
        s_recs = self.recs[RING_S]
        s_times = []
        pos = {r: 0 for r in range(5)}           # drain positions = next seq (D:3.5, 4.3)
        files, fseq, file_clu = {}, {}, {}
        events_q = []
        worker_tick = int(case["worker_s"] * HZ)
        end_tick = int(case["end_s"] * HZ)
        s_seq = 0
        ms = {"seg_wr": 0, "led": 0, "set_or": 0, "clr_or": 0}
        part_start, data_start, spc = 8192, 32 + 2 * 29800, 64     # FAT32, 32 KB clusters, 512 B blocks
        geom = (part_start, 32, 29800, 2, 1, data_start, spc | (9 << 16))   # stats 153-159 (D:1.7, 4.8)
        dir_sector = part_start + data_start + (3 - 2) * spc
        fsinfo = part_start + 1
        spans = sorted(self.cmd_spans)
        span_t0 = [x[0] for x in spans]
        change = case.get("word2_change_s")

        def word2_at(tk):
            return 0xDEADBEEF if (change is not None and tk >= change * HZ) else self.word2

        def heads(T):
            hd = {r: bisect.bisect_right(ptimes[r], T) for r in range(5)}
            hd[RING_S] = bisect.bisect_right(s_times, T)
            return hd

        def chunk(ctype, payload, fs, plain=False):
            c = crc(payload, 0 if plain else NONCE)            # D:10.2: FILEHDR plain, others nonce-seeded
            return struct.pack(CHUNK_FMT, b"PSCK", ctype, 5, len(payload), fs, c) + payload + \
                b"\x00" * ((-len(payload)) % 4)

        def new_file(nnn, tk):
            name = "T001%03d.BIN" % nnn
            buf = bytearray(SEG)
            pad_payload = b"\x00" * 492                         # preallocation PAD sector (D:4.4 step 3)
            sec = struct.pack(CHUNK_FMT, b"PSCK", CH_PAD, 5, 492, 0xFFFFFFFF, crc(pad_payload, NONCE)) + pad_payload
            assert len(sec) == 512
            for off in range(FILEHDR_AREA, SEG, 512):
                buf[off:off + 512] = sec
            st = self.stats_block(tk, 50000, totals, heads(fine(tk, 50000)), geom, durable, word2=word2_at(tk), ms=ms)
            ver = case.get("fh_banner", case.get("banner", RELEASE_BANNER))
            fh = struct.pack(FILEHDR_FMT, b"PSCLOG5\x00", 5, 1, nnn, 1, PIDS["wrk"], PIDS["sup"], tk,
                             (INITIAL_JIFFIES + tk) & 0xFFFFFFFF, NONCE) + st + (ver + b"\x00" * 256)[:256]
            assert len(fh) == 1068
            c1 = chunk(CH_FILEHDR, fh, 0, plain=True)
            c2 = chunk(CH_PAD, b"\x00" * (FILEHDR_AREA - len(c1) - 20), 1)
            assert len(c1) + len(c2) == FILEHDR_AREA
            buf[0:FILEHDR_AREA] = c1 + c2
            files[nnn] = buf
            fseq[nnn] = 2
            file_clu[nnn] = 1000 + nnn * 64          # 64 contiguous 32 KB clusters per 2 MB file
            return name

        def clear_of_cmds(t, dur):
            # a Memory Stick transfer never overlaps a thread command here (generator simplification)
            while True:
                i = bisect.bisect_right(span_t0, t + dur) - 1
                if i >= 0 and spans[i][1] > t:
                    t = spans[i][1] + 20000
                    continue
                return t

        durable = {"tick": 0, "next": [0] * 5}
        active = 1
        seg_end = FILEHDR_AREA
        ctick = 0
        tk = worker_tick
        bytes_synced = 0
        while ci < len(cnt) and cnt[ci][0] <= fine(tk, 0):
            totals[cnt[ci][1]] = totals.get(cnt[ci][1], 0) + cnt[ci][2]
            ci += 1
        for n in (1, 2, 3):
            events_q.append("%d segment ready %s" % (tk, new_file(n, tk)))
        next_nnn = 4
        events_q[:0] = ["%d worker start inst 1 run 1 nonce %08x" % (tk, NONCE), "%d conlevel 0 0" % tk,
                        "%d guard ok stack_hw=2312" % tk, "%d names budget 494" % tk, "%d speed 121" % tk]
        kmsg_pending = (b"<4>PSC5 P4096 POLL2048 W256 S4096 M64 bootnop ret=%d nw=2 rx2=00\n" % STS +
                        b"<6>PSP Emulate Mouse driver (NEW)\n")
        catch_prev = False
        while tk < end_tick:
            ctick += 1
            T = fine(tk, 120000 + rnd.randint(0, 20000))
            while ci < len(cnt) and cnt[ci][0] <= T:
                totals[cnt[ci][1]] = totals.get(cnt[ci][1], 0) + cnt[ci][2]
                ci += 1
            hd = heads(T)
            stats = self.stats_block(tk, split(T)[1], totals, hd, geom, durable, word2=word2_at(tk), ms=ms)
            # capped drain (D:4.3 step 2), m = 1 at a steady 0.23 s cadence
            blocks = []
            catchup = False
            new_pos = dict(pos)
            for r in DRAIN_ORDER:
                lst = s_recs if r == RING_S else self.recs[r]
                avail = hd[r] - pos[r]
                take = min(avail, CAP[r])
                catchup = catchup or take < avail
                recs = [lst[i][1] for i in range(pos[r], pos[r] + take)]
                blocks.append(struct.pack(BLK_FMT, r, RECSIZE[r] // 4, len(recs), 0) + b"".join(recs))
                new_pos[r] = pos[r] + take
            if catchup != catch_prev:
                events_q.append("%d catch-up %s" % (tk, "start" if catchup else "end"))
                catch_prev = catchup
            if tk >= int(case["selftest_s"] * HZ):
                flags = 0x1FE | (1 << 9) | (1 << 13)
            else:
                flags = (1 << 9) | (1 << 13) | 0x02
            flags |= (1 << 12) if catchup else (1 << 11)
            uhb = struct.pack(UHB_FMT, ctick, tk, 1791331200 + tk // HZ, (tk % HZ) * 4000, tk * 100 // HZ, 20800,
                              totals.get("coll_pkts", 0), totals.get("coll_press", 0), bytes_synced, 2,
                              14 + rnd.randint(0, 6), 31, 262, 0, 0, flags, durable["tick"],
                              (tk - durable["tick"]) if durable["tick"] else 0, active | (2 << 29), 0, NONCE)
            parts = [(CH_RECS, b"".join(blocks)), (CH_UHB, uhb)]
            if ctick % 8 == 1:
                parts.append((CH_STATS, stats))
            if ctick % 40 == 2:
                parts.append((CH_PROCS, self.procs_text(tk)))
            if kmsg_pending:
                parts.append((CH_KMSG, kmsg_pending))
                kmsg_pending = b""
            if events_q:
                parts.append((CH_EVENT, ("\n".join(events_q) + "\n").encode()))
                events_q = []
            if seg_end + FLUSH_MAX > SEG:                 # D:4.4 "Use and switch"
                old = active
                active += 1
                seg_end = FILEHDR_AREA
                nm = new_file(next_nnn, tk)
                next_nnn += 1
                events_q.append("%d switch T001%03d.BIN T001%03d.BIN full" % (tk, old, active))
                events_q.append("%d segment ready %s" % (tk + 1500, nm))
            body = b""
            for (ct, pl) in parts:
                body += chunk(ct, pl, fseq[active])
                fseq[active] += 1
            rem = (-len(body)) % 512
            if rem < 20:
                rem += 512
            body += chunk(CH_PAD, b"\x00" * (rem - 20), fseq[active])
            fseq[active] += 1
            assert len(body) % 512 == 0 and len(body) <= FLUSH_MAX, len(body)
            assert len(parts[0][1]) + 20 <= 34404
            files[active][seg_end:seg_end + len(body)] = body
            # the flush's own sector writes as S records: data pages <= 8 sectors, the directory
            # entry, FSINFO (D:4.8, 5.2); drained at the next tick
            nsec = len(body) // 512
            first = part_start + data_start + (file_clu[active] - 2) * spc + seg_end // 512
            segs = []
            k = 0
            while k < nsec:
                n = min(8, nsec - k)
                segs.append((first + k, n, SF_WRITE))
                k += n
            segs += [(dir_sector, 1, SF_WRITE | SF_META), (fsinfo, 1, SF_WRITE | SF_META)]
            ts = T + us(4000)
            for (sector, n, fl) in segs:
                dur = us(1800) * n
                ts = clear_of_cmds(ts, dur)
                tk_on, c_on = split(ts)
                tk_off, c_off = split(ts + dur)
                p_head = bisect.bisect_right(ptimes[RING_P], ts)
                rec = struct.pack(S_FMT, s_seq, tk_on, c_on, c_off, sector, tk_off - tk_on, PIDS["wrk"], n, fl,
                                  p_head & 0xFFFF, 2 * n, 0, 0, 0x40, 0x40)
                s_recs.append((ts + dur, rec, {}))
                s_times.append(ts + dur)
                s_seq += 1
                ms["seg_wr"] += 1
                ms["led"] += 2 * n
                ms["set_or"] |= 0x40
                ms["clr_or"] |= 0x40
                ts += dur + us(300)
            seg_end += len(body)
            bytes_synced += len(body)
            pos = new_pos
            durable = {"tick": tk, "next": [pos[r] for r in range(5)]}
            tk += 57 if ctick % 2 else 58
        for nnn, buf in files.items():
            with open(os.path.join(outdir, "T001%03d.BIN" % nnn), "wb") as f:
                f.write(buf)
        self.files = sorted(files)
        self.last_durable = durable["tick"]
        self.drained = dict(pos)

    def procs_text(self, tk):
        return ("JP %d %d (kjoypad) S 1 1 0 0 -1\nOSK %d %d (psposk2) S 1 31 0 0 -1\n"
                "MD %d %d (pspmd) S 1 33 0 0 -1\nWRK %d %d (pscol) R 46 46 46 0 -1\n"
                "JPSTATUS State:\tD (disk sleep)\nJPSTATUS SigPnd:\t00000000\nJPSTATUS ShdPnd:\t00000000\n"
                "MEM MemFree:        20800 kB\n" % (PIDS["jp"], PIDS["jp"], PIDS["osk"], PIDS["osk"], PIDS["md"],
                                                    PIDS["md"], PIDS["wrk"], PIDS["wrk"])).encode()

    def stats_block(self, tk, c, totals, hd, geom, durable, word2=None, ms=None):
        """D:1.7, word by word."""
        w = [0] * 192
        T = lambda k: totals.get(k, 0) & 0xFFFFFFFF
        w[0] = 0x54535350
        w[1] = 5 | (768 << 16)
        w[2] = self.word2 if word2 is None else word2
        w[3], w[4] = HZ, CPT
        w[5] = durable["tick"]
        w[6] = INITIAL_JIFFIES
        w[7], w[8], w[9] = tk, c, (INITIAL_JIFFIES + tk) & 0xFFFFFFFF
        tot = tk * CPT + c
        w[10], w[11] = tot & 0xFFFFFFFF, tot >> 32
        w[12], w[13] = CPT + 4200, 0
        for i, r in enumerate((RING_P, RING_POLL, RING_W, RING_S, RING_M)):
            w[14 + i] = hd.get(r, 0)
        w[19] = 0
        w[20], w[21], w[22] = ADDR_SYSCON, ADDR_SCEXIT, ADDR_GETCTRL2
        w[23] = 5
        w[24], w[25], w[26] = 560, 912, 1160
        w[27], w[28] = T("wd_calls"), (tk // WD) * WD
        w[29], w[30] = T("p_nested"), T("p_ticked")
        for k in range(7):
            w[31 + k] = T("oc_p08%d" % k)
            w[38 + k] = T("oc_p33%d" % k)
            w[45 + k] = T("oc_w%d" % k)
        w[52], w[53], w[54], w[55] = PIDS["jp"], T("jp_loop"), 17, 0
        w[56], w[57], w[58], w[59] = 2, 0, 0, 3
        w[60], w[61], w[62], w[63] = self.jp_keys & 0xFFFFFFFF, 0, 1, 1
        names = ("jp_r3 jp_r4 jp_r5 jp_proc_calls jp_dedupe jp_changed jp_lcd_unblank jp_mode_toggles "
                 "jp_listsem_fail jp_push_ok jp_push_full jp_push_eintr jp_wake jp_mouse_calls jp_mouse_noop "
                 "jp_mouse_reports").split()
        for i, n in enumerate(names):
            w[68 + i] = T(n)
        w[84], w[85], w[86], w[87], w[88], w[89] = 1, 0, T("fop_read_enter"), T("fop_read_ret"), 0, 0
        w[90], w[91], w[92] = 0, 0, 0
        w[93], w[94], w[95], w[96] = 0, 0, 0, 2
        w[97], w[98], w[99] = T("md_event_syn"), T("md_notify_calls"), T("md_read_ret")
        ms = ms or {}
        w[100], w[101], w[102], w[103] = ms.get("led", 0), 0, ms.get("set_or", 0), ms.get("clr_or", 0)
        w[104], w[105], w[106] = ms.get("seg_wr", 0), 4, 0
        w[110] = T("kupd_count")
        kt = [k for k in self.kupd_ticks if k <= tk]
        w[111] = kt[-1] if kt else 0
        w[112] = durable["tick"]
        for i in range(5):
            w[113 + i] = durable["next"][i]
        w[118] = 40
        if tk > 14500:
            w[119], w[120], w[121], w[122], w[123] = 12, 14125, 2, 10, 228520
            w[148], w[149] = 228520, 1
        w[136], w[137] = T("wk_count"), 3300
        for i, (cls, pid) in enumerate(((1, PIDS["wrk"]), (2, PIDS["sup"]), (3, PIDS["osk"]), (4, PIDS["md"]),
                                        (5, PIDS["pdf1"]), (5, PIDS["pdf2"]))):
            w[140 + i] = (cls << 24) | pid
        w[153:160] = list(geom)
        return struct.pack(STATS_FMT, *w)

    def write_case(self, outdir):
        case = self.case
        d = os.path.join(outdir, self.name)
        logdir = os.path.join(d, "PSCLOG")
        self.phase_a()
        self.phase_b(logdir)
        sw = lambda s: "%d:%04.1f" % ((s + 10) // 60, (s + 10) % 60)
        with open(os.path.join(d, "times.txt"), "w") as f:
            f.write("# operator stopwatch times (RUNBOOK E5); stopwatch = uptime + 10 s\n")
            if case.get("early"):
                f.write("# early death: no SELFTEST PASS, no C0 (RUNBOOK B exception)\n")
                f.write("launch=0:00\nt_death=%s\nd0_start=%s\npull=%s\nuptime_offset=10\n"
                        % (sw(case["d0_s"] - 2.5), sw(case["d0_s"]), sw(case["end_s"])))
            else:
                f.write("launch=0:00\nselftest_pass=%s\nc0_start=%s\nc0_end=%s\nt_death=%s\nd0_start=%s\n"
                        "pull=%s\nuptime_offset=10\n" % (sw(case["selftest_s"]), sw(case["c0_s"]),
                                                            sw(case["c0_end_s"]), sw(case["death_seen_s"]),
                                                            sw(case["d0_s"]), sw(case["end_s"])))
        p = [x[2] for x in self.recs[RING_P]]
        exp = dict(case.get("expect", {}))
        exp.update(self.expect)
        exp["onset_tick"] = self.onset_tick
        exp["onset_wdph"] = self.onset_tick % WD
        exp["records"] = {nm: len(self.recs[r]) for nm, r in (("P", RING_P), ("POLL", RING_POLL), ("W", RING_W),
                                                               ("S", RING_S), ("M", RING_M))}
        exp["p08_nwords7_records"] = sum(1 for x in p if x.get("cmd") == 0x08 and x.get("nwords") == 7)
        exp["p08_nwords8_records"] = sum(1 for x in p if x.get("cmd") == 0x08 and x.get("nwords") == 8)
        exp["straddles"] = len(self.straddles)
        exp["files"] = ["T001%03d.BIN" % n for n in self.files]
        exp["word2"] = "0x%08x" % self.word2
        exp["nonce"] = "0x%08x" % NONCE
        exp["last_durable_tick"] = self.last_durable
        with open(os.path.join(d, "EXPECTED.json"), "w") as f:
            json.dump(exp, f, indent=1)
        return exp


# ---------------------------------------------------------------- cases
def early(onset_s, **kw):
    """Death before the self-test can pass (dossier 9.6: before 36 s; S3: 17 s)."""
    c = base(onset_s, early=True, selftest_s=1e9, d0_s=172.0, **kw)
    c["end_s"] = c["d0_s"] + 108.0
    return c


def base(onset_s, **kw):
    death = onset_s + 1.5
    d0 = kw.pop("d0_s", None) or death + 2.5
    c = {"selftest_s": 60.0, "c0_s": 70.0, "c0_end_s": 135.0, "worker_s": 25.0, "onset_s": onset_s,
         "death_seen_s": death, "d0_s": d0, "end_s": d0 + 108.0, "seed": 7}
    c.update(kw)
    return c


MID = 247.6       # onset tick 61,900: 650 ticks after Nop 49, 600 before Nop 50 (not a watchdog boundary)
NOP50 = 250.0     # tick 62,500 = 1250 x 50
CASES = {
    "H1": base(MID, mode="h1", expect={"state": ["H1"], "variant": "9.5 variant", "triggers": []}),
    "H1pure": base(MID, mode="h1pure", expect={"state": ["H1"], "variant": "pure", "triggers": []}),
    "H2": base(MID, mode="h2", expect={"state": ["H2"], "triggers": []}),
    "H3": base(MID, mode="h3", expect={"state": ["H3"], "triggers": []}),
    "H4": base(NOP50, mode="lag", straddle=True, straddle_c_start=CPT - 76000,
               expect={"state": ["N2b"], "triggers": ["H4"], "ppoint": "P5a"}),
    "H4p4": base(NOP50, mode="h4p4", straddle=True, straddle_c_start=CPT - 69000,
                 expect={"state": ["H1"], "triggers": ["H4"], "ppoint": "P4"}),
    "H5": base(MID, mode="h5busy", expect={"state": ["H5"], "triggers": [], "detail": "-5 BUSY"}),
    "H5cks": base(MID, mode="h5cks", expect={"state": ["H5"], "triggers": [], "detail": "-2 checksum"}),
    "H6": base(MID, mode="h6", expect={"state": ["H6"], "triggers": []}),
    "H6rx2": base(MID, mode="h6rx2", rx2={0x08: 0x82, 0x33: 0x82, 0x00: 0x82, 0x34: 0x82},
                  expect={"state": ["H6"], "triggers": [], "detail": "template rx[2] 0x82"}),
    "H7": base(MID, mode="h7", expect={"state": ["H7"], "triggers": []}),
    "H8": base(MID, mode="h8", expect={"state": ["H3"], "h8": True, "triggers": []}),
    "NONE": base(MID, mode="none", expect={"state": [], "verdict": "UNCLASSIFIED", "triggers": []}),
    "EARLY_H1": early(12.0, mode="h1", expect={"state": ["H1"], "triggers": [], "template": False}),
    "EARLY_H3": early(12.0, mode="h3", expect={"state": ["H3"], "triggers": [], "template": False}),
    "EARLY_H6": early(17.0, mode="h6", expect={"state": ["H6"], "triggers": [], "flag": "no C0 reference"}),
    "EARLY17_H1_FF": early(17.0, mode="h1", idle_raw=0xFFFFFFFF, expect={"state": ["H1"], "triggers": []}),
    "EARLY30_H1": early(30.0, mode="h1", expect={"state": ["H1"], "triggers": []}),
    "EARLY30_H1_FF": early(30.0, mode="h1", idle_raw=0xFFFFFFFF, expect={"state": ["H1"], "triggers": []}),
    "EARLY30_H3_FF": early(30.0, mode="h3", idle_raw=0xFFFFFFFF, expect={"state": ["H3"], "triggers": []}),
    "NW7OR8": base(NOP50, mode="nw7", straddle=True, straddle_c_start=CPT - 79000,
                   expect={"state": ["H5"], "triggers": ["H4"], "ppoint": "P6", "empty_pop": True}),
    "BID_WRONG": base(NOP50, mode="lag", straddle=True, straddle_c_start=CPT - 76000, banner=OTHER_BANNER,
                      expect={"epc": "REFUSED", "state": ["N2b"], "triggers": ["H4"]}),
    "BID_FHVER": base(NOP50, mode="lag", straddle=True, straddle_c_start=CPT - 76000, fh_banner=OTHER_BANNER,
                      expect={"epc": "enabled", "note": "FILEHDR /proc/version CRC mismatch"}),
    "BID_MIDRUN": base(NOP50, mode="lag", straddle=True, straddle_c_start=CPT - 76000, word2_change_s=200.0,
                       expect={"epc": "enabled", "instrumentation_suspect": True}),
}


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    which, out = sys.argv[1], sys.argv[2]
    names = list(CASES) if which == "all" else which.split(",")
    for n in names:
        g = Gen(n, CASES[n])
        exp = g.write_case(out)
        print("%s: %s" % (n, json.dumps(exp, sort_keys=True)))


if __name__ == "__main__":
    main()
