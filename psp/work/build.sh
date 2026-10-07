#!/bin/bash
# Clean build of the PSP uClinux 0.22 kernel in /home/ubuntu/psp/work/linux.
#
# Reconstructed by Recon C on 2026-09-27 from the evidence listed in
# /home/ubuntu/psp/handoff/recon/build.md. Run on the host as the ubuntu
# user (it calls sudo docker itself).
#
# What it does
#   1. Refuses to run if the tree is not a git work tree.
#   2. "Clean" = remove every untracked and ignored file in the tree
#      (git clean -fdx). Tracked files, including .config, are untouched.
#   3. Runs the kernel build inside the i386 container:
#        make ARCH=mips CROSS_COMPILE=mipsel-linux-uclibc- \
#             HOSTCC=/usr/bin/gcc HOSTCXX=/usr/bin/g++ -j$JOBS
#      with PATH = staging_dir/bin : staging_dir/usr/bin : system dirs
#      (the target-triplet dir staging_dir/usr/mipsel-linux-uclibc/bin is
#      deliberately NOT on PATH: it holds unprefixed gcc/as/ld).
#   4. vmlinux.bin      = mipsel-linux-uclibc-objcopy -O binary vmlinux
#      vmlinux-0.22.bin = cat vmlinux.bin | gzip -9 -n   (no name, mtime 0)
#   5. Gives the tree back to uid/gid 1001 (the container runs as root).
#   6. Copies the images plus sha256 into work/out/<stamp>/.
#
# Safety: the whole of /home/ubuntu/psp is mounted READ-ONLY in the
# container; only /home/ubuntu/psp/work is writable. The original tree
# /home/ubuntu/psp/build/linux therefore cannot be written by the build.
# NOTE: .config (as found) has
#   CONFIG_INITRAMFS_SOURCE="/work/build/linux/psp-initramfs.cpio"
# i.e. the initramfs is READ from the original tree, not from the copy.
# See build.md, "Initramfs path hazard".
#
# Environment knobs
#   JOBS=N                 make -j (default: nproc)
#   V=1                    verbose kbuild (full command lines in the log)
#   REPRODUCE_BASELINE=1   reuse the 2026-09-22 build identity (version #3,
#                          timestamp, user root, host 4a47ad9fa7f6) so the
#                          result can be compared byte for byte with the
#                          image found in build/linux. Do NOT use for images
#                          meant for the device: those should carry their
#                          own timestamp so /proc/version identifies them.
#   KBUILD_BUILD_VERSION, KBUILD_BUILD_TIMESTAMP   passed through if set.
#   BUILD_HOSTNAME         container hostname (default psp-work-build).
set -u
set -o pipefail

PSP=/home/ubuntu/psp
WORK=$PSP/work
TREE=$WORK/linux
LOGDIR=$WORK/logs
IMAGE=psp-build:bullseye
JOBS=${JOBS:-$(nproc)}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$LOGDIR/build-$STAMP.log
OUT=$WORK/out/$STAMP

mkdir -p "$LOGDIR"

die() { echo "build.sh: $*" | tee -a "$LOG" >&2; exit 1; }

[ "$(id -u)" = 1001 ] || die "run as the ubuntu user (uid 1001), not $(id -un)"
git -C "$TREE" rev-parse --git-dir >/dev/null 2>&1 || die "$TREE is not a git work tree"

HOSTNAME_IN=${BUILD_HOSTNAME:-psp-work-build}
KBV=${KBUILD_BUILD_VERSION:-}
KBT=${KBUILD_BUILD_TIMESTAMP:-}
if [ "${REPRODUCE_BASELINE:-0}" = 1 ]; then
    HOSTNAME_IN=4a47ad9fa7f6
    KBV=3
    KBT="Tue Sep 22 19:23:48 UTC 2026"
fi

{
    echo "=== build.sh started $(date -u '+%F %T UTC')"
    echo "tree:        $TREE"
    echo "git HEAD:    $(git -C "$TREE" rev-parse HEAD) ($(git -C "$TREE" log -1 --format=%s))"
    echo "git status (before clean, tracked changes only):"
    git -C "$TREE" status --porcelain --untracked-files=no | sed 's/^/    /'
    echo "image:       $IMAGE ($(sudo docker image inspect -f '{{.Id}}' $IMAGE 2>/dev/null))"
    echo "jobs:        $JOBS"
    echo "hostname:    $HOSTNAME_IN"
    echo "KBUILD_BUILD_VERSION='${KBV}' KBUILD_BUILD_TIMESTAMP='${KBT}' REPRODUCE_BASELINE='${REPRODUCE_BASELINE:-0}'"
} > "$LOG"

