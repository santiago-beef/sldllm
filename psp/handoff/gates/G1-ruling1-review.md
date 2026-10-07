# Gate G1, ruling after G2 attempt 1 (ruling attempt 1): design review

Reviewer: G1 design reviewer, fresh context. I did not write the design, the
code or any earlier gate report.
Date: 2026-10-06. Run: wf_2daaeb23-497.
Artifact: `design/DESIGN.md` (revision 7), checked against the frozen
`design/DESIGN.r7.md` through `design/g1ruling.diff`; the designer's section 17.
Scope: items R-1..R-6 (DESIGN 17, IMPLEMENTATION.md section 0) and the
blocking items they touch.

## Verdict: **PASS**

All six rulings are **accepted**. Every blocking item they touch still
PASSes: R-1 (D3, D10, D2), R-2 (D10), R-3 (D10), R-4 (D13), R-5 (D12) and
R-6 (D20). The diff is **confined** to R-1..R-6. Six advisories (section 4)
are text precision only. None of them changes a D item, and none needs
another G1 round.

| Item | Accepted | D items checked | Result |
|---|---|---|---|
| R-1 `nwords` 7 or 8 | yes | D3, D10, D2 | PASS, PASS, PASS |
| R-2 D10 acceptance test | yes | D10 | PASS |
| R-3 costs outside the window | yes | D10 | PASS |
| R-4 `build_id` | yes | D13 | PASS |
| R-5 memory and image figures | yes | D12 | PASS |
| R-6 two stale figures | yes | D20 | PASS |
| diff_confined | yes | | 27 hunks, each tagged §17 R-n or part of section 17 |

---

## 1. Provenance of the inputs (checked first)

- **Frozen r7.** I applied `design/round7.diff` to `DESIGN.r5.md` and
  `RUNBOOK.r5.md`, then applied `impl/A7-design.diff`, all in my scratchpad.
  The result is byte-equal to `design/DESIGN.r7.md` and
  `design/RUNBOOK.r7.md` (`cmp`). So r7 is the G1-approved revision 6 plus the
  A7 edits, as section 17 says.
- **The diff is the real diff.** `diff -u DESIGN.r7.md DESIGN.md` is
  byte-equal to `g1ruling.diff` after the two header lines.
- **RUNBOOK unchanged.** `cmp RUNBOOK.md RUNBOOK.r7.md`: identical.
- **Trees.**
  - `sha256sum -c --quiet gates/baseline-tree.sha256` in `build/linux`
    exits 0.
  - `work/linux` is at `c135ecdd` with 0 changed files.
  - I wrote nothing outside this report and my scratchpad.

## 2. Diff confinement

`g1ruling.diff` has 27 hunks. Every added text carries a **(§17 R-n)** tag,
except hunk 27, which is section 17 itself. Every deleted line is the text
that the tagged replacement supersedes.

| Hunks | Where | R |
|---|---|---|
| 1 | header note | all |
| 2-3 | Summary 1, Summary 7 | R-2, R-3, R-5 |
| 4-5 | section 0 rows K1, U1 | R-3, R-5 |
| 6 | 1.2 offset 22 | R-1 |
| 7 | 1.7 words 0-4 | R-4 |
| 8-9 | 2.1 A4; text after the 2.1 criteria | R-1, R-2 |
| 10 | 2.11 | R-6 |
| 11 | 4.2 | R-5 |
| 12 | 4.3 Bounds | R-6 |
| 13 | 5.1 | R-6 |
| 14-15 | 5.3, 5.4 | R-3, R-5 |
| 16 | 6 preamble | R-1 |
| 17 | 7.1, four rows | R-2, R-3, R-5 |
| 18 | 7.2 | R-2 |
| 19 | 7.3 | R-3 |
| 20 | 8.2 KRN | R-4 |
| 21 | 10.1 | R-4 |
| 22 | 10.2 | R-6 |
| 23-24 | 10.3, 10.7 | R-1 |
| 25-26 | 11.1 R6, R20 | R-3, R-5 |
| 27 | new section 17 | all |

What did not change:

- No record, field, offset, struct string, ring, chunk type, check, HUD line,
  panel state or RUNBOOK step was added or changed.
