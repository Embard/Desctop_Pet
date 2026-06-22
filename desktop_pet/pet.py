import math
import random
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QImage, QPainter, QPainterPath, QPixmap, QTransform
from PySide6.QtWidgets import QLabel, QMenu, QWidget


WINDOW_WIDTH = 140
WINDOW_HEIGHT = 178
PET_WIDTH = 92
PET_HEIGHT = 132
PHOTO_HEIGHT = 96
LEGS_TOP = 88
FLOOR_MARGIN = 10
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
                border-radius: 9px;
                color: #202020;
                font: 8pt "Segoe UI";
                padding: 4px;
            }
            """
        )
        self.bubble.setGeometry(8, 6, WINDOW_WIDTH - 16, 34)
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
        fullbody_frames = self.load_fullbody_sprite_frames()
        if fullbody_frames is not None:
            return fullbody_frames

        personal_frames = self.load_personal_photo_frames()
        if personal_frames is not None:
            return personal_frames

        idle = self.load_pixmap("pet_idle.png")
        if idle is None:
            return self.fallback_frames()

        walk_frames = [
            frame
            for frame in [
                self.load_pixmap("pet_walk_1.png"),
                self.load_pixmap("pet_walk_2.png"),
            ]
            if frame is not None
        ]

        return {
            "idle": [idle],
            "walk": walk_frames or [idle],
            "jump": [self.load_pixmap("pet_jump.png") or idle],
            "action": [self.load_pixmap("pet_action.png") or idle],
        }

    def load_fullbody_sprite_frames(self) -> dict[str, list[QPixmap]] | None:
        base = self.prepare_sprite_cutout("source_sprite.png")
        if base is None:
            return None

        return {
            "idle": self.build_smooth_frames(base, "idle", 28),
            "walk": self.build_smooth_frames(base, "walk", 32),
            "jump": self.build_smooth_frames(base, "jump", 18),
            "action": self.build_smooth_frames(base, "action", 28),
        }

    def prepare_sprite_cutout(self, name: str) -> QPixmap | None:
        path = assets_dir() / name
        if not path.exists():
            return None

        source = QImage(str(path))
        if source.isNull():
            return None

        image = source.scaledToHeight(
            360,
            Qt.TransformationMode.SmoothTransformation,
        ).convertToFormat(QImage.Format.Format_ARGB32)

        self.remove_light_connected_background(image)
        cropped = self.crop_to_visible(image)
        if cropped.isNull():
            return None

        return QPixmap.fromImage(cropped).scaled(
            PET_WIDTH,
            PET_HEIGHT - 6,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def build_smooth_frames(self, base: QPixmap, mode: str, count: int) -> list[QPixmap]:
        frames = []
        for index in range(count):
            phase = index / count
            wave = math.sin(phase * math.tau)
            wave2 = math.sin(phase * math.tau * 2)

            if mode == "idle":
                y_offset = -1.5 + wave * 1.2
                x_offset = 0.0
                angle = wave * 1.1
                scale_x = 1.0
                scale_y = 1.0
                shadow_scale = 1.0 - abs(wave) * 0.04
            elif mode == "walk":
                y_offset = -2.0 - abs(wave2) * 3.0
                x_offset = wave * 2.4
                angle = wave * 3.2
                scale_x = 1.0 + abs(wave2) * 0.025
                scale_y = 1.0 - abs(wave2) * 0.018
                shadow_scale = 0.92 - abs(wave2) * 0.08
            elif mode == "jump":
                jump_arc = math.sin(phase * math.pi)
                y_offset = -4.0 - jump_arc * 18.0
                x_offset = 0.0
                angle = wave * 2.0
                scale_x = 1.0 - jump_arc * 0.025
                scale_y = 1.0 + jump_arc * 0.03
                shadow_scale = 0.9 - jump_arc * 0.32
            else:
                y_offset = -2.0 + wave * 1.8
                x_offset = wave * 1.2
                angle = -4.0 + wave * 2.0
                scale_x = 1.0
                scale_y = 1.0
                shadow_scale = 0.96

            frames.append(
                self.compose_smooth_sprite(
                    base,
                    x_offset=x_offset,
                    y_offset=y_offset,
                    angle=angle,
                    scale_x=scale_x,
                    scale_y=scale_y,
                    shadow_scale=shadow_scale,
                    wave_mark=mode == "action" and 0.15 < phase < 0.85,
                )
            )

        return frames

    def compose_smooth_sprite(
        self,
        base: QPixmap,
        *,
        x_offset: float,
        y_offset: float,
        angle: float,
        scale_x: float,
        scale_y: float,
        shadow_scale: float,
        wave_mark: bool,
    ) -> QPixmap:
        pixmap = QPixmap(PET_WIDTH, PET_HEIGHT)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 45))
        shadow_width = max(24, round(PET_WIDTH * 0.58 * shadow_scale))
        painter.drawEllipse(
            (PET_WIDTH - shadow_width) // 2,
            PET_HEIGHT - 8,
            shadow_width,
            6,
        )

        painter.translate(PET_WIDTH / 2 + x_offset, PET_HEIGHT - 8 + y_offset)
        painter.rotate(angle)
        painter.scale(scale_x, scale_y)
        painter.translate(-base.width() / 2, -base.height())
        painter.drawPixmap(0, 0, base)

        painter.resetTransform()
        if wave_mark:
            self.draw_wave_mark(painter, lift=round(y_offset))

        painter.end()
        return pixmap

    def load_personal_photo_frames(self) -> dict[str, list[QPixmap]] | None:
        idle_photo = self.prepare_photo_cutout("source_idle.png")
        pose_photo = self.prepare_photo_cutout("source_pose.png") or idle_photo
        if idle_photo is None:
            return None

        return {
            "idle": [self.compose_photo_pet(idle_photo, step=0, lift=0, lean=0)],
            "walk": [
                self.compose_photo_pet(idle_photo, step=-5, lift=0, lean=-2),
                self.compose_photo_pet(idle_photo, step=5, lift=-1, lean=2),
            ],
            "jump": [self.compose_photo_pet(pose_photo, step=0, lift=-12, lean=0)],
            "action": [self.compose_photo_pet(pose_photo, step=0, lift=0, lean=-3, wave=True)],
        }

    def prepare_photo_cutout(self, name: str) -> QPixmap | None:
        path = assets_dir() / name
        if not path.exists():
            return None

        source = QImage(str(path))
        if source.isNull():
            return None

        image = source.scaledToHeight(
            260,
            Qt.TransformationMode.SmoothTransformation,
        ).convertToFormat(QImage.Format.Format_ARGB32)

        self.remove_light_connected_background(image)
        cropped = self.crop_to_visible(image)
        if cropped.isNull():
            return None

        return QPixmap.fromImage(cropped).scaled(
            PET_WIDTH - 8,
            PHOTO_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def remove_light_connected_background(self, image: QImage) -> None:
        width = image.width()
        height = image.height()
        visited: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = []

        for x in range(width):
            stack.append((x, 0))
            stack.append((x, height - 1))
        for y in range(height):
            stack.append((0, y))
            stack.append((width - 1, y))

        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= width or y >= height or (x, y) in visited:
                continue

            visited.add((x, y))
            color = image.pixelColor(x, y)
            if not self.is_background_color(color):
                continue

            color.setAlpha(0)
            image.setPixelColor(x, y, color)
            stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    def is_background_color(self, color: QColor) -> bool:
        red = color.red()
        green = color.green()
        blue = color.blue()
        spread = max(red, green, blue) - min(red, green, blue)
        return red > 168 and green > 168 and blue > 168 and spread < 42

    def crop_to_visible(self, image: QImage) -> QImage:
        min_x = image.width()
        min_y = image.height()
        max_x = 0
        max_y = 0

        for y in range(image.height()):
            for x in range(image.width()):
                if image.pixelColor(x, y).alpha() > 0:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x <= min_x or max_y <= min_y:
            return QImage()

        padding = 4
        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        max_x = min(image.width() - 1, max_x + padding)
        max_y = min(image.height() - 1, max_y + padding)
        return image.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def compose_photo_pet(
        self,
        photo: QPixmap,
        *,
        step: int,
        lift: int,
        lean: int,
        wave: bool = False,
    ) -> QPixmap:
        pixmap = QPixmap(PET_WIDTH, PET_HEIGHT)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        shadow_y = PET_HEIGHT - 7
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 55))
        painter.drawEllipse(PET_WIDTH // 4, shadow_y, PET_WIDTH // 2, 6)

        # The source photos are waist-up, so the app adds simple legs to make a tiny full-body pet.
        self.draw_photo_legs(painter, step=step, lift=lift)

        transformed = photo.transformed(
            QTransform().rotate(lean),
            Qt.TransformationMode.SmoothTransformation,
        )
        photo_x = (PET_WIDTH - transformed.width()) // 2
        photo_y = max(0, 5 + lift)
        painter.drawPixmap(photo_x, photo_y, transformed)

        if wave:
            self.draw_wave_mark(painter, lift=lift)

        painter.end()
        return pixmap

    def draw_photo_legs(self, painter: QPainter, *, step: int, lift: int) -> None:
        leg_color = QColor("#c8cdd2")
        shoe_color = QColor("#30343f")
        top = LEGS_TOP + lift
        center = PET_WIDTH // 2
        leg_width = max(10, PET_WIDTH // 6)
        leg_height = max(26, PET_HEIGHT // 3)
        left_leg = center - leg_width - 2 + step // 3
        right_leg = center + 2 - step // 3

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(leg_color)
        painter.drawRoundedRect(left_leg, top, leg_width, leg_height, 5, 5)
        painter.drawRoundedRect(right_leg, top, leg_width, leg_height, 5, 5)

        painter.setBrush(shoe_color)
        painter.drawRoundedRect(left_leg - 4 + step, top + leg_height - 5, leg_width + 9, 7, 3, 3)
        painter.drawRoundedRect(right_leg - 1 - step, top + leg_height - 5, leg_width + 9, 7, 3, 3)

    def draw_wave_mark(self, painter: QPainter, *, lift: int) -> None:
        painter.setPen(QColor("#6c63ff"))
        painter.drawArc(PET_WIDTH - 24, 22 + lift, 12, 12, 30 * 16, 110 * 16)
        painter.drawArc(PET_WIDTH - 18, 15 + lift, 13, 13, 20 * 16, 110 * 16)

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
        pixmap = QPixmap(170, 220)
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
        return pixmap.scaled(
            PET_WIDTH,
            PET_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def place_on_floor(self) -> None:
        screen = self.screen_geometry()
        self.floor_y = screen.bottom() - self.height() - FLOOR_MARGIN
        max_x = max(screen.left() + 41, screen.right() - self.width() - 40)
        x = random.randint(screen.left() + 40, max_x)
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
        self.frame_index = (self.frame_index + 1) % max(1, len(frames))
        pixmap = frames[self.frame_index % len(frames)]

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
