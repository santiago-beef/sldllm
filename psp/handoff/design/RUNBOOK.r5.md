# Runbook: PSP input-death trace run

This is the operator's procedure for the single hardware run. It goes with
[DESIGN.md](DESIGN.md) (section 9 there summarises this page).
**Revision 5 (2026-10-05), for G1 round 6.** What changed for you since
revision 4:

- **A4:** if the stick has no folder `PSCLOG` at its root, **create it** on the
  Mac (one command). If it exists, leave it as before.
- **B2:** the boot line now starts `PSC5 P4096` (was `PSC4`).
- **Line 6** at the start reads like `MS PREP 012S 045KB/S`: seconds since the
  recorder started and the **measured speed of the stick**. Two new abort
  states at 3:00: **`MS SLOW`** (the stick is too slow for this recorder) and
  **`MS DIR FULL`** (the `PSCLOG` folder is too full).
- **`META` is no longer a spoiled run.** Line 6 may show `META` followed by a
  number, in normal colour: one sector of the stick's file table refuses
  writes, but the recording carries on safely. Note it; the raw image becomes
  mandatory; the run **counts**. The bottom band no longer shows `PSC MS META`.
- **E1/E2:** count only the files of **this** run (the `rrr` digits from line
  1), not files left over from rehearsals.

Unchanged since revision 4: A0 (the Mac must not mount the stick by itself),
256 MB free (A3), the self-test decision at **3:00**, the bottom third of the
screen belonging to the kernel, TRIANGLE held **whatever `POLL` shows**, the
second `PSC TEST` before TRIANGLE (B4), and the raw image being mandatory in the
cases listed in E2.

*Note for the G3 R4 read-through: also walk the "`POLL:RATE` only" branch of
the abort rule in section B.*

You make **one** run, ending with a battery pull. Nothing here needs you to
type on the PSP: recording starts by itself at boot and is saved to the Memory
Stick continuously. Your jobs: check the self-test, use the PSP the way you did
when input died before, do a fixed button pattern after it dies, and take
photographs.

Read this page once end to end before you start. Keep it open or printed
beside you. If something happens that no step covers, write down the
stopwatch time and what you saw, take a photograph, and carry on with the next
step that fits.

---

## Before you start: three questions for the agents

Answer these in writing before the run. The run is set up to match.

1. In the earlier telem sessions where input died, **which buttons** were you
   pressing? If it was not "L trigger clicks in mouse mode", say what it was.
2. Were those sessions on **battery** or with the **AC adapter plugged in**?
   ("Don't know" is a valid answer.)
3. Was **mouse mode** on (the cursor moving with the stick)?

The agents reply with the power source to use (A5). Without a reply, use
battery only.

## What you need

- The PSP-1001 with a **fully charged battery**; the AC adapter only if the
  agents said to run on AC (A5).
- The Memory Stick, with **at least 256 MB free** (checked in A3).
- The deploy folder `uClinux_TRACE` from the agents, containing exactly
  `EBOOT.PBP`, `kmodlib.prx`, `pspboot.conf` and `vmlinux-0.22.bin`, and the
  release note with the checksum of `vmlinux-0.22.bin`.
- A phone as stopwatch and camera, and paper. "With the stopwatch in frame"
  means the stopwatch must be readable in the photograph (a second phone or a
  clock works).
- The Mac used for the stick, with an administrator password (A0, E).

## The two displays

**The PSC display** (drawn by the recording program) fills the **top
two-thirds** of the screen: a pulsing border, a **blinking block at the top
right** (the heartbeat) and ten lines of text:

