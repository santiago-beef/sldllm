export const meta = {
  name: 'psp-stage3-g3',
  description: 'PSP input-death: Stage 3 off-device verification and the agent-side checks of Gate G3 (R1-R7). Closes open advisories, runs the six Stage 3 tests plus the R20 pspboot-size analysis, has a fresh agent play operator on the runbook, then a verifier checks R1-R7. R8 (human signature) is never marked.',
  phases: [
    { title: 'Closure', detail: 'close G1-ruling/G2 advisories with text; reviewer confirms each' },
    { title: 'Tests', detail: 'ring logic, decoder, truncation, volume, package, initramfs, R20 in parallel' },
    { title: 'Runbook', detail: 'packager fills the sha256; fresh agent plays operator' },
    { title: 'G3 verify', detail: 'verifier checks R1-R7 against evidence' },
  ],
}

const H = '/home/ubuntu/psp/handoff'
const W = '/home/ubuntu/psp/work'
const COMMON = `
You are part of a gated kernel-debugging effort. Read these in full first:
  ${H}/DOSSIER.md (section 9 supersedes earlier sections), ${H}/WORKFLOW.md (Stage 3, Gate G3, Amendments), ${H}/design/DESIGN.md (with section 17, the G1 ruling), ${H}/design/RUNBOOK.md, ${H}/gates/LOG.md, ${H}/impl/IMPLEMENTATION.md, ${H}/gates/G2-attempt2-review.md, ${H}/gates/G2-attempt2-verify.md, ${H}/gates/G1-ruling1-review.md, ${H}/gates/G1-ruling1-redteam.md.
Trees: /home/ubuntu/psp/build/linux is the ORIGINAL tree, READ-ONLY (manifest ${H}/gates/baseline-tree.sha256; check exit 0 at the end of your work). ${W}/linux is the work tree, branch 'stage2-trace', released at HEAD 48dcc1b9. ${W}/pscol, ${W}/decoder, ${W}/build.sh, ${W}/package.sh, deploy package ${W}/deploy/uClinux_TRACE. Container: sudo docker run --rm --platform linux/386 -v /home/ubuntu/psp:/work:ro -v ${W}:/work/work psp-build:bullseye bash -c '...' with PATH /work/staging_dir/bin:/work/staging_dir/usr/bin inside.
THE RELEASED IMAGE IS FROZEN: vmlinux-0.22.bin sha256 4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8. Do not change kernel code, pscol, or the package contents. If you find that something would need such a change, STOP and report it as a blocking finding; do not make it.
Hard rules: cite file:line; mark unverified claims UNVERIFIED; never edit DOSSIER.md, WORKFLOW.md, gates/LOG.md or past gate reports (the orchestrator, i.e. the human's project manager, appends to LOG.md); never mark or imply G3 R8 (the human operator signs it); no hardware exists. Stage 3 evidence goes under ${H}/stage3/ (create it; logs in ${H}/stage3/logs/).
`

const CLOSE_SCHEMA = {
  type: 'object',
  properties: {
    items: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, closed: { type: 'boolean' }, how: { type: 'string' }, needs_kernel_change: { type: 'boolean' } },
      required: ['id', 'closed', 'how', 'needs_kernel_change'] } },
    report_path: { type: 'string' },
  },
  required: ['items', 'report_path'],
}
const CONFIRM_SCHEMA = {
  type: 'object',
  properties: {
    items: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, confirmed_closed: { type: 'boolean' }, evidence: { type: 'string' }, what_would_close_it: { type: 'string' } },
      required: ['id', 'confirmed_closed', 'evidence', 'what_would_close_it'] } },
    all_closed: { type: 'boolean' },
    report_path: { type: 'string' },
  },
  required: ['items', 'all_closed', 'report_path'],
}
const TEST_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'FAIL', 'BLOCKED'] },
    summary: { type: 'string' },
    counts: { type: 'string' },
    log_paths: { type: 'array', items: { type: 'string' } },
    findings: { type: 'array', items: { type: 'object', properties: {
      problem: { type: 'string' }, what_would_close_it: { type: 'string' }, blocking: { type: 'boolean' } },
      required: ['problem', 'what_would_close_it', 'blocking'] } },
    report_path: { type: 'string' },
  },
  required: ['verdict', 'summary', 'counts', 'log_paths', 'findings', 'report_path'],
}
const R_SCHEMA = {
  type: 'object',
  properties: {
    checks: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, result: { type: 'string', enum: ['PASS', 'FAIL', 'HUMAN'] }, evidence: { type: 'string' }, what_would_close_it: { type: 'string' } },
      required: ['id', 'result', 'evidence', 'what_would_close_it'] } },
    open_for_human: { type: 'array', items: { type: 'string' } },
    verdict: { type: 'string', enum: ['PASS_PENDING_R8', 'FAIL'] },
    report_path: { type: 'string' },
  },
  required: ['checks', 'open_for_human', 'verdict', 'report_path'],
}

