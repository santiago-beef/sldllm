#!/usr/bin/env python3
"""pathcount.py - per-path instruction counts and stack depth of the recording
code, measured by executing the kernel's own machine code (G2 attempt 1 F5,
section 17 R-3; G1 ruling advisory A-1, red team K8).

usage: pathcount.py BASE_OUT NEW_OUT [REPORT.txt]
  BASE_OUT  build.sh output of the baseline tree (work/out/20260927T204657Z)
  NEW_OUT   build.sh output of the build under review

How. objdump -d of each vmlinux (the tree's own objdump, in the container)
gives every instruction; vmlinux.bin is loaded at 0x88000000 with a zeroed BSS
up to _end. A small MIPS32 interpreter (integer instructions, branch delay
slots, likely branches, HI/LO, CP0 Count/Status/Cause as below) runs the code
from a real entry point to a stop address and counts every executed
instruction, delay slots included (a likely branch's annulled slot is not
counted). It records the lowest sp reached. Memory outside the image is a
sparse zero-filled store; the syscon SPI (0xbe58xxxx) and GPIO (0xbe24xxxx)
registers are a model of the transaction: RX FIFO empty at the start (no
drain), the ACK (0xbe240020 bit 4) after ACK_POLLS polls of a high GPIO3,
then the reply words in the FIFO. CP0 Count advances by one per instruction
(the 1-IPC assumption of DESIGN 5.4, UNVERIFIED for the Allegrex); Status IE
is 1 in thread context, 0 in the timer interrupt.

Paths (each run twice; the second, warm run is reported, the first too where
it differs):
  P08   _pspSysconGetCtrl2 (thread, cmd 0x08, a 5-word reply), entry to return
  P33   pspSyscon_tx_dword(1, 0x33, 3) (thread, a 2-word reply)
  TICK  plat_irq_dispatch on an ordinary timer tick, up to the call of
        irq_enter (everything the instrumentation adds to a tick runs there)
  WD    the same on a watchdog tick (tick 1250k): the Nop, thread idle
  WDP   a watchdog tick that interrupts the thread inside its 0x08 command at
        S14 (ACK wait): the thread's registers are saved as by SAVE_ALL into a
        pt_regs on its stack (thread_info->regs points at it) and the timer
        path runs below it (H4's straddle, interrupt side only)
  T2D   a tick at 125 mod 250 with the stall panel painting (the deepest
        frame, psc_panel_t2d 328 B); new build only
For the thread paths the counts are split at the transaction window: before
S5 (the first syscon MMIO access), S5..S20 (first to last MMIO access, both
included) and after S20; and by function. Stack: bytes below the entry sp
(thread paths) or below the pt_regs frame (interrupt paths; add PT_SIZE 176
for the exception frame itself, include/asm-mips/ptrace.h:30-52).
"""
import os
import re
import struct
import subprocess
import sys

DEC = '/home/ubuntu/psp/work/decoder'
sys.path.insert(0, DEC)
import psc_format as F  # noqa: E402

RN = {'zero': 0, 'at': 1, 'v0': 2, 'v1': 3, 'a0': 4, 'a1': 5, 'a2': 6, 'a3': 7,
      't0': 8, 't1': 9, 't2': 10, 't3': 11, 't4': 12, 't5': 13, 't6': 14, 't7': 15,
      's0': 16, 's1': 17, 's2': 18, 's3': 19, 's4': 20, 's5': 21, 's6': 22, 's7': 23,
      't8': 24, 't9': 25, 'k0': 26, 'k1': 27, 'gp': 28, 'sp': 29, 's8': 30, 'fp': 30, 'ra': 31}
M32 = 0xFFFFFFFF
PT_SIZE = 176
ACK_POLLS = 20
LINE = re.compile(r'^\s*([0-9a-f]{8}):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)$')
FUNC = re.compile(r'^([0-9a-f]{8}) <(\S+)>:')


def s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def disasm(out):
    cache = os.path.join(os.environ.get('PATHCOUNT_CACHE', '/tmp'),
                         'pathcount-%s.objdump' % os.path.basename(out.rstrip('/')))
    if not os.path.exists(cache):
        inner = '/work/' + (out + '/vmlinux')[len('/home/ubuntu/psp/'):]
        txt = subprocess.run(['sudo', 'docker', 'run', '--rm', '--platform', 'linux/386', '-v',
                              '/home/ubuntu/psp:/work:ro', 'psp-build:bullseye', 'bash', '-c',
                              'export PATH=/work/staging_dir/bin:/work/staging_dir/usr/bin:$PATH; '
                              'mipsel-linux-uclibc-objdump -d %s' % inner],
                             check=True, capture_output=True, text=True).stdout
        open(cache, 'w').write(txt)
    ins, funcs, cur = {}, {}, None
    for l in open(cache):
        m = FUNC.match(l)
        if m:
            cur = m.group(2)
            funcs[int(m.group(1), 16)] = cur
            continue
        m = LINE.match(l)
        if m:
            ops = m.group(4).split('<')[0].strip()
            ins[int(m.group(1), 16)] = (m.group(3), [o.strip() for o in ops.split(',')] if ops else [])
    return ins, funcs


