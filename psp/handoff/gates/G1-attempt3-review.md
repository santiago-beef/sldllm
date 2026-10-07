# Gate G1, attempt 3: design review

| | |
|---|---|
| Gate | G1 (design review checklist D1-D20) |
| Attempt | 3 |
| Artifact | `design/DESIGN.md` (3,006 lines, revision 2, 2026-10-01 00:31) and `design/RUNBOOK.md` (380 lines, revision 2, 2026-10-01 00:29) |
| Reviewer | G1 design reviewer, attempt 3. Fresh context. Not the designer. |
| Inputs read in full | DOSSIER.md (including 9.1-9.7), WORKFLOW.md, recon/syscon.md, recon/input.md, recon/build.md, gates/LOG.md, DESIGN.md, RUNBOOK.md. I also read the attempt-2 review for its closing conditions. |
| Source used | `/home/ubuntu/psp/build/linux`, `/home/ubuntu/psp/extract/root2`, `/home/ubuntu/psp/telem/` and `telem/logs-from-stick/`, all read only. I wrote nothing except this file. |
| **Verdict** | **PASS**: 0 blocking FAILs, 0 non-blocking FAILs. Five advisory findings stay open (section 6). G3 R1 requires them to be closed before release. |

## Why PASS

All twenty checklist items pass on the evidence. The blocking failure from
attempt 2 (F-A / D6) is fixed, and it is fixed in two independent ways:

- **Option (a).** The worker no longer draws rows 176-271 while the
  kernel's paint condition holds, or within 250 ticks of a paint
  (4.3 step 8, 2.10).
- **Option (b).** The pull check D8 (b) now also needs the HUD's `MS` line
  to show no red, no `CATCHUP`, and `DUR` below 3 s.

I tried to make D8 (b) pass while the post-death script was not yet on the
stick, and could not:

- a resumed stall;
- a promoted standby;
- a live write-error run;
- a first-paint race;
- a condition that starts inside the 5 s watch;
- `ctl` write failures.

Section 4 traces each one.

I re-ran every number in the budget. They are right to the byte
(section 3). Every r2-new citation resolves and says what is claimed, and
so do the r1 citations I sampled (section 4).

The open findings all concern the **2:00 self-test decision and the HUD
fields the runbook relies on**:

- **N-1.** The runbook gates the TRIANGLE press on POLL being green, so the
  new `POLL:RATE`-only exception can never be reached.
- **N-2.** The specified top HUD line cannot physically hold the check
  names the operator must read.
- **N-3.** `IN` and `DELIV` are used as death cues but are never defined.

None of these defeats D13's literal requirement: `SELFTEST PASS` and `TRI`
both fit on screen. But the early-death path is not rare (dossier 9.6:
input was already dead at app start in 2 of 5 sessions). So these must be
closed before G3.

---

## 1. Checklist

| ID | B | Result | One-line reason |
|---|---|---|---|
| D1 | B | PASS | Every `Syscon_cmd` call in every context, every poll, every Nop with its interrupted context, every in-flight tick (capped, with the excess counted), and every MS segment are streamed. Whole-run stats. No hypothesis is privileged. |
| D2 | B | PASS | Independent derivation in section 2. Every row separates, except two declared classes: "H8 in an unread register" and "operator did not press" against H6. Advisory N-4 on the literal `rx[2]`. |
| D3 | B | PASS | SC keeps `rx[16]`, `cmd`, `txlen`, `ret` (s16), `nwords`, `retries` (1.2, offsets 18-23 and 48). |
| D4 | B | PASS | No trigger. P and POLL rings hold 114.7 s, the others longer. Capped catch-up drains a full ring in at most about 24-33 s. Rewind on error loses nothing in a burst shorter than the ring span. |
| D5 | B | PASS | 3.3: "None. Nothing freezes." `DEAD?` controls nothing (8.4). |
| D6 | B | PASS | Panel rows are left to the kernel (4.3 step 8, 2.10). The two-display pull check is in RUNBOOK D8 (b). Loss is ≤ 4 s before a passing check, inside the 30 s hands-off wait. Otherwise the kernel shows the loss as `DUR` (4.5). F-A closed. |
| D7 | B | PASS | `pscol&` after `pspmd -s&` (`rc.sysinit:17-19` verified). The supervisor is written in C. Nothing is typed. |
| D8 | B | PASS | Explicit `psc_wd_ctx` at the only two `psp_pacify_watchdog` call sites (`psp.c:379,557`, verified). `wn`, `W.p_head`, `t_busy`, I samples and `lc_*` record an interrupt during a thread command. |
| D9 | B | PASS | One writer per ring and per structure, including the r2 `wk_*` (scheduler hooks with IRQs off), `lc_nest_id`, `seg_cur` and the guard words. `seq` invalidate/publish. Bracketed multi-word reads. |
| D10 | B | PASS | 0 instructions in S5..S20 (G2-checkable, 2.1/7.2). About 0.8 µs per command outside the window. The scheduler hooks add about 0.2 µs before the loop top. The panel's 0.2-1 ms is stated and counted, and never falls on a watchdog tick. |
| D11 | B | PASS | No new MMIO read or write. Captures reuse loads the code already makes. The panel writes VRAM RAM only. |
| D12 | B | PASS | Recomputed (section 3): 8,154 B/s payload, 8,904 B/s on the stick, 8.0 / 16.0 MB in 15 / 30 min. One `printk` at init. The kernel log is not used for history. |
| D13 | B | PASS | Nine checks, abort at 2:00, early-death exception, `POLL:RATE` window ≥ 5 s. Advisory N-1, N-2, N-3 and N-5 concern the readability and reachability of the 2:00 decision. |
| D14 | B | PASS | `ret` s16; per-command histograms (−2/−3/−4/−5 distinct); `drain` 0xFFFF and `ack_polls` 1,000,001 sentinels. |
| D15 |   | PASS | `jp_loop`, `jp_r3/r4/r5`, `ri_branch`, `pi_flags`, `push_*`, `mouse_flags`, `sig`, `jp_listsem_fail`, `jp_push_eintr`, `jp_sigpending`, stage codes. |
| D16 |   | PASS | `(localTick, Count)` stamps. The watchdog fires at tick ≡ 0 mod 1250 by construction (`psp.c:372-379`, verified). `ts_read` retries a torn read. |
| D17 |   | PASS | D1-D7 plus D7a name each button, its duration and its raw bit. C0 provides the healthy reference. P6 photographs `RAW`. |
| D18 |   | PASS | 7.7: objdump FP-register grep, FP-mnemonic grep, `nm` grep and `flthdr` (method of `telem/cbuild.sh:9`, verified). |
| D19 |   | PASS | `uClinux_TRACE`. RUNBOOK A1 forbids the three existing names. Data goes only to `/ms0/PSCLOG`. |
| D20 |   | PASS | Every 10.3 format string matches section 1 offset for offset (`struct.calcsize` re-run). F-B fixes verified. The flag-bit sweep holds. |

