#!/usr/bin/env python3
"""De-share the frame layout: give every animation its own rectangles.

The original Ax layout reuses the same rectangle across animations (e.g.
attack_1/attack_2, thrown/stunned_2/stand_up). Because the atlas is keyed by
rectangle, a shared rectangle can only hold ONE sprite, which is why choosing a
sprite per animation is ambiguous and `mapping.rect_overrides` exists.

This tool rewrites the layout into `chars/guybrush_layout.char`:

  * the first animation to use a rectangle keeps it;
  * every later animation that uses it gets a fresh rectangle of the same size,
    allocated in free space to the right of all existing geometry;
  * the `collider` / `point` lines that attach to a moved rectangle are copied
    to the new rectangle (translated), so hitboxes/grab points are preserved.

`build_atlas.py` reads `guybrush_layout.char` when present (else `ax_battler.char`),
so after running this just bake as usual:

    python deshare.py            # write guybrush_layout.char
    python build_atlas.py        # bake it (writes guybrush_threepwood.char)
    python make_reviewer.py      # refresh the reviewer (now no shared rects)

    python deshare.py --check    # verify hitboxes are preserved, write nothing
    python deshare.py --revert   # delete guybrush_layout.char (back to Ax layout)
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "assets" / "res"
SRC_CHAR = ROOT / "chars" / "ax_battler.char"
OUT_CHAR = ROOT / "chars" / "guybrush_layout.char"

SPRITE_RE = re.compile(
    r"^sprite\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")
SPECIAL = ("none", "logo")

GAP = 12  # vertical spacing between freshly allocated rectangles


def intersects(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def inside_point(px, py, r):
    return r[0] <= px < r[0] + r[2] and r[1] <= py < r[1] + r[3]


def read_lines():
    return SRC_CHAR.read_text(encoding="latin-1").splitlines()


def parse(lines):
    """Return (sprite_lines, colliders, points)."""
    sprites = []             # (line_index, anim, x, y, w, h, cx, cy)
    colliders = []           # (line_index, type, x, y, w, h)
    points = []              # (line_index, kind, x, y)
    for i, raw in enumerate(lines):
        m = SPRITE_RE.match(raw.strip())
        if m:
            sprites.append((i, m.group(1), int(m.group(3)), int(m.group(4)),
                            int(m.group(5)), int(m.group(6)),
                            int(m.group(7)), int(m.group(8))))
            continue
        t = raw.strip().split()
        if not t:
            continue
        if t[0] == "collider" and len(t) >= 5:
            x, y, w, h = (int(v) for v in t[-4:])
            colliders.append((i, t[1], x, y, w, h))
        elif t[0] == "point" and len(t) >= 4:
            points.append((i, t[1], int(t[-2]), int(t[-1])))
    return sprites, colliders, points


def frame_order(sprites):
    """anim -> list of distinct (x,y,w,h,cx,cy) in first-appearance order."""
    seen = {}
    order = {}
    for (_i, anim, x, y, w, h, cx, cy) in sprites:
        order.setdefault(anim, [])
        key = (x, y, w, h)
        if key not in seen.setdefault(anim, set()):
            seen[anim].add(key)
            order[anim].append((x, y, w, h, cx, cy))
    return order


def build(lines):
    sprites, colliders, points = parse(lines)
    order = frame_order(sprites)

    # all geometry, to place new rectangles clear of everything
    maxx = 0
    for (_i, _a, x, y, w, h, _cx, _cy) in sprites:
        maxx = max(maxx, x + w)
    for (_i, _t, x, y, w, h) in colliders:
        maxx = max(maxx, x + w)
    for (_i, _k, x, y) in points:
        maxx = max(maxx, x)
    base_x = maxx + 4

    owner = {}                 # rect -> anim (first user keeps it)
    new_coords = {}            # (anim, rect) -> (nx, ny)
    moved = defaultdict(list)  # rect -> [(nx, ny), ...]  (for collider cloning)
    next_y = 0
    alloc_w = 0

    for anim in order:
        if anim in SPECIAL:
            for r in order[anim]:
                owner.setdefault(r[:4], anim)
            continue
        for (x, y, w, h, cx, cy) in order[anim]:
            key = (x, y, w, h)
            if key not in owner:
                owner[key] = anim
            else:
                nx, ny = base_x, next_y
                next_y += h + GAP
                alloc_w = max(alloc_w, w)
                new_coords[(anim, key)] = (nx, ny)
                moved[key].append((nx, ny))

    # rewrite sprite coordinates
    out = list(lines)
    for (i, anim, x, y, w, h, cx, cy) in sprites:
        nc = new_coords.get((anim, (x, y, w, h)))
        if nc is None:
            continue
        nx, ny = nc
        out[i] = re.sub(
            r"^(sprite\s+\S+\s+\S+\s+)\S+\s+\S+(\s+\d+\s+\d+\s+\S+\s+\S+\s*$)",
            lambda m: m.group(1) + str(nx) + " " + str(ny) + m.group(2),
            out[i])

    # clone colliders/points for every moved rectangle
    cloned = []
    for (i, ctype, x, y, w, h) in colliders:
        for key, targets in moved.items():
            if intersects((x, y, w, h), key):
                for (nx, ny) in targets:
                    dx, dy = nx - key[0], ny - key[1]
                    cloned.append("collider %s %s %d %d %d %d"
                                  % (ctype, " ".join(lines[i].split()[2:len(lines[i].split()) - 4]),
                                     x + dx, y + dy, w, h))
    for (i, kind, x, y) in points:
        for key, targets in moved.items():
            if inside_point(x, y, key):
                for (nx, ny) in targets:
                    dx, dy = nx - key[0], ny - key[1]
                    cloned.append("point %s %d %d" % (kind, x + dx, y + dy))

    out.extend(cloned)
    atlas_w = base_x + alloc_w
    atlas_h = max(1000, next_y)
    stats = {
        "sprites": len(sprites),
        "moved_rects": len(new_coords),
        "cloned_colliders": len(cloned),
        "base_x": base_x,
        "atlas": (atlas_w, atlas_h),
    }
    return "\n".join(out) + "\n", stats


def attached(frames_by_anim, colliders, points):
    """anim -> [ frozenset of attached colliders/points, relative to the frame ]."""
    res = {}
    for anim, frames in frames_by_anim.items():
        res[anim] = []
        for (x, y, w, h, cx, cy) in frames:
            s = set()
            for (ctype, cx0, cy0, cw, ch) in colliders:
                if intersects((cx0, cy0, cw, ch), (x, y, w, h)):
                    s.add((ctype, cx0 - x, cy0 - y, cw, ch))
            for (kind, px, py) in points:
                if inside_point(px, py, (x, y, w, h)):
                    s.add(("point", px - x, py - y))
            res[anim].append(frozenset(s))
    return res


def check(layout_text):
    """Compare collider/point attachment before vs after de-sharing."""
    orig_lines = read_lines()
    new_lines = layout_text.splitlines()

    def parse_all(lines):
        sprites, colliders, points = parse(lines)
        frames = {}
        for (_i, anim, x, y, w, h, cx, cy) in sprites:
            if anim in SPECIAL:
                continue
            frames.setdefault(anim, []).append((x, y, w, h, cx, cy))
        cols = [(c[1], c[2], c[3], c[4], c[5]) for c in colliders]
        pts = [(p[1], p[2], p[3]) for p in points]
        return frames, cols, pts

    of, oc, op = parse_all(orig_lines)
    nf, nc_, np_ = parse_all(new_lines)
    ao = attached(of, oc, op)
    an = attached(nf, nc_, np_)

    ok = True
    if set(of) != set(nf):
        print("  animation set changed:", set(of) ^ set(nf)); ok = False
    for anim in sorted(set(of) & set(nf)):
        if len(of[anim]) != len(nf[anim]):
            print(f"  {anim}: frame count {len(of[anim])} -> {len(nf[anim])}"); ok = False; continue
        for i, (a, b) in enumerate(zip(ao[anim], an[anim])):
            if a != b:
                print(f"  {anim} frame {i}: attached set changed")
                print("    before:", sorted(a))
                print("    after :", sorted(b))
                ok = False
    return ok


def main():
    args = sys.argv[1:]
    if "--revert" in args:
        if OUT_CHAR.exists():
            OUT_CHAR.unlink()
            print("removed", OUT_CHAR, "- build_atlas will use ax_battler.char")
        else:
            print("nothing to revert")
        return 0

    lines = read_lines()
    out_text, stats = build(lines)
    print("de-shared layout:")
    print("  sprites          :", stats["sprites"])
    print("  moved rectangles :", stats["moved_rects"])
    print("  cloned colliders :", stats["cloned_colliders"])
    print("  new atlas size   :", stats["atlas"])

    print("checking hitbox preservation ...")
    if not check(out_text):
        print("FAILED: attached colliders/points changed; not writing.")
        return 1
    print("  OK: every frame keeps the same colliders/points.")

    if "--check" in args:
        print("(--check: not writing)")
        return 0

    OUT_CHAR.write_text(out_text, encoding="latin-1")
    print("wrote", OUT_CHAR)
    print("next: python build_atlas.py && python make_reviewer.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
