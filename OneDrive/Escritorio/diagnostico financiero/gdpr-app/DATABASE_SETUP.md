# PostgreSQL Database Setup Guide

This document provides instructions for setting up PostgreSQL for the GDPR Data Request Application.

## Prerequisites

- **PostgreSQL 13+** installed and running
- **Node.js 18+** with npm
- **pg** driver (installed via `npm install`)

## Quick Setup

### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download from [postgresql.org](https://www.postgresql.org/download/windows/) and run the installer.

### 2. Create Database and User

Connect to PostgreSQL:
```bash
psql -U postgres
```

Run these commands:
```sql
-- Create database
CREATE DATABASE gdpr_requests;

-- Create application user
CREATE USER gdpr_user WITH PASSWORD 'secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE gdpr_requests TO gdpr_user;

-- Connect to database
\c gdpr_requests

-- Grant schema privileges
GRANT ALL PRIVILEGES ON SCHEMA public TO gdpr_user;
```

Exit psql:
```bash
\q
```

### 3. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Update `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://gdpr_user:secure_password_here@localhost:5432/gdpr_requests
```

### 4. Run Migrations

The application automatically runs migrations on startup, but you can manually trigger them:

```bash
npm run db:migrate
```

### 5. Verify Connection

Test the database connection:
```bash
npm run db:health
```

You should see:
```
[DB] Connection verified: 2026-05-29 10:15:23.456789+00
```

## Manual Database Setup

If automatic migration fails, run migrations manually:

```bash
# Connect to the database
psql -U gdpr_user -d gdpr_requests -h localhost

# Run migration file
\i backend/migrations/001-initial-schema.sql

# Verify tables created
\dt

# Exit
\q
```

## Environment Variables

Essential PostgreSQL variables in `.env`:

```bash
# Basic connection
DATABASE_URL=postgresql://user:password@host:port/database

# Connection pooling
DB_POOL_MIN=2
DB_POOL_MAX=20
DB_IDLE_TIMEOUT=30000
DB_CONNECTION_TIMEOUT=2000
```

## Database Schema

The application creates these tables:

### `requests` table
- `id` (VARCHAR 50, PRIMARY KEY)
- `user_id` (VARCHAR 255)
- `email` (VARCHAR 255)
- `full_name` (VARCHAR 255)
- `status` (VARCHAR 50) - pending, processing, completed, failed, cancelled
- `data_categories` (TEXT array)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `completed_at` (TIMESTAMP, nullable)
- `reason` (TEXT)
- `data_json` (JSONB)

### `audit_logs` table
- `id` (SERIAL, PRIMARY KEY)
- `request_id` (VARCHAR 50, FOREIGN KEY)
- `action` (VARCHAR 100)
- `actor` (VARCHAR 255)
- `details` (TEXT)
- `created_at` (TIMESTAMP)

### `metrics` table
- `id` (SERIAL, PRIMARY KEY)
- `request_id` (VARCHAR 50, FOREIGN KEY)
- `metric_name` (VARCHAR 100)
- `metric_value` (NUMERIC 10,2)
- `recorded_at` (TIMESTAMP)

### `users` table
- `id` (VARCHAR 255, PRIMARY KEY)
- `email` (VARCHAR 255, UNIQUE)
- `password_hash` (VARCHAR 255)
- `full_name` (VARCHAR 255)
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

## Indexes

Automatically created for performance:

```sql
idx_requests_user_id
idx_requests_email
idx_requests_status
idx_requests_created_at
idx_audit_logs_request_id
idx_audit_logs_created_at
idx_audit_logs_action
idx_metrics_request_id
idx_metrics_metric_name
idx_users_email
```

## Backup and Restore

### Backup database

```bash
pg_dump -U gdpr_user -d gdpr_requests > backup.sql
```

### Restore from backup

```bash
psql -U gdpr_user -d gdpr_requests < backup.sql
```

### Full backup (including schema)

```bash
pg_dump -U gdpr_user -d gdpr_requests --create > full_backup.sql
```

## Troubleshooting

### Connection refused
- Ensure PostgreSQL is running: `brew services list` (macOS) or `sudo systemctl status postgresql` (Linux)
- Check DATABASE_URL format
- Verify user credentials

### Table doesn't exist
- Check if migrations ran: `npm run db:status`
- Manually run migrations: `npm run db:migrate`

### Permission denied for schema
- Grant schema privileges: `GRANT ALL PRIVILEGES ON SCHEMA public TO gdpr_user;`

### Connection pool errors
- Increase `DB_POOL_MAX` in `.env`
- Check concurrent connection count: `SELECT count(*) FROM pg_stat_activity;`

## Production Considerations

### Connection Pooling
Use **PgBouncer** for better connection management:

```bash
# Install PgBouncer
brew install pgbouncer  # macOS
sudo apt-get install pgbouncer  # Linux

# Configure pgbouncer.ini
[databases]
gdpr_requests = host=localhost port=5432 dbname=gdpr_requests

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

### Backup Strategy
- Automated daily backups to cloud storage
- Weekly full backups to separate location
- Test restore procedures regularly

### Monitoring
- Monitor slow queries: `log_min_duration_statement = 1000`
- Check index usage: `SELECT * FROM pg_stat_user_indexes`
- Monitor connections: `SELECT * FROM pg_stat_activity`

### SSL/TLS
For production, enable SSL:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
```

## Scripts

Available npm scripts for database management:

```bash
npm run db:migrate       # Run pending migrations
npm run db:status        # Check migration status
npm run db:health        # Test database connection
npm run db:backup        # Create backup
npm run db:reset         # Reset database (DANGER!)
```

## Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Node.js pg driver](https://node-postgres.com/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-security.html)

