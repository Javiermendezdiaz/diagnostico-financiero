from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-change-in-prod")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELOS ORM
# ============================================================================

class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True, index=True)
    plan_id = Column(Integer, index=True)
    text = Column(String)
    type = Column(String)  # "likert" o "open"
    order = Column(Integer, index=True)

class Draft(Base):
    __tablename__ = "drafts"
    id = Column(String, primary_key=True, index=True)
    user_email = Column(String, index=True)
    plan = Column(Integer, default=1)
    session_token = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_complete = Column(Boolean, default=False)

class DraftResponse(Base):
    __tablename__ = "draft_responses"
    id = Column(String, primary_key=True, index=True)
    draft_id = Column(String, index=True)
    question_id = Column(String, index=True)
    answer = Column(Text)
    order = Column(Integer, index=True)
    type = Column(String)
    low_quality = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ============================================================================
# ESQUEMAS PYDANTIC
# ============================================================================

class DraftCreateRequest(BaseModel):
    user_email: str
    plan: int = 1

class DraftCreateResponse(BaseModel):
    draft_id: str

class DraftResponseRequest(BaseModel):
    question_id: str
    answer: str
    order: int
    type: str
    open_text: str = ""

class QuestionNavigationRequest(BaseModel):
    target_order: int = None

# ============================================================================
# UTILIDADES
# ============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_session_token(draft_id: str) -> str:
    payload = {
        "draft_id": draft_id,
        "exp": datetime.utcnow() + timedelta(hours=4)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def is_low_quality(answer: str) -> bool:
    return len(answer.strip()) < 10 or (len(answer) > 0 and answer.count(" ") / len(answer) > 0.8)

def seed_questions():
    """Seed 520 preguntas en la base de datos"""
    db = SessionLocal()
    try:
        # Limpiar datos anteriores
        db.execute(text("DELETE FROM draft_responses"))
        db.execute(text("DELETE FROM drafts"))
        db.execute(text("DELETE FROM questions"))
        db.commit()
        print("✅ Tablas limpiadas antes de seeding")
    except Exception as clean_error:
        print("📝 Primera inicialización (sin datos previos)")

    try:
        # Plan 1: 100 preguntas
        for i in range(1, 101):
            q = Question(
                id=f"Q{str(i).zfill(3)}",
                plan_id=1,
                text=f"Pregunta {i} del Plan 1 — ¿Cómo calificas este aspecto de tu patrimonio?",
                type="likert",
                order=i
            )
            db.add(q)

        # Plan 2: 200 preguntas
        for i in range(1, 201):
            q = Question(
                id=f"Q{str(100 + i).zfill(3)}",
                plan_id=2,
                text=f"Pregunta {i} del Plan 2 — Evaluación profunda",
                type="likert" if i % 2 == 0 else "open",
                order=i
            )
            db.add(q)

        # Plan 3: 220 preguntas
        for i in range(1, 221):
            q = Question(
                id=f"Q{str(300 + i).zfill(3)}",
                plan_id=3,
                text=f"Pregunta {i} del Plan 3 — Análisis completo",
                type="likert" if i % 3 == 0 else "open",
                order=i
            )
            db.add(q)

        db.commit()
        print("✅ 520 preguntas insertadas correctamente")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al seedear: {e}")
    finally:
        db.close()

# Seed al iniciar
seed_questions()

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post("/api/draft/create")
def create_draft(request: DraftCreateRequest, db: Session = Depends(get_db)):
    """Crear un nuevo borrador de cuestionario"""
    draft_id = f"DRAFT_{datetime.utcnow().timestamp()}"
    session_token = generate_session_token(draft_id)

    draft = Draft(
        id=draft_id,
        user_email=request.user_email,
        plan=request.plan,
        session_token=session_token
    )
    db.add(draft)
    db.commit()

    return {"draft_id": draft_id, "session_token": session_token}

@app.get("/api/draft/banco-completo")
def get_banco_completo(db: Session = Depends(get_db)):
    """Devuelve todas las 520 preguntas del Plan 1 para descarga inicial en frontend"""
    try:
        preguntas = db.query(Question).filter(Question.plan_id == 1).order_by(Question.order).all()

        return {
            "preguntas": [
                {
                    "id": q.id,
                    "order": q.order,
                    "text": q.text,
                    "type": q.type
                } for q in preguntas
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener banco: {str(e)}")

@app.get("/api/draft/{draft_id}/question/first")
def get_next_question(draft_id: str, db: Session = Depends(get_db)):
    """
    🎯 ENDPOINT CORREGIDO: Devuelve la SIGUIENTE pregunta sin responder
    basada en el progreso REAL del usuario.
    """
    try:
        # Validar que el borrador existe
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail="Borrador no encontrado")

        # PASO 1: Obtener el MÁXIMO order que ya fue respondido
        max_order_answered = db.query(func.max(DraftResponse.order)).filter(
            DraftResponse.draft_id == draft_id
        ).scalar()

        # PASO 2: Calcular el siguiente order
        if max_order_answered is None:
            # Nada respondido aún → devolver pregunta 1
            next_order = 1
        else:
            # Ya respondió algo → siguiente pregunta
            next_order = max_order_answered + 1

        # PASO 3: Obtener la pregunta del siguiente order
        question = db.query(Question).filter(
            Question.plan_id == draft.plan,
            Question.order == next_order
        ).first()

        # PASO 4: Si no hay más preguntas, cuestionario completado
        if not question:
            return {
                "isComplete": True,
                "session_token": draft.session_token,
                "total": db.query(func.count(Question.id)).filter(
                    Question.plan_id == draft.plan
                ).scalar()
            }

        # PASO 5: Devolver la siguiente pregunta
        return {
            "question": {
                "id": question.id,
                "text": question.text,
                "type": question.type,
                "order": question.order,
                "required": True
            },
            "session_token": draft.session_token,
            "total": db.query(func.count(Question.id)).filter(
                Question.plan_id == draft.plan
            ).scalar()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en GET /question/first: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/draft/{draft_id}/answer")
def submit_answer(draft_id: str, request: DraftResponseRequest, db: Session = Depends(get_db)):
    """Guardar una respuesta del usuario"""
    try:
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail="Borrador no encontrado")

        # Crear respuesta
        response = DraftResponse(
            id=f"RESP_{datetime.utcnow().timestamp()}",
            draft_id=draft_id,
            question_id=request.question_id,
            answer=request.answer,
            order=request.order,
            type=request.type,
            low_quality=is_low_quality(request.answer)
        )
        db.add(response)

        # Verificar si es la última pregunta
        total_questions = db.query(func.count(Question.id)).filter(
            Question.plan_id == draft.plan
        ).scalar()

        is_complete = request.order >= total_questions
        if is_complete:
            draft.is_complete = True

        db.commit()

        return {
            "success": True,
            "isComplete": is_complete,
            "session_token": draft.session_token
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/draft/{draft_id}/question")
def get_question_by_order(draft_id: str, request: QuestionNavigationRequest, db: Session = Depends(get_db)):
    """
    Obtener pregunta por orden específico (si target_order) o ir atrás (si no).

    - Si request.target_order está presente: devuelve esa pregunta específica
    - Si no: devuelve la pregunta anterior (botón Atrás)
    """
    try:
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail="Borrador no encontrado")

        # CASO 1: Navegación por target_order (desde frontend)
        if request.target_order is not None:
            target_order = request.target_order
            question = db.query(Question).filter(
                Question.plan_id == draft.plan,
                Question.order == target_order
            ).first()

            if not question:
                # Si no existe esa pregunta, devolver isComplete
                return {
                    "isComplete": True,
                    "session_token": draft.session_token
                }

            return {
                "question": {
                    "id": question.id,
                    "text": question.text,
                    "type": question.type,
                    "order": question.order,
                    "required": True
                },
                "session_token": draft.session_token
            }

        # CASO 2: Ir atrás (botón Atrás)
        max_order = db.query(func.max(DraftResponse.order)).filter(
            DraftResponse.draft_id == draft_id
        ).scalar()

        if max_order is None or max_order <= 1:
            raise HTTPException(status_code=400, detail="No hay pregunta anterior")

        prev_order = max_order - 1
        question = db.query(Question).filter(
            Question.plan_id == draft.plan,
            Question.order == prev_order
        ).first()

        if not question:
            raise HTTPException(status_code=404, detail="Pregunta anterior no encontrada")

        return {
            "question": {
                "id": question.id,
                "text": question.text,
                "type": question.type,
                "order": question.order,
                "required": True
            },
            "session_token": draft.session_token
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ITAP Tier 2"}

@app.get("/")
def serve_frontend():
    """Servir frontend HTML desde Render"""
    frontend_path = Path(__file__).parent / "frontend_itap_tier2.html"
    if frontend_path.exists():
        return FileResponse(str(frontend_path), media_type="text/html")
    else:
        return {"message": "Frontend ITAP Tier 2 - Use /api/draft endpoints"}


# ============================================================================
# ENDPOINT TEMPORAL: Ejecutar migración ITAP Tier 2 (BORRAR DESPUÉS)
# ============================================================================
@app.get("/api/ejecutar-migracion-itap-tier2-secreta")
def ejecutar_migracion_temporal(db: Session = Depends(get_db)):
    """Endpoint temporal para ejecutar la migración SQL de segmentación de planes"""
    try:
        migration_sql = """
        ALTER TABLE drafts
          ADD COLUMN max_closed_questions INT DEFAULT 100 NOT NULL,
          ADD COLUMN max_open_questions INT DEFAULT 20 NOT NULL,
          ADD COLUMN closed_answered_count INT DEFAULT 0 NOT NULL,
          ADD COLUMN open_answered_count INT DEFAULT 0 NOT NULL,
          ADD COLUMN is_finalized BOOLEAN DEFAULT FALSE NOT NULL;

        CREATE INDEX CONCURRENTLY idx_drafts_finalized
          ON drafts(is_finalized)
          WHERE is_finalized = TRUE;

        CREATE INDEX CONCURRENTLY idx_drafts_active
          ON drafts(id, is_finalized)
          WHERE is_finalized = FALSE;

        ALTER TABLE draft_responses
          ADD CONSTRAINT unique_draft_question UNIQUE (draft_id, question_id);

        CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_unique_draft_question
          ON draft_responses (draft_id, question_id);

        UPDATE drafts
          SET max_closed_questions = CASE
                WHEN plan = 1 THEN 100
                WHEN plan = 2 THEN 200
                WHEN plan = 3 THEN 200
                ELSE 100
              END,
              max_open_questions = 20,
              closed_answered_count = 0,
              open_answered_count = 0,
              is_finalized = FALSE
          WHERE max_closed_questions IS NULL;
        """

        db.execute(text(migration_sql))
        db.commit()

        return {
            "status": "success",
            "message": "Migración ITAP Tier 2 ejecutada con éxito en producción",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Error en migración: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

