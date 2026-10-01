#!/usr/bin/env python3
"""Restore the 26.3 build's own translation keys in the all-languages EPK.

build_full_language_epk.py replaced en_us/zh_cn with Mojang's official files,
which lack keys this build adds (cushion blocks, joey_cushion_seat, Eagler
options and screens), and left assets/eagler/lang/zh_cn.json in English.
Keep the official translations, add back every key only the build defines,
and take the build's Chinese Eagler strings.

usage: restore_build_lang_keys.py <all-languages.epk> <build assets.epk> <out.epk>
"""
import json, sys
from build_full_language_epk import parse_epk, rebuild, file_map, encode_json

MERGE = ["assets/minecraft/lang/en_us.json", "assets/minecraft/lang/zh_cn.json",
         "assets/eagler/lang/en_us.json"]
PREFER_BUILD = ["assets/eagler/lang/zh_cn.json"]

def main():
    source = parse_epk(sys.argv[1])
    build = file_map(parse_epk(sys.argv[2]))
    current = file_map(source)
    replacements = {}
    for name in MERGE + PREFER_BUILD:
        have = json.loads(current[name])
        want = json.loads(build[name])
        merged = dict(have)
        if name in PREFER_BUILD:
            merged.update(want)
        else:
            for key, value in want.items():
                merged.setdefault(key, value)
        added = len(merged) - len(have)
        changed = sum(1 for k in have if merged[k] != have[k])
        print("%-36s +%d keys, %d replaced" % (name, added, changed))
        replacements[name] = encode_json(merged)
    rebuild(source, replacements, {}, sys.argv[3])

if __name__ == "__main__":
    main()
