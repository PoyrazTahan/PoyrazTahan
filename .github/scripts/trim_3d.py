"""Strip the star/fork counters from the 3D contribution SVGs.

They count only public repos, so they read small beside the calendar total.
The action has no switch to hide them, so this runs after it, on every file.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
G, TEXT = f"{{{SVG}}}g", f"{{{SVG}}}text"


def trim(path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    for g in root.findall(G):
        # The footer group starts with the "<total> contributions" pair of texts;
        # everything after those two is the star/fork icons and counts.
        texts = g.findall(TEXT)
        if len(texts) >= 2 and (texts[1].text or "").strip() == "contributions":
            for child in list(g)[2:]:
                g.remove(child)
    tree.write(path, encoding="unicode")


for p in sorted(Path(sys.argv[1]).glob("*.svg")):
    trim(p)
    print("trimmed", p.name)
