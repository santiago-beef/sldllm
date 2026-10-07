# Gate G1, attempt 6: red team report

Artifact under review: `design/DESIGN.md` revision 5 (2,588 lines) and
`design/RUNBOOK.md` revision 5 (483 lines), both 2026-10-05, for G1 round 6.
Reviewer role: G1 red team, attempt 6. Fresh context. I did not write the
design or any earlier gate report.
Date: 2026-10-05.

**Scope: FULL.** WORKFLOW.md Amendment A1 is suspended for this round. The
authority for that is the human's own text: WORKFLOW.md "Amendments", A1
"Fallback" ("the human has pre-authorized one further round at *full* scope
(A1 suspended) with every red-team fix adopted"), the gate-log note of
2026-10-05 ("a pre-authorized round 6 at full scope ... if round 5 fails for an
in-scope reason"), and the user's instruction relayed with this task ("Go with
option 1 prepared to go with option 2 if necessary"). Round 5 did fail for
in-scope reasons (attempt-5 review A5-1 under D6; attempt-5 red team IF9).
SPOILED-DETECTED is therefore not available; a persistent single-sector
metadata refusal must be DIAGNOSABLE like everything else.

Note for the orchestrator: `gates/LOG.md` has no entry for round 5 yet (it
ends with the note of 2026-10-05). The round-5 results should be appended
before round 6 is recorded.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding, 9.6 included), `WORKFLOW.md` (Amendment A1 included),
`recon/syscon.md`, `recon/input.md`, `recon/build.md`, `recon/image2008.md`,
`gates/LOG.md`, `gates/G1-attempt4-review.md`, `gates/G1-attempt4-redteam.md`,
`gates/G1-attempt5-review.md`, `gates/G1-attempt5-redteam.md`,
`design/DESIGN.md`, `design/RUNBOOK.md`, `design/r5-scripts/*.py`.

Method:
- Source was only read, in `/home/ubuntu/psp/build/linux`. Every vfat, block
  layer and driver claim below was checked in this tree: `fs/fat`, `fs/vfat`,
  `fs/buffer.c`, `fs/sync.c`, `fs/fs-writeback.c`, `fs/ioctl.c`, `fs/open.c`,
  `fs/read_write.c`, `mm/filemap.c`, `kernel/printk.c`,
  `drivers/block/ms_psp.c`, `arch/mips/psp/ipl_sdk/memstk.c`,
  `arch/mips/kernel/scall32-o32.S`.
- No disassembly was needed; every claim I rely on is settled by source.
- I re-ran the designer's own model (`design/r5-scripts/sim_r5.py`) from a copy
  in my scratchpad, once as written and once with one rule changed to match the
  design text (Appendix A).
- After the work: `cd build/linux && sha256sum -c --quiet
  ../../handoff/gates/baseline-tree.sha256` printed nothing (exit 0), and
  `git -C work/linux status --porcelain` printed nothing. I wrote only this file
  and scratch files in my scratchpad.
- "DESIGN:n" and "RUNBOOK:n" are line numbers in the artifacts as they stand
  today. Kernel paths are relative to `/home/ubuntu/psp/build/linux`.
- Anything the source cannot settle is marked **UNVERIFIED**.

---

## Verdict: PASS on the BLIND criterion, with two AMBIGUOUS findings that must be closed in writing before Stage 2

No scenario is BLIND. Two scenarios are **AMBIGUOUS**. In both, the design
states the right goal but leaves out one rule that an implementer needs, and a
literal reading of the text as written would lose data:

| # | What is missing | What a literal implementation would do |
|---|---|---|
| **IF7b** (re-run, full scope) | 4.4 step 4 says step 0 "also needs **its** directory write (the new entry) to succeed" (DESIGN:1078-1079), but nothing says how the worker tells its own directory write apart from another directory write in the same window. | Under a refusing `PSCLOG` directory sector, every new file is abandoned forever, the name budget runs out in about 30 ticks, and recording stops once the prepared files are full (about 9 minutes later). |
| **TE10** (new, prefix path) | "Use and switch" lets the worker switch to a file "still in creation with that much room" and then sets `seg_end = 1,536` (DESIGN:1138-1142). It never excludes the **active** file itself. | When the active file is still being created and runs out of room (a burst or a failed step during start-up catch-up, or after a takeover), it "switches" to itself and writes again from offset 1,536, over records that are already on the stick. |

Both are fixed by a sentence of specification plus one Stage 3 vector each
(section 6). No new mechanism is needed. Because WORKFLOW requires every
AMBIGUOUS finding to be fixed, or accepted by the designer with a reason the
design reviewer agrees with, this report is a PASS only when those two are
closed in writing.

Everything else is **DIAGNOSABLE**:
- 33 of the 35 rows re-run from attempt 5 (attempt-5 IF7 is split into IF7a and
  IF7b here);
- 7 of my 8 new scenarios.

Three new findings do not block, but should be corrected, because the text
contradicts itself or the code:
- **IF11.** An allocating creation step that fails only on a data sector can
  never be CONFIRMED on its in-place retry.
- **OE9.** A persistent FSINFO refusal now leaves a sustained burst of
  non-preemptible driver retries, in a run that is counted.
- **TE9.** At every allocating step, the directory size reaches the stick before
  the FAT link does.

### In plain words (for a reader still learning the system)

- **What changed in revision 5.** Revision 4 asked `fsync` whether a save
  worked. `fsync` answers "something failed" if *any* sector it touched failed,
  including bookkeeping sectors that do not matter for the data. Revision 5
  instead reads the stick's own answer for every sector, which the kernel
  already records (the "S records"). It also uses the file system's layout to
  know which sector holds data and which holds the file table (FAT), a
  directory or FSINFO. So a single bad bookkeeping sector no longer stops the
  recording. That is the right idea, and I checked it line by line in this
  tree's code.
- **Why two items are AMBIGUOUS.** In each case the design says *what* must hold
  but not *how* the program decides it. The tricky case for IF7b looks like
  this:
  1. Several stale directory entries ("aliases", see 4.4 step 1) are written into
     the bad directory sector.
  2. A good new file is then created in the next sector.
  3. Its first save writes its own directory entry successfully, and then also
     tries, and fails, to write the bad sector holding the aliases.
  4. Unless the program is told which of those two directory writes is "its"
     own, it will think the new file failed, every time.

  In TE10 the rule for choosing the next file does not say "never the file you
  are already writing". A literal reading would make the program start the
  current file over from the beginning, overwriting saved records.
- **Why this is still a PASS on the BLIND rule.** In both cases the design's own
  invariants elsewhere point to the right behaviour:
  - "each region handed to `write()` once" (DESIGN:1175-1176);
  - the Stage 3 pass condition "no sector of a region handed to `write()`
    written twice" (DESIGN:1843);
  - the designer's own simulation, which never switches to a file already used.

  A correct implementation exists and is clearly intended, so the right label is
  AMBIGUOUS, not BLIND. But they must be fixed in the text, because Stage 2 is
  told to implement the text.

---

## Summary table

| ID | Group | Scenario | Attempt 5 | Attempt 6 |
|---|---|---|---|---|
| UL1 | unlisted-shape (H10) | LED read-modify-write writes back bit 4 during a suspension at S14 | DIAGNOSABLE | **DIAGNOSABLE** |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off | DIAGNOSABLE | **DIAGNOSABLE** |
| UL3 | unlisted-shape | Link stays one reply behind | DIAGNOSABLE | **DIAGNOSABLE** |
| UL4 | unlisted-shape | Valid frames, HOLD bit stuck | DIAGNOSABLE | **DIAGNOSABLE** |
| UL5 | unlisted-shape (H10) | LED operations during a suspended transaction, clean read-back | DIAGNOSABLE | **DIAGNOSABLE** |
| UL6 | unlisted-shape | The Nop breaks the link with no thread command in flight | DIAGNOSABLE | **DIAGNOSABLE** |
| UL7 | unlisted-shape | Two-stage H4: benign straddle at Nop k, death at Nop k+1 | DIAGNOSABLE | **DIAGNOSABLE** (recommendation adopted) |
| TE1 | timing-edge | Death at 5 s, 17 s, 36 s | DIAGNOSABLE | **DIAGNOSABLE** (≥ 30 KB/s; note on `MS SLOW`) |
| TE2 | timing-edge | Nop on a suspended thread | DIAGNOSABLE | **DIAGNOSABLE** |
| TE3 | timing-edge | Minute 14 in `fsync`, 29:50, link wrap, console blank | DIAGNOSABLE | **DIAGNOSABLE** |
| TE4 | timing-edge | Slow Nop, nested tick, preemption at outer return, H10 | DIAGNOSABLE | **DIAGNOSABLE** |
| TE5 | timing-edge | Nop between the load and store of an LED read-modify-write | DIAGNOSABLE | **DIAGNOSABLE** |
| TE6 | timing-edge | Early death while the first file is created on a slow stick | DIAGNOSABLE | **DIAGNOSABLE** |
| TE7 | timing-edge | Pull while the active file is still being created; directory size ≠ `conf` | DIAGNOSABLE | **DIAGNOSABLE** (decoder note: UHB `conf` units) |
| TE8 | timing-edge | Catch-up flush ends exactly at `conf`; creation step shares the page | DIAGNOSABLE | **DIAGNOSABLE** |
| IF1 | instrumentation-fault | Transient write failure spanning onset | DIAGNOSABLE | **DIAGNOSABLE** |
| IF2 | instrumentation-fault | Worker killed at minute 13-14 | DIAGNOSABLE | **DIAGNOSABLE** |
| IF3 | instrumentation-fault | Reader races; head moves backwards | DIAGNOSABLE | **DIAGNOSABLE** |
| IF4 | instrumentation-fault | 25-35 s burst; about 98 sporadic failing ticks | AMBIGUOUS | **DIAGNOSABLE** (range re-send + 30 KB/s gate; model re-run) |
| IF5 | instrumentation-fault | Failed `fsync` on an allocating flush | DIAGNOSABLE | **DIAGNOSABLE** (designer's contest of the residual: agreed) |
| IF6 | instrumentation-fault | Corrupt slot `seq`, forward head jump | DIAGNOSABLE | **DIAGNOSABLE** |
| IF7a | instrumentation-fault (A1 class) | Persistent refusal of the FSINFO sector | SPOILED-DETECTED | **DIAGNOSABLE** (with the OE9 caveat) |
| IF7b | instrumentation-fault (A1 class) | Persistent refusal of the `PSCLOG` directory sector | SPOILED-DETECTED | **AMBIGUOUS** (step-0 "its directory write" not identifiable as specified) |
| IF8 | instrumentation-fault (A1 class) | Persistent refusal of the FAT sector at the allocator | SPOILED-DETECTED | **DIAGNOSABLE** |
| IF9 | instrumentation-fault | A data region of a prepared file refuses writes after creation | BLIND | **DIAGNOSABLE** (escape adopted) |
| IF10 | instrumentation-fault | Chunks from another boot merged by `(ring, seq)` | AMBIGUOUS | **DIAGNOSABLE** (nonce-seeded CRC) |
| OE1 | observer-effect | MS driver hang with raised preempt count | DIAGNOSABLE | **DIAGNOSABLE** |
| OE2 | observer-effect | `statfs` FAT scan | DIAGNOSABLE | **DIAGNOSABLE** |
| OE3 | observer-effect | Collector load sets the H4 start-delay exposure | DIAGNOSABLE | **DIAGNOSABLE** |
| OE4 | observer-effect | Kernel-privileged `pscol`, stray store | DIAGNOSABLE | **DIAGNOSABLE** |
| OE5 | observer-effect | Collector exit frees a mousedev client mid-walk | DIAGNOSABLE | **DIAGNOSABLE** |
| OE6 | observer-effect | Stall panel paints for minutes | DIAGNOSABLE | **DIAGNOSABLE** |
| OE7 | observer-effect | Global `drop_caches` walk with preemption off | DIAGNOSABLE | **DIAGNOSABLE** (stays replaced) |
| OE8 | observer-effect | Driver `DBG` printk storm drawn with interrupts off | DIAGNOSABLE | **DIAGNOSABLE** (console level 4 adopted) |
| A1-OE3 | observer-effect | Who held the CPU while the thread was preempted mid-command | DIAGNOSABLE | **DIAGNOSABLE** |
| **IF11** | instrumentation-fault (new; incremental creation) | A creation step fails at a cluster boundary: data-only failure of an allocating step; short `write()` and `vmtruncate` | – | **DIAGNOSABLE** (text contradiction; correction required) |
| **IF12** | instrumentation-fault (new; bad-region escape) | A flaky stick (intermittent whole-stick errors) triggers the escape on healthy files | – | **DIAGNOSABLE** (trigger should be tightened) |
| **TE9** | timing-edge (new; prefix path) | Pull between an allocating step's directory write and its FAT write: on-disk size and chain disagree | – | **DIAGNOSABLE** |
| **TE10** | timing-edge (new; prefix × F1(a) × switch) | The active file still in creation runs out of room during catch-up; the switch rule admits the active file itself | – | **AMBIGUOUS** |
| **OE9** | observer-effect (new; A1 class at full scope) | A META run now counts, but a refusing FSINFO costs ≥ 10 driver retries with preemption off at every `fsync` for the rest of the run | – | **DIAGNOSABLE** (recommendation: data-only sync for flushes) |
| **OE10** | observer-effect (new) | Console log level 4 could remove a perturbation the 9.6 sessions had (prevent the failure) | – | **DIAGNOSABLE** |
| **UL8** | unlisted-shape (new) | The syscon's own watchdog trips because a Nop arrives late in wall time (lost ticks), not at an interleave | – | **DIAGNOSABLE** (recommendation: wall-time Nop spacing in the report) |
| **UL9** | unlisted-shape (new) | The thread sleeps forever in `msleep` (stage 17, uninterruptible, never woken) | – | **DIAGNOSABLE** (H0 path; recommend a row) |

---

## 1. Source facts the scenarios rest on (verified by me in this tree)

### 1.1 The order of writes inside one `fsync` on vfat

| # | Fact | Evidence |
|---|---|---|
| V1 | `do_fsync` writes the file's dirty data pages first (`filemap_fdatawrite`), then calls the file system's `fsync`, then waits on the data. | `fs/sync.c:78-106` (`:90`) |
| V2 | vfat's `fsync` is `file_fsync`. It runs `write_inode_now(inode, 0)`, then `write_super`, then `sync_blockdev`. | `fs/sync.c:55-76` |
| V3 | `write_inode_now` always uses `WB_SYNC_ALL`. `__sync_single_inode` clears `I_DIRTY`, runs `do_writepages`, then `write_inode(inode, wait = 1)`. A failed `write_inode` does not dirty the inode again. | `fs/fs-writeback.c:568-576`; `:166`, `:170`, `:174` |
| V4 | `fat_write_inode` re-reads the entry's sector with `sb_bread`, puts the **in-memory** `i_size` and start cluster into the entry, and with `wait` calls `sync_dirty_buffer`. That is a synchronous single-sector write, issued **before** `write_super` and `sync_blockdev`. | `fs/fat/inode.c:556-611` (`:606`) |
| V5 | `sync_blockdev` then writes every dirty buffer of the block device in page-index order: FSINFO, FAT1, the FAT mirror and **any other dirty directory sector**. | `fs/sync.c:69`; `fs/fat/misc.c:40-72` |

**Consequence.** Inside one step-0 window the S records come in this order:
1. the step's DATA records;
2. **one DIR record for the file's own entry** (V4);
3. then FSINFO, FAT1, FATM and any other dirty DIR sectors (V5).

All of them carry the worker's pid unless `pdflush` interleaves. This order is
what the IF7b fix needs.

### 1.2 Directory slots, inodes and aliases

| # | Fact | Evidence |
|---|---|---|
| V6 | `fat_add_entries` scans from position 0 and takes the first free run (`IS_FREE`). It writes the new entry into the buffer with `mark_buffer_dirty`, and writes synchronously only under `IS_DIRSYNC`. | `fs/fat/dir.c:1190-1270` (`:1207`, `:1212`, `:1256`, `:1267`) |
| V7 | `fat_build_inode` returns any cached inode whose `i_pos` equals the slot (`fat_iget`). `vfat_create` does not dirty the inode it is given. | `fs/fat/inode.c:276-296`, `:398-421`; `fs/vfat/namei.c:735-760` |
| V8 | `fat_file_release` writes nothing without the `flush` mount option. | `fs/fat/file.c:117-125` |

### 1.3 Allocation, failed writes and truncation

| # | Fact | Evidence |
|---|---|---|
| V9 | `__fat_get_block` allocates only for the block at `mmu_private` that starts a cluster, and advances `mmu_private` per mapped block. | `fs/fat/inode.c:55-93` (`:85`, `:93`) |
| V10 | A failed `prepare_write` inside `write()` calls `vmtruncate(inode, isize)` when the write extended the file. | `mm/filemap.c:2148-2163` (`:2162`) |
| V11 | `fat_truncate` sets `mmu_private` back to `i_size`, then `fat_free` invalidates the cluster cache and walks the chain to the last kept cluster through the FAT buffers. It calls `fat_fs_panic` if that entry reads FREE. | `fs/fat/file.c:285-301` (`:296`); `:216-283` (`:224`, `:252`, `:262-266`) |
| V12 | `fat_get_cluster` reads only the entries of the clusters **before** the one it maps. A FREE entry on that walk panics. | `fs/fat/cache.c:217-272` (`:241`, `:255`) |
| V13 | `fat_alloc_clusters` searches from `prev_free + 1` and copies each touched FAT buffer to the mirror (`fat_mirror_bhs`). `prev_free` starts from FSINFO's hint at mount. | `fs/fat/fatent.c:455-516` (`:476`, `:510`); `fs/fat/inode.c:1274-1275`, `:1314`, `:1361-1364` |

### 1.4 The driver, FIBMAP and the system calls

| # | Fact | Evidence |
|---|---|---|
| V14 | `psp_ms_transfer_bio` adds the partition start to `bi_sector` and returns `-EIO` at the **first** failing bio segment. Later segments of that bio are never attempted, so they have **no** S record. | `drivers/block/ms_psp.c:238-279` (`:250`, `:275`). The design cites `:234` for the addition (DESIGN:541, :1358); the line is `:250`. |
| V15 | Each sector is tried 10 times with `mdelay(1)` after each failure, inside `__bio_kmap_atomic`, so preemption is off. One failed try ends either at `INT_REG_ERR` before the data transfer (fast) or after the transfer at `ms_wait_ready` (about one sector-write time). Which one happens is UNVERIFIED. | `ms_psp.c:254-268`, `:304-326`; `arch/mips/psp/ipl_sdk/memstk.c:342-374` |
| V16 | `FIBMAP` needs `CAP_SYS_RAWIO`, runs `bmap` under `lock_kernel()`, and vfat's `bmap` is `generic_block_bmap` with `create = 0`. It returns 0 when unmapped or on error. | `fs/ioctl.c:60-76`; `fs/fat/inode.c:193-196`; `fs/buffer.c:2564-2574` |
| V17 | `pread` works on any file opened through `dentry_open` (`FMODE_PREAD`) and passes its own position. | `fs/open.c:684`; `fs/read_write.c:404-405` |
| V18 | `do_syslog` type 8 sets `console_loglevel`. | `kernel/printk.c:292-300` |
| V19 | This kernel has `sys_sync_file_range` (o32 number 4305, seven argument slots). | `arch/mips/kernel/scall32-o32.S:650` |

---

## 2. Attempt-5 scenarios re-run against revision 5

The kernel side changed only by K37 (seven geometry words, DESIGN:2570-2571),
so the kernel-side traces of attempts 4 and 5 still hold. Below I give, for each
scenario, what r5 changed that touches it, what is recorded, and the ruling.

### UL1 (H10). LED write-back of bit 4 during a suspension at S14. DIAGNOSABLE

**Unchanged:**
- `led_or & 0x10`, `lc_epc` = S14, `ms_delta ≥ 2`, S `rd_clr_or` (K6, K8, K19);
- `pre_cls`, `pre_wrk`, `pre_tot` name the holder (K35).

**Ruling: DIAGNOSABLE.**

### UL2. One foreign frame toggles mouse mode off. DIAGNOSABLE

POLL `pi_flags` b3/b4, row N10 (DESIGN:1562) and D7a are unchanged.

**Ruling: DIAGNOSABLE.**

### UL3. Link one reply behind. DIAGNOSABLE

Row N2b against the template's per-command `rx[2]` (DESIGN:1554), tested before
H6.

**Ruling: DIAGNOSABLE.**

### UL4. HOLD stuck with valid frames. DIAGNOSABLE

Row N11 (DESIGN:1563).

**Ruling: DIAGNOSABLE.**

### UL5 (H10). LED operations during a suspension, clean read-back. DIAGNOSABLE

N1m is reported with:
- the step;
- the suspension bound;
- `ms_delta`, `led_pid`;
- the holder (`pre_*`);
- the pre-registered harm-rate table (DESIGN:1551, 10.7 step 7).

The designer's statement that these "cannot be separated in one run" is an
acceptance I agree with: both leave identical records.

**Ruling: DIAGNOSABLE.**

### UL6. The Nop breaks the link with no thread command in flight. DIAGNOSABLE

Row WB, the ± 2-cycle listing and the "both results valid" benign rule are in
place (DESIGN:1565, 10.7 step 5).

**Ruling: DIAGNOSABLE.**

### UL7. Two-stage H4. DIAGNOSABLE

Attempt-5's recommendation is adopted:
- every WT record within ± 2 cycles is listed with its step and both results;
- `H4 two-stage` is printed as a candidate (DESIGN:2064-2068);
- there is a Stage 3 vector (DESIGN:1850).

**Ruling: DIAGNOSABLE.**

### TE1. Death at 5 s, 17 s, 36 s. DIAGNOSABLE (≥ 30 KB/s)

**Trace.**
- The rings are BSS from boot. The worker reads from the oldest record.
- The first flush comes one 64 KB step after the FILEHDR, and 64 KB steps
  continue while the active file's room is below 81,920 bytes (DESIGN:1067-1071).
- The designer's model puts the first complete drain 18-35 s after the worker
  starts at 30 KB/s (DESIGN:2536). I re-ran the model (Appendix A); the backlog
  shrinks every tick, so no boot record is overwritten.

**Note (not a finding).** On a stick below 30 KB/s, STICK never passes
(`MS SLOW`). The early-death exception requires STICK green (DESIGN:1813-1817),
so an early death on such a stick is an **abort**:
- recording still runs, and RUNBOOK:248-250 has the operator copy `PSCLOG`;
- but the post-death script D is not done, so H6 against H7 is lost for that
  occurrence.

This is a policy choice I accept: the abort costs no run, and the gate is what
makes the IF4 claim hold. RUNBOOK B could say that an early death seen together
with `MS SLOW` should still be followed by section D before the pull, because
it costs nothing.

**Ruling: DIAGNOSABLE.**

### TE2. Nop on a suspended thread. DIAGNOSABLE

`lc_epc`/`lc_r` give the P6 step with `j` (K8). Unchanged.

**Ruling: DIAGNOSABLE.**

### TE3. Minute 14 in `fsync`; 29:50; 16-bit link wrap; console blank. DIAGNOSABLE

- D8 now allows `META` (RUNBOOK:374), and META no longer paints the panel
  (DESIGN:636). So a META run can pass D8; it is not stuck in D8 (c).
- 16-bit links fall back to `(tick, Count)` pairing (DESIGN:1980).
- A console blank is still recorded (N4).
- With console level 4 (OE10), level-4 printk lines no longer redraw the
  console. That changes nothing in a healthy run, which prints nothing.

**Ruling: DIAGNOSABLE.**

### TE4. Slow Nop, nested tick, preemption at the outer return, H10. DIAGNOSABLE

K9, `lc_flags` b4 and `pre_*` are unchanged.

**Ruling: DIAGNOSABLE.**

### TE5. Nop between the load and store of an LED read-modify-write. DIAGNOSABLE

`LEDRMW` label and row LEDSPLIT (DESIGN:1566, :2009).

**Ruling: DIAGNOSABLE.**

### TE6. Early death while the first file is created on a slow stick. DIAGNOSABLE

As TE1. The first flush needs only `conf ≥ 1,536 + 40,960`. A stick below
30 KB/s is gated out.

**Ruling: DIAGNOSABLE.**

### TE7. Pull while the active file is still being created; directory size ≠ `conf`. DIAGNOSABLE

**What r5 changed.**
- Every non-FILEHDR chunk's CRC is seeded with the boot nonce (DESIGN:1902-1905).
  A stale chunk of another boot in the tail `[conf, conf + k)` therefore fails its
  CRC.
- A chunk above the file's confirmed extent is listed, not merged
  (DESIGN:1929-1931).
- E1 step 5 says the decoder may ask for the image (RUNBOOK:408-414).

**Decoder note (minor).**
- UHB `seg` stores the creating file's `conf` "in units of 8,192 bytes (0-256)"
  (DESIGN:1919).
- Every `conf` is 1,536 + n × 8,192 or 1,536 + j × 65,536, so it is never a
  multiple of 8,192.
- Read from the UHB, the extent is therefore always 1,536 bytes short of the
  true `conf`.
- Only a maximal catch-up flush can end within 1,536 bytes of `conf`. Its RECS
  chunk ends at least 6,596 bytes below `conf` (34,364 ≤ 40,960 − 6,596), so only
  trailing KMSG, EVENT or PAD chunks of that flush could be listed instead of
  merged. Records are not affected.

**Recommendation:** store `conf` in 512-byte units (13 bits), or derive the
extent from the `stop` EVENT and the last confirmed step.

**Ruling: DIAGNOSABLE.**

### TE8. Catch-up flush ends exactly at `conf`; the creation step shares the page. DIAGNOSABLE

**What r5 changed.** The verdicts are per window (DESIGN:1383-1397).

**Trace.**
1. The flush's `fsync` writes the shared page's buffers 0-2 in the flush window.
2. The step's `write()` comes after it (4.3 steps 7-8) and dirties buffers 3-7.
3. Those go through the "confused" path (buffer 0 is clean), one bio per buffer,
   in the step's window.

So each verdict sees only its own sectors. Nothing allocates below `conf` (V9).

**Ruling: DIAGNOSABLE.**

### IF1. Transient write failure spanning onset. DIAGNOSABLE

**What r5 changed: range re-send.** A FAILED flush's records are queued by
`seq` range and re-sent after the next DURABLE flush, and a DURABLE flush is
durable for its own records (DESIGN:1246-1269).

**Trace.**
1. During the outage each flush goes to fresh space (F1(a)).
2. After it, the first DURABLE flush carries new records.
3. From the next tick the queued ranges go first, inside the cap.
4. EVENT and KMSG stay queued until a DURABLE flush carries them.
5. The verdicts come from the data sectors, so a recovered stick is recognised
   at the first good data write.

**Ruling: DIAGNOSABLE.**

### IF2. Worker killed at minute 13-14. DIAGNOSABLE

**Trace.**
1. The supervisor takes over in-process, with no allocation.
2. It seeks to `durable_next`, which is the start of the oldest queued range, so
   failed ranges are covered.
3. It creates a fresh file.

**r5 additions checked.** The new instance has not seen the old instance's
inodes:
- An old abandoned inode has `st_size = 1,536` and is rejected by size.
- A size-0 inode has `i_start = 0` (`fs/fat/misc.c:88-96`) and is safe to write
  through, as DESIGN:1053-1059 says.
- The boot nonce is passed to the new instance (DESIGN:902-903).

**But see TE10.** A fresh file after a takeover is active while still being
created, during a large catch-up. That is exactly where the literal switch rule
goes wrong.

**Ruling: DIAGNOSABLE** (conditional on TE10's fix, which is a separate row).

### IF3. Reader races; head moves backwards. DIAGNOSABLE

**Unchanged:** the resync on `head_regress` (DESIGN:941-943).

**Checked for r5.** The S-window `pread`s do not move the drain position (V17),
and the range re-send uses `lseek` (counted as `ring_rewinds`, which does not
turn REC red). Neither can be mistaken for a head regress.

**Ruling: DIAGNOSABLE.**

### IF4. 25-35 s burst; about 98 sporadic failing ticks. DIAGNOSABLE (was AMBIGUOUS)

**Both attempt-5 fixes are in place:**
- range-based durability (DESIGN:1246-1262);
- a throughput gate at 30 KB/s (DESIGN:1407-1410, 8.2 STICK).

**I re-ran the designer's model** (`sim_r5.py`, 60 runs per point, Appendix A):
- 0 s lost at 30-100 KB/s under both failure models;
- at 25 KB/s, whole-tick model: 0.3 s in 1 of 60 runs (the design reports 0
  over 200 runs; the difference is seed noise, and 25 KB/s is below the gate).

**Two things the model does not include:**
1. **The IF11 contradiction.** Under the design text, a retried allocating step
   can never be confirmed. With that rule added, the model still loses nothing at
   ≥ 30 KB/s, but uses about twice as many files under per-operation failures
   (9 → 17 per 30 min).
2. **Failed I/O is charged at normal speed.** A failed sector really costs up to
   10 × (try + 1 ms) (V15). That lengthens failing ticks but does not change what
   happens after recovery, which is where loss is decided. UNVERIFIED in size.

**I agree with the 30 KB/s gate** instead of my predecessor's 35 KB/s: the
model's margin holds, and the constant is one number to change.

**Ruling: DIAGNOSABLE.**

### IF5. Failed `fsync` on an allocating flush. DIAGNOSABLE; the designer's contest is agreed

**The core claim holds.** Every flush ends at or below `conf` ≤ `mmu_private`,
so `__fat_get_block` maps and returns before allocating (V9).

**The designer's contest of attempt-5's residual is correct in this tree:**
- a failed `write()` truncates only if it extended the file
  (`mm/filemap.c:2162`, V10);
- a flush never extends;
- `fat_get_cluster` reads only entries before the cluster it maps (V12), so a
  flush below `conf` never reads the unconfirmed link L → c.

**One related path the design does not mention (IF11).** A **creation step's**
failed `write()` does truncate: `vmtruncate` → `fat_truncate` → `fat_free`
invalidates that file's cluster cache and walks its chain (V11). It walks only
confirmed links, so it panics only over silent loss (R11). It does change
`mmu_private`; see IF11.

**Ruling: DIAGNOSABLE.**

### IF6. Corrupt slot `seq`, forward head jump. DIAGNOSABLE

**Unchanged:** skip-and-count and the `(tick, Count)` pairing fallback.

**r5 adds:** a window with a skipped `seq` makes the operation FAILED
(DESIGN:1393-1395). That is conservative.

**Ruling: DIAGNOSABLE.**

### IF7a. The FSINFO sector refuses writes for the rest of the run (A1 class, full scope). DIAGNOSABLE (with the OE9 caveat)

**Trace (V1-V5).**
1. Every `fsync` re-reads FSINFO with `sb_bread` (it is not up to date after a
   failure), marks it dirty, and `sync_blockdev` fails to write it.
2. `fsync` returns `-EIO`.
3. **Flush verdict.** The flush's data sectors were written first (V1) and have
   error-free DATA records, so it is DURABLE (DESIGN:1399-1403): UHB b30, EVENT
   `flush meta err` at most once per 10 s, `durable_tick` advances, no panel.
4. **Step verdicts.** Data, FAT1 and (for step 0) the file's own directory write
   (V4) succeed; FSINFO is tolerated (DESIGN:1080). Files keep growing, new files
   are created, and directory entries reach the stick, so even the Mac copy is
   complete.
5. **Display.** META on line 6 in about 1-2 s (not red), the FSINFO class in the
   EVENT. The runbook makes the raw image mandatory and the run counts
   (RUNBOOK:316-322).

**Recorded:** everything, as in a healthy run, plus the META evidence.

**Caveat (OE9).** Every `fsync` for the rest of the run costs ≥ 10 failed tries
with preemption off. That is a sustained perturbation in a run that is counted.
It is recorded and attributable, so it does not change this ruling, but it
needs a decoder flag and a better flush sync (OE9).

**Ruling: DIAGNOSABLE.**

### IF7b. The `PSCLOG` directory sector X refuses writes for the rest of the run (A1 class, full scope). **AMBIGUOUS**

**What the design intends** (DESIGN:2415-2433):
- Flushes stay DURABLE.
- New files whose entry would fall in X are abandoned at step 0.
- Each later attempt meets the cached inodes of those abandoned files at the
  same slots ("aliases"), rejects them, and opens again in the same tick.
- After at most 16 ticks a fresh file lands in sector X + 1 and works.
- Cost: at most 152 names; recording never stops.

**Where it breaks. Trace in this tree for the tick in which the fresh file
finally lands in X + 1:**
1. The tick's flush has already run. Its `fat_write_inode` re-read X, edited the
   active file's entry, and failed to write it. X is now clean and not up to date
   (V4; `fs/buffer.c:128-146`).
2. Creation, alias loop. Each `open(O_CREAT|O_EXCL)` scans from slot 0 (V6).
   `sb_bread` re-reads X from the stick, where the slots are free, so each open
   lands on a free-on-disk slot of X. `fat_iget` returns the cached inode, and the
   worker rejects it. Each alias's own entry is written into X's buffer with
   `mark_buffer_dirty` (V6). **X is now dirty.**
3. The fresh open takes the first slot of X + 1. Its entry is in X + 1's buffer,
   which is dirty too.
4. Step 0: `write()` of 1,536 bytes, then `fsync`:
   - DATA records (V1);
   - `fat_write_inode` of the fresh inode writes **X + 1**, successfully (V4);
   - `write_super` dirties FSINFO;
   - `sync_blockdev` writes FSINFO, FAT1, FATM and **X**, which **fails** (V5).
5. So step 0's window holds a **successful** DIR write of X + 1 (its own entry)
   and a **failed** DIR write of X (the aliases' entries).

**What the design specifies.** "Step 0 also needs its directory write (the new
entry) to succeed" (DESIGN:1078-1079). Nothing in 4.4, 4.8 or 10 says how the
worker knows which DIR record is "its":
- The worker has no API that gives its entry's sector: `FIBMAP` on the directory
  fails, because directories have no `bmap` (V16; `fat_fill_inode` gives
  `fat_aops` only to regular files).
- The 8.5 verdict vectors test only "directory failed at step 0 → abandoned"
  (DESIGN:1851). An implementation that treats **any** failed DIR record in the
  step-0 window as "its" passes those vectors.

**Consequence of that implementation:**
- Every fresh file in X + 1 is abandoned, every tick.
- Each tick costs about 17 names (16 aliases plus one abandon). A budget of
  478-990 names (`min(999, free slots − 16)`, DESIGN:1114-1120) is gone in about
  28-58 ticks.
- After that no file can be created. The active file and the two files ahead last
  about 9 minutes.
- Then the worker holds, and the rings overwrite.
- A death after that leaves only panel photographs: **S2 and S4 fail**. That
  would be BLIND.

**What a correct implementation can do.** By V1-V5, the file's own entry is
written by `fat_write_inode`'s `sync_dirty_buffer`:
- **after** the step's data;
- **before** `write_super` and `sync_blockdev`;
- with the worker's pid.

So "the first DIR-class S record with the worker's pid after the step's last
DATA record in the window" is the file's own entry. A `pdflush` record has
another pid. Every other DIR record in the window is META evidence only. With
that rule, the design's own trace holds, and I would rule DIAGNOSABLE.

**Why AMBIGUOUS and not BLIND.**
- The design states the right criterion ("its" write).
- Its traces (15.3) and the VFAT-FI IF7b pass condition (DESIGN:1843: "creation
  continues ... aliases rejected, ≤ 160 names") assume the correct one.
- The mechanism to identify it is simply absent. Stage 2 cannot implement a rule
  the design does not give, and VFAT-FI, the only test that would catch the wrong
  rule, is UNVERIFIED as buildable (R18).

**Fix needed:**
1. In 4.8 / 4.4 step 4, define the step-0 own-entry write as the first DIR-class
   S record with the worker's pid after the step's last DATA record in the step's
   window, with the order argument (`fs/sync.c:78-106`, `:55-76`;
   `fs/fs-writeback.c:166-174`; `fs/fat/inode.c:556-611`). Say that a missing
   own-entry record, or a failed one, abandons; that other DIR failures in the
   window are META evidence only; and that a `pdflush` DIR record is ignored.
2. Add an 8.5 verdict vector: a step-0 window with own DIR OK, then another DIR
   sector failing → CONFIRMED. Add the reverse → abandoned.
3. Tighten the VFAT-FI IF7b pass condition: a fresh file CONFIRMED within 20 ticks
   of META onset, and every later creation costing ≤ 17 names.

**in_scope_under_A1:** no (exactly the A1 class). It is in scope now.

### IF8. The FAT sector F at the allocator refuses writes (A1 class, full scope). DIAGNOSABLE

**Trace (V9, V13).**
1. **Flushes** never allocate, so they never write F.
   - If the active file's chain has entries in F and the cluster cache misses,
     `fat_get_cluster` re-reads F from the stick. Its pre-failure links are
     there, and only entries before the target are read (V12).
2. **The creating file.** Its allocating step dirties F (EOF for c, and maybe the
   L → c link). FAT1 fails, so the file stops. It is prefix-usable if
   `conf ≥ 42,496`.
3. **New attempts** start next tick, because data, directory and mirror writes
   succeeded (DESIGN:1108-1113). Each step 0 allocates at `prev_free + 1` inside
   F, its FAT1 write fails, and it is abandoned. `prev_free` advances one cluster
   per attempt.
   - After ≤ 128 attempts (FAT32, 128 entries per sector) the allocator leaves F,
     and the next file is CONFIRMED.
   - Fast attempts are capped at `min(400, budget/2) ≥ 200`.
4. **What the stick holds afterwards.**
   - The ≤ 128 abandoned files have directory entries that point at clusters FREE
     in FAT1 but EOF in the mirror (`fat_mirror_bhs`, V13).
   - They hold no records. Their Mac copies may fail, which makes E2 mandatory
     (RUNBOOK:418-423), as does META.
   - About 9 minutes of prepared files cover the time to recover.

The step verdict needs FAT1, not the mirror, which is right, because Linux reads
only FAT1 (DESIGN:1364-1367). META clears when "bypassed" (DESIGN:1347-1350).

**Recorded:** everything. The ≤ 128 retry storms (OE9 mechanism) last about 30-40 s.

**Ruling: DIAGNOSABLE.**

### IF9. A data region of a prepared file refuses writes after its creation. DIAGNOSABLE (was BLIND)

**Fix adopted** (DESIGN:1270-1285). After three consecutive FAILED flushes with
a DATA-sector error while another write in the same windows succeeded:
- the active file is retired;
- the worker switches to the next usable file, or holds and creates past the
  allocator.

**Trace (2 MB region, F1(a) passing each failed region).**
- About 3 ticks lose durability. The ranges are queued and re-sent after the next
  DURABLE flush.
- Even at 25 KB/s the hold, if any, is far below 114.7 s (the designer's model
  says ≤ 56 s at 25 KB/s; I did not re-run this part).
- The verdicts come from S records, so a whole-stick outage, where metadata
  fails as well, does not trigger the escape.

**Two edges (new scenarios):**
- a flaky stick can trigger the escape on healthy files (IF12);
- when the active file is still being created, the switch rule has a hole (TE10).

**Ruling: DIAGNOSABLE.**

### IF10. Chunks from another boot merged. DIAGNOSABLE (was AMBIGUOUS)

All five parts of attempt-5 G3 are adopted (DESIGN:1922-1937):
- run selection by FILEHDR `run` and nonce;
- other runs listed and excluded from the raw-image rule;
- chunks above the confirmed extent listed, not merged;
- `(ring, seq)` conflicts reported;
- and, beyond what was asked, every non-FILEHDR CRC seeded with the nonce.

A rehearsal chunk, or a stale tail of a deleted file of another boot, fails its
CRC outright.

**Residual R28** (nonce collision) is accepted: about 2⁻³², and a collision
would surface as conflicts.

**Ruling: DIAGNOSABLE.**

### OE1. Memory Stick driver hang with a raised preempt count. DIAGNOSABLE

Marker and panel are unchanged (K20, K30). r5 adds `pread`s and `FIBMAP`s, which
are not stick writes, so exposure is not raised beyond r4's.

**Ruling: DIAGNOSABLE.** I agree with R12.

### OE2. `statfs` FAT scan. DIAGNOSABLE

There is no `statfs`. r5's `stat` and `readdir` of `PSCLOG` (names budget,
DESIGN:1114-1120) do not scan the FAT.

**Note.** The first allocation after mount searches from FSINFO's hint (V13). If
the Mac left an invalid hint, `prev_free` restarts at cluster 2 and step 0 of
the first file scans the used part of the FAT once (reads only). That only
delays STICK, and an abort costs no run.

**Ruling: DIAGNOSABLE.**

### OE3. Collector load sets the H4 start-delay exposure. DIAGNOSABLE

K12 is unchanged. r5's extra collector work (two `pread`s per tick, ≤ 3 `FIBMAP`
per step, the alias loop) is collector CPU time and is charged to class WRK in
`wk_wrk` and `pre_wrk`.

**Ruling: DIAGNOSABLE.**

### OE4. Kernel-privileged `pscol`, stray store. DIAGNOSABLE

The guards are extended to the S-window and FIBMAP tables (DESIGN:913-918). I
accept R16.

**Ruling: DIAGNOSABLE.**

### OE5. Collector exit frees a mousedev client mid-walk. DIAGNOSABLE

The takeover-to-PROCS annotation is in place (DESIGN:2056-2057).

**Ruling: DIAGNOSABLE.**

### OE6. Stall panel paints for minutes. DIAGNOSABLE

N1p and `lc_flags` b5 are unchanged. META no longer paints, so there are fewer
paints.

**Ruling: DIAGNOSABLE.**

### OE7. Global `drop_caches`. DIAGNOSABLE

It is still replaced by one-page `fadvise64_64` through `syscall()`. Attempt 5
verified the marshalling.

**Ruling: DIAGNOSABLE.**

### OE8. Driver `DBG` printk drawn with interrupts off. DIAGNOSABLE

**Adopted:** console level 4 (DESIGN:884, :1621). The driver's lines carry the
default level 4, so they reach the log and the KMSG chunks but are not drawn
(V18).

**What remains** is the driver's own retry time (V15), which the design states
in 7.1 and which OE9 quantifies.

**Note for G2.** "`syslog(8, NULL, 4)`" must be the kernel call
(`syscall(__NR_syslog, 8, NULL, 4)` or `klogctl`, as telem does for type 3,
recon/input §6.1). uClibc's `syslog(3)` is the userland logger, and calling it
with these arguments would not set the level.

**Ruling: DIAGNOSABLE.**

### A1-OE3. Who held the CPU while the thread was preempted mid-command. DIAGNOSABLE

K35 is unchanged (DESIGN:696-709).

**Ruling: DIAGNOSABLE.**

---

## 3. New scenarios

### IF11. A creation step fails at a cluster boundary (instrumentation-fault; incremental creation). DIAGNOSABLE (correction required)

**Shape.** An 8 KB step crosses a cluster start (1 step in 4 at 32 KB clusters),
or a 64 KB step crosses one (always at start-up and during holds). Its
`write()` succeeds, and the `fsync` writes FAT1 successfully, but one DATA
sector fails transiently. This is in scope (sporadic error).

**What the design says:**
- (a) "Anything else failed (a data sector, a short `write()`): the step is
  retried in place at the next tick, up to 3 times. Its blocks are mapped ... and
  its clusters are linked on the stick (FAT1 was written), so the retry allocates
  nothing" (DESIGN:1085-1089).
- (b) A step is CONFIRMED only if "no FAT1 write in its window failed (and at
  least one succeeded if the step allocated: a step allocates if
  ⌊(conf + k − 1)/cl⌋ > ⌊(conf − 1)/cl⌋ ...)" (DESIGN:1072-1079).

**Trace.**
1. The retry has the same `conf` and `k`, so by the formula it "allocates" and
   needs ≥ 1 successful FAT1 record in its window.
2. By (a) and V9 it allocates nothing. The FAT buffers were written by the first
   try's `fsync` and are clean, so the retry's window has **no** FAT1 record.
3. The retry can never be CONFIRMED, however good the stick is.
4. Three retries later the file **stops** (DESIGN:1089). It is prefix-usable at
   `conf`, and a new file is needed.

**The short-`write()` variant contradicts (a) too.**
1. If the first try's `write()` failed in `prepare_write` (for example a FAT read
   error during the allocator's search), `generic_file_buffered_write` calls
   `vmtruncate` (V10).
2. `fat_truncate` resets `mmu_private` to `i_size` (V11).
3. So the retry **does** allocate again.
4. That path also invalidates the creating file's cluster cache and walks its
   chain (V11). It is harmless, because the walked links are confirmed, but if the
   creating file is also the active (prefix) file, later flushes re-walk the FAT
   on cache misses (reads only).

**What is recorded.** The step's window, `stop` EVENT, UHB b24, and the new
file's creation. No record is lost: flushes stay below `conf`.

**Effect, measured with the designer's own model** (Appendix A; the rule "a
retried allocating step is never confirmed" added):

| Model | Files per 30 min (as modelled → as written) | Lost |
|---|---|---|
| Per-operation failures, 25-100 KB/s | 9.0-9.4 → 11.1-17.1 | 0 s at every speed |
| Whole-tick failures, 25-100 KB/s | 19.4-27.9 → 19.5-33.6 | 0 s at ≥ 30 KB/s; 2.1 s in 4/60 runs at 25 KB/s (below the gate) |

**Interaction with TE10.** At start-up every 64 KB step allocates. A
data-only failure then means four ticks with no growth while catch-up flushes
use room, which is exactly TE10's trigger.

**Ruling: DIAGNOSABLE.** Nothing is lost at ≥ 30 KB/s, and every event is
recorded.

**Fix needed** (a correction, not a new mechanism):
- Define "allocated" per **try**: a FAT1 success is required only if this try's
  window shows a FAT1 write, or if `mmu_private` before the try was below the end
  of the step.
- Correct the sentence "the retry allocates nothing" for the short-`write()`
  case, citing V10 and V11.
- Add an 8.5 vector: an allocating step with one failed DATA sector, then a clean
  retry → CONFIRMED.
- Update the model.

### IF12. A flaky stick triggers the bad-region escape on healthy files (instrumentation-fault; bad-region escape). DIAGNOSABLE (trigger should be tightened)

**Shape.** For 30-60 s the stick refuses a random 50-80 % of sector writes: a
loose contact, or a card in thermal or voltage trouble. This is in scope
(transient, bursts of any length). It is neither a whole-stick outage (some
writes succeed) nor a bad region.

**Trace.**
1. A flush window has 3-8 DATA writes and 2 metadata writes (directory,
   FSINFO).
2. At 70 % failure, a flush is FAILED with near certainty, and "some other write
   in the same windows succeeded" holds about half the time (1 − 0.7² ≈ 51 %).
   So three consecutive such flushes happen within a few ticks.
3. **The active file is retired** (DESIGN:1270-1276), then the next, then the
   last. About 6 MB of prepared, healthy space is discarded.
4. The worker holds, and creation steps (64 KB) fail.
5. Next attempts are **fast**, because some write in each window succeeded
   (DESIGN:1108-1113). They use up the fast-attempt budget
   (`min(400, budget/2)`) and names at one per tick.
6. When the flaky period ends, a new file is created at 64 KB steps, and the
   queued ranges are re-sent.

**Records.** If the flaky period plus creation is ≤ about 100 s, nothing is lost
(the rings hold 114.7 s), as for a whole-stick burst. Every retire, abandon and
hold is in EVENTs and UHB. The S records show errors spread over every sector
class, unlike IF9, where they sit at `seg_end`.

**Ruling: DIAGNOSABLE.** The loss bound is that of an accepted whole-stick
burst (4.5 Case 2, DESIGN:4.6 "≤ 90-100 s lossless").

**Recommendation** (not required):
- Fire the escape only when, in all three windows, every metadata write and every
  write outside the active file succeeded, and the failed DATA sectors start at the
  window's own `seg_end` region.
- After a retire, require the next file to fail the same way before retiring it
  (so a flaky stick costs one file, not three).
- Count fast attempts caused by escapes against a separate, small budget, so a
  flaky minute cannot use up the fast attempts that IF8 needs later.

### TE9. Pull between an allocating step's directory write and its FAT write (timing-edge; prefix path). DIAGNOSABLE

**Shape.** This answers "the spare's directory entry size and its confirmed
prefix disagree after a pull". In every allocating step's `fsync`, the
directory entry with the **new** size is written by `fat_write_inode` before
`sync_blockdev` writes the FAT link of the cluster that size covers (V2-V5). A
battery pull in that interval leaves an entry whose size reaches past the end of
its chain on the stick. Step 0 has the same interval: an entry pointing at
cluster c, while FAT[c] is still FREE.

**How often.** The interval is the directory sector plus FSINFO (tens of ms,
UNVERIFIED), at roughly 0.2 allocating steps per second while a file is being
created. That is about 1 % of pulls, and more if the pull falls inside a
start-up or hold creation.

**Trace.**
- **Records.** Every flush is below the **previous** `conf`, which the chain on
  the stick covers. Nothing durable is affected, and the decoder is correct by
  construction.
- **The Mac copy.** It reads the file up to the end of its chain and then fails
  on the missing cluster (macOS behaviour UNVERIFIED). Either the copy fails or it
  is short.
- **The runbook.** "a file failed to copy" makes E2 mandatory (RUNBOOK:422-423).
  If the copy is silently short, that file holds RECS and is not 2 MB, and if it
  was the file being created at the pull, E1 step 5 says the decoder may ask for
  the image. E4 keeps the stick untouched until then (RUNBOOK:448-450).
- **The raw image** recovers every chunk under the run's nonce.

The same holds for a pull during a prefix flush. The flush lies below `conf`, the
entry's size already covers it, and a torn chunk fails its CRC. Its records were
not durable and are counted in `DUR`.

**Ruling: DIAGNOSABLE.**

**Recommendation.** State the order (size before link) in R11, and have the
decoder name this case when the raw image shows a file whose size exceeds its
chain by less than one step.

### TE10. The active file is still being created and runs out of room during catch-up; the switch rule admits the active file itself (timing-edge; prefix × F1(a) × switch). **AMBIGUOUS**

**Shape.** The active file A is still being created. That is the case:
- at start-up;
- after a takeover;
- after a switch into a file in creation (UHB b25).

The worker is in catch-up, so each flush is up to 40,960 bytes. Then one of
these happens (all in scope):
- a whole-stick burst of a few seconds;
- a creation step fails twice in a row (IF11 makes this certain for any
  data-only failure of a 64 KB step);
- two flushes fail.

Each failed catch-up flush still moves `seg_end` forward by its length (F1(a),
DESIGN:957-958; "≤ 40 KB for a catch-up flush", DESIGN:1302).

**Trace, with numbers.**
1. The start-up rule makes steps 64 KB while room < 81,920 (DESIGN:1067-1069).
   Room is at most about 81,920 + 65,536 after a good step.
2. Two ticks without growth, with 40,960-byte flushes, take room below 40,960.
3. Then "the next one would not fit" (`seg_end + 40,960 > conf`).
4. **The rule as written** (DESIGN:1138-1142): "the worker **switches** to the
   oldest file that is complete, or prefix-usable with room
   (`1,536 + 40,960 ≤` usable limit), or still in creation with that much room:
   `seg_end = 1,536`".
5. A itself is "still in creation" with `conf ≥ 42,496`, so it meets
   `1,536 + 40,960 ≤ conf`, and at start-up it is the **oldest** (only) file.
   Nothing in the text excludes the active file.
6. So a literal implementation sets `seg_end = 1,536` in A. The next DURABLE
   flush (after the burst, or the moment it is written) **overwrites A's records
   from offset 1,536: the boot records**, which are already on the stick.

**What is recorded.** The overwrite itself is invisible to the design's verdicts:
the new flush is DURABLE, and the old records are simply gone from the stick. The
rings still hold the last 114.7 s, so recent records are re-sent only if they
were queued. Boot records from long before are lost. An early death (9.6: before
36 s) would lose its onset window. **S2 and S4 fail.**

**Why AMBIGUOUS and not BLIND.** The design states invariants that forbid this:
- "A file holds ... tick flushes from 1,536 to `seg_end` (each region handed to
  `write()` once ...)" (DESIGN:1175-1176);
