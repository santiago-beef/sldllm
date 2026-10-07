#!/usr/bin/env python3
"""Decoder tests (WORKFLOW Stage 3 'Decoder' and 'Truncation'; DESIGN 8.5 decoder rows).

Streams come from synth.py (built from the record format, not from the
decoder); the decoder is run as a program (pscdec.py) and through its parse
layer.  Run:  python3 test/run_tests.py  (output also saved to TESTS.txt by
the caller).
"""

import hashlib
import json
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DEC = os.path.dirname(HERE)
sys.path.insert(0, DEC)
import psc_format as F          # noqa: E402
import synth                    # noqa: E402
import pscdec_parse as P        # noqa: E402

TMP = tempfile.mkdtemp(prefix="pscdec-test-")


def say(*a):
    print(*a, file=sys.stderr)


def rd(path, mode="r"):
    with open(path, mode) as f:
        return f.read()


def wr(path, data):
    with open(path, "wb") as f:
        f.write(data)


def jload(path):
    with open(path) as f:
        return json.load(f)
_cache = {}


def gen(name, shape, **kw):
    """Generate (once) a synthetic stream; returns its directory."""
    d = os.path.join(TMP, name)
    if name not in _cache:
        img = kw.pop("image", False)
        s = synth.Synth(shape, **kw)
        s.generate(d)
        if img:
            synth.make_image(d)
        _cache[name] = d
    return d


def decode(d, outname="dec", extra=(), inputs=None, times=True, build=True):
    out = os.path.join(d, outname)
    if os.path.exists(out):
        shutil.rmtree(out)
    cmd = [sys.executable, os.path.join(DEC, "pscdec.py"), "-o", out]
    if build:
        # the synthetic BUILD belongs to the synthetic image (10.1, K3: Stage 3 closure)
        cmd += ["--build", os.path.join(d, "build"), "--expect-image", synth.SYNTH_IMAGE_SHA256]
    if times:
        cmd += ["--times", os.path.join(d, "times.txt")]
    cmd += list(extra)
    cmd += inputs if inputs is not None else [os.path.join(d, "PSCLOG")]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    js = None
    if os.path.exists(os.path.join(out, "classification.json")):
        js = jload(os.path.join(out, "classification.json"))
    return p.returncode, p.stdout, js, out


class Shapes(unittest.TestCase):
    """Each H-shape is named correctly (Stage 3 'Decoder')."""

    def shape(self, shape):
        d = gen(shape, shape, seed=11)
        rc, so, js, out = decode(d)
        self.assertEqual(rc, 0, so)
        say("    %-7s -> %s | state %s triggers %s H8 flags %d | onset %s" %
              (shape, js["named"], js["state"], js["triggers"], len(js["h8"]), js["onset"]))
        return js, out

    def test_H1(self):
        js, _ = self.shape("H1")
        self.assertIn("H1", js["state"])
        self.assertNotIn("H4", js["triggers"])

    def test_H2(self):
        js, _ = self.shape("H2")
        self.assertEqual(js["state"][0], "H2")

    def test_H3(self):
        js, _ = self.shape("H3")
        self.assertEqual(js["state"][0], "H3")
        self.assertEqual(js["h8"], [])

    def test_H4(self):
        js, out = self.shape("H4")
        self.assertIn("H4", js["triggers"])
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("-> P4", rep)                 # step from the W EPC map (10.6)
        self.assertIn("allowed for P4", rep)        # P-point cross-check (10.7 step 5)
        self.assertIn("across (wn 1)", rep)         # 6.3 placement of the first failed command

    def test_H5(self):
        js, _ = self.shape("H5")
        self.assertEqual(js["state"][0], "H5")

    def test_H6(self):
        js, _ = self.shape("H6")
        self.assertEqual(js["state"], ["H6"])

    def test_H7(self):
        js, _ = self.shape("H7")
        self.assertEqual(js["state"][0], "H7")
        self.assertEqual(js["h7_stage"], ["b"])

    def test_H8(self):
        js, _ = self.shape("H8")
        self.assertTrue(any("gpio_in" in h for h in js["h8"]), js["h8"])
        self.assertTrue(any("ack_polls always 0" in h for h in js["h8"]), js["h8"])
        self.assertTrue(js["state"])                 # H8 is a flag beside a state, never alone

    def test_H9(self):
        js, _ = self.shape("H9")
        self.assertEqual(js["state"][0], "H9")

    def test_H10(self):
        js, out = self.shape("H10")
        self.assertIn("H10", js["triggers"])
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("S13..S20 (G3 high)", rep)
        self.assertIn("H10 trigger", rep)

    def test_healthy(self):
        js, out = self.shape("healthy")
        self.assertEqual(js["verdict"], "NO DEATH DETECTED")
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("no-death inference", rep)

    def test_none_unclassified(self):
        js, out = self.shape("none")
        self.assertEqual(js["named"], "H0 / UNCLASSIFIED")
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("UNCLASSIFIED", rep)
        self.assertIn("```", rep)                    # raw records printed with the verdict
        win = [f for f in os.listdir(out) if f.startswith("window_")]
        self.assertTrue(win)


class N4(unittest.TestCase):
    """Review N-4 / R22: a stale-frame stream whose healthy rx[2] is not 0x08."""

    def test_rx2_not_08(self):
        d = gen("n4", "H6", seed=12, rx2alt=True)
        rc, so, js, out = decode(d)
        say("    template    -> %s flags %s" % (js["named"], js["flags"]))
        self.assertEqual(js["state"], ["H6"])
        self.assertNotIn("rx2 literal", js["flags"])
        rc, so, js2, out2 = decode(d, "dec_notmpl", extra=["--no-template"])
        say("    no template -> %s flags %s" % (js2["named"], js2["flags"]))
        self.assertIn("rx2 literal", js2["flags"])
        self.assertNotIn("H6", js2["state"])


def file_order(d):
    t = jload(os.path.join(d, "truth.json"))
    return t, [f["name"] for f in t["files"]]