class Device(object):
    """SPI/GPIO of the syscon link, as Syscon_cmd uses them."""

    def __init__(self):
        self.reset(None)

    def reset(self, reply, words=None, never_ack=False, rx_stuck=False):
        self.reply = reply
        self.words = words          # explicit reply words (nwords table)
        self.never_ack = never_ack  # -4: GPIO4 never rises
        self.rx_stuck = rx_stuck    # -3: RX FIFO never empties before the request
        self.fifo = []
        self.g3_high = False
        self.polls = 0
        self.acked = False
        self.mmio = []          # (instruction index, addr, 'r'/'w')

    def read(self, a, n):
        if a == 0xbe58000c:     # SPI status: b2 RX not empty
            return (4 if (self.fifo or (self.rx_stuck and not self.g3_high)) else 0) | 1
        if a == 0xbe580008:     # RX data
            if self.rx_stuck and not self.g3_high and not self.fifo:
                return 0x1234
            return self.fifo.pop(0) if self.fifo else 0xFFFF
        if a == 0xbe240020:     # GPIO interrupt status: b4 = ACK (GPIO4)
            if self.g3_high and not self.acked and not self.never_ack:
                self.polls += 1
                if self.polls > ACK_POLLS:
                    self.acked = True
                    self.fifo = list(self.reply_words())
            return 0x10 if self.acked else 0
        if a == 0xbe240004:     # GPIO port read
            return 0x00000018
        return 0

    def write(self, a, v):
        if a == 0xbe240008 and v & 8:        # port set: GPIO3 high, a new request
            self.g3_high = True
            self.polls = 0
            self.acked = False
            self.fifo = []
        if a == 0xbe24000c and v & 8:        # port clear: GPIO3 low
            self.g3_high = False
        if a == 0xbe240024:
            self.acked = self.acked          # acknowledge (latched model)

    def reply_words(self):
        if self.words is not None:
            return self.words
        cmd, data = self.reply
        b = [0x22, 3 + len(data), cmd] + list(data)       # rx[1] = bytes before the checksum
        b.append((sum(b) & 0xFF) ^ 0xFF)
        if len(b) % 2:
            b.append(0xFF)
        return [(b[i] << 8) | b[i + 1] for i in range(0, len(b), 2)]


