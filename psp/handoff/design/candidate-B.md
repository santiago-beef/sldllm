# Candidate B: maximum-coverage instrumentation design

Stage 1 design, Designer role, 2026-09-30. Angle: **maximum coverage**. The
design assumes the failure has a shape nobody has listed (H0). It records
every syscon transaction in every context, with raw bytes and the register
values the unmodified code already loads. It records every stage from
`Syscon_cmd` entry to `input_sync` and the userland readers above it, with
counters and a per-poll record. Everything is streamed to the Memory Stick
continuously. There is no trigger and no freeze. The runbook is
`design/candidate-B-RUNBOOK.md`, which becomes `design/RUNBOOK.md` if this
candidate is chosen. It is written under a candidate name so that it does not
overwrite another designer's file.

Paths are relative to `/home/ubuntu/psp/build/linux` unless they start with
`/`. Labels: **[SRC]** means read in the source, with file:line.
**UNVERIFIED** means a guess or a hardware fact that the source does not settle.
Every UNVERIFIED item is listed again in section 11.

**Dossier 9.6 (H4 leading) is covered explicitly.** Every thread-context
command record says whether a watchdog command ran during it, and at which of
the recon interruption points P0 to P7 (`recon/syscon.md` §5.1). Every
watchdog command record names the thread command it interrupted and that
command's phase. Timestamps use a tick counter equal to the watchdog's own
counter, so the "exact phase is unknown" caveat of 9.6 goes away. See 1.2,
2.1 and 6 (row H4).

---

## 0. Architecture in one page

```
 Syscon_cmd (syscon.c:61)      timer IRQ (psp.c:348)        MS sector I/O (ms_psp.c:284,306)
   capture into a per-context  tick++, tick length,         M record per sector attempt,
   scratch; phase byte at      wd flag, 1 Hz SNAP           with the value read by the LED
   each step                        |                        read-modify-write
   |            |                   |                            |
   | JOY        | WD/BOOT           |                            |
   v            v                   v                            v
 [TSC ring]  [W ring] <-------------+                        [M ring]      [O ring] other threads
 [TPOLL ring] <- joypad thread: per-poll record (read_input -> process_input -> mouse -> input_sync)
 counters and histograms (single writer per word) <- joypad fops, vc_screen ioctl, mousedev, printk.c
                     \______________________ /proc/psptrace/{stream,counters,status} ___/
                                                  |
             /usr/bin/psptrace (supervisor, started from rc.sysinit) -> vfork/exec worker
             worker, per ~0.23 s tick (same cadence and load as telem):
                  drain stream + counters + /proc/kmsg + /proc/<pid>/stat
                  -> CRC-framed append to /ms0/PSPTRACE/Rrrr_ii.BIN, fsync
                  -> full-screen HUD (self-test, live raw button word, errors)
```

Five rings, each with exactly one writer context. No locks, no IRQ masking,
no atomics, no new MMIO access and no new syscon command anywhere on the
syscon path.

---

## 1. Record format

All multi-byte fields are little-endian (mipsel). Every record starts with the
same 8-byte header and ends with a 16-bit check word. Offsets are in bytes. The
Python `struct` strings in section 10 were checked with `struct.calcsize`.

### 1.0 Common header and check word

| Off | Size | Field | Meaning |
|---|---|---|---|
| 0 | 1 | `type` | 0x01 SC, 0x02 POLL, 0x03 SNAP, 0x04 MSIO |
| 1 | 1 | `ring` | 0 TSC, 1 TPOLL, 2 W, 3 M, 4 O |
| 2 | 2 | `len` | record length in bytes (144, 64, 128, 48) |
| 4 | 4 | `seq` | sequence number within `ring`, from 0, +1 per record. Written last before publication (3.3). |

**Check word** (last 2 bytes of every record): let `x` be the XOR of all
32-bit little-endian words of the record except the last one, XORed with the
low 16 bits of the last word. Then `check = ((x ^ (x >> 16)) & 0xFFFF) ^ 0xA55A`.
It detects torn or overwritten records. It costs about 40 instructions and is
computed by the writer at append time, outside any transaction window (7.2).

### 1.1 Encodings used by several records

**Origin** (`origin`, 1 byte). This is decided at `Syscon_cmd` entry, in this
order:

| Code | Name | Rule | Why it works although `in_interrupt()` is false (dossier 9.1) |
|---|---|---|---|
| 1 | WD | `psptrace_wd_active != 0` | A flag set by `psp_watchdog_tick` immediately before `psp_pacify_watchdog()` (`psp.c:379`) and cleared after it. It is set only with IRQs off, and the Nop cannot be nested or interrupted (`recon/syscon.md` §2.3), so the flag is exactly "inside the watchdog command". |
| 2 | IRQOFF | otherwise, CP0 Status.IE (bit 0) is 0 | The boot Nop from `prom_init` (`psp.c:557`) runs with IRQs disabled (`recon/syscon.md` §2.1 C2). |
| 0 | JOY | otherwise, `current == psptrace_joy_task` | The joypad thread sets `psptrace_joy_task = current` as the first statement of `psp_joypad_thread` (`joypad_psp.c:453-458`). |
| 3 | OTHER | otherwise | `pspSysconCtrlHRPower` (`serial_psp.c:352`), `pspSysconPowerStandby` (`psp.c:218`), anything unforeseen. |

The raw indicators are recorded too (`ctxbits`), so the decoder can check the
classification rather than trust it:

