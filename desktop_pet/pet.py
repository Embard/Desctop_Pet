"""Desktop pet window — rendering, input, lifecycle."""

from __future__ import annotations

import os
import random
import sys

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import QLabel, QMenu, QWidget

from asset_loader import ensure_assets
from animation import SpriteAnimator
from behavior import BehaviorController, BehaviorState
from pet_platform import PlatformTracker, feet_position, stand_y_on_floor

WINDOW_WIDTH = 112
WINDOW_HEIGHT = 182
PET_W = 100
PET_H = 156
FLOOR_MARGIN = 10
TICK_MS = 33


class PetWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        ensure_assets()

        self.setWindowTitle("Desktop Pet")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.pet_label = QLabel(self)
        self.pet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pet_label.setStyleSheet("background: transparent;")
        self.pet_label.setGeometry((WINDOW_WIDTH - PET_W) // 2, WINDOW_HEIGHT - PET_H - 4, PET_W, PET_H)

        self.bubble = QLabel(self)
        self.bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bubble.setWordWrap(True)
        self.bubble.setStyleSheet(
            """
            QLabel {
                background: rgba(255, 255, 255, 235);
                border: 1px solid rgba(40, 40, 40, 120);
                border-radius: 8px;
                color: #202020;
                font: 8pt "Segoe UI";
                padding: 4px;
            }
            """
        )
        self.bubble.setGeometry(6, 4, WINDOW_WIDTH - 12, 32)
        self.bubble.hide()

        self.animator = SpriteAnimator()
        self.behavior = BehaviorController()
        self.platforms = PlatformTracker(self.behavior.scanner)
        self.dragging = False
        self.drag_offset = QPoint()
        self.desktop_y = 0
        self.velocity_y = 0.0
        self.falling = False
        self.bubble_ticks = 0
        self._shutting_down = False

        self.place_on_floor()
        self.behavior.facing = random.choice([-1, 1])
        self.animator.set_clip("walk_right" if self.behavior.facing > 0 else "walk_left")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

    def place_on_floor(self) -> None:
        screen = self.screen_geometry()
        self.desktop_y = stand_y_on_floor(screen.bottom(), FLOOR_MARGIN)
        x = random.randint(screen.left() + 20, max(screen.left() + 21, screen.right() - self.width() - 20))
        self.move(x, self.desktop_y)

    def screen_geometry(self) -> QRect:
        screen = self.screen()
        if screen is None and self.windowHandle() is not None:
            screen = self.windowHandle().screen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)

    def tick(self) -> None:
        if self._shutting_down:
            return

        screen = self.screen_geometry()
        screen_rect = (screen.left(), screen.top(), screen.right(), screen.bottom())
        feet_x, feet_y = feet_position(self.x(), self.y(), self.width())
        platform = self.platforms.resolve(
            x=self.x(),
            y=self.y(),
            window_width=self.width(),
            screen_rect=screen_rect,
            floor_margin=FLOOR_MARGIN,
        )

        cursor = QCursor.pos()
        cursor_dx = cursor.x() - feet_x
        cursor_near = abs(cursor_dx) < 90 and abs(cursor.y() - feet_y) < 90

        output = self.behavior.tick(
            pet_feet=(feet_x, feet_y),
            pet_x=self.x(),
            platform=platform,
            screen_rect=screen_rect,
            dragging=self.dragging,
            cursor_near=cursor_near and not self.dragging,
            cursor_dx=cursor_dx,
        )

        self.animator.set_clip(output.animation)
        self.animator.tick(TICK_MS)

        if output.phrase:
            self.say(output.phrase)

        x = self.x() + output.velocity_x
        y = self.y()
        airborne = output.state in (BehaviorState.JUMP, BehaviorState.CLIMB) or self.falling or output.allow_fall

        if output.velocity_y != 0:
            self.velocity_y = output.velocity_y
            airborne = True
        elif self.falling:
            self.velocity_y += 0.65
        elif not airborne:
            self.velocity_y = 0.0

        if airborne:
            y += self.velocity_y
        elif output.lock_platform is not None:
            y = output.lock_platform.stand_y
            platform = output.lock_platform
            x = max(platform.left, min(x, platform.right))
        elif platform.is_window and output.state in (
            BehaviorState.WALK_WINDOW,
            BehaviorState.PAUSE,
            BehaviorState.SIT,
            BehaviorState.INTERACT,
        ):
            y = platform.stand_y
            x = max(platform.left, min(x, platform.right))
        else:
            y = self.desktop_y

        if airborne:
            land_feet_x, land_feet_y = feet_position(round(x), round(y), self.width())
            landing = self.platforms.find_under_feet(
                land_feet_x,
                land_feet_y,
                screen_rect,
                self.width(),
                FLOOR_MARGIN,
            )
            if landing and landing.is_window and self.velocity_y >= 0:
                y = landing.stand_y
                x = max(landing.left, min(x, landing.right))
                self.velocity_y = 0.0
                self.falling = False
                self.behavior.state = BehaviorState.WALK_WINDOW
                self.behavior.state_ticks = 0
            elif land_feet_y >= screen.bottom() - FLOOR_MARGIN:
                y = self.desktop_y
                self.velocity_y = 0.0
                self.falling = False
                if self.behavior.state == BehaviorState.CLIMB:
                    self.behavior.state = BehaviorState.ROAM
                    self.behavior.state_ticks = 0
        elif output.state in (BehaviorState.FLEE, BehaviorState.ROAM, BehaviorState.WALK_WINDOW):
            if platform.is_window:
                if x < platform.left - 4 or x > platform.right + 4:
                    self.falling = True
                    self.velocity_y = 1.5
            elif y < self.desktop_y - 8:
                self.falling = True
                self.velocity_y = 1.5

        if x <= screen.left():
            x = screen.left()
            self.behavior.facing = 1
        elif x >= screen.right() - self.width():
            x = screen.right() - self.width()
            self.behavior.facing = -1

        self.move(round(x), round(y))
        self.update_pet_frame()
        self.update_bubble()

    def update_pet_frame(self) -> None:
        frame = self.animator.current_frame()
        if frame is not None:
            self.pet_label.setPixmap(frame)

    def say(self, text: str) -> None:
        self.bubble.setText(text)
        self.bubble_ticks = 90
        self.bubble.show()

    def update_bubble(self) -> None:
        if self.bubble_ticks <= 0:
            self.bubble.hide()
            return
        self.bubble_ticks -= 1

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.falling = False
            self.velocity_y = 0.0
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.say(random.choice(["Куда идем?", "Лечу!", "Не урони!"]))
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.behavior.on_release()
            self.snap_to_surface()
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            out = self.behavior.force_jump()
            self.velocity_y = out.velocity_y
            self.falling = True
            if out.phrase:
                self.say(out.phrase)
            event.accept()

    def show_context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        jump = QAction("Подпрыгнуть", self)
        jump.triggered.connect(self.force_jump)
        wave = QAction("Помахать", self)
        wave.triggered.connect(self.wave)
        quit_action = QAction("Закрыть", self)
        quit_action.triggered.connect(self.shutdown)
        menu.addAction(jump)
        menu.addAction(wave)
        menu.addSeparator()
        menu.addAction(quit_action)
        menu.exec(point)

    def force_jump(self) -> None:
        out = self.behavior.force_jump()
        self.velocity_y = out.velocity_y
        self.falling = True
        if out.phrase:
            self.say(out.phrase)

    def wave(self) -> None:
        out = self.behavior.force_wave()
        if out.phrase:
            self.say(out.phrase)

    def snap_to_surface(self) -> None:
        screen = self.screen_geometry()
        screen_rect = (screen.left(), screen.top(), screen.right(), screen.bottom())
        self.desktop_y = stand_y_on_floor(screen.bottom(), FLOOR_MARGIN)
        feet_x, feet_y = feet_position(self.x(), self.y(), self.width())
        landing = self.platforms.find_under_feet(
            feet_x,
            feet_y,
            screen_rect,
            self.width(),
            FLOOR_MARGIN,
        )
        x = min(max(self.x(), screen.left()), screen.right() - self.width())
        if landing and landing.is_window:
            y = landing.stand_y
            x = max(landing.left, min(x, landing.right))
            self.behavior.state = BehaviorState.WALK_WINDOW
        else:
            y = self.desktop_y
        self.falling = False
        self.velocity_y = 0.0
        self.move(x, y)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.shutdown()
        event.accept()

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self.timer.stop()
        self.hide()
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.quit()
        QTimer.singleShot(1500, lambda: os._exit(0))
