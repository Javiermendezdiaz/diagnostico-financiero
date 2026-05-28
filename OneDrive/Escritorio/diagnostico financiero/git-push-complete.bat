@echo off
REM Git Push Complete - with commit
cd /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

REM Configure git user
echo.
echo Configurando usuario Git...
git config --global user.name "Javier Mendez"
git config --global user.email "javier@mendezconsultoria.com"

REM Check status
echo.
echo Verificando estado...
git status

REM Add all files
echo.
echo Agregando archivos...
git add .

REM Create initial commit
echo.
echo Creando commit inicial...
git commit -m "Initial commit: Diagnostico Financiero v6 - React + FastAPI"

REM Configure remote
echo.
echo Configurando remote origin...
git remote remove origin 2>nul
git remote add origin "https://github.com/javiermendez/diagnostico-financiero.git"

REM Rename branch to main
echo.
echo Asegurando rama principal...
git branch -M main

REM Push to GitHub
echo.
echo Pushing a GitHub...
git push -u origin main

echo.
echo ✓ Completado!
pause
