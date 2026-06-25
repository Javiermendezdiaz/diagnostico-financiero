"""ITAP — Backend de produccion. Instrumento + motor + Libros. Profundidad por tier. RGPD. Nombre del cliente."""
import os, uuid, json, datetime, tempfile, sqlite3, base64, urllib.request, urllib.error
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import report_book as rb
import report_couple as rc

app = FastAPI(title="ITAP")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
# Persistencia: si ITAP_DATA_DIR apunta a un disco persistente (Render disk), la base de datos
# y los PDF sobreviven a redespliegues y reinicios. Sin esa variable, cae al comportamiento previo
# (efimero), de modo que el cambio es 100% retrocompatible.
_DATA_DIR = (os.environ.get("ITAP_DATA_DIR") or "").strip()
if _DATA_DIR:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
    except Exception:
        _DATA_DIR = ""
REPORTS_DIR = _DATA_DIR or tempfile.gettempdir()
DB = os.path.join(_DATA_DIR, "itap_sessions.db") if _DATA_DIR \
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "itap_sessions.db")
TIER_LIMIT = {1: 60, 2: 1000, 3: 1000}
TIER_DEPTH = {1: "esencial", 2: "completo", 3: "completo"}
PRIVACIDAD_VERSION = "1.0"
BAREMO_MIN = int(os.environ.get("BAREMO_MIN", "30"))  # muestra minima para afirmar percentil
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "ITAP <itap@adaptafamilyoffice.com>")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "javier@mendezconsultoria.com")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_SECRET_KEY = (os.environ.get("STRIPE_SECRET_KEY", "")
                     or os.environ.get("STRIPE_API_KEY", "")
                     or os.environ.get("STRIPE_API_KEY_PROD", "")).strip()
# URL publica de la web (para volver tras el checkout). Por defecto, GitHub Pages.
PUBLIC_BASE_URL = (os.environ.get("PUBLIC_BASE_URL", "").strip()
                   or "https://javiermendezdiaz.github.io/diagnostico-financiero/empezar2.html")
# Precio por tier en centimos de euro.
PRECIOS = {1: 1900, 2: 3900, 3: 5400}
TIER_NOMBRE = {1: "Diagnostico Rapido", 2: "Libro Financiero (Avanzado)", 3: "Libro de la Pareja"}

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
                         ("abiertas","TEXT"),("sintesis","TEXT"),("perfil","TEXT"),("es_v2","INTEGER"),
                         ("progreso_idx","INTEGER"),("progreso_total","INTEGER"),("last_qid","TEXT"),("progreso_fecha","TEXT"),
                         ("es_inic","INTEGER"),("consent_pago_fecha","TEXT")]:
            if col not in cols:
                c.execute("ALTER TABLE sesiones ADD COLUMN %s %s" % (col, ddl))
init_db()

import threading, gc
_GEN_LOCK = threading.Lock()   # una sola generacion de PDF a la vez (la de pareja es pesada en RAM)
def _liberar_memoria():
    try:
        import matplotlib.pyplot as _plt; _plt.close("all")
    except Exception:
        pass
    try:
        gc.collect()
    except Exception:
        pass

def _build_isolated(fn, *a, **k):
    """Genera el PDF en un proceso HIJO que muere al terminar -> devuelve TODA la RAM al sistema (anti-OOM Render).
    El worker de uvicorn (padre) nunca acumula el pico. Si fork no esta disponible (Windows) o el hijo falla,
    cae a generacion en proceso: mismo comportamiento de siempre, cero riesgo."""
    try:
        pid = os.fork()
    except Exception:
        pid = -1
    if pid == 0:                       # --- proceso hijo: genera y muere ---
        try:
            fn(*a, **k); os._exit(0)
        except BaseException:
            os._exit(1)
    elif pid > 0:                      # --- padre: espera al hijo ---
        try:
            _, status = os.waitpid(pid, 0)
        except Exception:
            status = None
        if status is not None and os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0:
            return                     # OK: el hijo generó el PDF y liberó la RAM al morir
        if status is not None and os.WIFSIGNALED(status):
            # Muerte por señal (SIGKILL=9 en Render = casi seguro OOM). NO reintentamos en proceso:
            # eso cargaría el pico en el padre y tumbaría el servicio. Registramos alto y avisamos.
            _sig = os.WTERMSIG(status)
            print("!!! PDF_OOM_KILL · generación abortada por señal %d (probable falta de memoria en Render). "
                  "El servicio sigue vivo; reintentar. Si se repite, subir el plan de Render." % _sig, flush=True)
            raise MemoryError("Generación de PDF interrumpida por falta de memoria (señal %d). Reinténtalo en unos segundos." % _sig)
        # salida != 0 sin señal = error de código del hijo -> reintenta en proceso para propagar el traceback real
    fn(*a, **k)                        # fallback en proceso (fork no disponible, o error de código no-OOM)

class StartPayload(BaseModel):
    email: str
    tier: int
    nombre: Optional[str] = None
    sexo: Optional[str] = None
    consentimiento: bool = False

class CompletePayload(BaseModel):
    session_id: str
    email: Optional[str] = None
    respuestas: Dict[str, Any] = {}
    datos: Optional[Dict[str, Any]] = None
    pareja_de: Optional[str] = None
    abiertas: Optional[Dict[str, str]] = {}
    perfil: Optional[Dict[str, object]] = {}
    v2: Optional[bool] = False

class BorrarPayload(BaseModel):
    email: str

class NotifyPayload(BaseModel):
    session_id: str

