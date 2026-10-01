#!/usr/bin/env python3
import sys

# Function 12721 has defined ordinal 12623 in the 26.2 client image.
TARGET_ORDINAL = 12623

ordinal = -1
capturing = False
depth = 0
out = []

for line in sys.stdin:
    stripped = line.lstrip()
    if not capturing:
        # wasm-tools prints each defined function as a top-level "(func ..."
        # line. Imported funcs live inside "(import ...)" and are skipped.
        if stripped.startswith("(func "):
            ordinal += 1
            if ordinal == TARGET_ORDINAL:
                capturing = True
            else:
                continue
        else:
            continue

    for ch in line:
        out.append(ch)
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1

    if capturing and depth == 0:
        sys.stdout.write("".join(out))
        sys.exit(0)

raise SystemExit(f"defined ordinal {TARGET_ORDINAL} not found; saw {ordinal + 1} functions")
