# viewer.spec — PyInstaller spec for EggSentry Viewer exe
#
# Build with:  pyinstaller viewer.spec
#
# Output:  dist/EggSentry.exe  (single-file executable)

from PyInstaller.utils.hooks import collect_all, collect_data_files

# Grab every file ultralytics ships (configs, assets, etc.)
ultra_datas, ultra_binaries, ultra_hidden = collect_all("ultralytics")

a = Analysis(
    ["edge/viewer.py"],
    pathex=[".", "edge"],           # makes edge/*.py importable by name
    binaries=ultra_binaries,
    datas=[
        # YOLO NCNN model (entire directory)
        ("models/counter-yolo26n_ncnn_model", "models/counter-yolo26n_ncnn_model"),
        # ultralytics internal data (yaml configs, assets…)
        *ultra_datas,
    ],
    hiddenimports=[
        *ultra_hidden,
        # torch / vision
        "torch",
        "torchvision",
        "torchvision.transforms",
        # image / array
        "cv2",
        "numpy",
        "PIL",
        "PIL.Image",
        # ultralytics extras sometimes missed by collect_all
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
        # edge package modules
        "detector",
        "size_classifier",
        "config",
        "capture",
        "stabilizer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Strip things we don't need to keep the exe smaller
        "matplotlib",
        "tkinter",
        "IPython",
        "jupyter",
        "notebook",
        "pandas",
        "scipy",
        "sklearn",
        "tensorflow",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EggSentry",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=True keeps a terminal window visible so users can read errors.
    # Change to False once you've confirmed it works to hide the console.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,        # swap in an .ico file here if you have one
)
