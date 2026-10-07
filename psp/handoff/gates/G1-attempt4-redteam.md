# Gate G1, attempt 4: red team report

Artifact under review: `design/DESIGN.md` and `design/RUNBOOK.md`, revision 3
(2026-10-01, round 4 authorised by the human after the attempt-3 FAIL).
Reviewer role: G1 red team, attempt 4. Fresh context. I did not write the
design or any earlier gate report.
Date: 2026-10-01.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding, 9.6 included), `WORKFLOW.md`, `recon/syscon.md`,
`recon/input.md`, `recon/build.md`, `recon/image2008.md`, `gates/LOG.md`,
`gates/G1-attempt3-review.md`, `gates/G1-attempt3-redteam.md`,
`gates/G1-attempt1-redteam.md`, `gates/G1-attempt2-redteam.md`,
`design/DESIGN.md` (1,856 lines), `design/RUNBOOK.md` (443 lines).

Method:
- Source was only read, in `/home/ubuntu/psp/build/linux`. Nothing was
  written in either kernel tree. Every vfat and block-layer claim below was
  checked in this tree's own `fs/fat`, `fs/buffer.c`, `fs/sync.c`,
  `fs/fs-writeback.c`, `mm/filemap.c`, `mm/truncate.c`, `fs/drop_caches.c`.
- No disassembly was needed: every claim I rely on is settled by source.
- A small Monte Carlo of the r3 segment logic (4.4/4.6) was run in my
  scratchpad. Its model is stated in Appendix A, so the result can be
  reproduced without the script.
- Kernel paths are relative to `/home/ubuntu/psp/build/linux`.
  "DESIGN:n" and "RUNBOOK:n" are line numbers in the artifact as it stands
  on 2026-10-01.
- Anything the source cannot settle is marked **UNVERIFIED**.

---

## Verdict: FAIL

The round-4 fix works for the failure it was aimed at. A failed `fsync`
can no longer orphan records or turn `/ms0` read-only. Attempt-3 IF1 and
IF5 are now DIAGNOSABLE, and so are IF6 and UL5. I checked the claim
"a segment in use never dirties a FAT sector" line by line in this tree,
and it holds.

The preallocation path has opened a new class of failure. The design's
error model assumes a write failure is one of two kinds:

- **transient**, which the in-place retry absorbs; or
- **local to one segment's data**, which a switch to the spare escapes.

Three scenarios break that model, and all three are **BLIND**:

| # | What happens | Why the design loses the data |
|---|---|---|
| **IF4** (re-run, sporadic variant) | Attempt-3's "about 98 sporadic failing ticks" | Each 2 MB creation needs 256 consecutive good ticks, and any failure abandons it. On a stick in the slow half of the design's own speed range, holds outlast the 114.7 s ring span again and again. Simulated mean loss per 30 min: 12 min at 52 KB/s, 2 min at 100 KB/s. |
| **IF7** (new) | The FSINFO sector, or the PSCLOG directory sector, refuses writes persistently. Data sectors still write fine. | Every `fsync` returns `-EIO`. The in-place retry then overwrites the same region every tick with the same oldest records. Data that did reach the stick is destroyed. The switch and every new creation hit the same shared sector. |
| **IF8** (new) | The FAT sector at the allocator's position refuses writes persistently. | Every creation attempt is abandoned. Each attempt moves the allocator forward by one cluster, 10 s apart, so up to 128 attempts (about 21 min) pass before creation can succeed. Meanwhile the active segment fills and holds, and the rings overflow. |

Two scenarios are **AMBIGUOUS**:

- **A1-OE3, reopened by the cut of T2c and the I ring (K10, K11).** No
  mechanism now records who held the CPU while the thread was **preempted
  mid-command**. K12 records wake-ups only (DESIGN:663-664). An N1 onset
  with no Memory Stick I/O has no recorded actor, so S5 cannot say whether
  the collector caused it.
- **TE6 (new).** The first durable flush waits for a whole 2 MB segment to
  be created. On a stick slower than about 21-27 KB/s, the boot-time P and
  POLL records of an early death (dossier 9.6: before 36 s) are overwritten
  before the first drain.

Everything else is **DIAGNOSABLE**: 19 of the 22 attempt-3 scenarios, plus
the new OE7 and UL6.

**One design change closes IF4, TE6 and most of IF7/IF8.** Durability
would be judged from the data sectors, not from the global `fsync` return
code, and capacity would grow step by step instead of all-or-nothing. The
fixes are in section 6. A simulation of them is in Appendix A: zero loss
at 25-100 KB/s under the IF4 pattern.

| # | Group | Scenario | Attempt 3 | Attempt 4 |
|---|---|---|---|---|
| UL1 | unlisted-shape (H10) | LED RMW writes back bit 4 during a suspension at S14 | DIAGNOSABLE | **DIAGNOSABLE** |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off | DIAGNOSABLE | **DIAGNOSABLE** |
| UL3 | unlisted-shape | Link stays one reply behind | DIAGNOSABLE | **DIAGNOSABLE** |
| UL4 | unlisted-shape | Valid frames, HOLD bit stuck | DIAGNOSABLE | **DIAGNOSABLE** |
| UL5 | unlisted-shape (H10) | LED op disturbs a suspended transaction with a clean read-back | AMBIGUOUS | **DIAGNOSABLE** (N1m) |
| TE1 | timing-edge | Death at 5 s, 17 s, 36 s | DIAGNOSABLE | **DIAGNOSABLE** within the design's speed range (below it: TE6) |
| TE2 | timing-edge | Nop on a suspended thread (former I-cap case) | DIAGNOSABLE | **DIAGNOSABLE** |
| TE3 | timing-edge | Minute 14 in `fsync`, 29:50, link wrap, console blank | DIAGNOSABLE | **DIAGNOSABLE** |
| TE4 | timing-edge | Slow Nop, nested tick, preemption at outer return, H10 | DIAGNOSABLE | **DIAGNOSABLE** |
| TE5 | timing-edge | Nop between the load and store of an LED RMW | DIAGNOSABLE | **DIAGNOSABLE** (LEDSPLIT) |
| IF1 | instrumentation-fault | Transient write failure spanning onset | BLIND | **DIAGNOSABLE** |
| IF2 | instrumentation-fault | Worker killed at minute 13-14 | DIAGNOSABLE | **DIAGNOSABLE** |
| IF3 | instrumentation-fault | Reader races; head moves backwards | DIAGNOSABLE | **DIAGNOSABLE** (spec note) |
| IF4 | instrumentation-fault | 25-35 s burst; about 98 sporadic failing ticks | BLIND | **BLIND** (sporadic variant; new cause: all-or-nothing creation) |
| IF5 | instrumentation-fault | Failed `fsync` on an allocating flush | BLIND | **DIAGNOSABLE** |
| IF6 | instrumentation-fault | Corrupt slot `seq`, forward head jump | AMBIGUOUS | **DIAGNOSABLE** |
| OE1 | observer-effect | MS driver hang with raised preempt count | DIAGNOSABLE | **DIAGNOSABLE** |
| OE2 | observer-effect | `statfs` FAT scan | DIAGNOSABLE | **DIAGNOSABLE** |
| OE3 | observer-effect | Collector load sets the H4 start-delay exposure | DIAGNOSABLE | **DIAGNOSABLE** |
| OE4 | observer-effect | Kernel-privileged `pscol`, stray store | DIAGNOSABLE | **DIAGNOSABLE** |
| OE5 | observer-effect | Collector exit frees a mousedev client mid-walk | DIAGNOSABLE | **DIAGNOSABLE** (timing note) |
| OE6 | observer-effect | Stall panel paints for minutes | DIAGNOSABLE | **DIAGNOSABLE** (N1p) |
| A1-OE3 | observer-effect (reopened by the K10/K11 cut) | Who held the CPU while the thread was preempted mid-command | closed by T2c (r1/r2) | **AMBIGUOUS** |
| IF7 | instrumentation-fault (new; preallocation path) | Persistent write failure of FSINFO or the PSCLOG directory sector | – | **BLIND** |
| IF8 | instrumentation-fault (new; preallocation path) | Persistent write failure of the FAT sector at the allocator position | – | **BLIND** |
| TE6 | timing-edge (new; preallocation path) | Early death while the first 2 MB segment is created on a slow stick | – | **AMBIGUOUS** |
| OE7 | observer-effect (new; preallocation path) | Global `drop_caches` walks the page cache with preemption off once per segment | – | **DIAGNOSABLE** (unstated perturbation) |
| UL6 | unlisted-shape (new) | The watchdog Nop breaks the link with no thread command in flight | – | **DIAGNOSABLE** (decoder row recommended) |

