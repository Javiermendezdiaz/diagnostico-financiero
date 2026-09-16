@echo off
setlocal
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set PY=
where python >nul 2>&1 && set PY=python
if "%PY%"=="" (where py >nul 2>&1 && set PY=py)
echo Leyendo diferencias... (no se modifica nada)
%PY% diferencias.py
echo.
echo   LISTO - abre DIFERENCIAS.txt
echo.
pause
endlocal
