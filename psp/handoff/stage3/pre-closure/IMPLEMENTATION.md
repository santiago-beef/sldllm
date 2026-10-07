# IMPLEMENTATION.md: Stage 2 (integrated), revised for G2 attempt 2

Stage 2 integration record for Gate G2. Attempt 1 (2026-10-06, integrator,
HEAD `c135ecdd`) merged the three implementers' notes:

- `IMPLEMENTATION-kernel.md` (kernel, branch `stage2-trace`);
- `IMPLEMENTATION-pscol.md` (collector, `/home/ubuntu/psp/work/pscol/`);
- `IMPLEMENTATION-decoder.md` (decoder, `/home/ubuntu/psp/work/decoder/`).

**G2 attempt 2** (2026-10-06, the G2-attempt-2 implementer): G2 attempt 1
failed (`gates/G2-attempt1-review.md`, `gates/G2-attempt1-verify.md`) and was
routed back to G1, which ruled on R-1..R-6 (`design/DESIGN.md` section 17,
`design/g1ruling.diff`; `gates/G1-ruling1-review.md` and
`gates/G1-ruling1-redteam.md`, both PASS). This revision implements the
ruling and fixes every attempt-1 finding. **Section 8 answers each finding in
one line; section 9 holds the new material** (ruling implementation, measured
per-path costs and stack depth, the timeout-patch note, commit authorship).
The three per-implementer notes are attempt-1 records and were not edited;
where they and this file disagree, this file wins. The attempt-1 version of
this file is kept unchanged as `impl/IMPLEMENTATION.attempt1.md`.

The specification is `design/DESIGN.md` revision 7: revision 6 (G1 PASS at
attempt 7) with the A7-1..A7-3 text edits (section 3) and the G1 ruling
(section 17). No design text was changed by the implementer at attempt 2.
DOSSIER.md, WORKFLOW.md and the gate reports were not edited. The original
tree `/home/ubuntu/psp/build/linux` was only read: after all the work below,
`sha256sum -c --quiet gates/baseline-tree.sha256` exits 0.

Line numbers: kernel lines are at `stage2-trace` HEAD `48dcc1b9`. The kernel
sources are unchanged since `0b0a2acf` (attempt 2 changed only
`psp-initramfs.cpio`), so the kernel notes' line numbers hold. pscol and
decoder line numbers are those of the files as delivered at attempt 2
(sha256 in 5.4). In section 4, the pscol line numbers of attempt 1 were
re-mapped to the attempt-2 files by a line alignment of the two versions
(Python `difflib`, equal blocks only) and spot-checked: every reference
resolved, two by hand (old `main.c:72`, the run scan, now `pscol.c:2178`;
old `pscol.c:803`, `rq_add`, now `:837`).

**Release under review (attempt 2):** `vmlinux-0.22.bin` sha256
**`4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8`**
(936,714 B), `build_id` **`0x045b27d9`**, from `stage2-trace` `48dcc1b9`,
build `work/out/20261006T052947Z`.

---

## 0. Decisions: attempt-1 items ruled by G1, and items open now

### 0.1 Attempt-1 open decisions OD-1..OD-6 (all ruled; implemented as ruled)

| # | Item | G1 ruling (DESIGN 17) | Implemented at attempt 2 |
|---|---|---|---|
| OD-1 | `nwords` 7 for 8 words ending 0xFFFF (D3 against D10) | R-1 option (a): `nwords` = 7 with `rx[14..15]` = `ff ff` means "7 or 8", flagged `nw7or8`, read as {7, 8}; (b), (c) not approved | Kernel unchanged (`psc.c:275-280` already is option (a)). Decoder: flag and set membership (9.1). The compiled code's exit table re-derived by execution (9.2.5) |
| OD-2 | D10 window not literally identical | R-2: the 2.1 criteria are the test; three differences allowed | Kernel unchanged; window re-proved for the new build: identical to attempt 1 (5.1) |
| OD-3 | `build_id` undefined | R-4: CRC-32 (zlib, 0) of `linux_banner` = `/proc/version`; KRN compares; decoder uses `BUILD/build_id.txt` | pscol KRN (`pscol.c:442`, `:453`); decoder (`pscdec.py:234-243`, `pscdec_analysis.py:403`); `BUILD/build_id.txt` = `0x045b27d9` |
| OD-4 | Map syntax mismatch | (G2 code finding F3, not a design item) | One grammar, `work/decoder/psc_maps.py`, used by `handoff/impl/mkmaps.py` and the decoder (9.1, 8) |
| OD-5 | pscol 256 KB per process | R-5: ≤ 256 KB, both at boot | 183,040 B per process at attempt 2, one 256 KB block (1.4) |
| OD-6 | Image growth near the bound; pspboot load UNVERIFIED | R-5: bound 49,152 B per image; each G2 attempt restates both growths and the change since attempt 1 | 1.4: +44,036 B `vmlinux.bin` (5,116 B margin), +37,312 B `vmlinux-0.22.bin`; +405 B and +393 B since attempt 1. pspboot load still UNVERIFIED (R20) |

### 0.2 Open now (for the G2 reviewer, the orchestrator or the human; not decided here)

| # | Item | Where |
|---|---|---|
| OD-7 | **Measured costs above some design estimates (outside the window).** Executing the compiled code (9.2) gives, at 1 instruction per cycle and 220.9 MHz (UNVERIFIED): a watchdog tick adds +922 instructions (≈ 4.2 µs; the Nop alone +871, ≈ 3.9 µs; +990, ≈ 4.5 µs, on the first Nop of a boot); a watchdog tick that interrupts the thread inside a command adds +1,104 (≈ 5.0 µs, T2a included); every tick +48 (≈ 0.22 µs, 7.1 said ≈ 16 instructions); a tick finding the thread in a command +208 (7.1 said ≈ +33); a panel paint 228,520 instructions (≈ 1.03 ms; 7.1 said 0.2-1 ms). R-3's per-command figures hold (+557/+560, ≈ 2.5 µs, inside "≈ 460-610"). Nothing is inside S5..S20, no lock, no masking; the code is the code G1 ruled on (the kernel is unchanged since attempt 1). Whether 5.4/7.1/7.3's watchdog-path and per-tick figures need restating is a G1-text question, not a code change | 9.2 |
| OD-8 | G1 ruling red-team recommendations that need design text and were therefore not implemented: K1, K5, K6, K7 text, K8 (decoder printouts not in 10.7). K2, K3 (print part), K4 and K9 were implemented where they are code or tests (9.1) | 9.1 |
| OD-9 | pspboot loading the larger image (R20) remains UNVERIFIED; only a boot on the device settles it (an abort costs no run, 8.3) | 1.4 |

---

## 1. Integration steps performed

### 1.1 Initramfs (DESIGN 4.2; recon/build.md 1.3)

Attempt 1 (integrator):

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

**Attempt 2 (deviation I-6).** Only the collector changed. The committed
archive's `usr/bin/pscol` entry got the new bFLT (55,044 → 55,852 B, sha256
`7d7a5d78…f7c454`, the `cbuild.sh` output of `checks.sh`, 5.2) by
`work/initramfs-work/replace_pscol.py`: same inode, mode 0755, owner and
device fields; new size and mtime. The other 96 entries are byte-identical
(the script compares them and reports 96), the order is unchanged, the archive is padded to
512 B. Result: sha256 `5dde35cd…85a51a`, 1,313,792 B, 97 entries;
`cpio -itv` shows `-rwxr-xr-x root root 55852 usr/bin/pscol` and the
unchanged `etc/rc.sysinit` (772 B, lines 21-23). Commit `48dcc1b9`
"initramfs: pscol for G2 attempt 2 (run number, KRN build_id, re-send loss)"
changes only `psp-initramfs.cpio`.

### 1.2 Release build (attempt 2)

| Item | Value |
|---|---|
| Command | `/home/ubuntu/psp/work/build.sh` (normal mode, default identity: `KBUILD_BUILD_VERSION`, `KBUILD_BUILD_TIMESTAMP`, `REPRODUCE_BASELINE`, `BUILD_HOSTNAME` unset, as the log records, G1 ruling K3; `git clean -fdxq`, 0 untracked files after the clean) |
| Branch / HEAD | `stage2-trace` / `48dcc1b9dad43f0f919a859b5d9cc44771558f3d`, no tracked changes |
| Result | rc 0 (`MAKE_EXIT` 0), 187 s in the container |
| Log | `/home/ubuntu/psp/work/logs/build-20261006T052947Z.log` |
| Out dir | `/home/ubuntu/psp/work/out/20261006T052947Z/` |
| Banner | `Linux version 2.6.22 (root@psp-work-build) (gcc version 4.2.1) #1 PREEMPT Tue Oct 6 05:32:47 UTC 2026` |
| `vmlinux-0.22.bin` | **sha256 `4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8`**, 936,714 B |
| `vmlinux.bin` | `22fc39342882e04af332b2321a18b4b6373dd550c9e5f79f8d6f0ff0b01c312b`, 1,767,264 B |
| `vmlinux` | `7b8c075217f07228cc38938f5c77abf35ecd72efdb4ded13ef04d3e56ac96ae0`, 1,987,314 B |
| `System.map` | `77816657f56623d2a085ed3d8771584e5f5d01c45a5017c093b4dea328cdb5cf` |
| Warnings | 40 lines, 38 distinct; the distinct set is **identical** to the baseline normal build (`build-20260927T204657Z.log`, `diff` of the sorted unique `warning:` lines is empty) |
| `build_id` (R-4) | **`0x045b27d9`** = zlib CRC-32 of the 102 bytes of `banner.txt`, which occur exactly once in `vmlinux.bin`, NUL-terminated (`mkmaps.py` checks it); pscol's `psc_crc32` gives the same value on those bytes (5.2, `pscol_test krn`) |

**Against the attempt-1 release** (`out/20261006T021722Z`): `System.map`
differs in one line, `__initramfs_end` (881af5cb → 881af760; BSS starts at the
same page, 881b0000, so every kernel data symbol is unchanged). Below
`.init.ramfs`, `vmlinux.bin` differs in 12 bytes: the two banner copies (time
string, 0x88120055-5b and 0x881375dd-e3) and two bytes at 0x88147f58-59, the
`addiu a1,a1,-2208` of `__initramfs_end` in `populate_rootfs`. So the kernel
code, the D10 window, the capture sites (C7) and the maps are those reviewed
at attempt 1; 1.3 re-proves them anyway.

### 1.3 Proofs on the attempt-2 image

