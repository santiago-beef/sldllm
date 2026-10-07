"""oracle.py - Stage 3 TRUNCATION: ground truth for a dump, independent of the decoder.

Written from DESIGN.md 10.2 / 10.3 (chunk header '<4sHHIII', block header
'<BBHI', FILEHDR '<8sIIIIIIIII', record sizes P/M 80, POLL 40, W 288, S 40,
CRC-32 seeded with the boot nonce for every type except FILEHDR). It does NOT
import any decoder module.

A file is walked strictly in writer order:
  * with a region ledger (regions.tsv from gen_dumps, the writer's own
    write() calls): every FILEHDR / FLUSH / STEP region is walked chunk by
    chunk from its start (a STEP region is PAD sectors);
  * without one (synth.py files): from offset 0, chunk after chunk, then
    512-byte PAD sectors, using the synth truth ledger when present.
Every chunk's CRC is verified; a chunk that does not verify is an error of
the generator, not a truncation case, and makes the dump unusable.

Byte positions are absolute file offsets:
  off            chunk header start
  pay0           payload start (off + 20)
  pend           payload end (pay0 + len)      -> the decoder accepts the
                 chunk iff the file holds pend bytes (10.2 "the bytes exist")
  end            padded end (pay0 + pad4(len))
Records inside a RECS chunk carry [start, end) absolute.
"""

import struct
import zlib

HDR = struct.Struct('<4sHHIII')
BLK = struct.Struct('<BBHI')
FH = struct.Struct('<8sIIIIIIIII')
MAGIC = b'PSCK'
HVER = 5
NAMES = {0: 'PAD', 1: 'FILEHDR', 2: 'RECS', 3: 'STATS', 4: 'KMSG', 5: 'PROCS', 6: 'UHB', 7: 'EVENT'}
RING = {0: 'P', 1: 'POLL', 2: 'W', 3: 'S', 4: 'M'}
RECSIZE = {0: 80, 1: 40, 2: 288, 3: 40, 4: 80}
SEG = 2097152
FILEHDR_AREA = 1536
SECTOR = 512


def pad4(n):
    return (n + 3) & ~3


def crc(ctype, payload, nonce):
    return zlib.crc32(payload, 0 if ctype == 1 else nonce) & 0xFFFFFFFF


class OracleError(Exception):
    pass


def chunk_at(data, off, nonce):
    if off + 20 > len(data):
        raise OracleError("chunk header beyond file at %d" % off)
    magic, ctype, hver, ln, fseq, c = HDR.unpack_from(data, off)
    if magic != MAGIC or hver != HVER or ctype not in NAMES:
        raise OracleError("no chunk at %d (magic %r type %d hver %d)" % (off, magic, ctype, hver))
    pay0 = off + 20
    pend = pay0 + ln
    if pend > len(data):
        raise OracleError("chunk at %d runs past the file" % off)
    payload = bytes(data[pay0:pend])
    if nonce is not None and crc(ctype, payload, nonce) != c:
        raise OracleError("CRC mismatch for %s at %d" % (NAMES[ctype], off))
    return dict(off=off, pay0=pay0, pend=pend, end=pay0 + pad4(ln), type=ctype, name=NAMES[ctype],
                len=ln, fseq=fseq, payload=payload)


def records_of(ch):
    """Records of a RECS chunk with absolute byte ranges."""
    out = []
    p, end = ch['pay0'], ch['pend']
    pl = ch['payload']
    while p < end:
        if p + 8 > end:
            raise OracleError("block header cut inside chunk at %d" % ch['off'])
        rb, div4, count, lost = BLK.unpack_from(pl, p - ch['pay0'])
        ring, resend = rb & 0x7F, bool(rb & 0x80)
        if ring not in RECSIZE or RECSIZE[ring] != div4 * 4:
            raise OracleError("bad block header in chunk at %d" % ch['off'])
        p += 8
        for _k in range(count):
            sz = RECSIZE[ring]
            raw = pl[p - ch['pay0']:p - ch['pay0'] + sz]
            if len(raw) != sz:
                raise OracleError("record cut inside chunk at %d" % ch['off'])
            seq = struct.unpack_from('<I', raw, 0)[0]
            out.append(dict(ring=ring, seq=seq, start=p, end=p + sz, raw=raw, resend=resend, chunk=ch['off']))
            p += sz
    return out


def walk_span(data, a, b, nonce, must_end_pad=True):
    """Chunks laid back to back from a to b (a flush or the FILEHDR area)."""
    out = []
    off = a
    while off < b:
        ch = chunk_at(data, off, nonce)
        out.append(ch)
        off = ch['end']
    if off != b:
        raise OracleError("span %d..%d ends at %d" % (a, b, off))
    if must_end_pad and out and out[-1]['type'] != 0:
        raise OracleError("span %d..%d does not end with PAD" % (a, b))
    return out


def filehdr_of(ch):
    vals = FH.unpack_from(ch['payload'], 0)
    keys = ['magic', 'fmt', 'run', 'seg', 'inst', 'writer_pid', 'sup_pid', 'now_tick', 'now_jiffies', 'nonce']
    return dict(zip(keys, vals))


