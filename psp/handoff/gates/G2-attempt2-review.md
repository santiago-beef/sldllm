# Gate G2, attempt 2: code review

Reviewer: G2 code reviewer, attempt 2. Fresh context. I was not an implementer,
integrator, designer or earlier reviewer, and I did not write any artifact
under review.
Date: 2026-10-06.

**Artifact**
- Branch `stage2-trace` @ `48dcc1b9` in `/home/ubuntu/psp/work/linux`, diffed
  against `baseline` `775f8372`. `git diff --stat c135ecdd..48dcc1b9` touches
  only `psp-initramfs.cpio`.
- `/home/ubuntu/psp/work/pscol/` and `/home/ubuntu/psp/work/decoder/`. Every
  sha256 equals IMPLEMENTATION.md 5.4 (I re-ran `sha256sum` on all 24 listed
  files).
- `handoff/impl/IMPLEMENTATION.md` (attempt-2 revision),
  `handoff/impl/release-20261006T052947Z/`, and the package
  `work/deploy/uClinux_TRACE`.

**Specification**
- `design/DESIGN.md` revision 7: revision 6 plus the A7 edits plus section 17.
- I checked that `diff -u DESIGN.r7.md DESIGN.md` equals `g1ruling.diff` after
  its two header lines, and that `RUNBOOK.md` is byte-equal to `RUNBOOK.r7.md`.
- The ruling was accepted by `gates/G1-ruling1-review.md` (PASS) and
  `gates/G1-ruling1-redteam.md` (PASS).

**Attempt-1 sources for comparison**
- `orig/` in the shared scratchpad holds the attempt-1 sources. Their sha256
  values equal the attempt-1 values in IMPLEMENTATION.md 5.4: `pscol.c`
  `6fd80760…`, `main.c` `61770c8b…`, `pscol.h` `5beecf47…`, `pscdec.py`
  `7111cb01…`, `pscdec_parse.py` `07399bed…`, `pscdec_analysis.py` `dd1e5033…`.
- Every pscol and decoder change below comes from `diff -u` against those
  files.

## Verdict: **PASS**

- No checklist item fails, blocking or not.
- Every finding of G2 attempt 1, from the review and from the verifier, is
  closed. Section 6 gives the evidence for each.
- No deviation touches a blocking G1 item beyond what section 17 ruled.
  Section 7 explains why OD-7, the measured costs, is not such a deviation.
- Three non-blocking findings remain (N1-N3, section 8). None of them is a
  checklist FAIL.
- **For the orchestrator:** N1 and N2 need entries in the gate log before G3
  R1 ("no open findings").

| ID | B | Result |
|---|---|---|
| C1 | B | PASS |
| C2 | B | PASS |
| C3 | B | PASS |
| C4 | B | PASS |
| C5 | B | PASS |
| C6 | B | PASS (reviewer scope) |
| C7 | B | PASS |
| C8 | B | PASS |
| C9 | | PASS |
| C10 | | PASS |

Rule check: blocking FAILs 0; non-blocking FAILs 0; missing evidence none;
design deviations touching a blocking G1 item beyond section 17: none.
**PASS.**

---

## 1. Checklist C1-C10 (summary; details in sections 2-5)

| ID | B | Result | Evidence |
|---|---|---|---|
| C1 | B | PASS | **Formats:** the record format is unchanged since attempt 1. `include/linux/psc_format.h` was last changed in `ca7dac0a` (sha256 `ec4058ee…`), and `decoder/psc_format.py` is byte-identical to attempt 1 (`8d6154b9…`). I re-ran `psc_format.py` (selftest OK: SC 80, WEXT 208, W 288, POLL 40, S 40, M 80, STATS 768, CTL 32, FILEHDR 44, UHB 84) and `check_format.py` (OK, 355 field comparisons, 253 constants). The field-by-field table of attempt 1 (G2-attempt1-review section 2) therefore still holds, and the code beside each design field is unchanged. **Capture points:** the kernel code is byte-identical to attempt 1 (2.2). **Ruling items:** R-1 is implemented in the decoder (2.3) and R-4 in pscol and the decoder (2.4). **Segment life cycle:** unchanged apart from the drain accounting and the name scan (2.5). Attempt-1 F2 and F3 are fixed (sections 2.5 and 2.6) |
| C2 | B | PASS | **Confined diff:** the kernel diff is 19 files, the same as attempt 1 except the cpio, and each is mapped in IMPLEMENTATION 2.2 / 4.x and the kernel notes. **D10:** I re-derived the window with my own script (3.1): 105 = 105 instructions, and after the inverse renaming the only difference is the one delay slot that R-2 allows. **Timeout patch:** present and unchanged in behaviour (3.2) |
| C3 | B | PASS | Kernel unchanged. I re-read the timer, Nop, scheduler and ring paths (4.1): no sleep, allocation, lock, printk or `copy_to_user` on any interrupt path. Every append is ordered invalidate → `barrier()` → fill → `barrier()` → publish `seq` → `barrier()` → head, with volatile stores |
| C4 | B | PASS | **Kernel reader** (`psc.c` `psc_ring_read`): bounded, writes `*ppos` only, and `tmp[PSC_W_SIZE]` covers the largest record. **Stats and ctl:** bounded. **pscol:** the drain caps and flush bound are unchanged. The new `rqe.pre` accounting is correct by a greedy-absorption argument (2.5). The new scans are bounded by `getdents` record lengths (2.5). `build_id_read` reads at most `sizeof(B.text)` through `xread` (4.2) |
| C5 | B | PASS | Kernel unchanged: one BSS object; the WB Nop records into W seq 0 with no init function. `build_id` is computed in `psc_init` (`late_initcall`, `psc.c:1221`), before userland. pscol calls `build_id_read()` before the first `stats_read()` (`pscol.c:2833-2834`) |
| C6 | B | PASS (reviewer scope) | **Release build log** `build-20261006T052947Z.log`: default identity (line 8: `KBUILD_BUILD_VERSION='' KBUILD_BUILD_TIMESTAMP='' REPRODUCE_BASELINE='0'`), `git clean`, 0 untracked files, rc 0. **Warnings:** the distinct set equals the baseline log's (`diff` empty), and no warning names a changed file. **Second build:** another clean build of the same HEAD (`out/20261006T055351Z`, presumably the verifier's) differs in 8 banner bytes, with an identical `System.map`. **Growth:** `vmlinux.bin` +44,036 B and `vmlinux-0.22.bin` +37,312 B, both under 49,152 B, with the change since attempt 1 stated (+405 / +393; R-5). The verifier's own clean build is the verifier's evidence |
| C7 | B | PASS | I disassembled the release `vmlinux` myself. **Against attempt 1:** a whole-file `objdump -d` diff differs in one instruction, `88147f58 addiu a1,a1,-2208` (`__initramfs_end`), and `System.map` differs only in `__initramfs_end`. **Call sites:** I extracted every caller of every `psc_*` hook (4.3). All are at the intended sites, and `Syscon_cmd` is called only from `psc_syscon_cmd` |
| C8 | B | PASS | **Build and FP:** I rebuilt pscol from the delivered source with `cbuild.sh` on a scratch copy. 0 warnings, FP registers 0, FP mnemonics 0, no printf/soft-float/libm, malloc or fork symbols. **flthdr:** bFLT rev 4, PIC-GOT, stack 0x4000. **Binary:** it equals the delivered `7d7a5d78…` except the two build-date bytes (0x2a-0x2b). **Memory:** text+data+bss+stack = 183,040 B, one 256 KB block (R-5). **In the image:** the cpio extracted from the release image contains this binary, 0755, and `rc.sysinit:22 pscol&`. **No fork:** `vfork` + `execve` (`main.c:110-114`). **No operator input:** `/dev/null` on 0-2 (`main.c:81-88`), no tty read. **Writes:** every write and fsync is checked and shown (5.1). **Tests:** all host tests pass, built by me from source (5.2) |
| C9 | | PASS | Little-endian with explicit packing. Unchanged; `check_format.py` OK |
| C10 | | PASS | One new commit with one concern ("initramfs: pscol for G2 attempt 2 …"), changing only the cpio, and built from clean twice (rc 0). Authorship is documented (F7 closed; note in 6) |

