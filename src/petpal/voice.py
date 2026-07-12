from __future__ import annotations

import base64
import os
import queue
import threading
import time
import wave
from io import BytesIO

import numpy as np
from openai import OpenAI

from .config import PetPalVoiceConfig


class PetPalSoundReceiver:
    def __init__(self, config: PetPalVoiceConfig, task_queue: queue.Queue[str]) -> None:
        import pyaudio

        self.config = config
        self.task_queue = task_queue
        self.pyaudio = pyaudio
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.frames_per_buffer = 1024
        self.sample_width = 2
        self.recorded_frames: list[bytes] = []
        self.num_recorded_buffers = 0
        self.first_silent_timestamp: float | None = None
        self.recording = False
        self.listening = False
        self.lock = threading.RLock()
        self.stream = None
        self.audio = pyaudio.PyAudio()
        self.thread = threading.Thread(target=self._recorder_loop, daemon=True)
        self.start_listening()

    def start_listening(self) -> None:
        if self.listening:
            return
        print(f"[PetPalVoice] Starting microphone listener (device: {self.config.mic_index})")
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.config.mic_index,
            frames_per_buffer=self.frames_per_buffer,
            stream_callback=self._audio_callback,
        )
        self.stream.start_stream()
        self.listening = True
        if not self.thread.is_alive():
            self.thread.start()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        if self.recording:
            with self.lock:
                self.recorded_frames.append(in_data)
                self.num_recorded_buffers += 1
        self.last_frame = in_data
        return (None, self.pyaudio.paContinue)

    def _recorder_loop(self) -> None:
        while True:
            if not self.listening:
                time.sleep(0.1)
                continue

            rms = self._last_rms()
            if not self.recording and rms > self.config.rms_threshold:
                self.recording = True
                with self.lock:
                    self.recorded_frames = []
                    self.num_recorded_buffers = 0
            elif self.recording and rms < self.config.rms_threshold:
                if self.first_silent_timestamp is None:
                    self.first_silent_timestamp = time.time()
                elif time.time() - self.first_silent_timestamp > self.config.silence_seconds:
                    self._finish_recording()
            elif self.recording:
                self.first_silent_timestamp = None

            time.sleep(0.1)

    def _finish_recording(self) -> None:
        self.recording = False
        self.first_silent_timestamp = None
        with self.lock:
            audio_data = b"".join(self.recorded_frames)
            buffer_count = self.num_recorded_buffers
            self.recorded_frames = []
            self.num_recorded_buffers = 0

        seconds = buffer_count * self.frames_per_buffer / self.rate
        if seconds < self.config.min_recording_seconds:
            print("[PetPalVoice] Recording too short, skipped.")
            return

        print("[PetPalVoice] Recording complete, transcribing...")
        threading.Thread(target=self._transcribe_audio, args=(audio_data,), daemon=True).start()

    def _last_rms(self) -> float:
        data = getattr(self, "last_frame", b"")
        if len(data) < 2:
            return 0.0
        frame = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        if frame.size == 0:
            return 0.0
        return float(np.sqrt(np.dot(frame, frame) / frame.size))

    def _transcribe_audio(self, audio_data: bytes) -> None:
        try:
            wav_buffer = BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self.sample_width)
                wav_file.setframerate(self.rate)
                wav_file.writeframes(audio_data)
            wav_buffer.seek(0)

            audio_b64 = base64.b64encode(wav_buffer.read()).decode("ascii")
            api_key = os.environ.get(self.config.api_key_env)
            if not api_key:
                print(f"[PetPalVoice] Missing API key env: {self.config.api_key_env}")
                return

            client = OpenAI(api_key=api_key, base_url=self.config.base_url)
            completion = client.chat.completions.create(
                model=self.config.asr_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {"data": f"data:audio/wav;base64,{audio_b64}"},
                            }
                        ],
                    }
                ],
                stream=False,
                extra_body={
                    "asr_options": {
                        "language": self.config.asr_language,
                        "enable_itn": True,
                    }
                },
            )

            text = completion.choices[0].message.content if completion.choices else ""
            if not text:
                print("[PetPalVoice] No speech recognized.")
                return

            print(f"[PetPalVoice] Recognized: {text}")
            if self.config.wakeword.lower() in text.lower():
                self.task_queue.put(text)
            else:
                print(f"[PetPalVoice] Wakeword '{self.config.wakeword}' not found, ignored.")
        except Exception as exc:
            print(f"[PetPalVoice] Transcription failed: {exc}")

    def stop(self) -> None:
        self.listening = False
        self.recording = False
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.audio.terminate()