class CPU(object):
    def __init__(self, out):
        self.out = out
        self.ins, self.funcs = disasm(out)
        self.fstart = sorted(self.funcs)
        self.sym = {}
        for l in open(out + '/System.map'):
            a, k, n = l.split()[:3]
            self.sym[n] = int(a, 16)
        img = open(out + '/vmlinux.bin', 'rb').read()
        self.base = 0x88000000
        self.mem = bytearray(img) + bytearray(self.sym['_end'] - self.base - len(img))
        self.sparse = {}
        self.dev = Device()
        self.r = [0] * 32
        self.hi = self.lo = 0
        self.count = 0
        self.status = 0x1000FF01
        self.cause = 0
        self.n = 0
        self.trace = []

    # ---------------------------------------------------------------- memory
    def _mm(self, a):
        return 0xbe000000 <= a < 0xbf000000 or 0xbc000000 <= a < 0xbd000000

    def rd(self, a, n, signed=False):
        a &= M32
        if self._mm(a):
            v = self.dev.read(a, n)
            self.dev.mmio.append((self.n, a, 'r'))
        elif self.base <= a < self.base + len(self.mem):
            o = a - self.base
            v = int.from_bytes(self.mem[o:o + n], 'little')
        else:
            v = 0
            for i in range(n):
                v |= self.sparse.get(a + i, 0) << (8 * i)
        if signed and v & (1 << (8 * n - 1)):
            v -= 1 << (8 * n)
        return v & M32

    def wr(self, a, n, v):
        a &= M32
        if self._mm(a):
            self.dev.write(a, v & ((1 << 8 * n) - 1))
            self.dev.mmio.append((self.n, a, 'w'))
            return
        if self.base <= a < self.base + len(self.mem):
            o = a - self.base
            self.mem[o:o + n] = (v & ((1 << 8 * n) - 1)).to_bytes(n, 'little')
            return
        for i in range(n):
            self.sparse[a + i] = (v >> (8 * i)) & 0xFF

    def w32(self, a, v):
        self.wr(a, 4, v)

    def r32(self, a):
        return self.rd(a, 4)

    def func_of(self, pc):
        import bisect
        i = bisect.bisect_right(self.fstart, pc) - 1
        return self.funcs[self.fstart[i]] if i >= 0 else '?'

    # ---------------------------------------------------------------- execution
    def reg(self, t):
        return RN[t]

    def ea(self, t):
        m = re.match(r'^(-?\d+)\((\w+)\)$', t)
        return (int(m.group(1)) + self.r[RN[m.group(2)]]) & M32

    def imm(self, t):
        return int(t, 0)

    def run(self, pc, stop, maxn=2000000):
        self.minsp = self.r[29]
        while pc not in stop:
            pc = self.step(pc)
            if self.n > maxn:
                raise SystemExit('runaway at %08x (%s)' % (pc, self.func_of(pc)))
        return pc

    def step(self, pc, in_ds=False):
        if pc not in self.ins:
            raise SystemExit('no instruction at %08x' % pc)
        mn, o = self.ins[pc]
        r = self.r
        self.trace.append(pc)
        self.n += 1
        self.count += 1
        nxt = pc + 4
        br = None               # (taken, target, likely, link)
        if mn == 'nop' or mn in ('sync', 'cache', 'ssnop', 'ehb', 'pref'):
            pass
        elif mn == 'move':
            r[RN[o[0]]] = r[RN[o[1]]]
        elif mn == 'li':
            r[RN[o[0]]] = self.imm(o[1]) & M32
        elif mn == 'lui':
            r[RN[o[0]]] = (self.imm(o[1]) << 16) & M32
        elif mn in ('addiu', 'addi'):
            r[RN[o[0]]] = (r[RN[o[1]]] + self.imm(o[2])) & M32
        elif mn in ('addu', 'add'):
            r[RN[o[0]]] = (r[RN[o[1]]] + r[RN[o[2]]]) & M32
        elif mn in ('subu', 'sub'):
            r[RN[o[0]]] = (r[RN[o[1]]] - r[RN[o[2]]]) & M32
        elif mn == 'negu':
            r[RN[o[0]]] = (-r[RN[o[1]]]) & M32
        elif mn == 'and':
            r[RN[o[0]]] = r[RN[o[1]]] & r[RN[o[2]]]
        elif mn == 'or':
            r[RN[o[0]]] = r[RN[o[1]]] | r[RN[o[2]]]
        elif mn == 'xor':
            r[RN[o[0]]] = r[RN[o[1]]] ^ r[RN[o[2]]]
        elif mn == 'nor':
            r[RN[o[0]]] = ~(r[RN[o[1]]] | r[RN[o[2]]]) & M32
        elif mn == 'not':
            r[RN[o[0]]] = ~r[RN[o[1]]] & M32
        elif mn == 'andi':
            r[RN[o[0]]] = r[RN[o[1]]] & (self.imm(o[2]) & 0xFFFF)
        elif mn == 'ori':
            r[RN[o[0]]] = r[RN[o[1]]] | (self.imm(o[2]) & 0xFFFF)
        elif mn == 'xori':
            r[RN[o[0]]] = r[RN[o[1]]] ^ (self.imm(o[2]) & 0xFFFF)
        elif mn == 'sll':
            r[RN[o[0]]] = (r[RN[o[1]]] << self.imm(o[2])) & M32
        elif mn == 'srl':
            r[RN[o[0]]] = r[RN[o[1]]] >> self.imm(o[2])
        elif mn == 'sra':
            r[RN[o[0]]] = (s32(r[RN[o[1]]]) >> self.imm(o[2])) & M32
        elif mn == 'sllv':
            r[RN[o[0]]] = (r[RN[o[1]]] << (r[RN[o[2]]] & 31)) & M32
        elif mn == 'srlv':
            r[RN[o[0]]] = r[RN[o[1]]] >> (r[RN[o[2]]] & 31)
        elif mn == 'srav':
            r[RN[o[0]]] = (s32(r[RN[o[1]]]) >> (r[RN[o[2]]] & 31)) & M32
        elif mn == 'slt':
            r[RN[o[0]]] = 1 if s32(r[RN[o[1]]]) < s32(r[RN[o[2]]]) else 0
        elif mn == 'sltu':
            r[RN[o[0]]] = 1 if r[RN[o[1]]] < r[RN[o[2]]] else 0
        elif mn == 'slti':
            r[RN[o[0]]] = 1 if s32(r[RN[o[1]]]) < self.imm(o[2]) else 0
        elif mn == 'sltiu':
            r[RN[o[0]]] = 1 if r[RN[o[1]]] < (self.imm(o[2]) & M32) else 0
        elif mn == 'movn':
            if r[RN[o[2]]]:
                r[RN[o[0]]] = r[RN[o[1]]]
        elif mn == 'movz':
            if not r[RN[o[2]]]:
                r[RN[o[0]]] = r[RN[o[1]]]
        elif mn == 'multu':
            p = r[RN[o[0]]] * r[RN[o[1]]]
            self.lo, self.hi = p & M32, (p >> 32) & M32
        elif mn == 'mult':
            p = s32(r[RN[o[0]]]) * s32(r[RN[o[1]]])
            self.lo, self.hi = p & M32, (p >> 32) & M32
        elif mn in ('divu', 'div'):
            a, b = (r[RN[o[-2]]], r[RN[o[-1]]]) if mn == 'divu' else (s32(r[RN[o[-2]]]), s32(r[RN[o[-1]]]))
            if b:
                q = abs(a) // abs(b) * (1 if (a >= 0) == (b >= 0) else -1)
                self.lo, self.hi = q & M32, (a - q * b) & M32
        elif mn == 'mfhi':
            r[RN[o[0]]] = self.hi
        elif mn == 'mflo':
            r[RN[o[0]]] = self.lo
        elif mn == 'mthi':
            self.hi = r[RN[o[0]]]
        elif mn == 'mtlo':
            self.lo = r[RN[o[0]]]
        elif mn == 'teq':
            pass
        elif mn.startswith('0x'):    # objdump has no name for MIPS32r2 EXT/INS
            wd = int(mn, 16)
            rs, rt, rd, sa, fn = (wd >> 21) & 31, (wd >> 16) & 31, (wd >> 11) & 31, (wd >> 6) & 31, wd & 63
            if wd >> 26 != 0x1f or fn not in (0, 4):
                raise SystemExit('unsupported word %s at %08x (%s)' % (mn, pc, self.func_of(pc)))
            if fn == 0:              # ext rt, rs, pos=sa, size=rd+1
                r[rt] = (r[rs] >> sa) & ((1 << (rd + 1)) - 1)
            else:                    # ins rt, rs, pos=sa, size=rd-sa+1
                size = rd - sa + 1
                mask = ((1 << size) - 1) << sa
                r[rt] = (r[rt] & ~mask & M32) | ((r[rs] << sa) & mask)
        elif mn == 'mfc0':
            n = int(o[1].lstrip('$'))
            # $16 Config: D-cache size field (bits 8:6) = 3, 2048 << 3 = 16 KB
            # (pspClearDcache's loop bound; the Allegrex D-cache size is UNVERIFIED)
            r[RN[o[0]]] = {9: self.count & M32, 12: self.status, 13: self.cause, 16: 3 << 6}.get(n, 0)
        elif mn == 'mtc0':
            n = int(o[1].lstrip('$'))
            if n == 9:
                self.count = r[RN[o[0]]]
            elif n == 12:
                self.status = r[RN[o[0]]]
        elif mn in ('lw', 'lh', 'lhu', 'lb', 'lbu'):
            n = {'lw': 4, 'lh': 2, 'lhu': 2, 'lb': 1, 'lbu': 1}[mn]
            r[RN[o[0]]] = self.rd(self.ea(o[1]), n, mn in ('lh', 'lb'))
        elif mn in ('sw', 'sh', 'sb'):
            self.wr(self.ea(o[1]), {'sw': 4, 'sh': 2, 'sb': 1}[mn], r[RN[o[0]]])
        elif mn in ('lwl', 'lwr', 'swl', 'swr'):
            a = self.ea(o[1])
            al, k = a & ~3, a & 3
            w = self.rd(al, 4)
            t = RN[o[0]]
            if mn == 'lwr':         # little endian: bytes k..3 into the low end
                sh = 8 * k
                mask = M32 >> sh
                r[t] = (r[t] & ~mask & M32) | (w >> sh)
            elif mn == 'lwl':       # bytes 0..k into the high end
                sh = 8 * (3 - k)
                mask = (M32 << sh) & M32
                r[t] = (r[t] & ~mask & M32) | ((w << sh) & M32)
            elif mn == 'swr':
                sh = 8 * k
                mask = (M32 << sh) & M32
                self.wr(al, 4, (w & ~mask & M32) | ((r[t] << sh) & M32))
            else:
                sh = 8 * (3 - k)
                mask = M32 >> sh
                self.wr(al, 4, (w & ~mask & M32) | (r[t] >> sh))
        elif mn in ('j', 'b'):
            br = (True, int(o[-1], 16), False, None)
        elif mn == 'jal':
            br = (True, int(o[0], 16), False, 31)
        elif mn == 'jr':
            br = (True, r[RN[o[0]]], False, None)
        elif mn == 'jalr':
            br = (True, r[RN[o[-1]]], False, 31 if len(o) == 1 else RN[o[0]])
        elif mn in ('beq', 'bne', 'beql', 'bnel'):
            a, b = r[RN[o[0]]], r[RN[o[1]]]
            t = (a == b) if mn.startswith('beq') else (a != b)
            br = (t, int(o[2], 16), mn.endswith('l'), None)
        elif mn in ('beqz', 'bnez', 'beqzl', 'bnezl', 'blez', 'bgtz', 'bltz', 'bgez',
                    'blezl', 'bgtzl', 'bltzl', 'bgezl'):
            v = s32(r[RN[o[0]]])
            base = mn.rstrip('l') if mn not in ('bltz', 'bgez') else mn
            base = mn[:-1] if mn.endswith('zl') else mn
            t = {'beqz': v == 0, 'bnez': v != 0, 'blez': v <= 0, 'bgtz': v > 0,
                 'bltz': v < 0, 'bgez': v >= 0}[base]
            br = (t, int(o[1], 16), mn.endswith('zl'), None)
        elif mn in ('bal', 'bgezal'):
            br = (True, int(o[-1], 16), False, 31)
        else:
            raise SystemExit('unsupported %s %s at %08x (%s)' % (mn, o, pc, self.func_of(pc)))
        r[0] = 0
        if r[29] < self.minsp:
            self.minsp = r[29]
        if br is None:
            return nxt
        if in_ds:
            raise SystemExit('branch in a delay slot at %08x' % pc)
        taken, target, likely, link = br
        if link is not None:
            r[link] = pc + 8
        if taken or not likely:
            self.step(pc + 4, in_ds=True)
        return target if taken else pc + 8


