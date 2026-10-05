#!/usr/bin/env python3
"""Replace Ax Battler's portrait with Guybrush on the select-player screen."""
from PIL import Image
import numpy as np, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = str(HERE.parent.parent / "assets" / "res")
SRC_PATH = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "guybrush_source.png")
sel = Image.open(ROOT + r"\image\select_player.png").convert("RGBA")
src = Image.open(SRC_PATH).convert("RGB")

BG = np.array([0, 136, 68])
def key_green(im):
    a = np.array(im).astype(np.int16)
    dist = np.abs(a - BG).sum(axis=2)
    alpha = np.where(dist > 45, 255, 0).astype(np.uint8)
    return Image.fromarray(np.dstack([np.array(im), alpha]), "RGBA")

# clear Ax region (571,13,32,64) with margin
clear = Image.new("RGBA", (52, 84), (0, 0, 0, 0))
sel.paste(clear, (563, 3), clear)

idle = key_green(src.crop((378, 5, 378 + 24, 5 + 47)))
s = 64 / idle.height
nw, nh = round(idle.width * s), round(idle.height * s)
idle = idle.resize((nw, nh), Image.NEAREST)
# anchor (cx=16, cy=60) -> feet at (571+16, 13+60)
px, py = 571 + 16 - nw // 2, 13 + 60 - nh
sel.paste(idle, (px, py), idle)
sel.save(ROOT + r"\image\select_player.png")
print("patched select_player.png; pasted at", px, py, idle.size)

# rename sprite ax -> guybrush in select_player.char
cp = ROOT + r"\chars\select_player.char"
with open(cp, encoding="latin-1") as f:
    txt = f.read()
txt = re.sub(r"^sprite ax ", "sprite guybrush ", txt, flags=re.M)
with open(cp, "w", encoding="latin-1") as f:
    f.write(txt)
print("renamed sprite ax -> guybrush in select_player.char")
