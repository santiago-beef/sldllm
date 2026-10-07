# IMPLEMENTATION.md: Stage 2 (integrated)

Integrator, Stage 2, 2026-10-06. This document merges the three
implementers' notes into one record for Gate G2:

- `IMPLEMENTATION-kernel.md` (kernel, branch `stage2-trace`);
- `IMPLEMENTATION-pscol.md` (collector, `/home/ubuntu/psp/work/pscol/`);
- `IMPLEMENTATION-decoder.md` (decoder, `/home/ubuntu/psp/work/decoder/`).

It adds the integration steps: the initramfs, the release build, the image
check, the size check and the package. Those three notes stay as the detailed
records. Where this file and a note disagree on a fact about the release
build, this file wins; for anything else, the note wins.

The specification is `design/DESIGN.md` revision 6, which passed G1 at
attempt 7 (`gates/LOG.md`), with the three advisory edits A7-1..A7-3 applied
as text (section 3). No design substance was changed. DOSSIER.md, WORKFLOW.md
and the gate reports were not edited. The original tree
`/home/ubuntu/psp/build/linux` was only read: after all the work below,
`sha256sum -c --quiet gates/baseline-tree.sha256` exits 0.

Line numbers for the kernel are at `stage2-trace` HEAD `c135ecdd`. The
integration commit changed only `psp-initramfs.cpio`, so the source line
numbers in `IMPLEMENTATION-kernel.md` (written at `0b0a2acf`) still hold. Line
numbers for pscol and the decoder are those of the files as delivered (sha256
values in section 5.4).

---

## 0. Decisions needed before G2 closes (not taken here)

These are open. An agent cannot settle them; the orchestrator, the G2
reviewer or the human must. Each is described in full where indicated.

| # | Item | Touches | Where |
|---|---|---|---|
| OD-1 | **`nwords` (D3).** It is exact except in one case: 8 received words whose last word is 0xFFFF are reported as 7. Options: (a) accept as implemented; (b) exact, at +2 instructions per received word inside S18; (c) exact, at +1 instruction on the 8-word exit edge, in hand-written code inside the window | D3 (blocking), D10 | kernel DV-3 (6.1) |
| OD-2 | **D10 wording.** The S5..S20 window matches the baseline under the design's own G2 criteria (2.1, 7.2): same MMIO accesses in the same order and form, same 105 instructions, no calls, no global loads or base reloads. It is not "identical apart from stack offsets": five callee-saved registers are consistently renamed, and one delay slot after the −3 exit decision differs. The renaming comes from the per-attempt `spin = 0` store. Every form of that store that was tried caused it, and dropping the store would leave `drain` undefined | D10 (blocking) | kernel DV-4 (6.1), section 4.3 |
| OD-3 | **`build_id` (stats word 2).** The design gives it no value. The kernel defines it as the zlib CRC-32 of the `/proc/version` bytes (= `banner.txt`). pscol is built with `PSC_BUILD_ID=0`, so KRN does not compare it. The decoder reads it from `--build-id` or `BUILD/build_id.txt` and refuses the EPC analysis without it. One definition is needed. **For this release build the kernel's definition gives `0x9b3c599e`.** That value is not `0x27c67583`, which belonged to the kernel implementer's earlier build: the value changes with every build, because the banner carries the build time | 10.1, 8.2 KRN | kernel DV-12, pscol 5, decoder DV-17 |
| OD-4 | **Register-map syntax: the kernel and the decoder disagree (found at integration).** Loading the release `regmap.txt` into the decoder's `BuildInfo.load` gives these results: (1) S16/S17/S18 have no entry, because the kernel writes the range `S16-S18`, so P6's `j` is never computed. (2) The kernel's multi-word values (`i + 2`, `ptr + 2`) are parsed as location `+`. (3) `LEDRMW` yields the variable `loaded` with location `value`, so LEDSPLIT prints "not in regmap" for the loaded value. (4) `rx_buf` is under the label `all`, which the decoder never consults. Separately, `epcmap.txt` uses a label `S0` (`retry:`, a P0 point) that the decoder's `STEP_PPOINT` does not know. **D2/D20 are not affected by the record format, but the H4 step's k/j and the LEDSPLIT value would be lost.** One side must adopt the other's syntax, and the decoder's tests must then run on the real maps | 10.6, D20, C9 | section 4.4 |
| OD-5 | **pscol memory: 256 KB per process, not ≤ 128 KB.** This kernel forces text into the same allocation as data (`fs/binfmt_flat.c:471-472`). Both blocks are still allocated at boot; nothing is allocated later | 4.2, 5.3, C8 figure | pscol 1 (6.2) |
| OD-6 | **Image growth is above the design's component estimates, inside its bound.** `vmlinux.bin` grew +43,631 B against a 48 KB bound: 5,521 B of margin if 48 KB = 49,152 B. Whether pspboot loads the larger image is unknown (R20) | 5.3, C6, R20 | section 2.4 |

The implementers also raised these for reviewer attention, without asking for
a decision:

- pscol 4, 5: the stop rule for an allocating step with no FAT1 record, and
  STICK accepting any DURABLE flush.
- The speed-gate calibration (pscol section 5).
- The decoder's choice of headline onset (DV-7).
- Two stale design texts: the RECS bound 34,364 against 34,404, and "SC bytes
  42-46" in 2.11. Neither affects the code.

---

## 1. Integration steps performed

### 1.1 Initramfs (DESIGN 4.2; recon/build.md 1.3)

- **Config path.** Commit `4c4e7aee` sets `.config:163`
  `CONFIG_INITRAMFS_SOURCE="/work/work/linux/psp-initramfs.cpio"`. The release
  build's `usr/.initramfs_data.cpio.gz.cmd` confirms that the build reads the
  work tree's cpio:
  `... gen_initramfs_list.sh -o usr/initramfs_data.cpio.gz -u 0 -g 0 /work/work/linux/psp-initramfs.cpio`.
- **Original archive.** sha256 `ba50da6a…fada5`, 1,257,984 B, 96 newc
  (`070701`) entries plus padding to 512 B. It equals
  `/home/ubuntu/psp/extract/initramfs2.cpio`. It was unpacked as root into
  `/home/ubuntu/psp/work/initramfs-work/orig-root`, so the device nodes were
  created, and compared with `/home/ubuntu/psp/extract/root2`. They are the
  same: `diff -r` finds no difference in regular files or symlinks; type,
  owner, mode and link target agree for every path; the 18 device nodes have
  the same major:minor numbers. The archive order has no sorting: it is the
  original tool's `find` order.
- **Changes.**
  - `usr/bin/pscol` was added: the bFLT from `work/pscol/cbuild.sh`, 55,044 B,
    sha256 `e5090df3…1c9b6a`. Mode 0755 as instructed, `root:root` like every
    other entry, new inode 2303859 (largest + 1), header dev 8:2 like the rest,
    inserted right after `usr/bin/pspmd`.
  - `etc/rc.sysinit`: `work/pscol/rc.sysinit.patch` applied with `patch -p1`,
    cleanly. The three lines follow the `pspmd -s&` block (lines 21-23); the
    file grew from 659 to 772 B.
- **Repack (deviation I-1).** The archive was rebuilt by
  `work/initramfs-work/mkcpio.py`, with `newc.py` as its parser and writer.
  Every original entry is copied **byte for byte** (header and data) in the
  original order. Only `etc/rc.sysinit` gets new data and a new size and
  mtime; the `pscol` entry is inserted; the archive is padded to 512 B as
  before.
- **Result.** sha256 `012cdc33…8ca6b2`, 1,313,280 B, 97 entries.
- **Verification.**
  - The parser: 95 of 96 original entries are byte-identical, the order is
    preserved, and the only new name is `usr/bin/pscol`.
  - `cpio -itv`, old against new: the only differences are the `pscol` line
    and the `rc.sysinit` size and date.
  - The new archive was unpacked as root, and the files, metadata and device
    nodes were compared with the patched tree. Equal.
