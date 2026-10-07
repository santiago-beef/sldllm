# PSP uClinux input-death: handoff dossier

Prepared 2026-09-27 for a team of Opus 5.5 agents picking this up cold.
Companion document: [WORKFLOW.md](WORKFLOW.md) (roles, stages, review gates).

Every statement here carries one of three labels. Do not promote a label.

| Label | Meaning |
|---|---|
| **[HW]** | Observed on the real PSP by the human operator. Agents cannot re-check it. |
| **[SRC]** | Verified by reading the source in this tree on 2026-09-27. File and line given. Re-check before relying on it. |
| **[HYP]** | Hypothesis. Untested. |

---

## 1. Mission

Produce an **instrumented kernel** which, from **one** hardware run, tells us
why input dies, whatever the cause turns out to be and whenever in the run
it happens.

You are not asked to fix the bug. A fix attempted before diagnosis is out of
scope unless the human operator authorizes it (see open question Q5).

### Success criteria

The instrumented kernel and its runbook are successful if, after a single
run ending in a battery pull, the recovered data lets an analyst:

1. **S1** State which hypothesis in section 5 occurred, or state that none
   did and show the raw evidence for what did occur.
2. **S2** See the raw syscon traffic for a window before, across and after
   the moment input died, not only a sample at one instant.
3. **S3** Do this whether death came at 17 s or at 250 s or later, up to at
   least 15 minutes of run time.
4. **S4** Do this with the data that survives a battery pull.
5. **S5** Trust that the instrumentation did not itself cause, prevent or
   mask the failure, or know precisely how it might have.

---

## 2. System

| Item | Value | Label |
|---|---|---|
| Device | PSP-1001 | [HW] |
| OS | uClinux on PSP 0.22 (2008 port), kernel 2.6.22-uc1, mipsel, no MMU, bFLT userland | [HW] |
| Tick rate | `CONFIG_HZ=250` (4 ms jiffy) | [SRC] `.config:132` |
| Preemption | `CONFIG_PREEMPT=y` | [SRC] `.config:135` |
| Kernel log | `CONFIG_LOG_BUF_SHIFT=14` (16 KB), `CONFIG_PRINTK_TIME` off | [SRC] `.config:159,651` |
| Symbols | `CONFIG_KALLSYMS` off | [SRC] `.config:170` |
| Filesystems | `CONFIG_PROC_FS=y`, no sysfs, no debugfs | [SRC] `.config:568,570` |
| Input | `CONFIG_INPUT_MOUSEDEV=y`, `CONFIG_INPUT_EVDEV` off | [SRC] `.config:314,320` |
| Console | UART3 console compiled in, no adapter available | [SRC] `.config:359` / [HW] |
| USB | Compiled out | [HW] per `telem/telem.c:6` |

Paths below are relative to `/home/ubuntu/psp/build/linux` unless they
start with `/`.

### Input data path [SRC]

```
syscon chip  <--SPI + GPIO3/GPIO4-->  Syscon_cmd()           arch/mips/psp/ipl_sdk/syscon.c:61
                                        ^
                                        |  _pspSysconCtrlAStickPower(1)   cmd 0x33
                                        |  _pspSysconGetCtrl2()           cmd 0x08   syscon.c:355
                                        |
                        psp_joypad_read_input()              drivers/input/joypad_psp.c:474
                                        |
                        psp_joypad_thread()   loop + msleep  joypad_psp.c:453
                           |                          |
        psp_joypad_process_input()            psp_mouse_process_input()
        joypad_psp.c:498                      joypad_psp.c:593
        per-open queues, /dev/joypad          input core -> mousedev
        (char 39,200)                         -> /dev/input/mice, /dev/psaux
                           |                          |
                 psposk2 (on-screen keyboard)    pspmd (console mouse daemon)
                 binary only, from rc.sysinit    binary only, from rc.sysinit
```

Both userland consumers are fed by the same kernel thread and the same
`read_input()` call. Both dying together points at or below
`psp_joypad_thread`.

---

## 3. What has been observed [HW]

