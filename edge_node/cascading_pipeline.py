"""
AECHI Cascading Inference Pipeline
Implements the 3-tier YOLOv8 cascade: nano → small → medium

Escalation logic:
  - Always start with YOLOv8-nano (fastest, lowest power)
  - If max confidence < conf_nano threshold → escalate to YOLOv8-small
  - If max confidence < conf_small threshold → escalate to YOLOv8-medium
  - Return the highest-confidence result from the stopping tier
"""

import time
import logging
from typing import Optional
from ultralytics import YOLO

logger = logging.getLogger("aechi.pipeline")

# HAZARD-RELEVANT COCO CLASSES (subset we care about for urban triage)
RELEVANT_CLASSES = {
    0: "person",
    2: "car",
    5: "bus",
    7: "truck",
    56: "chair",    # proxy for debris
    58: "potted plant",  # proxy for obstruction
}

# Custom fine-tuned labels (if using custom model)
CUSTOM_HAZARD_CLASSES = [
    "fire", "smoke", "accident", "flood", "crowd",
    "fight", "fall", "debris", "weapon"
]


class CascadingPipeline:
    """
    3-tier cascading inference pipeline.
    Models are lazy-loaded on first use.
    """

    MODEL_SIZES = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"]
    TIER_NAMES = ["nano", "small", "medium"]

    def __init__(self, conf_nano: float = 0.60, conf_small: float = 0.75):
        self.conf_nano = conf_nano
        self.conf_small = conf_small
        self._models: list[Optional[YOLO]] = [None, None, None]
        logger.info(
            f"CascadingPipeline initialized | "
            f"thresholds: nano={conf_nano}, small={conf_small}"
        )

    def _get_model(self, tier: int) -> YOLO:
        """Lazy-load model at given tier index (0=nano, 1=small, 2=medium)."""
        if self._models[tier] is None:
            model_name = self.MODEL_SIZES[tier]
            logger.info(f"Loading {model_name} (first use)...")
            self._models[tier] = YOLO(model_name)
        return self._models[tier]

    def infer(self, frame) -> tuple[list[dict], str, float]:
        """
        Run cascading inference on a single frame.

        Returns:
            (detections, model_tier_name, total_inference_ms)
            detections: list of {"label", "confidence", "bbox"}
        """
        t_start = time.perf_counter()

        for tier_idx, (threshold, tier_name) in enumerate(
            zip(
                [self.conf_nano, self.conf_small, float("inf")],
                self.TIER_NAMES
            )
        ):
            model = self._get_model(tier_idx)
            results = model(frame, verbose=False, conf=0.25)[0]
            detections = self._parse_results(results)

            max_conf = max((d["confidence"] for d in detections), default=0.0)
            elapsed_ms = (time.perf_counter() - t_start) * 1000

            logger.debug(
                f"Tier={tier_name} | detections={len(detections)} | "
                f"max_conf={max_conf:.3f} | elapsed={elapsed_ms:.1f}ms"
            )

            # Stop cascade if confidence is sufficient OR we've hit the final tier
            if max_conf >= threshold or tier_idx == 2:
                return detections, tier_name, round(elapsed_ms, 2)

        # Should never reach here
        return [], "nano", 0.0

    def _parse_results(self, results) -> list[dict]:
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
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2],
                "class_id": class_id,
            })

        return detections
