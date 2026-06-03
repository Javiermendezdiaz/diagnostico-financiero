#!/bin/bash

# Fase 3 Integration Test Execution Script
# Execute comprehensive validation of GDPR request workflows

echo "=========================================="
echo "Fase 3 — GDPR Data Requests Integration Tests"
echo "=========================================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install --save-dev jest @testing-library/react @testing-library/user-event @testing-library/jest-dom identity-obj-proxy
fi

# Create Jest configuration if not exists
if [ ! -f "jest.config.js" ]; then
    echo "Creating jest.config.js..."
    cat > jest.config.js << 'JEST_CONFIG'
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  testMatch: ['**/*.test.tsx', '**/*.integration.test.tsx'],
  collectCoverageFrom: [
    '**/*.tsx',
    '**/*.ts',
    '!**/*.d.ts',
    '!**/node_modules/**',
  ],
};
JEST_CONFIG
fi

if [ ! -f "jest.setup.ts" ]; then
    echo "Creating jest.setup.ts..."
    cat > jest.setup.ts << 'JEST_SETUP'
import '@testing-library/jest-dom';

const localStorageMock: Storage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0,
};
global.localStorage = localStorageMock as any;
global.fetch = jest.fn();
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();
JEST_SETUP
fi

echo ""
echo "Test Suite Options:"
echo "===================="
echo "1. Run all tests"
echo "2. Run request creation tests"
echo "3. Run status polling tests"
echo "4. Run modal confirmation tests"
echo "5. Run auto-download tests"
echo "6. Run analytics tests"
echo "7. Run auth & token tests"
echo "8. Run end-to-end workflow test"
echo "9. Run with coverage report"
echo "0. Exit"
echo ""
read -p "Select option (0-9): " option

case $option in
    1)
        echo "Running all integration tests..."
        npm test -- DataRights.integration.test.tsx
        ;;
    2)
        echo "Running request creation tests..."
        npm test -- DataRights.integration.test.tsx -t "Request Creation"
        ;;
    3)
        echo "Running status polling tests..."
        npm test -- DataRights.integration.test.tsx -t "Status Polling"
        ;;
    4)
        echo "Running modal confirmation tests..."
        npm test -- DataRights.integration.test.tsx -t "Modal Confirmations"
        ;;
    5)
        echo "Running auto-download tests..."
        npm test -- DataRights.integration.test.tsx -t "Auto-Download"
        ;;
    6)
        echo "Running analytics tests..."
        npm test -- DataRights.integration.test.tsx -t "Analytics"
        ;;
    7)
        echo "Running auth & token management tests..."
        npm test -- DataRights.integration.test.tsx -t "Auth & Token Management"
        ;;
    8)
        echo "Running end-to-end workflow test..."
        npm test -- DataRights.integration.test.tsx -t "Complete Workflow"
        ;;
    9)
        echo "Running all tests with coverage report..."
        npm test -- DataRights.integration.test.tsx --coverage
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Test execution completed"
echo "=========================================="
