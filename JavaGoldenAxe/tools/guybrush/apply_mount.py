#!/usr/bin/env python3
"""Make the mount frame rectangles fit the placements from the mount editor.

The mount editor (mount_editor.html) records, per rider animation, where the
pose sits relative to the frame's *anchor* - the anchor is what the engine pins
to the beast's `mounted_*` point. A pose dragged to a new spot usually needs a
different rectangle than the one currently in the layout, so this rewrites the
`sprite <anim> RIGHT x y w h cx cy` lines for the mounted_* animations:

  1. keep the rectangle untouched when the art already fits inside it,
  2. otherwise grow it in place if the bigger box touches no other rectangle,
  3. otherwise allocate a fresh slot to the right of all geometry
     (build_atlas.py sizes the canvas from the rectangles, so the atlas grows).

A rectangle is only valid if the whole pose fits inside it, because the baker
clips to the rectangle and the engine draws exactly that rectangle with the
anchor on the mount point:
    cx + dx >= 0   and   cx + dx + nw <= w      (and the same for y)

Nothing attaches to the mount rectangles - no collider or point in the layout
intersects them - so growing or moving them cannot break a hitbox or grab point.

usage: apply_mount.py [--check] [--placements FILE]
"""
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "assets" / "res"
LAYOUT = ROOT / "chars" / "guybrush_layout.char"
PLACEMENTS = HERE / "mount_placements.json"
MAPPING = HERE / "mapping.json"
MAPPING_BACKUP = HERE / "mapping.backup.json"
MARGIN = 1

sprite_re = re.compile(
    r"^(sprite\s+(\S+)\s+(\S+)\s+)(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")


def parse_layout(path):
    lines, rects = [], []
    for i, line in enumerate(path.read_text(encoding="latin-1").splitlines()):
        m = sprite_re.match(line.strip())
        if m:
            rects.append({"line": i, "anim": m.group(2),
                          "x": int(m.group(4)), "y": int(m.group(5)),
                          "w": int(m.group(6)), "h": int(m.group(7)),
                          "cx": int(m.group(8)), "cy": int(m.group(9))})
        lines.append(line)
    return lines, rects


