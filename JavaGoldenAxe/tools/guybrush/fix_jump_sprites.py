#!/usr/bin/env python3
"""Attach the detached hair to the jump sprites, and split the merged pair.

The MI2 sheet draws Guybrush's ponytail DETACHED above his head in the jump
poses. Connected-component detection therefore keeps the body only: the hair
blob is smaller than MIN_AREA, so it is dropped, and the reviewer/baker show a
headless body. This tool finds those small "hair" components and grows the
target sprite boxes to include them. It also splits s0262, which is two figures
merged into one box.

    python fix_jump_sprites.py [--dry-run]

sprites.json is backed up to sprites.backup.json first (once). Run this before
make_reviewer.py / build_atlas.py; existing ids are never renumbered, and the
split's second figure is appended as a new id, so mappings stay valid.
Re-running is a no-op once the boxes already contain the hair.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from detect_sprites import (foreground_mask, components, MIN_AREA)  # noqa: E402
from PIL import Image                                               # noqa: E402

SHEET = HERE / "guybrush_source.png"
OUT_JSON = HERE / "sprites.json"
BACKUP = HERE / "sprites.backup.json"

# Sprites whose hair must be folded back into the box (left-to-right jump poses).
TARGETS = ["s0261", "s0256", "s0249", "s0250", "s0257", "s0262"]
# s0262 is actually two figures side by side: keep the left one as s0262 and
# append the right one as a new id.
SPLIT = "s0262"

HAIR_MIN_AREA = 20       # ignore 1-2px specks
HAIR_MAX_AREA = MIN_AREA  # only blobs detection dropped (< MIN_AREA)
MAX_UP_GAP = 20          # hair may sit this far above the body's top edge
MIN_H_OVERLAP = 3
TOUCH_SLACK = 2          # hair bottom may reach the body top within this many px


def box(s):
    return (s["x"], s["y"], s["x"] + s["w"] - 1, s["y"] + s["h"] - 1)


def union_boxes(boxes):
    x1 = min(int(b[0]) for b in boxes)
    y1 = min(int(b[1]) for b in boxes)
    x2 = max(int(b[2]) for b in boxes)
    y2 = max(int(b[3]) for b in boxes)
    return {"x": x1, "y": y1, "w": x2 - x1 + 1, "h": y2 - y1 + 1}


def h_overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) + 1


def hair_above(body, small):
    """Small components sitting just above a body box and horizontally over it."""
    picked = []
    for c in small:
        if h_overlap(body, c) < MIN_H_OVERLAP:
            continue
        if c[3] <= body[1] + TOUCH_SLACK and body[1] - c[3] <= MAX_UP_GAP:
            picked.append(c)
    return picked


def contained(inner, outer):
    return (inner[0] >= outer[0] and inner[1] >= outer[1]
            and inner[2] <= outer[2] and inner[3] <= outer[3])


def main():
    dry = "--dry-run" in sys.argv
    sprites = json.loads(OUT_JSON.read_text())
    by_id = {s["id"]: s for s in sprites}

    mask = foreground_mask(Image.open(SHEET).convert("RGB"))
    raw = components(mask)
    small = [c for c in raw if HAIR_MIN_AREA <= c[4] < HAIR_MAX_AREA]

    next_id = max(int(s["id"][1:]) for s in sprites) + 1
    changes = []
    added = []

    for sid in TARGETS:
        s = by_id.get(sid)
        if s is None:
            print("!! %s not found in sprites.json" % sid)
            continue
        b = box(s)

        if sid == SPLIT:
            bodies = sorted((c for c in raw if c[4] >= HAIR_MAX_AREA
                             and contained(c, b)), key=lambda c: c[0])
            if len(bodies) < 2:
                continue                      # already split
            for c in bodies:
                hair = hair_above(c, small)
                new = union_boxes([c] + [tuple(h) for h in hair])
                if c is bodies[0]:
                    changes.append((sid, box(s), new))
                    s.update(new)
                else:
                    entry = dict(new)
                    entry["id"] = "s%04d" % next_id
                    entry["row"] = round(entry["y"] / 12)
                    next_id += 1
                    added.append(entry)
            continue

        hair = hair_above(b, small)
        if not hair:
            continue                          # already attached
        new = union_boxes([b] + [tuple(h) for h in hair])
        changes.append((sid, b, new))
        s.update(new)

    if not changes and not added:
        print("nothing to do (already fixed)")
        return 0

    print("box changes (x1,y1,x2,y2 -> x1,y1,x2,y2):")
    for sid, old, new in changes:
        print("  %s: %s -> (%d,%d,%d,%d)"
              % (sid, old, new["x"], new["y"],
                 new["x"] + new["w"] - 1, new["y"] + new["h"] - 1))
    for e in added:
        print("  +%s: (%d,%d,%d,%d)"
              % (e["id"], e["x"], e["y"],
                 e["x"] + e["w"] - 1, e["y"] + e["h"] - 1))

    if dry:
        print("(dry run: not written)")
        return 0

    if not BACKUP.exists():
        shutil.copy(OUT_JSON, BACKUP)
        print("backed up ->", BACKUP.name)
    sprites.extend(added)
    OUT_JSON.write_text(json.dumps(sprites, indent=1))
    print("wrote %s (total %d)" % (OUT_JSON.name, len(sprites)))
    print("now run make_reviewer.py (or scripts\\ReviewSprites.bat)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
