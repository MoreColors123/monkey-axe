# HANDOFF — Golden Axe (Java) · Guybrush Threepwood mod

Everything another agent needs to continue this work. Read this top to bottom
before touching anything.

**Docs map:** `HANDOFF.md` (this file) = project + engine + backlog.
`REVIEWER.md` = the sprite reviewer in detail (`tools/guybrush/reviewer.html`).
`GUYBRUSH_MOD.md` = short player-facing summary.

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
The engine reads `/res/...` off the classpath, i.e. `build-custom\res\...`.
`build-custom/` is git-ignored.

> **Asset-copy gotcha (fixed):** the old copy used
> `Copy-Item -Recurse src dst` with `dst` already existing, which nests the
> source as `build-custom\res\res\...` instead of refreshing `build-custom\res`.
> The game kept running stale art even though `assets/res` was edited. `run.ps1`
> now removes the destination first. If a change "isn't showing up", check
> `build-custom\res` isn't a nested `res\res` and that its files match
> `assets/res`.

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
assets/res/chars/guybrush_threepwood.char            (layout copy + new header)
assets/res/chars/guybrush_layout.char                (de-shared layout, if deshare.py was run)
assets/res/image/hud_magic_guybrush_threepwood.png   (copy of Ax's)
assets/res/chars/hud_magic_guybrush_threepwood.char
tools/guybrush/...                                   (see §6)
HANDOFF.md (this file), REVIEWER.md (editor guide),
GUYBRUSH_MOD.md (player-facing summary)
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

`guybrush_threepwood.char` starts as Ax's `.char` with a new header — only the
referenced PNG differs, so every collider/point/state is inherited unchanged. If
`deshare.py` has been run it is instead generated from `guybrush_layout.char`
(de-shared rectangles; colliders/points cloned to the moved frames), still
preserving every collider/point/state.

---

## 5. The baking approach (and why)

`tools/guybrush/build_atlas.py` paints Guybrush art into the frame rectangles of
the layout (`guybrush_layout.char` if present, else `ax_battler.char`) on a fresh
transparent canvas sized to fit (base `600x1000`, grown when de-shared; currently
`654x1053`). Rules that matter:

1. **One source per rectangle, globally.** The Ax layout reuses rectangles both
   across frames in one animation (`attack_5`/`attack_6` = 3 boxes over 8 frames)
   and across animations (`attack_1`/`attack_2`, `thrown`/`stunned_2`/`stand_up`).
   The atlas is keyed by rectangle, so anything pasted there must be identical
   every time. The builder assigns one sprite + size + mode per unique `(x,y,w,h)`
   in first-appearance order; repeats and other animations reuse it. Without this
   a rectangle accumulated two alpha-composited poses — the "doubled sprite" bug.
   A rectangle can be forced with `mapping.json` → `rect_overrides` (§7).
2. **`bottom` mode keeps a constant size**: one scale for the whole animation,
   `min` over its distinct frames of `min(globalScale, cy/spriteH)`. It does
   **not** clamp by width — a wide pose clips at the frame edge instead of
   shrinking the whole body. (Clamping by width caused tiny Guybrush clones to
   pop up mid-attack.) Using a single animation-wide scale also stops a frame
   whose anchor (`cy`) sits higher than its neighbours from popping out larger
   (this was the `stunned_1` "big first frame" bug). `center` poses still fit
   their own box.
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
deshare.py            layout -> de-shared guybrush_layout.char (+ --check / --revert)
patch_select.py       swaps the select-screen portrait (also renamed sprite ax->guybrush)
serve_reviewer.py     local HTTP server for reviewer.html; lets Export save in place
reviewer.html         self-contained visual mapper (embeds everything as data URIs)
```

Typical commands:
```powershell
cd JavaGoldenAxe\tools\guybrush
python detect_sprites.py        # only if the sheet changes
python init_mapping.py          # only to reset the mapping
python make_reviewer.py         # after editing mapping.json, refresh the editor
python deshare.py               # OPTIONAL: give every animation its own rectangles
python build_atlas.py           # bake mapping.json into the game assets
python patch_select.py          # re-skin the select portrait
```

`deshare.py` is a one-time layout change (it writes `guybrush_layout.char`);
run `build_atlas.py` + `make_reviewer.py` afterwards. `deshare.py --check`
verifies hitboxes are preserved and writes nothing; `deshare.py --revert` goes
back to Ax's shared layout.

---

## 7. `mapping.json` schema & semantics

```json
{
  "global_scale": 1.15,
  "face": "s0121",
  "animations": {
    "walking_down": { "mode": "bottom", "frames": ["s0004","s0005","s0006","s0007"] },
    "knock_down":   { "mode": "center", "scale": 1.0, "frames": ["s0316"] }
  },
  "rect_overrides": {
    "176,296,39,55": "s0050",
    "308,685,42,36": { "id": "s0446", "mode": "center", "scale": 0.8 }
  }
}
```

* `frames` = ordered sprite ids from `sprites.json`. If an animation has more
  game frames than source frames, the list loops; one sprite per **distinct
  rectangle** (§5.1).
* `mode`: `bottom` (feet on the anchor) or `center` (lying).
* `scale`: optional per-animation override of `global_scale`.
* `rect_overrides` (optional): keyed by `"x,y,w,h"`, forces the sprite (and
  optionally `mode`/`scale`) baked into one atlas rectangle. Use it when a
  rectangle is shared by several animations and the first animation's choice is
  not the pose you want. After `deshare.py` no rectangle is shared, so overrides
  are rarely needed.
* Missing animation → falls back to `idle`.
* Sprite ids are assigned by `detect_sprites.py`; if the sheet is re-detected,
  ids can shift, so re-check `mapping.json` after re-running it.

Current walk mapping (tuned from the top two sheet rows):
`walking_down` = front-facing walk `s0004..s0007` (row 1),
`walking_up` = back-facing walk `s0017..s0020` (row 2), `idle` = `s0023`, and
`running` = the side walk from row 1 (`s0000,s0001,s0013,s0002,...`).

> **State note:** `mapping.json` is the working copy and changes often. After any
> edit run `BuildSprites.bat` (or `python build_atlas.py`) to bake it into
> `assets/res/image|chars/`, and check the atlas. `python init_mapping.py` resets
> to the original hand-picked mapping.

---

## 8. Using the reviewer (`reviewer.html`)

Open with `ReviewSprites.bat` (it regenerates the page from the current
`sprites.json`/`mapping.json`, starts `serve_reviewer.py` on
`http://127.0.0.1:8765/`, and opens it). The page is self-contained (everything
is embedded as data URIs); the server exists only so Export can write to disk.
The preview mirrors `build_atlas.py`: one source per **distinct** frame
rectangle, and one uniform scale per bottom-mode animation. The UI is split into
**named sections** (use these names when asking for changes): top bar, **Sheet**,
**Animations**, **Rectangles**, **Animation settings**, **Preview**, **Baked
frames**, **Frame list**. Controls:

* Top bar: `Help`, global scale, `Rectangles` (show/hide), `Undo`/`Redo`
  (`Ctrl+Z` / `Ctrl+Y`, also `Ctrl+Shift+Z`), `Reset all`, `Load mapping`,
  `Export mapping.json`.
* **Sheet** = the source sheet with every sprite boxed. Click to select,
  double-click to append the sprite to the current animation, drag to pan, wheel
  to zoom.
* `+ append selected sprite`, `replace frames with selected`, click a thumbnail
  to set that frame, `◀ ▶` reorder, `✕` remove.
* **Rectangles** bar: an inline, collapsible section directly under the animation
  list (the top-bar *Rectangles* button toggles it). It lists every atlas
  rectangle with its owner, the animations that use it and the sprite it bakes;
  select a sheet sprite then `Set` stores `mapping.rect_overrides`. Shared
  rectangles are highlighted and `borrowed` frames are outlined in orange. Since
  `deshare.py` there are no shared rectangles, so it is usually just a read-out.
* **Preview** (original vs new, playing together) and **Baked frames** show **every
  mapped frame**, including frames beyond the game layout — the inherited
  single-frame poses such as `jumping_attack`. Extra frames are drawn in orange and
  labelled `(extra)`; they illustrate the frame list but are not baked unless the
  layout has that many frames (see §10).
