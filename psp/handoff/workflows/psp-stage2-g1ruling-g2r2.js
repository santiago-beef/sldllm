export const meta = {
  name: 'psp-stage2-g1ruling-g2r2',
  description: 'PSP input-death: G1 ruling on the two design conflicts G2 found (nwords D3 vs D10; D10 window wording) plus the open design-text items, then G2 attempts 2 and 3 (implementer fixes, code reviewer + verifier). Escalates on failure.',
  phases: [
    { title: 'G1 ruling: amend', detail: 'designer proposes the amendment text, diff against revision 7' },
    { title: 'G1 ruling: review', detail: 'design reviewer + red team, limited to the amended items' },
    { title: 'G2 revise', detail: 'implementer fixes every G2 finding and implements the ruling' },
    { title: 'G2 review', detail: 'code reviewer C1-C10 + verifier clean build, in parallel' },
  ],
}

const H = '/home/ubuntu/psp/handoff'
const W = '/home/ubuntu/psp/work'
const COMMON = `
You are part of a gated kernel-debugging effort. Read these in full before doing anything else:
  ${H}/DOSSIER.md (section 9 supersedes earlier sections; 9.6, 9.8 latest), ${H}/WORKFLOW.md (gates G1 and G2; Amendments at the end), ${H}/design/DESIGN.md (G1-approved revision, with the A7 text edits applied in Stage 2), ${H}/design/RUNBOOK.md, ${H}/recon/build.md, ${H}/recon/syscon.md, ${H}/gates/LOG.md, ${H}/impl/IMPLEMENTATION.md (section 0 lists the open decisions OD-1..OD-6), ${H}/gates/G2-attempt1-review.md, ${H}/gates/G2-attempt1-verify.md.
Trees: /home/ubuntu/psp/build/linux is the ORIGINAL tree, READ-ONLY, never write there (manifest ${H}/gates/baseline-tree.sha256). ${W}/linux is the git work tree, branch 'stage2-trace' (HEAD c135ecdd at G2 attempt 1). ${W}/pscol, ${W}/decoder, ${W}/build.sh (the only kernel build path; it runs git clean -fdx first), ${W}/package.sh. Container: sudo docker run --rm --platform linux/386 -v /home/ubuntu/psp:/work:ro -v ${W}:/work/work psp-build:bullseye bash -c '...' with PATH /work/staging_dir/bin:/work/staging_dir/usr/bin inside.
Target: MIPS32 LE, no MMU, no FPU, CONFIG_PREEMPT, HZ=250, gcc 4.2.1, uClibc, bFLT. The syscon timeout patch's behaviour must remain unchanged.
Hard rules: cite file:line; mark unverified claims UNVERIFIED; never edit DOSSIER.md, WORKFLOW.md or past gate reports; no hardware exists.
`

