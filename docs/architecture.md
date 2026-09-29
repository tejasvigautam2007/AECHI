# AECHI Architecture Documentation

> **Adaptive Edge-Cloud Hierarchical Intelligence for Urban Hazard Triage**  
> *Dynamic Cascading Inference with Zero-Trust Local Anonymization*

---

## 1. Executive System Overview

Urban Internet of Things (IoT) surveillance systems capture terabytes of continuous video across metropolitan intersections. However, streaming 24/7 uncompressed HD video to centralized cloud providers incurs severe drawbacks:
1. **Network Congestion & Bandwidth Costs**: 4K/1080p feeds overwhelm municipal backhauls.
2. **Compute Bottlenecks & Thermal Throttling**: Running heavy vision transformers or large neural networks continuously on low-power edge nodes (Jetson Nano, Raspberry Pi) causes thermal throttling and power starvation.
3. **Data Privacy Regulations (GDPR / DPDP Act)**: Transmitting raw human faces and motor vehicle license plates without consent violates statutory data protection mandates.

AECHI resolves this trilemma via a two-tier hierarchical architecture:
* **Edge Tier**: Always-on low-power cascading inference coupled with zero-trust local anonymization.
* **Serverless Cloud Tier**: Event-driven ingestion, distributed spatial-temporal clustering (Geo-Clustering), and real-time urgency triage.

```
+───────────────────────────────────────────────────────────────────────────────+
|                                EDGE NODE                                      |
|                                                                               |
|  [Camera Feed] ──> [YOLOv8-Nano]                                              |
|                         │                                                     |
|                  conf < 0.60?                                                 |
|                         │ YES                                                 |
|                         ▼                                                     |
|                   [YOLOv8-Small]                                              |
|                         │                                                     |
|                  conf < 0.75?                                                 |
|                         │ YES                                                 |
|                         ▼                                                     |
|                   [YOLOv8-Medium]                                             |
|                         │                                                     |
|                         ▼                                                     |
|           [Zero-Trust Anonymizer] (Face Blur + Plate Redaction)               |
|                         │                                                     |
|                         ▼                                                     |
|           [Encrypted mTLS Uploader] (Metadata + Base64 Evidence Crop)         |
+─────────────────────────┼─────────────────────────────────────────────────────+
                          │ HTTPS (mTLS X.509)
                          ▼
+───────────────────────────────────────────────────────────────────────────────+
|                           AWS SERVERLESS CLOUD                                |
|                                                                               |
|  [API Gateway] ──> [Lambda: Ingest] ──┬──> [S3: Anonymized Crops Archive]     |
|                                       └──> [DynamoDB: aechi-events]           |
|                                                      │                        |
|                                             [EventBridge Bus]                 |
|                                                      │                        |
|                                                      ▼                        |
|                                             [Lambda: Triage]                  |
|                                       (Deduplication + Geo-Clustering)        |
|                                                      │                        |
|                                                      ▼                        |
|                                                [SNS Alerts]                   |
|                                                      │                        |
|                                                      ▼                        |
|                                              [Lambda: Alert]                  |
|                                       (Slack / PagerDuty / Email SES)         |
+───────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Edge Layer: Dynamic Cascading Inference

Edge nodes process frames through a 3-tier cascading execution pipeline:
* **Tier 0 (YOLOv8-Nano)**: Runs continuously at minimal wattage (~2.5ms inference on edge accelerators). Handles obvious, clear conditions.
* **Tier 1 (YOLOv8-Small)**: Triggered dynamically when maximum detection confidence drops below $\tau_{nano} = 0.60$ (~8ms inference). Resolves medium-distance or partially occluded hazards.
* **Tier 2 (YOLOv8-Medium)**: Invoked when confidence remains below $\tau_{small} = 0.75$ (~25ms inference). Provides high-resolution feature maps for complex multi-hazard scenes.

### Latency & Efficiency Gains
Compared to running YOLOv8-medium on every frame, AECHI achieves an average **~78% reduction in edge compute latency** and **over 95% bandwidth savings**, transmitting only compact JSON payloads and anonymized $128 \times 128$ evidence crops.

---

## 3. Zero-Trust Local Anonymization

Before any packet leaves the local edge node's memory space:
1. **Face Blurring**:
   * Evaluated via MediaPipe FaceDetection (with OpenCV Haar cascade fallback).
   * Irreversible 51x51 Gaussian blur or mosaic pixelation is applied to all facial bounding boxes.
2. **License Plate Redaction**:
   * Multi-stage vehicle ROI extraction (cars, trucks, buses, motorcycles).
   * Horizontal Sobel edge gradient + morphological rectangular closing ($17 \times 3$ kernel).
   * Candidate contours matching plate aspect ratios ($2.0 \le \text{AR} \le 5.5$) are fully blackened (`(0, 0, 0)` filled rect) with a 4px safety buffer.

---

## 4. Cloud Serverless Architecture

1. **Ingest Lambda**:
   * Parses JSON payloads from edge devices.
   * Decodes base64 crops and streams them directly into Amazon S3 (`CropsBucket`).
   * Writes initial telemetry records to DynamoDB with a 7-day TTL.
   * Emits batch events (`aechi.edge / HazardDetection`) to EventBridge.
2. **Triage Lambda**:
   * **Distributed Deduplication**: Conditional DynamoDB atomic locks ensure identical events within 5-second windows are not processed redundantly.
   * **Geo-Clustering**: Applies Haversine spatial correlation over active incidents ($r \le 150\text{m}$, $\Delta t \le 60\text{s}$). Multi-camera verification boosts the triage score and updates the incident cluster.
   * **Scoring Formula**:
     $$\text{Triage Score} = \min\left(10, \left(\text{Base} + \text{Conf Bonus} + \text{Multi-Cam Bonus}\right) \times \text{Multiplier}\right)$$
3. **Alert Lambda**:
   * Subscribes to the SNS alert topic.
   * Dispatches alerts to Slack / PagerDuty webhooks, Amazon SES email, and DynamoDB's live alerts feed.
4. **Dashboard API Lambda**:
   * Serves recent events, active geo-incidents, radar map telemetry, and statistics to the React frontend.
   * Issues presigned S3 URLs for viewing evidence crops securely.

---

## 5. Security & Compliance Matrix

| Regulation / Standard | Requirement | AECHI Implementation |
|---|---|---|
| **GDPR Art. 25 & 32** | Privacy by Design & Security | Face blur & plate redaction executed at edge before network serialization. |
| **India DPDP Act 2023** | Personal Data Protection | PII is never transmitted to cloud storage or logged in plaintext. |
| **Zero-Trust Network** | Authenticated Edge Uplink | Mutual TLS (mTLS) with X.509 client certificates and optional API key tokens. |
| **Data Retention** | Ephemeral Telemetry | DynamoDB TTL (7 days for events, 48 hours for alerts) and S3 Lifecycle (30 days). |
