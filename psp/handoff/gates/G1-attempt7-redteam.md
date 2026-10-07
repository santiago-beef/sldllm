# Gate G1, attempt 7: red team report

Artifact under review: `design/DESIGN.md` revision 6 (2,669 lines) and
`design/RUNBOOK.md` revision 6 (485 lines), with the diff against revision 5,
`design/round7.diff`, and the designer's response in DESIGN section 16.
Reviewer role: G1 red team, attempt 7. Fresh context. I did not write the
design or any earlier gate report.
Date: 2026-10-05.

**Scope: FULL.** Amendment A1 is on record but does not apply in this round
(gate-log note of 2026-10-05 authorizing round 7; the task brief). The round is
closure only: the designer could change only what closes review items A6-1 to
A6-4 and my predecessor's AMBIGUOUS IF7b and TE10. SPOILED-DETECTED is not
available.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding, 9.6 included), `WORKFLOW.md` (Amendments included),
`recon/syscon.md`, `recon/input.md`, `recon/build.md`, `recon/image2008.md`,
`gates/LOG.md`, `gates/G1-attempt6-review.md`, `gates/G1-attempt6-redteam.md`,
`design/round7.diff` (first), then `design/DESIGN.md` and `design/RUNBOOK.md`.

Method:
- Source was only read, in `/home/ubuntu/psp/build/linux`. Kernel paths below
  are relative to it. I verified the write order myself in `fs/sync.c`,
  `fs/fs-writeback.c`, `fs/fat/inode.c`, `fs/fat/dir.c`, `fs/buffer.c`,
  `fs/vfat/namei.c`, `mm/page-writeback.c` and `drivers/block/ms_psp.c`, and I
  opened every line the round-7 text cites (section 1).
- No disassembly was needed.
- I re-ran the designer's model (`design/r5-scripts/sim_r5.py`, copied to my
  scratchpad, unmodified) for the A6-3 (e) figures: 700 seeds at 28, 29 and
  30 KB/s (Appendix A).
- After the work: `cd build/linux && sha256sum -c --quiet
  ../../handoff/gates/baseline-tree.sha256` printed nothing (exit 0), and
  `git -C work/linux status --porcelain` printed nothing. I wrote only this file
  and scratch files in my scratchpad.
- "DESIGN:n" means a line number in DESIGN.md as it stands today.
- Anything the source cannot settle is marked **UNVERIFIED**.

---

## Verdict: PASS

**No scenario is BLIND, and no scenario is AMBIGUOUS.**

- **IF7b** (attempt-6 AMBIGUOUS) is now **DIAGNOSABLE**. The own-entry rule
  (DESIGN:1087-1113) picks the right S record in every case I could build from
  this tree's code: rejected-alias writes, FSINFO, another file's data,
  `pdflush`, and window and tick boundaries. The only way I found to defeat it
  needs a transient failure inside a window of a few milliseconds (IF13 below).
  Its records still survive on the stick.
- **TE10** (attempt-6 AMBIGUOUS) is now **DIAGNOSABLE**. A file that has been
  active can no longer be a switch target (DESIGN:1173-1178), and the
  hold-and-resume rule (DESIGN:1178-1182) cannot write a region twice.
- All 21 attempt-6 scenarios whose mechanism the diff touched were re-run.
  All are DIAGNOSABLE.
- The other 22 are carried with their attempt-6 rulings.
- My 7 new scenarios aim only at the changed text, at least one per group. All
  are DIAGNOSABLE.

Four corrections should be made before Stage 2. None is blocking, and none
changes a ruling:

| # | Correction | Why |
|---|---|---|
| **C1** (TE11) | The new 8.5 TE10 vectors (DESIGN:1888) require "the worker holds and resumes in the same file at its own `seg_end`". In both vectors the design's own rules **stop** the file instead, so a correct implementation cannot pass them. | A 3 s burst fails the step's FAT1 write, which stops growth (DESIGN:1114-1116). Two failed 64 KB steps never confirm, because of the still-open IF11. |
| **C2** (IF11, carried) | "The retry allocates nothing" (DESIGN:1119-1121) together with the allocation formula (DESIGN:1081-1083) still means an allocating step that is retried in place can never be CONFIRMED. | This was outside the round-7 brief, so it is still open. It now also sets C1 off, and it makes every data-only failure during a TE10 hold cost a whole file. |
| **C3** (IF13) | At step 0, also refuse CONFIRMED when any write record **of the own-entry record's own sector** with b1 set appears earlier in the window. Add a raw-image trigger for a durable gap. | This closes a rare case: a nameless entry is CONFIRMED, and its records are then found only in the raw image. |
| **C4** (IF4) | The new sentence "from 28 KB/s up the model loses nothing" (DESIGN:71-72, :1435-1436, R8) is not what the model gives. In 700 seeds, 1 run at 28 KB/s loses 10.8 s. | The 30 KB/s gate is unaffected: 0 runs in 700 lose anything at 30 KB/s. |

### In plain words

- **IF7b: what was wrong, and the fix.** When a new file is created, the stick
  receives several "bookkeeping" writes. One of them is the new file's own
  directory entry. Under a bad directory sector, another bookkeeping write
  (the bad sector, holding skipped "alias" entries) fails in the same save.
  The old text did not say which write was the file's own. The new text says
  it is the first directory write by the collector after the file's data. I
  checked in this kernel's code that the file's own entry is always written
  at exactly that point: after the data, and before any other bookkeeping
  sector. So the rule is right.
- **TE10: what was wrong, and the fix.** The old switching rule could pick the
  file currently being written and start it again from the top, over saved
  records. The new rule forbids that, and says "wait, then carry on where you
  were". I checked that the waiting always ends and never rewrites anything.
- **What I found that is new.** These are small items:
  - one test in the plan expects an outcome the rules do not produce (C1);
  - one older inconsistency is still in the text (C2);
  - one very rare timing case could hide a file's name on the stick, though
    not its data (C3);
  - one sentence about the stick-speed model is slightly too optimistic (C4).

---

## Summary table

"Re-run" = mechanism touched by the round-7 diff; "carried" = attempt-6 ruling
kept without change.

