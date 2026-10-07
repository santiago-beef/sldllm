#!/usr/bin/env python3
"""oracle.py - Stage 3 ring test: check every record of every dump byte for
byte against DESIGN 1.x, with every field value recomputed from the
harness's ground-truth event stream (build/ev/<scenario>.log), independently
of psc.c.

Ground truth used (all emitted by the harness, not by psc.c):
  XS/XE   one Syscon_cmd transaction, from the register-access observer
          (mmio.c): attempts, TX words, S5/S9/S11 values, drain pops, ACK
          polls, RX words, how it ended (-3, -4, normal)
  RC      every CP0 Count read with the psc.c function that made it (the
          capture instants: entry, exit, loop top, MS segment, sched hooks)
  TK/NOP  each timer interrupt with the interrupted context's frame
  SW/WK   context switches and thread wake-ups (scheduler model)
  LED/MSB/MSE  LED read-modify-writes and Memory Stick segments
  CTL/RR/OPEN  the collector's ctl writes and ring reads
  OSK/MOUSE    consumers
  BINJ/CINJ    forced injections (mid-irq-append)
Rules applied: DESIGN 1.2-1.5, 1.7, 2.1, 2.3 T2a/T2d, 2.4, 2.5, 2.10, 2.11,
3.4 and the section 17 R-1 / 18.3 `nwords` rule; syscon.c semantics for
`ret` (syscon.c:278-307); joypad_psp.c semantics for POLL (joypad_psp.c
479-766).

  oracle.py --events DIR --dumps DIR [--syms FILE] SCENARIO ...
"""
import argparse
import glob
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design_format as DF   # noqa: E402

CPT = 883651
DESIGN_MD = '/home/ubuntu/psp/handoff/design/DESIGN.md'
SYSCON_LO, SYSCON_HI = 0x880ceed0, 0x880cf300     # release Syscon_cmd .. Syscon_wait
JP_PID = 25
RING_IDX = {'P': 0, 'POLL': 1, 'W': 2, 'S': 3, 'M': 4}
RING_SIZE = {0: 80, 1: 40, 2: 288, 3: 40, 4: 80}
RING_NAME = {0: 'P', 1: 'POLL', 2: 'W', 3: 'S', 4: 'M'}
PSC_C = '/home/ubuntu/psp/work/linux/arch/mips/psp/psc.c'
TBUSY_LINE = 0
EXE = None          # host binary of the event logs (from --syms), for addr2line
_A2L = {}


def tbusy_set_line():
    """psc.c line of PSC_WR(psc_k.t_busy_p, 1) in psc_sc_entry"""
    with open(PSC_C) as fi:
        for i, line in enumerate(fi, 1):
            if 'PSC_WR(psc_k.t_busy_p, 1);' in line:
                return i
    raise RuntimeError('t_busy_p = 1 not found in psc.c')


def host_src_line(ra):
    """first (innermost) file:line of a host return address"""
    if ra not in _A2L:
        import subprocess
        out = subprocess.run(['addr2line', '-i', '-e', EXE, ra], capture_output=True, text=True).stdout
        first = out.splitlines()[0] if out else '?:0'
        f, _, ln = first.rpartition(':')
        _A2L[ra] = (os.path.basename(f), int(re.match(r'\d+', ln).group(0)) if re.match(r'\d+', ln) else 0)
    return _A2L[ra]


def sat(v, m):
    return m if v > m else (0 if v < 0 else v)


def dcount(t0, c0, t1, c1):
    """psc_dcount (DESIGN 2.11: (tick difference) x CPT + Count difference)"""
    dt = (t1 - t0) & 0xFFFFFFFF
    if dt > 4861:
        return 0xFFFFFFFF
    v = dt * CPT + c1
    if v < c0:
        return 0
    v -= c0
    return 0xFFFFFFFF if v > 0xFFFFFFFF else v


# ------------------------------------------------------------ DESIGN.md
def design_tables_check():
    """Extract the 1.2, 1.3, 1.4, 1.5 tables from DESIGN.md and compare them
    with design_format.py (catches a transcription slip)."""
    tmap = {'u32': 'I', 'u16': 'H', 'u8': 'B', 's16': 'h', 's8': 'b',
            'u8[16]': '16s', 'u32[16]': '16I'}
    lines = open(DESIGN_MD, encoding='utf-8').read().splitlines()
    heads = {'1.2': '### 1.2 SC record', '1.3': '### 1.3 W record', '1.4': '### 1.4 POLL record',
             '1.5': '### 1.5 S record'}
    tables = {}
    for key, h in heads.items():
        i = next(k for k, l in enumerate(lines) if l.startswith(h))
        rows = []
        for l in lines[i + 1:]:
            if l.startswith('### '):
                break
            m = re.match(r'^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', l)
            if m:
                typ = m.group(2).replace('`', '').strip()
                fld = m.group(3).replace('`', '').strip()
                if typ == 'u8, u16':          # 1.5 row "29 | u8, u16 | —"
                    rows.append((29, 'B', 'rsv29'))
                    rows.append((30, 'H', 'rsv30'))
                    continue
                if fld in ('—', '-'):
                    fld = 'rsv'
                rows.append((int(m.group(1)), tmap.get(typ, '?' + typ), fld))
        tables[key] = rows
    probs = []
    for key, mine in (('1.2', DF.SC_TABLE), ('1.3', DF.WEXT_TABLE), ('1.4', DF.POLL_TABLE), ('1.5', DF.S_TABLE)):
        got = tables[key]
        if [(o, c) for (o, c, _n) in got] != [(o, c) for (o, c, _n) in mine]:
            probs.append('DESIGN %s table differs from design_format.py: %s' % (key, got))
    return probs, {k: len(v) for k, v in tables.items()}


