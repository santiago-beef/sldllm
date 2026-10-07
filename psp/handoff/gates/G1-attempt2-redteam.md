# Gate G1, attempt 2: red team report

Artifact under review: `design/DESIGN.md` and `design/RUNBOOK.md`, revision 1
(2026-09-30, after the G1 attempt-1 FAIL).
Reviewer role: G1 red team, attempt 2. Fresh context. I did not write the
design or the attempt-1 reports.
Date: 2026-10-01.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding), `WORKFLOW.md`, `recon/syscon.md`, `recon/input.md`,
`recon/build.md` (sections 0-4; the rest is packaging), `gates/LOG.md`,
`gates/G1-attempt1-redteam.md`, `design/DESIGN.md`, `design/RUNBOOK.md`.

Source was only read: `/home/ubuntu/psp/build/linux` directly, and the
built objects through the toolchain container with `/home/ubuntu/psp`
mounted **read-only**. Nothing was written in either kernel tree. Kernel
paths below are relative to `/home/ubuntu/psp/build/linux`.
"DESIGN:n" and "RUNBOOK:n" are line numbers in the two artifact files as
they stand on 2026-10-01. Anything the source cannot settle is marked
**UNVERIFIED**.

---

## Verdict: FAIL

One scenario is **BLIND** (IF4). Three are **AMBIGUOUS** (TE4, OE3, OE4),
each with a concrete fix. Thirteen are **DIAGNOSABLE**.

Of the 11 attempt-1 scenarios, ten are now DIAGNOSABLE. OE3 stays
AMBIGUOUS because the fix that was adopted counts whole ticks, and the
delays that create the H4 exposure are shorter than one tick. Both
attempt-1 BLINDs (IF2, OE1) are closed.

The new BLIND (IF4) is in the same family as attempt-1 IF2: a benign
error pattern permanently stops the stick stream. The design itself says
this cannot happen (DESIGN:1277-1280).

