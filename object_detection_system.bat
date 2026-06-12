@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
  set "PYTHON_BIN=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
  set "PYTHON_BIN=python"
)

"%PYTHON_BIN%" "%SCRIPT_DIR%start.py" %*
endlocal
