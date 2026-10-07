"""mips32.py - a small MIPS32 (Allegrex subset) integer interpreter for counting
executed instructions of kernel paths. Stage 3 closure (G2 attempt 2 N1,
verifier advisory 4): written for this re-measurement, independently of
handoff/impl/pathcount.py (no code shared or copied).

Decodes the raw instruction words of vmlinux.bin (little-endian), executes
them with delay slots and branch-likely nullification, and counts:
  n      executed instructions (a nullified delay slot is not counted)
  nnull  nullified delay slots (reported separately)
CP0 Count advances by one per executed instruction (Count at the core clock
and one instruction per cycle are the DESIGN 5.4 assumptions, UNVERIFIED).

Memory: RAM 0x88000000..0x8a000000 (32 MB, kseg0; kseg1/uncached aliases
0xa8../0x48../0x08.. map to the same bytes); VRAM 0x04000000..0x04200000
(aliases 0x44.., 0x84.., 0xa4..) as a separate sink; MMIO through a device
callback. Any other access raises, so a path that touches something the
model does not know stops loudly instead of being miscounted.
"""

import struct

M32 = 0xFFFFFFFF
RAM_BASE, RAM_SIZE = 0x88000000, 0x02000000
VRAM_PHYS, VRAM_SIZE = 0x04000000, 0x00200000


def s32(v):
    v &= M32
    return v - 0x100000000 if v & 0x80000000 else v


def sx16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


class Stop(Exception):
    pass


