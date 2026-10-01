#!/usr/bin/env python3
import argparse, hashlib, json
from pathlib import Path

FUNC_OFFSET = 21326385
FUNC_SIZE = 2529
FUNC_SHA256 = "28f2efc39b4dcd431a88ec7bf8002111ac7922a41f8d186c83d4831876b4fdb4"

# Wasm encoding of: br_table 0 1 36
OLD = bytes.fromhex("0e02000124")
# Redirect SINGLEPLAYER (ordinal 0) to the same branch as UPLOAD_WORLD (ordinal 1):
# br_table 1 1 36
NEW = bytes.fromhex("0e02010124")

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("report", type=Path)
    a=ap.parse_args()

    data=bytearray(a.src.read_bytes())
    body=bytes(data[FUNC_OFFSET:FUNC_OFFSET+FUNC_SIZE])
    if len(body)!=FUNC_SIZE:
        raise SystemExit(f"function body truncated: {len(body)}")
    got=sha(body)
    if got!=FUNC_SHA256:
        raise SystemExit(f"function 12945 hash mismatch: {got}")

    hits=[]
    pos=0
    while True:
        i=body.find(OLD,pos)
        if i<0: break
        hits.append(i)
        pos=i+1
    if len(hits)!=1:
        raise SystemExit(f"expected exactly one empty-world br_table in function 12945, found {hits}")

    rel=hits[0]
    absolute=FUNC_OFFSET+rel
    data[absolute:absolute+len(OLD)]=NEW

    patched_body=bytes(data[FUNC_OFFSET:FUNC_OFFSET+FUNC_SIZE])
    if patched_body.count(NEW)<1 or patched_body.count(OLD)!=0:
        raise SystemExit("branch patch verification failed")

    a.dst.write_bytes(data)
    report={
        "function":12945,
        "function_offset":FUNC_OFFSET,
        "function_size":FUNC_SIZE,
        "original_function_sha256":FUNC_SHA256,
        "patched_function_sha256":sha(patched_body),
        "module_sha256":sha(bytes(data)),
        "relative_patch_offset":rel,
        "absolute_patch_offset":absolute,
        "old_bytes":OLD.hex(),
        "new_bytes":NEW.hex(),
        "semantic_change":"WorldSelectionList empty SINGLEPLAYER branch now follows the normal NoWorldsEntry branch instead of auto-opening CreateWorldScreen"
    }
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
