"""ITAP — Backend de produccion. Sirve el instrumento, puntua y genera el Libro Financiero."""
import os, uuid, datetime, tempfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import report_book as rb

app = FastAPI(title="ITAP")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
SESIONES: Dict[str, Dict[str, Any]] = {}
REPORTS_DIR = tempfile.gettempdir()
TIER_LIMIT = {1: 60, 2: 1000, 3: 1000}

class StartPayload(BaseModel):
    email: str
    tier: int

class CompletePayload(BaseModel):
    session_id: str
    email: Optional[str] = None
    respuestas: Dict[str, int] = {}
    datos: Optional[Dict[str, float]] = None

def adaptar_item(it):
    base = {"id": it["id"], "pregunta": it["texto"], "bloque": it.get("faceta", "")}
    if it["tipo"] == "escala":
        base["tipo"] = "opcion_multiple"; base["opciones"] = [o["texto"] for o in it["opciones"]]
    else:
        base["tipo"] = "numerica"; base["unidad"] = it.get("unidad", "")
    return base

def items_para_tier(tier):
    out = [adaptar_item(it) for capa in rb.INST["capas"] for it in capa["items"]]
    return out[:TIER_LIMIT.get(tier, 1000)]

@app.get("/")
def health():
    return {"status": "healthy", "service": "ITAP", "capas": len(rb.INST["capas"]),
            "version": rb.INST["meta"]["version"]}

@app.get("/api/questions/{tier}")
def questions(tier: int):
    items = items_para_tier(tier)
    return {"questions": items, "total_preguntas": len(items)}

@app.post("/api/start")
def start(payload: StartPayload):
    sid = str(uuid.uuid4())
    SESIONES[sid] = {"email": payload.email, "tier": payload.tier}
    return {"session_id": sid}

@app.post("/api/answer")
def answer(payload: dict):
    return {"ok": True}

@app.post("/api/open-answer")
def open_answer(payload: dict):
    return {"ok": True}

@app.post("/api/complete")
def complete(payload: CompletePayload):
    ses = SESIONES.get(payload.session_id, {})
    email = payload.email or ses.get("email", "cliente@itap.com")
    datos = dict(payload.datos or {})
    datos.setdefault("gasto_mensual", 2000)
    datos.setdefault("ingreso_mensual", 3000)
    datos.setdefault("ahorro_mensual", 300)
    datos.setdefault("patrimonio", 30000)
    datos.setdefault("edad", 40)
    cli = {"nombre": ses.get("nombre", email.split("@")[0].title()), "email": email,
           "fecha": datetime.datetime.now().strftime("%d/%m/%Y")}
    out = os.path.join(REPORTS_DIR, "itap_%s.pdf" % payload.session_id)
    try:
        rb.build_book(payload.respuestas, datos, cli, out)
    except Exception as e:
        raise HTTPException(500, "Error generando informe: %s" % e)
    SESIONES.setdefault(payload.session_id, {})["report"] = out
    return {"ok": True, "report_url": "/api/report/%s" % payload.session_id}

@app.get("/api/report/{session_id}")
def report(session_id: str):
    ses = SESIONES.get(session_id, {})
    path = ses.get("report")
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Informe no encontrado")
    return FileResponse(path, media_type="application/pdf", filename="Tu_Libro_Financiero_ITAP.pdf")
