#!/usr/bin/env python3
"""Generate mount_editor.html - drag the riding pose onto every beast.

The rider's position on a beast is decided by one thing we control: where the
pose sits inside its own frame rectangle, relative to that rectangle's anchor
(the anchor is what the engine pins to the beast's `mounted_*` point). This
editor shows every beast frame that carries a mount point, with the rider drawn
on it exactly the way the engine will draw it, and lets you drag the pose into
place.

  * drag      move the pose (per rider animation, shared across all beasts)
  * wheel     scale it
  * pose strip  swap the source sprite for that rider animation
  * Save      writes mount_placements.json (the agent applies it to mapping.json
              + the layout rectangles)

Rendering mirrors the engine:
  Resource.java / Animation.addFrame - a `point` attaches to a frame if the
      point lies inside the frame rectangle, stored relative to the sprite
      anchor.
  Sprite.draw - the anchor pixel sits on the actor's world position; a sprite
      authored LEFT drawn as RIGHT is mirrored about the anchor.
  build_atlas.py - how a source sprite is pasted into the frame rectangle.
"""
import base64
import io
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "assets" / "res"
OUT = HERE / "mount_editor.html"

RIDER = "guybrush_threepwood"
LAYOUT = "guybrush_layout.char"
BG = np.array([0, 136, 68])

MOUNT_ANIMS = ["mounted_down", "mounted_down_flip", "mounted_side",
               "mounted_side_flip", "mounted_up", "mounted_up_flip"]

# a spread of plausible riding poses, so the pose can be swapped while placing
POSE_CANDIDATES = ["s0443", "s1126", "s1127", "s1131", "s0408", "s0931",
                   "s0531", "s0812", "s1010", "s0016", "s0216", "s0217",
                   "s0004", "s0008", "s0013", "s0017", "s0021", "s0022"]

sprite_re = re.compile(
    r"^sprite\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")
point_re = re.compile(r"^point\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s*$")
param_re = re.compile(r"^parameter\s+(\S+)\s+(\S+)\s+(\S+)\s*$")


def png_uri(im):
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def key_green(im):
    a = np.array(im).astype(np.int16)
    alpha = np.where(np.abs(a - BG).sum(axis=2) > 45, 255, 0).astype(np.uint8)
    return Image.fromarray(np.dstack([np.array(im), alpha]), "RGBA")


def parse_char(path):
    """-> (frames-by-anim in file order, points, speeds)"""
    anims, order, points, speeds = {}, [], [], {}
    for line in path.read_text(encoding="latin-1").splitlines():
        text = line.strip()
        pm = param_re.match(text)
        if pm:
            if pm.group(2) == "animation_speed":
                speeds[pm.group(1)] = float(pm.group(3))
            continue
        qm = point_re.match(text)
        if qm:
            points.append({"name": qm.group(1), "x": int(qm.group(2)),
                           "y": int(qm.group(3))})
            continue
        m = sprite_re.match(text)
        if not m:
            continue
        anim = m.group(1)
        if anim in ("none", "logo"):
            continue
        if anim not in anims:
            anims[anim] = []
            order.append(anim)
        anims[anim].append({
            "anim": anim, "dir": m.group(2),
            "x": int(m.group(3)), "y": int(m.group(4)),
            "w": int(m.group(5)), "h": int(m.group(6)),
            "cx": int(m.group(7)), "cy": int(m.group(8)),
        })
    return anims, order, points, speeds


def fit_scale(spr_w, spr_h, w, h, cx, cy, mode, base, hip, hip_x):
    if mode == "place":
        return base
    if mode == "hip":
        return max(min(base, cy / max(1e-6, hip * spr_h),
                       (h - cy) / max(1e-6, (1.0 - hip) * spr_h)), 0.1)
    if mode == "center" or cy <= 0:
        return max(min(base, h / spr_h, w / spr_w), 0.1)
    return max(min(base, cy / spr_h), 0.1)


