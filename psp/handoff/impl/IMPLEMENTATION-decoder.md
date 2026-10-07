# IMPLEMENTATION notes: decoder (DESIGN.md revision 6, section 10)

Stage 2, Analyst. Date 2026-10-06. Code in `/home/ubuntu/psp/work/decoder/`
(outside the kernel tree, so `build.sh`'s `git clean` does not touch it).
Python 3.12, standard library only (`zlib`, `struct`, `mmap`, `math`, `csv`,
`json`, `bisect`). Every record layout comes from `psc_format.py`, the mirror
of `include/linux/psc_format.h` checked by `check_format.py` (exit 0 after this
work). `psc_format.py` was not changed.

Nothing here touches the kernel tree, the collector, DOSSIER.md, WORKFLOW.md,
the design or the gate reports. The original tree's manifest still checks
(`sha256sum -c`, exit 0). No deviation below touches a blocking G1 item
(D1-D14). The decoder reads the record format and does not change it, so D3
(raw data kept), D8 (contexts) and D14 (−2/−3/−4/−5 recorded distinctly) are
unaffected. Rows and thresholds follow section 6 and 10.7 (D2). Each
interpretation below changes only how the decoder reads the data.

## 1. Files

| File | Lines | Content |
|---|---|---|
| `pscdec.py` | 617 | CLI, outputs of 10.7 step 6, REPORT.md, 10.8 panel parsing |
| `pscdec_parse.py` | 625 | 10.2-10.4: chunks, CRC, run selection, extent, merge, `--raw`, raw-image rule |
| `pscdec_analysis.py` | ~1620 | 10.1, 10.3, 10.5-10.7 and the section 6 / 6.1 rows; 4.7 META repeat |
| `synth.py` | 814 | synthetic streams (Stage 3 "Decoder"), independent of the decoder |
| `test/run_tests.py` | ~520 | 26 tests; output in `TESTS.txt` |
| `README` | | usage |

Usage: `python3 pscdec.py -o OUT --build BUILD --times times.txt PSCLOG/ [--raw stick.img]`.
The exit status is one of these:

- 0: final `REPORT.md`.
- 3: RAW IMAGE REQUIRED. Only `REPORT-NOT-FINAL.md` is written.
- 2: inputs refused, with `REFUSED.txt`.

Every run also writes `classification.json`, which holds the classification triple, for scripts.

## 2. Section 10 rule → function map

| Design rule | Function(s) |
|---|---|
| 10.1 stats words 20-22 vs System.map, word 2 vs build_id; EPC analysis refused with the reason, parsing continues | `Model._build_check`; `Model.label_of` returns nothing when refused; `w_step` reports "unknown (EPC analysis refused: …)" |
| 10.2 chunk header `'<4sHHIII'`, magic at every 4-byte offset, type known, `hver` 5, `len ≤ 65,536`, bytes present, CRC (plain for FILEHDR, seeded with the nonce otherwise), else advance 4 bytes; skip PAD; drop a truncated tail chunk | `candidates`, `accept`, `crc_ok` (pscdec_parse) |
| 10.2 run selection by FILEHDR `run` and `nonce`; default highest run or `--run`; other runs listed and ignored (also for the raw rule) | `load` (pass 1 FILEHDRs, then selection), `Collection.notes`, `segments.txt` |
| 10.2 chunks of another boot fail the CRC under this run's nonce | `accept` (status `other-boot` when another known nonce verifies; `bad-crc` otherwise) |
| 10.2 confirmed extent (`segment ready` = SEG, `stop <name> <conf>`, UHB `seg` conf of the file in creation); a chunk above it is listed, not merged | `_extents`, `_bump`, `_merge` (`above_extent`, `bad.txt` "ABOVE-EXTENT" with its records) |
| 10.2 merge by (ring, seq); exact duplicates (re-sends) removed; a duplicate with different content is a conflict reported with both copies, never dropped; file names not authoritative, FILEHDR `seg` is | `_merge` (`conflicts`, `bad.txt` "CONFLICT … copy 1 / copy 2"), `_file_seg_of` |
| 10.2 RECS blocks `'<BBHI'`, ring b7 = re-send block, `recsize_div4`, one new-records block per ring per flush, at most one re-send block before it | `parse_recs` (structure violations are listed as anomalies) |
| 10.2 `--raw`: same scan, only chunks verifying under the run's nonce, grouped under the nearest FILEHDR of the run; with files, merged and records found only in the image listed | `load` (raw passes), `_file_seg_of` (raw), `_merge` phase "raw", `only_in_image` |
| 10.2 raw image primary path: EVENT `flush fail`, `stop`, `abandon`, `meta err`, `read-only`, `takeover`, `flush meta err`, `region bad`; UHB `write_errs > 0` or b30; a RECS-holding file of this run that is not 2,097,152 bytes. Final REPORT refused without `--raw` | `RAW_REQUIRED_EVENTS`, `_raw_rule`; `main` (exit 3, `REPORT-NOT-FINAL.md`) |
| 10.2 UHB `seg` decode (r7, A6-3) | `psc_format.uhb_seg_decode` (existing) |
| 10.3 record strings, `seq` 0xFFFFFFFF dropped, gaps explicit in the timeline | `norm_record`; `_merge` (`dropped_writing`); `Model._gaps`; `timeline.txt` "--- GAP" lines, `gaps.txt` (also block `lost`) |
| 10.3 16-bit links expanded to the value nearest the record's own position; if that lands on a missing seq, paired by (tick, Count), flagged | `Model._links` (`_expand`; `_link_by_time`, counted in `link_flags`) |
| 10.4 stats `'<192I'` named per 1.7 (62, 63 signed), `stats.csv`, any counter decrease reported | `parse_stats` (psc_format `STATS_FIELDS`), `_outputs` (`COUNTER_WORDS`, `stats_decreases`) |
| 10.5 fine time `tick × CPT + c`; SC end `(tick_in + dtick, c_out)`; WT `tick % 1250 == 0` asserted; long tick `c > CPT`; `wdph`; distance to nearest WT, `wb_kupdate`, collector activity; every SC with `dtick > 0` listed with the ticks it crossed and `wn ≥ 1` checked for a WT crossing; jiffies offset | `Model._sc`, `_timecheck`, `_uptime_offset` (`j_off`); `rec_line` (wdph), `distances`, `activity_ticks`, `crossings.txt` |
| 10.6 `epcmap.txt` `<start> <end> <label>`; step → P-point; S14 split into P4 / P5a by the W record's own `ack_polls`, `drain`, `drain_last`; k from `i` (P2), j from `ptr` (P6) through `regmap.txt`; Cause BD "EPC or its delay slot"; `ext_flags` b7 → step from `lc_epc`; SC `lc_flags` b4 "nested tick" | `BuildInfo.load/label`, `STEP_PPOINT`, `Model.w_step`, `reg_value`; `rec_line` annotation |
| 10.7 step 1 merged timeline, ties W before P | `timeline` (pscdec.py) |
| 10.7 step 2 template (window first P → 5 s before the earliest of O1, O2, O4, O5, excluding C0 when its times are given; ≥ 10 s and ≥ 150 polls; per command `nwords`, `rx[1]`, `rx[2]`, ranges of `ack_polls`, `drain`, duration, analog range, `gpio_in`/`spi_*` distributions, LED ORs) or `NO HEALTHY TEMPLATE` with the code expectations and `rx2 literal` | `Analysis.run`, `learn_template`, `Template.own_valid/outside/rx2/nwords`; REPORT "Template" |
| 10.7 step 3 POLL ↔ 0x33/0x08 by `sc_seq_lo`; branch recomputed vs `ri_branch`; simulated `lastKeys`, `mouseMode`, mouse deltas vs `pi_flags`/`mouse_flags`; each `mouseMode` toggle reported with its frame | `Model._links`, `Analysis.simulate_polls` (`sim_mismatch`, `toggles`) |
| 10.7 step 4 O1-O5, each with tick, `wdph`, 6.3 placements, nearest `wb_kupdate`, collector activity, S records within ± 100 ms, ± 30 s dump, operator stopwatch time | `onset_candidates`, `placements`; REPORT "Onset candidates"; `window_<cand>.txt` (−30 s … +60 s) |
| 6.3 last successful thread command, first failed one, nearest Nop: before / across / after tick 1250k (within tick 1250k only after the Nop's `c_out`) | `Analysis.placements` |
| 10.7 step 5 order: thread-stopped (H9, N4, N5, N9; takeover/PROCS and `jp_exit_tick` annotation) | `_stopped` |
| persistent states H1 (with the 9.5 variant), H2, H3, H5, N2b before H6, H6 (template `rx[2]`, `rx2 literal`, C0 reference or `no C0 reference`), N2, N3, N11 | `_states` |
| H7 (a)-(e), N6, N10 | `_h7`, `_n10` |
| H8 flags beside the state, `unassessable` without template, the declared blind spot | `_h8` |
| triggers: H4 (step, P-point, k/j, cross-check), H4 two-stage (UL7), WB, H10 (bits, window, holder), N1m, N1p, N1 (holder from `pre_*`), H10b, LEDSPLIT (loaded value, G3), N8; every WT within ± 2 cycles listed with step and both results | `_triggers`, `suspension`, `holder`, `crosscheck` |
| P-point cross-check (A1 TE2), `inconsistent` | `crosscheck` |
| guard status, `instrumentation-suspect` | `guard_status`, `run` |
| H10 conclusion, narrowed wording (A3 UL5): `H10 trigger`, `N1m`, `H10 untested in this run`, `H10 write-back mechanism refuted: …` never printed when the onset command had `ms_delta > 0` during a suspension in S5..S20, never from bit-3 counts | `h10_conclusion` |
| matching rows listed with evidence (ring, seq) and the triple; if none, H0 / UNCLASSIFIED with raw windows | `run` (`named`, `verdict`), `_report` (raw records inline plus `window_*.txt`) |
| 10.7 step 6 outputs: one CSV per record type, `stats.csv`, `uhb.csv`, `kmsg.txt`, `procs.txt`, `events.txt`, `segments.txt`, `bad.txt`, `gaps.txt`, `timeline.txt`, `REPORT.md` (classification, hazard statistics, late-start attribution, costs, loss at the pull) | `_outputs`, `_report` |
| 10.7 step 7 pre-registered harm-rate comparison (groups L/N, rates, 95 % bounds, one-sided Fisher, p < 0.01 and h_L ≥ 3) | `harm_table`, `fisher_one_sided`, `ub95` |
| 10.7 step 8 no-death inference per P-point, the n(P4)+n(P5a) ≥ 30 rule, late starts, holders | `no_death_inference`, `interleave_stats` |
| 10.8 panel photographs, EPCs mapped, placed by `NOW`, Memory Stick driver hang verdict | `panel_parse` (see DV-15) |
| 4.7 "the decoder repeats [META detection] from the files or the image", with the 4.8 sector classes | `Analysis.meta_repeat` |

## 3. Deviations and interpretations

None touches D1-D14. Each one is a reading of design text that does not settle the point, or an addition that only lists data.

| # | Where | What the decoder does | Why |
|---|---|---|---|
| DV-1 | 10.2 confirmed extent | If a file has **no** extent evidence at all (no `segment ready`, `stop` or UHB conf for its `seg`), its chunks are **merged**. The file is flagged as an anomaly "extent unverified". | Without evidence the rule cannot be applied. Dropping all of a file's records would lose real data, and another boot's chunks are already excluded by the nonce CRC (IF10 (5)). With evidence, the rule is applied exactly. |
| DV-2 | 10.2 truncated tail, Stage 3 "Truncation" | The truncated tail chunk is dropped as specified. So is a CRC-bad RECS chunk that starts exactly where the file's last accepted chunk ends (a torn last flush). The whole records inside such a chunk are additionally **listed** as `UNVERIFIED` in `bad.txt`. They are never merged. | Keeps "every complete record before the cut" visible to the analyst without merging unverified bytes. |
| DV-3 | 10.2 `--raw` grouping | A chunk's offset within its file is its image offset minus the nearest preceding FILEHDR of the run. The extent rule in raw mode relies on that. | The design gives "grouped under the nearest FILEHDR". This assumes each file's clusters are contiguous, which is likely: one file is created at a time with the sequential allocator, 4.4 (contiguity UNVERIFIED there). Records are merged by (ring, seq) regardless. |
| DV-4 | 10.2 run selection, R28 | If the selected run number carries two nonces (two boots with the same `rrr`), the decoder **refuses** with exit 2 until `--nonce` chooses one. | The design does not say what to do when one run number has two nonces; merging them is what IF10 forbids. |
| DV-5 | 10.2 "refuses a final REPORT" | The decoder writes `REPORT-NOT-FINAL.md` with a RAW IMAGE REQUIRED banner and the reasons, writes no `REPORT.md`, and exits 3. | The preliminary text helps the analyst decide on the image. It is never named REPORT.md. |
| DV-6 | operator times (RUNBOOK E5) | `--times` file of `key=m:ss` lines. The stopwatch is converted to uptime by `uptime_offset`, or by `selftest_pass` minus the `uptime_cs` of the first UHB with self-test flags b1-b8 all set. Uptime is converted to ticks through `now_jiffies − initial_jiffies` (10.5). The D1-D7 window is taken as `d0_start` … `d0_start + 70 s`. | The design names the times but not a format or the stopwatch-to-tick mapping. 70 s covers D1-D7 (61 s) plus the D0 photo. |
| DV-7 | 10.7 step 4/5, choice of the reported onset | All candidates are classified and reported. Candidates closer than 1 s are merged (names joined). The **primary** onset is the earliest candidate with a thread-stopped or state match. Failing that, it is the earliest candidate that is neither quiet nor refuted and has ≥ 10 s after it, which gives H0 / UNCLASSIFIED. If every candidate is quiet or refuted, the result is NO DEATH DETECTED and step 8 is printed. "Quiet" means healthy frames, no key change and no operator presses expected after the candidate. "Refuted" means key changes after it were delivered and consumed (`fop_read_ret` or `IN` rose). | The design says "all reported" but not which candidate the headline uses. Without the refutation, a healthy run's hands-off D8 tail would read as a death. |
| DV-8 | 6.3, 10.7 | "Own valid reply" means: `ret > 0`, `rx[0] = ret`, checksum recomputed OK, `rx[2]` equal to the template's (or the literal) code, and `nwords` and `rx[1]` equal to the template's. "First failed" is the first P record without its own valid reply from 2 s before the candidate. | These are the definitions step 7 and the cross-check use ("not its own valid reply"). |
| DV-9 | row H4 "reply-shaped `drain_last`" | Taken as `drain_last ∉ {0x0000, 0xFFFF}`. | Not defined further in the design. P4 / P5a otherwise falls back to "P4 or P5a" (R9). |
| DV-10 | row H4, UL7 | H4 is reported when a WT with `t_busy` b0 straddled the first failed command or one of the two commands before it. "H4 two-stage" is reported when a straddle at Nop k had both results valid and the first failed command straddles Nop k+1 or starts within 1 s after it. | "immediately before onset" quantified as ± 1 poll. |
| DV-11 | rows H10, N1m, N1 | Evaluated on the first failed command and the two before it (or on commands within ± 2 polls of the candidate when no command failed). | "Before onset" quantified. |
| DV-12 | row H7 (c) | The collector's own reads are taken as Δ UHB `mouse_pkts_total`. This assumes the collector makes one successful `read()` per 3-byte packet, as `telem.c:268` does. **Interface item for pscol.** | The design says "md_read_ret minus the collector's own reads" without giving the count. |
| DV-13 | row H7 (d) | Applied as written: `vcs_putchar` flat while `fop_read_ret` rises, or `console_sem` count ≤ 0 in STATS rows spanning ≥ 2 s. | If `psposk2` reads `/dev/joypad` without injecting characters while the OSK is hidden, (d) can match a state that is not a death. It is evaluated only after raw frames follow presses that were not delivered. |
| DV-14 | row N2 | When the template's own `drain` range already exceeds 0, persistent `drain > 0` is noted, not classified. | Otherwise the carry-over state would be indistinguishable from the healthy behaviour. |
| DV-15 | 10.8 | `--panel ID=L1|…|L6` is parsed by **keywords** (`DUR`, `RDR`, `PNT`, `NOW`, 8-digit hex EPCs, `PCNT`), not by the columns of `panellayout.txt`. | `panellayout.txt` is a Stage 2 deliverable of the kernel implementer and does not exist yet. When it does, `panel_parse` should switch to its columns (one function). |
| DV-16 | 10.6 `regmap.txt` | Format chosen by the decoder: lines `<label> <var> <location>`, for example `S11 i t0`, `S16 ptr a3`, `S16 rx_buf a1`, `LEDRMW val v0`. Registers can be written `rN` or by ABI name. **Interface item for the kernel implementer.** | The design lists the content but not the syntax. |
| DV-17 | 10.1 `build_id` | Taken from `--build-id` or `BUILD/build_id.txt`. Without it the EPC analysis is refused, giving the reason (as 10.1 says). | `build_id` has no defined value or source (open item from the format task). |
| DV-18 | 10.2 EVENT lines | Accepted grammar: an optional leading tick stamp (`12345 `, `t=12345 `, `[12345] `), then the words of 10.2 / 4.4 / 4.6 / 4.7. Names are matched by `T(\d{3})(\d{3})(.BIN)?`. `stop <name> <conf> …` gives the extent. **Interface item for pscol.** | The design names the words but not the line syntax. |
| DV-19 | 4.8 sector classes (META repeat) | FATM is `[fat_start + fat_length, fat_start + fats × fat_length)`. | Read literally, the text "below fat_start + fats × fat_length" would class FSINFO and the reserved sectors as FATM. |
| DV-20 | test hook | `--no-template` forces the no-template path (needed for the 8.5 N-4 row: "with the template removed"). | Not in the design. It changes nothing when unused. |
| DV-21 | thresholds | All thresholds are the constants at the top of `pscdec_analysis.py` and are printed in REPORT.md: 90 %, 10 s, ± 2 polls, ± 2 ticks, ± 2 s, ± 2 cycles, ± 100 ms, −30/+60 s, D window 70 s, p < 0.01 and h_L ≥ 3, n ≥ 30, p ≥ 0.1. | 10.7: fixed before the run (G3 R6). |
| DV-22 | 4.8 verdicts | The decoder does not re-judge flush durability or creation steps. That logic is the collector's. The decoder repeats only META (4.7). | Section 10 does not ask for it. |

Not implemented in this deliverable: none of the section 10 or section 6 rules.
N7 has no on-device signature, as the design says. It appears only as the
wording of the no-death result.

## 4. Two design inconsistencies carried over from the format task

The format task reported these (OPEN, not decided by me):

1. RECS chunk bound 34,364 against 34,404 bytes.
2. 2.11's stale "SC bytes 42-46 and 78".

The decoder is unaffected by both. It accepts any chunk of `len ≤ 65,536` (the sanity bound in 10.2) and parses SC records with the 1.2 table through `psc_format.py`.

## 5. Interface items other implementers must match

- **pscol**:
  - the EVENT line grammar (DV-18) and the exact words of 10.2;
  - `stop <name> <conf> <errno> <step>` with `conf` in bytes;
  - `segment ready <name>` carrying the name;
  - one `read()` per mouse packet (DV-12);
  - the UHB `seg` word exactly as 10.2 (r7).
- **kernel implementer**:
  - `regmap.txt` syntax (DV-16);
  - `epcmap.txt` labels `S1`..`S23`, `ENTRY`, `EXIT`, `REC`, `LEDRMW` and function names;
  - `panellayout.txt` (DV-15).
- **build_id**: one definition shared by the kernel (stats word 2), pscol (the KRN check) and the decoder (`build_id.txt` beside System.map).

## 6. Synthetic streams (`synth.py`)

`synth.py` imports `psc_format.py` only, never the decoder. It models the following independently:

- the joypad thread (`joypad_psp.c:453-659`: branch, dedupe, SELECT toggle, mouse conversion);
- the watchdog (WB at boot, a WT every 1250 ticks, with `t_busy`/`p_head`/`wn`/`w_head_lo` set when a thread command straddles it);
- M records;
- the collector:
  - capped drain;
  - flushes with RECS / UHB / STATS every 8th / PROCS every 40th / KMSG / EVENT and a PAD to 512;
  - FILEHDR + PAD = 1,536 B;
  - preallocated PAD sectors grown in 64 KB / 8 KB steps;
  - two files ahead;
  - UHB `seg` conf;
  - nonce-seeded CRCs;
  - S records for every write;
- the operator script (RUNBOOK B4, B6, C0, C1, D0-D8, with the stopwatch 10 s ahead of uptime).

Shapes after the onset, using each row's own fields:

| Shape | Post-onset behaviour |
|---|---|
| H1 | both commands −4 |
| H2 | P08 zero frame |
| H3 | P08 E3, with +16 drift in mouse mode |
| H4 | Nop at tick 32,500 straddles a P08 at S14, P4; −4 afterwards |
| H5 | −5 BUSY |
| H6 | frozen valid frame |
| H7 | frames follow presses; `fop_read_ret` flat |
| H8 | E3 plus `gpio_in` change and latch stuck |
| H9 | thread stops at stage 11; `qfree_stage` 2 on the same Q; OSK gone |
| H10 | P08 suspended at S14, `ms_delta` 4, `led_or` 0x48, overlapping S record, holder WRK |
| none | valid checksum, unknown `rx[2]` 0x42 |

There is also a healthy run, with options for:

- N-4 codes;
- a flush failure with a re-send;
- a raw image;
- other runs and nonces;
- a shortened run.

## 7. Test summary (`TESTS.txt`, 26 tests, all pass, about 50 s)

| Test | Result |
|---|---|
| Each shape named | H1, H2, H3, H5, H6, H9 as the state. H4 as trigger H4 with "→ P4", "allowed for P4" and "across (wn 1)". H7 stage (b). H8 flags (`gpio_in`, `ack_polls` always 0) beside state H3. H10 as trigger, window S13..S20 (G3 high). |
| Healthy | NO DEATH DETECTED. No-death inference printed. |
| Unmatched stream | `H0 / UNCLASSIFIED`, raw records inline, `window_*.txt` written |
| N-4 (healthy `rx[2]` 0x28) | H6 with the template. With the template removed, `rx2 literal` flagged and not H6. |
| Truncation at 50 random offsets (40 in the written part of file 1, 10 anywhere) | 436,757 complete records checked. 0 lost from complete chunks. Nothing after the cut merged. Every complete record of the cut chunk listed as UNVERIFIED. |
| Two boots | Run 1 files listed and ignored; records identical to run 2 alone. A boot-A RECS chunk inside a boot-B file listed OTHER-BOOT, not merged, 0 conflicts. One run number with two nonces refused (exit 2); with `--nonce`, only that boot is decoded. |
| `--raw` | Image only gives the same records and classification as the files. A short copy is refused without `--raw` (exit 3, no REPORT.md) and is final with it, with records listed as only in the image. An EVENT `flush fail` is refused without `--raw`; with it, re-sent duplicates are removed and there are 0 conflicts. |
| Merge | A modified duplicate gives CONFLICT with both copies. A valid chunk above the UHB-confirmed extent is listed, not merged. |
| META repeat | FSINFO, FAT1, FATM and DIR classes. Fewer than 5 failures, good writes or a whole-stick burst give none. |
| Robustness | Random bytes refused (no FILEHDR). 300 bit flips give no crash, 248 CRC-bad chunks listed and 0 conflicts. A panel photograph with its EPC in `ms_wait_ready` and preempt count 1 is reported as a Memory Stick driver hang. |

Per-poll simulation: 0 mismatches on every synthetic shape (the decoder's and
the synth's independent driver models agree).

Limits of these tests: the shapes are the design's signatures as I read them,
generated by the same analyst who wrote the decoder (WORKFLOW gives Stage 3 to
the verifier, who should add independent vectors). There is no VFAT-FI and no
real hardware data. Speed on a 35-minute run was not measured: the synthetic
runs are about 4 minutes (8,400 P records) and decode in about 1.2 s.
