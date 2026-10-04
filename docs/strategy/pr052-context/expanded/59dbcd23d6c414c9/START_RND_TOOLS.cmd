@echo off
cd /d "%~dp0"
py -3 app\rnd_tools_ui.py
if errorlevel 1 pause
