# Recon A: syscon transport

Stage 0 recon report. Author role: Recon A. Date 2026-09-27.
Scope: `Syscon_cmd` and everything that shares its hardware, in every
execution context. This report does not propose any designs or fixes.

Paths are relative to `/home/ubuntu/psp/build/linux` unless they start
with `/`. Every claim cites file:line and quotes the code. Labels:

- **[SRC]**: read in the source, quoted here.
- **[OBJ]**: read in the built object code (`syscon.o`, `psp.o`, `vmlinux`).
  I disassembled it with the tree's own `mipsel-linux-uclibc-objdump`,
  running in the `psp-build:bullseye` container with `/home/ubuntu/psp`
  mounted **read-only** (`-v /home/ubuntu/psp:/work:ro`).
- **[DERIVED]**: my reasoning from [SRC] or [OBJ] facts. The reasoning is
  shown.
- **UNVERIFIED** or **UNKNOWN**: the source does not settle it. This
  includes all hardware semantics.

I wrote nothing inside `build/linux`. I ran the patch tests on copies in
my scratchpad.

---

## 0. Summary of findings that change the dossier

| # | Dossier item | Verdict | Short reason |
|---|---|---|---|
| A1 | 4.1, last paragraph ("system stays alive never distinguished the two cases") | **Wrong for the unpatched kernel** | The timer-IRQ `pspSysconNop()` runs with interrupts disabled. In the unpatched kernel its busy-waits had no bound. If the syscon had stopped raising GPIO4 altogether, the whole machine would have frozen at the next 5 s watchdog tick. See §3.1. Which kernel observations 1 to 5 were made on is not recorded (new question QA1). |
| A2 | 4.1 / H1 | **New code-derived mechanism** | In the **unpatched** kernel, one interleave at the ACK-wait point (§5, point P4/P5a) can leave the poll thread spinning forever while the system and the watchdog keep working. That is a permanent input death with no printk. The timeout patch bounds this spin, so in the patched kernel this path alone cannot be permanent. See §5.4. |
| A3 | 4.4 | Confirmed, with one refinement | The watchdog Nop runs **before** `irq_enter()`, so `in_irq()` and `in_interrupt()` are false during it (§2, [OBJ]). The Nop is also issued once at boot from `prom_init`. |
| A4 | 4.5 | Confirmed. Two corrections. | (a) The `+16` is at `joypad_psp.c:690`, not 689. Y is reported as `-dy`, so the drift is REL_X +16, REL_Y −16 (`joypad_psp.c:652`). (b) An **all-zero** frame also skips the checksum, because `result` is the first byte (0), so the H2 shape needs no checksum luck (§4.5). |
| A5 | 4.6 | Confirmed, with additions | "Positive" means non-zero (the value is a `u8`). The checksum length is taken from the frame with no upper bound: an out-of-bounds read of the caller's stack when `rx_buf[1] >= 16`. Response codes `0x83` and `0x86` pass as success. |
| A6 | 6.4, Count | Confirmed, with four caveats | See §6. The important one: inside the watchdog Nop, Count has already been reset but `jiffies` has not yet been incremented, so a naive (jiffies, Count) stamp taken there sorts **before** the thread activity it interrupted. |
| A7 | 6.4, registers | Ranges correct, detail incomplete | Not every register in the ranges is used. `0xbe580018` is referenced only in compiled-out code. **No** SPI or GPIO register read is proven free of side effects by the source (§4). |
| A8 | 6.4, "other syscon callers" | **Incomplete** | Missing: `pspSysconNop` from `prom_init` (`psp.c:557`) and `pspSyscon_init` (`psp.c:135`). Also missing a **non-syscon writer of the same GPIO set/clear registers** that uses read-modify-write: `psp_led_ctrl`, called on every Memory Stick sector (§2.2). |
| A9 | 7, "Timeout patch as a diff" | **The patch file does not match the tree as a diff** | `syscon-timeout.patch` has wrong hunk headers. GNU `patch` and plain `git apply` both reject it. It applies only with `git apply --recount`. The result is semantically identical to the tree but textually different (§7). |

New questions for the human (add to dossier §8 if the fact checker agrees):

- **QA1**: Were observations 1 to 5 made on the unpatched baseline kernel
  or on the timeout-patched kernel? §3.1 and §5.4 depend on the answer.
- **QA2**: In an unpatched-kernel run, did `telem`'s loop rate (iterations
  per second, not only "still advancing") drop at the moment input died?
  A poll thread spinning forever at P4/P5a (§5.4) is a runnable CPU hog.

---

## 1. `Syscon_cmd` walked step by step

Source: `arch/mips/psp/ipl_sdk/syscon.c:61-258` (patched).
`REG32` is `#define REG32(ADDR) (*(vu32*)(ADDR))` (`syscon.c:15`), so every
access is a volatile 32-bit load or store. [OBJ] confirms the compiled
`Syscon_cmd` performs every access below, in this order. `syscon.o`
disassembly offsets are given as `+0x..`.

Notation: **G3** = GPIO bit 3 output (0x08), **G4L** = GPIO4 latched
status bit (0x10 of `0xbe240020`), **M** = value last written to
`0xbe580004`, **RXF / TXF** = SPI RX / TX FIFO.

### 1.1 Buffers and state

- All transaction state is local. There are no static variables in
  `syscon.c` [SRC, whole file]. `tx_buf` and `rx_buf` are `u8[0x10]` on
  each caller's stack: `syscon.c:265`, `:281`, `:357`
  `u8 tx_buf[0x10],rx_buf[0x10];`.
- **[DERIVED]** So an interrupt-context call and the thread-context call it
  interrupts share **only the hardware**: SPI and GPIO registers, and
  whatever state is inside the syscon chip.

### 1.2 Sequence

