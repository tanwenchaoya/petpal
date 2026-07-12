from __future__ import annotations

import os

from .agent import PetPalAgent
from .config import PetPalConfig
from .tools import build_basic_petpal_tools


def configure_llm_environment(config: PetPalConfig) -> None:
    if config.llm.base_url:
        os.environ.setdefault(config.llm.base_url_env, config.llm.base_url)


def build_petpal_agent(config: PetPalConfig) -> PetPalAgent:
    configure_llm_environment(config)

    from robocrew.core.camera import RobotCamera
    from robocrew.robots.XLeRobot.servo_controls import ServoControler

    main_camera = RobotCamera(config.robot.camera_index)
    servo_controler = ServoControler(
        right_arm_wheel_usb=config.robot.right_arm_port,
        left_arm_head_usb=config.robot.left_arm_port,
    )
    tools = build_basic_petpal_tools(servo_controler)
    agent = PetPalAgent(
        model=config.llm.langchain_model_name,
        tools=tools,
        main_camera=main_camera,
        voice_config=config.voice,
        servo_controler=servo_controler,
        thinking_level=config.llm.thinking_level,
        history_len=config.history_len,
        tts=config.tts,
    )
    agent.task = config.task
    return agent