class Truncation(unittest.TestCase):
    """Stage 3 'Truncation': cut at arbitrary byte offsets (a battery pull);
    every complete record before the cut is recovered."""

    def test_50_offsets(self):
        d = gen("trunc", "H1", seed=13)
        truth, names = file_order(d)
        sizes = [os.path.getsize(os.path.join(d, "PSCLOG", n)) for n in names]
        written = max(e["payload_end"] for e in truth["ledger"] if e["file"] == names[0])
        rng = random.Random(4242)
        offs = [(0, rng.randrange(0, written)) for _ in range(40)]
        total = sum(sizes)
        for _ in range(10):
            g = rng.randrange(0, total)
            fi = 0
            while g >= sizes[fi]:
                g -= sizes[fi]
                fi += 1
            offs.append((fi, g))
        worst = 0
        n_checked = 0
        for k, (fi, cut) in enumerate(offs):
            td = os.path.join(TMP, "cut%02d" % k)
            os.makedirs(td)
            paths = []
            for j, n in enumerate(names[:fi + 1]):
                src = rd(os.path.join(d, "PSCLOG", n), "rb")
                if j == fi:
                    src = src[:cut]
                pth = os.path.join(td, n)
                wr(pth, src)
                paths.append(pth)
            col = P.load(paths)
            got = set((r, s) for r in range(F.NRINGS) for s in col.records[r])
            unver = set((ring, int.from_bytes(raw[:4], "little")) for (_s, _o, _st, ring, raw) in col.unverified)
            exp_chunk, exp_rec = set(), set()
            for e in truth["ledger"]:
                j = names.index(e["file"])
                if j > fi:
                    continue
                for rid, end in zip(e["recs"], e["rec_ends"]):
                    rid = tuple(rid)
                    if j < fi or e["payload_end"] <= cut:
                        exp_chunk.add(rid)
                    if j < fi or end <= cut:
                        exp_rec.add(rid)
            missing = exp_chunk - got
            self.assertFalse(missing, "cut %d@%s: %d records of complete chunks lost" % (cut, names[fi], len(missing)))
            self.assertFalse(got - exp_rec, "records after the cut reported as merged")
            miss2 = exp_rec - got - unver
            self.assertFalse(miss2, "cut %d: %d complete records neither merged nor listed" % (cut, len(miss2)))
            worst = max(worst, len(exp_rec - got))
            n_checked += len(exp_rec)
            shutil.rmtree(td)
        say("    50 cuts: %d complete records checked; 0 lost from complete chunks; at most %d records of a "
              "cut chunk listed as unverified salvage (not merged)" % (n_checked, worst))


class TwoBoots(unittest.TestCase):
    """A5 IF10: another boot's files and chunks are never merged."""

    def setUp(self):
        self.a = gen("bootA", "healthy", seed=21, run_no=1, nonce=0xAAAA1111, duration_cap=90)
        self.b = gen("bootB", "H1", seed=22, run_no=2, nonce=0xBBBB2222)
        self.c = gen("bootC", "healthy", seed=23, run_no=2, nonce=0xCCCC3333, duration_cap=90)

    def merged_dir(self, name, dirs):
        md = os.path.join(TMP, name)
        if os.path.exists(md):
            shutil.rmtree(md)
        os.makedirs(os.path.join(md, "PSCLOG"))
        shutil.copytree(os.path.join(self.b, "build"), os.path.join(md, "build"))
        shutil.copy(os.path.join(self.b, "times.txt"), md)
        for dd in dirs:
            for n in os.listdir(os.path.join(dd, "PSCLOG")):
                shutil.copy(os.path.join(dd, "PSCLOG", n), os.path.join(md, "PSCLOG", n))
        return md

    def test_other_run_listed_and_ignored(self):
        rc, so, ref, _ = decode(self.b, "dec_alone")
        md = self.merged_dir("boots_AB", [self.a, self.b])
        rc, so, js, out = decode(md)
        self.assertEqual(rc, 0, so)
        self.assertEqual(js["run"], 2)
        self.assertEqual(js["records"], ref["records"])
        self.assertEqual(js["named"], ref["named"])
        seg = rd(os.path.join(out, "segments.txt"))
        self.assertIn("IGNORED: run 1", seg)
        say("    runs 1+2 in PSCLOG: run 2 selected, run 1 files ignored, records identical to run 2 alone")

    def test_te7_stale_chunk_inside_file(self):
        md = self.merged_dir("boots_te7", [self.a, self.b])
        # a RECS chunk of boot A written into a ready file of boot B, below its confirmed extent (TE7)
        fa = rd(os.path.join(md, "PSCLOG", "T001001.BIN"), "rb")
        cands = P.candidates(fa, "A")
        good, _ = P.accept(fa, cands, 0xAAAA1111)
        rc_a = next(c for c in good if c.ctype == F.CHUNK_RECS and c.length > 2000)
        raw = fa[rc_a.off:rc_a.end]
        pb = os.path.join(md, "PSCLOG", "T002002.BIN")
        fb = bytearray(rd(pb, "rb"))
        at = 1536 + 512 * 40
        fb[at:at + len(raw)] = raw
        wr(pb, bytes(fb))
        rc, so, js, out = decode(md)
        self.assertEqual(rc, 0, so)
        self.assertGreaterEqual(js["other_boot_chunks"], 1)
        self.assertEqual(js["conflicts"], 0)
        rc, so, ref, _ = decode(self.b, "dec_alone2")
        self.assertEqual(js["records"], ref["records"])
        self.assertIn("OTHER-BOOT", rd(os.path.join(out, "bad.txt")))
        say("    boot A RECS chunk inside a boot B file: listed OTHER-BOOT, not merged, 0 conflicts")

    def test_same_run_two_nonces_refused(self):
        md = self.merged_dir("boots_BC", [self.b])
        for n in os.listdir(os.path.join(self.c, "PSCLOG")):
            # same run number, other boot: give the copies names that do not collide (names are not
            # authoritative, 10.2: the FILEHDR is)
            shutil.copy(os.path.join(self.c, "PSCLOG", n), os.path.join(md, "PSCLOG", "T0029" + n[-6:]))
        rc, so, js, out = decode(md)
        self.assertEqual(rc, 2, so)
        self.assertIn("refusing to merge", so)
        self.assertFalse(os.path.exists(os.path.join(out, "REPORT.md")))
        rc, so, js, out = decode(md, extra=["--nonce", "BBBB2222"])
        self.assertEqual(rc, 0, so)
        rc2, so2, ref, _ = decode(self.b, "dec_alone3")
        self.assertEqual(js["records"], ref["records"])
        say("    run 2 with two nonces: refused (exit 2); with --nonce: only that boot decoded")


