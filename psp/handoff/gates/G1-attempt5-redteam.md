# Gate G1, attempt 5: red team report

Artifact under review: `design/DESIGN.md` revision 4 (2,050 lines) and
`design/RUNBOOK.md` revision 4 (457 lines), both 2026-10-05, for G1 round 5.
Reviewer role: G1 red team, attempt 5. Fresh context. I did not write the
design or any earlier gate report.
Scope: WORKFLOW.md Amendment A1 applies (round 5).
Date: 2026-10-05.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding, 9.6 included), `WORKFLOW.md` (including Amendment A1),
`recon/syscon.md`, `recon/input.md`, `recon/build.md`, `recon/image2008.md`,
`gates/LOG.md`, `gates/G1-attempt4-review.md`, `gates/G1-attempt4-redteam.md`,
`design/DESIGN.md`, `design/RUNBOOK.md`.

Method:
- Source was only read, in `/home/ubuntu/psp/build/linux`. Nothing was written
  in either kernel tree. After the work, `sha256sum -c --quiet
  gates/baseline-tree.sha256` printed nothing (exit 0), and
  `git -C work/linux status --porcelain` was empty.
- Every vfat, block-layer and driver claim below was checked in this tree:
  `fs/fat`, `fs/vfat`, `fs/buffer.c`, `fs/sync.c`, `fs/fs-writeback.c`,
  `fs/block_dev.c`, `mm/filemap.c`, `mm/fadvise.c`, `kernel/printk.c`,
  `kernel/sched.c`, `drivers/block/ms_psp.c`, `arch/mips/psp/ipl_sdk/memstk.c`,
  `drivers/video/pspfb.c`, `drivers/video/console/fbcon.c`.
- One disassembly, inside `psp-build:bullseye` with `/home/ubuntu/psp`
  mounted read-only and output to my scratchpad: uClibc's `syscall()` and
  `posix_fadvise()` from `staging_dir/usr/lib/libc.a` (section 7).
- A discrete-time simulation of the revision-4 segment rules was run in my
  scratchpad. Its model is in Appendix A so the numbers can be reproduced
  without the script.
- "DESIGN:n" and "RUNBOOK:n" are line numbers in the artifact as it stands
  today. Kernel paths are relative to `/home/ubuntu/psp/build/linux`.
- Anything the source cannot settle is marked **UNVERIFIED**.

---

## Verdict: FAIL

One scenario is **BLIND** and in scope under A1: **IF9**, a bad *data*
region inside a prepared segment file. Revision 4 removed the old rule
"switch to the next file after three failed flushes". Now the collector
crosses a bad region at the speed of its normal flushes, about 2 KB per
0.23 s tick. A region of 1.5-2 MB therefore takes about 3-4 minutes to cross.
During that time nothing reaches the stick. The kernel panel says
`PSC STALL`, and the runbook's final check (D8) tells the operator to pull
the battery before the crossing ends. If input dies early in that window,
the onset, the post-death script and every record after the region began are
lost. The fix is the rule revision 3 already had, applied to data-sector
errors (section 6). In my simulation it removes the loss completely.

Two scenarios are **AMBIGUOUS** and need fixes:
- **IF4** (sporadic errors), at the slow end of the design's own stick-speed
  range only.
- **IF10** (new): the decoder as specified merges files from earlier boots
  of the same build. The runbook allows such rehearsal files to stay on the
  stick.

Three Amendment-A1 scenarios rule **SPOILED-DETECTED**: the FSINFO sector
(IF7a), the `PSCLOG` directory sector (IF7b), and the FAT sector at the
allocator (IF8). The evidence that each meets A1's three conditions, and
destroys no data already on the stick, is in section 5.

Everything else is **DIAGNOSABLE**. That covers 25 of the 28 attempt-4
scenarios and 4 of my 6 new ones. A1-OE3 and TE6 are now closed.

**A correction to the record.** Attempt-4 (section 1.1 S9 and section 7)
stated that the Memory Stick driver prints nothing because "`DBG` is compiled
out". That is wrong. `drivers/block/ms_psp.c:17-22` reads `#if 1` /
`#define DEBUG 1`, so `DBG(args)` is `printk args`. Both strings are in the
baseline image (`strings vmlinux.bin`: "%s: Failed to write sector %d,
err=%d", "Failed to %s MS (%d,%d) with error of %d"). This creates a new
observer effect, OE8: every failed sector prints on the framebuffer console,
with interrupts off while it draws. It does not reverse any earlier ruling.
The design's perturbation statement should cover it (section 4, OE8).

### In plain words (for a reader still learning the system)

- **What the design does.** The kernel keeps a running log of every syscon
  (controller chip) conversation in memory "rings". The rings hold about the
  last 2 minutes. A user program (`pscol`) copies the rings to the Memory
  Stick about 4 times a second.
- **How files are written.** To avoid touching the stick's file table (the
  FAT) during the run, `pscol` first fills each 2 MB file with padding. That
  links all the file's space in the table and *confirms* it on the stick
  with `fsync`. The part of a file confirmed so far is its "confirmed
  prefix". Real data is then written only inside that prefix, so no
  file-table write is ever needed for it.
- **What went wrong.** Revision 4 promised never to overwrite a write that
  failed (good: that protects data). But it then moves forward only by the
  size of one normal write per tick. If a large stretch of the file goes bad,
  it inches through the bad stretch for minutes instead of jumping to the
  next good file. Meanwhile the in-memory rings (2 minutes) overflow, and the
  operator is told to pull the battery.
- **The three "spoiled" cases.** Each is a single bookkeeping sector of the
  stick that permanently refuses writes. The human ruled these acceptable
  losses if they are detected, shown and handled. Revision 4 does all three
  and never destroys saved data, so they pass under A1.

---

## Summary table

