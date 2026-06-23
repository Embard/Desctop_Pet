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
            "Чем займёмся сегодня?",
            "Куда дальше?",
            "Скучно...",
        ],
        SurfaceType.TASKBAR: [
            "Не наступай на панель задач!",
            "Осторожно, это панель!",
        ],
        SurfaceType.WINDOW: [
            "Работаем-работаем",
            "Я помогу!",
            "Нужен перерыв?",
            "Это окно выглядит важным.",
        ],
        SurfaceType.ICON: [
            "Хочешь открыть ярлык?",
            "Я на ярлыке!",
            "Привет!",
            "Я тут главная!",
        ],
        SurfaceType.FOLDER: [
            "Тут папка!",
            "Открыть папку?",
            "Ой, что это я натворила?",
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

    SPECIAL = [
        "Вау, как красиво!",
        "Пора отдохнуть",
        "Не поймаешь!",
        "Спокойной ночи!",
    ]

    def decide(self, surface: Surface, *, approaching: bool = False) -> ContextDecision:
        label_lower = surface.label.lower()
        phrase = random.choice(self.PHRASES.get(surface.kind, self.PHRASES[SurfaceType.FLOOR]))

        for key, hint in self.APP_HINTS.items():
            if key in label_lower:
                phrase = hint
                break

        if surface.kind == SurfaceType.WINDOW and surface.label:
            short = surface.label[:22]
            if approaching:
                phrase = f"Иду к окну: {short}"
            else:
                phrase = random.choice(["Работаем-работаем", "Я помогу!", f"Окно: {short}"])

        animation = "idle"
        should_sit = False
        should_interact = False
        nudge = None

        if surface.kind == SurfaceType.TASKBAR:
            animation = "run_left"
        elif surface.kind == SurfaceType.WINDOW:
            animation = "walk_right" if approaching else "climb_onto"
            should_interact = not approaching
            nudge = None if approaching else surface
        elif surface.kind == SurfaceType.ICON:
            animation = "walk_right" if approaching else "interact_icon"
            should_sit = not approaching
            should_interact = not approaching
            nudge = None if approaching else surface
        elif surface.kind == SurfaceType.FOLDER:
            animation = "walk_right" if approaching else "interact_folder"
            should_sit = not approaching
            should_interact = not approaching
            nudge = None if approaching else surface
        else:
            animation = "walk_right" if approaching else random.choice(["idle", "happy", "coffee"])

        if random.random() < 0.08 and not approaching:
            phrase = random.choice(self.SPECIAL)

        return ContextDecision(
            animation=animation,
            phrase=phrase,
            should_sit=should_sit,
            should_interact=should_interact,
            nudge_target=nudge,
        )
