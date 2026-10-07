"""pscdec_parse.py - file/image layer of the PSC decoder (DESIGN.md rev 6, section 10.2-10.4).

Chunk framing and CRC with the per-boot nonce, run selection by FILEHDR run and
nonce, the confirmed-extent rule, (ring, seq) merge with duplicate removal and
conflict reporting, the raw-image scan, and the raw-image-required rule.

Every record offset and struct string comes from psc_format.py (the mirror of
include/linux/psc_format.h); nothing here retypes an offset.
"""

import mmap
import os
import re
import struct
import zlib

import psc_format as F

HDR = struct.Struct(F.CHUNK_HDR_FMT)
BLK = struct.Struct(F.BLK_HDR_FMT)
_FH = struct.Struct(F.FILEHDR_FMT)
_UHB = struct.Struct(F.UHB_FMT)
_STATS = struct.Struct('<192I')

KNOWN_TYPES = set(range(len(F.CHUNK_NAMES)))


def crc_ok(ctype, payload, crc, nonce):
    """10.2: plain CRC-32 for FILEHDR, nonce-seeded for every other type."""
    if ctype == F.CHUNK_FILEHDR:
        return (zlib.crc32(payload, 0) & 0xFFFFFFFF) == crc
    if nonce is None:
        return False
    return (zlib.crc32(payload, nonce) & 0xFFFFFFFF) == crc


class Chunk(object):
    __slots__ = ("src", "off", "ctype", "hver", "length", "fseq", "crc", "payload",
                 "status", "nonce", "flush_tick", "file")

    def __init__(self, src, off, ctype, hver, length, fseq, crc):
        self.src, self.off, self.ctype, self.hver = src, off, ctype, hver
        self.length, self.fseq, self.crc = length, fseq, crc
        self.payload = None
        self.status = None      # good / bad-crc / truncated / other-boot / bad-header
        self.nonce = None
        self.flush_tick = None  # UHB stats_now_tick of the flush it belongs to
        self.file = None

    @property
    def end(self):
        return self.off + F.CHUNK_HDR_SIZE + F.pad4(self.length)

    @property
    def name(self):
        return F.CHUNK_NAMES[self.ctype] if self.ctype in KNOWN_TYPES else "type%d" % self.ctype

    def __repr__(self):
        return "<%s %s@%d len=%d fseq=%s %s>" % (self.name, self.src, self.off, self.length,
                                                 self.fseq, self.status)


def candidates(buf, src):
    """All chunk headers at 4-byte offsets (10.2 'scan for magic at every
    4-byte offset').  bytes.find is used to jump between magic hits, which is
    equivalent to testing every 4-byte offset and fast on large images."""
    out = []
    n = len(buf)
    pos = 0
    while True:
        i = buf.find(F.CHUNK_MAGIC, pos)
        if i < 0:
            break
        pos = i + 1
        if i & 3:
            continue
        if i + F.CHUNK_HDR_SIZE > n:
            c = Chunk(src, i, -1, 0, 0, 0, 0)
            c.status = "truncated-header"
            out.append(c)
            break
        _m, ctype, hver, ln, fseq, crc = HDR.unpack_from(buf, i)
        out.append(Chunk(src, i, ctype, hver, ln, fseq, crc))
    return out


