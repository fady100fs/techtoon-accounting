@echo off
title Techtoon Accounting
color 0B

echo ============================================================
echo   Techtoon Accounting
echo   Starting program...
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not installed!
    echo Please run install.bat first
    pause
    exit /b 1
)

:: Check libraries
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Libraries not installed!
    echo Please run install.bat first
    pause
    exit /b 1
)

:: Run program
echo [OK] Opening program in browser...
echo.
echo If browser does not open automatically, visit:
echo http://localhost:8501
echo.
echo To stop the program, press Ctrl+C
echo ============================================================
echo.

streamlit run app.py --server.headless true --server.port 8501

pause