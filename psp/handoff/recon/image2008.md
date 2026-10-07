# Recon D: does the 2008 `2.6.22-uc1` image pacify the watchdog the way this tree does?

Stage 1 support recon. Role: Recon D. Written 2026-09-30.
Scope: one question from dossier 9.5. Is the watchdog path in the 2008
distributed image the same code as in this tree? Also: do that image's
`Syscon_cmd` and joypad thread differ from this tree's in any way that matters?
No kernel code was written. `build/linux` and `work/linux` were only read (see
section 8). Every file I produced is in
`/home/ubuntu/psp/handoff/recon/scratch-2008/`.

Tree paths are relative to `/home/ubuntu/psp/build/linux`. "2008 image" means
`/home/ubuntu/psp/extract/k`. "Tree image" means `build/linux/vmlinux.bin`.
Labels: **[BIN]** means read in the binary image, **[SRC]** means read in the tree
source, **[DERIVED]** means reasoning from those facts, with the reasoning shown.
**UNVERIFIED** means neither the binary nor the source settles it.

---

## 0. Verdicts

| # | Sub-question | Verdict |
|---|---|---|
| V1 | The 2008 image is the gunzipped `vmlinux-0.22.bin`, a raw binary loaded at `0x88000000`, same layout as the tree image | **CONFIRMED** |
| V2 | The watchdog sends syscon command `0x00` through `Syscon_cmd` (`psp_pacify_watchdog` → `pspSyscon_tx_noparam(0)` → `pspSyscon_tx_dword(0,0,2)` → `Syscon_cmd`) | **CONFIRMED**, same as the tree |
| V3 | It is called from the timer-interrupt path, inside `plat_irq_dispatch`, before `irq_enter()` | **CONFIRMED**, same as the tree |
| V4 | Interrupts are disabled when it runs (the `CLI` in `handle_int`, with nothing re-enabling them on the way) | **CONFIRMED** in code, same as the tree. That Status.IE=0 masks the timer on Allegrex is a hardware fact, UNVERIFIED here, but it is identical for both images |
| V5 | It runs every 1250 timer interrupts (`sltiu …,1250`, same `localTick`/`lastTick` variables) | **CONFIRMED**, same as the tree |
| V6 | The 2008 `Syscon_cmd` busy-waits have no bound: the RX drain, the GPIO4 ACK wait, and the 0x80/0x81 retry | **CONFIRMED**. **This is where it differs from the tree**, whose waits are bounded (−3/−4/−5) |
| V7 | The 2008 `Syscon_cmd` is exactly the unpatched `syscon.c.orig` | **CONFIRMED**, within compiler scheduling: 392 of 396 words match; the other 4 are two independent increments in swapped order |
| V8 | The 2008 joypad driver matches this tree's (poll period `msleep(50)`, HOLD test, AStickPower + GetCtrl2, dedupe, mouse mode, queues, thread creation) | **CONFIRMED**. `joypad_psp.o` `.text`, `.init.text`, `.data` and `.rodata` are identical once relocations are masked, and every external call resolves to an identical function |
| V9 | Nothing else on the watchdog, poll or timing path differs (`psp.o`, `genex.o`, `irq.o`, `time.o` (arch), `timer.o` incl. `msleep`, `msecs_to_jiffies`, `__do_softirq`, `sched.o`, `semaphore.o`, `input.o`, `mousedev.o`, `serial_psp.o`, `ms_psp.o`) | **CONFIRMED** for the objects listed. 101 functions in generic kernel code **do** differ (section 6). Their relevance is **UNVERIFIED** |
| V10 | `extract/k` is byte-for-byte the kernel the operator booted for observations 1 to 5 | **UNVERIFIED**. The banner is `2.6.22-uc1 … #1377`. Nothing on this machine ties it to the Memory Stick copy |

Short answer: **yes, with one difference.** The 2008 image pacifies the
watchdog with an identical call chain: command 0x00, from the timer
interrupt, IRQs off, every 1250 ticks. Its `Syscon_cmd` is the unpatched one,
so all three waits have no bound, and that includes the one the watchdog runs
with IRQs off. This is the premise dossier 9.5 needs. Its joypad thread matches
this tree's instruction for instruction.

---

## 1. Method

