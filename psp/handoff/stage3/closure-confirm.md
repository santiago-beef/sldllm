# Stage 3 closure: confirmation review

Reviewer: Stage 3 closure reviewer, fresh context, 2026-10-07. I did not write
the closures, the design, the kernel, `pscol` or the decoder, and I did not
review them at any earlier gate. I edited no artifact. G3 R8 is the human
operator's signature; nothing here marks or implies it.

**Inputs read:** DOSSIER.md (section 9 in full), WORKFLOW.md (Stage 3, G3,
Amendments), design/DESIGN.md (section 17 and the new section 18, plus every
sentence section 18 replaces), design/RUNBOOK.md (A2), gates/LOG.md,
impl/IMPLEMENTATION.md (9.2 and the new section 10), gates/G2-attempt2-review.md,
gates/G2-attempt2-verify.md, gates/G1-ruling1-review.md and
gates/G1-ruling1-redteam.md. The closer's evidence: stage3/closure.md,
stage3/closure.diff, stage3/measure/, stage3/logs/, stage3/pre-closure/, and
the commits `48dcc1b9..0b5ba13e` on `stage2-trace`.

**My evidence** is in `stage3/logs/confirm-*`:

| Log | What it holds |
|---|---|
| `confirm-state.log` | frozen image, package and BUILD checksums, branch file list, kernel inputs, protected files, original tree manifest (end of review) |
| `confirm-rebuild.log` | my own identity-pinned rebuild of HEAD `0b5ba13e`, made in a separate clone |
| `confirm-measure-rerun.log` | my re-run of `stage3/measure`, and its cross-check with `pathcount.txt` |
| `confirm-measure-extra.py` / `.log` | three runs that `measure.py` does not make: T2a, the K5 model at 8 words, and the gap's MMIO list |
| `confirm-k3-k6-demo.py` / `.log` | my attacks on the new decoder code |
| `confirm-decoder-tests.log` | the decoder suite, 44 tests |
| `confirm-pscol-run-all-20.log`, `confirm-pscol-krn.log` | the `pscol` host tests and the KRN argument forms |

## Verdict

**Not all closed.** 12 of the 19 rows are confirmed closed; 7 are not (N1, N2, Verifier-2, K3, K5, K6, K7).

| Item | Confirmed closed | One line |
|---|---|---|
| G2-N1 | **no** | One row of DESIGN 18.1 (T2a, "+208, 0.94 µs") was never re-measured. Executed, it is +218..+222 (≈ 0.99-1.00 µs). The rest is reproduced. The LOG entry is still to be appended. |
| G2-N2 | **no** | Composite: K3, K5, K6 and K7 below are not confirmed. K1, K8, A-2, A-3, A-5 and A-6 are. |
| G2-N3 | yes | `7\|8` appears in the WT, H4 and WB lines and is tested end to end. |
| Verifier-1 | yes | `run.sh` forwards every argument. `./pscol_test krn`, the call `checks.sh` makes, now gives the four KRN rows. |
| Verifier-2 (R20) | **no** | Not handled by the closer. It needs the device or the human. No R20 report exists. |
| Verifier-3 | yes | The packaged checksum is in the gate log and equals the deployed file. The decoder pins it, and 18.4 states the rule. |
| Verifier-4 | yes | The G2 reviewer ruled on OD-7, and I reproduced the independent re-measurement. |
| A-1 | yes | Per-path counts with the path stated. They are reproduced, and the hand-off block checks against the listing. |
| A-2 | yes | Stack +208 / +216 B was measured. `thread_info.h:66-67`, `:82` are correct in the original tree. |
| A-3 | yes | The first-iteration −3 exit is correct in both listings. |
| A-4 | yes | There is one BUILD directory, and 10.1's example is replaced. |
| A-5 | yes | The wording is fixed. The optional per-window print is implemented and tested. |
| A-6 | yes | The Summary 1 allowance gets the last-MMIO condition. |
| K1 | yes | The text is right, and so are the compiled-loop facts it cites. |
| K3 | **no** | The decoder certifies the BUILD directory, not the maps it actually reads. Both bypasses are shown below. |
| K5 | **no** | The pre-registered path model is not "exact": at 8 words, I is 8 too large, so the "upper bound" is not one. |
| K6 | **no** | The watchdog-edge counts are structurally zero, and they are labelled as removed or created straddles. |
| K7 | **no** | The text gives `fs/binfmt_flat.c:458`, a blank line, and calls the red team's correct `:459` "off by one". |
| K8 | yes | The headroom formula, the minimum, the 1 KB flag and the user-mode case are all right and tested. |

