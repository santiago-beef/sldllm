# Gate G1, attempt 6: design review

| | |
|---|---|
| Gate | G1 (design review checklist D1-D20), round 6. **Full scope**: the human suspended Amendment A1 for this attempt (gates/LOG.md, note of 2026-10-05). SPOILED-DETECTED is not available; a persistent single-sector metadata refusal must be survived like any other in-scope fault. |
| Artifact | `design/DESIGN.md` revision 5 (**2,588 lines** by `wc -l`; the design's own count in 15.8 agrees) and `design/RUNBOOK.md` revision 5 (483 lines), both 2026-10-05; scripts in `design/r5-scripts/` |
| Reviewer | G1 design reviewer, attempt 6. Fresh context. I did not write the design. |
| Inputs read in full | DOSSIER.md (section 9 superseding, 9.6 included), WORKFLOW.md (Amendments section included), recon/syscon.md, recon/input.md, recon/build.md, recon/image2008.md, gates/LOG.md, G1-attempt4-review.md, G1-attempt4-redteam.md, G1-attempt5-review.md, G1-attempt5-redteam.md, DESIGN.md, RUNBOOK.md |
| Source used | `/home/ubuntu/psp/build/linux`, read only. `/home/ubuntu/psp/staging_dir/usr/include` (headers only), `/home/ubuntu/psp/extract/root2/etc/rc.sysinit`, `/home/ubuntu/psp/telem/telem.c`. I wrote nothing except this file and one budget script in my scratchpad. The designer's simulation was run unmodified from its own directory (it writes nothing). |
| **Verdict** | **FAIL**: 1 blocking FAIL (D6, finding A6-1). 0 non-blocking FAILs. All four attempt-5 findings (A5-1 to A5-4) are closed. Three new advisories (A6-2 to A6-4). |

---

## Plain-language summary (for a reader who is still learning the system)

**What changed this round.** Revision 5 stops trusting `fsync`'s single "something failed" answer. Instead,
the collector reads the Memory Stick driver's own per-sector answers (the S records the kernel already
keeps), and works out from the file-system layout which sector is data, which is the file table (FAT),
which is FSINFO and which is a directory. Saved data counts as saved when its own sectors were written,
whatever else failed. That is a good idea, and almost every source claim behind it holds in this tree
(section 8). It also closes the attempt-5 blocking finding: when the kernel hands back an old,
half-made file under a new name (an "alias"), the collector now recognises it by its size and inode
number and never writes through it. I traced that against `fs/fat` and it works.

**What is still wrong.** The rule for confirming the very first write of a new file ("step 0") says the
file's own directory entry must have been written ("step 0 also needs its directory write (the new
entry) to succeed", 4.4 step 4). But the S records do not say *which* directory write is the new
file's own. In one in-scope fault, a directory sector X of the `PSCLOG` folder that permanently refuses
writes (red-team scenario IF7b, which A1 used to excuse and which this round must now survive), every
new file's step-0 window contains **two** directory writes: its own entry, in the next sector X+1, which
succeeds, and sector X, which fails. Sector X is rewritten because the alias entries the collector just
skipped were put into X's buffer. If "its directory write" is read as "any directory write" (which is
what the design's own Stage 3 test vector says: "directory failed at step 0 → abandoned"), no new file
can ever be created after X goes bad. The two files kept ahead last about 9 minutes; after that the
memory rings overflow and a later input death leaves no history. The design's trace of IF7b ("Nothing is
lost") only holds if the collector can tell its own entry from X, and the design never says how.

**How to fix it (cheap).** Say exactly how the own entry is recognised. The source gives a clean answer:
in `fsync` the file's own directory sector is written synchronously by `fat_write_inode` (called from
`file_fsync` line 62) **before** `sync_blockdev` (line 72) writes any other dirty directory sector, and
after the data. So "the first directory-class record after the step's data records" is the own entry.
Then fix the test vector and the IF7b name count (section 3).

---

## 1. Checklist

