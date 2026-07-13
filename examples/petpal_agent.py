#!/usr/bin/env python

from __future__ import annotations

import argparse
import os
import threading

from petpal import (
    PetPalConfig,
    PetPalLLMConfig,
    PetPalRobotConfig,
    PetPalVoiceConfig,
    build_petpal_agent,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PetPal agent")
    parser.add_argument("--camera", type=int, default=PetPalRobotConfig.camera_index)
    parser.add_argument("--right-arm", type=str, default="/dev/cu.usbmodem5AB01579071")
    parser.add_argument("--left-arm", type=str, default="/dev/cu.usbmodem5A7C1223751")
    parser.add_argument("--task", type=str, default="慢慢往前走0.1米")
    parser.add_argument("--model", type=str, default="qwen3.5-plus-2026-02-15")
    parser.add_argument("--provider", type=str, default="openai")
    parser.add_argument("--base-url", type=str, default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    parser.add_argument("--voice", action="store_true")
    parser.add_argument("--mic-index", type=int, default=0)
    parser.add_argument("--wakeword", type=str, default="robot")
    parser.add_argument("--asr-model", type=str, default="qwen3-asr-flash")
    parser.add_argument("--tts", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--no-reset", action="store_true", help="Do not reset head or arm positions on startup")
    parser.add_argument("--init-only", action="store_true", help="Initialize camera and robot, then disconnect")
    return parser.parse_args()


def make_config(args: argparse.Namespace) -> PetPalConfig:
    return PetPalConfig(
        llm=PetPalLLMConfig(model=args.model, provider=args.provider, base_url=args.base_url),
        robot=PetPalRobotConfig(
            camera_index=args.camera,
            right_arm_port=args.right_arm,
            left_arm_port=args.left_arm,
        ),
        voice=PetPalVoiceConfig(
            enabled=args.voice,
            mic_index=args.mic_index,
            wakeword=args.wakeword,
            asr_model=args.asr_model,
            base_url=args.base_url,
        ),
        task=args.task,
        simulate=args.simulate,
        tts=args.tts,
        reset_on_start=not args.no_reset,
    )


def run_simulation(config: PetPalConfig) -> None:
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage

    if config.llm.base_url:
        os.environ.setdefault(config.llm.base_url_env, config.llm.base_url)

    llm = init_chat_model(config.llm.langchain_model_name)
    response = llm.invoke([HumanMessage(content="Reply with exactly: PetPal ready")])
    print(response.content)


def run_init_only(config: PetPalConfig) -> None:
    from robocrew.core.camera import RobotCamera
    from robocrew.robots.XLeRobot.servo_controls import ServoControler

    camera = None
    servo_controler = None
    try:
        camera = RobotCamera(config.robot.camera_index)
        image_bytes = camera.capture_image(camera_fov=90)
        print(f"Camera {config.robot.camera_index} captured {len(image_bytes)} bytes.")

        servo_controler = ServoControler(
            right_arm_wheel_usb=config.robot.right_arm_port,
            left_arm_head_usb=config.robot.left_arm_port,
        )
        print("Servo controller initialized successfully.")

        if config.reset_on_start:
            servo_controler.reset_head_position()
            servo_controler.set_saved_position("default", "both")
            print("Startup reset completed.")
        else:
            print("Startup reset skipped.")
    finally:
        if servo_controler is not None:
            print("Disconnecting servo controller...")
            servo_controler.disconnect()
        if camera is not None:
            camera.release()


def main() -> None:
    args = parse_args()
    config = make_config(args)

    if config.simulate:
        run_simulation(config)
        return

    if args.init_only:
        run_init_only(config)
        return

    agent = build_petpal_agent(config)

    def read_tasks() -> None:
        while True:
            try:
                user_input = input("\nPetPal task: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_input.lower() in {"quit", "exit", "q"}:
                break
            if user_input:
                agent.task = user_input

    threading.Thread(target=read_tasks, daemon=True).start()
    agent.go()


if __name__ == "__main__":
    main()
