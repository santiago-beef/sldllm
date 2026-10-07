#!/usr/bin/env python3
"""trunc_test.py - Stage 3 TRUNCATION test of the PSC decoder (WORKFLOW Stage 3,
"Truncation"; DESIGN 8.5 "truncation at every byte offset", 10.2 parsing).

Subcommands (run in this order; see README):
  gen      build gen_dumps from work/pscol (unmodified) and generate the dumps
           (pscol host harness and the decoder's synth.py) under DUMPS/
  plan     compute the cut sets per dump and model; write plan.json
  run      execute every cut (parallel); per-cut TSV logs + summary.json
  summary  print the counts tables from summary.json

For every cut the decoder (work/decoder, unmodified, imported read-only) must
  (a) not crash: no exception, exit status in {0, 2, 3};
  (b) recover every complete record before the cut, byte-identical to the
      uncut decode: every record of a complete chunk merged with the same 80/
      40/288 bytes (parse layer) and the same CSV row (program output), every
      other complete record of the cut chunk at least listed (UNVERIFIED,
      same bytes), nothing after the cut merged, every complete UHB / STATS /
      EVENT / KMSG / PROCS chunk and FILEHDR before the cut kept;
  (c) say the dump is truncated: classified per cut as explicit (a chunk
      listed BAD truncated / truncated-header / bad-crc in the cut file),
      size (RAW IMAGE REQUIRED naming the cut file's size), refused (REFUSED
      with a reason), anomaly (only a REPORT anomaly line about the cut
      file), none; and N/A where the cut leaves the file byte-identical to an
      untorn writer state (nothing to report).

Tail models (what lies after the cut):
  TRUNC    the file ends at the cut; later files of the run absent
           (the WORKFLOW text: "cut a dump at arbitrary byte offsets")
  OVERLAY  the file keeps its size; bytes after the cut are what the stick
           held before the flushes: the preallocation PAD sectors (DESIGN 4.4
           step 3); later files reverted to FILEHDR + PAD (a pull: the newer
           segment partially written, the older complete segment intact)
  SUBSET   one flush torn with an arbitrary subset of its 512-byte sectors
           written (non-ascending write-back order; UNVERIFIED that the
           driver writes in ascending order)

Tiers: P = the decoder's parse layer pscdec_parse.load() (records, bad list,
raw-image rule); F = the whole program pscdec.main() in-process (every
output file, REPORT, exit status), with a pure spy on pscdec_parse.load to
capture the same collection without parsing twice.
"""

import argparse
import collections
import csv
import glob
import gzip
import hashlib
import io
import json
import multiprocessing as mp
import os
import random
import shutil
import struct
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle as O  # noqa: E402

PSP = "/home/ubuntu/psp"
DEC = os.path.join(PSP, "work/decoder")
PSCOL = os.path.join(PSP, "work/pscol")
PKG_BUILD = os.path.join(PSP, "work/deploy/uClinux_TRACE/BUILD")
DUMPS = os.path.join(HERE, "dumps")
LOGS = os.path.join(PSP, "handoff/stage3/logs")
SHM = "/dev/shm"

# ----------------------------------------------------------------- the dumps
# name, generator, arguments, cut policy.  pscol: gen_dumps WORKER_START END
# SEED SPEED [FAILFLUSH]; synth: shape, seed, duration.
DUMP_SPECS = [
    dict(name="pscol-short", gen="pscol", args=[5, 16, 21, 52], policy="all",
         what="short: one file in creation, 15 flushes; FILEHDR (stats words), UHB, STATS, KMSG, EVENT"),
    dict(name="pscol-resend", gen="pscol", args=[5, 20, 24, 52, 6], policy="all",
         what="short with the 6th flush FAILED (its region holds PAD sectors) and its records re-sent later"),
    dict(name="synth-short", gen="synth", shape="H2", seed=31, duration=26, policy="all",
         what="short, independent writer model (decoder synth.py), EPC-valid build, PROCS"),
    dict(name="pscol-wrapped", gen="pscol", args=[130, 175, 22, 52], policy="large",
         what="wrapped: P and POLL rings lapped before the first read (first blocks lost > 0)"),
    dict(name="pscol-span", gen="pscol", args=[30, 404, 23, 52], policy="large",
         what="segment-boundary-spanning: T001001 complete, T001002 active, T001003 ready, T001004 in creation"),
    dict(name="synth-H4", gen="synth", shape="H4", seed=32, duration=None, policy="large",
         what="large H4 run (3 files), EPC-valid build, onset inside the data"),
]

