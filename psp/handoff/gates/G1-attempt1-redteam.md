# Gate G1, attempt 1: red team report

Artifact under review: `design/DESIGN.md` and `design/RUNBOOK.md` (Stage 1
synthesis, 2026-09-30).
Reviewer role: G1 red team, attempt 1. Fresh context. I did not write the design.
Date: 2026-09-30.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding), `WORKFLOW.md`, `recon/syscon.md`, `recon/input.md`,
`recon/build.md` (sections 0-3; the rest is packaging and not used here),
`gates/LOG.md`, `design/DESIGN.md`, `design/RUNBOOK.md`.

Source was only read, in `/home/ubuntu/psp/build/linux`. Nothing was written
there or in `/home/ubuntu/psp/work/linux`. Kernel paths below are relative to
`/home/ubuntu/psp/build/linux`. "DESIGN:n" and "RUNBOOK:n" are line numbers
in those two files. Anything I could not settle from source is marked
**UNVERIFIED**.

---

## Verdict: FAIL

Two scenarios are **BLIND** (OE1, IF2). Six are **AMBIGUOUS**, each with a
concrete fix. Three are **DIAGNOSABLE**.

| # | Group | Scenario | Result |
|---|---|---|---|
| UL1 | unlisted-shape (built on H10) | The LED read-modify-write disturbs the syscon through a GPIO bit other than G3 | AMBIGUOUS, and the design's "H10 refuted" rule gives a false answer |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off; the kernel is healthy afterwards | DIAGNOSABLE |
| TE1 | timing-edge | Death at 17-60 s, before or inside the healthy-template window | AMBIGUOUS |
| TE2 | timing-edge (built on the Nop running before `irq_enter` with IRQs off) | Watchdog tick lands while the thread is *suspended* mid-command after the 4-sample I cap is spent | AMBIGUOUS (wrong P-point reported) |
| TE3 | timing-edge | Death at minute 14 during a flush; death at 29:50 | DIAGNOSABLE |
| IF1 | instrumentation-fault | Stick write/`fsync` fails transiently across onset | AMBIGUOUS |
| IF2 | instrumentation-fault | Worker killed at minute 13-14; restart cannot `exec` (no-MMU order-8 allocation) | **BLIND** |
| IF3 | instrumentation-fault | `/proc` reader races every writer; ring head corrupted | DIAGNOSABLE (hardening recommended) |
| OE1 | observer-effect (fault in the collector's own stick I/O) | Memory Stick driver spins forever with preemption disabled inside the collector's `fsync` | **BLIND** |
| OE2 | observer-effect | Collector's first `statfs` triggers a full FAT scan at boot | AMBIGUOUS |
| OE3 | observer-effect | Collector workload, not the instrumentation's instructions, sets the H4 exposure; a no-death run cannot be attributed | AMBIGUOUS |

---

## 1. Source facts the scenarios rest on (re-verified by me)

| # | Fact | Evidence |
|---|---|---|
| F1 | Timer handler order: Count reset, then the watchdog tick (with the Nop), then the UART tick, then `do_IRQ` (which leads to `irq_enter`, `do_timer`, softirqs and wake-ups). | `arch/mips/psp/psp.c:351-354`, `:359`, `:363`, `:367`; recon/syscon.md §2.3 ([OBJ] `jal irq_enter` at `+3b4` after the Nop at `+3a4`) |
| F2 | The Nop runs with IRQs off, before `irq_enter`, on the interrupted task's stack, and only sees `current`'s interrupt frame. | `arch/mips/kernel/genex.S:162-169` (`SAVE_ALL`, `CLI`, `LONG_S sp, TI_REGS($28)`); recon/syscon.md §2.3 |
| F3 | On IRQ return `TI_REGS` is restored **before** kernel preemption, so a preempted thread's `thread_info->regs` no longer points at its preemption frame. | `arch/mips/kernel/entry.S:39` (`LONG_S s0, TI_REGS($28)`), `:72` (`jal preempt_schedule_irq`) |
| F4 | Kernel preemption is skipped whenever `preempt_count != 0`. | `arch/mips/kernel/entry.S:63-64` (`lw t0, TI_PRE_COUNT($28)` / `bnez t0, restore_all`) |
| F5 | Every Memory Stick segment transfer runs inside `__bio_kmap_atomic`, i.e. `pagefault_disable()`, i.e. preempt count raised, synchronously in the submitter's context. | `drivers/block/ms_psp.c:228-236`, `:252-268`; `include/linux/highmem.h:49-56` |
| F6 | The MS driver has unbounded waits: `ms_wait_ready` spins on `MS_RDY` with no timeout; `ms_wait_ced` loops forever while `ms_get_reg_int()` keeps timing out (`result < 0`). The port author records that a similar status wait "forces my psp into a dead loop". | `arch/mips/psp/ipl_sdk/memstk.c:59-65`, `:174-181`, `:167-169` |
| F7 | A failed sector is retried 10 times with `mdelay(1)` each, inside the non-preemptible region, then `-EIO`. | `drivers/block/ms_psp.c:38`, `:306-326`, `:270-276` |
| F8 | A failed page write is not retried by later syncs: the buffer is marked with an I/O error and not uptodate ("lost page write due to I/O error"). | `fs/buffer.c:429-450` |
| F9 | Scheduler is the 2.6.22 O(1) scheduler: a woken task preempts `current` only with strictly better priority. | `kernel/sched.c:171-172` |
| F10 | bFLT exec allocates data+bss+stack as **one** `do_mmap` → `kmalloc(len)` (power-of-two slab size, contiguous pages). MAX_ORDER 11, no MMU. | `fs/binfmt_flat.c:575-596`; `mm/nommu.c:745`; `.config:11` (`# CONFIG_MMU is not set`), `.config:179` (`CONFIG_SLAB=y`); `include/linux/mmzone.h:21` |
| F11 | `statfs` on vfat scans the whole FAT when the free count is unknown (`-1`), which happens when FSINFO's count is `0xFFFFFFFF`, is larger than the cluster count, or FSINFO is unreadable. | `fs/fat/inode.c:540-541`, `:1274`, `:1302-1313`, `:1358-1360` |
| F12 | Mouse mode toggles on **any changed sample** with SELECT set; SELECT is key bit `0x100`, HOLD is `0x2000`; the key word is `~(rx[3] | rx[4]<<8 | ...)`. | `drivers/input/joypad_psp.c:44`, `:49`, `:490-493`, `:512-527`; `syscon.c:363` (recon/syscon.md §1.4) |
| F13 | The LED helpers are plain read-modify-writes of the GPIO set/clear registers and write back **every bit** that was read. | `arch/mips/psp/psp.c:399-407`, `:265-279` |
| F14 | The stick is ≈119 GB (`Adding disk ms0 118999M [0000003f-0e86bfc1]`); RAM is 32 MB, 8128 pages. The 2008 boot log shows no "Did not find valid FSINFO signature" line. | `/home/ubuntu/psp/telem/logs-from-stick/kmsg.txt` |

---

## 2. Scenarios

### UL1. The LED read-modify-write disturbs the syscon through a bit other than G3 (unlisted shape, built on H10)

**Shape.** H10 as written (dossier 9.2) is "RMW clears G3". The general
mechanism is "RMW writes back whatever the read returned" (F13). Suppose a
read of `0xbe24000c` or `0xbe240008` returns a word in which bit 4 (GPIO4, the
syscon ACK line, configured by `GpioSetIntrMode(4,3)`, recon/syscon.md §4.2)
or another non-LED bit is set, and writing that bit to CLEAR/SET disturbs the
ACK latch or line (hardware effect **UNVERIFIED**, as every GPIO semantic is,
recon/syscon.md §4). The thread is suspended in S14 (G3 high, waiting for ACK)
while the collector's `fsync` performs sector writes with LED RMWs. The ACK
edge is lost; the thread times out.

**What the design records.**
- P08 record: `ret = −4`, `ack_polls = 1,000,001`, `nwords = 0`, `rx` all
  `ff`, `ms_delta ≥ 2`, **`ms_b3 = 0`**, `preempt_delta ≥ 1`, `wn = 0` (not a
  Nop tick), `ni ≥ 1` (DESIGN:152-165).
- I record at the suspension tick: EPC in S14, `flags` b2 (if under the cap).
- S record(s): pid of `pscol`, `flags` b0 (write), b4/b5 (P in flight),
  **b2 = b3 = 0**, `led_ops ≥ 2` (DESIGN:287-289).
- Stats: `led_rd_set_b3 = led_rd_clr_b3 = 0` for the whole run;
  `led_last_rd_set/clr` = the raw value of whatever LED op happened *last*
  before each stats read (DESIGN:355-356), almost never the critical one.
- **Nothing records the full read-back value of the RMWs that overlapped the
  command.** Only bit 3 is reduced into counters and flags (DESIGN:163-164,
  287, 451-459).

**What the decoder concludes.** H10 needs `ms_b3 > 0` or S b2/b3
(DESIGN:935) → no. N1 needs `ms_delta = 0` (DESIGN:941) → no. H4 needs a W
record → no. Trigger = none. Then the run-wide test fires: "if
`led_rd_set_b3` and `led_rd_clr_b3` stay 0 for the whole run ... the
mechanism is refuted on this hardware" (DESIGN:935, 1056-1060). **That
conclusion is false here**, and would close the H10 family for future runs.

A second defect in the same test, independent of this shape: G3 is high only
between S13 and S20 of some command (`syscon.c:140`, `:222`;
recon/syscon.md §1.2), so a read can return bit 3 set only if an LED RMW
happens while a thread is suspended in that window. Zero bit-3 counts is the
expected result whether or not the register reads back the latch. The test
has no power unless such an overlap is shown to have occurred.

**Ruling: AMBIGUOUS.** The raw overlap (S record + I step + −4) survives, but
the value written back at the critical RMW is not recorded and the decoder's
H10 rule both misses it and falsely refutes H10.

**Fix needed.** (1) Record raw read-backs: add `led_or` and `led_and` (u32
each) of all values read by LED RMWs in the segment to the S record, and a
`led_or` of the read-backs during the command to the SC record (or stats OR/AND
accumulators per ring); keep per-bit counts of read-back bits in stats.
(2) Decoder H10 rule: "an LED RMW inside the command's window whose written-back
value contains any bit outside `0xC0`", not bit 3 only. (3) The "refuted"
statement is allowed only if at least one LED RMW is proven (I record + S
overlap) to have happened while the thread was suspended at S13..S20 and its
read-back had bit 3 clear; otherwise the report says "H10 untested in this
run".

---

### UL2. One foreign frame toggles mouse mode off; nothing in the kernel stays broken (unlisted shape)

**Shape.** Recon/syscon.md §5.1 shows that an H4 interleave at P3, P4 or P5a
can make the thread accept another command's reply as its own (E7, valid
checksum), and E4 accepts any first-byte-0 frame without checksum (§1.3). If
that one frame has raw `rx[4]` bit 0 = 0 (SELECT after inversion) and bit 5
= 1 (HOLD not set, so R4 does not reject it), `process_input` toggles
`mouseMode` (F12). The next genuine frame has no SELECT, so nothing toggles it
back. Mouse delivery stops for good (`joypad_psp.c:464`); the cursor stops
dead (fits Q1); telem-style "inputs", which count mouse presses only
(dossier 9.6), stop. The same garbage word is pushed to `psposk2`, whose
reaction is unobservable. The runbook forbids SELECT after death
(RUNBOOK:41, DESIGN:1431), so the operator never re-toggles.

