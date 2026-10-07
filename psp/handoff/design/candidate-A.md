# Candidate A: minimal-perturbation instrumentation design

Stage 1 design draft. Role: Designer (candidate A). Written 2026-09-30.
Assigned angle: **minimal perturbation**. The bug may be timing-sensitive
(H4, H10), so every instruction added to the syscon path must be justified.
Prefer the fewest capture points and the smallest records, and use the
coverage matrix to show that this is still enough.

The runbook is also written separately, as
[candidate-A-RUNBOOK.md](candidate-A-RUNBOOK.md). It is named for the
candidate so that it cannot overwrite another designer's `RUNBOOK.md`.

Conventions:

- Kernel paths are relative to `/home/ubuntu/psp/build/linux`. That tree is
  read-only; I verified against it and wrote nothing there.
- `[SRC]` means read in the source, with file:line given.
- `[OBJ]` means read in the built `syscon.o`. I disassembled it read-only in
  the `psp-build:bullseye` container. The output is in my scratchpad, not in
  the handoff tree.
- `[DOS]` means taken from DOSSIER.md, whose section 9 overrides earlier
  sections.
- `UNVERIFIED` means a guess or a hardware fact the source cannot settle.
  Every guess is also listed in section 11.
- **Dossier 9.6 and 9.7 were added while I was writing.** They report three
  bracketed input deaths, each on a 5 s watchdog boundary, and recover the
  baseline boot folder. This design takes both into account. In particular,
  9.6 asks the design to resolve which interruption point occurred. Section
  2.3 does this without adding any instruction to the thread's transaction.

---

## 0. Design in one page

1. **One ring record per syscon command, written after the transaction has
   ended.** Nothing is recorded between the transaction's first register
   access (S5, `syscon.c:102`) and its last one (S20, `syscon.c:222`). Inside
   that window the only change is that five values the code already reads
   and discards (currently written to the throwaway `dmy`, or held in `spin`)
   are stored to separate stack variables instead. The instruction count is
   the same: **zero instructions are added in the window.** This is an
   acceptance criterion for G2, checked with objdump (section 7.2).
2. **Three single-writer rings, so no locks, no interrupt masking and no
   atomic operations are needed.**
   - W holds commands issued by the watchdog, with interrupts off. W records
     are 320 bytes.
   - P holds commands issued by the poll thread. P records are 64 bytes.
   - M holds commands from any other thread. M records are 64 bytes.

   Only one writer can ever be active on a given ring, so a record cannot be
   torn by a second writer. A per-record sequence number is written last, so
   a reader never accepts a record that was half-written.
3. **The watchdog path records the interrupted context, which gives phase
   resolution for H4.** When the timer interrupt's watchdog command runs,
   `current_thread_info()->regs` points at the interrupted context's saved
   registers (`genex.S:166-167`, `entry.S:39`). The W record copies the
   interrupted PC (EPC), Cause, Status, all 32 general registers and 88
   bytes of the interrupted stack. If the poll thread was in the middle of
   `Syscon_cmd`, the EPC gives the exact instruction, and so the exact step
   S1 to S23 and the interruption point P0 to P7 in recon/syscon.md
   section 5. The stack copy shows the thread's volatile locals, such as the
   ACK-wait counter. **All of this cost falls on the watchdog command, which
   the thread cannot observe. The thread pays nothing.**
4. **Every record is streamed to the Memory Stick. No trigger, freeze or
   onset detection is used.** A new userland collector, `pscol`, is derived
   from `telem.c` and started from `rc.sysinit`. It drains the rings
   continuously and appends every record, 1 Hz summaries and
   process-liveness data to `/ms0/PSCLOG/`. It issues one sector-aligned
   `write` plus `fsync` per second. Worst-case battery-pull loss is about
   1.5 s. The kernel rings hold at least 57 s of backlog, so a collector
   restart or a slow stick loses nothing.
5. **The design adds no register reads.** Every hardware value recorded is
   one the unmodified code already reads (dossier 9.1: no read is proven
   safe).
6. **Timestamps** are (jiffies, CP0 Count) at command entry and command
   end. A torn-read flag and the W-record flag let the decoder correct both
   Count/jiffies caveats. The watchdog boundaries are in the data itself:
   every W record *is* a boundary.

---

## 1. Record format

All multi-byte fields are little-endian (`.config:64`
`CONFIG_CPU_LITTLE_ENDIAN=y`). Structs are naturally aligned and declared
`__attribute__((packed, aligned(4)))`, with a compile-time size assertion.

### 1.1 Common record (P and M rings: 64 bytes; the first 64 bytes of every W record)

