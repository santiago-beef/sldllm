#!/usr/bin/env python3
"""summary.py - SUMMARY.txt from measure-output.json (Stage 3 closure)."""
import json
d = json.load(open('measure-output.json'))
s, a, g, h, f = d['scenarios'], d['added'], d['g3_low_gap'], d['thread_hooks'], d['fit']
US = 220.912896
L = []
w = L.append
w("Stage 3 closure re-measurement: summary of measure-output.json (python3 measure.py > measure-output.json; python3 summary.py)")
w("images: base vmlinux.bin %s ; new (release) vmlinux.bin %s = gunzip(vmlinux-0.22.bin 4f9b69dc...)"
  % (d['images']['base vmlinux.bin'][:16], d['images']['new vmlinux.bin'][:16]))
w("model: ACK after %d polls; replies 0x08 %d words, 0x33 %d, Nop %d; 1 instruction = 1 Count at %d Hz (UNVERIFIED)"
  % (d['model']['ack_polls'], d['model']['reply_08_words'], d['model']['reply_33_words'],
     d['model']['reply_nop_words'], d['model']['count_hz']))
w("")
w("THREAD PATH (warm; second call)          base  new   added  us    stack base->new")
for p in ('P08', 'P33'):
    b, n = s['base'][p][1], s['new'][p][1]
    w("%s before S5                            %4d  %4d  %+5d" % (p, b['before_s5'], n['before_s5'], n['before_s5'] - b['before_s5']))
    w("%s S5..S20 window                       %4d  %4d  %+5d" % (p, b['window_s5_s20'], n['window_s5_s20'], n['window_s5_s20'] - b['window_s5_s20']))
    w("%s after S20                            %4d  %4d  %+5d" % (p, b['after_s20'], n['after_s20'], n['after_s20'] - b['after_s20']))
    w("%s total                                %4d  %4d  %+5d  %.2f  %d->%d B (%+d)"
      % (p, b['total'], n['total'], n['total'] - b['total'], (n['total'] - b['total']) / US, b['stack_bytes'],
         n['stack_bytes'], n['stack_bytes'] - b['stack_bytes']))
    fn = n['by_function']
    w("%s new code by function: %s" % (p, ", ".join("%s %d" % (k, v) for k, v in fn.items()
                                                  if k not in ('Syscon_cmd', '_pspSysconGetCtrl2', 'pspSyscon_tx_dword'))))
    w("%s Syscon_cmd %d (base %d: +%d = hand-off and A2 store)"
      % (p, fn['Syscon_cmd'], s['base'][p][1]['by_function']['Syscon_cmd'],
         fn['Syscon_cmd'] - s['base'][p][1]['by_function']['Syscon_cmd']))
    w("%s new: entry->c_in %d, c_in->c_out %d (MMIO %d), c_out->t2 (p_rec_cost window) %d, t2->return %d, "
      "S20->c_out %d, c_in->S5 %d" % (p, n['entry_to_cin'], n['cin_to_cout'], n['mmio_cin_to_cout'], n['cout_to_t2'],
                                      n['t2_to_ret'], n['s20_to_cout'], n['cin_to_s5']))
w("")
w("TIMER INTERRUPT (plat_irq_dispatch entry to its call of irq_enter)")
for p in ('TICK', 'WD', 'WDP'):
    b, n = s['base'][p], s['new'][p]
    w("%-4s warm base %4d new %4d added %+5d (%.2f us); first of boot added %+d; stack below pt_regs %d->%d B (%+d)"
      % (p, b[1]['total'], n[1]['total'], a[p]['warm'], a[p]['warm_us'], a[p]['first'], b[1]['stack_below_ptregs'],
         n[1]['stack_below_ptregs'], a[p]['stack']))
    if 'before_nop_s5' in a[p]:
        w("     Nop: before its S5 %+d, its window %+d, after its S20 %+d"
          % (a[p]['before_nop_s5'], a[p]['nop_window'], a[p]['after_nop_s20']))
