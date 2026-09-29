"""
AECHI Edge Node — Simulation Mode
Runs the full edge pipeline against a local video file or sample frames.
No physical camera required. Useful for demos and evaluation.

Usage:
    python simulate.py --video ../demo/sample_urban.mp4 --endpoint https://xxx.execute-api.ap-south-1.amazonaws.com/prod
    python simulate.py --synthetic --endpoint https://xxx.execute-api.ap-south-1.amazonaws.com/prod
"""

import argparse
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aechi.simulate")


def parse_args():
    parser = argparse.ArgumentParser(description="AECHI Simulation Mode")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video", help="Path to a video file to process")
    group.add_argument("--synthetic", action="store_true",
                       help="Generate synthetic random detection payloads (no CV required)")
    parser.add_argument("--endpoint", required=True, help="Cloud API Gateway endpoint URL")
    parser.add_argument("--device-id", default="sim-node-01")
    parser.add_argument("--fps-cap", type=int, default=5,
                        help="Frames per second to process (default: 5)")
    parser.add_argument("--duration", type=int, default=60,
                        help="Simulation duration in seconds (synthetic mode, default: 60)")
    return parser.parse_args()


def run_video_simulation(args):
    """Full pipeline simulation on a video file."""
    # Append parent to sys.path so we can import edge_node modules
    sys.path.insert(0, os.path.dirname(__file__))
    from main import main as edge_main

    # Patch sys.argv to pass to main()
    sys.argv = [
        "main.py",
        "--source", args.video,
        "--endpoint", args.endpoint,
        "--device-id", args.device_id,
        "--fps-cap", str(args.fps_cap),
    ]
    logger.info(f"Starting video simulation: {args.video}")
    edge_main()


def run_synthetic_simulation(args):
    """
    Sends synthetic random detection payloads directly to the cloud endpoint.
    No CV models loaded — purely for testing cloud backend and dashboard.
    """
    import time
    import random
    import json
    import requests

    CLASSES = ["person", "car", "fire", "smoke", "crowd", "accident", "truck"]
    SEVERITIES = {"fire": "HIGH", "smoke": "HIGH", "accident": "HIGH",
                  "crowd": "MEDIUM", "person": "LOW", "car": "LOW", "truck": "LOW"}
    TIERS = ["nano", "small", "medium"]

    endpoint = args.endpoint.rstrip("/") + "/events"
    headers = {
        "Content-Type": "application/json",
        "X-Device-ID": args.device_id,
    }

    logger.info(f"Starting SYNTHETIC simulation | duration={args.duration}s | endpoint={endpoint}")
    t_end = time.time() + args.duration
    event_count = 0

    while time.time() < t_end:
        label = random.choice(CLASSES)
        tier = random.choice(TIERS)
        conf = round(random.uniform(0.55, 0.99), 4)
        event = {
            "device_id": args.device_id,
            "timestamp": int(time.time() * 1000),
            "class_label": label,
            "confidence": conf,
            "bbox": [
                random.randint(0, 400),
                random.randint(0, 300),
                random.randint(401, 640),
                random.randint(301, 480),
            ],
            "model_tier": tier,
            "inference_ms": round(random.uniform(2.0, 30.0), 2),
            "severity": SEVERITIES.get(label, "LOW"),
            "anon_crop_b64": "",  # no image in synthetic mode
        }

        payload = json.dumps({"device_id": args.device_id, "events": [event]})
        try:
            resp = requests.post(endpoint, data=payload, headers=headers, timeout=10)
            event_count += 1
            logger.info(
                f"[{event_count}] Sent: {label} | conf={conf} | severity={event['severity']} "
                f"| tier={tier} | status={resp.status_code}"
            )
        except requests.RequestException as e:
            logger.warning(f"Send failed: {e}")

        time.sleep(1.0 / args.fps_cap)

    logger.info(f"Simulation complete. Sent {event_count} events.")


if __name__ == "__main__":
    args = parse_args()
    if args.synthetic:
        run_synthetic_simulation(args)
    else:
        run_video_simulation(args)
