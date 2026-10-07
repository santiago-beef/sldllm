# Stage 3 VOLUME test: harness, how to run it, what it models

WORKFLOW.md Stage 3, "Volume": simulate 15 minutes at 20 polls per second of the
collector path; the output on the simulated Memory Stick must match the design
budget (DESIGN.md 5.1, 4.3, 4.4, and the 8.5 "Volume" row). Every run's verdict,
with each check's evidence, is in [results/RESULTS.md](results/RESULTS.md) (generated
by `src/summarize.py`; machine-readable `results/verdicts.json`). The narrative report
(verdict, the three required runs, the budget comparison, findings F1-F6) was returned
to the orchestrator as this agent's structured result: this environment does not let
the agent write a REPORT.md file. Per-run evidence is in `results/<run>/`, logs in
`/home/ubuntu/psp/handoff/stage3/logs/volume-*.log`.

## Run it

```
cd /home/ubuntu/psp/handoff/stage3/volume
src/run_all.sh [BIGDIR]      # about 1 minute; BIGDIR defaults to this session's scratchpad
```

`run_all.sh` builds the harness (`src/Makefile` -> `build/volsim`), checks that the
budget method reproduces the design's published figures, runs 21 scenarios, checks
every simulated stick (`src/check_stick.py`), and writes `results/RESULTS.md`
and `results/verdicts.json` (`src/summarize.py`). The simulation is deterministic: a
re-run reproduces every stick file, every produced-record dump and every summary byte
for byte (checked; `results/R1-nominal-20pps-52k/stick.sha256`).

One scenario by hand:

```
build/volsim name=R1 out=/tmp/r1/out big=/tmp/r1/big polls=20 speed=52 cl=32
python3 src/check_stick.py /tmp/r1/big /tmp/r1/out
```

volsim options: `polls=20|17.86` (20/s = 50 ms period; 17.86/s = 56 ms, the msleep(50)
period of dossier 9.1), `speed=` stick KB/s, `cl=32|64` cluster KB, `start=` worker
start s (30), `dur=` collection s after worker start (900), `cpu=` loop body ms
besides I/O (30), `press=` TRIANGLE press ms uptime (100000), `stall_at= stall_ms=`
(`stall_np=1`: the joypad thread is held too), `out_at= out_ms=` (every write fails),
`fail1_at=` (one flush data segment fails), `wfail_at= wfail_ms=` (write() returns -1).

## Files

| Path | What |
|---|---|
| `src/volsim.c` | The harness: the `os_*` layer of `pscol.h` as a simulated PSP (kernel `/proc/psc`, vfat on a Memory Stick, framebuffer with pixel read-back), and the driver loop that replays `worker_main` (pscol.c:2966-2976, which `-DPSCOL_HOST` compiles out) |
| `src/font_from_telem.py` | Extracts telem.c's 5x7 font (`telem/telem.c:73-133`) for the screen OCR, so the screen record does not rely on pscol's own copy; reports that the two tables are identical |
| `src/check_stick.py` | Decodes the simulated stick with the analyst's parse layer (`work/decoder/pscdec_parse.py`), compares every record with what the kernel model produced, walks every chunk for the byte accounting, checks the S ring |
| `src/design_budget.py` | The DESIGN 5.1 / 15.6 budget method with the poll rate and tick period as parameters; self-check: reproduces every published figure (7,598 B/s, 6.84 MB, 4,736 creation writes per file, 40.7 sector writes/s, ...) |
| `src/summarize.py` | Verdicts per run (criteria listed in its header), `results/RESULTS.md`, `results/verdicts.json` |
| `src/run_all.sh`, `src/Makefile` | Build and run everything |
| `results/<run>/summary.json` | Harness totals: ticks, bytes handed to `write()`, S records and sectors by operation and class, backlog maxima, pscol's own counters, panel model episodes, screen statistics |
| `results/<run>/check.json` | Stick verification and byte accounting (per file, per chunk type, per ring) |
| `results/<run>/screen.log` | The screen record: the ten HUD lines read back from the framebuffer pixels (colour mask under a line: `G` green, `R` red, `W` white) whenever a line changes other than in its digits, and every 60 s; `PANEL(model)` lines for the kernel stall panel |
| `results/<run>/events.log` | Every pscol EVENT line, with simulated time and tick |
| `results/<run>/ticks.csv.gz` | One row per collector tick: period, I/O time, bytes flushed / preallocated, S records, ring backlogs, lost, write_errs, hold, catch-up, active/creating file, the kernel's durable age, HUD lines 1, 6, 7, 8 as read from the pixels |
| `results/<run>/files.txt` | Every file the worker created: slot, inode, clusters, sizes in memory and in the directory entry on the stick |
| `results/R1/R2/R3 (52k)/stick.tgz`, `stick.sha256`, `produced.sha256` | The simulated stick of the three required runs (Mac-copy view `PSCLOG/` and every inode's raw data `raw/`), for re-decoding |

## What the harness models

Compiled code under test: `/home/ubuntu/psp/work/pscol/pscol.c` and `pscol.h`
**unchanged** (sha256 `1e89ac0a…` and `50afcf0a…`, IMPLEMENTATION.md 5.4), with
`-DPSCOL_HOST`, and the kernel header `work/linux/include/linux/psc_format.h`
(`ec4058ee…`, unchanged since `ca7dac0a`). The harness is written for Stage 3 and
shares only the `os_*` interface with the implementer's `pscol/test/sim.c`.

- **Kernel.** The five rings with this tree's reader (`psc.c:976-1033`: whole
  records, overwritten records skipped to the oldest, skip-and-count, `*ppos` for
  `read()`, a local position for `pread()`, `last_reader_tick` even for zero bytes),
  `llseek` (`psc.c:1035-1058`), the stats block built at each read (DESIGN 1.7),
  `ctl` ops 1-4 (`psc.c:1147-1195`). Records: per poll a 0x33 and a 0x08 P record and
  a POLL record; a WT record at every tick 1250k; WB at boot; one boot M record; S
  records from the stick model. `build_id` = CRC-32 of the packaged
  `BUILD/banner.txt` (0x045b27d9), the same bytes `/proc/version` returns.
