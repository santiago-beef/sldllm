# Gate G1, attempt 2: design review

| | |
|---|---|
| Gate | G1 (design review checklist D1-D20) |
| Attempt | 2 |
| Artifact | `design/DESIGN.md` (2,389 lines, revision 1) and `design/RUNBOOK.md` (341 lines, revision 1), both dated 2026-09-30 23:37-23:39 |
| Reviewer | G1 design reviewer, attempt 2, fresh context, not the designer |
| Inputs read in full | DOSSIER.md (including 9.1-9.7), WORKFLOW.md, recon/syscon.md, recon/input.md, recon/build.md (sections used), gates/LOG.md, gates/G1-attempt1-review.md, DESIGN.md, RUNBOOK.md |
| Source used | `/home/ubuntu/psp/build/linux` (read only), `/home/ubuntu/psp/extract/root2`, `/home/ubuntu/psp/telem/` (read only). Nothing was written outside this file. |
| **Verdict** | **FAIL** |

**Why FAIL.** One blocking item fails (D6) and one non-blocking item fails
(D20). The blocking FAIL is enough on its own.

D6 fails because the new kernel stall panel, which is now the only
indicator the loss bound rests on, is erased by the live worker's own
full-screen redraw. The worker writes all 272 rows every ≈ 0.23 s. The
panel is painted once a second into rows 176-271. So while the worker is
alive but not durable (catching up after a stall, or rewinding after write
errors), the panel is visible for at most ≈ 0.23 s in each second. Worse,
the D8 (c) exit condition "the panel is gone **and** the block is changing
again" becomes true the moment a stalled worker resumes. That is at the
start of its catch-up, before the stalled interval is on the stick. The
operator then pulls the battery, and the post-death script can be lost.
This is the attempt-1 F1 failure in a new form: the operator's pull check
can read "safe" while the data is not durable.

D20 fails on two field mismatches inside the specification. Both are
trivial to fix.

The rest of the revision is strong. The earlier findings F2 to F15 are all
closed (section 5). The budget arithmetic is right to the byte (section 3).
Every citation I opened resolves (section 4); one derivation (S records per
sector) is wrong in a direction that makes the budget conservative. The
design still depends on no hypothesis, streams everything, and adds nothing
inside S5..S20.

---

## 1. Checklist

| ID | B | Result | One-line reason |
|---|---|---|---|
| D1 | B | PASS | Every `Syscon_cmd` call in every context, every poll, every Nop with context, every in-flight tick, and every MS segment are streamed; whole-run stats; no hypothesis privileged |
| D2 | B | PASS | Independent derivation (section 2). Every row is separable, except the declared H8-in-an-unread-register class and "operator did not press" against H6 |
| D3 | B | PASS | SC keeps `rx[16]`, `cmd`, `txlen`, `ret` (s16), `nwords`, `retries` |
| D4 | B | PASS | No trigger; streamed; rings ≥ 114.7 s cover the pre-collector gap; capped catch-up drains the whole backlog with no 64 KB refusal |
| D5 | B | PASS | No trigger exists. `DEAD?` is display-only (8.4) |
| D6 | B | **FAIL** | The live worker erases the kernel panel; D8 (b)/(c) can pass during catch-up or write errors; the stated "≤ 4 s" and "panel disappears after catch-up completes" are false (F-A) |
| D7 | B | PASS | `pscol&` from `rc.sysinit` after `pspmd`; supervisor in C; no typing |
| D8 | B | PASS | Explicit `psc_wd_ctx` flag at both `psp_pacify_watchdog` call sites; `wn`, `W.p_head`, `lc_*`, I samples |
| D9 | B | PASS | One writer per ring and per new structure; `seq` invalidate/publish; `lc_seq` and `led_cmd_id` brackets; high-low-high for `total_counts` |
| D10 | B | PASS | 0 instructions in S5..S20 (G2-checkable); ≈ 0.8 µs per command outside the window; panel paint 0.2-1 ms is stated, counted and never on a watchdog tick |
| D11 | B | PASS | No new MMIO read or write; the panel writes VRAM memory and does a D-cache write-back only |
| D12 | B | PASS | 8,083 B/s payload, 8.9 KB/s total, 8.0/16.0 MB per 15/30 min, recomputed exactly; no poll-rate printk; kernel log not used for history. Writer buffer gap F-C does not change the volume |
| D13 | B | PASS | KRN, POLL, WDOG, CTX, STICK, REC, PANEL, SUP, BTN on screen; abort at 120 s; early-death exception. Advisory F-E (POLL:RATE window) |
| D14 | B | PASS | `ret` s16 plus per-command histograms (−2/−3/−4/−5 distinct); sentinels `drain` 0xFFFF and `ack_polls` 1,000,001 / 0xFFFFFFFF |
| D15 |   | PASS | `jp_loop`, `jp_r3/r4/r5`, POLL `ri_branch`/`pi_flags`/`push_*`/`mouse_flags`/`sig`, `jp_listsem_fail`, `jp_push_eintr`, `jp_sigpending` |
| D16 |   | PASS | `(localTick, Count)`, watchdog at tick ≡ 0 mod 1250 by construction (`psp.c:372-379`), `ts_read` retry |
| D17 |   | PASS | D1-D7 name each button, its duration and raw bit, with the C0 reference and the P6 photograph of RAW |
| D18 |   | PASS | 7.7: objdump FP-register grep, FP mnemonic grep, `nm` grep, `flthdr` |
| D19 |   | PASS | `uClinux_TRACE`; A1 forbids the three existing names; data goes to `/ms0/PSCLOG` |
| D20 |   | **FAIL** | 4.3 sets the catch-up flag in UHB b11, while 10.2/10.5 decode b11 as "no stick" and b12 as catch-up. 1.7 says M records are 64 bytes; 3.1 and 10.3 say 80 (F-B) |

