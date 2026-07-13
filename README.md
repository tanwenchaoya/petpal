# PetPal

PetPal is an embodied pet-care robot project based on an LLM decision layer, camera perception, and XLeRobot/RoboCrew
motion tools.

This repository contains the PetPal-specific application code. Keep upstream LeRobot and RoboCrew as dependencies
instead of putting competition logic inside their source trees.

## Quick Start

```bash
git clone https://github.com/tanwenchaoya/petpal.git
cd petpal
python -m pip install -e .
```

Set your model API key:

```bash
export OPENAI_API_KEY="your-bailian-api-key"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

Run the agent:

```bash
python examples/petpal_agent.py --camera 0
```

Voice mode:

```bash
python examples/petpal_agent.py --voice --camera 0 --model qwen3.5-plus-2026-02-15
```

Simulation mode only checks the LLM connection and does not connect robot hardware:

```bash
python examples/petpal_agent.py --simulate
```

## Project Layout

```text
src/petpal/
  agent.py       # PetPal LLM loop, prompt, image context, tool-call execution
  config.py      # LLM, voice, robot, and runtime configuration
  runtime.py     # Camera, servo controller, tools, and agent construction
  tools.py       # Tools exposed to the LLM
  reports.py     # Pet status report persistence
  vision.py      # Camera capture and YOLO-based cat detection
  voice.py       # Local ASR listener for voice commands
examples/
  petpal_agent.py
docs/
  maintenance.md
  camera_mapping.md
  project_overview.md
```

## Development Rule

PetPal-specific behavior should live under `src/petpal/`. Avoid editing installed files under `site-packages`.

Implemented core tools:

- `capture_pet_photo`
- `find_cat`
- `save_pet_status`

The next core tools to add are:

- `play_with_cat`
- `generate_daily_report`
