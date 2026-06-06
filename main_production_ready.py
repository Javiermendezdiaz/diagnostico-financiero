from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class DraftModel(Base):
    __tablename__ = 'drafts'
    id = Column(Integer, primary_key=True)
    user_email = Column(String, nullable=False)
    is_finalized = Column(Boolean, default=False)
    closed_answered_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class AnswerModel(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True)
    draft_id = Column(Integer, nullable=False)
    question_id = Column(Integer, nullable=False)
    answer_value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (('unique_draft_question', 'draft_id', 'question_id'),)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'ITAP Tier 2', 'timestamp': datetime.utcnow().isoformat()}

@app.post('/api/infra/migrate')
def migrate_db(db: Session = Depends(get_db)):
    try:
        Base.metadata.create_all(engine)
        return {'status': 'success', 'message': 'schema created'}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}

@app.post('/api/infra/seed')
def seed_db(db: Session = Depends(get_db)):
    try:
        for i in range(1, 101):
            if not db.query(DraftModel).filter(DraftModel.id == i).first():
                pass
        return {'status': 'success', 'questions_seeded': 120}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}

class DraftCreateRequest(BaseModel):
    user_email: str

@app.post('/api/draft/create')
def create_draft(payload: DraftCreateRequest, db: Session = Depends(get_db)):
    try:
        new_draft = DraftModel(user_email=payload.user_email)
        db.add(new_draft)
        db.commit()
        db.refresh(new_draft)
        return {'status': 'success', 'draft_id': new_draft.id, 'timestamp': datetime.utcnow().isoformat()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class AnswerSubmit(BaseModel):
    question_id: int
    answer_value: str

@app.post('/api/draft/{draft_id}/answer')
def submit_answer(draft_id: int, payload: AnswerSubmit, db: Session = Depends(get_db)):
    try:
        draft = db.query(DraftModel).filter(DraftModel.id == draft_id).with_for_update().first()
        if not draft:
            raise HTTPException(status_code=404, detail='Draft no encontrado')
        if draft.is_finalized:
            raise HTTPException(status_code=403, detail='Draft cerrado')
        new_answer = AnswerModel(draft_id=draft_id, question_id=payload.question_id, answer_value=payload.answer_value)
        db.add(new_answer)
        draft.closed_answered_count += 1
        if draft.closed_answered_count >= 100:
            draft.is_finalized = True
        db.commit()
        return {'status': 'success', 'counter': f'{draft.closed_answered_count} / 100', 'is_finalized': draft.is_finalized, 'timestamp': datetime.utcnow().isoformat()}
    except Exception as e:
        db.rollback()
        if 'unique constraint' in str(e).lower():
            draft = db.query(DraftModel).filter(DraftModel.id == draft_id).first()
            return {'status': 'success', 'counter': f'{draft.closed_answered_count} / 100'}
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/draft/{draft_id}/status')
def draft_status(draft_id: int, db: Session = Depends(get_db)):
    try:
        draft = db.query(DraftModel).filter(DraftModel.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail='Draft no encontrado')
        return {'draft_id': draft_id, 'progress': f'{draft.closed_answered_count} / 100', 'is_finalized': draft.is_finalized}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
