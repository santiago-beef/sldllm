# G2 attempt 1: verifier report

Verifier: Opus 5.5, fresh context. I was not an implementer, designer or reviewer.
Date: 2026-10-06. I built and measured everything below myself, and I re-ran
each number I took from IMPLEMENTATION.md.

Inputs read: DOSSIER.md (section 9, including 9.6 and 9.8), WORKFLOW.md (Stage 2,
G2), design/DESIGN.md rev 6 (sections 2.1-2.12, 4.2, 5.3, 7.1, 7.2, 7.6, 7.7 and 9),
recon/build.md (1.3 in particular), gates/LOG.md and impl/IMPLEMENTATION.md.

Evidence files (copies of the full logs and the scripts I used):
`/home/ubuntu/psp/work/verify-g2-attempt1/`. I wrote nothing in the original
tree, and nothing in `work/pscol`, `work/decoder` or `work/deploy`. The pscol
build and both test suites ran on scratch copies.

## Verdict: FAIL

Only one rule produces the FAIL: the task says FAIL if "the syscon window
differs", and it differs. Section 5 has the details. The difference is the one
the implementer already reported as **OD-2**: five callee-saved registers are
renamed consistently, stack slot offsets change, and one delay slot differs
after the −3 exit decision. Under the design's own acceptance criteria for the
window (DESIGN 2.1 "G2 acceptance criteria", 7.2) the window **passes**:

- 105 instructions on each side;
- the same MMIO loads and stores, in the same order and form;
- the same loop bodies and branch structure;
- 0 calls, 0 global loads, 0 gp-relative loads;
- no base-address reloads beyond the two the baseline already has.

The verifier cannot resolve OD-2. Under WORKFLOW principle 3 only the human
operator can waive an item, so I report the literal result. Every other check
passes.

| # | Check | Result |
|---|---|---|
| 1 | Original tree manifest | exit 0 (at start and again at the end) |
| 2 | Clean build of `stage2-trace` HEAD `c135ecdd` | OK. The sha256 differs from IMPLEMENTATION.md, but **only in the banner** (8 bytes) |
| 3 | New warnings in changed files | none. The 38 distinct warnings are identical to both 20260927 baseline logs |
| 4 | Symbols and capture sites (C7) | all present |
| 5 | D10 window (C2) | **not literally identical**. It meets the DESIGN 2.1/7.2 criteria (OD-2) |
| 6 | Userland (C8) | 0 FP registers, 0 FP mnemonics, valid bFLT, 55,044 B. pscol tests all PASS; decoder 26/26 OK |
| 7 | Initramfs | pscol is present with mode 0755. `rc.sysinit` starts it after `pspmd`, and nothing waits for input |
| 8 | Image size | +43,631 B (`vmlinux.bin`), within the 48 KB bound. Whether pspboot loads it is **UNVERIFIED** |
| 9 | Package | OK |

---

## 1. Original tree intact

```
$ cd /home/ubuntu/psp/build/linux && sha256sum -c --quiet /home/ubuntu/psp/handoff/gates/baseline-tree.sha256; echo "EXIT=$?"
EXIT=0
```

I ran it before any work and again after all work. Both runs exited 0 with no
output.

## 2. Clean build

```
$ cd /home/ubuntu/psp/work/linux && git checkout -q stage2-trace && git rev-parse HEAD
c135ecdd7da7efc4ef64e531b74b12d1982d3be2
$ /home/ubuntu/psp/work/build.sh
log: /home/ubuntu/psp/work/logs/build-20261006T022828Z.log
out: /home/ubuntu/psp/work/out/20261006T022828Z
RC=0
```

The log header and tail:

```
git HEAD:    c135ecdd7da7efc4ef64e531b74b12d1982d3be2 (initramfs: add pscol, start from rc.sysinit (DESIGN 4.2))
git status (before clean, tracked changes only):            <- empty
image:       psp-build:bullseye (sha256:77a15780...be2de8)
hostname:    psp-work-build
=== clean: git clean -fdxq
untracked/ignored files after clean: 0
MAKE_EXIT:0
BUILD_EXIT:0
CONTAINER_WALL_SECONDS:210
71beda70d3b9bfd20d59e4d94bf0641c951f7846b2c692a30a85c90064207308  vmlinux
483e61d0d2862ec81659034d5299862f3918ed39e93c089cfb37ec488dc973f4  vmlinux.bin
e7ffdd2c52567b6879d30d6c5e0bd30783deb938e64e89e7d7490f3d8e574549  vmlinux-0.22.bin
33b953409d6ce0896cfc1e9c320ab1a4332d85d99fe426f9ec9d6d6d82f05db4  System.map
Linux version 2.6.22 (root@psp-work-build) (gcc version 4.2.1) #1 PREEMPT Tue Oct 6 02:31:51 UTC 2026
```

