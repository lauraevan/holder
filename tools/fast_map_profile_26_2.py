#!/usr/bin/env python3
from pathlib import Path
import base64,re,brotli,json,sys
sys.path.insert(0,str(Path(__file__).parent))
from wasm_gc_model import build_model
src=Path("webmc/assets/26.2.html").read_text("utf-8",errors="replace")
m=re.search(r'<script type="application/octet-stream" id="eag-inline-wasm-br"[^>]*>\s*([A-Za-z0-9+/=\r\n]+?)\s*</script>',src,re.S)
comp=base64.b64decode(re.sub(r'\s+','',m.group(1)))
raw=brotli.decompress(comp)
Path("/tmp/client26.2.wasm").write_bytes(raw)
model=build_model(Path("/tmp/client26.2.wasm"),None)
strings={int(k):v for k,v in model["strings"].items()}
needles=("profile","singleplayer","multiplayer","menu.","title","language","options")
matched={g:v for g,v in strings.items() if any(n in v.lower() for n in needles)}
classes=[]
for g,c in model["classes"].items():
    n=(c.get("name") or "")
    if any(x in n.lower() for x in ("title","profile","option","language")):
        classes.append({"global":int(g),"name":n,"vtable":c.get("vtable"),"clinit":model.get("clinit",{}).get(g)})
funcs=[]
sg=set(matched)
for fid,f in model["functions"].items():
    hits=[g for g in f.get("strings",[]) if g in sg]
    if hits:
        funcs.append({"fid":int(fid),"lines":f["lines"],"strings":[[g,strings[g]] for g in hits],"calls":f["calls"],"allocs":f.get("allocs",[]),"type":f["type"],"p0type":f.get("p0type"),"fields":f.get("fields",[])[:20],"consts":f.get("consts",[])})
out={"raw_bytes":len(raw),"matched_strings":sorted([[g,v] for g,v in matched.items()]),"classes":classes,"functions":funcs}
Path("preview/26.3-asset-swap/profile-26.2-map.json").write_text(json.dumps(out,indent=2))
print("strings",len(matched),"classes",len(classes),"funcs",len(funcs))
