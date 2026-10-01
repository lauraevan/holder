#!/usr/bin/env python3
from pathlib import Path
import re, hashlib

for name in ("26.2.html","26.3.html"):
    p=Path("webmc/assets")/name
    b=p.read_bytes()
    s=b.decode("utf-8","replace")
    print("###",name)
    print("size",len(b),"sha256",hashlib.sha256(b).hexdigest())
    print("head",repr(s[:1200]))
    print("tail",repr(s[-800:]))
    for needle in ["Edit Profile","Singleplayer","Multiplayer","menu.singleplayer","menu.multiplayer","profile","eag-inline-wasm","wasm-br","classes.wasm","application/wasm","base64"]:
        xs=[m.start() for m in re.finditer(re.escape(needle),s,re.I)]
        print(needle, xs[:20], "count",len(xs))
        for i in xs[:3]:
            print(" context",repr(s[max(0,i-300):i+500]))
    # likely large encoded string assignments
    for pat in [r'([A-Za-z0-9_$.-]{3,40})\s*[:=]\s*["\']([A-Za-z0-9+/=]{100,})',
                r'data:application/wasm[^,]*,([A-Za-z0-9+/=]{100,})']:
        ms=list(re.finditer(pat,s))
        print("pattern",pat,"matches",len(ms))
        for m in ms[:10]:
            print(" enc",m.group(1)[:80], "len", len(m.group(m.lastindex)))
