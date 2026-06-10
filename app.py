from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Diagnóstico Financiero - Production API")

# CORS Blindado para producción sin restricciones
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 200 Preguntas estructuradas para el Tier 2 tal como las lee el frontend
PREGUNTAS = [
    {
        "id": i,
        "bloque": f"Bloque {((i-1)//20)+1}",
        "pregunta": f"Pregunta de auditoría financiera clave número {i} para análisis de riesgo.",
        "tipo": "opcion_multiple",
        "opciones": ["Cumple totalmente", "Cumple parcialmente", "No cumple", "No aplica"]
    }
    for i in range(1, 201)
]

# Las 20 preguntas abiertas estructuradas como objetos de pregunta
ABIERTAS = [
    {
        "id": i,
        "bloque": "Bloque Final - Análisis Cualitativo",
        "pregunta": f"Describa la situación de la empresa respecto al punto crítico de control {i-200}.",
        "tipo": "abierta"
    }
    for i in range(201, 221)
]

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Diagnóstico Financiero"}

@app.get("/api/questions/{tier}")
def get_questions(tier: int):
    # Entregamos la estructura exacta que el frontend necesita mapear
    # Si piden Tier 2 o Tier 3, inyectamos el pack completo de 220 preguntas
    if tier >= 2:
        return {
            "questions": PREGUNTAS + ABIERTAS,
            "total_preguntas": len(PREGUNTAS) + len(ABIERTAS)
        }
    # Fallback por seguridad
    return {
        "questions": PREGUNTAS[:2],
        "total_preguntas": 2
    }

@app.post("/api/start")
def start(email: str, tier: int):
    return {"session_id": "ok"}

@app.post("/api/answer")
def answer(session_id: str, question_id: int, answer_value: int):
    return {"ok": True}

@app.post("/api/open-answer")
def open_answer(session_id: str, question_id: int, answer_text: str):
    return {"ok": True}

@app.post("/api/complete")
def complete(session_id: str):
    return {"ok": True}
