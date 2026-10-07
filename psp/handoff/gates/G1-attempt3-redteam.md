# Gate G1, attempt 3: red team report

Artifact under review: `design/DESIGN.md` and `design/RUNBOOK.md`, revision 2
(2026-10-01, after the G1 attempt-2 FAIL).
Reviewer role: G1 red team, attempt 3. Fresh context. I did not write the
design or any earlier gate report.
Date: 2026-10-01.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding), `WORKFLOW.md`, `recon/syscon.md`, `recon/input.md`,
`recon/build.md` (sections 0-4; the rest is packaging), `gates/LOG.md`,
`gates/G1-attempt2-redteam.md`, `design/DESIGN.md`, `design/RUNBOOK.md`.

Method:
- Source was only read, in `/home/ubuntu/psp/build/linux`. Nothing was
  written in either kernel tree.
- The baseline `vmlinux` was disassembled with the tree's own
  `mipsel-linux-uclibc-objdump` inside `psp-build:bullseye`, with
  `/home/ubuntu/psp` mounted **read-only**. The output went to my scratchpad.
- Kernel paths below are relative to `/home/ubuntu/psp/build/linux`.
- "DESIGN:n" and "RUNBOOK:n" are line numbers in the two artifact files as
  they stand on 2026-10-01.
- Anything the source cannot settle is marked **UNVERIFIED**.

---

## Verdict: FAIL

Three scenarios are **BLIND**: IF1 (re-run), IF4 (re-run) and IF5 (new).
They share one root cause, and that root cause was introduced by revision
2's fix for attempt-2 IF4:

- r2 retries a failed flush **in place** in the same segment
  (DESIGN:1623-1636).
- On this kernel, a failed write of a FAT sector leaves that buffer
  "not up to date". Nothing ever writes it again.
- So the cluster link it carried is never on the stick. Records that the
  collector then reports as durable sit in clusters the file system cannot
  reach.
- At the segment's next cluster allocation, vfat reads the stale on-disk
  FAT, finds the file's last cluster marked free, and calls
  `fat_fs_panic`. That sets the whole `/ms0` file system **read-only**
  (`fs/fat/cache.c:255`, `fs/fat/misc.c:30-33`).
- From then on no flush, rotation or new segment can reach the stick for
  the rest of the run.

The design states the opposite: "A burst shorter than the ring span ...
loses nothing, whether it is one long burst or many short ones"
(DESIGN:1652-1657). The RUNBOOK also relies on "macOS can only write into
space the file system shows as free, which excludes the space of every
recording the PSP finished saving" (RUNBOOK:343-347). Under this mechanism
that is false.

Two scenarios are **AMBIGUOUS**, each with a concrete fix:

- **UL5:** a clean LED read-back during a mid-window suspension makes the
  decoder print "H10 refuted". The same suspension falls outside N1's
  `ms_delta = 0` gate.
- **IF6:** a corrupted ring slot or a forward head jump blocks one ring for
  its full span. The drain still counts as "complete", so nothing alarms.

Seventeen are **DIAGNOSABLE**. All three attempt-2 AMBIGUOUS scenarios
(TE4, OE3, OE4) are now DIAGNOSABLE. The name-space part of attempt-2 IF4
is fixed.