1. Kernel, timer and framebuffer keep running for minutes. Confirmed by the
   on-device telemetry app (`/home/ubuntu/psp/telem/telem.c`), whose own loop
   counter and clock keep advancing.
2. At an unpredictable point, 17 s to 250 s or more into a boot, all input
   stops: the mouse device and the on-screen keyboard character stream.
3. It never recovers within that boot.
4. It is not tied to idleness, not on a fixed timer, and memory does not leak.
5. The kernel ring buffer, captured continuously through the moment of
   death on two runs, did not change. No oops, no printk.
6. A kernel with spin-count timeouts added to the two busy-wait loops in
   `Syscon_cmd` was booted. Input still died on the same timescale.

---

## 4. Corrections to the incoming brief

These come from reading the source. They change what the instrumentation
must cover. Each one should be re-verified by the recon stage.

### 4.1 The timeout test did not falsify "the handshake stops arriving"

The incoming brief says the hang hypothesis is falsified. The test supports
a narrower conclusion.

- The timeout patch returns `-3`, `-4` or `-5` and prints nothing.
  [SRC] `syscon.c:113,154,254`
- `read_input()` turns any negative return into `FALSE`, silently.
  [SRC] `joypad_psp.c:487-488`
- The thread then sleeps and tries again. [SRC] `joypad_psp.c:468`

So if the syscon stops acknowledging permanently, the patched kernel
produces: input dead, system alive, empty kernel log. That is the same as
what was observed.

What observation 6 does establish: bounding the loops does not restore
input. What it does not establish: whether the loops are timing out.
**"ACK never arrives" remains a live hypothesis (H1).**

One unpatched-kernel caveat: with `CONFIG_PREEMPT=y`, a kernel thread
spinning forever would not freeze the system either, so "system stays alive"
never distinguished the two cases.

### 4.2 Kernel log silence carries almost no information

No code on the path from `Syscon_cmd` to the input queues prints anything
on failure. The `Kprintf` calls in `syscon.c` are all commented out. Silence
is what every hypothesis in section 5 predicts.

### 4.3 The poll period is about 50 ms, not 16 ms

`PSP_JOYPAD_SAMPLE_RATE` is 20, so the thread calls `msleep(50)`.
[SRC] `joypad_psp.c:64,468`. At HZ=250 the real period is a little longer,
plus the time of two syscon commands. Buffer sizing must use about 18 to 20
polls per second, which is about 18,000 polls in 15 minutes, with two
syscon commands each.

### 4.4 The watchdog calls the syscon from the timer interrupt, with no locking

- `psp_cputimer_handler()` calls `psp_watchdog_tick()` on every timer
  interrupt. [SRC] `arch/mips/psp/psp.c:348-359`
- Every `PSP_WATCHDOG_CYCLE * HZ` ticks (5 s) that calls
  `psp_pacify_watchdog()`, which calls `pspSysconNop()`, which runs a full
  `Syscon_cmd` transaction in interrupt context.
  [SRC] `psp.c:41,371-392`
- `Syscon_cmd` takes no lock and does not mask interrupts. The original
  `sceKernelCpuSuspendIntr()` is a comment. [SRC] `syscon.c:99`

So once every 5 s a complete syscon transaction can be inserted into the
middle of the poll thread's transaction. This is hypothesis H4. It was not
in the incoming brief.

### 4.5 Two different kinds of "bad data" behave differently

`Syscon_cmd` prefills `rx_buf` with `0xff`. [SRC] `syscon.c:92-93`.
`_pspSysconGetCtrl2` unpacks `rx_buf` regardless of the result.
[SRC] `syscon.c:362-366`. The driver inverts the button word.
[SRC] `joypad_psp.c:490`

| Raw button word | After inversion | `read_input()` | Visible effect |
|---|---|---|---|
| all `0x00` | all ones, HOLD set | `FALSE` | Everything suppressed. This is the brief's hypothesis. |
| all `0xff` (the prefill; happens if the RX FIFO is empty, in which case `result` stays 0 and the checksum is skipped) | zero, HOLD clear | `TRUE`, no buttons | Button state frozen at "nothing pressed". Analog reads `0xff,0xff`, which in mouse mode is +16 per poll on both axes (`joypad_psp.c:689`). |

