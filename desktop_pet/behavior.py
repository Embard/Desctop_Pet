"""Behavior finite state machine — human-like movement mapped to sprite clips."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from animation_map import (
    CLIMB_ONTO,
    CLIMB_UP,
    IDLE,
    JUMP,
    LAND,
    MISCHIEF,
    SIT,
    WAVE,
    animation_after_arrival,
    animation_for_approach,
    run_for_facing,
    walk_for_facing,
)
from context_engine import ContextEngine
from desktop_actions import DesktopActions
from desktop_scanner import DesktopScanner, Surface, SurfaceType
from pet_platform import PET_WINDOW_WIDTH, Platform, TITLEBAR_HEIGHT, stand_y_on_titlebar


class BehaviorState(str, Enum):
    ROAM = "roam"
    PAUSE = "pause"
    APPROACH = "approach"
    CLIMB = "climb"
    SIT = "sit"
    INTERACT = "interact"
    FLEE = "flee"
    DRAG = "drag"
    JUMP = "jump"
    MISCHIEF = "mischief"
    WALK_WINDOW = "walk_window"


@dataclass
class BehaviorOutput:
    state: BehaviorState
    animation: str
    velocity_x: float
    velocity_y: float
    phrase: str | None = None
    lock_platform: Platform | None = None
    allow_fall: bool = False


class BehaviorController:
    WALK_SPEED = 2.0
    RUN_SPEED = 3.5
    CLIMB_RISE = -3.2

    def __init__(self) -> None:
        self.state = BehaviorState.ROAM
        self.scanner = DesktopScanner()
        self.context = ContextEngine()
        self.actions = DesktopActions()
        self.target: Surface | None = None
        self.surface: Surface | None = None
        self.state_ticks = 0
        self.scan_cooldown = 0
        self.facing = random.choice([-1, 1])
        self.pause_in = random.randint(160, 260)
        self.window_target: Surface | None = None

    def tick(
        self,
        *,
        pet_feet: tuple[int, int],
        pet_x: int,
        platform: Platform,
        screen_rect: tuple[int, int, int, int],
        dragging: bool,
        cursor_near: bool,
        cursor_dx: int,
    ) -> BehaviorOutput:
        feet_x, feet_y = pet_feet

        if dragging:
            self.state = BehaviorState.DRAG
            return BehaviorOutput(BehaviorState.DRAG, walk_for_facing(self.facing), 0.0, 0.0)

        self.scan_cooldown -= 1
        if self.scan_cooldown <= 0:
            self.scan_cooldown = 15
            self.surface = self.scanner.scan(screen_rect, pet_feet)

        if self.surface and self.surface.kind == SurfaceType.TASKBAR:
            self.facing = -1 if feet_x > (screen_rect[0] + screen_rect[2]) // 2 else 1
            return BehaviorOutput(
                BehaviorState.FLEE,
                walk_for_facing(self.facing),
                self.WALK_SPEED * self.facing,
                -2.0,
                "Ой, панель задач!",
            )

        if cursor_near and self.state not in (BehaviorState.SIT, BehaviorState.INTERACT, BehaviorState.MISCHIEF):
            self.state = BehaviorState.FLEE
            self.facing = -1 if cursor_dx > 0 else 1
            return BehaviorOutput(
                BehaviorState.FLEE,
                run_for_facing(self.facing),
                self.RUN_SPEED * self.facing,
                0.0,
                random.choice(["Не поймаешь!", "Я убежала!"]),
                allow_fall=platform.is_window,
            )

        self.state_ticks += 1

        if self.state == BehaviorState.JUMP:
            if self.state_ticks <= 10:
                return BehaviorOutput(BehaviorState.JUMP, JUMP, 0.0, -6.5, allow_fall=True)
            if self.state_ticks <= 18:
                return BehaviorOutput(BehaviorState.JUMP, LAND, 0.0, 5.0, allow_fall=True)
            self.state = BehaviorState.ROAM
            self.state_ticks = 0
            return BehaviorOutput(
                BehaviorState.ROAM,
                walk_for_facing(self.facing),
                self.WALK_SPEED * self.facing,
                0.0,
            )

        if self.state == BehaviorState.PAUSE:
            if self.state_ticks > 50:
                self.state = BehaviorState.WALK_WINDOW if platform.is_window else BehaviorState.ROAM
                self.state_ticks = 0
                self.pause_in = random.randint(180, 280)
            return BehaviorOutput(
                BehaviorState.PAUSE,
                IDLE,
                0.0,
                0.0,
                lock_platform=platform if platform.is_window else None,
            )

        if self.state == BehaviorState.SIT:
            if self.state_ticks > 120:
                self.state = BehaviorState.WALK_WINDOW if platform.is_window else BehaviorState.ROAM
                self.state_ticks = 0
                self.target = None
            return BehaviorOutput(
                BehaviorState.SIT,
                SIT,
                0.0,
                0.0,
                lock_platform=platform if platform.is_window else None,
            )

        if self.state == BehaviorState.MISCHIEF:
            if self.state_ticks > 90:
                self.state = BehaviorState.WALK_WINDOW if platform.is_window else BehaviorState.ROAM
                self.state_ticks = 0
            return BehaviorOutput(
                BehaviorState.MISCHIEF,
                MISCHIEF,
                0.0,
                0.0,
                "Ой, что это я натворила?" if self.state_ticks == 1 else None,
            )

        if self.state == BehaviorState.WALK_WINDOW and platform.is_window:
            if pet_x <= platform.left + 8:
                self.facing = 1
            elif pet_x >= platform.right - 8:
                self.facing = -1

            if self.state_ticks % 300 == 0:
                next_window = self.scanner.nearest_window(pet_feet, max_dist=700)
                if next_window and next_window.handle != platform.surface.handle:
                    self.target = next_window
                    self.state = BehaviorState.APPROACH
                    self.state_ticks = 0
                    return BehaviorOutput(
                        BehaviorState.APPROACH,
                        walk_for_facing(self.facing),
                        self.WALK_SPEED * self.facing,
                        0.0,
                        lock_platform=platform,
                        allow_fall=True,
                    )

            if self.state_ticks >= self.pause_in:
                self.state = BehaviorState.PAUSE
                self.state_ticks = 0
                return BehaviorOutput(
                    BehaviorState.PAUSE,
                    IDLE,
                    0.0,
                    0.0,
                    random.choice(["Тут удобно", "Работаем дальше"]),
                    lock_platform=platform,
                )

            return BehaviorOutput(
                BehaviorState.WALK_WINDOW,
                walk_for_facing(self.facing),
                self.WALK_SPEED * self.facing,
                0.0,
                lock_platform=platform,
            )

        if self.state == BehaviorState.CLIMB and self.target:
            tx = (self.target.rect[0] + self.target.rect[2]) // 2
            title_top = self.target.rect[1]
            if abs(feet_x - tx) < 45 and feet_y <= title_top + TITLEBAR_HEIGHT + 6:
                self.state = BehaviorState.INTERACT
                self.state_ticks = 0
                self.window_target = self.target
                decision = self.context.decide(self.target)
                plat = Platform(
                    self.target,
                    stand_y_on_titlebar(title_top),
                    self.target.rect[0],
                    self.target.rect[2] - PET_WINDOW_WIDTH,
                )
                return BehaviorOutput(
                    BehaviorState.INTERACT,
                    CLIMB_ONTO,
                    0.0,
                    0.0,
                    decision.phrase,
                    lock_platform=plat,
                )
            self.facing = 1 if tx > feet_x else -1
            vx = self.WALK_SPEED * self.facing if abs(feet_x - tx) > 28 else 0.0
            return BehaviorOutput(BehaviorState.CLIMB, CLIMB_UP, vx, self.CLIMB_RISE, allow_fall=True)

        if self.state == BehaviorState.INTERACT:
            surf = self.target or self.window_target or self.surface or Surface(SurfaceType.FLOOR, screen_rect)
            decision = self.context.decide(surf, approaching=False)
            if self.state_ticks == 12 and decision.nudge_target:
                self.actions.nudge(decision.nudge_target, direction=self.facing)
            if self.state_ticks > 100:
                if surf.kind in (SurfaceType.ICON, SurfaceType.FOLDER) and random.random() < 0.35:
                    self.state = BehaviorState.SIT
                    self.state_ticks = 0
                    return BehaviorOutput(BehaviorState.SIT, SIT, 0.0, 0.0)
                if surf.kind == SurfaceType.WINDOW:
                    self.state = BehaviorState.WALK_WINDOW
                    self.state_ticks = 0
                    self.target = None
                    return BehaviorOutput(
                        BehaviorState.WALK_WINDOW,
                        walk_for_facing(self.facing),
                        self.WALK_SPEED * self.facing,
                        0.0,
                        lock_platform=platform if platform.is_window else None,
                    )
                self.state = BehaviorState.ROAM
                self.state_ticks = 0
                self.target = None
            lock = platform if platform.is_window or surf.kind == SurfaceType.WINDOW else None
            return BehaviorOutput(
                BehaviorState.INTERACT,
                decision.animation,
                0.0,
                0.0,
                decision.phrase if self.state_ticks == 1 else None,
                lock_platform=lock,
            )

        if self.state == BehaviorState.APPROACH and self.target:
            tx = (self.target.rect[0] + self.target.rect[2]) // 2
            ty = (self.target.rect[1] + self.target.rect[3]) // 2
            dx = tx - feet_x
            dy = ty - feet_y
            distance = abs(dx) + abs(dy)

            if self.target.kind == SurfaceType.WINDOW:
                title_top = self.target.rect[1]
                if abs(feet_x - tx) < 50 and feet_y > title_top + TITLEBAR_HEIGHT:
                    self.state = BehaviorState.CLIMB
                    self.state_ticks = 0
                    return BehaviorOutput(BehaviorState.CLIMB, CLIMB_UP, 0.0, self.CLIMB_RISE, allow_fall=True)
                if abs(feet_x - tx) < 45 and feet_y <= title_top + TITLEBAR_HEIGHT + 6:
                    self.state = BehaviorState.INTERACT
                    self.state_ticks = 0
                    self.window_target = self.target
                    decision = self.context.decide(self.target)
                    plat = Platform(
                        self.target,
                        stand_y_on_titlebar(title_top),
                        self.target.rect[0],
                        self.target.rect[2] - PET_WINDOW_WIDTH,
                    )
                    return BehaviorOutput(
                        BehaviorState.INTERACT,
                        CLIMB_ONTO,
                        0.0,
                        0.0,
                        decision.phrase,
                        lock_platform=plat,
                    )
            elif abs(dx) < 30 and abs(dy) < 50:
                self.state = BehaviorState.INTERACT
                self.state_ticks = 0
                decision = self.context.decide(self.target)
                anim = animation_after_arrival(self.target.kind)
                return BehaviorOutput(BehaviorState.INTERACT, anim, 0.0, 0.0, decision.phrase)

            self.facing = 1 if dx > 0 else -1
            anim, speed = animation_for_approach(self.target.kind, self.facing, distance)
            return BehaviorOutput(
                BehaviorState.APPROACH,
                anim,
                speed * self.facing,
                0.0,
                lock_platform=platform if platform.is_window else None,
                allow_fall=platform.is_window,
            )

        if self.state == BehaviorState.ROAM:
            if platform.is_window:
                self.state = BehaviorState.WALK_WINDOW
                self.state_ticks = 0
                return BehaviorOutput(
                    BehaviorState.WALK_WINDOW,
                    walk_for_facing(self.facing),
                    self.WALK_SPEED * self.facing,
                    0.0,
                    lock_platform=platform,
                )

            if self.state_ticks >= self.pause_in:
                self.state = BehaviorState.PAUSE
                self.state_ticks = 0
                return BehaviorOutput(
                    BehaviorState.PAUSE,
                    IDLE,
                    0.0,
                    0.0,
                    random.choice(["Пора отдохнуть", "Секунду..."]),
                )

            if self.state_ticks > 0 and self.state_ticks % 120 == 0:
                self.target = self.scanner.nearest_window(pet_feet, max_dist=700)
                if self.target:
                    self.state = BehaviorState.APPROACH
                    self.state_ticks = 0
                    return BehaviorOutput(
                        BehaviorState.APPROACH,
                        walk_for_facing(self.facing),
                        self.WALK_SPEED * self.facing,
                        0.0,
                    )

            if self.state_ticks > 400 and random.random() < 0.15:
                self.state = BehaviorState.MISCHIEF
                self.state_ticks = 0
                return BehaviorOutput(BehaviorState.MISCHIEF, MISCHIEF, 0.0, 0.0, "Уиии!")

            if self.state_ticks % 240 == 0:
                self.facing *= -1

            return BehaviorOutput(
                BehaviorState.ROAM,
                walk_for_facing(self.facing),
                self.WALK_SPEED * self.facing,
                0.0,
            )

        return BehaviorOutput(BehaviorState.ROAM, walk_for_facing(self.facing), self.WALK_SPEED * self.facing, 0.0)

    def force_jump(self) -> BehaviorOutput:
        self.state = BehaviorState.JUMP
        self.state_ticks = 0
        return BehaviorOutput(BehaviorState.JUMP, JUMP, 0.0, -7.0, "Уиии!", allow_fall=True)

    def force_wave(self) -> BehaviorOutput:
        self.state = BehaviorState.INTERACT
        self.state_ticks = 0
        self.target = None
        return BehaviorOutput(BehaviorState.INTERACT, WAVE, 0.0, 0.0, "Привет!")

    def on_release(self) -> None:
        self.state = BehaviorState.ROAM
        self.state_ticks = 0
        self.facing = random.choice([-1, 1])
