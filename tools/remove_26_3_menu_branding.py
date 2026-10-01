#!/usr/bin/env python3
from pathlib import Path
import brotli, hashlib, sys

src = Path(sys.argv[1])
out = Path(sys.argv[2])
raw = brotli.decompress(src.read_bytes())

needles = [
    b"26.3-JM",
    b"Made by Joey-JM",
    b"Made by Joey",
    b"Joey-JM",
    b"26.3 JM",
]
print("raw_size", len(raw))
print("raw_sha256", hashlib.sha256(raw).hexdigest())
for n in needles:
    pos=[]
    i=0
    while True:
        i=raw.find(n,i)
        if i<0: break
        pos.append(i)
        i+=1
    print(n.decode("utf-8","replace"), pos)

# Keep byte lengths identical so no Wasm section/offset rewriting is needed.
patched = raw
repls = {
    b"26.3-JM": b"       ",
    b"Made by Joey-JM": b"               ",
    b"Made by Joey": b"            ",
    b"Joey-JM": b"       ",
}
counts={}
for old,new in repls.items():
    c=patched.count(old)
    if c:
        patched=patched.replace(old,new)
    counts[old.decode()] = c
print("patched_counts", counts)
print("patched_sha256", hashlib.sha256(patched).hexdigest())
out.write_bytes(brotli.compress(patched, quality=11))
print("compressed_size", out.stat().st_size)
