#!/bin/bash
# state_check.sh - record the state of every frozen or read-only input of the
# TRUNCATION test (same commands as logs/trunc-prestate.log, plus the original
# tree manifest).  Usage: state_check.sh > logs/trunc-poststate.log
cd /home/ubuntu/psp || exit 2
date -u +%Y-%m-%dT%H:%M:%SZ
echo "== release image"
sha256sum work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin 2>&1
find work/deploy/uClinux_TRACE -type f | sort | xargs sha256sum
echo "== work/linux"
git -C work/linux rev-parse HEAD
git -C work/linux status --porcelain | wc -l
git -C work/linux diff --stat 48dcc1b9..HEAD -- . ':!psc-tools' | tail -1
echo "== pscol"
sha256sum work/pscol/pscol work/pscol/pscol.c
echo "== decoder"
(cd work/decoder && find . -type f | sort | xargs sha256sum)
echo "== pscol/test"
(cd work/pscol/test && sha256sum *)
echo "== original tree manifest"
(cd build/linux && sha256sum -c --quiet /home/ubuntu/psp/handoff/gates/baseline-tree.sha256; echo "exit $?";
 echo "entries $(wc -l < /home/ubuntu/psp/handoff/gates/baseline-tree.sha256)"; echo "files_in_tree $(find . -type f | wc -l)")
