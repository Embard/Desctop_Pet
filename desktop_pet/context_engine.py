"""Contextual phrases and behavior hints based on desktop location."""

from __future__ import annotations

import random
from dataclasses import dataclass

from desktop_scanner import Surface, SurfaceType


@dataclass
class ContextDecision:
    animation: str
    phrase: str
    should_sit: bool
    should_interact: bool
    nudge_target: Surface | None = None


class ContextEngine:
    PHRASES = {
        SurfaceType.FLOOR: [
            "Гуляю по рабочему столу.",
            "Тут свободно, можно побегать.",
            "Куда дальше?",
        ],
        SurfaceType.TASKBAR: [
            "Не наступай на панель задач!",
            "Осторожно, это панель!",
        ],
        SurfaceType.WINDOW: [
            "Работаем?",
            "Это окно выглядит важным.",
            "Можно тут постоять.",
        ],
        SurfaceType.ICON: [
            "Хочешь открыть ярлык?",
            "Я на ярлыке!",
            "Кликни, если нужно.",
        ],
        SurfaceType.FOLDER: [
            "Тут папка!",
            "Открыть папку?",
            "Документы рядом.",
        ],
    }

    APP_HINTS = {
        "chrome": "Хочешь в интернет?",
        "firefox": "Пойдем в браузер?",
        "word": "Пишем документ?",
        "excel": "Считаем таблицы?",
        "telegram": "Кому-то написать?",
        "discord": "Общаемся?",
        "explorer": "Смотрим файлы?",
    }

    def decide(self, surface: Surface, *, approaching: bool = False) -> ContextDecision:
        label_lower = surface.label.lower()
        phrase = random.choice(self.PHRASES.get(surface.kind, self.PHRASES[SurfaceType.FLOOR]))

        for key, hint in self.APP_HINTS.items():
            if key in label_lower:
                phrase = hint
                break

        if surface.kind == SurfaceType.WINDOW and surface.label:
            phrase = f"{phrase} ({surface.label[:24]})"

        animation = "idle"
        should_sit = False
        should_interact = False
        nudge = None

        if surface.kind == SurfaceType.TASKBAR:
            animation = "walk_left"
        elif surface.kind in (SurfaceType.ICON, SurfaceType.FOLDER, SurfaceType.WINDOW):
            if approaching:
                animation = "walk_right"
            else:
                animation = {
                    SurfaceType.WINDOW: "interact_window",
                    SurfaceType.ICON: "interact_icon",
                    SurfaceType.FOLDER: "interact_folder",
                }[surface.kind]
                should_sit = surface.kind != SurfaceType.WINDOW
                should_interact = True
                nudge = surface
        else:
            animation = "walk_right" if approaching else "idle"

        return ContextDecision(
            animation=animation,
            phrase=phrase,
            should_sit=should_sit,
            should_interact=should_interact,
            nudge_target=nudge,
        )
