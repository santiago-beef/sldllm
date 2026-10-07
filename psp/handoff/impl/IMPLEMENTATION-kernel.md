# Stage 2: kernel implementation notes (PSC trace)

Author: kernel implementer (Stage 2), 2026-10-06. Specification:
`design/DESIGN.md` revision 6 (G1 PASS, gates/LOG.md). Tree:
`/home/ubuntu/psp/work/linux`, branch `stage2-trace`, HEAD `0b0a2acf`.
The original tree `/home/ubuntu/psp/build/linux` was only read
(`sha256sum -c gates/baseline-tree.sha256`: exit 0 after the work).

Companion files in `handoff/impl/`:

| File | What |
|---|---|
| `syscon-window-diff.txt` | D10 proof: both `Syscon_cmd` listings and the S5..S20 comparison |
| `d10_proof.py` | the script that writes it (exit 0 = pass) |
| `epcmap.txt`, `regmap.txt` | DESIGN 10.6 maps for this build |
| `mkmaps.py` | writes them; refuses if the build does not match its step table |
| `panellayout.txt` | DESIGN 10.8 panel columns |
| `A7-design.diff` | the three G1 advisory edits to DESIGN.md (section 0) |

---

## 0. G1 advisories A7-1, A7-2, A7-3: applied to DESIGN.md

Applied as the "What would close it" column of
`gates/G1-attempt7-review.md` section 7 says, text only. Unified diff in
`impl/A7-design.diff`. DESIGN.md sha256 before `7f03ed8e…ce42`, after
`20f659e2…e471`; 2,669 lines before, 2,680 after.

