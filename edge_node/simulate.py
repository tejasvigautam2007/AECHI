"""
AECHI Edge Node — Simulation Mode
Runs the edge pipeline against local video files or generates synthetic telemetry.
Supports multi-node urban fleet simulation without physical cameras or GPUs.

Usage:
    python simulate.py --synthetic --endpoint https://xxx.execute-api.ap-south-1.amazonaws.com/prod
    python simulate.py --video ../demo/sample_urban.mp4 --endpoint https://xxx.execute-api.ap-south-1.amazonaws.com/prod
    python simulate.py --fleet --nodes 3 --endpoint https://xxx.execute-api.ap-south-1.amazonaws.com/prod
"""

import argparse
import logging
import sys
import os
import time
import random
import json
import base64
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aechi.simulate")

URBAN_CAMERAS = [
    {"device_id": "cam-connaught-01", "name": "Connaught Place Inner Circle", "lat": 28.6315, "lon": 77.2167},
    {"device_id": "cam-indiagate-02", "name": "India Gate North Junction", "lat": 28.6129, "lon": 77.2295},
    {"device_id": "cam-chandni-03", "name": "Chandni Chowk Main Rd", "lat": 28.6506, "lon": 77.2303},
    {"device_id": "cam-nehru-04", "name": "Nehru Place Outer Ring", "lat": 28.5494, "lon": 77.2520},
    {"device_id": "cam-aerocity-05", "name": "Aerocity Spine Road", "lat": 28.5528, "lon": 77.1219},
]

HAZARD_PROFILES = [
    {"class": "fire", "severity": "HIGH", "weight": 0.05, "conf_range": (0.80, 0.98)},
    {"class": "smoke", "severity": "HIGH", "weight": 0.08, "conf_range": (0.75, 0.94)},
    {"class": "accident", "severity": "HIGH", "weight": 0.12, "conf_range": (0.70, 0.96)},
    {"class": "crowd", "severity": "MEDIUM", "weight": 0.20, "conf_range": (0.65, 0.92)},
    {"class": "debris", "severity": "MEDIUM", "weight": 0.15, "conf_range": (0.60, 0.88)},
    {"class": "car", "severity": "LOW", "weight": 0.25, "conf_range": (0.75, 0.99)},
    {"class": "person", "severity": "LOW", "weight": 0.15, "conf_range": (0.70, 0.98)},
]


def parse_args():
    parser = argparse.ArgumentParser(description="AECHI Simulation Mode")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video", help="Path to a video file to process")
    group.add_argument("--synthetic", action="store_true", help="Generate single-device synthetic payloads")
    group.add_argument("--fleet", action="store_true", help="Simulate a fleet of distributed urban camera nodes")

    parser.add_argument("--endpoint", required=True, help="Cloud API Gateway endpoint URL")
    parser.add_argument("--device-id", default="sim-node-01")
    parser.add_argument("--nodes", type=int, default=3, help="Number of simulated cameras in fleet mode")
    parser.add_argument("--fps-cap", type=float, default=2.0, help="Events per second per camera (default: 2)")
    parser.add_argument("--duration", type=int, default=60, help="Simulation duration in seconds (default: 60)")
    parser.add_argument("--include-crops", action="store_true", help="Generate synthetic 128x128 crop images")
    return parser.parse_args()


def run_video_simulation(args):
    """Full pipeline simulation on a video file."""
    sys.path.insert(0, os.path.dirname(__file__))
    from main import main as edge_main

    sys.argv = [
        "main.py",
        "--source", args.video,
        "--endpoint", args.endpoint,
        "--device-id", args.device_id,
        "--fps-cap", str(int(args.fps_cap)),
        "--headless"
    ]
    logger.info(f"Starting video simulation from source: {args.video}")
    edge_main()


