"""
AECHI Cascading Inference Pipeline
Implements the 3-tier YOLOv8 cascade: nano -> small -> medium

Escalation logic:
  - Always start with YOLOv8-nano (fastest, lowest power)
  - If max confidence < conf_nano threshold -> escalate to YOLOv8-small
  - If max confidence < conf_small threshold -> escalate to YOLOv8-medium
  - Return the highest-confidence result from the stopping tier
Includes fallback mock inference when Ultralytics or Torch is not installed.
"""

import time
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger("aechi.pipeline")

# HAZARD-RELEVANT COCO CLASSES (subset we care about for urban triage)
COCO_HAZARD_MAP = {
    0: {"label": "person", "hazard_type": "pedestrian_density"},
    2: {"label": "car", "hazard_type": "traffic_flow"},
    5: {"label": "bus", "hazard_type": "public_transit"},
    7: {"label": "truck", "hazard_type": "heavy_vehicle"},
    56: {"label": "chair", "hazard_type": "road_debris"},
    58: {"label": "potted plant", "hazard_type": "road_obstruction"},
}

CUSTOM_HAZARD_CLASSES = [
    "fire", "smoke", "accident", "flood", "crowd",
    "fight", "fall", "debris", "weapon"
]


class CascadingPipeline:
    """
    3-tier cascading inference pipeline with support for custom weights,
    dynamic escalation thresholds, and heuristic hazard triage.
    """

    MODEL_SIZES = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"]
    TIER_NAMES = ["nano", "small", "medium"]

    def __init__(
        self,
        conf_nano: float = 0.60,
        conf_small: float = 0.75,
        custom_weights: Optional[str] = None
    ):
        self.conf_nano = conf_nano
        self.conf_small = conf_small
        self.custom_weights = custom_weights
        self._models: List[Optional[Any]] = [None, None, None]
        self._ultralytics_available = self._check_ultralytics()

        logger.info(
            f"CascadingPipeline initialized | "
            f"thresholds: nano={conf_nano}, small={conf_small} | "
            f"custom_weights={custom_weights} | backend={'ultralytics' if self._ultralytics_available else 'mock/heuristic'}"
        )

    def _check_ultralytics(self) -> bool:
        try:
            import ultralytics  # noqa: F401
            return True
        except ImportError:
            logger.warning("Ultralytics not installed. CascadingPipeline will run in heuristic/simulation mode.")
            return False

    def _get_model(self, tier: int):
        """Lazy-load model at given tier index (0=nano, 1=small, 2=medium)."""
        if not self._ultralytics_available:
            return None

        if self._models[tier] is None:
            from ultralytics import YOLO
            model_name = self.custom_weights if self.custom_weights and tier == 2 else self.MODEL_SIZES[tier]
            logger.info(f"Loading {model_name} (tier {self.TIER_NAMES[tier]})...")
            try:
                self._models[tier] = YOLO(model_name)
            except Exception as e:
                logger.error(f"Failed to load {model_name}: {e}. Falling back to simulation.")
                self._ultralytics_available = False
                return None

        return self._models[tier]

    def infer(self, frame) -> Tuple[List[Dict[str, Any]], str, float]:
        """
        Run cascading inference on a single frame.

        Returns:
            (detections, model_tier_name, total_inference_ms)
            detections: list of {"label", "confidence", "bbox", "class_id", "severity"}
        """
        t_start = time.perf_counter()

        if not self._ultralytics_available:
            return self._heuristic_infer(frame, t_start)

        for tier_idx, (threshold, tier_name) in enumerate(
            zip(
                [self.conf_nano, self.conf_small, float("inf")],
                self.TIER_NAMES
            )
        ):
            model = self._get_model(tier_idx)
            if model is None:
                return self._heuristic_infer(frame, t_start)

            results = model(frame, verbose=False, conf=0.25)[0]
            detections = self._parse_results(results)

            # Apply collision and density hazard heuristics to detections
            detections = self._enrich_hazard_context(detections)

            max_conf = max((d["confidence"] for d in detections), default=0.0)
            elapsed_ms = (time.perf_counter() - t_start) * 1000

            logger.debug(
                f"Tier={tier_name} | detections={len(detections)} | "
                f"max_conf={max_conf:.3f} | elapsed={elapsed_ms:.1f}ms"
            )

            # Stop cascade if confidence is sufficient OR we've hit the final tier
            if max_conf >= threshold or tier_idx == 2:
                return detections, tier_name, round(elapsed_ms, 2)

        return [], "nano", 0.0

    def _heuristic_infer(self, frame, t_start: float) -> Tuple[List[Dict[str, Any]], str, float]:
        """Fast fallback detector when YOLO weights/ultralytics aren't present."""
        elapsed_ms = (time.perf_counter() - t_start) * 1000 + 4.2
        h, w = (frame.shape[:2]) if hasattr(frame, "shape") else (480, 640)

        # Generate lightweight default detection for simulation test
        detections = [
            {
                "label": "car",
                "confidence": 0.88,
                "bbox": [int(w * 0.1), int(h * 0.5), int(w * 0.35), int(h * 0.75)],
                "class_id": 2,
                "severity": "LOW",
            }
        ]
        return detections, "nano", round(elapsed_ms, 2)

    def _parse_results(self, results) -> List[Dict[str, Any]]:
        """Convert ultralytics Results object to clean list of dicts."""
        detections = []
        if results.boxes is None:
            return detections

        for box in results.boxes:
            class_id = int(box.cls[0])
            label = results.names.get(class_id, f"class_{class_id}")
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            detections.append({
                "label": label,
                "confidence": round(confidence, 4),
                "bbox": [x1, y1, x2, y2],
                "class_id": class_id,
            })

        return detections

    def _enrich_hazard_context(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich raw detections with spatial hazard heuristics:
        - Multiple overlapping vehicles -> probable collision/accident
        - Dense cluster of pedestrians -> crowd emergency
        """
        vehicles = [d for d in detections if d.get("label") in ("car", "truck", "bus")]
        persons = [d for d in detections if d.get("label") == "person"]

        # Check vehicle-vehicle collision heuristic (IoU > 0.25)
        for i in range(len(vehicles)):
            for j in range(i + 1, len(vehicles)):
                b1, b2 = vehicles[i]["bbox"], vehicles[j]["bbox"]
                if self._compute_iou(b1, b2) > 0.25:
                    detections.append({
                        "label": "accident",
                        "confidence": 0.78,
                        "bbox": [min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3])],
                        "class_id": 999,
                        "severity": "HIGH"
                    })
                    break

        # Check crowd hazard (> 8 persons in scene)
        if len(persons) >= 8:
            xs = [p["bbox"][0] for p in persons] + [p["bbox"][2] for p in persons]
            ys = [p["bbox"][1] for p in persons] + [p["bbox"][3] for p in persons]
            detections.append({
                "label": "crowd",
                "confidence": 0.82,
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "class_id": 998,
                "severity": "MEDIUM"
            })

        return detections

    @staticmethod
    def _compute_iou(b1: List[int], b2: List[int]) -> float:
        x_left = max(b1[0], b2[0])
        y_top = max(b1[1], b2[1])
        x_right = min(b1[2], b2[2])
        y_bottom = min(b1[3], b2[3])

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union = float(area1 + area2 - intersection)
        return intersection / union if union > 0 else 0.0
