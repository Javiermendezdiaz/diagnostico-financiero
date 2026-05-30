#!/usr/bin/env python3
"""
Diagnóstico Financiero - FastAPI Backend + Static Frontend + GDPR Consent
Single port, all-in-one deployment for Render
UPDATED: Task #23 — ConsentManagement endpoints
"""

import sys
import json
import os
import logging
from pathlib import Path

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# App dir
app_dir = Path(__file__).parent.absolute()
os.chdir(app_dir)

# Create reports dir
output_dir = app_dir / "reports"
output_dir.mkdir(exist_ok=True)

# Import FastAPI
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    sys.exit(1)

# Import diagnostic modules
try:
    from diagnostic_engine import DiagnosticEngine
    from diagnostic_report_generator import DiagnosticReportGenerator
except ImportError as e:
    logger.error(f"Module import error: {e}")
    sys.exit(1)

# Import RGPD modules
try:
    from rgpd_endpoints import add_rgpd_endpoints_to_app
except ImportError as e:
    logger.warning(f"RGPD modules not available: {e}")

# Import open answers + email triggers modules
try:
    from open_answers_processor import encrypt_open_answers, save_diagnosis, OpenAnswerRecord
    from email_triggers import schedule_email_triggers
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    OPEN_ANSWERS_AVAILABLE = True
    # Setup BD for open answers (SQLite by default, PostgreSQL en producción)
    db_url = os.getenv("DATABASE_URL", "sqlite:///./diagnoses.db")
    engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
    SessionLocal = sessionmaker(bind=engine)
except ImportError as e:
    logger.warning(f"Open answers/email triggers not available: {e}")
    OPEN_ANSWERS_AVAILABLE = False

# [NEW] Import ConsentManagement
try:
    from consent_management import ConsentService, ConsentType, ConsentRecord, Base as ConsentBase
    CONSENT_AVAILABLE = True
    # Create tables
    ConsentBase.metadata.create_all(engine)
except ImportError as e:
    logger.warning(f"Consent management not available: {e}")
    CONSENT_AVAILABLE = False

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

# Create diagnostic engine
try:
    diagnostic_engine = DiagnosticEngine(str(schema_path))
    report_generator = DiagnosticReportGenerator(str(output_dir))
    logger.info("Diagnostic engine initialized")
except Exception as e:
    logger.error(f"Engine initialization error: {e}")
    sys.exit(1)

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register RGPD endpoints
try:
    add_rgpd_endpoints_to_app(app)
except NameError:
    logger.warning("RGPD endpoints not available")

# ============ API ENDPOINTS ============

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/api/v1/schema")
def get_schema():
    """Return all 500 questions in flat array format"""
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

# ============ [NEW] CONSENT ENDPOINTS (Task #23) ============

@app.post("/api/v1/consent/init")
async def init_consent_endpoint(request: Request):
    """
    Paso 1: Iniciar flujo consentimiento
    POST /api/v1/consent/init
    Body: {
      "user_id": "user_123",
      "email": "user@example.com",
      "consent_type": "diagnosis"  // diagnosis | email_triggers | data_retention | third_party_dpa
    }
    """
    if not CONSENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Consent management not available")

    try:
        data = await request.json()
        user_id = data.get("user_id")
        email = data.get("email")
        consent_type_str = data.get("consent_type", "diagnosis")
        ip_address = str(request.client.host if request.client else "unknown")
        user_agent = request.headers.get("user-agent", "")

        # Validar
        if not user_id or not email:
            raise HTTPException(status_code=400, detail="user_id and email required")

        consent_type = ConsentType[consent_type_str.upper()]

        session = SessionLocal()
        try:
            record, token = ConsentService.initiate_consent(
                user_id=user_id,
                email=email,
                consent_type=consent_type,
                ip_address=ip_address,
                user_agent=user_agent,
                session=session,
                send_email_func=None  # [TODO] Wire SMTP
            )
            return JSONResponse({
                "consent_id": record.id,
                "status": "pending_verification",
                "email": email,
                "message": f"Email de verificación enviado a {email}. Válido por 48h."
            }, status_code=201)
        finally:
            session.close()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error initiating consent: {e}")
        raise HTTPException(status_code=500, detail="Error initiating consent")