const AMEND = `${COMMON}
You are the Designer, acting on a Stage 2 "back to G1" routing. Gate G2 found that the approved design is internally in conflict on two blocking items, and left four text items open. Your job is to propose the amendment, nothing else. Freeze first: cp ${H}/design/DESIGN.md ${H}/design/DESIGN.r7.md and the same for RUNBOOK.md; at the end write diff -u of both into ${H}/design/g1ruling.diff.
Items, with the facts established by the implementers and reviewers (read IMPLEMENTATION.md section 0 and 6.1, the G2 review, the verify report, and ${H}/impl/syscon-window-diff.txt):
  R-1 (OD-1, D3 vs D10). nwords taken from the receive loop's counter at the exit is exact except when 8 words are received and the 8th is 0xFFFF: the record then says 7, and rx[14..15] = ff ff either way (the prefill). An exact count costs instructions inside S5..S20 (option b: +2 per received word in S18; option c: +1 on the 8-word exit edge, hand-written). Decide, and write the design text: either (a) define nwords in 1.2, 10.3 and 10.7 as exact for 0..7 and "7 or 8" when nwords = 7 and rx[14..15] = ff ff, with the decoder flagging the case and every rule that reads nwords stated to be unaffected (check each rule in sections 6 and 10.7 that uses nwords and say so one by one), or (b/c) approve a precise in-window cost and restate 2.1, 5.4 and 7.2 accordingly. Justify against D1-D14 and the round-3/4 red-team scenarios UL3 (link one reply behind) and H5/H8 shapes, which are the ones that read nwords.
  R-2 (OD-2, D10 wording). The window S5..S20 has the same 105 instructions, the same MMIO loads/stores in the same order and form, the same loop bodies, no calls, no global loads or base reloads; five callee-saved registers are consistently renamed and one delay slot after the -3 exit decision changed lw->nop. Decide whether the acceptance test for D10 is the 2.1/7.2 criteria (as the design itself states) and, if so, rewrite the sentence(s) that say "identical apart from stack offsets" (summary item 1, 7.2) so that text and criteria agree; state explicitly why register renaming and an off-path delay slot cannot change the timing of the on-path instruction stream on this core (or mark UNVERIFIED what you cannot show).
  R-3 (5.4/7.3 figures). objdump shows about 60 instructions before S5 (design: about 35) and about 400-550 after S20 including psc_sc_exit and psc_fill_sc (design: about 130), so about 2-2.5 us per thread command outside the window, and about 280 B more interrupt-stack depth on the Nop path. The design says G2 substitutes objdump counts. Restate 5.4 and 7.3 with the measured figures and re-derive the D10 ratio statement and the 7.3 "neither hides nor causes H4" argument with them. If you judge the exit cost must be trimmed instead, say what to trim and why; do not add mechanisms.
  R-4 (OD-3, build_id). Define stats word 2: adopt the kernel's definition (CRC-32 of the linux_banner bytes, which equal /proc/version) and require pscol's KRN check to compute the CRC-32 of /proc/version at start and compare (G2 advisory), and the decoder to take the value from the packaged build's BUILD/build_id.txt. Write it in 1.7, 8.2 and 10.1.
  R-5 (OD-5, OD-6 figures). Correct the 4.2/5.3 memory figure (binfmt_flat under CONFIG_SONY_PSP puts text in the same kmalloc: 256 KB per process, both allocated at boot, none later) and record the image growth (+43,631 B vmlinux.bin, 5,521 B under the 48 KB bound; pspboot load UNVERIFIED, R20). State whether the bound stands or needs a margin rule for later revisions.
  R-6 (stale texts found by the Interface implementer): the RECS chunk bound 34,364 vs 34,404 (4.3/10.2 vs the re-send block rule) and "SC bytes 42-46" in 2.11 (byte 45 is ms_delta). Fix both so the text matches the format.
Rules: no new mechanism; no change outside these items; put a section 17 "G1 ruling after G2 attempt 1" with one row per item: decision, sections changed, why D1-D14 still hold. Return a 15-line summary with the diff size.`

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'FAIL'] },
    rulings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, accepted: { type: 'boolean' }, d_items_checked: { type: 'string' }, evidence: { type: 'string' }, what_would_close_it: { type: 'string' } },
      required: ['id', 'accepted', 'd_items_checked', 'evidence', 'what_would_close_it'] } },
    diff_confined: { type: 'boolean' },
    report_path: { type: 'string' },
  },
  required: ['verdict', 'rulings', 'diff_confined', 'report_path'],
}
const REDTEAM_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'FAIL'] },
    scenarios: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, scenario: { type: 'string' }, what_design_records: { type: 'string' },
      result: { type: 'string', enum: ['DIAGNOSABLE', 'AMBIGUOUS', 'BLIND'] }, fix_needed: { type: 'string' } },
      required: ['id', 'scenario', 'what_design_records', 'result', 'fix_needed'] } },
    report_path: { type: 'string' },
  },
  required: ['verdict', 'scenarios', 'report_path'],
}

