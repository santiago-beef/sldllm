# Gate G2, attempt 1: code review

Reviewer: G2 code reviewer (fresh context; not the implementer, integrator or designer).
Date: 2026-10-06.
Artifact: branch `stage2-trace` @ `c135ecdd` in `/home/ubuntu/psp/work/linux` (diffed against `baseline` `775f8372`),
`/home/ubuntu/psp/work/pscol/` (sha256 of pscol.c `6fd80760…`, main.c `61770c8b…`, os_target.c `5e6becf3…`,
bFLT `e5090df3…`, all equal to IMPLEMENTATION.md 5.4), `/home/ubuntu/psp/work/decoder/`,
`handoff/impl/IMPLEMENTATION.md` (+ the three per-implementer notes it cites).
Specification: `design/DESIGN.md` revision 6 as passed at G1 attempt 7, plus the A7-1..A7-3 text edits.

## Verdict: **FAIL**

| Reason | Kind |
|---|---|
| DV-3 (`nwords` inexact: 8 received words whose last word is 0xFFFF are recorded as 7) is a deviation that touches **D3** (blocking G1 item). Forbidden at Stage 2; must go back to G1. | design deviation touching a blocking G1 item |
| C1 FAIL (blocking): the run number `rrr` and the next `nnn` are never found on the real file system (`main.c:87`, `pscol.c:2125`): every boot is run 001 | blocking |
| C1 FAIL (blocking): the decoder cannot read the kernel's `regmap.txt` / `epcmap.txt` (OD-4), so P6 `j` and the LEDSPLIT loaded value are never computed | blocking |

Everything else I checked holds up. The transaction window matches the baseline instruction for instruction, apart from a consistent register renaming. The record formats match DESIGN section 1 field by field in all three places: the C header, the decoder and the design. The ring protocol is safe against the timer interrupt. Boot is safe from BSS. The round-7 segment life cycle is implemented as approved.

---

## 1. Checklist C1-C10

| ID | B | Result | Evidence (summary; details in sections 2-6) |
|---|---|---|---|
| C1 | B | **FAIL** | The formats conform: `psc_format.h` = DESIGN 1.2-1.7 and 10.2-10.3 field by field (section 2), and `psc_format.py` = both (its self-test re-run, exit 0). The capture points conform to section 2 (section 3). The panel condition conforms to 2.10/4.5. The 4.4 round-7 life cycle conforms (section 5). **Fails on**: F2, the run number and `nnn` scans; F3, the decoder/kernel map syntax. DV-3 is routed to G1 |
| C2 | B | PASS | Every hunk of `git diff baseline..stage2-trace` (19 files) is mapped in IMPLEMENTATION.md 4 and kernel notes 2-3. The timeout patch is still present: defines at `syscon.c:12-13` are byte-identical to baseline, and the bounds, return values and teardown writes are unchanged. I re-derived the S5..S20 window with objdump myself (section 4). Driver logic is unchanged: `psp_led_ctrl` is still `lw/or/sw` in the same order, the joypad `if` is unchanged, and `ms_psp` keeps its statements in order |
| C3 | B | PASS | Section 6.1: no sleep, allocation, lock, printk or `copy_to_user` is reachable from the timer path, the Nop path or the scheduler hooks. The append order is invalidate → barrier → fill → barrier → publish `seq` (volatile) → barrier → head (volatile), for P, M, W, S and POLL. The scheduler hooks are O(1): an 8-slot class scan and a 64-bit multiply, nothing else |
| C4 | B | PASS | Section 6.2: indices `s & (N−1)`, M ring `s < 64`, the reader's 3.5 steps 1-5 with `*ppos` only, `rx[16]`, `nwords ≤ 8`. In pscol: drain caps, flush ≤ 37,888 < 40,960, CRC framing, PAD alignment, segment offsets ≤ 2 MB. One minor recount (F6) |
| C5 | B | PASS | Section 6.3: everything lives in one BSS object. The WB Nop in `prom_init` records into W seq 0 with no init function. The panel is guarded by `proc_opens > 0`. The cmdline area pspboot writes (0x88000008) is untouched |
| C6 | B | PASS (reviewer scope) | The release build `build-20261006T021722Z.log` ended rc 0. Its distinct warning set is **identical** to the baseline build's: I compared it with `diff`. `vmlinux.bin` grew +43,631 B and `vmlinux-0.22.bin` +36,919 B, both inside the 48 KB bound. A second clean build of the same HEAD (`build-20261006T022828Z.log`) also ended rc 0. The verifier's own clean build remains the verifier's step |
| C7 | B | PASS | Every capture call is present in the release `vmlinux` (objdump, section 6.4) |
| C8 | B | PASS | `flthdr`: bFLT rev 4, stack 0x4000. I re-ran the FP checks myself and got `$fN` 0, FP mnemonics 0, and no printf/strtod/atof/soft-float/malloc symbols. The only process creation is `syscall 4002`: uClibc's `#define vfork fork` (`staging_dir/usr/include/unistd.h:744`), which this kernel runs as `CLONE_VFORK|CLONE_VM` (`arch/mips/kernel/syscall.c:182-184`), then `execve`. Every flush and creation step is followed by `fsync`; FAILED verdicts turn the `MS` line red and increment `ERR`; a ctl failure turns KRN red. No tty read; stdin is `/dev/null`. The cpio committed in `c135ecdd` has `pscol&` right after `pspmd -s&`, which I checked by extracting it myself |
| C9 |   | PASS | Little-endian only (`#error` on big-endian). `packed, aligned(4)` with 200+ static offset asserts. The decoder's `'<'` strings equal DESIGN 10.3 character for character, and its `calcsize` values equal 80/208/40/40/84/44 |
| C10 |  | PASS | One concern per commit, with readable messages. I checked by reading: the first commit is header only (included nowhere, so it builds trivially); the `.config` commit changes one path and the cpio exists in the tree; the last commit changes only the cpio and was built twice (rc 0). The implementer's section 6a table covers the rest. Provenance note F7 |

