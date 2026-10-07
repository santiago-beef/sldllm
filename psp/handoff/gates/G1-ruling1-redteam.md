# Gate G1, amendment ruling after G2 attempt 1, attempt 1: red team report

Artifact under review: `design/DESIGN.md` revision 7, the G1 ruling text, with
`design/g1ruling.diff` (against the frozen `design/DESIGN.r7.md`) and the
designer's ruling table, DESIGN section 17 (DESIGN:2877-2906). `RUNBOOK.md` is
unchanged (byte-identical to `RUNBOOK.r7.md`, checked with `diff -q`).
Role: G1 red team for the amendment ruling, attempt 1. Fresh context. I did not
write the design, the implementation or any earlier gate report.
Date: 2026-10-06.

**Scope (limited, as the brief sets it).** I re-ran every earlier red-team
scenario that reads `nwords`, the words-received count, the stale-frame or
short-frame shapes (UL3, H5, H8, N2b, H6), the perturbation argument (OE3,
TE4, 7.3), or the collector's memory or image size, against the amended text,
keeping the ids. I added eight new scenarios aimed at R-1, R-3, R-4 and R-5.
Everything else is outside this ruling and keeps its attempt-7 verdict.

Inputs read in full before any analysis: `DOSSIER.md` (section 9 taken as
superseding; 9.6 and 9.8 latest), `WORKFLOW.md` (gates G1 and G2, Amendment
A1), `design/DESIGN.md`, `design/RUNBOOK.md`, `recon/build.md`,
`recon/syscon.md`, `gates/LOG.md`, `impl/IMPLEMENTATION.md` (section 0,
OD-1..OD-6), `gates/G2-attempt1-review.md`, `gates/G2-attempt1-verify.md`,
`design/g1ruling.diff`, and the G1 red-team reports of attempts 1-7 for the
scenario texts.

Method:
- I applied the diff check myself: `diff -u DESIGN.r7.md DESIGN.md` equals
  `g1ruling.diff` apart from its two header lines, so the diff is the whole
  change.
- Source was only read. Kernel paths are relative to
  `/home/ubuntu/psp/build/linux` (the original tree). Where I cite the Stage 2
  code, the path starts with `work/linux` (branch `stage2-trace`, HEAD
  `c135ecdd`, unchanged by me).
- I disassembled the **baseline** build `work/out/20260927T204657Z/vmlinux` in
  the container with the whole of `/home/ubuntu/psp` mounted read-only, to
  count the baseline G3-low gap (EX1) and to check the receive-loop exit state
  (NW1). I also used the verifier's baseline listing
  `work/verify-g2-attempt1/Syscon_cmd.baseline-20260927T204657Z.dis`.
- I computed the CRC-32 of the banner directly from the packaged
  `work/out/20261006T021722Z/vmlinux.bin` (KR1).
- "DESIGN:n" is a line of DESIGN.md as it stands today. "base:+n" is a line of
  the verifier's baseline `Syscon_cmd` listing.
- Anything the source cannot settle is marked **UNVERIFIED**.
- After the work: `sha256sum -c --quiet gates/baseline-tree.sha256` in
  `build/linux` printed nothing, exit 0; `git -C work/linux status --porcelain`
  printed nothing (HEAD `c135ecdd`). I wrote only this file and scratch files.

---

## Verdict: PASS

**No scenario is BLIND, and no scenario is AMBIGUOUS** (27 scenarios: 19
re-run with their old ids, 8 new).

- **R-1 (`nwords` "7 or 8").** I found **no pair of matrix rows (H0-H10, N1-N11,
  N2b, WB, LEDSPLIT) that the lost bit separates.** The reason is structural:
  an 8th word of `0xFFFF` leaves all 16 `rx` bytes identical to the prefill, so
  every rule that decides on bytes decides the same way (I checked every
  `nwords` reader, section 2 and NW1-NW3). Two finer questions do lose their
  `nwords` evidence:
  - whether a P6 thread popped an empty FIFO at j = 7 (NW1); the W record's
    exact EPC and `v0` still answer it;
  - whether a long frame was cut one word short or arrived whole with an
    all-ones tail (NW2); this stays open in the records, but it is a mechanism
    inside H5 (and inside the declared H8 blind spot), not a choice between
    hypotheses.
- **R-3 (measured costs).** The re-derived figures are right, and the 7.3
  argument holds. Two refinements are worth adding as text (EX1, EX2):
  - the added 2.1-3 µs roughly **triples the instruction part of the baseline
    0x33→0x08 G3-low gap** (about 255 instructions in the baseline, section
    1.4), so whether the gap crosses the commented 5 µs wait depends on the
    MMIO latency (UNVERIFIED);
  - the δ/T bound holds only for spread phases.
  Both effects are measurable from the run's own records.
- **R-4 (`build_id`).** The definition is sound and I reproduced the value
  (`0x9b3c599e`, from the image bytes). One sentence is false: "the value
  differs between any two builds". `build.sh` can pin the banner (KR1). There
  is also one decoder behaviour to settle: what happens if word 2 changes in
  the middle of a run (KR2).
- **R-5 (memory, image).** The figures are right, except one addend: text is
  51,968 B, not 51,904 B. The no-allocation-after-boot property (IF2) and the
  guards (OE4) still hold. The larger block is an order-6 allocation made at
  boot. If it fails, the run aborts and is not spent (MEM1).

Corrections recommended before G2 attempt 2. None is blocking, and none changes
a ruling:

