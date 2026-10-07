# G2 attempt 2: verifier report

Verifier: Opus 5.5, fresh context. I was not an implementer, designer, code
reviewer or earlier verifier. Date: 2026-10-06. I built and measured
everything below myself. Every number taken from IMPLEMENTATION.md was
re-measured.

Inputs read: DOSSIER.md (section 9, including 9.6 and 9.8), WORKFLOW.md
(G1, G2, Amendment A1), design/DESIGN.md (revision 7: 2.1, 7.2, section 17),
design/RUNBOOK.md ("What you need"), recon/build.md (1-3), recon/syscon.md
(headings, section 7), gates/LOG.md, impl/IMPLEMENTATION.md (attempt 2),
gates/G2-attempt1-review.md, gates/G2-attempt1-verify.md,
gates/G1-ruling1-review.md.

Evidence directory: `/home/ubuntu/psp/work/verify-g2-attempt2/`. It holds the
logs, the two `Syscon_cmd` listings, my comparison script `winv2.py` (written
for this check; it does not reuse `d10_proof.py` or the attempt-1 `win.py`),
`calls2.py`, the initramfs I extracted, and a `BUILD-verifier/` map set.

What I wrote, and where:
- Nothing in the original tree.
- Nothing in `work/pscol`, `work/decoder` or `work/deploy`. The pscol build
  and both test suites ran on scratch copies in `verify-g2-attempt2/scratch/`.
- `build.sh` wrote its normal outputs: the in-tree build products,
  `work/out/20261006T055351Z` and `work/logs/build-20261006T055351Z.log`.

## Verdict: PASS

None of the task's FAIL conditions holds:
- the build succeeded, and the manifest exits 0;
- no symbol is missing;
- the window meets the criteria the G1 ruling accepted (DESIGN 2.1/7.2, §17 R-2);
- 0 FP registers;
- the initramfs contains pscol, and `rc.sysinit` starts it;
- both test suites pass;
- the package is correct.

Section "Findings" lists the open non-blocking items.

| # | Check | Result |
|---|---|---|
| 1 | Original tree manifest | exit 0 (at the start and at the end) |
| 2 | Clean build of `stage2-trace` HEAD `48dcc1b9` | rc 0. The sha256 differs from the release, but **only in the banner**: 8 bytes in `vmlinux.bin`, all in the two time-string copies |
| 3 | New warnings in changed files | none. The distinct warning set (38) is identical to both 20260927 baseline logs and to the release log |
| 4 | Symbols and capture sites (C7) | all present, at the intended sites |
| 5 | S5..S20 window vs baseline (C2, D10) | **meets the §17 R-2 criteria**. Only the three allowed kinds of difference occur |
| 6 | pscol (C8) and test suites | 0 FP registers, 0 FP mnemonics, valid bFLT, 55,852 B. pscol tests: RESULT PASS, 0 failing cases. Decoder: 37/37 OK, including the 7 new release-map tests |
| 7 | Initramfs in my image | `usr/bin/pscol` 0755 is present (sha256 = delivered). `rc.sysinit:22` has `pscol&` |
| 8 | Image size | `vmlinux.bin` +44,036 B, 5,116 B under 49,152. `vmlinux-0.22.bin` +37,312 B. pspboot load **UNVERIFIED** |
| 9 | Package | SHA256SUMS OK; `EBOOT.PBP`, `pspboot.conf` and `kmodlib.prx` are byte-identical to `pspboot-baseline`; no name collision |

---

## 1. Original tree intact

```
$ cd /home/ubuntu/psp/build/linux && sha256sum -c --quiet /home/ubuntu/psp/handoff/gates/baseline-tree.sha256; echo "EXIT=$?"
EXIT=0
```

I ran it before any work and again after all work. Both runs exited 0 with no
output.

## 2. Clean build

**Before the build.**

```
$ git -C /home/ubuntu/psp/work/linux branch --show-current; git rev-parse HEAD; git status --porcelain
stage2-trace
48dcc1b9dad43f0f919a859b5d9cc44771558f3d
(empty)
$ git diff --stat c135ecdd..48dcc1b9
 psp-initramfs.cpio | Bin 1313280 -> 1313792 bytes      (the only change since G2 attempt 1)
```

**The build.**

```
$ /home/ubuntu/psp/work/build.sh
log: /home/ubuntu/psp/work/logs/build-20261006T055351Z.log
out: /home/ubuntu/psp/work/out/20261006T055351Z
RC=0
```

**Log header and markers.**