The second row predicts a drifting cursor if mouse mode is on. See Q1.

### 4.6 The checksum is only checked when the first received byte is positive

[SRC] `syscon.c:226`. `BYPASS_ERR_CHECK` is 1, so the SPI status checks are
compiled out. [SRC] `syscon.c:10,168`. A short or shifted frame can be
accepted as valid.

### 4.7 The poll thread is a bare `kernel_thread` that uses interruptible waits

Created with `kernel_thread(..., CLONE_FS | CLONE_SIGHAND)` and no
`daemonize()`. [SRC] `joypad_psp.c:195-197`. It calls `down_interruptible`
when feeding queues. [SRC] `joypad_psp.c:390,530`. If a signal ever becomes
pending on that thread it is never cleared, and every `down_interruptible`
fails from then on. This alone would not stop the mouse path, which takes no
semaphore, so it is a weak candidate given observation 2. It is cheap to
record and should be recorded.

---

## 5. Hypotheses the single run must discriminate

The instrumentation is judged on whether each row would leave a distinct,
recoverable signature. "Unknown" must also be recoverable: raw data, not
only classified counters.

| ID | Hypothesis [HYP] | What the trace would show |
|---|---|---|
| H1 | Syscon stops acknowledging. Timeouts fire on every poll. | Return `-4` (or `-3`) on every command after onset. Command duration jumps to the full spin budget. |
| H2 | Commands succeed, button word is all zero, read as HOLD. | Return ≥ 0, raw bytes 3..6 are `00`, `read_input` exits through the HOLD branch. |
| H3 | Commands return the `0xff` prefill. RX FIFO empty after ACK. | Return 0, zero words received, raw bytes all `ff`, `read_input` returns `TRUE`. |
| H4 | Timer-interrupt `pspSysconNop()` interleaves with the thread's transaction and desynchronises the link. | An interrupt-context command begins while a thread-context command is in flight, immediately before onset. Onset falls on a 5 s watchdog boundary. |
| H5 | Checksum failures or syscon BUSY/resend (`0x80`/`0x81`) become permanent. | Return `-2` or `-5`, with raw frame showing the shift or the response code. |
| H6 | Frames are well formed but stale: the syscon keeps answering with the same state whatever is pressed. | Valid returns, valid checksum, raw bytes never change although the operator is pressing buttons per the runbook. |
| H7 | Syscon data is fine, the fault is above it: thread stopped, signal pending, semaphore stuck, queue not drained, input core. | Raw bytes follow the operator's presses after onset. Loop counter, per-stage counters and `signal_pending` show where delivery stops. |
| H8 | Syscon or SPI/GPIO controller changes state: register values differ after onset. | Snapshot of the SPI and GPIO registers differs between a healthy poll and a dead one. |
| H0 | None of the above. | Raw ring contents and counters still recovered. Analyst works from raw data. |

H4 is attractive because it would explain the timing: a fixed 5 s
opportunity with a small chance each time gives a wide, memoryless spread
of failure times. It does not by itself explain why the failure is
permanent. Treat it as one row among nine, not as the answer.

---

## 6. Constraints on the instrumentation

### 6.1 Required property: history, not a point sample

The design must keep a running history of recent poll cycles with raw
syscon state, plus whole-run summaries. A single printk aimed at one
hypothesis does not meet the requirement. This is a named reviewer
checklist item in [WORKFLOW.md](WORKFLOW.md) (item D1).

### 6.2 Channels out of the device

| Channel | Status | Notes |
|---|---|---|
| Memory Stick file under `/ms0` | Works [HW] | `telem` appends and `fsync`s every tick. Survives battery pull up to the last completed sync. |
| Framebuffer | Works [HW] | Human-readable only. Useful for a live "death detected" indicator and for a photograph as backup. |
| Kernel ring buffer | Works [HW] | 16 KB. `telem` snapshots it to `/ms0/kmsg.txt`. It wraps, so high-rate printk destroys history. |
| `/proc` | Available [SRC] | Natural way to expose a kernel ring to userland. |
| UART3 serial | Not available | No adapter. |
| USB | Not available | Compiled out. |

