# PSP uClinux input-death: agent workflow and review gates

Read [DOSSIER.md](DOSSIER.md) first. This document defines who does what,
in what order, and what must pass before the hardware run is spent.

## Principles

1. **The hardware run is the scarce resource.** Agent time is cheap. Spend
   agent time to protect the run.
2. **Nobody reviews their own work.** Each gate is run by an agent with a
   fresh context that did not produce the artifact under review.
3. **A failed gate means revise and re-review.** Nobody overrides a verdict:
   not the author, not the orchestrator. Only the human operator can waive
   an item, in writing, in the gate log.
4. **Reviewers try to break the artifact.** A review that lists no attempted
   attacks is rejected as incomplete.
5. **Agents never touch hardware or the Memory Stick.** The last gate is a
   human signature.

## Roles

All agents are Opus 5.5 (`claude-opus-5-5`). One role per agent instance.
Reviewers receive the dossier and the artifact under review. They do not
receive the author's working notes or conversation.

| Role | Does | Must not |
|---|---|---|
| Orchestrator | Runs the stages, keeps the gate log, routes findings, escalates | Edit artifacts, alter or summarise away a verdict |
| Recon A, B, C | Read source, establish facts, reconstruct the build | Propose designs |
| Fact checker | Re-verifies recon claims against the source | Have been a recon agent |
| Designer | Writes the instrumentation design and the runbook draft | Write kernel code |
| Design reviewer | Gate G1 | Have been the designer |
| Red team | Gate G1, second reviewer: invents failure shapes the design would miss | Have been the designer |
| Implementer | Writes the patch and userland changes, drives the build | Change the approved design without going back to G1 |
| Code reviewer | Gate G2 | Have been the implementer or the designer |
| Verifier | Builds from clean, runs host-side tests, checks the package | Have been the implementer |
| Analyst | Writes the decoder before the run, interprets data after | |
| Human operator | Answers open questions, signs G3, performs the run | |

## Sequence

```
Stage 0  Recon ──────────────► G0  fact check
Stage 1  Design ─────────────► G1  design review + red team      ◄── most important gate
Stage 2  Implement + build ──► G2  code review
Stage 3  Off-device verify ──► G3  release review + human signature
Stage 4  Hardware run (human)
Stage 5  Analysis
```

A stage starts only when the previous gate has passed.

---

## Stage 0: Recon

Three agents in parallel, read-only except for Recon C.

| Agent | Task | Output |
|---|---|---|
| Recon A | Syscon transport and every caller, in every context. Re-verify dossier sections 4.1, 4.4, 4.5, 4.6 and 6.4. Determine which SPI and GPIO registers can be read without side effects. | `recon/syscon.md` |
| Recon B | Joypad driver, input core path to mousedev, thread lifecycle, signals. How `telem` captures data and what it would take to extend it. What `psposk2` and `pspmd` open, from strings or disassembly. Re-verify 4.3 and 4.7. | `recon/input.md` |
| Recon C | Copy the tree to `/home/ubuntu/psp/work/linux`. Put the copy under git with the unmodified state as the first commit. Reconstruct the build command. Rebuild the unmodified copy and compare against the existing `vmlinux-0.22.bin`. Write `build.sh` and `package.sh`. | `recon/build.md`, scripts, baseline commit |

Every claim in a recon report cites file and line and quotes the code.

### Gate G0: fact check

The fact checker opens each cited location and confirms the quote and the
conclusion drawn from it.

| Item | Pass condition |
|---|---|
| F1 | Every claim has a citation that resolves and says what is claimed |
| F2 | Every dossier statement labelled [SRC] is confirmed, or corrected with evidence |
| F3 | The build script rebuilds the unmodified tree from clean inside the container, and the result matches the existing image or the differences are explained |
| F4 | The original tree at `build/linux` is unchanged (checksums before and after) |

Fail: the recon agent concerned corrects and resubmits. The dossier is
amended by the orchestrator only with text the fact checker approved.

---

## Stage 1: Design

The designer writes `design/DESIGN.md` and `design/RUNBOOK.md`. No kernel
code yet. The design must contain:

1. **Record format.** Every field, its width, its source. Bytes per record.
2. **Capture points.** Where in `Syscon_cmd`, `read_input`, the thread loop
   and the delivery functions. Which execution context each runs in.
