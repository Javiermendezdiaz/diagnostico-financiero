"""ITAP — Backend de produccion. Instrumento + motor + Libros. Profundidad por tier. RGPD. Nombre del cliente."""
import os, uuid, json, datetime, tempfile, sqlite3, base64, urllib.request, urllib.error
from fastapi import FastAPI, HTTPException, Request
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
PRIVACIDAD_VERSION = "1.0"
BAREMO_MIN = int(os.environ.get("BAREMO_MIN", "30"))  # muestra minima para afirmar percentil
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "ITAP <itap@adaptafamilyoffice.com>")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "javier@mendezconsultoria.com")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sesiones(
            id TEXT PRIMARY KEY, email TEXT, nombre TEXT, tier INTEGER, respuestas TEXT, datos TEXT,
            creado TEXT, pareja_de TEXT, consentimiento INTEGER, consent_fecha TEXT, consent_version TEXT)""")
        cols = [r["name"] for r in c.execute("PRAGMA table_info(sesiones)")]
        for col, ddl in [("nombre","TEXT"),("pareja_de","TEXT"),("consentimiento","INTEGER"),
                         ("consent_fecha","TEXT"),("consent_version","TEXT"),("notificado","INTEGER"),
                         ("salud","REAL"),("sexo","TEXT"),("pagado","INTEGER"),
                         ("abiertas","TEXT"),("sintesis","TEXT")]:
            if col not in cols:
                c.execute("ALTER TABLE sesiones ADD COLUMN %s %s" % (col, ddl))
init_db()

class StartPayload(BaseModel):
    email: str
    tier: int
    nombre: Optional[str] = None
    sexo: Optional[str] = None
    consentimiento: bool = False

class CompletePayload(BaseModel):
    session_id: str
    email: Optional[str] = None
    respuestas: Dict[str, int] = {}
    datos: Optional[Dict[str, float]] = None
    pareja_de: Optional[str] = None
    abiertas: Optional[Dict[str, str]] = {}

class BorrarPayload(BaseModel):
    email: str

class NotifyPayload(BaseModel):
    session_id: str

def adaptar_item(it):
    base = {"id": it["id"], "pregunta": it["texto"], "bloque": it.get("faceta", "")}
    if it["tipo"] == "escala":
        base["tipo"] = "opcion_multiple"; base["opciones"] = [o["texto"] for o in it["opciones"]]
    else:
        base["tipo"] = "numerica"; base["unidad"] = it.get("unidad", "")
    if "depende_de" in it:
        base["depende_de"] = it["depende_de"]
    return base

def adaptar_seed(it):
    return {"id": it["id"], "pregunta": it["texto"], "bloque": "Antes de empezar",
            "tipo": "opcion_multiple", "opciones": [o["texto"] for o in it["opciones"]], "seed": True}

def adaptar_arq(it):
    return {"id": it["id"], "pregunta": it["texto"], "bloque": "Tu arquetipo del dinero",
            "tipo": "opcion_multiple", "opciones": [o["texto"] for o in it["opciones"]]}

def items_para_tier(tier):
    capa_items = [it for capa in rb.INST["capas"] for it in capa["items"]]
    if tier == 1:
        sel = [it for it in capa_items if it.get("tier1") or it["tipo"] == "numerica"]
    else:
        sel = capa_items
    out = [adaptar_item(it) for it in sel]
    seeds = [adaptar_seed(it) for it in rb.INST.get("seeds", [])]
    arq = [adaptar_arq(it) for it in rb.INST.get("arquetipo", [])] if tier in (2, 3) else []
    return seeds + out + arq

def _banco_abiertas():
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banco_abiertas.json")
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {"config_tier": {}, "abiertas": []}

def abiertas_para_tier(tier):
    b = _banco_abiertas()
    n = int(b.get("config_tier", {}).get(str(tier), 0))
    out = [a for a in b.get("abiertas", []) if a.get("tier_min", 1) <= tier]
    return out[:n] if n else []

def _retrato_individual(session_id, respuestas, abiertas, sexo=None, email=None, nombre=None):
    """Calcula el retrato narrativo con IA. Devuelve str o None. Nunca lanza excepcion."""
    try:
        if not abiertas or not any(str(v).strip() for v in abiertas.values()):
            return None
        import ai_sintesis
        qmap = {a["id"]: a["texto"] for a in _banco_abiertas().get("abiertas", [])}
        ab = {qmap.get(k, k): v for k, v in abiertas.items() if str(v).strip()}
        p, tr, salud = rb.perfil(respuestas)
        focos = [rb.CAPAS[c]["nombre"] for c in sorted(rb.CAPAS, key=lambda c: p[c]["score"], reverse=True)[:3]]
        arq = rb.arquetipo(respuestas)[0]
        arqn = rb.ARQ_META[arq]["nombre"] if arq and arq in rb.ARQ_META else None
        ctx = {"salud": round(salud), "focos": focos, "arquetipo": arqn}
        s = ai_sintesis.sintetizar_individual(ab, ctx)
        return s.get("retrato") if s else None
    except Exception:
        return None

def _friccion_pareja(id_a, id_b):
    """Sintesis IA del cruce de las abiertas de ambos miembros. str o None. Nunca lanza."""
    try:
        with db() as c:
            ra = c.execute("SELECT nombre,abiertas FROM sesiones WHERE id=?", (id_a,)).fetchone()
            rbb = c.execute("SELECT nombre,abiertas FROM sesiones WHERE id=?", (id_b,)).fetchone()
        if not ra or not rbb:
            return None
        qmap = {a["id"]: a["texto"] for a in _banco_abiertas().get("abiertas", [])}
        def _ab(row):
            try:
                d = json.loads(row["abiertas"] or "{}")
            except Exception:
                d = {}
            return {qmap.get(k, k): v for k, v in d.items() if str(v).strip()}
        aa, ab = _ab(ra), _ab(rbb)
        if not aa and not ab:
            return None
        import ai_sintesis
        s = ai_sintesis.sintetizar_pareja(aa, ab, nombres={"a": ra["nombre"], "b": rbb["nombre"]})
        return s.get("friccion") if s else None
    except Exception:
        return None

def datos_completos(d):
    d = dict(d or {})
    d.setdefault("gasto_mensual", 2000); d.setdefault("ingreso_mensual", 3000)
    d.setdefault("ahorro_mensual", 300); d.setdefault("patrimonio", 30000); d.setdefault("edad", 40)
    return d

def baremo(salud_score):
    """Percentil empirico real: % de la muestra menos sana que tu. None si la muestra aun es pequena."""
    try:
        with db() as c:
            scores = [r["salud"] for r in c.execute("SELECT salud FROM sesiones WHERE salud IS NOT NULL").fetchall()]
    except Exception:
        scores = []
    N = len(scores)
    if N < BAREMO_MIN or salud_score is None:
        return {"pct": None, "n": N}
    above = sum(1 for x in scores if x > salud_score)   # mas disfuncion = menos sano que tu
    eq = sum(1 for x in scores if x == salud_score)
    pct = (above + 0.5 * eq) / N * 100.0
    return {"pct": round(pct), "n": N}

def _guardar_salud(session_id, respuestas):
    try:
        _, _, salud = rb.perfil(respuestas)
        with db() as c:
            c.execute("UPDATE sesiones SET salud=? WHERE id=?", (float(salud), session_id))
        return salud
    except Exception:
        return None

def _cli(email, nombre=None, sexo=None):
    nom = (nombre or "").strip() or (email or "cliente").split("@")[0].replace("."," ").title()
    return {"nombre": nom, "email": email or "", "sexo": sexo or "",
            "fecha": datetime.datetime.now().strftime("%d/%m/%Y")}

def generar_pdf(sid, email, nombre, respuestas, datos, tier, bar=None, sexo=None, sintesis=None):
    if sintesis is None:
        try:
            with db() as c:
                r = c.execute("SELECT sintesis FROM sesiones WHERE id=?", (sid,)).fetchone()
            if r and r["sintesis"]:
                sintesis = r["sintesis"]
        except Exception:
            pass
    out = os.path.join(REPORTS_DIR, "itap_%s.pdf" % sid)
    rb.build_book(respuestas, datos_completos(datos), _cli(email, nombre, sexo), out,
                  depth=TIER_DEPTH.get(tier, "completo"), baremo=bar, sintesis=sintesis)
    return out

def generar_couple(out, arow, brow, sintesis=None):
    if sintesis is None:
        try:
            if "sintesis" in brow.keys() and brow["sintesis"]:
                sintesis = brow["sintesis"]
        except Exception:
            pass
    rc.build_couple(json.loads(arow["respuestas"]), datos_completos(json.loads(arow["datos"])), _cli(arow["email"], arow["nombre"]),
                    json.loads(brow["respuestas"]), datos_completos(json.loads(brow["datos"])), _cli(brow["email"], brow["nombre"]), out, sintesis=sintesis)

@app.get("/")
def health():
    return {"status": "healthy", "service": "ITAP", "capas": len(rb.INST["capas"]),
            "version": rb.INST["meta"]["version"], "persistencia": "sqlite", "pareja": True, "rgpd": True, "nombre": True, "arquetipo": True, "email": bool(RESEND_API_KEY)}

@app.get("/api/questions/{tier}")
def questions(tier: int):
    items = items_para_tier(tier)
    return {"questions": items, "total_preguntas": len(items), "abiertas": abiertas_para_tier(tier)}

@app.post("/api/start")
def start(payload: StartPayload):
    if not payload.consentimiento:
        raise HTTPException(400, "Debes aceptar la politica de privacidad para continuar.")
    sid = str(uuid.uuid4())
    with db() as c:
        c.execute("""INSERT INTO sesiones(id,email,nombre,sexo,tier,respuestas,datos,creado,pareja_de,
                     consentimiento,consent_fecha,consent_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (sid, payload.email, (payload.nombre or "").strip() or None, (payload.sexo or "").strip() or None,
                   payload.tier, "{}", "{}",
                   datetime.datetime.utcnow().isoformat(), None, 1,
                   datetime.datetime.utcnow().isoformat(), PRIVACIDAD_VERSION))
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
        row = c.execute("SELECT email,nombre,tier,sexo FROM sesiones WHERE id=?", (payload.session_id,)).fetchone()
    if not row:
        raise HTTPException(400, "Sesion no valida. Inicia el cuestionario aceptando la politica de privacidad.")
    email = payload.email or row["email"]
    nombre = row["nombre"]
    tier = row["tier"]
    datos = datos_completos(payload.datos)
    with db() as c:
        c.execute("UPDATE sesiones SET respuestas=?, datos=?, email=?, pareja_de=?, abiertas=? WHERE id=?",
                  (json.dumps(payload.respuestas), json.dumps(datos), email, payload.pareja_de,
                   json.dumps(payload.abiertas or {}), payload.session_id))
    if tier == 3:
        if not payload.pareja_de:
            return {"ok": True, "needs_partner": True, "codigo": payload.session_id}
        with db() as c:
            arow = c.execute("SELECT email,nombre,respuestas,datos FROM sesiones WHERE id=?", (payload.pareja_de,)).fetchone()
            brow = c.execute("SELECT email,nombre,respuestas,datos FROM sesiones WHERE id=?", (payload.session_id,)).fetchone()
        if not arow or arow["respuestas"] in (None, "{}"):
            raise HTTPException(409, "Tu pareja todavia no ha terminado su cuestionario.")
        fric = _friccion_pareja(payload.pareja_de, payload.session_id)
        if fric:
            try:
                with db() as c:
                    c.execute("UPDATE sesiones SET sintesis=? WHERE id=?", (fric, payload.session_id))
            except Exception:
                pass
        out = os.path.join(REPORTS_DIR, "itap_%s.pdf" % payload.session_id)
        try:
            generar_couple(out, arow, brow, sintesis=fric)
        except Exception as e:
            raise HTTPException(500, "Error generando informe de pareja: %s" % e)
        return {"ok": True, "es_pareja": True, "report_url": "/api/report/%s" % payload.session_id}
    salud = _guardar_salud(payload.session_id, payload.respuestas)
    bar = baremo(salud)
    retrato = _retrato_individual(payload.session_id, payload.respuestas, payload.abiertas, row["sexo"], email, nombre)
    if retrato:
        try:
            with db() as c:
                c.execute("UPDATE sesiones SET sintesis=? WHERE id=?", (retrato, payload.session_id))
        except Exception:
            pass
    try:
        generar_pdf(payload.session_id, email, nombre, payload.respuestas, datos, tier, bar, row["sexo"], sintesis=retrato)
    except Exception as e:
        raise HTTPException(500, "Error generando informe: %s" % e)
    return {"ok": True, "report_url": "/api/report/%s" % payload.session_id}

