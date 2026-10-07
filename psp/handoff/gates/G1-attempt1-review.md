# Gate G1, attempt 1: design review

| | |
|---|---|
| Gate | G1 (design review checklist D1-D20) |
| Attempt | 1 |
| Artifact | `design/DESIGN.md` (1,481 lines) and `design/RUNBOOK.md` (231 lines), both dated 2026-09-30 22:47 |
| Reviewer | G1 design reviewer, fresh context, not the designer |
| Inputs read in full | DOSSIER.md (incl. 9.1-9.7), WORKFLOW.md, recon/syscon.md, recon/input.md, recon/build.md (sections used), recon/image2008.md §0 and §7, gates/LOG.md, DESIGN.md, RUNBOOK.md |
| Source used | `/home/ubuntu/psp/build/linux` (read only), `recon/scratch-2008/syscon_tree.o.dis`, `/home/ubuntu/psp/extract/root2`, `/home/ubuntu/psp/telem/` |
| **Verdict** | **FAIL** |

**Why FAIL.** One blocking item fails (D6) and one non-blocking item fails
(D20). Either the blocking FAIL alone, or the rule "any blocking FAIL", is
enough. D6 fails because the bound on data lost at the battery pull rests on
an operator check (`SYNC AGE`, `TMAX`) that the stalled writer draws itself.
The check cannot detect the one condition it exists to catch, and the design
claims a signal ("SYNC AGE rising") that cannot appear. D20 fails because the
chunk format caps a chunk at 64 KB, while the writer's algorithm builds one
chunk per flush with no bound. The first flush after boot and every
post-restart catch-up can exceed that cap.

The rest of the design is strong. The zero-instruction-in-window capture is
real ([OBJ] checked below). The context flag is exact. The record format is
consistent to the byte. The byte budget arithmetic is right. Most citations
resolve. Both failures can be fixed without redesign.

Note for the orchestrator (gates/LOG.md, 2026-09-30 note): the design lists
dossier 9.6 among its inputs. It builds its timestamps (1.1), the W extension
(1.3), I samples (1.4) and the H4 row (section 6) around 9.6. **The design covers 9.6.**

---

## 1. Checklist

| ID | B | Result | One-line reason |
|---|---|---|---|
| D1 | B | PASS | Every call in every context is recorded, streamed in full, plus whole-run stats. No hypothesis is privileged |
| D2 | B | PASS | Independent derivation (section 2) finds every row separable except H8-in-an-unread-register, which is declared and unavoidable under D11 |
| D3 | B | PASS | SC record keeps `rx[16]`, `cmd`, `ret` (s16), `nwords` |
| D4 | B | PASS | No trigger; streamed; rings ≥ 114 s cover the pre-collector gap. Advisories F5, F11 |
| D5 | B | PASS | No trigger exists; nothing depends on detecting onset |
| D6 | B | **FAIL** | Stated ≤ 5 s bound is not enforced when the writer stalls; D8 check reads values the stalled writer draws (F1) |
| D7 | B | PASS | Collector from `rc.sysinit`, supervisor in C, no typing |
| D8 | B | PASS | Explicit origin flag; W extension links the in-flight P command; `wn`; I samples |
| D9 | B | PASS | One writer per ring, `seq` invalidate/publish, reader double-checks `seq` |
| D10 | B | PASS | 0 instructions in S5..S20 (G2-checkable), ≈0.7 µs outside, stated and measured |
| D11 | B | PASS | No new MMIO reads at all; only values the code already loads |
| D12 | B | PASS | 6.7 KB/s recomputed exactly; no poll-rate printk; kernel log not used for history. Corrections F3, F9 |
| D13 | B | PASS | HUD checks KRN..BTN; BTN proves a physical press in recorded raw data. Advisories F5, F7 |
| D14 | B | PASS | `ret` s16 keeps −2/−3/−4/−5 distinct; per-command histograms |
| D15 |   | PASS | `jp_loop`, `jp_r3/r4/r5`, POLL `ri_branch`, proc/push/mouse counters, `listsem_fail`, `push_eintr`, POLL `sig` |
| D16 |   | PASS | `(localTick, Count)`; watchdog at tick ≡ 0 mod 1250 by construction |
| D17 |   | PASS | D1-D7 name buttons, durations and the raw bit each sets; reference C0. Runbook hazard F4 |
| D18 |   | PASS | Integer-only; objdump/`nm`/`flthdr` check stated (7.7) |
| D19 |   | PASS | `uClinux_TRACE`; A1 forbids touching `uClinux*`; output goes to `/ms0/PSCLOG` |
| D20 |   | **FAIL** | Record structs match field for field, but the chunk/flush spec is self-inconsistent for backlogs (F2) |

Blocking FAILs: 1 (D6). Non-blocking FAILs: 1 (D20).

### Evidence per item