Input is dead after onset, so nothing may depend on the operator typing a
command. Extraction must be automatic and continuous from boot.

### 6.3 Things that would invalidate the run

- Adding a lock, interrupt masking or any timing change to the syscon path
  in the diagnostic kernel. That is a fix for H4 and would hide it.
  Observation cost must be small and must be stated.
- printk inside `Syscon_cmd` at poll rate. It wraps the log and writes to
  the framebuffer console.
- Recording from interrupt context with a structure that is not safe
  against the thread context it interrupts.
- Floating point anywhere in new userland code. No FPU, no emulator. See
  `telem/telem.c:30-35` and `telem/cbuild.sh` for the check.
- A log that grows without bound on the Memory Stick or blocks long enough
  to disturb the poll thread.
- Overwriting the baseline kernel folder on the Memory Stick.

### 6.4 Useful facts for the designer [SRC]

- The timer handler zeroes CP0 Count on every tick
  (`psp.c:350-355`), so `jiffies` plus CP0 Count gives sub-jiffy time.
  Verify before use.
- Registers touched by the transport: SPI `0xbe580000..0xbe580024`, GPIO
  `0xbe240000..0xbe240024`. Reading some of them has side effects
  (`0xbe580008` pops the RX FIFO). A register snapshot must only read the
  ones that are safe, and the design must say which and why.
- Other syscon callers: `pspSysconCtrlHRPower` at serial startup
  (`drivers/serial/serial_psp.c:352`), `pspSysconPowerStandby` at shutdown
  (`psp.c:218`). `psp_lcd_on()` does not touch the syscon (`psp.c:254`).

---

## 7. Build environment

This machine is the build box. `hostname` is `sldllm-node`, which is what
the brief calls `mynode`. aarch64, Ubuntu 24.04, passwordless sudo.

| Item | Location |
|---|---|
| Kernel tree, timeout patch applied, builds cleanly | `/home/ubuntu/psp/build/linux` |
| Timeout patch as a diff | `/home/ubuntu/psp/build/syscon-timeout.patch` |
| Pre-patch `syscon.c` | `build/linux/arch/mips/psp/ipl_sdk/syscon.c.orig` |
| Kernel config | `/home/ubuntu/psp/build/kernel-0.22.config` and `build/linux/.config` |
| Initramfs embedded in the kernel | `build/linux/psp-initramfs.cpio` (`CONFIG_INITRAMFS_SOURCE`) |
| Cross toolchain, i386 binaries | `/home/ubuntu/psp/staging_dir` |
| pspsdk shim headers | `/home/ubuntu/psp/build/pspsdk` |
| Telemetry app and its build script | `/home/ubuntu/psp/telem/` |
| Unpacked root filesystem for reference | `/home/ubuntu/psp/extract/root2` |
| Container notes | `/home/ubuntu/psp/BUILD_ON_UBUNTU.md` |

Container:

```
sudo docker run --rm --platform linux/386 -v ~/psp:/work -w /work psp-build:bullseye <cmd>
```

Both `psp-build:bullseye` and `i386/debian:bullseye` are present.

Known gotchas, already solved in the tree:

- Two "mixed implicit and normal rules" Makefile splits for make 4.3.
- `PATH` must contain only the staging_dir bin directories. The
  target-triplet bin directory shadows host binutils.
- `HOSTCC` and `HOSTCXX` must point at the container's real gcc and g++.
- Minimal pspsdk shim headers are in place for the ipl_sdk code.

Outputs of the last good build: `vmlinux`, `vmlinux.bin` (raw), and
`vmlinux-0.22.bin` (gzip of `vmlinux.bin`, 899,402 bytes). Verify any built
binary with `mipsel-linux-uclibc-objdump`, and bFLT userland with
`mipsel-linux-uclibc-flthdr`.

### Gaps in the build record