**What the design records.** W record at `tick ≡ 0 mod 1250`, `t_busy` b0,
EPC in S12..S14 (step), own `ack_polls`/`drain`/`drain_last`/`rx`. The P08 of
that poll: `ret > 0` with foreign `rx`, or `ret = 0, nwords ≥ 1, rx[0] = 0`.
POLL of that poll: `ri_branch = 5`, `pi_flags` b0 and **b3 (SELECT toggle)
set, b4 (`mouseMode` after) = 0**; `jp_mode_toggles` +1. Every later POLL:
`mouse_flags` b0 = 0. After onset: raw `rx` follows the D-script, `push_ok`,
`jp_wake`, `fop_read_ret` rise; `jp_mouse_calls`, `md_*` and the collector's
mouse packets are flat. HUD line 2 shows `MOUSE OFF` in P5-P7.

The decoder's rows do not name it (H7 (a)-(e) and N6 all require a delivery
stage to stop, DESIGN:932, 946), so it reports H0; but onset candidate O5
(collector's mouse press count stops, DESIGN:1360-1361) fires and the ±30 s
raw dump contains the toggle POLL, the foreign frame and the W record, and the
decoder's own `mouseMode` simulation (DESIGN:1353-1355) shows the flip.

**Ruling: DIAGNOSABLE** (from recorded fields, as H0 with the raw evidence,
which S1 allows).

**Recommended, not blocking.** A decoder rule "mouse-mode toggle whose SELECT
bit came from a foreign or unchecked frame", and a final runbook step after D7:
tap SELECT once and watch 10 s. After death J11's objection (SELECT toggles
mouse mode) is exactly the test.

