@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
  echo Git is required. Install Git for Windows and reopen this launcher.
  pause
  exit /b 1
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys, tkinter; assert sys.version_info >= (3, 11), 'Python 3.11+ required'" >nul 2>nul
  if not errorlevel 1 (
    py -3 app.py
    if errorlevel 1 pause
    exit /b
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys, tkinter; assert sys.version_info >= (3, 11), 'Python 3.11+ required'" >nul 2>nul
  if not errorlevel 1 (
    python app.py
    if errorlevel 1 pause
    exit /b
  )
)
echo Python 3.11+ with Tkinter is required. No packages are installed by this launcher.
echo Install Python with Tcl/Tk support, then open Launch_Windows.cmd again.
pause
exit /b 1
