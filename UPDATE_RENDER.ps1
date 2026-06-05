# Script para actualizar main_production_ready.py en Render
# Ejecutar en PowerShell en la carpeta del repositorio

Write-Host "🔧 Iniciando actualización de Render..." -ForegroundColor Cyan

# 1. Verificar que estamos en el repositorio
if (-not (Test-Path ".git")) {
    Write-Host "❌ No estamos en un repositorio Git" -ForegroundColor Red
    exit 1
}

# 2. Actualizar archivo local (si existe)
if (Test-Path "main_production_ready.py") {
    Write-Host "✅ Archivo encontrado" -ForegroundColor Green
} else {
    Write-Host "⚠️ main_production_ready.py no encontrado. Necesitas actualizarlo manualmente en Render" -ForegroundColor Yellow
}

# 3. Hacer commit de los cambios
Write-Host "📤 Commiteando cambios..." -ForegroundColor Cyan
git add -A
git commit -m "🔧 HOTFIX: Endpoint GET /question/first - Devuelve siguiente pregunta sin responder basado en progreso real"

# 4. Push a GitHub
Write-Host "🚀 Pusheando a GitHub..." -ForegroundColor Cyan
git push origin main

Write-Host "✅ Cambios pusheados. Render se redeploya automáticamente en 1-2 minutos" -ForegroundColor Green
Write-Host "⏳ Espera a que Render termine el deploy antes de probar" -ForegroundColor Yellow