def accept(buf, cands, nonce, other_nonces=(), filehdr_only=False):
    """Sequential acceptance (10.2 Parsing): a chunk is accepted if its type is
    known, hver == 5, len <= 65,536, the bytes exist and the CRC matches (plain
    for FILEHDR, seeded with the run's nonce otherwise); else advance 4 bytes.
    Candidates inside an accepted chunk are skipped.  Returns (good, rejected);
    rejected chunks carry a status: bad-header, truncated, bad-crc, other-boot
    (CRC verifies under another boot's nonce, IF10), unchecked (filehdr_only)."""
    n = len(buf)
    good, rej = [], []
    next_free = 0
    for c in cands:
        if c.off < next_free:
            continue
        if c.status == "truncated-header":
            rej.append(c)
            continue
        if c.ctype not in KNOWN_TYPES or c.hver != F.FORMAT_VERSION or c.length > F.CHUNK_LEN_MAX:
            c.status = "bad-header"
            rej.append(c)
            continue
        p0 = c.off + F.CHUNK_HDR_SIZE
        if p0 + c.length > n:
            c.status = "truncated"
            c.payload = bytes(buf[p0:n])
            rej.append(c)
            continue
        if filehdr_only and c.ctype != F.CHUNK_FILEHDR:
            c.status = "unchecked"
            continue
        payload = bytes(buf[p0:p0 + c.length])
        if crc_ok(c.ctype, payload, c.crc, nonce):
            c.payload, c.status, c.nonce = payload, "good", (0 if c.ctype == F.CHUNK_FILEHDR else nonce)
            good.append(c)
            next_free = min(c.end, n)
            continue
        for on in other_nonces:
            if on is not None and on != nonce and crc_ok(c.ctype, payload, c.crc, on):
                c.status, c.nonce, c.payload = "other-boot", on, payload
                break
        else:
            c.status = "bad-crc"
            c.payload = payload
        rej.append(c)
    return good, rej


def parse_filehdr(payload):
    if len(payload) < F.FILEHDR_FIXED:
        return None
    fh = dict(zip([f[0] for f in F.FILEHDR_FIELDS], _FH.unpack_from(payload, 0)))
    if fh["magic"] != F.FILEHDR_MAGIC or fh["fmt"] != F.FORMAT_VERSION:
        return None
    if len(payload) >= F.FILEHDR_FIXED + F.STATS_SIZE:
        fh["stats"] = parse_stats(payload[F.FILEHDR_FIXED:F.FILEHDR_FIXED + F.STATS_SIZE])
    ver = payload[F.FILEHDR_FIXED + F.STATS_SIZE:]
    fh["version_raw"] = ver.split(b"\0", 1)[0]      # 10.1: CRC-32 against stats word 2 (R-4)
    fh["version"] = fh["version_raw"].decode("ascii", "replace")
    return fh


def parse_stats(b):
    return F.unpack(F.STATS_FIELDS, b, 0)


def parse_uhb(b):
    return F.unpack(F.UHB_FIELDS, b, 0)


def norm_record(ring, raw):
    """Unpack one ring record into a dict.  W records are flattened to the SC
    names plus an 'ext' dict (C: w.sc.*, w.ext.*)."""
    d = F.unpack(F.RING_FIELDS[ring], raw, 0)
    if ring == F.RING_W:
        sc = {k[3:]: v for k, v in d.items() if k.startswith("sc.")}
        sc["ext"] = {k[4:]: v for k, v in d.items() if k.startswith("ext.")}
        d = sc
    d["_ring"] = ring
    if "nwords" in d and "rx" in d:
        # DESIGN 1.2 offset 22 / 10.3 (section 17 R-1): nwords = 7 with
        # rx[14] = rx[15] = 0xff means "7 or 8" (an 8th word 0xFFFF leaves the
        # same loop state and the same 16 bytes); every rule reads the set
        d["nw7or8"] = 1 if (d["nwords"] == 7 and d["rx"][14] == 0xFF and d["rx"][15] == 0xFF) else 0
    return d


