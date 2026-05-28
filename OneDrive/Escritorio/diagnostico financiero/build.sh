#!/bin/bash
set -e

echo "🔨 Building Diagnóstico Financiero..."

# Install Node.js dependencies and build React app
echo "📦 Installing npm dependencies..."
npm install --legacy-peer-deps

echo "🎨 Building React app with Vite..."
npm run build

# Install Python dependencies for FastAPI
echo "🐍 Installing Python dependencies..."
python --version
pip install --upgrade pip setuptools wheel --quiet
pip install --prefer-binary --no-cache-dir -r requirements.txt

echo "✅ Build complete. Frontend: dist/ | Backend: FastAPI ready"
