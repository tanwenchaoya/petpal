from __future__ import annotations

from typing import Any


def create_find_cat(main_camera: Any):
    from langchain_core.tools import tool

    from .vision import detect_cat, detection_result_to_json

    @tool
    def find_cat(confidence_threshold: float = 0.25, save_images: bool = True) -> str:
        """Detect cats in the current main camera frame using YOLO.

        Use this before approaching or interacting with a cat. The tool returns whether a cat was found,
        detection boxes, confidence values, and saved image paths for debugging.
        """

        result = detect_cat(
            main_camera,
            confidence_threshold=confidence_threshold,
            save_images=save_images,
        )
        return detection_result_to_json(result)

    return find_cat


def build_basic_petpal_tools(servo_controler: Any, main_camera: Any | None = None) -> list[Any]:
    from robocrew.core.tools import finish_task
    from robocrew.robots.XLeRobot.tools import create_move_forward, create_turn_left, create_turn_right

    tools = [
        create_move_forward(servo_controler),
        create_turn_left(servo_controler),
        create_turn_right(servo_controler),
        finish_task,
    ]
    if main_camera is not None:
        tools.insert(0, create_find_cat(main_camera))
    return tools
