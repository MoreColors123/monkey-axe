#!/usr/bin/env python3
"""Bake Guybrush Threepwood art into Ax Battler's exact frame layout.

Reads ax_battler.char (frame rects + anchors + colliders + points), paints the
corresponding Guybrush source sprite into every frame rectangle, and writes a
drop-in spritesheet (guybrush_threepwood.png) plus a .char copy.
"""
from PIL import Image
import numpy as np
import re, os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = str(HERE.parent.parent / "assets" / "res")
SRC_PATH = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "guybrush_source.png")
SRC = Image.open(SRC_PATH).convert("RGB")
ATLAS_W, ATLAS_H = 600, 1000
GLOBAL_S = 1.15

BG = np.array([0, 136, 68])

def key_green(im):
    a = np.array(im).astype(np.int16)
    dist = np.abs(a - BG).sum(axis=2)
    alpha = np.where(dist > 45, 255, 0).astype(np.uint8)
    rgba = np.dstack([np.array(im), alpha])
    return Image.fromarray(rgba, "RGBA")

def tile(rect):
    x, y, w, h = rect
    return key_green(SRC.crop((x, y, x + w, y + h)))

# --- source sprite libraries (x,y,w,h in the MI2 sheet) ---
SIDE = [(63,6,21,47),(108,6,19,47),(149,7,32,46),(201,6,18,47),(243,6,19,47),(285,7,31,46)]
FRONT = [(1,2165,23,47),(40,2165,23,47),(79,2165,23,47),(115,2165,26,47),
         (154,2165,26,47),(193,2165,26,47),(232,2165,26,47),(272,2165,27,47)]
IDLE = [(378,5,24,47),(558,5,25,47),(467,6,27,47)]
BACK = [(18,178,33,37),(63,178,36,37),(106,178,32,37),(154,177,24,38),
        (199,176,26,39),(243,178,24,37)]
ATK = [(249,118,37,47),(199,60,33,47),(243,60,35,47),(468,168,32,47)]
SWORD = [(294,114,34,51),(296,463,38,48)]
JUMP = [(157,111,26,53),(294,114,34,51)]
LIE = [(497,1149,51,26),(3,1595,46,27),(148,1734,44,27),(373,2282,38,25),(296,2061,45,30)]
FACE = (301,378,20,21)

# animation name -> (frame list, mode)  mode: bottom | center
AMAP = {
    "idle": (IDLE, "bottom"),
    "walking_down": (FRONT, "bottom"),
    "walking_up": (BACK, "bottom"),
    "running": (SIDE, "bottom"),
    "running_attack": (SIDE, "bottom"),
    "jumping": (JUMP, "bottom"),
    "jumping_attack": (JUMP, "bottom"),
    "jumping_death_stab": (JUMP, "bottom"),
    "attack_1": (ATK, "bottom"),
    "attack_2": (ATK, "bottom"),
    "attack_3": (ATK, "bottom"),
    "attack_5": (ATK, "bottom"),
    "attack_6": (ATK, "bottom"),
    "attack_7": (ATK, "bottom"),
    "attack_short": (ATK, "bottom"),
    "attack_special": (SWORD, "bottom"),
    "attack_special_return": (ATK, "bottom"),
    "grab_and_throw": (ATK, "bottom"),
    "thrown": (LIE, "center"),
    "stunned_1": (IDLE, "bottom"),
    "stunned_2": (IDLE, "bottom"),
    "knock_down": (LIE, "center"),
    "stand_up": (IDLE, "bottom"),
    "mounting": (IDLE, "bottom"),
    "mounted_side": (IDLE, "bottom"),
    "mounted_side_flip": (IDLE, "bottom"),
    "mounted_down": (IDLE, "bottom"),
    "mounted_down_flip": (IDLE, "bottom"),
    "mounted_up": (IDLE, "bottom"),
    "mounted_up_flip": (IDLE, "bottom"),
    "resting": (LIE, "center"),
    "magic": (JUMP, "bottom"),
    "dying": (LIE, "center"),
    "dead": (LIE, "center"),
}

sprite_re = re.compile(r"^sprite\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")

def parse_frames(char_path):
    frames = []
    with open(char_path, "r", encoding="latin-1") as f:
        for line in f:
            m = sprite_re.match(line.strip())
            if m:
                anim = m.group(1)
                frames.append((anim, int(m.group(3)), int(m.group(4)),
                               int(m.group(5)), int(m.group(6)),
                               int(m.group(7)), int(m.group(8))))
    return frames

def _place(dst, src, x, y):
    dst.paste(src, (x, y), src)


def fit_scale(spr, rect, mode):
    x, y, w, h, cx, cy = rect
    sw, sh = spr.size
    s = GLOBAL_S
    if mode == "bottom" and cy > 0:
        s = min(s, cy / sh)
    s = min(s, w / sw)
    if mode == "center":
        s = min(GLOBAL_S, h / sh, w / sw)
    s = max(s, 0.1)
    return s

def main():
    ax_char = os.path.join(ROOT, "chars", "ax_battler.char")
    frames = parse_frames(ax_char)
    per_anim_counter = {}

    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    src_cache = {}
    for (anim, x, y, w, h, cx, cy) in frames:
        if anim == "none":
            continue
        if anim == "logo":
            spr = tile(FACE).resize((w, h), Image.NEAREST)
            _place(atlas, spr, x, y)
            continue
        if anim not in AMAP:
            srclist, mode = IDLE, "bottom"
        else:
            srclist, mode = AMAP[anim]
        idx = per_anim_counter.get(anim, 0)
        per_anim_counter[anim] = idx + 1
        srcrect = srclist[idx % len(srclist)]
        key = srcrect
        if key not in src_cache:
            src_cache[key] = tile(srcrect)
        spr = src_cache[key]
        sw, sh = spr.size
        s = fit_scale(spr, (x, y, w, h, cx, cy), mode)
        nw, nh = max(1, round(sw * s)), max(1, round(sh * s))
        scaled = spr.resize((nw, nh), Image.NEAREST)
        if mode == "center":
            px = x + cx - nw // 2
            py = y + (h - nh) // 2
        else:
            px = x + cx - nw // 2
            py = y + cy - nh
        # clip strictly to the frame rect so packed neighbours never bleed
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        layer.paste(scaled, (px - x, py - y), scaled)
        _place(atlas, layer, x, y)

    out_png = os.path.join(ROOT, "image", "guybrush_threepwood.png")
    atlas.save(out_png)
    print("wrote", out_png, atlas.size)

    # --- write .char ---
    out_char = os.path.join(ROOT, "chars", "guybrush_threepwood.char")
    with open(ax_char, "r", encoding="latin-1") as f:
        content = f.read()
    content = content.replace("# --- ax battler ---",
                              "# --- guybrush threepwood (reskin of ax battler) ---", 1)
    with open(out_char, "w", encoding="latin-1") as f:
        f.write(content)
    print("wrote", out_char)

    # --- hud magic copy ---
    for ext in ("char", "png"):
        s = os.path.join(ROOT, "chars" if ext == "char" else "image",
                         f"hud_magic_ax_battler.{ext}")
        d = os.path.join(ROOT, "chars" if ext == "char" else "image",
                         f"hud_magic_guybrush_threepwood.{ext}")
        shutil.copyfile(s, d)
        print("wrote", d)

if __name__ == "__main__":
    main()