def parse_recs(payload, salvage=False):
    """RECS payload (10.2): blocks '<BBHI' + count records.  Returns
    (blocks, problems).  Each block = dict(ring, resend, count, lost, recs=[raw bytes]).
    With salvage=True a short payload yields every record wholly present."""
    blocks, probs = [], []
    pos, n = 0, len(payload)
    seen_new = set()
    seen_resend = set()
    while pos < n:
        if pos + F.BLK_HDR_SIZE > n:
            probs.append("block header cut at %d" % pos)
            break
        ring_b, div4, count, lost = BLK.unpack_from(payload, pos)
        ring, resend = ring_b & F.BLK_RING_MASK, bool(ring_b & F.BLK_RESEND)
        if ring >= F.NRINGS or F.RING_DIV4[ring] != div4:
            probs.append("bad block header at %d (ring byte %d, div4 %d)" % (pos, ring_b, div4))
            break
        pos += F.BLK_HDR_SIZE
        size = F.RING_RECSIZE[ring]
        recs = []
        for k in range(count):
            if pos + size > n:
                if not salvage:
                    probs.append("block %s cut after %d of %d records" % (F.RING_NAMES[ring], k, count))
                pos = n
                break
            recs.append(payload[pos:pos + size])
            pos += size
        if resend:
            if lost:
                probs.append("re-send block %s with lost=%d (must be 0)" % (F.RING_NAMES[ring], lost))
            if ring in seen_new or ring in seen_resend:
                probs.append("re-send block %s out of order" % F.RING_NAMES[ring])
            seen_resend.add(ring)
        else:
            if ring in seen_new:
                probs.append("second new-records block for ring %s" % F.RING_NAMES[ring])
            seen_new.add(ring)
        blocks.append({"ring": ring, "resend": resend, "count": count, "lost": lost, "recs": recs})
    if not salvage and pos == n and len(seen_new) != F.NRINGS:
        probs.append("RECS chunk without a new-records block for ring(s) %s" %
                     ",".join(F.RING_NAMES[r] for r in range(F.NRINGS) if r not in seen_new))
    return blocks, probs


# ------------------------------------------------------------------ EVENT grammar
# DESIGN 10.2 lists the EVENT words; the exact line syntax is the collector's.
# The decoder accepts an optional leading tick stamp ("12345 ", "t=12345 ",
# "[12345] ") and matches the words below (interface item, IMPLEMENTATION notes).
_STAMP = re.compile(r'^\s*(?:\[?t?=?(\d+)\]?[:\s]\s*)?(.*)$')
NAME_RE = re.compile(r'T(\d{3})(\d{3})(?:\.BIN)?', re.I)

RAW_REQUIRED_EVENTS = [   # 10.2 "the raw image is the primary path whenever ..."
    ("flush meta err", re.compile(r'^flush meta err\b')),
    ("flush fail", re.compile(r'^flush fail\b')),
    ("stop", re.compile(r'^(?:segment\s+)?stop\b')),
    ("abandon", re.compile(r'^(?:segment\s+)?abandon\b')),
    ("meta err", re.compile(r'^meta err\b')),
    ("read-only", re.compile(r'^read-?only\b')),
    ("takeover", re.compile(r'^takeover\b')),
    ("region bad", re.compile(r'^region bad\b')),
]


def split_event_line(line):
    m = _STAMP.match(line)
    tick = int(m.group(1)) if m.group(1) else None
    return tick, m.group(2).strip()


def name_seg(text):
    m = NAME_RE.search(text)
    return (int(m.group(1)), int(m.group(2))) if m else None


# ------------------------------------------------------------------ inputs
class Source(object):
    """A copied T*.BIN file or a raw image region group."""

    def __init__(self, path, kind):
        self.path, self.kind = path, kind
        self.size = os.path.getsize(path)
        self.fh = None          # FILEHDR dict (files) / nearest FILEHDR (raw groups)
        self.fh_off = None
        self.good, self.rej = [], []
        self.ignored = None     # reason if not part of the selected run

    @property
    def name(self):
        return os.path.basename(self.path)


def _open_buf(path):
    f = open(path, "rb")
    size = os.fstat(f.fileno()).st_size
    if size == 0:
        f.close()
        return None, b""
    return f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)


