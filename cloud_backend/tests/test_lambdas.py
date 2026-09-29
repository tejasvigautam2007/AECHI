"""
Unit tests for AECHI Cloud Backend Lambdas
Uses unittest.mock and explicit file loading to test handlers independently.
"""

import json
import os
import unittest
import importlib.util
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_module_from_file(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCloudBackend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["DYNAMODB_TABLE"] = "aechi-test-events"
        os.environ["CROPS_BUCKET"] = "aechi-test-crops"
        os.environ["ALERT_TOPIC_ARN"] = "arn:aws:sns:ap-south-1:123456789012:test-topic"

    @patch("boto3.resource")
    @patch("boto3.client")
    def test_ingest_lambda(self, mock_client, mock_resource):
        ingest_path = os.path.join(BASE_DIR, "lambdas", "ingest", "handler.py")
        ingest_mod = load_module_from_file("ingest_mod", ingest_path)

        mock_table = MagicMock()
        ingest_mod.table = mock_table
        ingest_mod.eventbridge = MagicMock()
        ingest_mod.s3 = MagicMock()

        test_payload = {
            "device_id": "test-cam-01",
            "events": [
                {
                    "timestamp": 1727618000000,
                    "class_label": "fire",
                    "confidence": 0.94,
                    "severity": "HIGH",
                    "bbox": [10, 20, 100, 200],
                    "lat": 28.6139,
                    "lon": 77.2090
                }
            ]
        }

        resp = ingest_mod.lambda_handler({"body": json.dumps(test_payload)}, None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["accepted"], 1)
        self.assertTrue(len(body["event_ids"]) > 0)
        self.assertTrue(mock_table.put_item.called)

    def test_triage_scoring(self):
        triage_path = os.path.join(BASE_DIR, "lambdas", "triage", "handler.py")
        triage_mod = load_module_from_file("triage_mod", triage_path)

        score = triage_mod._compute_triage_score("fire", "HIGH", 0.95, corroborating_count=2)
        self.assertEqual(score, 10)

        low_score = triage_mod._compute_triage_score("car", "LOW", 0.50, corroborating_count=1)
        self.assertLessEqual(low_score, 4)

    def test_haversine_distance(self):
        triage_path = os.path.join(BASE_DIR, "lambdas", "triage", "handler.py")
        triage_mod = load_module_from_file("triage_mod_dist", triage_path)

        # Distance between Connaught Place (28.6315, 77.2167) and India Gate (28.6129, 77.2295) is ~2.4km
        dist = triage_mod._haversine_distance_meters(28.6315, 77.2167, 28.6129, 77.2295)
        self.assertGreater(dist, 2000)
        self.assertLess(dist, 3000)

    @patch("boto3.resource")
    @patch("boto3.client")
    def test_dashboard_lambda_stats(self, mock_client, mock_resource):
        dash_path = os.path.join(BASE_DIR, "lambdas", "dashboard", "handler.py")
        dash_mod = load_module_from_file("dash_mod", dash_path)

        mock_table = MagicMock()
        mock_table.query.return_value = {"Count": 5}
        dash_mod.table = mock_table

        resp = dash_mod.lambda_handler({"path": "/dashboard/stats", "httpMethod": "GET"}, None)
        self.assertEqual(resp["statusCode"], 200)
        body = json.loads(resp["body"])
        self.assertEqual(body["total"], 15)


if __name__ == "__main__":
    unittest.main()