**Release check.** No item needs a kernel, `pscol` or package change. Nothing
found here touches the frozen image. Every fix listed under "What would close
each open item" is design text or host tooling (decoder, `stage3/measure`).

## 1. Release, package and branch (all confirmed)

- **Frozen image.**
  `work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin` has
  sha256 `4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8`.
  I checked it at the start and at the end of the review.
- **Package checksums.**
  - `SHA256SUMS` passes for all 4 files (exit 0).
  - `BUILD/SHA256SUMS` passes for all 8 files (exit 0).
  - `BUILD` is `diff -r`-identical to `impl/release-20261006T052947Z/BUILD`.
  - EBOOT.PBP, kmodlib.prx and pspboot.conf are byte-identical to `pspboot-baseline`.
- **Package files.** The package holds 15 files. None was modified after
  2026-10-06 06:00 UTC. `PROVENANCE.txt` is covered by no SHA256SUMS; its
  mtime is still the packaging time, 05:37:38, and its sha256 is
  `8a0fbd08…` (`confirm-state.log`).
- **Branch diff.** `git diff --name-status 48dcc1b9..HEAD` (`0b5ba13e`) lists
  16 added files, all under `psc-tools/`:
  - `README`;
  - `decoder/{README, TESTS.txt, check_format.out, check_format.py, psc_format.py, psc_maps.py, pscdec.py, pscdec_analysis.py, pscdec_parse.py, synth.py, test/run_tests.py}`;
  - `pscol-test/{run.sh, sim.c, vectors.c, xcheck.py}`.

  Outside `psc-tools/` the diff touches 0 files.
- **None of these feeds the image or the initramfs.**
  - The kbuild directory lists are fixed: `Makefile:436-440` and `:559` name
    init, drivers, sound, net, lib, usr, kernel, mm, fs, ipc, security,
    crypto and block.
  - Nothing outside `psc-tools/` names `psc-tools` (0 hits).
  - `CONFIG_LOCALVERSION_AUTO` is off (`.config:154`), so the git HEAD does
    not reach the banner.
  - The initramfs comes from `CONFIG_INITRAMFS_SOURCE` = `psp-initramfs.cpio`
    (`.config:163`). Its blob `6bac8c0c…` and the `.config` blob `4823ea33…`
    are the same at `48dcc1b9` and at HEAD.
  - `pscol` (not in git) is unchanged: bFLT `7d7a5d78…`, `pscol.c`
    `1e89ac0a…`. These are the IMPLEMENTATION 5.4 values.
- **Independent rebuild.** I cloned the work tree into my scratchpad, checked
  out `0b5ba13e`, and built it in the container with the release identity
  (`KBUILD_BUILD_VERSION=1`, timestamp `Tue Oct 6 05:32:47 UTC 2026`,
  hostname `psp-work-build`).
  - `vmlinux`, `vmlinux.bin`, `vmlinux-0.22.bin` and `System.map` are
    byte-identical to the release.
  - `vmlinux-0.22.bin` is byte-identical to the deployed file.
  - The shared work tree was neither cleaned nor built
    (`confirm-rebuild.log`).
