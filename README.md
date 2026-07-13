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
python examples/petpal_agent.py --camera 2
```

Voice mode:

```bash
python examples/petpal_agent.py --voice --camera 2 --model qwen3.5-plus-2026-02-15
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
  navigation.py  # Visual-servo approach policy
  runtime.py     # Camera, servo controller, tools, and agent construction
  tools.py       # Tools exposed to the LLM
  trajectories.py # Recorded pose playback for scripted interaction
  reports.py     # Pet status report persistence
  vision.py      # Camera capture and YOLO-based cat detection
  voice.py       # Local ASR listener for voice commands
examples/
  petpal_agent.py
  petpal_approach.py
  petpal_demo.py
  petpal_trajectory.py
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
- `approach_cat_tool`
- `record_petpal_pose`
- `play_with_cat`
- `save_pet_status`
- `generate_pet_daily_report`

`find_cat` prioritizes YOLO `cat` detections. When YOLO mislabels the visible cat as `dog`, PetPal returns it as
`cat_candidate` and preserves the original `model_label`.

## Recorded Pose Workflow

Release the arm torque before manually posing the arm:

```bash
PYTHONPATH=src python examples/petpal_trajectory.py release --arm-side right
```

Move the arm by hand, then record each pose:

```bash
PYTHONPATH=src python examples/petpal_trajectory.py record --position-name petpal_tease_left --arm-side right
PYTHONPATH=src python examples/petpal_trajectory.py record --position-name petpal_tease_center --arm-side right
PYTHONPATH=src python examples/petpal_trajectory.py record --position-name petpal_tease_right --arm-side right
```

Check the playback plan without moving:

```bash
PYTHONPATH=src python examples/petpal_trajectory.py play --arm-side right
```

Run the recorded playback:

```bash
PYTHONPATH=src python examples/petpal_trajectory.py play --arm-side right --run
```

The default playback baseline uses smooth interpolation:

```bash
PYTHONPATH=src python examples/petpal_trajectory.py play --arm-side right --run --interpolation-steps 28 --step-seconds 0.03 --dwell-seconds 0.1
```

Current baseline:

```text
interpolation_steps=28
step_seconds=0.03
dwell_seconds=0.1
```

## Approach Test

Dry-run visual approach with the head camera:

```bash
PYTHONPATH=src python examples/petpal_approach.py --camera 2
```

Actually run one short movement step when the area is clear:

```bash
PYTHONPATH=src python examples/petpal_approach.py --camera 2 --run
```

## Deterministic Demo

Run the MVP flow with one small approach step and recorded cat play:

```bash
PYTHONPATH=src python examples/petpal_demo.py --run-approach --run-play
```

Run a short closed-loop approach before cat play:

```bash
PYTHONPATH=src python examples/petpal_demo.py --run-approach --run-play --approach-steps 3 --forward-meters 0.02
```
