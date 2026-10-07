#!/bin/bash
# Runs the pspboot emulation (pspboot_emu.py) for the four R20 scenarios in
# parallel. Results: handoff/stage3/logs/r20-emu-<scenario>.{json,log}.
# Read-only on the deploy folder, pspboot-baseline and the build outputs.
set -u
R=/home/ubuntu/psp/handoff/stage3/r20
L=/home/ubuntu/psp/handoff/stage3/logs
E="python3 $R/pspboot_emu.py"
python3 $R/make_synth.py $R/work/synth > $L/r20-make-synth.log 2>&1 || { echo "make_synth failed"; exit 1; }
run() { local name=$1; shift; ( /usr/bin/time -v $E "$@" --json $L/r20-emu-$name.json > $L/r20-emu-$name.log 2>&1; echo "rc=$?" >> $L/r20-emu-$name.log ) & }
run release  /home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE --expect-bin /home/ubuntu/psp/work/out/20261006T052947Z/vmlinux.bin
run baseline /home/ubuntu/psp/pspboot-baseline --gamedir uClinux --expect-bin /home/ubuntu/psp/extract/k
run exact    $R/work/synth/exact/SYNTHETIC-NOT-FOR-THE-STICK --gamedir uClinux_TRACE --expect-bin $R/work/synth/exact/vmlinux.bin
run over     $R/work/synth/over/SYNTHETIC-NOT-FOR-THE-STICK --gamedir uClinux_TRACE --expect-bin $R/work/synth/over/vmlinux.bin --truncate-at 4194304
wait
