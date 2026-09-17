@echo off
REM ============================================================
REM  EL UNICO FICHERO QUE HAY QUE EJECUTAR.
REM  Los demas .bat de esta carpeta son versiones viejas: ignoralos.
REM
REM  Hace todo de una vez:
REM   1) Compara cada fichero con lo publicado en GitHub
REM   2) Comprueba las cifras
REM   3) Compila el informe individual y el de pareja (fuera de OneDrive)
REM   4) Exporta paginas a PNG para revisarlas
REM   5) Deja SUBIR-A-GITHUB con lo que hay que subir
REM ============================================================
setlocal
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set MPLBACKEND=Agg
cd /d "%~dp0"
set ORIGEN=%CD%
set LOG=RESULTADO.txt
if exist "%LOG%" del "%LOG%"

set PY=
where python >nul 2>&1 && set PY=python
if "%PY%"=="" (where py >nul 2>&1 && set PY=py)
if "%PY%"=="" (
  echo X No hay Python instalado. >> "%LOG%"
  goto FIN
)

echo ============================================================ >> "%LOG%"
echo  %DATE% %TIME% >> "%LOG%"
echo ============================================================ >> "%LOG%"

echo [1/5] Comparando con GitHub...
echo. >> "%LOG%"
echo ############ 1) COMPARACION CON GITHUB ############ >> "%LOG%"
git fetch >nul 2>&1
%PY% comparar.py >> "%LOG%" 2>&1

set BUILD=%TEMP%\adapta_run
if exist "%BUILD%" rmdir /s /q "%BUILD%"
mkdir "%BUILD%"
copy /y *.py "%BUILD%\" >nul 2>&1
copy /y *.json "%BUILD%\" >nul 2>&1
if exist fonts robocopy fonts "%BUILD%\fonts" /e /njh /njs /ndl /nc /ns /np >nul 2>&1
if exist static robocopy static "%BUILD%\static" /e /njh /njs /ndl /nc /ns /np >nul 2>&1
copy /y *.png "%BUILD%\" >nul 2>&1
copy /y *.jpg "%BUILD%\" >nul 2>&1
copy /y *.JPG "%BUILD%\" >nul 2>&1

pushd "%BUILD%"
echo [2/5] Comprobando las cifras...
echo. >> "%ORIGEN%\%LOG%"
echo ############ 2) CIFRAS ############ >> "%ORIGEN%\%LOG%"
%PY% test_numeros.py >> "%ORIGEN%\%LOG%" 2>&1

echo [3/5] Compilando el informe individual...
echo. >> "%ORIGEN%\%LOG%"
echo ############ 3) INFORME INDIVIDUAL ############ >> "%ORIGEN%\%LOG%"
%PY% mirar_informe.py >> "%ORIGEN%\%LOG%" 2>&1

echo [4/5] Compilando el informe de pareja...
echo. >> "%ORIGEN%\%LOG%"
echo ############ 4) INFORME DE PAREJA ############ >> "%ORIGEN%\%LOG%"
%PY% probar_pareja.py >> "%ORIGEN%\%LOG%" 2>&1

echo [4b] Probando el rescate de diagnosticos...
echo. >> "%ORIGEN%\%LOG%"
echo ############ 4b) RESCATE (endpoints de administracion) ############ >> "%ORIGEN%\%LOG%"
%PY% -m pip install httpx --quiet >nul 2>&1
%PY% probar_rescate.py >> "%ORIGEN%\%LOG%" 2>&1

echo [5/5] Exportando paginas para revisarlas...
echo. >> "%ORIGEN%\%LOG%"
echo ############ 5) PAGINAS ############ >> "%ORIGEN%\%LOG%"
REM Hasta la 45: las paginas del PLAN llevan listas con vinetas, y hay que poder
REM verlas para confirmar que la vineta se dibuja (Poppins no tiene el triangulito
REM que se usaba antes y se comia en silencio).
%PY% ver_paginas.py INFORME-PRUEBA.pdf 10-20 >> "%ORIGEN%\%LOG%" 2>&1

if exist INFORME-PRUEBA.pdf copy /y INFORME-PRUEBA.pdf "%ORIGEN%\" >nul
if exist INFORME-PAREJA-PRUEBA.pdf copy /y INFORME-PAREJA-PRUEBA.pdf "%ORIGEN%\" >nul
if exist PAGINAS robocopy PAGINAS "%ORIGEN%\PAGINAS" /e /njh /njs /ndl /nc /ns /np >nul 2>&1
popd

echo. >> "%LOG%"
echo ############ FICHEROS PARA SUBIR ############ >> "%LOG%"
if not exist SUBIR-A-GITHUB mkdir SUBIR-A-GITHUB
del /q SUBIR-A-GITHUB\*.* >nul 2>&1
copy /y report_book.py     SUBIR-A-GITHUB\ >nul
copy /y legado_design.py   SUBIR-A-GITHUB\ >nul
copy /y legado_pages.py    SUBIR-A-GITHUB\ >nul
copy /y comparar.py        SUBIR-A-GITHUB\ >nul
copy /y ver_paginas.py     SUBIR-A-GITHUB\ >nul
dir /b SUBIR-A-GITHUB >> "%LOG%" 2>&1

:FIN
echo. >> "%LOG%"
echo ==== FIN ==== >> "%LOG%"
cls
echo.
echo   ============================================================
echo    TERMINADO
echo   ============================================================
echo.
echo    Resultado en RESULTADO.txt
echo    Vuelve a la conversacion y escribe: listo
echo.
pause
endlocal