| ID | B | Result | One-line reason |
|---|---|---|---|
| D1 | B | PASS | Every `Syscon_cmd` call (P, W, M), every loop (POLL), every Nop with its interrupted context, every Memory Stick transfer (S), whole-run stats; all streamed; no trigger; no hypothesis privileged (DESIGN 3.2, 3.3). Unchanged kernel side in r5. |
| D2 | B | PASS | Independent derivation in section 2. Every row separates except the six declared classes. r5 changes no hypothesis-bearing field. |
| D3 | B | PASS | SC `cmd` @18, `txlen` @19, `ret` s16 @20, `nwords` @22, `retries` @23, `rx[16]` @48; recomputed with `struct.calcsize` (section 4). |
| D4 | B | PASS | No trigger; P/POLL rings 114.7 s; r5 start-up rule reproduces "first complete drain ≤ 35 s at 30 KB/s, worker at 40 s" (section 5); boot records never overwritten in the model. (A6-1 is charged to D6, not here.) |
| D5 | B | PASS | DESIGN 3.3 "None. Nothing freezes"; `DEAD?` controls nothing (8.4). |
| D6 | B | **FAIL** | **A6-1.** The IF7b loss statement ("Nothing is lost", 15.3; 4.7 "no longer stops recording") rests on a step-0 verdict that is not specified: "its directory write" cannot be identified from the S records as written, and the design's own vector (8.5) encodes the losing reading. Under it creation stops for the rest of the run once a `PSCLOG` directory sector refuses writes; loss after ≈ 9 minutes is unbounded. Everything else in D6 holds (section 3.4). |
| D7 | B | PASS | `pscol&` after `pspmd -s&` (`rc.sysinit:17-19` re-read); supervision in C; nothing typed. |
| D8 | B | PASS | Explicit `psc_wd_ctx` at `psp.c:379` and `:557` (grep: `:97` prototype, `:383` definition); `wn`, `w_head_lo`, W `p_head`/`t_busy`/`epc`/`lc_*`, `dtick`, `lc_n`, `preempt_delta`. Unchanged since r3. |
| D9 | B | PASS | r5's only kernel addition is K37: seven stats words written once (`ms_part_start` by the driver at init, six geometry words at `fat_fill_super` success, `fs/fat/inode.c:1415`). Single writers. |
| D10 | B | PASS (advisory A6-2) | 0 instructions in S5..S20 (unchanged); r5 adds no kernel work on any per-command or per-tick path. The OE8 console-level mitigation is specified with the wrong C function name (A6-2). |
| D11 | B | PASS | No new MMIO; the geometry words are RAM copies. |
| D12 | B | PASS (nit in A6-3) | Every 5.1-5.3 figure reproduces with my own script (section 5). No poll-rate printk; the 16 KB log is not used for history. 4.3's "UHB 100 … 37,692" is a stale r4 figure (r5: 104, 37,696; padded bound unchanged). |
| D13 | B | PASS | Eight checks; STICK now also needs the geometry self-check, ≥ 30 KB/s and names budget ≥ 400; aborts at 3:00 on `MS SLOW`/`MS DIR FULL`; model puts SELFTEST well before 3:00 (section 5); the early-death exception wins over "PSC TEST not seen". |
| D14 | B | PASS | `ret` s16 per record; seven outcome counters per command and context (stats 31-51); `drain` 0xFFFF and `ack_polls` 1,000,001 sentinels (`SYSCON_SPIN_MAX` 1,000,000, `syscon.c:12`). |
| D15 | | PASS | `jp_loop`, `jp_r3/r4/r5`, `jp_proc_calls`, `jp_dedupe`, `jp_push_*`, `jp_listsem_fail`, `jp_push_eintr`, `jp_sigpending`/`jp_sigword`, POLL `sig`, stage codes (1.4, 1.7, 2.5). |
| D16 | | PASS | `(psp_local_tick, Count)`; the Nop at tick ≡ 0 mod 1250 by construction (`psp.c:372-379` re-read); 6.3 placements at Count resolution. |
| D17 | | PASS | RUNBOOK D1-D7a, C0 runs D1-D7 healthy; bit map re-verified (`joypad_psp.c:40` TRIANGLE 0x10, `:37` RIGHT 0x02, `:45` LTRG 0x200, `:49` HOLD 0x2000, `:52` VOL_UP 0x10000). |
| D18 | | PASS | 7.7 method (`telem/cbuild.sh:9` grep, mnemonic grep, `nm` grep for printf/strtod, `flthdr`). New r5 userland calls (`ioctl` FIBMAP, `pread`, `syscall`) are integer-only. The `nm … printf` check would also catch A6-2 if libc `syslog()` were linked. |
| D19 | | PASS | `uClinux_TRACE`; never `uClinux`, `uClinux_FIX`, `uClinux_WIP` (RUNBOOK A1); data only under `/ms0/PSCLOG`. |
| D20 | | PASS (advisory in A6-3) | Every 10.2/10.3 string matches section 1 offset for offset (section 4). UHB `seg` stores `conf` in 8,192-byte units, which loses 1,536 bytes of the extent the decoder uses to separate anomalies (A6-3). |

Blocking FAILs: 1 (D6). Non-blocking FAILs: 0. **Verdict: FAIL.**

### Evidence and attacks per item (summary; details in later sections)

- **D1.** Attack: a failure shape visible only in a cut mechanism (I ring, T2c, histograms, mousedev counters). Stage codes, raw P records, W `lc_*`, POLL `wk_*` and SC `pre_*` remain. Nothing found.
- **D3.** `nwords` taken after S20 (`syscon.c:222`); prefill (`syscon.c:92-93`) kept in `rx`.
- **D4.** Attack: start-up on a slow stick. I re-ran the designer's model unmodified (`run(..., step_rule='rev')`): first flush 2.8 s, first complete drain 18 s / 35 s after a worker start at 20 s / 40 s at 30 KB/s, no boot record lost at 20-300 KB/s. The model's per-record flush cost (164 B per P record) is conservative against my per-record figure (≈ 127 B). PASS.
- **D6.** See section 3.
- **D9.** Attack: does any r5 userland path write a kernel word read by an interrupt? `ctl` op 4 now only feeds the panel's line-6 field (2.8); one writer (the active collector). PASS.
- **D10.** 7.1 and 7.4 add FIBMAP (`lock_kernel`, no I/O when the FAT buffer is up to date) and two `pread`s of `/proc/psc/s` per tick. Neither touches the syscon path.
- **D13.** Attack: a false abort from the speed gate. The gate uses the first two CONFIRMED 64 KB steps; r5's step rule guarantees two at start (after step 0, room = 0 → 64 KB; then room = 65,536 < 81,920 → 64 KB). The allocator starts at FSINFO's hint (`fs/fat/inode.c:1314`), so the first steps do not scan the FAT. A false abort would cost no run anyway.

---

## 2. D2: independent derivation from the record format

I worked from section 1 (SC, WEXT, POLL, S formats), the stats map (1.7) and the source only. `P08`/`P33` = P
record with that `cmd`; `key = rx[3] | rx[4]<<8 | rx[5]<<16 | rx[6]<<24` (`syscon.c:363`), inverted by the driver
(`joypad_psp.c:490`); HOLD = bit 13 = raw `rx[4]` b5 (`joypad_psp.c:49`).

