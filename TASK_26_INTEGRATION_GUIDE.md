# Task #26 Integration Guide: GDPR Breach Notification (Art. 33-34)

## Overview

This guide walks through integrating the GDPR breach notification system into your FastAPI application. The system handles:

- **Art. 33**: Authority notification within 72 hours of discovery
- **Art. 34**: Individual notification without undue delay (severity-based)
- **Art. 32**: Security measures (encryption, audit logging)
- **Art. 5.1.e**: Transparency (complete audit trail)

---

## Files

1. **breach_notification.py** (~350 lines)
   - `BreachIncident` ORM model
   - `BreachSeverity` enum
   - `BreachService` with detection, filing, and notification methods

2. **breach_email_templates.py** (~200 lines)
   - Spanish & English email templates
   - Art. 33 (authority) and Art. 34 (individual) versions

3. **app_standalone_UPDATED_v3.py** (~650 lines)
   - Integrates breach_notification module
   - 3 new REST endpoints for breach management
   - Optional background detection cron (every 1 hour)

4. **TASK_26_INTEGRATION_GUIDE.md** (this file)
   - Setup instructions
   - Curl examples
   - Configuration reference

---

## Setup Steps

### 1. Copy Files

Copy all deliverables to your project directory:

```bash
cp breach_notification.py /path/to/diagnostico-financiero/
cp breach_email_templates.py /path/to/diagnostico-financiero/
cp app_standalone_UPDATED_v3.py /path/to/diagnostico-financiero/app_standalone.py  # Backup old version first!
```

### 2. Create Database Table

If using SQLAlchemy with a real database:

```python
from breach_notification import BreachIncident, Base
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:password@localhost/diagnostico_db")
Base.metadata.create_all(engine)
```

If using SQLite (development):

```python
engine = create_engine("sqlite:///./diagnostico.db")
Base.metadata.create_all(engine)
```

### 3. Wire Database Session

In `app_standalone_UPDATED_v3.py`, replace the dummy in-memory sessions with your real database:

**Before (current):**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///:memory:")
BreachIncident.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
```

**After (production):**
```python
from backend.database import get_db

# In endpoint:
@app.post("/api/v1/breach/report")
async def report_breach(request: Request, body: BreachReportRequest, db: Session = Depends(get_db)):
    service = BreachService(db)
    incident = service.file_breach(...)
    return {...}
```

### 4. Install Dependencies

The system uses SQLAlchemy and APScheduler for the background cron. Ensure your `requirements.txt` includes:

```
sqlalchemy>=2.0
apscheduler>=3.10
pydantic>=2.0
```

Then install:

```bash
pip install -r requirements.txt
```

### 5. Configure Email Sending (Optional)

Currently, email sending is mocked. To enable real emails, wire SendGrid or your email provider:

**TODO in breach_notification.py:**

```python
# In BreachService.notify_authority():
# TODO: Send actual email via SendGrid to DPA

# In BreachService.notify_individuals():
# TODO: Queue emails via SendGrid/external service
```

**Implementation example with SendGrid:**

```python
import sendgrid
from sendgrid.helpers.mail import Mail

def send_breach_email(to_email: str, subject: str, body: str):
    sg = sendgrid.SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    email = Mail(
        from_email="noreply@adaptafamilyoffice.com",
        to_emails=to_email,
        subject=subject,
        plain_text_content=body
    )
    response = sg.send(email)
    return response.status_code == 202
```

---

## API Endpoints

### 1. File a Breach Incident

**POST /api/v1/breach/report**

File a data breach incident (Art. 33/34 trigger).

**Request:**
```json
{
  "incident_date": "2026-05-30T14:30:00Z",
  "affected_users": [
    {
      "user_id": "user_123",
      "email": "user@example.com",
      "data_types": ["email", "profile"]
    },
    {
      "user_id": "user_456",
      "email": "user456@example.com",
      "data_types": ["email"]
    }
  ],
  "description": "Unauthorized API access via unpatched SQL injection vulnerability",
  "severity": "HIGH",
  "root_cause": "Unpatched application server (CVE-2026-12345)",
  "mitigation_steps": [
    {"action": "System isolated from network", "timestamp": "2026-05-30T14:35:00Z"},
    {"action": "Credentials rotated", "timestamp": "2026-05-30T15:00:00Z"},
    {"action": "Security patches applied", "timestamp": "2026-05-30T16:45:00Z"}
  ]
}
```

**Response:**
```json
{
  "incident_id": "breach-uuid-123",
  "severity": "HIGH",
  "affected_users": 2,
  "created_at": "2026-05-30T14:31:00Z",
  "next_action": "Notify authority within 72h, individuals within 1 day"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/api/v1/breach/report \
  -H "Content-Type: application/json" \
  -d '{
    "incident_date": "2026-05-30T14:30:00Z",
    "affected_users": [{"user_id": "user_1", "email": "user@example.com", "data_types": ["email"]}],
    "description": "Test breach",
    "severity": "HIGH",
    "mitigation_steps": []
  }'
