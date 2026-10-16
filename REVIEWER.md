# REVIEWER — Guybrush sprite mapper

Everything about the visual sprite editor (`reviewer.html`) and its generator
`tools/guybrush/make_reviewer.py`. Read this before changing the reviewer; for
the game/mod in general read `HANDOFF.md`; for the player-facing summary read
`GUYBRUSH_MOD.md`.

The reviewer is a **self-contained web page** (all images/data embedded as data
URIs). It does not touch the game directly — it edits `mapping.json`; you then
bake with `build_atlas.py`.

---

## 1. How to open it

```
ReviewSprites.bat         # regenerates reviewer.html, starts the server, opens the browser
```

`ReviewSprites.bat` runs `python make_reviewer.py` then `python serve_reviewer.py`.
The server (`http://127.0.0.1:8765/`, ports 8765–8775) exists **only** so the
Export button can write `mapping.json` in place. `serve_reviewer.py --no-open`
starts it without launching a browser (used for tests).

Opening `reviewer.html` directly as a `file://` page still works, but Export then
falls back to a browser download.

> Do **not** drive the user's browser. To check the reviewer, inspect
> `reviewer.html` statically, run `node --check` on its `<script>`, and use the
> headless DOM-stub test (see §8).

---

## 2. Files

| File | Role |
| --- | --- |
| `tools/guybrush/make_reviewer.py` | Generator. Contains the whole page as the `TEMPLATE` string; reads data, writes `reviewer.html`. |
| `tools/guybrush/reviewer.html` | Generated page. **Do not edit by hand** — edit `make_reviewer.py` and regenerate. |
| `tools/guybrush/serve_reviewer.py` | Local server + in-place save endpoints (`/api/save`, `/api/suggestions`). |
| `tools/guybrush/mapping.json` | The editable map (embedded into the page on generate). |
| `tools/guybrush/suggestions.json` | The agent's proposed mappings + your approve/dismiss/comment state (§6b). |
| `tools/guybrush/sprites.json` | Sprite catalog from `detect_sprites.py`. |
| `assets/res/chars/guybrush_threepwood.char` | Current layout; drives `ga`, `animOrder`, speed/loop. |
| `assets/res/image/guybrush_source.png` | Source sheet (green keyed out in Python before embedding). |
| `assets/res/image/ax_battler.png` | Vanilla sheet, embedded for the original preview. |
| `assets/res/chars/ax_battler.char` | Vanilla layout, parsed into `origGa` (original preview). |

Embedded `DATA` object: `sheet`, `origSheet`, `sprites`, `mapping`, `animOrder`,
`ga` (frames per animation), `origGa`, `speed`, `loop`, `suggestions`.

---

## 3. UI sections (named)

Use these names when requesting changes.

* **Top bar** — `Help`, global scale, `Rectangles` (show/hide), `Undo`/`Redo`,
  `Reset all`, `Load mapping`, `Export mapping.json`, save status.
* **Sheet** — the source sprite sheet, all sprites boxed. Click to select,
  double-click to append to the current animation, drag to pan, wheel to zoom.
* **Animations** — the animation-chip list (click to edit). Auto-height.
* **Rectangles** — collapsible bar under Animations; the atlas-slot editor (§6).
* **Suggestions** — collapsible bar under Rectangles; the agent's proposed
  mappings with Approve/Dismiss/Reopen and a comment box (§6b). Open proposals
  come first, newest on top; a **closed** filter next to the section name hides
  handled ones (default hidden, remembered per browser).
* **Animation settings** — name, `Reset section`, `mode` (`bottom`/`center`/
  `place`), per-animation `scale`, and — in `place` mode — the `offset` fields
  plus a `mirror` checkbox. Those three belong to the **mount art** and are set by
  dragging on the beasts in `mount_editor.html` (see §11); editing them here is
  equivalent, and `Export` writes the same `mapping.json` keys.
* **Preview** — two animated canvases side by side, original (Ax) and new
  (Guybrush), plus play/replay/fps/loop and a meta line.
* **Baked frames** — filmstrip of the frames that will actually bake.
* **Frame list** — the editable source-sprite list (append/replace/clear, reorder,
  remove, click a thumbnail to set it).
* **Help popup** — the write-up (opened from the top bar), incl. a colour key:
  blue = section headings, gold monospace = a field/value/file you can edit,
  orange = borrowed/extra.

---

