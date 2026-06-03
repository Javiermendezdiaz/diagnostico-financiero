# Deployment script for Diagnóstico Financiero 3-Fase
# Execute from PowerShell in C:\Users\javie\OneDrive\Escritorio\diagnostico financiero

Set-Location "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

Write-Host "=== DEPLOYMENT: Diagnóstico Financiero 3-Fase ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1] Adding files..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: git add failed" -ForegroundColor Red; exit 1 }

Write-Host "[2] Committing..." -ForegroundColor Yellow
git commit -m "Ready for production"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: git commit failed" -ForegroundColor Red; exit 1 }

Write-Host "[3] Pushing to GitHub..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: git push failed" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "✓ Deployment complete. Next: Connect repository in railway.app" -ForegroundColor Green
Write-Host ""
Write-Host "Railway deployment steps:" -ForegroundColor Cyan
Write-Host "  1. Go to railway.app"
Write-Host "  2. New Project > GitHub"
Write-Host "  3. Select 'diagnostico-financiero' repository"
Write-Host "  4. Railway auto-detects Python/FastAPI and deploys"