| Line | Looks like | What it tells you |
|---|---|---|
| 1 | `PSC T001003 SELFTEST` → `PSC T001003 SELFTEST PASS` | The file being written, and the self-test result. `DEAD?` in red means input may have died. `PSC NO KRN` means the wrong kernel |
| 2 | `KRN WDOG STICK REC` | Four self-test checks, each green (passed) or red |
| 3 | `PANEL SUP POLL BTN` | Four more checks. A red `POLL` may read `POLL:RATE`, `POLL:RET` or `POLL:NW0` |
| 4 | `RAW 00DF2F12 X80 Y7F` | The raw button data; ` TRI` appears while TRIANGLE is held |
| 5 | `MOUSE ON IN 00041 DELIV 00.4S` | Mouse mode; **`IN`** counts your L/R clicks (**only in mouse mode**); **`DELIV`** is seconds since the PSP last delivered a button change |
| 6 | `MS DUR 00.3S TMAX 0.3S ERR 000` | The recording's own view: `DUR` = seconds not yet safe on the stick. `CATCHUP` instead of `TMAX` while it catches up. `MS PREP 012S 045KB/S` (not red) at the start: seconds since the recorder started and the stick's measured speed. `MS DUR 00.3S META 0001F2A0` (not red): one sector of the stick's file table refuses writes; recording is still safe (C4). The whole line turns **red** after a failed save (for 10 s), and in the states `MS READ-ONLY`, `MS WAIT SPARE`, `MS NO STICK`, `MS SLOW 028KB/S`, `MS DIR FULL` |
| 7 | `SEG 003 USED 1.2M RDY 2` | Recording files: the one in use, how full it is, how many are ready. ` MAKING 45%` at the end is normal; ` WAIT` means a file could not be prepared |
| 8 | `REC LOST 0000 BAD 0000 STUCK 000` | Recording health; red if any number grows after the start |
| 9 | `UP 00123S WD 0995/1250 SUP OK` | Uptime; `SUP DEAD` or `SUP RUN` means the backup process is gone or has taken over |
| 10 | `CMD MED 0210US MAX 01830US C 0.8US` | Timings for the analysts |

**The kernel band** (drawn by the kernel itself, independently of the
recording program) is the **bottom third** of the screen. Normally it is
**black**. When it has something to say it shows the **kernel panel**: six
lines of letters and numbers with a **magenta border**. The first line starts
with one of:

- `PSC TEST`: the self-test (B3, B4), about 5 seconds each time. Normal.
- `PSC STALL`: the recording is more than 3 seconds behind. It also shows
  for a few seconds at the start while the recording prepares its first file
  and saves what happened since boot; that is normal (B3). At any other time
  see C4. The number after `DUR` is how many seconds of data are not yet safe.
- `PSC MS RO`: the Memory Stick has become **read-only**. The recorder can
  still fill the files it had prepared (a few minutes at most), then nothing
  more is saved; the panel photographs are then the only record (C4).

The panel's sixth line may contain `META` and a number: the same file-table
sector as line 6 of the PSC display. It does not by itself make the panel
appear.

The panel stays as long as its condition lasts, updating once a second, and
the band goes black again about a second after. White text in the band
without a magenta border is a kernel message, not the panel; photograph it.
A small blinking text cursor may sit in the band; ignore it.

## Never press, at any point

| Buttons | Why |
|---|---|
| HOME + CIRCLE + CROSS together | The on-screen keyboard treats this as a power-off chord |
| L + R triggers together | Summons the on-screen keyboard and sends a middle click |
| SELECT, **except** the single tap in B6, the single tap in the `POLL:RATE` case of the abort rule (B), and the single tap in D7a | Every change while SELECT is held toggles mouse mode |
| HOME | Not needed |
| **The POWER/HOLD slider pushed UP** (towards power) | On the PSP-1001 the slider on the right edge does both: **up is power, down is HOLD**. Up could switch the PSP off or suspend it. Only D7 uses the slider, and only **down**. If the slider on your unit is marked differently, stop and ask the agents before the run |

Do not start `telem` or any other program. The new recorder replaces it.

---

## A. Before the run (at the Mac)

**A0. Stop the Mac from mounting the stick by itself, and check it.** After the
run the stick must not be written by the Mac. You set this up now and test it.

1. Insert the stick. It appears in Finder (for example as `Untitled`).
2. In Terminal run `diskutil list`. Find the stick by its size (about
   124.8 GB). Note its disk name, for example `/dev/disk4`, and its partition,
   for example `/dev/disk4s1`.
