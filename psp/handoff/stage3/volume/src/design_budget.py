#!/usr/bin/env python3
"""design_budget.py - the DESIGN 5.1 / 15.6 budget method, with parameters.

DESIGN.md 5.1 (and design/r5-scripts/budget_r5.py, which produced it) fixes the
poll rate at 250/14 = 17.86/s and the collector tick at 0.23 s (4.35/s, "rates
are maxima"). This file repeats that method step for step with the poll rate,
the tick period, the S records per creation step and the cluster size as
parameters, so the design's arithmetic can be evaluated at the conditions a
simulation actually ran under. It first checks that, at the design's own
parameters, it reproduces the published figures (5.1: 5,887 steady payload,
1,227/2,015/3,171 B flushes, 7,123 / 9,350 / 7,598 B/s on the stick, 6.8 MB in
15 minutes; 15.6: unchanged). The fixed point for the flush S rate (5.1: "3.2
data sectors per tick; S <= data + directory entry + FSINFO = 5.2 per tick =
22.6/s") is solved, not typed in.

Usage: design_budget.py [polls_per_s tick_s [step_S cluster_bytes]]   (prints JSON)
"""
import json
import math
import sys

SC, W, PO, S = 80, 288, 40, 40
SEG = 2097152
UHB_CHUNK = 20 + 84
STATS_CHUNK = 20 + 768
PROCS_CHUNK = 1156          # 5.1 "PROCS chunk ... ~1,156"