Rule check: one blocking item FAILs (C1), there are no non-blocking item FAILs, and one deviation touches a blocking G1 item. **Verdict FAIL.**

---

## 2. C1: the record format, field by field

### 2.1 `include/linux/psc_format.h` against DESIGN section 1

I compared every member against the DESIGN table row (offset, type, name) and confirmed each one with the header's own `PSC_ASSERT_OFF` lines.

- **SC (DESIGN 1.2, 80 B):** all 32 fields match the 1.2 table, including both reserved bytes. Offsets 0 to 78 and types as tabulated:

  | Off | Type | Field |
  |---|---|---|
  | 0 | u32 | seq |
  | 4 | u32 | tick_in |
  | 8 | u32 | c_in |
  | 12 | u32 | c_out |
  | 16 | u16 | dtick |
  | 18 | u8 | cmd |
  | 19 | u8 | txlen |
  | 20 | s16 | ret |
  | 22 | u8 | nwords |
  | 23 | u8 | retries |
  | 24 | u32 | ack_polls |
  | 28 | u16 | drain |
  | 30 | u16 | drain_last |
  | 32 | u16 | gpio_in |
  | 34 | u16 | spi_st9 |
  | 36 | u16 | spi_sttx |
  | 38 | u8 | ctx |
  | 39 | u8 | wn |
  | 40 | u16 | w_head_lo |
  | 42 | u16 | pre_wrk |
  | 44 | u8 | pre_cls |
  | 45 | u8 | ms_delta |
  | 46 | u8 | pre_flags |
  | 47 | u8 | preempt_delta |
  | 48 | u8[16] | rx |
  | 64 | u32 | lc_epc |
  | 68 | u16 | lc_dtick |
  | 70 | u8 | lc_n |
  | 71 | u8 | lc_flags |
  | 72 | u32 | led_or |
  | 76 | u16 | led_pid |
  | 78 | u16 | pre_tot |

- **W extension (1.3, 208 B; offsets within W):** match the 1.3 table, with `rsv` = 0.

  | Off | Field | Off | Field |
  |---|---|---|---|
  | 80 | epc | 186 | ext_flags |
  | 84 | cause | 187 | cur_pcnt |
  | 88 | status | 188 | c_pre |
  | 92 | ra | 192 | lc_tick |
  | 96 | sp | 196 | lc_c_pre |
  | 100 | r[16] | 200 | lc_cmd_id |
  | 164 | pid | 204 | lc_epc |
  | 168 | p_head | 208 | lc_cause |
  | 172 | jp_loop | 212 | lc_ra |
  | 176 | t_entry_tick | 216 | lc_sp |
  | 180 | t_entry_c | 220 | lc_r[16] |
  | 184 | t_busy | 284 | lc_n (u16) |
  | 185 | jp_stage | 286 | rsv (u16) |

- **POLL (1.4, 40 B):** match the 1.4 table. Offsets 0 to 31:

  | Off | Field | Off | Field |
  |---|---|---|---|
  | 0 | seq | 23 | push_fail |
  | 4 | tick_start | 24 | mouse_flags |
  | 8 | c_start | 25 | dx (s8) |
  | 12 | c_end | 26 | dy (s8) |
  | 16 | sc_seq_lo | 27 | sig |
  | 18 | body_ticks | 28 | period |
  | 19 | ri_branch | 29 | preempt_delta |
  | 20 | pi_flags | 30 | stage_max |
  | 21 | nqueues | 31 | nsc |
  | 22 | push_ok | | |

  Then 32 wk_delay, 34 wk_wrk, 36 wk_cls0, 37 wk_cls1, 38 wk_nsw, 39 rsv.
- **S (1.5, 40 B):** match the 1.5 table.

  | Off | Field | Off | Field |
  |---|---|---|---|
  | 0 | seq | 25 | flags |
  | 4 | tick_on | 26 | p_head_lo |
  | 8 | c_on | 28 | led_ops |
  | 12 | c_off | 29 | rsv |
  | 16 | sector | 30 | rsv (u16) |
  | 20 | dtick | 32 | rd_set_or |
  | 22 | pid | 36 | rd_clr_or |
  | 24 | nsect | | |

  Flag bits b0-b7 match.
- **Stats (1.7, 192 words):** every row start matches 1.7: 0, 5, 10, 14, 19-23, 24-30, 31/38/45, 52, 56, 60, 64, 68, 76, 84, 90, 93, 97, 100, 104, 112, 113, 118-124, 125-127, 128, 133, 136, 140, 148, 150, 153-159, 160. Words 62 and 63 are signed, as 10.4 says.
- **Other structures (10.2, 2.8):**
  - UHB: 21 words in 10.2 order.
  - FILEHDR: 44 B, with `nonce` at 40.
  - Chunk header: 20 B.
  - Block header: 8 B.
  - ctl: 32 B.
  - `PSC_UHB_SEG_MAKE`/`PSC_UHB_SEG_CONF` follow the r7 A6-3 mapping (⌊conf/8192⌋; 256 → SEG, else 8192·v + 1536).

### 2.2 `decoder/psc_format.py` against both

- Its `SC_FMT`, `WEXT_FMT`, `POLL_FMT` and `S_FMT` strings equal DESIGN 10.3 exactly:

  ```
  SC   '<IIIIHBBhBBIHHHHHBBHHBBBB16sIHBBIHH'
  WEXT '<5I16I5IBBBB4I4I16IHH'
  POLL '<IIIIH7B2b5BHHBBBB'
  S    '<IIIIIHHBBHBBHII'
  UHB  '<21I'
  FILEHDR '<8sIIIIIIIII'
  ```