- **Closer's change record.**
  - `closure.diff` equals a fresh `diff` of DESIGN.md against
    `pre-closure/DESIGN.md`, and of the tooling `16d3bc28..0b5ba13e`.
  - DESIGN.md changed only by appending lines 2907-3098. `pre-closure/DESIGN.md`
    is DESIGN.r7 plus `g1ruling.diff`.
  - RUNBOOK.md is byte-equal to RUNBOOK.r7.md.
  - The import commit `16d3bc28` is byte-identical to the delivered G2 tooling
    (`pre-closure/`).
- **Original tree.** `sha256sum -c gates/baseline-tree.sha256` exits 0 with
  23,495/23,495 OK, at the start and at the end.

## 2. Items confirmed closed

**G2-N3.**
- *Advisory:* `G2-attempt2-review.md:599-610` asked the H4/WB evidence lines
  to print `7|8` for a record flagged `nw7or8`, with a test.
- *Code:*
  - `nwtext()` is at `pscdec_analysis.py:31-34`.
  - It is used in the WT listing (`:1306-1307`), the H4 line for the Nop and
    for the thread (`:1331-1338`), and the WB line (`:1360-1362`).
- *My grep:* no other evidence line prints a raw `nwords`. The P6 cross-check
  already said "(7 or 8)" (`:1490`).
- *Tests:*
  - end to end, `Stage3Closure.test_n3_a5_evidence_prints_7or8`, which uses
    `synth.py nop7`;
  - the WB format string, `test_n3_wb_line`;
  - `NwordsSevenOrEight.test_evidence_text` (`run_tests.py:705-714`).
- My run of the suite: 44/44 OK, and `check_format.py` OK.

**Verifier-1.**
- *Asked for* (`G2-attempt2-verify.md:512-527`): forward `"$@"` in `run.sh`,
  and have `checks.sh` run the packaged form.
- *`run.sh:16-20`:* forwards `"${@:3}"` and refuses `krn <banner>` without a
  build_id (rc 2).
- *`sim.c`:*
  - with no banner given, `krn` and `all` look up the package BUILD
    (`:1597-1633`, `:1738-1753`);
  - so the unchanged `checks.sh:34` call `./pscol_test krn` gets the packaged
    rows.
- *My runs, on a scratch copy* (`confirm-pscol-krn.log`):
  - `run.sh krn`, `run.sh krn banner id` and the bare `./pscol_test krn`
    each give 4/4 PASS;
  - `krn banner` alone gives rc 2;
  - a wrong build_id gives `RESULT FAIL` (the check has teeth);
  - the ASan/UBSan `krn` and `names` runs are clean;
  - `run.sh all 20` gives `RESULT PASS (0 failing cases)`, with 4 KRN rows.
- *Not re-running `checks.sh` is correct.* It runs `cbuild.sh`, and
  `cbuild.sh:22-29` rewrites the delivered `work/pscol/pscol`.

**Verifier-3.**
- *Asked for* (`G2-attempt2-verify.md:532-538`): "G3 records the packaged
  checksum".
- The release checksum `4f9b69dc…cac8` is in `gates/LOG.md:353-355`. I
  confirmed it equals the deployed file.
- DESIGN 18.4 (`:3022-3047`) states the default-identity rule, and the cited
  lines are correct:
  - `build.sh:62-69` is the identity block;
  - `build.sh:80` is the log line;
  - the release log, line 8, reads `KBUILD_BUILD_VERSION='' … REPRODUCE_BASELINE='0'`.
- The decoder default pins that image (`pscdec_analysis.py:64`).
- *Still to do at G3 R3, and not a condition of this advisory:* the RUNBOOK
  A2 line (`RUNBOOK.md:168`) still shows the placeholder. The Stage 3
  packager fills it.

**Verifier-4.**
- *Asked for* (`G2-attempt2-verify.md:539-545`): "a G2 reviewer or G1 text
  ruling on OD-7".
- That ruling is in `G2-attempt2-review.md:521-533`.
- The independent re-measurement now exists. I re-ran it:
  - `measure-output.json` is byte-identical to the closer's (sha256
    `03f1eeca…`);
  - SUMMARY.txt is identical;
  - the inputs are the release `vmlinux.bin` `22fc3934…`, which is the
    gunzip of the deployed file.
