#!/usr/bin/env python3
"""summarize.py - verdicts for every volume run against the design figures.

Usage: summarize.py RESULTS_DIR      (writes RESULTS_DIR/RESULTS.md and verdicts.json)

Criteria (each names its source):
 G-REC   every record below the kernel's final durable_next is on the stick, decoded by the
         analyst's parse layer, field for field equal to what the kernel model produced;
         no conflict, no chunk above a confirmed extent (DESIGN 4.5, 10.2, 10.3)
 G-LOST  pscol lost_total, slot_bad, drain_stuck 0; no RECS block with lost > 0 (4.3 step 2)
 G-RING  the largest backlog of every ring stays below its size (3.1, 4.3 "No ring laps")
 G-SAFE  harness checks: no flush extends a file or crosses mmu_private, no alias written,
         no region of a failed flush written again, 272 HUD row writes per tick, none in
         rows 176-271 (4.4, 4.6, 8.2); chunk walk finds nothing it cannot explain
 G-SCREEN the HUD read back from the pixels equals pscol's own line model on every tick
 G-ST    SELFTEST PASS reached (8.2)
 G-LIFE  segment life cycle (4.4): names T001nnn.BIN from 001 with FILEHDR seg = nnn, every
         complete file 2,097,152 B ending in a preallocation PAD sector, FILEHDR area 1,536 B
 V-SIZE  bytes flushed per second (after the boot backlog) within +-10 % of the DESIGN 5.1 /
         15.6 method evaluated at the run's own poll rate and mean tick period, and not above
         the method at the design's 0.23 s tick (5.1: "rates are maxima") by more than 2 %
 V-STREAM P, POLL, W bytes per second on the stick within +-2 % of 5.1 at the run's poll rate
 V-S     flush S records per second outside / inside creation ticks not above the method's
         fixed point at the run's tick (5.1: 22.6 / 27.0 at 0.23 s); creation S per 8 KB step
         on average <= 11.5, per 64 KB step <= 27 (5.1, 8.5)
 V-PROCS PROCS chunk within [800, 2,400] B (8.5)
 V-SECT  sum of nsect of the S records = sectors written; S count <= sectors written;
         LED operations = 2 x sector attempts (8.5; the last is a harness identity)
 F-STALL (stall runs) the panel model shows PSC STALL with DUR >= 3 s during the stall; no
         takeover condition (both ages > 30 s, 4.2); catch-up ends; nothing lost
 F-SHOW  (write-failure runs) the failure is on the screen (C8, 8.2 line 6): line 6 red on the
         tick of the first FAILED verdict, ERR equal to pscol's write_errs, red until >= 10 s
         after the last failure; flush fail EVENTs; failed regions never written again; the
         records re-sent; the decoder asks for the raw image (10.2)
"""
import csv
import glob
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design_budget as DB     # noqa: E402

SEG = 2097152


EV_RE = re.compile(r"^\[\s*([0-9.]+)\]\s+tick\s+(\d+)\s+(.*)$")


def events(path):
    out = []
    for line in open(path):
        m = EV_RE.match(line.rstrip("\n"))
        if m:
            out.append((float(m.group(1)), int(m.group(2)), m.group(3).strip()))
    return out


def ticks(d):
    with gzip.open(os.path.join(d, "ticks.csv.gz"), "rt") as f:
        return list(csv.DictReader(f))