| # | Group | Scenario | Attempt 1 | Attempt 2 |
|---|---|---|---|---|
| UL1 | unlisted-shape (H10) | LED RMW disturbs the syscon through a non-G3 bit (bit 4, ACK line) | AMBIGUOUS | **DIAGNOSABLE** |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off | DIAGNOSABLE | **DIAGNOSABLE** |
| UL3 | unlisted-shape (new) | Link stays one reply behind after an interleave; every command receives the previous command's reply | – | **DIAGNOSABLE** (decoder hardening recommended) |
| UL4 | unlisted-shape (new) | Valid frames with the HOLD bit stuck on; R4 forever | – | **DIAGNOSABLE** |
| TE1 | timing-edge | Death at 5 s (first Nop), 17 s, 36 s: before PASS, C0 or a template | AMBIGUOUS | **DIAGNOSABLE** |
| TE2 | timing-edge (Nop before `irq_enter`, IRQs off) | Nop lands while the thread is suspended after the I cap is spent | AMBIGUOUS | **DIAGNOSABLE** |
| TE3 | timing-edge | Minute 14 during `fsync`; 29:50; 16-bit link wrap; console blank | DIAGNOSABLE | **DIAGNOSABLE** |
| TE4 | timing-edge (new; straddles a watchdog tick; Nop before `irq_enter`, IRQs off) | A slow Nop makes the next tick nest inside the softirq; T2a overwrites the thread's suspension point with a softirq EPC | – | **AMBIGUOUS** |
| IF1 | instrumentation-fault | Transient write/`fsync` failure across onset | AMBIGUOUS | **DIAGNOSABLE** (for bursts that do not trigger IF4) |
| IF2 | instrumentation-fault | Worker killed at minute 13-14 | BLIND | **DIAGNOSABLE** (one minor defect noted) |
| IF3 | instrumentation-fault | `/proc` reader races every writer; head corrupted | DIAGNOSABLE | **DIAGNOSABLE** |
| IF4 | instrumentation-fault (new) | Write errors on about 98 collector ticks (contiguous or spread over the run) use up the two-digit segment names; nothing reaches the stick again | – | **BLIND** |
| OE1 | observer-effect (collector's own stick I/O) | MS driver spins forever with a raised preempt count | BLIND | **DIAGNOSABLE** |
| OE2 | observer-effect | Start-up `statfs` FAT scan | AMBIGUOUS | **DIAGNOSABLE** (scenario removed) |
| OE3 | observer-effect | Collector load, not its instructions, sets the H4 exposure | AMBIGUOUS | **AMBIGUOUS** (residual: sub-tick delays) |
| OE4 | observer-effect (new) | `pscol` runs with kernel privilege (no MMU, `KU_USER` not set on PSP); a stray store corrupts kernel state or GPIO, which looks like H7/H9/N5/N1 | – | **AMBIGUOUS** |
| OE5 | observer-effect (new) | A collector death or SIGTERM takeover closes a mousedev client while the thread is preempted mid-walk (mousedev I9) | – | **DIAGNOSABLE** (counter recommended) |

---

## 1. Source facts the scenarios rest on (re-verified by me)

| # | Fact | Evidence |
|---|---|---|
| F1 | Timer handler order: Count reset, watchdog tick (and the Nop, IRQs off), UART tick, then `do_IRQ`, which leads to `irq_enter`, `do_timer` and softirqs. | `arch/mips/psp/psp.c:348-368` (reset `:351-356`, `:359`, `:363`, `:367`); `psp_watchdog_tick` `:370-380` |
| F2 | Every tick raises `TIMER_SOFTIRQ`, and `__do_softirq` runs it with **interrupts enabled**, with the softirq count raised. | `arch/mips/kernel/time.c:143` (`update_process_times`); `kernel/timer.c:819`, `:885`; `kernel/softirq.c:217` (`__local_bh_disable`), `:225` (`local_irq_enable()`), `:298-304` (`irq_exit` → `invoke_softirq`) |
| F3 | Kernel preemption happens only at an interrupt return with `preempt_count == 0` and IE set in the saved Status; `TI_REGS` is restored before it. | `arch/mips/kernel/entry.S:39`, `:61-73` |
| F4 | Count is reset at handler entry and Compare is fixed, so if a handler runs at least one tick (≈ 883,651 counts) before `__do_softirq` enables interrupts, IP7 is already pending and the next tick's handler **nests inside the softirq** on the same stack, with `current` unchanged. | F1, F2; `psp.c:38-39`, `:611-618` (Compare set once); `plat_irq_dispatch` services IP7 `psp.c:641-645` |
| F5 | The MS driver retries a failing sector 10 times with `mdelay(1)`, inside `__bio_kmap_atomic` (preempt count raised), with 2 LED RMWs per attempt, then returns −EIO for the bio. | `drivers/block/ms_psp.c:38`, `:252-276`, `:304-326`, `:355-379`; `include/linux/highmem.h:49-56` |
| F6 | A failed buffer write is not retried: "lost page write" / "Buffer I/O error" is printed and `AS_EIO` is set, so `fsync` returns EIO. | `fs/buffer.c:103-107`, `:445-449` |
| F7 | `ms_wait_ready` and `ms_wait_ced` have no bound. The MS path never masks interrupts. | `arch/mips/psp/ipl_sdk/memstk.c:59-65`, `:174-181`; no `irq`/`Intr` in that file (grep) |
| F8 | **User processes on this port keep kernel privilege**: `start_thread` sets `KU_USER` only `#ifndef CONFIG_SONY_PSP`, and `USER_DS` is defined as `KERNEL_DS`, so `access_ok` never rejects an address. A userland store can reach any RAM or MMIO (`0xbe24xxxx`). | `arch/mips/kernel/process.c:71-84`; `include/asm-mips/uaccess.h:58`, `:107-113`; `.config:11` (`# CONFIG_MMU is not set`), `.config:50` (`CONFIG_SONY_PSP=y`) |
| F9 | `mousedev_release` unlinks and frees the client with no list lock, while `mousedev_notify_readers` walks the same list and is preemptible between clients. `list_del` leaves `LIST_POISON1` = `0x00100100`. | `drivers/input/mousedev.c:235`, `:439-440`; `include/linux/poison.h:10` |
| F10 | The reply's third byte is the response code, which for 0x00-0x7f is "response of COMMAND 00-7f", i.e. it names the command that the reply answers. | `include/asm-mips/ipl_sdk/syscon.h:55-58` |
| F11 | Key bits: SELECT `0x100`, HOLD `0x2000`, MOUSE_MODE `0x800000`; the word is inverted and HOLD returns FALSE. | `drivers/input/joypad_psp.c:44`, `:49`, `:58`, `:490-493` |
| F12 | vfat starts the free-cluster search at the FSINFO next-cluster hint, not at the start of the FAT; it never scans the FAT for a free count without `statfs`. | `fs/fat/inode.c:1274-1275`, `:1311-1314`, `:540-541`; `fs/fat/fatent.c:455-460` |
| F13 | `telem`'s number formatter is variable width; there is no zero-padded helper to inherit. | `/home/ubuntu/psp/telem/telem.c:143-151` |
| F14 | Baseline frames: `_pspSysconGetCtrl2` has a 64-byte frame with `rx_buf` at `sp+32`; `psp_joypad_read_input` is inlined into `psp_joypad_thread` (72-byte frame). So the unbounded checksum (`syscon.c:228-240`) reads GetCtrl2's saved registers and then the thread's own frame. | `objdump -d` of the tree's `syscon.o` (`+0x588..+0x5c0`) and `joypad_psp.o` (`+0x94c..+0x978`), read-only container |

---

## 2. Attempt-1 scenarios re-run against revision 1

### UL1 (H10). LED RMW disturbs the syscon through bit 4, not G3. Re-run: DIAGNOSABLE

**Sequence.** At tick k the thread is in S14 (G3 high, waiting for the ACK,
`syscon.c:151-156`) and is preempted at the IRQ return (F3). `pscol`'s
`fsync` writes sectors. Each attempt does `psp_led_ctrl` on and off
(`ms_psp.c:312-314`), a read-modify-write of `0xbe240008`/`0xbe24000c`
(`psp.c:399-407`). The read of CLEAR returns bit 4 set, the write-back
disturbs the ACK (hardware effect UNVERIFIED), the ACK is lost, and the
thread returns −4.

**What revision 1 records.**
- Tick k, T2a (DESIGN:585): `lc_epc` = S14, `lc_tick` = k, `lc_r`.
- Each LED op, hook (DESIGN 2.4, lines 614-650): `led_cmd_or |= v` (bit 4
  set), `led_cmd_pid` = the `pscol` pid, `led_bit_clr[4]++`, run-wide
  OR/AND.
- S records: `rd_clr_or & 0x10`, `flags` b4/b5 (P in flight), pid.
- P08 (DESIGN:186-210): `ret −4`, `ack_polls 1,000,001`, `nwords 0`, `rx`
  all `ff`, `ms_delta ≥ 2`, `ms_b3 0`, `preempt_delta ≥ 1`, `lc_epc` in
  S14 with `lc_flags` b0/b2, `led_or & 0x10 ≠ 0`, `led_pid` = `pscol`.
- Stats: run-wide per-bit read-back counts.

**Decoder.** Row H10 (DESIGN:1487) matches: `ms_delta > 0`,
`preempt_delta > 0`, `lc_epc` in S13..S20, S overlap, and
`led_or & ~0xC0 ≠ 0`. The report gives "H10 trigger (bit 4)". The false
"refuted" verdict of attempt 1 is gone: refutation now needs a
demonstrated overlap with a clean read-back (DESIGN:1487, 10.7 step 5).

**Ruling: DIAGNOSABLE.** One residual is reported as TE4: when the
preempting tick has a nested tick inside its softirq, `lc_epc` is
overwritten and this row stops matching.

### UL2. One foreign frame toggles mouse mode off. Re-run: DIAGNOSABLE

**What revision 1 records.**
- The W record of the interleave: step, Nop `rx`/`ret`.
- The foreign P08. Its `rx[2]` names another command (F10). Or it is an
  E4 frame (`ret 0`, `nwords ≥ 1`).
- That poll's POLL: `pi_flags` b3 = 1, b4 = 0.
- Later polls: `mouse_flags` b0 = 0 while raw `rx` follows the script. HUD
  `MOUSE OFF`.

**Decoder.** Row N10 (DESIGN:1503) names the shape, and the 10.7 step 3
toggle report ties it to the frame. RUNBOOK D7a (SELECT tap, five L
clicks) re-toggles the mouse after death, so the recording itself confirms
it.

**Ruling: DIAGNOSABLE.**

### TE1. Early death: 5 s (the first watchdog Nop), 17 s, 36 s. Re-run: DIAGNOSABLE

**Trace, first 10 s.** The thread starts at the device initcall. The
first WT Nop runs at `psp_local_tick` = 1250 (`psp.c:375-379`), about 5 s
after the timer starts. Say it interleaves and input dies there.

- **Rings.** All rings are BSS, zeroed before `start_kernel` (DESIGN 3.1).
  They already hold the WB record (seq 0, `prom_init`, `psp.c:557`), the
  boot M record (`serial_psp.c:352`), every P/POLL from the thread's
  first poll, and the W/I records of the Nop.
- **Collector.** It starts later from `rc.sysinit` (time UNVERIFIED,
  well under the 114.7 s P/POLL span) and drains the backlog in capped
  catch-up flushes (DESIGN 4.3).
- **HUD.** `POLL:NW0`, `POLL:RET` or `POLL:RATE` (by shape), or BTN fails.
  The early-death exception (DESIGN 8.3, RUNBOOK B) sends the operator to
  section D, so the run is not aborted.
- **Decoder.**
  - Template window = first P record to onset − 5 s, which is under
    10 s, so the decoder prints `NO HEALTHY TEMPLATE` and marks H8 and N2
    "unassessable" (DESIGN:2091-2110).
  - H1, H2, H3, H5 and H9 are absolute rules and still classify.
  - The H4 trigger comes from the W record.
  - H6/H7 use the source bit map, flagged `no C0 reference`
    (DESIGN:1473-1483).

**Deaths at 17-60 s.** C0 now runs immediately after B6, so it exists for
most deaths after PASS. The PANEL test paint and any start-up catch-up
fall in this window. Paints happen only at ticks ≡ 125 mod 250, are
counted (`panel_paints`, `panel_last_tick`), and the decoder flags an
onset within 1 s of a paint or during a catch-up (DESIGN:1532, 10.7
step 4). The extra start-up Memory Stick load is declared (DESIGN 7.4).

**Ruling: DIAGNOSABLE.**

**Recommendation (not blocking).** When there is no template, use the WB
record, the boot M record and the first WT records as the H8 baseline.
They carry `gpio_in`, `spi_st9`, `spi_sttx`, `drain`, `drain_last` and
`ack_polls` captured before the thread ran, so even a 5 s death has a
pre-onset reference for H8.

### TE2 (Nop before `irq_enter`, IRQs off). Nop lands on a suspended thread after the I cap is spent. Re-run: DIAGNOSABLE

**Exact attempt-1 sequence, traced through revision 1.**

| Tick | What happens | What revision 1 stores |
|---|---|---|
| k | Thread at S12, preempted at the return | I sample 0; `lc` = S12 |
| k+1 .. k+3 | Another task runs | I samples 1-3 with `flags` b2 = 0; no `lc` update (T2a needs `current == thread`) |
| between ticks | Thread resumes and runs to S18 | – |
| k+4 | Thread current at S18; I cap reached, sample suppressed | T2a stores `lc_epc` = S18 and `lc_r` holding `t0` = `i`, `a3` = `ptr` (DESIGN:585) |
| k+4 return | Thread preempted | – |
| k+5 (WT) | The Nop drains the rest of the reply (P6) | W extension: b4 = 0, b5 = 1, `lc_epc` = S18, `lc_r` (DESIGN:254, 400-432) |
| afterwards | Thread resumes | `ret −2`, `nwords = j` |

**Decoder.** The H4 step comes from `lc_epc` (DESIGN:1481): S18, P6. The
outcome cross-check table (10.7 step 5, P6 row: −2 with `nwords` = j)
agrees.

**Ruling: DIAGNOSABLE.** This depends on R31 (`i` and `ptr` staying in
`lc_r` registers), which G2 checks from `regmap.txt`. The one case in
which this fix breaks is TE4.

### TE3. Minute 14 during `fsync`; death at 29:50; 16-bit link wrap; console blank. Re-run: DIAGNOSABLE

- **Minute 14, mid-`fsync`.** The onset records are drained at the next
  tick and durable one flush later. D8 (RUNBOOK:253) pulls only with a
  moving heartbeat and no panel, which bounds the loss at ≤ 4 s before the
  check, inside the 30 s hands-off wait.
- **Field widths.** Nothing saturates by minute 14: `dtick`/`lc_dtick` are
  u16 (262 s), the W ring spans 1,280 s, and the rings are streamed.
- **Link wrap.** The P link fields wrap at 65,536 records, about 30.6 min.
  A 30:00 control plus D8's 90 s crosses it once, and the decoder's
  nearest-value expansion (DESIGN 10.3) handles one wrap.
- **Death at 29:50, run through C6 as a control.** The data still shows
  the onset at 29:50.
- **Console blank.** The blank at about 600 s (`drivers/char/vt.c:174`)
  exercises the N4 path (`psp_lcd_on` → `do_unblank_screen`) in every run
  that is clicking. It is recorded (`pi_flags` b2, `jp_lcd_unblank`). If
  the screen is dark at D8, D8 (c) applies, and the true loss is
  recomputed from the last `durable_tick` on the stick (10.7 step 6).

**Ruling: DIAGNOSABLE.**

### IF1. Transient write or `fsync` failure across onset. Re-run: DIAGNOSABLE (for bursts below the IF4 limit)

**Trace.**
1. A sector fails 10 times with `mdelay(1)` and the bio gets −EIO (F5).
2. The buffer layer prints "lost page write" / "Buffer I/O error" and
   sets `AS_EIO` (F6), so `fsync` returns EIO.
3. The worker counts the error, turns `MS` red, closes the segment, opens
   the next one, seeks each ring back to `durable_seq + 1`, writes an
   EVENT "rewind" and drains again (DESIGN:1266-1280).
4. `durable_tick` is frozen, so the panel appears after 3 s with a rising
   `DUR`.

**What reaches the stick after the burst.** Every record of the burst
interval is re-sent, and the decoder removes duplicates by (ring, `seq`).
The S records carry `flags` b1 (error) and `led_ops` = 20 per failing
sector. KMSG carries the buffer messages.

**Ruling: DIAGNOSABLE**, provided the burst does not use up the segment
names (IF4).

### IF2. Worker killed at minute 13-14. Re-run: DIAGNOSABLE (minor defect noted)

**What revision 1 does.**
- The worker never exits on a runtime error.
- A pre-spawned standby takes over through a pipe with no new allocation
  (DESIGN:1001-1039). The process image is now ≤ 128 KB (order 5), so any
  later standby spawn is far easier.
- Failed spawns are logged with `buddyinfo` through the active worker.
- A stalled worker is taken over after 30 s.
- If a second worker death cannot be recovered, the kernel panel appears.

**Trace.**
1. The supervisor sees the death through `waitpid` within 2 s and writes
   `GO`.
2. The standby opens a new segment and seeks each ring to
   `durable_seq + 1`.
3. Catch-up drains the gap.
4. EVENT chunks record the promotion.

An input death after the kill is on the stick.

**Ruling: DIAGNOSABLE.**

**Minor defect (fix recommended).** `durable_seq[r]` is 0 both for "seq 0
is durable" and for "nothing is durable yet". The promoted standby seeks
to `durable_seq + 1` unconditionally (DESIGN:722, 1044-1047), so a
promotion before the first durable flush skips seq 0 of every ring. That
includes the boot WB record. The WDOG self-test needs "W `seq` 0 exists
with origin WB" (DESIGN:1786), so it can then never pass, and the abort
rule fires at 2:00, even during an early death. Fix: publish the next
sequence number to send, or add a valid flag per ring.

### IF3. `/proc` reader races every writer; ring head corrupted. Re-run: DIAGNOSABLE

The protections of attempt 1 are still in place:
- the seq-invalidate/publish writer and the before/after `seq` check on
  read (DESIGN 3.4-3.5);
- the `total_counts` high-low-high read (DESIGN 1.8);
- `head_regress` with a collector resync and EVENT (DESIGN 3.5 step 5);
- forward jumps appear as counted `lost` gaps.

Corruption of heads by **userland** stores is a separate exposure on this
port (F8); see OE4.

**Ruling: DIAGNOSABLE.**

### OE1 (fault in the collector's own stick I/O). MS driver spins forever with a raised preempt count. Re-run: DIAGNOSABLE

**Trace.**
- `pscol` is inside `ms_wait_ready`/`ms_wait_ced` (F7), with the preempt
  count raised inside `__bio_kmap_atomic`. No task switch happens again
  (F3), but the timer interrupt keeps running because IRQs are on (F7).
- Once a second, T2d sees `now − durable_tick > 750` and
  `now − last_reader_tick > 750` and paints the panel (DESIGN:746-800).
  The panel shows:
  - the running task's EPC (inside the MS wait, `epcmap.txt`) and
    `preempt_count > 0`;
  - the MS in-progress marker: sector, pid, start tick (DESIGN 2.4);
  - the frozen `jp_loop`;
  - the last P08 and the last W record.
- The operator photographs it (RUNBOOK C4, D0-D8). Everything up to the
  last durable flush is on the stick. The decoder labels the panel
  "Memory Stick driver hang (instrumentation exposure)" (DESIGN 10.8).

**Ruling: DIAGNOSABLE.** The event is identified and attributed to the
instrumentation, so S1 and S5 are met.

**Residual, accepted by me as a judgement call (J17), not a finding.**
Such a hang still uses up the run. If a genuine onset happened less than
one flush before the hang, its window is in RAM only.

### OE2. Start-up `statfs` scans the whole FAT. Re-run: DIAGNOSABLE (scenario removed)

The device no longer calls `statfs` (DESIGN 4.4, J20).
`fat_count_free_clusters` has no other caller (F12), so the scan cannot
occur.

**Residual.** The first cluster allocation scans from the FSINFO
next-cluster hint (`fs/fat/inode.c:1314`, `fs/fat/fatent.c:455-460`).
That is bounded by the length of the used run after the hint, which is
UNVERIFIED for this stick. It appears as S read records with `pscol`'s
pid in the first catch-up, and the decoder flags onsets during catch-up.

**Ruling: DIAGNOSABLE.**

### OE3. Collector load sets the H4 exposure; a no-death run cannot be attributed. Re-run: AMBIGUOUS (narrowed)

**What was fixed.**
- T2c counts ticks at which the thread is runnable but not running, by
  the class of `current` and by `preempt_count` (DESIGN:587, stats
  145-160, POLL `wait_ticks/cls/pcnt` DESIGN:355-357).
- The no-death inference is pre-registered (DESIGN 7.3, 10.7 step 7):
  1 − 0.05^(1/n) per P-point, and a conclusion at p ≥ 0.1 only if
  n(P4) + n(P5a) ≥ 30.

**What is still not recordable.**
- The Nop of tick k runs before tick k's wake-ups (F1). It can only hit a
  command that started in tick k−1 and is still in flight at the edge.
- The thread is woken by its `msleep` timer in tick k−1's softirq (F2).
- So a P4/P5a exposure needs the thread's start to be delayed, inside
  tick k−1, to within one command duration of the next edge. That delay
  is **shorter than one tick**, and the thread waits through it without a
  tick boundary passing.
- Therefore T2c never sees it: `wait_ticks = 0`, `wait_cls = 0`. Only the
  late `c_start` is recorded, not who ran.
- S records attribute the Memory Stick portions (pid, `c_on`/`c_off`).
  The CPU-bound portions are not attributed: `pscol`'s 272-row HUD
  render, its `/proc` parsing, and `psposk2`/`pspmd`, all
  equal-priority tasks the O(1) scheduler does not preempt
  (`kernel/sched.c:171-172`).
- PROCS CPU times every 2 s are far too coarse.

So DESIGN:1582-1583 ("the decoder reports the share of the thread's start
delay attributable to each class, and in particular to `pscol`") cannot
be met for exactly the delays that create H4 exposure. If n(P4) + n(P5a)
< 30, the "inconclusive" report carries a `pscol` share computed from the
wrong delays.

**Ruling: AMBIGUOUS.**

**Fix needed.** Add a context-switch hook in `schedule()`/`context_switch`
(`kernel/sched.c`). While the joypad thread is runnable but not running,
from its wake-up in `try_to_wake_up` to its switch-in, it accumulates
Count per class of `prev` at each switch, and per `preempt_count`. The
POLL record then gets:
- the start delay since wake-up in Count units;
- the class that held the CPU longest in that delay;
- that class's share.

The decoder attributes late starts (`c_start` > CPT − median command
duration) by class from these fields, not from `wait_hist`. State the
hook's cost in 7.1. It is outside the syscon path.

---

## 3. New scenarios

### UL3. The link stays one reply behind after an interleave (unlisted shape). DIAGNOSABLE, decoder hardening recommended

**Shape.**
- Recon §5.1 P3: TXF holds T's frame and then N's frame. N reads T's
  reply, and N's words may stay in TXF, in which case T receives the Nop's
  reply.
- Recon §1.3: TXF is never flushed, and whether it can hold residue
  across calls is UNKNOWN.
- Suppose, after such an interleave, the syscon stays **one reply behind**
  for the rest of the boot. Every command receives the reply to the
  previous request.
- In each poll, 0x08 receives 0x33's reply, and 0x33 receives the
  previous poll's 0x08 reply. The Nop receives whatever preceded it.
- This is a permanence mechanism for an H4 trigger that is not in
  H0-H10. It gives input death with a healthy-looking link.

**What the design records.**
- **P08.** `ret` = 0x33 reply's status byte (normally non-zero: the
  power-switch bit, `include/asm-mips/ipl_sdk/syscon.h:36-42`), so E7
  with a valid checksum;
  `nwords` = 0x33 reply length. `rx[2] = 0x33` (F10).
- **`rx[3..8]`.** The checksum byte and `ff` padding, constant. So
  `~key` has no buttons, HOLD is clear, R5 holds, and dedupe follows.
  Analog `ff` gives drift in mouse mode.
- **P33 records.** GetCtrl2-shaped frames with `rx[2] = 0x08` whose
  bytes **follow the D-script presses**, one poll late.
- **W records.** The Nop's `rx` is a ctrl frame (`rx[2] = 0x08`) or a
  0x33 frame.
- `drain = 0` on every command, so nothing is left in RXF.

**Decoder.**
- Row H6 (DESIGN:1483) matches on P08 alone: `ret > 0`, valid checksum,
  `rx[3..8]` byte-identical across the script, and C0 showing changes.
- Row N2 (DESIGN:1494) lists "`drain > 0` on every command" first, then
  "`rx[2]` echoes the previous command's response; the decoder checks
  `rx` against `cmd`". Whether those are a conjunction is not stated.
  - Read as a conjunction: only H6 matches, and the report says "the
    syscon answers with the same state whatever is pressed". That is the
    wrong mechanism, and the wrong answer to "is the syscon still reading
    buttons" (it is).
  - Read leniently: H6 and N2 are both listed.

**Ruling: DIAGNOSABLE.** The discriminating fields are recorded and the
matrix already names one of them: `rx[2]` against `cmd` in P, W and M
records, and press-tracking P33/W frames.

**Recommended (not blocking).**
- Make the `rx[2]`-against-`cmd` check a standalone rule (call it N2b,
  "reply lag"), not conditional on `drain`. It should test whether
  command n's `rx[2]` equals command n−1's command byte across the
  merged P+W+M timeline.
- Make H6 require `P08.rx[2] == 0x08`, and require that no P33 or W
  record carries a GetCtrl2-shaped frame that follows the presses.
- Add the sequence to Stage 3.

### UL4. Valid frames with the HOLD bit stuck on (unlisted shape). DIAGNOSABLE

**Shape.** After onset the syscon returns well-formed GetCtrl2 frames
(`rx[2] = 0x08`, valid checksum, `ret > 0`) whose other bits follow
presses. Raw `rx[4]` bit 5 is stuck at 0, so `~key` has HOLD set and
`read_input` returns FALSE through R4 every poll (F11). The cause could be
a syscon switch-state latch or a real slider fault. Input is dead and the
kernel is healthy.

**What the design records.**
- P08 frames as described.
- POLL `ri_branch = 4` every poll; `jp_r4` rising.
- D3, D4 and D6 change `rx[3]` and `rx[7]`/`rx[8]`.
- D7 (slider into HOLD and back) does not change `rx[4]` bit 5.
- C0's D7 shows that it did change while healthy.

**Decoder.**
- H2 needs every byte 0 and `rx[0] = 0`, so it does not match.
- H6 needs `rx[3..8]` frozen, so it does not match.
- H7's stages (a)-(e) start at R5, so it does not match.
- The report is H0 with the raw window, which shows the stuck bit
  directly.

**Ruling: DIAGNOSABLE** (S1 allows H0 with raw evidence).

**Recommended.** A named row: "persistent R4 with valid frames;
HOLD bit insensitive to D7 compared with C0". The dossier's Q3 asks
exactly this question.

### TE4. A slow Nop makes the next tick nest inside the softirq; the suspension point is overwritten (straddles a watchdog tick; built on the Nop running before `irq_enter` with IRQs off). AMBIGUOUS

**Shape.**
1. Watchdog tick 1250k lands while the thread is in S14 (P4).
2. The Nop runs before `irq_enter` with IRQs off (F1). It drops G3 and
   sends its own frame. The syscon, still busy with the thread's
   abandoned frame, ACKs the Nop late, or never: the −4 path, at least
   about 50 ms (recon §1.5, UNVERIFIED).
3. Any Nop longer than one tick (≈ 4 ms) means IP7 is pending when
   `__do_softirq` enables interrupts (F2, F4). Tick 1250k+1's handler
   therefore **nests inside tick 1250k's softirq**, on the thread's
   stack, with `current` = the thread.
4. At the outer return the thread is preempted (F3). A woken task with
   strictly better priority is needed. That becomes *more* likely in
   exactly this regime, because the thread's own ≥ 50 ms −4 spins use up
   its sleep average.
5. While the thread is suspended at S14 with G3 low, `pscol`'s `fsync`
   does LED RMWs that write back a non-LED bit (the H10 actor).
6. The thread resumes and returns −4. Input stays dead.

The true story is H4 at P4 plus an H10 write-back during the post-Nop
suspension.

**What the design records.**

| Moment | Record |
|---|---|
| Tick 1250k, inside the Nop | W record: own `ret −4` (or slow ACK), `ack_polls` large, `drain 0`; ext b4 = 1 (the thread is `current`), `epc` = S14, so P4 is correct |
| Tick 1250k, T2a | `lc` = S14, correct |
| Nested tick 1250k+1, T2a (DESIGN:585) | Condition `psc_t_busy_p && current == psc_jp_task` is true, so **`lc` is overwritten from the nested frame**: `lc_epc` inside `__do_softirq`, `lc_r` = softirq registers, `lc_tick` = 1250k+1 |
| Nested tick 1250k+1, T2b | I sample with `epc` in `__do_softirq`, `flags` b1 = 0, b2 = 1; T1 shows `c_pre` > CPT and `long_ticks++` |
| Suspension | `pscol` S records with b4/b5 and `rd_*_or & ~0xC0 ≠ 0`; `led_cmd_or`/`led_cmd_pid` set |
| P08 at exit | `ret −4`, `wn = 1`, `preempt_delta ≥ 1`, `ms_delta > 0`, `led_or & ~0xC0 ≠ 0`, **`lc_epc` in `__do_softirq`**, `lc_flags` b2 = 0 |

**Decoder.**
- H4 at P4 is reported correctly, from the W record.
- Row H10 (DESIGN:1487) requires "suspension step (`lc_epc`) in S13..S20".
  That fails, so the decoder prints "H10 untested in this run" and the
  write-back during the suspension is not attributed.
- The design's exactness argument (DESIGN:212-222, 1481: "the thread can
  only have been switched out at the return from the tick in `lc_tick`")
  is false when that tick was nested. The thread is switched out at the
  return from the **outer** frame, whose EPC the nested tick overwrote.

The same overwrite hits any later W record copied while the thread stays
suspended, which would then report a non-Syscon step.

An analyst can reconstruct the truth by hand from W.`epc` and the nested
I record, so the data is not BLIND. But the specified classifier drops
the H10 half of a combined H4+H10 permanence mechanism, which is the
leading-hypothesis case.

**Ruling: AMBIGUOUS.**

**Fix needed.**
- In T2a and T2b, and in the W extension's `current == thread` branch,
  treat a tick as nested when the interrupted context is not process
  context: at T2, before this handler's `irq_enter`,
  `softirq_count() | hardirq_count()` is non-zero, or `regs->cp0_epc` is
  outside `Syscon_cmd` while `current == thread` and the thread is
  inside a command.
- On a nested tick, do not overwrite `lc`. Increment `lc_nested`, and set
  an I/W flag "nested, EPC not the thread's own".
- The decoder ignores nested EPCs for step resolution. When the only
  `lc` is nested, it falls back to the outer frame, i.e. the W `epc` of
  the same handler.
- Add the sequence to Stage 3: a long Nop, a nested tick, a preemption at
  the outer return, and an LED write-back. Expected report: H4 P4 plus
  H10, not "H10 untested".

### IF4. Errors on about 98 collector ticks use up the segment names; nothing reaches the stick again (stick write fails). BLIND

**Shape.** The Memory Stick reports write errors for a stretch: a contact
disturbance from the grip on the left edge during 30 minutes of L-trigger
clicking, or a weak region of the stick (UNVERIFIED likelihood). Each
failing sector costs 10 × (attempt + 1 ms) non-preemptibly with 20 LED
RMWs (F5), and `fsync` returns EIO (F6).

**What the design specifies.**
- On **any** write or `fsync` error the worker "closes the segment, opens
  the next one (`O_EXCL`)" (DESIGN:1266-1272).
- Every collector tick in a burst fails, so every tick consumes a
  segment name.
- Names are `T<rrr>S<ii>.BIN`, "8.3 names" (DESIGN:1166-1168); the
  supervisor's glob is `T???S??.BIN` (DESIGN:1018); the HUD shows
  `T001S01` (DESIGN:1761).
- `<ii>` is therefore two digits: 99 names per run, shared with worker
  instances and standby promotions.
- Nothing says what happens when they run out. "Every error ... is
  retried on the next tick" (DESIGN:1005-1009). There is no inherited
  zero-padded formatter either (F13).

**Trace.**
1. With `fsync` failing every tick (≈ 0.25-0.35 s per tick with the
   retries), names S02..S99 are gone after about 98 failing ticks: about
   25-35 s of continuous errors. The same happens to sporadic single-tick
   errors spread over the run (about one every 18 s for 30 minutes), plus
   any restarts.
2. In memory each `open(O_CREAT|O_EXCL)` succeeds even while I/O fails,
   because vfat builds the entry in the buffer cache, so each name really
   is consumed.
3. When the stick recovers, the next `open` needs `S100`, which the
   specification has no name for. Depending on the implementation it
   fails (EEXIST on a wrapped `S00`; or a formatting overflow) and is
   retried forever.
4. The worker keeps reading the rings, so `last_reader_tick` advances and
   the supervisor's stall takeover (which needs both ages > 30 s,
   DESIGN:1029-1039) never fires. Even if it did, the standby draws from
   the same name space.
