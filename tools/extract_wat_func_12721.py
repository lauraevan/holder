#!/usr/bin/env python3
import sys

needle = "(func (;12721;)"
buf = ""
found = False
depth = 0
out = []
for chunk in iter(lambda: sys.stdin.read(65536), ""):
    if not found:
        buf += chunk
        i = buf.find(needle)
        if i < 0:
            buf = buf[-len(needle)*2:]
            continue
        found = True
        chunk = buf[i:]
        buf = ""
    for ch in chunk:
        out.append(ch)
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if found and depth == 0:
                sys.stdout.write("".join(out))
                sys.exit(0)
raise SystemExit("function 12721 not found")
