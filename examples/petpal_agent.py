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
    parser.add_argument("--camera", type=int, default=2)
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
    )


def run_simulation(config: PetPalConfig) -> None:
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage

    if config.llm.base_url:
        os.environ.setdefault(config.llm.base_url_env, config.llm.base_url)

    llm = init_chat_model(config.llm.langchain_model_name)
    response = llm.invoke([HumanMessage(content="Reply with exactly: PetPal ready")])
    print(response.content)


def main() -> None:
    args = parse_args()
    config = make_config(args)

    if config.simulate:
        run_simulation(config)
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
