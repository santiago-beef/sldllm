#!/bin/bash
# Stage 3 DECODER test: decode every dump under DUMPS with the analyst's decoder and
# the RELEASE build's BUILD directory; one log per case, one output dir per case.
# usage: run_decode.sh DUMPS OUTROOT LOGPREFIX [extra pscdec args...]
set -u
DUMPS=$1; OUT=$2; LP=$3; shift 3
DEC=/home/ubuntu/psp/work/decoder
BUILD=/home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD
mkdir -p "$OUT"
for d in "$DUMPS"/*/; do
  c=$(basename "$d")
  log=${LP}-${c}.log
  in="$d/PSCLOG"; [ -d "$in" ] || in="$d"
  args=(-o "$OUT/$c" --build "$BUILD")
  [ -f "$d/times.txt" ] && args+=(--times "$d/times.txt")
  {
    echo "# $(date -u +%FT%TZ) case $c"
    echo "# input sha256 before:"; (cd "$in" && sha256sum * | sha256sum)
    echo "\$ cd $DEC && python3 pscdec.py ${args[*]} $* $in"
    (cd $DEC && python3 pscdec.py "${args[@]}" "$@" "$in"); echo "rc=$?"
    echo "# input sha256 after:"; (cd "$in" && sha256sum * | sha256sum)
    echo "# REPORT classification lines:"
    R="$OUT/$c/REPORT.md"; [ -f "$R" ] || R="$OUT/$c/REPORT-NOT-FINAL.md"
    sed -n '/^## Classification/,/^### H10 conclusion/p' "$R"
    echo "# build consistency:"; sed -n '/^## Build consistency/,/^## `nwords`/p' "$R"
    echo "# nw7or8:"; sed -n '/^## `nwords` 7 or 8/,/^## Hazard/p' "$R"
    echo "# parsing:"; sed -n '/^## Parsing/,/^## What the data/p' "$R"
  } > "$log" 2>&1
  echo "$c: $(grep -m1 -E '^(CLASSIFIED|UNCLASSIFIED|NO DEATH|RAW IMAGE|REFUSED)' "$log") $(grep -m1 '^rc=' "$log")"
done