| ID | Group | Scenario | Attempt 4 | Attempt 5 |
|---|---|---|---|---|
| UL1 | unlisted-shape (H10) | LED read-modify-write writes back bit 4 during a suspension at S14 | DIAGNOSABLE | **DIAGNOSABLE** |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off | DIAGNOSABLE | **DIAGNOSABLE** |
| UL3 | unlisted-shape | Link stays one reply behind | DIAGNOSABLE | **DIAGNOSABLE** |
| UL4 | unlisted-shape | Valid frames, HOLD bit stuck | DIAGNOSABLE | **DIAGNOSABLE** |
| UL5 | unlisted-shape (H10) | LED operation during a suspended transaction, clean read-back | DIAGNOSABLE | **DIAGNOSABLE** (now with the holder) |
| UL6 | unlisted-shape | The Nop breaks the link with no thread command in flight | DIAGNOSABLE | **DIAGNOSABLE** (row WB adopted) |
| TE1 | timing-edge | Death at 5 s, 17 s, 36 s | DIAGNOSABLE | **DIAGNOSABLE** (any speed in range) |
| TE2 | timing-edge | Nop on a suspended thread | DIAGNOSABLE | **DIAGNOSABLE** |
| TE3 | timing-edge | Minute 14 in `fsync`, 29:50, link wrap, console blank | DIAGNOSABLE | **DIAGNOSABLE** |
| TE4 | timing-edge | Slow Nop, nested tick, preemption at outer return, H10 | DIAGNOSABLE | **DIAGNOSABLE** |
| TE5 | timing-edge | Nop between the load and store of an LED read-modify-write | DIAGNOSABLE | **DIAGNOSABLE** |
| TE6 | timing-edge | Early death while the first segment is created on a slow stick | AMBIGUOUS | **DIAGNOSABLE** |
| IF1 | instrumentation-fault | Transient write failure spanning onset | DIAGNOSABLE | **DIAGNOSABLE** |
| IF2 | instrumentation-fault | Worker killed at minute 13-14 | DIAGNOSABLE | **DIAGNOSABLE** |
| IF3 | instrumentation-fault | Reader races; head moves backwards | DIAGNOSABLE | **DIAGNOSABLE** (resync specified) |
| IF4 | instrumentation-fault | 25-35 s burst; about 98 sporadic failing ticks | BLIND | **AMBIGUOUS** (≤ ≈ 27 KB/s only) |
| IF5 | instrumentation-fault | Failed `fsync` on an allocating flush | DIAGNOSABLE | **DIAGNOSABLE** (one narrow residual noted) |
| IF6 | instrumentation-fault | Corrupt slot `seq`, forward head jump | DIAGNOSABLE | **DIAGNOSABLE** |
| IF7 | instrumentation-fault (A1 class) | Persistent refusal of FSINFO (a) or the `PSCLOG` directory sector (b) | BLIND | **SPOILED-DETECTED** |
| IF8 | instrumentation-fault (A1 class) | Persistent refusal of the FAT sector at the allocator | BLIND | **SPOILED-DETECTED** |
| OE1 | observer-effect | MS driver hang with raised preempt count | DIAGNOSABLE | **DIAGNOSABLE** |
| OE2 | observer-effect | `statfs` FAT scan | DIAGNOSABLE | **DIAGNOSABLE** |
| OE3 | observer-effect | Collector load sets the H4 start-delay exposure | DIAGNOSABLE | **DIAGNOSABLE** |
| OE4 | observer-effect | Kernel-privileged `pscol`, stray store | DIAGNOSABLE | **DIAGNOSABLE** |
| OE5 | observer-effect | Collector exit frees a mousedev client mid-walk | DIAGNOSABLE | **DIAGNOSABLE** |
| OE6 | observer-effect | Stall panel paints for minutes | DIAGNOSABLE | **DIAGNOSABLE** |
| OE7 | observer-effect | Global `drop_caches` walk with preemption off | DIAGNOSABLE (unstated) | **DIAGNOSABLE** (replaced, verified) |
| A1-OE3 | observer-effect | Who held the CPU while the thread was preempted mid-command | AMBIGUOUS | **DIAGNOSABLE** |
| **IF9** | instrumentation-fault (new; F1(a) × prefix × switch) | A data region of a prepared file refuses writes after creation | – | **BLIND** |
| **IF10** | instrumentation-fault (new; decoder) | Chunks from another boot (rehearsal files, stale tails) merged by `(ring, seq)` | – | **AMBIGUOUS** |
| **TE7** | timing-edge (new; prefix path) | Pull while the active file is still being created after a failed step: directory size ≠ confirmed prefix | – | **DIAGNOSABLE** |
| **TE8** | timing-edge (new; prefix path) | A catch-up flush ends exactly at `conf` and a creation step writes the same page in the same tick | – | **DIAGNOSABLE** |
| **OE8** | observer-effect (new) | Driver `DBG` printk storm drawn by fbcon with interrupts off | – | **DIAGNOSABLE** (unstated perturbation) |
| **UL7** | unlisted-shape (new) | Two-stage H4: a "benign" straddle at Nop k damages the syscon, death at Nop k+1 | – | **DIAGNOSABLE** (decoder note) |

---

## 1. Source facts the scenarios rest on (verified by me in this tree)

### 1.1 vfat and the block layer

| # | Fact | Evidence |
|---|---|---|
| V1 | `__fat_get_block` maps a block that `fat_bmap` finds (below `mmu_private`) and returns before allocating. It allocates (`fat_add_cluster`) only for the block at `mmu_private` that starts a cluster, and advances `mmu_private` per block. A create request for any other unmapped block calls `fat_fs_panic("corrupted file size")`. | `fs/fat/inode.c:65-72`, `:76-79`, `:83-87`, `:93` |
| V2 | `cont_prepare_write` extends nothing for a page below `mmu_private`'s page. On the boundary page it zero-fills nothing for a write starting below the boundary. Out-of-range buffers of an up-to-date page are re-marked up to date and not rewritten. | `fs/buffer.c:2084-2126`; `__block_prepare_write` `:1745-1790` (out-of-range branch) |
| V3 | **A failed `prepare_write` inside `write()` calls `vmtruncate(inode, i_size)`.** For vfat that is `fat_truncate` → `fat_free`. `fat_free` invalidates the cluster cache, walks the *on-disk* chain to the last kept cluster, and panics if that cluster's entry reads FREE. | `mm/filemap.c:2148-2163`; `fs/fat/file.c:216-283` (`:224` invalidate, `:252` walk, `:262-266` panic), `:285-301` |
| V4 | `fat_write_inode` writes the **in-memory** `i_size` and start cluster into the directory entry and then calls `sync_dirty_buffer`. | `fs/fat/inode.c:556-611` (`:590` area: `raw_entry->size = cpu_to_le32(inode->i_size)`, `:604` `sync_dirty_buffer`) |
| V5 | `file_fsync` = `write_inode_now`, then `write_super`, then `sync_blockdev`. `__sync_single_inode` uses `WB_SYNC_ALL` and propagates the `write_inode` error. | `fs/sync.c:55-76`; `fs/fs-writeback.c:153-181` |
| V6 | FSINFO is re-read with `sb_bread` and marked dirty on every `write_super` (FAT32). | `fs/fat/misc.c:40-72` |
| V7 | A failed async buffer write sets `AS_EIO`, clears the buffer's up-to-date bit and sets `PageError`. The mpage path sets `AS_EIO` too. The first `filemap_fdatawait` returns `-EIO` and clears the flag. A failed synchronous metadata write (`end_buffer_write_sync`) clears up-to-date with a rate-limited message. | `fs/buffer.c:429-452`, `:128-146`; `fs/mpage.c:82-85`; `mm/filemap.c:280-283` |
| V8 | `fat_chain_add` walks to the chain's end with `fat_get_cluster(inode, FAT_ENT_EOF, ...)` on every allocation, then writes the old last entry. The new cluster is not added to the cluster cache (the call is commented out). | `fs/fat/misc.c:78-115` (`:92`) |
| V9 | `fat_build_inode` returns an **already cached inode with the same `i_pos`** if one exists (`fat_iget`), instead of a new one. | `fs/fat/inode.c:276-296`, `:398-405`; `fs/vfat/namei.c:745-750` |
| V10 | The block-device inode that holds FAT, FSINFO and directory buffers has `i_mode = S_IFBLK`. | `fs/block_dev.c:573` |
| V11 | `stat.st_blksize` = the cluster size. | `fs/fat/file.c:310` |
| V12 | The per-inode cluster cache holds 8 runs. | `fs/fat/cache.c:16` |

### 1.2 Driver and console

| # | Fact | Evidence |
|---|---|---|
| D1 | **The Memory Stick driver's debug messages are compiled in.** `#if 1` / `#define DEBUG 1` / `#define DBG(args) printk args`. A failed sector prints "PSP MemStick: Failed to write sector N, err=-1" inside `psp_ms_write`, and then "Failed to write MS (s,n) with error of -1" in `psp_ms_transfer_bio`. There is no rate limit. Both strings are in the baseline `vmlinux.bin`. | `drivers/block/ms_psp.c:17-24`, `:272-274`, `:370-371` |
| D2 | Each failing sector is tried 10 times with `mdelay(1)` between tries, all inside `__bio_kmap_atomic` (preemption off). The first `DBG` runs inside that region, before the S record's hook point at `up()`. | `ms_psp.c:254-268`, `:304-326`, `:355-379` |
| D3 | `memstk.c`'s own messages are compiled out (`SHOW_ERR_MSG 0`). `Kprintf` is `printk`. | `arch/mips/psp/ipl_sdk/memstk.c:13-16`; `include/asm-mips/ipl_sdk/Kprintf.h:4` |
| D4 | `printk` draws through the console drivers inside `release_console_sem`, with **local interrupts disabled** from `spin_lock_irqsave(&logbuf_lock)` until `local_irq_restore` after `call_console_drivers`. | `kernel/printk.c:819-828` |
| D5 | Message level 4 (default) is below console level 7, so the lines reach the screen. `pspboot.conf` has `console=tty` and no `quiet`. `rc.sysinit` does not change the log level. | `kernel/printk.c:40-52`; `/home/ubuntu/psp/pspboot-baseline/pspboot.conf`; `extract/root2/etc/rc.sysinit` |
| D6 | `pspfb` sets `info->flags = FBINFO_FLAG_DEFAULT` (0), with software blits. So fbcon uses `SCROLL_REDRAW`, which redraws every character cell that changes on a scroll, across the whole screen. The font is 6x8 (80 × 34 cells). | `drivers/video/pspfb.c:73-76`, `:403`; `drivers/video/console/fbcon.c:2085-2089`; `.config:444,454` |