- "A failed flush is never overwritten" (DESIGN:1237);
- the Stage 3 pass condition "no sector of a region handed to `write()` written
  twice" (DESIGN:1843, 8.5 Errors);
- the designer's model, which never switches to a file already used
  (`usable(f)` requires `not f.used`, `design/r5-scripts/sim_r5.py`; when the
  active file is the one being created it holds and resumes at `seg_end`).

So the intended behaviour is "hold, then resume in A at its own `seg_end`", and
G2's conformance check would have the invariants to point at. But the operative
rule in 4.4 is the one Stage 2 will code, and as written it destroys data.

**Fix needed:**
1. In 4.4 "Use and switch", state:
   - a file that has been active is never a switch target again;
   - when the active file is still being created and the next flush does not fit,
     the worker holds (64 KB steps) and resumes flushing **in the same file at its
     current `seg_end`** as soon as `seg_end + 40,960 ≤ conf`;
   - `seg_end = 1,536` only for a file that was never active.
2. Add an 8.5 "Errors" vector: an active file in creation, catch-up flushes of
   40,960 bytes, two failed steps (or a 3 s burst) → hold, then resume at
   `seg_end`. Pass condition: no region written twice, and boot records intact.
3. Optionally, make the start-up step rule depend on the catch-up flush size
   (64 KB while room < 2 × the current flush size plus 40,960), so a single failed
   step cannot exhaust the room.