LARGE_FOCUS_FIRST = 1
LARGE_FOCUS_LAST = 2
LARGE_FOCUS_RANDOM = 2
RANDOM_OFFSETS = 500
WINDOW = 64
SEED = 20261007
SUBSET_MAX_EXHAUSTIVE = 10      # sectors; above: 256 random subsets
SUBSET_RANDOM = 256


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ----------------------------------------------------------------- gen
def cmd_gen(a):
    os.makedirs(DUMPS, exist_ok=True)
    gbin = os.path.join(a.scratch, "gen_dumps")
    cc = ["gcc", "-O2", "-g", "-Wall", "-W", "-Wno-unused-parameter", "-std=gnu89", "-DPSCOL_HOST",
          "-o", gbin, os.path.join(PSCOL, "pscol.c"), os.path.join(HERE, "gen_dumps.c"),
          os.path.join(PSCOL, "test/vectors.c"), "-lm"]
    log = [" ".join(cc)]
    p = subprocess.run(cc, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    log.append("rc %d, compiler output: %r" % (p.returncode, p.stdout))
    if p.returncode:
        print("\n".join(log))
        return 1
    for sp in DUMP_SPECS:
        d = os.path.join(DUMPS, sp["name"])
        if os.path.exists(d):
            shutil.rmtree(d)
        if sp["gen"] == "pscol":
            cmd = [gbin, d] + [str(x) for x in sp["args"]]
        else:
            cmd = [sys.executable, os.path.join(DEC, "synth.py"), sp["shape"], d, "--seed", str(sp["seed"])]
            if sp["duration"]:
                cmd += ["--duration", str(sp["duration"])]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        log.append("$ %s\n%s(rc %d)" % (" ".join(cmd), p.stdout, p.returncode))
        if p.returncode:
            print("\n".join(log))
            return 1
    # manifest
    lines = []
    for f in sorted(glob.glob(os.path.join(DUMPS, "*", "**"), recursive=True)):
        if os.path.isfile(f):
            lines.append("%s  %s" % (sha256(f), os.path.relpath(f, DUMPS)))
    with open(os.path.join(DUMPS, "SHA256SUMS"), "w") as fo:
        fo.write("\n".join(lines) + "\n")
    log.append("gen_dumps sha256 %s" % sha256(gbin))
    with open(os.path.join(LOGS, "trunc-gen.log"), "w") as fo:
        fo.write("\n".join(log) + "\n")
    print("\n".join(log))
    return 0


# ----------------------------------------------------------------- dump model
class Dump(object):
    def __init__(self, spec):
        self.spec = spec
        self.name = spec["name"]
        self.dir = os.path.join(DUMPS, self.name)
        regions = None
        rp = os.path.join(self.dir, "regions.tsv")
        if os.path.exists(rp):
            regions = collections.defaultdict(list)
            for line in open(rp):
                if line.startswith("#"):
                    continue
                f, k, x, y = line.split()
                regions[f].append((k, int(x), int(y)))
        files = []
        for p in glob.glob(os.path.join(self.dir, "PSCLOG", "T*.BIN")):
            with open(p, "rb") as fi:
                data = fi.read()
            n = os.path.basename(p)
            files.append(O.FileTruth(n, data, regions.get(n) if regions else None))
        files.sort(key=lambda ft: ft.fh["seg"])
        self.files = files
        self.regions = regions
        self.nonce = files[0].nonce
        # writer boundaries per file (untorn states): FILEHDR area end, every
        # tick-flush end; for synth (no ledger) every flush-ending PAD chunk end
        self.wb = []
        for ft in files:
            b = set([0, O.FILEHDR_AREA, ft.size])
            if ft.flushes:
                b.update(e for (_s, e) in ft.flushes)
            else:
                for ch in ft.chunks:
                    if ch["type"] == 0 and ch["fseq"] != 0xFFFFFFFF:
                        b.add(ch["end"])
            b.add(ft.written_end)
            self.wb.append(sorted(b))
        self.flushes = []           # per file: list of (start, end) tick flushes
        for i, ft in enumerate(files):
            if ft.flushes:
                self.flushes.append(list(ft.flushes))
            else:
                fl, st = [], O.FILEHDR_AREA
                for ch in ft.chunks:
                    if ch["off"] < O.FILEHDR_AREA or (ch["type"] == 0 and ch["fseq"] == 0xFFFFFFFF):
                        continue
                    if ch["type"] == 0:
                        fl.append((st, ch["end"]))
                        st = ch["end"]
                self.flushes.append(fl)

    def decoder_args(self):
        if self.spec["gen"] == "synth":
            sys.path.insert(0, DEC)
            import synth
            return ["--build", os.path.join(self.dir, "build"), "--expect-image", synth.SYNTH_IMAGE_SHA256,
                    "--times", os.path.join(self.dir, "times.txt")]
        return ["--build", PKG_BUILD]


# ----------------------------------------------------------------- plan
def window_offsets(points, lo, hi, w=WINDOW):
    out = set()
    for p in points:
        for c in range(max(lo, p - w), min(hi, p + w) + 1):
            out.add(c)
    return out


def plan_dump(d):
    """Return {(model, k): sorted cuts} and the tier-F subset, and SUBSET tasks."""
    rng = random.Random("%s/%d" % (d.name, SEED))
    cuts = {}
    fcuts = {}
    subsets = []
    pol = d.spec["policy"]
    for k, ft in enumerate(d.files):
        if pol == "all":
            # tier P: every byte offset of the file (0 = empty file, size = uncut)
            p = set(range(0, ft.size + 1))
            # tier F: every byte offset up to one sector past the written content;
            # in the preallocation PAD-sector region above it, +-64 around the first
            # 4 sector boundaries and the last, +-2 around every sector boundary
            we = min(ft.size, ft.written_end + 512)
            f = set(range(0, we + 1))
            f |= window_offsets([ft.written_end + 512 * i for i in range(5)] + [ft.size - 512, ft.size],
                                0, ft.size)
            f |= window_offsets(range(ft.written_end, ft.size + 1, 512), 0, ft.size, 2)
            f |= set(rng.sample(range(ft.size + 1), min(RANDOM_OFFSETS, ft.size + 1)))
        else:
            p = set()
            f = set()
            fl = d.flushes[k]
            idx = list(range(len(fl)))
            # (1) the FILEHDR area: every byte, tier P; its chunk boundaries, tier F
            p |= set(range(0, min(ft.size, O.FILEHDR_AREA + WINDOW) + 1))
            # (2) a partially written segment with little written (<= 64 KB, e.g. the
            #     newer segment of pscol-span): every byte of its written content
            small_written = bool(fl) and ft.written_end <= 65536
            if small_written:
                p |= set(range(0, min(ft.size, ft.written_end + 512) + 1))
                focus = set(idx)
            else:
                # (3) focus flushes: every offset within 64 bytes of each chunk and
                #     record boundary (= every byte of the flush and 64 around it)
                # a segment the writer left for a newer one (switched from): its last
                # flushes before the switch matter most; its catch-up start is the
                # same shape as pscol-wrapped's first flush
                switched = any(d.flushes[i] for i in range(k + 1, len(d.files)))
                focus = set(idx[-(LARGE_FOCUS_LAST + 1):]) if switched else \
                    (set(idx[:LARGE_FOCUS_FIRST]) | set(idx[-LARGE_FOCUS_LAST:]))
                for j, (s0, e0) in enumerate(fl):
                    for ch in ft.chunks:
                        if s0 <= ch["off"] < e0 and ch["type"] == 2:
                            pl = ch["payload"]
                            pos = 0
                            while pos + 8 <= len(pl):
                                rb, div4, cnt, lost = struct.unpack_from('<BBHI', pl, pos)
                                if (rb & 0x80) or lost:
                                    focus.add(j)      # a lapped ("wrapped") or re-send block
                                pos += 8 + cnt * div4 * 4
                if d.spec["gen"] == "synth":
                    onset = json.load(open(os.path.join(d.dir, "truth.json")))["onset_tick"]
                    for j, (s0, e0) in enumerate(fl):
                        t = None
                        for ch in ft.chunks:
                            if s0 <= ch["off"] < e0 and ch["type"] == 6:
                                t = struct.unpack_from('<21I', ch["payload"], 0)[1]
                        if t is not None and t >= onset:
                            focus.add(j)          # the flush that first carries the onset
                            break
                others = [j for j in idx if j not in focus]
                focus |= set(rng.sample(others, min(LARGE_FOCUS_RANDOM, len(others))))
                for j in sorted(focus):
                    s0, e0 = fl[j]
                    pts = [b for b in ft.boundaries() if s0 - WINDOW <= b <= e0 + WINDOW]
                    p |= window_offsets(pts, 0, ft.size)
                # (4) every other flush: each chunk start -1..+1 (a cut between chunks)
                for j in idx:
                    if j in focus:
                        continue
                    s0, e0 = fl[j]
                    p |= window_offsets([ch["off"] for ch in ft.chunks if s0 <= ch["off"] < e0], 0, ft.size, 1)
            # (5) the preallocation PAD sectors: 64 around the first 4 above the written
            #     extent and the last
            we = ft.written_end
            p |= window_offsets([x for x in [we + 512 * i for i in range(5)] + [ft.size - 512, ft.size]
                                 if 0 <= x <= ft.size], 0, ft.size)
            # tier F: chunk boundaries -1..+1 and the 4 magic bytes in the FILEHDR area
            # and the focus flushes; record start/end-1/end in the focus RECS chunks
            # (all of them for a small partially written segment, else the first two)
            fpts = set()
            nrecs = 0
            for ch in ft.chunks:
                inf = ch["off"] < O.FILEHDR_AREA or any(fl[j][0] <= ch["off"] < fl[j][1] for j in focus)
                if not inf:
                    continue
                for x in (ch["off"], ch["pay0"], ch["pend"], ch["end"]):
                    fpts |= set(range(max(0, x - 1), min(ft.size, x + 1) + 1))
                fpts |= set(range(ch["off"], min(ft.size, ch["off"] + 5)))
                if ch["type"] == 2 and (small_written or nrecs < 2):
                    nrecs += 1
                    for r in ch["recs"]:
                        fpts |= set((r["start"], r["end"] - 1, r["end"]))
            f |= fpts
            f |= set([0, ft.size])
            p |= f
        cuts[k] = p
        fcuts[k] = f
        # SUBSET tears: the last tick flush of the file, and for large dumps the focus flushes
        fl = d.flushes[k]
        if fl:
            js = [len(fl) - 1]
            if pol == "large":
                js = sorted(set([0, len(fl) - 1, len(fl) // 2]))
            for j in js:
                s, e = fl[j]
                ns = (e - s) // 512
                if ns <= SUBSET_MAX_EXHAUSTIVE:
                    masks = list(range(0, 1 << ns))
                else:
                    masks = sorted(set([0, (1 << ns) - 1] + [rng.getrandbits(ns) for _ in range(SUBSET_RANDOM)]))
                for m in masks:
                    subsets.append((k, j, m))
    # 500 random offsets over the whole dump (fixed seed), both tiers
    if pol == "large":
        total = sum(ft.size + 1 for ft in d.files)
        for _ in range(RANDOM_OFFSETS):
            g = rng.randrange(total)
            for k, ft in enumerate(d.files):
                if g <= ft.size:
                    cuts[k].add(g)
                    fcuts[k].add(g)
                    break
                g -= ft.size + 1
    return cuts, fcuts, subsets


def cmd_plan(a):
    plan = {}
    for sp in DUMP_SPECS:
        d = Dump(sp)
        cuts, fcuts, subsets = plan_dump(d)
        plan[d.name] = dict(cuts={str(k): sorted(v) for k, v in cuts.items()},
                            fcuts={str(k): sorted(v) for k, v in fcuts.items()},
                            subsets=subsets)
        print("%-14s files %d sizes %s | P-tier cuts %s | F-tier cuts %s | subsets %d"
              % (d.name, len(d.files), [ft.size for ft in d.files], [len(cuts[k]) for k in sorted(cuts)],
                 [len(fcuts[k]) for k in sorted(fcuts)], len(subsets)))
    with open(os.path.join(a.scratch, "plan.json"), "w") as fo:
        json.dump(plan, fo)
    return 0


# ----------------------------------------------------------------- worker state
G = {}


def init_worker():
    sys.path.insert(0, DEC)
    import pscdec_parse
    import pscdec
    G["P"] = pscdec_parse
    G["main"] = pscdec
    G["orig_load"] = pscdec_parse.load
    G["captured"] = []

    def spy(*args, **kw):
        col = G["orig_load"](*args, **kw)
        G["captured"].append(col)
        return col
    pscdec_parse.load = spy          # a spy: same call, same result, the collection is kept
    G["dumps"] = {}
    G["ref"] = REF
    G["wdir"] = os.path.join(SHM, "trunc-%d" % os.getpid())
    if os.path.exists(G["wdir"]):
        shutil.rmtree(G["wdir"])
    os.makedirs(G["wdir"])


def get_dump(name):
    if name not in G["dumps"]:
        sp = [s for s in DUMP_SPECS if s["name"] == name][0]
        G["dumps"][name] = Dump(sp)
    return G["dumps"][name]


def read_csv_rows(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None, []
    with open(path, newline="") as f:
        r = csv.reader(f)
        hdr = next(r, None)
        return hdr, [tuple(x) for x in r]


RING_CSV = {0: "p.csv", 1: "poll.csv", 2: "w.csv", 3: "s.csv", 4: "m.csv"}


def program_ref(d, indir, outdir):
    """The uncut decode (tier F reference): exit status, CSV rows by (ring, seq),
    stats/uhb rows, events lines."""
    import pscdec
    sys.path.insert(0, DEC)
    rc = pscdec.main(["-o", outdir] + d.decoder_args() + [indir])
    ref = dict(rc=rc, rows={}, hdr={}, side={})
    for ring, fn in RING_CSV.items():
        hdr, rows = read_csv_rows(os.path.join(outdir, fn))
        ref["hdr"][ring] = hdr
        si = hdr.index("seq") if hdr else 0
        ref["rows"][ring] = {int(r[si]): r for r in rows}
    for fn in ("stats.csv", "uhb.csv"):
        hdr, rows = read_csv_rows(os.path.join(outdir, fn))
        ref["side"][fn] = (hdr, collections.Counter(rows))
    with open(os.path.join(outdir, "events.txt")) as f:
        ref["side"]["events"] = collections.Counter(f.read().splitlines())
    return ref


REF = {}


def build_refs(names, scratch):
    sys.path.insert(0, DEC)
    import pscdec_parse
    import pscdec  # noqa: F401
    out = {}
    for n in names:
        d = Dump([s for s in DUMP_SPECS if s["name"] == n][0])
        col = pscdec_parse.load([os.path.join(d.dir, "PSCLOG", ft.name) for ft in d.files])
        raw = {(r, s): bytes(v) for r in range(5) for (s, v) in col.rec_src[r].items()}
        od = os.path.join(scratch, "ref-" + n)
        if os.path.exists(od):
            shutil.rmtree(od)
        pref = program_ref(d, os.path.join(d.dir, "PSCLOG"), od)
        # oracle against the uncut decode: identical record sets and bytes
        exp = {}
        dup_conf = 0
        for ft in d.files:
            for r in ft.records:
                key = (r["ring"], r["seq"])
                if key in exp and exp[key] != r["raw"]:
                    dup_conf += 1
                exp.setdefault(key, r["raw"])
        exp = {k: v for k, v in exp.items() if struct.unpack_from('<I', v, 0)[0] != 0xFFFFFFFF}
        out[n] = dict(raw=raw, prog=pref,
                      uncut_anomalies=set(t for (_k, t) in col.anomalies),
                      uncut_raw_files=set(ft.name for ft in d.files
                                          if any(("file %s holds" % ft.name) in r for r in col.raw_required)),
                      uncut_check=dict(oracle_records=len(exp), decoder_records=len(raw),
                                       equal=(exp == raw), oracle_dup_conflicts=dup_conf,
                                       conflicts=len(col.conflicts), bad=len(col.bad),
                                       above_extent=len(col.above_extent), raw_required=list(col.raw_required),
                                       rc=pref["rc"]))
    return out


# ----------------------------------------------------------------- one cut
def expected_for(d, k, cut, model, content, mask=None, flush=None):
    """Oracle expectation for files[:k] complete and file k as `content`.
    A chunk of file k is complete iff its bytes [off, pend) in `content` are
    the writer's (TRUNC: pend <= cut; OVERLAY: also when the bytes after the
    cut equal the pre-image; SUBSET: when its sectors were written or equal).
    "listed": records of an incomplete RECS chunk whose bytes from the chunk
    start to the record end are intact (complete records before the tear).
    Returns dict(verified={key: raw}, listed={key: raw}, side=set((file, off, type)),
    fh=set(file names whose FILEHDR is complete))."""
    bkey = ("base", d.name, k)
    if bkey not in G:
        bv, bs, bf = {}, set(), set()
        for ft in d.files[:k]:
            for ch in ft.chunks:
                if ch["type"] == 1:
                    bf.add(ft.name)
                elif ch["type"] == 2:
                    for r in ch["recs"]:
                        if r["seq"] != 0xFFFFFFFF:
                            bv.setdefault((r["ring"], r["seq"]), r["raw"])
                elif ch["type"] in (3, 4, 5, 6, 7):
                    bs.add((ft.name, ch["off"], ch["type"]))
        G[bkey] = (bv, bs, bf)
    bv, bs, bf = G[bkey]
    ver, lst, side, fh = dict(bv), {}, set(bs), set(bf)
    ft = d.files[k]
    data = ft.data
    torn = []
    for ch in ft.chunks:
        if content[ch["off"]:ch["pend"]] == data[ch["off"]:ch["pend"]]:
            if ch["type"] == 1:
                fh.add(ft.name)
            elif ch["type"] == 2:
                for r in ch["recs"]:
                    if r["seq"] != 0xFFFFFFFF:
                        ver.setdefault((r["ring"], r["seq"]), r["raw"])
            elif ch["type"] in (3, 4, 5, 6, 7):
                side.add((ft.name, ch["off"], ch["type"]))
        elif ch["type"] == 2 and content[ch["off"]:ch["pay0"]] == data[ch["off"]:ch["pay0"]]:
            torn.append(ch)
    for ch in torn:
        for r in ch["recs"]:
            key = (r["ring"], r["seq"])
            if r["seq"] != 0xFFFFFFFF and key not in ver and \
                    content[ch["off"]:r["end"]] == data[ch["off"]:r["end"]]:
                lst[key] = r["raw"]
    return dict(verified=ver, listed=lst, side=side, fh=fh)


def position(ft, c):
    if c >= ft.size:
        return "eof"
    for ch in ft.chunks:
        if ch["off"] <= c < ch["end"]:
            t = "PADSECT" if (ch["type"] == 0 and ch["fseq"] == 0xFFFFFFFF) else ch["name"]
            if c == ch["off"]:
                part = "at-start"
            elif c < ch["off"] + 4:
                part = "in-magic"
            elif c < ch["pay0"]:
                part = "in-header"
            elif c < ch["pend"]:
                part = "in-payload"
            else:
                part = "in-pad4"
            return "%s/%s" % (t, part)
    return "?"


def lost_data_chunks(ft, a, b, content):
    """Non-PAD writer chunks in [a, b) whose bytes in `content` differ from the writer's."""
    out = []
    for ch in ft.chunks:
        if a <= ch["off"] < b and ch["type"] != 0 and content[ch["off"]:ch["pend"]] != ft.data[ch["off"]:ch["pend"]]:
            out.append(ch)
    return out


def na_reason(d, k, cut, model, content=None, mask=None, flush=None):
    """N/A for (c): nothing the writer wrote is lost, or the cut file equals an
    untorn writer state (nothing to report).  TRUNC: only the uncut file."""
    ft = d.files[k]
    if model == "TRUNC":
        return "uncut" if cut == ft.size else ""
    if model == "OVERLAY":
        wb = [b for b in d.wb[k] if b >= O.FILEHDR_AREA]
        nb = [b for b in wb if b >= cut]
        pb = [b for b in wb if b <= cut]
        b2 = nb[0] if nb else ft.size
        b1 = pb[-1] if pb else 0
        if ft.data[cut:b2] == ft.preimage(cut, b2):
            return "untorn-at-%d" % b2
        if pb and ft.data[b1:cut] == ft.preimage(b1, cut):
            return "untorn-at-%d" % b1
        if content is None:
            content = ft.data[:cut] + ft.preimage(cut, ft.size)
        if not lost_data_chunks(ft, b1, b2, content):
            return "pad-only"
        return ""
    s0, e0 = flush
    ns = (e0 - s0) // 512
    if mask == 0:
        return "untorn-before-flush"
    if mask == (1 << ns) - 1:
        return "untorn-whole-flush"
    if content[s0:e0] == ft.data[s0:e0] or content[s0:e0] == ft.preimage(s0, e0):
        return "untorn-identical"
    if not lost_data_chunks(ft, s0, e0, content):
        return "pad-only"
    return ""


def prepare(d, k, model, workdir, cut=None, content=None):
    """Write the input directory for files[:k] complete, file k given, files
    after k absent (TRUNC) or reverted to FILEHDR + PAD (OVERLAY/SUBSET).
    Files other than k are written once per (dump, k, model)."""
    ind = os.path.join(workdir, "PSCLOG")
    key = (d.name, k, model)
    if G.get("prepared") != key:
        if os.path.exists(ind):
            shutil.rmtree(ind)
        os.makedirs(ind)
        for i, ft in enumerate(d.files):
            if i == k:
                continue
            if i < k:
                data = ft.data
            elif model == "TRUNC":
                continue
            else:
                data = ft.data[:O.FILEHDR_AREA] + ft.preimage(O.FILEHDR_AREA, ft.size) \
                    if ft.size > O.FILEHDR_AREA else ft.data
            with open(os.path.join(ind, ft.name), "wb") as fo:
                fo.write(data)
        G["prepared"] = key
    with open(os.path.join(ind, d.files[k].name), "wb") as fo:
        fo.write(content)
    return ind


def check_parse(d, k, cut, model, col, exp, ref):
    """Tier P checks on the decoder's collection.  Returns a dict of counts."""
    ft = d.files[k]
    res = {}
    got = {}
    for r in range(5):
        for s, v in col.rec_src[r].items():
            got[(r, s)] = bytes(v)
    ver = exp["verified"]
    miss = [key for key in ver if key not in got]
    diff = [key for key in ver if key in got and got[key] != ver[key]]
    refdiff = [key for key in ver if key in got and ref["raw"].get(key) != got[key]]
    extra = [key for key in got if key not in ver]
    unv = {}
    for (src, off, st, ring, raw) in col.unverified:
        unv[(ring, struct.unpack_from('<I', raw, 0)[0])] = (bytes(raw), src)
    lmiss = [key for key in exp["listed"] if not ((key in unv and unv[key][0] == exp["listed"][key]) or
                                                  (key in got and got[key] == exp["listed"][key]))]
    res.update(exp_ver=len(ver), miss=len(miss), diff=len(diff), refdiff=len(refdiff), extra=len(extra),
               exp_listed=len(exp["listed"]), listed_miss=len(lmiss), unverified=len(col.unverified),
               above_extent=len(col.above_extent), conflicts=len(col.conflicts))
    # side chunks: UHB, STATS by _src; EVENT, KMSG, PROCS by chunk position
    side_got = set()
    for u in col.uhb:
        side_got.add((u["_src"][0], u["_src"][1], 6))
    for st in col.stats:
        side_got.add((st["_src"][0], st["_src"][1], 3))
    for (_t, _x, c) in col.events:
        side_got.add((c.file.name, c.off, 7))
    good_by_src = {}
    for s in col.sources:
        for c in s.good:
            good_by_src.setdefault(s.name, set()).add((c.off, c.ctype))
    side_exp = exp["side"]
    sm = 0
    for (fn, off, t) in side_exp:
        if t in (3, 6, 7):
            if (fn, off, t) not in side_got and not dup_side(d, fn, off, t, side_got):
                sm += 1
        else:  # KMSG, PROCS: the chunk accepted as good in its file
            if (off, t) not in good_by_src.get(fn, set()):
                sm += 1
    se = len([x for x in side_got if x not in side_exp])
    res.update(exp_side=len(side_exp), side_miss=sm, side_extra=se)
    fh_got = set(s.name for s in col.sources if s.fh)
    res["fh_miss"] = len(exp["fh"] - fh_got)
    # phantoms: chunks accepted in the cut file that the writer did not write
    # there (a PAD sector of the pre-image at a sector boundary is not one)
    orig = G.setdefault(("orig", d.name, k), dict(((ch["off"], ch["type"], ch["len"]), ch["payload"])
                                                  for ch in ft.chunks))
    ph = []
    for s_ in col.sources:
        if s_.name != ft.name:
            continue
        for c in s_.good:
            key = (c.off, c.ctype, c.length)
            if key in orig and orig[key] == c.payload:
                continue
            if c.ctype == 0 and c.length == 492 and c.off % 512 == 0 and c.fseq == 0xFFFFFFFF:
                continue
            ph.append("%s@%d/%d" % (c.name, c.off, c.length))
    res["phantom"] = ";".join(ph)
    # (c) the decoder's statement about the cut file
    sig = []
    nm = ft.name
    if col.refused:
        sig.append("refused")
    if any(c.src == nm and c.status in ("truncated", "truncated-header", "bad-crc") for c in col.bad):
        sig.append("explicit")
    if model == "TRUNC" and any(("file %s holds RECS chunks and is %d bytes" % (nm, cut)) in r
                                for r in col.raw_required):
        sig.append("size" if nm not in ref["uncut_raw_files"] else "size-also-uncut")
    if any(nm in t and t not in ref["uncut_anomalies"] for (_k, t) in col.anomalies):
        sig.append("anomaly")
    res["signal"] = sig
    res["raw_required"] = len(col.raw_required)
    return res


def dup_side(d, fn, off, t, side_got):
    """A side chunk whose payload equals an earlier one is kept once (10.2
    dedupe by payload): accept the earlier copy."""
    ft = [f for f in d.files if f.name == fn][0]
    ch = [c for c in ft.chunks if c["off"] == off][0]
    for f2 in d.files:
        for c2 in f2.chunks:
            if c2["type"] == t and c2["payload"] == ch["payload"] and (f2.name, c2["off"], t) in side_got:
                return True
    return False


def len_of(d, k, cut, model):
    return cut if model == "TRUNC" else d.files[k].size


def check_program(d, k, cut, model, outdir, rc, exp, ref, col):
    res = {"rc": rc}
    rmiss = rdiff = rextra = hdrbad = 0
    for ring, fn in RING_CSV.items():
        hdr, rows = read_csv_rows(os.path.join(outdir, fn))
        if not rows:
            got = {}
        else:
            if hdr != ref["prog"]["hdr"][ring]:
                hdrbad += 1
            si = hdr.index("seq")
            got = {int(r[si]): r for r in rows}
        expk = [s for (rg, s) in exp["verified"] if rg == ring]
        for s in expk:
            if s not in got:
                rmiss += 1
            elif got[s] != ref["prog"]["rows"][ring].get(s):
                rdiff += 1
        rextra += len(set(got) - set(expk))
    res.update(csv_miss=rmiss, csv_diff=rdiff, csv_extra=rextra, csv_hdr=hdrbad)
    sx = 0
    for fn in ("stats.csv", "uhb.csv"):
        hdr, rows = read_csv_rows(os.path.join(outdir, fn))
        rh, rc_ = ref["prog"]["side"][fn]
        for row, n in collections.Counter(rows).items():
            if rc_.get(row, 0) < n:
                sx += 1
    ev = collections.Counter()
    if os.path.exists(os.path.join(outdir, "events.txt")):
        with open(os.path.join(outdir, "events.txt")) as f:
            ev = collections.Counter(f.read().splitlines())
    for line, n in ev.items():
        if ref["prog"]["side"]["events"].get(line, 0) < n:
            sx += 1
    res["side_rows_not_in_uncut"] = sx
    rep = None
    for n in ("REPORT.md", "REPORT-NOT-FINAL.md"):
        if os.path.exists(os.path.join(outdir, n)):
            rep = n
    res["report"] = rep or ("REFUSED.txt" if os.path.exists(os.path.join(outdir, "REFUSED.txt")) else "none")
    # exit status consistent with the collection
    want = 2 if col.refused else (3 if col.raw_required else 0)
    res["rc_consistent"] = int(rc == want)
    psig = []
    nm = d.files[k].name
    if os.path.exists(os.path.join(outdir, "bad.txt")):
        with open(os.path.join(outdir, "bad.txt")) as f:
            bt = f.read()
        for st in ("truncated", "truncated-header", "bad-crc"):
            if ("BAD %s %s@" % (st, nm)) in bt:
                psig.append("explicit")
                break
    if rep == "REPORT-NOT-FINAL.md":
        with open(os.path.join(outdir, rep)) as f:
            t = f.read()
        if model == "TRUNC" and "RAW IMAGE REQUIRED" in t and \
                ("file %s holds RECS chunks and is %d bytes" % (nm, cut)) in t:
            psig.append("size")
    if res["report"] == "REFUSED.txt":
        psig.append("refused")
    res["prog_signal"] = psig
    return res


def run_one(d, k, cut, model, content, tierF, mask=None, flush=None):
    """Decode one cut; return a result dict (never raises)."""
    ref = G["ref"][d.name]
    wd = G["wdir"]
    exp = expected_for(d, k, cut, model, content, mask, flush)
    out = dict(dump=d.name, model=model, k=k, cut=cut, mask=mask, tier="F" if tierF else "P")
    out["pos"] = position(d.files[k], cut) if model != "SUBSET" else "flush%d" % (flush[0])
    out["na"] = na_reason(d, k, cut, model, content, mask, flush)
    ind = prepare(d, k, model, wd, cut, content)
    G["captured"][:] = []
    od = os.path.join(wd, "out")
    rc = None
    try:                                    # only the decoder runs inside this try
        if tierF:
            if os.path.exists(od):
                shutil.rmtree(od)
            so, se = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = io.StringIO()
            try:
                rc = G["main"].main(["-o", od] + d.decoder_args() + [ind])
            finally:
                sys.stdout, sys.stderr = so, se
        else:
            paths = sorted(glob.glob(os.path.join(ind, "T*.BIN")))
            G["captured"].append(G["orig_load"](paths))
        out["crash"] = 0
    except BaseException as e:              # SystemExit included (argparse, sys.exit)
        out["crash"] = 1
        out["trace"] = ("%s: " % type(e).__name__) + traceback.format_exc()[-1500:]
        return out
    if rc not in (None, 0, 2, 3):
        out["crash"] = 1
        out["trace"] = "exit status %r" % (rc,)
        return out
    col = G["captured"][-1]
    try:
        out.update(check_parse(d, k, cut, model, col, exp, ref))
        if tierF:
            out.update(check_program(d, k, cut, model, od, rc, exp, ref, col))
    except Exception:
        out["harness_error"] = traceback.format_exc()[-800:]
    return out


def task(args):
    """A batch of cuts of one (dump, model, file k)."""
    name, model, k, items = args
    d = get_dump(name)
    ft = d.files[k]
    res = []
    for it in items:
        if model == "SUBSET":
            j, mask = it
            s, e = d.flushes[k][j]
            buf = bytearray(ft.data[:s] + ft.preimage(s, ft.size))
            for q in range((e - s) // 512):
                if (mask >> q) & 1:
                    buf[s + 512 * q:s + 512 * q + 512] = ft.data[s + 512 * q:s + 512 * q + 512]
            r = run_one(d, k, e, model, bytes(buf), True, mask, (s, e))
            r["cut"] = s
        else:
            cut, tierF = it
            if model == "TRUNC":
                content = ft.data[:cut]
            else:
                content = ft.data[:cut] + ft.preimage(cut, ft.size)
            r = run_one(d, k, cut, model, content, tierF)
        res.append(r)
    return res


def cmd_run(a):
    plan = json.load(open(os.path.join(a.scratch, "plan.json")))
    names = [s["name"] for s in DUMP_SPECS if (not a.only or s["name"] in a.only)]
    t0 = time.time()
    global REF
    REF = build_refs(names, a.scratch)
    for n in names:
        print("uncut %-14s %s" % (n, REF[n]["uncut_check"]), flush=True)
    tasks = []
    for n in names:
        pl = plan[n]
        for ks, cl in pl["cuts"].items():
            k = int(ks)
            fs = set(pl["fcuts"][ks])
            for model in ("TRUNC", "OVERLAY"):
                items = [(c, c in fs) for c in sorted(cl, reverse=True)]
                if a.ftier_only:
                    items = [x for x in items if x[1]]
                bs = a.batch
                for i in range(0, len(items), bs):
                    tasks.append((n, model, k, items[i:i + bs]))
        sub = collections.defaultdict(list)
        for (k, j, m) in pl["subsets"]:
            sub[k].append((j, m))
        for k, items in sub.items():
            for i in range(0, len(items), 64):
                tasks.append((n, "SUBSET", k, items[i:i + 64]))
    # big tasks first
    random.Random(SEED).shuffle(tasks)
    print("tasks %d, cuts %d" % (len(tasks), sum(len(t[3]) for t in tasks)), flush=True)
    os.makedirs(LOGS, exist_ok=True)
    outs = {}
    for n in names:
        outs[n] = gzip.open(os.path.join(LOGS, "trunc-%s.tsv.gz" % n), "wt")
        outs[n].write("\t".join(COLS) + "\n")
    agg = {}
    crashes = []
    harness_err = []
    done = 0
    with mp.Pool(a.jobs, initializer=init_worker) as pool:
        for res in pool.imap_unordered(task, tasks, chunksize=1):
            for r in res:
                try:
                    outs[r["dump"]].write("\t".join(fmt(r.get(c)) for c in COLS) + "\n")
                    accumulate(agg, r)
                except Exception:
                    harness_err.append((r.get("dump"), r.get("model"), r.get("k"), r.get("cut"),
                                        traceback.format_exc()[-800:]))
                if r.get("crash"):
                    crashes.append(r)
            done += 1
            if done % 200 == 0:
                print("  %d/%d tasks, %.0f s" % (done, len(tasks), time.time() - t0), flush=True)
    for f in outs.values():
        f.close()
    summ = dict(elapsed_s=round(time.time() - t0, 1), jobs=a.jobs,
                uncut={n: REF[n]["uncut_check"] for n in names},
                agg={"|".join(map(str, k)): v for k, v in agg.items()},
                crashes=crashes[:50], harness_errors=harness_err[:50], n_harness_errors=len(harness_err))
    with open(os.path.join(a.scratch, "summary-%s.json" % ("-".join(names) if a.only else "all")), "w") as fo:
        json.dump(summ, fo, indent=1, default=str)
    print("done in %.0f s; crashes %d; harness errors %d" % (time.time() - t0, len(crashes), len(harness_err)))
    return 0


COLS = ["dump", "model", "k", "cut", "mask", "tier", "pos", "na", "crash", "exp_ver", "miss", "diff", "refdiff",
        "extra", "exp_listed", "listed_miss", "unverified", "above_extent", "conflicts", "exp_side", "side_miss",
        "side_extra", "fh_miss", "phantom", "signal", "raw_required", "rc", "rc_consistent", "csv_miss", "csv_diff",
        "csv_extra", "csv_hdr", "side_rows_not_in_uncut", "report", "prog_signal", "trace", "harness_error"]


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return ",".join(v)
    return str(v).replace("\t", " ").replace("\n", " | ")


def accumulate(agg, r):
    key = (r["dump"], r["model"], r["tier"])
    a = agg.setdefault(key, collections.Counter())
    a["cuts"] += 1
    a["crash"] += r.get("crash", 0)
    if r.get("harness_error"):
        a["harness_error"] += 1
        raise RuntimeError("harness error in worker: " + r["harness_error"])
    if r.get("crash"):
        return
    b_ok = r["miss"] == 0 and r["diff"] == 0 and r["refdiff"] == 0 and r["extra"] == 0 and \
        r["side_miss"] == 0 and r["fh_miss"] == 0 and (r["side_extra"] == 0 or bool(r.get("phantom")))
    if r["tier"] == "F":
        b_ok = b_ok and r["csv_miss"] == 0 and r["csv_diff"] == 0 and r["csv_extra"] == 0 and \
            r["csv_hdr"] == 0 and (r["side_rows_not_in_uncut"] == 0 or bool(r.get("phantom"))) and \
            r["rc_consistent"] == 1
        a["rc_%s" % r["rc"]] += 1
    a["b_strict_ok"] += int(b_ok)
    a["b_listed_ok"] += int(b_ok and r["listed_miss"] == 0)
    a["records_checked"] += r["exp_ver"]
    a["records_listed_expected"] += r["exp_listed"]
    a["records_listed_missing"] += r["listed_miss"]
    a["miss"] += r["miss"]
    a["extra"] += r["extra"]
    a["diff"] += r["diff"] + r["refdiff"]
    a["side_miss"] += r["side_miss"]
    a["above_extent_cuts"] += int(r["above_extent"] > 0)
    if r.get("phantom"):
        a["phantom_cuts"] += 1
        for x in r["phantom"].split(";"):
            a["phantom|" + x.split("@")[0]] += 1
    sig = r["signal"]
    if r["na"]:
        a["c_na"] += 1
        a["c_na_but_signal"] += int(bool(sig))
    else:
        if "explicit" in sig:
            a["c_explicit"] += 1
        elif "refused" in sig:
            a["c_refused"] += 1
        elif "size" in sig:
            a["c_size_only"] += 1
        elif "size-also-uncut" in sig:
            a["c_size_also_uncut_only"] += 1
            a["c_size_also_uncut|" + r["pos"].split("/")[0]] += 1
        elif "anomaly" in sig:
            a["c_anomaly_only"] += 1
            a["c_anomaly|" + r["pos"]] += 1
        else:
            a["c_none"] += 1
            a["c_none|" + r["pos"]] += 1
    if r["tier"] == "F":
        ps = r.get("prog_signal") or []
        if not r["na"]:
            a["cF_prog_said"] += int(bool(ps))


def cmd_summary(a):
    for p in sorted(glob.glob(os.path.join(a.scratch, "summary-*.json"))):
        s = json.load(open(p))
        print("==", os.path.basename(p), "elapsed", s["elapsed_s"])
        for k, v in sorted(s["agg"].items()):
            print(k, dict(v))
        for c in s["crashes"][:5]:
            print("CRASH", {x: c.get(x) for x in ("dump", "model", "k", "cut", "trace")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "plan", "run", "summary"])
    ap.add_argument("--scratch", default=os.environ.get("TRUNC_SCRATCH", "/tmp/trunc-scratch"))
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--batch", type=int, default=400)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--ftier-only", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.scratch, exist_ok=True)
    return {"gen": cmd_gen, "plan": cmd_plan, "run": cmd_run, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
