#!/usr/bin/env pwsh
<#
.SYNOPSIS
Auto-detect GitHub username and push to GitHub
#>

$ErrorActionPreference = "Stop"

Write-Host "🔍 Detectando GitHub username..." -ForegroundColor Cyan

# Intento 1: Buscar en git config global
try {
    $username = git config --global user.github 2>$null
    if ($username) {
        Write-Host "✓ Username detectado en git config: $username" -ForegroundColor Green
    }
} catch {}

# Intento 2: Si está instalado GitHub CLI, usarlo
if (-not $username) {
    try {
        $username = & gh api user -q '.login' 2>$null
        if ($username) {
            Write-Host "✓ Username detectado con GitHub CLI: $username" -ForegroundColor Green
        }
    } catch {}
}

# Intento 3: Leer del archivo de perfil de VS Code si existe
if (-not $username) {
    $vscodeSettings = "$env:APPDATA\Code\User\settings.json"
    if (Test-Path $vscodeSettings) {
        try {
            $content = Get-Content $vscodeSettings -Raw | ConvertFrom-Json
            if ($content."github.username") {
                $username = $content."github.username"
                Write-Host "✓ Username detectado en VS Code settings: $username" -ForegroundColor Green
            }
        } catch {}
    }
}

# Si no se encontró, pedir al usuario
if (-not $username) {
    Write-Host "No se pudo detectar username automáticamente." -ForegroundColor Yellow
    $username = Read-Host "Ingresa tu GitHub username (ej: javierMendez)"
}

if (-not $username -or $username -eq "") {
    Write-Host "❌ Username no proporcionado. Abortando." -ForegroundColor Red
    exit 1
}

# Mostrar confirmación
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GitHub Push Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Username: $username" -ForegroundColor White
Write-Host "Repository: diagnostico-financiero" -ForegroundColor White
Write-Host "URL: https://github.com/$username/diagnostico-financiero.git" -ForegroundColor White
Write-Host ""

# Verificar que estamos en el directorio correcto
$currentDir = Get-Location
if (-not (Test-Path ".git")) {
    Write-Host "❌ No estamos en un repositorio git. Abortando." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Repositorio git detectado en: $currentDir" -ForegroundColor Green
Write-Host ""

# Agregar remote
Write-Host "📌 Configurando remote origin..." -ForegroundColor Cyan
try {
    git remote remove origin 2>$null
} catch {}

git remote add origin "https://github.com/$username/diagnostico-financiero.git"
Write-Host "✓ Remote agregado" -ForegroundColor Green

# Renombrar rama a main
Write-Host "🔀 Asegurando rama principal..." -ForegroundColor Cyan
git branch -M main
Write-Host "✓ Rama: main" -ForegroundColor Green

# Push a GitHub
Write-Host ""
Write-Host "📤 Pushing a GitHub..." -ForegroundColor Cyan
try {
    git push -u origin main
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ PUSH COMPLETADO" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Repositorio: https://github.com/$username/diagnostico-financiero" -ForegroundColor White
    Write-Host ""
    Write-Host "Próximo paso: Conectar a Render" -ForegroundColor Cyan
    Write-Host "1. Ir a: https://dashboard.render.com" -ForegroundColor White
    Write-Host "2. Click: New → Web Service" -ForegroundColor White
    Write-Host "3. Seleccionar: diagnostico-financiero" -ForegroundColor White
    Write-Host "4. Render detectará render.yaml automáticamente" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "❌ Error durante push: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "⚠️  Asegúrate de que:" -ForegroundColor Yellow
    Write-Host "1. El repositorio existe en GitHub: https://github.com/$username/diagnostico-financiero" -ForegroundColor White
    Write-Host "2. Tienes permiso de push" -ForegroundColor White
    Write-Host "3. Tu SSH key o token está configurado" -ForegroundColor White
    exit 1
}

Write-Host "Presiona Enter para cerrar..." -ForegroundColor Gray
Read-Host
