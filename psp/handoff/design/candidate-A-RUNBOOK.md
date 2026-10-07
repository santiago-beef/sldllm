# Runbook: PSP input-death trace run (candidate A)

This runbook goes with design [candidate-A.md](candidate-A.md). It is for
the human operator. You make one hardware run, ending with a battery pull.

Read it once end to end before you start. Keep it open, or printed, beside
you during the run.

Every step has a number. If something happens that no step covers, write
down the stopwatch time and what you saw, take a photograph, and carry on
with the next step that fits.

---

## What you need

- The PSP-1001, with a **fully charged battery**. The **AC adapter must stay
  unplugged for the whole run.** If the adapter is plugged in, pulling the
  battery does not cut power, and plugging or unplugging it also changes the
  syscon status byte.
- The Memory Stick, with **at least 64 MB free**.
- The deploy folder `uClinux_TRACE`, supplied by the agents. It contains
  `EBOOT.PBP`, `kmodlib.prx`, `pspboot.conf` and `vmlinux-0.22.bin`.
- A phone to use as a stopwatch and camera.
- A note of which buttons you pressed in your earlier telem sessions. If
  those differ from the L trigger used in step C1, use yours and write down
  which ones you used.

## Never press, at any point

| Buttons | Why |
|---|---|
| HOME + CIRCLE + CROSS together | The on-screen keyboard treats this as a power-off chord |
| L + R triggers together | This summons the on-screen keyboard and sends a middle click |
| SELECT, except the single tap in step B2 | Each change while SELECT is held toggles mouse mode |
| The power switch | Use the battery pull only |

---

## A. Before the run (on the Mac)

**A1.** Insert the stick. Do **not** touch the folders `PSP/GAME/uClinux`,
`uClinux_FIX` or `uClinux_WIP`. Copy the folder `uClinux_TRACE` to
`PSP/GAME/`. If a folder called `uClinux_TRACE` already exists there, stop
and ask the agents.

Check the new folder contains exactly the four files listed above. Check
`pspboot.conf` reads `kernel=vmlinux-0.22.bin` and
`cmdline=console=tty osk=Dv4`.

If the stick already has a folder called `PSCLOG`, leave it alone. The new
run takes the next free number.

**A2.** Eject the stick properly. Insert it in the PSP.

---

## B. Boot and self-test

**B1.** Launch `uClinux_TRACE` from the PSP menu. **Start the stopwatch at
the moment you press X to launch it.** This is time 0:00.

**B2.** Watch the boot text.

1. Within the first seconds you should see a line starting `PSC1 P2048 W128`.
   Photograph it.
2. A coloured band then appears at the top of the screen. This is the HUD.
3. Wait for the HUD's check line to show `KRN OK`, `POLL OK`, `WDOG OK`,
   `CTX OK`, `STICK OK` and `REC OK`. `WDOG` needs about 5 s.
4. Then **hold TRIANGLE for 2 seconds** and release it. `BTN OK` should
   appear, and the banner should turn green: `SELF-TEST PASS`.
5. Photograph the HUD. Note the stopwatch time.
6. Tap SELECT once, briefly, touching nothing else. The HUD should show
   `MOUSE ON`. If it shows `MOUSE OFF`, tap SELECT once more.

**B3. Abort rule. Aborting does not use up the run.** Power off (hold the
power switch) and report what you saw, with a photograph, if any of these
happens:

- The HUD has not appeared 2:00 after launch.
- Any of `KRN`, `POLL`, `WDOG`, `CTX`, `STICK` or `REC` is not OK within
  60 s of the HUD appearing.
- The HUD shows `NO STICK`, `STICK SPACE` or `WRITE ERR` in red.

**Exception.** If everything is OK except `BTN`, and holding TRIANGLE three
times does not give `BTN OK`, **do not abort.** Input may already be dead.
Go straight to section D.

---

## C. Healthy reference, then normal use