| Step | Line(s) | Code | Access | Notes |
|---|---|---|---|---|
| S0 | 75 | `retry:` | – | Retry re-enters here. Everything below repeats. |
| S1 | 77-81 | `cnt = tx_buf[1]; for(i=0;i<cnt;i++) sum += tx_buf[i]; tx_buf[cnt] = ~sum;` | memory | TX checksum. |
| S2 | 84 | `tx_buf[cnt+1] = 0xff;` | memory | Pad byte. |
| S3 | 92-93 | `for(i=0x0f;i>=0;i--) rx_buf[i]=0xff;` | memory | **Prefill all 16 bytes with 0xff.** Repeated on every retry. |
| S4 | 99 | `// sceKernelCpuSuspendIntr()` | – | Comment only. No interrupt masking, lock or preempt-disable anywhere in the function. |
| S5 | 102 | `dmy = REG32(0xbe240004);` | **R** GPIO+0x04 | Comment "sceGpioPortRead()". Value discarded. [OBJ] `+0xdc`. |
| S6 | 104 | `REG32(0xbe24000c) = 0x08;` | **W** GPIO+0x0c | "sceGpioPortClear(8)": G3 low. |
| S7 | 106 | `if(REG32(0xbe58000c) & 4)` | **R** SPI+0x0c | RX-not-empty test. |
| S8 | 110-116 | `spin = SYSCON_SPIN_MAX; while( REG32(0xbe58000c) & 4) { if(spin-- == 0) return -3; dmy = REG32(0xbe580008); }` | **R** SPI+0x0c, **R** SPI+0x08 per iteration | "clear prevouse data ?": drains RXF. **Exit −3.** |
| S9 | 119 | `dmy = REG32(0xbe58000c);` | **R** SPI+0x0c | Value discarded. |
| S10 | 121 | `REG32(0xbe580020) = 3; // clear error status ?` | **W** SPI+0x20 | |
| S11 | 128-134 | `for(i=0;i<(cnt+1);i+=2) { dmy = REG32(0xbe58000c); REG32(0xbe580008) = (ptr[0]<<8)\|ptr[1]; ptr += 2; }` | per word: **R** SPI+0x0c (discarded), **W** SPI+0x08 | Pushes ⌈(cnt+1)/2⌉ 16-bit words, first byte in the high half. For cnt=2 (Nop, GetCtrl2): `[cmd,02]`, `[sum,ff]`. For cnt=3 (AStickPower): `[33,03]`, `[01,sum]`. The TX FIFO space is never checked. |
| S12 | 136 | `REG32(0xbe580004) = 6; // RX mode ?` | **W** SPI+0x04 | M=6. |
| S13 | 140 | `REG32(0xbe240008) = 0x08;` | **W** GPIO+0x08 | "sceGpioPortSet(8)": G3 high = request asserted. |
| S14 | 151-156 | `spin = SYSCON_SPIN_MAX; while( (REG32(0xbe240020) & 0x10)==0) { if(spin-- == 0){ REG32(0xbe580004)=4; REG32(0xbe24000c)=0x08; return -4; } }` | **R** GPIO+0x20 per iteration | "sceGpioQueryIntr(4)": wait for G4L. **Exit −4** after writing M=4 and G3 low. |
| S15 | 159 | `REG32(0xbe240024) = 0x10;` | **W** GPIO+0x24 | "GpioAcquireIntr(4)": ack or clear G4L. |
| S16 | 166 | `result = 0;` | – | |
| S17 | 168-197 | `#if BYPASS_ERR_CHECK #else ... #endif` | none | Compiled out (`#define BYPASS_ERR_CHECK 1`, `syscon.c:10`). [OBJ]: there is no access to `0xbe580018` in `Syscon_cmd`. |
| S18 | 201-217 | `for(i=0;i<0x10;i+=2) { if( (REG32(0xbe58000c) & 4)==0) break; wdata = REG32(0xbe580008); bdata = wdata>>8; if(i==0) result = bdata; ptr[0] = bdata; ptr[1] = wdata & 0xff; ptr+=2; }` | per word: **R** SPI+0x0c, **R** SPI+0x08 | Reads 0 to 8 words, stopping when RXF is empty. `result` = first byte (0..255). |
| S19 | 219 | `REG32(0xbe580004) = 4;` | **W** SPI+0x04 | M=4. |
| S20 | 222 | `REG32(0xbe24000c) = 0x08;` | **W** GPIO+0x0c | G3 low. |
| S21 | 226-246 | `if(result>0) { cnt = rx_buf[1]; if(cnt < 3) result = -2; else { ...sum over rx_buf[0..cnt-1]...; if( (sum^0xff) != rx_buf[cnt]) result = -2; } }` | memory | Checksum only if the first byte is non-zero. **Exit −2.** |
| S22 | 249-255 | `switch(rx_buf[2]) { case 0x80: case 0x81: if(++retry_cnt < SYSCON_RETRY_MAX) goto retry; result = -5; break; }` | memory | Tests `rx_buf[2]` **whatever `result` is** (also after −2 or 0). 16 attempts in total. [OBJ] `+0x318..0x320`: `addiu t8,t8,1` / `bnel t8,v0(16),7c`. **Exit −5.** |
| S23 | 257 | `return result;` | – | |

### 1.3 Every exit: return value, hardware state, `rx_buf`

| Exit | Where | Return | `rx_buf` on exit | G3 | M (SPI+0x04) | G4L acked this attempt? | RXF |
|---|---|---|---|---|---|---|---|
| E1 | `syscon.c:113` | **−3** | all 16 bytes `0xff` (S3) | low (S6) | unchanged from before the call | no | possibly not empty (that is why it failed) |
| E2 | `syscon.c:154` | **−4** | all `0xff` | low | 4 | no | UNKNOWN. The TX words were queued. Whether they were shifted, and whether any reply arrived, is unknown. |
| E3 | `syscon.c:257`, no RX words (loop broke at i=0) | **0** | all `0xff` | low | 4 | yes | empty |
| E4 | `:257`, ≥1 word, first byte `0x00` | **0** (checksum skipped) | received bytes, remainder `0xff` | low | 4 | yes | empty, or more than 8 words left behind (UNKNOWN whether possible) |
| E5 | `:257`, first byte ≠ 0, `rx_buf[1] < 3` | **−2** (`:231`) | received, remainder `0xff` | low | 4 | yes | as E4 |
| E6 | `:257`, first byte ≠ 0, checksum mismatch | **−2** (`:243`) | received, remainder `0xff` | low | 4 | yes | as E4 |
| E7 | `:257`, first byte ≠ 0, checksum OK | **1..255** = first byte ("generic status", `syscon.h:35-52`) | received, remainder `0xff` | low | 4 | yes | as E4 |
| E8 | `:254`, 16th consecutive attempt with `rx_buf[2]` ∈ {0x80,0x81} | **−5** (overwrites any −2 or 0) | the last attempt's bytes | low | 4 | yes | as E4 |

Notes on the exits (all [SRC], quoted above, or [DERIVED] from them):

- A retry (S22) happens only after E3 to E7 conditions. An E1 or E2 inside
  a retry returns at once with a fresh all-0xff `rx_buf`.
- `−1` cannot be returned. The only assignments of −1 are inside the
  compiled-out block (`syscon.c:176,187`).
- Response codes other than 0x80 and 0x81 are not examined. `syscon.h:71-72`
  `// parameter size error` / `#define SYSCON_RES_83 0x83` and `:74-75`
  `// twice send command error` / `#define SYSCON_RES_86 0x86` therefore pass
  as E7 (success) if the checksum is valid.
- **Out-of-bounds read**: `cnt = rx_buf[1]` (`:228`) has no upper bound.
  The loop `for(i=0;i<cnt;i++) sum += *ptr++;` (`:237-238`) and
  `rx_buf[cnt]` (`:240`) read up to `rx_buf[255]`, but every caller's
  `rx_buf` is 16 bytes (`:265,281,357`). A first word with `rx_buf[1] >= 16`
  (for example all-0xff data **with** words present) reads the caller's
  stack beyond the buffer and almost surely yields −2. Nothing is
  written out of bounds.
- `tx_buf[cnt]` and `tx_buf[cnt+1]` are written in place (`:81,84`). Every
  in-tree caller has cnt ≤ 6 (`syscon.h` table; callers in §2), so these
  writes stay inside `tx_buf`.
- Nothing prints. Every `Kprintf` in `syscon.c` is inside `//` comments
  (`:74,108,115,117,126,131,135,138,146,155,165,173,185,193,199,215,218,224,242,248`).
- **Not re-initialised per call**: TXF (there is no TX flush anywhere in
  the file), `0xbe580000`, `0xbe580014`, `0xbe580024`, and GPIO
  `0x00/0x10/0x14/0x18`. These are written only in `pspSyscon_init`
  (`:30-47`). [DERIVED] These plus the syscon chip's internal state are the
  only state that can carry from one call to the next. Whether TXF can
  hold residue across calls is **UNKNOWN**.

### 1.4 `_pspSysconGetCtrl2` (the poll command)

`syscon.c:355-367`:
```
tx_buf[0] = 0x08;
tx_buf[1] = 2;
result = Syscon_cmd(tx_buf,rx_buf);
*ctrl = rx_buf[3]|(rx_buf[4]<<8)|(rx_buf[5]<<16)|(rx_buf[6]<<24);
*vol1  = rx_buf[7];
*vol2  = rx_buf[8];
return result;
```
It unpacks on every exit, E1 to E8. [OBJ] `+0x5bc..0x5fc` confirms the
stores happen unconditionally after the `jal Syscon_cmd`.

### 1.5 Duration bounds

- `#define SYSCON_SPIN_MAX 1000000` (`syscon.c:12`). [OBJ] `lui v0,0xf` /
  `ori s1,v0,0x4240` = 1,000,000.
