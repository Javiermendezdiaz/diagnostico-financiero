# Fase 3 — Integration Testing Guide

## Overview

The integration test suite validates the complete end-to-end GDPR data request workflow, covering all Articles (15, 17, 20) and all critical paths: creation, polling, modal confirmations, auto-download, and analytics.

**Test Coverage:**
- ✓ Request creation (POST /data-requests)
- ✓ Status polling with exponential backoff
- ✓ Modal confirmations (warning for cancel, danger for delete)
- ✓ Auto-download on completion with timestamp filename
- ✓ Analytics event batching (10 events or 30s threshold)
- ✓ Bearer token refresh on 401 Unauthorized
- ✓ Complete end-to-end workflow

## Setup

### 1. Install Testing Dependencies

```bash
npm install --save-dev jest @testing-library/react @testing-library/user-event @testing-library/jest-dom
```

### 2. Jest Configuration (jest.config.js)

```javascript
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  testMatch: ['**/*.test.tsx', '**/*.integration.test.tsx'],
};
```

### 3. Jest Setup (jest.setup.ts)

```typescript
import '@testing-library/jest-dom';

// Mock localStorage
const localStorageMock: Storage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0,
};
global.localStorage = localStorageMock as any;

// Mock fetch globally
global.fetch = jest.fn();

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();
```

## Running Tests

### Run All Integration Tests

```bash
npm test -- DataRights.integration.test.tsx
```

### Run Specific Test Suite

```bash
# Request creation only
npm test -- DataRights.integration.test.tsx -t "Request Creation"

# Status polling only
npm test -- DataRights.integration.test.tsx -t "Status Polling"

# Auto-download only
npm test -- DataRights.integration.test.tsx -t "Auto-Download"

# Modal confirmations only
npm test -- DataRights.integration.test.tsx -t "Modal Confirmations"

# Analytics tracking only
npm test -- DataRights.integration.test.tsx -t "Analytics"

# Auth & token refresh only
npm test -- DataRights.integration.test.tsx -t "Auth & Token Management"

# Complete workflow only
npm test -- DataRights.integration.test.tsx -t "Complete Workflow"
```

### Run with Coverage

```bash
npm test -- DataRights.integration.test.tsx --coverage
```

Expected coverage:
- **DataRequestList.tsx**: 85%+
- **DataRequestRow.tsx**: 90%+
- **ConfirmationModal.tsx**: 95%+
- **useAutoDownload.ts**: 100%
- **useDataRequests.ts**: 85%+
- **analytics.service.ts**: 90%+

## Test Structure

### 1. Request Creation Tests

**File:** `DataRights.integration.test.tsx` → `Request Creation`

**Validates:**
- POST /data-requests with correct request_type (access|deletion|portability)
- Response includes id, status, created_at
- Initial status is 'pending'
- DataRequestRow displays "En espera" badge

**Mocks:**
- `POST /data-requests` → 201 Created with DataRequest object

**Expected Flow:**
```
User clicks "Solicitar acceso" 
  → POST /data-requests (request_type: 'access')
  → 201 response with id, status='pending'
  → UI shows "En espera" badge
```

### 2. Status Polling Tests

**File:** `DataRights.integration.test.tsx` → `Status Polling`

**Validates:**
- GET /data-requests called every 5 seconds
- Exponential backoff on network errors: 1s → 2s → 4s (max 3 attempts)
- Status transitions: pending → processing → completed/rejected
- Polling stops after 24 hours or completion

**Mocks:**
- `GET /data-requests` → 200 OK with request list
- First 2 calls throw network error, 3rd succeeds (backoff test)

**Expected Flow:**
```
ComponentDidMount
  → 5s interval polling via setInterval
  → [pending] → [processing] → [completed]
  → Poll cancellation on completed/rejected
  → Or after 24h (1440 intervals × 5s)
```

### 3. Modal Confirmation Tests

**File:** `DataRights.integration.test.tsx` → `Modal Confirmations`