| ID | Group | Scenario | Attempt 6 | Attempt 7 |
|---|---|---|---|---|
| UL1 | unlisted-shape | LED write-back of bit 4 during a suspension at S14 | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL3 | unlisted-shape | Link one reply behind | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL4 | unlisted-shape | Valid frames, HOLD stuck | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL5 | unlisted-shape | LED ops during a suspension, clean read-back | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL6 | unlisted-shape | Nop breaks the link with no thread command in flight | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL7 | unlisted-shape | Two-stage H4 | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL8 | unlisted-shape | Syscon wall-time watchdog trips on a late Nop | DIAGNOSABLE | DIAGNOSABLE (carried) |
| UL9 | unlisted-shape | Thread asleep forever in `msleep` | DIAGNOSABLE | DIAGNOSABLE (carried) |
| TE1 | timing-edge | Death at 5 s, 17 s, 36 s | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| TE2 | timing-edge | Nop on a suspended thread | DIAGNOSABLE | DIAGNOSABLE (carried) |
| TE3 | timing-edge | Minute 14 in `fsync`, 29:50, link wrap, console blank | DIAGNOSABLE | DIAGNOSABLE (carried) |
| TE4 | timing-edge | Slow Nop, nested tick, preemption at outer return | DIAGNOSABLE | DIAGNOSABLE (carried) |
| TE5 | timing-edge | Nop inside an LED read-modify-write | DIAGNOSABLE | DIAGNOSABLE (carried) |
| TE6 | timing-edge | Early death while the first file is created | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| TE7 | timing-edge | Pull while the active file is still in creation | DIAGNOSABLE (decoder note) | **DIAGNOSABLE (re-run; note closed by A6-3)** |
| TE8 | timing-edge | Catch-up flush ends at `conf`; step shares the page | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| TE9 | timing-edge | Pull between a step's entry write and its FAT write | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| TE10 | timing-edge | Active file in creation runs out of room in catch-up | AMBIGUOUS | **DIAGNOSABLE (re-run; fixed)** |
| IF1 | instrumentation-fault | Transient failure spanning onset | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| IF2 | instrumentation-fault | Worker killed at minute 13-14 | DIAGNOSABLE | **DIAGNOSABLE (re-run; TE10 dependency gone)** |
| IF3 | instrumentation-fault | Reader races; head moves backwards | DIAGNOSABLE | **DIAGNOSABLE (re-run; A6-4)** |
| IF4 | instrumentation-fault | 25-35 s burst; ≈ 98 sporadic failing ticks | DIAGNOSABLE | **DIAGNOSABLE (re-run; text correction C4)** |
| IF5 | instrumentation-fault | Failed `fsync` on an allocating flush | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| IF6 | instrumentation-fault | Corrupt slot `seq`, forward head jump | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| IF7a | instrumentation-fault | FSINFO refuses for the rest of the run | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| IF7b | instrumentation-fault | `PSCLOG` directory sector refuses for the rest of the run | AMBIGUOUS | **DIAGNOSABLE (re-run; fixed)** |
| IF8 | instrumentation-fault | FAT sector at the allocator refuses | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| IF9 | instrumentation-fault | Bad data region in a prepared file | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| IF10 | instrumentation-fault | Chunks from another boot | DIAGNOSABLE | DIAGNOSABLE (carried) |
| IF11 | instrumentation-fault | Allocating step: data-only failure, then retry | DIAGNOSABLE (correction) | **DIAGNOSABLE (re-run; correction C2 still open)** |
| IF12 | instrumentation-fault | Flaky stick fires the bad-region escape | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| OE1 | observer-effect | MS driver hang, raised preempt count | DIAGNOSABLE | DIAGNOSABLE (carried) |
| OE2 | observer-effect | `statfs` FAT scan | DIAGNOSABLE | DIAGNOSABLE (carried) |
| OE3 | observer-effect | Collector load and H4 start-delay exposure | DIAGNOSABLE | DIAGNOSABLE (carried) |
| OE4 | observer-effect | Kernel-privileged `pscol`, stray store | DIAGNOSABLE | DIAGNOSABLE (carried) |
| OE5 | observer-effect | Collector exit frees a mousedev client mid-walk | DIAGNOSABLE | DIAGNOSABLE (carried) |
| OE6 | observer-effect | Stall panel paints for minutes | DIAGNOSABLE | DIAGNOSABLE (carried) |
| OE7 | observer-effect | Global `drop_caches` | DIAGNOSABLE | DIAGNOSABLE (carried) |
| OE8 | observer-effect | Driver `DBG` printk drawn with interrupts off | DIAGNOSABLE | **DIAGNOSABLE (re-run; A6-2)** |
| OE9 | observer-effect | Refusing FSINFO: driver retries with preemption off at every `fsync` | DIAGNOSABLE | **DIAGNOSABLE (re-run)** |
| OE10 | observer-effect | Console level 4 removes a baseline perturbation | DIAGNOSABLE | **DIAGNOSABLE (re-run; A6-2)** |
| A1-OE3 | observer-effect | Who held the CPU while the thread was preempted mid-command | DIAGNOSABLE | DIAGNOSABLE (carried) |
| **UL10** | unlisted-shape (new; own-entry rule) | A common cause kills input and a `PSCLOG` directory sector at the same moment | – | **DIAGNOSABLE** |
| **TE11** | timing-edge (new; hold-and-resume) | The active file in creation stops during its TE10 hold (burst, or data-only failures) | – | **DIAGNOSABLE** (8.5 pass condition to correct, C1) |
| **TE12** | timing-edge (new; own-entry rule) | Death and pull during the 17-tick IF7b first phase, at a 5 s boundary | – | **DIAGNOSABLE** |
| **IF13** | instrumentation-fault (new; own-entry rule) | The own entry's sector fails once **before** the step's data, by `pdflush`, and recovers | – | **DIAGNOSABLE** (tightening C3 recommended) |
| **IF14** | instrumentation-fault (new; own-entry rule × names) | IF7b plus wholesale reclaim of the alias inodes once the page cache fills RAM | – | **DIAGNOSABLE** |
| **IF15** | instrumentation-fault (new; own-entry rule × takeover) | After a takeover, "the worker's pid" is a different process | – | **DIAGNOSABLE** (wording and test recommended) |
| **OE11** | observer-effect (new; own-entry and hold rules) | IF7b now keeps recording, so its failing-sector load lasts the whole run; TE10 holds paint the panel during start-up | – | **DIAGNOSABLE** |

---

## 1. Source facts the rulings rest on (verified by me in this tree)

### 1.1 The order of writes in one `fsync` on vfat

