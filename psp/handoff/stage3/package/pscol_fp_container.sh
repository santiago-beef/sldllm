# Runs inside psp-build:bullseye. Toolchain dirs first (as cbuild.sh:14), host /usr/bin:/bin after them for the shell utilities.
export PATH=/work/staging_dir/bin:/work/staging_dir/usr/bin:/work/staging_dir/usr/mipsel-linux-uclibc/bin:/usr/bin:/bin
cd /s/fp || exit 1
echo "== container: $(uname -m); $(mipsel-linux-uclibc-objdump --version | head -1); flthdr = $(command -v mipsel-linux-uclibc-flthdr)"
echo "== mipsel-linux-uclibc-flthdr pscol.extracted   (scratch copy of usr/bin/pscol from the packaged image; print only, no option)"
mipsel-linux-uclibc-flthdr pscol.extracted; echo "flthdr rc=$?"
DS=$(mipsel-linux-uclibc-flthdr pscol.extracted | awk '/Data Start/{print $3}')
echo "== disassemble the bFLT text segment itself: file bytes 0x40 .. Data Start ($DS), MIPS32 little-endian"
mipsel-linux-uclibc-objdump -D -b binary -m mips:isa32 -EL --start-address=0x40 --stop-address=$DS pscol.extracted > bflt-text.dis; echo "objdump rc=$?"
echo "== the delivered ELF work/pscol/pscol.gdb (read only): objdump -d as cbuild.sh:30, and its section table"
mipsel-linux-uclibc-objdump -d /work/work/pscol/pscol.gdb > gdb.dis; echo "objdump rc=$?"
mipsel-linux-uclibc-objdump -h /work/work/pscol/pscol.gdb
mipsel-linux-uclibc-objcopy -O binary --only-section=.text /work/work/pscol/pscol.gdb gdb-text.bin; echo "objcopy .text rc=$?"
