#!/bin/bash
# Automated deployment script for Render.com
# Execute this from your project root: bash deploy.sh

set -e

echo "🚀 Diagnóstico Financiero — Automated Deployment"
echo ""

# ============ STEP 1: Git Setup ============
echo "📦 Step 1: Initializing Git repository..."

if [ -d ".git" ]; then
    echo "   ℹ️  Git repo already exists. Skipping init."
else
    git init
    git config user.email "javier@mendezconsultoria.com"
    git config user.name "Javier Mendez"
    echo "   ✓ Git initialized"
fi

# ============ STEP 2: Add & Commit ============
echo "📝 Step 2: Staging files and committing..."
git add .
git commit -m "Production-ready: React 18 + Vite + FastAPI + Render deployment" || {
    echo "   ℹ️  Nothing to commit (repository already up to date)"
}
echo "   ✓ Committed"

# ============ STEP 3: Set main branch ============
echo "🔀 Step 3: Setting main branch..."
git branch -M main
echo "   ✓ Main branch set"

# ============ STEP 4: GitHub Instructions ============
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 NEXT: Create GitHub Repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Open: https://github.com/new"
echo "2. Repository name: diagnostico-financiero"
echo "3. Set to PUBLIC (important for Render)"
echo "4. Click 'Create repository'"
echo ""
echo "5. Copy the repository URL (https://github.com/YOUR_USERNAME/diagnostico-financiero.git)"
echo ""
echo "6. Run these commands (replace YOUR_USERNAME):"
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/diagnostico-financiero.git"
echo "   git push -u origin main"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 THEN: Connect to Render"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Open: https://dashboard.render.com"
echo "2. Click: 'New' → 'Web Service'"
echo "3. Select: diagnostico-financiero repository"
echo "4. Render auto-detects render.yaml"
echo "5. Confirm settings (should auto-fill):"
echo "   - Build: ./build.sh"
echo "   - Start: python app_standalone.py"
echo "6. Click 'Create Web Service'"
echo ""
echo "✅ Render will build in 3-5 minutes"
echo "✅ Check dashboard for live URL"
echo ""
