#!/usr/bin/env python3
"""r20_check.py - host-side check that the released kernel image fits what the
deployed pspboot loader can load and where it puts it (Stage 3 item R20).

Read-only on every input. Exit 0 only if every check passes.

  A  the loader's own constants, decoded from the deployed EBOOT.PBP's
     DATA.PSP (not assumed): decompression buffer size, gzread length,
     destination, cmdline area, entry registers, heap size, its own load range
  B  the kernel image's layout from the release vmlinux ELF section table and
     System.map: load range [_text, _text + len(vmlinux.bin)), BSS, _end,
     initramfs, the cmdline area, gunzip(deployed file) == vmlinux.bin
  C  limits and margins for the release and for the images known to boot

Usage: r20_check.py   (paths are fixed below; all are read-only inputs)
"""
import gzip
import hashlib
import os
import struct
import sys
import zlib

DEPLOY = '/home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE'
BASELINE_FOLDER = '/home/ubuntu/psp/pspboot-baseline'
REL = '/home/ubuntu/psp/work/out/20261006T052947Z'
BASE = '/home/ubuntu/psp/work/prebuilt'            # baseline rebuild (= original tree's build outputs)
IMG2008 = '/home/ubuntu/psp/extract/k'             # the 2008 image, decompressed (recon/image2008.md 1)
RELEASE_SHA = '4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8'
RAM_TOP = 0x8A000000                               # 32 MB from 0x88000000 (PSP-1001; HIGHMEM_START, spaces.h:30)
USER_PARTITION_BASE = 0x08800000                   # PSP user partition base: public PSP documentation, UNVERIFIED here

fails = []