The build used `.config:163` `/work/work/linux/psp-initramfs.cpio`, as recon/build.md
1.3 requires. `usr/.initramfs_data.cpio.gz.cmd` reads
`... gen_initramfs_list.sh -o usr/initramfs_data.cpio.gz -u 0 -g 0 /work/work/linux/psp-initramfs.cpio`.

**Comparison with IMPLEMENTATION.md 1.2** (`out/20261006T021722Z`, sha256
`c72459e3...d38b738`):

- The sha256 does **not** match: mine is `e7ffdd2c...4549`, 936,322 B; theirs
  is 936,321 B.
- `System.map` is identical (`33b95340...`).
- `cmp -l` on the two `vmlinux.bin` files gives 8 differing bytes, and
  `cmp -l` on the two `vmlinux` files also gives 8.
- The differing bytes are at offsets 1179736-1179740 and 1275360-1275364, and
  both places are the banner time string. My build has `02:31:51` and theirs
  has `02:20:38` (in `linux_banner` and in the `utsname` version).

**The difference is banner-only.** The 1-byte gzip size difference follows from
that.

## 3. Warnings

```
$ grep 'warning:' build-20261006T022828Z.log | sort -u | wc -l      -> 38 (40 lines)
$ diff <(sort -u warnings of build-20260927T204657Z.log) <(... build-20261006T022828Z.log)   -> no difference
$ diff <(sort -u warnings of build-20260927T204324Z.log) <(... build-20261006T022828Z.log)   -> no difference
```

The set is identical to both 20260927 baseline logs, including line numbers.

I checked the changed files (`git diff --name-only baseline..stage2-trace`, 19
files) separately:

- No warning line names any of them.
- No `In file included from` chain mentions any of them.
- All 14 changed C units appear as `CC` lines in the log.

**New warnings in changed files: none.**

## 4. Symbols and capture sites (C7)

I made `nm -n` and `objdump -d` of the new `vmlinux` and of the baseline
`out/20260927T204657Z/vmlinux` in the container. The call sites come from
`work/verify-g2-attempt1/calls.py`, and the full list is in `callsites.txt`.

**New global and static functions present in `nm`:**

- the recorder: `psc_syscon_cmd`, `psc_sc_exit`, `psc_xfer_out`, `psc_fill_sc`,
  `psc_syscon_end_calc`, `psc_dcount`, `psc_cur_regs`, `psc_class`;
- hooks: `psc_tick_hook`, `psc_note_led`, `psc_ms_seg_begin`,
  `psc_ms_seg_end`, `psc_sched_wake_slow`, `psc_sched_switch_slow`,
  `psc_jp_thread_start`, `psc_poll_begin`, `psc_poll_end`;
- FAT and the semaphore accessors: `psc_fat_mounted`, `psc_fat_panic`,
  `psc_fat_rdonly`, `psc_console_sem_count`, `psc_jp_list_sem_count`;
- `/proc/psc`: `psc_ring_open`, `psc_ring_read`, `psc_ring_llseek`,
  `psc_stats_read`, `psc_ctl_write`, `psc_init` (registered through
  `__initcall_psc_init7`);
- the panel: `psc_panel_t2d`, `psc_panel_fill`, `psc_panel_account`,
  `pl_ch`, `pl_str`, `pl_hex`, `pl_dec`, `pl_age`.

**New data objects:** `psc_mem` (B), `psc_jp_task` (B), `psp_local_tick` (B,
replacing the static `localTick`), `psc_syscon_end`, `psc_fat_sb`,
`psc_font`, `psc_guard_word`, `psc_ring_desc`, `psc_ring_fops`,
`psc_stats_fops` and `psc_ctl_fops`.

**Inlined by gcc 4.2.1, not standalone symbols.** These are expected: each is
`static` (or `static inline` in `psc.h`) and has a single call site inside a
function that is present.