Blocking FAILs: 0. Non-blocking FAILs: 0.

### Evidence per item (attacks attempted are listed with each)

**D1 PASS.**
- 3.2 streams the following at full resolution:
  - every `Syscon_cmd` call (P, W, M rings);
  - every loop iteration (POLL);
  - every Nop with its interrupted frame (W, 512 B);
  - every in-flight tick (I, capped at 4 per command, with `i_suppressed` counting the rest, plus the uncapped `lc_*`);
  - every MS segment (S).
- Stats (1.8) carry the whole-run counters.
- Classification is done after the run (10.7), reported as trigger / state / H8 flags, with raw dumps for H0.
- Attack: a death shape that only shows in a counter not in the stats.
  - Stage-localised shapes have stage codes (2.5) and W `jp_stage` every 5 s.
  - Upper layers have fops/vcs/mousedev counters (2.6).
  - None was found.

**D2 PASS.** Section 2.

**D3 PASS.**
- 1.2: `cmd` @18, `txlen` @19, `ret` s16 @20, `nwords` @22 (`(ptr − rx_buf)/2`), `retries` @23, `rx[16]` @48.
- `nwords` is taken after S20 (`syscon.c:222`) and before `ptr` is reused at `:235` (verified).
- The prefill `syscon.c:92-93` is kept in `rx`.
- The W and M records reuse the SC layout.

**D4 PASS.**
- Ring spans (recomputed):
  - P: 4096 / 35.71 = 114.7 s;
  - POLL: 2048 / 17.86 = 114.7 s;
  - W: 1,280 s;
  - I: 455 s (80 s in the H1 shape);
  - S: ≥ 154 s.
- The collector starts from `rc.sysinit` (about 20-40 s of uptime), so a death at 17 s is still in the rings.
- Catch-up is capped. My worst case for a full P ring:
  - capacity ≥ 48 records per 0.23 s for every tick length up to 0.92 s, and capacity / T ≥ 208 records/s;
  - net drain ≥ 172 records/s;
  - so ≤ 24 s.
  - The design's 33 s (m = 1 at T = 0.3 s) is a conservative over-estimate.
- Attack: a write-error burst at 15 min.
  - Rewind to `durable_next` plus in-place retry (4.6).
  - Nothing is lost if the burst is shorter than 114.7 s.
  - Stage 3 tests 60 s, 130 s and sporadic bursts (8.5).

**D5 PASS.** No trigger and no freeze. The I cap is the only reduction, and it is counted.

**D6 PASS.** Section 4.1 traces every path.
- The worst-case loss stated for a passing check is 4 s (4.5 case 1), against a 30 s hands-off wait (RUNBOOK D8).
- When the check does not pass by 90 s (+45 s while `CATCHUP` shows), the loss equals the `DUR` that the kernel itself shows. The operator records it, and photographs keep the kernel's view.
- This is the same residual accepted in attempts 1 and 2. It needs a collector failure that the standby and the takeover did not cure.

**D7 PASS.**
- `extract/root2/etc/rc.sysinit:17-19` is the `pspmd -s&` block.
- `/dev/null` and `/usr/bin` exist in the initramfs.
- Busybox has no `sleep` link (`bin/` and `usr/bin/` listed). `grep -c sleep bin/busybox` = 0.

