"""Build both outputs from src/page.html:
  rift-roulette.html   the published web artifact (Google Fonts, no doc skeleton)
  app/src/index.html   the desktop app page (bundled fonts, full document)
Run from the workspace root after build_data.py.
"""
import base64, os, time
from pathlib import Path


def write_out(path, text):
    """Write via a temp file and swap it in, retrying while Windows (a browser tab, antivirus) holds the file."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except OSError:
            if attempt == 19:
                raise
            time.sleep(0.5)

page = Path("src/page.html").read_text(encoding="utf-8")
data = Path("site/items.js").read_text(encoding="utf-8")
web = page.replace("/*ITEM_DATA*/", data)
web = web.replace("/*CHAMP_DATA*/", Path("site/champs.js").read_text(encoding="utf-8"))

# Easter-egg sound: assets/vine-boom.(mp3|wav|ogg|m4a) is embedded as a data URI when present.
MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}
boom = next((f for f in sorted(Path("assets").glob("vine-boom.*")) if f.suffix.lower() in MIME), None) if Path("assets").exists() else None
if boom:
    uri = f"data:{MIME[boom.suffix.lower()]};base64," + base64.b64encode(boom.read_bytes()).decode()
    web = web.replace("/*VINE_BOOM*/", uri)
    print("embedded", boom.name, f"{boom.stat().st_size // 1024} KB")

# Easter-egg flag: assets/croatia-flag.(png|jpg|webp) replaces the drawn SVG flag when present.
import re
IMG = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
flag = next((f for f in sorted(Path("assets").glob("croatia-flag.*")) if f.suffix.lower() in IMG), None) if Path("assets").exists() else None
if flag:
    uri = f"data:{IMG[flag.suffix.lower()]};base64," + base64.b64encode(flag.read_bytes()).decode()
    web, n = re.subn(r'(<div class="egg" id="egg" aria-hidden="true">)<svg.*?</svg>(</div>)', lambda m: m.group(1) + f'<img src="{uri}" alt="">' + m.group(2), web, flags=re.S)
    print("embedded", flag.name, f"{flag.stat().st_size // 1024} KB" if n else "(egg markup not found!)")
write_out("rift-roulette.html", web)

lines = [l for l in web.splitlines() if "fonts.googleapis.com" not in l and "claude:viewport-fit-sides" not in l
         and l.strip() != '<meta charset="utf-8">']   # the app document declares its own
head_end = next(i for i, l in enumerate(lines) if l.startswith("</style>"))
doc = ["<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
       '<meta name="viewport" content="width=device-width, initial-scale=1">',
       "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'; img-src 'self' data:; media-src data:; style-src 'self' 'unsafe-inline'; script-src 'unsafe-inline'; font-src 'self'\">",
       '<link rel="stylesheet" href="fonts/fonts.css">']
doc += lines[:head_end + 1] + ["</head>", "<body>"] + lines[head_end + 1:] + ["</body>", "</html>"]
write_out("app/src/index.html", "\n".join(doc) + "\n")
print("ok")