| # | Fact | Evidence |
|---|---|---|
| W1 | `do_fsync` writes the file's data first (`filemap_fdatawrite`), then calls `f_op->fsync`, then waits on the data. | `fs/sync.c:90`, `:97`, `:100` |
| W2 | vfat's `fsync` is `file_fsync`. | `fs/fat/file.c:136` |
| W3 | `file_fsync` runs `write_inode_now(inode, 0)`, then `write_super`, then `sync_blockdev`. | `fs/sync.c:62`, `:67-68`, `:72` |
| W4 | `write_inode_now` always builds a `WB_SYNC_ALL` control. It waits for any other writer of the inode (`I_LOCK`), then runs `__sync_single_inode`. | `fs/fs-writeback.c:568-583`, `:270-283` |
| W5 | `__sync_single_inode` clears `I_DIRTY`, runs `do_writepages` (the data, already clean), then calls `write_inode(inode, wait = 1)`, but only if `I_DIRTY_SYNC` or `I_DIRTY_DATASYNC` was set. | `fs/fs-writeback.c:157`, `:163-166`, `:170`, `:173-174` |
| W6 | `fat_write_inode` re-reads the entry's sector with `sb_bread`. It puts in size, attributes, start and times (not the name), then calls `mark_buffer_dirty` and, with `wait`, `sync_dirty_buffer`. | `fs/fat/inode.c:571`, `:586-600`, `:604-606` |
| W7 | `sync_dirty_buffer` writes only if it clears the dirty bit itself. | `fs/buffer.c:2708-2709` |
| W8 | `fat_write_super` only marks FSINFO dirty. `sync_blockdev` writes the block device's dirty pages. | `fs/fat/inode.c:453-459`; `fs/fat/misc.c:40-72`; `fs/buffer.c:152-159` |
| W9 | The driver is a `make_request` driver. Every bio is transferred **synchronously in the submitting task's context**, under one semaphore. So an S record's `pid` is the task that issued the write, and S order is I/O order. | `drivers/block/ms_psp.c:190-191`, `:228-236`, `:252-265`, `:333`, `:351`, `:360`, `:378` |

**Consequence.** For step 0 (the file was just created and written, so it
carries `I_DIRTY_SYNC`), the worker's S records in its window come in this
order:
1. the step's DATA records;
2. **exactly one** DIR write record, the own entry (W6);
3. FSINFO, FAT1, FATM and **any other dirty directory sector** (W8).

The designer's statement of this order (DESIGN:1089-1105) and every citation
in it resolve to the lines claimed. I opened each of them.

### 1.2 How a directory sector gets dirtied, re-read and written by others

| # | Fact | Evidence |
|---|---|---|
| D1 | `fat_add_entries` writes the new entry into the directory buffer with `mark_buffer_dirty`, and writes it synchronously only under `DIRSYNC` (not set here). | `fs/fat/dir.c:1255-1269`, `rc.sysinit:10` |
| D2 | Directory sectors are read through `sb_bread`. A buffer that is not up to date is re-read from the stick. | `fs/fat/dir.c:87`; `fs/buffer.c:1382-1383` |
| D3 | A failed **asynchronous** write (`pdflush`, `sync_blockdev`) clears the buffer's up-to-date bit and sets `AS_EIO` on the block-device mapping. | `fs/buffer.c:429-452` (`:449`, `:451`) |
| D4 | `vfat_create` does not dirty the new inode. `vfat_add_entry` dirties the **directory** inode. | `fs/vfat/namei.c:758`; `:671` |
| D5 | An inode that is already dirty keeps its first `dirtied_when` (early return). `wb_kupdate` writes only inodes dirtied ≥ 30 s ago. | `fs/fs-writeback.c:74`; `mm/page-writeback.c:85`, `:442` |

So the block device inode stays dirty with an old `dirtied_when`, and `pdflush`
writes whatever block-device buffers happen to be dirty about once every 30 s.
A fresh step-0 inode is never old enough for `wb_kupdate`, so in practice only
the worker writes it.

---

## 2. IF7b and TE10 re-run

### IF7b. The `PSCLOG` directory sector X refuses writes for the rest of the run. **DIAGNOSABLE** (was AMBIGUOUS)

**The new rule** (DESIGN:1087-1113). The own-entry write is "the first DIR-class
write record (b0 set) carrying the worker's pid after the last DATA record of
the step's own data sectors in the window". It must exist and have b1 clear. A
DIR record of another pid between the two makes step 0 not CONFIRMED. Any other
failed DIR write in the window is META evidence only.

**Trace in this tree, the tick in which the fresh file lands in X + 1:**
1. The alias loop's `open`s re-read X (D2) and put the rejected aliases' entries
   into X's buffer. X is dirty (D1). Closing an alias writes nothing.
2. Step 0 `write()`, then `fsync`:
   - DATA (W1);
   - `fat_write_inode` writes X + 1, successfully (W5, W6): **the first worker
     DIR write record after DATA**;
   - `write_super` marks FSINFO dirty;
   - `sync_blockdev` writes FSINFO, FAT1, FATM and X, and X fails (W8).
3. The rule picks X + 1 and finds it OK. The X failure is META only. Step 0 is
   CONFIRMED, as 15.3 says (DESIGN:2467-2471).

**The task's four attacks on the rule:**

