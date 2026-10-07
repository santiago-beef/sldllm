#!/usr/bin/env python3
"""Compare the cpio embedded in the packaged image with the baseline initramfs
(extract/initramfs2.cpio = the original tree's psp-initramfs.cpio, IMPLEMENTATION 1.1),
entry by entry: raw 110-byte header + name + data. Usage: compare_cpio.py <embedded.cpio>"""
import sys, hashlib
def parse(b):
    p, out = 0, []
    while True:
        h = b[p:p + 110]; assert h[:6] == b'070701'
        f = [int(h[6 + 8 * i:14 + 8 * i], 16) for i in range(13)]
        nsz, fsz = f[11], f[6]
        name = b[p + 110:p + 110 + nsz - 1].decode()
        q = (p + 110 + nsz + 3) & ~3
        rec = (h, name, b[q:q + fsz], f)
        p = (q + fsz + 3) & ~3
        out.append(rec)
        if name == 'TRAILER!!!':
            return out, b[p:]
new, nt = parse(open(sys.argv[1], 'rb').read())
old, ot = parse(open('/home/ubuntu/psp/extract/initramfs2.cpio', 'rb').read())
print(f'baseline extract/initramfs2.cpio: {len(old)} entries incl. TRAILER, sha256 {hashlib.sha256(open("/home/ubuntu/psp/extract/initramfs2.cpio","rb").read()).hexdigest()}')
print(f'embedded (packaged image)       : {len(new)} entries incl. TRAILER')
on = [r[1] for r in old]; nn = [r[1] for r in new]
print('names only in embedded:', [n for n in nn if n not in on]); print('names only in baseline:', [n for n in on if n not in nn])
print('order of common names preserved:', [n for n in nn if n in on] == on)
od = {r[1]: r for r in old}
same = diff = 0
for r in new:
    o = od.get(r[1])
    if o is None: continue
    if o[0] == r[0] and o[2] == r[2]: same += 1
    else:
        diff += 1
        fields = ['ino','mode','uid','gid','nlink','mtime','filesize','devmaj','devmin','rdevmaj','rdevmin','namesize','check']
        ch = [f'{fields[i]} {o[3][i]:#x}->{r[3][i]:#x}' for i in range(13) if o[3][i] != r[3][i]]
        print(f'  differs: {r[1]}: header fields changed: {ch}; data changed: {o[2] != r[2]}')
print(f'common entries byte-identical (header+name+data): {same}; different: {diff}')
pe = [r for r in new if r[1] == 'usr/bin/pscol'][0]
print(f'new entry usr/bin/pscol: mode {pe[3][1]:o} uid {pe[3][2]} gid {pe[3][3]} nlink {pe[3][4]} ino {pe[3][0]} size {pe[3][6]} devmaj:min {pe[3][7]}:{pe[3][8]}')