class RawImage(unittest.TestCase):
    """--raw over a stick image; the raw-image-required rule (10.2)."""

    def test_raw_only_equals_files(self):
        d = gen("raw", "H3", seed=31, image=True)
        rc, so, jf, _ = decode(d, "dec_files")
        rc, so, jr, out = decode(d, "dec_raw", extra=["--raw", os.path.join(d, "stick.img")], inputs=[])
        self.assertEqual(rc, 0, so)
        self.assertEqual(jr["records"], jf["records"])
        self.assertEqual(jr["named"], jf["named"])
        say("    raw image only: %s records, %s (same as the copied files)" % (jr["records"], jr["named"]))

    def test_short_copy_requires_raw(self):
        d = gen("raw", "H3", seed=31, image=True)
        sd = os.path.join(TMP, "shortcopy")
        if os.path.exists(sd):
            shutil.rmtree(sd)
        os.makedirs(sd)
        names = sorted(os.listdir(os.path.join(d, "PSCLOG")))
        for n in names:
            data = rd(os.path.join(d, "PSCLOG", n), "rb")
            if n == names[0]:
                data = data[:700000]                 # a failed/short Mac copy
            wr(os.path.join(sd, n), data)
        rc, so, js, out = decode(d, "dec_short", inputs=[sd])
        self.assertEqual(rc, 3, so)
        self.assertIn("RAW IMAGE REQUIRED", so)
        self.assertFalse(os.path.exists(os.path.join(out, "REPORT.md")))
        self.assertTrue(os.path.exists(os.path.join(out, "REPORT-NOT-FINAL.md")))
        rc, so, js2, out = decode(d, "dec_short_raw", extra=["--raw", os.path.join(d, "stick.img")], inputs=[sd])
        self.assertEqual(rc, 0, so)
        self.assertGreater(js2["only_in_image"], 0)
        self.assertTrue(os.path.exists(os.path.join(out, "REPORT.md")))
        say("    short copy: refused without --raw (exit 3); with --raw final, %d records only in the image"
              % js2["only_in_image"])

    def test_flush_fail_requires_raw_and_resend_dedup(self):
        d = gen("ffail", "H2", seed=32, image=True, flush_fail=True)
        rc, so, js, out = decode(d)
        self.assertEqual(rc, 3, so)
        self.assertTrue(any("flush fail" in r for r in js["raw_required"]))
        rc, so, js, out = decode(d, "dec_raw", extra=["--raw", os.path.join(d, "stick.img")])
        self.assertEqual(rc, 0, so)
        self.assertEqual(js["conflicts"], 0)
        self.assertEqual(js["state"][0], "H2")
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertRegex(rep, r"exact duplicates removed [1-9]")
        say("    EVENT flush fail: refused without --raw; with --raw final, re-sent records de-duplicated")


class Merge(unittest.TestCase):
    """(ring, seq) conflicts are reported, never dropped; the confirmed-extent rule."""

    def test_conflict_reported(self):
        d = gen("confl", "H5", seed=41)
        md = os.path.join(TMP, "confl_m")
        if os.path.exists(md):
            shutil.rmtree(md)
        shutil.copytree(d, md, ignore=shutil.ignore_patterns("dec*"))
        p1 = os.path.join(md, "PSCLOG", "T001001.BIN")
        fa = rd(p1, "rb")
        good, _ = P.accept(fa, P.candidates(fa, "x"), 0x1234ABCD)
        c = next(c for c in good if c.ctype == F.CHUNK_RECS and c.length > 2000)
        pl = bytearray(c.payload)
        # flip one rx byte of the first P record of the chunk
        pos = 0
        while True:
            ring, div4, cnt, lost = struct.unpack_from(F.BLK_HDR_FMT, pl, pos)
            if ring == F.RING_P and cnt:
                rec0 = pos + 8
                break
            pos += 8 + cnt * div4 * 4
        seq = struct.unpack_from("<I", pl, rec0)[0]
        pl[rec0 + 48 + 5] ^= 0x01
        ch = synth.chunk(F.CHUNK_RECS, bytes(pl), 999, 0x1234ABCD)
        p2 = os.path.join(md, "PSCLOG", "T001002.BIN")
        fb = bytearray(rd(p2, "rb"))
        fb[1536 + 512 * 10:1536 + 512 * 10 + len(ch)] = ch
        wr(p2, bytes(fb))
        rc, so, js, out = decode(md)
        self.assertEqual(rc, 0, so)
        self.assertGreaterEqual(js["conflicts"], 1)
        bad = rd(os.path.join(out, "bad.txt"))
        self.assertIn("CONFLICT P seq %d" % seq, bad)
        self.assertIn("copy 2", bad)
        say("    modified duplicate of P seq %d: CONFLICT reported with both copies" % seq)

    def test_above_confirmed_extent_listed_not_merged(self):
        d = gen("ext", "healthy", seed=42, duration_cap=100)
        md = os.path.join(TMP, "ext_m")
        if os.path.exists(md):
            shutil.rmtree(md)
        shutil.copytree(d, md, ignore=shutil.ignore_patterns("dec*"))
        truth = jload(os.path.join(md, "truth.json"))
        incomplete = [f for f in truth["files"] if f["size"] < F.SEG_SIZE]
        self.assertTrue(incomplete, "synth: expected a file in creation")
        pth = os.path.join(md, "PSCLOG", incomplete[0]["name"])
        data = bytearray(rd(pth, "rb"))
        recs = struct.pack(F.BLK_HDR_FMT, F.RING_M, 20, 1, 0) + synth.pack(F.SC_FIELDS,
                                                                             dict(seq=60000, rx=b"\xff" * 16))
        ch = synth.chunk(F.CHUNK_RECS, recs, 77, 0x1234ABCD)
        data += ch + bytes(512 - len(ch) % 512)
        wr(pth, bytes(data))
        rc, so, js, out = decode(md, times=True)
        bad = rd(os.path.join(out, "bad.txt"))
        self.assertIn("ABOVE-EXTENT", bad)
        col = P.load([os.path.join(md, "PSCLOG", n) for n in sorted(os.listdir(os.path.join(md, "PSCLOG")))])
        self.assertNotIn(60000, col.records[F.RING_M])
        say("    valid chunk above the file's confirmed extent (UHB conf %s): listed, not merged"
              % [col.extent.get(f["nnn"]) for f in incomplete])


