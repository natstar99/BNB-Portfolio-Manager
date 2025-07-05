@echo off
setlocal enabledelayedexpansion

echo =========================================
echo     BNB Portfolio Manager - Coverage Mode
echo =========================================
echo.

:MENU
echo Choose an option:
echo 1. Start NEW coverage analysis (fresh scan)
echo 2. CONTINUE existing coverage analysis
echo 3. Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto NEW_COVERAGE
if "%choice%"=="2" goto CONTINUE_COVERAGE  
if "%choice%"=="3" goto EXIT
echo Invalid choice. Please try again.
echo.
goto MENU

:NEW_COVERAGE
echo.
echo 🧹 Cleaning up old coverage data...

REM Clean up old coverage files
if exist "backend\.coverage" del "backend\.coverage" >nul 2>&1
if exist "backend\coverage_html" rmdir /s /q "backend\coverage_html" >nul 2>&1
if exist "frontend\coverage" rmdir /s /q "frontend\coverage" >nul 2>&1

echo ✅ Old coverage data cleaned!
goto START_COVERAGE

:CONTINUE_COVERAGE
echo.
echo 📊 Continuing with existing coverage data...

:START_COVERAGE
echo.
echo 🚀 Starting BNB with coverage tracking...
echo.

REM Set script directory as working directory
cd /d "%~dp0"

REM Call the normal startup script with coverage parameter
call start-bnb.bat "python enhanced_coverage.py"

echo.
echo ========================================
echo          COVERAGE SESSION ENDED  
echo ========================================
echo.

REM Run frontend test coverage
echo 🧪 Generating frontend test coverage...
cd frontend
call npm test -- --coverage --watchAll=false --passWithNoTests >nul 2>&1
cd ..

echo.
echo 📊 Coverage reports generated:
echo.
echo BACKEND:
echo - HTML Report: backend\coverage_html\index.html
echo.
echo FRONTEND:
echo - Test Coverage: frontend\coverage\lcov-report\index.html
echo.
echo.
set /p openReports="🌐 Open coverage reports in browser? (y/n): "
if /i "%openReports%"=="y" (
    echo.
    echo 🚀 Opening coverage reports...
    if exist "backend\coverage_html\index.html" (
        start "" "backend\coverage_html\index.html"
    )
    if exist "frontend\coverage\lcov-report\index.html" (
        start "" "frontend\coverage\lcov-report\index.html"
    )
    echo ✅ Reports opened in your default browser
) else (
    echo 💡 You can manually open the HTML reports later
)
echo.

pause
goto EXIT

:EXIT
echo.
echo 👋 Goodbye!
exit