class Collection(object):
    """Everything the parse layer found for one decode."""

    def __init__(self):
        self.sources = []           # file Sources
        self.raw = None             # raw image path
        self.raw_groups = []        # (fh_off, fh) per FILEHDR of the run in the image
        self.run = None
        self.nonce = None
        self.runs = {}              # (run, nonce) -> [descriptions]
        self.notes = []
        self.anomalies = []         # (kind, text)
        self.chunks = []            # accepted chunks of the selected run (files + raw), merged
        self.above_extent = []      # chunks listed, not merged
        self.unverified = []        # salvage of truncated/torn tail RECS chunks (listed only)
        self.bad = []               # rejected chunks (bad.txt)
        self.other_boot = []        # chunks of another boot
        self.extent = {}            # seg nnn -> confirmed extent (bytes)
        self.extent_src = {}
        self.records = {r: {} for r in range(F.NRINGS)}   # ring -> seq -> rec dict
        self.rec_src = {r: {} for r in range(F.NRINGS)}
        self.conflicts = []
        self.dup_exact = 0
        self.dropped_writing = 0
        self.only_in_image = []
        self.block_lost = []        # (ring, first seq of block, lost, src)
        self.uhb = []
        self.stats = []
        self.events = []            # (tick or None, text, chunk)
        self.kmsg = []
        self.procs = []
        self.raw_required = []      # reasons
        self.refused = None         # run-selection refusal text
        self.raw_source = None


def load(paths, raw=None, run=None, nonce=None):
    col = Collection()
    col.raw = raw
    # ---- pass 1: FILEHDRs (plain CRC) of every input
    fileinfo = []
    for p in paths:
        s = Source(p, "file")
        f, buf = _open_buf(p)
        cands = candidates(buf, s.name) if len(buf) else []
        good, _ = accept(buf, cands, None, filehdr_only=True)
        fhs = [(c.off, parse_filehdr(c.payload)) for c in good if c.ctype == F.CHUNK_FILEHDR]
        fhs = [(o, fh) for (o, fh) in fhs if fh]
        if fhs:
            s.fh_off, s.fh = fhs[0]
            if s.fh_off != 0:
                col.anomalies.append(("filehdr", "%s: FILEHDR at offset %d, not 0" % (s.name, s.fh_off)))
            for (o, fh) in fhs[1:]:
                col.anomalies.append(("filehdr", "%s: second FILEHDR at offset %d (run %d seg %d)"
                                      % (s.name, o, fh["run"], fh["seg"])))
        fileinfo.append((s, cands))
        col.sources.append(s)
        if f:
            buf.close()
            f.close()
    raw_fhs = []
    raw_cands = None
    if raw:
        f, buf = _open_buf(raw)
        raw_cands = candidates(buf, "RAW")
        good, _ = accept(buf, raw_cands, None, filehdr_only=True)
        raw_fhs = [(c.off, parse_filehdr(c.payload)) for c in good if c.ctype == F.CHUNK_FILEHDR]
        raw_fhs = [(o, fh) for (o, fh) in raw_fhs if fh]
        if f:
            buf.close()
            f.close()
        # every chunk candidate was re-created by accept(); rebuild fresh ones in pass 2
    # ---- run selection (10.2, A5 IF10)
    for s in col.sources:
        if s.fh:
            col.runs.setdefault((s.fh["run"], s.fh["nonce"]), []).append("file %s seg %03d inst %d"
                                                                          % (s.name, s.fh["seg"], s.fh["inst"]))
    for (o, fh) in raw_fhs:
        col.runs.setdefault((fh["run"], fh["nonce"]), []).append("image @%d seg %03d" % (o, fh["seg"]))
    if not col.runs:
        col.refused = "no FILEHDR found in any input: run and nonce unknown"
        return col
    run_nos = sorted(set(r for (r, _n) in col.runs))
    sel_run = run if run is not None else run_nos[-1]
    nonces = sorted(set(n for (r, n) in col.runs if r == sel_run))
    if nonce is not None:
        if (sel_run, nonce) not in col.runs:
            col.refused = "run %d with nonce 0x%08x not found" % (sel_run, nonce)
            return col
        nonces = [nonce]
    if not nonces:
        col.refused = "run %d not found (runs present: %s)" % (sel_run, run_nos)
        return col
    if len(nonces) > 1:
        col.refused = ("run %d appears with %d different nonces (%s): files of two boots carry the "
                       "same run number; refusing to merge them. Choose one with --nonce."
                       % (sel_run, len(nonces), ", ".join("0x%08x" % n for n in nonces)))
        return col
    col.run, col.nonce = sel_run, nonces[0]
    all_nonces = sorted(set(n for (_r, n) in col.runs))
    for (r, n), desc in sorted(col.runs.items()):
        if (r, n) != (col.run, col.nonce):
            col.notes.append("other run %d nonce 0x%08x ignored: %s" % (r, n, "; ".join(desc)))
    # ---- pass 2: accept with the run's nonce
    for (s, _c) in fileinfo:
        if s.fh and (s.fh["run"], s.fh["nonce"]) != (col.run, col.nonce):
            s.ignored = "run %d nonce 0x%08x" % (s.fh["run"], s.fh["nonce"])
            continue
        f, buf = _open_buf(s.path)
        cands = candidates(buf, s.name) if len(buf) else []
        s.good, s.rej = accept(buf, cands, col.nonce, all_nonces)
        if not s.fh:
            col.anomalies.append(("filehdr", "%s: no FILEHDR of any run; chunks checked with run %d's nonce"
                                  % (s.name, col.run)))
            if not s.good:
                s.ignored = "no FILEHDR and no chunk of the selected run"
        for c in s.good:
            c.file = s
        _salvage(col, s)
        if f:
            buf.close()
            f.close()
    raw_good = []
    if raw:
        f, buf = _open_buf(raw)
        cands = candidates(buf, "RAW")
        good, rej = accept(buf, cands, col.nonce, all_nonces)
        groups = [(o, fh) for (o, fh) in raw_fhs if (fh["run"], fh["nonce"]) == (col.run, col.nonce)]
        groups.sort()
        col.raw_groups = groups
        rs = Source(raw, "raw")
        rs.good, rs.rej = good, rej
        for c in good:
            c.file = rs
        raw_good = good
        col.bad.extend(c for c in rej if c.status in ("bad-crc", "bad-header", "truncated"))
        col.other_boot.extend(c for c in rej if c.status == "other-boot")
        if f:
            buf.close()
            f.close()
        col.raw_source = rs
    for s in col.sources:
        if s.ignored:
            continue
        col.bad.extend(c for c in s.rej if c.status in ("bad-crc", "bad-header", "truncated", "truncated-header"))
        col.other_boot.extend(c for c in s.rej if c.status == "other-boot")
    _assign_flush_ticks(col, raw_good)
    _side_chunks(col, raw_good)
    _extents(col)
    _merge(col, raw_good)
    _raw_rule(col)
    return col


