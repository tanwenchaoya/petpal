from __future__ import annotations

import base64
import queue
import time
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from .config import PetPalVoiceConfig


PETPAL_SYSTEM_PROMPT = """
You are PetPal, an embodied pet-care robot for a home environment.

Decision rules:
- Use tools for physical actions. Do not claim a movement happened unless a tool ran.
- Prefer short, safe, observable steps over long blind movement.
- Before moving toward a pet, align the pet near the center of the camera view.
- Stop interaction if the pet leaves, appears stressed, or the task is complete.
- For photo requests, use capture_pet_photo.
- For pet status reports, inspect the current camera image, use save_pet_status, describe visible behavior
  and uncertainty, and do not make medical claims.
- For daily summaries, use generate_pet_daily_report after status reports have been saved.
- For cat-play requests, use play_with_cat only in short scripted runs. Keep dry_run true unless the owner
  explicitly asks for real movement and confirms the area is clear.
"""


class PetPalAgent:
    def __init__(
        self,
        model: str,
        tools: list[Any],
        main_camera: Any,
        *,
        voice_config: PetPalVoiceConfig | None = None,
        servo_controler: Any | None = None,
        system_prompt: str | None = None,
        thinking_level: str | None = None,
        camera_fov: int = 90,
        history_len: int | None = 8,
        tts: bool = False,
        reset_on_start: bool = True,
    ) -> None:
        self.task: str | None = None
        self.tools = tools
        self.tool_name_to_tool = {tool.name: tool for tool in self.tools}
        self.main_camera = main_camera
        self.camera_fov = camera_fov
        self.servo_controler = servo_controler
        self.history_len = history_len
        self.voice_config = voice_config
        self.task_queue: queue.Queue[str] | None = None
        self.sound_receiver = None

        prompt = system_prompt or PETPAL_SYSTEM_PROMPT
        if tts:
            from robocrew.core.tools import create_say

            self.tools.append(create_say(None))
            self.tool_name_to_tool = {tool.name: tool for tool in self.tools}
            prompt += "\nYou may use the say tool for short spoken updates."

        if voice_config and voice_config.enabled:
            from .voice import PetPalSoundReceiver

            self.task_queue = queue.Queue()
            self.sound_receiver = PetPalSoundReceiver(voice_config, self.task_queue)

        model_kwargs = {}
        if thinking_level is not None:
            model_kwargs["generation_config"] = {
                "thinking_config": {"thinking_level": thinking_level.upper()}
            }

        self.llm = init_chat_model(model, model_kwargs=model_kwargs).bind_tools(self.tools)
        self.system_message = SystemMessage(content=prompt)
        self.message_history = [self.system_message]

        if reset_on_start and self.servo_controler and getattr(self.servo_controler, "left_arm_head_usb", None):
            self.servo_controler.reset_head_position()
            self.servo_controler.set_saved_position("default", "both")

    def close(self) -> None:
        if self.sound_receiver:
            self.sound_receiver.stop()
        if self.servo_controler:
            print("Disconnecting servo controller...")
            self.servo_controler.disconnect()
        if self.main_camera and hasattr(self.main_camera, "release"):
            self.main_camera.release()

    def check_for_new_task(self) -> None:
        if self.task_queue is not None and not self.task_queue.empty():
            self.task = self.task_queue.get()

    def fetch_camera_images_base64(self) -> list[str]:
        from .vision import _capture_image_with_retry

        image_bytes = _capture_image_with_retry(self.main_camera, camera_fov=self.camera_fov)
        return [base64.b64encode(image_bytes).decode("utf-8")]

    def _trim_history(self) -> None:
        if not self.history_len:
            return
        human_indices = [i for i, msg in enumerate(self.message_history) if msg.type == "human"]
        if len(human_indices) >= self.history_len:
            start_index = human_indices[-self.history_len]
            self.message_history = [self.system_message] + self.message_history[start_index:]

    def invoke_tool(self, tool_call: dict[str, Any]) -> tuple[ToolMessage, HumanMessage | None]:
        requested_tool = self.tool_name_to_tool[tool_call["name"]]
        tool_output = requested_tool.invoke(tool_call["args"])
        if isinstance(tool_output, tuple) and len(tool_output) == 2:
            return (
                ToolMessage(tool_output[0], tool_call_id=tool_call["id"]),
                HumanMessage(content=tool_output[1]),
            )
        return ToolMessage(tool_output, tool_call_id=tool_call["id"]), None

    def run_one_step(self) -> str | None:
        if not self.task:
            return None

        camera_images = self.fetch_camera_images_base64()
        content = [
            {"type": "text", "text": "Main camera view:"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{camera_images[0]}"}},
            {"type": "text", "text": f"\n\nYour task is: '{self.task}'"},
        ]
        self.message_history.append(HumanMessage(content))
        response = self.llm.invoke(self.message_history)
        print(response.content)

        reasoning_tokens = response.usage_metadata.get("output_token_details", {}).get("reasoning", 0)
        if reasoning_tokens:
            print(f"[thinking: {reasoning_tokens} tokens]")

        self.message_history.append(response)
        self._trim_history()

        for tool_call in response.tool_calls:
            print(f"Calling {tool_call['name']} with {tool_call['args']} args")
            tool_response, additional_response = self.invoke_tool(tool_call)
            self.message_history.append(tool_response)
            if additional_response:
                self.message_history.append(additional_response)

            if tool_call["name"] == "finish_task":
                report = tool_call["args"].get("report", "Task finished")
                self.task = None
                print(f"Task finished: {report}")
                return report

        return None

    def go(self) -> None:
        try:
            while True:
                if self.task:
                    self.run_one_step()
                else:
                    time.sleep(0.5)

                if self.voice_config and self.voice_config.enabled:
                    self.check_for_new_task()
        except KeyboardInterrupt:
            print("Interrupted by user, shutting down.")
        finally:
            self.close()
