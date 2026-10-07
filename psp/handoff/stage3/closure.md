# Stage 3 closure: open advisories before G3 R1

Closer: Stage 3 closer (designer/implementer role, text and tooling only),
2026-10-07. Open list: `gates/LOG.md:375-377` (G2 attempt 2, "open:"). This
file is the closer's record; **an item counts as closed only when the closure
reviewer confirms it** (WORKFLOW G3 R1). G3 R8 is the human operator's and is
not touched here.

## What changed, and what did not

- **Design text:** `design/DESIGN.md` section 18 (lines 2908-3098), appended;
  sections 0-17 unchanged, section 18 takes precedence where it names a
  replaced sentence. `design/RUNBOOK.md` unchanged (`cmp` with `RUNBOOK.r7.md`).
- **Implementation record:** `impl/IMPLEMENTATION.md` section 10 "Stage 3
  closure" (lines 932-1011), appended.
- **Tooling:** decoder (`work/decoder`) and `pscol` host tests
  (`work/pscol/test`), committed on `stage2-trace` as `16d3bc28` (import as
  delivered), `145cdb73` (decoder), `23b0c625` (pscol tests), `0b5ba13e`
  (decoder test), author `Stage 3 closer (Claude agent)`.
- **Measurement:** `stage3/measure/` (own interpreter; `SUMMARY.txt`).
- **Diff of everything:** `stage3/closure.diff`.
- **Not changed:** kernel code, initramfs, `pscol` source and binary, the
  package. Evidence (`stage3/logs/closer-prestate.log`,
  `closer-poststate.log`, `pinned-rebuild-identity.log`):
  - `deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin` sha256
    `4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8`
    before and after; package `SHA256SUMS` and `BUILD/SHA256SUMS` OK;
  - `git diff --name-only 48dcc1b9..HEAD`: only `psc-tools/…`; the diff
    outside `psc-tools` is empty;
  - the final HEAD `0b5ba13e` rebuilt with the release identity gives
    byte-identical `vmlinux`, `vmlinux.bin`, `vmlinux-0.22.bin` (`4f9b69dc…`,
    also equal to the deploy file) and `System.map`;
  - `pscol` bFLT `7d7a5d78…` and `pscol.c` `1e89ac0a…` unchanged;
  - original tree manifest exit 0 at start and end.
- **No item needs a kernel, pscol or package change.** No blocking G1 or G2
  item is touched: section 18 restates estimates and adds decoder outputs; D10
  still holds (0 instructions in S5..S20, 105 = 105; the added time per
  command, 2.5 µs, is stated).

## One row per advisory