# -------------------------------------------------------------------- layout
def kstate_offsets(linux):
    """psc_kstate field offsets from include/asm-mips/psc.h (all u32 words,
    psc_xfer_raw 32 B, psc_poll 40 B); psc_mem.k follows the rings and stats."""
    txt = open(linux + '/include/asm-mips/psc.h').read()
    body = txt[txt.index('struct psc_kstate {'):]
    body = body[:body.index('\n};')]
    off, res = 0, {}
    for line in body.splitlines()[1:]:
        line = line.split('/*')[0].strip()
        if not line:
            continue
        m = re.match(r'^(u32|struct psc_xfer_raw|struct psc_poll)\s+(.*);$', line)
        if not m:
            continue
        size = {'u32': 4, 'struct psc_xfer_raw': 32, 'struct psc_poll': 40}[m.group(1)]
        for name in m.group(2).split(','):
            name = name.strip()
            mm = re.match(r'^(\w+)\[(\w+)\]$', name)
            cnt = 1
            if mm:
                name, n = mm.group(1), mm.group(2)
                cnt = {'PSC_NRINGS': 5, 'PSC_NREGS': 16}.get(n) or int(n)
            res[name] = off
            off += size * cnt
    kbase = (4 + F.RING_RECSIZE[F.RING_P] * F.RING_ENTRIES[F.RING_P] + 4 +
             F.RING_RECSIZE[F.RING_POLL] * F.RING_ENTRIES[F.RING_POLL] + 4 +
             F.RING_RECSIZE[F.RING_W] * F.RING_ENTRIES[F.RING_W] + 4 +
             F.RING_RECSIZE[F.RING_S] * F.RING_ENTRIES[F.RING_S] + 4 +
             F.RING_RECSIZE[F.RING_M] * F.RING_ENTRIES[F.RING_M] + 4)
    return kbase, kbase + F.STATS_SIZE, res