| # | Group | Scenario | Attempt 2 | Attempt 3 |
|---|---|---|---|---|
| UL1 | unlisted-shape (H10) | LED RMW writes back bit 4 (ACK line) during a thread suspension at S14 | DIAGNOSABLE | **DIAGNOSABLE** |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off | DIAGNOSABLE | **DIAGNOSABLE** |
| UL3 | unlisted-shape | Link stays one reply behind | DIAGNOSABLE | **DIAGNOSABLE** (N2b) |
| UL4 | unlisted-shape | Valid frames, HOLD bit stuck | DIAGNOSABLE | **DIAGNOSABLE** (N11) |
| UL5 | unlisted-shape (new, H10) | LED operation disturbs the transaction with a clean read-back (read side effect), or N1 while `pscol` writes | – | **AMBIGUOUS** |
| TE1 | timing-edge | Death at 5 s (first WT Nop), 17 s, 36 s | DIAGNOSABLE | **DIAGNOSABLE** |
| TE2 | timing-edge (Nop before `irq_enter`, IRQs off) | Nop on a suspended thread after the I cap is spent | DIAGNOSABLE | **DIAGNOSABLE** |
| TE3 | timing-edge | Minute 14 in `fsync`; 29:50; 16-bit link wrap; console blank | DIAGNOSABLE | **DIAGNOSABLE** |
| TE4 | timing-edge (straddles a watchdog tick; Nop before `irq_enter`) | Slow Nop, nested tick, preemption at outer return, H10 write-back | AMBIGUOUS | **DIAGNOSABLE** |
| TE5 | timing-edge (new; Nop before `irq_enter`, IRQs off; H10) | The Nop lands between the load and the store of an LED read-modify-write | – | **DIAGNOSABLE** (decoder rule recommended) |
| IF1 | instrumentation-fault | Transient stick write failure spanning onset | DIAGNOSABLE | **BLIND** (when the failing flushes allocate a cluster; see IF5) |
| IF2 | instrumentation-fault | Worker killed at minute 13-14 | DIAGNOSABLE | **DIAGNOSABLE** |
| IF3 | instrumentation-fault | `/proc` reader races every writer; head moves backwards | DIAGNOSABLE | **DIAGNOSABLE** |
| IF4 | instrumentation-fault | 25-35 s write-error burst, or about 98 sporadic failing ticks | BLIND | **BLIND** (name space fixed; new cause, IF5) |
| IF5 | instrumentation-fault + observer (new; fault in the collector's own stick I/O) | One failed `fsync` on a flush that allocated a cluster: orphaned "durable" records, then vfat read-only | – | **BLIND** |
| IF6 | instrumentation-fault (new; ring index corrupt) | Corrupt slot `seq` or forward head jump stalls a ring for 114.7 s with no alarm | – | **AMBIGUOUS** |
| OE1 | observer-effect (collector's own stick I/O) | MS driver spins forever with a raised preempt count | DIAGNOSABLE | **DIAGNOSABLE** |
| OE2 | observer-effect | Start-up `statfs` FAT scan | DIAGNOSABLE | **DIAGNOSABLE** |
| OE3 | observer-effect | Collector load sets the H4 exposure (sub-tick start delay) | AMBIGUOUS | **DIAGNOSABLE** |
| OE4 | observer-effect | `pscol` runs with kernel privilege; stray store | AMBIGUOUS | **DIAGNOSABLE** |
| OE5 | observer-effect | Collector exit frees a mousedev client mid-walk | DIAGNOSABLE | **DIAGNOSABLE** |
| OE6 | observer-effect (new) | Stall panel painting at 1 Hz for minutes; 0.2-1 ms IRQs-off stalls on in-flight commands | – | **DIAGNOSABLE** (recording recommended) |

---

## 1. Source facts the scenarios rest on (re-verified by me)

### 1.1 Facts carried over from attempt 2 (re-checked)

| # | Fact | Evidence |
|---|---|---|
| F1 | Timer handler order: Count reset, `localTick++`, the watchdog Nop (IRQs off, before `irq_enter`), UART tick, then `irq_enter`, `do_timer`, `irq_exit`. | `arch/mips/psp/psp.c:348-368`, `:370-380`; recon/syscon §2.3 |
| F2 | `__do_softirq` raises the softirq count before it enables interrupts. | `kernel/softirq.c:217` (`__local_bh_disable`), `:225` (`local_irq_enable()`) |
| F3 | Kernel preemption happens only at an interrupt return with `preempt_count == 0`. | `arch/mips/kernel/entry.S:61-73` |
| F4 | The wake-up hook site is reached only on activation. `schedule()` switches inside `if (likely(prev != next))`. | `kernel/sched.c:1644-1657` (`activate_task` … `success = 1;`), `:3700-3707` |
| F5 | A failing sector is tried 10 times with `mdelay(1)`, two LED read-modify-writes per try. Then the whole bio ends with `-EIO`. | `drivers/block/ms_psp.c:228-236`, `:238-276`, `:304-326` |
| F6 | User processes keep kernel privilege, and user copies are unchecked. | `arch/mips/kernel/process.c:81-83`; `include/asm-mips/uaccess.h:58`, `:107-113` |

### 1.2 New vfat facts behind IF1, IF4 and IF5

| # | Fact | Evidence |
|---|---|---|
| V1 | `fsync` on vfat is `file_fsync`: `write_inode_now`, then `write_super`, then `sync_blockdev`. The FAT sectors are written by `sync_blockdev` as ordinary buffers of the block device. | `fs/fat/file.c:136`; `fs/sync.c:55-76` |
| V2 | A failed asynchronous buffer write clears `BH_Uptodate` and sets `AS_EIO`. The buffer is no longer dirty, so no later sync writes it again. | `fs/buffer.c:429-451` (`clear_buffer_uptodate(bh)` at `:451`) |
| V3 | `sb_bread` of a buffer that is not up to date **re-reads the sector from the stick**. Any in-memory change that failed to write is discarded. | `fs/buffer.c:1378-1384` (`__bread` → `__bread_slow`), `:1179-1193` |
| V4 | Every FAT entry read goes through `sb_bread`: `fat_ent_read`, and the allocator's `fat_ent_read_block`. | `fs/fat/fatent.c:97-103`, `:320`, `:404`, `:460` |
| V5 | Extending a file past its last cluster runs this chain: `__fat_get_block` → `fat_add_cluster` → `fat_alloc_clusters` (search from `prev_free + 1`) → `fat_chain_add`. `fat_chain_add` calls `fat_get_cluster(inode, FAT_ENT_EOF)` to find the last cluster. After allocating, `__fat_get_block` maps the new cluster with `fat_bmap`, which walks the in-memory FAT and adds the new cluster to the inode's cluster cache. | `fs/fat/inode.c:40-52`, `:55-105`; `fs/fat/fatent.c:434-500`; `fs/fat/misc.c:78-110`; `fs/fat/cache.c:217-272` (`fat_cache_add` at `:270`) |
| V6 | `fat_get_cluster` starts from the end of the cached run. If the next FAT entry read is `FAT_ENT_FREE`, it calls `fat_fs_panic(... "invalid cluster chain")` and returns `-EIO`. | `fs/fat/cache.c` `fat_cache_lookup` (returns `fcluster + offset` of the nearest run), `:253-259` |
| V7 | `fat_fs_panic` sets `MS_RDONLY` on the superblock. 2.6.22 vfat has no `errors=` option and no way back short of a remount. | `fs/fat/misc.c:18-35` |
| V8 | On a read-only superblock, `open(O_CREAT)` in `/ms0/PSCLOG` fails with `-EROFS`, and `fat_write_super` stops writing FSINFO. | `fs/namei.c:232-239`; `fs/fat/inode.c:453-458` |
| V9 | FSINFO's next-free hint is written as `prev_free`, the last cluster allocated in memory. | `fs/fat/misc.c:40-72` (`fsinfo->next_cluster = cpu_to_le32(sbi->prev_free)`) |
| V10 | `fat_write_inode` re-reads the directory block and rewrites only size, attributes, start cluster and times of the entry at `i_pos`, **not the name**. | `fs/fat/inode.c:556-600` |
| V11 | Steady-state flushes allocate clusters. Segments are opened `O_WRONLY \| O_CREAT \| O_EXCL` with no preallocation, and the design counts about 0.27 cluster allocations per second. | DESIGN:1464-1466, `:1745-1751` |

---

## 2. Attempt-2 scenarios re-run against revision 2

### UL1 (H10). LED RMW writes back bit 4 during a suspension at S14. DIAGNOSABLE

Sequence: the thread is preempted at tick k inside S14 (`syscon.c:151-156`).
`pscol`'s `fsync` does LED read-modify-writes (`psp.c:399-407`,
`ms_psp.c:312-314`). A CLEAR read returns bit 4. The ACK is lost, and the
thread later returns −4.

What revision 2 records:
- **Tick k, T2a (DESIGN:668).** Not nested, so `lc_epc` = S14 and `lc_r`
  are stored.
- **The LED hook (DESIGN:703-722)** adds `v` to `led_cmd_or` and sets
  `led_cmd_pid` = the worker.
- **S records:** `rd_clr_or & 0x10`, flags b4/b5.
- **P08:** `ret −4`, `ack_polls 1,000,001`, `preempt_delta ≥ 1`,
  `ms_delta ≥ 2`, `led_or & 0x10`, `lc_flags` b0|b2.

Decoder: row H10 (DESIGN:1882) now fires for a suspension step anywhere in
S5..S20. Here the step is S14, so the report gives the S13..S20 window and
the bit. The r2 nested-tick rule means a nested tick can no longer
overwrite `lc` (see TE4).

**Ruling: DIAGNOSABLE.**

### UL2. A foreign frame toggles mouse mode off. DIAGNOSABLE

What is recorded:
- The W record of the interleave.
- The foreign `P08`: `rx[2]` is not 0x08, or `ret 0` with `nwords ≥ 1`.
- That poll's POLL: `pi_flags` b3 = 1 and b4 = 0.
- Later polls: `mouse_flags` b0 = 0.

N10 (DESIGN:1899) names the shape, and step 3 of 10.7 ties the toggle to
the frame that caused it. D7a re-toggles the mouse after death.

**Ruling: DIAGNOSABLE.**

### UL3. Link stays one reply behind. DIAGNOSABLE

N2b (DESIGN:1890) is now a standalone rule: across P + W + M, command n's
`rx[2]` equals command n−1's `cmd`, with `drain = 0`. H6 now requires
`rx[2] = 0x08` and no press-following GetCtrl2-shaped frame elsewhere
(DESIGN:1878). N2b is tested before H6 (10.7 step 5), and Stage 3 has the
sequence (DESIGN:2299).

**Ruling: DIAGNOSABLE.**

### UL4. HOLD stuck on with valid frames. DIAGNOSABLE

N11 (DESIGN:1900) matches:
- persistent `ri_branch = 4`;
- valid, non-zero `P08` frames that follow D3, D4 and D6;
- raw `rx[4]` b5 = 0 through D7, where C0's D7 changed it.

**Ruling: DIAGNOSABLE.**

### TE1. Death at the first WT Nop (about 5 s), at 17 s and at 36 s. DIAGNOSABLE

What is in place:
- Rings are BSS, so the WB record (W seq 0), the boot M record and every
  P/POLL record from the first poll are kept (DESIGN 3.1).
- `durable_next` = 0 means "nothing durable yet", so a promotion before
  the first durable flush still starts at seq 0 and keeps WB
  (DESIGN:547, `:1305-1308`).
- The early-death exception and the 2:00 decision apply (DESIGN 8.3).
- With no healthy template, H8 uses the WB record, the boot M record and
  the pre-onset WT records as its baseline (DESIGN:2575-2583).
- H1, H2, H3, H5, H9 and the H4 trigger are absolute rules.
- H6 and H7 use the source bit map, flagged `no C0 reference`.

**Ruling: DIAGNOSABLE.** (An early death combined with a stick write error
in the start-up catch-up is IF5. The STICK check would then turn red, and
the abort rule at 2:00 sends the run back without using it up.)

### TE2 (Nop before `irq_enter`, IRQs off). Nop on a suspended thread after the I cap is spent. DIAGNOSABLE

The attempt-2 sequence:
1. Sample 0 is taken at S12.
2. Samples 1-3 are taken on another task.
3. The thread resumes and runs to S18.
4. It is preempted at a tick whose I sample is suppressed.
5. At the next tick the WT Nop drains the rest of the reply.

What is recorded:
- T2a of the suppressed tick still stores `lc` = S18 and `lc_r` holding
  `i` and `ptr` (the cap applies only to T2b).
- The W extension has b4 = 0 and b5 = 1, with `lc_epc` = S18.

The decoder reports P6, and the cross-check (−2 with `nwords = j`) agrees.

**Ruling: DIAGNOSABLE.** This still depends on R31: G2 must confirm that
`i` and `ptr` stay in `lc_r` registers.

### TE3. Minute 14 in `fsync`, 29:50, link wrap, console blank. DIAGNOSABLE

- **Minute 14 in `fsync`:** the onset records are drained at the next tick
  and are durable one flush later. D8 holds the operator until both
  displays agree (DESIGN:1544-1567).
- **Field widths:** the u16 fields last 262 s, and the W ring spans
  1,280 s.
- **16-bit P link fields:** they wrap at about 30.6 min. A run of 30:00
  plus D8 (up to 2:15) crosses the wrap once, and nearest-value expansion
  handles one wrap.
- **Console blank at about 600 s:** it exercises N4, which is recorded
  (`pi_flags` b2, `jp_lcd_unblank`). `pscol` redraws over a software
  blank, so the HUD stays readable. If the screen is dark at D8, D8 (c)
  applies, and the decoder recomputes the real loss from the stick.

**Ruling: DIAGNOSABLE**, provided no stick write error occurs (IF5).

### TE4 (straddles a watchdog tick; Nop before `irq_enter`). Slow Nop, nested tick, preemption at the outer return, H10 write-back. DIAGNOSABLE

The sequence, traced through revision 2:

| Tick | What happens | What is stored |
|---|---|---|
| 1250k | The Nop lands with the thread at S14 (P4). The Nop is ACKed late or not at all, taking ≥ 1 tick. | W record: own `ret`/`ack_polls`; ext b4 = 1, b7 = 0; `epc` = S14 |
| 1250k, T2 after the Nop | `nested` is false: the thread was in process context. | T2a stores `lc` = S14 |
| 1250k+1 | Nests inside `__do_softirq`, because IP7 is already pending when `kernel/softirq.c:225` enables interrupts. `current` is still the thread. | `preempt_count & SOFTIRQ_MASK` ≠ 0, so `nested` = 1. T2a skips `lc` and counts `lc_nested`; `lc_nest_id` = this command; the I sample gets flags b5 |
| outer return | The thread is preempted (F3). `pscol` writes; the LED read-backs carry a non-LED bit. | S records, `led_cmd_or` |
| thread resumes | Returns −4. | P08: `wn = 1`, `lc_epc` = S14, `lc_flags` b4, `led_or & ~0xC0 ≠ 0` |

The decoder reports **H4 at P4 + H10 (S13..S20, with the bits)**. This is
the Stage 3 expectation at DESIGN:2296. The nested test reads the
interrupted context's count before this handler's `irq_enter` (T2 sits
before `psp_uart3_txrx_tick`; recon §2.3 puts `irq_enter` after both).

I tried to break it through the window in `preempt_schedule_irq` between
`local_irq_enable()` and `spin_lock_irq(&rq->lock)`. There,
`preempt_count` = `PREEMPT_ACTIVE` and is not masked by the nested test,
so a tick in that window would overwrite `lc` with an EPC in `schedule`.
For that tick to arrive inside a window of a few dozen instructions right
after a tick return, the preceding handler would have to last a whole
tick. A handler that long leaves IP7 pending, and IP7 is always taken
first inside that handler's own `__do_softirq` (the timer softirq is
raised every tick). So the window cannot be reached in practice, and a
miss would show as `lc_flags` b2 = 0, which R34 makes the decoder report.