**D1 PASS.** DESIGN 3.2: "every `Syscon_cmd` call in every context, every
thread loop iteration, every watchdog command ... every Memory Stick segment.
No sampling, decimation or deduplication, except the stated I cap". Stats
block 1.8 holds whole-run counters and histograms. Section 6 classifies after
the fact over every hypothesis. It is not a one-counter design.

**D2 PASS.** See section 2 (independent derivation). All rows H0-H10 leave
distinct field patterns. The one confusable class is H8 whose change is in a
register the code never reads. That is indistinguishable from pure H1/H3/H5
by any field. The design declares this blind spot in row H8. It cannot be
closed without reading registers that dossier 9.1 says are not proven safe.
That would violate D11.

**D3 PASS.** 1.2: offset 48 `rx` u8[16] "the whole `rx_buf[0..15]` after the
final attempt, including the 0xff prefill"; offset 18 `cmd`; offset 20 `ret`
s16; offset 22 `nwords` = `(ptr − rx_buf)/2` after S20. Source: `ptr = rx_buf`
at `syscon.c:201`, `ptr+=2` per word at `:216`, reused at `:235`. The
capture point is between them, so it is correct. The same record serves W
(watchdog) and M.

**D4 PASS.** 3.3: "None. Nothing freezes". 3.1: P 4096 × 64 at 35.71/s =
114.7 s (recomputed). Death at 17 s is in the rings until the collector
drains them. Death at 15 or 29 min is in the stream. 4.6 caps at 64 MB,
about 2.7 h. Advisories F5 (early death routed to "abort") and F11 (decoder
template undefined for early death) do not lose history. F2 (first-flush
size) is scored under D20.

**D5 PASS.** 3.3 and 8.4: the only onset indicator (`DEAD?`) "controls
nothing".

**D6 FAIL (blocking).** See F1. DESIGN 4.5 states "Worst-case loss = 2 ×
T_max ... ≤ 5 s" and makes the runbook enforce it with "`TMAX ≤ 2.5 s` and
`SYNC AGE < 3 s`". The same section then says "If the worker is stalled at
the pull, the loss equals the stall. The HUD shows it (frozen heartbeat,
`SYNC AGE` rising)". The HUD is drawn by the worker (4.3 step 8, after the
`fsync` at step 7). A stalled worker cannot draw a rising `SYNC AGE`. The
screen keeps the last value drawn, typically "0.2S". RUNBOOK D8 tells the
operator to read `SYNC AGE` and `TMAX` and pull if they are in range. It does
not require the heartbeat to be seen alive first. Line 180 sends a frozen
display through D1-D9 "in full", so D8 is evaluated on stale numbers. On a
live HUD `SYNC AGE` is structurally about 0, because rendering follows the
`fsync`. It moves only on write errors. The ≤ 5 s bound is therefore not
established. In the stalled case the loss is unbounded and unstated: every
record after the last completed `fsync`, possibly including onset and the
whole post-death script. That is exactly the S2 window.

**D7 PASS.** 4.2: three `rc.sysinit` lines after `pspmd -s&`
(`extract/root2/etc/rc.sysinit:17-19` verified). The supervisor is written in
C because busybox has no `sleep` (verified: no `sleep` link in `bin/` or
`usr/bin/`, no string in `bin/busybox`). `/dev/null` exists (c 1,3). The
operator only presses the scripted buttons.

**D8 PASS.** 1.9: origin WT is set by an explicit flag around
`psp.c:379`. This is exact because `psp_pacify_watchdog` has callers only at
`psp.c:379,557` (grep: `:97` prototype, `:383` definition). `in_interrupt()`
is kept only as a recorded cross-check (dossier 9.1). W extension: `t_busy`,
`p_head`, EPC/GPR/stack (1.3). P record: `wn` (1.2 offset 39). Non-watchdog
ticks during a command: I record (1.4). `regs = current_thread_info()->regs`
is valid: `genex.S:166-167` stores `sp` to `TI_REGS` before
`j plat_irq_dispatch`, and `entry.S:39` restores it.

**D9 PASS.** 3.4: one writer per ring (P thread, W timer/boot, I timer,
S under `s_psp_ms_rw_sem` at `ms_psp.c:333,360`, verified to be the only paths
to `psp_ms_read_sector`/`write_sector`: `ms_psp.c:131,260,264`, M
effectively boot-only). The invalidate-fill-publish sequence and the reader's
`seq` check before and after the copy are stated. The interruption case is
walked explicitly. Minor: F12 (64-bit `total_counts` read torn by the reader).

**D10 PASS.** 2.1 A3/7.2: captures are store-target substitutions. I checked
the baseline pattern in `syscon_tree.o.dis`:
- `+0xdc lw v0,0(s4)` / `+0xe0 andi` / `+0xe4 sh v0,0(sp)` (S5)
- `+0x14c..0x154` (drain `dmy`)
- `+0x168..0x174` (S9)
- `+0x190/0x1a0/0x1a8` (TX status)
- the spin counters `lw/addiu/sw/lw 4(sp)` at `+0x110..0x11c` and `+0x1dc..0x1e8`
- `−3` via `li t3,-3` in the delay slot at `+0x124` / `j` at `+0x128`, and `−4` at `+0x20c`
- S20 store at `+0x2ac sw s5,0(s0)`, with `s0` = `0xbe24000c`.