class ProgressPayload(BaseModel):
    session_id: str
    idx: Optional[int] = 0
    total: Optional[int] = 0
    last_qid: Optional[str] = None

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
    # Saneamiento anti-GIGO: una cifra disparatada del cliente no debe romper el informe.
    for _k in ("pct_gasto_fijo", "pct_vivienda", "rentabilidad_actual"):
        if d.get(_k) is not None:
            try: d[_k] = max(0.0, min(100.0, float(d[_k])))
            except Exception: d[_k] = None
    for _k in ("gasto_mensual", "ingreso_mensual", "ahorro_mensual", "patrimonio", "coste_vivienda",
               "cuota_deuda", "deuda_total", "pension_estimada", "gasto_estatus", "renta_pasiva",
               "inversiones_liquidas", "gastos_comunes", "gastos_anuales"):
        if d.get(_k) is not None:
            try: d[_k] = max(0.0, float(d[_k]))
            except Exception: pass
    # Coste de vida REAL: prorratea los gastos anuales no mensuales (seguros, IBI, vacaciones...)
    # y sumalos al gasto mensual. Aqui es donde la gente mas subestima su gasto.
    try:
        _ga = float(d.get("gastos_anuales") or 0)
        if _ga > 0:
            d["gasto_mensual"] = float(d.get("gasto_mensual") or 0) + _ga / 12.0
    except Exception:
        pass
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

def _guardar_salud_v2(session_id, respuestas):
    try:
        import score_v2, statistics
        p = score_v2.perfil_scores(respuestas, rb._cargar_v2()["capas"])
        salud = round(statistics.mean([v["score"] for v in p.values()]), 1) if p else None
        if salud is not None:
            with db() as c:
                c.execute("UPDATE sesiones SET salud=? WHERE id=?", (float(salud), session_id))
        return salud
    except Exception:
        return None

def _retrato_individual_v2(session_id, respuestas, abiertas, perfil, email=None, nombre=None):
    """Retrato narrativo IA para v2: contexto (salud, focos, arquetipo) desde el motor v2."""
    try:
        if not abiertas or not any(str(v).strip() for v in abiertas.values()):
            return None
        import ai_sintesis, score_v2, statistics
        qmap = {a["id"]: a["texto"] for a in _banco_abiertas().get("abiertas", [])}
        ab = {qmap.get(k, k): v for k, v in abiertas.items() if str(v).strip()}
        p = score_v2.perfil_scores(respuestas, rb._cargar_v2()["capas"])
        salud = round(statistics.mean([v["score"] for v in p.values()])) if p else None
        focos = [p[c]["nombre"] for c in sorted(p, key=lambda c: p[c]["score"], reverse=True)[:3]]
        arq = score_v2.arq_desde_perfil(perfil or {})
        arqn = rb.ARQ_META[arq]["nombre"] if arq and arq in rb.ARQ_META else None
        ctx = {"salud": salud, "focos": focos, "arquetipo": arqn}
        s = ai_sintesis.sintetizar_individual(ab, ctx)
        return s.get("retrato") if s else None
    except Exception:
        return None

def _cli(email, nombre=None, sexo=None):
    nom = (nombre or "").strip() or (email or "cliente").split("@")[0].replace("."," ").title()
    return {"nombre": nom, "email": email or "", "sexo": sexo or "",
            "fecha": datetime.datetime.now().strftime("%d/%m/%Y")}

def generar_pdf(sid, email, nombre, respuestas, datos, tier, bar=None, sexo=None, sintesis=None):
    es_v2 = False; perfil = {}
    try:
        with db() as c:
            r = c.execute("SELECT sintesis, perfil, es_v2 FROM sesiones WHERE id=?", (sid,)).fetchone()
        if r:
            if sintesis is None and r["sintesis"]:
                sintesis = r["sintesis"]
            es_v2 = bool(r["es_v2"])
            try: perfil = json.loads(r["perfil"] or "{}")
            except Exception: perfil = {}
    except Exception:
        pass
    out = os.path.join(REPORTS_DIR, "itap_%s.pdf" % sid)
    d = datos_completos(datos)
    if es_v2:
        extras = None
        try:
            import score_v2
            extras = score_v2.computar_extras(respuestas, d, perfil, rb._cargar_v2())
        except Exception:
            extras = None
        rb.build_book_v2(respuestas, d, _cli(email, nombre, sexo), out, perfil_in=perfil,
                        depth=TIER_DEPTH.get(tier, "completo"), baremo=bar, sintesis=sintesis, extras=extras)
    else:
        rb.build_book(respuestas, d, _cli(email, nombre, sexo), out,
                        depth=TIER_DEPTH.get(tier, "completo"), baremo=bar, sintesis=sintesis)
    return out

def generar_couple(out, arow, brow, sintesis=None):
    if sintesis is None:
        try:
            if "sintesis" in brow.keys() and brow["sintesis"]:
                sintesis = brow["sintesis"]
        except Exception:
            pass
    def _pf(row):
        try:
            return json.loads(row["perfil"] or "{}") if ("perfil" in row.keys() and row["perfil"]) else {}
        except Exception:
            return {}
    rc.build_couple(json.loads(arow["respuestas"]), datos_completos(json.loads(arow["datos"])), _cli(arow["email"], arow["nombre"]),
                    json.loads(brow["respuestas"]), datos_completos(json.loads(brow["datos"])), _cli(brow["email"], brow["nombre"]), out, sintesis=sintesis,
                    perfilA=_pf(arow), perfilB=_pf(brow))

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

@app.post("/api/progress")
def progress(payload: ProgressPayload):
    """Marca hasta donde ha llegado el usuario, para ver donde se cae quien no termina."""
    try:
        with db() as c:
            c.execute("""UPDATE sesiones SET progreso_idx=MAX(COALESCE(progreso_idx,0),?),
                         progreso_total=?, last_qid=?, progreso_fecha=? WHERE id=?""",
                      (int(payload.idx or 0), int(payload.total or 0), payload.last_qid,
                       datetime.datetime.utcnow().isoformat(), payload.session_id))
        return {"ok": True}
    except Exception:
        return {"ok": False}

