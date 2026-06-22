import random
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QPainter, QPainterPath, QPixmap, QTransform
from PySide6.QtWidgets import QLabel, QMenu, QWidget


WINDOW_WIDTH = 230
WINDOW_HEIGHT = 280
PET_WIDTH = 170
PET_HEIGHT = 220
FLOOR_MARGIN = 18
TICK_MS = 33


def app_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def assets_dir() -> Path:
    return app_root() / "assets"


class PetWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
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
        self.pet_label.setGeometry(
            (WINDOW_WIDTH - PET_WIDTH) // 2,
            WINDOW_HEIGHT - PET_HEIGHT,
            PET_WIDTH,
            PET_HEIGHT,
        )

        self.bubble = QLabel(self)
        self.bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bubble.setWordWrap(True)
        self.bubble.setStyleSheet(
            """
            QLabel {
                background: rgba(255, 255, 255, 230);
                border: 1px solid rgba(40, 40, 40, 130);
                border-radius: 12px;
                color: #202020;
                font: 11pt "Segoe UI";
                padding: 6px;
            }
            """
        )
        self.bubble.setGeometry(18, 10, WINDOW_WIDTH - 36, 48)
        self.bubble.hide()

        self.frames = self.load_frames()
        self.frame_index = 0
        self.state = "idle"
        self.drag_offset = QPoint()
        self.dragging = False
        self.velocity_x = random.choice([-2.4, 2.4])
        self.velocity_y = 0.0
        self.floor_y = 0
        self.idle_ticks = 0
        self.action_ticks = 0
        self.bubble_ticks = 0

        self.place_on_floor()
        self.update_pet_frame()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_MS)

    def load_frames(self) -> dict[str, list[QPixmap]]:
        loaded = {
            "idle": self.load_pixmap("pet_idle.png"),
            "walk": [
                self.load_pixmap("pet_walk_1.png"),
                self.load_pixmap("pet_walk_2.png"),
            ],
            "jump": self.load_pixmap("pet_jump.png"),
            "action": self.load_pixmap("pet_action.png"),
        }

        if loaded["idle"]:
            idle = loaded["idle"]
            walk = [frame for frame in loaded["walk"] if frame]
            return {
                "idle": [idle],
                "walk": walk or [idle],
                "jump": [loaded["jump"] or idle],
                "action": [loaded["action"] or idle],
            }

        return self.fallback_frames()

    def load_pixmap(self, name: str) -> QPixmap | None:
        path = assets_dir() / name
        if not path.exists():
            return None

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None

        return pixmap.scaled(
            PET_WIDTH,
            PET_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def fallback_frames(self) -> dict[str, list[QPixmap]]:
        return {
            "idle": [self.draw_person(arm_angle=0, step=0)],
            "walk": [
                self.draw_person(arm_angle=-18, step=-12),
                self.draw_person(arm_angle=18, step=12),
            ],
            "jump": [self.draw_person(arm_angle=24, step=0, jump=True)],
            "action": [self.draw_person(arm_angle=-35, step=0, wink=True)],
        }

    def draw_person(
        self,
        *,
        arm_angle: int,
        step: int,
        jump: bool = False,
        wink: bool = False,
    ) -> QPixmap:
        pixmap = QPixmap(PET_WIDTH, PET_HEIGHT)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        lift = -18 if jump else 0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#3a2a22"))
        painter.drawEllipse(52, 18 + lift, 66, 58)
        painter.drawRoundedRect(38, 55 + lift, 94, 72, 34, 34)

        painter.setBrush(QColor("#f0c7a8"))
        painter.drawEllipse(55, 30 + lift, 60, 58)

        painter.setBrush(QColor("#6c63ff"))
        body = QPainterPath()
        body.moveTo(58, 92 + lift)
        body.cubicTo(42, 122 + lift, 42, 170 + lift, 84, 176 + lift)
        body.cubicTo(128, 170 + lift, 128, 122 + lift, 110, 92 + lift)
        body.closeSubpath()
        painter.drawPath(body)

        painter.setBrush(QColor("#f0c7a8"))
        painter.drawRoundedRect(33, 106 + lift + arm_angle // 4, 28, 72, 14, 14)
        painter.drawRoundedRect(108, 106 + lift - arm_angle // 4, 28, 72, 14, 14)

        painter.setBrush(QColor("#202020"))
        painter.drawEllipse(72, 55 + lift, 6, 6)
        if wink:
            painter.drawRoundedRect(91, 57 + lift, 13, 3, 2, 2)
        else:
            painter.drawEllipse(95, 55 + lift, 6, 6)

        painter.setBrush(QColor("#e76f8a"))
        painter.drawRoundedRect(78, 72 + lift, 18, 6, 3, 3)

        painter.setBrush(QColor("#30343f"))
        painter.drawRoundedRect(58 + step // 5, 164 + lift, 25, 50, 12, 12)
        painter.drawRoundedRect(92 - step // 5, 164 + lift, 25, 50, 12, 12)

        painter.setBrush(QColor(0, 0, 0, 45))
        painter.drawEllipse(42, 210, 86, 10)
        painter.end()
        return pixmap

    def place_on_floor(self) -> None:
        screen = self.screen_geometry()
        self.floor_y = screen.bottom() - self.height() - FLOOR_MARGIN
        x = screen.left() + random.randint(40, max(41, screen.width() - self.width() - 40))
        self.move(x, self.floor_y)

    def screen_geometry(self) -> QRect:
        screen = self.screen()
        if screen is None and self.windowHandle() is not None:
            screen = self.windowHandle().screen()
        if screen is None:
            return QRect(0, 0, 1280, 720)
        return screen.availableGeometry()

    def tick(self) -> None:
        if self.dragging:
            return

        self.handle_cursor_reaction()
        self.update_position()
        self.update_state()
        self.update_pet_frame()
        self.update_bubble()

    def handle_cursor_reaction(self) -> None:
        cursor = QCursor.pos()
        center = self.geometry().center()
        distance_x = cursor.x() - center.x()
        distance_y = cursor.y() - center.y()

        if abs(distance_x) < 115 and abs(distance_y) < 105 and self.state != "jump":
            self.state = "walk"
            self.velocity_x = -3.6 if distance_x > 0 else 3.6
            if random.random() < 0.04:
                self.say(random.choice(["Не поймаешь!", "Я убежала!", "Ха-ха!"]))

    def update_position(self) -> None:
        screen = self.screen_geometry()
        x = self.x() + self.velocity_x
        y = self.y() + self.velocity_y

        if self.state == "jump":
            self.velocity_y += 0.55
            if y >= self.floor_y:
                y = self.floor_y
                self.velocity_y = 0.0
                self.state = "idle"

        if x <= screen.left():
            x = screen.left()
            self.velocity_x = abs(self.velocity_x)
            self.say("Тук-тук!")
        elif x >= screen.right() - self.width():
            x = screen.right() - self.width()
            self.velocity_x = -abs(self.velocity_x)
            self.say("Ой, край!")

        self.move(round(x), round(y))

    def update_state(self) -> None:
        if self.state == "action":
            self.action_ticks -= 1
            if self.action_ticks <= 0:
                self.state = "idle"
            return

        if self.state == "jump":
            return

        self.idle_ticks += 1
        if abs(self.velocity_x) > 0:
            self.state = "walk"

        if self.idle_ticks > random.randint(90, 170):
            self.idle_ticks = 0
            choice = random.choice(["idle", "walk", "jump", "action"])
            if choice == "idle":
                self.velocity_x = 0.0
                self.state = "idle"
            elif choice == "walk":
                self.velocity_x = random.choice([-2.4, 2.4])
                self.state = "walk"
            elif choice == "jump":
                self.velocity_y = -8.5
                self.state = "jump"
            else:
                self.start_action()

    def start_action(self) -> None:
        self.state = "action"
        self.action_ticks = 48
        self.velocity_x = random.choice([-1.5, 1.5])
        self.say(random.choice(["Привет!", "Я тут гуляю.", "Кликни меня!", "Можно перетащить."]))

    def update_pet_frame(self) -> None:
        frames = self.frames.get(self.state, self.frames["idle"])
        self.frame_index = (self.frame_index + 1) % max(1, len(frames) * 12)
        pixmap = frames[(self.frame_index // 12) % len(frames)]

        if self.velocity_x < 0:
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))

        self.pet_label.setPixmap(pixmap)

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
            self.state = "drag"
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.say(random.choice(["Куда идем?", "Лечу!", "Не урони!"]))
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if not self.dragging:
            return

        self.move(event.globalPosition().toPoint() - self.drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.dragging = False
        self.velocity_x = random.choice([-2.4, 2.4])
        self.velocity_y = 0.0
        self.snap_to_floor()
        self.state = "walk"
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self.velocity_y = -9.5
            self.state = "jump"
            self.say("Уиии!")
            event.accept()

    def show_context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        jump_action = QAction("Подпрыгнуть", self)
        jump_action.triggered.connect(self.force_jump)
        wave_action = QAction("Помахать", self)
        wave_action.triggered.connect(self.start_action)
        quit_action = QAction("Закрыть", self)
        quit_action.triggered.connect(self.close)

        menu.addAction(jump_action)
        menu.addAction(wave_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        menu.exec(point)

    def force_jump(self) -> None:
        self.velocity_y = -9.5
        self.state = "jump"
        self.say("Прыг!")

    def snap_to_floor(self) -> None:
        screen = self.screen_geometry()
        x = min(max(self.x(), screen.left()), screen.right() - self.width())
        self.floor_y = screen.bottom() - self.height() - FLOOR_MARGIN
        self.move(x, self.floor_y)
