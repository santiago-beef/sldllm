#!/usr/bin/env python3
"""Stage 3 PACKAGE test: read-only checks of work/deploy/uClinux_TRACE.

Run:  python3 check_package.py > ../logs/package-check.log 2>&1
Writes nothing except stdout. Exit 0 if every hard check passes, 1 otherwise.
Each check prints PASS/FAIL/INFO with the evidence it used.
"""
import gzip, hashlib, os, re, stat, subprocess, sys, zlib

PSP = '/home/ubuntu/psp'
PKG = PSP + '/work/deploy/uClinux_TRACE'          # package root (what agents deliver)
STICK = PKG + '/PSP/GAME/uClinux_TRACE'            # what goes on the stick
BASE = PSP + '/pspboot-baseline'                   # copy of stick PSP/GAME/uClinux (DOSSIER 9.7)
OUT = PSP + '/work/out/20261006T052947Z'           # release build (gates/LOG.md:353)
LOG = PSP + '/handoff/gates/LOG.md'
FROZEN = '4f9b69dcc72cb8e61322311fa4aabde5ea6f65fe3fc1158089af19161c51cac8'
NAME = 'uClinux_TRACE'
FAILS = []


def h(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def res(ok, what, ev=''):
    tag = 'PASS' if ok else 'FAIL'
    if not ok:
        FAILS.append(what)
    print(f'[{tag}] {what}' + (f'\n        {ev}' if ev else ''))


def info(what):
    print(f'[INFO] {what}')


def sec(t):
    print('\n=== ' + t)


# ---------------------------------------------------------------- 1 listing
sec('1. Full listing of the package (type mode size sha256 path)')
total = 0
allpaths = []
for root, dirs, files in os.walk(PKG):
    dirs.sort()
    for n in sorted(dirs + files):
        p = os.path.join(root, n)
        st = os.lstat(p)
        rel = os.path.relpath(p, PKG)
        allpaths.append(rel)
        if stat.S_ISDIR(st.st_mode):
            print(f'  d {stat.filemode(st.st_mode)} {"":>9} {"":64} {rel}/')
        elif stat.S_ISREG(st.st_mode):
            total += st.st_size
            print(f'  f {stat.filemode(st.st_mode)} {st.st_size:>9} {h(p)} {rel}')
        else:
            print(f'  ? {stat.filemode(st.st_mode)} {"":>9} {"":64} {rel}  (NOT a regular file or dir)')
    files.sort()
print(f'  package total: {total} bytes in {sum(1 for r in allpaths if os.path.isfile(os.path.join(PKG, r)))} files')

# ---------------------------------------------------------------- 2 stray files
sec('2. Stray files and special entries anywhere in the package')
stray_re = re.compile(r'(^\._|^\.DS_Store$|~$|\.bak$|\.orig$|\.rej$|\.swp$|\.swo$|\.tmp$|^Thumbs\.db$|^desktop\.ini$|^\.|^__MACOSX$|\.part$)', re.I)
stray = [r for r in allpaths if stray_re.search(os.path.basename(r))]
special = [r for r in allpaths if not (os.path.isfile(os.path.join(PKG, r)) or os.path.isdir(os.path.join(PKG, r))) or os.path.islink(os.path.join(PKG, r))]
empty = [r for r in allpaths if os.path.isfile(os.path.join(PKG, r)) and os.path.getsize(os.path.join(PKG, r)) == 0]
res(not stray, 'no stray files (.DS_Store, ._*, *~, *.bak, *.orig, *.rej, *.swp, *.tmp, Thumbs.db, desktop.ini, hidden)', f'matches: {stray}')
res(not special, 'no symlinks, device nodes, fifos or sockets', f'matches: {special}')
res(not empty, 'no empty files', f'matches: {empty}')

# ---------------------------------------------------------------- 3 stick folder content
sec('3. Stick folder PSP/GAME/uClinux_TRACE: exact content')
stick_files = sorted(os.listdir(STICK))
want = ['EBOOT.PBP', 'kmodlib.prx', 'pspboot.conf', 'vmlinux-0.22.bin']
res(stick_files == want, 'stick folder holds exactly EBOOT.PBP, kmodlib.prx, pspboot.conf, vmlinux-0.22.bin (RUNBOOK.md:62-63, :158)', f'found {stick_files}')
res(all(os.path.isfile(os.path.join(STICK, f)) for f in stick_files), 'every entry of the stick folder is a regular file (no sub-folders)')
top = sorted(os.listdir(PKG))
info(f'package root holds {top}; PSP/ holds {sorted(os.listdir(PKG + "/PSP"))}; PSP/GAME/ holds {sorted(os.listdir(PKG + "/PSP/GAME"))}')
stick_bytes = sum(os.path.getsize(os.path.join(STICK, f)) for f in stick_files)
info(f'stick folder total: {stick_bytes} bytes; on a FAT volume with 32 KiB clusters (cluster size of the operator stick UNVERIFIED): '
     f'{sum(-(-os.path.getsize(os.path.join(STICK, f)) // 32768) * 32768 for f in stick_files)} bytes allocated')

# ---------------------------------------------------------------- 4 checksums
sec('4. SHA256SUMS')
r = subprocess.run(['sha256sum', '-c', '../../../SHA256SUMS'], cwd=STICK, capture_output=True, text=True)
print('  $ cd PSP/GAME/uClinux_TRACE && sha256sum -c ../../../SHA256SUMS\n' + ''.join('    ' + l + '\n' for l in (r.stdout + r.stderr).splitlines()) + f'    rc={r.returncode}')
res(r.returncode == 0, 'package SHA256SUMS verifies')
listed = sorted(l.split()[1] for l in open(PKG + '/SHA256SUMS') if l.strip())
res(listed == stick_files, 'SHA256SUMS lists exactly the stick files (no file unlisted, no listed file missing)', f'listed {listed}')
r = subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=PKG + '/BUILD', capture_output=True, text=True)
print('  $ cd BUILD && sha256sum -c SHA256SUMS\n' + ''.join('    ' + l + '\n' for l in (r.stdout + r.stderr).splitlines()) + f'    rc={r.returncode}')
res(r.returncode == 0, 'BUILD/SHA256SUMS verifies')
blisted = sorted(l.split()[1] for l in open(PKG + '/BUILD/SHA256SUMS') if l.strip())
bfiles = sorted(f for f in os.listdir(PKG + '/BUILD') if f != 'SHA256SUMS')
res(blisted == bfiles, 'BUILD/SHA256SUMS lists every other BUILD file', f'listed {blisted}; present {bfiles}')

