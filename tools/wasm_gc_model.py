#!/usr/bin/env python3
"""Extract a structural model from a TeaVM Wasm-GC image.

WABT cannot parse these images (GC type forms such as 0x5e), so this tool
streams the text produced by ``wasm-tools print`` instead of decoding the
binary code section itself.

What it recovers (all from evidence present in the binary, nothing guessed):

* the TeaVM string-constant pool (data segment 0) mapped onto the string
  globals that the start function initialises, in order;
* class registrations: class global -> Java class name, superclass,
  interfaces, vtable global;
* vtable slots: for every class, which function fills each slot, keyed by the
  vtable struct type that *introduced* the slot;
* reflection method tables: per class, method name, modifiers, return type and
  parameter types;
* per-function facts: signature, size, direct calls, string constants used.

Usage:
    python tools/wasm_gc_model.py IMAGE.wasm OUT.json [--wat cached.wat]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Binary helpers (only the data section is read from the binary directly)
# ---------------------------------------------------------------------------

def _leb(buf: bytes, i: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if b < 0x80:
            return result, i


def data_segments(image: bytes) -> list[bytes]:
    """Return the payload of each active data segment."""
    i = 8
    segments: list[bytes] = []
    while i < len(image):
        section_id = image[i]
        i += 1
        size, i = _leb(image, i)
        end = i + size
        if section_id == 11:
            count, j = _leb(image, i)
            for _ in range(count):
                flags, j = _leb(image, j)
                if flags == 0:
                    # i32.const <offset> end
                    j += 1
                    while image[j] & 0x80:
                        j += 1
                    j += 2
                elif flags == 2:
                    _, j = _leb(image, j)
                    j += 1
                    while image[j] & 0x80:
                        j += 1
                    j += 2
                length, j = _leb(image, j)
                segments.append(image[j:j + length])
                j += length
        i = end
    return segments


class StringPoolReader:
    """Mirror of the TeaVM pool decoder (length in UTF-16 units, UTF-8 body)."""

    def __init__(self, pool: bytes):
        self.pool = pool
        self.pos = 0

    def _byte(self) -> int:
        b = self.pool[self.pos]
        self.pos += 1
        return b

    def next(self) -> str:
        length = shift = 0
        while True:
            b = self._byte()
            length |= (b & 0x7F) << shift
            if not b & 0x80:
                break
            shift += 7
        units: list[int] = []
        while len(units) < length:
            b = self._byte()
            if b < 0x80:
                units.append(b)
            elif b & 0xE0 == 0xC0:
                units.append(((b & 0x1F) << 6) | (self._byte() & 0x3F))
            elif b & 0xF0 == 0xE0:
                c = (b & 0x0F) << 12
                c |= (self._byte() & 0x3F) << 6
                c |= self._byte() & 0x3F
                units.append(c)
            elif b & 0xF8 == 0xF0:
                c = (b & 0x07) << 18
                c |= (self._byte() & 0x3F) << 12
                c |= (self._byte() & 0x3F) << 6
                c |= self._byte() & 0x3F
                units.append(0xD800 | (((c - 0x10000) >> 10) & 0x3FF))
                units.append(0xDC00 | (c & 0x3FF))
            else:
                raise ValueError(f"invalid pool byte {b:#x} at {self.pos - 1}")
        raw = b"".join(u.to_bytes(2, "little") for u in units)
        return raw.decode("utf-16-le", "surrogatepass").encode("utf-8", "replace").decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# WAT streaming
# ---------------------------------------------------------------------------

FUNC_RE = re.compile(r"^  \(func \(;(\d+);\) \(type (\d+)\)(.*)$")
IMPORT_FUNC_RE = re.compile(r'^  \(import "([^"]+)" "([^"]+)" \(func \(;(\d+);\) \(type (\d+)\)')
TYPE_RE = re.compile(r"\(type \(;(\d+);\) (.*)$")
GLOBAL_RE = re.compile(r"^  \(global \(;(\d+);\) (.*)$")
EXPORT_RE = re.compile(r'^  \(export "([^"]+)" \((func|global|memory|tag) (\d+)\)\)')
START_RE = re.compile(r"^  \(start (\d+)\)")
VALTYPE_RE = re.compile(r"\(ref(?: null)? \d+\)|i32|i64|f32|f64|v128|externref|anyref|eqref|funcref|i31ref|structref|arrayref|nullref|exnref")


def value_kinds(text: str) -> list[str]:
    kinds = []
    for tok in VALTYPE_RE.findall(text):
        kinds.append("ref" if tok.startswith("(ref") or tok.endswith("ref") else tok)
    return kinds


def ref_type_ids(rest: str, which: str) -> list[int | None]:
    """Concrete type index of each param/result (None for non-ref/abstract)."""
    out: list[int | None] = []
    for m in re.finditer(r"\((param|result)((?:[^()]|\([^()]*\))*)\)", rest):
        if m.group(1) != which:
            continue
        for tok in VALTYPE_RE.findall(m.group(2)):
            r = re.match(r"\(ref(?: null)? (\d+)\)", tok)
            out.append(int(r.group(1)) if r else None)
    return out


def parse_signature(rest: str) -> tuple[list[str], list[str]]:
    params: list[str] = []
    results: list[str] = []
    for m in re.finditer(r"\((param|result)((?:[^()]|\([^()]*\))*)\)", rest):
        (params if m.group(1) == "param" else results).extend(value_kinds(m.group(2)))
    return params, results


def wat_lines(wasm: Path, cached: Path | None):
    if cached and cached.exists():
        with cached.open("r", encoding="utf-8", errors="replace") as fh:
            yield from fh
        return
    proc = subprocess.Popen(["wasm-tools", "print", str(wasm)], stdout=subprocess.PIPE,
                            text=True, errors="replace", bufsize=1 << 20)
    assert proc.stdout is not None
    yield from proc.stdout
    if proc.wait() != 0:
        raise SystemExit("wasm-tools print failed")


# ---------------------------------------------------------------------------
# Model extraction
# ---------------------------------------------------------------------------

def build_model(wasm: Path, cached_wat: Path | None) -> dict:
    types: dict[int, dict] = {}
    type_sigs: dict[int, tuple[list[str], list[str]]] = {}
    import_types: dict[int, int] = {}
    globals_decl: dict[int, str] = {}
    imports: dict[int, str] = {}
    exports: dict[str, str] = {}
    start = None
    functions: dict[int, dict] = {}
    bodies_of_interest: dict[int, list[str]] = {}

    cur: dict | None = None
    cur_lines: list[str] | None = None
    cur_fid = -1
    prev_s = ""
    prev2_s = ""
    alloc_pairs: dict[tuple[int, int], int] = defaultdict(int)
    # Bodies are retained only for small functions (string-pool decoder chain)
    # and for parameterless void functions (start-function registration code).
    SMALL_BODY = 400

    for line in wat_lines(wasm, cached_wat):
        if cur is not None:
            if line.startswith("  (") or line.startswith(")"):
                cur = None
                cur_lines = None
            else:
                s = line.strip()
                cur["lines"] += 1
                if s.endswith(" 0") and s.startswith("struct.set ") and prev_s.startswith("global.get "):
                    # `global.get VT; struct.set T 0` stores a vtable into a
                    # freshly allocated instance of struct type T.
                    alloc_pairs[(int(s.split()[1]), int(prev_s[11:]))] += 1
                    cur["allocs"].add(int(prev_s[11:]))
                if s.startswith("global.set ") and len(cur["gsets"]) < 400:
                    g = int(s[11:])
                    if g not in cur["gsets"]:
                        cur["gsets"].append(g)
                if s.startswith("struct.set ") and prev_s.startswith("ref.func ") and prev2_s.startswith("global.get "):
                    # `global.get C; ref.func F; struct.set T k`: a Class field
                    # overwritten with a function (used by <clinit> to mark done)
                    _, t, k = s.split()
                    cur["class_fn_sets"].append([int(prev2_s[11:]), int(prev_s[9:]), int(t), int(k)])
                prev2_s = prev_s
                prev_s = s
                if s.startswith("call "):
                    tgt = s[5:]
                    if tgt.isdigit():
                        cur["calls"][int(tgt)] = cur["calls"].get(int(tgt), 0) + 1
                        # struct types allocated shortly before this call site:
                        # evidence that the callee is the constructor invoked on
                        # a fresh object (see recover_names this-type+ctor)
                        recent = {t for ln, t in cur["recent_new"] if cur["lines"] - ln <= 60}
                        if recent:
                            site = cur["site_allocs"].setdefault(int(tgt), {})
                            for t in recent:
                                site[t] = site.get(t, 0) + 1
                elif s.startswith(("struct.new ", "struct.new_default ")):
                    parts = s.split()
                    if len(parts) == 2 and parts[1].isdigit():
                        cur["recent_new"] = [x for x in cur["recent_new"] if cur["lines"] - x[0] <= 60]
                        cur["recent_new"].append((cur["lines"], int(parts[1])))
                elif s.startswith("global.get "):
                    cur["globals"].add(int(s[11:]))
                elif s.startswith("ref.func "):
                    cur["reffuncs"].add(int(s[9:]))
                elif s.startswith(("struct.get ", "struct.get_s ", "struct.get_u ", "struct.set ")):
                    parts = s.split()
                    if len(parts) == 3 and cur["lines"] <= 60:
                        cur["fields"].add((parts[0] == "struct.set", int(parts[1]), int(parts[2])))
                elif s.startswith("i32.const ") and cur["lines"] <= 25:
                    cur["consts"].append(int(s[10:]))
                elif s.startswith("ref.cast (ref") and cur["cast"] is None:
                    cm = re.search(r"(\d+)\)$", s)
                    cur["cast"] = int(cm.group(1)) if cm else None
                elif s.startswith("call_ref") or s.startswith("return_call_ref"):
                    cur["indirect"] += 1
                if cur_lines is not None:
                    cur_lines.append(s)
                    if len(cur_lines) > SMALL_BODY and not cur["void"]:
                        del bodies_of_interest[cur_fid]
                        cur_lines = None
                continue

        m = FUNC_RE.match(line)
        if m:
            fid, tid = int(m.group(1)), int(m.group(2))
            params, results = parse_signature(m.group(3))
            p0 = re.match(r"\s*\(param \(ref(?: null)? (\d+)\)", m.group(3))
            cur = {"type": tid, "params": params, "results": results, "lines": 0,
                   "ptypes": ref_type_ids(m.group(3), "param"),
                   "rtypes": ref_type_ids(m.group(3), "result"),
                   "p0type": int(p0.group(1)) if p0 else None,
                   "calls": {}, "globals": set(), "reffuncs": set(), "indirect": 0, "fields": set(),
                   "consts": [], "cast": None, "allocs": set(), "gsets": [], "class_fn_sets": [],
                   "recent_new": [], "site_allocs": {},
                   "void": not params and not results and "(local" not in m.group(3)}
            functions[fid] = cur
            cur_fid = fid
            cur_lines = []
            bodies_of_interest[fid] = cur_lines
            continue
        if line.startswith("    (type") or line.startswith("  (type") or line.startswith("  (rec"):
            for tm in re.finditer(r"\(type \(;(\d+);\) ", line):
                tid = int(tm.group(1))
                rest = line[tm.end():]
                sub = re.match(r"\(sub (?:final )?(\d+)?\s*\((struct|array|func)", rest)
                kind = None
                sup = None
                if sub:
                    sup = int(sub.group(1)) if sub.group(1) else None
                    kind = sub.group(2)
                else:
                    km = re.match(r"\((struct|array|func)", rest)
                    kind = km.group(1) if km else None
                entry = {"kind": kind, "super": sup}
                if kind == "struct":
                    entry["fields"] = rest.count("(field")
                    entry["field_kinds"] = [
                        "ref" if "ref" in fm.group(1) else fm.group(1).replace("mut", "").strip("() ")
                        for fm in re.finditer(r"\(field ((?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)", rest)]
                if kind == "func":
                    type_sigs[tid] = parse_signature(rest)
                types[tid] = entry
            continue
        m = IMPORT_FUNC_RE.match(line)
        if m:
            imports[int(m.group(3))] = f"{m.group(1)}.{m.group(2)}"
            import_types[int(m.group(3))] = int(m.group(4))
            continue
        m = GLOBAL_RE.match(line)
        if m:
            globals_decl[int(m.group(1))] = m.group(2)
            continue
        m = EXPORT_RE.match(line)
        if m:
            exports[m.group(1)] = f"{m.group(2)} {m.group(3)}"
            continue
        m = START_RE.match(line)
        if m:
            start = int(m.group(1))

    if start is None:
        raise SystemExit("image has no start function")
    init_funcs = [f for f in _ordered_calls(bodies_of_interest.get(start, []))]
    init_bodies = {f: bodies_of_interest[f] for f in init_funcs if f in bodies_of_interest}
    pool_reader_chain = _find_pool_init(functions, bodies_of_interest, imports)
    # Registration code: start callees first, then any other parameterless
    # void function (TeaVM builds reflection tables lazily in such functions).
    start_set = set(init_funcs)
    meta_funcs = init_funcs + sorted(f for f, fn in functions.items()
                                     if fn["void"] and f not in start_set and f != start and f in bodies_of_interest)
    meta_bodies = {f: bodies_of_interest[f] for f in meta_funcs}
    del bodies_of_interest

    image = wasm.read_bytes()
    segments = data_segments(image)
    strings = _decode_strings(segments[0], init_funcs, init_bodies, pool_reader_chain)

    classes, vtables, reflection, field_reflection, array_classes = _interpret_class_init(meta_funcs, meta_bodies, globals_decl, strings)

    # <clinit>: the function that overwrites its class's init hook with the
    # empty function (`global.get C; ref.func EMPTY; struct.set Class k`).
    clinit_of: dict[str, int] = {}
    hook_counts: dict[tuple[int, int], int] = defaultdict(int)
    for fid, f in functions.items():
        for g, fn_ref, t, k in f["class_fn_sets"]:
            if str(g) in classes and fid not in init_funcs:
                hook_counts[(t, k)] += 1
    if hook_counts:
        hook = max(hook_counts.items(), key=lambda kv: kv[1])[0]
        for fid, f in functions.items():
            if fid in init_funcs or fid == start:
                continue
            for g, fn_ref, t, k in f["class_fn_sets"]:
                if (t, k) == hook and str(g) in classes:
                    clinit_of[str(g)] = fid

    # Instance struct type -> class, via the vtable stored at allocation.
    instance_types: dict[str, list] = defaultdict(list)
    for (t, g), n in alloc_pairs.items():
        vt = vtables.get(str(g))
        if vt and vt.get("class") is not None:
            instance_types[str(t)].append(vt["class"])

    for fid, f in functions.items():
        f["strings"] = sorted(g for g in f["globals"] if g in strings)
        f["globals"] = sorted(f["globals"])
        f["reffuncs"] = sorted(f["reffuncs"])
        # (is_store, struct type, field index) for accesses in the first 60 lines
        f["fields"] = sorted([int(w), t, k] for w, t, k in f["fields"])
        if f["lines"] > 25:
            f["consts"] = []
        # classes this function instantiates (vtable globals stored at allocation)
        f["allocs"] = sorted(vtables[str(g)]["class"] for g in f["allocs"]
                             if str(g) in vtables and vtables[str(g)].get("class") is not None)
        f.pop("void", None)
        f.pop("class_fn_sets", None)
        f.pop("recent_new", None)
        # {callee: {struct type: call sites of callee within 60 lines after a
        # struct.new of that type}}; JSON keys become strings
        f["site_allocs"] = {str(c): {str(t): n for t, n in ts.items()} for c, ts in f["site_allocs"].items()}

    return {
        "image": str(wasm.name),
        "start": start,
        "exports": exports,
        "imports": {str(k): v for k, v in imports.items()},
        "import_types": {str(k): v for k, v in import_types.items()},
        # function types: [param kinds, result kinds] (calls, imports, block types)
        "func_types": {str(k): [p, r] for k, (p, r) in type_sigs.items()},
        "types": {str(k): v for k, v in types.items()},
        "global_types": {str(k): _global_ref_type(v) for k, v in globals_decl.items()},
        "strings": {str(k): v for k, v in strings.items()},
        "classes": classes,
        "vtables": vtables,
        "reflection": reflection,
        "field_reflection": field_reflection,
        "array_classes": array_classes,
        "instance_types": {k: sorted(set(v)) for k, v in instance_types.items()},
        "clinit": clinit_of,
        # kinds of globals written by static initialisers (for static fields)
        "global_kinds": {str(g): _global_kind(globals_decl.get(g, ""), types)
                         for fid in set(clinit_of.values()) for g in functions[fid]["gsets"]},
        "functions": {str(k): v for k, v in functions.items()},
        "init_functions": init_funcs,
    }


def _global_kind(decl: str, types: dict) -> str:
    """Value kind of a global: i32/i64/f32/f64, "func" for function refs, else "ref"."""
    m = re.match(r"\((?:mut )?(i32|i64|f32|f64)\)|(i32|i64|f32|f64)\b", decl)
    if m:
        return m.group(1) or m.group(2)
    m = re.search(r"\(ref(?: null)? (\d+)\)", decl)
    if m and types.get(int(m.group(1)), {}).get("kind") == "func":
        return "func"
    if "funcref" in decl.split(")")[0]:
        return "func"
    return "ref"


def _ordered_calls(body: list[str]) -> list[int]:
    out = []
    for s in body:
        if s.startswith("call ") and s[5:].isdigit():
            out.append(int(s[5:]))
    return out


def _global_ref_type(decl: str) -> int | None:
    m = re.match(r"\((?:mut )?\(ref(?: null)? (\d+)\)", decl)
    if m:
        return int(m.group(1))
    m = re.match(r"\(ref(?: null)? (\d+)\)", decl)
    return int(m.group(1)) if m else None


def _find_pool_init(functions, bodies, imports) -> dict:
    """Locate readByte -> readString -> initOne -> initArray by shape."""
    read_byte = None
    for fid, body in bodies.items():
        if len(body) < 12 and any(s == "i32.load8_u" for s in body) and any(s.startswith("global.set") for s in body):
            read_byte = fid
            break
    if read_byte is None:
        raise SystemExit("could not locate string pool byte reader")

    def callers(target):
        return [fid for fid, f in functions.items() if target in f["calls"]]

    read_string = callers(read_byte)
    init_one = [c for r in read_string for c in callers(r)]
    init_array = [c for r in init_one for c in callers(r)]
    if len(init_array) != 1:
        raise SystemExit(f"ambiguous pool init chain: {read_string} {init_one} {init_array}")
    array_type = None
    for s in bodies[init_array[0]]:
        m = re.match(r"array.get (\d+)", s)
        if m:
            array_type = int(m.group(1))
    return {"read_byte": read_byte, "read_string": read_string, "init_one": init_one,
            "init_array": init_array[0], "array_type": array_type}


def _decode_strings(pool: bytes, init_funcs, init_bodies, chain) -> dict[int, str]:
    marker = f"array.new_fixed {chain['array_type']} "
    order: list[int] = []
    for fid in init_funcs:
        run: list[int] = []
        for s in init_bodies.get(fid, []):
            if s.startswith("global.get "):
                run.append(int(s[11:]))
            elif s.startswith(marker):
                n = int(s.split()[-1])
                if n != len(run):
                    raise SystemExit(f"string array length mismatch in func {fid}")
                order.extend(run)
                run = []
            else:
                run = []
    reader = StringPoolReader(pool)
    out = {g: reader.next() for g in order}
    if reader.pos != len(pool):
        print(f"warning: pool not fully consumed ({reader.pos}/{len(pool)})", file=sys.stderr)
    return out


def _interpret_class_init(meta_funcs, meta_bodies, globals_decl, strings):
    """Symbolically execute the class-registration code in the start callees and lazy
    reflection initialisers.

    Only the handful of opcodes used by registration code are modelled;
    anything else clears the symbolic stack.
    """
    # Field layout of TeaVM's Class struct observed in the 26.x client/server
    # images. Other TeaVM builds (e.g. the mesh worker) shift every field by
    # the same amount, so all offsets are rebased on the detected name field.
    CLASS_TYPE_FIELD_NAME = 19
    CLASS_FIELD_SUPER = 12
    CLASS_FIELD_INTERFACES = 26
    CLASS_FIELD_METHODS = 28
    CLASS_FIELD_FIELDS = 27
    CLASS_FIELD_ARRAY_ITEM_FN = 29  # function hook; set on array classes and some others (see recover_names)

    classes: dict[int, dict] = defaultdict(dict)
    vtables: dict[int, dict] = defaultdict(lambda: {"class": None, "slots": []})
    reflection: dict[int, list] = {}
    field_reflection: dict[int, list] = {}
    array_classes: set[int] = set()

    # Discover the Class struct type and its name field from the pattern
    #   global.get <class>; global.get <string const>; struct.set <T> <k>
    # and the class-registration helper from
    #   global.get <class>; i32.const; i32.const; call <fn>
    pattern_counts: dict[tuple[int, int], int] = defaultdict(int)
    register_counts: dict[int, int] = defaultdict(int)
    for fid in meta_funcs:
        body = meta_bodies.get(fid, [])
        for i in range(2, len(body)):
            m = re.match(r"struct.set (\d+) (\d+)$", body[i])
            if m and body[i - 1].startswith("global.get ") and body[i - 2].startswith("global.get "):
                if int(body[i - 1][11:]) in strings:
                    pattern_counts[(int(m.group(1)), int(m.group(2)))] += 1
            if i >= 3 and body[i].startswith("call ") and body[i - 1].startswith("i32.const") \
                    and body[i - 2].startswith("i32.const") and body[i - 3].startswith("global.get"):
                register_counts[int(body[i][5:])] += 1
    (class_type, name_field), _ = max(pattern_counts.items(), key=lambda kv: kv[1])
    register_fn = max(register_counts.items(), key=lambda kv: kv[1])[0]
    if name_field != CLASS_TYPE_FIELD_NAME:
        shift = name_field - CLASS_TYPE_FIELD_NAME
        print(f"note: Class struct fields shifted by {shift:+d}", file=sys.stderr)
        CLASS_TYPE_FIELD_NAME += shift
        CLASS_FIELD_SUPER += shift
        CLASS_FIELD_INTERFACES += shift
        CLASS_FIELD_METHODS += shift
        CLASS_FIELD_FIELDS += shift
        CLASS_FIELD_ARRAY_ITEM_FN += shift
    link_fn = None
    method_counts: dict[int, int] = defaultdict(int)

    for fid in meta_funcs:
        stack: list = []
        for s in meta_bodies.get(fid, []):
            op, _, arg = s.partition(" ")
            if op == "global.get":
                stack.append(("g", int(arg)))
            elif op == "i32.const":
                stack.append(("i", int(arg)))
            elif op == "ref.null":
                stack.append(None)
            elif op == "ref.func":
                stack.append(("f", int(arg)))
            elif op == "array.new_fixed":
                _, n = arg.split()
                n = int(n)
                items = stack[len(stack) - n:] if n else []
                del stack[len(stack) - n:]
                stack.append(("list", items))
            elif op == "struct.new":
                t = int(arg)
                if len(stack) >= 6:
                    rec = stack[-6:]
                    del stack[-6:]
                    stack.append(("rec", t, rec))
                    method_counts[t] += 1
                else:
                    stack.clear()
            elif op == "call":
                target = int(arg)
                if target == register_fn and len(stack) >= 3 and stack[-3] and stack[-3][0] == "g" and stack[-2] and stack[-2][0] == "i" and stack[-1] and stack[-1][0] == "i":
                    c = stack[-3][1]
                    classes[c]["register"] = [stack[-2][1], stack[-1][1]]
                    classes[c]["register_fn"] = target
                    del stack[-3:]
                elif (link_fn is None or target == link_fn) and len(stack) >= 2 and stack[-2] and stack[-2][0] == "g" \
                        and stack[-1] and stack[-1][0] == "g" and "register" in classes.get(stack[-1][1], {}):
                    link_fn = target
                    vt, c = stack[-2][1], stack[-1][1]
                    vtables[vt]["class"] = c
                    classes[c]["vtable"] = vt
                    del stack[-2:]
                elif len(stack) >= 1 and stack[-1] and stack[-1][0] == "g":
                    stack[-1] = ("arrayof", stack[-1][1])
                else:
                    stack.clear()
            elif op == "struct.get" and stack and stack[-1] and stack[-1][0] == "arrayof":
                continue  # array class lookup: `global.get C; call arrayOf; struct.get Class k`
            elif op == "struct.set":
                t, k = (int(x) for x in arg.split())
                if len(stack) < 2:
                    stack.clear()
                    continue
                obj, val = stack[-2], stack[-1]
                del stack[-2:]
                if not obj or obj[0] != "g":
                    continue
                g = obj[1]
                if t == class_type:
                    if k == CLASS_TYPE_FIELD_NAME and val and val[0] == "g":
                        classes[g]["name_global"] = val[1]
                    elif k == CLASS_FIELD_SUPER and val and val[0] == "g":
                        classes[g]["super"] = val[1]
                    elif k == CLASS_FIELD_INTERFACES and val and val[0] == "list":
                        classes[g]["interfaces"] = [x[1] for x in val[1] if x and x[0] == "g"]
                    elif k == CLASS_FIELD_METHODS and val and val[0] == "list":
                        reflection[g] = [_method_record(r) for r in val[1] if r and r[0] == "rec"]
                    elif k == CLASS_FIELD_FIELDS and val and val[0] == "list":
                        field_reflection[g] = [_field_record(r) for r in val[1] if r and r[0] == "rec"]
                    elif val and val[0] == "f":
                        classes[g].setdefault("funcs", {})[str(k)] = val[1]
                        if k == CLASS_FIELD_ARRAY_ITEM_FN:
                            array_classes.add(g)
                elif val and val[0] == "f":
                    vtables[g]["slots"].append([t, k, val[1]])
            else:
                stack.clear()

    for c, info in classes.items():
        if "name_global" in info:
            info["name"] = strings.get(info["name_global"])
    return ({str(k): v for k, v in classes.items() if "register" in v or "name_global" in v},
            {str(k): v for k, v in vtables.items()},
            {str(k): v for k, v in reflection.items()},
            {str(k): v for k, v in field_reflection.items()},
            sorted(array_classes))


def _field_record(rec):
    _, _, (name, mods, access, ftype, _getter, _setter) = rec
    return {
        "name": name[1] if name and name[0] == "g" else None,
        "modifiers": mods[1] if mods and mods[0] == "i" else None,
        "access": access[1] if access and access[0] == "i" else None,
        "type": ftype[1] if ftype and ftype[0] == "g" else (["[]", ftype[1]] if ftype and ftype[0] == "arrayof" else None),
    }


def _method_record(rec):
    _, _, (name, mods, access, ret, params, caller) = rec

    def cls(v):
        if v is None:
            return None
        if v[0] == "g":
            return v[1]
        if v[0] == "arrayof":
            return ["[]", v[1]]
        return None

    return {
        "name": name[1] if name and name[0] == "g" else None,
        "modifiers": mods[1] if mods and mods[0] == "i" else None,
        "access": access[1] if access and access[0] == "i" else None,
        "returns": cls(ret),
        "params": [cls(p) for p in params[1]] if params and params[0] == "list" else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wasm", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--wat", type=Path, help="reuse an existing `wasm-tools print` output")
    args = ap.parse_args()
    model = build_model(args.wasm, args.wat)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        json.dump(model, fh, separators=(",", ":"))
    print(f"functions={len(model['functions'])} strings={len(model['strings'])} "
          f"classes={len(model['classes'])} vtables={len(model['vtables'])} "
          f"reflected={len(model['reflection'])}")


if __name__ == "__main__":
    main()
