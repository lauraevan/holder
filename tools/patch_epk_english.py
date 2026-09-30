#!/usr/bin/env python3
import gzip, io, json, struct, sys, zlib
from pathlib import Path

END=b":::YEE:>"

def u8(f):
    b=f.read(1)
    if len(b)!=1: raise EOFError
    return b[0]
def u16(f): return struct.unpack(">H",f.read(2))[0]
def u32(f): return struct.unpack(">I",f.read(4))[0]
def p8(n): return bytes([n])
def p16(n): return struct.pack(">H",n)
def p32(n): return struct.pack(">I",n)
def astr(f): return f.read(u8(f)).decode("latin1")
def pastr(s):
    b=s.encode("latin1")
    if len(b)>255: raise ValueError("name too long")
    return p8(len(b))+b

def parse_epk(path):
    raw=Path(path).read_bytes()
    if not raw.startswith(b"EAGPKG$$") or not raw.endswith(END): raise ValueError("bad EPK envelope")
    f=io.BytesIO(raw[:-8]); f.read(8)
    version=astr(f)
    filename=f.read(u8(f))
    comment=f.read(u16(f))
    millis=f.read(8)
    count=u32(f)
    comp=f.read(1)
    payload=f.read()
    if comp==b"G": body=gzip.decompress(payload)
    elif comp==b"Z": body=zlib.decompress(payload)
    elif comp==b"0": body=payload
    else: raise ValueError("unsupported compression")
    z=io.BytesIO(body); entries=[]
    for _ in range(count):
        typ=z.read(4); name=astr(z); ln=u32(z)
        if typ==b"FILE":
            crc=u32(z); data=z.read(ln-5)
            if z.read(1)!=b":" or z.read(1)!=b">": raise ValueError("bad FILE terminator "+name)
            if (zlib.crc32(data)&0xffffffff)!=crc: raise ValueError("CRC mismatch "+name)
            entries.append([typ,name,data])
        else:
            data=z.read(ln)
            if z.read(1)!=b">": raise ValueError("bad object terminator "+name)
            entries.append([typ,name,data])
    if z.read(4)!=b"END$": raise ValueError("missing END$")
    return dict(version=version,filename=filename,comment=comment,millis=millis,
                compression=comp,entries=entries)

def files(epk):
    return {n:d for typ,n,d in epk["entries"] if typ==b"FILE"}

def encode_json(obj):
    return (json.dumps(obj,ensure_ascii=False,indent=2,separators=(",", ": "))+"\n").encode("utf-8")

COLORS={
"black":"Black","blue":"Blue","brown":"Brown","cyan":"Cyan","gray":"Gray","green":"Green",
"light_blue":"Light Blue","light_gray":"Light Gray","lime":"Lime","magenta":"Magenta",
"orange":"Orange","pink":"Pink","purple":"Purple","red":"Red","white":"White","yellow":"Yellow"
}