---

## 2. C1 details

### 2.1 Record format: field by field, design field beside code field

The C header and the decoder strings are byte-unchanged since attempt 1, so the
attempt-1 table (`G2-attempt1-review.md` 2.1-2.2) still pairs each DESIGN 1.2-1.7 field
with its code field. I re-checked the five struct strings against DESIGN 10.3
by running `psc_format.py` (each `calcsize` equals the design size), and the
offsets against the C header by running `check_format.py` (355 comparisons,
OK). The SC fields that section 17 touched:

| DESIGN 1.2 field (off, type, name) | Code |
|---|---|
| 22, u8, `nwords`: exact for 0-7, but 7 with `rx[14..15]` = `ff ff` means "7 or 8" (R-1) | `psc.c:275-280`: `if (ret == -3 \|\| ret == -4 \|\| x->t0 < 2) nwords = 0; else if (x->t0 < 16) nwords = (x->t0 - 2) >> 1; else nwords = (sc->rx[14] == 0xff && sc->rx[15] == 0xff) ? 7 : 8;` |
| 48, u8[16], `rx` | `psc.c:301` `memcpy(r->rx, sc->rx, PSC_RX_LEN)` |
| stats word 2, `build_id` = CRC-32 (zlib, 0) of `linux_banner` (1.7, R-4) | `psc.c:1221` `psc_k.build_id = psc_crc32(0, linux_banner, strlen(linux_banner));`; `psc.c:1078` copies it into each snapshot |

The executed table in `impl/release-20261006T052947Z/pathcount.txt` (9.2.5)
agrees with section 17 R-1 and with the red team's K1 refinement:

- 0..6 words are exact;
- 7 words read 7, flagged;
- 8 words whose last word is not 0xFFFF read 8;
- 8 words whose last word is 0xFFFF read 7, flagged;
- 0 on −3 and −4;
- the −5 exit takes the final attempt's count.

I reproduced that file exactly by re-running `impl/pathcount.py` (`diff`
empty, section 9). I also checked the register hand-off against the listing:

- `t0` is the receive counter: `li t0,2` at `880cf218`, and `addiu t0,t0,2`
  in the delay slot at `880cf258`;
- the hand-off stores `t0` to `40(sp)` at `880cf174`.

### 2.2 Capture points (DESIGN 2)

The kernel sources are unchanged since `0b0a2acf`, and the binary differs from
attempt 1 only in `__initramfs_end` (C7). The attempt-1 conformance of 2.1-2.12
(G2-attempt1-review 2.3) therefore carries over unchanged. I re-confirmed these
in the attempt-2 listing:

- T1: `mfc0 s2,$9` at `880ce86c`, before `mtc0 zero,$9` at `880ce870`.
- The timer Nop flag: `li v0,2` / `sw v0,-2236(s1)` at `880ce950-954`, before
  `jal psp_pacify_watchdog` at `880ce958`, cleared by `sw zero,-2236(s1)` in the
  delay slot of `jal psc_tick_hook` at `880ce964-968`, before
  `psp_uart3_txrx_tick` and `irq_enter`.
- The `prom_init` Nop flag: `li v1,1` at `8815741c`, stored in the delay slot
  at `88157428` of `jal psp_pacify_watchdog` (`88157424`), cleared at
  `8815742c`.

