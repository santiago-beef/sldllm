"""G2 attempt 2: replace only the data of usr/bin/pscol in psp-initramfs.cpio (newc),
byte-preserving every other entry (header and data) and the archive order; the
pscol entry keeps its inode, mode 0755, owner and device fields, and gets the new
size and the bFLT's mtime. The archive is padded to 512 B as before.
usage: replace_pscol.py IN.cpio PSCOL_BFLT OUT.cpio"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc
src, bflt, out = sys.argv[1:4]
buf = open(src, "rb").read()
ents, end = newc.parse(buf)
assert len(buf) % 512 == 0 and not any(buf[end:])
data = open(bflt, "rb").read()
o = bytearray()
n = 0
for e in ents:
    if e["name"] == "usr/bin/pscol":
        h = dict(e["h"]); h["filesize"] = len(data); h["mtime"] = int(os.stat(bflt).st_mtime)
        assert h["mode"] == 0o100755
        o += newc.entry(h, e["name"], data); n += 1
    else:
        o += e["raw"]
assert n == 1, n
o += b"\0" * ((512 - len(o) % 512) % 512)
open(out, "wb").write(o)
ents2, _ = newc.parse(bytes(o))
assert [e["name"] for e in ents2] == [e["name"] for e in ents]
same = sum(1 for a, b in zip(ents, ents2) if a["raw"] == b["raw"])
print("wrote", out, len(o), "bytes;", len(ents2), "entries,", same, "byte-identical, pscol", len(data), "bytes")
