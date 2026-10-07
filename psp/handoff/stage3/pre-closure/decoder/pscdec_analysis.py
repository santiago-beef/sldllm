"""pscdec_analysis.py - analysis layer of the PSC decoder (DESIGN.md rev 7: rev 6 + section 17).

10.1 build consistency, 10.3 link expansion, 10.4 stats, 10.5 time
reconstruction, 10.6 EPC/register maps, 10.7 steps 1-8 (template, per-poll
simulation, onset candidates with the 6.3 placements, classification by every
row of section 6 / 6.1, H10 conclusion, harm-rate comparison, no-death
inference).  Thresholds are module constants, fixed before the run (G3 R6).
"""

import bisect
import math
import re
import zlib
from collections import Counter, defaultdict

import psc_format as F
import psc_maps


def nwset(r):
    """The nwords set of a record (1.2 offset 22, 10.3, section 17 R-1):
    {7, 8} for a record flagged nw7or8, else {nwords}."""
    if r.get("nw7or8"):
        return (7, 8)
    return (r["nwords"],)

CPT = F.CPT
TPS = F.HZ                          # ticks per second
WD = F.WD_CYCLE
# ---- pre-registered thresholds (10.7 step 5: printed in the REPORT)
PERSIST_FRAC = 0.90                 # "persistent" = >= 90 % of post-onset records ...
PERSIST_S = 10                      # ... over >= 10 s (section 6 preamble)
TEMPLATE_MIN_S = 10                 # 10.7 step 2
TEMPLATE_MIN_POLLS = 150
TEMPLATE_GUARD_S = 5                # window ends 5 s before the earliest of O1, O2, O4, O5
DELIVERY_GAP_S = 10                 # O2: none for >= 10 s after
STOP_GAP_S = 10                     # O4, thread-stopped shapes
NEAR_POLLS = 2                      # +- 2 polls
NEAR_TICKS = 2                      # +- 2 ticks (N8)
NEAR_S = 2                          # +- 2 s (H10b)
NEAR_CYCLES = 2                     # +- 2 watchdog cycles (WB, UL7)
S_NEAR_MS = 100                     # S records within +- 100 ms of a candidate
RAW_BEFORE_S, RAW_AFTER_S = 30, 60  # H0 raw windows
DUMP_S = 30                         # +- 30 s raw dump per candidate
D_WINDOW_S = 70                     # D1..D7 span after the D0 stopwatch time (RUNBOOK D)
LED_BITS = 0xC0                     # LED bits 0x40/0x80 (row H10)
H4_SUFF_N = 30                      # 10.7 step 8
H4_SUFF_P = 0.1
FISHER_P, FISHER_MIN_HL = 0.01, 3   # 10.7 step 7

KEY_HOLD = 0x00002000
KEY_SELECT, KEY_LTRG, KEY_RTRG = 0x00000100, 0x00000200, 0x00000400
KEY_UP, KEY_RT, KEY_DN, KEY_LT = 0x1, 0x2, 0x4, 0x8
KEY_MOUSE = 0x00800000

BUSY_CODES = (0x80, 0x81)
N3_CODES = (0x83, 0x86)


def fine(tick, c):
    return tick * CPT + c


def sec(tick):
    return tick / float(TPS)


def hexrx(rx):
    return " ".join("%02x" % b for b in rx)


def checksum_ok(rx):
    """syscon.c:226-246 recomputed: True/False, None if rx[1] >= 16 (the
    kernel's checksum read past the 16-byte buffer; not recomputable)."""
    cnt = rx[1]
    if cnt < 3:
        return False
    if cnt >= 16:
        return None
    return ((sum(rx[:cnt]) & 0xFF) ^ 0xFF) == rx[cnt]


def key_of(rec):
    rx = rec["rx"]
    return rx[3] | rx[4] << 8 | rx[5] << 16 | rx[6] << 24


def mouse_rel(v):
    """joypad_psp.c:661-693 psp_mouse_convert_to_rel."""
    n = (v >> 4) & 0xF
    return {0: -16, 1: -4, 2: -2, 3: -2, 4: -1, 5: -1, 0xA: 1, 0xB: 1, 0xC: 2, 0xD: 2,
            0xE: 4, 0xF: 16}.get(n, 0)


def fisher_one_sided(hL, nL, hN, nN):
    """P(X >= hL) for the hypergeometric of the 2x2 table (harm more frequent in L)."""
    tot_h, tot = hL + hN, nL + nN
    if tot == 0 or tot_h == 0:
        return 1.0

    def comb(n, k):
        return math.comb(n, k) if 0 <= k <= n else 0
    den = comb(tot, nL)
    p = 0
    for x in range(hL, min(nL, tot_h) + 1):
        p += comb(tot_h, x) * comb(tot - tot_h, nL - x)
    return p / den if den else 1.0


def ub95(n):
    return 1.0 if n == 0 else 1 - 0.05 ** (1.0 / n)


def _lines(path):
    with open(path) as f:
        return f.read().splitlines()


# ====================================================================== build files
class BuildInfo(object):
    """System.map, epcmap.txt, regmap.txt, build_id (10.1, 10.6).  The maps are
    read with the grammar of psc_maps.py, the module handoff/impl/mkmaps.py
    writes them with (G2 attempt 1 F3); a map in another syntax is an error
    that refuses the EPC analysis (10.1), never a silent partial read."""

    def __init__(self):
        self.sysmap = {}
        self.epc = []           # sorted (start, end, label)
        self.reg = {}           # label -> var -> [psc_maps.RegRow]
        self.build_id = None
        self.image_sha256 = None
        self.notes = []
        self.errors = []

    @classmethod
    def load(cls, system_map=None, epcmap=None, regmap=None, build_id=None, image_sha256=None):
        b = cls()
        if system_map:
            for line in _lines(system_map):
                p = line.split()
                if len(p) >= 3:
                    try:
                        b.sysmap[p[2]] = int(p[0], 16)
                    except ValueError:
                        pass
        if epcmap:
            try:
                with open(epcmap) as f:
                    b.epc = psc_maps.parse_epcmap_text(f.read(), epcmap)
            except psc_maps.MapError as e:
                b.errors.append(str(e))
        if regmap:
            try:
                with open(regmap) as f:
                    b.reg = psc_maps.parse_regmap_text(f.read(), regmap)
            except psc_maps.MapError as e:
                b.errors.append(str(e))
        if build_id is not None:
            b.build_id = build_id
        b.image_sha256 = image_sha256
        return b

    def label(self, addr):
        if not self.epc or addr is None:
            return None
        i = bisect.bisect_right(self.epc, (addr, 0xFFFFFFFF, "~")) - 1
        if i >= 0:
            s, e, lab = self.epc[i]
            if s <= addr < e:
                return lab
        return None

    def regval(self, label, var, epc, regs):
        """(value, row) of `var` at a W record's EPC (psc_maps.value)."""
        return psc_maps.value(self.reg, label, var, epc, regs)


STEP_PPOINT = {}
for _s in (0, 1, 2, 3, 4, 21, 22, 23):      # S0 = retry: (2.1 A2 store), P0 (G2 F3)
    STEP_PPOINT["S%d" % _s] = "P0"
for _l in ("ENTRY", "EXIT", "REC"):
    STEP_PPOINT[_l] = "P0"
for _s in range(5, 11):
    STEP_PPOINT["S%d" % _s] = "P1"
STEP_PPOINT["S11"] = "P2"
STEP_PPOINT["S12"] = STEP_PPOINT["S13"] = "P3"
STEP_PPOINT["S14"] = "P4|P5a"
STEP_PPOINT["S15"] = "P5b"
for _s in (16, 17, 18):
    STEP_PPOINT["S%d" % _s] = "P6"
STEP_PPOINT["S19"] = STEP_PPOINT["S20"] = "P7"


def kj_text(st):
    """' k=.. j=.. pending=..' for a w_step result (10.6), '' if none."""
    t = ""
    if st.get("k") is not None:
        t += " k=%s" % st["k"]
    if st.get("j") is not None:
        t += " j=%s" % st["j"]
    if st.get("pending") is not None:
        t += " pending=%s" % st["pending"]
    return t


def step_num(label):
    m = re.match(r'^S(\d+)$', label or "")
    return int(m.group(1)) if m else None


