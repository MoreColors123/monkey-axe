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
    # "bottom": keep one consistent size per character (clamp only by the space
    # above the anchor, never by width - a wide pose just clips at the frame
    # edge instead of shrinking the whole body).
    # "center": fit inside the frame (used for lying poses).
    if mode == "center" or cy <= 0:
        s = min(base, h / spr_h, w / spr_w)
    else:
        s = min(base, cy / spr_h)
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

    # Prefer a de-shared layout (deshare.py) if one exists; otherwise use Ax's.
    layout_path = ROOT / "chars" / "guybrush_layout.char"
    if not layout_path.exists():
        layout_path = ROOT / "chars" / "ax_battler.char"
    frames = parse_frames(layout_path)
    # a de-shared layout adds rectangles to the right, so size the canvas to fit
    max_x = max((x + w for (_a, x, y, w, h, cx, cy) in frames), default=ATLAS_W)
    max_y = max((y + h for (_a, x, y, w, h, cx, cy) in frames), default=ATLAS_H)
    atlas = Image.new("RGBA", (max(ATLAS_W, max_x), max(ATLAS_H, max_y)),
                      (0, 0, 0, 0))

    # Group sprite lines by animation, preserving order. Within one animation a
    # rectangle may repeat (the original art holds a pose for several frames);
    # those repeats must map to the SAME source sprite, otherwise the atlas
    # (which is keyed by rectangle) collapses the animation into one pose.
    grouped = {}
    order = []
    for (anim, x, y, w, h, cx, cy) in frames:
        if anim not in grouped:
            grouped[anim] = []
            order.append(anim)
        grouped[anim].append((x, y, w, h, cx, cy))

    # The atlas has ONE slot per rectangle, but the original layout reuses the
    # same rectangle across several animations (e.g. attack_1/attack_2,
    # thrown/stunned_2/stand_up). A rectangle must therefore resolve to exactly
    # one sprite + size + mode. The first animation (in layout order) that uses
    # a rectangle owns it; later animations reuse its choice. This is what stops
    # two poses being alpha-composited into the same slot (the "doubled sprite"
    # bug). A rectangle can be forced with mapping["rect_overrides"].
    plan = {}

    def plan_animation(anim):
        flist = grouped[anim]
        entry = animations.get(anim) or animations["idle"]
        ids = entry.get("frames") or animations["idle"]["frames"]
        mode = entry.get("mode", "bottom")
        base = entry.get("scale", global_scale)

        distinct = []
        seen = set()
        for (x, y, w, h, cx, cy) in flist:
            key = (x, y, w, h)
            if key not in seen:
                seen.add(key)
                distinct.append((x, y, w, h, cx, cy))
        if not distinct:
            return

        # One scale for the whole "bottom" animation. A frame's anchor (cy) can
        # differ from its neighbours (e.g. stunned_1 stands tall then crouches),
        # and fitting every frame to its own anchor made one pose pop out larger.
        # Fitting the whole animation to the smallest anchor keeps the character
        # a constant size. "center" (lying) poses still fit their own box.
        uniform = None
        if mode != "center":
            uniform = min(
                fit_scale(sprites[ids[i % len(ids)]]["w"],
                          sprites[ids[i % len(ids)]]["h"],
                          w, h, cx, cy, mode, base)
                for i, (x, y, w, h, cx, cy) in enumerate(distinct))

        for i, (x, y, w, h, cx, cy) in enumerate(distinct):
            key = (x, y, w, h)
            if key in plan:
                continue
            sp_id = ids[i % len(ids)]
            if mode == "center":
                sc = fit_scale(sprites[sp_id]["w"], sprites[sp_id]["h"],
                               w, h, cx, cy, mode, base)
            else:
                sc = uniform
            plan[key] = {"rect": (x, y, w, h, cx, cy), "id": sp_id,
                         "mode": mode, "scale": sc, "owner": anim}

    for anim in order:
        if anim not in ("none", "logo"):
            plan_animation(anim)

    # optional per-rectangle override, e.g. {"176,296,39,55": "s0050"} or
    # {"176,296,39,55": {"id": "s0050", "scale": 1.0}}
    for key_str, ov in (mapping.get("rect_overrides") or {}).items():
        key = tuple(int(t) for t in key_str.split(","))
        p = plan.get(key)
        if not p:
            continue
        if isinstance(ov, str):
            p["id"] = ov
        elif isinstance(ov, dict):
            for field in ("id", "mode", "scale"):
                if field in ov:
                    p[field] = ov[field]

    if "logo" in grouped:
        x, y, w, h, cx, cy = grouped["logo"][0]
        spr = tile(sprites[face_id]).resize((w, h), Image.NEAREST)
        place(atlas, spr, x, y)

    for p in plan.values():
        x, y, w, h, cx, cy = p["rect"]
        spr = tile(sprites[p["id"]])
        s = p["scale"]
        nw, nh = max(1, round(spr.width * s)), max(1, round(spr.height * s))
        scaled = spr.resize((nw, nh), Image.NEAREST)
        if p["mode"] == "center":
            px, py = x + cx - nw // 2, y + (h - nh) // 2
        else:
            px, py = x + cx - nw // 2, y + cy - nh
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        layer.paste(scaled, (px - x, py - y), scaled)
        # replace the whole rectangle (no alpha mask) so nothing can ghost
        atlas.paste((0, 0, 0, 0), (x, y, x + w, y + h))
        atlas.paste(layer, (x, y))

    out_png = ROOT / "image" / f"{CHAR_ID}.png"
    atlas.save(out_png)
    print("wrote", out_png, atlas.size)

    out_char = ROOT / "chars" / f"{CHAR_ID}.char"
    content = layout_path.read_text(encoding="latin-1")
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