@app.get("/api/estado/{session_id}")
def estado(session_id: str):
    with db() as c:
        row = c.execute("SELECT pagado FROM sesiones WHERE id=?", (session_id,)).fetchone()
    return {"pagado": bool(row and row["pagado"]), "gated": bool(STRIPE_WEBHOOK_SECRET)}

@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        return {"ok": False, "reason": "webhook_no_configurado"}
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        import stripe
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Firma de webhook invalida")
    if event.get("type") == "checkout.session.completed":
        ref = (event.get("data", {}).get("object", {}) or {}).get("client_reference_id")
        if ref:
            with db() as c:
                c.execute("UPDATE sesiones SET pagado=1 WHERE id=?", (ref,))
    return {"ok": True}

@app.get("/api/report/{session_id}")
def report(session_id: str):
    if STRIPE_WEBHOOK_SECRET:
        with db() as c:
            prow = c.execute("SELECT pagado FROM sesiones WHERE id=?", (session_id,)).fetchone()
        if not prow or not prow["pagado"]:
            raise HTTPException(402, "Pago requerido para acceder al informe.")
    path = os.path.join(REPORTS_DIR, "itap_%s.pdf" % session_id)
    if not os.path.exists(path):
        with db() as c:
            row = c.execute("SELECT email,nombre,tier,respuestas,datos,pareja_de,sexo,sintesis FROM sesiones WHERE id=?", (session_id,)).fetchone()
        if not row or row["respuestas"] in (None, "{}"):
            raise HTTPException(404, "Informe no encontrado")
        try:
            if row["pareja_de"]:
                with db() as c:
                    arow = c.execute("SELECT email,nombre,respuestas,datos FROM sesiones WHERE id=?", (row["pareja_de"],)).fetchone()
                generar_couple(path, arow, row)
            else:
                _resp = json.loads(row["respuestas"])
                _salud = _guardar_salud(session_id, _resp)
                generar_pdf(session_id, row["email"], row["nombre"], _resp, json.loads(row["datos"]), row["tier"], baremo(_salud), row["sexo"])
        except Exception as e:
            raise HTTPException(500, "Error regenerando informe: %s" % e)
    return FileResponse(path, media_type="application/pdf", filename="Tu_Libro_Financiero_ITAP.pdf")