---

### TE1. Death at 17-60 s, before or inside the healthy-template window (timing edge)

**Shape.** Dossier 9.6 shows deaths before 36 s (sessions s1, s3) and at
140 s. `SELFTEST PASS` normally comes up to 1:30 after launch (RUNBOOK:227).
The decoder learns its healthy template from "the 60 s after SELFTEST PASS
(excluding the reference step)" (DESIGN:1347-1350), and the healthy reference
C0 is at PASS + 30 s (RUNBOOK:110).

**What the design records.** Rings cover it: P/POLL hold ≥114 s from the
thread's start, W from the boot Nop (DESIGN:953-956). If death precedes BTN,
BTN fails three times and the operator goes to D (DESIGN:1148-1151,
RUNBOOK:102-104). C0 never happens. Either no PASS exists (template window
undefined) or the window contains post-onset records.

**Consequences.** O3 ("start of the longest trailing run outside the
template") finds nothing, because the template *is* the dead state. H8 flags
(`gpio_in`, `spi_*`, `drain`, `ack_polls` against the template, DESIGN:933)
come out clean. N2 ("`drain > 0` on every command after onset") cannot be told
from the template. H6's comparison with C0 (DESIGN:931) has no reference.
Unaffected: H1, H2, H3, H5 (absolute values), H4 trigger (W record), H9.

**Ruling: AMBIGUOUS.**

**Fix needed.** Learn the template from records, not from the self-test:
window = [first P record, earliest of O1/O2/O4/O5 − 5 s]; require ≥ 10 s and
≥ 150 polls, otherwise print `NO HEALTHY TEMPLATE`, mark H8 and N2
"unassessable", and fall back to code-derived expectations (`drain = 0`,
`nwords` per command, finite `ack_polls`, raw `gpio_in`/`spi_*` listed). Move
C0 to immediately after BTN so a reference exists as early as possible.

---

### TE2. Watchdog tick lands while the thread is suspended mid-command after the I cap is spent (timing edge; built on the Nop running before `irq_enter` with IRQs off)

**Shape.** The Nop runs inside the timer handler before `irq_enter`, IRQs
off, on the interrupted task's stack (F1, F2). Its W extension can only copy
`current`'s frame (DESIGN:182, 201). When the thread is *suspended*
mid-command, `current` is another task, and the design falls back to "the EPC
of the last I record for that command" (DESIGN:929). I samples are capped at 4
per command (DESIGN:437) and are also taken on ticks where the thread is not
current (DESIGN:237-241).

Concrete sequence for one P08 command:
1. Tick k: thread in S12, sample 0 (`current` = thread). It is preempted at
   IRQ return (a task woken at k has better priority, F9).
2. Ticks k+1..k+3: another task runs; samples 1-3 record *its* EPC.
3. Thread resumes, raises G3, gets its ACK, reads 2 of 4 reply words (S18).
4. Tick k+4 interrupts it at S18 and preempts it again: **suppressed** (cap).
5. Tick k+5 is a watchdog tick. The Nop drops G3 and drains the rest of the
   thread's reply (recon/syscon.md §5.1, P6).
6. The thread resumes: RX empty, `rx` = 2 words + `ff`, **`ret = −2`**.

The same happens without any preemption before step 4 if the ACK wait itself
spans ≥ 4 ticks (a slow ACK; a −4 alone is ≥ 12 ticks, recon/syscon.md §1.5).

**What the design records.** W: `t_busy` b0, `ext_flags` b4 = 0, EPC and GPRs
of the other task, its own `drain > 0`, `drain_last` = the thread's last reply
word, `ack_polls` normal. I: samples 0-3 only, `i_suppressed` +2. P08: `ret −2`,
`nwords = 2`, `wn = 1`, `ni = 4`, `preempt_delta = 2`.

**What the decoder concludes.** Last I record with `current` = thread is
sample 0 at S12 → **P3** (DESIGN:1331); or, with a slow-ACK variant, S14 plus
the Nop's `drain > 0` → **P5a** (DESIGN:929). The truth is **P6**. The
predicted outcome of P3/P5a (E7, E3 or −4, recon/syscon.md §5.1) contradicts
the recorded −2, but the decoder does not cross-check. Dossier 9.6 makes
"which interruption point occurred" load-bearing. Reading the suspended
thread's own `thread_info->regs` would not rescue it: `TI_REGS` is restored
before `preempt_schedule_irq` (F3).

The IRQs-off part is otherwise handled: if the Nop takes the P4 branch-b −4
exit (≥ 50 ms with IRQs off, `syscon.c:151-154`), ticks are lost, `dtick`
undercounts, and the next tick's `c_pre` and `long_ticks` show it
(DESIGN:128-133).

**Ruling: AMBIGUOUS** (a wrong P-point is reported with confidence).

**Fix needed.** In T2 keep hook-owned **overwrite** words, uncapped, for the
in-flight `cmd_id`: whenever `current == psc_jp_task`, store `tick`, `c_pre`,
`epc`, `ra`, Cause.BD, and the loop registers (`t0` = `i`, `a3` = `ptr`, per
`regmap.txt`). The W extension copies them when `ext_flags` b4 = 0 and
`t_busy` b0 = 1; `psc_sc_exit` copies them into the SC record (16 more bytes,
or a companion ring). The decoder takes the thread's step at the Nop from these
words and checks it against the P record's outcome using recon §5.1's outcome
table, reporting "inconsistent" instead of a P-point when they disagree.

---

### TE3. Death at minute 14 during a flush; death at 29:50 (timing edge)

**Trace.** At 14:00 the worker is inside `fsync` for flush n. Onset records
land in the rings, are drained at the next tick and are durable one flush
later. The D-script takes ≈ 95 s and D8 waits for `SYNC AGE < 3 s`
(RUNBOOK:174), so the loss bound (≤ 2 × T_max, DESIGN:785) is already past at
the pull. At minute 14 nothing in the record format saturates: `dtick` u16
(262 s), W ring 1,280 s, streamed rings. The 16-bit links wrap only at
65,536 P records ≈ 30.6 min (a 30:00 control plus 95 s crosses it); the
"nearest" expansion (DESIGN:1280-1282) handles one wrap. Console blanking at
≈ 600 s (`drivers/char/vt.c:174`) feeds N4, which is recorded
(`jp_stage` 7/8, `pi_flags` b2). A death at 29:50 that the operator does not
notice before 30:00 is run through D as a "control" (RUNBOOK:152-153); the
data still shows onset at 29:50 and the D-script after it.

**Ruling: DIAGNOSABLE.**

---

### IF1. Stick write or `fsync` fails transiently across onset (instrumentation fault)

**Trace.** A sector fails 10 times (`mdelay(1)` each, non-preemptible, F7);
`psp_ms_transfer_bio` returns −EIO; the buffer layer drops the page write and
does not retry it (F8); `fsync` returns EIO. The design's worker shows red,
counts the error and "retries on every tick and keeps draining"
(DESIGN:807-809). Its `/proc/psc` offsets have already advanced past the
records in the failed flush, and nothing re-reads them, although they stay in
the rings for ≥ 114 s. On the stick: a CRC-bad or missing chunk, an `fseq` gap,
per-ring `seq` gaps reported as "explicit gaps" (DESIGN:1278-1280).

If the error burst spans onset, the W record of the trigger Nop and the P/POLL
records of the onset window are missing. A common cause is plausible: the MS
LED and the syscon request share one GPIO block (dossier 9.2, H10), and MS
errors themselves lengthen non-preemptible stretches that delay the thread
(F5, F7). Persistent-state rows are still classified from records after the
burst; the trigger (H4 point, H10) and S2's "window across onset" are lost.

**Ruling: AMBIGUOUS.**

**Fix needed.** Make a failed flush non-destructive. Keep `durable_seq[ring]`
= last `seq` of each ring inside a flush whose `write` and `fsync` both
succeeded. On any write or `fsync` error: close the segment, open a new one
(`O_EXCL`), `lseek` each `/proc/psc/*` back to `durable_seq × recsize`, resend,
and write an EVENT chunk "rewind". The decoder's (ring, `seq`) dedupe already
tolerates duplicates. Any error burst shorter than the ring depth then loses
nothing.

---

### IF2. Worker killed at minute 13-14; restart cannot `exec` (instrumentation fault) — BLIND

**Shape.** The design's recovery claim is that a worker death is restarted in
≈ 2 s and "nothing is lost if the gap is under 114 s" (DESIGN:704-709). The
restart is `vfork` + `execve("/usr/bin/pscol")` (DESIGN:698). On this no-MMU
kernel, `exec` of a bFLT allocates data+bss+stack in **one** `kmalloc`
(F10). The worker's buffers are all static (DESIGN:753), including a telem-style
480×272×4 back buffer (522,240 bytes, DESIGN:749-750; `telem.c:299-306`), plus
a 16 KB stack (DESIGN:754): ≈ 550 KB, which the slab rounds to a 1 MB,
order-8, physically contiguous block. By minute 14 the worker has written
≈ 5.6 MB through the page cache (DESIGN:841) into 32 MB of RAM
(F14), leaving clean page-cache pages scattered across free memory. 2.6.22 has
no lumpy reclaim, so an order-8 request can fail with free memory still
plentiful (**UNVERIFIED on hardware**; the allocation path is not).

**Trace.** Worker dies (any cause: an address-error SIGBUS from a parser bug,
or an OOM kill). Supervisor: `execve` fails with ENOMEM
(`binfmt_flat.c:590-596` prints "Unable to allocate RAM for process data" into
the kernel log, which nobody reads now); child exits; supervisor sleeps 2 s;
after 20 failures it stops (DESIGN:700, 717-719). The HUD is frozen (only the
worker draws it). The operator follows C4: wait 60 s, then D, then pull
(RUNBOOK:138-141). The kernel rings keep recording and overwrite after 114 s.
On the stick: data up to the last sync before the kill, no EVENT for the
failed restarts (the supervisor never writes the stick, DESIGN:701,
1434). An input death after the kill is **not on the stick at all**, and the
operator may not even know whether input died.

A related gap: after any successful restart the new worker reads every ring
from offset 0 (≈ 614 KB: P 256 KB, POLL 64 KB, W 98 KB, I 128 KB, S 64 KB,
M 4 KB) through "a static 8 KB buffer" and "one `write()`" per flush
(DESIGN:726, 745-747). Backlog handling is unspecified; an implementation that
does it in one flush produces a multi-second burst of non-preemptible sector
writes exactly at the restart.

**Ruling: BLIND** for any death after the collector is permanently lost; S2,
S3 and S4 fail.

**Fix needed.** (1) The worker never exits on runtime errors. (2) Recovery
must not need a new large allocation: pre-spawn a standby worker at boot
(memory reserved while unfragmented) that takes over through a pipe when the
primary dies. (3) Before any re-exec the supervisor writes `1` to
`/proc/sys/vm/drop_caches` (`fs/drop_caches.c` is present), and PROCS logs
`/proc/buddyinfo` (`fs/proc/proc_misc.c:707`) and MemFree. (4) Specify
backlog draining: bounded chunks (≤ 64 KB), a per-tick byte cap, several
ticks if needed, never one huge flush. (5) The kernel-side stall panel of OE1
also covers a dead collector.

---

### IF3. `/proc` reader races every writer; ring head corrupted (instrumentation fault)

**Trace.** Writers: the thread (P, POLL), the timer IRQ (W, I), the MS path
under `s_psp_ms_rw_sem` with preemption off (S), other threads (M). The reader
is the preemptible collector. The seq-invalidate/publish protocol (DESIGN:598-604)
and the before/after `seq` check (DESIGN:636-644) reject every torn copy on a
uniprocessor, including an IRQ writer landing mid-copy. A slot can be torn only
if its ring laps during the copy, which needs ≥ 80 s (I ring, H1 worst case)
or ≥ 114 s (P); the loss is then counted as `lost` and shown on the HUD
(`LOST`). Multi-word stats are read without a retry: `total_counts` low/high
(words 10-11) can tear on a carry (once per ≈ 19.4 s of counts), producing a
one-sample jump that the decoder's monotonicity check reports as "kernel restart
or corruption" (DESIGN:1287-1288). The `t_busy/t_cmd/t_entry_*` group can tear
while the thread runs, but the classification rules that use it (H9, N9) read
a stuck, unchanging state.

Ring head corruption: heads are single-writer BSS words. The known wild-write
paths write freed slab memory, not BSS (H9 Q2, recon/input.md §1.6; mousedev
I9, §3.2). If a head were corrupted anyway: a forward jump makes the reader skip
to `head − N` (visible gap); a backward jump makes `s ≥ head` true, so `read()`
returns 0 for that ring until the head passes the old position, with no EVENT;
STATS heads (words 14-19) and the decoder's monotonicity check expose it.

**Ruling: DIAGNOSABLE.**

**Recommended hardening.** Read 64-bit and grouped stats with a high-low-high
(or `seq`-bracketed) retry; the reader resynchronises and emits an EVENT when
`head` < the requested `seq`.

---

### OE1. Memory Stick driver spins forever with preemption disabled inside the collector's `fsync` (observer effect: the fault is in the collector's own stick I/O) — BLIND

**Shape.** Every sector the collector writes goes through the MS driver
synchronously in the collector's context, inside `__bio_kmap_atomic`
(preempt count raised, F5). `ms_wait_ready` has no timeout, and `ms_wait_ced`
loops forever when the controller keeps reporting timeouts (F6). One
controller hiccup that fails to raise `MS_RDY`, or a persistent `MS_TIME_OUT`,
leaves the collector spinning with preemption disabled. Interrupts stay on:
the timer, the Nop and the softirqs run; wake-ups set `need_resched`; but no
task switch ever happens (F4). The joypad thread never runs again, so input
dies. `psposk2`, `pspmd`, the supervisor and the worker all stop. The design
roughly doubles telem's LED/sector rate (≈ 18 sector writes/s against ≈ 8.7,
DESIGN:849-859) and writes 6-12 MB per run, which telem never did, so this
exposure is the instrumentation's own. It also ends the observed input death,
if one had just begun, before its data is synced.