* **Help** is a popup (top-bar *Help* button) covering the sections, mode, scale,
  global scale, frames/extras, rectangles and shortcuts, plus a colour key: blue =
  section headings, gold monospace = a field/value/file you can edit (`cy`,
  `scale`, `rect_overrides`), orange = borrowed/extra frames. The "click a box…"
  sheet explainer and the rectangle explanation live here.
* The **Animations** list is auto-height (shows every chip). The JSON textarea and
  `Copy JSON` were removed — Export is the only JSON output.
* `mode` / per-animation `scale`.
* **Animated preview** plays at the animation's real speed (`fps` defaults to
  `animation_speed * 60`, overridable). One-shot animations hold their last
  frame exactly like in-game; tick **loop preview** to make every animation
  repeat while reviewing, and use **Replay** to restart one-shot clips.
* **Undo** (one action), **Reset section** (current animation), **Reset all**.
  "Last state" = last exported/loaded mapping; changed sections show `*`.
* **Export mapping.json** writes straight over
  `JavaGoldenAxe/tools/guybrush/mapping.json`, first copying the previous file
  to `mapping.backup.json` beside it (then run `BuildSprites.bat`). This needs
  the server, so launch via `ReviewSprites.bat`; if you open `reviewer.html`
  directly as a `file://` page there is no server and Export falls back to a
  browser download.

A red error banner appears at the top if the page throws.

---

## 9. Known issues / history of fixes

* **Attack sprites overlapped / showed tiny clones** (reported). Two causes fixed
  in `build_atlas.py` and mirrored in the reviewer's `drawFrameSprite`:
  shared-rectangle collapse and width-driven shrinking. See §5.
* **Doubled sprites on attack / thrown** (reported). A rectangle shared by two
  animations received two different sprites from the per-animation mapping and
  `Image.paste(..., mask)` alpha-composited them into one slot. Fixed by planning
  one sprite+size+mode per rectangle globally (first animation wins), pasting each
  rectangle once, plus `rect_overrides`. See §5.1 and §7.
* **Select portrait: Ax ghost + clipped top/bottom** (reported). `patch_select.py`
  "cleared" Ax by pasting an all-transparent image with itself as the mask, which
  replaces nothing, so Ax showed through; and it scaled Guybrush to 64px tall in a
  64px frame anchored 60px up, so the head was clipped. Fixed by clearing with
  `paste((0,0,0,0), box)` (maskless, stopping before Gilius at x=611) and fitting
  to `min(cy/h, w/w)`.
* **Animated preview blank in Brave**. Brave's fingerprinting protection can
  blank/randomise `canvas.getImageData()`, which the browser used to key the green
  background. Fixed by pre-keying the sheet in `make_reviewer.py` (Python) and
  embedding an already-transparent PNG — the page no longer calls `getImageData`.

## 10. Open issues / ideas (not done)

* Regular attacks reuse front "point/punch" poses; `attack_special` uses the
  raised-cutlass sprites. A better swing sequence could be sourced from the sheet.
* Cross-animation shared rectangles are collapsed to one sprite (the first
  animation in layout order owns the rectangle), so no doubling. The trade-off is
  that a sharing animation may show the owner's pose. Use `rect_overrides` in
  `mapping.json` to force a rectangle's sprite/size/mode. The reviewer lists any
  frames that come from shared rectangles owned by another animation.