5. `durable_tick` stays frozen. The kernel panel shows a rising `DUR`.
   The rings keep only the last 114.7 s.

**What the stick holds.** Data up to the last successful `fsync` before or
inside the burst, then nothing for the rest of the run. An input death
afterwards is recorded only as panel photographs: the last P08
`ret`/`nwords`/`rx[0..8]`, `jp_loop`/`jp_stage`/`t_busy`/`lc_epc`, and the
last W record (DESIGN:787-792), taken at the RUNBOOK C4/D steps. That is
a once-a-second point sample.
- No raw window before, across and after onset (S2 fails). No W
  extension, I records, S records or POLL history (S4 fails for the
  onset).
- The H4 P-point survives only if a photograph caught the panel within
  5 s of onset.

The design states the opposite: "An error burst shorter than the ring span
(114.7 s for P and POLL) loses nothing" (DESIGN:1277-1280). Its own
Stage 3 test "a 60 s burst ... after the burst the stick holds every
record of the burst interval" (DESIGN 8.5) cannot pass as specified.

A burst short enough not to use up the names is IF1, DIAGNOSABLE. During
any burst the collector's own error retries add up to tens of
milliseconds of non-preemptible time and 20 LED RMWs per failing sector.
That raises the H4 and H10 exposure, but it is recorded (S `flags` b1,
`led_ops`, `wait_pcnt`), so it is not a separate finding.

