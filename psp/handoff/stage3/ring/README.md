# Stage 3 ring-logic test (handoff/stage3/ring)

WORKFLOW.md Stage 3, row "Ring logic": compile the ring and record code on the
host with a stub for register access, drive it with synthetic sequences for H1
to H8 including an interrupt arriving mid-record, check the records against
DESIGN, and write dumps for the decoder test. The results were returned to
the orchestrator with the Stage 3 ring-logic result; the evidence is in
`../logs/ring-*.log` (listed below).

## What is compiled

The kernel files under test are compiled **unmodified** from
`/home/ubuntu/psp/work/linux` (`make` refuses to build unless each one is
byte-identical to `git show 48dcc1b9:<file>`, the `stage2-trace` commit of the
released image; hashes in `build/kernel-sources.sha256` and
`../logs/ring-kernel-sources.sha256`):

| File | How |
|---|---|
| `arch/mips/psp/psc.c` (rings, records, reader, stats, ctl, tick hook, scheduler hooks) | C, gnu89, as is |
| `arch/mips/psp/psc_panel.c` | C, as is (the T2d panel; the VRAM is an `mmap` at 0x84000000) |
| `arch/mips/psp/ipl_sdk/syscon.c` (`Syscon_cmd`, the instrumented transaction) | `#include`d by `src/syscon_host.cc` as C++ so that `REG32` (syscon.c:15) reaches the register model through a proxy type; the MIPS hand-off asm `PSC_XFER_OUT` (syscon.c:31, used at :310) becomes a call with the same six capture slots and `retry_cnt` |
| `drivers/input/joypad_psp.c` (the polling thread, `psposk2` queues, mouse) | `#include`d by `src/joypad_host.c` |
| `include/linux/psc_format.h`, `include/asm-mips/psc.h`, `psp.h`, `ipl_sdk/{syscon,kprintf,sysreg,cache}.h` | real headers via `src/realinc/` symlinks |

Everything else is host code written for this test:

| File | Role |
|---|---|
| `src/stubinc/host_kernel.h`, `src/stubinc/linux/*.h`, `src/stubinc/asm/*.h` | kernel interfaces the files use (task_struct fields, jiffies, printk, proc, cdev, semaphores, uaccess, `barrier()` = an injection point) |
| `src/stubinc/psptypes.h` | `vu32` as a register proxy (C++ only) |
| `src/mmio.c` | SPI/GPIO register model and the syscon behind it (all UNVERIFIED, see the header comment); an observer that labels every access of `Syscon_cmd` with its step S5..S20 and the release EPC (`BUILD/vmlinux`) |
| `src/sim.c` | Count/tick time base, the timer interrupt of `psp.c:353-394` (Count reset, `psp_local_tick`, the watchdog Nop every 1250 ticks with `wd_ctx` = timer, the real `psc_tick_hook`), tasks and context switches through the real `psc_sched_*` hooks, kernel memory arena |
| `src/collector.c` | a minimal collector (not `pscol`) that reads the real `/proc/psc/*` file operations and writes 2 MB `PSCLOG` segment files in the DESIGN 10.2 chunk format |
| `src/scen.c` | the operator script (RUNBOOK B4..D9 timing), the input model, the scenarios and their aimed interrupts |
| `src/tests.c` | unit tests (`build/ringtest`) |
| `src/place.ld` | puts `Syscon_cmd`, `pspSyscon_tx_noparam`, `_pspSysconGetCtrl2`, `psc_sc_exit` at their release addresses so that `psc.c`'s own pointer casts give the release values |
| `oracle/design_format.py`, `oracle/oracle.py` | the DESIGN 1.2-1.5 tables typed from DESIGN (and machine-checked against DESIGN.md), and an independent model that recomputes every record and the stats words from the event log, compared byte for byte |
| `tools/mkbanner.py`, `tools/signature.py`, `tools/decode_all.sh` | banner = `BUILD/banner.txt` (build_id 0x045b27d9); per-dump "observed" summary into `truth.json`; informational decoder run |

## Host, word size, endianness

