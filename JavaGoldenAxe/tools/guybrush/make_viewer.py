#!/usr/bin/env python3
"""Generate viewer.html - a playable animation sandbox for the baked character.

Unlike reviewer.html (which previews the mapping), this loads the ALREADY BAKED
assets the engine uses at runtime:

    assets/res/chars/guybrush_threepwood.char   (frames + speed/loop)
    assets/res/image/guybrush_threepwood.png    (the atlas)

and runs a small player state machine over them, so you can press the game's
keys - move, run, ATTACK, JUMP, JUMP+ATTACK, MAGIC, get hit, die - and watch the
moves animate the way the game does (phase-driven jump arc, LEFT mirroring,
attack combo). Vanilla Ax can be shown beside it.

    python make_viewer.py          # writes viewer.html
Then open viewer.html (or double-click scripts\\ViewAnimations.bat).
"""
import base64
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "assets" / "res"
OUT = HERE / "viewer.html"
CHAR_ID = "guybrush_threepwood"

sprite_re = re.compile(
    r"^sprite\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(-?\d+)\s*$")
param_re = re.compile(r"^parameter\s+(\S+)\s+(\S+)\s+(\S+)\s*$")


def parse_char(char_name):
    order, frames, speeds, loops = [], {}, {}, {}
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
            frames.setdefault(anim, [])
            if anim not in order:
                order.append(anim)
            frames[anim].append({
                "x": int(m.group(3)), "y": int(m.group(4)),
                "w": int(m.group(5)), "h": int(m.group(6)),
                "cx": int(m.group(7)), "cy": int(m.group(8)),
            })
    anims = {a: {"frames": frames[a], "speed": speeds.get(a, 0.1),
                 "loop": loops.get(a, False)} for a in order}
    return order, anims