**Ruling: BLIND** for any death after the name space is used up, under
the design as written. If an implementer happened to continue past
`S99` (the 8.3 base `T001S100` still fits), this would degrade to IF1.
But the design pins two digits and gives no rule, so that is not
something the gate can rely on.

**Fix needed.**
- Rotate at most once per error **burst**, not per failing tick. Keep
  appending to the current segment after a rewind: the records are
  re-sent and deduplicated by (ring, `seq`) anyway, and flushes are
  sector-aligned. Or rotate with exponential backoff.
- Give segments a name space that cannot run out within a run: 8.3 base
  `T<rrr><iiii>`, or a per-run directory `PSCLOG/R<rrr>/S<iiii>.BIN`.
- Define behaviour on exhaustion: reuse the newest segment in append
  mode. Never stop writing.
- Make the supervisor's run-number glob match the new pattern.
- Make Stage 3's 60 s burst inject errors on **every** tick, and add a
  test with about 120 sporadic single-tick errors spread over 30
  simulated minutes.

### OE4. The collector runs with kernel privilege; a stray store corrupts kernel state or GPIO (observer effect). AMBIGUOUS

**Shape.** On this port userland is not de-privileged and user pointers
are never range-checked (F8). `pscol` is new C: three processes, `/proc`
text parsing (`/proc/*/stat` name rescans, `buddyinfo`, `meminfo`,
`kmsg`), pipe protocol parsing, and a 49 KB flush buffer filled by
`read()`s whose lengths the worker computes. Any of these can go wrong:
- An out-of-bounds index.
- A `read()` length larger than the buffer. The kernel copies with no
  check, `USER_DS == KERNEL_DS`.