| Attack | Can it make the collector pick the wrong record? | Evidence |
|---|---|---|
| **A rejected-alias write** | No. An alias's entry is written only through X's dirty buffer, so only by `sync_blockdev`, which comes after `fat_write_inode` (W3). An alias inode is clean and its `release` writes nothing (D4; `fs/fat/file.c:117-125`). The only exception is a fresh entry in the **same** sector as the aliases (A5-1 case); then one write covers both, and the rule is right either way. | W3, W5, D1, D4 |
| **An FSINFO write** | No. It is class FSINFO, not DIR (DESIGN:1401). It is also never written before the own entry (W8). With wrong geometry the STICK self-check aborts (DESIGN:1453-1456). | W8; DESIGN 4.8 |
| **A data write for another file** | No. It is class DATA, never DIR. The rule's anchor is "the last DATA record **of the step's own data sectors**" (from FIBMAP), so a later DATA record of another file (for example `pdflush` writing a left-over dirty page of the active file) neither moves the anchor nor qualifies as the own entry. | DESIGN:1087-1090, 4.8 |
| **A tick boundary** | No. Windows are bounded by S heads, not ticks (DESIGN:1422-1432). Every write is complete, with its S record written, before `fsync` returns (W9). The step-0 window runs from the end of the flush's window to the head after the step's `fsync`. Records added between `fsync`'s return and the head read can only come **after** the own entry: a FAT1 failure there makes the verdict conservative, and a DIR failure there is META. When a probe `fsync` runs in the same tick (stick not working), its records come **before** the step's DATA and are ignored. | DESIGN 4.8 windows; W9 |
| **`pdflush` interleaving** (my addition) | Covered. `pdflush` can write the own-entry buffer between `fs/fat/inode.c:604` and `:606` (the BKL is preemptible, `.config:136`), so the worker's `sync_dirty_buffer` writes nothing (W7). The designer's extra rule (another pid between DATA and the worker's first DIR → not CONFIRMED) turns that into a lost name, never a false CONFIRMED. A `pdflush` write **after** the own entry is irrelevant. A `pdflush` failure **before** the DATA is the one gap (IF13). | W7; D5 |
| **The inode already cleaned by a third party** (my addition) | Then `__sync_single_inode` does not call `write_inode` (W5), and the own entry would be written by `sync_blockdev` in page order. That needs a `sync()` from another process, or a `writeback_inodes` with no age limit (`balance_dirty_pages`), between step 0's `write()` and its `fsync`. No process here calls `sync()` (`recon/input.md` §5.1 syscall lists). Dirty memory stays far below the thresholds, because every tick is synced. If it did happen, the first worker DIR record would usually be X (failed, lower in page order) → abandon, which is conservative. | W5; D5 |

**Names.** I re-derived 15.3: tick k uses k − 1 aliases plus one abandoned file
(k names); 16 such ticks use 136 names, and tick 17 uses 16 aliases plus the
fresh file. That is **153 names and 17 ticks**, as stated. Each later creation
uses ≤ 17 names, while the inodes stay cached. Fast attempts: 16 of
`min(400, budget/2)`. Inode eviction is IF14.

**Recorded:** the step windows, `abandon` and `inode reused` EVENTs, UHB b17
and b28, META on X with class DIR. Records go into the active file and the
files ahead, which keep growing, and later creations succeed. Entries in X are
missing on the stick, and the raw image is mandatory with META (RUNBOOK E2).

**Ruling: DIAGNOSABLE.** Fix needed: none blocking (see C3/IF13 for a
tightening).

### TE10. The active file in creation runs out of room during catch-up. **DIAGNOSABLE** (was AMBIGUOUS)

**The new rules:**
- Switch only to a file that has **never been active**. Set `seg_end = 1,536`
  only for such a file (DESIGN:1173-1178).
- If the active file is still in creation (and not retired) and the next flush
  does not fit, hold with 64 KB steps, and resume in the same file at its own
  `seg_end` once `seg_end + 40,960 ≤ conf` (DESIGN:1178-1182).

**Trace.**
1. My predecessor's numbers: room drops below 40,960, so the worker holds.
2. Each confirmed 64 KB step adds 65,536 bytes, so one confirmed step always
   resumes flushing (65,536 > 40,960).
3. After it resumes, a tick does at most −40,960 (the flush) then +65,536 (the
   step, while room is below 81,920; DESIGN:1075-1078). So room **grows by
   ≥ 24,576 per tick**: there is no livelock.
4. No region below `seg_end` is written again, and the boot records at
   1,536 + stay on the stick.

**Literal-reading check.**
- The file in creation is the newest file, and creation runs one file at a time
  (DESIGN:1016-1020). So when the active file is in creation, no never-active
  file exists ahead of it, and the new rule is reached exactly in the TE10
  case.
- A takeover instance writes only its own fresh files (DESIGN:896-903).
- The read-only rule still forbids creation steps (DESIGN:1343-1350). In that
  case the hold simply does not end. That is the accepted read-only outcome
  ("≈ 0-9 minutes"), and it never overwrites. 4.6 should say that its "no
  creation step" takes precedence over "holds … with 64 KB steps" (wording
  only).

**What the TE10 vector expects, and what really happens.** The realistic
triggers stop the file rather than letting it resume (TE11): a burst fails
FAT1, and data-only failures of an allocating step meet IF11. The stopped file
is then handled by the normal switch rule. That is safe, but the 8.5 pass
condition as written cannot be met (C1).

**Ruling: DIAGNOSABLE.** Fix needed: C1 (test text), and the precedence
sentence above.

---

## 3. Attempt-6 scenarios re-run because the diff touched their mechanism

**TE1. Death at 5 s, 17 s, 36 s. DIAGNOSABLE.**
- The start-up rule is unchanged (the first flush comes one 64 KB step after
  the FILEHDR).
- The new TE10 rule only adds a hold where r6's literal text would have
  overwritten. The rings hold from boot (P/POLL 114.7 s), and the boot records
  are no longer at risk.
- The speed-gate text changed (C4), but the gate did not.

**TE6. Early death while the first file is created. DIAGNOSABLE.** As TE1. The
first file becomes active with `seg_end = 1,536` (it was never active), and a
hold inside it resumes in place.

**TE7. Pull while the active file is still in creation. DIAGNOSABLE.**
- A6-3 (a) closes my predecessor's decoder note. The decoder maps v to
  `8,192·v + 1,536` (`SEG` at 256) (DESIGN:1960).
- I checked that every `conf` of a file in creation is 1,536 + a multiple of
  8,192: step 0 is 1,536 bytes; steps are 8 or 64 KB; the last step ends at
  `SEG` = 256 × 8,192.
- So the extent is now exact.

**TE8. Catch-up flush ends at `conf`; the step shares the page. DIAGNOSABLE.**
- Windows are unchanged.
- The own-entry rule reads only the step's own window. Step 0 never shares a
  page with a flush: flushes start at 1,536, and a file in creation becomes
  active only after a 64 KB step.

**TE9. Pull between an allocating step's entry write and its FAT write.
DIAGNOSABLE.** A6-1 rests on the same order (W3-W8), which I re-verified: the
entry with the new size reaches the stick before the FAT link does. My
predecessor's ruling holds.

**TE10.** Section 2.

**IF1. Transient failure spanning onset. DIAGNOSABLE.**
- Flush verdicts are unchanged.
- At step 0, a failure of a DIR sector other than the own entry no longer
  abandons the file.
- The A5-1 trace (DESIGN:2501-2514) still holds: when the whole stick fails,
  the own entry fails too.

**IF2. Worker killed at minute 13-14. DIAGNOSABLE.**
- Instance 2's fresh file is active while still in creation during a large
  catch-up. That is exactly TE10's case, and it is now covered by
  hold-and-resume.
- Instance 2's pid is IF15.

**IF3. Reader races; head moves backwards. DIAGNOSABLE.**
- A6-4: the ring `read()` sets `*ppos`, never `file->f_pos` (DESIGN section 2.8).
- `sys_read` copies its local position back (`fs/read_write.c:364-366`), while
  `pread` passes its own (`:404-405`).