3. Run `diskutil info /dev/disk4s1` (your partition) and find the line
   `Volume UUID:`. Write the long value down.
4. Run (replace `<UUID>` with that value):
   `echo "UUID=<UUID> none msdos rw,noauto" | sudo tee -a /etc/fstab`
   If there was no `Volume UUID` line, use instead
   `echo "LABEL=<name> none msdos rw,noauto" | sudo tee -a /etc/fstab`
   with the volume name exactly as Finder shows it.
5. Run `diskutil eject /dev/disk4` (your disk). Take the stick out, wait
   5 seconds, insert it again.
6. **Check:** after 10 seconds the stick must **not** appear in Finder, and
   `ls /Volumes` must not list it. Write down "A0 OK".
   If it **does** appear: write down "A0 FAILED", eject it, and tell the
   agents before going on. (If you go on anyway, E has a fallback.)
7. To copy the folder now, mount it by hand: `diskutil list` (the disk name
   may have changed), then `diskutil mount /dev/disk4s1`.

Leave the `/etc/fstab` line in place until E4.

**A1.** **Do not touch** `PSP/GAME/uClinux`, `uClinux_FIX` or `uClinux_WIP`.
Copy the folder `uClinux_TRACE` into `PSP/GAME/`. If a folder named
`uClinux_TRACE` already exists there, stop and ask the agents.

**A2. Checksum (mandatory).** Check that the new folder holds exactly the four
files listed above, and that `pspboot.conf` contains `kernel=vmlinux-0.22.bin`
and `cmdline=console=tty osk=Dv4`. Then run

```
shasum -a 256 /Volumes/<stick name>/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin
```

The printed value must equal the value in the release note and here:

`SHA256 vmlinux-0.22.bin = <filled in by the Stage 3 packager; G3 R3 checks it is filled and matches>`

If they differ, or this line still shows the placeholder, **stop** and ask
the agents.

**A3. Free space.** Run `df -h /Volumes/<stick name>`. `Avail` must show at
least 256M (a 30-minute run uses about 20 MB; the rest is a reserve for error
cases). If not, stop and ask.

**A4.** Run `ls /Volumes/<stick name>`. If there is a folder `PSCLOG` (from a
rehearsal), leave it as it is: the run creates new numbered files. If there is
**no** `PSCLOG`, create it now: `mkdir /Volumes/<stick name>/PSCLOG` (in
Terminal, not in Finder). Then run `ls /Volumes/<stick name>/PSCLOG` once to
check it exists.

**A5. Eject and set the power source.** Run `diskutil eject /dev/disk4`
(your disk). Insert the stick in the PSP.
- **Battery** (the default): check the AC adapter is unplugged.
- **AC**, only if the agents said so: plug the AC adapter in now and leave it
  in, battery in too. In D9 you will pull the battery **and then unplug the AC
  plug at once**.

---

## B. Boot and self-test (about 3 minutes)

**B1.** Start the stopwatch at the moment you press × on `uClinux_TRACE` in
the PSP menu. This is 0:00.

**B2.** Within the first seconds of boot text a line starting `PSC5 P4096`
appears. **Photograph it (photo P1).** If it has already scrolled away,
**carry on**: it is also saved on the stick.

**B3.** The PSC display appears in the top two-thirds of the screen. Line 1
reads `PSC Trrr--- SELFTEST`, where `rrr` is the run number (`001` unless
earlier rehearsal files are on the stick); the dashes become a number once
the first file is ready. Lines 2 and 3 show the eight check names; they turn
green one by one. For a few seconds (up to about a minute on a slow stick)
line 6 shows `MS PREP` with a seconds count and a speed, for example
`MS PREP 012S 045KB/S`, and the bottom band may show `PSC STALL`: both normal
at this stage. Then the band shows
**`PSC TEST`** for about 5 seconds, without warning: look at it if you can.
That is how `PANEL` turns green. Write down "PSC TEST seen" if you saw it.