# ------------------------------------------------------------ dump files
def parse_dump(psclog, nonce):
    """DESIGN 10.2 parse: chunks at any 4-byte offset, CRC (nonce seed for
    non-FILEHDR), RECS blocks -> records by (ring, seq)."""
    recs = {r: {} for r in range(5)}
    stats = []
    uhb = []
    events = []
    files = sorted(glob.glob(os.path.join(psclog, 'T*.BIN')))
    probs = []
    for fn in files:
        buf = open(fn, 'rb').read()
        if len(buf) != 2097152:
            probs.append('%s: size %d' % (fn, len(buf)))
        off = 0
        while off + 20 <= len(buf):
            if buf[off:off + 4] != b'PSCK':
                off += 4
                continue
            magic, typ, hver, ln, fseq, crc = struct.unpack_from(DF.CHUNK_FMT, buf, off)
            pay = buf[off + 20:off + 20 + ln]
            seed = 0 if typ == 1 else nonce
            if hver != 5 or ln > 65536 or len(pay) != ln or (zlib.crc32(pay, seed) & 0xFFFFFFFF) != crc:
                off += 4
                continue
            if typ == 2:
                p = 0
                while p < ln:
                    ring, d4, cnt, lost = struct.unpack_from(DF.BLOCK_FMT, pay, p)
                    p += 8
                    rs = d4 * 4
                    for k in range(cnt):
                        raw = pay[p:p + rs]
                        seq = struct.unpack_from('<I', raw)[0]
                        r = ring & 0x7F
                        if seq in recs[r] and recs[r][seq] != raw:
                            probs.append('conflict ring %d seq %d' % (r, seq))
                        recs[r][seq] = raw
                        p += rs
            elif typ == 3:
                stats.append(struct.unpack(DF.STATS_FMT, pay))
            elif typ == 6:
                uhb.append(struct.unpack(DF.UHB_FMT, pay))
            elif typ == 7:
                events.extend(pay.decode('latin-1').splitlines())
            off += 20 + ((ln + 3) & ~3)
    return recs, stats, uhb, events, probs, files