class Cpu(object):
    def __init__(self, image, device, trace_mmio=None):
        self.ram = bytearray(RAM_SIZE)
        self.ram[0:len(image)] = image
        self.vram = bytearray(VRAM_SIZE)
        self.vram_writes = 0
        self.vram_lo, self.vram_hi = None, None
        self.dev = device
        self.r = [0] * 32
        self.hi = self.lo = 0
        self.cp0 = {}
        self.pc = self.npc = 0
        self.n = 0
        self.nnull = 0
        self.mmio_log = []          # (n at access, 'r'/'w', addr, value)
        self.count_reads = []       # (n, pc) of every mfc0 $9
        self.min_sp = None
        self.ll_bit = 0
        self.watch = {}             # pc -> callback(cpu)
        self.profile = None         # dict pc -> executed count, when enabled
        self.fetch_cache = {}

    # ------------------------------------------------------------ memory
    def _map(self, a):
        a &= M32
        seg = a & 0xF0000000
        low = a & 0x0FFFFFFF
        if seg in (0x80000000, 0xA0000000, 0x40000000, 0x00000000):
            if 0x08000000 <= low < 0x08000000 + RAM_SIZE:
                return 'ram', low - 0x08000000
            if VRAM_PHYS <= low < VRAM_PHYS + VRAM_SIZE:
                return 'vram', low - VRAM_PHYS
        if 0xBC000000 <= a < 0xC0000000:
            return 'mmio', a
        raise Stop('unmapped access %08x at pc %08x' % (a, self.pc))

    def load(self, a, n, signed=False):
        if a % n:
            raise Stop('unaligned load %08x at pc %08x' % (a, self.pc))
        kind, off = self._map(a)
        if kind == 'ram':
            b = self.ram[off:off + n]
        elif kind == 'vram':
            b = self.vram[off:off + n]
        else:
            v = self.dev.read(off, n) & ((1 << (8 * n)) - 1)
            self.mmio_log.append((self.n, 'r', off, v))
            b = v.to_bytes(n, 'little')
        v = int.from_bytes(b, 'little')
        if signed and v & (1 << (8 * n - 1)):
            v -= 1 << (8 * n)
        return v & M32

    def store(self, a, n, v):
        if a % n:
            raise Stop('unaligned store %08x at pc %08x' % (a, self.pc))
        kind, off = self._map(a)
        v &= (1 << (8 * n)) - 1
        if kind == 'ram':
            self.ram[off:off + n] = v.to_bytes(n, 'little')
        elif kind == 'vram':
            self.vram[off:off + n] = v.to_bytes(n, 'little')
            self.vram_writes += 1
            self.vram_lo = off if self.vram_lo is None else min(self.vram_lo, off)
            self.vram_hi = off + n if self.vram_hi is None else max(self.vram_hi, off + n)
        else:
            self.mmio_log.append((self.n, 'w', off, v))
            self.dev.write(off, n, v)

    def w32(self, a, v):
        self.store(a, 4, v)

    def r32(self, a):
        return self.load(a, 4)

    def fetch(self, a):
        w = self.fetch_cache.get(a)
        if w is None:
            kind, off = self._map(a)
            if kind != 'ram':
                raise Stop('fetch outside RAM %08x' % a)
            w = struct.unpack_from('<I', self.ram, off)[0]
            self.fetch_cache[a] = w
        return w

    # ------------------------------------------------------------ run
    def call(self, entry, args=(), sp=None, stop_pc=0x8FFFFFF0, maxn=5000000, stop_at=None):
        """Call `entry` like a jal from stop_pc-8; run until pc == stop_pc
        (the return) or pc in stop_at. Returns the stop pc."""
        for i, a in enumerate(args):
            self.r[4 + i] = a & M32
        if sp is not None:
            self.r[29] = sp
        self.r[31] = stop_pc
        self.pc, self.npc = entry, entry + 4
        stops = set(stop_at or ())
        stops.add(stop_pc)
        n0 = self.n
        while self.pc not in stops:
            if self.n - n0 > maxn:
                raise Stop('no return after %d instructions (pc %08x)' % (maxn, self.pc))
            self.step()
        return self.pc

    def step(self):
        pc = self.pc
        cb = self.watch.get(pc)
        if cb:
            cb(self)
        ins = self.fetch(pc)
        if self.profile is not None:
            self.profile[pc] = self.profile.get(pc, 0) + 1
        nxt, nnxt = self.npc, self.npc + 4
        res = self.exe(ins, pc)
        self.n += 1
        self.cp0[9] = (self.cp0.get(9, 0) + 1) & M32
        sp = self.r[29]
        if self.min_sp is None or sp < self.min_sp:
            self.min_sp = sp
        if res is not None:
            if res == 'null':           # branch-likely not taken: skip the delay slot
                self.nnull += 1
                nxt, nnxt = self.npc + 4, self.npc + 8
            else:
                nnxt = res & M32
        self.pc, self.npc = nxt & M32, nnxt & M32

    # ------------------------------------------------------------ execute
    def exe(self, ins, pc):
        r = self.r
        op = ins >> 26
        rs = (ins >> 21) & 31
        rt = (ins >> 16) & 31
        rd = (ins >> 11) & 31
        sa = (ins >> 6) & 31
        fn = ins & 63
        imm = ins & 0xFFFF
        simm = sx16(imm)
        ret = None

        def setr(i, v):
            if i:
                r[i] = v & M32

        if op == 0:                                     # SPECIAL
            if fn == 0x00:
                setr(rd, r[rt] << sa)                   # sll (nop)
            elif fn == 0x02:
                if rs == 1:                             # rotr
                    v = r[rt]
                    setr(rd, ((v >> sa) | (v << (32 - sa))) if sa else v)
                else:
                    setr(rd, r[rt] >> sa)               # srl
            elif fn == 0x03:
                setr(rd, s32(r[rt]) >> sa)              # sra
            elif fn == 0x04:
                setr(rd, r[rt] << (r[rs] & 31))         # sllv
            elif fn == 0x06:
                s = r[rs] & 31
                if sa == 1:                             # rotrv
                    v = r[rt]
                    setr(rd, ((v >> s) | (v << (32 - s))) if s else v)
                else:
                    setr(rd, r[rt] >> s)                # srlv
            elif fn == 0x07:
                setr(rd, s32(r[rt]) >> (r[rs] & 31))    # srav
            elif fn == 0x08:
                ret = r[rs]                             # jr
            elif fn == 0x09:
                t = r[rs]
                setr(rd, pc + 8)                        # jalr
                ret = t
            elif fn == 0x0A:
                if r[rt] == 0:
                    setr(rd, r[rs])                     # movz
            elif fn == 0x0B:
                if r[rt] != 0:
                    setr(rd, r[rs])                     # movn
            elif fn == 0x0F:
                pass                                    # sync
            elif fn == 0x10:
                setr(rd, self.hi)                       # mfhi
            elif fn == 0x11:
                self.hi = r[rs]                         # mthi
            elif fn == 0x12:
                setr(rd, self.lo)                       # mflo
            elif fn == 0x13:
                self.lo = r[rs]                         # mtlo
            elif fn == 0x16:                            # clz (Allegrex encoding)
                v, c = r[rs], 0
                while c < 32 and not (v & (0x80000000 >> c)):
                    c += 1
                setr(rd, c)
            elif fn == 0x18:
                p = s32(r[rs]) * s32(r[rt])             # mult
                self.lo, self.hi = p & M32, (p >> 32) & M32
            elif fn == 0x19:
                p = r[rs] * r[rt]                       # multu
                self.lo, self.hi = p & M32, (p >> 32) & M32
            elif fn == 0x1A:                            # div
                a, b = s32(r[rs]), s32(r[rt])
                if b:
                    q = abs(a) // abs(b)
                    if (a < 0) != (b < 0):
                        q = -q
                    self.lo, self.hi = q & M32, (a - q * b) & M32
            elif fn == 0x1B:                            # divu
                if r[rt]:
                    self.lo, self.hi = (r[rs] // r[rt]) & M32, (r[rs] % r[rt]) & M32
            elif fn in (0x20, 0x21):
                setr(rd, r[rs] + r[rt])                 # add(u)
            elif fn in (0x22, 0x23):
                setr(rd, r[rs] - r[rt])                 # sub(u)
            elif fn == 0x24:
                setr(rd, r[rs] & r[rt])
            elif fn == 0x25:
                setr(rd, r[rs] | r[rt])
            elif fn == 0x26:
                setr(rd, r[rs] ^ r[rt])
            elif fn == 0x27:
                setr(rd, ~(r[rs] | r[rt]))
            elif fn == 0x2A:
                setr(rd, 1 if s32(r[rs]) < s32(r[rt]) else 0)
            elif fn == 0x2B:
                setr(rd, 1 if r[rs] < r[rt] else 0)
            elif fn == 0x2C:
                setr(rd, r[rs] if s32(r[rs]) > s32(r[rt]) else r[rt])   # max (Allegrex)
            elif fn == 0x2D:
                setr(rd, r[rs] if s32(r[rs]) < s32(r[rt]) else r[rt])   # min (Allegrex)
            elif fn == 0x34:
                if r[rs] == r[rt]:
                    raise Stop('teq trap at %08x' % pc)
            else:
                raise Stop('SPECIAL fn %02x at %08x (%08x)' % (fn, pc, ins))
        elif op == 1:                                   # REGIMM
            v = s32(r[rs])
            tgt = pc + 4 + (simm << 2)
            if rt in (0x00, 0x02, 0x10, 0x12):
                cond = v < 0
            elif rt in (0x01, 0x03, 0x11, 0x13):
                cond = v >= 0
            else:
                raise Stop('REGIMM rt %02x at %08x' % (rt, pc))
            if rt & 0x10:
                setr(31, pc + 8)
            if cond:
                ret = tgt
            elif rt & 0x02:
                ret = 'null'
        elif op in (2, 3):                              # j, jal
            if op == 3:
                setr(31, pc + 8)
            ret = ((pc + 4) & 0xF0000000) | ((ins & 0x03FFFFFF) << 2)
        elif op in (4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
            a, b = r[rs], r[rt]
            k = op & 3
            if k == 0:
                cond = a == b
            elif k == 1:
                cond = a != b
            elif k == 2:
                cond = s32(a) <= 0
            else:
                cond = s32(a) > 0
            if cond:
                ret = pc + 4 + (simm << 2)
            elif op >= 0x14:
                ret = 'null'
        elif op in (8, 9):
            setr(rt, r[rs] + simm)                      # addi(u)
        elif op == 0x0A:
            setr(rt, 1 if s32(r[rs]) < simm else 0)
        elif op == 0x0B:
            setr(rt, 1 if r[rs] < (simm & M32) else 0)
        elif op == 0x0C:
            setr(rt, r[rs] & imm)
        elif op == 0x0D:
            setr(rt, r[rs] | imm)
        elif op == 0x0E:
            setr(rt, r[rs] ^ imm)
        elif op == 0x0F:
            setr(rt, imm << 16)
        elif op == 0x10:                                # COP0
            if rs == 0:
                if rd == 9:
                    self.count_reads.append((self.n, pc))
                setr(rt, self.cp0.get(rd, 0))           # mfc0
            elif rs == 4:
                self.cp0[rd] = r[rt]                    # mtc0
            else:
                raise Stop('COP0 rs %02x at %08x (%08x)' % (rs, pc, ins))
        elif op == 0x1F:                                # SPECIAL3
            if fn == 0x00:                              # ext
                size = rd + 1
                setr(rt, (r[rs] >> sa) & ((1 << size) - 1))
            elif fn == 0x04:                            # ins
                size = rd - sa + 1
                m = ((1 << size) - 1) << sa
                setr(rt, (r[rt] & ~m) | ((r[rs] << sa) & m))
            elif fn == 0x20:
                if sa == 0x10:
                    setr(rd, sx16((r[rt] & 0xFF) | (0xFF00 if r[rt] & 0x80 else 0)))   # seb
                elif sa == 0x18:
                    setr(rd, sx16(r[rt]))               # seh
                elif sa == 0x02:                        # wsbh
                    v = r[rt]
                    setr(rd, ((v & 0x00FF00FF) << 8) | ((v >> 8) & 0x00FF00FF))
                else:
                    raise Stop('BSHFL sa %02x at %08x' % (sa, pc))
            else:
                raise Stop('SPECIAL3 fn %02x at %08x' % (fn, pc))
        elif op in (0x20, 0x21, 0x23, 0x24, 0x25):      # loads
            a = (r[rs] + simm) & M32
            n, sg = {0x20: (1, True), 0x21: (2, True), 0x23: (4, False), 0x24: (1, False),
                     0x25: (2, False)}[op]
            setr(rt, self.load(a, n, sg))
        elif op == 0x30:                                # ll
            a = (r[rs] + simm) & M32
            setr(rt, self.load(a, 4))
            self.ll_bit = 1
        elif op in (0x28, 0x29, 0x2B):                  # stores
            a = (r[rs] + simm) & M32
            self.store(a, {0x28: 1, 0x29: 2, 0x2B: 4}[op], r[rt])
        elif op == 0x38:                                # sc (single CPU, no interruption: succeeds)
            a = (r[rs] + simm) & M32
            self.store(a, 4, r[rt])
            setr(rt, 1)
        elif op in (0x22, 0x26):                        # lwl, lwr
            a = (r[rs] + simm) & M32
            al = a & ~3
            w = self.load(al, 4)
            k = a & 3
            if op == 0x22:
                sh = (3 - k) * 8
                m = (M32 << sh) & M32
                setr(rt, (r[rt] & ~m) | ((w << sh) & m))
            else:
                sh = k * 8
                m = M32 >> sh
                setr(rt, (r[rt] & ~m) | (w >> sh))
        elif op in (0x2A, 0x2E):                        # swl, swr
            a = (r[rs] + simm) & M32
            al = a & ~3
            w = self.load(al, 4)
            k = a & 3
            if op == 0x2A:
                sh = (3 - k) * 8
                m = M32 >> sh
                w = (w & ~m) | (r[rt] >> sh)
            else:
                sh = k * 8
                m = (M32 << sh) & M32
                w = (w & ~m) | ((r[rt] << sh) & m)
            self.store(al, 4, w)
        elif op == 0x2F:
            pass                                        # cache
        else:
            raise Stop('opcode %02x at %08x (%08x)' % (op, pc, ins))
        return ret
