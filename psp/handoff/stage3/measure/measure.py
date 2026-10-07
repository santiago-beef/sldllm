#!/usr/bin/env python3
"""measure.py - Stage 3 closure re-measurement of the instrumentation's cost
outside the S5..S20 window (G2 attempt 2 N1; verifier advisory 4; G1-ruling
review A-1, A-2; red team K5, K6, K8 constants).

Runs the machine code of two kernels with mips32.py (written for this
closure, independent of handoff/impl/pathcount.py: no code shared):
  BASE = work/out/20260927T204657Z   (the unmodified tree, built by build.sh)
  NEW  = work/out/20261006T052947Z   (the RELEASE build; its vmlinux-0.22.bin
         is sha256 4f9b69dc..., and gunzip of it is this vmlinux.bin)
Both images are only read.

Device model (syscon SPI 0xbe58xxxx / GPIO 0xbe24xxxx): RX FIFO empty at
entry; the ACK (0xbe240020 b4) after ACK_POLLS polls once GPIO3 is set;
then the reply words in the FIFO; a read of an empty FIFO returns 0xFFFF.
Any other MMIO address returns 0 and is listed. Counting assumptions
(DESIGN 5.4, UNVERIFIED): 1 instruction per cycle, CP0 Count at the core
clock 220,912,896 Hz, no cache or MMIO latency modelled.

Usage: python3 measure.py [--work /home/ubuntu/psp/work] > measure-output.json
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mips32 import Cpu, M32   # noqa: E402

HZ_COUNT = 220912896
US = HZ_COUNT / 1e6                 # Counts (instructions at 1 IPC) per microsecond
ACK_POLLS = 20

# fake kernel objects in RAM above the image (thread_info 8 KB aligned)
T_TI, T_TASK = 0x89E00000, 0x89E10000     # the joypad thread
I_TI, I_TASK = 0x89E04000, 0x89E12000     # another task (thread idle)
THREAD_SIZE, TI_SIZE = 8192, 52           # asm-offsets.h _THREAD_SIZE; thread_info = TI_REGS 48 + 4
TI_TASK, TI_REGS = 0, 48
ST_CU0, ST_IE, ST_IM7, CAUSE_IP7 = 0x10000000, 0x1, 0x8000, 0x8000
CONFIG = (2 << 9) | (3 << 6)              # I-cache 16 KB, D-cache 16 KB for pspClear*cache (UNVERIFIED)

# psc_mem layout: include/asm-mips/psc.h struct psc_mem, ring sizes include/linux/psc_format.h:86-90
ST_OFF = 4 + 4096 * 80 + 4 + 2048 * 40 + 4 + 256 * 288 + 4 + 4096 * 40 + 4 + 64 * 80 + 4
K_OFF = ST_OFF + 768
K_FIELDS = (['head%d' % i for i in range(5)] +
            ['t_busy_p', 't_cmd', 't_entry_tick', 't_entry_c', 't_cmd_id', 't_busy_m', 'wd_ctx', 'c_pre_cur'] +
            ['xfer%d' % i for i in range(24)] +
            ['lc_seq', 'lc_tick', 'lc_c_pre', 'lc_cmd_id', 'lc_epc', 'lc_cause', 'lc_ra', 'lc_sp'] +
            ['lc_r%d' % i for i in range(16)] + ['lc_n', 'lc_wdtick', 'lc_nest_id'] +
            ['led_cmd_id', 'led_cmd_or', 'led_cmd_pid', 'seg_led_ops', 'seg_set_or', 'seg_clr_or', 'seg_flags',
             's_tick_on', 's_c_on', 's_p_head', 's_busy_in'] +
            ['wk_%d' % i for i in range(14)] + ['pre_%d' % i for i in range(13)] + ['poll_%d' % i for i in range(10)] +
            ['poll_prev_tick', 'poll_started', 'poll_nivcsw0', 'poll_p_head0', 'poll_wk_count', 'last_p08',
             't2d_due', 'panel_cmd_id', 'panel_test_secs', 'panel_test_seen', 'panel_test_until', 'guards_armed',
             'build_id'])
STATS_WORD = {'last_reader_tick': 5, 'proc_opens': 23, 'p_rec_cost_last': 24, 'p_rec_cost_max': 25,
              'w_rec_cost_max': 26, 'wd_calls': 27, 'durable_tick': 112, 'panel_paints': 119,
              'panel_cost_max': 123, 'panel_cost_last': 148, 'panel_state': 149}


def reply_words(cmd, data):
    """[0x22, len, cmd, data..., checksum] as 16-bit words (syscon.c:201-245)."""
    b = [0x22, 3 + len(data), cmd] + list(data)
    b.append((sum(b[:b[1]]) & 0xFF) ^ 0xFF)
    if len(b) % 2:
        b.append(0xFF)
    return [(b[i] << 8) | b[i + 1] for i in range(0, len(b), 2)]


R08 = reply_words(0x08, [0xFF, 0xFF, 0xFF, 0xFF, 0x80, 0x80])     # 5 words
R33 = reply_words(0x33, [])                                         # 2 words
RNOP = reply_words(0x00, [])                                        # 2 words


class Syscon(object):
    def __init__(self):
        self.reset(RNOP)

    def reset(self, words, ack_polls=ACK_POLLS):
        self.words, self.ack_polls = list(words), ack_polls
        self.fifo, self.g3, self.polls, self.ack = [], 0, 0, 0
        self.other = []

    def read(self, a, n):
        if a == 0xbe240004:
            return 0
        if a == 0xbe58000c:
            return 4 if self.fifo else 0
        if a == 0xbe580008:
            return self.fifo.pop(0) if self.fifo else 0xFFFF
        if a == 0xbe240020:
            if self.g3 and not self.ack:
                self.polls += 1
                if self.polls > self.ack_polls:
                    self.ack = 1
                    self.fifo = list(self.words)
            return 0x10 if self.ack else 0
        self.other.append('r %08x' % a)
        return 0

    def write(self, a, n, v):
        if a == 0xbe240008 and v & 8:
            self.g3, self.polls, self.ack = 1, 0, 0
        elif a == 0xbe24000c and v & 8:
            self.g3 = 0
        elif a in (0xbe580008, 0xbe580004, 0xbe580020, 0xbe240024):
            pass
        else:
            self.other.append('w %08x %x' % (a, v))


def sysmap(path):
    d = {}
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 3:
                d.setdefault(p[2], int(p[0], 16))
    return d


def asm_offsets(path):
    d = {}
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 3 and p[0] == '#define':
                try:
                    d[p[1]] = int(p[2], 0)
                except ValueError:
                    pass
    return d


class Kernel(object):
    def __init__(self, outdir, new, pto):
        self.outdir, self.new, self.pto = outdir, new, pto
        with open(os.path.join(outdir, 'vmlinux.bin'), 'rb') as f:
            self.image = f.read()
        self.sha_bin = hashlib.sha256(self.image).hexdigest()
        self.sym = sysmap(os.path.join(outdir, 'System.map'))
        self.dev = Syscon()
        self.cpu = None

    def fresh(self):
        c = Cpu(self.image, self.dev)
        c.cp0[16] = CONFIG
        for ti, task in ((T_TI, T_TASK), (I_TI, I_TASK)):
            c.w32(ti + TI_TASK, task)
            c.w32(task + 4, ti)         # task_struct.stack (2.6.22) = its thread_info
        if self.new:
            c.w32(self.sym['psc_jp_task'], T_TASK)
        self.cpu = c
        return c

    def k(self, field):
        return self.sym['psc_mem'] + K_OFF + 4 * K_FIELDS.index(field)

    def st(self, field):
        return self.sym['psc_mem'] + ST_OFF + 4 * STATS_WORD[field]

    def tick_addrs(self):
        """(localTick, lastTick). Baseline: the statics plat_irq_dispatch reads
        (lw 10292(0x881b) and 10288(0x881b) at 880ce858/880ce860)."""
        if self.new:
            return self.sym['psp_local_tick'], self.sym['psp_local_tick'] + 4
        return 0x881b2834, 0x881b2830


def by_function(K, prof):
    """Executed instructions per function (System.map text symbols)."""
    import bisect
    if not hasattr(K, '_fsyms'):
        K._fsyms = sorted((a, n) for n, a in K.sym.items() if 0x88000000 <= a < 0x88160000)
        K._faddr = [a for a, n in K._fsyms]
    out = {}
    for pc, n in prof.items():
        i = bisect.bisect_right(K._faddr, pc) - 1
        name = K._fsyms[i][1] if i >= 0 else '?'
        out[name] = out.get(name, 0) + n
    return dict(sorted(out.items(), key=lambda x: -x[1]))


def window_marks(log):
    """Indices into an MMIO log: S5 (first 0xbe240004 load), S13 (first
    0xbe240008 = 8 store), S20 (the 0xbe24000c store after the 0xbe580004 = 4
    store that ends the receive loop)."""
    s5 = next(i for i, x in enumerate(log) if x[2] == 0xbe240004)
    s13 = next(i for i, x in enumerate(log) if x[1] == 'w' and x[2] == 0xbe240008 and x[3] & 8)
    s20 = None
    for i in range(len(log) - 1):
        if log[i][1] == 'w' and log[i][2] == 0xbe580004 and log[i][3] == 4 and \
                log[i + 1][1] == 'w' and log[i + 1][2] == 0xbe24000c:
            s20 = i + 1
    return s5, s13, s20


def run_thread(K, entry, args, words, ack_polls=ACK_POLLS, reps=2):
    """Thread-context call (origin P in the new build), `reps` times on one
    machine state; every run's counts are returned (index 0 = first of boot)."""
    c = K.fresh()
    runs = []
    for rep in range(reps):
        K.dev.reset(words, ack_polls)
        c.r[28] = T_TI
        c.cp0[12] = ST_CU0 | ST_IE | 0xFF00
        sp = T_TI + THREAD_SIZE - 32 - 512
        argv = [x(sp) if callable(x) else x for x in args]
        c.min_sp, c.mmio_log, c.count_reads = None, [], []
        c.profile = {}
        n0 = c.n
        c.call(entry, argv, sp=sp)
        n1 = c.n
        log = c.mmio_log
        i5, i13, i20 = window_marks(log)
        s5, s13, s20 = log[i5][0], log[i13][0], log[i20][0]
        cr = [x[0] for x in c.count_reads]
        o = dict(total=n1 - n0, before_s5=s5 - n0, window_s5_s20=s20 - s5 + 1, after_s20=n1 - s20 - 1,
                 entry_to_s13=s13 - n0, mmio_s5_to_s13_incl=i13 - i5 + 1, mmio_s5_to_s20_incl=i20 - i5 + 1,
                 mmio_total=len(log), stack_bytes=sp - c.min_sp, ret=c.r[2] if c.r[2] < 0x80000000 else c.r[2] - (1 << 32),
                 nnull=c.nnull)
        if K.new and len(cr) >= 3:
            o.update(entry_to_cin=cr[0] - n0, cin_to_cout=cr[1] - cr[0], cout_to_t2=cr[2] - cr[1],
                     t2_to_ret=n1 - cr[2], s20_to_cout=cr[1] - s20 - 1, cin_to_s5=s5 - cr[0], cin_to_s13=s13 - cr[0],
                     mmio_cin_to_cout=sum(1 for x in log if cr[0] <= x[0] < cr[1]))
        if K.dev.other:
            o['other_mmio'] = K.dev.other[:8]
        o['by_function'] = by_function(K, c.profile)
        if K.new:
            rec = psc_last_record(K, c, 0)
            o['record'] = rec
        runs.append(o)
    return runs