@app.get("/api/funnel")
def funnel():
    """Embudo agregado (sin datos personales): inicio -> progreso -> finalizacion -> pago + abandono por pregunta."""
    if os.environ.get("FUNNEL_KEY"):
        return {"error": "protegido"}  # placeholder; si se define clave, usar /api/funnel?key=
    try:
        with db() as c:
            rows = c.execute("SELECT tier,respuestas,pagado,progreso_idx,progreso_total,last_qid,creado FROM sesiones").fetchall()
    except Exception as e:
        raise HTTPException(500, "Error leyendo funnel: %s" % e)
    from collections import Counter
    total = len(rows)
    def _comp(r): return r["respuestas"] not in (None, "{}", "")
    completados = sum(1 for r in rows if _comp(r))
    pagados = sum(1 for r in rows if r["pagado"])
    aband = [r for r in rows if not _comp(r)]
    drop = Counter((r["last_qid"] or "(no empezo el test)") for r in aband)
    bytier = {}
    for t in (1, 2, 3):
        tr = [r for r in rows if r["tier"] == t]
        ct = sum(1 for r in tr if _comp(r))
        bytier[str(t)] = {"iniciados": len(tr), "completados": ct, "pagados": sum(1 for r in tr if r["pagado"])}
    return {
        "iniciados": total, "completados": completados, "pagados": pagados,
        "abandonos": total - completados,
        "tasa_finalizacion_pct": round(100.0 * completados / total, 1) if total else 0,
        "tasa_pago_sobre_completados_pct": round(100.0 * pagados / completados, 1) if completados else 0,
        "abandono_por_pregunta": dict(drop.most_common(20)),
        "por_tier": bytier,
    }

@app.post("/api/complete")
def complete(payload: CompletePayload, background_tasks: BackgroundTasks):
    with db() as c:
        row = c.execute("SELECT email,nombre,tier,sexo FROM sesiones WHERE id=?", (payload.session_id,)).fetchone()
    if not row:
        raise HTTPException(400, "Sesion no valida. Inicia el cuestionario aceptando la politica de privacidad.")
    email = payload.email or row["email"]
    nombre = row["nombre"]
    tier = row["tier"]
    datos = datos_completos(payload.datos)
    with db() as c:
        c.execute("UPDATE sesiones SET respuestas=?, datos=?, email=?, pareja_de=?, abiertas=?, perfil=?, es_v2=? WHERE id=?",
                  (json.dumps(payload.respuestas), json.dumps(datos), email, payload.pareja_de,
                   json.dumps(payload.abiertas or {}), json.dumps(payload.perfil or {}),
                   1 if payload.v2 else 0, payload.session_id))
    if tier == 3:
        if not payload.pareja_de:
            # INICIADOR: marca su rol, calcula su adelanto individual y pasa al pago YA.
            # El libro de pareja se generara bajo SU sesion (es el comprador y quien descarga).
            _sal = _guardar_salud_v2(payload.session_id, payload.respuestas) if payload.v2 else _guardar_salud(payload.session_id, payload.respuestas)
            with db() as c:
                c.execute("UPDATE sesiones SET es_inic=1 WHERE id=?", (payload.session_id,))
            return {"ok": True, "needs_partner": True, "codigo": payload.session_id,
                    "teaser": _teaser(datos, _sal, payload.perfil, payload.datos)}
        # PAREJA (segundo miembro): enlaza de vuelta al iniciador para que pueda generar/descargar.
        with db() as c:
            arow = c.execute("SELECT email,nombre,respuestas,datos,perfil,pagado FROM sesiones WHERE id=?", (payload.pareja_de,)).fetchone()
        if not arow or arow["respuestas"] in (None, "{}"):
            raise HTTPException(409, "Tu pareja todavia no ha empezado: pidele que inicie su parte primero.")
        with db() as c:
            c.execute("UPDATE sesiones SET pareja_de=? WHERE id=? AND (pareja_de IS NULL OR pareja_de='')",
                      (payload.session_id, payload.pareja_de))
        fric = _friccion_pareja(payload.pareja_de, payload.session_id)
        if fric:
            try:
                with db() as c:
                    c.execute("UPDATE sesiones SET sintesis=? WHERE id=?", (fric, payload.session_id))
            except Exception:
                pass
        # Si el iniciador YA pago, genera y envia el libro de pareja en segundo plano
        # (aunque haya cerrado la pestana): le llegara por email automaticamente.
        if arow["pagado"]:
            try:
                background_tasks.add_task(enviar_copia, payload.pareja_de)
            except Exception:
                pass
        # El segundo miembro NO paga (el iniciador es el comprador). Devuelve rol partner.
        return {"ok": True, "es_pareja": True, "rol": "partner", "inic_pagado": bool(arow["pagado"])}
    if payload.v2:
        salud = _guardar_salud_v2(payload.session_id, payload.respuestas)
        retrato = _retrato_individual_v2(payload.session_id, payload.respuestas, payload.abiertas, payload.perfil, email, nombre)
    else:
        salud = _guardar_salud(payload.session_id, payload.respuestas)
        retrato = _retrato_individual(payload.session_id, payload.respuestas, payload.abiertas, row["sexo"], email, nombre)
    bar = baremo(salud)
    if retrato:
        try:
            with db() as c:
                c.execute("UPDATE sesiones SET sintesis=? WHERE id=?", (retrato, payload.session_id))
        except Exception:
            pass
    # El PDF NO se genera aqui: seria trabajo pesado antes del pago y bloquea el worker.
    # Se genera de forma diferida en /api/report (tras el pago). El retrato IA ya quedo guardado.
    return {"ok": True, "report_url": "/api/report/%s" % payload.session_id,
            "teaser": _teaser(datos, salud, payload.perfil, payload.datos)}