### OE9. A META run now counts, but a refusing FSINFO costs ≥ 10 driver retries with preemption off at every `fsync` for the rest of the run (observer-effect; A1 class at full scope). DIAGNOSABLE

**Shape.** IF7a at full scope. r5 keeps recording (good) and counts the run
(RUNBOOK:15-18, :316-322; J15, DESIGN:2171). But it still calls `fsync` at about
4.35 per second plus every creation step, and every `fsync` writes FSINFO (V2,
V5).

**Trace (V15).**
1. Each failed FSINFO write is 10 tries × (try + 1 ms), with preemption off.
   A try that fails early costs about 1-2 ms; one that fails after the data
   transfer costs about one sector-write time (≈ 10 ms at 50 KB/s; UNVERIFIED).
2. That is **≈ 20-110 ms of non-preemptible time per `fsync`.**
3. The worker's tick lengthens by the same amount, which lowers the `fsync` rate.
   That leaves **≈ 10-30 % of all CPU time non-preemptible**, in 20-110 ms
   blocks, for the rest of the run.
4. **During those blocks:**
   - the joypad thread cannot start a poll, because its wake-up is delayed;
   - a thread command already preempted mid-transaction stays suspended with G3
     high for the whole block (N1 exposure);
   - every try does an LED read-modify-write pair, 20 per failing sector (H10
     exposure).