---

## 1. Source facts the scenarios rest on (verified by me in this tree)

### 1.1 What every `fsync` of a segment writes

| # | Fact | Evidence |
|---|---|---|
| S1 | `fsync` on vfat is `file_fsync` (`fs/fat/file.c:136`). It does three things: `write_inode_now(inode, 0)`, then `write_super`, then `sync_blockdev(sb->s_bdev)`. | `fs/sync.c:55-76` |
| S2 | `write_inode_now` always uses `WB_SYNC_ALL`, so `wait = 1`. The data pages are written by `do_writepages`. If the inode is dirty, `write_inode` runs synchronously. Then the data mapping is waited on. | `fs/fs-writeback.c:568-588`; `__sync_single_inode` `:153-183` (`:158` `wait = ... WB_SYNC_ALL`, `:174` `write_inode`, `:180` `filemap_fdatawait`) |
| S3 | **Every** `write()` dirties the inode. `file_update_time` changes mtime, and fat sets no coarse `s_time_gran` (grep: none in `fs/fat`, `fs/vfat`). | `mm/filemap.c:2276`; `fs/inode.c:1231-1242` (`mark_inode_dirty_sync`) |
| S4 | So every segment `fsync` rewrites the file's **directory sector**. `fat_write_inode` calls `sb_bread`, edits the entry, then `sync_dirty_buffer`. This is synchronous and returns `-EIO` if the sector write fails. | `fs/fat/inode.c:556-609` (`:568` `sb_bread`, `:603-604` `sync_dirty_buffer`); `fs/buffer.c:2703-2724` (`:2718-2719` `-EIO`); `fs/buffer.c:128-146` |
| S5 | A directory sector holds 16 entries. The segment names are valid uppercase 8.3 names, so vfat adds no long-name entries. Consecutively created segments therefore share a directory sector, about 15 times in 16. The exact slot layout is UNVERIFIED: earlier rehearsal files shift it. | `fs/fat/inode.c:1320-1321` (`dir_per_block` = 512/32) |
| S6 | Every `fsync` also marks **FSINFO** dirty, unconditionally, and `sync_blockdev` writes it. | `fs/fat/inode.c:453-459` (`fat_write_super`); `fs/fat/misc.c:40-72` (`mark_buffer_dirty` at `:68`) |
| S7 | A failed asynchronous buffer write sets `AS_EIO` on its mapping and clears the buffer's uptodate bit. The first `filemap_fdatawait` on that mapping returns `-EIO` and clears the flag. `sync_blockdev` is one such wait. | `fs/buffer.c:429-451` (`:449` `set_bit(AS_EIO...)`, `:451` `clear_buffer_uptodate`); `fs/buffer.c:152-158`; `mm/filemap.c:279-283` |
| S8 | `sb_bread` of a buffer that is not uptodate re-reads the sector from the stick. | `fs/buffer.c:1378-1384` |
| S9 | A failing sector is tried 10 times. Each try has one LED RMW pair; failed tries add `mdelay(1)`. All of it runs inside `__bio_kmap_atomic`, so the preempt count is raised. The driver itself prints nothing (`DBG` is compiled out). The buffer layer's "lost page write" is `printk_ratelimit`ed. | `drivers/block/ms_psp.c:21-25`, `:38`, `:252-268`, `:304-326`; `fs/buffer.c:443-447` |
| S10 | A partially written page is written back through `block_write_full_page` with **only its dirty buffers**. Buffers of earlier flushes on the same page are not rewritten, and 512-aligned writes read nothing first. | `fs/buffer.c:2073-2141` (`cont_prepare_write`); `fs/fat/inode.c:116-125` |

### 1.2 The preallocation claim (DESIGN 4.4), re-verified

| # | Fact | Evidence |
|---|---|---|
| P1 | A write wholly below `mmu_private` extends nothing. `cont_prepare_write` takes the `page->index < pgpos` branch, and `__fat_get_block` returns at the `phys` test, before `fat_add_cluster`. | `fs/buffer.c:2084`, `:2112-2114`; `fs/fat/inode.c:55-72` |
| P2 | `fat_bmap` maps from the per-inode cluster cache. Only on a miss does it walk the on-disk chain. The cache holds at most 8 runs. A walk that reads a FREE entry calls `fat_fs_panic`, which makes the file system read-only. | `fs/fat/cache.c:16`, `:217-272` (`:253-259` panic), `:295-329`; `fs/fat/misc.c:30-33` |
| P3 | The allocator searches from `prev_free + 1` and sets `prev_free` **in memory** for each allocated entry. It re-reads a non-uptodate FAT sector from disk (S8). | `fs/fat/fatent.c:455-476`; `fs/fat/inode.c:1274-1275`, `:1311` (`usefree` off, `:955`) |
| P4 | `fstat` reports `st_blksize` equal to the cluster size, so the collector can tell which creation steps allocate. | `fs/fat/file.c:307-312` |
| P5 | FIBMAP is supported: `.bmap = _fat_bmap`. A root process can map its own file to device sectors. | `fs/fat/inode.c:193-207` |
| P6 | `drop_caches` holds `inode_lock`, a spinlock, while it invalidates every clean page of every inode of every superblock. On this uniprocessor `CONFIG_PREEMPT=y` kernel that means **preemption off** for the whole walk. There is no `cond_resched`. | `fs/drop_caches.c:15-26`; `fs/inode.c:83`; `include/linux/spinlock_api_up.h:27-28`, `:51`; `.config:135` (no `CONFIG_SMP`) |
| P7 | `fadvise64(POSIX_FADV_DONTNEED)` invalidates one file's range without taking `inode_lock`. | `mm/fadvise.c:98-108`; `arch/mips/kernel/scall32-o32.S:599` |
| P8 | A preempted task keeps `TASK_RUNNING` and is switched out with `PREEMPT_ACTIVE` set. `schedule()`'s `prev != next` branch sees it, but `try_to_wake_up` does not. | `kernel/sched.c:3627`, `:3700-3707`, `:3788` |

**My conclusion on 4.4.** For **reported** errors the design is right. A
flush never allocates and never dirties a FAT sector (P1). A failed data
page is rewritten by the next flush (S10). The directory entry and FSINFO
are rebuilt from memory. No `fat_fs_panic` lies on the flush path.

What 4.4 does not consider is that S4 and S6 make every segment `fsync`
depend on two sectors that **every segment shares**. That is IF7.

---

## 2. Attempt-3 scenarios re-run against revision 3

### UL1 (H10). LED RMW writes back bit 4 during a suspension at S14. DIAGNOSABLE

The sequence is as in attempt 3: the thread is preempted at S14, `pscol`
does Memory Stick I/O, a CLEAR read-back carries bit 4, the ACK is lost,
and the thread gets −4.

What r3 records:
- **`lc`:** `lc_epc` = S14 (K8; DESIGN:472).
- **SC record:**
  - `led_or & 0x10 ≠ 0` and `led_pid` = worker (K6; DESIGN:231-232);
  - `ms_delta ≥ 2`, `preempt_delta ≥ 1`;
  - `ret −4`, `ack_polls 1,000,001`.
- **S record:** `rd_clr_or & 0x10` with b4/b5 set (DESIGN:355-360).

The per-bit counts and AND accumulators (K7) are cut. The OR values carry
the rule (row H10, DESIGN:1195), which reports the S13..S20 window and the
bit.

**Ruling: DIAGNOSABLE.**

### UL2. One foreign frame toggles mouse mode off. DIAGNOSABLE

- POLL `pi_flags` b3 is set and b4 is 0, on the poll whose `P08` is
  foreign.
- Later polls have `mouse_flags` b0 = 0 while `rx` follows the presses.
- Row N10 (DESIGN:1213) names the shape, and 10.7 step 3 ties the toggle
  to its frame.