const G1REV = (n) => `${COMMON}
You are the G1 DESIGN REVIEWER ruling on an amendment (attempt ${n} of the ruling; the design previously passed G1 at attempt 7). You did not write the design or the code. Artifact: ${H}/design/DESIGN.md with ${H}/design/g1ruling.diff against DESIGN.r7.md; the designer's section 17.
For each of R-1..R-6 (defined in section 17 and IMPLEMENTATION.md section 0): is the decision sound, is the text now consistent with itself and with the record format, and do the blocking items it touches (R-1: D3, D10, D2; R-2: D10; R-3: D10; R-4: D13; R-5: D12; R-6: D20) still PASS? Verify R-1 by reading every rule in sections 6 and 10.7 that uses nwords yourself. Verify R-2 by reading ${H}/impl/syscon-window-diff.txt and, in the container (read-only mount), re-deriving the two listings from ${W}/out/20261006T021722Z/vmlinux and the baseline ${W}/out/20260927T204657Z/vmlinux. Verify R-3's counts from the same objdump. Confirm the diff touches nothing outside R-1..R-6 (diff_confined). Any ruling not accepted = FAIL with exactly what would close it.
Write ${H}/gates/G1-ruling${n}-review.md and return the structured result.`
const G1RED = (n) => `${COMMON}
You are the G1 RED TEAM for an amendment ruling (attempt ${n}). Artifact: ${H}/design/DESIGN.md with ${H}/design/g1ruling.diff; section 17. Scope is limited: re-run every scenario from ${H}/gates/G1-attempt7-redteam.md and earlier attempts that reads nwords, the words-received count, the stale-frame or short-frame shapes (UL3, H5, H8, N2b, H6), the perturbation argument (OE3, TE4, 7.3) or the collector's memory/image size, against the amended text; keep their ids. Add at least 3 new scenarios: one where the nwords "7 or 8" ambiguity (if adopted) is the only difference between two hypotheses; one where the measured 2-2.5 us exit cost (R-3) shifts a command's start enough to change the straddle probability or the G3-low gap; one on the KRN build_id check (R-4) misfiring. Any BLIND = FAIL; AMBIGUOUS needs a concrete fix_needed.
Write ${H}/gates/G1-ruling${n}-redteam.md and return the structured result.`
const G1AMEND2 = (rv, rt) => `${COMMON}
You are the Designer. The G1 ruling amendment was not accepted. Reviewer rulings: ${JSON.stringify(rv ? rv.rulings.filter(r => !r.accepted) : [])}. Red team non-DIAGNOSABLE: ${JSON.stringify(rt ? rt.scenarios.filter(s => s.result !== 'DIAGNOSABLE') : [])}. Full reports: ${H}/gates/G1-ruling1-review.md, ${H}/gates/G1-ruling1-redteam.md.
Revise only the items named, in place, update section 17 (add a row per finding: FIXED at <section> or CONTESTED with evidence), regenerate ${H}/design/g1ruling.diff against DESIGN.r7.md. No new mechanism. Return a 10-line summary.`

const G2_REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'FAIL'] },
    items: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, blocking: { type: 'boolean' }, result: { type: 'string', enum: ['PASS', 'FAIL'] }, evidence: { type: 'string' } }, required: ['id', 'blocking', 'result', 'evidence'] } },
    findings: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, file_line: { type: 'string' }, problem: { type: 'string' }, what_would_close_it: { type: 'string' }, blocking: { type: 'boolean' } }, required: ['item', 'file_line', 'problem', 'what_would_close_it', 'blocking'] } },
    prior_findings_closed: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, closed: { type: 'boolean' }, note: { type: 'string' } }, required: ['id', 'closed', 'note'] } },
    design_deviations_touching_G1_blocking: { type: 'array', items: { type: 'string' } },
    report_path: { type: 'string' },
  },
  required: ['verdict', 'items', 'findings', 'prior_findings_closed', 'design_deviations_touching_G1_blocking', 'report_path'],
}
const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'FAIL'] },
    build_ok: { type: 'boolean' }, build_log: { type: 'string' }, out_dir: { type: 'string' },
    sha256_vmlinux_0_22_bin: { type: 'string' }, release_sha256_in_implementation_md: { type: 'string' }, banner_only_difference: { type: 'boolean' },
    image_size_bytes: { type: 'number' }, baseline_size_bytes: { type: 'number' }, vmlinux_bin_growth_bytes: { type: 'number' },
    new_warnings_in_changed_files: { type: 'array', items: { type: 'string' } },
    symbols_missing: { type: 'array', items: { type: 'string' } },
    syscon_window_meets_2_1_criteria: { type: 'boolean' }, syscon_window_note: { type: 'string' },
    pscol_fp_regs: { type: 'number' }, pscol_flthdr_ok: { type: 'boolean' }, pscol_tests: { type: 'string' }, decoder_tests: { type: 'string' },
    initramfs_has_pscol: { type: 'boolean' }, rc_sysinit_starts_pscol: { type: 'boolean' }, package_ok: { type: 'boolean' },
    original_tree_manifest_exit: { type: 'number' },
    findings: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, problem: { type: 'string' }, what_would_close_it: { type: 'string' }, blocking: { type: 'boolean' } }, required: ['item', 'problem', 'what_would_close_it', 'blocking'] } },
    report_path: { type: 'string' },
  },
  required: ['verdict', 'build_ok', 'build_log', 'out_dir', 'sha256_vmlinux_0_22_bin', 'release_sha256_in_implementation_md', 'banner_only_difference', 'image_size_bytes', 'baseline_size_bytes', 'vmlinux_bin_growth_bytes', 'new_warnings_in_changed_files', 'symbols_missing', 'syscon_window_meets_2_1_criteria', 'syscon_window_note', 'pscol_fp_regs', 'pscol_flthdr_ok', 'pscol_tests', 'decoder_tests', 'initramfs_has_pscol', 'rc_sysinit_starts_pscol', 'package_ok', 'original_tree_manifest_exit', 'findings', 'report_path'],
}