**Ruling: DIAGNOSABLE.**

### IF1. Transient stick write failure spanning onset. BLIND (under the conditions in IF5)

Revision 2's path for this error (DESIGN:1623-1636):
1. Count the error and turn the `MS` line red.
2. Rewind each ring to `durable_next`.
3. Keep `seg_end` where it is, and write the next flush over the failed
   one at the same offset.

Take a 3 s outage spanning onset: about 13 failing collector ticks
(UNVERIFIED tick length during errors).

- **The backlog grows.** Each tick re-reads from `durable_next`, with a
  per-ring cap of `cap_r × m` and m = 2 at Δt ≈ 0.25-0.35 s. That is up to
  96 P records against about 8 new ones per tick, so each retry is longer
  than the one before. After about 13 ticks the retry flush is about
  18 KB.
- **A cluster is allocated during the outage.** The extent
  `[seg_end, seg_end + 18 KB)` crosses a cluster boundary with probability
  of about 0.56 at 32 KB clusters (cluster size UNVERIFIED, DESIGN:1749).
  When it crosses, the `write()` allocates cluster C (V5). That puts the
  links B→C and C=EOF into the cached FAT sector, and the outage makes
  that sector's write fail (V2).
- **After the outage.** The in-place retry rewrites the same file range.
  Those blocks are already mapped, so nothing is allocated and the FAT
  sector is not dirtied again. The data, the directory entry and FSINFO
  are written; the FAT link is not. `fsync` returns 0.
  - The collector advances `durable_next` and `durable_tick`.
  - The panel goes away; the `MS` line stays red for 10 s.
  - **The onset records are now on the stick but in cluster C, which the
    on-disk FAT does not link** (FAT[B] = EOF, FAT[C] = free).
