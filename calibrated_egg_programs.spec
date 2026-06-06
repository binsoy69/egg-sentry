# PyInstaller spec for the standalone calibrated EggSentry programs.
#
# Build with:
#   python -m PyInstaller calibrated_egg_programs.spec --noconfirm
#
# Outputs:
#   dist/EggSentry-Calibrate.exe
#   dist/EggSentry-Counter.exe

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path.cwd()
MODEL_DIR = ROOT / "models" / "counter-yolo26n_ncnn_model"
MODEL_PT = ROOT / "models" / "counter-yolo26n.pt"

ultra_datas, ultra_binaries, ultra_hidden = collect_all("ultralytics")

datas = [*ultra_datas]
if MODEL_DIR.exists():
    datas.append((str(MODEL_DIR), "models/counter-yolo26n_ncnn_model"))
if MODEL_PT.exists():
    datas.append((str(MODEL_PT), "models/counter-yolo26n.pt"))

hiddenimports = [
    *ultra_hidden,
    "torch",
    "torchvision",
    "torchvision.transforms",
    "cv2",
    "numpy",
    "PIL",
    "PIL.Image",
    "ultralytics.models",
    "ultralytics.models.yolo",
    "ultralytics.models.yolo.detect",
    "ultralytics.models.yolo.detect.predict",
    "ultralytics.models.yolo.detect.train",
    "ultralytics.models.yolo.detect.val",
    "ultralytics.engine",
    "ultralytics.engine.model",
    "ultralytics.engine.predictor",
    "ultralytics.utils",
    "ultralytics.utils.torch_utils",
    "calibrated_egg_programs",
    "calibrated_egg_programs.calibration_core",
    "calibrated_egg_programs.detector",
    "calibrated_egg_programs.runtime",
]

excludes = [
    "matplotlib",
    "tkinter",
    "IPython",
    "jupyter",
    "notebook",
    "pandas",
    "scipy",
    "sklearn",
    "tensorflow",
]


def build_exe(script: str, name: str) -> EXE:
    analysis = Analysis(
        [script],
        pathex=[".", "calibrated_egg_programs"],
        binaries=ultra_binaries,
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=excludes,
        noarchive=False,
        optimize=0,
    )
    pyz = PYZ(analysis.pure)
    return EXE(
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )


calibrate_exe = build_exe(
    "calibrated_egg_programs/calibrate_camera.py",
    "EggSentry-Calibrate",
)
counter_exe = build_exe(
    "calibrated_egg_programs/run_counter.py",
    "EggSentry-Counter",
)