- A bad pointer.

The resulting store can land in:
1. heap objects next to the process's 128 KB block: `/dev/joypad` queues,
   mousedev clients, input handles, `psposk2`'s memory;
2. kernel BSS, including the design's own heads, busy flags and
   `psc_wd_ctx`;
3. MMIO, e.g. a store to `0xbe240008`/`0xbe24000c` that **bypasses the
   LED hook**.

Any of these can kill input. The 2008 daemons and telem had the same
privilege, so this is not new to the system, but `pscol`'s code is.

**What the design records.**
- (1) Shows up as H7, H9 or N5 symptoms: `jp_stage` fixed, `push_fail`,
  a W `epc` in mousedev, and so on.
- (2) Shows up as IF3-style gaps or `head_regress`, or as misclassified
  origins (W records off `tick ≡ 0 mod 1250`).
- (3) Shows up as a −4 or a foreign frame with `wn = 0`, `ms_delta = 0`
  and no S overlap, which the decoder calls N1 or "none".

Nothing records that `pscol` did it, unless it then crashes (an EVENT from
the promoted standby). The perturbation statement (DESIGN 7.1) and the
risk list (11.1) never mention user-mode privilege. G2 C8 checks only the
bFLT header, FP use, synced writes and visible write errors. So the
analyst would report a confident H7/H9/N5/N1 that the instrumentation
caused. S5 fails for this shape.