## 4. How the preview mirrors the baker

The page must show exactly what `build_atlas.py` will bake (see `HANDOFF.md` §5).

* `buildPlan()` — one entry per raw rectangle `x,y,w,h`:
  `{id, mode, scale, base, offset, flip, owner}`. **The first animation in layout
  order owns a rectangle**; later animations reuse it. Then
  `mapping.rect_overrides` is applied (which may also override `offset`/`flip`).
* `place` mode (the mount art, see `HANDOFF.md` §5.6): the scale is the mapping's
  absolute `scale`, and the sprite is drawn at `anchor + offset`; `flip: true`
  mirrors it *about the anchor* (`ctx.translate(ax,ay); ctx.scale(-1,1)`), exactly
  like a `left`/`right` facing swap in the engine. `neededRect`, the filmstrip and
  the animation preview all use this.
* `drawPlanned(ctx, gf, ax, ay, idOverride)` — draws a planned frame. When
  `idOverride` is given (an "extra" frame) it recomputes the scale from that
  sprite via `spriteScale()` and takes `offset`/`flip`/`mode` from the current
  animation instead of the rectangle's owner.
* `previewFrames(anim)` — the frame list the UI shows. Length is
  `max(layoutFrames, mappingFrames)`. Baked frames use the plan; frames beyond the
  layout are **extra** (drawn in orange, labelled `(extra)`, counter shows e.g.
  `1 game frame(s), 3 shown (2 extra from the frame list)`). Extras illustrate the
  frame list but do **not** bake until the layout has those rectangles.
* `drawAnimPreview()` — new animation from the plan; original animation from
  `origGa` + `ax_battler.png`, anchored so its feet share the ground line.
* `drawFilm()` — filmstrip; orange outline on frames that borrow another
  animation's rectangle.

---

## 5. Controls & shortcuts

* Click a sheet sprite to select; **double-click** to append it to the current
  animation.
* **Undo** = `Ctrl+Z`, **Redo** = `Ctrl+Y` (also `Ctrl+Shift+Z`). Stacks live in
  `history` / `redoStack`; any new edit clears the redo stack. `Reset section` /
  `Reset all` restore to the last exported/loaded state (`baseline`).
* Drag the divider between Sheet and the panels to resize; double-click to reset.
* Playback: `Pause`, `Replay`, `fps` (defaults to the animation's real speed
  `animation_speed * 60`), `loop preview` (off = hold last frame like in game).

---

## 6. Rectangles & `rect_overrides`

The atlas is one image with a fixed slot per rectangle, and the vanilla layout
**reuses rectangles across animations**, so a rectangle holds only one sprite.
The first animation that uses it owns it; others' choices are ignored (shown as
`borrowed`).

* The **Rectangles** bar lists every rectangle: key `x,y,w,h`, owner, animations
  that use it, the sprite it currently bakes (thumbnail + id), and any override.
* Select a sheet sprite then **Set** writes
  `mapping.rect_overrides["x,y,w,h"] = "sNNNN"`; **Clear** deletes it.
* Filter: "only rectangles used by the current animation".

After `deshare.py` (see `HANDOFF.md` §5/§6) there are **zero shared rectangles**,
so each animation owns its own and overrides are rarely needed.

---

## 6b. Suggestions (agent proposals)

The agent writes proposed mappings to `tools/guybrush/suggestions.json`; the
Suggestions bar (under Rectangles) shows each with its proposed frame strip
(thumbnails + ids, click a thumbnail to select that sprite on the sheet) and the
animation's current frames beside it.

* The bar lists **open proposals first, newest at the top**; handled
  (approved/dismissed) ones are hidden unless the **closed** filter next to the
  section name is ticked (remembered per browser). The agent prepends new
  proposals to `suggestions.json`, so they land on top.
* **Approve** — applies the proposal to the *page* mapping (frames + mode +
  scale, undoable). Then **Export mapping.json** + `BuildSprites.bat` as usual;
  exporting does **not** change the suggestion status.
* **Dismiss / Reopen** — marks the proposal rejected / back to open. Statuses
  and comments persist via `POST /api/suggestions` (atomic write to
  `suggestions.json`), so they survive a reload when the page runs through
  `serve_reviewer.py` (i.e. `ReviewSprites.bat`). Without the server the state
  stays in-memory only.