class Meta(unittest.TestCase):
    """4.7 META repeated by the decoder from S records, with the 4.8 sector classes."""

    def test_meta_classes(self):
        import pscdec_analysis as A

        class M(object):
            pass
        m = M()
        g = {k: 0 for (k, _c, _n) in F.STATS_FIELDS}
        g.update(pid_class=(77 | (1 << 24), 0, 0, 0, 0, 0, 0, 0), sec_per_clus_bits=64 | (9 << 16),
                 ms_part_start=63, fat_start=32, fat_length=4000, fats=2, fsinfo_sector=1, data_start=8192)
        m.stats = [g]

        def run(sector, fail=True, n=10, data_ok=True):
            S = []
            for t in range(100, 100 + n):
                S.append(dict(flags=0x01 | (0 if data_ok else 0x02), sector=99999, pid=77, tick_on=t))
                S.append(dict(flags=0x01 | 0x80 | (0x02 if fail else 0), sector=sector, pid=77, tick_on=t))
            m.S = S
            return A.Analysis(m).meta_repeat()
        self.assertEqual(run(64)[0][1], "FSINFO")
        self.assertEqual(run(63 + 32)[0][1], "FAT1")
        self.assertEqual(run(63 + 4032 + 5)[0][1], "FATM")
        self.assertEqual(run(63 + 8192 + 10)[0][1], "DIR")
        self.assertEqual(run(64, n=4), [])            # fewer than 5 failures
        self.assertEqual(run(64, fail=False), [])     # writes succeed
        self.assertEqual(run(64, data_ok=False), [])  # whole-stick burst never qualifies
        say("    META: FSINFO, FAT1, FATM, DIR classified; <5 failures, good writes, whole-stick burst: none")


class Robustness(unittest.TestCase):
    """Damaged inputs never crash the decoder; damage is listed, not merged."""

    def test_garbage_file_refused(self):
        gd = os.path.join(TMP, "garbage")
        os.makedirs(gd, exist_ok=True)
        rng = random.Random(7)
        wr(os.path.join(gd, "T001001.BIN"), bytes(rng.getrandbits(8) for _ in range(200000)) + b"PSCK" * 50)
        rc, so, js, out = decode(gd, inputs=[gd], times=False, build=False)
        self.assertEqual(rc, 2, so)
        self.assertIn("no FILEHDR", so)
        say("    random bytes: refused (no FILEHDR), exit 2")

    def test_random_corruption(self):
        d = gen("H6", "H6", seed=11)
        cd = os.path.join(TMP, "corrupt")
        if os.path.exists(cd):
            shutil.rmtree(cd)
        shutil.copytree(os.path.join(d, "PSCLOG"), cd)
        rng = random.Random(99)
        p1 = os.path.join(cd, "T001001.BIN")
        data = bytearray(rd(p1, "rb"))
        for _ in range(300):
            data[rng.randrange(1536, 1200000)] ^= 1 << rng.randrange(8)
        wr(p1, bytes(data))
        rc, so, js, out = decode(d, "dec_corrupt", inputs=[cd])
        self.assertIn(rc, (0, 3), so)
        self.assertEqual(js["conflicts"], 0)
        bad = rd(os.path.join(out, "bad.txt"))
        nbad = bad.count("\nBAD bad-crc")
        self.assertGreater(nbad, 0)
        say("    300 bit flips in file 1: no crash, %d CRC-bad chunks listed, 0 conflicts, verdict %s"
              % (nbad, js["named"]))

    def test_panel_transcription(self):
        d = gen("H6", "H6", seed=11)
        spec = ("P7a=PSC STALL DUR 12.5 RDR 3.1 PNT 7|NOW 0000A1B2 PID 0077 EPC 80160008 PCNT 1|"
                "LOOP 1A2B STG 11|P08 RET -4|W 00008000|MS 1 SEC 00012345")
        rc, so, js, out = decode(d, "dec_panel", extra=["--panel", spec])
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("Memory Stick driver hang", rep)
        self.assertIn("ms_wait_ready", rep)
        say("    panel photo with EPC in ms_wait_ready and preempt count 1: reported as a Memory Stick driver hang")


# ====================================================================== G2 attempt 2
import glob                     # noqa: E402
import zlib                     # noqa: E402
import pscdec_analysis as A     # noqa: E402
import psc_maps                 # noqa: E402


def release_build():
    """The packaged build's BUILD directory (mkmaps.py): $PSC_RELEASE_BUILD,
    else the newest handoff/impl/release-*/BUILD."""
    d = os.environ.get("PSC_RELEASE_BUILD")
    if d:
        return d
    c = sorted(glob.glob("/home/ubuntu/psp/handoff/impl/release-*/BUILD"))
    return c[-1] if c else None


def w_record(epc, regs, lc=False):
    """A W record (DESIGN 1.3) packed from the format and parsed by the
    decoder's parse layer: a watchdog Nop that interrupted the joypad thread
    at `epc` with registers `regs` ({regno: value})."""
    r = [0] * 16
    for n, v in regs.items():
        r[F.REGS_ORDER.index(n)] = v & 0xFFFFFFFF
    sc = dict(seq=1, tick_in=1250, cmd=0, txlen=2, ret=3, nwords=2, ctx=F.ORIGIN_WT, wn=0,
              rx=bytes([3, 3, 0, 0xF9] + [0xFF] * 12))
    ext = dict(epc=0 if lc else epc, r=[0] * 16 if lc else r, t_busy=1, pid=25,
               ext_flags=(F.EXT_F_LC_VALID if lc else F.EXT_F_REGS_VALID | F.EXT_F_JP_TASK | F.EXT_F_IN_SYSCON),
               lc_epc=epc if lc else 0, lc_r=r if lc else [0] * 16)
    return P.norm_record(F.RING_W, synth.pack_w(sc, ext))


class StubModel(object):
    """The parts of Model that w_step and the LEDSPLIT lookup use."""
    w_step = A.Model.w_step

    def __init__(self, build):
        self.build = build
        self.epc_ok, self.epc_reason = not build.errors, "; ".join(build.errors)