5. The Nop is not shifted: interrupts stay on.
6. The 9.6 sessions had none of this.

**What is recorded.**
- The S records carry each failing FSINFO write with its duration
  (`c_on`..`c_off`, `dtick`), b1, b7 and the worker's pid.
- `wk_delay`/`wk_wrk` and `pre_tot`/`pre_wrk` charge the delays to class WRK.
- POLL `period` shows the slowed polls.
- An onset during such a block is classified N1/N1m/H10 with the collector named
  as the holder.

So S5 ("know precisely how it might have") is met from the records.

**What is not done.** The decoder's onset annotation lists collector activity
"creation, catch-up, re-send, switch, takeover, panel paint, guard violation"
(DESIGN:1996-1998), not failing metadata writes. `flush meta err` EVENTs are
rate-limited to one per 10 s (DESIGN:1242). An automatic report could call such
a run "healthy conditions" when the instrumentation was taking a large part of
the CPU non-preemptibly.

**Ruling: DIAGNOSABLE** (an analyst has every record needed).

**Recommendations** (not required, but cheap and good):
1. **Data-only sync for tick flushes.** A flush never changes the file's size,
   chain or FSINFO (DESIGN:1149-1161), and its verdict comes from its DATA S
   records anyway (4.8). `sync_file_range(fd, off, len, WAIT_BEFORE | WRITE |
   WAIT_AFTER)` exists in this kernel (V19; seven o32 slots, so through `syscall()`
   like `fadvise64_64`). It would:
   - remove the directory and FSINFO writes from every flush: per-tick sector
     writes fall from 5.2 to 3.2, and LED operations by about 38 % (H10 exposure,
     7.5);
   - take IF7a's and most of IF7b's retry load out of the flush path entirely.

   Creation steps keep `fsync`. The directory entry still gets the right size from
   the step that confirmed it.