- **Within one cluster** (about 2-5 s at 1.5-4.5 KB per flush), the next
  allocation hits V6: `fat_fs_panic`, and `/ms0` becomes read-only (V7).
  The post-death script D1-D7 (about 100 s) is therefore never written
  (IF5 trace).

What the analyst gets:
- `PSCLOG` holds the segment only up to cluster B. A Mac read of a file
  whose size field is larger than its FAT chain gives a truncated file or
  an I/O error (UNVERIFIED).
- The onset window and everything after it are missing.
- The onset records survive only as orphaned clusters, which the
  *optional* raw image (RUNBOOK:320) can find by chunk magic, unless the
  Mac has already written over them (IF5, step 7).
- The post-death script exists only in panel photographs.

S2 (window after onset) and S4 fail, and H6 against H7 cannot be decided.

If the outage happens not to straddle an allocation, IF1 is DIAGNOSABLE
as in attempt 2. The design gives no way to avoid the straddle and no way
to detect it.

**Ruling: BLIND** in the allocating case. Fix: IF5.

### IF2. Worker killed at minute 13-14. DIAGNOSABLE

- The pre-spawned standby takes over within about 2 s, with no allocation.
- It opens `seg_cur + 1` (O_EXCL, monotonic) and seeks every ring to
  `durable_next`. The attempt-2 seq-0 defect is fixed (DESIGN:547,
  `:2853`).
- EVENT chunks record the promotion.

**Ruling: DIAGNOSABLE.**

### IF3. `/proc` reader races every writer; head moves backwards. DIAGNOSABLE

The protections are unchanged:
- the seq invalidate-and-publish writer, with `seq` checked before and
  after the copy (DESIGN 3.4, 3.5);
- `total_counts` read high-low-high;
- `head_regress` with an EVENT and a resync.

The r2 additions (`wk_*`, `lc_nest_id`, `md_*`) each have one writer or
are bracketed by `wk_seq` (DESIGN:1116-1123).

**Ruling: DIAGNOSABLE.** A *forward* jump of a head, and a corrupt slot
`seq`, are a separate gap: IF6.

### IF4. 25-35 s write-error burst, or about 98 sporadic failing ticks. BLIND (new cause)

**The attempt-2 cause is fixed.** Names are `T<rrr><iiii>` (9,999 per run).
A new segment is opened only after three consecutive failures, at most once
per 5 s. Exhaustion means "keep writing" (DESIGN:1460-1484).

**The same error pattern still ends the stick stream:**

- **Contiguous 25-35 s burst.**
  1. The retry flushes grow to the cap (22-44 KB), so cluster allocations
     certainly happen inside the burst. Their FAT sectors fail (V2).
  2. If a second allocation happens inside the burst, it already panics
     (V6): the allocator re-reads the stale sector, and the chain walk
     reads FAT[C] = free.
  3. Rotations inside the burst (one every 5 s) each create a file. The
     directory block holding the new entry is dirtied, and its write
     fails. So does the first cluster's FAT sector.
  4. After the stick recovers, `fat_write_inode` rewrites size and start
     cluster into a re-read directory block but **not the name** (V10).
     The new segment's entry may be missing from the directory
     (UNVERIFIED how the Mac shows a slot with no name).
  5. Whichever segment is live, its next allocation panics, and `/ms0`
     is read-only (V7). Rotation then gets `-EROFS` (V8). The design's
     rule "stay in the current segment, retry no sooner than 5 s later"
     (DESIGN:1479-1484, `:1658-1660`) loops for the rest of the run.
- **About 98 sporadic single-tick failures.** Each failing tick whose
  flush allocated (about 7% at a 2.2 KB average flush and 32 KB clusters)
  leaves a stale FAT sector if the outage covered the FAT write. With 98
  such ticks, P(at least one) ≈ 1 − 0.93^98 > 0.99.

The worker keeps reading the rings, so `last_reader_tick` advances and the
stall takeover never fires. That is correct, since a new worker writes to
the same read-only file system. The kernel panel shows `DUR` rising, but
nothing on it says "read-only".

The Stage 3 tests at DESIGN:2294 simulate the file, so they cannot reveal
this. They would pass while the device fails.

**Ruling: BLIND** for any death after the read-only point. Fix: IF5.

### OE1 (fault in the collector's own stick I/O). MS driver hang with a raised preempt count. DIAGNOSABLE

- The in-progress marker (DESIGN 2.4) and the panel are painted from the
  timer interrupt (DESIGN 2.10), which keeps running.