| Helper | Inlined into |
|---|---|
| `psc_sc_entry` | `psc_syscon_cmd` |
| `psc_fill_thread`, `psc_fill_wext` | `psc_sc_exit` (`psc.c:454`, `:505`) |
| `psc_t2d` | `psc_tick_hook` (`:617`), which calls `psc_panel_t2d` |
| `psc_stats_snapshot` | `psc_stats_read` (`:1132`), which calls both accessors |
| `psc_panel_lines`, `psc_panel_text`, `psc_glyph` | `psc_panel_t2d` |
| `psc_sched_wake`, `psc_sched_switch` (inline gates) | their callers |
| `psc_jp_stage`, `psc_jp_stage_arg` | the joypad functions |

**Capture calls at the intended sites (new `vmlinux`):**

| Site (design §) | Evidence |
|---|---|
| `Syscon_cmd` exit path (2.1 A4) | `Syscon_cmd@880cf17c jal psc_xfer_out`, on the single `out:` block that the −3, −4, −5 and normal exits all reach (`+0x218`) |
| Recording wrapper (2.1, DV-1) | `psc_syscon_cmd` calls `Syscon_cmd` (`880d353c`, `880d356c`), then `psc_sc_exit` (`880d3548`, `880d3578`) |
| Callers redirected | `_pspSysconGetCtrl2@880cf3a4`, `pspSyscon_rx_dword@880cf420`, `pspSyscon_tx_dword@880cf538` → `psc_syscon_cmd`. Nothing outside `psc_syscon_cmd` calls `Syscon_cmd` any more (in the baseline those three called it directly) |
| Watchdog Nop, timer path (2.2) | in `plat_irq_dispatch`: `880ce950 li v0,2`, `880ce954 sw v0,-2236(s1)` (`wd_ctx` = 2), `880ce958 jal psp_pacify_watchdog`, then `880ce968 sw zero,-2236(s1)` (`wd_ctx` = 0, in the delay slot of the next `jal`) |
| Watchdog Nop, `prom_init` (2.2) | `88157424 jal psp_pacify_watchdog` with `88157428 sw v1(=1),-2236(s0)` in the delay slot (before the call), then `8815742c sw zero,-2236(s0)` |
| T1 (2.3) | `mfc0 s2,$9` immediately before `mtc0 zero,$9` in `plat_irq_dispatch`. `c_pre_cur` is stored at `880ce8b8` |
| Timer hook and panel check (2.3 T2/T2d, 2.10) | `plat_irq_dispatch@880ce8bc` and `@880ce964 jal psc_tick_hook` (non-watchdog and watchdog paths), both before `psp_uart3_txrx_tick`. `psc_tick_hook@880d37a0 jal psc_panel_t2d` |
| Scheduler hooks (2.11) | `try_to_wake_up@8801c58c jal psc_sched_wake_slow`, `schedule@8811accc jal psc_sched_switch_slow` |
| Joypad poll loop (2.5) | `psp_joypad_thread`: `@88118208 jal psc_jp_thread_start`, `@88118278 jal psc_poll_begin`, `@88118258` and `@88118af0 jal psc_poll_end`. The function grew from 364 to 662 instructions (stages and counters inline) |
| MS driver (2.4) | `psp_ms_read@88111858/88111908` and `psp_ms_make_request@88111be8/88111c98` (`psp_ms_write` is inlined there) → `psc_ms_seg_begin` and `psc_ms_seg_end`. `psp_ms_init` references `psc_mem` (`ms_part_start`) |
| LED read-back (2.4) | `psp_led_ctrl@880ce9c8`, `@880ce9e0 j psc_note_led` (tail calls; `psp_gpio_set`/`clear` are inlined) |
| FAT (2.12) | `fat_fill_super@880b7dbc jal psc_fat_mounted`, `fat_fs_panic@880b84a8 jal psc_fat_panic` |
| Above-driver counters (2.6, 2.7) | `psc_mem` references in `psp_vcs_ioctl` (4), `mousedev_read`, `mousedev_event`, `mousedev_notify_readers`, `wb_kupdate` and `do_exit` |

**Symbols missing: none.**

## 5. D10 window (C2)

The window is compared from the first MMIO access (S5,
`lw REG32(0xbe240004)`) to the last (S20, `sw 0x08 → 0xbe24000c`).

- Baseline: `out/20260927T204657Z/vmlinux`, `Syscon_cmd` at `880cee10`, 218
  instructions.
- New: `out/20261006T022828Z/vmlinux`, `Syscon_cmd` at `880ceed0`, 268
  instructions.

