#!/usr/bin/env python

from __future__ import annotations

import argparse

from petpal.config import PetPalRobotConfig
from petpal.navigation import approach_cat
from petpal.vision import detection_result_to_json


class DryRunServo:
    def turn_left(self, degrees: float) -> None:
        raise RuntimeError("Dry-run servo should not move.")

    def turn_right(self, degrees: float) -> None:
        raise RuntimeError("Dry-run servo should not move.")

    def go_forward(self, meters: float) -> None:
        raise RuntimeError("Dry-run servo should not move.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PetPal visual-servo cat approach")
    parser.add_argument("--camera", type=int, default=PetPalRobotConfig.camera_index)
    parser.add_argument("--right-arm", type=str, default=PetPalRobotConfig.right_arm_port)
    parser.add_argument("--left-arm", type=str, default=PetPalRobotConfig.left_arm_port)
    parser.add_argument("--max-steps", type=int, default=1)
    parser.add_argument("--confidence-threshold", type=float, default=0.20)
    parser.add_argument("--center-tolerance", type=float, default=0.15)
    parser.add_argument("--target-area-ratio", type=float, default=0.03)
    parser.add_argument("--forward-meters", type=float, default=0.03)
    parser.add_argument("--no-save-images", action="store_true")
    parser.add_argument("--run", action="store_true", help="Actually move the robot")
    return parser.parse_args()


def main() -> None:
    from robocrew.core.camera import RobotCamera

    args = parse_args()
    camera = RobotCamera(args.camera)
    servo = DryRunServo()

    try:
        if args.run:
            from robocrew.robots.XLeRobot.servo_controls import ServoControler

            servo = ServoControler(
                right_arm_wheel_usb=args.right_arm,
                left_arm_head_usb=args.left_arm,
            )

        result = approach_cat(
            servo,
            camera,
            max_steps=args.max_steps,
            confidence_threshold=args.confidence_threshold,
            center_tolerance=args.center_tolerance,
            target_area_ratio=args.target_area_ratio,
            forward_meters=args.forward_meters,
            dry_run=not args.run,
            save_images=not args.no_save_images,
        )
        print(detection_result_to_json(result))
    finally:
        if args.run and hasattr(servo, "disconnect"):
            servo.disconnect()
        camera.release()


if __name__ == "__main__":
    main()