MANUAL={
"biome.minecraft.dappled_forest":"Dappled Forest",
"block.minecraft.orange_poplar_leaves":"Orange Poplar Leaves",
"block.minecraft.red_poplar_leaves":"Red Poplar Leaves",
"block.minecraft.yellow_poplar_leaves":"Yellow Poplar Leaves",
"block.minecraft.red_shrub":"Red Shrub",
"block.minecraft.shelf_mushroom":"Shelf Mushroom",
"block.minecraft.straw_bed":"Straw Bed",
"block.minecraft.poplar_button":"Poplar Button",
"block.minecraft.poplar_door":"Poplar Door",
"block.minecraft.poplar_fence":"Poplar Fence",
"block.minecraft.poplar_fence_gate":"Poplar Fence Gate",
"block.minecraft.poplar_hanging_sign":"Poplar Hanging Sign",
"block.minecraft.poplar_leaves":"Poplar Leaves",
"block.minecraft.poplar_log":"Poplar Log",
"block.minecraft.poplar_planks":"Poplar Planks",
"block.minecraft.poplar_pressure_plate":"Poplar Pressure Plate",
"block.minecraft.poplar_sapling":"Poplar Sapling",
"block.minecraft.poplar_shelf":"Poplar Shelf",
"block.minecraft.poplar_sign":"Poplar Sign",
"block.minecraft.poplar_slab":"Poplar Slab",
"block.minecraft.poplar_stairs":"Poplar Stairs",
"block.minecraft.poplar_trapdoor":"Poplar Trapdoor",
"block.minecraft.poplar_wall_hanging_sign":"Poplar Wall Hanging Sign",
"block.minecraft.poplar_wall_sign":"Poplar Wall Sign",
"block.minecraft.poplar_wood":"Poplar Wood",
"block.minecraft.potted_poplar_sapling":"Potted Poplar Sapling",
"block.minecraft.stripped_poplar_log":"Stripped Poplar Log",
"block.minecraft.stripped_poplar_wood":"Stripped Poplar Wood",
"entity.minecraft.joey_cushion_seat":"Cushion Seat",
"entity.minecraft.poplar_boat":"Poplar Boat",
"entity.minecraft.poplar_chest_boat":"Poplar Chest Boat",
"filled_map.bamboo_camp_map":"Bamboo Camp Map",
"filled_map.birch_forest_camp_map":"Birch Forest Camp Map",
"filled_map.cherry_grove_camp_map":"Cherry Grove Camp Map",
"filled_map.dappled_forest_camp_map":"Dappled Forest Camp Map",
"filled_map.flower_forest_camp_map":"Flower Forest Camp Map",
"filled_map.pale_garden_camp_map":"Pale Garden Camp Map",
"filled_map.swamp_camp_map":"Swamp Camp Map",
"filled_map.windswept_forest_camp_map":"Windswept Forest Camp Map",
"item.minecraft.buried_ancient_city_map":"Buried Ancient City Map",
"item.minecraft.buried_mineshaft_map":"Buried Mineshaft Map",
"item.minecraft.buried_trial_chambers_map":"Buried Trial Chambers Map",
"item.minecraft.desert_pyramid_map":"Desert Pyramid Map",
"item.minecraft.jungle_pyramid_map":"Jungle Pyramid Map",
"item.minecraft.poplar_boat":"Poplar Boat",
"item.minecraft.poplar_chest_boat":"Poplar Chest Boat",
"item.minecraft.warm_ocean_ruins_map":"Warm Ocean Ruins Map",
"item.minecraft.woodland_mansion_map":"Woodland Mansion Map",

"commands.item.block.modify.success":"Modified %1$s slots at %2$s, %3$s, %4$s",
"commands.item.block.replace.success":"Replaced %1$s slots at %2$s, %3$s, %4$s",
"commands.item.block.replace.success.known_item":"Replaced %1$s slots at %2$s, %3$s, %4$s with %5$s",
"commands.item.entity.modify.success.multiple":"Modified slots for %s entities",
"commands.item.entity.modify.success.single":"Modified %1$s slots for %2$s",
"commands.item.entity.replace.success.multiple":"Replaced slots for %s entities",
"commands.item.entity.replace.success.multiple.known_item":"Replaced slots for %1$s entities with %2$s",
"commands.item.entity.replace.success.single":"Replaced %1$s slots for %2$s",
"commands.item.entity.replace.success.single.known_item":"Replaced %1$s slots for %2$s with %3$s",
"commands.item.source.no_such_slot.unnamed":"Source does not have the specified slot",
"commands.item.target.failed":"No target accepted an item in the specified slot",
"commands.item.target.failed.known_item":"No target accepted item %s in the specified slot",
"commands.item.target.no_such_slot.unnamed":"Target does not have the specified slot",

"defaultUsernameDetected.changeUsername":"Change Username",
"defaultUsernameDetected.continueAnyway":"Continue Anyway",
"defaultUsernameDetected.doNotShow":"Do not show again",
"defaultUsernameDetected.text1":"This username may already be used by a player on large servers",
"defaultUsernameDetected.text2":"Would you like to use a different username?",
"defaultUsernameDetected.title":"Default Username Detected",

"editCape.addCape":"Add Cape",
"editCape.clearCape":"Reset to Default",
"editCape.playerCape":"Player Cape",
"editCape.title":"Edit Cape",
"editProfile.addSkin":"Add Skin",
"editProfile.capes":"Capes",
"editProfile.clearSkin":"Reset to Default",
"editProfile.importExport":"Import/Export",
"editProfile.playerSkin":"Player Skin",
"editProfile.steveOrAlex":"Which model is your skin made for?",
"editProfile.title":"Edit Player Profile",
"editProfile.username":"Username",

"settingsBackup.importExport.export":"Export Profile and Settings...",
"settingsBackup.importExport.import":"Import Profile and Settings...",
"settingsBackup.importExport.title":"What would you like to do?",

"singleplayer.backup.button":"Backup",
"singleplayer.backup.clearPlayerData":"Clear Player Data",
"singleplayer.backup.clearPlayerData.warning1":"Are you sure you want to delete all player data?",
"singleplayer.backup.duplicate":"Duplicate World",
"singleplayer.backup.export":"Export EPK File",
"singleplayer.backup.recreate":"Re-Create World",
"singleplayer.backup.seed":"Seed:",
"singleplayer.backup.title":"World Backup Menu: '%s'",
"singleplayer.backup.vanilla":"Convert to Vanilla World",
"singleplayer.busy.deleting":"Deleting World",
"singleplayer.busy.duplicating":"Duplicating World",
"singleplayer.busy.exporting.1":"Exporting world as EPK",
"singleplayer.busy.importing.1":"Importing world from EPK",
"singleplayer.busy.importing.2":"Importing vanilla world",
"singleplayer.busy.killTask":"Cancel Task",
"singleplayer.busy.startingIntegratedServer":"Starting Integrated Server",
"singleplayer.busy.title":"Starting Integrated Server",
"singleplayer.crashed.desc":"The crash report was shown in a separate window and saved to the logs directory",
"singleplayer.crashed.title":"Integrated Server Crashed!",
"singleplayer.create.create":"Create New World",
"singleplayer.create.import.epk":"Import EPK World",
"singleplayer.create.import.vanilla":"Import Vanilla World",
"singleplayer.create.title":"What would you like to do?",
"singleplayer.import.continue":"Continue",
"singleplayer.import.enterName":"Enter world name:",
"singleplayer.import.failed":"Failed to import world!",
"singleplayer.import.invalidFile":"Invalid world file",
"singleplayer.import.title":"Import World",
"singleplayer.integratedStartup":"Starting Integrated Server",
"subtitles.block.shelf_mushroom.bounce":"Something bounces on a Shelf Mushroom",
"test.player.coordinates":"Player coordinates: [%s, %s, %s] in %s",
"test.run.coordinates":"Test coordinates: [%s, %s, %s] in %s"
}

