# Recon B: input path above the syscon, and the userland channels

Stage 0 (Recon), role Recon B. Written 2026-09-27.
Scope: `drivers/input/joypad_psp.c`, signals on its kernel thread, the input
core and mousedev path, the real poll period, `psposk2` and `pspmd`, `telem`,
and the `/proc` facilities in this config.

This report gives facts only. It proposes no instrumentation design and no fix.

## Conventions

- Kernel paths are relative to `/home/ubuntu/psp/build/linux` unless they
  start with `/`. `file:line` refers to that tree as it stood on 2026-09-27.
- **UNVERIFIED** marks anything I could not confirm from source or binary.
- Userland binaries are bFLT v4, flag `Has-PIC-GOT`. Disassembly addresses
  below are **file offsets into the bFLT file**. The linked address is
  `0x400000 + offset - 0x40`, and `$gp` points at the start of the GOT
  (the first word of the data segment). The method and the scripts are listed
  in section 8.
- The original tree was only read. I ran nothing inside it and wrote nothing
  to it. Every file I produced is under
  `/home/ubuntu/psp/handoff/recon/scratch-input/` (see section 8).

---

## 0. Summary of findings that change the dossier

| # | Finding | Dossier section affected |
|---|---|---|
| B1 | **4.7 is wrong on one point.** A pending signal does *not* make "every `down_interruptible` fail from then on". On MIPS in this tree, the fast path takes the semaphore without looking at signals. Only a call that would have to sleep (a contended semaphore) returns `-EINTR`. A pending signal would make joypad delivery fail intermittently, not stop it. | 4.7 |
| B2 | **4.3's rate is slightly high.** `msleep(50)` is **14 jiffies** (`msecs_to_jiffies(50)` = 13, plus 1). The loop period is a whole number of jiffies, at least 14 (56 ms at a 4 ms jiffy), so at most **17.86 polls/s** and at most **16,071 polls in 15 min**. The dossier says 18 to 20 polls/s and about 18,000. Its figures are conservative for buffer sizing but the rate is wrong. | 4.3 |
| B3 | **New: a lock-order inversion in the joypad driver can wedge the poll thread for good, silently.** `psp_joypad_process_input` takes `list_sem` then a queue's `sem`. `psp_joypad_queue_free` (the `/dev/joypad` release path) takes the queue's `sem` then `list_sem`, and never releases the queue's `sem`. If a last close of `/dev/joypad` overlaps a feed, both sleep forever. The poll thread then never polls again, both the OSK stream and the mouse stop, and nothing is printed. A variant ends in use-after-free. The trigger needs `psposk2` (the only `/dev/joypad` opener found) to close its fd, which the disassembly shows it does only when it tears down. This is an H7-shaped mechanism that is not named in the dossier. | 5 (H7), 2 |
| B4 | **Mouse delivery only happens in mouse mode.** `psp_mouse_process_input` is called only when bit `0x00800000` is set in `s_psp_joypad_keys`. `telem`, `grow` and `keymap` all describe `/dev/input/mice` as "always live". It is not. Outside mouse mode no packets are produced, so their INPUT counters see only OSK characters on the tty. | 3 (obs. 1/2), 6.2 |
| B5 | **telem's kmsg capture goes blind once the log has held 16 KB.** `syslog(3)` returns `min(len, logged_chars)` and `logged_chars` stops at `log_buf_len` (16384). telem rewrites `/ms0/kmsg.txt` only when the returned *length* changes. After 16 KB has ever been logged the length is always 16384, so later printk output is never captured. Observation 5 ("ring buffer did not change") is valid only if the captured `kmsg.txt` is shorter than 16384 bytes. | 3 (obs. 5), 6.2 |
| B6 | **"Both dying together points at or below `psp_joypad_thread`" needs qualifying.** The two consumers share more than the thread: both use `/dev/vcs` (console semaphore), both mmap the framebuffer, and through B3 an exit of `psposk2` can take the thread down. A stuck console semaphore would freeze both daemons while the thread still delivers. Mouse-mode button presses counted by telem through `/dev/input/mice` would still tell these cases apart (B4). | 2 |
| B7 | **Signals.** The poll thread is in process group 1 and session 1, shares its `sighand` (all `SIG_DFL`) with `swapper`, has no controlling tty, and is not skipped by `kill(-1, ...)`. Neither `psposk2` nor `pspmd` sends signals to anything but itself (via `abort`). In normal operation I found no path that signals the thread. Busybox init's shutdown sequence and a root user's `kill -1` / `kill <pid>` would. | 4.7 |

---

## 1. `drivers/input/joypad_psp.c`

### 1.1 Build and initialisation

- The driver is built in, not a module: `.config:338` `CONFIG_INPUT_PSP_JOYPAD=y`;
  `drivers/input/Kconfig:187` `bool "Joypad on SONY PSP"`;
  `drivers/input/Makefile:26` `obj-$(CONFIG_INPUT_PSP_JOYPAD) += joypad_psp.o`.
- `module_init( psp_joypad_init );` (`joypad_psp.c:697`). Built in, this is a
  device initcall, run by `do_initcalls()` (`init/main.c:729`) inside
  `kernel_init()` in pid 1, before `init_post()` execs `/init`
  (`init/main.c:821` `do_basic_setup();` then `:841` `init_post();`).
- The init order in `psp_joypad_init` (`joypad_psp.c:159-207`) is:
  `register_chrdev_region` (166), `cdev_add` (176), `INIT_LIST_HEAD(&s_psp_joypad_queue_list)` (185),
  `psp_mouse_init()` (188), then the thread (195-197):
  ```
  s_psp_joypad_thread_id = kernel_thread( psp_joypad_thread,
                                          NULL,
                                          CLONE_FS | CLONE_SIGHAND );
  ```
  So the input device is registered before the thread starts.

### 1.2 Thread lifecycle

- The loop is at `joypad_psp.c:458-469`:
  ```
  while ( !s_psp_joypad_thread_terminated )
  {
    if ( psp_joypad_read_input( &keys, &x, &y ) )
    {
      psp_joypad_process_input( keys, x, y );

      if ( s_psp_joypad_keys & PSP_JOYPAD_KEY_MOUSE_MODE )
        psp_mouse_process_input( keys, x, y );
    } // end if

    msleep( 1000 / PSP_JOYPAD_SAMPLE_RATE );
  } // end while
  ```
- **The only exit** is `s_psp_joypad_thread_terminated` becoming true, after
  which the thread returns 0 (`:471`) and `kernel_thread_helper` calls
  `do_exit` (`arch/mips/kernel/process.c:219-222`). The flag is set only in
  `psp_joypad_exit()` (`:211` `s_psp_joypad_thread_terminated = TRUE;`).
  That function is called from the module exit hook, which never runs for a
  built-in driver, and from the init failure path at `:202`, which runs only
  if `kernel_thread` itself failed. **In a running system the thread cannot
  exit.** It can only block or spin.
- The thread has no name of its own. It is created from pid 1 before pid 1
  execs, and pid 1 is a copy of `init_task`, whose `.comm = "swapper"`
  (`include/linux/init_task.h:149`). Neither `init/main.c` nor
  `joypad_psp.c` calls `set_task_comm` or `daemonize` (grep: no hits). So
  in `ps` and `/proc/<pid>/stat` **the poll thread shows up as `swapper`
  with ppid 1**. So does the UART3 TX thread, created the same way at
  `drivers/serial/serial_psp.c:738-740`.
- It has no `mm`. When it is created, pid 1 is still a kernel thread with
  `mm == NULL`, and `copy_mm` returns early (`kernel/fork.c:545-547`
  `oldmm = current->mm; if (!oldmm) return 0;`). The OOM killer therefore
  skips it (`mm/oom_kill.c:222-223` `if (!p->mm) continue;`).
- Its priority is inherited from pid 1 (nice 0). The driver sets nothing.
  `CONFIG_PREEMPT=y` (`.config:135`), so the thread can be preempted
  anywhere outside spinlocks and IRQ-off regions, including while it holds
  `list_sem` or a queue `sem`. That matters for B3.

### 1.3 Every place the thread can block or wait

