#!/bin/bash
set -e

cd "/sessions/ecstatic-hopeful-ptolemy/mnt/diagnostico financiero"

echo "🔍 Git Push - Completo"
echo ""
echo "========================================" 
echo "Configurando Usuario Git"
echo "========================================" 
git config --global user.name "Javier Mendez"
git config --global user.email "javier@mendezconsultoria.com"
echo "✓ Usuario configurado"
echo ""

echo "📊 Estado del Repositorio"
git status
echo ""

echo "📌 Configurando remote origin..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/javiermendez/diagnostico-financiero.git"
echo "✓ Remote agregado"
echo ""

echo "📦 Agregando archivos..."
git add .
echo "✓ Archivos staged"
echo ""

echo "💾 Creando commit inicial..."
git commit -m "Initial commit: Diagnóstico Financiero v6 - React + FastAPI"
echo "✓ Commit creado"
echo ""

echo "🔀 Asegurando rama principal..."
git branch -M main
echo "✓ Rama: main"
echo ""

echo "📤 Pushing a GitHub..."
git push -u origin main
echo ""
echo "========================================"
echo "✅ PUSH COMPLETADO"
echo "========================================"
echo ""
echo "Repositorio: https://github.com/javiermendez/diagnostico-financiero"
echo ""
echo "Próximo paso: Conectar a Render"
echo "1. Ir a: https://dashboard.render.com"
echo "2. Click: New → Web Service"
echo "3. Seleccionar: diagnostico-financiero"
echo "4. Render detectará render.yaml automáticamente"
echo ""
