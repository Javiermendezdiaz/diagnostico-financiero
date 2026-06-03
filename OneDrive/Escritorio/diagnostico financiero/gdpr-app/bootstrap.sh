#!/bin/bash

# GDPR Data Request App — Bootstrap Script
# Automates initial setup: .env, dependencies, validation

set -e

echo "🚀 GDPR Data Request Application — Bootstrap Setup"
echo "=================================================="
echo ""

# 1. Check Node.js and npm
echo "✓ Checking Node.js and npm..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Install from https://nodejs.org (v18+)"
    exit 1
fi

NODE_VERSION=$(node -v)
NPM_VERSION=$(npm -v)
echo "  Node.js: $NODE_VERSION"
echo "  npm: $NPM_VERSION"
echo ""

# 2. Setup .env file
echo "✓ Setting up environment variables..."
if [ -f .env ]; then
    echo "  .env already exists (skipping)"
else
    cp .env.example .env
    echo "  Created .env from template"
    echo "  ⚠️  Edit .env to customize JWT_SECRET for production"
fi
echo ""

# 3. Install dependencies
echo "✓ Installing npm dependencies..."
npm install
echo ""

# 4. Validation
echo "✓ Validation checks..."
if [ -f package.json ]; then
    echo "  ✓ package.json found"
fi
if [ -f tsconfig.json ]; then
    echo "  ✓ tsconfig.json found"
fi
if [ -f .env ]; then
    echo "  ✓ .env configured"
fi
if [ -d node_modules ]; then
    echo "  ✓ node_modules installed ($(du -sh node_modules | cut -f1))"
fi
echo ""

# 5. Show next steps
echo "=================================================="
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start development servers:"
echo "     npm run dev"
echo ""
echo "  2. Open browser:"
echo "     http://localhost:3000"
echo ""
echo "  3. Login with demo credentials:"
echo "     Email: user@example.com"
echo "     Password: user123"
echo ""
echo "For detailed setup instructions, see SETUP.md"
echo "For API documentation, see README.md"
echo ""