1. **The exact kernel build command line is not recorded anywhere.** No
   script, no shell history. The build logs
   (`/home/ubuntu/psp/build/build*.log`) show output only. The recon stage
   must reconstruct it, prove it by rebuilding the unmodified tree to a
   byte-identical or functionally identical image, and commit it as a script.
2. **The tree is not under version control** and build outputs are owned by
   root. Do not edit it in place. Copy it and work in the copy.
3. `build3.log` ends in a link failure (`expand_stack`). The working image
   is dated later (Sep 22 19:24), so a later unlogged build succeeded.
   Recon must confirm the tree as it stands builds.

### Deploy convention

Each kernel goes in its own `PSP/GAME/<name>/` folder on the Memory Stick.
`pspboot` reads `pspboot.conf` relative to its own folder, so folders are
independent. Never write into the known-good baseline folder. Agents do not
have access to the Memory Stick. They produce a folder ready to copy and
the human copies it.

---

## 8. Open questions for the human operator

None of these block the recon or design stages. Answers sharpen the design.

| # | Question | Why it matters |
|---|---|---|
| Q1 | At the moment input died, was mouse mode on, and did the cursor stop dead or drift to a corner? | Drift indicates H3. A dead stop argues against it. **Answered 2026-09-27: operator thinks it stopped dead, not certain. Weak evidence against H3. H3 stays in the matrix.** |
| Q2 | Do the existing `telem.log` files give time of death relative to boot, and can they be shared? | H4 predicts death near 5 s multiples of uptime. Free evidence, no hardware run needed. **Answered 2026-09-27: not known. The design must timestamp against the watchdog cycle itself.** |
| Q3 | After input dies, does the physical HOLD switch, the power switch or the volume keys do anything? | Separates "syscon unresponsive" from "Linux not listening". |
| Q4 | Is it strictly one run, or one session in which several folders could be booted in turn? | If several, a second kernel can be staged at no extra build risk. |
| Q5 | May a second folder carry a candidate fix (for example masking interrupts around `Syscon_cmd`) in addition to the diagnostic kernel? | Out of scope unless authorized. |
| Q6 | What are the exact names of the baseline folder and the timeout-patch folder on the stick? | To guarantee the new folder name does not collide. |
| Q7 | How long can the operator keep pressing buttons after death before pulling the battery? | The runbook's post-death button sequence is what separates H6 from H7. |

---

## 9. Amendments after Gate G0 (2026-09-27)

Text in this section was approved by the G0 fact checkers and **supersedes
the sections above wherever they conflict**. Full evidence is in
[recon/syscon.md](recon/syscon.md), [recon/input.md](recon/input.md) and
[recon/build.md](recon/build.md).

### 9.1 Corrections

