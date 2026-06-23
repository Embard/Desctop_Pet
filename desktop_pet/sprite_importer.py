"""Import animation clips from the user-provided master sprite sheet."""

from __future__ import annotations

import json
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).resolve().parent / "assets"
MASTER = ASSETS / "master_spritesheet.png"
MANIFEST = ASSETS / "sheet_manifest.json"
OUTPUT_META = ASSETS / "animations.json"
TARGET_W = 84
TARGET_H = 126
_QT_APP: QApplication | None = None


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int


def ensure_qt() -> QApplication:
    global _QT_APP
    app = QApplication.instance()
    if app is not None:
        return app  # type: ignore[return-value]
    if _QT_APP is None:
        _QT_APP = QApplication(sys.argv)
    return _QT_APP


def import_master_sheet(force: bool = False) -> bool:
    if not MASTER.exists():
        return False
    if OUTPUT_META.exists() and not force:
        clips = json.loads(OUTPUT_META.read_text(encoding="utf-8"))
        if clips and all((ASSETS / info["sheet"]).exists() for info in clips.values()):
            return True

    ensure_qt()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    master = QPixmap(str(MASTER))
    if master.isNull():
        raise RuntimeError(f"Cannot load {MASTER}")

    mw, mh = master.width(), master.height()
    animations: dict[str, dict] = {}

    for clip_name, spec in manifest["clips"].items():
        frames = extract_row_clip(master, mw, mh, spec)
        if not frames:
            continue
        sheet_name = f"clip_{clip_name}.png"
        save_strip(frames, sheet_name)
        animations[clip_name] = {
            "sheet": sheet_name,
            "frames": len(frames),
            "frame_w": TARGET_W,
            "frame_h": TARGET_H,
            "fps": spec.get("fps", 10),
        }

    if "walk_right" in animations:
        animations["walk_left"] = dict(animations["walk_right"])
    if "run_right" in animations:
        animations["run_left"] = dict(animations["run_right"])

    OUTPUT_META.write_text(json.dumps(animations, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def extract_row_clip(master: QPixmap, mw: int, mh: int, spec: dict) -> list[QPixmap]:
    x0 = int(spec.get("x0_pct", 0.12) * mw)
    x1 = int(spec.get("x1_pct", 0.86) * mw)
    y0 = int(spec["y0_pct"] * mh)
    y1 = int(spec["y1_pct"] * mh)
    max_frames = int(spec.get("max_frames", 8))
    min_w = int(spec.get("min_w_pct", 0.02) * mw)
    max_w = int(spec.get("max_w_pct", 0.05) * mw)

    row = master.copy(x0, y0, x1 - x0, y1 - y0).toImage().convertToFormat(QImage.Format.Format_ARGB32)
    remove_sheet_background(row)

    regions = detect_sprite_regions(row, min_w=min_w, max_w=max_w)
    if not regions:
        return []

    if len(regions) > max_frames:
        step = len(regions) / max_frames
        pick = [regions[int(i * step)] for i in range(max_frames)]
        regions = pick
    else:
        regions = regions[:max_frames]

    return [render_sprite_frame(row, region) for region in regions]


def is_background(color) -> bool:
    return color.red() <= 45 and color.green() <= 45 and color.blue() <= 50


def remove_sheet_background(image: QImage) -> None:
    w, h = image.width(), image.height()
    visited: set[tuple[int, int]] = set()
    queue: deque[tuple[int, int]] = deque()

    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h - 1))
    for y in range(h):
        queue.append((0, y))
        queue.append((w - 1, y))

    while queue:
        x, y = queue.popleft()
        if x < 0 or y < 0 or x >= w or y >= h or (x, y) in visited:
            continue
        visited.add((x, y))
        color = image.pixelColor(x, y)
        if not is_background(color):
            continue
        color.setAlpha(0)
        image.setPixelColor(x, y, color)
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))


def detect_sprite_regions(image: QImage, *, min_w: int, max_w: int) -> list[Region]:
    w, h = image.width(), image.height()
    raw: list[tuple[int, int]] = []
    start = -1

    for x in range(w):
        count = 0
        for y in range(h):
            if image.pixelColor(x, y).alpha() > 20:
                count += 1
        active = count > max(6, h // 12)
        if active and start < 0:
            start = x
        elif not active and start >= 0:
            raw.append((start, x - 1))
            start = -1
    if start >= 0:
        raw.append((start, w - 1))

    merged: list[tuple[int, int]] = []
    for left, right in raw:
        width = right - left + 1
        if width < min_w // 2:
            continue
        if merged and left - merged[-1][1] <= 5:
            merged[-1] = (merged[-1][0], right)
        else:
            merged.append((left, right))

    regions: list[Region] = []
    for left, right in merged:
        width = right - left + 1
        if width < min_w or width > max_w * 2:
            continue
        top, bottom = h, 0
        for y in range(h):
            for x in range(left, right + 1):
                if image.pixelColor(x, y).alpha() > 20:
                    top = min(top, y)
                    bottom = max(bottom, y)
        if bottom <= top:
            continue
        pad = 2
        regions.append(
            Region(
                max(0, left - pad),
                max(0, top - pad),
                min(w, right + pad + 1) - max(0, left - pad),
                min(h, bottom + pad + 1) - max(0, top - pad),
            )
        )

    return regions


def render_sprite_frame(sheet_row: QImage, region: Region) -> QPixmap:
    cropped = sheet_row.copy(region.left, region.top, region.width, region.height)
    scaled = QPixmap.fromImage(cropped).scaled(
        TARGET_W,
        TARGET_H,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QPixmap(TARGET_W, TARGET_H)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawPixmap((TARGET_W - scaled.width()) // 2, TARGET_H - scaled.height(), scaled)
    painter.end()
    return canvas


def save_strip(frames: list[QPixmap], name: str) -> None:
    if not frames:
        raise ValueError(f"No frames to save for {name}")
    strip = QPixmap(TARGET_W * len(frames), TARGET_H)
    strip.fill(Qt.GlobalColor.transparent)
    painter = QPainter(strip)
    for index, frame in enumerate(frames):
        painter.drawPixmap(index * TARGET_W, 0, frame)
    painter.end()
    if not strip.save(str(ASSETS / name), "PNG"):
        raise RuntimeError(f"Failed to save {name}")


if __name__ == "__main__":
    try:
        ok = import_master_sheet(force=True)
        print("Master sheet imported." if ok else "No master sheet found.")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