### 1.3 Other claims checked

- **uClibc `syscall()` passes seven argument slots.** Disassembly of
  `libc.a(syscall.os)`: `move v0,a0; move a0,a1; move a1,a2; move a2,a3;
  lw a3,16(sp)`, then words 20-28(sp) are copied to 16-24(sp) of a new frame.
  `syscall(4254, fd, 0, SEG−4096, 0, 4096, 0, 4)` therefore arrives as fd,
  pad, 64-bit offset in a2:a3, length at 16-20(sp), advice 4 at 24(sp), which
  is `sys_fadvise64_64`'s layout. `posix_fadvise.os` does `sra a2,a1,31`
  (the five-slot misuse the design describes). **DESIGN 7.4 and R23 are
  correct.** `mm/fadvise.c` DONTNEED invalidates whole pages from
  `(offset+4095)>>12` to `(offset+len−1)>>12`, here page 511 only.
- Hook-S preemption branch: `prev->state` is `TASK_RUNNING` for an
  involuntary switch, which is counted in `nivcsw` (`kernel/sched.c:3626-3628`),
  inside `if (likely(prev != next))` (`:3699-3707`). Verified.

---

## 2. Attempt-4 scenarios re-run against revision 4

For each scenario: what changed in r4 that touches it, what the records
contain, and the ruling.

### UL1 (H10). LED write-back of bit 4 during a suspension at S14. DIAGNOSABLE

**Unchanged mechanisms** (K6, K8, K19):
- `led_or & 0x10`;
- `lc_epc` = S14;
- `ms_delta ≥ 2`;
- S `rd_clr_or`.

**New in r4.** `pre_cls`, `pre_wrk` and `pre_tot` (SC bytes 42-46, 78;
DESIGN:225-237) now also name the task that held the CPU while the thread
was preempted.

**Ruling: DIAGNOSABLE.**

### UL2. One foreign frame toggles mouse mode off. DIAGNOSABLE

POLL `pi_flags` b3/b4, row N10 (DESIGN:1319) and D7a are unchanged.

**Ruling: DIAGNOSABLE.**

### UL3. Link one reply behind. DIAGNOSABLE

Row N2b against the template `rx[2]` (DESIGN:1311) is unchanged.

**Ruling: DIAGNOSABLE.**

### UL4. HOLD stuck with valid frames. DIAGNOSABLE

Row N11 (DESIGN:1320) is unchanged.

**Ruling: DIAGNOSABLE.**

### UL5 (H10). LED operations during a suspension, clean read-back. DIAGNOSABLE

N1m is reported with:
- the step;
- the suspension bound;
- `ms_delta` and `led_pid`;
- **(r4)** the holder `pre_*` (DESIGN:1308);
- the pre-registered harm-rate table (10.7 step 7).

The designer's statement that N1 and an LED read side effect "cannot be
separated in one run" is an acceptance I agree with: both leave identical
records.

**Ruling: DIAGNOSABLE.**

### UL6. The Nop breaks the link with no thread command in flight. DIAGNOSABLE

The attempt-4 recommendation was adopted:
- row WB (DESIGN:1322);
- the ± 2-cycle WT listing;
- "benign only if both results valid" (10.7 step 5).

See UL7 for a remaining gap in the decoder's listing.

**Ruling: DIAGNOSABLE.**

### TE1. Death at 5 s, 17 s, 36 s. DIAGNOSABLE

**What r4 changes.** The first file takes flushes one 64 KB step after its
FILEHDR (DESIGN:1020-1022). At 25 KB/s that is about 2.7 s after the worker
starts. The rings hold 114.7 s from boot, and the reader starts at the
oldest record (DESIGN:575). So the boot records are the first to be flushed,
at any speed in the design's range.

The template fallback, the WB/M/WT baseline and the early-death exception
(8.3) are unchanged.

**Ruling: DIAGNOSABLE.**

### TE2. Nop on a suspended thread. DIAGNOSABLE

`lc_epc` and `lc_r` (K8) give the P6 step with `j`. Unchanged.

**Ruling: DIAGNOSABLE.**

### TE3. Minute 14 in `fsync`; 29:50; 16-bit link wrap; console blank. DIAGNOSABLE

- D8 now also rejects `META`.
- The 16-bit links fall back to `(tick, Count)` pairing (DESIGN:1696-1697).
- A console blank is undone by any later printk (`poke_blanked_console` in
  the vt console path).
- Nothing else changed.

**Ruling: DIAGNOSABLE.**

### TE4. Slow Nop, nested tick, preemption at outer return, H10. DIAGNOSABLE

K9 and `lc_flags` b4 are unchanged. **(r4)** `pre_*` adds the holder after
the preemption.

**Ruling: DIAGNOSABLE.**

### TE5. Nop between the load and store of an LED read-modify-write. DIAGNOSABLE

The `LEDRMW` label and row LEDSPLIT are unchanged.

**Ruling: DIAGNOSABLE.**

### TE6. Early death while the first segment is created on a slow stick. DIAGNOSABLE (was AMBIGUOUS)

**Trace at 25 KB/s with a collector start at 40 s:**
1. Step 0 writes 1,536 B; step 1 writes 64 KB; then `fsync`.
2. The first flush is at about 43 s of uptime.
3. Each tick is then about 4.4 s long (≤ 40 KB flush + 64 KB step).
4. Production per tick is about 157 P records, against a drain cap of
   48 × m = 192. The backlog shrinks.
5. The P ring (4,096 entries) never laps.

The onset P/POLL records, the onset command's own result and the W records
all reach the stick.

The attempt-4 fix F2(b) is implemented as asked.

**Ruling: DIAGNOSABLE.**

### IF1. Transient write failure spanning onset. DIAGNOSABLE

**Trace.**
1. A 3 s outage hits a flush. `seg_end` passes the failed region
   (DESIGN:914-915). `durable_*` freeze, and `resend` is set.
2. Later flushes during the outage go to fresh space and fail too.
3. The first success seeks every ring back to `durable_next`
   (DESIGN:1110-1118). The records are sent once more by the capped
   catch-up.
4. EVENT and KMSG payloads stay queued (DESIGN:1118-1119).
5. A creation step caught by the outage is retried in place if it does not
   allocate. If it allocates, it stops the file's growth, and the file's
   prefix stays usable (DESIGN:976-991).

**Note.** The outage also prints two console lines per failed sector (OE8).
They are in the KMSG chunks, and the interrupts-off rendering shows as long
ticks (`c_pre`, `long_ticks`). The decoder flags an onset near a `flush fail`
EVENT (10.5).

**Ruling: DIAGNOSABLE.**

### IF2. Worker killed at minute 13-14. DIAGNOSABLE

**Trace.**
1. The supervisor detects the death within 2 s and runs the worker loop
   in-process, with no allocation (U1).
2. It creates a fresh file. The first flush comes one 64 KB step after the
   FILEHDR.
3. It seeks to `durable_next`. That also covers any flush the old worker had
   failed and not yet re-sent.

Onset and script are inside the 114.7 s rings.

**Ruling: DIAGNOSABLE.**

### IF3. Reader races; head moves backwards. DIAGNOSABLE

The attempt-4 spec note was adopted: on a `head_regress` rise the ring is
re-seeked to its head, an EVENT is written and REC turns red (DESIGN:899-901).

**Ruling: DIAGNOSABLE.**

### IF4. 25-35 s burst; about 98 sporadic failing ticks. AMBIGUOUS (only at ≤ ≈ 27 KB/s)