const G2REVISE = (attempt, prior) => `${COMMON}
You are the IMPLEMENTER for G2 attempt ${attempt}. The G1 ruling on the design conflicts is in DESIGN.md section 17 and ${H}/design/g1ruling.diff (read ${H}/gates/G1-ruling*-review.md for what was accepted). Implement exactly what G1 ruled; a further deviation on a blocking item is forbidden (stop and report).
Then fix every finding of ${prior} (reviewer and verifier reports; the structured lists are in those files' tables), in particular:
  - pscol segment-name scan: 8.3 names are 11 characters with the dot at index 7, and /ms0 is mounted shortname=lower so readdir returns lower case; compare case-insensitively, count one slot per name, make run numbering and nnn behave per DESIGN 4.4; add the host tests the reviewer specified (lower-case names from an earlier boot; rrr advances; nnn restarts; one slot per file).
  - decoder/kernel map grammar: agree one grammar with an offset column used by both ${H}/impl/mkmaps.py and the decoder's BuildInfo.load; map S0 to P0; compute k and j with offsets; add a decoder test that runs on the RELEASE maps with W records at S11, S18 and LEDRMW and checks k, j and the loaded value.
  - nwords per the ruling (R-1); the D10 wording needs no code change if R-2 accepted the 2.1 criteria, else implement what was ruled.
  - KRN compares build_id per R-4 (pscol CRC-32 of /proc/version vs stats word 2); decoder takes build_id from the packaged build's BUILD/build_id.txt.
  - re-send double-counting of lost (pscol.c:932 with :1908): queue [pos0+lost, np) or equivalent, with a host vector.
  - IMPLEMENTATION.md: state per-path instruction counts (P entry, P exit, Nop) and worst-case interrupt stack depth from objdump; note the actual author of the kernel commits (the git identity 'Recon C' is a leftover config; set user.name to 'Stage 2 kernel implementer (Claude agent)' for new commits and say so); record the timeout-patch note (code moved into the wrapper, behaviour unchanged; give the reviewer a diff of the transaction body against baseline).
New commits only on 'stage2-trace' (never amend or rebase reviewed history). Rebuild from clean with ${W}/build.sh; re-run ${W}/pscol/cbuild.sh and both test suites; remove ${W}/deploy/uClinux_TRACE and re-package with PSPBOOT_DIR=/home/ubuntu/psp/pspboot-baseline; regenerate the release maps and BUILD/build_id.txt for the new build; update ${H}/impl/IMPLEMENTATION.md (new provenance and sha256, a "Response to G2 attempt ${attempt - 1}" section with one line per finding: FIXED at commit/file:line or CONTESTED with evidence). Return the per-finding list and the new release sha256.`

