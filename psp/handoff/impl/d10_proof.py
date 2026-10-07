#!/usr/bin/env python3
"""D10 proof for the PSC kernel (DESIGN 2.1 G2 criteria, 7.2).

usage: d10_proof.py BASE_VMLINUX BASE_SYSTEM_MAP NEW_VMLINUX NEW_SYSTEM_MAP OUT.txt

Disassembles Syscon_cmd from both images with the tree's own objdump (in the
psp-build:bullseye container), extracts every instruction on a control-flow
path from S5 (the load of 0xbe240004, syscon.c:102) to S20 (the GPIO3-low
store, syscon.c:222), including the -3 and -4 exits up to the point where
they leave the transaction, lists both in a canonical order (depth first from
S5, fall-through first), and compares them:
  1. instruction by instruction with stack offsets normalised;
  2. modulo a consistent register renaming (a bijection).
It also checks the assumptions of the exit hand-off asm (syscon.c
PSC_XFER_OUT): on every path from the receive loop and the retry test to the
hand-off, no instruction writes $8 (t0, the receive loop's i + 2) or $24
(t8, retry_cnt), and the slot offsets the asm reads are the offsets the
window stores to. Exit status 0 when the window is identical apart from
stack offsets and register renaming and the hand-off checks pass.
"""
import re, subprocess, sys

COND = {'beq', 'bne', 'beqz', 'bnez', 'bltz', 'bgez', 'blez', 'bgtz'}
LIKELY = {'beql', 'bnel', 'beqzl', 'bnezl', 'bltzl', 'bgezl', 'blezl', 'bgtzl'}
UNCOND = {'b', 'j'}
BR = COND | LIKELY | UNCOND
REGS = r'\b(zero|at|v[01]|a[0-3]|t[0-9]|s[0-8]|k[01]|gp|sp|fp|ra)\b'
LINE = re.compile(r'^\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)$')

def sym(mapfile, name):
    addrs = []
    for l in open(mapfile):
        a, t, n = l.split()[:3]
        addrs.append((int(a, 16), n))
    addrs.sort()
    for i, (a, n) in enumerate(addrs):
        if n == name:
            return a, addrs[i + 1][0]
    raise SystemExit('no symbol %s in %s' % (name, mapfile))

def objdump(vmlinux, start, stop):
    host = vmlinux
    if not host.startswith('/home/ubuntu/psp/'):
        raise SystemExit('vmlinux must be under /home/ubuntu/psp')
    inner = '/work/' + host[len('/home/ubuntu/psp/'):]
    cmd = ['sudo', 'docker', 'run', '--rm', '--platform', 'linux/386',
           '-v', '/home/ubuntu/psp:/work:ro', 'psp-build:bullseye', 'bash', '-c',
           'export PATH=/work/staging_dir/bin:/work/staging_dir/usr/bin:$PATH; '
           'mipsel-linux-uclibc-objdump -d --start-address=0x%x --stop-address=0x%x %s'
           % (0xffffffff00000000 | start, 0xffffffff00000000 | stop, inner)]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

def parse(text):
    out = []
    for l in text.splitlines():
        m = LINE.match(l)
        if m:
            a, w, mn, ops = m.groups()
            out.append((int(a, 16), mn, ops.split('<')[0].strip(), l.rstrip()))
    return out

def bounds(ins):
    s = e = None
    for i in range(len(ins) - 2):
        if ins[i][1] == 'lw' and ins[i + 1][1] == 'andi' and ins[i + 1][2].endswith('0xffff') \
           and ins[i + 2][1] == 'sh' and ins[i + 2][2].endswith('(sp)'):
            s = i
            break
    for i in range(s, len(ins) - 4):
        if ins[i][1] == 'lui' and ins[i][2].endswith('0xbe58') and ins[i + 1][1] == 'li' \
           and ins[i + 1][2].endswith(',4') and ins[i + 2][1] == 'ori' and ins[i + 3][1] == 'sw' \
           and ins[i + 4][1] == 'sw':
            e = i + 4
    return s, e

def target(ins, idx, i):
    return idx.get(int(ins[i][2].split(',')[-1].strip(), 16))