Both are extracted from `objdump -d` and compared with
`work/verify-g2-attempt1/win.py`. The full output is in
`syscon-window-compare.txt`, and the two listings are kept as `*.dis`.

The window is not contiguous in either build: the −4 teardown is followed by
exit code, and the receive part is placed after it. So I compared it as two
segments:

| Build | Segment 1 (S5 … −4 teardown) | Segment 2 (receive … S20) |
|---|---|---|
| Baseline | listing lines 56-133 | listing lines 146-172 |
| New | listing lines 57-134 | listing lines 209-235 |

```
window instructions: base 105, new 105
LITERAL comparison (addresses stripped): differs
  registers:   lw v0,0(s4) -> lw v0,0(s3); sw s6,0(s0) -> sw s5,0(s0); sw s5,0(s7) -> sw s4,0(s6);
               ori a1,s3,0xc -> ori a1,s7,0xc; sw s5,0(s0) -> sw s4,0(s0)   (S20)
  stack slots: spin 4(sp)->8(sp); dlast sh 0(sp)->2(sp); st9 0->4; sttx 0->6; spin_ack 4(sp)->12(sp); dmy stays 0(sp)
  one delay slot:  base  "j <exit>; lw s8,40(sp)"   new  "j <out>; nop"     (the first -3 exit decision)
  branch targets outside the window (exit blocks) differ in address, as expected
AFTER inverse renaming s7->s3, s3->s4, s4->s5, s5->s6, s6->s7, stack offsets and branch targets masked:
  only remaining difference:  -lw s8,N(sp)  +nop   (delay slot of the -3 exit jump)
MMIO-form loads/stores identical in order after renaming: True
calls in window: base 0 new 0
lui in window: base ['lui v0,0xbe58', 'lui v1,0xbe58'] new ['lui v0,0xbe58', 'lui v1,0xbe58']
gp-relative: base 0 new 0
branch targets as window index:  base [35,35,28,OUT,OUT,21,44,78,60,100,97,82,94]
                                 new  [35,35,28,OUT,OUT,21,44,78,60,100,97,82,94]  same: True
```

**Result: NOT identical.**

- **Against the DESIGN 2.1 criteria the window meets every one:** the same
  MMIO in the same order and form, loop bodies with the same instruction
  counts, no added calls, no global loads, and no base reloads.
- **Against the design's descriptive text it does not hold:** 7.2 says "another
  slot gives the same instructions at another offset", and that does not
  cover renamed registers.
- My measurement reproduces IMPLEMENTATION.md 5.1 / DV-4 exactly: 105 = 105,
  the same renaming map, and the same single delay slot.

**Timeout patch.** It is still there and behaves the same:

- `SYSCON_SPIN_MAX 1000000` and `SYSCON_RETRY_MAX 16` are at `syscon.c:12-13`.
- The drain bound is still `spin = SYSCON_SPIN_MAX`, and −3 is returned
  through `out:`.
- The ACK bound is still `SYSCON_SPIN_MAX`, now held in `spin_ack`. The −4
  teardown writes `0xbe580004=4` and `0xbe24000c=8` are unchanged.
- The −5 path still uses `++retry_cnt < SYSCON_RETRY_MAX`.

Its hunks no longer apply textually: `patch -R --dry-run` of
`work/syscon-timeout.applied.patch` on the new file fails hunks 2-4, while on
the baseline it gives rc 0. This is DV-17, and C2 is for the reviewer to rule.

**Watchdog code.** As DV-7 says, the `lastTick` store still sits in the delay
slot of `jal psp_pacify_watchdog` (the baseline does the same), and only the
`wd_ctx` stores and the T1/`psc_tick_hook` instructions are added around it.

## 6. Userland (C8)

**Build.** `cbuild.sh` was run unmodified, on a byte-identical copy of
`work/pscol` mounted at `/work/work/pscol`, so that the delivered binary was
not overwritten. The source sha256 values match IMPLEMENTATION.md 5.4.

