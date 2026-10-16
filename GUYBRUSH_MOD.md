# Guybrush Threepwood mod

Replaces **Ax Battler** with **Guybrush Threepwood** (Monkey Island 2: LeChuck's
Revenge) as a playable character in this Golden Axe remake.

> Building on / continuing this work? See **[HANDOFF.md](HANDOFF.md)** for the
> full technical handoff (engine internals, tool pipeline, mapping schema,
> known issues, verification steps) and **[REVIEWER.md](REVIEWER.md)** for the
> sprite reviewer itself.

Guybrush now appears:

* on the **SELECT PLAYER** screen (avatar + name `GUYBRUSH`),
* as the in-game player sprite in every stage,
* in the **HUD logo / magic potion bar**, and
* in the **ending cutscene** (the old Ax Battler actor is re-skinned too).

## How it works

The engine describes every character with a single `.char` file that lists
sprite sub-rectangles, colliders and grab points, and points those rectangles at
a PNG spritesheet (`res/image/<character-id>.png`).

Rather than hand-author a brand-new rig, the mod reuses Ax Battler's exact frame
layout (so all hitboxes, grab points and state names keep working) and *bakes*
Guybrush art into a fresh spritesheet (currently 2505×2166 — it grows as
rectangles are de-shared and the mount rectangles are resized to fit the riding
pose). The new character is registered as
`guybrush_threepwood`, which maps 1:1 onto the existing animation names
(`idle`, `walking_down`, `walking_up`,
`running`, `attack_1..7`, `attack_special`, `jumping`, `knock_down`, `dying`, ...).

## Choosing the sprites (the mapper)

Which Guybrush sprite is used for each Golden Axe animation lives in a plain
text file: `JavaGoldenAxe/tools/guybrush/mapping.json`. You can edit it by hand,
or use the visual editor.

### Visual editor

Double-click **`ReviewSprites.bat`** in the repo root. It regenerates
`reviewer.html` and starts a tiny local server so the editor can **save
`mapping.json` in place** (keeping the previous file as `mapping.backup.json`).
In the page:

* the **Sheet** shows the whole source sheet with every detected sprite boxed;
  click a box to select it, double-click to append it to the current animation,
  drag to pan, scroll to zoom;
* the **Animations** list picks which animation you edit; the **Rectangles** bar
  below it edits atlas slots directly (`rect_overrides`);
* **Preview** plays the original (Ax) and new (Guybrush) animations side by side
  at the real speed, alongside **Baked frames** and the editable **Frame list**;
* tune **mode** (`bottom` = feet on the ground, `center` = lying) and an optional
  per-animation **scale**; the top bar sets the **global scale**;
* **Undo** / **Redo** (`Ctrl+Z` / `Ctrl+Y`), **Reset section** and **Reset all**
  (edited sections are marked with a `*`);
* the **Help** button explains each section and setting.

When you are happy, click **Export mapping.json** — it saves straight over
`JavaGoldenAxe/tools/guybrush/mapping.json`. See [REVIEWER.md](REVIEWER.md) for
the full editor guide.

### The riding pose (the mount editor)

The sheet has no pose of Guybrush riding a beast, so the seated look is made by
**placing a pose on the beasts by hand**. Double-click **`ReviewMount.bat`**:

* it shows every frame of every mountable beast (the two dragons and the
  chicken-leg) that has a mount point, with the rider drawn exactly as the game
  will draw it;
* **drag** to position the pose, **wheel** to scale it, click a thumbnail to swap
  the pose, and **⇄ mirror** to flip it (the `*_flip` animations sit on beast
  frames that are drawn mirrored, so the rider must be mirrored there too);
* **Save placements** writes `mount_placements.json`.

Then bake it in:

```powershell
python apply_mount.py     # placements -> mapping.json + the frame rectangles
python build_atlas.py     # bake
```

`apply_mount.py` resizes the mount rectangles so the dropped pose always fits
(nothing else in the layout is touched, and it refuses to write if two rectangles
would overlap). The reviewer shows the same settings — `mode: place` with an
`offset` and a `mirror` flag — so the two tools never disagree.

### Bake it in

Double-click **`BuildSprites.bat`** (runs `build_atlas.py`). This repaints
`res/image/guybrush_threepwood.png` (and the `.char`/HUD files) from
`mapping.json`. Then run `GoldenAxe.bat` to play.

### Under the hood

```
detect_sprites.py  ->  sprites.json   every sprite on the sheet, with ids
init_mapping.py    ->  mapping.json   the default mapping (run once / to reset)
make_reviewer.py   ->  reviewer.html  the editor
serve_reviewer.py  ->  local server   lets the editor save mapping.json in place
deshare.py         ->  layout         gives every animation its own rectangles
build_atlas.py     ->  game assets    mapping.json + sprites.json -> spritesheet
make_mount_editor.py -> mount_editor.html  the riding-pose placement editor
serve_mount.py     ->  local server   serves both pages, saves the placements
apply_mount.py     ->  mapping+layout placements -> mapping.json + rectangles
patch_select.py    ->  select screen  swaps the portrait
```

`mapping.json` format:

```json
{
  "global_scale": 1.15,
  "face": "s0121",
  "animations": {
    "walking_down": { "mode": "bottom", "frames": ["s0004", "s0005"] },
    "knock_down":   { "mode": "center", "scale": 1.0, "frames": ["s0316"] }
  }
}
```