// ---------- Phase 1: closure ----------
const CLOSER = `${COMMON}
You are the CLOSER (designer/implementer role, text only). G3 R1 requires every open advisory closed with reviewer confirmation. Open list from ${H}/gates/LOG.md (G2 attempt 2 entry "open:"): G2 N1-N3 (N1 outside-window costs above design figures; N2 K1 and K3 from the G1-ruling red team need design text; N3 decoder evidence lines print raw nwords without nw7or8), verifier advisories 1-4 (run.sh krn argument forwarding, pspboot load of the larger image UNVERIFIED R20, per-build identity, costs not re-measured), G1-ruling reviewer advisories A-1..A-6 and red-team K1, K3. Find the exact wording of each in the G1-ruling and G2 attempt-2 reports.
For each: close it with the narrowest change that is NOT a kernel/pscol/package change: design or runbook text (record in IMPLEMENTATION.md a new section "Stage 3 closure" and, for design text, a clearly marked addendum at the end of DESIGN.md section 17 or a new section 18, with a unified diff in ${H}/stage3/closure.diff), decoder or test-script fixes in ${W}/decoder or ${W}/pscol/test (those are tooling, not the released image; commit on branch 'stage2-trace' as new commits with git user.name 'Stage 3 closer (Claude agent)'; kernel and initramfs inputs must not change, and you must show by sha256 that the released vmlinux-0.22.bin is untouched), or measurement (re-measure costs from the released vmlinux with objdump). If an advisory can only be closed by a kernel, pscol or package change, set needs_kernel_change true, do not make the change, and say what the human must decide. The R20 item (pspboot load of the larger image) is handled by a separate agent: for it, only record a pointer.
Write ${H}/stage3/closure.md with one row per advisory: id, wording, closed or not, how, file:line. Return the structured list.`

const CONFIRMER = (closure) => `${COMMON}
You are the CLOSURE REVIEWER. You did not write the closures. The closer reports: ${JSON.stringify(closure)}. Evidence: ${H}/stage3/closure.md, ${H}/stage3/closure.diff, the amended DESIGN.md/IMPLEMENTATION.md, new commits on 'stage2-trace' (git log 48dcc1b9..HEAD).
Independently confirm each advisory is closed: re-read the original wording, then the fix; re-run any re-measurement yourself. Confirm sha256 of ${W}/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin is still the frozen value and the whole package still matches its SHA256SUMS, and that the diff of branch 'stage2-trace' since 48dcc1b9 touches nothing that feeds the kernel image or initramfs (show the file list). An item whose closure changes the image or needs the human is not confirmed. Closure is yours alone to confirm: be strict, a text that merely restates the advisory is not a closure.
Write ${H}/stage3/closure-confirm.md and return the structured result.`

// ---------- Phase 2: tests ----------
const RING = `${COMMON}
Stage 3 test: RING LOGIC. Compile the ring and record code from ${W}/linux (the real kernel source files that implement the ring and the record writer, not a rewrite; extract/include with a stub for register and MMIO access, host gcc, build with -m32 or -m64 as needed but state the endianness handling) under ${H}/stage3/ring/ with a Makefile and a README stating how to run it. Drive it with synthetic sequences for each of H1..H8 from DESIGN.md (the hypothesis list and what each should record), including an interrupt arriving mid-record (simulate by invoking the IRQ-side append from inside the process-side append at each possible point, or the nearest faithful model of the real ordering rules in DESIGN section on ring append ordering). Check record format byte-for-byte against DESIGN 1.x, wrap-around, overflow/lost accounting, and the nwords rule as ruled. Write the produced dumps to ${H}/stage3/dumps/ (one per scenario, named H1..H8, plus 'mid-irq-*', plus one 'unclassified' sequence matching no hypothesis) for the decoder test. Report exact counts. Mark anything the host cannot model as UNVERIFIED.
Write ${H}/stage3/ring/REPORT.md; return the structured result.`