| ID | Where | Call | Can it last forever? |
|---|---|---|---|
| W1 | `:486-487` | `_pspSysconCtrlAStickPower(1)`, `_pspSysconGetCtrl2(...)` | That is Recon A's area (`recon/syscon.md`). |
| W2 | `:530` | `down_interruptible( &s_psp_joypad_queue_list_sem )` | Yes, if its holder never releases it (see B3, section 1.6). |
| W3 | `:390` (inside `queue_push`, called at `:534` while `list_sem` is held) | `down_interruptible( &queue_->sem )` | Yes. `psp_joypad_queue_free` takes this semaphore and **never ups it** (section 1.6). |
| W4 | `:518` then `arch/mips/psp/psp.c:259-262` | `psp_lcd_on()` → `do_unblank_screen(0)` | Only when `console_blanked` is set. See 1.7. |
| W5 | `:651-658` | `input_report_*`, `input_sync` → input core → mousedev | Takes no sleeping lock. Only per-client spinlocks (section 3). |
| W6 | `:468` | `msleep(50)` | Only if timer softirqs stop. telem's own `nanosleep` loop kept running (obs. 1) and rests on the same timer softirq, so a total timer stop is excluded by observation. |

### 1.4 Every exit branch of `psp_joypad_read_input` (`:474-496`)

| Branch | Code | Result |
|---|---|---|
| R1 | `:483-484` `if ( unlikely( pkeys_ == NULL \|\| px_ == NULL \|\| py_ == NULL ) ) return FALSE;` | Unreachable. The caller passes stack addresses (`:460`). |
| R2 | `:486` `(void)_pspSysconCtrlAStickPower( 1 );` | **The return value is discarded.** A failure of command 0x33 leaves no trace. |
| R3 | `:487-488` `if ( _pspSysconGetCtrl2( (u32*)&keys, px_, py_ ) < 0 ) return FALSE;` | Any negative return is lost silently. `*px_` and `*py_` have already been written by `_pspSysconGetCtrl2` (`syscon.c:364-365`) but are not used. |
| R4 | `:490` `*pkeys_ = ~keys;` then `:492-493` `if ( *pkeys_ & PSP_JOYPAD_KEY_HOLD ) return FALSE;` | The HOLD bit (`0x00002000`, `:49`) after inversion suppresses everything silently, whether the HOLD switch really is on or the frame is all zero (dossier 4.5). |
| R5 | `:495` `return TRUE;` | Proceeds to delivery. |

A note on bits 22 to 31: `_pspSysconGetCtrl2` builds the full 32-bit word
from `rx_buf[3..6]` (`syscon.c:363`
`*ctrl = rx_buf[3]|(rx_buf[4]<<8)|(rx_buf[5]<<16)|(rx_buf[6]<<24);`), and
`read_input` inverts all 32 bits. So bits 22 to 31 of the delivered word are
`~rx_buf[5]` bits 6 and 7 and `~rx_buf[6]`. `process_input` then **ORs** the
analog nibbles into bits 24 to 31 (`:509-510`), and does not replace them.
Also, `PSP_JOYPAD_KEY_MOUSE_MODE` is `0x00800000` (`:58`), which is bit 23,
which is `~rx_buf[5]` bit 7. If that raw bit were ever 0, mouse mode would be
forced on for that sample no matter what SELECT has done. What these raw bits
normally contain is **UNVERIFIED**. It depends on the syscon frame (Recon A)
and can only be seen on hardware.

### 1.5 `psp_joypad_process_input` (`:498-540`): every exit and silent loss

```
static unsigned long lastKeys = 0;          /* :505 */
static BOOL mouseMode = FALSE;              /* :506 */
keys_ |= ( ( (unsigned long)( x_ & 0xf0 ) << 20 ) |
           ( (unsigned long)( y_ & 0xf0 ) << 24 ) );   /* :509-510 */
if ( lastKeys == keys_ )
  return;                                   /* :512-513 */
lastKeys = keys_;                           /* :515 */
psp_lcd_on();                               /* :518 */
if ( keys_ & PSP_JOYPAD_KEY_SELECT )
  mouseMode = !mouseMode;                   /* :521-522 */
if ( mouseMode )
  keys_ |= PSP_JOYPAD_KEY_MOUSE_MODE;       /* :524-525 */
s_psp_joypad_keys = keys_;                  /* :527 */
if ( down_interruptible( &s_psp_joypad_queue_list_sem ) == 0 )   /* :530 */
{
  list_for_each( pos, &s_psp_joypad_queue_list )
  {
    (void)psp_joypad_queue_push( LIST_TO_QUEUE( pos ), keys_ );  /* :534 */
  }
  up( &s_psp_joypad_queue_list_sem );
  wake_up_interruptible( &s_psp_joypad_wait_queue );             /* :538 */
}
```

| ID | Silent stop or loss | Evidence |
|---|---|---|
| P1 | **Dedupe.** Nothing is delivered unless the combined word (buttons plus the high nibble of each analog axis) changes. A frozen frame looks exactly like "operator not pressing". | `:512-513` |
| P2 | **The mouse-mode toggle fires on any change while SELECT is held**, not just on the press. Moving the stick across a nibble boundary with SELECT held flips `mouseMode` again. | `:521-522` run on every changed sample |
| P3 | `lastKeys` and `s_psp_joypad_keys` are updated (`:515`, `:527`) **before** the semaphore. If `down_interruptible` at `:530` fails, that change is lost for good: it is not retried, because the next identical sample is deduped at `:512`. There is also no `wake_up`. | `:515`, `:527`, `:530` |
| P4 | `queue_push` failures are ignored (`(void)` at `:534`): the semaphore is interrupted (`:390-393` `return FALSE;`) or the queue is full (`:395-399`, 16 entries, `:63`). **When a queue is full the newest value is dropped**, and the reader later sees stale state. | `:390-399` |
| P5 | The mouse path depends only on `s_psp_joypad_keys` (`:464`), which is assigned at `:527` before the semaphore. So P3 and P4 **cannot** stop the mouse path. | `:464`, `:527` |
| P6 | Only processes that have `/dev/joypad` open have a queue. Delivery with no reader is a no-op. | `:305-314`, `:532-535` |

### 1.6 The `/dev/joypad` queue code, including B3

Relevant code:

```
/* open: :305-314 -> psp_joypad_queue_init */
static void psp_joypad_queue_init(psp_joypad_queue_t * queue_)      /* :331 */
  ...
  if ( down_interruptible( &s_psp_joypad_queue_list_sem ) == 0 )   /* :339 */
  {
    list_add( &queue_->list, &s_psp_joypad_queue_list );
    up( &s_psp_joypad_queue_list_sem );
  }

/* release: :319-329 -> psp_joypad_queue_free */
static void psp_joypad_queue_free(psp_joypad_queue_t * queue_)      /* :346 */
{
  if ( down_interruptible( &queue_->sem ) != 0 )                   /* :348 */
  {
    return;
  }

  if ( down_interruptible( &s_psp_joypad_queue_list_sem ) == 0 )   /* :353 */
  {
    list_del( &queue_->list );
    up( &s_psp_joypad_queue_list_sem );
  }

  kfree( queue_ );                                                  /* :359 */
}
```

Lock order:

- The poll thread takes `list_sem` (`:530`), then `Q->sem` (`:390`, via `:534`).
- The closer takes `Q->sem` (`:348`), then `list_sem` (`:353`). **`Q->sem` is
  never `up()`ed** before `kfree`.

Consequences, derived from the code:

| Case | Sequence | Outcome |
|---|---|---|
| Q1 deadlock | The thread holds `list_sem` and is preempted before it takes `Q->sem` (possible: `CONFIG_PREEMPT=y`, and the fast path of `down_interruptible` does not disable preemption, `include/asm-mips/semaphore.h:85-94`). The closer runs `:348` and gets `Q->sem`, then blocks at `:353` on `list_sem`. The thread resumes and blocks at `:390` on `Q->sem`. | **Both sleep forever** in `__down_interruptible` (`arch/mips/kernel/semaphore.c:147-160`), in TASK_INTERRUPTIBLE. The poll thread never polls again. Joypad queues and the mouse both stop. No printk. The kernel and other processes keep running. |
| Q2 use-after-free | As Q1, but the closer has a signal pending (for example it is being killed), so `:353` returns `-EINTR`. | `list_del` is skipped and `kfree(queue_)` runs (`:359`) while the queue is still on `s_psp_joypad_queue_list`, and possibly while the thread is asleep on the wait queue inside the freed block. Later pushes write freed memory. Results are unpredictable. No MMU, so no fault. |
| Q3 leak | The closer blocks at `:348` because the thread holds `Q->sem` inside push, and has a signal pending. | Returns early. The queue stays on the list with no reader, fills to 16, and further pushes drop (`:395-399`). Harmless to other readers. |
| Q4 open while signalled | `:339` fails. | The new opener's queue is never added to the list. That reader never receives an event and nothing reports it. |