- So the S-window `pread`s cannot move the drain position or be mistaken for a
  head regress. The new 8.5 reader vector tests the interleave.

**IF4. Burst and sporadic failures. DIAGNOSABLE (text correction C4).**
- I re-ran the model with seeds 0-699 (Appendix A), whole-tick model:
  - 30 KB/s loses nothing in 700 runs;
  - 29 KB/s loses nothing in 400;
  - **28 KB/s loses 10.8 s in 1 of 700** (seed 290);
  - 25 KB/s seed 9 reproduces the designer's 15.2 s.
- The gate (30 KB/s) is right. The sentence "from 28 KB/s up the model loses
  nothing" is not.
- A loss when it happens is Case 2: it is shown by the panel and `DUR`.

**IF5. Failed `fsync` on an allocating flush. DIAGNOSABLE.** 4.4 step 5 is
unchanged. Flushes stay below `conf` and never truncate. The step-0 change does
not reach flushes.

**IF6. Corrupt slot `seq`, forward head jump. DIAGNOSABLE.**
- A skipped `seq` in a window still makes the operation FAILED (DESIGN:1433-1434).
- For step 0 that is conservative: a skipped record could be the own entry, and
  the result is abandon, never a false CONFIRMED.

**IF7a. FSINFO refuses. DIAGNOSABLE (OE9 caveat carried).**
- The r7 text makes explicit that FSINFO failures are tolerated "at step 0 as
  at later steps" (DESIGN:1111-1113).
- My predecessor's reviewer note (step 0 "any failure abandons" would also have
  abandoned on FSINFO) is closed by "not CONFIRMED → abandoned"
  (DESIGN:1122-1123).
- FSINFO is written after the own entry (W8), so it can never be taken for it.

**IF7b.** Section 2.

**IF8. FAT sector at the allocator refuses. DIAGNOSABLE.**
- Step 0's FAT1 write fails, so the attempt is not CONFIRMED and is abandoned;
  the own entry (written earlier, OK) does not change that.
- After at most 128 attempts the allocator leaves F. The fast-attempt cap
  (≥ 200) covers this.

**IF9. Bad data region in a prepared file. DIAGNOSABLE.**
- Retire, then switch to the oldest **never-active** usable file. That is
  stricter than r5, and nothing is lost by it, because a retired or full file
  was never a valid target.
- A retired file that was still being created stops growing (DESIGN:1313), so
  the TE10 hold does not apply to it ("and not retired").

**IF11. Allocating step: data-only failure, then retry in place. DIAGNOSABLE
(correction C2 still open).**
- DESIGN:1081-1083 still requires a successful FAT1 record whenever the
  formula says the step allocates.
- DESIGN:1117-1121 still says the retry allocates nothing. So a retried
  allocating step has no FAT1 record and can never be CONFIRMED; it stops after
  the fourth try.
- No record is lost: flushes stay below `conf`, and a new file is created.
- **New interaction:** during a TE10 hold every step is a 64 KB allocating
  step. So one transient data failure there costs the whole active file, and
  the hold lengthens to the time it takes to create a new file (TE11). This also
  makes the new 8.5 TE10 vector unpassable (C1).

**IF12. Flaky stick fires the bad-region escape. DIAGNOSABLE.**
- Each retire switches to a never-active file, and finally holds and creates.
  This is the same bound as in attempt 6.
- Under a flaky stick, step 0's own entry often fails, so attempts are
  abandoned and fast. That is unchanged in kind. My predecessor's recommendation
  (a separate small budget for escape-caused fast attempts) remains valid.

**OE8. Driver `DBG` printk drawn with interrupts off. DIAGNOSABLE.**
- A6-2: the call is now `syscall(__NR_syslog, 8, 0, 4)` at worker start, with
  the return in EVENT `conlevel` (DESIGN:906-911).
- Verified:
  - `do_syslog` case 8 sets `console_loglevel` (`kernel/printk.c:292-300`);
  - default messages are level 4 (`:40`), so they are no longer drawn;
  - `telem.c:281` makes the same call with type 3;
  - `klogctl` is declared at `staging_dir/usr/include/sys/klog.h:30`.
- The time from the supervisor to the worker's start is one `vfork`/`execve`,
  so the change of process does not open a window that matters.

**OE9. Refusing FSINFO: driver retries at every `fsync`. DIAGNOSABLE.**
- Unchanged in mechanism. The round-7 brief did not admit the data-only
  `sync_file_range` recommendation.
- The persistent perturbation is recorded (S durations, `wk_*`/`pre_*`) but is
  not flagged by the decoder. See OE11, where IF7b now joins it.

**OE10. Console level 4 removes a baseline perturbation. DIAGNOSABLE.** Moving
the call to worker start changes nothing: the 9.6 sessions printed nothing after
boot (`kmsg.txt` 1,606 bytes), and every message still reaches KMSG.

## 4. Attempt-6 scenarios carried without change

UL1, UL2, UL3, UL4, UL5, UL6, UL7, UL8, UL9, TE2, TE3, TE4, TE5, IF10, OE1, OE2,
OE3, OE4, OE5, OE6, OE7, A1-OE3: **carried, DIAGNOSABLE**.
- The diff touches no kernel capture point, no record format other than the
  documentation of UHB `seg`, and no decoder row.
- IF10's run selection is unchanged. The `seg` mapping (TE7) only makes the
  confirmed extent exact.
- OE4's guards are unchanged.

---

## 5. New scenarios aimed at the changed text

### UL10 (unlisted-shape; own-entry rule). A common cause kills input and a `PSCLOG` directory sector together. DIAGNOSABLE

**Shape.**
- A supply sag or ESD event at a 5 s boundary does two things at once: it
  wedges the syscon, and it leaves one Memory Stick directory sector refusing
  writes from then on.
- Neither the dossier list nor H10 covers a **shared** cause of input death and
  stick damage.
- Under r6 as literally written, creation would have stopped for the rest of
  the run. Under r7 it does not.

**Trace.**
1. Input death leaves its syscon signature in P/W/POLL. The rings are drained,
   and flushes stay DURABLE (data sectors work).
2. META on X is detected within ≈ 1-2 s if the active file's entry is in X;
   otherwise at the next creation (DESIGN 4.7).
3. The next creation runs IF7b's first phase (≤ 17 ticks). Recording never
   stops.

**Recorded.** The onset tick (P/W) and `meta_tick`/EVENT `meta err` (S sector,
class DIR) are on one timeline. The decoder lists both. Their coincidence is
visible to the analyst, so S1's "show the raw evidence" holds.

