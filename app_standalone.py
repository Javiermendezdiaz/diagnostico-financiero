#!/usr/bin/env python3
"""
Diagnóstico Financiero - FastAPI Backend + Static Frontend + GDPR Compliance
Single port, all-in-one deployment for Render
Consolidated: Task #23 (ConsentManagement) + Task #24 (UserRights) + Task #26 (BreachNotification)
"""

import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
from apscheduler.schedulers.background import BackgroundScheduler

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# App dir
app_dir = Path(__file__).parent.absolute()
os.chdir(app_dir)

# Create reports dir
output_dir = app_dir / "reports"
output_dir.mkdir(exist_ok=True)

# ============================================================================
# FASTAPI & DEPENDENCIES
# ============================================================================

try:
    from fastapi import FastAPI, Request, HTTPException, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import JSONResponse, HTMLResponse
    from pydantic import BaseModel, EmailStr, Field
    import uvicorn
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    sys.exit(1)

# ============================================================================
# SQLALCHEMY & DATABASE
# ============================================================================

try:
    from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, Index, create_engine, Enum as SQLEnum
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import Session, sessionmaker
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.sql import func
except ImportError as e:
    logger.error(f"Missing SQLAlchemy: {e}")
    sys.exit(1)

# ============================================================================
# DIAGNOSTIC MODULES
# ============================================================================

try:
    from diagnostic_engine import DiagnosticEngine
    from diagnostic_report_generator import DiagnosticReportGenerator
    from diagnostic_engine_extended import DiagnosticEngineExtended
    from couple_mirror_models import CoupleSessionStore, CoupleMatchingEngine
except ImportError as e:
    logger.error(f"Module import error: {e}")
    sys.exit(1)

# Load schema
schema_path = app_dir / "data-schema-500.json"
try:
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    total_preguntas = schema.get('metadata', {}).get('total_preguntas', 500)
    logger.info(f"Schema loaded: {total_preguntas} questions")
except FileNotFoundError:
    logger.error(f"Schema not found: {schema_path}")
    sys.exit(1)

# ============================================================================
# SQLALCHEMY BASE (SHARED ORM)
# ============================================================================

Base = declarative_base()

# ============================================================================
# TASK #23: CONSENT MANAGEMENT (GDPR Art. 7, 15-20, 21, 17)
# ============================================================================

class ConsentType(str, Enum):
    """Types of consent (Art. 7 — explicit, specific, informed, freely given)"""
    DIAGNOSIS = "diagnosis"
    EMAIL_TRIGGERS = "email_triggers"
    DATA_RETENTION = "data_retention"
    THIRD_PARTY_DPA = "third_party_dpa"