def _salvage(col, s):
    """Truncation recovery (Stage 3 'Truncation'): the tail chunk cut by the
    end of the file, or a CRC-bad RECS chunk that starts exactly where the
    last accepted chunk of the file ends (a torn last flush), is parsed
    structurally; its whole records are LISTED as unverified, never merged
    (10.2: a chunk that fails its CRC is dropped)."""
    if not s.good:
        return
    last_end = max(c.end for c in s.good)
    for c in s.rej:
        if c.ctype != F.CHUNK_RECS or c.payload is None:
            continue
        if c.status == "truncated" or (c.status == "bad-crc" and c.off == last_end):
            blocks, _p = parse_recs(c.payload, salvage=True)
            for b in blocks:
                for raw in b["recs"]:
                    col.unverified.append((s.name, c.off, c.status, b["ring"], raw))


def _iter_good(col, raw_good):
    for s in col.sources:
        if s.ignored:
            continue
        for c in s.good:
            yield c
    for c in raw_good:
        yield c


def _assign_flush_ticks(col, raw_good):
    """A flush = the chunks up to and including the PAD that ends it (10.2).
    Each chunk gets the UHB stats_now_tick of its flush (for EVENT timing)."""
    seqs = [[c for c in s.good] for s in col.sources if not s.ignored] + [list(raw_good)]
    for chunks in seqs:
        chunks.sort(key=lambda c: c.off)
        group = []
        for c in chunks:
            group.append(c)
            if c.ctype == F.CHUNK_PAD:
                _close_group(group)
                group = []
        _close_group(group)


