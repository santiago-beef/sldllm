# Gate G1, attempt 7: design review

| | |
|---|---|
| Gate | G1 (design review checklist D1-D20), round 7. **Scope: FULL.** Amendment A1 is on record but does not apply to this verdict (gates/LOG.md note of 2026-10-05; WORKFLOW.md Amendments). SPOILED-DETECTED is not available. |
| Brief | Closure only: the designer could change only the text needed to close A6-1..A6-4 (gates/G1-attempt6-review.md) and red-team IF7b and TE10 (gates/G1-attempt6-redteam.md), with no new mechanism. |
| Artifact | `design/DESIGN.md` revision 6 (**2,669 lines** by `wc -l`; 2,254 through section 12, section 13 starts at line 2255), `design/RUNBOOK.md` (485 lines). Diff against the frozen revision 5: `design/round7.diff`. Response: DESIGN section 16. |
| Reviewer | G1 design reviewer, attempt 7. Fresh context. I did not write the design. |
| Inputs read | DOSSIER.md in full (section 9 taken as superseding), WORKFLOW.md in full (Amendments included), gates/LOG.md, G1-attempt6-review.md in full, G1-attempt6-redteam.md (verdict, summary, section 1.1, IF2, IF7b, IF8, IF9, TE10, OE9 and the fix table read; the rest scanned), round7.diff in full, DESIGN.md sections 0-4 (all of 4.1-4.8), 1.0-1.8, 2.1-2.9, 3.1-3.4, 5.3, 7.7, 8.2, 8.5, 10.2, 15.3, 16 and every changed hunk in context, RUNBOOK B2-B6, D8, timing summary. Recon: syscon.md sections 0, 1.3-1.5, 4.3, 5 read; input.md, build.md and image2008.md by heading only. **For items whose text the diff did not touch I rely on the attempt-6 review, as allowed, and say so per item; five or more of those were spot-checked against the source myself (section 4).** |
| Source used | `/home/ubuntu/psp/build/linux`, read only. Also `/home/ubuntu/psp/telem/telem.c`, `telem/cbuild.sh`, `/home/ubuntu/psp/staging_dir/usr/include/sys/klog.h`, `/home/ubuntu/psp/extract/root2/etc/rc.sysinit`. The designer's scripts in `design/r5-scripts/` were run unmodified from their directory (they write nothing). After the work: `sha256sum -c --quiet ../../handoff/gates/baseline-tree.sha256` in `build/linux` exit 0, `git -C work/linux status --porcelain` empty. I wrote only this file. |
| **Verdict** | **PASS.** 0 blocking FAILs, 0 non-blocking FAILs. A6-1 (blocking at attempt 6), A6-2, A6-3 and A6-4 are **closed**. The diff is confined to the brief. Three new advisories (A7-1 to A7-3) do not fail any item. |

---

## Plain-language summary

**What round 7 had to fix.** Last round's one blocking problem (A6-1) was this. When the collector makes a
new file, its very first save ("step 0") must write the file's own entry in the folder listing. The
collector checks this from the Memory Stick's own per-sector answers (the S records). But in one fault
case, a folder sector that refuses all writes (IF7b), the same save also tries and fails to write
*another* folder sector. The design never said how to tell the two apart. Read the wrong way, no new file
could ever be created again, and recording would stop about 9 minutes later.

**What the designer did.** The design now says exactly which record is the file's own entry: the first
folder-sector write by the collector after the file's data writes. I checked the kernel code in this
tree myself. It holds. The data is written first. Then the file's own folder sector is written at once,
alone, and the call waits for it. Only after that does the kernel write any other dirty folder sector,
including the refusing one. The Memory Stick driver does each write to completion in the caller's own
process, so the records come out in exactly that order.

When something unusual happens (a background kernel thread writes a folder sector in between, or the file
was already saved by memory pressure), the rule either throws the new file away or relies on a check that
already exists elsewhere. Throwing a file away costs only one file name. That check never writes through
a stale file. So the rule can waste a name but cannot lose records.

The other five items were small text fixes. All are done correctly, and the diff touches nothing else.

**What I would still tidy (advisory only).** (1) One line in 4.4 step 6 still says "IF7b ≤ 152" in a
place where the right figure is now 16 attempts (153 names). (2) The new IF7b accounting assumes the
kernel keeps the rejected files' records in memory. Under memory pressure late in a long run, that is not
guaranteed. The design marks this UNVERIFIED and has a margin, but it does not say what happens if the
margin runs out. (3) A naming nit of the same kind A6-2 fixed.

---

## 1. Diff audit (task item 1)

I regenerated the diff (`diff -u DESIGN.r5.md DESIGN.md`, `diff -u RUNBOOK.r5.md RUNBOOK.md`); apart from
the `---`/`+++` header lines it is identical to `design/round7.diff`. 23 DESIGN hunks and 1 RUNBOOK hunk:

