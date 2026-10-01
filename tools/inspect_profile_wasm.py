#!/usr/bin/env python3
from pathlib import Path
import base64,re,brotli,json,sys
sys.path.insert(0,str(Path(__file__).parent))
from wasm_gc_model import build_model

def decode_html(src:Path,out:Path):
    s=src.read_text("utf-8",errors="replace")
    m=re.search(r'<script type="application/octet-stream" id="eag-inline-wasm-br"[^>]*>\s*([A-Za-z0-9+/=\r\n]+?)\s*</script>',s,re.S)
    if not m: raise SystemExit(f"client payload not found in {src}")
    comp=base64.b64decode(re.sub(r'\s+','',m.group(1)))
    raw=brotli.decompress(comp)
    out.write_bytes(raw)
    return len(comp),len(raw)

def relevant(model):
    strings={int(k):v for k,v in model["strings"].items()}
    needles=("profile","singleplayer","multiplayer","title","options","language")
    sm={g:v for g,v in strings.items() if any(n in v.lower() for n in needles)}
    classes=[]
    for g,c in model["classes"].items():
        n=(c.get("name") or "")
        if any(x in n.lower() for x in ("titlescreen","profile","optionsscreen","languagescreen","screen")):
            if any(x in n.lower() for x in ("title","profile","option","language")):
                classes.append((int(g),n,c.get("vtable"),model.get("clinit",{}).get(g)))
    funcs=[]
    sg=set(sm)
    for fid,f in model["functions"].items():
        hits=[g for g in f.get("strings",[]) if g in sg]
        if hits:
            funcs.append({
                "fid":int(fid),
                "lines":f["lines"],
                "strings":[[g,strings[g]] for g in hits],
                "calls":f["calls"],
                "allocs":f.get("allocs",[]),
                "p0type":f.get("p0type"),
                "type":f.get("type")
            })
    return sm,classes,funcs

def extract_funcs(wasm:Path,fids:set[int],out:Path):
    import subprocess
    p=subprocess.Popen(["wasm-tools","print",str(wasm)],stdout=subprocess.PIPE,text=True,errors="replace",bufsize=1<<20)
    cur=None; buf=[]; found={}
    fre=re.compile(r'^  \(func \(;([0-9]+);\)')
    for line in p.stdout:
        m=fre.match(line)
        if m:
            if cur in fids: found[cur]=''.join(buf)
            cur=int(m.group(1)); buf=[line] if cur in fids else []
        elif cur in fids:
            if line.startswith("  (") or line.startswith(")"):
                found[cur]=''.join(buf); cur=None; buf=[]
            else: buf.append(line)
    if cur in fids: found[cur]=''.join(buf)
    p.wait()
    with out.open("w") as fh:
        for fid in sorted(found):
            fh.write(f"\n;;;; FUNCTION {fid}\n")
            fh.write(found[fid])

report={}
for ver in ("26.2","26.3"):
    wasm=Path(f"/tmp/{ver}.wasm")
    comp,raw=decode_html(Path("webmc/assets")/f"{ver}.html",wasm)
    model=build_model(wasm,None)
    sm,classes,funcs=relevant(model)
    report[ver]={
      "compressed":comp,"raw":raw,
      "strings":sorted([[g,v] for g,v in sm.items()]),
      "classes":classes,
      "functions":funcs
    }
    fids={x["fid"] for x in funcs}
    extract_funcs(wasm,fids,Path("preview/26.3-asset-swap")/f"profile-relevant-{ver}.wat")
Path("preview/26.3-asset-swap/profile-wasm-report.json").write_text(json.dumps(report,indent=2))
print(json.dumps({v:{"strings":len(report[v]["strings"]),"classes":len(report[v]["classes"]),"functions":len(report[v]["functions"])} for v in report},indent=2))