const G2REV = (attempt, prior) => `${COMMON}
You are the G2 CODE REVIEWER, attempt ${attempt}. You were not an implementer or the designer. Artifact: branch 'stage2-trace' in ${W}/linux (diff against 'baseline'), ${W}/pscol, ${W}/decoder, ${H}/impl/IMPLEMENTATION.md. Specification: ${H}/design/DESIGN.md as amended by the G1 ruling (section 17; ${H}/design/g1ruling.diff), which the G1 reviewer accepted in ${H}/gates/G1-ruling*-review.md.
Work the WORKFLOW.md Gate G2 checklist C1-C10 item by item with evidence (file:line, quoted code; for C1 the design field beside the struct field). Rules: any blocking FAIL = FAIL; two or more non-blocking FAILs = FAIL; missing evidence = FAIL. Specific checks as in attempt 1 (${H}/gates/G2-attempt1-review.md section headings): C1 format and capture points and the pscol segment life cycle; C2 confined diff, timeout patch behaviour, the D10 window per the ruled criteria (re-derive with objdump yourself); C3 interrupt-context safety and ring append ordering; C4 bounds everywhere including the /proc pread windows and pscol's flush assembly; C5 init order; C8 pscol (no fork, FP check, every write/fsync checked and shown, no operator input, rc.sysinit start); C9/C10.
For each finding in ${prior}: closed or not, with evidence, in prior_findings_closed. Re-check EVERY item, not only those; a fix can break another. Any deviation touching a blocking G1 item beyond what section 17 ruled: verdict FAIL and list it in design_deviations_touching_G1_blocking.
Write ${H}/gates/G2-attempt${attempt}-review.md and return the structured verdict; each finding says exactly what would close it.`

const G2VER = (attempt, prior) => `${COMMON}
You are the G2 VERIFIER, attempt ${attempt}. You were not an implementer. Reproduce, do not trust. Steps as in ${H}/gates/G2-attempt1-verify.md: (1) original tree manifest exit code; (2) clean build of 'stage2-trace' HEAD with ${W}/build.sh, sha256, and whether the difference from the release sha256 in IMPLEMENTATION.md is banner-only (cmp -l | wc -l and the banner strings); (3) new warnings in changed files vs the baseline logs; (4) symbols present at the intended sites; (5) the S5..S20 window of Syscon_cmd versus the baseline build's vmlinux, judged against the criteria the G1 ruling accepted (DESIGN 2.1/7.2 as amended): same MMIO accesses in the same order and form, same instruction counts per loop body, no calls, no global loads or base reloads; report any difference beyond those; (6) ${W}/pscol/cbuild.sh FP checks, flthdr, size; run ${W}/pscol/test and ${W}/decoder/test and give pass/fail counts, including the new release-map test; (7) initramfs from the built image contains pscol and rc.sysinit starts it; (8) image size deltas; (9) package verification (SHA256SUMS, pspboot.conf and EBOOT.PBP and kmodlib.prx byte-identical to /home/ubuntu/psp/pspboot-baseline, name collides with none of uClinux, uClinux_FIX, uClinux_WIP). Previous verifier findings to re-check: ${prior}.
Write ${H}/gates/G2-attempt${attempt}-verify.md with command lines and outputs, and return the structured result. FAIL if the build fails, manifest not 0, a symbol missing, the window fails the ruled criteria, FP registers used, initramfs lacks pscol, a test suite fails, or the package is wrong.`

// ---- G1 ruling ----
phase('G1 ruling: amend')
const amend = await agent(AMEND, { label: 'G1ruling:amend', phase: 'G1 ruling: amend', model: 'opus' })
log(`amend: ${String(amend).slice(0, 400)}`)