# ---------------------------------------------------------------- 5 baseline identity
sec('5. pspboot files byte-identical to the baseline (pspboot-baseline = stick PSP/GAME/uClinux, DOSSIER 9.7)')
loghex = re.sub(r'\s+', ' ', open(LOG).read())  # gate-log text with line breaks folded
for f, prefix in (('EBOOT.PBP', 'c915ba8a'), ('kmodlib.prx', '69adde5e'), ('pspboot.conf', 'e555890d')):
    a, b = open(os.path.join(STICK, f), 'rb').read(), open(os.path.join(BASE, f), 'rb').read()
    res(a == b, f'{f} == pspboot-baseline/{f} ({len(a)} B)', f'sha256 {h(os.path.join(STICK, f))}')
    res(h(os.path.join(STICK, f)).startswith(prefix) and f'{f} {prefix}' in loghex, f'{f} sha256 prefix {prefix} equals gates/LOG.md G2 attempt 2 entry')

# ---------------------------------------------------------------- 6 kernel identity
sec('6. Kernel image identity')
k = os.path.join(STICK, 'vmlinux-0.22.bin')
kh = h(k)
res(kh == FROZEN, 'packaged vmlinux-0.22.bin sha256 == frozen release value', kh)
res(FROZEN in loghex, 'frozen value appears in gates/LOG.md (G2 attempt 2, RELEASE)')
res(os.path.getsize(k) == 936714 and '936,714 B' in loghex, 'size 936,714 B as in gates/LOG.md', str(os.path.getsize(k)))
img = open(PKG + '/BUILD/IMAGE.sha256').read().split()
res(img == [FROZEN, 'vmlinux-0.22.bin'], 'BUILD/IMAGE.sha256 names this image', ' '.join(img))
res(h(OUT + '/vmlinux-0.22.bin') == kh and open(OUT + '/vmlinux-0.22.bin', 'rb').read() == open(k, 'rb').read(), f'== {OUT}/vmlinux-0.22.bin (release build output)')
res(h(PKG + '/BUILD/vmlinux') == h(OUT + '/vmlinux'), 'BUILD/vmlinux == release build vmlinux')
raw = open(k, 'rb').read()
info(f'gzip header of package image : {raw[:10].hex()} (magic 1f8b, CM 08, FLG {raw[3]:#04x}, MTIME {int.from_bytes(raw[4:8], "little")}, XFL {raw[8]}, OS {raw[9]})')
for ref in (BASE + '/vmlinux-0.22.bin', PSP + '/build/linux/vmlinux-0.22.bin', PSP + '/work/prebuilt/vmlinux-0.22.bin'):
    if os.path.exists(ref):
        rr = open(ref, 'rb').read(10)
        info(f'gzip header of {ref}: {rr.hex()} (FLG {rr[3]:#04x})')
