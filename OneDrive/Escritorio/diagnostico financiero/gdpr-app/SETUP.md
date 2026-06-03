# GDPR Data Request Application — Setup & Execution Guide

## Project Structure

```
gdpr-app/
├── backend/
│   ├── server.ts              # Express application server
│   ├── routes-requests.ts     # Request detail and download endpoints
│   ├── routes-metrics.ts      # SLA metrics endpoints
│   ├── types.ts               # TypeScript interfaces
│   └── middleware.ts          # JWT authentication middleware
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.tsx      # Dashboard with request list
│   │   │   ├── login.tsx      # Authentication form
│   │   │   ├── create-request.tsx  # GDPR request creation form
│   │   │   └── request/[id].tsx    # Request detail page
│   │   └── styles/
│   │       ├── Login-module.css
│   │       ├── Create-module.css
│   │       └── Request-module.css
│   ├── next.config.js         # Next.js configuration
│   └── tsconfig.json          # TypeScript configuration
├── package.json               # NPM dependencies
├── tsconfig.json              # Root TypeScript configuration
├── .env.example               # Environment variables template
├── SETUP.md                   # This file
└── README.md                  # Application documentation

## Prerequisites

- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher
- **Port availability**: 3000 (frontend), 3001 (backend)

## Installation Steps

### 1. Clone and Navigate
```bash
cd gdpr-app
```

### 2. Environment Setup
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration (JWT_SECRET is critical for production)
nano .env
```

### 3. Install Dependencies
```bash
# Install all project dependencies (both backend and frontend)
npm install
```

### 4. Directory Structure Verification
Ensure the following directories exist:
```bash
mkdir -p frontend/src/pages frontend/src/styles
mkdir -p backend
```

## Development Execution

### Option A: Full-Stack Development (Recommended)
Runs both backend and frontend with hot-reload:
```bash
npm run dev
```

This command:
- Starts backend on `http://localhost:3001`
- Starts frontend on `http://localhost:3000`
- Provides hot-reload for code changes
- Shows both services in parallel terminals

**Expected Output:**
```
> gdpr-data-request-app@1.0.0 dev
> concurrently "npm run dev:backend" "npm run dev:frontend"

[0] [backend] Server is running at http://localhost:3001
[1] [frontend] Ready in 1.2s
[1] [frontend] Local: http://localhost:3000
```

### Option B: Backend Only
```bash
npm run dev:backend
```

Starts Express server at `http://localhost:3001`

### Option C: Frontend Only
```bash
npm run dev:frontend
```

Starts Next.js dev server at `http://localhost:3000`
*Note: Backend must be running separately for API calls to work*

## Testing the Application

### 1. Access the Application
- Open browser: `http://localhost:3000`

### 2. Login with Demo Credentials
- **Email**: user@example.com
- **Password**: user123

*Alternative admin account: admin@example.com / admin123*

### 3. Dashboard
After login, you'll see:
- 3 mock GDPR requests (REQ-2026-001, REQ-2026-002, REQ-2026-003)
- Filter by status (pending, processing, completed)
- View request details
- Download completed request data

### 4. Test Create Request
- Click "New Request" button
- Fill multi-section form with test data
- Submit (currently saves to mock database in memory)

### 5. Test Download
- Click on a completed request (REQ-2026-003)
- Click "Download Data" button
- Receive ZIP file with:
  - `datos-solicitud.json` — Request metadata
  - Category data files with sample information
  - `AVISO-LEGAL.txt` — Spanish legal notice

## API Endpoints

### Authentication
```
POST /api/login
Body: { email: string, password: string }
Response: { token: string, user: { id: string, email: string } }
```

### Requests
```
GET /api/requests          # List requests (requires auth)
GET /api/requests/:id      # Get request detail (requires auth)
POST /api/requests         # Create request (requires auth)
GET /api/requests/:id/download  # Download data as ZIP (requires auth, status must be 'completed')
```

### Metrics
```
GET /api/metrics/sla       # SLA compliance metrics (requires auth)
```

### Health Check
```
GET /api/health            # No auth required
Response: { status: "ok", timestamp: string }
```

## Build and Production

### Build Frontend
```bash
npm run build
```

Generates optimized production build in `frontend/.next`

### Type Checking
```bash
npm run type-check
```

Validates TypeScript without emitting code

### Start Production Server
```bash
npm start
```

Runs compiled backend and serves frontend build

## Configuration Reference

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | 3001 | Backend server port |
| `NODE_ENV` | development | Environment mode |
| `JWT_SECRET` | your-secret-key-change-in-production | JWT signing key (⚠️ change in production) |
| `JWT_EXPIRATION` | 7d | Token validity period |
| `NEXT_PUBLIC_API_URL` | http://localhost:3001 | Frontend API endpoint |
| `GDPR_REQUEST_VALIDITY_DAYS` | 30 | Request validity period |
| `LOG_LEVEL` | info | Logging verbosity |

### Default Demo Users
| Email | Password | Role |
|-------|----------|------|
| user@example.com | user123 | User |
| admin@example.com | admin123 | Admin |

## Mock Database

Currently uses **in-memory Map storage** for requests. Three seed requests available:
- **REQ-2026-001** — Status: processing (5 days old)
- **REQ-2026-002** — Status: pending (recently created)
- **REQ-2026-003** — Status: completed (60 days old, can download)

### Replacing with Real Database
1. Update `routes-requests.ts` to use database queries instead of Map operations
2. Create database migrations
3. Update connection configuration in `.env`

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 3001
lsof -i :3001

# Or use different ports
PORT=3002 npm run dev:backend
```

### API Connection Errors
- Verify backend is running: `http://localhost:3001/api/health`
- Check `NEXT_PUBLIC_API_URL` in `.env`
- Ensure CORS is properly configured in `server.ts`

### TypeScript Errors
```bash
# Run type check to identify issues
npm run type-check
```

### Hot-Reload Not Working
- Restart development server: `npm run dev`
- Check file is in correct directory
- Verify file extension is `.ts` or `.tsx`

## Next Steps for Production

1. **Replace Mock Database**: Implement real database (PostgreSQL recommended)
2. **Environment Secrets**: Use secure secret management (AWS Secrets Manager, etc.)
3. **Email Notifications**: Implement SMTP for request status updates
4. **Rate Limiting**: Add express-rate-limit middleware
5. **Audit Logging**: Log all data access for compliance
6. **Data Encryption**: Encrypt sensitive data at rest
7. **SSL/TLS**: Enable HTTPS in production
8. **Monitoring**: Set up application monitoring and alerting
9. **Testing**: Implement unit and integration tests
10. **CI/CD**: Set up automated deployment pipeline

## Support

For issues or questions:
1. Check logs: `npm run dev` shows all output
2. Verify API response: Use curl or Postman to test endpoints
3. Review TypeScript errors: `npm run type-check`
4. Check environment configuration: Compare `.env` with `.env.example`