2. Add "failing metadata writes" to 10.5's collector-activity list, with the
   non-preemptible time per second computed from S records. Flag onsets during it
   as `instrumentation-exposure`.
3. State the figure in 7.1 and 7.5 for the persistent case.

**in_scope_under_A1:** no (the cause is the A1 class). It is in scope now.

### OE10. Console log level 4 could remove a perturbation the 9.6 sessions had (observer-effect). DIAGNOSABLE

**Shape.** Can the instrumentation **prevent** the failure? r5 sets the console
level to 4 at boot (V18). In the 9.6 sessions any level-4 message would have been
drawn on the framebuffer console with interrupts off (`kernel/printk.c:819-828`,
attempt-5 OE8). If such drawing were the trigger, r5 would suppress it.

**Evidence.**
- The recovered `kmsg.txt` from those sessions is 1,606 bytes and did not grow
  after boot (dossier 9.4 Q9: "the log really was silent"). So nothing was being
  drawn during those runs, and suppressing level-4 drawing removes nothing the
  baseline had.
- In r5 every message, suppressed or not, reaches the log and the KMSG chunks
  (DESIGN:1621). So any message printed during this run would be visible to the
  analyst, and the change would be noticed.

**Ruling: DIAGNOSABLE.**

### UL8. The syscon's own watchdog trips because a Nop arrives late in wall time (unlisted shape). DIAGNOSABLE (recommendation)