**B4.** As soon as **`KRN WDOG STICK REC`** (line 2) and **`PANEL SUP`**
(line 3) are all green, **look at the bottom band**: it shows **`PSC TEST`
again for about 5 seconds**. Write down "PSC TEST seen" if you have not
already. Then **hold TRIANGLE for 2 seconds, whatever `POLL` shows**, and
release. Line 4 should show `TRI` while you hold and `BTN` turns green. If
`BTN` stays red, release for 2 seconds and hold again; at most three holds.

**B5.** When line 1 shows **`SELFTEST PASS`** in green, **photograph the whole
screen with the stopwatch in frame (photo P2)**. Write down the time.

**B6.** Tap **SELECT once**, briefly, touching nothing else. Line 5 should read
`MOUSE ON`. If it reads `MOUSE OFF`, tap SELECT once more. Then go straight to
**C0**.

### Abort rule (an abort does not use up the run)

**The decision is taken at 3:00 on the stopwatch**, not earlier.

**Abort** (photograph the screen, pull the battery, report) if any of these
holds:

- At 3:00, line 1 does not show `SELFTEST PASS`, and the exception below does
  not apply.
- At 3:00, line 6 shows `MS NO STICK`, `MS SLOW` or `MS DIR FULL`, or line 1
  shows `PSC NO KRN`, or any of `KRN`, `WDOG`, `STICK`, `REC`, `PANEL`, `SUP`
  is still red. (Write down what line 6 shows: `MS SLOW` means this stick is too
  slow for the recorder, `MS DIR FULL` that the `PSCLOG` folder is too full;
  the agents will advise.)
- The PSC display never appears.
- **You never saw a `PSC TEST` band** (B3 or B4) although `PANEL` is green,
  **unless** the early-death exception below applies. The exception wins:
  write down "PSC TEST not seen" and go to section D.
- The PSP switches off, suspends, or goes black and stays black **before
  input has died** (for example after an accidental push of the slider up).
  Note the time.

**Every abort:** leave the Memory Stick exactly as it is (delete nothing), do
**E1** (copy the `PSCLOG` folder, read-only), and give it to the agents with
your report.

**Exception: possible early death. Do not abort** if `KRN`, `WDOG`, `STICK`,
`REC`, `PANEL` and `SUP` are green but

- `POLL` is still red at 3:00 (write down which: `POLL:RATE`, `POLL:RET` or
  `POLL:NW0`), and/or
- `BTN` did not turn green after three TRIANGLE holds.

Input may already be dead (earlier sessions died before 36 s). Write down the
time and what lines 1-3 show, and go straight to **section D**. This counts as
the run.

**One exception to the exception (`POLL:RATE` only).** If at 3:00 the **only**
red item is `POLL` showing `POLL:RATE` (not `POLL:RET`, not `POLL:NW0`) and
`BTN` is green: tap **SELECT once**; line 5 must read `MOUSE ON` (if it reads
`MOUSE OFF`, tap once more); then click the L trigger five times. If the `IN`
number on line 5 goes up, input works: write down "POLL:RATE only, IN rising"
and the time, take photo P2, and continue with **C0**. If `IN` does not go up,
go to section D.

---

## C. Healthy reference, then normal use

**C0. Reference pattern, once, immediately after B6.** Do steps **D1 to D7
exactly as written in section D**, while input works. Write down the
stopwatch time at the start and the end. Do not do D0, D7a, D8 or D9. After D7
(slider back up from HOLD to the middle), check line 5 shows `MOUSE ON` again.
This gives the analysts the healthy version of the same pattern.

**C1. Normal use, until input dies or until 30:00.** Reproduce what you did
when input died in the earlier telem sessions (your answers to the three
questions). By default:

- keep mouse mode on;
- **click the L trigger about 4 times per second**;
- move the analog stick now and then;
- you may rest, but **for no more than 10 seconds at a time**;
- avoid every button in the "never press" table.

While input is healthy, `IN` keeps rising while you click and `DELIV` stays
below about 1 s.

