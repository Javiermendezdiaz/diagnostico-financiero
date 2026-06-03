@echo off
REM ==================================================================
REM DEPLOYMENT: Diagnóstico Financiero 3-Fase
REM ==================================================================

setlocal enabledelayedexpansion

set DEPLOY_DIR=C:\Users\javie\OneDrive\Escritorio\diagnostico financiero

echo.
echo ================================================================== 
echo DEPLOYMENT: Diagnostico Financiero 3-Fase ^> GitHub + Railway
echo ==================================================================
echo.
echo Working directory: %DEPLOY_DIR%
echo.

cd /d "%DEPLOY_DIR%" || (
    echo ERROR: Cannot access directory
    pause
    exit /b 1
)

REM Check git
git --version >nul 2>&1 || (
    echo ERROR: Git not found. Install from git-scm.com
    pause
    exit /b 1
)

echo [1/3] Adding files...
git add .
if errorlevel 1 (
    echo ERROR: git add failed
    pause
    exit /b 1
)
echo OK

echo [2/3] Committing...
git commit -m "Ready for production"
if errorlevel 1 (
    echo ERROR: git commit failed
    pause
    exit /b 1
)
echo OK

echo [3/3] Pushing to GitHub...
git push origin main
if errorlevel 1 (
    echo ERROR: git push failed. Check GitHub credentials.
    pause
    exit /b 1
)
echo OK

echo.
echo ==================================================================
echo ^✓ DEPLOYMENT SUCCESSFUL
echo ==================================================================
echo.
echo Next steps:
echo   1. Go to railway.app
echo   2. New Project ^> GitHub
echo   3. Select 'diagnostico-financiero' repository
echo   4. Railway auto-deploys (Python/FastAPI detected)
echo.
echo System ready for production. (Press any key to exit)
echo ==================================================================

pause
exit /b 0