**Burst variant: DIAGNOSABLE.**
- During a 35 s whole-stick burst, every flush fails into fresh space.
- The creation in progress makes at most 3 in-place retries and then stops.
  Its prefix stays usable. Later attempts are abandons at least 10 s apart.
- After the burst, the re-send restores everything younger than 114.7 s.
- Space used: under 400 KB of failed regions, with two files ahead.

**Sporadic variant.** I simulated the r4 rules (Appendix A) under
attempt-4's pattern of 98 failure events per 30 min, under two failure
models:
- **whole tick:** an event fails every I/O in its tick (attempt-4's model);
- **per operation:** an event fails only the operation in progress.

| Stick speed | Mean lost per 30 min, whole tick | Runs with loss | Mean lost, per operation | Runs with loss |
|---|---|---|---|---|
| 25 KB/s | 202 s | 98/100 | 3.3 s | 13/100 |
| 30 KB/s | 0.1 s | 1/100 | 0 | 0 |
| 40, 52, 100, 300 KB/s | 0 | 0 | 0 | 0 |

Maximum holds stay at or below 32 s at every speed. Without errors, nothing
is lost down to 20 KB/s.

**Why the slowest speed loses.** The loss at 25 KB/s comes from the r4
re-send rule. The first successful flush after a failure is not counted as
durable: its records are re-sent after the seek back (DESIGN:1110-1116). So
every failure costs two flushes of durability, plus a catch-up. At 25 KB/s
the stick is already about 83 % busy (the design needs ≈ 20.8 KB/s, R8).
With the re-send cost switched off in the model, the loss at 25 KB/s falls to
3-6 s.

**Why AMBIGUOUS and not BLIND.**
- Across the rest of the design's stated range (30-300 KB/s) r4 is lossless
  under both models. That is a large improvement on attempt-4's
  "BLIND ≤ 100-150 KB/s".
- The loss at 25 KB/s depends strongly on how failures are modelled
  (3 s or 202 s).
- The designer's claim of zero loss (14.4) rests on attempt-4's model, which
  did not have r4's re-send rule. I disagree with that claim at 25 KB/s.
- The design's own Stage 3 test (8.5 "Errors", F6) runs ≈ 120 sporadic
  failures at 25 KB/s with the pass condition "no record lost". It would
  expose the loss before the run, if the harness models failures as whole
  ticks.

**Fix needed:**
1. **Range-based durability.** Make the first successful flush after a
   failure durable for its own records. Re-send only the failed regions'
   records, tracked as `seq` ranges, instead of discarding the success and
   re-sending everything from `durable_next`.
2. **A throughput gate in STICK.** STICK passes only when the measured
   sustained write speed of the first file's 64 KB steps is ≥ 35 KB/s.
   Otherwise abort at 3:00, which costs no run.
3. **State in R8** the minimum stick speed at which the IF4 pattern is
   lossless.

### IF5. Failed `fsync` on an allocating flush. DIAGNOSABLE (one narrow residual)

**The core claim holds.** I re-traced the envelope (V1, V2): every flush ends
at or below `conf` ≤ `mmu_private`, so `__fat_get_block` returns at
`fs/fat/inode.c:68-72`. A flush never dirties a FAT sector.

**Residual found (note, not a ruling).** The kernel truncates a file
implicitly when a `write()` fails in `prepare_write` (V3). The design's
statement "never truncated" (DESIGN:986) is about the collector's own calls
and does not cover this. A panic needs all of the following:
1. A stopped file B whose failed allocating step left an on-disk chain
   L → c with c FREE. That happens when L's FAT entry and c's sit in
   different FAT sectors and only c's sector write failed. It is 1 in 128
   for a transient error, but certain for the first allocation into a
   persistently bad sector (IF8).
2. B later becomes active as a prefix.
3. A flush into B misses the 8-run cluster cache (V12), which needs a
   fragmented B.
4. That miss meets a FAT read error.

Then `fat_free` walks to c and calls `fat_fs_panic`, and `/ms0` goes
read-only (`PSC MS RO`; panel photographs from then on).

The chain needs two independent errors plus fragmentation, so I do not rule
it as its own scenario. **Recommendation:** list it in R11, and do not
promote a stopped file to prefix-usable when its failed step's S records show
a FAT-area write error on a sector other than the one holding the file's
last confirmed entry.

**Ruling: DIAGNOSABLE.**

### IF6. Corrupt slot `seq`, forward head jump. DIAGNOSABLE

Skip-and-count (3.5) is unchanged. The `(tick, Count)` pairing fallback was
adopted (DESIGN:1696-1697).

**Ruling: DIAGNOSABLE.**

### IF7. Persistent refusal of FSINFO (IF7a) or the `PSCLOG` directory sector (IF7b). SPOILED-DETECTED

This is exactly the Amendment A1 class. The full trace and the evidence for
the three conditions are in section 5.

**Ruling: SPOILED-DETECTED.**

### IF8. Persistent refusal of the FAT sector at the allocator. SPOILED-DETECTED

This is the A1 class. See section 5.

Note: in this case r4 also keeps full coverage. That is useful even though A1
does not require it.

**Ruling: SPOILED-DETECTED.**

### OE1. MS driver hang with a raised preempt count. DIAGNOSABLE

The marker and panel are unchanged (K20, K30). The exposure is higher in r4
(two files ahead, 64 KB start-up steps, fast retries), and the design states
it (7.5).

**Ruling: DIAGNOSABLE.** I agree with the accepted residual R12.

### OE2. `statfs` FAT scan. DIAGNOSABLE

There is no `statfs`. ENOSPC is excluded by 256 MB free against ≤ 189 MB of
worst-case use (DESIGN:1005-1010; RUNBOOK:167-169).

**Ruling: DIAGNOSABLE.**

### OE3. Collector load sets the H4 start-delay exposure. DIAGNOSABLE

K12 is unchanged and measures the delay and the collector's share per
wake-up.

**Ruling: DIAGNOSABLE.**

### OE4. Kernel-privileged `pscol`, stray store. DIAGNOSABLE

The guards are unchanged. I accept R16.

**Ruling: DIAGNOSABLE.**

### OE5. Collector exit frees a mousedev client mid-walk. DIAGNOSABLE

The annotation now covers the takeover-to-PROCS window (10.7 step 5).

**Ruling: DIAGNOSABLE.**

### OE6. Stall panel paints for minutes. DIAGNOSABLE

N1p and `lc_flags` b5 are unchanged.

**Ruling: DIAGNOSABLE.**

### OE7. Global `drop_caches` with preemption off. DIAGNOSABLE (replaced)

`drop_caches` is gone. The read-back drops one page with `sys_fadvise64_64`
through `syscall()`. I verified both the argument layout (section 1.3) and
that DONTNEED touches only page 511. No unbounded non-preemptible walk
remains.

**Ruling: DIAGNOSABLE.**

### A1-OE3. Who held the CPU while the thread was preempted mid-command. DIAGNOSABLE (was AMBIGUOUS)

**The fix, K35** (DESIGN:672-685), is the attempt-4 F5 branch:
- condition `prev == psc_jp_task && prev->state == TASK_RUNNING &&
  psc_t_busy_p`;
- per-switch accumulation of `pre_wrk` (the collector's part);
- `pre_cls`: first preemptor in the low nibble, last holder in the high
  nibble;
- `pre_tot` and `pre_flags`;
- copied into the SC record under `pre_seq`.

**N1 trace.** An onset with `ms_delta = 0` and `wn = 0` now carries:
- who preempted the thread;
- who last held the CPU;
- the total preempted time;
- the collector's exact part of it.

S5 can therefore say whether the collector held the CPU.

**Checks I made:**
- **Involuntary switches only.** `nivcsw` counts only involuntary switches
  (`kernel/sched.c:3626-3628`).
- **`Syscon_cmd` never sleeps.** So the state test is exact.
- **The two accounting modes never overlap.** A preempted thread is never
  woken, so `wk_pending` and `pre_on` are never set at the same time
  (`try_to_wake_up` skips a task on the run queue).

**Ruling: DIAGNOSABLE.**

---

## 3. New scenarios

### IF9. A data region of a prepared segment file refuses writes after its creation (instrumentation-fault; F1(a) × prefix × switch). **BLIND**

**Premise.** A logical range of data sectors inside a file that creation
already filled with PAD and confirmed starts refusing writes later. Metadata
sectors and the rest of the stick keep working. Examples:
- a flash erase block the card's controller can no longer remap;
- a block-mapped controller that fails a 1-4 MB aligned range.

Two cases:
- **Range inside the active file.** It may also cover the next file, because
  files are allocated one after another from the allocator's sequential
  search (`fs/fat/fatent.c:455`).
- **Range inside a ready file.** The failure starts when that file becomes
  active.

**Is it in scope?** This is not the A1 class: it is data, not metadata, and
not a single sector. A1 kept everything else in scope. The premise is
UNVERIFIED, with the same standing as A1's own premise. The design itself
plans for "a bad region" (R8, DESIGN:1847) and still lists
"R36 retry in place on bad clusters → switch to the spare after three
failures" (DESIGN:1898). That rule was removed in r4: "The r3 'switch after
three failed flushes' is gone: flushes never meet the same sectors twice"
(DESIGN:1125-1126).

**Trace (region of R bytes starting at `seg_end` at time t0).**
1. **Flush n fails.** `psp_ms_write` breaks at the first failing sector after
   10 tries (D2). `seg_end += length` "whatever the result" (DESIGN:914-915).
   `resend` is set and `durable_*` freeze (DESIGN:1104-1110).
2. **The next flushes fail too.** The drain is complete every tick, so each
   flush holds only one tick's new records: about 2 KB (0.23-0.28 s at about
   7.6 KB/s, rounded up to 512). `seg_end` therefore advances about 2 KB per
   tick, roughly 8-9 KB/s. Crossing R = 2 MB takes about 4 minutes, and
   R = 4 MB (two contiguous files) about 8 minutes.
   - The collector never reacts. The failing sectors carry S `flags` b1 with
     b7 clear (data), so META does not apply (4.7).
   - Takeover does not apply, because the worker keeps reading (DESIGN:1148-1149).
   - No escape rule exists.
3. **Display.**
   - After 3 s the panel shows `PSC STALL` with `DUR` rising.
   - HUD line 6 is red (errors in the last 10 s).
   - The console prints about 2-4 `DBG` lines per tick (OE8).
4. **Operator, input healthy.** RUNBOOK C4.3: watch for 90 s, no recovery.
   C4.4: carry on, photographing the panel every 5 minutes.
5. **Operator, input dies at T_death in the window.** Section D takes about
   100 s, then D8: 30 s hands off and a 5 s check. The check fails (panel,
   red line 6). D8(c): wait up to 90 s. The extra 45 s is granted only if
   `CATCHUP` shows, and it does not, because the drain is complete. Then
   pull. So the pull comes at about T_death + 225 s (RUNBOOK:355).
6. **What survives.**
   - **If the crossing ends before the pull:** the first success re-sends
     from `durable_next`. The P and POLL rings keep only the last 114.7 s,
     so everything from t0 to (crossing end − 114.7 s) is lost (counted).
     The W ring (1,280 s) survives.
   - **If the pull comes first:** nothing after t0 reaches the stick at all.
     That includes W, the onset, the post-death script, STATS and KMSG.

**Outcomes for R = 2 MB (crossing ≈ 235-275 s):**

| Death time | What the stick holds | S2 / S4 | H6 vs H7 |
|---|---|---|---|
| t0 to t0 + ≈ 10-50 s | Nothing after t0. Panel photographs only (point samples of the last P08, W, stage, marker) | **fail** | **lost** |
| t0 + 50 s to t0 + 120 s | W records across onset; P/POLL only from t0 + 120 s (part of the script) | onset window lost | partly |
| after t0 + 160 s | complete | ok | ok |

With R = 4 MB the all-lost window lasts about 4 minutes.

**What r4 records that would have told it apart:** each failed flush's S
records (sector, b1, b7 clear), UHB `write_errs` and `last_errno`, and EVENT
`flush fail`. All of them sit in the rings with the data and are lost with
it, except the panel's marker line.

**Simulation** (Appendix A, no other errors; region inside the second file;
loss counted only at the region's end, i.e. with no early pull):

| Region | 52 KB/s, as written | 100 KB/s, as written | 300 KB/s, as written | Any speed, switch after 3 failed data flushes |
|---|---|---|---|---|
| ≤ 768 KB | 0 s | 0 s | 0 s | 0 s |
| 1 MB | 5 s | 0 s | 0 s | 0 s |
| 1.5 MB | 64 s | 49 s | 43 s | 0 s |
| 2 MB | 117 s | 99 s | 88 s | 0 s |

These numbers are lower bounds. They assume the operator does not pull
during the crossing, and step 6 shows the runbook does pull.

**Ruling: BLIND** (a death early in the crossing of a region ≳ 1.5 MB loses
the onset, the post-death script and the W trigger record).

**Fix needed** (cheap; it uses records the worker already drains):
- After 3 consecutive failed flushes whose S records show a **data-sector**
  write error (b1, b7 clear) while metadata writes in the same ticks
  succeeded, close the active file. Switch to the next complete or
  prefix-usable file, and mark the rest of the old file bad (EVENT
  `region bad <name> <seg_end>`).
- If the new file fails the same way within 3 flushes, switch again.
- With no usable file, hold (the rings buffer) and create at 64 KB per tick.
  Creation never writes into an old file, so the bad range is never met
  again.
- Alternatively, double the skip within the file on each consecutive failure
  (2 KB, 4 KB, 8 KB, …). That reaches the end of a 2 MB region in about
  10 flushes.
- Correct the stale R36 row in 11.3 and the R8 sentence "costs one failed
  flush per tick that meets it".
- Add a VFAT-FI schedule to Stage 3: a 2 MB data range of a ready file
  refusing writes after its creation.
  Pass condition: no hold or crossing longer than 114.7 s.

### IF10. Chunks from another boot are merged into this run (instrumentation-fault; decoder). AMBIGUOUS

**Premise.** The runbook expects rehearsal files from earlier boots of this
same build to stay on the stick:
- RUNBOOK:171-172 (A4): "If the stick already has a folder `PSCLOG` ...
  leave it";
- RUNBOOK B3 and DESIGN 8.2 line 1: `rrr` is "001 unless earlier rehearsal
  files are on the stick".

E1 copies the **whole** `PSCLOG` folder (RUNBOOK:387).

**Trace.**
1. The decoder's input is "the copied `T*.BIN` files", and "Records from all
   files merge by (ring, `seq`)" (DESIGN:1622, :1656). `seq` restarts at 0
   on every boot, so a rehearsal boot's P record 1234 and this run's P
   record 1234 collide.
2. "duplicates by (ring, `seq`) are removed" (DESIGN:1693). One of the two
   is dropped silently. Which one is unspecified. The timeline then mixes
   two boots.
3. A rehearsal file that is not 2 MB and holds RECS also triggers
   `RAW IMAGE REQUIRED` (DESIGN:1658-1663).
4. The `--raw` scan groups chunks "under the nearest FILEHDR"
   (DESIGN:1657). Nothing says only this run's FILEHDRs are kept.
5. **A second source of foreign chunks, inside this run's own files.**
   - After a failed creation step, the in-memory `i_size` is `conf + k`.
   - The next flush's `fsync` writes that size into the directory entry
     (V4).
   - So the copied file includes `[conf, conf + k)`. For a non-allocating
     step, those sectors were never rewritten with PAD, and they hold
     whatever was there before.
   - If an earlier run's deleted files used those clusters, CRC-valid PSCK
     chunks from that boot sit inside this run's file. The decoder's scan
     (every 4-byte offset, DESIGN:1653-1655) accepts them.

**What the analyst gets.** All of this run's records are present, but the
specified tool merges foreign records into them without saying so. For
example:
- an onset candidate O1 or O2 can be moved by a rehearsal's frames;
- a healthy template can absorb another boot's frames.

A careful analyst can separate the boots by file name, but the tool as
specified does not.

**Ruling: AMBIGUOUS.**

**Fix needed:**
1. Decode only files whose FILEHDR `run` equals the run being analysed. By
   default that is the highest `rrr`; it can also be named on the command
   line. Exclude other runs from the "not 2 MB" raw trigger.
2. Within a file, accept chunks only below its confirmed extent:
   - the last `conf` recorded in UHB `seg` for that file, or
   - the region below the file's last `stop <name> <conf>` EVENT.
3. In `--raw` mode, accept a chunk only inside the clusters of this run's
   files (from the FAT when it is intact), or else only when its records'
   `(tick, Count)` continue this run's timeline.
4. Report a `(ring, seq)` duplicate with different content as a
   **conflict**. Never drop it silently.
5. Optionally add a per-boot 32-bit nonce to FILEHDR and to the UHB's first
   word.

### TE7. Pull while the active file is still being created, after a failed step: directory size ≠ confirmed prefix (timing-edge; prefix path). DIAGNOSABLE

**Shape.** The active file is incomplete. That happens at start-up, after a
takeover, or after a switch to a prefix (UHB b25, DESIGN:1017-1018). A
creation step's `write()` succeeds but its `fsync` fails (transient). It is
non-allocating, so it is retried in place next tick (DESIGN:980-983). Before
the retry, the next tick's flush `fsync`s the inode with
`i_size = conf + k` (V4). Then the battery is pulled.

**Trace.**
- **Records.** Every flush lies below `conf` (DESIGN:1012-1014). All
  durable records are intact on the stick.
- **The tail.** The directory entry says `conf + k`, so the copy contains
  `[conf, conf + k)`: stale sectors, or PAD if the failed write partly
  landed.
- **Copy and decoder.**
  - The file holds RECS and is not 2 MB, so the decoder demands
    `--raw` (DESIGN:1658-1663).
  - RUNBOOK E1 step 5 tells the operator one smaller file is normal "(the
    file that was being prepared at the pull)" (RUNBOOK:390-391), so the
    operator makes no image at once.
  - E4 keeps the stick untouched until the agents confirm (RUNBOOK:424-426),
    so the image can still be made.
- **Allocating variant.** If the failed step was allocating and its FAT
  write failed, the directory size can exceed the on-disk chain. macOS may
  then fail to copy the file. "A file failed to copy" makes E2 mandatory.
  No record is lost.

**Ruling: DIAGNOSABLE.**

**Notes:**
- DESIGN 14.2's sentence "the file being created holds none" is false when
  the file being created is also the active one. RUNBOOK E1 step 5 should
  say the image will be requested if that smaller file holds records.
- The stale tail is the IF10 contamination route; its fix 2 covers it.

### TE8. A catch-up flush ends exactly at `conf`, and a creation step writes the same page in the same tick (timing-edge; prefix path). DIAGNOSABLE

**Shape.**
- The active file is still being created, and `seg_end + 40,960 = conf`.
  A catch-up flush of exactly 40,960 B is allowed (DESIGN:1012-1014) and
  ends at `conf`.
- `conf ≡ 1,536 (mod 4,096)` (FILEHDR 1,536 B, then whole-page steps).
  So the flush's last page holds blocks 0-2 of a page whose blocks 3-7 the
  creation step writes in step 8 of the same tick.

**Trace in this tree.**
1. **Flush.** On the shared page, `cont_prepare_write` takes the
   boundary branch: `zerofrom` = 1,536 and `offset` = 0, so `zerofrom`
   becomes 0 and nothing is zeroed. Blocks 0-2 are mapped (below
   `mmu_private`). Nothing is allocated (V1, V2). Its `fsync` writes blocks
   0-2.
2. **Creation step.** Same page, `from` = 1,536. Blocks 3-7 get `get_block`
   with create, at `mmu_private`. Within the cluster this is
   non-allocating; at a cluster start it allocates (V1). Blocks 0-2 lie
   outside the range and are only re-marked up to date (V2).
3. **If the flush failed on that page:** blocks 0-2 are not up to date, have
   `PageError`, and are not rewritten. `seg_end` has already passed them
   (F1(a)). The creation's `fsync` writes only its own dirty buffers, and
   its error stays its own, because the flush's `fsync` already consumed
   `AS_EIO` (V7).
4. **If the creation failed:** the flush's data is unaffected, since it was
   written and waited for first (4.3 steps 7-8).

**Ruling: DIAGNOSABLE.** Nothing allocates, nothing is overwritten, and each
error is attributed to the operation that caused it. The design's ordering
argument (DESIGN:1040-1044) holds at the exact boundary.

### OE8. The driver's `DBG` printk storm is drawn by fbcon with interrupts off (observer-effect). DIAGNOSABLE (unstated perturbation)

**Mechanism** (D1-D6). Every failed Memory Stick transfer prints two
unrate-limited lines:
- one from inside `psp_ms_write`, in the `kmap_atomic` region with
  preemption off;
- one from `psp_ms_transfer_bio`.

`printk` draws them through fbcon with **local interrupts disabled**
(`kernel/printk.c:819-828`). pspfb has no acceleration, so fbcon redraws every
changed cell on each scroll. The console cursor sits in the bottom band, as
RUNBOOK:105 notes, so every line scrolls the whole screen.

**Effect, per failing tick:**
- 2 lines per failed bio: the flush, the directory sector, FSINFO and the
  creation step can each fail;
- 10 tries × (command + 1 ms) of non-preemptible time before the first line;
- each line's rendering with interrupts off (duration UNVERIFIED; my estimate
  is 1-10 ms for a 6x8 redraw of the changed cells).