**Ruling: AMBIGUOUS.**

**Fix needed.**
1. State in 7.1 and as a new risk that userland runs in kernel mode
   (`process.c:81-83`) with unchecked user copies (`uaccess.h:58`), so
   `pscol` is part of the trusted base.
2. In `pscol`:
   - guard words before and after every static buffer, and at the
     process block's top and bottom;
   - a stack high-water mark (pre-fill the 16 KB stack);
   - every `read()` length computed as `min(cap, remaining buffer)` with
     an assertion;
   - check all of these each tick, with a UHB flag and an EVENT on any
     violation;
   - on violation, stop issuing reads and keep only the panel path.
3. G2 reviews `pscol` with C3/C4 rigour (bounds on every buffer and
   parser).
4. Stage 3 builds `pscol` natively with ASan/UBSan against recorded and
   fuzzed `/proc` text (long `comm` with spaces and parentheses,
   truncated lines, oversized `kmsg`), and against a simulated
   `/proc/psc`.
5. The decoder prints the guard and canary status beside every
   classification, and flags any onset after a violation as
   "instrumentation-suspect".

### OE5. A collector exit closes a mousedev client while the thread is mid-walk (observer effect). DIAGNOSABLE, counter recommended

**Shape.** The design's recovery path ends worker processes on purpose
(the SIGTERM stall takeover, DESIGN:1029-1039) and tolerates their
deaths. Every worker holds a `/dev/input/mice` client (DESIGN 4.3 step 5).
Its exit runs `mousedev_release`, which unlinks and frees the client with
no lock (F9). If the joypad thread is preempted at that moment between
clients in `mousedev_notify_readers` (`mousedev.c:235`, preemptible
outside the per-client spinlock), it resumes on a freed node or
`LIST_POISON1` = `0x00100100`. That is recon/input I9, now triggered by
the instrumentation. On the PSP the access probably bus-errors and oopses
the thread (UNVERIFIED), or it loops.