| # | Correction | Why |
|---|---|---|
| **K1** (NW1, NW3) | 1.2 and 2.1 A4: "exact for 0 to 7" → "exact for 0 to 6 and 8. **Every recorded 7 is flagged**, because a 7-word reply leaves `rx[14..15]` at the prefill. The identity of the two exit states is a property of the **compiled** loop (base:+148..+167; G2 review 4.2), not of `syscon.c:201-217`, where `i` and `ptr` differ." | The text implies some 7s are exact; none are. A future compiler output could change the identity. |
| **K2** (NW1) | 10.6: the EPC map labels, inside S18, the instructions **after the status load and up to the data load** (baseline `880cf068..880cf078`). The decoder names "P6, empty-FIFO pop" from `epc`/`lc_epc` and `v0`. Add a Stage 3 vector: a Nop at every instruction of the 8th iteration, with an empty pop returning `0xFFFF`. | Since R-1, nothing but the EPC separates a clean P6 stop at j = 7 from an empty pop. The P record and the W counter register `t0` are both identical (16) in the two cases. |
| **K3** (KR1) | 1.7 and 10.1: replace "differs between any two builds" with "differs between builds made with the default identity". The packaged build must be made without `KBUILD_BUILD_TIMESTAMP`, `KBUILD_BUILD_VERSION`, `BUILD_HOSTNAME` or `REPRODUCE_BASELINE` (its log records them, `build.sh:80`). The decoder also requires `BUILD/SHA256SUMS`' `vmlinux-0.22.bin` hash to equal the image hash in the gate log (G3 R3). Replace the attempt-1 example directory in 10.1 with "the packaged build's directory, as recorded at G3 R3". | `build.sh:34-41`, `:62-69` and `:97-98` let two different commits carry the same banner, and so the same `build_id`. The attempt-1 example goes stale at G2 attempt 2, because a new `pscol` changes the initramfs and with it the banner. |
| **K4** (KR2) | 10.1: the build check uses the word 2 of the run's **first** stats block (the value KRN verified). A later change of word 2 is reported as `instrumentation-suspect` from the first STATS chunk that shows it, and the EPC analysis is refused only for records after it. | `psc_k.build_id` is not one of the guarded words (`work/linux/arch/mips/psp/psc.c:44-47`), and it is copied into every snapshot (`:1078`). As written, a stray store at minute 20 would refuse the EPC analysis for an onset at minute 5. |
| **K5** (EX1) | 10.7 steps 6 and 8: print the recorded 0x33→0x08 gap distribution (minimum, 1st percentile, median) and its baseline equivalent, i.e. recorded minus `p_rec_cost` minus the wrapper entry. Give the MMIO-latency bound from the shortest command (≤ (minimum `c_out − c_in` − its instruction time) / 23). The no-death inference names the gap as "the one masking direction" with these numbers. | 7.3 calls this the one way the instrumentation could hide a failure, but step 8, the pre-registered no-death text, does not mention it. |
| **K6** (EX2) | 7.3 bullet 1: state the bound as δ × (largest start-phase density), which is δ/T only for spread phases. 10.7 step 6: print the number of thread windows ending within δ = 3.4 µs before a tick edge, and those starting within δ after one. | The thread wakes on a tick, so its windows are not spread across the tick. The data shows the true density, but nothing prints it. |
| **K7** (R-5) | 4.2 and 5.3: text 51,904 → **51,968** (`text_len = data_start` includes the 64-byte header, `fs/binfmt_flat.c:459`; flthdr Data Start 0xcb00). The sum 183,968 is right; 51,904 + 132,000 is 183,904. Also `mm/nommu.c:744` → `:745`, and `thread_info.h:65-66` → `:66-67`. | Arithmetic and citation nits only. The 256 KB block is unaffected. |
| **K8** (TE4) | 10.7 step 6: from each W record's `sp`, print the stack headroom at the Nop, `sp − (sp & ~8191) − sizeof(thread_info)`, and its minimum over the run. Flag anything below 1 KB. | This turns the "worst-case depth UNVERIFIED" of 5.3 into a figure measured for every context the Nop actually interrupted. |
| **K9** (NW1, KR1, NW3) | 8.5: add vectors for `nw7or8` (7 words; 8 words ending `0xFFFF`; 8 words not ending `0xFFFF`), for KRN (the packaged `banner.txt` bytes against word 2, and a 1-byte change → red), and for the decoder's build check (the verifier's rebuild is refused; an identity-pinned rebuild of another commit is refused by the image hash of K3). Add to G2: re-derive the loop-exit-to-`nwords` table (0-8 words, −3/−4, retry) from objdump whenever `syscon.c`, `psc.c` or the flags change. | The ruling added rules but no tests. These are test text, not mechanisms. |

### In plain words

- **What R-1 gives up, and why it costs almost nothing.** Each syscon reply is
  read 16 bits at a time, up to 8 words, into a buffer that was first filled
  with `0xFF` bytes. The amended design can no longer tell "7 words arrived" from
  "8 words arrived and the 8th was `0xFFFF`". In both cases the buffer holds
  exactly the same 16 bytes. Every rule that decides which hypothesis happened
  looks at those bytes, so every rule gives the same answer either way. I
  checked each rule that reads the word count, and none changes.
- **The two places where it does cost something.** Both are finer than the
  hypothesis list.
  - (1) The watchdog interrupts the thread just as it is about to read the
    8th word. The thread may then read an empty FIFO. Before R-1 the word
    count showed this. Now only the exact interrupted instruction shows it,
    and the records keep that instruction. So the decoder must be taught to
    name it (K2).
  - (2) A long, broken reply may have been cut one word short, or may have
    arrived whole with an all-ones last word. The records cannot tell these
    apart, but both are the same hypothesis (H5), and the bytes the driver
    saw are identical.
- **What R-3 changes.** The recording code after each command takes about
  2-2.5 µs instead of the 0.6 µs first estimated. It still runs entirely
  outside the time the syscon link is busy, so it cannot create or remove a
  watchdog collision. Two things do move slightly:
  - where in the tick the second command starts;
  - how long the request line stays low between the two commands of a poll.

  I counted that gap in the original kernel: about 255 instructions plus 9
  slow hardware accesses. The instrumentation roughly triples the instruction
  part. If the syscon needs the line low for at least 5 µs, which a
  commented-out wait in the code hints at, the instrumentation might push the
  gap over that limit and hide a failure. The design already says this. I ask
  that the decoder print the numbers (K5).
- **What R-4 changes.** The kernel stamps its stats with a checksum of its own
  version banner, and the collector checks it at boot. That check is sound.
  The design's claim that every build has a different banner is not quite
  true, because the build script can pin the banner. So the analyst's tool
  should also check the image hash (K3).
- **What R-5 changes.** The collector needs two 256 KB blocks instead of two
  128 KB blocks, both taken at boot. If the kernel ever refused one, the
  self-test would fail and the run would be aborted, not lost.

---

## Summary table

"Re-run" means re-traced against the amended text. "Prior" is the latest
ruling (attempt 7, or the last attempt that ruled the id).

| ID | Group | Scenario | Reads | Prior | This ruling |
|---|---|---|---|---|---|
| UL1 | unlisted-shape | LED write-back of bit 4 during a suspension at S14 | `nwords = 0` (−4 sentinel) | DIAGNOSABLE | DIAGNOSABLE |
| UL2 | unlisted-shape | One foreign frame toggles mouse mode off (N10) | `nwords ≥ 1` | DIAGNOSABLE | DIAGNOSABLE |
| UL3 | unlisted-shape | Link one reply behind (N2b) | stale frame; template `nwords` | DIAGNOSABLE | DIAGNOSABLE |
| UL6 | unlisted-shape | The Nop breaks the link with no thread command in flight (WB) | the Nop's own `nwords` | DIAGNOSABLE | DIAGNOSABLE |
| UL7 | unlisted-shape | Two-stage H4 ("both results valid") | validity against the template | DIAGNOSABLE | DIAGNOSABLE |
| TE1 | timing-edge | Death at 5 s, 17 s, 36 s; no template, code fallback | "exact length from `rx[1]`" | DIAGNOSABLE | DIAGNOSABLE |
| TE2 | timing-edge | Nop on a suspended thread; P6 cross-check | "−2 with `nwords` = j" | DIAGNOSABLE | DIAGNOSABLE (see NW1) |
| OE1 | observer-effect | MS driver hang; panel the only later record | panel `nwords` | DIAGNOSABLE | DIAGNOSABLE |
| H5 | state row | Persistent −2 / −5, short or shifted frames | short frame | (matrix) | DIAGNOSABLE (see NW2) |
| H8 | flag row | Controller state change; template departures | template `nwords` | (matrix) | DIAGNOSABLE |
| N2b | state row | Reply lag (A2 UL3) | template of `cmd` n−1 | (matrix) | DIAGNOSABLE |
| H6 | state row | Valid but stale frames | none (bytes only) | (matrix) | DIAGNOSABLE |
| OE3 | observer-effect | Collector load sets the H4 start-delay exposure | 7.3 | DIAGNOSABLE | DIAGNOSABLE |
| TE4 | timing-edge | Slow Nop, nested tick, preemption at the outer return, H10 | Nop path +2-4 µs, +280 B stack | DIAGNOSABLE | DIAGNOSABLE (K8) |
| 7.3 | observer-effect | The perturbation argument itself, re-derived | R-3 counts | (design) | DIAGNOSABLE (K5, K6) |
| A1-OE3 | observer-effect | Who held the CPU while the thread was preempted mid-command | 7.3 bullet 4 | DIAGNOSABLE | DIAGNOSABLE |
| OE6 | observer-effect | Stall panel paints; 328 B panel frame | R-3 stack | DIAGNOSABLE | DIAGNOSABLE |
| IF2 | instrumentation-fault | Worker killed at minute 13-14; takeover without allocation | block size | DIAGNOSABLE | DIAGNOSABLE |
| OE4 | observer-effect | Kernel-privileged `pscol`, stray store; guards | block layout | DIAGNOSABLE | DIAGNOSABLE |
| **NW1** | timing-edge (new; R-1) | P6 at j = 7: a clean stop against an empty-FIFO pop that returns `0xFFFF` | – | – | **DIAGNOSABLE** (K2) |
| **NW2** | unlisted-shape (new; R-1) | Persistent −2 on 15/16-byte frames: cut one word short, or whole with an all-ones tail | – | – | **DIAGNOSABLE** (residual stated) |
| **NW3** | instrumentation-fault (new; R-1) | A rebuild moves the loop counter; the hand-off reads the wrong state | – | – | **DIAGNOSABLE** (K9) |
| **EX1** | observer-effect (new; R-3) | The 0x33→0x08 G3-low gap crosses a 5 µs syscon minimum because of the added exit code | – | – | **DIAGNOSABLE** (K5) |
| **EX2** | observer-effect (new; R-3) | The exit stretch moves the 0x08 window; P-point mix and straddle chance with concentrated phases | – | – | **DIAGNOSABLE** (K6) |
| **KR1** | instrumentation-fault (new; R-4) | `build_id` false red at boot, false accept of the wrong maps, false refusal | – | – | **DIAGNOSABLE** (K3, K9) |
| **KR2** | instrumentation-fault (new; R-4) | A stray store changes word 2 in the middle of the run; the decoder refuses the EPC analysis for the whole run | – | – | **DIAGNOSABLE** (K4) |
| **MEM1** | instrumentation-fault (new; R-5) | The order-6 boot allocation fails, or G2 attempt 2 grows `pscol` or the image | – | – | **DIAGNOSABLE** |