- **Commit.** `c135ecdd` "initramfs: add pscol, start from rc.sysinit (DESIGN
  4.2)", on `stage2-trace`. It changes only `psp-initramfs.cpio`.

### 1.2 Release build

| Item | Value |
|---|---|
| Command | `/home/ubuntu/psp/work/build.sh` (normal mode, clean: `git clean -fdxq`, 0 untracked files after the clean) |
| Branch / HEAD | `stage2-trace` / `c135ecdd7da7efc4ef64e531b74b12d1982d3be2`, no tracked changes |
| Result | rc 0 (`MAKE_EXIT` 0) |
| Log | `/home/ubuntu/psp/work/logs/build-20261006T021722Z.log` |
| Out dir | `/home/ubuntu/psp/work/out/20261006T021722Z/` |
| Banner | `Linux version 2.6.22 (root@psp-work-build) (gcc version 4.2.1) #1 PREEMPT Tue Oct 6 02:20:38 UTC 2026` |
| `vmlinux-0.22.bin` | **sha256 `c72459e3e70f72605ffe35fc371ca8b93f9e7ab53d7fdac25021a0896d38b738`**, 936,321 B |
| `vmlinux.bin` | `1954c38613149fa22c840ddd7d45c9c94207b18520abcb125f25b76cfe73ea7d`, 1,766,859 B |
| `vmlinux` | `f3b4aed2d50800c4048c295e2f1a922a6533ce401e84832a74aca75fd013ce02`, 1,986,910 B |
| `System.map` | `33b953409d6ce0896cfc1e9c320ab1a4332d85d99fe426f9ec9d6d6d82f05db4` |
| Warnings | 40 lines, 38 distinct. The distinct set is **identical** to the baseline normal build (`build-20260927T204657Z.log`) and to the kernel implementer's build (`build-20261006T012834Z.log`): no new warning, and none in a changed or new file |
| `build_id` (kernel definition, OD-3) | `0x9b3c599e` = zlib CRC-32 of the 102 bytes of `banner.txt`, which equal the NUL-terminated `linux_banner` in `vmlinux.bin` |

Relation to the kernel implementer's build (`out/20261006T012834Z`, same
kernel source, old initramfs):

- `System.map` is identical up to `__initramfs_end`. From there on, every
  symbol (BSS, `_end`) moves by 0x7000, because `.init.ramfs` is larger.
- `vmlinux.bin` below `.init.ramfs` differs in 6,139 bytes: the BSS
  addresses in the code and the banner strings.
- The D10 window is not affected. See 1.3 for the re-run proof.

### 1.3 Proof that the image carries the new initramfs (WORKFLOW Stage 3 "Initramfs" in advance)

The proof is `work/initramfs-work/extract_ramfs.py`, run on the release
`vmlinux` and `vmlinux.bin`:

- `.init.ramfs` sits at VMA `0x8815e000`, size 333,259 B. The same bytes are
  at that offset in `vmlinux.bin`.
- `gunzip(vmlinux-0.22.bin)` = `vmlinux.bin` (`cmp`).
- The section is one gzip member with nothing after it. Decompressed, it
  gives 1,313,280 B with sha256 `012cdc33…8ca6b2`, equal to the committed
  `psp-initramfs.cpio` and to `zcat usr/initramfs_data.cpio.gz`. The same
  extraction from the kernel implementer's image gives the old `ba50da6a…`.
- Inside it:
  - `cpio -itv` lists `-rwxr-xr-x root root 55044 usr/bin/pscol`.
  - That entry's data has sha256 `e5090df3…`, the delivered binary.
  - `etc/rc.sysinit` lines 21-22 read
    `printf "\\033[37mLaunching PSC collector\\t\\t\\t\\033[0m"` and `pscol&`,
    after line 18 `pspmd -s&`.

**D10 proof re-run on the release build.** The command was
`impl/d10_proof.py work/prebuilt/vmlinux work/prebuilt/System.map out/20261006T021722Z/vmlinux out/20261006T021722Z/System.map`.
It exits 0. Its output is identical to the kernel implementer's
`syscon-window-diff.txt` apart from the path line:

- `Syscon_cmd` 880ceed0..880cf300.
- 105 against 105 instructions on the S5..S20 paths, including the −3/−4
  exits.
- Identical apart from stack offsets and the renaming s3→s7, s4→s3, s5→s4,
  s6→s5, s7→s6.
- The same MMIO order and form, and 0 calls.
- The hand-off checks pass.

`impl/mkmaps.py` regenerates `epcmap.txt` and `regmap.txt` for the release
build. Both are identical to the implementer's apart from the header lines.
The release copies are in
`/home/ubuntu/psp/handoff/impl/release-20261006T021722Z/`, as
`syscon-window-diff.txt`, `epcmap.txt` and `regmap.txt` (deviation I-3).

### 1.4 Image size (DESIGN 5.3, G2 C6)

| File | Reference | Size | This build | Delta |
|---|---|---|---|---|
| `vmlinux-0.22.bin` | baseline rebuild (`work/prebuilt`, = original 2026-09-22 image) | 899,402 | 936,321 | **+36,919** |
| `vmlinux-0.22.bin` | `pspboot-baseline/vmlinux-0.22.bin` (2008 `2.6.22-uc1`, what the stick boots today) | 899,282 | 936,321 | **+37,039** |
| `vmlinux-0.22.bin` | kernel implementer's build (old initramfs) | 909,168 | 936,321 | +27,153 |
| `vmlinux.bin` | baseline rebuild (and the 2008 image decompressed; both 1,723,228) | 1,723,228 | 1,766,859 | **+43,631** |
| BSS (`size vmlinux`) | baseline | 70,192 | 723,792 | +653,600 (not in the image) |

Where the bytes come from:

- **Kernel code and data:** `vmlinux.bin` +16,384 (text +16,660).
- **Initramfs:** cpio +55,296 B; gzipped section +27,247 B (306,012 →
  333,259).

**Against the design's budget (5.3).** The bound, "≤ 48 KB growth for each
of `vmlinux.bin` and `vmlinux-0.22.bin`", is **met**:

| File | Growth | Margin to 49,152 B | Margin to 48,000 B |
|---|---|---|---|
| `vmlinux.bin` | +43,631 B | 5,521 B | 4,369 B |
| `vmlinux-0.22.bin` | +36,919 B | 12,233 B | 11,081 B |

The design's component estimates were **exceeded**:

| Component | Estimate | Actual |
|---|---|---|
| Kernel text | ≈ +7 KB | +16.4 KB |
| pscol bFLT | ≈ 24-32 KB | 55,044 B |
| pscol gzipped | ≈ 12-18 KB | ≈ 27 KB of the gzipped initramfs |

So the growth was anticipated in kind and lies within the stated bound, but
not at the estimated size. Any further growth of pscol by more than about
5 KB would break the `vmlinux.bin` bound. Whether pspboot loads 1,766,859 B
uncompressed is UNVERIFIED (R20). The 2008 image it loads today is
1,723,228 B. The `mem=` warning in `pspboot.conf` concerns the command line,
not the size. This is OD-6.

### 1.5 Package (DESIGN 9; RUNBOOK A)

```
PSPBOOT_DIR=/home/ubuntu/psp/pspboot-baseline /home/ubuntu/psp/work/package.sh \
    uClinux_TRACE /home/ubuntu/psp/work/out/20261006T021722Z uClinux uClinux_FIX uClinux_WIP
```

The run gives exit 0 and status COMPLETE. Name collisions were checked
against `uClinux`, `uClinux_FIX` and `uClinux_WIP`, ignoring case.

- **Staging dir:** `/home/ubuntu/psp/work/deploy/uClinux_TRACE/`. The folder
  to copy to the stick is `PSP/GAME/uClinux_TRACE/` inside it. Beside it are
  `PROVENANCE.txt` (build out dir, log, commit `c135ecdd`, no tracked
  changes, banner) and `SHA256SUMS`.