A signal arriving for a thread asleep in `__down_interruptible` wakes it,
and the call returns `-EINTR` (`semaphore.c:148-156`). So a Q1 deadlock
would be broken by any signal to the poll thread. I found none in normal
operation (section 2.4).

**Who can trigger Q1 or Q2?** The last close of a `/dev/joypad` file.

- `psposk2` is the only `/dev/joypad` opener I found in the initramfs or in
  the operator's test programs:
  - `psposk2` opens it at file offset `0x6768`/`0x6770`:
    `addiu a0,v0,-4464` ("/dev/joypad"), `move a1,zero` (O_RDONLY), call `open`.
  - `pspmd` has no `/dev/joypad` string (section 5.2).
  - `telem.c`, `keymap.c`, `diffgrowth.c` and `hello_fb.c` never open it
    (grep).
- In `psposk2` the fd is closed only in object destructors (for example
  `0x680c`-`0x6880`: it stores the vtable, then `lw v0,4(obj)`,
  `bltz ... skip`, and calls `close`). So Q1 or Q2 needs `psposk2` to tear
  down: exit through its failure state
  ("OSK: Program terminated after encountering an error", referenced at
  `0x4938`) or die by `abort()`. **UNVERIFIED:** which runtime errors lead
  to teardown. The strings list open, read, ioctl, screenshot and
  framebuffer failures (section 5.1). Whether each one is fatal is not
  established.
- The window is narrow: the thread must be preempted between `:530` and
  `:390` in a poll where the keys changed. That would give an irregular,
  memoryless failure time. That is an inference, and it is labelled as one.

### 1.7 `psp_lcd_on()` from the poll thread

`arch/mips/psp/psp.c:254-263`:
```
void psp_lcd_on(void)
{
  extern int console_blanked;
  extern void do_unblank_screen(int leaving_gfx);

  if ( console_blanked )
  {
    do_unblank_screen( 0 );
  }
}
```

- `do_unblank_screen` expects the console semaphore to be held
  (`drivers/char/vt.c:3549` `WARN_CONSOLE_UNLOCKED();`). The poll thread
  calls it without that lock. The check is silent here:
  `include/linux/console.h:139-140` defines it as `WARN_ON(...)`,
  `.config:173` has `# CONFIG_BUG is not set`, and in that case
  `include/asm-generic/bug.h:55-59` defines `WARN_ON` as the bare condition
  with no printk. `include/asm-mips/bug.h` defines `HAVE_ARCH_WARN_ON` only
  inside `#ifdef CONFIG_BUG`.
- `do_unblank_screen` goes on to call `vc->vc_sw->con_blank(vc, 0, ...)`
  (`vt.c:3569`) and then `set_palette` and `set_cursor` (`vt.c:3574-3575`),
  racing any console writer.
- This path runs only when the console is blanked. The default blank
  interval is 10 minutes (`vt.c:174` `static int blankinterval = 10*60*HZ;`).
  It can be changed by the `CSI 9;n ]` escape (`vt.c:1398`). **It is not
  reachable before about 600 s of console inactivity**, so it cannot explain
  a death at 17 s. It can be reached in a 15-minute run in which nothing
  writes to the text console (telem draws to `/dev/fb0` directly and does not
  poke the console).

### 1.8 `psp_mouse_process_input` (`:593-659`): every exit

| ID | Exit | Code |
|---|---|---|
| M0 | Not called at all unless mouse mode is on | `:464` `if ( s_psp_joypad_keys & PSP_JOYPAD_KEY_MOUSE_MODE )` |
| M1 | No device | `:609-610` `if ( unlikely( s_psp_mouse_dev == NULL ) ) return;`. Set once at init (`:554`) and cleared only in `psp_mouse_exit` (`:589`). |
| M2 | No motion and no button change | `:639-645`. Analog nibbles `0x6` to `0x9` map to 0 (`:675-680` commented out, then `default: return 0;` at `:692-693`), so a centred stick with no D-pad and no triggers produces nothing. |
| M3 | Reports | `:651-658`: `input_report_rel` X, Y (Y negated), `input_report_key` LEFT, MIDDLE, RIGHT, `input_sync`. Filtered further by the input core (section 3). |

Mouse buttons are L-trigger (left), R-trigger (right), and both together
(middle) (`:615-627`).

### 1.9 Re-verification of dossier 4.3 and 4.7

**4.3.** Confirmed:
- `:64` `#define PSP_JOYPAD_SAMPLE_RATE        20      /* samples per second */`
- `:468` `msleep( 1000 / PSP_JOYPAD_SAMPLE_RATE );`
- "The real period is a little longer" is right.

Corrected: the numbers. See section 4. The period is at least 14 jiffies
(56 ms), so the rate is at most 17.86 polls/s and at most 16,071 polls in
15 min, not "about 18 to 20" and "about 18,000".

**4.7.** Confirmed:
- The flags: `:195-197`, quoted in 1.1.
- No `daemonize()`: grep finds none in `joypad_psp.c`.
- `down_interruptible` at `:390` and `:530`.
- "Never cleared": nothing in the file calls `flush_signals`, and a kernel
  thread never returns to user mode, where signals are dequeued.
- "Would not stop the mouse path": P5.

**Wrong:** "every `down_interruptible` fails from then on". See B1 and
section 2.3.

Missing from 4.7: the release path takes the same two semaphores in the
reverse order and leaks one of them (B3, section 1.6). That turns a stuck
semaphore into a way to stop the whole thread, which a pending signal alone
does not do.

---

## 2. Signals and the poll thread

### 2.1 How the thread is created

- `kernel_thread` on MIPS (`arch/mips/kernel/process.c:224-243`) ends in
  `return do_fork(flags | CLONE_VM | CLONE_UNTRACED, 0, &regs, 0, NULL, NULL);`
  (`:242`). The effective flags are
  `CLONE_FS | CLONE_SIGHAND | CLONE_VM | CLONE_UNTRACED`, with no
  `CLONE_THREAD`.
- **The parent is pid 1**, still running `kernel_init` (1.1).
  `exit_signal = clone_flags & CSIGNAL` (`kernel/fork.c:1166`), which is 0.
- **Signal handlers are shared, signal state is not.**
  - `copy_sighand` with `CLONE_SIGHAND` just increments the count
    (`kernel/fork.c:812-814`).
  - pid 1 was itself created with `CLONE_FS | CLONE_SIGHAND`
    (`init/main.c:435`), so the poll thread, pid 1 before exec, `swapper`
    (`.sighand = &init_sighand`, `init_task.h:154`) and the UART3 TX thread
    all share `init_sighand`.
  - When pid 1 execs `/init`, `de_thread` sees `count > 1` and gives pid 1
    a private copy (`fs/exec.c:599` check, `:745-771` switch). The poll
    thread keeps the old one.
  - Nobody changes its actions: `ignore_signals` is only used by
    `kthreadd` (`kernel/kthread.c:224`), which has its own `sighand`
    (`init/main.c:437`, flags `CLONE_FS | CLONE_FILES`). So **every action
    is `SIG_DFL`**.
  - `copy_signal` makes a separate `signal_struct` because there is no
    `CLONE_THREAD` (`kernel/fork.c:836-842`), with `sig->leader = 0`
    (`:873`).
- **The blocked mask is empty.** It is copied from pid 1, whose mask comes
  from `init_task` `.blocked = {{0}}` (`init_task.h:159`). Nothing in the
  driver blocks signals.
- **Process group and session are both 1.** `kernel_init` calls
  `__set_special_pids(1, 1);` at `init/main.c:809`, before `do_basic_setup()`
  at `:821`. The child inherits pgrp and session at `kernel/fork.c:1254-1257`.
