#!/usr/bin/env python3
"""pspboot_emu.py - run the deployed pspboot loader (EBOOT.PBP DATA.PSP) on the
host, from its ELF entry point to the jump into the Linux kernel, against the
files of a deploy folder. Stage 3 item R20 (pspboot loading a +37 KB image).

Written for R20; shares no code with handoff/stage3/measure/mips32.py or
handoff/impl/pathcount.py.

What it models
  * CPU: Allegrex integer subset (MIPS II + movz/movn, ext/ins, seb/seh,
    wsbh, clz/clo, max/min, madd/msub, ll/sc, lwl/lwr/swl/swr), delay slots,
    branch-likely nullification. Any FPU, unknown or unmodelled instruction
    stops the run loudly (Stop), it is never skipped.
  * Memory: main RAM physical 0x08000000..0x0A000000 (32 MB; reached through
    0x08.., 0x48.., 0x88.., 0xA8.. as on the PSP, see include/asm-mips/page.h:44
    PHYS_OFFSET 0x88000000 and DESIGN/IMPLEMENTATION's own interpreters),
    VRAM 0x04000000..0x04200000. Anything else stops the run.
  * The PSP OS only at the import stubs (.sceStub.text): each stub address
    is intercepted and implemented here (file I/O on the deploy folder,
    partition memory, threads, module load, display). The kmodlib export
    0xbc4bec55 is modelled as kmodlib.prx's own code does it (its .text
    0x18..0x74: k1 := 0, call func(arg), restore k1, return the result);
    the call into func runs in this emulator. Unimplemented stubs stop.
  * Nothing else of the Sony OS (interrupts, caches, the Media Engine, the
    Sony kernel's own memory use) is modelled. That is the stated limit.

Audit: from the moment Status.IE is cleared (pspboot 0x8900338) to the jump,
every instruction fetch, load and store is recorded with its physical
address, so the report can state exactly which memory the hand-off touches.

Usage: pspboot_emu.py FOLDER [--expect-bin FILE] [--json OUT]
"""

import gzip
import json
import os
import struct
import sys
import zlib

M32 = 0xFFFFFFFF
RAM_PHYS, RAM_SIZE = 0x08000000, 0x02000000
VRAM_PHYS, VRAM_SIZE = 0x04000000, 0x00200000
SENTINEL_KCALL_RET = 0x0FFFFFF0      # return address for the kcall model


class Stop(Exception):
    pass


def s32(v):
    v &= M32
    return v - 0x100000000 if v & 0x80000000 else v


def sx16(v):
    return v - 0x10000 if v & 0x8000 else v


# ----------------------------------------------------------------- ELF / PBP
def split_pbp(data):
    if data[:4] != b'\x00PBP':
        raise Stop('not a PBP')
    offs = list(struct.unpack('<8I', data[8:40])) + [len(data)]
    names = ['PARAM.SFO', 'ICON0.PNG', 'ICON1.PMF', 'PIC0.PNG', 'PIC1.PNG',
             'SND0.AT3', 'DATA.PSP', 'DATA.PSAR']
    return {n: data[offs[i]:offs[i + 1]] for i, n in enumerate(names)}


def parse_elf(elf):
    if elf[:4] != b'\x7fELF' or elf[4] != 1 or elf[5] != 1:
        raise Stop('DATA.PSP is not a little-endian ELF32')
    e_type, e_machine = struct.unpack('<HH', elf[16:20])
    e_entry, e_phoff, e_shoff = struct.unpack('<III', elf[24:36])
    e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack('<HHHHH', elf[42:52])
    phdrs = []
    for i in range(e_phnum):
        p = struct.unpack('<8I', elf[e_phoff + i * e_phentsize:e_phoff + i * e_phentsize + 32])
        phdrs.append(dict(type=p[0], offset=p[1], vaddr=p[2], paddr=p[3], filesz=p[4], memsz=p[5], flags=p[6]))
    shdrs = []
    for i in range(e_shnum):
        s = struct.unpack('<10I', elf[e_shoff + i * e_shentsize:e_shoff + i * e_shentsize + 40])
        shdrs.append(dict(name=s[0], type=s[1], addr=s[3], offset=s[4], size=s[5]))
    strtab = shdrs[e_shstrndx]
    for s in shdrs:
        o = strtab['offset'] + s['name']
        s['sname'] = elf[o:elf.index(b'\0', o)].decode()
    return dict(type=e_type, machine=e_machine, entry=e_entry, phdrs=phdrs, shdrs=shdrs)


# ----------------------------------------------------------------- CPU
class Audit(object):
    """Aggregates accesses into contiguous ranges per kind ('x' fetch, 'r'
    load, 'w' store) without keeping one entry per access, plus the set of
    PCs that issued loads/stores and every access near a watched window."""

    def __init__(self, watch_lo, watch_hi):
        self.ranges = {'x': [], 'r': [], 'w': []}
        self.count = {'x': 0, 'r': 0, 'w': 0}
        self.pcs = {'r': set(), 'w': set()}
        self.watch_lo, self.watch_hi = watch_lo, watch_hi
        self.watched = []

    def append(self, item):
        kind, pc, p, n = item
        self.count[kind] += 1
        if kind != 'x':
            self.pcs[kind].add(pc)
        if self.watch_lo <= p < self.watch_hi:
            self.watched.append((kind, pc, p, n))
        rs = self.ranges[kind]
        if rs:
            last = rs[-1]
            if last[0] <= p <= last[1]:
                if p + n > last[1]:
                    last[1] = p + n
                return
        for r in rs[-8:]:
            if r[0] <= p and p + n <= r[1]:
                return
        rs.append([p, p + n])


