#!/bin/bash

###############################################################################
# GDPR Data Request Application - Development Setup Script
# Initializes PostgreSQL, installs dependencies, and starts the app
###############################################################################

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   GDPR Data Request App - Development Setup                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Node.js version
echo -e "${BLUE}[1/6]${NC} Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js is not installed${NC}"
    echo "Install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v)
echo -e "${GREEN}✓ Found ${NODE_VERSION}${NC}"
echo ""

# Initialize PostgreSQL database
echo -e "${BLUE}[2/6]${NC} Initializing PostgreSQL database..."
if command -v psql &> /dev/null; then
    bash db-init.sh
    echo -e "${GREEN}✓ Database initialized${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL not found, skipping database setup${NC}"
    echo "   Install PostgreSQL first: https://www.postgresql.org/download/"
    echo "   Then run: bash db-init.sh"
fi
echo ""

# Create or update .env file
echo -e "${BLUE}[3/6]${NC} Configuring environment..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
else
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from template${NC}"
        echo -e "${YELLOW}⚠ Review .env and update secrets before deploying${NC}"
    else
        echo -e "${RED}✗ .env.example not found${NC}"
        exit 1
    fi
fi
echo ""

# Install npm dependencies
echo -e "${BLUE}[4/6]${NC} Installing dependencies..."
npm install
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Type checking
echo -e "${BLUE}[5/6]${NC} Running TypeScript type check..."
npm run type-check
echo -e "${GREEN}✓ Type check passed${NC}"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Setup Complete! 🚀                                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo ""
echo "  1. Review .env and update secrets:"
echo "     - JWT_SECRET: change to a long random string"
echo "     - DATABASE_URL: verify PostgreSQL connection string"
echo "     - CORS_ORIGIN: set to your frontend URL"
echo ""
echo "  2. Start the application:"
echo "     npm run dev"
echo ""
echo "  3. The app will run on:"
echo "     - Backend: http://localhost:3001"
echo "     - Frontend: http://localhost:3000"
echo "     - Health check: http://localhost:3001/health"
echo ""
echo "  4. API routes:"
echo "     - POST /api/auth/register - Create new account"
echo "     - POST /api/auth/login - Login"
echo "     - POST /api/requests - Create GDPR request (authenticated)"
echo "     - GET /api/requests - List requests (authenticated)"
echo "     - GET /api/requests/:id - Get request (authenticated)"
echo "     - GET /api/requests/:id/download - Download data ZIP (authenticated)"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo "  - Database: see DATABASE_SETUP.md"
echo "  - Deployment: see DEPLOYMENT.md"
echo "  - API: see backend/routes-requests-db.ts"
echo ""