**What the design records.**
- In RAM only: W records every 5 s whose extension holds the spinning task's
  EPC (inside `ms_wait_ready` or `ms_wait_ced`) and pid. That would be decisive,
  but nothing drains it.
- P and POLL stop. No I records (no command in flight). **No S record for the
  segment in progress**, because the S record is written only "before `up()`"
  (DESIGN:460-461).
- On the stick: complete chunks up to the last successful `fsync`, then
  possibly a partial chunk (CRC-rejected). The last UHB shows normal timings.
- On screen: the HUD freezes, including `SYNC AGE`, which therefore never
  shows a rising value (DESIGN:791-793 relies on the worker to draw it).
- Operator: C4 (freeze) → wait 60 s → photograph → D → pull (RUNBOOK:138-141).
  The photographs show a frozen HUD.

The analyst sees a healthy stream that simply ends. It cannot be told apart
from a thread wedged with interrupts off, a kernel deadlock, or a hung
collector followed by an unrelated input death. Which came first, the freeze or
the input death, is unknowable.

**Ruling: BLIND.** The run is also spent: RUNBOOK C4 ends it with a pull even
if the freeze happened long before any input death.

**Fix needed.** A kernel-side stall panel that does not depend on userland:
on each WT tick (already IRQs-off, every 5 s), if `psp_local_tick −
last_reader_tick > 750` (3 s), paint a compact hex block directly into the
framebuffer (memory stores only), or printk one line to the framebuffer console.
Contents: latest W extension (pid, EPC, RA, Status, Cause, `preempt_count` of
`current`), `jp_loop`, `jp_stage`, `t_busy`, `t_entry_tick`, the latest P08
`ret`/`nwords`/`rx[0..8]`, P/W heads, `last_reader_tick`, and an **MS
in-progress marker** (sector, pid, `tick_on`) published at segment entry. Zero
cost while the collector is alive (one compare per 5 s). RUNBOOK C4 must
photograph the panel at +10 s and +60 s, and must say whether a freeze with
input still alive counts as the run. Optionally, bound `ms_wait_ready` and
`ms_wait_ced` in the diagnostic kernel. That changes non-syscon code and needs
its own perturbation statement.