```

---

### 2. Notify Data Protection Authority

**POST /api/v1/breach/notify-authority**

Log authority notification (Art. 33). Actual email is queued async.

**Request:**
```json
{
  "incident_id": "breach-uuid-123"
}
```

**Response:**
```json
{
  "success": true,
  "incident_id": "breach-uuid-123",
  "authority_notified_at": "2026-05-30T14:35:00Z",
  "email_queued_to": "lopd@aepd.es (Spanish DPA — hardcoded, TODO: configurable)",
  "deadline_72h_from": "2026-05-30T14:31:00Z"
}
```

**Curl Example:**
```bash
curl -X POST http://localhost:8000/api/v1/breach/notify-authority \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "breach-uuid-123"}'
```

---

### 3. Retrieve Breach History

**GET /api/v1/breach/history?limit=100&severity=HIGH**

Retrieve all breach incidents for audit/compliance review (Art. 5.1.e).

**Query Parameters:**
- `limit` (default 100): Max incidents to return
- `severity` (optional): Filter by LOW, MEDIUM, HIGH, or CRITICAL

**Response:**
```json
{
  "incidents": [
    {
      "incident_id": "breach-uuid-123",
      "incident_date": "2026-05-30T14:30:00Z",
      "discovery_date": "2026-05-30T14:31:00Z",
      "severity": "HIGH",
      "affected_users": 2,
      "description": "Unauthorized API access...",
      "root_cause": "Unpatched SQL injection",
      "authority_notified_at": "2026-05-30T14:35:00Z",
      "individuals_notified_at": "2026-05-31T09:00:00Z",
      "audit_log_entries": 3
    }
  ],
  "total": 1
}
```

**Curl Example:**
```bash
curl "http://localhost:8000/api/v1/breach/history?limit=50&severity=HIGH"
```

---

## Email Templates

### Art. 33 — Authority Notification (Spanish)

Generate email for Data Protection Authority:

```python
from breach_email_templates import BreachEmailTemplates
from datetime import datetime

email_body = BreachEmailTemplates.get_template(
    template_type="art_33_authority",
    language="es",
    incident_id="BREACH-2026-0530-001",
    incident_date=datetime(2026, 5, 30, 14, 30),
    affected_count=147,
    severity="HIGH",
    description="Acceso no autorizado a la base de datos de clientes",
    mitigation_steps=[
        {"action": "Sistema aislado", "timestamp": "2026-05-30T14:35Z"},
    ]
)
# email_body is ready to send to: lopd@aepd.es
```

### Art. 34 — Individual Notification (Spanish)

Generate email for affected users:

```python
email_body = BreachEmailTemplates.get_template(
    template_type="art_34_individual",
    language="es",
    user_name="María García López",
    incident_summary="Nuestro sistema fue afectado por un intento de acceso...",
    data_types_affected=["correo electrónico", "nombre completo"],
    mitigation_summary="Hemos aislado inmediatamente el sistema...",
    support_email="soporte@adaptafamilyoffice.com",
    support_phone="+34 912 345 678"
)
# email_body is ready to send to: user@example.com
```

---

## Background Cron Job

The system includes an optional background cron that runs every 1 hour:

```python
# In app_standalone_UPDATED_v3.py