vb = gzip.decompress(raw)
res(len(vb) == 1767264 and hashlib.sha256(vb).hexdigest() == h(OUT + '/vmlinux.bin'), 'gunzip(package image) == release vmlinux.bin (1,767,264 B), single member, CRC and ISIZE checked by gzip',
    hashlib.sha256(vb).hexdigest())
d = zlib.decompressobj(16 + zlib.MAX_WBITS)
d.decompress(raw)
res(d.eof and d.unused_data == b'', 'one gzip member, no trailing bytes')

# ---------------------------------------------------------------- 7 pspboot.conf
sec('7. pspboot.conf: every key, every path it names, resolved inside PSP/GAME/uClinux_TRACE')
conf = open(os.path.join(STICK, 'pspboot.conf'), 'rb').read()
res(b'\r' not in conf, 'pspboot.conf has LF line ends only (as the baseline)')
known = {'kernel', 'cmdline', 'baud'}  # the three parameter names in EBOOT.PBP's DATA.PSP .rodata (DATA.PSP strings above; pspboot-disasm-excerpt.txt)
paths = []
for i, line in enumerate(conf.decode('ascii').split('\n'), 1):
    s = line.strip()
    if not s or s.startswith('#'):
        continue
    key, _, val = s.partition('=')
    print(f'  pspboot.conf:{i}: {key}={val}')
    res(key in known, f'key "{key}" is one pspboot parses (kernel/cmdline/baud)')
    if key == 'kernel':
        paths.append(val)
    if key == 'cmdline':
        info(f'cmdline tokens {val.split()}: no path, no initrd=, init= or rdinit= (the embedded initramfs and its /init are used)')
for p in paths:
    full = os.path.normpath(os.path.join(STICK, p))
    ok = os.path.isfile(full) and os.path.dirname(full) == STICK
    res(ok, f'kernel={p} resolves to PSP/GAME/{NAME}/{os.path.relpath(full, STICK)} and that file exists in the stick folder')
    res(not p.startswith(('/', 'ms0:', '..')) and '/' not in p, f'kernel={p} is a bare relative name (resolved against the folder EBOOT.PBP runs from, as for the baseline)')
ebp = open(os.path.join(STICK, 'EBOOT.PBP'), 'rb').read()
offs = [int.from_bytes(ebp[8 + 4 * i:12 + 4 * i], 'little') for i in range(8)] + [len(ebp)]
data_psp = ebp[offs[6]:offs[7]]           # PBP entry 6 = DATA.PSP (the loader ELF)
info(f'EBOOT.PBP: magic {ebp[:4]!r}, DATA.PSP at {offs[6]}, {len(data_psp)} B, ELF magic {data_psp[:4]!r} (unencrypted)')
for s in (b'pspboot.conf\0', b'kmodlib.prx\0', b'kernel\0', b'cmdline\0', b'baud\0', b'Unsupported param %s', b'Failed to open config file %s',
          b'Failed to open file %s', b'%d bytes loaded', b'ms0:', b'README', b'GAME150', b'.conf\0'):
    info(f'  DATA.PSP contains {s!r}: {data_psp.count(s)} time(s)' + (f' at file offset {data_psp.find(s):#x}' if s in data_psp else ''))