- **Initramfs in the image.** `work/initramfs-work/extract_ramfs.py` on the
  release `vmlinux`/`vmlinux.bin`: `.init.ramfs` at 0x8815e000, 333,664 B,
  the same bytes in `vmlinux.bin`, one gzip member with 0 trailing bytes;
  decompressed 1,313,792 B, sha256 `5dde35cd…` = the committed cpio. Inside:
  `usr/bin/pscol` mode 0100755, 55,852 B, sha256 `7d7a5d78…` = the delivered
  bFLT; `etc/rc.sysinit` lines 21-23 `printf "…Launching PSC collector…"`,
  `pscol&`, `printf "[  OK  ]…"`. `gunzip(vmlinux-0.22.bin)` = `vmlinux.bin`.
- **D10 window** (`impl/d10_proof.py work/prebuilt/vmlinux …/System.map
  work/out/20261006T052947Z/vmlinux …/System.map`): exit 0;
  `impl/release-20261006T052947Z/syscon-window-diff.txt` is identical to the
  attempt-1 release copy apart from the path line: 105 = 105 instructions on
  the S5..S20 paths, identical apart from stack offsets and the renaming
  s3→s7, s4→s3, s5→s4, s6→s5, s7→s6 (R-2), the same MMIO order and form, 0
  calls; hand-off checks pass.
- **Maps and BUILD.** `impl/mkmaps.py work/out/20261006T052947Z
  impl/release-20261006T052947Z/BUILD` refused nothing: every Syscon_cmd range
  and anchor instruction (now including every sub-range boundary of the
  register rows), the "all" registers (t5, t9, t8 written only in the
  prologue, the hand-off restore and the retry increment) and the banner
  check out. `BUILD/SHA256SUMS` verifies; `BUILD/IMAGE.sha256` names
  `4f9b69dc…`.
- **Executed paths** (9.2): the compiled code, run by `impl/pathcount.py`,
  writes P and W records that the decoder's parse layer decodes correctly
  (5-word 0x08 reply: `ret` 34, `nwords` 5, `ack_polls` 20, `drain` 0; the
  Nop that interrupts the thread at S14: origin WT, `t_busy` 1, EPC in S14,
  ext_flags 0x1d), and the `nwords` table of section 17 R-1 (9.2.5).

### 1.4 Image size and collector memory (DESIGN 5.3, R-5; G2 C6, C8)

| File | Reference | Ref size | Attempt 1 | Attempt 2 | Growth (attempt 2) | Margin to 49,152 B | Change since attempt 1 |
|---|---|---|---|---|---|---|---|
| `vmlinux.bin` | baseline rebuild (= the 2008 image decompressed) | 1,723,228 | 1,766,859 | 1,767,264 | **+44,036** | **5,116** | +405 |
| `vmlinux-0.22.bin` | baseline rebuild (`work/prebuilt`) | 899,402 | 936,321 | 936,714 | **+37,312** | **11,840** | +393 |
| `vmlinux-0.22.bin` | `pspboot-baseline` (2008 `2.6.22-uc1`, what the stick boots today) | 899,282 | 936,321 | 936,714 | +37,432 | — | +393 |
| BSS (`System.map`) | baseline | — | +653,600 | +653,600 | unchanged | — | 0 |

Both growths are inside the 49,152 B bound (R-5). All of the change since
attempt 1 is the initramfs (`.init.ramfs` 333,259 → 333,664 B, +405; the
kernel code and data are unchanged, 1.2). Whether pspboot loads 1,767,264 B
is UNVERIFIED (R20, OD-9).

**pscol (C8, R-5):** bFLT 55,852 B; `flthdr` rev 4, PIC-GOT, stack 0x4000;
text incl. the 64-byte header 52,768 (`Data Start` 0xce20), data 2,912, bss
110,976, stack 16,384: text + data + bss + stack = **183,040 B**, one
**256 KB** block per process under `CONFIG_SONY_PSP` (`fs/binfmt_flat.c:471-472`),
both at boot (attempt 1: 183,968 B). R-5's bound (≤ 256 KB) holds with
79,104 B of margin.

### 1.5 Package (DESIGN 9; RUNBOOK A)

```
rm -rf /home/ubuntu/psp/work/deploy/uClinux_TRACE
BUILD_DIR=/home/ubuntu/psp/handoff/impl/release-20261006T052947Z/BUILD \
PSPBOOT_DIR=/home/ubuntu/psp/pspboot-baseline /home/ubuntu/psp/work/package.sh \
    uClinux_TRACE /home/ubuntu/psp/work/out/20261006T052947Z uClinux uClinux_FIX uClinux_WIP
```

Exit 0, status COMPLETE; names checked against `uClinux`, `uClinux_FIX`,
`uClinux_WIP` ignoring case.

- **Stick folder** `deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/`: exactly
  the four files of RUNBOOK "What you need". `EBOOT.PBP`, `kmodlib.prx` and
  `pspboot.conf` are `cmp`-identical to `/home/ubuntu/psp/pspboot-baseline/`
  (`pspboot.conf` verbatim: `kernel=vmlinux-0.22.bin`,
  `cmdline=console=tty osk=Dv4`); `vmlinux-0.22.bin` is `cmp`-identical to the
  release build's.
- **`deploy/uClinux_TRACE/SHA256SUMS`** (`sha256sum -c` in the folder: all OK):

```
c915ba8ac0649fb537ca6b665bc2243d253f70907710e1b1a57838d46e7daacc  EBOOT.PBP
69adde5e6ad3b2d509a0d6d08a0122f0687cb6cf890211069229363fe0379846  kmodlib.prx
e555890d36878db975267c6a3a375e9b611c205099e0bdc25343f295437d7af7  pspboot.conf
4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8  vmlinux-0.22.bin
```

- **`deploy/uClinux_TRACE/BUILD/`** (I-5; not for the stick; the decoder's
  `--build`): `System.map`, `vmlinux`, `banner.txt`, `build_id.txt`
  (`0x045b27d9`), `epcmap.txt`, `regmap.txt` (grammar 2), `panellayout.txt`,
  `IMAGE.sha256` (`4f9b69dc…  vmlinux-0.22.bin`), `SHA256SUMS`; a verbatim copy
  of `handoff/impl/release-20261006T052947Z/BUILD/`.
- **`PROVENANCE.txt`**: out dir, log, commit `48dcc1b9`, no tracked changes,
  banner, pspboot source, BUILD source and `build_id`.

---

## 2. Commits

### 2.1 `git log --oneline baseline..stage2-trace`

```
48dcc1b9 initramfs: pscol for G2 attempt 2 (run number, KRN build_id, re-send loss)
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

`baseline` is `775f8372`: the original tree plus `.gitignore`. Reviewed history
was not amended or rebased; attempt 2 added one commit.

- `ca7dac0a` is the interface commit (`include/linux/psc_format.h`, unchanged
  since).
- The 14 kernel commits `4c4e7aee`..`0b0a2acf` each compile and link (kernel
  notes 6a). **Their git author "Recon C (Claude agent)" is wrong:** it is a
  leftover `user.name` in `work/linux/.git/config` from Recon C, who created
  the repository in Stage 0. The actual author of those 14 commits is the
  Stage 2 kernel implementer (Claude agent), as `IMPLEMENTATION-kernel.md`
  ("Author: kernel implementer (Stage 2)") and the gate log's Stage 2 run
  `wf_8f8df699-258` record (G2 attempt 1 F7). History is not rewritten.
- `c135ecdd` is the attempt-1 integrator's commit (author "Integrator").
- `48dcc1b9` is attempt 2's only commit (the initramfs, 1.1). Before it,
  `work/linux/.git/config` was set to `user.name = Stage 2 kernel implementer
  (Claude agent)`, `user.email = stage2-kernel-implementer@localhost` (the
  email was changed too, from `recon-c@localhost`, so that both fields name
  the role); the commit was made by the G2-attempt-2 implementer under that
  identity. The commit message ends with the Co-Authored-By line requested
  for this session.

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
 psp-initramfs.cpio             |  Bin 1257984 -> 1313792 bytes
 19 files changed, 3246 insertions(+), 23 deletions(-)
```

Every changed line is mapped as follows:

- The kernel files: kernel notes, sections 2-4.
- `.config`: `4c4e7aee`.
- `psp-initramfs.cpio`: section 1.1 (attempt 1 `c135ecdd`, attempt 2 `48dcc1b9`).

The generic-kernel hooks are inside `#ifdef CONFIG_SONY_PSP`. The syscon
timeout patch is still present, with the same defines `SYSCON_SPIN_MAX`
1000000 and `SYSCON_RETRY_MAX` 16 (`syscon.c:12-13`), the same bounds and the
same teardown writes. Its hunks no longer reverse-apply textually because new
lines sit in their context (kernel DV-17); section 9.3 gives the transaction
body's diff against the baseline.

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
| 1.2 | SC record, every field | `psc.c:259-302` (`psc_fill_sc`), `:304-370` (`psc_fill_thread`: lc, led, pre, panel flag); captures `syscon.c:119-123`, `:166`, `:171`, `:182`, `:203-206` | parses P records (`record_scan` `:1127`) | `norm_record` (flag `nw7or8`, `pscdec_parse.py:162-168`), `nwset` (`pscdec_analysis.py:20`), `psc_format` | DV-2, DV-3 (ruled: section 17 R-1), DV-9 |
| 1.3 | W record + 208-byte extension | `psc.c:372-425` (`psc_fill_wext`), `:493-519` | WDOG check `:2368-2381` | `Model.w_step` | DV-9 |
| 1.4 | POLL record | `psc.c:842-907`; fields in `joypad_psp.c` (2.5 row) | POLL, BTN checks | `simulate_polls` | DV-10 |
| 1.5 | S record | `psc.c:655-730`; `ms_psp.c:349`, `:364`, `:378`, `:393` | verdict windows `:768`, `:812` | META repeat, S windows in the timeline | none |
| 1.6 | M record, fill-once, `m_dropped` | `psc.c:475-492` | drained like the others | parsed as SC | none |
| 1.7 | Stats block, 192 words | `psc.c:1069-1120` (`psc_stats_snapshot`); writers at the hook sites | `stats_read` `:424`; KRN `build_id_read` `:453`, compared at `:442` (R-4) | `parse_stats`, `stats.csv` | DV-12 (ruled: R-4) |
| 1.8 | Origin by explicit flag, then `current == psc_jp_task` | `psc.c:197-257` (`psc_sc_entry`), `:169-176`; flag `psp.c:390-392`, `:578-580` | WDOG check | WT/WB/P/M from `ctx` | none |

### 4.2 Section 2: capture points

