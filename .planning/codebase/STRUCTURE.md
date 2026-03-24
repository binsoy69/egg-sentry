# Codebase Structure

**Analysis Date:** 2026-03-24

## Directory Layout

```
egg-sentry/
├── egg_sentry.py           # Main application entry point (256 lines)
├── requirements.txt        # Python dependencies
├── models/                 # Pre-trained YOLO models (binary)
│   ├── counter-yolo26n.pt  # YOLO model for egg counting
│   └── size-yolo26n.pt     # YOLO model for egg size classification
├── vids/                   # Test video files
│   └── egg-counter-test-vid.mp4
└── .planning/              # Documentation (generated)
    └── codebase/
```

## Directory Purposes

**Root Directory:**
- Purpose: Application entry point and main configuration
- Contains: Main Python module, dependency list, model files
- Key files: `egg_sentry.py`

**models/:**
- Purpose: Store pre-trained YOLO model weights
- Contains: Binary `.pt` PyTorch model files (5.3 MB each)
- Key files: `counter-yolo26n.pt`, `size-yolo26n.pt`
- Generated: No (committed to repo)
- Committed: Yes (required for inference)

**vids/:**
- Purpose: Store test/demo video files for testing
- Contains: MP4 video files (~162 MB)
- Committed: Yes (for reproducible testing)

**.planning/codebase/:**
- Purpose: Architecture and design documentation
- Generated: Yes (created by analysis tools)
- Committed: Yes (part of documentation)

## Key File Locations

**Entry Points:**
- `egg_sentry.py`: Main script entry point; run with `python egg_sentry.py`

**Configuration:**
- `requirements.txt`: Python dependency specification (ultralytics, opencv-python, numpy)
- `egg_sentry.py` lines 16-26: Hard-coded constants (SIZE_COLORS, STABLE_WINDOW)

**Core Logic:**
- `egg_sentry.py` lines 29-50: Argument parsing (`parse_args()`)
- `egg_sentry.py` lines 53-59: Model loading (`load_model()`)
- `egg_sentry.py` lines 62-70: Source validation (`resolve_source()`)
- `egg_sentry.py` lines 73-94: Stabilization functions (`stabilize_count()`, `stabilize_size_counts()`)
- `egg_sentry.py` lines 97-143: Detection visualization (`draw_detections()`)
- `egg_sentry.py` lines 146-172: HUD rendering (`draw_overlay()`)
- `egg_sentry.py` lines 175-246: Main inference loop (`run()`)

**Models (Binary):**
- `models/counter-yolo26n.pt`: YOLO26n model trained for egg counting (5.3 MB)
- `models/size-yolo26n.pt`: YOLO26n model trained for egg size classification (5.3 MB)

**Testing:**
- `vids/egg-counter-test-vid.mp4`: Test video for validation (162 MB)

## Naming Conventions

**Files:**
- Main module: snake_case (`egg_sentry.py`)
- Model files: descriptive with task and architecture (`counter-yolo26n.pt`, `size-yolo26n.pt`)
- Config files: lowercase with extensions (`requirements.txt`)

**Directories:**
- Purpose-based: lowercase plural for collections (`models/`, `vids/`)

**Functions:**
- Verb-based naming: `parse_args()`, `load_model()`, `resolve_source()`, `stabilize_count()`, `draw_detections()`, `draw_overlay()`
- Snake_case throughout

**Variables:**
- Snake_case: `count_history`, `size_history`, `stable_window`, `prev_time`, `is_camera`, `current_mode`
- Constants: UPPER_SNAKE_CASE (`MODELS_DIR`, `COUNTER_MODEL`, `SIZE_MODEL`, `SIZE_COLORS`, `DEFAULT_COLOR`, `STABLE_WINDOW`)

**Classes:**
- Not applicable (procedural design, no classes defined)

## Where to Add New Code

**New Feature (e.g., additional classification):**
- Primary code: `egg_sentry.py` - Add mode branching in `parse_args()`, `load_model()`, and `draw_detections()`
- Constants: Add to SIZE_COLORS dict or create new constant dict for feature colors
- Tests: Create `test_egg_sentry.py` in root (see Testing section below)

**New Detection Mode (e.g., quality classification):**
- Add argument choice to `parser.add_argument("--mode", ...)` (line 34-38)
- Add conditional model loading in `load_model()` (line 54-55)
- Add visualization logic in `draw_detections()` (line 120-125)
- Add stabilization function if needed (following pattern of `stabilize_size_counts()`)

**Utilities & Helpers:**
- Path utilities: Define near top with existing Path imports (`MODELS_DIR`, etc.)
- Drawing utilities: Add as functions in sequence with other drawing functions (before `run()`)
- Validation utilities: Add near `resolve_source()` (line 62-70)

**Configuration:**
- Hard-coded constants: Add to top-level constants section (lines 11-26)
- Command-line arguments: Add to `parse_args()` function (lines 29-50)
- Environment variables: Not currently used; introduce via `parse_args()` only if needed

## Special Directories

**models/:**
- Purpose: Pre-trained YOLO model storage
- Generated: No (pre-trained weights, manually added)
- Committed: Yes (essential for runtime)
- Size: ~10 MB total
- Note: Models are binary .pt files; do not edit directly

**vids/:**
- Purpose: Test video samples
- Generated: No (external video files)
- Committed: Yes (enables testing without camera)
- Size: ~162 MB
- Note: Single test video; can add more test cases here

**.planning/codebase/:**
- Purpose: Generated codebase documentation
- Generated: Yes (by analysis tools)
- Committed: Yes (part of documentation suite)
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md (when generated)

## Module Organization

**Current State:**
- Single monolithic module (`egg_sentry.py`)
- All functions organized sequentially: config → arg parsing → model loading → validation → stabilization → visualization → main loop

**Logical Grouping (if refactoring into modules):**
- `cli.py`: Argument parsing, user interaction
- `models.py`: Model loading and management
- `detection.py`: Detection visualization and drawing
- `stabilization.py`: Count stabilization logic
- `config.py`: Constants and configuration

---

*Structure analysis: 2026-03-24*
