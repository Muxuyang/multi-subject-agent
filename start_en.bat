@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Multi-Subject Agent System Starting...
echo ========================================
echo.

if not exist .env (
    echo [ERROR] .env file not found
    echo Copying from .env.example...
    copy .env.example .env
    echo Please edit .env and fill in LLM_API_KEY
    pause
    exit /b 1
)

if not exist logs mkdir logs

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

echo.
echo Starting agents...
echo.

start /B cmd /c "python subject_agents.py math > logs\math.log 2>&1"
echo [1/7] Math agent starting on port 8001
timeout /t 2 /nobreak >nul

start /B cmd /c "python subject_agents.py physics > logs\physics.log 2>&1"
echo [2/7] Physics agent starting on port 8002
timeout /t 2 /nobreak >nul

start /B cmd /c "python subject_agents.py chemistry > logs\chemistry.log 2>&1"
echo [3/7] Chemistry agent starting on port 8003
timeout /t 2 /nobreak >nul

start /B cmd /c "python subject_agents.py biology > logs\biology.log 2>&1"
echo [4/7] Biology agent starting on port 8004
timeout /t 2 /nobreak >nul

start /B cmd /c "python subject_agents.py english > logs\english.log 2>&1"
echo [5/7] English agent starting on port 8005
timeout /t 2 /nobreak >nul

start /B cmd /c "python subject_agents.py chinese > logs\chinese.log 2>&1"
echo [6/7] Chinese agent starting on port 8006
timeout /t 2 /nobreak >nul

start /B cmd /c "python orchestrator.py > logs\orchestrator.log 2>&1"
echo [7/7] Orchestrator starting on port 8000
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo All services started!
echo.
echo Service URLs:
echo    Orchestrator: http://localhost:8000
echo    Web UI: http://localhost:8000/static/index.html
echo    API Docs: http://localhost:8000/docs
echo.
echo View logs: type logs\*.log
echo Stop services: run stop.bat
echo ========================================
echo.
pause
