"""ITAP — Backend de produccion. Instrumento + motor + Libros (individual y pareja). Profundidad por tier."""
import os, uuid, json, datetime, tempfile, sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict
import report_book as rb
import report_couple as rc

app = FastAPI(title="ITAP")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
REPORTS_DIR = tempfile.gettempdir()
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "itap_sessions.db")
TIER_LIMIT = {1: 60, 2: 1000, 3: 1000}
TIER_DEPTH = {1: "esencial", 2: "completo", 3: "completo"}

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sesiones(
            id TEXT PRIMARY KEY, email TEXT, tier INTEGER,
            respuestas TEXT, datos TEXT, creado TEXT, pareja_de TEXT)""")
        cols = [r["name"] for r in c.execute("PRAGMA table_info(sesiones)")]
        if "pareja_de" not in cols:
            c.execute("ALTER TABLE sesiones ADD COLUMN pareja_de TEXT")
init_db()

class StartPayload(BaseModel):
    email: str
    tier: int

class CompletePayload(BaseModel):
    session_id: str
    email: Optional[str] = None
    respuestas: Dict[str, int] = {}
    datos: Optional[Dict[str, float]] = None
    pareja_de: Optional[str] = None   # codigo del primer miembro (si soy el segundo)

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

def _cli(email):
    return {"nombre": email.split("@")[0].replace("."," ").title(), "email": email,
            "fecha": datetime.datetime.now().strftime("%d/%m/%Y")}

def generar_pdf(sid, email, respuestas, datos, tier):
    out = os.path.join(REPORTS_DIR, "itap_%s.pdf" % sid)
    rb.build_book(respuestas, datos_completos(datos), _cli(email), out, depth=TIER_DEPTH.get(tier, "completo"))
    return out

def generar_couple(out, arow, brow):
    rc.build_couple(json.loads(arow["respuestas"]), datos_completos(json.loads(arow["datos"])), _cli(arow["email"]),
                    json.loads(brow["respuestas"]), datos_completos(json.loads(brow["datos"])), _cli(brow["email"]), out)

@app.get("/")
def health():
    return {"status": "healthy", "service": "ITAP", "capas": len(rb.INST["capas"]),
            "version": rb.INST["meta"]["version"], "persistencia": "sqlite", "pareja": True}

@app.get("/api/questions/{tier}")
def questions(tier: int):
    items = items_para_tier(tier)
    return {"questions": items, "total_preguntas": len(items)}

@app.post("/api/start")
def start(payload: StartPayload):
    sid = str(uuid.uuid4())
    with db() as c:
        c.execute("INSERT INTO sesiones(id,email,tier,respuestas,datos,creado,pareja_de) VALUES(?,?,?,?,?,?,?)",
                  (sid, payload.email, payload.tier, "{}", "{}", datetime.datetime.utcnow().isoformat(), None))
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
        row = c.execute("SELECT email,tier FROM sesiones WHERE id=?", (payload.session_id,)).fetchone()
    email = payload.email or (row["email"] if row else "cliente@itap.com")
    tier = row["tier"] if row else 2
    datos = datos_completos(payload.datos)
    with db() as c:
        c.execute("UPDATE sesiones SET respuestas=?, datos=?, email=?, pareja_de=? WHERE id=?",
                  (json.dumps(payload.respuestas), json.dumps(datos), email, payload.pareja_de, payload.session_id))
        if c.total_changes == 0:
            c.execute("INSERT OR REPLACE INTO sesiones(id,email,tier,respuestas,datos,creado,pareja_de) VALUES(?,?,?,?,?,?,?)",
                      (payload.session_id, email, tier, json.dumps(payload.respuestas), json.dumps(datos),
                       datetime.datetime.utcnow().isoformat(), payload.pareja_de))
    # --- Flujo de pareja (Tier 3) ---
    if tier == 3:
        if not payload.pareja_de:
            # Soy el primero: devuelvo el codigo para compartir
            return {"ok": True, "needs_partner": True, "codigo": payload.session_id}
        # Soy el segundo: cruzo con mi pareja
        with db() as c:
            arow = c.execute("SELECT email,respuestas,datos FROM sesiones WHERE id=?", (payload.pareja_de,)).fetchone()
            brow = c.execute("SELECT email,respuestas,datos FROM sesiones WHERE id=?", (payload.session_id,)).fetchone()
        if not arow or arow["respuestas"] in (None, "{}"):
            raise HTTPException(409, "Tu pareja todavia no ha terminado su cuestionario.")
        out = os.path.join(REPORTS_DIR, "itap_%s.pdf" % payload.session_id)
        try:
            generar_couple(out, arow, brow)
        except Exception as e:
            raise HTTPException(500, "Error generando informe de pareja: %s" % e)
        return {"ok": True, "es_pareja": True, "report_url": "/api/report/%s" % payload.session_id}
    # --- Individual (Tier 1 y 2) ---
    try:
        generar_pdf(payload.session_id, email, payload.respuestas, datos, tier)
    except Exception as e:
        raise HTTPException(500, "Error generando informe: %s" % e)
    return {"ok": True, "report_url": "/api/report/%s" % payload.session_id}

@app.get("/api/report/{session_id}")
def report(session_id: str):
    path = os.path.join(REPORTS_DIR, "itap_%s.pdf" % session_id)
    if not os.path.exists(path):
        with db() as c:
            row = c.execute("SELECT email,tier,respuestas,datos,pareja_de FROM sesiones WHERE id=?", (session_id,)).fetchone()
        if not row or row["respuestas"] in (None, "{}"):
            raise HTTPException(404, "Informe no encontrado")
        try:
            if row["pareja_de"]:
                with db() as c:
                    arow = c.execute("SELECT email,respuestas,datos FROM sesiones WHERE id=?", (row["pareja_de"],)).fetchone()
                generar_couple(path, arow, row)
            else:
                generar_pdf(session_id, row["email"], json.loads(row["respuestas"]), json.loads(row["datos"]), row["tier"])
        except Exception as e:
            raise HTTPException(500, "Error regenerando informe: %s" % e)
    return FileResponse(path, media_type="application/pdf", filename="Tu_Libro_Financiero_ITAP.pdf")
