import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uploader import EdgeUploader


class TestUploader(unittest.TestCase):

    def setUp(self):
        self.uploader = EdgeUploader(
            endpoint="https://example.com/api",
            device_id="test-device-01",
            latitude=28.6139,
            longitude=77.2090
        )

    def tearDown(self):
        self.uploader.flush(timeout=0.5)

    def test_crop_to_b64(self):
        frame = np.full((100, 100, 3), 120, dtype=np.uint8)
        bbox = [10, 10, 50, 50]
        crop_b64 = EdgeUploader._crop_to_b64(frame, bbox)
        self.assertIsInstance(crop_b64, str)
        self.assertGreater(len(crop_b64), 20)

    def test_payload_enqueue_with_coords(self):
        payload = {
            "timestamp": 123456789,
            "class_label": "fire",
            "confidence": 0.95,
            "severity": "HIGH",
        }
        self.uploader.enqueue(payload)
        self.assertEqual(payload.get("lat"), 28.6139)
        self.assertEqual(payload.get("lon"), 77.2090)


if __name__ == "__main__":
    unittest.main()
