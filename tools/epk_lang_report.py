#!/usr/bin/env python3
import gzip, io, json, struct, sys, zlib
from pathlib import Path

END=b":::YEE:>"

def u8(f): return f.read(1)[0]
def u16(f): return struct.unpack(">H", f.read(2))[0]
def u32(f): return struct.unpack(">I", f.read(4))[0]
def astr(f):
    n=u8(f)
    return f.read(n).decode("latin1")

def parse_epk(path):
    raw=Path(path).read_bytes()
    if not raw.startswith(b"EAGPKG$$") or not raw.endswith(END):
        raise ValueError("bad EPK envelope")
    f=io.BytesIO(raw[:-8])
    assert f.read(8)==b"EAGPKG$$"
    version=astr(f)
    fn=f.read(u8(f))
    comment=f.read(u16(f))
    millis=f.read(8)
    count=u32(f)
    c=f.read(1)
    rest=f.read()
    if c==b"G": body=gzip.decompress(rest)
    elif c==b"Z": body=zlib.decompress(rest)
    elif c==b"0": body=rest
    else: raise ValueError("bad compression "+repr(c))
    z=io.BytesIO(body)
    files={}
    heads=[]
    for i in range(count):
        typ=z.read(4)
        name=astr(z)
        ln=u32(z)
        if typ==b"HEAD":
            data=z.read(ln)
            if z.read(1)!=b">": raise ValueError("bad HEAD terminator")
            heads.append((name,data))
        elif typ==b"FILE":
            crc=u32(z)
            data=z.read(ln-5)
            if z.read(1)!=b":": raise ValueError("bad FILE colon")
            if z.read(1)!=b">": raise ValueError("bad FILE terminator")
            if (zlib.crc32(data)&0xffffffff)!=crc: raise ValueError("crc mismatch "+name)
            files[name]=data
        else:
            data=z.read(ln)
            if z.read(1)!=b">": raise ValueError("bad object terminator")
    if z.read(4)!=b"END$": raise ValueError("missing END$")
    return dict(version=version, filename=fn, comment=comment, millis=millis, compression=c, files=files, heads=heads)

def decode_text(b):
    for enc in ("utf-8","utf-8-sig","latin1"):
        try:return b.decode(enc)
        except UnicodeDecodeError: pass
    return None

def main():
    a=parse_epk(sys.argv[1]); b=parse_epk(sys.argv[2])
    out=[]
    out.append(f"26.2 files: {len(a['files'])}")
    out.append(f"26.3 files: {len(b['files'])}")
    out.append(f"26.2 compression: {a['compression'].decode()}")
    out.append(f"26.3 compression: {b['compression'].decode()}")
    names=sorted(set(a["files"])|set(b["files"]))
    lang=[n for n in names if "/lang/" in n.lower() or "en_us" in n.lower() or "zh_cn" in n.lower()]
    out.append("")
    out.append("LANGUAGE-LIKE FILES:")
    for n in lang:
        x=a["files"].get(n); y=b["files"].get(n)
        out.append(f"{n} | 26.2={len(x) if x is not None else '-'} | 26.3={len(y) if y is not None else '-'} | same={x==y if x is not None and y is not None else '-'}")
        if y is not None and ("en_us" in n.lower() or "zh_cn" in n.lower()):
            t=decode_text(y)
            if t is not None:
                chinese=sum('\u3400'<=c<='\u9fff' for c in t)
                out.append(f"  26.3 chars={len(t)} chinese_codepoints={chinese}")
                for key in ("menu.singleplayer","menu.multiplayer","menu.options","options.title"):
                    try:
                        obj=json.loads(t)
                        if isinstance(obj,dict) and key in obj: out.append(f"  {key} = {obj[key]}")
                    except Exception:
                        break
    Path(sys.argv[3]).write_text("\n".join(out)+"\n",encoding="utf-8")

if __name__=="__main__": main()