---

## 1. Facts the rulings rest on (verified by me)

### 1.1 The receive loop and `nwords`

| # | Fact | Evidence |
|---|---|---|
| F1 | `rx_buf` is pre-filled with `0xff` on **every** attempt, before S5. | `syscon.c:92-93` |
| F2 | The loop reads one 16-bit word per iteration while the status says "not empty", at most 8 words. In C, `i` and `ptr` differ at the two exits (14 against 16). | `syscon.c:201-217` (`:204-205` test and break, `:207` data read) |
| F3 | **In the compiled baseline loop** `t0` holds `i + 2` and `a3` holds `ptr + 2`. In the 8th iteration `t0 = 16`, so `slti t1` = 0. An empty FIFO exits at base:+153 (`beqz`, delay slot `a0 = t0 − 2`). After the 8th data read the `bnez t1` at base:+166 falls through. **Both exits reach S19 with `t0 = 16`, `a3 = rx_buf + 16`, `a0 = 14`.** | base:+148..+167; the release build is the same (G2 review 4.2) |
| F4 | The Stage 2 hand-off derives `nwords = (t0 − 2)/2` for `t0 < 16`. At `t0 = 16` it gives 7 if `rx[14..15] = ff ff`, else 8. | `work/linux/arch/mips/psp/psc.c:275-280` |
| F5 | **So every 7-word reception is recorded as 7 with `rx[14..15] = ff ff` (F1), and every recorded 7 is flagged.** The value 7 is never exact on its own; 0-6 and 8 are. | F1, F3, F4 |
| F6 | A read of an empty RX FIFO returns an UNKNOWN value. P6 "between its status test and its data read" pops it. | recon/syscon.md §4.1 (`0xbe580008`), §5.1 P6 |
| F7 | The W extension keeps registers 2..15, 24, 25 (so `v0` and `t0`) and the exact `epc`. `lc_*` keeps the same for a suspended thread. | DESIGN:115 (K14), DESIGN:265-271 |

### 1.2 `build_id`

| # | Fact | Evidence |
|---|---|---|
| B1 | `linux_banner` = "Linux version " UTS_RELEASE " (" BY "@" HOST ") (" COMPILER ") " UTS_VERSION "\n". | `init/version.c:37-39` |
| B2 | `/proc/version` prints `linux_proc_banner` with `utsname()` sysname, release and version, and these are the same compile-time strings. | `fs/proc/proc_misc.c:245-254`; `init/version.c:25-32`, `:41-44` |
| B3 | Release and version cannot be changed at run time: the sysctl entries are 0444, and there are no UTS namespaces and no binary sysctl. | `kernel/utsname_sysctl.c:87`, `:96`, `:105`; `.config:157`, `:169` |
| B4 | The kernel computes `psc_crc32(0, linux_banner, strlen(linux_banner))` once at init, and copies it into every stats snapshot. It is not a guarded word. | `work/linux/arch/mips/psp/psc.c:1221`, `:1078`, `:44-47` |
| B5 | The packaged image's banner is 102 bytes at `vmlinux.bin` offset 1,179,648. Its zlib CRC-32 is **`0x9b3c599e`**, equal to the CRC of `banner.txt` (`strings` + `grep -m1` adds the `\n` that `strings` drops). | my computation; `build.sh` "strings -a ... grep -m1" line; IMPLEMENTATION 1.2 |
| B6 | `build.sh` passes `KBUILD_BUILD_VERSION`, `KBUILD_BUILD_TIMESTAMP` and `BUILD_HOSTNAME` through, and `REPRODUCE_BASELINE=1` pins all three. With a pinned identity the banner is byte-identical (Recon C reproduced the 2026-09-22 image byte for byte this way). | `build.sh:34-41`, `:62-69`, `:97-98`, `:131`; recon/build.md:21, :127-130 |

### 1.3 The `pscol` allocation

| # | Fact | Evidence |
|---|---|---|
| M1 | Under `CONFIG_SONY_PSP` every bFLT is loaded RAM-style: one `do_mmap` of text + data + extra. The block is then remapped to the whole `ksize` slack. | `fs/binfmt_flat.c:471-472`, `:626-636` |
| M2 | `text_len = data_start` (it includes the 64-byte header); `MAX_SHARED_LIBS` is 0 without shared flat. For `pscol`: 0xcb00 + 2,896 + 112,720 + 16,384 = **183,968**. | `fs/binfmt_flat.c:459-462`, `:74-75`; `.config:224`; verifier flthdr output |
| M3 | `kmalloc` serves it from the 262,144-byte cache (no MMU), so one order-6 block. | `mm/nommu.c:745`; `include/linux/kmalloc_sizes.h:22-23`; `.config:179` |
| M4 | The stack sits at the **top** of the block (`end_brk = memp + ksize − stack_len`). About 78 KB of slack lies between the end of bss and the stack. | `fs/binfmt_flat.c:716-718` |
| M5 | A failed allocation prints "Unable to allocate RAM for process text/data" into the kernel log. | `fs/binfmt_flat.c:644` |

### 1.4 The baseline G3-low gap, counted (for EX1)

This is the path from the 0x33 command's S20 (base:+172, `sw s5,0(s0)`) to the
0x08 command's S13 (base:+114), cached and with no misses. The 0x33 reply
length is UNVERIFIED; I took `rx[1] = 3`.