* All `mounted_*` states use the plain standing pose (no mounted art exists).
* `magic` uses an arms-up pose; magic effects themselves are unchanged (Ax's volcano).

### Single-frame animations (inherited from the remake)

Several animations have exactly **one** sprite line in Ax's layout, and the
de-share step keeps frame counts identical, so Guybrush inherits the same counts.
Counted across the vanilla characters:

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

To animate any of these you must **add frames to the layout**. The baker already
reads a custom layout (`guybrush_layout.char`) when present, so:

1. Add extra `sprite <anim> RIGHT x y w h cx cy` lines to `guybrush_layout.char`
   using NEW rectangles in unused atlas space, plus optional `collider ATTACK ...`
   for the new frames. (The current `running_attack` rectangle already has an
   attack box at `(269,210,9,48)`.) Run `deshare.py` first if it does not exist.
2. Add the new art rectangles to `mapping.json` so the reviewer can pick them.

Do **not** edit `ax_battler.char` for this; that would change the vanilla
character. Nothing here is required for the mod to work — it is purely a
fidelity improvement. The reviewer previews extra mapped frames already
(`REVIEWER.md`), they just do not bake until the layout has the rectangles.
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
* Frame rectangles must not be moved **in place** (hitboxes attach by intersecting
  the rectangle). Everything normally works by swapping the referenced image
  pixels only. `deshare.py` is the one exception: it relocates rectangles and
  clones their colliders/points, verified by `deshare.py --check`.
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
| Reviewer server (in-place save) | `tools/guybrush/serve_reviewer.py` |
| De-share layout tool | `tools/guybrush/deshare.py` |
| De-shared layout (optional) | `assets/res/chars/guybrush_layout.char` |
| Baker | `tools/guybrush/build_atlas.py` |
| Sprite catalog | `tools/guybrush/sprites.json` |
| Player enum | `src/actor/Player.java` |
| Engine loader | `src/infra/Resource.java` |
| Select screen | `src/scene/SelectPlayer.java` |
| Reviewer guide | `REVIEWER.md` |
| Mod summary (user-facing) | `GUYBRUSH_MOD.md` |

---

## 14. Backlog / next steps

**If the user says "proceed", start at the first unchecked item below**, one
item at a time, and tick it off here as it is done.

### Already fixed
- [x] Reviewer: uniform scale per bottom animation (fixes `stunned_1` big first frame).
- [x] Reviewer: preview mirrors the baker (distinct-rectangle assignment).
- [x] Reviewer: double-click a sheet sprite to append it to the current animation.
- [x] Reviewer: Export saves `mapping.json` in place + `mapping.backup.json` (via `serve_reviewer.py`).
- [x] Baker: one sprite+size+mode per rectangle globally (first animation wins) — fixes doubled attack/thrown sprites. `rect_overrides` added.
- [x] `patch_select.py`: real clear (no-op mask bug) + fit inside the frame — fixes Ax ghost + clipped portrait.
- [x] `run.ps1`: fixed `Copy-Item -Recurse` nesting that left the game running stale assets.
- [x] Reviewer: **original (Ax) animation preview beside the new one** (embedded
  `ax_battler.png` + original layout `origGa`), both playing at the same frame.
- [x] Reviewer: **draggable splitter** between the sheet and the panel (the
  animation list is also taller); double-click resets to 430px.
- [x] Reviewer: **tooltips + a Help block** explaining `mode` (bottom/center),
  per-animation `scale`, `global scale`, and rectangles.
- [x] Reviewer: toast feedback on rectangle override Set/Clear.
- [x] Reviewer: preview/filmstrip/"all animations" show **every mapped frame**,
  including the inherited single-frame poses (`jumping_attack`, `running_attack`,
  `jumping_death_stab`, ...) that the layout has only one rectangle for. Extra
  frames are orange and labelled `(extra)`; the counter reads e.g.
  `1 game frame(s), 3 shown (2 extra from the frame list)`.
- [x] Reviewer: the Rectangles editor is now an **inline collapsible bar** directly
  under the animation list (top-bar button toggles it), not a modal overlay.
- [x] Reviewer: bars auto-size; the animation list shows every chip (auto height).
- [x] Reviewer: **Help** is a top-bar button opening a popup with a reviewed,
  colour-keyed write-up; the "click a box…" sheet explainer and the rectangles
  explanation moved into it.
- [x] Reviewer: **named sections** — Sheet, Animations, Rectangles, Animation
  settings, Preview, Baked frames, Frame list.
- [x] Reviewer: **Undo/Redo** stacks with `Ctrl+Z` / `Ctrl+Y` (and `Ctrl+Shift+Z`).
- [x] Reviewer: removed **Preview all animations**, the JSON textarea and
  `Copy JSON` (Export is the only JSON output).

### Phase 1 — Shared rectangles (the chosen pain point)
- [x] **1a.** Reviewer "Rectangles" panel (button in the top bar). Lists every
  atlas rectangle with its owner, the animations that use it, the sprite it
  currently bakes (thumbnail + id) and any override. Select a sprite on the
  sheet, then `Set` writes `mapping.rect_overrides["x,y,w,h"] = "sNNNN"`; `Clear`
  removes it. `borrowed` marks a frame whose rectangle is owned by another
  animation, and the filmstrip outlines those frames in orange. "Only rectangles
  used by the current animation" filter. (57 rectangles, 15 shared at time of
  writing.)
