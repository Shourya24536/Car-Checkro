@echo off
echo ==================================================
echo   Starting Diet Coke Can Inspection System
echo ==================================================

:: Run the environment setup first to ensure venv compatibility
python setup_env.py
if %ERRORLEVEL% neq 0 (
    echo Error setting up environment. Exiting...
    pause
    exit /b %ERRORLEVEL%
)

:: Run the main pipeline in simulation mode using the virtual environment
echo.
echo Launching application...
.venv\Scripts\python.exe src\main_gateway.py --url1 simulated --url2 simulated

pause
