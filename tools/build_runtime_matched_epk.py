#!/usr/bin/env python3
"""Build an assets EPK whose server data matches the 26.2 runtime.

The 26.3 assets EPK ships 26.3 `data/` (worldgen, tags, recipes, structures)
that reference blocks the 26.2 runtime does not register (poplar, cushions,
concrete stairs, ...). Loading it makes "Create New World" throw while the
world-creation screen loads its data packs. Keep the 26.3 client assets (title
screen, panorama, languages) but take every `data/` entry, plus any file 26.3
dropped, from the 26.2 EPK.

usage: build_runtime_matched_epk.py <26.3-assets.epk> <26.2-assets.epk> <out.epk>
"""
import sys
from build_full_language_epk import parse_epk, rebuild

def is_runtime_data(name):
    return name.startswith("data/")

def main():
    source=parse_epk(sys.argv[1])
    runtime=parse_epk(sys.argv[2])
    runtime_files={n:d for t,n,d in runtime["entries"] if t==b"FILE"}

    source["entries"]=[(t,n,d) for t,n,d in source["entries"]
                       if not (t==b"FILE" and is_runtime_data(n))]
    kept={n for t,n,d in source["entries"] if t==b"FILE"}
    additions={n:d for n,d in runtime_files.items()
               if is_runtime_data(n) or n not in kept}
    rebuild(source, {}, additions, sys.argv[3])
    print("kept %d source files, added %d runtime files" % (len(kept), len(additions)))

if __name__=="__main__":
    main()
