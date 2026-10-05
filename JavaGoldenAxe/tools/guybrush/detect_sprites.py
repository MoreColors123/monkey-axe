#!/usr/bin/env python3
"""Detect every sprite on the source sheet and write sprites.json.

The MI2 sheet is drawn on a solid green background, so sprites are found with
connected-component analysis. Small detached bits (a hand, a held item) that sit
right next to a bigger blob in the same row are merged back into it.
"""
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SHEET = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "guybrush_source.png"
OUT_JSON = HERE / "sprites.json"
OUT_PREVIEW = HERE / "sprites_overview.png"

BG = np.array([0, 136, 68])
MERGE_GAP = 2      # merge blobs separated by <= this many transparent pixels
MIN_AREA = 90
MAX_DIM = 200


def foreground_mask(im):
    a = np.array(im.convert("RGB")).astype(np.int16)
    return np.abs(a - BG).sum(axis=2) > 45


def components(mask):
    H, W = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        q = deque([(y0, x0)])
        seen[y0, x0] = True
        minx = maxx = x0
        miny = maxy = y0
        area = 0
        while q:
            y, x = q.popleft()
            area += 1
            if x < minx: minx = x
            if x > maxx: maxx = x
            if y < miny: miny = y
            if y > maxy: maxy = y
            for ny, nx in ((y, x - 1), (y, x + 1), (y - 1, x), (y + 1, x)):
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        out.append([minx, miny, maxx, maxy, area])
    return out


def merge(boxes, gap):
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            if boxes[i] is None:
                continue
            for j in range(i + 1, len(boxes)):
                if boxes[j] is None:
                    continue
                a, b = boxes[i], boxes[j]
                vov = min(a[3], b[3]) - max(a[1], b[1])
                if vov < 2:
                    continue
                if a[0] <= b[0]:
                    hgap = b[0] - a[2] - 1
                else:
                    hgap = a[0] - b[2] - 1
                if 0 <= hgap <= gap:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]),
                                max(a[2], b[2]), max(a[3], b[3]),
                                a[4] + b[4]]
                    boxes[j] = None
                    changed = True
        boxes = [b for b in boxes if b is not None]
    return boxes


def main():
    im = Image.open(SHEET).convert("RGB")
    mask = foreground_mask(im)
    raw = components(mask)
    merged = merge(raw, MERGE_GAP)

    sprites = []
    for x1, y1, x2, y2, area in merged:
        w, h = x2 - x1 + 1, y2 - y1 + 1
        if area < MIN_AREA or w > MAX_DIM or h > MAX_DIM:
            continue
        sprites.append({"x": int(x1), "y": int(y1), "w": int(w), "h": int(h)})
    # stable reading-order ids
    sprites.sort(key=lambda s: (round(s["y"] / 12), s["x"]))
    for i, s in enumerate(sprites):
        s["id"] = "s%04d" % i
        s["row"] = round(s["y"] / 12)

    OUT_JSON.write_text(json.dumps(sprites, indent=1))
    print(f"detected {len(sprites)} sprites -> {OUT_JSON}")

    # quick visual check
    scale = 0.5
    prev = im.resize((int(im.width * scale), int(im.height * scale)))
    d = ImageDraw.Draw(prev)
    for s in sprites:
        d.rectangle([s["x"] * scale, s["y"] * scale,
                     (s["x"] + s["w"]) * scale, (s["y"] + s["h"]) * scale],
                    outline=(255, 0, 0))
    prev.save(OUT_PREVIEW)
    print("preview ->", OUT_PREVIEW)


if __name__ == "__main__":
    main()
