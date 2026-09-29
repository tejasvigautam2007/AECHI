"""
AECHI Edge Node — Main Entry Point
Adaptive Edge-Cloud Hierarchical Intelligence for Urban Hazard Triage

Runs the camera loop with cascading YOLOv8 inference and zero-trust anonymization.
"""

import cv2
import time
import logging
import argparse
from cascading_pipeline import CascadingPipeline
from anonymizer.face_blur import FaceBlur
from anonymizer.plate_redact import PlateRedactor
from uploader import EdgeUploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aechi.edge")


def parse_args():
    parser = argparse.ArgumentParser(description="AECHI Edge Node")
    parser.add_argument("--source", default=0, help="Camera index or video path")
    parser.add_argument("--endpoint", required=True, help="Cloud API Gateway endpoint URL")
    parser.add_argument("--device-id", default="edge-node-01", help="Unique edge device ID")
    parser.add_argument("--confidence-nano", type=float, default=0.60,
                        help="Min confidence for nano model to stop cascade (default: 0.60)")
    parser.add_argument("--confidence-small", type=float, default=0.75,
                        help="Min confidence for small model to stop cascade (default: 0.75)")
    parser.add_argument("--fps-cap", type=int, default=10,
                        help="Max frames to process per second (default: 10)")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info(f"Initializing AECHI Edge Node | device={args.device_id}")

    # Initialize components
    pipeline = CascadingPipeline(
        conf_nano=args.confidence_nano,
        conf_small=args.confidence_small
    )
    face_blur = FaceBlur()
    plate_redactor = PlateRedactor()
    uploader = EdgeUploader(endpoint=args.endpoint, device_id=args.device_id)

    # Open video source
    cap = cv2.VideoCapture(int(args.source) if str(args.source).isdigit() else args.source)
    if not cap.isOpened():
        logger.error(f"Cannot open video source: {args.source}")
        raise SystemExit(1)

    logger.info(f"Stream opened: {args.source}")
    frame_interval = 1.0 / args.fps_cap
    last_frame_time = 0.0

    try:
        while True:
            now = time.time()
            if now - last_frame_time < frame_interval:
                time.sleep(0.001)
                continue
            last_frame_time = now

            ret, frame = cap.read()
            if not ret:
                logger.warning("End of stream or read error. Restarting...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop video
                continue

            # --- Cascading Inference ---
            detections, model_tier, inference_ms = pipeline.infer(frame)

            if not detections:
                continue

            # --- Zero-Trust Anonymization ---
            anon_frame = face_blur.apply(frame.copy(), detections)
            anon_frame = plate_redactor.apply(anon_frame, detections)

            # --- Build & Upload Payload ---
            for det in detections:
                payload = {
                    "device_id": args.device_id,
                    "timestamp": int(now * 1000),
                    "class_label": det["label"],
                    "confidence": round(det["confidence"], 4),
                    "bbox": det["bbox"],            # [x1, y1, x2, y2]
                    "model_tier": model_tier,       # "nano" | "small" | "medium"
                    "inference_ms": inference_ms,
                    "severity": _compute_severity(det),
                }
                uploader.enqueue(payload, anon_frame, det["bbox"])

            # Optional: display locally
            if args.source != 0:  # don't block on webcam display
                cv2.imshow("AECHI Edge — Anonymized Feed", anon_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        logger.info("Shutting down edge node...")
    finally:
        uploader.flush()
        cap.release()
        cv2.destroyAllWindows()


def _compute_severity(det: dict) -> str:
    """Map detected class labels to hazard severity levels."""
    HIGH = {"fire", "smoke", "accident", "weapon", "flood"}
    MEDIUM = {"crowd", "fight", "fall", "debris"}
    label = det.get("label", "").lower()
    if label in HIGH:
        return "HIGH"
    elif label in MEDIUM:
        return "MEDIUM"
    return "LOW"


if __name__ == "__main__":
    main()