### 2.3 R-1 in the decoder (10.3, 10.7 "`nwords` 7 or 8")

- **Flag.** `pscdec_parse.py:164-168` sets `nw7or8 = 1` iff `nwords == 7`
  and `rx[14] == rx[15] == 0xFF`, on SC, W and M records alike.
- **Set.** `nwset()` (`pscdec_analysis.py:20-25`) returns {7, 8} or
  {`nwords`}.
- **Template.**
  - The learned value 7 becomes {7, 8} when flagged (`:292-297`).
  - The code expectation "exact length from `rx[1]`" is a set (`:234-240`).
  - `own_valid` matches by set intersection (`:250-252`). All template rules
    (WB, H4, N2b/UL3, H8/O3, step 7 harm) go through `own_valid`. I grepped
    every use of `nwords` in `pscdec_analysis.py` and `pscdec.py`.
- **Thresholds.** The remaining uses are thresholds at 0 or ≥ 1 (H1 `:977`,
  H2 `:998`, H3 `:1008`, foreign `:1196`), which 10.7 says are unaffected, and
  display strings.
- **P6 cross-check.** It reads the set (`:1440-1464`).
- **REPORT.** It counts flagged records per command and origin
  (`pscdec.py:560-570`) and prints "ambiguity live" per template command
  (`:541`). The CSVs keep the raw value and the flag.
- **Tests.** The `NwordsSevenOrEight` tests pass (my run: 37/37).
- **Display gap** (non-blocking finding N3): the H4/WB evidence lines print
  the raw `nwords` without the flag.

### 2.4 R-4 `build_id` (1.7, 8.2 KRN, 10.1)

**pscol** (`pscol.c:453-469`, `build_id_read`):
- reads all of `/proc/version` through `xread` into `B.text` (2,048 B);
- on a read error, an empty file or a file that fills the buffer, leaves
  `build_ok = 0`, so KRN stays red;
- else sets `build_expect = psc_crc32(0, B.text, tot)`.

KRN is `G.krn_ok && G.krn_id_ok && !G.ctl_err`, with `krn_id_ok =
version_size ok && build_ok && st.build_id == build_expect`
(`pscol.c:442-443`, `:2368`). The cbuild knob is gone, and so is the old
`build_expect == 0` → never-checked hole.

**Packaged values, checked by me:**
- the zlib CRC-32 of `BUILD/banner.txt` (102 B, ending in `\n`) is
  `0x045b27d9`, equal to `BUILD/build_id.txt`;
- the banner bytes occur exactly once in the release `vmlinux.bin`, followed
  by a NUL;
- `out/20261006T052947Z/banner.txt` is equal to them.

**Decoder:**
- it reads `build_id.txt` and `IMAGE.sha256` from `--build`
  (`pscdec.py:236-244`);
- `_build_check` (`pscdec_analysis.py:403-452`) checks the first stats block
  (D-23);
- a later change of word 2 is reported and makes later onsets
  instrumentation-suspect (`:1690-1691`);
- each FILEHDR's `/proc/version` CRC is checked against word 2;
- map grammar errors refuse the EPC analysis (`why = list(self.build.errors)`).

### 2.5 pscol changes against 4.2 / 4.4 / 4.6 (attempt-1 F2, F6)

**Name parser** `pscol_tname` (`pscol.c:2153-2174`):
- 11 characters with a NUL at index 11, `T`/`t` at 0, digits at 1-6, `.` at 7,
  and `bin` compared case-insensitively;
- it returns `rrr` and `nnn`.

**Run scan** `pscol_run_scan` (`:2178-2198`) is called by the supervisor
(`main.c:93`):
- it returns 1 + the largest `rrr`, 1 if `PSCLOG` cannot be opened, and at
  most 999, which matches DESIGN 4.2 "(1 if none, ≤ 999)";
- it runs before `vfork`, in the supervisor's own data.

**Name scan** `names_scan` (`:2242-2295`):
- `next_nnn` = 1 + the largest `nnn` of `G.run`. `G.run` is set at
  `worker_init` (`:2781`), before the call at `:2835`.
- Slot counting:
  - `.` and `..` count one slot each;
  - names that cannot be short-only count 1 + ⌈len/13⌉;
  - possible short-only names count 1, plus up to ⌈len/13⌉ when the gap to
    the next entry's first slot is ≥ 2.

**I verified the two kernel facts the slot counting relies on** in the
original tree:
- `fs/fat/inode.c:948` sets `VFAT_SFN_DISPLAY_LOWER|VFAT_SFN_CREATE_WIN95` by
  default, and `fs/fat/dir.c:206-213` shows a short-only name in lower case.
- `fat_readdirx` passes `lpos = cpos − (long_slots+1)·32`, the entry's first
  slot (`fs/fat/dir.c:578`), as the `filldir` offset.
  - `filldir` writes that offset into the **previous** dirent's `d_off`.
  - On `FillFailed`, `f_pos` stays at the end of the last processed record,
    which is the first slot of the entry that did not fit (`fs/fat/dir.c`,
    `RecEnd`/`FillFailed`). So the last dirent's `d_off` in a full buffer is
    the next entry's first slot, and `pend` is right to defer it.
  - At `EODir` it is the end of the directory, which `names_scan` correctly
    drops.
- The host model (`test/sim.c:931-967`) implements the same semantics.

At worst the last entry of the directory is counted one long-name slot short.
The source comment states this, and it is inside the 16-slot margin.

**Re-send accounting** (F6; `pscol.c:68-73`, `:837-886`, `:955-1000`,
`:1035-1042`, `:1956-1960`):
- A FAILED flush re-queues `[first carried seq, np)` with `pre` = the holes
  already counted.
