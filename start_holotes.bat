@echo off
setlocal
pushd "%~dp0"

title Holotes Launcher

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] Virtual environment was not found:
    echo %PYTHON%
    echo.
    echo Create it and install dependencies:
    echo   py -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    popd
    exit /b 1
)

if not exist "%~dp0app.py" (
    echo [ERROR] app.py was not found.
    echo Put this BAT file in the Holotes project root.
    pause
    popd
    exit /b 1
)

if not exist "%~dp0run_holotes.py" (
    echo [ERROR] run_holotes.py was not found.
    echo Put this BAT file in the Holotes project root.
    pause
    popd
    exit /b 1
)

set "MODE=%~1"

if "%MODE%"=="" (
    echo.
    echo ==============================
    echo        Holotes Launcher
    echo ==============================
    echo.
    echo Press ENTER to start Web + Bot
    echo 1 - Start Web only
    echo 2 - Start Bot only
    echo.
    set /p "MODE=Select mode: "
)

if "%MODE%"=="" goto BOTH
if "%MODE%"=="0" goto BOTH
if "%MODE%"=="1" goto WEB
if "%MODE%"=="2" goto BOT

echo.
echo [ERROR] Unknown mode: %MODE%
echo Use:
echo   start_holotes.bat
echo   start_holotes.bat 1
echo   start_holotes.bat 2
echo.
pause
popd
exit /b 2

:BOTH
echo.
echo Starting Holotes Web + Telegram Bot...
echo Press Ctrl+C to stop both services.
echo.
"%PYTHON%" "%~dp0run_holotes.py"
set "EXIT_CODE=%ERRORLEVEL%"
goto END

:WEB
echo.
echo Starting Holotes Web...
echo Press Ctrl+C to stop.
echo.
"%PYTHON%" -m streamlit run "%~dp0app.py"
set "EXIT_CODE=%ERRORLEVEL%"
goto END

:BOT
echo.
echo Starting Holotes Telegram Bot...
echo Press Ctrl+C to stop.
echo.
"%PYTHON%" -m src.telegram_bot
set "EXIT_CODE=%ERRORLEVEL%"
goto END

:END
echo.
if not "%EXIT_CODE%"=="0" (
    echo Holotes stopped with exit code %EXIT_CODE%.
    pause
)

popd
exit /b %EXIT_CODE%
