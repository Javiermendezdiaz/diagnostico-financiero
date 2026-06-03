# Deployment Guide

Complete guide for deploying the GDPR Data Request Application to production.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Database Setup](#database-setup)
3. [Environment Configuration](#environment-configuration)
4. [Server Deployment](#server-deployment)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)

## Pre-Deployment Checklist

- [ ] All tests passing (`npm test`)
- [ ] TypeScript compilation succeeds (`npm run type-check`)
- [ ] Environment variables documented
- [ ] Database migrations tested
- [ ] SSL certificates obtained
- [ ] Backup strategy configured
- [ ] Monitoring tools set up
- [ ] Rate limiting configured
- [ ] CORS origins configured
- [ ] Security headers enabled

## Database Setup

### Production Database

Use a managed PostgreSQL service for reliability:

- **AWS RDS** - Recommended for AWS deployments
- **Google Cloud SQL** - For Google Cloud deployments
- **Azure Database for PostgreSQL** - For Azure deployments
- **DigitalOcean Managed Databases** - For DigitalOcean deployments
- **Heroku Postgres** - For Heroku deployments

### Database Configuration

Create a new database with the following settings:

```sql
-- Create database
CREATE DATABASE gdpr_requests_prod;

-- Create application user
CREATE USER gdpr_prod WITH PASSWORD 'use-a-strong-random-password';

-- Grant minimal required privileges
GRANT CONNECT ON DATABASE gdpr_requests_prod TO gdpr_prod;
GRANT USAGE ON SCHEMA public TO gdpr_prod;
GRANT CREATE ON SCHEMA public TO gdpr_prod;

-- Connect to database
\c gdpr_requests_prod

-- Grant table/sequence privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gdpr_prod;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gdpr_prod;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gdpr_prod;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO gdpr_prod;
```

### Run Migrations

```bash
# Set environment to production
export NODE_ENV=production

# Run migrations
npm run db:migrate
```

## Environment Configuration

### Production .env Variables

```bash
# Server
NODE_ENV=production
PORT=3001

# Security
JWT_SECRET=use-a-very-long-random-string-minimum-32-characters-for-hs256
JWT_EXPIRATION=7d

# Database
DATABASE_URL=postgresql://gdpr_prod:password@db-host.rds.amazonaws.com:5432/gdpr_requests_prod
DB_POOL_MAX=25
DB_IDLE_TIMEOUT=30000
DB_CONNECTION_TIMEOUT=2000

# API & CORS
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
CORS_ORIGIN=https://yourdomain.com

# GDPR
GDPR_REQUEST_VALIDITY_DAYS=30
GDPR_DATA_RETENTION_DAYS=90

# Email Notifications
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=GDPR Requests <noreply@yourdomain.com>

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# Logging
LOG_LEVEL=info
LOG_FORMAT=json

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## Server Deployment

### Using PM2 (Recommended)

1. Install PM2 globally:
```bash
npm install -g pm2
```

2. Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [
    {
      name: 'gdpr-app',
      script: './backend/server.js',
      instances: 'max',
      exec_mode: 'cluster',
      env: {
        NODE_ENV: 'production',
        PORT: 3001,
      },
      error_file: './logs/error.log',
      out_file: './logs/out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
    },
  ],
};
```

3. Start application:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Using Docker (Advanced)

1. Create `Dockerfile`:
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Build frontend
COPY . .
RUN npm run build

# Expose port
EXPOSE 3001

# Start application
CMD ["npm", "start"]
```

2. Build and run:
```bash
docker build -t gdpr-app:latest .
docker run -d \
  --name gdpr-app \
  -p 3001:3001 \
  --env-file .env \
  gdpr-app:latest
```

### Using Heroku

1. Login to Heroku:
```bash
heroku login
```

2. Create app:
```bash
heroku create gdpr-app
```

3. Add PostgreSQL addon:
```bash
heroku addons:create heroku-postgresql:standard-0
```

4. Set environment variables:
```bash
heroku config:set JWT_SECRET=your-secret
heroku config:set NODE_ENV=production
```

5. Deploy:
```bash
git push heroku main
```

## SSL/TLS Configuration

### Using Nginx as Reverse Proxy

1. Install Nginx:
```bash
sudo apt-get install nginx
```

2. Create configuration (`/etc/nginx/sites-available/gdpr-app`):
```nginx
upstream gdpr_backend {
    server localhost:3001;
}

upstream gdpr_frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # API proxy
    location /api {
        proxy_pass http://gdpr_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Frontend proxy
    location / {
        proxy_pass http://gdpr_frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/gdpr-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL Certificate with Let's Encrypt

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

## Monitoring and Maintenance

### Application Monitoring

Use services like:
- **Sentry** - Error tracking
- **DataDog** - Infrastructure monitoring
- **New Relic** - Application performance monitoring

### Database Monitoring

Monitor these metrics:
```bash
# Connection count
SELECT count(*) FROM pg_stat_activity;

# Slow queries (enable in PostgreSQL)
log_min_duration_statement = 1000

# Index usage
SELECT * FROM pg_stat_user_indexes;

# Cache hit ratio
SELECT
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
FROM pg_statio_user_tables;
```

### Automated Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U gdpr_prod gdpr_requests_prod | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Upload to cloud storage
aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://your-backup-bucket/

# Keep only last 30 days
find $BACKUP_DIR -mtime +30 -delete
```

## Troubleshooting

### Application won't start
```bash
# Check logs
pm2 logs gdpr-app

# Verify environment variables
env | grep DATABASE_URL

# Test database connection
npm run db:health
```

### Database connection errors
```bash
# Test connection string
psql -c "SELECT 1" postgresql://user:password@host:5432/database

# Check connection limits
SELECT count(*) FROM pg_stat_activity;
```

### High memory usage
```bash
# Increase memory limits
pm2 start ecosystem.config.js
pm2 kill
pm2 start ecosystem.config.js

# Monitor memory
pm2 monit
```

### SSL certificate issues
```bash
# Verify certificate
openssl s_client -connect yourdomain.com:443

# Check certificate expiration
certbot certificates
```

## Production Checklist

- [ ] Database backed up
- [ ] SSL certificate installed
- [ ] Environment variables set
- [ ] Monitoring configured
- [ ] Log aggregation enabled
- [ ] Rate limiting configured
- [ ] CORS properly restricted
- [ ] Security headers set
- [ ] Database password changed from default
- [ ] Admin user created
- [ ] Health checks configured
- [ ] Backup strategy tested