def _teaser(datos, salud=None, perfil=None, raw=None):
    """Datos reales del cliente para el adelanto gratis (prueba de valor antes del pago)."""
    try:
        rw = raw or datos
        _real_ing = float((rw or {}).get("ingreso_mensual") or 0) > 0
        _real_gas = float((rw or {}).get("gasto_mensual") or 0) > 0
        ing = float(datos.get("ingreso_mensual") or 0); gas = float(datos.get("gasto_mensual") or 0)
        margen = round((ing - gas) / ing * 100) if ing > 0 else None
        cifra = round(gas * 12 / 0.04) if gas > 0 else None  # regla del 4%
        out = {}
        # Solo mostramos cifras derivadas de ingreso/gasto si el usuario los aporto DE VERDAD
        # (evita ensenar numeros por defecto como si fueran reales).
        if margen is not None and _real_ing and _real_gas: out["margen"] = margen
        if cifra and _real_gas: out["cifra_libertad"] = cifra
        if ing > 0 and gas > 0 and _real_ing and _real_gas:
            out["esclavitud"] = round(min(100, gas / ing * 100))
        # Meses de libertad REALES: los que compra tu patrimonio, no el flujo del mes.
        # Es la cifra que de verdad mide lo libre que estas (un patrimonio alto vale
        # mas que un buen sueldo con poco respaldo).
        try:
            import score_v2
            _r = score_v2.calcular_resiliencia(datos)
        except Exception:
            _r = None
        if _r:
            out["meses_libertad"] = _r["meses_libertad"]
            out["anios_libertad"] = _r["anios_libertad"]
            out["meses_liquido"] = _r["meses_liquido"]
            out["resiliencia"] = _r["resiliencia"]
            out["fragilidad"] = _r["fragilidad"]
            out["nivel_libertad"] = _r["nivel"]
        if salud is not None:
            try: out["salud"] = round(100 - float(salud))  # 0=disfuncion -> tu relacion con el dinero
            except Exception: pass
        # Ratio de Vida (IRI) + foco principal del Nudo: el gancho personalizado antes del pago.
        if perfil:
            try:
                import score_v2 as _s2
                _rv = _s2.calcular_ratio_vida(perfil)
                if _rv:
                    out["iri"] = _rv["iri"]; out["foco"] = _rv["weakest"]
                _nd = _s2.calcular_nudo(perfil, datos)
                if _nd and _nd.get("principal"):
                    out["foco_tit"] = _nd["principal"]["tit"]
            except Exception:
                pass
        return out
    except Exception:
        return {}

@app.get("/api/estado/{session_id}")
def estado(session_id: str):
    with db() as c:
        row = c.execute("SELECT pagado FROM sesiones WHERE id=?", (session_id,)).fetchone()
    return {"pagado": bool(row and row["pagado"]), "gated": bool(STRIPE_WEBHOOK_SECRET)}

@app.get("/api/pareja-estado/{session_id}")
def pareja_estado(session_id: str):
    """Estado del flujo de pareja: dice al INICIADOR si ya puede descargar el libro conjunto."""
    with db() as c:
        row = c.execute("SELECT pareja_de,pagado,tier,es_inic FROM sesiones WHERE id=?", (session_id,)).fetchone()
    if not row:
        return {"existe": False}
    pid = row["pareja_de"]; lista = False
    if pid:
        with db() as c:
            pr = c.execute("SELECT respuestas FROM sesiones WHERE id=?", (pid,)).fetchone()
        lista = bool(pr and pr["respuestas"] not in (None, "{}", ""))
    return {"existe": True, "es_pareja": (row["tier"] == 3), "es_inic": bool(row["es_inic"]),
            "pareja_lista": lista, "pagado": bool(row["pagado"]), "gated": bool(STRIPE_WEBHOOK_SECRET)}

