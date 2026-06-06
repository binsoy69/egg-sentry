@echo off
REM ============================================================
REM  Build standalone calibrated EggSentry executables
REM
REM  Outputs:
REM    dist\EggSentry-Calibrate.exe
REM    dist\EggSentry-Counter.exe
REM ============================================================

echo.
echo ============================================================
echo  EggSentry Calibrated Programs - Build Script
echo ============================================================
echo.

echo [1/3] Installing build and runtime dependencies...
python -m pip install --upgrade pip pyinstaller
if errorlevel 1 (
    echo ERROR: Could not install PyInstaller.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Could not install runtime dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Building executables...
python -m PyInstaller calibrated_egg_programs.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed. Check the output above.
    pause
    exit /b 1
)

echo.
echo [3/3] Done.
echo.
echo Output files:
echo   dist\EggSentry-Calibrate.exe
echo   dist\EggSentry-Counter.exe
echo.
echo Put calibration.json next to EggSentry-Counter.exe, or create it there by running EggSentry-Calibrate.exe.
echo.
pause

