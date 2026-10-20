"""Build the champion list for the case opening, with small embedded portraits.

Usage: python tools/build_champs.py [ddragon version]   (default 16.10.1 = patch 26.10)
Writes site/champs.js. Needs Pillow (python -m pip install --user pillow).
"""
import base64, io, json, re, sys, urllib.request
from pathlib import Path
from PIL import Image

VER = sys.argv[1] if len(sys.argv) > 1 else "16.10.1"
CDN = f"https://ddragon.leagueoflegends.com/cdn/{VER}"
SIZE = 96

def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()

champs = json.loads(get(f"{CDN}/data/en_US/champion.json"))["data"]

# Lore regions come from Riot's Universe site; champions it lists as unaffiliated show as "Runeterra".
uni = json.loads(get("https://universe-meeps.leagueoflegends.com/v1/en_us/search/index.json"))
faction_names = {f["slug"]: f["name"] for f in uni["factions"]}
faction_names["freljord"] = "Freljord"          # Universe says "The Freljord"; the region is just Freljord
norm = lambda t: re.sub(r"[^a-z]", "", t.lower())
region_of = {}
for u in uni["champions"]:
    region = faction_names.get(u["associated-faction-slug"], "Runeterra")
    region_of[norm(u["name"])] = region_of[norm(u["slug"])] = region
out, icons, total = [], {}, 0
for c in sorted(champs.values(), key=lambda c: c["name"]):
    img = Image.open(io.BytesIO(get(f"{CDN}/img/champion/{c['image']['full']}"))).convert("RGB")
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO(); img.save(buf, "WEBP", quality=82)
    total += buf.tell()
    icons[c["id"]] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    out.append({"id": c["id"], "name": c["name"], "title": c["title"], "tags": c["tags"], "difficulty": c["info"]["difficulty"],
                "attack": c["info"]["attack"], "magic": c["info"]["magic"], "defense": c["info"]["defense"],
                "partype": c["partype"], "range": c["stats"]["attackrange"],
                "region": region_of.get(norm(c["name"])) or region_of.get(norm(c["id"]), "Runeterra")})

major, minor = VER.split(".")[:2]
payload = {"patch": f"{int(major) + 10}.{minor}", "ddragon": VER, "champs": out, "icons": icons}
Path("site").mkdir(exist_ok=True)
Path("site/champs.js").write_text("window.CHAMP_DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n", encoding="utf-8")
print(len(out), "champions,", total // 1024, "KB of portraits")