@app.post("/api/checkout/{session_id}")
def checkout(session_id: str, consent: int = 0):
    """Crea una sesion de Stripe Checkout para esta sesion concreta y devuelve la URL de pago.
    Inyecta client_reference_id=session_id (lo que el webhook usa para marcar pagado) y habilita
    el campo de codigo promocional (cupon ADAPTA100). Degrada con elegancia si falta la clave."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Pago no configurado: falta STRIPE_SECRET_KEY en el servidor.")
    with db() as c:
        row = c.execute("SELECT email,nombre,tier,pagado,respuestas FROM sesiones WHERE id=?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Sesion no encontrada.")
    if row["respuestas"] in (None, "{}", ""):
        raise HTTPException(409, "Completa el cuestionario antes de pagar.")
    if row["pagado"]:
        return {"url": None, "ya_pagado": True, "report_url": "/api/report/%s" % session_id}
    # Registro del consentimiento de entrega inmediata (renuncia al desistimiento), sello servidor.
    if consent:
        try:
            with db() as c:
                c.execute("UPDATE sesiones SET consent_pago_fecha=? WHERE id=?",
                          (datetime.datetime.utcnow().isoformat(), session_id))
        except Exception:
            pass
    tier = row["tier"] or 2
    precio = PRECIOS.get(tier, PRECIOS[2])
    nombre_prod = "ITAP - %s" % TIER_NOMBRE.get(tier, "Diagnostico")
    sep = "&" if ("?" in PUBLIC_BASE_URL) else "?"
    # Incluimos {CHECKOUT_SESSION_ID} (Stripe lo sustituye al volver) para poder VERIFICAR
    # el pago en el servidor sin depender del webhook.
    success_url = "%s%ssid=%s&paid=1&cs={CHECKOUT_SESSION_ID}" % (PUBLIC_BASE_URL, sep, session_id)
    cancel_url = "%s%ssid=%s&paid=0" % (PUBLIC_BASE_URL, sep, session_id)
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        # Usar el Price REAL de Stripe que coincida con el importe del tier (19/39/54 €),
        # para que el cupon QCADAPTA (restringido a esos productos) aplique. Si no hay match,
        # crea un precio al vuelo (retrocompatible).
        line_item = None
        try:
            for p in stripe.Price.list(active=True, currency="eur", limit=100, expand=["data.product"]).data:
                if int((p.unit_amount or 0)) != precio:
                    continue
                prod = p.product
                pname = (prod if isinstance(prod, str) else getattr(prod, "name", "")) or ""
                # Saltar los productos creados al vuelo por versiones anteriores (empiezan por "ITAP"),
                # para quedarnos con el producto REAL del catalogo (al que aplica el cupon).
                if pname.strip().upper().startswith("ITAP"):
                    continue
                nombre_prod = pname or nombre_prod
                line_item = {"price": p.id, "quantity": 1}
                break
        except Exception as _e:
            line_item = None
        if not line_item:
            line_item = {"price_data": {"currency": "eur", "unit_amount": precio,
                                        "product_data": {"name": nombre_prod,
                                                         "description": "Diagnostico psicofinanciero personalizado (PDF)."}},
                         "quantity": 1}
        cs = stripe.checkout.Session.create(
            mode="payment",
            line_items=[line_item],
            client_reference_id=session_id,
            customer_email=(row["email"] or None),
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"session_id": session_id, "tier": str(tier)},
        )
        return {"url": cs.url, "_prod": nombre_prod, "_li": ("price" if "price" in line_item else "inline")}
    except Exception as e:
        raise HTTPException(502, "No se pudo crear el pago: %s" % e)

@app.post("/api/verify/{session_id}")
def verify_payment(session_id: str, background_tasks: BackgroundTasks, cs: str = ""):
    """Verifica el pago directamente con Stripe (sin depender del webhook). Marca pagado si la
    sesion de checkout esta completada o pagada (incluye 0 EUR con cupon: 'no_payment_required').
    Al confirmar el pago, envia el libro por email en segundo plano (comprador + aviso a Adapta)."""
    if not STRIPE_SECRET_KEY or not cs:
        return {"pagado": False, "reason": "sin_datos"}
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        s = stripe.checkout.Session.retrieve(cs)
        ok = (getattr(s, "status", "") == "complete") or (getattr(s, "payment_status", "") in ("paid", "no_payment_required"))
        ref = getattr(s, "client_reference_id", None)
        if ok and ref == session_id:
            with db() as c:
                c.execute("UPDATE sesiones SET pagado=1 WHERE id=?", (session_id,))
            try: background_tasks.add_task(enviar_copia, session_id)   # entrega aunque cierre la pestana
            except Exception: pass
            return {"pagado": True}
        return {"pagado": False, "reason": "no_completado"}
    except Exception as e:
        return {"pagado": False, "reason": "error_%s" % type(e).__name__}

@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
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
            try: background_tasks.add_task(enviar_copia, ref)   # entrega garantizada via webhook
            except Exception: pass
    return {"ok": True}

@app.get("/api/report/{session_id}")
def report(session_id: str, background_tasks: BackgroundTasks):
    if STRIPE_WEBHOOK_SECRET:
        with db() as c:
            prow = c.execute("SELECT pagado FROM sesiones WHERE id=?", (session_id,)).fetchone()
        if not prow or not prow["pagado"]:
            raise HTTPException(402, "Pago requerido para acceder al informe.")
    path = os.path.join(REPORTS_DIR, "itap_%s.pdf" % session_id)
    if not os.path.exists(path):
      # Candado global: solo UNA generacion a la vez (evita pico de RAM por builds concurrentes).
      with _GEN_LOCK:
        if not os.path.exists(path):
          try:
            with db() as c:
                row = c.execute("SELECT email,nombre,tier,respuestas,datos,pareja_de,sexo,sintesis,perfil,es_inic FROM sesiones WHERE id=?", (session_id,)).fetchone()
            if not row or row["respuestas"] in (None, "{}"):
                raise HTTPException(404, "Informe no encontrado")
            if row["tier"] == 3 and not row["pareja_de"]:
                raise HTTPException(409, "Aun falta que tu pareja complete su parte.")
            if row["pareja_de"]:
                with db() as c:
                    prow = c.execute("SELECT email,nombre,respuestas,datos,perfil,sintesis FROM sesiones WHERE id=?", (row["pareja_de"],)).fetchone()
                if not prow or prow["respuestas"] in (None, "{}"):
                    raise HTTPException(409, "Aun falta que tu pareja complete su parte.")
                _tmp = path + ".building"
                # El INICIADOR (es_inic) va primero en el libro de pareja.
                if row["es_inic"]:
                    generar_couple(_tmp, row, prow)
                else:
                    generar_couple(_tmp, prow, row)
                os.replace(_tmp, path)   # escritura atomica: nadie lee un PDF a medias
            else:
                _resp = json.loads(row["respuestas"])
                _salud = _guardar_salud(session_id, _resp)
                generar_pdf(session_id, row["email"], row["nombre"], _resp, json.loads(row["datos"]), row["tier"], baremo(_salud), row["sexo"])
          except HTTPException:
            raise
          except Exception as e:
            raise HTTPException(500, "Error regenerando informe: %s" % e)
          finally:
            _liberar_memoria()
    # El PDF ya existe aqui: enviamos el email en segundo plano (comprador + aviso a Adapta).
    # enviar_copia respeta 'notificado', asi que no duplica en re-descargas.
    try:
        background_tasks.add_task(enviar_copia, session_id)
    except Exception:
        pass
    return FileResponse(path, media_type="application/pdf", filename="Tu_Libro_Financiero_ITAP.pdf")

def _asegurar_pdf(session_id):
    path = os.path.join(REPORTS_DIR, "itap_%s.pdf" % session_id)
    if os.path.exists(path):
        return path
    with _GEN_LOCK:
        if os.path.exists(path):
            return path
        with db() as c:
            row = c.execute("SELECT email,nombre,tier,respuestas,datos,pareja_de,sexo,sintesis,perfil,es_inic FROM sesiones WHERE id=?", (session_id,)).fetchone()
        if not row or row["respuestas"] in (None, "{}"):
            return None
        if row["tier"] == 3 and not row["pareja_de"]:
            return None
        try:
            if row["pareja_de"]:
                with db() as c:
                    prow = c.execute("SELECT email,nombre,respuestas,datos,perfil,sintesis FROM sesiones WHERE id=?", (row["pareja_de"],)).fetchone()
                if not prow or prow["respuestas"] in (None, "{}"):
                    return None
                _tmp = path + ".building"
                if row["es_inic"]:
                    generar_couple(_tmp, row, prow)
                else:
                    generar_couple(_tmp, prow, row)
                os.replace(_tmp, path)
            else:
                generar_pdf(session_id, row["email"], row["nombre"], json.loads(row["respuestas"]), json.loads(row["datos"]), row["tier"])
            return path if os.path.exists(path) else None
        except Exception:
            return None
        finally:
            _liberar_memoria()

def _resend_email(asunto, html, pdf_bytes, filename, to=None, extra=None):
    _att = [{"filename": filename, "content": base64.b64encode(pdf_bytes).decode("ascii")}]
    for _fn, _by in (extra or []):
        try: _att.append({"filename": _fn, "content": base64.b64encode(_by).decode("ascii")})
        except Exception: pass
    payload = {
        "from": RESEND_FROM,
        "to": to or [NOTIFY_EMAIL],
        "subject": asunto,
        "html": html,
        "attachments": _att,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://api.resend.com/emails", data=data, method="POST",
        headers={"Authorization": "Bearer %s" % RESEND_API_KEY, "Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "ignore")

def _pdf_fallback(path, cliente, tier):
    """PDF de respaldo de 1 pagina: el cliente SIEMPRE recibe algo aunque la generacion del libro falle."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        c=canvas.Canvas(path, pagesize=A4); W,H=A4
        c.setFillColorRGB(0.055,0.063,0.094); c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColorRGB(0.91,0.78,0.38); c.setFont("Helvetica-Bold",22); c.drawString(26*mm,H-40*mm,"ADAPTA FAMILY OFFICE")
        c.setFillColorRGB(0.93,0.92,0.89); c.setFont("Helvetica-Bold",16); c.drawString(26*mm,H-56*mm,"Tu Libro Financiero esta en preparacion")
        c.setFont("Helvetica",11.5); c.setFillColorRGB(0.62,0.65,0.71)
        for i,ln in enumerate(["Hola %s,"%(cliente or ""),"","Tu pago se ha recibido correctamente y tu informe se esta generando.",
                "Te lo enviaremos a este mismo correo en cuanto este listo (unos minutos).","",
                "Si en una hora no lo has recibido, escribenos y te lo entregamos al instante:",
                "info@adaptafamilyoffice.com   -   WhatsApp +34 683 34 35 31","","Gracias por confiar en Adapta Family Office."]):
            c.drawString(26*mm, H-76*mm-i*7*mm, ln)
        c.showPage(); c.save()
        return path if os.path.exists(path) else None
    except Exception:
        return None

