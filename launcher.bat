@echo off
setlocal enabledelayedexpansion
title Inspect.gg Launcher
echo Starting Inspect.gg Auto-Configuring Launcher...

:: Elevate to admin automatically (Needed for Python Silent Install and Hardware Scans)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator rights...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

:: Step 1: Verify Python Installation
set PYTHON_EXE=python
%PYTHON_EXE% -c "import sys" >nul 2>&1
if %errorLevel% neq 0 (
    echo =======================================================
    echo Python not found on standard PATH. Checking for local installations...
    
    :: Attempt to locate if installed but not in PATH
    if exist "C:\Program Files\Python311\python.exe" (
        set PYTHON_EXE="C:\Program Files\Python311\python.exe"
    ) else if exist "C:\Program Files\Python310\python.exe" (
        set PYTHON_EXE="C:\Program Files\Python310\python.exe"
    ) else (
        echo Python is inherently missing. Automating Python Installation...
        echo Please wait, downloading Python 3.11... (This may take a minute)
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile 'python-installer.exe'"
        
        echo Running silent installer...
        start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        
        echo Installer finished. Cleaning up...
        del python-installer.exe
        
        :: Set explicit path since environment variables aren't refreshed in this active cmd window
        set PYTHON_EXE="C:\Program Files\Python311\python.exe"
    )
)

echo Using Python Binary: %PYTHON_EXE%
%PYTHON_EXE% --version

:: Step 2: Handle Virtual Environment
if not exist venv\Scripts\activate.bat (
    echo [NOTICE] Virtual environment missing or corrupted. Rebuilding...
    if exist venv rmdir /s /q venv
    
    %PYTHON_EXE% -m venv venv
    if !errorLevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
    
    echo Activating environment and installing dependencies...
    call venv\Scripts\activate.bat
    
    python -m pip install --upgrade pip >nul 2>&1
    
    echo Installing required packages from requirements.txt...
    pip install -r requirements.txt
    if !errorLevel! neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b
    )

    echo Finalizing Windows system registration...
    python venv\Scripts\pywin32_postinstall.py -install >nul 2>&1
) else (
    call venv\Scripts\activate.bat
)

:: Step 3: Launch
if not exist src\app.py (
    echo [ERROR] src\app.py not found! Are you running the launcher from the root folder?
    pause
    exit /b
)

cd src
echo Starting Flask Application Server...
echo The browser will open shortly...

:: Start the browser with a 4 second delay
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:5000"

echo =======================================================
echo Inspect.gg is now live!
echo Do not close this terminal while utilizing the tool.
echo =======================================================

:: Run Python using the venv's python
python app.py
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] The application crashed or failed to start.
    pause
)