```
git HEAD:    48dcc1b9dad43f0f919a859b5d9cc44771558f3d (initramfs: pscol for G2 attempt 2 (...))
git status (before clean, tracked changes only):          <- empty
image:       psp-build:bullseye (sha256:77a157805abf...be2de8)
hostname:    psp-work-build
KBUILD_BUILD_VERSION='' KBUILD_BUILD_TIMESTAMP='' REPRODUCE_BASELINE='0'
=== clean: git clean -fdxq
untracked/ignored files after clean: 0
MAKE_EXIT:0  (log line 590)   BUILD_EXIT:0 (595)   CONTAINER_WALL_SECONDS:202
```

**Outputs** (`out/20261006T055351Z/SHA256SUMS`):

```
c6457dfbac0663c375f651268538e49388af5fda83bff4e59a850fff602d7683  vmlinux
bc34b243eee533ac54ef6633c460eda5b47c0f0ddee505c1afbda75687f3b4e3  vmlinux.bin
1b20768be13b8a89af421b168dcb1810e6d74225533bca463f1a3274564be80f  vmlinux-0.22.bin   (936,713 B)
77816657f56623d2a085ed3d8771584e5f5d01c45a5017c093b4dea328cdb5cf  System.map
banner: Linux version 2.6.22 (root@psp-work-build) (gcc version 4.2.1) #1 PREEMPT Tue Oct 6 05:57:06 UTC 2026
```

**Initramfs source.** The build read the work tree's cpio.
`.config:163` is `CONFIG_INITRAMFS_SOURCE="/work/work/linux/psp-initramfs.cpio"`,
and `usr/.initramfs_data.cpio.gz.cmd` reads
`... gen_initramfs_list.sh -o usr/initramfs_data.cpio.gz -u 0 -g 0 /work/work/linux/psp-initramfs.cpio`.

**Comparison with the release in IMPLEMENTATION.md 1.2** (`out/20261006T052947Z`,
`vmlinux-0.22.bin` sha256 `4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8`,
936,714 B):

```
$ cmp System.map (mine) System.map (release)                -> identical
$ cmp -l vmlinux.bin (mine) vmlinux.bin (release) | wc -l   -> 8
$ cmp -l vmlinux     (mine) vmlinux     (release) | wc -l   -> 8
  vmlinux.bin offsets 1179736,1179737,1179739,1179740 (vaddr 0x88120058..5c, linux_banner)
                      1275360,1275361,1275363,1275364 (vaddr 0x881375e0..e4, utsname version)
  mine:    "... #1 PREEMPT Tue Oct 6 05:57:06 UTC 2026"
  release: "... #1 PREEMPT Tue Oct 6 05:32:47 UTC 2026"
$ gunzip -c vmlinux-0.22.bin (mine) | cmp - vmlinux.bin (mine)  -> identical
```

- **The difference is banner-only:** 8 bytes, all of them banner time-string
  digits. The 1-byte size difference in the gzip file follows from that.
- My build's `build_id` (CRC-32 of its banner) is `0x608a79f9`. The packaged
  build's is `0x045b27d9`.
- I ran `impl/mkmaps.py` on my build into `verify-g2-attempt2/BUILD-verifier`.
  The result is refused for nothing, and these files are byte-identical to
  the release `BUILD/`: `epcmap.txt` and `regmap.txt` apart from their two
  header lines (path and banner), plus `System.map` and `panellayout.txt`.
- So the release maps describe the same code as my build.

## 3. Warnings

```
$ grep 'warning:' build-20261006T055351Z.log | wc -l                     -> 40
$ grep 'warning:' build-20261006T055351Z.log | sort -u | wc -l           -> 38
$ diff <(sort -u warnings build-20260927T204657Z.log) <(... 20261006T055351Z) -> no difference
$ diff <(sort -u warnings build-20260927T204324Z.log) <(... 20261006T055351Z) -> no difference
$ diff <(sort -u warnings build-20261006T052947Z.log) <(... 20261006T055351Z) -> no difference
```

The changed files are listed in `verify-g2-attempt2/changed-files.txt`
(`git diff --name-only baseline..stage2-trace`, 19 files).
- No `warning:` line names any of them.
- No `In file included from` chain names `psc.h` or `psc_format.h`.
- All 14 changed C units have a `CC` line: `syscon`, `psc`, `psc_panel`,
  `psp`, `ms_psp`, `vc_screen`, `joypad_psp`, `mousedev`, `fat/inode`,
  `fat/misc`, `exit`, `printk`, `sched`, `page-writeback`.

**New warnings in changed files: none.**

## 4. Symbols and capture sites (C7)