const DECODER = `${COMMON}
Stage 3 test: DECODER. Wait-free: the ring test agent writes dumps to ${H}/stage3/dumps/ in parallel with you, so FIRST build your own independent dump generator from the design's record format (do not copy the ring agent's) and generate dumps for each of H1..H8 and for a sequence matching none, under ${H}/stage3/decoder-dumps/. Feed them through the analyst's decoder in ${W}/decoder, using the RELEASE maps from the packaged build (${W}/deploy/uClinux_TRACE/BUILD). The decoder must name the right hypothesis for each and print 'unclassified' with raw data for the one matching none; also test the nw7or8 case from the G1 ruling, and the build_id check (wrong build_id must be flagged, not silently decoded). Then, if ${H}/stage3/dumps/ has files by the time you finish, run the decoder over those too and report agreement or disagreement per file (a disagreement between independently generated dumps and the decoder is a finding, say which side deviates from DESIGN.md). Write ${H}/stage3/decoder/REPORT.md with the command lines and outputs; return the structured result.`

const TRUNC = `${COMMON}
Stage 3 test: TRUNCATION. Take real decoder-valid dumps (generate with the host tools in ${W}/decoder or ${W}/pscol/test; at least 6 dumps covering a short, a wrapped, and a segment-boundary-spanning case, including one that has the stats/header words) and cut each at EVERY byte offset (and for large ones at every offset within 64 bytes of each record boundary plus 500 random offsets with a fixed seed). As a battery pull would: also test cuts that leave a partially written segment file plus an older complete segment. For each cut the decoder must (a) not crash, (b) recover every complete record before the cut, byte-identical to the uncut decode, (c) say the dump is truncated. Count the cases. Write the script under ${H}/stage3/trunc/ with README; report to ${H}/stage3/trunc/REPORT.md; return the structured result.`

const VOLUME = `${COMMON}
Stage 3 test: VOLUME. Simulate 15 minutes at 20 polls per second of the collector path (pscol's flush logic and the record rate implied by DESIGN: events per poll, the watchdog cadence of 5 s, panel/stats words as defined) on the host using the real pscol source with stubs. The output size on the simulated stick must match the design budget (DESIGN's size section, 4.3/10.2 and the segment life cycle in 4.4): report total bytes, file count, per-file size, the segment numbering, and whether the ring overflows or 'lost' is nonzero at the design's flush period. Run it three times: nominal; with a stalled flush (stick write blocked for 10 s, then released); with write failure injected (the collector must show the failure on screen per C8, in the stubs' screen record). Write under ${H}/stage3/volume/ with README, REPORT.md; return the structured result.`

const PACKAGE = `${COMMON}
Stage 3 test: PACKAGE and INITRAMFS (two items, one agent). PACKAGE: ${W}/deploy/uClinux_TRACE must contain the kernel, pspboot (EBOOT.PBP, kmodlib.prx) and pspboot.conf with the right paths: read pspboot.conf and show every path it names exists inside the folder layout exactly as the PSP will see it (PSP/GAME/uClinux_TRACE/...), compare to the baseline 'uClinux' layout in /home/ubuntu/psp/pspboot-baseline and the known-good stick layout described in DOSSIER; the name collides with none of uClinux, uClinux_FIX, uClinux_WIP (and no other folder in /home/ubuntu/psp that the user might have on the stick; list them); SHA256SUMS verify; EBOOT.PBP, kmodlib.prx, pspboot.conf byte-identical to the baseline; PROVENANCE.txt matches the gate log. Also check the folder name and file names are 8.3/FAT-safe where the PSP needs them, no stray files (.DS_Store, backup files), and total size. INITRAMFS: unpack the embedded cpio from the built image itself (find it inside vmlinux-0.22.bin of the PACKAGE, not from the build tree: locate the cpio magic 070701, extract with cpio in the container or host, handle compression if the initramfs is compressed), confirm pscol is present, executable, a valid bFLT with FP count 0 (flthdr), the same bytes as ${W}/pscol output, and that rc.sysinit (show the lines) starts it, in the right order relative to the input/joypad and syscon start, with no operator input needed. Write ${H}/stage3/package/REPORT.md with outputs; return the structured result.`