- The panel shows the running task's EPC, `preempt_count > 0`, the sector,
  the pid and the frozen `jp_loop`.
- The decoder labels it "Memory Stick driver hang (instrumentation
  exposure)" (DESIGN:2681-2686).

**Ruling: DIAGNOSABLE.** The residual (the run is spent) was accepted as
J17.

### OE2. Start-up `statfs` FAT scan. DIAGNOSABLE

There is no `statfs` on the device. `fat_count_free_clusters` has no other
caller (DESIGN:1494-1510). The first allocation's scan from the FSINFO
hint is recorded as S read records in the first catch-up.

**Ruling: DIAGNOSABLE.**

### OE3. Collector load sets the H4 exposure through sub-tick start delays. DIAGNOSABLE

The scheduler hooks of DESIGN 2.11 sit at verified sites:
- `try_to_wake_up` immediately before `success = 1`
  (`kernel/sched.c:1657`), reached only after `activate_task` (`:1644`);
- `schedule()` inside `prev != next` (`:3700-3707`).

They measure every wake-up-to-switch-in delay of the thread at Count
resolution and charge it to the class of each `prev`. POLL carries
`wk_delay`, `wk_cls` and `wk_share`, and stats carry `wk_acc[8]`. The
decoder attributes every late-start poll, `pscol` first
(DESIGN:2657-2673).

One note, not a defect: the thread sleeps in `msleep`, which is
`TASK_UNINTERRUPTIBLE`, so its wake-up is marked `SLEEP_NONINTERACTIVE`
(`kernel/sched.c:1626-1632`). `pscol` sleeps in `nanosleep`, which is
interruptible. So `pscol` can hold a better dynamic priority than the
thread and preempt it on waking. That raises the rate of mid-transaction
suspensions while `pscol` writes (the UL1/UL5 overlap). It is recorded
(`preempt_delta`, `lc`, `wait_*`, `wk_*`).

**Ruling: DIAGNOSABLE.**

### OE4. `pscol` runs with kernel privilege; a stray store. DIAGNOSABLE

What r2 adds:
- guards and a stack high-water check in every `pscol` process, with exit
  on a violation (DESIGN:1242-1266);
- kernel guard words checked at 1 Hz (DESIGN:1047-1056);
- ASan/UBSan fuzzing in Stage 3 (DESIGN:2298);
- the decoder's `instrumentation-suspect` label;
- R33 (DESIGN:2728), which states the undetectable residual (a store
  straight to GPIO) and requires the report to list it beside any
  unexplained frame with `wn = 0`, `ms_delta = 0` and no S overlap.

That meets S5's "know precisely how it might have".

**Ruling: DIAGNOSABLE.** A corrupted ring slot is not caught by the guards;
that is IF6.

### OE5. Collector exit frees a mousedev client while the thread walks the list. DIAGNOSABLE

What r2 adds:
- `md_open`, `md_release`, `md_last_pid` and `md_last_tick`
  (stats 210-213);
- the `do_exit` hook that clears `psc_jp_task` and stamps `jp_exit_tick`
  (DESIGN:786-792).

The decoder annotates a thread stop within 1 s of a collector exit
(DESIGN:2602-2604).

**Ruling: DIAGNOSABLE.**

---

## 3. New scenarios

### IF5. One failed `fsync` on a flush that allocated a cluster: "durable" records orphaned, then `/ms0` read-only (fault in the collector's own stick I/O). BLIND

**Shape.** The stick refuses writes for about one collector tick
(UNVERIFIED cause: a contact glitch from 30 minutes of grip pressure, a
card-internal stall reported as an error, or a weak block; no error
appears in the recovered `kmsg.txt`). This is the mildest error the design
plans for: "A transient error therefore costs one tick and no new file"
(DESIGN:1635-1636). The failing tick's flush happens to cross a cluster
boundary. About 7% of nominal flushes do, more during any catch-up (V11).

**Timeline, traced through the kernel.** Let B be the segment's last
cluster on disk (FAT[B] = EOF) and `seg_end` lie near B's end.

1. **Tick t0, `write()`.** The flush extends past B, so `__fat_get_block`
   → `fat_add_cluster` (`fs/fat/inode.c:84-87`, `:40-52`):
   - `fat_alloc_clusters` takes C (= `prev_free + 1`), sets FAT[C] = EOF
     in the cached FAT sector and marks it dirty (`fs/fat/fatent.c:455-479`,
     `:184`).
   - `fat_chain_add` sets FAT[B] = C (`fs/fat/misc.c:100-110`, the write
     at `:107`).
   - The second `fat_bmap` maps C and extends the inode's cluster cache
     run to C (`fs/fat/inode.c:94-97`, `fs/fat/cache.c:270`).
2. **Tick t0, `fsync`.** The data, then (V1) the directory entry, FSINFO
   and the FAT sector plus its mirror all go to `psp_ms_make_request`,
   which ends each bio with `-EIO` (`drivers/block/ms_psp.c:228-276`).
   - `end_buffer_async_write` clears `BH_Uptodate` on the FAT sector
     (`fs/buffer.c:451`).
   - `fsync` returns `-EIO`.
   - The collector counts it, turns `MS` red, writes an EVENT "rewind",
     rewinds the rings and keeps `seg_end` (DESIGN:1623-1636).
3. **Tick t1, the stick works again.** `lseek(seg_end)` and the retry
   `write()` land on already-mapped blocks below `mmu_private`, so nothing
   is allocated and the FAT sector is not dirtied again. `fsync` returns 0
   and writes:
   - the data into C;
   - the directory entry (`fat_write_inode` re-reads its block and writes
     the new size, V3, V10);
   - FSINFO with `next_cluster` = C (V9).

   It does **not** write the FAT sector, which is clean and not up to
   date. **On disk: FAT[B] = EOF, FAT[C] = free.**
4. **The collector's view after t1.** It advances `durable_next`, writes
   `ctl` op 1 and `durable_tick` advances. The kernel panel goes away, or
   never appeared (`DUR` stayed under 3 s). The `MS` line is red for 10 s.
   **The records of t0 and t1 are reported durable, and every later flush
   into C will be too. None of them is reachable through the file
   system.**