- D7a re-toggles mouse mode after death.

**Ruling: DIAGNOSABLE.**

### UL3. Link stays one reply behind. DIAGNOSABLE

- N2b now compares against the template's per-command `rx[2]`, and falls
  back to the literal value only without a template (DESIGN:1205).
- It is tested before H6 (10.7 step 5).
- Stage 3 has the sequence (DESIGN:1481).

**Ruling: DIAGNOSABLE.**

### UL4. Valid frames, HOLD bit stuck. DIAGNOSABLE

Row N11 (DESIGN:1214).

**Ruling: DIAGNOSABLE.**

### UL5 (H10). Clean LED read-back during a mid-window suspension. DIAGNOSABLE (was AMBIGUOUS)

**Trace.** The thread is preempted at S14 by the worker, whose `fsync`
does LED RMWs that read back only LED bits. The command returns −4 and
input stays dead.

`P08` records:
- `preempt_delta ≥ 1`;
- `lc_epc` = S14, with `lc_flags` b0 and b2;
- `ms_delta > 0`, `led_or & ~0xC0 = 0`, `led_pid` = worker;
- `wn = 0`.

**Decoder.**
- H10 does not match: the read-back is clean.
- **N1m matches** (DESIGN:1202). It is reported with:
  - the step;
  - the suspension bound `dtick − lc_dtick`;
  - `ms_delta` and `led_pid`;
  - the pre-registered with/without-LED harm-rate table (10.7 step 7,
    DESIGN:1683-1693).
- The narrowed refutation sentence is suppressed for this onset
  (DESIGN:1674-1676).

The run cannot separate N1 from a read side effect, and it says so. That
is the most one run can do. All four parts of the attempt-3 fix are in
place.

**Ruling: DIAGNOSABLE.** The designer's statement "these cannot be
separated in one run" is an acceptance I agree with.

### TE1. Death at 5 s, 17 s, 36 s. DIAGNOSABLE (within the design's speed range)

**What is in place:**
- The rings are BSS from boot.
- `durable_next = 0` keeps the WB record.
- The template has a code-derived fallback, with the WB, M and WT
  baseline for H8 (10.7 step 2).
- The early-death exception at 3:00 sends the operator to section D
  (8.3).

**What preallocation changes.** The first durable flush now waits for
the whole first 2 MB segment: FILEHDR plus 32 steps of 64 KB (DESIGN:927-936).
- The P and POLL rings hold 114.7 s.
- The collector starts at about 20-40 s of uptime (DESIGN:1223, UNVERIFIED).
- The design's own creation time is 7-40 s, so the first drain comes at
  about 80 s or earlier.

All boot records survive inside the design's stated range. Below it,
see TE6.

**Ruling: DIAGNOSABLE** for sticks at or above the design's assumed
≈ 52 KB/s.

### TE2. Nop on a suspended thread (the former I-cap case). DIAGNOSABLE

The `lc` overwrite words are uncapped and kept (K8; DESIGN:472, `:282-290`).

**Trace:**
1. At tick k+4 the thread is current at S18. T2a stores `lc_epc` = S18
   and `lc_r` holding `i` and `ptr`.
2. At the WT tick k+5 the W extension copies the `lc` block (`ext_flags`
   b4 = 0, b5 = 1).

The decoder reports P6, and the cross-check (−2 with `nwords = j`)
agrees. The I ring was never needed for this.

R10 (G2 checks that `i` and `ptr` stay in registers 2..15, 24, 25) is
unchanged.

**Ruling: DIAGNOSABLE.**

### TE3. Minute 14 in `fsync`; 29:50; 16-bit link wrap; console blank. DIAGNOSABLE

**Unchanged mechanisms:**
- The D8 two-display check (RUNBOOK:342).
- The 16-bit links wrap at about 30.6 min, and nearest-value expansion
  handles one wrap.
- The W ring spans 1,280 s.
- A console blank exercises N4, which is recorded.

**New in r3.** The HUD now writes only rows 0-175 (DESIGN:886-891). A
software blank by `fbcon` clears the whole screen. The HUD repaints its
rows at 4.35 Hz, and the kernel band is black unless the panel paints.
Nothing in D8 depends on the blank.

A death during a segment switch is also covered. The switch writes no
metadata; the spare's first flush goes to offset 1,536 (DESIGN:967-971).

**Ruling: DIAGNOSABLE.**

### TE4. Slow Nop, nested tick, preemption at the outer return, H10 write-back. DIAGNOSABLE

The nested tick no longer overwrites `lc`: the `preempt_count()` mask
(K9; DESIGN:472, `:244-250`) sees it. The tick:
- increments `lc_nested`;
- sets `lc_nest_id`, which appears as `lc_flags` b4 on the command.

The former I-record flag has gone with the I ring, but `lc_flags` b4
carries the same fact.

The decoder reports H4 at P4 plus H10 (S13..S20) (DESIGN:1478).

**Ruling: DIAGNOSABLE.**

### TE5. Nop between the load and the store of an LED RMW. DIAGNOSABLE

- The EPC label `LEDRMW` (DESIGN:1605-1606) and row LEDSPLIT
  (DESIGN:1216) report the loaded value from `r`, per `regmap.txt`, and
  the G3 transition.
- Stage 3 has a vector for it (DESIGN:1476).

**Ruling: DIAGNOSABLE.**

### IF1. Transient write failure spanning onset. DIAGNOSABLE (was BLIND)

**Trace through this tree.**
1. A 3 s outage hits a tick. The flush writes only data sectors below
   `mmu_private` (P1), the directory sector (S4) and FSINFO (S6).
2. The failing data buffers lose their uptodate bit (S7). The directory
   sector and FSINFO are re-read on their next use (S8) and rebuilt from
   memory.
3. The rewind re-sends the records from `durable_next`, and the retry
   overwrites the same offset (DESIGN:1042-1054).
4. Nothing allocates, so no FAT link can be lost. IF5's
   `fat_get_cluster` panic path (P2) is never reached.
5. A creation step caught by the outage is abandoned (DESIGN:943-950),
   and the next attempt starts at least 10 s later.

Records that were durable before the outage stay durable. After the
outage the catch-up writes everything since `durable_next`. The onset
window and the post-death script both reach the stick.

**Two notes, not findings.**
- **Stale tail.** If the retry flush is shorter than the failed one (the
  failed one carried PROCS or STATS), complete chunks of the failed flush
  can survive past the retry's end until the next flush overwrites them.
  They are CRC-valid duplicates. The decoder's (ring, `seq`) dedupe and
  UHB `tickno` handle them.
- **Non-ring chunks.** The design does not say whether EVENT and KMSG
  chunks in a failed flush are re-sent. `/proc/kmsg` reads consume the
  messages (`fs/proc/kmsg.c`), so a KMSG chunk overwritten by the retry
  is lost for good. I recommend keeping EVENT and KMSG payloads queued
  until a flush that contains them is durable.

**Ruling: DIAGNOSABLE.**

### IF2. Worker killed at minute 13-14. DIAGNOSABLE

1. The supervisor sees the death within 2 s (DESIGN:823-833).
2. It runs the worker loop in-process with its boot-time block. There is
   no `exec` and no allocation, so the attempt-1 BLIND cause is absent.
3. It creates a fresh segment at 64 KB per tick, then seeks every ring
   to `durable_next`.

The onset is in the 114.7 s rings, provided the creation takes less than
about 114 s minus the death-detection delay. That holds inside the
design's speed range. On a stick slower than about 18 KB/s it does not
(compare TE6).

**Ruling: DIAGNOSABLE.**

### IF3. Reader races; head moves backwards. DIAGNOSABLE (spec note)

The `seq` invalidate/publish protocol, the before/after check, and the
high-low-high read of `total_counts` are unchanged.

**Spec note.** For a backward head jump, 3.5 step 1 leaves `f_pos` at
`s > h` (DESIGN:761-762). Two consequences:
- 4.3 step 2 counts that ring as complete (`pos_r ≥ H_r`) rather than
  stuck.
- `head_regress` is not among the counters that turn REC red
  (DESIGN:863-869).

The resync appears only as a Stage 3 pass condition (DESIGN:1469) and an
EVENT name (DESIGN:1534).