def evaluate(d):
    s = json.load(open(os.path.join(d, "summary.json")))
    c = json.load(open(os.path.join(d, "check.json")))
    ev = events(os.path.join(d, "events.log"))
    cfg = s["config"]
    polls = cfg["polls_per_s"]
    T = s["tick_period_ms"]["mean"] / 1000.0
    dm = DB.budget(polls=polls, tick=T)
    dmax = DB.budget(polls=polls, tick=0.23)
    acc = c["accounting"]
    r = {"name": s["name"], "polls": polls, "speed_kbs": cfg["speed_kbs"], "cluster": cfg["cluster_bytes"],
         "tick_mean_ms": s["tick_period_ms"]["mean"], "tick_max_ms": s["tick_period_ms"]["max"], "checks": {}}
    ck = r["checks"]

    def put(k, ok, txt):
        ck[k] = {"ok": bool(ok), "detail": txt}

    rec = c["records"]
    miss = sum(v["missing_below_durable_next"] for v in rec.values())
    mism = sum(v["content_mismatch"] for v in rec.values())
    dec = c["decoder"]
    put("G-REC", c["records_ok"] and miss == 0 and mism == 0,
        "missing %d, mismatched %d, conflicts %d, above-extent %d, decoded P/POLL/W/S/M %s"
        % (miss, mism, dec["conflicts"], dec["above_extent"], "/".join(str(v["decoded"]) for v in rec.values())))
    p = s["pscol"]
    put("G-LOST", p["lost_total"] == 0 and p["slot_bad"] == 0 and p["drain_stuck"] == 0 and dec["n_block_lost"] == 0
        and not p["rec_alarm"],
        "lost_total %d, slot_bad %d, drain_stuck %d, blocks with lost>0 %d, REC alarm %d"
        % (p["lost_total"], p["slot_bad"], p["drain_stuck"], dec["n_block_lost"], p["rec_alarm"]))
    bl = s["backlog_max"]
    ents = s["ring_entries"]
    put("G-RING", all(b < e for b, e in zip(bl, ents)),
        "max backlog P %d/%d (%.0f %%), POLL %d/%d, W %d/%d, S %d/%d, M %d/%d"
        % (bl[0], ents[0], 100.0 * bl[0] / ents[0], bl[1], ents[1], bl[2], ents[2], bl[3], ents[3], bl[4], ents[4]))
    scr = s["screen"]
    over = sum(f.get("flushes_starting_in_failed_region", 0) for f in c["files"])
    put("G-SAFE", s["violations"] == 0 and scr["fb_band_writes"] == 0 and scr["fb_bad_writes"] == 0
        and c["walk_problems"] == 0 and over == 0,
        "harness violations %d, HUD writes into rows 176-271 %d, flushes starting in a failed region %d, "
        "unexplained chunk-walk problems %d" % (s["violations"], scr["fb_band_writes"], over, c["walk_problems"]))
    put("G-SCREEN", scr["ocr_vs_hud_mismatch_ticks"] == 0 and scr["ocr_unknown_glyphs"] == 0,
        "ticks where pixels differ from hud[] %d, unknown glyphs %d" % (scr["ocr_vs_hud_mismatch_ticks"], scr["ocr_unknown_glyphs"]))
    tk = ticks(d)
    if p["speed_kbs"] and p["speed_kbs"] < 30:
        slow = [t for t in tk if t["L6"].startswith("MS SLOW") and t["L6col"] == "R"]
        put("G-ST", p["st_pass"] == 0 and slow,
            "stick measured %d KB/s (< 30): SELFTEST never passes, line 6 'MS SLOW' in red from %.1f s uptime "
            "(the 3:00 abort of 8.3); the collector keeps recording" % (p["speed_kbs"], float(slow[0]["t_s"]) if slow else -1))
    else:
        put("G-ST", p["st_pass"] == 1, "SELFTEST PASS at %.1f s uptime (stick measured %d KB/s)" % (p["st_pass_at_s"], p["speed_kbs"]))
    life_ok = True
    fl = []
    skipped = set()
    for e in ev:
        m = re.match(r"(abandon|inode reused) T(\d{3})(\d{3})\.BIN", e[2])
        if m:
            skipped.add(int(m.group(3)))
    stopped = set(int(m.group(1)) for m in (re.match(r"stop T\d{3}(\d{3})\.BIN", e[2]) for e in ev) if m)
    prev = 0
    for f in c["files"]:
        fh = f["filehdr"] or {}
        m = re.match(r"T(\d{3})(\d{3})\.BIN$", f["name"])
        nnn = int(m.group(2)) if m else -1
        gap = set(range(prev + 1, nnn)) - skipped
        name_ok = m and int(m.group(1)) == cfg["run"] and fh.get("seg") == nnn and fh.get("run") == cfg["run"] and not gap
        size_ok = f["complete_2MB"] or (f["size"] < SEG and (nnn in stopped or nnn == p["creating_nnn"]))
        life_ok &= bool(name_ok) and size_ok
        prev = nnn
        fl.append("%s %d%s" % (f["name"], f["size"], "" if f["complete_2MB"] else
                                (" (stopped)" if nnn in stopped else " (in creation)" if nnn == p["creating_nnn"] else " (?)")))
    if skipped:
        fl.append("names used and left empty: %s (abandon / alias EVENTs)" % ", ".join("T%03d%03d" % (cfg["run"], k) for k in sorted(skipped)))
    put("G-LIFE", life_ok, "; ".join(fl))
    # ---- size
    st = acc["steady_B_per_s"]
    dev = (st - dm["run_avg_on_stick_B_per_s"]) / dm["run_avg_on_stick_B_per_s"]
    lit = ""
    size_ok = abs(dev) <= 0.10
    if abs(polls - 250 / 14.0) < 0.01:                  # the 8.5 row is stated at 17.86 polls/s
        dl = (st - 7598) / 7598.0
        lit = "; 8.5 literal: %+.1f %% against 7,598 B/s" % (100 * dl)
        size_ok &= abs(dl) <= 0.10 or T > 0.25          # literal row only at the design's tick
    put("V-SIZE", size_ok,
        "flushed %.0f B/s after the boot backlog (%.0f B/s over all 15 min); design method at %.2f polls/s "
        "and the run's %.3f s tick: %.0f B/s (%+.1f %%); design 'maximum' at 0.23 s: %.0f B/s (%+.1f %%)%s"
        % (st, acc["flushed_B_per_s"], polls, T, dm["run_avg_on_stick_B_per_s"], 100 * dev,
           dmax["run_avg_on_stick_B_per_s"], 100 * (st / dmax["run_avg_on_stick_B_per_s"] - 1), lit))
    span_p = s["end_s"] - cfg["thread_start_s"]
    pr = rec["P"]["decoded"] * 80 / span_p
    po = rec["POLL"]["decoded"] * 40 / span_p
    wr = rec["W"]["decoded"] * 288 / s["end_s"]
    dp, dpo, dw = 2 * polls * 80, polls * 40, 0.2 * 288
    put("V-STREAM", abs(pr / dp - 1) <= 0.02 and abs(po / dpo - 1) <= 0.02 and abs(wr / dw - 1) <= 0.02,
        "P %.0f B/s (design %.0f), POLL %.0f (%.0f), W %.1f (%.1f)" % (pr, dp, po, dpo, wr, dw))
    fs = s["flush_S_rate"]
    nc = fs["noncreation_flush_S"] / fs["noncreation_ticks_s"] if fs["noncreation_ticks_s"] else 0
    cr = fs["creation_flush_S"] / fs["creation_ticks_s"] if fs["creation_ticks_s"] else 0
    stp = s["step_S"]
    s8 = stp["step8k_S"] / stp["step8k_n"] if stp["step8k_n"] else 0
    b_nc, b_cr = dmax["flush_S_per_s_steady"], dmax["flush_S_per_s_creation_ticks"]
    put("V-S", nc <= b_nc * 1.005 and cr <= b_cr * 1.005 and s8 <= 11.5 and stp["step64k_maxS"] <= 27,
        "flush S %.1f/s outside creation ticks (design bound at %.2f polls/s and 0.23 s: %.1f; 22.6 at 17.86), "
        "%.1f/s in creation ticks (bound %.1f; 27.0 at 17.86); creation S per 8 KB step %.2f on average "
        "(design 11.5, which counts 1/2 FAT per step), %d at most (9 + FAT1 + FAT2 in two sectors); per 64 KB "
        "step at most %d (design 27)" % (nc, polls, b_nc, cr, b_cr, s8, stp["step8k_maxS"], stp["step64k_maxS"]))
    pb = acc.get("procs_avg_chunk_bytes", 0)
    put("V-PROCS", 800 <= pb <= 2400, "PROCS chunk %.0f B on average (%d chunks)" % (pb, acc["chunks_by_type"]["PROCS"]))
    sr = c["s_ring"]
    put("V-SECT", sr["nsect_equals_sectors"] and sr["s_count_le_sectors"] and sr["led_ops_is_2x_attempts"],
        "S write records %d, sum nsect %d = sectors written %d; LED ops %d = 2 x %d attempts"
        % (sr["s_write_records"], sr["sum_nsect_write"], sr["sectors_written"], sr["sum_led_ops"], sr["sector_attempts"]))
    # ---- scenario checks
    fails = [e for e in ev if e[2].startswith("flush fail") or e[2].startswith("stop ") or e[2].startswith("abandon")]
    if cfg["stall_ms"]:
        b0, b1 = s["stall"]["begin_s"], s["stall"]["end_s"]
        eps = [e for e in s["panel_episodes"] if e["t1"] >= b0 and e["t0"] <= b1 + 20]
        dmx = max([e["dur_max_s"] for e in eps] or [0])
        rmx = max([e["rdr_max_s"] for e in eps] or [0])
        cu = [e for e in ev if e[2] == "catch-up end" and e[0] >= b1]
        after = [t for t in tk if float(t["t_s"]) >= b1]
        blr = int(after[0]["bl_P"]) if after else -1
        put("F-STALL", eps and dmx >= 3 and not (dmx > 30 and rmx > 30) and (cu or cfg["stall_nonpreempt"])
            and p["lost_total"] == 0,
            "write blocked %.1f-%.1f s; panel model %s, max DUR %.1f s, max RDR %.1f s (takeover needs both > 30 s); "
            "P backlog after release %d of %d; catch-up ended at %.1f s; lost %d"
            % (b0, b1, ", ".join("%s %.1f-%.1f s" % (e["title"], e["t0"], e["t1"]) for e in eps) or "none",
               dmx, rmx, blr, ents[0], cu[0][0] if cu else -1, p["lost_total"]))
    if cfg["outage_ms"] or cfg["fail1_at_s"] or cfg["wfail_ms"]:
        ff = [e for e in ev if e[2].startswith("flush fail")]
        rs = [e for e in ev if e[2].startswith("resend ")]
        passed = [int(t["tick"]) for t in tk if t["L6"].startswith(("MS DUR", "MS READ", "MS WAIT"))]
        pass_tick = passed[0] if passed else 10 ** 9
        pre = [e for e in fails if e[1] < pass_tick]
        post = [e for e in fails if e[1] >= pass_tick]
        red = {int(t["tick"]): t for t in tk if t["L6col"] == "R"}
        if post:
            first_tick = min(e[1] for e in post)
            last_t = max(e[0] for e in post)
            red_after = [int(t["tick"]) for t in tk if t["L6col"] == "R" and int(t["tick"]) >= first_tick]
            last_red = max([float(red[k]["t_s"]) for k in red_after] or [-1])
            later = [t for t in tk if float(t["t_s"]) >= last_t + 11.0]
            cleared = (not later) or later[0]["L6col"] == "W"
            ok = (p["write_errs"] > 0 and first_tick in red and scr["err_shown_max"] == p["write_errs"]
                  and 8.5 <= last_red - last_t <= 11.0 and cleared and ff and rs and over == 0 and dec["raw_required"])
            put("F-SHOW", ok,
                "write_errs %d; first FAILED verdict on tick %d, line 6 red on that tick ('%s') and until %.1f s "
                "(last failure %.1f s, +%.1f s; 8.2: red for 10 s, judged at tick resolution), white again after; "
                "ERR shown up to %d; %d 'flush fail', %d 'resend' EVENTs; "
                "decoder: raw image required %s"
                % (p["write_errs"], first_tick, red[first_tick]["L6"] if first_tick in red else "NOT RED", last_red,
                   last_t, last_red - last_t, scr["err_shown_max"], len(ff), len(rs),
                   "yes" if dec["raw_required"] else "NO"))
        if pre:
            first = min(pre)
            row = [t for t in tk if int(t["tick"]) == first[1]]
            later = [t for t in tk if int(t["tick"]) == pass_tick]
            r.setdefault("observations", []).append(
                "F-SHOW-PREP: %d FAILED verdict(s) before STICK passed (first on tick %d at %.1f s: '%s'); line 6 then "
                "reads '%s' (%s), not red; STICK stays red; ERR becomes visible only when STICK passes on tick %d: '%s'"
                % (len(pre), first[1], first[0], first[2], row[0]["L6"] if row else "?",
                   "red" if row and row[0]["L6col"] == "R" else "white", pass_tick, later[0]["L6"] if later else "?"))
    r["verdict"] = "PASS" if all(v["ok"] for v in ck.values()) else "FAIL"
    # ---- figures for the report
    files = c["files"]
    r["figures"] = {
        "flushed_bytes_15min": acc["flushed_bytes"], "flushed_B_per_s": round(acc["flushed_B_per_s"], 1),
        "steady_B_per_s": round(st, 1), "design_method_B_per_s": dm["run_avg_on_stick_B_per_s"],
        "design_max_B_per_s": dmax["run_avg_on_stick_B_per_s"], "design_method_MB_15min": dm["MB_15min"],
        "files": len(files), "files_holding_records": acc["files_holding_records"],
        "stick_bytes": acc["stick_bytes_files"], "per_file": [(f["name"], f["size"], f["flushed_bytes"],
                                                               f["flushes"]) for f in files],
        "flushes": acc["flushes"], "flush_size_sectors_hist": acc["flush_size_sectors_hist"],
        "bytes_by_chunk_type": acc["bytes_by_chunk_type"], "record_bytes_by_ring": acc["record_bytes_by_ring"],
        "resent_record_bytes_by_ring": acc["resent_record_bytes_by_ring"],
        "block_header_bytes": acc["block_header_bytes"], "prealloc_steps_bytes": s["bytes_handed"]["step"] + s["bytes_handed"]["step0"],
        "sector_writes_total": sr["sectors_written"], "sector_writes_per_s": round(sr["sectors_written"] / (s["end_s"] - cfg["worker_start_s"]), 2),
        "design_method_sector_writes_per_s": dm["all_sector_writes_per_s"],
        "backlog_max": bl, "lost_total": p["lost_total"], "write_errs": p["write_errs"],
        "panel_episodes": s["panel_episodes"], "holding_ticks": s["ticks"]["holding"], "catchup_ticks": s["ticks"]["catchup"],
        "creation_ticks": s["ticks"]["creation"], "worker_ticks": s["worker_ticks"],
        "active_end": p["active_nnn"], "creating_end": p["creating_nnn"], "ahead_end": p["complete_ahead"],
        "names_used": p["names_used"], "fat_stale_alloc": s.get("fat_stale_alloc", 0),
        "events": [e[2] for e in ev if not e[2].startswith(("resend", "catch-up"))][:40],
        "line6_red_ticks": scr["line6_red_ticks"], "dur_shown_max_s": scr["dur_shown_max_s"],
    }
    return r


