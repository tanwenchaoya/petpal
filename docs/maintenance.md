# PetPal Agent Maintenance Notes

PetPal keeps competition-specific LLM, voice, and tool orchestration code inside this repository instead of editing
installed dependencies under `site-packages`.

## Main Entry

```bash
PYTHONPATH=src python examples/petpal_agent.py --camera 0
```

Voice mode:

```bash
export OPENAI_API_KEY="your-bailian-api-key"
PYTHONPATH=src python examples/petpal_agent.py --voice --camera 0 --model qwen3.5-plus-2026-02-15
```

## Where To Change Things

| Need | File |
|------|------|
| LLM model, base URL, API env names | `src/petpal/config.py` |
| Voice ASR model and wakeword settings | `src/petpal/config.py` and `src/petpal/voice.py` |
| Agent prompt and LLM loop | `src/petpal/agent.py` |
| Robot/camera/controller construction | `src/petpal/runtime.py` |
| Tools exposed to the LLM | `src/petpal/tools.py` |
| YOLO cat detection | `src/petpal/vision.py` |
| CLI flags | `examples/petpal_agent.py` |

## Design Rule

RoboCrew is still used for camera, servo control, and existing movement tools, but PetPal-specific behavior should live
in `src/petpal/`. Avoid editing files like:

```text
/Users/tanwenchao/miniforge/lib/python3.13/site-packages/robocrew/core/LLMAgent.py
/Users/tanwenchao/miniforge/lib/python3.13/site-packages/robocrew/core/sound_receiver.py
```

If PetPal needs new behavior, add it to `src/petpal/` first.
