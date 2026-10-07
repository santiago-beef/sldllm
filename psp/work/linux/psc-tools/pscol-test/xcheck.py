#!/usr/bin/env python3
"""Cross-check: parse the simulated stick files with the analyst's decoder
parse layer (decoder/pscdec_parse.py) and compare with the simulation's truth.
Usage: xcheck.py DIR"""
import glob, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'decoder'))
import pscdec_parse as P
d = sys.argv[1]
truth = {}
for line in open(os.path.join(d, 'truth.txt')):
    f = line.split()
    if f[0] == 'nonce':
        nonce = int(f[1])
    else:
        truth[int(f[1])] = (int(f[3]), int(f[5]))
col = P.load(sorted(glob.glob(os.path.join(d, 'T*.BIN'))))
ok = True
if col.refused:
    print('  decoder refused:', col.refused); sys.exit(1)
print('  decoder: run %d nonce 0x%08x (sim nonce 0x%08x) %s' % (col.run, col.nonce, nonce, 'OK' if col.nonce == nonce else 'MISMATCH'))
ok &= col.nonce == nonce
for r in range(5):
    recs = col.records[r]
    head, dn = truth[r]
    miss = [s for s in range(dn) if s not in recs]
    print('  ring %-4s decoded %6d records, max seq %6s; sim head %6d durable_next %6d; missing below durable_next: %d'
          % (['P', 'POLL', 'W', 'S', 'M'][r], len(recs), max(recs) if recs else '-', head, dn, len(miss)))
    ok &= not miss
print('  conflicts %d, exact duplicates removed %d, bad chunks %d, other-boot %d, above extent %d, block_lost %d'
      % (len(col.conflicts), col.dup_exact, len(col.bad), len(col.other_boot), len(col.above_extent), len(col.block_lost)))
ok &= not col.conflicts and not col.above_extent
print('  UHB %d, STATS %d, EVENT lines %d, KMSG %d, PROCS %d' % (len(col.uhb), len(col.stats), len(col.events), len(col.kmsg), len(col.procs)))
for a in col.anomalies[:6]:
    print('  anomaly:', a)
print('  raw image required:', col.raw_required if col.raw_required else 'no')
print('  XCHECK', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