| Segment | Instructions | MMIO before S13 |
|---|---|---|
| 0x33: S21-S23 and epilogue (base:+173..+198, +135..+145) | ≈ 44 | 0 |
| `pspSyscon_tx_dword` return (`880cf1b4..bc`) | 3 | 0 |
| thread, between `jal 880cf178` and `jal 880cf398` (`88114ae4..af8`) | ≈ 4 | 0 |
| `_pspSysconGetCtrl2` to its `jal` (`880cf398..3d0`) | 15 | 0 |
| `Syscon_cmd` prologue, TX checksum (2 bytes), prefill (base:+1..+55) | ≈ 145 | 0 |
| S5..S13 (base:+56..+114: S7 not set; TX loop, 2 words) | ≈ 44 | 9 (S5, S6, S7, S9, S10, 2 × (status, data), S12) |
| **Baseline total** | **≈ 255** | **9** |

So the baseline gap ≈ 1.15 µs + 9 m, where m is the uncached MMIO latency
(UNVERIFIED). The instrumentation adds ≈ 460-610 instructions plus the stage
stores (DESIGN:1594), which makes ≈ 715-885 instructions + 9 m. **The
instruction part grows about 2.8-3.5 times; the MMIO part is unchanged.**

| m (UNVERIFIED) | Baseline | Instrumented | 5 µs crossed? |
|---|---|---|---|
| 50 ns | ≈ 1.6 µs | ≈ 3.7-4.4 µs | no |
| 150 ns | ≈ 2.5 µs | ≈ 4.6-5.3 µs | sometimes |
| 300 ns | ≈ 3.9 µs | ≈ 5.9-6.7 µs | yes |

---

## 2. Re-run: scenarios that read `nwords`

The rule set I check against is DESIGN:2311-2344 ("`nwords` 7 or 8"), the
1.2 row (DESIGN:248), the 6 preamble (DESIGN:1640-1643) and the 10.3 flag
(DESIGN:2178-2181). In every case the question is whether a threshold or
comparison lies between 7 and 8, or whether a byte differs. By F1 and F3, no
byte differs.

**UL1. LED write-back of bit 4 during a suspension at S14. DIAGNOSABLE.**
- The trace reads `nwords` only as the −4 sentinel 0 (DESIGN:1648). The −4
  exit sets it to 0 explicitly (`psc.c:275`), and it is exact.
- `led_or`, `lc_epc`, `ms_delta` and `pre_*` are untouched by the ruling.

**UL2. One foreign frame toggles mouse mode off (N10). DIAGNOSABLE.**
- N10's "`ret = 0` with `nwords ≥ 1`" (DESIGN:1675) has no threshold between 7
  and 8.
- A Nop or 0x33 reply accepted as a foreign frame is ≤ 5 words, so its count
  is exact (F5).

**UL6. The Nop breaks the link with no thread command in flight (WB).
DIAGNOSABLE.**
- WB compares the Nop's own `ret`, `nwords`, `rx`, `ack_polls` and `drain`
  with the template (DESIGN:1678).
- A healthy Nop reply is short, so it is exact. A flagged Nop record is
  compared by set membership, and its 16 bytes decide.

**UL7. Two-stage H4. DIAGNOSABLE.**
- "Both results valid" decides on `ret` and `rx[2]` (DESIGN:2264-2268).
- Where the template's `nwords` enters, a flagged record matches if 7 or 8 is
  the template value. A frame that differs only in an 8th `0xFFFF` word is the
  same frame in every byte, so the benign or harmful verdict cannot flip.

**TE1. Early death; no template; code fallback. DIAGNOSABLE.**
- The fallback expects "for 0x08 ≥ 5 words, exact length from `rx[1]`"
  (DESIGN:2237-2238).
- The expected word count for `rx[1]` = c is ⌈(c + 1)/2⌉; this is 8 for c = 14
  or 15. A flagged record "matches" it. The case where a 7-word frame was cut
  from an 8-word one therefore passes the length test, but its bytes are what
  the cut frame would have been, and the checksum (`ret = −2`) still reports
  the frame bad. This is NW2's residual, and it does not change H1, H3, H5 or
  H9, which use absolute values.

**TE2. Nop on a suspended thread; P6 cross-check. DIAGNOSABLE.**
- "P6: −2 with `nwords` = j" (DESIGN:2276). For j ≤ 6 the check is as before,
  because those counts are exact (F5). An empty pop for word j + 1 ≤ 7 gives
  a count of j + 1, which is either exact or in a set that excludes j, so it
  is still caught.
- At j = 7 the design itself states the loss (DESIGN:2335-2339). NW1 shows
  that the case is still separable by the EPC.
- `lc_epc`/`lc_r` (K8) are unchanged.

**OE1. MS driver hang; panel photographs the only later record.
DIAGNOSABLE.**
- Panel line 4 shows `ret`, `nwords` and `rx[0..8]` (DESIGN:678), not
  `rx[14..15]`. So a photographed 7 reads "7 or 8" (DESIGN:2342-2344).
- That was already true of `rx[9..15]` before R-1: the panel never showed a
  long frame whole.
- OE1's subject, the driver hang with `preempt_count > 0`, does not read
  `nwords`.

## 3. Re-run: stale-frame and short-frame shapes (UL3, H5, H8, N2b, H6)

**UL3 / N2b. Link one reply behind. DIAGNOSABLE.**
- **Recorded.** P08 carries the 0x33's reply: `rx[2]` is the template's value
  for 0x33, `drain = 0`, and `nwords` is the 0x33 reply length (short, so
  exact). P33 and W carry GetCtrl2-shaped frames whose buttons follow the
  D-script one poll late.
- **Rule.** N2b compares command n's `rx[2]` with the template of command n−1's
  `cmd` across P + W + M (DESIGN:1667) and is tested before H6
  (DESIGN:2258). R-1 changes only the per-command `nwords` element of the
  template, which is now compared by set membership. Lagged replies are 2 or
  5 words, so the counts are exact.
- **Variant.** Suppose the lag concatenates replies, for example the Nop's 2
  words plus the 0x08's 5 words = 7. The P record says 7, flagged, and `rx`
  holds both frames. `rx[2]` is the first frame's, and that is what N2b reads.
  An 8th idle word would add no byte.

**H5. Persistent −2 / −5, short or shifted frames. DIAGNOSABLE.**
- The row decides on `ret`, `retries`, `rx[2] ∈ {0x80, 0x81}`, `rx[1] < 3`, a
  mismatch the decoder recomputes, or `rx[1] ≥ 16` (DESIGN:1652). It does not
  decide on `nwords` (DESIGN:2329-2331, confirmed).
- Short frames of ≤ 6 words keep an exact count, so "frame shorter than
  `rx[1]` says" remains visible for every frame up to 13 bytes.
- For 15- and 16-byte frames, "cut one word short" and "whole, with an
  all-ones tail" leave identical records: NW2.

**H8. Controller state change; template departures. DIAGNOSABLE.**
- The H8 flags compare `gpio_in`, `spi_*`, the drain rate, `drain_last`,
  `ack_polls`, the LED ORs and, through the template, `nwords`
  (DESIGN:1655, :2322-2326).
- A controller that adds or drops a word shows on the short frames (Nop 2
  words, 0x33 2 words, 0x08 5 words) with exact counts.
