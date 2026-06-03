# GDPR Application — Architectural Audit & Roadmap

**Date**: 2026-05-29  
**Status**: MVP Core Complete + Email Integration Ready (with fixes)  
**Architecture**: Express.js/PostgreSQL + Next.js 14

---

## 1. IMPLEMENTATION STATUS

### ✅ COMPLETE
- **User Authentication**: JWT-based login/register with token persistence
- **GDPR Request Lifecycle**: Create, read, update status, track expiration (30 days)
- **Data Download**: ZIP export with structured JSON + sample data + Spanish legal notice
- **Email Service**: Nodemailer integration written (welcome + status change notifications)
- **Audit Logging**: Request/status changes logged with timestamp + author
- **Rate Limiting**: 100 req/15min per IP configured
- **CORS/Security**: Credential-aware CORS, rate limiting, environment-driven config
- **Frontend UI**: Home, login, register, requests list, request detail, download pages (all Spanish)
- **API Client**: Full TokenManager + authApi + requestsApi integration

### ⚠️ CRITICAL BLOCKERS (Must fix before testing)

#### 1. **Status Enum Mismatch**
- **Frontend**: `'pending' | 'processing' | 'ready' | 'completed' | 'rejected'`
- **Backend**: `'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'`
- **Impact**: Frontend will fail to map backend status values to UI labels/colors
- **Fix**: Standardize on backend enums and update frontend interfaces

#### 2. **Missing Nodemailer Dependency**
- **Package.json**: No `nodemailer` or `@types/nodemailer`
- **Impact**: Email service will crash at runtime (require not found)
- **Fix**: Add `"nodemailer": "^6.9.7"` and `"@types/nodemailer": "^6.4.14"` to dependencies

#### 3. **Database Configuration Uncertainty**
- **SETUP.md states**: "Currently uses in-memory Map storage"
- **But**: `database.ts` has PostgreSQL pool, `migrations-runner.ts` exists
- **Actual status**: Unknown if migrations are created/executable
- **Fix**: Verify migrations are created and database is seeded before testing

### ⚠️ INCOMPLETE FEATURES