| Off | Type | Field | Source | Why it is needed (hypotheses) |
|---|---|---|---|---|
| 0 | u32 | `seq` | Per-ring sequence number, starting at 0. Set to `0xFFFFFFFF` while the record is being written, and to its real value last. | Loss and gap detection; reader validation (D9, C4) |
| 4 | u32 | `j_end` | `jiffies`, read twice at record time (the second read is stored) | Time (D16) |
| 8 | u32 | `c_end` | `read_c0_count()` at record time (`mipsregs.h:789`) | Sub-jiffy order; command duration (H1, H4) |
| 12 | u32 | `c_start` | `read_c0_count()` at `Syscon_cmd` entry, before `retry:` (`syscon.c:75`) | Duration; the command's start phase within the tick (H4 hazard) |
| 16 | u16 | `dj` | `j_end − j_start`, saturating at 0xFFFF | Duration across ticks |
| 18 | u8 | `cmd` | `tx_buf[0]` | D3; context of the caller |
| 19 | u8 | `txlen` | `tx_buf[1]` | D3; frame shape |
| 20 | s16 | `ret` | `Syscon_cmd`'s return value. Possible values: −5, −4, −3, −2, 0..255 (recon §1.3) | D3, D14 (−2, −3, −4 and −5 stay distinct) |
| 22 | u8 | `nwords` | 16-bit words actually received in the final attempt, 0..8. Computed as `(ptr − rx_buf)/2` after S20. Set to 0 on the −3 and −4 exits. | D3; H3 (0 words) versus H2 (words = 00) |
| 23 | u8 | `retries` | `retry_cnt` (`syscon.c:72,253`): the number of 0x80/0x81 resends | H5 |
| 24 | u32 | `ack_polls` | `SPIN_MAX − spin_ack` (mod 2³²). This is the number of GPIO4 polls that saw "no ACK" in the final attempt. A value of 0 means the ACK latch was already set before the request. 1,000,001 means the −4 timeout. | H1 (timeout), H4 (P5a: stale latch), H8 (latch stuck); ACK latency |
| 28 | u16 | `drain` | `SPIN_MAX − spin` after the RX pre-drain (S8, `syscon.c:110-116`), saturating at 0xFFFF. Also 0xFFFF on −3. | Stale RX words left by an earlier command (H4 P6, H5 shift, TXF/RXF carry-over) |
| 30 | u16 | `drain_last` | The last word popped by the drain loop (`syscon.c:114`). Meaningful only if `drain > 0`. | Which reply was stale (for example the watchdog's) |
| 32 | u16 | `gpio_in` | Low 16 bits of the `0xbe240004` value read at S5 (`syscon.c:102`), final attempt | G3/G4 levels at the start of the transaction (H8, H10: G3 high at start) |
| 34 | u16 | `spi_st9` | Low 16 bits of `0xbe58000c` read at S9 (`syscon.c:119`). Invalid if `ret == −3`. | SPI status after the drain (H8) |
| 36 | u16 | `spi_sttx` | Low 16 bits of `0xbe58000c` read at S11, before the last TX push (`syscon.c:130`). Invalid if `ret == −3`. | TX-side status (H8, TXF residue) |
| 38 | u8 | `ctx` | Bit 0 WD: the watchdog flag was set. Bit 1 IRQOFF: `irqs_disabled()`. Bit 2 INIRQ: `in_interrupt() != 0`. Bit 3 JPT: `current == psc_jp_task`. Bit 4 TORN: jiffies changed between the two reads at record time. Bit 5 TIMER: called from the timer interrupt. Bits 6-7: ring (0 = P, 1 = W, 2 = M). | D8: context identified independently of `in_interrupt()` (dossier 9.1) |
| 39 | u8 | `xmeta` | P and M: `wn`, the number of W records committed between entry and record time, saturating at 255. W: `t_busy`, the kind of thread command in flight (0 none, 1 poll thread, 2 other thread). | D8 from both sides; H4 |
| 40 | u16 | `xseq` | P and M: W head at record time, low 16 bits, so the nested W records are `xseq−wn .. xseq−1`. W: P head at record time, low 16 bits, which is the seq the in-flight P command will receive. | Cross-ring linkage (H4) |
| 42 | u16 | `loop` | Poll-thread loop counter, low 16 bits | Pairs the 0x33 and 0x08 records of one poll; thread heartbeat (H7, H9) |
| 44 | u8 | `stage` | Poll-thread stage code (section 2.5) | H7, H9: where the thread is |
| 45 | u8 | `ms_delta` | Change in `psc.led_calls` between entry and record, saturating at 255 | H10: Memory Stick LED RMW during this command |
| 46 | u8 | `preempt_delta` | Change in `current->nivcsw` between entry and record, saturating (`sched.h:907`; incremented on preemption, `kernel/sched.c:3626-3628`). Always 0 for W. | Thread suspended mid-command (H10, new shape H11) |
| 47 | u8 | `reserved` | 0 | — |
| 48 | u8[16] | `rx` | The whole `rx_buf[0..15]` after the final attempt. It includes the 0xff prefill where nothing was received. | D3: raw frame for every hypothesis |

The fields at offsets 24 to 36 cost nothing inside the transaction window
(section 7.2). They are the values the existing code already reads, stored
somewhere they are not immediately overwritten.

### 1.2 W record extension (bytes 64..319; W records are 320 bytes)

This part is filled only in the watchdog path, with interrupts off. It is
filled after the watchdog's own transaction has finished.

| Off | Type | Field | Source |
|---|---|---|---|
| 64 | u32 | `epc` | `regs->cp0_epc` of the interrupted context (`ptrace.h:48`). `regs` is `current_thread_info()->regs` (`thread_info.h:37`), which `handle_int` sets (`genex.S:166-167`). It is 0 if `regs` is invalid. |
| 68 | u32 | `cause` | `regs->cp0_cause`. The BD bit says whether EPC points at a branch. |
| 72 | u32 | `status` | `regs->cp0_status`. CU0 set means the interrupted context was in kernel mode (`entry.S:45-48`; `ptrace.h:89` defines `user_mode()` as CU0 clear on PSP). |
| 76 | u32 | `pid` | `current->pid`, the interrupted task |
| 80 | u32 | `p_head` | Full P head |
| 84 | u32 | `jp_loop` | Full poll-thread loop counter |
| 88 | u32 | `t_entry_j` | `jiffies` at the entry of the in-flight thread command (valid if `t_busy != 0`) |
| 92 | u32 | `t_entry_c` | CP0 Count at that entry |
| 96 | u8 | `t_busy` | 0, 1 or 2, as in `xmeta` |
| 97 | u8 | `jp_stage` | Poll-thread stage |
| 98 | u8 | `ext_flags` | Bit 0: `regs` valid. Bit 1: stack copy valid. Bit 2: interrupted in kernel mode. Bit 3: EPC inside `Syscon_cmd`. |
| 99 | u8 | reserved | 0 |
| 100 | u32 | `m_head` | Full M head |
| 104 | u32[32] | `gpr` | `regs->regs[0..31]` (`ptrace.h:37`) |
| 232 | u32[22] | `stk` | 88 bytes at `regs->regs[29]` (the interrupted `sp`). Copied only if that range lies inside the current task's stack (`task_thread_info(current)` to `+THREAD_SIZE`). Otherwise zero. |

**Why this is safe.** `regs` is dereferenced only if it points inside the
current task's stack block. The stack copy has the same bound check. At the
boot-time command (`psp.c:557`) no interrupt frame exists, so the TIMER flag
is 0 and the extension is zeroed without dereferencing anything. All reads
are of RAM. No MMIO is touched.

**Why it resolves 9.6.** The `Syscon_cmd` frame is 48 bytes in the current
build ([OBJ] `addiu sp,sp,-48` at `Syscon_cmd+0x0`). `dmy` is at `sp+0` and
`spin` at `sp+4`. Every register base address is held in `s0..s8`, `t2`,
`t4`, `t7` or `a2` ([OBJ] `+0x38..+0x70`). So the register dump and the
stack copy contain the interrupted thread's complete local state:

- `i` and `ptr` locate the thread inside the TX or RX loops, so P2 gives k
  and P6 gives j.
- `spin` and `spin_ack` give how long the thread had been draining or
  waiting for ACK.
- `result` and `cnt` are there too.

Stage 2 must regenerate the offset map from the instrumented build. That
build's frame is expected to be about 64 bytes, which fits in the 88 bytes
copied.

### 1.3 Sizes

- P and M records: 64 bytes, one D-cache line (Allegrex line size is
  UNVERIFIED).
- W record: 320 bytes.

---

## 2. Capture points

Only four sites write on hot paths. One more site fills values when the
collector reads `/proc`.

### 2.1 CP-A: `Syscon_cmd` (`syscon.c:61-258`). Every caller, every context

| Sub-point | Location | What it adds | Context |
|---|---|---|---|
| A1 entry | After the declarations, before `retry:` (`syscon.c:72-75`) | Reads `psc_wd_active`, CP0 Count, `jiffies`, `psc.w_head`, `psc.led_calls` and `current->nivcsw` into a stack scratch struct. If not WD, writes `psc_t_busy` (1 if `current == psc_jp_task`, else 2), `psc_t_entry_j` and `psc_t_entry_c`. Zeroes `gin`, `st9`, `sttx`, `dlast`. | Caller's context |
| A2 per attempt | At `retry:` (`syscon.c:75`), before S1 (`:77`) | `spin = SPIN_MAX; spin_ack = SPIN_MAX;`. This is outside the window: S1 to S4 touch memory only. | same |
| A3 in window | `syscon.c:102` (`dmy=` becomes `gin=`), `:114` (`dmy=` becomes `dlast=`), `:119` (`dmy=` becomes `st9=`), `:130` (`dmy=` becomes `sttx=`), `:151-154` (`spin` becomes `spin_ack`) | **Nothing added.** The same volatile load and store are kept; only the target stack slot changes. The new variables are `vu16` like `dmy`, and `spin_ack` is `vu32` like `spin`. | same |
| A4 exit | The three exits `:113` (−3), `:154` (−4, after its two teardown writes) and `:257` become `result = X; goto out;`. At `out:` the code computes `nwords` and calls `psc_record(tx_buf, rx_buf, result, &scratch, nwords, retry_cnt)`. | After the last register access of the transaction, or after the −4 teardown writes | same |

`psc_record()` is a new, non-inline function in a new file
(`arch/mips/psp/psc.c`). What it does:

1. Clear `psc_t_busy` if not WD.
2. Choose the ring: WD → W; else `current == psc_jp_task` → P; else → M.
3. Take the time stamp: `j1 = jiffies; c = read_c0_count(); j2 = jiffies`.
4. Invalidate the slot, fill it, bump that ring's outcome histogram, publish
   `seq`, then increment the head.
5. If TIMER, fill the W extension.
6. Store `psc.rec_cost_last = read_c0_count() − c`, and update the
   per-ring maximum.

### 2.2 CP-B: watchdog (`psp.c:370-397`)

- In `psp_pacify_watchdog`, after the `s_psp_shutdown` check (`psp.c:385-389`):
  `psc_wd_active = 1; psc.wd_calls++; psc.wd_last_j = jiffies;` then
  `pspSysconNop();` (`:392`) then `psc_wd_active = 0;`.
- In `psp_watchdog_tick`, around the call at `psp.c:379`:
  `psc_in_timer = 1; psp_pacify_watchdog(); psc_in_timer = 0;`.

`psp_pacify_watchdog` has exactly two callers: `psp.c:379` (the timer
interrupt, interrupts off, before `irq_enter`: `genex.S:163` `CLI`, recon
§2.3 [OBJ]) and `psp.c:557` (`prom_init`, interrupts off). I confirmed this
by grep over the whole tree: `psp.c:97` (prototype), `:379`, `:383`
(definition) and `:557`. **So the WD flag is set only while interrupts are
off**, and W has exactly one writer at any instant.

### 2.3 CP-B': the interrupted context (inside `psc_record`, W only, TIMER only)

This copies `regs` and the stack as described in 1.2. It gives
instruction-exact resolution of where the watchdog command landed, in the
thread or anywhere else, including inside the Memory Stick LED RMW
(section 7.5).

### 2.4 CP-C: `psp_gpio_set` and `psp_gpio_clear` (`psp.c:399-407`)

`PSP_GPIO_SET |= mask_;` becomes:

```
v = PSP_GPIO_SET;
PSP_GPIO_SET = v | mask_;
barrier();
psc_note_led(0, v);
```

The clear side is the same. It is the same single volatile load and the
same single volatile store, in the same order, with nothing added between
them. `psc_note_led` then increments `led_calls`, increments
`led_calls_t_busy` if `psc_t_busy`, increments `led_rd_{set,clr}_b3` if
`v & 0x08`, and stores `led_last_rd_{set,clr} = v`.

This measures, for free, whether a read of the set or clear register
returns bit 3 (G3). That is exactly the hardware unknown that H10 depends on
(recon §2.2).

### 2.5 CP-D: poll thread and driver counters (`joypad_psp.c`). None of these are inside `Syscon_cmd`.

| Location | Adds |
|---|---|
| `:453` thread start | `psc_jp_task = current; psc.jp_pid = current->pid;` |
| `:458-460` loop top | `psc.jp_loop++; psc.jp_stage = ST_READ (1)` |
| `:462` before process | `stage = ST_PROC (2)` |
| `:464-465` before mouse | `stage = ST_MOUSE (7)` |
| `:468` before `msleep` | `stage = ST_SLEEP (8)` |
| `:488` R3, `:493` R4, `:495` R5 | `jp_r3++`, `jp_r4++`, `jp_r5++` |
| `:498` process entry | `jp_proc_calls++`. At `:513` dedupe: `jp_proc_dedupe++`. |
| `:518` before `psp_lcd_on` | `stage = ST_LCD (3)` |
| `:527` | `psc.jp_keys = keys_` |
| `:530` before `down_interruptible` | `stage = ST_LISTSEM (4)`. On failure: `jp_listsem_fail++`. |
| `:534` before each push | `stage = ST_PUSH (5)` |
| `:536-538` after `up` | `stage = ST_WAKE (6)` |
| `:392` / `:398` / `:410` in `queue_push` | `jp_push_semfail++` / `jp_push_full++` / `jp_push_ok++` |
| `:593` mouse entry; `:658` before `input_sync` | `jp_mouse_calls++`; `jp_mouse_reports++` |
| `:313` open; `:319` release | `jp_opens++`; `jp_releases++` |
| `:346` `queue_free` entry and each exit; `:350` | `jp_free_inflight++` / `--`; `jp_free_semfail++` |

### 2.6 CP-E: values filled by the `/proc` reader

These cost nothing on any hot path. They are evaluated in the collector's
`read()` of `/proc/pspsc/stats`:

- `now_jiffies` and `now_count`.
- The three heads.
- The poll thread's `task->state` low byte, and `TIF_SIGPENDING` via
  `test_tsk_thread_flag`.
- `get_wchan(task)` (`arch/mips/kernel/process.c:441`).
- `nvcsw` and `nivcsw`.
- `console_blanked`.
- The kernel addresses of `Syscon_cmd`, `psc_record`, `_pspSysconGetCtrl2`
  and `pspSyscon_tx_dword`, so the decoder can check it has the right
  `System.map`.

---

## 3. History mechanism

### 3.1 Rings (static BSS; usable from `prom_init` because `head.S:182-184` clears `.bss` before `start_kernel`)

| Ring | Entries | Record | Bytes | Maximum fill rate | Time until the oldest record is overwritten |
|---|---|---|---|---|---|
| P | 2048 | 64 | 131,072 | 35.7 records/s (17.86 polls/s × 2, dossier 9.1 on 4.3) | **≥ 57 s** |
| W | 128 | 320 | 40,960 | 0.2 records/s (one per 1250 ticks) | about 640 s (10.7 min) |
| M | 64 | 64 | 4,096 | Fill-once. When full, further records are counted in `m_dropped` and not stored. | never overwrites |
| stats + globals | — | — | about 512 | — | — |

Total kernel BSS is about 176.6 KB. That is 0.85 % of the 20,808 KB
`MemFree` recorded by telem on the 2008 image
(`telem-v1.log`, session 10). The figure for this tree's kernel is
UNVERIFIED.

### 3.2 Full resolution, summaries, triggers

- **Everything is kept at full resolution on the stick**, for the whole
  run. Every record of every ring is written. The kernel rings are only a
  buffer between one drain and the next, with at least 57 s of slack.
- **Whole-run summaries** live in the 384-byte stats block (section 10.4).
  It holds cumulative counters since boot: outcome histograms per ring and
  command, nesting count, maximum ACK polls, the thread's per-branch and
  delivery counters, LED counters, record cost and collector heartbeat. The
  collector writes a copy to the stick every second. Even if chunks of
  records were lost, the counters still bracket what happened.
- **No trigger, no freeze, no dump.** Onset is found afterwards by the
  decoder. So a failure shape that never "fires" anything is still fully
  recorded (D5), and nothing can freeze too early or too late (D4).

### 3.3 Writer protocol (each ring has one writer)

```
s = head; r = &ring[s & (N-1)];
r->seq = 0xFFFFFFFF; barrier();
fill fields; barrier();
r->seq = s;       barrier();
head = s + 1;
```

On this uniprocessor, `barrier()` (a compiler barrier) is enough: a CPU
sees its own stores in program order, and the reader runs on the same CPU.
No LL/SC or atomics are used. Whether Allegrex supports LL/SC is UNVERIFIED,
even though `.config:109` sets `CONFIG_CPU_HAS_LLSC=y`, so the design avoids
them.

### 3.4 Why each ring has only one writer (D9)

| Ring | Writers | Can two writers be active at once? |
|---|---|---|
| W | `psc_record` with `psc_wd_active=1`, set only inside `psp_pacify_watchdog`, which runs only with interrupts off (2.2) | No. With interrupts off there is no preemption and no other interrupt, and a second watchdog call cannot nest inside the first. |
| P | Only the task `psc_jp_task` (the poll thread). A watchdog command that interrupts it is routed to W by the WD test, which is made first. | No. A thread cannot run twice concurrently. Other tasks that preempt it are routed to M. |
| M | Any other thread-context caller. Known callers: `pspSysconCtrlHRPower` once at boot (`serial_psp.c:352`, C4), and `pspSysconPowerStandby` at shutdown (`psp.c:218`, C7). | Not for the known callers. C4 runs in the serial initcall, which comes before the joypad initcall (`drivers/Makefile:28` `serial/` before `:59` `input/`; the 2008 boot log `kmsg.txt:22` UART3 before `:29` Joypad), and `console=tty` (`pspboot.conf`, dossier 9.7) means the UART3 console path is not used. C7 happens only at shutdown. **Two unknown thread-context callers could collide on M.** That is accepted: the seq check marks torn slots (section 11, risk R12). |

The interruption case (D9), stated explicitly: when the timer interrupt
interrupts the poll thread in the middle of `psc_record`, the watchdog
command writes only W, and reads P head, `psc_t_busy` and the stage fields,
which is harmless. The thread then continues its P record exactly where it
stopped. Every counter is also single-writer: histograms and maxima are
kept per ring, the `jp_*` counters are written by the thread only, and the
`led_*` counters are written by the Memory Stick I/O path only, which runs
with preemption disabled (recon §2.2). `jp_opens` and `jp_releases` can be
written by two concurrent openers. That tiny race is accepted, because
these are diagnostic counters only.

### 3.5 Reader protocol

Reading a record `s`:

1. Require `s < head`.
2. If `head − s > N`, the record has been overwritten: skip forward to
   `head − N`.
3. Copy the slot and check `seq == s` before and after the copy.
4. Deliver the record only if both checks pass. Otherwise skip it; the gap
   is visible in `seq`.

---

## 4. Extraction path

### 4.1 Kernel interface (`/proc/pspsc/`)

This uses custom `file_operations`, following the tree's own precedent at
`drivers/input/input.c:651-663`.

| File | Semantics |
|---|---|
| `p`, `w`, `m` | Binary record stream. The file offset is `seq × record_size`. `read()` returns only whole records from the requested seq up to the head, subject to the skip rule in 3.5, and advances `f_pos`. It returns 0 when nothing is new, and it never blocks. Each open has its own offset, so a restarted collector simply starts again from offset 0 and gets the oldest records still in the ring. |
| `stats` | A 384-byte snapshot, re-evaluated on every `read` at offset 0 |
| `ctl` | Write-only. The collector writes a 20-byte status (`'PSCW'`, bytes synced, jiffies of the last successful `fsync`, run/segment, last errno), and the stats block stores it. This puts the writer's health into both the HUD and the stick data without a writable RAM file. |

At initcall time the kernel prints **one** line: `PSC1 P2048 W128 M64 rec64/320 bootnop ret=%d nw=%d`.
It reports the `prom_init` watchdog record W[0]. That is the only printk.

### 4.2 Userland: a new collector `pscol`, derived from `telem.c`

**Why I chose a new program rather than extending telem.** telem's structure
conflicts with what is needed here:

- a single loop does both the HUD and the stick I/O, so a stuck `fsync`
  freezes the HUD;
- it reads the tty on stdin and quits on `q`, `Q`, `3` or ESC
  (`telem.c:356-359`);
- it silently falls back to RAM files when `/ms0` is missing
  (`:326`, `:293`);
- it blits the whole screen (`:299-306`);
- it detects kernel-log changes by length only (dossier 9.1, 6.2).

`pscol` keeps telem's proven pieces: the 5×7 font, the integer-only
`apps`/`appl` formatting, raw `write`, the no-printf rule
(`telem.c:29-34`), `nanosleep` pacing, and the `cbuild.sh` build with its
FP check.

**Processes.** All three are one binary, started once from `rc.sysinit`:

| Process | Role | Rate |
|---|---|---|
| `pscol` (supervisor) | Calls `setsid()`. Ignores SIGINT, SIGQUIT, SIGHUP, SIGTSTP, SIGTTIN, SIGTTOU and SIGPIPE; SIG_IGN survives `exec`. Starts `pscol -w` and `pscol -h` with `vfork` + `execve`. On `wait()`, sleeps 1 s and restarts whichever child died. It stops restarting a child after 20 deaths, and the HUD shows this. | idle |
| `pscol -w` (writer) | Reads `p`, `w` and `m` until empty, and drains `/dev/input/mice` (non-blocking, counting all packets and press edges), every 200 ms. Every 5th pass (1 Hz) it builds one flush: new records, stats, a PROCS chunk, a MOUSE chunk, a KMSG chunk if the kernel log's CRC changed, and a WRITER chunk. It pads the flush to a 512-byte boundary, then issues one `write`, one `fsync` and one `ctl` write. | 5 Hz read, 1 Hz write |
| `pscol -h` (HUD) | Reads `stats` and the last 4 P records, and draws a 480×112 band at the top of the screen (7 text rows). Blits only those rows. | 5 Hz |

- **Stick output.** Files are created in `/ms0/PSCLOG/`. Each run gets the
  next free run number, and each writer start opens a new segment:
  `T<run:03>S<seg:02>.BIN`, opened with `O_WRONLY | O_CREAT | O_EXCL | O_APPEND`.
  The writer never writes outside `/ms0/PSCLOG/` and never falls back to
  RAM. If `/ms0` is not mounted, or `statfs` shows less than 64 MB free,
  the writer does not start writing, and the HUD shows `NO STICK` or
  `STICK SPACE` in red. That is an abort condition (section 8).
- **Size cap.** A run stops appending at 48 MB, about 3.7 hours at the
  section 5 rate. The HUD then shows `LOG FULL`. Segments per run are capped
  at 32.
- **Start from rc.sysinit.** One line is inserted after the `/ms0` mount
  (`rc.sysinit:10-11`) and before `psposk2` (`:13-15`), so collection
  starts before the input daemons:
  ```
  printf "\\033[37mLaunching PSC collector\\t\\t\\t\\033[0m"
  /usr/bin/pscol </dev/null >/dev/null 2>&1 &
  printf "[  \\033[32mOK\\033[37m  ]\\033[0m\\n"
  ```
  `/dev/null` exists in the initramfs (`cpio -itv`: `dev/null c 1,3`).
  The busybox in the initramfs has no `sleep` applet (`extract/root2/bin`
  listing), so restarting is done in C by the supervisor, not by a shell
  loop.
- **What the collector never does.** It never opens `/dev/joypad`. Opening
  it would add a queue and a close path, which is the H9 trigger
  (`joypad_psp.c:319-359`). It never reads the tty.

### 4.3 What happens if parts of the collector die

| Failure | Effect | Data loss |
|---|---|---|
| Writer dies | The supervisor restarts it after 1 s. The new writer reads from ring offset 0, which gives the oldest 57 s of P (and all of W and M), so the gap is refilled. The decoder removes duplicates by (ring, seq). `proc_opens` in the stats counts the restarts. | None, if restarted within 57 s |
| HUD dies | It is restarted. Recording is unaffected. | None |
| Supervisor dies | The children keep running, but nothing will restart them any more. If the writer also dies later, the HUD shows `WRITER DEAD`, because its heartbeat in the stats is too old. | Everything after the writer dies (it stays in RAM and is lost at battery pull) |
| `fsync` blocks | The writer stalls. The kernel rings keep buffering. The HUD is a separate process, so it keeps running and shows `SYNC nn S` in red. | The time since the last completed sync, if the battery is pulled during the stall |
| Stick write error or full | The writer keeps retrying each second and puts the error in `ctl`. The HUD shows `WRITE ERR n` in red. | As above |
| Kernel stuck with preemption off (for example in Memory Stick PIO) | The HUD freezes: its heartbeat block stops blinking. This is a different failure shape from the one observed (dossier 3.1: the system stayed alive). | Everything since the last sync, at most about 1.5 s before the freeze |

### 4.4 Worst-case loss at battery pull (D6)

- **Normal case:** up to one flush interval (1.0 s) plus the flush's own
  duration. That duration is measured in the WRITER chunk and expected to
  be under 0.5 s (UNVERIFIED), so the loss is **about 1.5 s**.
- **Flushes are sector-aligned.** The file always grows by whole 512-byte
  sectors, so sectors that were already synced are never written again.
  Only the directory entry and FAT sectors are rewritten. A pull during a
  write can therefore damage only the flush in progress. If the FAT or
  directory entry is damaged, the chunk magic and CRC let the decoder
  recover everything from a raw image of the stick (runbook step A2).
- **Stalled writer:** the loss equals the stall, and the HUD shows it
  before the pull.
- The runbook's post-death wait is at least 60 s and ends with a check that
  `SYNC` is under 3 s. **So the loss is always shorter than the post-death
  wait.**

---

## 5. Budget

### 5.1 Stick volume

| Item | Rate | Per second |
|---|---|---|
| P records | ≤ 35.7/s × 64 B | ≤ 2,286 B |
| W records | 0.2/s × 320 B | 64 B |
| STATS chunk | 1/s × (16 + 384) | 400 B |
| PROCS chunk (stat lines for the poll thread, psposk2, pspmd and pscol ×3; the `MemFree` line) | 1/s, about 470 B | about 470 B |
| MOUSE + WRITER chunks | 1/s × (16+16) + (16+32) | 80 B |
| PREC/WREC/MREC chunk headers | about 2/s × 16 | 32 B |
| Padding to a sector boundary | 256 B average per flush | 256 B |
| **Total** | | **about 3.6 KB/s** |

- 15 minutes: **about 3.2 MB**. One hour: about 12.9 MB. Cap: 48 MB.
- Sector writes: about 7 data sectors, plus 1 directory-entry sector, plus
  occasional FAT sectors, per second. That is **about 8 to 9 sector writes/s,
  or about 17 LED RMW/s**, compared with section 7.5.

### 5.2 Kernel memory

About 176.6 KB of BSS (3.1), plus code estimated at about 3 KB
(UNVERIFIED until built). BSS is not in `vmlinux.bin`
([build.md §2](../recon/build.md): the image ends at `.init.ramfs`), so the
image grows only by the code, about 3 KB. `_end` moves up by about 180 KB.
`psp_detect_mem_size` starts its probe after `_end` (`psp.c:429`), so it
adapts.

### 5.3 Time added

Instruction counts are estimates. G2 must replace them with counts from
objdump. The run also measures the true cost as `rec_cost_*` in Count
units, which the HUD shows.

**Assumptions (UNVERIFIED):**

- about 1 instruction per cycle;
- 220.9 M cycles/s (`psp.c:38`, assuming Count runs at the core clock);
- up to 100 cycles per D-cache miss.

**Thread-context command (P), per command:**

| Where | Added instructions | Inside S5..S20? |
|---|---|---|
| A1 entry snapshot, globals, zero-init | about 24 | No, before `retry:` |
| A2 per attempt (`spin`, `spin_ack` init) | 4 per attempt | No: at `retry:`, before S1 |
| A3 window | **0** | Yes. Substitution only, verified by G2 (7.2). |
| A4 `nwords` + call | about 6 | No, after S20 |
| `psc_record` (P path) | about 110, plus ≤ 2 line misses | No |
| **Total per P command** | **about 145 instructions, about 0.66 µs; ≤ about 1.6 µs with misses** | 0 in the window |

**Per poll:** 2 commands plus about 40 instructions of thread counters,
which gives **about 1.5 µs, ≤ about 3.5 µs**. Against the minimum poll
period of 56 ms, that is about 0.006 %.

**Watchdog command (W):** about 18 at entry, plus about 8 for the flag, plus
about 110 for the record, plus about 130 for the extension. That is about
**265 instructions, about 1.2 µs, ≤ about 2.5 µs**, all added to the
existing interrupts-off time, and all after the watchdog's own transaction
has ended. It happens once per 1250 ticks.

**LED path:** about 10 instructions per call, after the RMW's store, about
17 times per second.

**Per timer tick with no watchdog command:** 0 added instructions. The
`psc_in_timer` stores are inside the `if` at `psp.c:376`.

A normal command's own duration is UNKNOWN from the source. It is measured
in the run as `c_end − c_start`, and the HUD shows the median, so the
"small against the command" claim (D10) is checked on the device within
the first seconds.

---

## 6. Coverage matrix

**Definitions used below.**

- `R(cmd)` is a P record with that command byte.
- "Onset" is found by the decoder (10.7), never on the device.
- `key` means `rx[3] | rx[4]<<8 | rx[5]<<16 | rx[6]<<24` (`syscon.c:363`).
- `branch` is recomputed from the record: R3 if `ret < 0`, R4 if
  `(~key) & 0x2000`, otherwise R5 (`joypad_psp.c:487-495`).

| ID | Identifying fields and values | Could be confused with | How the record separates them |
|---|---|---|---|
| **H0** Unknown | No rule below matches. The decoder prints the raw window: every P, W and M record from onset−30 s to onset+60 s, with the stats time series and the PROCS lines. | — | Raw data is always kept (D3) |
| **H1** No ACK | From onset on, the `R(0x33)` and `R(0x08)` records have `ret ∈ {−4, −3}`, `ack_polls = 1,000,001` (−4) or `drain = 0xFFFF` (−3), `nwords = 0`, `rx` all `ff`, and `c_end − c_start` at the full budget. Stats `hist[P][5]` grows at 2 per poll. **The 9.5 variant:** W records at the same time have `ret ≥ 0` and `ack_polls` normal, meaning the watchdog's command 0x00 is still answered. | A single −4 left behind by H4 at P4 or P5a (recon §5.1) | Persistence: every poll after onset versus a single poll. The W `ret` separates pure H1 from the variant. |
| **H2** All-zero, HOLD | `R(0x08)`: `ret = 0`, `nwords ≥ 1`, `rx[3..6] = 00` (in fact all received bytes `00`), branch R4. Stats `jp_r4` rises at 1 per poll. | The real HOLD switch | The real HOLD switch clears only bit 13 of the raw word (`rx[4]` bit 5, i.e. `0x2000` of `key` is 0), while every other bit is `1` (active low, `syscon.h:6`). H2 has every bit 0. The runbook toggles HOLD once before death as a reference. |
| **H3** Empty FIFO | `R(0x08)`: `ret = 0`, `nwords = 0`, `rx` all `ff`, `ack_polls` normal (an ACK was seen), branch R5 with `key` inverted to 0. The decoder's mouse simulation shows +16 X and −16 Y per poll in mouse mode (`joypad_psp.c:690`, `:652`). | One-poll E3 after an H4 interleave at P3, P4, P5a or P5b | Persistence, and the W extension's EPC for the triggering interleave |
| **H4** Watchdog interleave | A W record with `t_busy = 1` and `ext_flags` bit 3 set, meaning EPC is inside `Syscon_cmd` and `current` is the poll thread (ctx JPT in W). The EPC map (10.6) names the step S5..S20 and the interruption point P1..P7. The following P record with seq equal to W's `xseq` has `wn ≥ 1`. The onset is at that P record or the next poll, and its time equals the W boundary. P4 versus P5a is decided by the watchdog's own record: `ack_polls = 0` (latch already set) or `drain > 0` with `drain_last` shaped like the thread's reply means P5a; `ack_polls > 0` and `drain = 0` means P4. The interrupted thread's `spin_ack`, from `stk`, gives how long it had waited before the watchdog command. | H10 (both disturb the link mid-transaction); a thread preempted mid-command (H11) | EPC inside `Syscon_cmd` versus EPC inside `psp_gpio_*` or elsewhere; `ms_delta`; `preempt_delta`. **H4 is the trigger. The persistent shape afterwards is reported separately** as H1, H2, H3, H5, H6 or H0. That is the question 9.6 leaves open. |
| **H5** Checksum or BUSY | `ret ∈ {−2, −5}` dominant after onset. `retries = 16` on −5. `rx[2] ∈ {0x80, 0x81}` (−5), or `rx[1] < 3`, or a checksum mismatch that the decoder can recompute from `rx` (−2). If `rx[1] ≥ 16`, the decoder flags the out-of-bounds checksum (dossier 9.1 on 4.6). | H4 P2 or P6 (a single −2) | Persistence; the `rx` pattern (for example a 1-byte shift) |
| **H6** Stale frames | `R(0x08)`: `ret ≥ 0` and a valid checksum. `rx[0..8]` are **byte-identical** for every poll after onset, **including the analog bytes `rx[7]` and `rx[8]`**. Normal analog jitter is expected; that is UNVERIFIED, and the decoder learns the pre-onset jitter from the same run. They stay identical through the runbook's post-death presses (D1..D5), which would otherwise change `key` bits 4, 9, 16 and 13 and the analog bytes. | H7 (fresh data, delivery broken) | H6: the raw data does not follow the presses. H7: the raw data follows the presses. |
| **H7** Above the syscon | Raw `key` bits change in step with D1..D5 after onset, and branch R5 has changes. Delivery shows where it stops: `jp_proc_calls` and `jp_proc_dedupe` (process reached?), `jp_listsem_fail`, `jp_push_*`, `jp_mouse_reports`, the MOUSE chunk packet count (did packets reach userland?), and `jp_state`, `jp_sigpending` and `jp_wchan`. The decoder simulates `lastKeys` and `mouseMode` (`:505-527`) from the P records to predict what should have been delivered, and compares. | H9 (a subclass); H6 | If P records keep arriving, it is not H9. The raw data changing separates it from H6. |
| **H8** Controller state | `gpio_in`, `spi_st9`, `spi_sttx`, the `drain` rate, `ack_polls = 0` rate, and the `led_rd_*_b3` counters, compared before and after onset. **Limited by design:** registers the code never reads (for example `0xbe580004`, `0xbe580020`) are not observed (section 11, R3). | H4 or H10 leaving the hardware in a new state | The distributions change at onset; the EPC and `ms_delta` show what disturbed it |
| **H9** Deadlock | After onset, no P records while W records keep coming. In W: `jp_loop` constant, `jp_stage ∈ {4 LISTSEM, 5 PUSH}`. Stats: `jp_state = 1` (INTERRUPTIBLE), `jp_wchan` in `__down_interruptible`/`schedule` (via `System.map`), `jp_releases` rises and `jp_free_inflight = 1` just before onset. PROCS shows whether psposk2 has exited. | The thread stopped elsewhere (H7), for example `stage = 3 LCD`, or 7 MOUSE with the thread running (I9 loop) | The stage code and task state say where the thread is stopped |
| **H10** LED RMW | The P records just before onset have `ms_delta > 0` (an LED RMW happened between the command's entry and end), usually with `preempt_delta > 0`, because the thread must have been off the CPU. Alternatively a W record's EPC is inside `psp_gpio_set` or `psp_gpio_clear`, between their load and store. `gpio_in` bit 3 = 1 at S5 means G3 was high before the request. `led_rd_*_b3 > 0` proves a read of the set or clear register can return G3, which is the precondition. **If `led_rd_*_b3` stays 0 for the whole run, the H10 mechanism is refuted by the run.** | H4 | EPC location, `ms_delta`, `wn` |

### 6.1 Failure shapes not in the dossier, covered by the same fields

| Shape | Signature |
|---|---|
| H11: the thread is preempted mid-transaction (G3 high, M = 6) for a long time, with no watchdog command and no LED RMW | `preempt_delta > 0`, `c_end − c_start` far larger than `ack_polls` accounts for, `wn = 0`, `ms_delta = 0`, then onset |
| H12: TX or RX FIFO carry-over, meaning a permanent off-by-one in framing | `drain > 0` on every command after onset. The `rx[2]` response code equals the *previous* command's code (0x33 answered to 0x08, and so on). The decoder checks that `rx[2]` matches `cmd`. |
| H13: the syscon accepts commands but answers with 0x83 or 0x86 (accepted as success, dossier 9.1 on 4.6) | `rx[2] ∈ {0x83, 0x86}`, `ret > 0` |
| H14: the thread wedges in `psp_lcd_on` / `do_unblank_screen` once the console blanks (reachable after about 600 s; recon/input 1.7) | W records show `jp_stage = 3` fixed. `console_blanked` in the stats. |
| H15: the thread spins in the input core on a freed mousedev client (recon/input I9) | `jp_stage = 7` fixed, `jp_loop` fixed, `jp_state = 0` (running), the W EPC inside `mousedev_*` |
| H16: userland consumers die while kernel delivery works | `jp_push_ok` and MOUSE packets keep rising. The PROCS lines show psposk2 or pspmd missing, zombie or stuck. |
| H17: the 2008 image and this tree differ (dossier 9.5) | Not observable on the device. If this kernel never dies within 20 minutes, that is reported as a result together with section 7. |

---

## 7. Perturbation statement

### 7.1 What changes

| Aspect | Change | Effect on the syscon transaction |
|---|---|---|
| Locks | **None added.** No spinlock, semaphore, `preempt_disable` or atomic operation anywhere on the new paths. | None |
| Interrupt state | **None changed.** No `local_irq_*`. Records made in the watchdog run in the existing interrupts-off region. | None |
| Delay | **None inside S5..S20.** About 24 + 4 instructions before S5, and about 116 after S20. | The start of each command moves by about 0.13 µs, and the next command by about 0.66 µs (up to 1.6 µs) |
| Timer interrupt | Only in watchdog ticks: about 265 instructions after the watchdog's S20. That is about 1.2 µs (up to 2.5 µs) of extra interrupts-off time every 1250 ticks. Other ticks: 0. | The thread's resumption after a watchdog command is delayed by about 1.2 µs. Hardware state is latched meanwhile (see 7.3). |
| Printk | One line at init. Nothing at poll rate. | None |
| Code layout | `Syscon_cmd`'s frame grows by about 16 bytes. The kernel text grows by about 3 KB, and all later functions move. | I-cache alignment of the ACK and drain loops may change, which changes the loop iteration time and therefore the wall-clock length of the spin budget. `ack_polls` together with duration measures this in the run. |
| Memory | About 177 KB less RAM for userland (0.85 % of `MemFree`) | None on the syscon |
| Userland load | See 7.4 | See 7.4 |

### 7.2 The "zero instructions in the window" claim and how G2 verifies it

The window runs from the load at S5 (`syscon.c:102`, [OBJ] `Syscon_cmd+0xdc`)
to the store at S20 (`syscon.c:222`).

- In the baseline, `dmy` is a `volatile u16`. Each `dmy = REG32(x)` compiles
  to `lw`, `andi 0xffff`, `sh` ([OBJ] `+0xdc..+0xe4`).
- Assigning to another `vu16` produces the same three instructions with a
  different stack offset.
- `spin_ack` (`vu32`) replaces `spin` in the ACK loop, with the same
  11-instruction loop body ([OBJ] recon §1.5).

**G2 acceptance criteria:**

1. In `objdump -d vmlinux`, the instructions from the S5 load to the S20
   store contain the same MMIO accesses, in the same order.
2. The drain loop, TX loop, ACK loop and RX loop bodies have the same
   instruction counts as baseline `syscon.o`.
3. There are no added calls or loads of globals in that range.

If the compiler adds spills (from more locals), the implementer removes
capture variables in this order until the criteria hold, and records it as
a deviation: `spi_sttx`, then `drain_last`, then `spi_st9`, then `gin`. The
last fallback reuses `spin` for the ACK loop, which loses `drain`. Nothing
else in the design depends on those fields for classification. They are
supporting evidence only.

### 7.3 Why this neither hides nor causes H4

- Whether an interleave happens depends on whether a watchdog command (at
  the very start of a tick handler, `psp.c:350-359`) lands while a thread
  command is between S5 and S20. The poll thread wakes on a tick boundary
  (`msleep` rounds to jiffies, recon/input §4). So what matters is the
  command's start phase in the tick, and its length.
- We add nothing to the length inside the window. We add about 0.13 µs
  before S5 and at most about 1.6 µs between the 0x33 command and the 0x08
  command. The 0x08 command's start phase therefore moves by at most 1.6 µs
  of a 4,000 µs tick. The probability that a command straddles a tick
  boundary changes by at most 1.6/4000 = 0.04 percentage points.
- More importantly, **the run measures the hazard directly**. Every P record
  has `c_start`, `c_end` and `dj`, so the decoder gives the distribution of
  command phase and length, and counts every straddle of a tick boundary
  and of a watchdog boundary.
- **Resumption after a watchdog command.** The thread resumes about 1.2 µs
  later than it would have. If G4L is a latched status, which the code
  treats it as (a separate acknowledge write, `syscon.c:159`), a delay
  cannot lose an edge. If it is level-sensitive, a pulse shorter than
  1.2 µs could be missed. That is UNVERIFIED hardware behaviour and is
  listed as R4.

### 7.4 Userland load

What we know about the conditions of the observed deaths:

- The three bracketed deaths (dossier 9.6) happened with telem running at
  one tick per about 0.23 s, doing a full-screen 522 KB blit, a 16 KB
  `syslog` read and a `write` + `fsync` each tick (`telem.c:299-306`,
  `:348`, `:411-412`; tick length from the recovered logs).
- The operator was generating input about 4 times per second, in mouse
  mode (the INPUT counter counts mouse press edges, dossier 9.1).
- Two sessions were already dead when telem started (9.6), so death does
  not need telem's periodic writes. That is a [HYP] reading of the evidence.

`pscol` compared with telem:

| Activity | pscol | telem |
|---|---|---|
| Blit | 215 KB at 5 Hz (the 112-row band) | 522 KB at about 4.3 Hz |
| `/proc` reads | 5 Hz | |
| `write` + `fsync` | 1 Hz | about 4.3 Hz |

The CPU and bus load is the same order and somewhat lower. The runbook asks
the operator to repeat the same input pattern and mode (section 9). The
remaining difference is recorded in the run: the process CPU times in
PROCS, and the thread's wake-up phase in the P records.

### 7.5 How our Memory Stick writes interact with H10 (required statement)

- **Rate.** Each sector costs two LED RMWs (`ms_psp.c:290,292` and
  `:312,314`).
  - telem, in the conditions of the observed deaths: about 4.3 flushes/s,
    each about 1 data sector plus 1 directory-entry sector. That is about
    8.7 sector writes/s, or **about 17 LED RMW/s**.
  - pscol: 1 flush/s of about 7 data sectors plus 1 directory-entry sector
    plus occasional FAT. That is about 8.5 sector writes/s, or **about 17
    LED RMW/s**.

  We neither remove the exposure (which could hide H10) nor multiply it
  (which could cause it). The cadence differs: bursts once a second, rather
  than small writes 4 times a second. That is stated here as a known
  difference.
- **Measured, not assumed.** The stats count every LED RMW (`led_calls`) and
  every one that happened while a thread command was in flight
  (`led_calls_t_busy`). Each P record carries `ms_delta`. A watchdog command
  that lands inside an RMW shows its EPC inside `psp_gpio_*`.
  `led_rd_*_b3` tells whether the RMW could ever write G3 at all. If it
  never reads bit 3 set, H10's mechanism cannot occur on this hardware, and
  the run shows that.
- **Onset correlation.** The decoder reports the time from each onset to
  the nearest LED RMW and the nearest writer flush (WRITER chunk). The
  analyst can also compare onset times with the 1 Hz flush phase: H10
  predicts clustering near flushes, H4 near 5 s boundaries.

---

## 8. Self-test

### 8.1 Kernel, within the first seconds of boot

The one printk at initcall time
(`PSC1 P2048 W128 M64 rec64/320 bootnop ret=… nw=…`) appears on the
framebuffer text console, since `console=tty` (dossier 9.7). It proves:

- this is the instrumented kernel;
- the W ring recorded the `prom_init` watchdog command.

### 8.2 HUD, a few seconds after `/ms0` is mounted

A PASS line needs all of the following:

| Check | Condition |
|---|---|
| ST1 KRN | `/proc/pspsc/stats` has the right magic and version, and `build_id` equals the value compiled into `pscol` |
| ST2 POLL | P head advances at ≥ 15/s; the latest `R(0x08)` has `ret ≥ 0` and `nwords ≥ 1` |
| ST3 WDOG | W[0] exists with ctx WD=1, IRQOFF=1, TIMER=0. After about 5 s, a W record with TIMER=1 exists, and consecutive TIMER W records are 1250 jiffies apart |
| ST4 CTX | P records have JPT=1, WD=0, ring=0. W records have WD=1, ring=1. `ext_flags` bit 0 (regs valid) is set on the TIMER W record |
| ST5 STICK | Segment file open under `/ms0/PSCLOG/`, the first `fsync` returned 0, `SYNC` age < 3 s, free space ≥ 64 MB |
| ST6 REC | The latest P record passes internal checks: if `nwords = 0` then `rx` is all `ff`; if `ret > 0` then `rx[0] == ret`; `nwords ≤ 8` |
| ST7 BTN | The operator holds TRIANGLE; the HUD sees bit 0x10 of `key` go to 0 in a P record, and back |

The HUD also shows, from the start:

- the median P command duration and `rec_cost_max` in µs, so that the D10
  ratio is visible;
- `MOUSE ON/OFF`, from `jp_keys & 0x00800000`.

### 8.3 Abort rule

- If ST1 to ST6 are not all PASS within 60 s of the HUD first appearing, or
  the HUD does not appear within 120 s of launching: power off, photograph
  the screen, report. This does not count as the run.
- **Exception.** If ST1 to ST6 pass but ST7 fails three times, this is
  treated as an early death, not an abort. Input may already be dead (9.6
  shows deaths before 36 s). The operator goes straight to the post-death
  script. The kernel rings hold the boot-onward history (P for at least
  57 s), and the writer replays it from offset 0.

---

## 9. Runbook

The full text is in [candidate-A-RUNBOOK.md](candidate-A-RUNBOOK.md). In
summary:

1. **Deploy.**
   - Create the new folder `PSP/GAME/uClinux_TRACE/`. Do not use `uClinux`,
     `uClinux_FIX` or `uClinux_WIP` (dossier 9.7).
   - Copy `EBOOT.PBP`, `kmodlib.prx` and `pspboot.conf` verbatim from the
     baseline folder, plus our `vmlinux-0.22.bin`. `pspboot.conf` keeps
     `kernel=vmlinux-0.22.bin` and `cmdline=console=tty osk=Dv4`.
   - Check there are ≥ 64 MB free.
   - Run on battery only, with no AC adapter.
2. **Boot, self-test.** Start a stopwatch. Check for the printk, then the
   HUD PASS. Photograph it. Apply the abort rule.
3. **Reference pattern.** At PASS + 30 s, tap SELECT once and check the HUD
   shows MOUSE ON. Then perform the post-death sequence D1..D5 once while
   input is healthy. This gives the healthy reference for H6/H7/H2.
4. **Pre-death input.** Repeat the telem sessions' pattern: mouse mode on,
   L-trigger clicks about 4 times per second, until death or 20:00 on the
   stopwatch. Watch `DELIV` on the HUD. Photograph the HUD every 5
   minutes.
5. **At death.** The signs are: `DELIV` stops rising above 2 s while
   clicking; the cursor stops; the OSK does not appear. Note the stopwatch
   time. Photograph.
6. **Post-death script** (about 75 s):
   - D1: TRIANGLE held 3 s on, 3 s off, twice.
   - D2: L trigger held 3 s.
   - D3: VOL+ held 3 s.
   - D4: analog stick full right 3 s, full up 3 s.
   - D5: HOLD switch on 5 s, then off 5 s.
   - D6: photograph the RAW line while holding TRIANGLE.
   - D7: hands off 10 s; check `SYNC` < 3 s; photograph.
   - D8: pull the battery.
7. **No death by 20:00.** Run D1..D8 anyway, and report "no failure".
8. **HUD frozen.** Note the time, photograph, wait 30 s, photograph, pull.
9. **After the run.** Make a raw read-only image of the stick on the Mac
   (`diskutil list`, `diskutil unmountDisk`, `sudo dd if=/dev/rdiskN
   of=…img bs=1m`) before anything mounts it. Then copy `PSCLOG/`. Return
   the image, the files, the photos, the stopwatch notes and any departures
   from the runbook.

---

## 10. Decoder specification

### 10.1 Inputs

- One or more `T###S##.BIN` files, **or** a raw stick image to scan.
- `System.map`, and the EPC map `epcmap.txt` (10.6) from the exact build.
  The decoder checks the addresses at stats offsets 56..71 against
  `System.map`.

### 10.2 File and chunk format

A file is a sequence of chunks. Each flush is padded with a PAD chunk to a
512-byte boundary.

**Chunk header, 16 bytes:**

| Off | Type | Field |
|---|---|---|
| 0 | u8[4] | magic `'P','S','C','K'` |
| 4 | u16 | `type` |
| 6 | u16 | `hver` = 1 |
| 8 | u32 | `len` (payload bytes) |
| 12 | u32 | `crc32` of the payload (IEEE 802.3 polynomial, as zlib `crc32`) |

**Chunk types:**

| Type | Name | Payload |
|---|---|---|
| 0 | PAD | zeros (CRC still valid) |
| 1 | FILEHDR | `'PSCLOG1\0'`, u32 version = 1, u32 run, u32 seg, u32 writer pid, u32 `now_jiffies` at open, the 384-byte stats block, then `/proc/version` text (up to 256 bytes, NUL-padded to 256) |
| 2 | PREC | n × 64-byte common records (P ring) |
| 3 | WREC | n × 320-byte W records |
| 4 | MREC | n × 64-byte common records (M ring) |
| 5 | STATS | the 384-byte stats block (10.4) |
| 6 | PROCS | text. Each line is `<label> <pid> <contents of /proc/<pid>/stat>\n`, for labels `JP`, `OSK`, `MD`, `SUP`, `WR`, `HUD`. Then `MEM <MemFree line>\n` and `UP <contents of /proc/uptime>`. |
| 7 | MOUSE | u32 packets total, u32 packets this second, u32 press edges total, u8[3] last packet, u8 pad |
| 8 | KMSG | the whole kernel log text (`syslog(3)`), written only when its CRC32 changes |
| 9 | WRITER | u32 flush number, u32 `j_before_write`, u32 `j_after_write`, u32 `j_after_fsync` (each from `stats.now_jiffies`), s32 `write` return, s32 `fsync` return, u32 records skipped by the reader (seq gaps), u32 flags |
| 10 | EVENT | text: writer start, restart count, errors |

**Parsing rules:**

- Scan byte-wise for the magic. Accept a chunk only if the type is known,
  `len` ≤ 1 MB, and the CRC matches. A chunk cut by a battery pull fails
  its CRC and is dropped; everything before it is kept (Stage 3 truncation
  test).
- For a raw image, scan the whole image the same way. Group chunks by
  `(run, seg)` using the most recent FILEHDR seen.

### 10.3 Record formats

Exactly as in sections 1.1 and 1.2. The decoder must implement them field
for field, including offsets, widths and signedness (`ret` is s16). Records
with `seq = 0xFFFFFFFF` are dropped. Duplicates by (ring, seq) are removed.
Gaps are reported.

### 10.4 Stats block (384 bytes, u32 unless marked)

| Off | Field | Off | Field |
|---|---|---|---|
| 0 | magic `0x54535350` (`'PSST'`) | 4 | u16 version = 1, u16 size = 384 |
| 8 | u16 `p_rec_size` 64, u16 `w_rec_size` 320 | 12 | u16 `p_ring_n` 2048, u16 `w_ring_n` 128 |
| 16 | u16 `m_ring_n` 64, u16 `hz` 250 | 20 | `counts_per_tick` 883651 |
| 24 | `initial_jiffies` | 28 | `spin_max` 1000000 |
| 32 | `now_jiffies` | 36 | `now_count` |
| 40 | `p_head` | 44 | `w_head` |
| 48 | `m_head` | 52 | `m_dropped` |
| 56 | addr `Syscon_cmd` | 60 | addr `psc_record` |
| 64 | addr `_pspSysconGetCtrl2` | 68 | addr `pspSyscon_tx_dword` |
| 72..199 | `hist[32]`: [0..7] P cmd 0x08; [8..15] P other; [16..23] W; [24..31] M. Outcome index: 0 `ret > 0`; 1 `ret == 0 && nw > 0`; 2 `ret == 0 && nw == 0`; 3 −2; 4 −3; 5 −4; 6 −5; 7 other | 200 | `p_nested` (P records with `wn > 0`) |
| 204 | `p_max_ack` | 208 | `w_max_ack` |
| 212 | `p_rec_cost_last` (Count units) | 216 | `p_rec_cost_max` |
| 220 | `w_rec_cost_max` | 224 | `wd_calls` |
| 228 | `wd_last_jiffies` | 232 | `jp_loop` |
| 236 | `jp_r3` | 240 | `jp_r4` |
| 244 | `jp_r5` | 248 | `jp_proc_calls` |
| 252 | `jp_proc_dedupe` | 256 | `jp_listsem_fail` |
| 260 | `jp_push_ok` | 264 | `jp_push_semfail` |
| 268 | `jp_push_full` | 272 | `jp_mouse_calls` |
| 276 | `jp_mouse_reports` | 280 | `jp_opens` |
| 284 | `jp_releases` | 288 | `jp_free_semfail` |
| 292 | `jp_free_inflight` | 296 | `jp_keys` |
| 300 | u8 `jp_stage`, u8 `jp_state` (0xff if no task), u8 `jp_sigpending`, u8 `console_blanked` | 304 | `jp_pid` |
| 308 | `jp_wchan` | 312 | `jp_nvcsw` |
| 316 | `jp_nivcsw` | 320 | `led_calls` |
| 324 | `led_calls_t_busy` | 328 | `led_rd_set_b3` |
| 332 | `led_rd_clr_b3` | 336 | `led_last_rd_set` |
| 340 | `led_last_rd_clr` | 344 | `proc_opens` |
| 348 | `proc_reads` | 352 | `last_reader_jiffies` |
| 356 | `wr_magic` (`'PSCW'` when valid) | 360 | `wr_bytes_synced` |
| 364 | `wr_last_sync_jiffies` | 368 | `wr_seg` (run<<16 \| seg) |
| 372 | `wr_err` | 376 | `build_id` |
| 380 | `t_busy` (current value) | | |

Stage codes: 0 not started, 1 READ, 2 PROC, 3 LCD, 4 LISTSEM, 5 PUSH,
6 WAKE, 7 MOUSE, 8 SLEEP.

### 10.5 Time reconstruction

Let `CPT = counts_per_tick` and `IJ = initial_jiffies`.

**Tick index of a record:**

- W records (ctx bit 0 WD, and bit 5 TIMER): `T = j_end + 1 − IJ`. Inside the
  watchdog command, Count has already been reset but `jiffies` has not yet
  been incremented (dossier 9.1 on 6.4; recon §6 caveat 1).
- The boot W[0] (TIMER = 0): `T = j_end − IJ`.
- P and M records: `T = j_end − IJ`. If ctx bit 4 (TORN) is set and
  `c_end ≥ CPT/2`, use `T − 1`, because the tick fell between the Count
  read and the second jiffies read (recon §6 caveat 2).

**Fine time:** `t = T × CPT + c_end`, in Count units. Display it as
`T / 250` seconds of uptime plus `c_end / 220.9 MHz`. If `c_end > CPT`, flag
"long tick": a lost tick is possible (recon §6 caveat 3).

**Start time:** `j_start = j_end − dj`. `t_start = (j_start − IJ) × CPT + c_start`.
This has an error of ±1 tick when `dj > 0`; the decoder notes it.

**Watchdog alignment:**

- Every W record with TIMER set is a boundary. The boundaries should be
  1250 ticks apart. The decoder checks this and reports any deviation.
- Each P record gets a phase: the number of ticks and counts since the
  previous boundary.
- A P record *straddles* a boundary if the boundary lies in
  `[t_start, t_end]`. Its `wn` must then be ≥ 1, and the decoder checks
  this consistency.
- This alignment does not depend on `localTick` or on the INITIAL_JIFFIES
  offset. It uses the boundaries in the data. That resolves the
  zero-point caveat in dossier 9.6.

### 10.6 EPC map

This map is produced in Stage 2 from `objdump -d vmlinux` of the final
build, reviewed at G2, and tested in Stage 3. It is a text file with one
line per address range:

```
<start> <end> <step>
```

Steps are S1 to S23, `ENTRY`, `EXIT`, `REC`, and for other functions the
symbol name.

Step to interruption point (recon §5.1):

| Steps | Point |
|---|---|
| S1–S4, `ENTRY`, `EXIT`, `REC` | P0 |
| S5–S10 | P1 |
| S11 | P2, with k taken from the `i` register in `gpr` |
| S12–S13 | P3 |
| S14 | P4 or P5a, decided by the watchdog's own `ack_polls` and `drain` (section 6, H4 row) |
| between S14 exit and S15 | P5b |
| S16–S18 | P6, with j from `ptr` in `gpr` |
| S19–S20 | P7 |

The register-to-variable and stack-offset-to-variable assignments for
`Syscon_cmd` are part of the same file. If Cause.BD is set, EPC is the
branch, and the decoder reports "EPC or its delay slot".

### 10.7 Algorithm and outputs

1. Parse, validate and de-duplicate. Merge P, W and M into one timeline
   ordered by `t`. Break ties by ring order W before P, because a watchdog
   command completes before the thread command it interrupted.
2. **Healthy template.** From the 30 s after the self-test PASS, find the
   typical values of `nwords`, `rx[1]`, `rx[2]` per command, the ranges of
   `ack_polls` and duration, the analog jitter, and the distribution of
   `gpio_in`, `spi_st9` and `spi_sttx`.
3. **Per poll**, pair the 0x33 and 0x08 records by `loop`. Recompute the
   branch (R3, R4 or R5). Simulate `lastKeys` and `mouseMode` and the mouse
   deltas (`joypad_psp.c:505-527`, `:593-658`) to get the expected delivery
   events.
4. **Onset candidates.** Report each of these:
   - last raw change of `key`;
   - last R5 poll with a changed combined word;
   - last rise in the stats series `jp_proc_calls`, `jp_push_ok` and
     `jp_mouse_reports`;
   - last MOUSE packet;
   - start of the longest trailing run of anomalous records.

   The onset is the start of the anomalous run if there is one, otherwise
   the last delivery. The decoder also prints the operator's stopwatch
   time for comparison, after offsetting the stopwatch by the HUD's first
   PASS photograph.
5. **Classify** using the section 6 rules, in this order:
   - H9 and thread-stopped shapes;
   - persistent-state shapes H1, H2, H3, H5, H6 and H12–H13;
   - H7 localisation;
   - H8 distribution shifts;
   - trigger analysis: H4 (the W record and EPC point nearest onset) and
     H10 (`ms_delta`, `led_rd_b3`, EPC in `psp_gpio_*`), plus H11.

   A result is a triple: **trigger** (H4, H10, H11 or none), **persistent
   shape** (H1, H2, H3, H5, H6, H7, H9, H12..H16) and **H8 flags**. If no
   rule matches, the result is **H0**.
6. **Outputs:**
   - `records.csv` (every field, with `t` and phase);
   - `w_records.csv` (with the EPC step and interruption point);
   - `stats.csv` (the 1 Hz series);
   - `window.txt` (a raw hex dump from onset−30 s to onset+60 s);
   - `verdict.md`: the triple, the evidence record seqs, what is
     unexplained, and the H10 and H4 hazard statistics (the fraction of P
     commands straddling a tick, the rate of watchdog nesting, the rate of
     LED RMW during a command).
7. **Stage 3 tests** (WORKFLOW):
   - synthetic dumps for every row, including a watchdog command landing at
     each of P0 to P7, which must yield the right point;
   - truncation at any byte offset;
   - a 15-minute volume test at 20 polls/s.

---

## 11. Open risks (every place this design guesses)

| # | Risk | Where it matters | Mitigation or check |
|---|---|---|---|
| R1 | gcc may schedule capture code, or spill, into S5..S20 | The "0 in window" claim (7.2) | G2 objdump criteria; fallback removal order |
| R2 | The instructions-per-cycle rate, whether Count runs at the core clock, the D-cache line size and the miss penalty are all guesses | The µs figures in 5.3 | The run measures `rec_cost_*` and command duration; the HUD shows them |
| R3 | No new register reads, so H8 is observed only through values the code already reads (`0xbe240004`, `0xbe58000c`, drained words, the ACK and drain counts, the LED RMW reads). Registers such as `0xbe580004` and `0xbe580020` stay unobserved. | H8 | Accepted under dossier 9.1. A change in unobserved registers appears as a persistent shape with normal `gpio_in` and `spi_*`, and is reported as H0 or H8-unresolved. |
| R4 | Whether G4L is latched or level-sensitive (recon §4.2) | 7.3: the thread resumes about 1.2 µs later after a watchdog command | If level-sensitive, a pulse under 1.2 µs could be missed. Judged very unlikely. |
| R5 | Reading CP0 Count (`mfc0 $9`) is assumed free of side effects on Allegrex. Architecturally it is. This kernel never reads Count at run time today (the MIPS clocksource is not initialised, recon §6 fact 3). | Every record | A Count read is a coprocessor move, not MMIO. It is exercised from the self-test onward: a problem would show up before death. |
| R6 | The EPC and register capture assume `thread_info->regs` is set by `handle_int` (`genex.S:166-167`) and restored at `entry.S:39`, and that the timer interrupt is dispatched only through that path | H4 phase resolution | The bound checks make it safe even if wrong. ST4 on the HUD checks "regs valid". |
| R7 | If the poll thread is **preempted** (not interrupted) in the middle of a transaction, the watchdog's EPC shows the other task, not the thread's step. We know the thread was in flight (`t_busy`, `t_entry_*`), for how long, and whether LED RMWs or a watchdog command happened meanwhile, **but not at which step it was suspended.** | H11, H10, part of H4 | Considered and rejected on perturbation grounds: sampling the EPC on every tick while `t_busy` is set (about 5 instructions per tick, plus about 60 when busy). It can be added if G1 requires it. |
| R8 | Only the **final** attempt of a retried command is recorded (`retries` counts the rest) | H5 detail | `hist` and `retries` show that retries happened; the intermediate frames are lost |
| R9 | The conditions of the observed deaths (telem load, mouse mode, which buttons were pressed, AC or battery) are partly unknown. The runbook reproduces what 9.6 implies. | Reproduction probability | Ask the operator: which buttons were pressed in the telem sessions, and whether it was on AC or battery |
| R10 | The failure was observed on the 2008 image. This kernel descends from observation 6's kernel, which died "on the same timescale" (dossier 3.6), but with no bracketed timing | Whether it will die at all | "No failure in 20 minutes" is reported as a result, with section 7 |
| R11 | vfat append + `fsync` behaviour, whether sector-aligned appends avoid rewriting old sectors, and the flush duration are all assumed | D6 (1.5 s loss) | WRITER chunks measure it; the raw image plus chunk CRC recovers data even if FAT is corrupted |
| R12 | Two unknown thread-context syscon callers could tear an M slot | M ring only | The seq check drops torn slots. No such caller is known. |
| R13 | `get_wchan` without kallsyms may return 0 (recon/input 7.3) | H9 detail | The stage code and task state cover it |
| R14 | Which buttons are harmless with the OSK hidden. HOME+CIRCLE+CROSS is a power-off chord (recon/input 5.1). SELECT toggles mouse mode. | Runbook safety | The runbook forbids HOME, SELECT (after the first tap) and L+R together. The operator may substitute buttons they know to be harmless. |
| R15 | The 112-row HUD band and 5 Hz blit differ from telem's full screen | 7.4 load | Measured in PROCS (CPU times). Judged small. |
| R16 | The initramfs root must allow `/usr/bin/pscol` to be added. `.config:163` points at the original tree's cpio (dossier 9.1). | Build | Stage 2 must change `.config:163` in its own commit |
| R17 | uClibc `vfork`, `execve`, `setsid` and `nanosleep` are assumed available (telem uses `nanosleep`, `telem.c:415`) | Supervisor | Stage 3 links it and checks `flthdr` |
| R18 | The H6 rule assumes the analog bytes normally jitter | Separating H6 from H7 | The decoder learns the jitter from the healthy template. If there is none, H6 rests on D1..D5 alone. |
| R19 | The pspboot `EBOOT.PBP` must load a kernel image about 3 KB larger (UNVERIFIED size, and pspboot's size limit is unknown) | Boot | The size difference is stated at G2 C6. A boot failure shows up at self-test (the abort rule), so it costs no run. |