# ------------------------------------------------------------ the model
class Model(object):
    def __init__(self):
        self.exp = {r: [] for r in range(5)}       # expected dicts in seq order
        self.p_pub = 0          # P records published (cost RC seen)
        self.w_count = 0        # W records (XE T/B)
        self.m_count = 0
        self.m_dropped = 0
        self.t_cmd_id = 0
        self.t_busy_p = 0
        self.t_busy_m = 0
        self.t_entry = (0, 0)
        self.lc = dict(seq=0, tick=0, c_pre=0, cmd_id=0, epc=0, cause=0, ra=0, sp=0, r=[0] * 16, n=0,
                       wdtick=0)
        self.lc_nest_id = 0
        self.lc_nested = 0
        self.wd_calls = 0
        self.wd_last_tick = 0
        self.led_calls = 0
        self.led_calls_t_busy = 0
        self.led_cmd = dict(id=0, orv=0, pid=0)
        self.led_or_run = [0, 0]
        self.seg = None
        self.jp_loop = 0
        self.stage = 0
        self.last_rc = {}
        self.tick = 0
        self.cur_pid = 0
        self.ctx = []           # stack of open transactions
        self.p_open = None
        self.pid_class = {}
        self.wk = dict(pending=0, t0=(0, 0), last=(0, 0), acc=0, nsw=0, cls0=0, count=0,
                       pub=(0, 0, 0, 0, 0))
        self.poll_wk_count = 0
        self.pre = dict(cmd_id=0, on=0, t0=(0, 0), last=(0, 0), tot=0, wrk=0, n=0, flags=0, cls0=0, cls1=0)
        self.jp_nivcsw = 0
        self.panel = dict(due=125, test_seq=0, test_seen=0, until=0, state=0, paints=0, cmd_id=0,
                          last_tick=0, test_done=0)
        self.proc_opens = 0
        self.durable_tick = 0
        self.last_reader_tick = 0
        self.oc = {'08': [0] * 7, '33': [0] * 7, 'W': [0] * 7}
        self.p_nested = 0
        self.p_ticked = 0
        self.total_counts = 0
        self.c_pre_max = 0
        self.long_ticks = 0
        self.ms_seg_wr = 0
        self.ms_seg_rd = 0
        self.irq_depth = 0
        self.binj = None
        self.poll = None
        self.poll_prev_tick = None
        self.joy = dict(lastKeys=0, mouseMode=False, s_keys=0, btn=(False, False, False), q=0, osk_open=False)
        self.stats_snaps = []
        self.notes = []
        self.pending_poll_p = []
        self.devmode = 0
        self.run_pid = 0        # the task running outside interrupts (SW events)
        self.p_entry = None     # psc_sc_entry snapshots of the thread's command (psc.c:214-241)

    def cls_of(self, pid):
        if pid in self.pid_class:
            return self.pid_class[pid]
        return 7 if pid in (77, 76, 30, 31) else 6

    # ---- syscon.c semantics
    @staticmethod
    def ret_of(how, attempts, rx, nrx):
        if how == 3:
            return -3
        if how == 4:
            return -4
        result = rx[0] if nrx >= 1 else 0
        if result > 0:
            cnt = rx[1]
            if cnt < 3:
                result = -2
            else:
                if cnt >= 16:
                    return None           # reads past rx_buf: not predictable
                if ((sum(rx[:cnt]) & 0xFF) ^ 0xFF) != rx[cnt]:
                    result = -2
        if rx[2] in (0x80, 0x81) and attempts == 15:
            result = -5
        return result

    @staticmethod
    def nwords_of(how, nrx, rx):
        if how in (3, 4):
            return 0
        t0 = min(2 * nrx + 2, 16)
        if t0 < 16:
            return (t0 - 2) >> 1
        return 7 if (rx[14] == 0xff and rx[15] == 0xff) else 8

    @staticmethod
    def oc_index(ret, nwords):
        if ret > 0:
            return 0
        if ret == 0:
            return 1 if nwords else 2
        return {-2: 3, -3: 4, -4: 5}.get(ret, 6)

    def sc_common(self, x, xe):
        how, attempts = xe['how'], xe['attempts']
        rx = xe['rx']
        ret = self.ret_of(how, attempts, rx, xe['nrx'])
        nw = self.nwords_of(how, xe['nrx'], rx)
        busy_final = how == 0 and xe['nrx'] >= 2 and rx[2] in (0x80, 0x81)
        drain = 0
        if xe['drain_n'] or how == 3:
            drain = 0xFFFF if how == 3 else sat(xe['drain_n'], 0xFFFF)
        origin = {'P': 0, 'M': 1, 'B': 2, 'T': 3}[x['origin']]
        ctx = origin
        if x['ie']:
            ctx |= 0x04
        if x['pcnt'] & 0x0FFFFF00:
            ctx |= 0x08
        if x['pid'] == JP_PID:
            ctx |= 0x10
        if x['pcnt']:
            ctx |= 0x20
        if origin <= 1 and x['sig']:
            ctx |= 0x40
        d = dict(seq=0, tick_in=x['cin'][0], c_in=x['cin'][1], c_out=xe['c'],
                 dtick=sat((xe['tick'] - x['cin'][0]) & 0xFFFFFFFF, 0xFFFF),
                 cmd=xe['txw0'] >> 8, txlen=xe['txw0'] & 0xFF, ret=ret if ret is not None else 0,
                 nwords=nw, retries=attempts + (1 if busy_final and attempts == 15 else 0),
                 ack_polls=0xFFFFFFFF if how == 3 else (1000001 if how == 4 else xe['ack_fail']),
                 drain=drain, drain_last=(xe['dlast'] if drain else 0), gpio_in=xe['gin'],
                 spi_st9=0 if how == 3 else xe['st9'], spi_sttx=0 if how == 3 else xe['sttx'],
                 ctx=ctx, wn=0, w_head_lo=0, pre_wrk=0, pre_cls=0, ms_delta=0, pre_flags=0, preempt_delta=0,
                 rx=bytes(rx), lc_epc=0, lc_dtick=0, lc_n=0, lc_flags=0, led_or=0, led_pid=0, pre_tot=0)
        if ret is None:
            d['_ret_unknown'] = True
        return d

    # ---- events
    def on_xs(self, f):
        o = f[1]
        x = dict(origin=o, tick=int(f[2]), c=int(f[3]), pid=int(f[4]), ie=int(f[5]), pcnt=int(f[6]),
                 sig=int(f[7]))
        x['cin'] = self.last_rc.get('psc_syscon_cmd', (x['tick'], x['c']))
        x['wd0'] = self.wd_calls
        x['led0'] = self.led_calls
        x['niv0'] = self.jp_nivcsw if o == 'P' else 0
        if o == 'P' and self.p_entry is not None:
            # psc_sc_entry already ran (snapshots, cmd_id, t_entry); an
            # interrupt may have run between it and the transaction
            e = self.p_entry
            self.p_entry = None
            x.update(cin=e['cin'], wd0=e['wd0'], led0=e['led0'], niv0=e['niv0'], cmd_id=e['cmd_id'])
            self.t_busy_p = 1
        elif o == 'P':
            self.t_cmd_id += 1
            x['cmd_id'] = self.t_cmd_id
            self.t_entry = x['cin']
            self.t_busy_p = 1
            self.stage = 2 if not self.pending_poll_p else 3
        elif o == 'M':
            self.t_busy_m = 1
        self.ctx.append(x)

    def on_xe(self, f):
        x = self.ctx.pop()
        rxh = f[15]
        xe = dict(tick=int(f[2]), c=int(f[3]), how=int(f[4]), attempts=int(f[5]), txw0=int(f[6]),
                  gin=int(f[8]), drain_n=int(f[9]), dlast=int(f[10]), st9=int(f[11]), sttx=int(f[12]),
                  ack_fail=int(f[13]), nrx=int(f[14]), rx=list(bytes.fromhex(rxh)))
        d = self.sc_common(x, xe)
        o = x['origin']
        d['_x'] = x
        if o in ('T', 'B'):
            s = self.w_count
            d['seq'] = s
            d['w_head_lo'] = s & 0xFFFF
            d['lc_dtick'] = 0
            if o == 'T':
                d.update({'ext.' + k: v for k, v in self.w_ext.items()})
            else:
                for n in DF.WEXT_NAMES:
                    d['ext.' + n] = 0
            self.exp[2].append(d)
            self.w_count += 1
            self.wd_calls += 1
            self.wd_last_tick = x['cin'][0]
            if '_ret_unknown' not in d:
                self.oc['W'][self.oc_index(d['ret'], d['nwords'])] += 1
        elif o == 'P':
            d['seq'] = len(self.exp[0])
            d['wn'] = sat(self.wd_calls - x['wd0'], 0xFF)
            d['w_head_lo'] = self.w_count & 0xFFFF
            d['ms_delta'] = sat(self.led_calls - x['led0'], 0xFF)
            d['preempt_delta'] = sat(self.jp_nivcsw - x['niv0'], 0xFF)
            d['_pending_exit'] = True
            self.p_open = d
            self.t_busy_p = 0
            self.exp[0].append(d)
            self.pending_poll_p.append(d)
        else:
            s = self.m_count
            self.m_count += 1
            d['wn'] = sat(self.wd_calls - x['wd0'], 0xFF)
            d['w_head_lo'] = self.w_count & 0xFFFF
            d['ms_delta'] = sat(self.led_calls - x['led0'], 0xFF)
            d['lc_dtick'] = 0xFFFF
            self.t_busy_m = 0
            if s < 64:
                d['seq'] = s
                self.exp[4].append(d)
            else:
                self.m_dropped += 1

    def finish_p(self):
        """psc_fill_thread (psc.c:304-369) for the P record just exited"""
        d = self.p_open
        self.p_open = None
        x = d['_x']
        idv = x['cmd_id']
        lc = self.lc
        flags = 0
        d['lc_dtick'] = 0xFFFF
        if lc['cmd_id'] == idv and lc['n']:
            flags |= 0x01
            if lc['cause'] & 0x80000000:
                flags |= 0x02
            if SYSCON_LO <= lc['epc'] < SYSCON_HI:
                flags |= 0x04
            if lc['wdtick']:
                flags |= 0x08
            d['lc_epc'] = lc['epc']
            d['lc_dtick'] = sat((lc['tick'] - x['cin'][0]) & 0xFFFFFFFF, 0xFFFF)
            d['lc_n'] = sat(lc['n'], 0xFF)
        if self.lc_nest_id == idv:
            flags |= 0x10
        if self.panel['cmd_id'] == idv:
            flags |= 0x20
        d['lc_flags'] = flags
        if self.led_cmd['id'] == idv:
            d['led_or'] = self.led_cmd['orv']
            d['led_pid'] = self.led_cmd['pid'] & 0xFFFF
        if self.pre['cmd_id'] == idv:
            pf = self.pre['flags'] | 0x01
            if (self.pre['tot'] >> 8) > 0xFFFF or (self.pre['wrk'] >> 8) > 0xFFFF:
                pf |= 0x04
            d['pre_tot'] = sat(self.pre['tot'] >> 8, 0xFFFF)
            d['pre_wrk'] = sat(self.pre['wrk'] >> 8, 0xFFFF)
            d['pre_cls'] = (self.pre['cls0'] & 0xF) | ((self.pre['cls1'] & 0xF) << 4)
            d['pre_flags'] = pf
        del d['_pending_exit']
        cmd = d['cmd']
        if '_ret_unknown' not in d:
            if cmd == 0x08:
                self.oc['08'][self.oc_index(d['ret'], d['nwords'])] += 1
            elif cmd == 0x33:
                self.oc['33'][self.oc_index(d['ret'], d['nwords'])] += 1
        if d['wn']:
            self.p_nested += 1
        if d['dtick']:
            self.p_ticked += 1
        self.p_pub += 1

    def on_tk(self, f):
        newtick = int(f[1])
        c_pre = int(f[2])
        pid = int(f[3])
        nested = int(f[4])
        epc, cause, status, ra, sp = [int(v, 16) for v in f[5:10]]
        pcnt = int(f[10])
        msact = int(f[11])
        regs = [int(v, 16) for v in f[12].split(',')]
        self.irq_depth += 1
        self.tick = newtick
        self.cur_pid = pid
        self.total_counts += c_pre
        if c_pre > self.c_pre_max:
            self.c_pre_max = c_pre
        if c_pre > CPT + CPT // 2:
            self.long_ticks += 1
        # the W extension as the Nop of this tick would fill it (psc_fill_wext)
        lc = self.lc
        ef = 0x01
        if status & 0x10000000:
            ef |= 0x04
        if SYSCON_LO <= epc < SYSCON_HI:
            ef |= 0x08
        if pid == JP_PID:
            ef |= 0x10
        if self.cur_t_busy_p() and lc['cmd_id'] == self.t_cmd_id and lc['n']:
            ef |= 0x20
        if msact:
            ef |= 0x40
        if pcnt & 0x0FFFFF00:
            ef |= 0x80
        self.w_ext = dict(epc=epc, cause=cause, status=status, ra=ra, sp=sp, pid=pid,
                          p_head=self.p_pub_at_irq(), jp_loop=self.jp_loop,
                          t_entry_tick=self.t_entry[0], t_entry_c=self.t_entry[1],
                          t_busy=(1 if self.cur_t_busy_p() else 0) | (2 if self.t_busy_m else 0),
                          jp_stage=self.stage, ext_flags=ef, cur_pcnt=pcnt & 0xFF, c_pre=c_pre,
                          lc_tick=lc['tick'], lc_c_pre=lc['c_pre'], lc_cmd_id=lc['cmd_id'], lc_epc=lc['epc'],
                          lc_cause=lc['cause'], lc_ra=lc['ra'], lc_sp=lc['sp'], lc_n=sat(lc['n'], 0xFFFF), rsv=0)
        for i in range(16):
            self.w_ext['r[%d]' % i] = regs[i]
            self.w_ext['lc_r[%d]' % i] = lc['r'][i]
        self.tk_pending = dict(tick=newtick, c_pre=c_pre, pid=pid, nested=nested, epc=epc, cause=cause,
                               ra=ra, sp=sp, regs=regs)

    def cur_t_busy_p(self):
        if self.binj is not None:
            return self.binj['t_busy_p']
        return self.t_busy_p

    def p_pub_at_irq(self):
        return self.p_pub

    def t2a_t2d(self):
        """psc_tick_hook after the Nop (psc.c:561-619)"""
        tk = self.tk_pending
        if self.cur_t_busy_p() and tk['pid'] == JP_PID:
            if tk['nested']:
                self.lc_nested += 1
                self.lc_nest_id = self.t_cmd_id
            else:
                lc = self.lc
                lc['tick'] = tk['tick']
                lc['c_pre'] = tk['c_pre']
                lc['epc'], lc['cause'], lc['ra'], lc['sp'] = tk['epc'], tk['cause'], tk['ra'], tk['sp']
                lc['r'] = list(tk['regs'])
                if lc['cmd_id'] != self.t_cmd_id:
                    lc['cmd_id'] = self.t_cmd_id
                    lc['n'] = 0
                if lc['n'] < 0xFFFF:
                    lc['n'] += 1
                lc['wdtick'] = 1 if (self.wd_calls and self.wd_last_tick == tk['tick']) else 0
        # T2d (once a second at the tick == due, psc.c:612-618; panel 2.10)
        if tk['tick'] == self.panel['due']:
            self.panel['due'] = tk['tick'] + 250
            self.t2d(tk['tick'])

    def t2d(self, tick):
        pn = self.panel
        if not self.proc_opens:
            return
        if pn['test_seq'] != pn['test_seen']:
            pn['test_seen'] = pn['test_seq']
            pn['until'] = tick + 250 * pn['test_secs']
        test_active = ((pn['until'] - tick) & 0xFFFFFFFF) < 0x80000000 and pn['until'] != tick
        cond = ((tick - self.durable_tick) & 0xFFFFFFFF) > 750 or \
               ((tick - self.last_reader_tick) & 0xFFFFFFFF) > 750 or test_active
        if cond:
            pn['paints'] += 1
            pn['last_tick'] = tick
            if self.cur_t_busy_p():
                pn['cmd_id'] = self.t_cmd_id
            pn['state'] = 2
            if test_active:
                pn['test_done'] += 1
        elif pn['state'] == 2:
            pn['paints'] += 1
            pn['last_tick'] = tick
            if self.cur_t_busy_p():
                pn['cmd_id'] = self.t_cmd_id
            pn['state'] = 1

    def on_tkx(self, f):
        self.t2a_t2d()
        self.irq_depth -= 1

    def on_led(self, f):
        st, v, pid = int(f[1]), int(f[2]), int(f[3])
        self.led_calls += 1
        if self.t_busy_p or self.t_busy_m:
            self.led_calls_t_busy += 1
        self.led_or_run[0 if st else 1] |= v
        if self.seg is not None:
            self.seg['led_ops'] += 1
            if st:
                self.seg['set_or'] |= v
                if v & 0x08:
                    self.seg['flags'] |= 0x04
            else:
                self.seg['clr_or'] |= v
                if v & 0x08:
                    self.seg['flags'] |= 0x08
        if self.t_busy_p:
            if self.led_cmd['id'] != self.t_cmd_id:
                self.led_cmd['orv'] = 0
                self.led_cmd['id'] = self.t_cmd_id
            self.led_cmd['orv'] |= v
            self.led_cmd['pid'] = pid

    def on_msb(self, f):
        self.seg = dict(sector=int(f[1]), nsect=int(f[2]), write=int(f[3]), pid=int(f[4]),
                        led_ops=0, set_or=0, clr_or=0, flags=0, busy_in=(1 if self.t_busy_p else 0) |
                        (2 if self.t_busy_m else 0), p_head=self.p_pub, on=None)

    def on_mse(self, f):
        sg = self.seg
        self.seg = None
        rt, meta = int(f[4]), int(f[5])
        on = sg['on']
        off = sg['off']
        fl = sg['flags'] | (0x01 if sg['write'] else 0) | (0x02 if rt < 0 else 0)
        if sg['busy_in'] & 1:
            fl |= 0x10
        if self.t_busy_p:
            fl |= 0x20
        if (sg['busy_in'] & 2) or self.t_busy_m:
            fl |= 0x40
        if meta:
            fl |= 0x80
        d = dict(seq=len(self.exp[3]), tick_on=on[0], c_on=on[1], c_off=off[1], sector=sg['sector'],
                 dtick=sat((off[0] - on[0]) & 0xFFFFFFFF, 0xFFFF), pid=sg['pid'] & 0xFFFF,
                 nsect=sat(sg['nsect'], 0xFF), flags=fl, p_head_lo=sg['p_head'] & 0xFFFF,
                 led_ops=sat(sg['led_ops'], 0xFF), rsv29=0, rsv30=0, rd_set_or=sg['set_or'],
                 rd_clr_or=sg['clr_or'])
        self.exp[3].append(d)
        if sg['write']:
            self.ms_seg_wr += 1
        else:
            self.ms_seg_rd += 1

    def on_rc(self, f):
        fn, t, c = f[1].split('.')[0], int(f[2]), int(f[3])   # gcc clones: name.part.N
        self.last_rc[fn] = (t, c)
        if fn == 'psc_syscon_cmd' and self.irq_depth == 0 and self.run_pid == JP_PID:
            # psc_sc_entry of a thread command (origin P): tick_in/c_in, then
            # wd_calls0, led_calls0, nivcsw0 (psc.c:214-219); t_cmd, t_entry,
            # ++t_cmd_id (psc.c:235-239); t_busy_p = 1 after the barrier at
            # psc.c:240 (set at the XS event, or at an injection after it)
            self.t_cmd_id += 1
            self.t_entry = (t, c)
            self.stage = 2 if not self.pending_poll_p else 3
            self.p_entry = dict(cin=(t, c), wd0=self.wd_calls, led0=self.led_calls,
                                niv0=self.jp_nivcsw, cmd_id=self.t_cmd_id)
        if fn == 'psc_sc_exit':
            # the first read is c_out (already in XE); the second (P and W
            # paths) is the cost read after the record is published
            if self.p_open is not None and self.irq_depth == 0:
                n = self.p_open.setdefault('_exit_reads', 0) + 1
                self.p_open['_exit_reads'] = n
                if n == 2:
                    self.finish_p()
        elif fn == 'psc_poll_begin':
            self.poll_begin(t, c)
        elif fn == 'psc_poll_end':
            self.poll_end(t, c)
        elif fn == 'psc_ms_seg_begin':
            if self.seg is not None and self.seg['on'] is None:
                self.seg['on'] = (t, c)
        elif fn == 'psc_ms_seg_end':
            if self.seg is not None and 'off' not in self.seg:
                self.seg['off'] = (t, c)
        elif fn == 'psc_sched_wake_slow':
            self.wk_wake(t, c)
        elif fn == 'psc_sched_switch_slow':
            if self.sw_pending is not None:
                self.switch_hook(self.sw_pending, (t, c))
                self.sw_pending = None
        elif fn == 'psc_stats_read':
            self.stats_snaps.append(self.stats_now(t, c))

    # ---- scheduler hooks (DESIGN 2.11, psc.c:732-828)
    def wk_wake(self, t, c):
        self.wk.update(pending=1, t0=(t, c), last=(t, c), acc=0, nsw=0, cls0=self.cls_of(self.cur_pid))

    def on_sw(self, f):
        prev, nxt, pstate = int(f[1]), int(f[2]), int(f[3])
        self.run_pid = nxt
        if prev == JP_PID and pstate == 0:
            self.jp_nivcsw += 1
        # hook S runs after ++*switch_count (sched.c:3707-3713); its Count
        # read (RC psc_sched_switch_slow) follows only when it has work
        self.sw_pending = (prev, nxt, pstate)

    def switch_hook(self, sw, now):
        prev, nxt, pstate = sw
        wk = self.wk
        if wk['pending']:
            d = dcount(wk['last'][0], wk['last'][1], now[0], now[1])
            cls = self.cls_of(prev)
            if cls in (1, 2):
                wk['acc'] = min(0xFFFFFFFF, wk['acc'] + d)
            wk['last'] = now
            wk['nsw'] += 1
            if nxt == JP_PID:
                delay = dcount(wk['t0'][0], wk['t0'][1], now[0], now[1]) >> 8
                wk['pub'] = (sat(delay, 0xFFFF), sat(wk['acc'] >> 8, 0xFFFF), wk['cls0'], cls, sat(wk['nsw'], 0xFF))
                wk['count'] += 1
                wk['pending'] = 0
        pre = self.pre
        if prev == JP_PID and pstate == 0 and self.t_busy_p:
            if pre['cmd_id'] != self.t_cmd_id:
                pre.update(cmd_id=self.t_cmd_id, tot=0, wrk=0, n=0, flags=0, cls0=self.cls_of(nxt), cls1=0)
            else:
                pre['flags'] |= 0x02
            pre.update(t0=now, last=now, on=1)
        elif pre['on']:
            d = dcount(pre['last'][0], pre['last'][1], now[0], now[1])
            cls = self.cls_of(prev)
            if cls in (1, 2):
                pre['wrk'] = min(0xFFFFFFFF, pre['wrk'] + d)
            else:
                pre['flags'] |= 0x08
            if 3 <= cls <= 5:
                pre['flags'] |= 0x10
            pre['last'] = now
            if nxt == JP_PID:
                pre['tot'] = min(0xFFFFFFFF, pre['tot'] + dcount(pre['t0'][0], pre['t0'][1], now[0], now[1]))
                pre['cls1'] = cls
                pre['n'] += 1
                pre['on'] = 0

    # ---- the joypad thread (joypad_psp.c:479-766) and POLL (1.4, 2.5)
    def poll_begin(self, t, c):
        self.jp_loop += 1
        p = dict(seq=len(self.exp[1]), tick_start=t, c_start=c, c_end=0, sc_seq_lo=self.p_pub & 0xFFFF,
                 body_ticks=0, ri_branch=0, pi_flags=0, nqueues=0, push_ok=0, push_fail=0, mouse_flags=0,
                 dx=0, dy=0, sig=0, period=0 if self.poll_prev_tick is None else sat(t - self.poll_prev_tick, 0xFF),
                 preempt_delta=0, stage_max=1, nsc=0, wk_delay=0, wk_wrk=0, wk_cls0=0, wk_cls1=0, wk_nsw=0, rsv=0)
        self.poll_prev_tick = t
        self.poll_niv0 = self.jp_nivcsw
        self.poll_p0 = self.p_pub
        if self.wk['count'] != self.poll_wk_count:
            p['wk_delay'], p['wk_wrk'], p['wk_cls0'], p['wk_cls1'], p['wk_nsw'] = self.wk['pub']
            self.poll_wk_count = self.wk['count']
        self.poll = p
        self.pending_poll_p = []
        self.stage = 1

    def poll_end(self, t, c):
        p = self.poll
        if p is None:
            return
        p['c_end'] = c
        p['body_ticks'] = sat(t - p['tick_start'], 0xFF)
        p['preempt_delta'] = sat(self.jp_nivcsw - self.poll_niv0, 0xFF)
        p['nsc'] = sat(self.p_pub - self.poll_p0, 0xFF)
        self.simulate_driver(p)
        self.exp[1].append(p)
        self.poll = None
        self.stage = 17

    @staticmethod
    def conv(v):
        n = (v >> 4) & 0xF
        return {0: -16, 1: -4, 2: -2, 3: -2, 4: -1, 5: -1, 0xA: 1, 0xB: 1, 0xC: 2, 0xD: 2, 0xE: 4,
                0xF: 16}.get(n, 0)

    def simulate_driver(self, p):
        ps = [d for d in self.pending_poll_p]
        p08 = next((d for d in ps if d['cmd'] == 0x08), None)
        smax = 4
        if p08 is None:
            p['ri_branch'] = 0
            p['stage_max'] = 3
            return
        rx = p08['rx']
        key = rx[3] | (rx[4] << 8) | (rx[5] << 16) | (rx[6] << 24)
        keys = (~key) & 0xFFFFFFFF
        j = self.joy
        if p08['ret'] < 0:
            p['ri_branch'] = 3
            self.jp_r[0] += 1
        elif keys & 0x2000:
            p['ri_branch'] = 4
            self.jp_r[1] += 1
        else:
            p['ri_branch'] = 5
            self.jp_r[2] += 1
            x, y = rx[7], rx[8]
            pi = 0x01
            kk = keys | ((x & 0xF0) << 20) | ((y & 0xF0) << 24)
            smax = 5
            if j['lastKeys'] == kk:
                pi |= 0x02
                smax = 6
            else:
                j['lastKeys'] = kk
                smax = 8
                if kk & 0x100:
                    j['mouseMode'] = not j['mouseMode']
                    pi |= 0x08
                if j['mouseMode']:
                    kk |= 0x00800000
                    pi |= 0x10
                j['s_keys'] = kk
                pi |= 0x20
                smax = 10
                if j['osk_open']:
                    p['nqueues'] = 1
                    smax = 12
                    if j['q'] >= 16:
                        p['push_fail'] = 1
                    else:
                        j['q'] += 1
                        p['push_ok'] = 1
                pi |= 0x80
                smax = 14
            p['pi_flags'] = pi
            if j['s_keys'] & 0x00800000:
                mf = 0x01
                smax = 15
                dx, dy = self.conv(x), self.conv(y)
                left = mid = right = False
                if (keys & 0x200) and (keys & 0x400):
                    mid = True
                elif keys & 0x200:
                    left = True
                elif keys & 0x400:
                    right = True
                if keys & 0x8:
                    dx -= 2
                if keys & 0x2:
                    dx += 2
                if keys & 0x1:
                    dy -= 2
                if keys & 0x4:
                    dy += 2
                if dx == 0 and dy == 0 and j['btn'] == (left, mid, right):
                    mf |= 0x04
                else:
                    j['btn'] = (left, mid, right)
                    mf |= 0x08 | (0x10 if left else 0) | (0x20 if mid else 0) | (0x40 if right else 0)
                    p['dx'] = max(-128, min(127, dx))
                    p['dy'] = max(-128, min(127, dy))
                    smax = 16
                p['mouse_flags'] = mf
        p['stage_max'] = smax

    # ---- stats (1.7) at the instant of a stats read
    def stats_now(self, t, c):
        return dict(now_tick=t, now_count=c, head=[self.p_pub, len(self.exp[1]), self.w_count, len(self.exp[3]),
                                                    min(self.m_count, 64)],
                    m_dropped=self.m_dropped, wd_calls=self.wd_calls, wd_last_tick=self.wd_last_tick,
                    p_nested=self.p_nested, p_ticked=self.p_ticked, oc_p08=list(self.oc['08']),
                    oc_p33=list(self.oc['33']), oc_w=list(self.oc['W']), jp_loop=self.jp_loop,
                    led_calls=self.led_calls, led_or_set_run=self.led_or_run[0],
                    led_or_clr_run=self.led_or_run[1], ms_seg_wr=self.ms_seg_wr, ms_seg_rd=self.ms_seg_rd,
                    total_counts=self.total_counts, c_pre_max=self.c_pre_max, long_ticks=self.long_ticks,
                    durable_tick=self.durable_tick, lc_nested=self.lc_nested, panel_paints=self.panel['paints'],
                    panel_test_done=self.panel['test_done'], proc_opens=self.proc_opens,
                    jp_r=list(self.jp_r))

    def on_ctl(self, f):
        op = int(f[1])
        a = [int(v) for v in f[2:8]]
        if op == 1:
            self.durable_tick = a[0]
        elif op == 2:
            self.pid_class[a[1]] = a[2]
        elif op == 3:
            self.panel['test_seq'] += 1
            self.panel['test_secs'] = a[0]

    def on_rr(self, f):
        self.last_reader_tick = int(f[2])

    def run(self, path):
        self.jp_r = [0, 0, 0]
        self.w_ext = {}
        self.tk_pending = None
        self.sw_pending = None
        binj_stack = []
        with open(path) as fi:
            for line in fi:
                f = line.split()
                if not f:
                    continue
                k = f[0]
                if k == 'RC':
                    self.on_rc(f)
                elif k == 'XS':
                    self.on_xs(f)
                elif k == 'XE':
                    self.on_xe(f)
                elif k == 'TK':
                    self.on_tk(f)
                elif k == 'TKX':
                    self.on_tkx(f)
                    if binj_stack and self.irq_depth == 0:
                        self.binj = binj_stack.pop()
                        self.binj = None
                elif k == 'LED':
                    self.on_led(f)
                elif k == 'MSB':
                    self.on_msb(f)
                elif k == 'MSE':
                    self.on_mse(f)
                elif k == 'SW':
                    self.on_sw(f)
                elif k == 'CTL':
                    self.on_ctl(f)
                elif k == 'RR':
                    self.on_rr(f)
                elif k == 'OPEN':
                    self.proc_opens += 1
                elif k == 'OSK':
                    n = int(f[1])
                    if n > 0:
                        self.joy['q'] = max(0, self.joy['q'] - n)
                elif k == 'BINJ':
                    # forced tick inside an append: the thread state at that
                    # barrier of psc_sc_exit / psc_poll_end / psc_ms_seg_end
                    fn = f[4].split('+')[0]
                    idx = int(f[1])
                    st = {'t_busy_p': self.t_busy_p}
                    if fn == 'psc_sc_exit' and self.p_open is not None:
                        st['t_busy_p'] = 1 if idx == 0 else 0
                    elif fn == 'psc_syscon_cmd' and self.p_entry is not None:
                        # inlined psc_sc_entry: the barrier before the
                        # t_busy_p store (return address on that line) or the
                        # one after it (psc.c:240, :245)
                        src, ln = host_src_line(f[3] if f[3].startswith('0x') else '0x' + f[3])
                        if not (src == 'psc.c' and ln == TBUSY_LINE):
                            self.t_busy_p = 1
                        st['t_busy_p'] = self.t_busy_p
                    self.binj = st
                    binj_stack.append(st)
                elif k == 'PRINTK' and 'Joypad' in line:
                    pass
                elif k == 'DEVMODE':
                    self.devmode = int(f[1])
        # the osk queue opens at boot (jp_host_osk_open before the thread)
        return self


