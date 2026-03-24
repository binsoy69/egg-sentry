# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- Python 3.x - All application logic and entry point at `egg_sentry.py`

## Runtime

**Environment:**
- Python interpreter (CPython)

**Package Manager:**
- pip - Python package management
- Lockfile: `requirements.txt` present (minimal, no lock file with pinned versions)

## Frameworks

**Core:**
- Ultralytics YOLO 8.x - Object detection and tracking framework for egg detection and size classification

**Vision/Video:**
- OpenCV (cv2) - Video capture, frame processing, visualization (bounding boxes, overlays)
- NumPy - Numerical operations and array handling for frame data

**Utilities:**
- argparse - Standard library for command-line argument parsing
- collections (Counter, deque) - Built-in Python utilities for counting and sliding window operations
- pathlib (Path) - File path handling (standard library)
- time - Performance monitoring and FPS calculation (standard library)
- sys - System operations like exit (standard library)

## Key Dependencies

**Critical:**
- `ultralytics` - YOLO8 model framework for detecting and classifying eggs by size
  - Provides `.track()` for persistent object tracking across frames
  - Provides `.names` for class label mapping
- `opencv-python` - Core video I/O and frame rendering capabilities
- `numpy` - Required by OpenCV and YOLO for array operations

## Configuration

**Environment:**
- No environment variables detected
- Command-line arguments control runtime behavior (mode, source, confidence threshold)
- Configuration is argument-driven via `argparse`

**Build:**
- No build system detected (single-file Python application)
- Runs directly with `python egg_sentry.py`

## Platform Requirements

**Development:**
- Python 3.7+ (based on use of f-strings, pathlib, and type hints)
- OpenCV system dependencies (may require opencv-contrib-python on some systems)

**Production:**
- System with video input source (webcam or video file)
- YOLO model files must exist at:
  - `models/counter-yolo26n.pt` - For counting mode
  - `models/size-yolo26n.pt` - For size classification mode
- GPU optional but recommended for real-time inference (YOLO will auto-detect CUDA)

## Model Files

**Pre-trained Models:**
- `models/counter-yolo26n.pt` (5.3 MB) - Counts eggs only
- `models/size-yolo26n.pt` (5.4 MB) - Classifies eggs into size categories: small, medium, large, extra-large, jumbo

---

*Stack analysis: 2026-03-24*
