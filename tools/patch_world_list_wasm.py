#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

# The exact function was independently identified from the current canonical
# 26.2 image by its use of "mco.upload.select.world.none".
ABSOLUTE_FUNCTION_INDEX = 12945
DEFINED_ORDINAL = 12847

# Wasm encoding of:
#   br_table 0 1 36
# SINGLEPLAYER ordinal 0 auto-opens CreateWorldScreen.
OLD = bytes.fromhex("0e02000124")
# Redirect ordinal 0 to the same empty-list branch as ordinal 1:
#   br_table 1 1 36
NEW = bytes.fromhex("0e02010124")

def sha(b):
    return hashlib.sha256(b).hexdigest()

def read_uleb(data, pos):
    value = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise EOFError("unexpected EOF reading ULEB")
        b = data[pos]
        pos += 1
        value |= (b & 0x7f) << shift
        if not (b & 0x80):
            return value, pos
        shift += 7
        if shift > 35:
            raise ValueError("ULEB too large")

def find_section(data, wanted):
    if data[:8] != b"\0asm\x01\0\0\0":
        raise ValueError("not a WebAssembly v1 module")
    pos = 8
    while pos < len(data):
        sid = data[pos]
        pos += 1
        size, pos = read_uleb(data, pos)
        start = pos
        end = start + size
        if end > len(data):
            raise EOFError("section extends past module")
        if sid == wanted:
            return start, end
        pos = end
    raise ValueError(f"section {wanted} not found")

def locate_defined_body(data, ordinal):
    start, end = find_section(data, 10)
    pos = start
    count, pos = read_uleb(data, pos)
    if ordinal < 0 or ordinal >= count:
        raise IndexError(f"defined ordinal {ordinal} outside code count {count}")
    for i in range(count):
        body_size, body_start = read_uleb(data, pos)
        body_end = body_start + body_size
        if body_end > end:
            raise EOFError(f"function body {i} extends past code section")
        if i == ordinal:
            return body_start, body_end
        pos = body_end
    raise AssertionError("unreachable")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("report", type=Path)
    a=ap.parse_args()

    data=bytearray(a.src.read_bytes())
    body_start, body_end = locate_defined_body(data, DEFINED_ORDINAL)
    body=bytes(data[body_start:body_end])

    hits=[]
    pos=0
    while True:
        i=body.find(OLD,pos)
        if i<0:
            break
        hits.append(i)
        pos=i+1
    if len(hits)!=1:
        raise SystemExit(
            f"function {ABSOLUTE_FUNCTION_INDEX} expected exactly one "
            f"br_table 0,1,36 encoding, found {hits}; "
            f"body_offset={body_start} size={len(body)} sha256={sha(body)}"
        )

    rel=hits[0]
    absolute=body_start+rel
    data[absolute:absolute+len(OLD)]=NEW

    patched_body=bytes(data[body_start:body_end])
    if patched_body.find(OLD) != -1:
        raise SystemExit("old empty-world branch still present after patch")
    if patched_body.count(NEW) < 1:
        raise SystemExit("patched empty-world branch not present")

    a.dst.write_bytes(data)
    report={
        "function":ABSOLUTE_FUNCTION_INDEX,
        "defined_ordinal":DEFINED_ORDINAL,
        "function_offset":body_start,
        "function_size":len(body),
        "original_function_sha256":sha(body),
        "patched_function_sha256":sha(patched_body),
        "original_module_sha256":sha(a.src.read_bytes()),
        "patched_module_sha256":sha(bytes(data)),
        "relative_patch_offset":rel,
        "absolute_patch_offset":absolute,
        "old_bytes":OLD.hex(),
        "new_bytes":NEW.hex(),
        "semantic_change":"Empty SINGLEPLAYER world list follows the normal NoWorldsEntry branch instead of auto-opening CreateWorldScreen"
    }
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
