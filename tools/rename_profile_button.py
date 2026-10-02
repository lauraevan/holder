#!/usr/bin/env python3
"""Label the title screen's Edit Profile button "Minecraft Realms", and add
the assets for the small profile button patch_26_3_branding.js --profile-button
puts next to the language button.

The big button reads translation key eagler.menu.profile, which only zh_cn
defined (other languages used the "Edit Profile" fallback in the client). Set
it in every language to that language's own vanilla Realms label, menu.online.
The small button is labelled eagler.menu.editProfile (missing languages fall
back to en_us) and draws the icon/profile GUI sprite.

usage: rename_profile_button.py <in.epk> <out.epk>
"""
import json, sys
from pathlib import Path
from build_full_language_epk import parse_epk, rebuild, file_map, encode_json

KEY = "eagler.menu.profile"
SOURCE = "menu.online"
EDIT_KEY = "eagler.menu.editProfile"
EDIT_LABELS = {"en_us": "Edit Profile", "zh_cn": "\u7f16\u8f91\u73a9\u5bb6\u6863\u6848"}
SPRITE = "assets/minecraft/textures/gui/sprites/icon/profile.png"

def main():
    epk = parse_epk(sys.argv[1])
    replacements = {}
    for name, data in file_map(epk).items():
        if not (name.startswith("assets/minecraft/lang/") and name.endswith(".json")) or name.endswith("deprecated.json"):
            continue
        lang = json.loads(data)
        lang[KEY] = lang.get(SOURCE, "Minecraft Realms")
        code = name[len("assets/minecraft/lang/"):-len(".json")]
        if code in EDIT_LABELS:
            lang[EDIT_KEY] = EDIT_LABELS[code]
        replacements[name] = encode_json(lang)
    count = len(replacements)
    sprite = (Path(__file__).parent / "assets" / "icon_profile.png").read_bytes()
    replacements[SPRITE] = sprite
    rebuild(epk, replacements, {SPRITE: sprite}, sys.argv[2])
    print("set %s in %d languages" % (KEY, count))

if __name__ == "__main__":
    main()
