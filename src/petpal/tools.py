from __future__ import annotations

from typing import Any


def create_capture_pet_photo(main_camera: Any):
    from langchain_core.tools import tool

    from .vision import capture_camera_frame, detection_result_to_json

    @tool
    def capture_pet_photo(save_image: bool = True) -> str:
        """Capture one frame from the main camera and optionally save it to outputs/captures.

        Use this when the owner asks for a photo, a visual check, or a pet status snapshot.
        The current camera image is also visible to the LLM in the conversation context.
        """

        result = capture_camera_frame(main_camera, save_image=save_image)
        return detection_result_to_json(result)

    return capture_pet_photo


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


def create_save_pet_status_report():
    from langchain_core.tools import tool

    from .reports import save_pet_status_report
    from .vision import detection_result_to_json

    @tool
    def save_pet_status(
        behavior_description: str,
        mood_estimate: str,
        attention_advice: str,
        confidence: str = "medium",
        photo_path: str | None = None,
    ) -> str:
        """Save a concise pet status report based on the visible camera image.

        Use this after visually inspecting the current camera frame. Keep wording observational:
        describe visible behavior, uncertainty, and practical owner advice. Do not make medical claims.
        """

        result = save_pet_status_report(
            behavior_description=behavior_description,
            mood_estimate=mood_estimate,
            attention_advice=attention_advice,
            confidence=confidence,
            photo_path=photo_path,
        )
        return detection_result_to_json(result)

    return save_pet_status


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
        tools.insert(0, create_capture_pet_photo(main_camera))
    tools.insert(-1, create_save_pet_status_report())
    return tools
