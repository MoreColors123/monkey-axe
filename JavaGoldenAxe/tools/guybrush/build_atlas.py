#!/usr/bin/env python3
"""Bake the mapped Guybrush sprites into Ax Battler's frame layout.

Reads:
  sprites.json  - every sprite detected on the source sheet
  mapping.json  - which sprite ids are used for each Golden Axe animation
  guybrush_source.png - the source sheet

Writes the drop-in character spritesheet + .char + HUD magic files.

Edit mapping.json (or use reviewer.html) to pick different sprites, then rerun.
"""
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "assets" / "res"
SHEET_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "guybrush_source.png"

ATLAS_W, ATLAS_H = 600, 1000
BG = np.array([0, 136, 68])
CHAR_ID = "guybrush_threepwood"


def load_json(p):
    return json.loads(p.read_text())


def key_green(im):
    a = np.array(im).astype(np.int16)
    alpha = np.where(np.abs(a - BG).sum(axis=2) > 45, 255, 0).astype(np.uint8)
    return Image.fromarray(np.dstack([np.array(im), alpha]), "RGBA")


sprite_re = re.compile(
    r"^sprite\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")


def parse_frames(char_path):
    frames = []
    with open(char_path, encoding="latin-1") as f:
        for line in f:
            m = sprite_re.match(line.strip())
            if m:
                frames.append((m.group(1), int(m.group(3)), int(m.group(4)),
                               int(m.group(5)), int(m.group(6)),
                               int(m.group(7)), int(m.group(8))))
    return frames


def fit_scale(spr_w, spr_h, w, h, cx, cy, mode, base):
    s = base
    if mode == "center":
        s = min(base, h / spr_h, w / spr_w)
    elif cy > 0:
        s = min(base, cy / spr_h)
        s = min(s, w / spr_w)
    return max(s, 0.1)


def place(dst, src, x, y):
    dst.paste(src, (x, y), src)


def main():
    sprites = {s["id"]: s for s in load_json(HERE / "sprites.json")}
    mapping = load_json(HERE / "mapping.json")
    global_scale = mapping.get("global_scale", 1.15)
    face_id = mapping.get("face")
    animations = mapping["animations"]

    src_sheet = Image.open(SHEET_PATH).convert("RGB")
    src_cache = {}

    def tile(sprite):
        key = sprite["id"]
        if key not in src_cache:
            x, y, w, h = sprite["x"], sprite["y"], sprite["w"], sprite["h"]
            src_cache[key] = key_green(src_sheet.crop((x, y, x + w, y + h)))
        return src_cache[key]

    ax_char = ROOT / "chars" / "ax_battler.char"
    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    counters = {}

    for (anim, x, y, w, h, cx, cy) in parse_frames(ax_char):
        if anim == "none":
            continue
        if anim == "logo":
            spr = tile(sprites[face_id]).resize((w, h), Image.NEAREST)
            place(atlas, spr, x, y)
            continue

        entry = animations.get(anim) or animations["idle"]
        ids = entry.get("frames") or animations["idle"]["frames"]
        mode = entry.get("mode", "bottom")
        base = entry.get("scale", global_scale)
        idx = counters.get(anim, 0)
        counters[anim] = idx + 1

        sprite = sprites[ids[idx % len(ids)]]
        spr = tile(sprite)
        s = fit_scale(spr.width, spr.height, w, h, cx, cy, mode, base)
        nw, nh = max(1, round(spr.width * s)), max(1, round(spr.height * s))
        scaled = spr.resize((nw, nh), Image.NEAREST)

        if mode == "center":
            px, py = x + cx - nw // 2, y + (h - nh) // 2
        else:
            px, py = x + cx - nw // 2, y + cy - nh

        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        layer.paste(scaled, (px - x, py - y), scaled)
        place(atlas, layer, x, y)

    out_png = ROOT / "image" / f"{CHAR_ID}.png"
    atlas.save(out_png)
    print("wrote", out_png, atlas.size)

    out_char = ROOT / "chars" / f"{CHAR_ID}.char"
    content = (ROOT / "chars" / "ax_battler.char").read_text(encoding="latin-1")
    content = content.replace("# --- ax battler ---",
                              "# --- guybrush threepwood (reskin of ax battler) ---", 1)
    out_char.write_text(content, encoding="latin-1")
    print("wrote", out_char)

    for ext, sub in (("char", "chars"), ("png", "image")):
        shutil.copyfile(ROOT / sub / f"hud_magic_ax_battler.{ext}",
                        ROOT / sub / f"hud_magic_{CHAR_ID}.{ext}")
    print("wrote HUD magic files")


if __name__ == "__main__":
    main()
