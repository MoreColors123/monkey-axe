# Guybrush Threepwood mod

Replaces **Ax Battler** with **Guybrush Threepwood** (Monkey Island 2: LeChuck's
Revenge) as a playable character in this Golden Axe remake.

> Building on / continuing this work? See **[HANDOFF.md](HANDOFF.md)** for the
> full technical handoff (engine internals, tool pipeline, mapping schema,
> known issues, verification steps).

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
Guybrush art into a new 600x1000 spritesheet. The new character is registered as
`guybrush_threepwood`, which maps 1:1 onto the existing animation names
(`idle`, `walking_down`, `walking_up`, `running`, `attack_1..7`,
`attack_special`, `jumping`, `knock_down`, `dying`, ...).

## Choosing the sprites (the mapper)

Which Guybrush sprite is used for each Golden Axe animation lives in a plain
text file: `JavaGoldenAxe/tools/guybrush/mapping.json`. You can edit it by hand,
or use the visual editor.

### Visual editor

Double-click **`ReviewSprites.bat`** in the repo root. It builds and opens
`reviewer.html` (a single self-contained page — no server needed). In the page:

* the left side shows the whole source sheet with every detected sprite boxed;
  click a box to select it, drag to pan, scroll to zoom;
* the right side lists every Golden Axe animation. Pick one to see a live
  filmstrip preview and a **play/pause animated preview** that plays at the
  animation's real speed (the `fps` box defaults to the speed from the `.char`
  and can be overridden for previewing). One-shot animations hold their last
  frame like the game does — tick **loop preview** to make them repeat;
* assign sprites with **+ append selected sprite** / **replace frames with
  selected**, click a thumbnail to set that frame, and reorder with the arrows;
* tune **mode** (`bottom` = feet on the ground, `center` = lying) and an optional
  per-animation **scale**;
* **Undo** steps back one action; **Reset section** restores just the current
  animation and **Reset all** restores everything to the last exported/loaded
  mapping (edited sections are marked with a `*`);
* click **Preview all animations** for a full overview.

When you are happy, click **Export mapping.json** and save the downloaded file
over `JavaGoldenAxe/tools/guybrush/mapping.json`.

### Bake it in

Double-click **`BuildSprites.bat`** (runs `build_atlas.py`). This repaints
`res/image/guybrush_threepwood.png` (and the `.char`/HUD files) from
`mapping.json`. Then run `GoldenAxe.bat` to play.

### Under the hood

```
detect_sprites.py  ->  sprites.json   every sprite on the sheet, with ids
init_mapping.py    ->  mapping.json   the default mapping (run once / to reset)
make_reviewer.py   ->  reviewer.html  the self-contained editor
build_atlas.py     ->  game assets    mapping.json + sprites.json -> spritesheet
patch_select.py    ->  select screen  swaps the portrait
```

`mapping.json` format:

```json
{
  "global_scale": 1.15,
  "face": "s0121",
  "animations": {
    "walking_down": { "mode": "bottom", "frames": ["s0540", "s0541"] },
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
| `idle`, `stunned_*`, `stand_up`, mounted | front standing |
| `walking_down` | front-facing walk (sheet row 1) |
| `walking_up` | back-facing walk (sheet row 2) |
| `running`, `running_attack` | side-view walk |
| `attack_1..7`, `attack_short`, `grab_and_throw` | forward point/punch |
| `attack_special` | raised cutlass |
| `jumping*` | arms-up |
| `magic` | arms-up |
| `knock_down`, `thrown`, `resting`, `dying`, `dead` | lying on ground |

## Files changed

```
assets/res/image/guybrush_threepwood.png          (new)
assets/res/chars/guybrush_threepwood.char         (new)
assets/res/image/hud_magic_guybrush_threepwood.png(new)
assets/res/chars/hud_magic_guybrush_threepwood.char(new)
assets/res/image/select_player.png                (Ax portrait -> Guybrush)
assets/res/chars/select_player.char               (sprite ax -> guybrush)
assets/res/anim/ending.ani                        (ending actor -> guybrush)
src/actor/Player.java                             (enum AX -> GUYBRUSH)
src/infra/Actor.java                              (magic switch AX -> GUYBRUSH)
src/infra/GoldenAxeGame.java                      (demo character)
src/scene/SelectPlayer.java                       (select avatar)
GoldenAxe.bat / run.ps1                           (double-click launcher)
ReviewSprites.bat / BuildSprites.bat              (edit / bake the mapping)
tools/guybrush/guybrush_source.png                (source sheet)
tools/guybrush/sprites.json                       (detected sprite catalog)
tools/guybrush/mapping.json                       (editable animation -> sprite map)
tools/guybrush/detect_sprites.py                  (rebuild sprites.json)
tools/guybrush/init_mapping.py                    (reset mapping.json)
tools/guybrush/make_reviewer.py                   (build reviewer.html)
tools/guybrush/reviewer.html                      (visual mapper)
tools/guybrush/build_atlas.py                     (bake mapping.json -> game assets)
tools/guybrush/patch_select.py                    (swap the select portrait)
```

## Known limitations

* Animations are **approximations**. The MI2 sheet is an adventure-game set
  (walking in 4 directions, gestures, lying poses) and has no Golden-Axe-style
  axe swing, so attacks reuse point/punch/cutlass poses and several states
  (mounting, thrown, resting) reuse a single stand-in pose.
* Guybrush is drawn slightly smaller than the original Ax art so the sprites fit
  inside the existing frame rectangles without clipping.
* Colliders/points are inherited unchanged from Ax Battler, so reach and grab
  points are approximately where the original character had them.
* Several special poses are single-frame in the original remake and therefore
  here too — `running_attack`, `jumping_attack`, `jumping_death_stab`,
  `stand_up`, `mounting`/`mounted_*`, `resting`, `dead`. They are held for a
  code-timed window rather than animated. See `HANDOFF.md` for why and how to
  add frames if you want them animated.
