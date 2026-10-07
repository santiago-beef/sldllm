#!/usr/bin/env python3
"""psc_maps.py - the one grammar of epcmap.txt and regmap.txt (DESIGN 10.6).

Shared by the writer, handoff/impl/mkmaps.py (kernel side), and the reader,
BuildInfo.load in pscdec_analysis.py (decoder).  G2 attempt 1 found the two
sides using different syntaxes (review F3, IMPLEMENTATION.md OD-4); since G2
attempt 2 both import this module, and the reader refuses a file that does not
follow it.

epcmap.txt
    first line   "# PSC-EPCMAP 2"
    rows         <start> <end> <label>        hex addresses, end exclusive
    labels       S0..S23, ENTRY, EXIT, REC inside Syscon_cmd (and the recording
                 wrapper / exit code), LEDRMW, otherwise a function name.

regmap.txt
    first line   "# PSC-REGMAP 2"
    rows         <steps> <var> <slot> <offset> <epc>   [# where, free text]
      steps      one label (S0..S23, LEDRMW, ...), a range "S16-S18" (inclusive),
                 or "all" = every step label S0..S23 of Syscon_cmd
      var        identifier [a-z_][a-z0-9_]*
      slot       r[N]      W r[N] / lc_r[N], N = 0..15: r[0..13] are $2..$15,
                           r[14] is $24 (t8), r[15] is $25 (t9) (DESIGN 1.3)
                 zero      the constant 0 ($0)
                 stack+N   byte N above Syscon_cmd's sp: not in a W record
                 -         not recoverable from a W record
      offset     signed decimal: the slot holds var + offset, so
                 var = slot - offset
      epc        "-" (anywhere in the step) or "<start>-<end>" (hex, end
                 exclusive): the row applies only when the EPC is in that
                 range; a row with a range wins over a row without one.
    Lines that are empty or start with '#' are comments.

The decoder computes, from a W record's EPC and r[] / lc_r[] (10.6):
    P2 (S11):  k = i // 2   (i = bytes the thread has pushed to the TX FIFO)
    P6 (S16-S18): j = i // 2 (i = bytes the thread has popped from the RX FIFO)
               pending = 1 between its status load and its data load
               (the window of the 10.7 rule "anything if between its status
               test and its data read"; red-team K2 / NW1)
    LEDRMW:    loaded = the value the read-modify-write loaded
"""

import re

EPCMAP_MAGIC = "# PSC-EPCMAP 2"
REGMAP_MAGIC = "# PSC-REGMAP 2"

STEP_LABELS = ["S%d" % i for i in range(0, 24)]
# W r[16] / lc_r[16] hold registers 2..15, 24, 25 in that order (DESIGN 1.3)
SLOT_REGS = list(range(2, 16)) + [24, 25]
REG_NAMES = {2: "v0", 3: "v1", 4: "a0", 5: "a1", 6: "a2", 7: "a3", 8: "t0", 9: "t1", 10: "t2",
             11: "t3", 12: "t4", 13: "t5", 14: "t6", 15: "t7", 24: "t8", 25: "t9"}

_VAR = re.compile(r'^[a-z_][a-z0-9_]*$')
_SLOT_R = re.compile(r'^r\[(\d+)\]$')
_SLOT_ST = re.compile(r'^stack\+(\d+)$')
_RANGE = re.compile(r'^S(\d+)-S(\d+)$')
_EPC = re.compile(r'^([0-9a-f]{8})-([0-9a-f]{8})$')


class MapError(Exception):
    pass


def slot_of_reg(regno):
    """r[N] slot name for a MIPS register number (2..15, 24, 25)."""
    return "r[%d]" % SLOT_REGS.index(regno)


def expand_steps(tok):
    if tok == "all":
        return list(STEP_LABELS)
    m = _RANGE.match(tok)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if not (0 <= a <= b <= 23):
            raise MapError("bad step range %r" % tok)
        return ["S%d" % i for i in range(a, b + 1)]
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', tok):
        raise MapError("bad step label %r" % tok)
    return [tok]


def parse_slot(tok):
    if tok == "-":
        return None
    if tok == "zero":
        return ("zero",)
    m = _SLOT_R.match(tok)
    if m:
        n = int(m.group(1))
        if n > 15:
            raise MapError("slot %r out of range (r[0]..r[15])" % tok)
        return ("r", n)
    m = _SLOT_ST.match(tok)
    if m:
        return ("stack", int(m.group(1)))
    raise MapError("bad slot %r" % tok)