---

### OE2. The collector's first `statfs` triggers a full FAT scan at boot (observer effect)

**Shape.** Before its first write the worker `statfs`es `/ms0` and requires
≥ 128 MB free (DESIGN:762-765); the STICK check keeps running after PASS
(DESIGN:1132, 1136). vfat's `statfs` counts free clusters by reading the
**entire FAT** when the free count is unknown (F11). On a ≈ 119 GB stick
(F14) with 32 KB clusters that is ≈ 3.7 M entries, ≈ 15 MB, ≈ 29,000 sector
reads (cluster size **UNVERIFIED**), each with two LED RMWs and each a
non-preemptible segment. telem never called `statfs`, so this load was never
present in the 9.6 sessions (contrary to the load-parity claim of DESIGN:1023-1035).
Whether the count is unknown on this stick is **UNVERIFIED**: the 2008 log shows
the FSINFO signature was accepted (F14), but not whether the count field is
`0xFFFFFFFF` or out of range (`fs/fat/inode.c:1312-1313`, `:1358-1360`).

**What the design records.** During the scan the worker is inside `statfs`
and does not drain. The S ring (2,048 entries, DESIGN:563) is written at the
scan's segment rate and wraps in seconds; P/POLL (114 s) and W survive. If an
H10 or N1 death occurs during the scan: the P record keeps `ms_delta`, `ms_b3`
and `preempt_delta`, and the I record keeps the step, but the S records that
give the pid, timing and overlap of the disturbing segments are overwritten.
H10 against N1 against N8 (DESIGN:935, 941, 948) cannot be separated, and the
analyst learns only from `ms_seg_rd` that the collector itself was the actor.
If STICK does not pass within 120 s the run aborts, which costs nothing, but
the operator may also simply see a slow self-test.

