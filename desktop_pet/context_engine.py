"""Contextual phrases and behavior hints based on desktop location."""

from __future__ import annotations

import random
from dataclasses import dataclass

from animation_map import animation_for_surface
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
            "Чем займёмся сегодня?",
            "Куда дальше?",
        ],
        SurfaceType.TASKBAR: [
            "Не наступай на панель задач!",
            "Осторожно, это панель!",
        ],
        SurfaceType.WINDOW: [
            "Работаем-работаем",
            "Я помогу!",
            "Нужен перерыв?",
        ],
        SurfaceType.ICON: [
            "Хочешь открыть ярлык?",
            "Я на ярлыке!",
            "Привет!",
        ],
        SurfaceType.FOLDER: [
            "Тут папка!",
            "Открыть папку?",
            "Посмотрим, что внутри?",
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

        if surface.kind == SurfaceType.WINDOW and surface.label and not approaching:
            phrase = random.choice(["Работаем-работаем", "Я помогу!", f"Окно: {surface.label[:22]}"])

        animation = animation_for_surface(surface.kind, arriving=approaching)
        should_sit = surface.kind in (SurfaceType.ICON, SurfaceType.FOLDER) and not approaching
        should_interact = surface.kind in (SurfaceType.WINDOW, SurfaceType.ICON, SurfaceType.FOLDER) and not approaching
        nudge = surface if should_interact else None

        return ContextDecision(
            animation=animation,
            phrase=phrase,
            should_sit=should_sit,
            should_interact=should_interact,
            nudge_target=nudge,
        )
