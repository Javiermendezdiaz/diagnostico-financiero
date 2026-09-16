@echo off
REM ============================================================
REM  INVENTARIO - solo mide, no toca nada.
REM  Compara TODOS los ficheros de codigo y paginas de esta
REM  carpeta con lo publicado en GitHub. Deja INVENTARIO.txt.
REM ============================================================
setlocal
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set PY=
where python >nul 2>&1 && set PY=python
if "%PY%"=="" (where py >nul 2>&1 && set PY=py)
echo Midiendo... (no se modifica nada)
%PY% inventario.py
echo.
echo   ============================================================
echo    LISTO - abre INVENTARIO.txt
echo   ============================================================
echo.
pause
endlocal
