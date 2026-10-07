#!/bin/bash
# Stage 3 PACKAGE + INITRAMFS test: re-runs every check and rewrites the logs in
# handoff/stage3/logs/package-*.log. Read-only on the package, work/pscol, the
# original tree and pspboot-baseline. Needs sudo (cpio extraction as root so the
# device nodes are created; docker for flthdr/objdump in psp-build:bullseye).
#
#   bash run_all.sh [scratch-dir]     (default: a new mktemp -d)
set -u
P=/home/ubuntu/psp/handoff/stage3/package
L=/home/ubuntu/psp/handoff/stage3/logs
S=${1:-$(mktemp -d)}
mkdir -p "$S" "$L"
echo "scratch: $S"

# 0. original tree manifest (start)
( cd /home/ubuntu/psp/build/linux && date -u '+%F %T UTC' && sha256sum -c --quiet /home/ubuntu/psp/handoff/gates/baseline-tree.sha256; echo "EXIT=$?" ) > $L/package-manifest-start.log 2>&1

# 1. PACKAGE checks
python3 $P/check_package.py > $L/package-check.log 2>&1; echo "check_package rc=$?"

# 2. INITRAMFS: find and unpack the cpio inside the packaged image (own parser)
python3 $P/extract_initramfs.py $S/initramfs > $L/package-initramfs-extract.log 2>&1; echo "extract rc=$?"
cp $S/initramfs/newc-list.txt $P/initramfs-newc-list.txt

# 3. the cpio tool: list, extract as root, compare pscol
{
  echo "== $(date -u '+%F %T UTC') host $(cpio --version | head -1)"
  sha256sum $S/initramfs/initramfs.cpio
  echo "== cpio -itvn --quiet < initramfs.cpio"
  cpio -itvn --quiet < $S/initramfs/initramfs.cpio; echo "rc=$?"
  sudo rm -rf $S/initramfs/root; mkdir -p $S/initramfs/root
  echo "== sudo cpio -idmu --no-absolute-filenames --quiet"
  ( cd $S/initramfs/root && sudo cpio -idmu --no-absolute-filenames --quiet < $S/initramfs/initramfs.cpio; echo "rc=$?" )
  echo "== extracted tree: $(sudo find $S/initramfs/root | wc -l) paths incl. the root"
  ( cd $S/initramfs/root && ls -ln etc/rc.sysinit etc/inittab init sbin/init usr/bin/pscol usr/bin/pspmd usr/bin/psposk2 )
  stat -c '%A %a %U:%G %s %n' $S/initramfs/root/usr/bin/pscol
  file $S/initramfs/root/usr/bin/pscol
  cmp $S/initramfs/root/usr/bin/pscol /home/ubuntu/psp/work/pscol/pscol && echo "cmp work/pscol/pscol: IDENTICAL"
  cmp $S/initramfs/root/usr/bin/pscol $S/initramfs/files/usr_bin_pscol && echo "cmp own parse: IDENTICAL"
  sha256sum $S/initramfs/root/usr/bin/pscol /home/ubuntu/psp/work/pscol/pscol
  echo "== cross-check only: committed archive at 48dcc1b9"
  git -C /home/ubuntu/psp/work/linux show 48dcc1b9:psp-initramfs.cpio | cmp - $S/initramfs/initramfs.cpio && echo "embedded cpio == git show 48dcc1b9:psp-initramfs.cpio: IDENTICAL"
} > $L/package-initramfs-cpio.log 2>&1

# 4. entry-by-entry comparison with the baseline initramfs
python3 $P/compare_cpio.py $S/initramfs/initramfs.cpio > $L/package-initramfs-vs-baseline.log 2>&1

