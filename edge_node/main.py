"""
AECHI Edge Node — Main Entry Point
Adaptive Edge-Cloud Hierarchical Intelligence for Urban Hazard Triage

Runs the local video/camera loop with:
  - 3-Tier Cascading YOLOv8 inference (nano -> small -> medium)
  - Zero-Trust Anonymization (MediaPipe face blur + plate redaction)
  - mTLS / Authenticated encrypted uplink to AWS Serverless Backend
"""

import time
import logging
import argparse
from typing import Dict, Any

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
    parser.add_argument("--api-key", default=None, help="Optional API Gateway key")

    # Geolocation metadata
    parser.add_argument("--lat", type=float, default=28.6139, help="Device latitude (default: New Delhi)")
    parser.add_argument("--lon", type=float, default=77.2090, help="Device longitude")

    # mTLS certificates
    parser.add_argument("--client-cert", default=None, help="Path to mTLS client certificate (.crt/.pem)")
    parser.add_argument("--client-key", default=None, help="Path to mTLS client private key (.key)")
    parser.add_argument("--ca-bundle", default=None, help="Path to custom CA bundle for server verification")

    # Model & Pipeline thresholds
    parser.add_argument("--confidence-nano", type=float, default=0.60,
                        help="Min confidence for nano model to stop cascade (default: 0.60)")
    parser.add_argument("--confidence-small", type=float, default=0.75,
                        help="Min confidence for small model to stop cascade (default: 0.75)")
    parser.add_argument("--custom-weights", default=None,
                        help="Path to fine-tuned hazard detection weights (.pt/.onnx)")
    parser.add_argument("--fps-cap", type=int, default=10,
                        help="Max frames to process per second (default: 10)")
    parser.add_argument("--headless", action="store_true",
                        help="Run without local GUI preview window")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info(f"Initializing AECHI Edge Node | device={args.device_id} | pos=({args.lat}, {args.lon})")

    # Initialize components
    pipeline = CascadingPipeline(
        conf_nano=args.confidence_nano,
        conf_small=args.confidence_small,
        custom_weights=args.custom_weights
    )
    face_blur = FaceBlur()
    plate_redactor = PlateRedactor()
    uploader = EdgeUploader(
        endpoint=args.endpoint,
        device_id=args.device_id,
        api_key=args.api_key,
        client_cert=args.client_cert,
        client_key=args.client_key,
        ca_bundle=args.ca_bundle,
        latitude=args.lat,
        longitude=args.lon
    )

    # Open video source (OpenCV or fallback)
    try:
        import cv2
    except ImportError:
        logger.error("OpenCV is required to capture video streams. Run 'pip install opencv-python'.")
        return

    source = int(args.source) if str(args.source).isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.error(f"Cannot open video source: {source}")
        return

    logger.info(f"Stream opened successfully: {source}")
    frame_interval = 1.0 / max(1, args.fps_cap)
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
                logger.warning("End of stream or read error. Restarting stream...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                time.sleep(0.1)
                continue

            # 1. Cascading Inference
            detections, model_tier, inference_ms = pipeline.infer(frame)

            if not detections:
                continue

            # 2. Zero-Trust Anonymization (Before network)
            anon_frame = face_blur.apply(frame.copy(), detections)
            anon_frame = plate_redactor.apply(anon_frame, detections)

            # 3. Payload Construction & Secure Enqueue
            for det in detections:
                severity = det.get("severity") or _compute_severity(det)
                payload = {
                    "device_id": args.device_id,
                    "timestamp": int(now * 1000),
                    "class_label": det["label"],
                    "confidence": round(det["confidence"], 4),
                    "bbox": det["bbox"],
                    "model_tier": model_tier,
                    "inference_ms": inference_ms,
                    "severity": severity,
                    "lat": args.lat,
                    "lon": args.lon,
                }
                uploader.enqueue(payload, anon_frame, det["bbox"])

            # 4. Optional local preview
            if not args.headless and str(args.source) != "0":
                cv2.imshow("AECHI Edge — Anonymized Stream", anon_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        logger.info("Interrupt signal received. Shutting down edge node...")
    finally:
        uploader.flush()
        cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


def _compute_severity(det: Dict[str, Any]) -> str:
    """Map detected class labels to hazard severity levels."""
    HIGH = {"fire", "smoke", "accident", "weapon", "flood", "explosion"}
    MEDIUM = {"crowd", "fight", "fall", "debris", "road_obstruction"}
    label = det.get("label", "").lower()

    if label in HIGH:
        return "HIGH"
    elif label in MEDIUM:
        return "MEDIUM"
    return "LOW"


if __name__ == "__main__":
    main()