1. **Image identity.** `zcat extract/vmlinux-0.22.bin | cmp - extract/k`
   reports no difference. sha256: `k` = `52dbebe5…11ed43`, `vmlinux-0.22.bin` =
   `628dddfe…82d2`. The banner is at file offset `0x11c000`:
   `Linux version 2.6.22-uc1 (root@rhl9.JacksonMo) (gcc version 4.2.1) #1377 PREEMPT Mon Feb 18 17:41:19 HKT 2008`.
   The tree image has its banner at the same offset (`0x11c000`).
2. **Load address.** The first word of both images is `0a04f400`, which is
   `j 0x8813d000`. `0x8813d000` is `kernel_entry` in `System.map:5189`. The load
   address is `0x88000000` from `arch/mips/Makefile:598`
   `load-$(CONFIG_SONY_PSP) += ( 0xffffffff08000000 + CONFIG_PSP_ADDRESS_BASE )`
   and `.config:51` `CONFIG_PSP_ADDRESS_BASE=0x80000000`. **File offset =
   VA − 0x88000000** for both images.
3. **Configuration.** `build/kernel-0.22.config` (header
   `# Linux kernel version: 2.6.22-uc1`) differs from `build/linux/.config`
   only in three path strings (`INITRAMFS_SOURCE`, `PSP_SDK_PATH`,
   `PSP_TOOLCHAIN_PATH`). This is from `diff` of the sorted non-comment lines.
   `CONFIG_HZ=250` and `CONFIG_PREEMPT=y` hold in both (`kernel-0.22.config:132,135`).
   That this config file is the one the 2008 image was built with is **UNVERIFIED**,
   but the binary agrees with it: `1250 = 5*HZ` in section 3, and `msleep(50)`
   and `msecs_to_jiffies` in section 5 are identical.
4. **Disassembly.** Both raw images went through
   `mipsel-linux-uclibc-objdump -D -b binary -m mips:isa32 -EL --adjust-vma=0x88000000`
   in `psp-build:bullseye`. The output is `scratch-2008/k.dis` and
   `scratch-2008/tree.bin.dis`. The tree's `vmlinux` was also disassembled with
   symbols (`tree.vmlinux.dis`).
5. **Object matching (the main evidence).** For each tree object section I
   took the raw bytes (`objcopy -O binary -j <sec>`) and its relocation list
   (`objdump -r`). `scratch-2008/cmpobj.py` then searched both images for
   the section. The comparison is word by word, and in words that carry a
   relocation only the bits the linker cannot change are compared:
   opcode bits 31..26 for `R_MIPS_26`, bits 31..16 for `HI16`/`LO16`, and
   nothing for `R_MIPS_32`. `scratch-2008/resolve.py` then resolved every
   `R_MIPS_26` target in both images. It checks that local jumps land at the
   same offset inside the function, and that every external callee has the
   same code (24 words, immediates and jump fields masked) in both images.
   This handles the fact that the two images put everything at different
   addresses.
6. **Unpatched reference.** I copied `arch/mips/psp/ipl_sdk/syscon.c.orig` to
   the scratch directory and compiled it with the exact flags from
   `arch/mips/psp/ipl_sdk/.syscon.o.cmd:1` (tree mounted read-only). The
   result is `scratch-2008/syscon_orig.o`.
7. **Whole-image sweep.** `scanall.py` (per section) and `scanfuncs.py` (per
   function, from `objdump -t`) apply the same comparison to all 357 tree
   objects (section 6).

---

## 2. V2: the watchdog issues command 0x00 through `Syscon_cmd` [BIN]

Tree source for reference [SRC]: `psp.c:383` `void psp_pacify_watchdog(void)`,
`:392` `pspSysconNop();`; `include/asm-mips/ipl_sdk/syscon.h:101`
`static inline int pspSysconNop(void){ return pspSyscon_tx_noparam(0x00); }`;
`syscon.c.orig:295-297` `return pspSyscon_tx_dword(0,cmd,2);`;
`syscon.c.orig:253-263` builds `tx_buf` and `return Syscon_cmd(tx_buf,rx_buf);`.

In the 2008 image, `psp.o .text` is at file offset `0xce1e0` (tree: `0xce550`).
Its 316 words match with 0 differences. `psp_pacify_watchdog` is at `0x880ce464`:

```
880ce464: 3c02881b  lui   v0,0x881b
880ce468: 8c432838  lw    v1,10296(v0)      # s_psp_shutdown @ 0x881b2838 (same address in the tree)
880ce46c: 10600003  beqz  v1,0x880ce47c
880ce470: 3c048813  lui   a0,0x8813
880ce474: 0a0088e7  j     0x8802239c         # printk("Stop pacifying watchdog\n"), string at file 0x12c558
880ce478: 2484c558  addiu a0,a0,-15016
880ce47c: 0a033ba6  j     0x880cee98         # pspSyscon_tx_noparam
880ce480: 00002021  move  a0,zero            # cmd = 0x00
```
Tree equivalent: `0x880ce7d4` (`tree.vmlinux.dis`), identical except the jump targets.

`pspSyscon_tx_noparam` in 2008 is at `0x880cee98`:
```
880cee98: 308400ff  andi a0,a0,0xff
880cee9c: 00802821  move a1,a0               # cmd
880ceea0: 24060002  li   a2,2                # tx_len 2
880ceea4: 0a033b53  j    0x880ced4c          # pspSyscon_tx_dword
880ceea8: 00002021  move a0,zero             # param 0
```
`pspSyscon_tx_dword` (`0x880ced4c`) calls `Syscon_cmd` at `0x880ceaa0`.
The relocations in `syscon_orig.o` at `+0x2e0` and `+0x314` resolve to
`0x880ceaa0` in the 2008 image (`resolve.py` output, section 1 item 5).

---

## 3. V3, V5: called from the timer interrupt, every 1250 ticks, before `irq_enter` [BIN]

Tree source [SRC]: `psp.c:348` `psp_cputimer_handler`, `:352`
`"mtc0 $0, $9\n"`, `:359` `psp_watchdog_tick();`, `:375-378`
`localTick++; if ( localTick - lastTick >= ( PSP_WATCHDOG_CYCLE * HZ ) ) { lastTick = localTick;`,
`:41` `#define PSP_WATCHDOG_CYCLE 5`, `:367` `do_IRQ( PSP_PLAT_IRQ_CPUTIMER );`.

In the 2008 image `plat_irq_dispatch` is at `0x880ce4a8` (tree: `0x880ce818`).
Both handlers inline into it.
```
880ce4b4: 40026000  mfc0  v0,c0_status
880ce4b8: 40036800  mfc0  v1,c0_cause
880ce4c4: 30648000  andi  a0,v1,0x8000       # IP7 (timer) pending?
880ce4d0: 40804800  mtc0  zero,c0_count      # psp.c:352 Count = 0
880ce4d8: 40025800  mfc0  v0,c0_compare
880ce4e0: 40825800  mtc0  v0,c0_compare
880ce4e4: 3c04881b  lui   a0,0x881b
880ce4e8: 8c832834  lw    v1,10292(a0)       # localTick @ 0x881b2834 (same address in the tree)
880ce4ec: 3c05881b  lui   a1,0x881b
880ce4f0: 8ca22830  lw    v0,10288(a1)       # lastTick  @ 0x881b2830 (same address in the tree)
880ce4f4: 24630001  addiu v1,v1,1            # localTick++
880ce4f8: 00621023  subu  v0,v1,v0
880ce4fc: 2c4204e2  sltiu v0,v0,1250         # 5*HZ = 1250
880ce500: 10400020  beqz  v0,0x880ce584      # >= 1250 -> pacify
880ce504: ac832834  sw    v1,10292(a0)
...
880ce584: 0e033919  jal   0x880ce464         # psp_pacify_watchdog   <-- the Nop
880ce588: aca32830  sw    v1,10288(a1)       # lastTick = localTick (delay slot)
880ce58c: 0e04075e  jal   0x88101d78         # psp_uart3_txrx_tick
880ce594: 0e00a621  jal   0x88029884         # irq_enter             <-- only after the Nop
880ce5ac: 0e011912  jal   0x88046448         # __do_IRQ(66) (a0=66 in delay slot)
```
The tree has the same sequence at `0x880ce840..0x880ce91c`
(`mtc0 zero,$9` at `0x880ce840`, `sltiu v0,v0,1250` at `0x880ce86c`,
`jal psp_pacify_watchdog` at `0x880ce8f4`, `jal irq_enter` at `0x880ce904`).
The immediate 1250 (`2c4204e2`) appears in each image exactly once as a
`sltiu`: 2008 at `0x880ce4fc`, tree at `0x880ce86c`. `grep ',1250$'` over both
disassemblies finds only these, plus two unrelated `addiu`/`li` in generic code.

