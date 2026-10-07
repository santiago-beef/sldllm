# Instrumentation design for the PSP input-death run (synthesis for Gate G1)

Stage 1 design, Synthesis designer. **Revision 5, 2026-10-05, for G1 round 6**
(the human's pre-authorised fallback: **full scope**, Amendment A1 suspended,
every outstanding red-team fix adopted). Revision 3 (round 4) preallocated
fixed-size segment files and cut every mechanism not load-bearing (section 0);
responses to attempts 1-2 are in [DESIGN-history.md](DESIGN-history.md), to
attempt 3 in section 13, to attempt 4 in section 14 (both unchanged except
corrections marked r5). Revision 4 grew segments in confirmed steps, kept two
ahead and never overwrote a failed flush. **Revision 5** answers attempt 5
(section 15): every flush and creation step is judged from the Memory Stick's
own per-transfer records with the sectors mapped by `FIBMAP` (4.8, attempt-4
F1(b) and F4 in full), so a refusing FSINFO, directory or FAT sector no longer
stops recording; a kernel-reused inode is detected and never written (4.4 step
1); failed records are re-sent by range (4.6); a bad data region is escaped
(4.6); a throughput gate and a smaller start-up step bound the self-test time
(8.2, 8.3); runs are told apart by a boot nonce that seeds every chunk CRC
(10.2). Record sizes are unchanged; the UHB, FILEHDR and stats words 153-159
change, so the **format version is 5**. The operator procedure is
[RUNBOOK.md](RUNBOOK.md), regenerated. **Round 7 (closure only):** the text
needed to close A6-1 to A6-4 and red-team IF7b and TE10 changed, nothing else;
each change is listed in section 16. **Revision 7 (G1 ruling after G2 attempt
1, 2026-10-06):** only the text of the six items G2 routed back changed (R-1
`nwords`, R-2 the D10 wording, R-3 the costs outside the window, R-4
`build_id`, R-5 the memory and image figures, R-6 two stale figures); no
mechanism, record, field, check or runbook step was added. Each change is
marked **(§17 R-n)**; section 17 gives the ruling on each.

Inputs: the dossier, WORKFLOW, the four recon reports, the gate log and
reports, the candidates. Conventions: kernel paths are relative to
`/home/ubuntu/psp/build/linux`, only read. `[SRC]` = read in the source,
file:line given; `[OBJ]` = the recon disassembly of the tree's `syscon.o`
(`recon/scratch-2008/syscon_tree.o.dis`); `[BIN]` = a Recon D finding on the
2008 image. `fs/fat`, `fs/vfat`, `fs/buffer.c`, `fs/sync.c`, `fs/mpage.c` and
`mm/filemap.c` in this tree are byte-identical to vanilla 2.6.22 (`diff -rq`
against `/home/ubuntu/psp/ksrc/linux-2.6.22`: only build outputs differ);
every vfat claim was checked in this tree. **UNVERIFIED** marks what the
source cannot settle; each is listed in section 11. "Thread" is
`psp_joypad_thread` (`drivers/input/joypad_psp.c:453-472`); "Nop" is the
timer-interrupt `pspSysconNop()` (`arch/mips/psp/psp.c:379,392`); steps S1-S23
and points P0-P7 are those of recon/syscon.md §1.2, §5.1. No kernel code is
written in this stage; code fragments specify behaviour for Stage 2.

---
## Summary (not a numbered section)

1. **Nothing is added inside the syscon transaction** (S5 to S20); values the
   code already loads into `dmy`, and its spin counters, go to stack slots.
   **(§17 R-2)** The window keeps the baseline's instruction count, its MMIO
   loads and stores in the same order and form, its loop bodies and branch
   structure, with no call, global load or base reload. The compiler may move
   stack slots, rename registers consistently and change an exit branch's delay
   slot after the exit decision. The test is the criteria of 2.1, not literal
   identity (7.2).
2. **Records:** an 80-byte SC record per `Syscon_cmd` call in every context
   (raw `rx_buf`, `ret`, words, retries, captures, entry/exit time, Nops
   during it, the thread's last interrupted instruction `lc`, the LED
   read-backs); a 288-byte W record per Nop with the interrupted context; a
   40-byte POLL record per thread loop (delivery, mouse, signal, wake-up delay
   and who held the CPU); a 40-byte S record per Memory Stick transfer; a
   768-byte stats block. Context is an explicit flag, not `in_interrupt()`.
   Time is the watchdog's own tick plus CP0 Count, so every Nop is at tick
   ≡ 0 (mod 1250) and phases are exact (6.3).
3. **Everything is streamed; no trigger, no freeze.** `pscol`, started from
   `rc.sysinit`, drains five rings every ≈ 0.23 s, appends a sector-aligned
   CRC-framed flush, `fsync`s it, **(r5)** judges it from the S records of its
   own data sectors (4.8) and tells the kernel how far it is durable.
4. **2 MB segments grown in confirmed PAD steps**, two kept ahead; a flush
   writes only below a file's confirmed size, so **it never allocates a cluster
   or dirties a FAT sector** (4.4); a failed flush is never overwritten and its
   records are re-sent by range (4.6); **(r5)** a refusing FSINFO, directory or
   FAT sector is shown as `META` and recording continues (4.7); a bad data
   region is escaped (4.6); vfat read-only shows as `MS RO`.
5. **A kernel stall panel** in the bottom third of the screen, which only the
   kernel writes, shows the durable age and kernel state whenever the stick is
   > 3 s behind, the collector stopped reading, or vfat is read-only.
6. **The supervisor becomes the worker** if the worker dies or stalls 30 s: no
   `exec`, no allocation.
7. **Budget (5):** ≈ 7.6 KB/s of records (6.8 MB in 15 min), written once more
   as preallocation; ≈ 653 KB of kernel BSS; **(§17 R-5)** two 256 KB `pscol`
   blocks, both at boot; **(§17 R-3)** ≈ 2.1-2.8 µs per thread command outside
   the window (≈ 460-610 instructions, objdump), 0 inside. **Worst-case loss at the pull: 4 s** when the
   final check passes, else the `DUR` the panel shows. **(r5)** A stick slower
   than 30 KB/s fails the self-test (no run lost); from 28 KB/s up the model
   loses nothing under the sporadic error pattern, and at 25 KB/s 1 run in 260
   loses 15 s (15.6).

---
## 0. Traceability: every mechanism, what it is for, what it costs

**For** names the D items, gate scenarios (A1/A2/A3 = attempt-1/2/3 red team;
F1-F15, F-A..F-H, N-1..N-5 = attempt-1/2/3 review findings) and S1-S5 that
depend on it; **Cost** is bytes, instructions per event and rough Stage 2
lines. A mechanism not load-bearing for a blocking D item, a BLIND/AMBIGUOUS
scenario or S1-S5 is CUT, and the row says what it once closed and why that
does not reopen.

### 0.1 Kernel

| # | Mechanism | For | Cost | Decision |
|---|---|---|---|---|
| K1 | SC record core: `seq`, (tick, Count) in/out, `cmd`, `txlen`, `ret`, `nwords`, `retries`, `rx[16]` (1.2) | D1, D3, D14, D16; H1-H6 rows; 6.3 | 52 B/record; **(§17 R-3)** ≈ 60 instr before S5, ≈ 400-550 after S20 (objdump, 5.4); ≈ 120 LOC with the ring | KEEP |
| K2 | In-window free captures `ack_polls`, `drain`, `drain_last`, `gpio_in`, `spi_st9`, `spi_sttx` (2.1 A3) | D14 (−3/−4 sentinels), H8, H4 P4/P5a split | 12 B; **0 instr in the window** (slot substitution); ≈ 20 LOC | KEEP |
| K3 | Explicit watchdog context flag + `ctx` byte (1.8, 2.2) | D8, dossier 9.1, WDOG self-test | 1 B; ≈ 6 instr; ≈ 15 LOC | KEEP |
| K4 | `wn`, `w_head_lo` (Nops during this command) | D8, H4, 6.3 | 3 B; ≈ 10 instr | KEEP |
| K5 | `preempt_delta` (`nivcsw` delta) | H10, N1, N1m (A3 UL5) | 1 B; 4 instr | KEEP |
| K6 | LED hook: per-command `led_or`, `led_pid`, `ms_delta`; run-wide OR per register (2.4) | H10, A1 UL1, A2 TE4, A3 UL5 | 7 B/SC, 2 stats words; ≈ 25 instr per LED operation; ≈ 40 LOC | KEEP |
| K7 | LED per-bit counts (16 words), AND accumulators, bit-3 counters `ms_b3`/`led_rd_*_b3` | "whole-run per-bit data" in the H10 report only | 20 words, ≈ 15 instr per LED op | **CUT.** Was part of the A1 UL1 fix; UL1 is carried by the OR values (`led_or`, S `rd_*_or`), which show every bit that was ever read back. No rule used the ANDs or counts |
| K8 | `lc` overwrite words (T2a, uncapped): the thread's EPC, registers and tick at the last tick it was running in a command; copied into SC (`lc_*`) and W (1.2, 1.3, 2.3) | A1 TE2 (AMBIGUOUS→closed), A2 TE4, H10/N1/N1m step, D8 | 8 B/SC, 92 B/W; ≈ 30 instr per tick that finds the thread running in a command; ≈ 60 LOC | KEEP |
| K9 | Nested-tick test (`preempt_count()` masks, 2.3 T2a) | A2 TE4 (AMBIGUOUS→closed) | ≈ 3 instr; ≈ 10 LOC | KEEP |
| K10 | I ring: capped per-tick in-flight samples (T2b, `i_suppressed`, SC `ni`/`i_head_lo`) | was supporting evidence for TE2, H1, N9 | 131 KB BSS; ≤ 1.6 KB/s on the stick; ≈ 45 instr per sample; ≈ 70 LOC + decoder | **CUT.** TE2 has been closed by K8 since r1 (the I cap was its cause); TE4 by K8+K9 (the I nested flag was supporting only). D8 stays met: a tick during a command shows as `dtick`, the ticks that found the thread running as `lc_n`, a Nop as `wn` + W, a preemption as `preempt_delta`. The OE6 recommendation that wanted an I flag goes to SC `lc_flags` b5 (K32) |
| K11 | T2c per-tick wait-class sampling (`wait_ticks/cls/pcnt`, `wait_hist[16]`) | A1 OE3 fix, superseded in r2 by K12 | 3 B/POLL, 18 words; ≈ 20 instr per tick | **CUT.** A2 OE3 was rated AMBIGUOUS *with* T2c present and closed by K12. K12's delay range is widened to 76 ms (19 ticks), so it also covers the multi-tick waits T2c counted; longer stalls show as POLL `period`; the raised-preempt-count part comes from overlapping S records (A2 OE3 response, kept) |
| K12 | Scheduler hooks at wake-up (`kernel/sched.c:1657`) and switch (`:3700-3707`); POLL `wk_*` (2.11) | A2 OE3 (AMBIGUOUS→closed), 7.3 no-death inference (S5) | 8 B/POLL, 2 stats words; one compare per wake-up, one load per switch, ≈ 25 instr per thread wake-up and ≈ 15 per switch while it waits; ≈ 45 LOC | KEEP, **simplified**: no 8-class accumulator array or share computation; per wait it keeps the delay, the part the collector held the CPU, the class at wake-up, the last holder's class and the switch count. That is what A2 OE3 asked for ("delay, longest holder, `pscol` first"): with one holder the last holder is it; with several, the collector's part is measured exactly |
| K13 | T1 tick length (`c_pre`, `total_counts`, `c_pre_max`, `long_ticks`) | D16, 6.3, wall time | 4 words; ≈ 8 instr per tick | KEEP |
| K14 | W extension: interrupted EPC, Cause, Status, `ra`, `sp`, registers 2-15, 24, 25, thread context words (1.3) | D2 (H4 step), D8, P2 k / P6 j, A3 TE5 | 208 B per Nop (0.2/s); ≈ 110 instr with IRQs off | KEEP (registers reduced from 32 to the 18 the maps use) |
| K15 | W 128-byte stack snapshot `stk[32]` | none: it held `dmy` and the spin counters of a running thread | 128 B/W; ≈ 40 instr | **CUT** (brief candidate). How long the interrupted command had waited is `W tick − t_entry_tick`; its final spin counts are in its own SC record; k and j come from registers. No scenario cited it |
| K16 | W copies of other heads, `ms_ip_*`, `durable_tick`, `last_reader_tick`, `cur_pc_hi` | none | 40 B/W | **CUT.** The stats carry them; the W flags keep "MS transfer in progress" (b6) and "nested" (b7) |
| K17 | POLL core (branch, `pi_flags`, pushes, mouse, `dx`/`dy`, `sig`, `period`, stage) (1.4) | D15, H3, H7, N10 (A1 UL2) | 32 B per poll; ≈ 60 instr; ≈ 80 LOC | KEEP |
| K18 | Thread stage codes and `jp_stage_arg` (2.5) | H9, N4, N5 | ≈ 2 instr per stage | KEEP |
| K19 | S record per Memory Stick segment (1.5) | H10, N8, A1 UL1, A3 UL5 | 40 B (ANDs cut); ≈ 50 instr per segment | KEEP; **(r4)** `flags` b7 added (K36) |
| K20 | MS in-progress marker (2.4) | A1 OE1 (BLIND→closed) | 3 words | KEEP |
| K21 | M ring (other thread callers) | D8, H8 baseline (A1 TE1) | 5 KB; reuses the SC code | KEEP |
| K22 | Stats block (1.7): outcome counters per command and context (21 words), thread, fops, queue-free, vcs, mousedev counters | D1 (whole-run summaries), D14, D15, H7, H9, N4 | 768 B (was 1024) | KEEP; the counters replace the 32-word histograms (same seven outcomes for P08, P33 and W; the M histogram is dropped: M records are kept whole) |
| K23 | `pdflush` `wb_kupdate` hook | N8 | 2 words; 2 instr per 5 s | KEEP |
| K24 | `mousedev_open/release` counters | A2 OE5 recommendation (DIAGNOSABLE without it) | 4 words; 2 hooks | **CUT.** OE5 was rated DIAGNOSABLE before the counters existed; a collector exit is already in the timeline as an EVENT or a takeover |
| K25 | `do_exit` hook clearing `psc_jp_task` | correctness of K12 and the stats reader if the thread ever exits (A2 OE5) | 1 compare per process exit | KEEP |
| K26 | Kernel guard words, checked once a second | A2 OE4 (AMBIGUOUS→closed) | 7 words; 7 compares/s | KEEP |
| K27 | `/proc/psc` ring files: offset = `seq` × size, `llseek`, `head_regress` (2.8, 3.5); **(r4, A4 IF3)** the collector resyncs a ring to its head on a `head_regress` rise; **(r5)** positioned reads (`pread`) for the S windows of 4.8 | D4, D6, A1 IF1/IF2/IF3, A4 IF3 | ≈ 150 LOC; resync ≈ 5 LOC in `pscol` | KEEP |
| K28 | **(r3)** Reader skip-and-count (`slot_bad`), complete-drain definition (3.5, 4.3) | A3 IF6 (AMBIGUOUS) | 5 words; ≈ 10 LOC | NEW |
| K29 | `ctl`: durable point, pid classes, panel test (2.8) | D6 (A1 F1, A2 F-A), K12 classes, PANEL self-test | 32-byte commands; ≈ 40 LOC | KEEP; op 4 (`seg_cur`) **CUT** with U7; **(r4)** op 4 reused for META (U20); **(r5)** META no longer paints the panel (shown in its line 6 field only) |
| K30 | Kernel stall panel (2.10) | D6 (A1 F1, A2 F-A, blocking), A1 OE1 (BLIND), IF5 fix 2 | ≈ 46,000 pixel stores per paint; ≈ 250 LOC | KEEP, **simplified**: the bottom band is the kernel's alone (the collector never writes it), so the r2 "spare the panel rows" rule and its race are gone; the kernel clears the band when its condition ends |
| K31 | **(r3)** vfat hooks: `fat_fs_panic` counter, `MS_RDONLY` bit, panel `MS RO` (2.12) | A3 IF5 fix 2 | 3 words; 2 one-line hooks | NEW |
| K32 | **(r3)** Panel-paint flag per command (SC `lc_flags` b5) and `panel_cost_last` | A3 OE6 recommendation; N1p rule | 1 bit, 1 word | NEW |
| K33 | Out-of-bounds checksum recomputation (`ck_calc`, `ck_rx`) | an A2 note, not a scenario | 2 B/SC; up to 256 loads | **CUT.** The note's substance (the stack above `rx_buf` changed, so which corrupt long frame passes by chance changes) is stated in 7.1; every such acceptance stays visible as `ret > 0` with `rx[1] ≥ 16` |
| K34 | Boot `printk` `PSC5 ...` (2.8; **(r5)** format version 5) | D13 | one line at init | KEEP |
| K35 | **(r4)** Hook S preemption branch: who held the CPU while the thread was preempted inside a command, published into SC bytes 42-43, 44 and 46, and 78-79 (`pre_wrk`, `pre_cls`, `pre_flags`, `pre_tot`; byte 45 is `ms_delta`, A5-4) (2.11) | A1-OE3 (reopened in A4, AMBIGUOUS), N1, N1m, H10 actor, S5 | 0 B (reserved bytes), 3 stats words; 1 compare per switch, ≈ 15 instr per switch while preempted; ≈ 25 LOC | NEW |
| K36 | **(r4)** S `flags` b7: the transferred page belongs to the block device's page cache (FAT, FSINFO, directory) (2.4) | META (4.7); **(r5)** sector classes and verdicts (4.8) | ≈ 6 instr per MS segment; ≈ 8 LOC | NEW (r4) |
| K37 | **(r5)** Geometry words, stats 153-159: partition start from the driver's table, FAT start, length, count, FSINFO sector, data start, cluster size and block-size shift from `fat_fill_super` (2.4, 2.12) | A4 F1(b) and F4 (sector classes, FIBMAP → S-record sector), A5 IF7, IF8 diagnosable (4.8) | 7 words; 7 stores at mount, 1 at driver init; ≈ 12 LOC | NEW |

### 0.2 Collector `pscol`