Without a resync, a ring whose head jumped back by more than N records
stays silent until the writer passes the old position, and the drain
still counts as complete. 4.3 should state the rule: on any
`head_regress` increase, seek that ring to its head, emit the EVENT and
turn REC red.

**Ruling: DIAGNOSABLE**, because the Stage 3 pass condition binds
Stage 2 to the resync.

### IF4. 25-35 s burst, or about 98 sporadic failing ticks. **BLIND** (sporadic variant; new cause)

**Burst variant: DIAGNOSABLE.**
- A contiguous 25-35 s burst is shorter than the ring span.
- Flushes retry in place without allocating.
- A creation caught by the burst is abandoned and redone at least 10 s
  after it.
- Names cannot run out: 999 per run, attempts at least 10 s apart
  (DESIGN:1068-1071).

**Sporadic variant: BLIND.** The design claims "**A burst shorter than the
ring span (114.7 s) loses nothing, whether one burst or many**"
(DESIGN:1068). Its Stage 3 error test expects "≈ 120 sporadic failures
over 30 min → no record lost" (DESIGN:1470). Under the preallocation
rules both are false.

**Mechanism.** These rules combine:
- A spare is created 8 KB per tick while the active segment has room.
  That is 256 steps (DESIGN:933-934).
- **Any** failed step abandons the whole file (DESIGN:943-950).
- The next attempt starts from scratch, at least 10 s later
  (DESIGN:949-952).

Under attempt-3 IF4's pattern, 98 failing ticks per 30 min, the per-tick
failure probability is q ≈ 98 / 7,826 ≈ 1.25 %. So:
- One 8 KB-per-tick attempt succeeds with probability (1 − q)^257 ≈ 4 %.
- The active segment lasts about 294 s. In most cycles no spare is ready
  when it fills.
- The worker then **holds** (DESIGN:970-973). It reads the rings with
  zero bytes and creates at 64 KB per tick. That is 32 steps, all of
  which allocate, so all of which abandon on failure.
- How long that takes depends on the stick's speed. The design's own
  range for a 2 MB creation is 7-40 s (DESIGN:936, `:1224`), which is
  about 52-300 KB/s, UNVERIFIED (R8).
- Any time held beyond 114.7 s is lost, counted, and shown only on the
  panel.

**Simulated** (Appendix A; 200 runs of 30 min each):

| Stick speed | Mean lost per 30 min | p90 lost | Holds per run | Mean hold |
|---|---|---|---|---|
| 25 KB/s | 1,334 s | 1,397 s | 1.3 | 1,168 s |
| 52 KB/s | 743 s | 1,109 s | 4.3 | 273 s |
| 100 KB/s | 131 s | 335 s | 5.7 | 92 s |
| 150 KB/s | 33 s | 109 s | 5.4 | 58 s |
| 300 KB/s | 2 s | 0 s | 5.0 | 32 s |
| any, with no errors | 0 | 0 | 0 | – |

About 62 abandons per run are also burned, against the 999 names. If an
implementer counts abandoned files towards "at most 32 segments per run"
(DESIGN:952-954; the text does not say which), the cap is reached within
the run and the hold becomes permanent.

**What the analyst gets.** A death inside a lost window leaves:
- the rings' last 114.7 s at the end of each hold;
- panel photographs, which are point samples;
- whole-run STATS counters only at the 1.8 s points that reached the
  stick.

There is no raw window across onset (**S2 fails**) and no stick history
for that span (**S4 fails**). At 52 KB/s about 41 % of the run is in such
windows, and at 100 KB/s about 7 %.

**Ruling: BLIND** for a stick at or below about 100-150 KB/s under this
error pattern. Neither the speed nor the error rate is known. The design
accepted the premise (attempt-3 IF4), and the speed is within its own
stated range.

**Fix needed** (section 6, F2 and F3):
- Retry non-allocating creation steps in place. A step allocates if it
  crosses a multiple of `st_blksize` (P4).
- Abandon only after a failed **allocating** step.
- Let flushes use the **confirmed prefix** of a segment that is still
  being created (writes below its fsynced size never allocate, P1).
- Count only completed segments towards the cap.

Simulated with these fixes: **0 s lost** at 25, 40, 52 and 100 KB/s
under the same pattern (Appendix A).

### IF5. Failed `fsync` on a flush that allocated a cluster. DIAGNOSABLE (was BLIND)

I retraced attempt-3's IF5 timeline against r3:

1. **Tick t0.** The flush writes only blocks below `mmu_private` (P1).
   No `fat_add_cluster` runs, no FAT sector is dirtied, and no link like
   attempt-3's B→C exists.
2. **The failure.** The `fsync` fails on the data, directory or FSINFO
   writes.
3. **Retry.** The retry rewrites the same data blocks. The directory
   entry and FSINFO are rebuilt from re-read sectors (S4, S6, S8).
4. **Reads.** Nothing reads a stale FAT sector, because the flush path
   never consults the FAT on a cache hit (P2). On a cache miss it reads
   the on-disk chain, which was confirmed by `fsync` at creation.
5. **vfat.** It stays writable.

The read-only state now shows on the panel (`PSC MS RO`, 2.12), and
RUNBOOK E mounts the stick read-only.

**Allocation failures during creation.**
- The failed FAT sector belongs to a file that is abandoned and never
  touched again (DESIGN:943-947).
- The next attempt re-reads the sector (S8) and allocates from
  `prev_free + 1` (P3). So it neither reuses the leaked cluster nor walks
  the abandoned file's chain.
- `fat_chain_add` walks only the new file's own cached chain.

I found no way for a reported error to leave a **used** segment's
on-disk chain inconsistent. The `AS_EIO` flag on the block device
(S7) is consumed by the next `sync_blockdev`. Within a worker tick the
creation step's `fsync` follows its own `write()` (DESIGN:879-885), so a
failure of a FAT write that the creation dirtied is reported to the
creation step. Even a `pdflush` write of that buffer in the gap is
reported there.

**Ruling: DIAGNOSABLE.** The silent-loss residual R11 is hardware
behaviour; I accept it as stated (section 5).

### IF6. Corrupt slot `seq`, or forward head jump. DIAGNOSABLE (was AMBIGUOUS)

**Corrupt slot.** 3.5 step 4 skips and counts it (DESIGN:767-773):
- `slot_bad[r]` is incremented and `f_pos` advances;
- the drain is complete only when `pos_r ≥ H_r`;
- REC turns red on any `slot_bad` or `lost` increase (DESIGN:863-869).

**Forward head jump.** The reader skips to `h − N`. Those slots hold
older `seq`s, so it skips them one by one. Each skipped slot counts as
`slot_bad`, except the first, which counts as a lap. The reader reaches
the head within one call (at most N skips). The skipped slots had already
been drained, so the only real loss is the few records written between
the last drain and the jump.

**One note.** After a forward jump of J records, the 16-bit POLL→P link
(`sc_seq_lo`) is expanded "nearest to the record's own position"
(DESIGN:1575-1576). When |J mod 65,536| ≥ 32,768 that picks the wrong P
record. I recommend that the decoder fall back to pairing by
`(tick, Count)` whenever the nearest-value expansion lands on a missing
`seq`.

**Ruling: DIAGNOSABLE.**

### OE1. MS driver hang with a raised preempt count. DIAGNOSABLE

- The marker (K20) and the panel (K30) are kept.
- The panel shows the running task's pid, its EPC in `ms_wait_ready` or
  `ms_wait_ced`, and `preempt_count > 0` (DESIGN:615-622, `:1703-1708`).
- Preallocation doubles the exposure, as stated (DESIGN:1350).

**Ruling: DIAGNOSABLE.** The run-spending residual was accepted in
attempt 2 (J17), and I agree.

### OE2. `statfs` FAT scan. DIAGNOSABLE

There is no `statfs` call (DESIGN:996-1001).

**Residual.** A creation that hits ENOSPC when the free count is unknown
(`free_clusters = -1`, `fs/fat/inode.c:1274`) would scan the **whole**
FAT inside one `write()`: `fs/fat/fatent.c:456-499`, with
`free_clusters = 0` set at `:498-500`. That is about 30,000 sector reads
on this stick, a `statfs`-sized scan. Only an exhausted stick reaches it,
and the A3 check (128 MB free against at most about 18 MB used, plus
abandons) prevents that.