* **Comment box** — free text for the agent ("what to change about this
  proposal"), saved with *Save comment*; drafts are kept while you keep editing
  the page.

Workflow: agent edits `suggestions.json` → you run `ReviewSprites.bat` (it
regenerates `reviewer.html` with the new proposals) → approve/comment → Export.

---

## 7. Saving

* **Export mapping.json** → `POST /api/save`. The server validates the payload
  has an `animations` object, copies the current file to
  `mapping.backup.json` (beside it), then writes atomically (`.json.tmp` swap).
* Without the server (plain `file://`) Export downloads `mapping.json`.
* After exporting, bake with `BuildSprites.bat` (or `python build_atlas.py`).

---

## 8. Modifying the reviewer

1. Edit `TEMPLATE` (and/or the data assembly) in `make_reviewer.py`. Keep the
   preview logic in sync with `build_atlas.py` when a change affects what bakes.
2. Regenerate: `python make_reviewer.py`.
3. Syntax-check the generated script:
   ```powershell
   python -c "import re,pathlib;h=pathlib.Path('reviewer.html').read_text(encoding='utf-8');m=re.search(r'<script>(.*?)</script>',h,re.S);pathlib.Path('_c.js').write_text(m.group(1),encoding='utf-8')"
   node --check _c.js
   ```
4. Optional headless behaviour test: write a Node file that stubs `document`,
   `Image`, `window`, `performance`, `requestAnimationFrame`, canvas `getContext`
   (a Proxy returning no-ops), then concatenate the extracted `<script>` and call
   functions (`buildPlan`, `previewFrames`, `renderRects`, `undo`/`redo`, handlers).
   Set `imgSource = rawImg` to simulate the sheet load. This catches runtime
   errors without a browser. (Keep such scratch files out of the repo.)

---

## 9. Gotchas

* **Regenerate after editing.** `reviewer.html` is generated; stale it and your
  change won't show.
* **Brave fingerprint protection** blanked `canvas.getImageData()`; the sheet is
  therefore green-keyed **in Python** (`make_reviewer.py`) and embedded already
  transparent — the page never calls `getImageData`.
* The `ga` frames come from `guybrush_threepwood.char`; `origGa` from
  `ax_battler.char`. After de-share the new rectangles don't exist in
  `ax_battler.png`, which is why the original preview uses `origGa`.
* Only the RIGHT direction is previewed; the engine mirrors for LEFT.
* `rect_overrides` changes don't mark animation sections with `*` (that compares
  `animations` only) — the Rectangles bar is the source of truth for overrides.

---

## 10. Current state / backlog

Working: named sections, original-vs-new preview, full mapped-frame preview
(incl. extras), resizable splitter, rectangles bar + overrides, undo/redo,
tooltips, Help popup, in-place save + backup, `place`/`flip` support for the mount
art, headless-testable.

Backlog for the reviewer and the mod lives in `HANDOFF.md` §14 ("Backlog / next
steps"). Reviewer-specific ideas: atlas/layout visual preview with rectangle
outlines, per-rectangle scale/mode editing in the bar, a conflict report of
ignored per-animation choices, and animating the single-frame specials (needs
layout frames — `HANDOFF.md` §10).

---

## 11. The mount editor (sibling page)

`mount_editor.html` (`make_mount_editor.py` + `serve_mount.py`, launched by
`ReviewMount.bat`) is the companion tool for the **riding pose**, which cannot be
judged in the reviewer because it only makes sense drawn *on a beast*.

* It embeds the beast sheets (`dragon_blue`, `dragon_red`, `chicken_leg`), their
  `.char` frames and every frame that carries a `mounted_*` point, plus the rider
  layout rectangles and a strip of candidate poses.
* For each beast frame it draws the beast (mirrored when the sheet is authored
  `LEFT`, which the dragons are) with the mount point marked, then the rider at
  that point using the same `place`/`flip` maths as the baker.
* Drag = move, wheel = scale, click a thumbnail = swap the pose, `⇄ mirror` =
  `flip`. Placement is **per rider animation** and shared across every beast and
  frame. **Save** posts `mount_placements.json` via `/api/mount`.
* `apply_mount.py` turns those placements into `mapping.json` entries *and* resizes
  the mount rectangles to fit; then `build_atlas.py` bakes. See `HANDOFF.md` §6b.

The reviewer and the mount editor must not disagree: both implement `place` mode
identically, and `apply_mount.py` writes exactly the keys the reviewer shows.