def psc_last_record(K, c, ring):
    """The newest P record (ring 0) as the kernel wrote it: SC fields 1.2."""
    import struct
    head = c.r32(K.k('head0'))
    a = K.sym['psc_mem'] + 4 + ((head - 1) & 4095) * 80
    b = bytes(c.ram[a - 0x88000000:a - 0x88000000 + 80])
    f = struct.unpack('<IIIIHBBhBBIHHHHHBBHHBBBB16sIHBBIHH', b)
    return dict(seq=f[0], c_in=f[2], c_out=f[3], dtick=f[4], cmd=f[5], ret=f[7], nwords=f[8], retries=f[9],
                ack_polls=f[10], drain=f[11], wn=f[17], preempt_delta=f[23], lc_n=f[27])


def run_tick(K, kind, reps=2, words=None):
    """One timer interrupt from plat_irq_dispatch's entry to its call of
    irq_enter (every instruction the instrumentation adds to a tick runs
    there). kind: TICK (ordinary, thread idle), WD (watchdog tick, thread
    idle), WDP (watchdog tick interrupting the joypad thread at S14 of its
    0x08: T2a runs, t_busy set), T2D (tick 125 mod 250 with the stall panel
    painting; new build only). The interrupted context is a kernel-mode frame
    (Status.CU0 = 1) on the interrupted task's stack."""
    c = K.fresh()
    pto = K.pto
    lt, last = K.tick_addrs()
    ti, task = (T_TI, T_TASK) if kind == 'WDP' else (I_TI, I_TASK)
    runs = []
    for rep in range(reps):
        cyc = 7 + rep
        cur = 1250 * cyc + {'TICK': 37, 'WD': 0, 'WDP': 0, 'T2D': 125}[kind]
        c.w32(lt, cur - 1)
        c.w32(last, cur - 1250 if kind in ('WD', 'WDP') else 1250 * cyc)
        isp = ti + THREAD_SIZE - 32 - 1024
        regs = isp - pto['PT_SIZE']
        c.w32(ti + TI_REGS, regs)
        epc = K.s14_epc if kind == 'WDP' else K.sym['schedule']
        c.w32(regs + pto['PT_R29'], isp)
        c.w32(regs + pto['PT_EPC'], epc)
        c.w32(regs + pto['PT_STATUS'], ST_CU0 | ST_IE | 0xFF00)
        c.w32(regs + pto['PT_CAUSE'], CAUSE_IP7)
        if K.new:
            c.w32(K.k('t2d_due'), cur + 100 if kind != 'T2D' else cur)
            if kind == 'WDP':
                c.w32(K.k('t_busy_p'), 1)
                c.w32(K.k('t_cmd_id'), 5 + rep)
                c.w32(K.k('t_cmd'), 0x08)
            else:
                c.w32(K.k('t_busy_p'), 0)
            if kind == 'T2D':
                c.w32(K.st('proc_opens'), 1)
                c.w32(K.st('durable_tick'), 0)
                c.w32(K.st('last_reader_tick'), cur)
        K.dev.reset(words or (R08 if kind == 'WDP' else RNOP))
        c.r[28] = ti
        c.cp0[12] = ST_CU0 | ST_IM7
        c.cp0[13] = CAUSE_IP7
        c.cp0[9] = 883651
        c.cp0[11] = 883651
        c.min_sp, c.mmio_log, c.count_reads = None, [], []
        c.vram_writes, c.vram_lo, c.vram_hi = 0, None, None
        c.profile = {}
        n0 = c.n
        stop = c.call(K.sym['plat_irq_dispatch'], (), sp=regs, stop_at=[K.sym['irq_enter']])
        assert stop == K.sym['irq_enter'], hex(stop)
        o = dict(total=c.n - n0, stack_below_ptregs=regs - c.min_sp, mmio=len(c.mmio_log), nnull=c.nnull)
        if c.vram_writes:
            o.update(vram_stores=c.vram_writes, vram_bytes='%08x..%08x' % (0x04000000 + c.vram_lo,
                                                                         0x04000000 + c.vram_hi))
        if c.mmio_log:
            log = c.mmio_log
            i5, i13, i20 = window_marks(log)
            o.update(before_nop_s5=log[i5][0] - n0, nop_window=log[i20][0] - log[i5][0] + 1,
                     after_nop_s20=c.n - log[i20][0] - 1)
        if K.new and kind == 'WDP':
            o['lc_epc'] = '%08x' % c.r32(K.k('lc_epc'))
            o['lc_n'] = c.r32(K.k('lc_n'))
        if K.new and kind in ('WD', 'WDP'):
            o['w_rec_cost_max'] = c.r32(K.st('w_rec_cost_max'))
        if K.new and kind == 'T2D':
            o['panel_cost_last'] = c.r32(K.st('panel_cost_last'))
            o['panel_state'] = c.r32(K.st('panel_state'))
        if K.dev.other:
            o['other_mmio'] = sorted(set(K.dev.other))[:8]
        o['by_function'] = by_function(K, c.profile)
        runs.append(o)
    return runs


