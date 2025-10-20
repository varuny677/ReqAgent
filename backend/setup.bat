@echo off
echo ========================================
echo Company Search Agent - Backend Setup
echo ========================================
echo.

echo Checking Python version...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher from https://python.org
    pause
    exit /b 1
)
echo.

echo Step 1: Removing old virtual environment (if exists)...
if exist venv (
    rmdir /s /q venv
    echo ✓ Old virtual environment removed
)
echo.

echo Step 2: Creating new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo ✓ Virtual environment created
echo.

echo Step 3: Activating virtual environment...
call venv\Scripts\activate
echo ✓ Virtual environment activated
echo.

echo Step 4: Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
echo ✓ pip upgraded
echo.

echo Step 5: Installing dependencies...
echo This may take a few minutes...
echo.
pip install --no-cache-dir -r requirements.txt
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Failed to install dependencies
    echo ========================================
    echo.
    echo This might be because:
    echo 1. Some packages require Visual C++ Build Tools
    echo 2. Internet connection issues
    echo 3. Package compatibility issues
    echo.
    echo Trying to install with pre-built wheels only...
    echo.
    pip install --only-binary=:all: -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Still failed. Trying one more approach...
        echo Installing core packages individually...
        pip install fastapi uvicorn python-dotenv pydantic pydantic-settings
        pip install google-generativeai
        pip install temporalio==1.6.0
        pip install aiohttp websockets python-multipart
        pip install black flake8 isort
        if errorlevel 1 (
            echo.
            echo ERROR: Could not install all packages
            echo Please check your internet connection and try again
            pause
            exit /b 1
        )
    )
)
echo ✓ Dependencies installed
echo.

echo Step 6: Verifying installation...
python -c "import fastapi; import temporalio; import google.generativeai; print('✓ All core packages installed successfully')"
if errorlevel 1 (
    echo WARNING: Some packages may not have installed correctly
    echo But continuing anyway...
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Virtual environment is now activated.
echo.
echo Next steps:
echo 1. Start Temporal server in another terminal:
echo    docker-compose up
echo.
echo 2. In a new terminal, start the worker:
echo    cd backend
echo    venv\Scripts\activate
echo    python worker.py
echo.
echo 3. In another new terminal, start the API:
echo    cd backend
echo    venv\Scripts\activate
echo    python app.py
echo.
echo 4. Start the frontend:
echo    cd frontend
echo    npm install
echo    npm run dev
echo.
pause