5. **Tick tk, the flush leaves C** (one cluster later, about 7-20 nominal
   flushes, 2-5 s). The chain runs `fat_add_cluster` →
   `fat_alloc_clusters`:
   - It reads the FAT sector through `sb_bread`. The buffer is not up to
     date, so the sector is re-read from the stick (V3, V4) and shows
     FAT[C] = free.
   - It allocates C+1.
   - `fat_chain_add` → `fat_get_cluster(inode, FAT_ENT_EOF)`. The cache
     lookup returns the end of the run, (n, C). Reading FAT[C] gives
     `FAT_ENT_FREE`, so `fat_fs_panic("invalid cluster chain")` runs
     (`fs/fat/cache.c:253-259`).
   - **`/ms0` is now `MS_RDONLY`** (`fs/fat/misc.c:30-33`). The function
     returns `-EIO`, and `fat_add_cluster` frees C+1.
   - The `write()` is short, so the collector rewinds and retries. Every
     retry needs a new cluster and fails the same way.
6. **From then on.**
   - After three failures, rotation calls `open(O_CREAT|O_EXCL)`, which
     returns `-EROFS` (`fs/namei.c:236-239`). The worker "stays in the
     current segment and tries again no sooner than 5 s later"
     (DESIGN:1658-1660), for the rest of the run.
   - `durable_tick` stops. The kernel panel appears 3 s later with `DUR`
     rising and stays up until the pull.
   - The KMSG lines "FAT: Filesystem panic ... File system has been set
     read-only" are read by the worker but can never be written.
   - Neither the panel nor the HUD says "read-only". The HUD shows only
     `MS` red, the error count and `last_errno` in UHB, which also never
     reaches the stick.
   - The stall takeover does not fire, correctly (reads continue). A new
     segment cannot be created anyway.
7. **At the Mac** (RUNBOOK E1, `:310-318`). `PSCLOG/T…0003.BIN` reaches
   only cluster B. Its size field is larger than its chain, so the copy is
   truncated or fails with an I/O error (macOS behaviour UNVERIFIED).
   - The records from t0 to tk exist only as orphaned clusters C….
   - On disk these clusters are **free**, and FSINFO's next-free hint
     points at C (V9). That is exactly where a FAT allocator on the Mac
     starts writing: `.fseventsd`, `.Spotlight-V100` and similar files on
     a writable mount (UNVERIFIED).
   - RUNBOOK:343-347 tells the operator the opposite: that the Mac cannot
     overwrite finished recordings. The raw image is optional (E2) and is
     taken *after* the mount.

**What the run then holds for a death at any time after tk** (say t0 at
9:00 and onset at 14:00):
- The stick has nothing after the last pre-t0 durable flush.
- The rings hold only the last 114.7 s at the pull.
- The evidence is the panel photographs: a 1 Hz point sample of the last
  P08, the last W record, the thread's stage and `lc_epc`, but only at the
  moments the operator photographed (RUNBOOK C4 asks for one every
  5 minutes before death, then one per D step).
- There is no raw window before, across and after onset (**S2 fails**), no
  W extension, I, S or POLL history (**S4 fails**), and no recorded
  post-death script (H6 against H7 cannot be decided).

**Death between t0 and tk:** the onset records are "durable" but orphaned.
The read-only point follows within seconds, so the post-death script is
lost as in IF1.

**Why the design cannot see it:**
- The design's model of an error is "a failed page write is not retried
  by later syncs" (DESIGN:1623-1626). It applies that to file data and
  answers it by rewriting the data. A failed **FAT** sector has the same
  property, but the collector never rewrites it, because it never touches
  the FAT directly.
- 4.4 says "Every byte below `seg_end` belongs to a flush whose `write`
  and `fsync` succeeded" (DESIGN:1486-1490). That is true, but not enough:
  `fsync` succeeding on a retry does not make an earlier failed metadata
  write durable.
- Revision 1 opened a new file after every error and never extended the
  failed file again, so it did not reach V6. **The r2 fix for attempt-2
  IF4 created this path.**

**Ruling: BLIND.**

**Fix needed** (any one of 1a or 1b, plus 2 to 4):
1. Never extend a file across a failed metadata write.
   - **(a) Preferred: preallocate segments.** Create each segment at a
     fixed size, for example 4 MB (about 7.5 minutes at 8.9 KB/s), by
     writing PAD chunks and calling `fsync`. Confirm success (`fstat`
     size, and a read-back of the last sector) before using it. Steady-
     state flushes then overwrite already-linked clusters, so no FAT
     sector is ever dirtied during the run except when a segment is
     created. In-place retries are then safe: data sectors only, plus the
     directory entry and FSINFO, which `fat_write_inode` and
     `fat_clusters_flush` rebuild from re-read blocks (V3, V10).
     - Create the next segment ahead of need, when the current one is
       half full.
     - If any error occurs while creating a segment, abandon that file
       (never extend it) and create another.
     - The decoder already skips PAD.
   - **(b) Or abandon a segment after any failed `fsync`.** Never extend
     that file again, and treat everything written to it after the error
     as **not** durable: keep `durable_next` at its pre-error value until
     a flush in a *new* segment succeeds. The new segment must be created
     only after the outage ends (one creation per burst, rate-limited as
     now).
2. **Make the read-only state visible.**
   - The kernel adds a stats bit for `MS_RDONLY` on the `/ms0`
     superblock, and a counter incremented in `fat_fs_panic`
     (`fs/fat/misc.c:18`).
   - The kernel panel's first line shows `MS RO`.
   - The runbook says that from then on the panel photographs are the
     only record.
3. **RUNBOOK E.**
   - If the HUD ever showed `MS` red, a rotation, or a panel outside the
     self-test, or if `PSCLOG` copies short: image the stick **before**
     mounting it read-write, or mount it read-only
     (`diskutil mount readOnly`). Make the raw image mandatory in that
     case.
   - Correct the claim at RUNBOOK:343-347.
   - Make `--raw` the decoder's primary path whenever an EVENT "rewind"
     exists.
4. **Stage 3** must exercise the error path against this tree's
   2.6.22 vfat code (for example `fs/fat` built into a host harness or a
   UML/qemu build, with a fault-injecting block device), not against a
   simulated file. It must check:
   - after an outage covering a cluster allocation, the copied file
     contains every record the collector reported durable;
   - `/ms0` stays writable.

### IF6. A corrupted slot `seq` or a forward head jump stalls a ring for its full span, with no alarm (ring index corrupt). AMBIGUOUS