All as the design states. Added time: ≈150 instructions per command outside
the window (5.4). The command's own duration is UNKNOWN from source, but it
is at least 23 uncached MMIO accesses plus ACK latency, and it is measured in
the run (`CMD MED`, `p_rec_cost_*`). No lock, no `local_irq_*`, no
`preempt_*` (7.1). The W extension adds ≈1.4 µs of IRQ-off time after the
Nop. It is stated, and its only risk (G4L level-sensitive) is declared as
R5, UNVERIFIED.

**D11 PASS.** 7.1: "MMIO accesses: None added, none removed, same order".
The LED hook keeps the single `lw`/`sw` of `psp.c:401,406`. The W
extension reads RAM only. CP0 Count/Status reads are coprocessor moves (R6).
The design reads no register the code does not already read. That is
stricter than D11 requires.

**D12 PASS.** Recomputed (section 3): payload 5,215 B/s, padded 1,536 B per
flush, total 6,682 B/s, 6.01 MB per 15 min, 12.03 MB per 30 min. This matches
DESIGN 5.1. Kernel rings 626,688 B, matching 3.1. The only printk is at init
(2.8). The history does not use the 16 KB log. Two premises are wrong and
must be corrected, but neither changes log volume materially:
- F3: FSINFO is written on every `fsync`, which changes the LED/sector
  figures in 5.2.
- F9: the PROCS chunk is underestimated.

**D13 PASS.** 8.2: KRN (magic, `build_id`), POLL, WDOG (`tick % 1250 == 0`),
CTX (`in_interrupt()` 0 in WT), STICK (first `write`/`fsync` returned 0),
REC, BTN. BTN checks P08 `rx[3]` bit 4. Verified: `PSP_JOYPAD_KEY_TRIANGLE
0x00000010` (`joypad_psp.c:40`), which is key bit 4 of `rx[3]`
(`syscon.c:363`), active-low (`joypad_psp.c:490`). The abort rule is 120 s
(8.3, RUNBOOK B). Advisories: F5 (early-death shapes other than "BTN only"
are routed to abort) and F7 (on-device `statfs` may delay PASS).

**D14 PASS.** 1.2 `ret` s16. `hist` indices 3..6 are −2, −3, −4, −5 per
command (1.8 words 35-66). Sentinels distinguish −3 (`drain` 0xFFFF,
`ack_polls` 0xFFFFFFFF) from −4 (`ack_polls` 1,000,001, which is the correct
u32 wrap of `spin-- == 0` at `syscon.c:154`).

**D15 PASS.** 1.5 POLL (`ri_branch`, `pi_flags`, `push_ok/fail`,
`mouse_flags`, `sig`) and 1.8 words 67-100 (`jp_loop`, `jp_r3/r4/r5`,
`jp_proc_calls`, `jp_listsem_fail`, `jp_push_eintr`, `jp_sigpending`).

**D16 PASS.** 1.1: `localTick` (`psp.c:372,375`). It is incremented once per
handler after the Count reset (`psp.c:352`, the first action) and before the
Nop (`psp.c:379`). The watchdog fires exactly at `localTick = 1250·k`
(`psp.c:376-378`, both counters start at 0), verified. Watchdog records sort
after the thread activity they interrupted with no correction. `ts_read()`
retry covers the torn read.

**D17 PASS.** RUNBOOK D1-D7 and DESIGN row H6 name each button with its raw
bit. Verified against `joypad_psp.c:36-58`:
- TRIANGLE 0x10 → `rx[3]` b4
- RIGHT 0x02 → `rx[3]` b1
- LTRG 0x200 → `rx[4]` b1
- HOLD 0x2000 → `rx[4]` b5
- VOL_UP 0x10000 → `rx[5]` b0
- stick → `rx[7]`/`rx[8]`

Durations are fixed. P6 photographs the RAW line during a hold. The same
script is run healthy (C0). Runbook hazard F4 (POWER/HOLD slider direction)
does not affect separability.

**D18 PASS.** 7.7: objdump `grep -c '[$]f[0-9]'` = 0, the FP mnemonic grep,
the `nm` grep for printf/soft-float, and `flthdr`. This follows
`telem/cbuild.sh:9`.

**D19 PASS.** DESIGN 9 item 1, RUNBOOK A1: new folder `uClinux_TRACE`, which
does not collide with `uClinux`, `uClinux_FIX` or `uClinux_WIP` (dossier
9.7). "Do not touch" the baseline. Stop if the name exists. Data goes to
`/ms0/PSCLOG/`.

**D20 FAIL (non-blocking).** Field-for-field check done with
`struct.calcsize` and offset walk:

| Struct | Size | Matches |
|---|---|---|
| SC | 64 | 1.2 at every offset |
| WEXT | 320 | 1.3 at 64..383 |
| I | 32 | yes |
| POLL | 32 | yes |
| S | 32 | yes |
| STATS | 512 | word map 0..127 contiguous, no overlap |
| chunk header | 20 | yes |
| FILEHDR fixed part | 40 | yes |
| block header | 8 | yes |
| UHB | 64 | 16 named fields |

The failure is in the framing, see F2. 10.2 accepts a chunk only if
`len ≤ 65,536`. 4.3 steps 1 and 7 build "one RECS chunk" per flush from
everything drained, with no bound. 4.2 claims "Nothing is lost if the gap is
under 114 s", which means draining up to 626,688 B in one tick. The static
buffer that must hold it is unspecified. The decoder as specified would
reject such a chunk and advance 4 bytes at a time past it.

---

## 2. D2: independent coverage derivation (from the record format only)

Derived from DESIGN 1.2-1.8 and the source. The designer's section 6 was
not used to build this. It was compared afterwards.

| Row | What the recorded fields would contain | Confusable with | Separable by |
|---|---|---|---|
| H0 | No pattern below. Full P/POLL/W/I/S/M streams + STATS/KMSG/PROCS remain | – | Raw data is the evidence |
| H1 (no ACK) | P33/P08 persistently: `ret −4`, `ack_polls 1,000,001`, `nwords 0`, `rx` 16×`ff`, `dtick ≥ ~12`, large `c_out−c_in`; or `ret −3`, `drain 0xFFFF`, `ack_polls 0xFFFFFFFF`, `spi_st9 = spi_sttx = 0`. POLL `ri_branch 3`, `period ≫ 14`. I records 4 per command, `i_suppressed` rising. hist words 39/40, 47/48. W: pure H1 → W `ret −4` and `c_pre`/`long_ticks` large (IRQ-off timeout); 9.5 variant → W `ret ≥ 0` | (a) H4 at P2/P3/P4/P5a (single −4); (b) **H8 in an unread register** | (a) persistence and `wn`; (b) **not separable**: captured values would be unchanged. Reported "H8 unresolved" (declared) |
| H2 | P08 `ret 0`, `nwords ≥ 1`, `rx[0]=00`, `rx[3..6]=00` (checksum skipped since `result=0`, `syscon.c:226`). POLL `ri_branch 4`, `jp_r4` +1/poll, no delivery | Real HOLD switch; partial-zero frames | Real HOLD: only raw bit 13 clear, `rx[0]` = status ≠ 0, valid checksum (C0/D7 reference). Partial frames: unclassified → raw |
| H3 | P08 `ret 0`, `nwords 0`, `rx` 16×`ff`, `ack_polls` in healthy range. POLL `ri_branch 5`, dedupe after first. In mouse mode POLL `dx=+16, dy=+16` every poll (`joypad_psp.c:690`) | H4 one-off E3 (P3/P4/P5a/P5b); H8-unread (RX path) | Persistence + `wn`; H8-unread not separable (declared) |
| H4 | WT record (`tick ≡ 0 mod 1250`) with `t_busy` b0, `p_head` = seq of a P record with `wn ≥ 1`. W `epc` (if `ext_flags` b4) → step via epcmap; else step from that command's first I record. W's own `ack_polls/drain/drain_last/rx/ret` show what the Nop consumed. Damage visible in following P records; onset at that poll or next | H10; N8 (`pdflush` 5 s); N1; coincidence | W vs S record as interrupter; `kupd_last_tick`; `ms_delta`; benign-interleave base rate from all W records. Step resolution needs the first I sample of a command (cap 4). Adequate for short commands |
| H5 | Persistent `ret −5` with `retries 16`, `rx[2]∈{80,81}`; or `ret −2` with `rx[1]<3`, or checksum recomputable from `rx` fails, or `rx[1] ≥ 16` (OOB) | H4 at P2/P6 (one −2); N2 framing shift (can also yield −2); H8-unread | Persistence; N2 by `drain>0` and `rx` echo; H8-unread not separable (declared) |
| H6 | P08 `ret>0` = `rx[0]`, checksum valid, `rx[3..8]` byte-identical through D1-D7; POLL dedupe every poll. C0 shows the same presses changing the named bits | H7; operator not pressing | Raw bits follow presses (H7) or not (H6). "Not pressing" only by operator notes (P6 photographs the screen, not the finger) |
| H7 | `rx` follows presses. Delivery halts at a stage visible in POLL `pi_flags/nqueues/push_*`, `mouse_flags`; stats `fop_read_ret`, `md_*`, `vcs_*`, `console_sem`, POLL `sig` | H9 (if thread stops), N6 | P/POLL continuing excludes H9. N6 is a sub-case by construction (daemon side of H7(b)/(c)) |
| H8 | Captured values (`gpio_in` low 16, `spi_st9`, `spi_sttx`, `drain`, `drain_last`, `ack_polls` distribution, `led_last_rd_*`) leave the healthy range after onset | H1/H3/H5 when the change is in an unread register | Only through captured values. Otherwise blind (declared, forced by D11 and dossier 9.1) |
| H9 | P and POLL stop; W continue with fixed `jp_loop`, `jp_stage` 11 (arg = Q) or 9; stats `qfree_stage 2`, `qfree_queue = Q`, `fop_release` +1, `jp_state 1`; PROCS shows `psposk2` exiting | N4 (stage 7/8), N5 (stage 15/16, state 0), N9 (`t_busy` set) | `jp_stage`/`qfree_stage`/`t_busy` |
| H10 | P record `ms_delta>0`, `ms_b3>0`, `preempt_delta>0`; overlapping S record with `flags` b4/b5 and b2/b3; I record with thread step in S13..S20 then I records with `current ≠ thread`; run-wide `led_rd_*_b3` | H4; N1 | S vs W as interrupter; `ms_delta = 0` for N1. **Additional variant** not in the designer's rule: an LED-set RMW reading back bit 3 while **no** command is in flight would raise G3 outside a transaction. That shows as `led_rd_set_b3 > 0` / S `flags` b2 with `t_busy = 0` (F10) |