**D8 PASS.**
- `psp.c:379` and `:557` are the only callers (`:97` is the prototype, `:383` the definition; grep verified).
- The Nop runs in `psp_watchdog_tick` with IE off before `do_IRQ` (`psp.c:348-368`, verified), so the flag window is exact.
- An interrupt during a thread command is recorded:
  - by `wn` in the P record;
  - by `t_busy`/`p_head`/`epc`/`ext_flags` in W;
  - by I samples on ordinary ticks;
  - by `lc_*` when the thread is suspended.
- Nested ticks are excluded from `lc` by `preempt_count() & (SOFTIRQ_MASK|HARDIRQ_MASK)`.
  - `__do_softirq` raises the softirq count (`kernel/softirq.c:217`) before `local_irq_enable` (`:225`), verified.
  - Masks are at `include/linux/hardirq.h:52-53`.

**D9 PASS.**
- 3.4 lists one writer for each structure.
- Attacks on the r2 additions:
  - **Hook W/S against T2.** All run with IRQs off: `task_rq_lock` → `local_irq_save` at `kernel/sched.c:441`, `spin_lock_irq` at `:3624`, and T2 in the hard IRQ. On a uniprocessor they cannot interleave.
  - **`do_exit` clearing `psc_jp_task` against T2c dereferencing it.** T2c loads the pointer once with IRQs off, so it cannot be split by `do_exit`.
  - **`durable_*` / `seg_cur` with two collectors after a takeover.** The old worker dies on the pending SIGTERM at its next syscall return, before its `ctl` write. The standby writes only after `GO`.
- No defect found.

**D10 PASS.**
- 2.1 A3 and 7.2 state the window rule.
- 7.1 lists every new delay:
  - before S5: about 0.16 µs;
  - after S20: about 0.65 µs;
  - Nop extension: about 1.6 µs;
  - scheduler hooks: about 0.2 µs at the loop top (2.11);
  - panel: 0.2-1 ms, only in the occasions listed in 2.10.
- The panel paint can stretch a command that straddles a painting tick. This is stated, counted (`panel_paints`, `panel_last_tick`) and flagged by the decoder (onset within 1 s after a paint).
- `kernel/sched.c` hook sites verified: `:1657` `success = 1;`, `:1659` `out_running:`, `:3700` `if (likely(prev != next))`, `:3707` `context_switch`.

**D11 PASS.**
- 7.1: "MMIO accesses: None added, none removed".
- The LED hook keeps the single load and store of `psp.c:401,406` (`PSP_GPIO_SET |= mask_`, verified).
- The panel writes `PSP_VRAM_BASE` = `0x04000000 + CONFIG_PSP_ADDRESS_BASE` (`include/asm-mips/psp.h:36`, `.config:51` = `0x80000000`), and calls `pspClearDcache` (`ipl_sdk/cache.c:22-37`), the same as `pspfb_sync` (`pspfb.c:348-352`).

**D12 PASS.** Section 3.

**D13 PASS, with advisory findings.**
- 8.2 checks: KRN, POLL (now over ≥ 5 s, P ≥ 20/s and POLL ≥ 10/s, against healthy 14.7-17.86 polls/s and ≤ 6.4 polls/s in the −4 shape), WDOG, CTX, STICK, REC, PANEL, SUP and BTN.
- BTN needs P08 `rx[3]` bit 4 to clear and then set again (TRIANGLE `0x10` at `joypad_psp.c:40` → `rx[3]` via `syscon.c:363`, verified).
- Abort at 2:00; early-death exception; decision time fixed (8.3, RUNBOOK B).
- The literal D13 requirement holds: `SELFTEST PASS` (13 chars) and the `RAW … TRI` line (25 chars) fit on screen.
- Defects in the 2:00 decision path are findings N-1, N-2, N-3 and N-5.

**D14 PASS.**
- `ret` is s16, so −2, −3, −4 and −5 are all representable.
- `hist` index 3-6 per command and per context (1.8 words 35-66).
- `retries` = 16 for −5 (`syscon.c:253-254`, verified).

**D15 PASS.** 1.5, 1.8 words 67-116, 2.5.

**D16 PASS.**
- `psp.c:372-379` verified. `localTick++` then the Nop when `localTick − lastTick ≥ 1250`, both starting at 0. So the Nop runs at tick 1250·k.
- The ordering fix inside the handler holds, because Count is reset at `:351-356` before `:359`.

**D17 PASS.**
- RUNBOOK D1-D7a:
  - L clicks (`rx[4]` b1);
  - TRIANGLE ×2 (`rx[3]` b4);
  - D-pad RIGHT (`rx[3]` b1);
  - VOL+ (`rx[5]` b0);
  - stick right and up (`rx[7]`/`rx[8]`);
  - HOLD (`rx[4]` b5);
  - SELECT tap.
- Each has a duration. P6 photographs `RAW`.
- C0 runs the same steps healthy. Bit map verified at `joypad_psp.c:36-58`.

**D18 PASS.** 7.7 repeats `telem/cbuild.sh:9` and adds a mnemonic grep, an `nm` grep and a `flthdr` stack check.

**D19 PASS.** RUNBOOK A1/A2. The deploy folder holds exactly four files. `pspboot.conf` lines match dossier 9.7.

**D20 PASS.**
- `struct.calcsize`:
  - SC 80, WEXT 432, I 32, POLL 40, S 48, STATS 1024;
  - chunk header 20, block 8, UHB 80, FILEHDR fixed 40, SELFTEST 8, CTL 32.