| Item | Where (new line) | Before | After |
|---|---|---|---|
| A7-1 | 4.4 step 6 (l. 1146-1147) | "(≥ 200: IF8 needs ≤ 128, IF7b ≤ 152)" | "(≥ 200: IF8 needs ≤ 128, IF7b ≤ 16 per creation that meets the refusing sector (≤ 153 names, 15.3))" |
| A7-2 (a)+(b) | 15.3 IF7b (l. 2483-2493) | ended "…the margin at the minimum budget covers 5 such)." | adds: **if the margin runs out**, creation stops (names budget spent), the files ahead last ≈ 9 minutes, then the worker holds and the panel shows; **why eviction is unlikely**: unused dentries and inodes are pruned only by `shrink_slab` during reclaim (`mm/vmscan.c:1048`, `:1216`, re-read in this tree) or by `drop_caches`, which the design does not use; segment pages stay cached at ≈ 2 MB per file created (10 files in 35 min, 15.6) against ≈ 20.8 MB `MemFree` (5.3), so reclaim cannot begin much before minute 30 (estimate, UNVERIFIED on hardware), and the runbook ends normal use at 30:00 (RUNBOOK C6); VFAT-FI runs this schedule with ample guest memory (8.5) |
| A7-2 (VFAT-FI) | 8.5 VFAT-FI pass conditions (l. 1885) | IF7b "… every later creation ≤ 17 names)" | adds "**(A7-2)** the IF7b schedule runs with guest memory well above the page-cache total, so reclaim never evicts the rejected inodes (15.3)" (the review's first option) |
| A7-3 | 4.3 step 3 (l. 953-954) | "one `syslog(3)` into the 16 KB buffer, as telem" | "one `syscall(__NR_syslog, 3, buf, 16384)` as telem (`telem.c:279-282`), into the 16 KB buffer" |

No other DESIGN.md text was changed. DOSSIER.md, WORKFLOW.md and the gate
reports were not edited.

---

## 1. Summary

- **Build:** `/home/ubuntu/psp/work/build.sh` from clean, rc 0, log
  `/home/ubuntu/psp/work/logs/build-20261006T012834Z.log`, outputs
  `/home/ubuntu/psp/work/out/20261006T012834Z/` (git HEAD
  `0b0a2acf8a0a25bd69be071ebee773b7a45d72ed`, no tracked changes). Banner
  `Linux version 2.6.22 (root@psp-work-build) (gcc version 4.2.1) #1 PREEMPT Tue Oct 6 01:31:35 UTC 2026`.
- **`vmlinux-0.22.bin` sha256 `5d4a30e0a5c2cf05195063ef2ee42e192ba9fcf91bed7362e877731f4b9d8c32`**,
  909,168 bytes (+9,766 against the baseline rebuild 899,402 in
  `work/out/20260927T204324Z/` and `work/prebuilt/`; +9,764 against
  `work/out/20260927T204657Z/` 899,404; +9,886 against the 2008 image in
  `pspboot-baseline/` 899,282). `vmlinux.bin` 1,739,612 (+16,384).
  Within the 48 KB bound of DESIGN 5.3 (G2 C6). Section 7.
- **Warnings:** the 38 distinct warning lines of the baseline build, no
  other (the set is identical; no warning in a changed or new file).
- **D10:** the instruction stream on every path from S5 to S20 (105
  instructions, including the −3 and −4 exits) is the baseline's, apart from
  stack offsets and a **consistent renaming of five callee-saved registers**
  (s3→s7, s4→s3, s5→s4, s6→s5, s7→s6) and the delay slot of the first −3
  exit branch (after the exit decision). Same MMIO loads and stores in the
  same order and form, same instruction counts, no call. It is **not**
  byte-identical apart from stack offsets: section 5 and deviation DV-4.
- **Needs a decision (touches D3): nwords.** The design's nwords capture
  cannot be had at zero cost inside the window; the implementation keeps the
  window unchanged and reports nwords exactly except one case (7 or 8 words
  with the 8th word 0xFFFF reads 7). DV-3; options listed there.
- **Interface item for the other implementers:** `build_id` (stats word 2)
  is defined here as zlib CRC-32 of `linux_banner` (= `/proc/version`). DV-12.

---

## 2. Commits (branch `stage2-trace`, on top of `ca7dac0a` psc_format.h)

| # | Commit | Subject | Files | DESIGN |
|---|---|---|---|---|
| 1 | `4c4e7aee` | config: build the initramfs from the work tree | `.config` | recon/build.md 1.3, R20 |
| 2 | `84112996` | psp: watchdog localTick at file scope as psp_local_tick | `arch/mips/psp/psp.c` | 1.1, 2.2 |
| 3 | `a109c03b` | printk, joypad: read-only semaphore count accessors | `kernel/printk.c`, `drivers/input/joypad_psp.c` | 1.7 w62-63, 2.6 |
| 4 | `b2469e76` | psc: trace rings, records, stats and /proc/psc | `include/asm-mips/psc.h`, `arch/mips/psp/psc.c`, `arch/mips/psp/Makefile` | 1, 2.1, 2.3, 2.4, 2.5, 2.8, 2.11, 2.12, 3 |
| 5 | `bd182ffb` | syscon: record every Syscon_cmd call (A1-A4) | `arch/mips/psp/ipl_sdk/syscon.c` | 2.1, 7.2 |
| 6 | `d5679835` | psp: explicit watchdog context flag around both Nop call sites | `psp.c` | 1.8, 2.2 |
| 7 | `bcc20c71` | psp: timer tick hooks T1 and T2 | `psp.c` | 2.3 |
| 8 | `a9f70a04` | psp: LED read-modify-write read-back | `psp.c` | 2.4 |
| 9 | `90d275aa` | ms_psp: S record per segment transfer, marker, metadata tag | `drivers/block/ms_psp.c` | 1.5, 2.4, 4.8 |
| 10 | `14766616` | joypad: thread stages, POLL record, driver counters | `drivers/input/joypad_psp.c` | 1.4, 2.5 |
| 11 | `fa705875` | sched: wake-up and switch hooks | `kernel/sched.c` | 2.11 |
| 12 | `30616d25` | exit, writeback, vcs, mousedev: above-driver counters | `kernel/exit.c`, `mm/page-writeback.c`, `drivers/char/vc_screen.c`, `drivers/input/mousedev.c` | 2.6, 2.7 |
| 13 | `90a206b2` | fat: read-only detection and geometry for the trace | `fs/fat/inode.c`, `fs/fat/misc.c` | 2.12, 4.8 |
| 14 | `0b0a2acf` | psc: kernel stall panel | `arch/mips/psp/psc_panel.c`, `psc.c` (1 call), `Makefile` | 2.10 |

`psc_format.h` (`ca7dac0a`, interface implementer) was not modified.
Every commit compiles and links (section 6, C10). `git diff baseline..HEAD`:
19 files, the 3 new files `include/asm-mips/psc.h` (279 lines),
`arch/mips/psp/psc.c` (1,247), `arch/mips/psp/psc_panel.c` (338).
Generic-kernel hooks (`kernel/`, `mm/`, `fs/fat/`, `drivers/char/`,
`drivers/input/mousedev.c`) are inside `#ifdef CONFIG_SONY_PSP`.

---

## 3. Design → code

Line numbers are of HEAD `0b0a2acf`. `psc.c` = `arch/mips/psp/psc.c`.

| DESIGN | Element | Code | Commit |
|---|---|---|---|
| 1.0 | packed LE structs, sizes asserted | `include/linux/psc_format.h` (interface) | `ca7dac0a` |
| 1.1 | tick = `psp_local_tick`; `ts_read()` | `psp.c:70-71`, `:384-395`; `include/asm-mips/psc.h:40-52` (`psc_ts_read`) | 2, 4 |
| 1.1 | tick length `c_pre`, `total_counts`, `c_pre_max`, `long_ticks` | `psp.c:355-356` (T1 mfc0), `psc.c:561-573` | 7, 4 |
| 1.2 | SC record, all fields | `psc.c:259-302` (`psc_fill_sc`), `:304-370` (`psc_fill_thread`: lc, led, pre, panel flag) | 4 |
| 1.3 | W record + extension (interrupted frame, lc block) | `psc.c:372-425` (`psc_fill_wext`), `:493-519` (W branch of `psc_sc_exit`) | 4 |
| 1.4 | POLL record | `psc.c:842-907` (`psc_poll_begin/end`); fields set in `joypad_psp.c` (row 2.5) | 4, 10 |
| 1.5 | S record | `psc.c:655-730` (`psc_ms_seg_begin/end`) | 4 |
| 1.6 | M record, fill-once, `m_dropped` | `psc.c:475-492` | 4 |
| 1.7 | stats block, every word (live words in `psc_mem.st`, [R] words at read) | `psc.c:1069-1120` (`psc_stats_snapshot`); writers at the hook sites | 4 |
| 1.8 | origin by explicit flag, then `current == psc_jp_task` | `psc.c:197-257` (`psc_sc_entry`), `:169-176` (hand-off area by the same rule); flag `psp.c:390-392`, `:578-580` | 4, 6 |
| 2.1 A1 | entry, inline, no call | `psc.c:197-257`, called inline from `psc_syscon_cmd` `psc.c:526-533` | 4 |
| 2.1 A2 | per-attempt capture default | `syscon.c:127` (`spin = 0`); other defaults derived at exit (DV-2) | 5 |
| 2.1 A3 | in-window captures into stack slots | `syscon.c:119-123` (slots), `:166`, `:171`, `:182`, `:203-206`; `dmy` (S5) and `spin` (drain) unchanged lines | 5 |
| 2.1 A4 | −3/−4 → `goto out`; exit hand-off; `psc_sc_exit` | `syscon.c:165`, `:206`, `:309-310`, macro `:17-61`; `psc.c:188-191` (`psc_xfer_out`), `:427-520` (`psc_sc_exit`) | 5, 4 |
| 2.1 | callers record through the wrapper | `syscon.c:330`, `:344`, `:419`; wrapper `psc.c:526-533` | 5 |
| 2.2 | watchdog context flag at both call sites; `localTick` at file scope | `psp.c:384-395`, `:576-580` | 2, 6 |
| 2.3 T1 | Count before the reset | `psp.c:351-365` | 7 |
| 2.3 T2 | `psc_tick_hook` after `psp_watchdog_tick`, before `psp_uart3_txrx_tick` | `psp.c:370-371` → `psc.c:561-618` | 7, 4 |
| 2.3 T2a | lc words, uncapped, nested-tick test | `psc.c:575-610` | 4 |
| 2.3 T2d | once a second at tick ≡ 125 (mod 250): panel, guard words | `psc.c:539-559`, `:612-617` | 4, 14 |
| 2.4 | LED read-modify-write: same load and store, then `psc_note_led` | `psp.c:412-428`; `psc.c:625-652` | 8, 4 |
| 2.4 | MS segment marker and S record under `s_psp_ms_rw_sem` | `ms_psp.c:349`, `:364`, `:378`, `:393` | 9 |
| 2.4 | metadata tag (block-device page cache), MBR read 0 | `ms_psp.c:262-275`, `:132` | 9 |
| 2.4 | partition start (stats 153) | `ms_psp.c:202-203` | 9 |
| 2.5 | thread start, loop top, stages 1-17, `ri_branch`, `pi_flags`, pushes, mouse, counters | `joypad_psp.c:484-499`, `:515-541`, `:557-626`, `:405-435`, `:702-766` | 10 |
| 2.5 | fops counters | `joypad_psp.c:232`, `:248`, `:252`, `:266`, `:304`, `:327` | 10 |
| 2.5 | `queue_free` stages 1-5 (H9) | `joypad_psp.c:355-374` | 10 |
| 2.6 | `do_exit` clears `psc_jp_task` | `kernel/exit.c:922-928` | 12 |
| 2.6 | vcs ioctl counters | `drivers/char/vc_screen.c:576`, `:581`, `:586`, `:591` | 12 |
| 2.6 | mousedev SYN, notify, read counters | `drivers/input/mousedev.c:239`, `:343`, `:669` | 12 |
| 2.6 | `console_sem` / `list_sem` count accessors | `kernel/printk.c:71-76`; `joypad_psp.c:629-633` | 3 |
| 2.7 | `wb_kupdate` count and tick | `mm/page-writeback.c:452-455` | 12 |
| 2.8 | `/proc/psc/{p,poll,w,s,m}` read (3.5, `*ppos` only), `llseek`, open | `psc.c:954-1067` | 4 |
| 2.8 | `/proc/psc/stats` | `psc.c:1069-1145` | 4 |
| 2.8 | `/proc/psc/ctl` ops 1-4 | `psc.c:1147-1195` | 4 |
| 2.8 | the one printk, from W seq 0 | `psc.c:1242-1244` (`PSC_BOOT_PRINTK_FMT`) | 4 |
| 2.9 | contexts | section 6, C3 | |
| 2.10 | stall panel: condition, paint, clear, test, VRAM stores only, `pspClearDcache` | `psc_panel.c:301-338`, font `:37-58`, fill `:135-155`, lines `:185-282`, accounting `:284-299` | 14 |
| 2.11 | hook W (one compare) | `sched.c:1661` → `psc.h` `psc_sched_wake`, `psc.c:732-748` | 11, 4 |
| 2.11 | hook S (`wk_*` and the preemption-holder branch) | `sched.c:3713` → `psc.h` `psc_sched_switch`, `psc.c:750-831` | 11, 4 |
| 2.12 | `fat_fill_super` success: sb + geometry 154-159 | `fs/fat/inode.c:1418-1420` → `psc.c:912-926` | 13, 4 |
| 2.12 | `fat_fs_panic` counter and first tick | `fs/fat/misc.c:25-27` → `psc.c:928-933` | 13, 4 |
| 2.12 | `ms_rdonly` (reader and T2d) | `psc.c:936-941` | 4 |
| 3.1 | one static BSS object, 652,288 B of rings, 7 guard words | `psc.h:185-200` (`struct psc_mem`), `psc.c:37-47`; armed in `psc_init` `psc.c:1211-1214` | 4 |
| 3.4 | writer protocol (invalidate, fill, publish seq, then head) | P `psc.c:450-458`, M `:482-490`, W `:499-509`, POLL `:894-900`, S `:684-715` | 4 |
| 3.5 | reader: overwritten → oldest, skip and count, ≤ N skips, whole records | `psc.c:976-1033` | 4 |
| 3.6 | in-flight state in stats, W, panel | stats 64-67, W ext, panel line 3 | 4, 14 |
| 4.5 | `durable_tick` vs now, panel when > 750 ticks | `psc_panel.c:317-320` | 14 |
| 10.6 | EPC map, register map | `impl/epcmap.txt`, `impl/regmap.txt` | |
| 10.8 | panel columns | `impl/panellayout.txt` | |
| recon/build.md 1.3 | `CONFIG_INITRAMFS_SOURCE="/work/work/linux/psp-initramfs.cpio"` | `.config:163` | 1 |

Not kernel work (other implementers): the collector `pscol`, the
`rc.sysinit` lines and the initramfs contents (4.2), the decoder (10).
Commit 1 only redirects the build to the work tree's cpio, which is
identical to the original today (sha256 `ba50da6a…fada5`), so this image
still carries the 2008 initramfs without `pscol`.

---

## 4. Deviations from the design (every one, with the reason)

"Touches" names a blocking G1 item where one is involved.

**DV-1 Structure of the Syscon_cmd capture (2.1).** The design puts A1,
the scratch `sc` and the `psc_sc_exit()` call inside `Syscon_cmd`. Here
`Syscon_cmd` keeps only the transaction; a recording wrapper
`psc_syscon_cmd()` (psc.c) runs A1 inline (no call), calls `Syscon_cmd`, then
`psc_sc_exit()`; the three callers in syscon.c call the wrapper. Inside
`Syscon_cmd` the capture slots are locals (`dmy` keeps the S5 load,
`spin` the drain counter, new `dlast`, `st9`, `sttx`, `spin_ack` declared
after the original locals), and the exit label hands them over through an
opaque asm (memory operands only; it saves and restores every register it
touches) to `psc_xfer_out()`, which stores them in a per-origin static area
(P thread, W Nop, M other) that `psc_sc_exit()` reads.
*Reason:* with gcc 4.2.1 every visible addition inside `Syscon_cmd` changed
the allocation inside S5..S20, measured on the object code: inline A1 and a
C call at the exit permuted most registers and stopped `0xbe240024` being
held in a register (a base-address reload in the window); extra locals
declared before the original ones, or the kernel headers included before the
function, swapped two instructions in the receive loop; a C store at the
exit label swapped t3/t4; register operands to the exit asm did the same.
The structure above is the one that leaves the window as close to the
baseline as found (DV-4). *Touches D10 only in the direction of keeping it.*
The A1 work, cost and position (before the transaction) are as designed;
the wrapper adds a call and about 280 bytes of stack on the Nop path (72 B
wrapper frame, +8 B in `Syscon_cmd`, 128 B for the hand-off, `psc_sc_exit`).
*EPC consequence:* the wrapper and `psc_sc_exit` are labelled ENTRY/REC
(both P0) in `epcmap.txt`.

**DV-2 A2 reduced to one store.** Per attempt only `spin = 0` is stored (the
design stores `spin`, `spin_ack`, `dlast`, `st9`, `sttx`). The other
sentinels are derived in `psc_fill_sc` (psc.c:259) with the same values:
`ack_polls` = 0xFFFFFFFF ("not reached") when `ret` is −3 (the only exit that
does not reach the ACK loop); `spi_st9` = `spi_sttx` = 0 on −3; `drain` = 0
when `spin` is still 0, and `drain_last` = 0 when `drain` = 0. *Reason:* each
store in the retry loop changes gcc's register choice in the window (DV-4).
One corner differs: a drain that pops exactly 1,000,000 words and then finds
the FIFO empty reads `drain` 0 instead of 0xFFFF (the −3 bound fires at that
count; physically impossible with a FIFO).

**DV-3 nwords (A4). NEEDS A DECISION — touches D3.** The design takes
`nwords = (ptr − rx_buf) >> 1` after S20 and counts it as costing nothing
inside the window. Measured: any C use of `ptr` or `i` after the receive loop
makes gcc keep the pointer's value in the loop: **+2 instructions per
received word inside S18** (`move v1,a3` and `addiu a0,a3,-2`), and the
`i` forms rebuild the loop with more instructions. Information-theoretically
the baseline loop cannot give the count at zero cost: a loop that broke after
7 words and one that ran all 8 leave identical registers once S19
(`li v0,4`, `lui v1,0xbe58`) has run; only `rx[14..15]` differs, and not when
the 8th word is 0xFFFF. **Implemented:** the exit hand-off copies the receive
loop's counter register `t0` (= i + 2; the window is unchanged, so its
registers are the baseline's) and `psc_fill_sc` reports k = (t0 − 2)/2 for
t0 < 16; for t0 = 16 it reports 8 unless `rx[14] = rx[15] = 0xff`, then 7.
**Exact except one case: 8 words whose last word is 0xFFFF are reported as 7.**
The record stays self-describing (`nwords = 7` with `rx[14..15] = ff ff`
means "7, or 8 with the last word 0xFFFF"; the raw bytes are identical either
way). `d10_proof.py` checks for this build that no instruction on any path
from the loop to the hand-off writes t0 or t8. Options for the decision:
(a) accept as implemented; (b) exact nwords at +2 ALU instructions per
received word inside S18 (≤ 16 instructions, ≈ 70 ns per command; breaks the
7.2 "0 instructions in the window" claim); (c) exact nwords at +1 instruction
on the 8-word exit edge only (needs hand-written code in the window). I did
not choose (b) or (c) because the computed task makes zero added
instructions in S5..S20 non-negotiable and D10/7.2 rest on it.

**DV-4 Window identity.** The window is identical to the baseline's apart from
stack offsets, a consistent renaming s3→s7, s4→s3, s5→s4, s6→s5, s7→s6, and
the delay slot of the first −3 exit (baseline: an epilogue restore pulled
into it; new: `nop`; executed after the exit decision). The renaming is
caused by the per-attempt A2 store (DV-2): every placement and form of it
tried (C store at `retry:`, after the checksum, after the prefill, in the
retry path, as an asm with a memory operand, as an initialiser) produced a
rename; without any A2 store the window is identical apart from stack
offsets, but then `drain` of an attempt that skips the drain loop would be
undefined. The design's G2 criterion (2.1: same MMIO loads and stores in the
same order, loop bodies with the same instruction counts, no added calls,
global loads or base-address reloads) is met; the computed task's stricter
"identical apart from stack offsets" is not, and only by register names, which
change neither instruction count, dependencies nor timing on this in-order
core. *Touches D10 (blocking)*: in my reading it is met; the G2 reviewer
decides.

