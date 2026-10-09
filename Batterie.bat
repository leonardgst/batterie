@echo off
cd /d "%~dp0"
uv run batterie
if errorlevel 1 pause