**Who is exposed:**
- IF1/IF4 transient errors: several lines per failing tick;
- IF9 crossing: about 9-17 lines/s for minutes;
- the A1 persistent cases: ≥ 2 lines per `fsync`, about 10-20 lines/s.

**Consequences:**
1. **Timing.** Interrupt-off stretches delay timer ticks, and ticks over
   4 ms are lost. That shifts the Nop in wall time and delays the thread.
   DESIGN 7.1 "Interrupt state: None changed" (DESIGN:1361) and "`printk`:
   One line at init" (DESIGN:1371) are true of the design's own code, but
   the collector's error path now creates interrupt-off time the statement
   does not mention.
2. **Display.** Console text overwrites the left half of the screen (about
   45 characters, x < 270 px) at every scroll.
   - The HUD is redrawn in step 9 of each tick, after that tick's
     `fsync`s, so it is clean for most of the 200 ms sleep.
   - The kernel panel is painted once a second at an arbitrary phase. Its
     title (`PSC MS META`, `PSC STALL`), at the left, is overwritten within
     ≤ 0.2 s by the next tick's lines.

**What is recorded:**
- **Long ticks.** The interrupt-off time shows as `c_pre`, `long_ticks` and
  `c_pre_max` (T1).
- **The first line.** It is inside the S record's `[c_on, c_off]`, because
  the S record is written before `up()` (DESIGN:506-507).