| Row | What the fields would contain | Confusable with | What separates them |
|---|---|---|---|
| H0 | No rule below matches. All P, POLL, W, S, M records, STATS, KMSG, PROCS, EVENT and UHB remain raw. | anything | the raw windows |
| H1 | From onset, `P33`/`P08`: `ret −4` with `ack_polls = 1,000,001`, `nwords 0`, `rx` all `ff`, `retries 0` (E2 exit, `syscon.c:154`); or `ret −3` with `drain = 0xFFFF`, `spi_st9 = spi_sttx = 0`. `dtick` ≥ ≈ 12 ticks; `lc_epc` in the S14 (or S8) loop, `lc_n` large. POLL `ri_branch 3`, `period` ≫ 14. Stats −4/−3 counters rise. W own `ret −4` (pure H1) or `≥ 0` with normal `ack_polls` (dossier 9.5 variant). | one −4 left by an H4 interleave (P2-P5a); H8 behind the ACK; N9; a 0x33-only failure | persistence; N9 has no returning P record (`t_busy` fixed, `lc_n` rising in every W); P08 vs P33 (0x33-only leaves `ri_branch 5`); H8 is a flag, not a state |
| H2 | `P08`: `ret 0` (first byte 0, so checksum skipped, `syscon.c:211,226`), `nwords ≥ 1`, received bytes `00`, rest `ff`; POLL `ri_branch 4`; `jp_r4` +1 per poll; no `process_input` | the real HOLD switch; N11 | a real HOLD frame has `ret = rx[0] > 0`, a valid checksum and only `rx[4]` b5 clear (C0/D7 shows it) |
| H3 | `P08`: `ret 0`, `nwords 0`, `rx` all `ff`, `ack_polls` finite; POLL `ri_branch 5`, `pi_flags` b0 then b1 (dedupe); in mouse mode `mouse_flags` b3 with `dx = dy = +16` | one E3 from H4 (P3, P4, P5a, P5b); N2b | persistence and `wn = 0`; N2b has `nwords ≥ 1`, `ret > 0` |
| H4 | A WT record (`tick ≡ 0 mod 1250`), `t_busy` b0, `p_head` = `seq` of a P record with `wn ≥ 1` and `tick_in < 1250k ≤ tick_out`; step from W `epc` (`ext_flags` b4 = 1, b7 = 0) or `lc_epc`/`lc_r` (b5); P4 vs P5a from the Nop's own `ack_polls`, `drain`, `drain_last`; the thread's own outcome checked against the P-point | H10; N8; WB; coincidence; P4 vs P5a | S overlap without W (H10); `kupd_last_tick` (N8); WB has `t_busy` 0; benign-hit rate over all W; P4/P5a may stay paired (R9) |
| H5 | persistent `ret −5` (`retries 16`, `rx[2]` ∈ {80, 81}) or `−2` (`rx[1] < 3`, a mismatch recomputed from `rx`, or `rx[1] ≥ 16`); W own `ret` shows whether 0x00 is also hit | single −2 from H4 (P2, P6); N2; N3 | persistence; N2 `drain > 0` with a shifted `drain_last`; N3 has `ret > 0`, `rx[2]` ∈ {83, 86} |
| H6 | `P08`: `ret > 0`, valid checksum, `rx[2]` = template, `rx[3..8]` constant through D1-D7 while C0 changed them; POLL dedupe every poll; no P33/W/M frame of GetCtrl2 shape following the presses | operator not pressing; N2b; H7 | notes and photo P6 only (declared); N2b shows frames one command late; H7 has `rx` following |
| H7 | `rx` follows the script; P and POLL continue; delivery stops at a stage: (a) `push_fail`, `jp_listsem_fail` or `nqueues 0`; (b) `jp_wake` rises, `fop_read_ret` flat; (c) `md_*` rise, `md_read_ret` minus the collector's reads flat while `IN` rises; (d) `vcs_putchar` flat or `console_sem` ≤ 0; (e) POLL `sig` b0 | H9; H6; N6; N10 | P/POLL continue (not H9); `rx` changes (not H6); (b)/(c) and N6 are the same stage by definition; N10 has `pi_flags` b3 then `mouse_flags` b0 = 0 |
| H8 | `gpio_in`, `spi_st9`, `spi_sttx`, `drain`/`drain_last`, `ack_polls`, `led_or`, S `rd_*_or`, stats 100-103 leave the template (or the WB/M/WT baseline) | H1, H3, H5 (behaviour); H4, H10 (cause) | reported as flags; registers the code never reads are unobservable (declared, dossier 9.1) |
| H9 | P and POLL stop; W continues with `jp_loop` fixed, `jp_stage` 11 (`jp_stage_arg` = Q) or 9, `t_busy` 0; stats `jp_state` 1, `qfree_stage` 2 with `qfree_queue` = Q, `fop_release` +1; PROCS `psposk2` gone | N4, N5, N9, starvation | stage plus `qfree_queue`; N9 has `t_busy` set; starvation has `jp_state` 0 and large `wk_delay` |
| H10 | P command with `preempt_delta > 0`, `lc_epc` in S5..S20 (b0, b2, not nested), `ms_delta > 0`, `led_or & ~0xC0 ≠ 0`; overlapping S record (b4/b5, `rd_*_or & ~0xC0 ≠ 0`); `led_pid`; `pre_cls`, `pre_tot`, `pre_wrk` name who held the CPU | N1m; H4; N1; H10b | a clean read-back gives N1m (declared inseparable); W vs S; N1 has `ms_delta 0`; H10b has no command in flight |

**Rows the data alone cannot separate** (all declared in the design): (1) H6 vs "operator not pressing"; (2) H8 in
an unread register vs plain H1/H3/H5; (3) P4 vs P5a inside H4 (R9); (4) H10 vs N1m with a clean read-back;
(5) H6 vs N2b in an early death without a template (`rx2 literal`, R22); (6) H7 (b)/(c) vs N6.

