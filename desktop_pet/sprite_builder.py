"""Build realistic sprite sheets from user reference photos."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

FRAME_W = 96
FRAME_H = 140
ASSETS = Path(__file__).resolve().parent / "assets"


def build_all_sheets(force: bool = False) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    meta_path = ASSETS / "animations.json"
    if meta_path.exists() and not force:
        required = [
            "spritesheet_walk_right.png",
            "spritesheet_walk_left.png",
            "spritesheet_idle.png",
            "spritesheet_sit.png",
            "spritesheet_jump.png",
            "spritesheet_interact.png",
        ]
        if all((ASSETS / name).exists() for name in required):
            return

    upper = prepare_upper_body(ASSETS / "reference_face.png")
    if upper is None:
        upper = prepare_upper_body(ASSETS / "reference_pose.png")
    if upper is None:
        raise FileNotFoundError("reference_face.png or reference_pose.png required")

    walk_right = build_walk_sheet(upper, direction=1)
    walk_left = build_walk_sheet(upper, direction=-1)
    idle = build_idle_sheet(upper)
    sit = build_sit_sheet(upper)
    jump = build_jump_sheet(upper)
    interact = build_interact_sheet(upper)

    save_sheet(walk_right, "spritesheet_walk_right.png")
    save_sheet(walk_left, "spritesheet_walk_left.png")
    save_sheet(idle, "spritesheet_idle.png")
    save_sheet(sit, "spritesheet_sit.png")
    save_sheet(jump, "spritesheet_jump.png")
    save_sheet(interact, "spritesheet_interact.png")

    meta = {
        "walk_right": {"sheet": "spritesheet_walk_right.png", "frames": len(walk_right), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 12},
        "walk_left": {"sheet": "spritesheet_walk_left.png", "frames": len(walk_left), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 12},
        "idle": {"sheet": "spritesheet_idle.png", "frames": len(idle), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 8},
        "sit": {"sheet": "spritesheet_sit.png", "frames": len(sit), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 8},
        "jump": {"sheet": "spritesheet_jump.png", "frames": len(jump), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 14},
        "interact_window": {"sheet": "spritesheet_interact.png", "frames": len(interact), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 10},
        "interact_icon": {"sheet": "spritesheet_interact.png", "frames": len(interact), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 10},
        "interact_folder": {"sheet": "spritesheet_interact.png", "frames": len(interact), "frame_w": FRAME_W, "frame_h": FRAME_H, "fps": 10},
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def prepare_upper_body(path: Path) -> QPixmap | None:
    if not path.exists():
        return None
    image = QImage(str(path)).convertToFormat(QImage.Format.Format_ARGB32)
    image = image.scaledToHeight(320, Qt.TransformationMode.SmoothTransformation)
    remove_light_background(image)
    cropped = crop_visible(image)
    if cropped.isNull():
        return None
    return QPixmap.fromImage(cropped).scaled(
        FRAME_W - 6,
        88,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def remove_light_background(image: QImage) -> None:
    w, h = image.width(), image.height()
    visited: set[tuple[int, int]] = set()
    stack: list[tuple[int, int]] = []
    for x in range(w):
        stack.extend([(x, 0), (x, h - 1)])
    for y in range(h):
        stack.extend([(0, y), (w - 1, y)])

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or (x, y) in visited:
            continue
        visited.add((x, y))
        c = image.pixelColor(x, y)
        if not (c.red() > 168 and c.green() > 168 and c.blue() > 168):
            continue
        c.setAlpha(0)
        image.setPixelColor(x, y, c)
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])


def crop_visible(image: QImage) -> QImage:
    min_x, min_y = image.width(), image.height()
    max_x, max_y = 0, 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 0:
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
    if max_x <= min_x:
        return QImage()
    pad = 4
    return image.copy(
        max(0, min_x - pad),
        max(0, min_y - pad),
        min(image.width(), max_x + pad) - max(0, min_x - pad),
        min(image.height(), max_y + pad) - max(0, min_y - pad),
    )


def build_walk_sheet(upper: QPixmap, direction: int) -> list[QPixmap]:
    frames = []
    for i in range(10):
        phase = i / 10
        swing = math.sin(phase * math.tau)
        frames.append(compose_frame(upper, mode="walk", swing=swing, direction=direction))
    return frames


def build_idle_sheet(upper: QPixmap) -> list[QPixmap]:
    return [compose_frame(upper, mode="idle", swing=math.sin(i / 5 * math.tau) * 0.25, direction=1) for i in range(5)]


def build_sit_sheet(upper: QPixmap) -> list[QPixmap]:
    return [compose_frame(upper, mode="sit", swing=i * 0.15, direction=1) for i in range(4)]


def build_jump_sheet(upper: QPixmap) -> list[QPixmap]:
    return [compose_frame(upper, mode="jump", swing=math.sin(i / 5 * math.pi), direction=1) for i in range(6)]


def build_interact_sheet(upper: QPixmap) -> list[QPixmap]:
    return [compose_frame(upper, mode="interact", swing=math.sin(i / 4 * math.pi), direction=1) for i in range(4)]


def compose_frame(upper: QPixmap, *, mode: str, swing: float, direction: int) -> QPixmap:
    frame = QPixmap(FRAME_W, FRAME_H)
    frame.fill(Qt.GlobalColor.transparent)
    painter = QPainter(frame)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    lift = 0.0
    if mode == "walk":
        lift = -abs(float(swing)) * 2.5
    elif mode == "jump":
        lift = -18 * max(0.0, float(swing))
    elif mode == "sit":
        lift = 8 * float(swing)

    shadow_w = 42 - int(abs(swing) * 6) if mode == "jump" else 46
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 50))
    painter.drawEllipse((FRAME_W - shadow_w) // 2, FRAME_H - 8, shadow_w, 6)

    leg_top = 86 + int(lift)
    draw_legs(painter, swing=swing, top=leg_top, mode=mode, direction=direction)

    upper_x = (FRAME_W - upper.width()) // 2
    upper_y = 8 + int(lift) - (8 if mode == "sit" else 0)
    painter.drawPixmap(upper_x, upper_y, upper)

    if mode == "interact":
        painter.setPen(QColor(80, 80, 80, 180))
        arm_y = 52 + int(lift)
        painter.drawLine(FRAME_W // 2 + 8, arm_y, FRAME_W // 2 + 22, arm_y - 10 - int(swing * 8))
        painter.drawLine(FRAME_W // 2 + 22, arm_y - 10 - int(swing * 8), FRAME_W // 2 + 30, arm_y - 4)

    painter.end()
    return frame


def draw_legs(painter: QPainter, *, swing: float, top: int, mode: str, direction: int) -> None:
    pants = QColor("#b8bcc2")
    shoe = QColor("#2b2f36")
    stripe = QColor("#e8eaee")
    center = FRAME_W // 2
    s = float(swing) * direction

    if mode == "sit":
        painter.setBrush(pants)
        painter.drawRoundedRect(center - 28, top + 8, 24, 14, 5, 5)
        painter.drawRoundedRect(center + 4, top + 8, 24, 14, 5, 5)
        painter.setBrush(shoe)
        painter.drawRoundedRect(center - 30, top + 18, 28, 8, 3, 3)
        painter.drawRoundedRect(center + 2, top + 18, 28, 8, 3, 3)
        return

    left_x = center - 18 + int(s * 8)
    right_x = center + 2 - int(s * 8)
    left_h = 34 - int(abs(s) * 6)
    right_h = 34 - int(abs(-s) * 6)
    if mode == "jump":
        left_x -= 6
        right_x += 6
        left_h = 28
        right_h = 28

    painter.setBrush(pants)
    painter.drawRoundedRect(left_x, top, 14, left_h, 5, 5)
    painter.drawRoundedRect(right_x, top, 14, right_h, 5, 5)
    painter.setBrush(stripe)
    painter.drawRect(left_x + 5, top, 2, left_h - 4)
    painter.drawRect(right_x + 5, top, 2, right_h - 4)
    painter.setBrush(shoe)
    painter.drawRoundedRect(left_x - 3 + int(s * 4), top + left_h - 3, 20, 7, 3, 3)
    painter.drawRoundedRect(right_x - 1 - int(s * 4), top + right_h - 3, 20, 7, 3, 3)


def save_sheet(frames: list[QPixmap], name: str) -> None:
    sheet = QPixmap(FRAME_W * len(frames), FRAME_H)
    sheet.fill(Qt.GlobalColor.transparent)
    painter = QPainter(sheet)
    for i, frame in enumerate(frames):
        painter.drawPixmap(i * FRAME_W, 0, frame)
    painter.end()
    sheet.save(str(ASSETS / name))


if __name__ == "__main__":
    build_all_sheets(force=True)
    print("Sprite sheets built.")
