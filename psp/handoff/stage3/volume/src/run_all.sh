#!/bin/bash
# Stage 3 VOLUME test: build the harness, run every scenario, check every stick,
# summarise. Small outputs go to ../results/<run>/, logs to
# /home/ubuntu/psp/handoff/stage3/logs/volume-*.log, large outputs (stick
# images, produced-record dumps) to $BIG (default: the session scratchpad).
#
# Usage: src/run_all.sh [BIGDIR]
set -euo pipefail
cd "$(dirname "$0")"
SRC=$(pwd)
VOL=$(cd .. && pwd)
RES=$VOL/results
LOGS=/home/ubuntu/psp/handoff/stage3/logs
BIG=${1:-/tmp/claude-1001/-home-ubuntu-psp/6146dc03-2451-42b8-b1df-134d36152e49/scratchpad/volume/runs}
mkdir -p "$RES" "$LOGS" "$BIG"

{
  echo "# build $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum /home/ubuntu/psp/work/pscol/pscol.c /home/ubuntu/psp/work/pscol/pscol.h \
            /home/ubuntu/psp/work/linux/include/linux/psc_format.h /home/ubuntu/psp/telem/telem.c \
            volsim.c check_stick.py design_budget.py font_from_telem.py Makefile run_all.sh summarize.py
  make clean && make
  echo "# design budget method self-check (must reproduce DESIGN 5.1 / 15.6)"
  python3 design_budget.py
} > "$LOGS/volume-build.log" 2>&1
tail -3 "$LOGS/volume-build.log"

# name | volsim arguments                    (all: 15 min of collection after a 30 s worker start)
SCEN=(
 "R1-nominal-20pps-52k|polls=20 speed=52 cl=32"
 "R2-stall10s-20pps-52k|polls=20 speed=52 cl=32 stall_at=420000 stall_ms=10000"
 "R3-wfail5s-20pps-52k|polls=20 speed=52 cl=32 out_at=600000 out_ms=5000"
 "R1-nominal-20pps-32k|polls=20 speed=32 cl=32"
 "R2-stall10s-20pps-32k|polls=20 speed=32 cl=32 stall_at=420000 stall_ms=10000"
 "R3-wfail5s-20pps-32k|polls=20 speed=32 cl=32 out_at=600000 out_ms=5000"
 "R1-nominal-20pps-300k|polls=20 speed=300 cl=32"
 "R2-stall10s-20pps-300k|polls=20 speed=300 cl=32 stall_at=420000 stall_ms=10000"
 "R3-wfail5s-20pps-300k|polls=20 speed=300 cl=32 out_at=600000 out_ms=5000"
 "V2b-stall10s-thread-held-20pps-52k|polls=20 speed=52 cl=32 stall_at=420000 stall_ms=10000 stall_np=1"
 "V3b-wfail5s-in-creation-20pps-52k|polls=20 speed=52 cl=32 out_at=450000 out_ms=5000"
 "V3c-one-flush-fails-20pps-52k|polls=20 speed=52 cl=32 fail1_at=300000"
 "V3d-write-returns-EIO-2s-20pps-52k|polls=20 speed=52 cl=32 wfail_at=300000 wfail_ms=2000"
 "V3e-wfail5s-during-startup-20pps-52k|polls=20 speed=52 cl=32 out_at=36000 out_ms=5000"
 "G0-gate-raw30k-20pps|polls=20 speed=30 cl=32"
 "B1-17.86pps-design-tick|polls=17.86 speed=4000 cl=32"
 "B2-17.86pps-52k|polls=17.86 speed=52 cl=32"
 "B3-17.86pps-52k-64Kcl|polls=17.86 speed=52 cl=64"
 "B4-20pps-52k-64Kcl|polls=20 speed=52 cl=64"
 "B5-20pps-design-tick|polls=20 speed=4000 cl=32"
 "L1-nominal-20pps-52k-30min|polls=20 speed=52 cl=32 dur=1800"
)
fail=0
for s in "${SCEN[@]}"; do
  name=${s%%|*}; args=${s#*|}
  out=$RES/$name; big=$BIG/$name
  rm -rf "$out" "$big"; mkdir -p "$out" "$big"
  log=$LOGS/volume-$name.log
  {
    echo "# $name: volsim name=$name $args"
    ../build/volsim name="$name" out="$out" big="$big" $args
    echo "# check"
    python3 check_stick.py "$big" "$out"
  } > "$log" 2>&1 || { echo "FAILED: $name (see $log)"; fail=1; }
  gzip -9 -f "$out/ticks.csv"
  head -1 "$log" | cut -c1-120; sed -n 2p "$log"; grep '^check ' "$log" || true
done
python3 summarize.py "$RES" > "$LOGS/volume-summary.log" 2>&1 || fail=1
cat "$LOGS/volume-summary.log" | tail -40
exit $fail