**What r5 changes in D2:** nothing in SC, WEXT, POLL or S. The new UHB/FILEHDR words and stats 153-159 serve the
instrumentation, not a hypothesis row. The nonce-seeded CRC (10.2) could only hide records if the decoder used
the wrong nonce; FILEHDR carries it in plain CRC, and a takeover instance reuses it (4.2). **D2 PASSES.**

---

## 3. A6-1 (blocking, D6): the step-0 directory verdict is unspecified, and the specified reading loses IF7b

### 3.1 What the design says

- 4.4 step 4: "A step is CONFIRMED when … no FAT1 write in its window failed …, every data sector … has an
  error-free S record …, and `fstat` gives `conf + k`; **step 0 also needs its directory write (the new entry)
  to succeed**." Then: "FSINFO, FAT-mirror and **(after step 0)** directory failures do not stop growth", and
  "**Step 0 is never retried in place: any failure abandons the file**".
- 4.8: "Step verdict. 4.4 step 4." No rule says how the worker finds *its own* entry's record among the
  window's DIR-class records. The S record carries only `sector`, `pid`, `flags` (1.5).
- 8.5 verdict vectors: "directory failed at step 0 … → **abandoned**", with no distinction between the own
  entry and another directory sector.
- 15.3 IF7b: "after at most 16 slots the next fresh slot is in X + 1, which works … **Nothing is lost**."

### 3.2 Why the window always holds a failing write of X in IF7b (all [SRC], this tree)

1. Sector X of `PSCLOG` refuses writes from t0. A file created after t0 whose entry falls in X fails its own
   entry write (`fat_write_inode` → `sync_dirty_buffer`, `fs/fat/inode.c:571`, `:604-606`); the buffer is left
   clean and not up to date (`end_buffer_write_sync`, `fs/buffer.c:128-146`). The file is abandoned; its slot is
   free on disk; its inode stays hashed by `i_pos` (`fs/fat/inode.c:251-261`).
2. Next attempt: `fat_add_entries` scans from position 0 (`fs/fat/dir.c:1205-1212`) through `fat__get_entry` →
   `sb_bread` (`fs/fat/dir.c:87`), which **re-reads X from the stick** because it is not up to date
   (`fs/buffer.c:1382-1383`). Every lost slot of X looks free again. Each one returns the cached inode
   (`fat_build_inode` → `fat_iget`, `fs/fat/inode.c:404-406`, `:276-295`): an alias, rejected (4.4 step 1). Each
   rejection leaves the alias's entry in X's buffer and marks it dirty (`fs/fat/dir.c:1266-1267`).
3. The fresh file then lands in X+1. Its step-0 `fsync` runs `do_fsync` → data first (`fs/sync.c:90`), then
   `file_fsync` → `write_inode_now` (`:62`) → own entry X+1 written synchronously (succeeds), then
   `sync_blockdev` (`:72`) writes every dirty block-device buffer, **including X**, which fails.
4. So the step-0 window holds: DATA ok, DIR(X+1) ok, FAT1/FATM/FSINFO ok, **DIR(X) failed**.

Under the reading the design's own vector encodes ("directory failed at step 0 → abandoned"), this fresh file is
abandoned too. The next attempt repeats steps 2-4 (X is re-read again each time), forever. Fast attempts run one
per tick (4.4 step 6: other writes succeeded), each costing up to 17 names, so the names budget (≥ 400) is spent in
about 25 ticks, and no file is ever created again. The two files kept ahead give ≈ 9 minutes; then the worker
holds, the rings overflow after 114.7 s, and a death after ≈ t0 + 11 minutes has only panel photographs.
**S2 and S4 fail.** At full scope (A1 suspended) this is exactly the class the human asked to be survived.

Note also that 4.4 step 4's literal "any failure abandons" at step 0 would abandon on a failing FSINFO too, which
would make IF7a lose the same way. The 15.3 IF7a trace ("FSINFO is tolerated … new files continue") shows the
intended meaning is "any failure of the CONFIRMED conditions"; the text should say so.

### 3.3 Two further defects in the IF7b account (same root)

- **Later files re-pay the aliases.** Because X is re-read from the stick on every scan (step 2 above), *every*
  later creation meets all of X's lost slots again: ≤ 16 aliases + 1 fresh file per new file, not only during the
  first 16 ticks. The 15.3 figure "≤ 152 names" covers only the first phase. With ≈ 8 more files in a 35-minute run
  the total is ≈ 152 + 8 × 17 ≈ 290 names. That still fits the ≥ 400 budget, but it must be stated.
- **The Stage 3 pass condition is wrong.** 8.5 requires "IF7b: aliases rejected, ≤ 160 names" over 30 simulated
  minutes. A correct implementation exceeds 160 names once two or more files are created after t0, so the test
  would fail a correct collector (or push the implementer toward a wrong one).

### 3.4 The rest of D6 holds

- Case 1 (check passes): ≤ 4 s before the check against the 30 s hands-off wait (4.5); unchanged.
- r5 durability from data-sector S records (4.5, 4.8): a DURABLE flush is on the stick in clusters whose links
  were confirmed; I verified that a flush never allocates (section 8) and that `fsync`'s other failures cannot
  undo it.
- IF7a, IF8, IF9, A5-1, whole-stick bursts: traced (section 8, 15.3) and consistent with the source, given the
  verdict rules as written. Only the step-0 directory rule is missing.

### 3.5 What would close A6-1

All of:
1. **Define the own-entry write.** For example: "at step 0 the own entry's write is the first DIR-class S record in
   the window after the step's DATA records; it must have b1 clear. It is `fat_write_inode`'s synchronous
   `sync_dirty_buffer` (`fs/fat/inode.c:604-606`), issued from `write_inode_now` (`fs/sync.c:62`) after the data
   (`fs/sync.c:90`) and before `sync_blockdev` (`fs/sync.c:72`). Any other DIR failure in the window is META
   evidence and does not abandon." If order is not to be relied on, give another source-backed way to identify it.
