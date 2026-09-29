# AECHI - Adaptive Edge-Cloud Hierarchical Intelligence for Urban Hazard Triage

> **Dynamic Cascading Inference with Zero-Trust Local Anonymization**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![AWS Serverless](https://img.shields.io/badge/AWS-Serverless-orange.svg)](https://aws.amazon.com/serverless/)
[![Vite + React](https://img.shields.io/badge/Dashboard-React_18_%2B_Vite-61dafb.svg)](dashboard)

---

## 🚨 Problem Statement

Modern metropolitan IoT deployments face three critical bottlenecks:

| Bottleneck | Industry Reality | AECHI Solution |
|---|---|---|
| **Network Congestion** | Continuous 1080p/4K streaming exhausts backhaul bandwidth | 3-tier lightweight inference runs at the edge; only compact telemetry + anonymized $128 \times 128$ evidence crops are uploaded. |
| **Compute & Power Caps** | Edge devices cannot sustain heavy vision models continuously | **Dynamic Cascading Pipeline**: `nano` (~2.5ms) → `small` (~8ms) → `medium` (~25ms), dynamically escalated based on confidence thresholds. |
| **Data Privacy (GDPR / DPDP)** | Streaming unredacted faces and license plates violates compliance | **Zero-Trust Edge Anonymization**: Faces blurred (MediaPipe/Haar) and plates blackened before any network transmission. |

---

## 🏛️ System Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         EDGE NODE (RPi / Jetson / PC)                         │
│                                                                               │
│  Camera Feed ──> YOLOv8-nano (always-on, low-power baseline)                  │
│                        │                                                      │
│                 conf < 0.60?                                                  │
│                        │ YES ──> YOLOv8-small (tier 1 escalation)             │
│                        │               │                                      │
│                        │        still < 0.75? ──> YOLOv8-medium (tier 2 final)│
│                        │               │                 │                    │
│                        ▼               ▼                 ▼                    │
│                 Zero-Trust Anonymizer (Face Blur + Plate Redaction)           │
│                        │                                                      │
│                        ▼                                                      │
│                 Authenticated Uploader (mTLS X.509 / HTTPS + Geo-Tagging)     │
└────────────────────────┼──────────────────────────────────────────────────────┘
                         │ HTTPS / mTLS
                         ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            AWS SERVERLESS BACKEND                             │
│                                                                               │
│  API Gateway ──> Lambda: Ingest ──┬──> Amazon S3 (Anonymized Crops Archive)   │
│                                   └──> DynamoDB (Raw Telemetry + 7d TTL)      │
│                                                  │                            │
│                                          EventBridge Bus                      │
│                                                  │                            │
│                                                  ▼                            │
│                                          Lambda: Triage                       │
│                               (Deduplication + Spatial Geo-Clustering)        │
│                                                  │                            │
│                                                  ▼                            │
│                                          Amazon SNS Topic                     │
│                                                  │                            │
│                                                  ▼                            │
│                                          Lambda: Alert                        │
│                               (Slack/PagerDuty Webhook + SES Email)           │
└────────────────────────┼──────────────────────────────────────────────────────┘
                         │ REST / Polling Stream
                         ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                      TACTICAL COMMAND CENTER DASHBOARD                        │
│   • Live Urban GIS Map       • Multi-Camera Incident Clusters                 │
│   • Threat Breakdown Charts  • Edge Fleet & Threshold Tuning                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
AECHI/
├── edge_node/                  # Edge device runtime
│   ├── main.py                 # Live camera loop + cascade + anonymizer
│   ├── cascading_pipeline.py   # 3-tier YOLO cascade (nano -> small -> medium)
│   ├── anonymizer/             # Zero-trust privacy module
│   │   ├── face_blur.py        # MediaPipe / Haar cascade face blur
│   │   └── plate_redact.py     # Contour morphology + aspect ratio redaction
│   ├── uploader.py             # mTLS / authenticated payload uploader
│   ├── simulate.py             # Multi-node urban fleet simulator
│   ├── requirements.txt        # Python dependencies
│   └── tests/                  # Unit test suite
│       ├── test_cascading.py
│       ├── test_anonymizer.py
│       └── test_uploader.py
│
├── cloud_backend/              # AWS Serverless SAM Backend
│   ├── api/
│   │   └── template.yaml       # SAM template (API Gateway, Lambdas, DynamoDB, S3)
│   ├── lambdas/
│   │   ├── ingest/             # S3 crop persistence + DynamoDB storage
│   │   ├── triage/             # Spatial-temporal geo-clustering + scoring
│   │   ├── alert/              # Webhook (Slack/PagerDuty) + SES notifications
│   │   └── dashboard/          # Serves incidents, events, map GIS, and stats
│   ├── requirements.txt
│   └── tests/
│       └── test_lambdas.py     # Lambda unit tests with mocked AWS SDK
│
├── dashboard/                  # React 18 + Vite + Tailwind Tactical UI
│   ├── src/
│   │   ├── components/         # HazardMap, IncidentsView, FleetConfigView, etc.
│   │   ├── api.js              # API client with offline fallback support
│   │   └── App.jsx             # Multi-view command center
│   ├── package.json
│   └── amplify.yml             # AWS Amplify hosting configuration
│
├── infra/                      # Infrastructure as Code (IaC)
│   └── terraform/              # Terraform alternative deployment
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
├── docs/                       # Architecture specifications
│   └── architecture.md
├── demo/                       # Local demo assets & video generators
│   └── generate_sample_video.py
├── LICENSE                     # MIT License
└── .github/
    └── workflows/
        └── deploy_aws.yml      # CI/CD: Automated testing + SAM deploy
```

---

## 🚀 Quick Start Guide

### 1. Run Edge Node Unit Tests
```bash
cd edge_node
python -m unittest discover tests -v
```

### 2. Launch Urban Fleet Simulation (No Hardware Needed)
Simulate 3 distributed camera nodes transmitting real-time hazards with geo-coordinates:
```bash
cd edge_node
python simulate.py --fleet --nodes 3 --endpoint https://<your-api-gateway-url>.amazonaws.com/prod
```

### 3. Deploy Serverless Backend to AWS
```bash
cd cloud_backend/api
sam build
sam deploy --guided
```

### 4. Launch Tactical Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser. If no AWS backend is deployed, the dashboard automatically initializes with rich interactive demo telemetry.

---

## 🔒 Security & Privacy Guarantee

* **Edge Anonymization**: All faces and license plates are permanently obscured using Gaussian blur and morphological blackout **prior** to network transmission.
* **Encrypted Uplink**: Mutual TLS (mTLS) with X.509 client certificate authentication ensures only authorized edge devices can push data to API Gateway.
* **Data Minimization**: Raw video streams never leave the edge; only structured metadata and $128 \times 128$ anonymized evidence crops are stored with automated 7-day DynamoDB TTL and 30-day S3 expiration.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