- 8.2 KRN is the same check. Only its `build_id` comparison is now defined.
- Historical text in sections 13-16 (for example the 15.6 line "37,696 →
  37,888") is untouched, which is correct: those sections record past
  rounds.

**diff_confined = true.**

---

## 3. Rulings

### R-1: `nwords` (OD-1, DV-3; D3 against D10): ACCEPTED

**What I verified in the object code.** The receive loop in the release
`Syscon_cmd` runs from 880cf218 to 880cf264, as listed in section 2.3:

- `li t0,2`;
- the status test `beqz v0,880cf268`, with `addiu a0,t0,-2` in its delay slot;
- the per-word path `bnez t1` / `addiu t0,t0,2`, where `t1 = slti t0,16` is
  computed before the read.

Traced case by case:

- **k ≤ 7 words, then FIFO empty:** the loop exits with `t0 = 2k + 2`.
- **8 words:** the loop falls through after the 8th word with `t0 = 16` and
  `a3 = rx_buf + 16`. That is the same register state as "7 words, then
  empty".
- **Both cases:** `rx[14..15]` is `ff ff` whenever the 8th word is absent,
  because the prefill (`syscon.c:92-93` in the original tree) runs per attempt
  after `retry:`.

So `psc_fill_sc` (`work/linux/arch/mips/psp/psc.c:275-280`) is right:

- `t0 < 16` gives `(t0-2)/2` exactly;
- `t0 = 16` with `rx[14..15] ≠ ff ff` gives 8 exactly;
- `t0 = 16` with `rx[14..15] = ff ff` gives "7 or 8".

The −3 and −4 exits are forced to 0. On −5, `t0` comes from the final
attempt's loop: on a retry the `bnel` delay-slot `lbu t0` is followed by a
fresh `li t0,2`. The record states exactly what the code produces. The two
cases differ only in a 0xFFFF word whose bytes equal the prefill.

**Is the decision sound?** Yes.

- The conflict is real. Exactness costs instructions inside S13..S20:
  - (b) +2 instructions per received word in S18;
  - (c) hand-written code on the 8-word exit edge.
- The dossier forbids exactly that. 6.3 says any timing change on the syscon
  path invalidates the run, and H4 (9.6) acts in S5..S20.
- The bit that is lost carries no byte of the frame. `ret`, the checksum,
  `rx[2]` and the button bytes are identical either way.
- The record itself identifies the ambiguous case.

**D3: PASS.**

- Raw `rx[16]`, `cmd`, `ret` and the word count are recorded.
- The count is exact except for one case that the record identifies. The
  decoder carries that case as the set {7, 8} (1.2 offset 22, 10.3).

**D10: PASS.** Nothing is added in S5..S20. 105 = 105 instructions, re-derived
under R-2 below.

**D2: PASS.** I read every rule in sections 6 and 10.7 that reads `nwords`,
plus the other readers of the field:

| Reader | Uses | Effect of {7, 8} |
|---|---|---|
| 6 preamble / 10.7 step 2: template per command `nwords`; code expectation "for 0x08 ≥ 5 words, exact length from `rx[1]`" | equality / length | Set membership. "≥ 5" holds for both values. Equality differs only for a frame whose 8th word is 0xFFFF, and then `rx[1]`, `rx[2]`, `ret` and the checksum are identical |
| H1 (`nwords = 0`) | = 0 | 0 is exact |
| H2 (`nwords ≥ 1`) | ≥ 1 | unchanged |
| H3 (`nwords = 0`); "N2b has `nwords ≥ 1`" | = 0 / ≥ 1 | unchanged |
| H4 ("the Nop's own `rx`, `ret`, `nwords`") | display / template | A Nop template is short, so 7 and 8 both mismatch it. Unchanged |
| WB ("that Nop's own `ret`, `nwords` … against the template") | template | as H4 |
| N10 (`ret = 0` with `nwords ≥ 1`) | ≥ 1 | unchanged |
| 10.7 step 5: E3 (`nwords 0`), E4 (`nwords ≥ 1`) | = 0 / ≥ 1 | unchanged |
| 10.7 step 5: P6 "−2 with `nwords` = j" | equality | j ≤ 7 (recon/syscon.md:431, "1 ≤ j < n"). A flagged record with j = 7 passes. It loses only the one "inconsistent" case, and −2 is allowed at P6 either way |
| 8.2 REC (`nwords ≤ 8`; `nwords = 0` ⇒ `rx` all ff), POLL:NW0 (≥ 1) | bounds | unchanged |
| 1.7 words 31-51 (`nwords > 0` / `== 0`) | bounds | unchanged |
| 2.10 panel line 4, 2.8 boot printk | display | raw value; stated as display-only |
| H5, H6, H7, H8 (fields), H9, H10, N1-N11 other than above, step 7 | none | do not read `nwords` |

The 10.7 list ("`nwords` 7 or 8") names every one of these readers, and I
found no reader it omits. The H4 identification (leading hypothesis, dossier
9.6) does not depend on the 7/8 distinction. Where a short reply is a
symptom of a link shift, the next command's `drain`/`drain_last` still shows
the leftover word (N2).

**Consistent with itself and with the record format.**

- The field stays u8 at offset 22, and the struct string `'<…hBB…'` is
  unchanged.
- 1.2, 2.1 A4, the 6 preamble, 10.3 and 10.7 say the same thing.
- The code (`psc.c:275-280`) already implements it.
- See advisory A-5 for a wording nit.

### R-2: D10 wording (OD-2, DV-4): ACCEPTED

**Re-derived independently.** I ran the container with only
`-v /home/ubuntu/psp:/work:ro`, and `PATH` set to the staging_dir bins.

- `mipsel-linux-uclibc-objdump -d` on `work/out/20260927T204657Z/vmlinux`
  (baseline, `Syscon_cmd` 880cee10, 218 instructions) and on
  `work/out/20261006T021722Z/vmlinux` (release, `Syscon_cmd` 880ceed0, 268
  instructions).
- Extracted listings, sha256: `a04e1a5a…` (baseline) and `fa4d3359…`
  (release).
- My own script, not `d10_proof.py`:
  - takes the windows 880ceeec..880cf020 + 880cf054..880cf0bc (baseline) and
    880cefb0..880cf0e4 + 880cf210..880cf278 (release);
  - normalises `N(sp)`;
  - maps branch targets to window indices;
  - applies the inverse map s7→s3, s3→s4, s4→s5, s5→s6, s6→s7.

```
window instr: base 105 new 105
literal (stack-normalised) differences: 6
differences after inverse renaming: [(20, 'lw s8,S(sp)', 'nop', 0x880cef3c, 0x880cf000)]
non-stack memory ops equal in order after renaming: True (27)
calls in window: 0 0
lui in window: ['lui v0,0xbe58', 'lui v1,0xbe58'] both
writes to s3..s7 in new window: []
gp refs: 0
```

This equals `impl/syscon-window-diff.txt`, whose release copy differs only in
its header lines.

**Prologue values (release vs baseline).** Each renamed register holds the
same constant, which matches 7.2(a):

| Release | Baseline | Value |
|---|---|---|
| `s3` | `s4` | `0xbe240004` (`ori s3,v1,0x4` at 880cef28) |
| `s7` | `s3` | `0xbe240000` (`lui s7,0xbe24` at 880ceee4) |
| `s6` | `s7` | `0xbe240008` |
| `s4`, `s5` | `s5`, `s6` | 8 |
| `s8` | `s8` | `s7`/`s3` \| 0x24 |

None of these registers is written inside the window.

**Is the decision sound?** Yes.

- The 2.1 criteria were the G1-approved acceptance test all along.
- 7.2's "same instructions at another offset" described the expected output.
  It was not a stricter test.
- The three allowed differences are tightly bounded. On an in-order MIPS32
  pipeline, a value-preserving renaming of general registers leaves opcodes,
  operands, the dependency graph and MMIO order unchanged. That Allegrex has
  no register-number-dependent timing is marked UNVERIFIED, which is honest.
- The one delay-slot difference executes after the −3 decision and after the
  last MMIO read. The slot is on a path that is in practice unreachable
  (advisory A-3).

**D10: PASS.** Nothing is added in the window: 105 = 105, the same MMIO order
and form, no call, no global or `gp` load, no extra base reload. No lock and
no interrupt masking (7.1, unchanged).

The timeout patch is unchanged:
- `syscon.c:12-13` defines are identical;
- the −3 and −4 bounds and the teardown writes are the same instructions in
  the listing;
- −5 uses the same `bnel t8,16` logic.

**Consistent.** Summary 1, 2.1, 7.1 "Code layout" and 7.2 agree (advisory A-6
for a summary nit). The 0xc4 shift = 880cefb0 − 880ceeec, confirmed.

### R-3: costs outside the window (G2 F5): ACCEPTED

**Function sizes from the same objdump: exact.**

| Function | Instructions |
|---|---|
| `psc_syscon_cmd` | 102 |
| `psc_sc_exit` | 583 |
| `psc_fill_sc` | 151 |
| `psc_xfer_out` | 34 |
| `psp_joypad_thread` | 364 → 662 |

**Stack frames: as stated.**

| Frame | Bytes |
|---|---|
| wrapper | 72 |
| `Syscon_cmd` | 48 → 56 |
| hand-off | 128 |
| `psc_sc_exit` | 104 |
| `psc_fill_sc` | 64 |
| panel | 328 |

**My path count for a typical P command (cmd 0x08):** `ret > 0`, IE = 1, no
`lc`/LED/`pre` match, no new maximum.

- **Before S5:** `psc_syscon_cmd` from entry to its `jal Syscon_cmd`, plus
  the A2 store: **≈ 74** instructions.
- **After S20:**

  | Part | Instructions |
  |---|---|
  | hand-off 880cf0e8..880cf1dc | 62 |
  | `psc_xfer_out` P path | 32 |
  | `psc_sc_exit` P path | ≈ 167 |
  | `psc_dcount` | ≈ 22 |
  | `psc_fill_sc` | ≈ 118 |
  | `__bzero`(76) | ≈ 37 |
  | `memcpy`(16) | ≈ 20-30 (estimated, UNVERIFIED) |
  | wrapper tail | 6 |
  | **Total** | **≈ 465-475** |

- **Total:** ≈ 540 instructions, about 2.45 µs at 1 IPC and 220.9 MHz.

That lies inside the design's "≈ 460-610 instructions" and "≈ 2.1-2.8 µs"
(Summary 7, 5.4, D10 paragraph). The component split differs from 5.4
(advisory A-1); the totals and every derived figure hold:

- per poll ≈ 1,200-1,500 instructions;
- G3-low gap +2.1-3 µs;
- 7.3: δ ≤ 3.4 µs, so δ/T ≤ 0.085 %;
- 10 % of a 28 µs command = 2.8 µs.

The W path is stated as uncounted (UNVERIFIED) and is measured on the device
as `w_rec_cost_max`. That is acceptable.

**Is the decision sound?** Yes.

- The added code is the record append itself: the fill, the bracketed
  `lc`/LED/`pre` copies, the publish, and the cost measurement. The register
  save and restore in the hand-off is the price of leaving the window's
  allocation untouched.
- It all runs outside S5..S20, with no lock and no masking.
- Trimming buys at most ≈ 0.05 % of a tick.
- The design states the one direction in which the instrumentation could hide
  a failure (a longer G3-low gap, about half of the 5 µs wait the original
  code comments out). That gap is recorded per poll and reported (7.3, R6,
  10.7 step 6).

**D10: PASS.** Nothing is inside the window. Added time is stated, measured on
every command (`c_out − c_in`, `p_rec_cost_*`, HUD line 10) and small against
the ≥ 56 ms poll period. The ratio to the command's own duration is honestly
marked UNVERIFIED and is measured on the device. The stack figure is within
8 KB (advisory A-2: the sum of the cited frames gives ≤ ≈ 210 B, so 280 B is
conservative).

### R-4: `build_id` (OD-3, G2 F4): ACCEPTED

**Verified.**

- `init/version.c:37-39`: `linux_banner = "Linux version " UTS_RELEASE " (" BY "@" HOST ") (" COMPILER ") " UTS_VERSION "\n"`.
- `fs/proc/proc_misc.c:250-253`: `version_read_proc` prints
  `linux_proc_banner` (`init/version.c:41-44`) with `utsname()` sysname,
  release and version.
- The sysname is `UTS_SYSNAME "Linux"` (`include/linux/uts.h:8`).
- The fields come from `init/version.c:24-28`, the same compile-time strings.
- The sysctls are mode 0444 (`kernel/utsname_sysctl.c:86,95,104`).
- `CONFIG_UTS_NS` is off (`.config:157`).
- The only `utsname` writers are for `nodename` and `domainname`
  (`kernel/sys.c:1887,1933`).
- So `/proc/version` equals `linux_banner` byte for byte.
- The kernel computes `psc_crc32(0, linux_banner, strlen(...))`
  (`work/linux/arch/mips/psp/psc.c:1221`).
- zlib CRC-32 of `out/20261006T021722Z/banner.txt` (102 B, ending in `\n`) is
  **0x9b3c599e**, as stated.

**Is the decision sound?** Yes. Collector and kernel are one image, because
`pscol` is in the initramfs. So a build-time constant in the collector would
add nothing. KRN now proves that the stats block belongs to the running
kernel, and in passing that the collector's CRC matches the kernel's. The
decoder refuses maps from any image other than the packaged one, which is
correct given the per-build banner (verifier finding 4).

**D13: PASS.** KRN is still one of the eight pre-death checks, and a red KRN
is still an abort (RUNBOOK B4/B5, unchanged).

**Consistent.** 1.7, 8.2 and 10.1 agree on the CRC (zlib, initial 0, bytes
without the NUL; FILEHDR text up to its first NUL). See advisory A-4 for the
named directory.

### R-5: memory and image figures (OD-5, OD-6): ACCEPTED

**Verified.**

- `fs/binfmt_flat.c:471-472`: `#ifdef CONFIG_SONY_PSP flags |= FLAT_FLAG_RAM`.
- `:626-628`: one `do_mmap` of text + data + extra.
- `mm/nommu.c:744`: `kmalloc(len, …)`.
- `.config:50`: `CONFIG_SONY_PSP=y`.
- 51,904 + 2,896 + 112,720 + 16,384 = 183,968 B, which takes a 262,144-B
  block.
- 2 × 256 KB = 512 KB, 2.5 % of 20.8 MB.
- Image sizes from `ls`:

  | File | Before | After | Growth | Margin to 49,152 |
  |---|---|---|---|---|
  | `vmlinux.bin` | 1,723,228 | 1,766,859 | +43,631 | 5,521 |
  | `vmlinux-0.22.bin` | 899,402 | 936,321 | +36,919 | 12,233 |

  16,384 + 27,247 = 43,631.

**Is the decision sound?** Yes.

- Both blocks are still taken at boot, and the takeover runs in the
  supervisor's own block. So "no allocation after boot" (D7, IF2) holds.
- If the 256 KB `exec` fails at boot, there is no HUD and the self-test
  aborts; nothing is lost.
- Keeping 49,152 B as the bound, with every G2 attempt restating both growths,
  is the right minimum, because the pspboot limit is unknown (R20,
  UNVERIFIED).

**D12: PASS.** The budget arithmetic in 5.3 is shown and correct. Stick
volume is unchanged.

### R-6: two stale texts: ACCEPTED

**Verified.**

- RECS ≤ 4 × 8,576 + 80 + 20 = 34,404:
  - 8,576 = 48·80 + 24·40 + 2·288 + 64·40 + 8·80;
  - 80 = 5 rings × 2 blocks × `'<BBHI'` 8 B.
- That matches 10.2's "per ring one new-records block … preceded by at most
  one re-send block". Re-sent records count inside the cap (4.6, "inside the
  normal cap").
- The flush is 34,404 + 104 + 788 + 2,420 + 20 = 37,736, padded to 37,888,
  which is ≤ 40,960.
- 2.11's bytes 42-44, 46 and 78-79 match 1.2:
  - `pre_wrk` u16 at 42;
  - `pre_cls` at 44;
  - `ms_delta` at 45;
  - `pre_flags` at 46;
  - `pre_tot` u16 at 78.
- It also matches K35.

**D20: PASS.** The decoder text now matches the format field for field, and
D12's flush bound still holds.

---

## 4. Advisories (non-blocking; text only; no G1 round needed)

**A-1 (R-3): component counts.**
- By my path count the entry part is ≈ 74 instructions, not ≈ 60.
- After S20, the hand-off is ≈ 94 (62 + 32), not ≈ 85.
- `psc_sc_exit` on the typical P path is ≈ 190 including `psc_dcount`, not
  ≈ 250-300. `psc_fill_sc` plus `__bzero`/`memcpy` is ≈ 180.
- The totals (≈ 540) and all µs figures hold.
- Close it: in the restatement 17 already requires of G2 attempt 2, give
  per-path counts with the path assumptions stated.

**A-2 (R-3, 5.3): stack figure and citation.**
- Over the baseline's 48-B frame, the cited frames give +208 B inside
  `Syscon_cmd` (72 + 8 + 128) or +192 B in the exit (72 + 104 + 64). The
  ≈ 280 B figure is conservative.
- The citation `include/asm-mips/thread_info.h:65-66` should be `:66-67`.
  `:82` is correct.

**A-3 (R-2, 7.2(b)): which exit the changed delay slot is on.**
- The changed delay slot belongs to the **first-iteration** −3 exit, C17-C20
  (baseline 880cef30-880cef3c, release 880ceff4-880cf000).
- That exit fires only if the volatile `spin` slot reads 0 immediately after
  `sw s1` stored 1,000,000.
- The full-budget −3, after the drain iterations, leaves through C103-C104
  (`beq v1,v0,EXIT` / `li t3,-3`), which is **unchanged**.
- The text's "occurs only on a −3 exit, after 1,000,001 drain iterations"
  therefore names the wrong exit. The conclusion is stronger than stated.

**A-4 (R-4, 10.1): the release directory.**
- 10.1 names `work/out/20261006T021722Z` as holding `System.map`,
  `epcmap.txt`, `regmap.txt`, `panellayout.txt`, `banner.txt` and
  `build_id.txt`.
- Today it holds only `System.map` and `banner.txt`. The maps are in
  `handoff/impl/release-20261006T021722Z/` and `handoff/impl/`.
- Stage 2 should assemble one BUILD directory for the packaged image. The
  G2 attempt-2 image will in any case have a new banner and `build_id`.

**A-5 (R-1, 1.2): wording.**
- "the loop leaves the same state … (`syscon.c:201-217`)" is true of the
  generated code (`t0`, `a3`). It is not true of C semantics, where `i` and
  `ptr` differ (14 vs 16). 2.1 A4 states the build dependence correctly.
- Optionally, the decoder could print "ambiguity live" whenever flagged
  records fall in a classification window, not only when the template holds
  them. 10.3 already counts them per command and origin in REPORT.md.

**A-6 (R-2, Summary 1): missing condition.** The summary omits "and after the
path's last MMIO access" from the delay-slot allowance. 2.1 and 7.2, which
are normative, include it.

## 5. Attacks tried (WORKFLOW principle 4)

1. **Another `nwords` ambiguity besides 7/8.** Traced `t0` for k = 0..8 and
   the −3, −4 and −5 exits, including a −5 after a retry. Only k = 7 vs
   k = 8 with an 8th word of 0xFFFF collide. **Held.**
2. **A rule that reads `nwords` and is not in the 10.7 list.** Grepped every
   occurrence in DESIGN.md (sections 0, 1.2, 1.7, 2.1, 2.10, 6, 6.1, 8.2,
   10.3, 10.7, 17). None is missing. **Held.**
3. **The P6 cross-check with a flagged record.** j ≤ 7 by recon §5.1, and set
   membership passes it. One "inconsistent" detection is lost, and the
   P-point classification is unchanged. **Held** (stated in 10.7).
4. **A healthy reply that is always 8 words of 0xFF padding** (every 0x08
   record flagged). The bytes, `ret` and the driver behaviour are identical
   either way. A one-word shift shows as `drain`/`drain_last` on the next
   command. The template prints that the ambiguity is live. **Held.**
5. **Renaming that is not value-preserving.** Checked the prologue constants
   and found no write to s3..s7 inside the window. **Held.**
6. **The delay slot on a path that matters.** It is on the unreachable
   first-iteration exit, after the last MMIO access. **Held** (A-3).
7. **The window changed outside the renaming.** My own script found one
   difference (the delay slot), the MMIO order equal, and no calls, `gp` or
   extra `lui`. **Held.**
8. **The cost figures understated.** My path count is inside the stated
   totals, though the parts differ. **Held** (A-1).
9. **`/proc/version` differs from `linux_banner`** (namespaces, a sysctl
   write, a different sysname). `CONFIG_UTS_NS` is off, the sysctls are
   0444, and `UTS_SYSNAME` is "Linux". **Held.**
10. **A late allocation reintroduced by the 256 KB figure.** No: both blocks
    are taken at boot. **Held.**
11. **An unrelated change hidden in the diff.** All 27 hunks were mapped.
    **Held.**

## 6. What I did not verify

- Runtime behaviour, the CP0 Count rate, Allegrex pipeline timing, and
  whether pspboot loads the image (R20). All are UNVERIFIED and remain open
  risks in 11.1.
- The W-path instruction count, which the design also marks UNVERIFIED.
- Exact `memcpy` iteration counts.