| # | Location (r6) | What changed | Serves |
|---|---|---|---|
| 1 | header, line 20-22 | note "Round 7 (closure only) … listed in section 16" | documentation of the round |
| 2 | Summary item 7 | "from 28 KB/s up the model loses nothing …, at 25 KB/s 1 run in 260 loses 15 s" | A6-3(e) |
| 3 | 0.2 U6 | adds "after vfat read-only, no creation step …" (a row for an existing r5 rule) | A6-3(d) |
| 4 | 0.2 U21, U24 | own-entry wording; `syscall(__NR_syslog, 8, 0, 4)` at worker start, EVENT `conlevel` | A6-1, A6-2 |
| 5 | 2.4 | partition hook placed after the loop ending at `ms_psp.c:199`, before `:201`; `:234` → `:250` | A6-3(c) |
| 6 | 2.8 | ring `read()` sets `*ppos`, never `file->f_pos` | A6-4 |
| 7-8 | 4.2 | console-level call removed from the supervisor, added at worker start with its return in EVENT `conlevel` | A6-2 |
| 9 | 4.3 Bounds | "UHB 104 … 37,696" | A6-3(b) |
| 10 | 4.4 step 4 | own-entry rule with the source order; `pdflush` case; other DIR failures are META only | A6-1 / IF7b |
| 11 | 4.4 step 4, step 0 bullet | "if it is not CONFIRMED the file is abandoned" | A6-1(2) |
| 12 | 4.4 Use and switch | never-active targets only; active file in creation holds and resumes at its own `seg_end` | TE10 |
| 13 | 4.8 Sector classes | `ms_psp.c:250` | A6-3(c) |
| 14 | 4.8 Step verdict, Speed | pointer to 4.4 step 4; 28 KB/s statement | A6-1, A6-3(e) |
| 15 | 7.1 `printk` row | worker sets level with the kernel call; EVENT `conlevel` | A6-2 |
| 16 | 8.5 | VFAT-FI: "within 10 s plus one tick of recovery"; IF7b pass condition (≤ 153 names to the first fresh file within 20 ticks, ≤ 17 per later creation); reader row interleaving `pread` with drains; Errors vector for TE10; three step-0 verdict vectors | A6-3(f), A6-1(3)(4), A6-4, TE10 |
| 17 | 10.2 | UHB `seg` decoder mapping (conf = SEG for v = 256, else 8,192·v + 1,536); EVENT list gains `conlevel` | A6-3(a), A6-2 |
| 18 | 11.1 R8 | 25 KB/s statement | A6-3(e) |
| 19 | 11.1 R25 | `ms_psp.c:250` | A6-3(c) |
| 20 | 15.3 IF7b | own-entry trace; 153 names; later creations ≤ 17; 306 per 35 min; eviction UNVERIFIED | A6-1(4) / IF7b |
| 21 | 15.4 OE8 row | the corrected call | A6-2 |
| 22 | 15.6 IF4 | 1 run in 260 at 25 KB/s | A6-3(e) |
| 23 | section 16 (new) | response table | the round's response |
| R1 | RUNBOOK B5 | "write down … the run number `rrr`" | A6-3(g) |

**Every hunk serves one of the six items or documents the round.** Two hunks warrant a check that they
add no mechanism:

- **A6-2 moves the console-level call from the supervisor to the worker.** A6-2 asked for the supervisor
  to log the return in an EVENT. The supervisor writes neither the stick nor `ctl` (DESIGN 4.2), so it
  cannot. The call is the same single system call, made once per worker instance. The level is global
  (`kernel/printk.c:298`), so instance 2 repeating it is harmless. **This is a relocation that A6-2
  required, not a new mechanism.**
- **A6-1's `pdflush` rule is stricter than the red team's text.** The red team wrote "a `pdflush` DIR
  record is ignored". The design writes "a DIR record of another pid between the last DATA record and the
  worker's first DIR record makes step 0 not CONFIRMED". This is specification inside A6-1. It is more
  conservative (section 2.3).

`diff_confined_to_brief`: **true**. No D item takes a FAIL from the diff audit.

---

## 2. A6-1: the own-entry ordering, verified in `/home/ubuntu/psp/build/linux` (task item 2)

### 2.1 The rule as written (DESIGN 4.4 step 4, r7)

The own-entry write is defined as follows.

- It is the first DIR-class write record (b0 set) carrying the worker's pid after the last DATA record of
  the step's own data sectors in the window.
- It must exist and have b1 clear.
- A DIR record of another pid between that last DATA record and the worker's first DIR record makes
  step 0 not CONFIRMED.
- Any other failed DIR write in the window is META evidence only.

### 2.2 The order of writes in a step-0 `fsync`, traced in this tree

