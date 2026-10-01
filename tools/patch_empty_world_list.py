#!/usr/bin/env python3
import brotli, hashlib, json, sys
from pathlib import Path

OFFSET=21326385
SIZE=2529
EXPECTED_BODY_SHA="28f2efc39b4dcd431a88ec7bf8002111ac7922a41f8d186c83d4831876b4fdb4"
PATTERN=b"\x45\x0d\x02"  # i32.eqz ; br_if 2
REPLACEMENT=b"\x45\x0c\x02"  # i32.eqz ; br 2 (always take normal-list path)

src=Path(sys.argv[1]).read_bytes()
if src[:8] != b"\x00asm\x01\x00\x00\x00":
    raise SystemExit("not wasm")
body=src[OFFSET:OFFSET+SIZE]
sha=hashlib.sha256(body).hexdigest()
if sha != EXPECTED_BODY_SHA:
    raise SystemExit(f"function body sha mismatch: {sha}")
positions=[]
p=0
while True:
    i=body.find(PATTERN,p)
    if i<0: break
    positions.append(i); p=i+1
if len(positions)!=1:
    raise SystemExit(f"expected exactly one i32.eqz/br_if2 pattern in function 12945, found {positions}")
rel=positions[0]
patched=bytearray(src)
patched[OFFSET+rel:OFFSET+rel+3]=REPLACEMENT
newbody=bytes(patched[OFFSET:OFFSET+SIZE])
if newbody.count(REPLACEMENT)<1:
    raise SystemExit("replacement missing")
Path(sys.argv[2]).write_bytes(patched)
Path(sys.argv[3]).write_bytes(brotli.compress(bytes(patched), quality=11))
report={
  "function":12945,
  "function_offset":OFFSET,
  "function_size":SIZE,
  "original_function_sha256":sha,
  "patched_function_sha256":hashlib.sha256(newbody).hexdigest(),
  "patch_relative_offset":rel,
  "patch_absolute_offset":OFFSET+rel,
  "original_bytes":PATTERN.hex(),
  "patched_bytes":REPLACEMENT.hex(),
  "original_wasm_sha256":hashlib.sha256(src).hexdigest(),
  "patched_wasm_sha256":hashlib.sha256(patched).hexdigest(),
  "compressed_sha256":hashlib.sha256(Path(sys.argv[3]).read_bytes()).hexdigest(),
  "compressed_bytes":Path(sys.argv[3]).stat().st_size,
}
Path(sys.argv[4]).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
