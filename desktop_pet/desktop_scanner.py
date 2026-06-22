"""Scan desktop surfaces: windows, icons, folders."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

try:
    import win32gui
    import win32process
except ImportError:  # pragma: no cover
    win32gui = None  # type: ignore
    win32process = None  # type: ignore


class SurfaceType(str, Enum):
    FLOOR = "desktop_floor"
    TASKBAR = "taskbar"
    WINDOW = "window_titlebar"
    ICON = "desktop_icon"
    FOLDER = "folder_icon"


@dataclass
class Surface:
    kind: SurfaceType
    rect: tuple[int, int, int, int]  # left, top, right, bottom
    label: str = ""
    handle: int | None = None
    icon_index: int | None = None


user32 = ctypes.windll.user32
LVM_GETITEMCOUNT = 0x1004
LVM_GETITEMPOSITION = 0x1010


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class DesktopScanner:
    SYSTEM_TITLES = {
        "Program Manager",
        "Desktop Pet",
        "DesktopPet",
        "Windows Input Experience",
        "Settings",
    }

    def __init__(self) -> None:
        self.icons_available = False
        self._icon_positions: list[tuple[int, int, str, int]] = []
        self.refresh_icons()

    def refresh_icons(self) -> None:
        self._icon_positions = []
        if win32gui is None:
            return
        try:
            progman = win32gui.FindWindow("Progman", None)
            if not progman:
                return
            shell = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
            if not shell:
                worker = self._find_workerw()
                if worker:
                    shell = win32gui.FindWindowEx(worker, 0, "SHELLDLL_DefView", None)
            if not shell:
                return
            listview = win32gui.FindWindowEx(shell, 0, "SysListView32", None)
            if not listview:
                return
            desktop_names = self._desktop_entry_names()
            count = win32gui.SendMessage(listview, LVM_GETITEMCOUNT, 0, 0)
            for i in range(min(count, 80)):
                pt = POINT()
                win32gui.SendMessage(listview, LVM_GETITEMPOSITION, i, ctypes.addressof(pt))
                label = desktop_names[i] if i < len(desktop_names) else f"icon_{i}"
                self._icon_positions.append((pt.x, pt.y, label, i))
            self.icons_available = len(self._icon_positions) > 0
        except Exception:
            self.icons_available = False

    def _desktop_entry_names(self) -> list[str]:
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "OneDrive" / "Desktop"
        if not desktop.exists():
            return []
        names: list[str] = []
        for entry in sorted(desktop.iterdir(), key=lambda p: p.name.lower()):
            if entry.suffix.lower() in {".lnk", ""} or entry.is_dir():
                names.append(entry.stem if entry.suffix == ".lnk" else entry.name)
        return names

    def _find_workerw(self) -> int | None:
        result = None

        def callback(hwnd, _):
            nonlocal result
            if win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None):
                result = hwnd

        win32gui.EnumWindows(callback, None)
        return result

    def scan(self, screen_rect: tuple[int, int, int, int], pet_center: tuple[int, int]) -> Surface:
        left, top, right, bottom = screen_rect
        px, py = pet_center

        taskbar_top = bottom - 48
        if py >= taskbar_top:
            return Surface(SurfaceType.TASKBAR, (left, taskbar_top, right, bottom), "Панель задач")

        for surf in self._window_surfaces():
            if self._point_in_rect(px, py, surf.rect):
                return surf

        if self.icons_available:
            for x, y, label, idx in self._icon_positions:
                icon_rect = (x, y, x + 72, y + 80)
                if self._point_in_rect(px, py, icon_rect):
                    kind = SurfaceType.FOLDER if self._looks_like_folder(label) else SurfaceType.ICON
                    return Surface(kind, icon_rect, label, icon_index=idx)

        return Surface(SurfaceType.FLOOR, screen_rect, "Рабочий стол")

    def nearest_interactable(self, pet_center: tuple[int, int], max_dist: int = 180) -> Surface | None:
        px, py = pet_center
        best: Surface | None = None
        best_dist = max_dist

        for surf in self._window_surfaces():
            cx = (surf.rect[0] + surf.rect[2]) // 2
            cy = (surf.rect[1] + surf.rect[3]) // 2
            dist = abs(px - cx) + abs(py - cy)
            if dist < best_dist:
                best_dist = dist
                best = surf

        if self.icons_available:
            for x, y, label, idx in self._icon_positions:
                cx, cy = x + 36, y + 40
                dist = abs(px - cx) + abs(py - cy)
                if dist < best_dist:
                    best_dist = dist
                    kind = SurfaceType.FOLDER if self._looks_like_folder(label) else SurfaceType.ICON
                    best = Surface(kind, (x, y, x + 72, y + 80), label, icon_index=idx)

        return best

    def _window_surfaces(self) -> list[Surface]:
        surfaces: list[Surface] = []
        if win32gui is None:
            return surfaces

        def callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd)
            if not title or title in self.SYSTEM_TITLES:
                return True
            if win32gui.IsIconic(hwnd):
                return True
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                return True
            left, top, right, bottom = rect
            if right - left < 120 or bottom - top < 80:
                return True
            titlebar = (left, top, right, top + 36)
            surfaces.append(Surface(SurfaceType.WINDOW, titlebar, title, handle=hwnd))
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        return surfaces

    @staticmethod
    def _point_in_rect(x: int, y: int, rect: tuple[int, int, int, int]) -> bool:
        return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]

    @staticmethod
    def _looks_like_folder(label: str) -> bool:
        lower = label.lower()
        return "folder" in lower or "папк" in lower or lower.endswith(" docs") or lower.endswith(" files")
