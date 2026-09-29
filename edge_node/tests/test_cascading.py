import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cascading_pipeline import CascadingPipeline


class TestCascadingPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = CascadingPipeline(conf_nano=0.60, conf_small=0.75)

    def test_pipeline_initialization(self):
        self.assertEqual(self.pipeline.conf_nano, 0.60)
        self.assertEqual(self.pipeline.conf_small, 0.75)
        self.assertEqual(len(self.pipeline.TIER_NAMES), 3)

    def test_inference_on_synthetic_frame(self):
        # Create a mock 480x640 frame
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections, tier, latency = self.pipeline.infer(mock_frame)

        self.assertIsInstance(detections, list)
        self.assertIn(tier, ["nano", "small", "medium"])
        self.assertGreaterEqual(latency, 0.0)

    def test_iou_computation(self):
        b1 = [0, 0, 100, 100]
        b2 = [50, 50, 150, 150]
        iou = CascadingPipeline._compute_iou(b1, b2)
        self.assertGreater(iou, 0.1)
        self.assertLess(iou, 0.5)

        # Disjoint boxes
        b3 = [200, 200, 300, 300]
        self.assertEqual(CascadingPipeline._compute_iou(b1, b3), 0.0)


if __name__ == "__main__":
    unittest.main()
