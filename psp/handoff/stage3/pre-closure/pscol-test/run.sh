#!/bin/bash
# Host unit tests for pscol: builds the collector core natively against the
# simulated kernel/vfat/stick (test/sim.c) and runs every test.
# Usage: test/run.sh [all|vectors|hud|nominal|burst|te10|if7b|if4|names|krn|resend] [seeds]
#        test/run.sh krn <banner.txt> <build_id>   (KRN against a packaged build, K9)
set -e
cd "$(dirname "$0")"
CFLAGS="-O2 -g -Wall -W -Wno-unused-parameter -std=gnu89 -DPSCOL_HOST -m32"
if ! echo 'int main(void){return 0;}' | gcc -m32 -x c - -o /tmp/pscol_m32probe 2>/dev/null; then
  CFLAGS="${CFLAGS/-m32/}"     # 64-bit host build if no multilib
fi
gcc $CFLAGS -o pscol_test ../pscol.c sim.c vectors.c -lm
./pscol_test "${1:-all}" "${2:-20}"
