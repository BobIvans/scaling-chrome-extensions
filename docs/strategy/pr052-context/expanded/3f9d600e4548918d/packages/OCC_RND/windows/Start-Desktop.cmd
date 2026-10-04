@echo off
python "%~dp0..\tools\desktop_archive.py"
if errorlevel 1 pause
