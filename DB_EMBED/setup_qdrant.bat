@echo off
REM Quick setup script for Qdrant embedding
REM Run this to set up everything automatically

echo ============================================================
echo Vietnamese Legal Documents - Qdrant Setup
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please create venv first: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/4] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if packages are installed
echo.
echo [2/4] Checking required packages...
python -c "import qdrant_client" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installing required packages...
    pip install qdrant-client sentence-transformers torch
) else (
    echo [OK] Packages already installed
)

REM Check if Qdrant is running
echo.
echo [3/4] Checking Qdrant server...
curl -s http://localhost:6333/collections >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Qdrant is not running!
    echo.
    echo Please start Qdrant first:
    echo   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
    echo.
    echo Or download from: https://github.com/qdrant/qdrant/releases
    echo.
    pause
    exit /b 1
) else (
    echo [OK] Qdrant is running
)

REM Run embedding
echo.
echo [4/4] Starting embedding process...
echo This may take 5-10 minutes...
echo.
python embed_to_qdrant.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo Success! Your documents are now in Qdrant
    echo ============================================================
    echo.
    echo Next steps:
    echo   1. Test search: python search_example.py
    echo   2. Start web UI: uvicorn search_api:app --reload
    echo   3. Open browser: http://localhost:8000
    echo.
) else (
    echo.
    echo [ERROR] Embedding failed. Check the error messages above.
    echo.
)

pause