def build_model(evpath):
    m = Model()
    m.joy['osk_open'] = True
    return m.run(evpath)


# ------------------------------------------------------------ comparison
def compare(model, recs, scen, report):
    total = {'checked': 0, 'equal': 0, 'missing': 0, 'extra': 0}
    first_bad = []
    field_bad = {}
    kinds = {0: 'P', 1: 'POLL', 2: 'W', 3: 'S', 4: 'M'}
    for r in range(5):
        exp = model.exp[r]
        got = recs[r]
        kind = kinds[r]
        for d in exp:
            seq = d['seq']
            if seq not in got:
                total['missing'] += 1
                continue
            raw = got[seq]
            dd = {k: v for k, v in d.items() if not k.startswith('_')}
            try:
                want = DF.pack(kind, dd)
            except Exception as e:  # noqa: BLE001
                first_bad.append('%s seq %d: pack error %s' % (kind, seq, e))
                continue
            total['checked'] += 1
            if want == raw:
                total['equal'] += 1
                continue
            a = DF.unpack(kind, raw)
            diffs = [n for n in a if a[n] != dd.get(n)]
            for n in diffs:
                field_bad.setdefault((kind, n), 0)
                field_bad[(kind, n)] += 1
            if len(first_bad) < 12:
                first_bad.append('%s seq %d: %s' % (kind, seq, ', '.join('%s got %r want %r' % (n, a[n], dd.get(n))
                                                                           for n in diffs[:6])))
        extra = [s for s in got if s >= len(exp) or s < 0]
        total['extra'] += len(extra)
    return total, first_bad, field_bad


