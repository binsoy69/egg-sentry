# Codebase Concerns

**Analysis Date:** 2026-03-24

## Tech Debt

**Minimal Error Recovery:**
- Issue: The application exits immediately on model load or video source errors with `sys.exit(1)` calls, providing no graceful degradation or recovery options
- Files: `egg_sentry.py` (lines 56-57, 68-69, 181-182)
- Impact: Any transient failures (missing model file, temporarily unavailable camera, invalid video path) crashes the entire application without allowing user intervention or retry
- Fix approach: Implement retry logic with exponential backoff, user prompts for alternative sources, or fallback modes. Consider moving to exception-based error handling instead of sys.exit()

**Hard-Coded Configuration Values:**
- Issue: Critical parameters are hard-coded: STABLE_WINDOW=15, default confidence=0.5, window size=1280x720, all color mappings
- Files: `egg_sentry.py` (lines 15-23, 26, 47, 187)
- Impact: Changing behavior requires code modifications and redeployment; no runtime configurability for different hardware/scenarios
- Fix approach: Move to configuration file (YAML/JSON) or environment variables; allow CLI overrides for more parameters

**No Logging System:**
- Issue: Application uses only print() statements with no structured logging, log levels, or output redirection capability
- Files: `egg_sentry.py` (lines 56, 58, 68, 181, 189-190, 209, 243)
- Impact: No audit trail, no log persistence, no way to capture errors in production, debugging video processing issues is difficult
- Fix approach: Integrate logging module with file output, configurable levels, and timestamp tracking

**Incomplete Mode Switching Error Handling:**
- Issue: When toggling modes (line 239-240), if the new model fails to load, the application state is corrupted but no error is caught
- Files: `egg_sentry.py` (lines 238-243)
- Impact: Mode toggle could leave application in inconsistent state with mismatched model and history
- Fix approach: Validate model load before committing state change; rollback to previous mode on failure

## Known Bugs

**Frame History Not Cleared on Mode Switch:**
- Symptoms: When switching between count and size modes, detection history may contain data from the previous mode, potentially causing momentary display inconsistencies
- Files: `egg_sentry.py` (lines 238-242)
- Trigger: Press 'm' key to toggle mode while detections are active
- Workaround: Wait until no eggs are detected before switching modes

**Stability Window Inconsistency with Video Loops:**
- Symptoms: When a video file loops back to frame 0 (line 205), history is cleared but stabilization window size remains the same, potentially showing inflated or deflated counts on the loop boundary
- Files: `egg_sentry.py` (lines 204-208)
- Trigger: Play a video file to completion and observe first few frames of the second loop
- Workaround: Use live camera input instead of looping video files

**Display Label Overflow:**
- Symptoms: Long size class names or high tracking IDs may cause text labels to extend beyond bounding box background rectangle
- Files: `egg_sentry.py` (lines 136-141)
- Trigger: Detect eggs with tracking IDs > 100 in size classification mode
- Workaround: Labels will still be readable but may look misaligned

## Security Considerations

**Path Traversal Risk:**
- Risk: Video source file paths are not validated beyond existence check; no sanitization or restriction to safe directories
- Files: `egg_sentry.py` (lines 62-70)
- Current mitigation: Only existence check via Path.exists()
- Recommendations: Implement path allowlist validation, restrict to specific video directories, use pathlib to resolve and validate paths are within allowed scope

**No Input Validation on Confidence Threshold:**
- Risk: Confidence parameter accepts any float value without bounds checking; values outside [0, 1] could cause YOLO inference issues
- Files: `egg_sentry.py` (line 47, passed to line 213)
- Current mitigation: None - float type only
- Recommendations: Add validation: 0 <= conf <= 1, provide clear error message for invalid values

**Model Files Not Authenticated:**
- Risk: `.pt` model files are loaded without checksum verification; malicious models could be substituted
- Files: `egg_sentry.py` (lines 11-13, 54-59)
- Current mitigation: None
- Recommendations: Implement MD5/SHA256 verification of model files before loading; document expected checksums

## Performance Bottlenecks

**Model Reload on Every Mode Toggle:**
- Problem: Each mode switch fully reloads the YOLO model into memory, causing UI freeze
- Files: `egg_sentry.py` (line 240)
- Cause: No model caching; both models are reloaded even though they both exist at startup
- Improvement path: Load both models at startup (increases initial load time ~2-3s but eliminates toggle freezes); maintain in memory or use lazy loading with background threads

**Tracking ID Display Without Reset:**
- Problem: Tracking IDs never reset and increment indefinitely; high IDs cause slower text rendering and display clutter
- Files: `egg_sentry.py` (line 132)
- Cause: YOLO tracker maintains persistent ID sequences across entire session
- Improvement path: Implement periodic ID remapping or batch reset strategy every N frames; limit displayed ID digits

**Rolling History Inefficiency:**
- Problem: Stabilization uses mode (most frequent value) which is O(n) for each frame when calculating Counter
- Files: `egg_sentry.py` (lines 73-78, 81-94)
- Cause: `Counter.most_common()` is called every frame for every size class
- Improvement path: Use deque of numpy arrays for vectorized operations; implement exponential moving average instead of mode

**Frame Read Blocking:**
- Problem: Synchronous video capture blocks main thread; if inference is slow, frame reading falls behind
- Files: `egg_sentry.py` (lines 202, 213)
- Cause: Single-threaded while loop with no async processing
- Improvement path: Implement frame queue with producer/consumer threads to decouple capture from inference