Blocking FAILs: 1 (D6). Non-blocking FAILs: 1 (D20).

### Evidence per item

**D1 PASS.** 3.2: "every `Syscon_cmd` call in every context, every thread
loop iteration, every watchdog command with the interrupted context, every
in-flight tick sample (up to 4 per command), and every Memory Stick segment.
No sampling, decimation or deduplication, except the stated I cap, whose
excess is counted." The stats block (1.8) holds cumulative counters and
histograms. Section 6 classifies after the run, as a trigger / state / flags
triple, with H0 raw dumps.

**D2 PASS.** See section 2.

**D3 PASS.** 1.2: offset 48 `rx` u8[16] "the whole `rx_buf[0..15]` after the
final attempt, including the 0xff prefill". `cmd` offset 18, `ret` s16
offset 20, `nwords` offset 22 = `(ptr − rx_buf)/2` "taken right after S20
(`syscon.c:222`) and before `ptr` is reused by the checksum
(`syscon.c:235`)". Source: `ptr` advances by 2 per received word in the RX
loop (`syscon.c:201-217`). The W and M records use the same 80-byte SC
layout.

**D4 PASS.**
- 3.3: "None. Nothing freezes."
- 3.1: P 4,096 × 80 B at 35.71/s = 114.7 s (recomputed). All W, I, S and M
  records from boot are kept.
- 4.3: the capped drain takes a full-ring backlog in steps. Each RECS chunk
  is ≤ 43,972 B, so the 64 KB chunk limit refuses nothing (6.2).
- A death at 17 s sits in the rings until the first drain. A death at 15 or
  29 min is in the stream.
- The early pull in F-A loses data at the end, not the history before
  onset, so it is scored under D6.

**D5 PASS.** 8.4: `DEAD?` "controls nothing". No condition changes what is
recorded.

**D6 FAIL (blocking).** See F-A. Evidence:
- DESIGN 4.3 step 8 renders the full screen: "272 pairs of one 1,920-byte
  row each". 8.2 describes a "full-screen HUD".