**What the design records.**
- An EVENT for the worker death or takeover from the new worker; SUP
  status; PROCS with the new pid.
- KMSG carries the oops if the thread faulted.
- P/POLL stop; `jp_stage` 15/16 fixed; W `epc` in `mousedev_*` (N5
  row).
- Or `jp_state` and `jp_pid` show that the task is gone.

The decoder reports N5. The timeline puts the worker exit at onset.

**Ruling: DIAGNOSABLE.** The window is a few hundred instructions per
mouse report, and it is only open while a worker exits.

**Recommended.**
- Count mousedev `open`/`release` with pid and tick in the stats.
- Have the decoder flag any thread-stopped shape within 1 s of a
  collector exit as "instrumentation-suspect".
- On thread exit, `psc_jp_task` becomes a dangling pointer that T2c and
  the stats keep dereferencing. Clear it from the oops/exit path, or
  validate it by pid, so a reused `task_struct` is not counted as the
  thread.

---

## 4. Notes that are not scenarios

- **The out-of-bounds checksum reads instrumented stack.** When
  `rx[1] ≥ 16` the checksum sums `rx_buf[16..rx[1]]`. Those bytes are
  GetCtrl2's saved registers and then the thread's frame (F14). The
  design adds locals and POLL scratch to the thread. That changes which
  out-of-bounds frames pass the checksum by chance (≈ 1/256 per frame;
  the baseline already varies with the previous key word held in that
  frame). The design records `ret` and `rx[0..15]`, so any acceptance is
  visible. Recommend:
  - `psc_sc_exit` recomputes and records the 8-bit out-of-bounds sum and
    the compared byte (the caller frames are still live then);
  - 7.1 lists the effect.
