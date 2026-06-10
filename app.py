from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PREGUNTAS = [{"id": i, "pregunta": f"Pregunta {i}", "tipo": "escala"} for i in range(1, 201)]
ABIERTAS = [f"Abierta {i}" for i in range(1, 21)]

@app.get("/api/questions/{tier}")
def get_questions(tier: int):
    return {"questions": PREGUNTAS, "open_questions": ABIERTAS}

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