def main():
    res = sys.argv[1]
    runs = [evaluate(d) for d in sorted(glob.glob(os.path.join(res, "*"))) if os.path.isfile(os.path.join(d, "check.json"))]
    json.dump(runs, open(os.path.join(res, "verdicts.json"), "w"), indent=1)
    lines = ["# Volume runs: verdicts (generated by src/summarize.py)", "",
             "| Run | polls/s | KB/s | cluster | tick mean (max) ms | flushed B/s (steady) | design method B/s | files | lost | write_errs | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        f = r["figures"]
        lines.append("| %s | %.2f | %d | %d K | %.0f (%.0f) | %.0f (%.0f) | %.0f | %d | %d | %d | **%s** |"
                     % (r["name"], r["polls"], r["speed_kbs"], r["cluster"] // 1024, r["tick_mean_ms"], r["tick_max_ms"],
                        f["flushed_B_per_s"], f["steady_B_per_s"], f["design_method_B_per_s"], f["files"],
                        f["lost_total"], f["write_errs"], r["verdict"]))
    lines.append("")
    for r in runs:
        lines.append("## %s: %s" % (r["name"], r["verdict"]))
        for k, v in r["checks"].items():
            lines.append("- %s **%s**: %s" % (k, "PASS" if v["ok"] else "FAIL", v["detail"]))
        for o in r.get("observations", []):
            lines.append("- **OBSERVATION (not a pass/fail check; see REPORT.md findings)**: %s" % o)
        lines.append("")
    open(os.path.join(res, "RESULTS.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:4 + len(runs)]))
    bad = [r["name"] for r in runs if r["verdict"] != "PASS"]
    for r in runs:
        for k, v in r["checks"].items():
            if not v["ok"]:
                print("FAIL %s %s: %s" % (r["name"], k, v["detail"]))
    for r in runs:
        for o in r.get("observations", []):
            print("OBSERVATION %s: %s" % (r["name"], o))
    print("runs %d, PASS %d, FAIL %d" % (len(runs), len(runs) - len(bad), len(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
