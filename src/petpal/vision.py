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
    source: str = "full_frame"
    model_label: str | None = None


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


def _cat_detections_from_result(
    result: Any,
    *,
    image_width: int,
    image_height: int,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    scale: float = 1.0,
    source: str = "full_frame",
    accepted_labels: tuple[str, ...] = ("cat",),
    output_label: str = "cat",
) -> list[Detection]:
    detections: list[Detection] = []
    for box in result.boxes:
        class_id = int(box.cls[0])
        model_label = result.names[class_id]
        if model_label not in accepted_labels:
            continue

        raw_x1, raw_y1, raw_x2, raw_y2 = [float(value) for value in box.xyxy[0]]
        x1 = offset_x + raw_x1 / scale
        y1 = offset_y + raw_y1 / scale
        x2 = offset_x + raw_x2 / scale
        y2 = offset_y + raw_y2 / scale
        confidence = float(box.conf[0])
        box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        detections.append(
            Detection(
                label=output_label,
                confidence=round(confidence, 4),
                xyxy=[round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                center_xy=[round((x1 + x2) / 2, 1), round((y1 + y2) / 2, 1)],
                area_ratio=round(box_area / float(image_width * image_height), 4),
                source=source,
                model_label=model_label,
            )
        )
    return detections


def _tile_regions(width: int, height: int) -> list[tuple[str, int, int, int, int]]:
    half_w = width // 2
    half_h = height // 2
    return [
        ("wide_lower", width // 3, height * 5 // 12, width * 3 // 4, height * 5 // 6),
        ("center_lower", width * 2 // 5, height * 5 // 12, width * 2 // 3, height * 3 // 4),
        ("right_middle", width * 7 // 16, height * 5 // 12, width * 3 // 4, height * 3 // 4),
        ("lower_right", half_w, half_h, width, height),
        ("lower_left", 0, half_h, half_w + width // 8, height),
        ("upper_right", half_w - width // 8, 0, width, half_h + height // 8),
        ("upper_left", 0, 0, half_w + width // 8, half_h + height // 8),
    ]


def _detect_cat_in_tiles(
    model: Any,
    frame: np.ndarray,
    *,
    confidence_threshold: float,
    scale: float = 2.0,
    accepted_labels: tuple[str, ...] = ("cat",),
    output_label: str = "cat",
) -> list[Detection]:
    height, width = frame.shape[:2]
    detections: list[Detection] = []
    for name, x1, y1, x2, y2 in _tile_regions(width, height):
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        crop_big = cv2.resize(crop, (int(crop.shape[1] * scale), int(crop.shape[0] * scale)))
        result = model.predict(crop_big, conf=confidence_threshold, verbose=False)[0]
        detections.extend(
            _cat_detections_from_result(
                result,
                image_width=width,
                image_height=height,
                offset_x=x1,
                offset_y=y1,
                scale=scale,
                source=f"tile:{name}",
                accepted_labels=accepted_labels,
                output_label=output_label,
            )
        )
    return detections


def _draw_cat_detections(frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
    annotated = frame.copy()
    for detection in detections:
        x1, y1, x2, y2 = [int(value) for value in detection.xyxy]
        model_label = detection.model_label or detection.label
        label = f"{detection.label}/{model_label} {detection.confidence:.2f} {detection.source}"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(
            annotated,
            label,
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    return annotated


def capture_camera_frame(
    camera: Any,
    *,
    capture_dir: Path = DEFAULT_CAPTURE_DIR,
    prefix: str = "pet_photo",
    camera_fov: int = 90,
    save_image: bool = True,
) -> dict[str, Any]:
    image_bytes = _capture_image_with_retry(camera, camera_fov=camera_fov)
    frame = _decode_jpeg(image_bytes)
    height, width = frame.shape[:2]

    image_path = None
    if save_image:
        capture_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        image_path = capture_dir / f"{timestamp}_{prefix}.jpg"
        cv2.imwrite(str(image_path), frame)

    return {
        "image_path": str(image_path) if image_path else None,
        "image_size": {"width": width, "height": height},
        "bytes": len(image_bytes),
    }


def detect_cat(
    camera: Any,
    *,
    model_path: str = "yolo11s.pt",
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

    detections = _cat_detections_from_result(result, image_width=width, image_height=height)
    if not detections:
        detections = _detect_cat_in_tiles(
            model,
            frame,
            confidence_threshold=confidence_threshold,
        )
    if not detections:
        detections = _cat_detections_from_result(
            result,
            image_width=width,
            image_height=height,
            accepted_labels=("dog",),
            output_label="cat_candidate",
        )
    if not detections:
        detections = _detect_cat_in_tiles(
            model,
            frame,
            confidence_threshold=confidence_threshold,
            accepted_labels=("dog",),
            output_label="cat_candidate",
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
        cv2.imwrite(str(annotated_path), _draw_cat_detections(frame, detections))

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