| § | Element | Code | Deviations |
|---|---|---|---|
| 2.1 A1 | Entry, inline, no call | `psc.c:197-257`, inline from the wrapper `psc_syscon_cmd` `psc.c:526-533` | **DV-1** (wrapper structure; `Syscon_cmd` keeps its name) |
| 2.1 A2 | Per-attempt defaults | `syscon.c:127` `spin = 0`; the other sentinels are derived at exit (`psc_fill_sc`) | **DV-2** |
| 2.1 A3 | In-window captures to stack slots | `syscon.c:119-123` (slots), `:166`, `:171`, `:182`, `:203-206` | DV-4 (ruled: R-2) |
| 2.1 A4 | −3/−4 → `goto out`; exit hand-off; `psc_sc_exit` | `syscon.c:165`, `:206`, `:309-310`, macro `:17-61`; `psc.c:188-191` (`psc_xfer_out`), `:427-520` (`psc_sc_exit`); callers `syscon.c:330`, `:344`, `:419` | DV-1, DV-3, DV-5, DV-17 |
| 2.1 G2 window criteria | objdump proof | `impl/d10_proof.py` → `impl/syscon-window-diff.txt`; re-run on each release build: `impl/release-20261006T021722Z/syscon-window-diff.txt` (attempt 1) and `impl/release-20261006T052947Z/syscon-window-diff.txt` (attempt 2), both exit 0 and equal apart from the path line | DV-4 (ruled: R-2) |
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
| 4.1 | Collector derived from telem's FP-free parts | font `:2479-2510`, formatting `:236-275`, mice `:2060`, blit `:2757`; `os_target.c:110`, `:139`, `:149` | none |
| 4.2 | rc.sysinit lines; one binary, two processes; supervisor (setsid, `/dev/null`, signals, `mkdir PSCLOG`, run number, nonce, vfork+execve `/usr/bin/pscol -w rrr nonce`, 2 s watch); takeover in-process; worker start (conlevel EVENT, seek to `durable_next`, names budget, pid classes); guards; "never" list | **initramfs `c135ecdd`** (`etc/rc.sysinit:21-23`, `usr/bin/pscol` 0755; the pscol entry replaced in `48dcc1b9`); `main.c:70`, `:80`, `:90`, `:92`, `pscol.c:2178` (`pscol_run_scan`, called at `main.c:93`), `:96`, `:110-114`, `:116`, `:122-133`; `pscol.c:2966` (`worker_main`), `:2775` (`worker_init`), `:2810`, `:2342`, `:2242`, `:2296`; guards `:301`, `:316`, `:341`, `:286`, `:2928` | P-1 (ruled: R-5), P-7, P-13, P-15, I-1, I-6 |
| 4.3 | Worker tick, steps 1-10 and bounds | `:2847` (`worker_tick`), `:424`; drain `:901`, `:949`, `:1018`, `:1047`; KMSG/syslog/PROCS/mice/meminfo `:2048`, `:2085`, `:2060`, `:2024`; flush `:1841`, `:1913`; creation `:1771`; META `:1225`; bad region `:1963`; HUD `:2757`; guards and `nanosleep` `:2920-2921`, `:2973`; fit test `:1880`; EVENT queue `:375` | P-14 |
| 4.4 | Segment files: steps 1-8, creation rule, use and switch (TE10), hold | step 1 `:1544`, `:1590-1618`, probe `:1604`; step 0 `:1470`; steps `:1689`, `:1642`, template `:528`, `os_target.c:48`; verdict `:671`, `:692`, `:1417`, `:1715`; stop/abandon `:1348`; next attempt `:1324`, `:2242`; completion `:1655`, `os_target.c:99` (fadvise 4254, seven slots); cap and creation rule `:1756`; names `:2153` (`pscol_tname`), `:2205`, `:2242` (`names_scan`; F2); switch `:1782`, `:1789`, `:1793`, `:1816`, hold `:913-917` | P-2, P-3, **P-4**, P-10, P-12 (replaced by the F2 rule, 6.2) |
| 4.5 | `durable_tick` / `durable_next` via ctl op 1; the kernel compares and paints | pscol `:1940`, `:882`, `:493`; kernel `panel:317-320`, `psc.c:1147-1195` | none |
| 4.6 | Failed flush never overwritten; range re-send; fsync-error DURABLE (b30); bad-region escape; read-only; ENOSPC; takeover rule | `:1913`, `:837`, `:949-1015`, `:1956`, `:1919`, `:1963`, `:2877`, `:1771`; `main.c:122-133`; re-send accounting (F6) `:837-886`, `:972-979`, `:1035-1041`, `:1956-1960` | P-16 |
| 4.7 | META detection, display (not red, no panel paint), clearing and bypass | pscol `:1225`, `:1102`, `:1199`, `:1214`, `:1729-1736`, `:2911-2913`; kernel ctl op 4 `psc.c:1147-1195`, panel line 6 field; decoder `Analysis.meta_repeat` | P-10 (16 tracked sectors) |
| 4.8 | Sector classes from the stats geometry; extent table by FIBMAP; S windows by `pread`; flush and step verdicts; speed; geometry self-check | pscol `:541`, `:561`, `:768`, `:812`, `:642`, `:736`, `:1401`, `:1417`; kernel stats 153-159 (`ms_psp.c:202-203`, `fs/fat/inode.c:1418-1420` → `psc.c:912-926`), S `flags` b7 (`ms_psp.c:262-275`) | P-4, P-10; D-19 (FATM range in the decoder's repeat) |

### 4.5 Section 5: budget

| § | Element | Where it is realised or checked | Notes |
|---|---|---|---|
| 5.1 | Bytes to the stick | n/a: budget figures. Realised by the 4.3 caps and chunk sizes in pscol. Checked by Stage 3 "Volume" | pscol's nominal 5-minute host run produced every chunk type with 0 records missing; the volume figures are for Stage 3 |
| 5.2 | Memory Stick operations (H10 exposure) | n/a: budget. Measured on the device by `led_calls`, S records and the read-back ORs | none |
| 5.3 | Memory and image | Kernel: BSS +653,600 B (`psc_mem` 653,584 + 3 words), as budgeted (≈ 653 KB). Userland: 2 × 256 KB (P-1, ruled R-5; 183,040 B per process at attempt 2). Image: section 1.4 (within the 49,152 B bound, R-5) | P-1 |
| 5.4 | Time added | Zero instructions inside S5..S20 (proof 1.3; R-2). Outside the window: measured by executing the compiled code, section 9.2 (`impl/pathcount.py`, `release-20261006T052947Z/pathcount.txt`); on the device `p_rec_cost_*`, `w_rec_cost_max`, `panel_cost_*` (stats 24-26, 118-124, 148), HUD line 10 | DV-1 (+208 B stack on the thread path, +216 B on the Nop path, 9.2), DV-15 |

### 4.6 Section 6: coverage matrix (the decoder classifies; kernel and pscol supply the fields)

| § | Element | Decoder | Deviations |
|---|---|---|---|
| 6 | H0-H10 rows; template; triple (trigger, state, H8 flags); early death without C0 | `ana`: `_stopped`, `_states` (H1 with the 9.5 variant, H2, H3, H5, N2b before H6, H6 with template/`rx2 literal`, N2, N3, N11), `_h7`, `_n10`, `_h8`, `_triggers` (H4, H4 two-stage, WB, H10, N1m, N1p, N1, H10b, LEDSPLIT, N8), `learn_template`, `run`; H0 raw windows `window_*.txt` | D-7, D-8, D-9, D-10, D-11, D-12, D-13, D-14 |
| 6.1 | N1, N1m, N1p, N2, N2b, N3-N11, H10b, WB, LEDSPLIT | the same functions; `crosscheck`, `holder`, `suspension` | D-9..D-14; D-24; OD-4 resolved (LEDSPLIT loaded value and P6 j from the release regmap, `psc_maps.py`) |
| 6.2 | Onset timing: rings ≥ 114 s; first complete drain | kernel ring sizes (`fmt.h`, 3.1); pscol catch-up `:901-1052` | none |
| 6.3 | Phase in the 1250-tick cycle: before, across, after | `Analysis.placements` | none |

### 4.7 Section 7: perturbation

| § | Element | Where | Notes |
|---|---|---|---|
| 7.1 | No lock, no IRQ masking, no new MMIO read; one printk; console log level 4 | kernel notes 6 (C3: no lock, interrupt masking or delay anywhere; the only new memory-mapped accesses are panel VRAM stores); pscol `conlevel` at worker start (`syscall(__NR_syslog, 8, 0, 4)`, `:2814`) | DV-1 (wrapper call and stack) |
| 7.2 | Zero instructions in the window; G2 objdump check | `impl/syscon-window-diff.txt`, `impl/d10_proof.py`; release re-runs in `impl/release-20261006T021722Z/` and `impl/release-20261006T052947Z/` | DV-4 (ruled: R-2) |
| 7.3 | Why this neither hides nor causes H4; no-death inference | n/a: statement. The pre-registered inference is in the decoder (`no_death_inference`, `interleave_stats`); `wk_*` and `pre_*` are recorded (2.11) | none |
| 7.4 | Userland load parity with telem: 272 row writes, syslog type 3, `/proc` reads, mice client; fadvise instead of `drop_caches` | pscol `:2757` (272 writes of 1,920 B, rows 0-175 then 0-95), syslog `os_target.c`, fadvise `os_target.c:99` (objdump-checked: seven slots) | P-2 (`writev`) |
| 7.5 | Own stick I/O and H10 | n/a: statement. Exposure recorded through S records, LED hooks and creation EVENTs | none |
| 7.6 | Kernel identity: timeout patch unchanged | `syscon.c:12-13` defines unchanged; behaviour unchanged; text hunks displaced; body diff against the baseline in 9.3 and `impl/release-20261006T052947Z/syscon-cmd-body.diff` | DV-17 (9.3) |
| 7.7 | No floating point | pscol: `cbuild.out`/`CHECKS.txt`, FP registers 0, FP mnemonics 0, no soft-float/printf/strtod/atof symbols, `flthdr` valid with stack 16384. Kernel: new and changed objects have 0 FP instructions and no soft-float or 64-bit division helpers (kernel notes 6b) | none |

### 4.8 Section 8: self-test

| § | Element | Where | Deviations |
|---|---|---|---|
| 8.1 | Boot `printk` `PSC5 P4096 ...` from W seq 0 | `psc.c:1242-1244` (`PSC_BOOT_PRINTK_FMT` in `fmt.h`) | none |
| 8.2 | HUD (ten lines, ≤ 35 characters, rows 0-175); checks KRN, WDOG, STICK, REC, PANEL, SUP, POLL, BTN; second PSC TEST | pscol `:2554` (`ms_line`), `:2611`, `:2717`; checks `:2368-2381`, `:2383`, `:1127`, `:2409`, `:2422`; panel test via ctl op 3 (kernel `psc.c:1147-1195`, `panel:301-338`) | **P-5**, P-6, P-7, P-11; KRN checks `build_id` (R-4: `pscol.c:442`, `:453`) |
| 8.3 | Abort rule at 3:00 | n/a: runbook. HUD states `MS NO STICK`, `MS SLOW`, `MS DIR FULL` (pscol `ms_line`) | P-6 (from uptime 170 s) |
| 8.4 | `DEAD?` display-only hint | pscol `:2431` | P-8 |
| 8.5 | Host-side tests | n/a: Stage 3. Already partly exercised: pscol `test/` (28 verdict vectors, HUD render, step-0 burst, IF4, IF7b, TE10, and at attempt 2 names, KRN, re-send loss; section 5.2) and decoder `test/run_tests.py` (37 tests, 11 of them new at attempt 2; 5.3). Not yet done: VFAT-FI, the ring/reader code on the host, the takeover, the panel render on the host | — |

### 4.9 Section 9: runbook

| § | Element | Where |
|---|---|---|
| 9 | Deploy `PSP/GAME/uClinux_TRACE/` with the baseline's `EBOOT.PBP`, `kmodlib.prx`, `pspboot.conf` and our checksummed `vmlinux-0.22.bin` | n/a: runbook. Package: `/home/ubuntu/psp/work/deploy/uClinux_TRACE/` (1.5); I-2 |

### 4.10 Section 10: decoder (`work/decoder/`)

| § | Element | Code | Deviations |
|---|---|---|---|
| 10 (intro) | Inputs: files, `--raw`, System.map, `epcmap.txt`, `regmap.txt`, `panellayout.txt`; inputs never modified | `cli` (`-o`, `--build`, `--times`, `--raw`); `BuildInfo.load` (`pscdec_analysis.py:120`) | OD-4 resolved: one grammar, `psc_maps.py` |
| 10.1 | Words 20-22 against System.map, word 2 against `build_id`; refuse the EPC analysis otherwise | `Model._build_check` (`pscdec_analysis.py:403`: first stats block, FILEHDR `/proc/version` CRC-32), `label_of`; `build_id.txt`/`IMAGE.sha256` from `--build` (`pscdec.py:234-243`) | D-17 (ruled: R-4), D-23 |
| 10.2 | Chunks, nonce CRC, run selection, confirmed extent, merge/conflicts, `--raw`, raw-image rule | `parse`: `candidates`, `accept`, `crc_ok`, `load`, `_extents`, `_bump`, `_merge`, `parse_recs`, `_raw_rule`, `RAW_REQUIRED_EVENTS`; `cli` exit 3. Writer side in pscol `:503` (`chunk_put`), `:1470-1499`, `:1841-1898`, `:2446`, `:2468` | D-1, D-2, D-3, D-4, D-5, D-18 |
| 10.3 | Record strings, dropped `seq` 0xFFFFFFFF, explicit gaps, 16-bit links | `norm_record`, `Model._gaps`, `Model._links` (`_expand`, `_link_by_time`) | none |
| 10.4 | Stats, `stats.csv`, counter decreases | `parse_stats`, `_outputs` | none |
| 10.5 | Time reconstruction | `Model._sc`, `_timecheck`, `_uptime_offset`, `rec_line`, `crossings.txt` | D-6 (operator times) |
| 10.6 | EPC map and register map (Stage 2 deliverables) | **Kernel side:** `impl/mkmaps.py` writes the BUILD directory, `impl/release-20261006T052947Z/BUILD/` (copied to `deploy/uClinux_TRACE/BUILD/`). **Grammar:** `work/decoder/psc_maps.py` (both sides). **Decoder side:** `BuildInfo.load/label/regval` (`pscdec_analysis.py:120-174`), `STEP_PPOINT` with S0 → P0 (`:179`), `Model.w_step` (k, j, `pending`, ptr cross-check, `:570-618`) | OD-4 resolved; D-16 replaced by the grammar |
| 10.7 | Steps 1-8 | `cli.timeline`; `learn_template`; `simulate_polls`; `onset_candidates`, `placements`; classification (6.1 row above); `_outputs`, `_report` (nw7or8 section, `pscdec.py:560`); `harm_table`, `fisher_one_sided`, `ub95`; `no_death_inference`; `nwords` 7 or 8 by set membership (`nwset`, `Template.nwords`/`own_valid` `:234-251`, `crosscheck`) | D-7, D-20, D-21, D-22, D-24 |
| 10.8 | Panel from photographs | `panel_parse`, by keyword | D-15: `impl/panellayout.txt` now exists, so the parser should switch to its columns |

---

## 5. Evidence summaries

### 5.1 D10 proof

| Item | Value |
|---|---|
| Script | `/home/ubuntu/psp/handoff/impl/d10_proof.py` |
| Attempt 1 | `impl/syscon-window-diff.txt` (build `20261006T012834Z`), `impl/release-20261006T021722Z/syscon-window-diff.txt` |
| **Attempt 2** | `impl/release-20261006T052947Z/syscon-window-diff.txt` (exit 0), identical to the attempt-1 release copy apart from the path line |

Result: 105 instructions on both sides; identical apart from stack offsets and
the consistent renaming s3→s7, s4→s3, s5→s4, s6→s5, s7→s6; the same MMIO
loads and stores in the same order and form; 0 calls in the window; hand-off
checks pass. Under section 17 R-2 this is the D10 acceptance test (the 2.1
criteria with the three allowed differences: stack offsets, value-preserving
renaming, the first −3 exit's delay slot). Not literal identity, by ruling.

### 5.2 pscol CHECKS (`/home/ubuntu/psp/work/pscol/CHECKS.txt`, 2026-10-06 05:27 UTC, `checks.sh 50`)

Build (container, gcc 4.2.1): `COMPILE_OK`, **0 warnings** (`-Wall -W`); FP
registers **0**, FP mnemonics **0**, 7.7 grep **0**; no
`printf`/`strtod`/`atof`/soft-float/libm, `malloc`/`opendir`/`fopen` or `fork`
symbols; `flthdr`: bFLT rev 4, PIC-GOT, stack **16,384**; bFLT **55,852 B**,
sha256 `7d7a5d78…f7c454` (the binary in the initramfs); one **256 KB** block
per process (1.4). Host tests (`test/run.sh`, all PASS; ASan/UBSan clean on
every test):

| Test | Result |
|---|---|
| S-record verdict vectors | 28/28 |
| HUD render | PASS (longest line 34) |
| Nominal 5 min at 52 KB/s | SELFTEST PASS, 0 missing |
| Step-0 burst | 8/8 |
| TE10 hold-and-resume | 6/6 |
| IF7b | PASS (105 names, 13 ticks; later creations ≤ 14 names) |
| IF4 sporadic, 30 min | 200/200 (50 seeds × 4 speeds), 0 missing |
| **names (F2, new)** | 6 directory cases + the name parser (11 names): run number advances over lower-case `t001001.bin` names of an earlier boot, `nnn` restarts at 001 for the new run, a takeover continues this run's `nnn`, one slot per 8.3 file, a Mac long name 2 slots, a lower-case long name and a deleted slot counted on the safe side, a 64-byte `getdents` buffer |
| **krn (R-4, new)** | KRN green when word 2 = CRC-32 of `/proc/version`, red when it differs by one bit; with the **packaged** `BUILD/banner.txt` bytes against `BUILD/build_id.txt` `0x045b27d9`: green, and red with one banner byte changed (`impl/release-20261006T052947Z/pscol-krn-packaged-banner.txt`) |
| **resend (F6, new)** | 3 scenarios (rings lapped before the first drain with the first flush FAILED; the same with two FAILED; a 130 s stall inside an fsync with the stick refusing 1.5 s): `lost_total` equals the records missing below `durable_next` (915, 1,020, 1,020). The attempt-1 accounting gives 1,674, 1,779, 1,869 on the same scenarios (checked on a scratch copy with only the two accounting lines reverted) |
| Decoder cross-check (`pscdec_parse.load` on the simulated stick) | 3/3 |
| Original manifest | exit 0 |

The supervisor/takeover processes, the guard exit and the real system calls
are not run on the host; the vfat model is a model (attempt 1 unchanged).

### 5.3 Decoder TESTS (`/home/ubuntu/psp/work/decoder/TESTS.txt`, 2026-10-06, 37 tests, all OK)

The attempt-1 26 tests still pass. New at attempt 2:

| Class | Tests |
|---|---|
| `ReleaseMaps` (F3; on the **release** maps `impl/release-20261006T052947Z/BUILD`) | maps load with no error and S0 maps to P0; W records at **S11** (8 EPC/register cases, `epc` and `lc_epc`): `k` from `t0` with offset 0 or 2 by EPC; at **S18** (9 cases): `j` and `pending`, ptr cross-check, and a deliberately inconsistent `a3` flagged; every EPC of the **8th receive iteration** (18 EPCs: `pending` exactly between the status load and the data load, j 7 then 8, "P6, empty-FIFO pop" named; K2); the P6 cross-check (flagged j = 7 allowed, empty pop named, j = 3 with nwords 5 inconsistent); **LEDRMW**: the loaded value at every EPC of both read-modify-writes; a map in the old syntax is an error |
| `NwordsSevenOrEight` (R-1, K9) | 7 words; 8 ending 0xFFFF (same bytes, both flagged {7, 8}); 8 not ending 0xFFFF (exact 8); set membership against a template and the code expectation; REPORT section and `p.csv` columns |
| `BuildCheck` (R-4, K9) | the packaged `build_id`: EPC analysis enabled; another build's `build_id` (a rebuild of the same commit): REFUSED with the reason, parsing still runs; a FILEHDR whose `/proc/version` CRC-32 differs from word 2: reported |

`check_format.py` exits 0 (355 field comparisons, 253 constants). The synth
streams' `build_id` is now the CRC-32 of their own banner (R-4), and their maps
use grammar 2.

### 5.4 Provenance (attempt 2)

Kernel: `stage2-trace` `48dcc1b9`; out `work/out/20261006T052947Z` (1.2).
Release directory: `/home/ubuntu/psp/handoff/impl/release-20261006T052947Z/`.

| File | sha256 |
|---|---|
| `deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin` (release) | `4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8` |
| `work/linux/psp-initramfs.cpio` (`48dcc1b9`) | `5dde35cd2f372dc174d27ee1694641e5ed4243dcf47b21cfe037e5c8bc85a51a` |
| `work/pscol/pscol` (bFLT, in the initramfs) | `7d7a5d785da565caf94e84010945b89765e64332d4cecb577686ecaa58f7c454` |
| `work/pscol/pscol.c` | `1e89ac0a252d6c52f61e3d6d37791f554488f063138821134e2e81fc4c640049` |
| `work/pscol/pscol.h` | `50afcf0a307ef0d3208589fda4d7d5d44b1727342721916c83e842e188e494fe` |
| `work/pscol/main.c` | `c069a958c57f5ccb114773d58cf8d91ec67172643d86db88513f30d61bc15736` |
| `work/pscol/os_target.c` (unchanged) | `5e6becf37301691916c2f13109b2d52177a6d066a343a89f182d2b88ddd613cc` |
| `work/pscol/cbuild.sh` | `97f6f0f1179151de51c1ff5c12d7a1ada9e7c3968b3db4c895b9f0d0385e15bd` |
| `work/pscol/checks.sh` | `03a5356d9eee37928511b7f0f9a78bee6d5f1272d3b4dffc103cf9ecc7d65a50` |
| `work/pscol/rc.sysinit.patch` (unchanged) | `61b8d0cad25973491b706fcbb9fdffaf1c88caa148117aa9c371863da4ac103b` |
| `work/pscol/test/sim.c` | `04e9ca80a91184bc4a68a84620b9c809187b814cc31f788e5cf284d57d42f9b6` |
| `work/pscol/test/vectors.c` (unchanged) | `bcb61bf019c61b4672b4f2f93772e9e2569ddbc56813644494242a45bbfaa1ae` |
| `work/pscol/test/run.sh` | `dbcd09f98ec28d846018a4cbfd86590836e4246143b67d817372162e6c8bd2ad` |
| `work/decoder/psc_maps.py` (new) | `27bb32b7a29baf66b88a78baef057067babc6b76c1e08948fe41993a71b6c055` |
| `work/decoder/pscdec.py` | `c566c7e24a1b7e4032cc30a675b9242d18a62b174bff712a437e41a936f842f3` |
| `work/decoder/pscdec_parse.py` | `167723ee6f77486d903c459909c9c68d8c3599c4b33480b40bdda905bd834947` |
| `work/decoder/pscdec_analysis.py` | `eae4c09f3e3b566b4be7e79634a84b367b2d10d489247b1f010c4e3ea19d4b48` |
| `work/decoder/psc_format.py` (unchanged) | `8d6154b97c4d69099f06c7501c81f3e864202e3e627490875afd6f5729856a81` |
| `work/decoder/synth.py` | `ef1282610f45152cdb7c18a72b94659ae4a8d269ccf91f446cc6d490e54ac5d7` |
| `work/decoder/test/run_tests.py` | `e1e2dd489f03fd5efff77b1ab55beb5e21f4cee0d2cfc1cf0f6181dd4fb83584` |
| `handoff/impl/mkmaps.py` | `08d1e98ef5c467c97a3fb789d45bd237c5f565f37461ea0cb3c9612b4b87b519` |
| `handoff/impl/pathcount.py` (new) | `8bf8633e153d7fbb53eca77f98f957c4b654363040c4e1edc146cfa6c89274d4` |
| `handoff/impl/d10_proof.py` (unchanged) | `6d4319931d5e78b9a2c9e169f5994f0839cc784ffcb4eae417cc39498a746864` |
| `work/initramfs-work/replace_pscol.py` (new) | `f337ba8a5994e57ce47db01865ec08985571f7961a0edbd20bf255297e09a454` |
| `work/package.sh` | `b26874e97302e4ba2506cd8ec736f64a74f79d6a8d67c23608a31e9154e24d16` |

Attempt-1 values (for the reviewer's comparison): `pscol.c` `6fd80760…`,
`pscol.h` `5beecf47…`, `main.c` `61770c8b…`, `cbuild.sh` `1f4f39ee…`, bFLT
`e5090df3…`, cpio `012cdc33…`, release `c72459e3…` (`build_id` 0x9b3c599e),
decoder `pscdec.py` `7111cb01…`, `pscdec_parse.py` `07399bed…`,
`pscdec_analysis.py` `dd1e5033…`, `synth.py` `6c6f2348…`, `run_tests.py`
`6ab80c5a…`.

---

## 6. Every deviation from the design, with its reason

### 6.1 Kernel (`IMPLEMENTATION-kernel.md` section 4)

| # | Deviation | Reason | Touches |
|---|---|---|---|
| DV-1 | The transaction keeps the name `Syscon_cmd`. A wrapper, `psc_syscon_cmd`, does A1 inline, calls it, then calls `psc_sc_exit`. The captures are locals of `Syscon_cmd`, handed over at the exit label through an opaque asm to `psc_xfer_out` (a per-origin static area) | With gcc 4.2.1 every other arrangement changed the register allocation or caused a base-address reload inside S5..S20. Costs a call and about 280 B of stack on each path (Nop included); measured at attempt 2: +208 B on the thread path, +216 B on the Nop path (9.2). EPCs in the wrapper are ENTRY, in `psc_sc_exit` REC (P0) | D10, in the direction of keeping it |
| DV-2 | A2 is reduced to one per-attempt store (`spin = 0`). The other sentinels are derived at exit with the same values. Corner: a drain of exactly 1,000,000 words that then finds the FIFO empty reads `drain` 0, not 0xFFFF | Each further store in the retry loop changed register choice in the window | none |
| DV-3 | `nwords` comes from the receive loop's counter register `t0` at the exit. Exact except: 8 words with the last word 0xFFFF reads 7 | Any C use of `ptr`/`i` after the loop adds 2 instructions per word in S18; the machine state after S19 cannot separate the two cases | D3, D10: **ruled by G1** (section 17 R-1, option (a)); the kernel is unchanged and the decoder reads the case as {7, 8} (9.1) |
| DV-4 | The window is identical apart from stack offsets, a consistent renaming of five callee-saved registers, and one delay slot after the −3 exit decision | Caused by the A2 store; without it `drain` would be undefined. The design's 2.1 criteria hold | D10: **ruled by G1** (R-2: the 2.1 criteria are the test; the three allowed differences) |
| DV-5 | In `psc_sc_exit` the snapshots and the `t_busy` clear come before filling and publishing | Keeps W `t_busy`/`p_head` consistent with `wn`/`w_head_lo`, and freezes the `lc`/`led_cmd`/`pre` words during the copy | none |
| DV-6 | T1: only `mfc0 $9` runs before the Count reset; the accounting runs after the reset with the same `c_pre`. `c_pre_cur` is stored for the W extension | One instruction before the reset, as the design allows (1-2) | none |
| DV-7 | `psp_watchdog_tick`: the watchdog's own instructions are unchanged, interleaved with the T1 store and the `wd_ctx` stores | Compiler scheduling; the design asks for the flag stores | none |
| DV-8 | "EPC inside `Syscon_cmd`" = from `Syscon_cmd` to the next syscon.c function in link order, computed once | gcc no longer emits syscon.c in source order | none |
| DV-9 | W records have `lc_dtick` 0 (all `lc_*` 0 as 1.3 says), not the 0xFFFF "none" of 1.2; `lc_flags` b0 = 0 | 1.3 and 1.2 conflict; 1.3 is specific to W | none |
| DV-10 | POLL `stage_max` excludes stage 17 | Every iteration reaches 17, so the field would be constant | none |
| DV-11 | `qfree_stage` 3 is set after `down(list_sem)` succeeds; a failed down goes from 2 to 5 | The closer blocked in `:353` stays at 2 (the H9 signature) | none |
| DV-12 | `build_id` = zlib CRC-32 of `linux_banner` (= `/proc/version`) | The design gave no value | **Adopted by G1** (R-4); KRN and the decoder implement it (9.1) |
| DV-13 | Panel: 40-column fixed layout (`panellayout.txt`); the clearing paint is counted like a paint and sets `panel_cmd_id` | A clearing paint is interrupts-off time too, which N1p must see | none |
| DV-14 | Guard words armed in `psc_init` (late_initcall) | The design does not say when | none |
| DV-15 | Hook S gate: 3 loads and 2 compares per switch (design: 1 load, 1 compare); `psc_tick_hook` is a call (≈ 6 more instructions per tick; measured at attempt 2: a tick +48 instructions in all, 9.2) | Implementation cost, outside `Syscon_cmd` | none |
| DV-16 | No kernel-initiated "PSC TEST" at init | Not in the design: the test is requested by the collector through ctl op 3 | none |
| DV-17 | The timeout patch's text hunks no longer reverse-apply; its defines, bounds, teardown writes and return values are unchanged | New lines in the hunks' context (hand-off macro, slot declarations, `goto out`, `out:`) | C2: body diff against the baseline in 9.3 |
| DV-18 | `ctl` returns −EINVAL for slot ≥ 8 or seconds outside 1..10; a partial write returns the bytes applied; op 1 writes `durable_next` before `durable_tick`, op 4 `meta_tick` before `meta_sector` | Input validation; ordering so the interrupt never sees a new tick with old positions | none |

### 6.2 pscol (`IMPLEMENTATION-pscol.md` section 4)

| # | Deviation | Reason | Touches |
|---|---|---|---|
| P-1 | 256 KB per process (512 KB for both), not ≤ 128 KB; extent tables 9.2 KB, not ≈ 6 KB | `fs/binfmt_flat.c:471-472` forces text into the same `kmalloc`; text + data + bss + stack = 183,968 B. Still allocated only at boot | figure **corrected by G1** (R-5: ≤ 256 KB); attempt 2: 183,040 B |
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
| P-12 | (attempt 1: used slots include `.`/`..` and LFN slots, and counted our own short names as long names.) **Replaced at attempt 2 (F2):** `.`/`..` one slot each; a name that cannot be a short-only entry 1 + ceil(len/13); a possible short-only name one slot, or two when the next entry starts ≥ 2 slots later (the safe side); the last entry one | `getdents` returns no slot counts; positions come from `d_off` (`fs/readdir.c:155-158`, `fs/fat/dir.c:578`, `:625`) | none: the budget rule of 4.4 step 6 is unchanged |
| P-13 | Without `/proc/psc` the supervisor's nonce falls back to `gettimeofday` ^ pid | No stats to read | none |
| P-14 | The first drain's `m` counts Δt from worker start | Allows the start-up backlog to drain at `m` up to 4 | none |
| P-15 | (attempt 2) The run-number scan moved from `main.c` into `pscol.c` (`pscol_run_scan`, `:2178`), with the name parser `pscol_tname` (`:2153`) shared with `names_scan` | One parser for both scans, and the host harness can test the supervisor's scan (F2) | none |
| P-16 | (attempt 2) A FAILED flush queues, per ring, `[first carried seq, np)` instead of `[pos0, np)`, with `pre` = the holes already counted in `lost`; a re-send counts only missing seqs beyond `pre`; a re-sent range that fails again is queued with all its missing seqs counted; an overflow merge adds the two `pre` but not the gap (a gap seq found missing is counted: over, never under) | F6: `lost` counted once. 4.6 "one seq range per ring" is kept; `durable_next` can now start after a lost prefix, which is never durable anyway | none |
| P-17 | (attempt 2) KRN (8.2) compares stats word 2 with the CRC-32 of `/proc/version` read once at worker start (`build_id_read`, `:453`); the cbuild knob `PSC_BUILD_ID` was removed | Section 17 R-4 | none (the ruling's text) |

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
| D-16 | (attempt 1: `regmap.txt` syntax `<label> <var> <location>`, which did not match the kernel's file, OD-4.) **Replaced at attempt 2:** grammar 2 of `psc_maps.py` (`<steps> <var> <slot> <offset> <epc>`), written by `mkmaps.py` and read by `BuildInfo.load`; a file without the grammar's first line is an error that refuses the EPC analysis | G2 attempt 1 F3 | — |
| D-17 | `build_id` from `--build-id` or `BUILD/build_id.txt` (the packaged build's); EPC analysis refused without it | **Ruled by G1** (R-4) | — |
| D-18 | EVENT line grammar (optional tick stamp, then the 10.2 words) | Not specified. pscol's strings match (`segment ready`, `stop`, `abandon`, `flush fail`, `region bad`, `meta err`, `inode reused`, `speed`, `names budget`, `conlevel`, `switch`, `takeover`, `guard`) |
| D-19 | FATM = `[fat_start + fat_length, fat_start + fats × fat_length)` | The literal text would class FSINFO as FATM |
| D-20 | `--no-template` test hook | Needed by the 8.5 N-4 row |
| D-21 | All thresholds fixed as constants and printed | 10.7, G3 R6 |
| D-22 | The decoder does not re-judge flush/step verdicts; it repeats META only | Section 10 does not ask for it |
| D-23 | (attempt 2) The 10.1 word-2 check uses the **first** stats block (the one KRN verified); a later block whose word 2 differs is listed and makes onsets from its tick `instrumentation-suspect`; each FILEHDR's `/proc/version` CRC-32 is checked against stats word 2 (R-4) and a mismatch is listed | 10.1 does not say which block; G1 ruling red team K4 / KR2 recommends this, so a stray store late in the run does not refuse the EPC analysis of an earlier onset | — |
| D-24 | (attempt 2) P6 cross-check: the regmap's `pending` (status loaded, data not yet read, an EPC sub-range) decides 10.7's "anything if between its status test and its data read"; with `pending` = 1 and `j + 1` in the record's set the line names "P6, empty-FIFO pop" (K2); with `pending` = 0 a result outside the 10.7 list is `INCONSISTENT`, except the thread's own valid reply when all `j` words were read (`j` = n, outside recon 5.1's 1 ≤ j < n) | Attempt 1 could not decide the window and always printed "allowed only if ..."; the cross-check is an annotation and changes no classification | — |
| D-25 | (attempt 2) REPORT.md prints the BUILD directory's `IMAGE.sha256` (to compare with the G3 R3 record) and a `nwords` 7-or-8 section (flagged records per command and origin; "ambiguity live" per template command) | Section 17 R-1 (10.3: "REPORT.md counts the flagged records per command and origin") and K3 (print, not enforce) | — |

### 6.4 Integration

| # | Deviation | Reason | Touches |
|---|---|---|---|
| I-1 | The initramfs was not repacked with the `cpio` tool from the unpacked tree. A small newc writer (`work/initramfs-work/mkcpio.py`) copied every original entry byte for byte and changed or added only `etc/rc.sysinit` and `usr/bin/pscol`. The tree was still unpacked as root and checked against `extract/root2`, and the result against the patched tree | `cpio -o` from an unpacked tree would renumber inodes, rewrite directory mtimes and depend on host `find` order. The byte-preserving rewrite keeps all 95 untouched entries identical, which `cpio -itv` and the parser both confirm | none |
| I-2 | `work/package.sh` now also requires and copies `kmodlib.prx` verbatim from `PSPBOOT_DIR`. The diff is two lines plus a comment; the previous version is kept at `work/initramfs-work/package.sh.before-integrator` | DESIGN 9 and RUNBOOK "What you need" list `kmodlib.prx` as one of the four files of the folder. Recon wrote `package.sh` before the baseline folder was recovered (dossier 9.7), so it copied only `EBOOT.PBP` and `pspboot.conf`. `pspboot.conf` is still copied verbatim | none |
| I-3 | Release-build copies of `syscon-window-diff.txt`, `epcmap.txt` and `regmap.txt` were written to `impl/release-20261006T021722Z/`. The implementer's files in `impl/` were left as delivered | The decoder needs maps "from the exact build" (10). Their content is identical apart from the header lines | none |
| I-4 | `pscol` is mode 0755, while the other two daemons in the archive are 0744 | The task and pscol's notes ask for 0755; the owner is root:root like every entry | none |
| I-5 | (attempt 2) `work/package.sh` takes an optional `BUILD_DIR`: verifies its `SHA256SUMS`, requires its `IMAGE.sha256` to name the packaged kernel, and copies it to `<stage>/BUILD/` beside `PSP/` (never into the stick folder); the previous version is kept at `work/initramfs-work/package.sh.before-g2a2` | Section 17: "the package carries `BUILD/build_id.txt` from the packaged build's `banner.txt`" | none |
| I-6 | (attempt 2) The initramfs was updated by `work/initramfs-work/replace_pscol.py`: only the data, size and mtime of `usr/bin/pscol` change; the other 96 entries are byte-identical | The same byte-preserving method as I-1 | none |
| I-7 | (attempt 2) `handoff/impl/mkmaps.py` writes a whole BUILD directory (maps in grammar 2, `System.map`, `vmlinux`, `banner.txt`, `build_id.txt`, `IMAGE.sha256`, `panellayout.txt`, `SHA256SUMS`) and refuses to write unless every anchor instruction, the registers of the `all` rows and the banner check out | G1 ruling advisory A-4 (one BUILD directory for the packaged image); F3 | none |

---

## 7. Paths

| What | Path |
|---|---|
| Kernel branch | `/home/ubuntu/psp/work/linux`, `stage2-trace` @ `48dcc1b9` |
| Build log | `/home/ubuntu/psp/work/logs/build-20261006T052947Z.log` |
| Build out | `/home/ubuntu/psp/work/out/20261006T052947Z/` |
| Deploy folder | `/home/ubuntu/psp/work/deploy/uClinux_TRACE/PSP/GAME/uClinux_TRACE/` (+ `../../../SHA256SUMS`, `PROVENANCE.txt`, `BUILD/`) |
| Release directory (this build) | `/home/ubuntu/psp/handoff/impl/release-20261006T052947Z/`: `BUILD/` (decoder inputs), `syscon-window-diff.txt` (D10), `syscon-cmd-body.diff` and `syscon-vs-baseline.diff` (timeout patch, 9.3), `pathcount.txt` (9.2), `pscol-krn-packaged-banner.txt` |
| Collector | `/home/ubuntu/psp/work/pscol/` (`CHECKS.txt`) |
| Decoder | `/home/ubuntu/psp/work/decoder/` (`TESTS.txt`) |
| Map writer, path counter | `/home/ubuntu/psp/handoff/impl/mkmaps.py`, `/home/ubuntu/psp/handoff/impl/pathcount.py` |
| Integration tools | `/home/ubuntu/psp/work/initramfs-work/` (`replace_pscol.py`, `extract_ramfs.py`, `newc.py`) |
| Attempt-1 release (superseded) | `/home/ubuntu/psp/handoff/impl/release-20261006T021722Z/`, `work/out/20261006T021722Z/` |
| Panel layout | `/home/ubuntu/psp/handoff/impl/panellayout.txt` (also in `BUILD/`) |

---

## 8. Response to G2 attempt 1

One line per finding of `gates/G2-attempt1-review.md` (sections 1, 3.2, 8, 9)
and `gates/G2-attempt1-verify.md` (Findings 1-5). FIXED = changed, with
where; RULED = settled by G1 (DESIGN 17) and implemented as ruled; NOTED =
no code change needed, evidence given. Nothing is CONTESTED.

| Finding | Status | Where (commit / file:line) and evidence |
|---|---|---|
| Review F1 (DV-3 / OD-1, D3: `nwords` 7 for 8 words ending 0xFFFF; routed to G1) | RULED (R-1 option (a)), implemented | Kernel unchanged (`arch/mips/psp/psc.c:275-280`). Decoder: flag `work/decoder/pscdec_parse.py:162-168`; set `pscdec_analysis.py:20` (`nwset`), template `:234-251`, `:296`, P6 cross-check `:1440-1464`; REPORT section `pscdec.py:560`, template "ambiguity live" `:541`; CSV keeps `nwords` and `nw7or8`. Tests `test/run_tests.py:640` (NwordsSevenOrEight). The compiled code's table, executed: `impl/release-20261006T052947Z/pathcount.txt` (9.2.5) |
| Review F2 (C1: run number / `nnn` scans never match; names budget overcounts) | FIXED | `work/pscol/pscol.c:2153` (`pscol_tname`: 11 characters, dot at 7, any case), `:2178` (`pscol_run_scan`, used by `main.c:93`), `:2205`/`:2242` (`sfn_lower`, `names_scan`: one slot per 8.3 entry, positions from `d_off`), `pscol.h:69` (`OS_DIRENT_OFF`); host harness `test/sim.c:936` (vfat readdir with shortname=lower display and `d_off`), `:285` (entries of earlier boots), tests `:1506` (`test_names`): lower-case names of an earlier boot → `rrr` 2, `nnn` restarts at 001, a takeover continues `nnn`, 1 slot per file. In the image: `48dcc1b9` |
| Review F3 (C1: decoder cannot read the kernel's maps, OD-4) | FIXED | One grammar with an offset column and EPC sub-ranges: `work/decoder/psc_maps.py` (reader and formatter), written by `handoff/impl/mkmaps.py` and read by `pscdec_analysis.py:120-174` (`BuildInfo.load`, `regval`); S0 → P0 `:179`; k and j with offsets, `pending`, ptr cross-check `:570-618`; LEDSPLIT `loaded` `:1377`. Release maps: `impl/release-20261006T052947Z/BUILD/`. Test on the release maps with W records at S11, S18 and LEDRMW: `test/run_tests.py:538` (ReleaseMaps, 7 tests) |
| Review F4 (KRN never compares `build_id`, OD-3) | FIXED (as ruled, R-4) | `work/pscol/pscol.c:453` (`build_id_read`: CRC-32 of `/proc/version` at worker start, `:2833`), `:442` (KRN needs word 2 equal); `cbuild.sh` knob removed. Decoder: `BUILD/build_id.txt` via `--build` (`pscdec.py:234-243`), first-block check and FILEHDR `/proc/version` CRC (`pscdec_analysis.py:403-452`). Package carries `BUILD/build_id.txt` = `0x045b27d9` (1.5). Tests: pscol `krn` (5.2), decoder `BuildCheck` (`test/run_tests.py:684`) |
| Review F5 (costs and stack not restated from object code) | FIXED | 9.2: per-path counts (P entry +75, P exit +482/+485, the Nop +871, watchdog tick +922, straddle +1,104, tick +48) and stack depth (thread +208 B; Nop path 344 B below the exception frame, +216; worst before `irq_enter` 488 + 176 = 664 B on the T2d tick), measured by executing the compiled code: `handoff/impl/pathcount.py`, output `impl/release-20261006T052947Z/pathcount.txt`. Figures above some 5.4/7.1 estimates are listed as OD-7 |
| Review F6 (lost recounted on re-send, `pscol.c:932` with `:1908`) | FIXED | `work/pscol/pscol.c:68-72` (`struct rqe` `pre`), `:837-886` (`rq_add` with `pre`), `:972-979` (re-send counts only missing seqs beyond `pre`), `:993` (re-queued re-send range: all counted), `:1035-1041` (new block queued from its first carried seq, holes in `newpre`), `:1956-1960` (FAILED re-queue). Host vector `test/sim.c:1649` (`test_resend_lost`): lost = missing (915/1,020/1,020); the attempt-1 accounting gives 1,674/1,779/1,869 |
| Review F7 (commit provenance, "Recon C") | FIXED | 2.1: the 14 kernel commits' actual author is the Stage 2 kernel implementer; `work/linux/.git/config` `user.name` set to `Stage 2 kernel implementer (Claude agent)` (and `user.email` `stage2-kernel-implementer@localhost`) before `48dcc1b9`; history not rewritten |
| Review 3.2 U1 (= F2) | FIXED | as F2 |
| Review 3.2 U2 (= F5) | FIXED | as F5 |
| Review 3.2 U3 (= F6) | FIXED | as F6 |
| Review 3.2 U4 (= F4) | FIXED | as F4 |
| Review C1 FAIL (blocking) | FIXED / RULED | its three reasons: F1 (RULED), F2 and F3 (FIXED) |
| Review C2, DV-17 (timeout patch text) | NOTED | 9.3: the transaction body's diff against the baseline (`impl/release-20261006T052947Z/syscon-cmd-body.diff`) and every timeout-patch element mapped to its place; defines `syscon.c:12-13` byte-identical; behaviour unchanged; the code is the attempt-1 code |
| Review C6 (clean build, image size) | NOTED | 1.2 (rc 0, warnings identical to the baseline), 1.4 (growths restated per R-5) |
| Review C7 (symbols) | NOTED | kernel code identical to attempt 1 apart from the banner and `__initramfs_end` (1.2); `System.map` differs only in `__initramfs_end` |
| Review C8 (userland) | NOTED | 5.2 (0 FP, bFLT valid, 183,040 B ≤ 256 KB) |
| Review C9, C10 | NOTED | formats unchanged (`check_format.py` exit 0); one new commit with one concern, built from clean |
| Review section 7 (A7-1..A7-3) | NOTED | confirmed closed by the reviewer; no change |
| Review section 9, attacks 11-13 | FIXED / RULED | 11 → F2, 12 → F3, 13 → F1 |
| Verify Finding 1 (D10 window not literally identical, OD-2; BLOCKING under the verifier's rule) | RULED (R-2) | The 2.1 criteria are the test; window re-proved on the attempt-2 image, identical to attempt 1 (`impl/release-20261006T052947Z/syscon-window-diff.txt`, 5.1) |
| Verify Finding 2 (pscol memory over the 128 KB figure, OD-5) | RULED (R-5) | 183,040 B, one 256 KB block per process, both at boot (1.4) |
| Verify Finding 3 (image growth near the bound; pspboot load UNVERIFIED, OD-6) | RULED (R-5); restated | `vmlinux.bin` +44,036 B (margin 5,116), `vmlinux-0.22.bin` +37,312 B (margin 11,840); +405 / +393 since attempt 1 (1.4). Load UNVERIFIED (OD-9) |
| Verify Finding 4 (release sha256 is per build) | NOTED | The packaged attempt-2 image is `4f9b69dc…` with `build_id` `0x045b27d9`; its BUILD directory (with `IMAGE.sha256`) is in the package and in the release directory (1.5). A verifier's rebuild of `48dcc1b9` will differ in the banner only and its maps must not be used (10.1, R-4) |
| Verify Finding 5 (timeout patch no longer reverse-applies, DV-17) | NOTED | as Review C2 (9.3) |

---

## 9. G2 attempt 2: what changed, and the measurements

### 9.1 The G1 ruling (DESIGN 17), item by item

| Item | Required by 17 | Implemented |
|---|---|---|
| R-1 | Decoder flags `nw7or8` and applies set membership in the rules of 10.7 | `pscdec_parse.py:162-168` (flag on SC, W and M records: `nwords` 7 with `rx[14..15]` = `ff ff`); `pscdec_analysis.py:20` `nwset`; template value 7 learned from flagged records is {7, 8} (`:296`), the fallback expectation "exact length from `rx[1]`" is a set (`:234-240`), `own_valid` matches by intersection (`:251`); the P6 cross-check reads the set (`:1440-1464`); E3/E4, H1-H3, N10, REC and POLL:NW0 thresholds (0, ≥ 1) are unaffected and read the raw value; REPORT counts flagged records per command and origin and prints "ambiguity live" per template command (`pscdec.py:541`, `:560`); CSVs keep `nwords` and `nw7or8`. Kernel unchanged |
| R-2 | (no implementation item) | Window re-proved (5.1) |
| R-3 | IMPLEMENTATION restates the 5.4 counts if `psc.c` or `syscon.c` change | They did not change; the counts are restated anyway from executed object code (9.2), as G2 F5 asked |
| R-4 | pscol KRN: CRC-32 of `/proc/version` at worker start against word 2; package carries `BUILD/build_id.txt`; decoder uses it and checks each FILEHDR's `/proc/version` | pscol `pscol.c:453`, `:442`, `:2833`; package `deploy/uClinux_TRACE/BUILD/build_id.txt`; decoder `pscdec.py:234-243`, `pscdec_analysis.py:403-452` |
| R-5 | Restate both image growths and the change since attempt 1 | 1.4 |
| R-6 | (text only) | — |

**G1 ruling advisories and red-team recommendations** (non-blocking; listed so
none is lost):

| Item | Status |
|---|---|
| Review A-1 (component counts) | Done: 9.2 gives per-path counts with the path assumptions stated |
| Review A-2 (stack figure, citation) | Measured: +216 B on the Nop path (the 5.3 text says ≈ 280 B, conservative); the citation fix is design text |
| Review A-3, A-5, A-6 (wording) | Design text; nothing to implement. A-5's optional decoder print: REPORT counts flagged records and prints "ambiguity live" per template command; per classification window it does not |
| Review A-4 (one BUILD directory for the packaged image) | Done: `mkmaps.py` writes it; it is in the package (1.5) |
| Red team K1 (wording) | Design text. Consistent with the code: a recorded 7 is always flagged (the compiled-code table, 9.2.5) |
| Red team K2 (EPC sub-label in S18, automatic "P6, empty-FIFO pop", Stage 3 vector) | Done without a new EPC label: the regmap's `pending` row (an EPC sub-range of S18) and the cross-check line (D-24); vector `test_eighth_word_every_epc` |
| Red team K3 (default identity; image hash) | Built with the default identity (1.2); `BUILD/IMAGE.sha256` written, checked by `package.sh` and printed by the decoder. The decoder does not refuse on it (that needs 10.1 text) |
| Red team K4 (first stats block; later change → instrumentation-suspect) | Done (D-23) |
| Red team K5, K6, K8 (more decoder printouts in 10.7 steps 6 and 8) | Not implemented: 10.7 was not amended; OD-8 |
| Red team K7 (figures) | Design text; this file uses text 52,768 B incl. the header (1.4) |
| Red team K9 (vectors; re-derive the exit table on rebuilds) | Done: `nw7or8` vectors, KRN with the packaged banner, decoder build check; the exit-to-`nwords` table re-derived by executing the compiled code (9.2.5) |

### 9.2 Measured cost and stack depth of each path (G2 F5; R-3)

**Method.** `handoff/impl/pathcount.py BASE_OUT NEW_OUT` runs the kernels' own
machine code: objdump of each `vmlinux` (the tree's objdump in the
container), `vmlinux.bin` loaded at 0x88000000 with a zero BSS, a MIPS32
integer interpreter with delay slots and likely branches, and a model of the
syscon SPI/GPIO registers (RX FIFO empty at entry, ACK after 20 polls, the
reply words). It counts every executed instruction (delay slots included)
and the lowest `sp`. Baseline = `work/out/20260927T204657Z` (the unmodified
tree), new = the release build. CP0 Count advances one per instruction;
µs below assume 1 instruction per cycle at 220.9 MHz (DESIGN 5.4,
UNVERIFIED; caches not modelled). Output:
`impl/release-20261006T052947Z/pathcount.txt`. Cross-checks of the model: the
S5..S20 count is equal in both builds on every path (D10), the Syscon_cmd
difference is the hand-off (+64), and the records it writes decode correctly
(1.3); the per-function counts agree with the G1 reviewer's hand count
(`psc_xfer_out` 32, `psc_fill_sc` ≈ 118 → 111, hand-off 62).

**9.2.1 Thread command (P path), entry to return of the caller.** "Before S5"
= from the caller's entry to the first syscon MMIO access; "after S20" = from
the last one to the caller's return (warm, second run).

| Path | Before S5 base → new (added) | S5..S20 | After S20 base → new (added) | Total added | ≈ µs | Stack below the caller's sp |
|---|---|---|---|---|---|---|
| P08 `_pspSysconGetCtrl2` (0x08, 5-word reply) | 160 → 235 (**+75**) | 357 = 357 (0) | 94 → 576 (**+482**) | **+557** | 2.52 | 112 → 320 B (+208) |
| P33 `pspSyscon_tx_dword(1, 0x33, 3)` (2-word reply) | 166 → 241 (**+75**) | 312 = 312 (0) | 46 → 531 (**+485**) | **+560** | 2.54 | 104 → 312 B (+208) |

P entry (+75): the wrapper `psc_syscon_cmd` up to its call (A1 inline) and
`Syscon_cmd`'s per-attempt A2 store and larger prologue. P exit (+482/+485):
the hand-off asm (62) and `psc_xfer_out` (32), the wrapper's tail and
`psc_sc_exit` (167-170), `psc_fill_sc` (111), `__bzero`/`memset` (≈ 44),
`memcpy` (≈ 29), `psc_dcount` (30). The first call of a boot costs one more.
**G3-low gap** (0x33's S20 to 0x08's S5): +485 + 75 = +560 instructions ≈ 2.5
µs, plus the thread's stage stores between the two calls (not executed here;
`psp_joypad_thread` grew 364 → 662 instructions). R-3's "≈ 60 before S5 and
≈ 400-550 after S20, ≈ 2.1-2.8 µs per command, G3-low gap +2.1-3 µs" holds.

**9.2.2 Timer interrupt, `plat_irq_dispatch` to its call of `irq_enter`**
(everything the instrumentation adds to a tick runs there). Stack is below
the pt_regs frame; add PT_SIZE 176 B (`include/asm-mips/ptrace.h:30-52`) for
the exception frame.

| Path | Base | New | Added | ≈ µs | Stack base → new |
|---|---|---|---|---|---|
| TICK, ordinary tick | 33 | 81 | **+48** (T1 + `psc_tick_hook`) | 0.22 | 24 → 72 B (+48) |
| WD, watchdog tick, thread idle (warm) | 564 | 1,486 | **+922** (+64 before the Nop's S5, 13 of them T1; +858 after its S20, 38 of them T2; the Nop alone +871: +51 before its S5, +820 after its S20) | 4.17 (Nop alone 3.94) | 128 → 344 B (+216) |
| WD, first Nop of a boot (`psc_syscon_end` computed once) | 564 | 1,554 | **+990** | 4.48 | 128 → 344 B |
| WDP, watchdog tick interrupting the thread at S14 of its 0x08 (T2a runs: 198 vs 38 in `psc_tick_hook`; the Nop receives the thread's reply, H4's foreign reply) | 639 | 1,743 | **+1,104** | 5.00 | 128 → 344 B (+216) |
| T2D, tick at 125 mod 250 with the stall panel painting (new only) | — | 228,520 | (paint: `psc_panel_fill` 139,575, `psc_panel_t2d` 81,916, `pspClearDcache` 1,289 with a 16 KB D-cache, UNVERIFIED; 184,320 B of VRAM written, 96 rows × 480 × 4) | ≈ 1,030 | 488 B |

So R-3's "watchdog path +2-4 µs" holds for the Nop alone in steady state (3.9
µs) and is exceeded for a whole watchdog tick (4.2 µs, 4.5 µs once per
boot) and for a watchdog tick that finds the thread mid-command (5.0 µs);
7.1's "≈ 16 instructions per tick, ≈ 33 more when the thread is in a
command" is +48 and +208 measured; a paint is ≈ 1.03 ms against 7.1's
"0.2-1 ms" (OD-7). All of this is outside S5..S20, takes no lock and masks
nothing new (the timer handler already runs with interrupts off).

**9.2.3 Worst-case interrupt stack depth.** Before `irq_enter` the deepest
new path is the T2d paint: 488 B below the pt_regs + 176 B = **664 B** below
the interrupted context's `sp` (baseline: the watchdog tick, 128 + 176 = 304
B). On a watchdog tick: 344 + 176 = **520 B** (+216 B, R-3's ≈ 280 B was
conservative). The two never coincide (T2d ≡ 125 mod 250, the Nop ≡ 0 mod
1250). The Nop's depth equals the static frame sum of its deepest chain
(`plat_irq_dispatch` 32 + `pspSyscon_tx_dword` 56 + `psc_syscon_cmd` 72 +
`Syscon_cmd` 56 + hand-off 128 = 344 B; the `psc_sc_exit` 104 + `psc_fill_sc`
64 branch is 16 B shallower). After `irq_enter` the code is the unchanged
generic kernel, except `psc_sched_wake_slow` (24 B frame) on wake-ups from
softirq timers. The interrupted context's own depth (for example a task deep
in vfat writeback) is not measured: UNVERIFIED, as in 5.3; 8 KB stacks
(`include/asm-mips/thread_info.h:66-67`, `:82`). Process-context frames, for
the record: `psc_stats_read` 808 B and `psc_ring_read` 360 B (`/proc` reads
by pscol, never in an interrupt).

**9.2.4 Thread side of a straddle.** In WDP the interrupted thread is at
880cf0a4 (S14, the ACK wait); the Nop it suffers runs the same code as WD
plus T2a. The thread resumes +1,104 instructions (≈ 5.0 µs) later than in
the baseline; the window itself is unchanged.

**9.2.5 The `nwords` table of the compiled code** (K9; section 17 R-1),
P records written by the release kernel's own code for each reply:

| Reply | `ret` | `nwords` | `nw7or8` | `retries` | `ack_polls` | `drain` |
|---|---|---|---|---|---|---|
| 0 words (FIFO empty after the ACK) | 0 | 0 | 0 | 0 | 20 | 0 |
| 1 .. 6 words | −2 | 1 .. 6 | 0 | 0 | 20 | 0 |
| 7 words | −2 | 7 | **1** | 0 | 20 | 0 |
| 8 words, the 8th 0x3333 | −2 | **8** | 0 | 0 | 20 | 0 |
| 8 words, the 8th 0xFFFF | −2 | **7** | **1** | 0 | 20 | 0 |
| `rx[2]` = 0x80 on every try | −5 | 2 (final attempt) | 0 | 16 | 20 | 0 |
| no ACK | −4 | 0 | 0 | 0 | 1,000,001 | 0 |
| RX FIFO never empties before the request | −3 | 0 | 0 | 0 | 0xFFFFFFFF | 0xFFFF |

(The frames are cut from one 10-byte frame, so the checksum fails, `ret` −2;
`ret` is not what this table tests.) This is exactly section 17 R-1: exact for
0..6 and for 8 not ending 0xFFFF; every recorded 7 is flagged; 8 ending
0xFFFF reads 7, flagged; 0 on −3 and −4; the 1.2 sentinels for −3 and −4.

### 9.3 The syscon timeout patch (DV-17; G2 C2; verifier Finding 5)

The callers now call the recording wrapper `psc_syscon_cmd`
(`arch/mips/psp/psc.c:526-533`; `syscon.c:330`, `:344`, `:419`), which calls
the unchanged-in-behaviour `Syscon_cmd`. The patch's text no longer
reverse-applies because new lines sit in its hunks' context. Each element of
`work/syscon-timeout.applied.patch`, as it stands at `48dcc1b9`:

| Patch element | Now |
|---|---|
| `#define SYSCON_SPIN_MAX 1000000`, `#define SYSCON_RETRY_MAX 16` | `syscon.c:12-13`, byte-identical |
| `vu32 spin; int retry_cnt = 0;` | `syscon.c:117-118`, unchanged |
| drain: `spin = SYSCON_SPIN_MAX;` and `if(spin-- == 0) return -3;` | `syscon.c:162`, `:165`: the same bound; `return -3` → `{ result = -3; goto out; }`, which returns −3 after the hand-off (DESIGN 2.1 A4) |
| ACK: `spin = SYSCON_SPIN_MAX;` and `if(spin-- == 0){ REG32(0xbe580004)=4; REG32(0xbe24000c)=0x08; return -4; }` | `syscon.c:203`, `:206`: the same bound in `spin_ack` (2.1 A3), the same two teardown writes in the same order, `return -4` → `result = -4; goto out;` |
| `if(++retry_cnt < SYSCON_RETRY_MAX) goto retry; result = -5; break;` | `syscon.c:305-306`, unchanged |

Diff of the transaction body (`Syscon_cmd`, baseline `syscon.c:61` against
`stage2-trace` `syscon.c:107`; also
`impl/release-20261006T052947Z/syscon-cmd-body.diff`; the whole file's diff is
`syscon-vs-baseline.diff` there):

```
@@ -12,2 +12,7 @@
 	int retry_cnt = 0;
+	/* PSC (DESIGN 2.1 A3): further capture slots. dmy keeps the S5 load
+	 * (gpio_in) and spin the drain counter; declared after the original
+	 * locals so the code generated for S5..S20 does not change (7.2). */
+	volatile u16 dlast, st9, sttx;
+	vu32 spin_ack;
 
@@ -15,2 +20,3 @@
 retry:
+	spin = 0;	/* PSC 2.1 A2: "drain loop not entered" (memory only, before S5) */
 	// calc & set TX sum
@@ -52,4 +58,4 @@
 		{
-			if(spin-- == 0) return -3;
-			dmy = REG32(0xbe580008);
+			if(spin-- == 0) { result = -3; goto out; }	/* PSC A4 */
+			dlast = REG32(0xbe580008);	/* PSC A3: was dmy */
 //Kprintf("%04X:",dmy);
@@ -58,3 +64,3 @@
 	}
-	dmy = REG32(0xbe58000c);
+	st9 = REG32(0xbe58000c);	/* PSC A3: was dmy */
 ;
@@ -69,3 +75,3 @@
 	{
-		dmy = REG32(0xbe58000c);
+		sttx = REG32(0xbe58000c);	/* PSC A3: was dmy */
 //Kprintf("%04X ",(ptr[0]<<8)|ptr[1] );
@@ -90,6 +96,6 @@
 // 		r2 = sceGpioQueryIntr(4)
-	spin = SYSCON_SPIN_MAX;
+	spin_ack = SYSCON_SPIN_MAX;	/* PSC A3: was spin */
 	while( (REG32(0xbe240020) & 0x10)==0)
 	{
-		if(spin-- == 0){ REG32(0xbe580004)=4; REG32(0xbe24000c)=0x08; return -4; }
+		if(spin_ack-- == 0){ REG32(0xbe580004)=4; REG32(0xbe24000c)=0x08; result = -4; goto out; }	/* PSC A3, A4 */
 //Kprintf("%02X ",REG32(0xbe240004)&0x18);
@@ -196,2 +202,4 @@
 
+out:	/* PSC 2.1 A4: hand the captures to the recorder, then return as before */
+	PSC_XFER_OUT(dmy, spin, spin_ack, dlast, st9, sttx);
 	return result;
```

Behaviour: the same MMIO accesses in the same order (5.1), the same bounds
and return values; executed, the −3 and −4 exits return −3 and −4 after
1,000,001 iterations with nothing else changed (9.2.5), and the −5 path after
16 tries. The `dmy`/`spin` reads that became captures are the same volatile
loads to stack slots (2.1 A3).

### 9.4 Authorship

See 2.1: commits `4c4e7aee`..`0b0a2acf` were written by the Stage 2 kernel
implementer although git says "Recon C"; `48dcc1b9` carries the corrected
identity `Stage 2 kernel implementer (Claude agent)`. The attempt-2 changes to
pscol, the decoder, `mkmaps.py`, `pathcount.py`, `package.sh` and the
initramfs tool, and this revision of IMPLEMENTATION.md, are by the
G2-attempt-2 implementer.
