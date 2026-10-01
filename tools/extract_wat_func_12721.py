#!/usr/bin/env python3
import sys

# Function 12721 has defined ordinal 12623 in the 26.2 client image.
TARGET_ORDINAL = 12623

ordinal = -1
capturing = False
out = []

for line in sys.stdin:
    stripped = line.lstrip()
    is_func = stripped.startswith("(func ")

    if is_func:
        ordinal += 1
        if capturing:
            # The next top-level defined function marks the end of the target.
            break
        if ordinal == TARGET_ORDINAL:
            capturing = True

    if capturing:
        out.append(line)

if not capturing:
    raise SystemExit(f"defined ordinal {TARGET_ORDINAL} not found; saw {ordinal + 1} functions")

sys.stdout.write("".join(out))