| Section | Correction |
|---|---|
| 2, OS row | This tree builds `Linux version 2.6.22`, not `2.6.22-uc1`. It is vanilla 2.6.22 + `kernel-0.22.lf.patch` + a make-4 Makefile fix (`Makefile:415-418`, `:1446-1449`) + the syscon timeout change + the uc0 mm graft. The `-uc1` banner belongs to the 2008 distributed kernel in `/home/ubuntu/psp/extract/`. **Which kernel each [HW] observation in section 3 used is not known.** |
| 4.1 | Addition, not refutation. The watchdog `pspSysconNop()` runs with interrupts off. In the unpatched kernel its waits are unbounded, so a syscon that had stopped acknowledging entirely would freeze the whole machine at the next watchdog tick. If observations 1 to 5 were made on the unpatched kernel, the system staying alive shows watchdog commands kept completing after input died. |
| 4.3 | `msleep(50)` at HZ=250 is 14 jiffies. Minimum period 56 ms: at most 17.86 polls/s, at most 16,071 polls in 15 minutes, two syscon commands each. Use 18,000 only as a conservative upper bound. |
| 4.4 | The watchdog period is 1250 timer interrupts, nominally 5 s. The watchdog command runs **before `irq_enter()`** (confirmed in compiled `psp.o`), so `in_irq()` and `in_interrupt()` are false inside it. Context must be identified some other way. It is also sent once at boot from `prom_init` (`psp.c:557`). |
| 4.5 | +16 is at `joypad_psp.c:690`. REL_Y is reported as `-dy` (`:652`), so H3 drift is X +16, Y −16 per poll. An all-zero frame returns 0 and skips the checksum. |
| 4.6 | Also: the frame length used for the checksum (`rx_buf[1]`, `syscon.c:228`) has no upper bound and can read past the 16-byte buffer. Syscon error codes 0x83 and 0x86 are returned as success. |
| 4.7 | On MIPS, `down_interruptible` checks for signals only on its contended slow path (`include/asm-mips/semaphore.h:85-94`). A pending signal would lose events intermittently, not permanently. No path that signals the thread in normal running was found. |
| 6.4, timestamps | Inside the watchdog command CP0 Count is already reset but `jiffies` is not yet incremented, so its records would sort before the thread activity they interrupted unless corrected. |
| 6.4, registers | The source proves **no** SPI or GPIO register read to be free of side effects. Only `0xbe580008` is proven harmful. Every other register is UNKNOWN. A snapshot must justify each address from hardware documentation, not from source alone. |
| 6.4, callers | Add: `pspSyscon_init` at boot (`psp.c:135`), boot-time `pspSysconNop` (`psp.c:557`). Add a non-syscon actor on the same GPIO registers: `psp_led_ctrl` does read-modify-write on `0xbe240008`/`0xbe24000c` on every Memory Stick sector (`psp.c:401,406`; `ms_psp.c:290-292,312-314`). |
| 7, timeout patch | `/home/ubuntu/psp/build/syscon-timeout.patch` does not apply and is not the diff of the tree. The reference is `/home/ubuntu/psp/work/syscon-timeout.applied.patch`. |
| 7, config | `build/linux/.config` is the config in use. `kernel-0.22.config` is the 2008 uc1 config and its line numbers differ. |
| 7, initramfs | `.config:163` points at the **original** tree's cpio by absolute path. A build of the work copy ignores its own cpio until that line is changed. |
| 7, build gaps | Resolved. `/home/ubuntu/psp/work/build.sh` with `REPRODUCE_BASELINE=1` rebuilds the unmodified tree to byte-identical `vmlinux`, `vmlinux.bin`, `vmlinux-0.22.bin` and `System.map`. About 3 minutes. Images are made by hand after `make`: `objcopy -O binary`, then `gzip -9 -n`. `build.sh` runs `git clean -fdx`, so new files must be `git add`ed first. |
| 6.2, kernel log | `telem` saves `kmsg.txt` only when the log length changes. After 16 KB has been logged the length stays at 16384 and later messages are never captured. Observation 5 holds only if the saved files are under 16 KB. |
| 2, data path | The mouse path runs only in mouse mode (`joypad_psp.c:464`). `telem`'s INPUT counter counts mouse button presses only. Both daemons also share `/dev/vcs` and the framebuffer, so "both died, so the fault is at or below the thread" needs qualifying. `psposk2` injects characters by `ioctl(101)` on `/dev/vcs`. |

### 9.2 Hypotheses added to the section 5 matrix

| ID | Hypothesis [HYP] | What the trace would show |
|---|---|---|
| H9 | Lock-order deadlock between the poll thread's queue feed (`list_sem` then queue sem, `joypad_psp.c:530,390`) and close of `/dev/joypad` (queue sem then `list_sem`, never released, `:348-359`). Needs `psposk2` to exit or close first. | Thread loop counter stops advancing. Last record shows the thread inside delivery. Syscon records from the thread stop while watchdog records continue. |
| H10 | `psp_led_ctrl` read-modify-write on the GPIO set/clear registers during Memory Stick I/O disturbs the syscon request line (GPIO3) mid-transaction. | Onset coincides with Memory Stick activity. **The instrumentation's own logging to the stick raises the rate of this event**, which the perturbation statement must address. |

### 9.3 Blocker

**No `pspboot` files exist on this machine.** A bootable deploy folder
cannot be produced until the human supplies the contents of an existing
`PSP/GAME/<name>/` folder (EBOOT.PBP and `pspboot.conf`).

