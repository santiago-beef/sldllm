"""Minimal newc (070701/070702) cpio reader/writer that keeps entries byte-for-byte."""
import sys
FIELDS = ["ino","mode","uid","gid","nlink","mtime","filesize","devmajor","devminor","rdevmajor","rdevminor","namesize","check"]
def pad4(n): return (4 - n % 4) % 4
def parse(buf):
    off = 0; ents = []
    while True:
        start = off
        magic = buf[off:off+6].decode()
        assert magic in ("070701","070702"), (off, magic)
        h = {"magic": magic}
        for i,f in enumerate(FIELDS):
            h[f] = int(buf[off+6+8*i: off+14+8*i], 16)
        off += 110
        name = buf[off: off+h["namesize"]-1].decode()
        off += h["namesize"]; off += pad4(110 + h["namesize"])
        data = buf[off: off+h["filesize"]]
        off += h["filesize"]; off += pad4(h["filesize"])
        ents.append(dict(h=h, name=name, data=data, raw=buf[start:off]))
        if name == "TRAILER!!!":
            return ents, off
def header(h, name):
    nb = name.encode() + b"\0"
    s = h["magic"] + "".join("%08X" % (len(nb) if f=="namesize" else h[f]) for f in FIELDS)
    out = s.encode() + nb
    return out + b"\0"*pad4(len(out))
def entry(h, name, data):
    return header(h, name) + data + b"\0"*pad4(len(data))
if __name__ == "__main__":
    buf = open(sys.argv[1],"rb").read()
    ents, end = parse(buf)
    print("entries", len(ents), "end", end, "filelen", len(buf), "tail-nonzero", any(buf[end:]))
    for e in ents:
        h=e["h"]; print(h["magic"], "%6o"%h["mode"], h["ino"], h["uid"], h["gid"], h["nlink"], h["mtime"], h["filesize"], h["rdevmajor"], h["rdevminor"], h["devmajor"], h["devminor"], h["check"], e["name"])
