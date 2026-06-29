"""ITAP — Backend de produccion. Instrumento + motor + Libros. Profundidad por tier. RGPD. Nombre del cliente."""
import os, uuid, json, datetime, tempfile, sqlite3, base64, urllib.request, urllib.error, urllib.parse
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import report_book as rb
import report_couple as rc
import motor_financiero_v3 as mfv3
import secciones_v3 as sv3

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
# Remitente e enlace base para la invitacion de pareja (parametrizables por env).
# Por fiabilidad de entrega, por defecto usa el MISMO remitente probado que los informes (RESEND_FROM, itap@),
# que ya tiene historial de envio y reputacion. Override con INVITE_FROM si se quiere otra direccion.
INVITE_FROM = (os.environ.get("INVITE_FROM", "").strip() or RESEND_FROM)
INVITE_BASE_URL = (os.environ.get("INVITE_BASE_URL", "").strip()
                   or "https://diagnostico.adaptafamilyoffice.com/empezar2.html")
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

class InvitarParejaPayload(BaseModel):
    uuid_pareja: str
    email_destino: str
    nombre_iniciador: Optional[str] = None

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
    for _k in ("pct_gasto_fijo", "pct_vivienda", "rentabilidad_actual", "suscripciones_pct", "dti", "dti_neto", "concentracion_ingresos"):
        if d.get(_k) is not None:
            try: d[_k] = max(0.0, min(100.0, float(d[_k])))
            except Exception: d[_k] = None
    for _k in ("gasto_mensual", "ingreso_mensual", "ahorro_mensual", "patrimonio", "coste_vivienda",
               "cuota_deuda", "deuda_total", "pension_estimada", "gasto_estatus", "renta_pasiva",
               "inversiones_liquidas", "gastos_comunes", "gastos_anuales", "valor_inmuebles", "ing_alquiler"):
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
    # Derivar de los desgloses por partidas (cuando el cliente los rellena, mandan sobre la pregunta suelta)
    try:
        _ind=d.get("ingreso_mensual_detalle")
        if isinstance(_ind,list):
            _PAS={"alquileres","dividendos","intereses / cupones","intereses","plusvalías","plusvalias","royalties / propiedad intelectual","royalties","pensión","pension"}
            _rp=sum(float((r or {}).get("v") or 0) for r in _ind if str((r or {}).get("c","")).strip().lower() in _PAS)
            if _rp>0: d["renta_pasiva"]=_rp
    except Exception: pass
    try:
        _pd=d.get("patrimonio_detalle")
        if isinstance(_pd,list):
            _tot=sum(float((r or {}).get("v") or 0) for r in _pd)
            _viv=sum(float((r or {}).get("v") or 0) for r in _pd if "vivienda" in str((r or {}).get("c","")).lower())
            if _tot>0 and _viv>0: d["pct_vivienda"]=max(0.0,min(100.0,100.0*_viv/_tot))
    except Exception: pass
    # Valor de los inmuebles EN ALQUILER (inversion): se DERIVA de la categoria «Otros inmuebles» del
    # desglose de patrimonio (ya no se pregunta suelta). NO incluye «Vivienda habitual» ni «Segunda vivienda»
    # (son activos de USO, no de renta). Solo se deriva si hay senal de alquiler (ingreso de alquiler > 0) o
    # si ya hay «Otros inmuebles» > 0. Con esto report_book calcula la rentabilidad REAL del ladrillo.
    try:
        _pd=d.get("patrimonio_detalle")
        if isinstance(_pd,list):
            _otros=0.0
            for r in _pd:
                _c=str((r or {}).get("c","")).strip().lower()
                if "otros inmuebles" in _c:
                    try: _otros+=max(0.0,float((r or {}).get("v") or 0))
                    except Exception: pass
            # senal de alquiler: ingreso de alquiler derivado, campo suelto, o categoria «Alquileres» del desglose de ingresos
            _senal_alq=0.0
            try: _senal_alq=float(d.get("ingreso_alquiler") or 0)
            except Exception: _senal_alq=0.0
            if _senal_alq<=0:
                try: _senal_alq=float(d.get("ing_alquiler") or 0)
                except Exception: _senal_alq=0.0
            if _senal_alq<=0:
                _ind2=d.get("ingreso_mensual_detalle")
                if isinstance(_ind2,list):
                    try: _senal_alq=sum(float((r or {}).get("v") or 0) for r in _ind2 if "alquil" in str((r or {}).get("c","")).strip().lower())
                    except Exception: _senal_alq=0.0
            if _otros>0 and (_senal_alq>0 or _otros>0):
                d["valor_inmuebles"]=_otros
    except Exception: pass
    # Coste de vivienda: se DERIVA de la categoria Vivienda del desglose de gasto (ya no se pregunta suelta)
    try:
        _gd=d.get("gasto_mensual_detalle")
        if isinstance(_gd,list):
            _cv=sum(float((r or {}).get("v") or 0) for r in _gd if "vivienda" in str((r or {}).get("c","")).lower())
            if _cv>0: d["coste_vivienda"]=_cv
    except Exception: pass
    # Suscripciones: peso de la categoria "Suscripciones / servicios" del desglose de gasto sobre el gasto total.
    # Sustituye la pregunta cualitativa: el dato manda sobre la sensacion.
    try:
        _gd=d.get("gasto_mensual_detalle")
        if isinstance(_gd,list):
            _gtot=sum(float((r or {}).get("v") or 0) for r in _gd)
            _sus=sum(float((r or {}).get("v") or 0) for r in _gd if "suscrip" in str((r or {}).get("c","")).lower())
            if _sus>0:
                d["suscripciones_eur"]=_sus
                if _gtot>0: d["suscripciones_pct"]=max(0.0,min(100.0,100.0*_sus/_gtot))
    except Exception: pass
    # Concentracion de ingresos: cuanto pesa la mayor fuente del desglose de ingresos (% del total).
    # Deriva de las partidas, no de una pregunta de percepcion. Tambien deja el nº de fuentes con peso real.
    try:
        _ind=d.get("ingreso_mensual_detalle")
        if isinstance(_ind,list):
            _vals=[float((r or {}).get("v") or 0) for r in _ind if float((r or {}).get("v") or 0)>0]
            _tot=sum(_vals)
            if _tot>0 and _vals:
                d["concentracion_ingresos"]=max(0.0,min(100.0,100.0*max(_vals)/_tot))
                d["n_fuentes_ingreso"]=len(_vals)
    except Exception: pass
    # Ingreso por alquileres: se deriva de la categoria «Alquileres» del desglose de ingresos,
    # del campo ing_alquiler, o de la renta pasiva tipo alquiler. Conservador: solo lo que es claramente alquiler.
    try:
        _ial=0.0
        _ind=d.get("ingreso_mensual_detalle")
        if isinstance(_ind,list):
            _ial=sum(float((r or {}).get("v") or 0) for r in _ind if "alquil" in str((r or {}).get("c","")).strip().lower())
        if _ial<=0:
            _ial=float(d.get("ing_alquiler") or 0)
        if _ial>0:
            d["ingreso_alquiler"]=_ial
    except Exception: pass
    # DTI (debt-to-income): peso fijo de la deuda sobre el ingreso. Se deriva de cuota_deuda/ingreso_mensual
    # cuando el cliente da la cuota; complementa (no sustituye) la percepcion cualitativa de la capa C10.
    # dti_neto: resta del coste de la deuda lo que cubren los alquileres (deuda de inversion multipatrimonial).
    # Un inversor con hipotecas cubiertas por alquileres NO esta asfixiado; el dti bruto daria una alerta roja falsa.
    try:
        _cuo=float(d.get("cuota_deuda") or 0); _ing=float(d.get("ingreso_mensual") or 0)
        if _cuo>0 and _ing>0:
            d["dti"]=max(0.0,min(100.0,100.0*_cuo/_ing))
            _ial=float(d.get("ingreso_alquiler") or 0)
            _cuo_neta=max(0.0,_cuo-_ial)
            d["dti_neto"]=max(0.0,min(100.0,100.0*_cuo_neta/_ing))
    except Exception: pass
    # Hijos: si el cliente dio las edades una a una (edades_hijos=[...]), el nº de hijos y la edad del menor
    # se DERIVAN del array (manda sobre las preguntas sueltas). Las edades "no las sé / más tarde" llegan como
    # null y no rompen el calculo. Se conserva edad_hijo_menor por compatibilidad con el motor existente.
    try:
        _eh=d.get("edades_hijos")
        if isinstance(_eh,list) and _eh:
            d["n_hijos"]=len(_eh)
            _conoc=[]
            for _x in _eh:
                try:
                    if _x is not None and str(_x)!="":
                        _conoc.append(int(float(_x)))
                except Exception: pass
            if _conoc:
                d["edad_hijo_menor"]=min(_conoc)
    except Exception: pass
    # ratio_dividendo_nomina: del desglose de ingresos, peso del dividendo sobre la suma
    # nomina+dividendo. Es la senal objetiva de como se autorretribuye el empresario:
    # 0 = solo nomina (suele dejar fiscalidad sin optimizar); >0.6 = sobreponderar dividendo
    # (riesgo de cotizacion/jubilacion floja). report_book emite el juicio de salud fiscal.
    # Sustituye la lectura cualitativa: el desglose manda sobre la percepcion.
    try:
        _ind=d.get("ingreso_mensual_detalle")
        if isinstance(_ind,list):
            _nom=0.0; _div=0.0
            for r in _ind:
                _c=str((r or {}).get("c","")).strip().lower()
                try: _v=max(0.0,float((r or {}).get("v") or 0))
                except Exception: _v=0.0
                if "nómina" in _c or "nomina" in _c or "salario" in _c: _nom+=_v
                elif "dividendo" in _c: _div+=_v
            _base=_nom+_div
            if _base>0:
                d["ratio_dividendo_nomina"]=max(0.0,min(1.0,_div/_base))
                d["nomina_eur"]=_nom; d["dividendo_eur"]=_div
    except Exception: pass
    # Art. 2 (una cifra, un dueno): el ingreso NETO total lo da el cliente en NUM-2 (ingreso_mensual) y lo
    # DESGLOSA por categorias en ingreso_mensual_detalle. Las 4 preguntas sueltas de importe por fuente
    # (ing_trabajo/inversion/alquiler/otros) se ELIMINARON del cuestionario por redundantes con el desglose.
    # Aqui los 4 "buckets" ing_* se DERIVAN del desglose (mapeando categorias a fuentes) para alimentar el
    # €/hora de score_v2.calcular_fuentes. Conservador: clamp >=0, solo si el bucket no viene ya dado.
    try:
        _ind=d.get("ingreso_mensual_detalle")
        if isinstance(_ind,list):
            _B_TRAB={"nómina / salario","nomina / salario","bonus / variable","autónomo / actividad","autonomo / actividad","negocio propio (sl)"}
            _B_INV ={"dividendos","intereses / cupones","plusvalías","plusvalias"}
            _B_ALQ ={"alquileres"}
            _B_OTR ={"royalties / propiedad intelectual","pensión","pension","otros"}
            _bt=_bi=_ba=_bo=0.0
            for r in _ind:
                _c=str((r or {}).get("c","")).strip().lower()
                try: _v=max(0.0,float((r or {}).get("v") or 0))
                except Exception: _v=0.0
                if   _c in _B_TRAB: _bt+=_v
                elif _c in _B_INV:  _bi+=_v
                elif _c in _B_ALQ:  _ba+=_v
                elif _c in _B_OTR:  _bo+=_v
            for _k,_val in (("ing_trabajo",_bt),("ing_inversion",_bi),("ing_alquiler",_ba),("ing_otros",_bo)):
                if d.get(_k) is None or str(d.get(_k))=="":
                    d[_k]=max(0.0,_val)
    except Exception:
        pass
    # ingreso_mensual: se mantiene el TOTAL que da el cliente (NUM-2). Solo como red de seguridad, si no
    # llega o es 0 pero el desglose suma algo, usamos la suma del desglose como total.
    try:
        _ind=d.get("ingreso_mensual_detalle")
        if isinstance(_ind,list):
            _sd=sum(max(0.0,float((r or {}).get("v") or 0)) for r in _ind)
            if _sd>0 and not (float(d.get("ingreso_mensual") or 0)>0):
                d["ingreso_mensual"]=_sd
    except Exception:
        pass
    # horas_semana: si el cliente declaro horas por fuente (h_*), el total semanal se DERIVA de la suma.
    # (Las preguntas de HORAS por fuente SIGUEN en el cuestionario: el desglose no captura el tiempo.)
    try:
        _kh=("h_trabajo","h_inversion","h_alquiler","h_otros")
        if any(d.get(k) is not None and str(d.get(k))!="" for k in _kh):
            _sh=sum(float(d.get(k) or 0) for k in _kh)
            if _sh>0: d["horas_semana"]=_sh
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
        # Guardián de coherencia (fuente única de verdad): SOLO avisa por log, nunca bloquea la entrega.
        try:
            import qa_coherencia
            _hall = qa_coherencia.revisar_coherencia(d, extras)
            if _hall:
                print("[QA-COHERENCIA] sesion=%s tier=%s\n%s" % (
                    (email or "?"), tier, qa_coherencia.resumen_log(_hall)), flush=True)
        except Exception as _e:
            print("[QA-COHERENCIA] guardián no ejecutado: %s" % _e, flush=True)
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
        row = c.execute("SELECT pareja_de,pagado,tier,es_inic,nombre FROM sesiones WHERE id=?", (session_id,)).fetchone()
    if not row:
        return {"existe": False}
    pid = row["pareja_de"]; lista = False
    if pid:
        with db() as c:
            pr = c.execute("SELECT respuestas FROM sesiones WHERE id=?", (pid,)).fetchone()
        lista = bool(pr and pr["respuestas"] not in (None, "{}", ""))
    # nombre_iniciador: solo el de pila, para personalizar la invitacion ("Marta te ha invitado...").
    # Nunca exponemos el email ni datos sensibles del iniciador.
    _nom = (row["nombre"] or "").strip()
    _nom_pila = _nom.split()[0] if _nom else ""
    return {"existe": True, "es_pareja": (row["tier"] == 3), "es_inic": bool(row["es_inic"]),
            "pareja_lista": lista, "pagado": bool(row["pagado"]), "gated": bool(STRIPE_WEBHOOK_SECRET),
            "nombre_iniciador": _nom_pila}