- **No controlling tty.** The child gets `p->signal->tty = current->signal->tty;`
  (`kernel/fork.c:1253`). At initcall time pid 1 has opened nothing, and
  even its later `sys_open("/dev/console")` (`init/main.c:761`) sets
  `noctty = 1` (`drivers/char/tty_io.c:2592-2598`), so no ctty is acquired
  (`:2656-2660` needs `!noctty && current->signal->leader`).

### 2.2 Can a signal become pending on it? Yes, by these routes only

**Generation.** `__group_send_sig_info` (`kernel/signal.c:911-936`) drops a
signal only if `sig_ignored()` returns true (`:919-920`). `sig_ignored`
(`:43-65`) returns true only for `SIG_IGN` or for `SIG_DFL` plus
`sig_kernel_ignore`, which is SIGCONT, SIGCHLD, SIGWINCH and SIGURG
(`include/linux/signal.h:349-351`). Every other signal is queued and
`TIF_SIGPENDING` is set. For a default-fatal signal
(`signal.h:368-370` `sig_fatal`), `__group_complete_signal` also sets
`SIGNAL_GROUP_EXIT`, adds SIGKILL to the thread's pending set and calls
`signal_wake_up(t, 1)` (`kernel/signal.c:853-875`). Nothing kills the
thread, because a kernel thread never reaches `get_signal_to_deliver`. The
pending state stays.

**Routes that reach it:**

| Route | Code | Can it reach the thread? |
|---|---|---|
| `kill(-1, sig)` | `kernel/signal.c:1115-1129`: `for_each_process(p) { if (p->pid > 1 && p->tgid != current->tgid) { ... group_send_sig_info(sig, info, p);` | **Yes.** Kernel threads are not excluded. Permission is checked in `check_kill_permission` (`:519-537`), and all userland here runs as root. Busybox 1.7.0 init (the version string `BusyBox v1.7.0 (2008-02-01 16:57:07 HKT)` is in `/bin/busybox`) contains the strings "The system is going down NOW!" and "Sending SIG%s to all processes", which fits the usual shutdown `kill(-1, SIGTERM)` then SIGKILL. **UNVERIFIED** in the busybox binary itself. This happens only at halt, reboot or poweroff. |
| `kill(pid, sig)` aimed at the thread's pid | `:1132-1133` | Yes, if a user types it. The thread shows as `swapper` (1.2). |
| `kill(0, sig)` or `killpg(1, sig)` | `:1113-1114`, `:1130-1131` | Only from a process in pgrp 1. pid 1 is in pgrp 1. Children of busybox init normally `setsid()` (**UNVERIFIED** in the binary). |
| tty job-control signals (^C, ^Z, hangup) | sent to `tty->pgrp` | Only if a tty had session 1 and foreground pgrp 1. The thread has no ctty (2.1). Opening `/dev/console` never makes one (`tty_io.c:2592-2598`). The kernel does let pid 1 call `setsid()` despite pgrp 1 existing (`kernel/sys.c:1584-1588`). Whether busybox init then opens a real tty without `O_NOCTTY` is **UNVERIFIED**. If it did, an OSK-injected `0x03` (section 5.1) into that tty would send SIGINT to pgrp 1 and so to the poll thread. |
| SIGIO from mousedev fasync | `drivers/input/mousedev.c:270` `kill_fasync(&client->fasync, SIGIO, POLL_IN);` | Only to fasync owners. The thread has no files. |
| SIGCHLD | — | Ignored at generation (`SIG_DFL`, `sig_kernel_ignore`). The thread has no children anyway. |
| Faults, `SIGPIPE`, timers | — | These are sent to the task making the syscall or taking the fault. The thread makes no syscalls. A kernel fault would oops, not signal. |
| `psposk2`, `pspmd` | Section 5 | **No.** Each has exactly one `kill` syscall stub, reached only from `raise()`, which does `kill(getpid(), sig)`. In `psposk2`, `raise` is at `0x18f70` (calls `getpid` via `lw t9,864(gp)`, then tail-calls `kill` via `lw t9,1152(gp)`), and is called from `0x17724` with `li a0,6` (SIGABRT, that is `abort()`). In `pspmd`, `getpid` is called at `0x1592c` and `kill` at `0x15944`, the same pattern. The number of `syscall` instructions equals the number of distinct syscall stubs (18 in `psposk2`, 16 in `pspmd`), so there is no generic `syscall()` path that could issue another `kill`. |

**Conclusion.** In normal operation (no shutdown, nobody typing `kill`) I
found no path that makes a signal pending on the poll thread. The only
generic routes are `kill(-1, ...)` (including busybox init's shutdown
sequence) and a root user signalling pid 1's process group or the thread's
pid.

### 2.3 What a pending signal does to `msleep` and `down_interruptible`

- **`msleep` is unaffected.** `kernel/timer.c:1529-1535`:
  ```
  void msleep(unsigned int msecs)
  {
  	unsigned long timeout = msecs_to_jiffies(msecs) + 1;

  	while (timeout)
  		timeout = schedule_timeout_uninterruptible(timeout);
  }
  ```
  `schedule_timeout_uninterruptible` sets `TASK_UNINTERRUPTIBLE`
  (`:1080`). `signal_wake_up` wakes only `TASK_INTERRUPTIBLE`, plus
  STOPPED and TRACED for SIGKILL (`kernel/signal.c:458-461`). Even an early
  wake would re-sleep for the rest of the timeout, because of the `while`
  loop. 2.6.22 has no TASK_KILLABLE (grep for `fatal_signal_pending` and
  `TASK_KILLABLE` in `include/linux/sched.h` finds nothing).
- **`down_interruptible` fails only when contended.**
  `include/asm-mips/semaphore.h:85-94`:
  ```
  static inline int down_interruptible(struct semaphore * sem)
  {
  	int ret = 0;

  	might_sleep();

  	if (unlikely(atomic_dec_return(&sem->count) < 0))
  		ret = __down_interruptible(sem);
  	return ret;
  }
  ```
  The signal is checked only in the slow path
  (`arch/mips/kernel/semaphore.c:147-157`):
  ```
  while (__sem_update_count(sem, -1) <= 0) {
  	if (signal_pending(current)) {
  		...
  		retval = -EINTR;
  		break;
  	}
  	schedule();
  ```
  With a signal pending:
  - `:530` fails only when `list_sem` is held by a process opening or
    closing `/dev/joypad`.
  - `:390` fails only when a reader is inside `queue_pop` (`:422-442`) or
    `queue_reset` (`:364-371`), or a closer is in `queue_free`.

  **The result is lost events now and then (P3, P4), not permanent
  silence.** The mouse path is unaffected (P5).
- One side effect: a pending signal would turn the Q1 deadlock into Q2
  behaviour on the thread's side. The thread's `:390` would return `-EINTR`
  instead of sleeping.

---

## 3. From `input_report_*` through the input core to mousedev

### 3.1 The path

1. `include/linux/input.h:1147-1175` defines the helpers as thin wrappers:
   - `input_report_key` → `input_event(dev, EV_KEY, code, !!value)`
   - `input_report_rel` → `input_event(dev, EV_REL, code, value)`
   - `input_sync` → `input_event(dev, EV_SYN, SYN_REPORT, 0)`
2. `input_event` is at `drivers/input/input.c:46-195`. It takes no lock and
   can be called from the thread in process context. It calls
   `add_input_randomness` (`:53`), filters by type, and then hands the event
   to every open handle (`:186-194`):
   ```
   if (type != EV_SYN)
   	dev->sync = 0;

   if (dev->grab)
   	dev->grab->handler->event(dev->grab, type, code, value);
   else
   	list_for_each_entry(handle, &dev->h_list, d_node)
   		if (handle->open)
   			handle->handler->event(handle, type, code, value);
   ```
3. The mousedev handler matches because the device sets `EV_KEY | EV_REL`,
   `BTN_LEFT` and `REL_X | REL_Y` (`joypad_psp.c:565-569`), against
   `mousedev_ids[0]` (`drivers/input/mousedev.c:776-782`).
   `mousedev_event` (`:304-353`):
   - accumulates REL into `mousedev->packet` (`mousedev_rel_event`, `:187-194`);
   - sets or clears button bits in `mousedev->packet` and
     `mousedev_mix.packet` (`:196-226`);
   - on `SYN_REPORT` calls `mousedev_notify_readers` twice, once for the
     per-device node and once for the mixer (`:345-346`).
