#!/usr/bin/env python3
"""Replace the assets EPK's splashes.txt with the official one for a version.

usage: sync_official_splashes.py <in.epk> <out.epk> [version, default 26.3]
"""
import io, json, sys, urllib.request, zipfile
from build_full_language_epk import parse_epk, rebuild, file_map

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
SPLASHES = "assets/minecraft/texts/splashes.txt"

def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()

def main():
    source, out = sys.argv[1], sys.argv[2]
    version_id = sys.argv[3] if len(sys.argv) > 3 else "26.3"
    manifest = json.loads(get(MANIFEST))
    version = json.loads(get(next(v for v in manifest["versions"] if v["id"] == version_id)["url"]))
    client = zipfile.ZipFile(io.BytesIO(get(version["downloads"]["client"]["url"])))
    official = client.read(SPLASHES)
    epk = parse_epk(source)
    current = file_map(epk)[SPLASHES]
    lines = lambda b: [l for l in b.decode("utf-8").splitlines() if l.strip()]
    added = set(lines(official)) - set(lines(current))
    dropped = set(lines(current)) - set(lines(official))
    print("official %s splashes: %d (+%d, -%d vs current)" % (version_id, len(lines(official)), len(added), len(dropped)))
    rebuild(epk, {SPLASHES: official}, {}, out)

if __name__ == "__main__":
    main()