- A re-send absorbs up to `pre` of the missing seqs it finds. If a range is
  split by the per-tick budget, the greedy absorption still totals
  min(Σmiss, pre), so the lost count over the whole range equals the number of
  missing seqs.
- A failed re-send is re-queued with `pre = miss`.
- An overflow merge over-counts gap seqs, never under-counts. The source
  comment says so.
- `durable_next` may now start after a lost prefix that was never durable
  (P-16); DESIGN 4.6's one-range-per-ring is kept.

**Everything else is unchanged:** creation steps, verdicts, switch and hold,
META and the flush assembly. `diff -u` shows no other hunk, so the attempt-1
4.4 life-cycle review holds. My host runs of the burst, TE10, IF7b and IF4
tests pass (5.2).

### 2.6 Decoder maps (attempt-1 F3, OD-4)

**One grammar.** `work/decoder/psc_maps.py` is used by `mkmaps.py` and by
`BuildInfo.load`, and it requires the magic first lines `# PSC-EPCMAP 2` and
`# PSC-REGMAP 2`. I loaded the release `BUILD/` maps: no errors, and 4,955
EPC rows.

**My check of the regmap rows against my own listing** (section 3):

| Step | EPC | Registers | Result |
|---|---|---|---|
| S18 | `880cf220` | t0 = 2 | i 0, pending 0 |
| S18 | `880cf234` (the data load, not executed) | t0 = 16 | i 14, j 7, pending 1 |
| S18 | `880cf238` | — | i 16, j 8, pending 0 |
| S18 | `880cf254` | a3 advanced | ptr − rx_buf 16 = i |
| S11 | `880cf05c` | — | k 0 |
| S11 | `880cf070` | — | k 0 |
| S11 | `880cf084` (push not done) | — | k 0 |
| S11 | `880cf088` | — | k 1, ptr − tx_buf = i |

- **Registers in the listing:** `t0`, `a3` (rx), `t9` = rx_buf + 2 (`880cef44`),
  `t5` = tx_buf (`880cef14`), `t8` = retry_cnt (`880cef24`, `880cf2e4`).
- **LEDRMW:** `loaded` = `r[3]` = `a1`, the register `psp_led_ctrl` loads into
  at `880ce9bc` and `880ce9d4`. The map ranges are `880ce9c0-9c8` and
  `880ce9d8-9e0`.
- **Step mapping:** `STEP_PPOINT` maps S0 to P0 (`pscdec_analysis.py:179`).
- **The epcmap step boundaries match recon/syscon.md 1.2:**
  - S15 = `sw v0,0(s8)` with s8 = 0xbe240024, at `880cf21c`;
  - S19 = `880cf268-274`;
  - S20 = `880cf278`.

---

## 3. C2 details

### 3.1 D10 window, re-derived by me

- **Disassembly.** I ran `mipsel-linux-uclibc-objdump -d` in the container on
  `out/20260927T204657Z/vmlinux` (baseline, `Syscon_cmd` at 880cee10, 218
  instructions) and on `out/20261006T052947Z/vmlinux` (release, 880ceed0, 268
  instructions).
- **Release against attempt 1.** The release `Syscon_cmd` is byte-identical,
  at the same addresses, to the attempt-1 release
  (`cmp` of the opcode columns).
- **Windows compared.**
  - Baseline: 880ceeec..880cf020 and 880cf054..880cf0bc.
  - Release: 880cefb0..880cf0e4 and 880cf210..880cf278.
  - The hand-off block 880cf0e8-880cf20c is excluded.

```
window instr base 105 new 105
literal differences (stack-normalised): 6
   0  lw v0,0(s4) | lw v0,0(s3)        3  sw s6,0(s0) | sw s5,0(s0)
  20  lw s8,N(sp) | nop               58  sw s5,0(s7) | sw s4,0(s6)
  71  ori a1,s3,0xc | ori a1,s7,0xc  104  sw s5,0(s0) | sw s4,0(s0)
after inverse renaming (s7->s3, s3->s4, s4->s5, s5->s6, s6->s7): 1
  20  0x880cef3c lw s8,N(sp) | 0x880cf000 nop
non-stack mem ops equal in order: True 27
calls: 0 0      lui: [lui v0,0xbe58, lui v1,0xbe58] both      gp: 0 0
writes to s0-s8 inside the new window: none
```

**The renaming is value-preserving.** Each renamed register holds the same
constant from the prologue:

| Release | Baseline | Value |
|---|---|---|
| `s3` (`ori s3,v1,0x4` at `880cef28`) | `s4` | 0xbe240004 |
| `s7` (`lui s7,0xbe24` at `880ceee4`) | `s3` | 0xbe240000 |
| `s6` (`ori s6,v1,0x8`) | `s7` | 0xbe240008 |
| `s4`, `s5` (= 8) | `s5`, `s6` | 8 |
| `s8` (`ori s8,s7,0x24`) | `s8` | 0xbe240024 |

**The one changed instruction** is the delay slot of the first-iteration −3
exit `j` (`880ceffc`/`880cf000`). It runs after the exit decision and after
that path's last MMIO access.

**Under section 17 R-2 this passes.** Exactly the three allowed differences
occur: stack offsets, a value-preserving renaming, and the exit delay slot.
There is no call, no global or `gp` load, and no extra base reload.

### 3.2 Timeout patch (DV-17)

Checked by `git diff baseline..stage2-trace -- arch/mips/psp/ipl_sdk/syscon.c`
and in the listing:

- `SYSCON_SPIN_MAX 1000000` and `SYSCON_RETRY_MAX 16` are unchanged
  (`syscon.c:12-13`).
