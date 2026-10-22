@echo off
REM ---------------------------------------------------------------------------
REM CivicSense launcher. Starts the database (if needed), the API and the web
REM app, then opens the browser.
REM
REM   scripts\run.bat          start everything and open the browser
REM   scripts\run.bat --stop   stop the API and the web app
REM ---------------------------------------------------------------------------
setlocal EnableDelayedExpansion
set ROOT=%~dp0..
set VENV=%ROOT%\.venv\Scripts\python.exe
set API=http://127.0.0.1:8000
set WEB=http://127.0.0.1:5173

if /i "%~1"=="--stop" goto :stop

REM --- 1. database ---------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { Invoke-WebRequest -Uri 'http://127.0.0.1:5432' -TimeoutSec 2 -UseBasicParsing | Out-Null } catch { }" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\local-db.ps1" status >nul 2>&1
if errorlevel 1 (
  echo [1/3] starting PostgreSQL + PostGIS ...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\local-db.ps1" start
) else (
  echo [1/3] database already running
)

REM --- 2. API --------------------------------------------------------------
powershell -NoProfile -Command ^
  "try { (Invoke-WebRequest -Uri '%API%/health' -TimeoutSec 2 -UseBasicParsing) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo [2/3] starting the API on %API%
  start "CivicSense API" cmd /k "cd /d "%ROOT%\backend" && "%VENV%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
  REM give uvicorn time to load the models before the UI talks to it
  powershell -NoProfile -Command ^
    "1..40 | ForEach-Object { Start-Sleep -Milliseconds 500; try { (Invoke-WebRequest -Uri '%API%/health' -TimeoutSec 2 -UseBasicParsing) | Out-Null; exit 0 } catch { } }; exit 1" >nul 2>&1
) else (
  echo [2/3] API already running on %API%
)

REM --- 3. web app ----------------------------------------------------------
powershell -NoProfile -Command ^
  "try { (Invoke-WebRequest -Uri '%WEB%' -TimeoutSec 2 -UseBasicParsing) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo [3/3] starting the web app on %WEB%
  start "CivicSense web" cmd /k "cd /d "%ROOT%\frontend" && npm run dev -- --host 127.0.0.1 --port 5173"
  powershell -NoProfile -Command ^
    "1..40 | ForEach-Object { Start-Sleep -Milliseconds 500; try { (Invoke-WebRequest -Uri '%WEB%' -TimeoutSec 2 -UseBasicParsing) | Out-Null; exit 0 } catch { } }; exit 1" >nul 2>&1
) else (
  echo [3/3] web app already running on %WEB%
)

echo.
echo   Web app   %WEB%
echo   API docs  %API%/docs
echo.
start "" "%WEB%"
endlocal
goto :eof

:stop
echo stopping ...
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn app.main:app|vite' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
echo done
endlocal
goto :eof
