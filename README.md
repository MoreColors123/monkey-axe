# Golden Axe — Guybrush Threepwood mod

A playable Golden Axe remake in pure Java (Java2D/AWT/Swing/Java Sound, no
external libraries), with **Guybrush Threepwood** from *Monkey Island 2: LeChuck's
Revenge* as the first player character (the slot that used to be Ax Battler) — on
the select screen, in stage, in the HUD and in the ending.

![Golden Axe — Guybrush Threepwood mod](Screenshot.png)

---

## ▶ Play now (Windows) — nothing to build

**Easiest:** download **`monkeyaxe.zip`** from the
[latest release](https://github.com/MoreColors123/monkey-axe/releases/latest) and
unzip it anywhere — that is the game, complete. (The same zip sits in the repo
root: get the repo via **Code → Download ZIP** and unzip *that* copy — it also
brings the sources and the sprite tools.)

1. **Install Java 17** (Temurin JRE):
   <https://adoptium.net/temurin/releases/?version=17>
   pick *Operating System: Windows → Architecture: x64 → Package Type: JRE →
   `.msi`*, run the installer (default options are fine).
2. **Double-click the `Play.bat`** in that folder.

That's the whole install — the game and all of its art, music and sound live
**inside `monkeyaxe.jar`**; no data files sit next to it, and there is nothing else
to download or build. `Play.bat` is only a small wrapper that finds your Java and
opens the download page if it is missing — with Java installed you can just as well
double-click `monkeyaxe.jar` itself, or run

```
java -jar monkeyaxe.jar
```

from any OS.

Notes:

- Java **17 or newer** is all that's needed — no JDK, no Ant, no Python.
- `monkeyaxe.jar` was called `GoldenAxe.jar` up to the rename; release assets
  published before it still carry the old name and still work.
- Double-clicking the jar does nothing? Then your system has no `.jar`
  association — use `Play.bat`, which always works.

## What's in the repo

| Path | What it is |
|---|---|
| `monkeyaxe.zip` | **the shipped game**: `monkeyaxe.jar` (code + all assets) + `Play.bat` + `HowToPlay.txt` — unzip and play |
| `scripts\` | every launcher: `Play.bat` (the one that goes into the zip), run, build, release, sprite tools |
| `JavaGoldenAxe\` | the game — `src\` (Java sources), `assets\res\` (art, music, stages), `tools\guybrush\` (sprite pipeline) |
| `JavaGoldenAxeAnimationEditor2\` | the standalone animation editor the game's `.char`/`.ani` data was authored with |
| `HANDOFF.md`, `REVIEWER.md`, `GUYBRUSH_MOD.md` | how the mod, the sprite pipeline and the release work |
| `HowToPlay.txt` | player instructions (also the text of the GitHub release) |

## Controls

- Arrows — move · `O` attack · `P` jump · `I` magic
- `F12` fullscreen · `F11` toggle aspect ratio
- 2P: `WASD` move · `G` attack · `H` jump · `F` magic

## Cheats (hidden)

Type the word **`ape`** anywhere in-game to open the cheat menu (UP/DOWN to
navigate, ENTER to toggle/activate, ESC to close):

- **STAGE SELECT** — jump to any stage (type `1`–`9`, ENTER)
- **MOUNT BEAST** — spawn a mountable beast beside you
- **AUTO-KILL ENEMIES**, **NO THIEVES**, **INVINCIBLE PLAYER**

---

## Building from source (developers)

Needs a **JDK 17** (not just a JRE); no Ant required. The sprite tools additionally need **Python 3 with Pillow + numpy** (`python -m pip install pillow numpy`).

Every launcher lives in `scripts\` — `Play.bat` is the one packed into the zip (it also works from the repo, finding the jar one level up):

- **`scripts\Play.bat`** — play (`..\monkeyaxe.jar`, or the jar right next to it inside the unzipped zip).
- **`scripts\GoldenAxe.bat`** — compile the sources and play (uses `scripts\run.ps1`; `.\scripts\run.ps1 -Rebuild` forces a recompile).
- **`scripts\BuildRelease.bat`** — rebuild the shipped `monkeyaxe.zip` (jar + `Play.bat` + `HowToPlay.txt`); the jar it packs stays in the root as a git-ignored intermediate.
- **`scripts\BuildSprites.bat`** — re-bake the Guybrush sprites from `mapping.json`.
- **`scripts\ReviewSprites.bat`** — open the sprite mapper (`reviewer.html`).
- **`scripts\ReviewMount.bat`** — place the riding pose on the beasts (`mount_editor.html`).
- **`scripts\ViewAnimations.bat`** — open a playable move sandbox (`viewer.html`).

The usual loop: change a sprite → **`scripts\ReviewSprites.bat`** to check it → **`scripts\BuildSprites.bat`** to bake it in → **`scripts\BuildRelease.bat`** to rebuild the jar and the shipped zip → **`scripts\Play.bat`** to play it. For pure source edits skip the jar entirely: **`scripts\GoldenAxe.bat`** compiles and runs straight from `JavaGoldenAxe\assets\res`.

**`monkeyaxe.zip` is the committed build**: after every game change rebuild it and commit it — and upload it to the release — or clones and downloads keep serving the old game. The jar beside it is only a build intermediate and is git-ignored. For a machine with no Java at all, `jpackage` can bundle a runtime — see `HANDOFF.md`.

See `HANDOFF.md` and `REVIEWER.md` for the full sprite pipeline.

---

## Credits

- Original Golden Axe remake by **Leonardo Ono** —
  <https://github.com/leonardo-ono/JavaGoldenAxe>
- Java GoldenAxe clone this fork is based on —
  <https://github.com/derek-keeler/GoldenAxeClone>
- Guybrush Threepwood sprites ripped from *Monkey Island 2* by **Ultimecia**
  (spriters-resource) — keep the credit.
- References: <https://goldenaxe.fandom.com/wiki/Main_Page>
