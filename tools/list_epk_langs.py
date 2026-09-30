#!/usr/bin/env python3
import gzip,io,struct,zlib,sys
from pathlib import Path
END=b":::YEE:>"
def u8(f): return f.read(1)[0]
def u16(f): return struct.unpack(">H",f.read(2))[0]
def u32(f): return struct.unpack(">I",f.read(4))[0]
def astr(f): return f.read(u8(f)).decode("latin1")
def files(path):
    raw=Path(path).read_bytes(); f=io.BytesIO(raw[:-8]); assert f.read(8)==b"EAGPKG$$"
    astr(f); f.read(u8(f)); f.read(u16(f)); f.read(8); n=u32(f); c=f.read(1); p=f.read()
    b=gzip.decompress(p) if c==b"G" else zlib.decompress(p) if c==b"Z" else p
    z=io.BytesIO(b); out=[]
    for _ in range(n):
        typ=z.read(4); name=astr(z); ln=u32(z)
        if typ==b"FILE": z.read(4); data=z.read(ln-5); z.read(2); out.append((name,data))
        else: z.read(ln); z.read(1)
    return out
fs=files(sys.argv[1])
langs=sorted((n,len(d)) for n,d in fs if "/lang/" in n.lower())
Path(sys.argv[2]).write_text("\n".join(f"{n}\t{s}" for n,s in langs)+"\n",encoding="utf-8")