I made `objdump -d`, `nm -n` and `objdump -h` of my `vmlinux` in the container.
The outputs are `new-vmlinux.dis`, `new-nm.txt` and `new-sections.txt`. The
baseline listing came from `out/20260927T204657Z/vmlinux`. Call sites were
found with `calls2.py`; the output is `callsites.txt`.

**Symbols.** Every name in this list is in `nm`:
- the recorder: `psc_syscon_cmd`, `psc_sc_exit`, `psc_xfer_out`, `psc_fill_sc`,
  `psc_syscon_end_calc`, `psc_dcount`, `psc_cur_regs`, `psc_class`;
- hooks: `psc_tick_hook`, `psc_note_led`, `psc_ms_seg_begin`, `psc_ms_seg_end`,
  `psc_sched_wake_slow`, `psc_sched_switch_slow`, `psc_jp_thread_start`,
  `psc_poll_begin`, `psc_poll_end`;
- FAT and the semaphore accessors: `psc_fat_mounted`, `psc_fat_panic`,
  `psc_fat_rdonly`, `psc_console_sem_count`, `psc_jp_list_sem_count`;
- `/proc/psc`: `psc_ring_open`, `psc_ring_read`, `psc_ring_llseek`,
  `psc_stats_read`, `psc_ctl_write`, `psc_init`, `__initcall_psc_init7`;
- the panel: `psc_panel_t2d`, `psc_panel_fill`, `psc_panel_account`, `pl_ch`,
  `pl_str`, `pl_hex`, `pl_dec`, `pl_age`;
- data: `psc_mem` (B 881bd860), `psc_jp_task`, `psp_local_tick`,
  `psc_syscon_end`, `psc_fat_sb`, `psc_font`, `psc_guard_word`,
  `psc_ring_desc`, `psc_ring_fops`, `psc_stats_fops`, `psc_ctl_fops`.

The watchdog context flag is the field `psc_k.wd_ctx`
(`include/asm-mips/psc.h:107`), not a symbol of its own. It is stored at
`-2236(s1)`, inside `psc_mem`.

**Call sites in my `vmlinux`** (equal to those listed at attempt 1):

```
Syscon_cmd            <- psc_syscon_cmd@880d353c, @880d356c  (only caller; baseline callers were the three below)
psc_syscon_cmd        <- _pspSysconGetCtrl2@880cf3a4, pspSyscon_rx_dword@880cf420, pspSyscon_tx_dword@880cf538
psc_xfer_out          <- Syscon_cmd@880cf17c (the single out: hand-off reached by -3, -4, -5 and normal exits)
psc_sc_exit           <- psc_syscon_cmd@880d3548, @880d3578
psp_pacify_watchdog   <- plat_irq_dispatch@880ce958 (880ce950 li v0,2; 880ce954 sw v0,-2236(s1); 880ce968 sw zero,-2236(s1))
                         prom_init@88157424 (88157428 sw v1(=1),-2236(s0) in the delay slot; 8815742c sw zero)
psc_tick_hook         <- plat_irq_dispatch@880ce8bc, @880ce964 (both before psp_uart3_txrx_tick @880ce96c)
T1                       880ce86c mfc0 s2,$9 immediately before 880ce870 mtc0 zero,$9
psc_panel_t2d         <- psc_tick_hook@880d37a0
psc_note_led          <- psp_led_ctrl@880ce9c8 j, @880ce9e0 j (tail calls)
psc_ms_seg_begin/end  <- psp_ms_read@88111858/88111908, psp_ms_make_request@88111be8/88111c98
psc_sched_wake_slow   <- try_to_wake_up@8801c58c
psc_sched_switch_slow <- schedule@8811accc
psc_jp_thread_start   <- psp_joypad_thread@88118208; psc_poll_begin @88118278; psc_poll_end @88118258, @88118af0
psc_fat_mounted       <- fat_fill_super@880b7dbc;  psc_fat_panic <- fat_fs_panic@880b84a8
```

`psc_mem` high-half references (`lui 0x881b`/`0x881c`) exist in
`psp_vcs_ioctl` (4), `mousedev_read` (1), `mousedev_event` (3),
`mousedev_notify_readers` (1), `wb_kupdate` (5), `do_exit` (6) and
`psp_ms_init` (1).

**Symbols missing: none.**

## 5. S5..S20 window of `Syscon_cmd` (C2, D10)

**The two functions.**
- Baseline: `out/20260927T204657Z/vmlinux`, `Syscon_cmd` 880cee10..880cf178,
  218 instructions (`base-Syscon_cmd.dis`).