- The drain bound: `spin = SYSCON_SPIN_MAX` and `if(spin-- == 0)`, now
  `{ result = -3; goto out; }` (`syscon.c:162-165`). In the listing:
  `sw s1,8(sp)` at `880cefd0`, `li t3,-3` and `j 880cf0e8`.
- The ACK bound: in `spin_ack` with the same two teardown writes in the same
  order, `REG32(0xbe580004)=4; REG32(0xbe24000c)=0x08`, then
  `result = -4; goto out;` (`syscon.c:203-206`). In the listing: `880cf0dc`
  then `880cf0e4`, `li t3,-4` between them.
- The retry: `++retry_cnt < SYSCON_RETRY_MAX` is unchanged. In the listing:
  `addiu t8,t8,1` / `bnel t8,v0(16)` at `880cf2e4-e8`.
- `out:` runs the hand-off (`PSC_XFER_OUT`, which saves and restores every
  register it touches) and returns `result` unchanged (`move v0,t3` at
  `880cf204`).
- Executed, the −3 and −4 exits return −3 and −4 after 1,000,001 iterations,
  and −5 after 16 tries (pathcount table, reproduced).

**Behaviour unchanged.** The textual hunks no longer reverse-apply, as
declared in DV-17.

### 3.3 Confined diff

- **Kernel.** The kernel sources are unchanged since attempt 1. Every hunk is
  mapped in IMPLEMENTATION 2.2 / 4.1-4.10 and in the kernel notes, sections
  2-4 (attempt 1 verified that mapping). The one new commit changes only the
  cpio, which is mapped in IMPLEMENTATION 1.1 (I-6).
- **Driver logic** is unchanged: the `psp_led_ctrl` `lw/or/sw` is in the same
  order (`880ce9bc-9c4`, `880ce9d4-9dc`), and the joypad and `ms_psp` code is
  as at attempt 1.
- **The IMPLEMENTATION citations I spot-checked** all resolve to the cited code:
  - `psc.c:275-280`, `:526-533`;
  - `pscol.c:442`, `:453`, `:837`, `:972`, `:993`, `:1035`, `:1956`,
    `:2153`, `:2178`, `:2205`, `:2242`, `:2833`;
  - `pscol.h:69`;
  - `pscdec_parse.py:162-168`;
  - `pscdec_analysis.py:20`, `:179`, `:403`, `:570`, `:1377`, `:1440`;
  - `pscdec.py:541`, `:560`.

---

## 4. C3, C4, C5, C7 details

### 4.1 C3

I re-read `psc.c` 1-660 and 655-1245. The kernel is unchanged since the
attempt-1 PASS.

**Interrupt paths**
- `psc_tick_hook` calls `psc_cur_regs`, which is bounds-checked against the
  thread stack.
- T2a's `lc_*` block is bracketed by `lc_seq` (odd while writing).
- T2d paints the panel.
- The Nop path: `psc_syscon_cmd` → `Syscon_cmd` → `psc_xfer_out` (one struct
  copy into a per-origin area) → `psc_sc_exit`, using the W branch, `memset`,
  `memcpy` and `psc_dcount`.
- No lock, sleep, allocation, printk or `copy_to_user`.

**Append order**
- Every ring writes `PSC_WR(seq, PSC_SEQ_WRITING)`; `barrier()`; fill;
  `barrier()`; `PSC_WR(seq, s)`; `barrier()`; `PSC_WR(head, s+1)`. This holds
  for P (`psc.c:449-458`), M (`:483-491`), W (`:499-510`), S (`:683-715`) and
  POLL (`:894-900`).
- `PSC_WR`/`PSC_RD` are volatile accesses (`include/asm-mips/psc.h:26-27`).
- The Nop writes only W and its counters.
- `t_busy_p` is set after `t_cmd_id++` and a `barrier()` (`:237-240`), and
  cleared after the exit snapshots (`:446-451`).

**Scheduler hooks**
- They run under the rq lock and are O(1) (`:735-829`).

### 4.2 C4

**Kernel**
- `psc_ring_read` (`psc.c:976-1033`):
  - rejects a negative `*ppos` or one that is not a record multiple;
  - handles `s > h` as `head_regress` and `h − s > n` as overwritten;
  - checks `done + size > count` before each record;
  - skips at most n slots;
  - writes `*ppos` only.
- Stats read is bounded by 768 − `*ppos`.
- ctl takes whole 32-byte commands with validated slots and seconds.

**pscol** (unchanged bounds)
- `xread`/`xpread` assert `buf + len ≤ end` (`pscol.c:316-331`).
- The flush buffer bound of 37,888 ≤ 40,960 is unchanged.
- The re-send `infl` array is guarded by `G.ninfl < RESEND_MAX + PSC_NRINGS`.

**New pscol code**
- `build_id_read` loops `xread(fd, B.text + tot, sizeof − tot, END_OF(B.text))`.
- The two `getdents` scans stop on `rl == 0 || off + rl > n`.
- `pscol_tname` reads at most `nm[0..11]` and returns early at a NUL.

### 4.3 C7: every caller of a `psc_*` hook in the release `vmlinux` (my extraction)

| Hook | Called from |
|---|---|
| `Syscon_cmd` | `psc_syscon_cmd` only |
| `psc_syscon_cmd` | `_pspSysconGetCtrl2`, `pspSyscon_rx_dword`, `pspSyscon_tx_dword` |
| `psc_xfer_out` | `Syscon_cmd` (`880cf17c`) |
| `psc_sc_exit` | `psc_syscon_cmd` |
| `psc_tick_hook` | `plat_irq_dispatch` |
| `psc_panel_t2d` | `psc_tick_hook` |
| `psc_note_led` | `psp_led_ctrl` |
| `psc_ms_seg_begin`, `psc_ms_seg_end` | `psp_ms_read`, `psp_ms_make_request` |
| `psc_sched_wake_slow` | `try_to_wake_up` |
| `psc_sched_switch_slow` | `schedule` |
| `psc_jp_thread_start`, `psc_poll_begin`, `psc_poll_end` | `psp_joypad_thread` |
| `psc_fat_mounted` | `fat_fill_super` |
| `psc_fat_panic` | `fat_fs_panic` |
| `psc_fat_rdonly` | `psc_panel_t2d`, `psc_stats_read` |