**Ruling: DIAGNOSABLE.**

### OE3. Collector load sets the H4 start-delay exposure. DIAGNOSABLE

The K12 hooks are kept and simplified (DESIGN:632-671). For every
**wake-up** of the thread they record:
- the delay (`wk_delay`, to 76 ms);
- the collector's exact share (`wk_wrk`);
- the class at wake-up and the last holder.

That is what attempt-2 OE3 asked for. Dropping the 8-class accumulator
removes "longest non-collector holder". S5 needs the collector's part,
and that is exact.

**Ruling: DIAGNOSABLE.** I agree with the simplification (K12). The
preemption half of the older A1-OE3 is a different matter: section 3.

### OE4. Kernel-privileged `pscol`, stray store. DIAGNOSABLE

- The worker guards (U18) and the kernel guards (K26) are kept.
- A violation means `_exit(3)` and a takeover. The supervisor's own image
  was not touched by the worker's stray store, so the takeover is clean.
- Later onsets are marked `instrumentation-suspect`.
- The R16 residual is stated.

**Ruling: DIAGNOSABLE.** After a takeover no second recovery exists
(R14). For a deterministic bug the standby design fared no better,
because it ran the same code. I accept R14.

### OE5. Collector exit frees a mousedev client while the thread walks the list. DIAGNOSABLE (timing note)

The thread-stopped shape N5 (`jp_stage` 15/16 fixed, W `epc` in
`mousedev_*`) is recorded, and the `do_exit` hook is kept (K25).

**Timing note.** The mousedev open/release counters (K24) are cut. The
old worker's exit after a stall SIGTERM happens "at its next return to
user mode" (DESIGN:830-832). That can be seconds after the takeover
EVENT. PROCS now runs only every 40 ticks (about 9 s).

So the decoder's annotation "a stop within 1 s of a takeover"
(10.7 step 5) cannot always be decided. The decoder should apply the
`instrumentation-suspect` annotation to any N5 within the takeover-to-PROCS
window, not 1 s.

**Ruling: DIAGNOSABLE** (OE5 was DIAGNOSABLE before K24 existed).

### OE6. Panel paints for minutes. DIAGNOSABLE

- SC `lc_flags` b5 marks every command that a paint overlapped, and
  `panel_cost_last` gives each paint's cost (K32; DESIGN:230, `:600-603`).
- Row N1p replaces the useless 1-second proximity flag (DESIGN:1203).

**Ruling: DIAGNOSABLE.** The recommendation is adopted.

---

## 3. Attempt-1 and attempt-2 scenarios closed by a mechanism now CUT

I checked every CUT row of section 0 against every attempt-1 and
attempt-2 scenario. Only one scenario reopens, and only in part.

### A1-OE3, preemption half (reopened by K10 and K11). AMBIGUOUS

**What closed it.** Attempt-1 OE3 asked for this fix (1): "whenever
`psc_jp_task` is TASK_RUNNING but not current, count the tick ... by class
of `current` ... and by `preempt_count(current) > 0`"
(`G1-attempt1-redteam.md`, OE3 fix 1). T2c (K11) implemented it. It
counted every tick at which the thread was runnable but not running.
That covers two cases:
- **woken but not yet run.** This is the H4 start-delay exposure.
- **preempted mid-command.** The command stays in flight, so it is
  exposed to every Nop during the suspension. This is also the N1, N1m
  and H10 exposure.

The I ring (K10) additionally sampled `current` at each in-flight tick.

**What r3 keeps.**
- K12 hooks only wake-ups. The design says so: "A preemption of the
  running thread is not a wake-up (`preempt_delta` and `lc` cover it)"
  (DESIGN:663-664).
- `preempt_delta` says **that** the thread was preempted, and `lc` says
  **where**.
- `dtick − lc_dtick` bounds **how long**.
- Nothing records **who held the CPU** during a mid-command suspension
  unless that task did Memory Stick I/O. In that case `led_pid` and the S
  records' `pid` name it.
- At a Nop instant the W record's `pid` names the current task. That is
  one sample per 5 s.

**Shape that is now unattributable.** An **N1** onset, by definition with
`ms_delta = 0` and `wn = 0` (DESIGN:1201). The thread is preempted at
S14 and held off for, say, 40 ms by a task that does no Memory Stick I/O
in that span. The candidates:
- `pscol`'s supervisor, which wakes every 2 s and reads `stats`
  (DESIGN:823-824);
- the worker while it renders the HUD (272 `fb_sys_write` calls, each
  with a full D-cache write-back, DESIGN:886-891);
- `psposk2`, `pspmd`, or the UART3 TX thread.

O(1) priorities make the interactive sleepers, `pscol` included, the
likely preemptors (attempt-3 OE3 note; `kernel/sched.c:171-172`).

**What is recorded.**
- `P08`: `ret −4`, `preempt_delta 1`, `lc_epc` = S14, `ms_delta 0`,
  `led_pid 0`.
- No W record (`wn = 0`) and no S record.
- POLL `wk_*` describes the **next** wake-up, not this preemption.

The decoder prints N1 with the step and the suspension bound, and no
actor. S5 asks to "know precisely how [the instrumentation] might have"
caused it. The run cannot say whether the collector held the CPU.

The pre-registered no-death inference (10.7 step 8, DESIGN:1694-1699)
attributes late starts by class. It cannot attribute the in-flight time
created by mid-command preemptions, which is the larger part of P4/P5a
exposure whenever such preemptions occur.

**Ruling: AMBIGUOUS.**

**Fix needed** (cheap, single-writer):
- In hook S (`kernel/sched.c:3700-3707`, IRQs off), add a branch:
  `if (prev == psc_jp_task && prev->state == TASK_RUNNING)`. That is an
  involuntary switch-out (P8).
- The branch starts "preempted wait" accounting identical to the
  wake-up accounting:
  - `pre_t0`;
  - `pre_cls0` = class of `next`;
  - collector part `pre_wrk`;
  - switch count.
- Publish it at the thread's switch-in. Copy it into the SC record when
  `psc_t_busy_p` is set; the reserved bytes 42-46 have room for
  `pre_cls0`, `pre_wrk` (u16 in Count/256) and a flag. Otherwise copy it
  into POLL.
- The decoder adds "holder" to N1, N1m and H10, and adds in-flight
  attribution to step 8.
- Cost: one compare per switch-out, which already loads `psc_jp_task`.

### Cuts checked and found not to reopen anything

| Cut | Scenario it served | Why it stays closed |
|---|---|---|
| K7 per-bit LED counts and ANDs | A1 UL1 | The OR values (`led_or`, S `rd_*_or`, run-wide ORs) show every bit ever read back. No rule used the ANDs. |
| K10 I ring (other uses) | A1 TE2, A2 TE4, A3 OE6 | `lc` (K8) gives the exact suspension point. The nested-tick test (K9) plus `lc_flags` b4 replaces the I nested flag. `lc_flags` b5 replaces the I paint flag. |
| K11 T2c (wake-up half) | A2 OE3 | K12 measures wake-up delays at Count resolution, up to 76 ms. Longer stalls show in POLL `period`. |
| K15 stack snapshot, K16 W copies | none | No rule read them. W b6 keeps "MS transfer in progress". |
| K24 mousedev counters | A2 OE5 | Rated DIAGNOSABLE without them (timing note in OE5 above). |
| K33 out-of-bounds checksum recompute | A2 note | Not a scenario. Acceptances stay visible as `ret > 0` with `rx[1] ≥ 16`. |
| U2 standby | A1 IF2, A2 IF2 | U1 gives the same allocation-free first recovery (IF2 above). A2's `durable_seq` defect stays fixed by `durable_next` (DESIGN:400). |
| U7 r2 segment rules | A2 IF4, A3 IF4 (names) | 999 names and at least 10 s between attempts. The name space cannot run out in a run. IF4's **new** cause is the all-or-nothing creation, not U7. |
| U8 summary mode | none | – |
| U10 PANEL read-back | review N-5 | Replaced by the operator seeing `PSC TEST`, an abort item. |
| U11 SELFTEST chunk | none | UHB b1-b8 carry the checks. |
| X11 decoder reports | none | No matrix row depended on them. |