**Ruling: AMBIGUOUS.**

**Fix needed.** No FAT-scanning `statfs` on the device: check free space on the
host in RUNBOOK A (and have the package step or the Mac write a valid FSINFO
free count), and on the device check only the mount type via `/proc/mounts`. If
a device-side check is kept, run it before any ring matters and report its
duration. Add per-command S attribution that cannot be overwritten (pid of the
last LED op during the command in the SC record), or size the S ring for
FAT-scan rates, and have the decoder mark "H10/N1/N8 separation unavailable"
whenever the S ring shows `lost > 0` near onset.

---

### OE3. Collector workload, not the instrumentation's instructions, sets the H4 exposure; a no-death run cannot be attributed (observer effect)

**Shape.** The Nop of tick k runs before that tick's softirqs (F1), so it can
never hit a command the thread started after being woken at tick k. It can hit
only a command that started earlier and is still in flight at the tick edge.
Since a command normally takes well under one tick (the HUD shows a median of
≈ 210 µs, DESIGN:1120), an interleave needs the thread's start to be pushed
towards the next tick edge. What pushes it is whoever holds the CPU when the
thread is woken: non-preemptible MS segments (F5), and any equal-priority task
running its tick body, which the O(1) scheduler does not preempt on a tie
(F9). `pscol`'s tick body is not telem's: six ring reads, stats, kmsg, PROCS
every 8th tick, ≈ 1.5 KB and 2× the LED operations per `fsync`, the same 522 KB
blit (DESIGN:726-751, 849-859). The design's perturbation statement bounds only
its own instructions (≈ 0.02 %, DESIGN:998-1001) and asserts that the MS load
"raises the rate" (DESIGN:1051-1055). The direction actually depends on phase,
and it is not bounded.