def _enviar_resend(asunto, html, pdf_bytes, filename, to, reintentos=3, extra=None):
    """Envia por Resend con reintentos. Devuelve True si entrego."""
    import time
    for _i in range(reintentos):
        try:
            st,_=_resend_email(asunto, html, pdf_bytes, filename, to=to, extra=extra)
            if 200<=st<300: return True
        except Exception:
            pass
        time.sleep(2)
    return False

_ENVIANDO = set()
_ENVIO_LOCK = threading.Lock()
def enviar_copia(session_id):
    """Single-flight por sesion: una sola entrega a la vez. Evita el email duplicado
    a Adapta y la corrupcion de la tarjeta PNG por escritura concurrente del mismo fichero."""
    with _ENVIO_LOCK:
        if session_id in _ENVIANDO:
            return {"ok": True, "en_curso": True}
        _ENVIANDO.add(session_id)
    try:
        return _enviar_copia_impl(session_id)
    finally:
        with _ENVIO_LOCK:
            _ENVIANDO.discard(session_id)

def _enviar_copia_impl(session_id):
    """Entrega DURABLE y multicanal. notificado: 0=nada, 2=respaldo enviado (real pendiente), 1=real entregado.
    Idempotente: si ya se entrego el real, no hace nada. La pareja solo se entrega cuando esta lista."""
    if not RESEND_API_KEY:
        return {"ok": False, "reason": "resend_no_configurado"}
    with db() as c:
        row = c.execute("SELECT email,nombre,tier,respuestas,notificado,pareja_de,sexo FROM sesiones WHERE id=?", (session_id,)).fetchone()
    if not row or row["respuestas"] in (None, "{}"):
        return {"ok": False, "reason": "sesion_sin_respuestas"}
    if row["notificado"] == 1:
        return {"ok": True, "ya_enviado": True}
    if row["tier"] == 3 and not row["pareja_de"]:
        return {"ok": False, "reason": "pareja_pendiente"}   # no entregar hasta que la pareja complete
    cliente = (row["nombre"] or "").strip() or "(sin nombre)"
    email_cli = (row["email"] or "").strip()
    cli_valido = bool(email_cli) and ("@" in email_cli) and (not email_cli.lower().endswith(".test"))
    nuevo = (row["notificado"] != 2)   # primera vez que entramos en estado de espera
    tier_nombre = {1:"Diagnostico Rapido (19 EUR)",2:"Informe Avanzado (39 EUR)",3:"Analisis de Pareja (54 EUR)"}.get(row["tier"], "Tier %s"%row["tier"])
    # 1) Generar el PDF real; si falla, respaldo de 1 pagina (nunca dejamos al cliente sin nada)
    path = _asegurar_pdf(session_id); fallback = False
    if not path:
        path = os.path.join(REPORTS_DIR, "fallback_%s.pdf" % session_id)
        if not _pdf_fallback(path, cliente, row["tier"]):
            try: _resend_email("[CRITICO] ITAP no genera - %s"%cliente, "<p>Generacion y respaldo fallaron para %s (%s). Regenerar manualmente.</p>"%(cliente,email_cli), b"x", "aviso.txt", to=[NOTIFY_EMAIL])
            except Exception: pass
            return {"ok": False, "reason": "pdf_y_respaldo_fallaron"}
        fallback = True
    try:
        with open(path,"rb") as f: pdf_bytes=f.read()
    except Exception:
        return {"ok": False, "reason": "pdf_lectura"}
    # 2) Entrega al CLIENTE (el real siempre; el de espera solo una vez)
    cli_ok = False
    if cli_valido:
        if fallback:
            if nuevo:
                html_cli="<div style='font-family:Helvetica,Arial;color:#222;max-width:560px'><h2>Tu Libro Financiero esta en camino</h2><p>Hola %s, tu pago se recibio correctamente. Tu informe se esta terminando de generar y te llegara a este mismo correo en unos minutos. Si en una hora no lo tienes, escribenos a info@adaptafamilyoffice.com y te lo entregamos al instante.</p><p style='color:#888;font-size:12px'>Adapta Family Office</p></div>"%cliente
                cli_ok=_enviar_resend("Tu Libro Financiero esta en camino - Adapta", html_cli, pdf_bytes, "Adapta_en_preparacion.pdf", to=[email_cli])
        else:
            html_cli="<div style='font-family:Helvetica,Arial;color:#222;max-width:560px'><h2 style='color:#0a0a0b'>Tu Libro Financiero</h2><p>Hola %s,</p><p>Aqui tienes tu <b>diagnostico psicofinanciero completo</b>, en el PDF adjunto. Guardalo: es tu mapa de los proximos 100 dias.</p><p>Gracias por confiar en Adapta Family Office.</p><p style='color:#888;font-size:12px'>Adapta Family Office</p></div>"%cliente
            cli_ok=_enviar_resend("Tu Libro Financiero - Adapta Family Office", html_cli, pdf_bytes, "Tu_Libro_Financiero_Adapta.pdf", to=[email_cli])
    # 3) Adapta SIEMPRE recibe copia + estado (al entregar real, o la primera vez que algo va mal)
    if (not fallback) or nuevo:
        estado = "[REGENERAR-GENERACION-FALLO] " if fallback else ("[EMAIL-CLIENTE-FALLO] " if (cli_valido and not cli_ok) else ("[SIN-EMAIL-CLIENTE] " if not cli_valido else ""))
        html_adm="<h2>%sCompra ITAP</h2><p><b>Cliente:</b> %s<br><b>Email:</b> %s<br><b>Producto:</b> %s</p><p>%s</p>"%(estado or "", cliente, email_cli or "(sin email)", tier_nombre, ("ATENCION: requiere accion manual." if estado else "Copia del libro adjunta."))
        # Tarjeta del arquetipo (16 tipos) - PNG social premium, lista para redes (todos los tiers).
        _card_extra = None
        try:
            if row["respuestas"] not in (None, "{}", ""):
                _resp = json.loads(row["respuestas"]) if isinstance(row["respuestas"], str) else row["respuestas"]
                import arq16
                _code, _meta = arq16.arquetipo16(_resp)
                if _code and _meta:
                    _traits = " \u00b7 ".join(arq16.desglose(_code))
                    import tempfile as _tf
                    _cfd, _cardp = _tf.mkstemp(suffix=".png", prefix="arq_", dir=REPORTS_DIR); os.close(_cfd)
                    if rb.tarjeta_arquetipo16(_cardp, row["sexo"], _meta["n"], _meta["lema"], _meta["color"], _traits, _code):
                        with open(_cardp, "rb") as _cf:
                            _cbytes = _cf.read()
                        if _cbytes and _cbytes[:8] == b"\x89PNG\r\n\x1a\n" and _cbytes[-8:] and (b"IEND" in _cbytes[-12:]):
                            _card_extra = [("Arquetipo_%s.png" % cliente.replace(" ", "_"), _cbytes)]
                    try: os.remove(_cardp)
                    except Exception: pass
        except Exception:
            _card_extra = None
        _enviar_resend(("%sITAP - %s - %s"%(estado, cliente, tier_nombre)).strip(), html_adm, pdf_bytes, "ITAP_%s.pdf"%cliente.replace(" ","_"), to=[NOTIFY_EMAIL], extra=_card_extra)
    # 4) Estado de entrega
    if not fallback and (cli_ok or not cli_valido):
        with db() as c: c.execute("UPDATE sesiones SET notificado=1 WHERE id=?", (session_id,))
        return {"ok": True, "entregado": "real"}
    if fallback and row["notificado"] != 2:
        with db() as c: c.execute("UPDATE sesiones SET notificado=2 WHERE id=?", (session_id,))
    return {"ok": False, "reason": ("respaldo_enviado_real_pendiente" if fallback else "email_cliente_fallo")}