- Mine: `out/20261006T055351Z/vmlinux`, `Syscon_cmd` 880ceed0..880cf300,
  268 instructions (`new-Syscon_cmd.dis`).

**How `winv2.py` finds the window.** It locates the window by pattern, not by
address:
- S5 is the first `lw` whose base register holds 0xbe240004, found by constant
  propagation over the prologue.
- Segment 1 runs from S5 to the store after `li t3,-4`.
- Segment 2 runs from the ACK-poll exit target to S20. S20 is the first store
  to 0xbe24000c after the store to 0xbe580004 that follows the receive loop.

Output (`syscon-window-compare.txt`):

```
$ python3 winv2.py base-Syscon_cmd.dis new-Syscon_cmd.dis
baseline window: S5 880ceeec .. -4 teardown 880cf020 ; receive 880cf054 .. S20 880cf0bc
new      window: S5 880cefb0 .. -4 teardown 880cf0e4 ; receive 880cf210 .. S20 880cf278
window instructions: base 105 new 105
literal differences (stack offsets and branch targets normalised): 6
   W0   base lw v0,0(s4)        new lw v0,0(s3)
   W3   base sw s6,0(s0)        new sw s5,0(s0)
   W20  base lw s8,N(sp)        new nop
   W58  base sw s5,0(s7)        new sw s4,0(s6)
   W71  base ori a1,s3,0xc      new ori a1,s7,0xc
   W104 base sw s5,0(s0)        new sw s4,0(s0)
register correspondence new->base observed: s3->s4, s4->s5, s5->s6, s6->s7, s7->s3
renaming consistent (one-to-one): True
differences after inverse renaming: 1
   W20  base 880cef3c lw s8,N(sp)   new 880cf000 nop
renamed registers written inside the new window: []
   new s3 = 0xbe240004  base s4 = 0xbe240004  SAME
   new s4 = 0x8         base s5 = 0x8         SAME
   new s5 = 0x8         base s6 = 0x8         SAME
   new s6 = 0xbe240008  base s7 = 0xbe240008  SAME
   new s7 = 0xbe240000  base s3 = 0xbe240000  SAME
MMIO accesses in window (op, address), base 20 new 20, identical in order: True
   lw be240004, sw be24000c, lw be58000c x2, lw be580008, lw be58000c x2, sw be580020, lw be58000c,
   sw be580008, sw be580004, sw be240008, lw be240020, sw be580004, sw be24000c (-4 teardown),
   sw be240024, lw be58000c, lw be580008, sw be580004, sw be24000c (S20)
calls in window: base 0 new 0
gp-relative accesses: base 0 new 0
lui in window: base ['lui v0,0xbe58', 'lui v1,0xbe58'] new ['lui v0,0xbe58', 'lui v1,0xbe58']
non-stack memory ops: base 27 new 27
backward branches (target, branch, body incl. delay slot): base [(21,33,14),(44,54,12),(60,69,11),(82,95,15),(94,98,6)]
                                                           new  [(21,33,14),(44,54,12),(60,69,11),(82,95,15),(94,98,6)] same: True
branch targets as window index: base/new [W35,W35,W28,OUT,OUT,W21,W44,W78,W60,W100,W97,W82,W94] same: True
```

**Judged against the ruled criteria** (DESIGN 2.1 "G2 acceptance criteria",
7.2 §17 R-2):

| Criterion | Result |
|---|---|
| (1) Same instruction count, same loop-body lengths, same branch structure | 105 = 105; five loops with bodies 14/12/11/15/6 on both sides; identical branch-target map. PASS |
| (2) Same MMIO loads and stores in the same order and form (width, base value, offset) | 20 = 20, identical list. PASS |
| (3) No call | 0 / 0. PASS |
| (4) No global load, no base-address reload | 0 gp; the same two `lui 0xbe58` that the baseline has; non-stack memory operations 27 = 27, all MMIO or `rx_buf` stores at the same positions. PASS |
| Allowed difference: stack-slot offsets | Present. Baseline `dmy` 0, `spin` 4. New `dmy` 0, `dlast` 2, `st9` 4, `sttx` 6, `spin` 8, `spin_ack` 12 (`sw s1,8(sp)` at 880cefd0, `sw s1,12(sp)` at 880cf09c) |
| Allowed difference: consistent value-preserving renaming | Present. It is one-to-one, every renamed register holds the same prologue constant, and none is written in the window |
| Allowed difference: delay slot of an exit branch after the exit decision and the path's last MMIO access | Present, once: W20, the first-iteration −3 `j` (baseline 880cef38/3c `j; lw s8,40(sp)`, new 880ceffc/880cf000 `j 880cf0e8; nop`). It runs after `bne v1,a3` has fallen through (with `li t3,-3` in its delay slot) and after the status read at W15. The full-budget −3 exit (`beq v1,v0` / `li t3,-3`) is unchanged |

