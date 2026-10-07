#!/usr/bin/env python3
"""probe_phantom.py - Stage 3 TRUNCATION, targeted probe (finding T-2 / T-3).

A chunk header that begins on a 512-byte sector boundary and is torn after
its type field (bytes 5..8 written, the rest still the preallocation PAD
sector, DESIGN 4.4 step 3) leaves: magic 'PSCK', the new type, hver 5,
len 492, fseq 0xFFFFFFFF and the PAD sector's CRC over 492 zero bytes. The
CRC covers only the payload (DESIGN 10.2), so the decoder accepts a chunk
of the new type with 492 zero bytes ("phantom").

Part 1 (reachable): the real tear, in the OVERLAY model, 5..8 bytes into
the header of the first RECS chunk of a tick flush of pscol-short.
Part 2 (synthetic, every type): the same header bytes planted at the first
preallocation sector above the written extent of pscol-short, decoded by the
parse layer and by the whole program.
Part 3: which chunk types the two writers ever start on a sector boundary
(precondition of part 1), over all six dumps.

The decoder (work/decoder) is imported read-only; nothing is modified.
"""
import collections
import io
import os
import shutil
import struct
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/psp/work/decoder")
import oracle as O            # noqa: E402
import pscdec_parse as P      # noqa: E402
import pscdec                 # noqa: E402
import trunc_test as T        # noqa: E402

BUILD = "/home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD"
SRC = os.path.join(HERE, "dumps/pscol-short/PSCLOG/T001001.BIN")


def decode(data, tmp):
    d = os.path.join(tmp, "PSCLOG")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(d)
    with open(os.path.join(d, "T001001.BIN"), "wb") as f:
        f.write(data)
    out = {}
    try:
        col = P.load([os.path.join(d, "T001001.BIN")])
        out["parse"] = "ok"
        out["col"] = col
    except Exception as e:
        out["parse"] = "EXCEPTION %s: %s at %s" % (type(e).__name__, e,
                                                    traceback.extract_tb(e.__traceback__)[-2:])
    so = sys.stdout
    sys.stdout = io.StringIO()
    try:
        out["rc"] = pscdec.main(["-o", os.path.join(tmp, "out"), "--build", BUILD, d])
    except Exception as e:
        out["rc"] = "EXCEPTION %s" % type(e).__name__
    finally:
        sys.stdout = so
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="phantom-", dir="/dev/shm")
    ft = O.FileTruth("T001001.BIN", open(SRC, "rb").read())
    print("input %s (%d bytes, written extent %d)" % (SRC, ft.size, ft.written_end))
    print("\n== Part 1: OVERLAY tear inside the header of a tick flush's first chunk (RECS)")
    rc0 = [c for c in ft.chunks if c["type"] == 2][3]
    f0 = rc0["off"]
    for k in range(0, 21):
        cut = f0 + k
        data = ft.data[:cut] + ft.preimage(cut, ft.size)
        r = decode(data, tmp)
        col = r.get("col")
        g = [(c.name, c.length) for c in col.sources[0].good if c.off == f0] if col else "-"
        bad = [(c.status) for c in col.bad if c.off == f0] if col else "-"
        an = [t for (_k, t) in col.anomalies if "@%d" % f0 in t] if col else "-"
        print("  cut flush+%2d: accepted at %d %s; rejected %s; anomaly %s; exit %s"
              % (k, f0, g, bad, an, r["rc"]))
    print("\n== Part 2: phantom of each type planted at the first preallocation sector (offset %d)" % ft.written_end)
    for t in range(1, 8):
        data = bytearray(ft.data)
        struct.pack_into("<H", data, ft.written_end + 4, t)
        r = decode(bytes(data), tmp)
        col = r.get("col")
        if col:
            g = [(c.name, c.length) for c in col.sources[0].good if c.off == ft.written_end]
            print("  type %d %-7s parse ok, accepted %s, uhb %d stats %d event lines %d kmsg %d procs %d, "
                  "anomalies %s, exit %s" % (t, O.NAMES[t], g, len(col.uhb), len(col.stats), len(col.events),
                                             len(col.kmsg), len(col.procs),
                                             [x for (_k, x) in col.anomalies][:1], r["rc"]))
        else:
            print("  type %d %-7s parse %s; exit %s" % (t, O.NAMES[t], r["parse"], r["rc"]))
    print("\n== Part 3: chunks that start on a 512-byte sector boundary (tick flushes and FILEHDR), all dumps")
    tot, al = collections.Counter(), collections.Counter()
    for sp in T.DUMP_SPECS:
        d = T.Dump(sp)
        for f in d.files:
            for ch in f.chunks:
                if ch["type"] == 0 and ch["fseq"] == 0xFFFFFFFF:
                    continue
                tot[ch["name"]] += 1
                if ch["off"] % 512 == 0:
                    al[ch["name"]] += 1
    for n in sorted(tot):
        print("  %-7s %5d of %5d" % (n, al[n], tot[n]))
    shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
