#!/usr/bin/env python3
import json, subprocess, re
from pathlib import Path

BR="origin/fix-singleplayer-integrated-server"
def gitshow(path):
    return subprocess.check_output(["git","show",f"{BR}:{path}"])

subprocess.run(["git","fetch","origin","fix-singleplayer-integrated-server:refs/remotes/origin/fix-singleplayer-integrated-server"],check=True)
report=json.loads(gitshow("preview/26.3-asset-swap/profile-wasm-report.json"))
wanted_vals={"Edit Profile","menu.singleplayer","menu.multiplayer","eagler.menu.profile"}

summary={}
selected={}
for ver in ("26.2","26.3"):
    d=report[ver]
    strings={int(g):v for g,v in d["strings"]}
    wanted={g:v for g,v in strings.items() if v in wanted_vals}
    funcs=[]
    for f in d["functions"]:
        hits=[[int(g),strings[int(g)]] for g in f.get("strings",[]) if int(g) in wanted]
        if len(hits)>=2 or any(v=="Edit Profile" for _,v in hits):
            funcs.append({"fid":int(f["fid"]),"lines":f["lines"],"hits":hits,"calls":f["calls"],"allocs":f.get("allocs",[]),"p0type":f.get("p0type"),"type":f.get("type")})
    summary[ver]={"wanted":wanted,"functions":funcs}
    selected[ver]={x["fid"] for x in funcs}

def extract(path, ids):
    p=subprocess.Popen(["git","show",f"{BR}:{path}"],stdout=subprocess.PIPE,text=True,errors="replace",bufsize=1<<20)
    out=[]; keep=False
    marker=re.compile(r'^;;;; FUNCTION (\d+)')
    for line in p.stdout:
        m=marker.match(line)
        if m:
            keep=int(m.group(1)) in ids
        if keep: out.append(line)
    p.wait()
    return ''.join(out)

Path("preview/26.3-asset-swap/title-profile-function-map.json").write_text(json.dumps(summary,indent=2))
Path("preview/26.3-asset-swap/title-profile-26.2.wat").write_text(extract("preview/26.3-asset-swap/profile-relevant-26.2.wat",selected["26.2"]))
Path("preview/26.3-asset-swap/title-profile-26.3.wat").write_text(extract("preview/26.3-asset-swap/profile-relevant-26.3.wat",selected["26.3"]))
print(json.dumps(summary,indent=2))