def stats_off(name):
    return F.offsets(F.STATS_FIELDS)[name][0]


# -------------------------------------------------------------------- scenarios
TI = 0x89000000          # thread_info of the joypad thread (8 KB aligned)
TASK = 0x89100000        # its task_struct (zeroed)
TI2 = 0x89200000         # an idle task's thread_info
TASK2 = 0x89300000
BUF = 0x89400000         # caller buffers
MAGIC = 0x8FFFFFF0       # return address that ends a thread path


class Bench(object):
    def __init__(self, out, linux, new):
        self.c = CPU(out)
        self.new = new
        c = self.c
        if new:
            self.mem = c.sym['psc_mem']
            kb, self.kofs, self.k = kstate_offsets(linux)
            self.st = self.mem + kb
            c.w32(c.sym['psc_jp_task'], TASK)
        for ti, task in ((TI, TASK), (TI2, TASK2)):
            c.w32(ti + 0, task)
            c.w32(ti + 20, 0)                    # preempt_count
            c.w32(task + 4, 0)
        self.sc_start = c.sym['Syscon_cmd']
        self.sc_end = min(a for a in c.fstart if a > self.sc_start)

    def kaddr(self, name):
        return self.mem + self.kofs + self.k[name]

    def thread(self, entry, args, reply, label):
        c = self.c
        c.dev.reset(reply)
        c.r = [0] * 32
        c.r[28] = TI
        c.r[29] = TI + 8192 - 64
        c.r[31] = MAGIC
        for i, v in enumerate(args):
            c.r[4 + i] = v
        c.status = 0x1000FF01
        sp0 = c.r[29]
        c.trace = []
        c.n = 0
        c.dev.mmio = []
        c.run(entry, {MAGIC})
        return self.split(label, sp0 - c.minsp)

    def split(self, label, depth):
        c = self.c
        io = [i for (i, a, k) in c.dev.mmio if 0xbe240000 <= a < 0xbe250000 or 0xbe580000 <= a < 0xbe590000]
        first, last = (io[0], io[-1]) if io else (None, None)
        byf = {}
        reg = {'before S5': 0, 'S5..S20': 0, 'after S20': 0}
        for idx, pc in enumerate(c.trace, 1):
            f = c.func_of(pc)
            byf[f] = byf.get(f, 0) + 1
            if first is None:
                continue
            if idx < first:
                reg['before S5'] += 1
            elif idx <= last:
                reg['S5..S20'] += 1
            else:
                reg['after S20'] += 1
        return dict(label=label, total=len(c.trace), regions=reg, byfunc=byf, depth=depth,
                    mmio=len(io))

    def tick(self, label, watchdog, interrupted=None, t2d=False):
        """plat_irq_dispatch until its call of irq_enter."""
        c = self.c
        lt = c.sym['psp_local_tick'] if 'psp_local_tick' in c.sym else None
        # localTick and lastTick: the baseline keeps them as statics next to
        # each other (System.map localTick/lastTick); psp.c:375-376
        pid = c.sym['plat_irq_dispatch']
        enter = c.sym['irq_enter']
        stop = [a for a in range(pid, min(x for x in c.fstart if x > pid), 4)
                if c.ins.get(a, ('', []))[0] == 'jal' and int(c.ins[a][1][0], 16) == enter]
        tick_addr, last_addr = self.tick_vars(pid)
        if t2d:     # an uptime past the 3 s durable-age threshold (2.10: > 750 ticks)
            c.w32(tick_addr, 50000 - 1)
        cur = c.r32(tick_addr)
        if watchdog:
            c.w32(last_addr, (cur + 1 - 1250) & M32)
        else:
            c.w32(last_addr, cur)
        if self.new:
            due = self.kaddr('t2d_due')
            c.w32(due, (cur + 1) if t2d else (cur + 100000))
            if t2d:
                c.w32(self.st + stats_off('proc_opens'), 1)
                c.w32(self.st + stats_off('durable_tick'), 0)
        if interrupted is None:
            c.dev.reset((0x00, []))             # the Nop's own 2-word reply
            c.r = [0] * 32
            c.r[28] = TI2
            c.r[29] = TI2 + 8192 - 64 - PT_SIZE
            c.w32(TI2 + 48, c.r[29])            # ti->regs
            c.w32(c.r[29] + 172, 0x88000400)    # its EPC (cpu_idle area)
        else:
            c.r = list(interrupted)
        sp0 = c.r[29]
        c.r[31] = MAGIC
        c.status = 0x1000FF00
        c.cause = 0x00008000
        c.trace = []
        c.n = 0
        c.dev.mmio = []
        c.run(pid, set(stop) | {MAGIC})
        return self.split(label, sp0 - c.minsp)

    def tick_vars(self, pid):
        """The two words plat_irq_dispatch compares (localTick, lastTick):
        the first two lw from lui-based addresses after the Count reset."""
        c = self.c
        seen = []
        regs = {}
        a = pid
        while len(seen) < 2:
            mn, o = c.ins[a]
            if mn == 'lui':
                regs[o[0]] = int(o[1], 0) << 16
            elif mn == 'lw' and re.match(r'^-?\d+\((\w+)\)$', o[1]):
                m = re.match(r'^(-?\d+)\((\w+)\)$', o[1])
                if m.group(2) in regs:
                    seen.append((regs[m.group(2)] + int(m.group(1))) & M32)
            a += 4
        return seen[0], seen[1]

    def straddle(self, label):
        """WDP: run the thread's 0x08 until it waits for the ACK (S14), then
        take the timer interrupt there."""
        c = self.c
        c.dev.reset((0x08, [0xFF, 0xFF, 0xFF, 0xFF, 0x80, 0x80]))
        c.r = [0] * 32
        c.r[28] = TI
        c.r[29] = TI + 8192 - 64
        c.r[31] = MAGIC
        c.r[4], c.r[5], c.r[6] = BUF, BUF + 16, BUF + 32
        c.status = 0x1000FF01
        c.trace = []
        c.n = 0
        pc = c.sym['_pspSysconGetCtrl2']
        while not (self.sc_start <= pc < self.sc_end and c.dev.polls >= 3):
            pc = c.step(pc)
        # SAVE_ALL: pt_regs below the thread's sp, ti->regs, then the handler
        pt = (c.r[29] - PT_SIZE) & ~7
        for i in range(32):
            c.w32(pt + 24 + 4 * i, c.r[i])
        c.w32(pt + 152, c.status)
        c.w32(pt + 168, 0x00008000)
        c.w32(pt + 172, pc)
        c.w32(TI + 48, pt)
        regs = list(c.r)
        regs[29] = pt
        saved = (pc, list(c.r), c.dev.__dict__.copy())
        res = self.tick(label, True, interrupted=regs)
        res['epc'] = pc
        return res


