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


def ga_frames():
    """Parse the character .char into frames + per-animation speed/loop."""
    anims = {}
    order = []
    speeds = {}
    loops = {}
    with open(ROOT / "chars" / "guybrush_threepwood.char", encoding="latin-1") as f:
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
    order, ga, speeds, loops = ga_frames()

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

    data = {
        "sheet": "data:image/png;base64," + sheet_b64,
        "sprites": sprites,
        "mapping": mapping,
        "animOrder": order,
        "ga": ga,
        "speed": speeds,
        "loop": loops,
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
  #left { flex:1 1 auto; min-width:0; display:flex; flex-direction:column; border-right:1px solid #333; }
  #sheetwrap { flex:1 1 auto; position:relative; overflow:hidden; background:#0c0e12; }
  #sheet { position:absolute; inset:0; width:100%; height:100%; }
  #sheetinfo { padding:5px 10px; background:#12141a; border-top:1px solid #333; font-family:monospace; white-space:nowrap; overflow:hidden; }
  #right { width:430px; flex:0 0 430px; display:flex; flex-direction:column; }
  #animlist { height:190px; overflow:auto; border-bottom:1px solid #333; padding:6px; }
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
  #overlay { position:fixed; inset:0; background:#0c0e12; z-index:50; overflow:auto; display:none; padding:14px; }
  #overlay h2 { margin-top:0; }
  .hint { color:#98a; font-size:12px; }
  #err { display:none; background:#7a2020; color:#fff; padding:6px 12px; font-family:monospace; white-space:pre-wrap; }
</style>
</head>
<body>
<div id="top">
  <h1>Guybrush sprite mapper</h1>
  <span class="hint">Click a box on the sheet to select a sprite; drag to pan, wheel to zoom.</span>
  <span style="flex:1"></span>
  <label>global scale <input id="gscale" type="number" step="0.05" style="width:70px"></label>
  <button id="all">Preview all animations</button>
  <button id="undo" title="Undo the last change">Undo</button>
  <button id="resetall" title="Restore every section to the last exported state">Reset all</button>
  <label class="hint">Load mapping <input id="load" type="file" accept=".json" style="width:150px"></label>
  <button id="export" class="primary">Export mapping.json</button>
</div>
<div id="err"></div>
<div id="main">
  <div id="left">
    <div id="sheetwrap"><canvas id="sheet"></canvas></div>
    <div id="sheetinfo">no sprite selected</div>
  </div>
  <div id="right">
    <div id="animlist"></div>
    <div id="editor">
      <div class="row">
        <b id="animname"></b>
        <button id="resetsection" title="Restore this section to the last exported state">Reset section</button>
        <label>mode <select id="mode"><option value="bottom">bottom (feet on ground)</option><option value="center">center (lying)</option></select></label>
        <label>scale <input id="ascale" type="number" step="0.05" placeholder="default" style="width:80px"></label>
      </div>
      <div class="row">
        <canvas id="animprev" width="260" height="150"></canvas>
        <div>
          <div><button id="play">Pause</button> <button id="replay">Replay</button> <label>fps <input id="fps" type="number" step="0.5" style="width:70px"></label></div>
          <div class="row" style="margin:4px 0"><label><input id="forceloop" type="checkbox" checked> loop preview</label></div>
          <div class="hint" id="animmeta"></div>
          <div class="hint">animated at the animation's real speed</div>
        </div>
      </div>
      <canvas id="film" height="110"></canvas>
      <div class="row">
        <button id="append">+ append selected sprite</button>
        <button id="onlysel">replace frames with selected</button>
        <button id="clear">clear frames</button>
        <span class="hint" id="count"></span>
      </div>
      <div class="framebar" id="framebar"></div>
      <div class="hint">Click a frame thumbnail to set it to the selected sprite. Use the arrows to reorder.</div>
      <textarea id="out" spellcheck="false" placeholder="Export to see / copy the JSON here"></textarea>
      <div class="row"><button id="copy">Copy JSON</button></div>
    </div>
  </div>
</div>
<div id="overlay">
  <h2>All animations <button id="closeoverlay">close</button></h2>
  <div id="overlaybody"></div>
</div>
<script>
/*__DATA__*/
const S = {}; DATA.sprites.forEach(s => S[s.id] = s);
let mapping = JSON.parse(JSON.stringify(DATA.mapping));
if (!mapping.animations) mapping.animations = {};
let selected = null;
let selAnim = DATA.animOrder[0];

// baseline = the last exported/loaded state; each section can be reset to it.
// history = undo stack, one entry per edit action.
let baseline = JSON.parse(JSON.stringify(mapping));
let history = [];
function pushHistory(){ history.push(JSON.stringify(mapping)); if (history.length > 500) history.shift(); }
function undo(){ if (!history.length) return; mapping = JSON.parse(history.pop()); refresh(); }
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

let zoom=0.55, panX=0, panY=0;
function fitView(){ resizeCanvas(); }
function resizeCanvas(){
  const r = sheetCanvas.parentElement.getBoundingClientRect();
  sheetCanvas.width = Math.max(50, r.width);
  sheetCanvas.height = Math.max(50, r.height);
  if (imgSource && zoom<=0){}
}
window.addEventListener('resize', ()=>{ resizeCanvas(); drawSheet(); });

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
  if (best){ selected = best; showInfo(); drawSheet(); drawFrames(); }
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
function drawFrameSprite(ctx, sp, gf, mode, base, ax, ay){
  if (!imgSource || !sp) return; // sheet may not have loaded yet
  // mirrors build_atlas.fit_scale: "center" fits the frame, "bottom" keeps a
  // constant size and clips wide poses instead of shrinking the character.
  let s;
  if (mode==='center' || gf.cy<=0) s = Math.min(base, gf.h/sp.h, gf.w/sp.w);
  else s = Math.min(base, gf.cy/sp.h);
  s = Math.max(s, 0.1);
  const nw = Math.max(1, Math.round(sp.w*s)), nh = Math.max(1, Math.round(sp.h*s));
  const dx = ax - Math.floor(nw/2);
  const dy = mode==='center' ? ay - gf.cy + Math.floor((gf.h-nh)/2) : ay - nh;
  ctx.drawImage(imgSource, sp.x, sp.y, sp.w, sp.h, dx, dy, nw, nh);
}

const film = document.getElementById('film');
function drawFilm(){
  const {e, ids} = animFrames(selAnim);
  const gfs = DATA.ga[selAnim] || [];
  const cell = 72, H = 110;
  film.width = Math.max(340, gfs.length*cell);
  film.height = H;
  film.style.width = '100%';
  const ctx = film.getContext('2d');
  ctx.clearRect(0,0,film.width,H);
  ctx.fillStyle = '#0c0e12'; ctx.fillRect(0,0,film.width,H);
  ctx.imageSmoothingEnabled = false;
  const base = e.scale || mapping.global_scale || 1.15;
  gfs.forEach((gf,i) => {
    const sp = S[ids[i % ids.length]];
    if (!sp) return;
    const ax = i*cell + cell/2, ay = H-24;
    // ground line
    ctx.strokeStyle='rgba(120,120,120,0.25)';
    ctx.beginPath(); ctx.moveTo(i*cell, ay+0.5); ctx.lineTo((i+1)*cell, ay+0.5); ctx.stroke();
    drawFrameSprite(ctx, sp, gf, e.mode||'bottom', base, ax, ay);
    ctx.fillStyle='#678'; ctx.fillText(String(i), i*cell+4, 12);
  });
  document.getElementById('count').textContent = `${gfs.length} game frames, ${ids.length} source frame(s)`;
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
let playing = true, animT = 0, lastT = performance.now();

function realFps(a){ const sp = (DATA.speed[a] != null) ? DATA.speed[a] : 0.1; return sp * 60; }
function currentFps(){
  const ov = parseFloat(document.getElementById('fps').value);
  if (!isNaN(ov) && ov > 0) return ov;
  return Math.max(0.5, realFps(selAnim));
}
function drawAnimPreview(){
  const {e, ids} = animFrames(selAnim);
  const gfs = DATA.ga[selAnim] || [];
  const ctx = apctx, W = animPrev.width, H = animPrev.height;
  ctx.setTransform(1,0,0,1,0,0);
  ctx.clearRect(0,0,W,H); ctx.fillStyle='#0c0e12'; ctx.fillRect(0,0,W,H);
  ctx.imageSmoothingEnabled = false;
  if (!gfs.length || !imgSource) return;
  const n = gfs.length;
  const i = Math.min(n-1, Math.floor(animT));
  const gf = gfs[i];
  const sp = S[ids[i % ids.length]];
  const base = e.scale || mapping.global_scale || 1.15;
  const z = 2, ax = W/2, ay = H-18;
  if (sp){
    ctx.save(); ctx.scale(z,z);
    drawFrameSprite(ctx, sp, gf, e.mode||'bottom', base, ax/z, ay/z);
    ctx.restore();
  }
  ctx.strokeStyle='rgba(120,120,120,0.4)';
  ctx.beginPath(); ctx.moveTo(0,ay+0.5); ctx.lineTo(W,ay+0.5); ctx.stroke();
  ctx.fillStyle='#adf'; ctx.font='12px monospace';
  ctx.fillText('frame ' + (i+1) + '/' + n, 6, 14);
}
function tick(now){
  const dt = Math.min(0.1, (now - lastT)/1000); lastT = now;
  if (playing && imgSource){
    const n = (DATA.ga[selAnim]||[]).length;
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
  renderAnimList(); drawFilm(); drawFrames(); drawAnimPreview(); showInfo();
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
document.getElementById('export').onclick = () => {
  const text = JSON.stringify(mapping, null, 1);
  document.getElementById('out').value = text;
  baseline = JSON.parse(JSON.stringify(mapping));
  history = [];
  renderAnimList();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], {type:'application/json'}));
  a.download = 'mapping.json'; a.click();
};
document.getElementById('copy').onclick = () => {
  const t = JSON.stringify(mapping, null, 1);
  document.getElementById('out').value = t;
  navigator.clipboard.writeText(t);
};
document.getElementById('load').onchange = e => {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = () => {
    try {
      mapping = JSON.parse(r.result);
      baseline = JSON.parse(JSON.stringify(mapping));
      history = [];
      refresh();
    } catch(err){ alert('bad JSON: '+err); }
  };
  r.readAsText(f);
};
document.getElementById('all').onclick = () => {
  const body = document.getElementById('overlaybody'); body.innerHTML='';
  const rowH = 120, cell = 64;
  const cv = document.createElement('canvas');
  cv.width = 64 + 12*cell; cv.height = rowH*DATA.animOrder.length;
  const ctx = cv.getContext('2d'); ctx.imageSmoothingEnabled=false;
  ctx.fillStyle='#0c0e12'; ctx.fillRect(0,0,cv.width,cv.height);
  DATA.animOrder.forEach((a,r) => {
    const {e, ids} = animFrames(a);
    const base = e.scale || mapping.global_scale || 1.15;
    ctx.fillStyle='#adf'; ctx.fillText(a, 4, r*rowH+14);
    (DATA.ga[a]||[]).forEach((gf,i) => {
      const sp = S[ids[i % ids.length]]; if (!sp) return;
      drawFrameSprite(ctx, sp, gf, e.mode||'bottom', base, 64+i*cell+cell/2, r*rowH+rowH-16);
    });
  });
  body.appendChild(cv);
  document.getElementById('overlay').style.display='block';
};
document.getElementById('closeoverlay').onclick = () => document.getElementById('overlay').style.display='none';

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