def fit_cin_cout(K, entry, args, cmd, datalens, acks):
    """Instructions and MMIO accesses from c_in to c_out (the record's own
    duration) for replies of several lengths and ACK poll counts; a linear
    model in (ack_polls, nwords, rx[1]) is fitted and checked on every point."""
    pts = []
    for dl in datalens:
        for ack in acks:
            w = reply_words(cmd, [0x11] * dl)
            r = run_thread(K, entry, args, w, ack_polls=ack, reps=2)[1]
            rec = r['record']
            assert rec['ack_polls'] == ack and rec['nwords'] == len(w) and rec['ret'] > 0, rec
            assert rec['c_out'] - rec['c_in'] == r['cin_to_cout'], (rec, r['cin_to_cout'])
            pts.append(dict(ack_polls=ack, nwords=len(w), rx1=3 + dl, I=r['cin_to_cout'], N=r['mmio_cin_to_cout'],
                            rec_dur=rec['c_out'] - rec['c_in']))
    # solve I = a + b*ack + c*nwords + d*rx1 from four independent points, check all
    import fractions
    def solve(key):
        rows = [(1, p['ack_polls'], p['nwords'], p['rx1'], p[key]) for p in pts]
        # Gaussian elimination on the first 4 independent rows
        m = [list(map(fractions.Fraction, r)) for r in rows]
        sel, used = [], set()
        for col in range(4):
            for i, row in enumerate(m):
                if i in used:
                    continue
                trial = sel + [row]
                if rank(trial) == len(trial):
                    sel.append(row)
                    used.add(i)
                    break
        coef = gauss(sel)
        ok = all(sum(cf * x for cf, x in zip(coef, r[:4])) == r[4] for r in m)
        return [float(x) for x in coef], ok
    ci, oki = solve('I')
    cn, okn = solve('N')
    return dict(points=pts, I_coef_const_ack_nwords_rx1=ci, I_fit_exact=oki, N_coef_const_ack_nwords_rx1=cn,
                N_fit_exact=okn)


