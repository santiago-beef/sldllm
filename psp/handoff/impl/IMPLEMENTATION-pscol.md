# IMPLEMENTATION-pscol: the PSC collector (Stage 2, userland)

Implementer: userland implementer (Opus 5.5), 2026-10-06. Specification:
`design/DESIGN.md` revision 6 (G1 PASS), sections 4.1-4.8 and 8.2-8.4, with
10.2 for the file format. The record and file format comes only from the
shared kernel header `work/linux/include/linux/psc_format.h` (commit
`ca7dac0a` on `stage2-trace`), included by path. Nothing in the design was
changed. No DOSSIER, WORKFLOW, gate report or design file was edited. The
original tree was only read (`sha256sum -c baseline-tree.sha256`: exit 0,
CHECKS.txt section 5).

## 1. Files (all in `/home/ubuntu/psp/work/pscol/`)

| File | Lines | What |
|---|---|---|
| `pscol.h` | 195 | Internal interface: the `os_*` system-call layer, budget constants, verdict-function prototypes, HUD line model |
| `pscol.c` | 2,909 | Worker (4.3-4.8), HUD and self-test (8.2-8.4), guards (4.2). Host-only test hooks are under `#ifdef PSCOL_HOST` at the end and are not compiled for the PSP |
| `main.c` | 178 | `main` and the supervisor (4.2) |
| `os_target.c` | 174 | The `os_*` layer with the real system calls (uClibc, no stdio, no malloc) |
| `cbuild.sh` | 61 | Container build: bFLT, `flthdr -s 16384`, FP and symbol checks, sizes. Writes `cbuild.out` |
| `checks.sh` | 60 | Regenerates `CHECKS.txt` (target build, host tests, sanitizers, decoder cross-check, manifest) |
| `rc.sysinit.patch` | | The three `rc.sysinit` lines of 4.2, as a unified diff against `extract/root2/etc/rc.sysinit` |
| `test/sim.c` | 1,445 | Host harness: a simulated kernel, vfat and Memory Stick with fault injection, plus the end-of-run decoder check |
| `test/vectors.c` | 219 | The 8.5 S-record verdict vectors and the 8.5 HUD render test |
| `test/xcheck.py` | 37 | Cross-check: simulated stick files parsed by `decoder/pscdec_parse.py` |
| `test/run.sh` | 12 | Builds and runs the host tests |
| Outputs | | `pscol` (bFLT, 55,044 B), `pscol.gdb` (ELF for objdump), `pscol.dis`, `cbuild.out`, `CHECKS.txt` |

How to build: `sudo docker run --rm --platform linux/386 -v /home/ubuntu/psp:/work:ro -v /home/ubuntu/psp/work:/work/work psp-build:bullseye bash /work/work/pscol/cbuild.sh`.
Everything at once: `/home/ubuntu/psp/work/pscol/checks.sh [IF4 seeds per speed, default 50]` (about 2 minutes).

## 2. CHECKS.txt summary (2026-10-06 01:13 UTC)

