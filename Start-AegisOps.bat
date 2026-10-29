@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  echo Open http://127.0.0.1:8080 in your browser. Press Ctrl+C to stop.
  py -3 backend\server.py
) else (
  echo Open http://127.0.0.1:8080 in your browser. Press Ctrl+C to stop.
  python backend\server.py
)
pause
