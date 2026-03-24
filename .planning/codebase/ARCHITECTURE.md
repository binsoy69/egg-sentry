# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Single-module procedural application with clear separation of concerns through functional decomposition.

**Key Characteristics:**
- Command-line driven entry point with argument parsing
- Real-time video processing pipeline (capture → inference → visualization)
- YOLO model-based object detection with optional tracking
- Frame-level stabilization using rolling window mode detection
- Dual-mode operation (count-only or count+size-classify)

## Layers

**Entry Point & CLI:**
- Purpose: Parse arguments and orchestrate application flow
- Location: `egg_sentry.py` (lines 249-255: `main()` function)
- Contains: Argument parser definition, main execution flow
- Depends on: `run()` function, argument parsing utilities
- Used by: Direct script execution

**Model Management:**
- Purpose: Load and manage YOLO detection models
- Location: `egg_sentry.py` (lines 11-23: constants, lines 53-59: `load_model()`)
- Contains: Model path resolution, model loading with error handling
- Depends on: Ultralytics YOLO library, filesystem paths
- Used by: `run()` function

**Video Source Resolution:**
- Purpose: Validate and resolve video input (camera index or file path)
- Location: `egg_sentry.py` (lines 62-70: `resolve_source()`)
- Contains: Camera/file detection, path validation
- Depends on: Filesystem operations
- Used by: `run()` function

**Inference & Detection:**
- Purpose: Run YOLO inference with tracking on video frames
- Location: `egg_sentry.py` (lines 175-246: `run()` function, line 213 inference call)
- Contains: Video capture loop, frame inference, tracking persistence
- Depends on: YOLO model, OpenCV for video capture
- Used by: Visualization layer

**Counting & Classification:**
- Purpose: Extract and categorize detections (count or size-based)
- Location: `egg_sentry.py` (lines 97-143: `draw_detections()`)
- Contains: Bounding box extraction, class label resolution, count aggregation
- Depends on: YOLO results format
- Used by: Stabilization layer

**Stabilization:**
- Purpose: Reduce jitter in counts using statistical mode across rolling window
- Location: `egg_sentry.py` (lines 73-94: `stabilize_count()`, `stabilize_size_counts()`)
- Contains: Counter-based mode calculation, per-size aggregation
- Depends on: Collections library (Counter, deque)
- Used by: Visualization layer

**Visualization:**
- Purpose: Render detections and metrics to frame
- Location: `egg_sentry.py` (lines 97-172: `draw_detections()`, `draw_overlay()`)
- Contains: Bounding box drawing, color mapping, HUD text rendering, transparency effects
- Depends on: OpenCV drawing primitives
- Used by: `run()` function

## Data Flow

**Real-time Detection Pipeline:**

1. **Input Stage** - `run()` opens video source (camera or file) via OpenCV
2. **Inference Stage** - Each frame passed to `model.track()` for detection and tracking
3. **Detection Extraction** - `draw_detections()` processes YOLO results into counts and labels
4. **Aggregation** - Raw per-frame counts stored in rolling deque (STABLE_WINDOW=15 frames)
5. **Stabilization** - `stabilize_count()` / `stabilize_size_counts()` compute mode of recent frames
6. **Rendering** - `draw_overlay()` renders stabilized counts + FPS to frame
7. **Display** - Frame shown via OpenCV window, waits for user input (q to quit, m to toggle mode)
8. **Loop Control** - Repeats from Inference Stage for next frame (or resets video if file)

**State Management:**
- Frame-level: Raw detection results from YOLO model
- Multi-frame: `count_history` deque (total eggs), `size_history` deque (per-size breakdown)
- Session: Current mode (count/size), confidence threshold, FPS calculation
- Cleared on: Mode toggle, video restart

## Key Abstractions

**YOLO Model Abstraction:**
- Purpose: Isolate model loading logic from main loop
- Examples: `load_model()` function (line 53-59)
- Pattern: Conditional loading based on mode; early exit on missing model

**Stabilization Abstraction:**
- Purpose: Encapsulate rolling-window mode detection
- Examples: `stabilize_count()` (line 73-78), `stabilize_size_counts()` (line 81-94)
- Pattern: Counter-based frequency analysis on deque history

**Size Classification Abstraction:**
- Purpose: Map YOLO class labels to size categories with consistent colors
- Examples: `SIZE_COLORS` dict (line 16-22), mode-conditional logic in `draw_detections()`
- Pattern: Dictionary lookup with fallback color

**Detection Drawing Abstraction:**
- Purpose: Separate detection visualization from counting logic
- Examples: `draw_detections()` function (line 97-143)
- Pattern: Returns both visual output (drawn frame) and data output (counts)

## Entry Points

**Command-line Entry:**
- Location: `egg_sentry.py` lines 254-255 (`if __name__ == "__main__"`)
- Triggers: `python egg_sentry.py [--mode count|size] [--source 0|path] [--conf 0.5]`
- Responsibilities: Parse arguments, validate inputs, launch `main()`

**Main Function:**
- Location: `egg_sentry.py` lines 249-251
- Triggers: `if __name__ == "__main__"` block
- Responsibilities: Call `parse_args()`, pass to `run()`

**Run Function:**
- Location: `egg_sentry.py` lines 175-246
- Triggers: Called by `main()`
- Responsibilities: Initialize video source, model, window; execute main inference loop

## Error Handling

**Strategy:** Early validation with immediate exit; graceful degradation during runtime.

**Patterns:**

1. **Model Loading:** Check file existence before loading (line 55-57)
   ```python
   if not model_path.exists():
       print(f"Error: Model not found at {model_path}")
       sys.exit(1)
   ```

2. **Video Source:** Validate path or camera index before opening (line 62-70)
   ```python
   if source.isdigit():
       return int(source)
   path = Path(source)
   if not path.exists():
       print(f"Error: Video file not found: {source}")
       sys.exit(1)
   ```

3. **Video Capture:** Check if source opened successfully (line 180-182)
   ```python
   if not cap.isOpened():
       print(f"Error: Cannot open video source: {args.source}")
       sys.exit(1)
   ```

4. **Frame Read Failure:** For files, restart; for camera, break (line 203-210)
   ```python
   if not ret:
       if not is_camera:
           cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Restart video
           continue
       print("Error: Failed to read from camera.")
       break
   ```

5. **None Checks:** Handle optional YOLO outputs (line 104)
   ```python
   if boxes is None:
       continue
   ```

## Cross-Cutting Concerns

**Logging:** Direct print() statements for user feedback (model loading, mode switch, startup info)

**Validation:** Path validation (file exists), argument range checks (confidence 0.5 default), camera index validation

**Configuration:** Command-line arguments define behavior; constants define visual appearance (SIZE_COLORS, STABLE_WINDOW)

---

*Architecture analysis: 2026-03-24*
