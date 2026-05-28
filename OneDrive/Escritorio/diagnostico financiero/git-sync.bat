@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Git Sync Script
echo ========================================
echo.

cd /d "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

echo [1/2] Ejecutando git pull origin main...
echo.
git pull origin main
echo.

echo [2/2] Ejecutando git push origin main...
echo.
git push origin main
echo.

echo ========================================
echo Sincronización completada
echo ========================================
pause
