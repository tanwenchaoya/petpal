from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    script_path = Path(__file__).resolve().parents[2] / "examples" / "petpal_agent.py"
    runpy.run_path(str(script_path), run_name="__main__")