`resolve.py` maps the callees `irq_enter`, `irq_exit`, `__do_IRQ`,
`psp_uart3_txrx_tick` and `pspSyscon_tx_noparam` to code that is identical in
both images.

Boot-time Nop: `psp.o .init.text` (252 words, `prom_init` and others) matches
in 2008 at file `0x1531c4` with 0 differences. Its local call at `+0x2fc`
resolves to `0x880ce464` (2008 `psp_pacify_watchdog`), just as the tree's
resolves to `0x880ce7d4`. So the 2008 image also sends the boot Nop from
`prom_init` (tree: `psp.c:557`).

---

## 4. V4: interrupts are off during the Nop [BIN]

`arch/mips/kernel/genex.o .text` (1456 words, containing `handle_int`) is
identical in 2008 at the same file offset `0x1240` (0 differences). Tree source
[SRC]: `genex.S:163-169` `SAVE_ALL` / `CLI` / … / `j plat_irq_dispatch`, and
`include/asm-mips/stackframe.h:383-389` defines `CLI` as
`mfc0 t0,CP0_STATUS; li t1,ST0_CU0|STATMASK; or t0,t1; xori t0,STATMASK; mtc0 t0,CP0_STATUS`.
In the 2008 image:
```
8800130c: 40086000  mfc0  t0,c0_status
88001314: 3529001f  ori   t1,t1,0x1f
8800131c: 3908001f  xori  t0,t0,0x1f         # clears IE (bit 0), EXL, ERL, KSU
88001320: 40886000  mtc0  t0,c0_status
8800133c: 0a03392a  j     0x880ce4a8         # plat_irq_dispatch
```
Nothing between that point and the Nop writes Status. The 2008
`plat_irq_dispatch` (`0x880ce4a8..0x880ce5b8`) contains no
`mtc0 …,c0_status`, and I counted 0. `psp_pacify_watchdog`,
`pspSyscon_tx_noparam`, `pspSyscon_tx_dword` and `Syscon_cmd` contain no
`c0_` access at all (`grep -c 'c0_' k_Syscon_cmd.dis` = 0). So the Nop runs
with Status.IE = 0, as in the tree (`recon/syscon.md` §2.3).
**UNVERIFIED (hardware):** that IE=0 blocks the Allegrex timer interrupt. It is
standard MIPS behaviour, and it is the same for both images.

---

## 5. V6, V7: the 2008 `Syscon_cmd` is the unpatched one, with unbounded waits [BIN]

### 5.1 Identity with `syscon.c.orig`

`syscon_orig.o` (the tree's `syscon.c.orig` compiled with the tree's flags) has
`Syscon_cmd` at `+0x000` (size `0x2ac`), `pspSyscon_tx_dword` `+0x2ac`,
`pspSyscon_rx_dword` `+0x2f4`, `pspSyscon_tx_noparam` `+0x3f8`, `Syscon_wait`
`+0x40c`, `pspSysconCtrlLED` `+0x47c`, `_pspSysconGetCtrl2` `+0x4cc`,
`pspSyscon_init` `+0x55c`.

In the 2008 image the whole 396-word section is found at file offset
`0xceaa0`, VA `0x880ceaa0` (`cmpobj.out`). All 12 relocations resolve
consistently: the three local jumps land at the same function offsets, and
`Syscon_cmd`, `pspSyscon_tx_dword`, `sceSysregSpiClkSelect` and
`sceSysregSpiClkEnable` resolve to identical code. **392 of 396 words are
identical.** The 4 that differ:

| Offset in `.o` | `syscon_orig.o` | 2008 image |
|---|---|---|
| `+0x1cc`, `+0x1d0` | `addiu a2,a2,2` ; `addiu a3,a3,2` | `addiu a3,a3,2` ; `addiu a2,a2,2` |
| `+0x250`, `+0x258` (a `j` and its delay slot) | `addiu a2,a2,2` ; `j` ; `addiu a3,a3,2` | `addiu a3,a3,2` ; `j` ; `addiu a2,a2,2` |

