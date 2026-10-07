#!/usr/bin/env python3
"""check_format.py - cross-check include/linux/psc_format.h against psc_format.py.

Default (host only, no compiler): parse the header text, compute the packed
layout of every struct (all members have explicit widths and the structs are
packed, DESIGN 1.0), and compare struct by struct, field by field
(name, offset, element type and signedness, count) with psc_format.py; then
compare every numeric constant that both define. Exits 0 only if all agree.

--cc additionally runs the target compiler (mipsel-linux-uclibc-gcc 4.2.1)
in the i386 build container on a generated probe that includes the header in
userland mode (as pscol will) and in kernel mode (-D__KERNEL__, the tree's
own include/ and asm-mips headers), emits sizeof/offsetof/signedness of
every field as data, and compares the compiler's layout with psc_format.py.
It also compiles the header's psc_crc32() with the container's native gcc
and checks it against zlib.crc32 on psc_format.CRC_VECTORS.

Usage: python3 check_format.py [--header PATH] [--cc]
"""

import argparse
import os
import re
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import psc_format as pf  # noqa: E402

DEFAULT_HEADER = "/home/ubuntu/psp/work/linux/include/linux/psc_format.h"
WORK = "/home/ubuntu/psp/work"
CONTAINER = ["sudo", "docker", "run", "--rm", "--platform", "linux/386",
             "-v", "/home/ubuntu/psp:/work:ro", "-v", "/home/ubuntu/psp/work:/work/work",
             "psp-build:bullseye", "bash", "-c"]

CTYPES = {"__u8": ("B", 1), "__s8": ("b", 1), "__u16": ("H", 2), "__s16": ("h", 2),
          "__u32": ("I", 4), "__s32": ("i", 4)}

# C struct -> (psc_format RECORDS key(s), flatten prefix rule)
STRUCT_MAP = {
    "psc_sc": ["SC", "M"], "psc_wext": ["WEXT"], "psc_w": ["W"], "psc_poll": ["POLL"],
    "psc_s": ["S"], "psc_stats": ["STATS"], "psc_ctl": ["CTL"],
    "psc_chunk_hdr": ["CHUNK_HDR"], "psc_block_hdr": ["BLK_HDR"],
    "psc_filehdr": ["FILEHDR"], "psc_uhb": ["UHB"],
}

errors = []


def err(msg):
    errors.append(msg)
    print("MISMATCH: " + msg)


# ------------------------------------------------------------------ parsing
def strip_comments(text):
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.S)


