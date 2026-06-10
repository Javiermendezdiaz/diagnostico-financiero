"""ITAP — Backend de produccion (hardened). Instrumento + motor + Libro Financiero con persistencia y regeneracion bajo demanda."""
import os, uuid, json, datetime, tempfile, sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import report_book as rb

app = FastAPI(title="ITAP")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
REPORTS_DIR = tempfile.gettempdir()
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "itap_sessions.db")
TIER_LIMIT = {1: 60, 2: 1000, 3: 1000}

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sesiones(
            id TEXT PRIMARY KEY, email TEXT, tier INTEGER,
            respuestas TEXT, datos TEXT, creado TEXT)""")
init_db()

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

def datos_completos(d):
    d = dict(d or {})
    d.setdefault("gasto_mensual", 2000); d.setdefault("ingreso_mensual", 3000)
    d.setdefault("ahorro_mensual", 300); d.setdefault("patrimonio", 30000); d.setdefault("edad", 40)
    return d

def generar_pdf(sid, email, respuestas, datos):
    cli = {"nombre": email.split("@")[0].title(), "email": email,
           "fecha": datetime.datetime.now().strftime("%d/%m/%Y")}
    out = os.path.join(REPORTS_DIR, "itap_%s.pdf" % sid)
    rb.build_book(respuestas, datos_completos(datos), cli, out)
    return out

@app.get("/")
def health():
    return {"status": "healthy", "service": "ITAP", "capas": len(rb.INST["capas"]),
            "version": rb.INST["meta"]["version"], "persistencia": "sqlite"}

@app.get("/api/questions/{tier}")
def questions(tier: int):
    items = items_para_tier(tier)
    return {"questions": items, "total_preguntas": len(items)}

@app.post("/api/start")
def start(payload: StartPayload):
    sid = str(uuid.uuid4())
    with db() as c:
        c.execute("INSERT INTO sesiones(id,email,tier,respuestas,datos,creado) VALUES(?,?,?,?,?,?)",
                  (sid, payload.email, payload.tier, "{}", "{}",
                   datetime.datetime.utcnow().isoformat()))
    return {"session_id": sid}

@app.post("/api/answer")
def answer(payload: dict):
    return {"ok": True}

@app.post("/api/open-answer")
def open_answer(payload: dict):
    return {"ok": True}

@app.post("/api/complete")
def complete(payload: CompletePayload):
    with db() as c:
        row = c.execute("SELECT email FROM sesiones WHERE id=?", (payload.session_id,)).fetchone()
    email = payload.email or (row["email"] if row else "cliente@itap.com")
    datos = datos_completos(payload.datos)
    # persistir respuestas+datos para poder regenerar
    with db() as c:
        c.execute("UPDATE sesiones SET respuestas=?, datos=?, email=? WHERE id=?",
                  (json.dumps(payload.respuestas), json.dumps(datos), email, payload.session_id))
        if c.total_changes == 0:
            c.execute("INSERT OR REPLACE INTO sesiones(id,email,tier,respuestas,datos,creado) VALUES(?,?,?,?,?,?)",
                      (payload.session_id, email, 2, json.dumps(payload.respuestas), json.dumps(datos),
                       datetime.datetime.utcnow().isoformat()))
    try:
        generar_pdf(payload.session_id, email, payload.respuestas, datos)
    except Exception as e:
        raise HTTPException(500, "Error generando informe: %s" % e)
    return {"ok": True, "report_url": "/api/report/%s" % payload.session_id}

@app.get("/api/report/{session_id}")
def report(session_id: str):
    path = os.path.join(REPORTS_DIR, "itap_%s.pdf" % session_id)
    if not os.path.exists(path):
        # regenerar desde la sesion persistida (sobrevive a reinicios de instancia)
        with db() as c:
            row = c.execute("SELECT email,respuestas,datos FROM sesiones WHERE id=?", (session_id,)).fetchone()
        if not row or row["respuestas"] in (None, "{}"):
            raise HTTPException(404, "Informe no encontrado")
        try:
            generar_pdf(session_id, row["email"], json.loads(row["respuestas"]), json.loads(row["datos"]))
        except Exception as e:
            raise HTTPException(500, "Error regenerando informe: %s" % e)
    return FileResponse(path, media_type="application/pdf", filename="Tu_Libro_Financiero_ITAP.pdf")