---

## 4. New scenarios

### IF7. The FSINFO sector, or the PSCLOG directory sector, refuses writes for the rest of the run (instrumentation-fault; preallocation path). BLIND

**Premise.** One logical sector stops accepting writes, while the data
sectors keep working. The likelihood is UNVERIFIED and lower than for a
transient error. Two points put it inside the design's own error model:
- the design plans for "a persistently bad region" (R8; "Persistent
  failure", DESIGN:1055-1057);
- the two sectors involved are the most-written on the stick. At one
  `fsync` per flush plus one per creation step, each is written about
  9 times per second, roughly 19,000 times in a 35-minute run, against
  telem's 4.35 per second.

`pspMsWriteSector` fails on `INT_REG_ERR` or on a wait error
(`arch/mips/psp/ipl_sdk/memstk.c:342-374`). A card that refuses one worn
logical block reports exactly that.

**Trace (sector D = the PSCLOG directory sector; FSINFO behaves the same
through S6/S7).**
1. **Flush n** writes its data sectors successfully (S2: `do_writepages`
   runs first). `fat_write_inode` then fails `sync_dirty_buffer(D)` after
   10 tries per attempt of non-preemptible retries (S9). `fsync` returns
   `-EIO` (S4).
2. **The worker's rule.** It applies "rewind and retry in place"
   (DESIGN:1042-1054):
   - rewind every ring to `durable_next`;
   - keep `seg_end`;
   - overwrite.
3. **Flush n+1 and every later flush** are written to the same
   `seg_end`. Each holds the records from `durable_next`, capped at
   `cap_r × m` per ring (DESIGN:859-862).
   - Production is about 9 P records per tick, and the cap is 48 or 96.
     So within 5-10 ticks the backlog exceeds the cap.
   - From then on every retry carries **the same oldest records**, and
     the newer ones are never written anywhere.
   - After 114.7 s those oldest records are overwritten in the ring. The
     reader skips forward, counting `lost`, and the window slides at the
     production rate. Each tick's write overwrites the previous window.
4. **After 3 failures** the worker switches to the spare (DESIGN:1055-1057).
   The spare's entry is in the same directory sector with probability
   about 15/16 (S5). For FSINFO the probability is 1. The in-place retry
   continues in the spare.
5. **Every creation step's `fsync` also fails** (S4, S6). Every new
   segment is abandoned (DESIGN:943-950). After the spare fills, the
   worker holds.
6. **The takeover never fires**, because the worker keeps reading
   (DESIGN:826-829). That is correct: a new worker would fail the same
   way.
7. **Display.**
   - `durable_tick` freezes. The panel shows `PSC STALL` with a rising
     `DUR` for the rest of the run.
   - The HUD `MS` line is red and `ERR` keeps rising.
   - RUNBOOK C4 sends the operator back to normal use with a panel photo
     every 5 minutes. D8 never passes (P7b), and the raw image is
     mandatory.

**What the stick holds at the pull.**
- Everything before the failure (below the old `seg_end`).
- About 1-2 s of records just after it.
- **One** window of a few seconds of records from about 114.7 s before
  the pull, written by the last retry.
- Nothing else after the failure.

The raw image cannot recover the rest. The records **did** reach the
stick and were then physically overwritten by the design's own retries.

**What the analyst gets for a death after the failure:**
- the panel photographs: point samples of the last `P08`, the last W
  record, the stage and `lc_epc`, taken at the moments the operator
  photographed;
- whole-run STATS only if the last surviving flush happened to carry a
  STATS chunk (1 tick in 8).

There is no raw window across onset (**S2 fails**), no W extension
history and no POLL history (**S4 fails**), and no recorded post-death
script, so H6 against H7 is lost.

The S records in the final window name the failing sector by number
(DESIGN:351-355). So the **instrumentation** failure is diagnosable; the
input death is not.

**Why the design cannot see it.**
- 4.6 assumes that an `fsync` error means this flush's data may not be
  on the stick. Its two answers both depend on that: re-send the same
  records to the same place, or escape to fresh space.
- Neither works when the failing sector is shared metadata. The retry
  also destroys data that did reach the stick.
- The design already holds the information that would tell the cases
  apart. The S ring records every transfer's sector and error bit
  (DESIGN:355), and the collector drains it every tick. It is never used
  for a decision.

**Ruling: BLIND.**

**Fix needed** (section 6, F1):
- Never overwrite a region already handed to `write()`. After a failed
  flush, advance `seg_end` past it. The segment is preallocated, so this
  costs space, not FAT writes.
- Keep a `written_next[r]` separate from `durable_next[r]`, so retries
  carry only records not yet written. Re-send the failed flush's records
  once.
- Judge data durability from the S records of the segment's own data
  sectors. The worker maps its file with FIBMAP (P5) once at creation.
- A flush whose data sectors all completed without b1 is durable, even
  if `fsync` returned `-EIO` because FSINFO, the directory sector or a
  FAT sector failed. The chain and the directory entry were confirmed at
  creation and do not change.
- Show this state as `MS META ERR` (a new HUD state and panel title).
  Make the RUNBOOK treat it like a red line: raw image mandatory.

### IF8. The FAT sector at the allocator's position refuses writes (instrumentation-fault; preallocation path). BLIND

**Premise.** As in IF7, but the bad logical sector is the FAT sector
holding the entries just after `prev_free`. A FAT32 sector holds 128
entries (4 MB of 32 KB clusters). Sector-level persistence is UNVERIFIED.

**Trace.**
1. Creation attempt a starts with step 1:
   - `open(O_CREAT|O_EXCL)`, which writes the directory sector (fine);
   - the 1,536-byte FILEHDR write, which allocates one cluster c at
     `prev_free + 1` (P3) and dirties the bad FAT sector F;
   - `fsync`, where `sync_blockdev` fails on F and returns `-EIO` (S7).
   The worker abandons the attempt (DESIGN:943-950).
2. The in-memory `prev_free` is now c (`fs/fat/fatent.c:476`). F is not
   uptodate.
3. Attempt a+1, at least 10 s later (DESIGN:949-952):
   - `fat_ent_read_block` re-reads F from disk (S8), where c is free
     again;
   - the search starts at c + 1, inside F;
   - the allocation dirties F and fails again.
4. **Each attempt moves the allocator by one cluster, 10 s apart.** Up
   to 128 attempts are needed to leave F: **up to about 21 minutes**.
   Names are not the limit (999).
5. **Meanwhile:**
   - the active segment fills (at most 294 s);
   - the worker holds (DESIGN:970-973);
   - after 114.7 s the rings overwrite records, counted as `lost`;
   - the panel shows `PSC STALL`, and the HUD `WAIT SPARE`.
6. If abandoned files count towards "at most 32 segments per run"
   (DESIGN:952-954; the text does not say), the cap is hit after 32
   attempts (5.3 min). The hold is then **permanent**.

**What the stick holds.** Everything up to about 294 s after the
failure, then nothing for up to about 14 minutes (or for good, under the
cap reading).

A death in that window has only panel photographs: **S2 and S4 fail**.

The S records of each attempt (b1 set, FAT sector number) are in the
rings. They reach the stick only after a creation finally succeeds.

**Why the design cannot see it.**
- 4.6 says a creation failure leaves "the active segment ... unaffected"
  (DESIGN:1058).
- It accepts "a stick refusing writes for minutes" as Case 2
  (DESIGN:1033-1034). That is the whole stick.
- Here the stick accepts every data write. The loss comes from the
  design's dependence on one new FAT link per 294 s, from its 10 s
  attempt spacing, and from keeping only one spare.

**Ruling: BLIND.**

**Fix needed** (section 6, F3 and F4):
- Count only completed segments towards the 32 cap, and say so.
- Use the S records to recognise a FAT-sector failure, which is visible
  as the failing `sector` lying in the FAT area. After such an abandon,
  let the next attempt start without the 10 s wait, bounded by a name
  budget (for example at most 200 attempts per run). 128 one-cluster
  attempts at about one per tick then take under a minute.
- Keep **two** segments ahead: one ready and one in creation. That
  doubles the active's margin to about 10 minutes.

### TE6. Early death while the first segment is created on a slow stick (timing-edge; preallocation path). AMBIGUOUS

**Shape.** Dossier 9.6: in 2 of 5 sessions input was already dead before
36 s. In r3 **nothing is durable and nothing is drained** until the
first whole 2 MB segment exists. The worker "reads rings with zero
bytes" while holding (DESIGN:971-973, `:1223-1227`).

**Timeline.**
- The thread starts at the device initcall: a few seconds of uptime,
  UNVERIFIED.
- The collector starts at about 20-40 s (DESIGN:1223).
- The first segment is FILEHDR plus 32 steps of 64 KB, all at the
  stick's single-sector speed. The driver writes one sector per command
  with busy waits (`arch/mips/psp/ipl_sdk/memstk.c:342-374`;
  `drivers/block/ms_psp.c:304-326`). The real speed is UNVERIFIED (R8).
- The P and POLL rings hold 114.7 s from the thread's start. A first
  drain after uptime of about 117 s loses the earliest records.
- That happens when 2,048 KB / (117 s − collector start) exceeds the
  stick's speed: below about 21 KB/s with a 20 s start, or about 27 KB/s
  with a 40 s start.
- The S ring is **not** at risk. The whole creation produces about 700 S
  records, against 4,096 entries.

**Below that speed, for a death at 5-17 s.**

| Record | Lost or kept |
|---|---|
| Onset P and POLL records | **Lost**, counted as `lost` in the first RECS block (DESIGN:1529) |
| Onset command's own result | **Lost**, so the 10.7 step 5 P-point cross-check is impossible |
| W records (1,280 s span) | Kept: the Nop's own result, `epc`, `lc_*`, `p_head`. The H4 step is still reported. |
| Post-onset P records | Kept for the state classification |
| Template | Already `NO HEALTHY TEMPLATE` for so early a death |

**Ruling: AMBIGUOUS.** The trigger step survives in W, but its outcome
cross-check and the S2 window before and across onset do not. The
design states the condition in 6.2, but it is not accepted with a
reason in section 13, and the fix is cheap.

**Fix needed** (section 6, F2): let tick flushes use the **confirmed
prefix** of a segment under creation:
- bytes below the last size confirmed by `fsync` and `fstat`, minus
  40,960;
- such writes are below `mmu_private` and never allocate (P1), so the
  4.4 argument holds unchanged;
- the first durable flush then comes one 64 KB step after the FILEHDR,
  that is, in seconds;
- if a later creation step of that file fails, the file stops growing
  and its confirmed prefix remains valid and durable.

Simpler alternative: make the first segment small (for example 512 KB)
and create the normal 2 MB spare behind it.

### OE7. `drop_caches` walks the whole page cache with preemption off, once per segment (observer-effect; preallocation path). DIAGNOSABLE

**Shape.** Step 4 of every creation writes `1` to
`/proc/sys/vm/drop_caches` (DESIGN:937-942). That is once at start-up,
then once about every 4.9 minutes. In this tree that call:
- holds `inode_lock` across the invalidation of **every** clean page of
  **every** inode of every superblock (P6);
- includes the block device's metadata pages;
- has no `cond_resched`.

On this uniprocessor `PREEMPT` kernel that is a non-preemptible stretch.
Interrupts stay enabled (`include/linux/spinlock_api_up.h:27-28`), so
ticks and Nops still run. The stretch is not named in 7.1, 7.4 or 5.4.
It is new in r3: r2 used `drop_caches` only before a standby respawn,
which was rare (DESIGN:116).

**Size.**
- Between two drops the cache holds about one spare (512 pages), up to
  one active segment (at most 512 pages), and the block device's FAT,
  directory and FSINFO pages.
- `invalidate_complete_page` runs per page, which includes freeing the
  page's 8 buffer heads (`mm/truncate.c:269-313`).
- Estimate: **5-15 ms** (UNVERIFIED). That is the same order as one
  8-sector Memory Stick bio segment, which the collector already runs
  non-preemptibly several times per second (S9).

**What is recorded.**
- **If the stretch delays a thread wake-up:** POLL `wk_delay` up to
  76 ms, with `wk_cls0 = wk_cls1 = WRK` and `wk_wrk` close to the whole
  delay (K12). The adjacent EVENT `segment ready` and the S read record
  of the read-back place it.
- **If the thread was already preempted mid-command by the worker:** the
  suspension spans the step's `fsync`, `drop_caches` and `pread`. The
  writes and the read carry LED operations, so `ms_delta > 0` and
  `led_pid` = worker. N1m is reported with the suspension bound, and the
  actor is known.

**Ruling: DIAGNOSABLE.** The effect is attributed to the collector by
existing fields, though not by name.

**Recommendation (not blocking):**
- Replace the global `drop_caches` with
  `fadvise64(fd, SEG − 4096, 4096, POSIX_FADV_DONTNEED)` on the spare
  (P7). It invalidates the one page the read-back needs and takes no
  `inode_lock`.
- Or time the call in UHB and state it in 7.1 and 7.4.

### UL6. The watchdog Nop breaks the link with no thread command in flight (unlisted shape). DIAGNOSABLE (decoder row recommended)

**Shape.** Dossier 9.6 places three deaths in a 0.45 s window that
contains a 5 s boundary. H4 needs a thread command in flight at the Nop.
Another cause fits the same data: the Nop **itself** puts the syscon or
link into a bad state, with no interleave.

Recon §5.1 lists the syscon's internal behaviour as UNKNOWN. Possible
variants:
- an earlier event (a benign-looking straddle at 1250(k−1), or an LED
  write-back) leaves residue that only command 0x00 trips;
- the Nop's own transaction fails (its own −4, −2 or foreign reply) and
  the syscon changes state;
- the onset then falls at the first thread command after tick 1250k,
  with `t_busy = 0` in that WT record.

**What r3 records.**
- **The WT record at 1250k.** Its own `ret`, `nwords`, `rx`,
  `ack_polls`, `drain` and `drain_last` (DESIGN:256-262), with
  `t_busy = 0` and `ext_flags` b4 = 0.
- **Every earlier WT record.** Each has its own outcome, and the W
  outcome counters are in stats words 45-51.
- **The 6.3 placements.** The last good thread command is placed before
  tick 1250k and the first failed one after it, at Count resolution.
  The thread is woken by that tick's softirq after the Nop
  (`psp.c:359` before `:367`), so the gap can be microseconds.

**Decoder.**
- Row H4 needs `t_busy` b0 (DESIGN:1189), so it does not fire. The
  trigger is printed as "none".
- The placements show the Nop between the last good and first bad
  command.
- The ±30 s raw window contains the Nop's own frame.
- The per-step benign-interleave count treats a straddle at 1250(k−1)
  whose thread result was fine as **benign**, even when the Nop's own
  result was not.

An analyst has everything needed. The automatic report steers away from
the watchdog in exactly the case 9.6 makes most interesting.

**Ruling: DIAGNOSABLE.**

**Recommendation (not blocking).**
- Add a trigger row "**WB: watchdog boundary without interleave**": the
  first failed thread command is the first after a WT record that had
  `t_busy = 0`. Report that Nop's own outcome against the healthy
  template.
- In every report, list all WT records within ±2 cycles of onset whose
  own outcome is not a valid Nop reply.
- Count a straddle as benign only if **both** the thread's result and
  the Nop's own result were valid.

---

## 5. Section 13 acceptances: do I agree?

| Acceptance or judgement | My position |
|---|---|
| N1 and an LED read side effect "cannot be separated in one run" (N1m) | **Agree.** Both leave identical records. The pre-registered harm-rate comparison is the right partial remedy. |
| R11: a silently lost FAT or directory write (hardware) is answered by the raw image and the shallow read-back (J11) | **Agree.** Reported errors cannot produce it (IF5 above). A deep chain walk in the kernel could itself panic (P2). A non-panicking alternative exists if wanted: FIBMAP (P5) plus a raw read of the FAT through `/dev/ms0` after a scoped invalidate. |
| K12 simplified to "collector part + last holder" | **Agree for wake-ups**, since the collector's exact share is what S5 needs. **Not** a replacement for T2c's preemption half (section 3). |
| R14: no recovery after a takeover | **Agree.** A deterministic bug defeats any same-binary recovery. |
| J10: one spare, created at 8 KB per tick | **Disagree.** With sporadic errors (IF4) or a bad FAT sector (IF8), one all-or-nothing spare leaves the run exposed to holds longer than the ring span. |
| 4.6: retry in place is now safe | **Agree that it no longer risks the file system. Disagree that it is harmless.** Under a persistent metadata failure it destroys data that reached the stick (IF7). |
| 4.5 Case 2: "a stick refusing writes for minutes" accepted, with the panel as the record | **Agree only for a whole-stick refusal.** IF7 and IF8 are refusals of one shared metadata sector while the data region works, and the design can route around them. |

---

## 6. Fixes required to pass (consolidated)

The three BLINDs and TE6 share one root: durability and capacity hinge
on all-or-nothing operations against shared metadata. The fixes are
small and stay inside 4.4's proven envelope (writes below `mmu_private`
never allocate).

