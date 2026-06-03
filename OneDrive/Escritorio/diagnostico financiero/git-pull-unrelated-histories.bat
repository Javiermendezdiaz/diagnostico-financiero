@echo off
REM Git Pull + Push - Resolver conflicto de historias no relacionadas
cd /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

REM Configurar usuario git
echo.
echo Configurando usuario Git...
git config --global user.name "Javier Mendez"
git config --global user.email "javier@mendezconsultoria.com"

REM Ver estado actual
echo.
echo Verificando estado actual...
git status

REM Pull remoto para sincronizar (permitiendo historias no relacionadas)
echo.
echo Sincronizando con repositorio remoto (permitiendo historias divergentes)...
git pull origin main --allow-unrelated-histories --no-edit

REM Push a GitHub
echo.
echo Pushing a GitHub...
git push -u origin main

echo.
echo ✓ Completado!
pause