| Check | Result |
|---|---|
| COMPILE_OK, gcc 4.2.1 `-Wall -W` | yes, **0 warnings** |
| FP_REGS_USED (`objdump -d pscol.gdb \| grep -c '[$]f[0-9]'`) | **0** |
| FP mnemonics (add/sub/mul/div/abs/neg/mov/sqrt.s/.d, lwc1, swc1, ldc1, sdc1, mtc1, mfc1, cfc1, ctc1, cvt.) | **0** (and the 7.7 grep: 0) |
| `nm` for printf, strtod, atof, soft-float (`__*sf*`, `__*df*`), libm | **none** |
| `nm` for malloc, calloc, realloc, free, opendir, fopen / fork | **none / none** (vfork + execve only) |
| `flthdr` | bFLT rev 4, Has-PIC-GOT, **Stack Size 0x4000 (16,384, set with `flthdr -s 16384`)** |
| Sizes | text 51,904; data 2,896; bss 112,720; bFLT file **55,044 B** |
| Allocation per process | text + data + bss + stack = 183,968 B → **one 256 KB kmalloc block each** (deviation 1) |
| fadvise call | objdump: `a0=4254, a1=fd, a2=0, a3=off, 16(sp)=0, 20(sp)=len, 24(sp)=0, 28(sp)=4` through `syscall()`, which shifts them to the o32 seven-slot layout (4.4 step 7, 7.4, R23) |
| `pread` | uClibc `__libc_pread` → `pread64` (4200) with the 64-bit offset in the even pair, correct for o32 |
| Verdict vectors (8.5) | **28/28 PASS**: every listed vector of "S-record verdicts" (including the three r7 own-entry vectors, the pdflush-before-own case, the skipped seq and the wrong partition offset) plus nine extra edge vectors |
| HUD render (8.2, 8.5 N-2) | **PASS**: 11 forced states with maximal field widths; longest line 34 characters; no text pixel at x ≥ 428 in rows 8-39 or in rows ≥ 168 |
| Nominal 5 min, 52 KB/s, HUD on, TRIANGLE pressed | **PASS**: SELFTEST PASS (all 8 bits); exactly 272 fb writes per tick, none in rows ≥ 176; every chunk type present; 0 records missing |
| **3 s write-error burst during step 0** (file 1 at start-up and file 3 mid-run; 25/52/100/300 KB/s) | **8/8 PASS**: the hit file is abandoned; the next attempt meets the alias of its inode, rejects it, and creates a fresh file 7.1-7.4 s after the stick recovers (bound: 10 s + 1 tick); no alias written; no record missing |
| **IF4 sporadic** (Poisson whole-tick failures, 98 per 30 min, 30 min, 50 seeds per speed) | **200/200 PASS** at 25, 52, 100 and 300 KB/s: 0 records missing below `durable_next`, 0 violations, 82-119 FAILED verdicts per run, longest hold 9.5 s. SELFTEST passes at 52-300 KB/s; at 25 KB/s it fails on `MS SLOW` as designed |
| **IF7b own-entry vectors** | in the vector table above (all PASS) |
| IF7b scenario (extra): the PSCLOG directory sector refuses every write from 60 s, 25 min | **PASS**: META in 1.4 s; the first fresh file 13 collector ticks after the first attempt with 105 names (design: ≤ 20 ticks, ≤ 153 names); later creations ≤ 14 names (≤ 17); nothing lost; META cleared as "bypassed" and re-detected, as 4.7 says |
| **TE10 hold-and-resume** (100 s backlog, the active file still in creation; (a) a step and its first retry fail, (b) a 3 s burst at a step; 25/52/100 KB/s) | **6/6 PASS**: holds in the same file (1.1-13.5 s) and resumes at its own `seg_end`; `seg_end = 1,536` never reused in a file that was active; no flush region written twice; boot records intact |
| ASan + UBSan, all host tests | **clean** |
| Decoder cross-check (the analyst's `pscdec_parse.load()` on the simulated stick) | **3/3 PASS** (nominal; step-0 burst; IF4 at 25 KB/s): nonce matches; every record below `durable_next` decoded; 0 conflicts; 0 chunks above the confirmed extent; the raw-image rule fires exactly in the error runs |

What the harness checks in every run: no write through an alias; no flush
extends a file or lies over a cluster whose FAT link failed; no flush region
is written twice and no step writes over a flush; every flush is 512-aligned
and ≤ 40,960 B; holds ≤ 114.7 s; the worker counted no lost record; at the
end every record with `seq < durable_next` is on the simulated stick (decoded
by CRC with the nonce), `durable_next` is ≤ 5 s behind, and the W seq 0 (WB),
P seq 0 and M seq 0 boot records are present.

## 3. Design section → code

`pscol.c` unless named. Line numbers are those of the files as delivered.

| Design | Mechanism | Code |
|---|---|---|
| 4.1, 7.4 | Derived from telem: font, integer formatting, mouse client, 272-row blit, `syscall(__NR_syslog)` | `pscol.c:2326-2357` (font), `:227-266` (formatting), `:2008` (mice), `:2604` (blit); `os_target.c:110`, `:139`, `:149` |
| 4.2 supervisor | setsid, `/dev/null` on 0-2, ignored signals, `mkdir PSCLOG` if missing, run number, boot nonce, vfork + execve, 2 s waitpid and stats read, takeover on death/guard (exit 3) or 30 s stall | `main.c:105` (supervisor), `:115`, `:125`, `:127`, `:72` (run_scan), `:131` (nonce), `:145-149` (vfork/execve), `:157-168` (watch, takeover) |
| 4.2 takeover | The supervisor runs the worker loop in-process as instance 2, same run and nonce, no exec, no allocation | `main.c:151`, `:161`, `:167` → `pscol.c:2815` (`worker_main`) |
| 4.2 worker start | Console level 4 by the kernel syslog call, EVENT `conlevel`; ring files seeked to `durable_next`; names budget; pid classes (ctl op 2); template; fb, mice | `pscol.c:2622` (`worker_init`), `:2660`, `:2189` (`krn_attach`), `:2095` (`names_scan`), `:2143` (`classes_register`) |
| 4.2 guards | 16-byte patterns between every buffer and around data; one asserting read helper; stack pre-fill and high-water; `guard ok stack_hw=`; violation → EVENT, last flush, `_exit(3)` | `:292` (`guards_check`), `:307` (`xread`), `:332` (`stack_fill`), `:277` (`guard_violation`), `:2777` (`emergency_flush`) |
| 4.2 "never" | No `/dev/joypad`, no tty, no `statfs`, no truncate/unlink/reopen, never writes through an alias | by construction (no such calls; `nm` and grep confirm) |
| 4.3 step 1 | Snapshot: one stats read, heads, `drain_tick`, S window start | `:2696` (`worker_tick`), `:415` (`stats_read`) |
| 4.3 step 2 | Capped drain W, P, POLL, S, M with `m`; re-send block first; one new-records block per ring; complete, catch-up, stuck, head regress, lost; REC alarm | `:862` (`drain`), `:908`, `:971`, `:995` |
| 4.3 steps 3-6 | KMSG (`/proc/kmsg`, non-blocking), load-parity syslog type 3 into 16 KB, PROCS every 40th tick, mice, meminfo/uptime | `:1996`, `:2033`, `:2008`, `:1972` |
| 4.3 step 7 | Flush: RECS, UHB, STATS every 8th, PROCS, KMSG/EVENT if ≤ 40,960, PAD to 512; `lseek`, one `write`, `fsync`, timed; `seg_end` advances whatever the result | `:1789` (`flush`), `:1861` |
| 4.3 step 8 | Creation step, META, bad-region rule | `:1719` (`creation`), `:1173` (META), `:1911` |
| 4.3 step 9 | HUD: 10 lines, 272 writes of 1,920 B, rows 0-175 then 0-95 | `:2604` (`hud_draw`), `:2458`, `:2564` |
| 4.3 step 10 | Guards, then `nanosleep(200 ms)` | `:2769-2770`, `:2822` |
| 4.3 Bounds | 40,960-byte flush buffer; KMSG/EVENT only if the padded flush still fits; EVENT queue 8 KB with `events dropped <n>` | `:1828` (`FITS`), `:366` (`ev`) |
| 4.4 step 1 | `open(O_CREAT\|O_EXCL)`, EEXIST → next; alias test (`st_size` or a seen `st_ino`) → EVENT `inode reused`, UHB b28, close; same-tick loop ≤ 24 opens while the stick works; probe `fsync` of the first alias otherwise | `:1492` (`create_attempt`), `:1538-1566` (alias), `:1552` (probe) |
| 4.4 step 2 | Step 0: FILEHDR + PAD = 1,536 B at offset 0, `fsync` | `:1418` (`step0`) |
| 4.4 step 3 | PAD-sector steps from the 4 KB template; 64 KB while holding or room < 81,920, else 8 KB; last step stops at SEG; `fsync` always | `:1637` (`do_step`), `:1590` (`choose_k`), `:494` (template), `os_target.c:48` |
| 4.4 step 4, 4.8 | Step verdicts: FAT part, then FIBMAP of the new clusters, then data, `fstat`, step 0's own entry (r7 A6-1); retry in place ≤ 3, fourth failure stops; FAT1 failure stops; step 0 never retried | `:637` (`judge_step_fat`), `:658` (`judge_step_data`), `:1365` (`fibmap_new`), `:1663` |
| 4.4 step 5 | Stopped: prefix-usable (≥ 42,496) or abandoned (EVENT, b17, line 7 WAIT, closed) | `:1296` (`seg_stop`) |
| 4.4 step 6 | Next attempt: next tick if the failed window had a successful write (≤ min(400, budget/2) such), else ≥ 10 s; names budget from the free slots | `:1272`, `:2095` |
| 4.4 step 7 | Completion: `fstat`, `fadvise64_64` through syscall 4254 with seven slots, `pread` of the last 512 B against the PAD sector, `ms_seg_rd` check | `:1603` (`seg_complete`), `os_target.c:99` |
| 4.4 step 8 | Cap: confirmed bytes of complete and prefix-usable files ≥ 64 MB stops creation | `:1704` (`should_create`) |
| 4.4 creation rule | One file at a time, while fewer than two complete files wait ahead | `:1704` |
| 4.4 Use and switch | Flush only while `seg_end + 40,960 ≤` usable limit; switch to the oldest never-active complete, prefix-usable or in-creation file with room; **(r7 TE10)** a once-active file is never a target; `seg_end = 1,536` only for a never-active file; an active file still in creation holds and resumes in place; hold = zero-byte reads, EVENTs, b0 | `:1730` (`target_select`), `:1737`, `:1741`, `:1764`, `:872-876` |
| 4.5 | `durable_tick` = drain tick only on a complete drain with an empty re-send queue; `durable_next[r]`; ctl op 1 after each DURABLE flush | `:1888`, `:843`, `:459` |
| 4.6 F1(a) | A failed flush is never overwritten; its records are queued by `seq` range (≤ 32, merging), re-sent after the next DURABLE flush, re-queued if the re-send fails; EVENT `resend`; EVENT/KMSG kept until carried by a DURABLE flush | `:1861`, `:803` (`rq_add`), `:908-968`, `:1904` |
| 4.6 fsync error | DURABLE with `fsync` error: b30, `flush meta err` ≤ once per 10 s, line 6 not red | `:1867` |
| 4.6 bad region | Three consecutive FAILED flushes with a DATA error while another write succeeded → retire, EVENT `region bad`, b27, switch | `:1911` |
| 4.6 read-only | `ms_rdonly` or EROFS: line 6 `MS READ-ONLY` red, b21, EVENT, no creation step, flush into prepared files, then hold | `:2726`, `:1719` |
| 4.7 META | A metadata sector whose last 5 writes failed over ≥ 3 ticks while the worker's data writes succeeded in each; ctl op 4, EVENT `meta err <sector> <class>`, b23, line 6 (not red); clear on a good write or when bypassed (60 s unwritten with every flush DURABLE, or for a FAT sector a confirmed allocating step outside it) | `:1173` (`meta_record`), `:1050`, `:1147`, `:1162`, `:1677-1684` (FAT bypass), `:2760-2762` (60 s bypass) |
| 4.8 | Sector classes from the stats geometry; S windows by `pread` (drain position untouched); a skipped seq makes the operation FAILED; flush verdict; geometry self-check; "stick working" | `:507`, `:527`, `:734` (`win_load`), `:778` (`win_take`), `:608` (`judge_flush`), `:702` |
| 4.8 Speed | First two CONFIRMED 64 KB steps → KB/s, EVENT `speed` | `:1349` (`speed_note`) |
| 8.2 HUD | Exact strings of the ten lines, colours, `IN`, `DELIV`, `MOUSE ON/OFF`, `MS` line states, `MS PREP nnnS nnnKB/S` | `:2401` (`ms_line`), `:2458` (`hud_build_lines`), `:2564` |
| 8.2 self-test | KRN, WDOG, STICK, REC, PANEL (ctl op 3, 5 s, ≥ 3 paints within 6 s), SUP, POLL (`POLL:RATE/RET/NW0`), BTN; second `PSC TEST` when the six are first green; UHB b1-b8 | `:2215-2228`, `:2230` (`selftest_update`), `:1075` (`record_scan`), `:2256`, `:2269` |
| 8.4 | `DEAD?` display-only hint | `:2278` |
| 10.2 | Chunk header and CRC with the nonce (FILEHDR plain), PAD, UHB 21 words, FILEHDR payload, RECS blocks, EVENT lines, PROCS lines | `:469` (`chunk_put`), `:1789-1846` (flush chunks), `:1418-1447` (FILEHDR), `:2293` (`uhb_flags`), `:2315` (`uhb_seg`), `:2033` |
| rc.sysinit (4.2) | Three lines after the `pspmd -s&` block | `rc.sysinit.patch` |
| 7.7, G2 C8 | FP, symbol, `flthdr` checks | `cbuild.sh` |

## 4. Deviations from the design, with reasons

None touches a blocking G1 item (D1-D14) as far as I can judge. Items 1 and
2 change a figure or a system-call name, not a mechanism. The reviewer
should check 4, 5 and 10.

1. **Memory: one 256 KB block per process, not ≤ 128 KB (4.2, 5.3, U1, G2 C8 figure).**
   This kernel forces `FLAT_FLAG_RAM` for every bFLT (`fs/binfmt_flat.c:471-472`, `CONFIG_SONY_PSP=y` at `.config:50`), so the text (51,968 B with header) is in the same `kmalloc` as data + bss + stack (`:627`). The design's own buffer list (40 KB flush, 16 KB syslog, 16 KB stack, 4 KB template, 4 KB KMSG, 8 KB EVENT queue, extent tables) already needs about 100 KB without text, so ≤ 128 KB cannot be met on this kernel. Data + bss + stack is 132,000 B; with text 183,968 B → 256 KB per process, **512 KB for both**, against telem's 1 MB. Both blocks are still allocated at boot, and **nothing is allocated after boot**, so the IF2 closure (U1) is unchanged. The extent tables are 9.2 KB (6 files × 128 runs × 12 B), not ≈ 6 KB. With the block at 256 KB anyway, I did not trim them.
2. **Creation steps use one `writev()` instead of one `write()` (4.4 step 3).** The design asks for `k` bytes (up to 64 KB) "with one write()" from a 4 KB template. `writev` with 16 copies of the template is one system call, the same `generic_file_aio_write` path, the same `i_mutex` and the same page-cache effect, with no 64 KB buffer. All PAD sectors are identical, so the bytes are exactly those of a 64 KB `write`.
3. **"A step allocates" is evaluated only on a step's first attempt (4.4 step 4).** Applied to a retry in place, the offset formula would demand a FAT1 write in the retry's window. A retry never makes one: the design itself says the retry "allocates nothing" because the failed attempt's FAT check had passed. The first build stopped growth on every retry. **The TE10 harness found this, and it is fixed** (`:1663`).
4. **Allocating step with no successful FAT1 record, or with a skipped `seq` in its window → growth stops (4.4 step 4).** 4.4 says only that a failed FAT1 write stops growth. "At least one succeeded if the step allocated" is a CONFIRMED condition, and the design leaves open what failing it means. I chose stop: a missing or hidden FAT1 write may hide an unlinked cluster, and the rule is "never extend after a failed allocating step". A skipped `seq` in a non-allocating step gives a retry in place; in step 0 it gives an abandon.
5. **STICK requires *a* DURABLE flush, not literally *the first* (8.2).** A single sporadic failure on the very first flush would otherwise leave STICK red forever and abort a good run at 3:00. What STICK proves ("data reaches the stick … and the kernel knows how far") is unchanged: geometry self-check, `durable_tick` published, speed ≥ 30 KB/s, names budget ≥ 400.
6. **The "3:00" HUD states (`MS NO STICK`, `MS SLOW`, `MS DIR FULL`) appear from kernel uptime 170 s (8.2 line 6).** The collector cannot see the operator's stopwatch. 8.3 assumes ≈ 10 s of pspboot loading before uptime 0. Until then line 6 shows `MS PREP`. If the load is shorter, the state appears a few seconds after 3:00, and STICK is red at 3:00 either way (an abort).
7. **WDOG for instance 2:** the WB sub-check counts as passed when the takeover instance starts with `durable_next[W] > 0`, because W `seq` 0 was already durable before it started and is not read again.
8. **`DEAD?` "HOLD for 2 s outside the reference step" (8.4)** is implemented as HOLD (`ri_branch` 4) for 2 s. The collector cannot know when C0 runs. The hint is display-only.
9. **Extra EVENT strings**, all ASCII lines like the listed ones: `ctl err <op> <errno>` (a failed `ctl` write also turns KRN red: C8, every write's return shown); `fadvise <ret> <errno>` (R23: "the worker checks the return"); `names exhausted <n>`; and `abandon <name> <errno> 0 open` for a failed `open`. `catch-up start/end` is spelled as in 10.2.
10. **Conservative bounds the design does not state:** a verdict window holds ≤ 256 S records, and a larger one counts as skipped (FAILED); at most 6 segment files are open, and creation pauses while all 6 slots are in use (no test reached 4); at most 16 metadata sectors are tracked for META (LRU).
11. **Undefined UHB fields given a definition:** `bytes_synced_total` = bytes of DURABLE flushes + CONFIRMED steps; `lag_max` = largest `now − durable_tick` seen, in ticks; `max_tick_ms_60s` = largest loop period in 60 s, also shown as line 6 `TMAX`; `last_write_ms` is the last flush's or step's `write` time. Line 10 shows µs as Count / 221 (integer for 220.9), the median over the last 256 P records and the run maximum. `SELFTEST PASS` latches once all eight checks have passed; the eight words stay live.
12. **Names budget slot count (4.4 step 6):** used slots = every `getdents` entry including `.` and `..`, plus ⌈len/13⌉ LFN slots for a name that is not upper-case 8.3.
13. **Supervisor without `/proc/psc`:** the nonce falls back to `gettimeofday` ^ pid, and the worker shows `PSC NO KRN` and retries every tick (4.2).
14. **First drain's `m`:** Δt is counted from worker start, so the first drain after the start-up hold can use `m` up to 4.

## 5. Open items for the orchestrator and the integrator

- **`build_id` (stats word 2) has no definition anywhere.** The header implementer reported the same gap. KRN compares it only when the build sets `PSC_BUILD_ID` (`PSC_BUILD_ID=<u32> cbuild.sh`); the default 0 means "not checked", and `cbuild.out` prints the value used. The decoder's `BUILD_DIR/build_id.txt` and the kernel must use the same definition. **One definition is needed before G2 closes.**
- **Install as `/usr/bin/pscol`, mode 0755** (the supervisor execs that path, 4.2), and apply `rc.sysinit.patch` to the initramfs copy. Per recon/build.md 1.3, `.config:163` must point at the work tree's cpio, or the old initramfs is built in silently.
- **Speed gate calibration (observation, design unchanged).** 4.8 measures speed as bytes / (`write` + `fsync` time) over 64 KB steps, and the `fsync` includes the directory entry, FSINFO and FAT writes. In the 15.6 time model (1 KB per `fsync`), a stick with a raw 30 KB/s measures **28 KB/s** and fails STICK with `MS SLOW`. The effective raw threshold is about 32 KB/s. This is consistent with the text, but the orchestrator may want the reviewer to note it.
- The design inconsistencies in the header report (the RECS bound 34,364 against re-send blocks, and SC bytes 42-46 in 2.11) do not affect `pscol`. The flush fit test uses the padded total against 40,960, which holds for either reading.
- A7-1..A7-3 (design text edits) were not part of this task and are untouched. A7-3, the syslog naming, is implemented as the kernel call: `syscall(__NR_syslog, 3, buf, 16384)` per tick and `(8, 0, 4)` at worker start.

## 6. What is not covered by my tests (for G2 and Stage 3)

- **Not tested on the host:** the supervisor and takeover (`main.c`), the guard exit with `emergency_flush`, and the real `os_target.c` calls. They are checked only by compiling, by objdump (fadvise, pread) and by `nm`. Stage 3's takeover and OE4 rows cover them.
- **The vfat model in `test/sim.c` is a model.** It follows the write order of 4.4 step 4 and the directory-buffer and inode-cache behaviour of 4.4 step 1. It does not model `pdflush` writeback, inode eviction, the Memory Stick driver's ten tries per sector, or FAT-sector re-reads after a failure. The VFAT-FI harness of 8.5 remains the real test of those paths.
- The IF4 runs use the whole-tick failure model only, not the per-operation variant of 15.6.
