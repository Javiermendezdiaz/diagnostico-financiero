#!/bin/bash
set -e

PROJECT_DIR="/sessions/ecstatic-hopeful-ptolemy/mnt/Escritorio/diagnostico\ financiero"

echo "Changing to project directory..."
cd "$PROJECT_DIR"

echo "Installing npm dependencies..."
npm install --legacy-peer-deps --verbose 2>&1 | tail -100

echo "Building React app with Vite..."
npm run build 2>&1 | tail -50

echo "Build complete!"
ls -la dist/ 2>/dev/null || echo "dist/ folder not found after build"
