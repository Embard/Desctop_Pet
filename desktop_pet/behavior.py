"""Behavior finite state machine for desktop pet."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from context_engine import ContextEngine
from desktop_actions import DesktopActions
from desktop_scanner import DesktopScanner, Surface, SurfaceType


class BehaviorState(str, Enum):
    ROAM = "roam"
    APPROACH = "approach"
    SIT = "sit"
    INTERACT = "interact"
    FLEE = "flee"
    DRAG = "drag"
    JUMP = "jump"
    MISCHIEF = "mischief"


@dataclass
class BehaviorOutput:
    state: BehaviorState
    animation: str
    velocity_x: float
    velocity_y: float
    phrase: str | None = None
    target_y: int | None = None


class BehaviorController:
    WALK_SPEED = 2.0
    RUN_SPEED = 3.6

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
        self.state_ticks = 0

    def tick(
        self,
        *,
        pet_center: tuple[int, int],
        screen_rect: tuple[int, int, int, int],
        floor_y: int,
        dragging: bool,
        cursor_near: bool,
        cursor_dx: int,
    ) -> BehaviorOutput:
        if dragging:
            self.state = BehaviorState.DRAG
            anim = "walk_right" if self.facing > 0 else "walk_left"
            return BehaviorOutput(BehaviorState.DRAG, anim, 0.0, 0.0)

        self.scan_cooldown -= 1
        if self.scan_cooldown <= 0:
            self.scan_cooldown = 15
            self.surface = self.scanner.scan(screen_rect, pet_center)

        if cursor_near and self.state not in (BehaviorState.SIT, BehaviorState.INTERACT, BehaviorState.MISCHIEF):
            self.state = BehaviorState.FLEE
            self.facing = -1 if cursor_dx > 0 else 1
            anim = "run_left" if self.facing < 0 else "run_right"
            return BehaviorOutput(
                BehaviorState.FLEE,
                anim,
                self.RUN_SPEED * self.facing,
                0.0,
                random.choice(["Не поймаешь!", "Я убежала!", "Ха-ха!"]),
            )

        self.state_ticks += 1

        if self.state == BehaviorState.JUMP:
            if self.state_ticks <= 8:
                self.jump_phase = "up"
                anim = "jump"
                vy = -7.0
            elif self.state_ticks <= 14:
                self.jump_phase = "down"
                anim = "land"
                vy = 5.0
            else:
                self.state = BehaviorState.ROAM
                self.state_ticks = 0
                anim = "idle"
                vy = 0.0
            return BehaviorOutput(BehaviorState.JUMP, anim, 0.0, vy)

        if self.state == BehaviorState.SIT:
            if self.state_ticks > 140:
                self.state = BehaviorState.ROAM
                self.state_ticks = 0
                self.target = None
            return BehaviorOutput(BehaviorState.SIT, "sit", 0.0, 0.0)

        if self.state == BehaviorState.MISCHIEF:
            if self.state_ticks > 100:
                self.state = BehaviorState.ROAM
                self.state_ticks = 0
            return BehaviorOutput(
                BehaviorState.MISCHIEF,
                "mischief",
                0.0,
                0.0,
                "Ой, что это я натворила?" if self.state_ticks == 1 else None,
            )

        if self.state == BehaviorState.INTERACT:
            decision = self.context.decide(self.surface or Surface(SurfaceType.FLOOR, screen_rect), approaching=False)
            if self.state_ticks == 10 and decision.nudge_target:
                self.actions.nudge(decision.nudge_target, direction=self.facing)
            if self.state_ticks > 100:
                self.state = BehaviorState.ROAM
                self.state_ticks = 0
            return BehaviorOutput(
                BehaviorState.INTERACT,
                decision.animation,
                0.0,
                0.0,
                decision.phrase if self.state_ticks == 1 else None,
            )

        if self.state == BehaviorState.APPROACH and self.target:
            tx = (self.target.rect[0] + self.target.rect[2]) // 2
            ty = (self.target.rect[1] + self.target.rect[3]) // 2
            px, py = pet_center
            dx = tx - px
            dy = ty - py
            if abs(dx) < 28 and abs(dy) < 36:
                self.state = BehaviorState.SIT if self.target.kind in (SurfaceType.ICON, SurfaceType.FOLDER) else BehaviorState.INTERACT
                self.state_ticks = 0
                decision = self.context.decide(self.target)
                return BehaviorOutput(
                    self.state,
                    decision.animation if self.state == BehaviorState.INTERACT else "sit",
                    0.0,
                    0.0,
                    decision.phrase,
                    target_y=ty - 36 if self.state == BehaviorState.SIT else None,
                )
            self.facing = 1 if dx > 0 else -1
            speed = self.RUN_SPEED if abs(dx) > 120 else self.WALK_SPEED
            anim = "run_right" if self.facing > 0 else "run_left"
            if speed == self.WALK_SPEED:
                anim = "walk_right" if self.facing > 0 else "walk_left"
            return BehaviorOutput(BehaviorState.APPROACH, anim, speed * self.facing, 0.0)

        if self.state == BehaviorState.ROAM:
            if self.state_ticks > random.randint(60, 120):
                self.target = self.scanner.nearest_interactable(pet_center)
                if self.target:
                    self.state = BehaviorState.APPROACH
                    self.state_ticks = 0
                elif random.random() < 0.25:
                    self.state = BehaviorState.MISCHIEF
                    self.state_ticks = 0
                    return BehaviorOutput(BehaviorState.MISCHIEF, "mischief", 0.0, 0.0, "Уиии!")
                else:
                    self.state_ticks = 0
                    self.facing = random.choice([-1, 1])
            elif self.surface and self.surface.kind != SurfaceType.FLOOR:
                decision = self.context.decide(self.surface)
                if decision.should_interact and random.random() < 0.03:
                    self.state = BehaviorState.INTERACT
                    self.state_ticks = 0
                    return BehaviorOutput(BehaviorState.INTERACT, decision.animation, 0.0, 0.0, decision.phrase)

            anim = "walk_right" if self.facing > 0 else "walk_left"
            return BehaviorOutput(BehaviorState.ROAM, anim, self.WALK_SPEED * self.facing, 0.0)

        return BehaviorOutput(BehaviorState.ROAM, "idle", 0.0, 0.0)

    def force_jump(self) -> BehaviorOutput:
        self.state = BehaviorState.JUMP
        self.state_ticks = 0
        self.jump_phase = "up"
        return BehaviorOutput(BehaviorState.JUMP, "jump", 0.0, -8.0, "Уиии!")

    def on_release(self) -> None:
        self.state = BehaviorState.ROAM
        self.state_ticks = 0
        self.facing = random.choice([-1, 1])
