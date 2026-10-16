# HANDOFF — Golden Axe (Java) · Guybrush Threepwood mod

Everything another agent needs to continue this work. Read this top to bottom
before touching anything.

**Docs map:** `HANDOFF.md` (this file) = project + engine + tools + backlog.
`REVIEWER.md` = the sprite reviewer in detail (`tools/guybrush/reviewer.html`).
`GUYBRUSH_MOD.md` = short player-facing summary.

---

## 0. Status, and the ship checklist (READ FIRST)

### Where the mod stands

Everything in the mod works and has been verified headlessly and in play:

* **Guybrush is the first player character** — select screen, in stage, HUD,
  ending (Phases 1–5 in §14 are done).
* **Mounting is finished, art included.** The riding pose is no longer a
  walking-frame stand-in: it is a real pose, **placed by hand on the beasts**
  with a purpose-built drag editor (`ReviewMount.bat`, §6b), then applied and
  numerically verified. All 6 `mounted_*` animations use `mode: "place"` with a
  per-animation offset/scale, and the two `*_flip` animations are mirrored (§5.6).
* **Boot stage-select** (`1`–`9` + ENTER) and a **test arena** in Stage 1 with one
  of each mountable beast next to the spawn (§2).
* **Draw order fixed** (§9): a player at the same depth as an enemy or corpse used
  to be drawn *behind* it; that is fixed, and a corpse killed off a beast now
  falls to the floor behind the beast instead of hanging in front of the rider.
* **The dragon-riding crash of §0-old is gone** — root-caused and guarded
  (`Actor.getCurrentFrameColliders()` returns an empty list when there is no
  current animation). Ridden for a full session with no recurrence.

### Ship checklist — DONE (shipped state)

1. ~~**Remove the temporary mount diagnostics**~~ — DONE.
2. ~~**Revert the test arena**~~ — DONE. The three beast `SPAWN` lines in
   `assets/res/stage/stage_1.inf` are commented again; the cheat menu's
   **MOUNT BEAST** spawns one for testing instead.
3. ~~**Turn the boot/test toggles off**~~ — DONE. `TEST_BOOT_TO_GAME = false`
   (normal boot: OL Presents → disclaimer → winners → title → select → intro →
   Stage 1), `SKIP_INTRO = false`, `DEBUG_STATE_SWITCH = false`. The cheat toggles
   (`TEST_AUTO_KILL_ENEMIES`, `TEST_NO_THIEVES`, `TEST_INVINCIBLE`) stay, driven
   only by the hidden **`ape`** menu.
4. ~~**Decide the fate of the mount gate.**~~ — DONE. Players always can mount.
5. ~~**Restore Stage 1's walk-in + opening dialogue**~~ — DONE (the two
   `walk_to ... show_start_dialog_text` spawns are active again).
6. ~~**Rebuild**~~ — `build-custom/` is deleted; the next `scripts\GoldenAxe.bat`
   recompiles and re-copies assets.
7. **Commit** — the working tree holds the whole mod; see §14.

### Release build (how another PC runs it)

```powershell
.\scripts\run.ps1 -Rebuild        # play locally (needs a JDK)
.\scripts\BuildRelease.bat        # or: powershell -File make_release.ps1
```

`make_release.ps1` compiles `src/**` + copies `assets/res` into a single
`GoldenAxe.jar` **in the repo root** (Main-Class `main.Main`, assets at
`/res/...` on the classpath). There is no `dist/` folder any more: ship the root
jar (or the GitHub release asset). The target PC
needs only a **Java 17 runtime** (`java -version` → 17+) and then double-clicks
`Play.bat` (or runs `java -jar GoldenAxe.jar`). No JDK, Ant, Python or assets
folder is required. For a fully bundled runtime (no Java install at all) use
`jpackage --input dist --main-jar GoldenAxe.jar --main-class main.Main
--type app-image --name GoldenAxe` (per-platform).

### Known open issues (details in §10)

* Sort order still keys on `wz` alone, while the drawn position is `wy + wz`, so
  occlusion can disagree with the picture on slopes/ledges. Fix "C" in §10 is
  written up but deliberately not applied.
* `magic` still plays Ax's volcano effect; sound is still Ax's `hit`/`hit_rap`.
* Single-frame specials (`running_attack`, `jumping_attack`, `jumping_death_stab`)
  are still held poses — animating them needs extra layout rectangles (§10).

---

## 1. Goal

Replace **Ax Battler** in the Java Golden Axe remake (codebase:
`derek-keeler/GoldenAxeClone`) with **Guybrush Threepwood** from *Monkey Island 2:
LeChuck's Revenge*, using the sprite sheet:

<https://www.spriters-resource.com/pc_computer/monkeyisland2/asset/24322/>
(ripped by **Ultimecia** — keep the credit).

Guybrush is the first/leftmost player character (the slot that used to be Ax), on
the select screen, in-stage, in the HUD, and in the ending cutscene.

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

Launchers (double-click; `Play.bat` lives in the repo root, the rest in `scripts/`):

* `scripts\GoldenAxe.bat` — builds (first time) and plays.
* `scripts\ReviewSprites.bat` — regenerates and opens `reviewer.html` (the sprite mapper).
* `scripts\ViewAnimations.bat` — regenerates and opens `viewer.html`: a playable sandbox
  for the baked character (move, run, JUMP, ATTACK, JUMP+ATTACK, magic, hit, die).
* `scripts\BuildRelease.bat` — rebuilds the shippable `GoldenAxe.jar` in the repo root.
* `scripts\ReviewMount.bat` — regenerates and opens `mount_editor.html`: drag the riding
  pose onto every beast, then Save (`mount_placements.json`).
