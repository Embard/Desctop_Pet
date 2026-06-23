"""Load sprite assets from master sheet or fallback builder."""

from __future__ import annotations

from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"


def ensure_assets() -> None:
    if (ASSETS / "master_spritesheet.png").exists():
        from sprite_importer import import_master_sheet

        if import_master_sheet():
            return

    from sprite_builder import build_all_sheets

    build_all_sheets()