class ReleaseMaps(unittest.TestCase):
    """G2 attempt 1 F3 / OD-4: the decoder reads the RELEASE epcmap.txt and
    regmap.txt written by handoff/impl/mkmaps.py (one grammar, psc_maps.py)
    and computes P2 k, P6 j (with the regmap offsets) and the LEDSPLIT loaded
    value from W records at S11, S18 and LEDRMW."""

    @classmethod
    def setUpClass(cls):
        cls.bd = release_build()
        if not cls.bd:
            raise AssertionError("no release BUILD directory (run handoff/impl/mkmaps.py)")
        cls.b = A.BuildInfo.load(os.path.join(cls.bd, "System.map"), os.path.join(cls.bd, "epcmap.txt"),
                                 os.path.join(cls.bd, "regmap.txt"),
                                 int(rd(os.path.join(cls.bd, "build_id.txt")).split()[0], 0))
        cls.m = StubModel(cls.b)
        cls.base = cls.b.sysmap["Syscon_cmd"]

    def test_maps_load(self):
        self.assertEqual(self.b.errors, [])
        labs = set(l for (_a, _b, l) in self.b.epc)
        for need in ("S0", "S11", "S14", "S15", "S18", "ENTRY", "REC", "EXIT", "LEDRMW"):
            self.assertIn(need, labs)
        self.assertEqual(A.STEP_PPOINT["S0"], "P0")
        self.assertEqual(self.b.label(self.base + 0x7c), "S0")
        say("    %s: %d EPC ranges, %d regmap labels, build_id 0x%08x"
            % (self.bd, len(self.b.epc), len(self.b.reg), self.b.build_id))

    def step(self, off, regs, lc=False):
        return self.m.w_step(w_record(self.base + off, regs, lc))

    def test_s11_k(self):
        # TX push loop (release +0x17c..+0x1c0): t0 = bytes pushed at the loop
        # top, t0 = i + 2 between "addiu t0,t0,2" (+0x19c) and the push (+0x1b4)
        cases = [(0x17c, {8: 3}, 0), (0x18c, {8: 0, 7: 0x81001000}, 0), (0x190, {8: 2, 7: 0x81001002}, 1),
                 (0x1a4, {8: 4, 7: 0x81001002}, 1), (0x1b4, {8: 4, 7: 0x81001004}, 1),
                 (0x1b8, {8: 4, 7: 0x81001004}, 2), (0x190, {8: 6, 7: 0x81001006}, 3)]
        for off, regs, k in cases:
            regs = dict(regs)
            regs[13] = 0x81001000              # t5 = tx_buf
            st = self.step(off, regs)
            self.assertEqual((st["label"], st["ppoint"], st["k"]), ("S11", "P2", k), "+%#x %s" % (off, st))
            self.assertNotIn("map_note", st)
        st = self.step(0x1a4, {8: 4, 7: 0x81001002, 13: 0x81001000}, lc=True)
        self.assertEqual((st["src"], st["k"]), ("lc_epc", 1))
        say("    S11 (P2): k from t0 with offset 0 or 2 by EPC: %d cases, epc and lc_epc" % (len(cases) + 1))

    def test_s18_j_pending(self):
        rxb = 0x81002000
        # receive loop (release +0x350..+0x398): t0 = i + 2 at the loop top up
        # to the data load (+0x364), t0 = i after it; pending between the
        # status load (+0x350) and the data load
        cases = [(0x350, 8, rxb + 8, 3, 0), (0x354, 8, rxb + 8, 3, 1), (0x364, 8, rxb + 8, 3, 1),
                 (0x368, 8, rxb + 8, 4, 0), (0x380, 8, rxb + 8, 4, 0), (0x384, 8, rxb + 10, 4, 0),
                 (0x38c, 8, rxb + 8, 4, 0), (0x350, 16, rxb + 16, 7, 0), (0x354, 16, rxb + 16, 7, 1)]
        for off, t0, a3, j, pend in cases:
            st = self.step(off, {8: t0, 7: a3, 25: rxb + 2})
            self.assertEqual((st["label"], st["ppoint"], st["j"], st["pending"]), ("S18", "P6", j, pend),
                             "+%#x %s" % (off, st))
            self.assertNotIn("map_note", st, "+%#x" % off)
        st = self.step(0x350, {8: 8, 7: rxb + 20, 25: rxb + 2})      # a3 not rx_buf + i + 2
        self.assertIn("map_note", st)
        say("    S18 (P6): j from t0 with offset 2 or 0 by EPC, pending window, ptr cross-check: %d cases"
            % len(cases))

    def test_eighth_word_every_epc(self):
        """K2 / NW1: a Nop at every instruction of the 8th iteration of the
        receive loop (t0 = 16 at its top). Between the status load and the
        data load the decoder says pending (an empty-FIFO pop is possible:
        with nwords 7|8 it names it); after the data load j = 8."""
        rxb = 0x81002000
        thr = dict(ret=-2, nwords=7, retries=0, cmd=0x08, rx=bytes([0x08, 14] + [1] * 12 + [0xFF, 0xFF]),
                   nw7or8=1)
        tmpl = A.Template()
        seen = []
        for off in range(0x350, 0x398, 4):
            epc = self.base + off
            if self.b.label(epc) != "S18":
                continue
            a3 = rxb + 16 + (2 if 0x384 <= off < 0x38c else 0)
            st = self.step(off, {8: 16, 7: a3, 25: rxb + 2})
            want_j = 7 if off < 0x368 else 8
            want_p = 1 if 0x354 <= off < 0x368 else 0
            self.assertEqual((st["j"], st["pending"]), (want_j, want_p), "+%#x" % off)
            self.assertNotIn("map_note", st, "+%#x" % off)
            cc = A.Analysis(None).crosscheck("P6", thr, tmpl, st)
            if want_p:
                self.assertIn("empty-FIFO pop", cc, "+%#x" % off)
            else:
                self.assertIn("allowed for P6 (-2 with nwords = j = %d, flagged nw7or8)" % want_j, cc)
            seen.append(off)
        self.assertEqual(len(seen), 18)
        say("    8th receive iteration, %d EPCs: pending (empty-FIFO pop named) in the 5 between the status load "
            "and the data load, j = 7 before, j = 8 after" % len(seen))

    def test_p6_crosscheck(self):
        tmpl = A.Template()
        rxb = 0x81002000
        thr7 = dict(ret=-2, nwords=7, retries=0, cmd=0x08, rx=bytes([0x08, 14] + [1] * 12 + [0xFF, 0xFF]),
                    nw7or8=1)
        st = self.step(0x350, {8: 16, 7: rxb + 16, 25: rxb + 2})      # j = 7, not pending
        cc = A.Analysis(None).crosscheck("P6", thr7, tmpl, st)
        self.assertIn("allowed for P6 (-2 with nwords = j = 7, flagged nw7or8)", cc)
        st = self.step(0x358, {8: 14, 7: rxb + 14, 25: rxb + 2})      # j = 6, pending: empty-FIFO pop
        cc = A.Analysis(None).crosscheck("P6", thr7, tmpl, st)
        self.assertIn("empty-FIFO pop", cc)
        thr5 = dict(ret=-2, nwords=5, retries=0, cmd=0x08, rx=bytes([0x08, 14] + [1] * 8 + [0xFF] * 6), nw7or8=0)
        st = self.step(0x350, {8: 8, 7: rxb + 8, 25: rxb + 2})        # j = 3, not pending, nwords 5
        cc = A.Analysis(None).crosscheck("P6", thr5, tmpl, st)
        self.assertIn("INCONSISTENT for P6", cc)
        say("    P6 cross-check: j = 7 with a flagged record allowed; pending + nwords j+1 = empty-FIFO pop; "
            "j = 3 with nwords 5 inconsistent")

    def test_ledrmw_loaded(self):
        led = [(a, b) for (a, b, l) in self.b.epc if l == "LEDRMW"]
        self.assertEqual(len(led), 2)
        for (a, b) in led:
            for epc in range(a, b, 4):
                w = w_record(epc, {5: 0x00000048, 3: 0x40})
                self.assertEqual(self.b.label(epc), "LEDRMW")
                val, row = self.b.regval("LEDRMW", "loaded", epc, w["ext"]["r"])
                self.assertEqual(val, 0x48)
        say("    LEDRMW: loaded value from a1 at every EPC of both read-modify-writes (G3 bit 3 set: 0x48)")

    def test_old_grammar_refused(self):
        d = os.path.join(TMP, "oldmap")
        os.makedirs(d, exist_ok=True)
        wr(os.path.join(d, "regmap.txt"), b"S11 i t0\nLEDRMW val v0\n")
        b = A.BuildInfo.load(None, None, os.path.join(d, "regmap.txt"), 1)
        self.assertTrue(b.errors and "PSC-REGMAP 2" in b.errors[0])
        say("    a regmap in another syntax is an error (EPC analysis refused), not a silent partial read")


