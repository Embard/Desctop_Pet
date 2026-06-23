"""Preview each manifest row to verify sprite cropping (run after placing master_spritesheet.png)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QApplication

ASSETS = Path(__file__).resolve().parent / "assets"
MASTER = ASSETS / "master_spritesheet.png"
MANIFEST = ASSETS / "sheet_manifest.json"


def main() -> int:
    if not MASTER.exists():
        print(f"Missing {MASTER}")
        return 1

    app = QApplication(sys.argv)
    master = QPixmap(str(MASTER))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = manifest["rows"]

    preview = QPixmap(master.width(), master.height())
    preview.fill(Qt.GlobalColor.transparent)
    painter = QPainter(preview)
    painter.setOpacity(0.35)
    painter.drawPixmap(0, 0, master)
    painter.setOpacity(1.0)

    colors = [
        Qt.GlobalColor.red,
        Qt.GlobalColor.green,
        Qt.GlobalColor.blue,
        Qt.GlobalColor.yellow,
        Qt.GlobalColor.magenta,
        Qt.GlobalColor.cyan,
        Qt.GlobalColor.darkRed,
        Qt.GlobalColor.darkGreen,
        Qt.GlobalColor.darkBlue,
        Qt.GlobalColor.darkYellow,
    ]

    for index, (name, row) in enumerate(rows.items()):
        color = colors[index % len(colors)]
        painter.setPen(color)
        y0, y1 = int(row["y0"]), int(row["y1"])
        x0, x1 = int(row["x0"]), int(row["x1"])
        cols = int(row["cols"])
        cell_w = (x1 - x0) // cols
        painter.drawRect(x0, y0, x1 - x0, y1 - y0 + 1)
        for col in range(cols):
            sx = x0 + col * cell_w
            painter.drawRect(sx, y0, cell_w, y1 - y0 + 1)
        painter.drawText(x0 + 4, y0 + 14, name)

    painter.end()
    out = ASSETS / "sheet_validation_preview.png"
    preview.save(str(out), "PNG")
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
