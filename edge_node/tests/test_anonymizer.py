import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from anonymizer.face_blur import FaceBlur
from anonymizer.plate_redact import PlateRedactor


class TestAnonymizer(unittest.TestCase):

    def setUp(self):
        self.face_blur = FaceBlur()
        self.plate_redactor = PlateRedactor()

    def test_face_blur_with_detections(self):
        # 200x200 test frame
        frame = np.ones((200, 200, 3), dtype=np.uint8) * 150
        detections = [
            {"label": "person", "bbox": [50, 40, 150, 180], "confidence": 0.9}
        ]
        blurred = self.face_blur.apply(frame, detections)
        self.assertIsNotNone(blurred)
        self.assertEqual(blurred.shape, (200, 200, 3))

    def test_plate_redaction_safeguard(self):
        frame = np.ones((300, 300, 3), dtype=np.uint8) * 200
        # Car detection box
        detections = [
            {"label": "car", "bbox": [50, 50, 250, 250], "confidence": 0.85}
        ]
        redacted = self.plate_redactor.apply(frame, detections)
        self.assertIsNotNone(redacted)

        # Confirm some pixels in the car region were blackened (solid 0)
        black_pixels = np.sum(redacted[150:250, 50:250] == 0)
        self.assertGreater(black_pixels, 0)


if __name__ == "__main__":
    unittest.main()