class NwordsSevenOrEight(unittest.TestCase):
    """Section 17 R-1 (K9 vectors): 7 words; 8 words ending 0xFFFF; 8 words not
    ending 0xFFFF. The first two leave identical records and are flagged."""

    def rec(self, words):
        rx = bytearray([0xFF] * 16)
        for i, wv in enumerate(words):
            rx[2 * i], rx[2 * i + 1] = wv >> 8, wv & 0xFF
        nw = 7 if len(words) == 8 and words[-1] == 0xFFFF else len(words)   # the hand-off's rule (psc.c)
        sc = dict(seq=1, cmd=0x08, txlen=2, ret=rx[0], nwords=nw, ctx=F.ORIGIN_P, rx=bytes(rx))
        return P.norm_record(F.RING_P, synth.pack(F.SC_FIELDS, sc))

    def test_vectors(self):
        w7 = [0x080E, 0x0800, 0x0000, 0x0000, 0x8080, 0x0000, 0x0012]
        r7 = self.rec(w7)
        r8f = self.rec(w7 + [0xFFFF])
        r8 = self.rec(w7 + [0x34A5])
        self.assertEqual((r7["nwords"], r7["nw7or8"], A.nwset(r7)), (7, 1, (7, 8)))
        self.assertEqual((r8f["nwords"], r8f["nw7or8"], A.nwset(r8f)), (7, 1, (7, 8)))
        self.assertEqual(r7["rx"], r8f["rx"])
        self.assertEqual((r8["nwords"], r8["nw7or8"], A.nwset(r8)), (8, 0, (8,)))
        r6 = self.rec(w7[:6])
        self.assertEqual((r6["nwords"], r6["nw7or8"]), (6, 0))
        # template / code expectation by set membership (10.7 "nwords 7 or 8")
        T = A.Template()
        self.assertEqual(T.nwords(0x08, r7["rx"]), (8,))             # rx[1] = 14: exact length 8
        self.assertTrue(set(T.nwords(0x08, r7["rx"])) & set(A.nwset(r8f)))
        T.ok = True
        T.cmd[0x08] = {"nwords": (7, 8)}
        self.assertTrue(set(T.nwords(0x08, r8["rx"])) & set(A.nwset(r8)))
        say("    7 words / 8 ending 0xFFFF: same bytes, nwords 7 flagged {7, 8}; 8 not ending 0xFFFF: 8 exact; "
            "set membership against template and code expectation")

    def test_evidence_text(self):
        """G2 attempt 2 N3: the H4/WB/WT evidence lines print a flagged record as 7|8
        (end to end: Stage3Closure.test_n3_a5_evidence_prints_7or8)."""
        w7 = [0x080E, 0x0800, 0x0000, 0x0000, 0x8080, 0x0000, 0x0012]
        self.assertEqual(A.nwtext(self.rec(w7)), "7|8")
        self.assertEqual(A.nwtext(self.rec(w7 + [0xFFFF])), "7|8")
        self.assertEqual(A.nwtext(self.rec(w7 + [0x34A5])), "8")
        self.assertEqual(A.nwtext(self.rec(w7[:6])), "6")
        say("    evidence text: 7 words and 8 ending 0xFFFF print 7|8, exact counts print the number (N3)")

    def test_report_counts(self):
        d = gen("H1", "H1", seed=11)
        rc, so, js, out = decode(d, "dec_nw")
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("## `nwords` 7 or 8 (section 17 R-1)", rep)
        hdr = rd(os.path.join(out, "p.csv")).splitlines()[0]
        self.assertIn("nwords", hdr)
        self.assertIn("nw7or8", hdr)
        say("    REPORT has the nw7or8 section; p.csv keeps nwords and the flag")


