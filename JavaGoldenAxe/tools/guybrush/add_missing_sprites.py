#!/usr/bin/env python3
"""Append manually-scoped sprites to sprites.json WITHOUT renumbering.

detect_sprites.py merges figures that touch via ground-level dirt pixels;
a whole row can collapse into one oversized component and be dropped
(MAX_DIM), leaving it invisible to the reviewer. This tool re-detects ONLY
inside a given band, splits merged blobs by foreground-free column gaps,
and APPENDS the figures as new ids (sNNNN continuing after the current
maximum) - existing ids are never touched, so mappings stay valid.

    python add_missing_sprites.py X0 Y0 X1 Y1 [--min-area N] [--dry-run]

    e.g. the horn row: python add_missing_sprites.py 400 2120 900 2175
Afterwards re-run make_reviewer.py so the page embeds the new sprites.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from detect_sprites import (foreground_mask, components, merge,     # noqa: E402
                           MIN_AREA, MAX_DIM, MERGE_GAP)
from PIL import Image                                              # noqa: E402

SHEET = HERE / "guybrush_source.png"
OUT_JSON = HERE / "sprites.json"


def split_by_columns(boxes, band, gap_needed=2):
    """Split merged boxes into figures using empty vertical columns.

    boxes: merged (x1,y1,x2,y2,area) tuples in band-local coordinates.
    Returns per-figure band-local boxes (x1,y1,x2,y2).
    """
    figures = []
    for (x1, y1, x2, y2, _a) in boxes:
        w, h = x2 - x1 + 1, y2 - y1 + 1
        if w <= 30:                    # already a single figure
            figures.append((x1, y1, x2, y2))
            continue
        occ = [0] * w
        for (bx1, by1, bx2, by2) in column_boxes(x1, y1, x2, y2, band):
            pass
        # occupancy via band mask restricted to this component's bbox
        cols = band["cols"]
        for cx in range(x1, x2 + 1):
            occ[cx - x1] = cols[cx]
        runs, start = [], None
        empty = 0
        for i, o in enumerate(occ):
            if o:
                if start is None:
                    start = i
                empty = 0
            elif start is not None:
                empty += 1
                if empty >= gap_needed:
                    runs.append((start, i - empty))
                    start = None
        if start is not None:
            runs.append((start, len(occ) - 1))
        for (a, b) in runs:
            figures.append((x1 + a, y1, x1 + b, y2))
    return figures


def column_boxes(*_a):
    return []          # unused; kept for clarity of split_by_columns flow


def tight_bbox(mask, x0, y0, x1, y1):
    """Tight box around foreground inside the given box (band-local)."""
    minx, miny, maxx, maxy = None, None, None, None
    for y in range(y0, y1 + 1):
        row = mask[y]
        for x in range(x0, x1 + 1):
            if row[x]:
                if minx is None or x < minx: minx = x
                if maxx is None or x > maxx: maxx = x
                if miny is None or y < miny: miny = y
                if maxy is None or y > maxy: maxy = y
    return (minx, miny, maxx, maxy)


def main():
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    min_area = MIN_AREA
    if "--min-area" in argv:
        min_area = int(argv[argv.index("--min-area") + 1])
    args = []
    skip = False
    for a in argv:
        if skip:
            skip = False
            continue
        if a == "--min-area":
            skip = True
            continue
        if a.startswith("--"):
            continue
        args.append(a)
    if len(args) != 4:
        print(__doc__)
        return 2
    x0, y0, x1, y1 = (int(v) for v in args)

    im = Image.open(SHEET).convert("RGB")
    crop = im.crop((x0, y0, x1, y1))
    mask = foreground_mask(crop)

    raw = components(mask)
    merged = merge(raw, MERGE_GAP)

    # column occupancy per merged component, then split wide ones
    figures = []
    for (bx1, by1, bx2, by2, area) in merged:
        w, h = bx2 - bx1 + 1, by2 - by1 + 1
        if w > 30:
            occ = [0] * w
            for y in range(by1, by2 + 1):
                row = mask[y]
                for x in range(bx1, bx2 + 1):
                    if row[x]:
                        occ[x - bx1] += 1
            # split at columns with LOW occupancy: ground-level dirt gives a
            # column 1-2px tall, a figure fills ~30%+ of the component height
            thr = max(3, int(0.3 * h))
            runs, start = [], None
            for i, o in enumerate(occ):
                if o >= thr:
                    if start is None:
                        start = i
                elif start is not None:
                    runs.append((start, i - 1))
                    start = None
            if start is not None:
                runs.append((start, len(occ) - 1))
            for (a, b) in runs:
                figures.append((bx1 + a, by1, bx1 + b, by2))
        else:
            figures.append((bx1, by1, bx2, by2))

    sprites = json.loads(OUT_JSON.read_text())
    next_id = max(int(s["id"][1:]) for s in sprites) + 1
    added = []
    for (fx1, fy1, fx2, fy2) in figures:
        # row-split each figure: detached fragments from neighbouring rows
        # (e.g. heads below the feet) must not ride inside the box
        occ = [0] * (fy2 - fy1 + 1)
        for y in range(fy1, fy2 + 1):
            row = mask[y]
            for x in range(fx1, fx2 + 1):
                if row[x]:
                    occ[y - fy1] += 1
        segs, start, empty = [], None, 0
        for i, o in enumerate(occ):
            if o:
                if start is None:
                    start = i
                empty = 0
            elif start is not None:
                empty += 1
                if empty >= 2:
                    segs.append((start, i - empty))
                    start = None
        if start is not None:
            segs.append((start, len(occ) - 1))
        for (a, b) in segs:
            t = tight_bbox(mask, fx1, fy1 + a, fx2, fy1 + b)
            if t[0] is None:
                continue
            tx1, ty1, tx2, ty2 = t
            w, h = tx2 - tx1 + 1, ty2 - ty1 + 1
            area = sum(1 for y in range(ty1, ty2 + 1)
                       for x in range(tx1, tx2 + 1) if mask[y][x])
            if area < min_area or w > MAX_DIM or h > MAX_DIM:
                continue
            added.append({"x": x0 + tx1, "y": y0 + ty1, "w": w, "h": h})

    added.sort(key=lambda s: (s["y"], s["x"]))
    for s in added:
        s["id"] = "s%04d" % next_id
        s["row"] = round(s["y"] / 12)
        next_id += 1

    print(f"band ({x0},{y0})-({x1},{y1}): {len(added)} new sprite(s)")
    for s in added:
        print(f'  {s["id"]} x={s["x"]} y={s["y"]} w={s["w"]} h={s["h"]}')
    if not added:
        return 0
    if dry:
        print("(dry run: not written)")
        return 0
    sprites.extend(added)
    OUT_JSON.write_text(json.dumps(sprites, indent=1))
    print(f"appended to {OUT_JSON} (ids never renumbered; total {len(sprites)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())