- The ACK-wait loop body is 11 instructions including one uncached MMIO
  load and 3 stack loads and stores, since `spin` is `vu32`
  ([OBJ] `+0x1cc..0x1f4`).
- **UNVERIFIED estimate**: at ~221 MHz (`psp.c:38`
  `#define PSP_COUNTS_PER_SEC 220912896 /* measured by tests */`, assuming
  Count runs at the CPU clock) and ≥1 cycle per instruction, one −4
  timeout costs **at least ~50 ms**. The real figure depends on MMIO read
  latency, which the source does not state. That is at least 12 timer
  ticks (4 ms each).
- Worst case for one call: 16 attempts, each draining RXF up to the
  budget and waiting for ACK up to the budget.

---

## 2. Every caller, and its execution context

Method: `grep -rnI -E 'Syscon|syscon'` over `*.c *.h *.S *.s` of the whole
tree, then filtered to PSP code. The non-PSP hits (`omap_udc.c`,
`clps711x`, `sysconf`, ...) are unrelated identifiers. I also grepped
`-i 'be58|be24|psp_pacify_watchdog|psp_shutdown|psp_led_ctrl|PSP_GPIO_(SET|CLEAR)'`
and all `0xbe2xxxxx|0xbe5xxxxx|0xbc10xxxx` literals under `arch/mips`,
`drivers` and `include/asm-mips`.

### 2.1 Calls into `syscon.c`

| # | Call site | Syscon function / cmd | Context | IRQs | Preemptible | When |
|---|---|---|---|---|---|---|
| C1 | `psp.c:135` `pspSyscon_init();` in `arch_early_setup()`, called from `init/main.c:506` (first statement of `start_kernel`) | `pspSyscon_init` (register setup, **no** `Syscon_cmd`) | early boot, only task | bootloader state (`local_irq_disable()` is later, `main.c:516`). The timer is not programmed yet (`plat_timer_setup`, via `time_init`, `main.c:568`). | n/a | once |
| C2 | `psp.c:557` `psp_pacify_watchdog();` in `prom_init()`, called from `arch/mips/kernel/setup.c:527`, called from `init/main.c:530` | `pspSysconNop()` (cmd 0x00) | early boot | **disabled** (`main.c:516`) | n/a | once |
| C3 | `psp.c:359` `psp_watchdog_tick();` → `:379` `psp_pacify_watchdog();` → `:392` `pspSysconNop();` | cmd 0x00 | **hard IRQ**: `handle_int` (`genex.S:162-169`: `SAVE_ALL`, `CLI`, `j plat_irq_dispatch`) → `plat_irq_dispatch` `psp.c:641-644` → `psp_cputimer_handler` | **disabled** | no | every 1250th timer interrupt (§2.3) |
| C4 | `serial_psp.c:352` `pspSysconCtrlHRPower( 1 );` in `psp_uart3_setup()` | cmd 0x34 | either `console_init()` (`main.c:580`: IRQs enabled at `:573`, preemption disabled since `:546`) through `register_console` → `.setup` (`serial_psp.c:151,687-694`), or `psp_serial_modinit` → `:723` (initcall in the `kernel_init` thread) | enabled | C4a: no. C4b: yes. | **once**: guarded by `static int baud = 0; if ( baud != 0 ) return 0; baud = ...` (`serial_psp.c:328-341`). Which path runs first depends on the `console=` argument: `CONFIG_CMDLINE=""` (`.config:658`), and `pspboot.conf` is not in the tree. **UNVERIFIED.** |
| C5 | `joypad_psp.c:486` `(void)_pspSysconCtrlAStickPower( 1 );` | cmd 0x33 | kernel thread `psp_joypad_thread` (created `joypad_psp.c:195-197` `kernel_thread( psp_joypad_thread, NULL, CLONE_FS \| CLONE_SIGHAND )`) | enabled | **yes** (`CONFIG_PREEMPT=y`, `.config:135`; no lock or preempt-disable on the path `joypad_psp.c:474-496`, `syscon.c:61-258`) | each poll, about 20/s (`joypad_psp.c:468`) |
| C6 | `joypad_psp.c:487` `if ( _pspSysconGetCtrl2( (u32*)&keys, px_, py_ ) < 0 ) return FALSE;` | cmd 0x08 | same thread | enabled | yes | each poll, immediately after C5 |
| C7 | `psp.c:216-219` `for (;;) { pspSysconPowerStandby(); }` in `psp_shutdown()`, called from `kernel/sys.c:910,925,934` (`sys_reboot`, restart/halt/power-off, under `lock_kernel()` `:906`) | cmd 0x35, forever | process context of the task calling `reboot()` | enabled | yes (the BKL is preemptible: `CONFIG_PREEMPT_BKL=y`, `.config:136`) | at shutdown. First sets `s_psp_shutdown = TRUE` (`:206`), after which C3 becomes `printk( "Stop pacifying watchdog\n" )` every 5 s from IRQ context (`psp.c:385-388`). |

Defined but **never called** (only comments or the header refer to them):
- `pspSysconCtrlLED` (`syscon.c:330`).
- `Syscon_wait` (commented calls at `syscon.c:97,144`).
- `pspSysconResetDevice` (commented, `psp.c:212`).
- `pspSysconMsOn` and `pspSysconCtrlMsPower` (commented, `ms_psp.c:116-117`).
- Every other inline in `syscon.h:101-178`.
- `pspMsInit` (`memstk.c:230`; its only call, `ms_psp.c:118`, is commented out).

### 2.2 Other code that touches the same GPIO registers (not through `syscon.c`)

`psp.c:32-33`:
```
#define PSP_GPIO_SET          ( *(volatile unsigned long *)( 0xbe240008 ) )
#define PSP_GPIO_CLEAR        ( *(volatile unsigned long *)( 0xbe24000c ) )
```
`psp.c:399-407`:
```
static void psp_gpio_set(unsigned long mask_)   { PSP_GPIO_SET |= mask_; }
static void psp_gpio_clear(unsigned long mask_) { PSP_GPIO_CLEAR |= mask_; }
```
[OBJ] `psp.o` `psp_led_ctrl` `+0x18..0x40`: `lw v0,0(0xbe240008)` /
`or` / `sw`, and `lw v0,0(0xbe24000c)` / `or` / `sw`. This is a genuine
**read-modify-write of the set and clear registers**.

Callers of `psp_led_ctrl` (`psp.c:265-279`, which uses bits 0x40 and 0x80,
`psp.c:35-36`):

| Call site | Context |
|---|---|
| `ms_psp.c:290,292` (`psp_ms_read_sector`: LED on, `pspMsReadSector`, LED off) and `ms_psp.c:312,314` (write) | Process context of the bio submitter, via `psp_ms_make_request` (`ms_psp.c:228`) → `psp_ms_transfer_bio`. Inside `__bio_kmap_atomic` (`ms_psp.c:254`), which on this config is `pagefault_disable()` → `inc_preempt_count()` (`include/linux/highmem.h:49-52`, `include/linux/uaccess.h:16-18`). So the submitter is non-preemptible there, with IRQs enabled. Runs on **every sector read or written**. |
| `ms_psp.c:119` | `psp_ms_init`, initcall, once |
| `psp.c:151` | `psp_debug_except_handler`, `__init`, early-boot exceptions only |

**[DERIVED] with an UNKNOWN core.** The LED-off path writes
`(value read from 0xbe24000c) | 0x40` into the clear register. What a read
of `0xbe24000c` or `0xbe240008` returns is not established anywhere in the
source (§4). If it returns the output latch, and G3 is high at that moment
(only during S13..S20 of some `Syscon_cmd`), then this write would **clear
G3 in the middle of a transaction**. That can happen only if the poll
thread is preempted between S13 and S20 and a Memory Stick transfer runs
before it resumes. `CONFIG_PREEMPT=y` permits this, and `telem` does
Memory Stick I/O continuously (dossier 6.2 [HW]). This interaction is **not
in the dossier's hypothesis list**. It is a code fact whose consequence
hangs on a hardware unknown, and I am routing it to the orchestrator. The
disabled watchdog alternative, `psp.c:394-395`
`psp_gpio_clear( PSP_GPIO_WATCHDOG ); psp_gpio_set( PSP_GPIO_WATCHDOG );`
with `#define PSP_GPIO_WATCHDOG (unsigned long)( 0x8 )` (`psp.c:34`), names
the same bit 3 that `syscon.c` uses as G3.

