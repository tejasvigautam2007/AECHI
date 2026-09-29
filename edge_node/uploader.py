"""
Edge Node Uploader
Batches and sends anonymized detection payloads to the AWS API Gateway endpoint.
Uses a background thread with retry logic and exponential backoff.
"""

import base64
import json
import logging
import queue
import threading
import time
from typing import Optional

import cv2
import requests

logger = logging.getLogger("aechi.uploader")

MAX_QUEUE_SIZE = 500
BATCH_SIZE = 10
RETRY_DELAYS = [1, 2, 4, 8, 16]  # Exponential backoff (seconds)


class EdgeUploader:
    """
    Non-blocking upload manager.
    Detections are enqueued and sent in background batches.
    """

    def __init__(self, endpoint: str, device_id: str, api_key: Optional[str] = None):
        self.endpoint = endpoint.rstrip("/") + "/events"
        self.device_id = device_id
        self.headers = {
            "Content-Type": "application/json",
            "X-Device-ID": device_id,
        }
        if api_key:
            self.headers["x-api-key"] = api_key

        self._queue: queue.Queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._upload_worker, daemon=True, name="uploader")
        self._worker.start()
        logger.info(f"EdgeUploader started | endpoint={self.endpoint}")

    def enqueue(self, payload: dict, frame, bbox: list[int]) -> None:
        """
        Enqueue a detection payload with its anonymized crop.

        Args:
            payload: Detection metadata dict
            frame: Anonymized frame (BGR numpy array)
            bbox: [x1, y1, x2, y2] of the detected object
        """
        try:
            crop_b64 = self._crop_to_b64(frame, bbox)
            payload["anon_crop_b64"] = crop_b64
            self._queue.put_nowait(payload)
        except queue.Full:
            logger.warning("Upload queue full — dropping oldest entry")
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(payload)
            except queue.Empty:
                pass

    def flush(self, timeout: float = 5.0) -> None:
        """Wait for queue to drain before shutdown."""
        logger.info("Flushing upload queue...")
        self._stop_event.set()
        self._worker.join(timeout=timeout)

    def _upload_worker(self) -> None:
        """Background thread: batches payloads and sends to cloud."""
        batch = []
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.5)
                batch.append(item)
                if len(batch) >= BATCH_SIZE:
                    self._send_batch(batch)
                    batch = []
            except queue.Empty:
                if batch:
                    self._send_batch(batch)
                    batch = []

        if batch:
            self._send_batch(batch)

    def _send_batch(self, batch: list[dict]) -> None:
        """Send a batch of payloads with retry logic."""
        body = json.dumps({"device_id": self.device_id, "events": batch})

        for attempt, delay in enumerate(RETRY_DELAYS + [None]):
            try:
                resp = requests.post(
                    self.endpoint,
                    data=body,
                    headers=self.headers,
                    timeout=10
                )
                resp.raise_for_status()
                logger.info(f"Uploaded batch of {len(batch)} events | status={resp.status_code}")
                return
            except requests.RequestException as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                if delay is None:
                    logger.error(f"Dropping batch of {len(batch)} events after max retries")
                    return
                time.sleep(delay)

    @staticmethod
    def _crop_to_b64(frame, bbox: list[int]) -> str:
        """Crop, resize, and encode frame region as base64 JPEG."""
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return ""
        crop_resized = cv2.resize(crop, (128, 128))
        _, buf = cv2.imencode(".jpg", crop_resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return base64.b64encode(buf).decode("utf-8")
