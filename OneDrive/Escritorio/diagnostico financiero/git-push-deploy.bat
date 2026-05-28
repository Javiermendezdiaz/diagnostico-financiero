@echo off
cd /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

REM Configurar git user
git config --global user.name "Javier Mendez"
git config --global user.email "javier@mendezconsultoria.com"

REM Verificar estado
echo.
echo Verificando repositorio git...
git status

REM Configurar remote
echo.
echo Configurando remote origin...
git remote remove origin 2>nul
git remote add origin "https://github.com/javiermendez/diagnostico-financiero.git"

REM Renombrar rama a main
echo.
echo Renombrando rama a main...
git branch -M main

REM Push a GitHub
echo.
echo Pushing a GitHub...
git push -u origin main

echo.
echo Completado!
pause