These are `ptr+=2` (`a2`) and `i+=2` (`a3`) in the RX loop
(`syscon.c.orig`, loop `for(i=0;i<0x10;i+=2)`). The two instructions use
separate registers and both finish before either register is read again (the
next use is `slti t0,a3,16` at `+0x1d8`). **[DERIVED] The behaviour is
identical.** Why the order differs is UNVERIFIED: a different build of gcc
4.2.1 or a trivially different source order would explain it.

The tree's patched `syscon.o` (444 words) is **not** present in the 2008
image (`cmpobj.out`: no candidate). `Syscon_cmd` in 2008 is `0x2ac` bytes; the
tree's is `0x368` (`System.map:3264-3265`). The spin constant and the timeout
returns are absent from the 2008 function. Its only negative immediates are
`li t2,-2` at `0x880ced0c` and `0x880ced48` (the checksum error). The tree's
has `lui v0,0xf`/`ori s1,v0,0x4240` (1,000,000) at `0x880cee20/58`, `li t3,-3`
at `0x880cef34/58`, `li t3,-4` at `0x880cf01c` and `li t3,-5` at `0x880cf13c`.

### 5.2 The three unbounded loops in 2008 (`k_Syscon_cmd.dis`)

Register setup (`0x880ceaa4..0x880ceb10`): `t1 = 0xbe58000c`,
`t3 = 0xbe580008`, `s1 = 0xbe580020`, `s3 = s8 = 0xbe580004`,
`s0 = 0xbe240004`, `t9 = 0xbe24000c`, `s5 = 0xbe240008`, `t5 = 0xbe240020`,
`s6 = 0xbe240024`.

**(a) RX drain**, `syscon.c.orig:101-111` `while( REG32(0xbe58000c) & 4) { dmy = REG32(0xbe580008); }`:
```
880ceb88: 8d220000  lw   v0,0(t1)       # 0xbe58000c
880ceb90: 1040000c  beqz v0,0x880cebc4  # (after andi 4) skip if RX empty
880ceba8: 8d620000  lw   v0,0(t3)       # pop 0xbe580008
880cebb0: a7a20000  sh   v0,0(sp)       # dmy
880cebb4: 8d230000  lw   v1,0(t1)       # 0xbe58000c
880cebb8: 30630004  andi v1,v1,0x4
880cebbc: 1460fffa  bnez v1,0x880ceba8  # no counter: unbounded
```
**(b) GPIO4 ACK wait**, `syscon.c.orig:144-147` `while( (REG32(0xbe240020) & 0x10)==0) { }`:
```
880cec14: ae740000  sw   s4,0(s3)       # 0xbe580004 = 6
880cec18: aeae0000  sw   t6,0(s5)       # 0xbe240008 = 8 (G3 high)
880cec1c: 8da20000  lw   v0,0(t5)       # 0xbe240020
880cec20: 30420010  andi v0,v0,0x10
880cec24: 1040fffd  beqz v0,0x880cec1c  # no counter: unbounded
880cec2c: aed70000  sw   s7,0(s6)       # 0xbe240024 = 0x10 (ack)
```
**(c) BUSY retry**, `syscon.c.orig:240-245` `case 0x80: case 0x81: goto retry;`:
```
880cec9c: 93020000  lbu  v0,0(t8)       # rx_buf[2]
880ceca0: 24030001  li   v1,1
880ceca4: 2442ff80  addiu v0,v0,-128
880ceca8: 0062102b  sltu v0,v1,v0       # (rx_buf[2]-0x80) > 1 ?
880cecac: 5040ff9a  beqzl v0,0x880ceb18 # 0x80/0x81 -> retry: no counter
```
Compare the tree [SRC]: `syscon.c:110-113` (`spin = SYSCON_SPIN_MAX; … if(spin-- == 0) return -3;`),
`:151-154` (`… return -4;`), `:253` (`if(++retry_cnt < SYSCON_RETRY_MAX) goto retry;`),
with `:12-13` `SYSCON_SPIN_MAX 1000000`, `SYSCON_RETRY_MAX 16`.

Every other part of the 2008 `Syscon_cmd` matches the tree logic that
`recon/syscon.md` §1.2 describes: the 0xff prefill, G3 low, `+0x20`=3, the
TX push, M=6, G3 high, the ack write, up to 8 RX words, M=4, G3 low, the
checksum only when the first byte is non-zero, and `rx_buf[1]` used without a
bound. `BYPASS_ERR_CHECK` is also in effect: no access to `0xbe580018`. The
only difference is the missing bounds.

