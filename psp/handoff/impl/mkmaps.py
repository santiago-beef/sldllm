#!/usr/bin/env python3
"""Write the BUILD directory of one kernel build (DESIGN 10.1, 10.6).

usage: mkmaps.py OUT_DIR DEST_DIR
  OUT_DIR   a work/out/<stamp> directory made by build.sh (vmlinux, System.map,
            banner.txt, vmlinux-0.22.bin, SHA256SUMS)
  DEST_DIR  the BUILD directory to create (must not exist)

DEST_DIR receives epcmap.txt, regmap.txt (grammar 2 of
work/decoder/psc_maps.py, the module the decoder reads them with: G2 attempt 1
F3 / OD-4), System.map, vmlinux, banner.txt, build_id.txt (0x%08x of the
CRC-32, zlib initial 0, of banner.txt: DESIGN 1.7 words 0-4, section 17 R-4),
panellayout.txt, IMAGE.sha256 (the sha256 of OUT_DIR's vmlinux-0.22.bin: the
image this directory belongs to, to compare with the G3 R3 record) and
SHA256SUMS (every file of the directory).

The Syscon_cmd step ranges and the register rows below were read from the
G2-attempt-1 disassembly (handoff/impl/syscon-window-diff.txt, the receive
and TX loops at +0x17c..+0x1c0 and +0x340..+0x398) against recon/syscon.md
1.2. The script refuses to write anything if the build does not match them:
the ranges must partition Syscon_cmd exactly, every anchor instruction (each
range and sub-range boundary of the register rows) must be where it says, the
registers the "all" rows name must not be written after the prologue except
by the hand-off's own restore, and the banner must be the NUL-terminated
linux_banner inside vmlinux.bin.
"""
import hashlib, os, re, shutil, subprocess, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, '/home/ubuntu/psp/work/decoder')
import psc_maps as M   # noqa: E402  the shared grammar

OUT = os.path.abspath(sys.argv[1]).rstrip('/')
DEST = os.path.abspath(sys.argv[2]).rstrip('/')
MAP = OUT + '/System.map'
VML = OUT + '/vmlinux'
if os.path.exists(DEST):
    sys.exit('%s exists; refusing to overwrite' % DEST)


def syms():
    t = []
    for l in open(MAP):
        a, k, n = l.split()[:3]
        t.append((int(a, 16), k, n))
    t.sort()
    return t


