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

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key-change-in-prod")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True, index=True)
    plan_id = Column(Integer, index=True)
    text = Column(String)
    type = Column(String)
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

class DraftCreateRequest(BaseModel):
    user_email: str
    plan: int = 1

class DraftResponseRequest(BaseModel):
    question_id: str
    answer: str
    order: int
    type: str
    open_text: str = ""

class QuestionNavigationRequest(BaseModel):
    target_order: int = None

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
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM draft_responses"))
        db.execute(text("DELETE FROM drafts"))
        db.execute(text("DELETE FROM questions"))
        db.commit()
        print("Tablas limpiadas")
    except:
        print("Primera inicializacion")
    
    try:
        for i in range(1, 101):
            q = Question(id=f"Q{str(i).zfill(3)}", plan_id=1, text=f"Pregunta {i}", type="likert", order=i)
            db.add(q)
        for i in range(1, 201):
            q = Question(id=f"Q{str(100 + i).zfill(3)}", plan_id=2, text=f"Pregunta {i}", type="likert" if i % 2 == 0 else "open", order=i)
            db.add(q)
        for i in range(1, 221):
            q = Question(id=f"Q{str(300 + i).zfill(3)}", plan_id=3, text=f"Pregunta {i}", type="likert" if i % 3 == 0 else "open", order=i)
            db.add(q)
        db.commit()
        print("520 preguntas seeding OK")
    except Exception as e:
        db.rollback()
        print(f"Error seeding: {e}")
    finally:
        db.close()

seed_questions()

@app.post("/api/draft/create")
def create_draft(request: DraftCreateRequest, db: Session = Depends(get_db)):
    draft_id = f"DRAFT_{datetime.utcnow().timestamp()}"
    session_token = generate_session_token(draft_id)
    draft = Draft(id=draft_id, user_email=request.user_email, plan=request.plan, session_token=session_token)
    db.add(draft)
    db.commit()
    return {"draft_id": draft_id, "session_token": session_token}

@app.get("/api/draft/banco-completo")
def get_banco_completo(db: Session = Depends(get_db)):
    preguntas = db.query(Question).filter(Question.plan_id == 1).order_by(Question.order).all()
    return {"preguntas": [{"id": q.id, "order": q.order, "text": q.text, "type": q.type} for q in preguntas]}

@app.get("/api/draft/{draft_id}/question/first")
def get_next_question(draft_id: str, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    max_order_answered = db.query(func.max(DraftResponse.order)).filter(DraftResponse.draft_id == draft_id).scalar()
    next_order = 1 if max_order_answered is None else max_order_answered + 1
    question = db.query(Question).filter(Question.plan_id == draft.plan, Question.order == next_order).first()
    if not question:
        return {"isComplete": True, "session_token": draft.session_token, "total": db.query(func.count(Question.id)).filter(Question.plan_id == draft.plan).scalar()}
    return {"question": {"id": question.id, "text": question.text, "type": question.type, "order": question.order, "required": True}, "session_token": draft.session_token, "total": db.query(func.count(Question.id)).filter(Question.plan_id == draft.plan).scalar()}

@app.post("/api/draft/{draft_id}/answer")
def submit_answer(draft_id: str, request: DraftResponseRequest, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    response = DraftResponse(id=f"RESP_{datetime.utcnow().timestamp()}", draft_id=draft_id, question_id=request.question_id, answer=request.answer, order=request.order, type=request.type, low_quality=is_low_quality(request.answer))
    db.add(response)
    total_questions = db.query(func.count(Question.id)).filter(Question.plan_id == draft.plan).scalar()
    is_complete = request.order >= total_questions
    if is_complete:
        draft.is_complete = True
    db.commit()
    return {"success": True, "isComplete": is_complete, "session_token": draft.session_token}

@app.post("/api/draft/{draft_id}/question")
def get_question_by_order(draft_id: str, request: QuestionNavigationRequest, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Borrador no encontrado")
    if request.target_order is not None:
        question = db.query(Question).filter(Question.plan_id == draft.plan, Question.order == request.target_order).first()
        if not question:
            return {"isComplete": True, "session_token": draft.session_token}
        return {"question": {"id": question.id, "text": question.text, "type": question.type, "order": question.order, "required": True}, "session_token": draft.session_token}
    max_order = db.query(func.max(DraftResponse.order)).filter(DraftResponse.draft_id == draft_id).scalar()
    if max_order is None or max_order <= 1:
        raise HTTPException(status_code=400, detail="No hay pregunta anterior")
    prev_order = max_order - 1
    question = db.query(Question).filter(Question.plan_id == draft.plan, Question.order == prev_order).first()
    if not question:
        raise HTTPException(status_code=404, detail="Pregunta anterior no encontrada")
    return {"question": {"id": question.id, "text": question.text, "type": question.type, "order": question.order, "required": True}, "session_token": draft.session_token}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ITAP Tier 2"}

@app.get("/")
def serve_frontend():
    frontend_path = Path(__file__).parent / "frontend_itap_tier2.html"
    if frontend_path.exists():
        return FileResponse(str(frontend_path), media_type="text/html")
    return {"message": "Frontend ITAP Tier 2"}

@app.get("/api/ejecutar-migracion-itap-tier2-secreta")
def ejecutar_migracion_temporal(db: Session = Depends(get_db)):
    try:
        db.execute(text("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS max_closed_questions INT DEFAULT 100"))
        db.execute(text("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS max_open_questions INT DEFAULT 20"))
        db.execute(text("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS closed_answered_count INT DEFAULT 0"))
        db.execute(text("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS open_answered_count INT DEFAULT 0"))
        db.execute(text("ALTER TABLE drafts ADD COLUMN IF NOT EXISTS is_finalized BOOLEAN DEFAULT FALSE"))
        db.execute(text("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_drafts_finalized ON drafts(is_finalized)"))
        db.execute(text("CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_unique_draft_question ON draft_responses(draft_id, question_id)"))
        db.commit()
        return {"status": "success", "message": "Migracion ejecutada", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e), "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
