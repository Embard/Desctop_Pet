"""Sprite sheet animation engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QTransform


def app_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


FLIPPED_CLIPS = {
    "walk_left": "walk_right",
    "run_left": "run_right",
}


class SpriteAnimator:
    def __init__(self) -> None:
        self.assets = app_root() / "assets"
        self.clips: dict[str, list[QPixmap]] = {}
        self.meta: dict[str, dict] = {}
        self.current = "idle"
        self.frame_index = 0.0
        self.elapsed_ms = 0
        self.load()

    def load(self) -> None:
        meta_path = self.assets / "animations.json"
        if not meta_path.exists():
            return
        self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for name, info in self.meta.items():
            if name in FLIPPED_CLIPS:
                continue
            sheet_path = self.assets / info["sheet"]
            if not sheet_path.exists():
                continue
            sheet = QPixmap(str(sheet_path))
            if sheet.isNull():
                continue
            frames = []
            fw, fh = info["frame_w"], info["frame_h"]
            for i in range(info["frames"]):
                frames.append(sheet.copy(i * fw, 0, fw, fh))
            self.clips[name] = frames

        for left_name, right_name in FLIPPED_CLIPS.items():
            if right_name in self.clips and left_name in self.meta:
                self.clips[left_name] = [
                    frame.transformed(QTransform().scale(-1, 1), Qt.TransformationMode.SmoothTransformation)
                    for frame in self.clips[right_name]
                ]

    def set_clip(self, name: str) -> None:
        if name not in self.clips:
            if name.endswith("_left") and name.replace("_left", "_right") in self.clips:
                name = name.replace("_left", "_right")
            elif name not in self.clips:
                name = "idle" if "idle" in self.clips else next(iter(self.clips), "idle")
        if name == self.current or name not in self.clips:
            return
        self.current = name
        self.frame_index = 0.0
        self.elapsed_ms = 0

    def tick(self, delta_ms: int) -> None:
        if self.current not in self.clips:
            return
        self.elapsed_ms += delta_ms
        fps = self.meta.get(self.current, {}).get("fps", 10)
        frame_time = 1000 / fps
        while self.elapsed_ms >= frame_time:
            self.elapsed_ms -= frame_time
            self.frame_index = (self.frame_index + 1) % len(self.clips[self.current])

    def current_frame(self) -> QPixmap | None:
        clip = self.clips.get(self.current)
        if not clip:
            return None
        idx = int(self.frame_index) % len(clip)
        return clip[idx]
