"""design_format.py - the record layouts of DESIGN.md, typed in from the
DESIGN text (NOT from include/linux/psc_format.h and NOT from the decoder's
psc_format.py), so that the ring test checks the kernel's bytes against the
design itself.

Sources (handoff/design/DESIGN.md as of 2026-10-07):
  1.2 SC table          DESIGN.md:238-271   (offset, type, field)
  1.3 W extension table DESIGN.md:302-329
  1.4 POLL table        DESIGN.md:342-368
  1.5 S table           DESIGN.md:383-398
  10.3 struct strings   DESIGN.md:2147-2167
  10.2 chunk / block / FILEHDR / UHB strings DESIGN.md:2093-2115
"""
import struct

# (offset, struct code, name) per the DESIGN tables
SC_TABLE = [
    (0, 'I', 'seq'), (4, 'I', 'tick_in'), (8, 'I', 'c_in'), (12, 'I', 'c_out'),
    (16, 'H', 'dtick'), (18, 'B', 'cmd'), (19, 'B', 'txlen'), (20, 'h', 'ret'),
    (22, 'B', 'nwords'), (23, 'B', 'retries'), (24, 'I', 'ack_polls'),
    (28, 'H', 'drain'), (30, 'H', 'drain_last'), (32, 'H', 'gpio_in'),
    (34, 'H', 'spi_st9'), (36, 'H', 'spi_sttx'), (38, 'B', 'ctx'), (39, 'B', 'wn'),
    (40, 'H', 'w_head_lo'), (42, 'H', 'pre_wrk'), (44, 'B', 'pre_cls'),
    (45, 'B', 'ms_delta'), (46, 'B', 'pre_flags'), (47, 'B', 'preempt_delta'),
    (48, '16s', 'rx'), (64, 'I', 'lc_epc'), (68, 'H', 'lc_dtick'), (70, 'B', 'lc_n'),
    (71, 'B', 'lc_flags'), (72, 'I', 'led_or'), (76, 'H', 'led_pid'), (78, 'H', 'pre_tot'),
]
WEXT_TABLE = [   # offsets within the W record (1.3)
    (80, 'I', 'epc'), (84, 'I', 'cause'), (88, 'I', 'status'), (92, 'I', 'ra'),
    (96, 'I', 'sp'), (100, '16I', 'r'), (164, 'I', 'pid'), (168, 'I', 'p_head'),
    (172, 'I', 'jp_loop'), (176, 'I', 't_entry_tick'), (180, 'I', 't_entry_c'),
    (184, 'B', 't_busy'), (185, 'B', 'jp_stage'), (186, 'B', 'ext_flags'),
    (187, 'B', 'cur_pcnt'), (188, 'I', 'c_pre'), (192, 'I', 'lc_tick'),
    (196, 'I', 'lc_c_pre'), (200, 'I', 'lc_cmd_id'), (204, 'I', 'lc_epc'),
    (208, 'I', 'lc_cause'), (212, 'I', 'lc_ra'), (216, 'I', 'lc_sp'),
    (220, '16I', 'lc_r'), (284, 'H', 'lc_n'), (286, 'H', 'rsv'),
]
POLL_TABLE = [
    (0, 'I', 'seq'), (4, 'I', 'tick_start'), (8, 'I', 'c_start'), (12, 'I', 'c_end'),
    (16, 'H', 'sc_seq_lo'), (18, 'B', 'body_ticks'), (19, 'B', 'ri_branch'),
    (20, 'B', 'pi_flags'), (21, 'B', 'nqueues'), (22, 'B', 'push_ok'),
    (23, 'B', 'push_fail'), (24, 'B', 'mouse_flags'), (25, 'b', 'dx'), (26, 'b', 'dy'),
    (27, 'B', 'sig'), (28, 'B', 'period'), (29, 'B', 'preempt_delta'),
    (30, 'B', 'stage_max'), (31, 'B', 'nsc'), (32, 'H', 'wk_delay'), (34, 'H', 'wk_wrk'),
    (36, 'B', 'wk_cls0'), (37, 'B', 'wk_cls1'), (38, 'B', 'wk_nsw'), (39, 'B', 'rsv'),
]
S_TABLE = [
    (0, 'I', 'seq'), (4, 'I', 'tick_on'), (8, 'I', 'c_on'), (12, 'I', 'c_off'),
    (16, 'I', 'sector'), (20, 'H', 'dtick'), (22, 'H', 'pid'), (24, 'B', 'nsect'),
    (25, 'B', 'flags'), (26, 'H', 'p_head_lo'), (28, 'B', 'led_ops'),
    (29, 'B', 'rsv29'), (30, 'H', 'rsv30'), (32, 'I', 'rd_set_or'), (36, 'I', 'rd_clr_or'),
]