# ====================================================================== template
class Template(object):
    """10.7 step 2: per command nwords, rx[1], rx[2], ranges of ack_polls,
    drain, duration; analog jitter; gpio_in/spi_* distributions; LED ORs.
    Or, without a healthy window, the code expectations ('fallback')."""

    def __init__(self):
        self.ok = False
        self.reason = ""
        self.cmd = {}           # cmd -> dict
        self.led_set_or = 0
        self.led_clr_or = 0
        self.led_or = 0
        self.window = None
        self.npolls = 0
        self.baseline = None    # fallback H8 baseline (WB, boot M, pre-onset WT)

    def rx2(self, cmd):
        """(value, literal?) expected rx[2] for a reply to `cmd` (N-4, R22)."""
        if self.ok and cmd in self.cmd and self.cmd[cmd].get("rx2") is not None:
            return self.cmd[cmd]["rx2"], False
        return cmd, True

    def nwords(self, cmd, rx):
        """Expected word counts (a tuple) for a reply to `cmd`, or None: the
        template's set, else the code expectation "exact length from rx[1]".
        A record matches when its own set (nwset) meets it (10.7, R-1)."""
        if self.ok and cmd in self.cmd and self.cmd[cmd].get("nwords") is not None:
            return self.cmd[cmd]["nwords"]
        return ((rx[1] + 2) // 2,) if 3 <= rx[1] < 16 else None

    def own_valid(self, r):
        """The command received its own valid reply (10.7 step 5, step 7)."""
        rx = r["rx"]
        if r["ret"] <= 0 or rx[0] != r["ret"] or checksum_ok(rx) is not True:
            return False
        exp, _lit = self.rx2(r["cmd"])
        if rx[2] != exp:
            return False
        nw = self.nwords(r["cmd"], rx)
        if nw is not None and not set(nw) & set(nwset(r)):
            return False
        if self.ok and r["cmd"] in self.cmd and self.cmd[r["cmd"]].get("rx1") is not None \
                and rx[1] != self.cmd[r["cmd"]]["rx1"]:
            return False
        return True

    def outside(self, r):
        """Record outside the template (O3, H8 helper)."""
        if not self.ok:
            return not self.own_valid(r)
        if not self.own_valid(r):
            return True
        t = self.cmd.get(r["cmd"])
        if t is None:
            return True
        dur = r["_t1"] - r["_t0"]
        if t["dur"] and dur > 2 * t["dur"][1] + 2000:
            return True
        return False


def learn_template(recs, polls, srecs, t_lo, t_hi):
    T = Template()
    T.window = (t_lo, t_hi)
    inwin = [r for r in recs if t_lo <= r["_t0"] < t_hi]
    pw = [p for p in polls if t_lo <= p["_t0"] < t_hi]
    T.npolls = len(pw)
    span_s = (t_hi - t_lo) / float(CPT * TPS) if t_hi > t_lo else 0
    if span_s < TEMPLATE_MIN_S or len(pw) < TEMPLATE_MIN_POLLS:
        T.reason = "window %.1f s, %d polls (< %d s or < %d polls)" % (span_s, len(pw), TEMPLATE_MIN_S,
                                                                      TEMPLATE_MIN_POLLS)
        return T
    by = defaultdict(list)
    for r in inwin:
        if r["ret"] > 0 and checksum_ok(r["rx"]) is True and r["rx"][0] == r["ret"]:
            by[r["cmd"]].append(r)
    for cmd, rs in by.items():
        if len(rs) < 5:
            continue
        mode = lambda xs: Counter(xs).most_common(1)[0][0]
        nwm = mode([r["nwords"] for r in rs])
        nflag = sum(1 for r in rs if r.get("nw7or8"))
        d = {"n": len(rs),
             # R-1: a template value 7 learned from flagged records is {7, 8}
             "nwords": (7, 8) if nwm == 7 and any(r.get("nw7or8") for r in rs if r["nwords"] == 7) else (nwm,),
             "nw7or8": nflag,
             "rx1": mode([r["rx"][1] for r in rs]),
             "rx2": mode([r["rx"][2] for r in rs]),
             "ack": (min(r["ack_polls"] for r in rs), max(r["ack_polls"] for r in rs)),
             "drain": (min(r["drain"] for r in rs), max(r["drain"] for r in rs)),
             "dur": (min(r["_t1"] - r["_t0"] for r in rs), max(r["_t1"] - r["_t0"] for r in rs)),
             "gpio_in": Counter(r["gpio_in"] for r in rs),
             "spi_st9": Counter(r["spi_st9"] for r in rs),
             "spi_sttx": Counter(r["spi_sttx"] for r in rs),
             "drain_last": Counter(r["drain_last"] for r in rs)}
        if cmd == 0x08:
            d["x"] = (min(r["rx"][7] for r in rs), max(r["rx"][7] for r in rs))
            d["y"] = (min(r["rx"][8] for r in rs), max(r["rx"][8] for r in rs))
        T.cmd[cmd] = d
        T.led_or |= 0
    for r in inwin:
        T.led_or |= r.get("led_or", 0)
    for s in srecs:
        if t_lo <= s["_t0"] < t_hi:
            T.led_set_or |= s["rd_set_or"]
            T.led_clr_or |= s["rd_clr_or"]
    T.ok = 0x08 in T.cmd
    if not T.ok:
        T.reason = "no healthy 0x08 replies in the window"
    return T


# ====================================================================== model
class Model(object):
    def __init__(self, col, build, times=None, no_template=False):
        self.col, self.build = col, build
        self.times = times or {}
        self.no_template = no_template
        self.notes = []
        self.checks = []                # 10.5 consistency exceptions
        self.flags = []                 # global flags (rx2 literal, no C0 reference, ...)
        R = col.records
        self.P = self._sc(sorted(R[F.RING_P].values(), key=lambda r: r["seq"]), "P")
        self.M = self._sc(sorted(R[F.RING_M].values(), key=lambda r: r["seq"]), "M")
        self.W = self._sc(sorted(R[F.RING_W].values(), key=lambda r: r["seq"]), "W")
        self.POLL = sorted(R[F.RING_POLL].values(), key=lambda r: r["seq"])
        self.S = sorted(R[F.RING_S].values(), key=lambda r: r["seq"])
        for p in self.POLL:
            p["_t0"] = fine(p["tick_start"], p["c_start"])
            p["_t1"] = fine(p["tick_start"] + p["body_ticks"], p["c_end"])
            p["_tick"] = p["tick_start"]
        for s in self.S:
            s["_t0"] = fine(s["tick_on"], s["c_on"])
            s["_t1"] = fine(s["tick_on"] + s["dtick"], s["c_off"])
            s["_tick"] = s["tick_on"]
        self.Pseq = {r["seq"]: r for r in self.P}
        self.Wseq = {r["seq"]: r for r in self.W}
        self.POLLseq = {r["seq"]: r for r in self.POLL}
        self.P08 = [r for r in self.P if r["cmd"] == 0x08]
        self.P33 = [r for r in self.P if r["cmd"] == 0x33]
        self.WT = [w for w in self.W if (w["ctx"] & 3) == F.ORIGIN_WT]
        self.stats = col.stats
        self.uhb = col.uhb
        self.P_t0 = [r["_t0"] for r in self.P]
        self.POLL_t0 = [p["_t0"] for p in self.POLL]
        self.t_end = self._t_end()
        self.epc_ok, self.epc_reason = self._build_check()
        self.offset_ticks = self._uptime_offset()
        self._timecheck()
        self._links()
        self._gaps()

    # ---------------------------------------------------------------- 10.5
    def _sc(self, recs, ring):
        for r in recs:
            r["_t0"] = fine(r["tick_in"], r["c_in"])
            r["_tick"] = r["tick_in"]
            r["_tick_out"] = r["tick_in"] + r["dtick"]
            r["_t1"] = fine(r["_tick_out"], r["c_out"])
            r["_rn"] = ring
        return recs

    def _t_end(self):
        ts = []
        for xs in (self.P, self.W, self.POLL, self.S, self.M):
            if xs:
                ts.append(max(x["_t0"] for x in xs))
        if self.stats:
            ts.append(fine(self.stats[-1]["now_tick"], self.stats[-1]["now_count"]))
        if self.uhb:
            ts.append(fine(self.uhb[-1]["stats_now_tick"], 0))
        return max(ts) if ts else 0

    def _timecheck(self):
        for w in self.WT:
            if w["tick_in"] % WD:
                self.checks.append("WT W seq %d at tick %d is not on a 1250 boundary" % (w["seq"], w["tick_in"]))
        wt_ticks = sorted(w["tick_in"] for w in self.WT)
        for r in self.P + self.M:
            if r["c_in"] > CPT or r["c_out"] > CPT:
                r.setdefault("_notes", []).append("long tick")
            if r["dtick"] > 0:
                k = bisect.bisect_left(wt_ticks, r["tick_in"] + 1)
                if k < len(wt_ticks) and wt_ticks[k] <= r["_tick_out"] and r["wn"] == 0:
                    self.checks.append("%s seq %d crosses WT tick %d with wn = 0" %
                                       (r["_rn"], r["seq"], wt_ticks[k]))
        for a, b in zip(wt_ticks, wt_ticks[1:]):
            if b - a != WD:
                self.checks.append("consecutive WT ticks %d, %d differ by %d (W records missing or late)"
                                   % (a, b, b - a))

    def _build_check(self):
        """10.1: stats words 20-22 against System.map, word 2 against build_id
        (R-4: build_id.txt of the packaged build). The first stats block is
        checked, the one KRN verified at the worker's start; a later block
        whose word 2 differs is reported and makes onsets from its tick
        instrumentation-suspect (G1 red team K4, KR2), not a whole-run refusal.
        Each FILEHDR's /proc/version CRC-32 is checked against word 2 (R-4)."""
        st = self.stats[0] if self.stats else (self.col.chunks and None)
        self.word2_change = None
        self.build.notes = [n for n in self.build.notes if not n.startswith("10.1")]
        if not st:
            return False, "no STATS chunk"
        for s in self.stats[1:]:
            if s["build_id"] != st["build_id"]:
                self.word2_change = s["now_tick"]
                self.build.notes.append("10.1: stats word 2 changed from 0x%08x to 0x%08x at tick %d: "
                                        "instrumentation-suspect from that tick" % (st["build_id"], s["build_id"],
                                                                                 s["now_tick"]))
                break
        fhs = [(sr.name, sr.fh) for sr in self.col.sources if getattr(sr, "fh", None) and not sr.ignored]
        fhs += [("image @%d" % o, fh) for (o, fh) in getattr(self.col, "raw_groups", [])]
        for name, fh in fhs:
            vr = fh.get("version_raw")
            if vr is None:
                continue
            c = zlib.crc32(vr) & 0xFFFFFFFF
            w2 = fh["stats"]["build_id"] if fh.get("stats") else None
            if w2 is not None and c != w2:
                self.build.notes.append("10.1: %s FILEHDR /proc/version CRC-32 0x%08x != its stats word 2 0x%08x"
                                        % (name, c, w2))
            elif c != st["build_id"]:
                self.build.notes.append("10.1: %s FILEHDR /proc/version CRC-32 0x%08x != stats word 2 0x%08x"
                                        % (name, c, st["build_id"]))
        why = list(self.build.errors)
        if not self.build.sysmap:
            why.append("no System.map")
        else:
            for word, name in (("addr_syscon_cmd", "Syscon_cmd"), ("addr_psc_sc_exit", "psc_sc_exit"),
                               ("addr_getctrl2", "_pspSysconGetCtrl2")):
                if self.build.sysmap.get(name) != st[word]:
                    why.append("stats %s = 0x%08x, System.map %s = %s" %
                               (word, st[word], name, hex(self.build.sysmap[name]) if name in self.build.sysmap
                                else "missing"))
        if self.build.build_id is None:
            why.append("build_id of the build not supplied (BUILD/build_id.txt of the packaged build, 10.1)")
        elif self.build.build_id != st["build_id"]:
            why.append("stats build_id 0x%08x != build 0x%08x" % (st["build_id"], self.build.build_id))
        if not self.build.epc:
            why.append("no epcmap.txt")
        return (not why), "; ".join(why)

    def _uptime_offset(self):
        """stopwatch seconds - offset = uptime; uptime -> tick via jiffies (10.5)."""
        self.j_off = 0
        if self.stats:
            s = self.stats[-1]
            self.j_off = s["now_tick"] - ((s["now_jiffies"] - s["initial_jiffies"]) & 0xFFFFFFFF)
        t = self.times
        if "uptime_offset" in t:
            return t["uptime_offset"]
        if "selftest_pass" in t:
            for u in self.uhb:
                if (u["flags"] >> 1) & 0xFF == 0xFF:
                    return t["selftest_pass"] - u["uptime_cs"] / 100.0
        return None

    def sw_tick(self, key):
        """Operator stopwatch time -> kernel tick (None if unknown)."""
        if key not in self.times or self.offset_ticks is None:
            return None
        up = self.times[key] - self.offset_ticks
        return int(round(up * TPS)) + self.j_off

    # ---------------------------------------------------------------- 10.3 links
    @staticmethod
    def _expand(lo, ref):
        return ref + ((lo - ref + 0x8000) & 0xFFFF) - 0x8000

    def _links(self):
        self.link_flags = Counter()
        # POLL.sc_seq_lo -> P seq of this poll's 0x33 record
        for p in self.POLL:
            k = bisect.bisect_left(self.P_t0, p["_t0"])
            ref = self.P[k]["seq"] if k < len(self.P) else (self.P[-1]["seq"] + 1 if self.P else 0)
            s = self._expand(p["sc_seq_lo"], ref)
            r33 = self.Pseq.get(s)
            p["_p33"], p["_p08"] = None, None
            if r33 is not None and r33["cmd"] == 0x33:
                p["_p33"] = r33
                r08 = self.Pseq.get(s + 1)
                if r08 is not None and r08["cmd"] == 0x08:
                    p["_p08"] = r08
            else:
                # (r4, A4 IF6) paired by (tick, Count) instead, flagged
                cand = [r for r in self.P[k:k + 4] if r["_t0"] <= p["_t1"] + CPT]
                for r in cand:
                    if r["cmd"] == 0x33 and p["_p33"] is None:
                        p["_p33"] = r
                    elif r["cmd"] == 0x08 and p["_p08"] is None:
                        p["_p08"] = r
                if p["_p33"] or p["_p08"]:
                    p["_link_by_time"] = True
                    self.link_flags["POLL->P by time"] += 1
            if p["_p08"] is not None:
                p["_p08"]["_poll"] = p
        # SC.w_head_lo -> the Nops of this command (w_head - wn .. w_head - 1)
        w_t0 = [w["_t0"] for w in self.W]
        for r in self.P + self.M:
            if r["wn"] == 0:
                r["_nops"] = []
                continue
            k = bisect.bisect_right(w_t0, r["_t1"])
            ref = (self.W[k - 1]["seq"] + 1) if k > 0 else 0
            head = self._expand(r["w_head_lo"], ref)
            nops = [self.Wseq.get(s) for s in range(head - r["wn"], head)]
            if all(n is not None for n in nops):
                r["_nops"] = nops
            else:
                r["_nops"] = [w for w in self.WT if r["_t0"] <= w["_t0"] <= r["_t1"]]
                r["_link_by_time"] = True
                self.link_flags["SC->W by time"] += 1
        # S.p_head_lo -> P head at entry
        for s in self.S:
            k = bisect.bisect_right(self.P_t0, s["_t0"])
            ref = (self.P[k - 1]["seq"] + 1) if k > 0 else 0
            s["_p_head"] = self._expand(s["p_head_lo"], ref)

    def _gaps(self):
        self.gaps = []
        for ring, recs in ((F.RING_P, self.P), (F.RING_POLL, self.POLL), (F.RING_W, self.W),
                           (F.RING_S, self.S), (F.RING_M, self.M)):
            seqs = [r["seq"] for r in recs]
            for a, b in zip(seqs, seqs[1:]):
                if b != a + 1:
                    self.gaps.append((F.RING_NAMES[ring], a + 1, b - 1, b - a - 1))
            if ring != F.RING_M and seqs and seqs[0] != 0:
                self.gaps.append((F.RING_NAMES[ring], 0, seqs[0] - 1, seqs[0]))

    # ---------------------------------------------------------------- helpers
    def post(self, recs, t_lo, t_hi=None):
        return [r for r in recs if r["_t0"] >= t_lo and (t_hi is None or r["_t0"] < t_hi)]

    def persistent(self, recs, pred):
        """(match, k, n, span_s): >= 90 % of `recs` satisfy pred over >= 10 s."""
        n = len(recs)
        if n == 0:
            return False, 0, 0, 0.0
        k = sum(1 for r in recs if pred(r))
        span = (recs[-1]["_t0"] - recs[0]["_t0"]) / float(CPT * TPS)
        return (k >= PERSIST_FRAC * n and span >= PERSIST_S), k, n, span

    def stats_between(self, t_lo, t_hi=None):
        return [s for s in self.stats if fine(s["now_tick"], s["now_count"]) >= t_lo and
                (t_hi is None or fine(s["now_tick"], s["now_count"]) < t_hi)]

    def stat_delta(self, field, t_lo, t_hi=None):
        rows = self.stats_between(t_lo, t_hi)
        if len(rows) < 2:
            return None
        return (rows[-1][field] - rows[0][field]) & 0xFFFFFFFF

    def label_of(self, addr):
        if not self.epc_ok:
            return None
        return self.build.label(addr)

    # ---------------------------------------------------------------- W step (10.6)
    def w_step(self, w):
        """Step and P-point of the thread command a WT record interrupted."""
        e = w["ext"]
        ef = e["ext_flags"]
        out = {"src": None, "epc": None, "label": None, "ppoint": None, "bd": False, "k": None, "j": None,
               "nested": bool(ef & F.EXT_F_NESTED)}
        if (ef & F.EXT_F_JP_TASK) and not (ef & F.EXT_F_NESTED) and (ef & F.EXT_F_REGS_VALID):
            out.update(src="epc", epc=e["epc"], bd=bool(e["cause"] & 0x80000000))
            regs = e["r"]
        elif ef & F.EXT_F_LC_VALID:
            out.update(src="lc_epc", epc=e["lc_epc"], bd=bool(e["lc_cause"] & 0x80000000))
            regs = e["lc_r"]
        else:
            return out
        if not self.epc_ok:
            out["ppoint"] = "unknown (EPC analysis refused: %s)" % self.epc_reason
            return out
        lab = self.build.label(out["epc"])
        out["label"] = lab
        pp = STEP_PPOINT.get(lab)
        if pp == "P4|P5a":
            # row H4: W's own ack_polls = 0 with drain > 0 and a reply-shaped
            # drain_last = P5a; ack_polls > 0 with drain = 0 = P4
            if w["ack_polls"] == 0 and w["drain"] > 0 and w["drain_last"] not in (0, 0xFFFF):
                pp = "P5a"
            elif w["ack_polls"] > 0 and w["drain"] == 0:
                pp = "P4"
            else:
                pp = "P4 or P5a"
        out["ppoint"] = pp
        # 10.6 with the regmap's offsets and EPC sub-ranges (psc_maps.py):
        # P2 k = i / 2 (bytes pushed), P6 j = i / 2 (bytes popped) and
        # `pending` (status loaded, data not yet read); ptr is cross-checked
        epc = out["epc"]
        if pp in ("P2", "P6"):
            i, row = self.build.regval(lab, "i", epc, regs)
            if i is not None:
                out["k" if pp == "P2" else "j"] = i // 2
            elif row is None:
                out["k" if pp == "P2" else "j"] = "i not in regmap for %s" % lab
            p, _r = self.build.regval(lab, "ptr", epc, regs)
            b, _r = self.build.regval(lab, "tx_buf" if pp == "P2" else "rx_buf", epc, regs)
            if p is not None and b is not None and i is not None and ((p - b) & 0xFFFFFFFF) != i:
                out["map_note"] = ("ptr - %s = %d but i = %d at %08x: regmap and record disagree"
                                   % ("tx_buf" if pp == "P2" else "rx_buf", (p - b) & 0xFFFFFFFF, i, epc))
        if pp == "P6":
            pv, _r = self.build.regval(lab, "pending", epc, regs)
            out["pending"] = pv
        return out


# ====================================================================== the analysis
class Analysis(object):
    def __init__(self, model):
        self.m = model
        self.result = {}

    # ---------------------------------------------------------------- step 3
    def simulate_polls(self, tmpl):
        """10.7 step 3: recompute the branch, simulate lastKeys, mouseMode and
        the mouse deltas (joypad_psp.c:474-496, :505-527, :593-658) against
        pi_flags and mouse_flags; report every mouseMode toggle with its frame."""
        m = self.m
        last_keys, mouse_mode, s_keys = 0, False, 0
        btn = (False, False, False)
        mism = []
        toggles = []
        for p in m.POLL:
            r08 = p.get("_p08")
            if r08 is None:
                continue
            ret = r08["ret"]
            key = key_of(r08)
            keys = (~key) & 0xFFFFFFFF
            if ret < 0:
                br = F.RI_R3
            elif keys & KEY_HOLD:
                br = F.RI_R4
            else:
                br = F.RI_R5
            p["_branch"] = br
            if br != p["ri_branch"]:
                mism.append((p["seq"], "branch %d recomputed, ri_branch %d" % (br, p["ri_branch"])))
            if p["ri_branch"] != F.RI_R5:
                continue
            x, y = r08["rx"][7], r08["rx"][8]
            kk = keys | ((x & 0xF0) << 20) | ((y & 0xF0) << 24)
            pf = p["pi_flags"]
            if kk == last_keys:
                exp_called, exp_dedupe = True, True
            else:
                exp_called, exp_dedupe = True, False
                last_keys = kk
                if kk & KEY_SELECT:
                    mouse_mode = not mouse_mode
                    toggles.append((p["seq"], p["_tick"], mouse_mode, hexrx(r08["rx"]), r08["seq"]))
                if bool(pf & F.PI_F_MOUSEMODE) != mouse_mode:
                    mism.append((p["seq"], "mouseMode simulated %d, pi_flags b4 %d (resynced)"
                                 % (mouse_mode, bool(pf & F.PI_F_MOUSEMODE))))
                    mouse_mode = bool(pf & F.PI_F_MOUSEMODE)
                s_keys = kk | (KEY_MOUSE if mouse_mode else 0)
            if bool(pf & F.PI_F_DEDUPE) != exp_dedupe:
                mism.append((p["seq"], "dedupe simulated %d, pi_flags b1 %d" % (exp_dedupe,
                                                                              bool(pf & F.PI_F_DEDUPE))))
            mf = p["mouse_flags"]
            if s_keys & KEY_MOUSE:
                dx, dy = mouse_rel(x), mouse_rel(y)
                left = bool(keys & KEY_LTRG) and not (keys & KEY_RTRG)
                right = bool(keys & KEY_RTRG) and not (keys & KEY_LTRG)
                mid = bool(keys & KEY_LTRG) and bool(keys & KEY_RTRG)
                dx += (-2 if keys & KEY_LT else 0) + (2 if keys & KEY_RT else 0)
                dy += (-2 if keys & KEY_UP else 0) + (2 if keys & KEY_DN else 0)
                if not (mf & F.MOUSE_F_CALLED):
                    mism.append((p["seq"], "mouse call expected (mouse mode), mouse_flags b0 = 0"))
                elif dx == 0 and dy == 0 and (left, mid, right) == btn:
                    if not (mf & F.MOUSE_F_NOOP):
                        mism.append((p["seq"], "mouse no-op expected"))
                else:
                    btn = (left, mid, right)
                    if not (mf & F.MOUSE_F_REPORTED) or p["dx"] != max(-128, min(127, dx)) \
                            or p["dy"] != max(-128, min(127, dy)):
                        mism.append((p["seq"], "mouse report dx %d dy %d expected, recorded flags 0x%02x "
                                     "dx %d dy %d" % (dx, dy, mf, p["dx"], p["dy"])))
            elif mf & F.MOUSE_F_CALLED:
                mism.append((p["seq"], "mouse called outside mouse mode"))
        self.sim_mismatch = mism
        self.toggles = toggles

    # ---------------------------------------------------------------- step 4
    def onset_candidates(self, tmpl=None):
        m = self.m
        c = []
        # O1 last raw change of key
        last = None
        o1 = None
        for r in m.P08:
            k = key_of(r)
            if last is not None and k != last:
                o1 = r
            last = k
        if o1 is not None:
            c.append(("O1", o1["_t0"], "last raw change of key (P08 seq %d)" % o1["seq"]))
        # O2 last POLL with a delivery, none for >= 10 s after
        deliv = [p for p in m.POLL if p["push_ok"] > 0 or p["mouse_flags"] & F.MOUSE_F_REPORTED]
        if deliv:
            lp = deliv[-1]
            if m.t_end - lp["_t0"] >= DELIVERY_GAP_S * TPS * CPT:
                c.append(("O2", lp["_t0"] + 1, "last POLL with a delivery (POLL seq %d), none for %.1f s after"
                          % (lp["seq"], (m.t_end - lp["_t0"]) / float(CPT * TPS))))
        elif m.POLL:
            c.append(("O2", m.POLL[0]["_t0"], "no POLL with a delivery in the whole run"))
        # O3 start of the longest trailing run outside the template
        if tmpl is not None and tmpl.ok and m.P:
            out_flags = [tmpl.outside(r) for r in m.P]
            n_out, best = 0, None
            for i in range(len(m.P) - 1, -1, -1):
                n_out += out_flags[i]
                n = len(m.P) - i
                if out_flags[i] and n_out >= PERSIST_FRAC * n:
                    best = i
            if best is not None and (m.P[-1]["_t0"] - m.P[best]["_t0"]) >= PERSIST_S * TPS * CPT:
                c.append(("O3", m.P[best]["_t0"], "start of the longest trailing run outside the template "
                          "(P seq %d, %d records)" % (m.P[best]["seq"], len(m.P) - best)))
        # O4 last jp_loop increment, if it stops
        if m.POLL and m.t_end - m.POLL[-1]["_t0"] >= STOP_GAP_S * TPS * CPT:
            c.append(("O4", m.POLL[-1]["_t0"] + 1, "last thread loop (POLL seq %d), %.1f s before the end"
                      % (m.POLL[-1]["seq"], (m.t_end - m.POLL[-1]["_t0"]) / float(CPT * TPS))))
        # O5 last rise of fop_read_ret and of IN
        for name, rows, field, tf in (("O5a", m.stats, "fop_read_ret", lambda s: fine(s["now_tick"], s["now_count"])),
                                      ("O5b", m.uhb, "mouse_press_total", lambda u: fine(u["stats_now_tick"], 0))):
            lr = None
            for a, b in zip(rows, rows[1:]):
                if b[field] != a[field]:
                    lr = b
            if lr is not None and m.t_end - tf(lr) >= DELIVERY_GAP_S * TPS * CPT:
                c.append((name, tf(lr), "last rise of %s (tick %d)" % (field, tf(lr) // CPT)))
        c.sort(key=lambda x: x[1])
        return c

    # ---------------------------------------------------------------- 6.3
    def placements(self, t_on, tmpl):
        """6.3: last successful thread command, first failed one, nearest Nop:
        before / across / after the same 1250k boundary."""
        m = self.m
        lo = t_on - NEAR_S * TPS * CPT
        first_failed = None
        for r in m.P:
            if r["_t0"] >= lo and not tmpl.own_valid(r):
                first_failed = r
                break
        anchor = first_failed["_t0"] if first_failed else t_on
        last_ok = None
        for r in m.P:
            if r["_t0"] >= anchor:
                break
            if tmpl.own_valid(r):
                last_ok = r
        nop = None
        if m.WT:
            nop = min(m.WT, key=lambda w: abs(w["_t0"] - anchor))
        res = {"last_ok": last_ok, "first_failed": first_failed, "nop": nop}

        def place(r):
            if r is None or nop is None:
                return None
            B = nop["tick_in"]
            if r["_tick_out"] < B:
                return "before"
            if r["tick_in"] < B <= r["_tick_out"]:
                return "across (wn %d)" % r["wn"]
            if r["tick_in"] == B and r["c_in"] < nop["c_out"]:
                return "after? (starts in tick %d before the Nop's c_out: inconsistent)" % B
            return "after"
        res["place_last_ok"] = place(last_ok)
        res["place_first_failed"] = place(first_failed)
        res["boundary"] = nop["tick_in"] if nop else None
        return res

    # ---------------------------------------------------------------- operator windows
    def d_window(self):
        m = self.m
        d0 = m.sw_tick("d0_start")
        if d0 is None:
            return None
        return fine(d0, 0), fine(d0 + D_WINDOW_S * TPS, 0)

    def c0_window(self):
        m = self.m
        a, b = m.sw_tick("c0_start"), m.sw_tick("c0_end")
        if a is None or b is None:
            return None
        return fine(a, 0), fine(b, 0)

    def c0_changes(self):
        """Which script bits changed in the C0 reference (row H6/N11)."""
        w = self.c0_window()
        if w is None:
            return None
        recs = [r for r in self.m.P08 if w[0] <= r["_t0"] < w[1] and r["ret"] > 0]
        out = Counter()
        prev = None
        for r in recs:
            rx = r["rx"]
            if prev is not None:
                if (rx[3] ^ prev[3]) & 0x10: out["TRIANGLE rx[3]b4"] += 1
                if (rx[3] ^ prev[3]) & 0x02: out["RIGHT rx[3]b1"] += 1
                if (rx[4] ^ prev[4]) & 0x02: out["LTRG rx[4]b1"] += 1
                if (rx[4] ^ prev[4]) & 0x20: out["HOLD rx[4]b5"] += 1
                if (rx[5] ^ prev[5]) & 0x01: out["VOL_UP rx[5]b0"] += 1
                if rx[7] != prev[7] or rx[8] != prev[8]: out["stick rx[7]/rx[8]"] += 1
            prev = rx
        return out

    # ---------------------------------------------------------------- step 5
    def classify(self, cand, tmpl):
        """Every section 6 / 6.1 row for one onset candidate.  Returns a dict
        with the triple (trigger, state, H8 flags), the evidence per row and
        the quiet/insufficient verdicts."""
        m = self.m
        name, t_on, why = cand
        res = {"cand": name, "t": t_on, "tick": t_on // CPT, "why": why, "stopped": [], "state": [],
               "triggers": [], "h8": [], "h7": [], "other": [], "evidence": defaultdict(list),
               "notes": [], "quiet": False}
        ev = res["evidence"]
        pl = self.placements(t_on, tmpl)
        res["placements"] = pl
        F_cmd = pl["first_failed"]
        # ---- thread-stopped shapes (H9, N4, N5, N9)
        stop_t = None
        if m.POLL and m.t_end - m.POLL[-1]["_t0"] >= STOP_GAP_S * TPS * CPT and \
                abs(m.POLL[-1]["_t0"] - t_on) <= (STOP_GAP_S * TPS * CPT):
            stop_t = m.POLL[-1]["_t0"]
        if stop_t is not None:
            self._stopped(res, stop_t, tmpl)
        post_p = m.post(m.P, t_on)
        post_08 = [r for r in post_p if r["cmd"] == 0x08]
        post_33 = [r for r in post_p if r["cmd"] == 0x33]
        post_poll = m.post(m.POLL, t_on)
        span = (m.t_end - t_on) / float(CPT * TPS)
        res["post_span_s"] = span
        if span < PERSIST_S and not res["stopped"]:
            res["notes"].append("post-onset span %.1f s < %d s: persistent rows not assessable" % (span, PERSIST_S))
        # ---- persistent states
        if not res["stopped"]:
            self._states(res, tmpl, post_p, post_08, post_33, post_poll, t_on)
        # ---- H8 flags
        self._h8(res, tmpl, post_p, t_on)
        # ---- triggers
        self._triggers(res, tmpl, t_on, F_cmd)
        # R16 residual: a stray store by a kernel-privileged process hitting no guard
        if F_cmd is not None and F_cmd["wn"] == 0 and F_cmd["ms_delta"] == 0 and \
                (F_cmd["ret"] == -4 or (F_cmd["ret"] > 0 and not tmpl.own_valid(F_cmd))) and \
                not [s for s in m.S if s["_t0"] <= F_cmd["_t1"] and s["_t1"] >= F_cmd["_t0"]]:
            res["notes"].append("R16 residual: the first failed command (P seq %d, ret %d) has wn 0, ms_delta 0 "
                                "and no overlapping S record; a stray store by a kernel-privileged process that "
                                "hits no guard would look like this" % (F_cmd["seq"], F_cmd["ret"]))
        # ---- quiet: nothing failed, nothing undelivered, no operator presses expected
        if not res["stopped"] and not res["state"] and not res["h7"]:
            n_valid = sum(1 for r in post_08 if tmpl.own_valid(r))
            changes = self._key_changes(post_08)
            dwin = self.d_window()
            pressing = dwin is not None and dwin[0] >= t_on - TPS * CPT
            healthy_frames = post_08 and n_valid >= PERSIST_FRAC * len(post_08)
            if healthy_frames and changes == 0 and not pressing:
                res["quiet"] = True
                if dwin is None:
                    res["notes"].append("quiet tail: frames healthy and unchanged, no operator times: "
                                        "H6 cannot be told from 'operator not pressing' (row H6)")
            elif healthy_frames and changes > 0:
                # refuted: the key changes after the candidate were delivered and consumed
                deliv = [p for p in post_poll if p["push_ok"] > 0 or p["mouse_flags"] & F.MOUSE_F_REPORTED]
                fop = m.stat_delta("fop_read_ret", t_on)
                ups = [u for u in m.uhb if fine(u["stats_now_tick"], 0) >= t_on]
                inr = (ups[-1]["mouse_press_total"] - ups[0]["mouse_press_total"]) if len(ups) >= 2 else 0
                if deliv and (fop or inr):
                    res["quiet"] = True
                    res["notes"].append("refuted: %d key changes after the candidate, %d deliveries, "
                                        "fop_read_ret +%s, IN +%d: input alive after it" % (changes, len(deliv),
                                                                                          fop, inr))
        return res

    def _key_changes(self, recs):
        n, prev = 0, None
        for r in recs:
            if r["ret"] <= 0:
                continue
            k = bytes(r["rx"][3:9])
            if prev is not None and k != prev:
                n += 1
            prev = k
        return n

    def _stopped(self, res, stop_t, tmpl):
        m = self.m
        ev = res["evidence"]
        rows = m.stats_between(stop_t)
        wpost = [w for w in m.WT if w["_t0"] > stop_t]
        last = rows[-1] if rows else None
        res["notes"].append("thread stopped: last POLL at tick %d; %d W and %d STATS records after"
                            % (stop_t // CPT, len(wpost), len(rows)))
        if not last:
            res["stopped"].append("thread stopped (no STATS after the stop: stage unknown)")
            return
        loops = set(s["jp_loop"] for s in rows) | set(w["ext"]["jp_loop"] for w in wpost)
        stage = last["jp_stage"]
        arg = last["jp_stage_arg"]
        ev["stop"].append("jp_loop values after the stop: %s; jp_stage %d (%s), jp_stage_arg 0x%08x, "
                          "jp_state 0x%x, t_busy %d, t_entry_tick %d"
                          % (sorted(loops)[:4], stage, F.STAGES.get(stage, "?"), arg, last["jp_state"],
                             last["t_busy"], last["t_entry_tick"]))
        # takeover / jp_exit annotation (r4, A4 OE5)
        tk = [e for e in m.col.events if re.match(r'^takeover\b', e[1])]
        if last["jp_exit_tick"]:
            res["notes"].append("jp_exit_tick = %d: the thread exited" % last["jp_exit_tick"])
        for e in tk:
            if e[0] is not None and e[0] <= stop_t // CPT:
                pr = [p for p in m.col.procs if p[0] is not None and p[0] > e[0]]
                if not pr or pr[0][0] > stop_t // CPT:
                    res["notes"].append("stop between takeover at tick %s and the first PROCS after it" % e[0])
        if stage in (11, 9):
            q = last["qfree_queue"]
            same = (stage == 9) or (last["qfree_stage"] == 2 and q == arg)
            if last["qfree_stage"] == 2 or stage == 11:
                txt = ("H9: jp_stage %d (jp_stage_arg 0x%08x), qfree_stage %d qfree_queue 0x%08x qfree_pid %d, "
                       "fop_release %d%s" % (stage, arg, last["qfree_stage"], q, last["qfree_pid"],
                                             last["fop_release"],
                                             "; jp_stage and qfree_stage name the same Q" if same and stage == 11
                                             else ""))
                res["stopped"].append("H9")
                ev["H9"].append(txt)
                pr = [p for p in m.col.procs if p[0] is not None and p[0] >= stop_t // CPT]
                if pr:
                    ev["H9"].append("PROCS after the stop: %s" % ("OSK present" if "\nOSK " in "\n" + pr[-1][1]
                                                                    else "no OSK line (psposk2 gone)"))
        if stage in (7, 8):
            pb = [p for p in m.POLL if p["_t0"] <= stop_t][-3:]
            res["stopped"].append("N4")
            ev["N4"].append("jp_stage %d fixed, console_blanked %d, POLL pi_flags b2 just before: %s"
                            % (stage, last["console_blanked"], [bool(p["pi_flags"] & F.PI_F_BLANKED) for p in pb]))
        if stage in (15, 16):
            labs = [m.label_of(w["ext"]["epc"]) for w in wpost]
            ev["N5"].append("jp_stage %d fixed, jp_loop fixed %s, jp_state %d, W epc labels %s"
                            % (stage, len(loops) == 1, last["jp_state"], sorted(set(str(l) for l in labs))))
            res["stopped"].append("N5")
        if last["t_busy"] & F.TBUSY_P:
            lcs = [(w["ext"]["lc_epc"], w["ext"]["lc_n"]) for w in wpost if w["ext"]["ext_flags"] & F.EXT_F_LC_VALID]
            fixed = len(set(a for a, _ in lcs)) <= 1
            rising = all(b2 >= b1 for (_a1, b1), (_a2, b2) in zip(lcs, lcs[1:]))
            if len(set(s["t_entry_tick"] for s in rows)) == 1:
                res["stopped"].append("N9")
                ev["N9"].append("t_busy b0 set, t_entry_tick fixed at %d; W with b5: %d, lc_epc fixed %s, "
                                "lc_n rising %s" % (last["t_entry_tick"], len(lcs), fixed, rising))
        if not res["stopped"]:
            res["stopped"].append("thread stopped (no H9/N4/N5/N9 signature)")
            res["other"].append("thread stopped, unattributed")

    def _states(self, res, tmpl, post_p, post_08, post_33, post_poll, t_on):
        m = self.m
        ev = res["evidence"]
        allff = lambda r: bytes(r["rx"]) == b"\xff" * 16
        rx2_08, lit08 = tmpl.rx2(0x08)
        if lit08:
            res["notes"].append("rx2 literal: no template, rx[2] compared with the literal command code "
                                "(syscon.h:55-58 author comment, R22)")
            if "rx2 literal" not in m.flags:
                m.flags.append("rx2 literal")
        # H1
        p_h1 = lambda r: r["ret"] in (F.RET_ACK_TIMEOUT, F.RET_DRAIN_TIMEOUT) and r["nwords"] == 0 and allff(r)
        for label, recs in (("P33+P08", post_p), ("P08", post_08), ("P33", post_33)):
            ok, k, n, sp = m.persistent(recs, p_h1)
            if ok:
                e4 = sum(1 for r in recs if r["ret"] == -4 and r["ack_polls"] == F.ACK_POLLS_TIMEOUT)
                e3 = sum(1 for r in recs if r["ret"] == -3 and r["drain"] == F.DRAIN_E3)
                durs = sorted(r["_t1"] - r["_t0"] for r in recs if p_h1(r))
                labs = Counter(m.label_of(r["lc_epc"]) for r in recs if p_h1(r) and r["lc_flags"] & F.LC_F_VALID)
                wpost = [w for w in m.WT if w["_t0"] >= t_on]
                wok = sum(1 for w in wpost if w["ret"] >= 0)
                variant = ("9.5 variant: %d of %d W records after onset kept ret >= 0" % (wok, len(wpost))
                           if wpost and wok >= PERSIST_FRAC * len(wpost) else "pure: W records fail too")
                ri3 = sum(1 for p in post_poll if p["ri_branch"] == F.RI_R3)
                res["state"].append("H1")
                ev["H1"].append("%s: %d of %d records ret -4/-3 with nwords 0 and rx all ff over %.1f s "
                                "(-4 with ack_polls 1,000,001: %d; -3 with drain 0xFFFF: %d); median duration "
                                "%.2f ms; lc_epc labels %s; POLL ri_branch 3 on %d of %d; %s"
                                % (label, k, n, sp, e4, e3, durs[len(durs) // 2] / CPT * 4.0 if durs else 0,
                                   dict(labs), ri3, len(post_poll), variant))
                break
        # H2
        p_h2 = lambda r: r["ret"] == 0 and r["nwords"] >= 1 and r["rx"][0] == 0 and bytes(r["rx"][3:7]) == b"\0" * 4
        ok, k, n, sp = m.persistent(post_08, p_h2)
        if ok:
            ri4 = sum(1 for p in post_poll if p["ri_branch"] == F.RI_R4)
            res["state"].append("H2")
            ev["H2"].append("P08 ret 0, nwords >= 1, rx[0] = 0, rx[3..6] = 00 on %d of %d over %.1f s; "
                            "POLL ri_branch 4 on %d of %d (not the HOLD switch: a real HOLD frame clears only "
                            "rx[4] b5 with a normal rx[0..2])" % (k, n, sp, ri4, len(post_poll)))
        # H3
        fin = lambda r: r["ack_polls"] not in (F.ACK_POLLS_TIMEOUT, F.ACK_POLLS_NOT_REACHED)
        p_h3 = lambda r: r["ret"] == 0 and r["nwords"] == 0 and allff(r) and fin(r)
        ok, k, n, sp = m.persistent(post_08, p_h3)
        if ok:
            ri5 = sum(1 for p in post_poll if p["ri_branch"] == F.RI_R5)
            mm = [p for p in post_poll if p["mouse_flags"] & F.MOUSE_F_CALLED]
            drift = sum(1 for p in mm if p["dx"] == 16 and p["dy"] == 16)
            ded = sum(1 for p in post_poll if p["pi_flags"] & F.PI_F_DEDUPE)
            res["state"].append("H3")
            ev["H3"].append("P08 ret 0, nwords 0, rx all ff, finite ack_polls on %d of %d over %.1f s; POLL "
                            "ri_branch 5 on %d of %d; mouse polls %d with dx=+16 dy=+16 on %d; dedupe on %d"
                            % (k, n, sp, ri5, len(post_poll), len(mm), drift, ded))
        # H5
        p_h5 = lambda r: r["ret"] in (F.RET_BADFRAME, F.RET_BUSY)
        for label, recs in (("P33+P08", post_p), ("P08", post_08), ("P33", post_33)):
            ok, k, n, sp = m.persistent(recs, p_h5)
            if ok:
                e5 = [r for r in recs if r["ret"] == -5]
                e2 = [r for r in recs if r["ret"] == -2]
                d5 = sum(1 for r in e5 if r["retries"] == F.RETRIES_E5 and r["rx"][2] in BUSY_CODES)
                d2 = Counter()
                for r in e2:
                    rx = r["rx"]
                    d2["rx[1]<3" if rx[1] < 3 else ("rx[1]>=16 (out-of-bounds checksum)" if rx[1] >= 16 else
                                                     ("checksum mismatch" if checksum_ok(rx) is False else
                                                      "checksum recomputes OK"))] += 1
                wbusy = sum(1 for w in m.WT if w["_t0"] >= t_on and w["rx"][2] in BUSY_CODES)
                res["state"].append("H5")
                ev["H5"].append("%s: ret -2/-5 on %d of %d over %.1f s; -5: %d (retries 16 with rx[2] 0x80/0x81: "
                                "%d); -2: %d %s; W records with BUSY rx[2] after onset: %d"
                                % (label, k, n, sp, len(e5), d5, len(e2), dict(d2), wbusy))
                break
        # N2b before H6 (merged P + W + M timeline)
        sc_all = sorted([r for r in m.P + m.M + m.W if r["_t0"] >= t_on], key=lambda r: (r["_t0"], r["_rn"] != "W"))
        lag = []
        for a, b in zip(sc_all, sc_all[1:]):
            exp_prev, _ = tmpl.rx2(a["cmd"])
            exp_own, _ = tmpl.rx2(b["cmd"])
            lag.append(b["rx"][2] == exp_prev and b["rx"][2] != exp_own and b["drain"] == 0)
        n2b = False
        if sc_all and len(lag) >= 2:
            k = sum(lag)
            sp = (sc_all[-1]["_t0"] - sc_all[0]["_t0"]) / float(CPT * TPS)
            if k >= PERSIST_FRAC * len(lag) and sp >= PERSIST_S:
                n2b = True
                getc = [r for r in sc_all if r["cmd"] != 0x08 and r["rx"][2] == rx2_08]
                res["state"].append("N2b")
                ev["N2b"].append("command n's rx[2] equals the expected rx[2] of command n-1's cmd with drain 0 "
                                 "on %d of %d over %.1f s%s; P33/W/M records carrying GetCtrl2-shaped frames: %d "
                                 "(button byte changes among them: %d)"
                                 % (k, len(lag), sp, " (rx2 literal)" if lit08 else "", len(getc),
                                    self._key_changes(getc)))
        # H6
        dwin = self.d_window()
        if dwin is not None:
            win08 = [r for r in post_08 if dwin[0] <= r["_t0"] < dwin[1]]
            win_note = "D1-D7 window from operator times"
        else:
            win08 = post_08
            win_note = "no operator times: D window = whole post-onset span"
        p_h6 = lambda r: r["ret"] > 0 and checksum_ok(r["rx"]) is True and r["rx"][2] == rx2_08
        ok6, k6, n6, sp6 = m.persistent(win08, p_h6)
        if ok6 and not n2b and (dwin is None or dwin[1] > t_on):
            ident = len(set(bytes(r["rx"][3:9]) for r in win08 if p_h6(r))) == 1
            getc = [r for r in m.P33 + m.W + m.M if r["_t0"] >= t_on and r["rx"][2] == rx2_08 and r["cmd"] != 0x08]
            follow = self._key_changes(sorted(getc, key=lambda r: r["_t0"]))
            pw = [p for p in post_poll if p["ri_branch"] == F.RI_R5]
            ded = sum(1 for p in pw if p["pi_flags"] & F.PI_F_DEDUPE)
            if ident and follow == 0:
                c0 = self.c0_changes()
                res["state"].append("H6")
                ev["H6"].append("P08 ret > 0, checksum valid, rx[2] = 0x%02x (%s), rx[3..8] byte-identical "
                                "(%s) on %d of %d over %.1f s [%s]; no P33/W/M GetCtrl2-shaped frame follows "
                                "presses; POLL dedupe on %d of %d R5 polls"
                                % (rx2_08, "rx2 literal" if lit08 else "template", hexrx(win08[0]["rx"][3:9]),
                                   k6, n6, sp6, win_note, ded, len(pw)))
                if c0 is None:
                    ev["H6"].append("no C0 reference (no operator C0 times): presses taken from the source bit "
                                    "map (TRIANGLE rx[3] b4, RIGHT rx[3] b1, LTRG rx[4] b1, HOLD rx[4] b5, "
                                    "VOL_UP rx[5] b0, stick rx[7]/rx[8])")
                    if "no C0 reference" not in m.flags:
                        m.flags.append("no C0 reference")
                else:
                    ev["H6"].append("C0 reference changed: %s" % dict(c0))
                if dwin is None:
                    ev["H6"].append("caveat: 'operator not pressing' is excluded only by the notes and photo P6")
        # N2
        p_n2 = lambda r: r["drain"] > 0 and r["drain"] != F.DRAIN_E3
        ok, k, n, sp = m.persistent(post_p, p_n2)
        if ok:
            t08 = tmpl.cmd.get(0x08) if tmpl.ok else None
            if t08 and t08["drain"][1] > 0:
                res["notes"].append("N2 candidate: drain > 0 but the template's drain range is %s" % (t08["drain"],))
            else:
                res["state"].append("N2")
                ev["N2"].append("drain > 0 on %d of %d commands over %.1f s; drain_last values %s%s"
                                % (k, n, sp, Counter(r["drain_last"] for r in post_p).most_common(3),
                                   "" if tmpl.ok else " (no template: compared with drain = 0, unassessable)"))
        # N3
        p_n3 = lambda r: r["ret"] > 0 and r["rx"][2] in N3_CODES
        ok, k, n, sp = m.persistent(post_08, p_n3)
        if ok:
            res["state"].append("N3")
            ev["N3"].append("rx[2] in {0x83, 0x86} with ret > 0 on %d of %d P08 over %.1f s" % (k, n, sp))
        # N11
        ok, k, n, sp = m.persistent(post_poll, lambda p: p["ri_branch"] == F.RI_R4)
        if ok:
            wf = [r for r in post_08 if r["ret"] > 0 and checksum_ok(r["rx"]) is True and not (r["rx"][4] & 0x20)
                  and r["rx"][0] != 0]
            if len(wf) >= PERSIST_FRAC * max(1, len(post_08)) and self._key_changes(wf) > 0:
                c0 = self.c0_changes()
                res["state"].append("N11")
                ev["N11"].append("persistent ri_branch 4 (%d of %d polls over %.1f s) with well-formed non-zero "
                                 "P08 frames whose other bytes change (%d changes), rx[4] b5 = 0 throughout; C0 "
                                 "HOLD changes: %s" % (k, n, sp, self._key_changes(wf),
                                                       None if c0 is None else c0.get("HOLD rx[4]b5", 0)))
        # H7 (a)-(e), N6, N10
        valid08 = [r for r in post_08 if tmpl.own_valid(r)]
        follows = self._key_changes(valid08)
        if dwin is not None:
            follows_d = self._key_changes([r for r in valid08 if dwin[0] <= r["_t0"] < dwin[1]])
        else:
            follows_d = follows
        if valid08 and len(valid08) >= PERSIST_FRAC * max(1, len(post_08)) and follows >= 2 and follows_d >= 1:
            self._h7(res, tmpl, post_poll, t_on, follows)
        self._n10(res, tmpl, post_poll)

    def _h7(self, res, tmpl, post_poll, t_on, follows):
        m = self.m
        ev = res["evidence"]
        stage = []
        changed = [p for p in post_poll if p["ri_branch"] == F.RI_R5 and p["pi_flags"] & F.PI_F_CALLED
                   and not p["pi_flags"] & F.PI_F_DEDUPE]
        fails = [p for p in changed if p["push_fail"] or p["pi_flags"] & F.PI_F_LISTSEM_FAIL or p["nqueues"] == 0]
        if changed and len(fails) >= PERSIST_FRAC * len(changed):
            stage.append("a")
            ev["H7"].append("(a) %d of %d changed polls with push_fail / list_sem failure / nqueues 0; "
                            "jp_listsem_fail +%s, jp_push_full +%s, jp_push_eintr +%s"
                            % (len(fails), len(changed), m.stat_delta("jp_listsem_fail", t_on),
                               m.stat_delta("jp_push_full", t_on), m.stat_delta("jp_push_eintr", t_on)))
        d = {f: m.stat_delta(f, t_on) for f in ("jp_push_ok", "jp_wake", "fop_read_ret", "jp_mouse_reports",
                                                 "md_event_syn", "md_notify_calls", "md_read_ret",
                                                 "vcs_putchar", "jp_changed")}
        ups = [u for u in m.uhb if fine(u["stats_now_tick"], 0) >= t_on]
        coll = (ups[-1]["mouse_pkts_total"] - ups[0]["mouse_pkts_total"]) if len(ups) >= 2 else None
        if d["jp_push_ok"] and d["jp_wake"] and d["fop_read_ret"] == 0:
            stage.append("b")
            ev["H7"].append("(b) pushes OK (+%d) and jp_wake rising (+%d), fop_read_ret flat: psposk2 not "
                            "consuming" % (d["jp_push_ok"], d["jp_wake"]))
        if d["jp_mouse_reports"] and d["md_event_syn"] and d["md_notify_calls"] and coll and \
                d["md_read_ret"] is not None and d["md_read_ret"] - coll <= 0:
            stage.append("c")
            ev["H7"].append("(c) mouse_reports +%d, md_event_syn +%d, md_notify_calls +%d; md_read_ret +%d minus "
                            "the collector's own reads %d = flat (pspmd not reading) while the collector's "
                            "client gets packets" % (d["jp_mouse_reports"], d["md_event_syn"],
                                                     d["md_notify_calls"], d["md_read_ret"], coll))
        rows = m.stats_between(t_on)
        low = [s for s in rows if s["console_sem_count"] <= 0]
        if (d["vcs_putchar"] == 0 and d["fop_read_ret"]) or (len(low) >= 2 and fine(low[-1]["now_tick"], 0) -
                                                              fine(low[0]["now_tick"], 0) >= NEAR_S * TPS * CPT):
            stage.append("d")
            ev["H7"].append("(d) vcs_putchar +%s while fop_read_ret +%s; console_sem count <= 0 in %d STATS rows"
                            % (d["vcs_putchar"], d["fop_read_ret"], len(low)))
        sig = [p for p in post_poll if p["sig"] & F.SIG_PENDING]
        if sig:
            stage.append("e")
            ev["H7"].append("(e) POLL sig b0 on %d of %d polls" % (len(sig), len(post_poll)))
        if stage:
            res["state"].append("H7")
            res["h7"] = stage
            ev["H7"].insert(0, "raw rx follows the presses after onset (%d key changes in valid P08), "
                               "delivery stops at stage %s" % (follows, ",".join(stage)))
            # N6: userland consumers die while kernel delivery works (PROCS)
            pr = [p for p in m.col.procs if p[0] is not None and fine(p[0], 0) >= t_on]
            if pr and ("b" in stage or "c" in stage):
                txt = pr[-1][1]
                miss = [lab for lab in ("OSK", "MD") if ("\n%s " % lab) not in ("\n" + txt)]
                stuck = re.findall(r'^(OSK|MD) \d+ \d+ \([^)]*\) ([DTZ])', txt, re.M)
                if miss or stuck:
                    res["state"].append("N6")
                    ev["N6"].append("kernel delivery works; PROCS after onset: missing %s, stuck %s" % (miss, stuck))

    def _n10(self, res, tmpl, post_poll):
        m = self.m
        for (pseq, tick, mode, rxh, rseq) in self.toggles:
            p = m.POLLseq.get(pseq)
            r = p.get("_p08") if p else None
            if r is None or mode:
                continue
            foreign = r["wn"] >= 1 or r["rx"][2] != tmpl.rx2(0x08)[0] or (r["ret"] == 0 and r["nwords"] >= 1)
            if foreign:
                after = [q for q in m.POLL if q["seq"] > pseq][:200]
                off = [q for q in after if not q["mouse_flags"] & F.MOUSE_F_CALLED]
                if off:
                    res["state"].append("N10")
                    res["evidence"]["N10"].append("POLL seq %d toggled mouse mode off on a foreign P08 seq %d "
                                                  "(wn %d, rx %s); mouse not called afterwards on %d polls"
                                                  % (pseq, rseq, r["wn"], rxh, len(off)))

    def _h8(self, res, tmpl, post_p, t_on):
        """Row H8: flags beside the state, never alone."""
        m = self.m
        if not tmpl.ok:
            base = [r for r in m.W + m.M if r["_t0"] < t_on]
            res["h8"].append("unassessable (no template): baseline WB/M/WT gpio_in %s spi_st9 %s spi_sttx %s"
                             % (sorted(set(r["gpio_in"] for r in base))[:6],
                                sorted(set(r["spi_st9"] for r in base))[:6],
                                sorted(set(r["spi_sttx"] for r in base))[:6]))
            return
        for cmd in (0x33, 0x08):
            t = tmpl.cmd.get(cmd)
            if not t:
                continue
            rs = [r for r in post_p if r["cmd"] == cmd and r["ret"] not in (-3, -4)]
            if len(rs) < 10:
                continue
            for fld in ("gpio_in", "spi_st9", "spi_sttx"):
                outv = Counter(r[fld] for r in rs if r[fld] not in t[fld])
                if sum(outv.values()) >= PERSIST_FRAC * len(rs):
                    res["h8"].append("cmd 0x%02x %s left the template %s: %s" %
                                     (cmd, fld, sorted(t[fld]), dict(outv.most_common(3))))
            z = sum(1 for r in rs if r["ack_polls"] == 0)
            if z >= PERSIST_FRAC * len(rs) and t["ack"][0] > 0:
                res["h8"].append("cmd 0x%02x ack_polls always 0 after onset (latch stuck) on %d of %d; template %s"
                                 % (cmd, z, len(rs), t["ack"]))
            dr = [r for r in rs if not (t["drain"][0] <= r["drain"] <= t["drain"][1])]
            if len(dr) >= PERSIST_FRAC * len(rs):
                res["h8"].append("cmd 0x%02x drain left the template %s" % (cmd, t["drain"]))
        sr = [s for s in m.S if s["_t0"] >= t_on]
        so = 0
        co = 0
        for s in sr:
            so |= s["rd_set_or"]
            co |= s["rd_clr_or"]
        if sr and ((so & ~tmpl.led_set_or) or (co & ~tmpl.led_clr_or)):
            res["h8"].append("LED read-back ORs gained bits after onset: set 0x%08x (template 0x%08x), clear "
                             "0x%08x (template 0x%08x)" % (so, tmpl.led_set_or, co, tmpl.led_clr_or))
        if res["h8"]:
            res["h8"].append("declared blind spot: SPI +0x00,+0x04,+0x14,+0x18,+0x20,+0x24 and GPIO +0x00,+0x10,"
                             "+0x14,+0x18,+0x24 are not observed (H8 unresolved there)")

    # ---------------------------------------------------------------- triggers
    def _triggers(self, res, tmpl, t_on, Fc):
        m = self.m
        ev = res["evidence"]
        onset_tick = (Fc["tick_in"] if Fc else t_on // CPT)
        cyc = NEAR_CYCLES * WD
        near_wt = [w for w in m.WT if abs(w["tick_in"] - onset_tick) <= cyc]
        # every WT within +- 2 cycles, with its step and both results (r5, UL7)
        listing = []
        for w in near_wt:
            st = m.w_step(w) if w["ext"]["t_busy"] & F.TBUSY_P else None
            thr = m.Pseq.get(w["ext"]["p_head"]) if w["ext"]["t_busy"] & F.TBUSY_P else None
            listing.append("WT seq %d tick %d: t_busy %d, own ret %d nwords %d rx[2] 0x%02x (%s)%s%s"
                           % (w["seq"], w["tick_in"], w["ext"]["t_busy"], w["ret"], w["nwords"], w["rx"][2],
                              "valid" if tmpl.own_valid(w) else "NOT a valid Nop reply",
                              "; straddled P seq %d step %s %s, thread ret %d (%s)"
                              % (thr["seq"], st["label"], st["ppoint"], thr["ret"],
                                 "valid" if tmpl.own_valid(thr) else "not valid") if thr else "",
                              "; P-link via time" if thr is None and w["ext"]["t_busy"] & 1 else ""))
        res["wt_listing"] = listing
        # H4: a WT with t_busy b0 linked to the in-flight P command with wn >= 1
        straddles = []
        for w in m.WT:
            if not (w["ext"]["t_busy"] & F.TBUSY_P):
                continue
            thr = m.Pseq.get(w["ext"]["p_head"])
            if thr is None:
                continue
            straddles.append((w, thr))
        res["straddles"] = straddles
        if Fc is not None:
            for (w, thr) in straddles:
                if Fc["seq"] - 2 <= thr["seq"] <= Fc["seq"]:
                    st = m.w_step(w)
                    cc = self.crosscheck(st["ppoint"], thr, tmpl, st)
                    res["triggers"].append("H4")
                    ev["H4"].append("WT seq %d at tick %d (wdph 0) with t_busy b0, W.p_head = P seq %d (wn %d); "
                                    "step from %s 0x%08x = %s -> %s%s%s; Nop's own ret %d nwords %d ack_polls %d "
                                    "drain %d drain_last 0x%04x rx %s; thread result ret %d nwords %d rx %s: %s"
                                    % (w["seq"], w["tick_in"], thr["seq"], thr["wn"], st["src"],
                                       st["epc"] or 0, st["label"], st["ppoint"],
                                       " (EPC or its delay slot)" if st["bd"] else "",
                                       kj_text(st),
                                       w["ret"], w["nwords"], w["ack_polls"], w["drain"], w["drain_last"],
                                       hexrx(w["rx"]), thr["ret"], thr["nwords"], hexrx(thr["rx"]), cc))
                    if st.get("map_note"):
                        ev["H4"].append(st["map_note"])
                    if thr["wn"] < 1:
                        ev["H4"].append("inconsistent: the straddled P record has wn = 0")
                    break
            # H4 two-stage: straddle at Nop k with both results valid, onset at Nop k+1
            for (w, thr) in straddles:
                if tmpl.own_valid(w) and tmpl.own_valid(thr):
                    k1 = w["tick_in"] + WD
                    if Fc["tick_in"] <= k1 <= Fc["_tick_out"] or 0 <= Fc["tick_in"] - k1 <= TPS:
                        res["triggers"].append("H4 two-stage")
                        ev["H4 two-stage"].append("straddle at Nop tick %d (P seq %d, both results valid), onset "
                                                  "at Nop k+1 = tick %d (P seq %d)" % (w["tick_in"], thr["seq"],
                                                                                     k1, Fc["seq"]))
            # WB: the first failed thread command is the first after a WT with t_busy b0 = 0
            prev_w = [w for w in m.WT if w["_t0"] <= Fc["_t0"]]
            if prev_w:
                w = prev_w[-1]
                between = [r for r in m.P if w["_t0"] < r["_t0"] < Fc["_t0"]]
                if not (w["ext"]["t_busy"] & F.TBUSY_P) and not between and "H4" not in res["triggers"]:
                    res["triggers"].append("WB")
                    ev["WB"].append("first failed P seq %d is the first command after WT seq %d (tick %d, t_busy 0); "
                                    "the Nop's own ret %d nwords %d rx %s ack_polls %d drain %d: %s"
                                    % (Fc["seq"], w["seq"], w["tick_in"], w["ret"], w["nwords"], hexrx(w["rx"]),
                                       w["ack_polls"], w["drain"],
                                       "valid Nop reply" if tmpl.own_valid(w) else "NOT a valid Nop reply"))
        # H10 / N1m / N1 / N1p on the onset command and the two before it
        if Fc is not None:
            cands = [m.Pseq.get(s) for s in (Fc["seq"] - 2, Fc["seq"] - 1, Fc["seq"])]
            cands = [c for c in cands if c is not None]
        else:
            cands = [r for r in m.P if abs(r["_t0"] - t_on) <= NEAR_POLLS * 14 * CPT]
        for r in cands:
            susp = self.suspension(r)
            if susp is None:
                continue
            step, win = susp
            holder = self.holder(r)
            ov = [s for s in m.S if s["_t0"] <= r["_t1"] and s["_t1"] >= r["_t0"]]
            led_dirty = (r["led_or"] & ~LED_BITS) != 0 or any(((s["rd_set_or"] | s["rd_clr_or"]) & ~LED_BITS)
                                                               for s in ov)
            if r["ms_delta"] > 0 and ov and led_dirty:
                res["triggers"].append("H10")
                ev["H10"].append("P seq %d (cmd 0x%02x) ms_delta %d, preempt_delta %d, suspended at %s (window %s), "
                                 "overlapping S seq %s (flags %s), led_or 0x%08x (bits other than 0x40/0x80: 0x%08x), "
                                 "led_pid %d; %s; onset at wdph %d"
                                 % (r["seq"], r["cmd"], r["ms_delta"], r["preempt_delta"], step, win,
                                    [s["seq"] for s in ov], ["0x%02x" % s["flags"] for s in ov], r["led_or"],
                                    r["led_or"] & ~LED_BITS, r["led_pid"], holder, r["tick_in"] % WD))
            elif r["ms_delta"] > 0:
                res["triggers"].append("N1m")
                ev["N1m"].append("P seq %d suspended at %s (window %s) with %d LED read-modify-writes and a clean "
                                 "read-back (led_or 0x%08x); suspension <= %d ticks (lc_tick to exit); led_pid %d; %s. "
                                 "N1 and an LED read side effect cannot be separated in one run"
                                 % (r["seq"], step, win, r["ms_delta"], r["led_or"],
                                    r["dtick"] - r["lc_dtick"] if r["lc_dtick"] != 0xFFFF else -1,
                                    r["led_pid"], holder))
            elif r["wn"] == 0:
                res["triggers"].append("N1")
                ev["N1"].append("P seq %d preempted mid-transaction at %s (window %s), wn 0, ms_delta 0, "
                                "suspension <= %d ticks; %s" % (r["seq"], step, win,
                                                                r["dtick"] - r["lc_dtick"] if r["lc_dtick"] != 0xFFFF
                                                                else -1, holder))
        if Fc is not None and Fc["lc_flags"] & F.LC_F_PANEL:
            st = m.stats_between(Fc["_t0"])
            pt = st[0]["panel_last_tick"] if st else None
            res["triggers"].append("N1p")
            ev["N1p"].append("a kernel panel paint landed while P seq %d was in flight; panel_last_tick %s "
                             "(mod 250 = %s), panel_cost_last %s; step %s"
                             % (Fc["seq"], pt, None if pt is None else pt % 250,
                                st[0]["panel_cost_last"] if st else None,
                                m.label_of(Fc["lc_epc"]) if Fc["lc_flags"] & F.LC_F_VALID else "n/a"))
        # H10b: LED set read-back with bit 3 and no command in flight, +- 2 s
        for s in m.S:
            if abs(s["tick_on"] - onset_tick) <= NEAR_S * TPS and \
                    ((s["flags"] & F.S_F_SET_B3) or (s["rd_set_or"] & 0x08)) and \
                    not (s["flags"] & (F.S_F_P_ENTRY | F.S_F_P_EXIT | F.S_F_M)):
                res["triggers"].append("H10b")
                ev["H10b"].append("S seq %d tick %d: LED set read-back bit 3 (rd_set_or 0x%08x) with no command in "
                                  "flight" % (s["seq"], s["tick_on"], s["rd_set_or"]))
                break
        # LEDSPLIT: a Nop between the load and the store of an LED RMW
        for w in m.WT:
            if m.label_of(w["ext"]["epc"]) == "LEDRMW" and w["ext"]["ext_flags"] & F.EXT_F_REGS_VALID:
                val, _row = m.build.regval("LEDRMW", "loaded", w["ext"]["epc"], w["ext"]["r"])
                near = abs(w["tick_in"] - onset_tick) <= cyc
                if near:
                    res["triggers"].append("LEDSPLIT")
                ev["LEDSPLIT"].append("WT seq %d tick %d%s: EPC 0x%08x in LEDRMW; loaded value %s; G3 (bit 3) %s"
                                      % (w["seq"], w["tick_in"], " (near onset)" if near else "", w["ext"]["epc"],
                                         "0x%08x" % val if val is not None else "not in regmap",
                                         "unknown" if val is None else
                                         ("set in the loaded value: the store re-asserts G3 the Nop had lowered"
                                          if val & 0x08 else "clear in the loaded value")))
        # N8: pdflush wb_kupdate within +- 2 ticks of onset
        kt = sorted(set(s["kupd_last_tick"] for s in m.stats if s["kupd_last_tick"]))
        nk = [t for t in kt if abs(t - onset_tick) <= NEAR_TICKS]
        if Fc is not None:
            nk += [t for t in kt if Fc["tick_in"] - NEAR_TICKS <= t <= Fc["_tick_out"] + NEAR_TICKS and t not in nk]
        if nk:
            pids = set(s["pid_class"][i] & 0xFFFFFF for s in m.stats[-1:] for i in range(8)
                       if (s["pid_class"][i] >> 24) == F.CLASS_PDFLUSH)
            ss = [s for s in m.S if Fc is not None and s["_t0"] <= Fc["_t1"] and s["_t1"] >= Fc["_t0"]
                  and s["pid"] in pids]
            res["triggers"].append("N8")
            ev["N8"].append("wb_kupdate at tick(s) %s within +-%d ticks of onset tick %d; pdflush S records in the "
                            "command's window: %d" % (nk, NEAR_TICKS, onset_tick, len(ss)))
        res["triggers"] = list(dict.fromkeys(res["triggers"]))

    def suspension(self, r):
        """Suspension step of a P command from lc_epc, never from a nested tick
        (lc_flags b0 valid); returns (label, window) if in S5..S20."""
        if not (r["preempt_delta"] > 0 and r["lc_flags"] & F.LC_F_VALID):
            return None
        lab = self.m.label_of(r["lc_epc"])
        n = step_num(lab)
        if n is None or not (5 <= n <= 20):
            return None
        return lab, ("S13..S20 (G3 high)" if n >= 13 else "S5..S12")

    def holder(self, r):
        if not r["pre_flags"] & F.PRE_F_VALID:
            return "holder: none recorded"
        a, b = F.pre_cls_first(r["pre_cls"]), F.pre_cls_last(r["pre_cls"])
        cn = lambda x: F.CLASS_NAMES[x] if x < len(F.CLASS_NAMES) else str(x)
        return ("holder: preemptor %s, last holder %s, preempted %d x256 counts, collector part %d x256%s"
                % (cn(a), cn(b), r["pre_tot"], r["pre_wrk"],
                   " (>=2 preemptions)" if r["pre_flags"] & F.PRE_F_MULTI else ""))

    def crosscheck(self, pp, thr, tmpl, st):
        """10.7 P-point cross-check (A1 TE2): the thread's result must be one
        recon section 5.1 allows."""
        if pp is None or pp.startswith("unknown"):
            return "outcome not cross-checked (no step)"
        own = tmpl.own_valid(thr)
        ret, nw, rx = thr["ret"], thr["nwords"], thr["rx"]
        e3 = ret == 0 and nw == 0
        e4 = ret == 0 and nw >= 1 and rx[0] == 0
        foreign = ret > 0 and checksum_ok(rx) is True and not own
        allowed = {
            "P0": own, "P1": own, "P7": own,
            "P2": ret in (-4, -2) or (own and thr["retries"] > 0) or e3 or e4 or foreign,
            "P3": foreign or ret == -4 or e3,
            "P4": e3 or foreign or ret == -4, "P5a": e3 or foreign or ret == -4,
            "P4 or P5a": e3 or foreign or ret == -4,
            "P5b": e3 or foreign,
        }.get(pp)
        if pp == "P6":
            j = st.get("j")
            pend = st.get("pending")
            nws = nwset(thr)
            nwtxt = "nwords %d%s" % (nw, " (7 or 8)" if thr.get("nw7or8") else "")
            if pend == 1:
                pop = isinstance(j, int) and (j + 1) in nws
                return ("allowed for P6 (the Nop fell between the thread's status test and its data read: "
                        "any result%s; ret %d, %s, j %s)"
                        % ("; P6, empty-FIFO pop: the thread read the data register after the Nop had "
                           "drained the FIFO" if pop else "", ret, nwtxt, j))
            if ret == -2 and isinstance(j, int) and j in nws:
                return "allowed for P6 (-2 with nwords = j = %d%s)" % (j, ", flagged nw7or8" if thr.get("nw7or8")
                                                                      else "")
            if thr["retries"] > 0:
                return "allowed for P6 (a retry)"
            if own and isinstance(j, int) and j in nws:
                return ("allowed for P6 (the Nop came after the thread had read all %d words: its own valid "
                        "reply, j = n, outside recon 5.1's 1 <= j < n)" % j)
            if pend == 0 and isinstance(j, int):
                return ("INCONSISTENT for P6 (ret %d, %s, j %d, Nop not between the status test and the data "
                        "read; epc/lc_epc, ext_flags, lc_n to be read)" % (ret, nwtxt, j))
            return ("allowed for P6 only if the Nop fell between the status test and the data read "
                    "(ret %d, %s, j %s; not determinable from the regmap)" % (ret, nwtxt, j))
        if allowed is None:
            return "outcome not cross-checked (P-point %s)" % pp
        return "allowed for %s" % pp if allowed else "INCONSISTENT for %s (epc/lc_epc, ext_flags, lc_n to be read)" % pp

    # ---------------------------------------------------------------- H10 conclusion (step 5)
    def h10_conclusion(self, onset_res, tmpl):
        m = self.m
        hi = []
        for r in m.P:
            s = self.suspension(r)
            if s and step_num(s[0]) >= 13 and r["ms_delta"] > 0:
                hi.append(r)
        if onset_res and "H10" in onset_res["triggers"]:
            return "H10 trigger (row H10, bits and window above)"
        if onset_res and "N1m" in onset_res["triggers"]:
            return "N1m (row N1m)"
        if not hi:
            return "H10 untested in this run (no LED operation overlapped a thread suspension at S13..S20)"
        Fc = onset_res["placements"]["first_failed"] if onset_res else None
        if Fc is not None and Fc["ms_delta"] > 0 and self.suspension(Fc):
            return ("H10 not refuted: the onset command itself had LED activity during a suspension in S5..S20 "
                    "(refutation never printed in that case)")
        clean = [r for r in hi if (r["led_or"] & ~LED_BITS) == 0]
        if clean:
            return ("H10 write-back mechanism refuted: the set/clear registers did not read back the "
                    "transaction's lines (%d overlap(s) at S13..S20 with led_or & ~0xC0 = 0; says nothing about "
                    "read side effects; not inferred from bit-3 counts)" % len(clean))
        return "H10 overlaps present with dirty read-backs but no onset attributed to them"

    # ---------------------------------------------------------------- step 7
    def harm_table(self, t_limit, tmpl, onset_cmd=None):
        m = self.m
        L = [0, 0]
        N = [0, 0]
        for r in m.P:
            if r["_t0"] >= t_limit:
                break
            if not (r["preempt_delta"] > 0 and r["lc_flags"] & F.LC_F_VALID and r["lc_flags"] & F.LC_F_IN_SYSCON):
                continue
            n = step_num(m.label_of(r["lc_epc"]))
            if n is None or not (5 <= n <= 20):
                continue
            harm = not tmpl.own_valid(r)
            g = L if r["ms_delta"] > 0 else N
            g[0] += 1
            g[1] += harm
        p = fisher_one_sided(L[1], L[0], N[1], N[0])
        verdict = ("LED activity during a suspended transaction is associated with harm on this hardware"
                   if p < FISHER_P and L[1] >= FISHER_MIN_HL else "no association detected")
        rate = lambda h, n: ("%d/%d (95%% upper bound %.3f)" % (h, n, ub95(n)) if h == 0
                             else "%d/%d = %.3f" % (h, n, h / float(n)))
        txt = ("pre-registered harm-rate comparison (10.7 step 7): group L (ms_delta > 0) %s; group N "
               "(ms_delta = 0) %s; one-sided Fisher p = %.4g; rule p < %.2g and h_L >= %d: %s"
               % (rate(L[1], L[0]), rate(N[1], N[0]), p, FISHER_P, FISHER_MIN_HL, verdict))
        if onset_cmd is not None:
            txt += "; onset command P seq %d: ms_delta %d, suspension %s" % (onset_cmd["seq"], onset_cmd["ms_delta"],
                                                                          self.suspension(onset_cmd))
        return txt

    # ---------------------------------------------------------------- step 8 / hazard statistics
    def interleave_stats(self, tmpl):
        m = self.m
        per = defaultdict(lambda: [0, 0])  # ppoint -> [hits, harmful]
        for w in m.WT:
            if not (w["ext"]["t_busy"] & F.TBUSY_P):
                continue
            thr = m.Pseq.get(w["ext"]["p_head"])
            st = m.w_step(w)
            pp = st["ppoint"] or "unknown"
            per[pp][0] += 1
            if thr is None or not (tmpl.own_valid(thr) and tmpl.own_valid(w)):
                per[pp][1] += 1
        return per

    def no_death_inference(self, tmpl):
        per = self.interleave_stats(tmpl)
        lines = []
        for pp in ("P0", "P1", "P2", "P3", "P4", "P5a", "P4 or P5a", "P5b", "P6", "P7"):
            hits, harm = per.get(pp, (0, 0))
            benign = hits - harm
            lines.append("%s: %d Nop hits on an in-flight command, %d benign; per-hit harm 95%% upper bound %s"
                         % (pp, hits, benign, "%.3f" % ub95(benign) if benign else "inf (n = 0)"))
        n45 = sum(per.get(k, (0, 0))[0] - per.get(k, (0, 0))[1] for k in ("P4", "P5a", "P4 or P5a"))
        if n45 >= H4_SUFF_N:
            verdict = "H4 at P4/P5a is not sufficient on this kernel at p >= %.1f (n = %d)" % (H4_SUFF_P, n45)
        else:
            verdict = "inconclusive (n(P4) + n(P5a) = %d < %d)" % (n45, H4_SUFF_N)
        m = self.m
        late = [p for p in m.POLL if p["wk_delay"]]
        late.sort(key=lambda p: -p["wk_delay"])
        exp = ("late starts: %d polls with a wake-up delay; longest %s x256 counts; collector part of those: %s; "
               "last holders %s" % (len(late), late[0]["wk_delay"] if late else 0,
                                    sum(p["wk_wrk"] for p in late[:20]),
                                    dict(Counter(F.CLASS_NAMES[p["wk_cls1"] & 7] for p in late[:50]))))
        pre = [r for r in m.P if r["pre_flags"] & F.PRE_F_VALID]
        exp2 = ("in-flight preempted time by holder class: %s" %
                dict(Counter((F.CLASS_NAMES[F.pre_cls_last(r["pre_cls"]) & 7]) for r in pre)))
        return lines, verdict, [exp, exp2]

    # ---------------------------------------------------------------- run everything
    def run(self):
        m = self.m
        # step 2 needs the onset candidates first
        cands0 = self.onset_candidates(None)
        early = [c for c in cands0 if c[0] in ("O1", "O2", "O4", "O5a", "O5b")]
        t_first = m.P[0]["_t0"] if m.P else 0
        t_hi = (min(c[1] for c in early) - TEMPLATE_GUARD_S * TPS * CPT) if early else m.t_end
        allsc = m.P + m.W + m.M
        c0 = self.c0_window()
        if c0:
            allsc = [r for r in allsc if not (c0[0] <= r["_t0"] < c0[1])]
            polls = [p for p in m.POLL if not (c0[0] <= p["_t0"] < c0[1])]
        else:
            polls = m.POLL
        if self.m.no_template:
            tmpl = Template()
            tmpl.reason = "template removed (--no-template)"
        else:
            tmpl = learn_template(allsc, polls, m.S, t_first, t_hi)
            if c0:
                tmpl.reason += " (C0 excluded)"
        if not tmpl.ok:
            tmpl.baseline = [r for r in m.W + m.M if r["_t0"] < t_hi]
        self.tmpl = tmpl
        self.simulate_polls(tmpl)
        cands = self.onset_candidates(tmpl)
        # merge candidates closer than 1 s, keep all names
        merged = []
        for c in cands:
            if merged and c[1] - merged[-1][1] <= TPS * CPT:
                merged[-1] = (merged[-1][0] + "+" + c[0], merged[-1][1], merged[-1][2] + "; " + c[2])
            else:
                merged.append(c)
        self.cands = merged
        self.results = [self.classify(c, tmpl) for c in merged]
        primary = None
        for r in self.results:
            if r["stopped"] or r["state"]:
                primary = r
                break
        if primary is None:
            for r in self.results:
                if not r["quiet"] and r["post_span_s"] >= PERSIST_S:
                    primary = r
                    break
        self.primary = primary
        guard = self.guard_status()
        if primary is None:
            self.verdict = "NO DEATH DETECTED"
            self.named = "NO DEATH DETECTED"
        else:
            state = primary["stopped"] or primary["state"]
            trig = primary["triggers"]
            primary["instrumentation_suspect"] = guard["suspect_from"] is not None and \
                primary["tick"] >= guard["suspect_from"]
            if state and not (state == ["thread stopped (no H9/N4/N5/N9 signature)"]):
                self.verdict = "CLASSIFIED"
                self.named = " + ".join(state) + ((" triggered by " + ", ".join(trig)) if trig else "")
            elif trig:
                self.verdict = "CLASSIFIED (trigger only)"
                self.named = "trigger " + ", ".join(trig) + "; state UNCLASSIFIED"
            else:
                self.verdict = "UNCLASSIFIED"
                self.named = "H0 / UNCLASSIFIED"
        self.guard = guard
        return self

    def meta_repeat(self):
        """4.7, repeated from the S records: a metadata sector X is stuck when its
        last 5 write records all have b1, with no successful write of X between
        them, over >= 3 ticks, and in each of those ticks a data write by the
        worker succeeded.  Class from the published geometry (4.8)."""
        m = self.m
        if not m.stats:
            return []
        g = m.stats[-1]
        wrk = set(x & 0xFFFFFF for x in g["pid_class"] if (x >> 24) == F.CLASS_WRK)
        scale = 1 << max(0, ((g["sec_per_clus_bits"] >> 16) & 0xFFFF) - 9)

        def cls(srec):
            if not srec["flags"] & F.S_F_META:
                return "DATA"
            rel = srec["sector"] - g["ms_part_start"]
            fs, fl = g["fat_start"] * scale, g["fat_length"] * scale
            if fs <= rel < fs + fl:
                return "FAT1"
            if fs + fl <= rel < fs + g["fats"] * fl:      # a mirror (4.8: "below fat_start + fats x fat_length")
                return "FATM"
            if rel == g["fsinfo_sector"] * scale:
                return "FSINFO"
            if rel >= g["data_start"] * scale:
                return "DIR"
            return "OTHER"
        ok_data_ticks = set(x["tick_on"] for x in m.S if x["flags"] & F.S_F_WRITE and not x["flags"] & F.S_F_META
                            and not x["flags"] & F.S_F_ERROR and x["pid"] in wrk)
        runs = {}
        out = []
        for x in m.S:
            if not (x["flags"] & F.S_F_WRITE and x["flags"] & F.S_F_META):
                continue
            sec = x["sector"]
            if x["flags"] & F.S_F_ERROR:
                runs.setdefault(sec, []).append(x)
                r = runs[sec][-5:]
                ticks = set(y["tick_on"] for y in r)
                if len(r) == 5 and len(ticks) >= 3 and all(t in ok_data_ticks for t in ticks) and \
                        sec not in [o[0] for o in out]:
                    out.append((sec, cls(x), r[-1]["tick_on"]))
            else:
                runs[sec] = []
        return out

    def guard_status(self):
        m = self.m
        first = None
        for s in m.stats:
            if s["kguard_bad"]:
                first = s["kguard_first_tick"] or s["now_tick"]
                break
        for u in m.uhb:
            if u["flags"] & (1 << 16):
                first = u["stats_now_tick"] if first is None else min(first, u["stats_now_tick"])
                break
        for (t, text, _c) in m.col.events:
            if re.match(r'^guard\s+(?!ok)', text):
                first = t if first is None or (t is not None and t < first) else first
        if getattr(m, "word2_change", None) is not None:    # 10.1, K4: stats word 2 changed mid-run
            first = m.word2_change if first is None else min(first, m.word2_change)
        return {"suspect_from": first}