Other shared registers (sysreg, not SPI or GPIO): `psp_uart_init`
(`ipl_sdk/psp_uart.c:96-104`) does `*(unsigned int *)0xbc100058 |= (0x40<<4);`
and `*(unsigned int *)0xbc100078 |= (0x00010000 << 4);`. These are the same
registers `sceSysregSpiClkEnable` (`sysreg.c:31-34`) and `pspSyscon_init`
(`syscon.c:27` `REG32(0xbc100078) |= (0x1000000<<0);`) modify. It is called
once, right after C4 (`serial_psp.c:353`). They are OR-only RMWs at boot.
Listed for completeness.

Nothing else in `arch/mips`, `drivers` or `include/asm-mips` addresses
`0xbe24xxxx` or `0xbe58xxxx` (grep above). The UART3 tick called from the
timer IRQ (`psp.c:363`, `serial_psp.c:284-293`) touches only
`0xbe500018`.

### 2.3 Order inside the timer interrupt ([OBJ], `psp.o` `plat_irq_dispatch`, relocations resolved)

```
2f0: mtc0 zero,$9              # Count = 0            (psp.c:352)
2f8: mfc0 v0,$11 / 300: mtc0 v0,$11   # rewrite Compare (psp.c:353-354)
304-324: localTick++ ; if (localTick-lastTick < 1250) skip   (psp.c:375-376)
3a4: jal psp_pacify_watchdog   # -> j pspSyscon_tx_noparam (a0=0)  = the Nop
3ac: jal psp_uart3_txrx_tick
3b4: jal irq_enter             # only now
...  irq_desc[66].handle_irq / __do_IRQ  -> timer_interrupt -> do_timer(1) (jiffies++)
350: jal irq_exit
```
Consequences [DERIVED]:
- The Nop runs with CP0 Status IE cleared (`genex.S:163` `CLI`), before
  `irq_enter()`. **`in_irq()`, `in_interrupt()` and `hardirq_count()` are
  all 0 during it.** Code that tests context with these macros will
  classify the watchdog Nop as thread context.
- The Nop runs on the kernel stack of whatever task was interrupted. MIPS
  in this tree has no separate IRQ stack: grepping for `irq_stack` in
  `arch/mips` and `include/asm-mips` finds nothing.
- The Nop cannot be nested or interrupted. The thread cannot run until it
  finishes.

---

## 3. Re-verification of dossier sections

### 3.1 Section 4.1

| Claim | Verdict | Evidence |
|---|---|---|
| "The timeout patch returns `-3`, `-4` or `-5` and prints nothing. `syscon.c:113,154,254`" | **Confirmed** | `:113` `if(spin-- == 0) return -3;`, `:154` `if(spin-- == 0){ REG32(0xbe580004)=4; REG32(0xbe24000c)=0x08; return -4; }`, `:254` `result = -5; break;`. No printk on these paths (§1.3). [OBJ] `li t3,-3`, `-4`, `-5` are present in both `syscon.o` and `vmlinux`. |
| "`read_input()` turns any negative return into `FALSE`, silently. `joypad_psp.c:487-488`" | **Confirmed** | `if ( _pspSysconGetCtrl2( (u32*)&keys, px_, py_ ) < 0 ) return FALSE;` Note: `(void)_pspSysconCtrlAStickPower( 1 );` (`:486`) discards its result entirely. |
| "The thread then sleeps and tries again. `joypad_psp.c:468`" | **Confirmed** | `msleep( 1000 / PSP_JOYPAD_SAMPLE_RATE );` inside `while ( !s_psp_joypad_thread_terminated )` (`:458`). |
| "'ACK never arrives' remains a live hypothesis (H1)" | **Confirmed for the patched kernel** | Nothing in the patched code distinguishes a −4 poll from other FALSE polls. |
| "with `CONFIG_PREEMPT=y`, a kernel thread spinning forever would not freeze the system either, so 'system stays alive' never distinguished the two cases" | **Wrong, or at best incomplete, for the unpatched kernel** | The thread-side half is right: the thread's spin is preemptible. The dossier omits C3. In the unpatched `syscon.c.orig` the waits have no bound (`syscon.c.orig:101-111`, loop at `:105-109` `while( REG32(0xbe58000c) & 4) { dmy = REG32(0xbe580008); }` and `:144-147` `while( (REG32(0xbe240020) & 0x10)==0) { }`). The watchdog Nop executes these waits with interrupts disabled (§2.3). **[DERIVED]** If after onset G4L never again became set for the Nop, or RX-not-empty stuck at 1, the first watchdog tick after onset would spin forever with IRQs off. Timer, scheduler and `telem` would stop. So, **if observations 1 to 5 were on the unpatched kernel** (QA1), the continued liveness shows that after onset every watchdog Nop (a) saw bit 2 of `0xbe58000c` clear within finite time and (b) saw bit 4 of `0xbe240020` set within finite time. That is evidence against "the syscon stops acknowledging entirely" in those runs. It is not evidence against "stops acknowledging the thread's commands" or "acknowledges but returns wrong or absent data", and it does not exclude G4L being stuck at 1. |

### 3.2 Section 4.4

| Claim | Verdict | Evidence |
|---|---|---|
| "`psp_cputimer_handler()` calls `psp_watchdog_tick()` on every timer interrupt. `psp.c:348-359`" | **Confirmed** | `:348` `static void psp_cputimer_handler(void)`, `:359` `psp_watchdog_tick();`. It is called from `plat_irq_dispatch` when IP7 is pending (`:641-643`). |
| "Every `PSP_WATCHDOG_CYCLE * HZ` ticks (5 s) that calls `psp_pacify_watchdog()`, which calls `pspSysconNop()`... `psp.c:41,371-392`" | **Confirmed**, with a precision | `:41` `#define PSP_WATCHDOG_CYCLE 5`. `:375-379` `localTick++; if ( localTick - lastTick >= ( PSP_WATCHDOG_CYCLE * HZ ) ) { lastTick = localTick; psp_pacify_watchdog(); }`. `:392` `pspSysconNop();`. `syscon.h:101` `static inline int pspSysconNop(void){ return pspSyscon_tx_noparam(0x00); }` → `syscon.c:307` → `:273` `return Syscon_cmd(tx_buf,rx_buf);`. **Precision**: the period is 1250 timer interrupts, not a wall-clock 5 s (§6). The first Nop is on the 1250th timer interrupt, when `localTick` becomes 1250. The Nop's return value is discarded (`psp.c:392`). |
| "runs a full `Syscon_cmd` transaction in interrupt context" | **Confirmed, refined** | Hard IRQ, IE off, but before `irq_enter()` (§2.3). |
| "`Syscon_cmd` takes no lock and does not mask interrupts. The original `sceKernelCpuSuspendIntr()` is a comment. `syscon.c:99`" | **Confirmed** | `:99` `// sceKernelCpuSuspendIntr()`. There is no lock, `local_irq_*` or `preempt_*` anywhere in `syscon.c` (whole file). The caller path `joypad_psp.c:474-496` takes nothing either. |
| (omitted by the dossier) | **Addition** | A second Nop call site exists at `psp.c:557` (boot, IRQs off). |

### 3.3 Section 4.5