| Id | Wording (source) | Closed (closer's claim) | How | file:line |
|---|---|---|---|---|
| **G2 N1** | "Measured costs exceed the design's estimates (OD-7) … every tick +48 (≈ 16), a tick finding the thread in a command +208 (≈ +33), whole watchdog tick +922 ≈ 4.2 µs, straddle +1,104 ≈ 5.0 µs (2-4 µs), panel paint ≈ 1.03 ms (0.2-1 ms) … *Closes it:* … the designer restates them as text … or the human accepts them" (`gates/G2-attempt2-review.md:556-583`) | yes | Independent re-measurement from the released image (own interpreter) confirms the figures (WD +925 vs +922) and finds more above-estimate rows (scheduler hooks 109/136/203, preempted 150/144/190, per poll ≈ 1,710). DESIGN 18.1 restates every row with "supersedes 5.4, 7.1, 7.3, 11.1 R6, R13"; 18.2 re-derives 7.3 (start shifts ≈ 2.5 / 5.1 µs, δ/T ≤ 0.13 % for spread phases, density otherwise) and R6 (≈ 5 µs). The gate-log entry that N1 also suggests is the orchestrator's to append; the restated figures remain estimates (1 IPC, no cache: UNVERIFIED), so the human may treat the 7.3/R6 thresholds as a residual at R8 | `design/DESIGN.md:2927-2986`; `stage3/measure/SUMMARY.txt:1-43`; `impl/IMPLEMENTATION.md:974` |
| **G2 N2** | "G1-ruling advisories still open (OD-8): K1, K3, K5, K6, K8, K7; A-2, A-3, A-5, A-6 … *Closes it:* … the designer applies the text edits (K5/K6/K8 would then need decoder code and a G2 re-check of that code)" (`gates/G2-attempt2-review.md:585-597`) | yes | Text edits in DESIGN 18.3-18.4; K5, K6, K8 as decoder code with tests (DESIGN 18.5; decoder `145cdb73`); the closure reviewer is the re-check of that code. Each sub-item has its own row below | `design/DESIGN.md:2988-3084`; `work/decoder/pscdec_analysis.py:1619-1787` |
| **G2 N3** | "The H4/WB evidence lines print the raw `nwords` … *Closes it:* print `7\|8` whenever `nw7or8` … in those three format strings, and add the case to the `NwordsSevenOrEight` test" (`gates/G2-attempt2-review.md:599-610`) | yes | `nwtext()` prints `7\|8` for a flagged record in the WT listing, the H4 step line (Nop and thread) and the WB line. Test: an H4 stream whose straddling Nop reply is 7 words (`synth.py nop7`) prints "nwords 7\|8" in both lines (class `Stage3Closure`, end to end), and `NwordsSevenOrEight.test_evidence_text` checks the text on the K9 vectors | `work/decoder/pscdec_analysis.py:31`, `:1307`, `:1337-1338`, `:1362`; `work/decoder/test/run_tests.py:705-714`, `:782-807` |
| **Verifier 1** | "`test/run.sh krn <banner> <build_id>` does not pass the packaged banner … *To close it:* forward `"$@"` in `run.sh`, and have `checks.sh` run the packaged form" (`gates/G2-attempt2-verify.md:512-527`) | yes | `run.sh` forwards every argument (`"${1:-all}" "${2:-20}" "${@:3}"`) and refuses `krn <banner>` alone; `sim.c`: with no banner, `krn` and `all` also run the packaged-banner cases against the package's BUILD, so `checks.sh`'s unchanged `./pscol_test krn` call yields four KRN rows. `checks.sh` itself was not edited: it is outside `pscol/test` and it rebuilds the delivered bFLT in place, so it must not be run while the release is frozen; `CHECKS.txt` stays the G2-attempt-2 record | `work/pscol/test/run.sh:16-20`; `work/pscol/test/sim.c:1597-1633`, `:1738-1753`; `stage3/logs/pscol-run-krn.log`, `pscol-run-all-20.log` |
| **Verifier 2** | "pspboot loading the 1,767,264-B image is UNVERIFIED (OD-9 / R20) … *To close it:* a boot on the device" (`gates/G2-attempt2-verify.md:528-531`) | **no** (not this agent's item) | Handled by the separate Stage 3 R20 agent; pointer only: `handoff/stage3/r20/REPORT.md`. DESIGN 11.1 R20 unchanged; growth +44,036 B / +37,312 B (IMPLEMENTATION 1.4). needs_kernel_change: not known here (R20 report decides) | `design/DESIGN.md:3094`; `stage3/r20/REPORT.md` (separate agent) |
| **Verifier 3** | "Release identity is per-build … G3 R3 must use `4f9b69dc…` … the decoder must use the packaged `BUILD/` … *To close it:* G3 records the packaged checksum" (`gates/G2-attempt2-verify.md:532-538`) | yes | The packaged checksum is already in the gate log (`gates/LOG.md:353-355`); DESIGN 18.4 states the identity rule; the decoder now refuses any BUILD whose `IMAGE.sha256` is not that image or whose `SHA256SUMS` fails (pinned `RELEASE_IMAGE_SHA256`). The RUNBOOK A2 checksum line is the Stage 3 packager's (RUNBOOK.md:168) | `design/DESIGN.md:3022-3047`; `work/decoder/pscdec_analysis.py:64`; `work/decoder/pscdec.py:207-249`, `:293` |
| **Verifier 4** | "Outside-window costs (OD-7) were not re-measured by me … *To close it:* a G2 reviewer or G1 text ruling on OD-7" (`gates/G2-attempt2-verify.md:539-545`) | yes | The G2 reviewer ruled OD-7 non-blocking (N1); re-measured now from the released `vmlinux` with an interpreter independent of `pathcount.py`; DESIGN 18.1 is the text | `stage3/measure/README`, `SUMMARY.txt`; `design/DESIGN.md:2927-2958` |
| **A-1** | "component counts … entry ≈ 74 not ≈ 60; hand-off ≈ 94 not ≈ 85; `psc_sc_exit` P path ≈ 190 incl. `psc_dcount`, not ≈ 250-300 … *Close it:* give per-path counts with the path assumptions stated" (`gates/G1-ruling1-review.md:417-424`) | yes | Per-path counts with the path stated (0x08/0x33 valid reply, IE 1, no `lc`/LED/`pre` match, no new maximum): entry +75; hand-off 62 + `psc_xfer_out` 32; `psc_sc_exit` 167-170; `psc_fill_sc` 111; `memset` 44; `memcpy` 29; `psc_dcount` 30; totals +557/+560 | `design/DESIGN.md:2939`; `stage3/measure/SUMMARY.txt:5-21` |
| **A-2** | "stack figure and citation … ≈ 280 B is conservative … `thread_info.h:65-66` should be `:66-67`" (`gates/G1-ruling1-review.md:426-430`) | yes | Measured +216 B (Nop path), +208 B (thread), T2d 664 B; citation corrected (checked in the original tree) | `design/DESIGN.md:2949`, `:3016-3020`; `build/linux/include/asm-mips/thread_info.h:66-67`, `:82` |
| **A-3** | "The changed delay slot belongs to the first-iteration −3 exit … the full-budget −3 … is unchanged … the text names the wrong exit" (`gates/G1-ruling1-review.md:433-441`) | yes | 7.2(b) wording replaced; release `880ceff4..880cf000` and `880cf018/1c` verified in the listing | `design/DESIGN.md:3002-3008` |
| **A-4** | "10.1 names `work/out/20261006T021722Z` … Stage 2 should assemble one BUILD directory for the packaged image" (`gates/G1-ruling1-review.md:443-450`) | yes | One BUILD directory exists since G2 attempt 2 (`mkmaps.py`, I-7; `deploy/uClinux_TRACE/BUILD`, `SHA256SUMS` OK); 10.1's example replaced by it | `design/DESIGN.md:3035-3047`; `impl/IMPLEMENTATION.md:665` |
| **A-5** | "'the loop leaves the same state …' is true of the generated code, not of C semantics … Optionally, the decoder could print 'ambiguity live' whenever flagged records fall in a classification window" (`gates/G1-ruling1-review.md:452-458`) | yes | Wording: DESIGN 18.3 (with K1). Optional part implemented: per onset candidate and for the classification window | `design/DESIGN.md:2990-3001`; `work/decoder/pscdec_analysis.py:1619`; `work/decoder/pscdec.py:516`, `:587` |
| **A-6** | "The summary omits 'and after the path's last MMIO access' from the delay-slot allowance" (`gates/G1-ruling1-review.md:460-462`) | yes | Summary 1 wording fixed by 18.3 | `design/DESIGN.md:3009-3011` |
| **K1** | "1.2 and 2.1 A4: 'exact for 0 to 7' → 'exact for 0 to 6 and 8. Every recorded 7 is flagged …' The identity … is a property of the compiled loop … not of `syscon.c:201-217`" (`gates/G1-ruling1-redteam.md:90`) | yes | Replacement text in 18.3, also covering the §17 R-1 row; consistent with the executed table (IMPLEMENTATION 9.2.5) | `design/DESIGN.md:2990-3001` |
| **K3** | "1.7 and 10.1: 'differs between any two builds' → 'differs between builds made with the default identity' … The decoder also requires `BUILD/SHA256SUMS`' `vmlinux-0.22.bin` hash to equal the image hash in the gate log (G3 R3). Replace the attempt-1 example directory" (`gates/G1-ruling1-redteam.md:92`) | yes | Text in 18.4; decoder enforces the image hash (refuses the EPC analysis otherwise; `--expect-image` only for tests, printed). Test: the packaged BUILD passes; an identity-pinned BUILD of another image is refused although `build_id` matches; a tampered BUILD file is refused; the default refuses a synthetic BUILD | `design/DESIGN.md:3022-3047`; `work/decoder/pscdec.py:207-249`; `work/decoder/test/run_tests.py:809-855` |
| K5 (in N2) | "10.7 steps 6 and 8: print the recorded 0x33→0x08 gap distribution … its baseline equivalent … the MMIO-latency bound from the shortest command … The no-death inference names the gap as 'the one masking direction'" (`gates/G1-ruling1-redteam.md:94`) | yes | Decoder prints g min/p1/median, m upper bound (exact path model I, N of the release image), the S20→S13 gap with and without the instrumentation for m ∈ [0, m_ub], whether 5 µs lies between; step 8 names it | `design/DESIGN.md:3053-3064`; `work/decoder/pscdec_analysis.py:1630-1703`, `:1609` |
| K6 (in N2) | "7.3 bullet 1: state the bound as δ × (largest start-phase density) … 10.7 step 6: print the number of thread windows ending within δ … and those starting within δ after one" (`gates/G1-ruling1-redteam.md:95`) | yes | 18.2 restates the bound; the decoder counts windows starting/ending within δ after (and before) a tick edge and a watchdog edge, δ from the measured shifts | `design/DESIGN.md:2962-2972`, `:3065-3069`; `work/decoder/pscdec_analysis.py:1705-1753` |
| K7 (in N2) | "4.2 and 5.3: text 51,904 → 51,968 … `mm/nommu.c:744` → `:745`, `thread_info.h:65-66` → `:66-67`" (`gates/G1-ruling1-redteam.md:96`) | yes | Corrected in 18.3 (the red team's `binfmt_flat.c:459` is `:458` in the tree); attempt-2 figure 183,040 B added | `design/DESIGN.md:3012-3018` |
| K8 (in N2) | "10.7 step 6: from each W record's `sp`, print the stack headroom at the Nop … and its minimum over the run. Flag anything below 1 KB" (`gates/G1-ruling1-redteam.md:97`) | yes | Decoder prints it for kernel-mode interruptions (`sp` − stack base − 52, and minus the measured 520 B Nop path), flags < 1 KB; user-mode interruptions run the Nop on the kernel stack top | `design/DESIGN.md:3070-3074`; `work/decoder/pscdec_analysis.py:1755-1787` |

Not in the open list (implemented at G2 attempt 2, `impl/IMPLEMENTATION.md:745-751`):
K2 (D-24), K4 (D-23), K9 (vectors and the 9.2.5 table).

## Tests run for this closure

| What | Result | Log |
|---|---|---|
| Decoder `python3 test/run_tests.py` | 44 tests OK (37 earlier + 6 `Stage3Closure` + `NwordsSevenOrEight.test_evidence_text`); `check_format.py` OK | `stage3/logs/decoder-tests.log` (= `work/decoder/TESTS.txt`) |
| `pscol` host tests `test/run.sh all 20` | RESULT PASS (0 failing cases), four KRN rows | `stage3/logs/pscol-run-all-20.log` |
| `run.sh krn` with and without arguments; `krn <banner>` alone | 4/4 PASS both ways; refused with rc 2 | `stage3/logs/pscol-run-krn.log` |
| ASan/UBSan build of the host tests, KRN | build 0 warnings; PASS, no sanitizer report | `stage3/logs/pscol-asan-build.log`, `pscol-asan-krn.log` |
| Re-measurement | as 18.1 | `stage3/measure/measure-output.json`, `SUMMARY.txt` |
| Identity-pinned rebuild of the final HEAD `0b5ba13e` | byte-identical to the release | `stage3/logs/pinned-rebuild-identity.log` |

## For the human (not decided here)

- R20 (verifier 2) is the separate R20 report's.
- The restated perturbation figures (18.1-18.2) are executed-instruction
  counts at 1 IPC without caches (UNVERIFIED); the run measures the real
  ones. The R6 level-sensitive-G4L threshold is now ≈ 5 µs and the 0x08
  start shift ≈ 5.1 µs; the G2 reviewer named N1 as the item to put to the
  human if these are read as ruled bounds rather than estimates.