def _generate_synthetic_crop_b64(severity: str, class_label: str) -> str:
    """Generate a lightweight synthetic JPEG image crop encoded in base64."""
    try:
        from PIL import Image, ImageDraw
        import io

        color_map = {
            "HIGH": (220, 50, 50),
            "MEDIUM": (230, 160, 40),
            "LOW": (40, 140, 60),
        }
        bg = color_map.get(severity, (80, 80, 80))
        img = Image.new("RGB", (128, 128), color=bg)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(8, 8), (120, 120)], outline=(255, 255, 255), width=2)
        draw.text((15, 55), class_label.upper()[:8], fill=(255, 255, 255))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        # Minimal 1x1 valid JPEG fallback
        return "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="


def run_fleet_simulation(args):
    """Simulate multiple distributed camera nodes sending concurrent telemetry."""
    active_cams = URBAN_CAMERAS[:min(args.nodes, len(URBAN_CAMERAS))]
    endpoint = args.endpoint.rstrip("/") + ("/events" if not args.endpoint.endswith("/events") else "")

    logger.info(f"Starting FLEET simulation with {len(active_cams)} nodes | duration={args.duration}s")
    for cam in active_cams:
        logger.info(f" -> Node: {cam['device_id']} ({cam['name']}) at ({cam['lat']}, {cam['lon']})")

    t_end = time.time() + args.duration
    sent_count = 0

    classes = [p["class"] for p in HAZARD_PROFILES]
    weights = [p["weight"] for p in HAZARD_PROFILES]

    while time.time() < t_end:
        cam = random.choice(active_cams)
        profile = random.choices(HAZARD_PROFILES, weights=weights, k=1)[0]
        conf = round(random.uniform(*profile["conf_range"]), 4)

        # Cascading tier simulation
        if conf >= 0.75:
            tier = "nano"
            inference_ms = round(random.uniform(2.0, 5.5), 2)
        elif conf >= 0.60:
            tier = "small"
            inference_ms = round(random.uniform(6.0, 12.0), 2)
        else:
            tier = "medium"
            inference_ms = round(random.uniform(15.0, 32.0), 2)

        crop_b64 = _generate_synthetic_crop_b64(profile["severity"], profile["class"]) if args.include_crops else ""

        # Small location jitter to simulate real camera field-of-view bounding box offset
        event = {
            "device_id": cam["device_id"],
            "timestamp": int(time.time() * 1000),
            "class_label": profile["class"],
            "confidence": conf,
            "bbox": [
                random.randint(10, 300),
                random.randint(10, 200),
                random.randint(310, 620),
                random.randint(210, 460),
            ],
            "model_tier": tier,
            "inference_ms": inference_ms,
            "severity": profile["severity"],
            "lat": round(cam["lat"] + random.uniform(-0.0003, 0.0003), 6),
            "lon": round(cam["lon"] + random.uniform(-0.0003, 0.0003), 6),
            "anon_crop_b64": crop_b64,
        }

        payload = json.dumps({"device_id": cam["device_id"], "events": [event]})
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": cam["device_id"],
        }

        try:
            resp = requests.post(endpoint, data=payload, headers=headers, timeout=5)
            sent_count += 1
            if sent_count % 5 == 0 or profile["severity"] == "HIGH":
                logger.info(
                    f"[{sent_count}] {cam['device_id']} -> {profile['class']} ({profile['severity']}) "
                    f"conf={conf} tier={tier} [{resp.status_code}]"
                )
        except requests.RequestException as e:
            logger.warning(f"Transmission failed for {cam['device_id']}: {e}")

        time.sleep(1.0 / (args.fps_cap * len(active_cams)))

    logger.info(f"Fleet simulation concluded. Total events transmitted: {sent_count}")


if __name__ == "__main__":
    args = parse_args()
    if args.video:
        run_video_simulation(args)
    elif args.fleet:
        run_fleet_simulation(args)
    else:
        # Single synthetic device
        args.nodes = 1
        run_fleet_simulation(args)
