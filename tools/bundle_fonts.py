"""Download the latin Google Fonts faces into app/src/fonts and write a local fonts.css."""
import re, sys, urllib.request
from pathlib import Path

out = Path(sys.argv[1])
css = (out / "fonts.css").read_text(encoding="utf-8")
blocks = re.findall(r"/\* latin \*/\s*(@font-face \{.*?\})", css, re.S)
local = []
for b in blocks:
    url = re.search(r"url\((https://[^)]+)\)", b).group(1)
    name = url.split("/s/")[1].replace("/", "-")
    if not (out / name).exists():
        urllib.request.urlretrieve(url, out / name)
    local.append(b.replace(url, name))
(out / "fonts.css").write_text("\n".join(local) + "\n", encoding="utf-8")
print(len(local), "faces")