- The one case it cannot show is a word added or dropped only on 8-word
  frames. That falls inside the declared H8 blind spot ("a change there shows
  only as behaviour, 'H8 unresolved'", DESIGN:1655; R4 at DESIGN:2365).

**H6. Valid but stale frames. DIAGNOSABLE.**
- The row decides on `ret > 0`, a valid checksum, `rx[2]` = the template's
  value, `rx[3..8]` byte-identical through D1-D7, and the absence of a
  press-following GetCtrl2-shaped frame elsewhere (DESIGN:1653). No `nwords`.
- The Stage 3 vector "stale-frame sequence whose healthy `rx[2]` is not
  0x08" (DESIGN:2038) is unaffected.

## 4. Re-run: the perturbation argument (OE3, TE4, 7.3, A1-OE3, OE6)

### 7.3. The argument, re-derived with the measured counts. DIAGNOSABLE

| Claim (DESIGN) | My check | Holds? |
|---|---|---|
| 0 instructions in S5..S20 (7.2; G2 105 = 105) | Two independent window comparisons (G2 review 4.1, verify 5); renaming and the delay slot are within 7.2's test | yes; that Allegrex timing does not depend on register numbers is UNVERIFIED, as stated |
| Before S5 ≈ 60, after S20 ≈ 400-550 → 0.27 / 1.8-2.5 µs (DESIGN:1593) | 60/222 MHz = 0.27 µs; 400-550/222 = 1.80-2.48 µs | yes (1 IPC UNVERIFIED) |
| 0x08 window shifted ≈ 2.4-3.4 µs (DESIGN:1807) | 0.3-0.6 + 2.1-2.8 | yes |
| δ/T ≤ ≈ 0.09 % (DESIGN:1810-1811) | 3.4/4,000 = 0.085 % | yes, **for spread phases**. For a start-phase density f the bound is δ·sup f (EX2, K6) |
| G3-low gap +2.1-3 µs, "about half" the commented 5 µs (DESIGN:1831-1835) | +460-610 instructions + stage stores. Baseline ≈ 255 instructions + 9 MMIO (1.4) | yes. The relative change is about ×3 on the instruction part (EX1, K5) |
| Recorded gap = 0x33 `c_out` → 0x08 `c_in`, "all of the added gap but the ≈ 85 hand-off" (DESIGN:1836-1838) | `c_out` is taken first in `psc_sc_exit` (DESIGN:478-479); `rec_cost` = Count − `c_out` (DESIGN:487). The recorded gap includes `rec_cost`, the return path, the thread, GetCtrl2 and the wrapper before `c_in`. It excludes the hand-off with `psc_xfer_out` and S21-S23 before `c_out`, and the wrapper after `c_in`, the prologue, S1-S4 and S5-S12 | yes, approximately. The baseline equivalent is computable (K5) |
| Nop path +2-4 µs, 450-800 instructions UNVERIFIED, measured as `w_rec_cost_max` (DESIGN:1596) | ≥ 85 + 151 + W branch | stated as UNVERIFIED and measured |
| D10 ratio ≤ 10 % for commands ≥ 28 µs (DESIGN:1613-1614) | 2.8/28 = 10 % | yes (duration measured, HUD line 10) |
| "Neither creates an interleave nor removes one beyond …" (DESIGN:1842-1848) | Nothing is added where a Nop can land. Outside the window only phases move, and every phase is recorded | yes |

**Ruling: DIAGNOSABLE.** Recommendations: K5, K6.

### OE3. Collector load sets the H4 start-delay exposure. DIAGNOSABLE

- R-3 adds ≈ 5.5-7 µs of the thread's own CPU per poll (DESIGN:1595). That
  is not collector load: the collector's work and cadence are unchanged by
  the ruling.
- The lever 7.3 names (MS I/O and equal-priority tasks delaying the thread's
  start) is still measured per poll (`wk_delay`, `wk_wrk`, `wk_cls*`, `period`,
  `c_start`) and per command (`pre_*`).
- The no-death inference (DESIGN:2303-2309) is unchanged. EX1 asks it to name
  the gap.

### TE4. Slow Nop, nested tick, preemption at the outer return, H10. DIAGNOSABLE (K8)

- TE4's Nop is the −4 path (≥ 50 ms, recon §1.5). Against that, +2-4 µs of
  recording changes nothing.
- The nested tick 1250k+1 is ≡ 1 (mod 250), so T2d's panel (≡ 125) cannot
  nest into it.
- **Stack.** The Nop path is ≈ 280 B deeper (DESIGN:1557-1564). In TE4 it sits
  on the interrupted thread's stack together with a second exception frame
  and the softirq. The joypad thread's own depth is shallow (kernel thread →
  read_input → GetCtrl2 → wrapper → `Syscon_cmd`). The deepest realistic host
  is `pscol` inside `fsync` → vfat → `ms_psp`. The worst case is UNVERIFIED,
  as 5.3 says.
- Every W record keeps the interrupted `sp` and `pid` (K14), so the headroom
  at every Nop the run saw is computable from the data (K8).
- An overflow on this no-MMU kernel would corrupt `thread_info` silently. Its
  consequence would show as an oops in KMSG or a stopped task (H9, N4, N5
  symptoms) together with a W record whose `sp` is near the base. That is
  attributable, not silent, if K8 is printed.

### A1-OE3. Who held the CPU while the thread was preempted mid-command. DIAGNOSABLE

- K35's hooks are unchanged. 7.3's new bullet 5 cites `wk_delay` and
  `pre_tot` as the load-induced variation against which the 2-3 µs shift is
  small.
- Both are recorded per poll and per command, so the comparison is made on
  the run's own numbers.

### OE6. Stall panel paints. DIAGNOSABLE

- The 328 B panel frame runs only at T2d, ≡ 125 (mod 250), never on a
  watchdog tick (DESIGN:1562-1563). The G2 review checked the first firing at
  tick 125 and every 250 after (G2 review 2.3).
- So the panel frame and the deeper Nop path never share one interrupt. N1p
  and `lc_flags` b5 are unchanged.

## 5. Re-run: the collector's memory and the image size

### IF2. Worker killed at minute 13-14; takeover without allocation. DIAGNOSABLE

- The A1 BLIND cause was a large contiguous allocation late in the run.
- R-5 corrects the block to 256 KB, but the property is unchanged:
  supervisor and worker are one binary, so the supervisor's boot-time block
  has the worker's size (M1-M3), and the takeover runs the worker loop
  in-process with no `exec` (DESIGN:919-927).
- What a takeover still allocates is small slab objects (file descriptors,
  dentries and inodes for a fresh segment file), as before.
- RAM. 512 KB of process blocks against the r5 assumption of 256 KB moves the
  IF14 page-cache fill point by ≈ 256 KB ÷ ≈ 16 KB/s of written data ≈ 16 s.
  That is negligible against minute 28-33 (UNVERIFIED, as IF14 said).

### OE4. Kernel-privileged `pscol`, stray store; guards. DIAGNOSABLE

- The guards are unchanged (DESIGN:942-949).
- The measured layout puts the 16 KB stack at the top of the 256 KB block
  with ≈ 78 KB of unused slack below it (M4). A stack overrun therefore runs
  into slack, not into bss. The pre-filled high-water mark still reports it,
  and it can no longer silently corrupt the flush buffer. This improves
  OE4's position.
- G2 C8 now records "≤ 256 KB" (DESIGN:908). The current use leaves 78,176 B
  of margin before the next power of two.

---

## 6. New scenarios

