# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**Machine Learning Models:**
- Ultralytics YOLO - Pre-trained neural networks for object detection
  - SDK/Client: `ultralytics` Python package
  - Models: Downloaded pre-trained `.pt` files (counter-yolo26n, size-yolo26n)
  - Auth: No authentication required

## Data Storage

**Databases:**
- None detected - No persistent database integration

**File Storage:**
- Local filesystem only
  - Model files: `models/` directory
  - Test videos: `vids/` directory
  - Input: Video files or camera device

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- None - No authentication system implemented

## Monitoring & Observability

**Error Tracking:**
- None detected - No error tracking service integrated

**Logs:**
- Console output only (`print()` statements for errors and status messages)
- No logging framework (no `logging` module or external service)

## Video I/O

**Input Sources:**
- Webcam/camera device (index 0 or other via `cv2.VideoCapture(int)`)
- Video files (MP4 and other formats supported by OpenCV via file path to `cv2.VideoCapture(str)`)

**Output:**
- Display window only (`cv2.imshow()`)
- No recording or export to file

## CI/CD & Deployment

**Hosting:**
- Not deployed - Standalone desktop/local application

**CI Pipeline:**
- None detected

**Version Control:**
- Git repository present (`.git/` directory)

## Environment Configuration

**Required files/directories:**
- `models/counter-yolo26n.pt` - Must exist (application exits with error if missing)
- `models/size-yolo26n.pt` - Must exist (application exits with error if missing)

**Secrets location:**
- No secrets used

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Hardware Dependencies

**Webcam/Camera:**
- Optional - Can use webcam at index 0 (default) or other indices
- Fallback: Video file input instead of camera

**Display:**
- Requires X11 or equivalent display server for `cv2.namedWindow()`

---

*Integration audit: 2026-03-24*
