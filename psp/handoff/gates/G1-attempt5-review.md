# Gate G1, attempt 5: design review

| | |
|---|---|
| Gate | G1 (design review checklist D1-D20), round 5, under WORKFLOW Amendment A1 (gates/LOG.md, note of 2026-10-05) |
| Artifact | `design/DESIGN.md` revision 4 (**2,050 lines** in total; 1,920 up to the end of section 12) and `design/RUNBOOK.md` revision 4 (457 lines), both 2026-10-05 |
| Reviewer | G1 design reviewer, attempt 5. Fresh context. I did not write the design. |
| Inputs read in full | DOSSIER.md (section 9 taken as superseding, 9.6 included), WORKFLOW.md (Amendment A1 included), recon/syscon.md, recon/input.md, recon/build.md, recon/image2008.md, gates/LOG.md, G1-attempt4-review.md, G1-attempt4-redteam.md, DESIGN.md, RUNBOOK.md |
| Source used | `/home/ubuntu/psp/build/linux` (read only). The uClibc archive `/home/ubuntu/psp/staging_dir/usr/lib/libc.a` was disassembled in the `psp-build:bullseye` container with `/home/ubuntu/psp` mounted **read-only**. I wrote nothing except this file and two scratch scripts in my scratchpad. |
| **Verdict** | **FAIL**: 1 blocking FAIL (D6). 0 non-blocking FAILs. All six attempt-4 advisories (A4-1 to A4-6) are closed. |

---

## Plain-language summary (for a reader who is still learning the system)

The design records everything the syscon, the joypad thread and the Memory Stick do, and streams it to fixed-size
files on the stick. Revision 4 made those files grow in small confirmed steps, so that a write error can never
leave records in clusters the file system does not know about. That idea is sound, and almost every claim I
checked in the kernel source holds.

**One claim does not hold.** When the very first write of a new file (its "step 0") fails, the design gives up on
that file ("abandons" it) and promises never to touch it again. But the Linux FAT driver keeps that file's
in-memory record (its *inode*) and indexes it by the position of its directory slot. If the failed write meant
the slot never reached the stick, the **next** file the collector creates lands in the same empty slot, and the
kernel quietly hands it the abandoned file's inode. That inode points at a cluster whose FAT entry was never
written. The first time the new file needs another cluster, the driver walks the chain, finds a "free" entry where
it expected a link, and declares the file system corrupt: `fat_fs_panic`, which makes `/ms0` **read-only**. From
then on no new file can be created, and once the files already open are full, nothing more is recorded.

This needs only a transient write failure (a burst, or one bad tick) that hits a step 0. Amendment A1 keeps
exactly that class ("transient and sporadic write failures, bursts of any length") fully in scope. It is the same
end state (vfat read-only during the run) that failed rounds 3 and 4, reached by a new path. That is why D6 fails.

The fix is small (section 3, A5-1): after creating a file, check that it really is new (`fstat` size 0, an inode
number not seen before); if not, never write through it.

---

## 1. Checklist

