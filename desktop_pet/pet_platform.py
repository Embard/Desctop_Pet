"""Platform / surface helpers — where the pet stands and walks."""

from __future__ import annotations

from dataclasses import dataclass

from desktop_scanner import DesktopScanner, Surface, SurfaceType

# Pet window top-left Y such that feet sit on a surface.
FEET_OFFSET = 178
TITLEBAR_HEIGHT = 36
PET_WINDOW_WIDTH = 112


@dataclass
class Platform:
    surface: Surface
    stand_y: int
    left: int
    right: int

    @property
    def is_window(self) -> bool:
        return self.surface.kind == SurfaceType.WINDOW


def stand_y_on_titlebar(title_top: int) -> int:
    return title_top + TITLEBAR_HEIGHT - FEET_OFFSET


def stand_y_on_floor(screen_bottom: int, margin: int = 10) -> int:
    return screen_bottom - margin - FEET_OFFSET


def feet_position(window_x: int, window_y: int, window_width: int) -> tuple[int, int]:
    return window_x + window_width // 2, window_y + FEET_OFFSET


class PlatformTracker:
    def __init__(self, scanner: DesktopScanner) -> None:
        self.scanner = scanner
        self.current: Platform | None = None

    def resolve(
        self,
        *,
        x: int,
        y: int,
        window_width: int,
        screen_rect: tuple[int, int, int, int],
        floor_margin: int = 10,
    ) -> Platform:
        feet_x, feet_y = feet_position(x, y, window_width)
        left, top, right, bottom = screen_rect
        desktop_y = stand_y_on_floor(bottom, floor_margin)

        taskbar = self.scanner.taskbar_rect()
        if taskbar and self.scanner._point_in_rect(feet_x, feet_y, taskbar):
            return Platform(
                Surface(SurfaceType.TASKBAR, taskbar, "Панель задач"),
                desktop_y,
                left,
                right - window_width,
            )

        for window in self.scanner._window_surfaces():
            wl, wt, wr, _wb = window.rect
            on_titlebar = (
                wl - 10 <= feet_x <= wr + 10
                and wt - 6 <= feet_y <= wt + TITLEBAR_HEIGHT + 10
            )
            if on_titlebar:
                return Platform(
                    window,
                    stand_y_on_titlebar(wt),
                    wl,
                    wr - window_width,
                )

        return Platform(
            Surface(SurfaceType.FLOOR, screen_rect, "Рабочий стол"),
            desktop_y,
            left,
            right - window_width,
        )

    def find_under_feet(
        self,
        feet_x: int,
        feet_y: int,
        screen_rect: tuple[int, int, int, int],
        window_width: int,
        floor_margin: int = 10,
    ) -> Platform | None:
        """Window titlebar directly under feet (for landing while falling)."""
        for window in self.scanner._window_surfaces():
            wl, wt, wr, _wb = window.rect
            if wl <= feet_x <= wr and wt - 4 <= feet_y <= wt + TITLEBAR_HEIGHT + 12:
                return Platform(
                    window,
                    stand_y_on_titlebar(wt),
                    wl,
                    wr - window_width,
                )
        return None