2. **Fix 4.4 step 4's wording**: "Step 0 is never retried in place: if it is not CONFIRMED, the file is
   abandoned" (FSINFO, FAT-mirror and other-sector DIR failures tolerated at step 0 as at later steps).
3. **Fix the 8.5 verdict vectors**: add "step 0, own entry OK, another directory sector failed later in the window
   → CONFIRMED" and "step 0, own entry failed, another directory sector OK → abandoned".
4. **Correct 15.3 IF7b and its VFAT-FI pass condition**: every later creation re-meets ≤ 16 aliases; state the
   names used over a 35-minute run against the budget; replace "≤ 160 names" with that bound plus "a fresh file
   CONFIRMED in X+1 within N ticks of each creation need, no hold over 114.7 s".

---

## 4. Format strings and offsets (D3, D20)

`struct.calcsize` (Python 3, my script) on the 10.3/10.2 strings: SC 80, WEXT 208 (W 288), POLL 40, S 40,
STATS 768, CTL 32, chunk header 20, block header 8, **FILEHDR fixed part 44, UHB 84**. FILEHDR payload
44 + 768 + 256 = 1,068; chunk 1,088 + PAD header 20 ≤ 1,536. UHB: 21 words, `nonce` at byte 80, `drain_stuck`
word 19 (4.3 cites "UHB word 19", consistent). FILEHDR `nonce` at byte 40. SC offsets: `ack_polls` 24, `ctx` 38,
`wn` 39, `w_head_lo` 40, `pre_wrk` 42, `pre_cls` 44, `ms_delta` 45, `pre_flags` 46, `preempt_delta` 47, `rx` 48,
`lc_epc` 64, `led_or` 72, `led_pid` 76, `pre_tot` 78. All match section 1. Stats 153-159 hold 7 words as listed
(1.7). Version 5 is consistent across 1.7, 2.8 (`PSC5`), 8.2 KRN, 10.2 (`hver`, `fmt`), RUNBOOK B2.

Nit (A6-3): UHB `seg` bits 20-28 hold `conf` in units of 8,192 bytes. Every `conf` is ≡ 1,536 (mod 8,192)
(FILEHDR 1,536 B, then 64 KB or 8 KB steps), so the field understates it by 1,536 bytes. The decoder uses that
value as the confirmed extent of a file in creation (10.2 "Run selection"), so a flush ending within 1,536 bytes
of `conf` (possible only for a flush > 39,424 B, i.e. a start-up catch-up flush carrying KMSG) would have its
tail listed as an anomaly and not merged.

---

## 5. Budget (D12) and the model, recomputed

My own script (independent of `budget_r5.py`), 17.86 polls/s, 2 commands per poll, a Nop per 1,250 ticks,
0.23 s tick, the 10.3 sizes:

| Quantity | Design | Mine |
|---|---|---|
| Nominal / +STATS / +STATS+PROCS flush | 1,227 / 2,015 / 3,171 | 1,226.7 / 2,014.7 / 3,170.7 |
| Data sectors per tick; S rate (fixed point) | 3.2; 22.6/s | 3.20; 22.61/s |
| Steady payload / on-stick | 5,887 / 7,123 B/s | 5,887 / 7,123 |
| Creation-tick flush sectors 4/5/8; on-stick | 9,350 B/s | (35×2,048+4×2,560+4,096)/40 × 4.35 = 9,354 |
| Run average on-stick (21.3 % creation ticks) | 7,598 B/s | 7,597 |
| 15 / 30 / 35 min; files | 6.84 / 13.68 / 15.96 MB; 4, 7, 8 | 6.84 / 13.68 / 15.95; 4, 7, 8 |
| Creation sector writes per file | 4,736 | 4,734 (data + 2 per step + 2 per cluster) |
| All S run average | 34.2/s | 34.2 |
| Sector writes / LED ops | 40.7/s / ≈ 81/s | 40.7 / 81.4 |
| Rings | 652,288 B | 652,288 |
| Spans P / POLL / W / S steady / 64 KB steps | 114.7 / 114.7 / 1,280 / 181 / 28 s | 114.69 / 114.69 / 1,280 / 181.2 / 28.4 |
| Per-cap records; RECS max; flush max | 8,576; 34,364; 37,696 → 37,888 | 8,576; 34,364; 37,696 |

Every figure reproduces. Stale text: 4.3 "Bounds" still says "UHB 100 … 37,692" (r4); 5.1 and 15.6 have the r5
values. The padded bound (37,888) is unchanged. **D12 PASS.**