**C0. Reference pattern, once.** At about 30 s after PASS, do D1 to D5
from section D **exactly as written there**, while everything is working.
Note the stopwatch time at the start and at the end.

After D5 (HOLD switch back off), check the HUD shows `MOUSE ON` again.

**C1. Normal use until death, or until 20:00 on the stopwatch.** Keep
generating input as you did in your telem sessions. The default is
**L-trigger clicks about 4 times per second**, with mouse mode on. You may
also move the cursor with the analog stick. Avoid the forbidden buttons.

- Glance at `DELIV` on the HUD. While input is healthy it stays below
  about 1 s while you click.
- Photograph the HUD at 5:00, 10:00 and 15:00 on the stopwatch.
- If the HUD's `SYNC` shows more than 10 s in red, or `WRITER DEAD`, write
  down the time and keep going.

**C2. Signs of death.** Any one of these:

- `DELIV` keeps climbing past 2 s while you are clicking.
- The cursor no longer moves.
- L+R would not bring up the keyboard. Do not test this deliberately.

When you see a sign, **note the stopwatch time immediately (T_death)** and
photograph the HUD. Then go to section D.

**C3. No death by 20:00.** Do section D anyway, as a "no failure" control,
and report "no failure".

**C4. HUD freezes.** You can tell because the heartbeat block at the top
right stops blinking. Note the time, photograph, wait 30 s, photograph
again, then do D8 (pull the battery).

---

## D. Post-death script (about 75 s)

Use the stopwatch for the timings. Do not click the L trigger except in
D2. Do each step completely even if nothing seems to happen on screen.
**That is the point.**

**D1.** Hold TRIANGLE for 3 s. Release for 3 s. Do this twice.

**D2.** Hold the L trigger for 3 s. Release for 3 s.

**D3.** Hold VOL+ for 3 s. Release for 3 s.

**D4.** Push the analog stick fully right for 3 s and let it centre for
3 s. Then push it fully up for 3 s and let it centre for 3 s.

**D5.** Slide the HOLD switch on. Wait 5 s. Slide it off. Wait 5 s.

**D6.** Hold TRIANGLE, and while holding it photograph the HUD, making sure
the `RAW` line is readable. Release.

**D7.** Take your hands off the PSP for 10 s. Check the HUD's `SYNC` value
is below 3 s. If it is higher, wait up to 60 s for it to drop, noting the
value. Photograph the HUD.

**D8.** Note the stopwatch time. **Pull the battery.**

---

## E. After the run (on the Mac)

**E1. Make a raw copy of the stick before opening any file on it.** This is
the backup if the battery pull damaged the file system.

1. Insert the stick.
2. In Terminal, run `diskutil list`. Find the stick by its size. Call it
   `/dev/diskN`.
3. Run `diskutil unmountDisk /dev/diskN`.
4. Run `sudo dd if=/dev/rdiskN of=$HOME/psc-run1.img bs=1m`.
   - `if=` must be the **stick**.
   - Never swap `if` and `of`.
   - Doing it the right way round only reads from the stick.
5. Run `shasum -a 256 $HOME/psc-run1.img` and keep the output.

**E2.** Mount the stick normally. Copy the whole folder `PSCLOG` to the
Mac. Do not delete anything from the stick.

**E3.** Give the agents all of the following:

- the image file;
- the `PSCLOG` folder;
- all photographs;
- your stopwatch times (launch = 0:00, PASS, C0 start and end, T_death,
  D-script start, battery pull);
- the buttons you used in C1;
- anything you did differently from this runbook, or anything odd you saw.

---

## Timing summary

| Phase | Stopwatch |
|---|---|
| Launch | 0:00 |
| HUD and self-test PASS | normally within about 0:30 to 1:30. Abort rule in B3. |
| Reference pattern C0 | PASS + 0:30, lasting about 1:00 |
| Normal use C1 | until death or 20:00 |
| Post-death script D1 to D8 | about 1:15 |
| Worst-case data lost at the battery pull | about 1.5 s, which D7 ensures is past |