**What the design records.** Per poll `c_start` (the thread's start phase),
`period`, `preempt_delta`; S records with pid; PROCS CPU times every 2 s; every W
with `t_busy` and step. So the **exposure in this run** is measurable: how many
Nops found the thread in flight, and at which step. What is not recorded is
**who delayed the thread** when no MS segment overlapped: equal-priority
collector CPU work leaves no preemption and no S record. And there is no telem
baseline. If no death occurs in 30 minutes (R1), the report cannot say whether
`pscol` prevented it (S5).

**Ruling: AMBIGUOUS.**

**Fix needed.** (1) In the tick hook: whenever `psc_jp_task` is TASK_RUNNING
but not `current`, count the tick in a small stats histogram by class of
`current` (`pscol` / `pdflush` / `psposk2` / `pspmd` / other) and by
`preempt_count(current) > 0` (inside MS I/O). Add a POLL byte "class that held
the CPU at the tick before the loop started". (2) Pre-register the no-death
inference in the decoder: per P-point, the count of Nops that landed on an
in-flight thread command; with at least N benign P4/P5a hits, "H4 at P4/P5a is
not sufficient on this kernel"; below N, "inconclusive, exposure X, Y % of
thread delay attributable to `pscol`".

---

## 3. Notes that are not scenarios

- **H10 and N1 need the thread to be preempted mid-command.** Under the O(1)
  scheduler that requires a task with *strictly* better dynamic priority to be
  woken at that tick (F9). The joypad thread sleeps ~99 % of the time and holds
  close to the maximum sleep bonus, so this is rarer than the design's rows
  imply. That does not break the design; it lowers the prior on H10 and N1 and
  makes TE2's preempted sequence the uncommon case. The common H4 case (thread
  running when the Nop lands) is fully captured by the W extension.
- **The RUNBOOK C4 path spends the run on any collector freeze**, whether or not
  input died (RUNBOOK:138-141). Together with OE1 and IF2 this is the main
  exposure of the single run to the instrumentation's own failure.
- **The design should state what the operator does when `SUPERV DEAD` or `RST`
  stops advancing.** C3 says "note and keep going" (RUNBOOK:133-134), and
  nothing then restores the collector.

## 4. UNVERIFIED items this report depends on

1. Whether writing a non-LED bit (for example bit 4) into GPIO SET/CLEAR has
   any hardware effect (UL1).
2. Whether the syscon's Nop reply, or any foreign frame, has `rx[4]` bit 0 = 0
   and bit 5 = 1 (UL2).
3. Whether the MS controller can fail to raise `MS_RDY` or keep reporting
   timeouts in normal use (OE1). The port author's comment at `memstk.c:167`
   shows a similar status wait did hang on this hardware.
4. Whether an order-8 allocation fails after ≈ 5-6 MB of page-cache churn in
   32 MB (IF2).
5. Whether this stick's FSINFO free count is valid, and its cluster size (OE2).
6. The real ACK latency distribution, which decides how often the I cap is
   exceeded (TE2).
