# Building PSP uClinux apps on the aarch64 Ubuntu box

The 2008 cross-toolchain is 32-bit **i386** Linux. Your build box is
**aarch64** (Ubuntu 24.04), so we run the toolchain inside a tiny **i386
Debian container** — qemu emulates i386 transparently, and the old
binaries run as "native" i386 there. They only need i386 glibc, which the
base image already has (no extra packages).

## 0. One-time: transfer the bundle from the Mac
On the **Mac** (adjust host if needed):

    scp "/Users/yago/Desktop/MFA YEAR 2/SLDLLM/PSP/uCLinux/psp-build-bundle.tar.gz" ubuntu@sldllm-node:~/

On the **Ubuntu box**:

    mkdir -p ~/psp && tar -xzf ~/psp-build-bundle.tar.gz -C ~/psp
    # ~/psp/staging_dir  = the cross-toolchain
    # ~/psp/hello_fb     = our app

## 1. One-time: install Docker + i386 emulation
    sudo apt-get update
    sudo apt-get install -y docker.io qemu-user-static binfmt-support
    sudo systemctl enable --now docker
    # (qemu-user-static registers the i386 binfmt handler automatically)

## 2. Enter the i386 build container
    cd ~/psp
    sudo docker run --rm -it --platform linux/386 \
        -v "$PWD:/work" -w /work \
        i386/debian:bullseye bash

## 3. Inside the container: compile
    export PATH=/work/staging_dir/bin:/work/staging_dir/usr/bin:$PATH
    mipsel-linux-uclibc-gcc --version      # sanity check the toolchain runs
    cd /work/hello_fb
    make
    mipsel-linux-uclibc-flthdr hello_fb    # should print a bFLT header

The output `hello_fb` is a bFLT flat binary. Copy it out of the container
dir (it's on the host at `~/psp/hello_fb/hello_fb`).

## 4. Run it on the PSP
Copy `hello_fb` onto the Memory Stick (e.g. `ms0:/hello_fb`). Boot uClinux,
then from the console:

    /hello_fb            # if ms0 is auto-mounted at /, else find the mount

If `/dev/fb0` is missing, create it once:

    mknod /dev/fb0 c 29 0

You should see an animated gradient fill the screen, then it exits.

## Notes
- If `make` errors because `ld` is not the elf2flt wrapper, run `make two-step`.
- If the flat binary loads but crashes, it's likely a PIC/relocation flag;
  we'll adjust CFLAGS/elf2flt options then.
- Later apps (framebuffer instrument, serial I/O) build the same way.