### NW1 (timing-edge; R-1). P6 at j = 7: a clean stop against an empty-FIFO pop. DIAGNOSABLE (K2)

**Shape.** A lagged or concatenated 8-word reply is in the RX FIFO. The thread
has read 7 words. The watchdog tick 1250k lands in one of two places:

- **(A) Clean stop.** The tick lands before the 8th status load (baseline
  `880cf064`). The Nop pre-drains word 8. The thread re-executes the status
  load, finds the FIFO empty and exits with 7 words.
- **(B) Empty-FIFO pop.** The tick lands after the status load and before the
  data load (`880cf068..880cf078`). The Nop pre-drains word 8. The thread,
  holding a "not empty" status in `v0`, reads the data register of an
  **empty** FIFO (F6). If that returns `0xFFFF` (UNVERIFIED but plausible),
  the thread has "8 words".

(B) is a candidate for carried-over controller state, an underflow, which
recon §5.4 says permanence needs. So telling (A) from (B) matters for 9.6's
"what leaves input permanently dead".

**What the design records.**

| Record | (A) | (B) |
|---|---|---|
| P08 `ret` | −2 if `rx[1] ≥ 14` (prefill compared as the checksum) | same |
| P08 `rx[0..15]` | 7 words + `ff ff` | 7 words + `ff ff` (popped) |
| P08 `nwords` | 7, flagged {7, 8} | 7, flagged {7, 8} (true 8) |
| W `drain`, `drain_last` | 1, word 8 | 1, word 8 |
| W `r` `t0` | 16 | 16 (F3) |
| W `epc` (thread running) / `lc_epc` (suspended) | at or before the status load | after the status load, up to the data load |
| W `r` `v0` | not a fresh status | status with bit 2 set |

**What the decoder concludes.**
- The P6 cross-check (DESIGN:2276-2277) accepts both: j = 7 ∈ {7, 8} for
  (A), and "anything if between its status test and its data read" for (B).
- Before R-1, (B) with an exact 8 would have contradicted j = 7 whenever the
  EPC sub-step was not resolved. Now **only the EPC (and `v0`) separates
  them**. The decoder's map has S-step granularity (DESIGN:2206-2207), and
  G2 found its S16-S18 grammar broken (OD-4, G2 F3).
- The raw `epc`, `cause` (BD) and `r` are kept in every W record and printed
  in the ±30 s dump, so an analyst with the packaged `vmlinux` resolves it
  exactly. I did this above for the baseline layout: BD on the `beqz` means
  the status was already loaded, which is (B).

**Ruling: DIAGNOSABLE.** **Recommended (K2):** a sub-label inside S18 and an
automatic "P6, empty-FIFO pop" line, plus the Stage 3 vector (K9). Without
them the case is still decided, but by hand.

### NW2 (unlisted-shape; R-1, the brief's "only difference" case). Persistent −2 on 15/16-byte frames: cut short, or whole with an all-ones tail. DIAGNOSABLE (residual stated)

**Shape.** After onset every P08 carries a frame with `rx[1]` = 14 (15 bytes,
so 8 words are needed), `rx[14] = rx[15] = 0xff` and `ret = −2`. Two
mechanisms fit:

- **(i) Cut short.** The syscon, or the controller, delivers only 7 words. The
  checksum byte never arrives, and the prefill `ff` is compared as the
  checksum.
- **(ii) Whole frame, corrupt tail.** All 8 words arrive and the 8th is
  `0xFFFF`: a checksum byte of `0xff` that is wrong, for example because MISO
  is stuck high at the end of the frame.

**What the design records.** Identical P records: `ret`, all 16 bytes, `nwords`
7 flagged. I looked for any other field that separates them:
- the next command's `drain` is 0 in both, because the FIFO ends empty;
- `spi_*` and `gpio_in` are captured before the receive;
- the duration differs by one status/data MMIO pair, below the
  ACK-latency jitter (UNVERIFIED but likely);
- no W record is involved.

**This is the case the brief asks for: the lost bit is the only difference.**

**What the decoder concludes.** H5 (persistent −2, with a checksum mismatch
it recomputes; DESIGN:1652) in both cases. H8 flags "`nwords` off the
template" in both, because the template is 5. The triple (trigger, state, H8
flags) is identical, which is right, because:
- the bytes the driver saw are identical (F1), so input died the same way;
- both mechanisms are forms of H5's "checksum failures become permanent";
- the controller form of (i) is inside the declared H8 blind spot.

What is lost is the mechanism detail inside H5. With an exact count, 8 would
have shown "frame complete, tail corrupt"; 7 would still not have told syscon
truncation from controller truncation. Cross-evidence often settles it: the
same fault on the exact short frames (0x33, Nop) shows as 1 word instead of
2, or as a `ff` tail on a 2-word frame. It stays open only when the effect is
confined to 8-word frames.

**Ruling: DIAGNOSABLE.** S1 is met (H5, with the raw frames). §17 R-1's
written reason ("the one bit lost carries no byte of the frame") covers it,
and I agree with that reason. **Recommended:** the decoder prints, beside an
H5 classification whose post-onset frames are flagged with `rx[1] ≥ 14`,
"complete frame with an all-ones last word, or one word short: not
determinable from these records". It also lists the exact-count evidence from
the shorter frames of other commands.

### NW3 (instrumentation-fault; R-1). A rebuild moves the loop's exit state; the hand-off reads the wrong count. DIAGNOSABLE (K9)

**Shape.** §17 says the kernel needs no change for the ruling (DESIGN:2900-2906).
But G2 attempt 2 rebuilds the image for the new `pscol` (initramfs). A later
change to `syscon.c`, `psc.c` or the flags could change register allocation
so that `t0` no longer holds `i + 2` at S19 (F3, F4). The hand-off would then
compute a wrong `nwords` for **every** record.

**What the design records, and what catches it.**
- An under-count, for example 1 word recorded as 0, fails REC's "`nwords = 0`
  ⇒ `rx` all `ff`" (DESIGN:1962). That is red at the self-test, an abort.
- An over-count passes REC and POLL:NW0. H3's `nwords = 0` would then never
  match, and an E3 poll would land in H0 with raw `rx` all `ff`. Raw data
  survives, but the classification is wrong.
- Nothing in G2's checklist as amended requires re-deriving the exit-state
  table. 2.1 A4 names the G2-attempt-1 build only (DESIGN:476).

**Ruling: DIAGNOSABLE** (raw `rx` is kept, and the prefill makes the true
count recoverable by hand for frames whose tail is not `ff`). **Recommended
(K9):** G2 re-derives the table on every relevant rebuild. The decoder also
checks `rx[2·nwords..15]` = `ff` for unflagged records, which costs nothing
and catches any under-count.

### EX1 (observer-effect; R-3). The added exit code lengthens the 0x33→0x08 G3-low gap across a syscon minimum. DIAGNOSABLE (K5)

**Shape.** The commented `Syscon_wait(5)` after G3 falls (`syscon.c:95-97`,
`:142-144`) hints at a ≥ 5 µs minimum G3-low time (UNVERIFIED). Suppose that
in the baseline a poll whose gap is below the minimum makes the syscon miss
or misframe the 0x08 request, rarely (for example when the caches are hot),
and that a misframe is permanent. By 1.4 the baseline gap is ≈ 255
instructions + 9 MMIO. The instrumented gap is ≈ 715-885 instructions + 9
MMIO. For m around 150-300 ns, the instrumentation moves part or all of the
gap distribution above 5 µs. The run then shows **no death**, or fewer
deaths, for a reason the instrumentation created.