# --- Invitacion de pareja por email (Resend, con degradacion elegante) ---
import re as _re
_EMAIL_RE = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _email_valido(e):
    e = (e or "").strip()
    return bool(e) and len(e) <= 254 and bool(_EMAIL_RE.match(e))

def _build_invite_email(uuid_pareja, email_destino, nombre_iniciador=None):
    """Construye el payload de Resend para la invitacion de pareja.
    Funcion pura (sin red) para poder testearla en aislamiento."""
    enlace = "%s?pareja=%s" % (INVITE_BASE_URL.rstrip("/") if "?" not in INVITE_BASE_URL else INVITE_BASE_URL,
                               urllib.parse.quote(uuid_pareja, safe=""))
    quien = (nombre_iniciador or "").strip()
    intro = ("%s te ha invitado a vuestro Diagnostico de Pareja de Adapta." % quien) if quien \
            else "Te han invitado a vuestro Diagnostico de Pareja de Adapta."
    asunto = ("%s te invita a vuestro Diagnostico de Pareja - Adapta" % quien) if quien \
             else "Te invitan a vuestro Diagnostico de Pareja - Adapta"
    html = (
        "<div style=\"font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;"
        "background:#101014;color:#e9e9e6;border-radius:16px;padding:30px 28px\">"
        "<div style=\"font-weight:800;font-size:20px;letter-spacing:.5px\">ADAPTA "
        "<span style=\"color:#fdd731;font-size:12px;font-weight:600\">family office</span></div>"
        "<h1 style=\"font-size:21px;line-height:1.3;margin:22px 0 14px\">%s</h1>"
        "<p style=\"font-size:15px;line-height:1.6;color:#c3c3bd\">La otra persona ya ha completado su parte y "
        "<b style=\"color:#fff\">el informe conjunto ya esta pagado</b>. Solo tienes que completar "
        "<b style=\"color:#fff\">tu cuestionario</b> &mdash; es <b style=\"color:#fdd731\">gratis</b>, no tienes que pagar nada &mdash; "
        "y se generara vuestro Libro de Pareja con los dos perfiles.</p>"
        "<p style=\"font-size:15px;line-height:1.6;color:#c3c3bd\">Te llevara unos 15-20 minutos. Cuando termines, "
        "ambos recibis el documento conjunto por email.</p>"
        "<div style=\"text-align:center;margin:26px 0\">"
        "<a href=\"%s\" style=\"display:inline-block;background:#fdd731;color:#101014;text-decoration:none;"
        "font-weight:700;font-size:16px;padding:14px 26px;border-radius:12px\">Empezar mi parte &rarr;</a></div>"
        "<p style=\"font-size:12px;line-height:1.6;color:#8a8a84\">Si el boton no funciona, copia este enlace en tu navegador:<br>"
        "<a href=\"%s\" style=\"color:#fdd731;word-break:break-all\">%s</a></p>"
        "<p style=\"font-size:11.5px;color:#6b6b66;margin-top:22px;border-top:1px solid #2a2a30;padding-top:14px\">"
        "Adapta Family Office &middot; Diagnostico psicofinanciero confidencial.</p>"
        "</div>"
    ) % (intro, enlace, enlace, enlace)
    return {"from": INVITE_FROM, "to": [email_destino], "subject": asunto, "html": html}, enlace