def succ(ins, idx, i):
    mn = ins[i][1]
    if mn in BR:
        t = target(ins, idx, i)
        return ([i + 2] if mn not in UNCOND else []) + [t]
    return [i + 1]

def terminal(x):
    a, mn, ops = x[:3]
    if mn in ('jr', 'jal', 'jalr'):
        return True
    if mn == 'addiu' and ops.startswith('sp,sp,'):
        return True
    if mn == 'lw' and re.match(r'(s[0-8]|ra|fp),-?\d+\(sp\)$', ops):
        return True
    return False

def window(ins):
    s, e = bounds(ins)
    idx = {x[0]: k for k, x in enumerate(ins)}
    order, seen = [], set()
    def walk(i):
        while i is not None and i not in seen:
            if i != s and terminal(ins[i]):
                return
            seen.add(i)
            order.append(i)
            if i == e:
                return
            if ins[i][1] in BR:
                seen.add(i + 1)
                order.append(i + 1)
                nx = succ(ins, idx, i)
                for n in nx[:-1]:
                    walk(n)
                i = nx[-1]
            else:
                i += 1
    walk(s)
    pos = {i: k for k, i in enumerate(order)}
    res = []
    for k, i in enumerate(order):
        a, mn, ops, raw = ins[i]
        o = re.sub(r'-?\d+\(sp\)', 'S(sp)', ops)
        if mn in BR:
            parts = o.split(',')
            t = idx.get(int(parts[-1].strip(), 16))
            parts[-1] = ('C%d' % pos[t]) if t in pos else 'EXIT'
            o = ','.join(parts)
        res.append([mn, o, a, raw])
    for k in range(1, len(res)):
        if res[k - 1][0] in BR and res[k - 1][1].endswith('EXIT'):
            res[k][0], res[k][1] = '(exit-ds)', '-'
    return s, e, res

def compare(B, N):
    exact = len(B) == len(N) and all(x[:2] == y[:2] for x, y in zip(B, N))
    fwd, bwd, ok, bad = {}, {}, len(B) == len(N), None
    if ok:
        for k, (x, y) in enumerate(zip(B, N)):
            rx, ry = re.findall(REGS, x[1]), re.findall(REGS, y[1])
            if x[0] != y[0] or re.sub(REGS, 'R', x[1]) != re.sub(REGS, 'R', y[1]):
                ok, bad = False, k
                break
            for p, q in zip(rx, ry):
                if fwd.setdefault(p, q) != q or bwd.setdefault(q, p) != p:
                    ok, bad = False, k
    return exact, ok, bad, {p: q for p, q in fwd.items() if p != q}

def mmio_order(res, ins_regs):
    """the sequence of loads/stores through non-sp bases, by kind"""
    return [(x[0], re.sub(REGS, 'R', x[1])) for x in res
            if x[0] in ('lw', 'sw', 'sh', 'lhu') and not x[1].endswith('(sp)')]

