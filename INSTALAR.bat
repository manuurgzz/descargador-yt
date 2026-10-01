@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
where python >nul 2>&1 || (
  echo Instalando Python...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-source-agreements --accept-package-agreements
)
echo Instalando / actualizando yt-dlp...
python -m pip install --upgrade "yt-dlp[default]"
where ffmpeg >nul 2>&1 || winget install -e --id Gyan.FFmpeg --silent --accept-source-agreements --accept-package-agreements
where deno >nul 2>&1 || winget install -e --id DenoLand.Deno --silent --accept-source-agreements --accept-package-agreements
echo.
echo Listo. Abre "Descargador YT.bat".
pause