**Confusable after all fields are used:**
1. H8-in-unread-register against H1, H3 and H5. Declared. Unavoidable
   without hardware documentation.
2. H6 against "operator did not press". Only the operator's notes separate
   them.
3. H7 against N6 overlap by definition, which is not a defect.

**Agreement with the designer's matrix:** the rows and separators match
mine. Two points go beyond it: the H10 out-of-transaction variant (F10), and
the early-death case, where no healthy template or C0 exists (F11).

---

## 3. Budget arithmetic, recomputed

| Quantity | Design | Recomputed | Note |
|---|---|---|---|
| Polls/s | 17.86 | 250/14 = 17.857 | `msleep(50)` = 14 jiffies (recon/input §4) |
| P B/s | 2,286 | 35.71 × 64 = 2,285 | |
| POLL B/s | 571 | 571.5 | |
| W, I, S B/s | 77, 288, 416 | same | I and S rates UNVERIFIED (declared) |
| RECS/STATS/UHB/PROCS B/s | 296/579/365/337 | 296/580/365/337 | PROCS uses 620 B per chunk: **low** (F9) |
| Payload | ≈5.2 KB/s | 5,215 B/s = 1,199 B/flush | |
| Padded | 1,536 B/flush | (1,199 + 20 PAD hdr) → 1,536 | |
| Total | ≈6.7 KB/s | 6,682 B/s | |
| 15 / 30 min | 6.0 / 12.1 MB | 6.01 / 12.03 MB | |
| Kernel rings | 626,688 B | 262,144 + 65,536 + 98,304 + 131,072 + 65,536 + 4,096 = 626,688 | |
| Ring spans | P/POLL 114.7 s, W 1,280 s, I 455 s (80 s at 51/s), S 157 s | identical | |
| H1 command rate | 12.8/s | 2 / (0.05 + 0.05 + 0.056) = 12.8 | Assumes −4 = 50 ms (UNVERIFIED lower bound) |
| RAM share | ≈3 % of 20.8 MB | 0.627/20.8 = 3.0 % | `kmsg.txt`: 32 MB RAM, telem MemFree 20,832 KB |
| First flush after boot | not stated | ≈3.6 KB per second of backlog → 64 KB after ≈18 s of thread uptime before the collector starts; a 114 s restart backlog ≈ 626 KB | F2 |

With PROCS at a realistic ≈1.3 KB (five `/proc/<pid>/stat` lines of ≈200-260
B, reviewer estimate, UNVERIFIED), the payload is ≈5.6 KB/s and the total is
≈7.1 KB/s, ≈6.4 MB per 15 min. That does not matter for the stick, but it is at the edge of
Stage 3's ±10 % tolerance (8.5).

---

## 4. Source citation check

Every citation below was opened and read. "OK" means it resolves and says
what the design claims.