| Claim | Verdict | Evidence |
|---|---|---|
| "`Syscon_cmd` prefills `rx_buf` with `0xff`. `syscon.c:92-93`" | **Confirmed** | `for(i=0x0f;i>=0;i--) rx_buf[i]=0xff;` (repeated on each retry). |
| "`_pspSysconGetCtrl2` unpacks `rx_buf` regardless of the result. `syscon.c:362-366`" | **Confirmed** | `:363-365` quoted in §1.4. [OBJ] confirms. |
| "The driver inverts the button word. `joypad_psp.c:490`" | **Confirmed** | `*pkeys_ = ~keys;`, then `:492-493` `if ( *pkeys_ & PSP_JOYPAD_KEY_HOLD ) return FALSE;`. |
| Row "all 0x00 → HOLD set → FALSE" | **Confirmed, strengthened** | `PSP_JOYPAD_KEY_HOLD 0x00002000` (`joypad_psp.c:49`). **Addition [DERIVED]**: if every received byte is 0x00, the first byte is 0, so `result = bdata` = 0 (`syscon.c:211`), `if(result>0)` is false (`:226`), the checksum is skipped, `rx_buf[2]`=0 matches no retry case, and the return is **0**. An all-zero frame needs no checksum luck. H2's signature is specifically "return 0, bytes 00". |
| Row "all 0xff (the prefill; happens if the RX FIFO is empty, in which case `result` stays 0 and the checksum is skipped)" | **Confirmed**, with a contrast | This is exit E3. **Contrast [DERIVED]**: 0xff bytes that were actually **received** give `result=0xff>0`, `cnt=rx_buf[1]=0xff`, and a 255-byte out-of-bounds checksum (§1.3), almost surely −2 → FALSE. Only "nothing received" gives the TRUE/no-buttons shape. §5 shows that an interleaved Nop that drains the thread's RXF also produces E3. |
| "Analog reads `0xff,0xff`, which in mouse mode is +16 per poll on both axes (`joypad_psp.c:689`)" | **Line and sign corrected** | `:689` is `case 0xf:`, and `:690` is `return 16;` in `psp_mouse_convert_to_rel` (`switch ( ( v_ >> 4 ) & 0xf )`, `:663`). Both `dx` and `dy` become +16 (`:612-613`), but they are reported as `input_report_rel( s_psp_mouse_dev, REL_X, dx ); input_report_rel( s_psp_mouse_dev, REL_Y, -dy );` (`:651-652`). So the report is REL_X +16, REL_Y −16 per poll. Mouse processing runs only when `s_psp_joypad_keys & PSP_JOYPAD_KEY_MOUSE_MODE` (`:464-465`). This is outside Recon A's scope; Recon B should confirm the screen direction. |

### 3.4 Section 4.6

| Claim | Verdict | Evidence |
|---|---|---|
| "The checksum is only checked when the first received byte is positive. `syscon.c:226`" | **Confirmed** | `if(result>0)`. `result` is 0 or a `u8` (`:211` `result = bdata;`, where `bdata` is `u8`, `:67`), so "positive" means "non-zero". [OBJ] `+0x2b0` `beqzl t3,...` compiles it as `!= 0`. |
| "`BYPASS_ERR_CHECK` is 1, so the SPI status checks are compiled out. `syscon.c:10,168`" | **Confirmed** | `:10` `#define BYPASS_ERR_CHECK 1`. `:168` `#if BYPASS_ERR_CHECK` with an empty branch. The error checks sit in `#else` (`:169-197`). The same holds in `.orig` (`:10`, `:159`). |
| "A short or shifted frame can be accepted as valid." | **Confirmed, made precise** | Accepted without any checksum when the first received byte is 0x00 (E4) or when nothing was received (E3). When the first byte is non-zero, a short frame is checked against 0xff padding and is usually rejected. |
| (additions) | | The out-of-bounds checksum read when `rx_buf[1] >= 16`. Response codes 0x83 and 0x86 accepted as success. Retry decided on `rx_buf[2]` even for unchecked or failed frames (`:249`). |

### 3.5 Section 6.4

| Claim | Verdict | Evidence |
|---|---|---|
| "The timer handler zeroes CP0 Count on every tick (`psp.c:350-355`)" | **Confirmed** | `:351-356` `"mtc0 $0, $9\n" /* Reset the counter */ "mfc0 $2, $11\n" "mtc0 $2, $11\n"`. [OBJ] `plat_irq_dispatch+0x2f0`. See §6 for what it means. |
| "so `jiffies` plus CP0 Count gives sub-jiffy time" | **Confirmed with caveats** | §6. |
| "Registers touched by the transport: SPI `0xbe580000..0xbe580024`, GPIO `0xbe240000..0xbe240024`" | **Confirmed as ranges** | The used and unused offsets are listed in §4. SPI `+0x10` and `+0x1c` are never touched. SPI `+0x18` appears only in compiled-out code. GPIO `+0x1c` is never touched. |
| "`0xbe580008` pops the RX FIFO" | **Confirmed as strongly code-implied** | §4. |
| "Other syscon callers: `pspSysconCtrlHRPower` at serial startup (`serial_psp.c:352`), `pspSysconPowerStandby` at shutdown (`psp.c:218`)" | **Confirmed but incomplete** | Missing: C1 `pspSyscon_init` (`psp.c:135`), C2 boot-time Nop (`psp.c:557`), and the non-syscon GPIO RMW writer `psp_led_ctrl` (§2.2). |
| "`psp_lcd_on()` does not touch the syscon (`psp.c:254`)" | **Confirmed** | `:254-263`: only `if ( console_blanked ) { do_unblank_screen( 0 ); }`. [OBJ] shows no syscon call. |

---

## 4. SPI (`0xbe58xxxx`) and GPIO (`0xbe24xxxx`) registers

**The source proves no read side-effect-free.** The tree contains no
hardware documentation. Every name below comes from the code's own
comments, which are Sony SDK function names left in by the port author.
Anything more is inference from usage. Following the instruction to be
conservative, every register's read side-effect status is **UNKNOWN**
unless the code shows that reading it *has* an effect. The "code usage
evidence" column shows how the existing code already treats reads, so the
designer can weigh the risk. It does not establish safety.

### 4.1 SPI block

| Addr | Code evidence of meaning | Written by | Read by (compiled code) | Read side effects |
|---|---|---|---|---|
| `0xbe580000` | none (init value 0xcf) | `syscon.c:30` `= 0xcf` (init only) | never | UNKNOWN. No code ever reads it. |
| `0xbe580004` | "RX mode ?" (`:136`). Toggled 4 → 6 → 4 per transaction. | `:31` `=0x04` (init), `:136` `=6`, `:154` `=4` (−4 path), `:219` `=4` | never | UNKNOWN. No code ever reads it. |
| `0xbe580008` | **Data FIFO**: writes push TX words (`:132`), reads return RX words (`:207`) | `:132` | `:114` (read and discard inside the drain loop "clear prevouse data ?"), `:207` | **HAS a side effect (pops RXF)**. The drain loop `while( REG32(0xbe58000c) & 4) { ... dmy = REG32(0xbe580008); }` terminates only if each read removes an entry, and the receive loop reads successive words from the same address. Must not be read by an observer. What a read of an **empty** FIFO returns is UNKNOWN. |
| `0xbe58000c` | **Status**. Bit 2 = RX not empty (`:106,111,204`). Bit 0 is checked in compiled-out code as "SYSCON err 2" when 0 (`:183`). | never written | `:106`, `:111` (loop), `:119` (discarded), `:130` (discarded, before each TX push), `:204` (loop) | UNKNOWN. Code usage: it is read many times per transaction, including reads whose value is thrown away (`:119`, `:130`). Why those discarded reads exist is not stated. They could be harmless leftovers or deliberate side-effect reads (for example clearing sticky status). The source does not say which. |
| `0xbe580010` | – | never | never | untouched |
| `0xbe580014` | none | `:32` `= 0` (init only) | never | UNKNOWN |
| `0xbe580018` | "error check ?" bit 0 (`:191`), compiled out | never (the `:194` write is compiled out) | never in compiled code ([OBJ]: no `0xbe580018` access in `Syscon_cmd`) | UNKNOWN |
| `0xbe58001c` | – | never | never | untouched |
| `0xbe580020` | "clear error status ?" (`:121`). Looks like write-to-clear. | `:121` `=3` each attempt. `:194` `=1` is compiled out. | never | UNKNOWN |
| `0xbe580024` | none | `:33` `= 0` (init only) | never | UNKNOWN |