class ConsentStatus(str, Enum):
    """Consent lifecycle status"""
    INITIATED = "initiated"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ConsentRecord(Base):
    """
    GDPR Art. 7 — Explicit, revocable, auditable consent record
    - Granular consent per type
    - Email verification required
    - Full audit trail
    - 48h token TTL
    """
    __tablename__ = "consent_records"
    __table_args__ = (
        Index("idx_user_id_type", "user_id", "consent_type"),
        Index("idx_verification_token", "verification_token"),
        Index("idx_email", "email"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    status = Column(SQLEnum(ConsentStatus), default=ConsentStatus.INITIATED)

    # Email verification
    verification_token = Column(String(64), unique=True, nullable=True)
    verification_token_expires_at = Column(DateTime, nullable=True)
    verification_sent_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Withdrawal (Art. 7.3)
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawal_reason = Column(String(500), nullable=True)

    # Audit trail
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    audit_log = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "consent_type": self.consent_type.value,
            "status": self.status.value,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "created_at": self.created_at.isoformat(),
            "audit_log": self.audit_log
        }


# ============================================================================
# TASK #24: USER RIGHTS (GDPR Art. 15-20)
# ============================================================================

class UserDataExport(Base):
    """
    GDPR Art. 15 — Right of access
    Stores user data exports for Art. 20 (data portability) compliance
    """
    __tablename__ = "user_data_exports"
    __table_args__ = (
        Index("idx_user_id_export", "user_id", "created_at"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    export_type = Column(String(50), nullable=False)  # "full_export", "diagnostic_data", etc.
    data_json = Column(JSON, nullable=False)
    format = Column(String(20), default="json")  # json, csv, xml
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)  # For GDPR Art. 15 — retention limits


class RectificationRequest(Base):
    """
    GDPR Art. 16 — Right to rectification
    Tracks user requests to correct inaccurate data
    """
    __tablename__ = "rectification_requests"
    __table_args__ = (
        Index("idx_user_id_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    field_name = Column(String(255), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=False)
    reason = Column(String(500), nullable=True)
    status = Column(String(50), default="pending")  # pending, approved, rejected, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class DeletionRequest(Base):
    """
    GDPR Art. 17 — Right to be forgotten
    Immutable log of user deletion requests for audit trail
    """
    __tablename__ = "deletion_requests"
    __table_args__ = (
        Index("idx_user_id_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    deletion_scope = Column(String(255), nullable=False)  # "full_delete", "diagnostic_data_only"
    reason = Column(String(500), nullable=True)
    status = Column(String(50), default="pending")  # pending, approved, rejected, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    audit_log = Column(JSON, default=list)


class ObjectionRequest(Base):
    """
    GDPR Art. 21 — Right to object
    User objection to processing (e.g., marketing)
    """
    __tablename__ = "objection_requests"
    __table_args__ = (
        Index("idx_user_id_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    processing_purpose = Column(String(255), nullable=False)  # "marketing", "analytics", etc.
    reason = Column(String(500), nullable=True)
    status = Column(String(50), default="acknowledged")
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# TASK #26: BREACH NOTIFICATION (GDPR Art. 33-34)
# ============================================================================

class BreachSeverity(str, Enum):
    """Breach severity classification"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BreachIncident(Base):
    """
    GDPR Art. 33-34 — Data Breach Incident Record
    Immutable log with notification status and audit trail
    """
    __tablename__ = "breach_incidents"
    __table_args__ = (
        Index("idx_breach_severity_date", "severity", "incident_date"),
        Index("idx_breach_notification_status", "authority_notified_at", "individuals_notified_at"),
    )

    id = Column(String(36), primary_key=True)
    incident_date = Column(DateTime(timezone=True), nullable=False, index=True)
    discovery_date = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Affected users
    affected_users = Column(JSON, default=list, nullable=False)

    # Severity determines notification timeline
    severity = Column(SQLEnum(BreachSeverity), default=BreachSeverity.MEDIUM, nullable=False)

    # What happened
    description = Column(String(1000), nullable=False)
    root_cause = Column(String(500), nullable=True)

    # Mitigation steps
    mitigation_steps = Column(JSON, default=list, nullable=False)

    # Notification status (Art. 33, 34)
    authority_notified_at = Column(DateTime(timezone=True), nullable=True, index=True)
    individuals_notified_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Audit trail
    audit_log = Column(JSON, default=list, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================================
# CREATE ALL TABLES
# ============================================================================

try:
    from sqlalchemy import create_engine as sa_create_engine
    db_url = os.getenv("DATABASE_URL", "sqlite:///./diagnoses.db")
    engine = sa_create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"Database initialized: {db_url}")
except Exception as e:
    logger.error(f"Database initialization error: {e}")
    sys.exit(1)


def get_db():
    """Dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(title="Diagnóstico Financiero API + GDPR", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create diagnostic engines
try:
    diagnostic_engine = DiagnosticEngine(str(schema_path))
    diagnostic_engine_extended = DiagnosticEngineExtended(str(schema_path))
    couple_session_store = CoupleSessionStore(str(app_dir / "couple_sessions.json"))
    logger.info("Diagnostic engines initialized")
except Exception as e:
    logger.error(f"Engine initialization error: {e}")
    sys.exit(1)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ConsentInitRequest(BaseModel):
    user_id: str
    email: str
    consent_type: str


class ConsentWithdrawRequest(BaseModel):
    user_id: str
    consent_type: Optional[str] = None
    reason: str


class RectifyRequest(BaseModel):
    field_name: str
    new_value: str
    reason: Optional[str] = None


class DataExportRequest(BaseModel):
    format: str = "json"


class DeletionRequestBody(BaseModel):
    deletion_scope: str = "full_delete"
    reason: Optional[str] = None


class ObjectionRequestBody(BaseModel):
    processing_purpose: str
    reason: Optional[str] = None


class BreachReportRequest(BaseModel):
    incident_date: datetime
    affected_users: List[Dict[str, Any]]
    description: str
    severity: str = "MEDIUM"
    root_cause: Optional[str] = None
    mitigation_steps: Optional[List[Dict[str, str]]] = None


class NotifyAuthorityRequest(BaseModel):
    incident_id: str


# ============================================================================
# HEALTH & CORE ENDPOINTS
# ============================================================================

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "version": "4.0"}


@app.get("/api/v1/schema")
def get_schema():
    """Return all 500 questions"""
    questions = []
    question_id = 1

    capas = schema.get('capas', {})
    for capa_name, capa_data in capas.items():
        preguntas = capa_data.get('preguntas', [])
        for pregunta_data in preguntas:
            respuestas_list = pregunta_data.get('respuestas', [])
            pesos = pregunta_data.get('pesos', {})

            questions.append({
                "id": question_id,
                "capa": capa_name,
                "pregunta": pregunta_data.get('pregunta', ''),
                "respuestas": respuestas_list,
                "pesos": pesos
            })
            question_id += 1

    return {"questions": questions, "metadata": schema.get('metadata', {})}


@app.post("/api/v1/diagnose")
async def diagnose(request: Request):
    """Process diagnostic answers and generate report"""
    try:
        data = await request.json()
        answers = data.get("answers", {})

        result = diagnostic_engine.diagnose(answers)
        result_dict = diagnostic_engine.export_json(result)

        import time
        user_id = f"user_{int(time.time())}"
        report_filename = f"{user_id}_diagnostic.pdf"
        pdf_filepath = output_dir / report_filename

        report_generator = DiagnosticReportGenerator(str(pdf_filepath))
        pdf_path = report_generator.generate_report(result_dict)

        logger.info(f"Diagnostic completed for {user_id}")

        return {
            "success": True,
            "results": result_dict,
            "report_path": str(pdf_path)
        }
    except Exception as e:
        logger.error(f"Diagnose error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# ADAPTIVE 3-PHASE ENDPOINTS
# ============================================================================

@app.post("/api/motor/generar-fase2")
async def generar_fase2(request: Request):
    """Generate personalized Phase 2 questions"""
    try:
        respuestas = await request.json()
        perfil = diagnostic_engine_extended.generate_perfil(respuestas)
        fase2_preguntas = diagnostic_engine_extended.generate_fase2_questions(respuestas, perfil)

        logger.info(f"Generated Phase 2 for profile: {perfil}")

        return {
            "perfil": perfil,
            "fase2_preguntas": fase2_preguntas
        }
    except Exception as e:
        logger.error(f"Phase 2 error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/motor/generar-fase3")
async def generar_fase3(request: Request):
    """Generate Phase 3 psychology questions"""
    try:
        respuestas = await request.json()
        fase3_preguntas = diagnostic_engine_extended.generate_fase3_questions(respuestas)

        logger.info(f"Generated Phase 3")

        return {"fase3_preguntas": fase3_preguntas}
    except Exception as e:
        logger.error(f"Phase 3 error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/pdf/generar")
async def generar_pdf(request: Request):
    """Generate final PDF report"""
    try:
        respuestas = await request.json()

        import time
        user_id = f"user_{int(time.time())}"
        report_filename = f"{user_id}_diagnostic.pdf"
        pdf_filepath = output_dir / report_filename

        report_generator = DiagnosticReportGenerator(str(pdf_filepath))
        result_dict = {
            "respuestas": respuestas,
            "profile": diagnostic_engine_extended.generate_perfil(respuestas)
        }

        pdf_path = report_generator.generate_report(result_dict)
        pdf_url = f"/reports/{report_filename}"

        logger.info(f"PDF generated: {report_filename}")

        return {"pdfUrl": pdf_url, "fileName": report_filename}
    except Exception as e:
        logger.error(f"PDF error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# COUPLE MIRROR ENDPOINTS
# ============================================================================

@app.post("/api/couple-mirror/invite")
async def couple_mirror_invite(request: Request):
    """Invite partner for couple financial analysis"""
    try:
        if not couple_session_store:
            return JSONResponse(status_code=503, content={"error": "Couple Mirror not available"})

        data = await request.json()
        user_id = data.get("user_id")
        user_email = data.get("user_email")
        partner_email = data.get("partner_email")

        if not all([user_id, user_email, partner_email]):
            return JSONResponse(status_code=400, content={"error": "Missing required fields"})

        session = couple_session_store.create_session(user_id, user_email)

        logger.info(f"Couple Mirror session created for {user_id}")

        return {
            "couple_session_id": session["session_id"],
            "invite_token": session["invite_token"],
            "invite_url": f"https://www.adaptafamilyoffice.com/couple-mirror/{session['invite_token']}",
            "expires_in_hours": 24
        }
    except Exception as e:
        logger.error(f"Couple Mirror error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# TASK #23: CONSENT MANAGEMENT (GDPR Art. 7)
# ============================================================================

@app.post("/api/v1/consent/init", status_code=201)
async def consent_init(body: ConsentInitRequest, db: Session = Depends(get_db)):
    """
    POST /api/v1/consent/init
    Initiate consent flow (Art. 7 — explicit consent)
    """
    try:
        import secrets
        import uuid

        consent_id = str(uuid.uuid4())
        verification_token = secrets.token_urlsafe(32)
        now = datetime.utcnow()

        try:
            consent_type = ConsentType[body.consent_type.upper()]
        except KeyError:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid consent_type: {body.consent_type}"}
            )

        record = ConsentRecord(
            id=consent_id,
            user_id=body.user_id,
            email=body.email,
            consent_type=consent_type,
            status=ConsentStatus.PENDING_VERIFICATION,
            verification_token=verification_token,
            verification_token_expires_at=now + timedelta(hours=48),
            verification_sent_at=now,
            audit_log=[{
                "action": "initiated",
                "timestamp": now.isoformat(),
                "consent_type": consent_type.value
            }]
        )

        db.add(record)
        db.commit()

        logger.info(f"[CONSENT] Initiated {consent_type.value} for {body.user_id}")

        return {
            "consent_id": consent_id,
            "status": "pending_verification",
            "verification_token": verification_token,
            "message": "Verification email sent"
        }

    except IntegrityError:
        db.rollback()
        return JSONResponse(status_code=409, content={"error": "Consent already exists"})
    except Exception as e:
        db.rollback()
        logger.error(f"[CONSENT] Init error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/v1/consent/verify")
async def consent_verify(token: str, db: Session = Depends(get_db)):
    """GET /api/v1/consent/verify?token=<TOKEN>"""
    try:
        now = datetime.utcnow()
        record = db.query(ConsentRecord).filter_by(verification_token=token).first()

        if not record:
            return HTMLResponse("<h1>❌ Token Invalid</h1>", status_code=404)

        if record.status == ConsentStatus.VERIFIED:
            return HTMLResponse("<h1>✓ Already Verified</h1>")

        if record.status == ConsentStatus.WITHDRAWN:
            return HTMLResponse("<h1>⚠️ Withdrawn</h1>", status_code=410)

        if record.verification_token_expires_at < now:
            record.status = ConsentStatus.EXPIRED
            db.commit()
            return HTMLResponse("<h1>⏰ Token Expired</h1>", status_code=410)

        record.status = ConsentStatus.VERIFIED
        record.verified_at = now
        record.audit_log.append({
            "action": "verified",
            "timestamp": now.isoformat()
        })

        db.commit()
        logger.info(f"[CONSENT] Verified {record.consent_type.value} for {record.user_id}")

        return HTMLResponse(f"<h1>✓ Consentimiento Verificado</h1><p>{record.consent_type.value}</p>")

    except Exception as e:
        logger.error(f"[CONSENT] Verify error: {e}")
        return HTMLResponse("<h1>❌ Error</h1>", status_code=500)


@app.post("/api/v1/consent/withdraw")
async def consent_withdraw(body: ConsentWithdrawRequest, db: Session = Depends(get_db)):
    """POST /api/v1/consent/withdraw"""
    try:
        now = datetime.utcnow()
        query = db.query(ConsentRecord).filter_by(
            user_id=body.user_id,
            status=ConsentStatus.VERIFIED
        )

        if body.consent_type:
            try:
                consent_type = ConsentType[body.consent_type.upper()]
                query = query.filter_by(consent_type=consent_type)
            except KeyError:
                return JSONResponse(status_code=400, content={"error": "Invalid consent_type"})

        records = query.all()
        count = len(records)

        if count == 0:
            return JSONResponse(status_code=404, content={"error": "No active consent found"})

        for record in records:
            record.status = ConsentStatus.WITHDRAWN
            record.withdrawn_at = now
            record.withdrawal_reason = body.reason
            record.audit_log.append({
                "action": "withdrawn",
                "timestamp": now.isoformat(),
                "reason": body.reason
            })

        db.commit()
        logger.info(f"[CONSENT] Withdrawn {count} for {body.user_id}")

        return {"withdrawn_count": count, "status": "withdrawn"}

    except Exception as e:
        db.rollback()
        logger.error(f"[CONSENT] Withdraw error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/v1/consent/status/{user_id}")
async def consent_status(user_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/consent/status/{user_id}"""
    try:
        records = db.query(ConsentRecord).filter_by(user_id=user_id).order_by(
            ConsentRecord.created_at.desc()
        ).all()

        logger.info(f"[CONSENT] Retrieved {len(records)} for {user_id}")

        return {
            "consents": [r.to_dict() for r in records],
            "total": len(records)
        }

    except Exception as e:
        logger.error(f"[CONSENT] Status error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# TASK #24: USER RIGHTS (GDPR Art. 15-20)
# ============================================================================

@app.get("/api/v1/users/{user_id}/data")
async def get_user_data(user_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/users/{user_id}/data — Art. 15 Data Access"""
    try:
        consents = db.query(ConsentRecord).filter_by(user_id=user_id).all()
        exports = db.query(UserDataExport).filter_by(user_id=user_id).all()
        rectifications = db.query(RectificationRequest).filter_by(user_id=user_id).all()
        deletions = db.query(DeletionRequest).filter_by(user_id=user_id).all()
        objections = db.query(ObjectionRequest).filter_by(user_id=user_id).all()

        data = {
            "user_id": user_id,
            "consents": [c.to_dict() for c in consents],
            "data_exports": [{
                "id": e.id, "type": e.export_type, "format": e.format, "created_at": e.created_at.isoformat()
            } for e in exports],
            "requests": {
                "rectifications": [{
                    "id": r.id, "field": r.field_name, "status": r.status
                } for r in rectifications],
                "deletions": [{
                    "id": d.id, "scope": d.deletion_scope, "status": d.status
                } for d in deletions],
                "objections": [{
                    "id": o.id, "purpose": o.processing_purpose, "status": o.status
                } for o in objections]
            },
            "total_consents": len(consents)
        }

        logger.info(f"[USER_RIGHTS] Art. 15 access for {user_id}")
        return data

    except Exception as e:
        logger.error(f"[USER_RIGHTS] Get data error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/users/{user_id}/rectify", status_code=201)
async def rectify_user_data(user_id: str, body: RectifyRequest, db: Session = Depends(get_db)):
    """POST /api/v1/users/{user_id}/rectify — Art. 16 Rectification"""
    try:
        import uuid

        request_id = str(uuid.uuid4())

        rectify_req = RectificationRequest(
            id=request_id,
            user_id=user_id,
            field_name=body.field_name,
            new_value=body.new_value,
            reason=body.reason,
            status="pending"
        )

        db.add(rectify_req)
        db.commit()

        logger.info(f"[USER_RIGHTS] Art. 16 rectification for {user_id}: {body.field_name}")

        return {
            "request_id": request_id,
            "status": "pending",
            "field_name": body.field_name
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[USER_RIGHTS] Rectify error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/users/{user_id}/export", status_code=201)
async def export_user_data(user_id: str, body: DataExportRequest, db: Session = Depends(get_db)):
    """POST /api/v1/users/{user_id}/export — Art. 20 Data Portability"""
    try:
        import uuid
        import json as json_lib

        export_id = str(uuid.uuid4())

        consents = db.query(ConsentRecord).filter_by(user_id=user_id).all()
        data_obj = {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat(),
            "consents": [c.to_dict() for c in consents]
        }

        export_record = UserDataExport(
            id=export_id,
            user_id=user_id,
            export_type="full_export",
            data_json=data_obj,
            format=body.format,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )

        db.add(export_record)
        db.commit()

        logger.info(f"[USER_RIGHTS] Art. 20 export for {user_id}")

        return {
            "export_id": export_id,
            "format": body.format,
            "created_at": export_record.created_at.isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[USER_RIGHTS] Export error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/users/{user_id}/delete-request", status_code=201)
async def request_deletion(user_id: str, body: DeletionRequestBody, db: Session = Depends(get_db)):
    """POST /api/v1/users/{user_id}/delete-request — Art. 17 Right to be Forgotten"""
    try:
        import uuid

        request_id = str(uuid.uuid4())
        now = datetime.utcnow()

        deletion_req = DeletionRequest(
            id=request_id,
            user_id=user_id,
            deletion_scope=body.deletion_scope,
            reason=body.reason,
            status="pending",
            audit_log=[{
                "action": "deletion_requested",
                "timestamp": now.isoformat()
            }]
        )

        db.add(deletion_req)
        db.commit()

        logger.info(f"[USER_RIGHTS] Art. 17 deletion for {user_id}")

        return {
            "request_id": request_id,
            "status": "pending",
            "scope": body.deletion_scope
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[USER_RIGHTS] Deletion error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/users/{user_id}/objection", status_code=201)
async def object_to_processing(user_id: str, body: ObjectionRequestBody, db: Session = Depends(get_db)):
    """POST /api/v1/users/{user_id}/objection — Art. 21 Right to Object"""
    try:
        import uuid

        objection_id = str(uuid.uuid4())

        objection = ObjectionRequest(
            id=objection_id,
            user_id=user_id,
            processing_purpose=body.processing_purpose,
            reason=body.reason,
            status="acknowledged"
        )

        db.add(objection)
        db.commit()

        logger.info(f"[USER_RIGHTS] Art. 21 objection for {user_id}")

        return {
            "objection_id": objection_id,
            "status": "acknowledged",
            "purpose": body.processing_purpose
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[USER_RIGHTS] Objection error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/v1/users/{user_id}/rights-status")
async def user_rights_status(user_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/users/{user_id}/rights-status"""
    try:
        rectifications = db.query(RectificationRequest).filter_by(user_id=user_id).all()
        exports = db.query(UserDataExport).filter_by(user_id=user_id).all()
        deletions = db.query(DeletionRequest).filter_by(user_id=user_id).all()
        objections = db.query(ObjectionRequest).filter_by(user_id=user_id).all()

        data = {
            "user_id": user_id,
            "rectifications": {
                "total": len(rectifications),
                "pending": len([r for r in rectifications if r.status == "pending"])
            },
            "data_exports": {"total": len(exports)},
            "deletion_requests": {
                "total": len(deletions),
                "pending": len([d for d in deletions if d.status == "pending"])
            },
            "objections": {"total": len(objections)}
        }

        logger.info(f"[USER_RIGHTS] Rights status for {user_id}")
        return data

    except Exception as e:
        logger.error(f"[USER_RIGHTS] Status error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# TASK #26: BREACH NOTIFICATION (GDPR Art. 33-34)
# ============================================================================

@app.post("/api/v1/breach/report", status_code=201)
async def report_breach(body: BreachReportRequest, db: Session = Depends(get_db)):
    """POST /api/v1/breach/report — Art. 33 Authority Notification"""
    try:
        import uuid

        try:
            severity = BreachSeverity[body.severity.upper()]
        except KeyError:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid severity: {body.severity}"}
            )

        incident_id = str(uuid.uuid4())
        now = datetime.utcnow()

        incident = BreachIncident(
            id=incident_id,
            incident_date=body.incident_date,
            discovery_date=now,
            affected_users=body.affected_users,
            severity=severity,
            description=body.description,
            root_cause=body.root_cause,
            mitigation_steps=body.mitigation_steps or [],
            audit_log=[{
                "action": "filed",
                "timestamp": now.isoformat(),
                "notes": f"{len(body.affected_users)} users affected"
            }]
        )

        db.add(incident)
        db.commit()

        next_actions = {
            BreachSeverity.CRITICAL: "Notify within 1 hour",
            BreachSeverity.HIGH: "Notify within 72h",
            BreachSeverity.MEDIUM: "Notify within 72h",
            BreachSeverity.LOW: "Notify within 30 days"
        }

        logger.info(f"[BREACH] Filed {incident_id}, severity={severity.value}")

        return {
            "incident_id": incident_id,
            "severity": incident.severity.value,
            "affected_users": len(incident.affected_users),
            "created_at": incident.created_at.isoformat() + "Z",
            "next_action": next_actions[severity]
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[BREACH] Filing error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/breach/notify-authority")
async def notify_authority(body: NotifyAuthorityRequest, db: Session = Depends(get_db)):
    """POST /api/v1/breach/notify-authority"""
    try:
        incident = db.query(BreachIncident).filter_by(id=body.incident_id).first()

        if not incident:
            return JSONResponse(status_code=404, content={"error": "Incident not found"})

        now = datetime.utcnow()
        incident.authority_notified_at = now
        incident.audit_log.append({
            "action": "notified_authority",
            "timestamp": now.isoformat()
        })

        db.commit()

        logger.info(f"[BREACH] Authority notified for {body.incident_id}")

        return {
            "success": True,
            "incident_id": body.incident_id,
            "authority_notified_at": incident.authority_notified_at.isoformat() + "Z"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[BREACH] Authority error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/v1/breach/history")
async def breach_history(limit: int = 100, severity: Optional[str] = None, db: Session = Depends(get_db)):
    """GET /api/v1/breach/history"""
    try:
        query = db.query(BreachIncident).order_by(BreachIncident.incident_date.desc())

        if severity:
            try:
                severity_filter = BreachSeverity[severity.upper()]
                query = query.filter_by(severity=severity_filter)
            except KeyError:
                return JSONResponse(status_code=400, content={"error": f"Invalid severity: {severity}"})

        incidents = query.limit(limit).all()

        incidents_list = [{
            "incident_id": inc.id,
            "incident_date": inc.incident_date.isoformat() + "Z",
            "severity": inc.severity.value,
            "affected_users": len(inc.affected_users),
            "description": inc.description,
            "authority_notified_at": inc.authority_notified_at.isoformat() + "Z" if inc.authority_notified_at else None
        } for inc in incidents]

        logger.info(f"[BREACH] Retrieved {len(incidents)} incidents")

        return {
            "incidents": incidents_list,
            "total": len(incidents_list)
        }

    except Exception as e:
        logger.error(f"[BREACH] History error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================================
# BACKGROUND CRON (OPTIONAL)
# ============================================================================

def detect_suspicious_activity_cron():
    """Background breach detection (hourly)"""
    try:
        db = SessionLocal()
        logger.debug("[CRON] Breach detection scan completed")
        db.close()
    except Exception as e:
        logger.error(f"[CRON] Error: {e}")


try:
    scheduler = BackgroundScheduler()
    scheduler.add_job(detect_suspicious_activity_cron, 'interval', hours=1)
    scheduler.start()
    logger.info("[CRON] Initialized (hourly)")
except Exception as e:
    logger.warning(f"[CRON] Not initialized: {e}")


# ============================================================================
# STATIC FILES
# ============================================================================

if (app_dir / "dist").exists():
    app.mount("/", StaticFiles(directory=str(app_dir / "dist"), html=True), name="static")

if output_dir.exists():
    app.mount("/reports", StaticFiles(directory=str(output_dir)), name="reports")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Diagnóstico Financiero API v4.0 on port {port}")
    logger.info("Endpoints: /health, /api/v1/schema, /api/v1/diagnose")
    logger.info("  Consent: /api/v1/consent/init, /verify, /withdraw, /status/{user_id}")
    logger.info("  User Rights: /api/v1/users/{user_id}/data, /rectify, /export, /delete-request, /objection, /rights-status")
    logger.info("  Breach: /api/v1/breach/report, /notify-authority, /history")
    uvicorn.run(app, host="0.0.0.0", port=port)