def parse_defines(text):
    """Object-like #defines -> raw value text (continuations joined)."""
    text = text.replace("\\\n", " ")
    defs = {}
    for m in re.finditer(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(\(?)(.*)$", text, re.M):
        name, paren, rest = m.group(1), m.group(2), m.group(3).strip()
        if paren:          # function-like macro: skip
            continue
        defs[name] = rest
    return defs


def eval_c(expr, defs, depth=0):
    """Evaluate a C integer constant expression made of literals and macros."""
    if depth > 20:
        raise ValueError("recursion")
    e = expr.strip()
    if e.startswith('"'):
        return bytes(e.strip('"'), "ascii").decode("unicode_escape")
    e = re.sub(r"\(\s*__u32\s*\)", "", e)
    e = re.sub(r"\b(0[xX][0-9A-Fa-f]+|\d+)[uUlL]+\b", r"\1", e)

    def sub(m):
        n = m.group(0)
        if n in defs:
            v = eval_c(defs[n], defs, depth + 1)
            if isinstance(v, str):
                raise ValueError("string in arithmetic")
            return "(%d)" % v
        raise ValueError("unknown name %s" % n)
    e = re.sub(r"\b[A-Za-z_]\w*\b", sub, e)
    if not re.fullmatch(r"[\s0-9xXa-fA-F()+\-*/%<>&|~^]*", e):
        raise ValueError("not a constant: %r" % expr)
    e = e.replace("/", "//")
    return eval(e, {"__builtins__": {}}, {})


def parse_structs(text, defs):
    structs = {}
    for m in re.finditer(r"struct\s+(psc_\w+)\s*\{(.*?)\}\s*PSC_PACKED\s*;", text, re.S):
        name, body = m.group(1), m.group(2)
        members = []
        for decl in body.split(";"):
            decl = " ".join(decl.split())
            if not decl:
                continue
            dm = re.fullmatch(r"(struct\s+psc_\w+|__[us](?:8|16|32))\s+(\w+)\s*(?:\[\s*([^\]]+)\s*\])?", decl)
            if not dm:
                err("%s: cannot parse member '%s'" % (name, decl))
                continue
            ctype, mname, count = dm.group(1), dm.group(2), dm.group(3)
            n = eval_c(count, defs) if count else 1
            if "bitfield" in decl or ":" in decl:
                err("%s.%s: bitfield" % (name, mname))
            members.append((ctype, mname, n, count is not None))
        structs[name] = members
    return structs


def layout(structs, name, prefix=""):
    """Flattened packed layout: list of (name, offset, code, count). Nested
    struct members are flattened with '<member>.' as in psc_format W_FIELDS."""
    out, off = [], 0
    for (ctype, mname, n, is_array) in structs[name]:
        if ctype.startswith("struct"):
            sub = ctype.split()[1]
            sublay, subsize = layout(structs, sub, prefix + mname + ".")
            assert n == 1
            out += [(fn, off + fo, c, k) for (fn, fo, c, k) in sublay]
            off += subsize
            continue
        code, size = CTYPES[ctype]
        if code == "B" and is_array:      # byte arrays are Python 's'
            out.append((prefix + mname, off, "s", n))
        else:
            out.append((prefix + mname, off, code, n))
        off += size * n
    return out, off


# ---------------------------------------------------------------- compare
def py_layout(key):
    fields = pf.RECORDS[key][1]
    tab = pf.offsets(fields)
    return [(n, tab[n][0], c, k) for (n, c, k) in fields]


def compare_layout(cname, clay, csize, key, source):
    plays = py_layout(key)
    psize = pf.RECORDS[key][2]
    ok = True
    if csize != psize:
        err("%s: %s size %d, psc_format %s %d" % (source, cname, csize, key, psize))
        ok = False
    if len(clay) != len(plays):
        err("%s: %s has %d fields, psc_format %s has %d" % (source, cname, len(clay), key, len(plays)))
        ok = False
    for c, p in zip(clay, plays):
        if c != p:
            err("%s: %s field %s != psc_format %s field %s" % (source, cname, c, key, p))
            ok = False
    return ok, len(clay)


# Constants whose Python name is not the C name minus "PSC_"
CONST_MAP = {
    "PSC_P_SIZE": pf.SC_SIZE,
    "PSC_P_ENTRIES": pf.RING_ENTRIES[pf.RING_P], "PSC_POLL_ENTRIES": pf.RING_ENTRIES[pf.RING_POLL],
    "PSC_W_ENTRIES": pf.RING_ENTRIES[pf.RING_W], "PSC_S_ENTRIES": pf.RING_ENTRIES[pf.RING_S],
    "PSC_M_ENTRIES": pf.RING_ENTRIES[pf.RING_M],
    "PSC_P_DIV4": pf.RING_DIV4[pf.RING_P], "PSC_POLL_DIV4": pf.RING_DIV4[pf.RING_POLL],
    "PSC_W_DIV4": pf.RING_DIV4[pf.RING_W], "PSC_S_DIV4": pf.RING_DIV4[pf.RING_S],
    "PSC_M_DIV4": pf.RING_DIV4[pf.RING_M],
    "PSC_CAP_P": pf.CAP[pf.RING_P], "PSC_CAP_POLL": pf.CAP[pf.RING_POLL],
    "PSC_CAP_W": pf.CAP[pf.RING_W], "PSC_CAP_S": pf.CAP[pf.RING_S], "PSC_CAP_M": pf.CAP[pf.RING_M],
    "PSC_SECTOR_SIZE": pf.SECTOR, "PSC_BLK_HDR_SIZE": pf.BLK_HDR_SIZE,
    "PSC_CHUNK_MAGIC": pf.CHUNK_MAGIC.decode(), "PSC_FILEHDR_MAGIC": pf.FILEHDR_MAGIC.rstrip(b"\0").decode(),
    "PSC_CHUNK_MAGIC_U32": int.from_bytes(pf.CHUNK_MAGIC, "little"),
    "PSC_PROC_P": pf.PROC_RING[pf.RING_P], "PSC_PROC_POLL": pf.PROC_RING[pf.RING_POLL],
    "PSC_PROC_W": pf.PROC_RING[pf.RING_W], "PSC_PROC_S": pf.PROC_RING[pf.RING_S],
    "PSC_PROC_M": pf.PROC_RING[pf.RING_M], "PSC_PROC_STATS": pf.PROC_STATS,
    "PSC_PROC_CTL": pf.PROC_CTL, "PSC_PROC_DIR": pf.PROC_DIR,
    "PSC_PIDCLASS_SLOTS": 8, "PSC_NREGS": len(pf.REGS_ORDER), "PSC_RX_LEN": 16,
    "PSC_NWORDS_MAX": 8, "PSC_OC_N": len(pf.OC_NAMES), "PSC_CHUNK_NTYPES": len(pf.CHUNK_NAMES),
    "PSC_STAGE_NOT_STARTED": 0, "PSC_STAGE_BEFORE_MSLEEP": max(pf.STAGES),
    "PSC_EVENT_QUEUE": 8192, "PSC_CONFIRMED_CAP": 64 * 1024 * 1024,
    "PSC_NAMES_MAX": 999, "PSC_RUN_MAX": 999, "PSC_CTL_PANEL_SECS_MIN": 1,
    "PSC_CTL_PANEL_SECS_MAX": 10, "PSC_SYSCON_SPIN_MAX": pf.SYSCON_SPIN_MAX,
    "PSC_PAD_SECTOR_LEN": pf.PAD_SECTOR_LEN, "PSC_SEG_NAME_FMT": "T%03u%03u.BIN",
    "PSC_UHB_SEG_CREATING_F": 0x80000000,
}
UHB_FLAG_C = {i: "PSC_UHB_F_" + n.upper() for i, n in enumerate(pf.UHB_FLAG_NAMES)}


def compare_constants(defs):
    n = 0
    seen = set()
    for cname, raw in sorted(defs.items()):
        if not cname.startswith("PSC_") or cname in ("PSC_PACKED",) or cname.startswith("PSC_SA_"):
            continue
        try:
            cval = eval_c(raw, defs)
        except Exception:
            continue    # format strings and the like, checked below if mapped
        pyname = cname[4:]
        if cname in CONST_MAP:
            pval = CONST_MAP[cname]
        elif hasattr(pf, pyname):
            pval = getattr(pf, pyname)
        else:
            continue
        seen.add(cname)
        n += 1
        if cval != pval:
            err("constant %s = %r, psc_format %r" % (cname, cval, pval))
    # UHB flags: bit i <-> UHB_FLAG_NAMES[i]
    for i, cname in UHB_FLAG_C.items():
        if cname not in defs:
            err("UHB flag bit %d: %s missing in header" % (i, cname))
            continue
        n += 1
        seen.add(cname)
        if eval_c(defs[cname], defs) != (1 << i):
            err("UHB flag %s != bit %d" % (cname, i))
    for cname in defs:
        if cname.startswith("PSC_UHB_F_") and cname not in seen:
            err("UHB flag %s has no psc_format name" % cname)
    # boot printk prefix
    if not eval_c(defs["PSC_BOOT_PRINTK_FMT"], defs).startswith(pf.BOOT_PRINTK_PREFIX):
        err("PSC_BOOT_PRINTK_FMT prefix differs")
    n += 1
    # every integer PSC_ constant must be either compared or listed as C-only
    c_only = []
    for cname, raw in sorted(defs.items()):
        if cname.startswith("PSC_") and cname not in seen and not cname.startswith("PSC_SA_"):
            try:
                v = eval_c(raw, defs)
                if not isinstance(v, str):
                    c_only.append(cname)
            except Exception:
                pass
    return n, c_only


# --------------------------------------------------------------- compiler
def probe_source(structs):
    lines = ['#include "/work/work/linux/include/linux/psc_format.h"',
             "#define S(t) (sizeof(struct t))",
             "#define O(t,m) (__builtin_offsetof(struct t, m))"]
    for sname in STRUCT_MAP:
        lay, _ = layout(structs, sname)
        lines.append("const unsigned long PROBE__%s__SIZE = S(%s);" % (sname, sname))
        for (fname, off, code, k) in lay:
            ident = fname.replace(".", "_D_")
            elem = "((struct %s *)0)->%s%s" % (sname, fname, "[0]" if (code == "s" or k > 1) else "")
            lines.append("const unsigned long PROBE__%s__%s__OFF = O(%s, %s);" % (sname, ident, sname, fname))
            lines.append("const unsigned long PROBE__%s__%s__ESZ = sizeof(%s);" % (sname, ident, elem))
            lines.append("const unsigned long PROBE__%s__%s__TSZ = sizeof(((struct %s *)0)->%s);"
                         % (sname, ident, sname, fname))
            lines.append("const unsigned long PROBE__%s__%s__SGN = ((__typeof__(%s))-1) < 0;"
                         % (sname, ident, elem))
    # codegen probe: how gcc 4.2.1 stores seq through a packed, aligned(4) pointer
    lines.append("void probe_seq_store(struct psc_sc *r, unsigned int s)"
                 " { r->seq = 0xFFFFFFFFu; __asm__ __volatile__(\"\" ::: \"memory\"); r->seq = s; }")
    lines.append("unsigned int probe_seq_load(volatile struct psc_sc *r) { return r->seq; }")
    lines.append("void probe_u16_store(struct psc_sc *r, unsigned short v) { r->dtick = v; }")
    lines.append("void probe_u32_store(struct psc_w *w, unsigned int v) { w->ext.epc = v; w->sc.ack_polls = v; }")
    return "\n".join(lines) + "\n"


def parse_asm(path):
    vals, cur = {}, None
    for line in open(path):
        m = re.match(r"^(PROBE__\w+):", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^\s*\.(word|long|4byte)\s+(-?\w+)", line)
        if m and cur:
            vals[cur] = int(m.group(2), 0)
            cur = None
        elif cur and re.match(r"^\s*\.(space|zero)\s+4", line):
            vals[cur] = 0
            cur = None
    return vals


def compiler_layout(vals, structs, sname):
    lay, _ = layout(structs, sname)
    out = []
    for (fname, _off, code, k) in lay:
        ident = "PROBE__%s__%s__" % (sname, fname.replace(".", "_D_"))
        off, esz, tsz, sgn = (vals[ident + x] for x in ("OFF", "ESZ", "TSZ", "SGN"))
        count = tsz // esz
        ccode = {1: "B", 2: "H", 4: "I"}[esz]
        if sgn:
            ccode = ccode.lower()
        if ccode == "B" and (code == "s"):
            ccode = "s"
        out.append((fname, off, ccode, count))
    return out, vals["PROBE__%s__SIZE" % sname]


def run_cc(structs):
    ldir = os.path.join(HERE, "layout")
    os.makedirs(os.path.join(ldir, "kinc"), exist_ok=True)
    link = os.path.join(ldir, "kinc", "asm")
    if not os.path.islink(link):
        os.symlink("/work/work/linux/include/asm-mips", link)
    open(os.path.join(ldir, "probe.c"), "w").write(probe_source(structs))
    crc_c = ['#include <stdio.h>',
             '#include "/work/work/linux/include/linux/psc_format.h"',
             'static const unsigned char d4[] = {%s};' % ",".join(str(b) for b in bytes(range(256)) * 3),
             'static unsigned char z492[492];',
             'int main(void) {',
             '  printf("%08x\\n", psc_crc32(0, "123456789", 9));',
             '  printf("%08x\\n", psc_crc32(0x12345678u, "123456789", 9));',
             '  printf("%08x\\n", psc_crc32(0xDEADBEEFu, "", 0));',
             '  printf("%08x\\n", psc_crc32(1, z492, 492));',
             '  printf("%08x\\n", psc_crc32(0xA5A5A5A5u, d4, sizeof d4));',
             '  return 0; }']
    open(os.path.join(ldir, "crc_test.c"), "w").write("\n".join(crc_c) + "\n")
    script = r"""
set -e
export PATH=/work/staging_dir/bin:/work/staging_dir/usr/bin:$PATH
cd /work/work/decoder/layout
CC=mipsel-linux-uclibc-gcc
WARN="-std=gnu89 -Wall -W -Wdeclaration-after-statement -Wstrict-prototypes -pedantic"
PWARN="-std=gnu89 -Wall"   # the probe's own signedness test trips -W; the header is checked by hdr_only.c
echo "== $($CC --version | head -1)"
# header alone, strictest flags, userland and kernel mode: must give 0 warnings
printf '#include "/work/work/linux/include/linux/psc_format.h"\nunsigned int f(const void *p, unsigned long n);\nunsigned int f(const void *p, unsigned long n) { return psc_crc32(0, p, n); }\n' > hdr_only.c
$CC --sysroot=/work/staging_dir -B/work/staging_dir/usr/mipsel-linux-uclibc/bin -O2 $WARN -c -o hdr_user.o hdr_only.c 2> hdr_user.warn || { cat hdr_user.warn; exit 1; }
echo "header-only userland (-pedantic -W): warnings in psc_format.h: $(grep -c 'psc_format.h:[0-9]*: warning' hdr_user.warn || true), elsewhere: $(grep -v psc_format.h hdr_user.warn | grep -c warning || true)"
GCCINC=$($CC -print-file-name=include)
$CC -nostdinc -isystem $GCCINC -D__KERNEL__ -Ikinc -I/work/work/linux/include -O2 $WARN -Wundef -G 0 -mno-abicalls -fno-pic -msoft-float -c -o hdr_kernel.o hdr_only.c 2> hdr_kernel.warn || { cat hdr_kernel.warn; exit 1; }
echo "header-only kernel   (-pedantic -W): warnings in psc_format.h: $(grep -c 'psc_format.h:[0-9]*: warning' hdr_kernel.warn || true), elsewhere: $(grep -v psc_format.h hdr_kernel.warn | grep -c warning || true) (the tree's own asm-mips 'long long' under -pedantic)"
echo "FP_REGS_USED(psc_crc32, userland)=$(mipsel-linux-uclibc-objdump -d hdr_user.o | grep -c '[$]f[0-9]' || true)"
# userland mode (pscol): sysroot headers, bFLT toolchain flags as telem/cbuild.sh
$CC --sysroot=/work/staging_dir -B/work/staging_dir/usr/mipsel-linux-uclibc/bin \
    -O2 $PWARN -S -o probe_user.s probe.c 2> probe_user.warn || { cat probe_user.warn; exit 1; }
$CC --sysroot=/work/staging_dir -B/work/staging_dir/usr/mipsel-linux-uclibc/bin \
    -O2 $PWARN -c -o probe_user.o probe.c 2>/dev/null
echo "probe userland warnings: $(grep -c warning probe_user.warn || true)"
# kernel mode: the tree's include/ and asm-mips, kernel-like flags
$CC -nostdinc -isystem $GCCINC -D__KERNEL__ -Ikinc -I/work/work/linux/include \
    -O2 $PWARN -Wundef -fno-strict-aliasing -fno-common -G 0 -mno-abicalls -fno-pic -msoft-float \
    -S -o probe_kernel.s probe.c 2> probe_kernel.warn || { cat probe_kernel.warn; exit 1; }
echo "probe kernel warnings: $(grep -c warning probe_kernel.warn || true)"
# CRC: header code compiled natively (no MIPS emulator here)
gcc -std=gnu89 -Wall -W -I/usr/include -o crc_test crc_test.c && ./crc_test > crc_test.out
"""
    r = subprocess.run(CONTAINER + [script], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stdout.write(r.stderr)
        err("container compile failed (exit %d)" % r.returncode)
        return
    for mode in ("user", "kernel"):
        vals = parse_asm(os.path.join(ldir, "probe_%s.s" % mode))
        nf = 0
        for sname, keys in STRUCT_MAP.items():
            clay, csize = compiler_layout(vals, structs, sname)
            for key in keys:
                ok, k = compare_layout(sname, clay, csize, key, "gcc-4.2.1 %s" % mode)
                nf += k
        print("gcc 4.2.1 %-6s layout: %d structs, %d field comparisons" % (mode, len(STRUCT_MAP), nf))
    # codegen note
    asm = open(os.path.join(ldir, "probe_user.s")).read()
    for fn in ("probe_seq_store", "probe_seq_load", "probe_u16_store", "probe_u32_store"):
        m = re.search(fn + r":(.*?)\.end\s+" + fn, asm, re.S)
        if m:
            kinds = sorted(set(re.findall(r"^\s+(sw|swl|swr|sb|sh|lw|lwl|lwr|lbu|lhu)\s", m.group(1), re.M)))
            print("codegen (gcc 4.2.1, packed+aligned(4)): %-16s -> %s" % (fn, ",".join(kinds)))
    got = open(os.path.join(ldir, "crc_test.out")).read().split()
    want = ["%08x" % (zlib.crc32(d, s) & 0xFFFFFFFF) for (s, d) in pf.CRC_VECTORS]
    if got != want:
        err("psc_crc32 C %s != zlib %s" % (got, want))
    else:
        print("psc_crc32 (C, header) == zlib.crc32 on %d vectors" % len(want))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--header", default=DEFAULT_HEADER)
    ap.add_argument("--cc", action="store_true", help="also check the gcc 4.2.1 layout in the container")
    a = ap.parse_args()

    pf.selftest(verbose=False)
    print("psc_format.py selftest: OK")
    raw = open(a.header).read()
    text = strip_comments(raw)
    if "//" in text:
        err("C99 // comment in header")
    if re.search(r":\s*\d+\s*;", text):
        err("bitfield in header")
    defs = parse_defines(text)
    structs = parse_structs(text, defs)
    print("header: %s (%d structs, %d #defines)" % (a.header, len(structs), len(defs)))
    missing = set(STRUCT_MAP) - set(structs)
    extra = set(structs) - set(STRUCT_MAP) - {"psc_filehdr_payload"}
    if missing or extra:
        err("struct set: missing %s, unmapped %s" % (sorted(missing), sorted(extra)))
    nf = 0
    for sname, keys in STRUCT_MAP.items():
        if sname not in structs:
            continue
        clay, csize = layout(structs, sname)
        for key in keys:
            ok, k = compare_layout(sname, clay, csize, key, "header")
            nf += k
            print("  %-16s -> %-9s size %4d  fields %3d  %s" % (sname, key, csize, k, "OK" if ok else "FAIL"))
    _, fsz = layout(structs, "psc_filehdr_payload")
    if fsz != pf.FILEHDR_PAYLOAD:
        err("psc_filehdr_payload size %d != %d" % (fsz, pf.FILEHDR_PAYLOAD))
    else:
        print("  %-16s -> payload   size %4d  (44 + 768 + 256)" % ("psc_filehdr_payload", fsz))
    nc, c_only = compare_constants(defs)
    print("header: %d field comparisons, %d constants compared" % (nf, nc))
    if c_only:
        print("C-only integer constants (no psc_format counterpart): " + " ".join(c_only))
    if a.cc:
        run_cc(structs)
    if errors:
        print("check_format: FAIL (%d mismatches)" % len(errors))
        return 1
    print("check_format: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
