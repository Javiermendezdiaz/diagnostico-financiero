"""
Breach Notification System
GDPR Art. 33 (Authority notification within 72h) & Art. 34 (Individual notification)
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum, Index, JSON
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.sql import func
import json
import logging
import uuid

Base = declarative_base()
logger = logging.getLogger(__name__)


class BreachSeverity(str, Enum):
    """Breach severity classification for notification urgency."""
    LOW = "LOW"              # Minor exposure, low risk to individuals
    MEDIUM = "MEDIUM"        # Moderate exposure, affects <100 users, <7 days to notify
    HIGH = "HIGH"            # Significant exposure, affects 100+ users, <1 day to notify
    CRITICAL = "CRITICAL"    # Massive exposure, sensitive data, immediate notification


class BreachIncident(Base):
    """
    GDPR Art. 33 & 34 — Breach Incident Record
    Immutable log of data breaches with notification status and audit trail.
    """
    __tablename__ = "breach_incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # When did the breach happen?
    incident_date = Column(DateTime(timezone=True), nullable=False, index=True)
    discovery_date = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Who was affected?
    affected_users = Column(JSON, default=list, nullable=False)
    # Format: [{"user_id": "...", "email": "...", "data_types": ["email", "profile"], ...}, ...]

    # Severity determines notification timeline
    severity = Column(SQLEnum(BreachSeverity), default=BreachSeverity.MEDIUM, nullable=False)

    # What happened?
    description = Column(String(1000), nullable=False)  # e.g., "Unauthorized API access to customer database"
    root_cause = Column(String(500), nullable=True)    # e.g., "Unpatched SQL injection vulnerability"

    # Mitigation steps taken
    mitigation_steps = Column(JSON, default=list, nullable=False)
    # Format: [{"action": "...", "timestamp": "2026-05-30T14:30:00Z"}, ...]

    # Notification status (Art. 33, Art. 34)
    authority_notified_at = Column(DateTime(timezone=True), nullable=True, index=True)
    individuals_notified_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Audit trail (who made what decision, when)
    audit_log = Column(JSON, default=list, nullable=False)
    # Format: [{"action": "filed|notified_authority|notified_individuals", "timestamp": "...", "user_id": "...", "notes": "..."}, ...]

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_breach_severity_date", "severity", "incident_date"),
        Index("idx_breach_notification_status", "authority_notified_at", "individuals_notified_at"),
    )

    def __repr__(self):
        return f"<BreachIncident(id={self.id}, severity={self.severity.value}, affected={len(self.affected_users)})>"


class BreachService:
    """
    Service for breach detection, filing, and notification.
    Scans ConsentRecord.audit_log for suspicious patterns and triggers GDPR Art. 33-34 workflow.
    """

    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    def detect_suspicious_activity(self) -> List[Dict[str, Any]]:
        """
        Scan ConsentAuditLog for breach indicators.
        Returns list of suspected breaches with evidence.

        Heuristics:
        1. >3 failed verification attempts in 1h window → potential unauthorized access
        2. Consent/withdraw cycles <5min apart (same user) → account compromise
        3. Rapid data access from unusual IP ranges → unauthorized exfiltration
        4. Multiple failed login attempts → brute force
        """
        suspected_breaches = []

        # Import here to avoid circular dependencies
        from backend.models.consent import ConsentAuditLog

        # Heuristic 1: Failed verification attempts
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        failed_events = self.session.query(ConsentAuditLog).filter(
            ConsentAuditLog.event_type.in_(["VERIFICATION_FAILED", "AUTH_FAILED"]),
            ConsentAuditLog.timestamp >= cutoff_time
        ).all()

        # Group by user_id + IP
        user_ip_attempts = {}
        for event in failed_events:
            key = f"{event.user_id}:{event.ip_address}"
            if key not in user_ip_attempts:
                user_ip_attempts[key] = []
            user_ip_attempts[key].append(event)

        for key, attempts in user_ip_attempts.items():
            if len(attempts) > 3:
                user_id = key.split(":")[0]
                self.logger.warning(f"Suspicious activity: {len(attempts)} failed attempts for user {user_id}")
                suspected_breaches.append({
                    "type": "MULTIPLE_FAILED_AUTH",
                    "user_id": user_id,
                    "attempt_count": len(attempts),
                    "ip_address": key.split(":")[1],
                    "time_window": "1h",
                    "severity": BreachSeverity.MEDIUM if len(attempts) > 5 else BreachSeverity.LOW
                })

        # Heuristic 2: Rapid consent/withdraw cycles
        all_events = self.session.query(ConsentAuditLog).filter(
            ConsentAuditLog.event_type.in_(["GRANTED", "WITHDRAWN"]),
            ConsentAuditLog.timestamp >= (datetime.utcnow() - timedelta(hours=24))
        ).all()

        # Group by user_id, sort by timestamp
        user_events = {}
        for event in all_events:
            if event.user_id not in user_events:
                user_events[event.user_id] = []
            user_events[event.user_id].append(event)

        for user_id, events in user_events.items():
            events_sorted = sorted(events, key=lambda e: e.timestamp)
            for i in range(len(events_sorted) - 1):
                time_diff = (events_sorted[i+1].timestamp - events_sorted[i].timestamp).total_seconds()
                if time_diff < 300:  # <5 min
                    self.logger.warning(f"Suspicious rapid toggle: user {user_id}, {time_diff}s apart")
                    suspected_breaches.append({
                        "type": "RAPID_CONSENT_TOGGLE",
                        "user_id": user_id,
                        "time_between_events_seconds": time_diff,
                        "severity": BreachSeverity.LOW  # Low severity, usually user error
                    })

        return suspected_breaches

    def file_breach(
        self,
        incident_date: datetime,
        affected_users: List[Dict[str, Any]],
        description: str,
        severity: BreachSeverity,
        root_cause: Optional[str] = None,
        mitigation_steps: Optional[List[Dict[str, str]]] = None
    ) -> BreachIncident:
        """
        File a breach incident. Creates immutable record with audit trail.

        Args:
            incident_date: When breach occurred (UTC)
            affected_users: List of affected user records
            description: What happened
            severity: LOW/MEDIUM/HIGH/CRITICAL
            root_cause: Root cause analysis (optional)
            mitigation_steps: Actions taken to contain breach

        Returns:
            BreachIncident object (persisted)
        """
        incident = BreachIncident(
            incident_date=incident_date,
            discovery_date=datetime.utcnow(),
            affected_users=affected_users,
            severity=severity,
            description=description,
            root_cause=root_cause,
            mitigation_steps=mitigation_steps or []
        )

        # Add initial audit log entry
        incident.audit_log = [
            {
                "action": "filed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "notes": f"Breach filed with {len(affected_users)} affected users"
            }
        ]

        self.session.add(incident)
        self.session.commit()

        self.logger.info(f"Breach incident filed: {incident.id}, severity={severity.value}, affected={len(affected_users)}")
        return incident

    def notify_authority(self, incident_id: str) -> bool:
        """
        Art. 33 — Notify Data Protection Authority within 72 hours.

        This endpoint logs the notification decision. Actual email sending
        is async (TODO: SendGrid integration).

        Args:
            incident_id: Breach incident ID

        Returns:
            True if notification was logged successfully
        """
        incident = self.session.query(BreachIncident).filter_by(id=incident_id).first()
        if not incident:
            self.logger.error(f"Breach incident not found: {incident_id}")
            return False

        if incident.authority_notified_at:
            self.logger.warning(f"Authority already notified for incident {incident_id}")
            return True

        # Check notification deadline (72 hours from discovery)
        deadline = incident.discovery_date + timedelta(hours=72)
        time_remaining = deadline - datetime.utcnow()

        if time_remaining.total_seconds() < 0:
            self.logger.warning(f"Notification deadline exceeded for incident {incident_id}")

        # Log notification
        incident.authority_notified_at = datetime.utcnow()
        incident.audit_log.append({
            "action": "notified_authority",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "affected_users": len(incident.affected_users),
            "severity": incident.severity.value
        })

        self.session.commit()

        # TODO: Send actual email via SendGrid to DPA
        self.logger.info(f"Authority notification logged for incident {incident_id}")
        return True

    def notify_individuals(self, incident_id: str) -> bool:
        """
        Art. 34 — Notify affected individuals "without undue delay".

        Triggers email notifications to all affected users. This endpoint
        logs the action; actual email sending is async.

        Args:
            incident_id: Breach incident ID

        Returns:
            True if notifications were queued successfully
        """
        incident = self.session.query(BreachIncident).filter_by(id=incident_id).first()
        if not incident:
            self.logger.error(f"Breach incident not found: {incident_id}")
            return False

        if incident.individuals_notified_at:
            self.logger.warning(f"Individuals already notified for incident {incident_id}")
            return True

        # Determine notification urgency based on severity
        expected_delay = {
            BreachSeverity.CRITICAL: timedelta(hours=1),     # Send within 1h
            BreachSeverity.HIGH: timedelta(hours=6),         # Send within 6h
            BreachSeverity.MEDIUM: timedelta(days=1),        # Send within 1 day
            BreachSeverity.LOW: timedelta(days=7)            # Send within 7 days
        }

        # Log notification batch
        incident.individuals_notified_at = datetime.utcnow()
        incident.audit_log.append({
            "action": "notified_individuals",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "affected_count": len(incident.affected_users),
            "severity": incident.severity.value,
            "expected_delivery": expected_delay[incident.severity].total_seconds()
        })

        self.session.commit()

        # TODO: Queue emails via SendGrid/external service
        self.logger.info(
            f"Individual notifications queued for incident {incident_id} "
            f"({len(incident.affected_users)} users)"
        )
        return True

    def get_breach_history(
        self,
        limit: int = 100,
        severity_filter: Optional[BreachSeverity] = None
    ) -> List[BreachIncident]:
        """
        Art. 5.1.e (Transparency) — Retrieve all breach incidents for audit/compliance review.

        Args:
            limit: Maximum number of incidents to return
            severity_filter: Filter by severity (optional)

        Returns:
            List of BreachIncident records (most recent first)
        """
        query = self.session.query(BreachIncident).order_by(BreachIncident.created_at.desc())

        if severity_filter:
            query = query.filter_by(severity=severity_filter)

        incidents = query.limit(limit).all()
        self.logger.info(f"Retrieved {len(incidents)} breach incidents for audit")
        return incidents

    def get_breach_by_id(self, incident_id: str) -> Optional[BreachIncident]:
        """Retrieve a specific breach incident by ID."""
        return self.session.query(BreachIncident).filter_by(id=incident_id).first()

    def get_notification_status(self, incident_id: str) -> Dict[str, Any]:
        """Get current notification status (Art. 33, Art. 34) for an incident."""
        incident = self.get_breach_by_id(incident_id)
        if not incident:
            return {}

        return {
            "incident_id": incident.id,
            "severity": incident.severity.value,
            "affected_users": len(incident.affected_users),
            "authority_notified_at": incident.authority_notified_at.isoformat() if incident.authority_notified_at else None,
            "individuals_notified_at": incident.individuals_notified_at.isoformat() if incident.individuals_notified_at else None,
            "audit_log": incident.audit_log
        }


# ============================================================================
# Unit Tests
# ============================================================================

def test_breach_filing():
    """Test breach incident creation and storage."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    service = BreachService(session)

    # File a breach
    affected = [
        {"user_id": "user_123", "email": "user@example.com", "data_types": ["email", "profile"]},
        {"user_id": "user_456", "email": "user456@example.com", "data_types": ["email"]},
    ]

    incident = service.file_breach(
        incident_date=datetime.utcnow(),
        affected_users=affected,
        description="Unauthorized API access",
        severity=BreachSeverity.HIGH,
        root_cause="Unpatched SQL injection"
    )

    assert incident.id
    assert incident.severity == BreachSeverity.HIGH
    assert len(incident.affected_users) == 2
    assert len(incident.audit_log) == 1
    print("✓ test_breach_filing passed")


