#!/usr/bin/env python3
"""Restore the sapling survival check on the 26.3 build's poplar trees.

Vanilla 26.3 places orange/red/yellow poplars and fallen poplar trees only
where a poplar sapling would survive. The 26.3 build ships these placed
features with an empty placement list, so Dappled Forest trees generate on
top of other trees' leaves (heightmap OCEAN_FLOOR includes leaves). Add the
same block_predicate_filter the build uses for every other tree.

usage: fix_poplar_tree_placement.py <in.epk> <out.epk>
"""
import json, sys
from build_full_language_epk import parse_epk, rebuild, file_map, encode_json

PLACED = "data/minecraft/worldgen/placed_feature/"
FEATURES = ["orange_poplar", "red_poplar", "yellow_poplar", "fallen_poplar_tree"]
SURVIVES = {
    "type": "minecraft:block_predicate_filter",
    "predicate": {
        "type": "minecraft:would_survive",
        "state": {"Name": "minecraft:poplar_sapling", "Properties": {"stage": "0"}},
    },
}

def main():
    epk = parse_epk(sys.argv[1])
    files = file_map(epk)
    replacements = {}
    for name in FEATURES:
        path = PLACED + name + ".json"
        placed = json.loads(files[path])
        if any(p.get("type") == "minecraft:block_predicate_filter" for p in placed["placement"]):
            print("%s already filtered" % name)
            continue
        placed["placement"].insert(0, SURVIVES)
        replacements[path] = encode_json(placed)
        print("%s: added would_survive(poplar_sapling)" % name)
    rebuild(epk, replacements, {}, sys.argv[2])

if __name__ == "__main__":
    main()