**Shape.** A stray store (the OE4 residual, R33, or a Stage 2 bug) changes
the `seq` word of one P slot holding record s (head − N ≤ s < head) to any
value other than s. Or it moves the P head forward. The design leaves
mid-ring corruption to "the seq checks (3.5) and `head_regress`"
(DESIGN:1054-1056).

**Trace under the reader protocol (DESIGN:1142-1161).**
- The reader reaches s. Step 1 holds (s < head) and step 2 holds
  (head − s ≤ N). Step 3 reads `seq` ≠ s, so the record is "not
  delivered".
- The protocol does not say whether `f_pos` then moves past s.
  - The natural implementation of "returns whole records only ... and
    advances `f_pos` past what it returned" (DESIGN:822) stops at s and
    returns what it has.
  - Every later read starts at s again and returns 0 records, until the
    writer has written N more records (4,096 P = **114.7 s**). Only then
    does step 2 skip forward.
- For a forward head jump, step 2 skips to `head − N`. Those slots still
  hold old seqs, so the same stall follows.
- **Meanwhile:**
  - The P drain returns fewer records than asked, which DESIGN:1331-1333
    defines as **complete**. So `durable_tick` advances, the panel stays
    off, `CATCHUP` stays off, and D8 can pass.
  - Only UHB `lag_max` (DESIGN:2416) and the HUD's frozen `REC P` count
    show it.
  - After 114.7 s the block's `lost` count is about 4,096.

**What a death in that window leaves:** POLL (`ri_branch`), W, I, S and
the per-second `hist` counters, but **no raw `P08`/`P33` frames**. The rows
H2, H3, H5, H6, N2, N2b, N3 and N11 need `rx`, and the H4 P-point
cross-check needs the thread's result. They become unassessable, and S2 is
lost for the syscon traffic.

**Ruling: AMBIGUOUS.** Some data survives, and the stall is visible
afterwards in `lag_max`.

**Fix needed.**
- In 3.5, any slot whose `seq` is not s, with head − s ≤ N, means record s
  cannot be recovered. That covers a value of s+N, `0xFFFFFFFF`, or
  garbage. The reader skips it, advances `f_pos`, counts a new
  `slot_bad[ring]` in stats, and continues.
- A drain is "complete" only if every ring's next `seq` equals its head
  as read from stats, not merely "fewer records than asked".
- The collector writes an EVENT and turns `REC` red on any `slot_bad`
  or `lost`.
- Stage 3 adds a test with a corrupted mid-ring `seq` and a forward head
  jump.

### UL5 (H10). An LED operation disturbs a transaction with a clean read-back, or the thread is suspended mid-window (N1) while `pscol` writes. AMBIGUOUS

**Shape.** The thread is preempted at S14 (G3 high) by the worker, which
does Memory Stick I/O; OE3 explains why that preemption is likely. The
LED read-modify-writes read back only LED bits
(`led_or & ~0xC0 = 0`). The ACK is lost and the command returns −4. Input
then stays dead (persistent state H1 or N2b).

Two physical causes fit the records exactly:
- **(i) N1.** The syscon gives up on a request held high for that long.
- **(ii) An LED register access has an effect not visible in the
  read-back.** Recon §4.2 proves no GPIO read free of side effects; for
  example, a read of `0xbe24000c` could clear the latched GPIO4 status.

**What is recorded.**
- `P08`: `ret −4`, `ack_polls 1,000,001`, `wn = 0`, `preempt_delta ≥ 1`,
  `lc_epc` = S14, `ms_delta ≥ 2`, `ms_b3 = 0`, `led_or ⊆ 0xC0`,
  `led_pid` = worker.
- An S record overlapping the command, with b4/b5 and clean OR/AND.
- I samples with `current` = worker.

**Decoder (DESIGN:1882, `:1888`, `:2637-2641`).**
- H10 needs `led_or & ~0xC0 ≠ 0`: no match.
- N1 needs `ms_delta = 0` ("no Nop and no LED activity"): no match.
- H4 needs a W record: no match.
- H10b needs no command in flight: no match.
- **The trigger is "none".**
- Worse, this very overlap meets the refutation rule ("at least one LED
  operation ... while the thread was suspended at S13..S20 with
  `led_or & ~0xC0 = 0`"). So REPORT.md prints **"H10 refuted on this
  hardware"** for the run in which the death followed exactly such an
  overlap.
- The raw ±30 s window still contains the S record, so an analyst can see
  it.

**Ruling: AMBIGUOUS.**

**Fix needed.**
1. Narrow the refutation wording to "the set/clear registers do not read
   back the transaction's lines (H10's write-back mechanism refuted)".
   Never print it for a run whose onset command itself had
   `ms_delta > 0` during a suspension in S5..S20.
2. Replace N1's `ms_delta = 0` gate with a discriminator. Add a trigger row
   "**N1m**: suspended in S5..S20 while LED operations ran with a clean
   read-back: N1, or an LED effect not visible in the read-back; these
   cannot be separated in this run". Report the suspension length
   (`lc_tick` to resume) and the LED count.
3. Pre-register, as in 7.3, a whole-run comparison of the harm rate of
   mid-window suspensions **with** LED operations against those
   **without**. Both counts are already in the SC records
   (`preempt_delta`, `lc` step, `ms_delta`).
4. Add the sequence to Stage 3.

### TE5 (straddles a watchdog tick; Nop before `irq_enter` with IRQs off; H10). The Nop lands between the load and the store of an LED read-modify-write. DIAGNOSABLE

**Shape.**
1. The thread is suspended at S14 (G3 high).
2. `pscol`'s LED-on path executes `v = PSP_GPIO_SET` (DESIGN:703-705;
   [OBJ] recon §2.2 `lw/or/sw`). The Memory Stick path runs with IRQs
   **on** (recon §2.2), so watchdog tick 1250k is taken between the `lw`
   and the `sw`.
3. The Nop runs before `irq_enter` with IRQs off, on `pscol`'s stack. It
   drops G3 (S6), raises it (S13) and drops it (S20). The thread's
   transaction is broken: P4 or P5a.
4. `pscol` resumes and stores `v | 0x40`. If `v` was read with bit 3 set
   (the SET register reads back the latch while the thread held G3 high,
   a hardware unknown), this store **raises G3 again after the Nop**. The
   result is a spurious request while the thread is still suspended.

**What is recorded.**
- **W record:** ext b4 = 0, b5 = 1 (the `lc` block is valid), b6 =
  transfer in progress. `cur_pcnt ≥ 1`. `epc` is inside `psp_led_ctrl`
  between the load and the store (DESIGN 10.6 labels `psp_gpio_set`).
  `gpr` holds `v` in the register the load targeted.
