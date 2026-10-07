# Gate G1, attempt 4: design review

| | |
|---|---|
| Gate | G1 (design review checklist D1-D20), round 4 authorised by the human (gates/LOG.md, note of 2026-10-01) |
| Artifact | `design/DESIGN.md` revision 3 (**1,856 lines**; 1,795 up to the end of section 12) and `design/RUNBOOK.md` revision 3 (443 lines), both 2026-10-01 17:26 |
| Reviewer | G1 design reviewer, attempt 4. Fresh context. I did not write the design. |
| Inputs read in full | DOSSIER.md (section 9 taken as superseding), WORKFLOW.md, recon/syscon.md, recon/input.md, recon/build.md, recon/image2008.md, gates/LOG.md, G1-attempt3-review.md, G1-attempt1/2/3-redteam.md, DESIGN.md, RUNBOOK.md |
| Source used | `/home/ubuntu/psp/build/linux` (read only), `/home/ubuntu/psp/ksrc/linux-2.6.22` (for the vanilla diff), `/home/ubuntu/psp/extract/root2`, `/home/ubuntu/psp/telem/`. I wrote nothing except this file and a scratch budget script in my scratchpad. |
| **Verdict** | **PASS**: 0 blocking FAILs, 0 non-blocking FAILs. N-1 to N-5 are all closed. No cut reopens a blocking item or a formerly closed BLIND. Six new advisory findings (A4-1 to A4-6, section 7) must be closed before G3 R1. |

## Why PASS

- **The round-4 root-cause fix is correct against this tree's own vfat code.** I traced it myself (section 4):
  - In steady state, a flush into a preallocated segment never reaches the allocation branch of `__fat_get_block`, so it never dirties a FAT sector.
  - A failed `fsync` leaves only data pages, the directory-entry block or FSINFO in a "write failed, not up to date" state. Each is rewritten from memory by the in-place retry or by the next `fsync`.
  - None of the `fat_fs_panic` paths is reachable from a flush unless the on-disk chain is already damaged. That residual is declared as R11 and backed by the mandatory raw image.
- **All five attempt-3 advisories are closed** as the attempt-3 review asked (section 5).
- **The cuts do not reopen anything blocking** (section 6). Two of them narrow attribution detail; I list those explicitly.
- **The new findings are real, but none wastes the run.**
  - A4-1: the budget leaves out the S records produced by segment creation, and three derived figures are 15-25 % low. Every headline number reproduces exactly, and every bound still holds.
  - A4-2: `drop_caches` is a new non-preemptible collector action that the perturbation statement does not mention.
  - A4-3, A4-4 and A4-5: runbook and decoder rules make the raw image mandatory in normal runs, and leave two abort rules ambiguous.
  - A4-6: cosmetic inconsistencies.

On the precedent of attempt 3, where an overreaching claim (N-5) was ruled advisory, these do not fail D12 or D13. The two items closest to the line are D12 (A4-1) and D13 (A4-4, A4-5). I record the reasoning at each one.

---

## 1. Checklist

| ID | B | Result | One-line reason |
|---|---|---|---|
| D1 | B | PASS | Every call of `Syscon_cmd` (P, W, M), every loop (POLL), every Nop with its interrupted context (W), every MS segment (S), plus whole-run stats. Streamed, no hypothesis privileged. |
| D2 | B | PASS | Independent derivation in section 2. Every row separates except the declared classes. |
| D3 | B | PASS | SC: `cmd` @18, `txlen` @19, `ret` s16 @20, `nwords` @22, `retries` @23, `rx[16]` @48 (format string checked). |
| D4 | B | PASS | No trigger. The P/POLL ring holds 114.7 s, the stick is the history, and the ring never laps while the worker runs. The start-up creation keeps the first drain inside the span unless the stick is slower than about 30 KB/s; that case is counted and fails REC, so it is an abort at no cost. |
| D5 | B | PASS | 3.3: "None. Nothing freezes." `DEAD?` controls nothing (8.4). |
| D6 | B | PASS | Worst case 4 s before a passing D8 check, against a 30 s hands-off wait. Otherwise the loss is the `DUR` the kernel itself shows. Preallocation makes "durable" true on disk (section 4). |
| D7 | B | PASS | `pscol&` after `pspmd -s&` (`rc.sysinit:17-19` verified). Supervision is in C. Nothing is typed. |
| D8 | B | PASS | Explicit `psc_wd_ctx` at the only two callers (`psp.c:379`, `:557`). `wn`, `w_head_lo`, W `p_head`/`t_busy`/`epc`/`lc_*`, `dtick`, `lc_n` and `preempt_delta` record an interrupt during a thread command. Cutting the I ring does not remove any of these. |
| D9 | B | PASS | One writer per structure, including the r3 additions (`slot_bad` reader, `psc_fat_*` vfat hooks, `panel_cmd_id`/`panel_cost_last` timer). Multi-word reads are bracketed. |
| D10 | B | PASS | 0 instructions in S5..S20 (G2-checkable, 2.1/7.2). About 35 instructions before S5 and about 130 after S20, stated. The panel (0.2-1 ms) is stated, flagged per command (`lc_flags` b5) and never runs on a watchdog tick. Advisory A4-2 covers `drop_caches`, which is not on the syscon path. |
| D11 | B | PASS | No new MMIO read or write (7.1). The LED hook keeps the single load and store of `psp.c:401,406`. The panel writes VRAM RAM only. |
| D12 | B | PASS (advisory A4-1) | Every headline figure reproduces exactly (section 3). One omitted term (creation-time S records, +2 to +5 % of stick bytes) and three secondary figures are low. No bound is affected. No poll-rate printk. The kernel log is not used for history. |
| D13 | B | PASS (advisories A4-4, A4-5) | Eight checks, decision at 3:00, early-death exception, the reachable `POLL:RATE`-only branch, and a `PSC TEST` that must be seen. |
| D14 | B | PASS | `ret` s16 per record. Seven outcome counters per command and context (stats 31-51). `drain` 0xFFFF and `ack_polls` 1,000,001 sentinels (`SYSCON_SPIN_MAX` 1,000,000, `syscon.c:12`). |
| D15 | | PASS | `jp_loop`, `jp_r3/r4/r5`, `jp_proc_calls`, `jp_dedupe`, `jp_push_*`, `jp_listsem_fail`, `jp_push_eintr`, `jp_sigpending`/`jp_sigword`, POLL `sig`, stage codes. |
| D16 | | PASS | `(psp_local_tick, Count)`. The Nop runs at tick ≡ 0 mod 1250 by construction (`psp.c:372-379`). 6.3 gives before/across/after placements at Count resolution. |
| D17 | | PASS | D1-D7 plus D7a, each with a duration and a raw bit (`joypad_psp.c:36-58` verified). C0 runs the same steps while healthy. P6 photographs `RAW`. |
| D18 | | PASS | 7.7: the method of `telem/cbuild.sh:9`, plus a mnemonic grep, an `nm` grep and `flthdr`. |
| D19 | | PASS | `uClinux_TRACE`. A1 forbids `uClinux`, `uClinux_FIX` and `uClinux_WIP`. Data goes only to `/ms0/PSCLOG`. |
| D20 | | PASS | Every 10.3 string matches section 1 offset for offset (`struct.calcsize`: SC 80, WEXT 208, POLL 40, S 40, STATS 768, CTL 32, chunk 20, block 8, FILEHDR 40, UHB 80). |

