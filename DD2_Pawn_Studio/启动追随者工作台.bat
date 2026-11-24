@echo off
cd /d "%~dp0"
where pythonw.exe >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw.exe "%~dp0pawn_studio.py"
) else (
    python "%~dp0pawn_studio.py"
)