def _close_group(group):
    tick = None
    for c in group:
        if c.ctype == F.CHUNK_UHB and len(c.payload) >= F.UHB_SIZE:
            tick = _UHB.unpack_from(c.payload, 0)[1]
    for c in group:
        c.flush_tick = tick


def _side_chunks(col, raw_good):
    seen = set()
    for c in _iter_good(col, raw_good):
        key = (c.ctype, c.payload)
        dup = key in seen
        seen.add(key)
        if c.ctype == F.CHUNK_UHB and not dup:
            u = parse_uhb(c.payload)
            u["_src"] = (c.file.name, c.off)
            col.uhb.append(u)
        elif c.ctype == F.CHUNK_STATS and not dup:
            st = parse_stats(c.payload)
            st["_src"] = (c.file.name, c.off)
            col.stats.append(st)
        elif c.ctype == F.CHUNK_EVENT and not dup:
            for line in c.payload.decode("ascii", "replace").splitlines():
                if line.strip():
                    tick, text = split_event_line(line)
                    col.events.append((tick if tick is not None else c.flush_tick, text, c))
        elif c.ctype == F.CHUNK_KMSG and not dup:
            col.kmsg.append((c.flush_tick, c.payload))
        elif c.ctype == F.CHUNK_PROCS and not dup:
            col.procs.append((c.flush_tick, c.payload.decode("ascii", "replace")))
    col.uhb.sort(key=lambda u: (u["stats_now_tick"], u["tickno"]))
    col.stats.sort(key=lambda s: s["now_tick"])
    col.events.sort(key=lambda e: (e[0] if e[0] is not None else -1))


def _bump(col, seg, val, why):
    if seg is None:
        return
    if val > col.extent.get(seg, -1):
        col.extent[seg] = val
        col.extent_src[seg] = why


def _extents(col):
    """Confirmed extent per file, keyed by FILEHDR seg (10.2: 'segment ready' =
    SEG; 'stop <name> <conf>'; UHB seg conf for the file in creation)."""
    for (tick, text, _c) in col.events:
        ns = name_seg(text)
        seg = ns[1] if ns and ns[0] == col.run else None
        if re.match(r'^(?:segment\s+)?ready\b', text):
            _bump(col, seg, F.SEG_SIZE, "EVENT segment ready")
        m = re.match(r'^(?:segment\s+)?stop\s+\S+\s+(\d+)', text)
        if m:
            _bump(col, seg, int(m.group(1)), "EVENT stop")
    for u in col.uhb:
        d = F.uhb_seg_decode(u["seg"])
        if d["in_progress"] and d["creating"]:
            _bump(col, d["creating"], d["conf"], "UHB seg (tick %d)" % u["stats_now_tick"])


def _file_seg_of(col, c):
    """seg nnn and offset within the file for a chunk (raw: nearest preceding FILEHDR)."""
    s = c.file
    if s.kind == "file":
        return (s.fh["seg"] if s.fh else None), c.off
    best = None
    for (o, fh) in col.raw_groups:
        if o <= c.off:
            best = (o, fh)
    if best is None:
        return None, None
    return best[1]["seg"], c.off - best[0]