def last_record(b, ring):
    """The newest record of a ring as the compiled code wrote it into
    psc_mem, parsed by the decoder's own parse layer (psc_format.py)."""
    import pscdec_parse as P
    c = b.c
    head = c.r32(b.mem + b.kofs + b.k['head'] + 4 * ring)
    n, size = F.RING_ENTRIES[ring], F.RING_RECSIZE[ring]
    off = 4
    for r in range(ring):
        off += F.RING_ENTRIES[r] * F.RING_RECSIZE[r] + 4
    a = b.mem + off + ((head - 1) % n) * size
    raw = bytes(c.rd(a + i, 1) for i in range(size))
    return head, P.norm_record(ring, raw)


def nwords_table(b):
    """K9 (G1 ruling red team): the receive-loop exit state -> nwords table of
    the compiled code, re-derived by running it: k = 0..8 reply words (the 8th
    0xFFFF or not), and the -3, -4 and -5 exits; each P record as written."""
    c = b.c
    g2 = c.sym['_pspSysconGetCtrl2']
    rows = []
    frame = [0x2209, 0x0800, 0x00FF, 0xFF80, 0x80D0, 0x1111, 0x2222, 0x3333]
    cases = [('%d words' % k, dict(words=frame[:k])) for k in range(0, 8)]
    cases.append(('8 words, 8th 0x3333', dict(words=frame[:8])))
    cases.append(('8 words, 8th 0xFFFF', dict(words=frame[:7] + [0xFFFF])))
    cases.append(('-5: rx[2] 0x80 on every try', dict(words=[0x2203, 0x80F2])))
    cases.append(('-4: no ACK', dict(words=[], never_ack=True)))
    cases.append(('-3: RX never empties', dict(words=[], rx_stuck=True)))
    for name, kw in cases:
        b.thread(g2, [BUF, BUF + 16, BUF + 32], (0x08, []), 'nw')
        c.dev.reset((0x08, []), **kw)
        c.r = [0] * 32
        c.r[28] = TI
        c.r[29] = TI + 8192 - 64
        c.r[31] = MAGIC
        c.r[4], c.r[5], c.r[6] = BUF, BUF + 16, BUF + 32
        c.status = 0x1000FF01
        c.trace = []
        c.n = 0
        c.run(g2, {MAGIC}, maxn=40000000)
        c.trace = []
        h, r = last_record(b, F.RING_P)
        rows.append((name, r['ret'], r['nwords'], r['nw7or8'], r['retries'], r['ack_polls'], r['drain'],
                     r['rx'].hex()))
    return rows