for implicit in ('pspboot.conf', 'kmodlib.prx'):
    res(os.path.isfile(os.path.join(STICK, implicit)), f'{implicit}: opened by EBOOT.PBP by bare relative name (DATA.PSP strings above; pspboot-disasm-excerpt.txt) and present beside EBOOT.PBP')
res(conf == open(BASE + '/pspboot.conf', 'rb').read(), 'kernel name in pspboot.conf unchanged from baseline, so the image file name must stay vmlinux-0.22.bin, which it does')

# ---------------------------------------------------------------- 8 layout vs baseline
sec('8. Layout against the baseline folder and the known-good stick layout (DOSSIER.md:471-484)')
bfiles = sorted(os.listdir(BASE))
print(f'  baseline  PSP/GAME/uClinux/       : {bfiles}')
print(f'  package   PSP/GAME/{NAME}/ : {stick_files}')
for f in sorted(set(bfiles) | set(stick_files)):
    a, b = os.path.join(BASE, f), os.path.join(STICK, f)
    sa = os.path.getsize(a) if os.path.exists(a) else None
    sb = os.path.getsize(b) if os.path.exists(b) else None
    same = sa is not None and sb is not None and open(a, 'rb').read() == open(b, 'rb').read()
    print(f'    {f:18} baseline {str(sa):>8}  package {str(sb):>8}  {"identical" if same else ("different" if sa and sb else "only in " + ("baseline" if sa else "package"))}')
res(set(stick_files) == set(bfiles) - {'README'}, 'same file names as the baseline minus README (release notes, not read by pspboot: no "README" string in DATA.PSP)')

# ---------------------------------------------------------------- 9 names
sec('9. Folder name: collisions and FAT safety')
taken = ['uClinux', 'uClinux_FIX', 'uClinux_WIP']
for t in taken:
    res(NAME.lower() != t.lower(), f'"{NAME}" != "{t}" ignoring case (FAT is case-insensitive)')
others = sorted(set(os.listdir(PSP)) | {'PSCLOG', 'GAME150', 'picture', 'FW150', 'telem.log', 'kmsg.txt', 'keymap.log', 'hello_fb', 'telem', 'keymap'})
hit = [o for o in others if o.lower() == NAME.lower()]
res(not hit, f'"{NAME}" equals none of {others} ignoring case', f'hits {hit}')
everywhere = subprocess.run(['find', PSP, '-path', PSP + '/build/linux', '-prune', '-o', '-path', PSP + '/work/linux', '-prune', '-o',
                             '-path', PSP + '/ksrc', '-prune', '-o', '-iname', NAME, '-print'], capture_output=True, text=True).stdout.split()
info(f'every path named {NAME} (any case) under {PSP}: {everywhere}')


def is83(n):
    b, dot, e = n.partition('.')
    ok_chars = re.fullmatch(r"[A-Z0-9_$%'\-@~`!(){}^#&]+", (b + e).upper() or 'x') is not None
    return ('.' not in e) and 1 <= len(b) <= 8 and len(e) <= 3 and ok_chars


def lfn_ok(n):
    return 1 <= len(n) <= 255 and not re.search(r'[\\/:*?"<>|\x00-\x1f]', n) and not n.endswith(('.', ' '))


for n in [NAME] + stick_files:
    fits = is83(n)
    case = 'upper' if n == n.upper() else ('lower' if n == n.lower() else 'mixed')
    info(f'{n:18} len {len(n):2}  fits 8.3 shape: {"yes" if fits else "no "}  case {case}  -> '
         + ('plain 8.3 entry' if fits and case == 'upper' else 'needs a VFAT long-name entry (or NT case flag), as do the baseline names'))
    res(lfn_ok(n), f'{n}: valid VFAT long name (<=255 chars, no \\ / : * ? " < > | or control chars, no trailing dot/space)')