## Fragile Areas

**Tracking Persistence Assumptions:**
- Files: `egg_sentry.py` (lines 107-116, 212-213)
- Why fragile: Code assumes `boxes.id` is always available when `persist=True`, but graceful handling for None case exists; assumption depends on YOLO version and model type
- Safe modification: Always test mode toggle and detection drawing after YOLO version updates; add explicit None checks for tracking IDs
- Test coverage: No unit tests for tracking edge cases; manual testing only

**Size Class Hardcoding:**
- Files: `egg_sentry.py` (lines 15-23, 150-154)
- Why fragile: If YOLO model is retrained with different size classes or order, colors array and size_history logic breaks silently
- Safe modification: Extract size classes to configuration with mapping validation; assert model.names matches expected sizes at model load time
- Test coverage: No validation that model outputs match configured size classes

**OpenCV Window Management:**
- Files: `egg_sentry.py` (lines 186-187, 233, 246)
- Why fragile: No cleanup on exception; if inference throws unhandled exception, window may hang or require manual close
- Safe modification: Wrap main loop in try/finally; ensure cv2.destroyAllWindows() always executes
- Test coverage: No error path testing

## Scaling Limits

**Single Video Source:**
- Current capacity: One camera or video file at a time
- Limit: Cannot simultaneously process multiple video streams or implement multi-camera counting
- Scaling path: Refactor to frame queue architecture; add threading or async frame processing; implement multi-source input manager

**Memory Footprint:**
- Current capacity: ~2GB for both YOLO models in memory simultaneously
- Limit: Cannot run on devices with <4GB RAM; model switching causes spikes
- Scaling path: Implement on-demand model loading; use model quantization (INT8); implement model streaming

**Large Video File Handling:**
- Current capacity: Tested on 160MB video files
- Limit: FPS counter suggests real-time or near real-time processing; batch processing of large archives unclear
- Scaling path: Implement video frame extraction to disk; add resume capability for interrupted processing; implement frame batching

## Dependencies at Risk

**Ultralytics YOLO Dependency:**
- Risk: Heavy dependency on ultralytics library; frequent breaking changes in updates; models may become incompatible with newer versions
- Impact: Model loading could fail on version updates; tracking API may change; inference performance may regress
- Migration plan: Pin ultralytics to specific version in requirements.txt with documented compatibility; implement model version validation; test all modes on version updates before deployment

**OpenCV Version Coupling:**
- Risk: Window management (namedWindow, resizeWindow) and API usage depends on specific OpenCV behavior that varies across versions
- Impact: Window display issues, waitKey behavior differences between cv2 versions
- Migration plan: Pin opencv-python version; document minimum/maximum tested versions; use version-agnostic API calls where possible

**Python Version Not Specified:**
- Risk: No Python version requirement; code may use features incompatible with Python < 3.8
- Impact: Unclear if code runs on Python 3.6 or 3.7
- Migration plan: Add python_requires=">=3.8" to setup; test on minimum specified version

## Missing Critical Features

**No Data Persistence:**
- Problem: Count statistics are not saved; every session starts fresh with no historical data
- Blocks: Analytics, trend detection, accuracy verification, export capabilities
- Recommendation: Add CSV/database logging of counts with timestamps; implement session save/restore

**No Model Performance Metrics:**
- Problem: No tracking of detection confidence distribution, false positive/negative rates, or per-size accuracy
- Blocks: Model validation, quality assurance, retraining decisions
- Recommendation: Implement per-frame logging of all detections with confidence scores; add summary stats at session end

**No Multi-Language Support for Labels:**
- Problem: Size class names hard-coded in English only
- Blocks: International deployment, localization
- Recommendation: Externalize label strings to i18n format

**No Unit Tests:**
- Problem: Zero automated test coverage
- Blocks: Safe refactoring, confidence in changes, CI/CD implementation
- Recommendation: Add pytest tests for stabilization logic, drawing functions, argument parsing

## Test Coverage Gaps

**Stabilization Logic:**
- What's not tested: `stabilize_count()` and `stabilize_size_counts()` functions with edge cases (empty history, single value, all zeros, rapid spikes)
- Files: `egg_sentry.py` (lines 73-94)
- Risk: Logic could silently fail with unusual detection patterns
- Priority: High

**Detection Drawing Edge Cases:**
- What's not tested: `draw_detections()` with no detections, None boxes, missing tracking IDs, very high confidence values
- Files: `egg_sentry.py` (lines 97-143)
- Risk: Could crash on edge cases or produce incorrect counts
- Priority: High

**Mode Switching:**
- What's not tested: Toggling between modes rapidly, switching while detections active, model loading failures during switch
- Files: `egg_sentry.py` (lines 238-242)
- Risk: State corruption, lost history, incorrect counts after mode switch
- Priority: Medium

**Video Source Resolution:**
- What's not tested: Invalid source strings, paths with special characters, network paths, corrupted video files
- Files: `egg_sentry.py` (lines 62-70)
- Risk: Unclear behavior on edge cases; potential crashes instead of graceful errors
- Priority: Medium

**Argument Parsing:**
- What's not tested: Invalid mode values, non-numeric camera index, missing arguments
- Files: `egg_sentry.py` (lines 29-50)
- Risk: argparse should handle, but validation of mode enum and conf bounds not tested
- Priority: Low

---

*Concerns audit: 2026-03-24*
