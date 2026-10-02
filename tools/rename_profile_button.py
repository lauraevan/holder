#!/usr/bin/env python3
"""Label the title screen's Edit Profile button "Minecraft Realms".

The button reads translation key eagler.menu.profile, which only zh_cn
defines (other languages use the "Edit Profile" fallback in the client). Set
it in every language to that language's own vanilla Realms label, menu.online.

usage: rename_profile_button.py <in.epk> <out.epk>
"""
import json, sys
from build_full_language_epk import parse_epk, rebuild, file_map, encode_json

KEY = "eagler.menu.profile"
SOURCE = "menu.online"

def main():
    epk = parse_epk(sys.argv[1])
    replacements = {}
    for name, data in file_map(epk).items():
        if not (name.startswith("assets/minecraft/lang/") and name.endswith(".json")) or name.endswith("deprecated.json"):
            continue
        lang = json.loads(data)
        lang[KEY] = lang.get(SOURCE, "Minecraft Realms")
        replacements[name] = encode_json(lang)
    rebuild(epk, replacements, {}, sys.argv[2])
    print("set %s in %d languages" % (KEY, len(replacements)))

if __name__ == "__main__":
    main()