def handoff_checks(ins, report):
    """$8 and $24 not written between the receive loop / retry test and the
    hand-off asm; slot offsets read by the asm = offsets written by the window."""
    idx = {x[0]: k for k, x in enumerate(ins)}
    # the hand-off asm starts with addiu sp,sp,-128
    h = [k for k, x in enumerate(ins) if x[1] == 'addiu' and x[2] == 'sp,sp,-128']
    if len(h) != 1:
        report.append('FAIL: hand-off asm (addiu sp,sp,-128) found %d times' % len(h))
        return False
    h = h[0]
    s, e = bounds(ins)
    ok = True
    # every instruction reachable from S20 along control flow before the
    # hand-off (the checksum, the 0x80/0x81 test, the -5 exit)
    # The walk does not follow the retry edge (a branch back to the attempt
    # top, before S5 in address order): a new attempt re-runs its own receive
    # loop, so the value at the hand-off is always the final attempt's.
    s5addr = ins[s][0]
    reach, stack = set(), [e]
    while stack:
        k = stack.pop()
        if k is None or k in reach or k >= len(ins):
            continue
        reach.add(k)
        if k == h:
            continue
        if ins[k][1] in BR:
            reach.add(k + 1)
            for n in succ(ins, idx, k):
                if n is not None and ins[n][0] < s5addr:
                    report.append('  retry edge not followed: %08x %s %s'
                                  % (ins[k][0], ins[k][1], ins[k][2]))
                    continue
                stack.append(n)
        elif ins[k][1] in ('jr', 'jal'):
            continue
        else:
            stack.append(k + 1)
    writes = []
    for k in sorted(reach):
        if k == h or k == e:
            continue
        a, mn, ops = ins[k][:3]
        dst = ops.split(',')[0] if ops else ''
        if mn in ('sw', 'sh', 'sb') or mn in BR or mn in ('jr', 'jal', 'nop'):
            continue
        if dst == 't8' and mn == 'addiu' and ops == 't8,t8,1':
            writes.append('  %08x %s %s (retry_cnt++ itself: allowed)' % (a, mn, ops))
            continue
        if dst in ('t0', 't8'):
            # annulled delay slot of a branch-likely: only on the taken
            # (retry) path, which leaves for the next attempt
            if k > 0 and ins[k - 1][1] in LIKELY:
                writes.append('  %08x %s %s (delay slot of %s: executed only on the taken (retry) path)'
                              % (a, mn, ops, ins[k - 1][1]))
                continue
            ok = False
            writes.append('  %08x %s %s  <-- WRITES %s on a path to the hand-off' % (a, mn, ops, dst))
    report.append('instructions on paths from S20 (%08x) to the hand-off (%08x): %d'
                  % (ins[e][0], ins[h][0], len(reach)))
    report.append('writes of t0 / t8 on those paths: %s' % ('none' if not writes else ''))
    report.extend(writes)
    # t8 is incremented in place on the 0x80/0x81 path (addiu t8,t8,1): that
    # is retry_cnt itself, so it is listed but allowed
    return ok

def slot_check(N, nins, report):
    """The hand-off asm reads gin, spin, spin_ack, dlast, st9, sttx at
    128 + their offsets; the window writes them: gin and dlast/st9/sttx are
    the four sh to stack slots in canonical order, spin and spin_ack the two
    stores of the SPIN_MAX register (the first and the last such sw)."""
    sh = [int(re.search(r',(-?\d+)\(sp\)', x[3].split('\t')[-1]).group(1))
          for x in N if x[0] == 'sh' and '(sp)' in x[3]]
    c8 = [x for x in N if x[0] == 'sw' and '(sp)' in x[3]]
    maxreg = None
    for x in c8:
        ops = x[3].split('\t')[-1]
        if not ops.startswith(('v0', 'v1', 'zero')):
            maxreg = ops.split(',')[0]
            break
    sw = []
    for x in c8:
        ops = x[3].split('\t')[-1]
        if ops.split(',')[0] == maxreg:
            off = int(re.search(r',(-?\d+)\(sp\)', ops).group(1))
            if off not in sw:
                sw.append(off)
    want = None
    if len(sh) >= 4 and len(sw) == 2:
        want = [sh[0], sw[0], sw[1], sh[1], sh[2], sh[3]]
    h = [k for k, x in enumerate(nins) if x[1] == 'addiu' and x[2] == 'sp,sp,-128'][0]
    got = []
    for x in nins[h:h + 60]:
        if x[1] == 'jal':
            break
        m = re.match(r'at,(\d+)\(sp\)$', x[2])
        if x[1] in ('lhu', 'lw') and m:
            got.append(int(m.group(1)) - 128)
    names = ['gin', 'spin', 'spin_ack', 'dlast', 'st9', 'sttx']
    report.append('window slot stores (gin, spin, spin_ack, dlast, st9, sttx): %s' % want)
    report.append('hand-off reads (offset - 128), same order:                  %s' % got)
    ok = want is not None and want == got
    report.append('slot offsets agree: %s' % ('YES' if ok else 'NO'))
    return ok

