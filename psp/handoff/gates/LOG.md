# Gate log (append-only)

```
gate:        G0
date:        2026-09-27
run:         wf_6f5bc63c-8bf

artifact:    recon/syscon.md
attempt:     1   reviewer: fresh context   verdict: PASS
items:       F1 PASS, F2 PASS, F3 N/A, F4 PASS
findings:    1 non-blocking (summary table says "Wrong" where body says "incomplete")

artifact:    recon/input.md
attempt:     1   reviewer: fresh context   verdict: PASS
items:       F1 PASS, F2 PASS, F3 N/A, F4 PASS
findings:    none

artifact:    recon/build.md
attempt:     1   reviewer: fresh context   verdict: FAIL
items:       F1 FAIL, F2 PASS, F3 PASS, F4 PASS
findings:    8 (wrong log citation; incomplete mm graft description; uncited
             "not a uc1 tree" claim; miscount of root-owned files; paraphrase
             presented as literal script; syscon-timeout.patch not checked;
             package.sh half-staging; one unverifiable search claim)
response:    author accepted all 8, revised in place, section 10 of report
attempt:     2   reviewer: fresh context   verdict: PASS
items:       F1 PASS, F2 PASS, F3 PASS, F4 PASS
findings:    5 non-blocking, carried into dossier section 9 where relevant

original tree: sha256sum -c against gates/baseline-tree.sha256, exit 0,
               23495/23495, no unmanifested files (checked by all 4 reviews)

overall:     PASS
dossier:     amended by orchestrator, section 9, checker-approved text only
open:        pspboot files absent from build machine (blocks packaging, not design)
```

```
note:        2026-09-30  human answers recorded in DOSSIER.md Q8-Q10 and 9.5
             (observations 1-5 on 2008 image; kmsg.txt 1,606 bytes; OSK
             cannot be raised after death). No gate state changed.
```

```
note:        2026-09-30  DOSSIER.md 9.6 added: stick telemetry shows all
             three bracketed input deaths at 5 s uptime multiples (275, 145,
             140). H4 promoted to leading hypothesis. 9.7 added: baseline
             boot folder recovered, kernel confirmed as 2008 image.
             Stage 1 workflow wf_e3298533-680 was already running; designers
             may not have seen 9.6. G1 reviewers launched after this note
             will. Orchestrator to confirm the passed design covers 9.6
             before Stage 2, or add a supplementary review.
```

```
gate:        G1
date:        2026-09-30 / 2026-10-01
run:         wf_e3298533-680
artifact:    design/DESIGN.md + design/RUNBOOK.md (synthesis of candidate-A
             minimal-perturbation and candidate-B maximum-coverage; recon/image2008.md
             confirmed the 2008 watchdog path is the same code, waits unbounded)

attempt 1    reviewer FAIL (D6 blocking: battery-pull loss bound unenforceable
             when the writer stalls; D20 decoder/flush size mismatch; 13 other)
             red team FAIL (2 BLIND: worker re-exec needs a 1 MB contiguous
             kmalloc late in the run; collector's own MS I/O can stall the
             machine with no record; 6 AMBIGUOUS)
response:    designer fixed 21 of 23, contested 2 sub-points with evidence
attempt 2    reviewer FAIL (D6 reopened: stall panel overwritten by live HUD
             redraw; D20 flag/size inconsistencies; 6 other)
             red team FAIL (1 BLIND: segment-name exhaustion under write-error
             bursts; 3 AMBIGUOUS incl. nested-tick case and kernel-privileged
             userland)
response:    designer revised in place, section 13
attempt 3    reviewer PASS (all D1-D20; 5 advisory findings N-1..N-5 open:
             POLL:RATE escape unreachable, HUD line width, IN/DELIV undefined,
             H6/N2b rely on unverified response-code comment, PANEL proves less
             than stated)
             red team FAIL (3 BLIND, all one root cause: a failed fsync on a
             flush that allocated a FAT cluster leaves records in unlinked
             clusters and can drive vfat read-only; 2 AMBIGUOUS)

overall:     FAIL after 3 rounds -> ESCALATED to human per WORKFLOW.md
root cause   The collector's segment files grow during the run, so every
of residual  cluster allocation is a FAT metadata write on the same stick
BLIND:       whose failure modes the run must survive. Red-team fix on record:
             preallocate fixed-size segments (PAD + fsync + verify) at start,
             so steady-state flushes never dirty the FAT; abandon any segment
             whose creation saw an error; expose MS_RDONLY on the panel.
note:        DESIGN.md is 3,006 lines / 273 KB with 25+ open risks. Orchestrator
             flags implementation-complexity risk for Stage 2 independently of
             the gate result.
```