- I mapped each format string to its section 1 table offset by offset:
  - SC: `ack_polls` @24, `ctx` @38, `rx` @48, `lc_epc` @64, `led_or` @72, `ck_calc` @78, `ck_rx` @79;
  - WEXT: `t_busy` @112, `m_head` @116, `ms_ip_*` @136/140, `gpr` @144, `stk` @272, `lc_*` @400, `lc_r` @432, `ms_ip_pid` @496, `durable_tick` @500, `lc_n` @508, `cur_pc_hi` @510;
  - POLL: `wk_delay` @36, `wk_cls` @38, `wk_share` @39;
  - S: `rd_*` @32-47.
- All are equal.
- Flag bits:
  - UHB b12 catch-up in 4.3 = 10.2 = 10.5;
  - b16-b20 equal across 4.2, 4.4, 4.3, 4.6 and 8.2;
  - self-test order equal in UHB b1-b9, SELFTEST b0-b8 and the HUD.
- 1.7 now says 80 bytes. `recsize_div4` POLL = 10. FILEHDR 20 + 40 + 1024 + 256 = 1,340.
- No stale `b11`, `64-byte`, `S??`, `durable_seq`, `PSC2` or `43,972` outside sections 12-14 (grep).

---

## 2. D2: independent derivation from the record format

I derived the expected field contents from section 1 and the source alone,
without the design's matrix. "P08" means a P record with `cmd` 0x08.

| Row | What the recorded fields would contain | Confusable with | Separating fields |
|---|---|---|---|
| H0 | No rule below fits. The full P/POLL/W/I/S/M/stats/KMSG/PROCS stream survives. | anything | Raw windows (D3) |
| H1 | From onset, every P33/P08 has `ret` −4 (`ack_polls` = 1,000,001, `nwords` 0, `rx` all ff), or −3 (`drain` 0xFFFF). `dtick` ≥ ~12 per command (≥ 50 ms, recon §1.5, UNVERIFIED). Each command has 4 I records with EPC at S14 (or S8), then `i_suppressed` rises. POLL `ri_branch` 3 and `period` ≥ ~39 ticks. If the Nop also gets no ACK: W `ret` −4, `c_pre_max` and `long_ticks` jump (IE off for ≥ 50 ms). In the 9.5 variant, W `ret` ≥ 0. | One −4 from H4 at P2-P5a. H8 in an unread register as the cause. N9. | Persistence. W `ret` (pure against variant). N9 has no P records and `t_busy` stuck. The H8 cause in unread registers is a declared blind spot. |
| H2 | P08 `ret` 0, `nwords` ≥ 1, received bytes 00 (`rx[0..2·nwords−1]` = 00, the rest ff). POLL `ri_branch` 4. `jp_r4` +1 per poll. No mouse calls. | The real HOLD switch. N11. | A real HOLD frame has `rx[0]` = status, valid checksum, and only `rx[4]` b5 = 0. C0/D7 record the real switch. |
| H3 | P08 `ret` 0, `nwords` 0, `rx` all ff, finite `ack_polls`. POLL `ri_branch` 5. In mouse mode, `mouse_flags` b3 with `dx` = `dy` = +16 **every poll** (`joypad_psp.c:612-613,690`, mouse path not deduped). `pi_flags` b1 dedupe after the first. | One E3 from H4 at P3/P4/P5a/P5b. N2b when the stolen reply is short (it also yields `~key` = 0 and drift). | Persistence and `wn`. N2b has `nwords` ≥ 1, `ret` > 0 and `rx[2]` = previous `cmd`. |
| H4 | A WT record (tick ≡ 0 mod 1250) with `t_busy` b0. P record `seq` = W `p_head` with `wn` ≥ 1. Step from W `epc` (b4 set, b7 clear) or W `lc_epc` (b5) through `epcmap`. W's own `ack_polls`, `drain`, `drain_last` and `rx` show what the Nop took. Onset in that poll or the next. | Coincidence. N8 (`pdflush` at 5 s). H10. P4 against P5a. | The benign per-step rate from every W. `kupd_last_tick` series. S overlap for H10. P4/P5a may stay "P4 or P5a" (R12, hardware unknown). |
| H5 | Persistent `ret` −5 (`retries` 16, `rx[2]` ∈ {80, 81}) or −2: `rx[1]` < 3, a recomputable mismatch, or `rx[1]` ≥ 16 with `ck_calc`/`ck_rx`. | One −2 from H4 at P2/P6. | Persistence and the `rx` pattern. |
| H6 | P08 `ret` > 0, checksum valid, `rx[3..8]` constant through D1-D7 while C0 showed them change. Dedupe every poll. | H7. "Operator not pressing". N2b. | H7: `rx` follows. Not pressing: photos P6 and notes only (declared). N2b: `rx[2]` = previous `cmd`. **The H6/N2b split rests on `rx[2]` echoing the command, which is UNVERIFIED hardware semantics (N-4).** |
| H7 | `rx` follows the script after onset, but delivery stops at a stage: push/listsem failures or `nqueues` 0; `jp_wake` without `fop_read_ret`; `mouse_reports`/`md_notify_calls` without `md_read_ret` beyond the collector's 3-byte reads (= `mouse_pkts_total`, `telem.c:268`); `vcs_putchar` flat; POLL `sig`. | H9. H6. N6. N10. | P/POLL keep coming (not H9). `rx` changes (not H6). N10 has `pi_flags` b3 and later `mouse_flags` b0 = 0. |
| H8 | Captured `gpio_in`, `spi_st9`, `spi_sttx`, `drain`, `drain_last`, `ack_polls` and LED read-back OR/AND leave the template. If there is no template, they are compared with the WB/M/WT references. | H1, H3, H5 (behaviour). H4, H10 (cause). | Reported as flags beside the state. Registers the code never reads are not observed (dossier 9.1, declared). |
| H9 | P/POLL stop. W continues every 5 s with `jp_loop` fixed and `jp_stage` 11 (`jp_stage_arg` = Q) or 9. Stats: `jp_state` 1, `qfree_stage` 2 with `qfree_queue` = Q, `fop_release` rose. PROCS: `psposk2` gone or exiting. | N4 (stage 7/8). N5 (stage 15/16, `jp_state` 0). N9 (`t_busy` set). Starvation (`jp_state` 0, `wait_*` rising). | Stage code plus `qfree_stage` naming the same Q. |
| H10 | P record with `ms_delta` > 0 and `preempt_delta` > 0, `lc_epc` in S5..S20, `led_or & ~0xC0` ≠ 0. Overlapping S record (`flags` b4/b5) with `rd_*_or & ~0xC0` ≠ 0. `led_pid` names the task. Onset need not be at a 1250 boundary. | H4. N1. H10b. | W against S. N1 has `ms_delta` = 0. H10b has no command in flight. |

