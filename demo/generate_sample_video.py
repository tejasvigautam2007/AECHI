"""
AECHI Demo Video Generator
Generates a synthetic urban traffic video with moving cars, pedestrians,
and an anomaly hazard event (e.g. fire/smoke/collision simulation)
for local testing of the AECHI edge node without needing real camera feeds.
"""

import os
import cv2
import numpy as np

def generate_synthetic_video(output_path: str = "demo/sample_urban.mp4", duration_sec: int = 10, fps: int = 20):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_sec * fps

    # Vehicle parameters
    car_x, car_y = 50, 320
    car_speed = 3

    # Pedestrian parameters
    ped_x, ped_y = 480, 200
    ped_speed = 1

    for frame_idx in range(total_frames):
        # Background: asphalt road & pavement
        frame = np.full((height, width, 3), (60, 60, 60), dtype=np.uint8)
        # Pavement
        cv2.rectangle(frame, (0, 0), (width, 220), (140, 140, 140), -1)
        # Road markings (dashed white line)
        for rx in range(0, width, 60):
            cv2.rectangle(frame, (rx, 340), (rx + 30, 345), (255, 255, 255), -1)

        # Move Car
        car_x = (50 + frame_idx * car_speed) % (width + 120) - 60
        # Draw Car body (blue)
        cv2.rectangle(frame, (car_x, car_y), (car_x + 90, car_y + 40), (180, 50, 40), -1)
        # Wheels
        cv2.circle(frame, (car_x + 20, car_y + 40), 8, (20, 20, 20), -1)
        cv2.circle(frame, (car_x + 70, car_y + 40), 8, (20, 20, 20), -1)
        # Mock License Plate (white rectangle with mock numbers)
        plate_w, plate_h = 32, 10
        plate_x, plate_y = car_x + 29, car_y + 24
        cv2.rectangle(frame, (plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h), (240, 240, 240), -1)
        cv2.putText(frame, "DL01", (plate_x + 2, plate_y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 0, 0), 1)

        # Move Pedestrian
        ped_x = 480 - (frame_idx * ped_speed) % 300
        # Pedestrian head (skin tone)
        cv2.circle(frame, (ped_x, ped_y - 20), 10, (160, 190, 225), -1)
        # Pedestrian body (shirt)
        cv2.rectangle(frame, (ped_x - 8, ped_y - 10), (ped_x + 8, ped_y + 25), (40, 150, 60), -1)

        # Hazard simulation (at frame > 80, simulate smoke / accident alert area)
        if frame_idx > 70:
            haz_x, haz_y = 280, 280
            overlay = frame.copy()
            # Pulsing smoke/hazard radius
            radius = int(25 + 10 * np.sin(frame_idx * 0.3))
            cv2.circle(overlay, (haz_x, haz_y), radius, (50, 140, 220), -1)
            cv2.putText(overlay, "HAZARD", (haz_x - 28, haz_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        out.write(frame)

    out.release()
    print(f"Generated synthetic demo video: {output_path} ({total_frames} frames)")

if __name__ == "__main__":
    generate_synthetic_video()
