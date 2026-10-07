# RUNBOOK: instrumented input-death run (candidate B)

This is the operator's procedure for the single hardware run. Design:
`design/candidate-B.md`. If this candidate is chosen, rename this file to
`design/RUNBOOK.md`.

Nothing here needs you to type anything on the PSP. All recording is
automatic from boot. Your job is to reproduce the conditions under which
input died before, to do the scripted button pattern after death, and to take
photographs.

---

## A. Before the run (at the computer)

1. **Do not touch the folder `PSP/GAME/uClinux/`.** Do not use `uClinux_FIX`
   or `uClinux_WIP` either.
2. Copy the release folder to the stick as `PSP/GAME/uClinux_TRACE/`. It must
   contain exactly these files:
   `EBOOT.PBP`, `kmodlib.prx`, `pspboot.conf`, `vmlinux-0.22.bin`.
   Check the release checksum of `vmlinux-0.22.bin` against the gate log (R3).
3. Check the stick has **at least 1 GB free**.
4. If a folder `PSPTRACE` already exists at the root of the stick from a
   rehearsal, leave it. The run creates a new numbered file.
5. Have ready:
   - a charged battery;
   - a stopwatch;
   - a phone camera;
   - this page;
   - paper to write stopwatch times.

## B. Boot and self-test (first 2 minutes)

| Step | Do | Expect |
|---|---|---|
| B1 | In the XMB, **start the stopwatch at the same moment** you press × on `uClinux_TRACE`. | Boot text appears. |
| B2 | Wait. | Within about 30 s the screen changes to the PSPTRACE display (full screen, pulsing border, heartbeat block top-right). |
| B3 | Look at the top line. | It shows `PSPTRACE Rnnn/01` and a list of self-test items turning green: K, REC, CTX, WD, MS. |
| B4 | **Press and hold × (CROSS) for 2 seconds**, then release. | The `RAW` line changes while you hold it and shows `X`. The BTN item turns green. The top line shows **`SELFTEST PASS`** in green. |
| B5 | **Photograph the whole screen with the stopwatch visible in the frame** (photo P1). Write down the stopwatch time. | |

**Abort rule.** If `SELFTEST PASS` is not shown within **90 seconds of
pressing × in the XMB**:

1. Photograph the screen.
2. Hold the power switch or pull the battery.
3. Report.

This does **not** count as the run.

Also abort if any line is red at this point (for example `MS ... ERR`,
`LOST`, or `SYNC` above 2 s).

## C. Calibration (about 1 minute, right after SELFTEST PASS)

Hold each for about 1 second, release for about 1 second, in this order. Do
not hurry and do not combine buttons.

1. D-pad UP, RIGHT, DOWN, LEFT.
2. △, ○, ×, □.
3. L trigger, R trigger.
4. START.
5. VOL+, VOL−.
6. NOTE (♪) button, SCREEN button.
7. Analog stick fully UP 2 s, fully RIGHT 2 s, fully DOWN 2 s, fully LEFT 2 s,
   then release.
8. **HOLD switch ON for 3 seconds, then OFF.**
9. Last: press **SELECT once** to enter mouse mode. The display shows
   `MODE MOUSE`, and the mouse cursor is usable.

## D. Normal use until input dies (up to 30 minutes)

Reproduce what you were doing when input died in the earlier telem sessions.
The recovered logs show about 4 input events per second at the moment of
death.

- **Keep clicking the L trigger about 4 times per second, and move the
  analog stick now and then.** Watch the `IN` counter rise.
- You may rest, but for **no more than 10 seconds at a time**.
- Do not start `telem` or any other program. Do not press HOME.
- At **minute 5 on the stopwatch**, photograph the screen with the stopwatch
  in frame (photo P2).
- Keep an eye on the `SYNC ... MAX` field. If `MAX` goes above 2 s, write down
  the value. The final hands-off wait (step E7) must then be at least 30 times
  that value.

**How to tell input has died:**

- your clicks and stick movements stop having any effect; or
- the `IN` counter stops rising while you click; or
- the display shows `DEAD?` in red at the top right.

Any one of these is enough. When it happens, **write down the stopwatch time
straight away** and go to E.

## E. After death: scripted pattern (about 3 minutes)

Do each step fully. Hold means hold steadily for the stated time. Release
means hands off the buttons for the stated time.

| Step | Do | Photo |
|---|---|---|
| E1 | Photograph the screen immediately (photo P3), stopwatch in frame. | P3 |
| E2 | Keep clicking L trigger about 4/s for **10 s** (as before). | |
| E3 | Release everything for **5 s**. **Photograph during this release** (photo P4). | P4 |
| E4 | Hold **×** 5 s. **Photograph while holding** (photo P5, the RAW line must be readable). Release 5 s. | P5 |
| E5 | Hold **D-pad RIGHT** 5 s, release 5 s. | |
| E6 | Push **analog stick fully UP** 5 s, release 5 s. | |
| E7 | Hold **L and R triggers together** 5 s, release 5 s. | |
| E8 | **HOLD switch ON** 5 s, then **OFF**, wait 5 s. Note whether anything visible happened. | |
| E9 | Press and hold **VOL+** 3 s, release 5 s. Note whether anything visible happened. | |
| E10 | Press **SELECT** once, wait 5 s, press **SELECT** once more, wait 5 s. | |
| E11 | Repeat E4 and E5 once. | |
| E12 | **Hands completely off for 60 seconds** (longer if step D said so). Do not touch anything. | |
| E13 | Photograph the screen with the stopwatch (photo P6). The heartbeat should still be pulsing. | P6 |
| E14 | **Pull the battery.** Write down the stopwatch time. | |

Notes:

- Do not press the power switch or HOME before pulling the battery.
- If the display has frozen (heartbeat not pulsing), still do E2 to E13 in
  full. Photograph the frozen screen and note when it froze.
- If the screen goes dark, still do E2 to E14 and note when it went dark.

## F. If input has not died by minute 30

1. Do the whole of section E anyway. It is the healthy control sample.
2. Pull the battery.
3. Write "no death by 30:00" in your notes.

## G. After the run (at the computer)

1. **Do not let any tool repair the stick.** If Windows or macOS offers to
   repair it, decline.
2. **If you can, make a raw image of the whole stick first.** For example on
   macOS: `diskutil list` to find the device, `diskutil unmountDisk`, then
   `sudo dd if=/dev/rdiskN of=stick.img bs=1m`. Keep the image. Skip this step
   if you are unsure; do not risk the stick.
3. Copy the whole folder `PSPTRACE` from the root of the stick.
4. Return all of the following:
   - the image (if made) and the `PSPTRACE` folder;
   - photos P1 to P6, with their stopwatch times;
   - your written times: death noticed, battery pull;
   - answers to E8 and E9 (did HOLD or VOL+ do anything visible?);
   - anything you did differently from this page.
5. You may then boot the baseline `uClinux` folder or the XMB normally.