const R20 = `${COMMON}
Stage 3 item: R20, the residual 'pspboot loading a +37 KB image is UNVERIFIED'. Establish, from evidence (the pspboot sources or binaries in /home/ubuntu/psp, the dossier, ${H}/recon/, strings/objdump of EBOOT.PBP and kmodlib.prx, pspboot.conf, the known load addresses and the memory map), what limits the size of the kernel image pspboot loads: a fixed buffer, load address collision with the initramfs/bss or the 48 KB bound mentioned in IMPLEMENTATION.md, a memory-stick read size, a PSP kernel-mode allocation. Show where the 48 KB bound came from and recompute the actual headroom for the released image (vmlinux-0.22.bin 936,714 B vs the baseline image; also the in-memory size after decompress/relocation: _end vs the load range, from System.map in BUILD and the baseline's). If you can construct a host-side check that proves the image fits wherever its load range must not overlap something (e.g. an ELF/linker map check of _text.._end vs the reserved regions), do and attach it. Verdict PASS only if the limit is established AND the image is under it with stated margin; otherwise BLOCKED with exactly what the human can do (e.g. a smaller-image fallback build, or accept the residual). Write ${H}/stage3/r20/REPORT.md; return the structured result.`

// ---------- Phase 3: runbook ----------
const PACKAGER = `${COMMON}
You are the RUNBOOK PACKAGER. The runbook ${H}/design/RUNBOOK.md has a line "SHA256 vmlinux-0.22.bin = <filled in by the Stage 3 packager; ...>" (about line 168). Fill it with the released sha256, and fill every other placeholder that Stage 3 owns (search for '<' placeholders, 'TBD', 'Stage 3'); do NOT change any step's meaning. Copy the result to the stick-ready location ${W}/deploy/uClinux_TRACE/RUNBOOK.md only if the runbook says it travels with the package (check; the package SHA256SUMS must then be regenerated, and say so). Record every edit as a diff in ${H}/stage3/runbook.diff. Also verify: R5 abort rule exists (self-test indicator not seen within a stated time of boot -> power off and report, explicitly not counting as the run) and name its section. Return a 10-line summary with the sha256 you filled in and the check you ran to confirm it equals the package file.`

const OPERATOR = `${COMMON}
You are playing the HUMAN OPERATOR for G3 R4. You did not write ${H}/design/RUNBOOK.md and must not read DESIGN.md, DOSSIER.md or any implementation file for help: you only get the runbook, the contents of the package folder ${W}/deploy/uClinux_TRACE (listing, not source), and the facts a real person at a PSP-1001 would have: a PC with a card reader, a Memory Stick, a PSP with battery you can pull, a phone camera, a clock. (Ignore the 'read these first' list above for this task, except the hard rules.) Walk the runbook end to end, step by step, as someone who has never seen it: at each step write what you would physically do, what you would expect to see, and whether any instruction is ambiguous, missing a precondition, uses a term you cannot know, can be done in two ways, or has an unstated wait time or abort condition. Specifically probe: which files go where on the stick and what NOT to overwrite (baseline 'uClinux' folder); how to confirm the copy; the boot and the self-test indicator and its time limit; what to do for each outcome (no indicator, indicator then death, no death within the time limit, panel shows something unexpected); what to record (times, photographs, 'time of death as perceived'); what to bring back from the stick and where the files are; the battery-pull moment relative to file sync; how a wrong step could destroy the evidence. Write ${H}/stage3/operator-readthrough.md and return the structured result with each ambiguity as a finding (blocking if a careful person could do the wrong thing or lose the run).`