---

## 5. C8 details

### 5.1 Every stick write and fsync: checked and shown

| Site | Check | Shown |
|---|---|---|
| Step 0 FILEHDR (`pscol.c:1504-1510`) | `w`, `s` with errno → `err_note`; verdict from the S window | `fail_note` → `write_errs++`, `ms_red_until` → HUD line 6 red (`:2608`), ERR count |
| Creation step `writev` + `fsync` (`:1702-1707`) | `w`, `s`, `err_note`; the S-window verdict | the same |
| Flush (`:1904-1913`) | `w`, `s`, `err_note`; `judge_flush` | the same; a DURABLE flush with an fsync error sets b30 and an EVENT (`:1923-1932`) |
| Probe `fsync` of an alias (`:1605`) | Not by its return. By DESIGN 4.4 step 1 it is judged from the S window (`window_has_ok_write`, `:1607`) | ≥ 10 s back-off; MS line states |
| Guard-exit `emergency_flush` (`:2962-2963`) | Best effort before `_exit(3)`, as DESIGN 4.2 specifies ("a last EVENT … if the flush buffer is intact") | the takeover instance's EVENT `takeover guard` and UHB b16 |
| Framebuffer rows (`:2767`) | `!= ROW_BYTES` checked | — |

### 5.2 Host tests (built by me from the delivered source)

`gcc -DPSCOL_HOST` in a scratch copy, with `../linux` linked to the work tree.

| Test | Result |
|---|---|
| `vectors` | 28 PASS |
| `hud` | PASS |
| `nominal` | PASS (SELFTEST PASS, 0 missing) |
| `burst` | 8/8 |
| `te10` | 6/6 |
| `if7b` | PASS (105 names, 13 ticks) |
| `names` | 6 cases + parser PASS (lower-case earlier boot → rrr 2, nnn 001; takeover continues nnn; 64-byte getdents buffer) |
| `krn` | PASS |
| `resend` | 3/3 (lost_total = missing below `durable_next`: 915, 1,020, 1,020) |
| `if4` (10 seeds × 4 speeds) | 40/40 |

Decoder: 37/37 OK (`test/run_tests.py`, 53.6 s).

---

## 6. Prior findings: closure

| Finding | Closed | Evidence |
|---|---|---|
| Review **F1** (DV-3, `nwords` 7/8, routed to G1) | yes | **Ruled** by section 17 R-1 option (a). **Kernel** is option (a) (`psc.c:275-280`). **Decoder** flags and uses sets (2.3). The executed `nwords` table (9.2.5) is reproduced by me |
| Review **F2** (run number, `nnn`, names budget) | yes | `pscol_tname`/`pscol_run_scan`/`names_scan` (2.5). Checked against the real vfat semantics in `fs/fat/inode.c:948` and `fs/fat/dir.c:206-213`, `:578`. The host `names` test passes when I build it. The new bFLT is in the image (cpio extracted from `vmlinux.bin`, `usr/bin/pscol` sha256 `7d7a5d78…`) |
| Review **F3** (decoder cannot read the kernel maps) | yes | One grammar (`psc_maps.py`). The release maps load with no error. S0 maps to P0. S11 `k`, S18 `j`/`pending` and LEDRMW `loaded` are correct at the EPCs I derived from the listing (2.6). An old-syntax map is refused |
| Review **F4** (KRN `build_id`) | yes | Implemented as R-4 (2.4). CRC `0x045b27d9` reproduced from `banner.txt` |
| Review **F5** (costs and stack from object code) | yes | IMPLEMENTATION 9.2 gives per-path counts with their assumptions (P +557/+560, Nop +871, tick +48, straddle +1,104) and stack (+208/+216 B; 664 B worst before `irq_enter`). I re-ran `pathcount.py` and its output equals `pathcount.txt`. The figures are consistent with the G1 reviewer's hand count (≈ 540). The parts above the design figures are N1 |
| Review **F6** (lost re-counted on re-send) | yes | `rqe.pre` accounting (2.5), with my greedy-absorption check. `resend` 3/3 |
| Review **F7** (commit provenance) | yes | IMPLEMENTATION 2.1 and 9.4 name the real authors of `4c4e7aee..0b0a2acf` (the Stage 2 kernel implementer) and of `48dcc1b9` (the G2-attempt-2 implementer, committing under the identity `Stage 2 kernel implementer (Claude agent)`). The trail is recoverable from the document, which was F7's closure condition. Note: that identity names a role other than the one that made `48dcc1b9`; later commits should use the committing role's name |
| Review **U1** (= F2), **U2** (= F5), **U3** (= F6), **U4** (= F4) | yes | as above |
| Review **C1 FAIL** | yes | its three reasons F1, F2 and F3 are closed |
| Review **C2 / DV-17** (timeout patch text) | yes | behaviour unchanged (3.2) |
| Review **section 7, A7-1..A7-3** | yes (remains closed) | `DESIGN.md` = r7 + `g1ruling.diff`, and r7 contains the A7 edits (G1 ruling review section 1) |
| Verify **Finding 1** (OD-2, window not literally identical) | yes | Ruled by R-2. Re-derived by me on the attempt-2 image (3.1) |
| Verify **Finding 2** (OD-5, pscol memory) | yes | R-5. My rebuild gives text 52,768 + data 2,912 + bss 110,976 + stack 16,384 = 183,040 B, one 256 KB block |
| Verify **Finding 3** (OD-6, image growth, pspboot load) | yes for G2 | R-5 bound met: +44,036 / +37,312, restated with the change since attempt 1 (+405 / +393). Whether pspboot loads the image stays UNVERIFIED as open risk R20 (OD-9). That is a G3/hardware item, not a G2 one |
| Verify **Finding 4** (release sha256 per build) | yes | The package carries `BUILD/` with `IMAGE.sha256` = `4f9b69dc…` and `build_id.txt` = `0x045b27d9` (`sha256sum -c` OK, equal to the release directory). A second clean build of `48dcc1b9` differs in 8 banner bytes, so G3 R3 and the decoder must use the packaged `BUILD/` |
| Verify **Finding 5** (patch no longer reverse-applies) | yes | as DV-17 |