- **`SHA256SUMS`:**

```
c915ba8ac0649fb537ca6b665bc2243d253f70907710e1b1a57838d46e7daacc  EBOOT.PBP
69adde5e6ad3b2d509a0d6d08a0122f0687cb6cf890211069229363fe0379846  kmodlib.prx
e555890d36878db975267c6a3a375e9b611c205099e0bdc25343f295437d7af7  pspboot.conf
c72459e3e70f72605ffe35fc371ca8b93f9e7ab53d7fdac25021a0896d38b738  vmlinux-0.22.bin
```

- **Baseline files.** `EBOOT.PBP`, `kmodlib.prx` and `pspboot.conf` are
  `cmp`-identical to `/home/ubuntu/psp/pspboot-baseline/`. `pspboot.conf` was
  copied verbatim and not edited: `kernel=vmlinux-0.22.bin`,
  `cmdline=console=tty osk=Dv4`.
- **Kernel.** `vmlinux-0.22.bin` is `cmp`-identical to the release build's.
- **Contents.** The folder holds exactly the four files RUNBOOK "What you
  need" lists.
- **`package.sh` change (deviation I-2).** It now also copies `kmodlib.prx`
  verbatim and requires it in `PSPBOOT_DIR`. Without this change the folder
  lacked `kmodlib.prx`.

---

## 2. Commits

### 2.1 `git log --oneline baseline..stage2-trace`

```
c135ecdd initramfs: add pscol, start from rc.sysinit (DESIGN 4.2)
0b0a2acf psc: kernel stall panel
90a206b2 fat: read-only detection and geometry for the trace
30616d25 exit, writeback, vcs, mousedev: above-driver counters
fa705875 sched: wake-up and switch hooks
14766616 joypad: thread stages, POLL record, driver counters
90d275aa ms_psp: S record per segment transfer, marker, metadata tag
a9f70a04 psp: LED read-modify-write read-back
bcc20c71 psp: timer tick hooks T1 and T2
d5679835 psp: explicit watchdog context flag around both Nop call sites
bd182ffb syscon: record every Syscon_cmd call (A1-A4)
b2469e76 psc: trace rings, records, stats and /proc/psc
a109c03b printk, joypad: read-only semaphore count accessors
84112996 psp: watchdog localTick at file scope as psp_local_tick
4c4e7aee config: build the initramfs from the work tree
ca7dac0a psc: shared record format header (DESIGN 1.x)
```

`baseline` is `775f8372`: the original tree plus `.gitignore`.

- `ca7dac0a` is the interface commit. It holds the shared format header
  `include/linux/psc_format.h`, which nobody changed afterwards.
- The 14 kernel commits each compile and link (kernel notes 6a).
- `c135ecdd` is this integration's only commit.

### 2.2 `git diff --stat baseline..stage2-trace`

```
 .config                        |    2 +-
 arch/mips/psp/Makefile         |    3 +
 arch/mips/psp/ipl_sdk/syscon.c |   75 ++-
 arch/mips/psp/psc.c            | 1247 ++++++++++++++++++++++++++++++++++++++++
 arch/mips/psp/psc_panel.c      |  338 +++++++++++
 arch/mips/psp/psp.c            |   35 +-
 drivers/block/ms_psp.c         |   30 +-
 drivers/char/vc_screen.c       |    5 +
 drivers/input/joypad_psp.c     |  109 ++++
 drivers/input/mousedev.c       |   12 +
 fs/fat/inode.c                 |    6 +
 fs/fat/misc.c                  |    6 +
 include/asm-mips/psc.h         |  279 +++++++++
 include/linux/psc_format.h     | 1087 ++++++++++++++++++++++++++++++++++
 kernel/exit.c                  |   11 +
 kernel/printk.c                |    8 +
 kernel/sched.c                 |    9 +
 mm/page-writeback.c            |    7 +
 psp-initramfs.cpio             |  Bin 1257984 -> 1313280 bytes
 19 files changed, 3246 insertions(+), 23 deletions(-)
```

Every changed line is mapped as follows:

- The kernel files: kernel notes, sections 2-4.
- `.config`: `4c4e7aee`.
- `psp-initramfs.cpio`: section 1.1.

The generic-kernel hooks are inside `#ifdef CONFIG_SONY_PSP`. The syscon
timeout patch is still present, with the same defines `SYSCON_SPIN_MAX`
1000000 and `SYSCON_RETRY_MAX` 16 (`syscon.c:12-13`), the same bounds and the
same teardown writes. Its hunks no longer reverse-apply textually because new
lines sit in their context (kernel DV-17; G2 C2 to rule).

---

## 3. G1 advisories A7-1..A7-3 (text edits to DESIGN.md)

The kernel implementer applied these at the start of Stage 2, as the "What
would close it" column of `gates/G1-attempt7-review.md` section 7 says. The
diff is `impl/A7-design.diff`. DESIGN.md went from 2,669 to 2,680 lines,
sha256 `7f03ed8e…ce42` → `20f659e2…e471`. Closure is for the G2 reviewer to
confirm (gates/LOG.md, G1 PASS entry).

| Item | Where | Edit |
|---|---|---|
| A7-1 | 4.4 step 6 | "IF7b ≤ 152" → "IF7b ≤ 16 per creation that meets the refusing sector (≤ 153 names, 15.3)" |
| A7-2 | 15.3 IF7b, 8.5 VFAT-FI | (a) states the outcome if the margin runs out: creation stops (names budget spent), the files ahead last ≈ 9 minutes, then the worker holds and the panel shows. (b) states why eviction is unlikely: `shrink_slab` only in reclaim (`mm/vmscan.c:1048`, `:1216`), no `drop_caches`, ≈ 2 MB cached per file against ≈ 20.8 MB `MemFree`, reclaim not much before minute 30 (UNVERIFIED), normal use ends at 30:00. (c) VFAT-FI runs IF7b with guest memory well above the page-cache total |
| A7-3 | 4.3 step 3 | "one `syslog(3)` into the 16 KB buffer" → "one `syscall(__NR_syslog, 3, buf, 16384)` as telem (`telem.c:279-282`), into the 16 KB buffer". pscol implements it as the kernel call (`os_target.c`) |

---

## 4. Design section → code (every numbered subsection of DESIGN.md 1-10)

Abbreviations:

- `psc.c` = `arch/mips/psp/psc.c`; `panel` = `arch/mips/psp/psc_panel.c`;
  `psc.h` = `include/asm-mips/psc.h`; `fmt.h` = `include/linux/psc_format.h`.
- `pscol` = `work/pscol/pscol.c` unless another file is named.
- `dec` = `work/decoder/` (`parse` = `pscdec_parse.py`, `ana` =
  `pscdec_analysis.py`, `cli` = `pscdec.py`).
- Kernel commit numbers are the rows of the kernel notes, section 2.
- "DV-k" names the kernel's deviations, "P-k" pscol's, "D-k" the decoder's,
  "I-k" the integrator's (section 6).

### 4.1 Section 1: record format

