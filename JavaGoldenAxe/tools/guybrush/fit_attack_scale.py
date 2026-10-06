#!/usr/bin/env python3
"""Enlarge attack frame rectangles so the cutlass cycle bakes at full scale.

The baker clamps a bottom-mode animation's scale to `cy / sprite_h` per frame
(build_atlas.fit_scale) and pastes the sprite bottom-centre on the anchor
`(cx, cy)`, clipping at the rectangle edges. The unified attack cycle uses
tall/wide sprites (s0321 23x54, s0322 42x47, s0320 37x47), and several
inherited attack rectangles have anchors too high (cy 46-58) or too little
room around the anchor, so attacks baked 3-15% smaller than the idle pose.

This tool rewrites `guybrush_layout.char`: each affected frame gets a fresh
rectangle in free atlas space (beyond all geometry, like deshare.py), sized
so the sprite fits around its anchor at the target scale. Colliders/points
that attached to the old rectangle are cloned, preserving their offset to the
ANCHOR - the engine stores collider offsets relative to
`rect_origin + (cx, cy)` (Animation.addFrame subtracts sprite.getCenterX/Y),
which is the actor's world position, so hitboxes stay exactly where they were
relative to the character.

    python fit_attack_scale.py            # fix + write guybrush_layout.char
    python fit_attack_scale.py --check    # verify only, write nothing

Afterwards: python build_atlas.py && python make_reviewer.py
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "assets" / "res"
LAYOUT = ROOT / "chars" / "guybrush_layout.char"
MAPPING = HERE / "mapping.json"
SPRITES = HERE / "sprites.json"

SPRITE_RE = re.compile(
    r"^sprite\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")
GAP = 12

# Animations whose frames must fit the cycle at full scale.
ANIMS = ["attack_1", "attack_2", "attack_3", "attack_5", "attack_6",
         "attack_7", "attack_short", "magic"]


def parse(lines):
    sprites = []    # (line_idx, anim, x, y, w, h, cx, cy)
    colliders = []  # (line_idx, tokens, x, y, w, h)
    points = []     # (line_idx, tokens, x, y)
    for i, raw in enumerate(lines):
        m = SPRITE_RE.match(raw.strip())
        if m:
            nums = [int(m.group(k)) for k in range(3, 9)]
            sprites.append((i, m.group(1), *nums))
            continue
        t = raw.split()
        if not t:
            continue
        if t[0] == "collider" and len(t) >= 5:
            x, y, w, h = (int(v) for v in t[-4:])
            colliders.append((i, t[:-4], x, y, w, h))
        elif t[0] == "point" and len(t) >= 4:
            points.append((i, t[:-2], int(t[-2]), int(t[-1])))
    return sprites, colliders, points


def distinct_rects(sprites, anims):
    """anim -> [(rect, sprite_line_idxs...)] first-appearance order."""
    order, seen = {}, {}
    for (i, anim, x, y, w, h, cx, cy) in sprites:
        if anim not in anims:
            continue
        key = (x, y, w, h)
        st = seen.setdefault(anim, set())
        if key not in st:
            st.add(key)
            order.setdefault(anim, []).append((x, y, w, h, cx, cy))
    return order


def assignments(sprites, anims, mapping):
    """Mirror the baker: distinct rect i of an animation gets frames[i % n]."""
    order = distinct_rects(sprites, anims)
    res = {}
    for anim, rects in order.items():
        entry = mapping["animations"].get(anim) or mapping["animations"]["idle"]
        ids = entry.get("frames") or mapping["animations"]["idle"]["frames"]
        res[anim] = list(zip(rects, [ids[i % len(ids)] for i in range(len(rects))]))
    return res


def anchor_rel_sets(lines_by_rect, sprites, colliders, points):
    """(anim) -> [frozenset of (kind, dx, dy, ...) relative to rect+anchor]."""
    res = {}
    for (i, anim, x, y, w, h, cx, cy) in sprites:
        s = set()
        for (_j, head, px, py, pw, ph) in colliders:
            if not (px + pw <= x or x + w <= px or py + ph <= y or y + h <= py):
                s.add(("col", head[0] if head else "", px - x - cx, py - y - cy, pw, ph))
        for (_j, head, px, py) in points:
            if x <= px < x + w and y <= py < y + h:
                s.add(("pt", head[0] if head else "", px - x - cx, py - y - cy))
        res.setdefault(anim, []).append((i, (x, y, w, h, cx, cy), frozenset(s)))
    return res


def main():
    check_only = "--check" in sys.argv[1:]
    lines = LAYOUT.read_text(encoding="latin-1").splitlines()
    sprites, colliders, points = parse(lines)
    mapping = json.loads(MAPPING.read_text())
    sheet = {s["id"]: s for s in json.loads(SPRITES.read_text())}
    global_scale = mapping.get("global_scale", 1.15)

    assign = assignments(sprites, ANIMS, mapping)

    before = anchor_rel_sets(None, sprites, colliders, points)

    # geometry bounds for fresh allocation (beyond every sprite/collider/point)
    maxx = 0
    for (_i, _a, x, y, w, h, _cx, _cy) in sprites:
        maxx = max(maxx, x + w)
    for (_i, _t, x, y, w, h) in colliders:
        maxx = max(maxx, x + w)
    for (_i, _t, x, y) in points:
        maxx = max(maxx, x)

    base_x = maxx + 4
    next_y = 0
    out = list(lines)
    fixes = []
    new_rects = []

    for anim in sorted(assign):
        entry = mapping["animations"].get(anim) or mapping["animations"]["idle"]
        base = entry.get("scale") or global_scale
        for (rect, sp_id) in assign[anim]:
            sp = sheet.get(sp_id)
            if not sp:
                print(f"  !! {anim}: sprite {sp_id} not in sprites.json")
                continue
            (x, y, w, h, cx, cy) = rect
            half = math.ceil(base * sp["w"] / 2)
            need_cy = math.ceil(base * sp["h"])
            d_cx = max(0, half - cx)
            d_cy = max(0, need_cy - cy)
            n_cx = cx + d_cx
            n_w = max(w + d_cx, n_cx + half)
            n_cy = cy + d_cy
            n_h = h + d_cy
            if d_cx == 0 and d_cy == 0 and n_w == w:
                continue  # already fits
            nx, ny = base_x, next_y
            next_y += n_h + GAP
            new_rects.append((anim, (nx, ny, n_w, n_h, n_cx, n_cy), rect))
            fixes.append((anim, rect, sp_id, (nx, ny, n_w, n_h, n_cx, n_cy)))
            # rewrite every sprite line using this rectangle
            for (i, a2, x2, y2, w2, h2, cx2, cy2) in sprites:
                if a2 == anim and (x2, y2, w2, h2) == (x, y, w, h):
                    out[i] = (f"sprite {a2} RIGHT {nx} {ny} {n_w} {n_h} "
                              f"{n_cx} {n_cy}")

    # clone colliders/points for the moved rectangles, anchor-relative
    cloned = []
    for (_i, head, px, py, pw, ph) in colliders:
        for (anim, new, old) in new_rects:
            (ox, oy, ow, oh, ocx, ocy) = old
            if not (px + pw <= ox or ox + ow <= px or py + ph <= oy or oy + oh <= py):
                (nx, ny, nw_, nh_, ncx, ncy) = new
                tx = nx + ncx + (px - (ox + ocx))
                ty = ny + ncy + (py - (oy + ocy))
                cloned.append(" ".join(["collider"] + head[1:]
                                       + [str(tx), str(ty), str(pw), str(ph)]))
    for (_i, head, px, py) in points:
        for (anim, new, old) in new_rects:
            (ox, oy, ow, oh, ocx, ocy) = old
            if ox <= px < ox + ow and oy <= py < oy + oh:
                (nx, ny, nw_, nh_, ncx, ncy) = new
                tx = nx + ncx + (px - (ox + ocx))
                ty = ny + ncy + (py - (oy + ocy))
                cloned.append(" ".join(["point"] + head[1:] + [str(tx), str(ty)]))

    if not fixes:
        print("nothing to fix - every frame already fits at full scale")
        return 0

    print(f"{len(fixes)} rectangle(s) to enlarge:")
    for (anim, rect, sp_id, new) in fixes:
        (x, y, w, h, cx, cy) = rect
        (nx, ny, nw_, nh_, ncx, ncy) = new
        print(f"  {anim} {sp_id}: ({x},{y} {w}x{h} c{cx},{cy}) -> "
              f"({nx},{ny} {nw_}x{nh_} c{ncx},{ncy})")

    out.extend(cloned)

    # ---- verification ----
    ns, nc_, np_ = parse(out)
    after = anchor_rel_sets(None, ns, nc_, np_)
    ok = True
    # 1. per-frame anchor-relative attachment sets must be identical
    for anim in set(list(before) + list(after)):
        b = [(fr, s) for (_i, fr, s) in before.get(anim, [])]
        a = [(fr, s) for (_i, fr, s) in after.get(anim, [])]
        if len(b) != len(a):
            print(f"  !! {anim}: frame count changed"); ok = False; continue
        for k, ((fb, sb), (fa, sa)) in enumerate(zip(b, a)):
            if sb != sa:
                print(f"  !! {anim} frame {k}: attached set changed"); ok = False
    # 2. no overlapping distinct sprite rectangles (duplicate lines sharing one
#    rectangle are intentional - several frames may use the same rect)
    rects = sorted({(a, x, y, w, h) for (_i, a, x, y, w, h, _cx, _cy) in ns})
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            (a1, x1, y1, w1, h1), (a2, x2, y2, w2, h2) = rects[i], rects[j]
            if not (x1 + w1 <= x2 or x2 + w2 <= x1
                    or y1 + h1 <= y2 or y2 + h2 <= y1):
                print(f"  !! overlap: {a1} ({x1},{y1} {w1}x{h1}) vs "
                      f"{a2} ({x2},{y2} {w2}x{h2})"); ok = False
    # 3. new rects must not pick up foreign colliders/points
    for (anim, new, old) in new_rects:
        (nx, ny, nw_, nh_, ncx, ncy) = new
        for (_i, head, px, py, pw, ph) in colliders:
            inside_new = not (px + pw <= nx or nx + nw_ <= px
                              or py + ph <= ny or ny + nh_ <= py)
            was_old = not (px + pw <= old[0] or old[0] + old[2] <= px
                           or py + ph <= old[1] or old[1] + old[3] <= py)
            if inside_new and not was_old:
                print(f"  !! {anim}: foreign collider attaches to new rect "
                      f"at {px},{py}"); ok = False
        for (_i, head, px, py) in points:
            inside_new = nx <= px < nx + nw_ and ny <= py < ny + nh_
            was_old = old[0] <= px < old[0] + old[2] and old[1] <= py < old[1] + old[3]
            if inside_new and not was_old:
                print(f"  !! {anim}: foreign point attaches to new rect "
                      f"at {px},{py}"); ok = False

    print("hitbox preservation:", "OK" if ok else "FAILED")
    if not ok:
        return 1
    if check_only:
        print("(--check: not writing)")
        return 0

    LAYOUT.write_text("\n".join(out) + "\n", encoding="latin-1")
    print(f"wrote {LAYOUT}")
    print("next: python build_atlas.py && python make_reviewer.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())