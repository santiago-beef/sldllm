"""Rebuild psp-initramfs.cpio (newc) byte-preserving: every original entry is copied
verbatim except etc/rc.sysinit (new data from new-root, new size/mtime) and a new
usr/bin/pscol entry inserted right after usr/bin/pspmd. Archive padded to 512 B like the original."""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc
src, newroot, out = sys.argv[1:4]
buf = open(src, "rb").read()
ents, end = newc.parse(buf)
assert len(buf) % 512 == 0 and not any(buf[end:])
def readroot(p):
    return subprocess.run(["sudo","cat",os.path.join(newroot,p)],check=True,capture_output=True).stdout
def mtime(p):
    return int(subprocess.run(["sudo","stat","-c","%Y",os.path.join(newroot,p)],check=True,capture_output=True,text=True).stdout)
maxino = max(e["h"]["ino"] for e in ents)
names = [e["name"] for e in ents]
assert "usr/bin/pscol" not in names
o = bytearray()
for e in ents:
    if e["name"] == "etc/rc.sysinit":
        h = dict(e["h"]); d = readroot("etc/rc.sysinit"); h["filesize"] = len(d); h["mtime"] = mtime("etc/rc.sysinit")
        o += newc.entry(h, e["name"], d)
    else:
        o += e["raw"]
    if e["name"] == "usr/bin/pspmd":
        ref = e["h"]; d = readroot("usr/bin/pscol")
        h = dict(magic=ref["magic"], ino=maxino+1, mode=0o100755, uid=0, gid=0, nlink=1,
                 mtime=mtime("usr/bin/pscol"), filesize=len(d), devmajor=ref["devmajor"],
                 devminor=ref["devminor"], rdevmajor=0, rdevminor=0, namesize=0, check=0)
        o += newc.entry(h, "usr/bin/pscol", d)
o += b"\0" * ((512 - len(o) % 512) % 512)
open(out, "wb").write(o)
print("wrote", out, len(o), "bytes; pscol ino", maxino+1)