Blocking FAILs: 0. Non-blocking FAILs: 0.

### Evidence and attacks per item

**D1.**
- 3.2 streams every record type at full resolution, and 1.7 carries the whole-run counters.
- Attack: a shape visible only in something that was cut (the I ring, T2c, histograms, the mousedev counters).
  - Stage-localised shapes keep their stage codes (2.5) and W `jp_stage`.
  - Per-command outcomes are kept raw in P records.
  - Nothing found.

**D3.** The format strings are checked in section 3. `nwords` is taken after S20 (`syscon.c:222`) and before `ptr` is reused at `:235` (verified). The prefill `syscon.c:92-93` survives in `rx`.

**D4.**
- Spans recomputed: P 114.7 s, POLL 114.7 s, W 1,280 s, S 181 s in steady state.
- Attack: the start-up creation delays the first drain.
  - Collector start at about 20-40 s (UNVERIFIED, see A4-6) plus 7-40 s of creation, then the first drain. That is below 114.7 s after the thread starts.
  - On a stick slower than about 30 KB/s the oldest P records are lost and counted, REC fails and the run is aborted at no cost.
- Attack: hold with no spare. The rings buffer at least 114 s while the spare is created at 64 KB per tick (7-40 s).
- Attack: S-ring overflow during creation. At most about 25 S per 64 KB step × 32 steps ≈ 800 records, against 4,096 entries. No loss.

**D5.** No trigger and nothing reduces resolution. The only limit is the 32-segment cap (64 MB, about 2.4 h).

**D6.**
- 4.5 case 1: the kernel paints when `now − durable_tick > 750`. A 5 s watch with no panel, a moving heartbeat and HUD `DUR` < 3 means durability up to 4 s before the check.
- Attack: can a "durable" record be absent from the copied files? In r2 it could (IF5). In r3, no: the clusters are linked and confirmed at creation, the flush path never allocates, and the directory size is already SEG (section 4).
- Attack: read-only `/ms0`. It is reachable only through on-disk damage (R11). Then the panel shows `PSC MS RO` permanently and D8 (b) cannot pass (RUNBOOK D8 (c), C4.2).
- The HUD can no longer overwrite the panel band at all (rows 176-271 are never written, 4.3 step 9). F-A's mechanism is gone.

**D7.** `rc.sysinit` lines 10, 14 and 17-19 verified. Busybox has no `sleep`, and the supervisor is C.

**D8.**
- `psp.c:379` and `:557` are the only calls (`:383` is the definition).
- The Nop runs with IE off before `do_IRQ` (`psp.c:348-368`).
- `plat_irq_dispatch` services only IP7 (`psp.c:637-654`), so every tick crossing a command is in `dtick`, every tick that found the thread running is in `lc_n`/`lc_*`, and every Nop is in W with `p_head`.
- Attack: the I ring is cut. D8 asks that the interrupt be *recorded as such*, not sampled. `wn`, W and `dtick` do that.

**D9.**
- The r3 additions each have a single writer: `slot_bad` (reader), `fat_panics` (any caller of `fat_fs_panic`; informational, a torn `++` is harmless), `ms_rdonly` (evaluated from `sb->s_flags` with one load), `panel_cmd_id` (T2d, IRQs off; read once by `psc_sc_exit`), and `wk_*` (scheduler hooks with IRQs off, `kernel/sched.c:441`, `:3624` verified; read between two `wk_seq` loads).
- Attack: the supervisor-turned-worker and a stalled old worker both write `ctl`. The old worker dies on the pending SIGTERM at its next return to user mode. `s_psp_ms_rw_sem` is never contended on this uniprocessor (its holder runs inside `kmap_atomic`), so `down_interruptible` cannot fail with a signal and turn a takeover into an I/O error (`ms_psp.c:333`, `:360`; dossier 9.1 on the MIPS fast path).

**D10.**
- 7.1 and 5.4 state the added time.
- `kernel/sched.c` hook sites verified: `:1657` `success = 1;`, `:1659` `out_running:`, `:3700` `if (likely(prev != next))`, `:3707` `context_switch`. `nivcsw` counts runnable switches (`:3626-3628`).
- Attack: does anything new run inside the window? Only an interrupt-level paint (stated, flagged N1p). The global `drop_caches` walk is collector-side and is advisory A4-2.

**D11.** No MMIO is added. The vfat hook reads a superblock word. The LED hook keeps the existing load and store (`psp.c:399-407`).