def _merge(col, raw_good):
    """Records merge by (ring, seq) (10.2, 10.3): exact duplicates removed, a
    duplicate with different content is a conflict reported with both copies,
    seq 0xFFFFFFFF dropped.  Chunks above their file's confirmed extent are
    listed, not merged.  Files first, then the raw image (records only in the
    image are listed)."""
    no_ext_warned = set()
    for phase, chunks in (("file", [c for c in _iter_good(col, []) ]), ("raw", list(raw_good))):
        chunks = sorted(chunks, key=lambda c: (_file_seg_of(col, c)[0] or 0, c.file.name, c.off))
        for c in chunks:
            if c.ctype == F.CHUNK_PAD:
                continue
            seg, rel = _file_seg_of(col, c)
            if c.ctype != F.CHUNK_FILEHDR and seg is not None and rel is not None:
                ext = col.extent.get(seg)
                if ext is None:
                    if (phase, seg) not in no_ext_warned:
                        no_ext_warned.add((phase, seg))
                        col.anomalies.append(("extent", "seg %03d (%s): no confirmed-extent evidence "
                                              "(no 'segment ready', 'stop' or UHB conf); chunks merged, "
                                              "extent unverified" % (seg, c.file.name)))
                elif rel + F.CHUNK_HDR_SIZE + F.pad4(c.length) > max(ext, F.FILEHDR_AREA):
                    col.above_extent.append((c, seg, rel, ext))
                    continue
            col.chunks.append(c)
            if c.ctype != F.CHUNK_RECS:
                continue
            blocks, probs = parse_recs(c.payload)
            for p in probs:
                col.anomalies.append(("recs", "%s@%d: %s" % (c.file.name, c.off, p)))
            for b in blocks:
                ring = b["ring"]
                if not b["resend"] and b["lost"]:
                    first = struct.unpack_from('<I', b["recs"][0], 0)[0] if b["recs"] else None
                    col.block_lost.append((ring, first, b["lost"], (c.file.name, c.off)))
                for raw in b["recs"]:
                    seq = struct.unpack_from('<I', raw, 0)[0]
                    if seq == F.SEQ_WRITING:
                        col.dropped_writing += 1
                        continue
                    have = col.rec_src[ring].get(seq)
                    if have is None:
                        rec = norm_record(ring, raw)
                        rec["_src"] = (c.file.name, c.off, phase)
                        rec["_resend"] = b["resend"]
                        col.records[ring][seq] = rec
                        col.rec_src[ring][seq] = raw
                        if phase == "raw" and col.sources:
                            col.only_in_image.append((ring, seq))
                    elif have == raw:
                        col.dup_exact += 1
                    else:
                        col.conflicts.append((ring, seq, col.records[ring][seq]["_src"], have,
                                              (c.file.name, c.off, phase), raw))


def _raw_rule(col):
    """10.2 (r3 IF5 fix 3; r4 A4-3; r5 TE7): evidence in the copied files of
    this run that makes the raw image the primary path."""
    reasons = []
    for (tick, text, c) in col.events:
        if c.file.kind != "file":
            continue
        for (name, rx) in RAW_REQUIRED_EVENTS:
            if rx.match(text):
                reasons.append("EVENT '%s' (tick %s, %s@%d)" % (text, tick, c.file.name, c.off))
                break
    file_uhb = [u for u in col.uhb if u["_src"][0] != "RAW"]
    if any(u["write_errs"] > 0 for u in file_uhb):
        u = next(u for u in file_uhb if u["write_errs"] > 0)
        reasons.append("UHB write_errs = %d (tick %d)" % (u["write_errs"], u["stats_now_tick"]))
    if any(u["flags"] & (1 << 30) for u in file_uhb):
        u = next(u for u in file_uhb if u["flags"] & (1 << 30))
        reasons.append("UHB flags b30 (DURABLE flush with fsync error, tick %d)" % u["stats_now_tick"])
    for s in col.sources:
        if s.ignored:
            continue
        if any(c.ctype == F.CHUNK_RECS for c in s.good) and s.size != F.SEG_SIZE:
            reasons.append("file %s holds RECS chunks and is %d bytes, not %d" % (s.name, s.size, F.SEG_SIZE))
    # de-duplicate, keep order
    out = []
    for r in reasons:
        if r not in out:
            out.append(r)
    col.raw_required = out
