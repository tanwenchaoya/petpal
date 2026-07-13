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


def generate_daily_report(
    *,
    report_date: str | None = None,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    date_prefix = report_date or time.strftime("%Y%m%d")
    report_dir.mkdir(parents=True, exist_ok=True)

    status_reports: list[dict[str, Any]] = []
    for path in sorted(report_dir.glob(f"{date_prefix}_*_pet_status.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        item["_source_path"] = str(path)
        status_reports.append(item)

    mood_counts: dict[str, int] = {}
    for item in status_reports:
        mood = str(item.get("mood_estimate") or "unknown")
        mood_counts[mood] = mood_counts.get(mood, 0) + 1

    latest = status_reports[-1] if status_reports else None
    data = {
        "date": date_prefix,
        "status_report_count": len(status_reports),
        "mood_counts": mood_counts,
        "latest_behavior": latest.get("behavior_description") if latest else None,
        "latest_advice": latest.get("attention_advice") if latest else None,
        "source_reports": [item["_source_path"] for item in status_reports],
    }

    json_path = report_dir / f"{date_prefix}_daily_report.json"
    markdown_path = report_dir / f"{date_prefix}_daily_report.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(
        "\n".join(
            [
                "# Pet Daily Report",
                "",
                f"- Date: {date_prefix}",
                f"- Status reports: {len(status_reports)}",
                f"- Mood counts: {mood_counts or {'unknown': 0}}",
                f"- Latest behavior: {data['latest_behavior'] or 'no status report yet'}",
                f"- Latest advice: {data['latest_advice'] or 'no advice yet'}",
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
