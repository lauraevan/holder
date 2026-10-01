#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

# Identified independently from the current canonical 26.2 WAT/model.
ABSOLUTE_FUNCTION_INDEX = 12945
NO_WORLDS_STRING_GLOBAL = 156617

# Wasm binary for: br_table 0 1 36
OLD = bytes.fromhex("0e02000124")
# Wasm binary for: br_table 1 1 36
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
        if shift > 70:
            raise ValueError("ULEB too large")

def encode_uleb(value):
    out=bytearray()
    while True:
        b=value & 0x7f
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

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

def iter_code_bodies(data):
    start, end=find_section(data,10)
    pos=start
    count,pos=read_uleb(data,pos)
    for ordinal in range(count):
        body_size,body_start=read_uleb(data,pos)
        body_end=body_start+body_size
        if body_end>end:
            raise EOFError(f"function body {ordinal} extends past code section")
        yield ordinal,body_start,body_end
        pos=body_end

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("src",type=Path)
    ap.add_argument("dst",type=Path)
    ap.add_argument("report",type=Path)
    a=ap.parse_args()

    original=a.src.read_bytes()
    data=bytearray(original)

    # global.get opcode is 0x23 followed by the global index as ULEB128.
    string_anchor=b"\x23"+encode_uleb(NO_WORLDS_STRING_GLOBAL)
    candidates=[]
    for ordinal,start,end in iter_code_bodies(data):
        body=bytes(data[start:end])
        branch_hits=[]
        p=0
        while True:
            i=body.find(OLD,p)
            if i<0: break
            branch_hits.append(i)
            p=i+1
        if string_anchor in body and branch_hits:
            candidates.append({
                "ordinal":ordinal,
                "start":start,
                "end":end,
                "branch_hits":branch_hits,
                "sha256":sha(body)
            })

    if len(candidates)!=1:
        raise SystemExit(
            "expected one code body containing both the NoWorldsEntry string "
            f"global and br_table 0,1,36, found {candidates}"
        )

    target=candidates[0]
    if len(target["branch_hits"])!=1:
        raise SystemExit(f"target body has ambiguous branch sites: {target}")

    rel=target["branch_hits"][0]
    absolute=target["start"]+rel
    data[absolute:absolute+len(OLD)]=NEW

    patched_body=bytes(data[target["start"]:target["end"]])
    if OLD in patched_body:
        raise SystemExit("old empty-world branch still present after patch")
    if NEW not in patched_body:
        raise SystemExit("new empty-world branch missing after patch")

    a.dst.write_bytes(data)
    report={
        "identified_absolute_function":ABSOLUTE_FUNCTION_INDEX,
        "discovered_defined_ordinal":target["ordinal"],
        "function_offset":target["start"],
        "function_size":target["end"]-target["start"],
        "no_worlds_string_global":NO_WORLDS_STRING_GLOBAL,
        "string_anchor_bytes":string_anchor.hex(),
        "original_function_sha256":target["sha256"],
        "patched_function_sha256":sha(patched_body),
        "original_module_sha256":sha(original),
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