| # | Mechanism | For | Cost | Decision |
|---|---|---|---|---|
| U1 | Supervisor that **becomes the worker** on death, stall or guard exit (4.2) | A1 IF2 (BLIND→closed), A2 OE4, D7 | ≈ 80 LOC; one block of the worker's size at boot (**(§17 R-5)** 256 KB, 5.3) | KEEP, **changed** |
| U2 | Pre-spawned standby worker, pipe protocol, standby respawn with `drop_caches`/`buddyinfo` logging | A1 IF2 | a third process (128 KB), ≈ 150 LOC | **CUT** (brief candidate). IF2 was BLIND because a restart needed a large contiguous allocation late in the run. U1 gives the same first recovery with **no** allocation: the supervisor already holds a block of the worker's size (same binary), allocated at boot, and runs the worker loop in-process. The standby design's second recovery needed a 128 KB allocation that could fail (old R28); revision 3 does not attempt one, and in both designs the fallback after that is the kernel panel |
| U3 | Capped per-ring drain with the time multiplier `m` and catch-up (4.3); **(r4, A4 IF3)** `head_regress` resync with EVENT and REC red | D4, A1 F2, A4 IF3 | ≈ 65 LOC | KEEP |
| U4 | Durable point (`durable_tick`, `durable_next[5]`) reported through `ctl` (4.3, 4.5) | D6 | one 32-byte write per flush | KEEP |
| U5 | **(r4)** Failed flush: never overwritten (`seg_end` passes it). **(r5, A5 IF4 G2)** its records are queued by `seq` range and re-sent after the next DURABLE flush; a success is durable for its own records (4.6) | A1 IF1, A2 IF4, A3 IF1/IF4/IF5, A4 IF7, A5 IF4 | ≈ 60 LOC (range queue ≤ 32 entries) | CHANGED (r4 discarded the first success after a failure and re-sent everything since) |
| U6 | 2 MB segments grown in confirmed steps: flushes use any file's confirmed prefix; failed steps retried in place unless a FAT1 write failed; two kept ahead; cap on counted bytes; `fstat` and read-back (after a one-page `fadvise`) at completion. **(r5)** step verdicts from S records with FIBMAP extents (4.4 step 4, 4.8); the alias test after every `open` and the alias `fsync` (A5-1, 4.4 step 1); step 0 strict; 64 KB steps only while room < 81,920 or holding (A5-3); one next-attempt rule (fast if any write in the window succeeded, ≤ min(400, budget/2) per run, else ≥ 10 s); names budget from the free directory slots (4.4); after vfat read-only, no creation step: flushes go into the files already prepared, then the worker holds (2.12, 4.6) | A3 IF5, IF1, IF4; A4 IF4, TE6, IF8, F1(b), F4; A5-1, A5-3, A5 IF7/IF8 | creation writes each segment once more (≈ 8.8 KB/s average, 5.2); ≈ 220 LOC | CHANGED (r4: verdicts from `fsync`, allocating/non-allocating proxy, no alias test, 64 KB steps for the whole first file) |
| U7 | r2 segment rules: 9,999 names, monotonic `seg_cur`, rotation after three failures at most once per 5 s, FILEHDR as its own flush, `SEG FULL` | A2 IF4, A2 F-C, F-D | ≈ 80 LOC | **CUT/replaced** (brief candidate). With preallocation a rotation is a switch to a ready file (no metadata write). **(r5 figures, A5-4)** Names per run: `min(999, free directory slots − 16)`, ≥ 400 by the self-test (a fresh `PSCLOG` has 494 at 16 KB clusters, 1,006 at 32 KB); at most half of them as fast attempts (≤ 400), the rest ≥ 10 s apart: ≥ 200 × 10 s ≈ 33 minutes of whole-stick refusal before the names run out, longer than the run could record through anyway; a whole-stick outage costs one name per 10 s (4.4 step 1). FILEHDR is written by the creation itself at offset 0 (F-C's bound holds: no flush contains a FILEHDR) |
| U8 | Volume cap and "summary mode" | 3.3 (r2) | ≈ 20 LOC | **CUT.** Replaced by the cap on confirmed bytes (64 MB, ≈ 2.3 h at the section 5 rate, 4.4 step 8; **(r5, A5-4)** the "32-segment cap" wording was r3's) |
| U9 | HUD: 10 text lines of ≤ 35 characters in rows 0-175; 272 row writes per tick (rows 0-175, then rows 0-95 again) (8.2); **(r4, A4-4)** line 6 `MS PREP`; **(r5)** `MS PREP` with the measured speed, `MS SLOW`, `MS DIR FULL`, `META` (not red) | D13, N-1, N-2, N-3; load parity with telem (7.4); A4-4; A5-3 | 1.9 KB row buffer; ≈ 110 LOC | KEEP, **reduced** from the full-screen layout (brief candidate). The same 272 `lseek`+`write` calls as telem keep the load equal; rows 176-271 are never written (K30) |
| U10 | PANEL pixel read-back from `/dev/fb0` | proved only that the paint routine ran (N-5) | ≈ 30 LOC | **CUT** (N-5). The proof that the panel is visible is the operator seeing `PSC TEST`, now an abort item |
| U11 | SELFTEST chunk type | duplicated UHB flags b1-b8 | one chunk type | **CUT** |
| U12 | UHB per tick (writer timings, errors, flags, segment state; **(r5)** nonce) | D6, IF5 (errno), self-test record | 104 B/tick (r5) | KEEP |
| U13 | STATS chunk every 8th tick (was 4th) | D1 | 788 B per ≈ 1.8 s | KEEP |
| U14 | KMSG chunk from `/proc/kmsg`; one `syslog(3)` call per tick for load parity | dossier 9.1 blind spot; IF5 (FAT panic text) | ≤ 4 KB, rare | KEEP |
| U15 | PROCS every 40th tick (was 8th): thread, `psposk2`, `pspmd`, worker; thread status lines; `MemFree` | H9, N6 | ≈ 1.1 KB per ≈ 9 s | KEEP, reduced (supervisor, standby and `buddyinfo` lines cut with U2) |
| U16 | Own `/dev/input/mice` client (`IN`) | H7 (c), C5 death sign, N-3 | ≈ 20 LOC | KEEP |
| U17 | EVENT chunk; **(r4)** EVENT and KMSG payloads re-sent until a flush carrying them succeeds | IF1/IF5 (rewind, abandon, read-only), takeover; A4 IF1 note | ≤ 1 KB | KEEP |
| U18 | `pscol` memory guards and stack high-water, exit on violation | A2 OE4 | ≈ 40 LOC | KEEP |
| U19 | Self-test, eight checks (CTX merged into WDOG) (8.2); **(r4, A4-5)** second `PSC TEST` when six checks are first green, independent of BTN; **(r5)** STICK also needs the geometry self-check, ≥ 30 KB/s measured and the names budget (8.2) | D13; A4-5; A5-3, A5 IF4 G2 | ≈ 95 LOC | KEEP |
| U20 | **(r4)** META detection from S records (K36), `ctl` op 4. **(r5)** informational: HUD line 6 `META` (not red), panel line 6 field, no panel paint; cleared on a later good write or when bypassed (4.7) | IF7, IF8 shown; A5-2 (no good run discarded) | ≈ 45 LOC | CHANGED |
| U21 | **(r5)** Verdicts from the S records: sector classes from K37, `FIBMAP` extent table per file, flush DURABLE iff every data sector has an error-free S record, step CONFIRMED iff FAT1 and data (and, at step 0, its own directory-entry) writes succeeded; S windows read with `pread` (4.8) | A4 F1(b), F4; A5 IF7, IF8 diagnosable (not merely detected); A5-1 | ≈ 2 `pread`s of ≤ 40 records per tick, ≤ 3 `ioctl`s per step; extent tables ≈ 6 KB; ≈ 120 LOC | NEW |
| U22 | **(r5)** Bad-region escape: three consecutive FAILED flushes with a data-sector error while other writes succeed retire the active file and switch (4.6) | A5 IF9 (BLIND) | ≈ 25 LOC | NEW |
| U23 | **(r5)** Throughput gate in STICK (≥ 30 KB/s over the first two 64 KB steps) (4.8, 8.2) | A5 IF4 G2 (lossless range), A5-3 (self-test time) | ≈ 10 LOC | NEW |
| U24 | **(r5)** Console log level 4 at worker start (**r7, A6-2:** `syscall(__NR_syslog, 8, 0, 4)`, return in EVENT `conlevel`) (4.2, 7.1) | A5 OE8 (interrupts-off drawing of the driver's error lines) | one system call | NEW |
| U25 | **(r5)** Boot nonce: in FILEHDR and UHB, and the initial value of every non-FILEHDR chunk CRC (10.2) | A5 IF10 (other boots' chunks merged) | 2 words of format; ≈ 10 LOC | NEW |

### 0.3 Decoder and runbook

| # | Mechanism | For | Decision |
|---|---|---|---|
| X1 | Parse, CRC, dedupe by (ring, `seq`), raw-image scan; **(r3)** raw image primary whenever the copied files show an error, abandon, takeover or read-only EVENT; **(r4)** or META, or a RECS-holding file shorter than 2 MB (10.2); **(r4, A4 IF6)** 16-bit links paired by `(tick, Count)` when the nearest value is missing (10.3); **(r5, A5 IF10)** one run selected by FILEHDR run and nonce, CRCs checked with that nonce, chunks above a file's confirmed extent listed not merged, `(ring, seq)` conflicts reported (10.2) | D20, S4, A3 IF5 fix 3, A4-3, A4 IF6, A5 IF10 | KEEP |
| X2 | Healthy template with code-derived fallback and the WB/M/WT H8 baseline | A1 TE1, F11; N-4 | KEEP |
| X3 | Onset candidates O1-O5, raw windows | D5, S2 | KEEP |
| X4 | Classification by the section 6 rows; **(r3)** N1m, N1p, LEDSPLIT; narrowed H10 wording; **(r4, A4 UL6, OE5)** row WB and the "both results valid" benign rule, the takeover-to-PROCS annotation; **(r5, A5 UL7)** every WT within ± 2 cycles listed with its step, and "straddle at k, onset at k+1" as a candidate (10.7 step 5) | D2, A3 UL5, OE6, TE5, A4 UL6, OE5, A5 UL7 | KEEP |
| X5 | P-point outcome cross-check | A1 TE2 | KEEP |
| X6 | EPC map and register map | H4 step, k/j, LEDSPLIT | KEEP |
| X7 | Panel transcription from photographs | A1 OE1; the only record after `MS RO` | KEEP |
| X8 | Pre-registered no-death inference | A1 OE3, S5 | KEEP |
| X9 | **(r3)** Pre-registered with/without-LED harm-rate comparison | A3 UL5 | NEW |
| X10 | Late-start attribution from `wk_*` | A2 OE3 | KEEP (simplified with K12) |
| X11 | `i.csv`, `wait_hist` and `wk_acc` reports, mousedev open/close alignment, `--photo` wall-time correction | no matrix row | **CUT** |
| RB1 | Two-display pull check D8 (kernel band + HUD `MS` line) | D6 | KEEP |
| RB2 | C0 healthy reference; post-death script D1-D7a | D17, A1 TE1, UL2 | KEEP |
| RB3 | **(r3)** Stick always mounted read-only on the Mac (automount blocked, rehearsed in A0); raw image mandatory after any error, abandon, read-only or panel after `SELFTEST PASS`; **(r4)** one file smaller than 2 MB is normal (A4-3); **(r5)** counted among this run's files only | A3 IF5 fix 3, A5-4 | CHANGED |
| RB5 | **(r4)** `META`: raw image mandatory. **(r5, A5-2)** the run counts; D8 decides on `DUR` as always | IF7, IF8 | CHANGED |
| RB4 | Self-test decision at **3:00** (was 2:00), because the first segment is created before STICK can pass; **(r5, A5-3)** time to the first complete drain computed (8.3) | D13 | CHANGED |
| RB6 | **(r5)** Abort at 3:00 on `MS SLOW` or `MS DIR FULL`; A4 creates `PSCLOG` on the Mac if absent; E1/E2 count only this run's files (A5-4) | U23, U6 names budget; A5-4 | NEW |

**Record types after the cut:** four formats (SC, W extension, POLL, S) in
five rings (P, POLL, W, S, M; the I ring is gone), seven chunk types plus PAD.
**Open risks:** 36 in revision 2, 22 in revision 3, 24 in revision 4, 28 now;
11.3 lists every removed risk with the cut that eliminated it or the reason it
is accepted.

---
## 1. Record format

### 1.0 Conventions

- Little-endian (`.config:64` `CONFIG_CPU_LITTLE_ENDIAN=y`); structs
  `__attribute__((packed, aligned(4)))` with a compile-time size assertion
  (G2 C9). Python `struct` strings are in 10.3; sizes checked with
  `struct.calcsize`: SC 80, W 288 (SC 80 + extension 208), POLL 40, S 40, M 80,
  stats 768, chunk header 20, block header 8, **(r5)** FILEHDR fixed part 44,
  UHB 84, ctl command 32.
- Each ring has its own `seq` (u32 from 0, +1 per record); a slot whose `seq`
  is `0xFFFFFFFF` is being written (3.4). Reserved bytes are 0.

### 1.1 Timestamps

- **Tick.** `psp_local_tick` is the existing `localTick` of
  `psp_watchdog_tick` (`psp.c:372`), moved to file scope, code unchanged: +1
  per timer interrupt (`psp.c:375`); the Nop fires when
  `localTick - lastTick >= 1250` (`:376`), then `lastTick = localTick`
  (`:378`). Both start at 0, so **the Nop runs exactly at
  `psp_local_tick` = 1250·k** [SRC]. Its only caller is `psp.c:359`.
- **Sub-tick.** CP0 Count (`read_c0_count()`, `mipsregs.h:789`) is zeroed first
  in each timer interrupt (`psp.c:351-352`); 220,912,896 counts/s (`psp.c:38`,
  "measured by tests", UNVERIFIED), ≈ 4.5 ns; a tick is `CPT = 883651`
  (`psp.c:39`).
- **Ordering in the handler (dossier 9.1).** Count reset (`psp.c:352`) and
  `localTick++` (`:375`) both precede the Nop (`:379`) with interrupts off: a
  W record reads `(1250k, small)`, the thread activity it interrupted
  `(1250k − 1, large)`, true order without correction. `jiffies` is not used.
- **Torn reads.** Thread-context stamps use `ts_read()`:
  `do { t1 = ACCESS_ONCE(psp_local_tick); c = read_c0_count(); t2 = ACCESS_ONCE(psp_local_tick); } while (t1 != t2);`
- **Tick length.** The hook reads Count before the reset (`c_pre`, the true
  length of the tick that ended); the stats keep its maximum, `long_ticks`
  (> 1.5 × CPT) and a 64-bit sum `total_counts` (wall time in counts).
- **Watchdog phase** of a record = `tick mod 1250` plus `c / CPT`; every WT
  record is a boundary and the decoder asserts `tick % 1250 == 0` (10.5, 6.3).

### 1.2 SC record: one per `Syscon_cmd` call (80 bytes). Rings P (thread), W (first 80 bytes), M (other)

| Off | Type | Field | Source and meaning |
|---|---|---|---|
| 0 | u32 | `seq` | per-ring sequence number |
| 4 | u32 | `tick_in` | `ts_read()` at entry, before `retry:` (`syscon.c:75`) |
| 8 | u32 | `c_in` | Count, same read |
| 12 | u32 | `c_out` | Count at the record, after the last register access |
| 16 | u16 | `dtick` | `tick_out − tick_in`, saturating at 0xFFFF |
| 18 | u8 | `cmd` | `tx_buf[0]` |
| 19 | u8 | `txlen` | `tx_buf[1]` |
| 20 | s16 | `ret` | return value: −5, −4, −3, −2 or 0..255 (recon §1.3; −1 cannot occur) |
| 22 | u8 | `nwords` | 16-bit words received in the final attempt, 0..8; 0 on the −3 and −4 exits. **(§17 R-1)** Derived after S20 from the state the receive loop leaves (2.1 A4), never from code added to the loop. **Exact for 0 to 7 received words; one exception:** when 8 words are received and the 8th is 0xFFFF the record says 7, because the loop leaves the same state after "7 words, then FIFO empty" as after 8 words (`syscon.c:201-217`), and `rx[14..15]` = `ff ff` either way (the prefill, `syscon.c:92-93`). So `nwords` = 7 with `rx[14]` = `rx[15]` = 0xff means **7 or 8**; every other value is exact. The decoder flags the case (10.3), and every rule reads it as the set {7, 8} (10.7, "`nwords` 7 or 8") |
| 23 | u8 | `retries` | `retry_cnt` (`syscon.c:72,253`): 0..15, or 16 on −5 |
| 24 | u32 | `ack_polls` | `SYSCON_SPIN_MAX − spin_ack` after the ACK loop (`syscon.c:151-156`), final attempt. 0 = latch already set at the first poll; 1,000,001 = the −4 timeout; 0xFFFFFFFF = loop not reached |
| 28 | u16 | `drain` | `SYSCON_SPIN_MAX − spin` after the RX pre-drain (`syscon.c:106-117`), saturating; 0xFFFF = −3 |
| 30 | u16 | `drain_last` | last word popped by the drain (`syscon.c:114`, the load that goes to `dmy`) |
| 32 | u16 | `gpio_in` | value loaded from `0xbe240004` at S5 (`syscon.c:102`), final attempt; low 16 bits as the code keeps them (`syscon.c:63`, [OBJ] `andi v0,v0,0xffff` at `+0xe0`) |
| 34 | u16 | `spi_st9` | value loaded from `0xbe58000c` at `syscon.c:119`; 0 on −3 |
| 36 | u16 | `spi_sttx` | value loaded from `0xbe58000c` at `syscon.c:130`, last TX push; 0 on −3 |
| 38 | u8 | `ctx` | b0-1 origin: 0 P (joypad thread), 1 M (other thread), 2 WB (boot Nop, `psp.c:557`), 3 WT (timer Nop, `psp.c:379`). b2 CP0 Status.IE at entry (`read_c0_status() & 1`, `mipsregs.h:810`). b3 `in_interrupt() != 0`. b4 `current == joypad task`. b5 `preempt_count() != 0`. b6 `signal_pending(current)` (P, M). b7 0 |
| 39 | u8 | `wn` | Nops that ran while this command was in flight (`wd_calls` difference, saturating). 0 for W |
| 40 | u16 | `w_head_lo` | W head at record time, low 16 bits; the Nops of this command are `w_head − wn .. w_head − 1` |
| 42 | u16 | `pre_wrk` | **(r4, 2.11)** part of this command's preempted time during which a collector process (class 1 or 2) held the CPU, Count/256, saturating |
| 44 | u8 | `pre_cls` | **(r4)** low nibble: class of the task that preempted the thread (first preemption in this command); high nibble: class of the last holder before it resumed; 0 if none |
| 45 | u8 | `ms_delta` | LED read-modify-writes (2 per Memory Stick sector attempt) between entry and record, saturating |
| 46 | u8 | `pre_flags` | **(r4)** b0 the `pre_*` fields belong to this command; b1 ≥ 2 preemptions; b2 `pre_tot` or `pre_wrk` saturated; b3 a holder outside classes 1-2 ran; b4 a holder of class 3, 4 or 5 ran |
| 47 | u8 | `preempt_delta` | `current->nivcsw` at record minus at entry (`include/linux/sched.h:907`; incremented for a switch while runnable, `kernel/sched.c:3626-3628`). Non-zero: the thread was preempted mid-command. 0 for W |
| 48 | u8[16] | `rx` | the whole `rx_buf[0..15]` after the final attempt, including the 0xff prefill (`syscon.c:92-93`) |
| 64 | u32 | `lc_epc` | EPC of the thread at the **last** tick that found this command in flight **with the thread running** (2.3 T2a, never a nested tick). 0 if none |
| 68 | u16 | `lc_dtick` | that tick minus `tick_in`, saturating; 0xFFFF = none |
| 70 | u8 | `lc_n` | ticks that found this command in flight with the thread running, saturating at 255 |
| 71 | u8 | `lc_flags` | b0 valid (the `lc` words belong to this command's `cmd_id`); b1 Cause.BD at that tick; b2 EPC inside `Syscon_cmd`; b3 that tick was a watchdog tick; b4 at least one *nested* tick found the thread current during this command and was not used (2.3 T2a); **(r3)** b5 the kernel panel was painted (2.10) while this command was in flight |
| 72 | u32 | `led_or` | OR of every raw word read from `0xbe240008`/`0xbe24000c` by the LED read-modify-writes (`psp.c:399-407`) that ran while this command was in flight; 0 if none |
| 76 | u16 | `led_pid` | pid (low 16) of the task that did the last of those; 0 if none |
| 78 | u16 | `pre_tot` | **(r4)** total time the thread spent preempted inside this command, Count/256, saturating at 0xFFFF (≈ 76 ms; longer: `dtick − lc_dtick`) |

TX bytes beyond `cmd`/`txlen` are constants in every caller
(`syscon.h:101,132-134`) and are not recorded.

**Why `lc_*` exists (A1 TE2).** The thread can leave the CPU inside
`Syscon_cmd` only at the return from a timer tick (`entry.S:61-73`; the timer
is the only interrupt, 2.3), so the EPC at the last tick that found it running
is its suspension point. `thread_info->regs` cannot supply it: `TI_REGS` is
restored before `preempt_schedule_irq` (`entry.S:39`, `:72`).

**Nested ticks (A2 TE4).** A handler that runs a tick or more makes the next
tick nest inside `__do_softirq` (softirq count raised at
`kernel/softirq.c:217`, interrupts enabled at `:225`) with `current` still the
thread; preemption happens only at a return with `TI_PRE_COUNT` = 0
(`entry.S:61-64`), i.e. at the outermost frame, whose EPC that tick stored. So
T2a never updates `lc` from a tick whose interrupted context has
`preempt_count() & (SOFTIRQ_MASK | HARDIRQ_MASK)` set (`hardirq.h:52-53,65`).

**Why `led_or` (A1 UL1).** The LED helpers write back every bit they read
(`psp.c:399-407`); which bits a read returns is a hardware unknown (recon §4),
so the whole word is kept, not bit 3 only.

### 1.3 W record: watchdog command (288 bytes = SC 80 + extension 208)

The first 80 bytes are the Nop's own SC record (its frame, return value and
captures, which the kernel otherwise discards, `psp.c:392`); its `lc_*`,
`led_or`, `led_pid` are 0 (the Nop runs with interrupts off). The extension
is filled after the Nop's transaction, interrupts still off, only for origin
WT. For WB (boot) there is no interrupt frame and the extension is zero.

| Off | Type | Field | Source |
|---|---|---|---|
| 80 | u32 | `epc` | `regs->cp0_epc` of the interrupted context; `regs = current_thread_info()->regs` (`include/asm-mips/thread_info.h:37`), set by `handle_int` (`arch/mips/kernel/genex.S:166-167`, vectored path `:266-267`) |
| 84 | u32 | `cause` | `regs->cp0_cause` (b31 BD) |
| 88 | u32 | `status` | `regs->cp0_status` (CU0 set = kernel mode on this port, `entry.S:45-48`) |
| 92 | u32 | `ra` | `regs->regs[31]` |
| 96 | u32 | `sp` | `regs->regs[29]` |
| 100 | u32[16] | `r` | `regs->regs[2..15]`, then `regs[24]`, `regs[25]` (`include/asm-mips/ptrace.h:37`). [OBJ] the baseline keeps `i` in `t0` (r8) and `ptr` in `a3` (r7) (`syscon.o +0x180..+0x1b4`, `+0x244..+0x298`) |
| 164 | u32 | `pid` | `current->pid` (the interrupted task) |
| 168 | u32 | `p_head` | P head = the `seq` the in-flight thread command will receive |
| 172 | u32 | `jp_loop` | thread loop counter |
| 176 | u32 | `t_entry_tick` | tick at entry of the in-flight thread command (valid if `t_busy`) |
| 180 | u32 | `t_entry_c` | Count at that entry |
| 184 | u8 | `t_busy` | b0 a P command in flight, b1 an M command in flight |
| 185 | u8 | `jp_stage` | thread stage code (2.5) |
| 186 | u8 | `ext_flags` | b0 `regs` valid; b1 0; b2 interrupted context in kernel mode; b3 EPC inside `Syscon_cmd`; b4 `current == joypad task`; b5 the `lc` block below belongs to the in-flight command; b6 a Memory Stick transfer is in progress (2.4); b7 *nested*: the interrupted context had a non-zero softirq or hardirq count, so `epc` is not the thread's own instruction even when b4 is set |
| 187 | u8 | `cur_pcnt` | `preempt_count()` of the interrupted task, low 8 bits (non-zero inside Memory Stick I/O, `include/linux/highmem.h:49-52`) |
| 188 | u32 | `c_pre` | Count at this handler's entry, before the reset |
| 192 | u32 | `lc_tick` | tick of the last tick at which the thread was running with this command in flight |
| 196 | u32 | `lc_c_pre` | Count before the reset at that tick |
| 200 | u32 | `lc_cmd_id` | the `cmd_id` the `lc` words belong to |
| 204 | u32 | `lc_epc` | the thread's EPC at that tick = its suspension point if it is not running now |
| 208 | u32 | `lc_cause` | its Cause |
| 212 | u32 | `lc_ra` | its `ra` |
| 216 | u32 | `lc_sp` | its `sp` |
| 220 | u32[16] | `lc_r` | its registers 2..15, 24, 25 at that tick |
| 284 | u16 | `lc_n` | ticks with the thread running in this command so far |
| 286 | u16 | — | reserved |

**Safe:** only RAM is read; `regs` is used only inside the current task's
stack (else b0 clear, registers 0); `lc` is a copy of timer-only words.

**What it resolves.** Thread interrupted (b4 = 1, b7 = 0): `epc` gives the step
and P-point, `r` gives k (P2) and j (P6). Thread suspended (b4 = 0) or tick
nested (b7 = 1), with b5 = 1: `lc_epc` and `lc_r` give them. How long the
interrupted command had run is `W tick − t_entry_tick`. Stage 2 regenerates the
register map from the final build (10.6).

### 1.4 POLL record: one per thread loop iteration (40 bytes, ring POLL)

| Off | Type | Field | Source |
|---|---|---|---|
| 0 | u32 | `seq` | |
| 4 | u32 | `tick_start` | `ts_read()` at loop top (`joypad_psp.c:458`) |
| 8 | u32 | `c_start` | same |
| 12 | u32 | `c_end` | Count just before `msleep` (`:468`) |
| 16 | u16 | `sc_seq_lo` | P head at loop top, low 16 = `seq` of this poll's 0x33 record |
| 18 | u8 | `body_ticks` | tick at `msleep` minus `tick_start`, saturating |
| 19 | u8 | `ri_branch` | 1 R1 (`:483-484`), 3 R3 GetCtrl2 < 0 (`:487-488`), 4 R4 HOLD (`:492-493`), 5 R5 TRUE (`:495`) |
| 20 | u8 | `pi_flags` | b0 `process_input` called; b1 returned at dedupe (`:512-513`); b2 `console_blanked` true at `psp_lcd_on` (`psp.c:259`); b3 SELECT toggle executed (`:521-522`); b4 `mouseMode` after; b5 `list_sem` acquired (`:530`); b6 `list_sem` down failed; b7 `wake_up_interruptible` called (`:538`) |
| 21 | u8 | `nqueues` | queues walked (`:532-535`) |
| 22 | u8 | `push_ok` | pushes that returned TRUE (`:409-410`) |
| 23 | u8 | `push_fail` | low nibble: full (`:395-399`); high nibble: `-EINTR` (`:390-393`) |
| 24 | u8 | `mouse_flags` | b0 called (`:464-465`); b1 M1 no device (`:609-610`); b2 M2 no-op (`:639-645`); b3 reported (`:651-658`); b4 left, b5 middle, b6 right |
| 25 | s8 | `dx` | passed to REL_X (`:651`) |
| 26 | s8 | `dy` | `dy` (REL_Y is reported as `−dy`, `:652`) |
| 27 | u8 | `sig` | b0 `signal_pending(current)` at loop top |
| 28 | u8 | `period` | `tick_start` minus the previous `tick_start`, saturating (nominal 14, recon/input §4) |
| 29 | u8 | `preempt_delta` | `nivcsw` delta over the loop body |
| 30 | u8 | `stage_max` | highest stage reached (2.5) |
| 31 | u8 | `nsc` | SC records produced in this iteration (normally 2) |
| 32 | u16 | `wk_delay` | **(r3)** the thread's last wake-up-to-switch-in delay (2.11), Count / 256 (≈ 1.16 µs), saturating at 0xFFFF (≈ 76 ms, 19 ticks); 0 if no completed wake-up since the previous loop top |
| 34 | u16 | `wk_wrk` | **(r3)** the part of that delay during which a collector process (class 1 or 2) held the CPU, same units |
| 36 | u8 | `wk_cls0` | class (2.11) of the task running when the thread was woken |
| 37 | u8 | `wk_cls1` | class of the task switched out to run the thread (the last holder) |
| 38 | u8 | `wk_nsw` | context switches during the wait, saturating |
| 39 | u8 | — | reserved |

The raw key word, `x` and `y` are `rx[3..8]` of the 0x08 SC record
(`syscon.c:363-365`), paired through `sc_seq_lo`.

### 1.5 S record: one per Memory Stick segment transfer (40 bytes, ring S)

Written in `psp_ms_read`/`psp_ms_write` (`drivers/block/ms_psp.c:328-353`,
`:355-379`) under `s_psp_ms_rw_sem` (`:333`, `:360`): one writer at a time.
`psp_ms_transfer_bio` calls them once per bio segment (`ms_psp.c:252-265`);
file data goes through `fat_writepages` → `mpage_writepages`
(`fs/fat/inode.c:126-129`) in pages of up to 8 sectors (`fs/mpage.c:488-535`),
metadata one 512-byte buffer each (`fs/buffer.c:2593-2621`). So the S rate is
**at most** the sector rate.

| Off | Type | Field | Meaning |
|---|---|---|---|
| 0 | u32 | `seq` | |
| 4 | u32 | `tick_on` | at entry, after the semaphore |
| 8 | u32 | `c_on` | |
| 12 | u32 | `c_off` | at exit, before `up()` |
| 16 | u32 | `sector` | first sector |
| 20 | u16 | `dtick` | |
| 22 | u16 | `pid` | the task doing the I/O |
| 24 | u8 | `nsect` | |
| 25 | u8 | `flags` | b0 write; b1 error (rt < 0); b2 an LED **set** read had bit 3; b3 an LED **clear** read had bit 3; b4 a P command in flight at entry; b5 at exit; b6 an M command in flight at either; **(r4)** b7 metadata: the page is in the block device's page cache (FAT, FSINFO, directory; 2.4), else file data |
| 26 | u16 | `p_head_lo` | P head at entry |
| 28 | u8 | `led_ops` | LED read-modify-writes in this segment (2 per sector attempt) |
| 29 | u8, u16 | — | reserved (29, 30-31) |
| 32 | u32 | `rd_set_or` | OR of every word read from `0xbe240008` (`psp.c:32,401`) by this segment's LED operations; 0 if none |
| 36 | u32 | `rd_clr_or` | OR of every word read from `0xbe24000c` (`psp.c:33,406`) |

### 1.6 M record

The SC format, for thread-context callers other than the joypad thread
(`pspSysconCtrlHRPower` at boot, `serial_psp.c:352`; `pspSysconPowerStandby`
at shutdown, `psp.c:218`; anything unforeseen). The M ring is fill-once (3.1).

### 1.7 Stats block (768 bytes = 192 × u32, `/proc/psc/stats`)

Evaluated at each read. Writers: T thread, W timer interrupt, L Memory Stick
path, R the reader at read time, P any process (plain `++`, informational,
never compared for equality), K `pdflush`, C the collector through `ctl`, X the
scheduler hooks, F the vfat hooks. `total_counts` is read high-low-high
(`do { h1 = hi; l = lo; h2 = hi; } while (h1 != h2);`; its only writer, the
timer interrupt, cannot be interrupted by the reader).

| Words | Content |
|---|---|
| 0-4 | magic `0x54535350` ('PSST'); `version` (low 16) = **5** (r5), `size` (high 16) = **768**; `build_id` (**§17 R-4**: CRC-32/IEEE as zlib `crc32` with initial value 0, of the bytes of `linux_banner` without its terminating NUL, computed once at init. Those bytes equal `/proc/version`: `init/version.c:37-39` against `:41-44` filled by `fs/proc/proc_misc.c:250-253` from `utsname()` sysname, release and version, which are the same compile-time strings, `init/version.c:24-28`, and are only read elsewhere in this tree. The value differs between any two builds, since the banner carries the build time); `hz` = 250; `counts_per_tick` = 883651 |
| 5-9 | `last_reader_tick` [R] (ring-file reads only, not `stats`); `initial_jiffies` (`include/linux/jiffies.h:137`); `now_tick`, `now_count`, `now_jiffies` [R] |
| 10-13 | `total_counts` low, high; `c_pre_max`; `long_ticks` [W] |
| 14-23 | heads P, POLL, W, S, M [R]; `m_dropped` [P]; addresses of `Syscon_cmd`, `psc_sc_exit`, `_pspSysconGetCtrl2`; `proc_opens` [R] |
| 24-30 | `p_rec_cost_last`, `p_rec_cost_max` [T], `w_rec_cost_max` [W] (Count units); `wd_calls`, `wd_last_tick` [W]; `p_nested` (P with `wn > 0`), `p_ticked` (P with `dtick > 0`) [T] |
| 31-37 | outcome counters for P cmd 0x08 [T]: `ret > 0`; `ret == 0 && nwords > 0`; `ret == 0 && nwords == 0`; −2; −3; −4; −5 |
| 38-44 | the same for P cmd 0x33 [T] |
| 45-51 | the same for W [W] |
| 52-55 | `jp_pid`, `jp_loop`, `jp_stage`, `jp_stage_arg` (queue pointer at stages 11-12) [T] |
| 56-59 | `jp_state` (`task->state`, 0xFFFFFFFF if none), `jp_sigpending` (TIF_SIGPENDING), `jp_sigword` (`pending.signal.sig[0]`), `jp_nivcsw` [R] |
| 60-63 | `jp_keys` (value stored at `joypad_psp.c:527`) [T]; `console_blanked`, `console_sem` count (read-only accessor, `kernel/printk.c`), `list_sem` count (read-only accessor, `joypad_psp.c`) [R] |
| 64-67 | `t_busy` (b0 P, b1 M) [R]; `t_cmd`, `t_entry_tick`, `t_entry_c` of the in-flight P command [T] |
| 68-75 | `jp_r3`, `jp_r4`, `jp_r5`, `jp_proc_calls`, `jp_dedupe`, `jp_changed`, `jp_lcd_unblank`, `jp_mode_toggles` [T] |
| 76-83 | `jp_listsem_fail`, `jp_push_ok`, `jp_push_full`, `jp_push_eintr`, `jp_wake`, `jp_mouse_calls`, `jp_mouse_noop`, `jp_mouse_reports` [T] |
| 84-89 | `fop_open`, `fop_release`, `fop_read_enter`, `fop_read_ret`, `fop_read_eintr`, `fop_ioctl` [P] |
| 90-92 | `qfree_stage` (1 entry, 2 after `:348` succeeded, 3 after `:353`, 4 after `list_del`, 5 before `kfree`), `qfree_queue`, `qfree_pid` [P] |
| 93-96 | `vcs_putchar`, `vcs_changecon`, `vcs_updscr`, `vcs_getsize` (`drivers/char/vc_screen.c:574-587`) [P] |
| 97-99 | `md_event_syn` [T], `md_notify_calls` [T], `md_read_ret` [P] (`drivers/input/mousedev.c:304`, `:228`, `:659`) |
| 100-103 | `led_calls`, `led_calls_t_busy`; `led_or_set_run`, `led_or_clr_run` (whole-run OR of every word read back from the set and clear registers) [L] |
| 104-111 | `ms_seg_wr`, `ms_seg_rd`, `ms_err`; marker `ms_ip_tick`, `ms_ip_sector`, `ms_ip_word` (pid low 16, `nsect` bits 16-23, b24 active, b25 write) [L]; `kupd_count`, `kupd_last_tick` [K] |
| 112 | `durable_tick` [C]: every record produced before this tick is on the stick (4.5) |
| 113-117 | `durable_next[5]` for P, POLL, W, S, M [C]: the `seq` after the last record of that ring in a flush whose `write` and `fsync` succeeded; 0 = none yet |
| 118-124 | `ctl_writes` [C]; `panel_paints`, `panel_last_tick` [W]; `panel_test_seq` [C]; `panel_test_done` (test paints) [W]; `panel_cost_max` [W]; `lc_nested` [W] |
| 125-127 | `kguard_bad` [W]; `ring_rewinds` (seeks of a ring file to an earlier record), `head_regress` (reads beyond the head) [R] |
| 128-132 | **(r3)** `slot_bad[5]` [R]: slots skipped because their `seq` was wrong and no lap explains it (3.5) |
| 133-135 | **(r3)** `fat_panics`, `fat_panic_tick` (first) [F]; `ms_rdonly` [R] (2.12) |
| 136-139 | `wk_count`, `wk_max` (Count/256) [X]; `jp_exit_tick` [P]; `kguard_first_tick` [W] |
| 140-147 | `pid_class[8]` [C]: pid low 24 bits, class in the top 8 (2.11) |
| 148-149 | **(r3)** `panel_cost_last` [W]; `panel_state` [W] (0 never painted, 1 cleared, 2 showing) |
| 150-152 | **(r4)** `meta_sector` [C] (0 none; 4.7), `meta_tick` [C] (first detection); `pre_count` [X] (preemptions of the thread inside a command, 2.11) |
| 153-159 | **(r5, 4.8)** geometry, written once: `ms_part_start` [L] (start sector of partition 0 = `/dev/ms0`, `ms_psp.c:175-179`, set at the end of `psp_ms_init`); then [F] at mount: `fat_start`, `fat_length`, `fats`, `fsinfo_sector`, `data_start` (all in `s_blocksize` units, `fs/fat/inode.c:1234-1291`, `:1323`, `:1336`), `sec_per_clus` (low 16) with `s_blocksize_bits` (high 16) |
| 160-191 | reserved, 0 |

### 1.8 How context is identified (`in_interrupt()` is false in the Nop, dossier 9.1)

| Origin | Rule (at `Syscon_cmd` entry, in order) | Why it is exact |
|---|---|---|
| WT | `psc_wd_ctx == 2` | set just before `psp_pacify_watchdog()` at `psp.c:379`, cleared after; that call runs only in the timer interrupt with interrupts off (`genex.S:162-169`, recon §2.3, [BIN] V4) and cannot nest |
| WB | `psc_wd_ctx == 1` | set around the boot call at `psp.c:557` (`prom_init`, interrupts off) |
| P | `current == psc_jp_task` | set first thing in `psp_joypad_thread` (`joypad_psp.c:453-458`) |
| M | otherwise | |

`psp_pacify_watchdog` has exactly two callers (grep: `psp.c:97,379,383,557`;
`:97` prototype, `:383` definition). The raw indicators stay in `ctx`, so the
decoder and the WDOG self-test check the classification.

---
## 2. Capture points

### 2.1 `Syscon_cmd` (`arch/mips/psp/ipl_sdk/syscon.c:61-258`): every caller, every context

A per-call scratch struct `sc` on `Syscon_cmd`'s stack holds the capture slots
(volatile), the entry snapshot and the origin.

| # | Location | Change | In S5..S20? |
|---|---|---|---|
| A1 entry | after the declarations, before `retry:` (`:72-75`) | inline, **no call**: origin (1.8); `ts_read()` → `tick_in`, `c_in`; snapshot `wd_calls`, `led_calls`, `current->nivcsw`, `ctx` bits. P: `psc_t_busy_p = 1`, `t_cmd`, `t_entry_tick/c`, `++psc_t_cmd_id`. M: `psc_t_busy_m = 1` | No |
| A2 per attempt | at `retry:` (`:75`), before S1 (`:77`) | `sc.spin = SYSCON_SPIN_MAX; sc.spin_ack = SYSCON_SPIN_MAX + 1; sc.dlast = sc.st9 = sc.sttx = 0;` (S1..S4 touch memory only) | No |
| A3 in window | `:102` `dmy =` → `sc.gin =`; `:114` → `sc.dlast =`; `:119` → `sc.st9 =`; `:130` → `sc.sttx =`; `:110`/`:113` `spin` → `sc.spin`; `:151`/`:154` → `sc.spin_ack` (assignments kept in place) | **Nothing added**: same volatile loads and stores to stack slots of the same width ([OBJ] `lw`, `andi 0xffff`, `sh` at `+0xdc..+0xe4`, `+0x14c..+0x154`, `+0x168..+0x174`, `+0x190..+0x1a8`; spin counters `lw/addiu/sw/lw` on `4(sp)` at `+0x110..+0x11c`, `+0x1dc..+0x1e8`) |
| A4 exits | `:113` `return -3;` → `{ result = -3; goto out; }`; `:154` likewise for −4 (teardown writes unchanged); **(§17 R-1)** after S20, `nwords` from the state the receive loop leaves at its exit (in the G2-attempt-1 build its counter register `t0`, handed over with the captures; the 7/8 case of 1.2), with no C use of `ptr` or `i` after the loop (one adds 2 instructions per received word in S18); `:257` → `out: psc_sc_exit(&sc, tx_buf, rx_buf, result, retry_cnt); return result;` | −3/−4 branch sites keep their instruction count ([OBJ] `+0x124..+0x128`, `+0x20c`); the rest is after S20 |

`psc_sc_exit()` (non-inline, new file `arch/mips/psp/psc.c`): (1) `ts_read()`
→ `tick_out`, `c_out`. (2) **P**: invalidate, fill and publish the P slot
(3.4), update the 0x08/0x33 outcome counters, clear `psc_t_busy_p`. **M**: the
same into the fill-once M ring (`m_dropped` when full), clear `psc_t_busy_m`.
**WT, WB**: fill the W slot and, for WT, the extension (1.3); `wd_calls++`,
`wd_last_tick`, W outcome counters. (3) P and M: copy the `lc` words if
`lc_cmd_id` equals this `cmd_id`, validated by `lc_seq` before and after (at
most one repeat per tick); `led_cmd_*` likewise via `led_cmd_id`; set
`lc_flags` b4 if `lc_nest_id == cmd_id`, b5 if `panel_cmd_id == cmd_id`.
(4) `rec_cost = read_c0_count() − c_out` into the per-origin last and maximum.

**G2 acceptance criteria for the window (7.2):** in `objdump -d vmlinux` from
the S5 load to the S20 store, the same MMIO loads and stores in the same
order as the baseline `syscon.o`; loop bodies with the same instruction counts;
no added calls, global loads or base-address reloads. If the compiler spills,
the implementer drops captures in this order until the criteria hold and
records the deviation: `sttx`, `dlast`, `st9`, `gin`, then `spin_ack` (back to
one `spin`, losing `drain`). No rule depends only on those fields.
**(§17 R-2)** These criteria are the acceptance test for D10. Within them 7.2
allows exactly three differences from the baseline: stack-slot offsets, a
consistent renaming of registers that keeps every value, and the delay slot of
an exit branch after the exit decision and the path's last MMIO access.

### 2.2 Watchdog (`arch/mips/psp/psp.c`)

`psp.c:378-379`: `psc_wd_ctx = 2; psp_pacify_watchdog(); psc_wd_ctx = 0;`
inside the existing `if` (ticks without a Nop gain nothing); `psp.c:557`: the
same with 1. `psp.c:372`: `localTick` moves to file scope as `psp_local_tick`;
the generated code of `psp_watchdog_tick` must be unchanged apart from the
symbol (G2). If `s_psp_shutdown` is set no Nop is sent (`psp.c:385-389`) and
no record is made; the runbook never shuts down.

### 2.3 Timer tick (`psp_cputimer_handler`, `psp.c:348-368`): hard interrupt, IE off, before `irq_enter`

| # | Location | Action |
|---|---|---|
| T1 | `asm volatile("mfc0 %0, $9")` immediately before `psp.c:351-356` | `c_pre` = Count before the reset; `total_counts += c_pre`; `c_pre_max`; `long_ticks`. ≈ 8 instructions; the reset moves 1-2 instructions later |
| T2 | after `psp_watchdog_tick()` (`psp.c:359`), before `psp_uart3_txrx_tick()` (`:363`) | `psc_tick_hook(c_pre)`: T2a then T2d |
| T2a | | **`lc` words, uncapped.** `nested = (preempt_count() & (SOFTIRQ_MASK \| HARDIRQ_MASK)) != 0`, read before this handler's `irq_enter`, so it describes the interrupted context. If `psc_t_busy_p`, `current == psc_jp_task` and `nested`: leave `lc`, `lc_nested++`, `lc_nest_id = psc_t_cmd_id`. If `psc_t_busy_p`, `current == psc_jp_task`, not `nested`: `lc_seq++`; store `psp_local_tick`, `c_pre` and, from `regs = current_thread_info()->regs` (bounds-checked as in 1.3), `cp0_epc`, `regs[31]`, `cp0_cause`, `regs[29]`, `regs[2..15]`, `regs[24..25]`; `lc_cmd_id = psc_t_cmd_id`; `lc_n` (reset when `lc_cmd_id` changes, +1, saturating); `lc_seq++`. Every tick, watchdog ticks included (the W extension copied the previous words first: the Nop runs inside `psp_watchdog_tick`). ≈ 30 instructions, only when the thread is running inside a command |
| T2d | | **Once a second** (countdown `panel_cd`, 125 then 250: ticks ≡ 125 mod 250, never a watchdog tick): the panel condition, paint or clear (2.10); compare the seven guard words (3.1), `kguard_bad++` and `kguard_first_tick` on a difference. Two instructions per tick otherwise |

Cost with nothing in flight: ≈ 16 instructions, ≈ 70 ns per tick. **Every
interruption of a thread transaction is seen:** `plat_irq_dispatch` services
only IP7, the timer (`psp.c:637-654`; other sources would print "Unknown IRQ",
absent from the recovered log, dossier 9.4 Q9; cascaded sources disabled at
`psp.c:594-595`), and in-kernel preemption happens only on a tick's return
(`entry.S:61-73`). Every tick crossing a command counts in its `dtick`; every
one finding the thread running updates `lc`; a watchdog tick leaves a W record.

### 2.4 LED read-modify-write and Memory Stick segments

- `psp.c:399-407`: `PSP_GPIO_SET |= mask_;` becomes
  `v = PSP_GPIO_SET; PSP_GPIO_SET = v | mask_; barrier(); psc_note_led(0, v);`
  (likewise CLEAR): the same single volatile load and store, same order,
  nothing between them ([OBJ] recon §2.2 `lw/or/sw`). After the store,
  `psc_note_led` does `led_calls++` (`led_calls_t_busy` if a command is in
  flight), ORs `v` into its register's run-wide accumulator and the current
  segment's (S `rd_*_or`, b2/b3 if `v & 0x08`), and if `psc_t_busy_p`: resets
  `led_cmd_or`/`led_cmd_pid` when `led_cmd_id != psc_t_cmd_id` (then
  `led_cmd_id = psc_t_cmd_id`), and does `led_cmd_or |= v`,
  `led_cmd_pid = current->pid`. ≈ 25 instructions. This measures, at no
  register cost, what a read of the set or clear register returns while a
  transaction is in flight: the hardware unknown behind H10 (recon §4.2).
- `ms_psp.c:333`, `:360`, after `down_interruptible`: snapshot tick, Count, LED
  counter, `t_busy`; reset the segment accumulators; publish the in-progress
  marker (`ms_ip_tick`, `ms_ip_sector`,
  `ms_ip_word = pid | nsect << 16 | 1 << 24 | write << 25`). Before `up()`
  (`:351`, `:378`): write the S record, clear bit 24. A transfer that never
  completes (`ms_wait_ready`, `memstk.c:59-65`; `ms_wait_ced`, `:174-181`)
  leaves the marker set for the W flags, stats and panel (A1 OE1).
- **(r4, A1 detection) Metadata tag.** In `psp_ms_transfer_bio`'s segment loop
  (`ms_psp.c:252-265`), `meta = m && !((unsigned long)m & 1) &&
  S_ISBLK(m->host->i_mode)` with `m = bvec->bv_page->mapping`, passed as a new
  last argument to `psp_ms_read`/`psp_ms_write` (static; callers `:260`,
  `:264`, and the MBR read `:131` with 0) and stored as S `flags` b7. vfat
  reads and writes FAT, FSINFO and directory sectors through `sb_bread`
  buffers, which live in the block device inode's page cache
  (`grow_dev_page`, `fs/buffer.c:984`; that inode has `i_mode = S_IFBLK`,
  `fs/block_dev.c:573`); file data pages belong to the file's own mapping.
- **(r5, 4.8) Partition start.** At the end of `psp_ms_init` (after the
  partition loop, which ends at `ms_psp.c:199`, before `s_initialized = TRUE`
  at `:201`): `psc_ms_part_start = s_psp_ms_partitions[0].startSector`
  (stats 153). The S record's `sector` is absolute: `psp_ms_transfer_bio` adds
  the partition start to `bi_sector` (`ms_psp.c:250`).
- `psp_led_ctrl`'s only callers (`ms_psp.c:119`, `:290,292,312,314` under the
  semaphore, `psp.c:151` at early boot) make all L words single-writer; the
  thread cannot run while that path holds a raised preempt count.

### 2.5 Thread and driver (`drivers/input/joypad_psp.c`), thread context unless stated

Stage codes (written only by the thread): 0 not started, 1 loop top,
2 AStickPower, 3 GetCtrl2, 4 `read_input` returned, 5 `process_input` entry,
6 dedupe return, 7 before `psp_lcd_on`, 8 after it, 9 before `down(list_sem)`,
10 `list_sem` held, 11 before `down(Q->sem)` (arg = queue pointer),
12 pushing, 13 after `up(list_sem)`, 14 after `wake_up`, 15 mouse entry,
16 before `input_sync`, 17 before `msleep`.

| Location | Action |
|---|---|
| `:453-458` thread start | `psc_jp_task = current; jp_pid = current->pid` |
| `:458` loop top | `jp_loop++`; start the POLL scratch (`ts_read`, `sig`, `nivcsw`, `period`, `sc_seq_lo`); copy `wk_*` if `wk_count` changed (2.11); stage 1 |
| `:486`, `:487` | stages 2, 3 |
| `:488`, `:493`, `:495` | `ri_branch`; `jp_r3/r4/r5` |
| `:498-540` | stages, POLL `pi_flags`, `nqueues`, `push_*`; counters `jp_proc_calls`, `jp_dedupe`, `jp_changed`, `jp_lcd_unblank` (just before `:518`), `jp_mode_toggles`, `jp_listsem_fail`, `jp_wake`; `jp_keys` at `:527` |
| `:384-411` `queue_push` | reason ok (`:409-410`), full (`:397-398`), `-EINTR` (`:392`) → POLL and counters |
| `:593-659` mouse | stages 15, 16; `mouse_flags`, `dx`, `dy`; counters |
| before `:468` | stage 17; finish and append the POLL record |
| `:219-250`, `:252-...`, `:295-317`, `:319-329` fops | `fop_*` counters (caller's context) |
| `:346-360` `queue_free` | `qfree_stage` 1..5, `qfree_queue`, `qfree_pid` (closer's context): **the direct H9 signature** |

None of these is inside `Syscon_cmd`.

### 2.6 Above the driver (counters only)

- `drivers/char/vc_screen.c:562-590` `psp_vcs_ioctl`: a counter per command
  (`:574,578,582,586`), the OSK's and `pspmd`'s injection liveness (H7 (d)).
- `drivers/input/mousedev.c:304` (`SYN_REPORT`), `:228`
  (`mousedev_notify_readers`), `:659` (successful return of `mousedev_read`)
  (H7 (c)). Read-only accessors for the `console_sem` count
  (`kernel/printk.c:67`) and the `list_sem` count (`joypad_psp.c`).
- `kernel/exit.c:916` (`do_exit`, after `PF_EXITING`): `if (current ==
  psc_jp_task) { psc_jp_task = NULL; jp_exit_tick = psp_local_tick; }`, so the
  stats reader and the hooks never use a freed task (the thread never exits in
  normal running, recon/input §1.2).

### 2.7 `pdflush` periodic writeback (`mm/page-writeback.c`)

`wb_kupdate` (`:433-473`) runs about every 5 s (`dirty_writeback_interval`,
`:80`), armed from `init/main.c:628` (`:585`) and re-armed at
`start_jif + interval` (`:453`, `:469-472`): a second 5 s cadence near the
watchdog's phase that can cause Memory Stick I/O. Hook at entry:
`kupd_count++; kupd_last_tick = psp_local_tick;` (N8). The collector samples
the stats every ≈ 1.8 s, so every run's tick is captured.

### 2.8 `/proc/psc/` (new file `arch/mips/psp/psc.c`, `late_initcall`)

`create_proc_entry` with custom `proc_fops`, the tree's own pattern at
`drivers/input/input.c:651-663` [SRC].

| File | Semantics |
|---|---|
| `p`, `poll`, `w`, `s`, `m` | Binary record streams; file offset = `seq` × record size. `read()` follows the reader protocol of 3.5: it returns whole records only, at most as many bytes as requested, skips and counts bad slots, never blocks, takes no lock, and sets **`*ppos`** (never `file->f_pos`) to the next `seq` to read: `read()` copies `*ppos` back to `f_pos` (`fs/read_write.c:364-366`), while a `pread` (4.8) passes a local position (`:404-405`) and so leaves the drain position alone. A fresh open starts at offset 0 (the oldest valid record). `llseek` (custom: `SEEK_SET` to a multiple of the record size, and `SEEK_CUR` with 0 to read the position) lets a writer resume at `durable_next`; a seek to an earlier record counts `ring_rewinds`. Every `read()` of a ring file, even of zero bytes, sets `last_reader_tick` |
| `stats` | The 768-byte block of 1.7, evaluated at each read at offset 0. Does not set `last_reader_tick` |
| `ctl` | Write-only, root only, whole 32-byte commands `'<I7I'`. Op 1 **durable**: `durable_tick`, `durable_next[5]`. Op 2 **class**: slot 0..7, pid, class (2.11). Op 3 **panel test**: argument = seconds (1..10); `panel_test_seq++`, `panel_test_secs = arg` (2.10). **(r4)** Op 4 **meta**: `meta_sector` (0 clears), `meta_tick` (4.7; **(r5)** shown in the panel's line 6 field, no paint). Anything else `-EINVAL`. `ctl_writes++` per command. One writer at a time (the active collector); each field is one aligned word read by the interrupt with one load |

At init, one `printk`: `PSC5 P4096 POLL2048 W256 S4096 M64 bootnop ret=%d
nw=%d rx2=%02x`, from the boot W record (W `seq` 0). It is the only `printk`
of the instrumentation and is also in the first KMSG chunk.

### 2.9 Execution context of each capture point

| Capture | Context | Interrupts | Preemptible |
|---|---|---|---|
| A1..A4 for P; thread stages; POLL | joypad thread | on | yes |
| A1..A4 for WT | timer interrupt, before `irq_enter` | off | no |
| A1..A4 for WB | `prom_init`, early boot | off | n/a |
| A1..A4 for M | serial initcall, or the task calling `reboot` | on | yes |
| T1, T2 (with the panel paint) | timer interrupt | off | no |
| LED hook, S records, marker | the task doing Memory Stick I/O, under `s_psp_ms_rw_sem`, inside `__bio_kmap_atomic` (`ms_psp.c:254`; `include/linux/highmem.h:49-52`) | on | no |
| fops, `queue_free`, vcs, `mousedev_read`, `do_exit`, vfat hooks (2.12), `wb_kupdate` hook | the calling process (a `pdflush` thread for `wb_kupdate`) | on | yes |
| `/proc/psc` reads, `ctl` writes | the collector (the supervisor reads `stats` only) | on | yes |
| wake and switch hooks (2.11) | the waker with `task_rq_lock` held; `schedule()` of the outgoing task with `rq->lock` held | off (`kernel/sched.c:441`, `:3624`) | no |

### 2.10 Kernel stall panel

**Purpose.** The loss bound in seconds and the kernel's state, on screen and
in photographs, from code that needs no userland and no Memory Stick I/O: the
timer interrupt runs even when no task can be switched (`entry.S:63-64`).
**(r3) The band belongs to the kernel:** rows 176-271 are written only here
(and by `fbcon` if the kernel prints); the HUD never writes them (8.2), so
revision 2's sparing rule and its first-paint race are gone.

**When it paints.** At T2d (ticks ≡ 125 mod 250, never a watchdog tick), once
a ring file has been opened (`proc_opens > 0`), if any of: `now − durable_tick
> 750` (the stick is > 3 s behind; true at start while `durable_tick` is 0);
`now − last_reader_tick > 750`; a test is active (when T2d sees
`panel_test_seq` change it sets `panel_test_until = now + 250 ×
panel_test_secs`; each test paint increments `panel_test_done`); `ms_rdonly`
or `fat_panics > 0` (2.12). **(r5, A5-2)** `meta_sector ≠ 0` no longer paints the panel: META does not threaten durability any more (4.7), and a META that painted would fail every D8 check. While the condition holds the panel is repainted
each second (`panel_state = 2`); at the first check where it is false the band
is painted black once (`panel_state = 1`), and then nothing is painted. Each
paint records `panel_paints`, `panel_last_tick`, `panel_cost_last`,
`panel_cost_max` and, if a P command is in flight, `panel_cmd_id =
psc_t_cmd_id` (SC `lc_flags` b5, A3 OE6).

**How.** Memory stores into the framebuffer at `PSP_VRAM_BASE` = `0x04000000 +
CONFIG_PSP_ADDRESS_BASE` (`include/asm-mips/psp.h:36`), 512 pixels per line,
32-bit pixels (`drivers/video/pspfb.c:28-39`), then `pspClearDcache()`
(`arch/mips/psp/ipl_sdk/cache.c:22-37`) as `pspfb_sync` does
(`pspfb.c:348-352`) on every `fb_sys_write` (`fb_sys_fops.c:89-90`). No SPI,
GPIO or syscon register, no lock, `printk` or allocation. 480 × 96 pixels,
black, a 5×7 font at scale 2 (40 columns × 6 lines; glyphs 0-9, A-Z, space,
`-`, `.`, ≈ 280 bytes), a 2-pixel magenta border. (A `printk` would draw
through `fbcon` in interrupt context and fill the log.)

| Line | Content (columns fixed by Stage 2 in `panellayout.txt`, 10.8) |
|---|---|
| 1 | title `PSC MS RO` (if `ms_rdonly` or `fat_panics`), else `PSC TEST` (test active), else `PSC STALL`; `DUR` durable age in s (one decimal); `RDR` reader age; `PNT` `panel_paints` **(r5: the r4 `PSC MS META` title is gone)** |
| 2 | `NOW` `psp_local_tick` (hex); running task's pid, EPC (bounds-checked `regs`), `preempt_count()` |
| 3 | `jp_loop` (low 16, hex), `jp_stage`, `t_busy`, `t_entry_tick` (hex), `lc_epc` |
| 4 | last P record with `cmd` 0x08: `ret`, `nwords`, `rx[0..8]` |
| 5 | last W record: tick, `epc`, `ra`, `cur_pcnt` |
| 6 | Memory Stick marker: active, sector, pid, start tick; `fat_panics`; **(r4)** `META` and `meta_sector` (hex) when set |

**Cost.** None while healthy (a countdown and a few compares per second). A
paint is ≈ 46,000 pixel stores and one write-back, estimated 0.2-1 ms with
interrupts off (UNVERIFIED; `panel_cost_last`), ≤ once a second, never on a
watchdog tick, only (a) for the PANEL self-test (≈ 5 s, twice, 8.2), (b) during
the start-up creation and catch-up, (c) during a later catch-up or error run
over 3 s, (d) while the collector is stalled or dead, (e) after vfat went
read-only; plus one clearing paint after each. 7.1 states the effect.

### 2.11 Thread wake-up to switch-in (A2 OE3)

**Purpose.** For every wake-up of the thread, the delay until it runs and who
held the CPU, at sub-tick resolution (the H4 exposure, 7.3). **Classes:** 1
WRK (active collector), 2 SUP (supervisor), 3 OSK (`psposk2`), 4 MD (`pspmd`),
5 `pdflush`, from the 8-entry `pid_class` table the collector registers (`ctl`
op 2); else 6 if `mm == NULL` (kernel thread, idle), else 7.

**Hook W** in `try_to_wake_up` (`kernel/sched.c:1507`), just before
`success = 1;` (`:1657`), reached only on an actual activation (not
`out_running`, `:1659`), interrupts off (`task_rq_lock`, `:441`). If
`p == psc_jp_task` (one compare per wake-up): `wk_seq++`; `wk_t0 = wk_last =
(psp_local_tick, read_c0_count())`; `wk_acc = 0`; `wk_nsw = 0`; `wk_cls0 =
class(current)`; `wk_pending = 1`; `wk_seq++`. ≈ 25 instructions, 17.86/s.

**Hook S** in `schedule()`, inside `if (likely(prev != next))` (`:3700`),
before `context_switch` (`:3707`, its only call), interrupts off
(`spin_lock_irq(&rq->lock)`, `:3624`). If `wk_pending` (one load per switch),
with `now = (psp_local_tick, read_c0_count())`: `d = (now.tick − wk_last.tick)
× CPT + now.c − wk_last.c` (u32, saturating); if `class(prev)` is 1 or 2,
`wk_acc += d`; `wk_last = now`; `wk_nsw++`. If `next == psc_jp_task`: publish,
bracketed by `wk_seq`, `wk_delay = min((now − wk_t0) >> 8, 0xFFFF)`, `wk_wrk =
min(wk_acc >> 8, 0xFFFF)`, `wk_cls0`, `wk_cls1 = class(prev)`, `wk_nsw`;
`wk_count++`; `wk_max`; `wk_pending = 0`. ≈ 15 instructions per switch while
pending, ≈ 15 more to publish.

**(r4, A4 F5) Hook S, preemption branch.** If `prev == psc_jp_task`,
`prev->state == TASK_RUNNING` and `psc_t_busy_p` (the thread is switched out
involuntarily inside a command: `Syscon_cmd` never sleeps, a sleep has a
non-zero state, `kernel/sched.c:3627`, `include/linux/sched.h:144`), bracketed
by `pre_seq`: if `pre_cmd_id ≠ psc_t_cmd_id`, reset `pre_tot`, `pre_wrk`,
`pre_n`, `pre_flags`, set `pre_cmd_id`, `pre_cls0 = class(next)`; `pre_t0 =
pre_last = now`; `pre_on = 1`; `pre_count++`. While `pre_on`, every switch does
what hook S does for `wk_*` (`d` into `pre_wrk` if `class(prev)` is 1 or 2;
`pre_flags` b3 if it is not, b4 if it is 3, 4 or 5); at `next ==
psc_jp_task`: `pre_tot += now − pre_t0`, `pre_cls1 = class(prev)`, `pre_n++`,
`pre_on = 0`. `psc_sc_exit` copies them into SC bytes 42-44, 46 and 78-79 (1.2;
byte 45 is `ms_delta`, **§17 R-6**) when
`pre_cmd_id` equals the command's `cmd_id`, between two reads of `pre_seq`.
Cost: one more compare per switch; ≈ 15 instructions per switch while the
thread is preempted. This names the actor of N1, N1m and H10 (6, 6.1).

**Reader:** the thread copies the published fields into POLL at its loop top,
between two reads of `wk_seq`, if `wk_count` changed (else 0).

**Safety.** Both hooks run with interrupts off on a uniprocessor, are the
only writers of `wk_*` and `pre_*`, read only `psp_local_tick`, Count, the class
table and the thread-owned `psc_t_busy_p`/`psc_t_cmd_id` (one load each), take
no extra lock, call nothing, touch no MMIO. A preempted thread is never woken,
so `wk_pending` and `pre_on` are never both set.

**Use.** For every poll that started late in its tick (`c_start > CPT −
median command duration`, the P4/P5a exposure, 7.3): the delay, the
collector's exact share `wk_wrk / wk_delay`, the task running at wake-up and
the last holder (with `wk_nsw = 1` the only holder). The non-preemptible Memory
Stick part comes from S records overlapping the wait (a task cannot be
switched out with a raised preempt count, `entry.S:61-64`, `sched.c:3744`).

### 2.12 vfat read-only detection (r3, A3 IF5 fix 2)

- `fs/fat/inode.c:1415` (the success `return 0;` of `fat_fill_super`):
  `psc_fat_sb = sb;` **(r5)** and the six geometry words of stats 154-159 copied
  from `MSDOS_SB(sb)` (4.8). `/ms0` is the only vfat mount (`rc.sysinit:10`) and
  stays mounted for the run, so the pointer and the words stay valid.
- `fs/fat/misc.c:18` (`fat_fs_panic`, which sets `MS_RDONLY` at `:30-33`):
  `psc_fat_panics++; if (!psc_fat_panic_tick) psc_fat_panic_tick = psp_local_tick;`.
- The stats reader sets `ms_rdonly = psc_fat_sb && (psc_fat_sb->s_flags &
  MS_RDONLY)`; T2d reads the same flag with one load. Either makes the panel
  title `PSC MS RO` and keeps the panel up for the rest of the run (2.10).
  `fat_fs_panic` is the only way the mounted `/ms0` becomes read-only while
  running (no remount; 2.6.22 vfat has no `errors=` option, `misc.c:14-35`).
  **(r5, A5-1 (4), corrected)** Read-only stops new names (`EROFS`,
  `fs/namei.c:237-239`) but not writes into files already open: there is no
  read-only test on the write path (`file_update_time` only skips,
  `fs/inode.c:1227`; `fat_write_inode` has none, `fs/fat/inode.c:556-611`;
  `fat_write_super` skips FSINFO, `:453-459`). The worker then makes no
  creation step, flushes into the files already prepared and holds when they
  are full (4.6); from then on the panel is the record. Under r5 no reported
  error leads to `fat_fs_panic` (4.4 step 5); it remains for silent loss (R11).

---
## 3. History mechanism

### 3.1 Rings (static BSS)

BSS is zeroed by `head.S` before `start_kernel`
(`arch/mips/kernel/head.S:182-187`), so recording works from
`arch_early_setup`, before the boot Nop. Nothing is ever allocated.

| Ring | Writer (one at a time) | Record | Entries | Bytes | Oldest record overwritten after, at the maximum rate |
|---|---|---|---|---|---|
| P | joypad thread | 80 | 4096 | 327,680 | 114.7 s at 35.71/s (17.86 polls/s × 2, dossier 9.1) |
| POLL | joypad thread | 40 | 2048 | 81,920 | 114.7 s |
| W | timer interrupt (IE off); boot Nop | 288 | 256 | 73,728 | 1,280 s at 0.2/s |
| S | Memory Stick path under `s_psp_ms_rw_sem` | 40 | 4096 | 163,840 | ≥ 181 s at ≤ 22.6/s; **(r4, A4-1, per-buffer count)** ≥ 53 s while a file is created at 8 KB per tick (≤ 77/s); ≥ 28 s during 64 KB steps (≤ 144/s, A5-4). The worker drains it every tick (≤ 34 per tick against the cap of 64) |
| M | other threads | 80 | 64 | 5,120 | fill-once; later records only counted (`m_dropped`) |
| **Total** | | | | **652,288** | |

Plus the stats block (768 B) and ≈ 1 KB of other globals and the panel font:
≈ 653 KB. **Guard words (A2 OE4):** a distinct constant before the first ring,
between rings and after the globals (seven words), compared by T2d once a
second; a change is counted (`kguard_bad`, `kguard_first_tick`), never
repaired. A store into the middle of a ring is caught, if at all, by the
reader's `seq` checks (3.5).

### 3.2 What is kept at full resolution, what is summarised

Every `Syscon_cmd` call in every context, every thread loop, every Nop with
its interrupted context and every Memory Stick segment transfer, for the
whole run, on the stick, with no sampling or decimation. The stats block,
written every ≈ 1.8 s, holds whole-run counters that bracket any lost stretch.
The rings are a ≥ 114 s buffer against a takeover, a slow `fsync`, a segment
switch or a starved collector; the stick is the history.

### 3.3 Triggers

**None.** Nothing freezes or changes resolution, and nothing on the device
detects onset (the decoder does, 10.7). A shape that would never fire a
trigger is recorded in full (D5); history before onset is streamed, so
wraparound cannot lose it (D4). The only limit is the 64 MB cap (4.4).

### 3.4 Writer protocol, and why the watchdog interrupting the thread mid-record is safe (D9)

```
s = head; r = &ring[s & (N-1)];
r->seq = 0xFFFFFFFF; barrier();  fill fields; barrier();
r->seq = s;          barrier();  head = s + 1;
```

Uniprocessor, same-CPU reader: compiler barriers suffice; no atomics (LL/SC on
Allegrex is UNVERIFIED despite `.config:109`). If the timer interrupt arrives
while the thread fills a P slot: the Nop writes only the W ring and its own
words (`wd_calls`, `wd_last_tick`, W counters); T2 writes only `lc_*`,
`lc_nested`, `lc_nest_id`, the tick statistics, the panel and guard words.
They **read** thread-owned words (`psc_t_busy_p`, `psc_t_cmd_id`, `t_entry_*`,
`jp_loop`, `jp_stage`, the P head), each one aligned word or byte read with
one load. **No variable is written by two contexts:** busy flags are split
(`psc_t_busy_p` thread, `psc_t_busy_m` others); counters are per ring; `wk_*`
belong to the scheduler hooks, the LED accumulators and marker to the Memory
Stick path (one task under `s_psp_ms_rw_sem`), `durable_*`, `pid_class`,
`panel_test_seq/secs` to the collector (`ctl`), `psc_fat_*` to the vfat hooks,
and `psc_jp_task = NULL` is written once by the thread in `do_exit`. Where
several words must agree the reader brackets them (`lc` by `lc_seq`,
`led_cmd_*` by `led_cmd_id`, `wk_*` by `wk_seq`); the W extension and the
panel run with interrupts off, so no writer runs while they read. When the
interrupt returns the thread continues its P record; its slot was never
touched. The only multi-writer structures are the informational P-counters and
the M ring (a torn M slot is rejected by `seq`; no concurrent M caller is
known, recon §2.1).

### 3.5 Reader protocol (r3: skip and count, A3 IF6)

A `read()` of ring r (N entries) from record `s = f_pos / size`:

1. Load `h = head`. If `s > h` (a head moved backwards): `head_regress++`,
   return what was copied, leave `f_pos` at `s`. If `s == h`: stop.
2. If `h − s > N`, records `s .. h−N−1` were overwritten: `s = h − N` (the
   collector sees the `seq` gap and counts it `lost`).
3. Copy slot `s & (N−1)`, reading its `seq` (volatile) before and after. If
   both equal `s`, deliver it and advance `s`.
4. **Otherwise skip and count:** reload `h`; if `h − s ≥ N` the slot was being
   overwritten by a newer record (a lap, a `lost` gap for the collector); else
   it is corrupt (`s + N` with no head movement, `0xFFFFFFFF` outside a write,
   garbage) and `slot_bad[r]++`. Either way `s++` and continue; a skipped slot
   uses none of the byte budget.
5. Stop when the next record would exceed the bytes requested (the
   collector's cap, 4.3); `f_pos = s × size`. At most N skips per call.

A corrupt slot thus costs exactly one counted record, and a forward head jump
costs the skipped slots, after which the reader is at the head; neither can
stall a ring. Publishing `seq` before `head` (3.4) guarantees that a slot with
`s < h` and the right `seq` is complete.

### 3.6 In-flight state

A stuck thread shows in the stats (`t_busy`, `t_cmd`, `t_entry_*`, `jp_stage`,
`jp_stage_arg`, `jp_loop`, state, signals), in every W record (context, `lc`,
`lc_n`) and, if the collector stops too, on the panel.

---
## 4. Extraction path

### 4.1 Choice: a new collector `pscol`, derived from `telem.c`

`telem` is interactive (raw tty, quits on `q`/ESC, `telem/telem.c:235-245`,
`:357`), falls back to RAM files (`:326`, `:293`) and its log capture goes blind
after 16 KB (dossier 9.1); it stays unchanged as the 9.6 reference. `pscol`
copies its FP-free pieces (`telem.c:249-306`) and blit calls, not its 522 KB
back buffer (`:56`).

### 4.2 Start from `rc.sysinit`; supervisor and worker

Three lines after the existing `pspmd -s&` block
(`extract/root2/etc/rc.sysinit:17-19`), so `mount /ms0` (`:10`), `psposk2`
(`:14`) and `pspmd` (`:18`) start exactly as in the baseline (the initramfs
busybox has no `sleep` applet, so supervision is in C):

```
printf "\\033[37mLaunching PSC collector\\t\\t\\t\\033[0m"
pscol&
printf "[  \\033[32mOK\\033[37m  ]\\033[0m\\n"
```

A bFLT `exec` allocates data + bss + stack as one contiguous `kmalloc`
(`fs/binfmt_flat.c:575-596` → `mm/nommu.c:745`), which may fail late in a run
(A1 IF2), so **nothing is allocated after boot**:

- **One binary, two processes, both started at boot**, each ≈ 100 KB (r5
  estimate) of data + bss + stack (40 KB flush buffer, 4 KB creation template, 16 KB `syslog`
  buffer, 4 KB `kmsg` and 2.4 KB PROCS buffers, 1.9 KB row buffer, **(r5)**
  ≈ 6 KB of extent tables, 2.5 KB of S-window scratch, the 32-entry re-send
  queue and the seen-inode list (4 KB), a 16 KB stack set with `flthdr -s
  16384`). **(§17 R-5, measured at G2 attempt 1)** data 2,896 + bss 112,720 +
  stack 16,384 = 132,000 B, and this kernel's `binfmt_flat` puts the text
  (51,904 B) in the same allocation: `CONFIG_SONY_PSP` forces `FLAT_FLAG_RAM`
  (`fs/binfmt_flat.c:471-472`), so one `do_mmap` takes text + data + bss +
  stack (`:626-628`), a `kmalloc` rounded to a power of two (`mm/nommu.c:744`):
  183,968 B in **one 256 KB block each**, both allocated at boot, none later;
  G2 C8 records the figure (≤ 256 KB).
- **Supervisor** (`pscol`, no arguments): `setsid()`; `/dev/null` on fds 0-2;
  ignores SIGINT, SIGQUIT, SIGHUP, SIGTSTP, SIGTTIN, SIGTTOU, SIGPIPE;
  `mkdir /ms0/PSCLOG` only if it is missing (RUNBOOK A4 creates it on the Mac,
  so normally nothing is allocated at boot); run number `rrr` = 1 + the largest
  `rrr` among names `T<rrr><nnn>.BIN` (1 if none, ≤ 999); **(r5, IF10)** boot
  nonce = `total_counts` low word XOR `now_count` XOR (`getpid()` << 20) from
  one `stats` read, 1 if that is 0 (10.2); `vfork` + `execve("/usr/bin/pscol",
  "-w", rrr, nonce)`; then every 2 s `waitpid(-1, WNOHANG)` and a `stats` read
  (which does not touch `last_reader_tick`). It writes neither the stick nor
  `ctl`.
- **(r3) Takeover, replacing the standby.** If the worker has died (including
  a guard exit), or if `durable_tick ≠ 0` and both `now − durable_tick` and
  `now − last_reader_tick` exceed 7500 (30 s), the supervisor sends SIGTERM (for
  a stall) and **runs the worker loop itself**, in-process, as instance 2: no
  `exec`, no allocation (its boot-time block has the worker's size). There is
  then no supervisor (HUD `SUP RUN`). A stalled old worker exits on the
  pending SIGTERM at its next return to user mode, before any further `write`.
  The new worker creates a fresh segment (4.4) and never writes a file the old
  one had open.
- **Worker** (`pscol -w rrr nonce`, or the supervisor after a takeover, same
  `rrr` and nonce): **(r5, OE8; r7, A6-2)** sets console log level 4 (7.1) with
  the kernel's `syslog` call, `syscall(__NR_syslog, 8, 0, 4)` as `telem.c:281`
  makes it for type 3 (equivalently `klogctl(8, NULL, 4)`,
  `staging_dir/usr/include/sys/klog.h:30`; not the C library's `syslog()`),
  and writes its return and `errno` in EVENT `conlevel <ret> <errno>` (0 on
  success, `kernel/printk.c:292-300`); opens the ring files, seeks each to `durable_next` (0 at
  the first start, which keeps the boot WB record), counts the names budget
  (4.4 step 6), registers pid classes (`ctl` op 2: itself 1, the
  supervisor 2 unless after a takeover, `psposk2` 3, `pspmd` 4, every
  `pdflush` found by name in `/proc/*/stat` 5), creates its first segment and
  runs the tick loop (4.3). It never exits on a runtime error (each is counted,
  shown, written as an EVENT, retried), only on SIGTERM, a crash, or a guard
  violation.
- **Memory guards (A2 OE4).** User processes keep kernel privilege (7.1):
  `pscol` guards its buffers and both ends of its data + bss with 16-byte
  patterns, checks a pre-filled stack's high-water mark, takes every `read()`
  length from one asserting helper, bounds its parsers (including the S-record
  and `FIBMAP` tables of 4.8); every tick; on a
  violation UHB b16, a last EVENT `guard <which> <tick>` if the flush buffer is
  intact, `_exit(3)`, takeover. `guard ok stack_hw=<bytes>` at start. The
  decoder labels later onsets **`instrumentation-suspect`**.
- **Supervisor dies:** `SUP DEAD`; a later worker failure is not recovered and
  the panel appears within 4 s (R14). **No `/proc/psc`:** `PSC NO KRN`, retry.
- **Never:** `pscol` never opens `/dev/joypad` (an extra queue changes the
  push loop; closing it exercises H9, `joypad_psp.c:346-360`), never reads a
  tty, never calls `statfs` (4.4), never truncates, unlinks or reopens a
  segment, **(r5)** never writes through an alias of a cached inode (4.4 step
  1), never extends or `FIBMAP`s a file at or above its confirmed size.

### 4.3 Worker tick (telem's cadence: `nanosleep(200 ms)` per loop, `telem.c:54,415`, ≈ 0.23 s)

1. **Snapshot**: read `stats`; keep the heads `H_r` and `now_tick`
   (`drain_tick`); `H_S` also opens the flush's S window (4.8).
2. **Capped drain**: for each ring (W, P, POLL, S, M) read at most `cap_r × m`
   records (`cap` P 48, POLL 24, W 2, S 64, M 8; `m = min(4, max(1, ⌈Δt /
   0.23 s⌉))`, Δt since the previous drain), then the position
   `pos_r = lseek(fd, 0, SEEK_CUR) / size`; count `seq` gaps (`lost`).
   **(r3, A3 IF6) The drain is complete only if `pos_r ≥ H_r` for every
   ring.** A ring that returned its full cap is in **catch-up** (HUD
   `CATCHUP`, UHB b12, EVENTs at start and end). A ring that returned fewer than
   asked while `pos_r < H_r` is **stuck** (the reader of 3.5 cannot produce
   this): `drain_stuck++` (UHB word 19), EVENT `drain stuck <ring> <pos>
   <head>`, HUD `REC` red; likewise any `lost` or `slot_bad` increase after the
   first complete drain. **(r4, A4 IF3)** A rise of `head_regress` (3.5 step 1)
   seeks that ring to its head `H_r`, writes EVENT `head regress <ring> <pos>
   <head>` and turns `REC` red; the jump is counted, the ring is not stalled.
3. `/proc/kmsg` (`O_NONBLOCK`, `fs/proc/kmsg.c:36`) → a KMSG chunk if new; one
   `syscall(__NR_syslog, 3, buf, 16384)` as telem (`telem.c:279-282`), into the
   16 KB buffer, for load parity only.
4. Every 40th tick (≈ 9 s), PROCS: `/proc/<pid>/stat` of the thread (`jp_pid`),
   `psposk2`, `pspmd`, the worker; `State:`, `SigPnd:`, `ShdPnd:` of the
   thread (`fs/proc/array.c:167,275-279`); `MemFree`.
5. Drain `/dev/input/mice` (non-blocking, as `telem.c:249-274`): packets and
   press edges (`IN`), a delivery check that bypasses both daemons.
6. Read `/proc/meminfo` and `/proc/uptime` (as telem).
7. **Flush** into the active file if `seg_end + 40,960` ≤ its usable limit
   (4.4): RECS (**(r5)** re-sent ranges first, 4.6), UHB, STATS every 8th tick,
   and PROCS, KMSG, EVENT if due and they fit, then PAD to the next 512-byte
   boundary; `lseek(fd, seg_end)`, one `write()`, `fsync()`, both timed;
   `seg_end += length` **whatever the result**. **(r5) Verdict from the S
   records of the window (4.8), not from `fsync`.** DURABLE: the flush's records
   are durable; `durable_next[r]` and `durable_tick` advance as 4.6 defines
   (`ctl` op 1). FAILED: 4.6.
8. **Creation step**, if a file is being created or a new one is due (4.4,
   including the alias test of step 1), with its own verdict (4.8); then META
   (4.7) and the bad-region rule (4.6).
9. **HUD** (8.2): ten lines rendered row by row into the 1,920-byte row buffer
   and written with `lseek` + `write` to `/dev/fb0`, rows 0-175 then rows 0-95
   again: 272 writes of 1,920 bytes, **exactly telem's blit calls**
   (`telem.c:299-306`), each through `fb_sys_write` → `pspfb_sync` →
   `pspClearDcache` (`fb_sys_fops.c:89-92`). **Rows 176-271 are never
   written** (2.10).
10. Check the memory guards (4.2); `nanosleep(200 ms)`.

**Bounds.** Records per unit of `cap`: 48 × 80 + 24 × 40 + 2 × 288 + 64 × 40 +
8 × 80 = 8,576 bytes; with `m ≤ 4` a RECS chunk is ≤ 34,304 + 80 (block
headers: per ring one new-records block and at most one re-send block, 10.2;
re-sent records count inside the cap, 4.6) + 20 = **34,404 bytes** (< 65,536;
**§17 R-6**: 34,364 left out the re-send blocks). With STATS 788, PROCS ≤ 2,420,
UHB 104 and the PAD header: 37,736 → 37,888, within the **40,960-byte flush
buffer**; KMSG (≤ 4,116) and EVENT (≤ 1,044) are added only if the flush stays
≤ 40,960, else deferred (EVENT queue 8 KB; on overflow one
`events dropped <n>`). Nominal flush 1.5-3.5 KB (5.1).

**No ring laps while the worker runs** (`4 × cap_r / T` above the rate: P and
POLL for T < 5.4 s, S < 6 s, W < 40 s); a longer stall is 4.5's case.
**Catch-up:** records overwritten before the first read count as `lost`; then a
full P ring drains in ≈ 14 s (`m` = 2) to 33 s (`m` = 1, T = 0.3 s). Catch-up
flushes (10-38 KB) are an exposure (7.5), recorded and reported.

### 4.4 Segment files: grown in steps confirmed from the S records (r3 IF5; r4 A4 F2, F3; r5 A4 F1(b), F4, A5-1, A5-3)

**The defect removed (r3).** In revision 2 a growing segment allocated a cluster
whenever a flush crossed a boundary (`fs/fat/inode.c:83-88` → `fat_add_cluster`
`:40-52` → `fs/fat/fatent.c:434-509`, `fs/fat/misc.c:78-110`); a failed write
of that FAT sector left it not up to date and never rewritten
(`fs/buffer.c:429-451`) while the retried data succeeded, orphaning "durable"
records, and the next allocation re-read the stale sector
(`fs/buffer.c:1378-1384`) and called `fat_fs_panic` (`fs/fat/cache.c:254-259`),
making `/ms0` read-only (`fs/fat/misc.c:30-33`). **A flush never extends a
file.** (r4) But a file need not be complete before flushes use it.

**Name, size:** `/ms0/PSCLOG/T<rrr><nnn>.BIN`, an upper-case 8.3 name, so one
directory slot and no long-name entries (`fs/vfat/namei.c:599-602`, `:623-624`),
from 001; at most **SEG = 2,097,152 bytes** (4,096 sectors), ≈ 4.6 minutes of
records. Each file has a **confirmed size** `conf`: the end of the last creation
step whose verdict (step 4, 4.8) was CONFIRMED and whose `fstat` agreed. It is
**complete** at `conf = SEG`; its **usable limit** is SEG if complete, else
`conf`. **(r5, A4 F1(b))** Each file keeps an **extent table** (≤ 128 runs of
file block, stick sector, length), filled by `FIBMAP` once per confirmed step for
the clusters that step added (4.8); flush verdicts use it.

**Creation**, by the worker only, one file at a time, **while fewer than two
complete files wait ahead of the active one** (steady state: two complete files
ahead and nothing in creation; when one of them becomes active, the next
creation starts. **(r5, A5-4)** The r4 parenthesis "one ready, one in creation"
did not describe this rule.)

1. **Open, with the alias test (r5, A5-1).** `open(name, O_RDWR | O_CREAT |
   O_EXCL)`, `nnn` = 1 + the largest of this run at worker start, then +1 per
   name used; `EEXIST` → next number. Then `fstat`: the file is **fresh** only if
   `st_size == 0` and `st_ino` is not one this worker instance has seen (it
   records every `st_ino` it is given). Otherwise the kernel has handed back a
   cached inode, an **alias**: `vfat_create` → `fat_build_inode` → `fat_iget`
   returns any cached inode whose `i_pos` is the slot just taken
   (`fs/vfat/namei.c:745-750`, `fs/fat/inode.c:276-295`, `:398-405`), and a slot
   is free on the stick again when an earlier attempt's directory write failed
   (the buffer is left not up to date and is re-read from the stick,
   `fs/buffer.c:128-146`, `:1378-1384`; `fat_add_entries` takes the first free
   slot, `fs/fat/dir.c:1202-1226`). For an alias: EVENT `inode reused <name>
   <ino>`, UHB b28; **nothing is ever written through it**, and it is closed,
   which writes nothing (`fat_file_release` acts only with the `flush` mount
   option, `fs/fat/file.c:117-125`, which `rc.sysinit:10` does not set; the
   cached inode is clean: its own failed `fsync` cleared `I_DIRTY` before
   writing, `fs/fs-writeback.c:163-166`, and `vfat_create` does not dirty it,
   `fs/vfat/namei.c:756-758`).
   **Why the next `open` gets a fresh slot:** `fat_add_entries` has put the
   alias's **own** entry (its name, start 0, size 0) into the up-to-date
   directory buffer (`fs/fat/dir.c:1255-1256`, `:1266-1267`), so the
   first-stage scan of the next `open` (`fs/fat/dir.c:1212`, `IS_FREE`,
   `msdos_fs.h:47`) passes that slot and takes a later one; a later slot
   carries a cached inode only if its own entry was lost too, and the same test
   catches that. The worker therefore opens again **in the same tick**, at most
   24 `open`s, **while the stick is working**: the most recent S window (this
   tick's flush, or when holding the last operation's, 4.8) shows a successful
   write. The aliases' entries reach the stick with the next successful
   `sync_blockdev` (normally the fresh file's own step 0) and stay as empty
   files. **When the stick is not working** (an outage, or a hold during one),
   the first alias is a probe instead: the worker `fsync`s its descriptor once,
   which writes no data and no inode (as above) and makes `sync_blockdev` write
   the dirty metadata buffers: the alias's directory sector and FSINFO
   (`fs/sync.c:55-76`). If that window shows a successful write, the alias's entry is now on
   the stick and the loop continues; if not, the attempt ends and the next one
   waits ≥ 10 s (step 6). An outage thus costs one name per attempt and leaves
   at most one free-on-disk slot behind, however long it lasts. (Without the
   probe rule a fresh file per attempt would add a lost slot each time, and
   every later attempt would pay one alias per lost slot.) A fresh file goes on
   to step 0 in the same tick. **Size-0 aliases
   after a takeover:** the new instance has not seen the old instance's inodes,
   so an alias of an inode the old instance created but never wrote passes the
   test; such an inode has `i_start = 0` and no chain (`fat_chain_add` walks
   only when `i_start ≠ 0`, `fs/fat/misc.c:88-96`), and writing through the new
   name puts the new entry's start and size into the slot that holds the new
   name, so it is safe.
2. **Step 0** writes a FILEHDR flush at offset 0 (FILEHDR + PAD = 1,536 B,
   10.2), so no tick flush ever contains a FILEHDR, then `fsync`.
3. **Later steps** write `k` bytes of **PAD sectors** at `conf` with one
   `write()`, then `fsync()`, **always**, even after a short or failed
   `write()`, so a step's metadata is written inside its own window (4.8). A PAD
   sector is a complete 512-byte PAD chunk (`PSCK`, type 0, `len` 492, `fseq`
   0xFFFFFFFF, CRC of 492 zero bytes with the boot nonce as initial value, 10.2,
   zero payload), from a 4 KB template. **(r5, A5-3) `k` = 64 KB while the
   worker holds, or while the active file's room `conf − seg_end` is below
   81,920 bytes (two maximal flushes); 8 KB otherwise** (256 steps for a whole
   file); the last step stops at SEG. (r4 used 64 KB for as long as the active
   file was incomplete, which stretched every start-up tick, A5-3.)
4. **Verdict (r5, 4.8).** A step is **CONFIRMED** when `write()` returned `k`,
   no FAT1 write in its window failed (and at least one succeeded if the step
   allocated: a step allocates if it writes a block at the start of a cluster,
   `⌊(conf + k − 1)/cl⌋ > ⌊(conf − 1)/cl⌋`, step 0 always, `cl` = `st_blksize`,
   `fs/fat/file.c:310`, `fs/fat/inode.c:82-85`), every data sector the step
   wrote has an error-free S record (sectors from `FIBMAP` of the new clusters,
   done only after the FAT check), and `fstat` gives `conf + k`; **step 0 also
   needs its own directory-entry write** to succeed. **(r7, A6-1) The own-entry
   write is the first DIR-class write record (b0 set) carrying the worker's pid
   after the last DATA record of the step's own data sectors in the window**;
   it must exist and have b1 clear. The order is this tree's: `do_fsync` writes
   the data first (`filemap_fdatawrite`, `fs/sync.c:90`, completed inside the
   driver, `ms_psp.c:228-236`), then calls vfat's `file_fsync` (`fs/sync.c:97`;
   `fs/fat/file.c:136`), whose `write_inode_now` (`fs/sync.c:62`;
   `WB_SYNC_ALL`, `fs/fs-writeback.c:568-576`) runs `__sync_single_inode`:
   data pages (`:170`, already clean), then `fat_write_inode(inode, 1)`
   (`:173-174`), which writes the entry's sector at once with
   `sync_dirty_buffer` (`fs/fat/inode.c:571`, `:604-606`); only then do
   `write_super` (`fs/sync.c:67-68`; it only marks FSINFO dirty,
   `fs/fat/inode.c:453-459`, `fs/fat/misc.c:40-72`) and `sync_blockdev`
   (`fs/sync.c:72`, `fs/buffer.c:152-159`) write FSINFO, FAT1, the mirrors and
   every other dirty directory sector. A DIR write record of another pid
   (`pdflush`, 2.7) between that last DATA record and the worker's first DIR
   record makes step 0 not CONFIRMED (`pdflush` may have written the entry's
   buffer between `mark_buffer_dirty` and `sync_dirty_buffer`,
   `fs/fat/inode.c:604-606`, the worker being preemptible there,
   `CONFIG_PREEMPT_BKL=y`, `.config:136`, and `sync_dirty_buffer` then writes
   nothing, `fs/buffer.c:2708-2709`); anywhere else in the window a `pdflush`
   DIR record is ignored. **Any other failed DIR write in the window** (for
   example a refusing sector holding rejected aliases' entries, IF7b, 15.3)
   **is META evidence only** (4.7) and never abandons the file. Then
   `conf += k`. FSINFO, FAT-mirror and directory failures other than step 0's
   own entry do not stop growth, at step 0 as at later steps: the chain on the
   stick is whole without them; they are META evidence (4.7).
   - **A FAT1 write of the step failed:** the file **stops growing** (EVENT
     `stop <name> <conf> <errno> <step>`, UHB b24): its in-memory chain may end
     in a link the stick does not hold.
   - **Anything else failed** (a data sector, a short `write()`): the step is
     **retried in place** at the next tick, up to 3 times. Its blocks are mapped
     (`mmu_private` advances per block, `fs/fat/inode.c:93`) and its clusters
     are linked on the stick (FAT1 was written), so the retry allocates nothing
     (`:68-72`). A fourth failure stops growth.
   - **Step 0 is never retried in place:** if it is not CONFIRMED the file is
     abandoned, since
     its entry may be lost and a rewrite would put a start and size into a slot
     with no name (`fat_write_inode` writes size, attributes, start and times,
     not the name, `fs/fat/inode.c:586-600`).
5. **Stopped and abandoned files (restated for kernel-reused inodes, A5-1).** A
   stopped or abandoned file is never written at or above `conf`, never
   extended, truncated, unlinked or reopened, and never `FIBMAP`ed at or above
   `conf`; the worker never writes through an alias (step 1). So **no FAT walk
   ever reaches an unconfirmed link**: `fat_get_cluster` reads only the entries
   of the clusters before the one it maps (`fs/fat/cache.c:241-251`), a flush
   maps only blocks below `conf`, and a `write()` that fails truncates only when
   it extends the file (`mm/filemap.c:2161-2162`), which a flush never does.
   The one way back to an abandoned file's inode that the worker does not
   control is the kernel's slot reuse, and step 1 rejects it before any write.
   With `conf ≥ 1,536 + 40,960` a stopped file is **prefix-usable**: it takes
   flushes below `conf` like any file. Otherwise it is **abandoned** (EVENT
   `abandon <name> <errno> <offset> <step>`, UHB b17, HUD line 7 `WAIT`), closed,
   and never held a record.
6. **Next attempt (r5, F4 in full; one rule, A5-4).** After a stop or an
   abandon, the next creation starts **at the next tick** if the failed
   operation's window (4.8) shows at least one successful write (the failure is
   local: a FAT, directory or data sector; IF7b, IF8, IF9), at most
   `min(400, budget / 2)` such fast attempts per run (≥ 200: IF8 needs ≤ 128,
   IF7b ≤ 16 per creation that meets the refusing sector (≤ 153 names, 15.3));
   otherwise (the whole stick refused) **≥ 10 s later**.
   **Names budget:** at most `min(999, free directory slots − 16)` names per run
   (aliases included), counted at worker start (`stat` of `PSCLOG` gives its
   size in whole clusters, `fat_calc_dir_size`, `fs/fat/inode.c:307-319`;
   `readdir` gives the used slots; deleted slots count as free), so the `PSCLOG`
   directory is never extended during the run (an extension allocates and links
   a directory cluster, `fs/fat/dir.c:1277-1295`). A budget below 400 is
   `MS DIR FULL` at the self-test (8.2, an abort).
7. **Completion.** At `conf = SEG`, `fstat` must give `st_size == SEG`; the
   worker drops the last page from the page cache with
   `fadvise64_64(fd, SEG − 4096, 4096, POSIX_FADV_DONTNEED)` (7.4) and `pread`s
   the last 512 bytes, which must equal the PAD sector. The file stays open,
   keeping its inode and cluster cache: it is **ready** (EVENT `segment
   ready`). A wrong read-back stops it as in step 4 with `conf = SEG − k`; one
   that did not reach the stick (stats `ms_seg_rd` unchanged) is EVENT
   `readback cached`.
8. **Cap (F3).** Creation stops when the confirmed sizes of complete and
   prefix-usable files reach 64 MB (≈ 2.3 h); abandoned files do not count.
   Worst-case stick use is 64 MB + 999 names × ≤ 128 KB (an abandoned file
   holds at most step 0 and one failed 64 KB step) ≈ 189 MB; RUNBOOK A3 requires
   256 MB free, so ENOSPC and the full FAT scan it would cause (OE2) cannot
   occur.

**Use and switch (F2).** Tick flushes go from `seg_end` upward in the
**active** file and only while `seg_end + 40,960 ≤` its usable limit, so every
flush lies below `conf`. When the next one would not fit, or **(r5, IF9)** the
active file has been retired (4.6), the worker **switches** to the oldest file
that has never been active and is complete, or prefix-usable with room
(`1,536 + 40,960 ≤` usable limit), or still in creation with that much room:
`seg_end = 1,536`, the old file is closed (EVENT `switch <old> <new> full|bad`,
UHB b19); a file still being created may become active and keeps growing (UHB
b25). **(r7, TE10)** A file that has been active is never a switch target
again, and `seg_end = 1,536` is set only for a file that was never active.
When the active file is itself still in creation (and not retired) and the
next flush does not fit, the worker does not switch: it holds as below, with
64 KB steps, and resumes flushing **in the same file at its own `seg_end`**
once `seg_end + 40,960 ≤ conf`. With no switch target it **holds**:
rings are read with zero bytes (alive, not a stall), so they buffer (≥ 114 s),
`MS WAIT SPARE` and UHB b0 show, the panel appears after 3 s, and creation runs
at 64 KB per tick. At start-up the first file takes flushes **one 64 KB step
after its FILEHDR** (≈ 1-4 s at 300-25 KB/s, 6.2).

**Why a flush never allocates or dirties a FAT sector.** Every flush ends at
or below `conf` ≤ `mmu_private` (the in-memory end, which a failed step may
have moved further). `fat_prepare_write` → `cont_prepare_write`
(`fs/fat/inode.c:143-148`, `fs/buffer.c:2073-2146`) extends nothing for a page
wholly below it (`:2111-2113`) and, on the page holding it, zero-fills nothing
for a write that ends below it (`:2114-2126`); `fat_get_block` finds every
block mapped (`fat_bmap`, `fs/fat/cache.c:295-329`, `last_block` from
`mmu_private` at `:312-315`) and returns at `fs/fat/inode.c:68-72`, before the
allocation branch (`:73-88`). A flush therefore writes data sectors, the
directory entry (rebuilt by `fat_write_inode` from the in-memory inode,
`fs/fat/inode.c:556-611`) and FSINFO (rebuilt on every `fsync`,
`fs/fat/misc.c:40-72`), never a FAT entry. Writes are 512-byte aligned on
512-byte blocks, so nothing is read first. With the cluster cache
(`fs/fat/cache.c:80-115`, `:217-274`) holding the chain, which it does for a
contiguous file from the allocator's sequential search (`fs/fat/fatent.c:455`;
contiguity UNVERIFIED), a write does not even read the FAT. A creation step
writes only at or above `conf` and a flush only below it, in that order within
a tick (4.3), and **(r5)** each verdict reads only the S records of its own
window (4.8), so each error is charged to the operation that caused it.

**The read-back is deliberately shallow:** it proves the last data sector
reached the stick at the mapped location, but does not reopen the file to walk
the on-disk chain, because over a silently lost FAT write that walk would
itself call `fat_fs_panic` and end the stream, whereas writing through the
cluster cache keeps recording, recoverable from a raw image (R11).

**A file holds** FILEHDR (0-1,535), tick flushes from 1,536 to `seg_end`
(each region handed to `write()` once; a failed one is skipped, 4.6), PAD or
unwritten space above; the decoder skips PAD and CRC-bad chunks and removes
duplicates.

**No `statfs` on the device:** it would read the whole FAT
(`fs/fat/inode.c:540-541` → `fatent.c:586-610`; the free count is always
unknown here, `usefree` off, `inode.c:955`, `:1311-1313`, `rc.sysinit:10`).
Free space is checked on the Mac (RUNBOOK A3). STICK (8.2) needs `/ms0` vfat in
`/proc/mounts`, the first flush DURABLE with the geometry self-check, the first
complete drain, ≥ 30 KB/s measured and the names budget; before that line 6
shows `MS PREP`, and `MS NO STICK`, `MS SLOW` or `MS DIR FULL` at 3:00 is an
abort. There is no fallback to a RAM file.

### 4.5 What a battery pull loses (D6)

**(r5, A4 F1(b))** A flush is **durable** when its verdict is DURABLE (4.8):
every data sector it covers has an S record with the error bit clear, in
clusters whose FAT links were confirmed by creation steps (4.4), **whatever
`fsync` returned**. The S record of a segment is written after the driver has
transferred it (before `up()`, 2.4) and the driver completes requests
synchronously (`ms_psp.c:228-236`), so the record is the stick's own answer.
The worker then publishes `durable_tick` (advanced only on a complete drain
with no failed range waiting for re-send: **every record produced before it is
on the stick**) and `durable_next[5]` (4.6). The **kernel** compares
`durable_tick` with now once a second and paints the panel (2.10) when the
stick is more than 3 s behind, with the age in seconds; nothing in userland can
draw over it, so a stalled writer cannot freeze a benign value on screen and a
live one cannot erase it. Where the directory entry on the stick lags (a
directory sector that refused, IF7b, or a pull before the next `fsync`), the
records are on the stick but beyond the size a Mac copy shows; the raw image
recovers them (10.2) and is mandatory in exactly those cases (UHB b23/b30,
RUNBOOK E2).

**The pull check (RUNBOOK D8):** during a 5 s watch the heartbeat block
changes, the kernel panel is never shown, and the HUD `MS` line is not red,
shows none of `CATCHUP`, `READ-ONLY`, `WAIT SPARE`, and shows `DUR` < 3 s
(**(r5)** `META` may show; it no longer blocks the check, 4.7). Kernel and
writer must agree; the panel appears ≤ 1 s after its condition starts, so a
5 s watch cannot miss a persisting condition.

**Case 1, the check passes: worst-case loss 4 s before the check** (3 s of lag
at the kernel's last check, ≤ 1 s old), inside the 30 s hands-off wait, so the
whole script is on the stick; nominal loss 0.3-0.6 s (UNVERIFIED). This holds
on every path (resumed stall, takeover, error run, segment switch, META): until
the interval is durable the panel shows and `DUR ≥ 3`, `CATCHUP` or red appears.

**Case 2, it does not pass:** a pull loses everything after `durable_tick`,
and the panel states it. A resumed worker or a takeover (≤ 30 s after a stall,
plus one 64 KB step of a fresh file, 4.4) still finds the last 114.7 s in the
rings, so the runbook waits up to **90 s**, and **45 s more** while the
heartbeat moves and `CATCHUP` shows (a live worker's backlog drains in ≤ 33
s); otherwise it pulls and records the `DUR` shown, and the panel photographs
keep the kernel's view. Case 2 needs two collector failures, a stick refusing
every write for minutes, or vfat read-only after the prepared files are full
(4.6); a Memory Stick hang with a raised preempt count (A1 OE1) stops every
task, the thread included (unlike the 9.6 deaths), and the panel identifies it.
A chunk cut by the pull fails its CRC and is dropped; if the pull damages
directory or FAT sectors, the decoder scans the raw image.

### 4.6 Stick errors

- **A failed flush is never overwritten (r4, A4 F1a).** `seg_end` has already
  passed the whole region handed to `write()` (4.3 step 7), so nothing is
  written there again. **(r5, A4 F1(b)) Its verdict comes from the S records
  (4.8), not from `fsync`.** A DURABLE flush whose `fsync` returned an error (a
  refusing FSINFO, directory or FAT-mirror sector) is durable: UHB b30, EVENT
  `flush meta err <errno>` at most once per 10 s, `last_errno`; the `MS` line is
  not turned red. A **FAILED** flush: UHB `write_errs`, `last_errno`, the `MS`
  line red until 10 s without a FAILED verdict, EVENT `flush fail <seg_end>
  <len> <errno>`, and its records are queued for re-send.
- **(r5, A5 IF4 G2) Range re-send.** A FAILED flush's records are queued as one
  `seq` range per ring (≤ 32 queue entries; adjacent ranges merge; on overflow
  the two oldest merge into their span, so some records are sent twice and the
  decoder removes the duplicates). From the tick after the next DURABLE flush,
  each drain takes the queued ranges first, oldest first, inside the normal cap
  (the ring file is `lseek`ed to the range start and back, counted in
  `ring_rewinds`), then new records; the RECS chunk carries them in a re-send
  block per ring (10.2). A re-sent flush that fails is queued again. **A
  DURABLE flush is durable for its own records** (r4 discarded the first
  success after a failure and re-sent everything since, which cost two
  flushes of durability per failure and lost records at 25 KB/s, A5 IF4).
  `durable_next[r]` = start of ring r's oldest queued range, else the position
  after the last DURABLE flush; `durable_tick` stays at the value it had before
  the oldest queued failure until that range is durable. While flushes keep
  failing nothing is re-sent, so a failing flush carries only its tick's new
  records (≈ 2 KB) and an outage wastes little space. A record older than the
  ring when its range is read is lost and counted (`lost`, 3.5 step 2).
  EVENT and KMSG payloads stay queued until a flush carrying them is DURABLE
  (A4 IF1 note: `/proc/kmsg` reads consume). A failed page is left cached with
  an error mark (`fs/mpage.c:82-85`) or not-up-to-date buffers
  (`fs/buffer.c:449-451`), and later flushes dirty only their own buffers of a
  shared page, which writeback writes alone (A4 red team S10,
  `fs/buffer.c:2073-2141`). No FAT link can be lost (4.4), nothing reported
  durable can be orphaned, and no `fat_fs_panic` lies on this path (4.4 step 5).
- **(r5, A5 IF9) A bad data region is escaped.** When three consecutive
  flushes into the active file are FAILED with an error on a DATA sector while
  some other write in the same windows succeeded (a local data failure, not a
  whole-stick outage), the active file is **retired**: EVENT `region bad <name>
  <seg_end>`, UHB b27; if it was still being created it stops growing. The
  worker switches to the next usable file (4.4 "Use and switch") and, if the
  same happens there, again; with none it holds (the rings buffer ≥ 114 s) and
  creates at 64 KB per tick in clusters past the allocator, which lie beyond a
  region inside older files. The queued ranges are re-sent into the new file
  after its first DURABLE flush. (The r3 rule "switch after three failed
  flushes" is back, limited to local data failures; r4's "flushes never meet the
  same sectors twice" was true, but a region longer than one flush was crossed at
  flush speed, ≈ 2 KB per tick, A5 IF9.) A bad region ahead of the allocator
  fails creation steps instead (data-only failures: retried, stopped, next
  attempt fast, 4.4 step 6), each attempt moving the allocator past the
  clusters it took.
- **A creation step fails:** 4.4 steps 4-6. The active file is unaffected: its
  blocks below `conf` were linked and confirmed by its own steps. A stopped
  file's chain may end, on the stick, in a link to a cluster whose own entry was
  not written (L → c with c free: the A5 red team's IF5 residual): flushes below
  `conf` never read that link (4.4 step 5) and never truncate
  (`mm/filemap.c:2161-2162`), but a Mac copy of that file may fail because its
  directory size covers c, so the raw image is mandatory (RUNBOOK E2; R11).
- **During a whole-stick burst nothing stops:** draining (capped) continues;
  every flush goes to fresh space with only its new records; `durable_tick`
  stops, the panel appears after 3 s and stays; creation attempts wait ≥ 10 s
  (4.4 step 6). After the first DURABLE flush the queued ranges return.
  **(r5, corrected; simulated, 15.6):** an outage of up to 90 s at 25 KB/s and up
  to 100 s at ≥ 30 KB/s loses nothing; a longer one loses the records that pass
  the ring span (114.7 s) before they are re-sent, counted, unless their first
  write reached the stick (the raw image shows them). The r4 sentence "a burst
  shorter than the ring span loses nothing" overstated this by the re-send and
  catch-up time. A failed flush wastes ≈ 2 KB (≤ 40 KB for a catch-up flush).
- **Read-only `/ms0` (r5, A5-1 (4), corrected).** `fat_fs_panic` sets
  `MS_RDONLY` (`fs/fat/misc.c:30-33`). Files already open still write (2.12).
  On `ms_rdonly` or `EROFS` the worker shows HUD `MS READ-ONLY` in red, sets UHB
  b21, writes an EVENT, makes **no creation step** (the file system reported an
  inconsistency, so nothing more is allocated), and flushes into the active
  file, then the complete and prefix-usable files (their space is linked and
  confirmed), then holds. Recording thus continues for ≈ 0-9 minutes; the panel
  shows `PSC MS RO` for the rest of the run (2.12) and the runbook photographs
  it once a minute (RUNBOOK C4).
- **ENOSPC** cannot occur (4.4 step 8, A3: 256 MB against ≤ 189 MB).
  **Takeover** still needs both ages over 30 s: a worker that reads but cannot
  write is not replaced (a new one writes the same stick).

### 4.7 A metadata sector that keeps refusing writes: META (r4; r5 full scope)

**Detection.** The worker examines every S record it drains (1.5: `sector` @16,
`pid` @22, `flags` @25 b0 write, b1 error, b7 metadata). A metadata sector X is
**stuck** when its last 5 write records all have b1, with no successful write of
X between them, over ≥ 3 ticks, and in each of those ticks a data write (b0
set, b7 clear) by the worker succeeded. FSINFO and the `PSCLOG` directory sector
are rewritten by every `fsync` (FSINFO `fs/fat/misc.c:40-72`; directory entry
`fs/fat/inode.c:556-611`, the inode being dirtied by every write,
`mm/filemap.c:2276`), so a refusing one is stuck within 3-5 ticks (≈ 1-2 s); a
refusing FAT sector at the allocator is written by every creation attempt (fast
attempts, 4.4 step 6), stuck within ≈ 5 ticks. A whole-stick burst never
qualifies (its data writes fail too), nor does a sporadic error (five in a row
on one sector). **(r5)** The class (FAT1, FATM, FSINFO, DIR, OTHER, 4.8) is
reported with it.

**(r5) What META means now.** Durability is judged from data sectors (4.8) and
growth from FAT1 and data (4.4 step 4), so a refusing FSINFO sector (IF7a),
`PSCLOG` directory sector (IF7b) or allocator FAT sector (IF8) no longer stops
recording: flushes stay DURABLE and `durable_tick` advances, files keep
growing, and new files find a working slot (aliases rejected and skipped, 4.4
step 1) or a working FAT sector (fast attempts, ≤ 128 per FAT sector of 128
entries). The traces are in 15.3. What remains is a stick whose file table may
not describe all the data (a file whose entry never reached the stick, or whose
size there lags), which the raw image covers.

**Display.** On the first stuck sector: `ctl` op 4 (`meta_sector`, `meta_tick`,
stats 150-151), EVENT `meta err <sector> <class>`, UHB b23, HUD line 6
`MS DUR nn.nS META hhhhhhhh` (**not red**; durability is shown by `DUR`), and
`META` with the sector in the panel's line 6 field whenever the panel is up for
another reason. **META does not paint the panel** (2.10), so D8 can pass.
**Clearing (A5-2):** a later successful write of X (`ctl` op 4 with 0, EVENT
`meta clear`), or **bypassed**: no write of X attempted for 60 s while every
flush in that time was DURABLE, or, for a FAT sector, a later allocating step
CONFIRMED outside it (EVENT `meta bypassed`). **Runbook:** raw image mandatory;
**the run counts**, and D8 decides as always (RUNBOOK C4, D8, E2). Detection
reads only S records, so the decoder repeats it from the files or the image.

### 4.8 Verdicts from the S records (r5; A4 F1(b), F4)

**Sector classes.** The kernel publishes the partition start and the FAT
geometry once (stats 153-159, 2.4, 2.12). An S record's `sector` is absolute
(`ms_psp.c:250`); `rel = sector − ms_part_start`, in 512-byte units, compared
with the geometry scaled by `2^(s_blocksize_bits − 9)`. A record with `flags`
b7 (block-device page cache, 2.4) is **FAT1** if `rel ∈ [fat_start, fat_start +
fat_length)`, **FATM** (a mirror) below `fat_start + fats × fat_length`,
**FSINFO** if `rel = fsinfo_sector`, **DIR** at or above `data_start` (directory
clusters are read and written through `sb_bread` buffers, `fs/fat/dir.c:87`,
`fs/fat/inode.c:571`), else **OTHER**; without b7 it is **DATA**. Linux reads
only the first FAT (`fat_ent_bread` from `fat_start`; mirrors are written by
`fat_mirror_bhs` as copies, `fs/fat/fatent.c:347-376`), so only FAT1 decides
whether a chain on the stick matches memory.

**Extent table (A4 F1(b): "map each segment's data sectors once at
creation").** After a step's FAT check passes, the worker calls
`ioctl(fd, FIBMAP, &blk)` for the first block of each cluster the step added
(≤ 3 per step, ≈ 64 per file at 32 KB clusters). FIBMAP needs root
(`CAP_SYS_RAWIO`) and calls the file's `bmap` (`fs/ioctl.c:60-76`); vfat's is
`generic_block_bmap` with `create = 0` (`fs/fat/inode.c:193-196`,
`fs/buffer.c:2564-2574`), so it allocates nothing and maps through the cluster
cache or the FAT (`fat_bmap`, `fs/fat/cache.c:295-329`); a lookup that fails
(for example a FAT read error) returns block 0, which makes the step FAILED. It runs only after the
FAT check because a lookup that reached an unwritten link would read a free or
end entry and call `fat_fs_panic` (`fs/fat/cache.c:251-258`, `:286-290`). A data
sector = `ms_part_start` + (FIBMAP result + offset in the cluster) ×
`2^(s_blocksize_bits − 9)`.

**Windows.** The worker reads the S records an operation produced with `pread`
on `/proc/psc/s` (every opened file gets `FMODE_PREAD`, `fs/open.c:684`, unless
`nonseekable_open` clears it, `:1119`, which the ring files do not use; `pread`
passes its own position to the ring's `read`, `fs/read_write.c:404-405`), which
leaves the drain position alone, so the normal drain
still copies them to the stick (2.8, K27): the flush window runs from `H_S` of
the tick's snapshot (4.3 step 1) to the head after the flush's `fsync`; a
creation step's window, or an alias `fsync`'s, from there to the head after its
own `fsync`. Writes complete inside the driver before `fsync` returns
(`ms_psp.c:228-236`), so every record of the operation is in its window; a
`pdflush` record in the same window can only add a failure, which makes a
verdict conservative. A window in which a `seq` is skipped (`slot_bad`) makes
the operation FAILED. The stick counts as **working** when the most recent
window (this tick's flush, or, when no flush ran, the last operation's)
contains at least one successful write; 4.4 steps 1 and 6 use this.

**Flush verdict.** **DURABLE** iff `write()` returned the full length and every
data sector of `[seg_end_old, seg_end_old + len)`, from the active file's extent
table, is covered by a DATA write record of the window with b1 clear;
otherwise **FAILED**. `fsync`'s return is recorded (UHB `last_errno`, b30) and
used for nothing else.

**Step verdict.** 4.4 step 4 (**r7**: including how step 0's own
directory-entry record is found in the window).

**Speed (A5-3, A5 IF4 G2).** The first two CONFIRMED 64 KB steps of the run give
the measured speed (bytes / time of `write` + `fsync`), shown on line 6 while
`MS PREP` and in EVENT `speed <KB/s>`. STICK needs ≥ 30 KB/s (8.2): the model of
15.6 is lossless under the sporadic error pattern from 28 KB/s up (at
25 KB/s 1 whole-tick run in 260 loses 15.2 s).

**Geometry self-check.** STICK also needs the first file's step-0 data sectors,
computed from FIBMAP and the geometry, to equal the DATA write records of its
window exactly. A wrong partition offset or geometry therefore fails the
self-test (an abort, no run lost) instead of misjudging the run.

**Cost.** ≈ 2 `pread`s of ≤ 40 records per tick (≈ 3 KB of `/proc` reads),
≤ 3 `ioctl`s per creation step, extent tables ≤ 128 × 12 B per open file
(≈ 6 KB in all), ≈ 120 LOC in `pscol`; no stick bytes.

---
## 5. Budget (recomputed for revision 5 with a script; rates are maxima)

17.86 polls/s (250/14), 2 commands per poll, a Nop per 1250 ticks, a 0.23 s
collector tick (4.35/s); Python with the 10.3 format strings.

### 5.1 Bytes to the stick

| Stream | Rate /s | Bytes each | B/s |
|---|---|---|---|
| P records | 35.71 | 80 | 2,857 |
| POLL records | 17.86 | 40 | 714 |
| W records | 0.2 | 288 | 58 |
| S records, flushes | ≤ 22.6 steady, ≤ 27.0 in creation ticks (fixed point below) | 40 | ≤ 904 (1,080) |
| **(r4, A4-1)** S records, creation steps | ≤ 11.5 per 8 KB step (5 + 1 + 3 data bios, directory, FSINFO, ½ FAT) during the 21 % of ticks with a step; ≤ 27 per 64 KB step | 40 | ≤ 2,000 in those ticks; **run average of all S: 34.2/s, 1,368** |
| RECS chunk header + 5 block headers | 4.35 | 60 | 261 |
| UHB chunk (**r5**: 21 words with the nonce) | 4.35 | 104 | 452 |
| STATS chunk | 0.54 | 788 | 428 |
| PROCS chunk | 0.11 | ≈ 1,156 | 126 |
| PAD chunk header | 4.35 | 20 | 87 |
| KMSG, EVENT | ≈ 0 (≈ 2 KB at boot, a few hundred bytes per event) | | ≈ 0 |
| **Payload** / padding / **records on the stick** (run average) | | | **≈ 6,351** (5,887 steady) / ≈ 1,248 / **≈ 7,598 B/s** (7,123 steady, 9,350 in creation ticks; unchanged by r5: the 4 extra UHB bytes fit in the same sectors) |

Over a 40-tick cycle (STATS every 8th, PROCS every 40th): 35 flushes of
1,227 B → 1,536 (3 sectors), 4 of 2,015 → 2,048 (4), 1 of 3,171 → 3,584 (7):
**3.2 data sectors per tick**; S ≤ data + directory entry + FSINFO = 5.2 per
tick = 22.6/s (in creation ticks 4.2 + 2 and 4 / 5 / 8 sectors per flush).
With a creation step in 21 % of ticks: **15 min: 6.8 MB; 30 min: 13.7 MB;
35 min (run plus self-test and D8): 16.0 MB**, i.e. 4, 7 and 8 files, plus two
ahead: 12, 18 and 20 MB of stick space (cap 64 MB, 4.4). **Creation** writes
each file once more: 4,096 data sectors plus directory entry and FSINFO per
8 KB step plus the FAT sector in two copies per cluster, 4,736 sector writes
(32 KB clusters), i.e. **8.8 KB/s** more physical writes on average, in
≈ 1-minute bursts every ≈ 4.6 minutes. In the H1 shape P and POLL fall (each −4 ≥ 50 ms, recon §1.5). A
catch-up flush is ≤ 40,960 bytes (**§17 R-6** 37,736 with the r5 UHB and the
re-send block headers, padded to 37,888).
**(r5)** The S-record verdicts (4.8) add no stick bytes: ≈ 3 KB of `/proc` reads
and ≤ 3 `FIBMAP` calls per creation step. Script: section 15.6.

### 5.2 Memory Stick operations (the H10 exposure)

Every `fsync` writes FSINFO (`file_fsync` calls `write_super`
unconditionally, `fs/sync.c:67-68`; `fat_write_super` → `fat_clusters_flush`
marks it dirty every time on FAT32, `fs/fat/inode.c:453-459`,
`fs/fat/misc.c:40-72`). **Records:** 3.2 data + 1 directory + 1 FSINFO =
5.2 × 4.35 = 22.6 sector writes/s (23.5 on average with creation ticks), 45
LED operations/s. **Creation:** 4,736 writes per ≈ 276 s file life, +17.2/s.
**Average 40.7 sector writes/s (20.8 KB/s), ≈ 81 LED operations/s, ≈ 3.1×
telem's** (1 data + 1 directory + 1 FSINFO per `fsync`: ≈ 13.0/s, ≈ 26
LED/s); **≈ 206 LED/s (≈ 7.9×) during the minute a file is created at 8 KB
per tick; ≈ 1,190/s (≈ 46×) during 64 KB steps** (**(r5, A5-3)** only while
the active file's room is below 81,920 bytes or the worker holds: 3-9 steps in
the first 2-50 s at 300-25 KB/s, modelled in 15.6, instead of r4's whole first
file, R8). Revision 2 did ≈ 53/s with no
bursts; 7.5 states why the increase is acceptable. Stage 3 expects
`led_calls` = 2 × the simulated sector writes, with 32 KB and 64 KB clusters.

### 5.3 Memory

**Kernel:** rings 652,288 B + stats 768 B + ≈ 1 KB = **≈ 653 KB**, 3.1 % of
telem's ≈ 20.8 MB `MemFree` (`telem/logs-from-stick/telem.log`); BSS is not in
`vmlinux.bin`; `psp_detect_mem_size` starts after `_end` (`psp.c:429`).
**Userland (§17 R-5, measured at G2 attempt 1):** two `pscol` processes, each
in **one 256 KB block** (text 51,904 + data 2,896 + bss 112,720 + stack
16,384 = 183,968 B; under `CONFIG_SONY_PSP` `binfmt_flat` puts the text in the
same allocation, `fs/binfmt_flat.c:471-472`, `:626-628`), both allocated at
boot, none later (4.2): 512 KB in all, 2.5 % of telem's ≈ 20.8 MB `MemFree`;
telem used one ≈ 540 KB block rounded to 1 MB (recon/input §6.1). The r5 figure
("≈ 100 KB each in one 128 KB block") was wrong twice: data + bss + stack alone
is 132,000 B, and the text was not counted. **Kernel stack (§17 R-3):** the
Nop path runs on the interrupted task's 8 KB kernel stack
(`include/asm-mips/thread_info.h:65-66`, `:82`; `.config:98`, `:100`) and is
≈ 280 B deeper than the baseline's (wrapper 72 B, `Syscon_cmd` frame 56 B
instead of 48, the hand-off 128 B, or `psc_sc_exit` 104 B + `psc_fill_sc`
64 B; G2 attempt 1 F5). The panel's 328 B frame runs only at T2d, never on a
watchdog tick (2.3), so it never adds to the Nop path. The worst-case depth
over an interrupted context's own stack is not measured (UNVERIFIED).
**Image (§17 R-5, measured):** `vmlinux.bin` 1,723,228 → 1,766,859 B
(**+43,631**: kernel code and data +16,384, the gzipped initramfs section
+27,247 with the 55,044-B `pscol` bFLT); `vmlinux-0.22.bin` 899,402 →
936,321 B (+36,919; +37,039 against the 2008 image the stick boots today). The
r5 component estimates (kernel text ≈ +7 KB, bFLT ≈ 24-32 KB) were low. **The
bound stands: ≤ 49,152 B (48 × 1,024) growth for each image against the
baseline rebuild**; attempt 1 leaves 5,521 B of margin for `vmlinux.bin` and
12,233 B for `vmlinux-0.22.bin`. For later revisions the one rule is that each
G2 attempt restates both growths and the change since attempt 1; growth above
49,152 B returns to G1. No tighter margin is set, because the bound is not
derived from a known pspboot limit (R20; the G2 reviewer's reading of a 4 MB
bound in the stripped loader is UNVERIFIED) and an image that does not load
fails before the run is spent (8.3: the PSC display never appears, an abort).
Whether pspboot loads the larger image is UNVERIFIED (R20).

### 5.4 Time added

Assumptions (UNVERIFIED): ≈ 1 instruction per cycle cached, Count at the core
clock (`psp.c:38`), a miss ≤ 100 cycles. **(§17 R-3)** The `Syscon_cmd` rows
below are G2 attempt 1's objdump counts of the release build
(`gates/G2-attempt1-review.md` F5; function sizes in its `System.map`:
`psc_syscon_cmd` 102, `psc_sc_exit` 583, `psc_fill_sc` 151, `psc_xfer_out` 34
instructions), replacing the r5 estimates; the run measures the costs
(`p_rec_cost_*`, `w_rec_cost_max`, `panel_cost_*`).

| Where | Added | Estimate |
|---|---|---|
| **Inside one transaction window (S5 → S20)** | **0 instructions** (2.1) | **0** |
| Thread command: before S5 / after S20 **(§17 R-3)** | ≈ 60 (the wrapper `psc_syscon_cmd` before its call) / ≈ 400-550 (the hand-off ≈ 85 in `Syscon_cmd` and `psc_xfer_out`; `psc_sc_exit` ≈ 250-300 on the P path; `psc_fill_sc` 151 with its `memset`/`memcpy`) | ≈ 0.27 / ≈ 1.8-2.5 µs cached, plus I-cache misses on ≈ 2 KB of exit code (UNVERIFIED, inside `p_rec_cost_*`) |
| G3-low gap between the 0x33 command's S20 and the 0x08 command's S13 **(§17 R-3)** | ≈ 460-610 instructions more than the baseline (the 0x33's exit, the 0x08's entry) plus the thread's stage stores between the two calls | ≈ 2.1-3 µs cached (7.3) |
| Per poll (2 commands, POLL, stages, counters) **(§17 R-3)** | ≈ 1,200-1,500 instructions (2 × 460-610, and ≈ 300 for POLL, stages and counters: `psp_joypad_thread` grew from 364 to 662) | ≈ 5.5-7 µs against ≥ 56 ms per poll (≈ 0.01 %) |
| Watchdog command (interrupts off) **(§17 R-3)** | ≈ 60 before its S5; after its S20 the hand-off ≈ 85, `psc_fill_sc` 151 and the W branch of `psc_sc_exit` with the inlined W extension: ≈ 450-800 (path not counted: UNVERIFIED) | ≈ +2-4 µs per 1250 ticks, measured as `w_rec_cost_max`; ≈ 280 B more stack (5.3) |
| Every tick / tick finding the thread running in a command | ≈ 16 / + ≈ 33 | ≈ 70 ns / + ≈ 0.15 µs |
| Wake-up of the thread; switches while it waits | ≈ 25; ≈ 15 each, ≈ 30 the last | its loop top starts ≈ 0.2 µs later |
| Any wake-up / any switch / LED operation / MS segment | 1 compare / 1 load + **(r4)** 1 compare / ≈ 25 / ≈ 56 | negligible |
| **(r4)** Switches while the thread is preempted inside a command | ≈ 15 each, ≈ 15 more at its switch-in | none on the thread while it is off the CPU |
| Stall panel | 0 while healthy; ≈ 46,000 stores + one write-back per paint | 0.2-1 ms interrupts off (UNVERIFIED), ≤ once a second, never on a watchdog tick |

A command's own duration is UNKNOWN from the source (≥ 23 uncached MMIO
accesses plus the ACK latency, recon §1.2); it is measured and the HUD shows
median and maximum, so the D10 ratio is checked on the device.

**(§17 R-3) The D10 ratio, re-derived with the measured counts.** Inside the
window the added time is 0 and the window keeps its instructions (2.1, 7.2), so
the ratio concerns only the time around it: ≈ 2.1-2.8 µs per thread command
cached (≈ 0.27 µs before S5, ≈ 1.8-2.5 µs after S20; r5 said ≈ 0.8 µs). The
command's own duration is at least its ≥ 23 uncached MMIO accesses, the
syscon's ACK latency and, for GetCtrl2, 2 SPI words out and ≥ 5 in
(`syscon.c:128-134`, `:201-217`; recon §1.2). The added time is ≤ 10 % of any
command that lasts ≥ 28 µs (UNVERIFIED: the SPI clock and the MMIO latency are
unknown). The run measures both sides of every command: the duration
`c_out − c_in` (which itself contains the ≈ 60 entry and ≈ 85 hand-off
instructions, ≈ 0.65 µs) and `p_rec_cost_last`/`max`, shown on HUD line 10 as
`CMD MED`, `MAX` and `C` (8.2) and printed by the decoder (10.7 step 6,
costs). D10's purpose, the window's own timing, does not depend on the ratio
(7.3).

---
## 6. Coverage matrix

`P08`/`P33` are P records with that `cmd`; `key = rx[3] | rx[4]<<8 |
rx[5]<<16 | rx[6]<<24` (`syscon.c:363`), the driver uses `~key`, a pressed
button is a raw 0 bit (`joypad_psp.c:490`). `branch` is recomputed (R3 if
`ret < 0`, R4 if `(~key) & 0x2000`, else R5, `joypad_psp.c:487-495`) and
checked against POLL `ri_branch`; onset is found by the decoder (10.7);
"persistent" = ≥ 90 % of post-onset records over ≥ 10 s. The **healthy
template** (per command `nwords`, `rx[1]`, **`rx[2]`**, and `ack_polls`,
`drain`, `gpio_in`, `spi_*`, jitter) and its fallback are in 10.7 step 2.
**Early death** (before `SELFTEST PASS` or C0): H1, H2, H3, H5, H9 and the H4
and H10 triggers use absolute values; H6 and H7 take each script button's raw
bit from the source bit map (`joypad_psp.c:36-58`: TRIANGLE `rx[3]` b4, RIGHT
`rx[3]` b1, LTRG `rx[4]` b1, HOLD `rx[4]` b5, VOL_UP `rx[5]` b0, stick
`rx[7]`/`rx[8]`, active-low), flagged `no C0 reference`. The result is a
triple: **trigger** (H4, WB, H10, N1, N1m, N1p, none), **state** (H1-H3, H5-H7,
H9, N2-N6, N2b, N11), **H8 flags** (H4 may trigger what another shape
sustains, 9.6); the raw stream always remains for the analyst. **(§17 R-1)**
Where a row reads `nwords`, a record flagged `nw7or8` (1.2, 10.3) is read as
the set {7, 8}; 10.7 ("`nwords` 7 or 8") shows row by row that no outcome
changes.

| ID | Identifying fields and values | Could be confused with | How the records separate them |
|---|---|---|---|
| **H0** | No rule matches. The decoder prints every P, POLL, W, S and M record from onset − 30 s to onset + 60 s around each candidate, the stats series, KMSG and PROCS | anything | The raw windows (D3) |
| **H1** | Persistent: `P33`/`P08` `ret ∈ {−4, −3}`; −4 with `ack_polls = 1,000,001`, −3 with `drain = 0xFFFF`; `nwords = 0`; `rx` all `ff`; `c_out − c_in` plus `dtick` at the full spin budget; `lc_epc` at S14 (or S8) with `lc_n` ≥ ≈ 12; POLL `ri_branch = 3`, `period` stretched; stats outcome counters −4/−3 rising. **9.5 variant:** W records keep `ret ≥ 0` and normal `ack_polls` | one −4 left by H4 at P2-P5a; H8 behind the missing ACK; N9 | Persistence. W `ret` separates pure H1 from the variant. N9 has no P records and `t_busy` stuck |
| **H2** | `P08`: `ret = 0`, `nwords ≥ 1`, received bytes `00` (`rx[0] = 0`, `rx[3..6] = 00`); POLL `ri_branch = 4`; `jp_r4` +1 per poll | the real HOLD switch; N11 | A real HOLD frame (C0, D7) clears only `rx[4]` b5, with a normal `rx[0..2]` and checksum |
| **H3** | `P08`: `ret = 0`, `nwords = 0`, `rx` all `ff`, finite `ack_polls`; POLL `ri_branch = 5`; in mouse mode `dx = +16`, `dy = +16` every poll (REL_Y −16, `joypad_psp.c:652,690`); then dedupe | one E3 from H4 at P3/P4/P5a/P5b; N2b with a short stolen reply | Persistence and `wn`; N2b has `nwords ≥ 1`, `ret > 0` |
| **H4** | A WT record (`tick ≡ 0 mod 1250`) with `t_busy` b0, linked to the in-flight P command (`W.p_head` = its `seq`; that record has `wn ≥ 1`). **Step:** if `ext_flags` b4 and not b7, W `epc` through the EPC map (10.6) gives S1..S23 and the P-point, with k (P2) and j (P6) from `r`; if b4 = 0 or b7 = 1 (with b5 = 1), `lc_epc` and `lc_r`. **P4 against P5a:** W's own `ack_polls = 0` with `drain > 0` and a reply-shaped `drain_last` = P5a; `ack_polls > 0` with `drain = 0` = P4. The Nop's own `rx`, `ret`, `nwords` show what it received. **Outcome cross-check:** the thread's result must be allowed for that P-point (10.7 step 5), else `inconsistent`. Benign interleaves are counted from every W record (per-step harm rate; 7.3) | H10; N8 (`pdflush` at the same 5 s boundary); coincidence | W present with EPC in the window, against an S record overlapping the command (H10); `kupd_last_tick` series (N8); the benign rate from all W records |
| **H5** | Persistent `ret ∈ {−2, −5}`. −5: `retries = 16`, `rx[2] ∈ {0x80, 0x81}`. −2: `rx[1] < 3`, a mismatch the decoder recomputes from `rx`, or `rx[1] ≥ 16` (out-of-bounds checksum, dossier 9.1). W records show whether BUSY also hits command 0x00 (not permanent for 0x00 on the 2008 image, recon/image2008.md §7) | H4 at P2 or P6 (a single −2) | Persistence; the `rx` pattern |
| **H6** | `P08`: `ret > 0`, valid checksum, **`rx[2]` equal to the template's value for 0x08** (**r3, N-4**: the literal 0x08 of `include/asm-mips/ipl_sdk/syscon.h:55-58`, an author comment, only without a template, flagged `rx2 literal`), and `rx[3..8]` byte-identical through D1-D7 while no P33, W or M record carries a GetCtrl2-shaped frame (template `rx[2]` of 0x08) whose button bytes follow the presses (that is N2b), while C0 showed the same presses change `rx[3]` (b4, b1), `rx[4]` (b1, b5), `rx[5]` (b0), `rx[7]`/`rx[8]`; POLL dedupe every poll | H7; N2b; operator not pressing | H7: the raw bytes follow the presses. N2b: replies lag one command. "Not pressing" is excluded only by the notes and photograph P6 |
| **H7** | Raw `rx` follows the script after onset, but delivery stops at a stage: (a) `ri_branch 5`, `jp_changed` rises, but `push_fail`/`jp_listsem_fail` rise or `nqueues = 0`; (b) pushes OK and `jp_wake` rising, `fop_read_ret` flat (`psposk2` not consuming; PROCS state); (c) `mouse_reports`, `md_event_syn`, `md_notify_calls` rising, `md_read_ret` minus the collector's own reads flat (`pspmd` not reading) while the collector's client still gets packets; (d) `vcs_putchar` flat while `psposk2` reads, or `console_sem` count ≤ 0 for seconds (recon/input B6); (e) POLL `sig` b0 | H9; H6 | P and POLL keep coming (not H9); raw data changing (not H6); the stage letter localises it |
| **H8** | After onset, captured values leave the template: `gpio_in`, `spi_st9`, `spi_sttx`, drain rate and `drain_last`, `ack_polls` (always 0: latch stuck), the LED read-back ORs (S, stats 102-103). Without a template: `unassessable`, raw values against code expectations and the WB/M/WT baseline. **Declared blind spot:** registers the code never reads (SPI `+0x00, +0x04, +0x14, +0x18, +0x20, +0x24`; GPIO `+0x00, +0x10, +0x14, +0x18, +0x24`, recon §4.3) are not observed (dossier 9.1); a change there shows only as behaviour, "H8 unresolved" | H1, H3, H5 (behaviour); H4, H10 (cause) | Flags beside the state, never alone |
| **H9** | P and POLL stop; W continues with `jp_loop` constant and `jp_stage` 11 (`jp_stage_arg = Q`) or 9; stats `jp_state` = 1, `qfree_stage = 2` with `qfree_queue = Q`, `qfree_pid` the closer, `fop_release` just incremented; PROCS: `psposk2` exiting or gone | N4, N5 (thread stopped elsewhere) | `jp_stage` and `qfree_stage` naming the same `Q` |
| **H10** | Before onset: a P command with `ms_delta > 0` and `preempt_delta > 0`, whose suspension step (`lc_epc`, never nested) is in **S5..S20**, reported with its window (**S13..S20**, G3 high, or **S5..S12**), an overlapping S record (`[tick_on, c_on]..c_off`, `flags` b4/b5), and a read-back that wrote back **any bit other than the LED bits 0x40/0x80** (`led_or & ~0xC0 ≠ 0`, or `rd_*_or & ~0xC0 ≠ 0`). `led_pid` names the task; **(r4)** `pre_cls`, `pre_wrk/pre_tot` name who held the CPU and the collector's share. Onset need not be at a 1250 boundary. **Refutation (r3, narrowed, A3 UL5):** see 10.7 step 5 | H4; N1m | The interrupter (S record, not W) and the tick phase; if both occur both are reported |

### 6.1 Failure shapes not in the dossier, covered by the same fields

| ID | Shape | Signature |
|---|---|---|
| N1 | Thread preempted mid-transaction (G3 high, M = 6) for a long time, no Nop, no LED activity | `preempt_delta > 0`, `lc_epc` in S5..S20, `wn = 0`, `ms_delta = 0`, suspension ≤ `dtick − lc_dtick` ticks, then onset; **(r4, A4 F5) holder**: `pre_cls` (preemptor, last holder), `pre_tot`, collector part `pre_wrk` (2.11) |
| **N1m** | **(r3, A3 UL5)** Suspended in S5..S20 while LED read-modify-writes ran with a **clean** read-back: N1, or an LED effect not visible in the read-back (a read side effect; recon §4.2 proves no GPIO read free of them). **These cannot be separated in one run** | as N1 but `ms_delta > 0` and `led_or & ~0xC0 = 0`; reported with the step, the suspension bound (`dtick − lc_dtick` ticks, from `lc_tick` to exit), `ms_delta`, `led_pid` and **(r4)** the holder (`pre_*`); the whole-run comparison of 10.7 step 7 is printed beside it |
| **N1p** | **(r3, A3 OE6)** A kernel panel paint (0.2-1 ms, interrupts off) landed while the onset command was in flight | SC `lc_flags` b5; the paint tick is in `panel_last_tick` and ≡ 125 (mod 250); `panel_cost_last`; step from `lc_epc` when the thread was running at that tick. Replaces revision 2's "onset within 1 s after a paint" flag |
| N2 | FIFO carry-over: a permanent one-frame shift with residue in the RX FIFO | `drain > 0` on every command after onset, `drain_last`/`rx` showing the shift; without a template compared with `drain = 0`, flagged `unassessable` |
| N2b | Reply lag: each request receives the previous request's reply, nothing left in the FIFO (A2 UL3) | Across the merged P + W + M timeline, command n's `rx[2]` equals the template's `rx[2]` **for command n−1's `cmd`** (**r3, N-4**; the literal `cmd` only without a template), persistently, with `drain = 0`; `P33`/W records carry GetCtrl2-shaped frames whose buttons follow the script one poll late. Tested before H6 |
| N3 | The syscon answers 0x83 or 0x86, accepted as success | `rx[2] ∈ {0x83, 0x86}` with `ret > 0` |
| N4 | The thread wedges in `psp_lcd_on` → `do_unblank_screen` after the console blanks (≈ 600 s, `drivers/char/vt.c:174`) | `jp_stage` 7 or 8 fixed, `console_blanked`, POLL `pi_flags` b2 just before |
| N5 | The thread loops in the input core on a freed mousedev client (recon/input §3.2 I9) | `jp_stage` 15/16 fixed, `jp_loop` fixed, `jp_state` 0, W `epc` in `mousedev_*` |
| N6 | Userland consumers die while kernel delivery works | `jp_push_ok`, `md_*` rise; `fop_read_ret`/`md_read_ret` flat; PROCS shows the daemon missing or stuck |
| N7 | The 2008 image and this tree differ (dossier 9.5; recon/image2008.md V6, V9) | Not observable on the device; "no failure in 30 minutes" is reported as a result with section 7 |
| N8 | `pdflush` 5 s writeback coincides with onset | `kupd_last_tick` within ± 2 ticks of onset; S records with the `pdflush` pid in the command's window |
| N9 | A thread command never returns (impossible by code, `syscon.c:110-113,151-154,253`; possible if an MMIO access stalls) | `t_busy` set, `t_entry_tick` fixed; every W record has b5 with a fixed `lc_epc` and `lc_n` rising |
| N10 | One foreign frame toggles mouse mode off (A1 UL2) | POLL `pi_flags` b3 and b4 = 0 on a poll whose `P08` is foreign (`wn ≥ 1`, `rx` not a GetCtrl2 reply, or `ret = 0` with `nwords ≥ 1`), then `mouse_flags` b0 = 0 while `rx` follows presses; HUD `MOUSE OFF`; D7a restores it |
| N11 | HOLD stuck with valid frames (A2 UL4) | persistent `ri_branch = 4`, well-formed non-zero `P08` frames following D3, D4, D6, raw `rx[4]` b5 = 0 through D7 although C0's D7 changed it (answers dossier Q3) |
| H10b | An LED **set** read-modify-write that reads back bit 3 with **no** command in flight raises G3 outside a transaction (A1 F10) | within ± 2 s of onset, an S record with `flags` b2 or `rd_set_or & 0x08` and b4 = b5 = b6 = 0 |
| **WB** | **(r4, A4 UL6)** The Nop breaks the link with no thread command in flight (9.6) | the first failed thread command is the first after a WT record with `t_busy` b0 = 0; that Nop's own `ret`, `nwords`, `rx`, `ack_polls`, `drain` against the template; every WT record within ± 2 cycles of onset whose own reply is not a valid Nop reply is listed. A straddle counts as benign only if the thread's and the Nop's results were both valid |
| LEDSPLIT | **(r3, A3 TE5)** The Nop landed between the load and the store of an LED read-modify-write | W `epc` labelled `LEDRMW` in the EPC map (10.6); the loaded value from `r` per `regmap.txt`; reported with the G3 (bit 3) transition the store then caused |

### 6.2 Onset timing (S3)

Death at 17 s, 250 s or 29 minutes falls in streamed data. A death before the
collector starts (9.6: before 36 s) is still in the rings (≥ 114 s of P and
POLL, all W, S, M) if the first drain comes within 114.7 s of the thread's
start: the collector starts at ≈ 20-40 s of uptime (UNVERIFIED; the first
UHB's `uptime_cs` records it) and **(r4, A4 TE6)** flushes into its first file
one 64 KB step after the FILEHDR, ≈ 1-4 s later at 300-25 KB/s (4.4). **(r5,
A5-3, corrected)** The first flush is not the first *complete* drain: the boot
backlog (≈ 600-1,300 P records) drains at ≤ 192 P records per tick while
production continues, and r4's 64 KB steps for the whole first file stretched
every tick. With r5's step rule (64 KB only while the room is below 81,920
bytes) the model of 15.6 gives the first complete drain 3-6 s after worker
start at 300 KB/s, 9-17 s at 52 KB/s, 18-35 s at 30 KB/s and 26-48 s at
25 KB/s (worker start at 20-40 s of uptime); the boot records are never
overwritten (the backlog shrinks every tick). An early death fails the POLL or
BTN self-test and the runbook runs the post-death script instead of aborting
(8.3).

### 6.3 Phase of a death in the 1250-tick watchdog cycle (r3, brief item (e))

The records resolve it exactly. Each P record has `(tick_in, c_in)` and
`(tick_in + dtick, c_out)` from `ts_read()`; each Nop is a WT record at
`(1250k, c_in..c_out)`; Count is reset at the entry of every tick handler,
before `localTick++` and the Nop (1.1). So for the last thread command that
succeeded, the first that failed and the nearest Nop, the analyst reads off
whether each lies **before** tick 1250k (`tick_out < 1250k`), **across** its
boundary (`tick_in < 1250k ≤ tick_out`: then `wn ≥ 1`, `W.p_head` names the
command and W `epc` or `lc_epc` the step the Nop hit), or **after** it
(`tick_in ≥ 1250k`, and within tick 1250k only with `c_in` after the Nop's
`c_out`, since the thread cannot run during the handler). Order is by Count
(≈ 4.5 ns) within a tick and by tick across ticks; dossier 9.6's ±0.2 s
uptime offset does not arise because the records use the watchdog counter
itself. The decoder prints the three placements per onset candidate (10.7).

---
## 7. Perturbation statement

### 7.1 What changes

| Aspect | Change | Effect on the syscon transaction |
|---|---|---|
| Locks | **None added**: no spinlock, semaphore, `preempt_disable` or atomic on any new path | None |
| Interrupt state | **None changed**: no `local_irq_*`; watchdog-side work, the tick hook and the panel run in the existing interrupts-off region of the timer handler; the scheduler hooks run where the scheduler already has interrupts off | None |
| Delay inside S5..S20 | **None** (2.1, G2-checked) | None |
| Delay around the transaction | **(§17 R-3)** ≈ 60 instructions before S5, ≈ 400-550 after S20 (objdump, 5.4) | Each command's S5 comes ≈ 0.3 µs later; the next command ≈ 2.1-3 µs later (cached) |
| MMIO accesses | **None added, none removed**, same order (2.1, 2.4); the panel writes framebuffer RAM only | None |
| New syscon commands | None | None |
| Timer interrupt | ≈ 16 instructions per tick; ≈ 33 more when the thread is running in a command; **(§17 R-3)** ≈ 2-4 µs extra on watchdog ticks (path count UNVERIFIED; `w_rec_cost_max`) | The thread resumes ≈ 0.15 µs (normal tick) or ≈ 2-4 µs (watchdog tick) later |
| Stall panel | Nothing while healthy; a paint is 0.2-1 ms interrupts off (UNVERIFIED, measured per paint), ≤ once a second, never on a watchdog tick, only in the occasions of 2.10 | A command straddling a painting tick is stretched by the paint time; flagged per command (`lc_flags` b5) and named by row N1p |
| Scheduler hooks (2.11) | One compare per wake-up, one load and **(r4)** one compare per switch; ≈ 25 per thread wake-up, ≈ 15 per switch while it waits or is preempted | Outside `Syscon_cmd`; the thread's 0x33 command starts ≈ 0.2 µs later after a wake-up; a preempted command resumes ≈ 0.1 µs later |
| Out-of-bounds checksum (A2 note) | The thread's and `Syscon_cmd`'s frames change, so the bytes the baseline checksum reads above `rx_buf` when `rx[1] ≥ 16` differ from the baseline's | Which corrupt long frame passes by chance (≈ 1/256) changes; the rate does not, and every acceptance is visible as `ret > 0` with `rx[1] ≥ 16` |
| Userland privilege (A2 OE4) | User processes keep kernel privilege (`arch/mips/kernel/process.c:81-83`; `USER_DS` = `KERNEL_DS`, `include/asm-mips/uaccess.h:58`, `:107-113`), so a `pscol` bug could store into kernel memory or MMIO | Mitigated (4.2 guards, 3.1 kernel guards, G2 review of `pscol` with C3/C4 rigour, Stage 3 ASan/UBSan fuzzing, decoder `instrumentation-suspect`); a stray store that hits no guard is not detectable (R16) |
| `printk` | One line at init. **(r5, A5 OE8)** The Memory Stick driver's `DBG` messages are compiled in (`ms_psp.c:17-24`; the attempt-4 statement that they were compiled out was wrong): two unthrottled lines per failed transfer (`:272-274`, `:370-371`), which `printk` draws through fbcon with interrupts off (`kernel/printk.c:819-828`). The worker sets the console log level to 4 at its start (**r7, A6-2:** `syscall(__NR_syslog, 8, 0, 4)`, the kernel call, not libc `syslog()`; return in EVENT `conlevel`, 4.2; `kernel/printk.c:292-300`): those lines carry the default level 4 (`:40`) and stay in the log and the KMSG chunks but are no longer drawn; `KERN_ERR` lines (FAT panic, `fs/fat/misc.c:22-32`; "Buffer I/O error", `fs/buffer.c:107`) still are | None on the syscon path. A healthy run is expected to print nothing after boot (any message is in KMSG, so a suppressed one is visible to the analyst); in error runs it removes interrupts-off drawing the instrumentation's own I/O would cause. What remains (the driver's 10 tries with `mdelay(1)` per failing sector, preemption off) is recorded as long S records and `wk_*`/`pre_*` holders |
| Code layout | `Syscon_cmd`'s frame grows (48 → 56 B); **(§17 R-5)** kernel code and data +16,384 B in `vmlinux.bin` (measured, 5.3); **(§17 R-2)** the window sits 0xc4 bytes later and five callee-saved registers are renamed | The drain and ACK loops' cache alignment may change the wall-clock length of the spin budget; `ack_polls` with duration measures it. The renaming itself changes no timing (7.2) |
| Memory | ≈ 653 KB less RAM for userland (3.1 % of `MemFree`); the collector's two processes use less than telem's one (**§17 R-5**: two 256 KB blocks against telem's 1 MB) | None |
| Userland load, Memory Stick activity | 7.4, 7.5 | 7.4, 7.5 |

### 7.2 The "zero instructions in the window" claim, and how G2 verifies it

From the S5 load (`syscon.c:102`, [OBJ] `+0xdc`) to the S20 store (`:222`,
`+0x2ac`) every baseline `dmy = REG32(x)` is `lw`, `andi 0xffff`, `sh 0(sp)`
and both spin counters are `lw/addiu/sw/lw` on `4(sp)`; another `vu16`/`vu32`
slot gives the same instructions at another offset, assignments and −3/−4
branch shapes unchanged. Criteria and fallback order: 2.1. A reviewer checks
it from two objdump listings.

**(§17 R-2) The acceptance test is the four criteria of 2.1**, applied to every
path from the S5 load to the S20 store, the −3 and −4 exits included: (1) the
same number of instructions, loop bodies of the same length and the same branch
structure; (2) the same MMIO loads and stores in the same order and form
(width, base value, offset); (3) no call; (4) no global load and no base-address
reload. Within them exactly three differences from the baseline are allowed:
**stack-slot offsets**; **a consistent renaming of registers that keeps every
value** (a register that holds an address or a constant in the baseline is
replaced throughout the window by one that holds the same value, set before S5
and not written in the window); and **the delay slot of an exit branch** that
runs after the exit decision and after the path's last MMIO access. The first
paragraph of this section ("another slot gives the same instructions at another
offset") and the summary described the compiler output expected, not the test;
read literally, as "identical apart from stack offsets", they excluded a
renaming that the criteria allow. The G2-attempt-1 build
(renaming s3→s7, s4→s3, s5→s4, s6→s5, s7→s6; the first −3 exit's delay slot
`lw s8,40(sp)` → `nop`; 105 = 105 instructions; `impl/syscon-window-diff.txt`,
re-derived independently in `gates/G2-attempt1-review.md` 4.1 and
`gates/G2-attempt1-verify.md` 5) passes it.

**Why these differences cannot change the timing of the on-path instructions.**
(a) **Renaming.** The renamed window has the same opcodes, immediates and memory
operands and the same dependency graph: every instruction reads the value made
by the same earlier instruction at the same distance. The renamed registers hold
the same constants, set in the prologue (baseline `s4` = new `s3` =
0xbe240004, `s7`/`s6` = 0xbe240008, `s3`/`s7` = 0xbe240000, `s5`/`s4` and
`s6`/`s5` = 8; impl/syscon-window-diff.txt, both listings), and the window only
reads them. On an in-order MIPS32 pipeline the cycles a sequence takes depend on
its opcodes, its producer-to-consumer distances (load-use and multiply
interlocks), the latency of each memory access (set by its address) and the
branch outcomes (set by the values); none of these depends on which general
register number carries a value, and only general registers are renamed (no
HI/LO or CP0 register). **UNVERIFIED:** that Allegrex has no timing that
depends on register numbers. The tree holds no description of its pipeline; the
claim rests on the standard in-order MIPS32 model. (b) **The delay slot.** It
belongs to the `j` taken when the drain loop's bound has run out
(`syscon.c:110-113`): the `bne` has fallen through, `li t3,-3` in its own delay
slot is unchanged, the −3 decision is made, and the path's last MMIO access (the
status read of `0xbe58000c`) is behind it; the original code touches no MMIO
register between that read and `return -3`. Baseline `lw s8,40(sp)` (the
epilogue's restore, scheduled early) against `nop` changes only the time from
the −3 decision to the record, by one cycle or one D-cache miss. That is time
after the transaction in the sense of 5.4, and it occurs only on a −3 exit,
after 1,000,001 drain iterations. (c) **What does move.** The window's
instructions sit 0xc4 bytes later and its stack slots at other offsets of a
deeper frame, so I-cache and D-cache line placement differ. That is 7.1's "Code
layout" row, true of any rebuild and not caused by the renaming; it can change
the wall-clock length of a spin loop, which `ack_polls` with the duration
measures. In the baseline too the slots' addresses vary with the caller (the
thread's stack, or the interrupted task's stack for the Nop).

### 7.3 Why this neither hides nor causes H4

- An interleave needs a Nop tick (the start of a handler, `psp.c:350-359`) to
  land while a thread command is in S5..S20. The thread wakes on a tick
  (`msleep` counts jiffies, recon/input §4), so its command's start phase and
  length decide. We add nothing to the length inside the window (7.2).
  **(§17 R-3, measured counts)** We shift starts: the 0x33 command's window by
  ≈ 0.3-0.6 µs (its ≈ 60 entry instructions and the POLL loop-top code), the
  0x08 command's by ≈ 2.4-3.4 µs (also the 0x33's ≈ 400-550 instructions after
  its S20), and a thread command resumed after a Nop by ≈ 2-4 µs. Against a
  4,000 µs tick, a shift δ changes the chance that a given Nop lands in a given
  window by at most δ / T when the window's phase is spread: ≤ ≈ 0.09 %
  absolute (r5 said 0.025 % from its estimates). Cache misses can make δ
  larger (UNVERIFIED; one 100-cycle miss is ≈ 0.45 µs). The phase is not
  assumed: every command's `(tick_in, c_in)` and `c_out` are recorded, so the
  windows' actual phases, the gap from the 0x33's `c_out` to the 0x08's `c_in`,
  and any window sitting within δ of a tick edge are in the data.
- **The larger lever is load (A1/A2 OE3).** The Nop of tick k runs before that
  tick's wake-ups (`psp.c:359` before `:367`), so it hits only a command that
  started before tick k. What pushes a command towards the next edge is
  whatever holds the CPU when the thread becomes runnable: a task inside
  Memory Stick I/O, or an equal-priority task the O(1) scheduler does not
  preempt (`kernel/sched.c:171-172`), such as the collector. So the run
  **measures** the exposure and its cause: per poll `c_start`, `period`,
  `preempt_delta`, the wake-up delay and the collector's exact share (`wk_*`);
  per Nop, whether a thread command was in flight, its step and the outcome
  (every W record); S records for the non-preemptible part.
- **Pre-registered inference if no death occurs (S5)**, fixed now (10.7 step
  8): per P-point, n benign Nop hits give a 95 % upper bound 1 − 0.05^(1/n) on
  the per-hit harm probability; "H4 at P4/P5a is not sufficient on this kernel
  at p ≥ 0.1" only if n(P4) + n(P5a) ≥ 30, else "inconclusive" with the
  exposure and the collector's share of late starts.
- **G3-low gap** (0x33's S20 to 0x08's S13) grows by ≈ 2.1-3 µs (**§17 R-3**;
  r5 said ≈ 0.75 µs); the original code comments out a 5 µs wait after GPIO3
  falls (`syscon.c:95-97`, `:142-144`), a hint of a syscon minimum, so a longer
  gap could make a "gap too short" failure rarer. The added time is now about
  half of that commented-out wait, so this is the one direction in which the
  instrumentation could hide a failure; it is recorded per poll (the 0x33's
  `c_out` to the 0x08's `c_in`, all of the added gap but the ≈ 85 hand-off
  instructions) and reported (R6). **Resumption after a Nop** is ≈ 2-4 µs later
  (**§17 R-3**): harmless if G4L is latched, as the code treats it
  (`syscon.c:159`); a pulse under ≈ 2-4 µs could be missed if it is
  level-sensitive (R6).
- **(§17 R-3) The conclusion holds with the measured counts.** H4 acts inside
  the window, which keeps its instructions and MMIO order (7.2); outside it the
  added time is ≈ 0.1 % of a tick, small against the variation of the
  thread's start that load already causes and the run records (`wk_delay`,
  `pre_tot`, 2.11), and measured per command. It neither creates an
  interleave (nothing is added where a Nop can land) nor removes one beyond
  the ≤ ≈ 0.09 % phase shift above and the G3-low gap effect just stated.

### 7.4 Userland load

The 9.6 deaths happened under telem (≈ 0.23 s tick, 272-row blit,
`telem.c:299-306`, 16 KB `syslog` read, `/proc` reads, a mousedev client, one
`write` + `fsync` per tick, ≈ 4 input events/s in mouse mode). `pscol` keeps
that work, order and cadence. Differences: `/proc/psc` reads and a `ctl` write;
no tty reads; 1.5-4 KB per `fsync` instead of ≈ 40 B; an extra 8 KB `write` +
`fsync` per tick for ≈ 1 minute every ≈ 4.6 minutes, at start **(r5)** 3-9
steps of 64 KB, then 8 KB until two files are ahead; **(r5)** two `pread`s of
`/proc/psc/s` per tick and ≤ 3 `FIBMAP` calls per creation step (4.8); the
console log level 4 (7.1); **(r4, A4-2) no
`drop_caches`**: the read-back's page is dropped by `syscall(4254, fd, 0,
SEG − 4096, 0, 4096, 0, 4)` = `sys_fadvise64_64` (`scall32-o32.S:599`, seven
argument slots), which invalidates one page of one file without `inode_lock`
(`mm/fadvise.c:98-108`). uClibc's `posix_fadvise` exists (`fcntl.h:184`,
`libc.a(posix_fadvise.os)`) but loads its arguments in the 5-slot layout,
which this entry misreads; `syscall()` (`libc.a(syscall.os)`) passes seven
slots unchanged (section 14). A supervisor waking every 2 s; a cache-resident
1.9 KB blit source (accepted, 11.3). Wake-up delays and holders are recorded
per poll, so the difference is measured; the start-up I/O, absent in the
early 9.6 sessions, is recorded and onsets during it are flagged.

### 7.5 How our own Memory Stick writes interact with H10 (required statement)

- **Every sector attempt performs an LED read-modify-write** on
  `0xbe240008`/`0xbe24000c` (`psp.c:401,406`; `ms_psp.c:290-292,312-314`), the
  H10 mechanism. **We do ≈ 3.1× telem's (≈ 81/s against ≈ 26/s), ≈ 7.9×
  during the minute a file is created and ≈ 46× during 64 KB steps (5.2).**
  Preallocation doubles the sector writes: that is its price for closing IF5.
- **Direction.** If H10 is real this raises its rate and death comes sooner;
  it does not mask it, and a death it causes is recorded exactly (S records,
  `lc_epc`, `ms_delta`, `led_or`, `led_pid`, creation EVENTs; onsets during a
  creation flagged). Non-preemptible writes (`ms_psp.c:254-268`) can also
  delay the thread's start, which `wk_*`, `period` and S times measure (7.3).
- **Zero bit-3 counts do not refute H10**: G3 is high only between S13 and S20
  (`syscon.c:140,222`). The refutation (10.7 step 5) needs a demonstrated
  overlap, is worded narrowly, and is never printed for a run whose onset
  command had one (A3 UL5). **Decorrelation:** the collector's ≈ 0.23 s
  period sweeps all watchdog phases; the 5 s confounder is `pdflush` (N8); the
  decoder tests alignment to Nop ticks, `wb_kupdate` ticks and S records
  separately.
- **Our own stick I/O can hang the machine (A1 OE1):** `ms_wait_ready` spins
  with no bound (`memstk.c:59-65`) and `ms_wait_ced` loops while the
  controller times out (`:174-181`), both non-preemptible. It is recorded (the
  marker and panel show the running task, its EPC in the driver, `preempt_count
  > 0`, the transfer, the frozen thread loop) and told apart from the
  investigated failure (telem kept running after the 9.6 deaths). The waits
  stay unbounded: a bound would change the H10 actor's code and timing on
  every sector and add an untested error path, and the author's recorded hang
  (`memstk.c:167-169`) is in the compiled-out `ms_wait_unk1` (J9, R12).
  Preallocation doubles this exposure too.

### 7.6 Kernel identity

This tree with the timeout patch unchanged (`syscon.c:12-13,110-113,151-154,
253-254`; G2 C2 against `work/syscon-timeout.applied.patch`). The 9.6 deaths
were on the unbounded 2008 image [BIN] V6-V7; here recon §5.4's endless spin
is one −4, so permanence needs carried-over state; observation 6 shows this
kernel fails too. No death in 30 minutes is a reported result (R1).

### 7.7 Floating point (D18)

`pscol` is integer-only (no `printf` family, no `strtod`/`atof`, table CRC-32
on `unsigned int`). Check, after `telem/cbuild.sh:9`: `objdump -d pscol.gdb |
grep -c '[$]f[0-9]'` and `grep -cE
'lwc1|swc1|ldc1|sdc1|mtc1|mfc1|cfc1|ctc1|cvt\.'` print 0; `nm pscol.gdb | grep
-Ei 'printf|strtod|atof|__.*sf|__.*df'` is empty; `flthdr` shows a valid bFLT
header and stack 16384.

---
## 8. Self-test

### 8.1 Kernel, in the first seconds of boot

The one `printk` (2.8) on the framebuffer console (`console=tty`, dossier 9.7)
proves the instrumented kernel runs and the boot Nop was recorded; a missed
photograph does not matter (the line is in the first KMSG chunk).

### 8.2 HUD (r3: closes N-1, N-2, N-3, N-5)

Ten lines at scale 2 (12-pixel advance, `telem.c:183`), 16-pixel pitch, rows
8-167, x from 8. **Every line ≤ 35 characters**, so nothing reaches x = 428,
where telem's heartbeat block starts (x 428-467, y 8-37, `telem.c:373`); the
border runs round rows 0-175; rows 176-271 are never written (2.10). Exact
strings (`n` digit, `h` hex digit, `[a|b]` alternatives), quoted by RUNBOOK:

| Line | Content | Max chars |
|---|---|---|
| 1 | `PSC T<rrr><nnn> SELFTEST` until all checks pass, then `PSC T<rrr><nnn> SELFTEST PASS`; `DEAD?` replaces `SELFTEST PASS` while 8.4 holds; `PSC NO KRN` if `/proc/psc` is missing (`---` for `nnn` before the first file) | 26 |
| 2 | `KRN WDOG STICK REC`, each word green when passed, red otherwise | 18 |
| 3 | `PANEL SUP POLL BTN`, likewise; a red POLL names its condition: `POLL:RATE`, `POLL:RET` or `POLL:NW0` | 23 |
| 4 | `RAW hhhhhhhh Xhh Yhh` + ` TRI` while `rx[3]` b4 is 0 in the latest `P08` (TRIANGLE held) | 24 |
| 5 | `MOUSE [ON|OFF] IN nnnnn DELIV nn.nS` | 31 |
| 6 | `MS DUR nn.nS TMAX n.nS ERR nnn` (`ERR` = FAILED verdicts, 4.8); `CATCHUP` replaces `TMAX n.nS` while catching up; **(r5)** `META hhhhhhhh` replaces `TMAX n.nS ERR nnn` while a META sector is set (4.7, **not red**); `MS READ-ONLY ERR nnn`, `MS WAIT SPARE` in those states; `MS PREP nnnS nnnKB/S` (seconds since worker start and the measured speed, **not red**, A4-4, A5-3) until STICK passes; at 3:00 if STICK has not passed, `MS NO STICK`, `MS SLOW nnnKB/S` (below 30 KB/s) or `MS DIR FULL` (names budget < 400); red after a FAILED flush or step in the last 10 s, and always in the `READ-ONLY`, `WAIT SPARE`, `NO STICK`, `SLOW` and `DIR FULL` states | 30 |
| 7 | `SEG nnn USED n.nM RDY n` (complete files ahead) + ` MAKING nn%` while a file is created, ` WAIT` after an abandon | 34 |
| 8 | `REC LOST nnnn BAD nnnn STUCK nnn`, red on any increase after the first complete drain | 32 |
| 9 | `UP nnnnnS WD nnnn/1250 SUP [OK|DEAD|RUN]` | 32 |
| 10 | `CMD MED nnnnUS MAX nnnnnUS C n.nUS` (median and maximum thread command duration, record cost) | 34 |

**`IN`** (N-3) = UHB `mouse_press_total`, the press edges in the PS/2 packets
the collector reads from its own `/dev/input/mice` client (`(p[0] & 7) &&
!(prev & 7)`, `telem.c:270`); the mouse path runs only in mouse mode
(`joypad_psp.c:464`), so **`IN` rises only in mouse mode**, one per L or R
click. **`DELIV`** (N-3) = `(now_tick − tick_start) / 250` of the latest POLL
with `push_ok > 0` or `mouse_flags` b3, capped at 99.9 s. `MOUSE ON/OFF` =
`jp_keys & 0x00800000` (`joypad_psp.c:58`).

| Check | Passes when | Proves |
|---|---|---|
| KRN | `/proc/psc/stats` opens with magic `PSST`, version 5, size 768, and **(§17 R-4)** stats word 2 equals the CRC-32 (zlib, initial value 0) of `/proc/version` as the worker reads it once at its start (1.7); a mismatch keeps KRN red | the stats block belongs to the running kernel, whose banner the FILEHDR records (10.2). Collector and kernel are one image (`pscol` is in its initramfs, 4.2), so the collector carries no build-time value |
| WDOG | W `seq` 0 has origin WB; ≥ 1 WT record with `tick % 1250 == 0`, consecutive WT ticks differ by 1250; WT records have `ctx` b2 (IE) = 0, **b3 (`in_interrupt()`) = 0**, `ext_flags` b0 = 1; P records have origin P with `ctx` b4 = 1, b2 = 1 (CTX merged here) | watchdog recording, cycle alignment, both contexts told apart without `in_interrupt()` |
| STICK | `/proc/mounts` shows `/ms0` vfat; **(r5)** the first flush into the first file's confirmed prefix is DURABLE by its S records, with the geometry self-check (4.8); `durable_tick` advanced (the first complete drain); the measured speed ≥ 30 KB/s; the names budget ≥ 400 (4.4 step 6) | data reaches the stick, the worker reads the stick's own answers correctly, the stick is fast enough for the lossless range of 15.6, and the kernel knows how far |
| REC | `LOST 0 BAD 0 STUCK 0` for 3 s after the first complete drain; `nwords ≤ 8`; `nwords = 0` ⇒ `rx` all `ff`; `ret > 0` ⇒ `rx[0] == ret` | records are consistent |
| PANEL | after the first complete drain the worker requests a 5 s test (`ctl` op 3); within 6 s `panel_test_done` has risen by ≥ 3 | the kernel paints from the timer interrupt. **It does not prove the band is visible** (N-5): the read-back that r2 used went through the cached `screen_base` (`pspfb.c:24,396`; `fb_sys_fops.c:41-45`) and proved only that the routine ran, so it is cut. Visibility is proved by the operator seeing `PSC TEST`, an abort item (8.3) |
| SUP | `getppid()` is not 1 | a worker death or stall can be recovered without an allocation (4.2) |
| POLL | over ≥ 5 s ending now, from two stats reads: P head ≥ 20 records/s and POLL ≥ 10/s (else `POLL:RATE`); healthy is 14.7-17.86 polls/s, a thread whose commands time out ≤ 6.4/s (each −4 ≥ 50 ms, recon §1.5); latest `P08` `ret ≥ 0` (else `POLL:RET`) and `nwords ≥ 1` (else `POLL:NW0`) | thread recording is live |
| BTN | a `P08` record shows `rx[3]` b4 clear, then set again after release | a physical press appears in the recorded raw data |

**(r4, A4-5)** When KRN, WDOG, STICK, REC, PANEL and SUP are first all green, a
second 5 s test is requested, independent of BTN; RUNBOOK B4 tells the
operator to watch the band at that moment, before holding TRIANGLE. Checks keep running after
PASS; UHB b1-b8 carry them (the SELFTEST chunk is cut).

### 8.3 Abort rule (G3 item R5); decision at **3:00** on the stopwatch

**(r5, A5-3, corrected)** r4's "STICK passes ≈ 1-3 s after the worker starts"
confused the first flush with the first complete drain, which STICK, REC and
PANEL all wait for. With the r5 step rule and the 30 KB/s gate, the model of
15.6 puts the first complete drain ≤ 35 s after the worker starts (at 30 KB/s
and a 40 s worker start; 3-17 s at 52-300 KB/s), so REC (3 s) and PANEL (≤ 6 s)
are green by ≈ 85 s of uptime, plus the unknown pspboot load time before
uptime 0 (UNVERIFIED, ≈ 10 s assumed): ≥ 80 s of margin before 3:00 for B4 and
B5. A stick below 30 KB/s shows `MS SLOW` and is an abort, not a run; a
slow first complete drain for any other reason leaves STICK red at 3:00, also
an abort. 3:00 is kept.

- **Abort** (not the run; power off, photograph, report, leave the stick as it
  is, return `PSCLOG`) if at 3:00 `SELFTEST PASS` is not on line 1 and the
  exception does not apply; or at 3:00 `MS NO STICK`, `MS SLOW`, `MS DIR FULL`
  or `PSC NO KRN` shows, or
  any of KRN, WDOG, STICK, REC, PANEL, SUP is red; or the PSC display never
  appears; or **the `PSC TEST` band was never seen** (N-5) and the exception
  does not apply (**it wins**, A4-5: note "PSC TEST not seen" and go to D); or
  the PSP powers off, suspends or goes permanently black before input died.
- **TRIANGLE (N-1):** when KRN, WDOG, STICK, REC, PANEL and SUP are green, hold
  TRIANGLE for 2 s **whatever POLL shows**; if BTN does not turn green, release
  2 s and hold again, up to three holds.
- **Exception, possible early death:** KRN, WDOG, STICK, REC, PANEL, SUP pass
  but POLL fails (`POLL:RATE`, `POLL:RET`, `POLL:NW0`) and/or BTN fails after
  three holds: no abort, input may already be dead (9.6: deaths before 36 s);
  H1, H3, H5 fail `POLL:RET`/`POLL:NW0`, H9, N4, N5 fail `POLL:RATE`, H2, H6
  fail BTN. Note the condition, go to the post-death script; the run counts.
- **The one live-device case:** if the **only** red item is POLL with
  `POLL:RATE` and BTN is green (e.g. a persistently failing 0x33, whose result
  the driver discards, `joypad_psp.c:486`: ≤ 9.4 polls/s while GetCtrl2
  works), tap SELECT once (line 5 must read `MOUSE ON`, else tap once more),
  click L five times: if `IN` rises, write "POLL:RATE only, IN rising" and
  continue with C0; otherwise the exception applies. G3 R4's read-through must
  walk this branch.

### 8.4 Display-only onset hint

`DEAD?` on line 1 when `P08` results are all negative for 2 s, or HOLD for 2 s
outside the reference step, or `jp_loop` stops for 1 s, or `DELIV` ≥ 3 s after
`IN` rose. **It controls nothing**; the operator confirms (RUNBOOK C5).

### 8.5 Host-side tests (Stage 3; stated so the design is testable)

The ring, record and reader code compiles on the host with stubbed `REG32`,
CP0 and `current`. Stage 3 drives synthetic sequences for H1-H10, N1-N11, N1m,
N1p, N2b, H10b and LEDSPLIT, including a simulated Nop at each of P0-P7 in
the middle of a P record, a takeover, torn slots and truncation at every byte
offset. The decoder must classify each and report "unclassified" with raw
data for a sequence matching none. Further tests:

| Test | Pass condition |
|---|---|
| **VFAT-FI (r3, A3 IF5 fix 4): this tree's own `fs/fat` with a fault-injecting block device.** A MIPS Malta kernel (`arch/mips/mips-boards/malta` is in this tree) built from a copy of this tree with the staging toolchain and `CONFIG_VFAT_FS`, plus a test-only RAM block driver `psc_faultblk` that completes bios synchronously like `ms_psp.c:228-276` and fails, by a schedule set through `/proc`, writes to chosen sector classes (FAT, directory, FSINFO, data) in chosen windows; run under `qemu-system-mipsel -M malta` (feasibility UNVERIFIED, R18). `pscol`'s segment and flush code, built as a static ELF, writes 30 simulated minutes of records from a simulated `/proc/psc`. Schedules: an outage covering a creation step that allocates (FAT write fails); an outage covering one steady flush; a 30 s burst; ≈ 100 single-tick outages; an outage across a switch; a failing read-back; **(r4, A4 F6) persistent refusal for the rest of the run of the FSINFO sector, of the `PSCLOG` directory sector, and of the FAT sector at the allocator**; **(r5, A5-1)** every write fails for exactly the tick of a creation's step-0 `fsync`, then the stick recovers; a 30 s whole-stick burst starting during an 8 KB creation; a 10-minute whole-stick burst during a hold; **(r5, A5 IF9)** a 2 MB data range of a ready file refusing writes after its creation, and the same range spanning the active file and the next; **(r5)** a data range ahead of the allocator; each with the block driver paced at 25, 30, 52, 100 and 300 KB/s, and with the driver's `DBG` printks kept (OE8) | after each schedule, the image mounted read-only on the host (loop mount or mtools) and decoded: **every record with `seq < durable_next` at the end is present** (in the copied files, or with `--raw` where the decoder asks for it); the guest log has **no "Filesystem panic"**; abandoned files hold no records; **no alias is ever written** (the worker's `inode reused` EVENTs against the fault driver's write log: no data sector of an alias's clusters written after the alias's `open`); the next fresh file after a step-0 failure is created within 10 s plus one tick of the stick's recovery (**r7, A6-3**: after a whole-stick failure the next attempt waits ≥ 10 s, 4.4 step 6); the raw-image scan recovers the same set; no hold exceeds 114.7 s; names used ≤ 1 + (outage seconds / 10) per outage. **Persistent schedules (r5, full scope):** META detected within 30 s of onset (EVENT, UHB b23, `meta_sector`, line 6), **`durable_tick` keeps advancing (no panel after the first 3 s), no record lost, no hold over 114.7 s**, creation continues (IF8: a file confirmed within 60 s; IF7b, **r7**: aliases rejected, a fresh file CONFIRMED within 20 ticks of the first creation attempt after onset with ≤ 153 names up to it, and every later creation ≤ 17 names; **(A7-2)** the IF7b schedule runs with guest memory well above the page-cache total, so reclaim never evicts the rejected inodes (15.3)), and **no record already written is destroyed** (no sector of a region handed to `write()` written twice). **IF9:** `region bad` after 3 FAILED flushes, no record lost, no hold over 114.7 s |
| Full-ring first flush (every ring full at the collector's start) | every RECS chunk ≤ 65,536 B, every flush ≤ 40,960 B; lag falls every tick; only first blocks report `lost > 0` |
| Takeover: worker killed; separately, worker frozen 35 s | the supervisor runs the worker loop as instance 2, creates a fresh segment at 64 KB per tick, seeks to `durable_next`, no `seq` gap except counted first-read losses; a takeover before the first durable flush keeps the WB record |
| **(r3, A3 IF6)** reader: a corrupt mid-ring `seq`; a forward jump of the P head; a backward jump | the reader skips and counts (`slot_bad` +1, resp. the skipped slots), `f_pos` advances, the next drain is complete; the collector writes an EVENT and turns REC red; a backward jump counts `head_regress` and resyncs; **(r7, A6-4)** `pread` windows interleaved with ordinary drains: each `pread` returns the records at its own offset, and the next `read()` continues from the previous drain's end with no record skipped or repeated |
| Errors, **(r4, A4 F6)** with the modelled stick speed 25, 30, 52, 100 and 300 KB/s (tick time + bytes / speed), against both the flush and the creation path, **(r5)** with failures injected as whole ticks and as single operations, and with S records supplied by the harness: single flush failure; 60 s of failures on every tick; ≈ 120 sporadic failures over 30 min; 130 s burst; creation failures (`open`, `write`, `fsync`, FAT1, FAT mirror, directory, FSINFO, data, read-back); a flush whose `fsync` fails while its data sectors succeed; **(r7, TE10)** an active file still in creation during catch-up (40,960-byte flushes) with two failed steps, and separately with a 3 s burst | no record lost except, for 130 s, those older than the ring span (counted); each FAILED flush has a `flush fail` EVENT, no region handed to `write()` is written again, its records are re-sent by range after the next DURABLE flush and a DURABLE flush is never re-sent; a flush with data written and `fsync` failed is DURABLE (b30); a step is stopped exactly when a FAT1 write failed and retried in place otherwise (≤ 3); no hold exceeds 114.7 s; flushes never extend a file; **(r7, TE10)** the worker holds and resumes in the same file at its own `seg_end`, never sets `seg_end = 1,536` in a file that has been active, no region is written twice and the boot records are intact |
| Volume: 15 min at 17.86 polls/s, 32 KB and 64 KB clusters, creation minutes included (A4-1) | P, POLL, W within ± 2 % of 5.1; flush S ≤ 22.6/s outside and ≤ 27.0/s in creation ticks, creation S ≤ 11.5 per 8 KB and ≤ 27 per 64 KB step; total within ± 10 % of 7,598 B/s; PROCS within [800, 2,400] B; `led_calls` = 2 × simulated sector writes; S count ≤ sectors written and Σ `nsect` = sectors written |
| **(r4)** Decoder: a pull during a creation (that file holds no RECS); a stopped prefix file; META; a Nop's own failure with `t_busy` 0 | no `RAW IMAGE REQUIRED` in the first case, required in the others; the last classified WB (UL6) |
| **(r5, A5 IF10)** Decoder: files from an earlier boot of the same build (other nonce) in `PSCLOG` and in the image; a CRC-valid chunk of another boot inside a file's tail above `conf`; a `(ring, seq)` pair with two different contents; a straddle at Nop k with both results valid and onset at Nop k+1 (UL7) | nothing of another boot merged; the tail chunk listed as above the confirmed extent; the conflict reported with both copies; the k straddle listed with its step and the two-stage candidate printed |
| **(r5)** S-record verdicts: synthetic S windows (data sectors all good with `fsync` failed; one data sector failed; FAT1 failed, FAT mirror failed, directory failed at step 0 and at step 5; **(r7, A6-1)** step 0 with its own entry OK, then another directory sector failing later in the window; step 0 with its own entry failed, another directory sector OK; step 0 with no worker DIR record after its DATA records, or a `pdflush` DIR record before the worker's first; a skipped `seq`) and a wrong partition offset | DURABLE, FAILED, stopped, CONFIRMED, abandoned (own entry), CONFIRMED, CONFIRMED, abandoned, abandoned, FAILED as 4.8 and 4.4 step 4 define; the wrong offset fails the geometry self-check (STICK red) |
| Panel: paint routine on the host into a 512 × 272 buffer from stats snapshots | layout of 2.10 and 10.8, every field transcribable; `panel_cd` fires at ≡ 125 mod 250, never ≡ 0 mod 1250; the band is cleared once when the condition ends; title `PSC MS RO` when `ms_rdonly` or `fat_panics` is set |
| **(r3, N-2)** HUD render on the host, every state of every line | no glyph pixel at x ≥ 428 in rows 8-39 or in rows ≥ 168; every line ≤ 35 characters; every check name and POLL condition legible |
| **(r3, N-4)** stale-frame sequence whose healthy `rx[2]` is not 0x08 | classified H6 (template `rx[2]`), not H0; with the template removed, `rx2 literal` flagged |
| **(r3, A3 UL5)** suspension at S14 with LED operations and a clean read-back, `ret −4`, input then dead; and a run of benign overlaps | onset classified N1m (not "none"), never "H10 refuted"; the harm-rate comparison of 10.7 step 7 printed with its pre-registered rule |
| **(r3, A3 TE5)** a Nop between the load and the store of an LED read-modify-write | LEDSPLIT reported with the loaded value and the G3 transition |
| TE2 (A1): sample at S12, thread suspended, resumes to S18, preempted, Nop drains the rest | `lc_epc` in S18, `ext_flags` b5; decoder reports P6; a deliberately wrong `lc` gives `inconsistent` |
| TE4 (A2): a Nop at S14 lasting over a tick, a nested tick, preemption at the outer return, LED write-back | `lc_epc` = S14, `lc_nested` counted, `lc_flags` b4; decoder reports H4 P4 + H10 (S13..S20) |
| OE3 (A2): the thread woken at a known Count and held off by known classes for 0.1-1.5 ticks; **(r4, F5)** preempted at S14 by a known class for 2 ticks | `wk_delay`, `wk_wrk`, `wk_cls0/1`, `wk_nsw` as expected; late-start attribution names the collector first when it held the CPU; `pre_cls`, `pre_tot`, `pre_wrk`, `pre_flags` as expected and N1 printed with its holder |
| OE4 (A2): `pscol` built natively with `-fsanitize=address,undefined` against recorded and fuzzed `/proc` text (≥ 10⁶ inputs) | no sanitizer report; a corrupted guard makes the worker exit and the supervisor take over; later onsets marked `instrumentation-suspect` |
| UL3, UL4 (A2) | reply lag → N2b, not H6; HOLD stuck → N11, not H0 |
| Early death at 20 s | `NO HEALTHY TEMPLATE` if the window is short; H8/N2 `unassessable`; H1/H3/H5/H9 classified; `no C0 reference` |

---
## 9. Runbook

The procedure is [RUNBOOK.md](RUNBOOK.md): **A** on the Mac, block and
rehearse automatic mounting (A0), deploy `PSP/GAME/uClinux_TRACE/` (never
`uClinux`, `uClinux_FIX`, `uClinux_WIP`) with the baseline's `EBOOT.PBP`,
`kmodlib.prx`, `pspboot.conf` and our checksummed `vmlinux-0.22.bin`, check
≥ 256 MB free (4.4 step 8), **(r5)** create `PSCLOG` if it is missing, choose
battery or AC as in the 9.6 sessions; **B** boot and self-test, decided at 3:00
(8.3, including `MS SLOW` and `MS DIR FULL`); **C** reference pattern C0, then
normal use until death or 30:00, with the panel procedure C4; **D** the
post-death script and the two-display check D8, then the pull; **E** read-only
mount, copy, size check of **this run's** files, and a raw image whenever
RUNBOOK E requires it (after `SELFTEST PASS`: any red `MS` line, `READ-ONLY`,
`META`, `WAIT SPARE`, line 7 `WAIT`, a panel other than `PSC TEST`; a failed
D8; more than one file of this run smaller than 2 MB; a failed copy).
**(r5)** A run that showed `META` counts; D8 decides (4.7).

---
## 10. Decoder specification

Tool: `pscdec.py`, Python 3, standard library only, written by the Analyst
before the run (G3 R6). Inputs: the copied `T*.BIN` files and, when made, the
raw stick image (`--raw`), plus `System.map`, `epcmap.txt`, `regmap.txt` and
`panellayout.txt` from the exact build. It never modifies its inputs.

### 10.1 Consistency checks against the build

Stats words 20-22 must equal `System.map` and word 2 the build's `build_id`,
else the EPC analysis is refused with the reason (parsing still runs).
**(§17 R-4)** The build's `build_id` is read from `build_id.txt` in the build
directory given to the decoder (`BUILD/`), which must be the **packaged**
build's release directory (`System.map`, `epcmap.txt`, `regmap.txt`,
`panellayout.txt`, `banner.txt`, `build_id.txt`; for the G2-attempt-1 image,
`work/out/20261006T021722Z`, `0x9b3c599e`). `build_id.txt` holds `0x%08x` of
the CRC-32 (zlib, initial value 0) of `banner.txt`, which is the exact
`linux_banner` (1.7). A rebuild of the same commit has another banner (its build
time) and therefore another `build_id`, and is refused even when its
`System.map` is identical: the maps must come from the image that ran. The
decoder also checks that the CRC-32 of each FILEHDR's `/proc/version` text (up
to its first NUL, 10.2) equals stats word 2, and reports a mismatch.

### 10.2 File and chunk format

A file is a sequence of chunks; each flush ends with a PAD chunk to a 512-byte
boundary. **Chunk header, 20 bytes, `'<4sHHIII'`:** `magic` = `b'PSCK'`,
`type` u16, `hver` u16 = **5**, `len` u32 (payload bytes, ≤ 65,536), `fseq`
u32 (per file from 0; 0xFFFFFFFF in preallocation PAD sectors), `crc` u32 =
CRC-32/IEEE (zlib `crc32`) of the payload, which follows zero-padded to a
multiple of 4 (padding not in `len`); **(r5, A5 IF10) for every type except
FILEHDR the CRC's initial value is the boot nonce** (`zlib.crc32(payload,
nonce)`), so a chunk written by another boot fails its CRC here; a FILEHDR has
the plain CRC (initial 0) so that its nonce can be read first. **Writer
guarantees (4.3):** one RECS chunk per flush ≤ 34,404 B (**§17 R-6**: new-records
and re-send blocks); KMSG ≤ 4,096, EVENT ≤ 1,024, PROCS ≤ 2,400 B of
payload; STATS 768; UHB 84; a flush ≤ 40,960 B starting at a multiple of 512;
every segment starts with FILEHDR + PAD = 1,536 B written by its creation, and
no other flush has a FILEHDR. The decoder keeps 65,536 as a sanity bound.

| type | Name | Payload |
|---|---|---|
| 0 | PAD | zeros (492 bytes in preallocation sectors) |
| 1 | FILEHDR | `'<8sIIIIIIIII'` (**r5**, 44 bytes): `b'PSCLOG5\0'`, `fmt` = 5, `run`, `seg` (`nnn`), `inst` (1 worker, 2 supervisor after takeover), writer pid, supervisor pid, `now_tick`, `now_jiffies`, **`nonce`** (4.2); then the 768-byte stats block; then `/proc/version`, NUL-padded to 256 bytes (1,068 bytes) |
| 2 | RECS | blocks with header `'<BBHI'`: `ring` (0 P, 1 POLL, 2 W, 3 S, 4 M; **(r5)** b7 set for a **re-send block**, 4.6), `recsize_div4` (P and M 20, POLL 10, W 72, S 10), `count`, `lost` (`seq` values skipped since this ring's previous new-records block; 0 in a re-send block); then `count` records; per ring per flush one new-records block, even if empty, preceded by at most one re-send block |
| 3 | STATS | the stats block (1.7) |
| 4 | KMSG | raw bytes from `/proc/kmsg` |
| 5 | PROCS | lines `<label> <pid> <contents of /proc/<pid>/stat>` with labels `JP`, `OSK`, `MD`, `WRK`; `JPSTATUS` lines (`State:`, `SigPnd:`, `ShdPnd:`); `MEM <MemFree line>` |
| 6 | UHB | **`'<21I'`** (**r5**, 84 bytes): `tickno`, `stats_now_tick`, `gtod_sec`, `gtod_usec`, `uptime_cs`, `memfree_kb`, `mouse_pkts_total`, `mouse_press_total` (`IN`), `bytes_synced_total`, `last_write_ms`, `last_fsync_ms`, `max_fsync_ms_60s`, `max_tick_ms_60s`, `write_errs` (FAILED flushes and creation steps, 4.8), `last_errno` (the last error of any `write` or `fsync`, also on a DURABLE flush), `flags`, `durable_tick`, `lag_max`, `seg` (**r5 layout, A5-4**: bits 0-9 active `nnn`, 10-19 `nnn` of the file being created, 20-28 its `conf` as v = ⌊conf / 8,192⌋ (0-256; **r7, A6-3:** the decoder takes conf = SEG for v = 256, else 8,192·v + 1,536, exact because a file in creation always has conf = 1,536 plus a multiple of 8,192 (4.4 steps 2-3: step 0 is 1,536 B, later steps 8 or 64 KB, only the last ends at SEG); v = 0 before step 0 is confirmed reads as 1,536, below which lies only the FILEHDR), 29-30 complete files ahead (0-2), b31 a creation in progress), `drain_stuck`, **`nonce`**. `flags`: b0 holding; b1-b8 self-test KRN, WDOG, STICK, REC, PANEL, SUP, POLL, BTN; b9 supervisor alive; b10 no stick; b11 drain complete; b12 catch-up; b13 a complete file ahead; b14 writer is the supervisor after a takeover; b15 re-send pending (queued ranges); b16 memory-guard violation; b17 creation abandoned; b18 creation in progress; b19 segment switched; b20 `MS` line red; b21 read-only; b22 REC alarm; **(r4)** b23 META (4.7); b24 a file's growth stopped; b25 the active file is not complete (prefix); **(r5)** b26 waiting after an abandon (r4's `seg` b31); b27 a file retired (`region bad`); b28 an alias rejected; b29 speed gate passed; b30 a DURABLE flush whose `fsync` returned an error |
| 7 | EVENT | ASCII lines: worker start; takeover (`death`, `stall`, `guard`); write error; **(r4)** `flush fail`, `resend` (ring ranges), `stop`, `meta err` (**r5**: with class), `meta clear`, `readback cached`; **(r5)** `meta bypassed`, `flush meta err`, `inode reused <name> <ino>`, `region bad <name> <seg_end>`, `speed <KB/s>`, `names budget <n>`; **(r7)** `conlevel <ret> <errno>` (4.2); catch-up start/end; head regress; drain stuck; segment create, ready, abandon (name, errno, offset, step), switch (`full`, `bad`); hold start/end; read-only; `guard ok stack_hw=<bytes>`; `guard <which> <tick>`; `events dropped <n>` |

**Parsing.** Scan for `magic` at every 4-byte offset; accept a chunk if
`type` is known, `len ≤ 65,536`, the bytes exist and `crc` matches (plain for
FILEHDR, seeded with the run's nonce for the rest), else advance 4 bytes; skip
PAD; drop a truncated tail chunk, keep every earlier one. **(r5, A5 IF10) Run
selection:** the FILEHDRs give (`run`, `nonce`) per file; the decoder analyses
one run (default the highest `run`, or `--run`), accepts other chunks only if
their CRC verifies with that run's nonce, and lists files of other runs and
ignores them (also for the raw-image rule below). Within a file, a chunk above
the file's confirmed extent (`segment ready` = SEG; `stop <name> <conf>`; UHB
`seg` conf for the file in creation) is listed as an anomaly, not merged.
Records merge by (ring, `seq`); exact duplicates (re-sends) are removed; **a
duplicate with different content is a conflict**, reported with both copies,
never dropped. File names are not authoritative (an alias's name can end up on
a reused slot, 4.4 step 1); the FILEHDR `seg` is. `--raw` scans a whole-stick
image the same way, keeping only chunks that verify under the run's nonce,
grouped under the nearest FILEHDR of that run.
**(r3, A3 IF5 fix 3) The raw image is the primary path** whenever the copied
files of this run contain an EVENT `flush fail`, `stop`, `abandon`, `meta err`,
`read-only`, `takeover`, **(r5)** `flush meta err` or `region bad`, UHB
`write_errs > 0` or b30, or **(r4, A4-3)** a file of this run that holds a RECS
chunk and is not 2,097,152 bytes (a file being created that never became
active holds none, so a pull during such a creation alone does not count;
**(r5, A5 TE7)** one that was active does, and then the image is needed): the
decoder then requires `--raw` and refuses a final REPORT without it ("RAW IMAGE
REQUIRED"). With both it merges them and lists records found only in the
image.

### 10.3 Record formats (field for field with section 1)

```
SC    '<IIIIHBBhBBIHHHHHBBHHBBBB16sIHBBIHH'                                 = 80
      seq tick_in c_in c_out | dtick cmd txlen ret nwords retries | ack_polls |
      drain drain_last gpio_in spi_st9 spi_sttx | ctx wn | w_head_lo pre_wrk |
      pre_cls ms_delta pre_flags preempt_delta | rx[16] |
      lc_epc | lc_dtick lc_n lc_flags | led_or | led_pid pre_tot
WEXT  '<5I16I5IBBBB4I4I16IHH'                                               = 208
      epc cause status ra sp | r[16] | pid p_head jp_loop t_entry_tick t_entry_c |
      t_busy jp_stage ext_flags cur_pcnt | c_pre lc_tick lc_c_pre lc_cmd_id |
      lc_epc lc_cause lc_ra lc_sp | lc_r[16] | lc_n rsv
W     = SC (80) followed by WEXT (208)                                      = 288
POLL  '<IIIIH7B2b5BHHBBBB'                                                  = 40
      seq tick_start c_start c_end | sc_seq_lo | body_ticks ri_branch pi_flags
      nqueues push_ok push_fail mouse_flags | dx dy | sig period preempt_delta
      stage_max nsc | wk_delay wk_wrk | wk_cls0 wk_cls1 wk_nsw rsv
S     '<IIIIIHHBBHBBHII'                                                    = 40
      seq tick_on c_on c_off sector | dtick pid | nsect flags | p_head_lo |
      led_ops rsv | rsv | rd_set_or rd_clr_or
M     = SC                                                                  = 80
STATS '<192I'                                                               = 768 (word map in 1.7)
CTL   '<I7I'                                                                = 32 (2.8; not in the files)
```

`r[16]` and `lc_r[16]` hold registers 2..15 then 24, 25. `ret` is s16, `dx`,
`dy` s8, everything else unsigned. A record whose `seq` is `0xFFFFFFFF` is
dropped; duplicates by (ring, `seq`) are removed; `seq` gaps and block `lost`
counts are reported as **explicit gaps in the timeline**. The 16-bit link
fields (`w_head_lo`, `sc_seq_lo`, `p_head_lo`) are expanded by choosing the
value nearest the record's own position; **(r4, A4 IF6)** if that lands on a
missing `seq`, the record is paired by `(tick, Count)` instead (flagged). Every
string and offset of section 1 was rechecked with `struct.calcsize` (r5, 15.6).
**(§17 R-1)** An SC, W or M record with `nwords` = 7 and `rx[14]` = `rx[15]` =
0xff is flagged **`nw7or8`** and carries the value set {7, 8} (1.2); every other
record carries {`nwords`}. The CSV keeps the raw value and the flag, and
REPORT.md counts the flagged records per command and origin.

### 10.4 Stats

`'<192I'`, named per 1.7 (words 62, 63 signed); one row per STATS chunk in
`stats.csv`; any counter decrease is reported.

### 10.5 Time reconstruction

`CPT = 883651`. P, POLL, M, S at `(tick, c)` as stored; SC records end at
`(tick_in + dtick, c_out)`; WT at `(tick_in, c_in)` with `tick_in ≡ 0 mod
1250` asserted (exceptions reported); WB at boot; the thread's last running
tick for a command at `tick_in + lc_dtick` (SC) or `lc_tick` (W). Fine time `t
= tick × CPT + c` (`c > CPT` flagged "long tick"); seconds `tick / 250`, wall
time `total_counts / 220,912,896`. Each record gets `wdph = tick mod 1250 + c
/ CPT` and its distance to the nearest WT record, `wb_kupdate` and collector
activity (creation, catch-up, re-send, switch, takeover, panel paint, guard
violation: EVENTs, UHB flags, `panel_last_tick`, `kguard_bad`). Every SC
record with `dtick > 0` is listed with the ticks it crossed; one crossing a WT
tick must have `wn ≥ 1` (checked). `now_jiffies − initial_jiffies` against
`now_tick` gives the offset to dossier
9.6's uptime (`include/linux/jiffies.h:137`).

### 10.6 EPC map and register map (Stage 2 deliverables, reviewed at G2, tested in Stage 3)

`epcmap.txt` (from `objdump -d vmlinux` of the final build): `<start> <end>
<label>` per range: S1..S23, `ENTRY`, `EXIT`, `REC` inside `Syscon_cmd`;
**(r3)** `LEDRMW` for the instructions between the load and the store of each
LED read-modify-write in `psp_led_ctrl` (A3 TE5); function names elsewhere
(`mousedev_*`, `schedule`, `ms_wait_ready`, `ms_wait_ced`, `psp_ms_*`, ...).
`regmap.txt`: per window step, where `i`, `ptr`, `cnt`, `result`, `spin`,
`spin_ack` live, and for `LEDRMW` the register holding the loaded value; it
states whether `i` and `ptr` are among registers 2..15, 24, 25 at S11 and
S16-S18 (baseline: `t0`, `a3`, `syscon.o +0x180..+0x1b4`, `+0x244..+0x298`),
which G2 checks (R10).

**Step → P-point (recon §5.1):** S1-S4, `ENTRY`, `EXIT`, `REC`, S21-S23 → P0;
S5-S10 → P1; S11 → P2 (k from `i`, in `r` or `lc_r`); S12-S13 → P3; S14 → P4 or
P5a (split by the W record's own `ack_polls`, `drain`, `drain_last`, row H4);
from the S14 exit to S15 → P5b; S16-S18 → P6 (j from `ptr`); S19-S20 → P7.

If Cause b31 (BD) is set: "EPC or its delay slot". A W record with `ext_flags`
b7 carries a softirq's EPC: listed with its label, but the step comes from
`lc_epc`, which a nested tick never overwrites; an SC record with `lc_flags`
b4 is annotated "nested tick".

### 10.7 Algorithm and outputs

1. Parse, validate, deduplicate; merge all rings into one timeline ordered by
   `t`, ties W before P (a Nop completes before the command it interrupted).
2. **Template.** Compute the onset candidates first; window = first P record
   to 5 s before the earliest of O1, O2, O4, O5, excluding C0 if its times are
   given. If ≥ 10 s and ≥ 150 polls: learn per command `nwords`, `rx[1]`,
   **`rx[2]`** (N-4), ranges of `ack_polls`, `drain` and duration, analog
   jitter, the `gpio_in`/`spi_*` distributions, the LED read-back ORs.
   Otherwise `NO HEALTHY TEMPLATE`: H8 and N2 `unassessable`, O3 skipped,
   code expectations (`drain = 0`; for 0x08 ≥ 5 words, exact length from
   `rx[1]`; finite `ack_polls`; `ret = rx[0]` when `ret > 0`;
   `rx[2] ∉ {0x80, 0x81, 0x83, 0x86}`), the WB, boot M and pre-onset WT records
   as the H8 baseline, the literal `rx[2]` rules flagged `rx2 literal`, H6/H7
   from the source bit map.
3. **Per poll:** pair POLL with its 0x33 and 0x08 records via `sc_seq_lo`;
   recompute the branch against `ri_branch`; simulate `lastKeys`,
   `mouseMode` and the mouse deltas (`joypad_psp.c:505-527`, `:593-658`)
   against `pi_flags` and `mouse_flags`; report each `mouseMode` toggle with
   its frame (N10).
4. **Onset candidates** (all reported): O1 last raw change of `key`; O2 last
   POLL with a delivery, none for ≥ 10 s after; O3 start of the longest
   trailing run outside the template; O4 last `jp_loop` increment, if it
   stops; O5 last rise of `fop_read_ret` and of `IN`. For each: tick, `wdph`,
   **the 6.3 placements** (last successful thread command, first failed one,
   nearest Nop: before, containing or after tick 1250k), the nearest
   `wb_kupdate` and collector activity, S records within ± 100 ms, a ± 30 s
   raw dump, the operator's stopwatch time.
5. **Classify** with section 6, in order: thread-stopped shapes (H9, N4, N5,
   N9; **(r4, A4 OE5)** a stop between a takeover and the first PROCS after it,
   or with `jp_exit_tick`, annotated);
   persistent states (H1, H2, H3, H5, N2b before H6, H6, N2, N3, N11); H7
   (a)-(e), N6, N10; H8 flags; triggers (H4 with the P-point and the
   cross-check; WB; H10 with bits and window; N1m; N1p; N1; H10b; LEDSPLIT;
   N8; N1, N1m and H10 with their holder, `pre_*`).
   Each classification carries the guard status; an onset at or after a guard
   violation is **`instrumentation-suspect`**. Thresholds (90 %, 10 s, ± 2
   polls, ± 2 ticks, ± 2 s) are printed. **(r5, A5 UL7)** Every WT record
   within ± 2 cycles of an onset candidate is listed with its step and both
   results, valid straddles included, and "straddle at Nop k with both results
   valid, onset at Nop k+1" is printed as candidate `H4 two-stage` beside WB and
   H4. Every matching row is listed with its
   evidence (ring, `seq`) and the triple; if none, **H0 / unclassified** with
   the raw windows.
   **P-point cross-check (A1 TE2):** the thread's result must be one recon
   §5.1 allows, else `inconsistent` (with `epc`/`lc_epc`, `ext_flags`,
   `lc_n`): P0, P1, P7: its own valid reply. P2: −4; −2; a retried success;
   E3 (`ret 0`, `nwords 0`); E4 (`ret 0`, `nwords ≥ 1`, `rx[0] = 0`); a
   foreign reply. P3: a foreign reply (E7); −4; E3. P4, P5a: E3; E7; −4.
   P5b: E3; E7. P6: −2 with `nwords` = j; a retry if `rx[2] ∈ {0x80, 0x81}`;
   anything if between its status test and its data read.
   **H10 conclusion (r3, narrowed, A3 UL5):** one of `H10 trigger` (row H10,
   bits and window); `N1m` (row N1m); `H10 untested in this run` (no LED
   operation overlapped a thread suspension at S13..S20); `H10 write-back
   mechanism refuted: the set/clear registers did not read back the
   transaction's lines` (≥ 1 such overlap with `led_or & ~0xC0 = 0`). The last
   is **never printed for a run whose onset command itself had `ms_delta > 0`
   during a suspension in S5..S20**, says nothing about read side effects, and
   is never inferred from zero bit-3 counts.
6. **Outputs:** one CSV per record type, `stats.csv`, `uhb.csv`, `kmsg.txt`,
   `procs.txt`, `events.txt`, `segments.txt`, `bad.txt`, `gaps.txt`,
   `timeline.txt`, and `REPORT.md`: the classification; hazard statistics
   (straddle and benign-interleave rates per step, LED operations in G3-high
   windows, the G3-low gap, `pdflush` alignment); late-start attribution;
   costs; the loss at the pull (last durable tick against the pull time).
7. **(r3, A3 UL5) Pre-registered with/without-LED harm-rate comparison.** Over
   P records before the earliest onset candidate, a *mid-window suspension* is
   a command with `preempt_delta > 0`, `lc_flags` b0 and b2, and `lc_epc` in
   S5..S20; group L has `ms_delta > 0`, group N `ms_delta = 0`; *harm* = the
   result is not its own valid reply (`ret ≤ 0`, or `rx[2]` not the
   template's value for its `cmd`). Printed: n_L, h_L, n_N, h_N, each rate
   with its 95 % upper bound (1 − 0.05^(1/n) when h = 0), and the one-sided
   Fisher exact p for "harm more frequent in L". **"LED activity during a
   suspended transaction is associated with harm on this hardware"** only if
   p < 0.01 and h_L ≥ 3; otherwise "no association detected" with the counts.
   The table, with the onset command added, is printed beside any N1m.
8. **Pre-registered no-death inference (7.3, A1 OE3).** With no onset: per
   P-point print 1 − 0.05^(1/n) (n = Nops that hit an in-flight command there,
   ∞ for 0); "H4 at P4/P5a is not sufficient on this kernel at p ≥ 0.1" only if
   n(P4) + n(P5a) ≥ 30, else "inconclusive" with the exposure and the late
   starts' delay, collector part (`wk_wrk`), last holders and Memory Stick
   part, **(r4)** and the in-flight preempted time by holder class with its
   collector part (`pre_tot`, `pre_wrk`, `pre_cls`). All rules and thresholds are fixed in the tool before the run (G3 R6).

**`nwords` 7 or 8 (§17 R-1), every rule that reads it.** A flagged record (10.3)
differs from an exact one only in whether an 8th word 0xFFFF arrived; its 16
`rx` bytes, and so its checksum result `ret`, its `rx[2]` and its button bytes,
are the same either way. Rule by rule:
- **Stats outcome counters** (1.7 words 31-51: `ret == 0 && nwords > 0`, `ret
  == 0 && nwords == 0`): unaffected, 7 and 8 are both > 0.
- **H1, H3** (`nwords = 0`) and the P-point outcome **E3** (`ret 0`, `nwords 0`,
  step 5): unaffected; 0 is exact, the case needs 7 words read.
- **H2, N10, E4** (`nwords ≥ 1`), **H3 against N2b** (N2b has `nwords ≥ 1`),
  the self-test **POLL:NW0** (`nwords ≥ 1`) and **REC** (`nwords ≤ 8`; `nwords
  = 0` ⇒ `rx` all `ff`): unaffected; no threshold lies between 7 and 8.
- **Template comparisons**, step 2 (per-command `nwords`, and the code
  expectation "exact length from `rx[1]`"), used by **H8** flags and **O3**,
  by **WB** and **H4** (the Nop's own reply against the template), by **N2b /
  UL3** (command n's reply against the template of command n−1's `cmd`) and by
  **H5** wherever the received length is compared with `rx[1]`: a record matches
  a template value or expected length L when L is in its set. The outcome could
  differ only for a frame whose 8th word would be exactly 0xFFFF, and then the
  bytes these rows decide on (`ret`, `rx[1]`, `rx[2]`, the checksum, the
  response code) are identical; H5 itself reads `ret`, `retries` and `rx`, not
  `nwords`. If the healthy template holds flagged records for a command, the
  decoder prints that the ambiguity is live for it. By the source a healthy
  0x08 reply is ≥ 5 words (`syscon.c:362-365`); whether any healthy reply is 8
  words is UNVERIFIED, and the template shows it.
- **P6 cross-check** (step 5, "−2 with `nwords` = j"): j ≤ 7 (the Nop came after
  j of n ≤ 8 words), so a flagged record with j = 7 passes. The check then
  cannot flag the one inconsistency "the thread read an 8th word 0xFFFF
  itself", which an exact count could; −2 is allowed at P6 either way, so the
  P-point and the classification do not change.
- **Step 7** harm (`ret`, `rx[2]`) and **H6, H7, H9-H10, N1-N11** other than
  those above: do not read `nwords`.
- **Display only:** the panel's line 4 (2.10) and the boot `printk` `nw=` (2.8)
  show the raw value. The panel does not show `rx[14..15]`, so a panel
  `nwords` 7 reads "7 or 8"; the records decide.

### 10.8 Transcribing the stall panel from photographs

`--panel photo_id=<line 1>|...|<line 6>` is parsed by column
(`panellayout.txt`, tested in Stage 3), EPCs mapped, each panel placed by its
`NOW` tick. A panel repeating the same Memory Stick marker with the running
EPC in `ms_wait_ready`/`ms_wait_ced` and `preempt_count > 0` is reported as
"Memory Stick driver hang (instrumentation exposure, not the investigated
failure)". After `PSC MS RO` the photographs are the only later record.

---
## 11. Open risks (every place this design guesses), and alternatives not taken

### 11.1 Risks and guesses (28; renumbered in revision 3, 11.3 maps the old numbers; R23-R24 new in r4, R25-R28 in r5)

| # | Risk or guess | Where it matters | Mitigation or check |
|---|---|---|---|
| R1 | This kernel (timeout patch) may not die in 30 minutes, or may die by another permanence path; the 9.6 deaths were on the 2008 image, whose waits are unbounded ([BIN] V6) | whether the run reproduces | Observation 6 says it dies on the same timescale; "no failure" is a reported result with the 7.3/7.5 exposures; an unbounded spin would appear as N9 |
| R2 | gcc may schedule capture code, or spill, into S5..S20 | the "0 in window" claim | G2 objdump criteria and the capture-removal order (2.1, 7.2) |
| R3 | CPU constants (IPC, Count = core clock, cache) are guesses; reading CP0 Count/Status is assumed free of side effects (the kernel never reads Count today, recon §6) | µs figures; every record | Costs measured on the device; CP0 moves are not MMIO and run from the self-test on, so a problem shows before death |
| R4 | No new register reads: H8 sees only values the code already reads | H8 | Declared blind spot (row H8), required by dossier 9.1 |
| R5 | EPC capture assumes `thread_info->regs` is set by the interrupt entry (`genex.S:166-167`, `:266-267`) and the timer is the only interrupt (`psp.c:637-654`) | H4, H10, N1 step | Bounds checks; WDOG checks `regs` valid; another IRQ would print "Unknown IRQ" into KMSG |
| R6 | Syscon timing sensitivity: G4L latched or level (resumption ≈ 2-4 µs later); G3-low gap ≈ 2.1-3 µs longer (**§17 R-3**, measured counts; r5 said 1 µs and 0.75 µs), original gap unknown | could lower a timing-dependent failure's rate | Gap measured per poll and reported (7.3); level-sensitive G4L judged unlikely (separate acknowledge write, `syscon.c:159`) |
| R7 | LED read-modify-writes ≈ 3.1× telem's on average, ≈ 7.9× in creation minutes, ≈ 46× in 64 KB steps (preallocation); cluster size and FAT copies UNVERIFIED | H10 exposure | Raises, does not mask; measured (`led_calls`, S records, read-back ORs); creation intervals flagged by the decoder (7.5) |
| R8 | Memory Stick throughput and `fsync` duration are UNKNOWN; the design needs ≈ 20.8 KB/s of physical writes on average; the collector's start time (≈ 20-40 s) is UNVERIFIED | loss bound, creation time, catch-up, self-test time | **(r5)** Measured at start and gated: STICK needs ≥ 30 KB/s (4.8, 8.2), else `MS SLOW` and an abort. The model of 15.6 loses nothing under the sporadic pattern (98 events per 30 min, whole-tick and per-operation) from 28 KB/s up (**r7, A6-3:** at 25 KB/s 1 whole-tick run in 260 loses 15.2 s) and under whole-stick outages ≤ 100 s at ≥ 30 KB/s; the first complete drain comes ≤ 35 s after worker start at 30 KB/s. The kernel shows the durable age; UHB timings and the first UHB's `uptime_cs`; the runbook waits 90 s (+45 s); **(r5)** a bad data region costs 3 FAILED flushes before the switch (4.6; the r4 wording "one failed flush per tick that meets it" was wrong, A5 IF9) |
| R9 | P4 against P5a relies on the syscon's behaviour after a dropped G3 (recon §5.1) | H4 point | Several fields; if ambiguous, reported "P4 or P5a" |
| R10 | The EPC and register maps must match the build, and `i`/`ptr` must sit in registers 2..15, 24, 25 for a suspended thread | H4 step, P2 k, P6 j, LEDSPLIT | 10.1 address and `build_id` checks; G2 checks `regmap.txt`; the step itself does not depend on k/j |
| R11 | **(r3)** A FAT or directory sector write that fails (in a creation or a flush) and destroys the sector's old content, or a FAT write lost silently, could damage the on-disk chain or entry of the active segment (hardware behaviour UNVERIFIED). **(r5)** Also: a stopped file whose last link L → c reached the stick while c's own entry did not (A5 red team IF5 residual) has a directory size covering a free cluster, so its Mac copy can fail; a destroyed directory sector could free the slot of a file in use, whose alias the r5 test then rejects (4.4 step 1); the only remaining source of `fat_fs_panic` is silent loss | the Mac copy of that segment | The kernel keeps writing through the cluster cache (4.4); flushes never read the unconfirmed link and never truncate (4.4 step 5, `mm/filemap.c:2161-2162`); the stick is mounted read-only and a raw image is mandatory after any error (RUNBOOK E); the decoder's raw path needs no FAT (10.2); VFAT-FI tests the reported-error cases (8.5) |
| R12 | The Memory Stick driver's unbounded waits (`memstk.c:59-65`, `:174-181`) could hang the machine in our own I/O (A1 OE1); preallocation doubles the exposure | a run spent on an instrumentation hang | Recorded and identified by the marker and panel (2.4, 2.10, 10.8), told apart from the failure (7.5); not bounded (J9) |
| R13 | The panel's cost (0.2-1 ms interrupts off) and its cached VRAM write-back are estimates | panel perturbation and visibility | Measured per paint; painted only in the 2.10 occasions, never on a watchdog tick; flagged per command (N1p); visibility confirmed by the operator (`PSC TEST`, abort item) |
| R14 | Supervisor death is not recovered; after a takeover there is no further recovery | collector restarts | Small code; `SUP DEAD`/`SUP RUN` shown; the panel covers a second failure |
| R15 | Busybox 1.7.0 `msh` with `pscol&`, and uClibc `vfork`/`execve`/`setsid` on no-MMU, are assumed standard | collector start | Same idiom as `rc.sysinit:14,18`; Stage 3 links and checks `flthdr`; a failure shows at the self-test (abort costs no run) |
| R16 | User processes keep kernel privilege (`process.c:81-83`, `uaccess.h:58`): a `pscol` bug could corrupt kernel memory or MMIO and cause a death | S5 | Guards, stack high-water, bounded reads, exit on violation; kernel guard words; ASan/UBSan fuzzing; `instrumentation-suspect`. **Residual:** a stray store that hits no guard (e.g. straight into GPIO SET/CLEAR) shows as an unexplained foreign frame or −4 with `wn = 0`, `ms_delta = 0` and no S overlap; the report lists this beside any such classification |
| R17 | Nested-tick detection relies on the softirq/hardirq count (`softirq.c:217,225`); the scheduler hooks sit at `sched.c:1657` and `:3700-3707` (`try_to_wake_up` is reached from `:1669`, `:1676`, `:3817`) | exact `lc` step; wake-up attribution | By construction; a missed nested tick shows as `lc_epc` outside `Syscon_cmd` while `t_busy` is set; G2 checks hook placement with objdump; Stage 3 tests |
| R18 | **(r3)** The VFAT-FI harness (a Malta build of this tree under `qemu-system-mipsel`) may not build or boot with the staging toolchain (UNVERIFIED) | evidence for the IF5 fix before the run | If it cannot be made to work, Stage 3 reports the test as failed (G3 R2) and the human decides; the code argument of 4.4 stands on its own |
| R19 | **(r3)** macOS behaviour: whether an `/etc/fstab` `noauto` entry stops automount of this stick, and whether a read-only mount writes nothing (UNVERIFIED) | the stick's state after the run | Rehearsed on the operator's Mac before the run (RUNBOOK A0); fallback: unmount at once and image (RUNBOOK E) |
| R20 | Packaging: pspboot must load the larger image (limit unknown; growth ≤ 49,152 B each; **§17 R-5**: +43,631 B `vmlinux.bin`, +36,919 B `vmlinux-0.22.bin` at G2 attempt 1); Stage 2 must point `.config:163` at the work copy's cpio (recon/build.md §1.3) | boot, collector present | G2 C6 sizes; Stage 3 unpacks the embedded cpio and checks `pscol` and the `rc.sysinit` lines; a failure shows at the self-test |
| R21 | The PSP-1001 POWER/HOLD slider direction (up power, down HOLD) is hardware knowledge | runbook D7, C0 | RUNBOOK states it and says to stop and ask if the unit is marked differently; accidental power-off before death is an abort |
| R22 | **(r3, N-4)** That a reply's `rx[2]` names the command it answers rests on an author comment (`syscon.h:55-58`), UNVERIFIED | H6, N2b | Rules compare with the template's per-command `rx[2]`; the literal value only without a template, flagged `rx2 literal`; Stage 3 tests a healthy `rx[2]` other than 0x08 |
| R23 | **(r4, A4-2)** The read-back page is dropped by `fadvise64_64` through `syscall()` in the o32 seven-slot layout because uClibc's `posix_fadvise` marshals five (section 14); the call is never used by any other program on this system | whether the read-back reaches the stick | The worker checks the return (0) and that `ms_seg_rd` rose; a cached read-back is only an EVENT; G2 checks the call in objdump; VFAT-FI runs the same `mm/fadvise.c` |
| R24 | **(r4)** META can flag a metadata sector that refuses ≥ 5 writes and later recovers; the S b7 tag reads `page->mapping` of a page under I/O | the operator's notes | **(r5)** META is informational: the run counts, D8 decides on `DUR`; the flag clears on a later good write or when bypassed (4.7); a mis-tagged page would show as a META on a data sector (class reported), never as a lost record; Stage 3 VFAT-FI |
| R25 | **(r5)** The S-record verdicts rest on the published geometry, the partition offset (`ms_psp.c:250`), `FIBMAP` (`fs/ioctl.c:60-76`) and the S hook seeing every transfer | every durability verdict | The geometry self-check at STICK (4.8) compares FIBMAP + geometry with the first step's own S records, so an error is an abort, not a misjudged run; a window with a skipped `seq` is FAILED (conservative, costs a re-send); Stage 3 verdict vectors (8.5) and VFAT-FI |
| R26 | **(r5)** Aliases: the test depends on `fstat` showing the cached inode's size and number (`fs/fat/inode.c:276-295`, `:412`); a takeover instance has not seen its predecessor's numbers | A5-1 | Size-0 aliases have no chain and are safe to write (4.4 step 1); written aliases show `st_size ≠ 0`; ≤ 24 `open`s per tick and a names budget from the free slots bound the cost; a long outage costs one name per 10 s; Stage 3 schedules (8.5) |
| R27 | **(r5)** Console log level 4 hides level-4 messages from the screen for the whole run | photographs of kernel messages | Every message is still in the log and the KMSG chunks; `KERN_ERR` and more serious still draw (7.1) |
| R28 | **(r5)** The boot nonce is derived from tick and Count sums, so two boots could collide (probability ≈ 2^-32 per pair, UNVERIFIED distribution) | run separation in the decoder | The decoder also selects by FILEHDR `run` and checks timeline continuity; a collision would show as `(ring, seq)` conflicts, which are reported, never dropped (10.2) |

### 11.2 Judgement calls, with the alternative not taken

| # | Decision | Alternative | Why |
|---|---|---|---|
| J1 | Zero added instructions in S5..S20 | in-window phase bytes (candidate B) | H4 is a timing hazard inside that window; W and `lc` give the step at no cost there |
| J2 | `localTick` timestamps; `seq` invalidate-publish; sector-aligned CRC flushes; per-segment S records | a new tick counter; check words; unpadded appends; per-sector records | same ordering with no added instructions; one writer per ring; a pull damages only the flush in progress; timing and pid at a third of the volume |
| J3 | **(r3)** One uncapped `lc` snapshot per command; I ring cut | per-tick samples | `lc` is the exact suspension point (TE2); samples added volume, no closure (K10) |
| J4 | Collector cadence like telem (fsync every ≈ 0.23 s, 272 row writes) | a 1 Hz flush | the 9.6 deaths occurred under telem's load; halves the loss bound |
| J5 | Kernel panel painted from the timer interrupt | a band drawn by the supervisor | a task stops with every other task in the A1 OE1 hang |
| J6 | The writer reports the durable point; the kernel compares and shows it | the kernel infers it | only the writer knows; a stalled writer cannot misreport by freezing |
| J7 | Takeover after 30 s without durable progress and reads; no `statfs` | a shorter threshold; keep `statfs` | a slow `fsync` or catch-up must not trigger it; `statfs` scans the whole FAT (4.4) |
| J8 | **(r3)** Preallocated fixed-size segments (red-team fix 1a) | 1b: abandon a segment after any failed `fsync` | 1a removes FAT writes from steady state; 1b still extends files and creates a segment per burst |
| J9 | Memory Stick driver waits left unbounded (R12) | bound them | a bound changes the H10 actor's timing on every sector and adds an untested error path |
| J10 | **(r4)** 2 MB files grown in confirmed steps, usable as they grow, two ahead; **(r5)** verdicts from S records with FIBMAP extents (A4 F1(b), adopted at full scope) | preallocate the whole run; one all-or-nothing spare (r3); verdicts from the `fsync` return (r4) | whole-run preallocation delays the first record; r3 lost data under sporadic errors (A4 IF4); `fsync` fails whenever any shared metadata sector fails, which froze durability under IF7 (section 15) |
| J14 | **(r5)** Alias test after `open`, `fsync` of the alias, same-tick retry (4.4 step 1) | pre-create every entry at start; give each file its own directory | pre-created entries fail the same way if their batch write fails and then a later `fsync` writes a size into a nameless slot; a directory per file allocates a directory cluster per file (a FAT write outside the step protocol) |
| J15 | **(r5)** META informational; the run counts | "not counted" at D8 (r4, under A1) | at full scope META cases keep recording durably (4.7, 15.3); discarding them would throw away good runs (A5-2) |
| J11 | **(r3)** Shallow read-back; the file stays open | reopen and walk the chain | the walk would call `fat_fs_panic` over a silently lost FAT write (4.4) |
| J12 | **(r3)** Supervisor becomes the worker; HUD of ten lines in rows 0-175 | a standby; a full-screen HUD sparing the panel rows | same allocation-free recovery with one process less; the kernel owns the band outright, load parity kept |
| J13 | Post-death script without L + R, SELECT tap last (D7a); C0 right after the self-test; 30-minute limit; launch after `pspmd`; record `pdflush` | B's variants | L + R summons the OSK; same script healthy and dead; S3 needs ≥ 15 min; baseline start order; a second 5 s cadence |

### 11.3 Risks of revision 2 removed or merged

| r2 risk | Disposition |
|---|---|
| R11 I-record rate | **Eliminated**: I ring cut (K10) |
| R13 `get_wchan` without KALLSYMS | **Eliminated**: `jp_wchan` cut; H9 rests on stage codes and `qfree_stage` |
| R14 M ring and P-counters with several writers | **Accepted**: informational, never compared for equality; torn M slots rejected by `seq` (3.4) |
| R17 console blanking at ≈ 600 s | **Accepted**: `pspfb` has no `fb_blank` (`drivers/video/pspfb.c:64-76`), so a blank is a one-off clear the HUD repaints; N4 records the path |
| R18 conditions of the 9.6 deaths inferred | **Accepted**: answered by the operator before the run (RUNBOOK "Before you start") |
| R19 H6 analog jitter | **Eliminated**: H6 rests on the script buttons and the template |
| R23 `pdflush` phase | **Accepted**: measured (K23) |
| R24 recon/image2008 V10 | **Accepted**: does not affect this run (7.6) |
| R25 HUD readability | **Eliminated** by the N-2 render test (8.5) |
| R28 a new standby needs a 128 KB allocation | **Eliminated**: no allocation after boot (U1) |
| R29 HUD blit source cache-resident | **Accepted**: stated in 7.4; syscall count and bytes equal telem's |
| R36 retry in place on bad clusters | **Merged into R8.** (r3: switch to the spare after three failures; dropped in r4; **(r5)** back as the bad-region escape, limited to local data failures, 4.6) |
| R3 + R6; R5 + R8; R20 + R31; R21 + R22; R34 + R35 | **Merged** into new R3, R6, R10, R20, R17 |
| R1, R2, R4, R7, R9, R10, R12, R15, R16, R26, R27, R30, R32, R33 | kept as new R1, R2, R4, R5, R7, R8, R9, R15, R14, R12, R13, R19, R21, R16 |

---
## 12. Provenance

Candidate A (minimal perturbation) gave the zero-in-window captures and G2
criteria, the W record with the interrupted context, the explicit watchdog
flag, the `seq` protocol, sector-aligned CRC flushes, the self-test with its
early-death exception and trigger/state/flags reporting. Candidate B (maximum
coverage) gave the tick-equals-watchdog timestamps, tick-length accounting,
POLL records, stage codes and the H9 signature, upper-layer counters,
per-segment Memory Stick records, the `pdflush` hook and the telem cadence.
Revisions 1-3 added what the gates asked (DESIGN-history.md; sections 0 and
13). The candidates' factual disagreements, settled against the source in
revision 1, still hold: FSINFO on every `fsync` (B; `fs/sync.c:67-68`); the Nop
at exactly tick 1250·k (B; `psp.c:372-379`); a 48-byte `Syscon_cmd` frame with
`dmy` at `sp+0`, `spin` at `sp+4` (A, [OBJ]); C4 precedes the joypad thread
(A; `drivers/Makefile:28`, `:59`); `0xbe240004` bit 4 unproven (supporting
evidence only).

---
## 13. Response to G1 attempt 3 and the round-4 brief

Reports answered: `gates/G1-attempt3-review.md` (PASS, advisory N-1..N-5) and
`gates/G1-attempt3-redteam.md` (FAIL: IF1, IF4, IF5 BLIND; IF6, UL5
AMBIGUOUS; recommendations under TE5 and OE6). Findings are closed only by
the reviewers; this is the designer's response. Responses to attempts 1 and 2
are in DESIGN-history.md.

### 13.1 Findings and scenarios

| Item | Response | Where |
|---|---|---|
| **N-1** B4 gated TRIANGLE on POLL green, so the `POLL:RATE`-only escape was unreachable | **FIXED as the review asked.** (1) TRIANGLE is held when KRN, WDOG, STICK, REC, PANEL and SUP are green, whatever POLL shows, up to three holds; (2) the never-press SELECT row lists the abort-rule tap; (3) RUNBOOK tells the G3 R4 read-through to walk the `POLL:RATE`-only branch | 8.3; RUNBOOK B4, abort rule, never-press table, header note |
| **N-2** line 1 could not hold the check names | **FIXED.** Ten lines, every one ≤ 35 characters, exact strings tabulated; the check names split over lines 2 and 3 (18 and ≤ 23 characters); rows 176-271 not written; Stage 3 host render test asserting nothing reaches x ≥ 428 in rows 8-39 or rows ≥ 168 | 8.2, 8.5; RUNBOOK "The PSC display" |
| **N-3** `IN` and `DELIV` undefined | **FIXED as suggested.** `IN` = UHB `mouse_press_total` (the collector's own mousedev press edges; mouse mode only); `DELIV` = seconds since the last POLL with `push_ok > 0` or `mouse_flags` b3. RUNBOOK C5 says `IN` counts only in mouse mode | 8.2; RUNBOOK C5 |
| **N-4** H6/N2b used the literal `rx[2]` = 0x08 from an author comment | **FIXED.** H6 and N2b compare `rx[2]` with the template's per-command value; the literal only without a template, flagged `rx2 literal`; marked UNVERIFIED as R22; Stage 3 adds a stale-frame sequence whose healthy `rx[2]` is not 0x08 | 6 (H6), 6.1 (N2b), 10.7 step 2, 11.1 R22, 8.5 |
| **N-5** PANEL "proves" the write-back | **FIXED.** The pixel read-back is cut (it only proved the routine ran); 8.2 says what PANEL proves; not seeing the `PSC TEST` band is an abort item, and a second 5 s test is shown right after BTN turns green, when the operator is looking | 8.2, 8.3, section 0 U10; RUNBOOK B3, B4, abort rule |
| **IF5** (BLIND) a failed `fsync` on a flush that allocated a cluster orphans "durable" records and drives vfat read-only | **FIXED by red-team fix 1a plus fixes 2-4.** (1a) Segments are preallocated at a fixed 2 MB: PAD sectors written and `fsync`ed step by step, `fstat` size check, read-back of the last sector after `drop_caches`; the next segment is created ahead of need; any creation error abandons the file, which is never written, extended, truncated, unlinked or reopened. A segment in use is written only below `mmu_private`, so a flush never allocates or dirties a FAT sector (`fs/fat/inode.c:68-72`, `fs/buffer.c:2111-2113`, `fs/fat/cache.c:312-315`, all checked in this tree); retry in place is then safe (4.6). (2) `fat_fs_panic` counter and `MS_RDONLY` bit in the stats (hooks at `fs/fat/misc.c:18`, `fs/fat/inode.c:1415`), panel title `PSC MS RO`, runbook: from then on the panel photographs are the only record. (3) RUNBOOK E: the stick is always mounted read-only (automount blocked and rehearsed in A0), the raw image is mandatory after any error, abandon, read-only, panel or short copy, and the old claim (RUNBOOK r2 lines 343-347) is replaced by a correct one; the decoder makes `--raw` the primary path when such evidence exists. (4) Stage 3 VFAT-FI runs this tree's own `fs/fat` (identical to vanilla 2.6.22) on a Malta build with a fault-injecting block device | 4.4, 4.6, 2.12, 2.10, 1.7 words 133-135, 10.2, 8.5, R11, R18, R19; RUNBOOK A0, C4, E |
| **IF1** (BLIND under IF5) transient failure spanning onset | **FIXED via IF5.** The failed flush is rewritten at the same offset in a segment that does not allocate; records are re-sent from `durable_next`; a creation step caught by the outage is abandoned and redone; nothing becomes read-only | 4.4, 4.6 |
| **IF4** (BLIND) 25-35 s burst or ≈ 98 sporadic failures | **FIXED via IF5.** No failure consumes FAT links, file space, records or names (creation attempts ≥ 10 s apart, 999 names per run, cap 32 segments); the "burst shorter than the ring span loses nothing" statement now holds; Stage 3 runs these schedules against this tree's vfat | 4.6, 8.5 |
| **IF6** (AMBIGUOUS) a corrupt slot or a forward head jump stalled a ring with no alarm | **FIXED as asked.** Skip and count: a slot whose `seq` is wrong and not explained by a lap is skipped, `slot_bad[ring]` counted, `f_pos` advanced; a complete drain means every ring's position reached the head read at the drain's start; a short read below the head is `drain_stuck`, an EVENT and the HUD `REC ... STUCK` line in red; `lost`/`slot_bad` after the first drain also turn REC red; Stage 3 tests both corruptions | 3.5, 4.3 step 2, 1.7 words 128-132, 8.2 line 8, 10.2 (UHB word 19), 8.5 |
| **UL5** (AMBIGUOUS) a clean LED read-back during a mid-window suspension printed "H10 refuted" | **FIXED as asked.** (1) The wording is now "H10 write-back mechanism refuted: the set/clear registers did not read back the transaction's lines", never printed when the onset command had `ms_delta > 0` during a suspension in S5..S20; (2) new row N1m with the suspension bound and LED count, "cannot be separated in this run"; (3) the with/without-LED harm-rate comparison is pre-registered with a fixed decision rule; (4) Stage 3 sequence | 10.7 steps 5 and 7, 6.1 N1m, 8.5 |
| **TE5** recommendation (Nop between an LED load and store) | **FIXED as recommended.** EPC label `LEDRMW`, row LEDSPLIT reporting the loaded value and the G3 transition, Stage 3 vector | 10.6, 6.1, 8.5 |
| **OE6** recommendation (panel paints for minutes) | **FIXED, adapted.** The recommended I-record flag has no home after the I ring's cut, so each SC record carries `lc_flags` b5 "a panel paint ran while this command was in flight", with `panel_cost_last` per paint; row N1p replaces the 1-second proximity flag | 1.2, 1.7 word 148, 2.10, 6.1 N1p |
| **(e)** phase of a death against the 1250-tick cycle | **FIXED**: 6.3 states that the last successful command, the first failed one and the nearest Nop are each placed before, across or after tick 1250k at Count resolution; the decoder prints the placements per onset candidate | 6.3, 10.7 step 4 |
| Attempt-3 review: budget and format strings | **Re-run** for revision 3 (5; 10.3 strings and offsets checked with `struct.calcsize`) | 5, 10.3 |

### 13.2 The cut (brief, part 2)

Every mechanism is in section 0 with what it is for, its cost and the
decision. The brief's named candidates: **standby worker** CUT, replaced by the
supervisor running the worker loop (U2, J12); **128-byte stack snapshots** CUT
(K15); **uncapped overwrite words** KEPT, the cheapest exact closure of TE2 and
TE4 (K8); **scheduler hooks** KEPT and simplified, the OE3 closure (K12); **the
stats histograms** replaced by 21 outcome counters in a 768-byte block (K22);
**record types** down to four formats in five rings (I ring cut, K10; SELFTEST
chunk cut, U11); **9,999-name space** replaced by 999 names per run that cannot
run out (U7); **full-screen HUD** reduced to ten short lines, load parity kept
(U9); **decoder features** without a matrix row cut (X11). Also cut: T2c
(K11), per-bit LED counts (K7), W copies (K16), mousedev open/release counters
(K24), the out-of-bounds checksum recompute (K33), the volume cap (U8), the
PANEL read-back (U10). DESIGN.md up to the end of section 12 (title,
summary, sections 0-12) is 1,795 lines (revision 2: 3,006 including
responses); open risks went from 36 to 22 (11.3).

### 13.3 Attempt-3 DIAGNOSABLE scenarios, re-checked against the cuts

| Scenario | Still closed by |
|---|---|
| UL1 (bit-4 write-back) | `led_or`, S `rd_*_or`, row H10 at S5..S20 (K6, K19) |
| UL2, UL3, UL4 | N10; N2b with the template `rx[2]`; N11 |
| TE1 (death at 5, 17, 36 s) | rings from boot, `durable_next` = 0 keeps WB, template fallback with the WB/M/WT baseline; the first segment's creation (7-40 s) keeps the first drain inside the ring span except on a stick slower than ≈ 30 KB/s (6.2, R8) |
| TE2, TE4 | `lc` words and the nested-tick rule (K8, K9); no longer depends on the I cap, which is gone |
| TE3 (minute 14 in `fsync`, 29:50, link wrap, blank) | unchanged: the D8 check, 16-bit links with nearest-value expansion, W span 1,280 s; R17 of r2 accepted (11.3) |
| IF2 (worker killed) | the supervisor runs the worker loop with its boot-time block, creates a fresh segment at 64 KB per tick, seeks to `durable_next` (U1) |
| IF3 (reader races) | `seq` protocol, `head_regress`, and now skip-and-count (3.5) |
| OE1 (MS driver hang) | marker and kernel panel (K20, K30) |
| OE2 (`statfs` FAT scan) | no `statfs` (4.4) |
| OE3 (load sets the exposure) | the simplified hooks: per wait, delay, the collector's exact part, wake-up and last-holder classes (K12) |
| OE4 (kernel-privileged `pscol`) | `pscol` and kernel guards, fuzzing, `instrumentation-suspect` (K26, U18) |
| OE5 (mousedev client freed mid-walk) | rated DIAGNOSABLE without the counters; `do_exit` hook kept (K25); collector exits are EVENTs or takeovers |

---
## 14. Response to G1 attempt 4 (round 5)

Reports answered: `gates/G1-attempt4-review.md` (PASS, advisories A4-1..A4-6)
and `gates/G1-attempt4-redteam.md` (FAIL: IF4, IF7, IF8 BLIND; A1-OE3, TE6
AMBIGUOUS; fixes F1-F6), under WORKFLOW Amendment A1 (persistent refusal of one
metadata sector is SPOILED-DETECTED if detected, displayed and handled, and no
data already on the stick is destroyed). Only the mechanisms of the round-5
brief were added. Findings are closed only by the reviewers. DESIGN.md through
section 12: **1,920 lines** (1,795 + 125). **(r5, A5-4)** The "+ 150 allowance"
cited here in r4 is not in `gates/LOG.md`; the line count is the orchestrator's
to record.

### 14.1 Red-team fixes (attempt-4 red team section 6)

| Item | Response | Where |
|---|---|---|
| **F2** incremental creation | **FIXED.** (a) A file grows in steps of 64 KB (while the active file is not complete, or holding) or 8 KB; a step allocates iff it writes a block at offset 0 of a cluster (`fs/fat/inode.c:82-85`, `cl` = `st_blksize`, `fs/fat/file.c:310`); a failed non-allocating step is retried in place (≤ 3; its blocks are already mapped, `:93`), a failed allocating step (or a fourth failure) stops growth. (b) Flushes use any file's `fsync`-confirmed prefix (`seg_end + 40,960 ≤ conf`), so the first durable flush comes one 64 KB step after the FILEHDR (≈ 1-3 s at 300-25 KB/s). (c) A stopped file with `conf ≥ 42,496` is prefix-usable. Envelope kept: every flush ends at or below `conf ≤ mmu_private`, so `cont_prepare_write` extends nothing (`fs/buffer.c:2111-2126`) and `__fat_get_block` returns before the allocation branch (`fs/fat/inode.c:68-72`, `fs/fat/cache.c:312-315`) | 4.4 steps 3-5, "Use and switch", "Why a flush never allocates"; 6.2 |
| **F3** cap and margin | **FIXED.** The cap counts only complete or prefix-usable files, by confirmed bytes (64 MB); creation runs while fewer than two complete files are ahead (one ready, one in creation, ≈ 9 minutes of margin); abandoned space is budgeted: 64 MB + 999 names × ≤ 128 KB ≈ 189 MB, RUNBOOK A3 now requires 256 MB | 4.4 preamble and step 8; 9; RUNBOOK A3 |
| **F5** preemption holder | **FIXED as specified.** Hook S branch `prev == psc_jp_task && prev->state == TASK_RUNNING` (plus `psc_t_busy_p`), publishing `pre_wrk` (42), `pre_cls` = preemptor and last holder (44), `pre_flags` (46), `pre_tot` (78) into the SC record's reserved bytes; one more compare per switch. N1, N1m, H10 and the no-death inference print the holder and the collector's share | 2.11, 1.2, 1.7 word 152, 5.4, 6, 6.1, 7.1, 10.3, 10.7 steps 5 and 8, 8.5 |
| **F1 (a)+(c)** | **FIXED.** `seg_end` advances past every region handed to `write()` whatever the result, so **nothing written is ever overwritten**; `durable_*` stay frozen; the records of failed flushes are re-sent once, by one seek back to `durable_next` at the first successful flush. "Once" is per recovery: a re-send that fails is re-sent after the next success, which keeps transient bursts (in scope) lossless, while under a persistent refusal nothing succeeds and every record is written exactly once instead of the same oldest records being rewritten every tick (the IF7 mechanism). (c) is `MS META` (4.7). **F1 (b) not adopted** in r4: under A1 the persistent class needs detection, not durability. **(r5) Adopted at full scope** (4.8, section 15) | 4.3 step 7, 4.6, 4.7; J10 |
| **A1 detection** | **FIXED.** The kernel tags each S record `flags` b7 when the transferred page lives in the block device's page cache (FAT, FSINFO, directory: `sb_bread` buffers, `fs/buffer.c:984`, `fs/block_dev.c:573`), else file data. The worker reads the S records it drains anyway (`sector` @16, `pid` @22, `flags` @25) and declares META when one metadata sector's last 5 writes failed over ≥ 3 ticks while the worker's data writes in those ticks succeeded: ≈ 1-2 s for FSINFO or the directory sector, ≈ 5 ticks for the allocator's FAT sector. Display: HUD line 6 `MS META ERR <sector>` red, kernel panel `PSC MS META` (via `ctl` op 4). Runbook: raw image mandatory, run not counted if still shown at D8. No data on the stick is destroyed (F1a) | 2.4, 1.5, 1.7 words 150-151, 2.8, 2.10, 4.7, 8.2, 10.2; RUNBOOK C4, D8, E2 |
| **F4** (cheap part) | **FIXED.** After an abandon whose failing write was a metadata write (b7) while its data writes succeeded, the next attempt starts at the next tick (≤ 256 such per run); other abandons wait ≥ 10 s. IF8's ≤ 128 one-cluster attempts then take ≈ 30 s instead of ≈ 21 min. No other sector classification | 4.4 step 6 |
| **F6** Stage 3 | **FIXED.** Error tests at modelled 25, 52, 100, 300 KB/s on the flush and creation paths; VFAT-FI schedules for a persistently refusing FSINFO, directory and allocator FAT sector with the pass condition "detected within 30 s, displayed, no already-written record destroyed" (checked from the fault driver's write log) | 8.5 |

### 14.2 Review advisories (attempt-4 review section 7, "What would close it")

| # | Response | Where |
|---|---|---|
| A4-1 | **FIXED.** New 5.1 row for creation S records (≤ 11.5 per 8 KB step, ≤ 27 per 64 KB step; run average of all S 34.2/s); 3.1 spans from per-buffer counts (≥ 53 s, ≥ 29 s); creation physical writes 8.8 KB/s at r4 rates (8.24 KB/s at r3's 294 s life, the review's 8.25); average 40.7 sector writes/s = 20.8 KB/s (R8); Stage 3 volume test with per-stream tolerances, creation minutes included | 5.1, 5.2, 3.1, R7, R8, 8.5 |
| A4-2 | **FIXED by replacement.** uClibc exposes `posix_fadvise` (`staging_dir/usr/include/fcntl.h:184`; `libc.a` member `posix_fadvise.os`, symbol T) but its code is `sra a2,a1,31; sw advice,16(sp); li v0,4254; syscall`, i.e. (fd, off, off>>31, len, advice), while this kernel's 4254 is `sys_fadvise64_64` with **seven** slots (`arch/mips/kernel/scall32-o32.S:599`: fd, pad, 64-bit offset in a2:a3, 64-bit length at 16-20(sp), advice at 24(sp)), so it would misread offset, length and advice. `syscall()` (`libc.a(syscall.os)`) moves a1-a3 down and copies 20-28(sp) to 16-24(sp), passing seven slots unchanged. The worker therefore calls `syscall(4254, fd, 0, SEG − 4096, 0, 4096, 0, 4)`: one page of one file, no `inode_lock` (`mm/fadvise.c:98-108`). `drop_caches` is gone, so nothing unbounded remains to list in 7.1, 7.4 or 11; the call is in 7.4 and R23 | 4.4 step 7, 7.4, R23 |
| A4-3 | **FIXED.** The raw image is required for a RECS-holding file that is not 2 MB (a file being created holds none **unless it was also the active file; (r5, A5 TE7) the r4 wording was too wide**); RUNBOOK E1 step 5 says one smaller file is normal; Stage 3 decoder case | 10.2, 8.5; RUNBOOK E1, E2 |
| A4-4 | **FIXED.** Line 6 shows `MS PREP nnnS`, not red, until the first durable flush; B3 says it is normal; `MS NO STICK` counts only at 3:00; E2's line-6/line-7/panel triggers apply only after `SELFTEST PASS` | 8.2, 8.3; RUNBOOK B3, abort rule, E2 |
| A4-5 | **FIXED.** The early-death exception wins over "PSC TEST never seen" (write it down, go to D); the second test is requested when the six checks first turn green, independent of BTN, and B4 tells the operator to watch the band then | 8.2, 8.3; RUNBOOK B3, B4 |
| A4-6 | **FIXED.** (a) K1 says ≈ 130. (b) RUNBOOK examples use the fixed widths. (c) B3 says `PSC Trrr---` (run number, 001 unless rehearsal files exist). (d) 6.2 and R8 mark the collector start UNVERIFIED; the first UHB's `uptime_cs` (written in the flush of the first drain) records it. (e) RUNBOOK mentions a possible text cursor in the band. (f) 1,920 lines through section 12, inside the round-5 allowance | 0, 6.2, R8; RUNBOOK |

### 14.3 Non-blocking red-team notes adopted

IF1: EVENT and KMSG payloads are re-sent until a flush carrying them succeeds
(4.6). IF3: a `head_regress` rise seeks that ring to its head, writes an EVENT
and turns REC red (4.3 step 2). IF6: a 16-bit link that expands onto a missing
`seq` is paired by `(tick, Count)` (10.3). OE5: an N5 stop between a takeover
and the next PROCS is annotated (10.7 step 5). UL6: row WB, the ± 2-cycle WT
listing and the "both results valid" benign rule (6.1, 10.7, 8.5). OE7: A4-2.

### 14.4 The attempt-4 scenarios, traced by the designer (the red team rules)

| Scenario | Trace under revision 4 |
|---|---|
| IF4 sporadic (≈ 98 failing ticks per 30 min, 25-300 KB/s) | A failed flush costs ≤ 40 KB of space and its records return after the next success. A failed creation step is retried in place unless it allocates; an allocating failure stops growth, but the prefix already takes flushes and the next file starts (≥ 10 s later). Holds need both files ahead and every prefix to fill, ≈ 9 minutes of failures. This is the red team's "prefix-usable + in-place" variant (0 s lost at 25-100 KB/s in its Appendix A), plus a second file ahead. **(r5)** The A5 red team showed r4's re-send rule lost records at 25 KB/s; r5 re-sends by range and gates at 30 KB/s (15.2) |
| TE6 early death, slow stick | The first flush follows one 64 KB step (≈ 3 s at 25 KB/s); the rings hold 114.7 s |
| IF7 persistent FSINFO or `PSCLOG` directory sector | Every `fsync` fails; nothing is overwritten (F1a) and nothing re-sent; every flush writes its records once onto working data sectors; META within ≈ 1-2 s; panel and HUD show it; the runbook makes the raw image mandatory. When the files ahead are full the worker holds (SPOILED-DETECTED under A1); no record that reached the stick is destroyed. **(r5)** At full scope recording continues (15.3) |
| IF8 persistent FAT sector at the allocator | Flushes are unaffected (they never allocate; the failed FAT buffer is clean and not up to date, so a flush `fsync` does not rewrite it). Abandons are metadata-caused, so attempts follow at one per tick; META within ≈ 5 ticks (displayed); after ≤ 128 attempts (≈ 30 s) the allocator leaves the sector and creation succeeds; meanwhile two files ahead cover ≈ 9 minutes. **(r5)** META now clears when bypassed and the run counts (15.3) |
| A1-OE3 | An N1 onset now carries the preemptor's class, the last holder's class, the total preempted time and the collector's part of it |
| IF1, IF5 (re-checked) | IF1: a burst writes each flush to fresh space and re-sends after it ends; lossless below 114.7 s (**(r5)** corrected to ≤ 90-100 s by simulation, 4.6). IF5: flushes still never allocate; a creation that allocated and failed leaves an in-memory cluster beyond `conf` that no flush ever writes. **(r5, A5-1) Restated:** the worker never writes it, and the kernel's reuse of that inode through a freed directory slot is rejected by the alias test before any write (4.4 steps 1, 5) |

### 14.5 Budget (script, section 5) and remaining weak point

Run average 7.6 KB/s on the stick (7.1 steady, 9.35 in creation ticks); 6.8 /
13.7 / 16.0 MB for 15 / 30 / 35 minutes; 12 / 18 / 20 MB of stick space with
two files ahead; physical writes 20.8 KB/s, LED operations ≈ 81/s (≈ 3.1×
telem); kernel memory unchanged (≈ 653 KB; three stats words, no new ring). Every
10.3 string recomputed with `struct.calcsize` (SC 80, W 288, POLL 40, S 40,
STATS 768, UHB 80, CTL 32, FILEHDR 40, chunk 20, block 8); the new SC fields sit
at 42 (H), 44 (B), 46 (B), 78 (H), where the string already had those types.
**Weakest point:** META detection and the file logic rest on this tree's
vfat ordering (data pages, then the directory entry, then FSINFO and FAT in
`sync_blockdev`) and on the Memory Stick's real failure behaviour, both of
which only the VFAT-FI harness (R18, feasibility UNVERIFIED) can exercise
before the run.

---
## 15. Response to G1 attempt 5 (round 6)

Reports answered: `gates/G1-attempt5-review.md` (FAIL: A5-1 blocking under D6;
advisories A5-2, A5-3, A5-4) and `gates/G1-attempt5-redteam.md` (FAIL: IF9
BLIND; IF4 and IF10 AMBIGUOUS; IF7a, IF7b, IF8 SPOILED-DETECTED under A1;
notes OE8, UL7, IF5 residual, TE7). **Scope (gates/LOG.md, note of
2026-10-05):** round 6 is the human's pre-authorised fallback at **full scope**:
Amendment A1 is suspended, so the persistent-metadata-sector class (IF7a, IF7b,
IF8) must be DIAGNOSABLE, not only detected, and every red-team fix still
outstanding from attempts 4 and 5 is adopted, including attempt-4 F1(b) and the
full F4. The no-new-mechanism discipline holds otherwise: every new mechanism
is a section 0 row with its cost (K37, U21-U25, RB6; 15.7). Findings are closed
only by the reviewers; this is the designer's response. Kernel paths are
relative to `/home/ubuntu/psp/build/linux`; every new source claim was read in
this tree.

**In plain words.** Revision 4 trusted the answer of `fsync`, which says "some
write failed" without saying which. Any one bad bookkeeping sector of the stick
then made every save look failed, and a failed first save of a new file could
leave a half-made file that the kernel later handed back under a new name.
Revision 5 reads the stick's own per-sector answers, which the kernel already
records (the S records), and knows from the file system's layout which answer
belongs to data, to the file table or to a directory. Saved data counts as
saved when its own sectors were written, whatever else failed; a new file
counts as grown when its data and its file-table links were written; and a
file the kernel hands back by mistake is recognised by its size and inode
number and never written.

### 15.1 Reviewer findings (attempt-5 review section 10)

| # | Response | Where |
|---|---|---|
| **A5-1** (blocking, D6) inode reuse after a failed step-0 `fsync` leads to `fat_fs_panic` | **FIXED, all four parts.** (1) After every `open(O_CREAT\|O_EXCL)` the worker requires `st_size == 0` and an `st_ino` it has not seen; otherwise EVENT `inode reused <name> <ino>`, UHB b28, nothing is ever written through it. **Why the next attempt gets a fresh slot, from the source:** the alias's own entry (its name, start 0, size 0) is in the up-to-date directory buffer (`fs/fat/dir.c:1255-1256`, `:1266-1267`), so the next `open` in the same tick finds that slot occupied (`IS_FREE`, `fs/fat/dir.c:1212`, `msdos_fs.h:47`) and takes a later one; a later slot has a cached inode only if its entry was lost too, which the same test catches (≤ 24 `open`s per tick). This same-tick loop runs while the stick is working (the latest S window shows a successful write). During an outage the first alias is a probe: its descriptor is `fsync`ed once, which writes only that directory sector and FSINFO, because the cached inode is clean (its own failed `fsync` cleared `I_DIRTY` before writing, `fs/fs-writeback.c:163-166`; `vfat_create` does not dirty it, `fs/vfat/namei.c:756-758`) and has no dirty pages (failed pages are not re-dirtied); if nothing in that window succeeded the attempt ends and the next waits ≥ 10 s, so an outage costs one name per attempt and leaves at most one free-on-disk slot. Takeover instance: size-0 aliases have `i_start = 0`, no chain (`fs/fat/misc.c:88-96`), and are safe. Also: a failed step 0 is never retried in place (4.4 step 4), and step 0 needs its directory write. (2) 4.4 step 5, 4.6 and 14.4 restated: "no FAT walk ever reaches an unconfirmed link", with the kernel's reuse named as the one path the worker does not control and the alias test as its closure. (3) VFAT-FI schedules added: every write fails for exactly the step-0 `fsync` tick then recovers; a 30 s burst starting during an 8 KB creation; also a 10-minute burst during a hold. Pass: no "Filesystem panic", no alias written, the next fresh file in the first tick after recovery, names ≤ 1 + outage/10 s. (4) 2.12 and 4.6 corrected: read-only stops new names (`fs/namei.c:237-239`) but not writes into open files (`fs/inode.c:1227`; `fs/fat/inode.c:556-611`, `:453-459`); the worker then makes no creation step, flushes into the files already prepared, then holds | 4.4 steps 1, 4, 5; 4.6; 2.12; 8.5; 14.4; 10.2 (UHB b28, EVENT) |
| **A5-2** META latched discards a fully recorded run | **FIXED, both ways.** At full scope META no longer means the run is spoiled: recording stays durable (4.7, 15.3), so "not counted" is gone; D8 decides on `DUR` as for any run, and META no longer paints the panel (which would fail every D8). META also clears when **bypassed** (no write of the sector for 60 s while every flush was DURABLE, or for a FAT sector a later allocating step confirmed outside it; EVENT `meta bypassed`). RUNBOOK C4, D8, E5 updated | 4.7, 2.10; RUNBOOK C4, D8, E5 |
| **A5-3** STICK waits for the first complete drain, ≈ 1-2.6 min at 20-52 KB/s | **FIXED, both parts asked.** (a) Computed: the model of 15.6 gives the time to the first complete drain at 20-300 KB/s for worker starts at 20 s and 40 s of uptime (table in 15.6; my model reproduces the reviewer's r4 figure at 25 KB/s, 124 s against 120-123 s). (b) Start-up steps are small while catching up: **64 KB only while the active file's room is below 81,920 bytes, or while holding** (the reviewer's suggestion), which brings the first complete drain to 3-6 s at 300 KB/s, 9-17 s at 52 KB/s, 18-35 s at 30 KB/s and 26-48 s at 25 KB/s. A stick below the new 30 KB/s gate fails STICK as `MS SLOW` (an abort, no run lost), so at 3:00 PANEL and BTN have ≥ 80 s of margin. 8.3 and 6.2 corrected | 4.4 step 3, 6.2, 8.2, 8.3, 15.6 |
| **A5-4** (1) six r4 mechanisms without section 0 rows | **FIXED.** `head_regress` resync: U3 and K27; WB and the benign rule: X4; 16-bit link fallback: X1; OE5 annotation: X4; `MS PREP`: U9; second `PSC TEST`: U19 | 0 |
| A5-4 (2) U7, U8 stale figures | **FIXED** with r5's figures (fast attempts ≤ min(400, budget/2), names budget ≥ 400; 64 MB of confirmed bytes) | 0 (U7, U8) |
| A5-4 (3) 4.4 "two complete ahead" against "one ready, one in creation" | **FIXED.** The rule is "while fewer than two complete files wait ahead"; the parenthesis is replaced by the steady state it produces | 4.4 |
| A5-4 (4) no delay after a stop in 4.4; 14.4 says ≥ 10 s | **FIXED.** One rule for stops and abandons (4.4 step 6): next tick if the failed window shows a successful write (≤ min(400, budget/2) per run), else ≥ 10 s | 4.4 step 6 |
| A5-4 (5) K35 "bytes 42-46" | **FIXED**: 42-43, 44, 46, 78-79; 45 is `ms_delta` | 0 (K35) |
| A5-4 (6) 64 KB-step S rate 144/s | **FIXED**: ≤ 144/s, span ≥ 28 s | 3.1 |
| A5-4 (7) UHB `seg` bits 20-27 cannot hold 256 | **FIXED**: `seg` repacked, `conf` in bits 20-28 in units of 8,192 bytes (0-256); the r4 b31 moved to `flags` b26 | 10.2 |
| A5-4 (8) RUNBOOK C4 "it will not [go away]" applied to META | **FIXED**: META has its own paragraph in C4 (may clear; the run counts) | RUNBOOK C4 |
| A5-4 (9) E1/E2 count rehearsal files | **FIXED**: only files `T<rrr>…` of this run (`rrr` from line 1) are counted; the decoder ignores other runs too (10.2) | RUNBOOK E1, E2; 10.2 |
| A5-4 (10) the "+150 allowance" is not in the gate log | **Accepted**: the claim is withdrawn in 14's preamble; the line count is the orchestrator's (15.8) | 14 |

### 15.2 Red-team findings (attempt-5 red team section 6)

| # | Response | Where |
|---|---|---|
| **IF9** (BLIND) a data region of the active or a ready file refuses writes after creation; r4 crossed it at ≈ 2 KB per tick | **FIXED as the red team specified (G1).** After 3 consecutive FAILED flushes whose windows show a DATA-sector error while another write in the same windows succeeded, the active file is retired (EVENT `region bad <name> <seg_end>`, UHB b27) and the worker switches to the next complete, prefix-usable or in-creation file with room; again if that one fails the same way; with none it holds and creates at 64 KB per tick past the allocator. The verdicts come from S records (4.8), so a whole-stick outage (data and metadata failing together) never triggers it. R8's sentence and the stale 11.3 R36 row corrected. VFAT-FI: a 2 MB range of a ready file, and one spanning the active and the next file; pass when `region bad` comes after 3 FAILED flushes, no record is lost and no hold exceeds 114.7 s. **Simulated** (15.6): with the escape 0 s lost at 25-300 KB/s for 0.75-2 MB regions (hold ≤ 56 s at 25 KB/s); without it 77-192 s lost for 1.5-2 MB, as the red team found | 4.6, 4.4 "Use and switch", 8.5, R8, 11.3 |
| **IF4** (AMBIGUOUS) 25-35 s burst; ≈ 98 sporadic failing ticks; loss at 25 KB/s from r4's re-send rule | **FIXED (G2), threshold changed with evidence.** (1) Range-based durability: a DURABLE flush is durable for its own records; only the failed flushes' `seq` ranges are queued and re-sent, after the next DURABLE flush, inside the normal cap (4.6). (2) Throughput gate in STICK: the first two confirmed 64 KB steps must show ≥ **30 KB/s**, else `MS SLOW` and an abort at 3:00. The red team proposed 35 KB/s for r4's rule; with r5's range re-send the model loses nothing from 25 KB/s up (60-200 runs of 30 min per point, whole-tick and per-operation failures), so 30 KB/s keeps a 5 KB/s margin while aborting fewer usable sticks; a reviewer who prefers 35 can change one constant. (3) R8 states the lossless minimum: 25 KB/s in the model, 30 KB/s gated. Stage 3 F6 runs at 25 and 30 KB/s and must pass | 4.6, 4.8, 8.2, R8, 8.5, 15.6 |
| **IF10** (AMBIGUOUS) chunks of another boot merged | **FIXED, all five parts (G3).** (1) The decoder analyses one run, selected by FILEHDR `run` and nonce; other runs are listed and ignored, also for the raw-image rule. (2) A chunk above its file's confirmed extent (`segment ready`, `stop <name> <conf>`, UHB `seg` conf) is listed, not merged. (3) `--raw` keeps only chunks that verify under the run's nonce. (4) A `(ring, seq)` duplicate with different content is a reported conflict, never dropped. (5) The per-boot nonce is in FILEHDR and UHB and, beyond what was asked, is the initial value of every non-FILEHDR chunk CRC, so another boot's chunk (a rehearsal file, or a stale tail of a deleted file inside this run's file, TE7) fails its CRC outright. RUNBOOK E1/E2 count only this run's files | 10.2, 4.2, 8.5; RUNBOOK E1, E2 |
| **IF7a, IF7b, IF8** (A1 class; at full scope they must be DIAGNOSABLE) | **FIXED by adopting attempt-4 F1(b) and the full F4** (4.8): durability and growth are judged from the S records of data and FAT1 sectors, so a refusing FSINFO, `PSCLOG` directory or allocator FAT sector no longer stops durable recording; new files skip aliases (IF7b) and the allocator's bad FAT sector (IF8) at one attempt per tick. Traces in 15.3. VFAT-FI pass conditions for these schedules are now those of a normal run (no record lost, no hold over 114.7 s, `durable_tick` advancing) plus META shown | 4.4, 4.7, 4.8, 8.5, 15.3 |

### 15.3 Full-scope traces (the designer traces; the red team rules)

- **IF7a, FSINFO refuses from t0.** Every `fsync` returns `-EIO`: FSINFO is
  marked dirty on every `fsync` (`fs/fat/inode.c:453-459`, `fs/fat/misc.c:40-72`)
  and `sync_blockdev`'s wait reports the failed write (`fs/buffer.c:449`,
  `mm/filemap.c:282-283`). Each flush's data sectors are written (`do_writepages`
  runs first, `fs/fs-writeback.c:170`), so its verdict is DURABLE (UHB b30,
  EVENT `flush meta err` once per 10 s); `durable_tick` advances; no panel;
  line 6 `MS DUR 0.3S META <sector>` within ≈ 1-2 s. Creation steps: data and
  FAT1 succeed, FSINFO is tolerated, so growth and new files continue normally.
  Directory entries reach the stick, so even the Mac copy is complete. D8 can
  pass. **Nothing is lost.**
- **IF7b, the `PSCLOG` directory sector X refuses from t0.** Flushes: DURABLE
  as above (the directory write fails, `fs/fat/inode.c:604-605`, after the data).
  The active and ready files keep growing (after step 0 a directory failure is
  tolerated). A new file whose entry falls in X: its step 0 fails on its own
  entry's write (the first DIR record after its data, 4.4 step 4) and it is
  abandoned; the next attempt (next tick: other
  writes succeeded, so the stick counts as working) meets the alias of that
  inode at the same slot (the buffer was re-read, `fs/buffer.c:1378-1384`),
  rejects and closes it, and in the same tick opens again: the alias's entry
  occupies the slot in the buffer, so the next fresh slot follows. Each tick
  adds one slot of X (tick k: k − 1 aliases and one abandon, k names); after
  at most 16 slots the next fresh slot is in X + 1. **(r7, A6-1)** Its step-0
  window holds its own entry's write of X + 1 (OK, from `fat_write_inode`)
  and then `sync_blockdev`'s write of X (failed: the rejected aliases dirtied
  X's re-read buffer, `fs/fat/dir.c:87`, `:1266-1267`); by the own-entry rule
  of 4.4 step 4 it is CONFIRMED, the X failure being META evidence. So
  ≤ 17 ticks and ≤ 153 names (Σ k for k ≤ 16 = 136, then 16 aliases and the
  fresh file; r6 said 152), while the active file and the files ahead
  (≈ 9 minutes) keep recording. **Every later creation re-meets X's lost
  slots** (X is re-read from the stick at each scan): ≤ 16 aliases and the
  fresh file, ≤ 17 names in one tick. A 35-minute run creates 10 files (8
  written and 2 ahead, 15.6), so ≤ 153 + 9 × 17 = 306 names against a budget
  of ≥ 400 (4.4 step 6). This assumes the rejected inodes stay cached; one
  evicted by memory reclaim makes its slot a fresh file again, abandoned at
  step 0, ≤ 17 more names and one more tick for the creation that meets it
  (how often reclaim evicts them is UNVERIFIED; the margin at the minimum
  budget covers 5 such). **(A7-2) If the margin runs out:** creation stops
  (names budget spent), the files ahead last ≈ 9 minutes, then the worker
  holds and the panel shows. **Why eviction is unlikely in this run:** unused
  dentries and inodes are pruned only by `shrink_slab` during reclaim
  (`mm/vmscan.c:1048`, `:1216`) or by `drop_caches`, which the design does
  not use; by the design's own figures segment pages stay cached at about
  2 MB per file created (10 files in 35 min, 15.6) against ≈ 20.8 MB
  `MemFree` (5.3), so reclaim cannot begin much before minute 30 (an
  estimate from those figures, UNVERIFIED on hardware), and the runbook ends
  normal use at 30:00 (RUNBOOK C6). VFAT-FI runs this schedule with guest
  memory well above the page-cache total (8.5). Files
  whose entries are in X have stale or missing entries on the stick; their
  records are on data sectors whose FAT links were written, recovered by the
  raw image (mandatory with META, RUNBOOK E2). **Nothing is lost.** (If X were
  the last slot sector of a directory cluster with every earlier slot used, no
  later slot would exist and creation would stop with ≈ 9 minutes of margin;
  that needs a directory cluster already full except for X's slots, which the
names budget rules out at the start, R26.)
- **IF8, the FAT sector F at the allocator refuses from t0.** Flushes never
  touch F (they never allocate, 4.4). The creating file's step that allocates
  into F fails its FAT1 check and stops (prefix-usable if ≥ 42,496 bytes); the
  next attempt (next tick: data and directory succeeded) allocates at
  `prev_free + 1`, still in F (`fs/fat/fatent.c:455-476`), and is abandoned;
  each attempt moves the allocator one cluster, so ≤ 128 attempts (FAT32: 128
  entries per sector), ≈ 30-40 s, leave F, and the next file is confirmed.
  These abandons leave directory entries pointing at clusters whose FAT entry
  is free on the stick; they hold no records and are never touched again (4.4
  step 5); their Mac copies may fail, the raw image is mandatory. META clears
  when bypassed. **Nothing is lost.**
- **A5-1, a transient outage over a step-0 `fsync`.** Attempt A: data,
  directory and FAT1 fail; A is abandoned (no write succeeded: next attempt
  ≥ 10 s later). After recovery, attempt B gets A's slot and A's inode
  (`fs/fat/inode.c:398-405`); `st_size` = 1,536 and the seen `st_ino` reject
  it and closes it (the tick's flush succeeded, so the stick counts as
  working); the next `open` in the same tick takes the next slot, B's empty
  entry still occupying A's slot in the buffer, and gets a fresh inode; its
  step 0 writes B's and its own entries; that file grows normally. (Had the
  stick still been refusing, B would have been `fsync`ed as a probe and the
  attempt ended.) A's
  inode is never written, extended or walked; no `fat_chain_add` runs on it, so
  the `fat_get_cluster` → FREE → `fat_fs_panic` path of the review (A5-1 step 6)
  is never entered.
- **IF9** and **IF4**: 15.2 and 15.6.

### 15.4 Red-team notes and recommendations (section 6, "Not blocking")

| Note | Response | Where |
|---|---|---|
| **OE8** the driver's `DBG` lines are compiled in and drawn with interrupts off; attempt-4 S9 said otherwise | **Adopted.** Console log level 4 set once at worker start (**r7, A6-2:** `syscall(__NR_syslog, 8, 0, 4)`, return in EVENT `conlevel`; r6 named libc `syslog()` and the supervisor); the error-path printk is stated in 7.1 and VFAT-FI keeps the `DBG` path. **Correction to the record:** attempt-4 red team S9 and anything that relied on it ("the driver prints nothing") was wrong: `ms_psp.c:17-24` defines `DEBUG` and `DBG(args)` as `printk args` | 7.1, 4.2, 8.5, U24, R27 |
| **UL7** a "benign" straddle at Nop k, death at Nop k+1 | **Adopted**: all WT within ± 2 cycles listed with step and both results; `H4 two-stage` candidate; Stage 3 vector | 10.7 step 5, 8.5, X4 |
| **IF5 residual** an implicit truncate after a failed `write()` could walk to a free entry in a stopped file | **Contested with source, and listed in R11.** `generic_file_buffered_write` truncates only when the failed write extends the file: `if (pos + bytes > isize) vmtruncate(inode, isize);` (`mm/filemap.c:2161-2162`). A flush ends at or below `conf` ≤ `i_size`, so it never truncates; and a flush's `fat_bmap` reads only the entries of clusters before the one it maps (`fs/fat/cache.c:241-251`), so it never reads the unconfirmed link either. The red team's chain therefore cannot start from a flush. Its other consequence, a Mac copy that fails because the directory size covers a free cluster, is in R11 and makes the raw image mandatory. The recommended "do not promote" rule is not needed for safety and would only shorten the margin; with F4's classification the worker could apply it, and Stage 2 may if the reviewer prefers | 4.4 step 5, 4.6, R11 |
| **TE7** 14.2's "the file being created holds none" is false when it is also active | **Adopted**: 14.2 and 10.2 corrected; RUNBOOK E1 step 5 says the image may then be requested | 14.2, 10.2; RUNBOOK E1 |
| **A1 cases: let a complete META run count** | **Adopted** (A5-2) | 4.7 |
| 7 "Inode alias" recommendation: compare a new file's `st_ino` with the open files' | **Adopted, generalised**: the alias test compares with every inode the worker has seen (4.4 step 1) | 4.4 |
| 7 "P and POLL rings 4× larger" for long whole-stick outages | **Not adopted.** It costs ≈ 1.2 MB of BSS and is not tied to a non-DIAGNOSABLE scenario: the model shows no loss for outages up to 90-100 s and only the span's excess beyond (15.6); a longer whole-stick refusal is the accepted Case 2 (4.5), which the panel records | 4.5, 4.6 |
| 8 J10 "nothing replaces S records for data errors" | **Agreed and done**: S records now decide both durability and the IF9 escape | 4.8, 4.6 |

### 15.5 Attempt-4 red-team fixes, status at round 6

| Fix | Status |
|---|---|
| F1 (a) never overwrite a failed flush | Kept (4.6). |
| F1 (b) FIBMAP mapping once at creation; a flush is durable when every data sector has an error-free S record, whatever `fsync` returned | **Adopted** (4.8, 4.5); r4 had declined it under A1. |
| F1 (c) `MS META ERR` on HUD and panel; raw image | Kept, changed to informational (4.7; A5-2). |
| F2 incremental creation | Kept; verdicts from S records; start-up step rule (4.4). |
| F3 cap and margin | Kept (4.4 steps 6, 8). |
| F4 escape a bad FAT sector: classify the failing sector as FAT area from the S records; fast retry under a per-run budget | **Adopted in full**: sector classes from the published geometry (4.8); fast attempts (≤ min(400, budget/2) per run) whenever the failed window shows any successful write, ≥ 10 s otherwise (4.4 step 6). |
| F5 preemption holder | Kept (2.11). |
| F6 Stage 3 at 25-300 KB/s, persistent schedules | Kept and extended (8.5). |

### 15.6 Budget, model and format re-check (by script)

Scripts: `design/r5-scripts/budget_r5.py` (budget and format sizes) and
`design/r5-scripts/sim_r5.py` with its `run_*.py` drivers (the model).

**Budget** (17.86 polls/s, 0.23 s tick, the 10.3 strings, the r5 UHB):

| Quantity | r4 | r5 |
|---|---|---|
| Steady payload | 5,870 B/s | 5,887 B/s (UHB +4 B per tick) |
| Nominal / +STATS / +STATS+PROCS flush | 1,223 / 2,011 / 3,167 | 1,227 / 2,015 / 3,171 (same padded sectors) |
| On the stick: steady / creation ticks / run average | 7,123 / 9,350 / 7,598 B/s | unchanged |
| Run-average payload | 6,334 B/s | 6,351 B/s |
| 15 / 30 / 35 min | 6.8 / 13.7 / 16.0 MB | 6.84 / 13.68 / 15.96 MB (4, 7, 8 files; + two ahead: 12, 18, 20 MB) |
| Creation | 4,736 sector writes per file, 17.2/s, 8.8 KB/s | unchanged |
| Sector writes, all / LED operations | 40.7/s / ≈ 81/s | unchanged; 64 KB steps only 3-9 times at start-up |
| Flush bound | 37,692 → 37,888 | 37,696 → 37,888 |
| Rings; spans P / W / S steady / 8 KB / 64 KB | 652,288 B; 114.7 / 1,280 / 181 / 53 / 29 s | 652,288 B; 114.7 / 1,280 / 181 / 53 / 28 s |
| Kernel memory | ≈ 653 KB | ≈ 653 KB (7 more stats words in the reserved area) |
| Worst-case stick use | ≈ 189 MB | ≈ 189 MB |

**Format re-check (D20).** `struct.calcsize`: SC 80, WEXT 208, W 288, POLL 40,
S 40, STATS 768, CTL 32, chunk header 20, block header 8, **FILEHDR fixed part
44, UHB 84** (r5). SC offsets recomputed field by field (`seq` 0 … `pre_wrk` 42,
`pre_cls` 44, `ms_delta` 45, `pre_flags` 46, `preempt_delta` 47, `rx` 48,
`lc_epc` 64, `led_or` 72, `led_pid` 76, `pre_tot` 78): unchanged. UHB `nonce`
at byte 80; FILEHDR `nonce` at byte 40. Every 10.2/10.3 string matches section
1 and 1.7.

**Model** (`sim_r5.py`; reproducible from this description). The P ring is the
binding ring (35.71 records/s, 4,096 entries); a drain takes ≤ 48·m P records,
m = min(4, max(1, ⌈Δt/0.23⌉)); a flush carries 164 B per P record drained plus
280 B, padded to 512, minimum 1,536, only if `seg_end + 40,960 ≤` the usable
limit; tick = 0.23 s + (flush + step + 1 KB per `fsync` + 1 KB per allocating
step) / speed (speed in units of 1,024 B/s); a flush is DURABLE iff its data
write succeeded; failed records are queued by range and re-sent from the tick
after the next DURABLE flush; a record older than `head − 4,096` when needed is
lost. Creation: step 0 of 1,536 B, then 64 KB while holding or while the room is
below 81,920 B, else 8 KB; 32 KB clusters; FAT1 failure stops, other failures
retry ≤ 3; next attempt next tick unless the whole tick failed (≥ 10 s); two
complete files ahead. Failures: Poisson, 98 per 1,800 s, applied to whole ticks
or to single operations by their duration; bursts fail every operation in
their interval; IF9 fails flushes inside a region of file 2 from 60 s after the
worker starts. Collector start 20 or 40 s, thread start 3 s.

**Start-up (A5-3)**, first flush / first complete drain after the worker
starts (worker at 20 s / 40 s of uptime):

| KB/s | 20 | 25 | 30 | 35 | 40 | 52 | 100 | 300 |
|---|---|---|---|---|---|---|---|---|
| r5 rule | 3.9 / 41-76 s | 3.2 / 26-48 s | 2.8 / 18-35 s | 2.4 / 14-29 s | 2.2 / 13-22 s | 1.8 / 9-17 s | 1.2 / 5-9 s | 0.7 / 3-6 s |
| r4 rule (same model) | 3.9 / 170-187 s | 3.2 / 57-124 s | 2.8 / 31-70 s | 2.4 / 24-48 s | 2.2 / 18-37 s | 1.8 / 12-25 s | 1.2 / 6-11 s | 0.7 / 3-6 s |

No boot record is lost at any speed in either rule. (The reviewer's model put
r4 at 52 KB/s near 60 s; mine gives 25 s there and agrees at 25 KB/s.)

**IF4 sporadic** (98 events per 30 min, worker at 40 s; 200 runs of 30 min
per point at 22-35 KB/s, 60 runs at 20 and 40-300 KB/s): r5 loses nothing at
28, 30, 35, 40, 52, 100 and 300 KB/s under both failure models, nor at 25 KB/s
in these 200 runs; **(r7, A6-3)** with the seeds 0-59 of `run_if4.py`, one
whole-tick run at 25 KB/s (seed 9) loses 15.2 s (longest hold 22 s), so 1 run
in 260 at 25 KB/s (re-run for round 7; none at 28 or 30 KB/s with seeds 0-59);
at 22 KB/s, whole-tick failures lose 0.09-0.13 s on average (1-2 runs
of 200); at 20 KB/s (60 runs) 10.2 s on average in 14 of 60 runs. Per-operation
failures lose nothing from 20 KB/s up; the longest hold is 34 s. Hence the
30 KB/s gate.

**Whole-stick bursts** (start swept over the run in 37 s steps): no loss up to
90 s at 25 KB/s and up to 100 s at 30-300 KB/s; at 110 s, 13 / 7 / 4 / 1 / 0 s
lost at 25 / 30 / 52 / 100 / 300 KB/s; at 130 s, 19-30 s.

**IF9** (region in file 2): without the escape, 0.75 MB loses 0-7 s, 1.5 MB
77-128 s and 2 MB 126-192 s at 25-300 KB/s; with the escape **0 s** in every
case, longest hold 56 s at 25 KB/s, 13 s at 35 KB/s, ≤ 1 s at ≥ 52 KB/s.

### 15.7 New and changed mechanisms, with their cost (no-new-mechanism discipline)

| Row | What | Cost |
|---|---|---|
| K37 (new) | geometry words, stats 153-159 | 7 words, 8 one-time stores, ≈ 12 LOC (kernel) |
| U21 (new) | S-record verdicts, sector classes, FIBMAP extents (F1(b), F4) | ≈ 2 `pread`s per tick, ≤ 3 `ioctl`s per step, ≈ 6 KB tables, ≈ 120 LOC |
| U22 (new) | bad-region escape (IF9) | ≈ 25 LOC |
| U23 (new) | 30 KB/s throughput gate (IF4, A5-3) | ≈ 10 LOC |
| U24 (new) | console log level 4 (OE8) | one system call |
| U25 (new) | boot nonce in FILEHDR, UHB and CRC seeds (IF10) | 2 format words, ≈ 10 LOC |
| RB6 (new) | `MS SLOW`/`MS DIR FULL` aborts; A4 `mkdir`; E1/E2 this run only | runbook lines |
| U5, U6, U9, U19, U20, X1, X4, RB4, RB5, K27, K29, K34, K35, U3, U7, U8, U12 (changed) | range re-send; alias test and step verdicts, start-up step, one attempt rule, names budget; HUD states; STICK; META informational; decoder run selection and UL7; corrected figures | ≈ +120 LOC in `pscol` over r4 besides U21 |

Nothing was cut in r5. Kernel additions are the K37 stores only; the syscon
path, the timer interrupt and the scheduler hooks are unchanged (D10, 7.1).

### 15.8 Line count and remaining weak point

DESIGN.md is now **2,588 lines** in total (2,050 in r4), 2,213 through
section 12 (1,920 in r4); RUNBOOK.md (revision 5) is 483 lines. The orchestrator
records the count; no allowance is claimed.

**Weakest point.** Every r5 verdict depends on two things only the stick can
show: that the S hook sees each transfer's real outcome (the driver returns a
sector's error only after 10 tries, `ms_psp.c:252-268`, and a "successful" write
that the card silently loses is invisible, R11), and that this tree's vfat
behaves under failure as read (FAT1 and the directory written from in-memory
buffers in `sync_blockdev`, the alias path of 4.4 step 1). The geometry
self-check catches a wrong mapping before the run, and VFAT-FI (R18,
feasibility UNVERIFIED) is the only place the failure paths can be exercised
before the run. If VFAT-FI cannot be built, the alias and verdict logic reach
the hardware tested only by the host vectors of 8.5.

---

## 16. Response to G1 attempt 6 (round 7)

Closure only (gates/LOG.md, note of 2026-10-05): `gates/G1-attempt6-review.md`
A6-1 to A6-4 and `gates/G1-attempt6-redteam.md` IF7b and TE10. No mechanism,
record type, field, ring, HUD line, panel state, counter or runbook step was
added; the one new EVENT string is the record A6-2 asks for. The order of
writes A6-1 relies on was read in `/home/ubuntu/psp/build/linux` for this round.

| Item | Response |
|---|---|
| **A6-1** (blocking, D6; = IF7b) | **FIXED at 4.4 step 4, 4.8, 8.5, 15.3, U21.** Step 0's own entry is the first DIR-class write record with the worker's pid after the last DATA record of the step's data sectors; it must exist and be error-free; other DIR failures are META evidence only; "any failure abandons" now reads "not CONFIRMED → abandoned". Order verified: data `fs/sync.c:90` (synchronous driver, `ms_psp.c:228-236`), then `file_fsync` `:97` (`fs/fat/file.c:136`) → `write_inode_now` `:62` (`fs/fs-writeback.c:568-576`) → `fat_write_inode(…, 1)` `fs/fs-writeback.c:173-174` → `sync_dirty_buffer` `fs/fat/inode.c:604-606`, before `write_super` `fs/sync.c:67-68` and `sync_blockdev` `:72`. One deliberate difference from the red team's text ("a `pdflush` DIR record is ignored"): a `pdflush` DIR record *between* the last DATA record and the worker's first DIR record makes step 0 not CONFIRMED, because `pdflush` can write the entry's buffer between `fs/fat/inode.c:604` and `:606` (`CONFIG_PREEMPT_BKL=y`, `.config:136`) and `sync_dirty_buffer` then writes nothing (`fs/buffer.c:2708-2709`); this can only cost a name. 8.5: three step-0 vectors added (own OK + other DIR failed → CONFIRMED; own failed + other OK → abandoned; own record missing or preceded by `pdflush` → abandoned). VFAT-FI IF7b: fresh file CONFIRMED within 20 ticks, timed from the first creation attempt after onset rather than META onset (META can show minutes before a creation is due, when the active file's entry is in X), ≤ 153 names up to it, ≤ 17 per later creation. 15.3: first phase ≤ 153 names (r6's 152 counted the abandons twice and left out the confirming tick), each later creation ≤ 17, ≤ 306 in a 35-minute run against ≥ 400; inode eviction by reclaim marked UNVERIFIED. 4.4 step 6 "IF7b ≤ 152" is left as it was: it bounds fast attempts, and IF7b needs at most 16 |
| **A6-2** (advisory) | **FIXED at 4.2, 7.1, U24, 15.4, 10.2 (EVENT list).** `syscall(__NR_syslog, 8, 0, 4)` as `telem.c:281` (or `klogctl(8, NULL, 4)`, `staging_dir/usr/include/sys/klog.h:30`); return and `errno` in EVENT `conlevel <ret> <errno>`. The call moved from the supervisor to worker start, because the supervisor writes no EVENT (4.2: "writes neither the stick nor `ctl`"); the level is global, so an instance-2 repeat is harmless |
| **A6-3** (advisory, a-g) | **FIXED.** (a) at 10.2 UHB `seg`: storage unchanged (⌊conf / 8,192⌋); the decoder takes SEG for 256, else 8,192·v + 1,536, which is exact for every conf a file in creation can have. (b) at 4.3: UHB 104, 37,696. (c) at 2.4, 4.8, R25: `ms_psp.c:250`; hook after the loop ending at `:199`. (d) at section 0 U6: the read-only worker rule. (e) at summary 7, 4.8, R8, 15.6: re-run gives 1 run in 260 at 25 KB/s losing 15.2 s (seed 9 of 0-59, whole tick), none at 28 or 30 KB/s; the gate stays 30 KB/s; 15.2's round-6 sentence stays as the record of that round, and 15.6 supersedes it. (f) at 8.5 VFAT-FI: within 10 s plus one tick of recovery. (g) at RUNBOOK B5: write down `rrr` |
| **A6-4** (advisory) | **FIXED at 2.8 and 8.5 (reader row).** The ring `read()` sets `*ppos`, never `file->f_pos` (`fs/read_write.c:364-366`, `:404-405`); Stage 3 interleaves `pread` windows with ordinary drains |
| **TE10** (red-team AMBIGUOUS) | **FIXED at 4.4 "Use and switch" and 8.5 Errors.** A file that has been active is never a switch target again; `seg_end = 1,536` only for a never-active file; an active file still in creation holds with 64 KB steps and resumes at its own `seg_end` once `seg_end + 40,960 ≤ conf`. Errors vector: catch-up with two failed steps, and with a 3 s burst; pass: no region written twice, boot records intact. The red team's optional fix 3 (tie the start-up step to the flush size) is not adopted: it is optional and would change a rule and the model |
| **Budget** | `budget_r5.py` re-run: every figure unchanged; **no budget number changed**. Only stale text was corrected to the script's values (4.3). `sim_r5.py` re-run for (e) only |
| **D20** | UHB `seg` re-checked: `'<21I'`, `seg` word 18 at byte 72, bits 20-28, writer and decoder now state the same mapping; no other field's description changed. The EVENT list (10.2) gains `conlevel` to match 4.2 |
| **Lines** | DESIGN.md through section 12: **2,213 → 2,254 (+41)**; RUNBOOK.md 483 → 485 (+2) |

---

## 17. G1 ruling after G2 attempt 1

Designer's proposal on the "back to G1" routing of `gates/LOG.md` (G2,
2026-10-06): `gates/G2-attempt1-review.md` F1 (DV-3) and F4-F5,
`gates/G2-attempt1-verify.md` findings 1-3, `impl/IMPLEMENTATION.md` section 0
(OD-1, OD-2, OD-3, OD-5, OD-6) and its two stale texts. Text only: no
mechanism, record, field, ring, check, HUD line, panel state or runbook step was
added, and nothing outside these six items changed. Frozen inputs:
`design/DESIGN.r7.md`, `design/RUNBOOK.r7.md` (the G1-approved revision 6 with
the A7 edits); the change is `design/g1ruling.diff`. RUNBOOK.md is unchanged:
none of its steps, strings or figures depends on these items (KRN red is an
abort as before; `POLL:NW0` is unaffected, 10.7). The G2 code findings F2, F3,
F6 and F7 need no design change and stay with G2.

| Item | Decision | Sections changed | Why D1-D14 still hold |
|---|---|---|---|
| **R-1** (OD-1, DV-3; D3 against D10) | **Option (a).** `nwords` is exact for 0 to 7 received words; `nwords` = 7 with `rx[14..15]` = `ff ff` means "7 or 8", flagged `nw7or8` by the decoder and read as the set {7, 8} by every rule. Options (b) (+2 instructions per received word in S18) and (c) (+1 hand-written instruction on the 8-word exit edge) are **not approved**: both add instructions inside S13..S20, the G3-high part of the window where H4 and H10 act (J1, 7.3), and (c) would be hand-written code inside the window, a new mechanism that the 2.1 criteria cannot compare with the baseline | Header; 1.2 offset 22; 2.1 A4; 6 (preamble); 10.3; 10.7 ("`nwords` 7 or 8", rule by rule) | **D3:** `rx[16]`, `cmd`, `ret` and the word count are recorded raw; the count is exact except in one case that the record itself identifies, and there the 16 `rx` bytes are identical whether the 8th word arrived or not, so the one bit lost carries no byte of the frame. **D2:** every row that reads `nwords` was checked (10.7): thresholds at 0, ≥ 1 and ≤ 8 are not crossed; template, WB, H4, N2b (UL3), H5 and H8/O3 comparisons use set membership and decide on bytes that are the same either way; the P6 cross-check loses only an "inconsistent" flag in a case whose outcome (−2) is allowed either way. **D10:** 0 instructions in the window, unchanged. **D14:** `ret` still separates −2, −3, −4, −5. D1, D4-D9, D11-D13 do not involve `nwords` |
| **R-2** (OD-2, DV-4; D10 wording) | **The acceptance test for D10 is the 2.1 criteria** (as 2.1 and 7.2 already said); literal identity is not. Within them exactly three differences are allowed: stack-slot offsets, a consistent value-preserving renaming of registers, and an exit branch's delay slot after the exit decision and the path's last MMIO access. The G2-attempt-1 window passes (105 = 105, same MMIO order and form, no call, no global load or base reload) | Summary 1; 2.1 (after the criteria); 7.1 "Code layout"; 7.2 (test, and why the differences cannot change on-path timing) | **D10:** nothing is added inside the window and its timing is unchanged: renaming keeps opcodes, operands, values and the dependency graph, on which in-order MIPS32 timing depends (that Allegrex has no register-number-dependent timing is UNVERIFIED, 7.2); the changed delay slot runs after the −3 decision and the last MMIO access. The layout shift (0xc4 bytes) was already accepted in 7.1 and is measured (`ack_polls`, duration). No lock or interrupt masking anywhere (7.1). Other D items are not involved |
| **R-3** (G2 F5; 5.4, 7.3) | **Restated with the objdump counts; no trim.** ≈ 60 instructions before S5 and ≈ 400-550 after S20 per thread command (≈ 2.1-2.8 µs cached, r5: ≈ 0.8 µs); G3-low gap +2.1-3 µs (r5: 0.75 µs); watchdog path +2-4 µs (path count UNVERIFIED, measured as `w_rec_cost_max`); ≈ 280 B more stack on the Nop path. Not trimmed: the cost is outside the window, takes no lock and masks nothing; trimming `psc_sc_exit` would rework code that passed C3/C4 (the DV-5 snapshot order) for a gain of ≈ 0.05 % of a tick, and the G3-low-gap effect is recorded per poll | Summary 7; section 0 K1; 5.3 (stack); 5.4 (rows, D10 ratio paragraph); 7.1 two rows; 7.3 bullets 1 and 4, new bullet 5; 11.1 R6 | **D10:** "beyond the few instructions needed to append a record": the added code is the record append itself (fill, copy of the `lc`/LED/holder words under their brackets, publish) and is outside S5..S20; its time is stated (5.4) and is ≤ 10 % of any command lasting ≥ 28 µs (UNVERIFIED; measured on every command, HUD line 10). The H4 argument (7.3) holds: the window is unchanged and start phases move ≤ ≈ 0.09 % of a tick, recorded per command. The one direction that could hide a failure, a longer G3-low gap, is stated and recorded (7.3, R6). **D9, C3:** the deeper Nop stack is ≈ 280 B of 8 KB, with the panel never on a watchdog tick |
| **R-4** (OD-3, G2 F4; `build_id`) | **The kernel's definition is adopted:** stats word 2 = CRC-32 (zlib, initial 0) of `linux_banner`, whose bytes equal `/proc/version`. KRN requires word 2 to equal the CRC-32 of `/proc/version` read by the worker at start; the decoder takes the expected value from the packaged build's `BUILD/build_id.txt` and also checks it against each FILEHDR's `/proc/version` | 1.7 words 0-4; 8.2 KRN; 10.1 | **D13:** KRN still proves, before death, that the stats block is the running kernel's; the collector-kernel match is by construction (one image). **D2, D20:** the EPC and register maps are accepted only from the image that ran, so the H4 step (W `epc`, `lc_epc`) cannot be read through another build's maps. No kernel or record change (the value is already computed and stored) |
| **R-5** (OD-5, OD-6) | **Figures corrected; the image bound stands.** `pscol`: 183,968 B per process (text included under `CONFIG_SONY_PSP`, `fs/binfmt_flat.c:471-472`), one 256 KB block each, both at boot, none later. Image: +43,631 B `vmlinux.bin` (5,521 B under 49,152), +36,919 B `vmlinux-0.22.bin`; pspboot load UNVERIFIED (R20). Bound kept at 49,152 B per image; the only rule for later revisions is that each G2 attempt restates both growths and the change since attempt 1, and growth above the bound returns to G1 (an image that does not load is an abort, 8.3, so no tighter margin buys anything) | Summary 7; section 0 U1; 4.2; 5.3; 7.1 "Code layout", "Memory"; 11.1 R20 | **D7, IF2 (U1):** no allocation after boot still holds: both blocks are taken at boot and the takeover runs in the supervisor's own block. 512 KB is 2.5 % of `MemFree` and less than telem's 1 MB, so 7.1's memory statement stands. **D12:** stick volume unchanged. Other D items are not involved |
| **R-6** (two stale texts) | **Fixed to match the format.** A RECS chunk is ≤ 34,304 + 80 (a new-records block and at most one re-send block per ring) + 20 = 34,404 B; a flush 37,736 → 37,888 B, still ≤ 40,960. 2.11 now names SC bytes 42-44, 46 and 78-79 (`pre_*`); byte 45 is `ms_delta` | 4.3 Bounds; 5.1; 10.2 writer guarantees; 2.11 | **D20:** the text now matches the format field for field (the code already did: G2 attempt 1 section 6.2). **D12:** the flush bound still fits the 40,960-byte buffer. No record, chunk or code changes |

**Consequences for Stage 2 (to implement exactly, then G2 attempt 2):** the
decoder flags `nw7or8` and applies set membership in the rules of 10.7; pscol's
KRN computes the CRC-32 of `/proc/version` at worker start and compares it with
stats word 2; the package carries `BUILD/build_id.txt` from the packaged build's
`banner.txt`; IMPLEMENTATION.md restates the 5.4 counts if `psc.c` or
`syscon.c` change, and both image growths. The kernel needs no change for these
items.
