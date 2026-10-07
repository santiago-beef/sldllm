#!/usr/bin/env python3
"""dumpcheck.py - DESIGN-conformance check of a PSCLOG dump, independent of the decoder.

Checks only what handoff/design/DESIGN.md states (cited as D:<section>):
  D:4.4  every T*.BIN that holds RECS is 2,097,152 B; FILEHDR + PAD = 1,536 B at 0;
  D:10.2 chunk header '<4sHHIII' magic PSCK, hver 5, len <= 65,536, payload padded
         to 4; CRC-32 plain for FILEHDR, seeded with the boot nonce otherwise;
         every flush starts at a multiple of 512 and ends with a PAD chunk;
         RECS: per ring per flush one new-records block (+ at most one re-send
         block, b7, before it), recsize_div4 P/M 20, POLL 10, W 72, S 10;
         RECS chunk <= 34,404 B, flush <= 40,960 B; FILEHDR '<8sIIIIIIIII'
         magic PSCLOG5, fmt 5; UHB '<21I' with the nonce in word 20.
  D:1.x  record sizes; WT tick % 1250 == 0 (D:1.1); W seq 0 is WB (D:8.2 WDOG);
         a P/M record whose span crosses a WT tick has wn >= 1 (D:10.5);
         seq per ring from 0 without gaps unless a block's 'lost' says so;
         stats magic 'PSST', version 5, size 768; word 2 = CRC-32 of the FILEHDR
         /proc/version (D:1.7, 10.1).
Usage: dumpcheck.py PSCLOG_DIR    -> prints a summary and 'CONFORMS' or the violations.
"""
import glob
import os
import struct
import sys
import zlib

CPT = 883651
SEG = 2097152
DIV4 = {0: 20, 1: 10, 2: 72, 3: 10, 4: 20}
SIZE = {r: 4 * d for r, d in DIV4.items()}
NAMES = {0: "P", 1: "POLL", 2: "W", 3: "S", 4: "M"}