3. **History mechanism.** Ring size, what is kept at full resolution, what
   is summarised, what triggers a freeze or dump of the ring.
4. **Extraction path.** How data reaches the Memory Stick with no operator
   input, how often, and what is lost if the battery is pulled at the worst
   moment.
5. **Budget.** Bytes per second to the stick and total for 15 minutes.
   Kernel memory used. Time added per syscon command and per poll.
6. **Coverage matrix.** One row per hypothesis H0 to H8 from the dossier.
   For each: the exact fields and values that identify it, and which other
   rows it could be confused with.
7. **Perturbation statement.** What the instrumentation changes about
   timing, locking and interrupt state, and the argument that this neither
   hides nor causes the failure.
8. **Self-test.** How the run proves, before death occurs, that the
   instrumentation is alive and recording correctly.
9. **Runbook.** Operator steps, including a scripted button pattern before
   death, a scripted pattern after death, how long to wait before the
   battery pull, and what to photograph.
10. **Decoder specification.** The format the analyst's tool will parse.

### Gate G1: design review

Two independent reviewers, in parallel: the design reviewer works the
checklist, the red team attacks. Both must pass.

#### Design reviewer checklist

Each item is marked PASS or FAIL with evidence. Items marked **B** are
blocking: one FAIL fails the gate.

| ID | B | Check |
|---|---|---|
| D1 | B | **Single-shot coverage, not guess-and-check.** The design records a running history of raw syscon state across many poll cycles and keeps whole-run summaries. It does not depend on any one hypothesis being right. A design built around one printk or one counter aimed at the HOLD theory fails this item. |
| D2 | B | **Coverage matrix is real.** For each of H0 to H8 the reviewer independently derives what the recorded fields would contain and confirms the row is distinguishable. The reviewer does this from the record format, not from the designer's matrix. |
| D3 | B | **Raw data is kept.** Full `rx_buf`, the command byte, the return value, and the number of words actually received are recorded. Classified or decoded values alone are not enough. |
| D4 | B | **Window independence.** Works for death at 17 s and at 15 minutes. History before onset is not lost to wraparound. History after onset is not lost to a freeze trigger that fires too early. |
| D5 | B | **Onset is captured without needing to detect onset.** If the design uses a trigger, the reviewer confirms that a failure shape which never fires the trigger still leaves usable history. |
| D6 | B | **Survives battery pull.** States the worst-case data loss in seconds. It must be smaller than the post-death wait in the runbook. |
| D7 | B | **No operator input needed after boot.** |
| D8 | B | **Both contexts recorded.** Thread-context and interrupt-context syscon commands are both logged, with context identified, and an interrupt arriving during a thread-context command is recorded as such. |
| D9 | B | **Context safety.** The recording structure is safe when the timer interrupt interrupts the thread mid-record. The mechanism is stated. |
| D10 | B | **Perturbation.** No new lock, interrupt masking or delay around the syscon transaction beyond the few instructions needed to append a record. Added time per command is stated and small against the command's own duration. |
| D11 | B | **No unsafe register reads.** Any register snapshot lists each address and cites the recon evidence that reading it has no side effect. |
| D12 | B | **Log volume.** Budget arithmetic is shown and is right. No poll-rate printk. The 16 KB kernel log is not relied on for history. |
| D13 | B | **Self-test before death.** The operator can confirm from the screen in the first seconds that records are being written and that a button press appears in them. If not, the run is aborted and costs nothing. |
| D14 | B | **Timeout visibility.** The existing silent returns `-3`, `-4`, `-5` and `-2` are each recorded distinctly. |
| D15 |   | Above-syscon stages have counters: loop iterations, `read_input` exits by branch, process and delivery calls, semaphore failures, `signal_pending`. |
| D16 |   | Timestamps allow ordering within a jiffy and alignment with the 5 s watchdog cycle. |
| D17 |   | The runbook's post-death button pattern is specific enough to separate H6 from H7. |
| D18 |   | No floating point in userland. Check method stated. |
| D19 |   | The deploy folder name is new and the baseline folder is not written. |
| D20 |   | The decoder specification matches the record format field for field. |

Two or more non-blocking FAILs also fail the gate.

#### Red team task

Produce at least five concrete failure scenarios and, for each, trace what
the design would record. At least one must come from each group:

- a failure shape not in the dossier's list
- a timing edge: death in the first 10 s, death during a flush to the
  stick, death at minute 14
- a fault in the instrumentation itself: ring index corrupted, extraction
  process killed, stick write blocks or fails, stick fills
- an observer effect: the instrumentation changes timing enough that the
  failure does not happen in the run, or happens for a new reason

For each scenario the verdict is DIAGNOSABLE, AMBIGUOUS or BLIND. Any BLIND
fails the gate. Any AMBIGUOUS must be either fixed or accepted by the
designer with a written reason that the design reviewer agrees with.

#### Verdicts

| Verdict | Meaning | Next |
|---|---|---|
| PASS | All blocking items pass, fewer than two non-blocking fails, no BLIND | Stage 2 |
| FAIL | Anything else | Designer revises, then a full re-review |

Re-review covers every item again, not only the ones that failed, because
a fix to one item can break another. The reviewer sees the previous
findings and the designer's response to each. A finding is closed only by
the reviewer.

After three failed rounds the orchestrator stops and escalates to the human
with the findings. A fourth attempt by the same designer is not made without
the human's direction.

---

## Stage 2: Implement and build

The implementer works on a branch in `/home/ubuntu/psp/work/linux`.

- Kernel changes as small commits, one concern each.
- Userland changes (extension of `telem` or a new collector) with the same
  build and FP check as `telem/cbuild.sh`.
- Initramfs updated so collection starts from `rc.sysinit` with no input.
- Build through `build.sh` from clean. Full log kept.
- `IMPLEMENTATION.md` maps each design section to the code that implements
  it, and lists every deviation from the design.

Any deviation that touches a blocking G1 item sends the design back to G1.

### Gate G2: code review

| ID | B | Check |
|---|---|---|
| C1 | B | **Conformance.** The diff implements the approved design. Record format in code equals the format in the design, field by field. |
| C2 | B | **Diff is confined.** Every changed line is accounted for in `IMPLEMENTATION.md`. No behaviour change to the syscon transaction or driver logic apart from recording. The timeout patch is still present and unchanged. |
| C3 | B | **Context safety in code.** Nothing that can sleep is reachable from interrupt context: no `kmalloc(GFP_KERNEL)`, no semaphore, no `copy_to_user`, no printk at rate. Ring append is correct when interrupted mid-append. |
| C4 | B | **Bounds.** Ring index arithmetic, wraparound, `/proc` read handling of partial reads and offsets, buffer sizes against `rx_buf[0x10]`. |
| C5 | B | **Does not break boot.** Init order: recording is safe to call from `arch_early_setup` time, before the ring's consumers exist. Interrupt-context syscon calls start before the driver initialises. |
| C6 | B | **Clean build.** Built from clean by the verifier, not the implementer. No new warnings in changed files. Image size within what `pspboot` loaded before, with the difference stated. |
| C7 | B | **Symbols present.** `objdump` of the final `vmlinux` shows the new functions and the capture calls at the intended sites. |
| C8 | B | **Userland.** `flthdr` shows a valid bFLT header. FP register use count is zero. Stick writes are synced. Write failure is shown on screen, not ignored. |
| C9 |   | Endianness and struct packing are explicit, and the decoder agrees. |
| C10 |   | Commit history is readable and each commit builds. |

Verdict rules, re-review rules and the three-round limit are the same as G1.

---

## Stage 3: Off-device verification

There is no emulator to rely on. This stage tests everything that can be
tested without the device.

| Test | Method |
|---|---|
| Ring logic | Compile the ring and record code on the host with a stub for register access. Drive it with synthetic sequences for each of H1 to H8, including an interrupt arriving mid-record. |
| Decoder | Feed the host-generated dumps through the analyst's decoder. It must name the right hypothesis for each, and report "unclassified" with raw data for a sequence matching none. |
| Truncation | Cut a dump at arbitrary byte offsets, as a battery pull would. The decoder recovers every complete record before the cut. |
| Volume | Simulate 15 minutes at 20 polls per second. Output size matches the design budget. |
| Package | The deploy folder contains the kernel, `pspboot` and `pspboot.conf` with the right paths, and has a name that collides with nothing. |
| Initramfs | Unpack the embedded cpio from the built image. Confirm the collector is present, executable, and started from `rc.sysinit`. |