- [x] **1b.** De-share tool (`deshare.py`). Rewrites the layout into
  `chars/guybrush_layout.char`: the first animation to use a rectangle keeps it,
  later animations get fresh rectangles allocated in free space to the right of
  all geometry, and the `collider`/`point` lines that attach to a moved
  rectangle are cloned (translated). `build_atlas.py` reads the de-shared layout
  when present and sizes the canvas dynamically (now 654×1053). `deshare.py
  --check` verifies every frame keeps the same colliders/points before writing;
  `--revert` removes the layout. Result: **0 shared rectangles**, so per-animation
  editing in the reviewer is now unambiguous (17 rectangles were split). The
  "original (Ax)" preview uses `origGa` from `ax_battler.char` so it still works.

### Phase 2 — Attack fidelity
- [ ] Map coherent swing sequences for `attack_1..7`, `attack_short`,
  `attack_special`, `attack_special_return` (currently a few front "point/punch"
  poses; `attack_special` uses the raised-cutlass sprites).
- [ ] `running_attack`, `jumping_attack`, `jumping_death_stab` are single held
  poses; to animate them, add frames to the layout (see §10). The reviewer now
  previews the full mapped frame list for these, but the extra frames only bake
  once the layout actually has that many rectangles.

### Phase 3 — Held / reaction states
- [ ] Proper collapse/lying poses for `stunned_1/2`, `knock_down`, `stand_up`,
  `thrown`, `dying`, `dead`, `resting`.

### Phase 4 — Mounted & magic
- [ ] `mounting` / `mounted_*`: no mounted art; decide (reuse a sit/crouch pose or leave standing).
- [ ] `magic`: pose + decide whether to replace Ax's volcano effect (`magic_fire_*.ani`).

### Phase 5 — Presentation
- [ ] Select screen: verify name/portrait; consider a nicer full-body pose.
- [ ] Ending cutscene (`ending.ani`): verify Guybrush appears and dialogue reads right.
- [ ] HUD: verify `logo` portrait + `hud_magic_guybrush_threepwood`.
- [ ] Sounds: `.char` still plays Ax's `hit`/`hit_rap`; optionally remap.

### Phase 6 — Robustness & docs
- [ ] Headless "render every animation" contact sheet + one-command
  "rebuild assets + game" script.
- [ ] Keep this file current; commit atomically.

### Where an agent can help most
- Reviewer Rectangles panel + shared-rect highlighting + one-click override (1a).
- Headless all-animation audit / labelled candidate contact sheets.
- De-share tool (1b).
- Source/curate attack and special poses from the sheet.
- Add layout frames/colliders for the single-frame specials.

### Shared-rectangle solution (agreed direction)
The atlas has one slot per rectangle and the layout reuses slots across
animations, so a shared slot holds exactly one sprite. Recommended: **Option 1
(1a)** — edit the *rectangle*, not the animation, via `rect_overrides` with a
reviewer panel. Fallback for full per-animation freedom: **Option 2 (1b)** —
de-share the layout.