- **The text.** It reaches the KMSG chunks (4.3 step 3).
- **Attribution.** The time is charged to the worker in `pre_*`/`wk_*`, and
  the decoder flags onsets near `flush fail` EVENTs (10.5).

The effect can therefore be attributed after the run, by proximity.

**Ruling: DIAGNOSABLE.** The perturbation is unstated, and the panel's
legibility in error states is reduced (relevant to A1 condition 2; section
5).

**Recommendations:**
1. At start, `pscol` sets the console log level to 4 with
   `syslog(8, NULL, 4)`. The driver's level-4 `DBG` lines and the
   rate-limited buffer warnings then stay off the console, while level-3
   errors (FAT panic, "Buffer I/O error") still show. Everything still
   reaches `/proc/kmsg` and the KMSG chunks.
2. Add the error-path printk to 7.1, 7.5 and section 11, and have VFAT-FI
   keep the driver's `DBG` path.
3. Correct attempt-4 S9 in the record.

### UL7. Two-stage H4: a "benign" straddle at Nop k leaves the syscon damaged; input dies at Nop k+1 (unlisted shape). DIAGNOSABLE (decoder note)

**Shape.** Dossier 9.6 places deaths at a 5 s boundary. The syscon's
internal state is UNKNOWN (recon §5.1). A Nop that straddles a thread
command at a point the code calls benign (P0, P1 or P7) could leave hidden
state, with both results valid. The next Nop, at 1250(k+1), with or without a
thread command in flight, then trips it.