- It is independent of `pathcount.py`:
  - it decodes raw instruction words, where `pathcount.py` parses objdump
    text, and shares only 6 idiomatic lines with it;
  - it agrees with `pathcount.txt` on P08 +557, P33 +560, TICK +48, WDP
    +1,104 and the stacks;
  - WD is +925 against +922: `psc_sc_exit` runs 354 against 351 in the warm
    run (`confirm-measure-rerun.log`).

**A-1.**
- *Asked for* (`G1-ruling1-review.md:417-424`): per-path counts with the path
  stated.
- DESIGN 18.1, row 1 (`:2939`), gives:
  - the path: valid reply, IE 1, no `lc`/LED/`pre` match, no new maximum;
  - the counts: entry +75; hand-off 62 + `psc_xfer_out` 32; `psc_sc_exit`
    167/170; `psc_fill_sc` 111; memset 44 (`__bzero` 29 + `memset_partial`
    13 + `memset` 2); memcpy 29; `psc_dcount` 30.
- These sum to +482 with the 7-instruction wrapper tail (`psc_syscon_cmd` is
  80 = 73 + 7).
- I reproduced them. I also checked from my own listing that 880cf0e8..880cf1dc
  is 62 straight-line instructions (no branch; one `jal psc_xfer_out`).

**A-2.**
- Measured stack, reproduced:
  - the thread path is 112→320 B (+208);
  - the Nop path is 128→344 B below `pt_regs` (+216), so 520 B below the
    interrupted `sp`;
  - T2d is 488 B below `pt_regs` (664 B).
- The corrected citations hold in the original tree:
  - `include/asm-mips/thread_info.h:66-67` is the 4 KB/32-bit
    `THREAD_SIZE_ORDER (1)`;
  - `:82` is `THREAD_SIZE`;
  - `.config:98`, `:100` are `CONFIG_32BIT=y` and `CONFIG_PAGE_SIZE_4KB=y`.

**A-3.**
- In my objdump listings:
  - the changed delay slot is release `880cf000` `nop`, against baseline
    `880cef3c` `lw s8,40(sp)`;
  - it belongs to the first-iteration `bne v1,a3` / `j` exit (release
    `880ceff4..880cf000`).
- The full-budget exit is unchanged: `beq v1,v0` / `li t3,-3` at release
  `880cf018/1c` and baseline `880cef54/58`.
- 18.3 (`:3002-3008`) names the replaced sentence correctly (`:1790-1791`).

**A-4.**
- `deploy/uClinux_TRACE/BUILD` is the single BUILD directory and equals the
  release BUILD.
- 18.4 (`:3035-3047`) replaces 10.1's stale `work/out/20261006T021722Z` /
  `0x9b3c599e` example (`:2081-2082`).

**A-5.**
- *Wording.* The K1 text (`:2990-3001`) says the identity of the two exit
  states belongs to the compiled loop, not to `syscon.c:201-217`.
- *Optional print.* `flagged_in_window()` (`pscdec_analysis.py:1619-1628`)
  prints "the ambiguity is live in this window" for every onset candidate
  (`pscdec.py:587-590`) and for the classification window (`:516-519`).
  The test asserts both strings.

**A-6.** The Summary 1 allowance (`:51-53`) is replaced by 18.3 (`:3009-3011`)
with "and after the path's last MMIO access", as in 2.1 and 7.2.

**K1.** The replacement text (`:2990-3001`) says:
- exact for 0-6, and for 8 when the 8th word is not 0xFFFF;
- every recorded 7 is flagged;
- the identity is a property of the compiled loop.

I verified the loop in my release listing:
- `880cf218 li t0,2` … `880cf264`. The empty-FIFO exit (`beqz` at `880cf22c`)
  and the fall-through after the 8th word (`bnez t1` at `880cf260`) both
  leave `t0` = 16 and `a3` = `rx_buf` + 16.
