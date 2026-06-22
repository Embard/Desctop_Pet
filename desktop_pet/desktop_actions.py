"""Light desktop interactions: nudge windows and icons."""

from __future__ import annotations

import time

try:
    import win32con
    import win32gui
except ImportError:  # pragma: no cover
    win32con = None  # type: ignore
    win32gui = None  # type: ignore

import ctypes

from desktop_scanner import POINT, Surface, SurfaceType

LVM_GETITEMPOSITION = 0x1010
LVM_SETITEMPOSITION = 0x100F


class DesktopActions:
    COOLDOWN_SEC = 7.0

    def __init__(self) -> None:
        self._last_action = 0.0
        self._listview = None

    def can_act(self) -> bool:
        return time.time() - self._last_action >= self.COOLDOWN_SEC

    def nudge(self, surface: Surface, direction: int = 1) -> bool:
        if not self.can_act() or win32gui is None:
            return False
        ok = False
        if surface.kind == SurfaceType.WINDOW and surface.handle:
            ok = self._nudge_window(surface.handle, direction)
        elif surface.kind in (SurfaceType.ICON, SurfaceType.FOLDER) and surface.icon_index is not None:
            ok = self._nudge_icon(surface.icon_index, direction)
        if ok:
            self._last_action = time.time()
        return ok

    def _nudge_window(self, hwnd: int, direction: int) -> bool:
        try:
            if win32gui.IsZoomed(hwnd):
                return False
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            dx = 28 * direction
            win32gui.SetWindowPos(
                hwnd,
                None,
                left + dx,
                top,
                0,
                0,
                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
            return True
        except Exception:
            return False

    def _find_listview(self) -> int | None:
        if self._listview and win32gui.IsWindow(self._listview):
            return self._listview
        progman = win32gui.FindWindow("Progman", None)
        shell = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None) if progman else 0
        if not shell:
            return None
        self._listview = win32gui.FindWindowEx(shell, 0, "SysListView32", None)
        return self._listview

    def _nudge_icon(self, index: int, direction: int) -> bool:
        listview = self._find_listview()
        if not listview:
            return False
        try:
            pt = POINT()
            win32gui.SendMessage(listview, LVM_GETITEMPOSITION, index, ctypes.addressof(pt))
            pt.x += 24 * direction
            win32gui.SendMessage(listview, LVM_SETITEMPOSITION, index, ctypes.addressof(pt))
            return True
        except Exception:
            return False
