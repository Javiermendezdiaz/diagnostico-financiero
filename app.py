from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Diagnostico Financiero - Production API")

# CORS para produccion.
# IMPORTANTE: con allow_origins=["*"] el navegador exige allow_credentials=False.
# El frontend no envia cookies/credenciales, asi que esta es la combinacion correcta.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Modelos de entrada (el frontend envia JSON en el body, NO query params).
# Esto corrige el error 422 que rompia /api/start, /api/open-answer y /complete.
# ---------------------------------------------------------------------------
class StartPayload(BaseModel):
    email: str
    tier: int

class AnswerPayload(BaseModel):
    session_id: str
    question_id: int
    answer_value: int

class OpenAnswerPayload(BaseModel):
    session_id: str
    question_id: int
    answer_text: str

class CompletePayload(BaseModel):
    session_id: str

# ---------------------------------------------------------------------------
# Banco de preguntas
# ---------------------------------------------------------------------------
# 200 preguntas de opcion multiple, estructuradas tal como las lee el frontend
PREGUNTAS = [
    {
        "id": i,
        "bloque": f"Bloque {((i - 1) // 20) + 1}",
        "pregunta": f"Pregunta de auditoria financiera clave numero {i} para analisis de riesgo.",
        "tipo": "opcion_multiple",
        "opciones": ["Cumple totalmente", "Cumple parcialmente", "No cumple", "No aplica"],
    }
    for i in range(1, 201)
]

# 20 preguntas abiertas (analisis cualitativo)
ABIERTAS = [
    {
        "id": i,
        "bloque": "Bloque Final - Analisis Cualitativo",
        "pregunta": f"Describa la situacion de la empresa respecto al punto critico de control {i - 200}.",
        "tipo": "abierta",
    }
    for i in range(201, 221)
]


@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Diagnostico Financiero"}


@app.get("/api/questions/{tier}")
def get_questions(tier: int):
    # Tier 2 y 3: pack completo de 220 preguntas (200 cerradas + 20 abiertas)
    if tier >= 2:
        return {
            "questions": PREGUNTAS + ABIERTAS,
            "total_preguntas": len(PREGUNTAS) + len(ABIERTAS),
        }
    # Tier 1: diagnostico rapido (primeras 100 preguntas cerradas)
    return {
        "questions": PREGUNTAS[:100],
        "total_preguntas": 100,
    }


@app.post("/api/start")
def start(payload: StartPayload):
    # En produccion aqui se crearia y persistiria la sesion.
    return {"session_id": "ok", "email": payload.email, "tier": payload.tier}


@app.post("/api/answer")
def answer(payload: AnswerPayload):
    return {"ok": True}


@app.post("/api/open-answer")
def open_answer(payload: OpenAnswerPayload):
    return {"ok": True}


@app.post("/api/complete")
def complete(payload: CompletePayload):
    return {"ok": True}