- The executed table (`pathcount.txt` 9.2.5) agrees: 7 words record 7,
  flagged.

18.3 names `:248`, `:476` and `:2893`, the only places that carry the old
wording (my grep).

**K8.**
- `stack_headroom()` (`pscdec_analysis.py:1755-1787`), for kernel-mode WT
  records:
  - selects them by `ext_flags` b2. The kernel sets it from `ST0_CU0`
    (`work/linux/arch/mips/psp/psc.c:386`), and `sp` is `regs->regs[29]`
    (`:383`);
  - computes `sp` − its 8 KB block base − 52;
  - 52 is `sizeof(struct thread_info)`: `TI_REGS` 48 + the 4-byte `regs`
    pointer (`thread_info.h:24-38`, `asm-offsets.h:68`).
- It then:
  - subtracts the measured 520 B;
  - reports the minimum;
  - flags anything below 1 KB, which is stricter than K8's raw-value flag.
- A user-mode interruption gets 8192 − 32 − 52 − 176 − 344 = 7,588 B.
- Tested in `test_k6_k8_counts`.

## 3. Items not confirmed (with evidence)

### G2-N1: one restated row was not re-measured, and it is low

- **Claim.** DESIGN 18.1 (`:2929-2935`) says the table is "re-measured from
  the released image … with an interpreter written for this closure" and
  "supersedes" 5.4, 7.1, 7.3, R6 and R13.
- **Where the T2a figure comes from.** The row "A tick that finds the thread
  running in a command (T2a) | +160 more (+208 in all) | 0.94" (`:2942`)
  has no scenario in `measure.py`. It is not in SUMMARY.txt. It is
  IMPLEMENTATION 9.2's derivation, 48 + (198 − 38), taken from the
  `psc_tick_hook` totals of WDP and WD.
- **What that derivation leaves out.** T2a also calls `psc_cur_regs`
  (13 instructions; WDP runs it 26 against WD's 13).
- **My run.** I ran the case on the closer's own interpreter: an ordinary
  tick, 37 mod 1250, with the thread at S14 of its 0x08 and `t_busy_p` = 1
  (`confirm-measure-extra.log` part 1). The tick adds:
  - **+218** on the first tick of a command;
  - **+222** on every later tick of the same command (`lc_n` ≥ 2).

  That is ≈ 0.99-1.00 µs, not 0.94 µs.
- **Size.** The understatement is ≈ 5 %, in the direction N1 complained
  about. It changes no conclusion. But a superseding table that claims
  re-measurement must not carry an unmeasured row that is low.
- **Every other row reproduces** (my re-run, plus the arithmetic of 18.2):
  - 553 = 48 + 109 + 203 + 95 + 7 + 16 + 75;
  - 1,119 = 553 + 566;
  - 566 = 485 + 6 + 75;
  - 1,708 per poll;
  - δ/T = 5.1/4,000 = 0.13 %.

  The 10 MMIO accesses in the G3-low gap are right (`confirm-measure-extra.log`
  part 3, executed, the same in both builds): r `be240004`, w `be24000c`,
  r `be58000c` twice, w `be580020`, then 2 × (r `be58000c`, w `be580008`),
  then w `be580004`. The red team's "9" was a mis-sum of its own list of 10
  (`G1-ruling1-redteam.md`, section 1.4).
- **Also pending.** N1's closure text asks the orchestrator to record in
  `gates/LOG.md` that the measured figures supersede the design's. That entry
  has not been appended. It is the orchestrator's to make.

### G2-N2: composite

N2 closes when each part does. K1, K8, A-2, A-3, A-5 and A-6 are confirmed.
K3, K5, K6 and K7 are not (below). N2 also asked for a G2 re-check of the new
decoder code; sections K3, K5 and K6 are that re-check.

### K3: the identity certificate does not bind the maps the decoder reads

What exists and holds:
- `image_identity()` (`pscdec.py:207-249`) verifies the BUILD directory:
  - its SHA256SUMS, which must cover `IMAGE.sha256`;
  - `IMAGE.sha256` against the pinned release hash.
- Its errors refuse the EPC analysis (`pscdec_analysis.py:482`).
- The four cases in `test_k3_image_identity` pass.

What it leaves open:
- The maps the EPC analysis actually reads are chosen by
  `pick = lambda name, explicit: explicit or <BUILD/name>` (`pscdec.py:281`).
  So an explicit `--system-map`, `--epcmap`, `--regmap` or `--build-id`
  silently wins over the verified BUILD.
- SHA256SUMS is not required to list the map files.

My demonstration (`confirm-k3-k6-demo.log`) uses the synthetic H4 stream with
an epcmap of "other code", in which the labels S11 and S14 are swapped:

| Decoder input | H4 step printed | REPORT says |
|---|---|---|
| (0) the verified BUILD | S14 → P4 | "image identity (K3) … MATCH", EPC analysis enabled |
| (a) the same `--build`, plus `--epcmap other/epcmap.txt` | **S11 → P2 k=2** | the same "MATCH", EPC analysis enabled |
| (b) a BUILD whose SHA256SUMS lists only `IMAGE.sha256` | **S11 → P2 k=2** | "MATCH (SHA256SUMS verifies 1 files)", EPC analysis enabled |

K3's purpose (red team KR1(b)) is to stop the H4 step, which dossier 9.6 makes
load-bearing, from being read through another build's map. The new "MATCH"
line certifies exactly that, and here it is false.

### K5: the pre-registered path model is wrong for 8-word replies

DESIGN 18.5 (`:3055-3060`) and the code comments (`pscdec_analysis.py:74-78`,
`:1631-1635`) make two claims:
- I = I0 + 11·ack + 15·nwords + 5·rx[1] is "exact on the release image";
- I and N are lower bounds, "so the bound stays an upper bound".

The closer fitted this model on 2..7-word replies only. I executed the release
image for 1..8 words × ack 0/1/5/37 × both commands, 72 cases
(`confirm-measure-extra.log` part 2):
- **all 56 cases of 1-7 words are exact;**
- **all 16 cases of 8 words have I 8 too large.** The last iteration skips the
  loop-back `addiu`/`j`/`addiu` (3 instructions), and there is no final
  empty-FIFO check (5 instructions). See release `880cf220..880cf264`.
- N is right, including its −1.

So for an unflagged 8-word clean record, `mmio_bound()` (`:1645`) can return a
value below the true m. The error is small, ≤ ≈ 1 ns. But the bound is
pre-registered (G3 R6), and as written it is not a bound.

*Advisory, not a closure condition:* a negative raw bound, meaning the
instruction model exceeds the measured duration, is clamped to 0 without a
word (`:1674`). That case means the 1-IPC / Count-rate assumption failed. The
printout should say so.

### K6: the watchdog-edge counts cannot detect what they are labelled as

The printout (`pscdec_analysis.py:1742-1748`; DESIGN 18.5 `:3065-3069`) gives
"(n, n at a watchdog edge: straddles the shift could have removed /
created)". It computes window positions from the recorded `c_in` + 200 and
`c_out` − 188 (`:1721-1734`).

A window that a Nop interrupts, or that comes after it, is recorded after the
Nop. At m = 0 and 20 ACK polls, the watchdog tick alone runs ≥ 1,491
instructions before `irq_enter` (WD, SUMMARY.txt:23). That is longer than
δ(0x08) = 1,119 and δ(0x33) = 553 Counts. Therefore:
- **"end after watchdog edge" is structurally 0.**
- **"start after watchdog edge" counts only a Nop that lands in the last 200
  Counts before S5** (between `c_in` and S5, where `c_in` was recorded before
  the edge).
- It misses a Nop in any other part of the 1,119-Count shift: the 0x33's
  window or its exit/REC code, the thread code, or the wrapper entry before
  `c_in`.

My demonstration (`confirm-k3-k6-demo.log`) builds a physically consistent case:
- the 0x33's `c_out` is 10 Counts before the watchdog edge;
- the Nop lands in its REC code (P0);
- the 0x08 is recorded after the Nop.

The undisturbed 0x08 S5 is at E + 609 Counts, so the baseline S5 is at E − 510.
In the baseline the Nop lands inside the 0x08 window whenever that window
lasts more than 2.3 µs (any MMIO latency above about 15 ns at the modelled
ACK). That is a straddle the instrumentation removed. The decoder prints
**0, 0**.

The same bias, an edge's own interrupt pushing nearby windows out of the δ
band, lowers the "density" read at ordinary tick edges. EX2's own
recommendation, a count of the P0 Nops within δ after a P33 `c_out`
(`G1-ruling1-redteam.md:601-633`), is not implemented. For the no-death
inference on the leading hypothesis, the printout as it stands would report
"no straddles removed or created" whatever happened.

### K7: a new wrong citation

- K7 (`G1-ruling1-redteam.md:96`) cites `fs/binfmt_flat.c:459` for
  `text_len = data_start`.
- In the original tree, line 459 is `text_len  = ntohl(hdr->data_start);`
  and line 458 is blank (`sed -n 454,460p`, and `grep -n` gives 459).
- DESIGN 18.3 (`:3014`) cites `:458`. `closure.md:61` says "the red team's
  `binfmt_flat.c:459` is `:458` in the tree". `IMPLEMENTATION.md:979`
  repeats `:458`.
- The rest of K7 holds:
  - 51,968 = 0xcb00;
  - `mm/nommu.c:745` is the `kmalloc`;
  - `thread_info.h:66-67`;
  - 183,040 = 52,768 + 2,912 + 110,976 + 16,384, which matches the
    released bFLT header.

### Verifier-2 (R20): not closed

- **Who handles it.** The closer did not take it; it points to a separate R20
  agent.
- **The report is missing.** `handoff/stage3/r20/REPORT.md` does not exist at
  the time of this review. DESIGN 11.1 R20 is unchanged.
- **What would settle it.** The advisory's own closure is "a boot on the
  device". So it needs the human or Stage 4. No agent can confirm it.
- **No image change.** Nothing found here calls for a change to the image.

## 4. What would close each open item (all of it tooling or text; no kernel, pscol or package change)

- **N1.**
  - Measure the T2a row and correct DESIGN 18.1 `:2942`: +218 on the first
    tick of a command, +222 on later ticks, ≈ 0.99-1.00 µs; +170/+174 more
    than an ordinary tick, `psc_cur_regs` 13 included.
  - Preferably add the scenario to `stage3/measure/measure.py`, so the whole
    table is what the interpreter ran.
  - Then the orchestrator appends the LOG entry that N1 names.
- **K3.**
  - Require BUILD/SHA256SUMS to list and verify every file the decoder reads
    from BUILD: `System.map`, `epcmap.txt`, `regmap.txt`, `build_id.txt` and
    `IMAGE.sha256`.
  - While the image check is active, refuse the EPC analysis when
    `--system-map`, `--epcmap`, `--regmap` or `--build-id` overrides BUILD,
    or print "identity NOT established" for that input instead of MATCH.
  - Add cases (a) and (b) to `test_k3_image_identity`.
  - Add one sentence to 18.4.
- **K5.**
  - At `pscdec_analysis.py:1645`, subtract 8 from I for an unflagged 8-word
    record.
  - Add an 8-word vector to `test_k5_mmio_bound_arithmetic`.
  - Correct the "exact" claims in 18.5 and at `:74-78` and `:1631-1635`.
- **K6.**
  - Replace or rename the watchdog-edge counts.
  - Count removed straddles from the WT records themselves: Nops whose W step
    is P0 (EXIT/REC of the 0x33 or ENTRY of the 0x08) within δ before the
    0x08's undisturbed S5. This is EX2's count.
  - Count created straddles likewise: Nops within the last δ before an
    undisturbed S20.
  - Correct for each edge's own interrupt duration (the W record carries the
    Nop's duration), or state the bias in the ordinary-edge density line.
  - Correct the 18.5 K6 bullet.
  - Test with records whose times follow the Nop.