---

## 7. Deviations: do any touch a blocking G1 item beyond section 17?

The attempt-2 additions are P-15, P-16, P-17, D-23, D-24, D-25, I-5, I-6 and I-7.

**Earlier deviations.** DV-3, DV-4, DV-12 and P-1 are now ruled (R-1, R-2,
R-4, R-5) and implemented as ruled. The other attempt-1 deviations are
unchanged and were accepted at attempt 1.

**New deviations, one by one:**

| # | Touches a blocking G1 item? | Ruling |
|---|---|---|
| P-15 run scan moved into `pscol.c` | No | Code placement only |
| P-16 re-send range from the first carried seq | No | D6 is unaffected: nothing durable is lost, only the never-durable lost prefix leaves `durable_next` |
| P-17 KRN by CRC of `/proc/version` | No | This is section 17 R-4 |
| P-12 (replaced) slot counting | No | The 4.4 step 6 budget rule is unchanged |
| D-23 first stats block for 10.1 | No | 10.1 does not say which block. This follows red-team K4 and only narrows a refusal |
| D-24 P6 cross-check from the regmap `pending` sub-range | No | An annotation only; the classification does not change (10.7). It implements K2 without a new EPC label |
| D-25 REPORT prints `IMAGE.sha256` and the 7/8 section | No | This is section 17 R-1 and 10.3 |
| I-5, I-6, I-7 package `BUILD/`, cpio replacement, `mkmaps.py` | No | Packaging only |

**OD-7, measured costs above some design figures: not a deviation of the
implementation.** I rule it non-blocking (finding N1), for three reasons:

1. The code is byte-identical to the code G1 examined at R-3. The ruling
   reviewer counted functions on the same binary and accepted the W path as
   "uncounted (UNVERIFIED) … measured on the device as `w_rec_cost_max`".
2. The design's figures are labelled estimates. DESIGN 5.4 has an "Estimate"
   column and "Assumptions (UNVERIFIED)", and says the run measures the
   costs. The implementation does what the design specifies: T1, T2a `lc_*`
   capture, W extension and panel.
3. D10's substance is intact: 0 instructions in S5..S20 (3.1), no lock, no
   new masking. The attempt-1 reviewer ruled the same class of estimate miss
   (U2/F5, 3-4×) as not touching a blocking item.

The design text is now stale in five places, which N1 asks to record:
- the per-tick figures (+48, not ≈ 16);
- T2a (+160 more, not ≈ 33);
- the whole watchdog tick (4.2 µs);
- straddle resumption (≈ 5.0 µs, not ≈ 2-4 µs; 7.3 and R6);
- the panel paint (≈ 1.03 ms modelled, not 0.2-1 ms).

If the orchestrator or the human reads the 7.3/R6 straddle figure as a ruled
bound rather than an estimate, this item is the one to put to the human.

**OD-8, the G1-ruling advisories not implemented** (K1, K5, K6, K7, K8 and
review A-2/A-3/A-5/A-6): these are design-text recommendations that G1 passed
without. They are not implementation deviations. Their open status is
finding N2.

`design_deviations_touching_G1_blocking`: **none**.

---

## 8. Findings (each: where, problem, what closes it)

**N1: non-blocking. Measured costs exceed the design's estimates (OD-7).**
- *Where:* IMPLEMENTATION.md 9.2.2-9.2.4 and `impl/release-20261006T052947Z/pathcount.txt`, against these DESIGN rows:
  - 5.4: the "Every tick / tick finding the thread running in a command" row (≈ 16 / + ≈ 33), the "Watchdog command" row and the "Stall panel" row (0.2-1 ms);
  - 7.1: the "Timer interrupt" and "Stall panel" rows;
  - 7.3: "Resumption after a Nop is ≈ 2-4 µs later";
  - 11.1: R6 and R13.
- *Problem:* executed at 1 IPC (no cache model, UNVERIFIED):

  | Path | Measured | Design figure |
  |---|---|---|
  | Every tick | +48 instructions | ≈ 16 |
  | A tick finding the thread in a command | +208 instructions (≈ 0.94 µs) | ≈ +33 more, ≈ 0.15 µs resumption |
  | Nop alone | +871 instructions, ≈ 3.9 µs | inside R-3's 2-4 µs |
  | Whole watchdog tick | +922 instructions, ≈ 4.2 µs | — |
  | First Nop of a boot | +990 instructions, ≈ 4.5 µs | — |
  | Watchdog tick straddling a thread command (the H4 case; the thread resumes this much later) | +1,104 instructions, ≈ 5.0 µs | 2-4 µs |
  | A panel paint | 228,520 instructions, ≈ 1.03 ms | 0.2-1 ms |

  The mechanisms are the specified ones, and all of this runs outside S5..S20
  with no lock or new masking. But the perturbation statement's numbers, which
  D10 asks to be "stated", are low. The R6 threshold for a level-sensitive G4L
  pulse moves from ≈ 2-4 µs to ≈ 5 µs.
