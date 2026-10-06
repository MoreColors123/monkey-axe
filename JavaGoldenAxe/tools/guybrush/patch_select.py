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

# Clear Ax's old portrait. Frame is (571,13,32,64), anchor (16,60). Stop at
# x=604 so Gilius (whose sprite starts at x=611) is untouched. NOTE: the clear
# must be pasted with NO mask - pasting an alpha-0 image using itself as mask
# replaces nothing, which is why the old Ax art used to show through.
sel.paste((0, 0, 0, 0), (569, 9, 604, 81))

idle = key_green(src.crop((378, 5, 378 + 24, 5 + 47)))
# Fit inside the frame: at most cy (60) tall above the feet and w (32) wide,
# otherwise the portrait is clipped at the top of the sprite rectangle.
s = min(60 / idle.height, 32 / idle.width)
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
