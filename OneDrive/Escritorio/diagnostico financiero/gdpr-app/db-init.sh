#!/bin/bash

###############################################################################
# PostgreSQL Database Initialization Script
# Sets up PostgreSQL for the GDPR Data Request Application
###############################################################################

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   GDPR Data Request App - PostgreSQL Database Setup           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="gdpr_requests"
DB_USER="gdpr_user"
DB_PASSWORD="postgres_password"
DB_HOST="localhost"
DB_PORT="5432"
POSTGRES_USER="postgres"

# Check if PostgreSQL is installed
echo -e "${BLUE}[1/5]${NC} Checking PostgreSQL installation..."
if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL is not installed${NC}"
    echo "Please install PostgreSQL first:"
    echo "  macOS: brew install postgresql"
    echo "  Linux: sudo apt-get install postgresql"
    echo "  Windows: Download from https://www.postgresql.org/download/windows/"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL found${NC}"
echo ""

# Check if PostgreSQL is running
echo -e "${BLUE}[2/5]${NC} Checking PostgreSQL service..."
if ! psql -U $POSTGRES_USER -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
    echo "Start PostgreSQL:"
    echo "  macOS: brew services start postgresql"
    echo "  Linux: sudo systemctl start postgresql"
    echo "  Windows: Start the PostgreSQL service from Services.msc"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is running${NC}"
echo ""

# Create database
echo -e "${BLUE}[3/5]${NC} Creating database and user..."
psql -U $POSTGRES_USER << EOSQL
-- Create database if not exists
CREATE DATABASE $DB_NAME;

-- Create or replace user
DROP USER IF EXISTS $DB_USER;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOSQL

echo -e "${GREEN}✓ Database created${NC}"
echo -e "${GREEN}✓ User created${NC}"
echo ""

# Update .env file
echo -e "${BLUE}[4/5]${NC} Updating .env file..."
if [ -f .env ]; then
    # Update existing .env
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME|g" .env
    rm -f .env.bak
    echo -e "${GREEN}✓ .env updated${NC}"
else
    # Copy from .env.example
    if [ -f .env.example ]; then
        cp .env.example .env
        sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME|g" .env
        rm -f .env.bak
        echo -e "${GREEN}✓ .env created from template${NC}"
    else
        echo -e "${RED}✗ .env.example not found${NC}"
        exit 1
    fi
fi
echo ""

# Run migrations
echo -e "${BLUE}[5/5]${NC} Running database migrations..."

# Check if migrations directory exists
if [ -d "backend/migrations" ]; then
    # Run each migration file
    for migration in backend/migrations/*.sql; do
        if [ -f "$migration" ]; then
            echo "  → Running $(basename $migration)..."
            psql -U $DB_USER -d $DB_NAME -h $DB_HOST < "$migration"
        fi
    done
    echo -e "${GREEN}✓ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠ Migrations directory not found${NC}"
    echo "  Migrations will be run automatically on application startup"
fi
echo ""

# Verification
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   Setup Complete!                                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Database Configuration:${NC}"
echo "  Database:  $DB_NAME"
echo "  User:      $DB_USER"
echo "  Host:      $DB_HOST:$DB_PORT"
echo "  Connection: postgresql://$DB_USER:***@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""

# Test connection
echo "Testing connection..."
if psql -U $DB_USER -d $DB_NAME -h $DB_HOST -c "SELECT NOW();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connection successful${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review the .env file"
    echo "  2. Run: npm install"
    echo "  3. Run: npm run dev"
    echo ""
else
    echo -e "${RED}✗ Connection test failed${NC}"
    echo "Verify that the DATABASE_URL in .env is correct"
    exit 1
fi
