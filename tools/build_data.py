"""Build the randomizer's item pools from Riot's Data Dragon.

Usage: python build_data.py <SR ddragon version> <out dir> [ARAM ddragon version | latest]
Summoner's Rift uses patch 26.10 (Data Dragon 16.10.1). ARAM uses the latest patch by default.
Data Dragon version 16.x.y is game patch 26.x.
"""
import base64, json, re, sys, urllib.request
from pathlib import Path

SR_VER = sys.argv[1] if len(sys.argv) > 1 else "16.10.1"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
ARAM_VER = sys.argv[3] if len(sys.argv) > 3 else "latest"

def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()

if ARAM_VER == "latest":
    ARAM_VER = json.loads(get("https://ddragon.leagueoflegends.com/api/versions.json"))[0]

def patch_of(ver):
    major, minor = ver.split(".")[:2]
    return f"{int(major) + 10}.{minor}"

def stats_of(desc):
    m = re.search(r"<stats>(.*?)</stats>", desc)
    out = []
    if m:
        for part in m.group(1).split("<br>"):
            part = re.sub(r"<[^>]+>", "", part).strip()
            if part:
                out.append(part)
    return out

def passives_of(desc):
    body = re.sub(r"<stats>.*?</stats>", "", desc)
    names = re.findall(r"<(?:passive|active)>(.*?)</(?:passive|active)>", body)
    seen = []
    for n in names:
        n = re.sub(r"<[^>]+>", "", n).strip()
        if n and n not in seen:
            seen.append(n)
    return seen

def icons_for(ver, ids):
    cdn = f"https://ddragon.leagueoflegends.com/cdn/{ver}"
    return {i: "data:image/png;base64," + base64.b64encode(get(f"{cdn}/img/item/{i}.png")).decode() for i in sorted(ids)}

ENCHANTER = {"6617", "6620", "6621", "3107", "3222", "3504", "2065", "4005", "6616"}
WARDEN = {"3190", "3109", "3050", "2524"}

# ---------------- Summoner's Rift (classes: AD / AP / Bruiser / Tank / Support) ----------------
JUNGLE_PETS = {"1101", "1102", "1103"}
LANE_STARTERS = {"1054", "1055", "1056", "1082", "1083", "1086", "1120"}
SUPPORT_STARTER = {"3865"}

def sr_classes(k, stats):
    s = " ".join(stats)
    ap = "Ability Power" in s
    ad = any(x in s for x in ("Attack Damage", "Critical Strike", "Attack Speed"))
    defensive = bool(re.search(r"\d Health|Armor(?! Pen)|Magic Resist", s))
    c = []
    if ad: c.append("AD")
    if ap: c.append("AP")
    if ad and defensive and not ap: c.append("Bruiser")
    if defensive and not (ad or ap) and k not in ENCHANTER: c.append("Tank")
    if k == "3053": c = ["Bruiser", "Tank"]  # Sterak's lists no flat AD
    if k in ENCHANTER or k in WARDEN: c.append("Support")
    if k in WARDEN and "Tank" not in c: c.append("Tank")
    return c

def build_sr(items):
    pool = {"legendary": [], "boots": [], "starter": []}
    seen_names = set()
    for k, v in sorted(items.items(), key=lambda kv: int(kv[0])):
        if not (int(k) < 10000 and v["maps"].get("11") and v["gold"]["purchasable"] and v.get("inStore", True) is not False):
            continue
        t, desc = v["tags"], v["description"]
        rec = {"id": k, "name": v["name"], "gold": v["gold"]["total"], "stats": stats_of(desc), "passives": passives_of(desc)}
        if "Boots" in t and v.get("depth") == 2:
            up = (v.get("into") or [None])[0]
            rec["upgrade"] = {"id": up, "name": items[up]["name"], "gold": items[up]["gold"]["total"]} if up else None
            pool["boots"].append(rec)
        elif k in JUNGLE_PETS | LANE_STARTERS | SUPPORT_STARTER:
            rec["role"] = "jungle" if k in JUNGLE_PETS else "support" if k in SUPPORT_STARTER else "lane"
            pool["starter"].append(rec)
        elif (not v.get("into") and v.get("depth", 1) >= 2 and v["gold"]["total"] >= 1500
              and "Boots" not in t and "Lane" not in t and v["name"] not in seen_names):
            seen_names.add(v["name"])
            rec["classes"] = sr_classes(k, rec["stats"])
            pool["legendary"].append(rec)
    return pool

