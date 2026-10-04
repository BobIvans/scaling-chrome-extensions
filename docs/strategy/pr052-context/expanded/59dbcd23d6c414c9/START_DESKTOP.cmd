@echo off
cd /d "%~dp0"
py -3 app\desktop.py
if errorlevel 1 (
  echo Install Python 3.11+ with Tcl/Tk, then run: py -3 app\desktop.py
  pause
)