**Model (15.6), re-run unmodified.**
- Start-up (A5-3): reproduces the 15.6 table exactly (e.g. 30 KB/s: 2.8 s / 18 s and 35 s; 25 KB/s: 26 s and 48 s).
- IF4 sporadic, whole-tick model, seeds 0-59 (the seeds of the designer's own `run_if4.py`): at 25 KB/s **one run
  of 60 loses 15.2 s** (seed 9; max hold 22 s); none at 28 KB/s; none in my 15-seed checks at 30 and 52 KB/s;
  per-operation model none. The design's 200-run figures used seeds 1000-1199 (`run_if4b.py`). The statement
  "from 25 KB/s up the model loses nothing" (summary item 7, 4.8, R8, 15.6) is therefore slightly too strong;
  the gate at 30 KB/s is unaffected (A6-3).
- IF9 with the escape at 30 KB/s (2 MB region in file 2): 0 s lost, max hold 30 s. Burst of 100 s at 30 KB/s:
  0 s lost. Consistent with 15.6.

---

## 6. Prior findings (attempt-5 review section 10)

| # | Closed? | Evidence |
|---|---|---|
| **A5-1** | **CLOSED** | (1) 4.4 step 1: after every `open(O_CREAT\|O_EXCL)`, `fstat` must show `st_size == 0` and an unseen `st_ino`, else EVENT `inode reused`, UHB b28, nothing written. I verified the slot argument: the alias's own entry is written into the up-to-date directory buffer and marked dirty (`fs/fat/dir.c:1266-1267`), so the next scan's `IS_FREE` test (`:1212`, `include/linux/msdos_fs.h:47`) passes it; `fat_iget` keys only on `i_pos` (`fs/fat/inode.c:276-295`); a fresh inode is built from the new entry (start 0, size 0) with a new `iunique` number (`:412`, `:414`). Closing an alias writes nothing (`fat_file_release`, `fs/fat/file.c:117-125`, no `flush` option in `rc.sysinit:10`); the cached inode is clean (`I_DIRTY` cleared before writing, `fs/fs-writeback.c:163-166`, not re-dirtied on failure; `vfat_create` does not dirty it, `fs/vfat/namei.c:756-758`). In the attempt-5 trace B is rejected (size 1,536, seen `st_ino`) and the next fresh file never runs `fat_chain_add` on A's chain. (2) 4.4 step 5, 4.6 and 14.4 restated. (3) VFAT-FI schedules added with "no Filesystem panic, no alias written". (4) 2.12 and 4.6 corrected: read-only stops `O_CREAT` (`fs/namei.c:237-239`) but not writes (`fs/inode.c:1227`), and the worker's behaviour is stated. (A6-1 is a different path; A6-3 notes that the VFAT-FI condition "next fresh file in the first tick after the stick recovers" conflicts with the ≥ 10 s rule after a whole-stick failure.) |
| **A5-2** | **CLOSED** | META is informational (4.7, U20): no panel paint (2.10), D8 decides on `DUR` (4.5, RUNBOOK D8 (b) "`META` on line 6 is allowed"), the run counts (RUNBOOK C4.3, E5), and META clears on a good write or when bypassed (60 s without a write of the sector while every flush was DURABLE, or a FAT sector bypassed by a confirmed allocating step). |
| **A5-3** | **CLOSED** | (a) The time to the first complete drain is computed for 20-300 KB/s and two worker starts (15.6); I reproduced the table. (b) 64 KB steps only while room < 81,920 or holding (4.4 step 3); 8.3 and 6.2 corrected; a 30 KB/s gate makes a slower stick an abort. |
| **A5-4** | **CLOSED** | Section 0 rows added for all six r4 mechanisms (U3, K27, X4, X1, U9, U19); U7/U8 figures updated; 4.4 rule restated; one next-attempt rule (4.4 step 6); K35 bytes 42-43, 44, 46, 78-79; 144/s and ≥ 28 s; UHB `seg` repacked to hold 256 (see A6-3 for its granularity); RUNBOOK C4 META paragraph says it may clear; E1/E2 count only `T<rrr>` of this run; the "+150" claim withdrawn (14 preamble). |

---

## 7. Section 0 traceability, re-checked

**r5 mechanisms with a row:** K37 (geometry words), U21 (S-record verdicts, sector classes, FIBMAP extents,
`pread` windows), U22 (bad-region escape), U23 (speed gate), U24 (console level), U25 (nonce), RB6 (`MS SLOW`,
`MS DIR FULL`, A4 `mkdir`, this-run counting); changed rows U5 (range re-send), U6 (alias test and probe, step 0
strict, start-up step, attempt rule, names budget), U9, U12, U19, U20, X1, X4, RB3, RB4, RB5, K27, K29, K34.
15.7 lists them with costs.

**r5 mechanism without a row (A6-3):** the worker's new behaviour after read-only (no creation step, flush into the
prepared files, then hold; 2.12, 4.6). It is a changed rule, not covered by K31 (which is detection only).

**Cut rows:** none has become load-bearing again. U22 restores a *narrower* version of the r3 switch rule cut with
U7, as a new row with its own cost; U7's cut rationale (rotation as a switch to a ready file, no metadata write)
still holds. K10, K11, K15, K16, K24, K33, U2, U8, U10, U11, X11: no r5 rule or trace uses them.

---

## 8. fs/fat, driver and other source claims checked (new or relied on in r5)