**Validates:**
- ConfirmationModal appears on cancel button click
- Variant is 'warning' for cancellation, 'danger' for deletion
- Modal title and message are conditional on request_type
- confirmText matches action type
- POST /data-requests/{id}/cancel on "Continuar" click
- Escape key closes modal

**Mocks:**
- `GET /data-requests` → pending/processing requests
- `POST /data-requests/{id}/cancel` → 200 OK

**Expected Flow:**
```
User clicks "Cancelar" button
  → ConfirmationModal opens
  → variant = request_type === 'deletion' ? 'danger' : 'warning'
  → User clicks "Continuar"
  → POST /data-requests/{id}/cancel
  → Modal closes, success message shows
  → Analytics tracks request_cancelled
```

### 4. Auto-Download Tests

**File:** `DataRights.integration.test.tsx` → `Auto-Download`

**Validates:**
- Download triggered when status changes to 'completed'
- Download filename format: `data_export_YYYY-MM-DD_HHMMSS.json`
- One-time download (not repeated on rerenders)
- URL revoked after download (cleanup)

**Mocks:**
- `GET /data-requests` → status='completed' with result_url
- `GET /data-requests/{id}/download` → 200 OK with Blob

**Expected Flow:**
```
Request status becomes 'completed'
  → useAutoDownload hook triggers
  → GET /data-requests/{id}/download
  → Blob received
  → document.createElement('a')
  → link.download = 'data_export_2026-05-29_143050.json'
  → link.click() (silent download)
  → URL.revokeObjectURL(url)
  → Analytics tracks export_downloaded
```

### 5. Analytics Tests

**File:** `DataRights.integration.test.tsx` → `Analytics`

**Validates:**
- Events batched: max 10 events or 30-second timeout
- Correct event types tracked: request_created, request_completed, export_downloaded, request_cancelled, request_failed, error_occurred
- Events include timestamp, user_id (from token), request_id
- POST /api/v1/analytics/events with Bearer token
- Queue flushed on page unload (beforeunload listener)

**Mocks:**
- `POST /api/v1/analytics/events` → 200 OK

**Expected Flow:**
```
User action (create/download/cancel)
  → Analytics.track*(...)
  → Event queued
  → Queue size >= 10 || 30s elapsed
  → POST /api/v1/analytics/events with Bearer token
  → Response 200 → queue cleared
  → Response 401 → re-enqueue to head (retry with refreshed token)
```

### 6. Auth & Token Management Tests

**File:** `DataRights.integration.test.tsx` → `Auth & Token Management`

**Validates:**
- 401 Unauthorized response triggers token refresh
- POST /auth/refresh with refresh_token
- New access_token stored in localStorage
- Original request retried with new Bearer token
- 15-minute expiration (900 seconds)

**Mocks:**
- First request: 401 Unauthorized
- `POST /auth/refresh` → 200 OK with new access_token
- Retry request: 200 OK

**Expected Flow:**
```
GET /data-requests with expired Bearer token
  → 401 Unauthorized
  → POST /auth/refresh with refresh_token
  → 200 OK: access_token='new-token', expires_in=900
  → localStorage.setItem('auth_token', 'new-token')
  → Retry GET /data-requests with new Bearer token
  → 200 OK: request list returned
```

### 7. End-to-End Workflow Test

**File:** `DataRights.integration.test.tsx` → `Complete Workflow`

**Validates:**
- Full lifecycle: create → poll → complete → download → analytics
- All components working together
- Proper event sequencing
- No race conditions

**Mocks:**
- All endpoints (create, list, download, analytics, refresh)

**Expected Sequence:**
```
1. User clicks "Solicitar acceso"
   → request_created event tracked
   
2. Polling begins every 5s
   → request_created event queued
   
3. Status changes to 'completed'
   → request_completed event tracked
   → Auto-download triggered
   → export_downloaded event tracked
   
4. Queue reaches 3+ events or 30s passes
   → POST /api/v1/analytics/events
   → analytics_batched event logged
   
5. Page cleanup
   → beforeunload flushes remaining events
```

## Running Tests in CI/CD

### GitHub Actions Example

