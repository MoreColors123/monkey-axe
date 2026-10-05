#!/usr/bin/env python3
"""Create the initial mapping.json from the hand-tuned source rectangles.

Run once (or to reset the mapping). Afterwards edit mapping.json directly or
use reviewer.html.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRITES = json.loads((HERE / "sprites.json").read_text())
OUT = HERE / "mapping.json"

# hand-picked source rectangles used by the original mod build
SIDE = [(63,6,21,47),(108,6,19,47),(149,7,32,46),(201,6,18,47),(243,6,19,47),(285,7,31,46)]
FRONT = [(1,2165,23,47),(40,2165,23,47),(79,2165,23,47),(115,2165,26,47),
         (154,2165,26,47),(193,2165,26,47),(232,2165,26,47),(272,2165,27,47)]
IDLE = [(378,5,24,47),(558,5,25,47),(467,6,27,47)]
BACK = [(18,178,33,37),(63,178,36,37),(106,178,32,37),(154,177,24,38),
        (199,176,26,39),(243,178,24,37)]
ATK = [(249,118,37,47),(199,60,33,47),(243,60,35,47),(468,168,32,47)]
SWORD = [(294,114,34,51),(296,463,38,48)]
JUMP = [(157,111,26,53),(294,114,34,51)]
LIE = [(497,1149,51,26),(3,1595,46,27),(148,1734,44,27),(373,2282,38,25),(296,2061,45,30)]
FACE = (301,378,20,21)

AMAP = {
    "idle": (IDLE, "bottom"),
    "walking_down": (FRONT, "bottom"),
    "walking_up": (BACK, "bottom"),
    "running": (SIDE, "bottom"),
    "running_attack": (SIDE, "bottom"),
    "jumping": (JUMP, "bottom"),
    "jumping_attack": (JUMP, "bottom"),
    "jumping_death_stab": (JUMP, "bottom"),
    "attack_1": (ATK, "bottom"),
    "attack_2": (ATK, "bottom"),
    "attack_3": (ATK, "bottom"),
    "attack_5": (ATK, "bottom"),
    "attack_6": (ATK, "bottom"),
    "attack_7": (ATK, "bottom"),
    "attack_short": (ATK, "bottom"),
    "attack_special": (SWORD, "bottom"),
    "attack_special_return": (ATK, "bottom"),
    "grab_and_throw": (ATK, "bottom"),
    "thrown": (LIE, "center"),
    "stunned_1": (IDLE, "bottom"),
    "stunned_2": (IDLE, "bottom"),
    "knock_down": (LIE, "center"),
    "stand_up": (IDLE, "bottom"),
    "mounting": (IDLE, "bottom"),
    "mounted_side": (IDLE, "bottom"),
    "mounted_side_flip": (IDLE, "bottom"),
    "mounted_down": (IDLE, "bottom"),
    "mounted_down_flip": (IDLE, "bottom"),
    "mounted_up": (IDLE, "bottom"),
    "mounted_up_flip": (IDLE, "bottom"),
    "resting": (LIE, "center"),
    "magic": (JUMP, "bottom"),
    "dying": (LIE, "center"),
    "dead": (LIE, "center"),
}


def iou(a, s):
    ax, ay, aw, ah = a
    ix = max(0, min(ax + aw, s["x"] + s["w"]) - max(ax, s["x"]))
    iy = max(0, min(ay + ah, s["y"] + s["h"]) - max(ay, s["y"]))
    inter = ix * iy
    union = aw * ah + s["w"] * s["h"] - inter
    return inter / union if union else 0.0


def match(rect):
    best, best_iou = None, -1.0
    for s in SPRITES:
        v = iou(rect, s)
        if v > best_iou:
            best_iou, best = v, s
    if best_iou < 0.10:
        cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
        best = min(SPRITES, key=lambda s: (s["x"] + s["w"] / 2 - cx) ** 2 +
                   (s["y"] + s["h"] / 2 - cy) ** 2)
        print(f"  ! weak match {rect} iou={best_iou:.2f} -> {best['id']}")
    return best["id"]


def main():
    data = {
        "global_scale": 1.15,
        "face": match(FACE),
        "animations": {},
    }
    for anim, (rects, mode) in AMAP.items():
        data["animations"][anim] = {
            "mode": mode,
            "frames": [match(r) for r in rects],
        }
    OUT.write_text(json.dumps(data, indent=1))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