4. `mousedev_notify_readers` (`:228-277`) takes the per-client
   `spin_lock_irqsave(&client->packet_lock, flags)` (`:236`), merges into
   the client's packet ring (`PACKET_QUEUE_LEN 16`, `:89`), marks the client
   `ready`, sends SIGIO to fasync owners and calls
   `wake_up_interruptible(&mousedev->wait)` (`:275-276`).
5. The device nodes:
   - `/dev/input/mice` (13,63) is minor `MOUSEDEV_MINOR_BASE + MOUSEDEV_MIX`
     (`:12-14`, `:839-840`).
   - `/dev/psaux` (10,1) is a misc device with `mousedev_fops`
     (`:816-819`, registered at `:846-853` under
     `.config:315 CONFIG_INPUT_MOUSEDEV_PSAUX=y`). Its open maps to the mixer
     (`:462-464`). `/dev/mouse -> psaux` in the initramfs.
   - `/dev/input/mouse0` (13,32) is the per-device node.

   All three exist in the embedded initramfs (section 5).
6. Readers get 3-byte PS/2 packets by default (`mousedev_packet`,
   `:508-554`, the `MOUSEDEV_EMUL_PS2` default at `:537-542`).

### 3.2 Places where events are dropped or merged without any report

| ID | Where | Behaviour |
|---|---|---|
| I1 | `input.c:50-51` | Event type not in `dev->evbit` is dropped. EV_KEY, EV_REL and EV_SYN are all set, so this does not apply. |
| I2 | `input.c:74-75` | **A key report equal to the current state is dropped.** The driver reports all three buttons on every call, so only changes pass. |
| I3 | `input.c:125-126` | **`EV_REL` with value 0 is dropped.** |
| I4 | `input.c:64-66` | `SYN_REPORT` is dropped if `dev->sync` is already 1, that is, if nothing since the last sync survived I2 or I3. |
| I5 | `input.c:192-194` | **Events reach mousedev only if `handle->open` is non-zero**, meaning some process has a mousedev node open. `handle->open` is raised by `input_open_device` (`input.c:253-273`). |
| I6 | `mousedev.c:400-413` | When the *first* mixer client opens, `mixdev_open_devices` calls `input_open_device` per device, and on error does `continue` (`:406-407`) with no report. `input_open_device` can fail with `-EINTR` from `mutex_lock_interruptible` (`input.c:258-260`). If that happens, the mixer (`/dev/input/mice`, `/dev/psaux`) gets nothing from this device until every mixer client closes and one reopens. This only happens at open time. |
| I7 | `mousedev.c:239-245` | If a client's ring is full (the reader is not reading), motion is **merged** into the head packet and button transitions can be **merged away**. Motion is not lost. |
| I8 | `mousedev.c:264-265` | A client is marked ready only if the accumulated packet has motion or a button change. |
| I9 | `mousedev.c:235`, `:439-440` | `mousedev_notify_readers` walks `client_list` with no list lock (only the per-client spinlock is held inside the loop body). `mousedev_release` does `list_del(&client->node); kfree(client);` with no lock either. With `CONFIG_PREEMPT=y` the poll thread can be preempted between clients while another process closes a mousedev node. It could then follow a freed node, or `LIST_POISON1` = `0x00100100` (`include/linux/poison.h:10`, `list.h:171`). There is no MMU to fault, so the thread could read garbage or loop, silently. It needs a mousedev close at that moment: `telem`, `keymap` or `grow` exiting, or `pspmd` exiting. Documented as a mechanism only. |

The `/dev/joypad` path does not go through the input core at all. It is the
driver's own queue (section 1.6).

---

## 4. The actual poll period

- `HZ` is `CONFIG_HZ` (`include/asm-mips/param.h:14`), which is 250
  (`.config:132`).
- `msecs_to_jiffies(50)` (`kernel/time.c:526-532`, taken because
  `HZ <= MSEC_PER_SEC && !(MSEC_PER_SEC % HZ)`):
  `(m + (MSEC_PER_SEC / HZ) - 1) / (MSEC_PER_SEC / HZ)` = `(50 + 3) / 4` = **13**.
- `msleep` adds 1 (`kernel/timer.c:1531`), so it requests **14 jiffies**.
- `schedule_timeout` sets `expire = timeout + jiffies;` and
  `__mod_timer(&timer, expire);` (`kernel/timer.c:1053-1056`). The timer
  wheel runs a timer once `jiffies` has reached its expiry
  (`kernel/timer.c:613` `while (time_after_eq(jiffies, base->timer_jiffies))`).
  So the thread wakes on the tick that takes `jiffies` from `J+13` to `J+14`,
  where `J` is `jiffies` when `msleep` was called.
- The loop body (wake latency, `AStickPower`, `GetCtrl2`, processing) starts
  just after a tick. If it finishes before the next tick, `msleep` is called
  in the same jiffy and **the period is exactly 14 jiffies**. Each tick
  boundary crossed during the body adds one jiffy: 15, 16 and so on.
- **At a nominal 4 ms jiffy: 56 ms, at most 17.86 polls/s, at most 16,071
  polls (32,142 thread-context syscon commands) in 900 s.** A 60 ms period
  gives 16.67 polls/s. Watchdog `Nop`s add about 180 interrupt-context
  commands in 15 min (dossier 4.4; the cycle is at `psp.c:41` and
  `psp.c:376`).