- *Closes it:* the orchestrator records in `gates/LOG.md` that the
  IMPLEMENTATION.md 9.2 figures supersede the DESIGN figures listed above, as
  R-3 did for the thread path. The designer restates them as text at the next
  G1 contact, or the human accepts them. G3 R6 reads the on-device
  `w_rec_cost_max`, `panel_cost_*` and the per-poll gap. Nothing in the code
  needs to change.

**N2: non-blocking. G1-ruling advisories still open (OD-8).**
- *Where:*
  - `gates/G1-ruling1-redteam.md`: K1 (the "exact for 0 to 7" wording), K3
    (10.1: refuse on the image hash, and replace the attempt-1 example
    directory), K5, K6, K8 (decoder printouts in 10.7 steps 6 and 8), K7
    (text 51,904 → 51,968 B, citations);
  - `gates/G1-ruling1-review.md`: A-2 (citation), A-3, A-5 and A-6
    (wording).
- *Problem:* each needs design text, so the implementer did not act on it
  (IMPLEMENTATION 9.1). G3 R1 requires "no open findings".
- *Closes it:* a gate-log entry in which the human or the G1 reviewer accepts
  them as won't-fix. Alternatively, the designer applies the text edits
  (K5/K6/K8 would then need decoder code and a G2 re-check of that code).

**N3: non-blocking. The H4/WB evidence lines print the raw `nwords`.**
- *Where:*
  - `decoder/pscdec_analysis.py:1260-1261` (the WT listing);
  - `:1285-1292` (the H4 step line: the Nop's and the thread's `nwords`);
  - `:1315-1316` (the WB line).
- *Problem:* a flagged record (`nw7or8`) prints as "nwords 7" in the evidence
  for the leading hypothesis. The timeline (`pscdec.py:116`) prints "7|8",
  and every rule uses the set, so classification is unaffected. Only an
  analyst reading the H4 text could be misled.
- *Closes it:* print `7|8` whenever `nw7or8`, as `pscdec.py:116` does, in
  those three format strings, and add the case to the `NwordsSevenOrEight`
  test.

---

## 9. Attacks tried (WORKFLOW principle 4)

1. **Earlier-boot files on the real vfat** (`shortname=lower`, mixed long
   names, deleted slots, a short `getdents` buffer). I traced `fat_readdirx`
   and `filldir` offsets in the original tree.
   - `d_off` is the next entry's first slot.
   - On `FillFailed` it is the unfitting entry's first slot.
   - At EOD it is the directory end.
   
   `names_scan` handles all three. At most one LFN slot is uncounted at the
   directory end, inside the 16-slot margin. **Held.**
2. **A re-send split across ticks, with the holes in the second piece.** The
   greedy `pre` absorption totals min(Σmiss, pre), so the count is exact.
   **Held.**
3. **`/proc/version` unreadable or ≥ 2,048 B.** `build_ok = 0`, so KRN is red
   and the run aborts per the RUNBOOK. **Held.**
4. **A Nop with EPC exactly at the S18 data load** (`880cf234`), or in a
   delay slot. `pending` = 1, j = 7, and a delay-slot EPC cannot occur (BD
   reports the branch). Every sub-range is correct against my listing. **Held.**
5. **Window drift between attempts.** The whole-kernel disassembly diff shows
   only `__initramfs_end`. **Held.**
6. **The image's initramfs is not the committed one.** I extracted
   `.init.ramfs` (0x51760 B at 0x8815e000) from `vmlinux.bin`: one gzip
   member, 0 trailing bytes, cpio sha256 `5dde35cd…` = commit `48dcc1b9`.
   `gunzip(vmlinux-0.22.bin) == vmlinux.bin`. **Held.**
7. **The delivered bFLT does not match its source.** My rebuild differs only
   in the two build-date bytes. **Held.**
8. **The decoder fed another build's maps, or the old syntax.** Refused, by
   test and by code (`errors` → `why`). **Held.**
9. **Unchecked writes.** The probe `fsync` and the guard-exit flush are both
   by design (5.1). **Held.**
10. **Costs against the ruling.** The straddle figure exceeds 7.3's 2-4 µs:
    **N1.**
11. **A rebuild's banner.** The second clean build differs in 8 bytes. The
    package's `BUILD/IMAGE.sha256` pins the image. **Held.**
12. **The supervisor's run scan races the worker's use of `B.text`.**
    Separate processes (`execve`). The takeover runs in-process only after
    the scan completes. **Held.**

## 10. What I did not verify

- Runtime behaviour on hardware.
- The CP0 Count rate.
- Allegrex pipeline timing.
- Cache effects on the measured costs.
- Whether pspboot loads 1,767,264 B (R20).
- **Process caveat:** I re-ran `pathcount.py`, the implementer's interpreter,
  rather than writing my own. Its output is consistent with the G1 reviewer's
  independent hand count.
- The verifier's clean build is the verifier's evidence. I noted
  `out/20261006T055351Z` only as a reproducibility check.
- The host vfat model is a model.

## State left behind

- **Original tree:** `sha256sum -c --quiet gates/baseline-tree.sha256` in
  `build/linux` exits 0, checked at the start and at the end.
- **Work tree:** `work/linux` is on `stage2-trace` @ `48dcc1b9`, with
  `git status --porcelain` empty. I wrote nothing in `work/` and did not run
  `build.sh`, because another build was running concurrently.
- **Scratch files:** under `scratchpad/g2a2rev/` (`mywin.py`, the `sc.*.dis`
  listings, the extracted `ramfs2/`, `pathcount-mine.txt`, scratch copies of
  pscol and the decoder).
- **The only file I wrote** in the handoff tree is this report.