def objdump(start, stop):
    inner = '/work/' + VML[len('/home/ubuntu/psp/'):]
    cmd = ['sudo', 'docker', 'run', '--rm', '--platform', 'linux/386',
           '-v', '/home/ubuntu/psp:/work:ro', 'psp-build:bullseye', 'bash', '-c',
           'export PATH=/work/staging_dir/bin:/work/staging_dir/usr/bin:$PATH; '
           'mipsel-linux-uclibc-objdump -d --start-address=0x%x --stop-address=0x%x %s'
           % (0xffffffff00000000 | start, 0xffffffff00000000 | stop, inner)]
    txt = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    ins = {}
    for l in txt.splitlines():
        m = re.match(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(\S+)\s*(.*)$', l)
        if m:
            ins[int(m.group(1), 16)] = (m.group(2) + ' ' + m.group(3).split('<')[0].strip()).strip()
    return ins


S = syms()
addr = {n: a for a, k, n in S}
nxt = {}
for i, (a, k, n) in enumerate(S[:-1]):
    nxt[n] = S[i + 1][0]

base = addr['Syscon_cmd']
end = nxt['Syscon_cmd']

# (offset from Syscon_cmd, end offset exclusive, label) for this build
STEPS = [
    (0x000, 0x078, 'ENTRY'),   # prologue, hoisted bases and constants
    (0x078, 0x07c, 'S1'),      # lbu t0,0(t6): cnt = tx_buf[1]
    (0x07c, 0x080, 'S0'),      # retry: sw zero,8(sp) (PSC 2.1 A2)
    (0x080, 0x0bc, 'S1'),      # TX checksum, tx_buf[cnt] = ~sum
    (0x0bc, 0x0c0, 'S2'),      # tx_buf[cnt+1] = 0xff
    (0x0c0, 0x0e0, 'S3'),      # rx_buf prefill 0xff
    (0x0e0, 0x0ec, 'S5'),      # dmy = REG32(0xbe240004)
    (0x0ec, 0x0f0, 'S6'),      # REG32(0xbe24000c) = 8
    (0x0f0, 0x100, 'S7'),      # RX not empty?
    (0x100, 0x16c, 'S8'),      # drain loop, -3 exit
    (0x16c, 0x17c, 'S9'),      # st9 = REG32(0xbe58000c) (+ li v1,3 of S10)
    (0x17c, 0x180, 'S11'),     # addiu t1,t0,1 (cnt + 1)
    (0x180, 0x184, 'S10'),     # REG32(0xbe580020) = 3
    (0x184, 0x1c0, 'S11'),     # TX push loop
    (0x1c0, 0x1c8, 'S12'),     # REG32(0xbe580004) = 6
    (0x1c8, 0x1cc, 'S13'),     # REG32(0xbe240008) = 8 (G3 high)
    (0x1cc, 0x218, 'S14'),     # ACK wait, -4 teardown
    (0x218, 0x30c, 'REC'),     # exit hand-off asm (PSC_XFER_OUT) and psc_xfer_out call
    (0x30c, 0x340, 'EXIT'),    # epilogue
    (0x340, 0x350, 'S15'),     # ptr, result = 0 (S16), i, then the ack store at +0x34c
    (0x350, 0x398, 'S18'),     # receive loop
    (0x398, 0x3a8, 'S19'),     # REG32(0xbe580004) = 4
    (0x3a8, 0x3ac, 'S20'),     # REG32(0xbe24000c) = 8 (G3 low)
    (0x3ac, 0x400, 'S21'),     # checksum
    (0x400, 0x428, 'S22'),     # 0x80/0x81 retry, -5
    (0x428, 0x430, 'S1'),      # cnt == 0: no sum loop
]
ANCHORS = {
    0x044: 'move t5,a0',
    0x050: 'addiu t6,a0,1',
    0x054: 'move t8,zero',
    0x074: 'addiu t9,a1,2',
    0x078: 'lbu t0,0(t6)',
    0x07c: 'sw zero,8(sp)',
    0x0bc: 'sb v0,0(a0)',
    0x0e0: 'lw v0,0(s3)',
    0x0ec: 'sw s5,0(s0)',
    0x100: 'sw s1,8(sp)',
    0x16c: 'lw v0,0(t2)',
    0x17c: 'addiu t1,t0,1',
    0x180: 'sw v1,0(a2)',
    0x184: 'move a3,t5',
    0x188: 'move t0,zero',
    0x18c: 'lbu v0,0(a3)',
    0x19c: 'addiu t0,t0,2',
    0x1b0: 'addiu a3,a3,2',
    0x1b4: 'sw v0,0(t4)',
    0x1b8: 'bnezl a0,%08x' % (base + 0x190),
    0x1c0: 'li v0,6',
    0x1c8: 'sw s4,0(s6)',
    0x1cc: 'sw s1,12(sp)',
    0x218: 'addiu sp,sp,-128',
    0x30c: 'addiu sp,sp,128',
    0x338: 'jr ra',
    0x340: 'move a3,t9',
    0x344: 'move t3,zero',
    0x348: 'li t0,2',
    0x34c: 'sw v0,0(s8)',
    0x350: 'lw v0,0(t2)',
    0x364: 'lw v0,0(t4)',
    0x380: 'addiu a3,a3,2',
    0x384: 'j %08x' % (base + 0x350),
    0x388: 'addiu t0,t0,2',
    0x390: 'bnez t1,%08x' % (base + 0x380),
    0x3a8: 'sw s4,0(s0)',
    0x414: 'addiu t8,t8,1',
    0x418: 'bnel t8,v0,%08x' % (base + 0x07c),
    0x41c: 'lbu t0,0(t6)',
}


def rng(a, b):
    return (base + a, base + b)


# regmap rows: (steps, var, slot, offset, epc range or None, where)
# var = slot - offset (psc_maps.py). i at S11 = bytes pushed to the TX FIFO;
# i at S15-S18 = bytes popped from the RX FIFO; k = i // 2, j = i // 2 (10.6).
ROWS = [
    ('all', 'tx_buf', M.slot_of_reg(13), 0, None, 't5 = a0 from +0x44; not written after the prologue'),
    ('all', 'rx_buf', M.slot_of_reg(25), 2, None, 't9 = rx_buf + 2 from +0x74 (a1 is reused by the -4 teardown)'),
    ('all', 'retry_cnt', M.slot_of_reg(24), 0, None, 't8: 0 at +0x54, +1 at +0x414'),
    ('S0-S3', 'cnt', M.slot_of_reg(8), 0, None, 't0 = tx_buf[1] (lbu at +0x78; at +0x41c on a retry)'),
    ('S1', 'cnt', '-', 0, rng(0x078, 0x07c), 'the load at +0x78 has not run'),
    ('S11', 'cnt', M.slot_of_reg(9), 1, rng(0x180, 0x1c0), 't1 = cnt + 1 (+0x17c)'),
    ('S11', 'i', 'zero', 0, rng(0x17c, 0x180), 'TX loop not started: nothing pushed'),
    ('S11', 'i', 'zero', 0, rng(0x184, 0x18c), 'TX loop not started: nothing pushed'),
    ('S11', 'i', M.slot_of_reg(8), 0, rng(0x18c, 0x1a0), 't0 = i (bytes pushed) until addiu t0 at +0x19c'),
    ('S11', 'i', M.slot_of_reg(8), 2, rng(0x1a0, 0x1b8), 't0 = i + 2 from +0x19c until the push at +0x1b4 runs'),
    ('S11', 'i', M.slot_of_reg(8), 0, rng(0x1b8, 0x1c0), 'push done: t0 = i'),
    ('S11', 'ptr', M.slot_of_reg(7), 0, rng(0x188, 0x1b4), 'a3 = tx_buf + i (move a3,t5 at +0x184)'),
    ('S11', 'ptr', M.slot_of_reg(7), 2, rng(0x1b4, 0x1b8), 'a3 advanced at +0x1b0, push at +0x1b4 not run'),
    ('S11', 'ptr', M.slot_of_reg(7), 0, rng(0x1b8, 0x1c0), 'push done: a3 = tx_buf + i'),
    ('S8', 'spin', 'stack+8', 0, None, 'drain counter, stack slot of Syscon_cmd'),
    ('S14', 'spin_ack', 'stack+12', 0, None, 'ACK counter, stack slot of Syscon_cmd'),
    ('S15', 'i', 'zero', 0, None, 'nothing popped yet'),
    ('S15', 'result', M.slot_of_reg(11), 0, rng(0x348, 0x350), 't3 = 0 from +0x344'),
    ('S16-S18', 'result', M.slot_of_reg(11), 0, None, 't3'),
    ('S16-S18', 'i', M.slot_of_reg(8), 2, rng(0x350, 0x368), 't0 = i + 2 (li t0,2 at +0x348) up to the data load at +0x364'),
    ('S16-S18', 'i', M.slot_of_reg(8), 0, rng(0x368, 0x398), 'the data load ran: this word is popped, t0 = i until addiu t0 at +0x388'),
    ('S16-S18', 'pending', 'zero', -1, rng(0x354, 0x368), '1: status loaded at +0x350, data load at +0x364 not run (10.7 P6 "between its status test and its data read")'),
    ('S16-S18', 'pending', 'zero', 0, None, '0 elsewhere in the loop'),
    ('S16-S18', 'ptr', M.slot_of_reg(7), 2, rng(0x350, 0x368), 'a3 = rx_buf + i + 2 (move a3,t9 at +0x340)'),
    ('S16-S18', 'ptr', M.slot_of_reg(7), 0, rng(0x368, 0x384), 'a3 = rx_buf + i'),
    ('S16-S18', 'ptr', M.slot_of_reg(7), 2, rng(0x384, 0x38c), 'a3 advanced at +0x380, t0 not yet (delay slot +0x388)'),
    ('S16-S18', 'ptr', M.slot_of_reg(7), 0, rng(0x38c, 0x398), 'a3 = rx_buf + i (stores before the advance)'),
    ('S21-S22', 'result', M.slot_of_reg(11), 0, None, 't3'),
    ('LEDRMW', 'loaded', M.slot_of_reg(5), 0, None, 'a1 in both read-modify-writes of psp_led_ctrl'),
]

ins = objdump(base, end)
errs = []
if end - base != STEPS[-1][1]:
    errs.append('Syscon_cmd size %#x, ranges end at %#x' % (end - base, STEPS[-1][1]))
cover = sorted((a, b) for a, b, l in STEPS)
if cover[0][0] != 0:
    errs.append('ranges do not start at 0')
for (a0, b0), (a1, b1) in zip(cover, cover[1:]):
    if b0 != a1:
        errs.append('gap or overlap at %#x/%#x' % (b0, a1))
for off, want in ANCHORS.items():
    got = ins.get(base + off, '').replace('\t', ' ')
    if got != want:
        errs.append('anchor +%#x: want "%s", got "%s"' % (off, want, got))
# the "all" registers are written only in the prologue, by the hand-off's
# restore (REC +0x218..+0x30c) and, for t8, by the retry increment
STORE = ('sw', 'sh', 'sb', 'j', 'jr', 'jal', 'b', 'mthi', 'mtlo')
for reg, allowed in (('t5', {0x044}), ('t9', {0x074}), ('t8', {0x054, 0x414})):
    for a, t in sorted(ins.items()):
        mn, _, ops = t.partition(' ')
        if mn in STORE or mn.startswith('b'):
            continue
        if ops.split(',')[0] == reg and (a - base) not in allowed and not (0x218 <= a - base < 0x30c):
            errs.append('%s written at +%#x (%s): an "all" row would be wrong' % (reg, a - base, t))
led = addr['psp_led_ctrl']
li = objdump(led, nxt['psp_led_ctrl'])
led_set = [a for a, t in li.items() if t.startswith('lw a1,0(v0)')]
if len(led_set) != 2:
    errs.append('psp_led_ctrl: expected 2 LED loads, got %d' % len(led_set))
for a in led_set:
    if not li.get(a + 8, '').startswith('sw v1,0(v0)'):
        errs.append('psp_led_ctrl: no store 8 bytes after the load at %08x' % a)
banner = open(OUT + '/banner.txt', 'rb').read()
img = open(OUT + '/vmlinux.bin', 'rb').read()
if not banner.startswith(b'Linux version ') or not banner.endswith(b'\n') or img.count(banner + b'\0') != 1:
    errs.append('banner.txt is not the NUL-terminated linux_banner of vmlinux.bin')
if errs:
    print('\n'.join(errs))
    sys.exit(1)

build_id = zlib.crc32(banner) & 0xFFFFFFFF
os.makedirs(DEST)
epc = [M.EPCMAP_MAGIC + '\n',
       '# epcmap.txt (DESIGN 10.6) for %s\n' % OUT,
       '# banner: %s' % banner.decode(),
       '# <start> <end> <label>: end exclusive, hex (grammar: work/decoder/psc_maps.py).\n'
       '# Step labels S0..S23, ENTRY, EXIT, REC inside Syscon_cmd (recon/syscon.md 1.2);\n'
       '# LEDRMW between the load and the store of an LED read-modify-write; function\n'
       '# names elsewhere. S0 = retry: (the per-attempt PSC store, memory only), P0.\n'
       '# S4 and S17 have no code (a comment and a compiled-out block). S15 covers\n'
       '# ptr/result/i set-up and the ack store at +0x34c: an EPC labelled S15 means the\n'
       '# ack has not yet executed (P5b). S16 (result = 0) is the "move t3,zero" inside\n'
       '# S15. The recording wrapper psc_syscon_cmd (A1, the call, the exit call) is\n'
       '# ENTRY as a whole; psc_sc_exit and psc_xfer_out are REC. Both map to P0 (10.6).\n']
for a, b, l in STEPS:
    epc.append('%08x %08x %s\n' % (base + a, base + b, l))
w = addr['psc_syscon_cmd']
epc.append('%08x %08x ENTRY\n' % (w, nxt['psc_syscon_cmd']))
for n in ('psc_sc_exit', 'psc_xfer_out'):
    epc.append('%08x %08x REC\n' % (addr[n], nxt[n]))
for a in sorted(led_set):
    epc.append('%08x %08x LEDRMW\n' % (a + 4, a + 12))   # after the lw, through the sw
for i, (a, k, n) in enumerate(S[:-1]):
    if k in 'tT' and n not in ('Syscon_cmd', 'psc_syscon_cmd', 'psc_sc_exit', 'psc_xfer_out'):
        epc.append('%08x %08x %s\n' % (a, S[i + 1][0], n))
epc = ''.join(epc)

reg = [M.REGMAP_MAGIC + '\n',
       '# regmap.txt (DESIGN 10.6) for %s\n' % OUT,
       '# banner: %s' % banner.decode(),
       '# <steps> <var> <slot> <offset> <epc>  [# where]   (grammar: work/decoder/psc_maps.py)\n'
       '# var = slot - offset. Slots r[0..13] = $2..$15, r[14] = $24 (t8), r[15] = $25 (t9),\n'
       '# the order of W r[] / lc_r[] (DESIGN 1.3); zero = 0; stack+N = Syscon_cmd stack slot\n'
       '# (not in a W record); epc "-" = the whole step, else start-end (hex, end exclusive),\n'
       '# and a row with a range wins. i at S11 = bytes pushed (k = i / 2, P2); i at S15-S18 =\n'
       '# bytes popped (j = i / 2, P6). i and ptr are in registers 2..15 at S11 and S16-S18\n'
       '# (t0 = $8, a3 = $7), as in the baseline (syscon.o +0x180..+0x1b4, +0x244..+0x298):\n'
       '# k and j are recoverable from W r[] and lc_r[] (R10).\n']
for steps, var, slot, off, er, where in ROWS:
    reg.append(M.format_regrow(steps, var, slot, off, er, where))
reg = ''.join(reg)

# the reader must accept what the writer wrote (one grammar)
M.parse_epcmap_text(epc, 'epcmap.txt')
M.parse_regmap_text(reg, 'regmap.txt')

with open(DEST + '/epcmap.txt', 'w') as f:
    f.write(epc)
with open(DEST + '/regmap.txt', 'w') as f:
    f.write(reg)
for n in ('System.map', 'vmlinux', 'banner.txt'):
    shutil.copy2(OUT + '/' + n, DEST + '/' + n)
shutil.copy2(os.path.join(HERE, 'panellayout.txt'), DEST + '/panellayout.txt')
with open(DEST + '/build_id.txt', 'w') as f:
    f.write('0x%08x\n' % build_id)
with open(DEST + '/IMAGE.sha256', 'w') as f:     # the image this directory belongs to (G3 R3)
    f.write('%s  vmlinux-0.22.bin\n' % hashlib.sha256(open(OUT + '/vmlinux-0.22.bin', 'rb').read()).hexdigest())
with open(DEST + '/SHA256SUMS', 'w') as f:
    for n in sorted(os.listdir(DEST)):
        if n != 'SHA256SUMS':
            f.write('%s  %s\n' % (hashlib.sha256(open(DEST + '/' + n, 'rb').read()).hexdigest(), n))
print('BUILD written to %s for %s; build_id 0x%08x' % (DEST, OUT, build_id))