class BuildCheck(unittest.TestCase):
    """Section 17 R-4 (K9): the decoder takes build_id from BUILD/build_id.txt
    and refuses the EPC analysis for another build (the verifier's rebuild of
    the same commit has another banner, so another build_id); each FILEHDR's
    /proc/version CRC-32 is checked against stats word 2."""

    def test_rebuild_refused(self):
        d = gen("H4", "H4", seed=11)
        rc, so, js, out = decode(d, "dec_bid_ok")
        self.assertEqual(rc, 0, so)
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("EPC analysis enabled", rep)
        self.assertNotIn("FILEHDR /proc/version CRC-32", rep)
        bd2 = os.path.join(d, "build_rebuild")
        if os.path.exists(bd2):
            shutil.rmtree(bd2)
        shutil.copytree(os.path.join(d, "build"), bd2)
        other = zlib.crc32(synth.SYNTH_BANNER.replace(b"synth", b"synth rebuild")) & 0xFFFFFFFF
        wr(os.path.join(bd2, "build_id.txt"), b"0x%08x\n" % other)
        synth.write_sums(bd2)                  # a consistent BUILD of the same (synthetic) image
        rc, so, js, out = decode(d, "dec_bid_bad", extra=["--build", bd2, "--expect-image", synth.SYNTH_IMAGE_SHA256],
                                 build=False)
        self.assertEqual(rc, 0, so)
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("EPC analysis REFUSED", rep)
        self.assertIn("!= build 0x%08x" % other, rep)
        self.assertFalse(js["epc_ok"])
        say("    packaged build_id: EPC analysis enabled; a rebuild's build_id: REFUSED with the reason, parsing runs")

    def test_filehdr_version_crc(self):
        d = gen("healthy", "healthy", seed=11)
        cd = os.path.join(TMP, "fhver")
        if os.path.exists(cd):
            shutil.rmtree(cd)
        shutil.copytree(os.path.join(d, "PSCLOG"), cd)
        p1 = sorted(glob.glob(os.path.join(cd, "T*.BIN")))[0]
        data = bytearray(rd(p1, "rb"))
        i = data.find(b"(psc synth)")
        data[i + 1] = ord("P")                 # one byte of /proc/version in the FILEHDR
        hdr = 20
        plen = struct.unpack_from("<I", data, 8)[0]
        crc = zlib.crc32(bytes(data[hdr:hdr + plen])) & 0xFFFFFFFF
        struct.pack_into("<I", data, 16, crc)   # keep the FILEHDR chunk itself valid
        wr(p1, bytes(data))
        rc, so, js, out = decode(d, "dec_fhver", inputs=[cd])
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("FILEHDR /proc/version CRC-32", rep)
        say("    a FILEHDR whose /proc/version CRC-32 differs from stats word 2 is reported (10.1)")