- **RUNBOOK C5 cursor sign.** "Any one of these is enough" includes "your
  clicks ... stop having any effect on the cursor" (RUNBOOK:221-223).
  But `pscol` redraws the whole 480×272 screen 4.35 times a second over
  `pspmd`'s cursor and `psposk2`'s overlay. A cursor that is hard to see
  could lead to a false death call, which spends the run on a control.
  Recommend that C5 require one of the HUD signs (`IN` flat while
  clicking, `DELIV > 2 s`, `DEAD?`) before section D.
- **H10 and N1 prior.** Preemption mid-command needs a strictly better
  priority (`kernel/sched.c:171-172`). It is rare while the thread is
  healthy (mostly asleep) and likelier once it burns ≥ 50 ms per −4 wait.
  The analyst should expect H10/N1 overlaps mainly after the link has
  already degraded.

## 5. UNVERIFIED items this report depends on

1. Whether writing a non-LED bit into GPIO SET/CLEAR has any effect (UL1,
   TE4).
2. Whether the syscon can stay one reply behind, and the 0x33 reply
   format (UL3).
3. The Nop's ACK latency after an abandoned thread frame (whether it
   exceeds one tick), and the −4 duration (TE4).
4. The likelihood of Memory Stick write errors in this setup (IF4). The
   recovered `kmsg.txt` (1,606 bytes) shows none in that session.
5. What a load from `0x00100100` does on the PSP (OE5).
6. How long the used-cluster run after the FSINFO hint is on this stick
   (OE2 residual).
7. The collector's start time after boot (TE1). It is assumed below the
   114.7 s ring span.