@app.get("/api/entregas")
def entregas(key: str = "", limite: int = 150):
    """Panel visual de entregas: cada venta y si el cliente recibio su PDF. Abre la URL con ?key=TU_CLAVE."""
    _k = os.environ.get("FUNNEL_KEY") or os.environ.get("RECONCILE_KEY")
    if _k and key != _k:
        return HTMLResponse("<body style='font-family:sans-serif;padding:40px'><h3>Panel protegido</h3><p>Anade <code>?key=TU_CLAVE</code> a la URL.</p></body>", status_code=403)
    try:
        with db() as c:
            rows = c.execute("SELECT id,nombre,email,tier,pagado,notificado,creado FROM sesiones "
                             "WHERE pagado=1 ORDER BY creado DESC LIMIT ?", (limite,)).fetchall()
    except Exception as e:
        return HTMLResponse("<body><h3>Error: %s</h3></body>" % e, status_code=500)
    TN = {1:"T1 - Rapido (19)", 2:"T2 - Avanzado (39)", 3:"T3 - Pareja (54)"}
    def estado(n):
        if n == 1: return (0, "ENTREGADO", "#1f9d55", "#e7f6ec")
        if n == 2: return (1, "EN CURSO",  "#b7791f", "#fdf6e3")
        return (2, "PENDIENTE", "#c53030", "#fdecec")  # pagado pero sin entregar -> el reconciliador lo reintenta
    data = []
    for r in rows:
        pr, txt, col, bg = estado(r["notificado"])
        data.append((pr, txt, col, bg, r))
    data.sort(key=lambda x: (-x[0], ))  # pendientes y en curso arriba
    n_ent = sum(1 for d in data if d[1]=="ENTREGADO")
    n_cur = sum(1 for d in data if d[1]=="EN CURSO")
    n_pen = sum(1 for d in data if d[1]=="PENDIENTE")
    filas = []
    for pr, txt, col, bg, r in data:
        nom = (r["nombre"] or "-"); em = (r["email"] or "-"); cr = (r["creado"] or "")[:16].replace("T", " ")
        filas.append("<tr style='background:%s'><td><b style='color:%s'>%s</b></td><td>%s</td><td>%s</td><td>%s</td><td style='color:#888'>%s</td></tr>"
                     % (bg, col, txt, nom, em, TN.get(r["tier"], r["tier"]), cr))
    html = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<meta http-equiv='refresh' content='60'><title>Entregas - Adapta</title>