def pad(b):
    return max(1536, (int(math.ceil(b)) + 511) // 512 * 512)    # budget_r5.py


def budget(polls=250 / 14, tick=0.23, step_S=11.5, cl=32768, creation_flush_S=None):
    tps = 1.0 / tick
    P = 2 * polls
    Wr = 250 / 1250

    def flush_sizes(nom):
        return [pad(nom)] * 35 + [pad(nom + 788)] * 4 + [pad(nom + 788 + PROCS_CHUNK)]

    def rates(sflush):
        return {"P": P * SC, "POLL": polls * PO, "W": Wr * W, "S": sflush * S,
                "RECS hdr": tps * (20 + 5 * 8), "UHB": tps * UHB_CHUNK, "STATS": tps / 8 * STATS_CHUNK,
                "PROCS": tps / 40 * PROCS_CHUNK, "PAD hdr": tps * 20}

    # steady flush S fixed point: S/s = (data sectors per flush + dir + FSINFO) * ticks/s
    sflush = 22.6
    for _ in range(100):
        rt = rates(sflush)
        payload = sum(rt.values())
        nom = (payload - rt["STATS"] - rt["PROCS"]) / tps
        avg = sum(flush_sizes(nom)) / 40.0
        new = (avg / 512 + 2) * tps
        if abs(new - sflush) < 1e-9:
            break
        sflush = new
    rt = rates(sflush)
    payload = sum(rt.values())
    nom = (payload - rt["STATS"] - rt["PROCS"]) / tps
    avg = sum(flush_sizes(nom)) / 40.0
    # creation ticks: the flush also carries the creation step's S records
    cflush = creation_flush_S if creation_flush_S is not None else sflush
    for _ in range(100):
        cnom = nom + (cflush - sflush) * S / tps + step_S * S
        cavg = sum(flush_sizes(cnom)) / 40.0
        new = (cavg / 512 + 2) * tps
        if creation_flush_S is not None or abs(new - cflush) < 1e-9:
            break
        cflush = new
    cnom = nom + (cflush - sflush) * S / tps + step_S * S
    cavg = sum(flush_sizes(cnom)) / 40.0
    steps_per_file = 256                    # 8 KB steps per 2 MB file
    frac = 0.213
    for _ in range(100):
        ticks_per_file = (SEG - 1536) / (avg * (1 - frac) + cavg * frac)
        new = steps_per_file / ticks_per_file
        if abs(new - frac) < 1e-12:
            break
        frac = new
    oavg = (1 - frac) * avg + frac * cavg
    run_payload = payload + frac * ((cflush - sflush) * S + step_S * S * tps)
    on = oavg * tps
    fat_writes = 2 * (SEG // cl)            # FAT1 + mirror per cluster
    cw = 4096 + 256 * 2 + fat_writes
    life = ticks_per_file * tick
    sw = (avg / 512 + 2) * tps * (1 - frac) + (cavg / 512 + 2) * tps * frac
    out = {
        "params": {"polls_per_s": polls, "tick_s": tick, "ticks_per_s": tps, "step_S": step_S, "cluster": cl},
        "stream_B_per_s": {k: round(v, 1) for k, v in rt.items()},
        "flush_S_per_s_steady": round(sflush, 2), "flush_S_per_s_creation_ticks": round(cflush, 2),
        "steady_payload_B_per_s": round(payload, 1),
        "flush_nominal_B": round(nom), "flush_with_STATS_B": round(nom + 788),
        "flush_with_STATS_PROCS_B": round(nom + 788 + PROCS_CHUNK),
        "padded_avg_flush_B": avg, "data_sectors_per_tick": avg / 512,
        "on_stick_steady_B_per_s": round(avg * tps, 1), "on_stick_creation_ticks_B_per_s": round(cavg * tps, 1),
        "creation_tick_fraction": round(frac, 4), "run_avg_payload_B_per_s": round(run_payload, 1),
        "run_avg_on_stick_B_per_s": round(on, 1), "file_life_s": round(life, 1),
        "MB_15min": round(on * 900 / 1e6, 3), "MB_30min": round(on * 1800 / 1e6, 3),
        "files_15min": math.ceil(on * 900 / (SEG - 1536)),
        "creation_sector_writes_per_file": cw, "creation_sector_writes_per_s": round(cw / life, 2),
        "flush_sector_writes_per_s": round(sw, 2), "all_sector_writes_per_s": round(sw + cw / life, 2),
    }
    return out


def selfcheck():
    """At the design's own parameters the method must give the published numbers."""
    d = budget(creation_flush_S=27.0)
    want = [("steady_payload_B_per_s", 5887, 1), ("flush_nominal_B", 1227, 1), ("flush_with_STATS_B", 2015, 1),
            ("flush_with_STATS_PROCS_B", 3171, 1), ("on_stick_steady_B_per_s", 7123, 1),
            ("on_stick_creation_ticks_B_per_s", 9350, 1), ("run_avg_on_stick_B_per_s", 7598, 1),
            ("run_avg_payload_B_per_s", 6351, 1), ("MB_15min", 6.84, 0.01), ("files_15min", 4, 0),
            ("creation_sector_writes_per_file", 4736, 0), ("all_sector_writes_per_s", 40.7, 0.1)]
    ok = True
    rows = []
    for k, v, tol in want:
        got = d[k]
        good = abs(got - v) <= tol
        ok &= good
        rows.append((k, v, got, good))
    fp = budget()                         # creation-tick S solved as a fixed point too
    return ok, rows, d, fp


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        a = [float(x) for x in sys.argv[1:]]
        kw = {"polls": a[0], "tick": a[1]}
        if len(a) >= 3:
            kw["step_S"] = a[2]
        if len(a) >= 4:
            kw["cl"] = int(a[3])
        print(json.dumps(budget(**kw), indent=1))
    else:
        ok, rows, d, fp = selfcheck()
        for k, v, got, good in rows:
            print("%-34s design %-8s method %-10s %s" % (k, v, got, "OK" if good else "DIFFERS"))
        print("selfcheck", "PASS" if ok else "FAIL")
        print("with the creation-tick S rate solved as a fixed point instead of 27.0: run avg %.1f B/s, "
              "creation-tick S %.2f/s" % (fp["run_avg_on_stick_B_per_s"], fp["flush_S_per_s_creation_ticks"]))
        sys.exit(0 if ok else 1)