- **K7.**
  - Change DESIGN 18.3 `:3014` to `fs/binfmt_flat.c:459`.
  - Delete the "off by one" remark in `closure.md:61`.
  - Correct `IMPLEMENTATION.md:979`.
- **N2.** It closes when K3, K5, K6 and K7 are re-confirmed.
- **Verifier-2.** The R20 item: either a device boot, or the human's ruling
  in the gate log.

## 5. Attacks tried (WORKFLOW principle 4)

1. **The closure touches the image through the branch** (a git-describe
   banner, a Makefile glob, or the cpio). The file list, the kbuild
   directory lists, `LOCALVERSION_AUTO` off, the blobs unchanged, and an
   independent rebuild in a separate clone, byte-identical. **Held.**
2. **The package changed under its SHA256SUMS** (e.g. PROVENANCE or an extra
   file). There are 15 files, none touched after packaging, and every sum
   passes. **Held.**
3. **The re-measurement is not reproducible, or not independent.**
   Re-running it gives byte-identical output. Its decoder is raw-binary, and
   it agrees with `pathcount.py` on all shared rows within 3 instructions.
   **Held.**
4. **A restated row was never measured.** The T2a row: **found** (N1).
5. **The K5 model is extrapolated beyond its fit.** At 8 words: **found** (K5).
6. **The gap's MMIO count.** 10 is right (the red team mis-summed 9).
   **Held.**
7. **The decoder is fed the maps of other code while certifying identity.**
   Two routes: **found** (K3).
8. **The K6 counts on a physically consistent straddle.** **Found** (K6).
9. **The K8 formula against `struct thread_info`, the CU0 convention and the
   kernel stack top.** **Held.**
10. **The `7|8` text in every H4/WB/WT evidence line.** I grepped every
    print of `nwords`. **Held.**
11. **`run.sh` argument forms, a missing package, a wrong build_id, and
    sanitizers.** **Held.** The wrong build_id fails as it should.
12. **The replaced sentences match their citations** (`:51-53`, `:248`,
    `:417`, `:476`, `:904-907`, `:1551-1553`, `:1559`, `:1790-1791`,
    `:2081-2086`, `:2893`). They match. The only bad citation is K7's
    `:458`.
13. **The cited source lines.** `binfmt_flat.c:459` (correct; the closer's
    `:458` is wrong), `nommu.c:745`, `thread_info.h:66-67`, `:82`, and
    `build.sh:62-69`, `:80`. **Checked.**

## 6. UNVERIFIED (unchanged by this review)

- **All µs figures.** They assume 1 instruction per Count and Count at
  220,912,896 Hz, with no cache or MMIO latency modelled. This is DESIGN 5.4's
  assumption.
- **The real syscon ACK latency, the MMIO latency m, and the Nop's real
  duration.** The K6 argument needs only the lower bound of 1,491
  instructions, which holds at m = 0.
- **Whether a healthy reply is ever 8 words.** This decides whether the K5
  error can occur in a run.
- **Whether pspboot loads the 1,767,264-B image** (R20).

## State left behind

- **Written in the handoff tree:** this file, plus `stage3/logs/confirm-*`
  (8 logs, 2 scripts).
- **Not touched:**
  - DOSSIER.md, WORKFLOW.md, gates/LOG.md and the past gate reports;
  - DESIGN.md, RUNBOOK.md and IMPLEMENTATION.md;
  - the closer's files;
  - `work/linux` (still `stage2-trace` @ `0b5ba13e`, porcelain empty),
    `work/pscol`, `work/decoder` and `work/deploy`.

  The protected-file sha256 values are in `confirm-state.log` and equal the
  closer's post-state.
- **Scratch work** (my clone, the scratch copies, the listings and the
  outputs) is in the session scratchpad.
- **Original tree manifest:** exit 0 at the start and at the end.