**Differences beyond those: none inside S5..S20.**

My window equals the one IMPLEMENTATION.md 5.1 reports for the release build
(105 = 105, the same renaming, the same single delay slot). That is expected,
because my `vmlinux` differs from the release only in the banner.

**Outside the window, for completeness.** These are not criteria, but I
report them:
- **Before S5:** the A2 store `sw zero,8(sp)` at 880cef4c runs on every
  attempt.
- **After S20:** baseline `bnezl v0,880cf028 / lw s8,40(sp)` became
  `bnez v0,880cf0e8 / li v0,16`. The exit now goes to the hand-off.
- The hand-off block at 880cf0e8..880cf20c (calls `psc_xfer_out`) sits between
  the two window segments.

All three belong to the R-3 "costs outside the window" that G1 ruled on.

**Timeout patch.**
- The defines at `arch/mips/psp/ipl_sdk/syscon.c:12-13` (`SYSCON_SPIN_MAX
  1000000`, `SYSCON_RETRY_MAX 16`) are byte-identical to `baseline:` (`diff`
  of those lines is empty). `baseline:syscon.c` is identical to the original
  tree's file.
- Drain bound: `syscon.c:162` `spin = SYSCON_SPIN_MAX` and `:165`
  `if(spin-- == 0) { result = -3; goto out; }`.
- ACK bound and −4 teardown: `:203` `spin_ack = SYSCON_SPIN_MAX` and `:206`
  `... REG32(0xbe580004)=4; REG32(0xbe24000c)=0x08; result = -4; goto out;`.
- Retry: `:305-306` `if(++retry_cnt < SYSCON_RETRY_MAX) goto retry;
  result = -5; break;`.
- In the object code the −3 and −4 bounds, the teardown stores and the retry
  test are the same instructions.

Behaviour unchanged. The textual reverse-apply failure (DV-17) is as
reported at attempt 1.

## 6. Userland (C8) and test suites

**pscol sources.** The sha256 values equal IMPLEMENTATION.md 5.4:
`pscol.c 1e89ac0a…`, `main.c c069a958…`, `os_target.c 5e6becf3…`,
`pscol.h 50afcf0a…`, bFLT `7d7a5d78…`.

**Target build.** `cbuild.sh` ran unmodified on a byte-identical copy mounted
over `/work/work/pscol`. The log is `pscol-cbuild.txt`.

```
$ sudo docker run --rm --platform linux/386 -v /home/ubuntu/psp:/work:ro -v /home/ubuntu/psp/work:/work/work \
    -v /home/ubuntu/psp/work/verify-g2-attempt2/scratch/pscol:/work/work/pscol psp-build:bullseye bash /work/work/pscol/cbuild.sh
COMPILE_OK
WARNINGS=0
FP_REGS_USED=0
FP_MNEMONICS=0
FP_MNEMONICS_DESIGN_GREP=0
NM_SOFTFLOAT_LIBM_PRINTF: (none)   MALLOC_SYMBOLS: (none)   FORK_SYMBOLS: (none)
FLTHDR: Magic bFLT, Rev 4, Entry 0x400060, Data Start 0xce20, Data End 0xd980, BSS End 0x28b00,
        Stack Size 0x4000, Reloc Start 0xd980, Reloc Count 0x2b, Flags 0x2 ( Has-PIC-GOT )
SIZES: text 52704 data 2912 bss 110976  (pscol.gdb)
-rwxr--r-- 1 root root 55852 pscol
TEXT(incl. header)=52768 DATA=2912 BSS=110976 STACK=16384 RELOCS=43
BINFMT_FLAT_ALLOC=text+data+bss+stack=183040 -> kmalloc block 262144 per process
```

**My own checks.**
- `grep -c '\$f[0-9]' pscol.dis` gives 0.
- A grep for any COP1 mnemonic (`lwc1|swc1|ldc1|sdc1|mtc1|mfc1|cfc1|ctc1|bc1t|bc1f`)
  gives 0.
- My Python parse of the bFLT header: magic `bFLT`, rev 4, entry 0x400060,
  data_start 52,768, data_end 55,680, bss_end 166,656, stack 16,384,
  reloc_start 55,680, reloc_count 43, flags 2. The file length is
  55,680 + 43 × 4 = 55,852, which equals the file size.

