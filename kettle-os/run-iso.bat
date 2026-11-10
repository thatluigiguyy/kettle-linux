@echo off
rem Double-click me to boot the Kettle Linux desktop ISO
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-iso.ps1"
if errorlevel 1 pause