# ---------------- ARAM (classes: AD / AP / Health / Resistances / Support) ----------------
# Any item that gives the stat counts, so Gunblade is both AD and AP, Guinsoo's is AP too, and so on.
ARAM_SUPPORT = ENCHANTER | WARDEN | {"124011"}   # + Sword of Blossoming Dawn (ARAM's own support item)
# Guardian's items only. Data Dragon flags Doran's items for the ARAM map, but they can't be bought there.
ARAM_STARTERS = {"2051", "3112", "3177", "3184"}

def aram_classes(k, stats):
    c = []
    if any(re.fullmatch(r"\d+ Attack Damage", s) for s in stats): c.append("AD")
    if any(re.fullmatch(r"\d+ Ability Power", s) for s in stats): c.append("AP")
    if any(re.fullmatch(r"\d+ Health", s) for s in stats): c.append("Health")
    if any(re.fullmatch(r"\d+ (Armor|Magic Resist)", s) for s in stats): c.append("Resistances")
    if k in ARAM_SUPPORT: c.append("Support")
    return c

def build_aram(items):
    def on_aram(k, v):
        # 77xxxx items are a retro event set that is also flagged for the ARAM map; leave them out.
        return (int(k) < 700000 and v["maps"].get("12") and v["gold"]["purchasable"]
                and v.get("inStore", True) is not False)
    pool = {"legendary": [], "boots": [], "starter": []}
    seen_names = set()
    for k, v in sorted(items.items(), key=lambda kv: int(kv[0])):
        if not on_aram(k, v):
            continue
        t, desc = v["tags"], v["description"]
        rec = {"id": k, "name": v["name"], "gold": v["gold"]["total"], "stats": stats_of(desc), "passives": passives_of(desc)}
        if "Boots" in t and v.get("depth") == 2:
            up = (v.get("into") or [None])[0]
            ok = up and up in items and on_aram(up, items[up])
            rec["upgrade"] = {"id": up, "name": items[up]["name"], "gold": items[up]["gold"]["total"]} if ok else None
            pool["boots"].append(rec)
        elif k in ARAM_STARTERS:
            rec["role"] = "lane"
            pool["starter"].append(rec)
        elif (not v.get("into") and v.get("depth", 1) >= 2 and v["gold"]["total"] >= 1500
              and "Boots" not in t and "Consumable" not in t and rec["stats"] and v["name"] not in seen_names):
            seen_names.add(v["name"])
            rec["classes"] = aram_classes(k, rec["stats"])
            pool["legendary"].append(rec)
    return pool

def ids_of(pool):
    ids = {r["id"] for g in pool.values() for r in g}
    return ids | {r["upgrade"]["id"] for r in pool["boots"] if r.get("upgrade")}

sr_items = json.loads(get(f"https://ddragon.leagueoflegends.com/cdn/{SR_VER}/data/en_US/item.json"))["data"]
aram_items = json.loads(get(f"https://ddragon.leagueoflegends.com/cdn/{ARAM_VER}/data/en_US/item.json"))["data"]
sr, aram = build_sr(sr_items), build_aram(aram_items)

OUT.mkdir(parents=True, exist_ok=True)
sr_payload = {"patch": patch_of(SR_VER), "ddragon": SR_VER, **sr, "icons": icons_for(SR_VER, ids_of(sr))}
aram_payload = {"patch": patch_of(ARAM_VER), "ddragon": ARAM_VER, **aram, "icons": icons_for(ARAM_VER, ids_of(aram))}
(OUT / "items.js").write_text(
    "window.ITEM_DATA = " + json.dumps(sr_payload, separators=(",", ":")) + ";\n"
    "window.ARAM_DATA = " + json.dumps(aram_payload, separators=(",", ":")) + ";\n", encoding="utf-8")
print("SR", patch_of(SR_VER), {k: len(v) for k, v in sr.items()})
print("ARAM", patch_of(ARAM_VER), {k: len(v) for k, v in aram.items()})