```
note:        2026-10-01  Human reviewed the G1 escalation and authorized ONE
             further round (round 4) with a changed brief, per WORKFLOW.md
             ("a fourth attempt ... is not made without the human's
             direction"). Brief: close IF5/IF1/IF4 by preallocated fixed-size
             segments (red-team fix 1a + 2-4), close IF6 and UL5, close
             N-1..N-5, confirm watchdog-phase resolution (dossier 9.6), and
             CUT every mechanism not load-bearing for D1-D20, S1-S5 or an
             attempt-1..3 scenario, with a traceability table (new section 0)
             proving no closed scenario reopens. Target under 1,800 lines.
             Then full re-review by checklist reviewer and red team.
             No round 5 is scheduled: a FAIL escalates again.
run:         wf_111cdfc7-8c3   (attempt 4 reports will be gates/G1-attempt4-*.md)
```

```
gate:        G1
date:        2026-10-01
run:         wf_111cdfc7-8c3   (round 4, human-authorized, scoped brief)
artifact:    design/DESIGN.md revision 3 (1,856 lines incl. section 13; 1,795
             through section 12; was 3,006), design/RUNBOOK.md (443 lines),
             design/DESIGN-history.md (responses to attempts 1-2 moved out).
             Section 0 traceability table added. Open risks 36 -> 22.
             Cut: I ring, per-tick wait-class sampling, standby worker,
             W stack/copies, histograms, 9,999-name scheme, pixel read-back,
             unused decoder features; HUD reduced to 10 lines.

attempt 4    reviewer PASS (all D1-D20; N-1..N-5 confirmed closed; cuts
             audited, none reopens a blocking item or a closed BLIND; vfat
             claim "a segment in use never dirties a FAT sector" verified in
             tree; 6 advisories A4-1..A4-6: S-record rate during creation
             under-counted, drop_caches walk under inode_lock unbounded and
             unlisted in 7.1/7.4, spare-under-creation forces raw image in
             ~20 % of normal runs, HUD line 6 unspecified during start-up
             creation, early-death vs PSC TEST abort conflict, consistency)
             red team FAIL (3 BLIND: IF4 sporadic variant re-opened by
             all-or-nothing 2 MB creation; IF7 persistent FSINFO/directory
             sector refusal destroys in-place-retried data; IF8 persistent
             FAT-sector refusal stalls creation ~21 min. 2 AMBIGUOUS: A1-OE3
             reopened by the cut of T2c + I ring (preempted-mid-command
             holder no longer recorded; fix F5 is small); TE6 early death
             on a slow stick before the first 2 MB segment exists.
             IF1, IF5, IF6, UL5 now DIAGNOSABLE; 19/22 attempt-3 scenarios
             DIAGNOSABLE.)
             red-team fixes on record F1-F6 (section 6 of the report):
             judge durability from data-sector S records not fsync return,
             incremental creation with usable confirmed prefix, cap/margin,
             FAT-sector escape, preemption-holder hook, Stage 3 schedules.

overall:     FAIL -> ESCALATED to human (second escalation)
orchestrator The attempt-4 residuals are all in one premise: Memory Stick
note:        write failures (sporadic, or persistent on one metadata sector)
             during the run. That premise is UNVERIFIED (red team 8.1): the
             recovered kmsg.txt has no MS error, and telem wrote telem.log
             and telem-v1.log to the same stick for >11 min total without
             a recorded error. Each round's fix to the stick path has opened
             the next stick-failure shape (r1 IF4 -> r2 IF5 -> r3 IF4/IF7/
             IF8). Whether that class stays in scope is a human decision.
original tree: sha256sum -c baseline-tree.sha256 exit 0 after round 4.
```

