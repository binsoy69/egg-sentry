# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Files:**
- Single module files use lowercase with underscores: `egg_sentry.py`
- Model files stored in `models/` directory with descriptive names: `counter-yolo26n.pt`, `size-yolo26n.pt`

**Functions:**
- All functions use snake_case: `parse_args()`, `load_model()`, `resolve_source()`, `stabilize_count()`, `draw_detections()`
- Functions with descriptive verb-noun patterns for clarity
- Single responsibility principle observed: functions do one thing well

**Variables:**
- snake_case for all variables: `cap`, `frame`, `current_mode`, `count_history`, `stable_window`
- Constants in UPPER_CASE: `MODELS_DIR`, `COUNTER_MODEL`, `SIZE_MODEL`, `SIZE_COLORS`, `DEFAULT_COLOR`, `STABLE_WINDOW`
- Dictionary keys in lowercase with hyphens for display strings: `"small"`, `"medium"`, `"extra-large"`

**Types:**
- Type hints used in function signatures: `def parse_args():`, `def load_model(mode: str) -> YOLO:`, `def stabilize_count(history: deque) -> int:`
- Return type annotations included where applicable

## Code Style

**Formatting:**
- No explicit linter configuration detected; follows PEP 8 conventions by default
- Indentation: 4 spaces (standard Python)
- Line length: Appears to target ~100 characters based on actual code lines
- Blank lines: Single blank lines between functions, double blank lines between major sections

**Linting:**
- No detected linting configuration (`.flake8`, `.pylintrc`, `pyproject.toml`)
- Code follows implicit PEP 8 standards
- No type checking framework (mypy, pyright) configured

## Import Organization

**Order:**
1. Standard library: `argparse`, `sys`, `time`, `collections`, `pathlib`
2. Third-party libraries: `cv2`, `numpy`, `ultralytics`

**Path Aliases:**
- Uses `from pathlib import Path` for cross-platform path handling
- Path construction at module level: `MODELS_DIR = Path(__file__).parent / "models"`

## Error Handling

**Patterns:**
- Explicit error checks with early exit: Lines 55-57 (model existence check)
- Print-then-exit pattern for critical errors:
  ```python
  if not model_path.exists():
      print(f"Error: Model not found at {model_path}")
      sys.exit(1)
  ```
- Validation checks before operations: `resolve_source()` validates video file existence (lines 66-70)
- Video source error handling: Lines 180-182 check if video capture opened successfully

**Exception Handling:**
- No explicit try-catch blocks observed; relies on validation and early exits
- OpenCV operations assumed to succeed after validation

## Logging

**Framework:** `print()` - standard output only

**Patterns:**
- Informational messages prefixed with context: `"Loading model: ..."` (line 58)
- Error messages prefixed with "Error:" for clarity: Lines 56, 68, 181, 209
- Status messages during execution: Lines 189-190, 243
- FPS calculation and display for real-time performance feedback (line 156)

## Comments

**When to Comment:**
- Docstrings used for public functions explaining purpose, parameters, and return values:
  ```python
  def stabilize_count(history: deque) -> int:
      """Return the most frequent (mode) count from recent frames."""
  ```
- Inline comments explain non-obvious logic (lines 25-26, 115-116, 212)
- Comments explain "why" rather than "what": Line 197 explains stabilization purpose

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Uses Python docstring convention (triple-quoted strings)

## Function Design

**Size:** Functions are compact and focused (10-40 lines typical)
- `parse_args()`: 21 lines - argument parsing
- `load_model()`: 7 lines - model loading with validation
- `draw_detections()`: 46 lines - detection rendering (longer due to nested loops)
- Largest function is `run()` at 72 lines (main event loop)

**Parameters:**
- Minimal parameters passed (1-3 parameters typical)
- Uses objects when multiple related values needed: `frame`, `results`, `boxes`
- Immutable defaults for optional values: `conf=0.5`

**Return Values:**
- Functions return single values or tuples: `def draw_detections() -> (int, dict):`
- Consistent return type: Lines 77-78, 93-94, 143
- Early returns used for validation: Lines 75-76

## Module Design

**Exports:**
- Single entry point: `main()` function (lines 249-251)
- Supporting functions organized in logical order: parsing → loading → processing → display
- All functions at module level (no classes)

**Barrel Files:**
- Not applicable (single-file application)

**Global State:**
- Module-level constants for configuration: `MODELS_DIR`, `SIZE_COLORS`, `STABLE_WINDOW`
- Runtime state managed locally within functions or passed as arguments
- Camera state managed via OpenCV `VideoCapture` object

## Architecture Patterns

**Design Approach:**
- Functional programming style: pure functions with minimal side effects
- Command-line interface pattern: `parse_args()` → `run()` → `main()`
- Pipeline pattern for frame processing: capture → detect → draw → display
- State management via collections: `deque()` for stabilization history

**Separation of Concerns:**
- Model loading: `load_model()`
- Argument validation: `resolve_source()`
- Detection rendering: `draw_detections()`
- Overlay rendering: `draw_overlay()`
- Count stabilization: `stabilize_count()`, `stabilize_size_counts()`
- Main loop: `run()`

---

*Convention analysis: 2026-03-24*