**Shape.** Dossier 9.6 ties the deaths to the 5 s boundary. H4 and WB assume a
problem inside or right after one Nop. Another reading: the syscon expects the
Nop every 5 s of **wall time**, and treats a late one as a host fault, for
example by stopping key scanning while still answering commands. This tree counts
1,250 **ticks**, not seconds:
- a handler that runs longer than a tick loses ticks (recon/syscon §6 caveat 3);
- so the next Nop arrives late in wall time by the lost time.

In this tree the only interrupts-off stretches longer than 4 ms are a slow Nop
itself (a −4 Nop is ≥ 50 ms, recon §1.5) and, on the 2008 image, an unbounded
one.

**What is recorded.**
- Every WT record has its own duration (`c_out` since the Count reset, which can
  exceed CPT), its result, and `c_pre` (the length of the tick that ended at that
  Nop).
- `long_ticks`, `c_pre_max` and the 64-bit `total_counts` are in every STATS
  chunk (every ≈ 1.8 s).
- The WB and two-stage rows list every WT within ± 2 cycles with its own result
  (10.7 step 5).
- So the wall-time spacing of consecutive Nops can be reconstructed: exactly when
  no long tick fell between two STATS samples, and bounded by `c_pre_max`
  otherwise.

**Ruling: DIAGNOSABLE** (an analyst can compute it).