- I re-ran `python3 psc_format.py`: "selftest: OK". My own `calcsize` gives 80/208/40/40/84/44.
- `check_format.out` shows 355 field comparisons against the C header, the gcc 4.2.1 layout OK in both user and kernel builds, and the CRC equal to zlib on 5 vectors.

### 2.3 Capture points against DESIGN section 2

**Syscon (2.1)**
- **A1:** done inline in the wrapper `psc_syscon_cmd`. Origin is set from `wd_ctx`, then `current == psc_jp_task` (1.8). `ts_read`, the snapshots and the ctx bits match 1.2 byte 38.
- **A2:** `spin = 0` (`syscon.c:127`), memory only, before S5. The other per-attempt defaults are derived at exit (DV-2).
- **A3:** in-window captures go to stack slots `dmy` 0(sp), `dlast` 2, `st9` 4, `sttx` 6, `spin` 8, `spin_ack` 12.
- **A4:** `goto out` replaces the `-3`/`-4` returns (`syscon.c:165`, `:206`). The `out:` label runs the hand-off (`:309-310`).
- Every caller goes through the wrapper (`syscon.c:330`, `:344`, `:419`; `pspSysconNop` reaches it through `pspSyscon_tx_noparam`).

**Watchdog, timer tick, LED (2.2, 2.3, 2.4)**
- **2.2:** `psp_local_tick` is at file scope. `wd_ctx` is set to 2 or 1 around both Nop call sites. In objdump of `plat_irq_dispatch`, the watchdog's own sequence (load, +1, `sltiu 1250`, store, `lastTick` store) is unchanged.
- **2.3:**
  - T1: `mfc0 s2,$9` sits one instruction before `mtc0 zero,$9`.
  - T2: `psc_tick_hook` is called after the Nop, before `psp_uart3_txrx_tick` and `irq_enter`, on both paths.
  - T2a: matches 1.2/2.3, including the nested-tick test on `preempt_count()` before `irq_enter`.
  - T2d: first fires at tick 125, then every +250, so always ≡ 125 (mod 250) and never a watchdog tick.
- **2.4:**
  - LED: `lw/or/sw` is unchanged, then a tail jump to `psc_note_led`. The loaded value is in `a1`, matching `regmap` LEDRMW.
  - S record: begin after `down_interruptible`, end before `up()`. The metadata tag uses `PAGE_MAPPING_ANON` and `S_ISBLK(host->i_mode)`. The MBR read passes 0. `ms_part_start` is set after the partition loop.

**Thread, counters, proc, panel, scheduler, vfat (2.5-2.12)**
- **2.5:** stages 1-17, `ri_branch`, `pi_flags`, pushes, mouse, fops and `queue_free` stages 1-5 are all at the cited lines. DV-10 and DV-11 are declared.
- **2.6 / 2.7:** vcs, mousedev, `do_exit` and `wb_kupdate` counters are at the cited sites, inside `#ifdef CONFIG_SONY_PSP`.
- **2.8:** `/proc/psc/{p,poll,w,s,m,stats,ctl}`. The reader follows 3.5 and writes `*ppos` only (A6-4). ctl ops 1-4 are implemented, with op 1 writing `durable_next` before `durable_tick`. There is exactly one printk (`psc_init`).
- **2.10 panel paint condition** (`psc_panel.c:307-337`), checked against 2.10 and 4.5:
  - `proc_opens > 0`;
  - and any of: `now − durable_tick > 750`, `now − last_reader_tick > 750`, a test active, `ms_rdonly`, or `fat_panics`;
  - `meta_sector` does **not** paint (r5 A5-2).

  The panel repaints every second while the condition holds, clears once when it ends, and sets `panel_cmd_id` while a P command is in flight. The title priority is MS RO > TEST > STALL. Line 6 carries META.
- **2.11:** hook W sits in `try_to_wake_up` before `success = 1`. Hook S sits inside `prev != next` before `prepare_task_switch`. The preemption branch fires on `prev == psc_jp_task && prev->state == TASK_RUNNING && t_busy_p`, as 2.11 specifies.
- **2.12:** `fat_fill_super` success stores the superblock pointer and the six geometry words; `fat_fs_panic` increments the counter; `ms_rdonly` is read at stats time and by T2d.

---

## 3. Design deviations: declared and undeclared, and whether each touches D1-D14

### 3.1 Declared (IMPLEMENTATION.md 0 and 6)

**Kernel (DV-1 to DV-18)**

| # | Touches a blocking G1 item? | Ruling |
|---|---|---|
| **DV-3** (OD-1) `nwords` 7 for 8 words ending in 0xFFFF | **YES: D3** ("the number of words actually received") | **Forbidden at Stage 2. Routed to G1.** I verified it independently from objdump (section 4.2). The design's exact `nwords` cannot be had at zero instructions in S5..S20 with this compiler output: the machine state after S19 is identical in the "7 words, then FIFO empty" and "8 words" cases. So this is a D3/D10 conflict inside the approved design, and the approved design must settle it. Options for G1: accept "7 or 8" with the decoder flagging `nwords=7 ∧ rx[14..15]=ff ff` as ambiguous; or spend instructions in the window (D10) |
| DV-4 (OD-2) callee-saved register renaming in the window; one exit delay slot | **No** | All four G2 acceptance criteria of DESIGN 2.1 hold, which I verified myself (section 4): same MMIO loads and stores in the same order and form; same loop bodies and counts (105 = 105); no calls; no global loads or base reloads. Register numbers do not change timing. The one differing instruction is the delay slot of the first −3 exit branch (`lw s8,40(sp)` → `nop`): it runs after the exit decision and after the path's last MMIO. **Not a deviation from the approved criteria; no G1 routing.** |
| DV-1 wrapper + asm hand-off | No (D10 substance kept: nothing added in S5..S20, no lock, no IRQ change) | Accepted. But the added time is larger than 5.4 estimates; see F5 |
| DV-2 sentinels derived at exit; drain of exactly 1,000,000 then empty reads 0 | No (`ret` still separates −3; raw `rx` intact) | Accepted |
| DV-5 to DV-18 | No | Accepted. DV-9 resolves a 1.2/1.3 conflict as 1.3 says. DV-11 keeps the H9 signature (`qfree_stage` 2 for a closer blocked at the list semaphore) |

