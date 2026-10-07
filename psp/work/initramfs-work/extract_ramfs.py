"""Extract the .init.ramfs section from a MIPS ELF32 LE vmlinux and the same bytes
from vmlinux.bin (load base 0x88000000), gunzip, write the cpio."""
import struct, sys, zlib, hashlib
elf, binf, out = sys.argv[1:4]
d = open(elf,'rb').read()
assert d[:4] == b'\x7fELF' and d[4] == 1 and d[5] == 1
e_shoff, = struct.unpack_from('<I', d, 0x20)
e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<HHH', d, 0x2e)
secs = [struct.unpack_from('<IIIIIIIIII', d, e_shoff + i*e_shentsize) for i in range(e_shnum)]
strtab = secs[e_shstrndx]; so = strtab[4]
def nm(o): return d[so+o: d.index(b'\0', so+o)].decode()
s = [x for x in secs if nm(x[0]) == '.init.ramfs'][0]
addr, off, size = s[3], s[4], s[5]
blob = d[off:off+size]
b = open(binf,'rb').read()[addr-0x88000000: addr-0x88000000+size]
print(".init.ramfs VMA 0x%08x size %d; vmlinux.bin slice equal: %s" % (addr, size, b == blob))
gz = blob  # section = gzip stream (+ possible padding)
dec = zlib.decompressobj(16+zlib.MAX_WBITS); cpio = dec.decompress(gz) + dec.flush()
print("gzip member consumed, trailing bytes after member:", len(dec.unused_data), "nonzero:", any(dec.unused_data))
open(out,'wb').write(cpio)
print("cpio from image: %d bytes sha256 %s" % (len(cpio), hashlib.sha256(cpio).hexdigest()))