# DESIGN 10.3 strings (DESIGN.md:2148-2163), verbatim
SC_FMT = '<IIIIHBBhBBIHHHHHBBHHBBBB16sIHBBIHH'
WEXT_FMT = '<5I16I5IBBBB4I4I16IHH'
POLL_FMT = '<IIIIH7B2b5BHHBBBB'
S_FMT = '<IIIIIHHBBHBBHII'
# DESIGN 10.2 (DESIGN.md:2093, 2111, 2110, 2115)
CHUNK_FMT = '<4sHHIII'
BLOCK_FMT = '<BBHI'
FILEHDR_FMT = '<8sIIIIIIIII'
UHB_FMT = '<21I'
STATS_FMT = '<192I'

SIZES = {'SC': 80, 'WEXT': 208, 'W': 288, 'POLL': 40, 'S': 40, 'STATS': 768,
         'CHUNK': 20, 'BLOCK': 8, 'FILEHDR': 44, 'UHB': 84}


def _codes(fmt):
    """expand a struct format into one code per value"""
    out = []
    num = ''
    for ch in fmt[1:]:
        if ch.isdigit():
            num += ch
            continue
        n = int(num) if num else 1
        num = ''
        if ch == 's':
            out.append('%ds' % n)
        else:
            out.extend([ch] * n)
    return out


def table_codes(table):
    out = []
    for (_o, c, _n) in table:
        if c[0].isdigit() and c[-1] != 's':
            out.extend([c[-1]] * int(c[:-1]))
        else:
            out.append(c)
    return out


def table_offsets_ok(table, size, base=0):
    """the offsets in a DESIGN table are contiguous and add up to the size"""
    probs = []
    pos = base
    for (o, c, n) in table:
        if o != pos:
            probs.append('%s at %d, previous fields end at %d' % (n, o, pos))
        pos = o + struct.calcsize('<' + c)
    if pos != base + size:
        probs.append('table ends at %d, size %d' % (pos, base + size))
    return probs


def self_check():
    """DESIGN 1.x tables against DESIGN 10.3 strings: offsets, types, sizes."""
    probs = []
    for (name, table, fmt, size, base) in (
            ('SC', SC_TABLE, SC_FMT, 80, 0), ('WEXT', WEXT_TABLE, WEXT_FMT, 208, 80),
            ('POLL', POLL_TABLE, POLL_FMT, 40, 0), ('S', S_TABLE, S_FMT, 40, 0)):
        if struct.calcsize(fmt) != size:
            probs.append('%s: 10.3 string size %d != %d' % (name, struct.calcsize(fmt), size))
        probs += ['%s: %s' % (name, p) for p in table_offsets_ok(table, size, base)]
        if table_codes(table) != _codes(fmt):
            probs.append('%s: 1.x field types %s != 10.3 string %s' % (name, table_codes(table), _codes(fmt)))
    for (fmt, size) in ((CHUNK_FMT, 20), (BLOCK_FMT, 8), (FILEHDR_FMT, 44), (UHB_FMT, 84), (STATS_FMT, 768)):
        if struct.calcsize(fmt) != size:
            probs.append('%s size %d != %d' % (fmt, struct.calcsize(fmt), size))
    return probs


def names(table):
    out = []
    for (_o, c, n) in table:
        if c[0].isdigit() and c[-1] != 's':
            out.extend(['%s[%d]' % (n, i) for i in range(int(c[:-1]))])
        else:
            out.append(n)
    return out


SC_NAMES = names(SC_TABLE)
WEXT_NAMES = names(WEXT_TABLE)
POLL_NAMES = names(POLL_TABLE)
S_NAMES = names(S_TABLE)


def unpack(kind, raw):
    if kind in ('P', 'M'):
        return dict(zip(SC_NAMES, struct.unpack(SC_FMT, raw)))
    if kind == 'W':
        d = dict(zip(SC_NAMES, struct.unpack(SC_FMT, raw[:80])))
        d.update({'ext.' + k: v for k, v in zip(WEXT_NAMES, struct.unpack(WEXT_FMT, raw[80:]))})
        return d
    if kind == 'POLL':
        return dict(zip(POLL_NAMES, struct.unpack(POLL_FMT, raw)))
    if kind == 'S':
        return dict(zip(S_NAMES, struct.unpack(S_FMT, raw)))
    raise ValueError(kind)


def pack(kind, d):
    def vals(nm, dd, prefix=''):
        return [dd[prefix + n] for n in nm]
    if kind in ('P', 'M'):
        return struct.pack(SC_FMT, *vals(SC_NAMES, d))
    if kind == 'W':
        return struct.pack(SC_FMT, *vals(SC_NAMES, d)) + struct.pack(WEXT_FMT, *vals(WEXT_NAMES, d, 'ext.'))
    if kind == 'POLL':
        return struct.pack(POLL_FMT, *vals(POLL_NAMES, d))
    if kind == 'S':
        return struct.pack(S_FMT, *vals(S_NAMES, d))
    raise ValueError(kind)


if __name__ == '__main__':
    p = self_check()
    print('DESIGN 1.x tables vs 10.3 strings:', 'OK' if not p else p)
