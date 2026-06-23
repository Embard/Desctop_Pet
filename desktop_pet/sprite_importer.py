"""Import animation clips from the master sprite sheet using a fixed grid per row."""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).resolve().parent / "assets"
MASTER = ASSETS / "master_spritesheet.png"
MANIFEST = ASSETS / "sheet_manifest.json"
OUTPUT_META = ASSETS / "animations.json"
_QT_APP: QApplication | None = None


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
        meta = json.loads(OUTPUT_META.read_text(encoding="utf-8"))
        if meta and all((ASSETS / info["sheet"]).exists() for info in meta.values()):
            return True

    ensure_qt()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    target_w, target_h = manifest.get("target", [100, 148])

    master = QPixmap(str(MASTER))
    if master.isNull():
        raise RuntimeError(f"Cannot load {MASTER}")

    rows = manifest["rows"]
    animations: dict[str, dict] = {}

    for clip_name, spec in manifest["clips"].items():
        row_spec = rows[spec["row"]]
        indices = spec.get("frame_indices")
        frames = extract_grid_row(master, row_spec, indices, target_w, target_h)
        if not frames:
            print(f"WARNING: no frames for {clip_name}", file=sys.stderr)
            continue

        sheet_name = f"clip_{clip_name}.png"
        save_strip(frames, sheet_name, target_w, target_h)
        animations[clip_name] = {
            "sheet": sheet_name,
            "frames": len(frames),
            "frame_w": target_w,
            "frame_h": target_h,
            "fps": spec.get("fps", 10),
        }

    if "walk_right" in animations:
        animations["walk_left"] = dict(animations["walk_right"])
    if "run_right" in animations:
        animations["run_left"] = dict(animations["run_right"])

    OUTPUT_META.write_text(json.dumps(animations, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def extract_grid_row(
    master: QPixmap,
    row: dict,
    frame_indices: list[int] | None,
    target_w: int,
    target_h: int,
) -> list[QPixmap]:
    y0, y1 = int(row["y0"]), int(row["y1"])
    x0, x1 = int(row["x0"]), int(row["x1"])
    cols = int(row["cols"])
    gutter = int(row.get("gutter", 2))
    row_w = x1 - x0
    cell_w = row_w // cols

    indices = frame_indices if frame_indices is not None else list(range(cols))
    frames: list[QPixmap] = []

    for index in indices:
        if index >= cols:
            continue
        sx = x0 + index * cell_w + gutter
        sw = max(8, cell_w - gutter * 2)
        sh = y1 - y0 + 1 - gutter * 2
        sy = y0 + gutter
        cell = master.copy(sx, sy, sw, sh).toImage().convertToFormat(QImage.Format.Format_ARGB32)
        remove_sheet_background(cell)
        cropped = crop_visible(cell)
        if cropped.isNull() or not has_content(cropped):
            continue
        frames.append(render_frame(cropped, target_w, target_h))

    return frames


def is_background(color) -> bool:
    return color.red() <= 48 and color.green() <= 48 and color.blue() <= 55


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


def has_content(image: QImage, min_pixels: int = 80) -> bool:
    count = 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 20:
                count += 1
                if count >= min_pixels:
                    return True
    return False


def crop_visible(image: QImage) -> QImage:
    min_x, min_y = image.width(), image.height()
    max_x, max_y = 0, 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 15:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x <= min_x:
        return QImage()
    pad = 3
    return image.copy(
        max(0, min_x - pad),
        max(0, min_y - pad),
        min(image.width(), max_x + pad + 1) - max(0, min_x - pad),
        min(image.height(), max_y + pad + 1) - max(0, min_y - pad),
    )


def render_frame(cropped: QImage, target_w: int, target_h: int) -> QPixmap:
    scaled = QPixmap.fromImage(cropped).scaled(
        target_w,
        target_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QPixmap(target_w, target_h)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.drawPixmap((target_w - scaled.width()) // 2, target_h - scaled.height(), scaled)
    painter.end()
    return canvas


def save_strip(frames: list[QPixmap], name: str, target_w: int, target_h: int) -> None:
    strip = QPixmap(target_w * len(frames), target_h)
    strip.fill(Qt.GlobalColor.transparent)
    painter = QPainter(strip)
    for index, frame in enumerate(frames):
        painter.drawPixmap(index * target_w, 0, frame)
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