class Cpu(object):
    def __init__(self):
        self.ram = bytearray(RAM_SIZE)
        self.vram = bytearray(VRAM_SIZE)
        self.r = [0] * 32
        self.hi = self.lo = 0
        self.pc = self.npc = 0
        self.n = 0
        self.status = 0x20000001          # IE set: interrupts enabled under the OS
        self.config = (2 << 9) | (3 << 6)  # Allegrex Config cache-size fields (UNVERIFIED value; only sizes the cache loops)
        self.cp0 = {}
        self.hooks = {}
        self.audit = None                 # list while auditing
        self.cache_ops = 0
        self.ic = 1
        self.mtic_count = 0
        self.decoded = {}

    def _buf(self, a, n):
        p = a & 0x1FFFFFFF
        seg = (a & M32) >> 28
        if seg not in (0x0, 0x4, 0x8, 0xA):
            raise Stop('unmapped address %08x at pc %08x' % (a & M32, self.pc))
        if RAM_PHYS <= p and p + n <= RAM_PHYS + RAM_SIZE:
            return self.ram, p - RAM_PHYS, p
        if VRAM_PHYS <= p and p + n <= VRAM_PHYS + VRAM_SIZE:
            return self.vram, p - VRAM_PHYS, p
        raise Stop('unmapped address %08x at pc %08x' % (a & M32, self.pc))

    def load(self, a, n, signed=False):
        a &= M32
        if a % n:
            raise Stop('unaligned load %08x at pc %08x' % (a, self.pc))
        buf, off, p = self._buf(a, n)
        if self.audit is not None:
            self.audit.append(('r', self.pc, p, n))
        v = int.from_bytes(buf[off:off + n], 'little')
        if signed and v >> (8 * n - 1):
            v -= 1 << (8 * n)
        return v & M32

    def store(self, a, n, v):
        a &= M32
        if a % n:
            raise Stop('unaligned store %08x at pc %08x' % (a, self.pc))
        buf, off, p = self._buf(a, n)
        if self.audit is not None:
            self.audit.append(('w', self.pc, p, n))
        buf[off:off + n] = (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'little')

    def read_bytes(self, a, n):
        buf, off, _ = self._buf(a, n)
        return bytes(buf[off:off + n])

    def write_bytes(self, a, data):
        buf, off, _ = self._buf(a, len(data))
        buf[off:off + len(data)] = data

    def cstr(self, a, maxn=4096):
        out = bytearray()
        while len(out) < maxn:
            b = self.read_bytes(a + len(out), 1)[0]
            if b == 0:
                break
            out.append(b)
        return out.decode('latin-1')

    def fetch(self, a):
        if self.audit is not None:
            self.audit.append(('x', a, a & 0x1FFFFFFF, 4))
        return self.load_nolog(a)

    def load_nolog(self, a):
        buf, off, _ = self._buf(a, 4)
        return int.from_bytes(buf[off:off + 4], 'little')

    # run
    def run(self, maxn=400000000):
        r = self.r
        hooks = self.hooks
        while True:
            pc = self.pc
            if pc in hooks:
                if hooks[pc](self):
                    return
                continue
            if self.n >= maxn:
                raise Stop('instruction budget exhausted at pc %08x' % pc)
            ins = self.fetch(pc)
            self.n += 1
            npc = self.npc
            nnpc = (npc + 4) & M32
            op = ins >> 26
            rs = (ins >> 21) & 31
            rt = (ins >> 16) & 31
            rd = (ins >> 11) & 31
            sa = (ins >> 6) & 31
            imm = ins & 0xFFFF
            if op == 0:
                f = ins & 63
                if f == 0x21:                     # addu
                    if rd: r[rd] = (r[rs] + r[rt]) & M32
                elif f == 0x20:                   # add (no overflow trap modelled: stop if it would trap)
                    v = s32(r[rs]) + s32(r[rt])
                    if v > 0x7FFFFFFF or v < -0x80000000:
                        raise Stop('add overflow at %08x' % pc)
                    if rd: r[rd] = v & M32
                elif f == 0x23:                   # subu
                    if rd: r[rd] = (r[rs] - r[rt]) & M32
                elif f == 0x22:
                    v = s32(r[rs]) - s32(r[rt])
                    if v > 0x7FFFFFFF or v < -0x80000000:
                        raise Stop('sub overflow at %08x' % pc)
                    if rd: r[rd] = v & M32
                elif f == 0x25:
                    if rd: r[rd] = r[rs] | r[rt]
                elif f == 0x24:
                    if rd: r[rd] = r[rs] & r[rt]
                elif f == 0x26:
                    if rd: r[rd] = r[rs] ^ r[rt]
                elif f == 0x27:
                    if rd: r[rd] = (~(r[rs] | r[rt])) & M32
                elif f == 0x2A:
                    if rd: r[rd] = 1 if s32(r[rs]) < s32(r[rt]) else 0
                elif f == 0x2B:
                    if rd: r[rd] = 1 if r[rs] < r[rt] else 0
                elif f == 0x00:                   # sll (nop)
                    if rd: r[rd] = (r[rt] << sa) & M32
                elif f == 0x02:
                    if rs == 1:                   # rotr (Allegrex)
                        v = r[rt]
                        if rd: r[rd] = ((v >> sa) | (v << (32 - sa))) & M32 if sa else v
                    else:
                        if rd: r[rd] = r[rt] >> sa
                elif f == 0x03:
                    if rd: r[rd] = (s32(r[rt]) >> sa) & M32
                elif f == 0x04:
                    if rd: r[rd] = (r[rt] << (r[rs] & 31)) & M32
                elif f == 0x06:
                    if sa == 1:
                        s = r[rs] & 31; v = r[rt]
                        if rd: r[rd] = ((v >> s) | (v << (32 - s))) & M32 if s else v
                    else:
                        if rd: r[rd] = r[rt] >> (r[rs] & 31)
                elif f == 0x07:
                    if rd: r[rd] = (s32(r[rt]) >> (r[rs] & 31)) & M32
                elif f == 0x08:                   # jr
                    nnpc = r[rs]
                elif f == 0x09:                   # jalr
                    t = r[rs]
                    if rd: r[rd] = (pc + 8) & M32
                    nnpc = t
                elif f == 0x0A:                   # movz
                    if r[rt] == 0 and rd: r[rd] = r[rs]
                elif f == 0x0B:                   # movn
                    if r[rt] != 0 and rd: r[rd] = r[rs]
                elif f == 0x0C:
                    raise Stop('syscall instruction at %08x (stubs are intercepted, a raw syscall is unexpected)' % pc)
                elif f == 0x0D:
                    raise Stop('break at %08x' % pc)
                elif f == 0x0F:                   # sync
                    pass
                elif f == 0x10:
                    if rd: r[rd] = self.hi
                elif f == 0x12:
                    if rd: r[rd] = self.lo
                elif f == 0x11:
                    self.hi = r[rs]
                elif f == 0x13:
                    self.lo = r[rs]
                elif f == 0x18:                   # mult
                    v = (s32(r[rs]) * s32(r[rt])) & 0xFFFFFFFFFFFFFFFF
                    self.lo, self.hi = v & M32, v >> 32
                elif f == 0x19:
                    v = r[rs] * r[rt]
                    self.lo, self.hi = v & M32, (v >> 32) & M32
                elif f == 0x1A:                   # div
                    a, b = s32(r[rs]), s32(r[rt])
                    if b != 0:
                        q = abs(a) // abs(b)
                        if (a < 0) != (b < 0):
                            q = -q
                        self.lo, self.hi = q & M32, (a - q * b) & M32
                elif f == 0x1B:
                    if r[rt] != 0:
                        self.lo, self.hi = (r[rs] // r[rt]) & M32, (r[rs] % r[rt]) & M32
                elif f in (0x1C, 0x1D, 0x2E, 0x2F):   # madd, maddu, msub, msubu (Allegrex)
                    acc = (self.hi << 32) | self.lo
                    if f in (0x1C, 0x2E):
                        p = s32(r[rs]) * s32(r[rt])
                    else:
                        p = r[rs] * r[rt]
                    acc = (acc + p) if f in (0x1C, 0x1D) else (acc - p)
                    acc &= 0xFFFFFFFFFFFFFFFF
                    self.lo, self.hi = acc & M32, acc >> 32
                elif f == 0x16:                   # clz
                    v = r[rs]; n = 0
                    while n < 32 and not (v & (0x80000000 >> n)):
                        n += 1
                    if rd: r[rd] = n
                elif f == 0x17:                   # clo
                    v = r[rs]; n = 0
                    while n < 32 and (v & (0x80000000 >> n)):
                        n += 1
                    if rd: r[rd] = n
                elif f == 0x2C:                   # max
                    if rd: r[rd] = r[rs] if s32(r[rs]) > s32(r[rt]) else r[rt]
                elif f == 0x2D:                   # min
                    if rd: r[rd] = r[rs] if s32(r[rs]) < s32(r[rt]) else r[rt]
                else:
                    raise Stop('unmodelled SPECIAL %02x at %08x (%08x)' % (f, pc, ins))
            elif op == 0x09:                      # addiu
                if rt: r[rt] = (r[rs] + sx16(imm)) & M32
            elif op == 0x23:                      # lw
                v = self.load((r[rs] + sx16(imm)) & M32, 4)
                if rt: r[rt] = v
            elif op == 0x2B:                      # sw
                self.store((r[rs] + sx16(imm)) & M32, 4, r[rt])
            elif op == 0x0F:                      # lui
                if rt: r[rt] = (imm << 16) & M32
            elif op == 0x0D:
                if rt: r[rt] = r[rs] | imm
            elif op == 0x0C:
                if rt: r[rt] = r[rs] & imm
            elif op == 0x0E:
                if rt: r[rt] = r[rs] ^ imm
            elif op == 0x0A:
                if rt: r[rt] = 1 if s32(r[rs]) < sx16(imm) else 0
            elif op == 0x0B:
                if rt: r[rt] = 1 if r[rs] < (sx16(imm) & M32) else 0
            elif op == 0x08:                      # addi
                v = s32(r[rs]) + sx16(imm)
                if v > 0x7FFFFFFF or v < -0x80000000:
                    raise Stop('addi overflow at %08x' % pc)
                if rt: r[rt] = v & M32
            elif op in (4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
                a, b = r[rs], r[rt]
                k = op & 3
                if k == 0:
                    take = a == b
                elif k == 1:
                    take = a != b
                elif k == 2:
                    take = s32(a) <= 0
                else:
                    take = s32(a) > 0
                if take:
                    nnpc = (pc + 4 + (sx16(imm) << 2)) & M32
                elif op >= 0x14:                  # likely: nullify the delay slot
                    self.pc = (npc + 4) & M32
                    self.npc = (npc + 8) & M32
                    continue
            elif op == 1:                         # REGIMM
                v = s32(r[rs])
                if rt in (0, 2, 0x10, 0x12):
                    take = v < 0
                elif rt in (1, 3, 0x11, 0x13):
                    take = v >= 0
                else:
                    raise Stop('unmodelled REGIMM %02x at %08x' % (rt, pc))
                if rt >= 0x10:
                    r[31] = (pc + 8) & M32
                if take:
                    nnpc = (pc + 4 + (sx16(imm) << 2)) & M32
                elif rt in (2, 3, 0x12, 0x13):
                    self.pc = (npc + 4) & M32
                    self.npc = (npc + 8) & M32
                    continue
            elif op in (2, 3):                    # j, jal
                if op == 3:
                    r[31] = (pc + 8) & M32
                nnpc = ((pc + 4) & 0xF0000000) | ((ins & 0x03FFFFFF) << 2)
            elif op == 0x20:
                v = self.load((r[rs] + sx16(imm)) & M32, 1, True)
                if rt: r[rt] = v
            elif op == 0x24:
                v = self.load((r[rs] + sx16(imm)) & M32, 1)
                if rt: r[rt] = v
            elif op == 0x21:
                v = self.load((r[rs] + sx16(imm)) & M32, 2, True)
                if rt: r[rt] = v
            elif op == 0x25:
                v = self.load((r[rs] + sx16(imm)) & M32, 2)
                if rt: r[rt] = v
            elif op == 0x28:
                self.store((r[rs] + sx16(imm)) & M32, 1, r[rt])
            elif op == 0x29:
                self.store((r[rs] + sx16(imm)) & M32, 2, r[rt])
            elif op in (0x22, 0x26):              # lwl, lwr
                a = (r[rs] + sx16(imm)) & M32
                al = a & ~3
                w = self.load(al, 4)
                sh = a & 3
                if op == 0x22:
                    v = ((w << (8 * (3 - sh))) | (r[rt] & ((1 << (8 * (3 - sh))) - 1))) & M32
                else:
                    keep = (r[rt] & ~(M32 >> (8 * sh))) & M32
                    v = (w >> (8 * sh)) | keep
                if rt: r[rt] = v & M32
            elif op in (0x2A, 0x2E):              # swl, swr
                a = (r[rs] + sx16(imm)) & M32
                al = a & ~3
                w = self.load(al, 4)
                sh = a & 3
                if op == 0x2A:
                    mask = M32 >> (8 * (3 - sh))
                    v = (w & ~mask & M32) | (r[rt] >> (8 * (3 - sh)))
                else:
                    mask = (M32 << (8 * sh)) & M32
                    v = (w & ~mask & M32) | ((r[rt] << (8 * sh)) & M32)
                self.store(al, 4, v)
            elif op == 0x30:                      # ll
                v = self.load((r[rs] + sx16(imm)) & M32, 4)
                if rt: r[rt] = v
            elif op == 0x38:                      # sc (single thread: succeeds)
                self.store((r[rs] + sx16(imm)) & M32, 4, r[rt])
                if rt: r[rt] = 1
            elif op == 0x2F:                      # cache: no cache is modelled; counted
                self.cache_ops += 1
            elif op == 0x10:                      # COP0
                if rs == 0:                       # mfc0
                    if rd == 12:
                        v = self.status
                    elif rd == 16:
                        v = self.config
                    else:
                        v = self.cp0.get(rd, 0)
                    if rt: r[rt] = v
                elif rs == 4:                     # mtc0
                    if rd == 12:
                        old = self.status
                        self.status = r[rt]
                        if (old & 1) and not (r[rt] & 1) and self.on_ie_off:
                            self.on_ie_off(self)
                    else:
                        self.cp0[rd] = r[rt]
                else:
                    raise Stop('unmodelled COP0 %08x at %08x' % (ins, pc))
            elif op == 0x1C:                      # Allegrex mfic/mtic (interrupt controller enable)
                f = ins & 63
                if f == 0x24:                     # mfic rt
                    if rt: r[rt] = self.ic
                elif f == 0x26:                   # mtic rt
                    self.ic = r[rt]
                    self.mtic_count += 1
                else:
                    raise Stop('unmodelled SPECIAL2 %02x at %08x (%08x)' % (f, pc, ins))
            elif op == 0x1F:                      # SPECIAL3
                f = ins & 63
                if f == 0x00:                     # ext rt, rs, pos=sa, size=rd+1
                    size = rd + 1
                    if rt: r[rt] = (r[rs] >> sa) & ((1 << size) - 1)
                elif f == 0x04:                   # ins rt, rs, lsb=sa, msb=rd
                    size = rd - sa + 1
                    mask = ((1 << size) - 1) << sa
                    if rt: r[rt] = (r[rt] & ~mask & M32) | ((r[rs] << sa) & mask)
                elif f == 0x20:                   # BSHFL
                    v = r[rt]
                    if sa == 0x10:                # seb
                        res = v & 0xFF
                        res = (res - 0x100) & M32 if res & 0x80 else res
                    elif sa == 0x18:              # seh
                        res = v & 0xFFFF
                        res = (res - 0x10000) & M32 if res & 0x8000 else res
                    elif sa == 0x02:              # wsbh
                        res = ((v & 0x00FF00FF) << 8) | ((v >> 8) & 0x00FF00FF)
                    elif sa == 0x03:              # wsw (Allegrex)
                        res = int.from_bytes(v.to_bytes(4, 'little'), 'big')
                    elif sa == 0x14:              # bitrev (Allegrex)
                        res = int('{:032b}'.format(v)[::-1], 2)
                    else:
                        raise Stop('unmodelled BSHFL %02x at %08x' % (sa, pc))
                    if rd: r[rd] = res & M32
                else:
                    raise Stop('unmodelled SPECIAL3 %02x at %08x' % (f, pc))
            else:
                raise Stop('unmodelled opcode %02x at %08x (%08x)' % (op, pc, ins))
            self.pc = npc
            self.npc = nnpc

    on_ie_off = None


# ----------------------------------------------------------------- the PSP OS model
class PspModel(object):
    def __init__(self, folder, gamedir='uClinux_TRACE'):
        self.folder = folder
        self.gamedir = gamedir
        self.ms_prefix = 'ms0:/PSP/GAME/%s/' % gamedir
        self.files = {}           # fd -> [host path, pos, data]
        self.next_fd = 3
        self.opens = []           # (guest path, host path or None, result)
        self.reads = []           # (fd, requested, returned)
        self.console = []
        self.blocks = {}
        self.events = []
        self.next_uid = 0x100
        # partition 2 (user) free list; the ELF block is reserved at load time
        self.user_lo, self.user_hi = 0x08800000, 0x0A000000
        self.user_used = []       # (start, end)
        self.kcalls = []
        self.loaded_modules = []
        self.malloc_requests = []
        self.final = None
        self.failed = None

    def host_path(self, guest):
        g = guest
        if g.lower().startswith(self.ms_prefix.lower()):
            g = g[len(self.ms_prefix):]
        elif ':' in g or g.startswith('/'):
            return None
        g = g.lstrip('/')
        if '/' in g or g in ('', '.', '..'):
            return None
        p = os.path.join(self.folder, g)
        return p if os.path.isfile(p) else None

    def alloc_user(self, size, high=False):
        size = (size + 0xFF) & ~0xFF
        spans = sorted(self.user_used)
        if not high:
            cur = self.user_lo
            for s, e in spans:
                if cur + size <= s:
                    break
                cur = max(cur, e)
            start = cur
        else:
            cur = self.user_hi
            for s, e in sorted(spans, key=lambda x: -x[1]):
                if e <= cur - size:
                    if cur - size >= e:
                        break
                cur = min(cur, s)
            start = cur - size
        if start < self.user_lo or start + size > self.user_hi:
            raise Stop('user partition exhausted for %d bytes' % size)
        for s, e in spans:
            if start < e and s < start + size:
                raise Stop('allocator overlap')
        self.user_used.append((start, start + size))
        return start

    # printf transcript (non-intrusive: the real code still runs)
    def fmt(self, cpu, a0_reg=4):
        f = cpu.cstr(cpu.r[a0_reg])
        args = [cpu.r[i] for i in range(a0_reg + 1, 12)]
        out, i, k = [], 0, 0
        while i < len(f):
            c = f[i]
            if c != '%':
                out.append(c); i += 1; continue
            j = i + 1
            while j < len(f) and f[j] in '-0123456789l':
                j += 1
            conv = f[j] if j < len(f) else ''
            spec = f[i:j + 1]
            a = args[k] if k < len(args) else 0
            k += 1
            if conv == 's':
                out.append(cpu.cstr(a))
            elif conv == 'd':
                out.append(('%' + spec[1:-1].replace('l', '') + 'd') % s32(a))
            elif conv in 'xX':
                out.append(('%' + spec[1:-1].replace('l', '') + conv) % a)
            elif conv == 'c':
                out.append(chr(a & 0xFF))
            elif conv == '%':
                out.append('%'); k -= 1
            else:
                out.append(spec)
            i = j + 1
        return ''.join(out)


def build(folder):
    pbp = open(os.path.join(folder, 'EBOOT.PBP'), 'rb').read()
    parts = split_pbp(pbp)
    elf = parts['DATA.PSP']
    info = parse_elf(elf)
    cpu = Cpu()
    os_ = PspModel(folder)
    # load PT_LOAD segments
    for p in info['phdrs']:
        if p['type'] == 1:
            cpu.write_bytes(p['vaddr'], elf[p['offset']:p['offset'] + p['filesz']])
            # bss is zero already
            os_.user_used.append((p['vaddr'] & ~0xFF, (p['vaddr'] + p['memsz'] + 0xFF) & ~0xFF))
    sec = {s['sname']: s for s in info['shdrs']}
    # import stubs
    stub = sec['.lib.stub']
    stubs = {}
    for i in range(stub['size'] // 20):
        o = stub['offset'] + 20 * i
        name, ver, attr, elen, vc, fc, nidtab, stubtab = struct.unpack('<IHHBBHII', elf[o:o + 20])
        lib = cpu.cstr(name)
        for k in range(fc):
            nid = struct.unpack('<I', cpu.read_bytes(nidtab + 4 * k, 4))[0]
            stubs[stubtab + 8 * k] = (lib, nid)
    return cpu, os_, info, stubs, parts


def install_os(cpu, os_, stubs, printf_addr=None):
    R = cpu.r
    A0, A1, A2, A3, T0, T1, T2, T3 = 4, 5, 6, 7, 8, 9, 10, 11
    V0, V1, SP, RA, K1 = 2, 3, 29, 31, 27

    def ret(v, v1=None):
        R[V0] = v & M32
        if v1 is not None:
            R[V1] = v1 & M32
        cpu.pc = R[RA]
        cpu.npc = (R[RA] + 4) & M32

    def ev(name, *a):
        os_.events.append((cpu.n, name) + tuple(a))

    handlers = {}

    def h(lib, nid):
        def deco(fn):
            handlers[(lib, nid)] = fn
            return fn
        return deco

    # --- ThreadMan
    @h('ThreadManForUser', 0x446d8de6)        # sceKernelCreateThread(name, entry, prio, stack, attr, opt)
    def _ct():
        name = cpu.cstr(R[A0])
        stack = R[A3]
        base = os_.alloc_user(stack, high=True)
        uid = os_.next_uid; os_.next_uid += 1
        os_.blocks[uid] = ('thread', name, R[A1], base, stack)
        ev('CreateThread', name, '%08x' % R[A1], stack, '%08x' % base)
        ret(uid)

    @h('ThreadManForUser', 0xf475845d)        # sceKernelStartThread(uid, arglen, argp): switch to it
    def _st():
        kind, name, entry, base, stack = os_.blocks[R[A0]]
        arglen, argp = R[A1], R[A2]
        data = cpu.read_bytes(argp, arglen) if arglen else b''
        top = (base + stack) & ~0xF
        argcopy = (top - ((arglen + 15) & ~15)) & M32
        cpu.write_bytes(argcopy, data)
        ev('StartThread', name, arglen)
        # the creating context (module_start) is abandoned: the new thread is
        # the one that runs the loader to its end
        for i in range(32):
            R[i] = 0
        R[A0] = arglen
        R[A1] = argcopy if arglen else 0
        R[SP] = (argcopy - 64) & M32
        R[RA] = 0x0FFFFFE0                    # thread exit sentinel
        R[28] = cpu.gp
        cpu.pc = entry
        cpu.npc = (entry + 4) & M32

    @h('ThreadManForUser', 0xceadeb47)        # sceKernelDelayThread
    def _dt():
        ev('DelayThread', R[A0]); ret(0)

    @h('ThreadManForUser', 0xaa73c935)        # sceKernelExitThread
    def _et():
        os_.failed = 'ExitThread(%d)' % s32(R[A0]); raise Stop(os_.failed)

    @h('LoadExecForUser', 0x05572a5f)         # sceKernelExitGame
    def _eg():
        os_.failed = 'sceKernelExitGame (loader gave up)'
        raise Stop(os_.failed)

    # --- SysMem
    @h('SysMemUserForUser', 0x237dbd4f)       # sceKernelAllocPartitionMemory(part, name, type, size, addr)
    def _ap():
        part, name, typ, size = R[A0], cpu.cstr(R[A1]), R[A2], R[A3]
        if part != 2:
            raise Stop('AllocPartitionMemory partition %d not modelled' % part)
        base = os_.alloc_user(size, high=(typ == 1))
        uid = os_.next_uid; os_.next_uid += 1
        os_.blocks[uid] = ('mem', name, base, size)
        ev('AllocPartitionMemory', part, name, typ, size, '%08x' % base)
        ret(uid)

    @h('SysMemUserForUser', 0x9d9a5ba1)       # sceKernelGetBlockHeadAddr
    def _gb():
        b = os_.blocks[R[A0]]; ret(b[2])

    @h('SysMemUserForUser', 0xb6d61d02)
    def _fp():
        ev('FreePartitionMemory', R[A0]); ret(0)

    @h('SysMemUserForUser', 0xa291f107)       # sceKernelMaxFreeMemSize
    def _mf():
        ret(0x01400000)

    # --- Stdio
    @h('StdioForUser', 0x172d316e)
    def _so(): ret(1)

    @h('StdioForUser', 0xa6bab2e9)
    def _se(): ret(2)

    @h('StdioForUser', 0xf78ba90a)
    def _si(): ret(0)

    # --- IoFileMgr
    @h('IoFileMgrForUser', 0x109f50bc)        # sceIoOpen(path, flags, mode)
    def _op():
        g = cpu.cstr(R[A0]); flags = R[A1]
        hp = os_.host_path(g)
        if hp is None or (flags & 0x0602):     # only read-only opens of existing files
            os_.opens.append((g, hp, 'ENOENT' if hp is None else 'write refused'))
            ret(0x80010002)
            return
        fd = os_.next_fd; os_.next_fd += 1
        os_.files[fd] = [hp, 0, open(hp, 'rb').read()]
        os_.opens.append((g, hp, fd))
        ret(fd)

    @h('IoFileMgrForUser', 0x6a638d83)        # sceIoRead(fd, buf, n)
    def _rd():
        fd, buf, n = R[A0], R[A1], R[A2]
        if fd not in os_.files:
            ret(0x80020323); return
        f = os_.files[fd]
        data = f[2][f[1]:f[1] + n]
        cpu.write_bytes(buf, data)
        f[1] += len(data)
        os_.reads.append((os.path.basename(f[0]), n, len(data)))
        ret(len(data))

    @h('IoFileMgrForUser', 0x27eb27b8)        # sceIoLseek(fd, off64 in a2:a3, whence t0)
    def _ls():
        fd = R[A0]; off = s32(R[A2]) if R[A3] in (0, M32) else (R[A3] << 32) | R[A2]
        whence = R[T0]
        f = os_.files[fd]
        base = {0: 0, 1: f[1], 2: len(f[2])}[whence]
        f[1] = base + off
        ev('IoLseek', os.path.basename(f[0]), off, whence, f[1])
        ret(f[1] & M32, f[1] >> 32)

    @h('IoFileMgrForUser', 0x810c4bc3)        # sceIoClose
    def _cl():
        os_.files.pop(R[A0], None); ret(0)

    @h('IoFileMgrForUser', 0x42ec03ac)        # sceIoWrite(fd, buf, n): only stdout/stderr
    def _wr():
        fd, buf, n = R[A0], R[A1], R[A2]
        if fd not in (1, 2):
            raise Stop('sceIoWrite to fd %d: the loader is not expected to write files' % fd)
        os_.console.append(('stdout', cpu.read_bytes(buf, n).decode('latin-1')))
        ret(n)

    @h('IoFileMgrForUser', 0xace946e8)        # sceIoGetstat(path, SceIoStat*)
    def _gs():
        g = cpu.cstr(R[A0])
        hp = os_.host_path(g)
        ev('IoGetstat', g, hp is not None)
        if hp is None:
            ret(0x80010002); return
        st = bytearray(88)
        struct.pack_into('<IIQ', st, 0, 0x21FF, 0x27, os.path.getsize(hp))   # FIO_S_IFREG|0777, file attr
        cpu.write_bytes(R[A1], bytes(st))
        ret(0)

    @h('IoFileMgrForUser', 0xb29ddf9c)        # sceIoDopen(path): only the game folder itself
    def _do():
        g = cpu.cstr(R[A0])
        ok = g.rstrip('/').lower() == os_.ms_prefix.rstrip('/').lower()
        ev('IoDopen', g, ok)
        ret(0x3000 if ok else 0x80010002)

    @h('IoFileMgrForUser', 0xeb092469)        # sceIoDclose
    def _dc():
        ret(0)

    @h('IoFileMgrForUser', 0x55f4717d)        # sceIoChdir
    def _cd():
        ev('IoChdir', cpu.cstr(R[A0])); ret(0)

    # --- ModuleMgr
    @h('ModuleMgrForUser', 0x977de386)        # sceKernelLoadModule(path, flags, opt)
    def _lm():
        g = cpu.cstr(R[A0])
        hp = os_.host_path(g)
        opt = R[A2]
        part = None
        if opt:
            # SceKernelLMOption {size, mpidtext, mpiddata, flags, position, access, creserved[2]}
            part = cpu.load(opt + 4, 4)
        os_.loaded_modules.append((g, hp, part))
        ev('LoadModule', g, hp, part)
        if hp is None:
            ret(0x8002012e); return
        ret(0x2000)

    @h('ModuleMgrForUser', 0x50f0c1ec)        # sceKernelStartModule
    def _sm():
        ev('StartModule', R[A0]); ret(0)

    @h('ModuleMgrForUser', 0xd1ff982a)        # sceKernelStopModule
    def _stm():
        ev('StopModule', R[A0]); ret(0)

    @h('ModuleMgrForUser', 0x2e0911aa)        # sceKernelUnloadModule
    def _um():
        ev('UnloadModule', R[A0]); ret(0)

    # --- display / GE (pspDebugScreen)
    @h('sceDisplay', 0x0e20f177)
    def _dm(): ret(0)

    @h('sceDisplay', 0x289d82fe)
    def _df(): ret(0)

    @h('sceGe_user', 0xe47e40e4)              # sceGeEdramGetAddr
    def _ge(): ret(0x04000000)

    # --- kmodlib (kmodlib.prx .text 0x18..0x74 and 0x10)
    @h('kmodlib', 0xbc4bec55)                 # kcall(func, arg): k1=0; v=func(arg); k1=old; return v
    def _kc():
        func, arg = R[A0], R[A1]
        os_.kcalls.append(('%08x' % func, '%08x' % arg, cpu.n))
        ev('kmodlib.kcall', '%08x' % func, '%08x' % arg)
        if func == 0:
            ret(0); return
        cpu.kcall_saved = (R[RA], R[K1], R[16], R[17], R[18], R[SP])
        R[K1] = 0
        R[A0] = arg
        R[RA] = SENTINEL_KCALL_RET
        cpu.pc = func
        cpu.npc = (func + 4) & M32

    @h('kmodlib', 0x282407db)
    def _ki(): ret(0)

    def kcall_return(c):
        ra, k1, s0, s1, s2, sp = c.kcall_saved
        v = R[V0]
        R[K1] = k1; R[16], R[17], R[18], R[SP] = s0, s1, s2, sp
        R[RA] = ra
        ev('kcall returned', s32(v))
        ret(v)
        return False

    cpu.hooks[SENTINEL_KCALL_RET] = kcall_return

    def thread_exit(c):
        os_.failed = 'user_main returned %d' % s32(R[V0])
        raise Stop(os_.failed)

    cpu.hooks[0x0FFFFFE0] = thread_exit

    for addr, (lib, nid) in stubs.items():
        fn = handlers.get((lib, nid))

        def make(fn=fn, lib=lib, nid=nid, addr=addr):
            def hook(c):
                if fn is None:
                    raise Stop('unmodelled import %s 0x%08x called (stub %08x, ra %08x)' % (lib, nid, addr, R[RA]))
                fn()
                return False
            return hook
        cpu.hooks[addr] = make()

    if printf_addr:
        orig = cpu.hooks.get(printf_addr)

        def pf(c):
            os_.console.append(('printf', os_.fmt(c)))
            # run the real code: temporarily remove the hook for one step
            del c.hooks[printf_addr]
            save = c.pc
            # execute one instruction, then restore the hook
            c.hooks[save + 4] = restore
            return False

        def restore(c):
            del c.hooks[printf_addr + 4]
            c.hooks[printf_addr] = pf
            return False
        cpu.hooks[printf_addr] = pf


def run_folder(folder, expect_bin=None, kernel_jump=0x88000000, printf_addr=0x0890b21c, maxn=900000000,
               gamedir=None, truncate_at=None):
    cpu, os_, info, stubs, parts = build(folder)
    if gamedir:
        os_.gamedir = gamedir
        os_.ms_prefix = 'ms0:/PSP/GAME/%s/' % gamedir
    sec = {s['sname']: s for s in info['shdrs']}
    # gp from .reginfo (ri_gp_value at offset 20)
    ri = sec['.reginfo']
    elf = parts['DATA.PSP']
    cpu.gp = struct.unpack('<I', elf[ri['offset'] + 20:ri['offset'] + 24])[0]
    install_os(cpu, os_, stubs, printf_addr)
    result = dict(folder=folder)
    ie_off = {}

    def on_ie_off(c):
        ie_off['n'] = c.n
        ie_off['pc'] = c.pc
        ie_off['sp'] = c.r[29]
        sp_phys = c.r[29] & 0x1FFFFFFF
        c.audit = Audit(sp_phys - 0x1000, sp_phys + 0x1000)
    cpu.on_ie_off = on_ie_off

    def at_kernel(c):
        os_.final = dict(n=c.n, a0=c.r[4], a1=c.r[5], a2=c.r[6], a3=c.r[7], sp=c.r[29], ra=c.r[31],
                         status=c.status)
        return True
    cpu.hooks[kernel_jump] = at_kernel

    # module_start(args, argp): argp = the EBOOT path, as the PSP passes it
    argv0 = (os_.ms_prefix + 'EBOOT.PBP').encode() + b'\0'
    tmp = 0x09FF0000
    cpu.write_bytes(tmp, argv0)
    cpu.r[4] = len(argv0)
    cpu.r[5] = tmp
    cpu.r[29] = 0x09FFF000
    cpu.r[31] = 0x0FFFFFD0
    cpu.r[28] = cpu.gp
    os_.user_used.append((0x09FF0000, 0x0A000000))   # module_start's own stack/args (model)
    cpu.hooks[0x0FFFFFD0] = lambda c: (_ for _ in ()).throw(Stop('module_start returned without starting user_main'))
    cpu.pc = info['entry']
    cpu.npc = (info['entry'] + 4) & M32
    try:
        cpu.run(maxn)
        result['outcome'] = 'JUMPED_TO_KERNEL'
    except Stop as e:
        result['outcome'] = 'STOPPED'
        result['stop'] = str(e)
    result['instructions'] = cpu.n
    result['console'] = [t for _, t in os_.console]
    result['opens'] = os_.opens
    result['reads_summary'] = summarize_reads(os_.reads)
    result['events'] = [list(map(str, e)) for e in os_.events]
    result['kcalls'] = os_.kcalls
    result['modules'] = os_.loaded_modules
    result['cache_ops'] = cpu.cache_ops
    result['mtic_writes'] = cpu.mtic_count
    result['eboot_sha256'] = __import__('hashlib').sha256(open(os.path.join(folder, 'EBOOT.PBP'), 'rb').read()).hexdigest()
    result['kernel_file_sha256'] = __import__('hashlib').sha256(open(os.path.join(folder, 'vmlinux-0.22.bin'), 'rb').read()).hexdigest()
    result['final'] = os_.final
    if os_.final is None:
        return result, cpu, None
    # what the loader reported as loaded
    loaded = None
    for line in result['console']:
        if line.endswith(' bytes loaded\n'):
            loaded = int(line.split()[0])
    result['loaded_reported'] = loaded
    result['ie_off'] = dict(n=ie_off.get('n'), pc='%08x' % ie_off.get('pc', 0), sp='%08x' % ie_off.get('sp', 0))
    result['audit'] = analyse_audit(cpu.audit, loaded) if cpu.audit else None
    # memory at the jump
    if expect_bin and truncate_at:
        exp = open(expect_bin, 'rb').read()
        T = truncate_at
        mem = cpu.read_bytes(0x88000000, len(exp) + 64)
        result['memcheck'] = dict(
            expect_file=expect_bin, file_len=len(exp), truncate_at=T, loaded_len=loaded,
            prefix_identical_outside_cmdline=bool(mem[:8] == exp[:8] and mem[264:T] == exp[264:T]),
            beyond_cut_untouched=bool(mem[T:len(exp) + 64] == b'\0' * (len(exp) + 64 - T)),
            file_beyond_cut_nonzero=bool(exp[T:] != b'\0' * (len(exp) - T)),
            cmdline_at_0x88000008=mem[8:264].split(b'\0')[0].decode('latin-1'))
    elif expect_bin:
        exp = open(expect_bin, 'rb').read()
        mem = cpu.read_bytes(0x88000000, max(len(exp), loaded or 0) + 64)
        cmd_area = mem[8:8 + 256]
        same_outside_cmd = (mem[:8] == exp[:8] and mem[264:len(exp)] == exp[264:])
        result['memcheck'] = dict(
            expect_file=expect_bin, expect_len=len(exp),
            loaded_len=loaded,
            identical_outside_cmdline=bool(same_outside_cmd),
            image_bytes_8_263_all_zero=bool(exp[8:264] == b'\0' * 256),
            cmdline_at_0x88000008=cmd_area.split(b'\0')[0].decode('latin-1'),
            bytes_after_image_untouched=bool(mem[len(exp):len(exp) + 64] == b'\0' * 64),
            first_mismatch=first_mismatch(mem[:len(exp)], exp, skip=(8, 264)))
    return result, cpu, os_


def first_mismatch(a, b, skip=(0, 0)):
    n = min(len(a), len(b))
    for i in range(n):
        if skip[0] <= i < skip[1]:
            continue
        if a[i] != b[i]:
            return i
    return None if len(a) == len(b) or n == len(b) else n


def summarize_reads(reads):
    out = {}
    for name, req, got in reads:
        d = out.setdefault(name, dict(calls=0, requested_sizes={}, bytes=0))
        d['calls'] += 1
        d['requested_sizes'][str(req)] = d['requested_sizes'].get(str(req), 0) + 1
        d['bytes'] += got
    return out


def merge(ranges):
    ranges = sorted(ranges)
    out = []
    for s, e in ranges:
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def analyse_audit(au, loaded):
    """Classify every access made after Status.IE was cleared."""
    fm = merge(au.ranges['x'])
    rm = merge(au.ranges['r'])
    wm = merge(au.ranges['w'])
    fmt = lambda rs: ['%08x-%08x (%d B)' % (s, e, e - s) for s, e in rs]
    dest_lo, dest_hi = 0x08000000, 0x08000000 + (loaded or 0)
    inside = lambda rs: fmt([(s, e) for s, e in rs if s < dest_hi and dest_lo < e])
    return dict(counts=au.count,
                fetch_ranges=fmt(fm), read_ranges=fmt(rm), write_ranges=fmt(wm),
                load_pcs=sorted('%08x' % p for p in au.pcs['r']),
                store_pcs=sorted('%08x' % p for p in au.pcs['w']),
                stack_window=('%08x-%08x' % (au.watch_lo, au.watch_hi)),
                stack_window_accesses=[(k, '%08x' % pc, '%08x' % p, n) for k, pc, p, n in au.watched],
                reads_inside_destination=inside(rm),
                fetches_inside_destination=inside(fm),
                writes_inside_destination=inside(wm))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--expect-bin')
    ap.add_argument('--json')
    ap.add_argument('--gamedir', help='folder name under ms0:/PSP/GAME (default: the folder basename)')
    ap.add_argument('--truncate-at', type=int, help='expect the loader to stop at this many bytes')
    a = ap.parse_args()
    gd = a.gamedir or os.path.basename(os.path.normpath(a.folder))
    res, cpu, os_ = run_folder(a.folder, a.expect_bin, gamedir=gd, truncate_at=a.truncate_at)
    res['gamedir'] = gd
    txt = json.dumps(res, indent=1, default=str)
    if a.json:
        open(a.json, 'w').write(txt + '\n')
    print(txt)
    ok = res['outcome'] == 'JUMPED_TO_KERNEL'
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