class Stage3Closure(unittest.TestCase):
    """Stage 3 closure (DESIGN 18): G2 attempt 2 N3 (7|8 in the evidence
    lines), red team K3 (image identity), K5 (G3-low gap and the MMIO bound),
    K6 (windows near a tick edge), K8 (stack headroom), review A-5 (the
    ambiguity per classification window)."""

    def test_n3_a5_evidence_prints_7or8(self):
        d = gen("H4nop7", "H4", seed=11, nop7=True)
        rc, so, js, out = decode(d, "dec_n3")
        self.assertEqual(rc, 0, so)
        self.assertIn("H4", js["triggers"])
        rep = rd(os.path.join(out, "REPORT.md"))
        h4 = [l for l in rep.splitlines() if l.startswith("- **H4**:")]
        self.assertTrue(h4, rep[:2000])
        self.assertIn("Nop's own ret 36 nwords 7|8", h4[0])
        self.assertNotIn("nwords 7 ", h4[0])
        wt = [l for l in rep.splitlines() if l.startswith("- WT seq") and "t_busy 1" in l]
        self.assertTrue(wt and "nwords 7|8" in wt[0], wt)
        self.assertIn("`nwords` 7 or 8 live in the classification window", rep)
        self.assertIn("the ambiguity is live in this window", rep)
        say("    H4 evidence and the WT listing print 'nwords 7|8' for a flagged Nop reply (N3); the "
            "classification window says the ambiguity is live (A-5)")

    def test_n3_wb_line(self):
        r = {"nwords": 7, "nw7or8": 1}
        self.assertEqual(A.nwtext(r), "7|8")
        self.assertEqual(A.nwtext({"nwords": 7, "nw7or8": 0}), "7")
        src = rd(os.path.join(DEC, "pscdec_analysis.py"))
        wb = src[src.index('ev["WB"].append('):src.index('ev["WB"].append(') + 400]
        self.assertIn("nwords %s", wb)
        self.assertIn("nwtext(w)", wb)
        say("    nwtext: 7|8 when flagged, else the raw value; the WB line uses it")

    def test_k3_image_identity(self):
        import pscdec
        rel = os.environ.get("PSC_PACKAGE_BUILD", "/home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD")
        if os.path.isdir(rel):
            img = rd(os.path.join(rel, "IMAGE.sha256")).split()[0]
            exp, errs, note = pscdec.image_identity(rel, img, A.RELEASE_IMAGE_SHA256)
            self.assertEqual(errs, [], errs)
            self.assertEqual(img, A.RELEASE_IMAGE_SHA256)
            say("    packaged BUILD: IMAGE.sha256 = the released image, %s" % note)
        d = gen("H4", "H4", seed=11)
        bd = os.path.join(d, "build")
        exp, errs, note = pscdec.image_identity(bd, synth.SYNTH_IMAGE_SHA256, A.RELEASE_IMAGE_SHA256)
        self.assertTrue(any("not the released image" in e for e in errs), errs)
        exp, errs, note = pscdec.image_identity(bd, synth.SYNTH_IMAGE_SHA256, "any")
        self.assertEqual((exp, errs), (None, []))
        self.assertIn("DISABLED", note)
        # an identity-pinned rebuild of ANOTHER commit: same banner, same build_id, maps of other code,
        # another image hash -> refused by the image hash although build_id matches (K3, K9)
        bd2 = os.path.join(d, "build_pinned_other")
        if os.path.exists(bd2):
            shutil.rmtree(bd2)
        shutil.copytree(bd, bd2)
        other_img = hashlib.sha256(b"identity-pinned rebuild of another commit").hexdigest()
        synth.write_sums(bd2, other_img)
        rc, so, js, out = decode(d, "dec_k3", extra=["--build", bd2, "--expect-image", synth.SYNTH_IMAGE_SHA256],
                                 build=False)
        self.assertEqual(rc, 0, so)
        rep = rd(os.path.join(out, "REPORT.md"))
        self.assertIn("EPC analysis REFUSED", rep)
        self.assertIn("not the released image", rep)
        self.assertFalse(js["epc_ok"])
        self.assertNotIn("!= build", js["epc_reason"])          # build_id itself matched
        # a BUILD file changed after SHA256SUMS was written -> refused
        bd3 = os.path.join(d, "build_tampered")
        if os.path.exists(bd3):
            shutil.rmtree(bd3)
        shutil.copytree(bd, bd3)
        with open(os.path.join(bd3, "regmap.txt"), "a") as f:
            f.write("# edited\n")
        exp, errs, note = pscdec.image_identity(bd3, synth.SYNTH_IMAGE_SHA256, synth.SYNTH_IMAGE_SHA256)
        self.assertTrue(any("regmap.txt does not match" in e for e in errs), errs)
        # the default (no --expect-image) refuses the synthetic BUILD: the release hash is pinned
        rc, so, js, out = decode(d, "dec_k3_default", extra=["--build", bd], build=False)
        self.assertFalse(js["epc_ok"])
        self.assertIn(A.RELEASE_IMAGE_SHA256, js["epc_reason"])
        say("    image identity: packaged BUILD accepted; a pinned-identity BUILD of another image refused with "
            "build_id matching; a tampered BUILD file refused; the default pins the released image")

    def test_k5_k6_k8_report_lines(self):
        d = gen("healthy", "healthy", seed=11)
        rc, so, js, out = decode(d, "dec_k568")
        self.assertEqual(rc, 0, so)
        rep = rd(os.path.join(out, "REPORT.md"))
        for need in ("G3-low gap (K5): recorded g", "1st percentile", "baseline equivalent",
                     "MMIO latency bound", "cmd 0x08, delta", "cmd 0x33, delta", "stack headroom at the Nop (K8)",
                     "the one masking direction (7.3, K5)"):
            self.assertIn(need, rep)
        say("    REPORT step 6 prints K5 (gap min/p1/median, with/without instrumentation, m bound), K6 (edge "
            "windows), K8 (stack headroom); step 8 names the gap as the one masking direction")

    def _rec(self, **kw):
        r = dict(cmd=0x08, ret=0x22, retries=0, drain=0, dtick=0, wn=0, preempt_delta=0, lc_n=0, ack_polls=20,
                 nwords=5, nw7or8=0, rx=bytes([0x22, 9, 8]) + bytes(13), c_in=1000, c_out=1000, tick_in=100,
                 seq=1, ctx=0)
        r.update(kw)
        return r

    def test_k5_mmio_bound_arithmetic(self):
        class M(object):
            pass
        m = M()
        I = A.CMD_I0[0x08] + 11 * 20 + 15 * 5 + 5 * 9          # the path's instructions (744, as measured)
        N = 16 + 20 + 2 * 5                                     # its MMIO accesses (46)
        mm = 33                                                 # 33 Counts per access
        m.P = [self._rec(c_out=1000 + I + N * mm), self._rec(seq=2, c_out=1000 + I + N * 50),
               self._rec(seq=3, c_out=1000 + I, retries=1)]      # the retried one is not eligible
        an = A.Analysis.__new__(A.Analysis)
        an.m = m
        best, n, arg = an.mmio_bound()
        self.assertEqual((round(best, 6), n, arg["seq"]), (mm, 2, 1))
        self.assertEqual(I, 744)
        say("    m bound: (c_out - c_in - I) / N with I = 404 + 11 ack + 15 nwords + 5 rx[1], N = 16 + ack + 2 nwords; "
            "ineligible records skipped")

    def test_k6_k8_counts(self):
        class M(object):
            pass
        m = M()
        CPT = A.CPT
        m.P = [self._rec(tick_in=1250, c_in=10, c_out=5000),                     # S5 at 210 < delta: start after edge
               self._rec(seq=2, tick_in=2499, c_in=CPT - 3000, c_out=100, dtick=1),  # S20 at CPT-88 of 2499: end before
               self._rec(seq=4, tick_in=3749, c_in=CPT - 3000, c_out=200, dtick=1),  # S20 at 12 of 3750: end after (wd)
               self._rec(seq=3, tick_in=3000, c_in=500000, c_out=600000)]          # far from both edges
        an = A.Analysis.__new__(A.Analysis)
        an.m = m
        lines, c, n = an.edge_windows()
        self.assertEqual(c[(0x08, "start after edge")], 1)
        self.assertEqual(c[(0x08, "start after watchdog edge")], 1)
        self.assertEqual(c[(0x08, "end before edge")], 1)
        self.assertEqual((c[(0x08, "end after edge")], c[(0x08, "end after watchdog edge")]), (1, 1))
        self.assertEqual(n[0x08], 4)
        m.WT = [dict(seq=1, ext=dict(ext_flags=F.EXT_F_REGS_VALID | F.EXT_F_KMODE, sp=0x81F00000 + 1500)),
                dict(seq=2, ext=dict(ext_flags=F.EXT_F_REGS_VALID | F.EXT_F_KMODE, sp=0x81F02000 + 7000)),
                dict(seq=3, ext=dict(ext_flags=F.EXT_F_REGS_VALID, sp=0x40001000))]
        lines, flagged = an.stack_headroom()
        self.assertEqual(flagged, [1])                         # 1500 - 52 - 520 = 928 < 1024
        self.assertIn("minimum sp - stack base - 52 = 1448 B", lines[0])
        m.WT.append(dict(seq=4, ext=dict(ext_flags=F.EXT_F_REGS_VALID | F.EXT_F_KMODE, sp=0x81F04000)))
        lines, flagged = an.stack_headroom()                   # sp on a block boundary: an empty stack, 8140 B
        self.assertEqual(flagged, [1])
        self.assertIn("1 user-mode", lines[0])
        say("    K6: windows within delta of a (watchdog) tick edge counted; K8: kernel-mode headroom "
            "sp - stack base - 52 - 520 flagged below 1 KB, user-mode Nops on the kernel stack top")


if __name__ == "__main__":
    print("decoder tests; scratch %s" % TMP)
    r = unittest.main(verbosity=2, exit=False).result
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(0 if r.wasSuccessful() else 1)