**DV-5 Order inside `psc_sc_exit`.** Exit time, `wd_calls`, the W head,
`led_calls` and `nivcsw` are snapshotted first, then `t_busy_p`/`t_busy_m`
is cleared, then the record is filled and published (the design lists
"clear psc_t_busy_p" after publishing). *Reason:* a Nop, LED operation or
preemption then falls either before both the snapshots and the cleared flag
or after both, so W `t_busy`/`p_head` and the record's `wn`/`w_head_lo`
agree, and the `lc`, `led_cmd` and `pre` words cannot change for this
`cmd_id` while they are copied.

**DV-6 T1 split.** Only `mfc0 $9` runs before the Count reset (one
instruction, the design's "the reset moves 1-2 instructions later"); the
accounting (`total_counts`, `c_pre_max`, `long_ticks`) runs in
`psc_tick_hook` after the reset with the same `c_pre`. The current tick's
`c_pre` is also stored for the W extension (`psc_k.c_pre_cur`) before
`psp_watchdog_tick()`.

**DV-7 `psp_watchdog_tick` code.** The watchdog's own instructions
(increment, compare with `lastTick`, update) are unchanged; the compiler
interleaves the T1 store and the address of `psc_mem` with them, and the
Nop branch gains the two `wd_ctx` stores the design asks for. Listing in
section 6 (C7).

**DV-8 "EPC inside Syscon_cmd"** (SC `lc_flags` b2, W `ext_flags` b3) is the
range from `Syscon_cmd` to the next syscon.c function in the link, computed
once on first use (psc.c:95-127). gcc no longer emits syscon.c in source
order (`Syscon_wait` now follows `Syscon_cmd`), so no fixed neighbour is
used. The wrapper and `psc_sc_exit` are outside the range (ENTRY/REC, P0).

**DV-9 W record lc fields.** For W records all of `lc_*`, `led_or`,
`led_pid` are 0, including `lc_dtick` (1.3: "its lc_*, led_or, led_pid are
0"), although 1.2 defines 0xFFFF as "none" for `lc_dtick`. `lc_flags` b0 is
0, so the record says the lc words are not valid. P records without lc use
0xFFFF; M records too.

**DV-10 POLL `stage_max`** is the highest stage below 17 reached in the
iteration: stage 17 (before `msleep`) is reached by every record, so
including it would make the field constant. Stats `jp_stage` and W
`jp_stage` do take 17.

**DV-11 `qfree_stage` 3** is written when the `down(list_sem)` at :353
succeeded (before `list_del`); a failed down goes from 2 to 5. A closer
blocked inside :353 stays at 2, the H9 signature.

**DV-12 `build_id` (stats word 2), not defined by the design.** Implemented
as zlib CRC-32 (initial 0) of `linux_banner`, i.e. of the exact bytes of
`/proc/version` and of the build's `work/out/<stamp>/banner.txt` (both end
in "\n"). Computed once in `psc_init` (psc.c:1221). For this build: `0x27c67583`
(zlib CRC-32 of the 102 bytes of `out/20261006T012834Z/banner.txt`, equal to
the NUL-terminated `linux_banner` string in `vmlinux.bin`). The collector's KRN check and
the decoder (10.1) must use the same definition; the interface implementer
flagged this as open.

**DV-13 Panel details (2.10).** Lines are fixed to 40 columns with short
labels (`panellayout.txt`): `DUR`/`RDR` ages as "ddd.d" (whole seconds above
999.9), `PNT` mod 100000; line 2 preempt count 8 hex; line 6 sector 7 hex,
pid 4 digits, start tick low 20 bits, `fat_panics` capped 9, `META` followed
directly by the sector. The clearing paint is counted in `panel_paints`,
`panel_last_tick`, `panel_cost_*` and sets `panel_cmd_id` like any paint
(it is interrupts-off time too, which N1p must see).

**DV-14 Guard words** are written and armed in `psc_init` (late_initcall),
before any userland; a stray store before that is not detected. The design
does not say when they are set; BSS is zero at boot.

**DV-15 Hook S cost.** The inline gate loads `wk_pending` and `pre_on` and
compares `prev` with `psc_jp_task` (three loads, two compares per switch;
the design counts "one load and one compare"). `psc_tick_hook` is a call per
tick (≈ 6 instructions of call overhead over the design's ≈ 16).

**DV-16 "PSC TEST band at init"** (named in the Stage 2 task text) is not in
DESIGN: the panel test is requested by the collector through `ctl` op 3
(2.8, 2.10, 8.2). No kernel-initiated band at init was added.

**DV-17 Timeout patch text (C2).** All five hunks of
`work/syscon-timeout.applied.patch` no longer reverse-apply, because new lines
sit in or next to their context (the hand-off macro after `REG32`, the slot
declarations after `retry_cnt`, the −3/−4 `goto out` the design specifies,
the `out:` label before `return`). The behaviour is unchanged: the same
defines (`SYSCON_SPIN_MAX` 1000000, `SYSCON_RETRY_MAX` 16), the same `spin`
and `retry_cnt` declarations, the same bounds (`spin-- == 0`,
`spin_ack-- == 0`, `++retry_cnt < 16`), the same teardown writes before −4 in
the same order, the same return values; the hand-off between the exit label
and `return result` restores every register. The −3/−4 paths are in the
window proof (identical apart from the renaming).

**DV-18 `ctl` input checks.** Op 2 with slot ≥ 8 and op 3 with seconds outside
1..10 return −EINVAL; a write of several commands stops at the first bad one
and returns the bytes of the commands applied. Op 1 writes `durable_next[5]`
before `durable_tick`; op 4 writes `meta_tick` before `meta_sector`.

---

## 5. D10 proof

`impl/syscon-window-diff.txt`, written by `impl/d10_proof.py`
(baseline `work/prebuilt/vmlinux`, the original 2026-09-22 image, against
`work/out/20261006T012834Z/vmlinux`; both disassembled with the tree's
`mipsel-linux-uclibc-objdump` in the container). Method: every instruction
on a control-flow path from S5 (the load of `0xbe240004`, syscon.c:102) to S20
(the GPIO3-low store, syscon.c:222), including the −3 and −4 exits up to the
point where they leave the transaction, listed depth-first from S5, so code
layout does not matter; stack offsets normalised.

```
S5 .. S20: baseline 880ceeec..880cf0bc, new 880cefb0..880cf278
instructions on S5..S20 paths incl. the -3/-4 exits: baseline 105, new 105
identical apart from stack offsets: NO
identical apart from stack offsets and a consistent register renaming: YES
register renaming (baseline -> new): s3->s7, s4->s3, s5->s4, s6->s5, s7->s6
non-stack loads/stores (MMIO and buffers) in the same order and form: YES
calls inside the window: baseline 0, new 0
exit hand-off checks (t0/t8 unwritten between the loop and the hand-off;
slot offsets): PASS
```

The five renamed registers hold `0xbe24` (the −4 path's base),
`0xbe240004`, the constant 8 (twice) and `0xbe240008`. The capture slots are
`0(sp)` (S5, as the baseline's `dmy`), `2(sp)` drain word, `4(sp)` S9 status,
`6(sp)` TX status, `8(sp)` drain counter (as the baseline's `spin` at
`4(sp)`), `12(sp)` ACK counter: each an `sh`/`sw` where the baseline had
`sh v0,0(sp)` or the `spin` load-modify-store on `4(sp)`. The only added
instruction before S5 is the per-attempt `sw zero,8(sp)` at `retry:`
(`880cef4c`, outside the window); everything else added is after S20 or in
the wrapper.

---

## 6. G2 checklist evidence (implementer's view; the reviewer re-checks)

**C1 Conformance.** Records are written through the `psc_format.h` structs
(`check_format.py --cc` passed on the header, interface commit); every field
of 1.2-1.7 has a writer (section 3). `/proc/psc` names, ctl ops, the printk
format and ring sizes come from the header.

**C2 Diff confined.** Every changed line is in section 3 or 4. The driver
logic is untouched: joypad, MS and LED code keep their statements in order
(the LED read-modify-write is the same single load and store); the one
restructuring in the joypad thread loop places stage 4 in both branches of
the unchanged `if`. Timeout patch: DV-17.

**C3 Context safety.**

| Hook | Context | Why it cannot sleep or deadlock |
|---|---|---|
| A1, `psc_sc_exit`, hand-off | caller's (thread, Nop IRQ-off, boot, M thread) | plain loads/stores, `memset`/`memcpy`; no lock, no call that sleeps |
| T1, T2 (`psc_tick_hook`, T2d, panel) | timer interrupt, IE off, before `irq_enter` | stores to BSS and VRAM, `pspClearDcache()` (cache ops only) |
| LED hook | MS path inside `__bio_kmap_atomic` (preemption off) | stores only |
| S record, marker | MS path under `s_psp_ms_rw_sem` | stores only |
| hooks W, S | `task_rq_lock` / `rq->lock` held, IE off | stores, `psc_class` (8 loads), arithmetic |
| thread, fops, `queue_free`, vcs, mousedev, `do_exit`, `wb_kupdate`, vfat | the calling process | counters; no new lock |
| `/proc` read, llseek, ctl write | collector, process context | `copy_to_user`/`copy_from_user` with no lock held |

Single writer per ring: P and POLL the thread, W the Nop (IE off) and the
boot Nop, S the MS path under its semaphore, M other threads (fill-once,
not known to be concurrent, 3.4). A record interrupted mid-write keeps
`seq = 0xFFFFFFFF` until published, and the reader checks `seq` before and
after copying. One printk (psc_init). No interrupt masking, lock or delay
anywhere. No new MMIO read (D11): the only new memory-mapped accesses are
VRAM stores by the panel.

**C4 Bounds.** Ring index `s & (N−1)` (N a power of two, asserted in the
header); M ring `s < 64` checked; reader: `*ppos` must be a multiple of the
record size (−EINVAL), overwritten records → oldest valid, at most N skips,
stops before exceeding `count`, returns whole records, sets `*ppos` only;
stats read bounded by 768 and `*ppos`; ctl requires `count % 32 == 0`, slot
< 8, seconds 1..10; `rx` copies 16 bytes; `nwords` ≤ 8; `retries`, `wn`,
`ms_delta`, `preempt_delta`, `lc_n`, `led_ops`, `nsect` saturate to their
widths; the panel line formatter never writes past 40 characters and the
font index is 0..38; the hand-off writes inside its own 128-byte frame.

**C5 Boot.** Everything lives in the BSS object `psc_mem` (zeroed by
`head.S`), so the boot Nop in `prom_init` (origin WB, before the scheduler,
the timer, any initcall) records into W seq 0; nothing needs `psc_init`
before the first record. `psc_init` (late_initcall, before userland) only
arms the guards, computes `build_id`, creates `/proc/psc` and prints the
boot line. Scheduler hooks compare with `psc_jp_task` (NULL until the
thread starts); T2d paints nothing before a ring file is opened.

**C6 Clean build.** By the verifier; the implementer's build is section 1.

**C7 Symbols.** `System.map` of the build: `Syscon_cmd` 880ceed0,
`psc_syscon_cmd` 880d3420, `psc_sc_exit` 880d2b04, `psc_xfer_out` 880d1e3c,
`psc_tick_hook`, `psc_note_led`, `psc_ms_seg_begin/end`,
`psc_sched_wake_slow`, `psc_sched_switch_slow`, `psc_poll_begin/end`,
`psc_panel_t2d`, `psc_mem` (B, 653,584 bytes). Capture call sites in the
object code: the three syscon.c callers `jal psc_syscon_cmd`;
`plat_irq_dispatch` `mfc0 s2,$9` one instruction before `mtc0 zero,$9`,
`sw s2` to `c_pre_cur`, then `jal psc_tick_hook` after the watchdog block on
both paths; `psp_led_ctrl` load/or/store then `j psc_note_led`; the
exit hand-off `jal psc_xfer_out` inside `Syscon_cmd` at 880cf17c.

**C9 Endianness and packing.** From the header (packed, aligned(4),
asserted); the kernel adds no format.

**C10 Each commit builds.** See section 6a.

### 6a. Per-commit build

Each commit of the series checked out in a scratch clone and built with
`make ARCH=mips CROSS_COMPILE=mipsel-linux-uclibc- -j16 vmlinux` in the same
container as `build.sh` (the clone mounted at `/work/work/linux` so the
initramfs path of commit 1 resolves). Every one compiles and links. The
"warning lines" column counts lines containing "warning" in that build's log;
every build after the first recompiled the whole tree and shows the same 33
(the first also built the host kconfig tools, 7 more).

| Commit | Result | Warning lines |
|---|---|---|
| `ca7dac0a` | make exit 0 | 40 |
| `4c4e7aee` | make exit 0 | 33 |
| `84112996` | make exit 0 | 33 |
| `a109c03b` | make exit 0 | 33 |
| `b2469e76` | make exit 0 | 33 |
| `bd182ffb` | make exit 0 | 33 |
| `d5679835` | make exit 0 | 33 |
| `bcc20c71` | make exit 0 | 33 |
| `a9f70a04` | make exit 0 | 33 |
| `90d275aa` | make exit 0 | 33 |
| `14766616` | make exit 0 | 33 |
| `fa705875` | make exit 0 | 33 |
| `30616d25` | make exit 0 | 33 |
| `90a206b2` | make exit 0 | 33 |
| `0b0a2acf` | make exit 0 | 33 |

### 6b. Floating point and helpers

`objdump -d` of `psc.o`, `psc_panel.o`, `syscon.o`, `psp.o`, `ms_psp.o`,
`joypad_psp.o`, `sched.o`: 0 instructions matching
`$fN|lwc1|swc1|ldc1|sdc1|mtc1|mfc1|cfc1|ctc1|cvt.`; `nm -u`: no soft-float
or 64-bit division helpers (`__*sf*`, `__*df*`, `__divdi3`, `__udivdi3`,
`__muldi3`, …). `vmlinux` has no soft-float symbol. The kernel is built
`-msoft-float`. 64-bit arithmetic in the new code is limited to additions,
comparisons and a 32×32 multiply (`psc_dcount`) and `do_div` by a 32-bit
record size (the arch's inline divide).

---

## 7. Size and memory

| | baseline | this build | change |
|---|---|---|---|
| `vmlinux-0.22.bin` (gzip, what pspboot loads) | 899,402 (`work/prebuilt`, `out/20260927T204324Z`) / 899,404 (`out/20260927T204657Z`) / 899,282 (`pspboot-baseline`, the 2008 image) | **909,168** | +9,766 / +9,764 / +9,886 |
| `vmlinux.bin` | 1,723,228 | 1,739,612 | +16,384 (text +16,660 B) |
| BSS (`size vmlinux`) | 70,192 | 723,792 | +653,600 (`psc_mem` 653,584 + 3 words) |
| `_end` | 881b6230 | 88259b50 | +653,600 |

DESIGN 5.3 bound: ≤ 48 KB growth for each image: met. BSS is not in the
image; `psp_detect_mem_size` starts after `_end` (psp.c), so the ≈ 654 KB
come out of userland RAM (3.1 % of telem's `MemFree`, 5.3). The 190,246-byte
`EBOOT.PBP` is the loader and is unchanged.

---

## 8. For the collector and decoder implementers

- `build_id` = zlib CRC-32 (seed 0) of the `/proc/version` bytes (DV-12);
  0x27c67583 for this build. **To reconcile with the collector and decoder
  notes** (`IMPLEMENTATION-pscol.md`: compile-time `PSC_BUILD_ID`, 0 = not
  checked; `IMPLEMENTATION-decoder.md`: `BUILD_DIR/build_id.txt`): the
  decoder's `build_id.txt` is `crc32(out/<stamp>/banner.txt)`; for `pscol`
  either (a) compute `crc32` of `/proc/version` at run time and compare with
  stats word 2 (no build coupling), or (b) pass `PSC_BUILD_ID` =
  `crc32` of the banner the release build will produce, which is predictable
  only when the release build fixes `KBUILD_BUILD_VERSION` and
  `KBUILD_BUILD_TIMESTAMP` (both supported by `build.sh`), because the
  banner carries the build time and `pscol` is built before the kernel that
  embeds it. Not decided here; the orchestrator should pick one.
- `nwords` 7 with `rx[14..15] = ff ff` means 7, or 8 with the 8th word
  0xFFFF (DV-3).
- W records have `lc_dtick` 0, not 0xFFFF (DV-9); P and M without lc have
  0xFFFF.
- POLL `stage_max` excludes 17 (DV-10).
- `ack_polls` 0xFFFFFFFF ⇔ `ret` −3; `drain` 0 ⇔ no RX pre-drain in the
  final attempt (DV-2).
- `/proc/psc/ctl` returns −EINVAL for bad slot/seconds; partial writes return
  the bytes applied (DV-18).
- Stats words at read: 0-4 constants, 5 `last_reader_tick` (ring reads,
  even of 0 bytes), 7-9 now, 10-11 hi-lo-hi, 14-18 heads, 20-22 addresses,
  56-63 from the thread's task and the two semaphores, 64-67 in-flight, 135
  `ms_rdonly`. All others are the live counters.
- `epcmap.txt` labels: S0 is `retry:` (the per-attempt PSC store); S15
  covers the set-up before the ack store (an EPC there is P5b); the wrapper
  is ENTRY, `psc_sc_exit` and `psc_xfer_out` REC (all P0).
- `regmap.txt`: i and ptr are in t0 ($8) and a3 ($7) at S11 and S16-S18, as
  in the baseline (R10).

---

## 9. What was checked and what was not

Checked here: the build (clean, `build.sh`), the warning set, the window
(object code), the hand-off register assumptions, symbol order, sizes, FP,
the original tree's manifest, each commit compiling. Not checked (no
hardware, no emulator in this stage): any runtime behaviour, the panel's
appearance on screen, the CP0 Count rate, the Memory Stick tag on real
transfers. Stage 3's host tests (8.5) are where the ring, reader, record and
panel code is exercised.