```
note:        2026-10-05  Human reviewed the round-4 escalation and chose:
             (1) amend the red-team scope per WORKFLOW.md Amendment A1
             (persistent single-sector metadata refusal -> SPOILED-DETECTED
             when detected, displayed and covered by the runbook; data
             already on the stick must still never be destroyed), and
             (2) authorize round 5 under A1, with a pre-authorized round 6
             at full scope adopting every red-team fix if round 5 fails
             for an in-scope reason. Round 7 is not authorized.
```

```
gate:        G1
date:        2026-10-05
run:         wf_5b75d687-59e   (rounds 5 and 6, human-authorized)

attempt 5    scope: Amendment A1. artifact: DESIGN.md revision 4 (2,050 lines;
             1,920 through section 12), RUNBOOK.md 457 lines.
             designer: F2 incremental creation + confirmed prefix, F3, F5
             preemption-holder hook, F1(a)+(c) no-overwrite, A1 META
             detection (kernel tags metadata-page S records; 5 failed writes
             over 3 ticks), F4 fast retry, F6, A4-1..A4-6 closed
             (drop_caches replaced by raw syscall 4254 fadvise).
             reviewer FAIL (D6 blocking A5-1: a transient failure during a
             creation's step-0 fsync can make the next O_CREAT|O_EXCL reuse
             the abandoned inode; its first allocating step then hits
             fat_fs_panic and /ms0 goes read-only; in scope under A1.
             A4-1..A4-6 all confirmed closed. 3 advisories A5-2..A5-4.)
             red team FAIL (1 BLIND in scope: IF9, a data region of a
             confirmed file refusing writes; seg_end advances only 2 KB per
             tick. 2 AMBIGUOUS in scope: IF4 re-send rule, IF10 chunks from
             another boot merged. IF7, IF8 ruled SPOILED-DETECTED under A1.)

attempt 6    scope: FULL (A1 suspended, pre-authorized fallback). artifact:
             DESIGN.md revision 5 (2,588 lines; 2,213 through section 12),
             RUNBOOK.md 483 lines, design/r5-scripts/ (budget + simulation).
             designer: A5-1 fixed (fstat size 0 + unseen inode after every
             create), IF9 fixed (switch file after 3 data-sector failures),
             IF4/IF10 fixed (per-boot nonce seeds chunk CRC), F1(b) FIBMAP
             durability and full F4 sector classification adopted, META
             made informational.
             reviewer FAIL (D6 blocking A6-1: under a persistently refusing
             PSCLOG directory sector, the step-0 rule "its directory write
             failed -> abandon" cannot tell the file's own entry write from
             the refusing sector's rejected-alias writes, so creation never
             succeeds again and later deaths have no history. Fix is a
             specification: identify the own-entry write as the first
             DIR-class S record after the step's DATA records. A5-1..A5-4
             all confirmed closed. 3 advisories A6-2..A6-4: syslog() is the
             libc function not the kernel call; consistency nits; pread
             f_pos note.)
             red team PASS (43 scenarios, 0 BLIND at full scope. 2 AMBIGUOUS
             with concrete fixes: IF7b, the same own-entry identification
             the reviewer asks for; TE10, the active file still in creation
             must not be its own switch target during catch-up.)

overall:     FAIL -> ESCALATED to human (third escalation). No round 7
             authorized.
orchestrator First red-team PASS at full scope. The one blocking item is a
note:        specification gap, and both reviewers name the same closing
             text. Design size has grown back from 1,856 (r3) to 2,588
             lines: the round-4 complexity concern stands.
original tree: sha256sum -c exit 0 after round 6; work/linux clean.
```

```
note:        2026-10-05  Human reviewed the third escalation and authorized
             ROUND 7, closure only: the designer may change only the text
             needed to close A6-1..A6-4 and red-team IF7b and TE10, must add
             no mechanism, and must produce a diff against revision 5
             (frozen copies design/DESIGN.r5.md, design/RUNBOOK.r5.md).
             Scope: FULL (A1 remains on record but was not needed at round 6).
             Both reviewers re-review with the diff. No round 8 authorized.
```

