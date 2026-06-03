@echo off
REM Fix GitHub remote URL and retry push
cd /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

REM Configure git user
echo.
echo Configurando usuario Git...
git config --global user.name "Javier Mendez"
git config --global user.email "javier@mendezconsultoria.com"

REM Remove incorrect remote
echo.
echo Removiendo remote incorrecto...
git remote remove origin 2>nul

REM Add correct remote URL
echo.
echo Agregando remote CORRECTO (javiermendezdiaz)...
git remote add origin "https://github.com/javiermendezdiaz/diagnostico-financiero.git"

REM Ensure main branch
echo.
echo Asegurando rama principal...
git branch -M main

REM Push to GitHub
echo.
echo Pushing a GitHub (remoto CORRECTO)...
git push -u origin main

echo.
echo ✓ Completado!
pause
