#!/usr/bin/env python3
import json
from pathlib import Path
p=Path("preview/26.3-asset-swap/profile-26.2-map.json")
d=json.loads(p.read_text())
strings={int(g):v for g,v in d["matched_strings"]}
wanted_vals=["Edit Profile","menu.singleplayer","menu.multiplayer","menu.online","menu.options",
             "eaglercraft.menu.editProfile","editProfile.title"]
wanted={g:v for g,v in strings.items() if v in wanted_vals or "editprofile" in v.lower()}
classes=[c for c in d["classes"] if any(x in c["name"].lower() for x in ("titlescreen","profile"))]
fns=[]
for f in d["functions"]:
    hits=[[g,v] for g,v in f.get("strings",[]) if g in wanted]
    if hits:
        f2=dict(f); f2["wanted_strings"]=hits; fns.append(f2)
# caller graph among all mapped functions
byid={f["fid"]:f for f in d["functions"]}
target_ids={f["fid"] for f in fns}
callers={}
for f in d["functions"]:
    for t in f.get("calls",{}):
        ti=int(t)
        if ti in target_ids:
            callers.setdefault(str(ti),[]).append(f["fid"])
out={"wanted_strings":wanted,"classes":classes,"functions":fns,"callers":callers}
Path("preview/26.3-asset-swap/profile-26.2-focus.json").write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