def check_stats(model, stats_chunks):
    """compare the STATS chunks (snapshots, in order) with the model's
    counters at the matching stats reads"""
    probs = []
    n = 0
    snaps = {s['now_tick'] * 10000000 + s['now_count']: s for s in model.stats_snaps}
    for st in stats_chunks:
        key = st[7] * 10000000 + st[8]
        s = snaps.get(key)
        if s is None:
            probs.append('stats chunk at tick %d: no matching stats read' % st[7])
            continue
        n += 1
        want = {
            'head P': (st[14], s['head'][0]), 'head POLL': (st[15], s['head'][1]), 'head W': (st[16], s['head'][2]),
            'head S': (st[17], s['head'][3]), 'head M': (st[18], s['head'][4]), 'm_dropped': (st[19], s['m_dropped']),
            'wd_calls': (st[27], s['wd_calls']), 'wd_last_tick': (st[28], s['wd_last_tick']),
            'p_nested': (st[29], s['p_nested']), 'p_ticked': (st[30], s['p_ticked']),
            'oc_p08': (list(st[31:38]), s['oc_p08']), 'oc_p33': (list(st[38:45]), s['oc_p33']),
            'oc_w': (list(st[45:52]), s['oc_w']), 'jp_loop': (st[53], s['jp_loop']),
            'jp_r3..r5': (list(st[68:71]), s['jp_r']),
            'led_calls': (st[100], s['led_calls']), 'led_or_set_run': (st[102], s['led_or_set_run']),
            'led_or_clr_run': (st[103], s['led_or_clr_run']), 'ms_seg_wr': (st[104], s['ms_seg_wr']),
            'total_counts': (st[10] | (st[11] << 32), s['total_counts']), 'c_pre_max': (st[12], s['c_pre_max']),
            'long_ticks': (st[13], s['long_ticks']), 'durable_tick': (st[112], s['durable_tick']),
            'lc_nested': (st[124], s['lc_nested']), 'panel_paints': (st[119], s['panel_paints']),
            'panel_test_done': (st[122], s['panel_test_done']), 'proc_opens': (st[23], s['proc_opens']),
            'magic': (st[0], 0x54535350), 'version_size': (st[1], (768 << 16) | 5), 'build_id': (st[2], 0x045b27d9),
            'hz': (st[3], 250), 'cpt': (st[4], CPT), 'addr Syscon_cmd': (st[20], 0x880ceed0),
            'addr psc_sc_exit': (st[21], 0x880d2b04), 'addr GetCtrl2': (st[22], 0x880cf370),
            'slot_bad': (list(st[128:133]), [0] * 5), 'head_regress': (st[127], 0),
        }
        for k, (a, b) in want.items():
            if a != b:
                probs.append('stats at tick %d: %s = %r, model %r' % (st[7], k, a, b))
    return n, probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', required=True)
    ap.add_argument('--dumps', required=True)
    ap.add_argument('--syms')
    ap.add_argument('scenarios', nargs='+')
    a = ap.parse_args()
    global EXE, TBUSY_LINE
    if a.syms:
        EXE = a.syms[:-5] if a.syms.endswith('.syms') else a.syms
    TBUSY_LINE = tbusy_set_line()
    fails = 0
    p = DF.self_check()
    q, counts = design_tables_check()
    print('DESIGN 1.x tables (machine-extracted from DESIGN.md, rows %s) vs design_format.py and the 10.3 strings: %s'
          % (counts, 'OK' if not (p or q) else (p + q)))
    if p or q:
        fails += 1
    grand = {'checked': 0, 'equal': 0, 'missing': 0}
    for scen in a.scenarios:
        evp = os.path.join(a.events, scen + '.log')
        dumpdir = os.path.join(a.dumps, scen)
        nonce = None
        with open(evp) as fi:
            m0 = re.search(r'nonce ([0-9a-f]+)', fi.readline())
            nonce = int(m0.group(1), 16)
        model = build_model(evp)
        recs, stats, uhb, events, probs, files = parse_dump(os.path.join(dumpdir, 'PSCLOG'), nonce)
        tot, bad, fb = compare(model, recs, scen, None)
        nst, sprobs = check_stats(model, stats)
        nrec = {RING_NAME[r]: len(recs[r]) for r in range(5)}
        nexp = {RING_NAME[r]: len(model.exp[r]) for r in range(5)}
        # records produced after the last flush are lost at the pull
        tail = {RING_NAME[r]: len(model.exp[r]) - len(recs[r]) for r in range(5)}
        ok = tot['checked'] == tot['equal'] and not probs and not sprobs and \
            all(v >= 0 for v in tail.values())
        missing_not_tail = 0
        for r in range(5):
            seqs = sorted(recs[r])
            if seqs and seqs != list(range(seqs[0], seqs[-1] + 1)):
                missing_not_tail += 1
            if seqs and seqs[0] != 0:
                missing_not_tail += 1
        ok = ok and missing_not_tail == 0
        fails += 0 if ok else 1
        print('%-16s %s  records in dump %s; model %s; byte-equal %d of %d checked; stats chunks %d checked%s'
              % (scen, 'PASS' if ok else 'FAIL', nrec, nexp, tot['equal'], tot['checked'], nst,
                 '' if not missing_not_tail else '; SEQ GAPS'))
        for b in bad[:12]:
            print('    ' + b)
        for (k, n), c in sorted(fb.items()):
            print('    field %s.%s differs in %d records' % (k, n, c))
        for pr in (probs + sprobs)[:12]:
            print('    ' + pr)
        if len(probs + sprobs) > 12:
            print('    ... %d more' % (len(probs + sprobs) - 12))
        grand['checked'] += tot['checked']
        grand['equal'] += tot['equal']
    print('TOTAL records checked byte for byte: %d, equal: %d; scenarios failing: %d'
          % (grand['checked'], grand['equal'], fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