**Ruling: DIAGNOSABLE.** Fix needed: none. Recommended: the onset annotation of
10.7 should list a META onset within ± 5 s of a death as a coincident event.

### TE11 (timing-edge; hold-and-resume). The active file in creation stops during its TE10 hold. DIAGNOSABLE (correction C1)

**Shape.** A TE10 hold is in progress, so the active file is in creation and
taking 64 KB steps. Then one of these happens:
- (a) a 3 s whole-stick burst: the step's FAT1 write fails;
- (b) two data-only failures of the step.

**Trace.**
1. Case (a): "A FAT1 write of the step failed: the file stops growing"
   (DESIGN:1114-1116).
2. Case (b): every 64 KB step allocates (⌊(conf+k−1)/cl⌋ > ⌊(conf−1)/cl⌋ for
   k ≥ cl), and the retries never confirm (IF11). The fourth try stops the file.
3. Either way the file is now **stopped**, not "in creation":
   - it is prefix-usable if `conf ≥ 42,496`;
   - its room is below 40,960, so no flush fits;
   - the normal switch rule finds no never-active file, so the worker holds.
4. The next creation starts:
   - in case (a) after ≥ 10 s (the window had no successful write);
   - in case (b) at the next tick.
5. The new file becomes a switch target after step 0 plus one 64 KB step.
6. Hold length at 30 KB/s: (a) ≈ 3 + 10 + 3 ≈ 16-18 s; (b) ≈ 6 ticks of 64 KB,
   ≈ 15 s. Both are far below 114.7 s.
7. Queued ranges are re-sent after the new file's first DURABLE flush. In a
   start-up catch-up at 30 KB/s, the oldest P records are re-sent at about
   t ≈ 60 s, against a ring span of 114.7 s.

**Recorded:** EVENTs `stop`, `hold start/end`, `segment create`, `switch`
(`full`); UHB b0, b24, b25; the panel after 3 s (Case 2 while it lasts).

**What is wrong.** The new 8.5 Errors vector (DESIGN:1888) expects "the
worker holds and resumes in the same file at its own `seg_end`" for "two failed
steps" and for "a 3 s burst". By the design's own rules neither case can
resume in the same file. A correct implementation therefore fails the test,
and an implementer chasing the test could weaken the FAT1 stop rule.

**Ruling: DIAGNOSABLE.**

**Fix needed (C1):**
- Restate the pass condition: "holds; resumes in the same file if it is still
  in creation; if it has stopped, switches to a never-active file; in no case
  sets `seg_end = 1,536` in a file that has been active, writes a region twice,
  or loses a boot record".
- Add one vector in which the step fails once in a **non-allocating** way, so
  that the resume path itself is exercised. Or fix IF11 (C2), so that
  vector (b) resumes in place.

### TE12 (timing-edge; own-entry rule). Death and pull during the IF7b first phase, at a 5 s boundary. DIAGNOSABLE

**Shape.**
- X goes bad shortly before a creation is due. The first phase (≤ 17 ticks,
  ≈ 4 s) therefore runs across a Nop boundary at which input dies.
- The operator runs the D script, and the pull comes later.

**Trace.**
- The phase does not touch the flush path. Each tick's flush is DURABLE before
  the creation step (4.3 steps 7-8), so `durable_tick` keeps advancing and D8
  can pass. META is allowed by D8 (b).
- The abandoned files hold only FILEHDRs. Their entries are in X, so they are
  not on the stick at all, and they hold no records (DESIGN:1138-1140).
- At the pull, the Mac copy shows the active file and the files ahead.
- E2 is mandatory (META), and the decoder requires `--raw` (`abandon` EVENT,
  10.2).

**Recorded:** everything in the rings and every window. The alias loop's CPU
time is charged to WRK (`wk_wrk`, `pre_wrk`), so an onset inside it is
annotated.

**Ruling: DIAGNOSABLE.** Fix needed: none.

### IF13 (instrumentation-fault; own-entry rule). The own entry's sector fails once **before** the step's data, then recovers. DIAGNOSABLE (tightening C3 recommended)

**Shape.** Between the fresh file's `open` and its step-0 `fsync`, the
own entry's sector Y is dirty (D1). The steps:
1. `pdflush` (`wb_kupdate`, about every 30 s for the block device inode, D5)
   writes Y.
2. That write fails transiently. The buffer loses its up-to-date bit (D3).
3. The step's DATA follows.
4. `fat_write_inode` re-reads Y from the stick (W6, D2). On the stick the slot
   is still free (name byte 0x00 or 0xE5). It writes size, attributes and start
   into the free slot (not the name, `fs/fat/inode.c:586-600`), and
   `sync_dirty_buffer` succeeds.

**What the rule does.**
- The `pdflush` failure lies **before** the last DATA record, so it is "ignored
  anywhere else in the window".
- The first worker DIR record after DATA is the successful write of Y, so step
  0 is **CONFIRMED**.
- But the stick now holds a nameless entry: exactly the case step 0's strictness
  exists to prevent (DESIGN:1122-1127).

**Consequences.**
- The file's FAT chain is linked (FAT1 succeeded), and its records are on data
  sectors.
- The Mac copy does not show it. If the free byte was 0x00 (end of directory),
  the Mac also stops listing the files that follow it (msdosfs behaviour
  UNVERIFIED).
- At the next creation the in-memory slot looks free. The alias loop takes it:
  `fat_iget` returns this file's inode, which is rejected (`st_size ≠ 0`), and
  the alias's **name** goes into the slot. If the file is still dirty when the
  next `fsync` writes the slot, the stick then shows the alias name with this
  file's start and size. Otherwise it shows a 0-byte alias file, and the data
  is reachable only by the raw image.
- No raw-image trigger of 10.2 fires: no `abandon`, `meta err`, `flush fail`
  or `stop`, `write_errs` = 0, and b30 is set only for a flush.
- The step's `fsync` does return `-EIO` (`AS_EIO`, D3), but that is recorded
  only in `last_errno`.

**How likely.**
- The window is open → `fat_write_inode`, about 5-50 ms. `pdflush`'s block
  device writeback runs about every 30 s. So the overlap probability is
  ≈ 2 × 10⁻³ per creation, and that write must fail transiently and the stick
  must recover within milliseconds.
- In total ≈ 10⁻⁶ per creation at the modelled sporadic rate, about 10⁻⁵ per
  run. A **persistent** refusal of Y does not reach this case: `fat_write_inode`'s
  write fails too, and the file is abandoned.