* Host: aarch64 Ubuntu 24.04, gcc/g++ 13.3.0, Python 3.12, GNU binutils 2.42.
* **Word size: LP64 (-m64; the aarch64 compiler has no -m32).** The record
  formats do not depend on it: `psc_format.h` declares them packed with fixed
  widths and static size asserts (`psc_format.h:877-880` and others), and
  `psc.c` uses explicit `u32`/`unsigned long long` for counters and positions
  (`psc.c:62-66`, `:982`, `:1038`). Kernel pointers that `psc.c` stores as
  `u32` are made exact by placement (`src/place.ld`, all below 4 GB) and by a
  kernel-memory arena at 0x89c00000 (`src/sim.c`). An ILP32 build was not
  made (UNVERIFIED).
* **Endianness: little-endian on both sides** (host aarch64 LE, target
  mipsel). `psc_format.h:35-37` stops the build on a big-endian target; every
  DESIGN format string is `<`. No byte swapping is done anywhere.

## How to run

From this directory (no root, no network; `make` needs gcc, g++, python3,
git and addr2line):

```
make              # check the kernel sources are 48dcc1b9's, build build/ringsim and build/ringtest
make test         # unit tests            -> ../logs/ring-unit-tests.log   (fails unless RESULT PASS)
make dumps        # 21 scenarios          -> ../dumps/<name>/, ../logs/ring-dumps.log,
                  #                          ../logs/ring-signatures.log, ../logs/ring-dumps.sha256
make oracle       # byte-for-byte check   -> ../logs/ring-oracle.log       (fails unless 0 scenarios failing)
make all-checks   # test + dumps + oracle + original-tree manifest, frozen-image hash, kernel tree status
                  #                       -> ../logs/ring-manifest.log
make crosscheck   # informational: run work/decoder over every dump -> ../logs/ring-decoder-crosscheck.log
make clean
```

One scenario by hand: `build/ringsim <name> <outdir> <eventlog>`; the event
log is what the oracle reads. Runs are deterministic: `make clean && make
dumps` reproduces `../logs/ring-dumps.sha256` exactly.

## Dumps (for the decoder test)

`/home/ubuntu/psp/handoff/stage3/dumps/<name>/`:

* `PSCLOG/T001001.BIN`: one 2 MB segment file as the collector leaves it on
  the stick (FILEHDR, then RECS/STATS/UHB/PROCS/KMSG/EVENT chunks, PAD).
* `times.txt`: the operator's stopwatch times (RUNBOOK form, `uptime_offset=10`).
* `truth.json`: the generator's ground truth: `expected` (what the decoder
  should name, in DESIGN section 6 terms), `onset_tick`/`onset_uptime_s`,
  `nonce`, the aimed interrupts (`aims`), record and loss totals, and
  `observed` (what the dump itself shows around the onset; `tools/signature.py`).

Decode with the packaged BUILD:
`python3 /home/ubuntu/psp/work/decoder/pscdec.py -o OUT --build /home/ubuntu/psp/work/deploy/uClinux_TRACE/BUILD --times <dump>/times.txt <dump>/PSCLOG/`

| Name | What happens (onset at uptime 131.3 s unless stated) |
|---|---|
| H1 | ACK never comes for P commands (W Nops still answered): −4 every command, the 9.5 variant |
| H2 | 0x08 replies all zero (`ret 0`, 5 words of 00) |
| H3 | 0x08 replies empty (`ret 0`, `nwords 0`) |
| H4 | a Nop aimed at S14 of a P08 at tick 32500 (P4), then the device lags one reply (N2b) |
| H5 | BUSY (0x80) on every 0x08 (−5 after 16 attempts) |
| H6 | 0x08 replies valid but frozen |
| H7 | replies follow the presses; `psposk2` and `pspmd` stop reading |
| H8 | ACK latch stuck set, `gpio_in` 0x0002 → 0x0006 |
| unclassified | valid checksum with an unknown code 0x42, frozen buttons |
| mid-irq-P0 .. P7, P6pop | healthy run with one watchdog Nop aimed into the P08 at tick 25000 at step S3/S5, S7, S11 (2nd push), S13, S14, S14 with latch set, S15, S18 status test, S18 data read, S20 |
| mid-irq-append | healthy run, Nops aimed at every ordering point of the P, POLL and S appends and at the W reader copy |
| mid-irq-entry | healthy run, Nops aimed at the two ordering points of the P entry (`psc.c:240`, `:245`) |