| # | Fix | Closes |
|---|---|---|
| **F1** | **No overwrite; data-sector durability.** (a) After a failed flush, advance `seg_end` past it, keep `durable_*` frozen, and send only records past `written_next[r]`; re-send the failed flush's records once. (b) Map each segment's data sectors once with FIBMAP (P5). A flush is durable when every one of its data sectors has a matching S record with b1 clear, whatever `fsync` returned. (c) New HUD and panel state `MS META ERR`. RUNBOOK: treat it as a red line, raw image mandatory. | IF7 |
| **F2** | **Incremental creation.** (a) A failed creation step that did not cross a cluster boundary (`st_blksize`, P4) is retried in place, as flushes are. Only a failed allocating step stops the file's growth. (b) Tick flushes may use any segment's confirmed prefix: bytes below its last `fsync`-confirmed size, minus 40,960. (c) A file whose growth stopped stays usable up to its confirmed prefix. | IF4, TE6 |
| **F3** | **Cap and margin.** Count only completed (or prefix-usable) segments towards the 32 cap, and budget abandoned-file space in the A3 free-space check. Keep one segment ready and one in creation. | IF4, IF8 |
| **F4** | **Escape a bad FAT sector.** When the S records show the abandon was caused by a FAT-area sector, skip the 10 s wait and retry at most once per tick, under a per-run attempt budget. | IF8 |
| **F5** | **Preemption holder.** Add the hook-S branch of section 3 (`pre_cls0`, `pre_wrk` into the SC record's reserved bytes), and give N1, N1m and H10 an actor. | A1-OE3 (reopened) |
| **F6** | **Stage 3.** The 8.5 error test with about 120 sporadic failures must run with a modelled stick speed of 25-300 KB/s, against **both** the flush and the creation path. Add VFAT-FI schedules for a persistently failing FSINFO sector, directory sector and allocator FAT sector. Pass condition: every record whose data sectors completed is in the raw image, and no hold exceeds 114.7 s. | IF4, IF7, IF8 |

Not blocking: IF1 (re-send EVENT and KMSG until durable), IF3 (state the
`head_regress` resync in 4.3 and turn REC red), IF6 (pair by time when
the 16-bit link misses), OE5 (wider annotation window), OE7 (`fadvise`
instead of `drop_caches`, or time it), UL6 (row WB).

---

## 7. Attacks attempted that found nothing (or only notes)

| Attack on the preallocation path | Result |
|---|---|
| Preallocated size disagrees with the on-disk chain through a **reported** error. `AS_EIO` on the block device is one flag, consumed by the first waiter (S7). Could a flush's `fsync` consume a creation's FAT error? | No. Within a tick each creation `write()` is followed by its own `fsync` (DESIGN:879-885). A `pdflush` write of the dirty FAT buffer in that gap sets the flag, and the creation's `fsync` consumes it. A short or failed creation `write()` that skips its `fsync` leaves a dirty FAT buffer that the next flush's `sync_blockdev` writes. If that fails, the flush rewinds harmlessly, and the buffer belongs to an abandoned file. |
| Steady flushes read the FAT after `drop_caches` drops the block device's FAT pages | Only on a cluster-cache miss: a segment of more than 8 fragments (P2), possible on a fragmented stick (UNVERIFIED). These are reads, not writes. A read error fails the flush, which is retried. A FREE entry would panic, but only over a silently lost FAT write (R11). |
| A rewind lands inside PAD; a torn flush; a retry shorter than the failed flush | Every PAD sector is a complete CRC-valid chunk. A torn chunk fails its CRC and the scan resyncs at the next 512-byte header. A stale tail is a duplicate (IF1 note). |
| The stick fills during preallocation | Prevented by A3. Reaching it would trigger a full FAT scan (OE2 residual). Abandoned files add space (F3). |
| A transient directory or FSINFO write failure during a flush | Benign. The next `fsync` re-reads (S8) and rebuilds from memory (S4, S6). Unsynced edits in the directory sector cannot exist at that point, because creation's `open` is always followed by its FILEHDR `fsync` in the same step. |
| `drop_caches` drops ramfs or initramfs pages, including executables | Ramfs pages stay dirty (`__set_page_dirty_no_writeback`), and `invalidate_mapping_pages` skips dirty pages (`mm/truncate.c:300-301`). |
| A takeover while the old worker is inside a creation step | Both processes take `lock_fat` and `lock_super` in turn. The new worker never touches the old worker's files, and the old worker dies at its next return to user mode. Same as IF2. |
| A printk storm from Memory Stick errors on the framebuffer console | The buffer layer is `printk_ratelimit`ed (`fs/buffer.c:443-447`, `:135-140`), and the driver's `DBG` is compiled out. |

---

## 8. UNVERIFIED items this report depends on

1. Whether Memory Stick write errors occur at all in this setup, sporadic
   or persistent, and whether a single logical sector can fail
   persistently (IF4, IF7, IF8). The recovered `kmsg.txt` shows none.
2. The stick's sustained speed for single-sector PIO writes. The design
   assumes about 52-300 KB/s. IF4's ruling holds at or below about
   100-150 KB/s, and TE6 needs about 21-27 KB/s or less.
3. The collector's start time and the thread's start time (TE6, TE1).
4. The cost of `drop_caches` on this CPU (OE7).
5. The directory-slot layout of PSCLOG (IF7: same sector for consecutive
   segments).
6. The syscon's behaviour after a Nop (UL6).

---

## Appendix A. Model behind the IF4 numbers

The model is a discrete-time simulation of DESIGN 4.3, 4.4 and 4.6 as
written:

- **Ticks.** Each tick lasts 0.23 s plus (flush bytes + creation step
  bytes) / stick speed.
- **Records.** 7,123 B/s (DESIGN:1100), into a 2 MB segment
  (2,097,152 − 1,536 B usable). The flush per tick is
  max(1,536, backlog), capped at 40,960.
- **Failures.** Failure events are Poisson in time, at 98 per 1,800 s.
  Every I/O in a tick that contains an event fails.
- **Flush failure.** The backlog grows; nothing is lost.
- **Creation (r3 as written).** A FILEHDR step, then 8 KB steps while
  the active has room, 64 KB steps while holding. Any failed step
  abandons the file. The next attempt starts at least 10 s after the
  failure.
- **Switch and hold.** The worker switches when the active has under
  40,960 B free and a spare is ready. Otherwise it holds, with no
  flushes. Hold time beyond 114.7 s counts as lost.
- **Runs.** 200 runs of 1,800 s each.

**Variants.**
- "In-place": a failed step that does not cross a 32 KB cluster boundary
  is retried, not abandoned.
- "2 spares": creation continues until two segments are ready.
- "Prefix-usable": confirmed creation bytes become flush capacity at
  once.

| Variant | 25 KB/s | 52 KB/s | 100 KB/s |
|---|---|---|---|
| r3 as written: mean lost per 30 min | 1,334 s | 743 s | 131 s |
| In-place only | 1,272 s | 396 s | 23 s |
| In-place + 2 spares | 1,265 s | 296 s | 10 s |
| Prefix-usable + in-place (F2) | 0 s | 0 s | 0 s |

With no failures every variant loses 0 s at every speed, so the
mechanism is the creation policy under errors, not the record rate.