def _asegurar_pdf(session_id):
    path = os.path.join(REPORTS_DIR, "itap_%s.pdf" % session_id)
    if os.path.exists(path):
        return path
    with db() as c:
        row = c.execute("SELECT email,nombre,tier,respuestas,datos,pareja_de,sexo,sintesis FROM sesiones WHERE id=?", (session_id,)).fetchone()
    if not row or row["respuestas"] in (None, "{}"):
        return None
    try:
        if row["pareja_de"]:
            with db() as c:
                arow = c.execute("SELECT email,nombre,respuestas,datos FROM sesiones WHERE id=?", (row["pareja_de"],)).fetchone()
            generar_couple(path, arow, row)
        else:
            generar_pdf(session_id, row["email"], row["nombre"], json.loads(row["respuestas"]), json.loads(row["datos"]), row["tier"])
        return path if os.path.exists(path) else None
    except Exception:
        return None

def _resend_email(asunto, html, pdf_bytes, filename):
    payload = {
        "from": RESEND_FROM,
        "to": [NOTIFY_EMAIL],
        "subject": asunto,
        "html": html,
        "attachments": [{"filename": filename, "content": base64.b64encode(pdf_bytes).decode("ascii")}],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://api.resend.com/emails", data=data, method="POST",
        headers={"Authorization": "Bearer %s" % RESEND_API_KEY, "Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "ignore")

def enviar_copia(session_id):
    if not RESEND_API_KEY:
        return {"ok": False, "reason": "resend_no_configurado"}
    with db() as c:
        row = c.execute("SELECT email,nombre,tier,respuestas,notificado FROM sesiones WHERE id=?", (session_id,)).fetchone()
    if not row or row["respuestas"] in (None, "{}"):
        return {"ok": False, "reason": "sesion_sin_respuestas"}
    if row["notificado"]:
        return {"ok": True, "ya_enviado": True}
    path = _asegurar_pdf(session_id)
    if not path:
        return {"ok": False, "reason": "pdf_no_disponible"}
    tier_nombre = {1: "Diagnostico Rapido (19 EUR)", 2: "Informe Avanzado (39 EUR)", 3: "Analisis de Pareja (54 EUR)"}.get(row["tier"], "Tier %s" % row["tier"])
    cliente = (row["nombre"] or "").strip() or "(sin nombre)"
    email_cli = row["email"] or "(sin email)"
    asunto = "Nueva compra ITAP - %s - %s" % (cliente, tier_nombre)
    html = ("<h2>Nueva compra ITAP</h2>"
            "<p><b>Cliente:</b> %s<br><b>Email:</b> %s<br><b>Producto:</b> %s</p>"
            "<p>Adjunto va una copia del libro financiero generado.</p>"
            "<p style='color:#888;font-size:12px'>Notificacion automatica - Adapta Family Office</p>") % (cliente, email_cli, tier_nombre)
    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()
        status, _ = _resend_email(asunto, html, pdf_bytes, "ITAP_%s.pdf" % cliente.replace(" ", "_"))
    except urllib.error.HTTPError as e:
        try: detalle = e.read().decode("utf-8","ignore")[:400]
        except Exception: detalle = ""
        return {"ok": False, "reason": "resend_error_%s" % e.code, "detalle": detalle}
    except Exception as e:
        return {"ok": False, "reason": "error_%s" % type(e).__name__}
    if 200 <= status < 300:
        with db() as c:
            c.execute("UPDATE sesiones SET notificado=1 WHERE id=?", (session_id,))
        return {"ok": True}
    return {"ok": False, "reason": "resend_status_%s" % status}

@app.post("/api/notify-purchase")
def notify_purchase(payload: NotifyPayload):
    try:
        return enviar_copia(payload.session_id)
    except Exception as e:
        return {"ok": False, "reason": "error_%s" % type(e).__name__}

@app.post("/api/borrar-datos")
def borrar_datos(payload: BorrarPayload):
    email = (payload.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Indica un correo valido.")
    with db() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM sesiones WHERE lower(email)=?", (email,)).fetchall()]
        c.execute("DELETE FROM sesiones WHERE lower(email)=?", (email,))
    for sid in ids:
        p = os.path.join(REPORTS_DIR, "itap_%s.pdf" % sid)
        if os.path.exists(p):
            try: os.remove(p)
            except OSError: pass
    return {"ok": True, "borrados": len(ids), "mensaje": "Hemos eliminado todos los datos asociados a ese correo."}