### 4.2 GPIO block

| Addr | Code evidence of meaning | Written by | Read by (compiled code) | Read side effects |
|---|---|---|---|---|
| `0xbe240000` | **Direction**: `:38-41` `// GPIO3 OUT REG32(0xbe240000) \|= 0x08; // GPIO4 IN REG32(0xbe240000) &= ~0x10;` | init RMW `:39,41` | init RMW, and `Syscon_wait` `:321` `dmy ^= REG32(0xbe240000);` used as a busy-delay read, although `Syscon_wait` has no live caller | UNKNOWN. Code usage: the author wrote a delay loop that reads it repeatedly, which suggests they believed reads are benign. Not proof. |
| `0xbe240004` | **Port input read**: `:101-102` `// sceGpioPortRead(); dmy = REG32(0xbe240004);`. A commented debug line reads `&0x18`, i.e. the G3 and G4 levels (`:155`). | never | `:102` every attempt, value discarded | UNKNOWN. Code usage: already read and discarded at the start of every transaction, in both contexts. |
| `0xbe240008` | **Port set**: `:139-140` `// sceGpioPortSet(8) REG32(0xbe240008) = 0x08;`. Also `PSP_GPIO_SET` (`psp.c:32`). | `:140`; `psp.c:401` (RMW) | **`psp.c:401` `PSP_GPIO_SET \|= mask_;`** (LED on, per MS sector) | UNKNOWN. Also UNKNOWN what value a read returns, which decides whether `psp_led_ctrl` disturbs G3 (§2.2). |
| `0xbe24000c` | **Port clear**: `:103-104` `// sceGpioPortClear(8)`. Also `PSP_GPIO_CLEAR` (`psp.c:33`). | `:36` init, `:104`, `:154`, `:222`; `psp.c:406` (RMW) | **`psp.c:406` `PSP_GPIO_CLEAR \|= mask_;`** (LED off, per MS sector) | UNKNOWN, as above. |
| `0xbe240010` | Interrupt mode, part of `// GpioSetIntrMode(4,3)` (`:43-47`) | init RMW `:44` `&= ~0x10` | init RMW | UNKNOWN |
| `0xbe240014` | same | init RMW `:45` `&= ~0x10` | init RMW | UNKNOWN |
| `0xbe240018` | same | init RMW `:46` `\|= 0x10` | init RMW | UNKNOWN |
| `0xbe24001c` | – | never | never | untouched |
| `0xbe240020` | **Interrupt status (latched)**: `:150` `// r2 = sceGpioQueryIntr(4)`, polled for bit 4 | never | `:152` loop, every attempt | UNKNOWN. Code usage is *consistent* with a plain status register: the code clears it separately with a write to `+0x24`. But a read-to-clear register would also satisfy this loop, because the loop exits on the first read that sees the bit. **Whether the bit is edge-latched or level** depends on `GpioSetIntrMode(4,3)` semantics (mode 3), which the source does not give. UNKNOWN. |
| `0xbe240024` | **Interrupt ack**: `:158-159` `// GpioAcquireIntr(4) REG32(0xbe240024) = 0x10;` | `:47` init, `:159` every successful ACK | never | UNKNOWN |

The GPIO4 interrupt does not reach the CPU: `arch_init_irq` writes
`PSP_IRQ_CTRL0 = 0x0; PSP_IRQ_CTRL1 = 0x0;` (`psp.c:594-595`), and
`plat_irq_dispatch` services only IP7 (`psp.c:641`). G4L is observed only
by polling.

### 4.3 What the code implies for a snapshot (facts only)

- Proven harmful to read: `0xbe580008`.
- Read by the running kernel in every transaction already, so the hardware
  is at least exercised this way continuously: `0xbe58000c`, `0xbe240004`,
  `0xbe240020`.
- Read by the running kernel in other paths: `0xbe240008`, `0xbe24000c`
  (MS LED RMW), and `0xbe240000/10/14/18` (init only).
- Never read by any code in the tree: `0xbe580000`, `0xbe580004`,
  `0xbe580014`, `0xbe580018`, `0xbe580020`, `0xbe580024`, `0xbe240024`.
- Nowhere is any of these reads proven free of side effects.

---

## 5. Timer-IRQ Nop interleaved with a thread-context transaction

### 5.1 Model

- T = thread-context `Syscon_cmd` (C5 cmd 0x33, or C6 cmd 0x08; both have
  2 TX words, §1.2 S11).
- N = watchdog Nop (C3, cmd 0x00, 2 TX words). N runs to completion with
  IRQs off (§2.3) and is invisible to T except through hardware.
- N's own sequence is S3..S22 of §1.2: `N-S6` = G3 low, `N-S7/S8` = drain
  RXF, `N-S10` = `+0x20`=3, `N-S11` = push 2 words, `N-S12` = M=6,
  `N-S13` = G3 high, `N-S14` = wait G4L, `N-S15` = ack G4L, `N-S18` =
  read RXF, `N-S19` = M=4, `N-S20` = G3 low.
- N's result is discarded (`psp.c:392`). N does not retry apart from the
  0x80/0x81 rule.
- The syscon chip's behaviour (what it does when G3 drops mid-command,
  when a frame is short, or when it gets two frames) is not in the source.
  Every "syscon does X" below is **UNKNOWN**, and I give the branches.
- Whether the SPI controller transmits on G3 high, on M=6, or continuously
  is **UNKNOWN**. So is whether writing `+0x20` or `+0x04` flushes TXF.

T can be interrupted between any two instructions from S1 to S23 (IRQs
enabled, §2.1 C5/C6). The distinct points, grouped by the hardware state T
has built up:

| Pt | T interrupted between | Hardware state T has created | What N does to it | What N sees | What T sees after resuming |
|---|---|---|---|---|---|
| P0 | S1..S4 (before any register access) or S21..S23 (after S20) | none pending (G3 low, M=4) | a normal, isolated Nop | normal result | its own transaction, unaffected. Benign per the code. |
| P1 | S5..S10 (G3 cleared, drain in progress, before the first TX push) | G3 low. RXF may hold stale data T is draining. | N drains RXF itself (N-S8), then runs a full Nop | a normal Nop, if the drain found only stale data | T's drain loop finds RXF empty and continues. Benign per the code. |
| P2 | inside S11 after pushing k=1 of 2 words | TXF = T word 1 `[cmd,len]` | N-S10, then pushes its 2 words **behind** T's word (if TXF persists), then M=6, G3 high | The syscon receives T-w1, N-w1, N-w2, i.e. a misframed command (UNKNOWN response). N gets that response or none. If `rx_buf[2]`∈{80,81} N retries with a clean frame. Possible outcomes: N −4, N −2, N retried success, or whatever misframe reply the syscon sends. | After N, G3 is low and M=4. T pushes its word 2 alone, sets M=6 and G3 high. The syscon gets a 1-word frame (if TXF was consumed) or residue. Outcomes: −4 (no ACK), −2, retry on 0x80 then recovery, or E3/E4. **Possible TXF residue if it was not fully shifted: UNKNOWN.** |
| P3 | after S11..S12, before S13 (TX loaded, M=6, G3 not yet high) | TXF = T's full frame, M=6 | N pushes 2 more words (TXF = T frame + N frame), M=6, G3 high | The syscon processes the first frame in TXF = **T's command**. N reads **T's reply**. For cmd 0x08 that is a full ctrl frame with a valid checksum, so N returns success with T's data, discarded. N's own words may remain in TXF (UNKNOWN). N sets M=4 and G3 low. | T resumes at S13: raises G3 with **M=4** (N overwrote T's 6). If N's words remain in TXF, the syscon may answer the **Nop**. T then gets the Nop reply, E7 with valid checksum, and `rx_buf[3..]` holds Nop bytes / 0xff. GetCtrl2 returns ≥0 with garbage buttons for one poll. If TXF is empty: −4, or E3 (0, all 0xff: the H3 shape) for one poll. |
| P4 | inside S14 (T waiting for ACK; G3 high, M=6), **before** the syscon ACKs T | syscon processing T's frame | N-S6 **drops G3 in the middle of T's command**. N-S8 drains any partial reply. N sends the Nop, raises G3, waits for G4L. | Branch a: the syscon abandons T and ACKs N, so N gets the Nop reply or T's (UNKNOWN), acks G4L at N-S15, M=4, G3 low. Branch b: no ACK for N, so N −4 after the spin budget with IRQs off (§1.5: ≥~50 ms, so several ticks are lost). | G3 is now low and T never raises it again. T keeps polling G4L. Case a: N already cleared the latch, so T sees G4L only if the syscon later produces **another** ACK edge (UNKNOWN). Then T reads whatever is in RXF (the Nop reply, giving E7 with wrong data, or nothing, giving E3). If no further edge comes: **patched kernel: −4 after the budget. Unpatched kernel: T spins forever (§5.4).** |
| P5a | inside S14, **after** the syscon's ACK for T has latched G4L but before T's next poll of it | G4L=1 (T's ACK), T's reply arriving in RXF | N-S6 G3 low. N-S8 **drains T's reply** from RXF, discarding it. N sends the Nop, raises G3. N-S14 sees the **still-latched T ACK** and exits at once, then N-S15 **clears the latch**. N-S18 reads RXF (probably empty, since the syscon has not answered the Nop yet). M=4, G3 low. | N: E3 (0, all 0xff) or a partial reply. Discarded. | T polls G4L: cleared by N. The situation is the same as P4: it depends on whether the syscon produces a later ACK edge for N's frame after N lowered G3 (UNKNOWN). If it does, T acks, reads the Nop reply: E7 with the Nop payload in `rx_buf`, or E3. If not: −4 (patched) or **infinite spin (unpatched)**. |
| P5b | between S14 exit (G4L seen) and S15 (ack) | G4L=1, reply in RXF | same as P5a, except T has already left the wait loop | same as P5a | T writes the ack (harmless: already cleared) and reads RXF, which N drained. Result: **E3, return 0, all 0xff**: the H3 row (TRUE, no buttons, vol 0xff) for this poll. Or the Nop reply, if it arrives before T's reads (UNKNOWN timing). |
| P6 | inside S18 after T has read j of its reply words (1 ≤ j < n), or between T's `+0x0c` test and its `+0x08` read | part of T's reply still in RXF, G3 high | N-S6 G3 low. N-S8 drains the rest of **T's reply**. The Nop then runs on an idle link. | normal Nop result | T: RXF empty, so the loop breaks. `rx_buf` holds j words plus 0xff. If the first byte ≠ 0: checksum over 0xff padding, giving **−2** (or retry if `rx_buf[2]`∈{80,81}). If T was between its status test and its data read: T pops an **empty** FIFO, and the value returned is UNKNOWN. |
| P7 | between S19 and S20 (reply fully read, M=4, G3 still high) | G3 high, idle | N-S6 drops G3 (T was about to), then a normal Nop | normal | T writes G3 low again (no-op). T's data is intact. Benign. |

Summary of what the code allows the **thread** to observe from one
interleave. Each case needs the syscon's behaviour to fill in the UNKNOWNs.

- **Own valid data**: P0, P1, P7.
- **E3, return 0, all 0xff (the "H3" shape) for one poll**: P3, P4, P5a,
  P5b.
- **Another command's reply accepted as its own (E7, valid checksum)**:
  P3, P4, P5a.
- **−2**: P2, P6.
- **−4**: P2, P3, P4, P5a (patched kernel).
- **Permanent spin**: P4, P5a (unpatched kernel only).
- **N** can receive **T's** ctrl reply (P3). N's outcome is always
  discarded, so N's failures are invisible except as IRQ-off time.

### 5.2 Which points are wide

Everything below is **[DERIVED]**.

- P0 and P1 are microseconds of memory work plus a few MMIO accesses.
- **P4 and P5a cover the whole time T spends waiting for the syscon's
  ACK**. That is the only phase whose length the syscon controls, so it is
  probably the widest window. The ACK latency is UNKNOWN; the source does
  not state it.
- P6 is up to 8 MMIO read pairs.

### 5.3 Other interleavings (thread context, not timer IRQ)

- T is preemptible (`CONFIG_PREEMPT=y`) everywhere between S1 and S23, so
  a transaction can be suspended for an arbitrary time with G3 high and
  M=6 (for example if preempted at P4). **[DERIVED]**
- In steady state no other thread-context syscon caller exists: C4 runs
  once at boot and C7 only at shutdown. C4 can overlap T only if the
  joypad initcall runs before the serial one. The `console=` path is
  UNVERIFIED.
- The MS LED RMW (§2.2) can run while T is preempted. Its effect on G3 is
  UNKNOWN.

### 5.4 Permanence in the unpatched kernel ([DERIVED], code only)

In `syscon.c.orig` the ACK wait is
`while( (REG32(0xbe240020) & 0x10)==0) { }` (`syscon.c.orig:144-147`),
with no bound and no exit. At P4 or P5a, T is left waiting for a G4L edge
after N has lowered G3 (and, at P5a, after N has already consumed and
acked the edge meant for T). If the syscon does not raise GPIO4 again
without a new request, **T never leaves the loop**:

- Input stops permanently.
- The thread is preemptible, so the system stays up.
- Later watchdog Nops raise their own G3, get their own ACK, and complete.
  At N-S15 they clear the latch, but T is still spinning, so T could catch
  a later Nop's ACK edge between that Nop's N-S14 and N-S15. N runs with
  IRQs off, so T cannot run in that window. T also cannot catch an edge
  after N-S15 unless a stray edge occurs. [DERIVED: T effectively never
  sees those edges.]
- No printk anywhere.

This matches the observed "dies at an unpredictable time, never recovers,
empty log" **for the unpatched kernel only**, and it depends on the
UNKNOWN "no ACK edge without a fresh request". In the **patched** kernel
the same interleave gives −4 once, and the next poll starts a fresh
transaction (S6..S13). So by the code alone, this path cannot explain
observation 6 (death in the patched kernel). That needs either state that
carries across calls (§1.3: TXF residue, syscon internal state, the never
re-initialised registers) or a different cause. Stated as analysis only.
It bears on QA1 and QA2.

---

## 6. CP0 Count and sub-jiffy timestamps

Facts:

1. `psp.c:352` `"mtc0 $0, $9\n" /* Reset the counter */` and `:353-354`
   rewrite Compare with its own value. This clears the pending timer
   interrupt; that is MIPS architecture behaviour, and the Allegrex
   specifics are UNVERIFIED. It runs as the **first** action of every
   timer interrupt ([OBJ] `plat_irq_dispatch+0x2f0`).
2. Compare is set once to `PSP_COUNTS_PER_TICK` (`psp.c:611-618`
   `"mtc0 $0, $9\n" "li $2, %0\n" "mtc0 $2, $11\n" : : "i"( PSP_COUNTS_PER_TICK )`),
   and `#define PSP_COUNTS_PER_TICK (unsigned long)( PSP_COUNTS_PER_SEC / HZ )`
   = 220912896/250 = **883651** (`psp.c:38-39`).
3. Nothing else writes Count or Compare. Grep for `mtc0 ... $9/$11`,
   `write_c0_count` and `write_c0_compare` in `arch/mips` finds only
   `psp.c:352-354,612-614`, plus generic `time.c:99,105,121`,
   `smp-mt.c`, `smtc.c`. The generic ack is not installed:
   `arch/mips/kernel/time.c:377-381`. With `mips_hpt_frequency == 0` and
   no `mips_timer_state` (the PSP code sets neither; grep of
   `arch/mips/psp` and `include/asm-mips/psp.h` finds nothing), only
   `clocksource_mips.read` is set, and `:410-412` installs
   `null_timer_ack`. `init_mips_clocksource` returns early (`:341`
   `if (!mips_hpt_frequency || ...) return;`), so the kernel clocksource
   is jiffies-based (`CONFIG_GENERIC_TIME=y`, `.config:60`), and
   `gettimeofday` has no sub-jiffy resolution. This last point is
   [DERIVED] from the 2.6.22 generic-time code path.
4. `jiffies` is incremented later in the same interrupt, in
   `timer_interrupt` → `do_timer(1)` (`time.c:159`), which is reached only
   after `irq_enter` (§2.3).
5. `INITIAL_JIFFIES` is `((unsigned long)(unsigned int) (-300*HZ))`
   (`include/linux/jiffies.h:137`, used at `kernel/timer.c:46`). So
   `jiffies` wraps about 300 s after boot and is not uptime.
   `jiffies - INITIAL_JIFFIES` is.

What this means ([DERIVED]):

- **Confirmed**: within a jiffy, Count measures time since the **entry**
  of the latest timer handler, so (jiffies, Count) is a usable sub-jiffy
  clock. One count ≈ 4.5 ns if `PSP_COUNTS_PER_SEC` is right. That
  constant is "measured by tests" (`psp.c:38`) and is UNVERIFIED here.
- **Caveat 1, in-handler inversion**: during the watchdog Nop, Count has
  already been reset to ≈0 but `jiffies` still holds the old value (fact
  4). A (jiffies, Count) stamp taken inside N reads as (J, small), while
  the T activity it interrupted, a moment earlier, reads as (J, ≈883651).
  **N's records would sort before the T records they interrupted.**
- **Caveat 2, torn reads in thread context**: a tick between a thread's
  read of `jiffies` and its read of Count gives (J, small) when the truth
  is (J+1, small), a one-jiffy backward error, unless the pair is read in
  a retry-consistent way.
- **Caveat 3, tick length is not constant**: Count is zeroed at handler
  entry, not at the Compare match, so any interrupt-entry latency (time
  with IRQs off, including a long N) is thrown away each tick. Each jiffy
  lasts 883651 counts plus that latency. Also, if one handler runs longer
  than one tick (for example an N that times out, ≥~50 ms per §1.5,
  UNVERIFIED), Count passes Compare during the handler. At most one
  further interrupt is latched, so **ticks are lost** and `jiffies` falls
  behind real time. Within a jiffy, Count can exceed 883651 in that case.
- **Caveat 4, watchdog phase**: `localTick` and `jiffies` each advance
  once per handler (facts 1 and 4, `psp.c:375`). The Nop fires in the
  handler where `localTick` becomes 1250·k. During that Nop,
  `jiffies - INITIAL_JIFFIES == 1250·k − 1`, and after the handler it is
  1250·k. This is **UNVERIFIED on hardware** and assumes nothing else
  touches `jiffies`; `do_timer(1)` is the only increment in this path. It
  lets the watchdog boundary be computed from `jiffies`, but "5 s" of
  wall time is 1250 × (tick + latency).

---

## 7. `syscon.c` vs `syscon.c.orig` vs `syscon-timeout.patch`

Checksums: `syscon.c` `ad6cd082bc0bbd14117a929b5875f159`,
`syscon.c.orig` `bea267313950ef82bd09ec58724c39ec`.
`/home/ubuntu/psp/build/syscon-timeout.patch` is 2131 bytes, dated
Sep 22 18:13.

### 7.1 Tree diff (`diff -u syscon.c.orig syscon.c`)

The tree adds exactly:
- `SYSCON_SPIN_MAX 1000000` and `SYSCON_RETRY_MAX 16` (`:12-13`)
- the locals `vu32 spin; int retry_cnt = 0;` (`:71-72`)
- the −3 bound in the drain loop (`:110,113`)
- the −4 bound with teardown in the ACK wait (`:151,154`)
- the retry bound with −5 (`:253-254`), replacing `.orig:244`
  `goto retry;`

Nothing else differs. `BYPASS_ERR_CHECK`, all register accesses and all
other logic are identical.

### 7.2 The patch file is not a valid diff of the tree

- `patch -p1 --dry-run` against a copy of `.orig`: **`Hunk #1 FAILED at 7.
  1 out of 1 hunk FAILED ... Ignoring the trailing garbage.`**
- `git apply --check`: **`error: patch fragment without header at line 18`**.
- Cause: the hunk headers do not match their bodies. Hunk 1 says
  `@@ -7,6 +7,12 @@`, but its body has 8 old and 14 new lines. Hunk 2 says
  `-59`, but `volatile u16 dmy;` is at `.orig:60`. Hunk 4 says `-143`,
  but its first context line is at `.orig:140`.
- `git apply --recount` (which ignores the header counts) applies it
  cleanly, with offsets of +1, +1, −3 and +1.

### 7.3 Patch applied with `--recount` vs the tree: textual differences

1. The patch has a 3-line comment above the defines ("Bounded busy-wait
   budget ... See spin-budget note."). The tree does not. No
   "spin-budget note" exists anywhere under `/home/ubuntu/psp` outside
   `build/linux`, `staging_dir` and `extract` (grep for
   `spin-budget|spin budget|SYSCON_SPIN_MAX` finds only `DOSSIER.md` and
   the patch itself).
2. The −3 check: the patch has
   `if(spin-- == 0)\n return -3; /* RX pre-drain stuck: bus idle, rx_buf already 0xff */`.
   The tree has the one-liner `if(spin-- == 0) return -3;` (`:113`).
3. The −4 check: in the patch the block comes **after** the commented
   `//Kprintf("%02X ",...)` line and has comments ("SYSCON ACK never
   arrived (aged HW)..."). In the tree it is a one-liner **before** that
   line (`:154-155`).
4. The −5 path: the patch uses multi-line form with the comment
   `/* SYSCON stuck reporting BUSY */`. The tree uses the one-liner
   (`:253-254`).

**Semantics are identical.** The only reordering is around a line that is
entirely a comment. Every statement, constant and return value matches.

### 7.4 The built outputs match the patched source ([OBJ])

- `syscon.o` (Sep 22 19:23, newer than `syscon.c` at 18:22) contains
  `1000000` (`lui 0xf`/`ori 0x4240`) and `li t3,-3/-4/-5/-2`.
- `vmlinux` `Syscon_cmd` (at `0x880cee10` per `nm`) is instruction-for-
  instruction identical to `syscon.o`'s. Only the 3 relocated `j` targets
  differ.

Whether `vmlinux-0.22.bin` was produced from this `vmlinux` is Recon C's
question.

---

## 8. Things I could not verify (consolidated)

- Every hardware semantic: register read side effects (§4), FIFO
  behaviour, whether TXF persists or flushes, the G4L edge/level mode, and
  the syscon's response to dropped G3, short frames or double frames (§5).
- The duration of the spin budget (§1.5) and the Count rate (§6).
- Which C4 path runs first (depends on `console=` in `pspboot.conf`).
- Which kernel observations 1 to 5 were made on (QA1), and whether
  `telem`'s loop rate changed at onset (QA2).
- The watchdog phase relation of §6 caveat 4 on real hardware.