**Against the delivered binary.**
- `cmp -l` against the delivered `work/pscol/pscol` shows 2 bytes, at file
  offsets 0x2a-0x2b: the bFLT `build_date`.
- `pscol.gdb` and `pscol.dis` are byte-identical to the delivered ones.
- Per process: 183,040 B, within one 256 KB block (R-5 bound ≤ 256 KB).

**pscol host tests** (`test/run.sh all 50` on the scratch copy; the log is
`pscol-test-all.log`):

| Test | Result |
|---|---|
| S-record verdict vectors | 28/28 PASS |
| HUD render | PASS (longest line 34) |
| Nominal 5 min, 52 KB/s | PASS (SELFTEST PASS, 0 missing) |
| Step-0 burst | 8/8 PASS |
| TE10 | 6/6 PASS |
| IF7b | PASS (105 names, 13 ticks) |
| IF4 | 200/200 (50 seeds × 4 speeds), 0 missing, 0 violations |
| names (F2, new) | 6/6 cases + parser (11 names) PASS |
| krn (R-4, new) | 2/2 PASS |
| resend (F6, new) | 3/3 PASS (`lost_total` = missing: 915, 1,020, 1,020) |
| Overall | **`RESULT PASS (0 failing cases)`**, rc 0 |

The word "FAIL" appears 14 times in the log. Every occurrence is an expected
`FAILED` verdict in a vector row that is itself marked PASS.

**KRN against the packaged banner (K9).** I ran
`test/pscol_test krn <deploy BUILD/banner.txt> 0x045b27d9` directly. The log
is `pscol-test-krn-packaged.log`; 4/4 PASS:
- the packaged banner with `build_id.txt` gives CRC 045b27d9: green;
- one changed byte gives CRC 60614103: red.

This matches `impl/release-20261006T052947Z/pscol-krn-packaged-banner.txt`.
See finding 1 for the wrapper.

**Decoder** (`python3 test/run_tests.py -v` on a scratch copy; the log is
`decoder-tests.log`):
- **`Ran 37 tests … OK`: 37 pass, 0 fail.**
- By class:

  | Class | Tests |
  |---|---|
  | Shapes | 12 |
  | **ReleaseMaps** (new) | **7** |
  | BuildCheck (new) | 2 |
  | NwordsSevenOrEight (new) | 2 |
  | RawImage | 3 |
  | Robustness | 3 |
  | TwoBoots | 3 |
  | Merge | 2 |
  | Meta | 1 |
  | N4 | 1 |
  | Truncation | 1 |

- **The release-map tests** read `/home/ubuntu/psp/handoff/impl/release-20261006T052947Z/BUILD`
  ("4955 EPC ranges, 25 regmap labels, build_id 0x045b27d9"). All 7 pass:
  - `test_maps_load`;
  - `test_old_grammar_refused`;
  - `test_s11_k` (8 cases);
  - `test_s18_j_pending` (9 cases);
  - `test_eighth_word_every_epc` (18 EPCs);
  - `test_p6_crosscheck`;
  - `test_ledrmw_loaded`.
- `check_format.py` gives `check_format: OK` (355 field comparisons, 253
  constants), rc 0.

## 7. Initramfs (my own extraction, from my build)

```
objdump -h: .init.ramfs VMA 8815e000 size 0x51760 (333,664 B); __initramfs_end 881af760
offset 0x15e000 + 0x51760 = 1,767,264 = len(vmlinux.bin): section ends exactly at the end of the image
zlib gunzip: one member, 0 trailing bytes; cpio 1,313,792 B, sha256 5dde35cd2f372dc174d27ee1694641e5ed4243dcf47b21cfe037e5c8bc85a51a
git show 48dcc1b9:psp-initramfs.cpio | sha256sum -> 5dde35cd...85a51a  (equal)
cpio -itv: -rwxr-xr-x 1 root root 55852 Oct  6 05:27 usr/bin/pscol
extracted usr/bin/pscol sha256 7d7a5d78...f7c454 == work/pscol/pscol (delivered); vs my rebuild: 2 bytes (build_date)
diff of cpio -itv, baseline cpio vs mine: + usr/bin/pscol; etc/rc.sysinit 659 -> 772 B; nothing else
```

- `etc/inittab` has `::sysinit:/etc/rc.sysinit`.
- `diff extract/root2/etc/rc.sysinit` against the extracted file shows only
  added lines 21-23: `printf "…Launching PSC collector…"`, **`pscol&`** (line
  22) and `printf "[  OK  ]…"`.
- These follow `pspmd -s&` (line 18), which is started the same way from
  `/usr/bin`.
- Nothing in the file reads input or waits.

