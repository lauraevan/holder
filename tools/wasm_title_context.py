#!/usr/bin/env python3
import brotli, string, sys
from pathlib import Path
raw=brotli.decompress(Path(sys.argv[1]).read_bytes())
offsets=[99631208,99631272,99950881,99950911,100520478,101694784,101748555,101901092,101905055,101907643,101915544]
def printable_runs(lo,hi):
    data=raw[max(0,lo):min(len(raw),hi)]
    base=max(0,lo)
    runs=[]; st=None
    for i,b in enumerate(data):
        ok=(32<=b<=126)
        if ok and st is None: st=i
        elif not ok and st is not None:
            if i-st>=4: runs.append((base+st,data[st:i].decode('latin1')))
            st=None
    if st is not None and len(data)-st>=4:runs.append((base+st,data[st:].decode('latin1')))
    return runs
lines=[]
for off in offsets:
    lines.append(f"## OFFSET {off}")
    for pos,s in printable_runs(off-300,off+300):
        lines.append(f"{pos}: {s}")
    lines.append("")
Path(sys.argv[2]).write_text("\n".join(lines),encoding="utf-8")