`frames` is an ordered list of sprite ids; if an animation has more game frames
than source frames, the list is looped. Animations missing from the file fall
back to `idle`.

Requires Python 3 with Pillow and numpy (on this machine the `python` on PATH,
Inkscape's bundled build, already has both).

### Source art

* Spritesheet: *Guybrush Threepwood* by **Ultimecia** on The Spriters Resource
  <https://www.spriters-resource.com/pc_computer/monkeyisland2/asset/24322/>
  (Monkey Island 2: LeChuck's Revenge, PC).
* The sheet has a solid green background which is keyed out to transparency when
  the atlas is built.

### Animation mapping

| Golden Axe animation | Guybrush source |
| --- | --- |
| `idle` | standing stance (`s0137`) |
| `walking_down` | front-facing walk (sheet row 1) |
| `walking_up` | back-facing walk (sheet row 2) |
| `walking_side`, `running` | side walk (sheet row 1) |
| `attack_1..7` | cutlass swing cycle (`s0321`/`s0322`/`s0320`) |
| `attack_short` | short swing sequence (`s0549`..`s0571`) |
| `running_attack` | cutlass lunge |
| `attack_special` | special sequence (`s0484`, `s0486`, `s0496`..`s0503`) |
| `attack_special_return` | pointing poses |
| `jumping*` | arms-up |
| `magic` | horn-blow poses (`s1142`/`s1145`) |
| `grab_and_throw` | grab / throw poses |
| `stunned_1/2`, `stand_up` | stunned / getting-up poses |
| `mounting`, `mounted_*` | **hand-placed riding pose** (a lunging stance, `s0443`), mirrored for the `*_flip` animations; positioned per beast in the mount editor |
| `knock_down`, `thrown`, `resting`, `dying`, `dead` | lying on ground |

## Files changed

```
assets/res/image/guybrush_threepwood.png          (new)
assets/res/chars/guybrush_threepwood.char         (new)
assets/res/chars/guybrush_layout.char             (new; de-shared layout)
assets/res/image/hud_magic_guybrush_threepwood.png(new)
assets/res/chars/hud_magic_guybrush_threepwood.char(new)
assets/res/image/select_player.png                (Ax portrait -> Guybrush)
assets/res/chars/select_player.char               (sprite ax -> guybrush)
assets/res/anim/ending.ani                        (ending actor -> guybrush)
src/actor/Player.java                             (enum AX -> GUYBRUSH)
src/infra/Actor.java                              (magic switch; draw order + corpse placement)
src/infra/GoldenAxeGame.java                      (demo character)
src/scene/SelectPlayer.java                       (select avatar)
GoldenAxe.bat / run.ps1                           (double-click launcher)
ReviewSprites.bat / BuildSprites.bat              (edit / bake the mapping)
ReviewMount.bat                                   (place the riding pose on the beasts)
tools/guybrush/guybrush_source.png                (source sheet)
tools/guybrush/sprites.json                       (detected sprite catalog)
tools/guybrush/mapping.json                       (editable animation -> sprite map)
tools/guybrush/mount_placements.json              (the riding-pose placements)
tools/guybrush/detect_sprites.py                  (rebuild sprites.json)
tools/guybrush/init_mapping.py                    (reset mapping.json)
tools/guybrush/make_reviewer.py                   (build reviewer.html)
tools/guybrush/reviewer.html                      (visual mapper)
tools/guybrush/serve_reviewer.py                  (local server: save in place)
tools/guybrush/make_mount_editor.py               (build mount_editor.html)
tools/guybrush/mount_editor.html                  (mount placement editor)
tools/guybrush/serve_mount.py                     (serve both review pages)
tools/guybrush/apply_mount.py                     (placements -> mapping + layout)
tools/guybrush/deshare.py                         (de-share the frame layout)
tools/guybrush/build_atlas.py                     (bake mapping.json -> game assets)
tools/guybrush/patch_select.py                    (swap the select portrait)
HANDOFF.md / REVIEWER.md                          (technical docs)
```

## Known limitations

* Animations are **approximations**. The MI2 sheet is an adventure-game set
  (walking in 4 directions, gestures, lying poses) and has no Golden-Axe-style
  axe swing, so attacks reuse point/punch/cutlass poses.
* Guybrush is drawn slightly smaller than the original Ax art so the sprites fit
  inside the existing frame rectangles without clipping.
* Colliders/points are inherited unchanged from Ax Battler, so reach and grab
  points are approximately where the original character had them.
* **The riding pose is hand-placed, not authored.** The sheet has no pose of
  Guybrush riding a beast either, so a lunging stance is positioned on each beast
  by hand in the mount editor and mirrored on the beast frames that are drawn
  mirrored. It reads as a rider, but it is still a stand-in for real riding art.
  The player's ability to mount can be toggled with **X** at runtime.
* Several special poses are single-frame in the original remake and therefore
  here too — `running_attack`, `jumping_attack`, `jumping_death_stab`,
  `stand_up`, `mounting`/`mounted_*`, `resting`, `dead`. They are held for a
  code-timed window rather than animated. See `HANDOFF.md` for why and how to
  add frames if you want them animated.
