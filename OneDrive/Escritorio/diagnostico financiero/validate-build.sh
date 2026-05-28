#!/bin/bash
# Validation script for local testing before Render deploy
# Run: bash validate-build.sh

set -e

echo "🔍 Validating Diagnóstico Financiero build..."
echo ""

# Check Node.js
echo "✓ Node.js version:"
node --version || { echo "❌ Node.js not installed"; exit 1; }

# Check Python
echo "✓ Python version:"
python --version || { echo "❌ Python not installed"; exit 1; }

# Check package.json
echo "✓ Checking package.json..."
test -f package.json || { echo "❌ package.json not found"; exit 1; }

# Check vite.config.js
echo "✓ Checking vite.config.js..."
test -f vite.config.js || { echo "❌ vite.config.js not found"; exit 1; }

# Check src files
echo "✓ Checking React source files..."
test -f src/main.jsx || { echo "❌ src/main.jsx not found"; exit 1; }
test -f src/App.jsx || { echo "❌ src/App.jsx not found"; exit 1; }
test -f src/components/QuestionnaireFlow.jsx || { echo "❌ src/components/QuestionnaireFlow.jsx not found"; exit 1; }

# Check Python files
echo "✓ Checking Python backend files..."
test -f app_standalone.py || { echo "❌ app_standalone.py not found"; exit 1; }
test -f diagnostic_engine.py || { echo "❌ diagnostic_engine.py not found"; exit 1; }
test -f diagnostic_report_generator.py || { echo "❌ diagnostic_report_generator.py not found"; exit 1; }
test -f requirements.txt || { echo "❌ requirements.txt not found"; exit 1; }

# Check schema
echo "✓ Checking data schema..."
test -f data-schema-500.json || { echo "❌ data-schema-500.json not found"; exit 1; }

# Check build config
echo "✓ Checking build configuration..."
test -f build.sh || { echo "❌ build.sh not found"; exit 1; }
test -f render.yaml || { echo "❌ render.yaml not found"; exit 1; }

# Check permissions
echo "✓ Checking build.sh permissions..."
test -x build.sh || { echo "❌ build.sh not executable"; exit 1; }

echo ""
echo "✅ All validations passed!"
echo ""
echo "Next steps:"
echo "1. npm install --legacy-peer-deps"
echo "2. npm run build"
echo "3. python app_standalone.py"
echo ""
echo "Then test at http://localhost:8000"
