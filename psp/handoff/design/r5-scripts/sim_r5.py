#!/usr/bin/env python3
"""Discrete-time model of the revision-5 collector (DESIGN 15.6).
The resend='r4' option is a rough sketch, NOT a faithful model of revision 4,
and no figure in the design uses it.

Model of (DESIGN 4.3, 4.4, 4.6),
integer arithmetic only where it matters.  Used for: start-up first complete
drain (A5-3), IF4 sporadic/burst loss, IF9 bad data region, IF8/IF7 coverage.

Model (stated in DESIGN 15.x so it can be reproduced):
- P ring is the binding ring: 35.71 rec/s, 4096 entries; every other ring
  scales with it (POLL 24/48 of the cap, same span).
- A drain reads at most 48*m P records, m = min(4, max(1, ceil(dt/0.23))).
- A flush carries BPR bytes per P record drained + FIX bytes, padded to 512,
  minimum 1536; it is allowed only if seg_end + 40960 <= usable limit.
- Tick = 0.23 s + (flush + step + metadata bytes) / speed.
- Metadata: 1 KB per fsync (dir + FSINFO), +1 KB per allocating step (FAT x2).
- Durability (r5, F1(b)): a flush is durable iff its data write succeeded.
- Re-send (r5, range based): records of a failed flush are queued as a seq
  range and re-sent oldest first, sharing the drain cap; a record older than
  head - 4096 when it is needed is lost (counted).
- Creation (r5): step 0 = 1536 B (allocates; needs data+FAT+dir), then steps
  of k bytes; a step allocates if it crosses a 32 KB cluster start; a failed
  step whose FAT write failed stops growth; a data-only failure is retried in
  place up to 3 times, then stops; a stopped file with conf >= 42496 is
  prefix-usable; else abandoned.  Next attempt: whole-stick failure +10 s,
  metadata-only failure next tick.
- Two complete files ahead; one creation at a time.
"""
import math, random, sys

PR = 250.0 / 14 * 2          # P records per second (35.71)
N = 4096                     # P ring entries
BPR = 164                    # flush payload bytes per P record drained
FIX = 280                    # per-flush fixed bytes (UHB, PAD hdr, STATS share)
SEG = 2097152
HDR = 1536
CL = 32768
FLUSHMAX = 40960
TBASE = 0.23
THREAD_START = 3.0

def pad512(b):
    b = max(1536, b)
    return (b + 511) // 512 * 512

