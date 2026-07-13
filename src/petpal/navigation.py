from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .vision import detect_cat


ApproachAction = Literal["turn_left", "turn_right", "move_forward", "stop", "none"]


@dataclass
class ApproachDecision:
    action: ApproachAction
    reason: str
    center_error: float | None = None
    turn_degrees: float | None = None
    forward_meters: float | None = None


def decide_approach_action(
    detection_result: dict[str, Any],
    *,
    center_tolerance: float = 0.15,
    target_area_ratio: float = 0.03,
    min_turn_degrees: float = 3.0,
    max_turn_degrees: float = 10.0,
    forward_meters: float = 0.03,
) -> ApproachDecision:
    if not detection_result.get("found"):
        return ApproachDecision(action="none", reason="cat_not_found")

    best = detection_result.get("best_detection")
    image_size = detection_result.get("image_size") or {}
    if not best or not image_size.get("width"):
        return ApproachDecision(action="none", reason="missing_detection_geometry")

    width = float(image_size["width"])
    center_x = float(best["center_xy"][0])
    center_error = (center_x - width / 2.0) / (width / 2.0)
    area_ratio = float(best.get("area_ratio") or 0.0)

    if abs(center_error) > center_tolerance:
        turn_degrees = min(max_turn_degrees, max(min_turn_degrees, abs(center_error) * max_turn_degrees))
        if center_error < 0:
            return ApproachDecision(
                action="turn_left",
                reason="cat_left_of_center",
                center_error=round(center_error, 4),
                turn_degrees=round(turn_degrees, 2),
            )
        return ApproachDecision(
            action="turn_right",
            reason="cat_right_of_center",
            center_error=round(center_error, 4),
            turn_degrees=round(turn_degrees, 2),
        )

    if area_ratio < target_area_ratio:
        return ApproachDecision(
            action="move_forward",
            reason="cat_centered_and_far",
            center_error=round(center_error, 4),
            forward_meters=round(forward_meters, 3),
        )

    return ApproachDecision(
        action="stop",
        reason="cat_centered_and_close_enough",
        center_error=round(center_error, 4),
    )


def execute_approach_action(
    servo_controler: Any,
    decision: ApproachDecision,
    *,
    dry_run: bool = True,
) -> bool:
    if dry_run:
        return False

    if decision.action == "turn_left" and decision.turn_degrees is not None:
        servo_controler.turn_left(decision.turn_degrees)
        return True
    if decision.action == "turn_right" and decision.turn_degrees is not None:
        servo_controler.turn_right(decision.turn_degrees)
        return True
    if decision.action == "move_forward" and decision.forward_meters is not None:
        servo_controler.go_forward(decision.forward_meters)
        return True
    return False


def approach_cat(
    servo_controler: Any,
    camera: Any,
    *,
    max_steps: int = 1,
    confidence_threshold: float = 0.20,
    center_tolerance: float = 0.15,
    target_area_ratio: float = 0.03,
    forward_meters: float = 0.03,
    dry_run: bool = True,
    save_images: bool = True,
) -> dict[str, Any]:
    max_steps = max(1, min(int(max_steps), 5))
    forward_meters = max(0.01, min(float(forward_meters), 0.05))

    steps: list[dict[str, Any]] = []
    finished = False
    for step_index in range(max_steps):
        detection = detect_cat(
            camera,
            confidence_threshold=confidence_threshold,
            save_images=save_images,
        )
        decision = decide_approach_action(
            detection,
            center_tolerance=center_tolerance,
            target_area_ratio=target_area_ratio,
            forward_meters=forward_meters,
        )
        executed = execute_approach_action(servo_controler, decision, dry_run=dry_run)
        steps.append(
            {
                "step": step_index + 1,
                "detection": detection,
                "decision": asdict(decision),
                "executed": executed,
            }
        )

        if decision.action in {"none", "stop"}:
            finished = decision.action == "stop"
            break
        if not dry_run:
            time.sleep(0.5)

    return {
        "executed": any(step["executed"] for step in steps),
        "dry_run": dry_run,
        "finished": finished,
        "steps": steps,
    }
