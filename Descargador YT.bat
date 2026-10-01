@echo off
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
start "" pythonw descargador_yt.py