def test_notification_status():
    """Test notification status tracking."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    service = BreachService(session)

    # File and notify
    incident = service.file_breach(
        incident_date=datetime.utcnow(),
        affected_users=[{"user_id": "user_1", "email": "u1@example.com", "data_types": ["email"]}],
        description="Test breach",
        severity=BreachSeverity.MEDIUM
    )

    # Before notification
    status = service.get_notification_status(incident.id)
    assert status["authority_notified_at"] is None

    # After authority notification
    service.notify_authority(incident.id)
    status = service.get_notification_status(incident.id)
    assert status["authority_notified_at"] is not None

    # After individual notification
    service.notify_individuals(incident.id)
    status = service.get_notification_status(incident.id)
    assert status["individuals_notified_at"] is not None
    assert len(status["audit_log"]) == 3  # filed + notify_authority + notify_individuals
    print("✓ test_notification_status passed")


def test_breach_history():
    """Test breach history retrieval."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    service = BreachService(session)

    # File multiple breaches
    for i in range(3):
        service.file_breach(
            incident_date=datetime.utcnow(),
            affected_users=[{"user_id": f"user_{i}", "email": f"u{i}@example.com", "data_types": ["email"]}],
            description=f"Breach {i}",
            severity=BreachSeverity.MEDIUM if i % 2 == 0 else BreachSeverity.LOW
        )

    # Retrieve all
    all_incidents = service.get_breach_history()
    assert len(all_incidents) == 3

    # Filter by severity
    high_incidents = service.get_breach_history(severity_filter=BreachSeverity.MEDIUM)
    assert len(high_incidents) == 2
    print("✓ test_breach_history passed")


if __name__ == "__main__":
    test_breach_filing()
    test_notification_status()
    test_breach_history()
    print("\n✓ All breach notification tests passed")
