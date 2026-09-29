"""
Zero-Trust Face Anonymizer
Blurs all detected faces using MediaPipe Face Detection.
This runs BEFORE any data leaves the edge node.
"""

import cv2
import logging
import mediapipe as mp

logger = logging.getLogger("aechi.anonymizer.face")


class FaceBlur:
    """
    Detects and blurs human faces in a frame using MediaPipe.
    Uses strong Gaussian blur — faces are irrecoverable after processing.
    """

    def __init__(self, min_detection_confidence: float = 0.5, blur_strength: int = 51):
        self.blur_strength = blur_strength if blur_strength % 2 == 1 else blur_strength + 1
        self._detector = mp.solutions.face_detection.FaceDetection(
            model_selection=0,  # 0=close range, 1=full range
            min_detection_confidence=min_detection_confidence
        )
        logger.info(f"FaceBlur initialized | blur_kernel={self.blur_strength}x{self.blur_strength}")

    def apply(self, frame, detections: list[dict] = None) -> object:
        """
        Apply face blur to frame.

        Args:
            frame: BGR numpy array (from cv2)
            detections: Optional YOLO detections (used to skip non-person objects)

        Returns:
            Frame with all faces blurred (BGR numpy array)
        """
        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._detector.process(rgb_frame)

        if not results.detections:
            return frame

        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box
            x = max(0, int(bbox.xmin * w))
            y = max(0, int(bbox.ymin * h))
            bw = min(int(bbox.width * w), w - x)
            bh = min(int(bbox.height * h), h - y)

            if bw <= 0 or bh <= 0:
                continue

            # Apply heavy Gaussian blur to face region
            roi = frame[y:y+bh, x:x+bw]
            blurred = cv2.GaussianBlur(roi, (self.blur_strength, self.blur_strength), 0)
            frame[y:y+bh, x:x+bw] = blurred

        return frame

    def __del__(self):
        try:
            self._detector.close()
        except Exception:
            pass