| Claim (DESIGN) | Result |
|---|---|
| `fat_add_entries` takes the first free slot; `IS_FREE`; entries filled into buffers and marked dirty; synchronous only with DIRSYNC (`fs/fat/dir.c:1202-1226`, `:1212`, `:1255-1256`, `:1266-1269`; `msdos_fs.h:47`) | Verified. `/ms0` is mounted without options (`rc.sysinit:10`). |
| Directory reads through `sb_bread` (`fs/fat/dir.c:87`); a not-up-to-date buffer is re-read (`fs/buffer.c:1378-1384`); a failed sync write clears up-to-date (`:128-146`) | Verified. This is also what makes A6-1 recur on every scan. |
| `fat_iget` / `fat_build_inode` / `iunique` (`fs/fat/inode.c:276-295`, `:398-405`, `:412`); `vfat_create` (`fs/vfat/namei.c:745-750`, `:756-758`) | Verified. |
| 8.3 upper-case name → one slot (`fs/vfat/namei.c:599-602`, `:623-624`) | Verified (`vfat_create_shortname` returns 1, `goto shortname`). |
| `__sync_single_inode` clears `I_DIRTY` before writing (`fs/fs-writeback.c:163-166`) | Verified; not redirtied on a `write_inode` error (`:185-215`). |
| `fat_file_release` writes only with the `flush` option (`fs/fat/file.c:117-125`) | Verified. |
| `fat_write_inode` writes size, attr, start, times, not the name (`fs/fat/inode.c:586-600`); synchronous with `wait` (`:604-606`) | Verified. |
| `fat_chain_add` walks only when `i_start ≠ 0` (`fs/fat/misc.c:88-96`) | Verified (also: the new cluster is not cached, `:112`). |
| `fat_get_cluster` reads the entries of clusters before the target (`fs/fat/cache.c:241-251`); FREE → panic (`:254-258`); beyond EOF → panic (`:286-290`) | Verified. |
| Truncate after a failed `prepare_write` only when extending (`mm/filemap.c:2161-2162`) | Verified. |
| `fat_calc_dir_size` (`fs/fat/inode.c:307-319`); directory extension allocates (`fs/fat/dir.c:1277-1295`) | Verified. |
| FIBMAP needs `CAP_SYS_RAWIO`, calls `bmap` (`fs/ioctl.c:60-76`); `_fat_bmap` → `generic_block_bmap(…, 0)` (`fs/fat/inode.c:193-196`, `fs/buffer.c:2564-2574`) | Verified; `create = 0` never allocates; a block beyond `mmu_private` maps to 0 (`fs/fat/cache.c:312-315`). |
| `pread` on ring files: `FMODE_PREAD` set by `__dentry_open` (`fs/open.c:683-684`), cleared only by `nonseekable_open` (`:1119`); `sys_pread64` passes its own position (`fs/read_write.c:404-405`) | Verified. Stage 2 must use `*ppos`, not `file->f_pos`, in the ring `read` (2.8 says "leaves `f_pos`"; G2 should check). |
| Geometry in `fat_fill_super` (`fs/fat/inode.c:1234-1291`, `dir_start` `:1323`, `data_start` `:1336`, success `:1415`); FAT mirrors written as copies (`fs/fat/fatent.c:347-376`); allocator from `prev_free + 1` (`:455-476`) | Verified. |
| Partition start (`ms_psp.c:175-179`); added to `bi_sector` "at `ms_psp.c:234`"; hook "at `ms_psp.c:196`, after the partition loop" | **Line errors (A6-3):** the addition is at `drivers/block/ms_psp.c:250`; `:196` is inside the loop, which ends at `:199`. The facts are right. |
| One S record per bio segment; a failing segment ends the bio, later segments get no record (`ms_psp.c:252-276`) | Verified. Missing records make a verdict FAILED, so this is conservative, as 4.8 says. |
| `DBG` compiled in (`ms_psp.c:17-25`), lines at `:272-274`, `:370-371`; console path with interrupts off (`kernel/printk.c:819-828`); `do_syslog` case 8 (`:292-300`); default message level 4 (`:40`); FAT panic is `KERN_ERR` (`fs/fat/misc.c:22-32`); "Buffer I/O error" `KERN_ERR` (`fs/buffer.c:107`) | Verified. See A6-2 for the userland call. |
| `fs/namei.c:237-239` EROFS; `fs/inode.c:1227` `file_update_time` skips on read-only | Verified. |
| `do_fsync` order: data (`fs/sync.c:90`), then `file_fsync` (`:97`) = `write_inode_now` (`:62`), `write_super` (`:67-68`), `sync_blockdev` (`:72`) | Verified. This order is what fixes A6-1 cheaply. |
| Scheduler hooks, `TASK_RUNNING`, `nivcsw` (`kernel/sched.c:1657`, `:3624`, `:3626-3628`, `:3700-3707`; `include/linux/sched.h:144`, `:907`) | Re-verified, unchanged. |

---

## 9. Runbook walked as a newcomer

- **Unambiguous:** A0-A5 (A4's `mkdir` is one command with a check), B1-B6, the abort rule with its precedence,
  the `POLL:RATE`-only branch, C0-C6 (C4 now separates `PSC MS RO`, `META` and `PSC STALL`), D0-D9 (D8 allows
  `META`), E1-E5, the timing summary. Line 6's new strings match 8.2 (`MS PREP 012S 045KB/S`,
  `MS DUR 00.3S META 0001F2A0`, `MS SLOW 028KB/S`).
- **Minor (A6-3):** E1 step 5 needs the run number `rrr` "from line 1 during this run", but no step tells the
  operator to write it down (photo P2 shows it). Add "write down the three digits after `PSC T`" to B5.
- **Consistent with the design:** an alias or abandoned file appears on the stick as a short `T<rrr>` file. That
  happens only after a failed step (line 6 red), so E2 already requires the image; the decoder ignores files
  without RECS.

---

## 10. New findings