`_pspSysconGetCtrl2` (2008 `0x880cef6c`) and `pspSyscon_tx_dword` (2008
`0x880ced4c`) are part of the identical 392 words, so they are the same as
the tree's (`syscon.c.orig:345-357`, tree `syscon.c:355-367`): the unpack
happens whatever the result.

---

## 6. V8, V9: joypad thread and the rest of the image [BIN]

### 6.1 `joypad_psp.o`

| Section | Words | Tree file offset | 2008 file offset | Differences |
|---|---|---|---|---|
| `.text` | 1092 (193 relocated) | `0x114110` | `0x113e40` | 0 |
| `.init.text` (`psp_joypad_init`, `kernel_thread(…, CLONE_FS\|CLONE_SIGHAND)`) | 123 (60 relocated) | `0x155e58` | `0x155e90` | 0 |
| `.data` (fops, `list_sem`, wait queue) | 56 | `0x13cba0` | `0x13cba0` | 0 |
| `.rodata` (the jump table of `psp_mouse_convert_to_rel`, 16 entries relocated against `.text`) | 16 | `0x124ec0` | `0x124ec0` | 0 (every entry equals the section base plus the same offset) |
| `.rodata.str1.4` (strings) | 384 B | `0x12e4ac` | `0x12e520` | 0 (exact bytes) |

`resolve.py` (`res_joypad.txt`): all 39 local jumps are consistent. All 34
external calls resolve to code identical in both images. They include
`msleep` (2008 `0x8802e15c`), `pspSyscon_tx_dword`, `_pspSysconGetCtrl2`,
`psp_lcd_on`, `__down_interruptible`, `__up`, `__wake_up`, `input_event`,
`kmem_cache_alloc`, `kfree`, `schedule`, `prepare_to_wait` and `finish_wait`.
The `.bss` addresses match too: the 2008 code loads `s_psp_joypad_keys` from
`0x881b6200` and `s_psp_joypad_thread_terminated` from `0x881b6208`, the
tree's `System.map:6323,6325` addresses.

The 2008 poll loop, `psp_joypad_thread` inlined with `read_input`
(`joypad_psp.c:458-469,486-495`):
```
8811480c: 24040001  li   a0,1              # param 1
88114810: 24050033  li   a1,51             # cmd 0x33 AStickPower
88114814: 0e033b53  jal  0x880ced4c        # pspSyscon_tx_dword; result ignored
88114818: 24060003  li   a2,3
88114824: 0e033bdb  jal  0x880cef6c        # _pspSysconGetCtrl2
8811482c: 0440fff1  bltz v0,0x881147f4     # < 0 -> FALSE -> sleep (silent)
88114834: 0002a027  nor  s4,zero,v0        # keys = ~raw
88114838: 32832000  andi v1,s4,0x2000      # PSP_JOYPAD_KEY_HOLD
8811483c: 1460ffed  bnez v1,0x881147f4     # HOLD -> FALSE -> sleep
88114868: 1092ffdc  beq  a0,s2,0x881147dc  # dedupe (lastKeys == keys)
881147e4: 3c030080  lui  v1,0x80           # PSP_JOYPAD_KEY_MOUSE_MODE
881147f4: 0e00b857  jal  0x8802e15c        # msleep
881147f8: 24040032  li   a0,50             # 1000/PSP_JOYPAD_SAMPLE_RATE
```
**[DERIVED]** The poll period (14 jiffies minimum, `recon/input.md` §4), the
HOLD handling, the dropped AStickPower result, the silent `< 0` exit and the
driver's lock order (H9) are the same in the 2008 image. `msleep` (14 words),
`msecs_to_jiffies` (7 words) and all of `kernel/timer.o` `.text` (932 words),
`.init.text` and `.sched.text` are identical. There is no retry logic in the
driver in either image. The only retry is the 0x80/0x81 one inside
`Syscon_cmd`, bounded in the tree and unbounded in 2008.

### 6.2 Other objects on the path, all identical (0 differences)

