#!/usr/bin/env python3
import sys
from pathlib import Path
try:
    import brotli
except ImportError:
    print("brotli module missing", file=sys.stderr)
    raise

src=Path(sys.argv[1]).read_bytes()
raw=brotli.decompress(src)
needles=[
    b"Rewritten by o_xer",
    b"Rewritten by",
    b"o_xer",
    b"Eaglercraft 26.2 u1",
    b"Eaglercraft 26.2",
    b"26.2 u1",
]
lines=[f"decoded_size={len(raw)}", f"magic={raw[:8].hex()}"]
for n in needles:
    offs=[]; start=0
    while True:
        i=raw.find(n,start)
        if i<0: break
        offs.append(i); start=i+1
    lines.append(f"{n.decode('utf-8',errors='replace')}: {offs}")
Path(sys.argv[2]).write_text("\n".join(lines)+"\n",encoding="utf-8")