def report(base, new, out):
    L = []
    w = L.append
    w('pathcount.py: baseline %s, under review %s' % (base, new))
    w('Counts are executed instructions (delay slots included); "warm" = second run.')
    w('Device model: RX FIFO empty at entry, ACK after %d polls, reply as given.' % ACK_POLLS)
    w('')
    res = {}
    for tag, out_dir, isnew in (('base', base, False), ('new', new, True)):
        b = Bench(out_dir, '/home/ubuntu/psp/work/linux', isnew)
        g2 = b.c.sym['_pspSysconGetCtrl2']
        txd = b.c.sym['pspSyscon_tx_dword']
        r = {}
        for k in range(2):
            r['P08'] = b.thread(g2, [BUF, BUF + 16, BUF + 32], (0x08, [0xFF, 0xFF, 0xFF, 0xFF, 0x80, 0x80]), 'P08')
            if k == 0:
                r['P08 cold'] = r['P08']
        for k in range(2):
            r['P33'] = b.thread(txd, [1, 0x33, 3], (0x33, []), 'P33')
        for k in range(2):
            r['TICK'] = b.tick('TICK', False)
        for k in range(2):
            r['WD'] = b.tick('WD', True)
            if k == 0:
                r['WD cold'] = r['WD']
        if isnew:
            b.thread(g2, [BUF, BUF + 16, BUF + 32], (0x08, [0xFF, 0xFF, 0xFF, 0xFF, 0x80, 0x80]), 'P08')
            hp, rp = last_record(b, F.RING_P)
            out_keys = b.c.r32(BUF)
        r['WDP'] = b.straddle('WDP')
        if isnew:
            hw, rw = last_record(b, F.RING_W)
            nwtab = nwords_table(b)
            r['T2D'] = b.tick('T2D', False, t2d=True)
            sp_lo = [a for a in b.c.sparse if not (0x89000000 <= a < 0x89500000)]
            vram = (len(sp_lo), min(sp_lo) if sp_lo else 0, max(sp_lo) if sp_lo else 0)
        res[tag] = r
    for p in ('P08', 'P08 cold', 'P33', 'TICK', 'WD', 'WD cold', 'WDP', 'T2D'):
        a, n = res['base'].get(p), res['new'].get(p)
        if n is None:
            continue
        w('== %s' % p)
        if a:
            w('   total     base %5d   new %5d   added %+5d' % (a['total'], n['total'], n['total'] - a['total']))
        else:
            w('   total     new %5d' % n['total'])
        for k in ('before S5', 'S5..S20', 'after S20'):
            if a and n['mmio'] and a['mmio']:
                w('   %-9s base %5d   new %5d   added %+5d' % (k, a['regions'][k], n['regions'][k],
                                                              n['regions'][k] - a['regions'][k]))
        w('   stack     base %5s   new %5d   added %+5s  (bytes below the entry sp%s)'
          % (a['depth'] if a else '-', n['depth'], (n['depth'] - a['depth']) if a else '-',
             '; + PT_SIZE 176 for the exception frame' if p in ('TICK', 'WD', 'WD cold', 'WDP', 'T2D') else ''))
        if 'epc' in n:
            w('   interrupted at %08x (base %08x)' % (n['epc'], a['epc']))
        fs = sorted(n['byfunc'].items(), key=lambda x: -x[1])
        w('   by function (new): ' + ', '.join('%s %d' % kv for kv in fs))
        if a:
            fs = sorted(a['byfunc'].items(), key=lambda x: -x[1])
            w('   by function (base): ' + ', '.join('%s %d' % kv for kv in fs))
        w('')
    w('== Records written by the compiled code in these runs (decoded with pscdec_parse.norm_record)')
    w('   P head %d: cmd 0x%02x ret %d nwords %d nw7or8 %d rx %s ctx 0x%02x ack_polls %d drain %d wn %d'
      % (hp, rp['cmd'], rp['ret'], rp['nwords'], rp['nw7or8'], rp['rx'].hex(), rp['ctx'], rp['ack_polls'],
         rp['drain'], rp['wn']))
    w('   _pspSysconGetCtrl2 output word 0x%08x (rx[3..6], joypad_psp.c reads it)' % out_keys)
    e = rw['ext']
    w('   W head %d (the WDP Nop): origin %d ret %d nwords %d rx %s ext_flags 0x%02x t_busy %d epc %08x '
      'lc_n %d' % (hw, rw['ctx'] & 3, rw['ret'], rw['nwords'], rw['rx'].hex(), e['ext_flags'], e['t_busy'],
                   e['epc'], e['lc_n']))
    w('   T2D: %d bytes written outside the image and the test stacks, %08x..%08x (the panel band of VRAM)'
      % vram)
    w('')
    w('== nwords table of the compiled code (K9): reply as the device gives it -> P record')
    w('   %-30s %5s %6s %6s %7s %9s %6s  rx' % ('case', 'ret', 'nwords', 'nw7or8', 'retries', 'ack_polls', 'drain'))
    for row in nwtab:
        w('   %-30s %5d %6d %6d %7d %9d %6d  %s' % row)
    w('')
    txt = '\n'.join(L) + '\n'
    if out:
        open(out, 'w').write(txt)
    sys.stdout.write(txt)


if __name__ == '__main__':
    report(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
