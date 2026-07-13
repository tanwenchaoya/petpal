from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal


ArmSide = Literal["left", "right", "both"]

DEFAULT_TEASE_POSES = [
    "petpal_tease_left",
    "petpal_tease_center",
    "petpal_tease_right",
    "petpal_tease_center",
]


@dataclass
class TrajectoryStepResult:
    pose_name: str
    arm_side: ArmSide
    status: str
    position_file: str | None = None


def _position_file(position_name: str) -> Path:
    from robocrew.robots.XLeRobot.servo_controls import DEFAULT_ARM_POSITION_DIR

    file_name = position_name if position_name.endswith(".json") else f"{position_name}.json"
    return Path(DEFAULT_ARM_POSITION_DIR).expanduser() / file_name


def _load_saved_pose(position_name: str, arm_side: ArmSide) -> dict[str, float]:
    path = _position_file(position_name)
    raw_data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict) or "arm_side" not in raw_data or "positions" not in raw_data:
        raise ValueError(f"Invalid saved pose file: {path}")

    saved_side = raw_data["arm_side"]
    positions = raw_data["positions"]
    if saved_side != arm_side:
        raise ValueError(f"Saved pose '{position_name}' is for '{saved_side}', not '{arm_side}'.")
    if arm_side == "both":
        raise ValueError("Smooth playback currently supports one arm at a time.")
    if not isinstance(positions, dict):
        raise ValueError(f"Invalid positions in saved pose file: {path}")
    return {name: float(value) for name, value in positions.items()}


def _interpolate_positions(
    start: dict[str, float],
    target: dict[str, float],
    *,
    interpolation_steps: int,
) -> list[dict[str, float]]:
    shared_names = [name for name in target if name in start]
    if not shared_names:
        return [target]

    frames: list[dict[str, float]] = []
    for step in range(1, interpolation_steps + 1):
        ratio = step / interpolation_steps
        frame = target.copy()
        for name in shared_names:
            frame[name] = start[name] + (target[name] - start[name]) * ratio
        frames.append(frame)
    return frames


def _move_smoothly_to_pose(
    servo_controler: Any,
    *,
    current_positions: dict[str, float],
    target_positions: dict[str, float],
    arm_side: ArmSide,
    interpolation_steps: int,
    step_seconds: float,
) -> dict[str, float]:
    for frame in _interpolate_positions(
        current_positions,
        target_positions,
        interpolation_steps=interpolation_steps,
    ):
        servo_controler.set_arm_position(frame, arm_side)
        time.sleep(step_seconds)
    return target_positions.copy()


def record_arm_pose(
    servo_controler: Any,
    *,
    position_name: str,
    arm_side: ArmSide = "right",
) -> dict[str, Any]:
    positions = servo_controler.read_arm_present_position(arm_side)
    path = servo_controler.save_arm_position(position_name, arm_side)
    return {
        "position_name": position_name,
        "arm_side": arm_side,
        "position_file": path,
        "positions": positions,
    }


def play_pose_sequence(
    servo_controler: Any,
    *,
    pose_names: list[str] | None = None,
    arm_side: ArmSide = "right",
    repeat: int = 1,
    dwell_seconds: float = 0.1,
    interpolation_steps: int = 28,
    step_seconds: float = 0.03,
    dry_run: bool = True,
) -> dict[str, Any]:
    selected_poses = pose_names or DEFAULT_TEASE_POSES
    repeat = max(1, min(int(repeat), 5))
    dwell_seconds = max(0.1, min(float(dwell_seconds), 3.0))
    interpolation_steps = max(1, min(int(interpolation_steps), 40))
    step_seconds = max(0.01, min(float(step_seconds), 0.2))

    missing = [pose for pose in selected_poses if not _position_file(pose).exists()]
    if missing and not dry_run:
        return {
            "executed": False,
            "dry_run": dry_run,
            "error": "Missing saved pose files. Record these poses before running the trajectory.",
            "missing_poses": missing,
        }
    if arm_side == "both" and not dry_run:
        return {
            "executed": False,
            "dry_run": dry_run,
            "error": "Smooth playback supports one arm at a time. Use --arm-side left or --arm-side right.",
        }

    steps: list[TrajectoryStepResult] = []
    current_positions = None
    if not dry_run:
        current_positions = servo_controler.read_arm_present_position(arm_side)

    for _ in range(repeat):
        for pose_name in selected_poses:
            position_file = _position_file(pose_name)
            if dry_run:
                status = "planned_missing" if not position_file.exists() else "planned"
            else:
                target_positions = _load_saved_pose(pose_name, arm_side)
                current_positions = _move_smoothly_to_pose(
                    servo_controler,
                    current_positions=current_positions,
                    target_positions=target_positions,
                    arm_side=arm_side,
                    interpolation_steps=interpolation_steps,
                    step_seconds=step_seconds,
                )
                status = "executed"
                time.sleep(dwell_seconds)
            steps.append(
                TrajectoryStepResult(
                    pose_name=pose_name,
                    arm_side=arm_side,
                    status=status,
                    position_file=str(position_file),
                )
            )

    return {
        "executed": not dry_run,
        "dry_run": dry_run,
        "repeat": repeat,
        "dwell_seconds": dwell_seconds,
        "interpolation_steps": interpolation_steps,
        "step_seconds": step_seconds,
        "steps": [asdict(step) for step in steps],
    }
