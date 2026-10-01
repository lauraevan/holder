#!/usr/bin/env python3
import gzip, io, json, struct, sys, urllib.request, zipfile, zlib
from pathlib import Path

END=b":::YEE:>"
MANIFEST="https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)

def get_bytes(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

def u8(f):
    b=f.read(1)
    if len(b)!=1: raise EOFError
    return b[0]
def u16(f): return struct.unpack(">H",f.read(2))[0]
def u32(f): return struct.unpack(">I",f.read(4))[0]
def p8(n): return bytes([n])
def p16(n): return struct.pack(">H",n)
def p32(n): return struct.pack(">I",n)
def astr(f): return f.read(u8(f)).decode("latin1")
def pastr(s):
    b=s.encode("latin1")
    if len(b)>255: raise ValueError("name too long")
    return p8(len(b))+b

def parse_epk(path):
    raw=Path(path).read_bytes()
    if not raw.startswith(b"EAGPKG$$") or not raw.endswith(END):
        raise ValueError("bad EPK envelope")
    f=io.BytesIO(raw[:-8]); f.read(8)
    version=astr(f)
    filename=f.read(u8(f))
    comment=f.read(u16(f))
    millis=f.read(8)
    count=u32(f)
    comp=f.read(1)
    payload=f.read()
    if comp==b"G": body=gzip.decompress(payload)
    elif comp==b"Z": body=zlib.decompress(payload)
    elif comp==b"0": body=payload
    else: raise ValueError("unsupported EPK compression")
    z=io.BytesIO(body); entries=[]
    for _ in range(count):
        typ=z.read(4); name=astr(z); ln=u32(z)
        if typ==b"FILE":
            crc=u32(z); data=z.read(ln-5)
            if z.read(1)!=b":" or z.read(1)!=b">": raise ValueError("bad FILE terminator "+name)
            if (zlib.crc32(data)&0xffffffff)!=crc: raise ValueError("CRC mismatch "+name)
            entries.append([typ,name,data])
        else:
            data=z.read(ln)
            if z.read(1)!=b">": raise ValueError("bad object terminator "+name)
            entries.append([typ,name,data])
    if z.read(4)!=b"END$": raise ValueError("missing END$")
    return dict(version=version,filename=filename,comment=comment,millis=millis,compression=comp,entries=entries)

def file_map(epk):
    return {n:d for typ,n,d in epk["entries"] if typ==b"FILE"}

def encode_json(obj):
    return (json.dumps(obj,ensure_ascii=False,indent=2,separators=(",",": "))+"\n").encode("utf-8")

def resolve_26_3():
    manifest=get_json(MANIFEST)
    matches=[v for v in manifest["versions"] if v["id"]=="26.3"]
    if not matches:
        raise RuntimeError("official Mojang version manifest does not contain exact release id 26.3")
    return get_json(matches[0]["url"])

def official_languages(version):
    out={}
    pack_meta=None

    # Mojang's 26.3 asset index contains both the language resources and the
    # built-in pack.mcmeta language registry.
    idx=get_json(version["assetIndex"]["url"])
    for key,obj in idx.get("objects",{}).items():
        lk=key.lower()
        h=obj["hash"]
        url="https://resources.download.minecraft.net/"+h[:2]+"/"+h
        if lk.startswith("minecraft/lang/") and lk.endswith(".json"):
            out["assets/"+key]=get_bytes(url)
        elif lk=="pack.mcmeta":
            pack_meta=json.loads(get_bytes(url).decode("utf-8-sig"))

    # The default locale can also be shipped directly in the client jar.
    client=get_bytes(version["downloads"]["client"]["url"])
    with zipfile.ZipFile(io.BytesIO(client)) as z:
        for name in z.namelist():
            ln=name.lower()
            if ln.startswith("assets/minecraft/lang/") and ln.endswith(".json"):
                out.setdefault(name,z.read(name))

    if not isinstance(pack_meta,dict):
        raise RuntimeError("official 26.3 asset index did not provide pack.mcmeta")
    meta=pack_meta.get("language")
    if not isinstance(meta,dict) or not meta:
        raise RuntimeError("official 26.3 pack.mcmeta has no language registry")
    return out,meta,pack_meta

def rebuild(epk, replacements, additions, out):
    body=bytearray()
    seen=set()
    entries=[]
    for typ,name,data in epk["entries"]:
        if typ==b"FILE" and name in replacements:
            data=replacements[name]
        entries.append((typ,name,data))
        seen.add(name)
    for name,data in sorted(additions.items()):
        if name not in seen:
            entries.append((b"FILE",name,data))

    for typ,name,data in entries:
        body += typ + pastr(name)
        if typ==b"FILE":
            body += p32(len(data)+5)
            body += p32(zlib.crc32(data)&0xffffffff) + data + b":" + b">"
        else:
            body += p32(len(data)) + data + b">"
    body += b"END$"

    comp=epk["compression"]
    if comp==b"G": packed=gzip.compress(bytes(body),compresslevel=9,mtime=0)
    elif comp==b"Z": packed=zlib.compress(bytes(body),9)
    else: packed=bytes(body)
    raw=(b"EAGPKG$$"+pastr(epk["version"])+p8(len(epk["filename"]))+epk["filename"]+
         p16(len(epk["comment"]))+epk["comment"]+epk["millis"]+p32(len(entries))+
         comp+packed+END)
    Path(out).write_bytes(raw)

def main():
    source=parse_epk(sys.argv[1])
    baseline=parse_epk(sys.argv[2])
    src_files=file_map(source); base_files=file_map(baseline)

    version=resolve_26_3()
    langs,meta,official_pack_meta=official_languages(version)

    # Normalize official paths and discard languages.json from per-locale counting.
    official={}
    for name,data in langs.items():
        if not name.startswith("assets/"):
            name="assets/"+name
        official[name]=data

    # Merge Mojang's language registry into the EPK's existing root pack
    # metadata, preserving any custom fields already present in the 26.3 pack.
    existing_pack={}
    if "pack.mcmeta" in src_files:
        try:
            existing_pack=json.loads(src_files["pack.mcmeta"].decode("utf-8-sig"))
        except Exception:
            existing_pack={}
    if not isinstance(existing_pack,dict):
        existing_pack={}
    existing_pack["language"]=official_pack_meta["language"]
    if "pack" not in existing_pack and "pack" in official_pack_meta:
        existing_pack["pack"]=official_pack_meta["pack"]
    pack_mcmeta_bytes=encode_json(existing_pack)

    codes=sorted(k.lower() for k in meta.keys())
    for required in ("en_us","tr_tr","en_pt"):
        if required not in codes:
            raise RuntimeError("official 26.3 language metadata is missing "+required)

    # Title-screen spacing request: suppress first line and use the former
    # rewritten-by line for the compact Minecraft 26.3 label.
    eagler=json.loads(base_files["assets/eagler/lang/en_us.json"].decode("utf-8-sig"))
    eagler["eagler.menu.brand"]=""
    eagler["eagler.menu.rewrittenBy"]=""
    eagler_bytes=encode_json(eagler)

    replacements={}
    additions={}
    if "pack.mcmeta" in src_files:
        replacements["pack.mcmeta"]=pack_mcmeta_bytes
    else:
        additions["pack.mcmeta"]=pack_mcmeta_bytes

    # Install every official Minecraft language resource.
    for name,data in official.items():
        if name in src_files: replacements[name]=data
        else: additions[name]=data

    # Keep Eagler-specific UI usable in every locale by supplying an English
    # fallback file for each official locale. Vanilla/Minecraft strings still
    # come from the actual locale-specific Mojang files above.
    replacements["assets/eagler/lang/en_us.json"]=eagler_bytes
    for code in codes:
        name=f"assets/eagler/lang/{code}.json"
        if name=="assets/eagler/lang/en_us.json": continue
        if name in src_files: replacements[name]=eagler_bytes
        else: additions[name]=eagler_bytes

    rebuild(source,replacements,additions,sys.argv[3])

    check=parse_epk(sys.argv[3]); fm=file_map(check)
    # Validation of requested languages and title.
    for code in ("en_us","tr_tr","en_pt"):
        p=f"assets/minecraft/lang/{code}.json"
        if p not in fm: raise RuntimeError("rebuilt EPK missing "+p)
    ce=json.loads(fm["assets/eagler/lang/en_us.json"].decode("utf-8"))
    if ce.get("eagler.menu.brand")!="": raise RuntimeError("brand first line was not cleared")
    if ce.get("eagler.menu.rewrittenBy")!="": raise RuntimeError("brand second line was not cleared")

    # Count official locale resources actually present.
    present=[c for c in codes if f"assets/minecraft/lang/{c}.json" in fm]
    if len(present)!=len(codes):
        missing=sorted(set(codes)-set(present))
        raise RuntimeError("missing official locale files: "+", ".join(missing[:20]))

    report={
      "minecraft_version":version["id"],
      "language_metadata_source":"official 26.3 asset-index pack.mcmeta",
      "official_language_count":len(codes),
      "installed_language_count":len(present),
      "has_turkish":"tr_tr" in present,
      "has_pirate_speak":"en_pt" in present,
      "title_first_line":ce.get("eagler.menu.brand"),
      "title_second_line":ce.get("eagler.menu.rewrittenBy"),
      "languages":[{"code":c, **(meta[c] if isinstance(meta[c],dict) else {"name":str(meta[c])})} for c in codes]
    }
    Path(sys.argv[4]).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