# 5. flthdr + FP count in the container on a scratch copy of the extracted pscol
mkdir -p $S/fp; cp $S/initramfs/root/usr/bin/pscol $S/fp/pscol.extracted; chmod 644 $S/fp/pscol.extracted
cp $P/pscol_fp_container.sh $S/fp/fp.sh
sudo docker run --rm --platform linux/386 -v /home/ubuntu/psp:/work:ro -v /home/ubuntu/psp/work:/work/work -v $S:/s \
    psp-build:bullseye bash /s/fp/fp.sh > $S/fp/container.out 2>&1
{
  echo "# $(date -u '+%F %T UTC') pscol extracted from the packaged image; scratch copy $(sha256sum $S/fp/pscol.extracted | cut -c1-64)"
  cat $S/fp/container.out
  echo "== host counts (regexes of work/pscol/cbuild.sh:31-33, plus other COP1 forms)"
  python3 - "$S/fp" <<'EOF'
import sys, collections
d = sys.argv[1]
b = open(d + '/pscol.extracted', 'rb').read(); g = open(d + '/gdb-text.bin', 'rb').read()
ds = int.from_bytes(b[12:16], 'big'); t = b[0x40:ds]
print('bFLT header: magic', b[:4], 'rev', int.from_bytes(b[4:8], 'big'), 'entry', hex(int.from_bytes(b[8:12], 'big')), 'data_start', hex(ds),
      'data_end', hex(int.from_bytes(b[16:20], 'big')), 'bss_end', hex(int.from_bytes(b[20:24], 'big')), 'stack', int.from_bytes(b[24:28], 'big'),
      'reloc_count', int.from_bytes(b[32:36], 'big'), 'flags', hex(int.from_bytes(b[36:40], 'big')), 'size', len(b),
      '= data_end + 4*relocs:', len(b) == int.from_bytes(b[16:20], 'big') + 4 * int.from_bytes(b[32:36], 'big'))
print('bFLT text 0x40..data_start (%d B) == .text of work/pscol/pscol.gdb (%d B): %s' % (len(t), len(g), t == g))
c = collections.Counter(hex(int.from_bytes(t[i:i + 4], 'little') >> 26) for i in range(0, len(t), 4)
                        if int.from_bytes(t[i:i + 4], 'little') >> 26 in (0x11, 0x13, 0x31, 0x35, 0x39, 0x3d))
print('raw opcode scan of %d text words: COP1/COP1X/LWC1/LDC1/SWC1/SDC1 = %d %s' % (len(t) // 4, sum(c.values()), dict(c)))
EOF
  for f in bflt-text.dis gdb.dis; do
    echo "-- $f: decoded lines $(grep -c '^ *[0-9a-f]\+:' $S/fp/$f)"
    echo "   FP_REGS_USED=$(grep -c '[$]f[0-9]' $S/fp/$f)  FP_MNEMONICS=$(grep -cE '\s(add|sub|mul|div|abs|neg|mov|sqrt)\.(s|d)\s|\s(lwc1|swc1|ldc1|sdc1|mtc1|mfc1|cfc1|ctc1)\s|\scvt\.' $S/fp/$f)  FP_MNEMONICS_DESIGN_GREP=$(grep -cE 'lwc1|swc1|ldc1|sdc1|mtc1|mfc1|cfc1|ctc1|cvt\.' $S/fp/$f)  COP1_OTHER=$(grep -cE '\s(c\.[a-z]+\.(s|d)|bc1[ft]l?|lwxc1|swxc1|madd\.(s|d)|msub\.(s|d)|trunc\.|round\.|floor\.|ceil\.)\s' $S/fp/$f)"
  done
} > $L/package-pscol-flthdr-fp.log 2>&1

# 6. rc.sysinit / inittab
R=$S/initramfs/root
{
  echo "# $(date -u '+%F %T UTC') etc/rc.sysinit and etc/inittab from the initramfs inside the PACKAGED vmlinux-0.22.bin"
  sha256sum $R/etc/rc.sysinit $R/etc/inittab
  ls -l $R/init $R/sbin/init
  echo "## cat -n etc/inittab"; cat -n $R/etc/inittab
  echo "## cat -n etc/rc.sysinit"; cat -n $R/etc/rc.sysinit
  echo "## operator-wait candidates (read getty login askfirst wait sleep):"; grep -n -E '\b(read|getty|login|askfirst|wait|sleep)\b' $R/etc/rc.sysinit || echo "(none)"
  echo "## background starts: $(grep -n '&$' $R/etc/rc.sysinit | tr '\n' ' ')"
  echo "## set -e / exit: $(grep -n -E '^\s*(set -e|exit)' $R/etc/rc.sysinit || echo none)"
  echo "## diff baseline extract/root2/etc/rc.sysinit -> packaged"; diff /home/ubuntu/psp/extract/root2/etc/rc.sysinit $R/etc/rc.sysinit
  echo "## inittab vs baseline: $(diff /home/ubuntu/psp/extract/root2/etc/inittab $R/etc/inittab >/dev/null && echo identical)"
  T=$(mktemp -d); cp /home/ubuntu/psp/extract/root2/etc/rc.sysinit $T/rc.sysinit
  ( cd $T && patch -s rc.sysinit < /home/ubuntu/psp/work/pscol/rc.sysinit.patch && cmp rc.sysinit $R/etc/rc.sysinit && echo "baseline + work/pscol/rc.sysinit.patch == packaged rc.sysinit: IDENTICAL" ); rm -rf $T
} > $L/package-initramfs-rcsysinit.log 2>&1

# 7. original tree manifest (end)
( cd /home/ubuntu/psp/build/linux && date -u '+%F %T UTC' && sha256sum -c --quiet /home/ubuntu/psp/handoff/gates/baseline-tree.sha256; echo "EXIT=$?" ) > $L/package-manifest-end.log 2>&1
grep -h -E '^EXIT|^(all hard|FAIL)' $L/package-manifest-start.log $L/package-check.log $L/package-manifest-end.log