**What r4 records:**
- the W record at 1250k: `t_busy` b0, `epc`/`lc_epc` step, the Nop's own
  frame;
- its P record: `wn = 1`, valid;
- the W record at 1250(k+1);
- the 6.3 placements.

**How the decoder classifies it.** It reports H4 at Nop k+1 (if that Nop
straddled), or WB (if not). The k straddle is counted **benign**, because
both results were valid (10.7 step 5). It is not listed by WB's ± 2-cycle
listing, which lists only Nops whose own reply was invalid
(DESIGN:1322). The raw ± 30 s window contains both stages, so an analyst can
see them.

**Ruling: DIAGNOSABLE.**

**Recommendation:** in every onset report, list all WT records within ± 2
cycles, including straddles with valid results, with their step. Add the
pattern "straddle at k, onset at k+1" as a reported candidate.

---

## 4. Ruling notes on OE8 for the earlier scenarios

OE8 changes no earlier ruling:
- IF1, IF4 (burst) and IF9 already involve write errors; OE8 adds interrupt-off
  rendering, which is recorded.
- The self-test and the healthy run print nothing, because no errors occur.

It does mean the earlier claim "the driver prints nothing" must not be
reused.

---

## 5. SPOILED-DETECTED rulings (Amendment A1)

A1's three conditions:
1. the design detects the condition from its own records within 30 s;
2. it shows the condition on the kernel panel and the HUD;
3. the runbook says what to do (raw image mandatory, run not counted).

A1 also requires that the design never destroys data already on the stick.

| Scenario | 1. Detected from own records ≤ 30 s | 2. Panel and HUD | 3. Runbook | No destruction of data already on the stick |
|---|---|---|---|---|
| **IF7a** FSINFO refuses writes | See note 1 below. **About 1-2 s.** | See note 4. | See note 5. | See note 6. |
| **IF7b** `PSCLOG` directory sector refuses writes | See note 2. **About 1-2 s.** | As IF7a. | As IF7a. | See note 7. |
| **IF8** FAT sector at the allocator refuses writes | See note 3. **About 5 ticks** after the first write of that sector. | As IF7a. | As IF7a. | See note 8. |

**Notes to the table:**

1. **IF7a detection.**
   - FSINFO is re-read with `sb_bread` and marked dirty on every `fsync`
     (V6); `sync_blockdev` writes it (V5).
   - Its page is in the block device's page cache (`fs/block_dev.c:573`
     `S_IFBLK`), so S `flags` b7 is set (DESIGN:509-517).
   - It is written once per flush `fsync` and once per creation `fsync`, so
     at least 5 failing writes come within ≤ 3 ticks, with the worker's data
     writes succeeding (DESIGN:1155-1164).
2. **IF7b detection.**
   - `fat_write_inode` re-reads the sector, which is not up to date after
     the failure (V7), and writes it synchronously on every `fsync`, because
     every `write()` dirties the inode (V4, V5).
   - The b7 tag applies as for FSINFO. Same rule and timing.
3. **IF8 detection.**
   - Each creation attempt's step 0 allocates at `prev_free + 1` inside the
     bad sector and fails in `sync_blockdev`.
   - The abandon is metadata-caused with data writes OK, so the next
     attempt follows at the next tick (DESIGN:992-996).
   - Five failing writes come within about 5 ticks.
4. **Display (all three).**
   - The panel shows `PSC MS META` whenever `meta_sector ≠ 0`, painted by
     the timer interrupt even if the worker stalls (DESIGN:612, :631, :636,
     :1166-1169).
   - HUD line 6 shows `MS META ERR hhhhhhhh` in red (DESIGN:1507).
   - **Caveat (OE8):** the driver's printk lines overwrite the left part of
     the screen at each failing `fsync`. The HUD is redrawn right after them
     in each tick, so line 6 stays legible for most of each tick. The panel
     title is legible for at most about 0.2 s per second. I judge condition
     2 met, through the HUD and the panel's persistent right-hand part and
     border. The console-level fix in OE8 would make it robust.
5. **Runbook (all three).**
   - RUNBOOK C4.2 (:299-303): treat `PSC MS META` / `MS META ERR` like
     `PSC MS RO`; the raw image is mandatory; "If `META` is still shown at
     D8, the run will not be counted".
   - D8 (:355): META fails the check, and the operator does not wait.
   - E2 (:395-397): META makes the raw image mandatory.
   - E5 (:436): report "META at D8".
6. **IF7a, no destruction.**
   - Every region handed to `write()` is passed by `seg_end`, whatever the
     result (DESIGN:914-915, :1104-1110).
   - `resend` never succeeds, so nothing is re-sent, and every record is
     written exactly once (DESIGN:1116-1118).
   - Creation retries rewrite only `[conf, conf + k)`. That is PAD, at or
     above every flush (DESIGN:1012-1014).
   - Nothing truncates, unlinks or reopens a file (DESIGN:881-884).
   - Data keeps reaching the stick in the active file and the two files
     ahead, whose directory entries already say 2 MB from creation. So
     about 9 more minutes of records are physically on the stick and
     readable on the Mac.
7. **IF7b, no destruction.** As IF7a, plus the inode-alias check (V9):
   - New attempts find the slot left free on disk in the bad sector, and
     `fat_build_inode` returns the **cached inode of the previous abandoned
     attempt**.
   - That attempt held no records, and the alias rewrites only its FILEHDR.
     The step-0 `fstat` check (DESIGN:969-970) would reject an alias to any
     larger, records-holding file.
   - A records-holding file always had a successful `fsync`, so its
     directory entry is on disk and its slot is never free.
8. **IF8, no destruction.**
   - Flushes never allocate (V1).
   - A failed FAT write leaves the buffer clean and not up to date, so no
     flush rewrites it (V7).
   - The allocator moves forward one cluster per attempt (`prev_free`) and
     never returns, so no cluster is reused.
   - The L → c split can only, together with further errors, end in
     read-only (IF5 residual). That stops writes; it does not overwrite.
   - **Coverage is in fact kept:** after ≤ 128 attempts (about 30 s) the
     allocator leaves the sector, and the two files ahead cover about 9
     minutes.

**Rulings: IF7a, IF7b and IF8 are SPOILED-DETECTED.** All three conditions
are met, and the design destroys no data already on the stick.

**Recommendations, not required by A1:**
- In IF7b (when later files' entries fall in good sectors, so writing
  recovers) and in IF8, the run's data is complete. "Not counted if META at
  D8" spoils a good run.
- Let the decoder decide afterwards: count the run when no record after the
  META onset is missing in the raw image. RUNBOOK C4.2 already says "the
  agents still analyse it".

---

## 6. Fixes required to pass (consolidated)

| # | Fix | Closes |
|---|---|---|
| **G1** | **Escape a bad data region.** After 3 consecutive failed flushes whose S records show data-sector write errors (b1, b7 clear) while metadata writes succeeded, close the active file and switch to the next usable file (EVENT `region bad`). Repeat for that file. With no usable file, hold and create at 64 KB per tick. Or use an exponential skip within the file. Correct R8 and the stale R36 row in 11.3. Add a VFAT-FI schedule: a 2 MB data range of a ready file refuses writes after creation; pass when no hold or crossing exceeds 114.7 s. | IF9 (BLIND) |
| **G2** | **Range-based re-send and a throughput gate.** The first successful flush after a failure is durable for its own records. Re-send only failed ranges. STICK requires ≥ 35 KB/s measured during the first file's 64 KB steps, else abort at 3:00. State the lossless minimum speed in R8. | IF4 (AMBIGUOUS) |
| **G3** | **Decoder run selection.** Decode only this run's files (FILEHDR `run`), and only chunks below each file's confirmed extent. In `--raw` mode keep only this run's clusters, or records that continue this run's timeline. Report `(ring, seq)` conflicts instead of dropping them. Optionally add a boot nonce. | IF10 (AMBIGUOUS), TE7 note |