def rank(rows):
    import fractions
    m = [list(r[:4]) for r in rows]
    rk, col = 0, 0
    for col in range(4):
        piv = next((i for i in range(rk, len(m)) if m[i][col] != 0), None)
        if piv is None:
            continue
        m[rk], m[piv] = m[piv], m[rk]
        for i in range(len(m)):
            if i != rk and m[i][col] != 0:
                f = m[i][col] / m[rk][col]
                m[i] = [a - f * b for a, b in zip(m[i], m[rk])]
        rk += 1
    return rk


def gauss(rows):
    m = [list(r) for r in rows]
    n = len(m)
    for col in range(n):
        piv = next(i for i in range(col, n) if m[i][col] != 0)
        m[col], m[piv] = m[piv], m[col]
        for i in range(n):
            if i != col and m[i][col] != 0:
                f = m[i][col] / m[col][col]
                m[i] = [a - f * b for a, b in zip(m[i], m[col])]
    return [m[i][n] / m[i][i] for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default='/home/ubuntu/psp/work')
    a = ap.parse_args()
    pto = asm_offsets(os.path.join(a.work, 'linux/include/asm-mips/asm-offsets.h'))
    assert pto['PT_SIZE'] == 176 and pto['TI_REGS'] == TI_REGS and pto['_THREAD_SIZE'] == THREAD_SIZE
    B = Kernel(os.path.join(a.work, 'out/20260927T204657Z'), False, pto)
    N = Kernel(os.path.join(a.work, 'out/20261006T052947Z'), True, pto)
    # S14 (ACK wait) EPC of each build: the lw of 0xbe240020 in the ACK loop (DESIGN 10.6 S14)
    B.s14_epc, N.s14_epc = 0x880cefe0, 0x880cf0a4
    out = dict(images={'base vmlinux.bin': B.sha_bin, 'new vmlinux.bin': N.sha_bin},
               model=dict(ack_polls=ACK_POLLS, reply_08_words=len(R08), reply_33_words=len(R33),
                          reply_nop_words=len(RNOP), count_hz=HZ_COUNT, ipc=1))
    sc = {}
    for name, K in (('base', B), ('new', N)):
        sc[name] = dict(
            P08=run_thread(K, K.sym['_pspSysconGetCtrl2'], (lambda sp: sp + 256, lambda sp: sp + 260,
                                                              lambda sp: sp + 261), R08),
            P33=run_thread(K, K.sym['pspSyscon_tx_dword'], (1, 0x33, 3), R33),
            TICK=run_tick(K, 'TICK'),
            WD=run_tick(K, 'WD'),
            WDP=run_tick(K, 'WDP'),
        )
    sc['new']['T2D'] = run_tick(N, 'T2D', reps=1)
    out['scenarios'] = sc
    d = {}
    for p in ('P08', 'P33'):
        b, n = sc['base'][p][1], sc['new'][p][1]
        d[p] = dict(before_s5=n['before_s5'] - b['before_s5'], window=n['window_s5_s20'] - b['window_s5_s20'],
                    after_s20=n['after_s20'] - b['after_s20'], total=n['total'] - b['total'],
                    total_us=round((n['total'] - b['total']) / US, 2), stack=n['stack_bytes'] - b['stack_bytes'])
    for p in ('TICK', 'WD', 'WDP'):
        b, n = sc['base'][p], sc['new'][p]
        d[p] = dict(warm=n[1]['total'] - b[1]['total'], warm_us=round((n[1]['total'] - b[1]['total']) / US, 2),
                    first=n[0]['total'] - b[0]['total'], stack=n[1]['stack_below_ptregs'] - b[1]['stack_below_ptregs'])
        if 'before_nop_s5' in n[1]:
            d[p].update(before_nop_s5=n[1]['before_nop_s5'] - b[1]['before_nop_s5'],
                        nop_window=n[1]['nop_window'] - b[1]['nop_window'],
                        after_nop_s20=n[1]['after_nop_s20'] - b[1]['after_nop_s20'])
    d['T2D'] = dict(total=sc['new']['T2D'][0]['total'], total_us=round(sc['new']['T2D'][0]['total'] / US, 1))
    out['added'] = d
    # G3-low gap: 0x33's S20 store to the 0x08's S13 store (DESIGN 7.3). The thread
    # code between the two calls is counted from the listings (see README): base 4
    # instructions (88114aec..88114af8), new 10 with stage_max < 3, else 9
    # (881182a4..881182c8).
    TB, TN = 4, 10
    b33, n33, b08, n08 = sc['base']['P33'][1], sc['new']['P33'][1], sc['base']['P08'][1], sc['new']['P08'][1]
    gap_b = b33['after_s20'] + TB + b08['entry_to_s13']
    gap_n = n33['after_s20'] + TN + n08['entry_to_s13']
    out['g3_low_gap'] = dict(
        base_instr=gap_b, new_instr=gap_n, added=gap_n - gap_b, added_us=round((gap_n - gap_b) / US, 2),
        mmio_in_gap=b08['mmio_s5_to_s13_incl'] - 1,
        recorded_g_instr=n33['cout_to_t2'] + n33['t2_to_ret'] + TN + n08['entry_to_cin'],
        cout_to_t2_P33=n33['cout_to_t2'],
        outside_g_instr=n33['s20_to_cout'] + n08['cin_to_s13'],
        new_s20_to_cout_P33=n33['s20_to_cout'], new_cin_to_s13_P08=n08['cin_to_s13'],
        delta_I_gap=gap_n - gap_b)
    # extra code on the thread side that shifts the 0x33's start (loop top) and
    # the scheduler hooks of a wake-up (DESIGN 5.4 rows), run as the thread
    c = N.fresh()
    c.r[28] = T_TI
    c.cp0[12] = ST_CU0 | ST_IE | 0xFF00
    sp0 = T_TI + THREAD_SIZE - 32 - 512
    hooks = {}
    pidc = N.sym['psc_mem'] + ST_OFF + 4 * 140        # stats words 140-147 pid_class[8] (1.7)
    for i, (pid, cls) in enumerate(((31, 1), (32, 2), (25, 3), (24, 4), (5, 5))):
        c.w32(pidc + 4 * i, (cls << 24) | pid)
    O_TASK = 0x89E14000
    c.w32(T_TASK + 168, 40)                         # task_struct.pid (offset from psc_jp_thread_start)
    c.w32(O_TASK + 168, 7)
    c.w32(I_TASK + 168, 0)
    for nm, args, st in (('psc_poll_begin', (), 0), ('psc_poll_begin', (), 0), ('psc_poll_end', (), 0),
                         ('psc_poll_end', (), 0),
                         ('psc_sched_wake_slow', (), 0),                 # current = idle (softirq)
                         ('psc_sched_switch_slow', (I_TASK, O_TASK), 0),  # a switch while the thread waits
                         ('psc_sched_switch_slow', (O_TASK, T_TASK), 0),  # the switch-in of the thread
                         ('psc_sched_switch_slow', (T_TASK, I_TASK), 1)):  # the thread goes to sleep
        c.w32(T_TASK + 0, st)                       # task_struct.state (offset 0)
        c.r[28] = I_TI if nm != 'psc_poll_begin' else T_TI
        n0 = c.n
        c.call(N.sym[nm], args, sp=sp0)
        hooks.setdefault(nm, []).append(c.n - n0)
    # the thread preempted inside a command (2.11 hook S preemption branch):
    # switch-out while running with t_busy_p, a switch while it is off the CPU, its switch-in
    c.w32(N.k('t_busy_p'), 1)
    c.w32(N.k('t_cmd_id'), 77)
    c.w32(T_TASK + 0, 0)                            # TASK_RUNNING: an involuntary switch
    pre = []
    for args in ((T_TASK, O_TASK), (O_TASK, I_TASK), (I_TASK, T_TASK)):
        c.r[28] = I_TI
        n0 = c.n
        c.call(N.sym['psc_sched_switch_slow'], args, sp=sp0)
        pre.append(c.n - n0)
    hooks['psc_sched_switch_slow_preempted'] = pre
    out['thread_hooks'] = hooks
    out['fit'] = dict(
        P08=fit_cin_cout(N, N.sym['_pspSysconGetCtrl2'], (lambda sp: sp + 256, lambda sp: sp + 260,
                                                          lambda sp: sp + 261), 0x08, (3, 6, 10), (0, 20, 100)),
        P33=fit_cin_cout(N, N.sym['pspSyscon_tx_dword'], (1, 0x33, 3), 0x33, (0, 3, 7), (0, 20, 100)))
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