**pscol (P-1 to P-14)**

| # | Touches a blocking G1 item? | Ruling |
|---|---|---|
| P-1 (OD-5) 256 KB per process, not 128 KB | No (still no allocation after boot; +256 KB against ≈ 20.8 MB) | Accepted; the design's "≤ 128 KB" figure is not met and is recorded here |
| P-4 allocating step with no FAT1 record, or a skipped `seq` → stop | No | Conservative reading of "at least one succeeded if the step allocated". It cannot fire systematically: the FAT1 buffer dirtied by the step's own allocation is always written by that step's `sync_blockdev` |
| P-5 STICK accepts any DURABLE flush | No (D13 still proven: DURABLE + geometry check + `durable_tick` + speed + names) | Accepted |
| P-12 names budget counts LFN slots | Not as declared, but the implementation is wrong | See F2 |
| Other P items | No | Accepted |

**Decoder and integration**

| # | Touches a blocking G1 item? | Ruling |
|---|---|---|
| D-1 to D-22 | No; D-16 is a defect | See F3 |
| I-1 to I-4 | No | Accepted. I extracted the committed cpio myself: 97 entries; `usr/bin/pscol` 0755 with sha `e5090df3…`; the `rc.sysinit` lines are correct |

### 3.2 Undeclared (found here)