```
$ sudo docker run --rm --platform linux/386 -v /home/ubuntu/psp:/work:ro -v /home/ubuntu/psp/work:/work/work \
    -v <scratch>/pscol-copy:/work/work/pscol psp-build:bullseye bash /work/work/pscol/cbuild.sh
COMPILE_OK
WARNINGS=0
FP_REGS_USED=0
FP_MNEMONICS=0
FP_MNEMONICS_DESIGN_GREP=0          (DESIGN 7.7 grep: lwc1|swc1|ldc1|sdc1|mtc1|mfc1|cfc1|ctc1|cvt\.)
NM_SOFTFLOAT_LIBM_PRINTF: (none)    MALLOC_SYMBOLS: (none)    FORK_SYMBOLS: (none)
FLTHDR: Magic bFLT, Rev 4, Entry 0x400060, Data Start 0xcb00, Data End 0xd650, BSS End 0x28ea0,
        Stack Size 0x4000, Reloc Start 0xd650, Reloc Count 0x2d, Flags 0x2 (Has-PIC-GOT)
SIZES: text 51904 data 2896 bss 112720
-rwxr--r-- 1 root root  55044 pscol
DATA+BSS+STACK=132000 (design 4.2/5.3 figure: <= 131072 without text)
BINFMT_FLAT_ALLOC=text+data+bss+stack=183968 -> kmalloc block 262144 per process
```

**Comparison with the delivered binary.**

- My `pscol` differs from the delivered `work/pscol/pscol` (sha256
  `e5090df3...`) in 2 bytes only, at offsets 0x2a-0x2b: the bFLT `build_date`
  field.
- My `pscol.gdb` and `pscol.dis` are byte-identical to the delivered ones.

**bFLT header check.**

- The header has the same form (rev 4, entry `0x400060`, PIC-GOT) as the 2008
  `pspmd` in the initramfs and as `telem`, both of which run on the device.
- The file length is consistent with the header: 0xd650 + 45 × 4 = 55,044.

**Host tests** (`test/run.sh all 50` on the scratch copy; the log is
`pscol-test-all.log`):

| Test | Result |
|---|---|
| Verdict vectors | 28/28 PASS |
| HUD render | PASS (longest line 34) |
| Nominal 5 min | PASS (SELFTEST PASS, 0 missing) |
| Step-0 burst | 8/8 |
| TE10 | 6/6 |
| IF7b | PASS (105 names, 13 ticks) |
| IF4 | 200/200 (50 seeds × 4 speeds) |
| Overall | `RESULT PASS (0 failing cases)` twice. 0 FAIL lines |

**Decoder** (`python3 test/run_tests.py -v` on a scratch copy):
`Ran 26 tests in 48.856s OK`, so 26 pass and 0 fail. `check_format.py` gives
`check_format: OK` (355 field comparisons, 253 constants).

## 7. Initramfs (my own extraction, from my build)

```
.init.ramfs  VMA 8815e000 size 0x515cb, ends exactly at the end of vmlinux.bin (1,766,859)
gunzip(vmlinux-0.22.bin) == vmlinux.bin: True; one gzip member, 0 trailing bytes
decompressed cpio: 1,313,280 B, sha256 012cdc3317106652d23d1b95d774add24004dcd84729faf7b1f70d477b8ca6b2
  == git show stage2-trace:psp-initramfs.cpio  (baseline cpio is ba50da6a...fada5)
cpio -itv: -rwxr-xr-x 1 root root 55044 Oct 6 02:16 usr/bin/pscol
extracted usr/bin/pscol sha256 e5090df3...1c9b6a == delivered work/pscol/pscol
diff of cpio -itv listings, baseline vs new: only + usr/bin/pscol and etc/rc.sysinit 659 -> 772 B
```

- `etc/inittab` has `::sysinit:/etc/rc.sysinit`.
- The extracted `etc/rc.sysinit` differs from `extract/root2/etc/rc.sysinit`
  only by the lines added at 21-23.
- Those lines come after `pspmd -s&` at line 18, and `pscol&` at line 22 runs
  in the background.
- No line waits for input. The supervisor calls `setsid()` and puts
  `/dev/null` on fds 0-2 (`main.c:115-116`), as DESIGN 4.2 specifies.

## 8. Image size

| File | Reference | Ref size | This build | Delta |
|---|---|---|---|---|
| `vmlinux-0.22.bin` | `pspboot-baseline` (2008 uc1, sha256 `628dddfe...`) | 899,282 | 936,322 | **+37,040** |
| `vmlinux-0.22.bin` | baseline normal build `out/20260927T204657Z` | 899,404 | 936,322 | +36,918 |
| `vmlinux-0.22.bin` | baseline reproduce build (= original) | 899,402 | 936,322 | +36,920 |
| `vmlinux.bin` | baseline (and the 2008 image decompressed) | 1,723,228 | 1,766,859 | **+43,631** |
| BSS | baseline | 70,192 | 723,792 | +653,600 (not in the image) |