- Caveat on the jiffy length (**UNVERIFIED on hardware**; the timer is Recon
  A's area):
  - The tick is CP0 Compare `PSP_COUNTS_PER_TICK = 220912896 / HZ`
    (`arch/mips/psp/psp.c:38-39`, programmed at `:611-618`), with Count reset
    to 0 in each handler (`:352`).
  - Each real tick is therefore `PSP_COUNTS_PER_TICK` counts plus the
    latency from interrupt to reset. It is never shorter than nominal.
  - The PSP port sets neither `mips_hpt_frequency` nor `mips_timer_state`
    (grep of `arch/mips/psp/`: no hits), so `time_init` takes the
    "unknown frequency" branch (`arch/mips/kernel/time.c:377-381`) and
    `mips_timer_ack = null_timer_ack` (`:410-412`).
  - The Count rate of 220,912,896/s is annotated "measured by tests"
    (`psp.c:38`) and cannot be checked here.
  - telem's `ELAP` (from `gettimeofday`) and `KUP` (from `/proc/uptime`)
    both derive from jiffies, so telem cannot detect a wrong tick rate.
    Only an external stopwatch can.

---

## 5. Userland: `psposk2` and `pspmd`

### 5.0 Provenance and launch

- `md5sum`:
  - `build/linux/psp-initramfs.cpio` = `026067ded27954783933b2a7ab90d591`
  - `/home/ubuntu/psp/extract/initramfs2.cpio` is the same, so `extract/root2`
    is the embedded initramfs.
  - `extract/initramfs.cpio` (`ba549df0...`) is a different, older archive.
    I did not use it.
- I unpacked the embedded cpio to `scratch-input/initramfs/`. Device nodes
  could not be created without root. The listing (`cpio -itv`) shows:
  - `dev/joypad` c 39,200
  - `dev/input/mice` c 13,63
  - `dev/input/mouse0` c 13,32
  - `dev/psaux` c 10,1, plus `dev/mouse -> psaux`
  - `dev/vcs` c 7,0
  - `dev/fb0` c 29,0, plus `dev/fb -> fb0`
  - `dev/console` c 5,1
  - `dev/tty1`..`tty6`
  - `dev/ttySRC2` c 4,200
  - `dev/ms0` b 31,200
- Binaries:
  - `/usr/bin/psposk2`: 530,332 bytes, bFLT v4, built "Sun Feb 3 07:49:04 2008", stack 0x1000.
  - `/usr/bin/pspmd`: 121,228 bytes, bFLT v4, built "Sun Feb 3 07:49:22 2008", stack 0x1000.

  Both are statically linked C++ (the strings include `__gnu_cxx::__concurrence_lock_error`).
- `/init -> bin/busybox` (BusyBox v1.7.0). `etc/inittab:3`
  `::sysinit:/etc/rc.sysinit`. Lines 9-12 respawn `-/bin/msh` on tty1 to
  tty4. Line 16 is `::shutdown:/bin/umount -a -r`.
- `etc/rc.sysinit`:
  - `:6` `mount -t proc proc /proc`
  - `:10` `mount -t vfat /dev/ms0 /ms0`
  - `:14` ``psposk2 `cat /proc/cmdline|sed 's,.*osk=\([^ ]*\).*,-s\1,'`&``
  - `:18` `pspmd -s&`

  Both daemons run in the background, as children of the sysinit shell, and
  are reparented to init when it exits.
- Note on `:14`: if the kernel command line has no `osk=`, the `sed`
  substitution does not match and `psposk2` receives the whole command line
  as arguments. The effect is **UNVERIFIED**; the `pspboot.conf` command
  line is on the Memory Stick, which is not available.
- **telem is not in the initramfs** and not in `rc.sysinit`. How it was
  started on the device (presumably typed at a shell, from `/ms0`) is
  **UNVERIFIED**.

### 5.1 `psposk2`: device nodes and how the OSK injects characters

Strings: `/dev/vcs`, `/dev/joypad`, `/dev/fb0`,
`/usr/screenshots/screenshot%04d.bmp`, and the class names `OskCore`,
`OskInput_Psp`, `OskConsole_Psp`, `OskCanvas_Psp`, `OskCore::MouseState`,
`KbdState`, `FailedState`.

Opens and calls, from the annotated disassembly
(`scratch-input/psposk2.ann`; string addresses resolved through the GOT page
entry `lw v0,12(gp)` = 0x420000):

| Offset | Instruction(s) | Meaning |
|---|---|---|
| `0x6694`-`0x66a4` | `addiu a0,v0,-4476` ("/dev/vcs"), `move a1,zero`, `lw t9,308(gp)` → `open` | `open("/dev/vcs", O_RDONLY)` ("console" agent; the error string at `0x66ec` is "OSK: Failed to open device for console") |
| `0x6768`-`0x6778` | `addiu a0,v0,-4464` ("/dev/joypad"), `move a1,zero`, → `open` | `open("/dev/joypad", O_RDONLY)`, blocking ("input" agent; error string at `0x67c0`) |
| `0x7014`-`0x7030` | `lw v0,4(obj)` (the fd), `addiu v1,s8,28`, `li a2,4`, → `read` | `read(joypad_fd, &word, 4)`: one 32-bit key word per read, blocking in `wait_event_interruptible` (`joypad_psp.c:242-247`). `0x7048` `sltiu v0,v0,4` → "OSK: Failed to read device, err=%d" if fewer than 4 bytes. |
| `0x7468`-`0x7470` | `addiu a0,v0,-4452` ("/dev/fb0"), `li a1,2` → `open` | `open("/dev/fb0", O_RDWR)` |
| `0x74fc`-`0x7504` | `li a1,17920` → `ioctl` | `FBIOGET_VSCREENINFO` (0x4600) |
| `0x7614`-`0x7624` | `move a0,zero`, `li a2,3`, `li a3,1` → `mmap` | `mmap(NULL, len, PROT_READ\|PROT_WRITE, MAP_SHARED, fb, 0)` |
| `0x6594`-`0x65bc` | `lw a0,4(obj)`, loop over bytes (`lb v0,0(v0)`), `li a1,101`, `move a2,v0` → `ioctl` | **Character injection:** `ioctl(vcs_fd, 101, ch)` once per byte of a string |
| `0x6450`-`0x6458` | `li a1,107` → `ioctl` | `PSP_VCS_IOCTL_CHANGE_CON` |
| `0x634c`-`0x6350` | `li a1,108` → `ioctl` | `PSP_VCS_IOCTL_UPDATE_SCR` |

`psposk2` makes no `ioctl` on `/dev/joypad`: no `li a1,1` or `li a1,2` at
an `ioctl` call site. It uses only `read`.

The kernel side of the injection is `drivers/char/vc_screen.c`, compiled
under `CONFIG_SONY_PSP`:

- `:476` `#define PSP_VCS_IOCTL_PUTCHAR       101`
- `:477` `CHANGE_CON 107`, `:478` `UPDATE_SCR 108`, `:479` `GET_SIZE 109`
- `:488-492`:
  ```
  static void _psp_vcs_ioctrl_putchar(struct tty_struct * tty_, int ch_)
  {
    tty_insert_flip_char( tty_, (unsigned char)ch_, TTY_NORMAL );
    tty_schedule_flip( tty_ );
  }
  ```
- `:501-505` inserts into `vc_cons[ fg_console ].d->vc_tty` (the foreground
  VT's tty). Under `CONFIG_SERIAL_PSP_UART3_CONSOLE` (`.config:360`) it also
  inserts into `s_psp_serial_ports[ 2 ].info->tty` if that tty is open
  (`:507-512`). It always returns 0 (`:515`).
- `CHANGE_CON` and `UPDATE_SCR` take the console semaphore
  (`acquire_console_sem()` at `:530` and `:539`).
- `vcs_fops.ioctl = psp_vcs_ioctl` (`:605-607`).

So OSK characters enter the foreground VT's flip buffer as if typed on a
keyboard, and go through the line discipline (echo, ISIG). There is no
keyboard driver in this path. Any character, including `0x03` or ESC, is
possible.

Other `psposk2` behaviour relevant to the failure:

- **Teardown closes `/dev/joypad`** in destructors only
  (`close` at `0x6878`, `0x69bc`, `0x6b00`, `0x6c44`, `0x6d88`, `0x6ecc`,
  `0x77c0`, `0x7980`, `0x7b40`). This is the B3 trigger (section 1.6).
- **Power-off chord (semantics UNVERIFIED).** At `0x4b54`-`0x4ba0` the code
  tests bits `0x1000`, `0x20` and `0x40` of a word at `obj+60`. Those are
  HOME, CIRCLE and CROSS in `joypad_psp.c:41-48`. It clears them
  (`li v0,-4193` = `~0x1060`) and calls `0x15d4`. That function issues a raw
  `fork` syscall (`li v0,4002; syscall` at `0x15f4`). It tests
  `sltiu v0,v0,1` without checking the `a3` error flag. In the child it
  execs `"/sbin/poweroff"` (`addiu a0,v0,-5124` at `0x1610`), then exits.
  I did not check what `fork` does on this no-MMU kernel.
- The syscalls present are exit, fork, read, write, open, close, execve,
  getpid, kill (via `raise` only, section 2.2), ioctl, fcntl, mmap, munmap,
  fsync, _llseek, rt_sigaction, rt_sigprocmask and fcntl64. There is no
  `select` or `poll`, so all input is blocking `read`.

### 5.2 `pspmd`

Strings: `/dev/mouse`, `/dev/fb`, `/dev/vcs`, "PSP Mouse Daemon v0.1",
"MD: Failed to paste to console", "MD: Failed to read vcs device",
"MD: Mouse daemon terminates", "MD: Enter failure state!".

| Offset | Instruction(s) | Meaning |
|---|---|---|
| `0x1ec0`-`0x1ec8` | `addiu a0,v0,-22576` ("/dev/mouse"), `move a1,zero` → `open` | `open("/dev/mouse", O_RDONLY)`, blocking. `/dev/mouse -> psaux` (10,1), which is the **mousedev mixer**. |
| `0x1934`-`0x1938` | `li a2,3` → `read` | `read(mouse_fd, pkt, 3)`: 3-byte PS/2 packets |
| `0x2750`-`0x2758` | "/dev/vcs", `move a1,zero` → `open` | `open("/dev/vcs", O_RDONLY)` |
| `0x27e4`-`0x27ec` | `li a1,109` → `ioctl` | `PSP_VCS_IOCTL_GET_SIZE` |
| `0x2574`-`0x257c` | `li a1,101` → `ioctl` | **Paste into the console** through the same `PUTCHAR` injection as the OSK |
| `0x4164`-`0x4168` | → `lseek`, plus reads | Reads screen text from `/dev/vcs`. `vcs_read` takes the console semaphore (`vc_screen.c:123`). |
| `0x290c`-`0x2914` | "/dev/fb", `li a1,2` → `open`; `0x29a0` `ioctl 0x4600`; `0x2ab8`-`0x2ac8` `mmap` | Framebuffer, O_RDWR |

`pspmd` does not open `/dev/joypad` (no string). It is fed only through the
input core and the mousedev mixer, and so **only while mouse mode is on**
(M0).

**UNVERIFIED:** whether `pspmd` reads `/dev/vcs` on every cursor move, which
would put the console semaphore on its cursor path. The code is there
(`lseek` plus `read` on vcs) but I did not trace the call graph.

### 5.3 Other consumers on the device

These are taken from their sources in `/home/ubuntu/psp`, not from the
device.

- `telem`, `keymap` and `grow` each open `/dev/input/mice` `O_RDONLY | O_NONBLOCK`,
  falling back to `/dev/psaux` (`telem.c:251-260`, `keymap.c:204-212`,
  `diffgrowth.c:279-287`), and read the tty on stdin.
- Each one is a separate mixer client with its own 16-packet ring, so it does
  not take packets from `pspmd`.
- The comment in `keymap.c:15-16` ("There is NO raw per-button event device
  exposed to userspace on this kernel") is wrong: `/dev/joypad` exists and
  `psposk2` reads it.
- The comment in `keymap.c:8-10` ("/dev/input/mice ... always live") is
  wrong outside mouse mode (B4).

---

## 6. `telem` (`/home/ubuntu/psp/telem/telem.c`, `cbuild.sh`)

### 6.1 What it records, how often, where, and how it syncs

| Item | Detail | Evidence |
|---|---|---|
| Tick | `nanosleep` 200 ms **after** each loop body, so the period is 200 ms plus the body time. Body time is not measured. It includes a full redraw, a 522,240-byte framebuffer write, two `/proc` reads, a 16 KB `syslog` read and one or two `fsync`s. The real rate is **below 5 Hz, UNVERIFIED how far**. | `:54` `#define TICK_MS 200`; `:415` `ts.tv_sec = 0; ts.tv_nsec = TICK_MS * 1000000L; nanosleep(&ts, 0);` |
| Log file | `/ms0/telem.log`, `O_WRONLY \| O_CREAT \| O_APPEND`. **If that fails it falls back to `telem.log` in the cwd**, which on the initramfs is RAM and is lost on battery pull. | `:65`, `:325-326` |
| Header | `# PSP telem session start` / `# seq,elapsed_ds,kuptime_s,memfree_kb,inputs,lastinput_ds,kmsglen`, fsync'd | `:327-332` |
| Per-tick line | `seq` (loop count); `elapsed_ds` (deciseconds since start, from `gettimeofday`); `kuptime_s` (the first token of `/proc/uptime`, as text); `memfree_kb` (`MemFree:` from `/proc/meminfo`, or -1); `inputs` (count of ticks with at least one "ping"); `lastinput_ds`; `kmsglen` (return of `syslog(3)`) | `:404-410` |
| Sync | `write(logfd, ...)` then `fsync(logfd)` every tick. A battery pull loses at most the line in progress plus whatever vfat or the Memory Stick driver had not committed. Memory Stick driver behaviour is not examined here. | `:411-412` |
| What counts as a ping | (a) `poll_mouse()`: a **button press edge** in PS/2 byte 0 (`(p[0] & 0x07) && !(mprev & 0x07)`, `:270`). **Motion is not counted.** Mouse packets exist only in mouse mode (B4). (b) Any byte read from stdin (the tty), except `q`, `Q`, `3` or `27`, which quit (`:356-359`). The stdin bytes are OSK characters when telem's VT is in the foreground. | `:264-274`, `:355-360` |
| Terminal mode | `raw_on()` clears only `ICANON \| ECHO` and sets `VMIN=0`, `VTIME=0`. **`ISIG` stays on**, so an OSK-injected `0x03` raises SIGINT in the line discipline instead of reaching the `kb == 3` test at `:357`. | `:241-243` |
| kmsg capture | `syscall(__NR_syslog, 3, kbuf, 16384)` every tick. `/ms0/kmsg.txt` is rewritten (`O_TRUNC`, `write`, `fsync`, `close`) **only when the returned length changes**. It falls back to cwd `kmsg.txt`. | `:67`, `:279-297` |
| Blind spot (B5) | `kernel/printk.c:241-246` `count = len; if (count > log_buf_len) count = log_buf_len; ... if (count > logged_chars) count = logged_chars;` and `:422-423` `if (logged_chars < log_buf_len) logged_chars++;`. With `CONFIG_LOG_BUF_SHIFT=14`, once 16384 characters have ever been logged, every call returns 16384 and `kn != klast` (`telem.c:291`) is never true again. **After that, telem never captures new kernel messages.** | as quoted |
| HUD | Drawn into a static 480x272x4 back buffer and written to `/dev/fb0` with 272 `lseek`+`write` pairs. It does not use the console, so it does not keep the console from blanking (1.7). | `:56`, `:299-306`, `:364-400` |
| Memory and stack | bFLT stack is **0x1000 (4 KB)** (flthdr: `Stack Size: 0x1000`). `mem_free_kb` puts a **2048-byte** buffer on that stack (`:225`). `kbuf[16384]` and `back[]` are static (BSS end 0x867c0, about 540 KB). No MMU means no stack guard. | flthdr output; `:67`, `:225` |
| FP check | I reran `objdump -d telem.gdb`. `grep -c '[$]f[0-9]'` gives **0**, and `lwc1`, `swc1`, `mtc1`, `mfc1`, `cvt.`, `ldc1`, `sdc1`, `cfc1`, `ctc1` give **0**. | `scratch-input/telem.gdb.dis` |

`cbuild.sh` (`/home/ubuntu/psp/telem/cbuild.sh:1-10`):

- It runs inside the i386 container.
- `PATH` includes `/work/staging_dir/usr/mipsel-linux-uclibc/bin`, the
  target-triplet directory that dossier 7 warns about for kernel builds
  (`:3`).
- It builds with
  `mipsel-linux-uclibc-gcc --sysroot=/work/staging_dir -B.../mipsel-linux-uclibc/bin -Wl,-elf2flt -O2 -Wall -o telem telem.c`
  (`:6-8`).
- It prints `FP_REGS_USED=$(mipsel-linux-uclibc-objdump -d telem.gdb ... | grep -c '[$]f[0-9]')`
  (`:9`) and `flthdr` (`:10`).

### 6.2 What telem would need in order to also drain a kernel `/proc` file to the stick

Description only. Nothing here is implemented.

1. **Start without operator input.** Today telem is neither in the
   initramfs nor in `rc.sysinit`. It would have to be added to the embedded
   cpio and launched from `rc.sysinit` after `mount -t vfat /dev/ms0 /ms0`
   (`rc.sysinit:10`).
2. **Detach from the tty.** Launched from `rc.sysinit`, its stdin would be
   the console. `raw_on()` would alter that tty's settings (`:235-245`), and
   the stdin loop (`:356-359`) would take OSK characters away from the shell
   on the same tty, quitting on `q`/`Q`/ESC. The stdin handling and the quit
   keys would have to go, or stdin would have to come from `/dev/null`.
3. **Read binary data.** `read_file()` (`:200-209`) is text-oriented: it
   reserves a byte for NUL and caps at `n-1`. A binary drain needs its own
   loop: repeated `read` until 0, handling short reads. With the legacy
   `read_proc` interface a single call returns at most `PROC_BLOCK_SIZE` =
   `PAGE_SIZE - 1024` = 3072 bytes per `read_proc` round
   (`fs/proc/generic.c:49`, `:80`, 4 KB pages at `.config:100`), so a larger
   buffer needs several `read()` calls.
4. **Snapshot or consume.** Two semantics are possible, and they must be
   chosen together with the kernel side:
   - **snapshot**: reopen or seek to 0 and read the whole ring each tick, as
     `kmsg_capture` does now;
   - **consume**: read only what is new since the last read, like `/proc/kmsg`.

   Either way the tick rate matters. The kernel produces at most about 17.9
   polls/s (section 4), which is at least 3.6 polls per 200 ms telem tick,
   more when `fsync` stalls lengthen the tick.
5. **A new output file on `/ms0`**, opened `O_APPEND`. Today's practice is
   one `write` plus `fsync` per tick, and the same can apply. The code must
   not fall back silently to the cwd copy (`:326`, `:293`), which is in RAM.
   Its size must stay bounded, because the existing `telem.log` grows by one
   line per tick with no limit.
6. **Keep the no-FP rule.** Keep using `apps`/`appl` and raw `write`, with no
   `printf` (`:29-34`), and repeat the `cbuild.sh` FP grep and `flthdr` check.
7. **Watch the stack.** Any new buffer must be static, not on the stack
   (4 KB stack, 1 KB+ already used at peak, see 6.1).
8. **Fix the length-only change test** (B5) wherever change detection is
   reused.
9. Existing per-pid `/proc` files that telem could read with no kernel
   change are listed in 7.3.

---

## 7. `/proc` facilities in this kernel and config

### 7.1 Configuration

- `.config:568` `CONFIG_PROC_FS=y`
- `.config:569` `CONFIG_PROC_SYSCTL=y`
- `.config:570` `# CONFIG_SYSFS is not set`
- `rc.sysinit:6` mounts `/proc`.
- `fs/Makefile:58` `obj-$(CONFIG_PROC_FS) += proc/`. The built objects
  include `fs/proc/generic.o`, `kmsg.o`, `proc_misc.o` and `base.o`.
- `seq_file` is always built: `fs/Makefile:12` (`seq_file.o` in `obj-y`),
  and `fs/seq_file.o` is present.

### 7.2 APIs available to a driver in 2.6.22

| API | Location | Notes |
|---|---|---|
| `create_proc_entry(name, mode, parent)` | `include/linux/proc_fs.h:112`; `fs/proc/generic.c:669-699` | Returns a `proc_dir_entry`. If the caller leaves `proc_fops` NULL, it is set to `proc_file_operations` at registration (`generic.c:548-549`). |
| `read_proc` / `write_proc` callbacks | `proc_fs.h:43-45` (typedefs), `:64-65` (fields); driven by `proc_file_read` (`generic.c:52-...`, `:136-137` `n = dp->read_proc(page, &start, *ppos, count, &eof, dp->data);`) | One page (4 KB) is allocated per `read()` (`:76`) and filled in chunks of `PROC_BLOCK_SIZE` (3072, `:49`, `:80`). The three `*start` conventions are documented at `:89-135`. Binary content is allowed, since it is a byte copy. The offset is truncated to `off_t` and must stay under `MAX_NON_LFS` (`:69-73`). |
| `create_proc_read_entry(name, mode, base, read_proc, data)` | `proc_fs.h:164-168` (inline) | Wraps `create_proc_entry` and sets `read_proc` and `data`. |
| Custom `file_operations` | set `entry->proc_fops` after `create_proc_entry` | This tree does exactly that for `/proc/bus/input/devices` and `handlers` (`drivers/input/input.c:651-663`). It gives full control over `read`, `llseek` and `poll`, and over binary layout, with no page limit. |
| `seq_file` (`seq_open`, `seq_read`, `single_open`) | `include/linux/seq_file.h:34-35`, `:47` | Available. Text-oriented, with record iteration. |
| `proc_create()` (public, with fops) | — | **Not in 2.6.22.** The name exists only as a static helper inside `generic.c`, called at `:687`. |
| `/proc/kmsg`, `syslog(2)` | `fs/proc/kmsg.o` built; `kernel/printk.c` | The 16 KB ring, with the saturation shown in 6.1. |
| debugfs, sysfs | — | Absent (`CONFIG_SYSFS` off; no debugfs). |

### 7.3 Per-task `/proc` files that exist without kernel changes

- `/proc/<pid>/status` shows `SigPnd:`, `ShdPnd:`, `SigBlk:`, `SigIgn:` and
  `SigCgt:` (`fs/proc/array.c:275-279`), plus `State:` (`:167`). This
  exposes a pending signal on the poll thread directly (section 2).
- `/proc/<pid>/stat` includes a numeric `wchan` (`fs/proc/array.c:317`,
  `:392-393` `wchan = get_wchan(task);`). Without `CONFIG_KALLSYMS`
  (`.config:170`), MIPS `get_wchan` returns `thread_saved_pc(task)` with no
  unwinding (`arch/mips/kernel/process.c:441-465`), and that address can be
  looked up in `System.map` off the device. `thread_saved_pc` needs
  `schedule_mfi.pc_offset >= 0` (`:359-360`). Without kallsyms,
  `frame_info_init` scans at most 128 instructions of `schedule()`
  (`:294-296`, `:324-335`) and prints "Can't analyze schedule() prologue"
  on failure (`:341-342`). **UNVERIFIED** whether that works on this build;
  the boot log would show.
- `/proc/<pid>/wchan` as a file exists only with `CONFIG_KALLSYMS`
  (`fs/proc/base.c:1989-1990`), so **it is absent here**.
- The poll thread's pid is not fixed. It can be identified as a `swapper`
  task with ppid 1 (1.2). The UART3 TX thread looks the same.

---

## 8. Method, reproducibility and scratch contents

All files are in `/home/ubuntu/psp/handoff/recon/scratch-input/`:

| File | What it is |
|---|---|
| `initramfs/` | `cpio -idm` of `build/linux/psp-initramfs.cpio`. Device nodes could not be created (mknod EPERM); the listing comes from `cpio -itv`. |
| `psposk2.text`, `pspmd.text`, `*.data` | Segments of each bFLT file: text is `[0x40, data_start)`, data is `[data_start, data_end)`. |
| `psposk2.dis`, `pspmd.dis` | `mipsel-linux-uclibc-objdump -D -b binary -m mips:3000 -EL --adjust-vma=0x40`, run in `psp-build:bullseye`. Owned by root, because the container wrote them. |
| `annot.py`, `*.ann` | Adds syscall-stub names to `lw t9,N(gp)` calls via the GOT, and string guesses to `addiu` immediates (GOT page + `%lo`). The address mapping is linked = `0x400000 + off - 0x40` (checked: the GOT holds `0x400000`, `0x410000`, `0x420000`, and the `/dev/joypad` string at file offset `0x1eed0` resolves from page `0x420000` + `-4464`). |
| `gotref.py`, `*.calls` | Helper and the extracted call-site contexts. |
| `telem.gdb.dis` | `objdump -d` of `/home/ubuntu/psp/telem/telem.gdb`, used for the FP recount. |

Scope limits: I did not disassemble busybox. I did not trace `psposk2` or
`pspmd` beyond the call sites cited. I did not boot anything. There is no
hardware or Memory Stick access.

---

## 9. UNVERIFIED items, collected

1. The normal values of raw `rx_buf[5]` bits 6 and 7 and `rx_buf[6]`, and so
   whether bit 23 (MOUSE_MODE) is ever forced by the syscon word (1.4).
2. Which `psposk2` runtime errors lead to teardown, and so to a `/dev/joypad`
   close (1.6, 5.1).
3. Busybox 1.7.0 init details: `setsid()` in init and children, any tty
   opened without `O_NOCTTY`, and the `kill(-1)` shutdown sequence (2.2).
4. Whether `pspmd` touches `/dev/vcs`, and so the console semaphore, on
   every cursor move (5.2).
5. The real jiffy length. It depends on the true CP0 Count rate versus the
   "measured" 220,912,896/s, plus handler latency (section 4).
6. telem's real loop period on hardware (6.1).
7. How telem was started on the device, and the exact kernel command line
   (5.0).
8. Whether `get_wchan` gives usable values without kallsyms on this build
   (7.3).
9. `psposk2`'s HOME+CIRCLE+CROSS → `fork`/`execve("/sbin/poweroff")` path,
   and what `fork` does on this no-MMU kernel (5.1).

## 10. Open questions this recon adds (for the orchestrator to route to the operator)

| # | Question | Why |
|---|---|---|
| QB1 | In the runs where telem showed death, was **mouse mode** on, and did **L or R trigger presses** stop bumping telem's INPUT? | telem sees mousedev directly, bypassing both daemons. If trigger presses still counted after "death", the kernel thread was alive and the fault was above it (B6). If they stopped, the thread or mousedev was dead. Outside mouse mode telem's INPUT depended only on the OSK. |
| QB2 | After death, was the OSK overlay still drawn and did its highlight move? Was the text console still printing, for example a blinking cursor? | A torn-down `psposk2` is the trigger for B3. A stuck console semaphore would freeze the vcs users while the framebuffer (telem) keeps going. |
| QB3 | How large are the recovered `/ms0/kmsg.txt` files? | If 16384 bytes, observation 5 carries no information after the ring filled (B5). |
| QB4 | Does telem's `ELAP` agree with a stopwatch over a few minutes? | It checks the jiffy length assumption behind every rate figure (section 4). |