**initramfs_has_pscol: yes. rc_sysinit_starts_pscol: yes.**

## 8. Image size

| File | Reference | Ref size | This build | Release (packaged) | Delta (release) |
|---|---|---|---|---|---|
| `vmlinux.bin` | baseline rebuild = 2008 image decompressed | 1,723,228 | 1,767,264 | 1,767,264 | **+44,036** (5,116 under 49,152) |
| `vmlinux-0.22.bin` | baseline rebuild `work/prebuilt` | 899,402 | 936,713 | 936,714 | **+37,312** (11,840 under) |
| `vmlinux-0.22.bin` | `pspboot-baseline` (what the stick boots today) | 899,282 | 936,713 | 936,714 | +37,432 |
| `vmlinux-0.22.bin` | baseline normal build `out/20260927T204657Z` | 899,404 | 936,713 | 936,714 | +37,310 |
| `vmlinux.bin` | G2 attempt-1 release | 1,766,859 | | 1,767,264 | +405 |
| `vmlinux-0.22.bin` | G2 attempt-1 release | 936,321 | | 936,714 | +393 |
| BSS (`_end − __bss_start`) | baseline 0x11230 = 70,192 | | 0xb0b50 = 723,792 | same | +653,600 (not in the image) |

These equal IMPLEMENTATION.md 1.4 to the byte. All growth since attempt 1 is
`.init.ramfs` (+405 B), because `System.map` differs from the attempt-1
release only in `__initramfs_end`. Both images are within the R-5 bound.

**Whether pspboot loads 1,767,264 B uncompressed is UNVERIFIED** (OD-9, R20).
No hardware exists.

## 9. Package

```
$ cd /home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE && sha256sum -c ../../../SHA256SUMS
EBOOT.PBP: OK   kmodlib.prx: OK   pspboot.conf: OK   vmlinux-0.22.bin: OK     (rc 0)
$ cmp {EBOOT.PBP,pspboot.conf,kmodlib.prx} /home/ubuntu/psp/pspboot-baseline/   -> identical (all three)
$ cmp vmlinux-0.22.bin /home/ubuntu/psp/work/out/20261006T052947Z/vmlinux-0.22.bin -> identical (4f9b69dc...cac8)
folder contents: EBOOT.PBP kmodlib.prx pspboot.conf vmlinux-0.22.bin   (RUNBOOK "What you need": exactly these four)
pspboot.conf: kernel=vmlinux-0.22.bin ; cmdline=console=tty osk=Dv4   (verbatim baseline; file present under that name)
name 'uClinux_TRACE' vs 'uClinux' / 'uClinux_FIX' / 'uClinux_WIP' (case-insensitive equality): False, False, False
$ cd ../../../BUILD && sha256sum -c SHA256SUMS   -> all 8 OK
BUILD/IMAGE.sha256: 4f9b69dc...cac8  vmlinux-0.22.bin ; BUILD/build_id.txt 0x045b27d9 = zlib.crc32(BUILD/banner.txt)
diff -r deploy/uClinux_TRACE/BUILD handoff/impl/release-20261006T052947Z/BUILD -> identical
cmp BUILD/vmlinux out/20261006T052947Z/vmlinux -> identical
```

`PROVENANCE.txt` names:
- out dir `20261006T052947Z`;
- commit `48dcc1b9`, with no tracked changes;
- the release banner (05:32:47);
- `build_id` `0x045b27d9`.

**Package correct.** G3 R3 must use the packaged checksum,
`4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8`, not the
checksum of this verification build.

---

## 10. Re-check of the attempt-1 findings

**G2-attempt1-verify.md**

| Finding | Status at attempt 2 (my evidence) |
|---|---|
| 1 Window not literally identical (OD-2; blocking under the attempt-1 rule) | **Closed by ruling §17 R-2.** The window meets every ruled criterion, and only the three allowed differences occur (section 5) |
| 2 pscol memory over 128 KB (OD-5) | **Closed by ruling R-5.** 183,040 B, one 256 KB block per process (section 6) |
| 3 Image growth near the bound; pspboot load unverified (OD-6) | Growth restated and re-measured: +44,036 / +37,312, inside the bound. **pspboot load still UNVERIFIED** (OD-9). Open, non-blocking, needs the device |
| 4 Release sha256 is per-build | Reproduced: my rebuild is `1b20768b…` with `build_id` `0x608a79f9`, banner-only different. The package carries the release's `BUILD/` with `IMAGE.sha256` and `build_id.txt`, and the decoder refuses another build's `build_id` (BuildCheck test passes). Handled |
| 5 Timeout patch does not reverse-apply textually (DV-17) | Behaviour unchanged (section 5). Noted as at attempt 1 |