```
gate:        G1
date:        2026-10-06
run:         wf_2142ee15-7a5   (round 7, human-authorized, closure only)
artifact:    design/DESIGN.md revision 6 (2,669 lines; 2,254 through section
             12), design/RUNBOOK.md (485 lines), design/round7.diff (350
             lines against frozen design/DESIGN.r5.md + RUNBOOK.r5.md)

attempt 7    reviewer PASS (all D1-D20; A6-1..A6-4 confirmed closed; diff
             confined to the brief: 23 DESIGN hunks + 1 RUNBOOK hunk, each
             mapped to one of the six items, no new mechanism; own-entry
             write order re-verified in tree fs/sync.c, fs/fs-writeback.c,
             fs/fat/inode.c, fs/buffer.c. 3 advisories A7-1..A7-3: a stale
             IF7b figure in 4.4 step 6; the 306-name IF7b bound assumes
             cached inodes are not evicted, state the outcome and run the
             VFAT-FI guest with ample memory; a syslog(3) naming nit in 4.3.)
             red team PASS (50 scenarios, 0 BLIND, 0 AMBIGUOUS; IF7b and
             TE10 now DIAGNOSABLE; new scenarios against the own-entry,
             never-a-switch-target and hold-and-resume rules all
             DIAGNOSABLE.)

overall:     PASS  (7 attempts; human authorized rounds 4-7; Amendment A1
             was on record but the passing review ran at FULL scope)
open:        A7-1, A7-2, A7-3 advisory. G3 R1 requires them closed; the
             orchestrator will have the implementer apply the three text
             edits at the start of Stage 2 and the G2 code reviewer confirm
             closure, so the design and the code are reviewed together.
next:        Stage 2 (implement and build) may be authorized by the human.
original tree: sha256sum -c exit 0; work/linux clean.
```

```
note:        2026-10-06  Human answered the runbook's three pre-run
             questions (recorded in DOSSIER.md 9.8: any or no buttons;
             battery; mouse mode off) and AUTHORIZED STAGE 2 as a
             workflow. Stage 2 run: see next entry.
```

```
gate:        G2
date:        2026-10-06
run:         wf_8f8df699-258   (Stage 2: interface, kernel, pscol, decoder,
             integrate; G2 attempt 1)
artifact:    branch stage2-trace in work/linux (HEAD c135ecdd, 16 commits),
             work/pscol (bFLT 55,044 B), work/decoder, impl/IMPLEMENTATION.md,
             package work/deploy/uClinux_TRACE, release vmlinux-0.22.bin
             sha256 c72459e3e70f72605ffe35fc371ca8b93f9e7ab53d7fdac25021a0896d38b738
             (936,321 B; +37,039 B vs pspboot-baseline; vmlinux.bin +43,631 B,
             5,521 B under the design's 48 KB bound)

attempt 1    verifier FAIL: build ok, manifest exit 0, no new warnings, all
             symbols present, pscol FP regs 0, flthdr ok, initramfs has
             pscol, package ok; BLOCKING OD-2: Syscon_cmd S5..S20 not
             literally identical to baseline (105 instructions, same MMIO
             order, 0 calls; five callee-saved registers renamed, one delay
             slot after the -3 exit lw->nop). Meets DESIGN 2.1 criteria, not
             the literal "identical apart from stack offsets". Advisories:
             pscol data+bss+stack 132,000 B vs 128 KB figure; image size
             pspboot load UNVERIFIED (R20); banner-only sha256 difference
             between verifier and release builds; timeout patch -R dry-run
             fails because the code moved into a wrapper (behaviour same).
             reviewer FAIL (C1): BACK_TO_G1 for DV-3: nwords records 7 when
             8 words arrive and the 8th is 0xFFFF; an exact count needs
             instructions inside S5..S20 (D3 vs D10 conflict in the approved
             design). Two further BLOCKING code bugs: pscol segment-name
             scan tests strlen==12 / dot at 8 for an 11-char 8.3 name and
             ignores shortname=lower, so run numbering never advances;
             decoder's map grammar does not match the release maps (P6 j
             never computed, LEDSPLIT 'not in regmap'). Advisories: KRN
             never compares build_id; measured perturbation 400-550
             instructions after S20 vs design's ~130 (about 2-2.5 us);
             re-send double-counts lost; commit author attribution.
             A7-1..A7-3 confirmed closed by the reviewer.

overall:     attempt 1 FAIL; routed BACK TO G1 per WORKFLOW.md Stage 2
             ("Any deviation that touches a blocking G1 item sends the
             design back to G1"). G2 attempts 2-3 remain available after
             the G1 ruling.
run:         wf_2daaeb23-497   G1 ruling on R-1..R-6 (designer amendment,
             design reviewer + red team, limited scope), then G2 attempts 2
             and 3 (implementer revise, code reviewer + verifier). Launched
             2026-10-06 by the orchestrator under the Stage 2 authorization.
```