res(re.fullmatch(r'[A-Za-z0-9_]+', NAME) is not None, f'{NAME}: only letters, digits and "_" (all also legal in 8.3 short names; no space, no dot)')
info('baseline names on the stick that already need long-name entries and boot today [HW]: "uClinux" (mixed case), "pspboot.conf" (4-char extension), '
     '"vmlinux-0.22.bin" (two dots, 12-char base); the new folder name adds only length (13 chars)')
info('full path as the PSP sees the kernel: ms0:/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin = '
     f'{len("ms0:/PSP/GAME/uClinux_TRACE/vmlinux-0.22.bin")} chars (baseline ms0:/PSP/GAME/uClinux/vmlinux-0.22.bin = {len("ms0:/PSP/GAME/uClinux/vmlinux-0.22.bin")})')

# ---------------------------------------------------------------- 10 provenance
sec('10. PROVENANCE.txt against the gate log and the release build')
prov = open(PKG + '/PROVENANCE.txt').read()
print(''.join('  | ' + l + '\n' for l in prov.splitlines()))
head = open(OUT + '/git-head.txt').read().strip()
res(f'git commit:    {head}' in prov and head.startswith('48dcc1b9') and 'HEAD 48dcc1b9' in loghex, 'commit 48dcc1b9... == out/git-head.txt == gates/LOG.md G2 attempt 2 "HEAD 48dcc1b9"', head)
res('build out dir: ' + OUT in prov and 'out/20261006T052947Z' in loghex, 'out dir 20261006T052947Z == gates/LOG.md "release build out/20261006T052947Z"')
res(os.path.getsize(OUT + '/git-status.txt') == 0 and re.search(r'tracked changes at build time:\nkernel banner', prov) is not None, 'no tracked changes at build time (out/git-status.txt empty; nothing listed in PROVENANCE)')
banner = open(PKG + '/BUILD/banner.txt', 'rb').read()
res(('kernel banner: ' + banner.decode().rstrip('\n')) in prov, 'PROVENANCE banner == BUILD/banner.txt')
res(banner.rstrip(b'\n') + b'\n' == banner and vb.count(banner + b'\0') == 1, 'banner.txt (with its newline, NUL-terminated) occurs exactly once in gunzip(package image): the banner is the packaged image\'s own')
bid = f'0x{zlib.crc32(banner) & 0xffffffff:08x}'
res(bid == open(PKG + '/BUILD/build_id.txt').read().strip() == '0x045b27d9' and 'build_id 0x045b27d9' in loghex and 'build_id 0x045b27d9' in prov,
    'zlib CRC-32(banner) == BUILD/build_id.txt == PROVENANCE == gates/LOG.md build_id 0x045b27d9', bid)
blog = open(PSP + '/work/logs/build-20261006T052947Z.log').read()
res(f'build log:     {PSP}/work/logs/build-20261006T052947Z.log' in prov and f'git HEAD:    {head}' in blog and "KBUILD_BUILD_VERSION='' KBUILD_BUILD_TIMESTAMP='' REPRODUCE_BASELINE='0'" in blog,
    'build log named in PROVENANCE exists, records HEAD 48dcc1b9 and the default identity (DESIGN 18.4)')
res('pspboot files copied verbatim from: ' + BASE in prov and 'status: COMPLETE' in prov, 'PROVENANCE names pspboot-baseline as the loader source and status COMPLETE')
res(f'folder:        PSP/GAME/{NAME}' in prov, f'PROVENANCE folder == PSP/GAME/{NAME}')
res(subprocess.run(['diff', '-r', PKG + '/BUILD', PSP + '/handoff/impl/release-20261006T052947Z/BUILD'], capture_output=True).returncode == 0,
    'BUILD/ == handoff/impl/release-20261006T052947Z/BUILD (named in PROVENANCE)')
info('PROVENANCE.txt does not itself state the image sha256; SHA256SUMS beside it does (4f9b69dc...cac8)')

sec('RESULT')
print('FAIL: ' + '; '.join(FAILS) if FAILS else 'all hard checks PASS')
sys.exit(1 if FAILS else 0)
