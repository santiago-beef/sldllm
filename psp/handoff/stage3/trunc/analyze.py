#!/usr/bin/env python3
"""analyze.py - Stage 3 TRUNCATION: tables from the per-cut logs
(logs/trunc-<dump>.tsv.gz written by trunc_test.py run).  Output on stdout
(saved as logs/trunc-summary.txt)."""
import collections
import csv
import gzip
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trunc_test as T  # noqa: E402

LOGS = T.LOGS
csv.field_size_limit(1 << 24)


def ints(r, *ks):
    return [int(r[k]) if r.get(k) not in (None, "") else 0 for k in ks]


def main():
    grand = collections.Counter()
    print("# Stage 3 TRUNCATION: per-cut results\n")
    for sp in T.DUMP_SPECS:
        name = sp["name"]
        path = os.path.join(LOGS, "trunc-%s.tsv.gz" % name)
        if not os.path.exists(path):
            print("%s: no log" % name)
            continue
        d = T.Dump(sp)
        # last non-PAD payload end per file (TRUNC: data lost iff the cut is below it)
        last_data = {}
        for k, ft in enumerate(d.files):
            ends = [ch["pend"] for ch in ft.chunks if ch["type"] != 0]
            last_data[k] = max(ends) if ends else 0
        rows = csv.DictReader(gzip.open(path, "rt"), delimiter="\t")
        agg = collections.OrderedDict()
        none_pos = collections.Counter()
        anom_pos = collections.Counter()
        phantoms = collections.Counter()
        crashes = []
        listed_cases = collections.Counter()
        for r in rows:
            key = (r["model"], r["tier"])
            a = agg.setdefault(key, collections.Counter())
            a["cuts"] += 1
            grand["cuts"] += 1
            grand["cuts_" + r["tier"]] += 1
            if r["crash"] == "1":
                a["crash"] += 1
                grand["crash"] += 1
                crashes.append((r["model"], r["k"], r["cut"], r["trace"][:300]))
                continue
            miss, diff, refdiff, extra, sm, se, fhm = ints(r, "miss", "diff", "refdiff", "extra", "side_miss",
                                                            "side_extra", "fh_miss")
            ph = r["phantom"]
            b = miss == 0 and diff == 0 and refdiff == 0 and extra == 0 and sm == 0 and fhm == 0 and \
                (se == 0 or ph)
            if r["tier"] == "F":
                cm, cd, cx, ch, sr, rcc = ints(r, "csv_miss", "csv_diff", "csv_extra", "csv_hdr",
                                               "side_rows_not_in_uncut", "rc_consistent")
                b = b and cm == 0 and cd == 0 and cx == 0 and ch == 0 and (sr == 0 or ph) and rcc == 1
                a["rc%s" % r["rc"]] += 1
            a["b_ok"] += int(b)
            a["b_fail"] += int(not b)
            ev, el, lm = ints(r, "exp_ver", "exp_listed", "listed_miss")
            a["rec_checked"] += ev
            grand["rec_checked"] += ev
            a["listed_exp"] += el
            a["listed_miss"] += lm
            if el:
                a["cuts_with_listed"] += 1
                a["cuts_listed_all_missing"] += int(lm == el)
                listed_cases[(r["model"], lm == 0)] += 1
            if ph:
                a["phantom"] += 1
                for x in ph.split(";"):
                    phantoms[(r["model"], x.split("@")[0])] += 1
            sig = r["signal"].split(",") if r["signal"] else []
            if r["na"]:
                a["c_NA"] += 1
                continue
            a["c_required"] += 1
            k = int(r["k"])
            cut = int(r["cut"])
            if "explicit" in sig:
                a["c_explicit"] += 1
            elif "refused" in sig:
                a["c_refused"] += 1
            elif "size" in sig:
                a["c_size"] += 1
            elif "size-also-uncut" in sig:
                lost = r["model"] == "TRUNC" and cut < last_data[k]
                a["c_size_also_uncut"] += 1
                a["c_size_also_uncut_datalost" if lost else "c_size_also_uncut_padonly"] += 1
            elif "anomaly" in sig:
                a["c_anomaly"] += 1
                anom_pos[(r["model"], r["pos"])] += 1
            else:
                lost = (cut < last_data[k]) if r["model"] == "TRUNC" else True
                a["c_none"] += 1
                a["c_none_datalost" if lost else "c_none_nothinglost"] += 1
                none_pos[(r["model"], r["pos"], "data lost" if lost else "nothing lost")] += 1
        print("## %s (%s)\n" % (name, sp["what"]))
        print("files: %s" % ", ".join("%s %d B (written %d, %d records)" % (ft.name, ft.size, ft.written_end,
                                                                           len(ft.records)) for ft in d.files))
        cols = ["cuts", "crash", "b_ok", "b_fail", "rec_checked", "cuts_with_listed", "listed_exp", "listed_miss",
                "cuts_listed_all_missing", "c_required", "c_explicit", "c_refused", "c_size", "c_size_also_uncut",
                "c_size_also_uncut_datalost", "c_size_also_uncut_padonly", "c_anomaly", "c_none",
                "c_none_datalost", "c_none_nothinglost", "c_NA", "phantom", "rc0", "rc2", "rc3"]
        print("\n| model/tier | " + " | ".join(cols) + " |")
        print("|---|" + "---|" * len(cols))
        for key, a in agg.items():
            print("| %s/%s | " % key + " | ".join(str(a.get(c, 0)) for c in cols) + " |")
            for c in cols:
                grand[c] += a.get(c, 0) if c not in ("cuts", "crash", "rec_checked") else 0
        if none_pos:
            print("\nNo statement (c none), by position: %s" % dict(sorted(none_pos.items())))
        if anom_pos:
            print("Anomaly only, by position: %s" % dict(sorted(anom_pos.items())))
        if phantoms:
            print("Phantom chunks: %s" % dict(sorted(phantoms.items())))
        if crashes:
            print("CRASHES (first 5): %s" % crashes[:5])
        print()
    print("## Totals\n\n%s" % dict(grand))


if __name__ == "__main__":
    main()