| # | Item | B | Problem | What would close it |
|---|---|---|---|---|
| **A6-1** | D6; 4.4 step 4, 4.8, 8.5, 15.3 | **yes** | The step-0 verdict needs "its directory write (the new entry)", but no rule identifies which DIR-class S record that is, and 8.5's vector says "directory failed at step 0 → abandoned". Under IF7b (a `PSCLOG` directory sector X refusing writes; in scope at full scope) every new file's step-0 window also holds a failing write of X, because rejected aliases dirty X's re-read buffer (`fs/fat/dir.c:87,1266-1267`; `fs/buffer.c:128-146,1382-1383`) and `sync_blockdev` writes it (`fs/sync.c:72`). Read that way, creation never succeeds again: the names budget is spent in ≈ 25 ticks, the two files ahead last ≈ 9 min, then the rings overflow and later deaths have no history (S2, S4 fail). 15.3's "Nothing is lost" depends on an unstated rule. Also: later creations re-pay ≤ 16 aliases each (15.3 counts only the first phase), and VFAT-FI's "≤ 160 names" would fail a correct implementation. | Section 3.5: (1) define the own-entry write (e.g. the first DIR-class record after the step's DATA records, which is `fat_write_inode`'s synchronous write, `fs/fat/inode.c:604-606`, issued at `fs/sync.c:62` after data `:90` and before `sync_blockdev` `:72`); other DIR failures are META evidence; (2) reword 4.4 step 4's "any failure abandons" as "not CONFIRMED → abandon"; (3) add the two step-0 vectors (own OK + other DIR failed → CONFIRMED; own failed + other OK → abandoned) to 8.5; (4) correct 15.3 IF7b's name count over a 35-minute run against the budget and replace VFAT-FI's "≤ 160 names" with that bound plus "fresh file confirmed, no hold over 114.7 s". |
| A6-2 | D10 / 4.2, 7.1, 15.4, U24 (advisory) | no | `syslog(8, NULL, 4)` names the C library's message-logging function (`staging_dir/usr/include/syslog.h`), not the kernel call. As written it would send a log message with a NULL format (or fail) and never change the console level, leaving OE8's interrupts-off drawing in error runs, with nothing on the screen to show it. The kernel side cited (`kernel/printk.c:292-300`) is right. | Specify `klogctl(8, NULL, 4)` (`staging_dir/usr/include/sys/klog.h:30`) or `syscall(__NR_syslog, 8, 0, 4)` as telem already does for type 3 (`telem/telem.c:281`); have the supervisor check the return and write it in an EVENT (or read `/proc/sys/kernel/printk`). |
| A6-3 | Consistency (D12, D20 nits) (advisory) | no | (a) UHB `seg` `conf` in 8,192-byte units understates `conf` by 1,536 B; the decoder uses it as the confirmed extent (section 4). (b) 4.3 "UHB 100 … 37,692" is r4's; r5 is 104 and 37,696. (c) `ms_psp.c:234` should be `:250`; the K37 hook "at `:196`, after the partition loop" is inside the loop (ends `:199`). (d) No section 0 row for the r5 read-only worker rule (no creation, flush prepared files, hold). (e) "From 25 KB/s up the model loses nothing" (summary 7, 4.8, R8, 15.6): the designer's own model loses 15.2 s in 1 of 60 runs at 25 KB/s (seed 9, whole-tick); none seen at ≥ 28 KB/s. (f) VFAT-FI's "next fresh file in the first tick after the stick recovers" conflicts with 4.4 step 6's ≥ 10 s wait after a whole-stick failure. (g) RUNBOOK B5 should tell the operator to write down `rrr` (E1 step 5 needs it). | (a) store `(conf − 1,536) / 8,192` or `conf / 512`, or state the 1,536-byte correction in 10.2; (b)-(c) correct the figures and citations; (d) add a row or extend K31/U6; (e) state the 25 KB/s result as measured (≈ 1 run in 60-260 loses ≈ 15 s) and keep the 30 KB/s gate; (f) restate the pass as "within 10 s plus one tick of recovery"; (g) add the note to B5. |
| A6-4 | D9/G2 note (advisory) | no | 2.8 says the ring `read()` "leaves `f_pos` at the next `seq`". With `pread` (4.8) the position passed in is a local copy (`fs/read_write.c:405`); a handler that updates `file->f_pos` instead of `*ppos` would move the drain position and break the window logic. | Say "updates `*ppos`" in 2.8 and add a Stage 3 reader test that interleaves `pread` windows with ordinary drains. |

---

## 11. Attacks attempted that found nothing (or only advisories)

- **A5-1 through other paths.** (i) Alias of an inode the worker has open (a destroyed directory sector): rejected
  by size and inode number before any write (R11). (ii) Takeover instance meeting a size-0 alias: `i_start = 0`,
  so `fat_chain_add` does not walk (`fs/fat/misc.c:88-96`); safe. (iii) An abandoned file's dirty inode being
  written later through the alias's slot: the inode is clean after its failed `fsync` and nothing dirties it.
  Nothing found.
- **FIBMAP reaching an unconfirmed link.** It runs only after the step's FAT1 writes succeeded; the walk reads
  only entries of clusters before the target (`fs/fat/cache.c:241-251`); stopped files are never FIBMAPped at or
  above `conf`. No panic path.
- **A flush verdict fooled by a shared page.** The first page of a flush holds clean buffers of the previous flush;
  writeback writes only dirty buffers, so the flush's sectors are exactly its own; a previously failed buffer
  outside the new range is at most re-marked up to date (only if the page is, `fs/buffer.c:1745` ff.,
  out-of-range branch) and never dirtied, so it is not rewritten (`fs/buffer.c:2111-2126`). Verdict correct.
- **A multi-segment data bio failing midway.** Later segments get no S record (`ms_psp.c:270-276`), so the flush
  or step is FAILED: conservative, as 4.8 says.
- **IF8 with the allocator's FAT sector shared by the active file's last entries.** Flushes never read the link
  past `conf`; a cache miss re-reads the sector from the stick, where the confirmed entries are. Allocator leaves
  the sector in ≤ 128 one-tick attempts (`fs/fat/fatent.c:455-476`), within the fast-attempt cap (≥ 200).
- **IF7a.** FSINFO failures are tolerated at every step (15.3); the 4.4 step 4 wording issue is part of A6-1 (2).
- **IF7b with X the last directory sector.** The names budget (≥ 400 free slots) and first-free-slot allocation
  imply ≥ 384 free slots after X; the design's argument holds.
- **Speed gate false abort.** Two 64 KB steps are guaranteed at start; the allocator starts at the FSINFO hint
  (`fs/fat/inode.c:1314`). An abort costs no run.
- **Nonce collisions and other boots.** Different runs have different `rrr` (4.2); the CRC seed rejects other
  boots' chunks; conflicts are reported, never dropped (10.2).
- **Budget and formats.** Every figure and offset reproduces (sections 4, 5).
- **Kernel-side perturbation.** r5 adds only one-time stores at mount and driver init; the syscon window, the
  timer interrupt and the scheduler hooks are unchanged (15.7).