* `scripts\BuildSprites.bat` — bakes `mapping.json` into the game sprites.
* `scripts\run.ps1` — the engine behind the bats; `.\scripts\run.ps1 -Rebuild` forces recompile.

> **Never launch the game yourself.** `scripts\GoldenAxe.bat`/`scripts\run.ps1` open a GUI window
> on the user's desktop. Ask the user to start the game and to test; do not run
> it as an agent step. (Same for the two review bats — don't drive the user's
> browser. An in-app/headless browser of your own for checking your own work is
> fine.)

Testing toggles (in `src/infra/GoldenAxeGame.java`) and their **current** values:

* `TEST_BOOT_TO_GAME = false` — normal boot (OL Presents → disclaimer → winners
  → title → select → intro → Stage 1).
* `SKIP_INTRO = false` — the title's attract intro plays as usual.
* `DEBUG_STATE_SWITCH = false` — no console spam.

### The cheat menu (`infra/CheatMenu.java`)

The loose in-game cheat keys are gone. Instead, **type the magic word `ape`**
anywhere — the menu overlay opens and pauses the active scene. Navigate with
UP/DOWN, toggle/activate with ENTER, close with ESC (or `ape` again):

* **STAGE SELECT** — jumps to the stage-select prompt (`scene/StageSelect.java`):
  type `1`–`9`, ENTER to start there as Guybrush.
* **MOUNT BEAST** — spawns a `chicken_leg` **resting** just beside the player
  (`Stage.spawnMountBeast`), so beast mounting can be tested in any stage now
  that the Stage 1 test arena is gone.
* **AUTO-KILL ENEMIES** (`TEST_AUTO_KILL_ENEMIES`, default off) — every enemy
  dies 3 s after spawn; **beasts are skipped** so mounts survive, and killing a
  **mounted** rider calls `unmount()` so the beast drops to `resting`
  (mountable), and the corpse is put on the floor behind the beast (§9).
  `Actor.forceKill`.
* **NO THIEVES** (`TEST_NO_THIEVES`, default off) — the mana/food **thieves**
  never spawn in any stage and existing ones are swept (`Command` SPAWN skips
  `Thief` and releases its camera lock). Global.
* **INVINCIBLE PLAYER** (`TEST_INVINCIBLE`, default off) — the players cannot be
  hit (`Actor.isInvincible` returns true for `PLAYER_1`/`PLAYER_2`).

The **test arena** and Stage 1's skipped walk-in are **reverted** for shipping
(§0): the beast spawns and the `walking` player spawns in `stage_1.inf` are
commented again, the `walk_to ... show_start_dialog_text` intro is active, and
the **MOUNT BEAST** cheat replaces the arena for mount testing.

`run.ps1` compiles all `src/**.java` into `JavaGoldenAxe/build-custom/` and
**always re-copies** `assets/res` there, so asset edits show up on next launch.
The engine reads `/res/...` off the classpath, i.e. `build-custom\res\...`.
`build-custom/` is git-ignored.

> **Asset-copy gotcha (fixed):** the old copy used
> `Copy-Item -Recurse src dst` with `dst` already existing, which nests the
> source as `build-custom\res\res\...`. `run.ps1` now removes the destination
> first. If a change "isn't showing up", check `build-custom\res` isn't a nested
> `res\res` and that its files match `assets/res`.

> There is **no browser-automation step** required. To inspect a review page,
> open it yourself; don't drive the user's browser.

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
  rectangles** — doing so breaks hitboxes and grab points. (The mount rectangles
  are the one safe exception: nothing intersects them, see §5.6/§12.)
* Animations are only registered if present; the available names drive which
  states exist (`Actor.createAllAvailableStates`). Player animation names:
  `idle`, `walking_down`, `walking_up`, `walking_side`, `running`,
  `running_attack`, `jumping`, `jumping_attack`, `jumping_death_stab`,
  `attack_1..7`, `attack_special`, `attack_special_return`, `attack_short`,
  `grab_and_throw`, `thrown`, `stunned_1/2`, `knock_down`, `stand_up`,
  `mounting`, `mounted_*`, `resting`, `magic`, `dying`, `dead`.
  `walking_side` = NEW (mod): profile side-walk for horizontal movement, added
  by an approved engine patch in `Actor.Walking` (plays it when the character
  provides it, else the original walking_down/up behaviour).
  `mounting`/`mounted_*` = NEW art, hand-placed (§5.6) — see §10 for the state
  mechanics.
