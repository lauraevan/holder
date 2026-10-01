#!/usr/bin/env python3
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wasm_gc_model import build_model

target = "mco.upload.select.world.none"
model = build_model(Path(sys.argv[1]), None)
globals_for_target = {int(g) for g, value in model["strings"].items() if value == target}
hits = []
for fid, fn in model["functions"].items():
    used = set(fn.get("strings", []))
    if used & globals_for_target:
        hits.append({
            "function": int(fid),
            "signature": {
                "params": fn.get("params"),
                "results": fn.get("results"),
                "ptypes": fn.get("ptypes"),
                "rtypes": fn.get("rtypes"),
            },
            "string_globals": sorted(used & globals_for_target),
            "calls": fn.get("calls"),
            "fields": fn.get("fields"),
            "allocs": fn.get("allocs"),
            "lines": fn.get("lines"),
        })
out={"target":target,"globals":sorted(globals_for_target),"hits":sorted(hits,key=lambda x:x["function"])}
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,indent=2))