# ---- clean: remove all untracked + ignored files (build outputs) ----
echo "=== clean: git clean -fdxq" >> "$LOG"
git -C "$TREE" clean -fdxq >> "$LOG" 2>&1 \
    || die "git clean failed (root-owned leftovers? run: sudo chown -R 1001:1001 $TREE)"
LEFT=$(git -C "$TREE" status --porcelain --ignored --untracked-files=all | grep -c '^[?!]')
echo "untracked/ignored files after clean: $LEFT" >> "$LOG"
[ "$LEFT" = 0 ] || die "tree not clean after git clean"

# ---- the build, inside the container ----
INNER=$(cat <<'EOS'
set -u
set -o pipefail
export PATH=/work/staging_dir/bin:/work/staging_dir/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export KCONFIG_NOSILENTUPDATE=1   # fail instead of silently rewriting .config
[ -n "$KBV" ] && export KBUILD_BUILD_VERSION="$KBV"
[ -n "$KBT" ] && export KBUILD_BUILD_TIMESTAMP="$KBT"
cd /work/work/linux || exit 90
echo "--- container: $(uname -m) $(cat /etc/debian_version) user=$(whoami) host=$(hostname)"
echo "--- make: $(make --version | head -1); gzip: $(gzip --version | head -1)"
echo "--- host gcc: $(/usr/bin/gcc --version | head -1)"
echo "--- cross gcc: $(command -v mipsel-linux-uclibc-gcc) $(mipsel-linux-uclibc-gcc -dumpversion)"
echo "--- cross ld:  $(command -v mipsel-linux-uclibc-ld)"
echo "--- PATH=$PATH"
T0=$(date +%s)
set -x
make ARCH=mips CROSS_COMPILE=mipsel-linux-uclibc- \
     HOSTCC=/usr/bin/gcc HOSTCXX=/usr/bin/g++ \
     ${V:+V=$V} -j"$JOBS"
rc=$?
{ set +x; } 2>/dev/null
echo "MAKE_EXIT:$rc"
if [ $rc = 0 ]; then
    set -x
    mipsel-linux-uclibc-objcopy -O binary vmlinux vmlinux.bin && \
    cat vmlinux.bin | gzip -9 -n > vmlinux-0.22.bin
    rc=$?
    { set +x; } 2>/dev/null
fi
T1=$(date +%s)
echo "BUILD_EXIT:$rc"
echo "CONTAINER_WALL_SECONDS:$((T1-T0))"
chown -R 1001:1001 /work/work/linux
exit $rc
EOS
)

W0=$(date +%s)
sudo docker run --rm --platform linux/386 \
    --hostname "$HOSTNAME_IN" \
    -v "$PSP:/work:ro" \
    -v "$WORK:/work/work" \
    -w /work/work/linux \
    -e KBV="$KBV" -e KBT="$KBT" -e JOBS="$JOBS" -e V="${V:-}" \
    "$IMAGE" bash -c "$INNER" >> "$LOG" 2>&1
RC=$?
W1=$(date +%s)
echo "=== docker exit $RC, wall clock $((W1-W0)) s" >> "$LOG"

if [ $RC = 0 ]; then
    mkdir -p "$OUT"
    cp -p "$TREE/vmlinux" "$TREE/vmlinux.bin" "$TREE/vmlinux-0.22.bin" "$TREE/System.map" "$OUT/"
    (cd "$OUT" && sha256sum vmlinux vmlinux.bin vmlinux-0.22.bin System.map > SHA256SUMS)
    strings -a "$OUT/vmlinux.bin" | grep -m1 '^Linux version' > "$OUT/banner.txt"
    git -C "$TREE" rev-parse HEAD > "$OUT/git-head.txt"
    git -C "$TREE" status --porcelain --untracked-files=no > "$OUT/git-status.txt"
    { echo "=== outputs in $OUT"; cat "$OUT/SHA256SUMS"; ls -l "$OUT"; cat "$OUT/banner.txt"; } >> "$LOG"
fi
echo "=== build.sh finished $(date -u '+%F %T UTC') rc=$RC" >> "$LOG"
echo "log: $LOG"
[ $RC = 0 ] && echo "out: $OUT"
exit $RC
