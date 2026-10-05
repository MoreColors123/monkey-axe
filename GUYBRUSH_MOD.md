# Guybrush Threepwood mod

Replaces **Ax Battler** with **Guybrush Threepwood** (Monkey Island 2: LeChuck's
Revenge) as a playable character in this Golden Axe remake.

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

## Regenerating the art

The helper scripts live in `JavaGoldenAxe/tools/guybrush/`:

```bash
cd JavaGoldenAxe/tools/guybrush
python build_atlas.py            # rebuilds res/image/guybrush_threepwood.png + .char + HUD magic
python patch_select.py           # swaps the select-screen portrait
```

Both take an optional path to the source sheet and otherwise use
`guybrush_source.png` in the same folder.

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
| `walking_down` | front-facing walk |
| `walking_up` | back-facing walk |
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
tools/guybrush/*                                  (generator scripts + source sheet)
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