def overlaps(a, b):
    return (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
            and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"])


def art_box(entry, sprite):
    """-> (nw, nh, dx, dy) with dx/dy = art top-left relative to the anchor"""
    nw = max(1, round(sprite["w"] * entry["scale"]))
    nh = max(1, round(sprite["h"] * entry["scale"]))
    dx, dy = entry["dx"], entry["dy"]
    if entry.get("flip"):
        dx = -(dx + nw)                     # mirrored about the anchor
    return nw, nh, dx, dy


def fits(rect, nw, nh, dx, dy):
    return (rect["cx"] + dx >= 0 and rect["cx"] + dx + nw <= rect["w"]
            and rect["cy"] + dy >= 0 and rect["cy"] + dy + nh <= rect["h"])


def main():
    check = "--check" in sys.argv
    pfile = PLACEMENTS
    if "--placements" in sys.argv:
        pfile = Path(sys.argv[sys.argv.index("--placements") + 1])
    placements = json.loads(pfile.read_text())["placements"]
    sprites = {s["id"]: s for s in json.loads((HERE / "sprites.json").read_text())}
    lines, rects = parse_layout(LAYOUT)

    by_anim = {}
    for r in rects:
        by_anim.setdefault(r["anim"], []).append(r)

    live = [dict(r) for r in rects]                 # every rectangle, updated as we go
    max_x = max(r["x"] + r["w"] for r in rects)
    slot_y = 0
    plan = []

    for anim in sorted(placements):
        entry = placements[anim]
        targets = by_anim.get(anim)
        if not targets:
            print(f"  {anim}: no rectangles in the layout - skipped")
            continue
        sprite = sprites[entry["pose"]]
        nw, nh, dx, dy = art_box(entry, sprite)
        flip = " FLIP" if entry.get("flip") else ""
        for r in targets:
            me = next(l for l in live if l["line"] == r["line"])
            if fits(r, nw, nh, dx, dy):
                plan.append((me, dict(me), "unchanged"))
                print(f"  {anim:19s} pose {entry['pose']} {sprite['w']}x{sprite['h']}"
                      f" scale {entry['scale']:<5} offset ({dx},{dy}){flip}"
                      f" -> fits rect {r['w']}x{r['h']} anchor {r['cx']},{r['cy']}"
                      f"  [unchanged]")
                continue

            acx = max(0, -dx) + MARGIN
            acy = max(0, -dy) + MARGIN
            w = acx + dx + nw + MARGIN
            h = acy + dy + nh + MARGIN
            candidate = {"x": me["x"], "y": me["y"], "w": w, "h": h, "cx": acx, "cy": acy}
            others = [o for o in live if o["line"] != me["line"]]
            if any(overlaps(candidate, o) for o in others):
                candidate = {"x": max_x + 8, "y": slot_y, "w": w, "h": h,
                             "cx": acx, "cy": acy}
                slot_y += h + 8
                note = f"allocated ({candidate['x']},{candidate['y']})"
            else:
                note = "grown in place"
            me.update(candidate)
            plan.append((me, dict(candidate), note))
            print(f"  {anim:19s} pose {entry['pose']} {sprite['w']}x{sprite['h']}"
                  f" scale {entry['scale']:<5} offset ({dx},{dy}){flip}"
                  f" -> rect {w}x{h} anchor {acx},{acy}  [{note}]"
                  f"  (was {r['w']}x{r['h']} anchor {r['cx']},{r['cy']})")

    # global sanity: two rectangles may share a slot only when they are exactly
    # the same box (the original layout repeats a rectangle to hold a pose over
    # several frames). Any *partial* overlap would make the atlas paste two
    # different poses into one slot - that must never happen.
    def same_box(a, b):
        return (a["x"], a["y"], a["w"], a["h"]) == (b["x"], b["y"], b["w"], b["h"])

    bad = [(a, b) for i, a in enumerate(live) for b in live[i + 1:]
           if a["anim"] != "logo" and b["anim"] != "logo"
           and not same_box(a, b) and overlaps(a, b)]
    if bad:
        print(f"\nERROR: {len(bad)} overlapping rectangle pair(s) after the plan:")
        for a, b in bad[:10]:
            print(f"   {a['anim']} ({a['x']},{a['y']},{a['w']},{a['h']}) <-> "
                  f"{b['anim']} ({b['x']},{b['y']},{b['w']},{b['h']})")
        print("nothing written")
        return 1
    print(f"\noverlap check: clean ({len(live)} rectangles)")

    if check:
        print("--check: nothing written")
        return 0

    for me, box, note in plan:
        m = sprite_re.match(lines[me["line"]].strip())
        lines[me["line"]] = (m.group(1) + f"{box['x']} {box['y']} "
                             f"{box['w']} {box['h']} {box['cx']} {box['cy']}")
    LAYOUT.write_text("\n".join(lines) + "\n", encoding="latin-1")
    print(f"wrote {LAYOUT}")

    # merge the placements into mapping.json so build_atlas.py bakes them
    mapping = json.loads(MAPPING.read_text())
    for anim, entry in placements.items():
        e = mapping["animations"].setdefault(anim, {})
        e["mode"] = "place"
        e["frames"] = [entry["pose"]]
        e["scale"] = entry["scale"]
        e["offset"] = [entry["dx"], entry["dy"]]
        e["flip"] = True if entry.get("flip") else None
        if e["flip"] is None:
            del e["flip"]
        e.pop("hip", None)
        e.pop("hip_x", None)
    shutil.copyfile(MAPPING, MAPPING_BACKUP)
    MAPPING.write_text(json.dumps(mapping, indent=1), encoding="utf-8")
    print(f"wrote {MAPPING} (backup: {MAPPING_BACKUP.name})")
    print("next: python build_atlas.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
