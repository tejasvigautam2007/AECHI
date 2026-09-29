# AECHI — Adaptive Edge-Cloud Hierarchical Intelligence for Urban Hazard Triage

> **Dynamic Cascading Inference with Zero-Trust Local Anonymization**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![AWS Serverless](https://img.shields.io/badge/AWS-Serverless-orange.svg)](https://aws.amazon.com/serverless/)

---

## 🎯 Problem Statement

Modern urban IoT deployments face three critical bottlenecks:

| Problem | Industry Reality | AECHI Solution |
|---|---|---|
| **Network Congestion** | Edge cameras can't stream HD video 24/7 | Run lightweight inference locally, only upload metadata + anonymized crops |
| **Compute Constraints** | Low-power edge nodes can't run large CV models continuously | Cascading model pipeline: nano→small→medium triggered by confidence thresholds |
| **Data Privacy (GDPR/DPDP)** | Raw faces & license plates violate compliance | Zero-trust anonymization at edge before any data leaves the node |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EDGE NODE (RPi / Jetson Nano)            │
│                                                                  │
│  Camera Feed → YOLOv8-nano (always-on, low-power)               │
│                    │                                             │
│           confidence < 0.6?                                      │
│                    │ YES → YOLOv8-small (escalate)              │
│                    │         │                                   │
│                    │  still < 0.75? → YOLOv8-medium (final)    │
│                    │                                             │
│  Detected Objects → Anonymizer (blur faces, redact plates)      │
│                    │                                             │
│  Payload: {timestamp, class, confidence, bbox, anon_crop_b64}  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS (mTLS)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS SERVERLESS BACKEND                        │
│                                                                  │
│  API Gateway → Lambda: ingest  → DynamoDB (raw events)         │
│                    │                                             │
│               EventBridge → Lambda: triage                      │
│                    │  (severity scoring, dedup, geo-cluster)    │
│                    │                                             │
│               SNS → Lambda: alert (PagerDuty / email)          │
│                    │                                             │
│               S3 (anonymized crops archive)                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ WebSocket / REST
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│               LIVE DASHBOARD (React + AWS Amplify)               │
│  Real-time hazard map · Severity heatmap · Alert feed · Stats  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Repository Structure

```
AECHI/
├── edge_node/               # Runs on Raspberry Pi / Jetson Nano / any PC (simulation mode)
│   ├── main.py              # Entry point: camera loop + cascading inference
│   ├── cascading_pipeline.py# YOLOv8 nano→small→medium cascade logic
│   ├── anonymizer/          # Zero-trust face blur + license plate redaction
│   │   ├── face_blur.py
│   │   └── plate_redact.py
│   ├── uploader.py          # mTLS HTTPS payload sender
│   ├── simulate.py          # Simulation mode (no camera required, uses video files)
│   └── requirements.txt
│
├── cloud_backend/           # AWS Serverless
│   ├── lambdas/
│   │   ├── ingest/          # Lambda: receives edge payloads
│   │   ├── triage/          # Lambda: severity scoring + dedup
│   │   └── alert/           # Lambda: SNS alerting
│   ├── api/
│   │   └── template.yaml    # SAM template (API Gateway + Lambdas + DynamoDB + S3)
│   └── requirements.txt
│
├── dashboard/               # React live dashboard
│   ├── src/
│   │   ├── components/      # HazardMap, AlertFeed, SeverityGauge, StatsBar
│   │   └── pages/           # Home, Analytics, Config
│   ├── package.json
│   └── amplify.yml
│
├── infra/
│   ├── cloudformation/      # CloudFormation stacks
│   └── terraform/           # Terraform alternative
│
├── .github/
│   └── workflows/
│       ├── edge_tests.yml   # CI: edge node unit tests
│       └── deploy_aws.yml   # CD: SAM deploy to AWS on push to main
│
├── docs/
│   └── architecture.md
└── demo/                    # Sample video files for simulation mode
```

---

## 🚀 Quick Start

### 1. Edge Node (Simulation Mode — no camera needed)
```bash
cd edge_node
pip install -r requirements.txt
# Download YOLOv8 weights automatically on first run
python simulate.py --video demo/sample_urban.mp4 --endpoint https://<your-api-gw>.amazonaws.com/prod
```

### 2. Deploy AWS Backend
```bash
cd cloud_backend/api
sam build
sam deploy --guided
```

### 3. Dashboard
```bash
cd dashboard
npm install
npm run dev          # local dev
# OR: push to GitHub → auto-deploys via AWS Amplify
```

---

## 🔑 Key Technical Features

- **Cascading Inference**: 3-tier model escalation (nano 2ms → small 8ms → medium 25ms avg latency)
- **Zero-Trust Anonymization**: Faces blurred with MediaPipe, plates redacted with OpenCV regex-OCR — *before* any network call
- **Serverless Scaling**: API Gateway + Lambda scales from 0 to 10,000 events/sec automatically
- **Real-Time Dashboard**: WebSocket push from DynamoDB Streams → API Gateway WS → React
- **Privacy-First Payload**: Only metadata + anonymized crops leave the edge node

---

## 👨‍💻 Team

Built for academic evaluation — Edge AI + Serverless Cloud integration project.

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