| § | Element | Kernel | pscol | Decoder | Deviations |
|---|---|---|---|---|---|
| 1.0 | LE, packed + aligned(4), size assertions (SC 80, W 288, POLL 40, S 40, M 80, stats 768, chunk hdr 20, block hdr 8, FILEHDR 44, UHB 84, ctl 32) | `fmt.h` (`ca7dac0a`, asserted at compile time) | includes `fmt.h` by path | `psc_format.py`; `check_format.py` (`--cc` probe with gcc 4.2.1) exit 0 | none |
| 1.1 | `psp_local_tick`, `ts_read()`, sub-tick Count, tick length (`c_pre`, `total_counts`, `c_pre_max`, `long_ticks`) | `psp.c:70-71`, `:384-395`; `psc.h:40-52`; T1 `psp.c:355-356`; `psc.c:561-573` | reads stats 10-13 | 10.5 `Model._sc`, `_timecheck` | DV-6 (T1 split), DV-7 |
| 1.2 | SC record, every field | `psc.c:259-302` (`psc_fill_sc`), `:304-370` (`psc_fill_thread`: lc, led, pre, panel flag); captures `syscon.c:119-123`, `:166`, `:171`, `:182`, `:203-206` | parses P records (`record_scan` `:1075`) | `norm_record`, `psc_format` | DV-2, **DV-3 (OD-1)**, DV-9 |
| 1.3 | W record + 208-byte extension | `psc.c:372-425` (`psc_fill_wext`), `:493-519` | WDOG check `:2215-2228` | `Model.w_step` | DV-9 |
| 1.4 | POLL record | `psc.c:842-907`; fields in `joypad_psp.c` (2.5 row) | POLL, BTN checks | `simulate_polls` | DV-10 |
| 1.5 | S record | `psc.c:655-730`; `ms_psp.c:349`, `:364`, `:378`, `:393` | verdict windows `:734`, `:778` | META repeat, S windows in the timeline | none |
| 1.6 | M record, fill-once, `m_dropped` | `psc.c:475-492` | drained like the others | parsed as SC | none |
| 1.7 | Stats block, 192 words | `psc.c:1069-1120` (`psc_stats_snapshot`); writers at the hook sites | `stats_read` `:415` | `parse_stats`, `stats.csv` | **DV-12 `build_id` (OD-3)** |
| 1.8 | Origin by explicit flag, then `current == psc_jp_task` | `psc.c:197-257` (`psc_sc_entry`), `:169-176`; flag `psp.c:390-392`, `:578-580` | WDOG check | WT/WB/P/M from `ctx` | none |

### 4.2 Section 2: capture points

| § | Element | Code | Deviations |
|---|---|---|---|
| 2.1 A1 | Entry, inline, no call | `psc.c:197-257`, inline from the wrapper `psc_syscon_cmd` `psc.c:526-533` | **DV-1** (wrapper structure; `Syscon_cmd` keeps its name) |
| 2.1 A2 | Per-attempt defaults | `syscon.c:127` `spin = 0`; the other sentinels are derived at exit (`psc_fill_sc`) | **DV-2** |
| 2.1 A3 | In-window captures to stack slots | `syscon.c:119-123` (slots), `:166`, `:171`, `:182`, `:203-206` | DV-4 (OD-2) |
| 2.1 A4 | −3/−4 → `goto out`; exit hand-off; `psc_sc_exit` | `syscon.c:165`, `:206`, `:309-310`, macro `:17-61`; `psc.c:188-191` (`psc_xfer_out`), `:427-520` (`psc_sc_exit`); callers `syscon.c:330`, `:344`, `:419` | DV-1, DV-3, DV-5, DV-17 |
| 2.1 G2 window criteria | objdump proof | `impl/d10_proof.py` → `impl/syscon-window-diff.txt`; re-run on the release build `impl/release-20261006T021722Z/syscon-window-diff.txt` (exit 0) | DV-4 (OD-2) |
| 2.2 | Watchdog context flag at both call sites; `localTick` → `psp_local_tick` | `psp.c:384-395`, `:576-580` (commits 2, 6) | DV-7 |
| 2.3 T1 | Count before the reset | `psp.c:351-365` | DV-6 |
| 2.3 T2 / T2a | `psc_tick_hook` after `psp_watchdog_tick`; uncapped `lc` words, nested-tick test | `psp.c:370-371` → `psc.c:561-618`, T2a `:575-610` | DV-15 (call overhead) |
| 2.3 T2d | Once a second at ≡ 125 mod 250: panel, guard words | `psc.c:539-559`, `:612-617` | DV-14 |
| 2.4 | LED read-modify-write: same load and store, then `psc_note_led` | `psp.c:412-428`; `psc.c:625-652` | none |
| 2.4 | MS marker and S record under `s_psp_ms_rw_sem`; metadata tag b7; MBR read 0; partition start (stats 153) | `ms_psp.c:349`, `:364`, `:378`, `:393`; `:262-275`, `:132`; `:202-203` | none |
| 2.5 | Thread start, stages 1-17, `ri_branch`, `pi_flags`, pushes, mouse; fops; `queue_free` (H9) | `joypad_psp.c:484-499`, `:515-541`, `:557-626`, `:405-435`, `:702-766`; fops `:232`, `:248`, `:252`, `:266`, `:304`, `:327`; `queue_free` `:355-374` | DV-10, DV-11 |
| 2.6 | `do_exit` clears `psc_jp_task`; vcs counters; mousedev counters; `console_sem`/`list_sem` count accessors | `kernel/exit.c:922-928`; `vc_screen.c:576`, `:581`, `:586`, `:591`; `mousedev.c:239`, `:343`, `:669`; `printk.c:71-76`, `joypad_psp.c:629-633` | none |
| 2.7 | `wb_kupdate` count and tick | `mm/page-writeback.c:452-455` | none |
| 2.8 | `/proc/psc/{p,poll,w,s,m}` (3.5 reader, `*ppos` only), `llseek`; `stats`; `ctl` ops 1-4; the one printk | `psc.c:954-1067`; `:1069-1145`; `:1147-1195`; `:1242-1244` | DV-18 |
| 2.9 | Execution context of each capture point | kernel notes 6 (C3 table) | none |
| 2.10 | Kernel stall panel: condition, paint, clear, test, VRAM stores, `pspClearDcache` | `panel:301-338`, font `:37-58`, fill `:135-155`, lines `:185-282`, accounting `:284-299`; columns `impl/panellayout.txt` | DV-13, DV-16 |
| 2.11 | Hook W (wake-up); hook S (`wk_*`, preemption-holder branch) | `sched.c:1661` → `psc_sched_wake`, `psc.c:732-748`; `sched.c:3713` → `psc_sched_switch`, `psc.c:750-831` | DV-15 |
| 2.12 | `fat_fill_super` success: sb + geometry 154-159; `fat_fs_panic` counter; `ms_rdonly` | `fs/fat/inode.c:1418-1420` → `psc.c:912-926`; `fs/fat/misc.c:25-27` → `psc.c:928-933`; `psc.c:936-941` | none |

### 4.3 Section 3: history mechanism

| § | Element | Code | Deviations |
|---|---|---|---|
| 3.1 | One static BSS object `psc_mem` (rings 652,288 B, stats, 7 guard words) | `psc.h:185-200`, `psc.c:37-47`; guards armed in `psc_init` `psc.c:1211-1214`. `size`: `psc_mem` 653,584 B | DV-14 |
| 3.2 | Full resolution, everything streamed | by construction: no sampling anywhere in the kernel code; pscol drains everything (4.3) | none |
| 3.3 | No triggers | none in the code (the decoder finds onset, 10.7) | none |
| 3.4 | Writer protocol: invalidate `seq`, fill, publish `seq`, then head | P `psc.c:450-458`, M `:482-490`, W `:499-509`, POLL `:894-900`, S `:684-715` | DV-5 (order in `psc_sc_exit`) |
| 3.5 | Reader: overwritten → oldest, skip and count `slot_bad`, ≤ N skips, whole records, `head_regress` | `psc.c:976-1033` | none |
| 3.6 | In-flight state | stats 64-67, W extension, panel line 3 | none |

### 4.4 Section 4: extraction path (pscol unless stated)