def b64_png(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main():
    order, anims = parse_char(f"{CHAR_ID}.char")
    _, orig_anims = parse_char("ax_battler.char")
    data = {
        "canvas": [276, 207],
        "atlas": b64_png(ROOT / "image" / f"{CHAR_ID}.png"),
        "origAtlas": b64_png(ROOT / "image" / "ax_battler.png"),
        "order": order, "anims": anims, "origAnims": orig_anims,
        "walkSpeed": 1.0, "runSpeed": 2.5,
        "jumpWalkSpeed": 5.0, "jumpRunSpeed": 6.5, "gravity": 0.2,
    }
    html = TEMPLATE.replace("/*__DATA__*/", "const DATA = " + json.dumps(data) + ";")
    OUT.write_text(html, encoding="utf-8")
    print("wrote", OUT, f"({OUT.stat().st_size // 1024} KB)", "-", len(order), "animations")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Guybrush move sandbox</title>
<style>
  * { box-sizing:border-box; }
  body { margin:0; font:13px/1.45 system-ui,Segoe UI,sans-serif; background:#15181d; color:#e6e6e6; }
  #top { display:flex; gap:12px; align-items:center; padding:8px 12px; background:#0f1116;
         border-bottom:1px solid #333; flex-wrap:wrap; }
  #top h1 { font-size:15px; margin:0 10px 0 0; }
  button { background:#262c36; color:#e6e6e6; border:1px solid #454b58;
           border-radius:5px; padding:5px 10px; cursor:pointer; user-select:none; }
  button:hover { background:#333c4a; }
  button:active { background:#3f6fb0; }
  .key { color:#8fd8b0; font-family:monospace; }
  #main { display:flex; height:calc(100vh - 46px); }
  #stagewrap { flex:1 1 auto; min-width:0; display:flex; flex-direction:column;
               align-items:center; justify-content:center; background:#0c0e12; }
  canvas#stage { image-rendering:pixelated; border:1px solid #2a2f3a; border-radius:6px; box-shadow:0 0 24px #0008; }  #side { width:290px; flex:0 0 290px; overflow:auto; border-left:1px solid #333; background:#101319; padding:10px; }
  .pad { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin:8px 0; }
  .pad button { padding:12px 0; font-size:15px; }
  .pad .sp { visibility:hidden; }
  .acts { display:grid; grid-template-columns:1fr 1fr; gap:6px; margin:8px 0; }
  .acts button { padding:9px 0; }
  .sechead { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:#8fa6d8;
             border-bottom:1px solid #333; padding:3px 0; margin-top:12px; }
  #list { display:flex; flex-wrap:wrap; gap:4px; }
  @media (max-width:820px){
    #main { flex-direction:column; }
    #stagewrap { flex:1 1 auto; min-height:52vh; }
    #side { width:auto; flex:0 0 auto; border-left:none; border-top:1px solid #333; }
  }
  .anim { padding:3px 7px; border:1px solid #313844; border-radius:5px; background:#1a1f27;
          color:#dbe4f2; cursor:pointer; font-size:12px; }
  .anim.active { background:#2c4b7a; border-color:#5f86d6; }
  .hint { color:#8a93a6; font-size:12px; }
  #err { display:none; background:#7a2020; color:#fff; padding:6px 12px; font-family:monospace; }
</style>
</head>
<body>
<div id="top">
  <h1>Guybrush move sandbox</h1>
  <button id="play">Pause</button>
  <button id="replay">Reset</button>
  <label>speed <input id="mult" type="number" value="1" step="0.25" min="0.1" style="width:60px">x</label>
  <label><input id="cmp" type="checkbox" checked> compare Ax</label>
  <span style="flex:1"></span>
  <span class="hint">keys: <span class="key">&#8592;&#8593;&#8595;&#8594;</span> move &middot; <span class="key">shift</span> run &middot;
    <span class="key">P</span> jump &middot; <span class="key">O</span> attack &middot; <span class="key">I</span> magic &middot;
    <span class="key">B</span> jump+attack</span>
</div>
<div id="err"></div>
<div id="main">
  <div id="stagewrap"><canvas id="stage" width="276" height="207"></canvas></div>
  <div id="side">
    <div class="sechead">Move</div>
    <div class="pad">
      <button class="sp"></button><button id="up">&#8593;</button><button class="sp"></button>
      <button id="left">&#8592;</button><button id="run" class="hint" style="padding:6px 0">RUN</button><button id="right">&#8594;</button>
      <button class="sp"></button><button id="down">&#8595;</button><button class="sp"></button>
    </div>
    <div class="sechead">Moves</div>
    <div class="acts">
      <button id="jump"><b>JUMP</b><br><span class="hint">P</span></button>
      <button id="attack"><b>ATTACK</b><br><span class="hint">O</span></button>
      <button id="jattack"><b>JUMP + ATK</b><br><span class="hint">B</span></button>
      <button id="magic"><b>MAGIC</b><br><span class="hint">I</span></button>
      <button id="special">SPECIAL</button>
      <button id="hit">GET HIT</button>
      <button id="knock">KNOCK DOWN</button>
      <button id="die">DIE</button>
    </div>
    <div class="hint" id="status">-</div>
    <div class="sechead">Play one animation (Reset to resume)</div>
    <div id="list"></div>
  </div>
</div>
<script>
/*__DATA__*/
const CW = DATA.canvas[0], CH = DATA.canvas[1];
const stage = document.getElementById('stage');
const ctx = stage.getContext('2d');
const anims = DATA.anims, order = DATA.order;

function fitStage(){
  const el = document.getElementById('stagewrap');
  const availW = el.clientWidth - 28, availH = el.clientHeight - 28;
  const z = Math.max(0.4, Math.min(availW/CW, availH/CH, 4));
  stage.style.width = Math.round(CW*z)+'px';
  stage.style.height = Math.round(CH*z)+'px';
}
addEventListener('resize', fitStage);

const atlas = new Image(), origAtlas = new Image();
let ready = 0;
atlas.onload = origAtlas.onload = () => { if (++ready === 2){ fitStage(); renderList(); } };
atlas.onerror = () => showErr('atlas failed to load');
origAtlas.onerror = () => showErr('original atlas failed to load');
atlas.src = DATA.atlas; origAtlas.src = DATA.origAtlas;
function showErr(m){ const e=document.getElementById('err'); e.style.display='block'; e.textContent='Error: '+m; }
window.onerror = (m,s,l) => showErr(m+' (line '+l+')');

const frames = n => anims[n] ? anims[n].frames : [];
const has    = n => !!anims[n];
const fps    = n => anims[n] ? anims[n].speed*60 : 6;
const loops  = n => anims[n] ? anims[n].loop : false;
const dur    = n => Math.max(20, Math.round(frames(n).length / (fps(n)/60)));

// ---- player state (constants mirror the engine) ----
const COMBO = ['attack_1','attack_2','attack_3'];
const P = {
  wx:CW/2, wz:0, vy:0, onFloor:true, facing:1, anim:'idle', frameT:0,
  jumpH:0, attacking:false, combo:0, comboTimer:0, locked:0, dead:false, inspect:false,
};
function setAnim(n){
  if(!has(n)) n='idle';
  if(P.anim!==n){ P.anim=n; P.frameT=0; }
}
function reset(){
  Object.assign(P,{ wx:CW/2, wz:0, vy:0, onFloor:true, facing:1, anim:'idle', frameT:0,
    jumpH:0, attacking:false, combo:0, comboTimer:0, locked:0, dead:false, inspect:false });
  document.getElementById('run').style.background='';
  runToggle=false;
}
const doneGround = () => P.frameT >= (frames(P.anim).length||1);

// ---- input ----
const keys = {}, pressed = {};
let attackHeld = false;
function press(c){ P.inspect=false; if(P.locked>1e6) P.locked=0; pressed[c]=true; }
function bindHold(id, code){
  const b=document.getElementById(id);
  const on=()=>{ P.inspect=false; keys[code]=true; }, off=()=>{ keys[code]=false; };
  b.addEventListener('mousedown',on); b.addEventListener('mouseup',off); b.addEventListener('mouseleave',off);
  b.addEventListener('touchstart',e=>{e.preventDefault();on();}); b.addEventListener('touchend',off);
}
bindHold('left','L'); bindHold('right','R'); bindHold('up','U'); bindHold('down','D');
let runToggle=false;
document.getElementById('run').onclick=()=>{ runToggle=!runToggle;
  document.getElementById('run').style.background = runToggle ? '#3f6fb0' : ''; };
function holdAttack(id, withJump){
  const b=document.getElementById(id);
  const on=()=>{ P.inspect=false; attackHeld=true; press('A'); if(withJump){ press('J'); } };
  const off=()=>{ attackHeld=false; };
  b.addEventListener('mousedown',on); b.addEventListener('mouseup',off); b.addEventListener('mouseleave',off);
  b.addEventListener('touchstart',e=>{e.preventDefault();on();}); b.addEventListener('touchend',off);
}
document.getElementById('jump').onclick=()=>press('J');
holdAttack('attack', false); holdAttack('jattack', true);
document.getElementById('magic').onclick=()=>press('M');
document.getElementById('special').onclick=()=>act('attack_special');
document.getElementById('hit').onclick=()=>act('stunned_1');
document.getElementById('knock').onclick=()=>act('knock_down');
document.getElementById('die').onclick=()=>{ P.dead=true; P.locked=0; setAnim('dying'); };
function act(n){ if(P.dead||!P.onFloor) return; P.inspect=false; P.attacking=false; P.locked=dur(n); setAnim(n); }
document.getElementById('replay').onclick=reset;
let playing = true;
document.getElementById('play').onclick=e=>{ playing=!playing; e.target.textContent=playing?'Pause':'Play'; };

addEventListener('keydown', e=>{
  const k=e.key;
  if(k==='ArrowLeft'){keys.L=true;} else if(k==='ArrowRight'){keys.R=true;}
  else if(k==='ArrowUp'){keys.U=true;} else if(k==='ArrowDown'){keys.D=true;}
  else if(k==='Shift'){keys.run=true;}
  else if(k==='p'||k==='P'){ if(!e.repeat) press('J'); }
  else if(k==='o'||k==='O'){ attackHeld=true; if(!e.repeat) press('A'); }
  else if(k==='i'||k==='I'){press('M');}
  else if(k==='b'||k==='B'){ attackHeld=true; if(!e.repeat){ press('J'); pressed['A']=true; } }
  else return;
  e.preventDefault();
});
addEventListener('keyup', e=>{
  const k=e.key;
  if(k==='ArrowLeft')keys.L=false; else if(k==='ArrowRight')keys.R=false;
  else if(k==='ArrowUp')keys.U=false; else if(k==='ArrowDown')keys.D=false;
  else if(k==='Shift')keys.run=false;
  else if(k==='o'||k==='O'||k==='b'||k==='B')attackHeld=false;
});

// ---- one 1/60 s simulation tick ----
function step(){
  if(P.dead){ if(P.anim!=='dead' && doneGround()) setAnim('dead'); return; }
  if(P.inspect) return;
  if(P.locked>0){
    P.locked--;
    if(P.locked===0){
      if(P.anim==='knock_down'){ setAnim('stand_up'); P.locked=dur('stand_up'); }
      else setAnim('idle');
    }
    return;
  }

  const running = keys.run || runToggle;
  let vx=0, vz=0;
  if(keys.L) vx-=1; if(keys.R) vx+=1;
  if(keys.U) vz-=1; if(keys.D) vz+=1;
  if(vx) P.facing = vx>0 ? 1 : -1;

  if(pressed.J && P.onFloor && !P.attacking){
    P.vy = running ? -DATA.jumpRunSpeed : -DATA.jumpWalkSpeed;
    P.onFloor=false; P.jumpH=0; setAnim('jumping');
  }
  if(pressed.A){
    if(!P.onFloor){ P.attacking=true; setAnim(running ? 'jumping_death_stab' : 'jumping_attack'); }
    else if(!P.attacking){
      setAnim(COMBO[Math.min(P.combo, COMBO.length-1)]);
      P.combo = Math.min(P.combo+1, COMBO.length);
      P.comboTimer = 45; P.attacking = true;
    }
  }
  if(pressed.M && P.onFloor && !P.attacking){ P.locked=dur('magic'); setAnim('magic'); }

  const spd = running ? DATA.runSpeed : DATA.walkSpeed;
  const den = Math.abs(vx)+Math.abs(vz) || 1;
  P.wx += vx/den*spd; P.wz += vz/den*spd;
  P.wx = Math.max(22, Math.min(CW-22, P.wx)); P.wz = Math.max(-40, Math.min(40, P.wz));

  if(!P.onFloor){
    P.vy += DATA.gravity; P.jumpH -= P.vy;
    if(P.jumpH<=0){ P.jumpH=0; P.vy=0; P.onFloor=true; P.attacking=false; }
  }
  if(P.attacking && !attackHeld && P.anim==='jumping_attack'){ P.attacking=false; setAnim('jumping'); }
  if(P.attacking && P.onFloor && doneGround()) P.attacking=false;

  if(P.onFloor && !P.attacking){
    const moving = (vx!==0 || vz!==0);
    if(moving){ if(vz===0 && has('walking_side')) setAnim('walking_side');
                else setAnim(vz>=0 ? 'walking_down' : 'walking_up'); }
    else setAnim('idle');
  }
  if(P.comboTimer>0 && --P.comboTimer===0) P.combo=0;
}

// ---- render ----
let acc=0, last=performance.now();
function advance(dt){
  if(!playing) return;
  const mult = parseFloat(document.getElementById('mult').value) || 1;
  acc += dt*mult;
  let guard=0;
  while(acc >= 1/60 && guard++ < 30){
    acc -= 1/60;
    step();
    P.frameT += fps(P.anim)/60;
    for(const k in pressed) delete pressed[k];
  }
}
function frameIndex(){
  const n = frames(P.anim).length;
  if(n<=1) return 0;
  if(P.anim==='jumping'){
    const v0 = DATA.jumpWalkSpeed;
    const t = Math.max(0, Math.min(1, (P.vy+v0)/(2*v0)));
    return Math.round(t*(n-1));
  }
  return loops(P.anim) ? Math.floor(P.frameT)%n : Math.min(n-1, Math.floor(P.frameT));
}
function drawSprite(img, f, wx, wy, facing){
  if(!img.complete || !f) return;
  if(facing<0){
    ctx.save(); ctx.translate(wx,0); ctx.scale(-1,1);
    ctx.drawImage(img, f.x,f.y,f.w,f.h, f.w-f.cx, wy-f.cy, f.w, f.h);
    ctx.restore();
  } else {
    ctx.drawImage(img, f.x,f.y,f.w,f.h, Math.round(wx-f.cx), Math.round(wy-f.cy), f.w, f.h);
  }
}
function shadow(x,y,scale){ ctx.save(); ctx.globalAlpha=0.25; ctx.fillStyle='#000';
  ctx.beginPath(); ctx.ellipse(x, y+1, 12*scale, 4*scale, 0, 0, Math.PI*2); ctx.fill(); ctx.restore(); }
function draw(){
  ctx.setTransform(1,0,0,1,0,0); ctx.imageSmoothingEnabled=false;
  ctx.fillStyle='#0c0e12'; ctx.fillRect(0,0,CW,CH);
  const groundLine = CH - 28;
  ctx.strokeStyle='rgba(120,120,120,0.15)'; ctx.beginPath();
  ctx.moveTo(0,groundLine+0.5); ctx.lineTo(CW,groundLine+0.5); ctx.stroke();
  const feetY = groundLine - 18 - P.wz*0.5;
  const i = frameIndex(), f = frames(P.anim)[i];
  const lift = P.jumpH;
  shadow(P.wx, feetY, P.onFloor?1:Math.max(0.4,1-lift/70));
  drawSprite(atlas, f, P.wx, feetY-lift, P.facing);

  if(document.getElementById('cmp').checked){
    const oa = DATA.origAnims[P.anim];
    if(oa && origAtlas.complete){
      let oi = loops(P.anim) ? Math.floor(P.frameT)%oa.frames.length : Math.min(oa.frames.length-1, Math.floor(P.frameT));
      const ox = CW/2 - 80;
      shadow(ox, feetY, P.onFloor?1:Math.max(0.4,1-lift/70));
      drawSprite(origAtlas, oa.frames[oi], ox, feetY-lift, P.facing);
      ctx.fillStyle='#6f7f96'; ctx.font='10px monospace';
      ctx.fillText('Ax', ox-12, feetY+16); ctx.fillText('Guybrush', P.wx-26, feetY+16);
    }
  }
  ctx.fillStyle='#bcd'; ctx.font='12px monospace';
  ctx.fillText(P.anim+'  '+(i+1)+'/'+(frames(P.anim).length||1)+
    (P.facing<0?'  (left)':'')+(P.onFloor?'':'  air'), 6, 14);
  document.getElementById('status').textContent =
    P.anim+' · frame '+(i+1)+'/'+(frames(P.anim).length||1)+' · '+
    (P.onFloor?'ground':'airborne')+' · facing '+(P.facing<0?'left':'right');
}
function tick(now){
  const dt = Math.min(0.1, (now-last)/1000); last=now;
  advance(dt); draw(); requestAnimationFrame(tick);
}
function renderList(){
  const el=document.getElementById('list'); el.innerHTML='';
  for(const n of order){
    const b=document.createElement('div');
    b.className='anim'+(n===P.anim?' active':'');
    b.textContent=n;
    b.onclick=()=>{ P.dead=false; P.locked=0; P.attacking=false; P.inspect=true; setAnim(n); P.frameT=0; };
    el.appendChild(b);
  }
}

fitStage();
requestAnimationFrame(tick);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