The Nop-side gaps hardly move:
- thread S20 → Nop S13 grows only by the Nop's wrapper entry, ≈ 0.27 µs. A
  Nop can land right after the thread's S20, so the minimum of that gap is
  set by the interrupt path;
- Nop S20 → resumed thread S13 grows by 2-4 µs, on top of the rest of the
  timer handler, which is already long (UNVERIFIED).

So this masking acts on the 0x33→0x08 pair, which is not Nop-aligned. A
gap-sensitive cause would not by itself explain 9.6's 5 s alignment; H4 still
leads.

**What the design records.**
- Per poll, P33 `c_out` and P08 `c_in` (the recorded gap).
- `p_rec_cost_last`/`max` (`rec_cost` = Count − `c_out`, DESIGN:487, :421).
- Every command's duration. The shortest one bounds m: `c_out − c_in` ≥ 23
  MMIO accesses plus the known instructions.
- The decoder prints "the G3-low gap" in REPORT.md (DESIGN:2290). 7.3 and R6
  state the masking direction (DESIGN:1831-1838, :2367).

**What the analyst can conclude.**
- The recorded gap is a lower bound on the instrumented gap.
- The baseline equivalent = recorded − `rec_cost` − wrapper entry, and the
  absolute value can be bounded with m.
- So for a no-death run the report can say how far the gap moved and whether
  it could have crossed a 5 µs minimum. That is S5's "know precisely how it
  might have".
- For a death run, the classification is unaffected.

**Ruling: DIAGNOSABLE.** **Recommended (K5):** print those numbers, and put
them in step 8's pre-registered no-death text. 7.3 calls this the one masking
direction, and step 8 is where a no-death run is concluded.

### EX2 (observer-effect / timing-edge; R-3). The exit stretch moves the 0x08 window; P-point mix and straddle chance with concentrated phases. DIAGNOSABLE (K6)

**Shape.** Take a Nop that lands τ µs after the 0x33's S20.
- In the baseline the 0x08's S5 comes ≈ 0.95 µs + a few MMIO later and S13
  ≈ 2-4 µs later. A Nop at τ ≈ 1-4 µs lands at **P1-P3 of the 0x08**: a
  misframe or a foreign reply is possible (recon §5.1).
- In the instrumented kernel the same τ lands in the 0x33's EXIT/REC code or
  the 0x08's wrapper entry, which is **P0**, benign by code (DESIGN:2217).
- The 0x08's P1-P3 now begin ≈ 2.4-3.4 µs later.

A second point. The thread wakes on a tick (DESIGN:1802-1803), so its windows
start at a nearly fixed phase after the tick edge, not at a spread one. A
window straddles the **next** edge only after a long start delay. The change
in straddle probability is then δ × f(T − L), where f is the density of the
start phase near the edge. That is δ/T only when f is uniform.

**What the design records.**
- Per W record: the step (EXIT, REC, ENTRY → P0; S5-S10 → P1; S11 → P2;
  S12-S13 → P3; DESIGN:2217-2220) and both results.
- Per command: `(tick_in, c_in)`, `c_out`.
- Per poll: `c_start`, `wk_delay` and the holders.

So every Nop's distance from the nearest thread `c_out` and `c_in`, every
window's phase, and the empirical density near the edge are in the data. A
Nop reported at P0 within ≈ 3 µs after a P33 `c_out` is exactly the one that
would have been P1-P3 in the baseline, and the analyst can count them.

**Ruling: DIAGNOSABLE.** The per-Nop probability of meeting a given 0x08 step
is shift-invariant when phases are spread. When they are not, the data shows
by how much it moved. The no-death inference is per P-point, from the run's
own counts. **Recommended (K6):** restate the bound, and print the number of
windows within δ of a tick edge and of P0 Nops within 3.4 µs after a P33
`c_out`.

### KR1 (instrumentation-fault; R-4). The `build_id` check misfires: false red, false accept, false refusal. DIAGNOSABLE (K3, K9)

**(a) False red at boot (KRN).**
- KRN requires stats word 2 to equal the CRC-32 of `/proc/version` as the
  worker reads it at start (DESIGN:1959).
- By B1-B3 the two byte strings are equal by construction: the same macros,
  the same `\n`, and release and version cannot change at run time. By B4-B5
  the kernel hashes `strlen` bytes, including the `\n`. I reproduced
  `0x9b3c599e` from the image bytes.
- A false red therefore needs an implementation slip, for example hashing the
  256-byte NUL-padded FILEHDR field, or a short `read()`.
- **What happens:** KRN red at 3:00 is an abort (DESIGN:1986-1992;
  RUNBOOK:238). No run is spent, but the hardware session is lost. No Stage 3
  vector exercises KRN with the real banner bytes (DESIGN:2016-2046): K9.

**(b) False accept of the wrong maps (decoder).**
- 10.1 rests on "a rebuild … has another banner (its build time)"
  (DESIGN:2084-2086) and 1.7's "the value differs between any two builds"
  (DESIGN:417). Both are false under `build.sh`'s identity knobs (B6).
- A **different commit** built with the packaged identity (for example by a
  Stage 3 verifier reproducing the release byte for byte) has the same
  `build_id`. If `Syscon_cmd`, `psc_sc_exit` and `_pspSysconGetCtrl2` did not
  move, so that words 20-22 also match, the decoder accepts that build's
  `epcmap.txt` and `regmap.txt`, and the H4 step and k/j could be read
  through the wrong map.
- This is narrow (it needs a deliberate identity override and a change that
  keeps the three addresses), and the raw `epc` stays in the records.
- Fix (K3): bind `BUILD/` to the image that ran through the G3 R3 hash, and
  make the packaged build with the default identity.

**(c) False refusal.**
- The G2 verifier's rebuild of the same HEAD differs only in the banner (8
  bytes; verify §2). Given that directory, the decoder refuses the EPC
  analysis and prints the reason. Parsing still runs. That is the intended
  outcome (DESIGN:2084-2086).
- But 10.1 names the G2-attempt-1 directory and `0x9b3c599e` as the example
  (DESIGN:2081-2082). G2 attempt 2 must rebuild, because a new `pscol` means
  a new initramfs and a new banner, so the example becomes a trap for the
  analyst. K3 replaces it with the G3 R3 record.

**Ruling: DIAGNOSABLE.** No record is lost in (a)-(c). (a) aborts before the
run, (b) is narrow and leaves raw EPCs, and (c) refuses with a reason.

### KR2 (instrumentation-fault; R-4 × OE4). A stray store changes word 2 in the middle of the run. DIAGNOSABLE (K4)

**Shape.** A kernel-privileged stray store (OE4 class, R16) hits
`psc_k.build_id`, which is outside the seven guard words (B4). Every later
STATS chunk carries the changed word 2, and FILEHDRs written after it
mismatch their own `/proc/version` CRC.

**What the design records.**
- KRN passed at start, with the true value.
- The first FILEHDR and the early STATS chunks hold the true value; the later
  ones hold the changed value.
- 10.1 refuses the EPC analysis if "word 2" differs from `build_id.txt`
  (DESIGN:2076-2077), but does not say **which** stats block. A decoder that
  checks every block refuses the EPC analysis for the whole run, including an
  onset at minute 5 whose maps are right. The H4 step label, which 9.6 makes
  load-bearing, would then not be computed automatically. The raw `epc` and
  `r` survive, and an analyst can map them with the packaged `System.map`.