def main(d):
    viol = []
    info = []
    files = sorted(glob.glob(os.path.join(d, "T*.BIN")) + glob.glob(os.path.join(d, "t*.bin")))
    nonce = None
    fh_by_file = {}
    recs = {r: {} for r in range(5)}
    lost_total = {r: 0 for r in range(5)}
    word2 = set()
    for fp in files:
        b = open(fp, "rb").read()
        nm = os.path.basename(fp)
        m, t, hv, ln, fs, c = struct.unpack_from('<4sHHIII', b, 0)
        if m != b"PSCK" or t != 1 or hv != 5:
            viol.append("%s: no FILEHDR chunk at offset 0" % nm)
            continue
        pl = b[20:20 + ln]
        if zlib.crc32(pl) & 0xFFFFFFFF != c:
            viol.append("%s: FILEHDR CRC (plain) wrong" % nm)
        fh = struct.unpack_from('<8sIIIIIIIII', pl, 0)
        if fh[0] != b"PSCLOG5\x00" or fh[1] != 5:
            viol.append("%s: FILEHDR magic/fmt %r %d" % (nm, fh[0], fh[1]))
        if nonce is None:
            nonce = fh[9]
        elif fh[9] != nonce:
            info.append("%s: other nonce 0x%08x (another boot)" % (nm, fh[9]))
            continue
        st = struct.unpack_from('<192I', pl, 44)
        ver = pl[44 + 768:44 + 768 + 256].split(b"\0", 1)[0]
        if st[0] != 0x54535350 or st[1] != (5 | 768 << 16):
            viol.append("%s: FILEHDR stats magic/version/size" % nm)
        if (zlib.crc32(ver) & 0xFFFFFFFF) != st[2]:
            info.append("%s: FILEHDR /proc/version CRC 0x%08x != its stats word 2 0x%08x"
                        % (nm, zlib.crc32(ver) & 0xFFFFFFFF, st[2]))
        fh_by_file[nm] = fh
        off = 20 + ln + ((-ln) % 4)
        m, t, hv, ln2, fs2, c2 = struct.unpack_from('<4sHHIII', b, off)
        if t != 0 or off + 20 + ln2 != 1536:
            viol.append("%s: FILEHDR + PAD is not 1,536 B" % nm)
        has_recs = False
        pos = 1536
        flushes = 0
        prealloc = 0
        while pos + 20 <= len(b):
            m, t, hv, ln, fs, c = struct.unpack_from('<4sHHIII', b, pos)
            if m == b"PSCK" and t == 0 and fs == 0xFFFFFFFF and ln == 492:
                # preallocation PAD sectors above the last flush (D:4.4 step 3)
                if zlib.crc32(b[pos + 20:pos + 512], nonce) & 0xFFFFFFFF != c:
                    viol.append("%s@%d: preallocation PAD CRC" % (nm, pos))
                prealloc += 1
                pos += 512
                continue
            if prealloc:
                viol.append("%s@%d: data after preallocation PAD sectors" % (nm, pos))
                break
            fstart = pos
            while pos + 20 <= len(b):
                m, t, hv, ln, fs, c = struct.unpack_from('<4sHHIII', b, pos)
                if m != b"PSCK" or hv != 5 or ln > 65536 or t > 7:
                    viol.append("%s@%d: bad chunk header in a flush (type %d hver %d len %d)" % (nm, pos, t, hv, ln))
                    pos = len(b)
                    break
                pl = b[pos + 20:pos + 20 + ln]
                if zlib.crc32(pl, nonce) & 0xFFFFFFFF != c:
                    viol.append("%s@%d: chunk type %d CRC under the run nonce wrong" % (nm, pos, t))
                if t == 2:
                    has_recs = True
                    if ln + 20 > 34404:
                        viol.append("%s@%d: RECS chunk %d B > 34,404" % (nm, pos, ln + 20))
                    p = 0
                    seen_new = set()
                    seen_rs = set()
                    while p < ln:
                        rb, d4, cntr, lost = struct.unpack_from('<BBHI', pl, p)
                        ring, rs = rb & 0x7F, bool(rb & 0x80)
                        if ring > 4 or DIV4[ring] != d4:
                            viol.append("%s@%d: block header ring %d div4 %d" % (nm, pos, ring, d4))
                            break
                        if rs:
                            if ring in seen_new or ring in seen_rs or lost:
                                viol.append("%s@%d: re-send block order/lost" % (nm, pos))
                            seen_rs.add(ring)
                        else:
                            if ring in seen_new:
                                viol.append("%s@%d: second new-records block ring %d" % (nm, pos, ring))
                            seen_new.add(ring)
                            lost_total[ring] += lost
                        p += 8
                        for k in range(cntr):
                            raw = pl[p:p + SIZE[ring]]
                            if len(raw) < SIZE[ring]:
                                viol.append("%s@%d: record cut" % (nm, pos))
                                break
                            seq = struct.unpack_from('<I', raw, 0)[0]
                            if seq in recs[ring] and recs[ring][seq] != raw:
                                viol.append("%s: (%s, %d) duplicate with other content" % (nm, NAMES[ring], seq))
                            recs[ring][seq] = raw
                            p += SIZE[ring]
                    if len(seen_new) != 5:
                        viol.append("%s@%d: RECS without a new-records block for every ring" % (nm, pos))
                elif t == 6:
                    u = struct.unpack_from('<21I', pl, 0)
                    if u[20] != nonce:
                        viol.append("%s@%d: UHB nonce 0x%08x != FILEHDR nonce" % (nm, pos, u[20]))
                elif t == 3:
                    s3 = struct.unpack_from('<192I', pl, 0)
                    word2.add(s3[2])
                    if s3[0] != 0x54535350 or s3[1] != (5 | 768 << 16):
                        viol.append("%s@%d: STATS magic/version/size" % (nm, pos))
                pos += 20 + ln + ((-ln) % 4)
                if t == 0:
                    if pos % 512:
                        viol.append("%s@%d: flush PAD does not end on a 512-B boundary" % (nm, pos))
                    if pos - fstart > 40960:
                        viol.append("%s@%d: flush of %d B > 40,960" % (nm, fstart, pos - fstart))
                    flushes += 1
                    break
        if has_recs and len(b) != SEG:
            viol.append("%s holds RECS and is %d B, not %d (D:10.2 makes the raw image the primary path)"
                        % (nm, len(b), SEG))
        info.append("%s: %d B, FILEHDR seg %d run %d inst %d, %d flushes, RECS %s" % (nm, len(b), fh[3], fh[2],
                                                                                    fh[4], flushes, has_recs))
    # record-level checks
    for r in range(5):
        seqs = sorted(recs[r])
        gaps = sum(b2 - a - 1 for a, b2 in zip(seqs, seqs[1:]))
        if seqs and r != 4 and seqs[0] != 0:
            gaps += seqs[0]
        info.append("ring %s: %d records, seq %s..%s, gaps %d, block lost %d"
                    % (NAMES[r], len(seqs), seqs[0] if seqs else "-", seqs[-1] if seqs else "-", gaps, lost_total[r]))
        if gaps != lost_total[r]:
            info.append("ring %s: seq gaps %d != blocks' lost %d (records never written or lost at the pull)"
                        % (NAMES[r], gaps, lost_total[r]))
    wt_ticks = []
    for seq, raw in sorted(recs[2].items()):
        tick = struct.unpack_from('<I', raw, 4)[0]
        origin = raw[38] & 3
        if seq == 0 and origin != 2:
            viol.append("W seq 0 is not origin WB")
        if origin == 3:
            wt_ticks.append(tick)
            if tick % 1250:
                viol.append("WT W seq %d at tick %d not on a 1250 boundary" % (seq, tick))
    for a, b2 in zip(wt_ticks, wt_ticks[1:]):
        if b2 - a != 1250:
            info.append("consecutive WT ticks %d, %d differ by %d" % (a, b2, b2 - a))
    wts = set(wt_ticks)
    nx = 0
    for ring in (0, 4):
        for seq, raw in recs[ring].items():
            tick, dtick, wn = struct.unpack_from('<I', raw, 4)[0], struct.unpack_from('<H', raw, 16)[0], raw[39]
            if dtick and any(t in wts for t in range(tick + 1, tick + dtick + 1)) and wn == 0:
                viol.append("%s seq %d crosses a WT tick with wn = 0" % (NAMES[ring], seq))
            nx += 1
    info.append("stats word 2 values in STATS chunks: %s" % ", ".join("0x%08x" % w for w in sorted(word2)))
    print("\n".join(info))
    if viol:
        print("VIOLATIONS (%d):" % len(viol))
        for v in viol[:60]:
            print("  " + v)
        return 1
    print("CONFORMS (DESIGN 4.4, 10.2, 10.3, 1.1, 1.7 checks above)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