- The packaged image (the implementer's build) is 936,321 B, which is +37,039
  against `pspboot-baseline`.
- The DESIGN 5.3 bound is ≤ 48 KB growth for each file. It is met for both:
  `vmlinux.bin` has 5,521 B of margin to 49,152.
- **Whether pspboot can load the larger image (1,766,859 B uncompressed,
  936,321/936,322 B compressed) is UNVERIFIED.** There is no hardware here.
  This is OD-6 / R20.

## 9. Package

```
$ cd /home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE && sha256sum -c ../../../SHA256SUMS
EBOOT.PBP: OK   kmodlib.prx: OK   pspboot.conf: OK   vmlinux-0.22.bin: OK      (rc 0)
cmp EBOOT.PBP / pspboot.conf / kmodlib.prx  vs /home/ubuntu/psp/pspboot-baseline/  -> identical (all three)
cmp vmlinux-0.22.bin vs out/20261006T021722Z/vmlinux-0.22.bin -> identical (sha256 c72459e3...d38b738)
pspboot.conf: kernel=vmlinux-0.22.bin   (file present in the folder under that name)
folder contents: EBOOT.PBP kmodlib.prx pspboot.conf vmlinux-0.22.bin
name uClinux_TRACE vs uClinux / uClinux_FIX / uClinux_WIP (case-insensitive): no collision
```

The packaged kernel is the implementer's release build, `c72459e3...`. It
differs from the build I verified only in the 8 banner bytes (section 2). G3 R3
must use the packaged checksum, `c72459e3e70f72605ffe35fc371ca8b93f9e7ab53d7fdac25021a0896d38b738`.

## Findings

1. **BLOCKING under the task's verdict rule: the D10 window is not literally
   identical (OD-2).**
   - What I measured: consistent renaming s3→s7, s4→s3, s5→s4, s6→s5, s7→s6;
     shifted stack slots; one delay slot after the −3 exit (`lw s8` → `nop`).
   - What is the same: 105 = 105 instructions, the same MMIO order and form,
     0 calls, 0 global loads, and identical branch structure.
   - It passes DESIGN 2.1/7.2's criteria.
   - **To close it:** either a ruling by the human (or the G2 reviewer, if the
     human delegates it) that DESIGN 2.1's criteria are the test and not
     literal identity, or a build whose window is literally identical apart
     from stack offsets. The implementer reports that every placement of the
     A2 store tried caused the renaming.
2. **Not blocking: pscol memory exceeds the design figure (OD-5).**
   - data + bss + stack = 132,000 B, which is above 131,072 even without text.
   - With text, as this kernel's `binfmt_flat` forces, it is 183,968 B, and
     the `kmalloc` block is 262,144 B per process (two processes).
   - DESIGN 4.2/5.3 says "one 128 KB block each; G2 C8 records the figure
     (≤ 128 KB)".
   - **To close it:** the G2 reviewer or the human accepts the figure, or
     pscol is trimmed.
3. **Not blocking: the image growth is close to the bound, and loading is
   unverified (OD-6).**
   - `vmlinux.bin` +43,631 B against a bound of 48 KB.
   - pspboot loading of the larger image is UNVERIFIED.
   - **To close it:** human acceptance, or a hardware boot test.
4. **Not blocking: the release sha256 is per-build.**
   - Any rebuild changes the banner and therefore `build_id` (OD-3: the kernel
     defines it as the CRC-32 of the banner).
   - The packaged image is `c72459e3...` with `build_id` `0x9b3c599e` per
     IMPLEMENTATION.md. My verification build is banner-different
     (`e7ffdd2c...`).
   - **To close it:** G3 uses the packaged checksum, and the decoder's
     `build_id`/maps come from `out/20261006T021722Z`, not from this
     verification build.
5. **Not blocking: the timeout patch no longer reverse-applies textually
   (DV-17).** Its defines, bounds, teardown writes and return codes are
   unchanged (section 5). **To close it:** a C2 ruling by the G2 reviewer.

## State left behind

- `work/linux` is on `stage2-trace` @ `c135ecdd`, with no tracked changes. Its
  in-tree build outputs are now those of my build.
- New: `out/20261006T022828Z`, `logs/build-20261006T022828Z.log` and
  `work/verify-g2-attempt1/`.
- `work/pscol`, `work/decoder` and `work/deploy` are unchanged.
- Original tree manifest: exit 0.
