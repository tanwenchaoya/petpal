#!/usr/bin/env python

from __future__ import annotations

import argparse

from petpal.config import PetPalRobotConfig
from petpal.navigation import approach_cat
from petpal.reports import generate_daily_report, save_pet_status_report
from petpal.trajectories import play_pose_sequence
from petpal.vision import capture_camera_frame, detection_result_to_json


class DryRunServo:
    def turn_left(self, degrees: float) -> None:
        raise RuntimeError("Dry-run servo should not move.")

    def turn_right(self, degrees: float) -> None:
        raise RuntimeError("Dry-run servo should not move.")

    def go_forward(self, meters: float) -> None:
        raise RuntimeError("Dry-run servo should not move.")

    def read_arm_present_position(self, arm_side: str = "right") -> dict[str, float]:
        return {}

    def set_arm_position(self, positions: dict[str, float], arm_side: str = "right") -> dict[str, float]:
        raise RuntimeError("Dry-run servo should not move.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a deterministic PetPal MVP demo")
    parser.add_argument("--camera", type=int, default=PetPalRobotConfig.camera_index)
    parser.add_argument("--right-arm", type=str, default=PetPalRobotConfig.right_arm_port)
    parser.add_argument("--left-arm", type=str, default=PetPalRobotConfig.left_arm_port)
    parser.add_argument("--run-approach", action="store_true", help="Actually run one small approach step")
    parser.add_argument("--run-play", action="store_true", help="Actually run the recorded cat-play trajectory")
    parser.add_argument("--approach-steps", type=int, default=1)
    parser.add_argument("--forward-meters", type=float, default=0.02)
    parser.add_argument("--confidence-threshold", type=float, default=0.20)
    return parser.parse_args()


def _status_from_approach(approach_result: dict) -> tuple[str, str, str, str]:
    step = approach_result["steps"][-1]
    detection = step["detection"]
    decision = step["decision"]

    if detection.get("found"):
        behavior = (
            "从头部摄像头画面中检测到猫。当前演示报告只基于目标框位置和画面观察，"
            f"靠近策略判断为 {decision['action']}，原因是 {decision['reason']}。"
        )
        mood = "无法准确判断，画面中未见明显应激动作"
        advice = "可以继续观察猫是否愿意互动；如果猫离开或回避，应停止逗猫。"
        confidence = "medium"
    else:
        behavior = "当前头部摄像头画面没有稳定检测到猫。机器人没有执行盲目前进。"
        mood = "unknown"
        advice = "建议先调整机器人朝向或等待猫进入头部摄像头视野，再继续靠近测试。"
        confidence = "low"
    return behavior, mood, advice, confidence


def main() -> None:
    from robocrew.core.camera import RobotCamera

    args = parse_args()
    camera = RobotCamera(args.camera)
    servo = DryRunServo()

    try:
        if args.run_approach or args.run_play:
            from robocrew.robots.XLeRobot.servo_controls import ServoControler

            servo = ServoControler(
                right_arm_wheel_usb=args.right_arm,
                left_arm_head_usb=args.left_arm,
            )

        photo = capture_camera_frame(camera, prefix="demo_photo", save_image=True)
        print("PHOTO")
        print(detection_result_to_json(photo))

        approach_result = approach_cat(
            servo,
            camera,
            max_steps=args.approach_steps,
            confidence_threshold=args.confidence_threshold,
            forward_meters=args.forward_meters,
            dry_run=not args.run_approach,
            save_images=True,
        )
        print("APPROACH")
        print(detection_result_to_json(approach_result))

        behavior, mood, advice, confidence = _status_from_approach(approach_result)
        status_report = save_pet_status_report(
            behavior_description=behavior,
            mood_estimate=mood,
            attention_advice=advice,
            confidence=confidence,
            photo_path=photo["image_path"],
        )
        print("STATUS_REPORT")
        print(detection_result_to_json(status_report))

        play_result = play_pose_sequence(
            servo,
            arm_side="right",
            repeat=1,
            dry_run=not args.run_play,
        )
        print("CAT_PLAY")
        print(detection_result_to_json(play_result))

        daily_report = generate_daily_report()
        print("DAILY_REPORT")
        print(detection_result_to_json(daily_report))
    finally:
        if hasattr(servo, "disconnect"):
            servo.disconnect()
        camera.release()


if __name__ == "__main__":
    main()