* Render order: `Stage.draw` sorts `actors` (stable sort) and draws
  shadows then sprites in that order; `Actor.compareTo` decides. See §9/§12.

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
assets/res/chars/guybrush_threepwood.char            (generated from the layout)
assets/res/chars/guybrush_layout.char                (de-shared layout, the source of truth)
assets/res/image/hud_magic_guybrush_threepwood.png   (copy of Ax's)
assets/res/chars/hud_magic_guybrush_threepwood.char
src/infra/CheatMenu.java                             (hidden "ape" cheat-menu overlay)
tools/guybrush/viewer.html, make_viewer.py           (playable move sandbox)
scripts/ViewAnimations.bat                           (double-click the sandbox)
scripts/BuildRelease.bat, scripts/make_release.ps1   (build GoldenAxe.jar in the repo root)
tools/guybrush/...                                   (see §6)
tools/guybrush/mount_editor.html                     (mounted_* placement editor)
tools/guybrush/mount_placements.json                 (the editor's drag results)
tools/guybrush/make_mount_editor.py / serve_mount.py (build / serve that editor)
tools/guybrush/apply_mount.py                        (placements -> mapping + layout)
scripts/ReviewMount.bat                              (double-click the editor)
HANDOFF.md (this file), REVIEWER.md, GUYBRUSH_MOD.md
```

Modified:
```
src/actor/Player.java          AX -> GUYBRUSH
src/infra/Actor.java           magic switch; draw order + forceKill corpse fix (§9);
                               walking_side patch; players always can mount;
                               TEST_INVINCIBLE in isInvincible(); phase-driven
                               `jumping` animation (§10)
src/infra/GoldenAxeGame.java   demo character; test toggles; cheat-menu hook; boot
src/infra/Input.java           rolling typed-character buffer (cheat-menu opener)
src/scene/SelectPlayer.java    avatar constant
src/scene/Stage.java           test arena hooks, auto-kill + no-thieves switches
src/scene/StageSelect.java     stage-select prompt (now reached from the cheat menu)
assets/res/image/select_player.png   Ax portrait -> Guybrush
assets/res/chars/select_player.char  sprite ax -> guybrush
assets/res/anim/ending.ani     add_actor ending ax guybrush_threepwood
assets/res/stage/stage_1.inf   skipped walk-in/dialogue + test arena (revert to ship)
tools/guybrush/mapping.json                (see §7)
tools/guybrush/build_atlas.py              place/flip support
tools/guybrush/make_reviewer.py,reviewer.html  place/offset/mirror in the preview
run.ps1 / .gitignore / GoldenAxe.bat / ReviewSprites.bat / BuildSprites.bat
```

`guybrush_threepwood.char` is generated by `build_atlas.py` from
`guybrush_layout.char` (only the header comment differs), so the layout file is
the thing to edit; the `.char` is an output.

---

## 5. The baking approach (and why)

`tools/guybrush/build_atlas.py` paints Guybrush art into the frame rectangles of
the layout (`guybrush_layout.char`) on a fresh transparent canvas sized to fit
(currently `2505x2166` — it has grown as rectangles were de-shared and the mount
rectangles were resized). Rules that matter:

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
   shrinking the whole body. `center` poses still fit their own box.
3. **`center` mode** (lying poses) fits inside the frame: `min(globalScale, h/H, w/W)`,
   vertically centred.
4. Art is clipped strictly to each frame rectangle, so packed neighbours never bleed.
5. Green background `(0,136,68)` is keyed to transparency with threshold 45.
6. **`place` mode** (the mount animations) takes the sprite, `scale` and
   `offset [dx,dy]` straight from the mapping. `offset` is where the sprite's
   top-left goes **relative to the frame's anchor** — i.e. relative to the point
   the engine pins to the beast's `mounted_*` point. `"flip": true` mirrors the
   pose *about the anchor* (`dx` becomes `-(dx + scaledWidth)`) and is used by
   `mounted_side_flip`/`mounted_up_flip`, whose beast frames are drawn mirrored.
   Both the baker and the reviewer preview implement this identically, and
   `apply_mount.py` sizes the rectangles so the art always fits inside them.

`face` (in `mapping.json`) is the sprite pasted into the 16×16 `logo` rectangle
for the HUD portrait.

---

## 6. Tool pipeline (`JavaGoldenAxe/tools/guybrush/`)

```
guybrush_source.png   raw MI2 sheet (green background)
sprites.json          every detected sprite: {id,x,y,w,h,row}   (~1146 of them)
mapping.json          THE EDITABLE MAP (see §7)
mount_placements.json the mount editor's drag results (per mounted_* animation)
suggestions.json      agent-proposed mappings; the reviewer's Suggestions bar reads them
detect_sprites.py     sheet -> sprites.json   (connected components + small merge)
add_missing_sprites.py  re-detect a band and APPEND sprites without renumbering
fix_jump_sprites.py   attach detached ponytail blobs to the jump poses; split s0262 (+s1146)
init_mapping.py       reset mapping.json to the original hand-picked mapping
make_reviewer.py      sprites.json + mapping.json + .char -> reviewer.html
make_viewer.py        baked .char + .png -> viewer.html (playable move sandbox)
build_atlas.py        mapping.json + sprites.json -> game assets
deshare.py            layout -> de-shared guybrush_layout.char (+ --check / --revert)
make_mount_editor.py  beasts + rider layout + mapping -> mount_editor.html
serve_mount.py        local server for both review pages; saves placements/mapping
apply_mount.py        mount_placements.json -> mapping.json + layout rectangles
patch_select.py       swaps the select-screen portrait (also renamed sprite ax->guybrush)
serve_reviewer.py     local HTTP server for reviewer.html; lets Export save in place
reviewer.html         self-contained visual mapper (embeds everything as data URIs)
viewer.html           self-contained move sandbox (plays the baked character)
mount_editor.html     self-contained mount placement editor
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

### 6b. Placing the riding pose (the mount editor)

The MI2 sheet has no riding pose, so the seated look is achieved by **placing a
chosen pose on the beasts by hand**:

```powershell
cd JavaGoldenAxe\tools\guybrush
python serve_mount.py           # or double-click scripts\ReviewMount.bat
#   drag on each beast cell to position the pose, wheel to scale,
#   click a thumbnail to swap the pose, ⇄ mirror to flip it, then Save placements
python apply_mount.py           # placements -> mapping.json + layout rectangles
python build_atlas.py           # bake
```

* `mount_editor.html` shows **every beast frame that carries a `mounted_*` point**
  (dragon_blue, dragon_red, chicken_leg; 24 beast-frames), with the rider drawn
  exactly the way the engine will draw it. Placement is per **rider animation**
  (`mounted_down`, `mounted_side`, `mounted_up` + `_flip`) and shared across all
  beasts and frames, so the rider cannot drift between them.
* The red crosshair is the beast's `mounted_*` point — the anchor the engine pins
  the rider to. Dragging writes `offset` relative to that point, in atlas pixels.
* **Mirror**: `mounted_side_flip`/`mounted_up_flip` sit on the chicken_leg's
  `attack_1` frames that are drawn mirrored in the sheet (its `attack_1[3]`,`[4]`
  face the other way), so the rider must be mirrored there too. The editor has a
  `⇄ mirror` toggle per animation; `apply_mount.py` records it as `"flip": true`.
* `apply_mount.py` also **resizes the mount rectangles** to fit what you dropped
  (see §12) and runs an overlap check over all rectangles before writing.

---

## 7. `mapping.json` schema & semantics

```json
{
  "global_scale": 1.15,
  "face": "s0121",
  "animations": {
    "walking_down": { "mode": "bottom", "frames": ["s0004","s0005","s0006","s0007"] },
    "knock_down":   { "mode": "center", "scale": 1.0, "frames": ["s0316"] },
    "mounted_side": {
      "mode": "place", "scale": 1.25, "offset": [-20, -30], "frames": ["s0443"]
    },
    "mounted_side_flip": {
      "mode": "place", "scale": 1.15, "offset": [-20, -28], "flip": true,
      "frames": ["s0443"]
    }
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
* `mode`: `bottom` (feet on the anchor) / `center` (lying) / `place` (mount art —
  `offset` + `flip`, see §5.6).
* `scale`: optional per-animation override of `global_scale`. For `place` it is
  the absolute scale.
* `offset` (place only): `[dx,dy]`, the sprite's top-left relative to the frame
  anchor. Produced by the mount editor — don't hand-write it, drag it.
* `flip`: mirror the pose about the anchor. Used by the mount `*_flip` animations
  and by the reaction poses (`knock_down`, `thrown`, `stunned_1/2`) whose source
  art faces the opposite way from Ax's (see §9). The baker applies it for
  **every** mode and the reviewer preview mirrors accordingly.
* `rect_overrides` (optional): keyed by `"x,y,w,h"`, forces the sprite (and
  optionally `mode`/`scale`/`offset`/`flip`) baked into one atlas rectangle. After
  `deshare.py` no rectangle is shared, so overrides are rarely needed.
* Missing animation → falls back to `idle`.
* Sprite ids are assigned by `detect_sprites.py`; if the sheet is re-detected, ids
  can shift, so re-check `mapping.json` after re-running it.

Current walk mapping: `walking_down` = front walk `s0004..s0007`, `walking_up` =
back walk `s0017..s0020`, `idle` = `s0137`, `walking_side` = the row-1 side walk
(`s0000,s0001,s0013,s0001,s0002,s0003,s0014,s0003`), `running` = the same side
walk at a shorter cycle.

Current mount mapping (placed with the editor, applied by `apply_mount.py`):

| animation | pose | scale | offset | rect (after fit) |
| --- | --- | --- | --- | --- |
| `mounted_down` | `s0443` | 1.25 | −31,−33 | 51×58 anchor 32,34 |
| `mounted_down_flip` | `s0004` | 1.15 | 1,1 | 31×57 anchor 1,1 |
| `mounted_side` | `s0443` | 1.25 | −20,−30 | 51×58 anchor 21,31 |
| `mounted_side_flip` | `s0443` | 1.15 | −20,−28 **+mirror** | 47×54 anchor 26,29 |
| `mounted_up` | `s1131` | 1.15 | −30,−23 | 42×55 anchor 31,24 |
| `mounted_up_flip` | `s1126` | 1.05 | −20,−19 | 37×50 anchor 21,20 |

> **State note:** `mapping.json` is the working copy and changes often. After any
> edit run `BuildSprites.bat` (or `python build_atlas.py`) to bake it into
> `assets/res/image|chars/`, and check the atlas. `python init_mapping.py` resets
> to the original hand-picked mapping.

---

## 8. Using the reviewer (`reviewer.html`)

Open with `scripts\ReviewSprites.bat` (it regenerates the page from the current
`sprites.json`/`mapping.json`, starts `serve_reviewer.py` on
`http://127.0.0.1:8765/`, and opens it). The page is self-contained (everything is
embedded as data URIs); the server exists only so Export can write to disk. The
preview mirrors `build_atlas.py`: one source per **distinct** frame rectangle, one
uniform scale per bottom-mode animation, and `place`/`flip` for the mount art.

UI is split into **named sections** (use these names when asking for changes):
top bar, **Sheet**, **Animations**, **Rectangles**, **Animation settings**,
**Preview**, **Baked frames**, **Frame list**.

* Top bar: `Help`, global scale, `Rectangles`, `Undo`/`Redo` (`Ctrl+Z`/`Ctrl+Y`),
  `Reset all`, `Load mapping`, `Export mapping.json`.
* **Sheet** = the source sheet with every sprite boxed. Click to select,
  double-click to append to the current animation, drag to pan, wheel to zoom.
* `+ append selected sprite`, `replace frames with selected`, click a thumbnail to
  set that frame, `◀ ▶` reorder, `✕` remove.
* **Rectangles** bar (collapsible, directly under the animation list) lists every
  atlas rectangle with its owner, the animations that use it and the sprite it
  bakes; select a sheet sprite then `Set` stores `mapping.rect_overrides`.
  Shared rectangles are highlighted, `borrowed` frames outlined in orange. Since
  `deshare.py` there are no shared rectangles, so it is usually a read-out.
* **Suggestions** bar: cards from `suggestions.json` with approve/dismiss/comment,
  persisted through `serve_reviewer.py`. See `REVIEWER.md` §6b.
* **Preview** (original Ax vs new, playing together) and **Baked frames** show
  every mapped frame, including extras beyond the layout (orange, `(extra)`).
* **Animation settings**: `mode` (`bottom`/`center`/`place`), per-animation
  `scale`, and for `place` the `offset` fields plus a `mirror` checkbox — those
  are the mount art's settings; they are *set by dragging* in `mount_editor.html`
  (§6b) and shown here read-only-ish so the two tools can't disagree.
* **Animated preview** plays at the animation's real speed; one-shots hold their
  last frame exactly like in-game (`loop preview` repeats them for review).
* **Export mapping.json** writes straight over `mapping.json`, first copying the
  previous file to `mapping.backup.json`. Needs the server, so launch via
  `scripts\ReviewSprites.bat`; as a `file://` page Export falls back to a download.

A red error banner appears at the top if the page throws.

---

## 9. Known issues / history of fixes

* **Attack sprites overlapped / showed tiny clones** — shared-rectangle collapse
  and width-driven shrinking. Fixed in `build_atlas.py` + the reviewer preview. §5.
* **Doubled sprites on attack / thrown** — one rectangle received two different
  sprites and alpha-composited them. Fixed by planning one sprite+size+mode per
  rectangle globally, plus `rect_overrides`. §5.1.
* **Select portrait: Ax ghost + clipped top/bottom** — `patch_select.py` pasted
  with a no-op mask and mis-scaled. Fixed (§5-style clear + fit inside the frame).
* **Animated preview blank in Brave** — `getImageData()` fingerprinting protection;
  the sheet is now pre-keyed in `make_reviewer.py`.
* **Dragon-riding crash (NPE in `Actor.getCurrentFrameColliders`)** — the temporary
  mount-diagnostic scan dereferenced an actor whose animation was momentarily
  null. Both call sites are now null-safe (`getCurrentFrameColliders()` returns an
  empty list) and no recurrence has been seen in play.
* **Riding pose looked wrong** — the mount animations were baked `mode: bottom`,
  which pins the art's **feet** to the saddle, so Guybrush stood on the dragon at
  full size; and all 7 mount animations shared the same 3 front-walk frames, so he
  faced the camera on a side-on beast. Fixed by hand-placing a real pose per
  animation (`place` mode + mirror, §5.6/§6b) and sizing the mount rectangles to
  fit it.
* **Dead bodies drawn in front of the player** — two causes, both fixed:
  1. `Actor.compareTo` compared `wz` only, and `Collections.sort` is stable, so
     actors at the *same* depth kept insertion order; players are spawned first, so
     any enemy/corpse at the player's exact depth was drawn **over** him. That tie
     is the norm here — the enemy AI steers its `z` to the player's `z` in whole
     pixels. Equal depths now draw the player last.
  2. `forceKill()` (the cheat-menu auto-kill) called `unmount()`, which parks the released
     rider at `beast.wz + 0.01` — *in front of* a live rider on the same beast,
     who only gets `beast.wz + 0.000001` — and still at saddle height. A corpse
     killed off a beast therefore hung in front of whoever rode it next. It now
     falls to the floor **behind** the beast (`beast.wz − 0.01`,
     `wy = Terrain.getHeight(...)`).
  While fixing (1) the old asymmetric epsilon in `compareTo` (`this.wz + az`
  against the other's plain `wz`) was removed: it cancelled out for a mount pair,
  so "rider drawn over its beast" only worked when the beast happened to be first
  in the list. The mount code's own `+1e-6` on the rider's `wz` now orders the
  pair deterministically. Verified with `work/CompareTest.java` (§11).
* **Reviewer: uniform scale per bottom animation**, draggable splitter, tooltips,
  inline Rectangles bar, Undo/Redo, named sections — see §14.
* **Jump poses: detached ponytail missing from the box** — the MI2 sheet draws
  Guybrush's ponytail detached above his head in the jump frames, so it was
  smaller than `MIN_AREA` and dropped: the reviewer/baker showed a headless body,
  and `s0262` was actually two figures merged into one box. `fix_jump_sprites.py`
  folds the hair blob back into `s0261`/`s0256`/`s0249`/`s0250`/`s0257`/`s0262`
  and splits the pair into `s0262` + a new `s1146` (ids never renumbered; the old
  file is kept as `sprites.backup.json`). `s0263`'s ponytail is horizontally
  adjacent and was already merged. Re-run it after any re-detect (it is a no-op
  when the boxes already contain the hair).
* **Jump looked bad / static** — the game's `jumping` animation never advanced,
  so only frames 0 (take-off) and 1 (falling) ever showed and the whole MI2 jump
  sequence was unusable; `jumping_attack`/`jumping_death_stab` were mapped to
  *standing* sword poses. Fixed by giving Guybrush an 8-frame `jumping` (new
  rectangles in the layout) and driving the frame from the physics phase in
  `Actor.Jumping.fixedUpdate`; the two attack poses are now airborne jump poses.
  See §10 for the mechanism.
* **Reaction poses faced the wrong way** — `thrown`, `stunned_1/2` and
  `knock_down` use MI2 sprites drawn facing the opposite direction from Ax's
  (e.g. the lying pose had the head to the right, so a beat-down read as "back
  to the enemy"). Fixed two ways: `"flip": true` on those animations in
  `mapping.json` (so the base art faces like Ax), **and** `Actor.react` now turns
  the actor to face whoever hit it (the engine only ever mirrored by `direction`;
  it never turned the victim, so a hit from behind kept the back to the enemy).
* **Death flicker** — `dying` looped a fall→lie pair at 30 fps (`animation_speed
  0.5`, `animation_loop true`), so a downed character strobed between the two
  sprites. `dying` is now a **single lying frame** (the extra `sprite dying` rect
  was removed; a lethal `knock_down` has already shown the fall), and `dying` +
  `dead` are flipped to match `knock_down`. `resting` unchanged.

## 10. Open issues / ideas (not done)

* **Projected-depth sort (option "C").** `compareTo` still uses `wz` alone while
  the drawn position is `wy + wz` (terrain height + depth), so on slopes/ledges an
  actor that looks further away can still sort in front. The principled fix is to
  sort by `wy + wz`, **with a mounted pair sharing the beast's depth** (the rider's
  `wy` is the saddle height, not the ground, so a naive change draws the beast over
  its rider). Engine-wide; wants its own before/after verification.
* Regular attacks all play the same 3-frame cutlass cycle — `s0321` → `s0322` →
  `s0320`. The sheet's swordfight rows mix props (stick/bone/cutlass), so one
  consistent weapon wins over per-attack variety. `attack_special` keeps its own
  sequence; `attack_special_return` keeps the pointing poses.
* Cross-animation shared rectangles are collapsed to one sprite (first animation in
  layout order owns the rectangle). Use `rect_overrides` to force a choice.
* **Mount mechanics** (for reference): a riderless beast (its `TOUCH MOUNT`
  collider lives on its **`resting`** frame) is mounted by whoever walks into it —
  player or enemy, no gate. The cheat-menu auto-kill makes `Actor.forceKill()`
  call the beast's `unmount()`, dropping it back to `resting` (mountable) and
  putting the corpse on the ground behind it.
  `Actor.spawnTime` + `Stage` drive the 3 s auto-kill; the auto-kill **skips
  beasts**. `Mounted.fixedUpdate` picks the rider's animation from the **beast's**
  frame point name (`mounted_side`, `mounted_down`, `mounted_up`, `*_flip`) — on a
  dragon only `mounted_down` (walking/running/runaway/jumping) and `mounted_side`
  (attack frames) are ever used; the chicken_leg also uses the `*_flip` variants.
* `magic` uses horn-blow poses (`s1142`/`s1145`); the magic *effect* is still Ax's
  volcano.
* Sounds: `.char` still plays Ax's `hit`/`hit_rap`; optionally remap.

### Single-frame animations (inherited from the remake)

Several animations have exactly **one** sprite line in Ax's layout, and the
de-share step keeps frame counts identical, so Guybrush inherits the same counts:

| Animation | Ax | Gilius | Tyris | Guybrush |
| --- | --- | --- | --- | --- |
| `jumping` | 2 | 2 | 2 | **8** (see below) |
| `running_attack` | 1 | 1 | 1 | 1 |
| `jumping_attack` | 1 | 1 | 1 | 1 |
| `jumping_death_stab` | 1 | 1 | 1 | 1 |
| `stand_up` | 1 | 3 | 1 | 1 |
| `mounting`, `mounted_side/_flip`, `mounted_down/_flip`, `mounted_up/_flip` | 1 | 1 | 1 | 1 |
| `resting`, `dead` | 1 | 1 | 1 | 1 |

These poses are **held for a code-timed window**, not animated frame-by-frame:
`running_attack` (`Actor.Running.fixedUpdate` ~1527), `jumping_attack`
(`Actor.Jumping.fixedUpdate` ~1582), `jumping_death_stab` (a single held pose).

**`jumping` is the exception (done).** `Actor.Jumping` used to only ever set
frame 0 (take-off) or frame 1 (falling) and never advanced the animation, so
Guybrush inherited a two-pose hop no matter how many frames were mapped. It now
**drives the frame from the physics phase** — first frame at take-off, middle at
the apex, last at touch-down — so an 8-pose sequence
(`s0261,s0256,s0249,s0250,s0257,s0262,s1146,s0263`) plays against the arc. The 8
rectangles were added to `guybrush_layout.char` (72×90, cy 88, in free atlas
space; the old jumping rectangles had **no collider**, so they are safe to
replace, like the mount rects). An airborne `jumping_attack` is **held while the
attack button is held** — releasing it drops back to the jump pose (the running
`jumping_death_stab`, and enemies, hold until touch-down). Vanilla two-frame
characters still just hop between their two poses (the phase math rounds to
0/1).

To animate the remaining one-frame poses you must **add frames to the layout**:

1. Add extra `sprite <anim> RIGHT x y w h cx cy` lines to `guybrush_layout.char`
   using NEW rectangles in unused atlas space, plus optional
   `collider ATTACK ...` for the new frames.
2. Add the new art rectangles to `mapping.json` so the reviewer can pick them.
3. If the pose should play over time, make the state advance it (see
   `Actor.Jumping.fixedUpdate` for the phase-driven example, or call
   `animationPlayer.update()` like the attack states do).

Do **not** edit `ax_battler.char`. Nothing here is required for the mod to work.
* The reviewer only previews the RIGHT direction; the engine mirrors for LEFT
  (`Sprite.draw` flips), so that's usually fine. **Exception:** the chicken_leg's
  `attack_1` frames that are drawn mirrored in the sheet (they pair with the
  rider's `*_flip` animations) — see §6b.
* Select-screen name is `GUYBRUSH` (rendered by the bitmap font).

### Reviewing all game parts (proposed — not built)

The stage chain is sequential and gated, so a full pass is 30+ minutes. Proposal:
a 3-part harness behind a single `TEST_MODE` flag (default off, revertible):

| Part | Where | What the mod can break |
| --- | --- | --- |
| Stages 1–9 | `stage_N.inf` | walk-in, waves, camera locks, grabs, mounted combat, magic, pits/death height |
| Bosses | end of stages (Death Adder at 9) | hit reactions on big sprites, death-stab |
| Map interludes | `OldMap` | Guybrush on the map, SPACE-advance |
| Continue / game over | on death | death poses, continue screen |
| Ranking | after ending | portrait / entry |
| 2-player co-op | any stage | partner revive/throws, 2× HUD |

* **A. Boot stage select** — DONE, now via the cheat menu (**STAGE SELECT**, §2).
* **B. Wave-skip** — DONE via the cheat-menu **AUTO-KILL ENEMIES** switch (§2).
* **C. God/potion keys** — partly built: the cheat menu has **INVINCIBLE PLAYER**.
  Still unbuilt: a "refill magic potions" entry. (There are no loose god keys.)

---

## 11. Verification workflow

1. **Compile + run:** `.\scripts\run.ps1` (or `scripts\GoldenAxe.bat`). Needs a display — the user
   runs this, not you.
2. **Headless asset check** (no display): build a classpath dir and use the
   scratch harnesses in `C:\opencode\goldenaxeswitch\work`:
   ```powershell
   $out='C:\opencode\goldenaxeswitch\work\out'
   # compile once:  javac -d $out (all src\**\*.java)
   Copy-Item -Recurse -Force JavaGoldenAxe\assets\res "$out\res"
   javac -cp $out -d $out C:\...\work\AttackRender.java
   java -cp $out AttackRender C:\...\work\out.png idle walking_down walking_up
   ```
   `AttackRender` takes the output PNG then any number of animation names.
3. **Mount placement preview** (`work/CompositeRender.java`): draws the real beast
   plus the rider at the real `mounted_*` point using the engine's own maths
   (`FramePoint.convertPointToCameraSpace` + `Sprite.draw` anchors), so the mount
   art can be judged without launching the game:
   ```powershell
   javac -cp $out -d $out ...\work\CompositeRender.java
   java -cp "<assets-dir>;$out" CompositeRender out.png 8 5 chicken_leg guybrush_threepwood attack_1
   #                                  png     zoom cols beast      rider            anims...
   ```
4. **Placement pipeline check** (`work/verify_shipped_bake.py`): recomputes the
   expected pixels for every placed mount rectangle straight from the source sheet
   and diffs them against the shipped atlas — expects mean abs diff `0.00`.
5. **Draw-order / comparator test** (`work/CompareTest.java`): drives the real
   `Actor.compareTo` on `Unsafe.allocateInstance` actors — targeted tie cases, then
   50×400 randomised sorts (TimSort throws on a broken comparator contract) and a
   check that a player is never ordered before a same-depth corpse.
   ```powershell
   javac -cp $out -d $out ...\work\CompareTest.java ; java -cp $out CompareTest
   ```
6. **In game:** title → `1P START` → select `GUYBRUSH` (`O`) → Stage 1 (or boot
   stage-select with `1`). Attack `O`, jump `P`, magic `I`. For mounts, use the
   arena (§2) and mount each beast.

---

## 12. Gotchas

* `.char` files hold sprites **and** colliders **and** points in one file.
* The `logo` frame is drawn at a fixed HUD position, ignoring its anchor — it's
  just a 16×16 portrait.
* Frame rectangles must not be moved **in place** (hitboxes attach by intersecting
  the rectangle). `deshare.py` is the exception — it relocates rectangles and
  clones their colliders/points, verified by `deshare.py --check`.
* **The mount rectangles are the other exception**: no collider and no point in the
  layout intersects `mounting`/`mounted_*`, so `apply_mount.py` may grow/move them
  freely. It keeps a rectangle where it is when the pose still fits, grows it in
  place when that touches nothing, and otherwise allocates a fresh slot to the
  right of all geometry (the baker sizes the canvas from the rectangles). It
  refuses to write if any two rectangles would partially overlap — the atlas is
  keyed by rectangle, so that would paste two poses into one slot.
* **Draw order** is `Actor.compareTo`: depth (`wz`) ascending, ties → the player
  last, everything else → insertion order. A mounted pair is ordered by the
  rider's `wz = beast.wz + 1e-6`. See §9/§10.
* `build-custom/` and `sprites_overview.png` are git-ignored; Windows "` - Kopie`"
  duplicates are too (`* - Kopie.*`).
* `.gitattributes`/CRLF warnings on commit are harmless.
* `detect_sprites.py` uses a BFS over ~0.8M foreground pixels — takes a few seconds.
* `run.ps1` only recompiles when `build-custom\main\Main.class` is **missing**.
  After switching/reverting commits the source is newer but the stale build is
  still used, so the game can boot the old behaviour. Delete
  `JavaGoldenAxe\build-custom` (or run `.\run.ps1 -Rebuild`) whenever you change
  Java sources outside a normal edit-and-run.
* `mount_debug.log` (repo root) is written by the temporary diagnostics — delete it
  and them before shipping (§0).

---

## 13. Key files quick reference

| Purpose | Path |
| --- | --- |
| Character layout / hitboxes | `assets/res/chars/guybrush_layout.char` |
| Generated character file | `assets/res/chars/guybrush_threepwood.char` |
| Character art | `assets/res/image/guybrush_threepwood.png` |
| Edit the map | `tools/guybrush/mapping.json` |
| Visual mapper | `tools/guybrush/reviewer.html` |
| Move sandbox (press jump/attack) | `tools/guybrush/viewer.html` (`scripts/ViewAnimations.bat`) |
| Reviewer server (in-place save) | `tools/guybrush/serve_reviewer.py` |
| De-share layout tool | `tools/guybrush/deshare.py` |
| Baker | `tools/guybrush/build_atlas.py` |
| Sprite catalog | `tools/guybrush/sprites.json` |
| Mount placement editor | `tools/guybrush/mount_editor.html` |
| Mount placements (drag results) | `tools/guybrush/mount_placements.json` |
| Build/serve the mount editor | `tools/guybrush/make_mount_editor.py`, `serve_mount.py` |
| Apply placements to mapping + layout | `tools/guybrush/apply_mount.py` |
| Draw order / corpse placement | `src/infra/Actor.java` (`compareTo`, `forceKill`) |
| Cheat menu overlay ("ape") | `src/infra/CheatMenu.java` |
| Cheat switches + boot toggle | `src/infra/GoldenAxeGame.java` |
| Typed-key buffer (opener) | `src/infra/Input.java` |
| Auto-kill / no-thieves hooks | `src/scene/Stage.java` |
| Stage-select prompt | `src/scene/StageSelect.java` |
| Player enum | `src/actor/Player.java` |
| Engine loader | `src/infra/Resource.java` |
| Select screen | `src/scene/SelectPlayer.java` |
| Test arena / stage data | `assets/res/stage/stage_1.inf` |
| Reviewer guide | `REVIEWER.md` |
| Mod summary (user-facing) | `GUYBRUSH_MOD.md` |

---

## 14. Backlog / next steps

**If the user says "proceed", start at the first unchecked item below**, one item
at a time, and tick it off here as it is done. **For shipping, §0's checklist
comes first.**

### Already fixed
- [x] Reviewer: uniform scale per bottom animation; preview mirrors the baker;
      double-click to append; Export saves in place; Rectangles bar; Undo/Redo;
      Help; named sections; draggable splitter; Suggestions bar.
- [x] Baker: one sprite+size+mode per rectangle globally; `rect_overrides`.
- [x] `patch_select.py` clear/fit fix; `run.ps1` copy fix; Brave preview fix.
- [x] Player mounting works (player and enemy); the auto-kill releases the beast
      to `resting`; players always mount (the `X` gate is gone).
- [x] Stage-select (`scene/StageSelect.java`) — now a cheat-menu option.
- [x] `NO THIEVES` sweeps the mana/food goblins globally (`TEST_NO_THIEVES`).
- [x] Defensive null guard in `Actor.getCurrentFrameColliders()`.
- [x] De-share tool (`deshare.py`) — 0 shared rectangles.
- [x] Unified cutlass attack cycle for `attack_1..7`, `attack_short`.
- [x] Collapse/lying poses mapped and baked (`thrown`, `knock_down`, `dying`,
      `dead`, `resting`, `stand_up`, `stunned_*`, `idle`).
- [x] **Mount art placed by hand** — `mount_editor.html` + `apply_mount.py`;
      `place`/`flip` in the baker and the reviewer preview; rectangles resized to
      fit; verified numerically (§11.4).
- [x] **Test arena** in Stage 1 (one of each beast at the spawn).
- [x] **Draw order**: player over same-depth enemies/corpses; killed rider's corpse
      falls behind the beast; asymmetric comparator epsilon removed.
- [x] **Cheat menu** (`infra/CheatMenu.java`): the loose **Y**/**X**/**G** hotkeys
      are gone — type `ape` for an overlay with STAGE SELECT, AUTO-KILL ENEMIES,
      NO THIEVES and INVINCIBLE PLAYER. The player mount gate (**X**) is dismissed
      (players always mount).
- [x] Mount diagnostics + `mount_debug.log` removed; boot goes straight to Stage 1
      for now (stage-select is a cheat-menu option).

### Before shipping
- [ ] Do §0's ship checklist (revert the arena, flip the boot/test toggles,
      restore Stage 1's intro, commit).
- [ ] Play one full pass through the stages with the release toggles.
- [ ] Decide on `magic` effect and the Ax `hit` sounds (§10).

### Phase 2 (left) — Attack fidelity
- [ ] `running_attack`, `jumping_attack`, `jumping_death_stab` are single held
      poses; to animate them, add frames to the layout (§10). The reviewer already
      previews the full mapped frame list for these.

### Phase 4 (left) — Magic
- [ ] Decide whether to replace Ax's volcano effect (`magic_fire_*.ani`).

### Phase 5 (left) — Presentation
- [ ] Sounds: remap Ax's `hit`/`hit_rap` (optional).
- [ ] Select screen: consider a nicer full-body pose (cosmetic).

### Phase 6 — Robustness & docs
- [ ] Headless "render every animation" contact sheet + one-command
      "rebuild assets + game" script.
- [ ] Option "C": projected-depth sort with mount-pair depth sharing (§10).
- [ ] Keep this file current; commit atomically.

### Uncommitted work at the time of writing

```
 M assets/res/chars/guybrush_layout.char        (mount rectangles resized)
 M assets/res/chars/guybrush_threepwood.char
 M assets/res/image/guybrush_threepwood.png     (re-baked mount art)
 M assets/res/stage/stage_1.inf                 (test arena - revert to ship)
 M src/infra/Actor.java                         (draw order + corpse placement)
 M tools/guybrush/build_atlas.py                (place/flip)
 M tools/guybrush/make_reviewer.py              (place/offset/mirror in preview)
 M tools/guybrush/mapping.json                  (mount placements)
 M tools/guybrush/reviewer.html
?? tools/guybrush/apply_mount.py
?? tools/guybrush/make_mount_editor.py
?? tools/guybrush/mount_editor.html
?? tools/guybrush/serve_mount.py
?? tools/guybrush/mount_placements.json
?? tools/guybrush/mount_placements.backup.json
?? ReviewMount.bat
```