def translate_extra(k):
    if k in MANUAL: return MANUAL[k]
    if k.startswith("block.minecraft."):
        x=k[len("block.minecraft."):]
        for color,label in COLORS.items():
            p=color+"_"
            if x.startswith(p):
                tail=x[len(p):]
                names={
                  "concrete_slab":"Concrete Slab","concrete_stairs":"Concrete Stairs",
                  "cushion":"Cushion","wool_slab":"Wool Slab","wool_stairs":"Wool Stairs"
                }
                if tail in names: return label+" "+names[tail]
    if k.startswith("item.minecraft."):
        x=k[len("item.minecraft."):]
        for color,label in COLORS.items():
            if x==color+"_cushion": return label+" Cushion"
    return None

def rebuild(epk, replacements, out):
    body=bytearray()
    for typ,name,data in epk["entries"]:
        if typ==b"FILE" and name in replacements: data=replacements[name]
        body += typ + pastr(name)
        if typ==b"FILE":
            body += p32(len(data)+5)
            body += p32(zlib.crc32(data)&0xffffffff) + data + b":" + b">"
        else:
            body += p32(len(data)) + data + b">"
    body += b"END$"
    comp=epk["compression"]
    if comp==b"G": packed=gzip.compress(bytes(body),compresslevel=9,mtime=0)
    elif comp==b"Z": packed=zlib.compress(bytes(body),9)
    else: packed=bytes(body)
    raw=(b"EAGPKG$$"+pastr(epk["version"])+p8(len(epk["filename"]))+epk["filename"]+
         p16(len(epk["comment"]))+epk["comment"]+epk["millis"]+p32(len(epk["entries"]))+
         comp+packed+END)
    Path(out).write_bytes(raw)

