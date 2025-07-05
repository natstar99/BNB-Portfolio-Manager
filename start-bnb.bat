@echo off
echo ==========================================
echo BNB Portfolio Manager - Startup Script
echo ==========================================
echo.

REM Set script directory as working directory
cd /d "%~dp0"

echo Checking prerequisites...
python --version
node --version
echo.

echo Setting up backend...
cd backend

if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Setting up database...
set FLASK_APP=run.py
set FLASK_ENV=development

REM Database will be automatically initialized on first run

echo Backend setup complete!
cd ..

echo Setting up frontend...
cd frontend

if not exist "node_modules\" (
    echo Installing npm dependencies...
    npm install
)

echo Frontend setup complete!
cd ..

echo.
echo Starting servers...
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
echo.

if "%~1"=="" (
    start "BNB Backend" cmd /k "cd /d %CD%\backend && call venv\Scripts\activate.bat && python run.py"
) else (
    start "BNB Backend" cmd /k "cd /d %CD%\backend && call venv\Scripts\activate.bat && %~1"
)
timeout /t 3 >nul
start "BNB Frontend" cmd /k "cd /d %CD%\frontend && npm start"

echo.
echo Servers are starting in separate windows!
echo Press any key to close this window...
pause >nul