def main():
    bv, bm, nv, nm, out = sys.argv[1:6]
    bs, be = sym(bm, 'Syscon_cmd')
    ns, ne = sym(nm, 'Syscon_cmd')
    btxt, ntxt = objdump(bv, bs, be), objdump(nv, ns, ne)
    bins, nins = parse(btxt), parse(ntxt)
    b0, b1, B = window(bins)
    n0, n1, N = window(nins)
    exact, renamed, bad, ren = compare(B, N)
    rep = []
    rep.append('D10 proof: Syscon_cmd transaction window S5..S20 (DESIGN 2.1, 7.2)')
    rep.append('=' * 72)
    rep.append('baseline: %s  Syscon_cmd %08x..%08x (%d bytes)' % (bv, bs, be, be - bs))
    rep.append('new:      %s  Syscon_cmd %08x..%08x (%d bytes)' % (nv, ns, ne, ne - ns))
    rep.append('S5 (lw 0xbe240004) .. S20 (sw 0x08 -> 0xbe24000c): baseline %08x..%08x, new %08x..%08x'
               % (bins[b0][0], bins[b1][0], nins[n0][0], nins[n1][0]))
    rep.append('instructions on S5..S20 paths incl. the -3/-4 exits: baseline %d, new %d' % (len(B), len(N)))
    rep.append('identical apart from stack offsets: %s' % ('YES' if exact else 'NO'))
    rep.append('identical apart from stack offsets and a consistent register renaming: %s'
               % ('YES' if renamed else 'NO (first difference at C%s)' % bad))
    if ren:
        rep.append('register renaming (baseline -> new): ' +
                   ', '.join('%s->%s' % kv for kv in sorted(ren.items())))
    bm_, nm_ = mmio_order(B, None), mmio_order(N, None)
    rep.append('non-stack loads/stores (MMIO and buffers) in the same order and form: %s'
               % ('YES' if bm_ == nm_ else 'NO'))
    nb = sum(1 for x in B if x[0] == 'jal' or x[0] == 'jalr')
    nn = sum(1 for x in N if x[0] == 'jal' or x[0] == 'jalr')
    rep.append('calls inside the window: baseline %d, new %d' % (nb, nn))
    rep.append('')
    rep.append('exit hand-off (syscon.c PSC_XFER_OUT) checks, new image:')
    ok_h = handoff_checks(nins, rep)
    ok_h = slot_check(N, nins, rep) and ok_h
    rep.append('hand-off checks: %s' % ('PASS' if ok_h else 'FAIL'))
    rep.append('')
    rep.append('Canonical listing (C index; S(sp) = a stack slot; EXIT = leaves the')
    rep.append('transaction; (exit-ds) = the delay slot of an exit branch, executed after')
    rep.append('the exit decision; !! = differs other than by stack offset)')
    rep.append('-' * 72)
    for k in range(max(len(B), len(N))):
        x = B[k] if k < len(B) else ['', '', 0, '']
        y = N[k] if k < len(N) else ['', '', 0, '']
        flag = '  ' if x[:2] == y[:2] else '!!'
        rep.append('%s C%-3d %08x %-8s %-22s | %08x %-8s %s' % (
            flag, k, x[2], x[0], x[1] if x[0] != '(exit-ds)' else x[3].split('\t')[-2] + ' ' + x[3].split('\t')[-1],
            y[2], y[0], y[1] if y[0] != '(exit-ds)' else y[3].split('\t')[-2] + ' ' + y[3].split('\t')[-1]))
    rep.append('')
    rep.append('Full listing, baseline Syscon_cmd (window instructions marked *)')
    rep.append('-' * 72)
    bset = {x[2] for x in B}
    for x in bins:
        rep.append(('* ' if x[0] in bset else '  ') + x[3])
    rep.append('')
    rep.append('Full listing, new Syscon_cmd (window instructions marked *)')
    rep.append('-' * 72)
    nset = {x[2] for x in N}
    for x in nins:
        rep.append(('* ' if x[0] in nset else '  ') + x[3])
    open(out, 'w').write('\n'.join(rep) + '\n')
    print('\n'.join(rep[:16]))
    sys.exit(0 if renamed and ok_h and bm_ == nm_ and nn == 0 else 1)

main()