**D12.** See section 3.
- PASS because the stated rates, volumes, ring sizes, flush bounds and memory reproduce exactly.
- The defects are an omitted secondary term and understated derived figures that change no bound.
- If the human or the orchestrator holds "is right" to the byte, this item is the one that would flip. Advisory A4-1 says exactly what to correct.

**D13.**
- 8.2 checks: KRN, WDOG (with CTX merged in), STICK, REC, PANEL, SUP, POLL, BTN.
- Abort at 3:00 (8.3; RUNBOOK B "The decision is taken at 3:00 on the stopwatch, not earlier").
- BTN needs a P08 with `rx[3]` b4 clear and then set (TRIANGLE `0x10`, `joypad_psp.c:40`, through `syscon.c:363`).
- The `POLL:RATE`-only branch is now reachable (N-1).
- The `PSC TEST` band is an abort item (N-5).
- The literal D13 requirement holds. A4-4 and A4-5 are ambiguities that could cause a false abort, which costs nothing under WORKFLOW but should not happen.

**D14.** `ret` s16; counters at stats words 31-51; `retries` = 16 on −5 (`syscon.c:253-254`, `SYSCON_RETRY_MAX` 16 at `:13`).

**D15.** 1.7 words 52-99 and POLL fields.

**D16.**
- `psp.c:375-379`: `localTick++`, then the Nop when the difference is ≥ 1250. Both counters start at 0.
- Count is reset at `:351-352` before `:359`, so a W record reads `(1250k, small)`.

**D17.** RUNBOOK D1-D7a; the bit map is verified (TRIANGLE 0x10, RIGHT 0x02, LTRG 0x200, HOLD 0x2000, VOL_UP 0x10000).

**D18.** 7.7.

**D19.** RUNBOOK A1/A2.

**D20.**
- Offsets: SC `ack_polls` @24, `ctx` @38, `ms_delta` @45, `preempt_delta` @47, `rx` @48, `lc_epc` @64, `led_or` @72, `led_pid` @76.
- WEXT (+80): `pid` @164, `p_head` @168, `t_busy` @184, `c_pre` @188, `lc_epc` @204, `lc_r` @220, `lc_n` @284.
- POLL: `wk_delay` @32, `wk_wrk` @34, `wk_cls0` @36.
- S: `rd_set_or` @32, `rd_clr_or` @36.
- UHB is 20 words, with `drain_stuck` at word 19 as 4.3 says.
- `recsize_div4` 20/10/72/10/20.
- FILEHDR 20 + 40 + 768 + 256 = 1,084 → PAD to 1,536.
- PAD sector 20 + 492 = 512.
- Stats word map counted word by word (0-149 assigned, 150-191 reserved). Decoder 10.1 reads words 20-22 = the three addresses.

---

## 2. D2: independent derivation from the record format

I worked from section 1 (record formats) and the source only.
- "P08"/"P33": P records with that `cmd`.
- `key = rx[3] | rx[4]<<8 | rx[5]<<16 | rx[6]<<24` (`syscon.c:363`), inverted by the driver (`joypad_psp.c:490`).

| Row | What the recorded fields contain | Confusable with | What separates them |
|---|---|---|---|
| H0 | No rule below fits. The full P/POLL/W/S/M streams, STATS, KMSG and PROCS remain. | anything | the raw windows (D3) |
| H1 | From onset P33/P08 `ret` −4 with `ack_polls` 1,000,001, `nwords` 0, `rx` all ff. Or −3 with `drain` 0xFFFF and `spi_st9`/`spi_sttx` 0. `c_out − c_in` and `dtick` at the spin budget. `lc_epc` at S14 (or the drain loop) with `lc_n` large. POLL `ri_branch` 3, `period` stretched. Stats −4/−3 counters rise. W `ret`: −4 in pure H1 (with `c_pre_max`/`long_ticks` jumping, IE off), ≥ 0 in the 9.5 variant. | One −4 left by an H4 interleave; H8 behind it; N9; a failing 0x33 alone (not H1: GetCtrl2 OK and input alive) | Persistence. W `ret` (pure against variant). N9 has no P records and `t_busy` stuck. P08 against P33. |
| H2 | P08 `ret` 0 (`rx[0]` 0, so `result` = 0 and the checksum is skipped, `syscon.c:211,226`), `nwords` ≥ 4, received bytes 00, the rest ff. POLL `ri_branch` 4, `jp_r4` +1 per poll, no `process_input`/mouse calls. | The real HOLD switch; N11 | A real HOLD frame has `ret` > 0 = `rx[0]`, a valid checksum and only `rx[4]` b5 = 0 (C0 and D7 show it). |
| H3 | P08 `ret` 0, `nwords` 0, `rx` all ff, finite `ack_polls`. POLL `ri_branch` 5, `pi_flags` b0 then b1 (dedupe). In mouse mode `mouse_flags` b3 with `dx` = `dy` = +16 every poll. | A single E3 from H4; N2b with a short stolen reply | Persistence and `wn`. N2b has `nwords` ≥ 1, `ret` > 0 and the template `rx[2]` of the previous command. |
| H4 | A WT record (tick ≡ 0 mod 1250) with `t_busy` b0 and `p_head` = `seq` of a P record that has `wn` ≥ 1. The step comes from W `epc` (`ext_flags` b4 = 1, b7 = 0) or from `lc_epc`/`lc_r` (b5). P4 against P5a comes from W's own `ack_polls`/`drain`/`drain_last`. The thread's outcome is cross-checked. 6.3 placements. | Coincidence; N8; H10; P4 against P5a | Benign-hit rate from all W records; `kupd_last_tick`; an S overlap instead of W; P4/P5a may stay paired (R9). |
| H5 | Persistent `ret` −5 (`retries` 16, `rx[2]` ∈ {80, 81}) or −2 (`rx[1]` < 3, a recomputable mismatch for `rx[1]` ≤ 15, or `rx[1]` ≥ 16) | A single −2 from H4 at P2/P6; N2 | Persistence; `drain` > 0 for N2 |
| H6 | P08 `ret` > 0, valid checksum, `rx[2]` equal to the template's value, `rx[3..8]` constant through D1-D7 although C0 changed them. Dedupe every poll. | H7; N2b; "operator not pressing" | H7: `rx` follows. N2b: P33/W frames that follow the presses. "Not pressing": only notes and P6 (declared). |
| H7 | `rx` follows the script after onset, but delivery stops: `push_fail`/`jp_listsem_fail`/`nqueues` 0; or `jp_wake` without `fop_read_ret`; or `mouse_reports`/`md_notify_calls` without `md_read_ret` beyond the collector's reads; or `vcs_putchar` flat; or POLL `sig` | H9; H6; N6; N10 | P/POLL continue (not H9). `rx` changes (not H6). PROCS for N6 (H7 (b)/(c) and N6 overlap by definition, both "above syscon"). N10 has `pi_flags` b3 and then `mouse_flags` b0 = 0. |
| H8 | `gpio_in`, `spi_st9`, `spi_sttx`, `drain`/`drain_last`, `ack_polls` and the LED read-back ORs (SC `led_or`, S `rd_*_or`, stats 102-103) leave the template, or the WB/M/WT baseline when there is no template | H1/H3/H5 (behaviour); H4/H10 (cause) | Reported as flags. Registers the code never reads are not observed (declared, dossier 9.1). |
| H9 | P and POLL stop. W continues with `jp_loop` fixed and `jp_stage` 11 (`jp_stage_arg` = Q) or 9. Stats `jp_state` 1, `qfree_stage` 2 with `qfree_queue` = Q, `fop_release` +1. PROCS `psposk2` gone. | N4, N5, N9, starvation | Stage code plus `qfree_queue`; N9 has `t_busy` set; starvation has `jp_state` 0 and large `wk_delay` |
| H10 | P command with `preempt_delta` > 0, `ms_delta` > 0, `lc_epc` in S5..S20 and `led_or & ~0xC0` ≠ 0, plus an overlapping S record with `rd_*_or & ~0xC0` ≠ 0. `led_pid` names the task. No 1250 alignment needed. | H4; N1m; H10b | W against S. A clean read-back gives N1m (declared inseparable). H10b has no command in flight. |

