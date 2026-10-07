#!/usr/bin/env python3
"""make_synth.py - build two synthetic deploy folders for the pspboot size
limit test (R20). Each is a copy of the release deploy folder's EBOOT.PBP,
kmodlib.prx and pspboot.conf (byte-identical, checked) with a synthetic
vmlinux-0.22.bin: the release vmlinux.bin followed by a deterministic
non-zero pattern, to exactly 4,194,304 B ("exact") and to 4,259,840 B
("over", 64 KiB past pspboot's 0x400000 gzread buffer). gzip -9 -n style
(mtime 0, no name), as build.sh makes the real image. Nothing in the deploy
folder is written."""
import gzip, hashlib, os, random, shutil, sys

DEPLOY = '/home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE'
REL_BIN = '/home/ubuntu/psp/work/out/20261006T052947Z/vmlinux.bin'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/psp/handoff/stage3/r20/work/synth'
LIMIT = 0x400000

rnd = random.Random(20)
block = bytes(rnd.randrange(1, 256) for _ in range(4096))
base = open(REL_BIN, 'rb').read()
for name, size in (('exact', LIMIT), ('over', LIMIT + 65536)):
    d = os.path.join(OUT, name, 'SYNTHETIC-NOT-FOR-THE-STICK')
    os.makedirs(d, exist_ok=True)
    open(os.path.join(OUT, name, 'README'), 'w').write('Synthetic R20 test input (fake kernel of %d B). NEVER copy to a Memory Stick.\n' % size)
    for f in ('EBOOT.PBP', 'kmodlib.prx', 'pspboot.conf'):
        shutil.copyfile(os.path.join(DEPLOY, f), os.path.join(d, f))
        assert open(os.path.join(DEPLOY, f), 'rb').read() == open(os.path.join(d, f), 'rb').read()
    pad = size - len(base)
    img = base + (block * (pad // 4096 + 1))[:pad]
    assert len(img) == size
    open(os.path.join(OUT, name, 'vmlinux.bin'), 'wb').write(img)
    with open(os.path.join(d, 'vmlinux-0.22.bin'), 'wb') as fh:
        fh.write(gzip.compress(img, compresslevel=9, mtime=0))
    gz = open(os.path.join(d, 'vmlinux-0.22.bin'), 'rb').read()
    print('%-6s uncompressed %9d B sha256 %s  gz %8d B' % (name, size, hashlib.sha256(img).hexdigest()[:16], len(gz)))
