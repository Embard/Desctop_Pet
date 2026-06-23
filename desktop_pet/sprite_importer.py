"""Import animation clips from the user-provided master sprite sheet."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).resolve().parent / "assets"
MASTER = ASSETS / "master_spritesheet.png"
MANIFEST = ASSETS / "sheet_manifest.json"
OUTPUT_META = ASSETS / "animations.json"
TARGET_W = 72
TARGET_H = 108
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
        frames = extract_clip(master, mw, mh, spec)
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


def extract_clip(master: QPixmap, mw: int, mh: int, spec: dict) -> list[QPixmap]:
    x0 = int(spec["x_start_pct"] * mw)
    y0 = int(spec["y_pct"] * mh)
    fw = int(spec["frame_w_pct"] * mw)
    fh = int(spec["frame_h_pct"] * mh)
    count = int(spec["frames"])
    frames: list[QPixmap] = []

    for i in range(count):
        sx = x0 + i * fw
        if sx + fw > mw or y0 + fh > mh:
            break
        raw = master.copy(sx, y0, fw, fh)
        frames.append(process_frame(raw))

    return frames


def process_frame(raw: QPixmap) -> QPixmap:
    image = raw.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    remove_near_white(image)
    cropped = crop_visible(image)
    if cropped.isNull():
        cropped = image
    scaled = QPixmap.fromImage(cropped).scaled(
        TARGET_W,
        TARGET_H,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QPixmap(TARGET_W, TARGET_H)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.drawPixmap((TARGET_W - scaled.width()) // 2, TARGET_H - scaled.height(), scaled)
    painter.end()
    return canvas


def remove_near_white(image: QImage, threshold: int = 245) -> None:
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.red() >= threshold and c.green() >= threshold and c.blue() >= threshold:
                c.setAlpha(0)
                image.setPixelColor(x, y, c)


def crop_visible(image: QImage) -> QImage:
    min_x, min_y = image.width(), image.height()
    max_x, max_y = 0, 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 10:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if max_x <= min_x:
        return QImage()
    pad = 2
    return image.copy(
        max(0, min_x - pad),
        max(0, min_y - pad),
        min(image.width(), max_x + pad) - max(0, min_x - pad),
        min(image.height(), max_y + pad) - max(0, min_y - pad),
    )


def save_strip(frames: list[QPixmap], name: str) -> None:
    sheet = QPixmap(TARGET_W * len(frames), TARGET_H)
    sheet.fill(Qt.GlobalColor.transparent)
    painter = QPainter(sheet)
    for i, frame in enumerate(frames):
        painter.drawPixmap(i * TARGET_W, 0, frame)
    painter.end()
    if not sheet.save(str(ASSETS / name), "PNG"):
        raise RuntimeError(f"Failed to save {name}")


if __name__ == "__main__":
    try:
        ok = import_master_sheet(force=True)
        print("Master sheet imported." if ok else "No master sheet found.")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