class FileTruth(object):
    """Ground truth of one file: every chunk the writer left, in file order,
    the record ledger, and the pre-image used by the OVERLAY model."""

    def __init__(self, name, data, regions=None, nonce=None):
        self.name = name
        self.data = bytes(data)
        self.size = len(data)
        fh = chunk_at(self.data, 0, None)
        if fh['type'] != 1:
            raise OracleError("%s: no FILEHDR at 0" % name)
        self.fh = filehdr_of(fh)
        self.nonce = self.fh['nonce'] if nonce is None else nonce
        if crc(1, fh['payload'], 0) != HDR.unpack_from(self.data, 0)[5]:
            raise OracleError("%s: FILEHDR CRC" % name)
        chunks = {}
        self.flushes = []           # (a, b) of every tick flush, writer order
        if regions:
            for (kind, a, b) in regions:
                if b > self.size:
                    raise OracleError("%s: region %s %d..%d beyond file size %d" % (name, kind, a, b, self.size))
                if kind == 'STEP':
                    continue
                for ch in walk_span(self.data, a, b, self.nonce):
                    chunks[ch['off']] = ch
                if kind == 'FLUSH':
                    self.flushes.append((a, b))
            # sectors not covered by FILEHDR/FLUSH regions must be PAD sectors
            covered = set()
            for off, ch in chunks.items():
                for s in range(off // SECTOR, (ch['end'] + SECTOR - 1) // SECTOR):
                    covered.add(s)
            for s in range(self.size // SECTOR):
                if s in covered:
                    continue
                ch = chunk_at(self.data, s * SECTOR, self.nonce)
                if ch['type'] != 0 or ch['end'] != (s + 1) * SECTOR:
                    raise OracleError("%s: sector %d is not a PAD sector" % (name, s))
                chunks[ch['off']] = ch
        else:
            off = 0
            while off < self.size:
                ch = chunk_at(self.data, off, self.nonce)
                chunks[ch['off']] = ch
                off = ch['end']
        self.chunks = [chunks[k] for k in sorted(chunks)]
        # contiguity: every byte of the file belongs to exactly one chunk
        pos = 0
        for ch in self.chunks:
            if ch['off'] != pos:
                raise OracleError("%s: bytes %d..%d belong to no chunk" % (name, pos, ch['off']))
            pos = ch['end']
        if pos != self.size:
            raise OracleError("%s: tail %d..%d belongs to no chunk" % (name, pos, self.size))
        self.records = []
        for ch in self.chunks:
            if ch['type'] == 2:
                ch['recs'] = records_of(ch)
                self.records.extend(ch['recs'])
        # written extent = end of the last non-PAD-sector chunk (tick flushes)
        last = 0
        for ch in self.chunks:
            if not (ch['type'] == 0 and ch['fseq'] == 0xFFFFFFFF):
                last = ch['end']
        self.written_end = last
        # the preallocation PAD sector (all sectors above the written extent)
        self.pad_sector = None
        for ch in self.chunks:
            if ch['type'] == 0 and ch['fseq'] == 0xFFFFFFFF and ch['len'] == 492:
                self.pad_sector = self.data[ch['off']:ch['end']]
                break

    def boundaries(self):
        """Every chunk and record boundary (offsets where a cut changes what
        is complete): chunk off, payload end, padded end; record start/end."""
        bs = set([0, self.size])
        for ch in self.chunks:
            bs.update((ch['off'], ch['pay0'], ch['pend'], ch['end']))
            for r in ch.get('recs', ()):
                bs.update((r['start'], r['end']))
        return sorted(bs)

    def preimage(self, start, end):
        """Bytes the stick held at [start, end) before the tick flushes were
        written: the preallocation PAD sectors (4.4 step 3) above the
        FILEHDR area, zeros inside it (a torn step 0 on a fresh cluster)."""
        if getattr(self, "_pre", None) is None:
            n = self.size
            if self.pad_sector is None or n <= FILEHDR_AREA:
                self._pre = bytes(n)
            else:
                reps = (n - FILEHDR_AREA + SECTOR - 1) // SECTOR
                self._pre = bytes(FILEHDR_AREA) + (self.pad_sector * reps)[:n - FILEHDR_AREA]
        return self._pre[start:end]


def ledger_for_cut(files, k, cut):
    """Expected content for a dump whose file index k is cut at `cut`
    (files before k complete, files after k absent or record-free).
    Returns (complete_chunks, cut_chunk) where complete_chunks lists
    (file_index, chunk) with pend <= cut for file k; cut_chunk is the chunk
    of file k containing the cut inside [off, pend), or None."""
    done = []
    cut_chunk = None
    for i, ft in enumerate(files):
        if i > k:
            break
        for ch in ft.chunks:
            if i < k or ch['pend'] <= cut:
                done.append((i, ch))
            elif ch['off'] < cut < ch['pend'] or (ch['off'] == cut and False):
                cut_chunk = ch
    return done, cut_chunk
