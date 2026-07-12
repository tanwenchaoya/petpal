from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


DEFAULT_CAPTURE_DIR = Path("outputs/captures")


@dataclass
class Detection:
    label: str
    confidence: float
    xyxy: list[float]
    center_xy: list[float]
    area_ratio: float


_YOLO_MODEL: Any | None = None


def _load_yolo_model(model_path: str) -> Any:
    global _YOLO_MODEL
    if _YOLO_MODEL is None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Ultralytics is not installed. Install vision dependencies with: "
                'python -m pip install -e ".[vision]"'
            ) from exc
        _YOLO_MODEL = YOLO(model_path)
    return _YOLO_MODEL


def _decode_jpeg(image_bytes: bytes) -> np.ndarray:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError("Failed to decode camera JPEG bytes.")
    return frame


def _capture_image_with_retry(camera: Any, *, camera_fov: int = 90, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return camera.capture_image(camera_fov=camera_fov)
        except Exception as exc:
            last_error = exc
            if hasattr(camera, "reopen"):
                camera.reopen()
            time.sleep(0.3 * (attempt + 1))

    usb_port = getattr(camera, "usb_port", None)
    if usb_port is None:
        raise RuntimeError(f"Failed to capture camera image after {attempts} attempts: {last_error}")

    capture = cv2.VideoCapture(usb_port)
    try:
        for _ in range(5):
            ok, frame = capture.read()
            if ok and frame is not None:
                ok, buffer = cv2.imencode(".jpg", frame)
                if ok:
                    return buffer.tobytes()
            time.sleep(0.1)
    finally:
        capture.release()

    raise RuntimeError(f"Failed to capture camera image with RoboCrew and OpenCV fallback: {last_error}")


def detect_cat(
    camera: Any,
    *,
    model_path: str = "yolo11n.pt",
    confidence_threshold: float = 0.25,
    capture_dir: Path = DEFAULT_CAPTURE_DIR,
    save_images: bool = True,
) -> dict[str, Any]:
    model = _load_yolo_model(model_path)
    image_bytes = _capture_image_with_retry(camera, camera_fov=90)
    frame = _decode_jpeg(image_bytes)

    results = model.predict(frame, conf=confidence_threshold, verbose=False)
    result = results[0]
    height, width = frame.shape[:2]

    detections: list[Detection] = []
    for box in result.boxes:
        class_id = int(box.cls[0])
        label = result.names[class_id]
        if label != "cat":
            continue

        x1, y1, x2, y2 = [float(value) for value in box.xyxy[0]]
        confidence = float(box.conf[0])
        box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        detections.append(
            Detection(
                label=label,
                confidence=round(confidence, 4),
                xyxy=[round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                center_xy=[round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
                area_ratio=round(box_area / float(width * height), 4),
            )
        )

    detections.sort(key=lambda item: item.confidence, reverse=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    raw_path = None
    annotated_path = None
    if save_images:
        capture_dir.mkdir(parents=True, exist_ok=True)
        raw_path = capture_dir / f"{timestamp}_raw.jpg"
        annotated_path = capture_dir / f"{timestamp}_cat_detection.jpg"
        cv2.imwrite(str(raw_path), frame)
        cv2.imwrite(str(annotated_path), result.plot())

    best = detections[0] if detections else None
    response = {
        "found": bool(detections),
        "count": len(detections),
        "best_detection": asdict(best) if best else None,
        "detections": [asdict(detection) for detection in detections],
        "image_size": {"width": width, "height": height},
        "raw_image_path": str(raw_path) if raw_path else None,
        "annotated_image_path": str(annotated_path) if annotated_path else None,
    }
    return response


def detection_result_to_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
