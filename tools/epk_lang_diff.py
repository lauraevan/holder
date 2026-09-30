#!/usr/bin/env python3
import gzip, io, json, struct, sys, zlib
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
            crc=u32(z); data=z.read(ln-5); assert z.read(1)==b":" and z.read(1)==b">"; files[name]=data
        else:
            z.read(ln); assert z.read(1)==b">"
    return files
def obj(files,name): return json.loads(files[name].decode("utf-8-sig"))
a=parse(sys.argv[1]); b=parse(sys.argv[2])
out=[]
for name in ("assets/minecraft/lang/en_us.json","assets/eagler/lang/en_us.json"):
    x=obj(a,name); y=obj(b,name)
    extra=sorted(set(y)-set(x)); missing=sorted(set(x)-set(y)); common=set(x)&set(y)
    same=sum(1 for k in common if x[k]==y[k])
    out.append(f"## {name}")
    out.append(f"26.2 keys={len(x)} 26.3 keys={len(y)} common={len(common)} same_values={same} extra26.3={len(extra)} missing26.3={len(missing)}")
    out.append("EXTRA 26.3 KEYS:")
    for k in extra: out.append(f"{k} = {y[k]}")
    out.append("")
Path(sys.argv[3]).write_text("\n".join(out),encoding="utf-8")