### 9.4 New open questions

| # | Question | Why it matters |
|---|---|---|
| Q8 | Which kernel was running for each observation in section 3? | **Answered 2026-09-30: observations 1 to 5 were on the 2008 distributed image (`2.6.22-uc1`). Observation 6 was necessarily the kernel rebuilt here.** See 9.5. |
| Q9 | Are the saved `kmsg.txt` files smaller than 16 KB? | **Answered 2026-09-30: 1,606 bytes. Observation 5 stands: the log really was silent.** |
| Q10 | When input died, was the on-screen keyboard still drawn and was `psposk2` still running? | **Answered 2026-09-30: after death the OSK cannot be brought up with L+R triggers.** That is consistent with `psposk2` alive but receiving nothing from `/dev/joypad`; there is no sign it exited. H9 needs a close of `/dev/joypad`, so H9 is now low priority but stays in the matrix because whether the process exited was not directly observed. |

### 9.5 Consequence of Q8: H1 is now disfavored, with a caveat

Observations 1 to 5 were made on the 2008 `2.6.22-uc1` image. If that image
pacifies the watchdog the same way this tree does (an unbounded
`pspSysconNop()` with interrupts off every 1250 ticks, dossier 4.1
amendment), then a syscon that had stopped acknowledging would have frozen
the machine within 5 s of input dying. It did not. So on that kernel the
syscon kept answering the watchdog after input died, and **H1 in its pure
form (no ACK ever again) is disfavored.** A variant survives: the syscon
answers the watchdog's command 0x00 but not the controller commands 0x08 or
0x33, or answers them badly. The instrumentation must still record H1's
signature.

Caveat: this tree is not the uc1 tree (9.1, OS row). The recon stage did not
confirm that the 2008 image's watchdog path is the same code. The Stage 1
designer should treat "same watchdog path in the 2008 image" as
UNVERIFIED and may ask for a disassembly check of
`/home/ubuntu/psp/extract/k` if the design depends on it.

Second consequence: observation 6 (the timeout-patch kernel) is the only
observation on the kernel the agents can build. The instrumented kernel
descends from that one. Any difference in behaviour between the 2008 image
and this tree is itself a candidate cause and must be kept in mind when the
run's data is read.

### 9.6 New evidence from the stick (2026-09-30): input deaths fall on the 5 s watchdog boundary

The telemetry logs recovered from the Memory Stick
(`/home/ubuntu/psp/telem/logs-from-stick/telem.log`, `telem-v1.log`) record
kernel uptime (`/proc/uptime`) on every 0.23 s tick together with a running
count of input events. In three sessions the operator was generating input
continuously (about 4 events/s) when input died, so the death is bracketed
to one tick. All three sessions ran the 2008 image (9.7).

| Log, session | Last tick with input (uptime s) | First tick without (uptime s) | 5 s multiple inside the window |
|---|---|---|---|
| telem-v1 s10 | 274.90 | 275.12 | **275.0** |
| telem s2 | 145.07 | 145.30 | **145.0** (input counted at 145.07 occurred after the previous tick at 144.84) |
| telem s8 | 139.99 | 140.24 | **140.0** |

Three out of three deaths fall inside a window of about 0.45 s that contains
an exact multiple of 5 s of kernel uptime. By chance alone that is roughly
1 in 1,000. The only 5 s cadence in this kernel is the watchdog
(`psp_watchdog_tick`, 1250 timer interrupts, `psp.c:41,375-376`), whose
action is a syscon command sent from the timer interrupt path with
interrupts off, unbounded in the 2008 image if 9.5's caveat holds.

Consequences:

- **H4 (watchdog command interleaving with the poll thread's transaction) is
  now the leading hypothesis.** It is still not proven: the interleave is
  the trigger, and what leaves input permanently dead afterwards is not yet
  known. The recon report `recon/syscon.md` section 5 lists the interruption
  points and their outcomes; at least one leaves the thread waiting for an
  ACK that was consumed by the watchdog's transaction.
- The design's requirement to timestamp against the watchdog cycle (G1 item
  D16) is now load-bearing, not nice-to-have. Records must show, for each
  thread-context command, whether a watchdog command began during it, and
  at which phase.
