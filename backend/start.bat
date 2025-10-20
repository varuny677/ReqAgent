@echo off
echo Starting Company Search Backend...
echo.

echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Choose which component to start:
echo 1. Temporal Worker
echo 2. FastAPI Server
echo 3. Both (requires 2 terminals)
echo.

set /p choice="Enter your choice (1, 2, or 3): "

if "%choice%"=="1" (
    echo Starting Temporal Worker...
    python worker.py
) else if "%choice%"=="2" (
    echo Starting FastAPI Server...
    python app.py
) else if "%choice%"=="3" (
    echo Starting both... Please run this script in 2 separate terminals instead.
    echo Terminal 1: Choose option 1
    echo Terminal 2: Choose option 2
    pause
) else (
    echo Invalid choice!
    pause
)