**Not blocking:**
- OE8: console level 4 at `pscol` start; state the error-path printk in 7.1,
  7.5 and 11; correct attempt-4 S9.
- UL7: list all ± 2-cycle WT straddles.
- IF5: residual implicit-truncate path into R11.
- TE7: wording of 14.2 and RUNBOOK E1 step 5.
- A1 cases: let a complete META run count.

---

## 7. Attacks attempted that found nothing (or only notes)

| Attack | Result |
|---|---|
| A flush lands exactly at the confirmed-prefix boundary | TE8: no allocation, no zero-fill, correct error attribution. |
| A non-allocating step's in-place retry allocates after all | No. The first try advanced `mmu_private` per block (V1, `inode.c:93`). After a `prepare_write` failure, `vmtruncate` sets `mmu_private` to `i_size` ≥ `conf`, which is still at or above the retry's start. |
| The allocating-step formula misclassifies a step | No. ⌊(conf+k−1)/cl⌋ > ⌊(conf−1)/cl⌋ is exactly "a multiple of `cl` lies in [conf, conf+k)", and `fat_add_cluster` runs only at offset 0 of a cluster (`inode.c:82-87`). |
| `fstat` agreement is meaningless because `i_size` is in memory | True, it only confirms the `write()`. But `conf` needs the `fsync` too, and `fsync` returns 0 only if the data, the directory entry (`write_inode`, V5) and FSINFO/FAT (`sync_blockdev`) were written. So `conf` implies the chain and entry are on disk, apart from silent loss (R11). |
| A pdflush write consumes a creation step's `AS_EIO` on the block device | No. The creation's own `sync_blockdev` wait consumes it in the same step (V7). A pdflush inode write between `write()` and `fsync` leaves the directory buffer dirty, and `sync_blockdev` writes it. |
| Inode alias (V9) destroys a records-holding file | Only if the directory sector's old content is *destroyed* on the medium and reads back as zeros (R11 hardware, UNVERIFIED). Even then the step-0 `fstat` check (expected 1,536, a records file is larger) stops the attempt after its 1,536-byte FILEHDR write. That would overwrite the other file's FILEHDR, not records. **Recommendation:** after any directory-sector write error, compare `fstat(st_ino)` of a new file against the open files' inode numbers before the first write. |
| The `fadvise64_64` call through `syscall()` is mis-marshalled | Verified correct (section 1.3). |
| Hook S misses a preemption because `prev->state ≠ 0` | Not inside `Syscon_cmd`, which never sets a state. |
| The cap or names run out under IF8 fast retries | ≤ 128 fast attempts for one bad sector, against 256 fast and 999 names per run. Directory growth past one cluster (1,024 entries at 32 KB) is not reached in one run. |
| A long whole-stick burst (minutes) that ends before the pull | Records older than 114.7 s at the burst's end are lost. This is the accepted Case 2 (4.5), which attempt-4 agreed with for a whole-stick refusal. No stick-writing design can route around a whole-stick refusal; only larger RAM rings could. **Recommendation:** P and POLL rings 4× larger (about +1.2 MB of BSS, against 20.8 MB free) would cover about 7.6 minutes. |

---

## 8. Designer acceptances: do I agree?

| Acceptance | My position |
|---|---|
| N1m "cannot be separated in one run" | **Agree** (identical records). |
| R11 silent FAT/directory loss answered by the raw image | **Agree**, with the IF5 residual and the alias note added. |
| J10 / 14.1 "F1(b) not adopted": data-sector durability not needed under A1 | **Agree for the A1 class.** **Disagree** that nothing replaces the use of S records for *data* errors. IF9 needs the same S-record reading, for the escape, not for durability. |
| 14.4 IF4: "lossless at 25-300 KB/s" | **Disagree at 25 KB/s** (section 2, IF4; Appendix A). The claim relies on attempt-4's model, which lacked r4's re-send rule. |
| 4.6 "flushes never meet the same sectors twice" (reason for dropping the switch rule) | **True, but not sufficient.** A failure region larger than one flush is crossed at flush speed (IF9). |
| 14.5 weakest point: vfat ordering and real stick failure behaviour | **Agree.** Also add the driver's `DBG` printk (OE8) to the list of facts VFAT-FI must reproduce. |

---

## 9. UNVERIFIED items this report depends on

1. Whether Memory Stick write errors occur in this setup at all, and whether
   a logical *data* range can start refusing writes after being written
   successfully (IF9). The same uncertainty underlies A1.
2. The stick's sustained single-sector write speed (IF4 at 25 KB/s; IF9
   crossing time).
3. The duration of fbcon's interrupt-off rendering per printk line on this
   CPU (OE8). My estimate is 1-10 ms.
4. Whether rehearsal or deleted earlier-run PSCLOG data exist on the
   operator's stick (IF10).
5. The syscon's internal state after a "benign" straddle (UL7).
6. What a destroyed directory sector reads back as (zeros, 0xFF or an error),
   for the alias note.

---

## Appendix A. Simulation model (r4 rules)

A discrete-time model of DESIGN 4.3, 4.4 and 4.6 as written in revision 4.

**Ticks.**
- Each tick lasts 0.23 s plus (flush bytes + creation-step bytes + metadata)
  / stick speed.
- Metadata is 1 KB per `fsync` (directory entry and FSINFO), plus 1 KB per
  allocating step (FAT and its mirror).

**Records and flushes.**
- Records arrive at 7,598 B/s (DESIGN 5.1).
- The reader position R and the durable point D are tracked separately.
- A flush carries what the reader drains: everything since R, capped at
  34,364 B. It is padded to 512 B, with a minimum of 1,536.
- **Success with `resend` clear:** D = R.
- **Failure:** `seg_end` advances, `resend` is set, D is unchanged.
- **First success with `resend` set:** nothing becomes durable, and the
  reader seeks back to D.
- **Overflow:** records older than 114.7 s (D < now − 114.7) are lost and
  counted.

**Segments.**
- 2,097,152 B files, FILEHDR 1,536 B, 32 KB clusters.
- Creation runs while fewer than two complete files are ahead.
- Step size: 64 KB while the active file is not complete or the worker
  holds; 8 KB otherwise.
- A step allocates if it crosses a cluster start.
- A failed non-allocating step is retried, up to 3 times.
- A failed allocating step, or a fourth failure, stops the file: it is
  prefix-usable if `conf` ≥ 42,496, otherwise abandoned, with the next
  attempt ≥ 10 s later.
- **Switch:** to the oldest complete or prefix-usable file with room. With
  none, hold.

**Failures.**
- Poisson events at 98 per 1,800 s.
- **Whole-tick model** (attempt-4's): every I/O in a tick containing an
  event fails.
- **Per-operation model:** an operation fails with probability
  1 − exp(−λ × its I/O time).

**Bad data region (IF9).**
- Flushes overlapping [offset_lo, offset_hi) of file #1 fail. Creation is
  unaffected, because the region goes bad after creation.
- "Escape" variant: switch files after 3 consecutive failed flushes.

**Runs.** 100 runs of 1,800 s per point. The results are in IF4 and IF9.
Scripts: `sim_r4b.py` and `sim_r4p.py` in this agent's scratchpad, not part
of the handoff.

| IF4 check | 25 KB/s | 30 KB/s | ≥ 40 KB/s |
|---|---|---|---|
| r4 as written, whole-tick failures | 202 s mean lost, 98/100 runs | 0.1 s, 1/100 | 0 |
| r4 as written, per-operation failures | 3.3 s, 13/100 | 0 | 0 |
| r4 with range-based re-send (G2), whole-tick | 3-6 s, 7-13/60 | 0 | 0 |
| No failures | 0 | 0 | 0 |