**G2-attempt1-review.md**

| Finding | Status (my evidence) |
|---|---|
| F1 / DV-3 `nwords` 7 for 8 words ending 0xFFFF | Ruled §17 R-1 option (a). The kernel is unchanged since attempt 1 (`git diff c135ecdd..48dcc1b9` touches only the cpio). The decoder's `NwordsSevenOrEight` tests pass (2/2) |
| F2 run number / `nnn` scan | Fixed. `pscol.c:2153-2174` (`pscol_tname`: 11 characters, dot at 7, `nm[0]` T or t, `bin` case-folded) and `:2178-2197` (`pscol_run_scan`), called at `main.c:93`. Host `names` tests 6/6 + parser PASS, with lower-case `t001001.bin` from an earlier boot giving `rrr` 2. The fixed binary is in my image's initramfs |
| F3 decoder cannot read the kernel maps | Fixed. ReleaseMaps 7/7 PASS on the release `BUILD/`. My regenerated maps are identical to the release maps apart from the header lines |
| F4 KRN `build_id` | Fixed as ruled. `krn` 2/2 PASS, plus packaged banner 4/4 PASS; decoder BuildCheck 2/2 PASS |
| F5 cost and stack restatement | IMPLEMENTATION 9.2 restates it from executed code. **Not re-measured by me** (outside the verifier's step list), and listed as OD-7 for the reviewer. Nothing is in the window (section 5) |
| F6 re-send double count | Fixed. `resend` 3/3 PASS |
| F7 commit provenance | `48dcc1b9` author is `Stage 2 kernel implementer (Claude agent) <stage2-kernel-implementer@localhost>`. Earlier history is not rewritten, and IMPLEMENTATION 2.1 names the real author |

## Findings

All of the following are non-blocking. None meets a FAIL condition of this
task.

1. **`test/run.sh krn <banner> <build_id>` does not pass the packaged
   banner (test tooling).**
   - *Where:* `work/pscol/test/run.sh` last line,
     `./pscol_test "${1:-all}" "${2:-20}"`. It forwards only two arguments,
     but `test/sim.c:1699-1700` needs `argc > 3` to run the packaged-banner
     cases.
   - *Problem:* the usage line in `run.sh` documents the 3-argument form.
     That form silently runs only the two simulated KRN cases and still
     prints `RESULT PASS`.
   - `checks.sh` also calls `./pscol_test krn` with no banner, so
     `CHECKS.txt:149-151` has 2 KRN rows, not 4.
   - The packaged-banner evidence exists only as
     `impl/release-20261006T052947Z/pscol-krn-packaged-banner.txt`. I
     reproduced it by calling `pscol_test` directly (4/4 PASS).
   - *To close it:* forward `"$@"` in `run.sh`, and have `checks.sh` run the
     packaged form.
2. **pspboot loading the 1,767,264-B image is UNVERIFIED** (OD-9 / R20).
   - The growth is inside the R-5 bound (+44,036, 5,116 B margin).
   - *To close it:* a boot on the device. An abort there costs no run
     (DESIGN 8.3).
3. **Release identity is per-build.**
   - My rebuild of the same commit has a different image hash (`1b20768b…`)
     and `build_id` (`0x608a79f9`).
   - G3 R3 must use `4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8`.
   - The decoder must use the packaged `BUILD/` (`build_id` `0x045b27d9`).
     The package already does this.
   - *To close it:* G3 records the packaged checksum.
4. **Outside-window costs (OD-7) were not re-measured by me.**
   - IMPLEMENTATION 9.2 states watchdog-tick figures above the 5.4/7.1
     estimates: +922 instructions, ≈ 4.2 µs; +1,104 on a straddle; +48 per
     tick; 1.03 ms per panel paint.
   - These are outside S5..S20, so they are not part of the window criteria.
   - *To close it:* a G2 reviewer or G1 text ruling on OD-7, as the
     implementer asks.

## State left behind

- `work/linux` is on `stage2-trace` @ `48dcc1b9`, with 0 tracked changes. Its
  in-tree build products are now those of my build.
- New:
  - `work/out/20261006T055351Z`;
  - `work/logs/build-20261006T055351Z.log`;
  - `work/verify-g2-attempt2/`, which holds the logs, listings, scripts,
    scratch copies, the extracted initramfs and `BUILD-verifier/`.
- `work/pscol`, `work/decoder`, `work/deploy` and every handoff file other
  than this report are unchanged.
- Original tree manifest: exit 0.