class RegRow(object):
    __slots__ = ("steps", "var", "slot", "offset", "lo", "hi", "where", "line")

    def __init__(self, steps, var, slot, offset, lo, hi, where="", line=0):
        self.steps, self.var, self.slot, self.offset = steps, var, slot, offset
        self.lo, self.hi, self.where, self.line = lo, hi, where, line

    def value(self, regs):
        """var = slot - offset, from a W r[16] / lc_r[16] array; None if the
        slot is not in a W record."""
        if self.slot is None or self.slot[0] == "stack":
            return None
        v = 0 if self.slot[0] == "zero" else regs[self.slot[1]]
        return (v - self.offset) & 0xFFFFFFFF

    def __repr__(self):
        return "RegRow(%s %s %s %d %s)" % (",".join(self.steps), self.var, self.slot, self.offset,
                                         "-" if self.lo is None else "%08x-%08x" % (self.lo, self.hi))


def format_regrow(steps, var, slot, offset, epc=None, where=""):
    """One regmap row; epc = None or (start, end)."""
    if not _VAR.match(var):
        raise MapError("bad var %r" % var)
    parse_slot(slot)
    expand_steps(steps)
    e = "-" if epc is None else "%08x-%08x" % epc
    s = "%-8s %-10s %-9s %3d %-17s" % (steps, var, slot, offset, e)
    return (s + ("  # " + where if where else "")).rstrip() + "\n"


def parse_regmap_text(text, name="regmap.txt"):
    """-> dict label -> var -> [RegRow]; raises MapError on any bad line."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != REGMAP_MAGIC:
        raise MapError("%s: first line is not %r (grammar of psc_maps.py; a map in another syntax "
                       "is refused, G2 attempt 1 F3)" % (name, REGMAP_MAGIC))
    out = {}
    for n, line in enumerate(lines[1:], 2):
        body, _, where = line.partition("#")
        body = body.strip()
        if not body:
            continue
        p = body.split()
        if len(p) != 5:
            raise MapError("%s:%d: %d fields, want 5 (<steps> <var> <slot> <offset> <epc>): %r"
                           % (name, n, len(p), line))
        steps = expand_steps(p[0])
        if not _VAR.match(p[1]):
            raise MapError("%s:%d: bad var %r" % (name, n, p[1]))
        slot = parse_slot(p[2])
        try:
            off = int(p[3], 10)
        except ValueError:
            raise MapError("%s:%d: bad offset %r" % (name, n, p[3]))
        if p[4] == "-":
            lo = hi = None
        else:
            m = _EPC.match(p[4])
            if not m:
                raise MapError("%s:%d: bad epc range %r" % (name, n, p[4]))
            lo, hi = int(m.group(1), 16), int(m.group(2), 16)
            if hi <= lo:
                raise MapError("%s:%d: empty epc range %r" % (name, n, p[4]))
        row = RegRow(steps, p[1], slot, off, lo, hi, where.strip(), n)
        for lab in steps:
            out.setdefault(lab, {}).setdefault(p[1], []).append(row)
    return out


def parse_epcmap_text(text, name="epcmap.txt"):
    """-> sorted [(start, end, label)]; raises MapError on any bad line."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != EPCMAP_MAGIC:
        raise MapError("%s: first line is not %r" % (name, EPCMAP_MAGIC))
    out = []
    for n, line in enumerate(lines[1:], 2):
        body = line.split("#", 1)[0].strip()
        if not body:
            continue
        p = body.split()
        if len(p) != 3:
            raise MapError("%s:%d: %d fields, want 3 (<start> <end> <label>): %r" % (name, n, len(p), line))
        try:
            a, b = int(p[0], 16), int(p[1], 16)
        except ValueError:
            raise MapError("%s:%d: bad address in %r" % (name, n, line))
        if b < a:
            raise MapError("%s:%d: end before start" % (name, n))
        out.append((a, b, p[2]))
    out.sort()
    return out


def lookup(reg, label, var, epc):
    """The row of `var` for a W record whose EPC is `epc` with label `label`:
    a row whose epc range contains it, else a row without a range; None."""
    rows = reg.get(label, {}).get(var, [])
    best = None
    for r in rows:
        if r.lo is not None:
            if epc is not None and r.lo <= epc < r.hi:
                return r
        elif best is None:
            best = r
    return best


def value(reg, label, var, epc, regs):
    """(value or None, row or None)."""
    r = lookup(reg, label, var, epc)
    if r is None:
        return None, None
    return r.value(regs), r