**Recommendation.** Print, per onset candidate, the wall-time spacing of the
surrounding WT records (from `total_counts` samples, W `c_pre` and the Nops'
own durations), and flag any spacing above 5.0 s + 1 tick.

### UL9. The thread sleeps forever in `msleep` (unlisted shape). DIAGNOSABLE (recommendation)

**Shape.** The thread reaches `msleep(50)` (stage 17) and its timer never fires,
for example a lost or corrupted on-stack timer. It stays in
`TASK_UNINTERRUPTIBLE` (recon/input §2.3: `msleep` uses
`schedule_timeout_uninterruptible`). telem's `nanosleep` kept running in the 9.6
sessions, so the timer wheel as a whole worked, but a single lost timer is not
excluded.

**What is recorded.**
- P and POLL stop.
- W records continue with `t_busy` 0, `ext_flags` b4 = 0, `jp_loop` fixed and
  `jp_stage` 17.
- Stats: `jp_state` = 2 (uninterruptible), `jp_stage` 17, `wk_count` flat (no
  wake-up), `t_busy` 0.
- PROCS shows the thread in state D.

**Decoder.** None of the thread-stopped rows matches:
- H9 needs stage 11/9 and state 1;
- N4 needs stage 7/8;
- N5 needs stage 15/16 and state 0;
- N9 needs `t_busy` set.

So it prints **H0 / unclassified** with the raw windows and the stats series, as
S1 allows ("state that none did and show the raw evidence").

**Ruling: DIAGNOSABLE.**

**Recommendation.** Add a row N12, "thread asleep at stage 17, never woken", with
that signature, so it is named rather than unclassified.

---

## 4. SPOILED-DETECTED rulings (Amendment A1)

**None.** A1 is suspended for this round, so SPOILED-DETECTED is not available,
and every scenario was ruled DIAGNOSABLE, AMBIGUOUS or BLIND.

For the record, the three A1-class scenarios, their full-scope rulings, and
(information only, in case the human ever reinstates A1) whether revision 5
would still meet A1's three conditions:

| Scenario | Full-scope ruling | A1 (1): detected from own records ≤ 30 s | A1 (2): shown on the kernel panel **and** the HUD | A1 (3): runbook says what to do | Data already on the stick never destroyed |
|---|---|---|---|---|---|
| IF7a FSINFO | DIAGNOSABLE | Yes: about 1-2 s (4.7, every `fsync` writes FSINFO, V5) | **No longer as written**: META now shows on HUD line 6 and in the panel's line 6 field **only when the panel is up for another reason**; META does not paint the panel (DESIGN:636, :1346) | Yes: RUNBOOK C4 item 3, E2 | Yes: F1(a) keeps every written region; nothing is re-sent over it |
| IF7b `PSCLOG` directory sector | AMBIGUOUS (section 2) | Yes: about 1-2 s | As IF7a | Yes | Yes. Aliases are never written (4.4 step 1, V7-V8); I checked that the alias inode is clean (V3) and that closing it writes nothing (V8) |
| IF8 allocator FAT sector | DIAGNOSABLE | Yes: about 5 ticks | As IF7a | Yes | Yes. Flushes never allocate (V9); the allocator never returns (V13) |