**C2. Photographs.** At **5:00** and **15:00**, photograph the screen with the
stopwatch in frame (photos P3, P4).

**C3. Note, but do not act on:** `SUP DEAD` or `SUP RUN` on line 9; `WAIT`
on line 7; the `MS` line turning red; `META` appearing on line 6 (see C4); any
`REC` number growing. Write down the
time and what you saw, and keep going. `MAKING` on line 7, and `CATCHUP` for a
few seconds, are normal. If the screen goes dark (the console
blanks after about 10 minutes), keep clicking; it should come back. Write down
the time.

**C4. If the kernel panel appears, the PSC display freezes** (the blinking
block stops and the border stops pulsing), **or line 6 shows `META`:**

1. Write down the time. Photograph the screen, including the panel.
2. **If the panel's first line is `PSC MS RO`:** the stick is read-only. The
   recorder fills the files it had already prepared (a few minutes at most) and
   then nothing more is saved. **Treat the panel photographs as the record from
   now on.** Keep using the PSP normally (C1), **photograph the panel once a
   minute**, and at every step of section D if input dies. Do not wait for it
   to go away; it will not. At 30:00, or at death, continue as usual. The raw
   image (E2) is mandatory.
3. **`META` on line 6** (not red, for example `MS DUR 00.3S META 0001F2A0`),
   whether or not a panel shows: one sector of the stick's file table refuses
   writes. The recording carries on and is still safe; `DUR` tells you how far
   it is saved, as always. Write down the time and the number after `META`,
   take one photograph. It may disappear again later; note when. The raw image
   (E2) becomes mandatory. **The run counts**; D8 decides as usual. If a kernel
   panel is also showing, go on with item 4; otherwise carry on with C1.
4. For `PSC STALL`, or a frozen display: **keep using the PSP
   normally** and watch for up to **90 seconds**. It has **recovered** when,
   during 5 seconds of watching, all of these hold: the blinking block moves;
   no kernel panel (magenta border) appears at any moment; and line 6 is not red,
   does not show `CATCHUP`, and its `DUR` is below 3 s. If it recovers, note
   the time and carry on with C1; nothing is lost. If at 90 s the block moves
   and line 6 shows `CATCHUP`, keep going and watch for up to **45 seconds
   more**.
5. If it has not recovered by then: photograph the panel again and **carry on
   with C1 anyway**, photographing the panel every 5 minutes. The run is not
   over: the kernel keeps recording and the panel shows its state once a
   second. If input then dies, do section D and **photograph the panel at
   every step D0 to D8**. Whether this run counts is decided afterwards.

**C5. Signs that input has died.**

- `IN` stops rising while you click (in mouse mode), or `DELIV` keeps climbing
  past 2 s while you click;
- line 1 shows `DEAD?` in red;
- your clicks and stick movements stop having any effect on the cursor.

While the PSC display is live (the block blinks), the cursor sign alone is
**not** enough, because the display redraws the screen and the cursor can be
hard to see: confirm with one of the first two signs. If the display is frozen
or dark, the cursor sign (or your own sense that nothing responds) is enough.

When you see a sign, **write down the stopwatch time immediately (T_death)**
and go to section D.

**C6. No death by 30:00.** Do section D anyway as a healthy control, pull the
battery, and write "no death by 30:00".

---

## D. Post-death script (about 100 seconds, plus up to 2 min 15 s in D8)

"Hold" means hold steadily for the stated time; "release" means hands off.
Do every step completely even if nothing seems to happen on screen. **That is
the point:** the recording shows whether the PSP still sees your presses.