| # | What happens | Evidence (this tree) |
|---|---|---|
| 1 | `do_fsync` first calls `filemap_fdatawrite(mapping)`: the file's dirty data pages. | `fs/sync.c:90` |
| 2 | The Memory Stick driver is a `make_request` driver with no request queue or elevator. `psp_ms_make_request` transfers each bio synchronously in the submitter's context and then calls `bio_endio`. Each S record is therefore written in submission order, with `current` = the submitter. | `drivers/block/ms_psp.c:190-191` (`blk_queue_make_request`), `:228-236`, `:238-276` |
| 3 | Then `file->f_op->fsync`, which is `file_fsync` for vfat. | `fs/sync.c:97`; `fs/fat/file.c:136` |
| 4 | `file_fsync` first calls `write_inode_now(inode, 0)`. It always uses `WB_SYNC_ALL`. | `fs/sync.c:62`; `fs/fs-writeback.c:568-576` (`:573`) |
| 5 | `__sync_single_inode` runs `wait = (sync_mode == WB_SYNC_ALL)` = 1, clears `I_DIRTY`, then `do_writepages` (data, already clean after step 1), then `write_inode(inode, 1)` if `I_DIRTY_SYNC`/`I_DIRTY_DATASYNC` was set. | `fs/fs-writeback.c:158`, `:164-166`, `:170`, `:173-174` |
| 6 | `fat_write_inode(inode, 1)` reads the entry's block with `sb_bread` (a READ record, b0 clear, if not up to date), edits the entry, `mark_buffer_dirty`, and then `sync_dirty_buffer(bh)`. | `fs/fat/inode.c:571`, `:586-602`, `:604-606` |
| 7 | `sync_dirty_buffer` locks the buffer and, if it is still dirty, submits exactly that one buffer and waits. This is the **own-entry write**: one record, synchronous, before anything below. | `fs/buffer.c:2703-2719` (`:2708-2713`) |
| 8 | Only then `write_super` → `fat_write_super` → `fat_clusters_flush`. This reads FSINFO and only marks it dirty; it writes nothing. | `fs/sync.c:66-69`; `fs/fat/inode.c:453-459`; `fs/fat/misc.c:40-72` (`:69`) |
| 9 | Then `sync_blockdev` → `filemap_write_and_wait` on the block-device mapping: FSINFO, FAT1, the FAT mirror and **every other dirty directory buffer**, including a refusing sector X whose buffer was dirtied by alias entries. | `fs/sync.c:72`; `fs/buffer.c:152-159` |

**Why X's buffer is dirty in the IF7b tick, and why it is written only in step 9.**
- X was left clean and not up to date by its last failed write (`fs/buffer.c:128-146`).
- The next `fat_add_entries` scan re-reads X through `sb_bread` (`fs/fat/dir.c:87`; `fs/buffer.c:1382-1383`).
- Each alias's entry is copied into X's buffer and marked dirty, with no synchronous write, because DIRSYNC
  is off (`fs/fat/dir.c:1265-1269`; `/ms0` mounted without options, `rc.sysinit:10`).
- Nothing in steps 1-7 writes a block-device buffer other than the inode's own entry block. Step 1 is the
  file mapping only. Step 5's `do_writepages` is the file mapping only. Step 6 writes one `bh`.

**Answer to the task's question.** In the tick where a fresh file lands in X+1 under a refusing X, the
own entry (X+1) is the first worker DIR-class write after the step's data writes. It is reliable,
because it is written synchronously by `sync_dirty_buffer` at step 7, before `sync_blockdev` at step 9
ever touches X. That holds whatever the page order of X and X+1, and even when X+1 lies in another
directory cluster at a lower sector than X. The S record's `pid` is the worker's: the I/O runs in the
worker's own context (row 2). The `.config:136` citation (`CONFIG_PREEMPT_BKL=y`) is correct, so
`lock_kernel()` at `fs/fat/inode.c:570` does not stop `pdflush` from writing block-device pages while
the worker sits between `:604` and `:606`.

### 2.3 Cases that do not follow the main path, and what the rule does with them

| Case | What happens | Effect of the rule | Can it lose records? |
|---|---|---|---|
| `pdflush` writes the entry buffer between `:604` and `:606` | `sync_dirty_buffer` finds it clean and writes nothing (`fs/buffer.c:2709`, else branch). A `pdflush` DIR record lies between the last DATA record and the worker's first DIR. | Not CONFIRMED: abandoned, one name (≤ 17 in IF7b). The red team's text ("ignored") would have taken the next worker DIR record, which could be X (failed, a wrong abandon) or another sector (OK, a wrong CONFIRM). The design's stricter rule is better. | No |
| `pdflush` writes X+1 (or X) before the step's DATA records, or after the worker's own-entry record | Not between them. | Ignored, as the rule says. | No |
| The fresh inode is already clean when `fsync` runs. This needs background writeback (`background_writeout`, `mm/page-writeback.c:364-371`, `older_than_this = NULL`), which here only direct reclaim triggers (`mm/vmscan.c:1066-1068`), and only in the few milliseconds between `write()` and `fsync()`. `kupdate` cannot do it: the inode was first dirtied by this `write()`, since `vfat_create` does not dirty it (`fs/vfat/namei.c:756-758`). Dirty-threshold writeback cannot either: `dirty_background_ratio = 5` and `vm_dirty_ratio = 10` (`mm/page-writeback.c:70`, `:75`), against ≤ ≈ 100 KB dirty. | `write_inode` is skipped (`fs/fs-writeback.c:173`). The first worker DIR write then comes from `sync_blockdev`'s page-order walk. | In IF7b with X before X+1: X fails, so the file is abandoned (conservative, 17 names). If another DIR sector comes first and succeeds while the own entry later fails, step 0 is wrongly CONFIRMED. The file's entry slot is then free on the stick, so the next scan returns this file's own cached inode at that slot. That inode has `st_size ≠ 0` and an `st_ino` already seen, so 4.4 step 1 rejects it as an alias before any write. Its records are in data sectors with confirmed FAT1 links, recovered from the raw image, which META makes mandatory. | No |
| The worker's own data is written by a writeback in its own context during `write()` (`balance_dirty_pages`) | Needs dirty > 5 % of memory. It cannot occur at ≤ ≈ 100 KB dirty (thresholds above). | n/a | n/a |
| Takeover: the old worker's last `fsync` overlaps the new instance's step 0 | Its DIR records carry another pid. | Covered by "of another pid": not CONFIRMED, one name. | No |

**A6-1 is CLOSED.** All four parts of the closing text in G1-attempt6-review.md section 3.5 are done:

- **(1) The own-entry write is defined from the source order.** I re-verified that order above, line by
  line.
- **(2) The step-0 bullet now reads "if it is not CONFIRMED the file is abandoned".** FSINFO, mirror and
  other-sector DIR failures are tolerated at step 0, as at later steps.
- **(3) 8.5 has the step-0 vectors.** It has "own OK + other DIR failed → CONFIRMED" and "own failed +
  other OK → abandoned". It also has a third: "no worker DIR record after DATA, or `pdflush` before it →
  abandoned". I matched all 10 inputs to the 10 listed verdicts one to one.
- **(4) The IF7b account in 15.3 is corrected.**
  - Phase 1: tick k has k − 1 aliases plus one abandon. Σ k for k ≤ 16 is 136, plus 17 in the confirming
    tick, giving **153** names. I recomputed it.
  - Later creations cost ≤ 17 each, so a 35-minute run costs ≤ 306 names against the ≥ 400 budget.
  - The VFAT-FI pass condition now has the number bound and the time bound ("CONFIRMED within 20 ticks …
    no hold over 114.7 s", which was already there).

  The designer times VFAT-FI from the first creation attempt after onset, not from META onset. The reason
  given is correct: META on the active file's own entry can come minutes before a creation is due.

---

## 3. Prior findings

| # | Closed? | Evidence |
|---|---|---|
| **A6-1** (blocking, D6) | **CLOSED** | Section 2. |
| **A6-2** | **CLOSED** | 4.2 now specifies `syscall(__NR_syslog, 8, 0, 4)` at worker start (the form of `telem.c:281`, which I read: `return (int)syscall(__NR_syslog, 3, b, len);`; or `klogctl(8, NULL, 4)`, `staging_dir/usr/include/sys/klog.h:30`, read), "not the C library's `syslog()`". Its return and `errno` go in EVENT `conlevel <ret> <errno>`. `do_syslog` case 8 returns 0 and sets `console_loglevel = 4` (`kernel/printk.c:292-300`, read), so level-4 lines (the driver's `DBG`, and "lost page write", which is `KERN_WARNING`, `fs/buffer.c:137`) are not drawn, while `KERN_ERR` still is. The same text appears at U24, 7.1, 15.4 and in the 10.2 EVENT list. The move to the worker is explained in section 1. One residual naming nit at 4.3 step 3 (A7-3). |
| **A6-3** (a)-(g) | **CLOSED** | **(a)** 10.2: v = ⌊conf / 8,192⌋ is stored. The decoder takes SEG for v = 256, else 8,192·v + 1,536. This is exact: step 0 is 1,536 B and later steps are 8 KB or 64 KB (multiples of 8,192), except the last, which ends at SEG (4.4 steps 2-3). So conf ∈ {1,536 + 8,192·j, j ≤ 255} ∪ {SEG}, and ⌊(1,536 + 8,192 j)/8,192⌋ = j. A stopped file keeps its last conf, and a read-back stop sets conf = SEG − k, the previous conf, so both are of that form. v = 0 before step 0 reads as 1,536, and only the FILEHDR lies below that. Bits 20-28 (9 bits) hold 0-256. **(b)** 4.3: "UHB 104 … 37,696". **(c)** 2.4: the loop ends at `ms_psp.c:199` and `s_initialized = TRUE` is at `:201`; `sector = bio_->bi_sector + partition_->startSector` is at `:250`. All three read in the tree. 4.8 and R25 now say `:250`. **(d)** U6 has the read-only worker rule. **(e)** I re-ran `sim_r5.run(kb, collector_start=40, dur=1800, fail='tick', step_rule='rev', seed=s)` for s in 0-59: at 25 KB/s one run loses 15.2 s (seed 9, max hold 22.1 s); none at 28 or 30 KB/s. Together with the 200 runs of `run_if4b.py`, that is "1 in 260" as stated (summary 7, 4.8, R8, 15.6). **(f)** VFAT-FI: "within 10 s plus one tick of the stick's recovery". **(g)** RUNBOOK B5: "the three digits after `PSC T` on line 1 (the run number `rrr`)". This matches line 1's format `PSC T<rrr><nnn> SELFTEST PASS` (8.2). |
| **A6-4** | **CLOSED** | 2.8: the ring `read()` sets `*ppos`, never `file->f_pos`. `sys_read` copies its local `pos` back with `file_pos_write` (`fs/read_write.c:364-366`, read), while `sys_pread64` passes its own `pos` and writes nothing back (`:404-405`, read). 8.5 reader row: "`pread` windows interleaved with ordinary drains … the next `read()` continues from the previous drain's end with no record skipped or repeated". |
| IF7b (red team) | Text closed (design-reviewer view; the red team rules on its own scenario) | The same fix as A6-1. The red team's fix items 1-3 are adopted: the own-entry definition with the worker's pid, two (here three) 8.5 vectors, and the tighter VFAT-FI condition with ≤ 17 names per later creation. For `pdflush` the design takes a stricter variant (section 2.3). |
| TE10 (red team) | Text closed (design-reviewer view; the red team rules) | 4.4 Use and switch now says three things. A switch target must be a file "that has never been active". "`seg_end = 1,536` is set only for a file that was never active". And "When the active file is itself still in creation (and not retired) and the next flush does not fit, the worker does not switch: it holds … with 64 KB steps, and resumes … in the same file at its own `seg_end`". 8.5 Errors has the vector with two failed steps and with a 3 s burst. The pass condition is "never sets `seg_end = 1,536` in a file that has been active, no region is written twice and the boot records are intact". Fix item 3 (optional) is declined with a reason, which is acceptable for an optional item. I traced the edges myself (section 5). |

---

## 4. Checklist D1-D20 (task item 3)

"Untouched" means the diff changed no text that the item's evidence rests on. For those items I rely on
the attempt-6 review (G1-attempt6-review.md section 1 and the sections it cites), as allowed.
"Spot-checked" means I re-read the cited source myself this round.

| ID | B | Result | Touched by r7? | Evidence |
|---|---|---|---|---|
| D1 | B | **PASS** | no | Relying on attempt 6. Nothing is sampled or triggered: every `Syscon_cmd` call (P, W, M), every loop (POLL), every Memory Stick segment (S), whole-run stats (DESIGN 3.2, 3.3 re-read: "**None.** Nothing freezes or changes resolution"). |
| D2 | B | **PASS** | no | Derived independently from 1.2-1.7 and the source in section 6 below. Every row separates except the declared pairs. r7 changes no hypothesis-bearing field. |
| D3 | B | **PASS** | no | Relying on attempt 6, **spot-checked**: prefill `rx_buf[i]=0xff` (`syscon.c:92-93`); `ret` s16 at @20 covers −5..255 (`:113`, `:154`, `:231`, `:243`, `:254`, read); `nwords` taken after S20, where the reply loop ends just before `:219`; `rx[16]` @48; `cmd` @18, `retries` @23. The offsets are confirmed by the designer's `budget_r5.py`, which I re-ran (`SC offsets` printout). |
| D4 | B | **PASS** | indirectly (TE10) | No trigger. P/POLL rings 114.7 s, W 1,280 s, S ≥ 181 s (3.1 re-read; the script reproduces them). TE10's hold at start-up cannot occur in a fault-free run, because each tick's 64 KB step (room < 81,920) outgrows a ≤ 40,960-byte flush (section 5). Boot records are protected: a file that has been active is never restarted at 1,536 (4.4). |
| D5 | B | **PASS** | no | Relying on attempt 6. 3.3: no trigger; `DEAD?` is display only (8.4). |
| D6 | B | **PASS** | **yes** | A6-1 closed (section 2). TE10 closed (section 5). Case 1 is unchanged: worst-case loss 4 s, smaller than the 30 s hands-off wait (4.5; RUNBOOK D8 "Hands completely off for 30 s", re-read). IF7b no longer stops creation. Its residual name cost is bounded at ≤ 306 per 35 minutes against ≥ 400, with an UNVERIFIED eviction margin (A7-2, advisory: it needs reclaim, which by the design's own figures cannot begin before about minute 30, and the run ends by ≈ 35:00). |
| D7 | B | **PASS** | lightly (4.2) | **Spot-checked**: `pscol&` goes after `pspmd -s&` (`rc.sysinit:17-19`, read). The worker's start-up now also makes one system call. Nothing is typed. |
| D8 | B | **PASS** | no | Relying on attempt 6, **spot-checked**: `psp_pacify_watchdog` appears at `psp.c:97` (prototype), `:379` (timer), `:383` (definition) and `:557` (boot), as 1.8 states (grep). `ctx` origin bits, `wn`, `w_head_lo`, W `p_head`/`t_busy`/`epc`/`lc_*` are unchanged. |
| D9 | B | **PASS** | lightly (2.8) | Relying on attempt 6 for the ring writer protocol (3.4 re-read: invalidate `seq`, fill, publish `seq`, then `head`). The r7 `*ppos` text concerns only the userland reader's position. Its kernel side is per-call and takes no lock (2.8). |
| D10 | B | **PASS** | **yes** (7.1, 4.2) | Nothing is added in S5..S20 (2.1, unchanged). The 7.1 `printk` row now names the right call. Moving the call to the worker changes only the moment, a fraction of a second after boot start of `pscol`, before any collector stick I/O. The set level and its effect are as in r5. No new kernel work on any per-command or per-tick path. |
| D11 | B | **PASS** | no | Relying on attempt 6. No new MMIO in r6/r7. The only register reads are the loads the code already makes into `dmy` (2.1 A3) and the LED read-modify-writes the code already does (2.4). recon/syscon.md 4.3 (read) lists both as read by the running kernel. |
| D12 | B | **PASS** | **yes** (4.3 text) | I re-ran `budget_r5.py`: steady 5,887 B/s payload, 7,123 B/s on stick; run average 7,599 B/s; 15/30/35 min = 6.84/13.68/15.96 MB; rings 652,288 B; per cap 8,576; RECS max 34,364; flush max 37,696. 4.3 now says "UHB 104 … 37,696 → 37,888", consistent. No poll-rate `printk`. The 16 KB log is not used for history. The summary/4.8/R8/15.6 statement about 25 KB/s reproduces (A6-3(e)). |
| D13 | B | **PASS** | lightly (B5, 4.8 speed sentence) | Relying on attempt 6 for the eight checks and the 3:00 abort (8.2, 8.3). The B5 addition is a note-taking step, and line 1 shows `rrr` at that moment (8.2 line 1 format). The 30 KB/s gate is unchanged. |
| D14 | B | **PASS** | no | **Spot-checked**: −3 `syscon.c:113`, −4 `:154`, −2 `:231` and `:243`, −5 `:254` (read). Each is recorded in `ret` s16. Outcome counters are kept per command and context (stats 31-51). `drain` 0xFFFF and `ack_polls` 1,000,001 are sentinels (`SYSCON_SPIN_MAX` 1,000,000 at `:12`). |
| D15 | | **PASS** | no | Relying on attempt 6: `jp_loop`, `jp_r3/r4/r5`, `jp_proc_calls`, `jp_dedupe`, push counters, `jp_listsem_fail`, `jp_push_eintr`, `jp_sigpending`/`jp_sigword`, POLL `sig`, stage codes (1.4, 1.7, 2.5 re-read). |
| D16 | | **PASS** | no | **Spot-checked**: `localTick++` (`psp.c:375`), `if (localTick - lastTick >= PSP_WATCHDOG_CYCLE*HZ)` (`:376`), `lastTick = localTick` (`:378`), Nop at `:379` (read). So the Nop runs at `psp_local_tick` ≡ 0 mod 1250 by construction. Sub-tick ordering comes from (tick, Count) (1.1). |
| D17 | | **PASS** | no | **Spot-checked**: TRIANGLE 0x10, RT 0x02, LTRG 0x200, HOLD 0x2000, VOL_UP 0x10000 (`joypad_psp.c:37-52`, read). Relying on attempt 6 for the RUNBOOK D1-D7a steps (the RUNBOOK diff does not touch D). |
| D18 | | **PASS** | no | **Spot-checked**: `telem/cbuild.sh:9` greps `objdump` output for `[$]f[0-9]` (read). 7.7 adds the mnemonic grep and the `nm` grep for printf/strtod/soft-float helpers. The r7 call `syscall(__NR_syslog, …)` is integer-only. |
| D19 | | **PASS** | no | RUNBOOK A1 (lines 154-156, read): `uClinux_TRACE`; never `uClinux`, `uClinux_FIX`, `uClinux_WIP`. |
| D20 | | **PASS** | **yes** (10.2) | Writer side (UHB `seg` stores ⌊conf/8,192⌋) and decoder side (inverse mapping) now agree (A6-3(a)). The EVENT list includes `conlevel <ret> <errno>`, as 4.2 specifies. Format sizes are unchanged (script: UHB 84 bytes, 21 words, `seg` at byte 72, `nonce` at 80; FILEHDR 44 + 1,068). Relying on attempt 6 for the remaining field-for-field match, whose text the diff does not touch. |

**Blocking FAILs: 0. Non-blocking FAILs: 0. Verdict: PASS.**

Spot-checks performed myself this round (more than five): D3, D7, D8, D14, D16, D17, D18, D19, plus the D6
and D20 source re-verification above.

---

## 5. TE10, traced against the new text

- **Start-up, fault-free.** Within a tick the flush runs before the creation step (4.3 steps 7-8). After
  step 1 (64 KB), conf = 67,072 and seg_end = 1,536.
  - The flush of ≤ 40,960 fits.
  - Each later tick adds 65,536 while room < 81,920 and takes at most 40,960, so room grows by ≥ 24,576
    per tick. The new hold branch never fires.
  - This matches the attempt-6 re-run of the start-up model.
- **Active file in creation, a step fails twice in place (data).**
  - Flushes keep advancing `seg_end` (F1(a)) until the next one does not fit.
  - The worker then holds, with rings buffering ≥ 114 s, and retries the step at 64 KB.
  - On CONFIRMED it resumes at its own `seg_end`. Nothing is written twice.
- **A fourth failure, or a FAT1 failure.** The file stops growing. A stopped file is not "being created"
  (4.4 step 5: never extended), so the switch rule applies, with no never-active target.
  - The worker holds, and creation starts a new file at the next tick (step 6).
  - After its FILEHDR and one 64 KB step it has room ≥ 42,496, so the worker switches to it with
    `seg_end = 1,536`. That file has never been active, so this is correct.
- **IF9 retire while in creation.** 4.6: "if it was still being created it stops growing". This matches
  the "(and not retired)" clause, and the case reduces to the one above.
- **Takeover.** The new instance writes only files it created (4.2). Its fresh file in creation is
  covered by the same hold rule.
- **Read-only during the hold.** No creation step is made (4.6), so the hold persists. 4.6 already
  states that recording ends there.
- **Can a never-active complete file exist while the active file is in creation?** No. Creation is one
  file at a time, and the oldest never-active file is always chosen first. So "does not switch" never
  passes over a usable file.

---

## 6. D2: independent derivation from the record format

Notation used below:
- `P08`/`P33` = a P record with that `cmd`.
- `key = rx[3] | rx[4]<<8 | rx[5]<<16 | rx[6]<<24` (`syscon.c:363`). The driver inverts it
  (`joypad_psp.c:490`), and HOLD = 0x2000 (`:49`), that is, raw `rx[4]` bit 5 clear.
- `ri_branch` comes from `read_input`'s branches (`joypad_psp.c:487-495`, read).
- `_pspSysconCtrlAStickPower`'s return is ignored (`:486`), so a P33 failure alone leaves `ri_branch` at 5.

| Row | What the fields contain | Confusable with | What separates them |
|---|---|---|---|
| H0 | No rule below fits. P, POLL, W, S and M records are kept raw, along with STATS, KMSG, PROCS, EVENT and UHB. | any | raw windows (S1 "show the raw evidence") |
| H1 | From onset, `P08` and `P33` show `ret −4`, `ack_polls` 1,000,001, `nwords 0`, `rx` all `ff` (E2, `syscon.c:154`), or `ret −3`, `drain` 0xFFFF. `dtick` is large, `lc_epc` is in the ACK loop, POLL `ri_branch 3`, `period` ≫ 14, and stats −4/−3 rise. W's own `ret` shows whether 0x00 is also refused (dossier 9.5 variant). | a single −4 from an H4 interleave (P2-P5a); H8 behind it; a stuck in-flight command | Persistence. The P08/P33 split (0x33-only keeps `ri_branch 5`). A stuck command leaves no returning P record, while W `t_busy` b0 is fixed and `lc_n` rises. |
| H2 | `P08`: `ret 0` with `nwords ≥ 1` (first byte 0, checksum skipped, `syscon.c:226`), received bytes `00`, the rest `ff`. POLL `ri_branch 4`, `jp_r4` rising, no `process_input`. | the real HOLD switch | A real HOLD frame has `ret = rx[0] > 0`, a valid checksum, and only `rx[4]` b5 clear. The C0 reference shows one. |
| H3 | `P08`: `ret 0`, `nwords 0`, `rx` all `ff`, finite `ack_polls` (E3). POLL `ri_branch 5`, `pi_flags` b0 then b1 (dedupe). In mouse mode `mouse_flags` b3 with `dx = dy = +16`. | one E3 from an H4 interleave (P3, P4, P5a, P5b) | Persistence. `wn` = 0 on the dead records. |
| H4 | A WT record (`tick` ≡ 0 mod 1250) with `t_busy` b0 and `p_head` = the `seq` of a P record with `wn ≥ 1` and `tick_in < 1250k ≤ tick_out`. The step comes from W `epc`/`r` (`ext_flags` b4 = 1, b7 = 0) or from `lc_epc`/`lc_r` (b5). The Nop's own `ack_polls`/`drain`/`drain_last` separate P4 from P5a. Onset follows the first such P record. | H10 (S overlap without a Nop); `pdflush` 5 s cadence (`kupd_last_tick`); a benign straddle | W present vs absent. `kupd_*`. The benign-hit rate over all WT. P4 and P5a may stay paired (declared, R9). |
| H5 | Persistent `ret −5` (`retries 16`, `rx[2]` ∈ {80, 81}, `syscon.c:250-254`) or `−2` (`rx[1] < 3`, or a checksum mismatch recomputable from `rx`, or `rx[1] ≥ 16`). | single −2 from H4 (P2, P6); 0x83/0x86 frames | Persistence. 0x83/0x86 frames have `ret > 0`. |
| H6 | `P08`: `ret > 0`, valid checksum, `rx[2]` = the healthy template, `rx[3..8]` constant through the post-death script while C0 showed them changing. POLL dedupe every poll. | operator not pressing; frames one command late; H7 | Operator not pressing: notes and photos only (declared). One-command-late frames show the presses shifted. H7 has `rx` following the presses. |
| H7 | `rx` follows the script, and P and POLL continue. Delivery stops at a stage visible in `push_*`, `nqueues`, `jp_listsem_fail`, `jp_wake` vs `fop_read_ret`, `md_*`, `vcs_*`, `console_sem`, or POLL `sig` b0. | H9; H6 | P/POLL continue (not H9); `rx` changes (not H6). |
| H8 | `gpio_in`, `spi_st9`, `spi_sttx`, `drain_last`, `led_or`, S `rd_*_or` and stats 100-103 leave their healthy template. | H1/H3/H5 (behaviour), H4/H10 (cause) | Reported as a flag. Registers the code never reads are unobservable (declared, dossier 9.1). |
| H9 | P and POLL stop while W continues. W shows `jp_loop` fixed and `jp_stage` 11 (arg = Q) or 9. Stats show `qfree_stage` 2 with `qfree_queue` = Q and `fop_release` +1. PROCS shows `psposk2` gone. | a stuck in-flight command; starvation | W `t_busy` set (stuck command) vs 0 (H9). Starvation has `jp_state` 0 and a large `wk_delay`. |
| H10 | A P command with `preempt_delta > 0`, `lc_epc` in S5..S20, `ms_delta > 0`, `led_or & ~0xC0 ≠ 0`. An overlapping S record (b4/b5) with its `rd_*_or`. `led_pid`; `pre_cls`/`pre_tot`/`pre_wrk` name who held the CPU. | H4; preemption without stick I/O; a clean read-back | W vs S overlap. `ms_delta 0` means preemption only. A clean read-back is inseparable (declared). |

Rows the data alone cannot separate are all declared in the design, and they are the same six that
attempt 6 listed. r6/r7 change no field these rows use: the r7 diff touches only collector rules, UHB
decoding and text. **D2 PASSES.**

---

## 7. New findings (all advisory; none fails an item)

| # | Item | B | Problem | What would close it |
|---|---|---|---|---|
| A7-1 | D6 consistency (4.4 step 6) | no | Step 6 still says the fast-attempt cap is "≥ 200: IF8 needs ≤ 128, **IF7b ≤ 152**". Section 16 says this was left on purpose because it "bounds fast attempts, and IF7b needs at most 16". But the figure in the text is neither the fast-attempt count (≤ 16 per creation that meets X, more if inodes are evicted) nor the name count (153). The bound still holds, so nothing breaks. An implementer or tester reading step 6 gets a third number for the same scenario. | Change to "IF7b ≤ 16 per creation that meets the refusing sector (≤ 153 names, 15.3)". |
| A7-2 | D6 (15.3 IF7b; 8.5 VFAT-FI) | no | The 306-name bound assumes the rejected and abandoned inodes stay cached. The design marks eviction UNVERIFIED with "the margin at the minimum budget covers 5 such". Two things are missing. **(a)** What happens if the margin runs out: creation stops, the files ahead last ≈ 9 minutes, then the worker holds and the panel shows. **(b)** Why eviction is unlikely in this run. Unused dentries and inodes are pruned only by `shrink_slab` during reclaim (`mm/vmscan.c:1048`, `:1216`) or `drop_caches`, which the design does not use. By the design's own figures, segment pages stay cached at about 2 MB per file created (10 files in 35 min, 15.6) against ≈ 20.8 MB `MemFree` (5.3). So reclaim cannot begin much before minute 30 (my estimate from those figures; UNVERIFIED on hardware), and the runbook ends normal use at 30:00 (C6). Also, VFAT-FI's "every later creation ≤ 17 names" would fail a correct implementation in a memory-limited guest. | In 15.3 state (a) and (b). Run VFAT-FI's IF7b schedule with guest memory well above the page-cache total and say so, or relax its pass condition to "≤ 17 names per later creation plus ≤ 17 per slot whose cached inode was evicted (an `abandon` at a slot previously reported as `inode reused`)". |
| A7-3 | D10 naming nit (4.3 step 3) | no | 4.3 step 3 still says "one `syslog(3)` into the 16 KB buffer, as telem (`telem.c:279-282`)". It is the same naming collision A6-2 fixed, here for type 3. The cited telem lines show the right call, so the meaning is recoverable. | Write "`syscall(__NR_syslog, 3, buf, 16384)` as telem". |

Section 2.3 notes one more point (no finding). The own-entry rule rests on the fresh inode being
`I_DIRTY_SYNC` at `fsync`. When background writeback has cleaned it, which only direct reclaim can
trigger in the milliseconds between `write()` and `fsync()`, the rule falls back to conservative or
alias-protected outcomes. Stage 2's VFAT-FI under memory pressure would exercise it. Optionally, add one
sentence to 4.4 step 4 saying so.

---

## 8. Attacks attempted that found nothing (or only the advisories above)

1. **The own-entry order with an elevator reordering by sector.** If the driver queued bios, a directory
   sector below the data could be issued first. It does not queue: `blk_queue_make_request` with a
   synchronous `psp_ms_make_request` (`ms_psp.c:190-191`, `:228-236`). Nothing found.
2. **A worker-context block-device write between the data and `fat_write_inode`.** `do_fsync` does nothing
   between `:90` and `:97` except `mutex_lock`. `__sync_single_inode` writes only the file mapping before
   `write_inode` (`:170`). `fat_write_inode` writes one buffer (`:604-606`). Nothing found.
3. **`write_inode_now(inode, 0)` being asynchronous.** `sync = 0` only skips `wait_on_inode`. The
   writeback control is `WB_SYNC_ALL`, so `write_inode(…, wait = 1)` (`fs/fs-writeback.c:158`, `:573`,
   `:585-586`). Nothing found.
4. **The red team's own text ("`pdflush` DIR record ignored").** It is weaker than the design's
   (section 2.3). The design's choice is correct.
5. **A false CONFIRM of step 0 with a lost own entry.** This is reachable only through the clean-inode
   case. The alias test (4.4 step 1: `st_size ≠ 0`, `st_ino` already seen) rejects the slot's reuse
   before any write, and the records are in data sectors with confirmed links. No loss.
6. **TE10 fix breaking the start-up path** (the first file is active while in creation). The hold branch
   cannot fire without a failure (section 5). Nothing found.
7. **TE10 fix trapping a stopped active file in a hold.** A stopped file is not "being created" (4.4
   step 5), and the switch rule then finds the next file. Nothing found.
8. **The A6-2 relocation leaving a window.** Between supervisor start and worker start there is no
   collector stick I/O, so no driver error line can be drawn. On takeover the level persists and is set
   again. Nothing found.
9. **The UHB `seg` decoder mapping for odd conf values** (stops, read-back failures, v = 0). All are of
   the form 1,536 + 8,192·j or SEG. Nothing found.
10. **Diff smuggling.** I regenerated the diff from the frozen copies; it matches `round7.diff`. No hunk
    adds a record, field, ring, HUD state, counter, runbook step or kernel change. The only new EVENT
    string is `conlevel`, which A6-2 asked for.
11. **Budget drift.** I re-ran `budget_r5.py`; every 5.x figure is unchanged.
12. **The 25 KB/s model claim.** Reproduced: seed 9 loses 15.2 s; 28 and 30 KB/s lose nothing (seeds 0-59).
13. **Page-cache growth as an observer effect.** It is not new in r7 (preallocated, kept-open segments
    since r3). By the design's figures it approaches `MemFree` only near the end of a 35-minute run, and
    PROCS records `MemFree` every ≈ 9 s, so an analyst can see it (S5). It is only noted here, as the
    background to A7-2.

---

## 9. Line count

`wc -l design/DESIGN.md` = **2,669** (section 16's own count: 2,254 through section 12, which agrees: section 13
starts at line 2255). `RUNBOOK.md` = 485.