- **W extension `lc_epc`:** S14, so the decoder reports P4 or P5a.
- **Then:** `psc_note_led` runs after the store and adds `v` into
  `led_cmd_or`.
- **`P08`:** `wn = 1`, `led_or & 0x08`, `lc_epc` = S14.
- **S record:** b2 set.

**Decoder.** H4 at P4/P5a plus H10 (bit 3, S13..S20). The order "read
before the Nop, write after it" is not stated by any rule, but it is in
the W record (EPC label plus `gpr`). The run-wide probability is tiny:
the window is a few cycles per LED operation, about 53 operations per
second, against one Nop every 5 s.

**Ruling: DIAGNOSABLE.**

**Recommended.**
- A decoder rule: "W `epc` inside `psp_gpio_set`/`psp_gpio_clear` between
  the load and the store: the Nop split an LED read-modify-write". Report
  the pre-Nop `v` from the register map, and name the G3 transition it
  caused.
- A Stage 3 vector for it.

### OE6. The stall panel paints at 1 Hz for minutes; each paint stalls an in-flight command for 0.2-1 ms with IRQs off. DIAGNOSABLE

**Shape.** The panel paints in the timer interrupt, with IRQs off, for an
estimated 0.2-1 ms (UNVERIFIED), at every tick ≡ 125 mod 250 while the
collector is behind (DESIGN 2.10, `:889-898`).
- After any long stall, catch-up or error run, and for the whole rest of
  the run after IF5's read-only point, that is once a second for minutes.
- A thread command is in flight at a given tick with probability of
  roughly 1-7% (command durations UNVERIFIED). So tens of paints land
  inside a transaction.
- Each paint holds the thread at its step (for example S14) for up to
  1 ms longer than any normal tick. That is an interrupt-level stall: no
  preemption, so `preempt_delta = 0`, and no Nop, so `wn = 0`. N1
  therefore does not name it.
- The decoder's only safeguard is "flag any onset within 1 s after a
  paint" (DESIGN:1929). When paints happen every second, every onset is
  within 1 s of a paint, so the flag carries no information.

**What is recorded.**
- An I record at that tick (a tick ≡ 125 mod 250, known by construction),
  with the thread's step.
- The SC record's `c_out − c_in` stretched by the paint.
- `panel_paints`, `panel_last_tick` (stats, 1 Hz) and `panel_cost_max`.

There is no per-paint cost and no I-record flag for "painted at this
tick", but the paint ticks are fixed by construction.

**Ruling: DIAGNOSABLE.** An analyst can match onset commands to paint
ticks and steps.

**Recommended.**
- I-record `flags` b6 = "panel painted at this tick", plus the paint's own
  Count cost in that I record.
- A decoder trigger row "N1p: a paint tick landed in S5..S20 of the onset
  command".
- Replace the 1-second proximity flag with this exact test.

---

## 4. Attacks attempted and discarded (not scenarios)

| Attack | Why it fails |
|---|---|
| Kernel stack overflow, from instrumentation code running in IRQ context on arbitrary tasks' stacks | `THREAD_SIZE` is 8 KB (`include/asm-mips/thread_info.h:67,82`; `.config:100`). Frame sizes from the baseline objdump: `do_fsync` 40, `write_cache_pages` 144, `__block_write_full_page` 56, `submit_bio` 96, `generic_make_request` 80, `psp_ms_make_request` 88, `pspMsWriteSector` 24, `plat_irq_dispatch` 24, `irq_exit` 24, `__do_softirq` 48, `run_timer_softirq` 72, `try_to_wake_up` 56, `Syscon_cmd` 48 bytes. The deepest path (MS write + softirq + nested tick + Nop, two `pt_regs`) totals about 2 KB, so a few hundred added bytes leave more than 5 KB of margin. Still, G2 should state the added frame sizes. |
| `pspClearDcache` from the panel discarding dirty data | It is cache op 0x14 over all lines (`arch/mips/psp/ipl_sdk/cache.c:22-37`), the same routine `pspfb_sync` runs on every HUD row write. It writes back, otherwise telem's display would not work. Its unlisted `t0`/`t1` clobbers are harmless across a call. |
| Two `/proc/kmsg` readers racing (`fs/proc/kmsg.c:36-44`), leaving one blocked | Only one worker has it open at a time. A worker blocked in the MS path exits on SIGTERM before its next syscall. |
| `s_psp_ms_rw_sem` contended inside `__bio_kmap_atomic` (sleeping while atomic) | On a uniprocessor the holder cannot be preempted inside the atomic region, so no second task can reach the semaphore while it is held. |
| Nested-tick test missing a tick inside `preempt_schedule_irq` | Not reachable in practice; see TE4. |

---

## 5. Fixes required to pass (consolidated)

1. **IF5, which also closes IF1 and IF4.** Fix 1a or 1b, plus fixes 2-4
   under IF5:
   - stop extending a file after a failed metadata write, preferably by
     preallocating segments;
   - make vfat's read-only state visible on the panel;
   - make the raw image mandatory, and avoid a read-write mount, after
     any write error;
   - test against the tree's own vfat code.
2. **IF6.** Define "skip and count" for a slot whose `seq` does not
   match, and define "complete drain" as reaching the head.
3. **UL5.** Narrow the H10 refutation wording, add N1m, and pre-register
   the with/without-LED harm-rate comparison.

The recommendations under TE5 and OE6 are not blocking.

## 6. UNVERIFIED items this report depends on

1. Whether Memory Stick write errors occur in this setup, in any burst
   shape (IF1, IF4, IF5). None appear in the recovered `kmsg.txt`. The
   premise is the same as attempt-2 IF4, which the design accepted as in
   scope (DESIGN:2844).
2. The cluster size of the 124.8 GB FAT32 stick (32 KB assumed, as in
   DESIGN:1749). It sets the per-tick probability that a flush allocates.
3. How macOS presents a FAT file whose size is larger than its cluster
   chain, a directory slot with no name, and whether it writes into free
   clusters at the FSINFO hint on mount.
4. Whether an LED register read has a side effect (UL5 (ii)).
5. The panel's paint cost (OE6), and command durations.
6. Whether a stray store into a ring slot is possible in practice (IF6).
   The design itself lists it as a residual (DESIGN:1054-1056, R33).
