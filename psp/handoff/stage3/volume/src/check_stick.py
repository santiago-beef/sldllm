#!/usr/bin/env python3
"""check_stick.py - verify and account the simulated Memory Stick of one volsim run.

Usage: check_stick.py BIGDIR OUTDIR

BIGDIR holds stick/PSCLOG/*.BIN (the Mac-copy view: file bytes up to the size in
the directory entry on the stick), stick/raw/* (every inode's on-stick data) and
produced/ring*_*.bin (every record the simulated kernel produced, in seq order).
OUTDIR holds summary.json from volsim; check.json is written there.

Two independent readings of the stick:
  1. the analyst's decoder parse layer (work/decoder/pscdec_parse.load), as the
     analyst will run it after the hardware run; every decoded record is compared
     field for field with the record the kernel model produced (norm_record of the
     produced bytes); every seq below the kernel's final durable_next must be there;
  2. a chunk walk written here (DESIGN 10.2 framing) for the byte accounting:
     FILEHDR area, every flush (chunks up to and including the PAD that ends it at
     a 512-byte boundary), preallocation PAD sectors (fseq 0xFFFFFFFF), per chunk
     type and per ring.
"""
import glob
import json
import os
import struct
import sys
import zlib

DEC = "/home/ubuntu/psp/work/decoder"
sys.path.insert(0, DEC)
import psc_format as F          # noqa: E402
import pscdec_parse as P        # noqa: E402

HDR = struct.Struct("<4sHHIII")
BLK = struct.Struct("<BBHI")
SEG = 2097152
NAMES = ("PAD", "FILEHDR", "RECS", "STATS", "KMSG", "PROCS", "UHB", "EVENT")


def pad4(n):
    return (n + 3) & ~3