t = s['new']['T2D'][0]
w("T2D  new only (tick 125 mod 250, panel painting): %d instructions (%.0f us); stack below pt_regs %d B; "
  "VRAM stores %d in %s" % (t['total'], t['total'] / US, t['stack_below_ptregs'], t['vram_stores'], t['vram_bytes']))
w("     by function: psc_panel_fill %d (fixed), pspClearDcache %d (16 KB D-cache UNVERIFIED), psc_panel_t2d %d + "
  "pl_* %d (text, content-dependent)" % (t['by_function']['psc_panel_fill'], t['by_function']['pspClearDcache'],
                                         t['by_function']['psc_panel_t2d'],
                                         sum(v for k, v in t['by_function'].items() if k.startswith('pl_'))))
w("")
w("G3-LOW GAP (0x33 S20 store -> 0x08 S13 store): base %d instructions, new %d, added %+d (%.2f us); "
  "MMIO in the gap %d (latency m each)" % (g['base_instr'], g['new_instr'], g['added'], g['added_us'], g['mmio_in_gap']))
w("  of the new gap: recorded interval g = c_out(0x33)..c_in(0x08) %d instructions (p_rec_cost window %d); "
  "outside g %d (S20->c_out %d + c_in->S13 %d)" % (g['recorded_g_instr'], g['cout_to_t2_P33'], g['outside_g_instr'],
                                                   g['new_s20_to_cout_P33'], g['new_cin_to_s13_P08']))
w("  thread code between the calls: base 4, new 10 (thread-code-listing.txt)")
w("")
w("THREAD-SIDE HOOKS (the functions the kernel calls; the inline call code, ~16 instructions, read from the listing, not included)")
sw = h['psc_sched_switch_slow']
pr = h['psc_sched_switch_slow_preempted']
w("  psc_poll_begin %s; psc_poll_end %s; psc_sched_wake_slow %s" % (h['psc_poll_begin'], h['psc_poll_end'], h['psc_sched_wake_slow']))
w("  psc_sched_switch_slow: a switch while the thread waits %d, the switch-in of the thread %d, the thread's own "
  "switch-out to sleep %d" % (sw[0], sw[1], sw[2]))
w("  preempted inside a command: its switch-out %d, a switch while it is off the CPU %d, its switch-in %d" % tuple(pr))
st33 = 48 + h['psc_sched_wake_slow'][0] + sw[1] + h['psc_poll_begin'][1] + 7 + 16 + a['P33']['before_s5']
w("  start shift of the 0x33's S5 after the thread's wake-up tick: tick +48, wake %d, switch-in %d, poll_begin %d, "
  "loop top 7, inline ~16, entry +75 = %d (%.2f us); 0x08's S5: + %d = %d (%.2f us)"
  % (h['psc_sched_wake_slow'][0], sw[1], h['psc_poll_begin'][1], st33, st33 / US, g['added'], st33 + g['added'],
     (st33 + g['added']) / US))
pp = a['P08']['total'] + a['P33']['total'] + 6 + 7 + h['psc_poll_begin'][1] + h['psc_poll_end'][0] + \
    h['psc_sched_wake_slow'][0] + sw[1] + sw[2] + 16
w("  per poll (2 commands, stage code between and at loop top, poll_begin/end, wake-up, switch-in, switch-out, "
  "inline ~16): %d instructions (%.1f us), plus %d per switch while it waits" % (pp, pp / US, sw[0]))
w("")
w("K5 MMIO-BOUND MODEL (new build, c_in -> c_out of a clean P record, exact on 9 points each)")
for p in ('P08', 'P33'):
    ci = [int(x) for x in f[p]['I_coef_const_ack_nwords_rx1']]
    cn = [int(x) for x in f[p]['N_coef_const_ack_nwords_rx1']]
    w("  %s: I = %d + %d ack_polls + %d nwords + %d rx[1] (exact %s); N = %d + %d ack_polls + %d nwords (exact %s)"
      % (p, ci[0], ci[1], ci[2], ci[3], f[p]['I_fit_exact'], cn[0], cn[1], cn[2], f[p]['N_fit_exact']))
open('SUMMARY.txt', 'w').write("\n".join(L) + "\n")
print("\n".join(L))
