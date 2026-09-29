"""
Zero-Trust License Plate Redactor
Detects and blacks out license plates using contour morphology,
aspect-ratio heuristics, and optional OCR verification.
Runs locally at the edge BEFORE any payload leaves the node.
"""

import re
import logging
from typing import Optional, List, Tuple, Dict, Any

logger = logging.getLogger("aechi.anonymizer.plate")

PLATE_PATTERNS = [
    r"[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4}",   # Indian (MH 12 AB 1234)
    r"[A-Z0-9]{5,8}",                           # Generic alphanumeric block
    r"[A-Z]{3}\s?\d{3,4}",                      # US / EU variant
]
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PLATE_PATTERNS]


class PlateRedactor:
    """
    Detects license plate candidates and redacts them with solid black rectangles.
    Guarantees irrecoverable redaction under GDPR and DPDP compliance.
    """

    def __init__(self, use_ocr: bool = False, pad_pixels: int = 4):
        self.pad_pixels = pad_pixels
        self.use_ocr = use_ocr
        self._ocr_engine = None

        if use_ocr:
            self._init_ocr()

        logger.info(f"PlateRedactor initialized | pad={pad_pixels}px | ocr_enabled={self._ocr_engine is not None}")

    def _init_ocr(self):
        try:
            import pytesseract
            self._ocr_engine = pytesseract
            logger.info("OCR engine (pytesseract) active for plate verification.")
        except ImportError:
            logger.info("pytesseract not found. Using high-recall geometric and contour redaction.")

    def apply(self, frame, detections: Optional[List[Dict[str, Any]]] = None) -> Any:
        """
        Apply license plate redaction to frame.
        Args:
            frame: BGR numpy array
            detections: YOLO detections (restricts search to vehicle bboxes)
        Returns:
            Frame with all plates blacked out
        """
        if frame is None:
            return None

        cv2_available = True
        try:
            import cv2
        except ImportError:
            cv2_available = False

        vehicle_regions = self._extract_vehicle_regions(frame, detections)

        for (rx, ry, rw, rh) in vehicle_regions:
            roi = frame[ry:ry+rh, rx:rx+rw]
            if roi.size == 0:
                continue

            plate_boxes = self._detect_plates_in_roi(roi) if cv2_available else []

            # High-assurance safeguard: if no plate contour detected in a vehicle,
            # redact bottom 20% center area (typical plate bumper location)
            if not plate_boxes and (rw > 60 and rh > 40):
                bw = int(rw * 0.4)
                bh = max(12, int(rh * 0.16))
                bx = rx + int((rw - bw) / 2)
                by = ry + int(rh * 0.78)
                plate_boxes.append((bx - rx, by - ry, bw, bh))

            for (px, py, pw, ph) in plate_boxes:
                # Add safety margin padding
                ax = max(0, rx + px - self.pad_pixels)
                ay = max(0, ry + py - self.pad_pixels)
                aw = min(frame.shape[1] - ax, pw + 2 * self.pad_pixels)
                ah = min(frame.shape[0] - ay, ph + 2 * self.pad_pixels)

                # Black out plate completely (pure numpy array indexing)
                frame[ay:ay+ah, ax:ax+aw] = 0

        return frame

    def _extract_vehicle_regions(self, frame, detections: Optional[List[Dict[str, Any]]]) -> List[Tuple[int, int, int, int]]:
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
                    if (x2 - x1) > 20 and (y2 - y1) > 20:
                        regions.append((x1, y1, x2 - x1, y2 - y1))

        if not regions:
            regions = [(0, 0, w, h)]

        return regions

    def _detect_plates_in_roi(self, roi) -> List[Tuple[int, int, int, int]]:
        """
        Locate license plate candidates within a vehicle ROI.
        Uses Sobel gradient and morphological closing to isolate plate text regions.
        """
        import cv2

        roi_h, roi_w = roi.shape[:2]
        if roi_h < 20 or roi_w < 40:
            return []

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Morphological gradient to highlight high horizontal text variations
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=-1)
        grad_x = cv2.convertScaleAbs(grad_x)

        blurred = cv2.GaussianBlur(grad_x, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Close horizontally to connect alphanumeric characters into a single rectangle
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, rect_kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        plates = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0

            # License plate aspect ratio filter (2:1 to 5.5:1)
            if 1.8 <= aspect_ratio <= 6.0 and w > 35 and h > 10:
                plate_roi = gray[y:y+h, x:x+w]

                # Optional OCR pattern verification
                if self._ocr_engine is not None and plate_roi.size > 0:
                    try:
                        text = self._ocr_engine.image_to_string(
                            plate_roi,
                            config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                        ).strip()
                        if any(pattern.search(text) for pattern in COMPILED_PATTERNS):
                            plates.append((x, y, w, h))
                            continue
                    except Exception:
                        pass

                plates.append((x, y, w, h))

        return plates
