#!/usr/bin/env python3
from pathlib import Path
import json, sys
from build_full_language_epk import parse_epk, rebuild, encode_json, file_map

src = Path(sys.argv[1])
out = Path(sys.argv[2])
report = Path(sys.argv[3])

epk = parse_epk(src)
fm = file_map(epk)
replacements = {}
changed = []
for name, data in fm.items():
    if not (name.startswith("assets/eagler/lang/") and name.endswith(".json")):
        continue
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except Exception:
        continue
    before = {
        "eagler.menu.brand": obj.get("eagler.menu.brand"),
        "eagler.menu.rewrittenBy": obj.get("eagler.menu.rewrittenBy"),
    }
    touched = False
    if "eagler.menu.brand" in obj and obj.get("eagler.menu.brand") != "":
        obj["eagler.menu.brand"] = ""
        touched = True
    if "eagler.menu.rewrittenBy" in obj and obj.get("eagler.menu.rewrittenBy") != "":
        obj["eagler.menu.rewrittenBy"] = ""
        touched = True
    if touched:
        replacements[name] = encode_json(obj)
        changed.append({"file": name, "before": before})

rebuild(epk, replacements, {}, out)

check = file_map(parse_epk(out))
left = []
for name, data in check.items():
    if not (name.startswith("assets/eagler/lang/") and name.endswith(".json")):
        continue
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except Exception:
        continue
    for key in ("eagler.menu.brand", "eagler.menu.rewrittenBy"):
        if key in obj and obj.get(key) != "":
            left.append({"file": name, "key": key, "value": obj.get(key)})
if left:
    raise SystemExit("branding remained: " + json.dumps(left[:20], ensure_ascii=False))

report.write_text(json.dumps({
    "changed_locale_files": len(changed),
    "changed": changed,
    "remaining_nonblank_branding_keys": left,
    "output_bytes": out.stat().st_size
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("changed locale files:", len(changed))
print("output bytes:", out.stat().st_size)
