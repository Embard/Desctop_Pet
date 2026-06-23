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

WINDOW_WIDTH = 96
WINDOW_HEIGHT = 168
PET_W = 84
PET_H = 126
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
        self.dragging = False
        self.drag_offset = QPoint()
        self.floor_y = 0
        self.velocity_y = 0.0
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
        self.floor_y = screen.bottom() - self.height() - FLOOR_MARGIN
        x = random.randint(screen.left() + 20, max(screen.left() + 21, screen.right() - self.width() - 20))
        self.move(x, self.floor_y)

    def screen_geometry(self) -> QRect:
        screen = self.screen()
        if screen is None and self.windowHandle() is not None:
            screen = self.windowHandle().screen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)

    def tick(self) -> None:
        if self._shutting_down:
            return

        screen = self.screen_geometry()
        center = self.geometry().center()
        cursor = QCursor.pos()
        cursor_dx = cursor.x() - center.x()
        cursor_near = abs(cursor_dx) < 90 and abs(cursor.y() - center.y()) < 80

        output = self.behavior.tick(
            pet_center=(center.x(), center.y()),
            screen_rect=(screen.left(), screen.top(), screen.right(), screen.bottom()),
            floor_y=self.floor_y,
            dragging=self.dragging,
            cursor_near=cursor_near and not self.dragging,
            cursor_dx=cursor_dx,
        )

        self.animator.set_clip(output.animation)
        self.animator.tick(TICK_MS)

        if output.phrase:
            self.say(output.phrase)

        x = self.x() + output.velocity_x
        y = self.y() + self.velocity_y

        if output.state == BehaviorState.JUMP or self.velocity_y != 0:
            self.velocity_y = output.velocity_y if output.state == BehaviorState.JUMP else self.velocity_y + 0.55
            y += self.velocity_y
            if y >= self.floor_y:
                y = self.floor_y
                self.velocity_y = 0.0

        if output.target_y is not None and output.state == BehaviorState.SIT:
            y = min(y, output.target_y)

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
            self.snap_to_floor()
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            out = self.behavior.force_jump()
            self.velocity_y = out.velocity_y
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
        if out.phrase:
            self.say(out.phrase)

    def wave(self) -> None:
        self.behavior.state = BehaviorState.INTERACT
        self.behavior.state_ticks = 0
        self.animator.set_clip("wave")
        self.say("Привет!")

    def snap_to_floor(self) -> None:
        screen = self.screen_geometry()
        x = min(max(self.x(), screen.left()), screen.right() - self.width())
        self.floor_y = screen.bottom() - self.height() - FLOOR_MARGIN
        self.move(x, self.floor_y)

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
