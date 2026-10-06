#!/usr/bin/env python3
"""Generate reviewer.html - a self-contained visual mapping editor.

Open the file in any browser (double-click, no server needed). Click sprites on
the sheet to pick them, assign them to Golden Axe animations, watch the live
filmstrip preview, then Export mapping.json and rerun build_atlas.py.
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
OUT = HERE / "reviewer.html"

sprite_re = re.compile(
    r"^sprite\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")


param_re = re.compile(r"^parameter\s+(\S+)\s+(\S+)\s+(\S+)\s*$")


def parse_char(char_name):
    """Parse a character .char into frames + per-animation speed/loop.

    Returns (animation order, frames-by-animation, speed, loop). `order` and the
    frame lists are in file order, which is what the baker and reviewer both use.
    """
    anims = {}
    order = []
    speeds = {}
    loops = {}
    with open(ROOT / "chars" / char_name, encoding="latin-1") as f:
        for line in f:
            text = line.strip()
            pm = param_re.match(text)
            if pm:
                a, k, v = pm.group(1), pm.group(2), pm.group(3)
                if k == "animation_speed":
                    speeds[a] = float(v)
                elif k == "animation_loop":
                    loops[a] = (v.lower() == "true")
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
                "x": int(m.group(3)), "y": int(m.group(4)),
                "w": int(m.group(5)), "h": int(m.group(6)),
                "cx": int(m.group(7)), "cy": int(m.group(8)),
            })
    return order, anims, speeds, loops


def main():
    sprites = json.loads((HERE / "sprites.json").read_text())
    mapping = json.loads((HERE / "mapping.json").read_text())
    # Proposed mappings written by the agent (suggestions.json): shown in the
    # Suggestions bar with approve/dismiss/comment controls.
    sugg_path = HERE / "suggestions.json"
    suggestions = (json.loads(sugg_path.read_text())
                   if sugg_path.exists() else {"suggestions": []})
    order, ga, speeds, loops = parse_char("guybrush_threepwood.char")
    # The vanilla layout, for the original (Ax) preview. If the layout has been
    # de-shared, the new rectangles do not exist in ax_battler.png, so the
    # original preview must use the original coordinates.
    _, orig_ga, _, _ = parse_char("ax_battler.char")

    # Pre-key the green background out here in Python and embed a ready-made
    # transparent PNG. Doing it in-browser needs canvas getImageData(), which
    # Brave's fingerprinting protection can blank/randomise.
    src = Image.open(HERE / "guybrush_source.png").convert("RGB")
    arr = np.array(src).astype(np.int16)
    alpha = np.where(np.abs(arr - np.array([0, 136, 68])).sum(axis=2) > 45,
                     255, 0).astype(np.uint8)
    rgba = Image.fromarray(np.dstack([np.array(src), alpha]), "RGBA")
    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    sheet_b64 = base64.b64encode(buf.getvalue()).decode()

    # Original Ax Battler sheet, so the reviewer can play the vanilla animation
    # beside the new one. The frame rectangles in the .char are the same layout,
    # so DATA.ga is valid for both images.
    orig_b64 = base64.b64encode(
        (ROOT / "image" / "ax_battler.png").read_bytes()).decode()

    data = {
        "sheet": "data:image/png;base64," + sheet_b64,
        "origSheet": "data:image/png;base64," + orig_b64,
        "sprites": sprites,
        "mapping": mapping,
        "animOrder": order,
        "ga": ga,
        "origGa": orig_ga,
        "speed": speeds,
        "loop": loops,
        "suggestions": suggestions,
    }

    html = TEMPLATE.replace("/*__DATA__*/", "const DATA = " + json.dumps(data) + ";")
    OUT.write_text(html, encoding="utf-8")
    print("wrote", OUT, f"({OUT.stat().st_size // 1024} KB)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Guybrush sprite mapper</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font:13px/1.4 system-ui,Segoe UI,sans-serif; background:#1b1e23; color:#e6e6e6; }
  #top { display:flex; gap:10px; align-items:center; padding:8px 12px; background:#12141a; border-bottom:1px solid #333; flex-wrap:wrap; }
  #top h1 { font-size:15px; margin:0 12px 0 0; }
  button, select, input[type=number] { background:#2a2f3a; color:#e6e6e6; border:1px solid #454b58; border-radius:5px; padding:4px 8px; cursor:pointer; }
  button:hover { background:#39404e; }
  button.primary { background:#2f6f3e; border-color:#3f8f52; }
  #main { display:flex; height:calc(100vh - 46px); }
  #left { flex:1 1 auto; min-width:0; display:flex; flex-direction:column; }
  #splitter { flex:0 0 7px; cursor:col-resize; background:#12141a; border-left:1px solid #333; border-right:1px solid #333; }
  #splitter:hover { background:#3a4b8a; }
  #sheetwrap { flex:1 1 auto; position:relative; overflow:hidden; background:#0c0e12; }
  #sheet { position:absolute; inset:0; width:100%; height:100%; }
  #sheetinfo { padding:5px 10px; background:#12141a; border-top:1px solid #333; font-family:monospace; white-space:nowrap; overflow:hidden; }
  #right { width:430px; flex:0 0 430px; display:flex; flex-direction:column; }
  #animlist { border-bottom:1px solid #333; padding:6px; }
  details.rectbar { border-bottom:1px solid #333; background:#101319; }
  details.rectbar > summary { cursor:pointer; padding:6px 8px; color:#adf; }
  details.rectbar > summary .hint { color:#98a; margin-left:8px; }
  #rectbarwrap { max-height:38vh; overflow:auto; padding:0 8px 6px; }
  .prevbox { display:inline-block; text-align:center; }
  .prevbox canvas { background:#0c0e12; border:1px solid #333; border-radius:5px; image-rendering:pixelated; }
  #helpbody { max-width:760px; line-height:1.55; }
  #helpbody h3 { color:#adf; margin:16px 0 4px; font-size:14px; }
  #helpbody p { margin:6px 0; }
  #helpbody code { color:#ffd84a; font-family:monospace; }
  .helpkey { border:1px solid #333; border-radius:5px; padding:8px 12px; background:#161920; margin:12px 0; }
  .helpkey kbd { color:#fff; background:#2a2f3a; border:1px solid #454b58; border-radius:4px; padding:0 5px; font-family:monospace; }
  #toast { position:fixed; left:50%; bottom:18px; transform:translateX(-50%); background:#2f6f3e; color:#fff; padding:8px 16px; border-radius:6px; display:none; z-index:80; box-shadow:0 2px 10px #0008; }
  .anim { display:inline-block; margin:2px; padding:3px 7px; border:1px solid #444; border-radius:5px; cursor:pointer; font-size:12px; }
  .anim.active { background:#3a4b8a; border-color:#6f87e0; }
  .anim .n { color:#9fd; }
  .anim .mod { color:#ffd84a; }
  #editor { flex:1 1 auto; overflow:auto; padding:10px; }
  #film { background:#0c0e12; border:1px solid #333; border-radius:5px; width:100%; }
  #animprev { background:#0c0e12; border:1px solid #333; border-radius:5px; image-rendering:pixelated; }
  .framebar { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }
  .fbox { border:1px solid #444; border-radius:5px; padding:2px; text-align:center; background:#22262e; }
  .fbox.sel { border-color:#ffea00; }
  .fbox canvas { display:block; image-rendering:pixelated; background:#0c0e12; }
  .fbox .c { display:flex; gap:2px; margin-top:2px; }
  .fbox .c button { padding:1px 4px; font-size:11px; }
  .row { margin:8px 0; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  #out { width:100%; height:120px; background:#0c0e12; color:#bfe; border:1px solid #333; border-radius:5px; font-family:monospace; font-size:11px; }
  #overlay, #helpoverlay { position:fixed; inset:0; background:#0c0e12; z-index:50; overflow:auto; display:none; padding:14px; }
  #overlay h2, #helpoverlay h2 { margin-top:0; }
  #helpoverlay { z-index:60; padding:18px; }
  .hint { color:#98a; font-size:12px; }
  .sechead { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:#8fa6d8;
             background:#12141a; border-bottom:1px solid #333; padding:4px 8px; font-weight:600; }
  .sechead .hint { text-transform:none; letter-spacing:0; font-weight:400; }
  table.recttable { border-collapse:collapse; width:100%; font-size:12px; }
  table.recttable th, table.recttable td { border:1px solid #333; padding:3px 6px; text-align:left; vertical-align:middle; }
  table.recttable th { background:#12141a; position:sticky; top:0; }
  table.recttable tr.cur { background:#1d2740; }
  table.recttable tr.shared td:first-child { color:#ffb44a; }
  table.recttable tr.borrowed { outline:2px solid #ff9d2e; outline-offset:-2px; }
  table.recttable td.mono { font-family:monospace; }
  table.recttable button { padding:1px 6px; font-size:11px; margin-right:3px; }
  #suggbarwrap { max-height:60vh; overflow:auto; padding:8px; }
  .sugg { border:1px solid #3a4050; border-radius:6px; padding:8px; margin:8px 0; background:#161920; }
  .sugg.approved { opacity:.8; border-color:#2f6f3e; }
  .sugg.dismissed { opacity:.55; border-color:#555; }
  .sugg .st { font-size:11px; padding:1px 7px; border-radius:8px; margin-left:8px; color:#fff; }
  .sugg .st.proposed { background:#2a4b8a; }
  .sugg .st.approved { background:#2f6f3e; }
  .sugg .st.dismissed { background:#555; }
  .sugg .strip { display:flex; flex-wrap:wrap; gap:4px; margin:5px 0; }
  .sugg .strip .t { text-align:center; font-family:monospace; font-size:10px; color:#9ab; background:#22262e; border:1px solid #444; border-radius:4px; padding:2px; cursor:pointer; }
  .sugg .strip .t:hover { border-color:#ffea00; }
  .sugg .curhint { color:#98a; font-size:11px; margin-top:6px; }
  .sugg textarea { width:100%; background:#0c0e12; color:#bfe; border:1px solid #333; border-radius:5px; font-family:monospace; font-size:11px; margin-top:6px; }
  .legend span { display:inline-block; margin-right:14px; }
  .swatch { display:inline-block; width:11px; height:11px; vertical-align:-1px; border:1px solid #555; }
  #err { display:none; background:#7a2020; color:#fff; padding:6px 12px; font-family:monospace; white-space:pre-wrap; }
</style>
</head>
<body>
<div id="top">
  <h1>Guybrush sprite mapper</h1>
  <button id="helpbtn" title="Open the help window">Help</button>
  <span style="flex:1"></span>
  <label title="Base size for every animation without a per-animation scale. 1.0 = 100%, 1.15 = 15% larger.">global scale <input id="gscale" type="number" step="0.05" style="width:70px"></label>
  <button id="rects" title="Show/hide the Rectangles section">Rectangles</button>
  <button id="undo" title="Undo the last change (Ctrl+Z)">Undo</button>
  <button id="redo" title="Redo the last undone change (Ctrl+Y)">Redo</button>
  <button id="resetall" title="Restore every section to the last exported state">Reset all</button>
  <label class="hint">Load mapping <input id="load" type="file" accept=".json" style="width:150px"></label>
  <button id="export" class="primary">Export mapping.json</button>
  <span id="savestatus" class="hint"></span>
</div>
<div id="err"></div>
<div id="main">
  <div id="left">
    <div class="sechead">Sheet</div>
    <div id="sheetwrap"><canvas id="sheet"></canvas></div>
    <div id="sheetinfo">no sprite selected</div>
  </div>
  <div id="splitter" title="Drag to resize the right panel; double-click to reset"></div>
  <div id="right">
    <div class="sechead">Animations</div>
    <div id="animlist"></div>
    <details class="rectbar" id="rectsbar" open>
      <summary>Rectangles <span id="rectcount" class="hint"></span></summary>
      <div id="rectbarwrap">
        <div class="legend hint">
          <label><input id="rectsonlycur" type="checkbox" checked> only rectangles used by the current animation</label>
          <span id="rectselinfo" style="margin-left:12px"></span>
        </div>
        <div id="rectsbody"></div>
      </div>
    </details>
    <details class="rectbar" id="suggbar" open>
      <summary>Suggestions <span id="suggcount" class="hint"></span></summary>
      <div id="suggbarwrap">
        <div id="suggbody"></div>
      </div>
    </details>
    <div id="editor">
      <div class="sechead">Animation settings</div>
      <div class="row">
        <b id="animname"></b>
        <button id="resetsection" title="Restore this section to the last exported state">Reset section</button>
        <label title="bottom = feet stand on the frame's anchor (cy); center = art is fitted and centred, ignoring the anchor.">mode
          <select id="mode"><option value="bottom">bottom</option><option value="center">center</option></select>
        </label>
        <label title="Optional size multiplier for THIS animation only. Blank = use the global scale.">scale
          <input id="ascale" type="number" step="0.05" placeholder="global" style="width:80px">
        </label>
      </div>
      <div class="sechead">Preview</div>
      <div class="row" style="align-items:flex-start">
        <div class="prevbox"><div class="hint">original (Ax)</div><canvas id="origprev" width="180" height="150"></canvas></div>
        <div class="prevbox"><div class="hint">new (Guybrush)</div><canvas id="animprev" width="180" height="150"></canvas></div>
        <div>
          <div><button id="play">Pause</button> <button id="replay">Replay</button> <label title="Preview playback speed in frames per second. Defaults to the animation's real speed.">fps <input id="fps" type="number" step="0.5" style="width:70px"></label></div>
          <div class="row" style="margin:4px 0"><label title="Repeat one-shot animations while reviewing; off = hold the last frame like in game."><input id="forceloop" type="checkbox" checked> loop preview</label></div>
          <div class="hint" id="animmeta"></div>
        </div>
      </div>
      <div class="sechead">Baked frames</div>
      <canvas id="film" height="110"></canvas>
      <div class="sechead">Frame list <span class="hint">the source sprites this animation plays</span></div>
      <div class="row">
        <button id="append">+ append selected sprite</button>
        <button id="onlysel">replace frames with selected</button>
        <button id="clear">clear frames</button>
        <span class="hint" id="count"></span>
      </div>
      <div class="framebar" id="framebar"></div>
      <div class="hint">Click a frame thumbnail to set it to the selected sprite. Use the arrows to reorder.</div>
    </div>
  </div>
</div>
<div id="helpoverlay">
  <h2>Help <button id="closehelp">close</button></h2>
  <div id="helpbody">
    <p class="helpkey">
      <b>Colour key:</b>
      <span style="color:#adf">blue headings</span> group the topics;
      <code>gold monospace</code> is a field, value or file you can edit
      (e.g. <code>cy</code>, <code>scale</code>, <code>rect_overrides</code>);
      <span style="color:#ffb44a">orange</span> marks frames or rectangles that are
      borrowed or extra.
    </p>

    <h3>mode — bottom (feet on ground)</h3>
    <p>The whole animation is drawn at one size and each frame's feet sit on its anchor,
       <code>cy</code> (the anchor's y inside the frame). Use it for poses that stand: idle,
       walking, running, attacks, jumping.</p>

    <h3>mode — center (lying / airborne)</h3>
    <p>The sprite is fitted and vertically centred inside the frame, ignoring
       <code>cy</code>. Use it for lying or tumbling poses: <code>thrown</code>,
       <code>knock_down</code>, <code>dying</code>, <code>dead</code>, <code>resting</code>.</p>

    <h3>scale (per animation)</h3>
    <p>An optional size multiplier for the selected animation only. Leave it blank to use the
       global scale. <code>1.0</code> = 100%, <code>1.15</code> = 15% larger. Raise it if one
       animation looks too small, lower it if it clips.</p>

    <h3>global scale</h3>
    <p>The base size for every animation that has no per-animation scale. Tuned so Guybrush
       matches Ax's height (currently <code>1.15</code>). Change it to grow or shrink the whole
       character at once.</p>

    <h3>frames, filmstrip and preview</h3>
    <p>The filmstrip and both previews show <b>every sprite in the current animation's frame
       list</b>, even when the game layout has fewer frames. Those extra frames are drawn in
       <span style="color:#ffb44a">orange</span> and labelled <code>(extra)</code>: they show
       what you are building, but they only bake into the game once the layout has a rectangle
       for each frame.</p>

    <h3>Rectangles</h3>
    <p>The atlas is one image with a fixed slot per rectangle, and the game layout reuses
       rectangles between animations, so a rectangle can hold only <b>one</b> sprite. The first
       animation in layout order that uses a rectangle <b>owns</b> it; any other animation that
       draws it reuses the owner's sprite and its own choice is ignored (shown as
       <span style="color:#ff9d2e">borrowed</span>).</p>
    <p>The <b>Rectangles</b> bar under the animation list shows every rectangle with its owner
       and the sprite it currently bakes. To force one: select a sprite on the sheet, then press
       <b>Set</b> on a rectangle. That is stored as <code>rect_overrides</code> in
       <code>mapping.json</code>; <b>Clear</b> removes it.</p>
    <p>After running <code>deshare.py</code> no rectangle is shared, so each animation owns its
       own and overrides are rarely needed.</p>

    <h3>Suggestions</h3>
    <p>Proposed mappings (written to <code>suggestions.json</code> by the agent) appear in the
       <b>Suggestions</b> bar: the proposed frame strip next to the animation's current frames.
       <b>Approve</b> applies the proposal to the page (then <b>Export mapping.json</b> keeps it);
       <b>Dismiss</b> rejects it; <b>Reopen</b> re-opens a handled one. The comment box is saved
       back to <code>suggestions.json</code> for the agent to read - as are the statuses, which
       survive a reload when the page runs via <code>serve_reviewer.py</code>.</p>

    <h3>the sections</h3>
    <p><b>Sheet</b> — the source sprite sheet (left). <b>Animations</b> — the list of
       animations (click one to edit it). <b>Rectangles</b> — the atlas-slot editor.
       <b>Suggestions</b> — the agent's proposed mappings with approve/dismiss/comment.
       <b>Animation settings</b> — mode/scale for the current animation. <b>Preview</b> —
       original vs new, playing together. <b>Baked frames</b> — what actually bakes.
       <b>Frame list</b> — the source sprites that make up the animation (editable).</p>

    <h3>controls and shortcuts</h3>
    <p>On the <b>Sheet</b>: click a box to select a sprite, <b>double-click</b> it to append it
       to the current animation, drag to pan and use the wheel to zoom.</p>
    <p>Drag the divider between the Sheet and the panels to resize them; double-click the
       divider to reset. <b>Undo</b> is <code>Ctrl+Z</code> and <b>Redo</b> is <code>Ctrl+Y</code>
       (also <code>Ctrl+Shift+Z</code>).</p>
    <p><b>Export mapping.json</b> saves in place, keeping the previous file as
       <code>mapping.backup.json</code>, when the page is launched via
       <code>ReviewSprites.bat</code>; opened as a plain file it downloads instead.</p>
  </div>
</div>
<div id="toast"></div>
<script>
/*__DATA__*/
const S = {}; DATA.sprites.forEach(s => S[s.id] = s);
let mapping = JSON.parse(JSON.stringify(DATA.mapping));
if (!mapping.animations) mapping.animations = {};
let selected = null;
let selAnim = DATA.animOrder[0];

// baseline = the last exported/loaded state; each section can be reset to it.
// history / redo = undo and redo stacks, one entry per edit action.
let baseline = JSON.parse(JSON.stringify(mapping));
let history = [];
let redoStack = [];
function pushHistory(){
  history.push(JSON.stringify(mapping));
  if (history.length > 500) history.shift();
  redoStack = [];                      // a new edit clears the redo stack
}
function undo(){
  if (!history.length) return;
  redoStack.push(JSON.stringify(mapping));
  mapping = JSON.parse(history.pop());
  refresh();
}
function redo(){
  if (!redoStack.length) return;
  history.push(JSON.stringify(mapping));
  mapping = JSON.parse(redoStack.pop());
  refresh();
}
function sectionEqual(a){
  return JSON.stringify(mapping.animations[a] || null)
       === JSON.stringify((baseline.animations || {})[a] || null);
}
function resetSection(){
  pushHistory();
  const b = (baseline.animations || {})[selAnim];
  if (b) mapping.animations[selAnim] = JSON.parse(JSON.stringify(b));
  else delete mapping.animations[selAnim];
  refresh();
}
function resetAll(){ pushHistory(); mapping = JSON.parse(JSON.stringify(baseline)); refresh(); }

const sheetCanvas = document.getElementById('sheet');
const sctx = sheetCanvas.getContext('2d');
let imgSource = null;
function showError(msg){
  const e = document.getElementById('err');
  e.style.display = 'block';
  e.textContent = msg;
}
window.onerror = (m, s, l, c) => { showError('JS error: ' + m + ' (line ' + l + ')'); };

// The embedded sheet is already transparent, so no canvas readback is needed
// (which also keeps it working with Brave's fingerprinting protection).
const rawImg = new Image();
rawImg.onload = () => { imgSource = rawImg; fitView(); drawSheet(); refresh(); };
rawImg.onerror = () => showError('The embedded sprite sheet failed to load.');
rawImg.src = DATA.sheet;

// vanilla Ax sheet, played beside the new animation for comparison
const origImg = new Image();
origImg.onload = () => drawAnimPreview();
origImg.onerror = () => showError('The embedded original (Ax) sheet failed to load.');
origImg.src = DATA.origSheet;

let zoom=0.55, panX=0, panY=0;
function fitView(){ resizeCanvas(); }
function resizeCanvas(){
  const r = sheetCanvas.parentElement.getBoundingClientRect();
  sheetCanvas.width = Math.max(50, r.width);
  sheetCanvas.height = Math.max(50, r.height);
  if (imgSource && zoom<=0){}
}
window.addEventListener('resize', ()=>{ resizeCanvas(); drawSheet(); });

// draggable splitter: resize the right-hand panel so more of the animation
// list is visible at once
const splitter = document.getElementById('splitter');
const rightPanel = document.getElementById('right');
let resizing = false;
function applyRightWidth(w){
  w = Math.max(300, Math.min(w, window.innerWidth - 220));
  rightPanel.style.flex = '0 0 ' + w + 'px';
  rightPanel.style.width = w + 'px';
}
splitter.addEventListener('mousedown', e => { resizing = true; e.preventDefault(); document.body.style.userSelect = 'none'; });
window.addEventListener('mousemove', e => { if (resizing) applyRightWidth(window.innerWidth - e.clientX - 4); });
window.addEventListener('mouseup', () => {
  if (!resizing) return;
  resizing = false; document.body.style.userSelect = '';
  resizeCanvas(); drawSheet();
});
splitter.addEventListener('dblclick', () => { applyRightWidth(430); resizeCanvas(); drawSheet(); });

let toastTimer = null;
function toast(msg){
  const t = document.getElementById('toast');
  t.textContent = msg; t.style.display = 'block';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.style.display = 'none'; }, 2500);
}

function drawSheet(){
  const ctx = sctx, c = sheetCanvas;
  ctx.setTransform(1,0,0,1,0,0);
  ctx.fillStyle = '#0c0e12'; ctx.fillRect(0,0,c.width,c.height);
  if (!imgSource) return;
  ctx.imageSmoothingEnabled = false;
  ctx.save();
  ctx.translate(panX,panY); ctx.scale(zoom,zoom);
  ctx.drawImage(imgSource,0,0);
  ctx.lineWidth = 1/zoom;
  for (const s of DATA.sprites){
    ctx.strokeStyle = (selected && selected.id===s.id) ? '#ffea00' : 'rgba(255,70,70,0.65)';
    ctx.strokeRect(s.x, s.y, s.w, s.h);
  }
  ctx.restore();
}

function sheetToScreen(x,y){ return [x*zoom+panX, y*zoom+panY]; }
function screenToSheet(x,y){ return [(x-panX)/zoom, (y-panY)/zoom]; }

let dragging=false, moved=false, lx=0, ly=0;
sheetCanvas.addEventListener('mousedown', e => { dragging=true; moved=false; lx=e.offsetX; ly=e.offsetY; });
sheetCanvas.addEventListener('mousemove', e => {
  if (!dragging) return;
  const dx = e.offsetX-lx, dy = e.offsetY-ly; lx=e.offsetX; ly=e.offsetY;
  if (Math.abs(dx)+Math.abs(dy) > 0){ moved=true; panX+=dx; panY+=dy; drawSheet(); }
});
sheetCanvas.addEventListener('mouseup', e => { if (!moved) pick(e.offsetX, e.offsetY); dragging=false; });
sheetCanvas.addEventListener('mouseleave', ()=>{ dragging=false; });
// double-click a sprite on the sheet -> append it to the current animation
sheetCanvas.addEventListener('dblclick', e => {
  pick(e.offsetX, e.offsetY);
  if (selected){ pushHistory(); entry(selAnim).frames.push(selected.id); refresh(); }
});
sheetCanvas.addEventListener('wheel', e => {
  e.preventDefault();
  const [sx,sy] = screenToSheet(e.offsetX, e.offsetY);
  zoom = Math.min(4, Math.max(0.08, zoom * (e.deltaY<0?1.15:1/1.15)));
  panX = e.offsetX - sx*zoom; panY = e.offsetY - sy*zoom;
  drawSheet();
}, {passive:false});

function pick(px,py){
  const [sx,sy] = screenToSheet(px,py);
  let best=null;
  for (const s of DATA.sprites){
    if (sx>=s.x && sx<s.x+s.w && sy>=s.y && sy<s.y+s.h){
      if (!best || s.w*s.h < best.w*best.h) best = s;
    }
  }
  if (best){ selected = best; showInfo(); drawSheet(); drawFrames();
    const rb = document.getElementById('rectsbar');
    if (rb && rb.open) renderRects();
  }
}
function showInfo(){
  document.getElementById('sheetinfo').textContent = selected
    ? `selected ${selected.id}   x=${selected.x} y=${selected.y} w=${selected.w} h=${selected.h}`
    : 'no sprite selected';
}

// ---- animation editor ----
function entry(anim){
  if (!mapping.animations[anim]) mapping.animations[anim] = {mode:'bottom', frames:[]};
  return mapping.animations[anim];
}
function animFrames(anim){
  const e = entry(anim);
  const ids = (e.frames && e.frames.length) ? e.frames : entry('idle').frames;
  return {e, ids: ids.slice()};
}
function baseOf(e){ return e.scale || mapping.global_scale || 1.15; }
// Mirrors build_atlas. The atlas is keyed by rectangle and the original layout
// reuses rectangles across animations (attack_1/attack_2, thrown/stunned_2/
// stand_up, ...), so each rectangle must resolve to ONE sprite + size + mode:
// the first animation to use a rectangle owns it and later ones reuse its
// choice, with optional mapping.rect_overrides. Without this, a rectangle
// accumulates two alpha-composited poses - the "doubled sprite" bug.
function rectKey(gf){ return gf.x+','+gf.y+','+gf.w+','+gf.h; }
let PLAN = {};
function buildPlan(){
  const plan = {};
  for (const a of DATA.animOrder){
    const e = entry(a);
    const ids = (e.frames && e.frames.length) ? e.frames : entry('idle').frames;
    const mode = e.mode || 'bottom';
    const base = baseOf(e);
    const gfs = DATA.ga[a] || [];
    const distinct = [], seen = new Set();
    for (const gf of gfs){ const k = rectKey(gf); if (!seen.has(k)){ seen.add(k); distinct.push(gf); } }
    const assign = {};
    distinct.forEach((gf,i) => { assign[rectKey(gf)] = ids[i % ids.length]; });
    // one uniform scale for a bottom-mode animation (see build_atlas.fit_scale)
    let uniform = null;
    if (mode !== 'center' && distinct.length){
      uniform = Infinity;
      distinct.forEach(gf => {
        const sp = S[assign[rectKey(gf)]]; if (!sp) return;
        const v = (gf.cy <= 0) ? Math.min(base, gf.h/sp.h, gf.w/sp.w)
                               : Math.min(base, gf.cy/sp.h);
        uniform = Math.min(uniform, v);
      });
      uniform = isFinite(uniform) ? Math.max(uniform, 0.1) : null;
    }
    distinct.forEach(gf => {
      const k = rectKey(gf);
      if (plan[k]) return;
      const sp = S[assign[k]]; if (!sp) return;
      const sc = (mode === 'center') ? Math.min(base, gf.h/sp.h, gf.w/sp.w) : uniform;
      plan[k] = {id: assign[k], mode: mode, scale: Math.max(sc == null ? 0.1 : sc, 0.1),
                 base: base, owner: a};
    });
  }
  const ov = mapping.rect_overrides || {};
  for (const key in ov){
    const p = plan[key]; if (!p) continue;
    const o = ov[key];
    if (typeof o === 'string') p.id = o;
    else if (o && typeof o === 'object'){
      if (o.id) p.id = o.id;
      if (o.mode) p.mode = o.mode;
      if (o.scale != null) p.scale = o.scale;
    }
  }
  return plan;
}
function spriteScale(sp, gf, mode, base){
  if (mode === 'center' || gf.cy <= 0) return Math.min(base, gf.h/sp.h, gf.w/sp.w);
  return Math.min(base, gf.cy/sp.h);
}
function drawPlanned(ctx, gf, ax, ay, idOverride){
  const p = PLAN[rectKey(gf)];
  if (!p) return;
  const sp = S[idOverride || p.id];
  if (!sp) return;
  // a frame list longer than the layout ("inherited" single-frame poses) shows
  // extra sprites on the same rectangle; size each by its own dimensions
  const s = idOverride
    ? Math.max(spriteScale(sp, gf, p.mode, p.base || p.scale), 0.1)
    : p.scale;
  drawFrameSprite(ctx, sp, gf, p.mode, p.base || p.scale, ax, ay, s);
}
// Frames the preview/filmstrip should show. The game layout may have fewer
// frames than the animation's frame list, so show every mapped frame: baked
// frames use the plan, extra mapped frames use their own sprite on the
// animation's rectangle.
function previewFrames(anim){
  const e = entry(anim);
  const ids = (e.frames && e.frames.length) ? e.frames : entry('idle').frames;
  const gfs = DATA.ga[anim] || [];
  if (!gfs.length) return {e: e, ids: ids, gfs: gfs, n: 0, frames: []};
  const n = Math.max(gfs.length, ids.length);
  const frames = [];
  for (let i = 0; i < n; i++){
    const gf = gfs[i % gfs.length];
    const p = PLAN[rectKey(gf)];
    const id = (i < gfs.length && p) ? p.id : ids[i % ids.length];
    frames.push({gf: gf, id: id, extra: i >= gfs.length});
  }
  return {e: e, ids: ids, gfs: gfs, n: n, frames: frames};
}
// ---- rectangle editor (shared atlas slots) ----
function rectCatalog(){
  const map = {};
  for (const a of DATA.animOrder){
    for (const gf of (DATA.ga[a] || [])){
      const k = rectKey(gf);
      let e = map[k];
      if (!e){ e = map[k] = {key:k, gf:gf, owner:a, anims:[]}; }
      if (!e.anims.includes(a)) e.anims.push(a);
    }
  }
  return Object.values(map);
}
function overrideText(k){
  const ov = (mapping.rect_overrides || {})[k];
  if (ov == null) return '';
  return (typeof ov === 'string') ? ov : JSON.stringify(ov);
}
function setOverride(k, id){
  pushHistory();
  if (!mapping.rect_overrides) mapping.rect_overrides = {};
  mapping.rect_overrides[k] = id;
  toast('rectangle ' + k + ' -> ' + id);
  refresh();
}
function clearOverride(k){
  if (!(mapping.rect_overrides && mapping.rect_overrides[k] != null)) return;
  pushHistory();
  delete mapping.rect_overrides[k];
  toast('cleared override for ' + k);
  refresh();
}
function rectThumb(id){
  const cv = document.createElement('canvas');
  const sp = S[id];
  if (!sp || !imgSource) return cv;
  const sc = Math.min(26/sp.w, 26/sp.h);
  cv.width = Math.max(1, Math.round(sp.w*sc));
  cv.height = Math.max(1, Math.round(sp.h*sc));
  const x = cv.getContext('2d'); x.imageSmoothingEnabled = false;
  x.drawImage(imgSource, sp.x, sp.y, sp.w, sp.h, 0, 0, cv.width, cv.height);
  cv.style.marginRight = '5px'; cv.style.verticalAlign = 'middle';
  return cv;
}
// ---- suggestions (proposed mappings from the agent, via suggestions.json) ----
let suggestions = (DATA.suggestions && Array.isArray(DATA.suggestions.suggestions))
  ? DATA.suggestions.suggestions : [];
async function saveSuggestions(){
  if (location.protocol === 'file:') { toast('opened as a file - suggestion state not saved'); return; }
  try {
    const r = await fetch('/api/suggestions', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({suggestions: suggestions})});
    if (!r.ok) throw new Error((await r.text()).trim() || ('HTTP ' + r.status));
  } catch(err){ toast('saving suggestion state failed: ' + err.message); }
}
function suggThumb(id, small){
  const sp = S[id];
  const wrap = document.createElement('div'); wrap.className = 't';
  if (sp && imgSource){
    const cv = document.createElement('canvas');
    const mw = small ? 26 : 52, mh = small ? 30 : 60;
    const sc = Math.min(mw/sp.w, mh/sp.h);
    cv.width = Math.max(1, Math.round(sp.w*sc)); cv.height = Math.max(1, Math.round(sp.h*sc));
    const x = cv.getContext('2d'); x.imageSmoothingEnabled = false;
    x.drawImage(imgSource, sp.x, sp.y, sp.w, sp.h, 0, 0, cv.width, cv.height);
    wrap.appendChild(cv);
  }
  const lab = document.createElement('div'); lab.textContent = id; wrap.appendChild(lab);
  wrap.title = id + ' - click to select it on the sheet';
  wrap.onclick = () => { if (sp){ selected = sp; showInfo(); drawSheet(); drawFrames(); } };
  return wrap;
}
function setSuggStatus(s, status){
  s.status = status;
  saveSuggestions();
  renderSuggestions();
}
function approveSuggestion(s){
  pushHistory();
  const e = entry(s.animation);
  e.mode = s.mode || 'bottom';
  if (s.scale != null) e.scale = s.scale; else delete e.scale;
  e.frames = (s.frames || []).slice();
  s.status = 'approved';
  saveSuggestions();
  refresh();
  toast('applied to ' + s.animation + ' - Export mapping.json to keep it');
}
function renderSuggestions(){
  const el = document.getElementById('suggbody');
  if (!el) return;
  el.innerHTML = '';
  const open = suggestions.filter(s => (s.status || 'proposed') === 'proposed').length;
  const cnt = document.getElementById('suggcount');
  if (cnt) cnt.textContent = suggestions.length + ' total, ' + open + ' open';
  if (!suggestions.length){
    el.innerHTML = '<div class="hint">No suggestions right now. Proposals are written to suggestions.json and appear here after ReviewSprites.bat regenerates the page.</div>';
    return;
  }
  for (const s of suggestions){
    const status = s.status || 'proposed';
    const card = document.createElement('div');
    card.className = 'sugg ' + status;
    const head = document.createElement('div');
    const nm = document.createElement('b'); nm.textContent = s.animation; head.appendChild(nm);
    const st = document.createElement('span'); st.className = 'st ' + status; st.textContent = status; head.appendChild(st);
    card.appendChild(head);
    if (s.note){ const n = document.createElement('div'); n.className = 'hint'; n.textContent = s.note; card.appendChild(n); }
    const pl = document.createElement('div'); pl.className = 'curhint'; pl.textContent = 'proposed frames:'; card.appendChild(pl);
    const strip = document.createElement('div'); strip.className = 'strip';
    (s.frames || []).forEach(id => strip.appendChild(suggThumb(id)));
    card.appendChild(strip);
    // current frames for comparison; read without entry() so nothing is created
    const curIds = ((mapping.animations[s.animation] || {}).frames || []);
    const cl = document.createElement('div'); cl.className = 'curhint'; cl.textContent = 'current frames:' + (curIds.length ? '' : ' (falls back to idle)');
    card.appendChild(cl);
    const cstrip = document.createElement('div'); cstrip.className = 'strip';
    curIds.forEach(id => cstrip.appendChild(suggThumb(id, true)));
    card.appendChild(cstrip);
    const row = document.createElement('div'); row.className = 'row';
    if (status !== 'approved'){
      const ab = document.createElement('button'); ab.className = 'primary'; ab.textContent = 'Approve';
      ab.title = 'apply these frames to ' + s.animation + ' in the page, then Export mapping.json to keep them';
      ab.onclick = () => approveSuggestion(s);
      row.appendChild(ab);
    }
    if (status !== 'dismissed'){
      const db = document.createElement('button'); db.textContent = 'Dismiss';
      db.title = 'mark this proposal as rejected (kept for the record)';
      db.onclick = () => setSuggStatus(s, 'dismissed');
      row.appendChild(db);
    }
    if (status !== 'proposed'){
      const rb = document.createElement('button'); rb.textContent = 'Reopen';
      rb.onclick = () => setSuggStatus(s, 'proposed');
      row.appendChild(rb);
    }
    card.appendChild(row);
    const ta = document.createElement('textarea'); ta.rows = 2;
    ta.placeholder = 'comment for the agent - what to change about this proposal';
    ta.value = s.comment || '';
    // keep in-memory while typing so a panel refresh does not lose the draft
    ta.oninput = () => { s.comment = ta.value; };
    const cb = document.createElement('button'); cb.textContent = 'Save comment';
    cb.onclick = () => { s.comment = ta.value; saveSuggestions(); toast('comment saved for ' + s.animation); };
    card.appendChild(ta); card.appendChild(cb);
    el.appendChild(card);
  }
}
function renderRects(){
  const el = document.getElementById('rectsbody');
  if (!el) return;
  el.innerHTML = '';
  const onlyCur = document.getElementById('rectsonlycur').checked;
  document.getElementById('rectselinfo').textContent =
    selected ? ('selected sprite: ' + selected.id) : 'select a sprite on the sheet to enable Set';
  const table = document.createElement('table');
  table.className = 'recttable';
  const head = document.createElement('tr');
  ['rectangle', 'size', 'owner', 'used by', 'current sprite', 'override', 'set / clear'].forEach(h => {
    const th = document.createElement('th'); th.textContent = h; head.appendChild(th);
  });
  table.appendChild(head);
  for (const c of rectCatalog()){
    if (onlyCur && !c.anims.includes(selAnim)) continue;
    const p = PLAN[c.key] || {};
    const shared = c.anims.length > 1;
    const borrowed = shared && c.owner !== selAnim && c.anims.includes(selAnim);
    const tr = document.createElement('tr');
    if (c.anims.includes(selAnim)) tr.classList.add('cur');
    if (shared) tr.classList.add('shared');
    if (borrowed) tr.classList.add('borrowed');
    tr.title = 'owner: ' + c.owner + ' | used by: ' + c.anims.join(', ');

    const td0 = document.createElement('td'); td0.className = 'mono'; td0.textContent = c.key; tr.appendChild(td0);
    const td1 = document.createElement('td'); td1.textContent = c.gf.w + 'x' + c.gf.h + (c.gf.cy > 0 ? '  cy' + c.gf.cy : ''); tr.appendChild(td1);
    const td2 = document.createElement('td'); td2.textContent = c.owner; tr.appendChild(td2);
    const td3 = document.createElement('td'); td3.textContent = c.anims.join(', '); tr.appendChild(td3);
    const td4 = document.createElement('td'); td4.appendChild(rectThumb(p.id));
    td4.appendChild(document.createTextNode(p.id || '?'));
    if (borrowed){ const b = document.createElement('span'); b.textContent = '  borrowed'; b.style.color = '#ff9d2e'; td4.appendChild(b); }
    tr.appendChild(td4);
    const td5 = document.createElement('td'); td5.className = 'mono'; td5.textContent = overrideText(c.key); tr.appendChild(td5);
    const td6 = document.createElement('td');
    const setb = document.createElement('button'); setb.textContent = 'Set';
    setb.disabled = !selected;
    setb.title = selected ? ('bake ' + selected.id + ' into this rectangle') : 'select a sprite on the sheet first';
    setb.onclick = () => { if (selected) setOverride(c.key, selected.id); };
    td6.appendChild(setb);
    const clb = document.createElement('button'); clb.textContent = 'Clear';
    clb.disabled = (mapping.rect_overrides || {})[c.key] == null;
    clb.onclick = () => clearOverride(c.key);
    td6.appendChild(clb);
    tr.appendChild(td6);
    table.appendChild(tr);
  }
  el.appendChild(table);
  const cnt = document.getElementById('rectcount');
  if (cnt){
    const all = rectCatalog();
    const shared = all.filter(c => c.anims.length > 1).length;
    cnt.textContent = `${all.length} total` + (shared ? `, ${shared} shared` : ', none shared');
  }
}
function drawFrameSprite(ctx, sp, gf, mode, base, ax, ay, sOverride){
  if (!imgSource || !sp) return; // sheet may not have loaded yet
  // mirrors build_atlas.fit_scale: "center" fits the frame, "bottom" keeps a
  // constant size and clips wide poses instead of shrinking the character.
  let s;
  if (sOverride != null) s = sOverride;
  else if (mode==='center' || gf.cy<=0) s = Math.min(base, gf.h/sp.h, gf.w/sp.w);
  else s = Math.min(base, gf.cy/sp.h);
  s = Math.max(s, 0.1);
  const nw = Math.max(1, Math.round(sp.w*s)), nh = Math.max(1, Math.round(sp.h*s));
  const dx = ax - Math.floor(nw/2);
  const dy = mode==='center' ? ay - gf.cy + Math.floor((gf.h-nh)/2) : ay - nh;
  ctx.drawImage(imgSource, sp.x, sp.y, sp.w, sp.h, dx, dy, nw, nh);
}

const film = document.getElementById('film');
function drawFilm(){
  const {gfs, frames, n} = previewFrames(selAnim);
  const cell = 72, H = 110;
  film.width = Math.max(340, n*cell);
  film.height = H;
  film.style.width = '100%';
  const ctx = film.getContext('2d');
  ctx.clearRect(0,0,film.width,H);
  ctx.fillStyle = '#0c0e12'; ctx.fillRect(0,0,film.width,H);
  ctx.imageSmoothingEnabled = false;
  frames.forEach((fr,i) => {
    const gf = fr.gf;
    const ax = i*cell + cell/2, ay = H-24;
    // ground line
    ctx.strokeStyle='rgba(120,120,120,0.25)';
    ctx.beginPath(); ctx.moveTo(i*cell, ay+0.5); ctx.lineTo((i+1)*cell, ay+0.5); ctx.stroke();
    drawPlanned(ctx, gf, ax, ay, fr.extra ? fr.id : null);
    // orange outline = this frame borrows a rectangle owned by another animation
    const pp = PLAN[rectKey(gf)];
    if (pp && pp.owner !== selAnim){
      ctx.strokeStyle = '#ff9d2e'; ctx.lineWidth = 2;
      ctx.strokeRect(i*cell+1, 1, cell-2, H-2); ctx.lineWidth = 1;
    }
    ctx.fillStyle = fr.extra ? '#ffb44a' : '#678';
    ctx.fillText(String(i), i*cell+4, 12);
  });
  const owners = new Set();
  gfs.forEach(gf => { const p = PLAN[rectKey(gf)]; if (p && p.owner !== selAnim) owners.add(p.owner); });
  const extras = Math.max(0, n - gfs.length);
  let msg = `${gfs.length} game frame(s), ${n} shown`;
  if (extras) msg += ` (${extras} extra from the frame list)`;
  if (owners.size) msg += ` - shared rects owned by: ${[...owners].join(', ')}`;
  document.getElementById('count').textContent = msg;
}

function drawFrames(){
  const bar = document.getElementById('framebar');
  bar.innerHTML = '';
  const {ids} = animFrames(selAnim);
  ids.forEach((id,i) => {
    const sp = S[id]; if (!sp) return;
    const box = document.createElement('div');
    box.className = 'fbox' + (selected && selected.id===id ? ' sel':'');
    const cv = document.createElement('canvas');
    const scale = Math.min(52/sp.w, 60/sp.h);
    cv.width = Math.max(1,Math.round(sp.w*scale)); cv.height = Math.max(1,Math.round(sp.h*scale));
    cv.title = id;
    if (imgSource){
      const x = cv.getContext('2d'); x.imageSmoothingEnabled=false;
      x.drawImage(imgSource, sp.x,sp.y,sp.w,sp.h, 0,0,cv.width,cv.height);
    }
    box.appendChild(cv);
    const c = document.createElement('div'); c.className='c';
    const mk = (t, fn) => { const b=document.createElement('button'); b.textContent=t; b.onclick=fn; c.appendChild(b); };
    mk('\u25c0', ()=>{ if(i>0){ pushHistory(); const a=entry(selAnim).frames; [a[i-1],a[i]]=[a[i],a[i-1]]; refresh(); }});
    mk('\u25b6', ()=>{ const a=entry(selAnim).frames; if(i<a.length-1){ pushHistory(); [a[i],a[i+1]]=[a[i+1],a[i]]; refresh(); }});
    mk('\u2715', ()=>{ pushHistory(); entry(selAnim).frames.splice(i,1); refresh(); });
    box.onclick = (ev)=>{ if (ev.target.tagName==='CANVAS' && selected){ pushHistory(); entry(selAnim).frames[i]=selected.id; refresh(); } };
    box.appendChild(c);
    bar.appendChild(box);
  });
}

// ---- animated preview (plays at the animation's real speed) ----
const animPrev = document.getElementById('animprev');
const apctx = animPrev.getContext('2d');
const origPrev = document.getElementById('origprev');
const opctx = origPrev.getContext('2d');
let playing = true, animT = 0, lastT = performance.now();

function realFps(a){ const sp = (DATA.speed[a] != null) ? DATA.speed[a] : 0.1; return sp * 60; }
function currentFps(){
  const ov = parseFloat(document.getElementById('fps').value);
  if (!isNaN(ov) && ov > 0) return ov;
  return Math.max(0.5, realFps(selAnim));
}
function drawAnimPreview(){
  const {gfs, frames} = previewFrames(selAnim);
  const ctx = apctx, W = animPrev.width, H = animPrev.height;
  ctx.setTransform(1,0,0,1,0,0);
  ctx.clearRect(0,0,W,H); ctx.fillStyle='#0c0e12'; ctx.fillRect(0,0,W,H);
  ctx.imageSmoothingEnabled = false;
  // original (Ax) canvas
  const octx = opctx, OW = origPrev.width, OH = origPrev.height;
  octx.setTransform(1,0,0,1,0,0);
  octx.clearRect(0,0,OW,OH); octx.fillStyle='#0c0e12'; octx.fillRect(0,0,OW,OH);
  octx.imageSmoothingEnabled = false;
  const n = frames.length;
  if (!n || !imgSource) return;
  const i = Math.min(n-1, Math.floor(animT));
  const fr = frames[i];
  const gf = fr.gf;
  const z = 2, ax = W/2, ay = H-18;
  ctx.save(); ctx.scale(z,z);
  drawPlanned(ctx, gf, ax/z, ay/z, fr.extra ? fr.id : null);
  ctx.restore();
  ctx.strokeStyle='rgba(120,120,120,0.4)';
  ctx.beginPath(); ctx.moveTo(0,ay+0.5); ctx.lineTo(W,ay+0.5); ctx.stroke();
  ctx.fillStyle = fr.extra ? '#ffb44a' : '#adf'; ctx.font='12px monospace';
  ctx.fillText('frame ' + (i+1) + '/' + n + (fr.extra ? ' (extra)' : ''), 6, 14);
  // the original art is already at frame size, so draw the rectangle unscaled,
  // with its anchor on the same ground line as the new sprite. Use the original
  // layout (origGa) because a de-shared layout points at new, empty rectangles.
  const ogfs = DATA.origGa[selAnim] || gfs;
  const ogf = ogfs[i % ogfs.length];
  if (origImg.complete && origImg.naturalWidth && ogf){
    const ox = OW/2, oy = OH-18;
    octx.save(); octx.scale(z,z);
    octx.drawImage(origImg, ogf.x, ogf.y, ogf.w, ogf.h,
                   ox/z - ogf.cx, oy/z - ogf.cy, ogf.w, ogf.h);
    octx.restore();
    octx.strokeStyle='rgba(120,120,120,0.4)';
    octx.beginPath(); octx.moveTo(0,oy+0.5); octx.lineTo(OW,oy+0.5); octx.stroke();
    octx.fillStyle='#adf'; octx.font='12px monospace';
    octx.fillText('frame ' + (i+1) + '/' + n, 6, 14);
  }
}
function tick(now){
  const dt = Math.min(0.1, (now - lastT)/1000); lastT = now;
  if (playing && imgSource){
    const n = Math.max((DATA.ga[selAnim]||[]).length,
                       (entry(selAnim).frames||[]).length);
    if (n > 0){
      animT += dt * currentFps();
      // force-loop in the preview; otherwise follow the animation's real
      // loop flag (one-shots hold their last frame, like in game).
      const loop = document.getElementById('forceloop').checked
                || DATA.loop[selAnim] === true;
      if (animT >= n){ animT = loop ? (animT % n) : n - 0.0001; }
    }
  }
  drawAnimPreview();
  requestAnimationFrame(tick);
}

function refresh(){
  document.getElementById('animname').textContent = selAnim;
  document.getElementById('mode').value = entry(selAnim).mode || 'bottom';
  const e = entry(selAnim);
  document.getElementById('ascale').value = e.scale || '';
  const loop = DATA.loop[selAnim] === true;
  document.getElementById('animmeta').textContent =
    `speed ${(DATA.speed[selAnim]!=null?DATA.speed[selAnim]:0.1)} = ${Math.round(realFps(selAnim)*10)/10} fps - ${loop?'loops':'plays once'}`;
  PLAN = buildPlan();
  renderAnimList(); drawFilm(); drawFrames(); drawAnimPreview(); showInfo();
  renderSuggestions();
  const rb = document.getElementById('rectsbar');
  if (rb && rb.open) renderRects();
}

function renderAnimList(){
  const el = document.getElementById('animlist');
  el.innerHTML = '';
  for (const a of DATA.animOrder){
    const e = mapping.animations[a];
    const d = document.createElement('div');
    d.className = 'anim' + (a===selAnim?' active':'');
    d.innerHTML = `${a} <span class="n">${e && e.frames ? e.frames.length : 0}</span>`
                + (sectionEqual(a) ? '' : ' <span class="mod">*</span>');
    d.onclick = () => { selAnim = a; animT = 0; document.getElementById('fps').value = Math.round(realFps(a)*10)/10; refresh(); };
    el.appendChild(d);
  }
}

// ---- controls ----
document.getElementById('mode').onchange = e => { pushHistory(); entry(selAnim).mode = e.target.value; refresh(); };
document.getElementById('ascale').onchange = e => {
  const v = parseFloat(e.target.value);
  pushHistory();
  if (isNaN(v)) delete entry(selAnim).scale; else entry(selAnim).scale = v;
  refresh();
};
document.getElementById('append').onclick = () => { if (selected){ pushHistory(); entry(selAnim).frames.push(selected.id); refresh(); } };
document.getElementById('onlysel').onclick = () => { if (selected){ pushHistory(); entry(selAnim).frames = [selected.id]; refresh(); } };
document.getElementById('clear').onclick = () => { pushHistory(); entry(selAnim).frames = []; refresh(); };
document.getElementById('undo').onclick = undo;
document.getElementById('redo').onclick = redo;
document.getElementById('resetall').onclick = resetAll;
document.getElementById('resetsection').onclick = resetSection;
document.getElementById('play').onclick = () => {
  playing = !playing;
  document.getElementById('play').textContent = playing ? 'Pause' : 'Play';
};
document.getElementById('replay').onclick = () => {
  animT = 0; playing = true;
  document.getElementById('play').textContent = 'Pause';
};
document.getElementById('gscale').onchange = e => { const v=parseFloat(e.target.value); if(!isNaN(v)){pushHistory(); mapping.global_scale=v; refresh();} };
document.getElementById('export').onclick = async () => {
  const text = JSON.stringify(mapping, null, 1);
  baseline = JSON.parse(JSON.stringify(mapping));
  history = [];
  redoStack = [];
  renderAnimList();
  const st = document.getElementById('savestatus');
  // When served by serve_reviewer.py we write straight over mapping.json and
  // keep the previous version as mapping.backup.json. Opened as a plain file
  // (file://) there is no server, so fall back to a download.
  if (location.protocol !== 'file:') {
    try {
      const r = await fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body:text});
      const msg = (await r.text()).trim();
      if (!r.ok) throw new Error(msg || ('HTTP ' + r.status));
      st.textContent = 'Saved mapping.json (previous kept as mapping.backup.json).';
      st.style.color = '#7de07d';
      return;
    } catch(err){
      st.textContent = 'Save failed: ' + err.message + ' - downloading instead.';
      st.style.color = '#ffb0b0';
    }
  } else {
    st.textContent = 'Opened as a file: downloading mapping.json (run ReviewSprites.bat to save in place).';
    st.style.color = '#ffd84a';
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], {type:'application/json'}));
  a.download = 'mapping.json'; a.click();
};
document.getElementById('load').onchange = e => {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = () => {
    try {
      mapping = JSON.parse(r.result);
      baseline = JSON.parse(JSON.stringify(mapping));
      history = [];
      redoStack = [];
      refresh();
    } catch(err){ alert('bad JSON: '+err); }
  };
  r.readAsText(f);
};

// keyboard shortcuts: Ctrl+Z undo, Ctrl+Y (or Ctrl+Shift+Z) redo
window.addEventListener('keydown', e => {
  if (!(e.ctrlKey || e.metaKey)) return;
  const k = (e.key || '').toLowerCase();
  if (k === 'z' && !e.shiftKey){ e.preventDefault(); undo(); }
  else if (k === 'y' || (k === 'z' && e.shiftKey)){ e.preventDefault(); redo(); }
});

// rectangle editor (inline bar under the animation list)
document.getElementById('rects').onclick = () => {
  const rb = document.getElementById('rectsbar');
  rb.open = !rb.open;
  renderRects();
  rb.scrollIntoView({behavior:'smooth', block:'start'});
};
document.getElementById('rectsbar').addEventListener('toggle', renderRects);
document.getElementById('rectsonlycur').onchange = renderRects;
document.getElementById('helpbtn').onclick = () => { document.getElementById('helpoverlay').style.display = 'block'; };
document.getElementById('closehelp').onclick = () => { document.getElementById('helpoverlay').style.display = 'none'; };

// init
resizeCanvas();
document.getElementById('gscale').value = mapping.global_scale;
document.getElementById('fps').value = Math.round(realFps(selAnim)*10)/10;
refresh();
requestAnimationFrame(tick);
window.addEventListener('load', ()=>{ resizeCanvas(); drawSheet(); });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