| ID | B | Result | One-line reason |
|---|---|---|---|
| D1 | B | PASS | Every `Syscon_cmd` call (P, W, M), every loop (POLL), every Nop with its interrupted context, every Memory Stick transfer (S), whole-run stats, all streamed; no trigger, no hypothesis privileged (DESIGN 3.2, 3.3). |
| D2 | B | PASS | Independent derivation in section 2. Every row separates except the declared classes (H6/not pressing, H8 unread registers, P4/P5a, H10/N1m, early-death H6/N2b, H7(b)(c)/N6). |
| D3 | B | PASS | SC: `cmd` @18, `txlen` @19, `ret` s16 @20, `nwords` @22, `retries` @23, `rx[16]` @48; offsets recomputed with `struct.calcsize` (section 4). |
| D4 | B | PASS | No trigger; P/POLL rings 114.7 s; start-up backlog ≤ ≈ 1,430 P records and net drain positive at ≥ 20 KB/s (my model, section 5), so boot records are never overwritten; first flush ≈ 0.7-3.3 s after the worker starts. |
| D5 | B | PASS | DESIGN 3.3 "None. Nothing freezes"; `DEAD?` controls nothing (8.4). |
| D6 | B | **FAIL** | **A5-1.** The D6 argument rests on "vfat read-only is reachable only through silent on-disk damage (R11)" and "a burst shorter than the ring span loses nothing" (4.6). An in-scope transient failure during a creation's step 0 reaches `fat_fs_panic` through `fat_iget` slot reuse (traced in section 3). After that, loss is unbounded once the open files fill. |
| D7 | B | PASS | `pscol&` after `pspmd -s&` (`rc.sysinit` verified, lines 17-19 of the file as printed); supervision in C; nothing typed. |
| D8 | B | PASS | Explicit `psc_wd_ctx` at the only two callers; `wn`, `w_head_lo`, W `p_head`/`t_busy`/`epc`/`lc_*`, `dtick`, `lc_n`, `preempt_delta`; unchanged from r3. |
| D9 | B | PASS | New r4 writers are single: `pre_*` only by hook S with IRQs off (`kernel/sched.c:3624`), read by `psc_sc_exit` between two `pre_seq` loads; S `flags` b7 by the MS path under `s_psp_ms_rw_sem`; `meta_*` by `ctl` (collector). |
| D10 | B | PASS | 0 instructions in S5..S20 (unchanged). r4 adds one compare per context switch, ≈ 15 instructions per switch while the thread is preempted (off the thread's CPU time), ≈ 6 per MS segment; `drop_caches` replaced by a one-page `fadvise` (verified, A4-2). |
| D11 | B | PASS | No new MMIO. The b7 tag reads `bv_page->mapping->host->i_mode` (RAM). |
| D12 | B | PASS | Every 5.1-5.3 figure reproduced by script (section 5). No poll-rate printk; the 16 KB log is not used for history. |
| D13 | B | PASS (advisory A5-3) | Eight checks, decision at 3:00, early-death exception wins over "PSC TEST not seen", second `PSC TEST` independent of BTN. Advisory: 8.3's "STICK passes ≈ 1-3 s after the worker starts" confuses the first flush with the first *complete drain*; at the bottom of the design's own speed range the 3:00 margin is thin. |
| D14 | B | PASS | `ret` s16 per record; seven outcome counters per command and context (stats 31-51); `drain` 0xFFFF and `ack_polls` 1,000,001 sentinels (`SYSCON_SPIN_MAX` 1,000,000, `syscon.c:12`). |
| D15 | | PASS | `jp_loop`, `jp_r3/r4/r5`, `jp_proc_calls`, `jp_dedupe`, `jp_push_*`, `jp_listsem_fail`, `jp_push_eintr`, `jp_sigpending`/`jp_sigword`, POLL `sig`, stage codes (1.4, 1.7, 2.5). |
| D16 | | PASS | `(psp_local_tick, Count)`; the Nop at tick ≡ 0 mod 1250 (`psp.c:372-379`); 6.3 placements at Count resolution. |
| D17 | | PASS | RUNBOOK D1-D7a with C0 running the same steps healthy; bit map verified in attempt 4 and unchanged. |
| D18 | | PASS | 7.7: `telem/cbuild.sh:9` method plus mnemonic grep, `nm` grep, `flthdr`. The new `syscall()` call is integer-only. |
| D19 | | PASS | `uClinux_TRACE`; never `uClinux`, `uClinux_FIX`, `uClinux_WIP` (RUNBOOK A1). Data only under `/ms0/PSCLOG`. |
| D20 | | PASS | Every 10.3 string matches section 1 offset for offset; the r4 fields (`pre_wrk` @42, `pre_cls` @44, `pre_flags` @46, `pre_tot` @78, S `flags` b7, UHB b23-b25 and `seg` bits 28-31, stats 150-152, new EVENTs) are in the decoder spec. |

Blocking FAILs: 1 (D6). Non-blocking FAILs: 0. **Verdict: FAIL.**

### Evidence and attacks per item

**D1.** 3.2 streams every record type; 1.7 holds whole-run counters; 4.7 adds META detection read from the S records
already streamed. Attack: a shape visible only in something cut (I ring, T2c, histograms, mousedev counters).
Stage codes, raw P records and W `lc_*` remain. Nothing found.

**D2.** Section 2.

**D3.** Format string recomputed (section 4): `rx` at 48, `nwords` at 22, `ret` at 20. `nwords` is taken after S20
(`syscon.c:222`) per 1.2.

**D4.**
- Spans: P 114.7 s, POLL 114.7 s, W 1,280 s, S 181 s steady, 53 s during 8 KB creation, 29 s during 64 KB steps
  (4,096 / 77 and 4,096 / 140; my 64 KB-step figure is 144/s, a trivial difference, and the per-tick bound of
  ≤ 34 S against a cap of 64 is what matters).
- Attack (TE6, start-up on a slow stick): the first flush needs only `conf ≥ 42,496`, reached after step 0 and one
  64 KB step. My model (section 5) gives the first flush 3.3 s after worker start at 25 KB/s and 0.7 s at 300 KB/s.
  The boot backlog (≤ 35.7/s × (collector start − thread start) ≈ 600-1,430 P records) shrinks every tick even at
  20 KB/s, because `m = 4` lets 192 P records drain per tick against ≤ 161 produced. The ring never laps. PASS.

**D5.** No trigger; nothing changes resolution.

**D6.** FAIL, A5-1 (section 3). The rest of D6 holds:
- Case 1 (check passes): 4 s worst case before the check, against a 30 s hands-off wait.
- F1a (never overwrite a failed region) is correct against the source. `seg_end` advances whatever the result; the
  failed buffers are left clean and not up to date (`fs/buffer.c:449-451`) or the page has `PageError`
  (`fs/mpage.c:82-85`). Later flushes dirty only their own buffers, which writeback writes alone. So under IF7
  (persistent FSINFO or directory refusal) no record that reached the stick is rewritten. That satisfies A1's
  "data already on the stick must never be destroyed".
- But the D6 acceptance of Case 2 assumed `PSC MS RO` could only come from silent hardware damage (attempt-4
  review D6: "It is reachable only through on-disk damage (R11)"). A5-1 shows a reported, transient, in-scope
  error path to it.

**D7.** `rc.sysinit` re-read: `mount -t vfat /dev/ms0 /ms0`, `psposk2 ...&`, `pspmd -s&`. No `dirsync` mount
option, which matters for A5-1: directory writes are not synchronous at create time.

**D8.** Unchanged since r3; `psp.c:379` and `:557` are the only callers.

**D9.** Hook S runs under `spin_lock_irq(&rq->lock)` (`kernel/sched.c:3624`). Inside `if (likely(prev != next))`
(`:3700`) before `context_switch` (`:3707`). The preemption test `prev->state == TASK_RUNNING`
(`include/linux/sched.h:144`) is right for a task preempted inside `Syscon_cmd`, which never sets a sleep state;
cf. `:3627`. `wk_pending` and `pre_on` cannot both be set because a preempted task is never woken. The S b7 tag
reads `m = bvec->bv_page->mapping` for a page under writeback/read in the submitter's context; page-cache pages
keep their mapping during I/O. Single writers throughout.

**D10.** 5.4 and 7.1 state the costs. Hook positions verified: `success = 1;` at `kernel/sched.c:1657`,
`out_running:` at `:1659`, `++*switch_count` and `context_switch` at `:3700-3707`. The `fadvise` replacement is
one page of one file. `sys_fadvise64_64` (`mm/fadvise.c:26`, DONTNEED branch at `:98-108`) takes no
`inode_lock`. It calls `filemap_flush` first, which is a no-op on a just-fsynced file.

**D11.** No register access added. The LED hook keeps the single load and store (unchanged).

**D12.** Section 5. All headline numbers reproduce.

**D13.** PASS with advisory A5-3.
- A4-4 and A4-5 are fixed (section 6).
- `MS PREP` is not red.
- "PSC TEST not seen" yields to the early-death exception (RUNBOOK lines 227-229).
- The second test is requested when the six checks are first green (DESIGN 8.2 last paragraph; RUNBOOK B4).

**D14-D20.** As in the table. D20 detail is in section 4.

---

## 2. D2: independent derivation from the record format

I worked only from section 1 (record formats), the stats map and the source. Notation: `P08`/`P33` = a P record
with that `cmd`; `key = rx[3] | rx[4]<<8 | rx[5]<<16 | rx[6]<<24` (`syscon.c:363`), inverted by the driver
(`joypad_psp.c:490`), HOLD = bit 13 = raw `rx[4]` b5.

| Row | What the recorded fields would contain | Confusable with | Separated by |
|---|---|---|---|
| H0 | No rule below fits. P, POLL, W, S, M streams, STATS, KMSG, PROCS remain raw. | anything | the raw windows |
| H1 | From onset P33/P08 `ret −4`, `ack_polls 1,000,001`, `nwords 0`, `rx` all ff, `retries 0`; or `ret −3`, `drain 0xFFFF`, `spi_st9`/`spi_sttx` 0. `c_out − c_in` with `dtick` at the spin budget; `lc_epc` at S14 (or S8), `lc_n` large; POLL `ri_branch 3`, `period` ≫ 14. Stats −4/−3 counters rise. W own `ret`: −4 too (pure H1), ≥ 0 (dossier 9.5 variant). | a single −4 left by H4 at P2-P5a; N9; H8 behind it; a 0x33-only failure | persistence; N9 has no returning record (`t_busy` stuck, `lc_n` rising in every W); P08 vs P33; H8 is a flag |
| H2 | P08 `ret 0` (`rx[0] = 0` so checksum skipped, `syscon.c:226`), `nwords ≥ 1`, received bytes 00, rest ff; POLL `ri_branch 4`, `jp_r4` +1 per poll, `pi_flags` b0 = 0 | real HOLD switch; N11 | a real HOLD frame has `ret = rx[0] > 0`, valid checksum, only `rx[4]` b5 clear (C0/D7) |
| H3 | P08 `ret 0`, `nwords 0`, `rx` all ff, `ack_polls` finite; POLL `ri_branch 5`, `pi_flags` b0 then b1 (dedupe); mouse mode `mouse_flags` b3, `dx = dy = +16` | one E3 from H4 (P3, P4, P5a, P5b); N2b with a short stolen reply | persistence and `wn`; N2b has `nwords ≥ 1`, `ret > 0` |
| H4 | WT record (tick ≡ 0 mod 1250), `t_busy` b0, `p_head` = `seq` of a P record with `wn ≥ 1` and `tick_in < 1250k ≤ tick_out`; step from W `epc` (`ext_flags` b4 = 1, b7 = 0) or `lc_epc`/`lc_r` (b5); P4 vs P5a from W's own `ack_polls`, `drain`, `drain_last`; thread outcome cross-checked against the P-point | coincidence; N8; H10; WB; P4/P5a | benign-hit rate from all W; `kupd_last_tick`; S overlap instead of W; WB has `t_busy` = 0; P4/P5a may stay paired (R9) |
| H5 | persistent `ret −5` (`retries 16`, `rx[2]` ∈ {80, 81}) or `−2` (`rx[1] < 3`, recomputed mismatch, `rx[1] ≥ 16`); W own `ret` shows whether 0x00 is also BUSY | single −2 from H4 at P2/P6; N2; N3 | persistence; N2 `drain > 0`; N3 has `ret > 0` with `rx[2]` ∈ {83, 86} |
| H6 | P08 `ret > 0`, valid checksum, `rx[2]` = template value, `rx[3..8]` constant through D1-D7 while C0 changed them; POLL dedupe each poll | operator not pressing; N2b; H7 | notes and P6 only (declared); N2b: P33/W/M carry GetCtrl2-shaped frames following presses one command late; H7: `rx` follows |
| H7 | `rx` follows the script; delivery stops: (a) `push_fail`, `jp_listsem_fail` or `nqueues 0`; (b) `jp_wake` rises, `fop_read_ret` flat; (c) `md_*` rise, `md_read_ret` minus collector reads flat, `IN` (collector's own client) rising; (d) `vcs_putchar` flat or `console_sem` ≤ 0; (e) POLL `sig` b0 | H9; H6; N6; N10 | P/POLL keep coming (not H9); `rx` changes (not H6); (b)(c) and N6 overlap by definition; N10 has `pi_flags` b3 then `mouse_flags` b0 = 0 |
| H8 | `gpio_in`, `spi_st9`, `spi_sttx`, `drain`/`drain_last`, `ack_polls`, `led_or`, S `rd_*_or`, stats 102-103 leave the template (or the WB/M/WT baseline) | H1, H3, H5 (behaviour); H4, H10 (cause) | reported as flags; registers never read are unobservable (declared, dossier 9.1) |
| H9 | P and POLL stop; W continues with `jp_loop` fixed, `jp_stage` 11 (`jp_stage_arg` = Q) or 9, `t_busy` 0; stats `jp_state` 1, `qfree_stage` 2 with `qfree_queue` = Q, `fop_release` +1; PROCS `psposk2` gone | N4, N5, N9, starvation | stage and `qfree_queue`; N9 has `t_busy` set; starvation has `jp_state` 0 and large `wk_delay` |
| H10 | P command with `preempt_delta > 0`, `lc_epc` in S5..S20 (b0, b2, not nested), `ms_delta > 0`, `led_or & ~0xC0 ≠ 0`, overlapping S record (b4/b5, `rd_*_or & ~0xC0 ≠ 0`); `led_pid`; **r4:** `pre_cls` (preemptor, last holder), `pre_tot`, `pre_wrk` name who held the CPU | N1m; H4; N1; H10b | a clean read-back gives N1m (declared inseparable); W vs S; N1 has `ms_delta 0`; H10b has no command in flight |

**Rows that the data alone cannot separate** (all declared in the design):
1. H6 against "operator not pressing" (notes and P6).
2. H8 in an unread register against plain H1, H3 or H5.
3. P4 against P5a inside H4 (R9).
4. H10 against N1m when the LED read-back is clean.
5. H6 against N2b in an early death with no template (`rx2 literal`, R22).
6. H7 (b)/(c) against N6 (the same stage, by definition).

**What r4 changes in D2.**
- The new `pre_*` fields add an actor to N1, N1m and H10. They do not change which rows separate.
- The S b7 tag concerns the instrumentation (META), not a hypothesis row.
- Row WB (6.1) separates "Nop broke the link with no thread command in flight" from H4 by W `t_busy` b0. That is a
  real improvement for dossier 9.6.

**D2 PASSES.**

---

## 3. A5-1 (blocking, D6): a transient failure at a creation's step 0 leads to `fat_fs_panic`

### 3.1 What the design claims

- 4.4 step 5: a stopped or abandoned file "is never written at or above `conf`, never truncated, unlinked or
  reopened".
- 4.6: "no `fat_fs_panic` lies on this path"; "**A burst shorter than the ring span (114.7 s) loses nothing**, one
  or many".
- 14.4: "IF5: ... a creation that allocated and failed leaves an in-memory cluster beyond `conf` that no flush ever
  writes."

These are promises about what the **worker** does. The FAT driver can reuse the abandoned inode on its own.

### 3.2 The trace, link by link (all [SRC] in this tree)

1. **Step 0 of attempt A.** The worker runs `open(name_A, O_CREAT|O_EXCL)`, then writes 1,536 bytes at offset 0.
   - `vfat_create` → `vfat_add_entry` → `fat_add_entries` writes the new entry into the directory buffer and calls
     `mark_buffer_dirty`. It is synchronous only if `IS_DIRSYNC` (`fs/fat/dir.c:1261-1269`), and `/ms0` is
     mounted without `dirsync` (`rc.sysinit`).
   - `fat_build_inode` → `fat_attach(inode, i_pos)` hashes the inode by its slot position
     (`fs/fat/inode.c:404-421`, `:251-261`).
   - The write maps block 0 through `__fat_get_block`. At cluster offset 0 that calls `fat_add_cluster`
     (`fs/fat/inode.c:82-85`) → `fat_alloc_clusters` writes EOF into the cached FAT buffer and sets
     `sbi->prev_free` (`fs/fat/fatent.c:466-476`).
   - `fat_chain_add` sets `i_start = c`, with no FAT walk because `i_start` was 0 (`fs/fat/misc.c:88-96`,
     `:113-115`).
2. **The step-0 `fsync` fails** (a burst, or one sporadic failing tick: both in scope under A1).
   - `file_fsync` → `write_inode_now` → `fat_write_inode` → `sync_dirty_buffer` of the directory sector
     (`fs/fat/inode.c:600-602`). On failure `end_buffer_write_sync` clears `BH_Uptodate` (`fs/buffer.c:128-146`),
     and the buffer is already clean (`test_clear_buffer_dirty`, `fs/buffer.c:2709`).
   - `sync_blockdev` then writes the dirty FAT buffer. It fails too, and `end_buffer_async_write` clears
     `BH_Uptodate` (`fs/buffer.c:449-451`).
   - The worker abandons A (`conf` < 42,496, DESIGN 4.4 step 5). Because the data write failed as well, the next
     attempt waits at least 10 s (step 6).
3. **What the stick and memory now hold.**
   - On disk, A's directory slot is still free and FAT[c] is still FREE.
   - In memory, A's inode stays in the FAT inode hash with `i_pos` = that slot and `i_start = c`. It leaves the
     hash only via `fat_clear_inode`, unlink or rename (`fs/fat/inode.c:265-272`, `fs/vfat/namei.c:789,813`). The
     worker does none of these, and there is no reclaim pressure at ≈ 20 MB `MemFree`; that last point is
     UNVERIFIED but likely.
4. **The next attempt B** (after the stick recovers), `open(name_B, O_CREAT|O_EXCL)`.
   - `fat_add_entries` scans from position 0 and takes the **first** free run of slots (`fs/fat/dir.c:1203-1226`).
     It reads through `sb_bread` (`fs/fat/dir.c:87`), which re-reads a not-up-to-date buffer from disk
     (`fs/buffer.c:1378-1384`). So B gets **A's slot**, with the same `i_pos`.
   - `vfat_create` → `fat_build_inode` → `fat_iget(sb, i_pos)` finds A's inode in the hash and returns it
     (`fs/fat/inode.c:276-295`, `:404-406`).
   - **B's file descriptor is A's inode**: `i_start = c`, `mmu_private` = 1,536.
5. **B's step 0 "succeeds".**
   - The write at offset 0 is below `mmu_private`, so nothing is allocated (`fs/buffer.c:2111-2126`,
     `fs/fat/inode.c:68-72`).
   - `fsync` writes the data and the directory entry (start = c, size = 1,536), and FSINFO. The FAT sector is not
     dirty, so it is not rewritten.
   - `fstat` returns 1,536, which equals `conf`. The worker sees nothing wrong.
6. **B's first allocating step** (step 1 at 64 KB; step 4 at 8 KB with 32 KB clusters).
   - `fat_add_cluster` → `fat_chain_add` sees `i_start ≠ 0` → `fat_get_cluster(inode, FAT_ENT_EOF, ...)`
     (`fs/fat/misc.c:89-92`).
   - The cluster cache is empty for this inode: cluster 0 lookups return before `fat_cache_add`,
     `fs/fat/cache.c:228-230`.
   - So it reads FAT[c] from the stick, finds `FAT_ENT_FREE`, and calls
     **`fat_fs_panic(sb, "invalid cluster chain")`** (`fs/fat/cache.c:251-258`). That sets `MS_RDONLY`
     (`fs/fat/misc.c:30-33`).
7. **Consequence.**
   - Every later `open(O_CREAT)` fails with `EROFS` (`fs/namei.c:237`), so creation is dead for the rest of the
     run.
   - Writes into files already open still reach the stick: there is no `MS_RDONLY` check on the
     `vfs_write`/`generic_file_aio_write` path (only `file_update_time` checks, `fs/inode.c:1227`), and
     `fat_write_super` merely skips FSINFO (`fs/fat/inode.c:453-459`). So the active file and any complete file
     ahead keep recording for ≈ 0-9 minutes.
   - The worker then holds and the rings overwrite. For a death after that, only panel photographs remain:
     **S2 and S4 fail**.
   - The design's 2.12 statement "After that nothing reaches the stick" is also inaccurate, in the conservative
     direction.

### 3.3 How likely, and is it in scope

- It needs both the directory write and the FAT write of one step-0 `fsync` to fail, followed by recovery before
  the next attempt. A whole-stick burst or a "every I/O in the tick fails" sporadic tick does exactly that.
- **A1 keeps that class in scope** ("transient and sporadic write failures, bursts of any length").
- **Bursts.** A burst of ≳ 3 s while a file is being created (≈ 21 % of run time) works like this: the step fails,
  it is retried ≤ 3 times, growth stops, and a new attempt's step 0 runs inside the burst. The panic then follows
  as soon as the burst ends.
- **Sporadic ticks.** At attempt-4's sporadic rate (≈ 1.25 % of ticks), the ≈ 9 step-0 ticks of a 30-minute run
  are hit with probability ≈ 11 %.
- The red team ruled this end state BLIND in rounds 3 and 4 (IF5, IF4). The design's VFAT-FI schedule "an outage
  covering a creation step that allocates" would probably expose it in Stage 3. G1, however, must not pass a design
  whose claimed invariant is false at the code level.

### 3.4 What would close A5-1

All four of these:
1. After every `open(O_CREAT|O_EXCL)`, the worker checks `fstat`: `st_size == 0` and an `st_ino` not seen before in
   this run.
   - If either check fails, the file is treated as an **inherited inode**: EVENT `inode reused <name> <ino>`, it is
     never written (not even step 0), it is kept open, and the next attempt proceeds.
   - The design must show from the source why that next attempt gets a fresh slot. B's own directory entry
     (start 0, size 0) is a dirty, up-to-date buffer after `fat_add_entries`, so it is written by the next
     successful `sync_blockdev`.
   - Alternatively, the design may give another source-backed mechanism that guarantees no creation step ever runs
     `fat_chain_add` on an inode whose `i_start` was not confirmed on disk.
2. Restate 4.4 step 5, 4.6 ("no `fat_fs_panic` lies on this path"; "a burst shorter than the ring span loses
   nothing") and 14.4 (IF5) so they cover inodes that the kernel reuses, not only files the worker reopens.
3. Add a VFAT-FI schedule. Every write fails for exactly the tick of a creation's step-0 `fsync`, then the stick
   recovers. A second schedule does the same for a 30 s burst starting during an 8 KB creation. Pass condition:
   no "Filesystem panic" in the guest log, and no reused `st_ino` written.
4. Correct 2.12 and 4.6 ("nothing new reaches the stick" after read-only). Say what the worker does with open files
   after `ms_rdonly`; writes to them still succeed in this tree.

---

## 4. Format strings and offsets (D3, D20)

`struct.calcsize` (Python 3) on the 10.3 strings: SC 80, WEXT 208, POLL 40, S 40, STATS 768, CTL 32, chunk header
20, block header 8, FILEHDR fixed part 40, UHB 80.

| Field | Offset I get | Table offset |
|---|---|---|
| SC `ack_polls` | 24 | 24 |
| SC `ctx` / `wn` | 38 / 39 | 38 / 39 |
| SC `w_head_lo` | 40 | 40 |
| SC `pre_wrk` / `pre_cls` | 42 / 44 | 42 / 44 |
| SC `ms_delta` / `pre_flags` / `preempt_delta` | 45 / 46 / 47 | 45 / 46 / 47 |
| SC `rx` | 48 | 48 |
| SC `lc_epc` / `lc_dtick` / `lc_n` / `lc_flags` | 64 / 68 / 70 / 71 | same |
| SC `led_or` / `led_pid` / `pre_tot` | 72 / 76 / 78 | same |
| POLL `wk_delay` / `wk_wrk` / `wk_cls0` | 32 / 34 / 36 | same |
| S `sector` / `pid` / `flags` / `rd_set_or` | 16 / 22 / 25 / 32 | same |

All match. Nit: UHB `seg` bits 20-27 hold `conf` in 1/256 of SEG, which cannot express 256 (a complete file). It
is harmless because a complete file is no longer "being created", but the decoder spec should say so.

---

## 5. Budget (D12), recomputed

Method: Python, 250/14 polls/s, 2 commands per poll, a Nop per 1,250 ticks, a 0.23 s tick, the 10.3 sizes, per-tick
S of 5.2 (flush ticks) and 6.2 + 11.5 (creation ticks).

| Quantity | Design | Mine |
|---|---|---|
| Steady payload | 5,870 B/s | 5,871 |
| Nominal / +STATS / +STATS+PROCS flush | 1,223 / 2,011 / 3,167 | 1,222 / 2,010 / 3,166 |
| Steady on-stick | 7,123 B/s | 7,127 |
| Creation-tick flush, on-stick | 4.2 sectors, 9,350 B/s | 4.2, 9,354 |
| Fraction of ticks with a creation step | 21 % | 21.3 % (256 / 1,200 ticks per 2 MB life of 276 s) |
| Run-average S | 34.2/s | 34.2 |
| Run-average payload / on-stick | 6,334 / 7,598 B/s | 6,335 / 7,602 |
| 15 / 30 / 35 min | 6.8 / 13.7 / 16.0 MB | 6.84 / 13.68 / 15.96 |
| Files needed (+ two ahead) | 4, 7, 8 → 12, 18, 20 MB | same |
| Creation sector writes per file; average | 4,736; 17.2/s; 8.8 KB/s | 4,736; 17.18; 8.80 |
| Average sector writes / LED operations | 40.7/s (20.8 KB/s); ≈ 81/s | 40.7; 81.4 |
| Flush bounds | 8,576 per `cap`; RECS ≤ 34,364; flush ≤ 37,888 (+KMSG/EVENT) ≤ 40,960 | 8,576; 34,364; 37,692 → 37,888 |
| Rings | 652,288 B | 652,288 |
| Spans P / POLL / W / S | 114.7 / 114.7 / 1,280 / 181 s (53, 29 s in creation) | 114.7 / 114.7 / 1,280 / 181.1 (53.2, 29.3) |
| Names: fast + slow | 256 + 743 × ≥ 10 s ≥ 2 h | 2.08 h |
| Worst-case stick use | ≈ 189 MB (64 MB + 999 × 128 KB) | 188.9 MiB |

Everything reproduces. **D12 PASS.**

**Start-up model (supports D4, and A5-3).** This is a tick-by-tick model of 4.3/4.4 at start:
- collector start at uptime 20 or 40 s, thread start at 3 s (UNVERIFIED);
- step 0, then 64 KB steps while the first file is incomplete;
- flushes only when `seg_end + 40,960 ≤ conf`;
- `m = min(4, ⌈Δt / 0.23⌉)`, P cap 48m, POLL cap 24m;
- tick = 0.25 s + I/O bytes / speed.

| Stick speed | First flush after worker start | First **complete** drain after worker start |
|---|---|---|
| 300 KB/s | 0.7 s | 3-7 s |
| 100 KB/s | 1.2 s | 6-12 s |
| 52 KB/s | 1.9 s | ≈ 58-60 s |
| 35 KB/s | 2.5 s | ≈ 85-87 s |
| 25 KB/s | 3.3 s | ≈ 120-123 s |
| 20 KB/s | 4.0 s | ≈ 154-161 s |

The model's S and overhead terms are rough. The trend is robust: the 64 KB steps stretch each tick, and `m ≤ 4` caps
the drain, so the boot backlog clears slowly on a slow stick. It is never overwritten (D4 PASS), but STICK
(`durable_tick` advanced), REC and PANEL all wait for the first complete drain (A5-3).

---

## 6. Prior findings (attempt-4 review section 7)

| # | Closed? | Evidence |
|---|---|---|
| A4-1 | **CLOSED** | New 5.1 row for creation S (≤ 11.5 per 8 KB step, ≤ 27 per 64 KB step; run average 34.2/s, reproduced). 3.1 spans from per-buffer counts (53 s, 29 s). Physical writes 8.8 KB/s and 20.8 KB/s (reproduced). The 8.5 volume test names per-stream tolerances with creation minutes included. |
| A4-2 | **CLOSED** | `drop_caches` is gone (grep: only the U2/U6 history rows mention it). Replaced by `syscall(4254, fd, 0, SEG − 4096, 0, 4096, 0, 4)`. I disassembled uClibc in the container (read-only mount). `posix_fadvise` marshals five slots (`sra a2,a1,0x1f; sw v0,16(sp); li v0,4254`), as the design says. `syscall()` moves a1-a3 down and copies 20/24/28(sp) to 16/20/24(sp). `scall32-o32.S:599` is `sys_fadvise64_64 7`. The arguments land as fd, pad, offset (a2:a3), len (16-20(sp)), advice 4 (24(sp)). `invalidate_mapping_pages` of page 511 only (`mm/fadvise.c:98-108`). `syscall()` returns the raw `v0`, a positive errno on error, so "check the return is 0" detects failure. R23 states the residual. |
| A4-3 | **CLOSED** | 10.2: raw image required for "a file that holds a RECS chunk and is not 2,097,152 bytes". RUNBOOK E1 step 5: one such file is normal. 8.5 decoder case "a pull during a creation". Nit (A5-4): E2's "more than one file" counts rehearsal leftovers too. |
| A4-4 | **CLOSED** | Line 6 `MS PREP nnnS`, not red (8.2). RUNBOOK B3 says normal. The abort bullet reads "At 3:00, line 6 shows `MS NO STICK`" (RUNBOOK line 224). E2 triggers are limited to "after `SELFTEST PASS`" (RUNBOOK line 397). |
| A4-5 | **CLOSED** | Precedence stated: "The exception wins: write down 'PSC TEST not seen' and go to section D" (RUNBOOK lines 227-229; DESIGN 8.3). The second test is requested when KRN, WDOG, STICK, REC, PANEL and SUP are first all green, independent of BTN (8.2). B4 tells the operator to look at the band then. |
| A4-6 | **CLOSED** | (a) K1 ≈ 130. (b) Examples match the fixed widths (`REC LOST 0000 BAD 0000 STUCK 000`; `CMD MED 0210US MAX 01830US C 0.8US` is 34 characters). (c) B3 `PSC Trrr---`. (d) 6.2 and R8 mark the collector start UNVERIFIED; `uptime_cs` in the first UHB. (e) Cursor in the band mentioned (RUNBOOK line 105). (f) The line count is the orchestrator's: **2,050 lines in total**, 1,920 through section 12. The "+150 allowance" the designer cites (14 preamble) is not in gates/LOG.md (UNVERIFIED). |

---

## 7. Section 0 traceability, re-checked

**Rows for r4 mechanisms present:** K35 (hook S preemption branch), K36 (S b7), U5 (no overwrite plus re-send),
U6 (incremental creation, two ahead, cap, fast retry, `fadvise`), U17 (EVENT/KMSG re-send), U20 (META), X1 (r4 raw
rule), RB3 (r4), RB4, RB5, K29 (op 4 reused).

**r4 mechanisms with no row, or a row not updated** (advisory A5-4):
1. The collector's `head_regress` resync (4.3 step 2): U3 and K27 are not updated.
2. Decoder row WB and the "both results valid" benign rule (6.1, 10.7): X4 not updated.
3. 16-bit link fallback pairing by `(tick, Count)` (10.3).
4. OE5 takeover-to-PROCS annotation (10.7 step 5).
5. HUD `MS PREP` state (8.2): U9 not updated.
6. Second `PSC TEST` request independent of BTN (8.2): U19 not updated.

**Cut rows: none has become load-bearing again.**
- A1-OE3 is now carried by K35, not by the cut T2c (K11) or I ring (K10).
- OE5's new annotation uses PROCS and EVENTs, not the cut mousedev counters (K24).

Two cut rows now carry stale facts, though their cut rationale still holds for a 35-minute run:
- U7: "creation attempts are at least 10 s apart ... more than 2.7 h". r4 allows 256 fast attempts at one per tick,
  giving ≈ 2.08 h.
- U8: "the 32-segment cap". r4 caps 64 MB of confirmed bytes.

---

## 8. fs/fat and other source claims checked

| Claim (DESIGN) | Result |
|---|---|
| `__fat_get_block` allocates only at cluster offset 0 (`fs/fat/inode.c:82-85`); `mmu_private` advances per mapped block (`:93`); returns before allocation when mapped (`:68-72`); "corrupted file size" panic at `:76-79` | Verified. The step-allocates formula `⌊(conf + k − 1)/cl⌋ > ⌊(conf − 1)/cl⌋` is correct for writes starting exactly at `mmu_private`. A retry of a failed non-allocating step finds its blocks below `mmu_private`, so `fat_bmap` maps them (`fs/fat/cache.c:312-315`) and nothing is allocated. |
| `cl` = `st_blksize` = cluster size (`fs/fat/file.c:310`, `fs/fat/inode.c:1267`) | Verified. |
| `cont_prepare_write` extends or zeroes nothing for a write ending at or below `mmu_private` (`fs/buffer.c:2111-2126`) | Verified, including the boundary-page branch `if (offset <= zerofrom) zerofrom = offset;` (`:2124-2126`). |
| Flushes never dirty a FAT sector; `fsync` writes data, directory entry, FSINFO (`fs/sync.c:55-76`; `fs/fat/misc.c:40-72`; `fs/fat/inode.c:453-459`, `:556-610`) | Verified. |
| Metadata goes through the block device's page cache, whose inode has `i_mode = S_IFBLK` (`fs/buffer.c:984`, `fs/block_dev.c:573`); directory reads use `sb_bread` (`fs/fat/dir.c:87`) | Verified (`grow_dev_page` → `find_or_create_page(bdev->bd_inode->i_mapping ...)`). bdev writeback is per-buffer (`def_blk_aops` → `blkdev_writepage` → `block_write_full_page`), so each metadata S record is one sector, as META detection assumes. |
| `psp_ms_read`/`psp_ms_write` callers at `ms_psp.c:260`, `:264`, MBR `:131` | Verified. One S record per bio segment (`:252-268`). |
| A failed FAT write leaves the buffer clean and not up to date, so flush `fsync`s do not rewrite it (14.4 IF8) | Verified (`fs/buffer.c:449-451`; `block_write_full_page` clears dirty before submit). |
| IF8: each attempt moves the allocator by one cluster | Verified: search from `prev_free + 1`, `prev_free = entry` (`fs/fat/fatent.c:455-476`), and the not-up-to-date FAT sector is re-read (`fs/buffer.c:1378-1384`). |
| "A stopped file is never ... reopened" protects the chain | **False as a guarantee**: the kernel reuses an abandoned inode through `fat_iget` (A5-1). |
| Scheduler hook sites `kernel/sched.c:1657`, `:1659`, `:3624`, `:3626-3627`, `:3700-3707`; `TASK_RUNNING` (`include/linux/sched.h:144`); `nivcsw` (`:907`) | Verified. |
| `fadvise` / `syscall()` marshalling (R23) | Verified by disassembly (A4-2 above). |
| uClibc `posix_fadvise` declared at `staging_dir/usr/include/fcntl.h:184` | Verified. |
| `fs/fat/fatent.c:539`, `fs/fat/file.c:264` panics on FREE entries in free and truncate | Verified. |

---

## 9. Runbook walked as a newcomer

- **Unambiguous:** A0-A5 (256 MB in A3), B1-B6, the abort rule with its precedence, the `POLL:RATE`-only branch,
  C0-C6, D0-D9, E1-E5, and the timing summary.
- **Minor ambiguities** (A5-4):
  - C4 tells the operator to treat `PSC MS META` "exactly as for `PSC MS RO`", which includes "Do not wait for it
    to go away; it will not". META can clear (4.7). The runbook only says what happens if it is still shown at D8.
  - E1 step 5 and E2 count every short `T*.BIN` file, including rehearsal leftovers that A4 permits. That can make
    the 130 GB / 3 h raw image mandatory in a normal run. Count only files of this run's `rrr`.
- **A5-2:** after a META on a FAT-area sector the allocator has already left (IF8), the run is declared "not
  counted" even though every record is durable.

---

## 10. New findings

| # | Item | B | Problem | What would close it |
|---|---|---|---|---|
| **A5-1** | D6; 4.4 step 5, 4.6, 14.4, 2.12 | **yes** | A transient write failure (burst or one failing tick, in scope under A1) during a creation's step-0 `fsync` loses both the new directory entry and the FAT link. The next creation lands in the same empty slot and `fat_iget` hands it the abandoned inode (`fs/fat/dir.c:1203-1226`, `fs/fat/inode.c:276-295,404-406`). That inode's first allocating step walks FAT[c] = FREE and calls `fat_fs_panic` (`fs/fat/misc.c:89-92`, `fs/fat/cache.c:251-258`, `fs/fat/misc.c:30-33`). `/ms0` becomes read-only, creation ends (`fs/namei.c:237`), and recording stops once the open files fill (≈ 0-9 min). Deaths after that have no stick history. The design's "no `fat_fs_panic` on this path" and "a burst shorter than the ring span loses nothing" are false. | Section 3.4: (1) after every `open(O_CREAT\|O_EXCL)`, `fstat` must show `st_size == 0` and an unseen `st_ino`, else EVENT `inode reused`, never write that file, and show from source why the next attempt gets a fresh slot (or give another source-backed mechanism that never runs `fat_chain_add` on an unconfirmed `i_start`); (2) restate 4.4 step 5, 4.6 and 14.4 accordingly; (3) VFAT-FI schedules "all writes fail for the step-0 `fsync` tick, then recover" and "30 s burst starting during an 8 KB creation", pass = no Filesystem panic and no reused inode written; (4) correct 2.12/4.6 on writes after read-only (open files still write in this tree) and state what the worker does then. |
| A5-2 | D6 / RB5, 4.7 (advisory) | no | META is latched until the sector is written successfully again. After IF8 the allocator leaves the refusing FAT sector within ≈ 128 attempts (≈ 30 s), never writes it again, and every flush stays durable. META therefore stays on, and RUNBOOK C4/D8 declare a fully recorded run "not counted". A1 permits that outcome, but it is a run thrown away for nothing. | Key "not counted" to META **and** frozen durability (e.g. META with `DUR ≥ 3` at D8). Or clear META for a FAT-area sector once a later allocating creation step succeeds outside it (EVENT `meta bypassed`), and say so in RUNBOOK C4, D8 and E5. |
| A5-3 | D13 / 8.3 (advisory) | no | 8.3 says "STICK passes ≈ 1-3 s after the worker starts". STICK needs `durable_tick` advanced, which needs a **complete** drain (4.3 step 7), and REC and PANEL also wait for it. At start-up the 64 KB creation steps stretch every tick and `m ≤ 4` caps the drain. My model gives the first complete drain ≈ 60 s after worker start at 52 KB/s, ≈ 2 min at 25 KB/s and ≈ 2.6 min at 20 KB/s. Near the bottom of the design's own 25-300 KB/s range the 3:00 decision can fall before PANEL and BTN, and a systematic false abort would stop every attempt on that stick. | Compute the time to the first complete drain for 25-300 KB/s with the start-up steps. Then either keep start-up steps small while catching up (e.g. 64 KB only while `conf − seg_end` < 2 × 40,960) or tie the decision time to the measured state (e.g. 3:00 or 60 s after STICK, whichever is later, shown on the HUD). Correct 8.3 and 6.2. |
| A5-4 | Consistency (no D item) | no | Section 0 lacks rows for six r4 mechanisms (section 7). U7/U8 carry stale figures. 4.4 says "while fewer than two complete files are ahead" but the parenthesis says "one ready, one in creation". 4.4 does not give the delay before the next attempt after a *stop* (14.4 says ≥ 10 s). K35 says "SC bytes 42-46" although 45 is `ms_delta`. 64 KB-step S rate is 144/s, not ≤ 140/s. UHB `seg` bits 20-27 cannot hold 256. RUNBOOK C4 "it will not [go away]" is applied to META. E1/E2 count rehearsal files. The "+150 line allowance" is not in the gate log. | Add or update the section 0 rows. Align 4.4 with 14.4 and the HUD. Correct the small figures. Let RUNBOOK C4 say META may clear. Count only this run's `rrr` in E1/E2. The orchestrator notes the line count (2,050). |

---

## 11. Attacks attempted that found nothing (or only advisories)

- **IF7 (persistent FSINFO or `PSCLOG` directory refusal) under A1.**
  - Every flush writes its records once into fresh space; `seg_end` never returns.
  - Creation PAD rewrites happen only at or above `conf`.
  - The inode reuse it causes (directory refusal) rewrites only a FILEHDR at offset 0 of an abandoned cluster.
  - No record that reached the stick is destroyed. META appears in ≈ 1-2 s, on the panel and the HUD; the runbook
    covers it.
  - **A1 conditions 1-3 hold: SPOILED-DETECTED** (the red team rules).
- **IF8 (persistent allocator FAT sector) under A1.** META in ≈ 5 ticks; recovery in ≈ 30 s; flushes are
  unaffected. A1 is satisfied. The only problem is A5-2.
- **A whole-stick burst wrongly raising META.** Not possible: the rule needs successful data writes in each of the
  ≥ 3 ticks.
- **Retry in place of a non-allocating step hitting "corrupted file size".** Not possible: the retry starts at
  `conf ≤ mmu_private` and proceeds block by block (`fs/fat/inode.c:76`).
- **A flush in the same page as `conf`.** Handled: `fs/buffer.c:2124-2126` sets `zerofrom = offset`.
- **The re-send seek-back after a long outage.** Records older than the ring are counted as lost. Their first
  write is on the stick, because the data sectors accepted them and the directory size is preallocated. The Mac
  copy and the raw image both hold them.
- **Hook S branch misclassifying a voluntary sleep as a preemption.** Not possible: `Syscon_cmd` never sets a
  sleep state, and the branch also requires `psc_t_busy_p`.
- **Budget.** Every figure reproduces (section 5).
- **Format strings.** Every offset checked (section 4).
