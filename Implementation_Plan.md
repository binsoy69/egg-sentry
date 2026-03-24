# EggSentry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an end-to-end egg counting and approximate size classification system for USEP Poultry — from periodic camera capture on a Raspberry Pi 5 edge device, through a REST API backend, to a React dashboard deployed on Vercel.

**Architecture:** A three-tier system: (1) an edge agent on Raspberry Pi 5 periodically captures still frames, runs YOLO inference to detect and count eggs, classifies size by bounding-box geometry, and POSTs results to a REST API; (2) a FastAPI backend on Railway stores events in PostgreSQL and serves dashboard data; (3) a React frontend on Vercel displays production analytics, history, alerts, and device status.

**Tech Stack:** Python 3.11+ (edge agent + backend), FastAPI, PostgreSQL, Ultralytics YOLOv8 Nano, React 18 + Vite + TailwindCSS + Recharts, Railway (backend/DB), Vercel (frontend).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Edge Inference Design](#3-edge-inference-design)
4. [Approximate Egg Size Classification Design](#4-approximate-egg-size-classification-design)
5. [Model Strategy](#5-model-strategy)
6. [Backend / API Plan](#6-backend--api-plan)
7. [Database Design](#7-database-design)
8. [Frontend / Web App Plan](#8-frontend--web-app-plan)
9. [Alerts and Business Logic](#9-alerts-and-business-logic)
10. [Deployment Plan](#10-deployment-plan)
11. [Development Roadmap](#11-development-roadmap)
12. [Risks and Mitigation](#12-risks-and-mitigation)
13. [Testing Strategy](#13-testing-strategy)
14. [Suggested Folder / Project Structure](#14-suggested-folder--project-structure)
15. [Recommended Defaults for v1](#15-recommended-defaults-for-v1)

---

## 1. Executive Summary

### Recommended Architecture

EggSentry is a **three-tier periodic-capture system**:

1. **Edge Agent** (Raspberry Pi 5 or PC): A Python daemon that wakes on a configurable interval (default: every 2 minutes), captures a single still frame from a USB/CSI camera, runs YOLOv8 Nano inference to detect eggs, derives approximate size from bounding-box area using rules-based thresholds, stabilizes counts across multiple captures, and POSTs confirmed detection events to the backend API. Between captures, the agent sleeps — the camera is not streaming.

2. **Backend API** (FastAPI on Railway): Receives detection events from the edge device, stores them in PostgreSQL, computes daily/weekly/monthly/yearly aggregations, manages device heartbeat and alerts, and serves dashboard data via REST endpoints. Authentication uses JWT tokens with predefined user accounts (no signup).

3. **Frontend Dashboard** (React on Vercel): A responsive single-page application matching the UI mockups exactly — login page, dashboard with camera card + weekly/monthly/yearly stats + metric cards + charts, history page with filterable records, and a modify-camera modal.

### Why This Design Fits the Constraints

- **Periodic capture** eliminates continuous GPU/CPU load, reduces heat on the Pi, and avoids unnecessary power consumption. Since eggs are stationary after being laid, nothing is lost by capturing every 2 minutes instead of streaming 30fps.
- **Rules-based size classification** from bounding-box geometry avoids the need for a second trained model. The existing `counter-yolo26n.pt` model detects eggs; bounding-box area relative to a calibrated reference determines size class.
- **YOLOv8 Nano** is the smallest YOLO variant (~5MB), proven to run on Raspberry Pi 5 at usable speeds for single-frame inference.
- **FastAPI + PostgreSQL on Railway** is the simplest deployment path — Railway provides managed Postgres and auto-deploys from Git with zero DevOps.
- **React on Vercel** is zero-config deployment with automatic HTTPS and CDN.
- **Two predefined accounts** with JWT avoids the complexity of a full auth system while being trivially extensible.

---

## 2. System Architecture

### 2.1 End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        EDGE DEVICE (RPi5 / PC)                  │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  Camera   │───>│  Capture │───>│   YOLO   │───>│   Size    │  │
│  │ (USB/CSI) │    │  (still) │    │ Inference│    │ Classify  │  │
│  └──────────┘    └──────────┘    └──────────┘    └─────┬─────┘  │
│                                                        │        │
│                              ┌─────────────┐           │        │
│                              │  Stabilizer  │<──────────┘        │
│                              │ (N-frame     │                    │
│                              │  consensus)  │                    │
│                              └──────┬──────┘                    │
│                                     │  count changed?           │
│                                     ▼                           │
│                              ┌─────────────┐                    │
│                              │  HTTP POST   │                    │
│                              │  to Backend  │                    │
│                              └──────┬──────┘                    │
│                                     │                           │
│  Heartbeat ─────────────────────────┤ (every 60s)              │
└─────────────────────────────────────┼───────────────────────────┘
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (Railway)                            │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  FastAPI  │───>│  Auth    │    │  Events  │    │  Alerts   │  │
│  │  Router   │    │  (JWT)   │    │  Service │    │  Engine   │  │
│  └──────────┘    └──────────┘    └──────────┘    └───────────┘  │
│                                       │                         │
│                                       ▼                         │
│                              ┌──────────────┐                   │
│                              │  PostgreSQL   │                   │
│                              │  (Railway)    │                   │
│                              └──────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                                      │ REST API
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vercel)                             │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  Login   │    │ Dashboard│    │ History  │    │  Modify   │  │
│  │  Page    │    │  Page    │    │  Page    │    │  Camera   │  │
│  └──────────┘    └──────────┘    └──────────┘    └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Edge Device Responsibilities

- **Periodic image capture** — capture one still frame every N seconds (default: 120s / 2 minutes).
- **YOLO inference** — run `counter-yolo26n.pt` on captured frame, extract detections with bounding boxes, confidence scores, and class IDs.
- **Size classification** — for each detected egg, compute bounding-box area, map to size class (small / medium / large / extra-large / jumbo / unknown) using calibrated pixel-area thresholds.
- **Count stabilization** — maintain a rolling window of recent capture results; only emit an event when the stabilized count changes or when a new egg detection differs from the previous confirmed state.
- **Event emission** — POST a `count_event` to the backend API when the stabilized count increases (new egg detected).
- **Heartbeat** — POST a heartbeat to the backend every 60 seconds so the dashboard can show device online/offline status.
- **Video test mode** — accept a video file path instead of a camera source, processing frames at the configured interval to simulate periodic capture. This allows testing the full pipeline without a live camera.

### 2.3 Backend Responsibilities

- **Authentication** — issue and validate JWT tokens for predefined users; issue device API keys for edge devices.
- **Event ingestion** — accept detection events from edge devices and store them in PostgreSQL.
- **Aggregation** — compute daily, weekly, monthly, and yearly egg totals and averages on demand.
- **Alerts** — evaluate alert rules on each event or on a schedule (device offline, low production, etc.).
- **Dashboard data** — serve aggregated stats, egg records, size distribution, and alert data via REST endpoints.

### 2.4 Frontend Responsibilities

- **Login** — authenticate user, store JWT token, redirect to dashboard.
- **Dashboard** — display camera info card, weekly/monthly/yearly stat cards, metric cards (today's eggs, all-time total, best day, top size), daily production line chart, egg size distribution bar chart.
- **History** — paginated/filterable table of individual egg detection records with date, size badge, and timestamp.
- **Modify Camera** — modal dialog to update cage count and chicken count for the device.
- **Logout** — clear token, redirect to login.

### 2.5 Why Periodic Still-Image Inference

| Continuous Video | Periodic Still Capture |
|---|---|
| 30fps = 30 inferences/sec | 1 inference every 2 min = 0.008/sec |
| Camera always on = heat | Camera active <1s per capture |
| GPU/CPU at 100% on Pi | CPU idle 99.9% of the time |
| Needs object tracking | No tracking needed (eggs stationary) |
| Complex dedup logic | Simple count-change detection |
| ~15W continuous draw | ~0.5W average draw |

Eggs don't move after being laid. A 2-minute capture interval means a new egg is detected within 2 minutes of being laid — acceptable for a production monitoring dashboard that reports daily totals.

---

## 3. Edge Inference Design

### 3.1 Agent Architecture

The edge agent runs as a Python script (systemd service on Pi, or manual run on PC). It follows a **capture-infer-report** loop with sleep between cycles.

```
┌─────────────────────────────────────────────┐
│               AGENT MAIN LOOP               │
│                                             │
│  ┌─────────┐                                │
│  │  SLEEP   │<──────────────────────┐       │
│  │ (N sec)  │                       │       │
│  └────┬─────┘                       │       │
│       ▼                             │       │
│  ┌─────────┐                        │       │
│  │ CAPTURE  │  ── camera open ──>   │       │
│  │  FRAME   │  ── snap frame  ──>   │       │
│  │          │  ── camera close ──>  │       │
│  └────┬─────┘                       │       │
│       ▼                             │       │
│  ┌─────────┐                        │       │
│  │  INFER   │  ── YOLO detect ──>   │       │
│  │          │  ── extract boxes ──> │       │
│  └────┬─────┘                       │       │
│       ▼                             │       │
│  ┌─────────┐                        │       │
│  │ CLASSIFY │  ── box area ──>      │       │
│  │  SIZES   │  ── threshold map ──> │       │
│  └────┬─────┘                       │       │
│       ▼                             │       │
│  ┌──────────┐                       │       │
│  │STABILIZE │  ── compare to ──>    │       │
│  │  & DIFF  │     previous state    │       │
│  └────┬─────┘                       │       │
│       ▼                             │       │
│  ┌──────────┐                       │       │
│  │  REPORT  │  ── POST events ──>   │       │
│  │  (if     │  ── heartbeat ──>     │       │
│  │  changed)│                       │       │
│  └────┬─────┘                       │       │
│       └─────────────────────────────┘       │
└─────────────────────────────────────────────┘
```

### 3.2 Capture Schedule Strategy

**v1 default: capture every 120 seconds (2 minutes).**

- The agent opens the camera, captures a single frame, closes the camera.
- On Raspberry Pi with a CSI or USB camera, `cv2.VideoCapture` can be opened/closed per capture. On some USB cameras, a brief warm-up (0.5s delay after open, discard first frame) is needed for auto-exposure.
- The interval is configurable via environment variable `CAPTURE_INTERVAL_SECONDS`.

**Camera warm-up sequence (per capture):**

```
1. cap = cv2.VideoCapture(source)
2. sleep(0.5)                      # auto-exposure settle
3. cap.read()                      # discard first frame
4. ret, frame = cap.read()         # use this frame
5. cap.release()                   # close camera
```

### 3.3 Video Test Mode

For development and testing, the agent accepts a video file path instead of a camera index. In video mode:

- Open the video file with `cv2.VideoCapture(path)`.
- Read frames at the configured interval (skip frames based on video FPS * interval).
- Process each sampled frame through the same infer-classify-stabilize pipeline.
- Optionally display annotated frames in an OpenCV window (enabled by `--display` flag).
- When the video ends, either loop (for continuous testing) or exit.
- This enables full end-to-end testing of the pipeline, including backend event submission, without a live camera.

**Frame skipping formula for video test mode:**

```
frames_to_skip = int(video_fps * capture_interval_seconds)
```

For a 30fps video with 120s interval, the agent would sample 1 frame every 3600 frames. For practical testing, use a shorter interval (e.g., 5 seconds = skip every 150 frames).

### 3.4 Count Stabilization Logic

Since eggs are stationary, count should be stable across consecutive captures. The stabilizer prevents noisy fluctuations from transient detection failures (e.g., lighting flicker, partial occlusion).

**Algorithm: Rolling Majority Vote**

```
# Maintain a rolling window of the last K capture results
STABILITY_WINDOW = 3  # number of recent captures

capture_history = deque(maxlen=STABILITY_WINDOW)

# After each capture:
capture_history.append({
    "total_count": len(detections),
    "size_counts": {"small": 1, "medium": 2, ...},
    "detections": [...]  # per-egg details
})

# Stabilized count = mode (most frequent) of recent total_counts
stabilized_count = Counter(
    [c["total_count"] for c in capture_history]
).most_common(1)[0][0]
```

**Why K=3:** With 2-minute intervals, K=3 means a new egg must be detected in at least 2 out of 3 consecutive captures (6 minutes window) before being confirmed. This is conservative enough to filter noise but fast enough for poultry monitoring.

### 3.5 Event Emission Logic

The agent tracks the **last confirmed state** (count + size breakdown). An event is emitted when:

1. **Count increases** — new egg(s) detected. Emit one `count_event` per new egg (if count goes from 3 to 5, emit 2 events).
2. **Full snapshot** — every capture cycle, the agent also sends a lightweight `snapshot` payload with the current total count and size breakdown, so the backend can reconcile if events were lost.

**When NOT to emit:**
- Count decreased (likely a false negative or egg removed — log locally but don't emit negative event).
- Count unchanged (no new eggs since last report).

**Pseudocode:**

```
previous_confirmed_count = 0
previous_size_breakdown = {}

def on_stabilized_result(stabilized_count, size_breakdown, detections):
    global previous_confirmed_count, previous_size_breakdown

    new_eggs = stabilized_count - previous_confirmed_count

    if new_eggs > 0:
        # Identify which detections are "new" by comparing sizes
        new_egg_sizes = compute_new_egg_sizes(
            previous_size_breakdown, size_breakdown, new_eggs
        )
        for size in new_egg_sizes:
            post_event(type="new_egg", size=size)

        previous_confirmed_count = stabilized_count
        previous_size_breakdown = size_breakdown

    # Always send snapshot for reconciliation
    post_snapshot(total=stabilized_count, sizes=size_breakdown)
```

### 3.6 How YOLO Is Used

1. Load `counter-yolo26n.pt` at agent startup using `ultralytics.YOLO()`.
2. For each captured frame, run `model.predict(frame, conf=0.5, verbose=False)`.
3. Extract from results:
   - `boxes.xyxy` — bounding box coordinates `[x1, y1, x2, y2]`
   - `boxes.conf` — confidence score per detection
   - `boxes.cls` — class ID (single class: `egg`)
4. Filter detections below confidence threshold (default: 0.5).
5. Count remaining detections = raw egg count.
6. Pass each bounding box to the size classifier.

**Note:** We use `model.predict()` instead of `model.track()` for periodic capture. Tracking requires continuous frames and is unnecessary when eggs are stationary and captures are minutes apart. The existing `egg_sentry.py` uses tracking for its video-processing mode — the edge agent will use `predict()` for periodic mode and optionally `track()` for video test mode display.

### 3.7 Egg Count Derivation

```
raw_count = number of detections with confidence >= threshold
```

For v1, this is straightforward since:
- Single class (`egg`) in the YOLO model.
- Fixed camera position means consistent field of view.
- No overlapping eggs expected in cage-based laying (eggs roll to collection area).

### 3.8 Handling Uncertain Detections

- **Low confidence detections (0.3 < conf < 0.5):** Logged locally but excluded from count. If the same low-confidence region persists across 3+ captures, flag it as a potential detection to the backend (could be an alert-worthy anomaly).
- **Overlapping boxes:** Apply Non-Maximum Suppression (NMS, built into YOLO) with IoU threshold of 0.5. This prevents double-counting overlapping eggs.
- **Edge-of-frame detections:** If a bounding box touches the frame edge (within 10px), classify its size as `unknown` since the full egg may not be visible.

---

## 4. Approximate Egg Size Classification Design

### 4.1 Approach: Rules-Based Bounding Box Area Thresholds

For v1, egg size is determined entirely from the **pixel area of the YOLO bounding box**. No second model is needed.

**Rationale:** With a fixed camera at a consistent distance from the laying area, the pixel area of a detected egg's bounding box correlates directly with the physical size of the egg. Larger eggs produce larger bounding boxes.

### 4.2 Size Classification Algorithm

```
def classify_egg_size(box_xyxy, frame_width, frame_height):
    x1, y1, x2, y2 = box_xyxy
    box_width = x2 - x1
    box_height = y2 - y1
    box_area = box_width * box_height

    # Normalize area relative to frame size for camera-independence
    frame_area = frame_width * frame_height
    normalized_area = box_area / frame_area

    # Check if box is at frame edge (possibly clipped)
    margin = 10  # pixels
    at_edge = (x1 < margin or y1 < margin or
               x2 > frame_width - margin or
               y2 > frame_height - margin)

    if at_edge:
        return "unknown"

    # Thresholds (calibrate with real data — see Section 4.4)
    if normalized_area < THRESHOLD_SMALL:
        return "small"
    elif normalized_area < THRESHOLD_MEDIUM:
        return "medium"
    elif normalized_area < THRESHOLD_LARGE:
        return "large"
    elif normalized_area < THRESHOLD_XL:
        return "extra-large"
    else:
        return "jumbo"
```

### 4.3 Size Classes

| Class | Typical Real Weight (ref only) | Detection Criteria |
|---|---|---|
| Small (S) | < 53g | `normalized_area < THRESHOLD_SMALL` |
| Medium (M) | 53–63g | `THRESHOLD_SMALL <= normalized_area < THRESHOLD_MEDIUM` |
| Large (L) | 63–73g | `THRESHOLD_MEDIUM <= normalized_area < THRESHOLD_LARGE` |
| Extra-Large (XL) | 73–83g | `THRESHOLD_LARGE <= normalized_area < THRESHOLD_XL` |
| Jumbo | > 83g | `normalized_area >= THRESHOLD_XL` |
| Unknown | — | Box at frame edge, confidence < 0.5, or ambiguous |

**Note:** Weight references are for context only. The system classifies by **visual size** (bounding-box area), not weight. There will be inaccuracies — this is acceptable for v1 approximate classification.

### 4.4 Threshold Calibration Process

To set initial thresholds:

1. **Collect calibration dataset:** Capture 50–100 frames with eggs of known sizes (manually measured or weighed). Ensure at least 5–10 examples per size class.
2. **Run YOLO inference** on each frame, extract bounding box areas.
3. **Compute `normalized_area`** for each detected egg.
4. **Plot distribution:** Create a scatter plot of `normalized_area` vs. known size class.
5. **Set thresholds** at natural break points between clusters. Start with percentile-based splits.
6. **Store thresholds** in a JSON config file that the edge agent loads at startup.

**Default starter thresholds (to be calibrated):**

```json
{
  "size_thresholds": {
    "small_max": 0.0020,
    "medium_max": 0.0030,
    "large_max": 0.0042,
    "xl_max": 0.0055
  }
}
```

These are placeholder values. **They must be calibrated with real camera data.** The exact values depend on camera resolution, distance from eggs, and lens focal length.

### 4.5 Aspect Ratio Sanity Check

As an additional filter, egg bounding boxes should have an aspect ratio (height/width) roughly between 0.8 and 1.5 (eggs are roughly oval). Detections with extreme aspect ratios (< 0.5 or > 2.0) may be false positives or partial occlusions — classify as `unknown`.

```
aspect_ratio = box_height / box_width
if aspect_ratio < 0.5 or aspect_ratio > 2.0:
    return "unknown"
```

### 4.6 Limitations and Assumptions

- **Fixed camera assumption:** Thresholds are only valid for one camera position/angle. If the camera moves, thresholds must be recalibrated.
- **Perspective distortion:** Eggs closer to the camera appear larger. If eggs can be at different distances from the lens, size classification will have error proportional to distance variation.
- **Single-class YOLO:** The current model detects "egg" as one class. Size is inferred post-detection, not by the model itself.
- **Accuracy expectation:** Expect ~70–80% accuracy on size classification for v1. This is approximate and is sufficient for trend analysis ("mostly medium eggs this week") but not for individual egg grading.
- **Overlapping eggs:** Two overlapping eggs may produce one large bounding box, classified as "jumbo" or "unknown". NMS mitigates this but isn't perfect.

---

## 5. Model Strategy

### 5.1 Model Selection

**Recommended: YOLOv8 Nano (already trained as `counter-yolo26n.pt`)**

The existing model is a ~5MB YOLOv8 Nano variant. This is the correct choice for Raspberry Pi 5 deployment:

| Model | Size | Pi5 Inference (est.) | Accuracy |
|---|---|---|---|
| YOLOv8n (Nano) | ~6MB | ~100–200ms/frame | Good for single-class |
| YOLOv8s (Small) | ~22MB | ~300–500ms/frame | Better but slower |
| YOLOv8m (Medium) | ~50MB | ~1–2s/frame | Overkill |

For single-class egg detection at 1 frame per 2 minutes, even 500ms inference is perfectly fine. But Nano is preferred to minimize resource usage and heat.

### 5.2 Training Data Requirements

Since the model is already trained, this section covers retraining or improvement:

- **Minimum training set:** 200–500 annotated images for single-class detection.
- **Recommended:** 500–1000 images with varied lighting conditions (morning, midday, afternoon, artificial light).
- **Negative examples:** Include 50–100 frames with no eggs to reduce false positives.
- **Augmentation:** Ultralytics handles augmentation automatically (flip, rotate, brightness, contrast).

### 5.3 Annotation Strategy

- **Tool:** Use [Roboflow](https://roboflow.com) (free tier, 1000 images) or [CVAT](https://cvat.ai) (open-source).
- **Format:** YOLO format (`.txt` files with `class_id center_x center_y width height` normalized coordinates).
- **Single class:** `0` = `egg`. No size classes in annotation — size is derived post-detection.
- **Labeling rules:**
  - Draw tight bounding boxes around each visible egg.
  - If an egg is >50% occluded, do not annotate it.
  - If an egg is at the frame edge and >50% visible, annotate it.

### 5.4 Deployment Runtime

**Recommendation: Use PyTorch (`.pt`) format directly via Ultralytics on both PC and Raspberry Pi 5.**

| Runtime | PC | Raspberry Pi 5 | Complexity |
|---|---|---|---|
| PyTorch (.pt) via Ultralytics | Works natively | Works (CPU) | Lowest — `pip install ultralytics` |
| ONNX Runtime | Works | Works | Medium — export + onnxruntime install |
| TFLite | N/A | Works | High — export + edge-specific tuning |
| OpenVINO | Intel only | N/A | N/A for Pi |

**v1 decision: Use `.pt` format with Ultralytics on both platforms.**

Why: The Ultralytics library handles `.pt` inference with zero configuration. On Raspberry Pi 5 (Cortex-A76, 4-core ARM), YOLOv8 Nano runs inference in ~100–300ms per frame using CPU. Since we only run inference once every 2 minutes, this is negligible load.

**Future optimization (v2):** Export to ONNX for ~30% speedup, or NCNN for ARM-optimized inference. Only worth doing if the capture interval decreases significantly.

### 5.5 Model File Location

```
models/
  counter-yolo26n.pt     # existing — single-class egg detector
```

The edge agent loads this model at startup. The model file is included in the repo (5.2MB is fine for Git).

---

## 6. Backend / API Plan

### 6.1 Stack

| Component | Choice | Reason |
|---|---|---|
| Framework | **FastAPI** | Async, auto-docs, Pydantic validation, Python ecosystem |
| Database | **PostgreSQL** | Reliable, Railway-managed, good for time-series queries |
| ORM | **SQLAlchemy 2.0** (async) | Mature, type-safe, works with Alembic migrations |
| Migrations | **Alembic** | Standard for SQLAlchemy |
| Auth | **JWT** (python-jose + passlib) | Stateless, simple, no session store |
| Server | **Uvicorn** | ASGI server, production-ready |

### 6.2 Authentication Design

#### User Authentication (Dashboard)

- **No signup endpoint.** Users are seeded in the database via a migration or startup script.
- **Login:** POST `/api/auth/login` with `{username, password}` → returns `{access_token, token_type}`.
- **Passwords:** Hashed with bcrypt via `passlib`.
- **JWT payload:** `{sub: user_id, username: str, exp: datetime}`.
- **Token expiry:** 24 hours. Frontend stores token in `localStorage`.
- **Protected routes:** All `/api/*` endpoints (except `/api/auth/login`) require `Authorization: Bearer <token>` header.

#### Device Authentication (Edge Agent)

- **API key-based.** Each device has a unique API key stored in the `devices` table.
- **Edge agent sends:** `X-Device-Key: <api_key>` header on all requests.
- **Simpler than JWT** because devices don't log in/out — they use a static key.
- **Key generation:** Generated during device registration (manual, via backend admin or seed script).

### 6.3 REST API Endpoints

#### Size Label Convention

The database stores **canonical lowercase names**: `small`, `medium`, `large`, `extra-large`, `jumbo`, `unknown`. All API responses include both the canonical `size` field and a `size_display` field with the abbreviated label (`S`, `M`, `L`, `XL`, `Jumbo`). The frontend uses `size_display` for rendering badges and charts. The mapping is defined once in the backend:

```json
{
  "small": "S",
  "medium": "M",
  "large": "L",
  "extra-large": "XL",
  "jumbo": "Jumbo",
  "unknown": "?"
}
```

#### Auth

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/auth/login` | User login | None |
| GET | `/api/auth/me` | Get current user | JWT |

**POST `/api/auth/login`**

Request:
```json
{
  "username": "admin",
  "password": "securepassword123"
}
```

Response (200):
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

Response (401):
```json
{
  "detail": "Invalid username or password"
}
```

#### Device / Heartbeat

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/devices/heartbeat` | Device heartbeat ping | Device Key |
| GET | `/api/devices` | List all devices + status | JWT |
| GET | `/api/devices/{id}` | Get device details | JWT |
| PUT | `/api/devices/{id}` | Update device config (cages, chickens) | JWT |

**POST `/api/devices/heartbeat`**

Request:
```json
{
  "device_id": "cam-001",
  "timestamp": "2026-03-24T10:30:00Z",
  "current_count": 5,
  "status": "ok"
}
```

Response (200):
```json
{
  "acknowledged": true
}
```

**PUT `/api/devices/{id}`**

Request:
```json
{
  "num_cages": 4,
  "num_chickens": 4
}
```

Response (200):
```json
{
  "id": 1,
  "device_id": "cam-001",
  "name": "Camera 1",
  "location": "Coop A - Layer Section",
  "num_cages": 4,
  "num_chickens": 4,
  "last_heartbeat": "2026-03-24T10:30:00Z",
  "is_online": true
}
```

#### Events (Edge Agent → Backend)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/events` | Submit detection event(s) | Device Key |

**POST `/api/events`**

Request:
```json
{
  "device_id": "cam-001",
  "timestamp": "2026-03-24T10:30:00Z",
  "total_count": 5,
  "new_eggs": [
    {
      "size": "medium",
      "confidence": 0.92,
      "bbox_area_normalized": 0.0028,
      "detected_at": "2026-03-24T10:30:00Z"
    },
    {
      "size": "large",
      "confidence": 0.87,
      "bbox_area_normalized": 0.0038,
      "detected_at": "2026-03-24T10:30:00Z"
    }
  ],
  "size_breakdown": {
    "small": 1,
    "medium": 2,
    "large": 1,
    "extra-large": 1,
    "jumbo": 0,
    "unknown": 0
  }
}
```

Response (201):
```json
{
  "accepted": true,
  "events_created": 2,
  "daily_total": 12
}
```

#### Dashboard Data

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/dashboard/summary` | Today's stats + metric cards | JWT |
| GET | `/api/dashboard/weekly?month=3&year=2026&week=4` | Weekly stats | JWT |
| GET | `/api/dashboard/monthly?month=3&year=2026` | Monthly stats | JWT |
| GET | `/api/dashboard/yearly?year=2026` | Yearly stats | JWT |
| GET | `/api/dashboard/daily-chart?from=2026-03-01&to=2026-03-24` | Daily production for chart | JWT |
| GET | `/api/dashboard/size-distribution?from=2026-03-01&to=2026-03-24` | Size distribution for chart | JWT |

**GET `/api/dashboard/summary`**

Response (200):
```json
{
  "today_eggs": 3,
  "all_time_eggs": 154,
  "best_day": {
    "date": "2026-02-27",
    "count": 7
  },
  "top_size": {
    "size": "medium",
    "count": 50
  },
  "device": {
    "id": 1,
    "name": "Camera 1",
    "location": "Coop A - Layer Section",
    "num_cages": 4,
    "num_chickens": 4,
    "today_count": 3,
    "is_online": true
  }
}
```

**GET `/api/dashboard/weekly?month=3&year=2026&week=4`**

Response (200):
```json
{
  "period": "Week 4 (22-28)",
  "month": "Mar",
  "year": 2026,
  "total_eggs": 7,
  "avg_per_day": 7.0
}
```

**GET `/api/dashboard/monthly?month=3&year=2026`**

Response (200):
```json
{
  "month": "March",
  "year": 2026,
  "total_eggs": 112,
  "avg_per_day": 5.1
}
```

**GET `/api/dashboard/yearly?year=2026`**

Response (200):
```json
{
  "year": 2026,
  "total_eggs": 154,
  "avg_per_day": 5.1
}
```

**GET `/api/dashboard/daily-chart?from=2026-03-01&to=2026-03-24`**

Response (200):
```json
{
  "data": [
    {"date": "2026-03-01", "count": 3},
    {"date": "2026-03-02", "count": 5},
    {"date": "2026-03-03", "count": 7},
    ...
  ]
}
```

**GET `/api/dashboard/size-distribution?from=2026-03-01&to=2026-03-24`**

Response (200):
```json
{
  "data": [
    {"size": "small", "display": "S", "count": 15},
    {"size": "medium", "display": "M", "count": 37},
    {"size": "large", "display": "L", "count": 24},
    {"size": "extra-large", "display": "XL", "count": 15},
    {"size": "jumbo", "display": "Jumbo", "count": 16}
  ]
}
```

#### History / Records

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/history?size=all&from=&to=&page=1&limit=50` | Paginated egg records | JWT |

**GET `/api/history?size=XL&from=2026-03-01&to=2026-03-22&page=1&limit=50`**

Response (200):
```json
{
  "total_records": 154,
  "page": 1,
  "limit": 50,
  "records": [
    {
      "id": 154,
      "date": "Sun, Mar 22, 2026",
      "size": "extra-large",
      "size_display": "XL",
      "detected_at": "Mar 22, 2026, 06:48 PM",
      "confidence": 0.91
    },
    {
      "id": 153,
      "date": "Sun, Mar 22, 2026",
      "size": "jumbo",
      "size_display": "Jumbo",
      "detected_at": "Mar 22, 2026, 05:11 PM",
      "confidence": 0.88
    }
  ]
}
```

#### Alerts

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/alerts?status=active&page=1&limit=20` | List alerts | JWT |
| PUT | `/api/alerts/{id}/dismiss` | Dismiss an alert | JWT |

**GET `/api/alerts`**

Response (200):
```json
{
  "alerts": [
    {
      "id": 5,
      "type": "device_offline",
      "severity": "warning",
      "message": "Camera 1 has not sent a heartbeat in 10 minutes",
      "created_at": "2026-03-24T10:45:00Z",
      "dismissed": false
    },
    {
      "id": 4,
      "type": "low_production",
      "severity": "info",
      "message": "Today's egg count (1) is below the daily average (5.1)",
      "created_at": "2026-03-24T18:00:00Z",
      "dismissed": false
    }
  ]
}
```

---

## 7. Database Design

### 7.1 Database Choice

**PostgreSQL on Railway** (managed). Railway provides a PostgreSQL instance with automatic backups, connection pooling, and zero-ops maintenance.

Connection string provided via `DATABASE_URL` environment variable.

### 7.2 Schema

#### Table: `users`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Auto-incrementing ID |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | Login username |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt hash |
| `display_name` | VARCHAR(100) | | Name shown in UI |
| `is_active` | BOOLEAN | DEFAULT TRUE | Account active flag |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Account creation time |

**Purpose:** Stores predefined user accounts. No signup — users are seeded via migration.

**Seed data (2 accounts):**
- `admin` / (hashed password)
- `viewer` / (hashed password)

#### Table: `devices`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Auto-incrementing ID |
| `device_id` | VARCHAR(50) | UNIQUE, NOT NULL | Unique device identifier (e.g., "cam-001") |
| `api_key` | VARCHAR(255) | UNIQUE, NOT NULL | Device authentication key |
| `name` | VARCHAR(100) | NOT NULL | Display name (e.g., "Camera 1") |
| `location` | VARCHAR(200) | | Location description (e.g., "Coop A - Layer Section") |
| `num_cages` | INTEGER | DEFAULT 1 | Number of cages monitored |
| `num_chickens` | INTEGER | DEFAULT 1 | Number of chickens in cages |
| `last_heartbeat` | TIMESTAMPTZ | | Last heartbeat timestamp |
| `is_active` | BOOLEAN | DEFAULT TRUE | Device active flag |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Device registration time |

**Purpose:** Stores device configuration and heartbeat status. `is_online` is computed: `last_heartbeat > NOW() - INTERVAL '5 minutes'`.

#### Table: `egg_detections`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Auto-incrementing ID |
| `device_id` | INTEGER | FK → devices.id, NOT NULL | Source device |
| `size` | VARCHAR(20) | NOT NULL | Size class: small, medium, large, extra-large, jumbo, unknown |
| `confidence` | FLOAT | | YOLO detection confidence |
| `bbox_area_normalized` | FLOAT | | Normalized bounding box area (for analysis) |
| `detected_at` | TIMESTAMPTZ | NOT NULL | When the egg was detected |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |

**Purpose:** One row per detected egg. This is the **primary fact table**. All aggregations (daily, weekly, monthly, yearly, size distribution) are computed from this table.

**Index:** `CREATE INDEX idx_detections_device_date ON egg_detections(device_id, detected_at);`

#### Table: `count_snapshots`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Auto-incrementing ID |
| `device_id` | INTEGER | FK → devices.id, NOT NULL | Source device |
| `total_count` | INTEGER | NOT NULL | Total eggs visible at capture time |
| `size_breakdown` | JSONB | | `{"small": 1, "medium": 2, ...}` |
| `captured_at` | TIMESTAMPTZ | NOT NULL | Capture timestamp |

**Purpose:** Stores each periodic snapshot from the edge agent for reconciliation and debugging. Not used for dashboard aggregations — those come from `egg_detections`.

#### Table: `alerts`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Auto-incrementing ID |
| `device_id` | INTEGER | FK → devices.id | Related device (nullable for system alerts) |
| `type` | VARCHAR(50) | NOT NULL | Alert type: `device_offline`, `low_production`, `uncertain_detection`, `missing_data` |
| `severity` | VARCHAR(20) | NOT NULL | `info`, `warning`, `critical` |
| `message` | TEXT | NOT NULL | Human-readable alert message |
| `is_dismissed` | BOOLEAN | DEFAULT FALSE | Whether user dismissed the alert |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Alert creation time |
| `dismissed_at` | TIMESTAMPTZ | | When alert was dismissed |

**Purpose:** Stores alert events for display on the dashboard.

### 7.3 Aggregation Queries

All aggregations are computed on-the-fly from `egg_detections`. For v1, this is fast enough — the table will have at most a few thousand rows per year for a single device.

**Daily total:**
```sql
SELECT DATE(detected_at AT TIME ZONE 'Asia/Manila') as date,
       COUNT(*) as total
FROM egg_detections
WHERE device_id = $1
  AND detected_at >= $2 AND detected_at < $3
GROUP BY DATE(detected_at AT TIME ZONE 'Asia/Manila')
ORDER BY date;
```

**Monthly total + average:**
```sql
SELECT COUNT(*) as total_eggs,
       ROUND(COUNT(*)::numeric / EXTRACT(DAY FROM $end_date - $start_date + INTERVAL '1 day'), 1) as avg_per_day
FROM egg_detections
WHERE device_id = $1
  AND detected_at >= $start_date AND detected_at < $end_date;
```

**Size distribution:**
```sql
SELECT size, COUNT(*) as count
FROM egg_detections
WHERE device_id = $1
  AND detected_at >= $start_date AND detected_at < $end_date
  AND size != 'unknown'
GROUP BY size;
```

**Best day:**
```sql
SELECT DATE(detected_at AT TIME ZONE 'Asia/Manila') as date,
       COUNT(*) as count
FROM egg_detections
WHERE device_id = $1
GROUP BY DATE(detected_at AT TIME ZONE 'Asia/Manila')
ORDER BY count DESC
LIMIT 1;
```

**Top size (most common):**
```sql
SELECT size, COUNT(*) as count
FROM egg_detections
WHERE device_id = $1 AND size != 'unknown'
GROUP BY size
ORDER BY count DESC
LIMIT 1;
```

### 7.4 Future Optimization

If `egg_detections` grows beyond 100K rows (unlikely for v1 with one device), add a materialized `daily_production` summary table populated by a nightly cron or trigger. Not needed for v1.

---

## 8. Frontend / Web App Plan

### 8.1 Stack

| Component | Choice | Reason |
|---|---|---|
| Framework | **React 18** + **Vite** | Fast builds, modern, Vercel-optimized |
| Styling | **TailwindCSS** | Utility-first, matches mockup style efficiently |
| Charts | **Recharts** | Simple, React-native charting library |
| HTTP Client | **Axios** | Interceptors for auth token injection |
| Routing | **React Router v6** | Standard React routing |
| State | **React Context** + hooks | Sufficient for v1, no Redux needed |
| Icons | **Lucide React** | Clean icon set matching mockup style |
| Date Handling | **date-fns** | Lightweight date formatting/manipulation |

### 8.2 Pages and Routes

| Route | Page | Description |
|---|---|---|
| `/login` | LoginPage | Authentication form |
| `/` | DashboardPage | Main dashboard (redirects to `/login` if unauthenticated) |
| `/history` | HistoryPage | Filterable egg records table |

**Note:** "Modify Camera" is a **modal dialog** on the Dashboard page, not a separate route.

### 8.3 Page Designs (Matching UI Mockups)

#### Login Page (`/login`)

Matches `login.png` exactly:

- **Background:** Light gray (`#F8FAFC`)
- **Centered card layout** with:
  - Orange egg logo (rounded square, `#F59E0B` background, white egg outline)
  - "EggSentry" heading (bold, `#1E293B`)
  - "USEP POULTRY" subtitle (muted blue-gray, `#94A3B8`)
  - "Egg Counter with Tracking System" (gray, `#64748B`)
  - White card with subtle shadow:
    - "Welcome Back" heading
    - "Sign in to access your egg production dashboard" subtitle
    - Username input with person icon
    - Password input with lock icon
    - Orange "Login →" button (full width, `#F59E0B`)
- **Behavior:** On submit, POST to `/api/auth/login`, store token, redirect to `/`.

#### Dashboard Page (`/`)

Matches `dashboard_1.png` and `dashboard_2.png`:

**Navigation Bar (persistent across all pages):**
- Left: Orange egg icon + "EggSentry" + "USEP POULTRY"
- Right: Dashboard (active state: orange pill), History, Modify Camera, Logout
- Active nav item has orange background pill with icon

**Dashboard Content (scrollable, top to bottom):**

1. **Page Header:**
   - "Dashboard" (bold `h1`)
   - "Egg production overview and analytics" (gray subtitle)

2. **Camera Card:**
   - Orange camera icon, "Camera 1", "Coop A - Layer Section"
   - Right side: "Cages: 4", "Chickens: 4", "Today: 0" (today count in orange)
   - Subtle orange left border accent

3. **Time Period Stats Row (3 cards):**
   - **Weekly Card** (blue calendar icon):
     - Month dropdown ("Mar") + Week dropdown ("Week 4 (22-28)")
     - Big number: total eggs, right side: avg/day in blue
   - **Monthly Card** (green calendar icon):
     - Month dropdown ("March") + Year dropdown ("2026")
     - Big number: total eggs, right side: avg/day in green
   - **Yearly Card** (purple calendar icon):
     - Year dropdown ("2026")
     - Big number: total eggs, right side: avg/day in purple

4. **Metric Cards Row (4 cards):**
   - **TODAY'S EGGS:** count + orange egg icon
   - **ALL TIME:** count + orange trend-up icon
   - **BEST DAY:** "Feb 27 (7)" + orange calendar icon
   - **TOP SIZE:** "M (50)" + orange bar-chart icon

5. **Charts Row (2 charts):**
   - **Daily Egg Production** (left):
     - Line chart with orange line and light orange area fill
     - X-axis: dates, Y-axis: egg count
     - Recharts `AreaChart` component
   - **Egg Size Distribution** (right):
     - Vertical bar chart with 5 bars (S, M, L, XL, Jumbo)
     - Colors: S=blue (`#3B82F6`), M=green (`#22C55E`), L=orange (`#F59E0B`), XL=purple (`#8B5CF6`), Jumbo=red (`#EF4444`)
     - Recharts `BarChart` component

#### History Page (`/history`)

Matches `history.png`:

1. **Page Header:**
   - "History" (bold `h1`)
   - "Browse all egg records with filters" (gray subtitle)

2. **Filter Section:**
   - "Filters" label with funnel icon + "N records" badge (right)
   - Three filter inputs in a row:
     - **Size:** dropdown ("All Sizes", S, M, L, XL, Jumbo, Unknown)
     - **From:** date input (`mm/dd/yyyy`)
     - **To:** date input (`mm/dd/yyyy`)

3. **Records Table:**
   - Column headers: DATE | SIZE | DATE & TIME
   - Each row:
     - Date: formatted as "Sun, Mar 22, 2026"
     - Size: colored badge (S=blue, M=green, L=orange, XL=purple, Jumbo=red)
     - Date & Time: "Mar 22, 2026, 06:48 PM"
   - Infinite scroll or pagination at bottom

#### Modify Camera Modal

Matches `modify_camera.png`:

- **Trigger:** Click "Modify Camera" in nav bar
- **Modal overlay:** semi-transparent dark background
- **Modal card:**
  - Orange camera icon + "Modify Camera" heading
  - "Camera 1 — Update cage and chicken count" subtitle
  - Close (X) button top-right
  - Two input fields side by side:
    - "Number of Cages" (numeric input)
    - "Number of Chickens" (numeric input)
  - "Cancel" button (outlined) + "Save Changes" button (orange filled)
- **Behavior:** PUT to `/api/devices/{id}` on save.

### 8.4 Component Structure

```
src/
  components/
    layout/
      Navbar.jsx           # Top navigation bar
      PageHeader.jsx       # "Dashboard" / "History" heading + subtitle
    dashboard/
      CameraCard.jsx       # Camera info card with cage/chicken/today stats
      PeriodCard.jsx       # Reusable weekly/monthly/yearly stat card
      MetricCard.jsx       # TODAY'S EGGS / ALL TIME / BEST DAY / TOP SIZE
      DailyChart.jsx       # Line/area chart for daily production
      SizeDistChart.jsx    # Bar chart for size distribution
    history/
      FilterBar.jsx        # Size dropdown + date range inputs
      RecordTable.jsx      # Egg records table with size badges
      SizeBadge.jsx        # Colored size badge component
    ModifyCameraModal.jsx  # Camera settings modal
    ProtectedRoute.jsx     # Auth guard wrapper
  pages/
    LoginPage.jsx
    DashboardPage.jsx
    HistoryPage.jsx
  hooks/
    useAuth.js             # Auth context + token management
    useDashboard.js        # Dashboard data fetching
    useHistory.js          # History data fetching with filters
  services/
    api.js                 # Axios instance with auth interceptor
    auth.js                # Login/logout API calls
    dashboard.js           # Dashboard API calls
    history.js             # History API calls
    devices.js             # Device API calls
  App.jsx                  # Router + AuthProvider
  main.jsx                 # Entry point
```

### 8.5 Color Palette (from mockups)

```
Primary Orange:    #F59E0B
Background:        #F8FAFC
Card Background:   #FFFFFF
Text Primary:      #1E293B
Text Secondary:    #64748B
Text Muted:        #94A3B8
Border:            #E2E8F0

Size Badge Colors:
  S (Small):       bg-blue-500     #3B82F6
  M (Medium):      bg-green-500    #22C55E
  L (Large):       bg-orange-400   #FB923C
  XL (Extra-Large): bg-purple-500  #8B5CF6
  Jumbo:           bg-red-500      #EF4444

Period Card Accents:
  Weekly:          Blue    #3B82F6
  Monthly:         Green   #22C55E
  Yearly:          Purple  #8B5CF6
```

---

## 9. Alerts and Business Logic

### 9.1 Alert Rules for v1

| Alert Type | Severity | Trigger Condition | Message Template |
|---|---|---|---|
| `device_offline` | warning | No heartbeat for 5 minutes | "Camera 1 has not sent a heartbeat in {minutes} minutes" |
| `low_production` | info | Daily count < 50% of 7-day rolling average by 6PM | "Today's egg count ({count}) is below the daily average ({avg})" |
| `uncertain_detection` | info | >3 `unknown` size classifications in 1 hour | "Multiple uncertain detections from Camera 1 in the last hour — check camera alignment" |
| `missing_data` | warning | No detection events for 6+ hours during daytime (6AM–6PM) | "No egg detections from Camera 1 in the last {hours} hours" |

### 9.2 Alert Evaluation

- **`device_offline`:** Checked by a background task (FastAPI `BackgroundTask` or a periodic task using `asyncio`) every 2 minutes. Queries `devices.last_heartbeat`.
- **`low_production`:** Evaluated once daily at 6PM (or on each dashboard load). Compares today's count against 7-day rolling average.
- **`uncertain_detection`:** Evaluated on each event ingestion. Counts `unknown` detections in the last hour.
- **`missing_data`:** Checked every 30 minutes by background task. Only triggers during configured daytime hours.

### 9.3 Alert Deduplication

- Each alert type + device combination has a **cooldown period** (default: 1 hour).
- If an alert of the same type for the same device was created within the cooldown window, do not create a duplicate.
- Stored as a simple check: `SELECT 1 FROM alerts WHERE type = $1 AND device_id = $2 AND created_at > NOW() - INTERVAL '1 hour'`.

### 9.4 Threshold Configuration

Alert thresholds are stored as environment variables for v1:

```
ALERT_HEARTBEAT_TIMEOUT_MINUTES=5
ALERT_LOW_PRODUCTION_THRESHOLD=0.5    # fraction of 7-day avg
ALERT_UNCERTAIN_THRESHOLD=3           # unknown detections per hour
ALERT_MISSING_DATA_HOURS=6
ALERT_COOLDOWN_MINUTES=60
```

---

## 10. Deployment Plan

### 10.1 Overview

| Component | Platform | Method |
|---|---|---|
| Frontend (React) | **Vercel** | Git push → auto-deploy |
| Backend (FastAPI) | **Railway** | Git push → auto-deploy |
| Database (PostgreSQL) | **Railway** | Managed PostgreSQL addon |
| Edge Agent | **Raspberry Pi 5** | SSH deploy, systemd service |
| Dev/Test | **PC** | Local Python + npm dev servers |

### 10.2 Frontend Deployment (Vercel)

1. Push `frontend/` directory to GitHub.
2. Connect repo to Vercel, set root directory to `frontend/`.
3. Vercel auto-detects Vite, runs `npm run build`, deploys to CDN.
4. Set environment variable: `VITE_API_URL=https://your-backend.railway.app`.
5. Automatic HTTPS, custom domain optional.

**`frontend/vercel.json`:**
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### 10.3 Backend Deployment (Railway)

1. Push `backend/` directory to GitHub.
2. Connect repo to Railway, set root directory to `backend/`.
3. Railway detects Python, uses `requirements.txt` or `Dockerfile`.
4. Add PostgreSQL service in the same Railway project.
5. Railway auto-injects `DATABASE_URL` environment variable.

**Additional Railway environment variables:**
```
SECRET_KEY=<generate-a-64-char-random-string>
ALLOWED_ORIGINS=https://your-frontend.vercel.app
DEFAULT_ADMIN_PASSWORD=<secure-password>
DEFAULT_VIEWER_PASSWORD=<secure-password>
DEVICE_API_KEY=<generate-a-random-key>
```

**`backend/Procfile`:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**`backend/railway.toml`:**
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

### 10.4 Edge Device Deployment (Raspberry Pi 5)

1. **OS:** Raspberry Pi OS (64-bit, Bookworm). Install headless (no desktop needed).
2. **Python:** System Python 3.11+ or install via `apt`.
3. **Dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv libgl1-mesa-glx libglib2.0-0
   ```
4. **Clone repo (edge agent only):**
   ```bash
   git clone <repo-url> ~/egg-sentry
   cd ~/egg-sentry/edge
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
5. **Configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with:
   # API_URL=https://your-backend.railway.app
   # DEVICE_ID=cam-001
   # DEVICE_API_KEY=<key-from-railway-env>
   # CAPTURE_INTERVAL=120
   # CONFIDENCE_THRESHOLD=0.5
   # CAMERA_SOURCE=0
   ```
6. **Systemd service:**
   ```ini
   # /etc/systemd/system/egg-sentry.service
   [Unit]
   Description=EggSentry Edge Agent
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/egg-sentry/edge
   ExecStart=/home/pi/egg-sentry/edge/.venv/bin/python agent.py
   Restart=always
   RestartSec=30
   EnvironmentFile=/home/pi/egg-sentry/edge/.env

   [Install]
   WantedBy=multi-user.target
   ```
7. **Enable and start:**
   ```bash
   sudo systemctl enable egg-sentry
   sudo systemctl start egg-sentry
   sudo systemctl status egg-sentry
   ```

### 10.5 Development / PC Setup

For development and testing on a PC:

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # edit with local DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
cp .env.example .env        # VITE_API_URL=http://localhost:8000
npm run dev                 # runs on :5173

# Edge Agent (video test mode)
cd edge
python agent.py --source ../vids/egg-counter-test-vid.mp4 --interval 5 --display
```

---

## 11. Development Roadmap

### Phase 1: Foundation (Edge Agent Core)

**Goal:** Edge agent captures frames, runs YOLO, classifies sizes, outputs results locally.

- [ ] **1.1** Set up `edge/` project structure with `pyproject.toml` or `requirements.txt`.
- [ ] **1.2** Implement `capture.py` — camera open/capture/close logic with warm-up sequence.
- [ ] **1.3** Implement `detector.py` — YOLO model loading and single-frame inference (wraps `model.predict()`).
- [ ] **1.4** Implement `size_classifier.py` — rules-based bounding-box area → size class mapping with configurable thresholds. Include placeholder thresholds in `edge/config.json` (values from Section 4.4) for development/testing — these will be recalibrated with real camera data in Phase 7.
- [ ] **1.5** Implement `stabilizer.py` — rolling window count stabilization (port from existing `egg_sentry.py` logic).
- [ ] **1.6** Implement `agent.py` — main loop: sleep → capture → infer → classify → stabilize → log to console.
- [ ] **1.7** Add video test mode — accept `--source path/to/video.mp4` with frame skipping for simulated periodic capture.
- [ ] **1.8** Add `--display` flag for OpenCV window with annotated detections (for development/debugging).
- [ ] **1.9** Test with `vids/egg-counter-test-vid.mp4` — verify count stability and size classification output.
- [ ] **1.10** Write unit tests for `size_classifier.py` and `stabilizer.py`.

### Phase 2: Backend API

**Goal:** FastAPI backend with auth, event ingestion, and dashboard endpoints.

- [ ] **2.1** Set up `backend/` project structure with FastAPI, SQLAlchemy, Alembic.
- [ ] **2.2** Define SQLAlchemy models for all tables (`users`, `devices`, `egg_detections`, `count_snapshots`, `alerts`).
- [ ] **2.3** Create Alembic migration for initial schema.
- [ ] **2.4** Implement seed script for default users and device.
- [ ] **2.5** Implement auth module — login endpoint, JWT token generation/validation, password hashing.
- [ ] **2.6** Implement device auth — API key validation middleware.
- [ ] **2.7** Implement event ingestion endpoint — `POST /api/events`.
- [ ] **2.8** Implement heartbeat endpoint — `POST /api/devices/heartbeat`.
- [ ] **2.9** Implement dashboard endpoints — summary, weekly, monthly, yearly, daily-chart, size-distribution.
- [ ] **2.10** Implement history endpoint — paginated, filterable egg records.
- [ ] **2.11** Implement device endpoints — list, get, update (for Modify Camera).
- [ ] **2.12** Implement alert endpoints — list, dismiss.
- [ ] **2.13** Write API tests for all endpoints.
- [ ] **2.14** Test with sample data — seed script or manual POST to verify aggregation queries.

### Phase 3: Edge-Backend Integration

**Goal:** Edge agent successfully POSTs events and heartbeats to the backend.

- [ ] **3.1** Implement `reporter.py` in edge agent — HTTP client for event submission and heartbeats.
- [ ] **3.2** Add device API key auth to the reporter.
- [ ] **3.3** Implement event emission logic — detect count changes, POST new eggs.
- [ ] **3.4** Implement heartbeat loop — send heartbeat every 60 seconds.
- [ ] **3.5** Add retry logic with exponential backoff for failed HTTP requests.
- [ ] **3.6** Add offline queue — buffer events locally if backend is unreachable, flush when connection resumes.
- [ ] **3.7** Integration test: run edge agent with test video against local backend, verify events appear in database.

### Phase 4: Frontend Dashboard

**Goal:** React dashboard matching UI mockups, connected to backend API.

- [ ] **4.1** Set up `frontend/` with Vite + React + TailwindCSS + React Router.
- [ ] **4.2** Implement auth context, API service, and Axios interceptor.
- [ ] **4.3** Build LoginPage matching `login.png` mockup.
- [ ] **4.4** Build Navbar component with routing and active state.
- [ ] **4.5** Build DashboardPage — CameraCard component.
- [ ] **4.6** Build DashboardPage — PeriodCard components (weekly, monthly, yearly) with dropdowns.
- [ ] **4.7** Build DashboardPage — MetricCard components (today, all-time, best day, top size).
- [ ] **4.8** Build DashboardPage — DailyChart (Recharts AreaChart).
- [ ] **4.9** Build DashboardPage — SizeDistChart (Recharts BarChart with per-bar colors).
- [ ] **4.10** Build HistoryPage — FilterBar + RecordTable with SizeBadge.
- [ ] **4.11** Build ModifyCameraModal dialog.
- [ ] **4.12** Implement ProtectedRoute and logout.
- [ ] **4.13** Responsive design pass — ensure works on mobile and desktop.

### Phase 5: Alerts Engine

**Goal:** Backend generates alerts, frontend displays them.

- [ ] **5.1** Implement alert evaluation logic in backend (background task).
- [ ] **5.2** Implement device offline detection.
- [ ] **5.3** Implement low production alert.
- [ ] **5.4** Implement uncertain detection alert.
- [ ] **5.5** Implement missing data alert.
- [ ] **5.6** Add alert display to frontend dashboard (alert banner or notification area).

### Phase 6: Deployment

**Goal:** System running in production.

- [ ] **6.1** Deploy backend to Railway with PostgreSQL.
- [ ] **6.2** Run Alembic migrations on Railway.
- [ ] **6.3** Seed production users and device.
- [ ] **6.4** Deploy frontend to Vercel.
- [ ] **6.5** Configure CORS and environment variables.
- [ ] **6.6** Deploy edge agent to Raspberry Pi 5.
- [ ] **6.7** Calibrate size thresholds with real camera data.
- [ ] **6.8** End-to-end production smoke test.

### Phase 7: Size Threshold Calibration

**Goal:** Accurate size classification for the production camera setup.

- [ ] **7.1** Capture 50–100 frames with eggs of known sizes.
- [ ] **7.2** Run YOLO inference, extract bounding box areas.
- [ ] **7.3** Plot area distribution per size class.
- [ ] **7.4** Set threshold values in `edge/config.json`.
- [ ] **7.5** Validate classification accuracy on a held-out set.

---

## 12. Risks and Mitigation

| # | Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | **Unstable lighting** — sunrise/sunset, shadows, artificial light changes affect detection accuracy | Medium | High | Use auto-exposure camera settings. Add brightness normalization preprocessing. Capture during consistent lighting. Include varied-lighting images in training data. |
| 2 | **Camera angle drift** — bumped camera invalidates size thresholds | High | Medium | Mount camera firmly with bracket/clamp. Add a visual marker (sticker) in frame corner to detect if perspective changed. Document exact mounting position for recalibration. |
| 3 | **Occlusion** — eggs blocked by hens, feathers, or other eggs | Medium | Medium | Accept that count may temporarily drop. Stabilization window smooths this. Hens typically leave the nest quickly. Count increases are reported; temporary decreases are not. |
| 4 | **False counts** — non-egg objects detected as eggs | Medium | Low | Train model with negative examples (empty cage, feathers, feed). Confidence threshold of 0.5 filters weak detections. Aspect ratio sanity check filters non-egg shapes. |
| 5 | **Inaccurate size classification** — rules-based approach has limited accuracy | Low | High | Set explicit accuracy expectations (~70-80%). Use `unknown` class liberally. Communicate this is approximate. Calibrate thresholds per camera. v2 can use a trained size model. |
| 6 | **Raspberry Pi performance** — YOLO inference too slow or Pi overheats | Medium | Low | YOLOv8 Nano is ~5MB and runs in <300ms on Pi5 CPU. With 2-min intervals, CPU is idle 99.9% of the time. If issues arise, increase interval or export to ONNX. |
| 7 | **Network connectivity** — Pi loses internet, events can't reach backend | Medium | Medium | Implement offline event queue in edge agent. Buffer events to local SQLite or JSON file. Flush to backend when connection resumes. Heartbeat failure triggers device_offline alert. |
| 8 | **Camera failure** — USB camera disconnects or CSI ribbon loosens | Medium | Low | Edge agent detects `cap.read()` failure, logs error, retries every 30 seconds. Heartbeat continues so backend knows device is alive but camera is down. |
| 9 | **Database growth** — egg_detections table grows unbounded | Low | Low | With 1 device producing ~5-10 eggs/day, that's ~3,650 rows/year. PostgreSQL handles millions of rows easily. No action needed for v1. v2 can add archiving. |
| 10 | **Security — exposed API** | Medium | Medium | JWT auth on dashboard endpoints. Device API key on edge endpoints. HTTPS enforced by Railway/Vercel. Rate limiting on login endpoint. Passwords bcrypt-hashed. |

---

## 13. Testing Strategy

### 13.1 Unit Tests

| Component | What to Test | Tool |
|---|---|---|
| `size_classifier.py` | Threshold boundaries, edge cases, unknown class, aspect ratio filter | pytest |
| `stabilizer.py` | Rolling window mode calculation, empty history, tie-breaking | pytest |
| `detector.py` | Model loads, detections returned in expected format | pytest (with fixture image) |
| `reporter.py` | Event payload construction, retry logic (mock HTTP) | pytest + httpx mock |
| Backend auth | Password hashing, JWT generation/validation, expiry | pytest |
| Backend events | Event ingestion, daily count increment, size storage | pytest + test DB |
| Backend dashboard | Aggregation queries, date range handling, empty data | pytest + test DB |

### 13.2 Integration Tests

| Test | Description |
|---|---|
| **Edge → Backend event flow** | Run edge agent with test video and `--interval 5` against local backend. Verify events appear in database with correct counts and sizes. |
| **Auth flow** | Login → get token → access protected endpoint → logout → verify token rejected. |
| **Dashboard data accuracy** | Seed known events, verify dashboard endpoints return correct aggregations. |
| **Device heartbeat** | Send heartbeats, verify device shows online. Stop heartbeats, verify device shows offline after timeout. |

### 13.3 Video-Based Validation (Offline Testing)

1. **Prepare test video** — use `vids/egg-counter-test-vid.mp4` or record new footage.
2. **Run edge agent in video mode:**
   ```bash
   python agent.py --source ../vids/egg-counter-test-vid.mp4 --interval 5 --display
   ```
3. **Manually count eggs** in the video at each sampled frame.
4. **Compare** agent's detected count vs. manual count.
5. **Compute metrics:**
   - Count accuracy: `correct_frames / total_frames`
   - Size classification accuracy: compare agent's size assignments to manual labels.
6. **Target for v1:** >90% count accuracy, >70% size classification accuracy.

### 13.4 Field Testing

1. **Deploy to Pi** with real camera pointed at the cage.
2. **Run for 24 hours** with logging enabled.
3. **Compare** daily total from dashboard vs. manual egg count.
4. **Check** for false positives (phantom eggs) and false negatives (missed eggs).
5. **Verify** heartbeat and offline detection.
6. **Test alert triggering** — unplug camera, verify `device_offline` alert.

### 13.5 Frontend Testing

| Test | Method |
|---|---|
| Login flow | Manual + Playwright E2E test |
| Dashboard renders with data | Mock API responses, verify components render |
| History filtering | Test with different filter combinations |
| Modify Camera modal | Test open/close, save, cancel |
| Auth guard | Unauthenticated access redirects to login |
| Responsive layout | Manual check on mobile viewport |

### 13.6 API Correctness

- Use **FastAPI TestClient** for all endpoint tests.
- Create a `tests/conftest.py` with:
  - Test database (SQLite in-memory or test PostgreSQL).
  - Fixture to seed test users, devices, and sample detection data.
  - Auth token fixture for protected endpoint tests.

---

## 14. Suggested Folder / Project Structure

```
egg-sentry/
│
├── edge/                              # Edge agent (runs on Pi / PC)
│   ├── agent.py                       # Main entry point — capture-infer-report loop
│   ├── capture.py                     # Camera open/capture/close with warm-up
│   ├── detector.py                    # YOLO model wrapper — load + predict
│   ├── size_classifier.py             # Rules-based bounding box → size class
│   ├── stabilizer.py                  # Rolling window count stabilization
│   ├── reporter.py                    # HTTP client — POST events + heartbeats
│   ├── config.py                      # Load env vars and config.json
│   ├── config.json                    # Size thresholds, capture interval, etc.
│   ├── requirements.txt              # Edge-specific Python deps
│   ├── .env.example                   # Template for environment variables
│   └── tests/
│       ├── test_size_classifier.py
│       ├── test_stabilizer.py
│       ├── test_detector.py
│       └── test_reporter.py
│
├── backend/                           # FastAPI backend (deploys to Railway)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, CORS, lifespan
│   │   ├── config.py                  # Settings from env vars
│   │   ├── database.py                # SQLAlchemy engine + session
│   │   ├── models.py                  # SQLAlchemy ORM models
│   │   ├── schemas.py                 # Pydantic request/response schemas
│   │   ├── auth.py                    # JWT + password utilities
│   │   ├── dependencies.py            # Auth dependency injectors
│   │   ├── seed.py                    # Seed default users + device
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py                # POST /api/auth/login, GET /api/auth/me
│   │       ├── events.py              # POST /api/events
│   │       ├── devices.py             # GET/PUT /api/devices, POST /api/devices/heartbeat
│   │       ├── dashboard.py           # GET /api/dashboard/*
│   │       ├── history.py             # GET /api/history
│   │       └── alerts.py              # GET /api/alerts, PUT /api/alerts/{id}/dismiss
│   ├── alembic.ini                    # Alembic configuration (lives at backend root)
│   ├── alembic/                       # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── tests/
│   │   ├── conftest.py                # Test DB, fixtures, auth helpers
│   │   ├── test_auth.py
│   │   ├── test_events.py
│   │   ├── test_dashboard.py
│   │   ├── test_history.py
│   │   ├── test_devices.py
│   │   └── test_alerts.py
│   ├── requirements.txt
│   ├── Procfile
│   ├── railway.toml
│   └── .env.example
│
├── frontend/                          # React dashboard (deploys to Vercel)
│   ├── public/
│   │   └── egg-logo.svg               # EggSentry logo
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Navbar.jsx
│   │   │   │   └── PageHeader.jsx
│   │   │   ├── dashboard/
│   │   │   │   ├── CameraCard.jsx
│   │   │   │   ├── PeriodCard.jsx
│   │   │   │   ├── MetricCard.jsx
│   │   │   │   ├── DailyChart.jsx
│   │   │   │   └── SizeDistChart.jsx
│   │   │   ├── history/
│   │   │   │   ├── FilterBar.jsx
│   │   │   │   ├── RecordTable.jsx
│   │   │   │   └── SizeBadge.jsx
│   │   │   ├── ModifyCameraModal.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   └── HistoryPage.jsx
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   ├── useDashboard.js
│   │   │   └── useHistory.js
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── auth.js
│   │   │   ├── dashboard.js
│   │   │   ├── history.js
│   │   │   └── devices.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css                  # Tailwind imports
│   ├── tailwind.config.js
│   ├── vite.config.js
│   ├── vercel.json
│   ├── package.json
│   └── .env.example
│
├── models/                            # YOLO model files
│   └── counter-yolo26n.pt             # Trained egg detection model
│
├── vids/                              # Test videos
│   └── egg-counter-test-vid.mp4       # Test footage for pipeline validation
│
├── ui_mockup/                         # UI design reference
│   ├── login.png
│   ├── dashboard_1.png
│   ├── dashboard_2.png
│   ├── history.png
│   └── modify_camera.png
│
├── egg_sentry.py                      # Original CLI tool (kept for reference/standalone use)
├── requirements.txt                   # Original requirements (kept for reference)
├── Implementation_Plan.md             # This document
└── .gitignore
```

---

## 15. Recommended Defaults for v1

| Setting | Default Value | Rationale |
|---|---|---|
| Capture interval | **120 seconds** (2 minutes) | Balanced between responsiveness and resource usage. Eggs don't move. |
| Confidence threshold | **0.5** | Filters weak detections. Can be tuned per deployment. |
| Stabilization window | **3 captures** | Requires consensus across 3 frames (~6 min) to confirm count change. |
| YOLO model | **counter-yolo26n.pt** (Nano, .pt) | Already trained, 5MB, fast on Pi5 CPU. |
| YOLO runtime | **Ultralytics (PyTorch)** | Simplest deployment, works on both PC and Pi5. |
| Size classes | **small, medium, large, extra-large, jumbo, unknown** | 5 real classes + unknown for uncertain detections. |
| Size classification method | **Rules-based bounding box area** | No second model needed. Calibrate thresholds per camera. |
| Backend framework | **FastAPI** | Fast, async, auto-docs, Pydantic validation. |
| Database | **PostgreSQL** (Railway managed) | Reliable, zero-ops on Railway. |
| Frontend framework | **React 18 + Vite + TailwindCSS** | Fast builds, utility CSS, Vercel-optimized. |
| Charts library | **Recharts** | Simple, React-native, sufficient for line + bar charts. |
| Auth (users) | **JWT, 24h expiry** | Stateless, simple. Two predefined accounts. |
| Auth (device) | **Static API key** | Simpler than JWT for always-on devices. |
| User accounts | **2** (admin, viewer) | Easily extensible — add rows to `users` table. |
| Devices | **1** (cam-001, "Camera 1", "Coop A - Layer Section") | Easily extensible — add rows to `devices` table. |
| Frontend deployment | **Vercel** | Zero-config, CDN, automatic HTTPS. |
| Backend deployment | **Railway** | Git-push deploy, managed Postgres, auto-HTTPS. |
| Edge deployment | **systemd on Pi5** | Standard Linux service management. |
| Heartbeat interval | **60 seconds** | Frequent enough for responsive offline detection. |
| Device offline threshold | **5 minutes** | No heartbeat for 5 min = offline. |
| Camera warm-up | **0.5s delay + discard first frame** | Allows auto-exposure to settle. |
| NMS IoU threshold | **0.5** | Standard YOLO default for suppressing duplicate boxes. |
| ROI | **Full frame** (single fixed ROI) | No cropping for v1. Camera should frame the cage area. |

---

## Assumptions

1. **One camera, one device, one cage area.** The system is designed for a single camera monitoring a single egg-laying area.
2. **Eggs are stationary after being laid.** No egg tracking across frames is required.
3. **Fixed camera position.** Size thresholds are calibrated for one camera distance/angle and are not transferable.
4. **Internet connectivity on Pi.** The edge agent needs network access to POST events to Railway. Brief outages are handled by offline queuing.
5. **Eggs are individually distinguishable.** No severe overlapping or stacking expected in cage-based laying.
6. **Daylight or consistent artificial lighting.** The YOLO model was trained under specific lighting; extreme lighting changes will reduce accuracy.
7. **Low volume.** At most ~10 eggs per day from one device. Dashboard aggregations are computed on-the-fly without materialized views.
8. **Two users are sufficient.** No role-based access control — both accounts see the same dashboard.
9. **The existing `counter-yolo26n.pt` model is functional** and detects eggs with reasonable accuracy. If not, retraining is needed before Phase 1 can complete.
10. **Raspberry Pi 5 has at least 4GB RAM.** YOLOv8 Nano + OpenCV runs comfortably in ~500MB.

---

## Out of Scope for v1

- **Multi-camera support** — the schema supports it, but the UI and edge agent assume one device.
- **Real-time video streaming** — no live video feed on the dashboard.
- **Egg tracking across frames** — not needed since eggs are stationary.
- **Weight-based grading** — no hardware scales; size is visual approximation only.
- **User signup / self-registration** — admin-seeded accounts only.
- **Role-based access control** — both users have identical permissions.
- **Mobile app** — responsive web app only, no native iOS/Android.
- **Notifications** — no push notifications, email, or SMS alerts. Alerts are dashboard-only.
- **Image storage** — captured frames are not stored in production. Only metadata is stored.
- **Model retraining pipeline** — no MLOps; model is trained offline and deployed as a static file.
- **Multi-language / i18n** — English only.
- **Egg removal detection** — if eggs are collected and count drops, no event is emitted. The daily total comes from accumulated detections, not live count.
- **Historical image review** — no ability to review past captured frames.
- **Rate limiting / API throttling** — not needed for a single-device system.

---

## Future v2 Upgrades

1. **ONNX or NCNN runtime** — export model for 30-50% faster inference on Pi. Useful if capture interval decreases.
2. **Trained size classification model** — replace rules-based classifier with a YOLO model trained on size-labeled data for better accuracy.
3. **Multi-camera support** — add camera selector to dashboard, support multiple devices per coop.
4. **Push notifications** — email or Telegram alerts for critical events (device offline, anomalous production).
5. **Live camera preview** — optional MJPEG stream endpoint on the edge agent for remote camera view.
6. **Image storage** — optionally store annotated frames in S3/R2 for debugging and audit.
7. **Egg collection tracking** — detect when eggs are removed (count decreases) and track collections separately.
8. **Analytics enhancements** — production trends, feed-to-egg ratio, seasonal patterns.
9. **Role-based access** — admin vs. viewer permissions with different dashboard capabilities.
10. **Automatic threshold calibration** — calibration wizard in the web app that guides the user through threshold setup.
11. **Offline-first edge agent** — full SQLite database on Pi for indefinite offline operation.
12. **Docker deployment** — containerize backend and edge agent for easier deployment.