`scanall.py` / explicit check: `arch/mips/kernel/{genex,entry,irq,time,semaphore,head,process}.o`,
`kernel/{timer,sched,signal,printk,kthread}.o`, `kernel/irq/{handle,chip,manage}.o`,
`kernel/time/{timekeeping,clocksource}.o`, `drivers/input/{input,mousedev}.o`,
`drivers/serial/serial_psp.o`, `drivers/block/ms_psp.o`,
`drivers/char/{vt,tty_io,n_tty}.o`, `arch/mips/psp/ipl_sdk/sysreg.o`, plus the
`.sched.text` of `sched.o`, `timer.o`, `semaphore.o` and `mutex.o`. In
`kernel/softirq.o`, the functions `__do_softirq`, `do_softirq`, `irq_enter`,
`irq_exit`, `raise_softirq`, `raise_softirq_irqoff` and `local_bh_enable` are
identical.

### 6.3 What differs in generic code (not analysed)

Of 5,074 tree functions compared, 4,108 are found exactly in the 2008 image.
Of the rest, 852 are too small to locate (fewer than three consecutive
unrelocated words) and 13 are not found cleanly in the tree image itself. Both
counts are limits of the method, not evidence of a difference. **101
functions** are found exactly in the tree image but differ, or are missing, in
2008 (`scratch-2008/funcs_differ.txt`). Grouped:

- **`Syscon_cmd`**: the timeout patch (section 5).
- **Direct I/O removed or changed in 2008**: `blkdev_direct_IO`,
  `blkdev_get_blocks`, `blkdev_get_block`, `max_block` and `fat_direct_IO`
  are not found; `generic_file_direct_IO`, `generic_file_direct_write` and
  `generic_file_aio_read` are not found; many `mm/filemap.c` functions differ
  by 1 to 4 words.
- **Process and memory management**: `copy_process` (475 words differ),
  `copy_fs_struct`, `dup_fd`, `mmput`, `do_wait` (18), `out_of_memory` (99),
  `kswapd`, `isolate_lru_pages`, `kmem_cache_create`.
- **`/proc`**: many `fs/proc/base.c` functions differ by 1 to 3 words,
  `oom_adjust_write` by 123 and `proc_pid_status` by 12.
- **Other**: `ksoftirqd` (50 words), `tasklet_action`, `tasklet_hi_action`,
  `tasklet_kill`, `sys_stime`, `do_sys_settimeofday`, `rd_load_image`,
  `vfat_add_entry` (48), `fat_get_block`, `fat_alloc_clusters`, `pipe_read`,
  `vcs_write` (2), `fbcon_getxy`, `fbcon_redraw_move`,
  `fb_pad_aligned_buffer`, `mem_init`, `loop_init`, `blk_recount_segments`.

**[DERIVED]** This fits the 2008 image being built from a genuine uClinux
`-uc1` tree, where this tree is vanilla 2.6.22 + `kernel-0.22.lf.patch` + fixes
(`recon/build.md` §5.1). The many 1-word differences look like
structure-offset changes, but that is UNVERIFIED. **None of these functions is
on the syscon, watchdog or joypad poll path.** Whether any of them matters to
the failure is **UNVERIFIED**, and so is the Memory Stick write path used by
`telem`. Candidates the designer may want listed: `ksoftirqd` (softirq
servicing under load), `vcs_write` (the vcs driver used by `psposk2`/`pspmd`;
their injection path is `ioctl`, not `write`), and the vfat/filemap changes
(the Memory Stick I/O path, relevant to H10).

---

## 7. Consequences for dossier 9.5 (derived, for the designer)

1. **The premise of 9.5 holds, and it now rests on the binary.** In the
   image used for observations 1 to 5, every 1250th timer interrupt runs a
   command-0x00 transaction with IRQs off and no bound on (a) draining RX,
   (b) waiting for the GPIO4 ACK, or (c) retrying on 0x80/0x81 (sections 3
   to 5). The kernel, the timer and `telem` stayed alive for minutes after
   input died (dossier 3.1). So after onset, every watchdog Nop in those runs
   saw RX-not-empty clear, saw `0xbe240020` bit 4 set, and got a
   `rx_buf[2]` other than 0x80/0x81 within finite time. This assumes V10 (the
   image booted is this file) and V4's hardware assumption.
2. **An addition to 9.5: H5 in its "permanent BUSY" form is disfavored on the
   2008 image in the same way as pure H1**, because the 2008 retry loop has no
   bound and the watchdog runs it with IRQs off. What survives is a syscon
   that answers 0x80/0x81 **only** to commands 0x08/0x33, or only when it is
   interleaved with the thread.