**Why still DIAGNOSABLE.**
- No record is destroyed.
- The decoder sees `(ring, seq)` ranges that the UHB `durable_next` reports as
  durable but that are missing from the copy, and a FILEHDR `seg` number missing
  between present ones.
- The stick stays untouched until the agents confirm (RUNBOOK E4), so the raw
  image can still be made and recovers every chunk under the run's nonce.

**Ruling: DIAGNOSABLE.**

**Fix recommended (C3)**, a few words of specification and no new mechanism:
- (i) at step 0, also require that no write record **of the own-entry record's
  sector** (any pid) with b1 set appears earlier in the window. The sector is
  known once the own-entry record is found.
- (ii) add to 10.2's "RAW IMAGE REQUIRED" list: a durable `(ring, seq)` gap or
  a missing FILEHDR `seg` of this run.
- (iii) add the matching 8.5 verdict vector.

### IF14 (instrumentation-fault; own-entry rule × names budget). IF7b plus wholesale eviction of the alias inodes. DIAGNOSABLE

**Shape.** IF7b with its first phase done. Each later creation relies on X's 16
lost slots still having **cached** inodes (15.3: "this assumes the rejected
inodes stay cached"). The design budgets for 5 evictions in all. But eviction
is driven by reclaim, and reclaim begins when the page cache has used up free
RAM:
- `MemFree` is ≈ 20.8 MB (telem logs; DESIGN:1521);
- every 2 MB segment stays in the page cache after it is written (only one page
  is dropped per file, 4.4 step 7);
- 3 files exist by about minute 3, then one more every ≈ 4.6 min, so RAM fills
  at about minute 28-33 (UNVERIFIED).

After that, the alias dentries are pruned first, as the oldest unused ones,
and then their inodes, which are untouched for 4.6 minutes between creations.
So all 16 can go together. A creation that meets 16 evicted slots repeats the
whole first phase: ≤ 153 names and 17 ticks.

**Arithmetic at the minimum budget (400).**
- Up to minute ≈ 28: 153 + 17 × (≈ 6 creations) ≈ 255 names.
- One wholesale eviction (+153 ≈ 408) exhausts the budget at the 9th or 10th
  creation, at about minute 30-33.
- The two files ahead then still give ≈ 9 minutes, so recording continues to
  about minute 39 or later.
- At the 16 KB-cluster budget (478) or the 32 KB one (990) the margin is
  larger.

**Recorded:** `inode reused`, `abandon`, `names budget`, and later
`MS DIR FULL`-style exhaustion with a hold and the panel (Case 2). Nothing is
silent.

**Ruling: DIAGNOSABLE.** S3's 15 minutes and the runbook's 30:00 are both
covered.

**Fix recommended:** restate 15.3's margin. "Covers 5 such" is per inode, while
eviction after the page cache fills is wholesale; the true bound is about one
wholesale event before about minute 33 at budget 400. Optionally, keep the ≤ 16
rejected alias descriptors open so that their inodes cannot be evicted. That is
a mechanism, so it is for a later round only if the reviewer wants it.

### IF15 (instrumentation-fault; own-entry rule × takeover). After a takeover, "the worker's pid" is another process. DIAGNOSABLE (wording and test recommended)

**Shape.**
- After a takeover the worker loop runs **inside the supervisor process**
  (DESIGN:893-903), so its writes carry the supervisor's pid (W9).
- The rule says "carrying the worker's pid". 4.2 defines the worker as "`pscol
  -w`, or the supervisor after a takeover", so the right reading is `getpid()`
  of the running instance.
- An implementation that keeps the original worker's pid (for example from the
  `ctl` op 2 registration) would find **no** own-entry record in any step-0
  window of instance 2. Then:
  - every attempt is abandoned (fast attempts, because the data succeeded);
  - no file is ever confirmed;
  - after the prepared space runs out the worker holds for the rest of the run.

**Is the wrong reading caught before the run?**
- 8.5's takeover test (DESIGN:1886) requires instance 2 to "create a fresh
  segment", which fails under the wrong pid, **if** the harness's S records
  carry the writing process's pid.
- 8.5 does not say how the harness assigns pids, and VFAT-FI has no takeover
  schedule.

**Recorded:** EVENT `takeover`, then `abandon` per tick, and the hold and panel.
Visible, not silent.

**Ruling: DIAGNOSABLE.** The text's own definition gives the right pid, and a
takeover is already a second fault.

**Fix recommended:**
- write "the pid of the process running this worker instance (`getpid()`; the
  supervisor's after a takeover)";
- require that the takeover vector's S records carry the writer's pid.

### OE11 (observer-effect; own-entry and hold rules). IF7b now keeps recording, so its failing-sector load lasts the whole run; TE10 holds paint the panel at start-up. DIAGNOSABLE

**Shape 1: IF7b load.**
- Under r6's literal reading, IF7b would have ended creation, and with it most
  of the failing writes of X.
- Under r7 the run continues, and X is written:
  - in every creation tick, once (the aliases);
  - in every flush, if the active file's entry is in X.
- Each failed write costs 10 tries with `mdelay(1)` and preemption off
  (`ms_psp.c:254-268`, `:304-326`). That is the same sustained load as OE9, now
  also in IF7b.

**Shape 2: TE10 holds at start-up.** A TE10 hold that lasts more than 3 s paints
the kernel panel from the timer interrupt, during the early-death window
(deaths before 36 s, 9.6).

**Recorded.**
- Load: S records with their durations and b1, `wk_wrk`/`pre_wrk`, the POLL
  `period` (as OE9).
- Panel: the paints fire at tick ≡ 125 mod 250, never at ≡ 0 mod 1250, where
  the Nop is (8.5 panel row), and `lc_flags` b5 marks them. A hold is UHB b0
  plus EVENT `hold start/end`.

**Ruling: DIAGNOSABLE.** The analyst can attribute both.

**Fix recommended:** adopt attempt-6 H4 (2), unchanged. Add "failing metadata
writes" to 10.5's collector-activity list, with the non-preemptible time per
second computed from S records, and flag an onset inside it as
`instrumentation-exposure`. IF7b makes this more likely to matter than it was
in attempt 6.

---

## 6. Section 16 statements: do I agree?

| Statement | My position |
|---|---|
| A6-1 / IF7b closed by the own-entry rule, with the order verified | **Agree.** I verified W1-W9 myself. All cited lines resolve. |
| The deliberate difference from my predecessor's text (a `pdflush` DIR record between DATA and the worker's first DIR makes step 0 not CONFIRMED) | **Agree.** It is stricter, it is justified by W7, and it costs only a name. |
| VFAT-FI IF7b timed from the first creation attempt after onset, not from META onset | **Agree.** META can show minutes before a creation is due. |
| 153 names (not 152) in the first phase, and ≤ 17 per later creation | **Agree** with the count. The eviction margin is understated (IF14). |
| 4.4 step 6 "IF7b ≤ 152" left as it was (it bounds fast attempts) | **Agree.** IF7b needs 16 fast attempts. |
| TE10 closed; optional fix 3 (tie the start-up step to the flush size) not adopted | **Agree.** Hold-and-resume suffices, and room grows ≥ 24,576 per tick after a resume. |
| A6-2 moved to worker start, EVENT `conlevel` | **Agree.** |
| A6-3 (a)-(g) | **Agree**, except the (e) wording "from 28 KB/s up … loses nothing" (C4). |
| A6-4 `*ppos` | **Agree.** |
| "No mechanism … added" | **Agree.** The EVENT string `conlevel` is the record A6-2 asked for. |

**AMBIGUOUS findings accepted by the designer in section 16:** none. Both
attempt-6 AMBIGUOUS findings were fixed, not accepted, and I rule them
DIAGNOSABLE.

---

## 7. Corrections and recommendations (consolidated; none blocking)

| # | Text | Closes |
|---|---|---|
| **C1** | 8.5 Errors TE10 vector: correct the pass condition (holds; resumes in the same file if it is still in creation, else switches to a never-active file; never `seg_end = 1,536` in a file that has been active; no region written twice; boot records intact), and add a non-allocating-failure vector for the resume path. | TE11 |
| **C2** | Attempt-6 H3, still open: judge "allocated" per try (a FAT1 success is needed only if this try's window shows a FAT1 write, or `mmu_private` was below the step's end before the try). Correct "the retry allocates nothing" for the short-`write()` / `vmtruncate` case. Add the vector. | IF11, TE11 (b) |
| **C3** | Step 0: no earlier failed write of the own-entry sector in the window. 10.2: a durable `(ring, seq)` gap or a missing FILEHDR `seg` makes the raw image required. One 8.5 verdict vector. | IF13 |
| **C4** | Summary 7, 4.8, R8, 15.6: "from 30 KB/s up the model loses nothing (0 of 700 runs); at 28 KB/s 1 of 700 whole-tick runs loses 10.8 s; at 25 KB/s 1 of 260 loses 15.2 s". | IF4 text |
| R1 | 4.6: the read-only rule ("no creation step") takes precedence over the TE10 hold's "with 64 KB steps". | TE10 wording |
| R2 | 4.4 step 4: "the worker's pid" = the pid of the running instance (`getpid()`; the supervisor's after a takeover); the takeover vector's S records carry the writer's pid. | IF15 |
| R3 | 15.3: restate the eviction margin for wholesale eviction after the page cache fills RAM (≈ minute 28-33, UNVERIFIED). | IF14 |
| R4 | Attempt-6 H4 (2): a decoder flag for failing-metadata load. Attempt-6 H5: an escape fast-attempt budget. Attempt-6 H6 leftovers (R11 note, N12, wall-time Nop spacing). | OE9, OE11, IF12, TE9, UL8, UL9 |

---

## 8. Attacks attempted that found nothing

| Attack | Result |
|---|---|
| A rejected alias's entry written before the own entry | Impossible. Alias entries reach the stick only through `sync_blockdev` (D1, W3). Closing an alias writes nothing. |
| FSINFO taken for the own entry | Impossible. It is class FSINFO, and it is written after (W8). |
| Another file's DATA moving the anchor | Impossible. The anchor uses the step's own FIBMAP sectors only. |
| The own-entry record outside the window (tick boundary) | Impossible. Synchronous driver (W9), and the window ends at the head read after `fsync` returns. |
| `fat_write_inode` not called at step 0 | Needs the inode cleaned by a third party (W5) between `write()` and `fsync`. No `sync()` caller exists, and `wb_kupdate` needs 30 s of age (D5). If it happens, the result is conservative in IF7b's geometry. |
| The PSCLOG directory inode, dirtied at every create (D4), writing a DIR sector early | It is written by `pdflush` with `wait = 0` (buffer only), then by a later `sync_blockdev`. Either way that is after the own entry, or by another pid. |
| A hold-and-resume livelock | None. Room grows ≥ 24,576 per tick after a resume. |
| A switch to a stopped or retired former active file | Excluded by "never been active". |
| A never-active file existing ahead of an active file in creation | Impossible. There is one creation at a time, and it is always the newest file. |
| A6-3 `conf` mapping wrong at the last step | Exact: the final step ends at `SEG` (v = 256). |
| `conlevel` call failing silently | Its return and `errno` go to an EVENT. Case 8 needs only root (`kernel/printk.c:292-300`). |
| `pread` moving the drain position | Not with `*ppos` (`fs/read_write.c:364-366`, `:404-405`). |

---

## 9. UNVERIFIED items this report depends on

1. When RAM fills with the segment files' page cache, and how wholesale the
   dentry and inode pruning is afterwards (IF14).
2. Whether the Mac's msdosfs stops listing at a 0x00 slot (IF13). It matters
   only for which files the copy shows, not for the raw image.
3. Whether Memory Stick write errors occur at all in this setup, and in which
   pattern (IF7b, IF13, TE11). The same premise underlies A1.
4. The sustained, as opposed to initially measured, write speed of the
   operator's stick (C4 margin between 28 and 30 KB/s).
5. That VFAT-FI (R18) can be built. If it cannot, the IF7b, IF13 and TE11 cases
   reach the hardware tested only by the host vectors, which is why C1 and C3
   ask for vectors.

---

## Appendix A. Model re-run (`sim_r5.py`, unmodified copy, whole-tick unless stated)

Settings: `collector_start=40`, `dur=1800`, `step_rule='rev'`, `resend='range'`,
98 failure events per 30 min.

| Speed | Seeds | Runs with loss | Max loss | Max hold |
|---|---|---|---|---|
| 25 KB/s | 9 only | 1/1 | 15.2 s | 22 s (reproduces the designer's figure) |
| 28 KB/s | 0-699 | **1/700** (seed 290) | 10.8 s | 24 s |
| 29 KB/s | 300-699 | 0/400 | 0 | – |
| 30 KB/s | 0-699 | 0/700 | 0 | 23 s |
| 32 KB/s | 0-299 | 0/300 | 0 | 23 s |
| 28, 30, 32 KB/s, per-operation model | 0-299 | 0/300 each | 0 | ≤ 10 s |

The model does not represent IF11, TE11, IF13 or IF14.