let rv = null, rt = null, rulingPass = false
for (let n = 1; n <= 2; n++) {
  if (n === 2) await agent(G1AMEND2(rv, rt), { label: 'G1ruling:amend#2', phase: 'G1 ruling: amend', model: 'opus' })
  phase('G1 ruling: review')
  ;[rv, rt] = await parallel([
    () => agent(G1REV(n), { label: `G1ruling:review#${n}`, phase: 'G1 ruling: review', model: 'opus', schema: REVIEW_SCHEMA }),
    () => agent(G1RED(n), { label: `G1ruling:redteam#${n}`, phase: 'G1 ruling: review', model: 'opus', schema: REDTEAM_SCHEMA }),
  ])
  rulingPass = !!(rv && rt && rv.verdict === 'PASS' && rt.verdict === 'PASS' && rv.diff_confined)
  log(`G1 ruling attempt ${n}: reviewer ${rv ? rv.verdict : 'none'} (${rv ? rv.rulings.filter(r => !r.accepted).map(r => r.id).join(',') || 'all accepted' : '?'}; confined ${rv ? rv.diff_confined : '?'}), red team ${rt ? rt.verdict : 'none'} (${rt ? rt.scenarios.filter(s => s.result !== 'DIAGNOSABLE').map(s => s.id + ':' + s.result).join(',') || 'all diagnosable' : '?'})`)
  if (rulingPass) break
}
if (!rulingPass) return { stage: 'G1 ruling', overall: 'FAIL_ESCALATE', amend, review: rv, redteam: rt }

// ---- G2 attempts 2 and 3 ----
const attempts = []
let crv = null, cvf = null
let priorDesc = `${H}/gates/G2-attempt1-review.md and ${H}/gates/G2-attempt1-verify.md`
for (let attempt = 2; attempt <= 3; attempt++) {
  phase('G2 revise')
  const resp = await agent(G2REVISE(attempt, priorDesc), { label: `G2:revise#${attempt - 1}`, phase: 'G2 revise', model: 'opus' })
  phase('G2 review')
  const [r, v] = await parallel([
    () => agent(G2REV(attempt, priorDesc), { label: `G2:review#${attempt}`, phase: 'G2 review', model: 'opus', schema: G2_REVIEW_SCHEMA }),
    () => agent(G2VER(attempt, priorDesc), { label: `G2:verify#${attempt}`, phase: 'G2 review', model: 'opus', schema: VERIFY_SCHEMA }),
  ])
  crv = r; cvf = v
  const backToG1 = !!(crv && crv.design_deviations_touching_G1_blocking.length > 0)
  const pass = !!(crv && cvf && crv.verdict === 'PASS' && cvf.verdict === 'PASS' && !backToG1)
  attempts.push({ attempt, response: resp, reviewer: crv ? crv.verdict : 'NO_VERDICT', verifier: cvf ? cvf.verdict : 'NO_VERDICT',
    reviewerFailed: crv ? crv.items.filter(i => i.result === 'FAIL').map(i => i.id) : [], reviewerFindings: crv ? crv.findings : [],
    verifierFindings: cvf ? cvf.findings : [], backToG1: backToG1 ? crv.design_deviations_touching_G1_blocking : [],
    sha256: cvf ? cvf.sha256_vmlinux_0_22_bin : null, releaseSha256: cvf ? cvf.release_sha256_in_implementation_md : null, bannerOnly: cvf ? cvf.banner_only_difference : null,
    imageSize: cvf ? cvf.image_size_bytes : null, growth: cvf ? cvf.vmlinux_bin_growth_bytes : null, windowOk: cvf ? cvf.syscon_window_meets_2_1_criteria : null,
    pscolTests: cvf ? cvf.pscol_tests : null, decoderTests: cvf ? cvf.decoder_tests : null, manifestExit: cvf ? cvf.original_tree_manifest_exit : null, pass })
  log(`G2 attempt ${attempt}: reviewer ${crv ? crv.verdict : 'none'} (${crv ? crv.items.filter(i => i.result === 'FAIL').map(i => i.id).join(',') || 'no item fails' : '?'}; ${crv ? crv.findings.length : '?'} findings), verifier ${cvf ? cvf.verdict : 'none'} (build ${cvf ? cvf.build_ok : '?'}, window ${cvf ? cvf.syscon_window_meets_2_1_criteria : '?'}, manifest ${cvf ? cvf.original_tree_manifest_exit : '?'}), back-to-G1 ${backToG1}`)
  if (pass || backToG1) break
  priorDesc = `${H}/gates/G2-attempt${attempt}-review.md and ${H}/gates/G2-attempt${attempt}-verify.md`
}
const final = attempts[attempts.length - 1]
return { stage: 'G2', overall: final.pass ? 'PASS' : (final.backToG1.length ? 'BACK_TO_G1' : 'FAIL_ESCALATE'), ruling: { amend, review: rv, redteam: rt }, attempts }