3. **The thread side of the 2008 image had no bounds either.** A thread-context
   `Syscon_cmd` that never saw its ACK, or got BUSY forever, would spin
   forever in the poll thread, preemptibly. That silently stops all input while
   the watchdog, which raises its own G3, keeps completing. This is the
   `recon/syscon.md` §5.4 mechanism, and the binary confirms it is available in
   the image that produced observations 1 to 5. In the tree's patched kernel
   the same situation gives −4 or −5 every poll (observation 6). So "pure H1
   disfavored" means "the syscon still answered the **watchdog's** commands",
   not "the thread's own transaction completed". The per-context split in
   dossier 9.5 stands.
4. **The joypad driver is not a variable between the two kernels.** Any
   difference in behaviour between the 2008 image and this tree on the input
   path must come from `Syscon_cmd`'s bounds (section 5) or from the generic
   code in 6.3. The driver, the watchdog code, the timer interrupt path,
   `msleep`, the input core and mousedev are all identical.

---

## 8. UNVERIFIED items and scope

- **V10**: that `extract/k` (`#1377`, Feb 18 2008) is byte-identical to the
  kernel on the operator's Memory Stick. The operator could confirm it by
  checksum of the file in the baseline folder, or by `/proc/version` in a saved
  `kmsg.txt` or boot log.
- Whether `build/kernel-0.22.config` is the config that built `k`. The binary
  agrees with it on HZ and on the code that depends on HZ.
- That Status.IE=0 masks the timer interrupt on Allegrex (hardware). It is the
  same for both images.
- Why the two increments in the RX loop are ordered differently (5.1). The
  behaviour is identical.
- The relevance of the 101 differing generic functions (6.3), and whatever
  sits in the functions too small for the sweep to locate. The PSP path objects
  were compared whole (per section, not per function), so this gap does not
  affect them.
- I did not compare `.data`/`.rodata` of objects other than `joypad_psp.o` and
  `psp.o`'s strings, and I did not check that every `HI16/LO16` pair resolves to
  the matching variable. For the path variables (`localTick`, `lastTick`,
  `s_psp_shutdown`, `s_psp_joypad_keys`, `s_psp_joypad_thread_terminated`) I
  checked the addresses by hand: the same VAs in both images.

**Original tree untouched:** after the work,
`cd build/linux && sha256sum -c --quiet /home/ubuntu/psp/handoff/gates/baseline-tree.sha256`
printed nothing, exit 0; `find . -newermt '2026-09-28 00:00' | wc -l` = 0;
`git -C work/linux status --porcelain` is empty. Every container run mounted
`/home/ubuntu/psp` read-only, with `scratch-2008/` as the only writable mount.
The one exception is the first disassembly run, which used the task's own
command line with a read-write mount of `/home/ubuntu/psp`. It wrote only the
three `.dis` files in `scratch-2008/`, and the checksum above confirms the tree
did not change.

## 9. Files in `scratch-2008/`

| File | Content |
|---|---|
| `k.dis`, `tree.bin.dis` | Raw-binary disassembly of the 2008 image and the tree image, VA-adjusted to `0x88000000` |
| `tree.vmlinux.dis` | `objdump -d` of the tree's `vmlinux`, with symbols |
| `k_Syscon_cmd.dis` | 2008 `Syscon_cmd`, `0x880ceaa0..0x880ced48` |
| `syscon_orig.c`, `syscon_orig.o`, `syscon_orig.o.dis` | The tree's `syscon.c.orig`, compiled with the tree's flags |
| `syscon_tree.*`, `joypad_tree.*`, `psp_tree.*` | Section bytes, relocations, symbols and disassembly of the tree objects |
| `cmpobj.py`, `cmpobj.out` | Relocation-masked section locator and comparator, and its results |
| `resolve.py`, `res_joypad.txt` | Call-target resolution and callee-body comparison |
| `scanall.py`, `scanall.out` | Every tree object section against both images |
| `scanfuncs.py`, `scanfuncs.out`, `funcs_differ.txt` | Per-function sweep; the 101 functions that differ |
| `objs/` | Extracted `.text`/`.init.text`/`.sched.text` bytes, relocations and symbol tables of the 357 tree objects |