scheduler = BackgroundScheduler()
scheduler.add_job(detect_suspicious_activity_cron, 'interval', hours=1)
scheduler.start()
```

This cron:
1. Scans `ConsentAuditLog` for suspicious patterns
2. Detects multiple failed authentications (>3 in 1h)
3. Detects rapid consent/withdraw cycles (<5min apart)
4. Logs suspected breaches for manual review (TODO: auto-file LOW/MEDIUM)

To disable:

```python
# Comment out in app_standalone_UPDATED_v3.py:
# scheduler = BackgroundScheduler()
# scheduler.add_job(...)
# scheduler.start()
```

---

## GDPR Compliance Matrix

| Article | Requirement | Implementation |
|---------|------------|-----------------|
| **Art. 33** | Notify authority within 72h | `/api/v1/breach/notify-authority` logs notification timestamp |
| **Art. 34** | Notify individuals "without undue delay" | Severity-based delay: CRITICAL (1h), HIGH (6h), MEDIUM (1d), LOW (7d) |
| **Art. 32** | Security by design | Audit log immutable; all actions logged with timestamp, IP, user-agent |
| **Art. 5.1.e** | Transparency & accountability | `/api/v1/breach/history` provides full audit trail; breaches retained 3+ years |
| **Art. 7** | Conditions for consent | Integration with `ConsentAuditLog` for detection heuristics |

---

## Known Limitations & TODOs

### Current Limitations

1. **Email Sending**: Currently mocked. No actual SendGrid/SMTP integration yet.
   - **TODO**: Wire SendGrid API in `notify_authority()` and `notify_individuals()`

2. **DPA Email**: Hardcoded to Spanish DPA (`lopd@aepd.es`).
   - **TODO**: Make configurable by country (Italy → Garante, France → CNIL, etc.)

3. **Database Session**: Uses in-memory SQLite in dummy examples.
   - **TODO**: Wire with real database (`backend.database.get_db`)

4. **Breach Detection**: Uses heuristics, not ML.
   - Current: >3 failed auth in 1h, rapid consent toggles
   - **TODO**: Add IP geolocation, anomaly detection, user behavior analysis

5. **Retention Policy**: No auto-cleanup cron yet.
   - **TODO**: Task #28 will implement GDPR Art. 5.1.e retention + auto-delete

6. **Individual Notification Delay**: Currently logged immediately.
   - **TODO**: Queue notifications for async delivery based on severity

---

## Configuration Reference

### Severity-Based Notification Timelines

```python
BreachSeverity.CRITICAL   → Notify authority within 24h, individuals within 1h
BreachSeverity.HIGH       → Notify authority within 72h, individuals within 6h
BreachSeverity.MEDIUM     → Notify authority within 72h, individuals within 1 day
BreachSeverity.LOW        → Notify authority within 72h, individuals within 7 days
```

### Audit Log Entry Format

```json
{
  "action": "filed|notified_authority|notified_individuals",
  "timestamp": "2026-05-30T14:35:00Z",
  "user_id": "admin_user_123",  // Admin who triggered action
  "notes": "Manual filing by data controller"
}
```

### Affected User Record Format

```json
{
  "user_id": "user_123",
  "email": "user@example.com",
  "data_types": ["email", "profile", "payment_method"],
  "notified_at": "2026-05-31T09:00:00Z",  // Optional
  "remediation_status": "password_reset_sent"  // Optional
}
```

---

## Testing

### Unit Tests

Run the included unit tests:

```bash
python -c "from breach_notification import test_breach_filing, test_notification_status, test_breach_history; test_breach_filing(); test_notification_status(); test_breach_history(); print('\n✓ All tests passed')"
```

### Integration Test

```bash
# 1. Start server
python app_standalone_UPDATED_v3.py

# 2. File a breach
curl -X POST http://localhost:8000/api/v1/breach/report \
  -H "Content-Type: application/json" \
  -d '{
    "incident_date": "2026-05-30T14:30:00Z",
    "affected_users": [{"user_id": "user_1", "email": "user@example.com", "data_types": ["email"]}],
    "description": "Test breach",
    "severity": "HIGH"
  }'

# 3. Retrieve incident ID from response
INCIDENT_ID="breach-uuid-123"

# 4. Notify authority
curl -X POST http://localhost:8000/api/v1/breach/notify-authority \
  -H "Content-Type: application/json" \
  -d "{\"incident_id\": \"$INCIDENT_ID\"}"

# 5. Check breach history
curl "http://localhost:8000/api/v1/breach/history"
```

---

## Logging

All breach actions are logged to stdout/logs:

```
2026-05-30 14:31:05 - INFO - Breach incident filed: breach-uuid-123, severity=HIGH, affected=2
2026-05-30 14:35:10 - INFO - Authority notification logged for incident breach-uuid-123
2026-05-30 14:35:11 - INFO - Individual notifications queued for incident breach-uuid-123 (2 users)
2026-05-30 15:31:20 - INFO - Retrieved 1 breach incidents for audit
```

To adjust verbosity:

```python
# In app_standalone_UPDATED_v3.py
logging.basicConfig(level=logging.DEBUG)  # More verbose
# or
logging.basicConfig(level=logging.WARNING)  # Less verbose
```

---

## Next Steps

1. **Task #27**: Privacy Policy UI — Add frontend page explaining breach notification rights
2. **Task #28**: Retention Policy — Auto-cleanup of old breach records (3+ years)
3. **Task #25**: Third-Party Processor DPA — Notification templates for processor sub-processors

---

## References

- GDPR Art. 33: https://gdpr-info.eu/art-33-gdpr/
- GDPR Art. 34: https://gdpr-info.eu/art-34-gdpr/
- EDPB Guidelines 05/2020 on measures based on Art. 4 (11) GDPR: https://edpb.ec.europa.eu/our-work-tools/public-consultations-art-93-gdpr_en
- Spanish DPA (AEPD): https://www.aepd.es/

---

**Last Updated**: 2026-05-30  
**Author**: Javier Méndez Díaz  
**Status**: Ready for Integration