**Rows that cannot be told apart from the data alone:**
1. H6 against "operator not pressing", separated by notes and P6 only (declared).
2. H8 in an unread register against plain H1/H3/H5 behaviour (declared, dossier 9.1).
3. P4 against P5a inside H4 (hardware unknown, R9).
4. H10 against N1 when the LED read-back is clean: N1m, declared "cannot be separated in one run", with the pre-registered comparison of 10.7 step 7.
5. H6 against N2b only in an early death with no template, where the literal `rx[2]` = 0x08 is used and flagged `rx2 literal` (R22).

**Effect of the cuts on D2.**
- The I ring's per-tick samples are replaced by `lc_*`/`lc_n` for the thread's own step (H1, N9, the H4 step) without loss.
- What is lost is the identity of a CPU-bound task that held the CPU during a mid-command suspension with no LED or S activity (an N1 attribution). No row uses it.
- In the leading case (H4 during a suspension), W `pid` still names the task that was current at the Nop.

**D2 PASSES.**

---

## 3. Budget (D12), recomputed

Method: Python with the 10.3 strings. 250/14 polls/s; 2 commands per poll; a Nop every 5 s; a 0.23 s collector tick; S per tick ≤ data + directory entry + FSINFO = 5.2.

| Quantity | Design | Mine |
|---|---|---|
| Nominal / +STATS / +STATS+PROCS flush | 1,223 / 2,011 / 3,167 → 1,536 / 2,048 / 3,584 | 1,222.7 / 2,010.7 / 3,166.7 → same |
| Data sectors per tick | 3.2 | 3.20 |
| Payload / records on the stick | 5,870 / 7,123 B/s | 5,869.9 / 7,123.5 |
| 15 / 30 / 35 min | 6.4 / 12.8 / 15.0 MB | 6.41 / 12.82 / 14.96 |
| Segments needed (+ spare) | 4, 7, 8 → 10, 16, 18 MB | same (usable ≈ 2.05 MB per segment) |
| Rings | 652,288 B | 327,680 + 81,920 + 73,728 + 163,840 + 5,120 = 652,288 |
| Spans P / POLL / W / S (steady) | 114.7 / 114.7 / 1,280 / 181 s | same |
| Record sector writes, LED operations | 22.6/s, 45/s | 22.6, 45.2 |
| Creation sector writes per segment | ≈ 4,744 → +16.1/s | 4,736 → 16.1/s |
| Creation physical bytes | "≈ 7 KB/s more" | **8.25 KB/s** (by the design's own 4,744 × 512 / 294 s) |
| Average physical writes (R8) | "≈ 15 KB/s" | **≈ 19.8 KB/s** of sector writes (38.7/s × 512) |
| LED average / creation minute / start-up | 77 / 206 / ≈ 1,150 per s | 77.4 / 206 / 1,166 |
| S rate during 8 KB creation (3.1) | ≤ 42/s, span ≥ 97 s | **≈ 64/s, span ≈ 64 s** (see below) |
| S rate during 64 KB start-up creation | ≤ 87/s, span ≥ 47 s | **≈ 109/s**, but only ≈ 800 records in total (fits 4,096) |
| S bytes in 5.1 | ≤ 22.6/s × 40 = 904 B/s | **omits creation-step S records**: +157 B/s average by the design's 3.1 figure, +332 B/s by mine (+2.2 % / +4.7 % of 7,123) |
| Flush bounds | RECS ≤ 34,364; flush ≤ 37,888 (+KMSG/EVENT) ≤ 40,960 | same |
| `wk_delay` saturation | 76 ms, 19 ticks | 18.99 ticks |
| Kernel memory | ≈ 653 KB, 3.1 % of 20.8 MB | same |

**Why S per creation step is higher than the design assumes.** Each step writes from page offset 1,536, because the FILEHDR is 1,536 bytes and the steps are a whole number of pages long.
- The first page of a step therefore holds clean, up-to-date buffers 0-2 from the previous step.
- `__mpage_writepage` sends such a page down the "confused" path (`fs/mpage.c:511-512`: `if (!buffer_dirty(bh) || !buffer_uptodate(bh)) goto confused;`).
- That path uses `block_write_full_page`, one bio per dirty buffer.
- `psp_ms_transfer_bio` makes one `psp_ms_write` call, and so one S record, per bio segment (`drivers/block/ms_psp.c:252-265`).
- So an 8 KB step yields 5 + 2 data S records + directory + FSINFO + ½ FAT ≈ 9.5, not ≈ 4.5.

This changes no bound:
- the S ring never overflows during creation;
- stick space is ≤ 19 MB against 128 MB checked;
- the per-tick flush bounds do not involve creation.

It does make the 5.1 S row false as a stated maximum ("rates are maxima"), the 3.1 creation spans too long, and the Stage 3 volume test's per-stream ±10 % comparison ambiguous. Advisory **A4-1**.

---

## 4. Preallocation against this tree's `fs/fat` (my own trace)

`fs/fat`, `fs/vfat`, `fs/buffer.c`, `fs/mpage.c` and `fs/sync.c` are identical to vanilla 2.6.22. `diff -rq` and `diff -q` against `/home/ubuntu/psp/ksrc/linux-2.6.22` show build outputs only. `CONFIG_VFAT_FS=y`, `CONFIG_PROC_SYSCTL=y` and `drop_pagecache` are in `System.map`, so `/proc/sys/vm/drop_caches` exists.

### 4.1 Does a steady-state overwrite of an already-linked cluster dirty any FAT sector? **No.**

1. `write()` → `fat_prepare_write` → `cont_prepare_write(..., &mmu_private)` (`fs/fat/inode.c:143-148`).
   - With `mmu_private` = SEG = 2,097,152, `pgpos` = 512.
   - Every page of the segment has `index ≤ 511 < pgpos`, so it takes the "completely inside the area" branch (`fs/buffer.c:2111-2113`).
   - It extends nothing and calls `__block_prepare_write(offset, to)`.
2. For each unmapped buffer, `fat_get_block` → `__fat_get_block`.
   - `fat_bmap` computes `last_block` from `mmu_private` (`fs/fat/cache.c:312-315`) and maps the block through `fat_bmap_cluster` → `fat_get_cluster` (cluster cache, `cache.c:217-274`).
   - It returns at `fs/fat/inode.c:68-72`, **before** the allocation branch (`:82-88`) and before the "corrupted file size" panic (`:76-79`).
3. Commit: `generic_commit_write` does not change `i_size` (write below `i_size`). `fat_commit_write` dirties the inode only once, for ATTR_ARCH (`inode.c:150-160`). `file_update_time` dirties it for mtime.
4. `fsync` = `do_fsync` (`fs/sync.c:78-106`):
   - `filemap_fdatawrite` writes the data pages;
   - `file_fsync` (`:55-76`) calls `write_inode_now`, then `fat_write_inode` (`inode.c:556-611`). That rewrites size, attr, start cluster and times of the directory entry from memory and calls `sync_dirty_buffer`;
   - `write_super` → `fat_clusters_flush` (`misc.c:40-72`) rewrites FSINFO every time;
   - `sync_blockdev` writes the remaining dirty buffers.
   - **No FAT entry is written.**
5. A FAT sector can be **read** on a cluster-cache miss: a non-contiguous chain beyond the 8-entry cache, with contiguity UNVERIFIED, as the design says.
   - Such a read panics only if the on-disk chain already reads FREE (`cache.c:254-259`) or ends early (`cache.c:287-290`), which is the R11 condition.
   - A failed read returns an error without a panic (`cache.c:251-253`), which the design handles as an in-place retry.

### 4.2 What does a failed `fsync` leave behind?

- **Data pages, mpage path.**
  - `PageError`, and `AS_EIO` on the file's mapping (`fs/mpage.c:82-85`). The page is clean.
  - `do_fsync`'s `filemap_fdatawait` (`fs/sync.c:101`) returns −EIO (`mm/filemap.c:272-283`).
  - Nothing rewrites the page until our in-place retry dirties it again.
- **Data pages, buffer path** (partially clean pages, which is the normal case at a flush's first page):
  - `end_buffer_async_write` sets `AS_EIO`, clears `BH_Uptodate` and sets `PageError` (`fs/buffer.c:449-452`).
  - The retry writes whole 512-byte blocks, so nothing is read.
  - `__block_commit_write` marks them up to date and dirty, so they are rewritten.
- **Directory-entry block** (`sync_dirty_buffer` from `fat_write_inode` with `wait` = 1) **or FSINFO** (`sync_blockdev`):
  - The buffer is clean and not up to date.
  - The next `sb_bread` re-reads it from the stick (`fs/buffer.c:1382-1383`, `:1179-1194`) and the entry or FSINFO is rebuilt from memory.
  - FSINFO is rebuilt on every `fsync`.
  - The directory entry is rebuilt when the inode is dirtied again (mtime). Its size and start cluster do not change in steady state, so the old on-disk entry is already right, unless the failed write damaged the sector (R11).
- **In-memory FAT and cluster cache.** Untouched: nothing in the flush path wrote them.
- **Retry geometry.** The retry may be shorter than the failed flush (the per-ring cap with a smaller `m`). The tail of the failed range then holds stale or partial chunks above the new `seg_end`.
  - Later flushes overwrite it.
  - The decoder drops CRC-bad chunks and deduplicates by `(ring, seq)`.
  - `durable_next` advances only to the last `seq` of a successful flush.
  - Nothing is lost.

**Conclusion.**
- No path from a tick flush, or from its failure, to `fat_fs_panic` or to an orphaned durable record exists unless the stick silently damages a sector (R11).
- The creation path is protected by "abandon on any error, never extend, truncate, unlink or reopen":
  - `fat_chain_add` (`misc.c:78-115`) walks only the spare's own chain, which every previous step `fsync`ed successfully;
  - a new spare starts with `i_start` = 0, so no walk is needed.
- Error attribution between the tick flush and the creation step can be wrong when pdflush writes a dirty buffer that belongs to the other file. The result is always conservative: an extra in-place retry, or an unnecessary abandon. It never causes a missed error.
- **IF5, IF1 and IF4 are closed by the mechanism.** That is my code-level opinion. The red team rules the scenarios.

---

## 5. Prior findings (attempt-3 review section 6)

| # | Closed? | Evidence |
|---|---|---|
| N-1 | **CLOSED** | 8.3 and RUNBOOK B4: TRIANGLE is held when KRN, WDOG, STICK, REC, PANEL and SUP are green "whatever POLL shows", up to three holds. CTX is merged into WDOG. The never-press SELECT row lists the abort-rule tap (RUNBOOK line 108). There is a G3 R4 note (RUNBOOK lines 22-23; 8.3 last bullet). The branch is now reachable: I walked it with a failing 0x33. |
| N-2 | **CLOSED** | 8.2: ten lines, each ≤ 35 characters. I counted the longest forms: line 7 is 34, line 10 is 34, line 5 is 30, line 3 with `POLL:RATE` is 23. At 12 px from x = 8, a 35-character line ends at x ≤ 427, before the heartbeat block at x = 428 (`telem.c:183,373`). Rows 176-271 are not written. The Stage 3 render test asserts no glyph at x ≥ 428 in rows 8-39 or in rows ≥ 168. The check names are split over lines 2 and 3. |
| N-3 | **CLOSED** | 8.2 defines `IN` = UHB `mouse_press_total` (press edges as at `telem.c:270`, mouse mode only) and `DELIV` = age of the latest POLL with `push_ok` > 0 or `mouse_flags` b3. RUNBOOK line 76 and C5 say `IN` counts only in mouse mode. |
| N-4 | **CLOSED** | Rows H6 and N2b compare with the template's per-command `rx[2]`. The literal is used only without a template and is flagged `rx2 literal`. 10.7 step 2 learns `rx[2]`. R22 marks it UNVERIFIED. There is a Stage 3 sequence with a healthy `rx[2]` ≠ 0x08. |
| N-5 | **CLOSED** | The read-back is cut (U10). 8.2 PANEL says what it proves and what it does not, citing `pspfb.c:24,396` and `fb_sys_fops.c:41-45`. "Never saw `PSC TEST`" is an abort item (8.3, RUNBOOK B). A second test is shown after BTN. (See A4-5 for its interaction with the early-death exception.) |

---

## 6. Audit of the cuts (section 0 rows marked CUT)

| Cut | What depended on it in D1-D20 or attempts 1-3 | Result |
|---|---|---|
| K7 LED per-bit counts, ANDs, `ms_b3`, `led_rd_*_b3` | The A1 UL1 fix asked for ORs, ANDs and per-bit counts. The A2 and A3 UL1 DIAGNOSABLE rulings used only `led_or` and `rd_clr_or`. H10b uses S `flags` b2/b3 and `rd_set_or`, which are kept. | Not reopened |
| K10 I ring | A1 TE2 (closed by `lc`, K8, since r1); A2 TE4 (the I nested flag was supporting; `lc_nested` and `lc_flags` b4 are kept); H1/N9 signatures (`lc_epc` + `lc_n`); A3 OE6 recommendation (moved to SC `lc_flags` b5); D8 (section 1). Lost: the identity of a CPU-bound preemptor during a mid-command suspension without LED/S activity. No row needs it, and W `pid` keeps it for the H4 case. | Not reopened |
| K11 T2c wait-class sampling | The A1 OE3 fix. A2 OE3 was AMBIGUOUS with T2c present and closed in A3 by the scheduler hooks (K12, kept but simplified). The simplification replaces "longest holder / per-class share" with the delay, the exact collector part `wk_wrk`, the wake-time class, the last holder and the switch count. The S5 question ("did `pscol` cause it?") is still answered exactly. Attribution among several non-collector holders is coarser. | Not reopened (narrowed) |
| K15 W stack snapshot | No scenario. TE5 cited `gpr`, which is the kept `r[16]`. k and j come from `t0`/`a3` in `r`. | Not reopened |
| K16 W copies of heads, `ms_ip_*`, `durable_tick` | No scenario. A1 OE1 used the marker in stats and the panel (kept, K20/K30). | Not reopened |
| K24 mousedev open/release counters | A2 OE5 was DIAGNOSABLE with the counters only recommended. The A3 ruling also rested on EVENTs, the takeover, the `do_exit` hook and N5 (kept). | Not reopened |
| K33 out-of-bounds checksum recompute | An A2 note, not a scenario. H5 −2 with `rx[1]` ≥ 16 is still identified by `ret` and `rx[1]`. | Not reopened |
| U2 standby worker | A1 IF2 (formerly BLIND). It is replaced by U1: the supervisor runs the worker loop in-process with its boot-time block. A takeover needs only order-0 slab allocations: file opens and page cache. The trace holds: death seen within 2 s, seek to `durable_next`, fresh segment in 7-40 s, inside the 114.7 s span. A second failure is unrecovered (R14), as in r2. | Not reopened |
| U7 r2 segment rules | A2 IF4 (formerly BLIND, name exhaustion), F-C, F-D. Replaced: creation attempts are ≥ 10 s apart, 999 names per run, rotation is a switch to a ready spare, and FILEHDR is written by creation. No exhaustion path. | Not reopened |
| U8 volume cap / summary mode | No scenario. The 32-segment cap replaces it. A full stick (ENOSPC at creation) is an abandon plus a hold. | Not reopened |
| U10 PANEL read-back | N-5 asked for it to be corrected. | Required, not reopened |
| U11 SELFTEST chunk | It duplicated UHB b1-b8. | Not reopened |
| X11 decoder extras (`i.csv`, `wait_hist`, `wk_acc`, mousedev alignment, `--photo`) | No gate report cited `--photo` or wall-time correction (grep). The takeover/`jp_exit_tick` annotation is kept (10.7 step 5). The HUD `UP` with stopwatch photos P2/P5 allows manual alignment. | Not reopened |
| K29 `ctl` op 4 | Went with U7. | Not reopened |

**No cut reopens a blocking item or a formerly closed BLIND.** Two closures are now narrower and should be stated as such in 13.3:
- the OE3 attribution among several non-collector holders;
- N1 preemptor identity.

---

## 7. New findings (all advisory; close before G3 R1)

| # | Item | Problem | What would close it |
|---|---|---|---|
| **A4-1** | D12 / 5.1, 3.1, 5.1 paragraph, R8 | (i) The 5.1 S row "≤ 22.6/s" (in a table headed "rates are maxima") omits the S records generated by segment creation. The design's own 3.1 gives ≤ 42/s during creation; per-buffer bio accounting gives ≈ 64/s (`fs/mpage.c:511-512` confused path for the partially clean first page of every step; one S per bio segment, `ms_psp.c:252-265`). That is +2.2 % to +4.7 % of stick bytes on average. (ii) The 3.1 S spans during creation (≥ 97 s, ≥ 47 s) are too long (≈ 64 s, ≈ 37 s). (iii) "≈ 7 KB/s more physical writes" is 8.25 KB/s by the design's own 4,744 sectors per 294 s. (iv) R8's "≈ 15 KB/s of physical writes" is ≈ 19.8 KB/s of sector writes. | Add a 5.1 row "S records from segment creation" (rate during creation and run average) and correct the totals. Restate the 3.1 creation spans from per-buffer S counts, or bound them by the sector rate. Correct the two physical-rate figures. Make the Stage 3 volume test name per-stream tolerances with creation minutes included. |
| **A4-2** | D10 / 7.1, 7.4, S5 | 4.4 step 4 writes `1` to `/proc/sys/vm/drop_caches` after each segment's creation (at start, about every 4.9 min, after a takeover). `drop_pagecache` walks every superblock's inode list under `spin_lock(&inode_lock)` (`fs/drop_caches.c:15-26`). With `CONFIG_PREEMPT` that disables preemption for the whole walk. `invalidate_mapping_pages` has no reschedule point (`mm/truncate.c:269-313`). Its duration is unbounded and unmeasured. telem never did this. It can delay the thread's wake-up, or extend a mid-command suspension (an N1 shape that would be reported with no attribution). It is absent from 7.1, 7.4 and section 11. | Either replace it with a per-file drop of the spare only (`posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)`: `sys_fadvise64_64` is in `arch/mips/kernel/scall32-o32.S:599` and `System.map`, `mm/fadvise.c:98-104`; uClibc library support UNVERIFIED, the header exists), or keep it and add it to 7.1/7.4 and section 11 with its duration timed by the worker (UHB field and EVENT `segment ready` carrying the drop time). Have the decoder flag onsets within that interval. |
| **A4-3** | RB3 / X1: RUNBOOK E1.5, E2; DESIGN 10.2 | The spare being created is a file smaller than 2,097,152 bytes, because each step `fsync`s a larger size into its directory entry. A pull during the ≈ 1 minute of each ≈ 4.9-minute segment life when a spare is being made (≈ 20 % of runs) therefore makes the raw image mandatory (E1 step 5, E2). The decoder refuses a REPORT without `--raw` ("any file that is not 2,097,152 bytes", 10.2). That needs ≥ 130 GB free on the Mac and up to 3 h, and more exposure to `dd` misuse, in normal runs. | Exempt a file that holds no RECS chunk, or the spare named in the last UHB `seg` with state 1 (creating): for example "any file that holds a RECS chunk and is not 2,097,152 bytes". RUNBOOK E1 step 5 should say one smaller file (the one being prepared) is normal. Add a Stage 3 decoder case with a pull during creation. |
| **A4-4** | D13 / 8.2 line 6, 4.4, RUNBOOK B3, B abort rule, E2 | HUD line 6 during the start-up creation (up to about 1 min at every boot) is unspecified. By 4.4 ("else `MS NO STICK`") and 8.2 (`WAIT SPARE`/`NO STICK` "always" red) it is red. B3 does not say this is normal. The abort bullet "Line 6 shows `MS NO STICK` ..." carries no "at 3:00": only the section header says "not earlier". E2 makes the raw image mandatory if line 6 "was ever red, or showed ... `WAIT SPARE`", with no start-up exception (the panel trigger has one). | Define line 6 before the first segment (for example `MS PREP nn%`, not red). Say in B3 that it is normal. Put "at 3:00" into the `MS NO STICK` bullet. Limit E2's line-6/line-7 triggers to after `SELFTEST PASS`, as was done for the panel. |
| **A4-5** | D13 / 8.3, RUNBOOK B abort rule | In an early death BTN never turns green, so the second `PSC TEST` (requested when BTN first turns green) never happens. If the operator missed the first, unannounced 5 s test during B3, the abort bullet "You never saw a `PSC TEST` band" conflicts with the early-death exception, and the runbook does not say which wins. A literal operator may abort a boot whose input already died and skip its post-death script. (The abort costs nothing under WORKFLOW, but the occurrence is lost.) | State the precedence: the early-death exception wins; write "PSC TEST not seen" and continue to D. Request the second test on a cue independent of BTN, for example when the six checks first turn green, and tell the operator in B4 to watch the band at that moment. |
| **A4-6** | Consistency (no D item) | (a) K1 says "≈ 100 after S20"; 5.4/7.1 say ≈ 130. (b) RUNBOOK examples `REC LOST 0 ...` and `CMD MED 210US` do not match the 8.2 fixed widths (`nnnn`). (c) B3's `PSC T001---` assumes run 001, but A4 allows earlier `PSCLOG` files. (d) 6.2's "collector starts at ≈ 20-40 s of uptime" is unmarked; attempt-2 red team listed it as UNVERIFIED, and with creation added it sets the D4 margin. (e) A blinking fbcon cursor may sit in the now-unwritten band (UNVERIFIED); RUNBOOK says the band is "black". (f) DESIGN.md is 1,856 lines against the brief's "under 1,800". The designer counts 1,795 by excluding section 13. | Align the figures and examples. Mark (d) UNVERIFIED in 6.2/R8 and record first-drain uptime in UHB. Mention a possible cursor in the band. The line count is for the orchestrator to note. |

---

## 8. Runbook walked as a newcomer

- **Unambiguous:** A0-A5 (the fstab trick, checksum, `df`, power source), B1, B2, B5, B6, the `POLL:RATE`-only branch, C0-C6, D0-D9 (timings add up to about 100 s, then 30 s, then 5 s, plus up to 90 + 45 s), E1, E3-E5, the timing summary.
- **Defects:** A4-3 (E1 step 5 and E2 in normal runs), A4-4 (line 6 at start-up), A4-5 (missed `PSC TEST` combined with early death), A4-6 (b, c, e).
- None of these makes the operator act wrongly in a way that loses data.
- A0's fstab method and read-only mount are UNVERIFIED macOS behaviour (R19), rehearsed in A0 with a fallback in E1.

## 9. Citations checked (all resolve and say what is claimed, except where noted)

- **r3-new:**
  - `fs/fat/inode.c:68-72`, `:73-88`, `:143-148`, `:556-610`, `:571-604`, `:1415`;
  - `fs/fat/cache.c:80-115`, `:217-274`, `:254-259`, `:295-329`, `:312-315`;
  - `fs/fat/misc.c:14-35`, `:18`, `:30-33`, `:40-72`, `:49-69`, `:78-110`;
  - `fs/fat/fatent.c:455`, `:539` (the panic in `fat_free_clusters`);
  - `fs/fat/file.c:136`, `:264`;
  - `fs/buffer.c:429-451`, `:449`, `:1378-1384`, `:2073-2146`, `:2111-2113`;
  - `fs/mpage.c:82-85`;
  - `fs/sync.c:55-76`;
  - `mm/filemap.c:282`;
  - `fs/drop_caches.c:15-46`;
  - `rc.sysinit:10`.
- **Re-checked from earlier revisions:**
  - `psp.c:32-41`, `:151`, `:218`, `:254-260`, `:348-368`, `:370-397`, `:399-407`, `:429`, `:557`, `:594-595`, `:637-654`;
  - `syscon.c:12-13`, `:61-258` (each cited line), `:355-366`;
  - `syscon.h:55-58`, `:101`, `:132-134`;
  - `joypad_psp.c:36-64`, `:195-197`, `:346-360`, `:384-411`, `:453-496`;
  - `kernel/sched.c:171-172`, `:441`, `:1507`, `:1657`, `:1659`, `:3624`, `:3626-3628`, `:3700`, `:3707`, `:3744`;
  - `include/linux/sched.h:907`;
  - `kernel/softirq.c:217`, `:225`;
  - `include/linux/hardirq.h:52-53`, `:65`;
  - `kernel/exit.c:916`;
  - `arch/mips/kernel/entry.S:39`, `:45-48`, `:61-73`;
  - `genex.S:162-169`, `:266-267`;
  - `ms_psp.c:119`, `:228-236`, `:252-282`, `:290-292`, `:312-314`, `:328-379`;
  - `mousedev.c:228`, `:659`, and `:304` (the function header of `mousedev_event`; the `SYN_REPORT` case is inside it);
  - `vc_screen.c:562-590`;
  - `kernel/printk.c:67`;
  - `fs/fat/inode.c:540-541`, `:955`, `:1311-1313`;
  - `mm/page-writeback.c:80`, `:433`, `:453`, `:469-472`, `:585`;
  - `init/main.c:628`;
  - `highmem.h:49-52`;
  - `vt.c:174`;
  - `telem.c:52-57`, `:183`, `:265-273`, `:299-306`, `:373`, `:410-415`.
- **Vanilla identity of `fs/fat`, `fs/vfat`, `buffer.c`, `mpage.c` and `sync.c`:** verified with `diff`.

## 10. Attacks attempted that found nothing

- **IF5 through the creation path:**
  - a FAT write failure inside a step;
  - a read error during allocation;
  - a short `write`;
  - pdflush writing an abandoned spare's dirty inode or pages;
  - the shared FAT sector between the active segment and the spare;
  - error attribution swapped between the tick flush and the creation step.
  All end in an in-place retry or an abandon. None reaches `fat_fs_panic` without on-disk damage.
- **A takeover turning a SIGTERM into an I/O error through `down_interruptible`:** not possible, because the semaphore is uncontended and the fast path does not check signals.
- **The HUD overwriting the panel:** not possible, because rows 176-271 are never written.
- **Name exhaustion under error bursts:** ≥ 10 s per attempt and 999 names, so more than 2.7 h.
- **The S ring overflowing at start-up:** about 800 records against 4,096.
- **Struct strings and the stats word map:** every offset checked.
- **The `drop_caches` sysctl missing in this build:** it is present (`CONFIG_PROC_SYSCTL=y`, `kernel/sysctl.c:749`, `drop_pagecache` in `System.map`).
- **Every budget headline:** reproduces exactly (section 3).
