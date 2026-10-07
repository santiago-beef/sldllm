#!/usr/bin/env python3
"""signature.py - what each dump recorded around its onset / aimed Nop, read
back from the dump files (oracle/oracle.py parser). Adds an "observed"
section to <dump>/truth.json and prints the counts used in the ring-logic result.

  signature.py DUMPS_DIR EVENTS_DIR SCENARIO ...
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'oracle'))
import design_format as DF        # noqa: E402
import oracle as O                # noqa: E402

LABEL = {  # release epcmap (BUILD/epcmap.txt) for the EPCs the harness uses
    0x880cef90: 'S3', 0x880cefb0: 'S5', 0x880cefbc: 'S6', 0x880cefc0: 'S7', 0x880cefd4: 'S8',
    0x880cf020: 'S8', 0x880cf02c: 'S8', 0x880cf03c: 'S9', 0x880cf050: 'S10', 0x880cf064: 'S11',
    0x880cf084: 'S11', 0x880cf094: 'S12', 0x880cf098: 'S13', 0x880cf0a0: 'S14', 0x880cf0dc: 'S14',
    0x880cf0e4: 'S14', 0x880cf150: 'REC', 0x880cf21c: 'S15', 0x880cf220: 'S18', 0x880cf234: 'S18',
    0x880cf274: 'S19', 0x880cf278: 'S20',
}


def label(epc):
    if epc in LABEL:
        return LABEL[epc]
    if 0x880d2b04 <= epc < 0x880d3420:
        return 'psc_sc_exit'
    if 0x880d3c04 <= epc < 0x880d3d04:
        return 'psc_poll_end'
    if 0x880d3d04 <= epc < 0x880d3e80:
        return 'psc_ms_seg_end'
    if 0x880d22fc <= epc < 0x880d25cc:
        return 'psc_ring_read'
    return '0x%08x' % epc


def main():
    dumps, evdir = sys.argv[1], sys.argv[2]
    out = {}
    for scen in sys.argv[3:]:
        d = os.path.join(dumps, scen)
        evp = os.path.join(evdir, scen + '.log')
        with open(evp) as fi:
            nonce = int(re.search(r'nonce ([0-9a-f]+)', fi.readline()).group(1), 16)
        recs, stats, uhb, events, probs, files = O.parse_dump(os.path.join(d, 'PSCLOG'), nonce)
        truth = json.load(open(os.path.join(d, 'truth.json')))
        onset = truth.get('onset_tick', -1)
        P = {s: DF.unpack('P', r) for s, r in recs[0].items()}
        POLL = {s: DF.unpack('POLL', r) for s, r in recs[1].items()}
        W = {s: DF.unpack('W', r) for s, r in recs[2].items()}
        obs = {'files': [os.path.basename(f) for f in files],
               'records': {O.RING_NAME[r]: len(recs[r]) for r in range(5)},
               'seq_ranges': {O.RING_NAME[r]: [min(recs[r]), max(recs[r])] if recs[r] else None for r in range(5)},
               'block_lost_total': 0}
        # straddles: W records with a P command in flight
        st = []
        for s, w in sorted(W.items()):
            if w['ext.t_busy'] & 1:
                ph = w['ext.p_head']
                p = P.get(ph)
                st.append({'W_seq': s, 'tick': w['tick_in'], 'epc': '0x%08x' % w['ext.epc'],
                           'step': label(w['ext.epc']), 'ext_flags': '0x%02x' % w['ext.ext_flags'],
                           'W_ret': w['ret'], 'W_nwords': w['nwords'], 'W_ack_polls': w['ack_polls'],
                           'W_drain': w['drain'], 'W_gpio_in': '0x%04x' % w['gpio_in'],
                           'W_rx': w['rx'].hex(),
                           'P_seq': ph, 'P_cmd': '0x%02x' % p['cmd'] if p else None,
                           'P_ret': p['ret'] if p else None, 'P_nwords': p['nwords'] if p else None,
                           'P_wn': p['wn'] if p else None, 'P_ack_polls': p['ack_polls'] if p else None,
                           'P_rx': p['rx'].hex() if p else None})
        obs['straddles'] = st
        if onset >= 0:
            post08 = [p for p in P.values() if p['cmd'] == 0x08 and p['tick_in'] >= onset]
            pre08 = [p for p in P.values() if p['cmd'] == 0x08 and p['tick_in'] < onset]
            post33 = [p for p in P.values() if p['cmd'] == 0x33 and p['tick_in'] >= onset]
            postpoll = [p for p in POLL.values() if p['tick_start'] >= onset]
            postW = [w for w in W.values() if w['tick_in'] >= onset]
            obs['after_onset'] = {
                'P08': len(post08), 'P33': len(post33), 'POLL': len(postpoll), 'W': len(postW),
                'P08_ret': dict(Counter(p['ret'] for p in post08)),
                'P08_nwords': dict(Counter(p['nwords'] for p in post08)),
                'P08_rx2': dict(Counter('0x%02x' % p['rx'][2] for p in post08)),
                'P08_ack_polls_0': sum(1 for p in post08 if p['ack_polls'] == 0),
                'P08_drain_gt0': sum(1 for p in post08 if p['drain']),
                'P08_gpio_in': dict(Counter('0x%04x' % p['gpio_in'] for p in post08)),
                'P08_distinct_key_bytes': len(set(p['rx'][3:9] for p in post08)),
                'P08_retries16': sum(1 for p in post08 if p['retries'] == 16),
                'P08_lc_n_ge12': sum(1 for p in post08 if p['lc_n'] >= 12),
                'P33_ret': dict(Counter(p['ret'] for p in post33)),
                'W_ret': dict(Counter(w['ret'] for w in postW)),
                'POLL_ri_branch': dict(Counter(p['ri_branch'] for p in postpoll)),
                'POLL_dedupe': sum(1 for p in postpoll if p['pi_flags'] & 0x02),
                'POLL_push_ok': sum(p['push_ok'] for p in postpoll),
                'POLL_push_fail_full': sum(p['push_fail'] & 0xF for p in postpoll),
                'POLL_mouse_reported': sum(1 for p in postpoll if p['mouse_flags'] & 0x08),
                'POLL_dx_dy_16': sum(1 for p in postpoll if p['dx'] == 16 and p['dy'] == 16),
                'P08_before_onset': len(pre08),
                'P08_ret_before': dict(Counter(p['ret'] for p in pre08)),
            }
        if stats:
            last = stats[-1]
            obs['last_stats'] = {'tick': last[7], 'jp_push_full': last[78], 'jp_push_ok': last[77],
                                 'fop_read_ret': last[87], 'md_event_syn': last[97], 'md_read_ret': last[99],
                                 'vcs_putchar': last[93], 'jp_r3_r4_r5': list(last[68:71]),
                                 'led_calls': last[100], 'wd_calls': last[27], 'oc_p08': list(last[31:38]),
                                 'panel_paints': last[119], 'slot_bad': list(last[128:133]),
                                 'head_regress': last[127], 'durable_tick': last[112]}
        obs['uhb_mouse_pkts_total'] = uhb[-1][6] if uhb else None
        obs['events'] = [e for e in events if 'segment' in e or 'switch' in e][:6]
        truth['observed'] = obs
        with open(os.path.join(d, 'truth.json'), 'w') as fo:
            json.dump(truth, fo, indent=1)
        out[scen] = obs
        a = obs.get('after_onset', {})
        print('%-15s rec %s straddles %d %s' % (scen, obs['records'], len(st),
                                                 ('| ' + ', '.join('%s=%s' % (k, a[k]) for k in
                                                  ('P08_ret', 'P08_nwords', 'P08_rx2', 'POLL_ri_branch',
                                                   'POLL_push_fail_full', 'P08_ack_polls_0', 'P08_gpio_in',
                                                   'P08_distinct_key_bytes'))) if a else ''))
        for s in st:
            print('      straddle W%d tick %d step %s: W ret %d nw %d ack %d drain %d gpio %s | P%d %s ret %s nw %s wn %s'
                  % (s['W_seq'], s['tick'], s['step'], s['W_ret'], s['W_nwords'], s['W_ack_polls'], s['W_drain'],
                     s['W_gpio_in'], s['P_seq'], s['P_cmd'], s['P_ret'], s['P_nwords'], s['P_wn']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