```
gate:        G1 (ruling on a Stage 2 back-to-G1 routing)
date:        2026-10-06
run:         wf_2daaeb23-497
artifact:    design/DESIGN.md revision 7 (2,906 lines), design/g1ruling.diff
             (532 lines, 27 hunks, all in DESIGN; RUNBOOK unchanged),
             frozen design/DESIGN.r7.md + RUNBOOK.r7.md, section 17
rulings:     R-1 nwords: option (a). Exact for 0-7; nwords=7 with
             rx[14..15]=ff ff means {7,8}; decoder flags nw7or8; every rule
             reads the set. In-window options (b)/(c) rejected.
             R-2 D10 acceptance test = the four 2.1 criteria (same MMIO
             accesses in order and form, same per-loop counts, no calls, no
             global loads/base reloads); three differences allowed: stack
             offsets, value-preserving register renaming, an exit delay slot
             after the exit decision and last MMIO access.
             R-3 costs restated from objdump: ~60 before S5, ~400-550 after
             S20 (~2.1-2.8 us per thread command, was 0.8); G3-low gap
             +2.1-3 us; Nop path +2-4 us and ~280 B stack. 7.3 H4 argument
             re-derived and holds; no trim.
             R-4 build_id = CRC-32 of linux_banner (= /proc/version); KRN
             compares; decoder reads BUILD/build_id.txt.
             R-5 pscol 256 KB per process, both at boot; image growth
             recorded, 48 KB bound stands, growth over it goes back to G1.
             R-6 RECS bound 34,404; 2.11 SC bytes 42-44, 46, 78-79.
attempt 1    design reviewer PASS (R-1..R-6 all accepted, diff confined;
             window re-derived in container; 6 advisories A-1..A-6, text)
             red team PASS (27 scenarios, 0 BLIND, 0 AMBIGUOUS; advisories
             K1, K3 need design text, still open)
overall:     PASS
```

```
gate:        G2
date:        2026-10-06
run:         wf_2daaeb23-497
artifact:    branch stage2-trace HEAD 48dcc1b9 (kernel code unchanged since
             attempt 1; one new commit, initramfs with the fixed pscol),
             work/pscol, work/decoder, impl/IMPLEMENTATION.md (sections 8-9),
             release build out/20261006T052947Z,
             RELEASE vmlinux-0.22.bin sha256
             4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8
             (936,714 B; build_id 0x045b27d9), package work/deploy/uClinux_TRACE
             (EBOOT.PBP c915ba8a..., kmodlib.prx 69adde5e..., pspboot.conf
             e555890d... all byte-identical to pspboot-baseline)

attempt 2    reviewer PASS (C1-C10; all 16 attempt-1 findings confirmed
             closed; no deviation touching a blocking G1 item; 3 advisories:
             N1 outside-window costs above design figures (+922 instr per
             watchdog tick ~4.2 us IRQs off, +48 per tick, panel paint
             1.03 ms), N2 G1-ruling red-team K1/K3 need design text,
             N3 decoder evidence lines print raw nwords without nw7or8)
             verifier PASS (clean rebuild, banner-only difference from the
             release; manifest exit 0; no new warnings; all symbols; window
             meets 2.1 criteria; pscol FP 0, flthdr ok, 50/50 host cases;
             decoder 37/37 incl. release-map tests; initramfs has pscol and
             rc.sysinit starts it; package ok; vmlinux.bin +44,036 B, 5,116 B
             under the bound; 4 advisories: run.sh krn argument forwarding,
             pspboot load UNVERIFIED (R20), per-build identity, costs not
             re-measured)
overall:     PASS (attempt 2 of 3)
open:        G2 advisories N1-N3 and verifier 1-4; G1-ruling advisories
             A-1..A-6 (reviewer) and K1, K3 (red team). G3 R1 requires all
             closed. Orchestrator: Stage 3 opens with a closure step
             (implementer/designer text + reviewer confirmation).
next:        Stage 3 (off-device verification) and Gate G3 need the human's
             authorization. G3 R8 is the human's signature.
```