| # | What | Touches a blocking G1 item? |
|---|---|---|
| U1 | Run-number and `nnn` scans never match (F2); names budget overcounts own files (F2) | Not a design change: a code defect against 4.2 and 4.4 steps 1 and 6. It weakens the D6 margin only in the IF7b name-cost case after earlier boots. Fix in code; no G1 routing |
| U2 | Recording cost and the G3-low gap are about 3-4× the 5.4/7.3 estimates (F5) | No (the D10 mechanism is intact; 5.4 says G2 substitutes objdump counts) |
| U3 | Re-send of a FAILED flush recounts records already counted `lost` (F6) | No |
| U4 | KRN does not check `build_id` (8.2), also OD-3 | No (pscol is inside the same image's initramfs) |

---

## 4. C2 / D10: the transaction window, re-derived (syscon-window-diff.txt independently checked)

### 4.1 Window comparison

- **Disassembly.** I ran `mipsel-linux-uclibc-objdump -d` in the container on `work/prebuilt/vmlinux` (baseline, `Syscon_cmd` 880cee10..880cf178) and on `out/20261006T021722Z/vmlinux` (release, 880ceed0..880cf300). The source tree was mounted read-only.
- **My own comparison.** I wrote a fresh script, not `d10_proof.py`. It walks address order from the S5 load to the S20 store:
  - baseline 880ceeec..880cf0bc, skipping its inline epilogue 880cf024..880cf050;
  - release 880cefb0..880cf278, skipping the hand-off block 880cf0e8..880cf20c;
  - it normalises stack offsets and branch targets, and maps release registers back to baseline names (s7→s3, s3→s4, s4→s5, s5→s6, s6→s7).
- **Result:**
  - 105 instructions on each side;
  - **one difference only**: the delay slot of the `-3` exit `j`, baseline `lw s8,40(sp)` against release `nop`;
  - every MMIO load and store (`0(s3)`/`0(s4)` GPIO, `0(t2)`, `0(t4)`, `0(a2)`, `0(s2)`, `0(s6)`/`0(s7)`, `0(t7)`, `0(s8)`, `0(s0)`) is in the same order and form;
  - no `jal` in the window.

  This equals the implementer's `syscon-window-diff.txt` (105/105, the same renaming, the same exit-ds difference). The release copy says the same.

### 4.2 Hand-off and `nwords` (DV-3)

**Hand-off registers.**
- `t0` ($8) is the receive-loop counter: `li t0,2` at 880cf218, then `addiu t0,t0,2` in the delay slot of the loop jump.
- The checksum loop after S20 uses `v1`/`a3`/`a0`, not `t0`.
- `t8` ($24) is `retry_cnt`. On the retry path, `bnel t8,v0,880cef4c` takes the jump with `lbu t0` in the delay slot, so the hand-off is not reached.
- The hand-off reads `lhu 128(sp)`=dmy, `lw 136`=spin, `lw 140`=spin_ack, `lhu 130/132/134` = dlast/st9/sttx. These are the same slots the window stores to. Correct.

**Loop exits.** Exit by FIFO-empty at `i = 14` (`beqz v0,880cf268`, delay slot `addiu a0,t0,-2`) and the fall-through after the 8th word (`bnez t1` not taken) both reach 880cf268 with `t0 = 16`, `a3 = rx_buf+16`, `a0 = 14`, `t1 = 0`. `v0` and `v1` are overwritten at 880cf268-880cf26c before S20. The two cases cannot be told apart, which confirms DV-3. `psc_fill_sc` (`psc.c:276-280`) then uses `rx[14..15] == ff ff` and reports 7.

### 4.3 Timeout patch

- `SYSCON_SPIN_MAX` and `SYSCON_RETRY_MAX` (`syscon.c:12-13`) are byte-identical to baseline.
- The −3/−4 bounds (`spin-- == 0` / `spin_ack-- == 0`), the −4 teardown writes, and the `−5` retry logic are unchanged.
- The text edits are exactly the ones DESIGN 2.1 A3/A4 prescribes.
- **DV-17 ruling:** the patch is present and its behaviour unchanged (verified in object code).

---

## 5. C1: segment life cycle in pscol against 4.4 (round 7), 4.6, 4.7

Each rule below was checked against pscol source and found to conform. Gaps are in the last two items.

**4.4 step 1: open, alias test, probe (`create_attempt`, pscol.c:1486-1574)**
- `open(O_CREAT|O_EXCL)`; `EEXIST` moves to the next number.
- Alias test: `fstat` gives `st_size != 0` or an `st_ino` this instance has seen (`seen[]`). An alias gets EVENT `inode reused`, UHB b28, is never written, is closed, and the loop retries in the same tick.
- At most 24 opens per tick.
- Probe: if the stick is not working, `fsync` the first alias, then judge the window. Not working → wait ≥ 10 s.
- `names_used` counts aliases.

**4.4 steps 2-4: FILEHDR and step verdicts (`step0`, `do_step`, `judge_step_fat`, `judge_step_data`)**
- Step 0 writes the FILEHDR + PAD 1,536 B, then `fsync`; it is never retried in place (`V_ABANDON`).
- FAT check: no FAT1 write in the window failed, and at least one succeeded if the step allocated. Allocation is `⌊(conf+k−1)/cl⌋ > ⌊(conf−1)/cl⌋`; step 0 always allocates.
- FIBMAP runs only after the FAT check passes.
- Data check: every data sector has a successful DATA record, and `fstat == conf + k`.
- **Own-entry rule (r7 A6-1):** after the last DATA record that covers the step's own sectors, the first DIR-class write must carry the worker's pid and be error-free. A DIR write from another pid that comes first causes abandon. Other DIR failures in the window are ignored (META evidence only).
- Retry in place up to 3 times; the 4th failure stops growth.
- Steps are 64 KB while holding or while room < 81,920 bytes, else 8 KB (`choose_k`).

**4.4 steps 5-8: stop, next attempt, completion, cap**
- Stopped/abandoned files (`seg_stop`): never written at or above `conf`, never reopened. Prefix-usable needs `conf ≥ 42,496`, or the file was already active.
- Next attempt (`next_attempt_rule`): next tick only if the failed window holds a successful write and `fast_used < min(400, budget/2)`; otherwise ≥ 10 s.
- Completion (`seg_complete`): `fadvise` through syscall 4254 with seven slots; I checked the call in `pscol.dis` — `fd, 0, off, 0, len, 0, 4` maps to o32 `sys_fadvise64_64` as 7.4 states. Then `pread` of the last sector, compared with the PAD template.
- Cap: 64 MB (`should_create`). Creation stops when two complete files wait ahead.

**4.4 "Use and switch", round-7 TE10 (`target_select`, pscol.c:1729-1765)**
- Flush only if `seg_end + 40,960 ≤ usable(active)`.
- An active file still in creation and not retired **holds**, with 64 KB steps, and resumes in the same file at its own `seg_end`.
- A switch target must never have been active (`!was_active`), be not retired, and be complete or have usable ≥ 42,496. The oldest by creation order wins.
- `seg_end = 1,536` is set only for the new, never-active target.

**4.3 / 4.6: no overwrite and re-send (`flush`)**
- `seg_end += len` whatever the result.
- Verdict from the S window, not from `fsync`.
- FAILED → the infl and new ranges are re-queued.
- DURABLE → durable for its own records. `durable_tick` advances only on a complete drain with an empty queue.
- Re-send starts the tick after a DURABLE flush.
- Bad region: 3 consecutive FAILED flushes with a local DATA error → retired.
- EVENT and KMSG are kept until a DURABLE flush carries them.

**4.7: META (`meta_record`)**
- Stuck = ≥ 5 consecutive failed write records of a metadata sector, spread over ≥ 3 drain batches, in each of which a worker DATA write succeeded.
- Reported via ctl op 4, EVENT, UHB b23. HUD line 6 is not red. No panel paint.
- Cleared by a later good write; bypassed after 60 s with no write and no failed flush; FAT-sector bypass on a CONFIRMED allocating step.

**4.8: windows**
- Read with `pread` on `/proc/psc/s`. uClibc `pread` goes through `pread64` (syscall 4200) with `a3 = 0` and the 64-bit offset in stack slots 5-6 (`pscol.dis` 0x40b4cc-0x40b45c). That is the correct o32 layout.

**Gaps:** the run number and `nnn` (F2), and `KRN build_id` (F4).

---

## 6. C3, C4, C5, C7 details

### 6.1 C3: context safety

**Paths reachable from the timer interrupt**
- `psc_tick_hook` → `psc_cur_regs` (bounds-checked), `psc_copy_regs`, `memset`.
- `psc_t2d` → `psc_panel_t2d` (VRAM stores, `pspClearDcache`: cache ops in its own non-inlined function; it clobbers only `t0`/`t1`) and `psc_fat_rdonly` (one pointer and one flag load).
- From the Nop: `psc_syscon_cmd` → `Syscon_cmd` → `psc_xfer_out` (8-word copy) → `psc_sc_exit` (W path: `psc_fill_sc`, `memset`/`memcpy`, `psc_fill_wext`, `psc_dcount` with an inline `multu`).

None of these sleeps, allocates, locks, calls printk or calls `copy_to_user`.

**Scheduler hooks** (both under the rq lock with IRQs off)
- Hook W: `psc_ts_read` (one iteration with IRQs off), `psc_class` (8 loads).
- Hook S: the same plus arithmetic. O(1).

**Interrupt landing mid-append**
- P (`psc.c:448-457`), M, POLL (`:894-900`) and S (`:670-711`) each do `PSC_WR(seq, 0xFFFFFFFF)`; `barrier()`; fill; `barrier()`; `PSC_WR(seq, s)`; `barrier()`; `PSC_WR(head, s+1)`. The `PSC_WR`s are volatile.
- The Nop writes only W, `xfer[W]`, `wd_calls` and the W counters. T2 writes only the `lc_*` words (bracketed by `lc_seq`, odd while writing), tick stats, panel and guards.
- The thread's readers bracket `lc` (`lc_seq`), `pre_*` (`pre_seq`) and `wk_*` (`wk_seq`).
- `led_cmd_*` is written only by the non-preemptible MS path while `t_busy_p` is set, and read after `t_busy_p` is cleared.
- `t_busy_p` is set after `t_cmd_id++` with a `barrier()`, and cleared after the exit snapshots (DV-5).

**Reader**
- `seq` is checked before and after the copy.
- A lap seen at a slot being written leaves `h − s ≥ N`, so it is not counted as `slot_bad`.

**Stack** (new, unverified risk; see F5)
- The Nop path in IRQ is now ≈ +280 B deeper: wrapper 72 + `Syscon_cmd` 56 (was 48) + hand-off 128, or `psc_sc_exit` 104 + `psc_fill_sc` 64.
- T2d's panel frame is 328 B.
- Kernel stacks are 8 KB (4 KB pages, order 1).

### 6.2 C4: bounds

**Kernel**
- `psc_ring_read`:
  - rejects `*ppos` not a multiple of the record size, and `pos > 2^32−1`;
  - `s > h` → `head_regress`;
  - `h − s > N` → `s = h − N`;
  - stops before `done + size > count`;
  - at most N skips;
  - `tmp[288]` covers the largest record;
  - writes `*ppos` only.
- Stats read is bounded by 768 − `*ppos`.
- ctl requires `count % 32 == 0`, slot < 8, seconds 1..10.
- `rx` copies 16 bytes from the caller's `rx_buf[0x10]`; `nwords ≤ 8`.
- The hand-off stays inside its own 128 B frame (raw block at 16..47, saves at 48..124).
- Panel lines are ≤ 40 characters (checked per line: 39/39/40/37/37/40); glyph index 0..38.

**pscol**
- Drain records per tick ≤ 4 × 8,576 = 34,304. RECS ≤ 20 + 10 × 8 + 34,304 = 34,404. + UHB 104 + STATS 788 + PROCS ≤ 2,420 + PAD header gives ≤ 37,888 ≤ 40,960. `xread` checks every length against `END_OF(B.flush)`. KMSG and EVENT are added only if they fit.
- Flushes start at 1,536 + k × 512 and end ≤ `usable` ≤ 2,097,152. Steps write ≤ `SEG − conf`. `writev` uses ≤ 20 iovecs × 4 KB.
- CRC covers the payload only; the seed is the nonce, 0 for FILEHDR. `fseq` 0xFFFFFFFF in preallocation sectors.
- S windows ≤ 256 records; more counts as skipped, giving FAILED.

### 6.3 C5: boot

**BSS and early records**
- `psc_mem` is BSS: `__bss_start` 881b0000, `_end` 88260b50.
- The WB Nop in `prom_init` (with `wd_ctx = 1`) → `psc_sc_entry` uses `current` (init_task, `$28` set by `head.S`), `read_c0_status`, `in_interrupt` → W seq 0. No init function is needed.
- `psc_syscon_end` is computed lazily.
- Early `psp_led_ctrl` (`psp.c:151`) touches only counters.
- T2d paints nothing before a ring file is opened. `psc_jp_task` is NULL-safe everywhere it is used.

**pspboot and cmdline**
- I disassembled `DATA.PSP` from the baseline `EBOOT.PBP`. pspboot copies the 256-byte cmdline to **0x88000008** (`ori a0,s0,0x8; li a2,256` at 0x8900684-0x8900690) and passes it as `a2`.
- Bytes 8..0x107 of `vmlinux.bin` are zero in both images; only the first jump word differs. BSS clearing never touches that area.
- pspboot appears to allocate and read with a **0x400000 (4 MB)** bound (`lui a0,0x40` at 0x89007bc, `lui a2,0x40` at 0x89007d4) against `vmlinux.bin` 1,766,859 B. This is my reading of a stripped loader: UNVERIFIED as function identity, but supporting evidence for OD-6/R20.

### 6.4 C7: symbols and call sites (release vmlinux)

| Hook | Called from (release vmlinux) |
|---|---|
| `psc_syscon_cmd` | `pspSyscon_tx_dword`, `pspSyscon_rx_dword`, `_pspSysconGetCtrl2` |
| `psc_xfer_out` | `jal` inside `Syscon_cmd` at 880cf17c |
| `psc_tick_hook` | both paths of `plat_irq_dispatch` |
| `psc_note_led` | both `psp_led_ctrl` paths |
| `psc_ms_seg_begin`, `psc_ms_seg_end` | `psp_ms_read`, and `psp_ms_make_request` (where `psp_ms_write` is inlined) |
| `psc_sched_wake_slow` | `try_to_wake_up` |
| `psc_sched_switch_slow` | `schedule` |
| `psc_jp_thread_start`, `psc_poll_begin`, `psc_poll_end` (2 sites) | `psp_joypad_thread` |
| `psc_fat_mounted` | `fat_fill_super` |
| `psc_fat_panic` | `fat_fs_panic` |

---

## 7. A7 advisories (G1 attempt 7, "What would close it")

I rebuilt revision 6 by applying `design/round7.diff` to the frozen `DESIGN.r5.md` and `RUNBOOK.r5.md`. Then I diffed it against the current `DESIGN.md`. The only differences are the three A7 hunks of `impl/A7-design.diff`; RUNBOOK is identical. No design substance changed.

| ID | Closed | Note |
|---|---|---|
| A7-1 | yes | 4.4 step 6 now reads "IF7b ≤ 16 per creation that meets the refusing sector (≤ 153 names, 15.3)", which is the review's text |
| A7-2 | yes | 15.3 now states (a) the outcome when the margin runs out (creation stops, ≈ 9 minutes of files ahead, then hold and panel) and (b) why eviction is unlikely (`shrink_slab`/`drop_caches` only, ≈ 2 MB per file against ≈ 20.8 MB, reclaim not before about minute 30, normal use ends at 30:00). 8.5 VFAT-FI runs IF7b with guest memory well above the page-cache total (the review's first option) |
| A7-3 | yes | 4.3 step 3 now reads "`syscall(__NR_syslog, 3, buf, 16384)` as telem". pscol's `os_syslog(3, …)` is `syscall(__NR_syslog, …)` (`os_target.c:110-113`) |

---

## 8. Findings (each: file:line, problem, what closes it)

**F1: G1 routing, D3 (blocking)**
- *Where:* `arch/mips/psp/psc.c:276-280`; DV-3 / OD-1.
- *Problem:* the 8-word frame whose last word is 0xFFFF is recorded as `nwords = 7`. The design (1.2 offset 22, D3) requires the words actually received. An exact count needs instructions inside S5..S20 (D10). This is a deviation touching a blocking G1 item.
- *Closes it:* a G1 ruling on the D3/D10 conflict. Either amend 1.2/10.3/10.7 to define `nwords = 7 ∧ rx[14..15] = ff ff` as "7 or 8", with the decoder flagging it; or approve a specific in-window instruction cost. Then implement exactly what G1 approves.

**F2: C1 (blocking): run number, next `nnn` and names budget**
- *Where:* `pscol/main.c:87`; `pscol/pscol.c:2118-2125`.
- *Problem:*
  - `T<rrr><nnn>.BIN` is **11** characters with the dot at index 7. The scans test `strlen == 12` (main.c) and `len == 12 && nm[8] == '.'` (pscol.c), so they never match, even in upper case.
  - In addition, `/ms0` is mounted without options (`rc.sysinit:10`), so vfat defaults to `shortname=lower` (`fs/fat/inode.c:948`), and `readdir` returns short names in lower case (`fs/fat/dir.c:211-212`): `t001001.bin`.
  - Results:
    - (a) `rrr` is **always 001** on every boot. FILEHDR `run` is 1 for all boots. RUNBOOK B3/B5/E1 step 5/E2 ("other `T<rrr>` digits are from earlier boots") then counts leftover files as this run's, which can force an unneeded raw image. The decoder's default run selection finds two nonces under run 1 and refuses (D-4) until the analyst picks one.
    - (b) `next_nnn` always starts at 1. Every earlier file costs an `EEXIST` open (24 per tick) and fast-attempt budget. The 999-name space is shared across boots, so a STICK-green self-test (budget ≥ 400 free slots) no longer guarantees ≥ 400 usable names. That weakens the IF7b/D6 margin of 15.3.
    - (c) The names budget counts each of our own files as 2 slots (lower case is treated as an LFN). This is conservative, but it can raise `MS DIR FULL` falsely.
  - The host harness hides all of this: `test/sim.c:850-868` returns upper-case names and always runs run 1.
- *Closes it:*
  - compare names case-insensitively with length 11 and the dot at index 7, in both scans;
  - count an 8.3 name as 1 slot regardless of displayed case (a name is SFN-only if it fits 8.3 and has no mixed case; or count directory slots from `getdents` positions);
  - add host tests where `getdents` returns lower-case `t001001.bin` from an earlier boot: expect `rrr = 2`, `nnn` restarting at 1 for run 2, and the budget counting 1 slot per file;
  - rebuild pscol, re-run the 7.7 checks, and repack the initramfs.

**F3: C1 (blocking): decoder cannot read the kernel's maps (OD-4)**
- *Where:* `decoder/pscdec_analysis.py:139-145`, `:190-196`, `:556-566`, `:1327-1328`; against `handoff/impl/release-20261006T021722Z/regmap.txt` and `epcmap.txt`.
- *Problem:* loading the release maps with `BuildInfo.load` gives:
  - `S16-S18 {'i': '+', 'ptr': '+'}` and `S18 {'i': '+'}`, so P6 `j` is never computed (the receive loop's EPC label is `S18`);
  - `LEDRMW {'loaded': 'value'}`, while the code asks for `"val"`, so LEDSPLIT prints "not in regmap";
  - `all {'tx_buf': '+', 'rx_buf': '+'}`;
  - EPC 0x880cef4c labelled `S0`, which has no P-point.

  Also, `regmap` gives `i + 2` and `ptr + 2` at S16-S18, but the decoder computes `j = (ptr − rx_buf)/2` with no offset. The decoder's 26 tests ran only on its own synthetic map syntax.
- *Closes it:*
  - one agreed map grammar, with a unit/offset column, used by `mkmaps.py` and `BuildInfo.load` alike;
  - `S0 → P0`;
  - P2 `k` and P6 `j` computed with the documented offsets;
  - a decoder test run on the **release** maps with a synthetic W record at S11, S18 and LEDRMW, checking `k`, `j` and the loaded value.

**F4: non-blocking: `build_id` (OD-3)**
- *Where:* `pscol/pscol.c:432` (`build_expect == 0` → never checked); `psc.c:1221` (kernel definition).
- *Problem:* DESIGN 8.2 KRN requires "the collector's build_id"; it is not compared. Low risk, because pscol ships inside the same image. Separately, note for the orchestrator: every rebuild changes the banner, so the 02:28 rebuild of the same HEAD has a different image hash (`e7ffdd2c…`) and `build_id` from the packaged one (`c72459e3…`, `0x9b3c599e`). The decoder and G3 R3 must use the packaged build's `banner.txt`.
- *Closes it:* pscol computes the CRC-32 of `/proc/version` at start and compares it with stats word 2 (KRN red on mismatch). Record the decision in IMPLEMENTATION.md, and give the decoder the packaged build's `build_id.txt`.

**F5: non-blocking: added time and stack not restated from object code (5.4, 7.3, D10 evidence)**
- *Where:* IMPLEMENTATION.md 4.5 row 5.4; `syscon.c:17-61`; `psc.c:427-533`.
- *Problem:* objdump counts (release build):
  - `psc_syscon_cmd` ≈ 60 instructions before calling `Syscon_cmd` (design ≈ 35);
  - after S20: hand-off ≈ 85, plus `psc_sc_exit` (583 instructions in total; ≈ 250-300 on the P path), plus `psc_fill_sc` (151, with `memset`/`memcpy`). That is ≈ 400-550 instructions (≈ 2-2.5 µs) against the design's ≈ 130 (≈ 0.6 µs);
  - so the G3-low gap grows by about 2.5-3 µs, not 0.75 µs (7.3, R6);
  - Nop path in IRQ: about +280 B of stack.

  Nothing is added in the window and nothing locks or masks, so D10's mechanism holds. But the stated figures are low by about 3-4×, and 5.4 says G2 substitutes objdump counts.
- *Closes it:* IMPLEMENTATION.md states the per-path instruction counts (P entry, P exit, the Nop) and the worst-case IRQ stack depth from objdump, and the orchestrator records that the 7.3 numbers are superseded by them. The run still measures `p_rec_cost` and median duration (HUD line 10).

**F6: non-blocking: lost records recounted on re-send**
- *Where:* `pscol/pscol.c:932` with `:1908`.
- *Problem:* the new range `[pos0, np)` of a FAILED flush is re-queued. It includes `seq` values already counted in that block's `lost`. Re-sending counts them again, which can turn REC red (UHB b22) after the first complete drain with no new loss.
- *Closes it:* queue `[pos0 + lost, np)`, or do not add to `lost_total` for re-send gaps that were already counted. Add a host vector.

**F7: non-blocking: commit provenance (C10)**
- *Where:* `work/linux/.git/config` `user.name = Recon C (Claude agent)`; commits `4c4e7aee`..`0b0a2acf`.
- *Problem:* the kernel implementer's 14 commits are attributed to "Recon C". This blurs the role audit trail that WORKFLOW's "nobody reviews their own work" relies on.
- *Closes it:* a note in the gate log, or IMPLEMENTATION.md, naming the actual author of those commits (history need not be rewritten).

---

## 9. Attacks tried (WORKFLOW principle 4)

1. **Timer Nop between `t_cmd_id++` and `t_busy_p = 1`, and between the exit snapshots and the clear.** Both are consistent: T2a and W `t_busy` see "not busy", and `wn`/`w_head_lo` agree with W `t_busy`.
2. **Nop during the hand-off asm or during `psc_xfer_out`.** Separate `xfer[]` areas per origin, and sp is lowered before any store. Safe.
3. **Collector preempted between the `seq` reads while the thread laps the slot.** `q2 ≠ s` and `h − s ≥ N`, so it is a lap, not `slot_bad`.
4. **Zero-byte reads during a hold longer than the ring.** The kernel moves `f_pos` silently. pscol's `pos0`/`np` accounting still counts the gap correctly.
5. **`pread` S window beyond the head (would raise `head_regress`).** Impossible: `s < b ≤` head. The o32 `pread64` argument layout was verified.
6. **Allocating step whose FAT1 write comes from `pdflush` before the step's `fsync`.** Excluded: the buffer is dirtied by the step's own `write()`, which is younger than 30 s.
7. **Active file in creation that runs out of room.** It holds and resumes in the same file. A stop or retirement while active → prefix-usable → switch to a never-active file only.
8. **Read-only `/ms0` while creating.** The creating file is stopped, and the target selection then switches or holds. No deadlock.
9. **BSS clear destroying boot parameters.** The cmdline is at 0x88000008, outside BSS. No other pspboot handoff data was found in [old `_end`, new `_end`].
10. **pspboot image size.** It appears to have a 4 MB decompression bound against 1.77 MB.
11. **Run numbering on the real vfat (shortname=lower).** **Broken: F2.**
12. **The decoder on the real release maps.** **Broken: F3.**
13. **Exactly 8 received words ending 0xFFFF.** Misrecorded: F1/DV-3.
14. **Deep interrupted stack + Nop + T2d panel.** About +280 B on the Nop path and 328 B in the panel frame, against 8 KB. Plausible but unmeasured: F5.

## 10. What I did not verify

- Runtime behaviour on hardware.
- The CP0 Count rate.
- The panel's visibility.
- The verifier's independent clean build (C6) and Stage 3 tests.
- pspboot function identities (read from a stripped binary).

I wrote nothing in `/home/ubuntu/psp/build/linux` or `/home/ubuntu/psp/work`. All disassembly was done in a read-only container mount with outputs in my scratchpad.