| Step | Do | Photo |
|---|---|---|
| **D0** | Photograph the screen at once, stopwatch in frame | P5 |
| **D1** | Keep clicking the L trigger about 4 times per second for **10 s** | |
| **D2** | Release everything for **5 s** | |
| **D3** | Hold **TRIANGLE** 3 s, release 3 s. Do this twice. **During the second hold, photograph the screen** so line 4 (`RAW`) is readable | P6 |
| **D4** | Hold **D-pad RIGHT** 3 s, release 3 s | |
| **D5** | Hold **VOL+** 3 s, release 3 s. Note whether anything visible happened | |
| **D6** | Push the **analog stick fully right** 3 s, let it centre 3 s. Then **fully up** 3 s, centre 3 s | |
| **D7** | Slide the **POWER/HOLD slider DOWN until it clicks into HOLD**, wait 5 s, let it back **up to the middle** (not further), wait 5 s. **Never push it up past the middle.** Note whether anything visible happened | |
| **D7a** | (Not in C0.) Tap **SELECT once**, then click the L trigger **5 times over 5 s**. Note whether the cursor moved and whether line 5 changed between `MOUSE ON` and `MOUSE OFF` | |
| **D8** | **Hands completely off for 30 s.** Then the **final check**: **(a)** watch the screen for **5 s**: the blinking block, the bottom band and line 6. **(b)** It **passes** only if during those 5 s: the block changed; **no kernel panel** (magenta border) was shown at any moment; and line 6 was **not red**, showed **none** of `CATCHUP`, `READ-ONLY`, `WAIT SPARE`, and showed `DUR` **below 3 s** (`META` on line 6 is allowed). If it passes: write down `DUR` and `TMAX` (or the `META` number) from line 6, photograph the screen with the stopwatch in frame (P7), go to D9. **(c)** Otherwise: write down the time, photograph the screen including the panel (P7a), and wait, hands off, **up to 90 s**, photographing the panel every 30 s and repeating the 5-second check. As soon as a check passes, do as in (b). If at 90 s the block is changing and line 6 shows `CATCHUP`, wait **up to 45 s more**, still checking. If no check passes by then (or the panel says `PSC MS RO`: then do not wait), photograph once more with the stopwatch in frame (P7b), **write down the number after `DUR` on the panel's first line** (or on line 6 if there is no panel), and go to D9 | P7 (P7a, P7b if needed) |
| **D9** | Write down the stopwatch time. **Pull the battery.** If on AC (A5), **unplug the AC plug immediately after** | |

During C0 you do D1 to D7 only: no photographs, no D7a, no D8, no pull.

If the display is frozen or dark when you reach section D, still do D0 to D9
in full and note it. D8 (c) then applies.

**Why D8 matters.** When the check passes, both the kernel (no panel) and
the recording program (line 6) confirm that everything up to about 4 seconds
before the check is safe, so the whole script is saved. When D8 (c) ends
without a pass, the number after `DUR` is how many seconds will be lost; the
panel photographs keep the kernel's view of that time.

---

## E. After the run (at the Mac)

The stick must **not** be written by the Mac. Thanks to A0 it should no longer
mount by itself; you mount it **read-only**.

**E1. Copy the recording (read-only).**