```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm ci
      - run: npm test -- DataRights.integration.test.tsx --coverage
      - uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
```

## Debugging Failed Tests

### Check Mock Implementation

```typescript
// In test, log mock calls:
console.log('fetch calls:', global.fetch.mock.calls);

// Or inspect specific calls:
global.fetch.mock.calls.forEach((call, i) => {
  console.log(`Call ${i}:`, call[0], call[1]?.method);
});
```

### Increase Timeout

```typescript
await waitFor(() => {
  expect(screen.getByText(/completed/i)).toBeInTheDocument();
}, { timeout: 10000 }); // 10 seconds instead of default 1000
```

### Verify Component Renders

```typescript
const { debug } = render(<DataRequestList />);
debug(); // Print DOM tree
```

### Check localStorage

```typescript
expect(localStorage.setItem).toHaveBeenCalledWith(
  'auth_token',
  expect.stringContaining('token')
);
```

## Continuous Integration Metrics

Track these metrics in CI/CD:

- **Test Pass Rate**: Target 100%
- **Code Coverage**: Target 85%+
- **Test Duration**: Target <30s for all tests
- **Network Timeout Resilience**: Verify exponential backoff works under simulated latency

## Manual Testing Checklist

Even with automated tests, validate these manually:

- [ ] Create access request → verify "En espera" badge
- [ ] Wait ~5 seconds → verify status polling visible in Network tab
- [ ] Wait for completion → verify auto-download triggers silently
- [ ] Download file → verify filename format `data_export_2026-05-29_HHMMSS.json`
- [ ] Click cancel → verify warning modal appears
- [ ] Cancel deletion request → verify danger (red) modal appears
- [ ] Accept cancellation → verify success message
- [ ] Check Network tab → verify POST /analytics/events batched
- [ ] Simulate 401 → verify token refresh and retry
- [ ] Leave page → verify analytics flush on unload

## Known Issues & Workarounds

### Issue: Timeout in Polling Test

**Symptom:** "Timeout of 1000ms exceeded" waiting for polling

**Root Cause:** setInterval timing in real browser differs from Jest timer mocks

**Workaround:**
```typescript
jest.useFakeTimers();
jest.advanceTimersByTime(5000); // Simulate 5s polling interval
jest.useRealTimers();
```

### Issue: Blob Download Not Triggering

**Symptom:** Auto-download test fails to verify URL.createObjectURL

**Root Cause:** jsdom environment doesn't support real Blob handling

**Workaround:**
```typescript
// Mock the entire download flow:
const mockLink = {
  click: jest.fn(),
  download: '',
  href: '',
};
global.document.createElement = jest.fn((tag) => {
  if (tag === 'a') return mockLink;
  return document.createElement(tag);
});
```

## Success Criteria

All tests pass:
```bash
PASS  DataRights.integration.test.tsx
  DataRights Integration — Request Creation
    ✓ should create access request (Article 15) and set pending status
    ✓ should create deletion request (Article 17) and display danger modal
  DataRights Integration — Status Polling
    ✓ should poll status every 5 seconds until completion
    ✓ should retry with exponential backoff on network error
  DataRights Integration — Modal Confirmations
    ✓ should show cancellation warning modal for pending requests
    ✓ should show deletion danger modal when cancelling deletion request
    ✓ should POST to /data-requests/{id}/cancel on confirmation
  DataRights Integration — Auto-Download
    ✓ should trigger download when request completes
    ✓ should generate timestamp-based filename
  DataRights Integration — Analytics
    ✓ should batch analytics events (max 10 or 30s)
    ✓ should track request_created event on form submission
    ✓ should track request_cancelled event on confirmation
    ✓ should track export_downloaded event on auto-download
  DataRights Integration — Auth & Token Management
    ✓ should refresh token on 401 Unauthorized response
    ✓ should store new token in localStorage after refresh
  DataRights Integration — Complete Workflow
    ✓ should complete full access request lifecycle

Test Suites: 1 passed, 1 total
Tests:       17 passed, 17 total
Coverage:    85.4%
```

