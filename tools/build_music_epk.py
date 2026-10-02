#!/usr/bin/env python3
"""Build music.epk for the 26.3 page and trim sounds.json to match.

The 26.3 client reports "Optional music pack is not installed" when no loaded
EPK has files under sounds/music/ or sounds/records/. The full official set is
~280 MB, too much to hold in memory on iPad, so this ships a curated set of
tracks re-encoded as mono 22 kHz Vorbis, and rewrites the music events in the assets
EPK's sounds.json to reference only shipped tracks (events left empty fall
back to music.game).

usage: build_music_epk.py <assets.epk in> <assets.epk out> <music.epk out>
Needs ffmpeg with libvorbis and network access to Mojang's asset servers.
"""
import json, subprocess, sys, tempfile, urllib.request
from pathlib import Path
from build_full_language_epk import parse_epk, rebuild, file_map, encode_json

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
VERSION = "26.3"

TRACKS = [
    # Title screen (C418)
    "music/menu/beginning_2", "music/menu/floating_trees", "music/menu/moog_city_2", "music/menu/mutation",
    # Overworld classics (C418)
    "music/game/clark", "music/game/danny", "music/game/dry_hands", "music/game/haggstrom",
    "music/game/key", "music/game/living_mice", "music/game/mice_on_venus", "music/game/minecraft",
    "music/game/oxygene", "music/game/subwoofer_lullaby", "music/game/sweden", "music/game/wet_hands",
    # Creative (C418), the two shortest
    "music/game/creative/aria_math", "music/game/creative/blind_spots",
    # Nether (C418)
    "music/game/nether/concrete_halls", "music/game/nether/dead_voxel", "music/game/nether/warmth",
    "music/game/nether/ballad_of_the_cats",
    # Underwater, End, boss (credits falls back to music.game)
    "music/game/water/shuniji", "music/game/end/the_end", "music/game/end/boss",
]
# Mono 22 kHz Vorbis q0 (~16 kbps) keeps the pack near 20 MB for iPad memory.
ENCODE = ["-ac", "1", "-ar", "22050", "-c:a", "libvorbis", "-q:a", "0"]
# Every music disc.
DISC_PREFIX = "records/"

def get_json(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)

def get_bytes(url):
    with urllib.request.urlopen(url) as r:
        return r.read()

def sound_name(entry):
    return entry if isinstance(entry, str) else entry["name"]

def main():
    assets_in, assets_out, music_out = sys.argv[1], sys.argv[2], sys.argv[3]
    manifest = get_json(MANIFEST)
    version = get_json(next(v for v in manifest["versions"] if v["id"] == VERSION)["url"])
    index = get_json(version["assetIndex"]["url"])["objects"]

    def asset(name):
        return index.get("minecraft/sounds/" + name + ".ogg")

    discs = sorted(k[len("minecraft/sounds/"):-4] for k in index
                   if k.startswith("minecraft/sounds/" + DISC_PREFIX) and k.endswith(".ogg"))
    wanted = []
    for name in TRACKS + discs:
        if asset(name) is None:
            raise RuntimeError("track not in the %s asset index: %s" % (VERSION, name))
        wanted.append(name)

    shipped = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name in wanted:
            obj = asset(name)
            h = obj["hash"]
            src = Path(tmp) / "in.ogg"
            dst = Path(tmp) / "out.ogg"
            src.write_bytes(get_bytes("https://resources.download.minecraft.net/%s/%s" % (h[:2], h)))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn"] + ENCODE + [str(dst)],
                           check=True)
            shipped[name] = dst.read_bytes()
            print("%-45s %6.2f MB -> %5.2f MB" % (name, obj["size"] / 1048576, len(shipped[name]) / 1048576))

    # Trim sounds.json music events to shipped tracks.
    assets = parse_epk(assets_in)
    files = file_map(assets)
    sounds = json.loads(files["assets/minecraft/sounds.json"])
    for event, spec in sounds.items():
        if not (event.startswith("music.") or event.startswith("music_disc.")):
            continue
        kept = [s for s in spec.get("sounds", [])
                if (isinstance(s, dict) and s.get("type") == "event") or sound_name(s) in shipped]
        if not kept and event.startswith("music.") and event != "music.game":
            kept = [{"name": "music.game", "type": "event"}]
        spec["sounds"] = kept
    rebuild(assets, {"assets/minecraft/sounds.json": encode_json(sounds)}, {}, assets_out)

    # music.epk reuses the assets EPK's envelope with only the music entries.
    music = dict(assets)
    music["filename"] = b"music.epk"
    music["entries"] = ([e for e in assets["entries"] if e[0] == b"HEAD"]
                        + [[b"FILE", "assets/minecraft/sounds/" + n + ".ogg", d] for n, d in sorted(shipped.items())])
    rebuild(music, {}, {}, music_out)
    print("music.epk: %d tracks, %.1f MB" % (len(shipped), Path(music_out).stat().st_size / 1048576))

if __name__ == "__main__":
    main()
