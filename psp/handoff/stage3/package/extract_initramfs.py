#!/usr/bin/env python3
"""Stage 3 INITRAMFS test, step 1: find and unpack the initramfs embedded in the
PACKAGED kernel image (not the build tree).

Usage: python3 extract_initramfs.py <out-dir>
Reads  work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin only
(BUILD/System.map and BUILD/vmlinux of the same package are used afterwards, as
a cross-check of the offset, never to find it). Writes into <out-dir>:
  vmlinux.bin (gunzip of the image), initramfs.cpio (the embedded archive),
  newc-list.txt (own parse of every entry), files/<name> for usr/bin/pscol,
  etc/rc.sysinit, etc/inittab.
Standard library only.
"""
import gzip, hashlib, os, re, struct, sys, zlib

PKG = '/home/ubuntu/psp/work/deploy/uClinux_TRACE'
IMG = PKG + '/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin'
FROZEN = '4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8'
out = sys.argv[1]
os.makedirs(out + '/files', exist_ok=True)
sha = lambda b: hashlib.sha256(b).hexdigest()

gz = open(IMG, 'rb').read()
print(f'image   {IMG}\n        {len(gz)} B sha256 {sha(gz)}  frozen match: {sha(gz) == FROZEN}')
assert sha(gz) == FROZEN, 'not the frozen release image'

# 1. The image file is gzip (pspboot inflates it). Unwrap the outer layer.
d = zlib.decompressobj(16 + zlib.MAX_WBITS)
vb = d.decompress(gz) + d.flush()
print(f'outer gzip: magic {gz[:3].hex()}, eof {d.eof}, trailing {len(d.unused_data)} B -> vmlinux.bin {len(vb)} B sha256 {sha(vb)}')
open(out + '/vmlinux.bin', 'wb').write(vb)

# 2. Raw newc magic "070701" in the uncompressed kernel image.
print('\nraw "070701" occurrences in vmlinux.bin:')
raw_hits = [m.start() for m in re.finditer(b'070701', vb)]
for o in raw_hits:
    hdr = vb[o:o + 110]
    is_hdr = re.fullmatch(rb'070701[0-9A-Fa-f]{104}', hdr) is not None
    print(f'  offset {o:#09x}: next 24 bytes {vb[o:o+24]!r}  valid 110-byte newc header: {is_hdr}')
if not raw_hits:
    print('  none')

# 3. gzip members inside vmlinux.bin: try every 1f 8b 08 and keep the ones that inflate to a newc archive.
print('\ngzip magic (1f 8b 08) occurrences in vmlinux.bin and what each inflates to:')
found = []
for m in re.finditer(b'\x1f\x8b\x08', vb):
    o = m.start()
    z = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        data = z.decompress(vb[o:]) + z.flush()
        ok = z.eof
    except zlib.error as e:
        print(f'  offset {o:#09x}: not a valid gzip stream ({e})')
        continue
    used = len(vb) - o - len(z.unused_data)
    kind = 'newc cpio' if data.startswith(b'070701') else 'other'
    print(f'  offset {o:#09x}: complete member {ok}, {used} compressed B -> {len(data)} B, starts {data[:6]!r} ({kind}); '
          f'{len(z.unused_data)} B follow the member, non-zero among them: {sum(1 for x in z.unused_data if x)}')
    if ok and kind == 'newc cpio':
        found.append((o, used, data))
assert len(found) == 1, f'expected exactly one embedded cpio, found {len(found)}'
o, used, cpio = found[0]
open(out + '/initramfs.cpio', 'wb').write(cpio)
print(f'\nembedded initramfs: gzip member at vmlinux.bin offset {o:#x}, {used} B compressed; cpio {len(cpio)} B sha256 {sha(cpio)}')

# 4. Cross-check the location with the package's own BUILD (ELF + System.map), not used to find it.
sm = {}
for l in open(PKG + '/BUILD/System.map'):
    a, t, n = l.split()
    sm[n] = int(a, 16)
