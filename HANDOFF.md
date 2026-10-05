# HANDOFF — Golden Axe (Java) · Guybrush Threepwood mod

Everything another agent needs to continue this work. Read this top to bottom
before touching anything.

---

## 1. Goal

Replace **Ax Battler** in the Java Golden Axe remake (codebase:
`derek-keeler/GoldenAxeClone`) with **Guybrush Threepwood** from *Monkey Island 2:
LeChuck's Revenge*, using the sprite sheet:

<https://www.spriters-resource.com/pc_computer/monkeyisland2/asset/24322/>
(ripped by **Ultimecia** — keep the credit).

Right now Guybrush is the first/leftmost player character (the slot that used to
be Ax), on the select screen, in-stage, in the HUD, and in the ending cutscene.

---

## 2. Environment & how to run things

| Thing | Value |
| --- | --- |
| Repo root | `C:\opencode\goldenaxeswitch\GoldenAxeClone` |
| Branch | `guybrush-mod` |
| Java | Temurin **17** (`javac`/`java` on PATH) |
| Ant | **not installed** — do not rely on `ant`; use `run.ps1` |
| Python | `C:\Program Files\Inkscape\bin\python.exe` (first on PATH) with **Pillow + numpy** |
| Workspace scratch | `C:\opencode\goldenaxeswitch\work` (NOT part of the repo) |

Launchers (double-click, all in the repo root):

* `GoldenAxe.bat` — builds (first time) and plays.
* `ReviewSprites.bat` — regenerates and opens `reviewer.html` (the sprite mapper).
* `BuildSprites.bat` — bakes `mapping.json` into the game sprites.
* `run.ps1` — the engine behind the bats; `.\run.ps1 -Rebuild` forces recompile.

`run.ps1` compiles all `src/**.java` into `JavaGoldenAxe/build-custom/` and
**always re-copies** `assets/res` there, so asset edits show up on next launch.
`build-custom/` is git-ignored.

> There is **no browser-automation step**. If you need to inspect the reviewer,
> open `reviewer.html` yourself; don't drive the user's browser.

---

## 3. How the engine loads a character (important)

Read `src/infra/Resource.java` + `src/infra/Animation.java` + `src/infra/Sprite.java`.

* `Resource.getAnimationPlayer(characterId, subtype)` opens
  `assets/res/chars/<characterId>.char`.
* Each line `sprite <anim> <dir> x y w h cx cy` defines a frame: sub-rectangle
  `(x,y,w,h)` of `assets/res/image/<characterId>.png`, plus an **anchor**
  `(cx,cy)`. The sprite is drawn so that the anchor pixel sits on the actor's
  world position (for grounded poses, the anchor is at the feet).
* The **same `.char` file** also contains the collider list and grab-point list
  (`collider ...`, `point ...`) as absolute coordinates. When a frame is built,
  any collider/point that intersects the frame's rectangle is attached to that
  frame, relative to the sprite. **This is why we must not move frame
  rectangles** — doing so breaks hitboxes and grab points.
* Animations are only registered if present; the available names drive which
  states exist (`Actor.createAllAvailableStates`). Player animation names:
  `idle`, `walking_down`, `walking_up`, `running`, `running_attack`, `jumping`,
  `jumping_attack`, `jumping_death_stab`, `attack_1..7`, `attack_special`,
  `attack_special_return`, `attack_short`, `grab_and_throw`, `thrown`, `stunned_1/2`,
  `knock_down`, `stand_up`, `mounting`, `mounted_*`, `resting`, `magic`, `dying`, `dead`.
  `walking_down` = toward camera (front-facing), `walking_up` = away (back-facing).

Player-character wiring:

* `src/actor/Player.java` → `enum PlayerCharacter { GUYBRUSH("guybrush_threepwood",6), TYRIS, GILIUS }`.
* `src/infra/Actor.java` → `UsingMagic` switch (GUYBRUSH uses Ax's volcano magic).
* `src/scene/SelectPlayer.java` + `assets/res/chars/select_player.char` + `select_player.png`.
* HUD logo + magic come from the character itself (`logo` frame, `hud_magic_<id>`).
* `assets/res/anim/ending.ani` → the ending actors.

---

## 4. What the mod adds / changes

New:
```
assets/res/image/guybrush_threepwood.png
assets/res/chars/guybrush_threepwood.char            (copy of ax_battler.char + new header)
assets/res/image/hud_magic_guybrush_threepwood.png   (copy of Ax's)
assets/res/chars/hud_magic_guybrush_threepwood.char
tools/guybrush/...                                   (see §6)
HANDOFF.md (this file), GUYBRUSH_MOD.md (player-facing summary)
```

Modified:
```
src/actor/Player.java          AX -> GUYBRUSH
src/infra/Actor.java           magic switch
src/infra/GoldenAxeGame.java   demo character
src/scene/SelectPlayer.java    avatar constant
assets/res/image/select_player.png   Ax portrait -> Guybrush (region ~563,3,52,84)
assets/res/chars/select_player.char  sprite ax -> guybrush
assets/res/anim/ending.ani     add_actor ending ax guybrush_threepwood
run.ps1 / .gitignore / GoldenAxe.bat / ReviewSprites.bat / BuildSprites.bat
```

Guybrush uses Ax's `.char` verbatim **except the first comment line**; only the
referenced PNG differs, so every collider/point/state is inherited unchanged.

---

## 5. The baking approach (and why)

`tools/guybrush/build_atlas.py` paints Guybrush art into Ax's existing frame
rectangles on a fresh `600x1000` transparent canvas. Rules that matter:

1. **One source per distinct rectangle per animation.** The Ax layout reuses
   rectangles across frames (e.g. `attack_5`/`attack_6` = 3 boxes over 8 frames;
   `attack_7`/`attack_short` share all boxes). The atlas is keyed by rectangle,
   so assigning a different sprite per *frame* made them overwrite each other.
   The builder now assigns one sprite per unique `(x,y,w,h)` in first-appearance
   order; repeats reuse it (matching the original art's reuse).
2. **`bottom` mode keeps a constant size**: `scale = min(globalScale, cy/spriteH)`.
   It does **not** clamp by width — a wide pose clips at the frame edge instead of
   shrinking the whole body. (Clamping by width caused tiny Guybrush clones to
   pop up mid-attack.)
3. **`center` mode** (lying poses) fits inside the frame: `min(globalScale, h/H, w/W)`,
   vertically centred.
4. Art is clipped strictly to each frame rectangle, so packed neighbours never bleed.
5. Green background `(0,136,68)` is keyed to transparency with threshold 45.

`face` (in `mapping.json`) is the sprite pasted into the 16×16 `logo` rectangle
for the HUD portrait.

---

## 6. Tool pipeline (`JavaGoldenAxe/tools/guybrush/`)

```
guybrush_source.png   raw MI2 sheet (green background)
sprites.json          every detected sprite: {id,x,y,w,h,row}   (1133 of them)
mapping.json          THE EDITABLE MAP (see §7)
detect_sprites.py     sheet -> sprites.json   (connected components + small merge)
init_mapping.py       reset mapping.json to the original hand-picked mapping
make_reviewer.py      sprites.json + mapping.json + .char -> reviewer.html
build_atlas.py        mapping.json + sprites.json -> game assets
patch_select.py       swaps the select-screen portrait (also renamed sprite ax->guybrush)
reviewer.html         self-contained visual mapper (embeds everything as data URIs)
```

Typical commands:
```powershell
cd JavaGoldenAxe\tools\guybrush
python detect_sprites.py        # only if the sheet changes
python init_mapping.py          # only to reset the mapping
python make_reviewer.py         # after editing mapping.json, refresh the editor
python build_atlas.py           # bake mapping.json into the game assets
python patch_select.py          # re-skin the select portrait
```

---

## 7. `mapping.json` schema & semantics

```json
{
  "global_scale": 1.15,
  "face": "s0121",
  "animations": {
    "walking_down": { "mode": "bottom", "frames": ["s0004","s0005","s0006","s0007"] },
    "knock_down":   { "mode": "center", "scale": 1.0, "frames": ["s0316"] }
  }
}
```

* `frames` = ordered sprite ids from `sprites.json`. If an animation has more
  game frames than source frames, the list loops; one sprite per **distinct
  rectangle** (§5.1).
* `mode`: `bottom` (feet on the anchor) or `center` (lying).
* `scale`: optional per-animation override of `global_scale`.
* Missing animation → falls back to `idle`.
* Sprite ids are assigned by `detect_sprites.py`; if the sheet is re-detected,
  ids can shift, so re-check `mapping.json` after re-running it.

Current walk mapping (tuned from the top two sheet rows):
`walking_down` = front-facing walk `s0004..s0007` (row 1),
`walking_up` = back-facing walk `s0017..s0020` (row 2), `idle` = `s0023`, and
`running` = the side walk from row 1 (`s0000,s0001,s0013,s0002,...`).

> **State note:** `mapping.json` currently contains edits to
> `jumping`, `jumping_attack`, `thrown`, `resting`, `dying` (made at ~15:06) that
> are **not yet baked into `assets/res/...`**. Run `BuildSprites.bat` to apply
> them, or `python init_mapping.py` to reset first. Verify the atlas after baking.

---

## 8. Using the reviewer (`reviewer.html`)

Open with `ReviewSprites.bat` (it regenerates the page from the current
`sprites.json`/`mapping.json`, then opens it). No server needed — everything is
embedded as data URIs. Controls:

* Left = the sheet with every sprite boxed. Click to select, drag to pan, wheel to zoom.
* Right = animation list + editor.
* `+ append selected sprite`, `replace frames with selected`, click a thumbnail
  to set that frame, `◀ ▶` reorder, `✕` remove.
* `mode` / per-animation `scale`.
* **Animated preview** plays at the animation's real speed (`fps` defaults to
  `animation_speed * 60`, overridable). One-shot animations hold their last
  frame exactly like in-game; tick **loop preview** to make every animation
  repeat while reviewing, and use **Replay** to restart one-shot clips.
* **Undo** (one action), **Reset section** (current animation), **Reset all**.
  "Last state" = last exported/loaded mapping; changed sections show `*`.
* **Export mapping.json** downloads the file — save it over
  `JavaGoldenAxe/tools/guybrush/mapping.json`, then run `BuildSprites.bat`.

A red error banner appears at the top if the page throws.

---

## 9. Known issues / history of fixes

* **Attack sprites overlapped / showed tiny clones** (reported). Two causes fixed
  in `build_atlas.py` and mirrored in the reviewer's `drawFrameSprite`:
  shared-rectangle collapse and width-driven shrinking. See §5.
* **Animated preview blank in Brave**. Brave's fingerprinting protection can
  blank/randomise `canvas.getImageData()`, which the browser used to key the green
  background. Fixed by pre-keying the sheet in `make_reviewer.py` (Python) and
  embedding an already-transparent PNG — the page no longer calls `getImageData`.

## 10. Open issues / ideas (not done)

* Regular attacks reuse front "point/punch" poses; `attack_special` uses the
  raised-cutlass sprites. A better swing sequence could be sourced from the sheet.
* Cross-animation shared rectangles (e.g. `(308,685)` used by
  `thrown`/`stunned_2`/`stand_up`) can cross-talk: whichever animation is baked
  last wins, so one of them may show an odd pose. Consider a rect→source override
  table if this matters.
* All `mounted_*` states use the plain standing pose (no mounted art exists).
* `magic` uses an arms-up pose; magic effects themselves are unchanged (Ax's volcano).

### Single-frame animations (inherited from the remake)

Several animations have exactly **one** sprite line in Ax's layout, and
`guybrush_threepwood.char` is a byte-for-byte copy of it, so Guybrush inherits
the same counts. Counted across the vanilla characters:

| Animation | Ax | Gilius | Tyris | Guybrush |
| --- | --- | --- | --- | --- |
| `running_attack` | 1 | 1 | 1 | 1 |
| `jumping_attack` | 1 | 1 | 1 | 1 |
| `jumping_death_stab` | 1 | 1 | 1 | 1 |
| `stand_up` | 1 | 3 | 1 | 1 |
| `mounting`, `mounted_side/_flip`, `mounted_down/_flip`, `mounted_up/_flip` | 1 | 1 | 1 | 1 |
| `resting`, `dead` | 1 | 1 | 1 | 1 |

These poses are **held for a code-timed window**, not animated frame-by-frame:

* `running_attack` — `Actor.Running.fixedUpdate` (~line 1527) sets it once,
  applies `vy = -3.0` and a boosted `vx`, and holds the pose for the whole lunge
  until `vy == 0` (then it switches back to `walking`).
* `jumping_attack` — `Actor.Jumping.fixedUpdate` (~line 1582) shows it for
  ~90 ms, then switches to `jumping_death_stab` (if running) or back to `jumping`.
* `jumping_death_stab` — a single held pose.

To animate any of these you must **add frames to the layout**. Note this is a
design decision, because `build_atlas.py` currently parses `ax_battler.char` as
the frame layout and writes `guybrush_threepwood.char` as a copy of it:

1. Add extra `sprite <anim> RIGHT x y w h cx cy` lines using NEW rectangles in
   unused atlas space, plus optional `collider ATTACK ...` for the new frames.
   (The current `running_attack` rectangle already has an attack box at
   `(269,210,9,48)`.)
2. Give the baker a layout source that can carry those extra frames — e.g. a
   hand-maintained `guybrush_layout.char` template read instead of Ax's `.char`.
3. Add the new art rectangles to `mapping.json` so the reviewer can pick them.

Do **not** edit `ax_battler.char` for this; that would change the vanilla
character. Nothing here is required for the mod to work — it is purely a
fidelity improvement.
* The reviewer only previews the RIGHT direction; the engine mirrors for LEFT
  (`Sprite.draw` flips), so that's usually fine.
* Select-screen name is `GUYBRUSH` (rendered by the bitmap font).

---

## 11. Verification workflow

1. **Compile + run:** `.\run.ps1` (or `GoldenAxe.bat`). Needs a display.
2. **Headless asset check** (no display): the scratch Java harnesses in
   `C:\opencode\goldenaxeswitch\work` (`TestRender.java`, `AttackRender.java`,
   `TestEnding.java`) load the character via `Resource.getAnimationPlayer(...)`
   and render frames/filmstrips with `Animation.draw(...)`. To reuse:
   ```powershell
   $out='C:\opencode\goldenaxeswitch\work\out'
   # compile once:  javac -d $out (all src\**\*.java)
   Copy-Item -Recurse -Force JavaGoldenAxe\assets\res "$out\res"
   javac -cp $out -d $out C:\...\work\AttackRender.java
   java -cp $out AttackRender C:\...\work\out.png idle walking_down walking_up
   ```
   `AttackRender` takes the output PNG then any number of animation names.
3. **In game:** title → `1P START` → select `GUYBRUSH` (`O`) → Stage 1. The
   opening dialogue runs a while; attack with `O`, jump `P`, magic `I`.
   (Taking screenshots was done earlier via PowerShell `CopyFromScreen`; don't
   automate the user's browser.)

---

## 12. Gotchas

* `.char` files hold sprites **and** colliders **and** points in one file.
* The `logo` frame is drawn at a fixed HUD position, ignoring its anchor — it's
  just a 16×16 portrait.
* Frame rectangles must not be moved (hitboxes). Everything works by swapping the
  referenced image pixels only.
* `build-custom/` and `sprites_overview.png` are git-ignored; Windows "` - Kopie`"
  duplicates are too (`* - Kopie.*`).
* `.gitattributes`/CRLF warnings on commit are harmless.
* `detect_sprites.py` uses a BFS over ~0.8M foreground pixels — takes a few seconds.

---

## 13. Key files quick reference

| Purpose | Path |
| --- | --- |
| Character layout / hitboxes | `assets/res/chars/guybrush_threepwood.char` |
| Character art | `assets/res/image/guybrush_threepwood.png` |
| Edit the map | `tools/guybrush/mapping.json` |
| Visual mapper | `tools/guybrush/reviewer.html` |
| Baker | `tools/guybrush/build_atlas.py` |
| Sprite catalog | `tools/guybrush/sprites.json` |
| Player enum | `src/actor/Player.java` |
| Engine loader | `src/infra/Resource.java` |
| Select screen | `src/scene/SelectPlayer.java` |
| Mod summary (user-facing) | `GUYBRUSH_MOD.md` |
