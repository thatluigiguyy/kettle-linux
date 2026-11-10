@echo off
rem Double-click me to build and boot Kettle Linux
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if errorlevel 1 pause
