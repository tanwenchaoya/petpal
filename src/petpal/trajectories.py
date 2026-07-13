from __future__ import annotations

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
    dwell_seconds: float = 0.7,
    dry_run: bool = True,
) -> dict[str, Any]:
    selected_poses = pose_names or DEFAULT_TEASE_POSES
    repeat = max(1, min(int(repeat), 5))
    dwell_seconds = max(0.1, min(float(dwell_seconds), 3.0))

    missing = [pose for pose in selected_poses if not _position_file(pose).exists()]
    if missing and not dry_run:
        return {
            "executed": False,
            "dry_run": dry_run,
            "error": "Missing saved pose files. Record these poses before running the trajectory.",
            "missing_poses": missing,
        }

    steps: list[TrajectoryStepResult] = []
    for _ in range(repeat):
        for pose_name in selected_poses:
            position_file = _position_file(pose_name)
            if dry_run:
                status = "planned_missing" if not position_file.exists() else "planned"
            else:
                servo_controler.set_saved_position(pose_name, arm_side)
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
        "steps": [asdict(step) for step in steps],
    }