So, if A1 were applied again to revision 5, condition 2 would fail as written.
That is a deliberate r5 change (A5-2: META must not fail D8), and it does not
matter at full scope.

---

## 5. Designer acceptances and contests: do I agree?

| Item | My position |
|---|---|
| N1m "cannot be separated in one run" | **Agree.** The records are identical. |
| IF5 residual contested (`mm/filemap.c:2161-2162`; `fs/fat/cache.c:241-251`) | **Agree.** Verified (V10, V12): a flush never truncates and never reads the unconfirmed link. |
| "Do not promote a stopped file" rule not adopted | **Agree**, for the same reason. |
| P and POLL rings 4× larger not adopted | **Agree.** A whole-stick refusal beyond about 100 s is the accepted Case 2, and nothing in my scenarios needs more span. |
| 30 KB/s gate instead of 35 | **Agree.** The model reproduces (Appendix A). |
| J15 META informational, the run counts | **Agree that recording continues. Partly disagree that nothing more is needed:** the persistent FSINFO case carries a large, unstated, recorded perturbation (OE9). It needs a decoder flag; the data-only sync would remove most of it. |
| 15.8 weakest point (S hook truth, vfat order) | **Agree.** I add one item the design should list: the step-0 own-entry identification (IF7b) also rests on the vfat write order V1-V5. |
| 4.4 step 4 "the retry allocates nothing" | **Disagree** (IF11): it is false after a short `write()` (V10, V11), and by the verdict rule as written an allocating retry can never be confirmed. |

---

## 6. Fixes required (consolidated)

| # | Fix | Closes | Kind |
|---|---|---|---|
| **H1** | **Step-0 own-entry identification.** In 4.8 and 4.4 step 4, define step 0's own directory write as the first DIR-class S record with the worker's pid after the step's last DATA record in its window (order from `fs/sync.c:78-106`, `:55-76`; `fs/fs-writeback.c:166-174`; `fs/fat/inode.c:556-611`). It must exist and be error-free. Other DIR failures in the window are META evidence only; a `pdflush` DIR record is ignored. Add two 8.5 verdict vectors and the tighter VFAT-FI IF7b pass condition. | IF7b (AMBIGUOUS) | specification, required |
| **H2** | **No switch to an active file.** In 4.4 "Use and switch": a file that has been active is never a switch target again. When the active file is still being created and the next flush does not fit, hold (64 KB steps) and resume in the same file at its own `seg_end`. `seg_end = 1,536` only for a never-active file. Add an 8.5 Errors vector (an active file in creation, catch-up, two failed steps or a 3 s burst; pass: no region written twice, boot records intact). | TE10 (AMBIGUOUS) | specification, required |
| H3 | **Allocating retries.** Judge "allocated" per try (a FAT1 success is needed only if this try wrote FAT1, or if `mmu_private` was below the step's end before the try). Correct "the retry allocates nothing" for a short `write()` (V10, V11). Add an 8.5 vector; update the model. | IF11 | correction, required for consistency, not blocking |
| H4 | Data-only `sync_file_range` (4305, via `syscall()`) for tick flushes; a decoder flag and a 7.1/7.5 figure for failing metadata writes. | OE9 | recommendation |
| H5 | Tighten the bad-region escape trigger, and give escape-caused fast attempts their own small budget. | IF12 | recommendation |
| H6 | UHB `seg` `conf` in 512-byte units; R11 note on "size before link"; decoder rows N12 and wall-time Nop spacing; `syslog(8)` named as the kernel call; citation `ms_psp.c:234` → `:250`. | TE7, TE9, UL8, UL9, OE8 notes | small corrections |

H1 and H2 together are perhaps 20 lines of text and four Stage 3 vectors. No
new mechanism, record field or kernel change is needed.

---

## 7. Attacks attempted that found nothing (or only notes)

| Attack | Result |
|---|---|
| A flush verdict DURABLE while some of its data never reached the stick | Not possible in this tree. A bio aborted at its first failing segment leaves the later segments **without** S records (V14), so the coverage test fails. A missing S record (the semaphore failed with a signal pending) fails it too. Data pages are written after `write()` and before the window ends (V1); `pdflush` records count, since pid is not required for DATA. |
| `pdflush` writes the flush's pages outside the window | It cannot write them before `write()`, and anything after that is inside the window, which starts at the tick's snapshot. |
| `FIBMAP` walking into an unconfirmed link and panicking | It runs only after the FAT1 check passes, with `create = 0` (V16), and the walk reads only entries before the target (V12). The new link is in an up-to-date buffer after a successful FAT1 write. |
| The alias inode written back later (size 1,536, start c into the alias's slot) | Not possible. Its failed `fsync` cleared `I_DIRTY` without re-dirtying it (V3), `vfat_create` does not dirty it (V7), and `release` writes nothing (V8). |
| An alias test false positive from inode-number reuse | `iunique` uses an increasing counter, so no reuse within a run. A false positive would cost only a name. |
| Takeover and the alias test | Old-instance inodes have `st_size ≠ 0` (rejected) or `i_start = 0` (safe), as the design says. |
| The S-window `pread` disturbing the drain or REC | `pread` passes its own position (V17) and calls no `llseek`. |
| The 64 KB start-up rule and the speed gate | First complete drain ≤ 35 s at 30 KB/s (model reproduced). |
| A whole-stick burst raising META or the escape | Neither fires: META needs successful data writes in each tick, and the escape needs another successful write in the window. (A **flaky** stick can fire the escape: IF12.) |
| IF8 cluster reuse | `prev_free` only advances (V13); the FREE entries in F are not reused within the run. |
| The names budget and long file names | `readdir` returns one name per file, while a Mac-made long name uses several slots, so the budget could be overstated if `PSCLOG` held Mac files. A0/E1 mount read-only and A4 uses `mkdir`, so none should exist. Note: count slots from name lengths, not files. |
| `FIBMAP` count "≤ 3 per step" | Holds at 32 KB clusters. At 16 KB a 64 KB step adds 4-5 clusters, so the count is slightly higher. Harmless. |

---

## 8. UNVERIFIED items this report depends on

1. How long a **failed** `pspMsWriteSector` try takes (early `INT_REG_ERR` or
   after the transfer). It sets OE9's 10-30 % figure (V15).
2. The cluster size of the operator's stick (16 or 32 KB). It affects IF8's
   attempt count, IF11's frequency and the names budget.
3. macOS behaviour when copying a file whose size exceeds its chain (TE9).
4. Whether the syscon has a wall-time watchdog tolerance (UL8).
5. Whether Memory Stick write errors occur at all in this setup, and in which
   pattern (IF7a/b, IF8, IF11, IF12, TE10). The same uncertainty underlies A1.
6. That VFAT-FI (R18) can be built. If it cannot, H1 and H2 reach the hardware
   tested only by the host vectors of 8.5, which is why the vectors in H1 and H2
   are required.

---

## Appendix A. Re-running the designer's model

Copied `design/r5-scripts/sim_r5.py` to my scratchpad. The model is unchanged
except for one optional rule, `ALLOC_RETRY_BUG`: when set, a step that allocates
by the 4.4 formula and is a retry (`f.retries > 0`) is never confirmed. That is
the design text as written (IF11).

Settings: 60 runs of 30 min per point, collector start 40 s, `step_rule='rev'`
(r5's 64 KB-while-room-below-81,920 rule), 98 failure events per 30 min.

| Rule | Failure model | 25 KB/s | 30 KB/s | 40 KB/s | 52 KB/s | 100 KB/s |
|---|---|---|---|---|---|---|
| as modelled by the designer | per operation | 0.0 s (0/60), 9.0 files | 0.0 s, 8.8 | 0.0 s, 9.6 | 0.0 s, 9.4 | 0.0 s, 9.2 |
| as modelled by the designer | whole tick | 0.3 s (1/60), 27.9 | 0.0 s, 27.6 | 0.0 s, 25.4 | 0.0 s, 23.5 | 0.0 s, 19.4 |
| as written (IF11) | per operation | 0.0 s (0/60), 17.1 | 0.0 s, 15.9 | 0.0 s, 14.7 | 0.0 s, 13.0 | 0.0 s, 11.1 |
| as written (IF11) | whole tick | 2.1 s (4/60), 33.6 | 0.0 s, 29.0 | 0.0 s, 26.5 | 0.0 s, 24.0 | 0.0 s, 19.5 |

Reading:
- At and above the 30 KB/s gate nothing is lost either way.
- The IF11 contradiction costs files and names, not records.

The model does not represent TE10 (it never switches to a used file), the IF7b
identification, or the longer duration of failed I/O (V15).