- Two other sessions (`telem-v1` s1 and s3) had zero input events from the
  moment the app started, at uptimes 36 s and 154 s. Input was already
  dead when the app started. They carry no timing information but show
  death can occur before 36 s.
- A design that is otherwise hypothesis-agnostic must nonetheless make sure
  the H4 signature is captured with the phase resolution needed to say
  *which* interruption point occurred.

Caveats: uptime and the watchdog counter both derive from the same timer
interrupt, but their zero points differ by a small constant, so the exact
phase is unknown (the observed offset is within about ±0.2 s of zero). The
`inputs` counter counts mouse events only (recon/input.md).

### 9.7 Baseline boot folder, recovered from the stick (2026-09-30)

Copied to `/home/ubuntu/psp/pspboot-baseline/` from
`/Volumes/Untitled/PSP/GAME/uClinux/` on the operator's Mac.

| File | Note |
|---|---|
| `EBOOT.PBP` | 190,246 bytes, the pspboot loader |
| `pspboot.conf` | `kernel=vmlinux-0.22.bin`, `cmdline=console=tty osk=Dv4`. Comment in the file: do not add `mem=`, it crashes. |
| `vmlinux-0.22.bin` | sha256 `628dddfe…1282d2`, identical to `/home/ubuntu/psp/extract/vmlinux-0.22.bin`. **This confirms Q8: the baseline folder boots the 2008 `2.6.22-uc1` image.** |
| `kmodlib.prx`, `README` | Loader support module and 2008 release notes |

Folder names on the stick (Q6): baseline is `uClinux`. Folders
`uClinux_FIX` and `uClinux_WIP` are to be ignored and are being deleted by
the operator. **The new folder must not be named `uClinux`, `uClinux_FIX`
or `uClinux_WIP`.** Suggested: `uClinux_TRACE`.

Other logs recovered: `kmsg.txt` (1,606 bytes, Q9), `keymap.log` (2,459
lines, a mouse-byte trace from a different tool).

### 9.8 Operator answers to the runbook's pre-run questions (2026-10-06)

Recorded verbatim in substance from the human operator; the design was
not changed (any change goes back to G1).

| # | Question (RUNBOOK "Before you start") | Answer |
|---|---|---|
| 1 | Which buttons were being pressed when input died in the earlier sessions? | **Input died no matter what buttons were pressed.** Sometimes it happened while the on-screen keyboard had just been raised with the Right and Left triggers at the command line; other times it happened **with no input at all**. |
| 2 | Battery or AC adapter? | **Battery.** AC "seemed to create more issues when booting uClinux". RUNBOOK A5: run on battery. |
| 3 | Was mouse mode on? | **No.** |

Orchestrator notes (not design changes):

- "With no input at all" is evidence against any explanation that needs a
  button press or a user-driven race to trigger the death (it weakens the
  pure forms of H6/H7 as *causes*; they remain in the matrix as *shapes*
  the records must still separate, D17). It is consistent with H4 (the
  5 s watchdog Nop colliding with the poll thread, which runs whether or
  not anything is pressed) and with H10 (Memory Stick LED read-modify-write
  from unrelated I/O). Together with 9.6 this strengthens H4 as leading.
- Mouse mode off in the earlier sessions means the dead-stop/drift
  question (Q1, H3) carried less information than assumed; H3 stays in
  the matrix on the design's evidence, not on Q1.
- The runbook's healthy-reference and post-death scripts (C0, D1-D7a)
  remain as designed: they exist to make the recorded shape separable,
  not because the operator's presses are thought to cause the death.
- Open operator questions still unanswered: Q3 (HOLD/power/volume after
  death), Q4 (one run or one session with several folders), Q5 (may a
  second folder carry a candidate fix), Q7 (how long presses can continue
  after death before the battery pull; the runbook's D script assumes
  about 100 s plus up to 2 min 15 s in D8). G3 R7 requires each answered
  or shown not to matter.