- 2.10 paints the panel into "rows 176-271" at ticks ≡ 125 mod 250.
- The only place where the worker spares the panel is the self-test (8.2
  PANEL: "The worker then leaves the panel on screen for 2 s before
  redrawing").
- 4.5 case 2: "The panel disappears when `durable_tick` is within 3 s of now
  again, that is, after catch-up completes." With a live worker this is
  false. The panel disappears at the worker's next row write, whatever the
  durable age.
- RUNBOOK D8 (c): "As soon as the panel is gone **and** the block is
  changing again, photograph the screen (P7) and go to D9." A stalled
  worker that resumes, or a promoted standby, satisfies this within one tick
  of resuming. That is at the start of a catch-up of up to 15-33 s (4.3).
- 4.3 step 7: `durable_tick` "advances only on a complete drain". So every
  record from the stall onwards, typically the whole post-death script, is
  not yet on the stick when the operator pulls.
- D8 (b) does not gate on the HUD's `DUR`, `CATCHUP` or a red `MS` line. It
  says only to write `DUR` and `TMAX` down.
- 4.6 relies on the panel for write errors ("the stall panel appears after
  3 s and shows the growing loss"). With the worker alive, it flickers
  instead.
- RUNBOOK "Two displays" tells the operator that the panel "updates once a
  second", which implies a steady display.

The stated worst case, "at most about 4 s when D8 (b) applies", therefore
does not hold for these paths. The real loss can exceed the post-death
wait. The attempt-1 closing condition F1(a), "pull only after a live
`TMAX ≤ 2.5 s` reading", is not met either: the new D8 no longer reads
`TMAX`, and 8.2 says `CATCHUP` replaces `TMAX` during catch-up.

**D7 PASS.**
- 4.2: three lines after `pspmd -s&` (`extract/root2/etc/rc.sysinit:17-19`,
  verified).
- The supervisor is written in C because busybox has no `sleep` (verified
  by the earlier review, not contested).
- Nothing requires typing. The operator only presses the scripted buttons.

**D8 PASS.**
- 1.9: WT when `psc_wd_ctx == 2`, set around `psp.c:379`. WB is set around
  `psp.c:557`. `psp_pacify_watchdog` has callers only at `:379` and `:557`
  (`:97` is the prototype, `:383` the definition; verified).
- `in_interrupt()` is kept only as a recorded bit.
- An interrupt during a thread command is recorded in several places:
  - `wn` in the P record;
  - `t_busy`, `p_head`, `epc` and `ext_flags` in the W extension;
  - I samples for ordinary ticks;
  - uncapped `lc_*` words for a suspended thread.
- `TI_REGS` is set at `genex.S:166-167` and restored at `entry.S:39` before
  `preempt_schedule_irq` at `:72` (verified), so the `lc` argument in 1.2
  holds.

**D9 PASS.**
- 3.4 gives one writer per ring and per new structure. The `lc` words are
  written only by the timer interrupt and read by the thread between two
  reads of `lc_seq`. `led_cmd_*` is written only by the MS path under
  `s_psp_ms_rw_sem`, and `ms_psp.c:333,360` are the only entries to the
  sector functions (`:131,260,264`).
- `durable_*` is written only by the collector through `ctl`.
- The `total_counts` high-low-high argument is correct: the single writer
  cannot be interrupted by the reader, so a carry between the reader's
  loads always changes `hi`.
- Minor, not failing: `led_cmd_or` and `led_cmd_pid` are bracketed only by
  `led_cmd_id`. An LED operation for the same command that runs between the
  thread's reads of `or` and `pid` can leave the two inconsistent. Both
  fields are informational.

**D10 PASS.**
- 2.1 A3 and 7.2: the captures are store-target substitutions. The
  attempt-1 reviewer checked the baseline instruction pattern in
  `syscon_tree.o.dis`. The revision does not change A3.
- Added time outside the window is stated in 5.4 (≈ 0.8 µs per command,
  ≤ 2.6 µs).
- No lock, no `local_irq_*`, no `preempt_*` (7.1).
- The panel adds 0.2-1 ms of interrupts-off time per paint (UNVERIFIED).
  It runs at most once a second and never at tick ≡ 0 mod 1250 (1250 ≡ 0
  mod 250, and 125 ≢ 0). It is stated in 7.1 with its effect, and the
  decoder flags any onset within 1 s of a paint.

**D11 PASS.** 7.1: "MMIO accesses: None added, none removed". The LED hook
keeps the single `lw`/`sw` of `psp.c:401,406` (verified: `PSP_GPIO_SET |=
mask_`). The panel writes `PSP_VRAM_BASE` (`include/asm-mips/psp.h:36`,
`0x04000000 + CONFIG_PSP_ADDRESS_BASE`, `.config:51` = `0x80000000`), which
is framebuffer memory, not a SPI, GPIO or syscon register. It then calls
`pspClearDcache` (`ipl_sdk/cache.c:22-37`), which `pspfb_sync` already
calls on every `fb_sys_write` (`pspfb.c:348-352`,
`fb_sys_fops.c:89-90`).

**D12 PASS.** Recomputed in section 3. The design's figures are right. No
printk runs at poll rate. The only printk is the `PSC2` line at init (2.8).
The 16 KB log is read through `/proc/kmsg` for KMSG chunks only, not for
history. F-C (FILEHDR outside the flush bound) and F-F (S rate derivation)
do not change the volume.

**D13 PASS.**
- 8.2 checks KRN, POLL, WDOG, CTX, STICK, REC, PANEL, SUP and BTN.
- BTN requires P08 `rx[3]` bit 4 to clear and then set again. TRIANGLE is
  `0x10` (`joypad_psp.c:40`), which is `rx[3]` bit 4 via `syscon.c:363`,
  active-low per `joypad_psp.c:490` (verified).
- The abort rule fires at 120 s (8.3, RUNBOOK B).
- The widened early-death exception is correct in intent.
- Advisory F-E: the POLL rate window is unspecified. A POLL:RATE-only
  failure can spend the run on a live device.

**D14 PASS.**
- `ret` is s16.
- `hist` indices 3..6 are −2, −3, −4 and −5 for each command, and are kept
  per ring (1.8 words 35-66).
- The −4 sentinel `ack_polls = 1,000,001` is the correct u32 wrap of
  `spin-- == 0` (`syscon.c:154`).
- For −3, `drain` saturates at 0xFFFF and `ack_polls` is 0xFFFFFFFF.

**D15 PASS.** 1.5 and 1.8 words 67-100. Stage codes 0-17 (2.5).

**D16 PASS.**
- `psp.c:372-379` (verified): `localTick` and `lastTick` both start at 0,
  there is one increment per handler, and `lastTick = localTick` when the
  Nop fires. So the Nop runs exactly at `localTick = 1250·k`.
- Count is reset at `psp.c:352`, before `psp_watchdog_tick()` at `:359`.
  That gives the sort order stated in 1.1.

**D17 PASS.** RUNBOOK D1-D7 and row H6. The bit map was verified against
`joypad_psp.c:36-58`:

| Button | Mask | Raw bit |
|---|---|---|
| TRIANGLE | 0x10 | `rx[3]` b4 |
| RIGHT | 0x02 (`:37`) | `rx[3]` b1 |
| LTRG | 0x200 | `rx[4]` b1 |
| HOLD | 0x2000 | `rx[4]` b5 |
| SELECT | 0x100 | `rx[4]` b0 |
| VOL_UP | 0x10000 | `rx[5]` b0 |

P6 photographs RAW during a hold, and the C0 reference runs the same
script.

**D18 PASS.** 7.7: `objdump -d pscol.gdb | grep -c '[$]f[0-9]'` = 0, the FP
mnemonic grep, the `nm` grep for printf, strtod and soft-float symbols, and
`flthdr` with stack 16384. This follows `telem/cbuild.sh:9`.

**D19 PASS.** DESIGN 9 item 1 and RUNBOOK A1 give `uClinux_TRACE`, which is
not `uClinux`, `uClinux_FIX` or `uClinux_WIP` (dossier 9.7). A1 says to stop
if the name already exists. The collector writes only under
`/ms0/PSCLOG/`.

**D20 FAIL (non-blocking).**
- I checked the struct strings with `struct.calcsize`: SC 80, WEXT 432, I
  32, POLL 36, S 48, chunk header 20, FILEHDR fixed part 40, block header 8,
  UHB 80, SELFTEST 8. Every field offset matches tables 1.2-1.6 in order.
- The stats word map 0-255 is contiguous with no overlap.
- `recsize_div4` values P/M 20, POLL 9, W 128, I 8, S 12 are correct.
- Two mismatches remain (F-B):
  1. 4.3 step 1: "catch-up (HUD `CATCHUP`, UHB flag b11)". 10.2 UHB
     `flags`: "b11 no stick; b12 catch-up", and 10.5 "UHB b12". A writer
     built from 4.3 would make the decoder report every catch-up as
     `NO STICK`.
  2. 1.7: "Same 64-byte format as SC". 3.1 and 10.3 say M = SC = 80 bytes.

---

## 2. D2: independent coverage derivation (from the record format only)

I built this from sections 1.1-1.8 and the source before reading section 6.
I compared it with section 6 afterwards.

| Row | What the recorded fields would contain | Confusable with | Separable by |
|---|---|---|---|
| H0 | No row below matches. All P/POLL/W/I/S/M records, STATS, KMSG, PROCS and UHB remain | — | Raw windows |
| H1 no ACK | P33/P08 persistently: `ret −4` with `ack_polls 1,000,001`, `nwords 0`, `rx` 16×ff, large `dtick`/`c_out−c_in` (≥ ~12 ticks, UNVERIFIED); or `ret −3` with `drain 0xFFFF`, `ack_polls 0xFFFFFFFF`, `spi_st9 = spi_sttx = 0`. POLL `ri_branch 3`, `period ≫ 14`; hist P idx 4/5 rising; I samples 4 per command and `i_suppressed` rising. W: pure H1 gives W `ret −4` plus `c_pre_max`/`long_ticks` (IRQ-off timeout); the 9.5 variant gives W `ret ≥ 0` | (a) one −4 from H4 at P2/P3/P4/P5a; (b) H8 in an unread register | (a) persistence and `wn`; (b) **not separable** (declared) |
| H2 | P08 `ret 0`, `nwords ≥ 4`, received bytes all 00 (`rx[0]=0` skips the checksum, `syscon.c:226`), `rx[3..6]=00`; POLL `ri_branch 4`; `jp_r4` +1 per poll | Real HOLD switch; partial zero frames | Real HOLD: only `rx[4]` b5 = 0, `rx[0]` = status ≠ 0, valid checksum (C0/D7). Partial frames: the decoder recomputes the branch from `rx` |
| H3 | P08 `ret 0`, `nwords 0`, `rx` 16×ff, `ack_polls` finite and in the healthy range; POLL `ri_branch 5`, then dedupe; mouse mode POLL `dx=+16`, `dy=+16` | One E3 from H4 at P3/P4/P5a/P5b; H8-unread | Persistence and `wn ≥ 1` on the lone E3; H8-unread not separable |
| H4 | WT record (`tick_in ≡ 0 mod 1250`) with `t_busy` b0, `p_head` = seq of a P record with `wn ≥ 1`. Step: W `epc` if `ext_flags` b4, else `lc_epc`/`lc_r` if b5. P4/P5a split by the Nop's own `ack_polls`, `drain`, `drain_last`. The Nop's `rx`/`ret` show what it consumed. Later P records show the state (triple) | H10; N8 (`pdflush` near the same boundary); N1; coincidence | W as interrupter vs S; `kupd_last_tick`; `ms_delta`; the benign-interleave rate from every W record |
| H5 | Persistent `ret −5` (`retries 16`, `rx[2]∈{80,81}`) or `ret −2` (`rx[1]<3`, a recomputed checksum mismatch, or `rx[1] ≥ 16`) | H4 at P2/P6 (one −2); N2 framing shift; H8-unread | Persistence; N2 by `drain>0` and `rx` echo; H8-unread not separable |
| H6 | P08 `ret>0`=`rx[0]`, checksum valid, `rx[3..8]` byte-identical through D1-D7; POLL dedupe every poll; C0 shows the same presses changing the named bits | H7; operator not pressing | H7 bytes follow the presses. "Not pressing" only by notes and photographs |
| H7 | `rx` follows presses; delivery stops at a stage: `push_fail`/`jp_listsem_fail`/`nqueues 0`; `jp_wake` rising with `fop_read_ret` flat; `md_*` rising with `md_read_ret` flat; `vcs_*`, `console_sem ≤ 0`; POLL `sig` | H9 if the thread stops; N6 (overlaps by definition) | P/POLL continuing excludes H9 |
| H8 | Captured `gpio_in`, `spi_st9`, `spi_sttx`, `drain`/`drain_last`, `ack_polls` distribution, LED read-back OR/AND outside the template after onset | H1/H3/H5 when the change is in a register the code never reads | Only through captured values (declared blind spot, forced by D11 and dossier 9.1) |
| H9 | P and POLL stop; W continues with fixed `jp_loop`, `jp_stage 11` (arg Q), `t_busy 0`; stats `jp_state 1`, `qfree_stage 2` with `qfree_queue = Q`, `fop_release` +1; PROCS shows `psposk2` exiting | N4 (stage 7/8), N5 (stage 15/16, state 0), N9 (`t_busy` set), a thread asleep in `msleep` forever (stage 17) | `jp_stage`, `qfree_stage`, `t_busy`, `jp_state` |
| H10 | P record `ms_delta>0`, `preempt_delta>0`, `lc_epc` in S13..S20, `led_or & ~0xC0 ≠ 0`, `led_pid`; overlapping S record with `flags` b4/b5 and `rd_*_or`; onset not at tick ≡ 0 mod 1250 | H4; N1 | Interrupter is S not W; N1 has `ms_delta 0` |
| H10b | S record `flags` b2 or `rd_set_or & 0x08`, with b4=b5=b6=0 near onset; `led_rd_set_b3` rising | H10 | In-flight flags |

**Confusable after every field is used:**
1. H8 in an unread register against H1, H3 and H5. This is declared and
   unavoidable without reading registers that dossier 9.1 says are not
   proven safe.
2. H6 against "operator did not press". Only the operator's notes and
   photographs separate them.
3. H7 against N6. They overlap by definition; this is not a defect.
4. Early death without C0 or a template. H6 and H7 rest on the source bit
   map, and H8 and N2 are `unassessable`. Declared in section 6 and 10.7
   step 2.
5. H10 written back while the thread is suspended in S5..S12. The rule in
   row H10 requires `lc_epc` in S13..S20, so this variant would fall to H0
   with raw data. It is recorded (`lc_epc`, `led_or`), but no rule reports
   it (advisory F-G).

**Agreement with the designer's matrix.** The rows and separators match
mine. Two points go beyond it: item 5, and stage 17 as a thread-stopped
shape outside H9, N4 and N5. That shape goes to H0 with raw data, which is
acceptable.

---

## 3. Budget arithmetic, recomputed (Python, independent of the design's script)

| Quantity | Design | Recomputed |
|---|---|---|
| Polls/s | 17.86 | 250/14 = 17.857 |
| P, POLL, W, I, S B/s | 2,857 / 643 / 102 / 288 / 1,278 | 2,857 / 643 / 102.4 / 288 / 1,277 |
| RECS hdr, STATS, UHB, PROCS, PAD B/s | 296 / 1,135 / 435 / 962 / 87 | 296 / 1,135 / 435 / 962 / 87 |
| Payload | 8,083 B/s | 8,083 B/s |
| Flushes (plain / +STATS / +STATS+PROCS) | 1,377→1,536; 2,421→2,560; 4,191→4,608 | 1,376→1,536; 2,420→2,560; 4,190→4,608 |
| Total, data sectors per tick | 8,904 B/s, 4.0 | 8,909 B/s, 4.0 |
| 15 / 30 min | 8.0 / 16.0 MB | 8.02 / 16.04 MB |
| Rings | 865,280 B | 865,280 B |
| Spans P, POLL, S, I | 114.7, 114.7, 154, 455 (80 at H1) s | 114.7, 114.7, 154.0, 455 (80.3) s |
| Drain cap unit / max RECS chunk | 10,976 / 43,972 B | 10,976 / 43,972 B |
| Largest flush (no KMSG/EVENT) | 48,756 → 49,152 | 48,756 → 49,152; **with a FILEHDR (1,340 B) 50,096 → 50,176, over the buffer (F-C)** |
| Sector writes/s, ours vs telem | 26.6 vs 13.0 (2.0×) | 26.1 + FAT vs 13.05 |
| Catch-up of a 114 s P backlog at 0.3 s ticks, m = 2 | ≈ 15 s | 4,096 / (96 − 10.7) = 48 ticks = 14.4 s |

The arithmetic is right. The 2.0× ratio (against the attempt-1 reviewer's
1.7×) is justified by the larger records: 4.0 data sectors plus 2 metadata
sectors per `fsync`, against telem's 1 + 2.

---

## 4. Source citation check

I opened every cited location below. "OK" means it resolves and says what
the design claims.

| Citation(s) | Result |
|---|---|
| `psp.c:32-41, 96-97, 133-136, 151, 204-223, 254-263, 265-279, 348-367, 370-381, 383-393, 399-407, 429, 554-557, 591-596, 611-618, 637-654` | OK |
| `genex.S:162-169, 166-167, 266-267`; `entry.S:39, 45-48, 61-73` | OK |
| `thread_info.h:37`; `ptrace.h` `regs[32]`; `mipsregs.h:789, 810`; `head.S:182-187`; `sched.h:907`; `sched.c:171-172, 3626-3628`; `highmem.h:49-52` | OK |
| `joypad_psp.c:36-58, 40, 37, 49, 58, 384-411, 453-472, 474-496` | OK (the `:35`→`:37` fix is in place) |
| `ms_psp.c:92, 119, 131, 228-236, 254, 260, 264, 284-326, 328-353, 355-379` | OK |
| `memstk.c:59-65, 167-169, 174-181` | OK (`ms_wait_unk1` compiled out, as stated) |
| `fs/sync.c:55-76, 62, 67-68`; `fs/fat/file.c:136`; `fs/fat/inode.c:453-459, 540-541, 955, 1189, 1243-1252, 1311-1313`; `fs/fat/misc.c:40-72, 65, 69`; `fs/fat/fatent.c:347, 434, 479, 500, 548, 586-611`; `fs/super.c:401-408` | OK. `fat_count_free_clusters` has exactly one caller (`inode.c:541`) |
| `fs/buffer.c:429-450` (lost page write) | OK |
| **`fs/buffer.c:2593-2621`, cited in 1.6 for "one bio per buffer head, so the S rate equals the sector rate"** | **Wrong conclusion for file data.** vfat file data is written by `fat_writepages` → `mpage_writepages` (`fs/fat/inode.c:126-129, 202`). A page whose buffers are all dirty and contiguous goes out as one bio segment of up to 8 sectors (`fs/mpage.c:488-535`). Only mixed pages fall back to per-buffer `submit_bh` (`:656-661`). `psp_ms_transfer_bio` calls `psp_ms_write` once per segment (`ms_psp.c:252-265`). So the S rate is ≤ the sector rate. The budget and ring span stay conservative (F-F) |
| `binfmt_flat.c:575-596, 590-594`; `mm/nommu.c:745` | OK |
| `kernel/sysctl.c:748-749`; `fs/drop_caches.c`; `fs/proc/proc_misc.c:707` | OK |
| `psp.h:31-37`; `pspfb.c:28-39, 66-68, 348-352`; `cache.c:22-37`; `fb_sys_fops.c:16-53, 89-92` | OK. `fb_sys_read` exists, so the PANEL pixel read-back is possible |
| `fs/proc/array.c:167, 275-279, 413`; `fs/proc/kmsg.c:36` | OK |
| `vc_screen.c:562-590`; `mousedev.c:228, 304, 659`; `printk.c:67`; `vt.c:174`; `input.c:656, 663` | OK |
| `mm/page-writeback.c:80, 433, 449, 453, 469-472, 585`; `init/main.c:568, 573, 628` | OK |
| `scripts/gen_initramfs_list.sh:287-290`; `.config:51, 64, 109, 163` | OK |
| `syscon.h:101, 132-134`; `syscon.c:92-99, 140-146`; `serial_psp.c:352`; `drivers/Makefile:28, 59` | OK |
| `extract/root2/etc/rc.sysinit:6, 10, 14, 17-19` | OK |
| `telem.c:367-373` (heartbeat toggles each tick); `telem/logs-from-stick/kmsg.txt` (118999M, 243,711,875 sectors; FPU emulator line; no "Unknown IRQ") | OK |
| `vmlinux.bin` 1,723,228 B, `vmlinux-0.22.bin` 899,402 B, `_end` `0x881b6230`, telem 12,076 B | OK |

---

## 5. Previous findings (attempt 1): closure

| Finding | Status | Evidence |
|---|---|---|
| F1 D6 (blocking) | **NOT CLOSED** (reopened as F-A) | (b) is done: 4.5 drops "SYNC AGE rising" and states the stalled loss. (c) is done in a stronger form: the kernel panel. (a) is not met. D8 no longer requires "a live `TMAX ≤ 2.5 s` reading". Its replacement, "panel gone and block changing", is satisfied by a live worker that has not caught up. See F-A |
| F2 D20 chunk vs flush | **CLOSED** | 4.3 caps give ≤ 43,972 B per RECS chunk; the 49,152 B buffer is stated; lap and catch-up arithmetic verified; Stage 3 full-ring and 100 s tests added (8.5). New gap F-C (FILEHDR) is separate |
| F3 FSINFO on every `fsync` | **CLOSED** | 5.2, 7.5, R9 and 12.2 F1 corrected; verdict "B"; Stage 3 `led_calls` model stated; the 2.0× ratio is justified |
| F4 POWER/HOLD slider | **CLOSED** | RUNBOOK D7 "DOWN until it clicks into HOLD … never push it up past the middle"; never-press row; the abort rule covers an accidental power-off; R32 |
| F5 early death to abort | **CLOSED** | 8.3 and RUNBOOK B exception cover POLL and/or BTN failures with the POLL condition named; every abort keeps the stick and returns `PSCLOG` (RUNBOOK lines 156-158). Advisory F-E |
| F6 raw image | **CLOSED** | E1 `PSCLOG` copy first as primary evidence; E2 optional with 124.8 GB, 130 G free check, 35 min-1 h 45 min; residual risk stated |
| F7 on-device `statfs` | **CLOSED** | 4.4 removes `statfs` (verified: `usefree` off by default, `inode.c:955`, `:1311-1313`); A3 checks free space on the Mac |
| F8 image growth | **CLOSED** | 5.3 and R21 give +22-28 / +17-23 KB with a ≤ 48 KB bound checked at G2 C6 |
| F9 PROCS size | **CLOSED** | Re-estimated from `array.c:413` (44 fields) to ≈ 1,750 B; bound 3,600 B; Stage 3 range [1,000, 3,600] |
| F10 H10 out-of-transaction | **CLOSED** | Row H10b and 10.7 step 5 |
| F11 early-death template | **CLOSED** | 10.7 step 2 `NO HEALTHY TEMPLATE` fallback; section 6 "Early death" |
| F12 torn `total_counts` | **CLOSED** | High-low-high in 1.8 and 3.5, with a correct argument |
| F13 A2 checksum | **CLOSED** | A2 mandatory, placeholder means stop |
| F14 AC/battery, mouse mode | **CLOSED** | "Before you start" questions 2-3; DESIGN 9 item 2 AC rule |
| F15 citations | **CLOSED** | `:37` in row H6; `mousedev.c:659` in 1.8 and 2.6 |

---

## 6. Runbook read as an operator who has never seen the code

1. **"Two displays" and D8.** The operator is told the panel "updates once
   a second" and that its absence means the data is safe. With a live worker
   the panel flashes for ≤ 0.23 s each second, or disappears at once when a
   stalled worker resumes. D8 (c) then sends the operator to pull during
   catch-up. D8 (b) never looks at `CATCHUP`, a red `MS` line or `DUR`
   (F-A).
2. **B3.** At first start `durable_tick` is 0 until the first complete
   drain. The start-up catch-up takes 3-8 s (4.3), so `PSC STALL` flashes
   during the self-test. The runbook explains only `PSC TEST`. An operator
   may think something is wrong, and section C4 does not apply yet (F-A
   closure item).
3. **B abort exception.** "POLL stays red" has no deadline. Is the decision
   made at 2:00? A `POLL:RATE`-only failure, with BTN green and the cursor
   responding, sends a live device to section D and spends the run (F-E).
4. **B2 (P1).** The `PSC2` line may scroll away before it can be
   photographed. The runbook does not say whether a missed P1 matters. It
   does not: the line is also in the KMSG chunk (F-H).
5. Everything else is unambiguous: A1-A5, C0-C6, D0-D7a, D9 and E1-E3 each
   give a time and an action, with photograph numbers. The slider direction,
   AC handling, checksum and free-space steps are now explicit.

---

## 7. Attacks attempted

| # | Attack | Outcome |
|---|---|---|
| A1 | Live worker overwrites the kernel panel; stall → resume → D8 (c) exit | **Breaks D6** (F-A) |
| A2 | Write-error burst at D8 time (worker live, `durable_tick` frozen) | Panel flickers at ≈ 20 % duty; D8 (b) passes on "no panel seen" (F-A) |
| A3 | Worst-case flush in a new segment (promotion or rewind) with FILEHDR, STATS and PROCS due | 50,096 B > the 49,152 B static buffer; FILEHDR placement unspecified (F-C) |
| A4 | 60 s error burst (Stage 3's own test) with one new segment per error, `S??` two digits | ≈ 261 segments needed, 100 available; EEXIST and exhaustion unspecified; ENOSPC loops (F-D) |
| A5 | Writer flag bits against decoder flag bits | UHB catch-up b11 vs b12 (F-B) |
| A6 | Record sizes across sections | 1.7 "64-byte" M vs 80 (F-B) |
| A7 | S records per sector? | No: `mpage_writepages` makes multi-sector segments; budget conservative (F-F) |
| A8 | Self-test POLL thresholds vs sampling noise and a 15-17 jiffy period | Window unspecified; false early-death path (F-E) |
| A9 | H10 variant while suspended at S5..S12 | Recorded, no rule (F-G) |
| A10 | Panel paint on a watchdog tick | Impossible: 125 mod 250 vs 0 mod 1250 |
| A11 | Panel reads MMIO? | No: VRAM stores plus `pspClearDcache` |
| A12 | `lc` tear between thread and IRQ | Rejected by the `lc_seq` bracket; the IRQ cannot be interrupted |
| A13 | Collector restart needs a 1 MB block | Removed: 128 KB images, pre-spawned standby |
| A14 | Catch-up can lap a ring | Only for ticks > 3.8 s (5.4 s for P); a 114 s gap catches up in ≈ 15 s |
| A15 | `statfs` FAT scan | Gone; only caller verified |
| A16 | Early death at 20 s: POLL fails, operator aborts? | No: exception → section D; template fallback |
| A17 | Budget and rings | All recomputed; correct |
| A18 | 64-bit stats tear | High-low-high correct |
| A19 | `led_cmd_or`/`led_cmd_pid` tear | Possible, informational only (noted under D9) |

---

## 8. Findings

Each finding states exactly what closes it. F-A fails the gate. F-B fails
D20 (non-blocking). The others are corrections or advisories that must be
answered in the revision. None of them alone would fail the gate.

### F-A. D6 (blocking FAIL): the live worker erases the kernel panel, so the pull check can pass while data is not durable

**Problem.**
- 4.3 step 8 redraws all 272 rows every tick, including the panel rows
  176-271 (2.10).
- Only the PANEL self-test spares them (8.2).
- While the worker is alive but `durable_tick` lags (catch-up after a stall
  or promotion, or a write-error burst), the panel flashes for ≤ 0.23 s per
  second.
- It vanishes the moment a stalled worker resumes.
- RUNBOOK D8 (c) then pulls "as soon as the panel is gone and the block is
  changing again". That is at the start of a catch-up of up to 15-33 s,
  before the stalled interval, typically the post-death script, is durable.
- D8 (b) does not check `CATCHUP`, a red `MS` line or `DUR`.
- These claims are false for a live worker:
  - 4.5 case 2: "The panel disappears when `durable_tick` is within 3 s of
    now again";
  - 4.6: the panel "appears after 3 s and shows the growing loss";
  - RUNBOOK "updates once a second";
  - RUNBOOK timing summary "at most about 4 s when D8 (b) applies".
- 2.10's list of paint occasions omits write-error bursts and post-stall
  catch-up.

**Closes when (all three):**
1. **Either**
   - (a) 4.3 step 8 and 2.10 specify that the worker does not write rows
     176-271 while the kernel's panel condition holds, that is while
     `now − durable_tick > 750`, or `now − last_reader_tick > 750`, or
     `panel_last_tick` is within the last 250 ticks. The worker reads all
     three from stats every tick. The panel then stays until the stick is
     within 3 s, and 4.5's statement becomes true.
   - **or** (b) RUNBOOK D8 (b), the D8 (c) recovery exit and C4 step 3
     additionally require the HUD `MS` line to show no `CATCHUP`, not to be
     red, and to show `DUR` below 3 s.

   (a) is recommended, and (b) is harmless to add as well.
2. The text is made consistent:
   - 4.5 case 2, 4.6 and 2.10 (paint occasions: add write errors and any
     catch-up);
   - RUNBOOK "Two displays" (what a flashing panel means);
   - RUNBOOK B3 (`PSC STALL` during the start-up catch-up is normal; with
     option (a) it stays up for those seconds);
   - the timing summary.
3. Stage 3 (8.5) adds a test: a 40 s stall, then resume and catch-up, and
   separately a 20 s write-error burst. The test asserts that the panel
   region is not overwritten by the worker (option a), or that the D8 exit
   condition is false (option b), until `now − durable_tick ≤ 750`.

### F-B. D20 (non-blocking FAIL): writer and decoder disagree on fields

**Problem.**
- 4.3 step 1 puts catch-up in "UHB flag b11". 10.2 defines b11 = no stick
  and b12 = catch-up, and 10.5 uses b12.
- 1.7 says M records are "the same 64-byte format as SC". 3.1 and 10.3 say
  80.

**Closes when:**
- 4.3 says b12;
- 1.7 says 80 bytes;
- a sweep confirms that every flag bit and size named outside section 10
  equals section 10. The 12.1 "64-byte SC record layout" provenance row
  should say "(attempt 1)".

### F-C. Flush buffer bound omits FILEHDR (correction)

**Problem.**
- FILEHDR (20 + 40 + 1,024 + 256 = 1,340 B, 10.2) is not in 4.3's list of
  chunks per flush, and not in the 49,152 B bound.
- Where it is written is unspecified.
- A promoted or rewound worker opens a new segment during catch-up, with
  STATS and PROCS possibly due: 48,756 + 1,340 = 50,096 B, which overflows
  the static buffer.
- If FILEHDR is instead written alone without padding, the "sector-aligned
  flushes" invariant (4.4) breaks.

**Closes when:**
- 4.3 and 10.2 state that FILEHDR is written as its own padded flush
  (`write` + `fsync`) at segment open, or add it to the deferral rule with
  recomputed bounds;
- the Stage 3 full-ring test includes a new-segment first flush with STATS
  and PROCS due.

### F-D. Segment numbering and churn during error bursts (correction)

**Problem.**
- Names are `T<rrr>S<ii>.BIN` with two-digit `ii` (4.4, and 4.2
  `T???S??.BIN`).
- 4.6 opens a new segment on every `write`/`fsync` error, that is about
  4.35 per second during a burst. Stage 3's own 60 s burst needs ≈ 261
  segments.
- Unspecified:
  - how `ii` is chosen across worker, standby and promotion;
  - what happens on `EEXIST` or at `ii = 99`;
  - what happens when `open` itself fails, or on ENOSPC, where each retry
    creates a directory entry.

**Closes when 4.4 and 4.6 specify:**
- the `ii` width (for example `T001S001`, still 8.3);
- monotonic allocation, taking the next number on `EEXIST`;
- a churn limit, for example reusing the current new segment while it holds
  no successful write, or opening at most one new segment per 5 s during a
  burst.

Stage 3's error-burst tests must then check the segment count.

### F-E. Self-test POLL:RATE window and the early-death exception (advisory)

**Problem.**
- 8.2 "P head advances ≥ 30 records/s and POLL ≥ 15/s" gives no
  measurement window.
- Over one 0.23 s tick, ±1 poll of quantisation (4.35 polls per window)
  can read ≈ 13/s on a healthy device. A 17-jiffy period (14.7 polls/s)
  also fails.
- The exception then sends the operator to section D, and "This counts as
  the run", even when BTN passed and the cursor still responds.
- "POLL stays red" has no deadline.

**Closes when:**
- 8.2 fixes the window (for example ≥ 5 s, from the stats heads and
  `now_tick`);
- RUNBOOK B says the decision is taken at 2:00;
- if only `POLL:RATE` is red and the cursor moves with the stick, the
  operator notes it and continues to C0 instead of D.

### F-F. S records are per bio segment, not per sector (citation correction)

**Problem.**
- 1.6 cites `fs/buffer.c:2593-2621` for "one bio per buffer head, so the S
  rate equals the sector rate". vfat file data goes through
  `mpage_writepages` (`fs/fat/inode.c:126-129, 202`).
- A fully dirty page is one segment of up to 8 sectors (`fs/mpage.c:488-535`),
  and each segment is one `psp_ms_write` call (`ms_psp.c:252-265`).
- The S rate is therefore ≤ 26.6/s. The budget and the 154 s span are
  conservative, but the text is wrong, and one S record can cover several
  sectors (`led_ops` > 2).

**Closes when:**
- 1.6 and 5.1 state the S rate as an upper bound with this path;
- Stage 3's volume model accepts S records ≤ sectors written.

### F-G. H10 rule excludes suspension at S5..S12 (advisory)

**Problem.** Row H10 requires `lc_epc` in S13..S20. The design itself treats
read-back semantics as unknown (the UL1 generalisation). A foreign bit
written back while the thread is suspended in S5..S12, for example bit 3
raising G3 before the TX FIFO is loaded, is recorded but reported as H0.

**Closes when** the H10 rule fires for any suspension step in S5..S20 with
`led_or & ~0xC0 ≠ 0` and reports the step, or 6 and 10.7 state why S5..S12
is excluded.

### F-H. RUNBOOK B2 photo P1 (advisory)

**Closes when** B2 says that if the `PSC2` line scrolls away before it can
be photographed, the operator carries on. This is not an abort; the line is
also recorded in the KMSG chunk.