def check(cond, what):
    print(('PASS  ' if cond else 'FAIL  ') + what)
    if not cond:
        fails.append(what)
    return cond


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ ELF helpers
def elf_sections(data):
    e_shoff = struct.unpack('<I', data[32:36])[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack('<HHH', data[46:52])
    secs = []
    for i in range(e_shnum):
        s = struct.unpack('<10I', data[e_shoff + i * e_shentsize:e_shoff + i * e_shentsize + 40])
        secs.append(dict(name_off=s[0], type=s[1], flags=s[2], addr=s[3], offset=s[4], size=s[5]))
    st = secs[e_shstrndx]
    for s in secs:
        o = st['offset'] + s['name_off']
        s['name'] = data[o:data.index(b'\0', o)].decode()
    return secs


def elf_phdrs(data):
    e_phoff = struct.unpack('<I', data[28:32])[0]
    e_phentsize, e_phnum = struct.unpack('<HH', data[42:46])
    out = []
    for i in range(e_phnum):
        p = struct.unpack('<8I', data[e_phoff + i * e_phentsize:e_phoff + i * e_phentsize + 32])
        out.append(dict(type=p[0], offset=p[1], vaddr=p[2], paddr=p[3], filesz=p[4], memsz=p[5]))
    return out


def sysmap(path):
    m = {}
    for line in open(path):
        a, t, n = line.split()[:3]
        m.setdefault(n, int(a, 16))
    return m


# ------------------------------------------------------------------ A: the loader
def word(elf, base_va, base_off, va):
    return struct.unpack('<I', elf[base_off + va - base_va:base_off + va - base_va + 4])[0]


def check_loader(folder, label):
    pbp = open(os.path.join(folder, 'EBOOT.PBP'), 'rb').read()
    offs = list(struct.unpack('<8I', pbp[8:40])) + [len(pbp)]
    elf = pbp[offs[6]:offs[7]]
    ph = elf_phdrs(elf)
    load = [p for p in ph if p['type'] == 1]
    check(len(load) == 1, '%s: DATA.PSP has one PT_LOAD' % label)
    L = load[0]
    va0, off0 = L['vaddr'], L['offset']
    W = lambda va: word(elf, va0, off0, va)
    lo, hi = va0, va0 + L['memsz']
    print('      %s: pspboot ELF load range %08x-%08x (filesz %d, memsz %d), entry %08x'
          % (label, lo, hi, L['filesz'], L['memsz'], struct.unpack('<I', elf[24:28])[0]))
    c = {}
    # decompress routine 0x890074c: malloc(0x400000) then gzread(gz, buf, 0x400000)
    c['malloc_call'] = (W(0x089007b8), W(0x089007bc))
    c['gzread_call'] = (W(0x089007c8), W(0x089007cc), W(0x089007d0), W(0x089007d4))
    ok_malloc = c['malloc_call'] == (0x0E243498, 0x3C040040)         # jal 0x890d260 ; lui a0,0x40
    ok_gzread = c['gzread_call'] == (0x02802021, 0x00402821, 0x0E240675, 0x3C060040)  # move a0,s4; move a1,v0; jal 0x89019d4; lui a2,0x40
    check(ok_malloc, '%s: 0x89007b8 jal 0x890d260 (newlib malloc) with a0 = 0x00400000 (lui a0,0x40 in the delay slot)' % label)
    check(ok_gzread, '%s: 0x89007d0 jal 0x89019d4 (zlib 1.2.3 gzread) with a1 = the malloc result, a2 = 0x00400000' % label)
    # the count returned by gzread is what is stored and later copied
    check((W(0x089007dc), W(0x089007fc)) == (0x00408021, 0xAE500000),
          '%s: gzread result (v0 -> s0) is stored as the size (sw s0,0(s2)) handed to the transfer' % label)
    # malloc identity: tail call into _malloc_r(_impure_ptr, n)
    check((W(0x0890d260), W(0x0890d264), W(0x0890d268), W(0x0890d26c)) == (0x00802821, 0x3C040892, 0x8C847324, 0x0A24349D),
          '%s: 0x890d260 = malloc(n) { return _malloc_r(_impure_ptr, n); }' % label)
    # gzread identity (zlib 1.2.3 gzio.c): s->mode != 'r' (offset 92) -> error; z_err -3 / -1 -> -1; 1 -> 0
    check((W(0x089019f8), W(0x089019fc), W(0x08901a0c), W(0x08901a14), W(0x08901a20)) ==
          (0x8083005C, 0x24020072, 0x2402FFFD, 0x2402FFFF, 0x24020001),
          '%s: 0x89019d4 has zlib 1.2.3 gzread\'s prologue checks (mode==\'r\', Z_DATA_ERROR, Z_ERRNO, Z_STREAM_END)' % label)
    check(b' inflate 1.2.3 Copyright 1995-2005 Mark Adler ' in elf, '%s: zlib "inflate 1.2.3" is linked' % label)
    # transfer 0x8900630(src, size): IE off, copy to 0x88000000, cmdline at +8 (256 B), jump 0x88000000
    exp = {0x0890065c: 0x0E242C87, 0x08900664: 0x0E2400CE, 0x08900674: 0x0E2400D4, 0x08900678: 0x3C048800,
           0x08900690: 0x36040008, 0x0890068c: 0x24060100, 0x089006e0: 0x3C028800, 0x089006e4: 0x0040F809,
           0x089006dc: 0x00002021, 0x089006e8: 0x00002821, 0x089006d8: 0x02203021,
           0x08900700: 0x0E2400D4, 0x08900704: 0x36110008}
    check(all(W(a) == v for a, v in exp.items()),
          '%s: transfer 0x8900630: IE off (jal 0x8900338), copy(0x88000000, src, size), copy(0x88000008, cmdline, 256), '
          'jalr 0x88000000 with a0 = 0, a1 = 0, a2 = s1 (0x88000008 or 0)' % label)
    check((W(0x08900338), W(0x0890033c), W(0x08900340), W(0x08900344)) == (0x40086000, 0x3409FFFE, 0x01094024, 0x40886000),
          '%s: 0x8900338 clears Status.IE (mfc0 t0,$12; and 0xfffe; mtc0)' % label)
    check([W(0x08900350 + 4 * i) for i in range(10)] ==
          [0x18C00008, 0x00804021, 0x00003821, 0x00A71021, 0x90440000, 0x01071821, 0x24E70001, 0x14E6FFFB, 0xA0640000, 0x03E00008],
          '%s: 0x8900350 is a forward byte copy using registers only (no stack)' % label)
    heap_kb = W(0x08925ff4)
    check(heap_kb == 8192, '%s: sce_newlib_heap_kb_size = %d KB (newlib heap: one 8 MB block, partition 2, by _sbrk 0x89139c0)' % (label, heap_kb))
    return dict(elf_lo=lo, elf_hi=hi, buf=0x00400000, dest=0x88000000, cmdline_off=8, cmdline_len=256,
                cmdline_global=0x08927348, heap=heap_kb * 1024, sha=sha(pbp))


# ------------------------------------------------------------------ B: a kernel build
def check_kernel(outdir, label, gz_path=None):
    elf = open(os.path.join(outdir, 'vmlinux'), 'rb').read()
    binimg = open(os.path.join(outdir, 'vmlinux.bin'), 'rb').read()
    sm = sysmap(os.path.join(outdir, 'System.map'))
    secs = elf_sections(elf)
    SHF_ALLOC = 2
    alloc = [s for s in secs if s['flags'] & SHF_ALLOC and s['size']]
    prog = [s for s in alloc if s['type'] != 8]      # not NOBITS
    nobits = [s for s in alloc if s['type'] == 8]
    text = sm['_text']
    lo = min(s['addr'] for s in prog)
    hi = max(s['addr'] + s['size'] for s in prog)
    print('      %s: ELF ALLOC sections:' % label)
    for s in sorted(alloc, key=lambda s: s['addr']):
        print('        %-22s %08x-%08x %8d B %s' % (s['name'], s['addr'], s['addr'] + s['size'], s['size'],
                                                   'NOBITS' if s['type'] == 8 else ''))
    check(text == 0x88000000 and lo == text, '%s: _text = lowest loadable address = 0x88000000 (load address, arch/mips/Makefile:598)' % label)
    check(hi - lo == len(binimg), '%s: vmlinux.bin length %d = highest loadable end %08x - _text' % (label, len(binimg), hi))
    check(hi == sm['__initramfs_end'], '%s: the loaded image ends at __initramfs_end %08x (initramfs is the last loaded section)' % (label, sm['__initramfs_end']))
    check(sm['__initramfs_end'] <= sm['__bss_start'], '%s: __initramfs_end %08x <= __bss_start %08x (initramfs and BSS do not overlap)' % (label, sm['__initramfs_end'], sm['__bss_start']))
    bss_lo = min(s['addr'] for s in nobits)
    bss_hi = max(s['addr'] + s['size'] for s in nobits)
    check(bss_lo >= hi and bss_hi == sm['_end'] and sm['__bss_stop'] == sm['_end'],
          '%s: all NOBITS sections lie in [%08x, %08x) above the loaded image; _end = __bss_stop = %08x' % (label, bss_lo, bss_hi, sm['_end']))
    for s in prog:
        o = s['addr'] - text
        if s['type'] == 1:
            if binimg[o:o + s['size']] != elf[s['offset']:s['offset'] + s['size']]:
                check(False, '%s: vmlinux.bin bytes of %s equal the ELF section' % (label, s['name']))
                break
    else:
        check(True, '%s: every PROGBITS section is at its address in vmlinux.bin, byte for byte' % label)
    w0 = struct.unpack('<I', binimg[:4])[0]
    check(w0 >> 26 == 2 and (0x88000000 | ((w0 & 0x3FFFFFF) << 2)) == sm['kernel_entry'],
          '%s: first word j kernel_entry (%08x)' % (label, sm['kernel_entry']))
    check(binimg[8:264] == b'\0' * 256 and sm['_stext'] >= 0x88000000 + 264,
          '%s: bytes 8..263 (pspboot\'s cmdline area) are zero padding of head.S .fill (head.S:141), _stext %08x' % (label, sm['_stext']))
    check(sm['__bss_start'] <= sm['fw_arg2'] < sm['_end'],
          '%s: fw_arg2 is in BSS; head.S:182-192 clears BSS first, then stores a0..a3' % label)
    gz_ok = None
    if gz_path:
        g = open(gz_path, 'rb').read()
        gz_ok = zlib.decompress(g, 31) == binimg
        check(gz_ok, '%s: gunzip(%s) == vmlinux.bin' % (label, gz_path))
    return dict(len=len(binimg), text=text, load_end=hi, bss_start=sm['__bss_start'], end=sm['_end'],
                initramfs=(sm['__initramfs_start'], sm['__initramfs_end']), sha=sha(binimg))


def main():
    print('== R20 host-side check (read-only inputs)')
    dep = {f: open(os.path.join(DEPLOY, f), 'rb').read() for f in ('EBOOT.PBP', 'kmodlib.prx', 'pspboot.conf', 'vmlinux-0.22.bin')}
    check(sha(dep['vmlinux-0.22.bin']) == RELEASE_SHA, 'deployed vmlinux-0.22.bin sha256 = released %s..' % RELEASE_SHA[:16])
    for f in ('EBOOT.PBP', 'kmodlib.prx', 'pspboot.conf'):
        check(dep[f] == open(os.path.join(BASELINE_FOLDER, f), 'rb').read(), 'deployed %s is byte-identical to pspboot-baseline/%s' % (f, f))
    conf = dep['pspboot.conf'].decode()
    check('\nkernel=vmlinux-0.22.bin' in conf, 'pspboot.conf names kernel=vmlinux-0.22.bin')

    print('\n== A. The loader (deployed EBOOT.PBP, DATA.PSP)')
    ld = check_loader(DEPLOY, 'deploy')

    print('\n== B. Kernel images')
    rel = check_kernel(REL, 'release', os.path.join(DEPLOY, 'vmlinux-0.22.bin'))
    base = check_kernel(BASE, 'baseline-rebuild', os.path.join(BASE, 'vmlinux-0.22.bin'))
    k2008 = open(IMG2008, 'rb').read()
    g2008 = open(os.path.join(BASELINE_FOLDER, 'vmlinux-0.22.bin'), 'rb').read()
    check(zlib.decompress(g2008, 31) == k2008, '2008 image: gunzip(pspboot-baseline/vmlinux-0.22.bin) == extract/k, %d B' % len(k2008))
    check(len(k2008) == base['len'], '2008 image has the baseline rebuild\'s length (%d B; recon/build.md: same size, other bytes)' % len(k2008))

    print('\n== C. Limits and margins')
    BUF = ld['buf']
    rows = [('2008 image (boots today [HW])', len(k2008), None),
            ('baseline rebuild', base['len'], base),
            ('RELEASE', rel['len'], rel)]
    for name, n, k in rows:
        print('      %-30s vmlinux.bin %9d B = 0x%06x; buffer margin %9d B (%.1f %% of 0x400000 used)'
              % (name, n, n, BUF - n, 100.0 * n / BUF))
    check(rel['len'] <= BUF, 'L1  release vmlinux.bin %d B <= pspboot gzread buffer %d B: margin %d B'
          % (rel['len'], BUF, BUF - rel['len']))
    dest_end_phys = (0x88000000 + rel['len']) & 0x1FFFFFFF
    check(dest_end_phys <= ld['elf_lo'] and dest_end_phys <= ld['cmdline_global'],
          'L2  copy destination [08000000, %08x) ends below pspboot\'s own code/data [%08x, %08x) and its cmdline global %08x: margin %d B'
          % (dest_end_phys, ld['elf_lo'], ld['elf_hi'], ld['cmdline_global'], ld['elf_lo'] - dest_end_phys))
    check(0x08000000 + BUF <= ld['elf_lo'],
          'L2  for ANY image the loader accepts (<= 0x400000 B) the destination ends at <= 08400000 < %08x' % ld['elf_lo'])
    print('      (L2, source buffer: copy is a forward byte copy from a source at a higher address than 0x08000000, '
          'so even an overlap with the source could not corrupt it; user partition base %08x is public PSP documentation, UNVERIFIED)'
          % USER_PARTITION_BASE)
    check(dest_end_phys <= USER_PARTITION_BASE, 'L2  destination end %08x <= user partition base %08x (UNVERIFIED base): margin %d B'
          % (dest_end_phys, USER_PARTITION_BASE, USER_PARTITION_BASE - dest_end_phys))
    det = (rel['end'] & ~0xFFFFF) + 0x100000
    check(rel['end'] < det <= RAM_TOP, 'L3  release _end %08x; psp_detect_mem_size starts at %08x < RAM top %08x (psp.c:429-441)'
          % (rel['end'], det, RAM_TOP))
    d_img = rel['len'] - base['len']
    d_bss = (rel['end'] - rel['bss_start']) - (base['end'] - base['bss_start'])
    d_gap = (rel['bss_start'] - rel['load_end']) - (base['bss_start'] - base['load_end'])
    d_all = (rel['end'] - rel['text']) - (base['end'] - base['text'])
    check(d_all == d_img + d_bss + d_gap, 'footprint growth adds up: %d = image %d + BSS %d + alignment gap %d' % (d_all, d_img, d_bss, d_gap))
    print('      in-memory footprint [_text, _end): release %d B (%08x-%08x), baseline %d B (%08x-%08x): +%d B'
          % (rel['end'] - rel['text'], rel['text'], rel['end'], base['end'] - base['text'], base['text'], base['end'], d_all))
    print('      growth vs baseline rebuild: vmlinux.bin +%d B, vmlinux-0.22.bin +%d B (the 48 KB = 49,152 B design bound: '
          'margins %d / %d B)' % (rel['len'] - base['len'], len(dep['vmlinux-0.22.bin']) - os.path.getsize(os.path.join(BASE, 'vmlinux-0.22.bin')),
                                  49152 - (rel['len'] - base['len']),
                                  49152 - (len(dep['vmlinux-0.22.bin']) - os.path.getsize(os.path.join(BASE, 'vmlinux-0.22.bin')))))
    print('      growth vs the 2008 image the stick boots: vmlinux.bin +%d B, vmlinux-0.22.bin +%d B'
          % (rel['len'] - len(k2008), len(dep['vmlinux-0.22.bin']) - len(g2008)))
    print('\nRESULT: %s (%d failed)' % ('PASS' if not fails else 'FAIL', len(fails)))
    for f in fails:
        print('  failed: ' + f)
    sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
