#!/bin/bash
# Informational: run the analyst's decoder (work/decoder) over every dump with
# the packaged BUILD; outputs in build/dec/<scenario>/; one summary line each.
D=/home/ubuntu/psp/handoff/stage3/dumps
B=/home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD
O=/home/ubuntu/psp/handoff/stage3/ring/build/dec
mkdir -p $O
for s in "$@"; do
  ( rm -rf $O/$s; cd /home/ubuntu/psp/work/decoder && \
    timeout 1200 python3 pscdec.py -o $O/$s --build $B --times $D/$s/times.txt $D/$s/PSCLOG/ > $O/$s.stdout 2>&1; \
    echo "rc=$?" >> $O/$s.stdout ) &
done
wait
for s in "$@"; do
  c=$(grep -m1 "^\*\*Classification" $O/$s/REPORT.md 2>/dev/null || grep -m1 "Classification" $O/$s/REPORT-NOT-FINAL.md 2>/dev/null)
  t=$(grep -m1 "^- triple:" $O/$s/REPORT.md 2>/dev/null | sed 's/^- //')
  echo "$s | $(tail -1 $O/$s.stdout) | $c | $t"
done
echo
echo "Decoder P-point attribution of Nop straddles (REPORT.md hazard statistics, hits / harmful):"
for s in "$@"; do
  echo "$s | $(grep -m1 'Nop straddles of an in-flight thread command, per P-point' $O/$s/REPORT.md 2>/dev/null | sed 's/.*(hits \/ harmful): //') | inconsistent: $(grep -ci 'inconsistent' $O/$s/REPORT.md 2>/dev/null)"
done
