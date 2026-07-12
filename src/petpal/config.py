from __future__ import annotations

from dataclasses import dataclass


DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


@dataclass
class PetPalLLMConfig:
    model: str = "qwen3.5-plus-2026-02-15"
    provider: str = "openai"
    base_url: str | None = DEFAULT_DASHSCOPE_BASE_URL
    api_key_env: str = "OPENAI_API_KEY"
    base_url_env: str = "OPENAI_BASE_URL"
    thinking_level: str | None = None

    @property
    def langchain_model_name(self) -> str:
        if ":" in self.model:
            return self.model
        return f"{self.provider}:{self.model}"


@dataclass
class PetPalVoiceConfig:
    enabled: bool = False
    mic_index: int | None = 0
    wakeword: str = "robot"
    asr_model: str = "qwen3-asr-flash"
    asr_language: str = "zh"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = DEFAULT_DASHSCOPE_BASE_URL
    rms_threshold: float = 200.0
    silence_seconds: float = 2.0
    min_recording_seconds: float = 1.5


@dataclass
class PetPalRobotConfig:
    camera_index: int = 0
    right_arm_port: str = "/dev/cu.usbmodem5AB01579071"
    left_arm_port: str = "/dev/cu.usbmodem5A7C1223751"


@dataclass
class PetPalConfig:
    llm: PetPalLLMConfig
    robot: PetPalRobotConfig
    voice: PetPalVoiceConfig
    task: str = "慢慢往前走0.1米"
    simulate: bool = False
    tts: bool = False
    reset_on_start: bool = True
    history_len: int | None = 8