def main():
    epk22=parse_epk(sys.argv[1]); epk23=parse_epk(sys.argv[2])
    f22=files(epk22); f23=files(epk23)
    mc="assets/minecraft/lang/en_us.json"; ea="assets/eagler/lang/en_us.json"
    en22=json.loads(f22[mc].decode("utf-8-sig"))
    cur23=json.loads(f23[mc].decode("utf-8-sig"))
    merged=dict(cur23)
    for k,v in en22.items():
        if k in merged: merged[k]=v
    extras=sorted(set(cur23)-set(en22))
    untranslated=[]
    for k in extras:
        v=translate_extra(k)
        if v is None:
            untranslated.append((k,cur23[k]))
        else:
            merged[k]=v
    if untranslated:
        Path(sys.argv[4]).write_text("\n".join(f"{k} = {v}" for k,v in untranslated),encoding="utf-8")
        raise SystemExit(f"{len(untranslated)} extra keys still need translations; see {sys.argv[4]}")
    chinese=[(k,v) for k,v in merged.items() if any("\u3400"<=c<="\u9fff" for c in str(v))]
    if chinese:
        Path(sys.argv[4]).write_text("\n".join(f"{k} = {v}" for k,v in chinese),encoding="utf-8")
        raise SystemExit(f"{len(chinese)} Chinese-valued keys remain")
    eagler_en=json.loads(f22[ea].decode("utf-8-sig"))
    eagler_en["eagler.menu.brand"]="Minecraft 26.3"
    eagler_en["eagler.menu.rewrittenBy"]=""
    replacements={mc:encode_json(merged),ea:encode_json(eagler_en)}
    rebuild(epk23,replacements,sys.argv[3])
    # round-trip validation
    chk=parse_epk(sys.argv[3]); cf=files(chk)
    cm=json.loads(cf[mc].decode("utf-8"))
    ce=json.loads(cf[ea].decode("utf-8"))
    assert cm["menu.singleplayer"]=="Singleplayer"
    assert cm["menu.multiplayer"]=="Multiplayer"
    assert not any("\u3400"<=c<="\u9fff" for v in cm.values() for c in str(v))
    assert not any("\u3400"<=c<="\u9fff" for v in ce.values() for c in str(v))
    assert ce["eagler.menu.brand"]=="Minecraft 26.3"
    assert ce["eagler.menu.rewrittenBy"]==""
    Path(sys.argv[4]).write_text(
      f"minecraft keys: {len(cm)}\neagler keys: {len(ce)}\nextra 26.3 keys translated: {len(extras)}\n"
      f"menu.singleplayer: {cm['menu.singleplayer']}\nmenu.multiplayer: {cm['menu.multiplayer']}\n"
      f"menu.options: {cm.get('menu.options')}\n"
      f"eagler.menu.brand: {ce['eagler.menu.brand']}\n"
      f"eagler.menu.rewrittenBy: {ce['eagler.menu.rewrittenBy']!r}\n"
      f"Chinese codepoints remaining: 0\n",
      encoding="utf-8")

if __name__=="__main__": main()