| Citation(s) | Result |
|---|---|
| `syscon.c:10,12-13,61-75,92-93,102,104,106-117,119,121,130,136,140,151-156,159,201-217,219,222,226-246,249-255,257`; `:63` `volatile u16 dmy` | OK |
| `syscon_tree.o.dis` offsets `+0x0` frame 48, `+0x38..+0x74` bases, `+0xdc..0xe4`, `+0xfc`, `+0x110..0x11c`, `+0x124..0x128`, `+0x14c..0x154`, `+0x168..0x174`, `+0x190..0x1a8`, `+0x1dc..0x1e8`, `+0x20c`, `+0x2ac` | OK. RX `ptr` is `a3` biased by +2 (`+0x244 move a3,t9`, `t9=a1+2`). Harmless; the regmap is regenerated at Stage 2 |
| `psp.c:32-41, 96-97, 135, 151, 204-223, 254-263, 265-279, 348-368, 370-381, 383-397, 399-407, 429, 554-576, 591-596, 637-654` | OK |
| `genex.S:162-169, 166-167, 266-267`; `entry.S:39, 45-48, 61-73` | OK |
| `thread_info.h:37`; `ptrace.h` regs[32]; `mipsregs.h:789, 810`; `head.S:182-187`; `sched.h:907`; `sched.c:3626-3628` | OK |
| `joypad_psp.c:40,49,52,58,195-197,219-250,295-329,346-360,384-411,453-472,474-496,498-540,593-659,663-694` | OK. Minor: row H6 cites `:35` for D-pad RIGHT (it is `:37`; `:35` is a comment) |
| `ms_psp.c:92,119,228-236,254,284-326,328-353,355-379` | OK; only `psp_ms_read/write` reach the sector functions (`:131,260,264`) |
| `mm/page-writeback.c:80,433-473,449,453,469-472,585`; `init/main.c:568,573,628` | OK |
| `fs/fat/file.c:136`, `fs/sync.c:55-76`, `fs/proc/kmsg.c:36` | OK |
| **`fs/fat/inode.c:453-459`, `fs/fat/fatent.c:479,500,548,611`, cited for "FSINFO is written only when the superblock is dirty" (5.2, 12.2 F1)** | **WRONG CONCLUSION.** `file_fsync` calls `write_super` unconditionally (`fs/sync.c:67-68`). `fat_write_super` (`fs/fat/inode.c:453-459`) clears `s_dirt` and calls `fat_clusters_flush` without testing it. On FAT32 that function `sb_bread`s FSINFO and `mark_buffer_dirty`s it every time (`fs/fat/misc.c:40-72`, `:69`). `sync_blockdev` then writes it. **FSINFO is rewritten on every `fsync`.** Candidate B's count was right. See F3 |
| `vc_screen.c:562-590`; `mousedev.c:228,304`; `input.c:651-663`; `printk.c:67`; `process.c:441-465`; `array.c:167,275-279`; `vt.c:174`; `jiffies.h:137`; `.config:64,109,163` | OK. Minor: `mousedev.c:629` is cited as "successful return" but is the function start (the return is `:659`) |
| `extract/root2/etc/rc.sysinit:10,14,17-19`, `etc/inittab`, `dev/null`, busybox has no `sleep` | OK |
| `telem.c:54, 235-245, 249-306, 326, 357, 367-373, 415`; `telem/logs-from-stick/kmsg.txt` | OK |
| `fb_write` path of the blit | Not cited by the design. I checked: `pspfb.c:68` `.fb_write = fb_sys_write`, which takes no console semaphore, so the HUD blit is not coupled to H7(d) |

---

## 5. Runbook read as an operator who has never seen the code

1. **D7 "Slide the HOLD switch on" (also in C0).** On a PSP-1001 the HOLD
   position and the power function are one slider (POWER/HOLD). The
   never-press table forbids "the power switch". The runbook gives no
   direction. Pushed the wrong way during C0, the PSP may power off or
   suspend (behaviour under uClinux UNVERIFIED) before any death. The abort
   rule does not cover that case. F4.
2. **D8** reads `SYNC AGE`/`TMAX` without first requiring the heartbeat to
   be alive, and line 180 applies D8 to a frozen display. F1.
3. **B abort rule / exception.** It is correct for "BTN only fails". An early
   death in H1, H3, H5 or H9 shape fails POLL instead. The operator is then
   told to power off and report, with no section D and no instruction to
   keep and return `PSCLOG`. F5.