@app.get("/api/v1/consent/verify")
async def verify_consent_endpoint(request: Request, token: str = None):
    """
    Paso 2: Verificar email + activar consentimiento
    GET /api/v1/consent/verify?token=<token>

    Endpoint que el usuario abre desde email
    """
    if not CONSENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Consent management not available")

    if not token:
        raise HTTPException(status_code=400, detail="token parameter required")

    try:
        session = SessionLocal()
        try:
            record = ConsentService.verify_consent(token, session)
            # Mostrar página HTML de confirmación
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Consentimiento Verificado</title>
                <style>
                    body {{ font-family: Arial; text-align: center; margin-top: 50px; }}
                    .success {{ color: #16a766; font-size: 24px; }}
                    .info {{ color: #666; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="success">✓ Consentimiento Verificado</div>
                <div class="info">
                    <p>Tu consentimiento para <strong>{record.consent_type.value}</strong> está activo.</p>
                    <p>Puedes volver a tu diagnóstico financiero.</p>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        finally:
            session.close()

    except ValueError as e:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Error de Verificación</title>
            <style>
                body {{ font-family: Arial; text-align: center; margin-top: 50px; }}
                .error {{ color: #cc3a21; font-size: 18px; }}
            </style>
        </head>
        <body>
            <div class="error">⚠ Error: {str(e)}</div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)
    except Exception as e:
        logger.error(f"Error verifying consent: {e}")
        raise HTTPException(status_code=500, detail="Error verifying consent")

@app.post("/api/v1/consent/withdraw")
async def withdraw_consent_endpoint(request: Request):
    """
    Revocar consentimiento (Art. 7.3)
    POST /api/v1/consent/withdraw
    Body: {
      "user_id": "user_123",
      "consent_type": "diagnosis",  // opcional, si omitido revoca todos
      "reason": "user_request"      // user_request | right_to_be_forgotten
    }
    """
    if not CONSENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Consent management not available")

    try:
        data = await request.json()
        user_id = data.get("user_id")
        consent_type_str = data.get("consent_type")
        reason = data.get("reason", "user_request")

        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")

        consent_type = None
        if consent_type_str:
            consent_type = ConsentType[consent_type_str.upper()]

        session = SessionLocal()
        try:
            withdrawn_count = ConsentService.withdraw_consent(
                user_id=user_id,
                consent_type=consent_type,
                reason=reason,
                session=session
            )

            # [IMPORTANTE] Si reason = "right_to_be_forgotten", marcar datos para borrado
            if reason == "right_to_be_forgotten" and OPEN_ANSWERS_AVAILABLE:
                from open_answers_processor import mark_for_deletion
                # TODO: mark_for_deletion(user_id, session)

            return JSONResponse({
                "user_id": user_id,
                "status": "withdrawn",
                "withdrawn_count": withdrawn_count,
                "message": f"Revocado(s) {withdrawn_count} consentimiento(s)"
            })
        finally:
            session.close()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error withdrawing consent: {e}")
        raise HTTPException(status_code=500, detail="Error withdrawing consent")

@app.get("/api/v1/consent/status/{user_id}")
async def get_consent_status_endpoint(user_id: str):
    """
    Art. 15 (Derecho de acceso): Ver todos los consentimientos y audit trail
    GET /api/v1/consent/status/{user_id}
    """
    if not CONSENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Consent management not available")

    try:
        session = SessionLocal()
        try:
            records = ConsentService.get_user_consents(user_id, session)
            return JSONResponse({
                "user_id": user_id,
                "consents": [r.to_dict() for r in records],
                "total": len(records)
            })
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error getting consent status: {e}")
        raise HTTPException(status_code=500, detail="Error getting consent status")

# ============ EXISTING DIAGNOSTIC ENDPOINT (UPDATED) ============

@app.post("/api/v1/diagnose")
async def diagnose(request: Request):
    """
    Process diagnostic answers (Q1-Q200) + open answers (OP1-OP3).
    RGPD-compliant: encripta respuestas abiertas, programa email triggers.
    [UPDATED] Requiere consentimiento verificado (Art. 7)
    """
    try:
        data = await request.json()
        answers = data.get("answers", {})
        open_answers = data.get("open_answers", {})
        user_id = data.get("user_id", f"user_{int(__import__('time').time())}")
        user_email = data.get("user_email")
        ip_address = data.get("ip_address", str(request.client.host if request.client else "unknown"))
        user_agent = request.headers.get("user-agent", "")

        # [NEW] Verificar consentimiento
        if CONSENT_AVAILABLE and open_answers:
            session_consent = SessionLocal()
            try:
                consent = ConsentService.get_consent_status(
                    user_id=user_id,
                    consent_type=ConsentType.DIAGNOSIS,
                    session=session_consent
                )
                if not consent:
                    return JSONResponse({
                        "success": False,
                        "error": "Consent required for diagnosis processing (Art. 7)",
                        "action": "redirect_to_consent"
                    }, status_code=403)
            finally:
                session_consent.close()

        # Run diagnostic (análisis de Q1-Q200)
        result = diagnostic_engine.diagnose(answers)
        result_dict = result if isinstance(result, dict) else result.__dict__

        # [TASK #46] Procesar respuestas abiertas si están disponibles
        encrypted_open_answers = {}
        email_triggers_scheduled = False

        if OPEN_ANSWERS_AVAILABLE and open_answers:
            try:
                # 1. Encriptar respuestas abiertas (AES-256-GCM)
                encrypted_open_answers = encrypt_open_answers(
                    user_id=user_id,
                    open_answers=open_answers,
                    answers_metadata={"ip_address": ip_address, "user_agent": user_agent}
                )
                logger.info(f"[OPEN_ANSWERS] Encriptadas para {user_id}")

                # 2. Generar diagnosis_id
                import uuid
                diagnosis_id = str(uuid.uuid4())

                # 3. Guardar en BD (OpenAnswerRecord con retención 12 meses)
                session = SessionLocal()
                try:
                    saved_record = __import__('open_answers_processor').save_diagnosis(
                        user_id=user_id,
                        diagnosis_id=diagnosis_id,
                        closed_answers=answers,
                        encrypted_open_answers=encrypted_open_answers,
                        scoring_result=result_dict.get("scoring", {}),
                        inconsistencies=result_dict.get("inconsistencies", {}),
                        key_variables=result_dict.get("key_variables", {}),
                        session=session
                    )
                    logger.info(f"[OPEN_ANSWERS] Guardado en BD: {diagnosis_id}")

                    # 4. Programar email triggers (30d + 180d) si user_email disponible
                    if user_email:
                        schedule_email_triggers(
                            user_id=user_id,
                            diagnosis_id=diagnosis_id,
                            email=user_email,
                            open_answers=open_answers,
                            session=session
                        )
                        email_triggers_scheduled = True
                        logger.info(f"[EMAIL_TRIGGERS] Programados para {user_email}: +30d, +180d")

                    session.commit()

                except Exception as e:
                    session.rollback()
                    logger.error(f"[OPEN_ANSWERS] Error guardando/triggers: {str(e)}")
                finally:
                    session.close()

            except Exception as e:
                logger.error(f"[OPEN_ANSWERS] Error procesando respuestas abiertas: {str(e)}")
                # Continuar sin open answers (fallback)

        # Generate PDF report (con inyección de open_answers si disponibles)
        report_filename = f"{user_id}_diagnostic.pdf"
        pdf_path = report_generator.generate_report(
            result,
            report_filename,
            open_answers=open_answers if open_answers else None
        )

        # Return result
        response = {
            "success": True,
            "results": result_dict,
            "report_path": str(pdf_path),
            "user_id": user_id,
        }

        # Agregar metadata de open answers si fueron procesadas
        if encrypted_open_answers:
            response["open_answers_processed"] = True
            response["email_triggers_scheduled"] = email_triggers_scheduled

        return response

    except Exception as e:
        logger.error(f"Diagnose error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ============ STATIC FILES ============

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    Serve static files or fallback to index.html for single-page app routing.
    This route is checked AFTER all other routes, so API endpoints take precedence.
    """
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.exceptions import HTTPException
    import os as os_module

    # Try to serve the actual file if it exists
    file_path = app_dir / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))

    # For CSS, JS, and other assets, return 404 if they don't exist
    if any(full_path.endswith(ext) for ext in ['.css', '.js', '.json', '.png', '.jpg', '.ico', '.svg', '.woff', '.woff2']):
        raise HTTPException(status_code=404, detail="Asset not found")

    # For other requests, serve index.html (SPA fallback)
    index_html = app_dir / "index.html"
    if index_html.exists():
        with open(str(index_html), 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())

    raise HTTPException(status_code=404, detail="Not found")

# ============ MAIN ============

if __name__ == "__main__":
    # Get port from environment (Render sets PORT env var)
    port = int(os.getenv("PORT", 8000))

    logger.info(f"Starting Diagnóstico Financiero on port {port}")
    logger.info(f"Frontend: http://localhost:{port}/")
    logger.info(f"API: http://localhost:{port}/api/v1/schema")
    logger.info(f"Consent Management: /api/v1/consent/init, /verify, /withdraw, /status")

    # Run uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
