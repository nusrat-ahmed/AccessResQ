@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PYTHON=py) else (set PYTHON=python)
if not exist .venv (
  %PYTHON% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo For local demo, the app can start now. For deployment, configure secrets in your host settings.
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