- **Kernel stall panel.** Its condition is evaluated at every tick 125 mod 250 exactly
  as `psc_panel.c:301-338` does (durable age > 3 s, reader age > 3 s, test active),
  including the test paints that `PANEL` counts. This is a **model**; the kernel's
  panel code is not executed. The screen record shows its episodes as `PANEL(model)`.
- **vfat and the Memory Stick.** Sequential cluster allocation from a free cluster
  after the PSCLOG directory; a FAT1 and a mirror sector dirtied per allocated
  cluster; a page cache with per-buffer mapped, dirty and uptodate state; `fsync` in
  this tree's order (data pages; the file's own directory entry, written at once;
  then FSINFO, FAT1, FAT2 and other dirty directory sectors; DESIGN 4.4 step 4,
  `fs/sync.c:55-76`, `fs/fs-writeback.c:158-174`). Data pages as `fs/mpage.c:464-690`
  writes them: a page whose buffers are all mapped, dirty and uptodate becomes one bio
  segment (contiguous pages merged, at most 255 sectors, `include/linux/blkdev.h:798`,
  `fs/bio.c:309`); a page with a clean mapped buffer goes through
  `block_write_full_page`, one bio per dirty buffer (`fs/buffer.c:1584-1736`). One S
  record per bio segment (`drivers/block/ms_psp.c:258-292` in the work tree); a
  failed segment ends its bio (`:282-287`) after 10 tries of its first sector with
  `mdelay(1)` (`:319-335`). FIBMAP, `fadvise(DONTNEED)` of whole pages
  (`mm/fadvise.c:98-108`), read-back by whole page. The PSCLOG directory buffer is
  re-read from the stick after a failed write, and the inode cache is keyed by slot,
  so a failed step-0 entry produces an alias (DESIGN 4.4 step 1). Geometry: FAT32,
  partition start 63 (`telem/logs-from-stick/kmsg.txt`: `ms0 [0000003f-0e86bfc1]`),
  32 reserved sectors, FSINFO at 1.
- **Time.** A simulated clock: tick = 4 ms, Count = 220.9 MHz (`psp.c:38`). Every stick
  segment takes `bytes / speed`, and the collector loop takes 30 ms of CPU plus the
  200 ms `nanosleep` plus its I/O. That is DESIGN 15.6's model ("tick = 0.23 s +
  I/O / speed"). The joypad thread polls at a fixed period regardless of I/O, which
  is the upper bound on record volume.
- **Faults.** A stalled flush: the first flush data segment at or after the given time
  blocks for N s, then completes; the thread keeps polling (worst case for the rings),
  or with `stall_np=1` it is held too. A whole-stick write outage: every write segment
  in the window fails (data and metadata). One failed flush data segment.
  `write()` returning -1 in a window.
- **Screen.** `/dev/fb0` is 512 x 272 x 32-bit with stride 2048. After every tick the
  ten HUD lines are read back **from the pixels**, using telem.c's font and each
  glyph's colour. The text is compared with pscol's own line model `hud[]` (no
  difference on any tick of any run). Writes into rows 176-271, the kernel's band,
  are counted (none).

## Model limits (what this test cannot show)

- No hardware. Stick timing is the design's linear model. Real per-command latency,
  the real Memory Stick's error behaviour, the real `fsync` duration and the CPU cost
  of a collector tick are UNVERIFIED (DESIGN R8, R3).
- The vfat behaviour is modelled from this tree's source, not executed. It covers the
  order of writes in `fsync`, the bio segmentation and the re-read after a failed
  buffer write. It does not cover FAT contents (a lost FAT1 link is only counted,
  `fat_stale_alloc`), `pdflush` writeback, memory reclaim or readahead. DESIGN 8.5's
  VFAT-FI harness (a Malta guest running this tree's `fs/fat`) would be the
  executed-code counterpart (R18); it is not this test.
- The joypad thread polls at a fixed period even while the driver holds the CPU
  without preemption during a transfer. Real polls would be delayed, so the simulated
  record volume is an upper bound.
- The supervisor and the takeover are not modelled; a stall shorter than 30 s cannot
  trigger the takeover (both ages must exceed 30 s, DESIGN 4.2).
- `/proc` text (stat, status, meminfo, uptime) is synthesised in this tree's formats
  (`fs/proc/array.c:413-461`). The PROCS chunk size therefore depends on the stub
  (881 B per chunk here).
- The record contents are synthetic. The analyst's decoder classifies them as
  `H0 / UNCLASSIFIED`, which is meaningless for this test. The decoder's
  classification is tested by the decoder agent.
