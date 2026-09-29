"""
Zero-Trust Face Anonymizer
Blurs or pixelates all detected faces.
Runs locally at the edge BEFORE any payload leaves the node.
Supports MediaPipe Face Detection with automatic OpenCV Haar Cascade fallback.
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("aechi.anonymizer.face")


class FaceBlur:
    """
    Detects and blurs human faces in a frame.
    Uses strong Gaussian blur (irrecoverable) or mosaic pixelation.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        blur_strength: int = 51,
        mode: str = "gaussian"  # "gaussian" or "pixelate"
    ):
        self.blur_strength = blur_strength if blur_strength % 2 == 1 else blur_strength + 1
        self.mode = mode
        self._mp_detector = None
        self._haar_detector = None

        self._init_detector(min_detection_confidence)
        logger.info(f"FaceBlur initialized | mode={mode} | blur_kernel={self.blur_strength}x{self.blur_strength}")

    def _init_detector(self, min_conf: float):
        try:
            import mediapipe as mp
            self._mp_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=min_conf
            )
            logger.info("Using MediaPipe FaceDetection backend.")
            return
        except (ImportError, Exception) as e:
            logger.warning(f"MediaPipe face detection unavailable ({e}). Initializing OpenCV fallback.")

        try:
            import cv2
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._haar_detector = cv2.CascadeClassifier(cascade_path)
            logger.info("Using OpenCV Haar Cascade backend.")
        except Exception as e:
            logger.warning(f"OpenCV Haar Cascade could not be loaded: {e}. Anonymizer will run in bbox mode.")

    def apply(self, frame, detections: Optional[List[Dict[str, Any]]] = None) -> Any:
        """
        Apply face blur to frame.
        Args:
            frame: BGR numpy array
            detections: Optional detections to locate person ROIs
        Returns:
            Frame with all faces blurred
        """
        if frame is None:
            return None

        h, w = frame.shape[:2]
        face_boxes = []

        # 1. MediaPipe detection
        if self._mp_detector is not None:
            try:
                import cv2
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self._mp_detector.process(rgb_frame)
                if results.detections:
                    for det in results.detections:
                        bbox = det.location_data.relative_bounding_box
                        x = max(0, int(bbox.xmin * w))
                        y = max(0, int(bbox.ymin * h))
                        bw = min(int(bbox.width * w), w - x)
                        bh = min(int(bbox.height * h), h - y)
                        if bw > 4 and bh > 4:
                            face_boxes.append((x, y, bw, bh))
            except Exception as e:
                logger.error(f"MediaPipe detection error: {e}")

        # 2. Haar Cascade fallback
        elif self._haar_detector is not None:
            try:
                import cv2
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self._haar_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))
                for (x, y, bw, bh) in faces:
                    face_boxes.append((x, y, bw, bh))
            except Exception as e:
                logger.error(f"Haar cascade detection error: {e}")

        # 3. Detection fallback: if person bounding boxes provided, blur top 20% (head region)
        if not face_boxes and detections:
            for det in detections:
                if det.get("label") == "person":
                    x1, y1, x2, y2 = det.get("bbox", [0, 0, 0, 0])
                    pw, ph = x2 - x1, y2 - y1
                    if pw > 0 and ph > 0:
                        # Top 25% of person is estimated head/face region
                        face_boxes.append((x1, y1, pw, int(ph * 0.25)))

        # Apply blur/redaction
        for (x, y, bw, bh) in face_boxes:
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            bw = min(bw, w - x)
            bh = min(bh, h - y)
            if bw <= 2 or bh <= 2:
                continue

            frame = self._blur_region(frame, x, y, bw, bh)

        return frame

    def _blur_region(self, frame, x: int, y: int, w: int, h: int) -> Any:
        try:
            import cv2
            roi = frame[y:y+h, x:x+w]
            if roi.size == 0:
                return frame

            if self.mode == "pixelate":
                # Pixelation effect
                small_w = max(1, w // 10)
                small_h = max(1, h // 10)
                temp = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
                pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
                frame[y:y+h, x:x+w] = pixelated
            else:
                # Strong Gaussian Blur
                ksize = self.blur_strength
                blurred = cv2.GaussianBlur(roi, (ksize, ksize), 0)
                frame[y:y+h, x:x+w] = blurred
        except Exception:
            # Solid black privacy fallback if cv2 blur fails
            frame[y:y+h, x:x+w] = 0

        return frame

    def __del__(self):
        if self._mp_detector is not None:
            try:
                self._mp_detector.close()
            except Exception:
                pass
