#!/usr/bin/env python

from __future__ import annotations

import argparse
from pathlib import Path

from petpal.config import PetPalRobotConfig
from petpal.trajectories import play_pose_sequence, record_arm_pose
from petpal.vision import detection_result_to_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record and replay PetPal arm trajectories")
    parser.add_argument("command", choices=["ports", "release", "hold", "record", "play"])
    parser.add_argument("--position-name", type=str, default="petpal_tease_center")
    parser.add_argument("--arm-side", choices=["left", "right", "both"], default="right")
    parser.add_argument("--right-arm", type=str, default=PetPalRobotConfig.right_arm_port)
    parser.add_argument("--left-arm", type=str, default=PetPalRobotConfig.left_arm_port)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--dwell-seconds", type=float, default=0.7)
    parser.add_argument("--run", action="store_true", help="Actually move the robot when playing")
    return parser.parse_args()


def print_ports() -> None:
    patterns = ["cu.usb*", "tty.usb*", "cu.*modem*", "tty.*modem*"]
    ports = []
    for pattern in patterns:
        ports.extend(str(path) for path in Path("/dev").glob(pattern))
    for port in sorted(set(ports)):
        print(port)
    if not ports:
        print("No USB serial ports found.")


def main() -> None:
    from robocrew.robots.XLeRobot.servo_controls import ServoControler

    args = parse_args()

    if args.command == "ports":
        print_ports()
        return

    if args.command == "play" and not args.run:
        result = play_pose_sequence(
            object(),
            arm_side=args.arm_side,
            repeat=args.repeat,
            dwell_seconds=args.dwell_seconds,
            dry_run=True,
        )
        print(detection_result_to_json(result))
        return

    servo = ServoControler(
        right_arm_wheel_usb=args.right_arm,
        left_arm_head_usb=args.left_arm,
    )
    try:
        if args.command == "release":
            servo.disable_torque("arms")
            print("Arm torque disabled. Move the arm by hand, then run the record command.")
            return

        if args.command == "hold":
            servo.enable_torque("arms")
            print("Arm torque enabled.")
            return

        if args.command == "record":
            result = record_arm_pose(
                servo,
                position_name=args.position_name,
                arm_side=args.arm_side,
            )
            print(detection_result_to_json(result))
            return

        result = play_pose_sequence(
            servo,
            arm_side=args.arm_side,
            repeat=args.repeat,
            dwell_seconds=args.dwell_seconds,
            dry_run=not args.run,
        )
        print(detection_result_to_json(result))
    finally:
        servo.disconnect()


if __name__ == "__main__":
    main()
