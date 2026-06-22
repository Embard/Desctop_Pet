"""Behavior finite state machine for desktop pet."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from context_engine import ContextDecision, ContextEngine
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


@dataclass
class BehaviorOutput:
    state: BehaviorState
    animation: str
    velocity_x: float
    velocity_y: float
    phrase: str | None = None
    target_y: int | None = None


class BehaviorController:
    WALK_SPEED = 2.2
    FLEE_SPEED = 3.4

    def __init__(self) -> None:
        self.state = BehaviorState.ROAM
        self.scanner = DesktopScanner()
        self.context = ContextEngine()
        self.actions = DesktopActions()
        self.target: Surface | None = None
        self.surface: Surface | None = None
        self.state_ticks = 0
        self.scan_cooldown = 0
        self.facing = 1

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
            return BehaviorOutput(BehaviorState.DRAG, "idle", 0.0, 0.0)

        self.scan_cooldown -= 1
        if self.scan_cooldown <= 0:
            self.scan_cooldown = 15
            self.surface = self.scanner.scan(screen_rect, pet_center)

        if cursor_near and self.state not in (BehaviorState.SIT, BehaviorState.INTERACT):
            self.state = BehaviorState.FLEE
            self.facing = -1 if cursor_dx > 0 else 1
            anim = "walk_left" if self.facing < 0 else "walk_right"
            return BehaviorOutput(
                BehaviorState.FLEE,
                anim,
                self.FLEE_SPEED * self.facing,
                0.0,
                random.choice(["Не поймаешь!", "Я убежала!"]),
            )

        self.state_ticks += 1

        if self.state == BehaviorState.JUMP:
            if self.state_ticks > 20:
                self.state = BehaviorState.ROAM
                self.state_ticks = 0
            return BehaviorOutput(BehaviorState.JUMP, "jump", 0.0, -6.0 if self.state_ticks < 10 else 4.0)

        if self.state == BehaviorState.SIT:
            if self.state_ticks > 120:
                self.state = BehaviorState.ROAM
                self.state_ticks = 0
                self.target = None
            return BehaviorOutput(BehaviorState.SIT, "sit", 0.0, 0.0)

        if self.state == BehaviorState.INTERACT:
            decision = self.context.decide(self.surface or Surface(SurfaceType.FLOOR, screen_rect), approaching=False)
            if self.state_ticks == 8 and decision.nudge_target:
                self.actions.nudge(decision.nudge_target, direction=self.facing)
            if self.state_ticks > 90:
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
            if abs(dx) < 24 and abs(dy) < 30:
                self.state = BehaviorState.SIT if self.target.kind != SurfaceType.WINDOW else BehaviorState.INTERACT
                self.state_ticks = 0
                decision = self.context.decide(self.target)
                return BehaviorOutput(
                    self.state,
                    "sit" if self.state == BehaviorState.SIT else decision.animation,
                    0.0,
                    0.0,
                    decision.phrase,
                    target_y=ty - 40 if self.state == BehaviorState.SIT else floor_y,
                )
            self.facing = 1 if dx > 0 else -1
            anim = "walk_right" if self.facing > 0 else "walk_left"
            return BehaviorOutput(BehaviorState.APPROACH, anim, self.WALK_SPEED * self.facing, 0.0)

        if self.state == BehaviorState.ROAM:
            if self.state_ticks > random.randint(100, 200):
                self.target = self.scanner.nearest_interactable(pet_center)
                if self.target:
                    self.state = BehaviorState.APPROACH
                    self.state_ticks = 0
                else:
                    self.state_ticks = 0
                    self.facing = random.choice([-1, 1])
            elif self.surface and self.surface.kind != SurfaceType.FLOOR:
                decision = self.context.decide(self.surface)
                if decision.should_interact and random.random() < 0.02:
                    self.state = BehaviorState.INTERACT
                    self.state_ticks = 0
                    return BehaviorOutput(BehaviorState.INTERACT, decision.animation, 0.0, 0.0, decision.phrase)

            anim = "walk_right" if self.facing > 0 else "walk_left"
            return BehaviorOutput(BehaviorState.ROAM, anim, self.WALK_SPEED * self.facing, 0.0)

        return BehaviorOutput(BehaviorState.ROAM, "idle", 0.0, 0.0)

    def force_jump(self) -> BehaviorOutput:
        self.state = BehaviorState.JUMP
        self.state_ticks = 0
        return BehaviorOutput(BehaviorState.JUMP, "jump", 0.0, -8.0, "Уиии!")

    def on_release(self) -> None:
        self.state = BehaviorState.ROAM
        self.state_ticks = 0
        self.facing = random.choice([-1, 1])