4. **A2** makes the checksum check optional ("If the release notes give a
   checksum"). G3 R3 needs it. F13.
5. **E1** will image a 118,999 MB device (`kmsg.txt` "Adding disk ms0
   118999M"). That needs about 119 GB free on the Mac and a long time, and
   the runbook states neither. Inserting the stick auto-mounts it before step
   3 unmounts it. macOS may write to the volume, and may repair a dirty FAT
   without asking (UNVERIFIED). "If the computer offers to repair, decline"
   may never apply. F6.
6. **"Before you start"** asks only about buttons. R18 also names AC versus
   battery for the 9.6 sessions, and the run forces battery. F14.
7. **Free space ≥ 128 MB** is listed under "What you need", but no A step
   checks it. The on-device check does it by `statfs`, which may be slow.
   F7.
8. Every other step is unambiguous: a time and an action, with photograph
   numbers and a timing summary.

---

## 6. Attacks attempted

| # | Attack | Outcome |
|---|---|---|
| A1 | Does any capture add an instruction between S5 and S20? | No. Baseline patterns confirmed in `syscon_tree.o.dis`; G2 criteria and fallback order are stated (2.1) |
| A2 | Is WT context identified wrongly because `in_interrupt()` is 0 in the Nop? | No: explicit flag, both call sites enumerated by grep |
| A3 | Can `current_thread_info()->regs` be stale in the W extension? | No: `genex.S:166-167` sets it on entry; bounded copy |
| A4 | Thread preempted mid-command, Nop lands while another task runs: is the step lost? | No: the first in-flight I sample is the preempting tick with `current = thread`. Cap-4 loss only for commands that already straddled 4 ticks |
| A5 | Torn ring slot when the collector preempts the thread mid-fill, or IRQ interrupts the reader | Rejected by `seq` (slot is `0xFFFFFFFF` and head not advanced) |
| A6 | Wrong button bit makes BTN fail on a healthy PSP → operator takes the "early death" branch and spends the run | Checked: TRIANGLE 0x10 = `rx[3]` b4, active-low. Correct |
| A7 | Is the watchdog boundary really `tick ≡ 0 mod 1250`? | Yes, `psp.c:372-379` |
| A8 | Budget arithmetic and ring spans | All recomputed; correct apart from the PROCS estimate (F9) |
| A9 | Writer stalls in `fsync` at death | **Breaks D6** (F1) |
| A10 | First flush after a late collector start, or restart after a 100 s gap | **Breaks the chunk spec** (F2) |
| A11 | LED/sector exposure claim versus the vfat `fsync` path | **Citation conclusion wrong** (F3); direction of the H10 argument unaffected |
| A12 | Death at 17 s in H1/H3/H5/H9 shape | Data kept, but the runbook sends it down the abort path (F5); decoder template undefined (F11) |
| A13 | `statfs` on a 118,999 MB FAT32 volume at collector start | May trigger a full FAT scan (`fs/fat/inode.c:540-541`), UNVERIFIED (F7) |
| A14 | Does the HUD blit take the console semaphore and couple the writer to H7(d)? | No: `fb_sys_write` |
| A15 | pspboot load size | BSS growth is harmless: `_end` goes from `0x881b6230` to ≈`0x88253000`, far below 8 MB. Image growth is understated (F8) |
| A16 | LED-set RMW raising G3 when no transaction is in flight | Recorded, but no classification rule reports it (F10) |
| A17 | Reader reads 64-bit `total_counts` while the timer updates it | Can tear (F12) |

---

## 7. Findings

Each finding says what closes it. F1 and F2 are gate-failing. The others
must be addressed or answered in the revision. None of them alone would fail
the gate.

**F1. D6 (blocking FAIL).** The ≤ 5 s loss bound is enforced by reading HUD
values that the writer draws. A stalled writer freezes them at a benign
value. DESIGN 4.5's "SYNC AGE rising" cannot happen. On a live HUD `SYNC AGE`
is ≈0 by construction. RUNBOOK D8 and line 180 do not require liveness
first. The stalled-writer loss is not stated in seconds. **Closes when:**
- (a) RUNBOOK D8 and C4 require the operator to watch the heartbeat block
  for ≥ 5 s and see it change before reading the MS line. If it does not
  change, the operator notes the freeze time, waits a stated time
  (≥ 90 s, since the rings hold 114 s) for it to resume, and pulls only after
  a live `TMAX ≤ 2.5 s` reading or after the stated maximum wait.
- (b) DESIGN 4.5 drops the "SYNC AGE rising" claim. It states the
  stalled-writer case explicitly: the loss is everything after the last
  completed `fsync` before the stall, the operator-noted freeze time bounds
  it, and the kernel rings keep it only if the writer resumes within
  ≈114 s. It gives the reason this is acceptable.
- (c) Recommended: a liveness and kernel-state indicator that does not
  depend on the writer. For example, the supervisor draws a small band with
  its own heartbeat, `now_tick − last_reader_tick` from `/proc/psc/stats`
  and the key counters. A stalled writer then shows as "WRITER STALLED nn s",
  and photos P5-P7 still carry kernel state.

**F2. D20 (non-blocking FAIL).** Chunk `len ≤ 65,536` (10.2) conflicts with
"one RECS chunk" per flush (4.3). The drain has no size bound and the flush
buffer size is unspecified. The 114 s restart claim (4.2) needs up to
626,688 B in one flush. A collector starting more than ≈18 s after the
joypad thread already exceeds 64 KB on its first flush, and that flush is
where an early death's history lives. **Closes when:** 4.3 and 10.2 specify
either:
- several RECS chunks per flush, each ≤ 65,536 B, with the flush buffer size
  stated; or
- a per-tick drain cap with catch-up over later ticks, and arithmetic
  showing that catch-up outpaces production before any ring laps (P 114 s).

Also, Stage 3 (8.5) must add a test with a full-ring backlog in the first
flush and after a simulated 100 s restart gap.

**F3. Citation error: FSINFO on every `fsync`.** DESIGN 5.2, 7.5, R9 and
12.2 F1 say FSINFO is written only when `s_dirt` is set. The code path is
`fs/sync.c:67-68` → `fs/fat/inode.c:453-459` → `fs/fat/misc.c:40-72` →
`mark_buffer_dirty` at `:69`. So on FAT32 every `fsync` rewrites FSINFO.
Corrected steady state:
- telem: ≈3 sector writes per tick, ≈13/s, ≈26 LED RMW/s.
- `pscol`: 3 data + directory entry + FSINFO ≈ 5 per flush, ≈21.8/s plus FAT
  on allocation, ≈44 LED RMW/s.
- The ratio is ≈1.7×, not 2×.

The direction of 7.5 (raises, does not mask) stands. **Closes when:** 5.2,
7.5, R9 and 12.2 F1 are corrected with these numbers or better ones. 12.2
F1's verdict becomes "B". Stage 3's `led_calls` expectation uses the
corrected rate.

**F4. Runbook: POWER/HOLD slider.** D7 and C0 say "Slide the HOLD switch
on" without a direction. On a PSP-1001 this is the same slider as power,
which the runbook forbids elsewhere. **Closes when:**
- D7 states "slide the POWER/HOLD switch DOWN until it clicks into HOLD;
  never push it UP";
- the never-press table names "pushing the POWER/HOLD switch UP";
- the abort rule says what to do after an accidental power-off before death.

**F5. Early death routed to abort (D4/D13 advisory).** In an H1, H3 or H5
death before PASS, P08 `ret < 0` or `nwords = 0`. In an H9 death, P stops.
Either way POLL fails. The exception in 8.3 and RUNBOOK B covers only "BTN
fails". Dossier 9.6 shows deaths before 36 s. **Closes when:** 8.3 and
RUNBOOK B treat "KRN, WDOG, CTX, STICK, REC pass but POLL and/or BTN fail"
as a possible early death, with the HUD showing which POLL condition failed.
In that case the operator runs section D. Every abort path also says "leave
the stick untouched and return `PSCLOG` with the report".

**F6. Runbook E1 (advisory).** The raw image of a 118,999 MB stick needs
≈119 GB free and a long time, and the runbook states neither. macOS mounts
the volume on insertion, before step 3, may write to it, and may run a FAT
repair without asking (UNVERIFIED). **Closes when:** E1 states the image size,
a free-space check and the expected duration. It also either gives a tested
way to stop the mount and repair, or states the residual risk and that the
fsync'd files in E2 are the primary evidence.

**F7. On-device `statfs` (advisory).** `fat_statfs` counts free clusters by
scanning the whole FAT when the FSINFO count is unknown
(`fs/fat/inode.c:540-541`, `fatent.c:586`). On this volume that is roughly
7-15 MB of FAT reads (cluster size UNVERIFIED) at collector start. It could
push PASS past 120 s. It would lap the S ring, which holds 2,048 segments.
It would also add a burst of LED RMWs that no 9.6 session had. **Closes
when:** the 128 MB check moves to RUNBOOK A (operator on the Mac) and 4.4
drops the on-device requirement, or the design states this risk and bounds
it.

**F8. Image growth understated (correction).** 5.3 and R21 say the image
grows only by ≈5 KB of code. The embedded initramfs also gains the `pscol`
bFLT (telem's is 12,076 bytes). **Closes when:** 5.3 and R21 give the
combined estimate, and G2 C6 checks it.

**F9. PROCS size (correction).** 620 B per PROCS chunk is low for five
`/proc/<pid>/stat` lines plus status and meminfo lines (reviewer estimate
≈1.3 KB, UNVERIFIED). **Closes when:** 5.1 is re-estimated from the 2.6.22
`/proc/<pid>/stat` format (`fs/proc/array.c`), or the Stage 3 volume test
tolerance is set from a measured line length.

**F10. H10 out-of-transaction variant (decoder rule, advisory).** A LED-set
RMW whose read-back has bit 3 set, while no command is in flight, would raise
G3 as a spurious request. It is recorded (`led_rd_set_b3`, S `flags` b2,
`led_last_rd_set`), but no section 6 rule reports it. **Closes when:**
section 6 and 10.7 add that signature near onset.

**F11. Healthy template for early death (decoder, advisory).** 10.7 step 2
learns the template from the 60 s after SELFTEST PASS. A death before PASS
has no such window and no C0 reference. **Closes when:** 10.7 defines the
fallback: the earliest records after thread start plus the source bit map
from `joypad_psp.c:36-58`. Section 6 H6 and H8 state what changes without C0.

**F12. Torn 64-bit stat (minor).** `total_counts` (1.8 words 10-11) is
written by the timer and read as two words by `/proc`. **Closes when:** the
reader uses a high-low-high retry, or the timer publishes a consistent
snapshot.

**F13. Runbook A2 checksum (advisory).** **Closes when:** the release note
and runbook carry the sha256 of `vmlinux-0.22.bin`, and A2 makes the check
mandatory (G3 R3).

**F14. Runbook "Before you start" (advisory).** **Closes when:** it also
asks whether the 9.6 sessions ran on AC or battery and in mouse mode (R18).
The design states what it does if the answer is AC.

**F15. Minor citation imprecisions.** Row H6 cites `joypad_psp.c:35` for
D-pad RIGHT (it is `:37`). 2.6 cites `mousedev.c:629` as the successful
return (it is `:659`). **Closes when:** both are corrected.