**Rows confusable in the data alone:**

1. H6 against "operator did not press". Separated only by the operator's notes and photograph P6 (declared in the design).
2. H8 in a register the code never reads, against plain H1/H3/H5. Declared, as dossier 9.1 requires.
3. P4 against P5a inside H4. A sub-row, and a hardware unknown (R12).
4. H6 against N2b, but only if the healthy GetCtrl2 reply's `rx[2]` is not 0x08. In that case both literal rules miss and the death falls to H0 with full raw data. This would be missed, not misclassified (N-4).

Every other pair separates on recorded fields. D2 PASSES.

---

## 3. Budget arithmetic (D12), recomputed

Method: Python with the 10.3 format strings, 17.857 polls/s (250/14),
35.714 P/s, 4.348 ticks/s (0.23 s), I at 9/s, and S solved to a fixed
point.

| Quantity | Design | Mine |
|---|---|---|
| Plain / STATS / STATS+PROCS flush | 1,393 / 2,437 / 4,207 → 1,536 / 2,560 / 4,608 | 1,393.2 / 2,437.2 / 4,207.2 → same |
| Data sectors per flush | 4.0 | 4.00 |
| Stick bytes | 8,904 B/s | 8,904 B/s |
| Payload | 8,154 B/s | 8,154.2 B/s |
| S rate (upper bound) | 26.6/s | 26.63/s |
| LED RMW | ≈ 53/s (2.0× telem's 26) | 53.3/s; telem 3 × 4.35 × 2 = 26.1 |
| 15 / 30 min | 8.0 / 16.0 MB | 8.01 / 16.03 MB |
| Rings | 873,472 B | 327,680 + 81,920 + 131,072 + 131,072 + 196,608 + 5,120 = 873,472 |
| Spans P / POLL / S / I / I (H1) | 114.7 / 114.7 / 154 / 455 / 80 s | 114.69 / 114.69 / 153.98 / 455.1 / 80.0 |
| Cap unit, max RECS, max flush | 11,072 / 44,356 / 49,140 → 49,152 | same |
| FILEHDR flush | 1,340 + PAD → 1,536 | 20 + 40 + 1024 + 256 = 1,340; + 20 + 176 = 1,536 |
| Catch-up of a full P ring | 14.4 s (m = 2) / 33.0 s (m = 1, T = 0.3) | 14.4 / 32.96 (my true worst case is ≤ 24 s; 33 s is conservative) |
| Backlog after takeover (≈ 33 s) | ≈ 9.2-10 s | 1,179 records, 9.5 s |
| H1 poll rate | ≤ 6.4/s | 1/0.156 = 6.41 polls/s, 12.8 P/s |
| `wk_delay` saturation | 1.19 ticks | 65535 × 16 / 883651 = 1.187 |
| `acc` u32 saturation | ≈ 19 s | 2³² / 220,912,896 = 19.4 s |
| Kernel memory | ≈ 876 KB (4.2 % of 20.8 MB) | 873,472 + ≈ 2.6 KB; 4.2 % |

There is one cosmetic inconsistency. 4.5 says "about 10 s" for the
backlog after a takeover, and 13.5 says 9.2 s. Both are right for 33 s and
32 s respectively. It is not a finding.

---

## 4. Specific verifications

### 4.1 D6: attacks on the pull check (F-A closure)

The kernel paints when `proc_opens > 0` and any of the following holds
(2.3 T2d):

- `now − durable_tick > 750`;
- `now − last_reader_tick > 750`;
- a test is pending.

The worker spares rows 176-271 when the same three conditions hold, or when
`now − panel_last_tick ≤ 250` (4.3 step 8, stats 7, 128, 5, 139, 140, 136,
138, all verified against 1.8). The conditions are complementary, so:

- no state leaves a stale panel on screen permanently;
- no state lets the worker draw over a condition that persists.

| Path | Kernel panel during the 5 s watch | HUD `MS` line | D8 (b) passes? |
|---|---|---|---|
| Stall, then resume and catch-up (15-33 s) | Up, refreshed each second, until ≤ 1.3 s after `durable_tick` is within 3 s | `CATCHUP`, `DUR` ≥ 3 | No, until durable |
| Standby promoted (new segment, catch-up from `durable_next`) | As above | As above | No, until durable |
| Live write-error run | Up after 3 s | Red for 10 s after the last error | No |
| Error run shorter than 3 s | Not painted | Red for 10 s | No for 10 s, then durable |
| First-paint race (2.10) | Missing ≤ ~2 s after the condition starts | `DUR` ≥ 3 | No (HUD catches it) |
| Condition starts in the last 2 s of the watch, worker stalls | Maybe not yet painted | Heartbeat changed earlier in the window | **Yes.** But durability up to (window end − 4 s) is still guaranteed by the kernel's checks earlier in the window, and the script ended ≥ 30 s before. |
| `ctl` write fails | Kernel `durable_tick` stale → panel | `DUR` from stats grows | No |
| Worker reads but the stats read fails | Kernel independent | HUD may be stale | Panel decides |

The loss bound "≤ 4 s before the check" holds on every path. **F-A is
CLOSED:**

- option (a): 4.3 step 8, 2.10;
- option (b): RUNBOOK D8 (b), D8 (c) exit, C4 step 3;
- consistency: 4.5 case 1/2, 4.6, 2.10 list (a)-(e), RUNBOOK "Two displays", B3, the timing summary;
- the Stage 3 test row (8.5 "Panel not overwritten").

Attempt-1 **F1 is CLOSED.** It was superseded by F-A, and its condition
(a), a live writer's reading, is met by D8 (b): heartbeat, `DUR` < 3, no
`CATCHUP`.

Side observations, not findings:

- pspfb has no `fb_blank` (`drivers/video/pspfb.c:64-76` ops list). fbcon's
  blank is therefore a one-off clear that the HUD and the panel repaint. R17
  can be downgraded.
- A kernel `printk` such as "lost page write" (`fs/buffer.c:443-445`) is
  drawn by fbcon over the HUD and the panel during an error run. Both are
  repainted (HUD ≤ 0.23 s, panel ≤ 1 s), and the pull check is conservative
  in that state.

### 4.2 Citations checked (all resolve and say what is claimed unless noted)

**r2-new citations:**

- `kernel/sched.c`: `:1507`, `:1657`, `:1659`, `:441`, `:171-172`, `:3583`, `:3624`, `:3626`, `:3700`, `:3707`, `:3744`, `:1669`, `:1676`, `:3817`, `:1949`.
- `kernel/softirq.c:217,225`.
- `include/linux/hardirq.h:52-53,65`.
- `arch/mips/kernel/entry.S`: `:39`, `:45-48` (PSP uses `ST0_CU0`), `:61-73`.
- `genex.S:166-167,266-267`.
- `kernel/exit.c:916` (`tsk->flags |= PF_EXITING`).
- `drivers/input/mousedev.c`: `:432`, `:439-440`, `:455`, `:659`.
- `arch/mips/kernel/process.c:81-83`.
- `include/asm-mips/uaccess.h:58,107-113`.
- `include/asm-mips/ipl_sdk/syscon.h:55-58`. This is an author comment, see N-4.
- `fs/fat/inode.c:126-129,202`.
- `fs/mpage.c:488-535`.
- `drivers/block/ms_psp.c:252-265`.
- `fs/buffer.c:2593-2621`.

**r1 citations I re-checked:**

- `psp.c`: `:32-39`, `:96-97`, `:348-368`, `:370-392`, `:399-407`, `:429`, `:557`, `:594-595`, `:637-654`.
- `syscon.c`, 45 cited lines.
- `joypad_psp.c`: `:36-64`, `:384-411`, `:453-495`, `:504-539`, `:609-658`, `:686-690`.
- `ms_psp.c`: `:38`, `:92`, `:119`, `:131`, `:254`, `:260`, `:264`, `:290-322`, `:328-378`.
- `memstk.c:59-65,167-169,174-181`.
- `fs/sync.c:55-76`.
- `fs/fat/file.c:136`.
- `fs/fat/misc.c:40-72`.
- `fs/fat/inode.c`: `:453-459`, `:540-541`, `:955`, `:1311-1313`.
- `fs/fat/fatent.c`: `:347`, `:434`, `:479`, `:500`, `:548`, `:586-610`.
- `fs/buffer.c:429-450`.
- `fs/super.c:401-408`.
- `mm/page-writeback.c:80,433-473,585`.
- `init/main.c:628`.
- `fs/binfmt_flat.c:575-596`.
- `mm/nommu.c:745`.
- `fs/proc/kmsg.c:36`.
- `fs/proc/array.c:167,275-279,413`.
- `kernel/sysctl.c:749`.
- `fs/proc/proc_misc.c:707`.
- `kernel/timer.c:988-990`.
- `include/linux/sched.h:907`.
- `mipsregs.h:789,810`.
- `thread_info.h:37`.
- `ptrace.h:37`.
- `head.S:182-187`.
- `.config:51,64,109,163`.
- `kernel/printk.c:67`.
- `vc_screen.c:562-590`.
- `psp.h:36`.
- `pspfb.c:28-39,348-352`.
- `fb_sys_fops.c:89-92`.
- `cache.c:22-37`.
- `include/linux/jiffies.h:137`.
- `scripts/gen_initramfs_list.sh:287-290`.
- `drivers/input/input.c:651-663`.
- `telem.c`: `:29-30`, `:54`, `:56`, `:143-151`, `:235-245`, `:249-274`, `:279`, `:293`, `:299-306`, `:326`, `:357`, `:367-373`, `:415`.
- `telem/logs-from-stick/kmsg.txt`: 1,606 B; "Adding disk ms0 118999M [0000003f-0e86bfc1]" = 243,711,875 sectors; no "Unknown IRQ"; "FPU Emulator v1.5" present.

**Claims that overreach their citation (advisory):**

- **8.2 PANEL** says the pixel read-back proves the D-cache write-back. `fb_sys_read` reads the cached `screen_base` (`pspfb.c:24,396`, `PSP_VRAM_BASE` in kseg0) after `fb_sync` (`fb_sys_fops.c:41-45`). So the read-back proves only that the paint routine ran. The visible proof is the operator seeing `PSC TEST` (N-5).
- **H6 / N2b** treat `rx[2]` = command as fact. `syscon.h:55-58` is a reverse-engineering comment (N-4).

### 4.3 Runbook executed as a newcomer

I walked A1→E3 as an operator who has never seen the code.

**Unambiguous:**

- A1-A5: checksum mandatory, `df`, AC rule;
- B1, B2 (a missed P1 is not an abort; F-H closed);
- B5, B6, C0-C6;
- D0-D9, with timings that add up to about 100 s + 30 s + 5 s;
- E1-E3;
- the never-press table, apart from one omission (N-1).

**Defects:**

- **B4 gating (N-1).** B4 fires only "When all except BTN are green". With POLL red, a literal operator never holds TRIANGLE, so BTN stays red. At 2:00 the "exception to the exception" needs "the only red item is POLL showing `POLL:RATE` … and BTN is green". It is unreachable, and the operator goes to D with a live device.
  - A concrete live state that produces `POLL:RATE` alone: a persistently failing 0x33 (`AStickPower`). The driver discards its result (`joypad_psp.c:486`), so it is invisible in the baseline. Each poll then takes ≥ 50 ms + 56 ms → ≤ 9.4 polls/s < 10, while `GetCtrl2` works.
- **Top-line overflow (N-2).** The HUD uses telem's 6×s advance (`telem.c:183`): 12 px per character at scale 2. The heartbeat block sits at x = 428-467, y = 8-37 (`telem.c:373`). Lines 1-2 therefore have about 35 usable columns.
  - Line 1 must show `PSC T0010001` plus `KRN POLL WDOG CTX STICK REC PANEL SUP BTN`: 54 characters, 59 with `POLL:RATE`.
  - The 8.2 example lines 1 and 4 are 43 and 41 characters against the stated 40-column grid.
  - There is no spare text line: 10 lines fill rows 8-167, and rows 176-271 belong to the panel.
  - RUNBOOK B3, B4 and the 2:00 rule require the operator to read each check's colour and the POLL condition text.
- **`IN` / `DELIV` (N-3).** These are the operator's death cues (C5) and the `POLL:RATE` test. They are not defined anywhere in DESIGN.md: only the example line 6 and a phrase in 13.1.

---

## 5. Status of previous findings

| Finding | Status | Evidence |
|---|---|---|
| F-A / D6 | **CLOSED** | Section 4.1. All three closing conditions met. |
| F-B / D20 | **CLOSED** | 4.3 step 1 b12; 1.7 80 bytes; 12.1 row marked; my own sweep (D20) found no mismatch. |
| F-C | **CLOSED** | 4.3 step 7 and bounds; 10.2; FILEHDR alone at offset 0, 1,536 B, `write` + `fsync`; Stage 3 row "New-segment flush during a full-ring catch-up". |
| F-D | **CLOSED** | `T<rrr><iiii>.BIN` (8.3); monotonic from `seg_cur` + 1, `EEXIST` → next (≤ 16 per tick); in-place retry; rotation after 3 failures, ≤ 1 per 5 s; `open`/ENOSPC ≤ 1 entry per 5 s; no stop at 9999; Stage 3 counts segments. |
| F-E (advisory) | **NOT CLOSED** | The ≥ 5 s window and the 2:00 decision are fixed. The live-device escape is unreachable because of the B4 gating. Superseded by N-1. |
| F-F | **CLOSED** | 1.6, 3.1, 5.1 upper bound with the `mpage` path; Stage 3 accepts S ≤ sectors and Σ `nsect` = sectors. |
| F-G | **CLOSED** | Row H10 and 10.7 step 5 fire at S5..S20 with the step window. Refutation still needs S13..S20, and the reason is given. |
| F-H | **CLOSED** | RUNBOOK B2; 2.8; 8.1. |
| Attempt-1 F1 | **CLOSED** | Via F-A. |
| Attempt-1 F2-F15 | **remain CLOSED** | Re-checked against r2. F2: bounds recomputed. F5: exception unchanged for H1/H3/H5/H9 shapes. F9: PROCS unchanged. F13: A2 placeholder present. |

---

## 6. Open findings (advisory; must be closed before G3 R1)

| # | Item | Problem | What would close it |
|---|---|---|---|
| N-1 | D13 / RUNBOOK B4, B abort rule; supersedes F-E | B4 holds TRIANGLE only "When all except BTN are green". With `POLL:RATE` red, BTN is never tried, so "the only red item is POLL … and BTN is green" cannot be met and a live device goes to D. A persistently failing 0x33 (result discarded, `joypad_psp.c:486`) gives exactly this state: ≤ 9.4 polls/s while `GetCtrl2` works. The never-press table also omits the exception's SELECT tap. | (1) RUNBOOK B4 and 8.3: "When KRN, WDOG, CTX, STICK, REC, PANEL and SUP are green, hold TRIANGLE for 2 s whatever POLL shows; if BTN does not turn green, repeat, up to three times". (2) The never-press SELECT row lists the B abort-rule tap. (3) G3 R4's read-through includes the `POLL:RATE`-only branch. |
| N-2 | D13 / 8.2 HUD layout | Line 1 must hold 54-59 characters (segment name plus nine check names, or `POLL:RATE`) in about 35 usable columns beside the heartbeat block (12 px advance, block at x = 428-467, y = 8-37, `telem.c:183,373`). The 8.2 example lines 1 and 4 (43 and 41 characters) exceed the stated 40 columns. Rows 168-271 are not available. The 2:00 decision depends on reading each check. | 8.2 gives a self-test status layout that fits: for example, lines 1-2 during the self-test, each ≤ 35 characters left of the heartbeat block, with the exact strings that RUNBOOK B3/B4 quote. Every HUD line ≤ 39 characters. Stage 3 adds a host render test of the HUD (like the panel test) asserting that no text overlaps the heartbeat block or rows ≥ 168, and that every check name and POLL condition is legible. |
| N-3 | D13 / 8.2, 8.4, RUNBOOK C5, B | `IN` and `DELIV` drive the death call (C5), the `POLL:RATE` escape and `DEAD?` (8.4), but have no definition, source or behaviour outside mouse mode. | 8.2 defines both from recorded data. For example: `IN` = UHB `mouse_press_total` (the collector's own mousedev press edges, mouse mode only); `DELIV` = seconds since the last POLL with `push_ok` > 0 or `mouse_flags` b3. RUNBOOK C5 says `IN` counts only in mouse mode. |
| N-4 | D2 / section 6 H6, N2b; 10.7 step 2 | The H6 and N2b rules use the literal `rx[2]` = 0x08 (= previous `cmd`), grounded only in the author comment `syscon.h:55-58` and not marked UNVERIFIED. If the healthy GetCtrl2 reply carries another code, a stale-frame death falls to H0. | H6 and N2b compare `rx[2]` with the healthy template's value per command (literal only when there is no template, flagged). Mark this in section 11. Stage 3 adds a stale-frame sequence whose healthy `rx[2]` is not 0x08. |
| N-5 | D13 / 8.2 PANEL "Proves" | The read-back goes through the cached `screen_base` (`pspfb.c:24,396`; `fb_sys_fops.c:41-45`), so it cannot prove the D-cache write-back reaches VRAM. | Correct the 8.2 wording. RUNBOOK B3: if PANEL turns green but no `PSC TEST` band was seen, write it down and report it (or make it an abort item). |

---

## 7. Attacks attempted that found nothing

- **Nested ticks.** Detection is sound: no hardirq nesting with IE off; the softirq count is raised before IRQs are enabled. The thread takes no BH lock in `Syscon_cmd`.
- **Wrong scheduler hook placement.** `try_to_wake_up` is reached from `process_timeout` through `wake_up_process` (`kernel/timer.c:988-990`, `kernel/sched.c:1669`); `context_switch` has a single call site.
- **Retry in place.** Failed `mpage` / `buffer` writes are not retried by the kernel. The rewrite at `seg_end` re-dirties. Leftover bytes stay above `seg_end` because every flush starts there.
- **`durable_tick` meaning.** `drain_tick` is read before the first ring read, and a record is counted in `head` only after it is published.
- **Permanent `CATCHUP` from a ring at its cap.** Every per-tick production rate is below its cap, even in the H1 shape (I 11.7 against 48).
- **PROCS bound.** The 2.6.22 stat line (`fs/proc/array.c:413-415`) is at most about 470 characters with a label. Six lines plus status, `MEM`, `UP` and `BUDDY` stay under 3,600.
- **Panel left stale on screen.** The worker's and the kernel's conditions are complementary.
- **Two collectors after a takeover.** The old worker exits on SIGTERM at its next syscall return, before `ctl`. `O_EXCL` separates the files.
- **Console blanking.** pspfb has no `fb_blank`, so a blank is a one-off clear.
- **Budget.** All figures re-derived (section 3).
- **Format strings.** All checked offset by offset.