| § | Element | Code | Deviations |
|---|---|---|---|
| 4.1 | Collector derived from telem's FP-free parts | font `:2326-2357`, formatting `:227-266`, mice `:2008`, blit `:2604`; `os_target.c:110`, `:139`, `:149` | none |
| 4.2 | rc.sysinit lines; one binary, two processes; supervisor (setsid, `/dev/null`, signals, `mkdir PSCLOG`, run number, nonce, vfork+execve `/usr/bin/pscol -w rrr nonce`, 2 s watch); takeover in-process; worker start (conlevel EVENT, seek to `durable_next`, names budget, pid classes); guards; "never" list | **initramfs `c135ecdd`** (`etc/rc.sysinit:21-23`, `usr/bin/pscol` 0755); `main.c:105`, `:115`, `:125`, `:127`, `:72`, `:131`, `:145-149`, `:151`, `:157-168`; `pscol.c:2815` (`worker_main`), `:2622` (`worker_init`), `:2660`, `:2189`, `:2095`, `:2143`; guards `:292`, `:307`, `:332`, `:277`, `:2777` | **P-1 (OD-5)**, P-7, P-13, I-1 |
| 4.3 | Worker tick, steps 1-10 and bounds | `:2696` (`worker_tick`), `:415`; drain `:862`, `:908`, `:971`, `:995`; KMSG/syslog/PROCS/mice/meminfo `:1996`, `:2033`, `:2008`, `:1972`; flush `:1789`, `:1861`; creation `:1719`; META `:1173`; bad region `:1911`; HUD `:2604`; guards and `nanosleep` `:2769-2770`, `:2822`; fit test `:1828`; EVENT queue `:366` | P-14 |
| 4.4 | Segment files: steps 1-8, creation rule, use and switch (TE10), hold | step 1 `:1492`, `:1538-1566`, probe `:1552`; step 0 `:1418`; steps `:1637`, `:1590`, template `:494`, `os_target.c:48`; verdict `:637`, `:658`, `:1365`, `:1663`; stop/abandon `:1296`; next attempt `:1272`, `:2095`; completion `:1603`, `os_target.c:99` (fadvise 4254, seven slots); cap and creation rule `:1704`; switch `:1730`, `:1737`, `:1741`, `:1764`, hold `:872-876` | P-2, P-3, **P-4**, P-10, P-12 |
| 4.5 | `durable_tick` / `durable_next` via ctl op 1; the kernel compares and paints | pscol `:1888`, `:843`, `:459`; kernel `panel:317-320`, `psc.c:1147-1195` | none |
| 4.6 | Failed flush never overwritten; range re-send; fsync-error DURABLE (b30); bad-region escape; read-only; ENOSPC; takeover rule | `:1861`, `:803`, `:908-968`, `:1904`, `:1867`, `:1911`, `:2726`, `:1719`; `main.c:157-168` | none |
| 4.7 | META detection, display (not red, no panel paint), clearing and bypass | pscol `:1173`, `:1050`, `:1147`, `:1162`, `:1677-1684`, `:2760-2762`; kernel ctl op 4 `psc.c:1147-1195`, panel line 6 field; decoder `Analysis.meta_repeat` | P-10 (16 tracked sectors) |
| 4.8 | Sector classes from the stats geometry; extent table by FIBMAP; S windows by `pread`; flush and step verdicts; speed; geometry self-check | pscol `:507`, `:527`, `:734`, `:778`, `:608`, `:702`, `:1349`, `:1365`; kernel stats 153-159 (`ms_psp.c:202-203`, `fs/fat/inode.c:1418-1420` → `psc.c:912-926`), S `flags` b7 (`ms_psp.c:262-275`) | P-4, P-10; D-19 (FATM range in the decoder's repeat) |

### 4.5 Section 5: budget

| § | Element | Where it is realised or checked | Notes |
|---|---|---|---|
| 5.1 | Bytes to the stick | n/a: budget figures. Realised by the 4.3 caps and chunk sizes in pscol. Checked by Stage 3 "Volume" | pscol's nominal 5-minute host run produced every chunk type with 0 records missing; the volume figures are for Stage 3 |
| 5.2 | Memory Stick operations (H10 exposure) | n/a: budget. Measured on the device by `led_calls`, S records and the read-back ORs | none |
| 5.3 | Memory and image | Kernel: BSS +653,600 B (`psc_mem` 653,584 + 3 words), as budgeted (≈ 653 KB). Userland: **2 × 256 KB** (P-1, OD-5). Image: section 1.4 (within the 48 KB bound, above the estimates, OD-6) | P-1 |
| 5.4 | Time added | Zero instructions inside S5..S20 (proof 1.3; OD-2 on the wording). Outside the window the costs are measured at run time (`p_rec_cost_*`, `w_rec_cost_max`, `panel_cost_*`, stats 24-26, 118-124, 148) and shown on HUD line 10 | DV-1 (≈ 280 B more stack and one extra call on each path, Nop included), DV-15 |

### 4.6 Section 6: coverage matrix (the decoder classifies; kernel and pscol supply the fields)

| § | Element | Decoder | Deviations |
|---|---|---|---|
| 6 | H0-H10 rows; template; triple (trigger, state, H8 flags); early death without C0 | `ana`: `_stopped`, `_states` (H1 with the 9.5 variant, H2, H3, H5, N2b before H6, H6 with template/`rx2 literal`, N2, N3, N11), `_h7`, `_n10`, `_h8`, `_triggers` (H4, H4 two-stage, WB, H10, N1m, N1p, N1, H10b, LEDSPLIT, N8), `learn_template`, `run`; H0 raw windows `window_*.txt` | D-7, D-8, D-9, D-10, D-11, D-12, D-13, D-14 |
| 6.1 | N1, N1m, N1p, N2, N2b, N3-N11, H10b, WB, LEDSPLIT | the same functions; `crosscheck`, `holder`, `suspension` | D-9..D-14; **OD-4** (LEDSPLIT loaded value and P6 j need a regmap the decoder can read) |
| 6.2 | Onset timing: rings ≥ 114 s; first complete drain | kernel ring sizes (`fmt.h`, 3.1); pscol catch-up `:862-1000` | none |
| 6.3 | Phase in the 1250-tick cycle: before, across, after | `Analysis.placements` | none |

### 4.7 Section 7: perturbation

| § | Element | Where | Notes |
|---|---|---|---|
| 7.1 | No lock, no IRQ masking, no new MMIO read; one printk; console log level 4 | kernel notes 6 (C3: no lock, interrupt masking or delay anywhere; the only new memory-mapped accesses are panel VRAM stores); pscol `conlevel` at worker start (`syscall(__NR_syslog, 8, 0, 4)`, `:2664`) | DV-1 (wrapper call and stack) |
| 7.2 | Zero instructions in the window; G2 objdump check | `impl/syscon-window-diff.txt`, `impl/d10_proof.py`; release re-run in `impl/release-20261006T021722Z/` | **DV-4 / OD-2** |
| 7.3 | Why this neither hides nor causes H4; no-death inference | n/a: statement. The pre-registered inference is in the decoder (`no_death_inference`, `interleave_stats`); `wk_*` and `pre_*` are recorded (2.11) | none |
| 7.4 | Userland load parity with telem: 272 row writes, syslog type 3, `/proc` reads, mice client; fadvise instead of `drop_caches` | pscol `:2604` (272 writes of 1,920 B, rows 0-175 then 0-95), syslog `os_target.c`, fadvise `os_target.c:99` (objdump-checked: seven slots) | P-2 (`writev`) |
| 7.5 | Own stick I/O and H10 | n/a: statement. Exposure recorded through S records, LED hooks and creation EVENTs | none |
| 7.6 | Kernel identity: timeout patch unchanged | `syscon.c:12-13` defines unchanged; behaviour unchanged; text hunks displaced | DV-17 (C2 to rule) |
| 7.7 | No floating point | pscol: `cbuild.out`/`CHECKS.txt`, FP registers 0, FP mnemonics 0, no soft-float/printf/strtod/atof symbols, `flthdr` valid with stack 16384. Kernel: new and changed objects have 0 FP instructions and no soft-float or 64-bit division helpers (kernel notes 6b) | none |

### 4.8 Section 8: self-test

| § | Element | Where | Deviations |
|---|---|---|---|
| 8.1 | Boot `printk` `PSC5 P4096 ...` from W seq 0 | `psc.c:1242-1244` (`PSC_BOOT_PRINTK_FMT` in `fmt.h`) | none |
| 8.2 | HUD (ten lines, ≤ 35 characters, rows 0-175); checks KRN, WDOG, STICK, REC, PANEL, SUP, POLL, BTN; second PSC TEST | pscol `:2401` (`ms_line`), `:2458`, `:2564`; checks `:2215-2228`, `:2230`, `:1075`, `:2256`, `:2269`; panel test via ctl op 3 (kernel `psc.c:1147-1195`, `panel:301-338`) | **P-5**, P-6, P-7, P-11; KRN does not check `build_id` (OD-3) |
| 8.3 | Abort rule at 3:00 | n/a: runbook. HUD states `MS NO STICK`, `MS SLOW`, `MS DIR FULL` (pscol `ms_line`) | P-6 (from uptime 170 s) |
| 8.4 | `DEAD?` display-only hint | pscol `:2278` | P-8 |
| 8.5 | Host-side tests | n/a: Stage 3. Already partly exercised: pscol `test/` (28 verdict vectors, HUD render, step-0 burst, IF4, IF7b, TE10; section 5.2) and decoder `test/run_tests.py` (26 tests; 5.3). Not yet done: VFAT-FI, the ring/reader code on the host, the takeover, the panel render on the host | — |

### 4.9 Section 9: runbook

| § | Element | Where |
|---|---|---|
| 9 | Deploy `PSP/GAME/uClinux_TRACE/` with the baseline's `EBOOT.PBP`, `kmodlib.prx`, `pspboot.conf` and our checksummed `vmlinux-0.22.bin` | n/a: runbook. Package: `/home/ubuntu/psp/work/deploy/uClinux_TRACE/` (1.5); I-2 |

### 4.10 Section 10: decoder (`work/decoder/`)

| § | Element | Code | Deviations |
|---|---|---|---|
| 10 (intro) | Inputs: files, `--raw`, System.map, `epcmap.txt`, `regmap.txt`, `panellayout.txt`; inputs never modified | `cli` (`-o`, `--build`, `--times`, `--raw`); `BuildInfo.load` | **OD-4** |
| 10.1 | Words 20-22 against System.map, word 2 against `build_id`; refuse the EPC analysis otherwise | `Model._build_check`, `label_of` | D-17 (OD-3) |
| 10.2 | Chunks, nonce CRC, run selection, confirmed extent, merge/conflicts, `--raw`, raw-image rule | `parse`: `candidates`, `accept`, `crc_ok`, `load`, `_extents`, `_bump`, `_merge`, `parse_recs`, `_raw_rule`, `RAW_REQUIRED_EVENTS`; `cli` exit 3. Writer side in pscol `:469` (`chunk_put`), `:1418-1447`, `:1789-1846`, `:2293`, `:2315` | D-1, D-2, D-3, D-4, D-5, D-18 |
| 10.3 | Record strings, dropped `seq` 0xFFFFFFFF, explicit gaps, 16-bit links | `norm_record`, `Model._gaps`, `Model._links` (`_expand`, `_link_by_time`) | none |
| 10.4 | Stats, `stats.csv`, counter decreases | `parse_stats`, `_outputs` | none |
| 10.5 | Time reconstruction | `Model._sc`, `_timecheck`, `_uptime_offset`, `rec_line`, `crossings.txt` | D-6 (operator times) |
| 10.6 | EPC map and register map (Stage 2 deliverables) | **Kernel side:** `impl/epcmap.txt`, `impl/regmap.txt` (from `impl/mkmaps.py`); release copies in `impl/release-20261006T021722Z/`. **Decoder side:** `BuildInfo.load/label`, `STEP_PPOINT`, `Model.w_step`, `reg_value` | **OD-4** (syntax mismatch; `S0` unknown to the decoder); D-16 |
| 10.7 | Steps 1-8 | `cli.timeline`; `learn_template`; `simulate_polls`; `onset_candidates`, `placements`; classification (6.1 row above); `_outputs`, `_report`; `harm_table`, `fisher_one_sided`, `ub95`; `no_death_inference` | D-7, D-20, D-21, D-22 |
| 10.8 | Panel from photographs | `panel_parse`, by keyword | D-15: `impl/panellayout.txt` now exists, so the parser should switch to its columns |

---

## 5. Evidence summaries

### 5.1 D10 proof

| Item | Value |
|---|---|
| Script | `/home/ubuntu/psp/handoff/impl/d10_proof.py` |
| Implementer's output | `/home/ubuntu/psp/handoff/impl/syscon-window-diff.txt` (build `20261006T012834Z`) |
| Release re-run | `/home/ubuntu/psp/handoff/impl/release-20261006T021722Z/syscon-window-diff.txt` (exit 0; identical apart from the build path) |

Result: 105 instructions on both sides. They are identical apart from stack
offsets and the consistent renaming s3→s7, s4→s3, s5→s4, s6→s5, s7→s6. The
MMIO loads and stores are the same, in the same order and form. There are 0
calls in the window. The hand-off checks pass (t0/t8 unwritten between the
loop and the hand-off). Not literally "identical apart from stack offsets":
OD-2.

### 5.2 pscol CHECKS (`/home/ubuntu/psp/work/pscol/CHECKS.txt`, 2026-10-06 01:13 UTC)

Build:

- gcc 4.2.1 `-Wall -W`: **0 warnings**.
- FP registers **0**, FP mnemonics **0**, and the design's 7.7 grep **0**.
- No `printf`/`strtod`/`atof`/soft-float/libm symbols; no
  `malloc`/`opendir`/`fopen`/`fork` symbols.
- `flthdr`: bFLT rev 4, PIC-GOT, stack **16,384**.
- Sizes: text 51,904, data 2,896, bss 112,720.
- bFLT file **55,044 B**, sha256 `e5090df3…`.
- Allocation: one **256 KB** block per process (P-1).
- The delivered binary (cbuild 01:14:10 UTC) comes from the same sources as
  the CHECKS run (01:11:56 UTC); only the bFLT build date differs.

System calls, from objdump:

- `fadvise64_64` = syscall 4254 with the seven o32 argument slots.
- `pread` goes through `pread64` with the offset in the even register pair.

Host tests, all PASS:

| Test | Result |
|---|---|
| 8.5 S-record verdict vectors (incl. the r7 own-entry vectors, pdflush-before-own, skipped seq, wrong partition offset) | 28/28 |
| HUD render (11 forced states; longest line 34 characters; no pixel at x ≥ 428 in rows 8-39 or in rows ≥ 168) | PASS |
| Nominal 5 min at 52 KB/s | SELFTEST PASS, 272 fb writes per tick, none in rows ≥ 176, 0 missing |
| 3 s burst during step 0 | 8/8; next fresh file 7.1-7.4 s after recovery; no alias written |
| IF4 sporadic, 30 min | 200/200 at 25/52/100/300 KB/s, 0 lost below `durable_next`; at 25 KB/s SELFTEST fails on `MS SLOW` as designed |
| IF7b scenario | META in 1.4 s; fresh file after 13 ticks and 105 names (bounds: 20 ticks, 153 names); later creations ≤ 14 names |
| TE10 hold-and-resume | 6/6 |
| ASan/UBSan | clean |
| Decoder cross-check (`pscdec_parse.load` on the simulated stick) | 3/3 |
| Original manifest | exit 0 |

The supervisor/takeover, the guard exit and the real system calls are not
tested on the host. The vfat model is a model.

### 5.3 Decoder TESTS (`/home/ubuntu/psp/work/decoder/TESTS.txt`)

**26 tests, all OK** (47 s).

| Test | Result |
|---|---|
| Shapes | H1, H2, H3, H5, H6, H9 as states; H4 as trigger at P4 ("allowed for P4", "across, wn 1") with H1 as state; H7 stage (b); H8 flags beside H3; H10 as trigger with window S13..S20 |
| Healthy run | NO DEATH DETECTED, with the no-death inference |
| Unmatched stream | H0 / UNCLASSIFIED with raw windows |
| N-4 | H6 with the template; `rx2 literal` and not H6 without it |
| Truncation at 50 offsets | 436,757 complete records, 0 lost from complete chunks, nothing after the cut merged |
| Two boots | other run ignored; other-boot chunk listed, not merged; two nonces refused (exit 2) |
| `--raw` and the raw-image rule | as specified |
| Merge | conflicts reported with both copies |
| META repeat | as specified |
| Robustness | 300 bit flips, no crash |

`check_format.py` exits 0. The tests ran on synthetic streams with the
decoder's own map syntax, **not** on the kernel's `epcmap.txt`/`regmap.txt`
(OD-4). The shapes were written by the decoder's author; Stage 3 should add
independent vectors.

### 5.4 Provenance of out-of-tree code (not under version control)

| File | sha256 |
|---|---|
| `work/pscol/pscol.c` | `6fd80760aa56449c4d35c92af9481bdc4526e63c52fdfe51df9fbde7eadc1eac` |
| `work/pscol/pscol.h` | `5beecf47f37ff311e477a8a0cb846b0c17a320f6568ae2d1ec7d2720ed0cf90d` |
| `work/pscol/main.c` | `61770c8bbe2550a8d42121b68967acdd75bd26d2690b1ef2aa4072ce2446a614` |
| `work/pscol/os_target.c` | `5e6becf37301691916c2f13109b2d52177a6d066a343a89f182d2b88ddd613cc` |
| `work/pscol/cbuild.sh` | `1f4f39eea780eac13c5f4f708fd303b3ec9a53b14bd4fc3f36854c7011846a03` |
| `work/pscol/rc.sysinit.patch` | `61b8d0cad25973491b706fcbb9fdffaf1c88caa148117aa9c371863da4ac103b` |
| `work/pscol/pscol` (bFLT, in the initramfs) | `e5090df3714684f28f35e4111a37f77ec34acea145eabf969b2b0bd65d1c9b6a` |
| `work/decoder/pscdec.py` | `7111cb018529cb7df1ea43336a642180dc0f654a73c9eedf3e417c8f33f79633` |
| `work/decoder/pscdec_parse.py` | `07399bed04659afc638a9dde914c74779f4784a48a9c6c989af7ebfb54dba6ac` |
| `work/decoder/pscdec_analysis.py` | `dd1e50332b7ad344a1951f14fdd3f53e37b318e73039a878c35ecf9564855ba3` |
| `work/decoder/psc_format.py` | `8d6154b97c4d69099f06c7501c81f3e864202e3e627490875afd6f5729856a81` |
| `work/decoder/synth.py` | `6c6f23482f8ede32b8a58054953bfe45a629f43907a7bd7e3792426074608049` |
| `work/decoder/test/run_tests.py` | `6ab80c5af10a903f21d1a9e7d621ee0c05b152050478805f1a399a7fbece531d` |
| `work/initramfs-work/newc.py`, `mkcpio.py`, `extract_ramfs.py` | integration tools of section 1 |

---

## 6. Every deviation from the design, with its reason

### 6.1 Kernel (`IMPLEMENTATION-kernel.md` section 4)

| # | Deviation | Reason | Touches |
|---|---|---|---|
| DV-1 | The transaction keeps the name `Syscon_cmd`. A wrapper, `psc_syscon_cmd`, does A1 inline, calls it, then calls `psc_sc_exit`. The captures are locals of `Syscon_cmd`, handed over at the exit label through an opaque asm to `psc_xfer_out` (a per-origin static area) | With gcc 4.2.1 every other arrangement changed the register allocation or caused a base-address reload inside S5..S20. Costs a call and about 280 B of stack on each path (Nop included). EPCs in the wrapper are ENTRY, in `psc_sc_exit` REC (P0) | D10, in the direction of keeping it |
| DV-2 | A2 is reduced to one per-attempt store (`spin = 0`). The other sentinels are derived at exit with the same values. Corner: a drain of exactly 1,000,000 words that then finds the FIFO empty reads `drain` 0, not 0xFFFF | Each further store in the retry loop changed register choice in the window | none |
| DV-3 | `nwords` comes from the receive loop's counter register `t0` at the exit. Exact except: 8 words with the last word 0xFFFF reads 7 | Any C use of `ptr`/`i` after the loop adds 2 instructions per word in S18; the machine state after S19 cannot separate the two cases | **D3 (blocking): OD-1** |
| DV-4 | The window is identical apart from stack offsets, a consistent renaming of five callee-saved registers, and one delay slot after the −3 exit decision | Caused by the A2 store; without it `drain` would be undefined. The design's 2.1 criteria hold | **D10 (blocking): OD-2** |
| DV-5 | In `psc_sc_exit` the snapshots and the `t_busy` clear come before filling and publishing | Keeps W `t_busy`/`p_head` consistent with `wn`/`w_head_lo`, and freezes the `lc`/`led_cmd`/`pre` words during the copy | none |
| DV-6 | T1: only `mfc0 $9` runs before the Count reset; the accounting runs after the reset with the same `c_pre`. `c_pre_cur` is stored for the W extension | One instruction before the reset, as the design allows (1-2) | none |
| DV-7 | `psp_watchdog_tick`: the watchdog's own instructions are unchanged, interleaved with the T1 store and the `wd_ctx` stores | Compiler scheduling; the design asks for the flag stores | none |
| DV-8 | "EPC inside `Syscon_cmd`" = from `Syscon_cmd` to the next syscon.c function in link order, computed once | gcc no longer emits syscon.c in source order | none |
| DV-9 | W records have `lc_dtick` 0 (all `lc_*` 0 as 1.3 says), not the 0xFFFF "none" of 1.2; `lc_flags` b0 = 0 | 1.3 and 1.2 conflict; 1.3 is specific to W | none |
| DV-10 | POLL `stage_max` excludes stage 17 | Every iteration reaches 17, so the field would be constant | none |
| DV-11 | `qfree_stage` 3 is set after `down(list_sem)` succeeds; a failed down goes from 2 to 5 | The closer blocked in `:353` stays at 2 (the H9 signature) | none |
| DV-12 | `build_id` = zlib CRC-32 of `linux_banner` (= `/proc/version`) | The design gives no value | OD-3 |
| DV-13 | Panel: 40-column fixed layout (`panellayout.txt`); the clearing paint is counted like a paint and sets `panel_cmd_id` | A clearing paint is interrupts-off time too, which N1p must see | none |
| DV-14 | Guard words armed in `psc_init` (late_initcall) | The design does not say when | none |
| DV-15 | Hook S gate: 3 loads and 2 compares per switch (design: 1 load, 1 compare); `psc_tick_hook` is a call (≈ 6 more instructions per tick) | Implementation cost, outside `Syscon_cmd` | none |
| DV-16 | No kernel-initiated "PSC TEST" at init | Not in the design: the test is requested by the collector through ctl op 3 | none |
| DV-17 | The timeout patch's text hunks no longer reverse-apply; its defines, bounds, teardown writes and return values are unchanged | New lines in the hunks' context (hand-off macro, slot declarations, `goto out`, `out:`) | C2: reviewer to confirm |
| DV-18 | `ctl` returns −EINVAL for slot ≥ 8 or seconds outside 1..10; a partial write returns the bytes applied; op 1 writes `durable_next` before `durable_tick`, op 4 `meta_tick` before `meta_sector` | Input validation; ordering so the interrupt never sees a new tick with old positions | none |

### 6.2 pscol (`IMPLEMENTATION-pscol.md` section 4)

| # | Deviation | Reason | Touches |
|---|---|---|---|
| P-1 | 256 KB per process (512 KB for both), not ≤ 128 KB; extent tables 9.2 KB, not ≈ 6 KB | `fs/binfmt_flat.c:471-472` forces text into the same `kmalloc`; text + data + bss + stack = 183,968 B. Still allocated only at boot | figure only (OD-5) |
| P-2 | Creation steps use one `writev()` (16 × the 4 KB template) instead of one `write()` | Same syscall path and bytes, no 64 KB buffer | none |
| P-3 | "A step allocates" is evaluated only on its first attempt | The design says a retry allocates nothing; the first build stopped growth on every retry (bug, found by the TE10 harness, fixed) | none |
| P-4 | An allocating step with no successful FAT1 record, or with a skipped `seq` in its window, stops growth | Conservative reading of "at least one succeeded if the step allocated" | reviewer to check |
| P-5 | STICK needs *a* DURABLE flush (plus geometry self-check, `durable_tick`, speed, names budget), not literally the first | One sporadic failure on the first flush would otherwise abort a good run | reviewer to check |
| P-6 | The 3:00 states (`MS NO STICK`, `MS SLOW`, `MS DIR FULL`) appear from uptime 170 s | The collector cannot see the stopwatch; 8.3 assumes ≈ 10 s of loading | none |
| P-7 | WDOG for a takeover instance: the WB sub-check passes when `durable_next[W] > 0` | W seq 0 was already durable and is not read again | none |
| P-8 | `DEAD?` "HOLD outside the reference step" = HOLD for 2 s | The collector cannot know when C0 runs; display only | none |
| P-9 | Extra EVENT strings: `ctl err`, `fadvise <ret> <errno>`, `names exhausted`, `abandon … 0 open` | R23 asks the worker to check fadvise; a failed ctl turns KRN red | none |
| P-10 | Bounds: verdict window ≤ 256 S records (more = skipped = FAILED); ≤ 6 open segment files; ≤ 16 META sectors tracked (LRU) | Fixed tables, no allocation | none |
| P-11 | Definitions of the UHB fields the design does not define (`bytes_synced_total`, `lag_max`, `max_tick_ms_60s`, `last_write_ms`); line 10 units; SELFTEST PASS latches | Not defined in 10.2/8.2 | none |
| P-12 | Names budget: used slots include `.`/`..` and LFN slots | Exact slot count | none |
| P-13 | Without `/proc/psc` the supervisor's nonce falls back to `gettimeofday` ^ pid | No stats to read | none |
| P-14 | The first drain's `m` counts Δt from worker start | Allows the start-up backlog to drain at `m` up to 4 | none |

### 6.3 Decoder (`IMPLEMENTATION-decoder.md` section 3)

| # | Deviation | Reason |
|---|---|---|
| D-1 | A file with no extent evidence at all is merged and flagged "extent unverified" | Dropping it would lose real data; other boots are already excluded by the nonce |
| D-2 | A CRC-bad RECS chunk at the end of the last accepted chunk is dropped; its whole records are listed UNVERIFIED (never merged) | Keeps salvage visible without merging unverified bytes |
| D-3 | `--raw`: a chunk's file offset = image offset − nearest preceding FILEHDR of the run | "Grouped under the nearest FILEHDR"; assumes contiguous clusters |
| D-4 | One run number with two nonces: refused (exit 2) until `--nonce` picks one | Not specified; merging is what IF10 forbids |
| D-5 | RAW IMAGE REQUIRED: writes `REPORT-NOT-FINAL.md` only, exit 3 | "Refuses a final REPORT" |
| D-6 | `--times` file format and the stopwatch-to-tick mapping; D window = d0_start + 70 s | Not specified |
| D-7 | Choice of the headline onset among candidates, including "quiet" and "refuted" | Without it a healthy run's D8 tail reads as a death |
| D-8 | "Own valid reply" definition | Used by step 7 and the cross-check |
| D-9 | "Reply-shaped `drain_last`" = not 0x0000/0xFFFF | Not defined further |
| D-10 | "Immediately before onset" = ± 1 poll; H4 two-stage within 1 s after Nop k+1 | Quantification |
| D-11 | H10/N1m/N1 evaluated on the first failed command and the two before it | Quantification |
| D-12 | H7 (c): the collector's own reads = Δ UHB `mouse_pkts_total` (one `read()` per 3-byte packet; pscol does exactly this, `pscol.c:2013`) | Count not given |
| D-13 | H7 (d) applied as written, only after raw frames follow undelivered presses | Avoids a false match while the OSK is hidden |
| D-14 | N2: persistent `drain > 0` only noted when the template's own drain range exceeds 0 | Otherwise indistinguishable from healthy |
| D-15 | Panel photographs parsed by keyword, not by `panellayout.txt` | The file did not exist when the decoder was written; it does now |
| D-16 | `regmap.txt` syntax `<label> <var> <location>` | Design gives content, not syntax. **Does not match the kernel's file: OD-4** |
| D-17 | `build_id` from `--build-id` or `BUILD/build_id.txt`; EPC analysis refused without it | No definition (OD-3) |
| D-18 | EVENT line grammar (optional tick stamp, then the 10.2 words) | Not specified. pscol's strings match (`segment ready`, `stop`, `abandon`, `flush fail`, `region bad`, `meta err`, `inode reused`, `speed`, `names budget`, `conlevel`, `switch`, `takeover`, `guard`) |
| D-19 | FATM = `[fat_start + fat_length, fat_start + fats × fat_length)` | The literal text would class FSINFO as FATM |
| D-20 | `--no-template` test hook | Needed by the 8.5 N-4 row |
| D-21 | All thresholds fixed as constants and printed | 10.7, G3 R6 |
| D-22 | The decoder does not re-judge flush/step verdicts; it repeats META only | Section 10 does not ask for it |

### 6.4 Integration

| # | Deviation | Reason | Touches |
|---|---|---|---|
| I-1 | The initramfs was not repacked with the `cpio` tool from the unpacked tree. A small newc writer (`work/initramfs-work/mkcpio.py`) copied every original entry byte for byte and changed or added only `etc/rc.sysinit` and `usr/bin/pscol`. The tree was still unpacked as root and checked against `extract/root2`, and the result against the patched tree | `cpio -o` from an unpacked tree would renumber inodes, rewrite directory mtimes and depend on host `find` order. The byte-preserving rewrite keeps all 95 untouched entries identical, which `cpio -itv` and the parser both confirm | none |
| I-2 | `work/package.sh` now also requires and copies `kmodlib.prx` verbatim from `PSPBOOT_DIR`. The diff is two lines plus a comment; the previous version is kept at `work/initramfs-work/package.sh.before-integrator` | DESIGN 9 and RUNBOOK "What you need" list `kmodlib.prx` as one of the four files of the folder. Recon wrote `package.sh` before the baseline folder was recovered (dossier 9.7), so it copied only `EBOOT.PBP` and `pspboot.conf`. `pspboot.conf` is still copied verbatim | none |
| I-3 | Release-build copies of `syscon-window-diff.txt`, `epcmap.txt` and `regmap.txt` were written to `impl/release-20261006T021722Z/`. The implementer's files in `impl/` were left as delivered | The decoder needs maps "from the exact build" (10). Their content is identical apart from the header lines | none |
| I-4 | `pscol` is mode 0755, while the other two daemons in the archive are 0744 | The task and pscol's notes ask for 0755; the owner is root:root like every entry | none |

---

## 7. Paths

| What | Path |
|---|---|
| Kernel branch | `/home/ubuntu/psp/work/linux`, `stage2-trace` @ `c135ecdd` |
| Build log | `/home/ubuntu/psp/work/logs/build-20261006T021722Z.log` |
| Build out | `/home/ubuntu/psp/work/out/20261006T021722Z/` |
| Deploy folder | `/home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/` (+ `../../../SHA256SUMS`, `PROVENANCE.txt`) |
| Collector | `/home/ubuntu/psp/work/pscol/` |
| Decoder | `/home/ubuntu/psp/work/decoder/` |
| Integration tools and scratch | `/home/ubuntu/psp/work/initramfs-work/` (`orig-root/`, `new-root/`, `check-root/` are root-owned unpacked trees) |
| Maps and D10 proof for this build | `/home/ubuntu/psp/handoff/impl/release-20261006T021722Z/` |
| Panel layout | `/home/ubuntu/psp/handoff/impl/panellayout.txt` |
