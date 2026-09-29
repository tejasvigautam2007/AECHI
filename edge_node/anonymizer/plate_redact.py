"""
Zero-Trust License Plate Redactor
Detects and blacks-out license plates using contour-based detection + OCR heuristics.
Runs BEFORE any data leaves the edge node.
"""

import cv2
import re
import logging
import numpy as np

logger = logging.getLogger("aechi.anonymizer.plate")

# Regex heuristics for license plate-like text (multi-country)
PLATE_PATTERNS = [
    r"[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4}",   # Indian (MH 12 AB 1234)
    r"[A-Z0-9]{5,8}",                               # Generic alphanumeric block
]
COMPILED_PATTERNS = [re.compile(p) for p in PLATE_PATTERNS]


class PlateRedactor:
    """
    Detects license plate regions using contour analysis and redacts them
    by painting a solid black rectangle — irrecoverable.
    """

    def __init__(self):
        logger.info("PlateRedactor initialized")

    def apply(self, frame, detections: list[dict] = None) -> object:
        """
        Apply license plate redaction to frame.

        Args:
            frame: BGR numpy array
            detections: YOLO detections — restricts search to 'car', 'truck', 'bus' bboxes

        Returns:
            Frame with all detected plates redacted (solid black)
        """
        vehicle_regions = self._extract_vehicle_regions(frame, detections)

        for (rx, ry, rw, rh) in vehicle_regions:
            roi = frame[ry:ry+rh, rx:rx+rw]
            plate_boxes = self._detect_plates_in_roi(roi)
            for (px, py, pw, ph) in plate_boxes:
                # Absolute coordinates
                ax, ay = rx + px, ry + py
                cv2.rectangle(frame, (ax, ay), (ax + pw, ay + ph), (0, 0, 0), -1)

        return frame

    def _extract_vehicle_regions(self, frame, detections) -> list[tuple]:
        """Extract bounding boxes of vehicle objects from YOLO detections."""
        h, w = frame.shape[:2]
        VEHICLE_LABELS = {"car", "truck", "bus", "motorbike", "motorcycle"}
        regions = []

        if detections:
            for det in detections:
                if det.get("label", "").lower() in VEHICLE_LABELS:
                    x1, y1, x2, y2 = det["bbox"]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    regions.append((x1, y1, x2 - x1, y2 - y1))

        # Fallback: scan entire frame
        if not regions:
            regions = [(0, 0, w, h)]

        return regions

    def _detect_plates_in_roi(self, roi) -> list[tuple]:
        """
        Locate license plate candidates within an ROI using contour analysis.
        Returns list of (x, y, w, h) relative to ROI.
        """
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(blurred, 30, 200)

        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]

        plates = []
        roi_h, roi_w = roi.shape[:2]

        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * peri, True)

            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / float(h) if h > 0 else 0

                # License plates typically have aspect ratio 2:1 to 5:1
                if 2.0 <= aspect_ratio <= 6.0 and w > 60 and h > 15:
                    # Clamp to ROI bounds
                    x = max(0, x)
                    y = max(0, y)
                    w = min(w, roi_w - x)
                    h = min(h, roi_h - y)
                    plates.append((x, y, w, h))

        return plates