### Gate G3: release to hardware

Run by the verifier plus the human operator.

| ID | Check |
|---|---|
| R1 | G0, G1 and G2 each show PASS in the gate log with no open findings |
| R2 | All Stage 3 tests pass, with logs attached |
| R3 | The image under release is the one reviewed: checksum in the gate log equals the checksum of the file in the deploy folder |
| R4 | The runbook has been read end to end by an agent that did not write it, playing the operator, and every step is unambiguous |
| R5 | The runbook has an abort rule: if the self-test indicator is not seen within a stated time of boot, power off and report. That does not count as the run. |
| R6 | The decoder exists and is tested now, before the run |
| R7 | Dossier open questions are answered, or the design is shown not to depend on the answer |
| R8 | **The human operator signs.** |

No agent may mark R8.

---

## Stage 4: Hardware run

Performed by the human following `RUNBOOK.md`. The human returns the files
from the stick, photographs, time of death as perceived, and any departure
from the runbook.

## Stage 5: Analysis

The analyst decodes and writes `analysis/REPORT.md`: which hypothesis, the
evidence, the confidence, and what the data cannot tell us. A second agent
reviews the report against the raw data before it goes to the human. The
same rule applies: findings are closed only by the reviewer.

If the run produced no failure within the runbook's time limit, that is
reported as a result, together with the perturbation analysis from the
design. It is not treated as a pass.

---

## Gate log

The orchestrator keeps `gates/LOG.md`. It is append-only. One entry per
gate attempt:

```
gate:        G1
attempt:     2
artifact:    design/DESIGN.md @ <commit>
reviewer:    <agent id>, fresh context: yes
verdict:     FAIL
findings:    D4 FAIL: ring holds 40 s, onset trigger absent, death at 200 s
             with H6 shape never freezes the ring ...
             (each finding: item, evidence, what would close it)
response:    <author's reply per finding, added on resubmission>
closed by:   <reviewer, per finding, on the next attempt>
```

## Escalation

| Situation | Action |
|---|---|
| Three failed attempts at one gate | Stop. Report to the human with all findings. |
| Reviewer and author disagree on a finding | The finding stands. The author may ask the orchestrator to put it to the human. |
| A reviewer finds a dossier statement is wrong | Stop the stage, route to the fact checker, amend the dossier, then resume |
| An agent finds it needs hardware access or information only the human has | Add to the open questions and continue with what does not depend on it |

---

## Amendments (human decisions that change a rule above)

### A1: scope of Memory Stick failure in the G1 red-team task (2026-10-05)

Decided by the human after the second G1 escalation (gate log, round 4).

**Rule change.** In the red-team task, a scenario whose cause is a
*persistent single-sector refusal of Memory Stick metadata* (one FAT,
FSINFO or directory sector refusing writes for the rest of the run while
data sectors still write) receives the verdict **SPOILED-DETECTED**
instead of BLIND, provided the design satisfies all three of:

1. it detects the condition from its own records within 30 s of onset;
2. it shows the condition on the kernel panel and the HUD, so the operator
   knows the run is spoiled;
3. the runbook says what to do (raw image mandatory, run not counted).

SPOILED-DETECTED does not fail the gate. It is listed separately in the
report. A scenario in this class where the design *destroys data that had
already reached the stick* (for example by overwriting it in place) is
still BLIND: detection excuses lost coverage, not lost records.

**Still fully in scope** (BLIND fails the gate as before): transient and
sporadic write failures, bursts of any length, slow sticks, stick full,
a pull during any collector activity, and anything the collector's own
behaviour causes.

**Evidence behind the decision.** The recovered `kmsg.txt` shows no
Memory Stick error. The earlier `telem` program wrote two logs to the same
stick for more than eleven minutes in total without a recorded error, and
both decoded cleanly. The premise is marked UNVERIFIED in every red-team
report that used it (attempt 3 item 1, attempt 4 item 1). Rounds 1-4 each
closed one stick-failure shape and opened the next; the human judged that
class open-ended against the evidence.

**Fallback.** If the gate still fails under A1 for an in-scope reason, the
human has pre-authorized one further round at *full* scope (A1 suspended)
with every red-team fix adopted, after which the gate escalates again.
