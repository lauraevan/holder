#!/usr/bin/env python3
import gzip, io, struct, sys, zlib
from pathlib import Path
END=b":::YEE:>"
def u8(f): return f.read(1)[0]
def u16(f): return struct.unpack(">H",f.read(2))[0]
def u32(f): return struct.unpack(">I",f.read(4))[0]
def astr(f): return f.read(u8(f)).decode("latin1")
def parse(path):
    raw=Path(path).read_bytes(); f=io.BytesIO(raw[:-8]); assert f.read(8)==b"EAGPKG$$"
    astr(f); f.read(u8(f)); f.read(u16(f)); f.read(8); count=u32(f); c=f.read(1); rest=f.read()
    body=gzip.decompress(rest) if c==b"G" else zlib.decompress(rest) if c==b"Z" else rest
    z=io.BytesIO(body); files={}
    for _ in range(count):
        typ=z.read(4); name=astr(z); ln=u32(z)
        if typ==b"FILE":
            z.read(4); data=z.read(ln-5); z.read(2); files[name]=data
        else:
            z.read(ln); z.read(1)
    return files
files=parse(sys.argv[1])
needles=[
    "Rewritten by o_xer",
    "Rewritten by",
    "o_xer",
    "Eaglercraft 26.2 u1",
    "Eaglercraft 26.2",
    "Minecraft 26.3",
    "dappled_forest",
    "Dappled Forest"
]
out=[]
for needle in needles:
    out.append("## "+needle)
    found=0
    for name,data in files.items():
        hit = needle.encode("utf-8") in data or needle.lower().encode("utf-8") in data.lower()
        if hit or needle.lower().replace(" ","_") in name.lower():
            out.append(name)
            found+=1
    out.append("count="+str(found))
    out.append("")
Path(sys.argv[2]).write_text("\n".join(out),encoding="utf-8")