| Bit | `ctxbits` |
|---|---|
| b0 | CP0 Status.IE at entry (`read_c0_status() & 1`, `include/asm-mips/mipsregs.h:810`) |
| b1 | `psptrace_wd_active` |
| b2 | `in_interrupt() != 0` (expected 0 in WD, per dossier 9.1) |
| b3 | `current == psptrace_joy_task` (can be 1 in WD: the Nop runs on the interrupted task's stack, `recon/syscon.md` §2.3) |
| b4 | `signal_pending(current)` (JOY and OTHER only) |
| b5 | `preempt_count() != 0` |
| b6 | record was held in the JOY scratch and appended after the poll's commands (2.3) |
| b7 | incomplete: an in-flight copy exported through `/proc/psptrace/counters` (3.5), not a finished record |

**Phase byte** (`phase`). The high nibble is the step, the low nibble is the
attempt index (0 to 15) or, in step 7, the number of RX words read so far.
Steps map one to one onto the recon interruption points (`recon/syscon.md`
§5.1). The phase byte is written with a single `sb`, so every reader sees
either the old or the new value.

| Step | Name | Set at | Recon point |
|---|---|---|---|
| 0 | IDLE | after the record is finished, before `return` | not in `Syscon_cmd` |
| 1 | ENTRY | `retry:` (`syscon.c:75`), each attempt | P0 (S1-S4) |
| 2 | G3LO | after S6 `REG32(0xbe24000c) = 0x08` (`syscon.c:104`) | P1 (S5-S10) |
| 3 | TXPART | after the first TX push (`syscon.c:132`, first iteration) | P2 |
| 4 | TXDONE | after S12 `REG32(0xbe580004) = 6` (`syscon.c:136`) | P3 |
| 5 | ACKWAIT | after S13 `REG32(0xbe240008) = 0x08` (`syscon.c:140`) | P4 / P5a |
| 6 | ACKSEEN | after the ACK loop exits (`syscon.c:156`), before S15 | P5b |
| 7 | RX | after S15 (`syscon.c:159`); low nibble = words read | P6 |
| 8 | RXDONE | after S19 `REG32(0xbe580004) = 4` (`syscon.c:219`) | P7 |
| 9 | POST | after S20 `REG32(0xbe24000c) = 0x08` (`syscon.c:222`), and on the -4 path after its own teardown (`syscon.c:154`) | P0 (S21-S23) |
| 10 | EXIT | building the record | P0 |

P4 and P5a (whether the syscon had already raised its ACK when the watchdog
struck) are told apart by `r_gpio04` bit 4 in the **watchdog's** record. That
value is the GPIO4 input level sampled by the watchdog's own existing S5 read
(`syscon.c:102`), as the commented debug line `&0x18` at `syscon.c:146,155`
suggests. The meaning of that bit is UNVERIFIED (section 11).

**Exit code** (`exit`). These follow `recon/syscon.md` §1.3 and are computed
from values already in hand, with no extra buffer reads:

| Code | Condition | Return |
|---|---|---|
| 1 E1 | drain loop budget exhausted (`syscon.c:113`) | -3 |
| 2 E2 | ACK loop budget exhausted (`syscon.c:154`) | -4 |
| 3 E3 | receive loop read 0 words | 0 |
| 4 E4 | ≥1 word, `rx[0] == 0` | 0 |
| 5 E5 | `rx[0] != 0`, `rx[1] < 3` (`syscon.c:229-231`) | -2 |
| 6 E6 | `rx[0] != 0`, `rx[1] >= 3`, result -2 (`syscon.c:240-243`) | -2 |
| 7 E7 | `rx[0] != 0`, checksum passed | 1..255 |
| 8 E8 | 16th attempt with `rx[2]` in {0x80,0x81} (`syscon.c:249-254`) | -5 |

### 1.2 Timestamps

- `psptrace_tick` (u32) is incremented in `psp_cputimer_handler`
  **immediately after** the Count reset (`psp.c:352`) and before
  `psp_watchdog_tick()` (`psp.c:359`). It starts at 0.
  `psp_watchdog_tick`'s `localTick` also starts at 0 and is incremented once
  per handler (`psp.c:372,375`), so `psptrace_tick == localTick` after every
  handler. **The watchdog Nop therefore runs at exactly
  `psptrace_tick == 1250·k`** (`psp.c:376`). The decoder checks this on every
  WD record and reports any deviation (10.4).
- **Sub-tick time** is CP0 Count (`read_c0_count()`,
  `include/asm-mips/mipsregs.h:789`), which is zeroed as the first action of
  each timer handler (`psp.c:352`). `(tick, Count)` is a monotone clock. At
  220,912,896 counts/s (`psp.c:38`, "measured by tests", UNVERIFIED) one count
  is about 4.5 ns.
- **The Count/jiffies ordering caveat (dossier 9.1, `recon/syscon.md` §6
  caveat 1) is removed by construction.** `psptrace_tick` advances in the same
  handler instruction window that zeroes Count, before the watchdog runs. A WD
  record reads `(k, small)`. The thread activity it interrupted reads
  `(k-1, large)`. The two sort in true order. `jiffies` (which lags by one tick
  inside the handler until `do_timer`) is recorded only as a cross-check
  (`jif_in`).
- **Torn reads in thread context** (`recon/syscon.md` §6 caveat 2). Entry and
  exit stamps use `ts_read()`: `do { t1 = tick; c = Count; t2 = tick; } while (t1 != t2)`.
  This is bounded (it can repeat only if a tick lands inside a 3-instruction
  window) and masks nothing. Stamps inside the transaction window (`cnt_g3hi`,
  `cnt_ack`, `cnt_s20`) are a single `mfc0` plus one tick load, stored as Count
  plus a tick delta, which keeps the window cheap. A tear there is at most ±1
  tick, and the decoder resolves it by monotonicity.
- **Tick length and lost ticks** (`recon/syscon.md` §6 caveat 3). The timer
  handler reads Count **before** zeroing it (one extra `mfc0` ahead of
  `mtc0 $0,$9` at `psp.c:352`). That value is the true length of the tick that
  just ended, handler latency included, and it stays correct even when ticks
  are lost, because it covers everything since the previous reset. It is kept
  as `tick_len_last`, a max, a count of ticks longer than 1.5× nominal
  (883,651 counts, `psp.c:39`), and a 64-bit sum (`total_counts`). The sum is
  the elapsed wall time since the first tick in counts, independent of lost
  ticks.
- **Alignment with the 1250-tick cycle:** `wdph = tick mod 1250` plus
  `Count/883651`. For each record the decoder also reports
  `(tick, Count) - (tick, Count)` of the nearest WD Nop record.

### 1.3 SC record: one per `Syscon_cmd` call (type 0x01, 144 bytes)

Rings: TSC (origin JOY), W (origin WD and IRQOFF), O (origin OTHER). The
values in the "reg" rows are the values of loads the **unmodified code already
performs**, at the same point and in the same order (see 2.2 and D11).

| Off | Size | Field | Source |
|---|---|---|---|
| 0 | 8 | header | 1.0 |
| 8 | 4 | `tick_in` | `ts_read()` at entry, before `retry:` (`syscon.c:75`) |
| 12 | 4 | `cnt_in` | same |
| 16 | 4 | `tick_out` | `ts_read()` just before `return` (`syscon.c:257`, and the -3/-4 returns `:113,:154`) |
| 20 | 4 | `cnt_out` | same |
| 24 | 4 | `jif_in` | raw `jiffies` at entry |
| 28 | 4 | `tick_len` | `tick_len_last` at entry (length of the tick before `tick_in`, counts) |
| 32 | 1 | `origin` | 1.1 |
| 33 | 1 | `ctxbits` | 1.1 |
| 34 | 2 | `pid` | `current->pid` (low 16 bits) |
| 36 | 8 | `tx[0..7]` | `tx_buf[0..7]` after checksum and pad (`syscon.c:81,84`), last attempt |
| 44 | 16 | `rx[0..15]` | `rx_buf[0..15]` at return: **raw, full buffer** |
| 60 | 2 | `result` (s16) | return value (-5..255) |
| 62 | 1 | `exit` | 1.1 |
| 63 | 1 | `nwords` | words read by the receive loop (`syscon.c:202-217`), last attempt, 0..8 |
| 64 | 1 | `attempts` | 1..16 (retries via `syscon.c:253`) |
| 65 | 1 | `phase_last` | highest step reached in the last attempt (e.g. 0x5a on -4) |
| 66 | 1 | `first_exit` | exit code of attempt 1 (equals `exit` if `attempts == 1`) |
| 67 | 1 | `first_rx2` | `rx_buf[2]` of attempt 1 |
| 68 | 2 | `exits_mask` | bit e set if any attempt ended with exit condition e |
| 70 | 1 | `wd_during` / `intr_origin` | JOY/OTHER: number of WD Nops that ran while this command was in flight (saturating). WD/IRQOFF: origin of the command it interrupted (0 JOY, 3 OTHER, 0xFF none) |
| 71 | 1 | `wd_hit_phase` / `intr_phase` | JOY/OTHER: phase byte this command was in when the last such Nop began. WD: phase byte of the interrupted command at Nop entry (0 = idle) |
| 72 | 4 | `cmd_id` | per-origin counter, assigned at entry |
| 76 | 4 | `link` | JOY: `joy_loop` at entry. WD: `cmd_id` of the interrupted JOY command, or 0xFFFFFFFF |
| 80 | 4 | `ack_spins` | `SYSCON_SPIN_MAX - spin` after the ACK loop (`syscon.c:151-156`), last attempt. 1,000,001 on -4 |
| 84 | 4 | `drain_n` | words drained by S8 (`syscon.c:110-116`), last attempt. 1,000,001 on -3 |
| 88 | 4 | `drained0` | value of the first `REG32(0xbe580008)` load in the drain loop (`syscon.c:114`), 0 if none |
| 92 | 4 | `drained1` | second such load |
| 96 | 4 | `r_gpio04` | value of the load `REG32(0xbe240004)` (`syscon.c:102`), last attempt |
| 100 | 4 | `r_spi0c_s7` | value of the load in `if(REG32(0xbe58000c) & 4)` (`syscon.c:106`) |
| 104 | 4 | `r_spi0c_s9` | value of `dmy = REG32(0xbe58000c)` (`syscon.c:119`) |
| 108 | 4 | `r_spi0c_tx0` | value of the first `dmy = REG32(0xbe58000c)` in the TX loop (`syscon.c:130`) |
| 112 | 4 | `r_g20_first` | first load of `REG32(0xbe240020)` in the ACK loop (`syscon.c:152`) |
| 116 | 4 | `r_g20_last` | last load in that loop (the one that saw bit 4, or the last before -4) |
| 120 | 4 | `r_spi0c_rxend` | the status load that ended the receive loop (`syscon.c:204`), 0xFFFFFFFF if the loop ran 8 words |
| 124 | 4 | `cnt_g3hi` | Count just before S13 (`syscon.c:140`), last attempt |
| 128 | 4 | `cnt_ack` | Count just after the ACK loop exit (`syscon.c:156`), 0 on -3/-4 |
| 132 | 4 | `cnt_s20` | Count just after S20 (`syscon.c:222`), or after the -4 teardown |
| 136 | 2 | `preempt_delta` | `current->nivcsw` at exit minus at entry (JOY/OTHER; 0 for WD). Involuntary switches only, `kernel/sched.c:3626-3628`, field `include/linux/sched.h:907`. Non-zero means **the thread was preempted mid-command** |
| 138 | 1 | `dtick_g3hi` | tick at `cnt_g3hi` minus `tick_in` (saturating) |
| 139 | 1 | `dtick_ack` | tick at `cnt_ack` minus `tick_in` |
| 140 | 1 | `dtick_s20` | tick at `cnt_s20` minus `tick_in` |
| 141 | 1 | reserved | 0 |
| 142 | 2 | `check` | 1.0 |

Derived by the decoder, not stored: command duration, ACK latency
(`cnt_ack - cnt_g3hi`), and the **G3-low gap** between consecutive JOY
commands (`cnt_g3hi` of command n+1 minus `cnt_s20` of command n, across
ticks). The gap is the interval the commented-out `Syscon_wait(5)` guarded
(`syscon.c:95-97,142-144`). See 7.2.

### 1.4 POLL record: one per joypad loop iteration (type 0x02, 64 bytes, ring TPOLL)

| Off | Size | Field | Source |
|---|---|---|---|
| 0 | 8 | header | |
| 8 | 4 | `tick_start` | `ts_read()` at loop top (`joypad_psp.c:458`) |
| 12 | 4 | `cnt_start` | same |
| 16 | 4 | `loop` | `joy_loop` (incremented at loop top) |
| 20 | 4 | `keys_raw` | `keys` as written by `_pspSysconGetCtrl2` (`syscon.c:363`, before the inversion at `joypad_psp.c:490`). 0 if not reached |
| 24 | 1 | `x` | `*px_` (`syscon.c:364`) |
| 25 | 1 | `y` | `*py_` (`syscon.c:365`) |
| 26 | 1 | `ri_branch` | 1 = R1 (`:483-484`), 3 = R3 GetCtrl2 < 0 (`:487-488`), 4 = R4 HOLD (`:492-493`), 5 = R5 TRUE (`:495`) |
| 27 | 1 | `pi_flags` | b0 `process_input` called; b1 returned at dedupe (`:512-513`); b2 `console_blanked` was true at `psp_lcd_on` (`psp.c:259`); b3 SELECT toggle executed (`:521-522`); b4 `mouseMode` after; b5 `list_sem` acquired (`:530`); b6 `wake_up_interruptible` called (`:538`); b7 `list_sem` down failed |
| 28 | 1 | `nqueues` | queues walked (`:532-535`) |
| 29 | 1 | `push_ok` | `queue_push` returned TRUE (`:409-410`) |
| 30 | 1 | `push_full` | returned at full (`:395-399`) |
| 31 | 1 | `push_eintr` | returned at `down_interruptible` failure (`:390-393`) |
| 32 | 4 | `keys_pi` | `keys_` as stored to `s_psp_joypad_keys` (`:527`), 0 if not reached |
| 36 | 1 | `mouse_flags` | b0 called (`:464-465`); b1 M1 no device (`:609-610`); b2 M2 no-op (`:639-645`); b3 reported (`:651-658`); b4 left; b5 mid; b6 right |
| 37 | 1 | `dx` (s8) | `dx` passed to REL_X (`:651`) |
| 38 | 1 | `dy` (s8) | `dy` (REL_Y is `-dy`, `:652`) |
| 39 | 1 | `sig` | b0 `signal_pending(current)`; b1 TIF_SIGPENDING raw; b2 pending set non-empty |
| 40 | 4 | `cmd_id_first` | `cmd_id` of the first JOY SC in this poll |
| 44 | 1 | `nsc` | number of JOY SC records in this poll (normally 2) |
| 45 | 1 | `stage_max` | highest `joy_stage` reached (2.4) |
| 46 | 2 | `preempt_delta` | `current->nivcsw` delta over the loop body |
| 48 | 4 | `tick_end` | `ts_read()` just before `msleep` (`:468`) |
| 52 | 4 | `cnt_end` | same |
| 56 | 2 | `period` | `tick_start` minus the previous `tick_start` (nominal 14, `recon/input.md` §4) |
| 58 | 1 | `ast_res` (s8) | `_pspSysconCtrlAStickPower` result, clamped to -128..127 (discarded by the driver at `:486`) |
| 59 | 1 | `gc2_res` (s8) | `_pspSysconGetCtrl2` result, clamped |
| 60 | 2 | reserved | 0 |
| 62 | 2 | `check` | |

### 1.5 SNAP record: 1 Hz state snapshot from the timer interrupt (type 0x03, 128 bytes, ring W)

Written by `psp_cputimer_handler` when `psptrace_tick % 250 == 125`, so never
on a watchdog tick (those are ≡ 0 mod 250). It reads memory only. It makes the
state above the syscon visible at 1 Hz even if the thread or the collector is
stuck.

| Off | Size | Field |
|---|---|---|
| 0 | 8 | header |
| 8 | 12 | `tick`, `cnt`, `jiffies` |
| 20 | 4 | `joy_loop` |
| 24 | 1 | `joy_stage` (2.4) |
| 25 | 1 | `joy_phase` (phase byte of the JOY context) |
| 26 | 1 | `joy_state` (`psptrace_joy_task->state`, low byte) |
| 27 | 1 | `joy_sig` (as POLL `sig`, sampled for the joypad task) |
| 28 | 4 | `joy_stage_arg` (queue pointer for stages 11-12) |
| 32 | 4 | `joy_sigword` (`task->pending.signal.sig[0]`, raw) |
| 36 | 16 | ring heads: TSC, TPOLL, W, M |
| 52 | 4 | ring head O |
| 56 | 16 | `gc2_calls`, `gc2_neg`, `ri_hold`, `ri_true` |
| 72 | 16 | `pi_changed`, `push_ok`, `push_full + push_eintr`, `mouse_reports` |
| 88 | 16 | `fop_read_ret`, `vcs_putchar`, `md_notify_calls`, `md_read_ret` |
| 104 | 4 | `console_sem_count` (s16), `list_sem_count` (s16) |
| 108 | 4 | `qfree_stage` (u8), `console_blanked` (u8), `nop_count` low 16 |
| 112 | 4 | `tick_len_max` since the previous SNAP |
| 116 | 4 | `long_ticks` (cumulative) |
| 120 | 4 | `reader_last_tick` (tick of the last `/proc/psptrace/stream` read) |
| 124 | 2 | `append_cost_last` (Count delta of the most recent SC append, measured in place) |
| 126 | 2 | `check` |

### 1.6 MSIO record: one per Memory Stick sector attempt (type 0x04, 48 bytes, ring M)

Written in `psp_ms_read_sector` and `psp_ms_write_sector` around each
`psp_led_ctrl` pair (`ms_psp.c:290-292`, `:312-314`).

| Off | Size | Field |
|---|---|---|
| 0 | 8 | header |
| 8 | 4 | `tick_on` (just before LED on) |
| 12 | 4 | `cnt_on` |
| 16 | 4 | `cnt_off` (just after LED off) |
| 20 | 4 | `sector` |
| 24 | 4 | `set_rd`: the value **loaded** by the read-modify-write `PSP_GPIO_SET |= mask_` (`psp.c:401`) |
| 28 | 4 | `clr_rd`: the value loaded by `PSP_GPIO_CLEAR |= mask_` (`psp.c:406`) |
| 32 | 2 | `rt` (s16): `pspMsReadSector` / `pspMsWriteSector` result |
| 34 | 1 | `op`: b0 write; b1-b4 attempt index `i` (`ms_psp.c:288,310`) |
| 35 | 1 | `dtick_off` |
| 36 | 1 | `t_phase_on`: JOY phase byte at LED on |
| 37 | 1 | `t_phase_off`: JOY phase byte at LED off |
| 38 | 2 | `pid` |
| 40 | 4 | `t_cmd_on`: JOY `cmd_id` in flight at LED on, 0xFFFFFFFF if idle |
| 44 | 2 | `nop_count` (low 16) at LED on |
| 46 | 2 | `check` |

`set_rd` and `clr_rd` settle the hardware unknown behind H10
(`recon/syscon.md` §2.2: what a read of `0xbe240008` or `0xbe24000c` returns)
without any new register access.

### 1.7 Counter block (`/proc/psptrace/counters`, binary, 32-byte header + 280 u32 words)

Header: `magic` u32 = 0x4E435450 ("PTCN"), `version` u16 = 1, `nwords` u16 =
280, `tick` u32, `cnt` u32, `jiffies` u32, `total_counts_lo` u32,
`total_counts_hi` u32, `check` u32 (XOR of the 280 words).

Each word has exactly one writer context, shown in brackets: J joypad thread,
W timer IRQ, M Memory Stick path, R `/proc` reader, P any process (fops,
vc_screen, mousedev read; plain `++`, informational, may undercount on a rare
preemption race, never used for equality).

| Words | Content |
|---|---|
| 0-11 | `joy_pid` [init], `joy_loop` [J], `joy_stage` [J], `joy_stage_arg` [J], `joy_phase` [J], `joy_cmd_id` [J], `nop_count` [W], `reader_opens` [R], `reader_last_tick` [R], `tick_len_last` [W], `tick_len_max_all` [W], `long_ticks` [W] |
| 12-13 | `ast_calls`, `gc2_calls` [J] |
| 14-19 | JOY cmd 0x33 result classes: -5, -4, -3, -2, 0, >0 [J] |
| 20-25 | JOY cmd 0x08 result classes [J] |
| 26-31 | WD+IRQOFF result classes [W] |
| 32-37 | OTHER result classes [P] |
| 38-45 | JOY exit-code counts E1..E8 [J] |
| 46-53 | WD exit-code counts E1..E8 [W] |
| 54-65 | first tick of each JOY result class (0x08 ×6, 0x33 ×6), 0xFFFFFFFF = never [J] |
| 66-77 | last tick of each [J] |
| 78-89 | WD first/last tick per class [W] |
| 90-101 | interleave histogram: WD Nops that found JOY in step 0..11 [W] |
| 102-122 | `ack_spins` log2 histogram, JOY, 21 buckets [J] |
| 123-143 | same, WD [W] |
| 144-151 | `drain_n` histogram JOY: 0, 1, 2, 3, 4-7, 8-15, ≥16, -3 [J] |
| 152-159 | G3-low gap histogram (counts, log2 from <64 to ≥8192) [J] |
| 160-167 | poll period histogram: 14, 15, 16, 17, 18-21, 22-29, 30-61, ≥62 ticks [J] |
| 168-171 | `ri` R1, R3, R4, R5 [J] |
| 172-187 | `pi_calls`, `pi_dedupe`, `pi_changed`, `lcd_unblank`, `mode_toggles`, `list_down_fail`, `push_ok`, `push_full`, `push_eintr`, `wake`, `nqueues_last`, `mouse_calls`, `mouse_noop`, `mouse_reports`, `sigpend_loops`, `sigpend_first_tick` [J] |
| 188-200 | `fop_open`, `fop_release`, `qfree_enter`, `qfree_got_qsem`, `qfree_got_list`, `qfree_done`, `qfree_stage`, `qfree_queue`, `qfree_pid`, `fop_read_enter`, `fop_read_ret`, `fop_read_eintr`, `fop_ioctl` [P] |
| 201-204 | `vcs_putchar`, `vcs_changecon`, `vcs_updscr`, `vcs_getsize` [P] |
| 205-208 | `md_event_syn` [J, via `input_sync`], `md_notify_calls` [J], `md_clients_walked` [J], `md_read_ret` [P] |
| 209-216 | `ms_rd_sect`, `ms_wr_sect`, `ms_err`, `led_set_rd_bit3`, `led_clr_rd_bit3`, `led_during_g3hi` (JOY step 5-8 at an LED op), `led_last_set_rd`, `led_last_clr_rd` [M] |
| 217-219 | `console_sem_count`, `list_sem_count`, `console_blanked`, sampled at read time [R] |
| 220-224 | ring heads TSC, TPOLL, W, M, O [R] |
| 225-226 | `append_cost_last`, `append_cost_max` [J] |
| 227 | scratch-valid flags [R] |
| 228-263 | **in-flight JOY SC scratch** (144 bytes), copied racily, `ctxbits` b7 set |
| 264-279 | **in-flight POLL scratch** (64 bytes) |

---

## 2. Capture points

Every hook is listed with its file:line in the unmodified tree, the context it
runs in, and what it does. "Same load" means that the compiled instruction
sequence of MMIO loads and stores must be unchanged (G2 checks this with
`objdump`, 7.4).

### 2.1 `Syscon_cmd` (`arch/mips/psp/ipl_sdk/syscon.c:61-258`): every context

| # | Where | Action | Inside the transaction window (G3 low S6 → G3 low S20)? |
|---|---|---|---|
| S-a | entry, before `retry:` (`:75`) | Origin (1.1). Pick scratch: JOY → `joy_scr[joy_nsc++]` (4 slots), WD/IRQOFF → `w_scr`, OTHER → `o_scr`. `ts_read` → `tick_in/cnt_in`, `jif_in`, `tick_len`, `pid`, `cmd_id`, `link`, `nivcsw` snapshot, `nop_count` snapshot. **WD only:** copy `joy_phase` and `joy_cmd_id` into `intr_phase` and `link`, then publish `wd_last_hit_cmd = joy_cmd_id`, `wd_last_hit_phase = joy_phase`, `nop_count++`, histogram word 90+step++. | No, before S5 |
| S-b | `retry:` (`:75`) | `attempt++`; phase = 0x10\|attempt | No |
| S-c | after `:84` | copy `tx_buf[0..7]` into scratch | No (before S5) |
| S-d | `:102` | `v = REG32(0xbe240004); dmy = v; scr->r_gpio04 = v;` **same load** | Starts the window |
| S-e | after `:104` | phase = 0x20\|a | Yes: one `sb` |
| S-f | `:106` | the `if` load kept in a register and stored to `r_spi0c_s7`. **Same load** | Yes |
| S-g | `:110-116` | drained word loads stored to `drained0/1` while the count < 2. `drain_n` taken from `spin` after the loop. On -3: `exit = 1`, go to S-q. **Same loads, same loop structure**; ≤ 3 extra instructions per drained word | Yes |
| S-h | `:119` | store the value to `r_spi0c_s9`. **Same load** | Yes |
| S-i | `:128-134` | first `:130` load value stored to `r_spi0c_tx0`; after the first `:132` push, phase = 0x30\|a | Yes |
| S-j | after `:136` | phase = 0x40\|a; `cnt_g3hi = mfc0 Count; dtick_g3hi = tick - tick_in` | Yes, 4 instructions |
| S-k | after `:140` | phase = 0x50\|a | Yes |
| S-l | `:151-156` | ACK loop **peeled**: `v = REG32(0xbe240020); scr->r_g20_first = v; while (!(v & 0x10)) { if (spin-- == 0) {...-4...} v = REG32(0xbe240020); } scr->r_g20_last = v;`. The order of load, test and budget check per iteration is identical to the original `while` (load, test, `spin--` check, load, ...). `ack_spins = SPIN_MAX - spin`. On -4: after the existing teardown writes (`:154`) set `exit = 2`, `phase_last`, go to S-q | Yes, 1 extra store before the loop and 1 after |
| S-m | after the loop | `cnt_ack = Count; dtick_ack`; phase = 0x60\|a | Yes |
| S-n | after `:159` | phase = 0x70 | Yes |
| S-o | `:202-217` | the `:204` status load kept; when the loop breaks, stored to `r_spi0c_rxend`; phase = 0x70\|(words read) after each word; `nwords` | Yes, 1 `sb` per word |
| S-p | after `:219` phase = 0x80\|a; after `:222` `cnt_s20 = Count; dtick_s20`; phase = 0x90\|a | | Last one closes the window |
| S-q | after the checksum (`:226-246`) and at `:249-254` | compute `exit` (1.1); `exits_mask`; on the first attempt set `first_exit/first_rx2`; on `goto retry` loop to S-b; on -5 `exit = 8` | No |
| S-r | before every `return` (`:113`, `:154`, `:257`, via one exit label) | `ts_read` → out stamps; copy `rx_buf[0..15]`; `result`; `preempt_delta`; `wd_during = nop_count - snapshot`; if `wd_during > 0 && wd_last_hit_cmd == my cmd_id` then `wd_hit_phase = wd_last_hit_phase`; update counters, histograms, first/last ticks; phase = 0xA0. **WD/IRQOFF/OTHER: append to the ring now. JOY: leave in scratch** (appended at J-c). Then phase = 0x00. | No |

Nothing is added to the -3 and -4 paths **before** their existing register
writes. The hooks run after them.

### 2.2 Register values: none read that the code does not already read

The design adds **zero** MMIO accesses. Every register value in a record is
the value of a load that the unmodified code performs at that point:
`0xbe240004` (`syscon.c:102`), `0xbe58000c` (`:106,:111,:119,:130,:204`),
`0xbe580008` (`:114`, `:207`, the latter is `rx_buf`), `0xbe240020` (`:152`),
`0xbe240008` and `0xbe24000c` (`psp.c:401,406`, read-modify-write already
performed per Memory Stick sector, `recon/syscon.md` §2.2 [OBJ]). This follows
dossier 9.1: the source proves no read safe, so no new read is made.
Registers never read by the running code (SPI +0x00, +0x04, +0x14, +0x18,
+0x20, +0x24; GPIO +0x00, +0x10, +0x14, +0x18, +0x24, `recon/syscon.md` §4.3)
are **not observed**. That blind spot is stated in row H8 of section 6.

### 2.3 Timer interrupt (`arch/mips/psp/psp.c`)

| # | Where | Action | Context |
|---|---|---|---|
| T-a | `psp.c:351-356` inline asm | add `mfc0 %0, $9` **before** `mtc0 $0, $9` → `tick_len_last`; after the reset: `psptrace_tick++`, `total_counts += tick_len_last`, max, `long_ticks` | hard IRQ, IE off, before `irq_enter` (`psp.c:367` → `include/asm-mips/irq.h:54`) |
| T-b | `psp.c:378-379` | `psptrace_wd_active = 1; psp_pacify_watchdog(); psptrace_wd_active = 0;` | same |
| T-c | after `psp_watchdog_tick()` (`psp.c:359`) | `if (psptrace_tick % 250 == 125) psptrace_snap();` → SNAP into W ring | same |
| T-d | `psp.c:399-407` `psp_gpio_set/clear` | `v = PSP_GPIO_SET; PSP_GPIO_SET = v \| mask_; psptrace_led_rd_set = v;` (and the same for CLEAR). The load and store pair is the same as the compiled `\|=` (`recon/syscon.md` §2.2 [OBJ] `lw/or/sw`) | caller's |

The boot Nop (`psp.c:557`) needs no hook. It records with origin IRQOFF at
tick 0.

### 2.4 Joypad thread and driver (`drivers/input/joypad_psp.c`): thread context unless stated

`joy_stage` is a byte written only by the thread and read by the timer (SNAP,
WD records) and the `/proc` reader. `joy_stage_arg` is a word written just
before the stage byte.

| # | Where | Action | `joy_stage` |
|---|---|---|---|
| J-a | `:453-458` thread start | `psptrace_joy_task = current; joy_pid = current->pid` | 0 |
| J-b | `:458` loop top | `joy_loop++`; start POLL scratch: `ts_read`, `sig`, `nivcsw`, `period` | 1 |
| J-read | `:486` / `:487` | before each call | 2 / 3 |
| J-ri | `:488`, `:490`, `:493`, `:495` | `ri_branch`, `keys_raw` (`keys` before `~`), `x`, `y`, results | 4 |
| J-c | after `:460` (read_input returned, every branch) | **append the JOY SC scratch records** (normally 2) to TSC, set `joy_nsc = 0`. Both transactions are finished, so this adds nothing between them | 5 |
| J-d | `:498-540` `process_input` | flags per 1.4: dedupe (`:512`), `console_blanked` (sampled before `psp_lcd_on`, `:518`), toggle (`:521`), `mouseMode` (`:524`), `keys_pi` (`:527`) | 6, 7, 8 (`lcd_on`) |
| J-e | `:530` | stage 9 before `down_interruptible`, 10 after success, `list_down_fail++` on failure | 9, 10 |
| J-f | `:534` / `:384-411` | per queue: stage 11 with arg = queue pointer before `:390`; the reason (ok/full/eintr) set inside `queue_push` at `:392`, `:397-398`, `:409-410`; stage 12 while pushing | 11, 12 |
| J-g | `:536`, `:538` | after `up`, after `wake_up_interruptible` | 13, 14 |
| J-h | `:593-658` `psp_mouse_process_input` | M1 (`:610`), M2 (`:644`), reported (`:651-658`), `dx`, `dy`, buttons | 15, 16 |
| J-i | before `:468` `msleep` | finish the POLL record, append it to TPOLL | 17, then 18 (in `msleep`) |
| F-a | `:219-250` `fop_read` | `fop_read_enter++`; on return `fop_read_ret++` or `fop_read_eintr++` (`:246`) | psposk2's context |
| F-b | `:252-293`, `:295-317`, `:319-329` | `fop_ioctl++`, `fop_open++`, `fop_release++` | caller |
| F-c | `:346-360` `queue_free` | `qfree_stage` = 1 entry, 2 after `:348` succeeds, 3 after `:353` succeeds, 4 after `:356`, 5 before `kfree` `:359`; `qfree_queue = queue_`; `qfree_pid`. **This is the direct H9 signature** | closer's context |

### 2.5 Above the driver

| # | Where | Action | Context |
|---|---|---|---|
| U-a | `drivers/char/vc_screen.c:562-590` `psp_vcs_ioctl` | counter per command (PUTCHAR `:574`, CHANGE_CON `:578`, UPDATE_SCR `:582`, GET_SIZE `:586`): psposk2 and pspmd injection liveness | psposk2 / pspmd |
| U-b | `drivers/input/mousedev.c:304` `mousedev_event` | `md_event_syn++` on SYN_REPORT | joypad thread (via `input_sync`, `joypad_psp.c:658`) |
| U-c | `drivers/input/mousedev.c:228` `mousedev_notify_readers` | `md_notify_calls++`, `md_clients_walked += n` | joypad thread |
| U-d | `drivers/input/mousedev.c:629` `mousedev_read` | `md_read_ret++` on a successful return (pspmd, and the collector's own mouse client, 4.2) | reader |
| U-e | `kernel/printk.c:67` | new accessor returning `atomic_read(&console_sem.count)` (read only) for SNAP and counters | any |
| U-f | `drivers/block/ms_psp.c:288-301`, `:310-323` | MSIO record per attempt (1.6): stamps around `psp_led_ctrl` pairs, the `set_rd`/`clr_rd` values from T-d, sector, `rt`, JOY phase, `t_cmd_on`. Runs inside `__bio_kmap_atomic` (`ms_psp.c:254` → `include/linux/highmem.h:49-52` → `include/linux/uaccess.h:16-18`, preemption disabled) and under `s_psp_ms_rw_sem` (`ms_psp.c:333,360`), so there is **one writer at a time** | the task doing the I/O (the collector, or pdflush) |

### 2.6 `/proc` (new file `arch/mips/psp/psptrace.c`, `late_initcall`)

`create_proc_entry` (`fs/proc/generic.c:669`) with custom `proc_fops`, the
same pattern as `drivers/input/input.c:651-663` (`recon/input.md` §7.2):

- `/proc/psptrace/stream`: binary stream of chunks (3.4). Non-seekable.
  Per-open cursors are allocated at open (`GFP_KERNEL`, process context).
- `/proc/psptrace/counters`: the counter block (1.7), one snapshot per read
  at offset 0.
- `/proc/psptrace/status`: a text summary for `cat` (debug only, not used by
  the collector).

One `printk` at init: `psptrace v1: TSC 4096 TPOLL 2048 W 1024 M 4096 O 64`.
There is no other printk anywhere in the instrumentation.

---

## 3. History mechanism

### 3.1 Rings

All rings are static arrays in BSS. BSS is zeroed by `head.S` before
`start_kernel` (`arch/mips/kernel/head.S:182-187`), so recording is valid from
`arch_early_setup`. That is before the boot Nop at `prom_init`
(`psp.c:557`), and no allocation is needed.

| Ring | Writer (only one) | Slot | Slots | Bytes | History held at max rate |
|---|---|---|---|---|---|
| TSC | joypad thread (JOY SC) | 144 | 4096 | 589,824 | 114.7 s at 35.71 SC/s |
| TPOLL | joypad thread | 64 | 2048 | 131,072 | 114.7 s at 17.86 polls/s |
| W | timer IRQ with IE off (WD SC, SNAP) and the IE-off boot Nop | 144 | 1024 | 147,456 | 853 s at 1.2 rec/s |
| M | Memory Stick path (serialized, 2.5 U-f) | 48 | 4096 | 196,608 | ≈146 s at ≈28 rec/s (UNVERIFIED rate) |
| O | other threads | 144 | 64 | 9,216 | boot/shutdown only |
| **Total** | | | | **1,074,176** | |

The kernel also has scratch (4 JOY SC slots, 1 POLL, 1 W, 1 O: about 1 KB)
and the 1,120-byte counter block.

**Why the rings exist at all.** They do not hold "the history". The stick
file does. The rings absorb collector outages: a crash and restart (≤ 3 s,
4.5), a slow `fsync`, or a CPU-starved collector. Everything survives a
collector outage shorter than 114 s with no loss.

### 3.2 Full resolution vs summarised

- **Full resolution, whole run:** every `Syscon_cmd` call in every context
  (raw tx, full raw rx, result, exit, words, attempts, captured register
  values, phases, timings), every poll iteration, every sector attempt, and a
  1 Hz state snapshot. All of it goes to the stick for the whole run. **No
  sampling, no decimation, no deduplication.**
- **Summarised:** cumulative counters, first/last tick per result class, and
  histograms of ACK spins, drain counts, G3-low gaps, poll periods and
  interleave phases (1.7), snapshotted to the stick about once a second. They
  give the whole-run picture even if some stream data were lost.

### 3.3 Context safety (D9)

- **One writer per ring.** The five rings are partitioned by context (3.1). A
  context never writes another context's ring or scratch. The timer IRQ
  interrupting the thread mid-record therefore writes only to W and to its own
  variables, and cannot tear a TSC or TPOLL record.
- **Cross-context data is single-word, single-writer.** The WD path reads
  `joy_phase` (byte) and `joy_cmd_id` (word), which only the thread writes.
  The thread reads `nop_count`, `wd_last_hit_cmd` and `wd_last_hit_phase`,
  which only WD writes. Aligned byte and word loads and stores are single
  instructions on MIPS. Nothing does a read-modify-write on a variable that
  another context also writes. That is why no atomic is needed. On this CPU an
  atomic may itself be implemented with IRQ masking (`include/asm-mips/atomic.h:53-65`
  uses `ll/sc` only when `cpu_has_llsc`, and PSP support for it is not
  established; UNVERIFIED).
- **Publish protocol (writer):** fill the slot at `head % N`, compute
  `check`, `barrier()`, store `seq`, `barrier()`, store `head = seq + 1`.
  This is a uniprocessor (dossier 2), so compiler barriers suffice.
- **Validate protocol (reader, process context, preemptible):** for index
  `i < head`: if `i < head - N + 1`, count the difference as lost and skip
  forward. Copy the slot to a 144-byte stack buffer, then re-read `head` as
  `h2`. The record is valid only if `i > h2 - N` (not being overwritten), the
  copied `seq == i`, and `check` verifies. Otherwise count it as lost. Then
  `copy_to_user`. The reader never blocks a writer and never takes a lock.
- **O ring** can in principle have two concurrent writers (two non-joypad
  threads calling the syscon at once). None does so in steady state
  (`recon/syscon.md` §2.1: C4 once at boot, C7 at shutdown). A tear would be
  caught by `check` and reported. This is accepted and listed in 11.

### 3.4 Stream chunk (`/proc/psptrace/stream` read)

Each `read()` returns one chunk: a 64-byte header followed by whole records.
It never splits a record. It returns `-EINVAL` if `count < 64 + 144`.

| Off | Size | Field |
|---|---|---|
| 0 | 4 | magic 0x434B5450 ("PTKC") |
| 4 | 2 | version = 1 |
| 6 | 2 | header length = 64 |
| 8 | 4 | `reader_id` (value of `reader_opens` at open) |
| 12 | 4 | `chunk_seq` (per open file, from 0) |
| 16 | 12 | `now_tick`, `now_cnt`, `now_jiffies` |
| 28 | 20 | heads TSC, TPOLL, W, M, O |
| 48 | 10 | records lost per ring since the previous chunk (u16 each, saturating) |
| 58 | 2 | `nrec` |
| 60 | 4 | `payload_len` (bytes of records that follow) |

Cursors start at the oldest valid record of each ring when the file is
opened. A restarted collector therefore re-reads up to 114 s of TSC history.
The decoder removes duplicates by `(ring, seq)`.

### 3.5 In-flight state

If the thread is stuck inside a command, or between its commands and the
flush, the unfinished JOY SC and POLL scratch are exported in the counter
block (words 228-279) with `ctxbits` b7 set, together with `joy_phase` and
`joy_stage`. The timer also samples `joy_stage`, `joy_phase` and the task
state into SNAP at 1 Hz and into every WD record. A thread that never returns
from any point is located to the step.

### 3.6 Triggers

**None.** Nothing freezes, stops or changes resolution on any condition. D4
and D5 are met by construction: history before and after onset is streamed at
full resolution, whatever the shape of the failure and whenever it happens.
The only mode change is a volume cap in the collector (4.6), set at 128 MB,
about 3.5 hours.

---

## 4. Extraction path

### 4.1 Choice: a new collector, `psptrace`, derived from `telem.c`

Decision: a **new** program, `/usr/bin/psptrace`, in the embedded initramfs.
It reuses `telem.c`'s FP-free helpers (`apps`, `appl`, the 5x7 font, `blit`,
`mem_free_kb`, `kernel_uptime`, `poll_mouse`) by copying them.

Reasons for not extending telem in place:

- telem is interactive. It puts its stdin tty in raw mode (`telem.c:235-245`)
  and steals OSK characters from the shell. It quits on `q`/`Q`/ESC/0x03
  (`:356-357`). It falls back **silently** to a RAM file when `/ms0` is
  missing (`:326`, `:293`). Its kmsg capture goes blind after 16 KB (dossier
  9.1, B5). A boot-started, headless collector must do none of these things.
- `telem.c` stays unchanged as the reference that produced the 9.6 evidence.

**Load fidelity with telem (important for S5 and for H4, see 7.3).** The three
bracketed deaths in dossier 9.6 all happened with telem running in the
foreground. The collector's tick reproduces telem's per-tick work, in order:

- a full-screen 480x272 HUD render and a `blit` of 272 `lseek` plus `write`
  calls to `/dev/fb0` (`telem.c:299-306`);
- reading `/proc/meminfo` and `/proc/uptime`;
- `syslog(3)` of 16 KB (`telem.c:279-282`), kept for load only; the kernel
  log itself is taken from `/proc/kmsg`;
- a non-blocking drain of `/dev/input/mice` (`telem.c:249-274`), which keeps
  a telem-equivalent mousedev client and the INPUT counter;
- one `write` plus `fsync` per tick;
- `nanosleep(200 ms)` (`telem.c:54,415`), giving about 0.23 s per tick, as in
  the recovered logs (dossier 9.6).

**The operator does not start telem** (runbook). The collector replaces it.

### 4.2 Start from `rc.sysinit`, supervision, and what happens on death

`rc.sysinit` gets three lines after the existing `pspmd -s&`
(`extract/root2/etc/rc.sysinit:17-19`), so that `mount /ms0` (`:10`),
`psposk2` (`:14`) and `pspmd` (`:18`) start exactly as in the baseline:

```
printf "\033[37mLaunching psptrace collector\t\t\t\033[0m"
psptrace&
printf "[  \033[32mOK\033[37m  ]\033[0m\n"
```

This uses the same `&` idiom as `:14` and `:18`. There is no redirection
syntax to depend on. The program redirects its own fds.

- **Supervisor** (`psptrace` with no arguments). It calls `setsid()`, opens
  `/dev/null` onto fds 0-2, and ignores SIGINT, SIGQUIT, SIGHUP, SIGTSTP and
  SIGPIPE. It creates `/ms0/PSPTRACE` and picks run number `rrr` as one more
  than the largest `R???_??.BIN` there. It then loops: `vfork` + `execve("/usr/bin/psptrace", "-w", rrr, ii)`;
  `waitpid`; append one line (instance, exit status or signal, kernel tick
  from `/proc/psptrace/counters`) to `/ms0/PSPTRACE/SUPERV.TXT`, then
  `fsync`; `nanosleep(2 s)`; `ii++`. It has no other I/O. It does not open any
  input device.
- **Worker** (`psptrace -w rrr ii`). It does the work described in 4.3 and
  4.4.
- **If the worker dies:** the supervisor restarts it within about 2 s. The new
  worker writes a new file `Rrrr_ii.BIN` and reopens the stream, whose cursors
  start at the oldest valid records (3.4). **Nothing is lost if the worker is
  down for less than 114 s.** The decoder removes the duplicates. Restarts are
  visible on the HUD (the instance number) and in `SUPERV.TXT`.
- **If the worker hangs** (for example blocked in `fsync`): the HUD heartbeat
  stops. That is visible and photographable. The kernel keeps recording and
  `reader_last_tick` stops advancing. Data already synced is safe. The
  supervisor cannot kill a task in D state, so it does not try.
- **If the supervisor dies:** nothing restarts it. Its code has no I/O except
  `vfork`/`exec`/`waitpid` and one small append per restart. This risk is
  listed in 11. `busybox` has no `sleep` applet in this initramfs (directory
  listing of `extract/root2/bin`), so a shell respawn loop would spin; a
  compiled supervisor avoids that.
- **Crash-loop guard:** a worker that fails during start-up sleeps 5 s before
  exiting, so a crash loop cannot saturate the CPU.
- `/dev/joypad` is **never** opened by the collector. An extra queue would
  change the thread's push loop, and closing it on a crash would exercise the
  H9 path (`joypad_psp.c:346-360`).

### 4.3 Worker tick (period ≈ 0.23 s)

1. `read()` `/proc/psptrace/stream` into a 4,000-byte static buffer until a
   chunk with `nrec == 0`. Each chunk becomes one frame (4.4). The frame
   stays under 4 KB, which helps raw-image recovery (10.2).
2. Every 4th tick, read `/proc/psptrace/counters` (1,152 bytes) → CNT frame.
3. Read `/proc/kmsg` opened `O_NONBLOCK` (`fs/proc/kmsg.c:36-37` returns
   `-EAGAIN` when empty) → KMSG frame if any. This has no 16 KB blind spot.
   There is no klogd in this initramfs (`inittab` lists none).
4. Every 8th tick (about 2 s): read `/proc/<pid>/stat` for the joypad thread
   (pid from counter word 0), `psposk2` and `pspmd`. Rescan `/proc` for these
   names every 40 ticks, or when a pid vanishes. Also read `/proc/<joy_pid>/status`
   and keep the `State:`, `SigPnd:` and `ShdPnd:` lines (`fs/proc/array.c:167,275-279`).
   All of it goes into a PROC frame as raw text.
5. `telem`-equivalent work (4.1), and a UHB frame (10.3).
6. One `write()` of the assembled static buffer (typically about 2.3 KB),
   then `fsync()`. The time of each is measured with `gettimeofday`
   (jiffy-resolution) and recorded in the next UHB.
7. HUD render and blit (8.2).
8. `nanosleep(200 ms)`.

All buffers are static (the bFLT stack is 4 KB, `recon/input.md` §6.1).
Stage 2 also raises the stack with `flthdr -s 16384`. No floating point is
used (D18, 7.6).

### 4.4 File layout on the stick

`/ms0/PSPTRACE/Rrrr_ii.BIN` (8.3-compatible), opened
`O_WRONLY|O_CREAT|O_APPEND`. Before first use, the worker `statfs`es `/ms0` and
requires the vfat magic 0x4d44 and at least 256 MB free. Otherwise it shows
SELFTEST FAIL. **It never falls back to a RAM file.** The file is a sequence
of frames (header 20 bytes + payload, payload ≤ 4,096 bytes, padded to 4),
described in section 10.

### 4.5 What a battery pull loses

After `fsync` returns, the data, the directory entry (size) and the FAT are on
the stick. `file_fsync` (`fs/sync.c:55-76`) writes the inode, calls
`write_super`, then `sync_blockdev`, and the Memory Stick driver completes I/O
synchronously in the caller (`ms_psp.c:228-236`). A record produced at time t
is on the stick by the end of the first `fsync` that starts after the next
stream read. Let W be the write+fsync duration and 0.2 s the sleep.

- **Worst-case loss = 2 × (0.2 s + W_max).** This happens when the pull comes
  just before an `fsync` completes. W_max is measured and recorded in every
  UHB and shown on the HUD. telem's own 0.23 s tick included its `fsync`, so
  small syncs take well under 30 ms. Our syncs are about 2.3 KB. The estimate
  is W ≤ 0.1 s, which gives a loss ≤ 0.6 s (UNVERIFIED).
- **The runbook requires W_max ≤ 2 s on the HUD. If it is higher, the idle
  wait is extended (runbook step D).** That bounds the loss at 4.4 s, against
  a 60 s hands-off wait before the pull (D6).
- A frame cut by the pull fails its CRC and is dropped. Every complete frame
  before it is recovered (10.2).
- If the pull corrupts the FAT or directory, the decoder can scan a **raw
  image** of the stick for frame magics (10.2). The runbook asks for a raw
  image before anything else touches the stick.

### 4.6 Stick errors, full stick, volume cap

- **Write or `fsync` error:** the HUD MS line turns red with the errno. The
  worker keeps trying every tick and never stops recording into the kernel
  rings. The error count is recorded in UHB.
- **Stick full** is prevented by the 256 MB free-space check at start and the
  cap.
- **Cap:** when the file passes 128 MB (about 3.5 hours at 10 KB/s), the worker
  switches to summary mode. It keeps W, M, CNT, KMSG, PROC and UHB, and
  discards TSC and TPOLL after reading them. The switch is recorded in a NOTE
  frame. Worst-case disk use is bounded by 128 MB plus about 1.5 KB/s.

---

## 5. Budget

### 5.1 Bytes to the stick

Rates are maxima: 17.86 polls/s (`recon/input.md` §4), 2 JOY commands per
poll, a watchdog Nop every 1250 ticks, a SNAP per 250 ticks, and a collector
tick of 0.23 s (4.35/s).

| Stream | Rate /s | Bytes each | B/s |
|---|---|---|---|
| TSC (JOY SC) | 35.71 | 144 | 5,143 |
| TPOLL | 17.86 | 64 | 1,143 |
| W: WD SC | 0.2 | 144 | 29 |
| W: SNAP | 1.0 | 128 | 128 |
| M: sector attempts | ≈ 28 (UNVERIFIED, 5.3) | 48 | 1,344 |
| O | ≈ 0 | 144 | 0 |
| Stream chunk headers | ≈ 4.35 | 64 | 278 |
| CNT frames | 1.09 | 1,152 | 1,253 |
| UHB | 4.35 | 64 | 278 |
| PROC | 0.54 | ≈ 600 | 326 |
| KMSG | ≈ 0 (≈ 2 KB at boot) | | ≈ 0 |
| Frame headers | ≈ 11 | 20 | 220 |
| **Total** | | | **≈ 10,140 B/s ≈ 9.9 KiB/s** |

**15 minutes: ≈ 9.1 MB. 30 minutes: ≈ 18.3 MB.** Cap: 128 MB (4.6). The
stick reports 118,999 MB (`telem/logs-from-stick/kmsg.txt`, "Adding disk ms0
118999M"; that figure is UNVERIFIED as real free space, and the 256 MB check
covers it).

### 5.2 Kernel memory

About 1,074 KB of rings (3.1), plus about 2.2 KB of scratch and counters, plus
code (estimated ≤ 8 KB text). The detected RAM shrinks by the same amount,
because `psp_detect_mem_size` starts from `_end` (`psp.c:429`). Recovered
telem logs on the 2008 image show MemFree between 20,780 and 20,844 KB
(`telem/logs-from-stick/telem*.log`, column 4). Rings are about 5% of that.
The HUD shows MemFree. BSS is not part of `vmlinux.bin` (`recon/build.md` §2),
so the image grows only by the code.

### 5.3 Memory Stick operation rate (H10 exposure)

About 10.1 KB/s is ≈ 19.8 data sectors/s. Each `fsync` also writes the
directory entry and the FSINFO sector (`write_super`), about 2 × 4.35/s. A FAT
sector is written per cluster allocated (cluster size UNVERIFIED). That gives
**≈ 28 sector writes/s, each with an LED set and clear read-modify-write**
(`ms_psp.c:312-314`). telem wrote about 1 data sector plus 2 metadata sectors
per tick, about 13 sectors/s (UNVERIFIED, estimated from the same `fsync`
path). **The collector therefore does about 2.2× telem's sector operations
at the same `fsync` cadence.** Section 7.3 explains why that is acceptable
and how it is measured.

### 5.4 Time added (estimates, instruction counts at ≈ 222 MHz and about 1 CPI when cached; UNVERIFIED, measured on device)

| Where | Added | Estimate |
|---|---|---|
| Inside one transaction window (S6 → S20) | 8 phase `sb`, 6 captured-value `sw`, 3 × (`mfc0` + tick load + 2 stores), 1 `sb` per TX word and per RX word, ≤ 3 instructions per drained word. **No new MMIO, no new loop iteration cost** (peeled ACK loop) | ≈ 35–45 instructions ≈ **0.2 µs** |
| Rest of `Syscon_cmd` (entry and exit, outside the window) | origin detection, 2 `ts_read`, 16-byte rx copy, counters, histograms | ≈ 80–100 instructions ≈ 0.45 µs |
| JOY SC append (deferred, after both of the poll's transactions) | 144-byte copy, check, publish | ≈ 150–200 instructions ≈ 1 µs each |
| WD Nop (IRQs off) | the rows above plus an immediate append | ≈ **+1.7 µs of IRQ-off time per Nop** |
| Per poll (total) | 2 SC + POLL append + stage stores | ≈ 4–5 µs per 56 ms poll (< 0.01% CPU) |
| Timer handler, every tick | `mfc0`, tick, sum, max | ≈ 12 instructions ≈ 60 ns |
| SNAP tick (1 Hz) | 128-byte record | ≈ 1.5 µs |
| MS sector attempt | MSIO record | ≈ 1 µs (sector PIO time ≫ this) |

The command's own duration is measured by the records (`cnt_out - cnt_in`).
From the source it is at least 23 uncached MMIO accesses (2-word TX, 8-word
RX) plus the syscon's ACK latency, which is UNKNOWN. **`append_cost_last/max`
measures the append cost in place on the device**, and 7.4 shows how the
window cost is checked from the compiled object.

---

## 6. Coverage matrix

The fields named are those of section 1. "Onset" is found by the decoder
without any trigger (10.4). Every row also leaves the complete raw record
stream, so an analyst can reject the decoder's classification.

| ID | Signature in the recorded fields | Could be confused with | How they are separated |
|---|---|---|---|
| **H0** | None of the rules below match. Every SC (raw tx/rx, result, exit, register values, phases, timings), every POLL (branch, flags, pushes, mouse), every MSIO, the 1 Hz SNAP and CNT words, KMSG, and PROC text of the three tasks are still available. The decoder prints ±15 s windows around every onset candidate O1-O4. | anything | the raw windows are the evidence |
| **H1** | After onset, JOY SC for 0x08 and 0x33 end with `result -4` (`exit 2`, `ack_spins 1,000,001`, `r_g20_last` bit 4 clear) or `-3` (`exit 1`, `drain_n 1,000,001`). POLL `ri_branch 3`. POLL `period` stretches by the spin-budget time. Counters 15/21 or 16/22 climb from their `first_tick`. **The 9.5 variant is separated:** WD SC for Nops after onset either also fail (pure H1) or succeed (`exit 7`), which shows the syscon still answers command 0x00. | H4 (the event that caused the stuck state); H8 (register state behind the missing ACK) | Row H4 applies to the onset record; H1 describes the persistent state. The report gives both ("trigger H4, state H1"). |
| **H2** | `result 0`, `exit 4`, `nwords ≥ 1`, `rx[0] 0`, `rx[3..6] 00` → `keys_raw 0` → POLL `ri_branch 4` (HOLD) on every poll. | the real HOLD switch | Runbook calibration (pre-death HOLD on/off) records the genuine HOLD frame: `exit 7` with non-zero `rx[0]` and only the HOLD bit changed. The post-death script toggles HOLD at known moments. |
| **H3** | `result 0`, `exit 3`, `nwords 0`, `rx` all 0xFF → `keys_raw 0xFFFFFFFF`, `x = y = 0xFF` → `ri_branch 5`; POLL `mouse_flags` reported with `dx +16`, `dy +16` (REL_Y −16) in mouse mode; `pi_flags` dedupe after the first poll. | single-poll E3 produced by an H4 interleave at P3/P4/P5a/P5b (`recon/syscon.md` §5.1) | H3 needs persistence across polls. A lone E3 at a WD-hit command is logged under H4. |
| **H4** | A WD SC record at `tick ≡ 0 (mod 1250)` with `intr_origin 0` (JOY), `intr_phase` step 2-9, and `link` = the interrupted JOY `cmd_id`. That JOY SC has `wd_during ≥ 1` and `wd_hit_phase` equal to the same step. **The step names the recon point** (1.1): step 5 is P4 or P5a (split by the WD record's `r_gpio04` bit 4), step 6 is P5b, and so on. The WD record's `drain_n` and `drained0/1` show what the Nop stole from the thread's FIFO. Its own `rx`, `exit` and `result`, discarded in the kernel (`psp.c:392`), are now recorded. The JOY record shows what the thread saw after resuming. Onset follows within that poll or the next. **What keeps input dead afterwards** is in the records that follow: `drain_n` and `drained*` (stale words at later command starts), `r_spi0c_*` status bits, Nop outcomes, and the JOY result sequence. Interleaves that do **not** cause onset are logged too (histogram words 90-101), which gives the per-phase harm rate. | H10 (another actor in the G3-high window); coincidence | H10 has an MSIO record instead of a WD record in the window. Tick phase ≡ 0 mod 1250 is required for H4. Every WD record gives `intr_phase`, so benign interleaves are counted, not guessed. |
| **H5** | `result -5` with `exit 8`, `attempts 16`, `rx[2]` ∈ {0x80, 0x81}; or `result -2` with `exit 5` or `6`, persistent. `exits_mask` and `first_exit/first_rx2` show retry history. Raw `rx` shows the shift (`rx[1]` out of range, response code). | H4 at P2/P6 (−2 once) | Persistence and `wd_hit_phase`. |
| **H6** | JOY SC 0x08: `exit 7`, checksum valid, `result > 0`, `rx[3..8]` constant across the post-death script, while the pre-death calibration showed those bits changing for the same buttons. POLL `pi_flags` b1 (dedupe) every poll, `pi_changed` flat. | H7 | H7 has `rx` changing with the script. |
| **H7** | `rx[3..6]` / `keys_raw` follow the post-death script (raw data is alive), but delivery stops at an identifiable stage: (a) `ri_branch 5`, `pi_changed` rises, yet `list_down_fail` / `push_full` / `push_eintr` rise, or `nqueues 0`; (b) pushes OK and `wake` called but `fop_read_ret` flat → psposk2 not consuming (PROC shows its state and wchan); (c) `mouse_reports` and `md_event_syn`/`md_notify_calls` rise but `md_read_ret` flat → pspmd not reading; (d) `vcs_putchar` flat while psposk2 reads → injection path; `console_sem_count ≤ 0` for a long time → console semaphore stuck (`recon/input.md` B6); (e) POLL `sig` b0 set → a pending signal (4.7). | H9 when the thread itself stops | (e) and the stage split. If the thread stops, there are no new POLL/TSC records; see H9. |
| **H8** | The captured values of existing reads (`r_gpio04`, `r_spi0c_s7/s9/tx0/rxend`, `r_g20_first/last`, MSIO `set_rd/clr_rd`) take a value after onset outside their pre-onset set. The decoder builds the pre-onset value set per field and lists new values. **Blind spot:** registers the code never reads (2.2) are not observed. A change there shows only through behaviour (H1/H3/H5 shapes) with unchanged captured values. | H1, H4 | Values vs results: a changed status word with a behaviour change is H8-consistent. The blind spot is declared, not hidden. |
| **H9** | JOY records (TSC, TPOLL) stop. SNAP `joy_loop` frozen; `joy_stage 11` with `joy_stage_arg = Q` (waiting on the queue sem), or `9` (waiting on `list_sem`); `joy_state` interruptible sleep. Counters: `fop_release` just incremented, `qfree_stage 2` with `qfree_queue = Q` (closer holds `Q->sem`, waits on `list_sem`), `qfree_pid` = the closer. PROC: psposk2 exited or in D/S. WD SC continue normally (Nops fine). | H7(d) (the thread stops for another reason) | `joy_stage`/`qfree_stage` pairing with the same `Q`. |
| **H10** | An MSIO record whose `t_phase_on` or `t_phase_off` is step 5-8 (G3 high), for a JOY command with `preempt_delta ≥ 1`, and `set_rd`/`clr_rd` with bit 3 (0x08) set, immediately before onset. Counters 212-214 give run-wide exposure. Onset tick need **not** be ≡ 0 mod 1250. The G3-high window of that JOY record shows the disturbance (`exit`, `ack_spins`, `rx`). | H4 | The interrupter type (MSIO vs WD record) and the tick phase. A composite (both in the same window) is reported as such, with both records. |

Onset timing (S3) plays no part: death at 17 s, 250 s or 15 minutes all fall
inside continuously streamed data (3.6). A death before the collector starts
(it starts within seconds of boot) is still in the rings, which hold 114 s
from boot.

---

## 7. Perturbation statement

### 7.1 What is not changed

- No lock, semaphore, `preempt_disable`, IRQ masking, delay, extra MMIO access,
  extra syscon command or printk is added to `Syscon_cmd`, its callers or the
  timer path. The timeout patch (`syscon.c:12-13,110-116,151-156,253-254`),
  `BYPASS_ERR_CHECK` (`:10`) and the discarded Nop result (`psp.c:392`) stay
  exactly as they are. G2 checks this against
  `/home/ubuntu/psp/work/syscon-timeout.applied.patch`.
- The watchdog cadence, the thread's `msleep(50)` and its priority, the
  driver's logic, the boot sequence up to the end of `rc.sysinit` and the
  kernel command line (`console=tty osk=Dv4`, dossier 9.7) are unchanged.
- Nothing reads `/dev/joypad`, so the queue list is exactly psposk2's.

### 7.2 Timing inside and between transactions

- **Inside the window (S6 → S20):** about 0.2 µs of cached stores and CP0
  reads, spread over about 12 points between uncached accesses. The **order
  and number of MMIO accesses are identical**. The two spin loops keep their
  per-iteration instruction sequence (drain loop plus ≤ 3 instructions only
  while words are actually drained; ACK loop peeled, unchanged per iteration),
  so the -3/-4 budgets keep their duration.
- **Between the poll's two commands (the G3-low gap):** the append of command
  A's record is deferred until after command B (2.4 J-c), so it is **not** in
  the gap. What remains in the gap is A's exit bookkeeping and B's entry
  bookkeeping, about 0.45 µs. The original gap length is UNVERIFIED: a few
  hundred instructions plus about 6 uncached accesses. **Risk:** if the
  failure needs a G3-low interval shorter than some syscon minimum (the
  commented-out `Syscon_wait(5)` at `syscon.c:95-97,142-144` hints that one
  exists), a longer gap would make that failure rarer. The gap is measured on
  every poll (`cnt_s20` → next `cnt_g3hi`) and summarised in histogram words
  152-159. The analyst will know the gap distribution in the run and whether
  onset follows short gaps. It cannot be ruled out a priori, so it is listed
  in 11.
- **Watchdog Nop:** about +1.7 µs of IRQ-off time per Nop (every 5 s). When a
  Nop interleaves with a thread transaction, the thread's resumption is
  delayed by that much, while it is spinning on a latched status anyway.
- **Interleave probability (H4).** A Nop can interleave only if a JOY
  transaction is in flight when a timer interrupt begins. The thread wakes
  from `msleep` in the timer softirq of a tick (`kernel/timer.c:1529-1535`),
  so its transactions normally start just after a tick. They straddle the
  *next* tick only if they are long or the thread was delayed. The
  instrumentation adds about 0.65 µs to each transaction's in-flight time.
  Against a 4 ms tick, the added straddle probability is about 0.02 %
  absolute. `cnt_in` of every JOY SC is exactly "time since the tick began",
  and `tick_out ≠ tick_in` marks every straddle, so the decoder measures the
  real exposure per 1250-tick cycle.

### 7.3 System load and Memory Stick activity (includes the required H10 statement)

- **Load profile.** The collector reproduces telem's per-tick CPU, framebuffer,
  `/proc`, mouse-client and `fsync` pattern (4.1). The three bracketed deaths
  (9.6) happened under that profile. Differences from those runs: the
  instrumented kernel is this tree, not the 2008 image (dossier 9.5 caveat);
  the collector adds `/proc/psptrace` reads (process context, preemptible, no
  locks); it does not read the tty; and it writes about 2.3 KB per `fsync`
  instead of about 40 bytes.
- **Our own stick writes and H10.** Every sector attempt does an LED
  read-modify-write on `0xbe240008`/`0xbe24000c` (`psp.c:401,406`;
  `ms_psp.c:290-292,312-314`). This is the H10 mechanism. **The collector does
  about 2.2× telem's sector operations, at the same `fsync` cadence** (5.3).
  If H10 is real, this raises its rate and death is expected sooner. It does
  not mask it. Two further effects:
  - The writes run non-preemptibly per bio segment inside
    `__bio_kmap_atomic` (`ms_psp.c:254-268`). A larger write lengthens the
    stretch during which the joypad thread cannot run. That delays its start
    within the tick and raises the chance that its transaction straddles a
    tick, which is **H4 exposure**. Again this raises the rate and does not
    mask it.
  - It could create a failure through the same mechanism that would not have
    appeared in the run otherwise. That is not a new mechanism, and it is
    recorded exactly: every sector attempt is an MSIO record with the thread's
    phase and command at LED on/off and the value read back (1.6). Every JOY
    record shows `preempt_delta` and its start offset in the tick.
  The analyst can therefore compute, from the run itself, how many LED
  operations fell inside G3-high windows, and how many transactions
  straddled a Nop tick because an MS stretch delayed them.
- **Decorrelation.** The collector period (≈0.23 s, drifting with work
  time) is not a divisor of 5 s, so its writes sweep all watchdog phases.
  **Confounder:** `pdflush` writeback runs every 5 s
  (`mm/page-writeback.c:80` `dirty_writeback_interval = 5 * HZ`). Our
  per-tick `fsync` leaves little for it to write, but any 5-periodic MS
  activity would appear in MSIO with its `pid`. The decoder tests "onset
  aligned to Nop tick" and "onset aligned to MSIO activity" separately.
- **Memory:** −1.08 MB of the about 20.8 MB free (5.2).
- **Code layout:** changed text alignment could change cache behaviour of the
  spin loops by a cycle at most. G2 confirms the loop bodies are unchanged
  (7.4).

### 7.4 Checks that make this statement verifiable (for G2/Stage 3)

1. `objdump -d` of `Syscon_cmd`: the ordered list of loads and stores to
   `0xbe24xxxx`/`0xbe58xxxx` must equal the baseline object's list
   (`recon/syscon.md` §1.2 table), and the two spin-loop bodies must be the
   same instructions, with register renaming allowed.
2. Count the instructions between S6 and S20, and between S20 and the next
   S13, in the new and baseline objects. Report the added count per segment.
3. `psp_gpio_set/clear`: still exactly one `lw` and one `sw` to the register.
4. On the device: SNAP `append_cost_last` and counter words 225-226 give the
   append cost. The G3-low gap histogram and `ack_spins` give the in-run
   distributions.

### 7.5 Conclusion (S5)

The instrumentation neither adds nor removes any hardware access or
synchronisation on the syscon path. Every timing change it makes is
sub-microsecond inside transactions and is measured in the run. Where it
changes exposure (Memory Stick load, H4 straddle probability), it changes it
**upward and measurably**. The one change that could lower a hypothetical
failure rate (the G3-low gap, 7.2) is measured on every poll. If no failure
occurs in 30 minutes, the report states that and gives these measured
exposures.

### 7.6 Floating point (D18)

The collector uses integer-only code: no `printf` family, no `atof`/`strtod`,
and the CRC32 is table-driven on `unsigned int`. Check method: the
`telem/cbuild.sh:9` recipe (`objdump -d psptrace.gdb | grep -c '[$]f[0-9]'`
must print 0), plus `grep -cE 'lwc1|swc1|ldc1|sdc1|mtc1|mfc1|cfc1|ctc1|cvt\.|\.[sd]\s'` = 0,
plus `nm psptrace.gdb | grep -Ei 'printf|strtod|atof|__.*sf|__.*df'` empty,
plus `flthdr` showing a valid bFLT header and stack 16384.

---

## 8. Self-test

### 8.1 Kernel, at boot

`psptrace_init` (`late_initcall`) prints one line with the ring sizes. It also
checks that the W ring already holds the IRQOFF record of the boot Nop (tick
0, `ctxbits` b0 = 0), and adds `boot-nop ok` or `boot-nop MISSING` to the same
line.

### 8.2 On screen, automatic, from the first HUD frame

The worker draws a full-screen HUD like telem's (pulsing border and heartbeat
block kept, `telem.c:366-373`), at font scale 2 (40 columns × 14 lines):

```
PSPTRACE R003/01          SELFTEST PASS
T 012345 (49.4S) WD 0995/1250  MODE MOUSE
REC TSC 1744 POLL 872 W 48 M 311 LOST 0
RAW 00DF2F12 X        (last 0x08 frame)
CTL +21 E7 ACK 000132 NOP +4 E7 ILV 0
ERR -2:0 -3:0 -4:0 -5:0  HOLD 0  E3 0
LOOP 872 AGE 0.05S STG 18 PI 34 1.2S
MS 00402K SYNC 0.04S MAX 0.09S ERR 0
MEM 19780K KMSG 1920 IN 41 GAP 0S
```

SELFTEST checks, each shown individually until all pass:

| Check | Passes when | Proves |
|---|---|---|
| K | `/proc/psptrace/stream` opens and the chunk magic/version match | kernel side present |
| REC | TSC `seq` advances ≥ 30/s with `LOST 0` and every `check` valid for 3 s | thread-context recording live and consistent |
| CTX | JOY records have `origin 0`, `ctxbits` b0 = 1, b3 = 1; W holds WD records with `origin 1`, `ctxbits` b1 = 1, b0 = 0, b2 = 0 | both contexts recorded and distinguished without `in_interrupt()` |
| WD | every WD Nop record has `tick_in % 1250 == 0`, and the boot IRQOFF record exists | watchdog-cycle alignment works |
| MS | the file's size (`fstat` after `fsync`) grows every tick, and the last `fsync` returned 0 | data reaches the stick |
| BTN | after the worker starts, a JOY 0x08 record's `rx[3..6]` differs from the idle frame. The operator presses and holds × (CROSS); the RAW line shows the new frame and `X` | a physical button press appears **in the recorded raw data** that is being written |

When all pass the line shows SELFTEST PASS in green and a SELFTEST frame is
written. After that, each check keeps running; a later failure turns the
field red (for example a `LOST` count, a check error, or MS errors).

### 8.3 Abort rule (for the runbook and R5)

If SELFTEST PASS is not on screen within **90 s of launching the new folder
from the XMB**, power off and report. This does not count as the run.

### 8.4 Display-only onset hint

The right side of line 1 shows `DEAD?` in red when any of these holds: JOY
0x08 results all negative for 2 s; HOLD branch for 2 s with no HOLD
calibration in progress; `joy_loop` not advancing for 1 s; no `pi_changed`
for 3 s while the INPUT counter was rising before. **It controls nothing.** It
only tells the operator when to start the post-death script. The operator's
own perception is the primary cue.

### 8.5 Host-side (Stage 3, stated here so the design is testable)

The ring and record code compiles on the host with stubbed `REG32` and CP0
accessors. Stage 3 drives synthetic sequences for H1-H10, including a
simulated WD Nop injected at each of phases 1-10 mid-record, collector
restarts, torn records, and truncation at every byte offset. The decoder must
classify each. The volume test simulates 15 minutes and must match 5.1 within
±10 %.

---

## 9. Runbook (summary; full text in `design/candidate-B-RUNBOOK.md`)

- Folder `PSP/GAME/uClinux_TRACE/` (new, not `uClinux`, `uClinux_FIX` or
  `uClinux_WIP`, dossier 9.7), holding `EBOOT.PBP`, `kmodlib.prx` and
  `pspboot.conf` copied verbatim from the baseline, plus our
  `vmlinux-0.22.bin`. Nothing is written to `uClinux/`.
- A stopwatch is started at launch. Photographs are taken with the stopwatch
  in frame at SELFTEST PASS and at minute 5. They calibrate the tick rate
  against wall time (QB4).
- Calibration pass: each button held 1 s in a fixed order; HOLD on and off;
  analog stick extremes. This gives the decoder the real bit patterns needed
  for H2 and H6.
- Enter mouse mode (SELECT). **Reproduce the 9.6 activity:** L-trigger clicks
  at about 4 per second with stick movements, rests of at most 10 s.
- On death (own perception or `DEAD?`): photograph, then the scripted
  post-death pattern (about 2.5 minutes of named holds and releases, HOLD,
  VOL+, SELECT; photos while holding × and while released). Then 60 s hands
  off, a final photo, and the battery pull.
- If there is no death by minute 30: run the same script as a healthy
  control, then pull.
- After the run: raw image of the stick first, then copy `/PSPTRACE/`.
  Return photos and notes.

---

## 10. Decoder specification

Tool: `ptdecode.py`, Python 3, standard library only. It is written by the
Analyst before the run (R6). Inputs: one or more `R*_*.BIN` files and/or a raw
stick image (`--raw`). It never modifies its inputs.

### 10.1 File frames

Frame header, `struct '<IHHIII'` (20 bytes):
`magic` 0x46525450 ("PTRF"), `type` u16, `flags` u16, `len` u32 (payload
bytes, ≤ 4096), `fseq` u32 (per file, from 0), `crc` u32 (CRC-32/IEEE of the
payload). The payload follows, padded with zeros to a multiple of 4
(padding is not included in `len`).

| type | Name | Payload |
|---|---|---|
| 0 | FILEHDR | `"PSPTRACE"` (8), `fmt` u16 = 1, `run` u16, `inst` u16, pad u16, `tv_sec` u32, `tv_usec` u32, `super_pid` u32, then `/proc/version` text |
| 1 | KCHUNK | exactly the bytes of one `/proc/psptrace/stream` read (3.4 header + records) |
| 2 | CNT | exactly the bytes of one `/proc/psptrace/counters` read (1.7) |
| 3 | KMSG | raw bytes read from `/proc/kmsg` |
| 4 | PROC | `path` NUL-terminated, then the raw file text |
| 5 | UHB | 16 × u32 (below) |
| 6 | NOTE | ASCII text (summary mode switch, write errors, SELFTEST state changes) |
| 7 | SELFTEST | u32 bitmask of passed checks K, REC, CTX, WD, MS, BTN (bits 0-5) + u32 tick |

UHB `'<16I'`: `seq`, `elapsed_ds`, `tv_sec`, `tv_usec`, `uptime_cs` (from
`/proc/uptime`, parsed as integer centiseconds), `memfree_kb`, `inputs`
(telem-equivalent mouse press edges), `lastinput_ds`, `kmsg_len` (syslog 3),
`bytes_total`, `last_write_ms`, `last_fsync_ms`, `max_fsync_ms`,
`write_errs`, `last_errno`, `flags` (b0 summary mode, b1-b6 selftest bits,
b7 supervisor alive (`getppid() != 1`)).

### 10.2 Frame recovery

Scan for `magic` at every 4-byte offset. Accept a frame if `len ≤ 4096`, the
file has `len` more bytes, and `crc` matches. Otherwise advance 4 bytes. A
truncated tail frame is reported and dropped. Every earlier complete frame is
recovered (Stage 3 truncation test). `--raw` does the same over a raw device
image. It groups frames by (run, inst) through the nearest preceding FILEHDR
and `fseq` continuity. A frame split across non-contiguous clusters is lost
(reported as an `fseq` gap).

### 10.3 Record parsing (field-for-field with section 1)

`struct` formats (little-endian; sizes verified):

```
SC    '<BBHI IIIII I BBH 8s16s h BBBBBB H BB II IIII IIIIIII III H BBBB H'   = 144
      type ring len seq | tick_in cnt_in tick_out cnt_out jif_in | tick_len |
      origin ctxbits pid | tx rx | result | exit nwords attempts phase_last first_exit first_rx2 |
      exits_mask | wd_during/intr_origin wd_hit_phase/intr_phase | cmd_id link |
      ack_spins drain_n drained0 drained1 |
      r_gpio04 r_spi0c_s7 r_spi0c_s9 r_spi0c_tx0 r_g20_first r_g20_last r_spi0c_rxend |
      cnt_g3hi cnt_ack cnt_s20 | preempt_delta | dtick_g3hi dtick_ack dtick_s20 reserved | check
POLL  '<BBHI III I BBBB BBBB I BbbB I BBH II H bb H H'                        = 64
      hdr | tick_start cnt_start loop | keys_raw | x y ri_branch pi_flags |
      nqueues push_ok push_full push_eintr | keys_pi | mouse_flags dx dy sig |
      cmd_id_first | nsc stage_max preempt_delta | tick_end cnt_end | period | ast_res gc2_res | reserved | check
SNAP  '<BBHI III I BBBB I I IIII I IIII IIII IIII hh BBH I I I H H'           = 128
      hdr | tick cnt jiffies | joy_loop | joy_stage joy_phase joy_state joy_sig | joy_stage_arg |
      joy_sigword | head_tsc head_tpoll head_w head_m | head_o |
      gc2_calls gc2_neg ri_hold ri_true | pi_changed push_ok push_fail mouse_reports |
      fop_read_ret vcs_putchar md_notify_calls md_read_ret | console_sem_count list_sem_count |
      qfree_stage console_blanked nop_count16 | tick_len_max | long_ticks | reader_last_tick |
      append_cost_last | check
MSIO  '<BBHI II I I I I h BB BB H I H H'                                        = 48
      hdr | tick_on cnt_on | cnt_off | sector | set_rd | clr_rd | rt | op dtick_off |
      t_phase_on t_phase_off | pid | t_cmd_on | nop_count16 | check
CHUNK '<I HH I I III IIIII HHHHH H I'                                           = 64
CNTHDR '<IHHIIIIII' (32) followed by '<280I'
```

Per record: verify `len` against `type`, verify `check` (1.0). Records
failing either are kept in `bad.csv` with their raw hex and are never used for
classification. Deduplicate by `(ring, seq)`. Report `seq` gaps per ring,
together with the chunk-header `lost` counts, as **explicit gaps in the
timeline**.

### 10.4 Timeline, onset and classification

- **Clock:** sort key `(tick, cnt)`. Seconds = `total_counts` interpolation
  from CNT headers, with 220,912,896 counts/s as nominal, corrected by the
  stopwatch photos if given (`--photo tick=...,wall=...`). `wdph = tick mod 1250`.
  Assert that every WD record has `wdph == 0`, and report any exception.
- **Straddles and interleaves:** list every JOY SC with `tick_out ≠ tick_in`,
  and every WD record with `intr_origin == 0`, joined to its JOY record by
  `link == cmd_id`. Print the recon point (1.1 table; P4 vs P5a by WD
  `r_gpio04 & 0x10`) and both records in full.
- **Onset candidates** (all reported, none assumed): O1 is the last POLL with
  `pi_flags` changed and a delivery (push_ok > 0 or mouse reported), after
  which none occur for ≥ 10 s until the end. O2 is the first JOY SC after
  which ≥ 90 % of 0x08 records are not "`exit 7` with `rx` in the pre-onset
  valid-frame set". O3 is the last `joy_loop` increment, if it stops. O4 is
  the last `fop_read_ret` / `md_read_ret` increment. For each: tick, `wdph`,
  nearest WD record (Δ), MSIO records within ±100 ms, and the ±15 s window
  dumped raw.
- **Rules:** each row of section 6 is coded as a predicate over the records in
  `[onset - 1 poll, end]`, with the thresholds written in the tool: e.g. H1 =
  ≥ 90 % of post-onset JOY SC with `result ∈ {-3,-4}`; H4 = a WD record with
  `intr_origin 0` whose `tick` lies in `[O - 2 polls, O]` for the chosen
  onset O. The report lists **every** matching row with its evidence records
  (ring, seq). It gives "trigger" and "state" separately, for example
  "trigger H4 at P5a, state H3". If nothing matches it reports **H0 /
  unclassified** and dumps the raw windows.
- **Outputs:** `sc.csv`, `poll.csv`, `snap.csv`, `msio.csv`, `counters.csv`
  (one row per CNT frame, all 280 words named per 1.7), `uhb.csv`,
  `kmsg.txt`, `proc.txt`, `supervisor.txt`, `bad.csv`, `gaps.txt`,
  `timeline.txt` (merged, human-readable), and `REPORT.txt` (classification,
  exposures from 7.3: LED ops inside G3-high, straddles per Nop, G3-low gap
  distribution, measured append cost, max `fsync` and the actual loss bound).

---

## 11. Open risks (every place this design guesses)

1. **Allegrex CP0 Status.IE bit semantics** (UNVERIFIED). This is used only
   for IRQOFF (boot Nop) classification. The WD flag is authoritative, and the
   raw bit is recorded.
2. **Instruction-cost estimates** (5.4) assume about 1 CPI when cached and
   Count ≈ CPU clock (`psp.c:38` "measured by tests"). Measured on the device
   by `append_cost_*`; the window cost comes from the compiled object (7.4).
3. **Original G3-low gap length is unknown.** The added ≈0.45 µs might be a
   significant fraction of it, and could lower the rate of a hypothetical
   "gap too short" failure (7.2). Measured every poll, but not avoidable
   without deferring entry bookkeeping further.
4. **Memory Stick throughput and `fsync` duration** are UNKNOWN. They set the
   battery-pull loss bound (4.5) and the non-preemptible stretches (7.3). The
   runbook enforces W_max ≤ 2 s or a longer wait.
5. **Sector-operation rate** (≈ 28/s vs telem's ≈ 13/s) is an estimate from
   the `fsync` path. The FAT cluster size is unknown.
6. **P4 vs P5a split** relies on `0xbe240004` bit 4 being the GPIO4 input
   level, inferred from a commented debug line (`syscon.c:146,155`).
   UNVERIFIED. If it is wrong, step 5 remains "P4 or P5a".
7. **`psptrace_tick == localTick`** is derived from the source (1.2). If
   anything else calls `psp_watchdog_tick`, the decoder detects it (WD records
   off the 1250 grid) and falls back to WD record ticks as the phase
   reference.
8. **`nivcsw` counts only switches of the thread itself**
   (`kernel/sched.c:3626-3628`). A preemption that happens and returns is
   counted. A switch while the thread is in a voluntary sleep cannot happen
   inside `Syscon_cmd` (no sleeping calls there).
9. **O ring** tolerates only one writer at a time. A concurrent tear is
   detected, not prevented.
10. **Supervisor death** is not recovered (4.2). The worker detects it
    (`getppid() == 1`, UHB flags b7) and keeps running, but a later worker
    crash would then not be restarted.
11. **Busybox 1.7.0 `msh` behaviour** for `psptrace&` is assumed identical
    to the existing `pspmd -s&` line. `vfork`/`execve` on uClibc no-MMU is
    assumed standard (UNVERIFIED on this device).
12. **Collector mousedev client.** It reproduces telem's client but is a new
    process that may crash and close. A close racing `mousedev_notify_readers`
    is the I9 mechanism (`recon/input.md` §3.2). Only a crash triggers it, and
    the supervisor records every crash.
13. **Console blanking at 10 minutes** (`drivers/char/vt.c:174`). If input
    died and the console later blanks, the HUD may go dark (the PSP fb blank
    behaviour is UNVERIFIED). Data keeps streaming. The runbook's photographs
    are all taken within about 4 minutes of death. The blank interval is
    deliberately **not** changed, because `psp_lcd_on` → `do_unblank_screen`
    is itself a candidate path (`recon/input.md` §1.7).
14. **2008 image vs this tree** (dossier 9.5, 9.7). The instrumented kernel
    descends from the rebuilt tree, which did die on the same timescale
    (observation 6), but the bracketed 5 s evidence is from the 2008 image.
15. **Operator activity reproduction** assumes the 9.6 sessions were mouse
    mode with continuous L-trigger clicking about 4/s (telem's INPUT counts
    mouse button press edges, `telem.c:270`). New question for the operator:
    what exactly was being done?
16. **HUD readability in photographs** at scale 2 is assumed.
17. **Decoder thresholds** (90 %, 10 s, ±15 s) are judgement calls. The raw
    windows are always emitted, so a wrong threshold cannot hide data.
18. **Ring sizes vs collector outage:** 114 s covers restarts and slow syncs,
    but not a collector hung for longer. After that, only W (853 s) and the
    counters remain complete. RAM is lost on a pull anyway.
19. **Stick free space:** 118,999 MB is the disk size from `kmsg.txt`, not
    free space. The 256 MB start check guards it.
20. **`pdflush` 5 s writeback** is a potential confounder for H4 (7.3).
    Handled by recording, not by prevention.
21. **Summary-mode cap** (128 MB) is arbitrary. It is 3.5 hours, beyond any
    planned run.