def walk_file(path, nonce, fail_regions=()):
    """Chunk walk of one segment file. Returns a dict of accounting. Sectors that do
    not start a chunk inside a FAILED flush's region (never overwritten, DESIGN 4.6;
    a failed bio can leave some of its later sectors written) are counted apart."""
    b = open(path, "rb").read()
    n = len(b)
    acc = {"name": os.path.basename(path), "size": n, "fh": None, "flushes": [], "prealloc_pad_sectors": 0,
           "bytes_by_type": {k: 0 for k in NAMES}, "chunks_by_type": {k: 0 for k in NAMES},
           "recs_by_ring": [0] * 5, "resend_by_ring": [0] * 5, "block_hdr_bytes": 0, "bad": [],
           "gaps_in_flush_region": 0, "seg_end": 0, "last_sector_pad": False}
    if n < 1536:
        acc["bad"].append("shorter than the FILEHDR area")
        return acc
    m, t, hv, ln, fseq, crc = HDR.unpack_from(b, 0)
    if m == b"PSCK" and t == 1 and zlib.crc32(b[20:20 + ln], 0) & 0xFFFFFFFF == crc:
        fh = struct.unpack_from("<8sIIIIIIIII", b, 20)
        acc["fh"] = {"magic": fh[0].rstrip(b"\0").decode(), "fmt": fh[1], "run": fh[2], "seg": fh[3], "inst": fh[4],
                     "writer_pid": fh[5], "sup_pid": fh[6], "now_tick": fh[7], "nonce": fh[9]}
        acc["bytes_by_type"]["FILEHDR"] += 20 + pad4(ln)
        acc["chunks_by_type"]["FILEHDR"] += 1
        off = 20 + pad4(ln)
        m2, t2, hv2, ln2, fseq2, crc2 = HDR.unpack_from(b, off)
        if m2 == b"PSCK" and t2 == 0 and (off + 20 + pad4(ln2)) == 1536:
            acc["filehdr_area_pad"] = 20 + pad4(ln2)
        else:
            acc["bad"].append("FILEHDR area not FILEHDR + PAD to 1,536")
    else:
        acc["bad"].append("no valid FILEHDR at offset 0")
    off = 1536
    cur = None          # current flush being assembled
    last_flush_end = 1536
    while off + 20 <= n:
        m, t, hv, ln, fseq, crc = HDR.unpack_from(b, off)
        if m != b"PSCK" or t > 7 or hv != 5 or ln > 65536 or off + 20 + pad4(ln) > n:
            if any(a <= off < e for a, e in fail_regions):
                acc["failed_region_unparsed_sectors"] = acc.get("failed_region_unparsed_sectors", 0) + 1
            else:
                acc["bad"].append("no chunk at %d" % off)
            off = (off // 512 + 1) * 512
            cur = None
            continue
        payload = b[off + 20:off + 20 + ln]
        seed = 0 if t == 1 else nonce
        if zlib.crc32(payload, seed) & 0xFFFFFFFF != crc:
            if any(a <= off < e for a, e in fail_regions):
                acc["failed_region_unparsed_sectors"] = acc.get("failed_region_unparsed_sectors", 0) + 1
            else:
                acc["bad"].append("CRC at %d type %s" % (off, NAMES[t]))
            off = (off // 512 + 1) * 512
            cur = None
            continue
        size = 20 + pad4(ln)
        if t == 0 and fseq == 0xFFFFFFFF and ln == 492:
            acc["prealloc_pad_sectors"] += 1
            if cur is not None:
                acc["bad"].append("flush at %d not closed by its PAD" % cur["off"])
                cur = None
            off += size
            continue
        if cur is None:
            cur = {"off": off, "len": 0, "types": {}, "tick": None, "recs": [0] * 5, "resend": [0] * 5}
            if off > last_flush_end:
                acc["gaps_in_flush_region"] += (off - last_flush_end) // 512
        cur["len"] += size
        cur["types"][NAMES[t]] = cur["types"].get(NAMES[t], 0) + size
        acc["bytes_by_type"][NAMES[t]] += size
        acc["chunks_by_type"][NAMES[t]] += 1
        if t == 6 and ln >= 8:
            cur["tick"] = struct.unpack_from("<I", payload, 4)[0]
        if t == 2:
            p = 0
            while p + 8 <= ln:
                ring, div4, cnt, lost = BLK.unpack_from(payload, p)
                r = ring & 0x7F
                p += 8
                acc["block_hdr_bytes"] += 8
                if r < 5:
                    if ring & 0x80:
                        acc["resend_by_ring"][r] += cnt
                        cur["resend"][r] += cnt
                    else:
                        acc["recs_by_ring"][r] += cnt
                        cur["recs"][r] += cnt
                p += cnt * div4 * 4
        off += size
        if t == 0:                                  # PAD closes the flush
            if off % 512:
                acc["bad"].append("flush at %d does not end on a sector" % cur["off"])
            acc["flushes"].append(cur)
            last_flush_end = off
            cur = None
    acc["seg_end"] = last_flush_end
    if n >= 512:
        m, t, hv, ln, fseq, crc = HDR.unpack_from(b, n - 512)
        acc["last_sector_pad"] = (m == b"PSCK" and t == 0 and fseq == 0xFFFFFFFF and ln == 492)
    return acc


def failed_regions(out):
    """'flush fail <seg_end> <len> <errno>' EVENTs (pscol.c:1949-1955) mapped to the
    active file of that tick (ticks.csv). Returns {file name: [(a, b), ...]}."""
    import csv
    act = {}
    with open(os.path.join(out, "ticks.csv")) as f:
        for row in csv.DictReader(f):
            act[int(row["tick"])] = int(row["active"])
    reg = {}
    for line in open(os.path.join(out, "events.log")):
        parts = line.split()
        # "[ t] tick N  flush fail OFF LEN ERRNO"
        if "flush fail" in line:
            i = parts.index("fail")
            tick = int(parts[parts.index("tick") + 1])
            a, ln = int(parts[i + 1]), int(parts[i + 2])
            nnn = act.get(tick, -1)
            reg.setdefault("T%03d%03d.BIN" % (1, nnn), []).append((a, a + ln))
    return reg


def s_ring_check(big, summ):
    """Every S record the kernel model produced: sum of nsect over write records
    against the sectors written, led_ops against the kernel's led_calls."""
    raw = open(glob.glob(os.path.join(big, "produced", "ring3_*.bin"))[0], "rb").read()
    nw = nr = sw = sr = led = err = 0
    for i in range(0, len(raw), 40):
        nsect, flags = raw[i + 24], raw[i + 25]
        led += raw[i + 28]
        if flags & 1:
            nw += 1
            sw += nsect
        else:
            nr += 1
            sr += nsect
        if flags & 2:
            err += 1
    sect_w = sum(v for k, d in summ["sectors"].items() for c, v in d.items() if c != "READ")
    sect_r = sum(d.get("READ", 0) for d in summ["sectors"].values())
    return {"s_write_records": nw, "s_read_records": nr, "sum_nsect_write": sw, "sum_nsect_read": sr,
            "sectors_written": sect_w, "sectors_read": sect_r, "s_error_records": err,
            "sum_led_ops": led, "kernel_led_calls": summ["kernel_led_calls"], "sector_attempts": summ["sector_attempts"],
            "nsect_equals_sectors": sw == sect_w and sr == sect_r,
            "s_count_le_sectors": nw <= sect_w,
            "led_ops_is_2x_attempts": led == 2 * summ["sector_attempts"] == summ["kernel_led_calls"]}


def main():
    big, out = sys.argv[1], sys.argv[2]
    summ = json.load(open(os.path.join(out, "summary.json")))
    fails = failed_regions(out)
    nonce = summ["config"]["nonce"]
    files = sorted(glob.glob(os.path.join(big, "stick", "PSCLOG", "*.BIN")))
    res = {"files": [], "decoder": {}, "records": {}, "accounting": {}}

    # ---- 1. the analyst's decoder parse layer
    col = P.load(files)
    produced = {}
    for r in range(5):
        pth = glob.glob(os.path.join(big, "produced", "ring%d_*.bin" % r))[0]
        raw = open(pth, "rb").read()
        sz = F.RING_RECSIZE[r]
        produced[r] = [raw[i:i + sz] for i in range(0, len(raw), sz)]
    dn = summ["kernel_durable_next"]
    ok = True
    for r in range(5):
        recs = col.records[r]
        prod = produced[r]
        missing = [s for s in range(min(dn[r], len(prod))) if s not in recs]
        beyond = [s for s in recs if s >= dn[r]]
        mism = 0
        first_mism = None
        for s, d in recs.items():
            if s >= len(prod):
                mism += 1
                continue
            want = P.norm_record(r, prod[s])
            got = {k: v for k, v in d.items() if k not in ("_src", "_resend")}   # parser provenance
            if got != want:
                mism += 1
                if first_mism is None:
                    first_mism = (s, {k: (got.get(k), want.get(k)) for k in set(want) | set(got) if got.get(k) != want.get(k)})
        res["records"][F.RING_NAMES[r]] = {
            "produced": len(prod), "kernel_durable_next": dn[r], "decoded": len(recs),
            "missing_below_durable_next": len(missing), "first_missing": missing[:5],
            "decoded_beyond_durable_next": len(beyond), "content_mismatch": mism,
            "first_mismatch": repr(first_mism) if first_mism else None,
            "not_on_stick_at_end": len(prod) - len(recs)}
        ok &= (not missing) and mism == 0
    res["decoder"] = {"run": col.run, "nonce": col.nonce, "nonce_ok": col.nonce == nonce,
                      "conflicts": len(col.conflicts), "dup_exact_removed": col.dup_exact, "bad_chunks": len(col.bad),
                      "other_boot": len(col.other_boot), "above_extent": len(col.above_extent),
                      "block_lost": [list(x[:3]) for x in col.block_lost][:10], "n_block_lost": len(col.block_lost),
                      "uhb": len(col.uhb), "stats": len(col.stats), "events": len(col.events), "kmsg": len(col.kmsg),
                      "procs": len(col.procs), "raw_required": [str(x) for x in col.raw_required],
                      "anomalies": [str(a) for a in col.anomalies][:10], "refused": col.refused}
    ok &= col.nonce == nonce and not col.conflicts and not col.above_extent and not col.refused
    res["records_ok"] = bool(ok)

    # ---- 2. independent chunk walk and byte accounting
    tot = {k: 0 for k in NAMES}
    nchunks = {k: 0 for k in NAMES}
    recs = [0] * 5
    resend = [0] * 5
    blk = 0
    flushes = []
    t0 = summ["config"]["worker_start_s"]
    for p in files:
        a = walk_file(p, nonce, fails.get(os.path.basename(p), ()))
        for k in NAMES:
            tot[k] += a["bytes_by_type"][k]
            nchunks[k] += a["chunks_by_type"][k]
        for r in range(5):
            recs[r] += a["recs_by_ring"][r]
            resend[r] += a["resend_by_ring"][r]
        blk += a["block_hdr_bytes"]
        flushes += [(f["tick"], f["len"], a["name"]) for f in a["flushes"]]
        holds_recs = sum(a["recs_by_ring"]) > 0
        res["files"].append({
            "name": a["name"], "size": a["size"], "complete_2MB": a["size"] == SEG and a["last_sector_pad"],
            "filehdr": a["fh"], "flushes": len(a["flushes"]),
            "flushed_bytes": sum(f["len"] for f in a["flushes"]), "seg_end": a["seg_end"],
            "room_left": a["size"] - a["seg_end"], "prealloc_pad_sectors": a["prealloc_pad_sectors"],
            "gap_sectors_in_flush_region": a["gaps_in_flush_region"], "holds_recs": holds_recs,
            "failed_flush_regions": fails.get(a["name"], []),
            "failed_region_unparsed_sectors": a.get("failed_region_unparsed_sectors", 0),
            "flushes_starting_in_failed_region": sum(1 for f in a["flushes"]
                                                     if any(x <= f["off"] < y for x, y in fails.get(a["name"], ()))),
            "records_by_ring": a["recs_by_ring"], "resent_by_ring": a["resend_by_ring"], "problems": a["bad"][:5]})
    flushed = sum(x[1] for x in flushes)
    dur = summ["end_s"] - t0
    # steady state: flushes whose UHB tick is >= 60 s after worker start (boot backlog drained)
    steady = [x for x in flushes if x[0] is not None and x[0] / 250.0 >= t0 + 60]
    st_t0 = t0 + 60
    st_dur = summ["end_s"] - st_t0
    sizes = {}
    for x in flushes:
        sizes[x[1] // 512] = sizes.get(x[1] // 512, 0) + 1
    payload = {k: tot[k] for k in NAMES}
    rec_bytes = [recs[r] * F.RING_RECSIZE[r] for r in range(5)]
    res_bytes = [resend[r] * F.RING_RECSIZE[r] for r in range(5)]
    procs = [c for c in col.procs] if col.procs else []
    res["accounting"] = {
        "files_on_stick": len(files), "stick_bytes_files": sum(os.path.getsize(p) for p in files),
        "files_holding_records": sum(1 for f in res["files"] if f["holds_recs"]),
        "flushes": len(flushes), "flushed_bytes": flushed, "duration_s": dur,
        "flushed_B_per_s": flushed / dur if dur else 0,
        "steady_flushes": len(steady), "steady_flushed_bytes": sum(x[1] for x in steady),
        "steady_duration_s": st_dur, "steady_B_per_s": sum(x[1] for x in steady) / st_dur if st_dur > 0 else 0,
        "filehdr_area_bytes": 1536 * len(files),
        "bytes_by_chunk_type": tot, "chunks_by_type": nchunks,
        "record_bytes_by_ring": dict(zip(F.RING_NAMES, rec_bytes)),
        "resent_record_bytes_by_ring": dict(zip(F.RING_NAMES, res_bytes)),
        "records_by_ring": dict(zip(F.RING_NAMES, recs)),
        "block_header_bytes": blk,
        "recs_chunk_header_bytes": 20 * nchunks["RECS"],
        "pad_bytes_in_flushes": tot["PAD"], "pad_chunks_in_flushes": nchunks["PAD"],
        "flush_size_sectors_hist": dict(sorted(sizes.items())),
        "procs_chunk_payload_bytes": ([len(x[1]) if isinstance(x, tuple) and len(x) > 1 and isinstance(x[1], (bytes, str)) else None for x in procs[:3]]),
    }
    # PROCS chunk payload sizes straight from the walk (bytes incl. header / count)
    if nchunks["PROCS"]:
        res["accounting"]["procs_avg_chunk_bytes"] = tot["PROCS"] / nchunks["PROCS"]
    if nchunks["STATS"]:
        res["accounting"]["stats_avg_chunk_bytes"] = tot["STATS"] / nchunks["STATS"]
    if nchunks["UHB"]:
        res["accounting"]["uhb_avg_chunk_bytes"] = tot["UHB"] / nchunks["UHB"]
    res["s_ring"] = s_ring_check(big, summ)
    res["walk_problems"] = sum(len(f["problems"]) for f in res["files"])
    json.dump(res, open(os.path.join(out, "check.json"), "w"), indent=1, default=str)

    # ---- print
    a = res["accounting"]
    print("check %s: records_ok=%s  files=%d (%d hold records)  flushes=%d  flushed=%d B  %.1f B/s (steady %.1f B/s)"
          % (summ["name"], res["records_ok"], a["files_on_stick"], a["files_holding_records"], a["flushes"],
             a["flushed_bytes"], a["flushed_B_per_s"], a["steady_B_per_s"]))
    for k, v in res["records"].items():
        print("  ring %-4s produced %6d durable_next %6d decoded %6d missing<dn %d mismatch %d not-on-stick-at-end %d"
              % (k, v["produced"], v["kernel_durable_next"], v["decoded"], v["missing_below_durable_next"],
                 v["content_mismatch"], v["not_on_stick_at_end"]))
    d = res["decoder"]
    print("  decoder: run %s nonce_ok %s conflicts %d dup_exact %d bad %d above_extent %d block_lost %d raw_required %s"
          % (d["run"], d["nonce_ok"], d["conflicts"], d["dup_exact_removed"], d["bad_chunks"], d["above_extent"],
             d["n_block_lost"], d["raw_required"] or "no"))
    for f in res["files"]:
        print("  %-12s %8d B complete=%s seg=%s flushes %4d flushed %8d seg_end %8d gaps %d problems %s"
              % (f["name"], f["size"], f["complete_2MB"], (f["filehdr"] or {}).get("seg"), f["flushes"],
                 f["flushed_bytes"], f["seg_end"], f["gap_sectors_in_flush_region"], f["problems"] or "-"))
    print("  S ring: %s" % res["s_ring"])
    return 0 if res["records_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
