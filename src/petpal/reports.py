from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("outputs/reports")


def save_pet_status_report(
    *,
    behavior_description: str,
    mood_estimate: str,
    attention_advice: str,
    confidence: str = "medium",
    photo_path: str | None = None,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    data = {
        "timestamp": timestamp,
        "behavior_description": behavior_description,
        "mood_estimate": mood_estimate,
        "attention_advice": attention_advice,
        "confidence": confidence,
        "photo_path": photo_path,
    }

    json_path = report_dir / f"{timestamp}_pet_status.json"
    markdown_path = report_dir / f"{timestamp}_pet_status.md"

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(
        "\n".join(
            [
                "# Pet Status Report",
                "",
                f"- Time: {timestamp}",
                f"- Photo: {photo_path or 'not saved'}",
                f"- Behavior: {behavior_description}",
                f"- Mood: {mood_estimate}",
                f"- Confidence: {confidence}",
                f"- Advice: {attention_advice}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        **data,
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }
