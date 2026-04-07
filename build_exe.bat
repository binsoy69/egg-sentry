@echo off
REM ============================================================
REM  build_exe.bat — Build EggSentry.exe
REM
REM  Requirements:
REM    - Python 3.10+ installed and on PATH
REM    - Run this script from the egg-sentry project root
REM ============================================================

echo.
echo ============================================================
echo  EggSentry Viewer — Build Script
echo ============================================================
echo.

REM --- Step 1: Install / upgrade build tools ---
echo [1/4] Installing build tools...
pip install --upgrade pyinstaller pip >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip failed. Make sure Python is installed and on PATH.
    pause
    exit /b 1
)

REM --- Step 2: Install runtime dependencies ---
echo [2/4] Installing runtime dependencies...
pip install ultralytics opencv-python numpy httpx
if errorlevel 1 (
    echo ERROR: Could not install dependencies.
    pause
    exit /b 1
)

REM --- Step 3: Build the exe ---
echo.
echo [3/4] Building EggSentry.exe (this can take several minutes)...
echo       The final exe will be large (~500 MB) because it bundles PyTorch.
echo.
pyinstaller viewer.spec --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. Check the output above for details.
    pause
    exit /b 1
)

REM --- Step 4: Done ---
echo.
echo [4/4] Done!
echo.
echo  Output:  dist\EggSentry.exe
echo.
echo  You can copy dist\EggSentry.exe to any Windows computer.
echo  No Python installation needed on the target machine.
echo.
pause