def placement_offset(mode, rect, nw, nh, hip, hip_x):
    """art top-left relative to the frame's anchor pixel"""
    _x, _y, _w, h, cx, cy = rect
    if mode == "hip":
        return cx - round(hip_x * nw), cy - round(hip * nh)
    if mode == "center":
        return cx - nw // 2, (h - nh) // 2
    return cx - nw // 2, cy - nh


def main():
    sprites = {s["id"]: s for s in json.loads((HERE / "sprites.json").read_text())}
    mapping = json.loads((HERE / "mapping.json").read_text())
    global_scale = mapping.get("global_scale", 1.15)

    # --- beasts: every character with a mounted_* point ---------------------
    beasts = []
    for char in sorted((ROOT / "chars").glob("*.char")):
        if char.name.startswith(LAYOUT[:6]):
            continue
        anims, order, points, speeds = parse_char(char)
        if not any(p["name"].startswith("mounted_") for p in points):
            continue
        cells_by_anim = {}
        for anim in order:
            for idx, fr in enumerate(anims[anim]):
                for p in points:
                    inside = (fr["x"] <= p["x"] < fr["x"] + fr["w"]
                              and fr["y"] <= p["y"] < fr["y"] + fr["h"])
                    if not inside:
                        continue
                    rel_x = p["x"] - fr["x"] - fr["cx"]
                    rel_y = p["y"] - fr["y"] - fr["cy"]
                    # the sheet is authored LEFT, we render RIGHT -> mirrored
                    mirrored = fr["dir"] != "RIGHT"
                    cells_by_anim.setdefault(p["name"], {})
                    key = (fr["x"], fr["y"], fr["w"], fr["h"])
                    if key in cells_by_anim[p["name"]]:
                        continue
                    cells_by_anim[p["name"]][key] = {
                        "anim": anim, "idx": idx,
                        "x": fr["x"], "y": fr["y"], "w": fr["w"], "h": fr["h"],
                        "cx": fr["cx"], "cy": fr["cy"],
                        "mirrored": mirrored,
                        "px": -rel_x if mirrored else rel_x, "py": rel_y,
                    }
        groups = []
        for name in MOUNT_ANIMS:
            if name not in cells_by_anim:
                continue
            cells = list(cells_by_anim[name].values())
            groups.append({"riderAnim": name, "cells": cells[:8],
                           "extra": max(0, len(cells) - 8)})
        if groups:
            beasts.append({
                "id": char.stem,
                "sheet": png_uri(Image.open(ROOT / "image" / f"{char.stem}.png").convert("RGBA")),
                "groups": groups,
            })

    # --- rider: layout rects + initial placement per mount animation --------
    rects_by_anim = {}
    for line in (ROOT / "chars" / LAYOUT).read_text(encoding="latin-1").splitlines():
        m = sprite_re.match(line.strip())
        if m and m.group(1) in MOUNT_ANIMS:
            rects_by_anim.setdefault(m.group(1), []).append({
                "x": int(m.group(3)), "y": int(m.group(4)), "w": int(m.group(5)),
                "h": int(m.group(6)), "cx": int(m.group(7)), "cy": int(m.group(8)),
            })

    placements = {}
    for anim in MOUNT_ANIMS:
        entry = mapping["animations"].get(anim)
        rects = rects_by_anim.get(anim)
        if not entry or not rects:
            continue
        mode = entry.get("mode", "bottom")
        base = entry.get("scale", global_scale)
        hip = entry.get("hip", 0.6)
        hip_x = entry.get("hip_x", 0.5)
        ids = entry.get("frames") or ["s0004"]
        sc = fit_scale(sprites[ids[0]]["w"], sprites[ids[0]]["h"],
                       rects[0]["w"], rects[0]["h"], rects[0]["cx"], rects[0]["cy"],
                       mode, base, hip, hip_x)
        nw = max(1, round(sprites[ids[0]]["w"] * sc))
        nh = max(1, round(sprites[ids[0]]["h"] * sc))
        if mode == "place" and entry.get("offset"):
            dx, dy = entry["offset"]
        else:
            dx, dy = placement_offset(
                mode, (rects[0]["x"], rects[0]["y"], rects[0]["w"],
                       rects[0]["h"], rects[0]["cx"], rects[0]["cy"]),
                nw, nh, hip, hip_x)
        placements[anim] = {"pose": ids[0], "scale": round(sc, 3),
                            "dx": int(dx), "dy": int(dy), "mode": mode,
                            "flip": bool(entry.get("flip", False))}

    # --- pose candidates (pre-keyed, like the reviewer does) ---------------
    src = Image.open(HERE / "guybrush_source.png").convert("RGB")
    poses, wanted = {}, set(POSE_CANDIDATES) | {p["pose"] for p in placements.values()}
    for sid in wanted:
        s = sprites.get(sid)
        if not s:
            continue
        tile = key_green(src.crop((s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"])))
        poses[sid] = {"id": sid, "w": s["w"], "h": s["h"], "row": s["row"],
                      "src": png_uri(tile)}

    data = {
        "beasts": beasts,
        "rider": {"rects": rects_by_anim, "poses": poses,
                  "placements": placements, "dir": "RIGHT"},
        "mountAnims": MOUNT_ANIMS,
        "candidates": [p for p in POSE_CANDIDATES if p in poses],
    }

    html = TEMPLATE.replace("/*__DATA__*/", "const DATA = " + json.dumps(data) + ";")
    OUT.write_text(html, encoding="utf-8")
    print("wrote", OUT)
    print("beasts:", [(b["id"], sum(len(g["cells"]) for g in b["groups"])) for b in beasts])
    print("placements:", json.dumps(placements, indent=1))


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Guybrush mount editor</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; background:#1e2624; color:#e8eeea;
         font:13px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; }
  header { position:sticky; top:0; z-index:5; background:#16201d;
           border-bottom:1px solid #2f3b37; padding:10px 14px; }
  h1 { font-size:15px; margin:0 0 6px; }
  .bar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  button { background:#2a3733; color:#e8eeea; border:1px solid #3d4c47;
           border-radius:5px; padding:5px 10px; cursor:pointer; }
  button:hover { background:#35443f; }
  button.primary { background:#2f6b4f; border-color:#3e8a66; }
  .hint { color:#9fb0aa; font-size:12px; }
  .warn { color:#ffc46b; }
  .ok { color:#8fe0b0; }
  section { margin:16px 0 4px; border-top:1px solid #2f3b37; padding-top:10px; }
  h2 { font-size:13px; margin:0 0 8px; text-transform:uppercase;
       letter-spacing:.06em; color:#9fd0ff; }
  h3 { font-size:12px; margin:10px 0 6px; color:#c9d6d1; }
  .row { display:flex; gap:10px; overflow-x:auto; padding-bottom:6px; }
  .cellwrap { text-align:center; }
  .cellwrap .cap { font-size:11px; color:#9fb0aa; margin-top:2px; }
  canvas { background:#16201d; border:1px solid #2f3b37; border-radius:4px;
           cursor:grab; display:block; }
  .readout { font-family:ui-monospace,Consolas,monospace; font-size:11px;
             color:#ffd98a; }
  .poses { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
  .posebtn { background:#22302c; border:2px solid transparent; border-radius:4px;
             padding:2px; cursor:pointer; }
  .posebtn.sel { border-color:#8fe0b0; }
  .posebtn img { display:block; image-rendering:pixelated; }
  .legend { color:#9fb0aa; font-size:11px; }
</style>
</head>
<body>
<header>
  <h1>Guybrush mount editor</h1>
  <div class="bar">
    <button class="primary" id="save">Save placements</button>
    <button id="reset">Reset</button>
    <span class="hint">drag = move &nbsp;·&nbsp; wheel = scale &nbsp;·&nbsp; click a pose to swap it</span>
    <span id="status" class="hint"></span>
  </div>
  <div class="bar" id="nav"></div>
  <div class="hint" id="needs"></div>
</header>
<div id="body"></div>
<script>
/*__DATA__*/

const Z = 4;                 // preview zoom
const CELL = { w: 200 * Z / 2, h: 190 * Z / 2 };
const ANCHOR = { x: CELL.w * 0.5, y: CELL.h * 0.72 };
const images = new Map();    // src -> Image
let placements = JSON.parse(JSON.stringify(DATA.rider.placements));
let active = null;           // last touched riderAnim

function getImg(src) {
  let im = images.get(src);
  if (!im) {
    im = new Image();
    im.onload = () => renderAll();
    im.src = src;
    images.set(src, im);
  }
  return im;
}

function poseFor(anim) {
  const p = placements[anim];
  if (!p) return null;
  const pose = DATA.rider.poses[p.pose];
  return pose ? { pose, scale: p.scale, dx: p.dx, dy: p.dy, flip: !!p.flip } : null;
}

function drawCell(cv, beast, cell) {
  const g = cv.getContext('2d');
  g.imageSmoothingEnabled = false;
  g.clearRect(0, 0, cv.width, cv.height);

  // --- beast frame: anchor pixel at ANCHOR, mirrored if authored LEFT ----
  const sheet = getImg(beast.sheet);
  const O = ANCHOR;
  if (sheet.complete && sheet.naturalWidth) {
    g.save();
    g.translate(O.x, O.y);
    if (cell.mirrored) {
      g.scale(-1, 1);
      g.drawImage(sheet, cell.x, cell.y, cell.w, cell.h,
                  -cell.cx, -cell.cy, cell.w, cell.h);
    } else {
      g.drawImage(sheet, cell.x, cell.y, cell.w, cell.h,
                  -cell.cx, -cell.cy, cell.w, cell.h);
    }
    g.restore();
  }

  // --- mount point (what the engine pins the rider's anchor to) -----------
  const M = { x: O.x + cell.px, y: O.y + cell.py };
  g.strokeStyle = 'rgba(255,90,90,.85)';
  g.lineWidth = 1;
  g.beginPath();
  g.moveTo(M.x - 6, M.y); g.lineTo(M.x + 6, M.y);
  g.moveTo(M.x, M.y - 6); g.lineTo(M.x, M.y + 6);
  g.stroke();

  // --- rider -------------------------------------------------------------
  const p = poseFor(cell.riderAnim);
  if (!p) return;
  const img = getImg(p.pose.src);
  const w = Math.round(p.pose.w * p.scale), h = Math.round(p.pose.h * p.scale);
  if (!img.complete || !img.naturalWidth) return;
  const ax = M.x + (p.flip ? -p.dx - w : p.dx), ay = M.y + p.dy;
  if (p.flip) {
    // mirror about the anchor, exactly like the baker does
    g.save();
    g.translate(M.x, M.y);
    g.scale(-1, 1);
    g.drawImage(img, 0, 0, p.pose.w, p.pose.h, p.dx, p.dy, w, h);
    g.restore();
  } else {
    g.drawImage(img, 0, 0, p.pose.w, p.pose.h, ax, ay, w, h);
  }

  // current frame rectangle (grey) + the rectangle this needs (dashed green)
  const rects = DATA.rider.rects[cell.riderAnim] || [];
  const r = rects[0];
  if (r) {
    g.strokeStyle = 'rgba(140,160,180,.45)';
    g.setLineDash([4, 3]);
    g.strokeRect(M.x - r.cx + .5, M.y - r.cy + .5, r.w, r.h);
    const need = neededRect(p, cell.riderAnim);
    g.strokeStyle = need.fits ? 'rgba(140,200,160,.5)' : 'rgba(255,196,107,.8)';
    g.strokeRect(M.x + need.x + .5, M.y + need.y + .5, need.w, need.h);
    g.setLineDash([]);
  }
}

function neededRect(p, anim) {
  const w = Math.ceil(p.pose.w * p.scale), h = Math.ceil(p.pose.h * p.scale);
  const m = 1;
  const left = p.flip ? -(p.dx + w) : p.dx;      // art box relative to the anchor
  const acx = Math.max(0, -left) + m, acy = Math.max(0, -p.dy) + m;
  const rects = DATA.rider.rects[anim] || [];
  const r = rects[0];
  const w2 = acx + left + w + m, h2 = acy + p.dy + h + m;
  const fits = r && w2 <= r.w && h2 <= r.h;
  return { x: -acx, y: -acy, w: w2, h: h2, fits: !!fits,
           acx: acx, acy: acy };
}

function renderNeeds() {
  const lines = [];
  for (const anim of Object.keys(placements)) {
    const p = poseFor(anim);
    if (!p) continue;
    const need = neededRect(p, anim);
    const r = (DATA.rider.rects[anim] || [])[0];
    lines.push(`${anim}: pose ${p.pose.id} ${p.pose.w}x${p.pose.h} scale ${p.scale.toFixed(2)} `
      + `offset (${p.dx},${p.dy})${p.flip ? ' MIRRORED' : ''} &rarr; needs rect ${need.w}x${need.h} `
      + `anchor ${need.acx},${need.acy}`
      + (r ? (need.fits ? ' <span class="ok">(fits)</span>'
                        : ` <span class="warn">(current rect ${r.w}x${r.h} - will be resized)</span>`) : ''));
  }
  document.getElementById('needs').innerHTML = lines.join('<br>');
}

function renderAll() {
  document.querySelectorAll('canvas').forEach(cv => {
    const beast = DATA.beasts.find(b => b.id === cv.dataset.beast);
    const group = beast.groups.find(gr => gr.riderAnim === cv.dataset.anim);
    const cell = group.cells[+cv.dataset.idx];
    if (cell) drawCell(cv, beast, Object.assign({ riderAnim: cv.dataset.anim }, cell));
  });
  renderNeeds();
}

function build() {
  const body = document.getElementById('body');
  body.innerHTML = '';
  for (const beast of DATA.beasts) {
    const sec = document.createElement('section');
    sec.id = 'beast-' + beast.id;
    sec.innerHTML = `<h2>${beast.id}</h2>`;
    for (const group of beast.groups) {
      const wrap = document.createElement('div');
      const head = document.createElement('h3');
      head.innerHTML = `rider animation <b>${group.riderAnim}</b>`
        + ` <span class="readout" data-out="${group.riderAnim}"></span>`;
      wrap.appendChild(head);

      const poses = document.createElement('div');
      poses.className = 'poses';
      const flip = document.createElement('button');
      flip.dataset.flipFor = group.riderAnim;
      flip.title = 'mirror the pose about the mount point (used by the *_flip animations, '
                 + 'because those beast frames are drawn mirrored)';
      flip.onclick = () => {
        const p = placements[group.riderAnim];
        p.flip = !p.flip;
        active = group.riderAnim;
        refresh();
      };
      poses.appendChild(flip);
      const strip = DATA.candidates.concat(
        Object.keys(DATA.rider.poses).filter(id => !DATA.candidates.includes(id)));
      for (const id of strip) {
        const pose = DATA.rider.poses[id];
        const b = document.createElement('button');
        b.className = 'posebtn' + (placements[group.riderAnim]
                                   && placements[group.riderAnim].pose === id ? ' sel' : '');
        b.dataset.anim = group.riderAnim; b.dataset.pose = id;
        b.title = `${id} (${pose.w}x${pose.h}, sheet row ${pose.row})`;
        const scaleTo = 40 / Math.max(pose.w, pose.h);
        b.innerHTML = `<img width="${Math.round(pose.w * scaleTo)}"
                            height="${Math.round(pose.h * scaleTo)}" src="${pose.src}">`;
        b.onclick = () => {
          placements[group.riderAnim].pose = id;
          document.querySelectorAll(`.posebtn[data-anim="${group.riderAnim}"]`)
                  .forEach(el => el.classList.toggle('sel', el.dataset.pose === id));
          refresh();
        };
        poses.appendChild(b);
      }
      wrap.appendChild(poses);

      const row = document.createElement('div');
      row.className = 'row';
      group.cells.forEach((cell, i) => {
        const cw = document.createElement('div');
        cw.className = 'cellwrap';
        const cv = document.createElement('canvas');
        cv.width = CELL.w; cv.height = CELL.h;
        cv.dataset.beast = beast.id; cv.dataset.anim = group.riderAnim;
        cv.dataset.idx = i;
        attachDrag(cv, group.riderAnim);
        cw.appendChild(cv);
        cw.insertAdjacentHTML('beforeend',
          `<div class="cap">${cell.anim}[${cell.idx}]</div>`);
        row.appendChild(cw);
      });
      if (group.extra) {
        row.insertAdjacentHTML('beforeend',
          `<div class="cellwrap"><div class="cap">+${group.extra} more<br>frames<br>(same placement)</div></div>`);
      }
      wrap.appendChild(row);
      sec.appendChild(wrap);
    }
    body.appendChild(sec);
  }
  const nav = document.getElementById('nav');
  nav.innerHTML = '<span class="hint">jump to:</span>';
  for (const beast of DATA.beasts) {
    const b = document.createElement('button');
    b.textContent = beast.id;
    b.onclick = () => document.getElementById('beast-' + beast.id)
                            .scrollIntoView({ behavior: 'smooth', block: 'start' });
    nav.appendChild(b);
  }
  renderAll();
}

function refresh() { renderAll(); updateOut(); }

function updateOut() {
  document.querySelectorAll('[data-out]').forEach(el => {
    const p = placements[el.dataset.out];
    if (!p) return;
    el.textContent = `offset (${p.dx},${p.dy})  scale ${p.scale.toFixed(2)}  `
      + `pose ${p.pose}${p.flip ? '  MIRRORED' : ''}`;
  });
  document.querySelectorAll('[data-flip-for]').forEach(el => {
    const p = placements[el.dataset.flipFor];
    const on = p && p.flip;
    el.textContent = on ? '⇄ mirrored' : '⇄ mirror';
    el.className = on ? 'primary' : '';
  });
}

function attachDrag(cv, anim) {
  let dragging = false, sx = 0, sy = 0, ox = 0, oy = 0;
  cv.addEventListener('mousedown', e => {
    dragging = true; cv.style.cursor = 'grabbing';
    sx = e.clientX; sy = e.clientY;
    ox = placements[anim].dx; oy = placements[anim].dy;
    active = anim;
    e.preventDefault();
  });
  window.addEventListener('mousemove', e => {
    if (!dragging) return;
    placements[anim].dx = ox + (e.clientX - sx);   // canvas is 1:1 world px
    placements[anim].dy = oy + (e.clientY - sy);
    refresh();
  });
  window.addEventListener('mouseup', () => {
    dragging = false; cv.style.cursor = 'grab';
  });
  cv.addEventListener('wheel', e => {
    e.preventDefault();
    const p = placements[anim];
    p.scale = Math.max(0.2, Math.min(3, +(p.scale + (e.deltaY < 0 ? 0.05 : -0.05)).toFixed(3)));
    active = anim;
    refresh();
  }, { passive: false });
}

// arrow-key nudge for the last touched animation (one listener, not one per cell)
window.addEventListener('keydown', e => {
  if (!active || !e.key.startsWith('Arrow')) return;
  const p = placements[active];
  const step = e.shiftKey ? 4 : 1;
  if (e.key === 'ArrowLeft') p.dx -= step;
  if (e.key === 'ArrowRight') p.dx += step;
  if (e.key === 'ArrowUp') p.dy -= step;
  if (e.key === 'ArrowDown') p.dy += step;
  e.preventDefault();
  refresh();
});

document.getElementById('save').onclick = async () => {
  const status = document.getElementById('status');
  try {
    const res = await fetch('/api/mount', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ placements }),
    });
    status.textContent = res.ok ? 'saved mount_placements.json'
                                : 'save failed: ' + await res.text();
    status.className = res.ok ? 'hint ok' : 'hint warn';
  } catch (err) {
    status.textContent = 'no server - copy the JSON below';
    status.className = 'hint warn';
    console.log(JSON.stringify({ placements }, null, 1));
    prompt('placements JSON (copy me):', JSON.stringify(placements));
  }
};

document.getElementById('reset').onclick = () => {
  placements = JSON.parse(JSON.stringify(DATA.rider.placements));
  build();
};

build();
updateOut();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