elf = open(PKG + '/BUILD/vmlinux', 'rb').read()
e_phoff, = struct.unpack_from('<I', elf, 28)
e_phentsize, e_phnum = struct.unpack_from('<HH', elf, 42)
loads = []
for i in range(e_phnum):
    p_type, p_off, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<6I', elf, e_phoff + i * e_phentsize)
    if p_type == 1:
        loads.append((p_vaddr, p_filesz, p_memsz))
base = min(v for v, _, _ in loads)
print(f'cross-check: lowest PT_LOAD vaddr of BUILD/vmlinux {base:#x} (= _text {sm.get("_text", 0):#x}: {base == sm.get("_text")}); '
      f'gzip member vaddr {base + o:#x}; System.map __initramfs_start {sm["__initramfs_start"]:#x}, __initramfs_end {sm["__initramfs_end"]:#x} '
      f'-> start match {base + o == sm["__initramfs_start"]}, section length {sm["__initramfs_end"] - sm["__initramfs_start"]} B '
      f'(member {used} B + {sm["__initramfs_end"] - sm["__initramfs_start"] - used} B padding)')

# 5. Own newc parse (independent of the cpio tool), every entry.
ents = []
p = 0
lines = []
while True:
    h = cpio[p:p + 110]
    assert h[:6] == b'070701', f'bad magic at {p:#x}'
    f = [int(h[6 + 8 * i:14 + 8 * i], 16) for i in range(13)]
    ino, mode, uid, gid, nlink, mtime, fsize, dmaj, dmin, rmaj, rmin, nsz, chk = f
    name = cpio[p + 110:p + 110 + nsz - 1].decode()
    q = (p + 110 + nsz + 3) & ~3
    data = cpio[q:q + fsize]
    p = (q + fsize + 3) & ~3
    if name == 'TRAILER!!!':
        lines.append(f'{"":>8} {"":>8} TRAILER!!! at {p:#x}')
        break
    ents.append((name, mode, uid, gid, fsize, data, mtime, (rmaj, rmin)))
    lines.append(f'{mode:08o} {uid}:{gid} {fsize:>8} {sha(data)[:16] if (mode & 0o170000) == 0o100000 else "":16} {name}'
                 + (f' -> {data.decode()}' if (mode & 0o170000) == 0o120000 else '')
                 + (f' dev {rmaj}:{rmin}' if (mode & 0o170000) in (0o020000, 0o060000) else ''))
rest = cpio[p:]
lines.append(f'after TRAILER: {len(rest)} B, all zero: {not any(rest)}')
open(out + '/newc-list.txt', 'w').write('\n'.join(lines) + '\n')
print(f'own newc parse: {len(ents)} entries + TRAILER; padding after trailer {len(rest)} B all zero {not any(rest)}; list in newc-list.txt')

byname = {e[0]: e for e in ents}
for want in ('usr/bin/pscol', 'etc/rc.sysinit', 'etc/inittab'):
    e = byname[want]
    open(out + '/files/' + want.replace('/', '_'), 'wb').write(e[5])
    print(f'  {want}: mode {e[1]:o} uid:gid {e[2]}:{e[3]} size {e[4]} sha256 {sha(e[5])}')
for want in ('init', 'sbin/init', 'bin/busybox', 'bin/sh', 'usr/bin/psposk2', 'usr/bin/pspmd', 'ms0', 'dev/console', 'dev/joypad', 'dev/fb0', 'proc'):
    e = byname.get(want)
    if e is None:
        print(f'  {want}: absent')
    else:
        t = {0o100000: 'file', 0o040000: 'dir', 0o120000: 'symlink', 0o020000: 'chardev', 0o060000: 'blockdev'}.get(e[1] & 0o170000, '?')
        print(f'  {want}: {t} mode {e[1]:o}' + (f' -> {e[5].decode()}' if t == 'symlink' else '') + (f' dev {e[7][0]}:{e[7][1]}' if 'dev' in t else '')
              + (f' size {e[4]}' if t == 'file' else ''))