def _resend_post(payload):
    """Envia un payload generico a Resend. Devuelve (status, body). No registra la clave."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request("https://api.resend.com/emails", data=data, method="POST",
        headers={"Authorization": "Bearer %s" % RESEND_API_KEY, "Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "ignore")

@app.post("/api/invitar-pareja")
def invitar_pareja(payload: InvitarParejaPayload):
    """Envia por email el enlace de invitacion a la pareja.
    Degradacion: si no hay RESEND_API_KEY o falla el envio, responde de forma controlada
    (ok:false + motivo) para que el frontend siga ofreciendo el enlace copiable. Nunca rompe el flujo."""
    email_destino = (payload.email_destino or "").strip()
    if not _email_valido(email_destino):
        return {"ok": False, "motivo": "email_invalido"}
    # Seguridad anti-spam: solo enviamos el enlace de un uuid que exista y sea un iniciador de pareja (tier 3).
    with db() as c:
        row = c.execute("SELECT tier,nombre FROM sesiones WHERE id=?", (payload.uuid_pareja,)).fetchone()
    if not row:
        return {"ok": False, "motivo": "uuid_invalido"}
    if row["tier"] != 3:
        return {"ok": False, "motivo": "uuid_invalido"}
    # Degradacion: sin clave configurada, no se rompe nada -> el frontend usa el enlace copiable.
    if not RESEND_API_KEY:
        return {"ok": False, "motivo": "email_no_configurado"}
    # Nombre del iniciador: el que envia el cliente o, si no, el de la base.
    nombre_iniciador = (payload.nombre_iniciador or "").strip()
    if not nombre_iniciador:
        _bn = (row["nombre"] or "").strip()
        nombre_iniciador = _bn.split()[0] if _bn else ""
    msg, _enlace = _build_invite_email(payload.uuid_pareja, email_destino, nombre_iniciador)
    try:
        status, _body = _resend_post(msg)
        if 200 <= status < 300:
            return {"ok": True}
        return {"ok": False, "motivo": "envio_fallido"}
    except Exception:
        # No registramos la excepcion entera para no arriesgar fugas; mensaje neutro.
        return {"ok": False, "motivo": "envio_fallido"}

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
        if tier==3:
            _lineas=["Hola %s,"%(cliente or ""),"","Tu pago se ha recibido correctamente.",
                "Recibireis vuestro Libro de Pareja por email en cuanto tu pareja complete su parte.","",
                "Si tras completarlo ambos no lo recibis en una hora, escribenos y te lo entregamos al instante:",
                "info@adaptafamilyoffice.com","","Gracias por confiar en Adapta Family Office."]
        else:
            _lineas=["Hola %s,"%(cliente or ""),"","Tu pago se ha recibido correctamente y tu informe se esta generando.",
                "Te lo enviaremos a este mismo correo en cuanto este listo (unos minutos).","",
                "Si en una hora no lo has recibido, escribenos y te lo entregamos al instante:",
                "info@adaptafamilyoffice.com","","Gracias por confiar en Adapta Family Office."]
        for i,ln in enumerate(_lineas):
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
        # Confirmacion de pago al iniciador (una sola vez). El libro se entrega cuando la pareja complete.
        if RESEND_API_KEY and row["notificado"] != 2:
            _cl = (row["nombre"] or "").strip() or "(sin nombre)"
            _ec = (row["email"] or "").strip()
            _from = INVITE_FROM   # misma clave 'from' que usa _build_invite_email (payload de invitacion)
            if _ec and ("@" in _ec) and not _ec.lower().endswith(".test"):
                _html_w = ("<div style='font-family:Helvetica,Arial;color:#222;max-width:560px'>"
                           "<h2 style='color:#0a0a0b'>Pago recibido</h2>"
                           "<p>Hola %s,</p>"
                           "<p>Tu pago se ha recibido correctamente. <b>Recibireis vuestro Libro de Pareja</b> por email "
                           "en cuanto tu pareja complete su parte.</p>"
                           "<p>Si aun no le has enviado la invitacion, hazlo desde la pantalla del diagnostico.</p>"
                           "<p>Gracias por confiar en Adapta Family Office.</p>"
                           "<p style='color:#888;font-size:12px'>Adapta Family Office</p></div>") % _cl
                try: _resend_post({"from": _from, "to": [_ec], "subject": "Pago recibido - Vuestro Libro de Pareja en camino - Adapta", "html": _html_w})
                except Exception: pass
            try:
                _html_a = ("<h2>Compra ITAP (Pareja) - pago recibido, esperando a la pareja</h2>"
                           "<p><b>Cliente:</b> %s<br><b>Email:</b> %s<br><b>Producto:</b> Analisis de Pareja (54 EUR)</p>"
                           "<p>El iniciador pago. Pendiente de que la pareja complete su parte.</p>") % (_cl, _ec or "(sin email)")
                _resend_post({"from": _from, "to": [NOTIFY_EMAIL], "subject": "ITAP - Pareja pagada (esperando pareja) - %s" % _cl, "html": _html_a})
            except Exception: pass
            try:
                with db() as c: c.execute("UPDATE sesiones SET notificado=2 WHERE id=?", (session_id,))
            except Exception: pass
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
    # Tarjeta del arquetipo: se genera ANTES para adjuntarla tambien al cliente
    # Tarjeta del arquetipo (16 tipos) - PNG social premium, lista para redes (todos los tiers).
    def _mk_card(_respuestas, _sexo, _nombre):
        """Genera UNA tarjeta de arquetipo (filename, bytes) o None. Misma validacion PNG/tempfile/cleanup."""
        try:
            if _respuestas in (None, "{}", ""):
                return None
            _resp = json.loads(_respuestas) if isinstance(_respuestas, str) else _respuestas
            import arq16
            _code, _meta = arq16.arquetipo16(_resp)
            if not (_code and _meta):
                return None
            _traits = " \u00b7 ".join(arq16.desglose(_code))
            import tempfile as _tf
            _cfd, _cardp = _tf.mkstemp(suffix=".png", prefix="arq_", dir=REPORTS_DIR); os.close(_cfd)
            _out = None
            try:
                if rb.tarjeta_arquetipo16(_cardp, _sexo, _meta["n"], _meta["lema"], _meta["color"], _traits, _code):
                    with open(_cardp, "rb") as _cf:
                        _cbytes = _cf.read()
                    if _cbytes and _cbytes[:8] == b"\x89PNG\r\n\x1a\n" and _cbytes[-8:] and (b"IEND" in _cbytes[-12:]):
                        _out = ("Arquetipo_%s.png" % (str(_nombre or "Adapta").replace(" ", "_")), _cbytes)
            finally:
                try: os.remove(_cardp)
                except Exception: pass
            return _out
        except Exception:
            return None
    _card_extra = []
    _ic = _mk_card(row["respuestas"], row["sexo"], cliente)
    if _ic: _card_extra.append(_ic)
    if row["tier"] == 3 and row["pareja_de"]:
        try:
            with db() as c:
                _pr2 = c.execute("SELECT respuestas,sexo,nombre FROM sesiones WHERE id=?", (row["pareja_de"],)).fetchone()
            if _pr2:
                _pc = _mk_card(_pr2["respuestas"], _pr2["sexo"], (_pr2["nombre"] or "Pareja"))
                if _pc and (_pc[0] != (_ic[0] if _ic else None)):
                    _card_extra.append(_pc)
                elif _pc and _ic and _pc[0] == _ic[0]:
                    _card_extra.append(("Arquetipo_pareja.png", _pc[1]))
        except Exception:
            pass
    if not _card_extra:
        _card_extra = None

    # 2) Entrega al CLIENTE (el real siempre; el de espera solo una vez)
    cli_ok = False
    if cli_valido:
        if fallback:
            if nuevo:
                if row["tier"]==3:
                    html_cli="<div style='font-family:Helvetica,Arial;color:#222;max-width:560px'><h2>Vuestro Libro de Pareja esta en camino</h2><p>Hola %s, tu pago se recibio correctamente. Lo recibireis los dos por email en cuanto tu pareja complete su parte. Si tras completarlo ambos no lo teneis en una hora, escribenos a info@adaptafamilyoffice.com y te lo entregamos al instante.</p><p style='color:#888;font-size:12px'>Adapta Family Office</p></div>"%cliente
                    cli_ok=_enviar_resend("Vuestro Libro de Pareja esta en camino - Adapta", html_cli, pdf_bytes, "Adapta_en_preparacion.pdf", to=[email_cli])
                else:
                    html_cli="<div style='font-family:Helvetica,Arial;color:#222;max-width:560px'><h2>Tu Libro Financiero esta en camino</h2><p>Hola %s, tu pago se recibio correctamente. Tu informe se esta terminando de generar y te llegara a este mismo correo en unos minutos. Si en una hora no lo tienes, escribenos a info@adaptafamilyoffice.com y te lo entregamos al instante.</p><p style='color:#888;font-size:12px'>Adapta Family Office</p></div>"%cliente
                    cli_ok=_enviar_resend("Tu Libro Financiero esta en camino - Adapta", html_cli, pdf_bytes, "Adapta_en_preparacion.pdf", to=[email_cli])
        else:
            html_cli="<div style='font-family:Helvetica,Arial;color:#222;max-width:560px'><h2 style='color:#0a0a0b'>Tu Libro Financiero</h2><p>Hola %s,</p><p>Aqui tienes tu <b>diagnostico psicofinanciero completo</b>, en el PDF adjunto. Guardalo: es tu mapa de los proximos 100 dias.</p><p>Gracias por confiar en Adapta Family Office.</p><p style='color:#888;font-size:12px'>Adapta Family Office</p></div>"%cliente
            cli_ok=_enviar_resend("Tu Libro Financiero - Adapta Family Office", html_cli, pdf_bytes, "Tu_Libro_Financiero_Adapta.pdf", to=[email_cli], extra=_card_extra)
    # 2b) Pareja (tier 3): el segundo miembro recibe TAMBIEN el Libro de Pareja conjunto, en envio SEPARADO (privacidad)
    if (not fallback) and row["tier"]==3 and row["pareja_de"]:
        try:
            with db() as c:
                _pr = c.execute("SELECT email,nombre FROM sesiones WHERE id=?", (row["pareja_de"],)).fetchone()
            _pe = ((_pr["email"] if _pr else "") or "").strip()
            if _pe and "@" in _pe and not _pe.lower().endswith(".test") and _pe.lower()!=email_cli.lower():
                _pn = ((_pr["nombre"] if _pr else "") or "").strip() or "(sin nombre)"
                _html_p = "<div style='font-family:Helvetica,Arial;color:#222;max-width:560px'><h2 style='color:#0a0a0b'>Vuestro Libro de Pareja</h2><p>Hola %s,</p><p>Aqui teneis vuestro <b>Diagnostico de Pareja completo</b>, con los dos perfiles cruzados, en el PDF adjunto.</p><p>Gracias por confiar en Adapta Family Office.</p><p style='color:#888;font-size:12px'>Adapta Family Office</p></div>" % _pn
                _enviar_resend("Vuestro Libro de Pareja - Adapta Family Office", _html_p, pdf_bytes, "Libro_de_Pareja_Adapta.pdf", to=[_pe], extra=_card_extra)
        except Exception:
            pass
    # 3) Adapta SIEMPRE recibe copia + estado (al entregar real, o la primera vez que algo va mal)
    if (not fallback) or nuevo:
        estado = "[REGENERAR-GENERACION-FALLO] " if fallback else ("[EMAIL-CLIENTE-FALLO] " if (cli_valido and not cli_ok) else ("[SIN-EMAIL-CLIENTE] " if not cli_valido else ""))
        html_adm="<h2>%sCompra ITAP</h2><p><b>Cliente:</b> %s<br><b>Email:</b> %s<br><b>Producto:</b> %s</p><p>%s</p>"%(estado or "", cliente, email_cli or "(sin email)", tier_nombre, ("ATENCION: requiere accion manual." if estado else "Copia del libro adjunta."))
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


# ---------- Diagnostico v3 (cuestionario adaptativo nuevo; aditivo, no toca /api/complete) ----------
class DiagV3(BaseModel):
    session_id: str = ""
    email: str = ""
    nombre: str = ""
    ruta: dict = {}
    ingresos: list = []
    gastos: dict = {}
    deudas: list = []
    cartera: dict = {}
    patrimonio: dict = {}
    familia: dict = {}
    riesgo: dict = {}
    expectativas: dict = {}

def _motor_v3(p: DiagV3):
    ing = mfv3.analizar_ingresos(p.ingresos)
    gas = mfv3.analizar_gastos(p.gastos.get("ancla"), p.gastos.get("detalle"))
    deu = mfv3.analizar_deuda(p.deudas, ing.get("ingreso_mensual"))
    car = mfv3.analizar_cartera(p.cartera, gas.get("gasto_mensual"),
                                p.cartera.get("horizonte"), p.cartera.get("perfil_declarado"))
    pat = mfv3.analizar_patrimonio(p.patrimonio.get("vivienda"), p.patrimonio.get("otros"),
                                   p.patrimonio.get("hipoteca_vivienda"),
                                   car.get("inversiones_liquidas", 0), deu.get("deuda_total", 0))
    fam = mfv3.analizar_familia(p.familia.get("edades")) if p.ruta.get("hijos") else {"n_dependientes": 0}
    perfil = p.riesgo.get("perfil_riesgo")
    rent_real = p.expectativas.get("rent_real") or mfv3.RENT_REAL_POR_PERFIL.get(perfil or 3, 5.5)
    exp = mfv3.analizar_expectativas(
        p.expectativas.get("gasto"), p.expectativas.get("pension"),
        car.get("inversiones_liquidas", 0),
        max(0, (ing.get("ingreso_mensual", 0) or 0) - (gas.get("gasto_mensual", 0) or 0)),
        p.expectativas.get("horizonte") or p.cartera.get("horizonte"), rent_real,
        p.expectativas.get("rent_esperada"), p.expectativas.get("herencia_importe", 0))
    ag = mfv3.agregar(ing, gas, deu, car, pat, fam, exp, p.ruta)
    payload_ia = mfv3.construir_payload_narrativo(ag, perfil)
    return {"ok": True, "ingresos": ing, "gastos": gas, "deuda": deu, "cartera": car,
            "patrimonio": pat, "familia": fam, "expectativas": exp, "agregado": ag,
            "perfil_riesgo": perfil, "payload_ia": payload_ia}

@app.post("/api/diag-v3")
def diag_v3(p: DiagV3):
    try:
        return _motor_v3(p)
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/diag-v3-pdf")
def diag_v3_pdf(p: DiagV3):
    """Anexo financiero v3 (7 secciones) bajo demanda. Aislado: NO toca /api/complete
    ni el disparador de entrega. Serializado con _GEN_LOCK (pico de RAM)."""
    try:
        res = _motor_v3(p)
    except Exception as e:
        raise HTTPException(500, "Error de motor v3: %s" % e)
    import tempfile
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    fd, tmp = tempfile.mkstemp(prefix="anexo_v3_", suffix=".pdf", dir=REPORTS_DIR)
    os.close(fd)
    with _GEN_LOCK:
        try:
            doc = SimpleDocTemplate(tmp, pagesize=A4, topMargin=18*mm, bottomMargin=18*mm,
                                    leftMargin=25*mm, rightMargin=25*mm)
            doc.build(sv3.secciones_financieras_v3(res))
        except Exception as e:
            try: os.remove(tmp)
            except Exception: pass
            raise HTTPException(500, "Error construyendo anexo: %s" % e)
        finally:
            _liberar_memoria()
    return FileResponse(tmp, media_type="application/pdf", filename="Anexo_Financiero_Adapta.pdf")