**Ruling: DIAGNOSABLE** (no data lost; the refusal names its reason). This is
also a **detected** stray store, which R16 otherwise calls undetectable.
**Recommended (K4):** check against the first stats block, and turn a later
change into `instrumentation-suspect` from its tick, not into a whole-run
refusal.

### MEM1 (instrumentation-fault; R-5). The order-6 boot allocation fails, or G2 attempt 2 grows `pscol` or the image. DIAGNOSABLE

**Shape and trace.**
1. **Supervisor `exec` fails** (no 256 KB block at ≈ 20-40 s of uptime). The
   PSC display never appears, which is an abort (DESIGN:1990-1991). M5's
   printk is in the kernel log.
2. **Worker `exec` fails.**
   - The `vfork` child exits and the supervisor's `waitpid` sees a death.
   - It takes over in-process, so there is no further recovery (R14).
   - HUD shows `SUP RUN`. SUP ("`getppid()` is not 1", DESIGN:1964) is no
     longer satisfiable once the supervisor itself is the worker, because its
     parent is the shell or init.
   - SUP red at 3:00 is an abort (DESIGN:1990), with no run spent.
   - The likelihood is very low: order 6 with ≈ 20 MB free shortly after boot
     (UNVERIFIED), and telem's order-8 block worked in the same position.
3. **G2 attempt 2 grows `pscol`.**
   - C8 now records ≤ 256 KB (DESIGN:908), with 78,176 B of margin.
   - The image has 5,521 B of margin to 49,152 B (DESIGN:1570-1574). A new
     bFLT adds about half its growth in gzipped initramfs bytes.
   - Above either bound the item returns to G1 (DESIGN:1573-1574).
   - An image that pspboot does not load is an abort (DESIGN:1576-1577; R20,
     UNVERIFIED).

**Ruling: DIAGNOSABLE.** Every branch ends in an abort before the run, or in a
G1 routing before release. None loses a run's records.

---

## 7. Section 17 statements: do I agree?

| Statement (DESIGN:2893-2906) | My position |
|---|---|
| R-1 option (a): no D2 outcome changes; thresholds at 0, ≥ 1 and ≤ 8 are not crossed; comparisons by set membership decide on identical bytes | **Agree.** Re-derived from the compiled loop (F3) and every reader (sections 2-3). Two wording fixes (K1), and one consequence the text does not name: the P6 j = 7 empty pop now rests on the EPC alone (NW1, K2) |
| Options (b) and (c) not approved, because they add instructions in S13..S20 where H4 and H10 act | **Agree.** H4's P4/P5a/P6 are in exactly that span (recon §5.1, §5.2) |
| R-2: the test is the 2.1 criteria, with three allowed differences | **Agree** (in my scope only through 7.3). The definition forbids renaming any register written in the window, so the k/j registers (`t0`, `a3`) cannot move under it |
| R-3: restated, not trimmed; 7.3 still holds | **Agree**, with K5 and K6 as text. The arithmetic checks (section 4) |
| R-4: the kernel's definition adopted; KRN compares with `/proc/version`; the decoder uses the packaged `build_id.txt` | **Agree with the mechanism; one sentence is false** ("differs between any two builds", KR1). K3 and K4 |
| R-5: 183,968 B, one 256 KB block each, both at boot; image bound kept | **Agree**; one addend is wrong (51,904 → 51,968, K7). The new figure improves OE4 (stack at the top of the block, M4) |
| R-6: 34,404 / 37,736 | Outside my scope. I checked the sums: 34,304 + 80 + 20 = 34,404; 34,404 + 788 + 2,420 + 104 + 20 = 37,736 → 37,888 |
| "Text only: no mechanism … was added" | **Agree.** The `nw7or8` flag and the KRN comparison are decoder and collector behaviour that the approved design already implied (stats word 2, the KRN check), not new records or rings |

**AMBIGUOUS findings accepted by the designer:** none. None of my scenarios is
AMBIGUOUS.

---

## 8. Attacks attempted that found nothing

| Attack | Result |
|---|---|
| A flagged record crossing a threshold (`nwords` = 0, ≥ 1, ≤ 8, stats outcome counters) | None lies between 7 and 8. The kernel's counters use the kernel's value, unchanged |
| An 8th `0xFFFF` word changing `ret`, `rx[1]`, `rx[2]`, the checksum or a button byte | Impossible: it rewrites the prefill with the same value (F1) |
| A healthy command with 7-word replies making every template record flagged | Then the template value is {7, 8}, and the decoder prints "ambiguity live" (DESIGN:2331-2334). A dead state that differs in any byte still leaves the template |
| N2b concatenation of two replies into 7 or 8 words | `rx[2]` comes from the first frame, so N2b decides on bytes. Any residue beyond 8 words shows as the next `drain` |
| The P6 j register (`t0`) separating 7 read from 8 read | It cannot: `t0 = 16` in both. Only `epc` does (NW1). After the 8th read the Nop's `drain = 0`, which separates "8 read" from both NW1 cases |
| R-2 renaming moving `i` or `ptr` out of registers 2..15, 24, 25 | Excluded: the definition allows renaming only registers that are not written in the window (DESIGN:1755-1758) |
| The panel (328 B) and the Nop path stacking on one tick | Impossible: T2d is ≡ 125 (mod 250), Nops are ≡ 0 (mod 1250) |
| `/proc/version` differing from `linux_banner` at run time (`sethostname`, sysctl, namespaces) | The nodename is not in either string; release and version are 0444; no UTS namespaces (B2, B3) |
| `strings` + `grep -m1` picking a different "Linux version" string | One match in the packaged image (offset 1,179,648); its CRC equals word 2 |
| The takeover needing a fresh 256 KB | No: same binary, same block (IF2) |
| A stack overrun corrupting `pscol`'s bss under the new layout | The stack is at the block's top with 78 KB of slack below (M4); the high-water mark reports it |
| The δ/T claim being wrong | Correct as stated ("when the window's phase is spread"). Made general in K6 |

---

## 9. UNVERIFIED items this report depends on

1. The value an empty RX FIFO read returns, and whether it leaves controller
   state behind (NW1; recon §4.1, §5.1).
2. The uncached MMIO latency m, and so the absolute G3-low gap (EX1). The run
   can bound it from the shortest command.
3. A syscon minimum G3-low time near 5 µs (EX1). The only hint is a commented
   wait.
4. The 0x33 reply length; I assumed `rx[1] = 3` (1.4). Each extra byte adds ≈
   5 instructions to the baseline gap.
5. 1 instruction per cycle and Count at the core clock (DESIGN:1582-1583),
   behind every µs figure.
6. The worst-case kernel stack depth under a Nop (TE4), measurable per Nop
   through K8.
7. Whether healthy replies of any command are 7 or 8 words long (NW2). The
   template shows it.
8. That pspboot loads the larger image (R20; MEM1).

---

## Housekeeping

- Original tree: `cd /home/ubuntu/psp/build/linux && sha256sum -c --quiet
  /home/ubuntu/psp/handoff/gates/baseline-tree.sha256` printed nothing, exit 0.
- Work tree: `git -C /home/ubuntu/psp/work/linux status --porcelain` printed
  nothing; HEAD `c135ecdd`.
- Disassembly ran in `psp-build:bullseye` with `/home/ubuntu/psp` mounted
  read-only. No file outside my scratchpad was written except this report.
