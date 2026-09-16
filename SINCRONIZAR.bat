@echo off
REM ============================================================
REM  SINCRONIZAR - trae de GitHub las paginas desfasadas.
REM  Hace COPIA DE SEGURIDAD de las tuyas antes de tocarlas.
REM  NO toca inicio.html.
REM ============================================================
setlocal
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
set PY=
where python >nul 2>&1 && set PY=python
if "%PY%"=="" (where py >nul 2>&1 && set PY=py)
%PY% sincronizar.py > RESULTADO-SINCRONIZAR.txt 2>&1
type RESULTADO-SINCRONIZAR.txt
echo.
echo   ============================================================
echo    LISTO - detalle en RESULTADO-SINCRONIZAR.txt
echo   ============================================================
echo.
pause
endlocal