1. Insert the stick. It should **not** appear in Finder (A0).
   *If it does appear anyway* (A0 failed or was skipped): run `diskutil list`,
   then at once `diskutil unmountDisk /dev/diskN` (the stick's disk), write
   down "auto-mounted at E1", and do **E2 before anything else** (the image is
   then mandatory), then continue here.
2. Run `diskutil list`; find the stick (about 124.8 GB) and its partition, for
   example `/dev/disk4s1`.
3. Run `diskutil mount readOnly /dev/disk4s1`. If macOS offers to repair the
   stick, refuse (Ignore / Eject) and tell the agents.
4. Copy the folder: `cp -Rp /Volumes/<stick name>/PSCLOG ~/PSCLOG-run1`. Do not
   delete or rename anything on the stick.
5. Run `ls -l ~/PSCLOG-run1/T<rrr>*` with `<rrr>` the three digits after
   `PSC T` on line 1 of the PSC display during this run (for example `T001`),
   and write down every such file that is not exactly **2097152** bytes, with
   its size, and any copy error. **One** such file is normal (the file that was
   being prepared at the pull); if the agents' decoder later asks for the raw
   image because of it, make it then (E2). Files with other `T<rrr>` digits are
   from earlier boots: leave them out of this count.
6. Run `shasum -a 256 ~/PSCLOG-run1/*` and keep the output.
7. Run `diskutil unmountDisk /dev/disk4` (your disk).

**E2. Raw image of the whole stick.** **Mandatory** if any of these happened
(check your notes): after `SELFTEST PASS`, line 6 was red, or showed
`READ-ONLY`, `WAIT SPARE` or `META`, line 7 showed `WAIT`, or the kernel panel
appeared other than as `PSC TEST`; line 9 showed `SUP RUN` or `SUP DEAD`; D8
never passed; **more than one** file of this run in E1 step 5 was not 2097152
bytes, or a file failed to copy; the stick auto-mounted in E1. Otherwise it is optional
but welcome. If the agents' decoder later reports "RAW IMAGE REQUIRED", make
it then (the stick stays untouched until they confirm, E4).

It needs **at least 130 GB free** on the Mac (`df -h ~`, `Avail`) and up to
**3 hours** (the stick is about 124.8 GB; at 20-60 MB/s that is 35 minutes to
1 hour 45 minutes). If the Mac lacks the space, do not delete anything from
the stick; keep it untouched and tell the agents.

1. Run `diskutil list`; find the stick and call it `/dev/diskN`.
2. Run `diskutil unmountDisk /dev/diskN`.
3. Run `sudo dd if=/dev/rdiskN of=$HOME/psc-run1.img bs=1m`.
   - `if=` must be the **stick**. **Never swap `if` and `of`.** The right way
     round only reads from the stick.
   - Let it finish.
4. Run `shasum -a 256 $HOME/psc-run1.img` and keep the output.

**E3. Why read-only.** The recorder only ever writes into space of a file that
was already linked in the stick's file table and checked, so macOS cannot
reuse it for its own files. But if a write error ever hit the stick (the red
line 6, `WAIT`, `READ-ONLY`, `META`), part of that table may be stale or may
not list all recorded data, and
macOS could then write its own small files over recordings. That is why the stick is never mounted read-write after
the run, and why the image is mandatory in those cases.

**E4.** Remove the A0 line: run `sudo sed -i '' '/<UUID>/d' /etc/fstab` (the
value from A0 step 3; or the `LABEL=` text if you used that). Keep the stick
untouched until the agents confirm they have what they need.

**E5.** Give the agents:

- the `PSCLOG` copy and its checksums, and the image and its checksum if made;
- photos P1 to P7 (and P7a, P7b and every kernel panel photograph), with
  their stopwatch times;
- your times: launch (0:00), `SELFTEST PASS`, C0 start and end, T_death, start
  of D0, the D8 values (`DUR`, `TMAX`, or the `DUR` from the last panel), the
  battery pull;
- "A0 OK" or "A0 FAILED", "PSC TEST seen" (or "not seen"), every time `META`
  appeared or disappeared on line 6 with its number, the `MS PREP` speed you
  saw at the start, and whether VOL+ (D5), HOLD (D7) or SELECT (D7a) did
  anything visible;
- your answers to the three questions and the power source used;
- anything you did differently from this page and anything odd you saw (the
  panel outside the self-test, a frozen or dark display, `SUP DEAD`/`SUP RUN`,
  `WAIT` on line 7, red lines, `META`, growing `REC` numbers).

You may then boot the baseline `uClinux` folder or the XMB normally.

---

## Timing summary

| Phase | Stopwatch |
|---|---|
| Launch | 0:00 |
| `PSC5` line (P1) | first seconds (if missed, carry on) |
| `SELFTEST PASS` (P2) | normally before 2:00; decision at **3:00** (abort unless the early-death exception applies) |
| Reference pattern C0 | right after B6, about 1 minute |
| Normal use C1 | until death or 30:00; photos at 5:00 and 15:00 |
| Post-death script D0-D9 | about 1:40, plus up to 1:30 in D8 (c), or 2:15 if `CATCHUP` shows at 1:30 |
| Data lost at the battery pull | at most about 4 s when the D8 check passes; otherwise the `DUR` you wrote down in D8 (c) |