// ---------- Phase 4: G3 verify ----------
const VERIFIER = (ctx) => `${COMMON}
You are the G3 VERIFIER. Check R1-R7 of WORKFLOW.md Gate G3 against evidence; R8 is the human's: return result 'HUMAN' for R8 and never PASS it. Reproduce key facts yourself rather than trusting reports.
R1: G0, G1, G2 PASS in gates/LOG.md with no open findings: closure confirmation (${H}/stage3/closure-confirm.md) must show all closed. R2: every Stage 3 test passed with logs attached (reports under ${H}/stage3/*/REPORT.md; read the logs, re-run at least the decoder and truncation scripts yourself). R3: sha256 in the gate log == sha256 of the file in ${W}/deploy/uClinux_TRACE (compute both). R4: ${H}/stage3/operator-readthrough.md has no unresolved blocking ambiguity (if the runbook was edited to resolve any, a re-read is needed: say so). R5: abort rule present. R6: decoder exists and tested now. R7: dossier open questions Q3, Q4, Q5, Q7 are either answered in the dossier or the design is shown not to depend on the answer; YOU MUST NOT ANSWER THEM: list each with its text, whether the design depends on it, and if so what the human must decide, in open_for_human. Also list the R20 outcome and every residual the human must accept at R8, in plain language.
Stage results so far: ${JSON.stringify(ctx)}.
Confirm the original tree manifest exit code 0. Write ${H}/stage3/G3-verify.md and return the structured result. verdict PASS_PENDING_R8 only if R1-R7 all PASS.`

// ---------- run ----------
phase('Closure')
const closure = await agent(CLOSER, { label: 'closure:close', phase: 'Closure', model: 'opus', schema: CLOSE_SCHEMA })
let confirm = null
if (closure) {
  confirm = await agent(CONFIRMER(closure), { label: 'closure:confirm', phase: 'Closure', model: 'opus', schema: CONFIRM_SCHEMA })
}
log(`closure: ${closure ? closure.items.filter(i => i.closed).length + '/' + closure.items.length + ' closed' : 'none'}, kernel-change needed: ${closure ? closure.items.filter(i => i.needs_kernel_change).map(i => i.id).join(',') || 'none' : '?'}; confirmed all_closed=${confirm ? confirm.all_closed : '?'}`)

// Tests do not depend on closure (the image is frozen), so run them regardless and report.
phase('Tests')
const specs = [
  ['ring', RING], ['decoder', DECODER], ['truncation', TRUNC], ['volume', VOLUME], ['package+initramfs', PACKAGE], ['R20', R20],
]
const tests = await parallel(specs.map(([name, prompt]) => () => agent(prompt, { label: `test:${name}`, phase: 'Tests', model: 'opus', schema: TEST_SCHEMA })))
const testSummary = specs.map(([name], i) => ({ name, verdict: tests[i] ? tests[i].verdict : 'NO_VERDICT', counts: tests[i] ? tests[i].counts : null, blocking: tests[i] ? tests[i].findings.filter(f => f.blocking).map(f => f.problem) : ['agent returned nothing'], report: tests[i] ? tests[i].report_path : null }))
log('tests: ' + testSummary.map(t => `${t.name}=${t.verdict}`).join(', '))

phase('Runbook')
const packaged = await agent(PACKAGER, { label: 'runbook:package', phase: 'Runbook', model: 'opus' })
const operator = await agent(OPERATOR, { label: 'runbook:operator-readthrough', phase: 'Runbook', model: 'opus', schema: TEST_SCHEMA })
log(`operator read-through: ${operator ? operator.verdict + ', blocking ambiguities: ' + operator.findings.filter(f => f.blocking).length : 'none'}`)

phase('G3 verify')
const ctx = { closure: confirm, tests: testSummary, packager: String(packaged).slice(0, 1200), operator: operator ? { verdict: operator.verdict, findings: operator.findings } : null }
const g3 = await agent(VERIFIER(ctx), { label: 'G3:verify', phase: 'G3 verify', model: 'opus', schema: R_SCHEMA })

return { stage: 'Stage 3 + G3 (agent side)', overall: g3 ? g3.verdict : 'NO_VERDICT', closure, confirm, tests: testSummary, operator, g3, packager: String(packaged).slice(0, 1200) }
