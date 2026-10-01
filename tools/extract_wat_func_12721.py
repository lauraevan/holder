#!/usr/bin/env python3
import sys

TARGET = "(func (;12721;)"
capturing = False
out = []

for line in sys.stdin:
    stripped = line.lstrip()
    if not capturing:
        if stripped.startswith(TARGET):
            capturing = True
            out.append(line)
        continue

    if stripped.startswith("(func "):
        break
    out.append(line)

if not capturing:
    raise SystemExit("literal function header (;12721;) not found")

sys.stdout.write("".join(out))
