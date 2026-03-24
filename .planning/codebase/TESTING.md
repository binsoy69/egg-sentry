# Testing Patterns

**Analysis Date:** 2026-03-24

## Test Framework

**Runner:**
- Not detected - no test framework currently configured
- Python project without pytest, unittest, or similar setup

**Assertion Library:**
- Not applicable - no testing infrastructure present

**Run Commands:**
```bash
# Testing not currently configured
# To add testing, would need:
pytest                 # Run all tests (after installation)
pytest --watch         # Watch mode (with pytest-watch)
pytest --cov           # Coverage (with pytest-cov)
```

## Test File Organization

**Location:**
- No test files currently present
- Pattern NOT YET established

**Naming:**
- Standard Python convention would be: `test_egg_sentry.py` or `egg_sentry_test.py`

**Structure:**
- No existing test structure to reference

## Test Coverage Gaps

**Untested Areas:**

**Argument Parsing:**
- Files: `/d/codeNcraft/egg-sentry/egg_sentry.py` (lines 29-50)
- What's not tested: `parse_args()` function with various argument combinations
- Risk: Invalid argument handling could fail silently or crash at runtime
- Priority: Medium - affects user experience with command-line interface

**Model Loading:**
- Files: `/d/codeNcraft/egg-sentry/egg_sentry.py` (lines 53-59)
- What's not tested: Model file existence check, missing model files, corrupted model files
- Risk: Application crashes with unclear error message if models not found
- Priority: High - critical for application startup

**Source Resolution:**
- Files: `/d/codeNcraft/egg-sentry/egg_sentry.py` (lines 62-70)
- What's not tested: Camera index validation, invalid video file paths, file permission errors
- Risk: Silent failures or unclear error messages when source invalid
- Priority: High - blocks video input setup

**Stabilization Logic:**
- Files: `/d/codeNcraft/egg-sentry/egg_sentry.py` (lines 73-94)
- What's not tested: `stabilize_count()` with various history sizes, edge cases (empty history, all zeros)
- What's not tested: `stabilize_size_counts()` with multiple size categories, missing size classes
- Risk: Incorrect count display or unexpected behavior with edge cases
- Priority: Medium - core feature reliability

**Detection Drawing:**
- Files: `/d/codeNcraft/egg-sentry/egg_sentry.py` (lines 97-143)
- What's not tested: Handling when boxes is None, confidence value display, color selection by size
- Risk: Visual display issues, incorrect count reporting
- Priority: Medium - affects UI accuracy

**Video Capture Loop:**
- Files: `/d/codeNcraft/egg-sentry/egg_sentry.py` (lines 175-246)
- What's not tested: Frame reading failures, mode toggling, history clearing on mode switch
- Risk: Incomplete or incorrect behavior during mode switching or source failures
- Priority: High - main program logic

## Recommended Testing Strategy

**Unit Test Priority:**
1. **Stabilization functions** (HIGH) - Pure functions, easily testable
   - `stabilize_count()` with various history sizes and values
   - `stabilize_size_counts()` with different size combinations

2. **Validation functions** (HIGH) - Input validation critical
   - `resolve_source()` with camera indices and file paths
   - Model loading with missing/corrupted models

3. **Data parsing** (MEDIUM)
   - `parse_args()` with different argument combinations
   - Source path resolution edge cases

**Integration Test Considerations:**
- Video capture behavior would require mocking or test video files
- Frame processing would require mock YOLO results
- Drawing operations would require mock OpenCV operations

**Proposed Test Structure:**

```python
# tests/test_egg_sentry.py

import pytest
from pathlib import Path
from collections import deque
from unittest.mock import Mock, patch, MagicMock

from egg_sentry import (
    parse_args,
    load_model,
    resolve_source,
    stabilize_count,
    stabilize_size_counts,
    draw_detections,
    draw_overlay
)

class TestArgumentParsing:
    def test_parse_args_default_count_mode(self):
        """Test default arguments parse to 'count' mode."""
        # Would test with sys.argv mock

class TestModelLoading:
    def test_load_model_missing_file(self):
        """Test error handling when model file not found."""
        # Would patch Path.exists() to return False

class TestSourceResolution:
    def test_resolve_source_camera_index(self):
        """Test camera index as string converts to int."""

    def test_resolve_source_video_file(self):
        """Test video file path validation."""

    def test_resolve_source_missing_file(self):
        """Test error on missing video file."""

class TestStabilization:
    def test_stabilize_count_empty_history(self):
        """Test empty history returns 0."""
        history = deque(maxlen=15)
        assert stabilize_count(history) == 0

    def test_stabilize_count_mode_selection(self):
        """Test most frequent count is returned."""
        history = deque([5, 5, 5, 6, 6], maxlen=15)
        assert stabilize_count(history) == 5

    def test_stabilize_size_counts_empty_history(self):
        """Test empty history returns empty dict."""
        history = deque(maxlen=15)
        assert stabilize_size_counts(history) == {}

    def test_stabilize_size_counts_multiple_sizes(self):
        """Test size breakdown stabilization."""
        history = deque([
            {"small": 2, "medium": 3},
            {"small": 2, "medium": 3},
            {"small": 2, "medium": 4},
        ], maxlen=15)
        result = stabilize_size_counts(history)
        assert result["small"] == 2
        assert result["medium"] == 3
```

## Mocking Strategy

**What to Mock:**
- `cv2.VideoCapture` - for video source testing
- `cv2.namedWindow`, `cv2.imshow`, `cv2.waitKey` - for display operations
- `YOLO.track()` - for model inference in testing
- `Path.exists()` - for file validation testing

**What NOT to Mock:**
- Pure utility functions like `stabilize_count()`
- Dictionary and deque operations
- Basic Python data structures

## Coverage Goals

**Recommended Minimums:**
- Critical functions (validation, stabilization): 90%+ coverage
- Display/drawing functions: 60%+ coverage (harder to test visually)
- Main loop: 50%+ coverage (complex state management)

**Overall target:** 70%+ code coverage for core logic

## Current Testing State

**Status:** No automated testing framework configured

**Missing:**
- pytest or unittest setup
- Test fixtures for mock YOLO models and video frames
- Mock objects for OpenCV operations
- CI/CD integration for test execution

**Quick-Start Setup:**

```bash
# Install testing dependencies
pip install pytest pytest-cov pytest-mock

# Create test directory structure
mkdir -p tests
touch tests/__init__.py
touch tests/test_egg_sentry.py

# Run tests with coverage
pytest tests/ --cov=egg_sentry --cov-report=html
```

---

*Testing analysis: 2026-03-24*
