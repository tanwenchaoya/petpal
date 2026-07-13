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


def create_approach_cat(servo_controler: Any, main_camera: Any):
    from langchain_core.tools import tool

    from .navigation import approach_cat
    from .vision import detection_result_to_json

    @tool
    def approach_cat_tool(
        max_steps: int = 1,
        confidence_threshold: float = 0.20,
        center_tolerance: float = 0.15,
        target_area_ratio: float = 0.03,
        forward_meters: float = 0.03,
        dry_run: bool = True,
        save_images: bool = True,
    ) -> str:
        """Take short visual-servo steps to align and approach a detected cat.

        The tool detects the cat, then chooses exactly one small action per step:
        turn_left, turn_right, move_forward, stop, or none. Keep dry_run=true unless
        the owner explicitly confirms the area is clear and asks for real movement.
        """

        result = approach_cat(
            servo_controler,
            main_camera,
            max_steps=max_steps,
            confidence_threshold=confidence_threshold,
            center_tolerance=center_tolerance,
            target_area_ratio=target_area_ratio,
            forward_meters=forward_meters,
            dry_run=dry_run,
            save_images=save_images,
        )
        return detection_result_to_json(result)

    return approach_cat_tool


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


def create_generate_daily_report():
    from langchain_core.tools import tool

    from .reports import generate_daily_report
    from .vision import detection_result_to_json

    @tool
    def generate_pet_daily_report(report_date: str | None = None) -> str:
        """Generate a simple daily report from saved pet status reports.

        report_date should use YYYYMMDD. If omitted, today's local date is used.
        """

        result = generate_daily_report(report_date=report_date)
        return detection_result_to_json(result)

    return generate_pet_daily_report


def create_record_petpal_pose(servo_controler: Any):
    from langchain_core.tools import tool

    from .trajectories import record_arm_pose
    from .vision import detection_result_to_json

    @tool
    def record_petpal_pose(position_name: str, arm_side: str = "right") -> str:
        """Record the current arm pose for later scripted playback.

        Use this during setup when a human has manually moved the arm to a useful laser-pointer pose.
        Recommended pose names: petpal_tease_left, petpal_tease_center, petpal_tease_right.
        """

        result = record_arm_pose(
            servo_controler,
            position_name=position_name,
            arm_side=arm_side,  # type: ignore[arg-type]
        )
        return detection_result_to_json(result)

    return record_petpal_pose


def create_play_with_cat(servo_controler: Any):
    from langchain_core.tools import tool

    from .trajectories import play_pose_sequence
    from .vision import detection_result_to_json

    @tool
    def play_with_cat(
        pose_names: list[str] | None = None,
        arm_side: str = "right",
        repeat: int = 1,
        dwell_seconds: float = 0.7,
        dry_run: bool = True,
    ) -> str:
        """Replay a recorded pose sequence for laser-pointer cat play.

        Keep dry_run=true unless the owner explicitly asks to run the movement and the area is clear.
        The default sequence expects petpal_tease_left, petpal_tease_center, and petpal_tease_right.
        """

        result = play_pose_sequence(
            servo_controler,
            pose_names=pose_names,
            arm_side=arm_side,  # type: ignore[arg-type]
            repeat=repeat,
            dwell_seconds=dwell_seconds,
            dry_run=dry_run,
        )
        return detection_result_to_json(result)

    return play_with_cat


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
        tools.insert(0, create_approach_cat(servo_controler, main_camera))
    tools.insert(-1, create_record_petpal_pose(servo_controler))
    tools.insert(-1, create_play_with_cat(servo_controler))
    tools.insert(-1, create_save_pet_status_report())
    tools.insert(-1, create_generate_daily_report())
    return tools