<style>body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0e1018;color:#edeae2}
.wrap{max-width:920px;margin:0 auto;padding:24px}
h1{color:#e8c861;font-size:20px;margin:0 0 4px} .sub{color:#8a93a6;font-size:13px;margin-bottom:18px}
.cards{display:flex;gap:12px;margin-bottom:18px;flex-wrap:wrap}
.card{flex:1;min-width:120px;background:#161a24;border:1px solid #2a3140;border-radius:10px;padding:14px 16px}
.card .n{font-size:26px;font-weight:700} .card .l{font-size:11px;color:#8a93a6;text-transform:uppercase;letter-spacing:.05em}
table{width:100%;border-collapse:collapse;background:#fff;color:#222;border-radius:10px;overflow:hidden;font-size:13px}
th{background:#161a24;color:#e8c861;text-align:left;padding:9px 11px;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
td{padding:9px 11px;border-bottom:1px solid #eee}
.foot{color:#5c6470;font-size:11px;margin-top:14px}</style></head>
<body><div class='wrap'>
<h1>Entregas - Adapta Family Office</h1>
<div class='sub'>Cada venta y si el cliente recibio su PDF. Se actualiza solo cada 60 s.</div>
<div class='cards'>
<div class='card'><div class='n' style='color:#5fb98e'>__ENT__</div><div class='l'>Entregados</div></div>
<div class='card'><div class='n' style='color:#e8c861'>__CUR__</div><div class='l'>En curso</div></div>
<div class='card'><div class='n' style='color:#d9755b'>__PEN__</div><div class='l'>Pendientes</div></div>
</div>
<table><thead><tr><th>Estado</th><th>Cliente</th><th>Email</th><th>Producto</th><th>Fecha</th></tr></thead>
<tbody>__FILAS__</tbody></table>
<div class='foot'>Total pagados: __TOT__ . Los pendientes se reintentan solos cada 10 min. Si alguno sigue rojo, escribe al cliente o avisame.</div>
</div></body></html>"""
    html = (html.replace("__ENT__", str(n_ent)).replace("__CUR__", str(n_cur)).replace("__PEN__", str(n_pen))
                .replace("__TOT__", str(len(data))).replace("__FILAS__", "".join(filas) or "<tr><td colspan=5 style='padding:20px;text-align:center;color:#888'>Aun no hay ventas.</td></tr>"))
    return HTMLResponse(html)

@app.get("/api/reconciliar")
def reconciliar(key: str = "", limite: int = 100):
    """Barre sesiones PAGADAS sin entrega confirmada y reintenta la entrega garantizada.
    Pensado para ejecutarse cada pocos minutos (tarea programada). Idempotente y seguro."""
    _k = os.environ.get("FUNNEL_KEY") or os.environ.get("RECONCILE_KEY")
    if _k and key != _k:
        return {"error": "protegido"}
    res = {"revisados": 0, "entregados": 0, "pendientes": 0, "detalle": []}
    try:
        with db() as c:
            rows = c.execute("SELECT id FROM sesiones WHERE pagado=1 AND (notificado IS NULL OR notificado<>1) "
                             "AND respuestas IS NOT NULL AND respuestas<>'{}' ORDER BY creado DESC LIMIT ?", (limite,)).fetchall()
        for r in rows:
            sid = r["id"]
            try:
                out = enviar_copia(sid)
            except Exception as e:
                out = {"ok": False, "reason": "excepcion_%s" % type(e).__name__}
            res["revisados"] += 1
            if out.get("ok") and out.get("entregado") == "real":
                res["entregados"] += 1
            else:
                res["pendientes"] += 1
            res["detalle"].append({"sid": sid[:8], "estado": out.get("reason") or ("entregado" if out.get("ok") else "?")})
    except Exception as e:
        res["error"] = "%s" % e
    return res

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


# === Reconciliador automatico en segundo plano: garantiza la entrega sin depender de cron externo ===
def _sweeper_loop():
    import time
    time.sleep(90)   # margen tras el arranque
    while True:
        try:
            reconciliar(key=(os.environ.get("FUNNEL_KEY") or os.environ.get("RECONCILE_KEY") or ""))
        except Exception:
            pass
        time.sleep(600)   # cada 10 minutos barre pagos sin entrega y reintenta

try:
    threading.Thread(target=_sweeper_loop, daemon=True).start()
except Exception:
    pass
