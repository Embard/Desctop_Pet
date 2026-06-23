"""Maps pet behavior states to sprite clips and human-like rules."""

from __future__ import annotations

from desktop_scanner import SurfaceType

# Animation clip names used by SpriteAnimator
WALK_RIGHT = "walk_right"
WALK_LEFT = "walk_left"
RUN_RIGHT = "run_right"
RUN_LEFT = "run_left"
IDLE = "idle"
JUMP = "jump"
LAND = "land"
CLIMB_UP = "climb_up"
CLIMB_ONTO = "climb_onto"
INTERACT_ICON = "interact_icon"
INTERACT_FOLDER = "interact_folder"
INTERACT_WINDOW = "interact_window"
SIT = "sit"
HAPPY = "happy"
WAVE = "wave"
COFFEE = "coffee"
MISCHIEF = "mischief"


def walk_for_facing(facing: int) -> str:
    return WALK_RIGHT if facing > 0 else WALK_LEFT


def run_for_facing(facing: int) -> str:
    return RUN_RIGHT if facing > 0 else RUN_LEFT


def animation_for_surface(kind: SurfaceType, *, arriving: bool) -> str:
    """Pick clip when pet reaches or targets a desktop surface."""
    if arriving:
        return walk_for_facing(1)

    mapping = {
        SurfaceType.FLOOR: IDLE,
        SurfaceType.TASKBAR: WALK_LEFT,
        SurfaceType.WINDOW: CLIMB_ONTO,
        SurfaceType.ICON: INTERACT_ICON,
        SurfaceType.FOLDER: INTERACT_FOLDER,
    }
    return mapping.get(kind, IDLE)


def animation_for_approach(target_kind: SurfaceType, facing: int, distance: int) -> tuple[str, float]:
    """Walk by default; run only when fleeing or hurrying to nearby icons."""
    if target_kind == SurfaceType.WINDOW:
        return walk_for_facing(facing), 2.0
    use_run = distance > 220 and target_kind in (SurfaceType.ICON, SurfaceType.FOLDER)
    if use_run:
        return run_for_facing(facing), 3.6
    return walk_for_facing(facing), 2.0


def animation_after_arrival(target_kind: SurfaceType) -> str:
    if target_kind == SurfaceType.WINDOW:
        return CLIMB_ONTO
    if target_kind == SurfaceType.FOLDER:
        return INTERACT_FOLDER
    if target_kind == SurfaceType.ICON:
        return INTERACT_ICON
    return SIT
