@echo off
setlocal

set PYFINS_REPO=git+https://github.com/reynoldxu/pyfins.git

echo Installing pyfins from GitHub...

where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    if "%UV_CACHE_DIR%"=="" set UV_CACHE_DIR=.uv-cache
    uv pip install "%PYFINS_REPO%"
) else (
    python -m pip install "%PYFINS_REPO%"
)

python -c "import importlib, importlib.util, sys; names=('pyfins','fins'); found=next((n for n in names if importlib.util.find_spec(n)), None); print('Installed module import OK: ' + found + ' -> ' + str(importlib.import_module(found))) if found else sys.exit('pyfins install finished, but neither pyfins nor fins could be imported.')"

if %ERRORLEVEL% NEQ 0 (
    echo pyfins installation check failed.
    exit /b %ERRORLEVEL%
)

echo pyfins installation check finished.
endlocal