def r8k(b):
    return max(8192, min(65536, (b + 8191) // 8192 * 8192))

class F:
    def __init__(s, idx):
        s.idx = idx; s.conf = 0; s.complete = False; s.stopped = False
        s.abandoned = False; s.used = False; s.retries = 0; s.bad = False
    def limit(s):
        return SEG if s.complete else s.conf

def run(speed, collector_start=40.0, dur=1800.0, fail='none', lam=98/1800.0,
        burst=None, step_rule='need', seed=1, if9=None, escape=True,
        resend='range', gate_only_start=False, verbose=False):
    rnd = random.Random(seed)
    t = collector_start
    head = (collector_start - THREAD_START) * PR      # float
    pos = 0.0                                          # drain position (seq)
    lost = 0.0
    pending = []                                       # [start, end) seq ranges
    files = []
    active = None; creating = None; next_attempt = t
    seg_end = HDR
    last_drain = t - TBASE
    first_flush = None; first_complete = None
    hold_start = None; max_hold = 0.0
    consec_data_fail = 0
    resend_flag = False
    last_ok = True
    nfiles = 0
    tick = 0
    if head > N:
        lost += head - N; pos = head - N
    while t < collector_start + dur:
        tick += 1
        dt = t - last_drain
        m = min(4, max(1, math.ceil(dt / TBASE - 1e-9)))
        last_drain = t
        snap_head = head
        # ---- failure decision for this tick (whole-tick model) ----
        def fails(op_time, t0):
            if fail == 'none':
                return False
            if fail == 'burst':
                b0, bl = burst
                return b0 <= t0 < b0 + bl
            if fail == 'tick':
                return tick_fail
            if fail == 'op':
                return rnd.random() < 1 - math.exp(-lam * op_time)
            return False
        tick_fail = False
        if fail == 'tick':
            tick_fail = rnd.random() < 1 - math.exp(-lam * max(dt, TBASE))
        # ---- switch / hold ----
        def usable(f):
            return (not f.used) and (not f.abandoned) and (not f.bad) and f.limit() >= HDR + FLUSHMAX
        growing = active is not None and active is creating and not active.bad
        if (active is None or seg_end + FLUSHMAX > active.limit() or active.bad) and not growing:
            cand = [f for f in files if usable(f)]
            if cand:
                if active is not None:
                    active.used = True
                active = cand[0]; active.used = True; seg_end = HDR
                consec_data_fail = 0
            else:
                if active is not None and (seg_end + FLUSHMAX > active.limit() or active.bad):
                    active = None
        holding = active is None or seg_end + FLUSHMAX > active.limit()
        if holding and nfiles > 0:
            if hold_start is None:
                hold_start = t
        else:
            if hold_start is not None:
                max_hold = max(max_hold, t - hold_start); hold_start = None
        # ---- drain + flush ----
        io = 0.0
        flush_bytes = 0
        drained = []
        if not holding:
            cap = 48 * m
            # lost check: anything older than head - N
            floor = head - N
            newp = []
            for (a, b) in pending:
                if b <= floor:
                    lost += b - a
                elif a < floor:
                    lost += floor - a; newp.append((floor, b))
                else:
                    newp.append((a, b))
            pending = newp
            if pos < floor:
                lost += floor - pos; pos = floor
            if resend == 'range' and last_ok:
                while pending and cap > 0:
                    a, b = pending[0]
                    take = min(cap, b - a)
                    drained.append((a, a + take)); cap -= take
                    if a + take >= b: pending.pop(0)
                    else: pending[0] = (a + take, b)
            take = min(cap, snap_head - pos)
            if take > 0:
                drained.append((pos, pos + take)); pos += take
            nrec = sum(b - a for a, b in drained)
            flush_bytes = pad512(int(nrec * BPR + FIX))
            flush_bytes = min(flush_bytes, FLUSHMAX)
            ftime = (flush_bytes + 1024) / speed
            # IF9 region
            data_bad = False
            if if9 is not None:
                fi, lo, hi, t_on = if9
                if active.idx == fi and t >= t_on and seg_end < hi and seg_end + flush_bytes > lo:
                    data_bad = True
            ok = not fails(ftime, t) and not data_bad
            io += flush_bytes + 1024
            seg_end += flush_bytes
            if first_flush is None:
                first_flush = t - collector_start
            last_ok = ok
            if ok:
                consec_data_fail = 0
                if resend == 'r4' and resend_flag:
                    # r4: first success after failure is not durable; seek back
                    resend_flag = False
                    pending = [(min(a for a, b in drained), pos)]
                    # nothing durable this tick
                else:
                    pass  # drained records durable
                complete_now = (pos >= snap_head - 1e-9) and not pending
                if complete_now and first_complete is None:
                    first_complete = t - collector_start
            else:
                if data_bad:
                    consec_data_fail += 1
                    if escape and consec_data_fail >= 3:
                        active.bad = True
                if resend == 'range':
                    pending = sorted(pending + drained)
                else:
                    resend_flag = True
                    pending = sorted(pending + drained)
                    # r4 keeps resending from the oldest at next success
        # ---- creation ----
        step_bytes = 0
        complete_ahead = sum(1 for f in files if f.complete and not f.used)
        if creating is None and complete_ahead < 2 and t >= next_attempt and nfiles < 400:
            nfiles += 1
            creating = F(nfiles); files.append(creating)
        if creating is not None:
            f = creating
            if f.conf == 0:
                k = HDR
            else:
                room = (f.conf - seg_end) if (active is f) else SEG
                if holding:
                    k = 65536
                elif active is f:
                    if step_rule == 'r4':
                        k = 65536
                    elif step_rule == 'rev':
                        k = 65536 if room < 81920 else 8192
                    else:  # 'need'
                        k = r8k(81920 + 8192 - room) if room < 81920 else 8192
                else:
                    k = 8192
                k = min(k, SEG - f.conf)
            alloc = f.conf == 0 or ((f.conf + k - 1) // CL > (f.conf - 1) // CL)
            stime = (k + 1024 + (1024 if alloc else 0)) / speed
            io += k + 1024 + (1024 if alloc else 0)
            step_bytes = k
            if fail == 'op':
                dfail = rnd.random() < 1 - math.exp(-lam * k / speed)
                mfail = rnd.random() < 1 - math.exp(-lam * 1024 / speed)
            else:
                dfail = mfail = fails(stime, t)
            fatfail = alloc and mfail
            dirfail = (f.conf == 0) and mfail
            if not dfail and not fatfail and not dirfail:
                f.conf += k; f.retries = 0
                if f.conf >= SEG:
                    f.complete = True; creating = None
            else:
                whole = dfail and mfail
                if fatfail or dirfail:
                    stop = True
                else:
                    f.retries += 1; stop = f.retries > 3
                if stop:
                    f.stopped = True; creating = None
                    if f.conf < HDR + FLUSHMAX:
                        f.abandoned = True
                        next_attempt = t + (10.0 if whole else 0.0)
                    else:
                        next_attempt = t
        # ---- time ----
        dur_tick = TBASE + io / speed
        t += dur_tick
        head += PR * dur_tick
    if hold_start is not None:
        max_hold = max(max_hold, t - hold_start)
    # final lost check
    floor = head - N
    for (a, b) in pending:
        if b <= floor: lost += b - a
        elif a < floor: lost += floor - a
    return dict(lost_s=lost / PR, first_flush=first_flush,
                first_complete=first_complete, max_hold=max_hold, files=nfiles)

if __name__ == '__main__':
    pass
