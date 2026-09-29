"""
Edge Node Uploader
Batches and sends anonymized detection payloads to AWS API Gateway.
Supports Mutual TLS (mTLS) client certificate authentication, API key auth,
exponential backoff retries, and offline queueing.
"""

import base64
import json
import logging
import os
import queue
import threading
import time
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger("aechi.uploader")

MAX_QUEUE_SIZE = 1000
BATCH_SIZE = 10
RETRY_DELAYS = [1, 2, 4, 8, 16]


class EdgeUploader:
    """
    Non-blocking upload manager with mTLS support,
    offline spooling, and automatic exponential retry.
    """

    def __init__(
        self,
        endpoint: str,
        device_id: str,
        api_key: Optional[str] = None,
        client_cert: Optional[str] = None,
        client_key: Optional[str] = None,
        ca_bundle: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ):
        self.endpoint = endpoint.rstrip("/") + ("/events" if not endpoint.endswith("/events") else "")
        self.device_id = device_id
        self.latitude = latitude
        self.longitude = longitude

        # mTLS certificate configuration
        self.client_cert = client_cert
        self.client_key = client_key
        self.ca_bundle = ca_bundle

        # Verify cert file existence if configured
        if client_cert and not os.path.exists(client_cert):
            logger.warning(f"Client cert path does not exist: {client_cert}")
        if client_key and not os.path.exists(client_key):
            logger.warning(f"Client key path does not exist: {client_key}")

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

        mtls_enabled = bool(self.client_cert and self.client_key)
        logger.info(f"EdgeUploader started | endpoint={self.endpoint} | mTLS={'ENABLED' if mtls_enabled else 'STANDARD_HTTPS'}")

    def enqueue(self, payload: Dict[str, Any], frame=None, bbox: Optional[List[int]] = None) -> None:
        """
        Enqueue a detection payload with its anonymized crop and geo-coordinates.
        """
        try:
            # Attach edge device location if not already specified
            if "lat" not in payload and self.latitude is not None:
                payload["lat"] = self.latitude
            if "lon" not in payload and self.longitude is not None:
                payload["lon"] = self.longitude

            # Attach base64 crop if frame provided
            if frame is not None and bbox is not None:
                crop_b64 = self._crop_to_b64(frame, bbox)
                payload["anon_crop_b64"] = crop_b64

            self._queue.put_nowait(payload)
        except queue.Full:
            logger.warning("Upload queue full — dropping oldest event to prevent memory pressure")
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

    def _send_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Send a batch of payloads with retry logic and mTLS."""
        body = json.dumps({"device_id": self.device_id, "events": batch})

        cert_arg = (self.client_cert, self.client_key) if (self.client_cert and self.client_key) else None
        verify_arg = self.ca_bundle if self.ca_bundle else True

        for attempt, delay in enumerate(RETRY_DELAYS + [None]):
            try:
                resp = requests.post(
                    self.endpoint,
                    data=body,
                    headers=self.headers,
                    cert=cert_arg,
                    verify=verify_arg,
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
    def _crop_to_b64(frame, bbox: List[int]) -> str:
        """Crop, resize, and encode frame region as base64 JPEG."""
        if frame is None or len(bbox) < 4:
            return ""

        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        crop = frame[y1:y2, x1:x2]

        if crop.size == 0:
            return ""

        try:
            import cv2
            crop_resized = cv2.resize(crop, (128, 128))
            _, buf = cv2.imencode(".jpg", crop_resized, [cv2.IMWRITE_JPEG_QUALITY, 75])
            return base64.b64encode(buf).decode("utf-8")
        except Exception:
            try:
                from PIL import Image
                import io
                # Fallback to PIL
                rgb = crop[:, :, ::-1] if crop.shape[2] == 3 else crop
                img = Image.fromarray(rgb).resize((128, 128))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=75)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
            except Exception:
                return ""
