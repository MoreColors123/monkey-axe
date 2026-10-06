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
         "attack_7", "attack_short", "magic", "walking_side",
         "stunned_1", "stunned_2", "knock_down", "stand_up",
         "thrown", "dying", "dead", "resting",
         "running_attack", "jumping_attack", "jumping_death_stab",
         "jumping", "idle", "walking_down", "walking_up", "running",
         "grab_and_throw", "mounting", "mounted_side", "mounted_side_flip",
         "mounted_up", "mounted_up_flip", "mounted_down", "mounted_down_flip"]


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


def attached_items(rect, colliders, points):
    """Absolute coords of every collider/point attaching to a rect."""
    (x, y, w, h) = rect[:4]
    cols, pts = [], []
    for (_i, head, px, py, pw, ph) in colliders:
        if not (px + pw <= x or x + w <= px or py + ph <= y or y + h <= py):
            cols.append((px, py, pw, ph))
    for (_i, head, px, py) in points:
        if x <= px < x + w and y <= py < y + h:
            pts.append((px, py))
    return cols, pts


def extents(rect, colliders, points):
    """Room the attached items need around the ANCHOR, per side.

    Returns (left, right, up, down) - how far the items reach from the
    anchor (cx, cy). A rect must leave at least this much room on each
    side or a clone will land outside it (unattachable) or inside a
    neighbour (foreign attachment).
    """
    (x, y, w, h, cx, cy) = rect
    cols, pts = attached_items(rect, colliders, points)
    left = right = up = down = 0
    for (px, py, pw, ph) in cols:
        left = max(left, (x + cx) - px)
        right = max(right, (px + pw) - (x + cx))
        up = max(up, (y + cy) - py)
        down = max(down, (py + ph) - (y + cy))
    for (px, py) in pts:
        left = max(left, (x + cx) - px)
        right = max(right, px - (x + cx))
        up = max(up, (y + cy) - py)
        down = max(down, py - (y + cy))
    return (left, right, up, down)


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
    col_x = base_x
    # generous packing: cloned colliders may overhang their rectangle by a
    # tall margin (a BODY box anchored low reaches ~40px above the frame),
    # so new rects must sit far enough apart that foreign clones cannot
    # reach in (12px was enough before colliders were cloned)
    PACK_GAP = 110
    COL_HEIGHT = 2200   # wrap into a fresh column to keep the atlas compact

    def alloc_slot(n_w, n_h):
        nonlocal next_y, col_x
        nx, ny = col_x, next_y
        next_y += n_h + PACK_GAP
        if next_y > COL_HEIGHT:
            col_x += 240
            next_y = 0
        return nx, ny

    out = list(lines)
    fixes = []
    new_rects = []

    # drop exact duplicate collider/point lines - the engine treats each
    # collider as its own hitbox, so duplicates double-count hits
    seen_cl = set()
    deduped = []
    for ln in out:
        t = ln.strip()
        if t.startswith(("collider ", "point ")):
            if t in seen_cl:
                continue
            seen_cl.add(t)
        deduped.append(ln)
    if len(deduped) != len(out):
        print(f"  ~ removed {len(out) - len(deduped)} duplicate "
              f"collider/point line(s)")
        out = deduped
        sprites, colliders, points = parse(out)
        assign = assignments(sprites, ANIMS, mapping)
        before = anchor_rel_sets(None, sprites, colliders, points)

    for anim in sorted(assign):
        entry = mapping["animations"].get(anim) or mapping["animations"]["idle"]
        base = entry.get("scale") or global_scale
        for (rect, sp_id) in assign[anim]:
            sp = sheet.get(sp_id)
            if not sp:
                print(f"  !! {anim}: sprite {sp_id} not in sprites.json")
                continue
            (x, y, w, h, cx, cy) = rect
            mode = (mapping["animations"].get(anim)
                    or mapping["animations"]["idle"]).get("mode", "bottom")
            (ex_l, ex_r, ex_u, ex_d) = extents(rect, colliders, points)
            # sprite room at the target scale (art pasted at px = x+cx-nw//2:
            # left span nw//2, right span nw - nw//2)
            nw = round(base * sp["w"])
            nh = round(base * sp["h"])
            if mode == "center":
                # centre-mode: art centred in the box; preserve the art's
                # exact offset to the anchor (h/2 - cy) so art and hitboxes
                # stay aligned relative to the actor
                art_off = h / 2 - cy            # art centre below anchor
                need_l = max(nw // 2, ex_l)
                need_r = max(nw - nw // 2, ex_r)
                need_u = max(math.ceil(nh / 2 - art_off), ex_u)
                need_d = max(math.ceil(nh / 2 + art_off), ex_d)
                if (cx >= need_l and w - cx >= need_r
                        and cy >= need_u and h - cy >= need_d):
                    continue  # already fits
                n_w = need_l + need_r + 2
                n_cx = need_l + 1
                n_h = need_u + need_d + 2
                n_cy = (n_h - round(2 * art_off)) // 2
                # rounding the art offset may cost a room; grow by 2 (keeps
                # the offset exact) until both rooms are safe
                while n_cy < need_u + 1 or n_h - n_cy < need_d + 1:
                    n_h += 2
                    n_cy = (n_h - round(2 * art_off)) // 2
            else:
                # bottom-mode: art bottom sits on the anchor
                need_l = max(nw // 2, ex_l)
                need_r = max(nw - nw // 2, ex_r)
                need_u = max(nh, ex_u)
                need_d = max(2, ex_d)
                if (cx >= need_l and w - cx >= need_r
                        and cy >= need_u and h - cy >= need_d):
                    continue  # already fits
                n_cx = need_l + 1
                n_w = n_cx + need_r + 1
                n_cy = need_u + 1
                n_h = n_cy + need_d + 1
            nx, ny = alloc_slot(n_w, n_h)
            new_rects.append((anim, (nx, ny, n_w, n_h, n_cx, n_cy), rect))
            fixes.append((anim, rect, sp_id, (nx, ny, n_w, n_h, n_cx, n_cy)))
            # rewrite every sprite line using this rectangle
            for (i, a2, x2, y2, w2, h2, cx2, cy2) in sprites:
                if a2 == anim and (x2, y2, w2, h2) == (x, y, w, h):
                    out[i] = (f"sprite {a2} RIGHT {nx} {ny} {n_w} {n_h} "
                              f"{n_cx} {n_cy}")

    # ---- allocate missing frames (Phase 2b): a mapped frame list longer than
    # the layout's rectangles means frames 2..n never bake ("(extra)" in the
    # reviewer). Allocate fresh rectangles so every distinct mapped id gets
    # one, appended to the animation's block, with the first existing rect's
    # colliders/points cloned anchor-relative (the lunge/stab keeps its
    # hitbox on the new frames).
    # Animations are processed by DESCENDING last-line position: every insert
    # shifts lines below it, so inserting from the bottom of the file upward
    # keeps each animation's computed insert index valid.
    alloc_order = sorted(assign, key=lambda a: -max(
        (i for (i, a2, *_r) in sprites if a2 == a), default=-1))
    for anim in alloc_order:
        entry = mapping["animations"].get(anim) or mapping["animations"]["idle"]
        ids = entry.get("frames") or mapping["animations"]["idle"]["frames"]
        rects = [r for (r, _sid) in assign[anim]]
        # distinct ids in list order; the baker assigns ids[i % len(ids)] to
        # rect i, so max(distinct, existing) rects cover every distinct pose
        distinct_ids = list(dict.fromkeys(ids))
        target = max(len(distinct_ids), len(rects))
        if target <= len(rects):
            continue
        base = entry.get("scale") or global_scale
        mode = entry.get("mode", "bottom")
        insert_at = max(i for (i, a2, *_rest) in sprites if a2 == anim) + 1
        (ox, oy, ow, oh, ocx, ocy) = rects[0]
        (ex_l, ex_r, ex_u, ex_d) = extents(rects[0], colliders, points)
        added = []
        for k in range(len(rects), target):
            sp = sheet.get(ids[k % len(ids)])
            if not sp:
                print(f"  !! {anim}: sprite {ids[k % len(ids)]} not in sprites.json")
                continue
            if mode == "center":
                half_w = math.ceil(base * sp["w"] / 2)
                half_h = math.ceil(base * sp["h"] / 2)
                # keep the same art-to-anchor offset as the clone source so
                # multi-frame lying animations do not wobble
                src_art_off = (oh / 2 - ocy)
                need_l = max(half_w, ex_l)
                need_r = max(half_w, ex_r)
                need_u = max(math.ceil(half_h - src_art_off), ex_u)
                need_d = max(math.ceil(half_h + src_art_off), ex_d)
                n_w = need_l + need_r + 2
                n_cx = need_l + 1
                n_h = need_u + need_d + 2
                n_cy = (n_h - round(2 * src_art_off)) // 2
                while n_cy < need_u + 1 or n_h - n_cy < need_d + 1:
                    n_h += 2
                    n_cy = (n_h - round(2 * src_art_off)) // 2
            else:
                half = math.ceil(base * sp["w"] / 2)
                n_cx = max(half, ex_l) + 1
                n_w = n_cx + max(half, ex_r) + 1
                n_cy = max(math.ceil(base * sp["h"]), ex_u) + 1
                n_h = n_cy + max(2, ex_d) + 1
            nx, ny = alloc_slot(n_w, n_h)
            out.insert(insert_at,
                       f"sprite {anim} RIGHT {nx} {ny} {n_w} {n_h} {n_cx} {n_cy}")
            insert_at += 1
            added.append((anim, (nx, ny, n_w, n_h, n_cx, n_cy), rects[0]))
        new_rects.extend(added)
        # NOTE: no clone loop here - the shared clone block below iterates
        # new_rects (allocated included); cloning here AND there would write
        # duplicate collider lines (double-counted hitboxes)
        if added:
            print(f"  + {anim}: allocated {len(added)} new frame rect(s) "
                  f"(was {len(rects)}, target {target})")

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
    # 1. per-frame anchor-relative attachment sets must be identical; frames
    # ADDED by this run must clone the first frame's attachment exactly
    for anim in set(list(before) + list(after)):
        b = [(fr, s) for (_i, fr, s) in before.get(anim, [])]
        a = [(fr, s) for (_i, fr, s) in after.get(anim, [])]
        if len(a) < len(b):
            print(f"  !! {anim}: lost frames ({len(b)} -> {len(a)})"); ok = False; continue
        for k, (fb, sb) in enumerate(b):
            if a[k][1] != sb:
                print(f"  !! {anim} frame {k}: attached set changed")
                print("    before:", sorted(sb))
                print("    after :", sorted(a[k][1])); ok = False
        for k in range(len(b), len(a)):
            if b and a[k][1] != b[0][1]:
                print(f"  !! {anim} new frame {k}: attachment differs from "
                      f"clone source")
                print("    source:", sorted(b[0][1]))
                print("    new   :", sorted(a[k][1])); ok = False
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