#### 4. **SMTP Configuration Not Validated**
- `.env.example` has `SMTP_ENABLED=false`
- **Problem**: Email service reads SMTP_ENABLED but doesn't validate config at startup
- **Risk**: Silent failures (emails won't send but no error thrown)
- **Fix**: Add startup validation of SMTP credentials when SMTP_ENABLED=true

#### 5. **No Request Expiration Cleanup**
- Requests have 30-day validity, but no cron job deletes/archives expired requests
- **Compliance Risk**: Could violate data retention policy if expired data not cleaned
- **Fix**: Add background job to archive requests after 30 days

#### 6. **Breach Notification Protocol Missing**
- GDPR Article 33-34 requires breach notification within 72 hours
- **Current state**: No code for managing data breaches
- **Fix**: Add breach logging + automated notification endpoint

#### 7. **Admin Dashboard Not Built**
- No way for admin to view/manage all requests, see patterns, trigger status changes
- **Workaround**: Can trigger via raw API calls, but not production-ready
- **Fix**: Build admin interface (separate routes + frontend pages)

#### 8. **No End-to-End Test Suite**
- Created features but no automated test coverage
- **Risk**: Regression bugs on next changes
- **Fix**: Add Jest tests for API + integration tests with real DB

---

## 2. CRITICAL PATH TO PRODUCTION

### Phase 0: Fix Blockers (1-2 hours)
```
Priority 1: Status Enum Mismatch
  - Standardize on: pending → processing → completed
  - Add: 'failed' | 'cancelled' as terminal states (optional, keep both)
  - Update frontend interfaces in lib/api.ts + all components
  - Update backend routes to return consistent enum

Priority 2: Add Nodemailer + SMTP Validation
  - npm install nodemailer @types/nodemailer
  - Add startup check in server.ts:
    if (process.env.SMTP_ENABLED === 'true') {
      validateSMTPConfig();
    }
  - Test email delivery with real Gmail/SendGrid account

Priority 3: Verify Database + Migrations
  - Confirm PostgreSQL running locally/Docker
  - Run migrations-runner
  - Seed test users (user@example.com, admin@example.com)
```

### Phase 1: E2E Testing (2-3 hours)
```
1. User Registration → Welcome email delivery
2. Create GDPR request → Stored in DB with correct status
3. Update status → Status change email sent + stored
4. Download request → ZIP generated with correct structure
5. Token expiration → Redirects to /login
6. Rate limiting → 101st request returns 429
```

### Phase 2: Production Hardening (4-6 hours)
```
1. Request expiration cleanup cron job
2. SMTP error handling + retry logic
3. Audit log retention policy
4. Admin dashboard (basic: list requests, filter by status, resend emails)
5. Database backup automation
6. Error logging to centralized system (Sentry optional)
```

### Phase 3: GDPR Compliance (8-10 hours)
```
1. Breach notification protocol
2. Right to be forgotten (data deletion endpoint)
3. Data portability improvements (multiple formats: JSON, CSV, PDF)
4. Consent management UI + withdrawal
5. Privacy policy & legal notice improvements
6. Audit trail export (for compliance review)
```

---

## 3. ARCHITECTURE OVERVIEW

### Backend Stack
```
Express.js 4 (HTTP server)
  ├── JWT Middleware (authentication)
  ├── Rate Limiter (100 req/15min)
  ├── CORS (credentials: true)
  ├── Routes
  │   ├── POST /api/auth/register → sendWelcomeEmail()
  │   ├── POST /api/auth/login
  │   ├── GET /api/requests (list)
  │   ├── GET /api/requests/:id
  │   ├── POST /api/requests (create)
  │   ├── PATCH /api/requests/:id/status → sendStatusChangeNotification()
  │   ├── GET /api/requests/:id/download (ZIP export)
  │   └── GET /health
  ├── Services
  │   ├── EmailService (Nodemailer)
  │   ├── AuthService (JWT + password hash)
  │   ├── RequestService (CRUD)
  │   └── AuditService (logging)
  └── Database (PostgreSQL with connection pool)

Frontend Stack
  └── Next.js 14 App Router (TypeScript)
      ├── Pages
      │   ├── / (home → login if not authenticated)
      │   ├── /login
      │   ├── /register
      │   ├── /requests (list)
      │   └── /requests/[id] (detail + download)
      ├── lib/api.ts (TokenManager + authApi + requestsApi)
      └── Middleware (session validation)
```

### Data Flow
```
User Registration
  → POST /api/auth/register
  → createUser() in database
  → generateJWT()
  → emailService.sendWelcomeEmail(user)
  → return token + user data
  → Frontend stores in localStorage

GDPR Request Created
  → POST /api/requests
  → createRequest() in database
  → logAudit('request_created')
  → return request with status='pending'

Status Update
  → PATCH /api/requests/:id/status
  → updateRequestStatus()
  → logAudit('status_changed')
  → emailService.sendStatusChangeNotification()
  → return updated request
```

---

## 4. KNOWN GAPS & RECOMMENDATIONS

| Gap | Severity | Workaround | Timeline |
|-----|----------|-----------|----------|
| Status enum mismatch | CRITICAL | Fix before any testing | Phase 0 |
| Nodemailer missing | CRITICAL | npm install before running | Phase 0 |
| No SMTP validation | HIGH | Manual env check before deploy | Phase 1 |
| No expiration cleanup | HIGH | Manual archive job setup | Phase 2 |
| No admin dashboard | MEDIUM | Use API directly for testing | Phase 2 |
| No test suite | MEDIUM | Manual E2E testing | Phase 1 |
| No breach protocol | MEDIUM | Add in Phase 3 | Phase 3 |
| No data deletion endpoint | MEDIUM | Add in Phase 3 | Phase 3 |

---

## 5. IMMEDIATE NEXT STEPS

**Priority 1 (do now):**
1. Add nodemailer to package.json + install
2. Fix status enum mismatch (update both BE + FE)
3. Verify PostgreSQL is running + migrations can execute
4. Configure real SMTP credentials (Gmail App Password or SendGrid)

**Priority 2 (within 2 hours):**
1. Run full E2E test: register → welcome email → create request → status change email → download
2. Verify email templates render correctly with real data
3. Test token expiration + rate limiting

**Priority 3 (before production):**
1. Add request expiration cleanup cron job
2. Build basic admin dashboard for status management
3. Add comprehensive error handling + logging
4. Deploy to staging environment with real database

---

## 6. FILE CHECKLIST

✅ **Frontend Complete**
- [ ] `frontend/app/page.tsx` (home)
- [ ] `frontend/app/login/page.tsx`
- [ ] `frontend/app/register/page.tsx`
- [ ] `frontend/app/requests/page.tsx` (list)
- [ ] `frontend/app/requests/[id]/page.tsx` (detail)
- [ ] `frontend/lib/api.ts` (API client)
- [ ] `frontend/middleware.ts` (session)

✅ **Backend Core Complete**
- [ ] `backend/server.ts` (main server)
- [ ] `backend/routes-requests-db.ts` (GDPR endpoints)
- [ ] `backend/services-auth.ts` (auth logic)
- [ ] `backend/services-email.ts` (Nodemailer integration)
- [ ] `backend/services-requests-db.ts` (DB layer)
- [ ] `backend/services-audit.ts` (logging)
- [ ] `backend/database.ts` (pool + queries)
- [ ] `backend/migrations-runner.ts` (schema setup)

❓ **Database** (Status unclear)
- [ ] SQL migrations (must exist and be executable)
- [ ] User table with email + password hash
- [ ] GDPR request table with lifecycle columns
- [ ] Audit log table

---

## 7. PRODUCTION CHECKLIST

- [ ] Nodemailer dependency installed + tested
- [ ] Status enum synchronized (BE ↔ FE)
- [ ] PostgreSQL running with migrations executed
- [ ] SMTP credentials configured (not hardcoded)
- [ ] JWT_SECRET changed from default
- [ ] CORS_ORIGIN updated for production domain
- [ ] Rate limiting tuned for expected load
- [ ] Audit logs being written and rotated
- [ ] Email templates tested with real data
- [ ] Token expiration cleanup cron running
- [ ] Admin dashboard functional
- [ ] End-to-end tests passing
- [ ] Error monitoring (Sentry) configured
- [ ] Database backups automated

---

**Status**: Ready to execute Phase 0 fixes → then full E2E testing → then production hardening.
