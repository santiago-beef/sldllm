#!/usr/bin/env python3
"""pscdec.py - PSC trace decoder (DESIGN.md revision 6, section 10).

Usage:
  pscdec.py -o OUT [options] T001001.BIN T001002.BIN ...   (or a PSCLOG directory)
  pscdec.py -o OUT --raw psc-run1.img [files ...]

Options:
  --raw IMG          whole-stick image (10.2): scanned like the files, only chunks
                     verifying under the run's nonce, grouped under the nearest
                     FILEHDR of that run
  --run N            analyse run N (default: the highest run in the inputs)
  --nonce HEX        choose the boot when one run number carries two nonces
  --build DIR        the packaged build's BUILD directory (handoff/impl/mkmaps.py):
                     System.map, epcmap.txt, regmap.txt (grammar of psc_maps.py),
                     panellayout.txt, build_id.txt and IMAGE.sha256 (10.1, 10.6)
  --system-map, --epcmap, --regmap, --build-id   the same individually
  --times FILE       operator stopwatch times (RUNBOOK E5), lines key=m:ss
                     (launch, selftest_pass, c0_start, c0_end, t_death, d0_start,
                     pull; optional uptime_offset=<seconds>)
  --panel ID=L1|L2|L3|L4|L5|L6   a stall-panel photograph transcription (10.8)
  --no-template      analyse without the healthy template (N-4 test hook)

Exit status: 0 final REPORT.md written; 3 RAW IMAGE REQUIRED (REPORT not final,
written as REPORT-NOT-FINAL.md); 2 inputs refused (run selection) or usage; 1 error.
Inputs are only read, never modified.
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import psc_format as F            # noqa: E402
import pscdec_parse as P          # noqa: E402
import pscdec_analysis as A       # noqa: E402

CPT = F.CPT
TPS = F.HZ

COUNTER_WORDS = ["total_counts_hi", "long_ticks", "head", "m_dropped", "proc_opens", "wd_calls", "p_nested",
                 "p_ticked", "oc_p08", "oc_p33", "oc_w", "jp_loop", "jp_nivcsw", "jp_r3", "jp_r4", "jp_r5",
                 "jp_proc_calls", "jp_dedupe", "jp_changed", "jp_lcd_unblank", "jp_mode_toggles",
                 "jp_listsem_fail", "jp_push_ok", "jp_push_full", "jp_push_eintr", "jp_wake", "jp_mouse_calls",
                 "jp_mouse_noop", "jp_mouse_reports", "fop_open", "fop_release", "fop_read_enter", "fop_read_ret",
                 "fop_read_eintr", "fop_ioctl", "vcs_putchar", "vcs_changecon", "vcs_updscr", "vcs_getsize",
                 "md_event_syn", "md_notify_calls", "md_read_ret", "led_calls", "led_calls_t_busy", "ms_seg_wr",
                 "ms_seg_rd", "ms_err", "kupd_count", "ctl_writes", "panel_paints", "panel_test_done", "lc_nested",
                 "kguard_bad", "ring_rewinds", "head_regress", "slot_bad", "fat_panics", "wk_count", "pre_count"]


def parse_times(path):
    t = {}
    with open(path) as fi:
        lines = fi.read().splitlines()
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        k, v = [x.strip() for x in line.split("=", 1)]
        if ":" in v:
            mm, ss = v.split(":", 1)
            t[k] = int(mm) * 60 + float(ss)
        else:
            t[k] = float(v)
    return t


def flat(d, skip=("_",)):
    out = {}
    for k, v in d.items():
        if k.startswith(skip) or k == "ext":
            continue
        if isinstance(v, (bytes, bytearray)):
            out[k] = v.hex()
        elif isinstance(v, tuple):
            for i, x in enumerate(v):
                out["%s%d" % (k, i)] = x
        else:
            out[k] = v
    if "ext" in d:
        for k, v in flat(d["ext"]).items():
            out["ext." + k] = v
    return out


def write_csv(path, rows):
    rows = [flat(r) for r in rows]
    if not rows:
        open(path, "w").close()
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def rec_line(m, r, tmpl):
    ring = r.get("_rn") or F.RING_NAMES[r["_ring"]]
    tick = r["_tick"]
    c = r["_t0"] - tick * CPT
    wd = "%4d+%.3f" % (tick % F.WD_CYCLE, c / float(CPT))
    head = "%10.4f %9d %6d wdph %s %-4s %7d " % (r["_t0"] / float(CPT * TPS), tick, c, wd, ring, r["seq"])
    if "cmd" in r:
        orig = F.ORIGIN_NAMES[r["ctx"] & 3]
        s = ("%s cmd %02x ret %4d nw %s rt %d dtick %d dur %.1fus ack %d drain %d/%04x gpio %04x st9 %04x "
             "sttx %04x wn %d pd %d ms %d lc %s/%d/%02x led %08x rx %s%s"
             % (orig, r["cmd"], r["ret"], "7|8" if r.get("nw7or8") else str(r["nwords"]), r["retries"], r["dtick"],
                (r["_t1"] - r["_t0"]) / (CPT / 4000.0), r["ack_polls"], r["drain"], r["drain_last"],
                r["gpio_in"], r["spi_st9"], r["spi_sttx"], r["wn"], r["preempt_delta"], r["ms_delta"],
                m.label_of(r["lc_epc"]) or "%08x" % r["lc_epc"], r["lc_n"], r["lc_flags"], r["led_or"],
                A.hexrx(r["rx"]), "" if tmpl.own_valid(r) else "  [not own valid]"))
        if r["lc_flags"] & F.LC_F_NESTED_SEEN:
            s += "  [nested tick]"
        if r.get("_notes"):
            s += "  [%s]" % ",".join(r["_notes"])
        if "ext" in r and (r["ctx"] & 3) == F.ORIGIN_WT:
            e = r["ext"]
            s += (" | ext epc %08x(%s) busy %d p_head %d loop %d stage %d ef %02x pcnt %d lc_epc %08x(%s)"
                  % (e["epc"], m.label_of(e["epc"]), e["t_busy"], e["p_head"], e["jp_loop"], e["jp_stage"],
                     e["ext_flags"], e["cur_pcnt"], e["lc_epc"], m.label_of(e["lc_epc"])))
        return head + s
    if "ri_branch" in r:
        return head + ("POLL sc %d body %d ri %d pi %02x nq %d ok %d fail %02x mouse %02x dx %d dy %d sig %d "
                       "period %d pd %d stage %d nsc %d wk %d/%d cls %d/%d nsw %d"
                       % (r["sc_seq_lo"], r["body_ticks"], r["ri_branch"], r["pi_flags"], r["nqueues"],
                          r["push_ok"], r["push_fail"], r["mouse_flags"], r["dx"], r["dy"], r["sig"],
                          r["period"], r["preempt_delta"], r["stage_max"], r["nsc"], r["wk_delay"],
                          r["wk_wrk"], r["wk_cls0"], r["wk_cls1"], r["wk_nsw"]))
    return head + ("S sector %d n %d flags %02x pid %d dtick %d p_head %d led_ops %d set %08x clr %08x"
                   % (r["sector"], r["nsect"], r["flags"], r["pid"], r["dtick"], r.get("_p_head", 0),
                      r["led_ops"], r["rd_set_or"], r["rd_clr_or"]))


def distances(m, r, kt, ct):
    """10.5: distance (ticks) to the nearest wb_kupdate and collector activity."""
    import bisect
    out = []
    for name, xs in (("kupd", kt), ("coll", ct)):
        if not xs:
            continue
        i = bisect.bisect_left(xs, r["_tick"])
        best = min(((xs[j] - r["_tick"]) for j in (i - 1, i) if 0 <= j < len(xs)), key=abs, default=None)
        if best is not None:
            out.append("%s %+d" % (name, best))
    return " d(" + ", ".join(out) + ")" if out else ""


def activity_ticks(col, m):
    """Collector activity (10.5): EVENT ticks, UHB creation/catch-up/re-send/switch/takeover flags,
    panel paints, guard violations."""
    t = set(e[0] for e in col.events if e[0] is not None)
    for u in m.uhb:
        if u["flags"] & ((1 << 12) | (1 << 15) | (1 << 16) | (1 << 18) | (1 << 19) | (1 << 14)):
            t.add(u["stats_now_tick"])
    for st in m.stats:
        if st["panel_last_tick"]:
            t.add(st["panel_last_tick"])
        if st["kguard_first_tick"]:
            t.add(st["kguard_first_tick"])
    return sorted(t)


def timeline(m):
    allr = []
    for xs in (m.P, m.M, m.POLL, m.S):
        allr.extend(xs)
    allr.extend(m.W)
    prio = lambda r: 0 if (r.get("_rn") == "W") else 1      # ties: W before P (10.7 step 1)
    allr.sort(key=lambda r: (r["_t0"], prio(r)))
    return allr


def panel_parse(spec, m):
    """10.8: '--panel ID=L1|..|L6'.  Fields are found by their keywords
    (panellayout.txt columns are a Stage 2 deliverable; see IMPLEMENTATION notes)."""
    pid, _, body = spec.partition("=")
    lines = body.split("|")
    out = {"photo": pid, "lines": lines}
    l1 = lines[0] if lines else ""
    out["title"] = ("PSC MS RO" if "MS RO" in l1 else "PSC TEST" if "TEST" in l1 else
                    "PSC STALL" if "STALL" in l1 else "?")
    for k in ("DUR", "RDR", "PNT"):
        mm = re.search(r'\b%s\s+([0-9.]+)' % k, l1)
        out[k] = mm.group(1) if mm else None
    if len(lines) > 1:
        mm = re.search(r'NOW\s+([0-9A-Fa-f]+)', lines[1])
        out["now_tick"] = int(mm.group(1), 16) if mm else None
        hx = re.findall(r'\b([0-9A-Fa-f]{8})\b', lines[1])
        out["epc"] = [(h, m.build.label(int(h, 16))) for h in hx[1:]] if hx else []
        mm = re.search(r'(?:PCNT|PC)\s+([0-9A-Fa-f]+)\s*$', lines[1])
        out["pcnt"] = int(mm.group(1), 16) if mm else None
    labs = [l for (_h, l) in out.get("epc", [])]
    if any(l in ("ms_wait_ready", "ms_wait_ced") for l in labs) and (out.get("pcnt") or 0) > 0:
        out["verdict"] = "Memory Stick driver hang (instrumentation exposure, not the investigated failure)"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="PSC decoder (DESIGN 10)")
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--raw")
    ap.add_argument("--run", type=int)
    ap.add_argument("--nonce", type=lambda s: int(s, 16))
    ap.add_argument("--build")
    ap.add_argument("--system-map")
    ap.add_argument("--epcmap")
    ap.add_argument("--regmap")
    ap.add_argument("--build-id", type=lambda s: int(s, 0))
    ap.add_argument("--times")
    ap.add_argument("--panel", action="append", default=[])
    ap.add_argument("--no-template", action="store_true")
    a = ap.parse_args(argv)

    files = []
    for p in a.inputs:
        if os.path.isdir(p):
            files.extend(sorted(glob.glob(os.path.join(p, "T*.BIN")) + glob.glob(os.path.join(p, "t*.bin"))))
        else:
            files.append(p)
    if not files and not a.raw:
        ap.error("no input files and no --raw image")
    bd = a.build
    pick = lambda name, explicit: explicit or (os.path.join(bd, name) if bd and os.path.exists(os.path.join(bd, name))
                                               else None)
    build_id = a.build_id
    if build_id is None and bd and os.path.exists(os.path.join(bd, "build_id.txt")):
        with open(os.path.join(bd, "build_id.txt")) as fi:
            build_id = int(fi.read().split()[0], 0)
    image_sha = None
    if bd and os.path.exists(os.path.join(bd, "IMAGE.sha256")):
        with open(os.path.join(bd, "IMAGE.sha256")) as fi:
            image_sha = fi.read().split()[0]
    build = A.BuildInfo.load(pick("System.map", a.system_map), pick("epcmap.txt", a.epcmap),
                             pick("regmap.txt", a.regmap), build_id, image_sha)
    times = parse_times(a.times) if a.times else {}
    os.makedirs(a.out, exist_ok=True)

    col = P.load(files, raw=a.raw, run=a.run, nonce=a.nonce)
    out = lambda name: os.path.join(a.out, name)
    if col.refused:
        with open(out("REFUSED.txt"), "w") as f:
            f.write("REFUSED: %s\n" % col.refused)
            for (k, d) in sorted(col.runs.items()):
                f.write("run %d nonce 0x%08x: %s\n" % (k[0], k[1], "; ".join(d)))
        with open(out("classification.json"), "w") as fo:
            json.dump({"final": False, "refused": col.refused}, fo, indent=1)
        print("REFUSED: " + col.refused)
        return 2

    m = A.Model(col, build, times, no_template=a.no_template)
    an = A.Analysis(m).run()
    tmpl = an.tmpl
    _outputs(a, col, m, an, out)
    final = not (col.raw_required and not a.raw)
    rep = _report(a, col, m, an, final, times)
    name = "REPORT.md" if final else "REPORT-NOT-FINAL.md"
    for stale in ("REPORT.md", "REPORT-NOT-FINAL.md"):
        if os.path.exists(out(stale)):
            os.remove(out(stale))
    with open(out(name), "w") as fo:
        fo.write(rep)
    pr = an.primary
    js = {"final": final, "raw_required": col.raw_required, "run": col.run, "nonce": col.nonce,
          "verdict": an.verdict, "named": an.named,
          "state": (pr["stopped"] or pr["state"]) if pr else [], "triggers": pr["triggers"] if pr else [],
          "h8": pr["h8"] if pr else [], "h7_stage": pr["h7"] if pr else [],
          "onset": {"cand": pr["cand"], "tick": pr["tick"]} if pr else None,
          "flags": m.flags, "template": tmpl.ok, "epc_ok": m.epc_ok, "conflicts": len(col.conflicts),
          "records": {F.RING_NAMES[r]: len(col.records[r]) for r in range(F.NRINGS)},
          "other_boot_chunks": len(col.other_boot), "above_extent": len(col.above_extent),
          "unverified": len(col.unverified), "only_in_image": len(col.only_in_image),
          "candidates": [{"name": r["cand"], "tick": r["tick"], "state": r["stopped"] or r["state"],
                          "triggers": r["triggers"], "quiet": r["quiet"]} for r in an.results]}
    with open(out("classification.json"), "w") as fo:
        json.dump(js, fo, indent=1, default=str)
    if not final:
        print("RAW IMAGE REQUIRED: final REPORT refused; %s" % "; ".join(col.raw_required))
        return 3
    print("%s: %s" % (an.verdict, an.named))
    return 0


def _outputs(a, col, m, an, out):
    tmpl = an.tmpl
    write_csv(out("p.csv"), m.P)
    write_csv(out("poll.csv"), m.POLL)
    write_csv(out("w.csv"), m.W)
    write_csv(out("s.csv"), m.S)
    write_csv(out("m.csv"), m.M)
    write_csv(out("stats.csv"), [dict(s) for s in col.stats])
    write_csv(out("uhb.csv"), [dict(u) for u in col.uhb])
    with open(out("kmsg.txt"), "wb") as f:
        for (t, b) in col.kmsg:
            f.write(b)
    with open(out("procs.txt"), "w") as f:
        for (t, txt) in col.procs:
            f.write("== flush tick %s\n%s\n" % (t, txt))
    with open(out("events.txt"), "w") as f:
        for (t, text, c) in col.events:
            f.write("%s\t%s\t%s@%d\n" % (t, text, c.file.name, c.off))
    with open(out("segments.txt"), "w") as f:
        f.write("run %d nonce 0x%08x\n" % (col.run, col.nonce))
        for n in col.notes:
            f.write("NOTE %s\n" % n)
        for s in col.sources:
            fh = s.fh
            f.write("%s size %d %s seg %s inst %s writer %s extent %s (%s) chunks %d %s\n"
                    % (s.name, s.size, "FILEHDR run %d" % fh["run"] if fh else "no FILEHDR",
                       "%03d" % fh["seg"] if fh else "-", fh["inst"] if fh else "-",
                       fh["writer_pid"] if fh else "-", col.extent.get(fh["seg"]) if fh else None,
                       col.extent_src.get(fh["seg"]) if fh else "", len(s.good),
                       ("IGNORED: " + s.ignored) if s.ignored else ""))
        if col.raw:
            f.write("raw image %s: %d chunks of the run, FILEHDRs of the run at %s\n"
                    % (col.raw, len(col.raw_source.good) if col.raw_source else 0,
                       [(o, fh["seg"]) for (o, fh) in col.raw_groups]))
        for (k, t) in col.anomalies:
            f.write("ANOMALY %s: %s\n" % (k, t))
    with open(out("bad.txt"), "w") as f:
        f.write("# chunks rejected (10.2): header, CRC, truncated; other boots; above the confirmed extent; "
                "unverified salvage; (ring, seq) conflicts\n")
        for c in col.bad:
            f.write("BAD %s %s@%d type %s len %d fseq %s\n" % (c.status, c.src, c.off, c.ctype, c.length, c.fseq))
        for c in col.other_boot:
            f.write("OTHER-BOOT %s@%d %s len %d nonce 0x%08x\n" % (c.src, c.off, c.name, c.length, c.nonce))
        for (c, seg, rel, ext) in col.above_extent:
            f.write("ABOVE-EXTENT %s@%d %s seg %03d rel %d len %d > confirmed extent %d (listed, not merged)\n"
                    % (c.src, c.off, c.name, seg, rel, c.length, ext))
            if c.ctype == F.CHUNK_RECS:
                blocks, _p = P.parse_recs(c.payload)
                for b in blocks:
                    for raw in b["recs"]:
                        f.write("    %s %s\n" % (F.RING_NAMES[b["ring"]], raw.hex()))
        for (src, off, st, ring, raw) in col.unverified:
            f.write("UNVERIFIED %s@%d (%s chunk, CRC not verifiable) %s seq %d %s\n"
                    % (src, off, st, F.RING_NAMES[ring], int.from_bytes(raw[:4], "little"), raw.hex()))
        for (ring, seq, s1, r1, s2, r2) in col.conflicts:
            f.write("CONFLICT %s seq %d\n  copy 1 %s: %s\n  copy 2 %s: %s\n"
                    % (F.RING_NAMES[ring], seq, s1, r1.hex(), s2, r2.hex()))
        if col.only_in_image:
            f.write("ONLY-IN-IMAGE %d records: %s\n" % (len(col.only_in_image),
                                                         ", ".join("%s:%d" % (F.RING_NAMES[r], s)
                                                                   for (r, s) in col.only_in_image[:2000])))
    with open(out("gaps.txt"), "w") as f:
        for g in m.gaps:
            f.write("GAP %s seq %d..%d (%d missing)\n" % g)
        for (ring, first, lost, src) in col.block_lost:
            f.write("BLOCK-LOST %s %d before seq %s (%s@%d)\n" % (F.RING_NAMES[ring], lost, first, src[0], src[1]))
    gaps_at = {}
    for (rn, a0, b0, n) in m.gaps:
        gaps_at.setdefault(rn, []).append((a0, b0, n))
    with open(out("timeline.txt"), "w") as f:
        for ch in m.checks:
            f.write("# CHECK %s\n" % ch)
        last_seq = {}
        kt = sorted(set(st["kupd_last_tick"] for st in m.stats if st["kupd_last_tick"]))
        ct = activity_ticks(col, m)
        f.write("# offset kernel tick - (jiffies - INITIAL_JIFFIES) = %d ticks (dossier 9.6 uptime alignment)\n"
                % m.j_off)
        for r in timeline(m):
            rn = r.get("_rn") or F.RING_NAMES[r["_ring"]]
            ls = last_seq.get(rn)
            if ls is not None and r["seq"] != ls + 1:
                f.write("--- GAP %s seq %d..%d (%d records missing)\n" % (rn, ls + 1, r["seq"] - 1, r["seq"] - ls - 1))
            last_seq[rn] = r["seq"]
            f.write(rec_line(m, r, tmpl) + distances(m, r, kt, ct) + "\n")
    # SC records with dtick > 0 and the ticks they crossed (10.5)
    wt = set(w["tick_in"] for w in m.WT)
    with open(out("crossings.txt"), "w") as f:
        for r in m.P + m.M:
            if r["dtick"] > 0:
                crossed = list(range(r["tick_in"] + 1, r["_tick_out"] + 1))
                wts = [t for t in crossed if t in wt]
                f.write("%s seq %d cmd 0x%02x ticks %d..%d crossed %s%s wn %d%s\n"
                        % (r["_rn"], r["seq"], r["cmd"], r["tick_in"], r["_tick_out"],
                           crossed[:20], " ..." if len(crossed) > 20 else "", r["wn"],
                           (" WT %s%s" % (wts, "" if r["wn"] >= 1 else " CHECK FAILED: wn = 0")) if wts else ""))
    # raw windows per candidate (H0 rule / +-30 s dump)
    tl = timeline(m)
    for r in an.results:
        lo = r["t"] - A.RAW_BEFORE_S * TPS * CPT
        hi = r["t"] + A.RAW_AFTER_S * TPS * CPT
        with open(out("window_%s.txt" % r["cand"].replace("+", "_")), "w") as f:
            f.write("# raw window %s: onset %.3f s, -%d s .. +%d s\n" % (r["cand"], r["t"] / float(CPT * TPS),
                                                                       A.RAW_BEFORE_S, A.RAW_AFTER_S))
            for x in tl:
                if lo <= x["_t0"] < hi:
                    f.write(rec_line(m, x, tmpl) + "\n")
            for s in m.stats_between(lo, hi):
                f.write("STATS tick %d %s\n" % (s["now_tick"], {k: s[k] for k in ("jp_loop", "jp_stage", "t_busy",
                                                                                   "fop_read_ret", "jp_push_ok",
                                                                                   "md_read_ret", "wd_calls")}))
    # stats decreases (10.4)
    dec = []
    for a0, b0 in zip(col.stats, col.stats[1:]):
        for k in COUNTER_WORDS:
            va, vb = a0[k], b0[k]
            if isinstance(va, tuple):
                for i, (x, y) in enumerate(zip(va, vb)):
                    if y < x:
                        dec.append("%s[%d] %d -> %d at tick %d" % (k, i, x, y, b0["now_tick"]))
            elif vb < va:
                dec.append("%s %d -> %d at tick %d" % (k, va, vb, b0["now_tick"]))
    an.stats_decreases = dec


def _fmt_place(pl):
    def one(r):
        if r is None:
            return "none"
        return "P seq %d cmd 0x%02x ticks %d..%d c_in %d ret %d" % (r["seq"], r["cmd"], r["tick_in"], r["_tick_out"],
                                                                    r["c_in"], r["ret"])
    nop = pl["nop"]
    return ("| last successful | %s | %s |\n| first failed | %s | %s |\n| nearest Nop | %s | boundary 1250k = %s |\n"
            % (one(pl["last_ok"]), pl["place_last_ok"], one(pl["first_failed"]), pl["place_first_failed"],
               "W seq %d tick %d c %d..%d" % (nop["seq"], nop["tick_in"], nop["c_in"], nop["c_out"]) if nop else "none",
               pl["boundary"]))


def _report(a, col, m, an, final, times):
    tmpl = an.tmpl
    L = []
    w = L.append
    w("# PSC decoder REPORT%s\n" % ("" if final else " (NOT FINAL)"))
    if not final:
        w("**RAW IMAGE REQUIRED.** The copied files of this run show evidence that makes the raw stick image the "
          "primary path (DESIGN 10.2); a final REPORT is refused without `--raw`. Reasons:\n")
        for r in col.raw_required:
            w("- %s" % r)
        w("\nEverything below is preliminary.\n")
    w("Run %d, nonce 0x%08x; inputs: %d file(s)%s. Decoder thresholds (pre-registered, 10.7): persistent = "
      ">= %d %% of post-onset records over >= %d s; +-%d polls, +-%d ticks, +-%d s, +-%d watchdog cycles; template "
      ">= %d s and >= %d polls ending %d s before the earliest of O1, O2, O4, O5.\n"
      % (col.run, col.nonce, len([s for s in col.sources if not s.ignored]),
         ", raw image %s" % a.raw if a.raw else "", int(A.PERSIST_FRAC * 100), A.PERSIST_S, A.NEAR_POLLS,
         A.NEAR_TICKS, A.NEAR_S, A.NEAR_CYCLES, A.TEMPLATE_MIN_S, A.TEMPLATE_MIN_POLLS, A.TEMPLATE_GUARD_S))
    pr = an.primary
    w("## Classification\n")
    w("**Classification: %s**\n" % an.named)
    if pr:
        state = pr["stopped"] or pr["state"]
        w("- verdict: %s" % an.verdict)
        w("- onset candidate: %s at tick %d (%.3f s, wdph %d)" % (pr["cand"], pr["tick"], pr["tick"] / 250.0,
                                                               pr["tick"] % F.WD_CYCLE))
        w("- triple: trigger %s; state %s; H8 flags %s" % (pr["triggers"] or ["none"], state or ["none"],
                                                           "yes" if pr["h8"] else "none"))
        if pr.get("instrumentation_suspect"):
            w("- **instrumentation-suspect**: this onset is at or after a guard violation (tick %s)"
              % an.guard["suspect_from"])
        else:
            w("- guard status: %s" % ("no guard violation" if an.guard["suspect_from"] is None else
                                      "guard violation at tick %s (after this onset)" % an.guard["suspect_from"]))
        if m.flags:
            w("- flags: %s" % ", ".join(m.flags))
        w("")
        w("### Evidence\n")
        for k, v in pr["evidence"].items():
            for line in v:
                w("- **%s**: %s" % (k, line))
        for h in pr["h8"]:
            w("- **H8 flag**: %s" % h)
        for n in pr["notes"]:
            w("- note: %s" % n)
        if pr.get("wt_listing"):
            w("\nEvery WT record within +-%d cycles of onset (r5, UL7):\n" % A.NEAR_CYCLES)
            for x in pr["wt_listing"]:
                w("- %s" % x)
        if not state:
            w("\nNo row of section 6 matched: **H0 / UNCLASSIFIED**. The raw windows (every P, POLL, W, S and M "
              "record from onset - %d s to onset + %d s) are in `window_%s.txt`; the stats series in `stats.csv`; "
              "KMSG in `kmsg.txt`; PROCS in `procs.txt`.\n" % (A.RAW_BEFORE_S, A.RAW_AFTER_S,
                                                                pr["cand"].replace("+", "_")))
            tl = [x for x in timeline(m) if pr["t"] - 3 * TPS * CPT <= x["_t0"] < pr["t"] + 3 * TPS * CPT]
            w("```")
            for x in tl[:120]:
                w(rec_line(m, x, tmpl))
            w("```")
        w("\n### H10 conclusion\n\n%s\n" % an.h10_conclusion(pr, tmpl))
    else:
        w("No onset candidate shows a failure: every candidate is a quiet period, refuted by later deliveries, "
          "or too short. If no death was perceived this is reported as a result (WORKFLOW Stage 5, row N7: "
          "the 2008 image and this tree may differ), with the perturbation analysis of DESIGN section 7, not as "
          "a pass.\n")
        lines, verdict, exp = an.no_death_inference(tmpl)
        w("### Pre-registered no-death inference (10.7 step 8)\n")
        for l in lines:
            w("- %s" % l)
        w("- **%s**" % verdict)
        for e in exp:
            w("- %s" % e)
        w("\n### H10 conclusion\n\n%s\n" % an.h10_conclusion(None, tmpl))
    w("\n### Harm-rate comparison (10.7 step 7)\n")
    t_lim = min((r["t"] for r in an.results), default=m.t_end)
    w(an.harm_table(t_lim, tmpl, pr["placements"]["first_failed"] if pr else None) + "\n")
    w("## Onset candidates (10.7 step 4)\n")
    st_off = m.offset_ticks
    for r in an.results:
        state = r["stopped"] or r["state"]
        sw = ""
        if st_off is not None:
            up = (r["tick"] - m.j_off) / 250.0
            s = up + st_off
            sw = ", operator stopwatch %d:%04.1f" % (int(s // 60), s % 60)
        w("### %s: tick %d (%.3f s, wdph %d + %.3f)%s\n" % (r["cand"], r["tick"], r["tick"] / 250.0,
                                                          r["tick"] % F.WD_CYCLE, (r["t"] % CPT) / float(CPT), sw))
        w("%s\n" % r["why"])
        w("- rows: state %s, triggers %s, H8 %s%s" % (state or "none", r["triggers"] or "none",
                                                      "yes" if r["h8"] else "none",
                                                      ", QUIET (no failure evidence after it)" if r["quiet"] else ""))
        w("\n| 6.3 placement | command | relative to the Nop boundary |\n|---|---|---|")
        w(_fmt_place(r["placements"]))
        kt = sorted(set(s["kupd_last_tick"] for s in m.stats if s["kupd_last_tick"]))
        if kt:
            near = min(kt, key=lambda t: abs(t - r["tick"]))
            w("- nearest wb_kupdate: tick %d (%+d ticks)" % (near, near - r["tick"]))
        ev = [e for e in col.events if e[0] is not None and abs(e[0] - r["tick"]) <= 5 * TPS]
        if ev:
            w("- collector activity within 5 s: %s" % "; ".join("%s@%d" % (e[1], e[0]) for e in ev[:8]))
        ss = [s for s in m.S if abs(s["_t0"] - r["t"]) <= A.S_NEAR_MS * TPS * CPT // 1000]
        w("- S records within +-%d ms: %d%s" % (A.S_NEAR_MS, len(ss), (" (seq %s)" % [s["seq"] for s in ss[:10]])
                                               if ss else ""))
        w("- raw dump: `window_%s.txt`\n" % r["cand"].replace("+", "_"))
    w("## Template (10.7 step 2)\n")
    if tmpl.ok:
        for cmd, d in sorted(tmpl.cmd.items()):
            w("- cmd 0x%02x: n %d, nwords %s, rx[1] %d, rx[2] 0x%02x, ack_polls %s, drain %s, duration %.1f-%.1f us, "
              "gpio_in %s" % (cmd, d["n"], " or ".join(str(x) for x in d["nwords"]), d["rx1"], d["rx2"], d["ack"],
                             d["drain"], d["dur"][0] / (CPT / 4000.0), d["dur"][1] / (CPT / 4000.0),
                             dict(d["gpio_in"])))
            if d.get("nw7or8"):
                w("  - **`nwords` 7 or 8: the ambiguity is live for cmd 0x%02x** (%d of its %d template records are "
                  "flagged nw7or8; every rule reads them as the set {7, 8}, section 17 R-1)"
                  % (cmd, d["nw7or8"], d["n"]))
        w("- LED read-back ORs: set 0x%08x clear 0x%08x, SC led_or 0x%08x" % (tmpl.led_set_or, tmpl.led_clr_or,
                                                                             tmpl.led_or))
    else:
        w("**NO HEALTHY TEMPLATE** (%s): H8 and N2 unassessable, O3 skipped, code expectations used "
          "(drain = 0; 0x08 >= 5 words, length from rx[1]; finite ack_polls; ret = rx[0]; rx[2] not in "
          "{0x80, 0x81, 0x83, 0x86}); rx[2] compared with the literal command code (`rx2 literal`); "
          "H6/H7 from the source bit map." % tmpl.reason)
    w("\n## Build consistency (10.1)\n")
    w("EPC analysis %s.\n" % ("enabled (stats words 20-22 match System.map, word 2 of the first stats block "
                              "matches build_id 0x%08x)" % m.build.build_id
                              if m.epc_ok else "REFUSED: " + m.epc_reason))
    if m.build.image_sha256:
        w("- BUILD directory belongs to image sha256 %s (compare with the G3 R3 record in gates/LOG.md)"
          % m.build.image_sha256)
    for n in m.build.notes:
        w("- %s" % n)
    w("\n## `nwords` 7 or 8 (section 17 R-1)\n")
    cnt = {}
    for r in m.P + m.W + m.M:
        if r.get("nw7or8"):
            k = (r["cmd"], F.ORIGIN_NAMES[r["ctx"] & 3])
            cnt[k] = cnt.get(k, 0) + 1
    if cnt:
        w("Records flagged nw7or8 (nwords 7 with rx[14..15] = ff ff: 7 words, or 8 with the 8th 0xFFFF; read as "
          "{7, 8} by every rule): %s.\n" % ", ".join("cmd 0x%02x %s: %d" % (c, o, n) for (c, o), n in sorted(cnt.items())))
    else:
        w("No record is flagged nw7or8.\n")
    w("## Hazard statistics (10.7 step 6)\n")
    per = an.interleave_stats(tmpl)
    w("- Nop straddles of an in-flight thread command, per P-point (hits / harmful): %s"
      % {k: tuple(v) for k, v in per.items()} if per else "- no Nop straddled a thread command")
    hi = sum(1 for r in m.P if an.suspension(r) and A.step_num(an.suspension(r)[0]) >= 13 and r["ms_delta"] > 0)
    w("- LED operations during a thread suspension in the G3-high window (S13..S20): %d commands" % hi)
    gaps = []
    for p in m.POLL:
        a33, a08 = p.get("_p33"), p.get("_p08")
        if a33 is not None and a08 is not None:
            gaps.append(a08["_t0"] - a33["_t1"])
    if gaps:
        gaps.sort()
        w("- G3-low gap (0x33 end to 0x08 start), median %.2f us, min %.2f us (n %d)"
          % (gaps[len(gaps) // 2] / (CPT / 4000.0), gaps[0] / (CPT / 4000.0), len(gaps)))
    kt = sorted(set(s["kupd_last_tick"] for s in m.stats if s["kupd_last_tick"]))
    if kt:
        w("- pdflush wb_kupdate phase (tick mod 1250) of %d observed runs: %s"
          % (len(kt), Counter(t % F.WD_CYCLE for t in kt).most_common(5)))
    late = [p for p in m.POLL if p["c_start"] > CPT - 20000]
    w("- late starts (c_start within ~90 us of the tick end, the P4/P5a exposure): %d polls; wake-up delay "
      "%s, collector part %s, last holders %s" % (len(late), [p["wk_delay"] for p in late[:10]],
                                                  [p["wk_wrk"] for p in late[:10]],
                                                  dict(Counter(F.CLASS_NAMES[p["wk_cls1"] & 7] for p in late))))
    if m.stats:
        s = m.stats[-1]
        w("- costs: p_rec_cost last %d max %d, w_rec_cost_max %d, panel_cost_max %d (Count units); panel paints %d"
          % (s["p_rec_cost_last"], s["p_rec_cost_max"], s["w_rec_cost_max"], s["panel_cost_max"],
             s["panel_paints"]))
    w("\n## Loss at the pull\n")
    dt = max([u["durable_tick"] for u in m.uhb] or [0])
    w("- last durable_tick %d (%.2f s); last tick in the data %d (%.2f s): %.2f s after the last durable point%s"
      % (dt, dt / 250.0, m.t_end // CPT, m.t_end / float(CPT * TPS), (m.t_end // CPT - dt) / 250.0,
         ("; operator pull at stopwatch %s" % times["pull"]) if "pull" in times else ""))
    w("\n## Parsing (10.2-10.5)\n")
    w("- records: %s; exact duplicates removed %d; seq 0xFFFFFFFF dropped %d"
      % ({F.RING_NAMES[r]: len(col.records[r]) for r in range(F.NRINGS)}, col.dup_exact, col.dropped_writing))
    w("- (ring, seq) conflicts: %d%s" % (len(col.conflicts), " (both copies in bad.txt)" if col.conflicts else ""))
    w("- gaps: %d (gaps.txt); chunks rejected %d, other boots %d, above confirmed extent %d (listed, not merged), "
      "unverified salvage records %d" % (len(m.gaps), len(col.bad), len(col.other_boot), len(col.above_extent),
                                         len(col.unverified)))
    if col.only_in_image:
        w("- records found only in the raw image: %d (bad.txt)" % len(col.only_in_image))
    meta = an.meta_repeat()
    w("- META repeated from the S records (4.7): %s" % ("; ".join("sector %d (%s) stuck at tick %d" % x for x in meta)
                                                        if meta else "no stuck metadata sector"))
    for n in col.notes:
        w("- %s" % n)
    for (k, t) in col.anomalies[:30]:
        w("- anomaly (%s): %s" % (k, t))
    for c in m.checks[:30]:
        w("- time check: %s" % c)
    if dict(m.link_flags):
        w("- 16-bit links paired by (tick, Count) instead of value: %s" % dict(m.link_flags))
    w("- per-poll simulation mismatches: %d%s" % (len(an.sim_mismatch), (" e.g. " + "; ".join(
        "POLL %d: %s" % x for x in an.sim_mismatch[:5])) if an.sim_mismatch else ""))
    w("- mouseMode toggles: %s" % ["POLL %d tick %d -> %s (P08 seq %d)" % (t[0], t[1], "ON" if t[2] else "OFF", t[4])
                                    for t in an.toggles[:20]])
    if getattr(an, "stats_decreases", None):
        w("- counter decreases: %s" % an.stats_decreases[:20])
    if a.panel:
        w("\n## Stall panel transcriptions (10.8)\n")
        for spec in a.panel:
            pp = panel_parse(spec, m)
            w("- %s: %s" % (pp["photo"], {k: v for k, v in pp.items() if k not in ("lines",)}))
    w("\n## What the data cannot tell\n")
    w("- registers the code never reads are not observed (row H8 blind spot); 'operator not pressing' is "
      "excluded only by the notes and photo P6 (row H6); N1 and an LED read side effect cannot be separated in "
      "one run (row N1m); a stray store by a kernel-privileged process that hits no guard is not detectable (R16).")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
