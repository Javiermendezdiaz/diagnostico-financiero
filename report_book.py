# -*- coding: utf-8 -*-
"""ITAP — Generador del 'Libro Financiero' (informe PDF narrativo, Tier 2)."""
import json, math, statistics, gc
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, Flowable, KeepTogether)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os as _os
try:
    from svglib.svglib import svg2rlg as _svg2rlg
    from reportlab.graphics import renderPDF as _renderPDF
    _SVG_OK=True
except Exception:
    _SVG_OK=False
_FD=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),"fonts")
try:
    for _n,_f in [("Poppins","Poppins-Regular.ttf"),("Poppins-Bold","Poppins-Bold.ttf"),
                  ("Poppins-Medium","Poppins-Medium.ttf"),("Poppins-Light","Poppins-Light.ttf")]:
        pdfmetrics.registerFont(TTFont(_n,_os.path.join(_FD,_f)))
    pdfmetrics.registerFontFamily("Poppins",normal="Poppins",bold="Poppins-Bold")
    import matplotlib.font_manager as _fm
    for _w in ("Regular","Medium","Bold","Light"):
        _fm.fontManager.addfont(_os.path.join(_FD,"Poppins-%s.ttf"%_w))
    matplotlib.rcParams["font.family"]="Poppins"
    _POPP=True
except Exception:
    _POPP=False
# --- Lora: serif editorial para titulares, cifras y citas (dirección premium) ---
try:
    for _n,_f in [("Lora","Lora-Regular.ttf"),("Lora-SemiBold","Lora-SemiBold.ttf"),
                  ("Lora-Bold","Lora-Bold.ttf"),("Lora-Italic","Lora-Italic.ttf")]:
        pdfmetrics.registerFont(TTFont(_n,_os.path.join(_FD,_f)))
    pdfmetrics.registerFontFamily("Lora",normal="Lora",bold="Lora-Bold",italic="Lora-Italic")
    import matplotlib.font_manager as _fm2
    for _f in ("Lora-Regular.ttf","Lora-SemiBold.ttf","Lora-Bold.ttf","Lora-Italic.ttf"):
        _fm2.fontManager.addfont(_os.path.join(_FD,_f))
    _LORA=True
except Exception:
    _LORA=False
FR=("Poppins" if _POPP else "Helvetica")
FB=("Poppins-Bold" if _POPP else "Helvetica-Bold")
SR=("Lora" if _LORA else FR)              # serif display
SSB=("Lora-SemiBold" if _LORA else FB)    # serif semibold
SB=("Lora-Bold" if _LORA else FB)         # serif bold
SI=("Lora-Italic" if _LORA else FR)       # serif italic
# rutas TTF para matplotlib (páginas-imagen hero)
LORA_TTF={k:_os.path.join(_FD,v) for k,v in {"reg":"Lora-Regular.ttf","sb":"Lora-SemiBold.ttf","bold":"Lora-Bold.ttf","it":"Lora-Italic.ttf"}.items()}
POPP_TTF={k:_os.path.join(_FD,v) for k,v in {"reg":"Poppins-Regular.ttf","med":"Poppins-Medium.ttf","bold":"Poppins-Bold.ttf","light":"Poppins-Light.ttf"}.items()}
try:
    import legado_pages as _legado_pages
    _LEGADO_OK=bool(_LORA)
except Exception:
    _legado_pages=None; _LEGADO_OK=False

INST=json.load(open("itap_instrumento.json",encoding="utf-8"))
CAPAS={c["code"]:c for c in INST["capas"]}
TRANS={"PSIQUE","LIQUIDEZ","VINCULO"}
# --- Piel v2 CLARA (cuerpo banca privada: crema + negro + amarillo Adapta) ---
INK=colors.HexColor("#17181C"); ACC=colors.HexColor("#2C313A"); ACCDK=colors.HexColor("#101113")
GREY=colors.HexColor("#5C6470"); LIGHT=colors.HexColor("#FFFFFF"); LINE=colors.HexColor("#E7E3D8")
AMARILLO=colors.HexColor("#FDD731"); NEGRO=colors.HexColor("#101113")
PAPER=colors.HexColor("#F3EFE2"); BANDC=["#2FAE6E","#C79A2E","#C26D2A","#9A3B2E"]
PAGEBG=colors.HexColor("#FBFAF6")  # fondo claro crema (v2 Adapta)
BLUEACC=colors.HexColor("#C9962B")

# ---------- scoring ----------
def phi(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def pctil(s): return round(100*(1-phi((s-45.0)/17.0)))
def peso(it): return 0.5 if "metacognición" in it.get("dimensiones","") else 1.0
# «Sobrecarga» es un término de estrés; para capas que no lo son, etiqueta por dominio (C1 lo conserva)
_BANDA_FIX={"C2":"Sin rumbo","C3":"Frágil","C4":"A la deriva","C5":"Expuesta","C6":"Inflado","C7":"Expuesta","C8":"Vulnerable","C9":"Con fugas","C10":"Apretada","C11":"Estancada","C12":"Parado"}
def banda(capa,s):
    for i,b in enumerate(capa["bandas"]):
        if b["min"]<=s<=b["max"]:
            _e=b["etiqueta"]
            if _e=="Sobrecarga" and capa.get("code") in _BANDA_FIX: _e=_BANDA_FIX[capa["code"]]
            return i,_e
    return 3,capa["bandas"][-1]["etiqueta"]
def _sal100(s):
    """Salud mostrada 0-100 con SUELO en 5: un '0/100' se lee como error, no como diagnostico.
    Solo afecta al numero que ve el cliente; el scoring y las bandas usan el valor real."""
    try: return max(5, min(95, round(100 - float(s))))
    except Exception: return 50

def score_capa(capa,resp):
    fac={}
    for it in capa["items"]:
        if it["tipo"]!="escala": continue
        if it.get("atencion"): continue
        if it.get("solo_validez"): continue   # gemela de control: NO suma a la media de la capa (solo valida consistencia)
        idx=resp.get(it["id"])
        if idx is None: continue
        fac.setdefault(it["faceta"],[]).append((it["opciones"][idx]["score"],peso(it)))
    facetas={f:round(sum(v*w for v,w in l)/sum(w for _,w in l),1) for f,l in fac.items()}
    return (round(statistics.mean(list(facetas.values())),1) if facetas else 0),facetas
def perfil(resp):
    out={}; tr={t:[] for t in TRANS}
    for code,capa in CAPAS.items():
        cs,fac=score_capa(capa,resp); bi,bl=banda(capa,cs)
        peor=max(fac,key=fac.get) if fac else None
        out[code]={"nombre":capa["nombre"],"score":cs,"banda":bl,"bi":bi,"facetas":fac,
                   "pct":pctil(cs),"peor":capa["facetas"].get(peor,"") if peor else ""}
        for it in capa["items"]:
            if it["tipo"]!="escala": continue
            if it.get("atencion"): continue
            if it.get("solo_validez"): continue   # gemela de control: fuera de las medias transversales (no doble-cuenta)
            idx=resp.get(it["id"])
            if idx is None: continue
            for t in [x for x in it.get("dimensiones","").split("·") if x in TRANS]:
                tr[t].append(it["opciones"][idx]["score"])
    trans={t:(round(statistics.mean(v),1) if v else None) for t,v in tr.items()}
    return out,trans,round(statistics.mean([v["score"] for v in out.values()]),1)
def fi_metrics(d):
    gasto=d.get("gasto_mensual") or 0; ingreso=d.get("ingreso_mensual") or 0
    pat=d.get("patrimonio") or 0; aho=d.get("ahorro_mensual") or 0
    # Capital INVERTIBLE = lo que genera renta del 4% (mercados + liquido). NO la vivienda ni el negocio iliquido.
    invertible=max(0.0, float(d.get("inversiones_liquidas") or 0)+float(d.get("colchon_liquido") or 0))
    fi=gasto*12*25; pct=round(100*invertible/fi,1) if fi else 0.0
    tasa=round(100*aho/ingreso,1) if ingreso else 0.0
    r,pv,m,n=0.05/12,invertible,aho,0
    while pv<fi and n<1200: pv=pv*(1+r)+m; n+=1
    return fi,pct,tasa,(round(n/12,1) if n<1200 else None)

# ---------- contenido narrativo ----------
QMIDE={
 "C1":"tu relación emocional y física con el dinero: el estrés, el sueño, la ansiedad y la culpa.",
 "C2":"cuánto te separa de la libertad financiera real y si tienes un plan que la sostenga.",
 "C3":"cuánto aguantarías un golpe —un paro, un gasto inesperado— sin que tu vida se derrumbe.",
 "C4":"si tu estilo de vida crece con sentido o se infla en silencio y se come tus ingresos.",
 "C5":"si tu patrimonio y tu familia están protegidos legalmente ante lo inesperado.",
 "C6":"cuánto de tu gasto financia una imagen en lugar de tu vida real.",
 "C7":"cuánto dependes de una sola fuente de ingresos: tu mayor riesgo oculto.",
 "C8":"si un shock te hunde o puedes salir reforzado de él.",
 "C9":"si gobiernas el dinero que entra y sale, o se te escapa sin saber a dónde.",
 "C10":"el peso y la salud de tu deuda, y si resistiría una caída de ingresos.",
 "C11":"si tu dinero solo se defiende o además construye: tu capacidad real de hacer crecer lo que ya tienes y de acercar la vida que quieres.",
 "C12":"si canalizas tu ahorro hacia la inversión —la única palanca que hace crecer tu patrimonio de forma exponencial— o lo dejas parado perdiendo valor contra la inflación."}
PASO={
 "C1":"dedica diez minutos a nombrar qué emoción exacta aparece cuando piensas en dinero.",
 "C2":"calcula y anota tu número: gasto anual × 25. Tenerlo a la vista cambia las decisiones.",
 "C3":"fija un objetivo de colchón en meses y automatiza una transferencia hacia él.",
 "C4":"revisa tus tres mayores gastos nuevos del último año y pregúntate si aún merecen la pena.",
 "C5":"escribe qué pasaría con tu dinero si faltaras mañana; las lagunas son tu checklist.",
 "C6":"elige un gasto de imagen y prueba un mes sin él; observa si alguien lo nota.",
 "C7":"identifica una segunda fuente de ingresos posible y da el primer paso esta semana.",
 "C8":"aparta una reserva líquida que solo se usaría para aprovechar una oportunidad.",
 "C9":"monta un presupuesto simple de tres cajas: fijos, variables y ahorro.",
 "C10":"ordena tus deudas por tipo de interés y ataca primero la más cara.",
 "C11":"elige una palanca de crecimiento —una segunda fuente o poner a trabajar tu excedente— y da el primer paso esta semana.",
 "C12":"automatiza tu primera aportación periódica a una cartera diversificada y de bajo coste; el primer movimiento es el que cuenta."}

RIESGO={
 "C1":"Ignorarlo no lo apaga: el estrés financiero sostenido erosiona el sueño, la salud y el juicio. Lo que hoy es incomodidad, mañana es una decisión tomada desde el miedo.",
 "C2":"Sin un número y un plan, los años pasan y el interés compuesto juega en tu contra. Cada año sin rumbo es un año que tendrás que recuperar con el doble de esfuerzo.",
 "C3":"Un solo imprevisto —una baja, una avería, un mes sin ingresos— puede convertir una vida estable en una espiral de deuda. La fragilidad no se nota hasta que llega el golpe.",
 "C4":"La deriva del estilo de vida es silenciosa: cada subida de ingreso que se vuelve gasto te ata un poco más a tu trabajo y aleja tu libertad sin que lo notes.",
 "C5":"Sin blindaje, un imprevisto legal o tu ausencia dejarían a los tuyos en un laberinto de trámites y exposición. Es el riesgo que nadie quiere mirar hasta que es tarde.",
 "C6":"El gasto de estatus es una rueda: cuanto más alimentas la imagen, más necesitas para sostenerla. Es dinero que se va sin construir nada que sea tuyo.",
 "C7":"Depender de una sola fuente es vivir sobre una sola pata: el día que falla, falla todo a la vez. Es el riesgo más subestimado de cualquier economía.",
 "C8":"Sin reservas ni opciones, una crisis solo puede hacerte daño. Quien no puede aprovechar el caos, únicamente lo sufre.",
 "C9":"Sin control del flujo, el dinero entra y sale sin rumbo: se ahorra lo que sobra (casi nada) y los imprevistos siempre pillan por sorpresa.",
 "C10":"La deuda mal gestionada crece en silencio con cada subida de tipos. Lo que hoy pagas con holgura, mañana puede asfixiarte.",
 "C11":"Un patrimonio que solo se defiende se queda quieto mientras la vida que quieres se encarece. Sin una palanca de crecimiento, el esfuerzo de hoy no compra el futuro que imaginas: solo sostiene el presente.",
 "C12":"El dinero parado no se mantiene: la inflación se lo come en silencio. Ahorrar sin invertir es llenar un cubo agujereado — tu esfuerzo se evapora año tras año y el patrimonio nunca despega."}
OPORTUNIDAD={
 "C1":"Trabajar esto te devuelve algo más valioso que dinero: dormir tranquilo y decidir con cabeza, no con ansiedad.",
 "C2":"Tener tu número claro convierte la libertad de un sueño difuso en un objetivo con fecha. Y lo que se mide, se alcanza.",
 "C3":"Un colchón sólido cambia tu relación con el riesgo: puedes decir que no, esperar la buena oportunidad y dormir aunque el mundo tiemble.",
 "C4":"Domar la deriva es la palanca más rápida hacia la libertad: cada euro que no se infla es un euro que trabaja para ti.",
 "C5":"Blindar tu patrimonio es el mayor acto de cuidado hacia los tuyos: les ahorras, en el peor momento, el peor de los problemas.",
 "C6":"Soltar el gasto de imagen libera dinero y cabeza a la vez: gastar en lo que de verdad te importa, no en lo que crees que se espera de ti.",
 "C7":"Diversificar tus ingresos es construir cimientos: cada nueva fuente te hace más libre y más difícil de tumbar.",
 "C8":"Volverte antifrágil hace que las crisis dejen de darte miedo y empiecen a darte oportunidades. Es el salto de la defensa al ataque.",
 "C9":"Gobernar tu flujo es tomar el mando: sabes a dónde va cada euro y decides tú, no las circunstancias.",
 "C10":"Una deuda sana libera flujo y tranquilidad. Pagar lo caro primero es la inversión con mejor rentabilidad garantizada que existe.",
 "C11":"Pasar de defender a construir cambia el juego: cuando el excedente y el patrimonio trabajan por ti, el tiempo deja de ser tu enemigo y se convierte en tu mayor aliado.",
 "C12":"Invertir con constancia convierte el ahorro en patrimonio que crece solo: el interés compuesto trabaja por ti mientras duermes y, a años vista, cambia por completo tu horizonte."}
ACCIONES={
 "C1":[PASO["C1"],"Pon una hora fija a la semana para mirar tus números; fuera de esa hora, no les des vueltas.","Si el malestar es alto, háblalo con alguien de confianza o un profesional: el dinero también es salud."],
 "C2":[PASO["C2"],"Automatiza una transferencia a inversión el día que cobras, antes de gastar.","Fija una fecha objetivo de libertad y revísala una vez al año."],
 "C3":[PASO["C3"],"Calcula tu presupuesto de supervivencia: lo mínimo para vivir un mes.","Identifica una segunda fuente de ingreso que podrías activar en una crisis."],
 "C4":[PASO["C4"],"Cancela hoy una suscripción que no uses; repite el ejercicio cada mes.","Cuando suba tu ingreso, sube primero el ahorro y solo después el gasto."],
 "C5":[PASO["C5"],"Haz o actualiza tu testamento y designa beneficiarios en seguros y cuentas.","Crea un inventario de activos con accesos y compártelo con quien confíes."],
 "C6":[PASO["C6"],"Antes de una compra de estatus, espera 72 horas: la mayor parte del impulso se evapora.","Redirige lo que ahorres de imagen a algo que de verdad te importe."],
 "C7":[PASO["C7"],"Invierte en una habilidad que aumente tu valor fuera de tu empleo actual.","Calcula qué % de tus ingresos depende de una sola fuente y ponte el objetivo de bajarlo."],
 "C8":[PASO["C8"],"Asegúrate de que parte de tu deuda esté a tipo fijo.","Haz una pequeña apuesta de bajo coste y alto potencial cada trimestre."],
 "C9":[PASO["C9"],"Separa tus cuentas: operativa, contingencia e inversión.","Revisa tu flujo una vez al mes, el mismo día, veinte minutos."],
 "C10":[PASO["C10"],"Renegocia o refinancia tu deuda más cara este mes.","Ponle fecha a tu día sin deuda mala y calcula cuánto pagar al mes para llegar."],
 "C11":[PASO["C11"],"Pon a trabajar el excedente y el patrimonio dormido con un plan a años vista, no en cuentas a la vista.","Define tu brecha exacta hacia la vida ideal y elige la palanca —ingresos o eficiencia— que más la acorte."],
 "C12":[PASO["C12"],"Reparte tu cartera por tipos de activo y geografías; que nada dependa de una sola apuesta.","Define tu plan y tu horizonte por escrito, y no lo rompas por miedo cuando los mercados caigan."]}

PRINCIPIO={
 "C1":"La paz financiera no es tener mucho, es no tener miedo.",
 "C2":"Lo que no se mide, no se alcanza. Tu número es tu brújula.",
 "C3":"No se trata de evitar la tormenta, sino de tener un barco que aguante.",
 "C4":"Cada euro que no se infla es un euro que trabaja para tu libertad.",
 "C5":"El verdadero patrimonio es el que sigue protegiendo cuando tú ya no estás.",
 "C6":"Nadie recuerda la marca de tu reloj; recuerdan si estabas tranquilo.",
 "C7":"Una sola fuente de ingresos es una sola forma de quedarte sin nada.",
 "C8":"El fuerte resiste la crisis; el antifrágil la aprovecha.",
 "C9":"El dinero que no controlas, te controla.",
 "C10":"La deuda barata es una herramienta; la cara, una trampa.",
 "C11":"Defender protege lo que tienes; construir es lo único que te acerca a lo que quieres.",
 "C12":"Ahorrar conserva; invertir es lo único que multiplica. El dinero parado, en realidad, encoge."}

REFLEX={
 "C1":"\u00bfCu\u00e1l es el pensamiento sobre dinero que m\u00e1s se repite en tu cabeza, y es realmente cierto?",
 "C2":"Si hoy tuvieras tu n\u00famero, \u00bfqu\u00e9 cambiar\u00edas ma\u00f1ana en tu vida?",
 "C3":"\u00bfCu\u00e1nto aguantar\u00edas sin ingresos antes de entrar en p\u00e1nico, y te parece suficiente?",
 "C4":"\u00bfQu\u00e9 gasto de tu vida actual no exist\u00eda hace tres a\u00f1os y ya das por imprescindible?",
 "C5":"Si faltaras ma\u00f1ana, \u00bfqu\u00e9 es lo primero que se complicar\u00eda para los tuyos?",
 "C6":"\u00bfQu\u00e9 comprar\u00edas distinto si nadie pudiera verlo?",
 "C7":"Si tu fuente principal de ingresos desapareciera hoy, \u00bfcu\u00e1l es tu plan B real?",
 "C8":"\u00bfLa \u00faltima crisis que viviste te hundi\u00f3 o te ense\u00f1\u00f3 algo que hoy usas?",
 "C9":"\u00bfSabr\u00edas decir, ahora mismo, cu\u00e1nto gastaste el mes pasado?",
 "C10":"\u00bfQu\u00e9 deuda llevas arrastrando que, en el fondo, sabes que deber\u00edas atacar ya?",
 "C11":"\u00bfTu dinero est\u00e1 hoy construyendo la vida que quieres, o solo defendiendo la que ya tienes?",
 "C12":"\u00bfTu ahorro est\u00e1 hoy invertido y creciendo, o parado perdiendo valor contra la inflaci\u00f3n?"}

def faceta_lectura(score):
    if score<30: return "base firme"
    if score<51: return "con margen"
    if score<76: return "a vigilar"
    return "punto crítico"
def _sevcol(sc):
    return "#1D6F42" if sc<30 else ("#B8860B" if sc<51 else ("#C2710C" if sc<76 else "#9A3B2E"))
def _vidx(code, n=3):
    return sum(ord(c) for c in (code or "x")) % n
_CONSEJO2={
 "C1":"No es cuestión de aguantar más, sino de ponerle límites al ruido financiero para que tu cabeza descanse.",
 "C2":"No te falta capacidad, te falta un plan con fecha: ponle número y calendario a tu libertad.",
 "C3":"Tu estructura prioriza el consumo presente sobre la resiliencia futura: monta el colchón antes que cualquier inversión.",
 "C4":"El gasto no se controla con fuerza de voluntad, sino con topes automáticos: ponlos y olvídate.",
 "C5":"Aquí el riesgo es de papeles, no de dinero: ordena la protección y dormirás distinto.",
 "C6":"Tu gasto de imagen capitaliza en contra de tu libertad: cada euro en aparentar es un euro que no compra tu independencia. Regla: 72 horas de pausa antes de comprar.",
 "C7":"No dependas de tu voluntad para diversificar: fíjate un objetivo de % por fuente y muévelo.",
 "C8":"La antifragilidad se construye con pequeñas apuestas, no con un gran salto: empieza por una.",
 "C9":"Aquí el problema no es de capacidad, es de sistema: automatiza el destino del dinero el día 1.",
 "C10":"La deuda no se vence con un sacrificio puntual, sino con un plan de amortización que no dependa de ti.",
 "C11":"Tu palanca no necesita esfuerzo extra, necesita una decisión: elige una y actívala este trimestre.",
 "C12":"No te falta dinero para empezar a invertir, te falta arrancar: automatiza una aportación pequeña y constante este mes."}
_CONSEJO3={
 "C1":"Es lo primero a atender: el desgaste con el dinero contamina todas las demás decisiones.",
 "C2":"Cada año a este ritmo aleja tu meta; reordenar el flujo ahora vale más que cualquier rentabilidad.",
 "C3":"Sin colchón estás a un imprevisto de una crisis: es la prioridad cero, por encima de todo.",
 "C4":"La fuga de estilo de vida es el agujero más caro y más fácil de tapar: actúa este mes.",
 "C5":"La protección no espera al imprevisto: lo que no blindes hoy, lo pagan los tuyos mañana.",
 "C6":"El gasto de imagen te está costando libertad medible: recórtalo y redirígelo ya.",
 "C7":"Tu única fuente es tu mayor vulnerabilidad: abrir una segunda es lo más urgente que tienes.",
 "C8":"Eres frágil ante un golpe: convertir esa fragilidad en holgura es la jugada que no admite espera.",
 "C9":"Recupera el mando del flujo antes que nada: sin él, el resto del plan se deshace solo.",
 "C10":"Tu deuda es el frente que más drena: atacar la más cara es tu mejor inversión garantizada.",
 "C11":"Tienes potencia sin usar: activarla ahora es lo que más cambia tu trayectoria.",
 "C12":"Tu ahorro parado pierde valor cada mes: ponerlo a invertir con un plan es lo que más cambia tu patrimonio a años vista."}
def segundo_parrafo(bi, code=""):
    V={0:["Mantén lo que funciona: revísalo de vez en cuando para que no se deteriore sin avisar.",
          "Aquí no hay nada que arreglar, solo que proteger: la fortaleza descuidada se oxida.",
          "Es terreno ganado. Tu único trabajo es no darlo por sentado."],
       1:["Tienes una base buena; un ajuste pequeño y sostenido te lleva al nivel más alto sin grandes sacrificios.",
          "Estás cerca de la zona óptima: pulir este punto es de las mejoras más rentables que puedes hacer.",
          "Con poco esfuerzo bien dirigido, esta área pasa de buena a excelente."]}
    if bi==2: return _CONSEJO2.get(code,"Está pidiendo atención, no rescate: un cambio concreto y medible la endereza en un trimestre.")
    if bi==3: return _CONSEJO3.get(code,"Es un frente abierto: cuanto antes lo cierres, menos te cuesta y deja de drenar al resto.")
    return V[bi][_vidx(code)]


# Cierres ÚNICOS por capa (premium: cero repeticiones entre capítulos)
CIERRE2={
 "C1":"tu cabeza carga con un peso que el dinero no debería darte; descargarla es lo primero.",
 "C2":"tu libertad avanza, pero a un ritmo más lento del que tu esfuerzo merece.",
 "C3":"hoy un golpe te haría tambalear más de lo que tu patrimonio sugiere; ahí está el frente.",
 "C4":"tu estilo de vida se infla un punto cada año sin que lo decidas, y eso sostenido pesa.",
 "C5":"lo que no está blindado hoy es justo lo que más duele el día del imprevisto.",
 "C6":"parte de tu gasto financia una imagen, no tu vida; recuperarlo es dinero y cabeza a la vez.",
 "C7":"depender de una sola fuente es el riesgo que no se ve hasta que falla; conviene moverlo antes.",
 "C8":"ante un shock saldrías a flote, pero raspando; un poco de holgura cambia ese margen.",
 "C9":"tu dinero entra y sale sin que lleves el mando del todo, y ahí se te escapa el control.",
 "C10":"tu deuda aún no aprieta, pero ya te resta aire que podrías usar para construir.",
 "C11":"tu mayor palanca sigue sin activar: cada mes que no la tocas es crecimiento que no llega.",
 "C12":"tu ahorro no se está invirtiendo: cada mes parado es interés compuesto que no llega y poder de compra que pierdes."}
CIERRE3={
 "C1":"es el primer frente: sin calma con el dinero, ninguna otra pieza encaja.",
 "C2":"a este ritmo la libertad no llega; es la prioridad que más mueve tu horizonte.",
 "C3":"estás expuesto: un imprevisto serio hoy te forzaría a decisiones malas y caras.",
 "C4":"la deriva ya te come ingresos; cerrarla es la mejora más rápida que tienes.",
 "C5":"es urgente: lo que no protejas ahora lo paga quien menos debería, el peor día.",
 "C6":"el gasto de aparentar te está costando libertad real; cortarlo libera mucho, y ya.",
 "C7":"tu ingreso cuelga de un hilo; diversificarlo es lo más urgente de todo el cuadro.",
 "C8":"un shock hoy te hundiría; pasar de la fragilidad a la holgura no admite demora.",
 "C9":"sin gobierno del flujo, todo lo demás se desordena solo; empieza por aquí.",
 "C10":"tu deuda drena el resto de tu economía; es el agujero que hay que tapar primero.",
 "C11":"tienes capacidad de sobra sin usar; activarla ahora es lo que más te cambia el cuadro.",
 "C12":"tu dinero está parado mientras la inflación lo erosiona; canalizarlo a inversión es lo más rentable que puedes hacer hoy."}

def interpretar(nombre,s,bl,bi,peor,code=None):
    nl=nombre.lower()
    if bi==0: return (f"En {nl} estás en terreno sólido (salud {_sal100(s)}/100). Es una de tus fortalezas. "
                      f"No la des por garantizada: lo que hoy va bien también se cuida.")
    if bi==1: return (f"En {nl} vas con margen (salud {_sal100(s)}/100). El punto que más pesa ahora es "
                      f"«{peor}»; ahí tienes la mejora más fácil y rentable.")
    if bi==2:
        c=CIERRE2.get(code,"todavía no duele, pero ya te está restando margen sin que lo notes.")
        return (f"{nombre} entra en zona «{bl}» (salud {_sal100(s)}/100), sobre todo en «{peor}»: {c}")
    c=CIERRE3.get(code,"no admite más demora: cada mes que pasa, el agujero se ensancha solo.")
    return (f"{nombre} está en zona crítica (salud {_sal100(s)}/100), en especial en «{peor}»: {c}")

def insights(p,tr,fi):
    o=[]
    if p["C1"]["facetas"].get("B1",0)>=50 and p["C1"]["score"]<35:
        o.append(("Tu cuerpo ya paga el precio","Tu relación global con el dinero parece sana, pero hay señales físicas (sueño, salud). El frente a trabajar es somático, no estructural."))
    if tr["LIQUIDEZ"] is not None and tr["LIQUIDEZ"]>=55 and p["C10"]["score"]>=50:
        o.append(("Mezcla frágil: poca liquidez con deuda tensionada","Es la combinación que convierte un imprevisto en crisis. Tu prioridad nº1 es el colchón, antes que cualquier inversión."))
    if p["C7"]["score"]>=55 and p["C3"]["score"]>=50:
        o.append(("Tu mayor riesgo es perder el ingreso","Dependes de una sola fuente y tu colchón es corto. El peligro no es invertir mal: es quedarte sin entrada de dinero."))
    if p["C2"]["score"]>=50 and fi[2]<12:
        o.append(("La libertad está lejos a este ritmo",f"Tu tasa de ahorro ({fi[2]}%) no sostiene tu meta: el horizonte es de décadas. La palanca está en el flujo de caja, no en la rentabilidad."))
    if p["C6"]["score"]>=50 and p["C4"]["score"]>=50:
        o.append(("Tu estatus compite con tu libertad","La capitalización de tu estatus social y la deriva de estilo de vida (lifestyle creep) compiten directamente con la compra de tu libertad futura. Aquí hay margen rápido y silencioso."))
    if tr["VINCULO"] is not None and tr["VINCULO"]>=50:
        o.append(("El dinero tensa tu vínculo","Hay fricción o falta de transparencia con tu pareja o familia: un multiplicador de todo lo demás. El informe de pareja lo aborda de frente."))
    if not o: o.append(("Un perfil equilibrado","No tienes focos críticos. Tu trabajo es de optimización fina, no de contención: pulir una maquinaria que ya funciona."))
    return o
def plan(p):
    d=[]
    for code,capa in CAPAS.items():
        for f,val in p[code]["facetas"].items():
            if val>=60: d.append((val,code,(capa.get("facetas") or {}).get(f,f)))
    d.sort(reverse=True); return d[:6]

# ---------- radar ----------
def radar_png(p,path):
    SHORT={"C1":"Salud emocional","C2":"Libertad","C3":"Resistencia","C4":"Control del gasto","C5":"Protección","C6":"Gasto con sentido","C7":"Diversificación","C8":"Antifragilidad","C9":"Eficiencia de flujo","C10":"Salud de deuda","C11":"Crecimiento","C12":"Inversión"}
    labels=[SHORT.get(c,c) for c in CAPAS]; vals=[p[c]["score"] for c in CAPAS]
    vsal=[100-x for x in vals]  # el radar se dibuja sobre SALUD (borde/lleno = sano), no sobre tension
    N=len(labels); ang=np.linspace(0,2*np.pi,N,endpoint=False).tolist(); ang+=ang[:1]; v=vsal+vsal[:1]
    m=sum(vals)/len(vals)
    # tono del poligono segun tension global: oro aristocratico -> ambar -> terracota
    fill = "#E8C861" if m<35 else ("#D99A2B" if m<58 else "#B5563C")
    fig,ax=plt.subplots(figsize=(5.8,5.8),subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1); ax.set_ylim(0,100)
    # anillos concentricos finos, sin rejilla dura
    ax.grid(False); ax.spines["polar"].set_visible(False)
    th=np.linspace(0,2*np.pi,240)
    for r in (25,50,75,100):
        ax.plot(th,[r]*len(th),color="#D5D0C0",linewidth=0.8,zorder=1)
    # radios suaves
    for a in ang[:-1]:
        ax.plot([a,a],[0,100],color="#DCD7C7",linewidth=0.7,zorder=1)
    # nucleo saludable
    ax.fill_between(th,70,100,color="#1D6F42",alpha=0.06,zorder=1)
    ax.set_yticks([25,50,75]); ax.set_yticklabels(["25","50","75"],color="#8A8676",size=7.5)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels,size=8,color="#2C313A")
    ax.tick_params(axis='x',pad=9)
    # silueta de referencia tenue (salud 50) para que SIEMPRE haya forma legible, aun en perfiles muy bajos
    ref=[50]*len(ang)
    ax.plot(ang,ref,color="#B8B3A3",linewidth=0.9,linestyle=(0,(4,3)),zorder=2)
    # poligono: doble relleno para profundidad + linea grafito + vertices
    ax.fill(ang,v,color=fill,alpha=0.12,zorder=3)
    ax.fill(ang,v,color=fill,alpha=0.22,zorder=3)
    ax.fill(ang,v,color=fill,alpha=0.46,zorder=4)
    for _lw,_al in [(9.0,0.05),(6.0,0.08),(3.6,0.14)]:
        ax.plot(ang,v,color=fill,linewidth=_lw,alpha=_al,zorder=4,solid_capstyle="round")
    ax.plot(ang,v,color="#17181C",linewidth=2.4,zorder=5,solid_capstyle="round")
    # Vertices coloreados por SALUD de cada eje: verde = fortaleza, rojo = critico.
    # Asi la pagina estrella comunica de un vistazo donde mirar (criticos gritan, fortalezas respiran).
    vcol=[BANDC[0] if hh>=75 else BANDC[1] if hh>=50 else BANDC[2] if hh>=25 else BANDC[3] for hh in vsal]
    ax.scatter(ang[:-1],vsal,s=64,color=vcol,zorder=6,edgecolors="#17181C",linewidths=1.6)
    ax.scatter(ang[:-1],vsal,s=14,color="#FFFFFF",zorder=7)
    plt.tight_layout(); fig.savefig(path,dpi=200,transparent=True); plt.close(fig); gc.collect()

def panel_dashboard(path, salud_disp, banda_lbl, cifra_lib, cobertura, tasa_ahorro, inv, par, ili, ing_act, ing_pas, g_fij, g_var, dormido, fecha):
    from matplotlib.patches import FancyBboxPatch, Rectangle
    BG="#0E1018"; PANEL="#161A24"; GOLD="#E8C861"; AM="#FDD731"; TX="#F4F1E8"; GR="#8A93A6"; GREEN="#2FB36B"; RED="#D8674F"; SLATE="#3A4150"
    def _e(n):
        try: return ("%s €"%format(float(n),",.0f")).replace(",",".")
        except Exception: return "—"
    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.axis("off"); ax.set_xlim(0,100); ax.set_ylim(0,141.6)
    def box(x,y,w,h,fc,r=1.4,ec=None,lw=0):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0,rounding_size=%s"%r,fc=fc,ec=ec or fc,lw=lw,zorder=2))
    def T(x,y,ss,size,c=TX,w="normal",ha="left"):
        ax.text(x,y,ss,fontsize=size,color=c,ha=ha,fontweight=w,family="DejaVu Sans",zorder=5)
    ax.add_patch(Rectangle((0,128),100,13.6,fc="#141A28",zorder=1))
    T(8,134,"ADAPTA",13,GOLD,"bold"); T(24.2,134.2,"FAMILY OFFICE",7,GR)
    ax.plot([8,92],[131.4,131.4],color="#262C3A",lw=1,zorder=3)
    T(8,123,"TU PANEL FINANCIERO",10,GOLD,"bold")
    T(8,116.5,"Tu vida económica, de un vistazo",19,TX,"bold")
    box(8,92,40,20,PANEL,2)
    T(28,108.5,"SALUD PSICOFINANCIERA",7,GR,"bold",ha="center")
    T(28,99,"%.0f"%salud_disp,46,AM,"bold",ha="center")
    T(28,93.6,"/100  ·  %s"%(banda_lbl or ""),8,GR,ha="center")
    cards=[("CIFRA DE LIBERTAD",_e(cifra_lib),GOLD),("COBERTURA ACTUAL","%.0f%%"%cobertura,TX),("TASA DE AHORRO","%.0f%%"%tasa_ahorro,GREEN)]
    cx=51
    for i,(lab,val,col) in enumerate(cards):
        yy=92+(2-i)*6.6; box(cx,yy,41,6.0,PANEL,1.4); T(cx+2.5,yy+3.6,lab,6.6,GR,"bold"); T(cx+38.5,yy+1.9,val,11,col,"bold",ha="right")
    tot=inv+par+ili
    T(8,90,"QUÉ TRABAJA Y QUÉ DUERME",8,GOLD,"bold")
    if tot>0:
        x=8
        for val,col,dark in [(inv,GREEN,True),(par,GOLD,True),(ili,SLATE,False)]:
            w=84*val/tot
            if w>0.5: box(x,83,max(w-0.4,0.6),5.0,col,1.0)
            if w>9: T(x+w/2,85.3,"%.0f%%"%(100*val/tot),9,"#0E1018" if dark else TX,"bold",ha="center")
            x+=w
        trab=100*inv/tot
        T(8,79.6,"●  %.0f%% TRABAJA para ti"%trab,7.5,GREEN,"bold")
        T(46,79.6,"●  %.0f%% DUERME — parado o en ladrillo/negocio"%(100-trab),7.5,GR)
    else:
        T(8,80,"Aún sin patrimonio que medir.",8,GR)
    ing=ing_act+ing_pas; gas=g_fij+g_var; mx=max(ing,gas,1.0)
    T(8,73.5,"DE DÓNDE VIENE Y A DÓNDE VA",8,GOLD,"bold")
    def flujo(y,lab,parts):
        T(8,y+4.4,lab,7,GR,"bold"); x=8
        for v,col in parts:
            w=84*v/mx
            if w>0.4: box(x,y,max(w-0.4,0.6),3.4,col,0.9)
            x+=w
    flujo(67.5,"INGRESOS",[(ing_act,"#5B6472"),(ing_pas,GREEN)])
    flujo(60.5,"GASTOS",[(g_fij,RED),(g_var,GOLD)])
    T(8,57.2,"●  activo   ●  pasivo (te libera)",6.8,GR); T(50,57.2,"●  fijo (te ata)   ●  variable",6.8,GR)
    if dormido and dormido>15000 and cobertura<100:
        box(8,46,84,7.6,"#1C2433",1.6,ec=GOLD,lw=1.2)
        T(11,51.2,"TU PALANCA #1",7,GOLD,"bold")
        T(11,47.8,"Tienes %s dormidos. Moverlos a renta sube tu cobertura del %.0f%% sin ganar un euro más."%(_e(dormido),cobertura),8.2,TX)
    T(8,40,"Las cifras de esta página son el resumen ejecutivo de tu Libro. El detalle, capa a capa, viene a continuación.",7,GR)
    ax.plot([8,92],[6.5,6.5],color="#262C3A",lw=1)
    T(8,4,"DOCUMENTO CONFIDENCIAL · ADAPTA FAMILY OFFICE · %s"%fecha,6.2,GR)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()

class Chip(Flowable):
    def __init__(s,t,c,w=92,h=14): s.t=t; s.c=colors.HexColor(c); s.w=w; s.h=h; Flowable.__init__(s)
    def wrap(s,*a): return (s.w,s.h)
    def draw(s):
        c=s.canv; c.setFillColor(s.c); c.roundRect(0,0,s.w,s.h,3,fill=1,stroke=0)
        c.setFillColor(colors.white); c.setFont(FB,7.5); c.drawCentredString(s.w/2,s.h/2-2.6,s.t)
class Bar(Flowable):
    def __init__(s,val,w=160,h=9): s.v=val; s.w=w; s.h=h; Flowable.__init__(s)
    def wrap(s,*a): return (s.w*mm if s.w<10 else s.w,s.h)
    def draw(s):
        c=s.canv; W=s.w; c.setFillColor(colors.HexColor("#E7E3D8")); c.roundRect(0,0,W,s.h,2,fill=1,stroke=0)
        h=100-s.v  # se dibuja SALUD (alto=bien): barra llena y verde = sano
        col=BANDC[0] if h>=75 else BANDC[1] if h>=50 else BANDC[2] if h>=25 else BANDC[3]
        c.setFillColor(colors.HexColor(col)); c.roundRect(0,0,max(3,W*h/100),s.h,2,fill=1,stroke=0)

class FotoPatrimonio(Flowable):
    """Barra apilada: cuanto del patrimonio esta invertido (trabaja), parado (liquido) e iliquido (ladrillo/negocio)."""
    def __init__(s,inv,par,ili,w=160,h=12):
        s.inv=max(0.0,inv); s.par=max(0.0,par); s.ili=max(0.0,ili); s.w=w; s.h=h; Flowable.__init__(s)
    def wrap(s,*a): return (s.w*mm, s.h*mm)
    def draw(s):
        c=s.canv; W=s.w*mm; H=s.h*mm; tot=s.inv+s.par+s.ili
        c.setFillColor(colors.HexColor("#E7E3D8")); c.roundRect(0,0,W,H,3,fill=1,stroke=0)
        if tot<=0: return
        x=0.0
        for val,col in [(s.inv,"#1D6F42"),(s.par,"#E3B341"),(s.ili,"#9CA3AF")]:
            ww=W*val/tot
            if ww>0.4:
                c.setFillColor(colors.HexColor(col)); c.rect(x,0,ww,H,fill=1,stroke=0)
                if ww>34:   # etiqueta de % dentro del segmento si cabe
                    c.setFillColor(colors.white); c.setFont(FB,8)
                    c.drawCentredString(x+ww/2,H/2-3,"%.0f%%"%(100*val/tot))
                x+=ww

class FlujoEstructura(Flowable):
    """Dos barras comparables: arriba ingresos (activo|pasivo), abajo gastos (fijo|variable). El hueco = ahorro o deficit."""
    def __init__(s,act,pas,fij,var,w=160,h=12):
        s.act=max(0.0,act); s.pas=max(0.0,pas); s.fij=max(0.0,fij); s.var=max(0.0,var); s.w=w; s.h=h; Flowable.__init__(s)
    def wrap(s,*a): return (s.w*mm, s.h*2*mm+9*mm)
    def _seg(s,segs,y,W,maxv,H):
        c=s.canv; c.setFillColor(colors.HexColor("#EFEce3")); c.roundRect(0,y,W,H,2,fill=1,stroke=0)
        x=0.0
        for val,col in segs:
            ww=W*val/maxv if maxv>0 else 0
            if ww>0.4:
                c.setFillColor(colors.HexColor(col)); c.rect(x,y,ww,H,fill=1,stroke=0); x+=ww
    def draw(s):
        c=s.canv; W=s.w*mm; H=s.h*mm; ing=s.act+s.pas; gas=s.fij+s.var; maxv=max(ing,gas,1.0)
        y2=0; y1=H+6   # gastos abajo, ingresos arriba
        c.setFillColor(colors.HexColor("#6B7280")); c.setFont(FB,8.5)
        c.drawString(0,y1+H+2,"INGRESOS")
        c.drawString(0,y2-9.5,"GASTOS")
        s._seg([(s.act,"#6B7280"),(s.pas,"#1D6F42")],y1,W,maxv,H)
        s._seg([(s.fij,"#C65C4E"),(s.var,"#E3B341")],y2,W,maxv,H)

def St(n,**k): k.setdefault("fontName",FR); k.setdefault("textColor",INK); return ParagraphStyle(n,**k)
h_book=St("hb",fontSize=17,leading=21,textColor=ACCDK,fontName=SB,spaceAfter=2)
h_sec=St("hs",fontSize=20,leading=24,textColor=ACCDK,fontName=SB,spaceAfter=8)
h_sub=St("hu",fontSize=10.5,leading=13,textColor=ACC,fontName=FB,spaceBefore=7,spaceAfter=3)
body=St("bd",fontSize=10,leading=15,spaceAfter=7,alignment=TA_JUSTIFY)
small=St("sm",fontSize=8,leading=11,textColor=GREY)
cap_kicker=St("ck",fontSize=8.5,leading=11,textColor=GREY,fontName=FB)

import re as _re
def _limpiar_txt(t):
    """Plancha erratas de picado: espacio tras puntuacion+mayuscula, colapsa dobles espacios,
    quita signos huerfanos. No inventa: solo corrige separaciones y espacios."""
    if not t: return t
    t=_re.sub(r'([.;,:!?])([A-Za-zÁÉÍÓÚÑáéíóúñ])', r'\1 \2', t)
    t=_re.sub(r'\s{2,}', ' ', t)
    return t.strip()

CLIENTE_NOMBRE=""
try:
    from reportlab.pdfgen.canvas import Canvas as _RLCanvas
    class NumberedCanvas(_RLCanvas):
        """Doble pasada: permite imprimir 'NN / TOTAL' porque al guardar ya sabe el total."""
        def __init__(self,*a,**k):
            _RLCanvas.__init__(self,*a,**k); self._saved=[]
        def showPage(self):
            self._saved.append(dict(self.__dict__)); self._startPage()
        def save(self):
            n=len(self._saved)
            for st in self._saved:
                self.__dict__.update(st)
                self.saveState(); self.setFont(FR,7.5); self.setFillColor(GREY)
                if self._pageNumber>1:
                    self.drawRightString(A4[0]-22*mm,12*mm,"%02d / %02d"%(self._pageNumber,n))
                self.restoreState()
                _RLCanvas.showPage(self)
            _RLCanvas.save(self)
except Exception:
    NumberedCanvas=None

from reportlab.platypus import Flowable as _Flowable
class DarkPage(_Flowable):
    """Pagina oscura full-bleed (azul prusia) para contraportada institucional / separadores."""
    def __init__(self, numero="", titulo="", sub="", legal=""):
        _Flowable.__init__(self); self.numero=numero; self.titulo=titulo; self.sub=sub; self.legal=legal; self.w=0; self.h=0
    def wrap(self, aw, ah): self.w=aw; self.h=ah; return aw, ah
    def draw(self):
        c=self.canv; c.saveState()
        c.setFillColor(colors.HexColor("#101113")); c.rect(-22*mm, -20*mm, A4[0], A4[1], fill=1, stroke=0)
        cx=self.w/2.0
        if self.numero:
            c.setFillColor(colors.HexColor("#26262B")); c.setFont(FB,150)
            c.drawCentredString(cx, self.h-150*mm, self.numero)
        c.setFillColor(colors.HexColor("#FDD731")); c.setFont(FB,22)
        c.drawCentredString(cx, self.h/2.0+6*mm, self.titulo or "ADAPTA")
        if self.sub:
            c.setFillColor(colors.HexColor("#E9E4D6")); c.setFont(FR,11)
            c.drawCentredString(cx, self.h/2.0-6*mm, self.sub)
        if self.legal:
            c.setFillColor(colors.HexColor("#8A8F99")); c.setFont(FR,7.5)
            c.drawCentredString(cx, 14*mm, self.legal)
        c.restoreState()

class FullBleedImage(_Flowable):
    """Página-imagen a sangre (cubre toda la hoja A4). Para portada/portadillas/joyas Legado."""
    def __init__(self, path): _Flowable.__init__(self); self.path=path; self.w=0; self.h=0
    def wrap(self, aw, ah): self.w=aw; self.h=ah; return aw, ah
    def draw(self):
        try:
            if _SVG_OK and self.path.lower().endswith(".svg"):
                d=_svg2rlg(self.path)
                if d is not None and d.width and d.height:
                    self.canv.saveState()
                    self.canv.translate(-22*mm,-20*mm)
                    self.canv.scale(A4[0]/d.width, A4[1]/d.height)
                    _renderPDF.draw(d, self.canv, 0, 0)
                    self.canv.restoreState()
                    return
            self.canv.drawImage(self.path, -22*mm, -20*mm, width=A4[0], height=A4[1],
                                preserveAspectRatio=False, mask=None)
        except Exception:
            pass

def deco(cv,doc):
    cv.saveState()
    # Fondo crema v2 (banca privada Adapta)
    cv.setFillColor(PAGEBG); cv.rect(0,0,A4[0],A4[1],fill=1,stroke=0)
    # Cabecera: banda negra con marca Adapta (desde la pagina 2)
    if doc.page>1:
        bh=11*mm
        cv.setFillColor(NEGRO); cv.rect(0,A4[1]-bh,A4[0],bh,fill=1,stroke=0)
        cv.setFillColor(AMARILLO); cv.setFont(FB,9.5); cv.drawString(22*mm,A4[1]-7.4*mm,"ADAPTA")
        cv.setFillColor(colors.HexColor("#E9E4D6")); cv.setFont(FR,7)
        cv.drawString(40*mm,A4[1]-7.1*mm,"FAMILY OFFICE")
        cv.drawRightString(A4[0]-22*mm,A4[1]-7.1*mm,"DIAGNÓSTICO PATRIMONIAL")
    # Pie: nota confidencial (el numero de pagina lo pone NumberedCanvas)
    cv.setStrokeColor(LINE); cv.setLineWidth(0.6); cv.line(22*mm,16*mm,A4[0]-22*mm,16*mm)
    cv.setFillColor(GREY); cv.setFont(FR,7)
    cv.drawString(22*mm,12*mm,"DOCUMENTO CONFIDENCIAL · USO PRIVADO")
    cv.restoreState()

def faceta_table(code, pc):
    facs = CAPAS[code]["facetas"]
    rows=[]
    for f,score in pc["facetas"].items():
        rows.append([Paragraph(facs.get(f,f), small), Bar(score, w=66*mm)])
    if not rows:
        return Spacer(1,1)
    t=Table(rows, colWidths=[84*mm,72*mm])
    t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(0,-1),0),("LEFTPADDING",(1,0),(1,-1),6)]))
    return t

ADAPTA={
 "C1":("Una conversaci\u00f3n, sin protocolo","Cuando el dinero pesa por dentro, el primer paso no es un producto: es que alguien te escuche y ordene el cuadro completo.","https://www.adaptafamilyoffice.com/informe"),
 "C2":("Gesti\u00f3n integral del patrimonio","Dise\u00f1amos tu camino a la libertad financiera dentro del cuadro completo, a\u00f1o tras a\u00f1o, sin productos propios ni conflictos de inter\u00e9s.","https://www.adaptafamilyoffice.com/casos/banca-privada"),
 "C3":("Plan de resiliencia patrimonial","Estructuramos tu colch\u00f3n y tus coberturas para que un imprevisto no se convierta en una crisis.","https://www.adaptafamilyoffice.com/servicios"),
 "C4":("Orden y eficiencia financiera","Ponemos tu estilo de vida y tu ahorro en su sitio, para que cada euro trabaje hacia tu objetivo.","https://www.adaptafamilyoffice.com/servicios"),
 "C5":("Herencia y blindaje legal","Sucesiones, protecci\u00f3n patrimonial y decisiones que se toman una sola vez \u2014 con criterio, antes de que sea tarde.","https://www.adaptafamilyoffice.com/casos/herencia"),
 "C6":("Una conversaci\u00f3n honesta sobre tu gasto","Te decimos la verdad, aunque duela: d\u00f3nde tu dinero financia una imagen en lugar de tu vida.","https://www.adaptafamilyoffice.com/informe"),
 "C7":("Diversificaci\u00f3n y banca privada","Reducimos tu dependencia de una sola fuente y estructuramos tu patrimonio para que no se sostenga sobre una sola pata.","https://www.adaptafamilyoffice.com/casos/banca-privada"),
 "C8":("Estrategia patrimonial antifr\u00e1gil","Estructuramos tu patrimonio para que las crisis dejen de ser una amenaza y empiecen a ser una oportunidad.","https://www.adaptafamilyoffice.com/casos/banca-privada"),
 "C9":("Control de tu flujo de caja","Montamos contigo el sistema para que sepas a d\u00f3nde va cada euro y decidas t\u00fa, no las circunstancias.","https://www.adaptafamilyoffice.com/servicios"),
 "C10":("Planificaci\u00f3n y reestructuraci\u00f3n de hipoteca","Renegociaci\u00f3n, subrogaci\u00f3n y las mejores condiciones que tu perfil permite \u2014 para que la deuda deje de pesar.","https://www.adaptafamilyoffice.com/casos/planificacion-hipoteca"),
 "C11":("Estrategia de crecimiento patrimonial","Ponemos a trabajar tu excedente y tu patrimonio con un plan a a\u00f1os vista \u2014 para que tu dinero deje de defenderse y empiece a construir la vida que quieres.","https://www.adaptafamilyoffice.com/casos/banca-privada"),
 "C12":("Estrategia de inversión","Diseñamos y gestionamos una cartera a tu medida —diversificada, de bajo coste y alineada con tu horizonte— para que tu ahorro deje de estar parado y empiece a componer a tu favor.","https://www.adaptafamilyoffice.com/casos/gestion-patrimonio")}

def seccion_adapta(p, datos=None):
    out=[PageBreak(), Paragraph("El siguiente paso con Adapta",h_sec),
         Paragraph("Este libro es un mapa. <b>Adapta Family Office</b> es quien lo recorre contigo: 25 a\u00f1os "
                   "cuidando patrimonios familiares, con visi\u00f3n integral y sin productos propios ni conflictos de inter\u00e9s.",body),
         Paragraph("Por lo que dice tu diagn\u00f3stico, esto es lo que m\u00e1s te conviene ahora mismo:",body)]
    orden=sorted(CAPAS,key=lambda c:p[c]["score"],reverse=True)
    # Upsell por PATRIMONIO REAL: nunca ofrecer banca privada / inversion sofisticada a
    # quien primero debe sanear deuda y montar colchon. Con poco patrimonio, la base va antes
    # que crecer; eso es criterio, y mantiene la credibilidad de todo el informe.
    _d=datos or {}
    try: _pat=float(_d.get("patrimonio") or 0)
    except Exception: _pat=0.0
    _BANCA_PRIVADA={"C7","C8","C11","C12"}  # diversificacion / antifragil / crecimiento / inversion
    if _pat < 100000:
        orden=[c for c in orden if c not in _BANCA_PRIVADA] or orden
    peores=orden[:2]
    for code in peores:
        ti,de,url=ADAPTA[code]
        out.append(Paragraph(f"<font color='#0284C7'><b>&#9656; {ti}</b></font>",St("ad1",fontSize=11,leading=14,spaceBefore=6,spaceAfter=2)))
        out.append(Paragraph(de,St("ad2",fontSize=10,leading=14,leftIndent=8,spaceAfter=2)))
        out.append(Paragraph(f"<a href='{url}'><font color='#1A1A17'>Ver c\u00f3mo lo trabajamos &#8594;</font></a>",St("ad3",fontSize=9.5,leading=13,leftIndent=8,spaceAfter=8)))
    # Art. 5.3 de la Constituci\u00f3n: UNA recomendaci\u00f3n honesta que NO nos beneficia. La credibilidad
    # de todo lo que s\u00ed recomendamos se compra siendo capaces de decir "esto hazlo t\u00fa solo, gratis".
    try: _deu=float(_d.get("deuda_total") or 0)
    except Exception: _deu=0.0
    if _deu>0 and _pat<100000:
        _solo=("Amortizar tu deuda m\u00e1s cara y mantener tu fondo de emergencia <b>no requiere contratarnos</b>: "
               "es gratis, lo puedes empezar hoy mismo, y es exactamente lo primero que te recomendar\u00edamos. "
               "Solo cuando esa base est\u00e9 firme tiene sentido hablar del resto.")
    else:
        _solo=("Automatizar una transferencia a tu ahorro el mismo d\u00eda que cobras <b>no requiere contratarnos</b>: "
               "es gratis y es el h\u00e1bito que m\u00e1s mueve la aguja. Empieza por ah\u00ed hoy \u2014 el resto puede esperar.")
    out+=[Spacer(1,3*mm),
          _box([Paragraph("Esto puedes hacerlo t\u00fa solo",St("hsolo_h",fontSize=10.5,leading=14,textColor=colors.HexColor("#1D6F42"),fontName=FB)),
                Paragraph(_solo,St("hsolo",fontSize=10,leading=14,spaceBefore=2))],
               "#EEF7F0","#1D6F42",ancho=160*mm)]
    out+=[Spacer(1,4*mm),
          Paragraph("Por d\u00f3nde empezamos",h_sub),
          Spacer(1,2.5*mm),
          Paragraph("Tienes el mapa. El siguiente paso es una <b>sesi\u00f3n estrat\u00e9gica</b> para pasar del diagn\u00f3stico a la ejecuci\u00f3n: "
                    "te escuchamos primero, te proponemos despu\u00e9s. Sin compromiso y sin llamadas de presi\u00f3n \u2014 como debe ser.",
                    St("cta",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=10,spaceBefore=0)),
          Spacer(1,2*mm),
          Paragraph("<b>Reserva tu conversaci\u00f3n:</b> <a href='https://www.adaptafamilyoffice.com/informe'><font color='#0284C7'>adaptafamilyoffice.com</font></a>  &#183;  "
                    "<b>WhatsApp:</b> <a href='https://wa.me/34683343531'><font color='#0284C7'>+34 683 34 35 31</font></a>  &#183;  info@adaptafamilyoffice.com",
                    St("cta2",fontSize=9.5,leading=14))]
    try:
        cierre_cta("_cierre_ind.png", "TU SIGUIENTE\nPASO",
                   "Este libro es tu mapa. Adapta Family Office es quien lo recorre contigo, con visión integral de tu patrimonio.",
                   ["Una sesión estratégica para pasar del diagnóstico a la ejecución.",
                    "Sin productos propios ni conflictos de interés: solo tu mejor decisión.",
                    "Te escuchamos primero, te proponemos después. Sin llamadas de presión."],
                   "adaptafamilyoffice.com    ·    WhatsApp +34 683 34 35 31    ·    info@adaptafamilyoffice.com")
        out += [PageBreak(), FullBleedImage("_cierre_ind.png")]
    except Exception:
        pass
    return out

def coherencia(salud, fi, datos):
    tasa=fi[2]; fipct=fi[1]; pat=datos.get("patrimonio",0)
    pat_txt=("%s"%format(pat,",.0f")).replace(",",".")
    fin_fuerte=(tasa>=20) or (fipct>=30) or (pat>=80000)
    fin_debil=(tasa<8) and (pat<15000)
    if salud>=50 and fin_fuerte:
        return ("Tu mayor hallazgo: una distorsi\u00f3n de seguridad",
                f"Tus n\u00fameros objetivos son fuertes \u2014ahorras alrededor de un {tasa:.0f}% y manejas un patrimonio de "
                f"{pat_txt} \u20ac\u2014, pero tu mente opera en estado de alerta. Tu problema de fondo no es el dinero: es c\u00f3mo "
                f"lo sientes. El trabajo aqu\u00ed no es ganar ni ahorrar m\u00e1s, sino aprender a habitar la seguridad que ya has construido.")
    if salud<30 and fin_debil:
        return ("Tu mayor hallazgo: una calma por confirmar",
                "Vives el dinero con serenidad, y eso es un activo. Pero tus n\u00fameros a\u00fan no la respaldan del todo: el colch\u00f3n y "
                "el ritmo de ahorro son ajustados. Esa tranquilidad ayuda a construir sin ag\u00f3bio, siempre que no te frene a mirar de frente "
                "el trabajo que todav\u00eda tienes por delante.")
    return None

# ---------- Arquetipo del dinero ----------
ARQ_META = {
 "SEG": {"nombre": "El Guardi\u00e1n", "lema": "El dinero es protecci\u00f3n.",
         "color": "#1D6F42",
         "desc": "Para ti el dinero es, antes que nada, un escudo. Priorizas el col"
                 "ch\u00f3n, te incomoda el riesgo y duermes mejor sabiendo que hay margen. "
                 "Tu fortaleza es la prudencia; tu punto ciego, dejar dinero parado por miedo "
                 "a moverlo.",
         "luz": "Aportas estabilidad y red de seguridad a cualquier decisi\u00f3n.",
         "sombra": "Puedes confundir prudencia con par\u00e1lisis y perder oportunidades por exceso de cautela."},
 "LIB": {"nombre": "El Explorador", "lema": "El dinero es libertad.",
         "color": "#0284C7",
         "desc": "El dinero, para ti, compra lo \u00fanico que no se recupera: tiempo y opciones. "
                 "Lo quieres para decidir c\u00f3mo vives, no para acumular. Tu fortaleza es la "
                 "claridad de prop\u00f3sito; tu punto ciego, infravalorar la seguridad que hace "
                 "posible esa libertad.",
         "luz": "Mantienes el foco en lo que de verdad importa: vivir a tu manera.",
         "sombra": "Puedes despreciar la planificaci\u00f3n y quedarte sin la base que sostiene la libertad."},
 "EST": {"nombre": "El Vividor", "lema": "El dinero es para vivir bien.",
         "color": "#B45309",
         "desc": "Crees que el dinero existe para disfrutarse, y vives el presente sin culpa. "
                 "Tu fortaleza es saber gozar lo ganado; tu punto ciego, que el nivel de vida "
                 "tiende a comerse el futuro si nadie le pone freno.",
         "luz": "Le das sentido y disfrute al dinero hoy, no s\u00f3lo en una hoja de c\u00e1lculo.",
         "sombra": "El gasto de estilo de vida puede asfixiar el ahorro sin que lo notes."},
 "MUL": {"nombre": "El Constructor", "lema": "El dinero es una herramienta.",
         "color": "#7C3AED",
         "desc": "Ves el dinero como materia prima para construir y multiplicar. Te sientes "
                 "c\u00f3modo con el riesgo calculado y piensas en sistemas, no en sueldos. Tu "
                 "fortaleza es la mentalidad de crecimiento; tu punto ciego, subestimar el coste "
                 "emocional que el riesgo tiene para quien te rodea.",
         "luz": "Conviertes recursos en m\u00e1s recursos: piensas a largo plazo.",
         "sombra": "Puedes asumir m\u00e1s riesgo del que tu entorno tolera y generar tensi\u00f3n."},
}
_ARQ_FALLBACK = ["SEG","LIB","EST","MUL"]
def tarjeta_arquetipo(arq_code, out_path, sexo=None):
    """Tarjeta social 1080x1080 PREMIUM (Pillow): degradado + cristal + medallon gendered +
    Poppins + boton CTA. Solo identidad: arquetipo + lema + link. Sin cifras ni nombre.
    Carga las fuentes Poppins bundleadas en fonts/. Degradado seguro: out_path o None."""
    try:
        import os, numpy as _np
        from PIL import Image as _I, ImageDraw as _D, ImageFont as _Fnt, ImageFilter as _Flt
        meta = ARQ_META.get(arq_code)
        if not meta:
            return None
        _FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        def _F(w, s): return _Fnt.truetype(os.path.join(_FD, "Poppins-%s.ttf" % w), s)
        W = 1080
        def _hx(c): c = c.lstrip("#"); return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
        def _lp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
        acc = _hx(meta.get("color") or "#FDD731")
        nombre = meta.get("nombre", ""); lema = meta.get("lema", "")
        # fondo: degradado grafito + glow de acento desde arriba
        arr = _np.zeros((W, W, 3), _np.uint8)
        top, bot = _hx("#0E1016"), _hx("#0A0B12")
        for y in range(W): arr[y, :] = _lp(top, bot, y / W)
        img = _I.fromarray(arr, "RGB").convert("RGBA")
        gl = _I.new("RGBA", (W, W), (0, 0, 0, 0)); dg = _D.Draw(gl)
        r = 560; gx, gy = W * 0.5, 110
        dg.ellipse([gx - r, gy - r, gx + r, gy + r], fill=acc + (70,))
        img = _I.alpha_composite(img, gl.filter(_Flt.GaussianBlur(190)))
        def _rr(d, b, rad, fill=None, outline=None, width=1): d.rounded_rectangle(b, radius=rad, fill=fill, outline=outline, width=width)
        def _sp(d, xy, text, font, fill, sp):
            ws = [d.textlength(ch, font=font) + sp for ch in text]; tot = sum(ws) - sp; x = xy[0] - tot / 2
            for ch, wd in zip(text, ws): d.text((x, xy[1]), ch, font=font, fill=fill, anchor="lm"); x += wd
        cx = W // 2; M = 58; panel = [M, M, W - M, W - M]
        ov = _I.new("RGBA", (W, W), (0, 0, 0, 0)); d = _D.Draw(ov)
        _rr(d, panel, 40, fill=(255, 255, 255, 10)); _rr(d, panel, 40, outline=(255, 255, 255, 40), width=2)
        d.line([M + 90, M + 118, W - M - 90, M + 118], fill=acc + (120,), width=2)
        img = _I.alpha_composite(img, ov); d = _D.Draw(img)
        _sp(d, (cx, M + 70), "ADAPTA   \u00b7   FAMILY OFFICE", _F("Light", 27), (214, 219, 228, 255), 7)
        # medallon gendered
        mcy = 346; R = 118; woman = "mujer" in (sexo or "").lower()
        md = _I.new("RGBA", (W, W), (0, 0, 0, 0)); dm = _D.Draw(md)
        dm.ellipse([cx - R, mcy - R, cx + R, mcy + R], fill=(255, 255, 255, 12))
        sl = _I.new("RGBA", (W, W), (0, 0, 0, 0)); ds = _D.Draw(sl)
        scx, scy, sr = cx, mcy + R * 0.06, R * 0.92
        if woman:
            ds.ellipse([scx - sr * 0.44, scy - sr * 0.34, scx + sr * 0.44, scy + sr * 0.40], fill=acc + (255,))
            sh, hr = sr * 0.66, sr * 0.27
        else:
            sh, hr = sr * 0.78, sr * 0.29
        ds.ellipse([scx - sh, scy + sr * 0.18, scx + sh, scy + sr * 1.5], fill=acc + (255,))
        ds.ellipse([scx - hr, scy - sr * 0.38, scx + hr, scy - sr * 0.38 + 2 * hr], fill=acc + (255,))
        mk = _I.new("L", (W, W), 0); _D.Draw(mk).ellipse([cx - R, mcy - R, cx + R, mcy + R], fill=255)
        md.paste(sl, (0, 0), _I.composite(sl.split()[3], _I.new("L", (W, W), 0), mk))
        dm.ellipse([cx - R, mcy - R, cx + R, mcy + R], outline=acc + (255,), width=5)
        img = _I.alpha_composite(img, md); d = _D.Draw(img)
        _sp(d, (cx, 538), "TU ARQUETIPO DEL DINERO", _F("Medium", 25), acc + (255,), 5)
        d.text((cx, 610), nombre, font=_F("Bold", 92), fill=(245, 246, 250, 255), anchor="mm")
        d.text((cx, 688), lema, font=_F("Light", 34), fill=(180, 188, 201, 255), anchor="mm")
        bw, bh = 560, 92; bx = cx - bw // 2; by = 812
        bd = _I.new("RGBA", (W, W), (0, 0, 0, 0)); db = _D.Draw(bd)
        _rr(db, [bx, by, bx + bw, by + bh], 46, fill=acc + (255,))
        img = _I.alpha_composite(img, bd); d = _D.Draw(img)
        txt = "Haz el test gratis"; tw = d.textlength(txt, font=_F("Medium", 34))
        d.text((cx - 22, by + bh // 2), txt, font=_F("Medium", 34), fill=(255, 255, 255, 255), anchor="mm")
        axp = cx - 22 + tw / 2 + 22; ayp = by + bh // 2
        d.polygon([(axp, ayp - 11), (axp, ayp + 11), (axp + 18, ayp)], fill=(255, 255, 255, 255))
        d.text((cx, 946), "diagnostico.adaptafamilyoffice.com", font=_F("Medium", 27), fill=(214, 219, 228, 255), anchor="mm")
        img.convert("RGB").save(out_path, quality=95)
        return out_path
    except Exception:
        return None


def tarjeta_arquetipo16(out_path, sexo, nombre, lema, color, traits, code=""):
    """Tarjeta social 1080x1080 PREMIUM del arquetipo de 16: degradado navy + bisel dorado +
    moneda metalica + Poppins + boton. Muestra NOMBRE + los 4 rasgos en palabras (sin acronimo).
    Carga Poppins de fonts/. Degradado seguro: out_path o None."""
    try:
        import os, numpy as _np
        from PIL import Image as _I, ImageDraw as _D, ImageFont as _Fn, ImageFilter as _Fl
        FD=os.path.join(os.path.dirname(os.path.abspath(__file__)),"fonts")
        def _F(w,s): return _Fn.truetype(os.path.join(FD,"Poppins-%s.ttf"%w),s)
        W=1080
        def _hx(c): c=c.lstrip("#"); return tuple(int(c[i:i+2],16) for i in (0,2,4))
        GOLD=_hx("#C9A86A"); GOLD_HI=_hx("#E7D9AF"); GOLD_LO=_hx("#8C7038"); SILVER=_hx("#C7CCD6")
        acc=_hx(color or "#7C3AED"); acc_lt=tuple(min(255,int(c*1.45+40)) for c in acc)
        yy,xx=_np.mgrid[0:W,0:W].astype(_np.float32); t=(xx+yy)/(2*W)
        c1,c2,c3=_hx("#0C1322"),_hx("#0A0F1C"),_hx("#06080F"); base=_np.zeros((W,W,3),_np.float32)
        for i in range(3):
            a=_np.clip(t*2,0,1); b=_np.clip(t*2-1,0,1); base[...,i]=(c1[i]+(c2[i]-c1[i])*a)+(c3[i]-c2[i])*b
        gd=_np.sqrt((xx-W*0.5)**2+(yy-90)**2)/620.0
        arr=_np.clip(base+_np.clip(1-gd,0,1)[...,None]*_np.array(acc,_np.float32)*0.28,0,255)
        arr=_np.clip(arr+_np.random.normal(0,3.2,(W,W,1)),0,255).astype(_np.uint8)
        img=_I.fromarray(arr,"RGB").convert("RGBA")
        def rr(d,b,rad,**k): d.rounded_rectangle(b,radius=rad,**k)
        def sp(d,xy,tx,f,fill,s):
            ws=[d.textlength(c,font=f)+s for c in tx]; x=xy[0]-(sum(ws)-s)/2
            for c,wd in zip(tx,ws): d.text((x,xy[1]),c,font=f,fill=fill,anchor="lm"); x+=wd
        cx=W//2; M=56; panel=[M,M,W-M,W-M]
        ov=_I.new("RGBA",(W,W),(0,0,0,0)); d=_D.Draw(ov)
        rr(d,panel,42,fill=(255,255,255,9)); rr(d,[M+2,M+2,W-M-2,W-M-2],40,outline=(255,255,255,26),width=1)
        rr(d,panel,42,outline=GOLD+(150,),width=2); rr(d,[M-1,M-1,W-M+1,W-M+1],43,outline=GOLD_HI+(60,),width=1)
        img=_I.alpha_composite(img,ov); d=_D.Draw(img)
        sp(d,(cx,M+60),"ADAPTA   \u00b7   FAMILY OFFICE",_F("Light",26),GOLD_HI+(255,),9)
        d.line([M+95,M+108,W-M-95,M+108],fill=GOLD+(120,),width=2)
        mcy=326; R=112
        yy,xx=_np.mgrid[0:W,0:W].astype(_np.float32); dist=_np.sqrt((xx-cx)**2+(yy-mcy)**2)
        ang=((xx-cx)*-0.5+(yy-mcy)*-0.6)/R; shade=_np.clip(0.5+ang*0.5,0,1)
        flt=_np.array(tuple(min(255,int(c*0.55+70)) for c in acc),_np.float32); fdk=_np.array(tuple(int(c*0.22+14) for c in acc),_np.float32)
        face=(fdk+(flt-fdk)*shade[...,None]); coin=_np.zeros((W,W,4),_np.uint8); ins=dist<=R
        for i in range(3): coin[...,i]=_np.where(ins,face[...,i],0).astype(_np.uint8)
        coin[...,3]=_np.where(ins,255,0).astype(_np.uint8); coinI=_I.fromarray(coin,"RGBA"); cd=_D.Draw(coinI)
        for rr_,col,wd in [(R,GOLD,4),(R-11,GOLD_LO,1),(R-18,acc,2)]: cd.ellipse([cx-rr_,mcy-rr_,cx+rr_,mcy+rr_],outline=col+(255,),width=wd)
        # icono de oficio/concepto por arquetipo (16), grabado en oro con relieve
        _ct=(11,13,20,255)
        def candado(dd,x,y,s,c): dd.arc([x-s*0.55,y-s*1.1,x+s*0.55,y-s*0.1],180,360,fill=c,width=int(s*0.22)); dd.rounded_rectangle([x-s*0.8,y-s*0.35,x+s*0.8,y+s*0.95],radius=s*0.18,fill=c)
        def casa(dd,x,y,s,c): dd.polygon([(x-s,y-s*0.05),(x,y-s),(x+s,y-s*0.05)],fill=c); dd.rectangle([x-s*0.72,y-s*0.05,x+s*0.72,y+s*0.95],fill=c)
        def ancla(dd,x,y,s,c):
            w=int(s*0.2); dd.ellipse([x-s*0.28,y-s*1.05,x+s*0.28,y-s*0.5],outline=c,width=w); dd.line([(x,y-s*0.7),(x,y+s*0.9)],fill=c,width=w)
            dd.line([(x-s*0.6,y-s*0.15),(x+s*0.6,y-s*0.15)],fill=c,width=w); dd.arc([x-s*0.85,y-s*0.1,x+s*0.85,y+s*1.15],20,160,fill=c,width=w)
        def copa(dd,x,y,s,c): dd.polygon([(x-s*0.7,y-s*0.9),(x+s*0.7,y-s*0.9),(x,y+s*0.05)],fill=c); dd.line([(x,y),(x,y+s*0.85)],fill=c,width=int(s*0.18)); dd.line([(x-s*0.55,y+s*0.9),(x+s*0.55,y+s*0.9)],fill=c,width=int(s*0.2))
        def torre(dd,x,y,s,c):
            dd.rectangle([x-s*0.65,y-s*0.45,x+s*0.65,y+s*0.95],fill=c)
            for dx in (-s*0.5,0,s*0.5): dd.rectangle([x+dx-s*0.16,y-s*0.95,x+dx+s*0.16,y-s*0.45],fill=c)
        def arbol(dd,x,y,s,c): dd.ellipse([x-s*0.85,y-s*1.05,x+s*0.85,y+s*0.35],fill=c); dd.rectangle([x-s*0.18,y+s*0.2,x+s*0.18,y+s*1.0],fill=c)
        def monedas(dd,x,y,s,c):
            for yy in (y+s*0.7,y+s*0.15,y-s*0.4): dd.ellipse([x-s*0.8,yy-s*0.22,x+s*0.8,yy+s*0.22],outline=c,width=int(s*0.16))
        def escudocor(dd,x,y,s,c):
            dd.polygon([(x-s,y-s*0.9),(x+s,y-s*0.9),(x+s,y+s*0.1),(x,y+s),(x-s,y+s*0.1)],outline=c,width=int(s*0.16)); r=s*0.3
            dd.pieslice([x-r*1.6,y-s*0.55,x,y-s*0.55+r*1.6],0,180,fill=c); dd.pieslice([x,y-s*0.55,x+r*1.6,y-s*0.55+r*1.6],0,180,fill=c); dd.polygon([(x-r*1.55,y-s*0.2),(x+r*1.55,y-s*0.2),(x,y+s*0.35)],fill=c)
        def diana(dd,x,y,s,c):
            for r,w in [(s,int(s*0.16)),(s*0.6,int(s*0.14))]: dd.ellipse([x-r,y-r,x+r,y+r],outline=c,width=w)
            dd.ellipse([x-s*0.2,y-s*0.2,x+s*0.2,y+s*0.2],fill=c)
        def cohete(dd,x,y,s,c):
            dd.polygon([(x-s*0.4,y+s*0.5),(x-s*0.4,y-s*0.4),(x,y-s),(x+s*0.4,y-s*0.4),(x+s*0.4,y+s*0.5)],fill=c)
            dd.polygon([(x-s*0.4,y+s*0.1),(x-s*0.8,y+s*0.7),(x-s*0.4,y+s*0.5)],fill=c); dd.polygon([(x+s*0.4,y+s*0.1),(x+s*0.8,y+s*0.7),(x+s*0.4,y+s*0.5)],fill=c); dd.polygon([(x-s*0.22,y+s*0.5),(x+s*0.22,y+s*0.5),(x,y+s*1.0)],fill=c)
        def brujula(dd,x,y,s,c): dd.ellipse([x-s,y-s,x+s,y+s],outline=c,width=int(s*0.14)); dd.polygon([(x,y-s*0.6),(x+s*0.25,y),(x,y+s*0.6),(x-s*0.25,y)],fill=c)
        def iman(dd,x,y,s,c):
            w=int(s*0.34); dd.arc([x-s*0.8,y-s*0.95,x+s*0.8,y+s*0.85],180,360,fill=c,width=w)
            dd.line([(x-s*0.8+w/2,y-s*0.05),(x-s*0.8+w/2,y+s*0.9)],fill=c,width=w); dd.line([(x+s*0.8-w/2,y-s*0.05),(x+s*0.8-w/2,y+s*0.9)],fill=c,width=w)
            dd.rectangle([x-s*0.97,y+s*0.7,x-s*0.63,y+s*1.0],fill=c); dd.rectangle([x+s*0.63,y+s*0.7,x+s*0.97,y+s*1.0],fill=c)
        def compas(dd,x,y,s,c):
            w=int(s*0.18); dd.line([(x,y-s*0.8),(x-s*0.6,y+s*0.9)],fill=c,width=w); dd.line([(x,y-s*0.8),(x+s*0.6,y+s*0.9)],fill=c,width=w); dd.ellipse([x-s*0.18,y-s*1.0,x+s*0.18,y-s*0.64],fill=c)
        def diamante(dd,x,y,s,c):
            dd.polygon([(x-s*0.9,y-s*0.45),(x+s*0.9,y-s*0.45),(x,y+s)],fill=c); dd.polygon([(x-s*0.9,y-s*0.45),(x-s*0.45,y-s*0.85),(x+s*0.45,y-s*0.85),(x+s*0.9,y-s*0.45)],fill=c); dd.line([(x-s*0.45,y-s*0.85),(x-s*0.2,y-s*0.45)],fill=_ct,width=2)
        def bandera(dd,x,y,s,c): w=int(s*0.16); dd.line([(x-s*0.5,y-s*0.95),(x-s*0.5,y+s*1.0)],fill=c,width=w); dd.polygon([(x-s*0.5,y-s*0.95),(x+s*0.85,y-s*0.55),(x-s*0.5,y-s*0.15)],fill=c)
        def ojo(dd,x,y,s,c):
            dd.pieslice([x-s,y-s*0.85,x+s,y+s*0.85],180,360,fill=c); dd.pieslice([x-s,y-s*0.85,x+s,y+s*0.85],0,180,fill=c); dd.ellipse([x-s*0.95,y-s*0.62,x+s*0.95,y+s*0.62],fill=_ct); dd.ellipse([x-s*0.34,y-s*0.34,x+s*0.34,y+s*0.34],fill=c)
        _IC={"SPMO":candado,"SPMT":casa,"SPIO":ancla,"SPIT":copa,"SLMO":torre,"SLMT":arbol,"SLIO":monedas,"SLIT":escudocor,
             "APMO":diana,"APMT":cohete,"APIO":brujula,"APIT":iman,"ALMO":compas,"ALMT":diamante,"ALIO":bandera,"ALIT":ojo}
        _ic=_IC.get(code or "", torre); _s=R*0.46
        _ic(cd, cx+3, mcy+4, _s, (0,0,0,150))
        _ic(cd, cx, mcy, _s, GOLD_HI+(255,))
        mk=_I.new("L",(W,W),0); _D.Draw(mk).ellipse([cx-R,mcy-R,cx+R,mcy+R],fill=255)
        img.paste(coinI,(0,0),_I.composite(coinI.split()[3],_I.new("L",(W,W),0),mk)); d=_D.Draw(img)
        sp(d,(cx,494),"TU ARQUETIPO DEL DINERO",_F("Medium",23),GOLD_HI+(255,),5)
        d.text((cx,556),nombre,font=_F("Bold",78),fill=(247,248,251,255),anchor="mm")
        sp(d,(cx,624),(traits or "").upper(),_F("Medium",22),GOLD+(255,),3)
        d.text((cx,682),lema,font=_F("Light",32),fill=SILVER+(255,),anchor="mm")
        d.text((cx,742),"Comp\u00e1rtelo con quienes m\u00e1s te importan",font=_F("Light",25),fill=GOLD_HI+(225,),anchor="mm")
        bw,bh=560,90; bx=cx-bw//2; by=802
        shd=_I.new("RGBA",(W,W),(0,0,0,0)); _D.Draw(shd).rounded_rectangle([bx,by+10,bx+bw,by+bh+10],radius=45,fill=(0,0,0,120))
        img=_I.alpha_composite(img,shd.filter(_Fl.GaussianBlur(14)))
        bg=_np.zeros((bh,bw,3),_np.float32)
        for x in range(bw): tt=x/bw; bg[:,x]=_np.array(acc_lt)*(1-tt)+_np.array(acc)*tt
        bm=_I.new("L",(bw,bh),0); _D.Draw(bm).rounded_rectangle([0,0,bw-1,bh-1],radius=45,fill=255)
        img.paste(_I.fromarray(bg.astype(_np.uint8),"RGB").convert("RGBA"),(bx,by),bm); d=_D.Draw(img)
        d.rounded_rectangle([bx,by,bx+bw,by+bh],radius=45,outline=(255,255,255,150),width=1)
        d.line([bx+30,by+2,bx+bw-30,by+2],fill=(255,255,255,90),width=2)
        txt="Haz el test gratis"; tw=d.textlength(txt,font=_F("Medium",33))
        d.text((cx-20,by+bh//2),txt,font=_F("Medium",33),fill=(255,255,255,255),anchor="mm")
        ax=cx-20+tw/2+22; ay=by+bh//2; d.polygon([(ax,ay-10),(ax,ay+10),(ax+17,ay)],fill=(255,255,255,255))
        d.text((cx,938),"diagnostico.adaptafamilyoffice.com",font=_F("Medium",26),fill=GOLD_HI+(235,),anchor="mm")
        # --- sello de marca (cuño dorado, esquina inferior derecha) ---
        import math as _m
        def _arc(im, ax, ay, ar, txt, fnt, fl, cdeg, cw):
            nn=len(txt); spr=min(14, 150/max(nn,1))
            for i,ch in enumerate(txt):
                a=_m.radians(cdeg+(i-(nn-1)/2)*spr*(1 if cw else -1))
                ci=_I.new("RGBA",(42,42),(0,0,0,0)); _D.Draw(ci).text((21,21),ch,font=fnt,fill=fl,anchor="mm")
                ci=ci.rotate(-(a*180/_m.pi+(90 if cw else -90)),resample=_I.BICUBIC,expand=True)
                im.alpha_composite(ci,(int(ax+ar*_m.cos(a)-ci.width/2),int(ay+ar*_m.sin(a)-ci.height/2)))
        _sx,_sy,_SR=915,852,62; _gA=GOLD+(235,); _gH=GOLD_HI+(235,)
        d.ellipse([_sx-_SR,_sy-_SR,_sx+_SR,_sy+_SR],outline=_gA,width=3)
        d.ellipse([_sx-_SR+9,_sy-_SR+9,_sx+_SR-9,_sy+_SR-9],outline=_gA,width=1)
        _arc(img,_sx,_sy,_SR-15,"ADAPTA \u00b7 FAMILY OFFICE",_F("Medium",15),_gH,-90,True)
        _arc(img,_sx,_sy,_SR-15,"\u00b7 RIGOR PATRIMONIAL \u00b7",_F("Light",13),_gA,90,False)
        _stc=[]
        for i in range(10):
            aa=-_m.pi/2+i*_m.pi/5; rd=_SR*0.30 if i%2==0 else _SR*0.30*0.42
            _stc.append((_sx+rd*_m.cos(aa),_sy+rd*_m.sin(aa)))
        d.polygon(_stc,fill=_gH)
        img.convert("RGB").save(out_path,quality=95)
        return out_path
    except Exception:
        return None


def arquetipo(resp):
    """Devuelve (code, votos, secundario|None) a partir de las preguntas ARQ-*. Degradado seguro."""
    votos={"SEG":0,"LIB":0,"EST":0,"MUL":0}
    for it in INST.get("arquetipo",[]):
        idx=resp.get(it["id"])
        if idx is None: continue
        try: a=it["opciones"][idx].get("arq")
        except (IndexError,TypeError): a=None
        if a in votos: votos[a]+=1
    total=sum(votos.values())
    if total==0:
        return None,votos,None
    orden=sorted(votos,key=lambda k:(-votos[k],_ARQ_FALLBACK.index(k)))
    dom=orden[0]
    sec=orden[1] if votos[orden[1]]>0 and votos[orden[1]]==votos[dom] else (orden[1] if votos[orden[1]]>=2 else None)
    if sec==dom: sec=None
    return dom,votos,sec

# ---------- Cuadro financiero: graficos y modulos deterministas ----------
def _eur(n):
    try: return ("%s"%format(int(round(n)),",d")).replace(",",".")+" €"
    except Exception: return "—"
def _en_tiempo(euros, datos):
    """Traduce un importe a tiempo de vida trabajando: lo unico que no se recupera."""
    try:
        ing=float((datos or {}).get("ingreso_mensual") or 0); euros=float(euros or 0)
        if ing<=0 or euros<=0: return ""
        meses=euros/ing
        if meses>=18:
            anos=meses/12.0
            if anos>45: return ""   # mas que una vida entera de trabajo: traducirlo no aporta, confunde
            return (("%.1f"%anos).replace(".",",")+" años de tu trabajo") if anos<10 else ("%.0f años de tu trabajo"%round(anos))
        if meses>=1:
            return "%.0f meses de tu trabajo"%round(meses)
        return "%.0f horas de tu vida"%round(euros/(ing/160.0))
    except Exception:
        return ""
def _tt(euros, datos, plantilla=" (≈%s)"):
    if not datos: return ""
    try:
        t=_en_tiempo(euros,datos)
    except Exception:
        return ""
    return (plantilla % t) if t else ""

def cashflow_waterfall(datos, path):
    ing=max(datos.get("ingreso_mensual",0),1); gas=datos.get("gasto_mensual",0); aho=datos.get("ahorro_mensual",0)
    resto=max(ing-gas-aho,0); deficit=max(gas+aho-ing,0)
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(6.4,3.0))
    pasos=[("Ingreso",ing,"#0F766E",0)]
    base=ing
    base-=gas; pasos.append(("Gastos",-gas,"#B45309",base))
    base-=aho; pasos.append(("Ahorro",-aho,"#1D6F42",base))
    # barras
    x=range(len(pasos)+1)
    labels=["Ingreso","Gastos","Ahorro","Sin destino"]
    # ingreso
    ax.bar(0,ing,color="#0F766E",width=0.6)
    ax.bar(1,gas,bottom=ing-gas,color="#C2710C",width=0.6)
    ax.bar(2,aho,bottom=ing-gas-aho,color="#1D6F42",width=0.6)
    libre=ing-gas-aho
    ax.bar(3,abs(libre),bottom=min(libre,0),color="#94A3B8" if libre>=0 else "#9A3B2E",width=0.6)
    for i,(lab,val) in enumerate(zip(labels,[ing,gas,aho,abs(libre)])):
        ax.text(i,val if i==0 else 0,"",ha="center")
    ax.set_xticks(range(4)); ax.set_xticklabels(labels,size=9,color="#2C313A")
    ax.annotate(_eur(ing),(0,ing),ha="center",va="bottom",size=8.5,color="#0F766E",weight="bold")
    ax.annotate(_eur(gas),(1,ing-gas/2),ha="center",va="center",size=8.5,color="white",weight="bold")
    ax.annotate(_eur(aho),(2,ing-gas-aho/2),ha="center",va="center",size=8.5,color="white",weight="bold")
    ax.annotate(_eur(abs(libre)),(3,abs(libre)),ha="center",va="bottom",size=8.5,
                color="#2C313A" if libre>=0 else "#9A3B2E",weight="bold")
    ax.set_ylim(0,ing*1.15); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBC6B6"); ax.tick_params(axis="y",labelsize=7,colors="#9CA3AF")
    ax.set_title("De cada euro que entra, a dónde va",size=10,color="#17181C",weight="bold",pad=8)
    plt.tight_layout(); fig.savefig(path,dpi=200,transparent=True); plt.close(fig); gc.collect()
    return libre

def panel_compat(path, compat, nA, nB, notaA, notaB):
    """Heroe oscuro de compatibilidad de pareja: el numero titular del libro."""
    import matplotlib.pyplot as plt, numpy as np
    from matplotlib.patches import Rectangle, FancyBboxPatch
    BG="#0E1018"; CARD="#161A24"; GOLD="#E8C861"; TX="#EDEAE2"; MUT="#8A93A6"
    A_COL="#E8C861"; B_COL="#6FA8DC"
    c=max(0,min(100,round(compat)))
    ccol="#5FB98E" if c>=75 else ("#E8C861" if c>=50 else "#D9755B")
    if c>=80: lect="Vivís el dinero de forma muy parecida. Vuestro reto no es entenderos: es no acomodaros."
    elif c>=60: lect="Hay sintonía de fondo y diferencias sanas. Bien habladas, esas diferencias os suman."
    elif c>=40: lect="Veis el dinero distinto en varias capas. No es incompatibilidad: es trabajo de traducción."
    else: lect="Partís de lugares muy distintos. La buena noticia: ahora sabéis exactamente dónde y por qué."
    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,141.6); ax.axis("off")
    ax.add_patch(Rectangle((0,0),100,141.6,color=BG,zorder=0))
    ax.add_patch(Rectangle((0,131.5),100,0.4,color=GOLD,zorder=2))
    ax.text(8,123,"VUESTRA RELACIÓN CON EL DINERO",color=GOLD,fontsize=13,fontweight="bold",va="center",zorder=3)
    ax.text(7.6,112,"COMPATIBILIDAD",color=TX,fontsize=30,fontweight="bold",va="center",zorder=3)
    ax.text(7.4,74,str(c),color=ccol,fontsize=128,fontweight="bold",va="center",zorder=4)
    # /100 a la derecha del numero
    ax.text(58,60,"/ 100",color=MUT,fontsize=24,fontweight="bold",va="center",zorder=4)
    import textwrap as _tw
    _ly=50.5
    for _ln in _tw.wrap(lect,58):
        ax.text(8,_ly,_ln,color=MUT,fontsize=12,va="center",zorder=4); _ly-=4.6
    # nombres con su salud
    ax.add_patch(FancyBboxPatch((8,28),40,14,boxstyle="round,pad=0.6,rounding_size=2",fc=CARD,ec="#2A3140",lw=1,zorder=3))
    from matplotlib.patches import Circle
    ax.add_patch(Circle((11.5,38.5),0.9,color=A_COL,zorder=5))
    ax.text(13.8,38.5,str(nA).upper(),color=TX,fontsize=11,fontweight="bold",va="center",zorder=5)
    ax.text(10.6,32.5,"Salud psicofinanciera  %d/100"%round(notaA),color=MUT,fontsize=9,va="center",zorder=5)
    ax.add_patch(FancyBboxPatch((52,28),40,14,boxstyle="round,pad=0.6,rounding_size=2",fc=CARD,ec="#2A3140",lw=1,zorder=3))
    ax.add_patch(Circle((55.5,38.5),0.9,color=B_COL,zorder=5))
    ax.text(57.8,38.5,str(nB).upper(),color=TX,fontsize=11,fontweight="bold",va="center",zorder=5)
    ax.text(54.6,32.5,"Salud psicofinanciera  %d/100"%round(notaB),color=MUT,fontsize=9,va="center",zorder=5)
    ax.text(8,9,"ADAPTA FAMILY OFFICE",color=GOLD,fontsize=8.2,fontweight="bold",va="center",zorder=4)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()

def cierre_cta(path, titulo, subtitulo, puntos, contacto):
    """Pagina de cierre a sangre: el siguiente paso con Adapta (CTA)."""
    import matplotlib.pyplot as plt, textwrap
    from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
    BG="#0E1018"; CARD="#161A24"; GOLD="#E8C861"; TX="#EDEAE2"; MUT="#8A93A6"
    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,141.6); ax.axis("off")
    ax.add_patch(Rectangle((0,0),100,141.6,color=BG,zorder=0))
    ax.add_patch(Rectangle((0,131.5),100,0.4,color=GOLD,zorder=2))
    ax.text(8,123,"ADAPTA FAMILY OFFICE",color=GOLD,fontsize=13,fontweight="bold",va="center",zorder=3)
    ax.text(7.6,110,titulo,color=TX,fontsize=33,fontweight="bold",va="top",zorder=3,linespacing=1.05)
    y=92
    for ln in textwrap.wrap(subtitulo, 64):
        ax.text(8,y,ln,color=MUT,fontsize=11.5,va="top",zorder=3); y-=4.4
    y-=4
    for p in puntos:
        ax.add_patch(Circle((9.2,y-0.6),0.9,color=GOLD,zorder=4))
        for j,ln in enumerate(textwrap.wrap(p,58)):
            ax.text(12,y-(j*4.0),ln,color=TX,fontsize=11.5,fontweight=("bold" if j==0 else "normal"),va="top",zorder=4)
        y-=4.0*max(1,len(textwrap.wrap(p,58)))+3.5
    # bloque de contacto
    ax.add_patch(FancyBboxPatch((8,16),84,15,boxstyle="round,pad=0.7,rounding_size=2.5",fc=CARD,ec=GOLD,lw=1.3,zorder=3))
    ax.text(11,26.5,"RESERVA TU CONVERSACIÓN, SIN COMPROMISO",color=GOLD,fontsize=10,fontweight="bold",va="center",zorder=4)
    ax.text(11,20.5,contacto,color=TX,fontsize=10.5,va="center",zorder=4)
    ax.text(8,8,"25 años cuidando patrimonios familiares · sin productos propios · sin conflictos de interés",color=MUT,fontsize=8,va="center",zorder=4)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()

def portadilla(path, acto, titulo, subtitulo):
    """Divisor de acto a sangre: numero filigrana, kicker dorado, titulo grande, subtitulo."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    BG="#0E1018"; GOLD="#E8C861"; TX="#EDEAE2"; MUT="#8A93A6"; FAINT="#171C28"
    num="".join(ch for ch in (acto or "") if ch.isdigit())
    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,141.6); ax.axis("off")
    ax.add_patch(Rectangle((0,0),100,141.6,color=BG,zorder=0))
    if num:
        ax.text(99,74,num,color=FAINT,fontsize=235,fontweight="bold",ha="right",va="center",zorder=1)
    ax.add_patch(Rectangle((8,58),1.3,26,color=GOLD,zorder=3))
    ax.text(12.5,80,(acto or "").upper(),color=GOLD,fontsize=14,fontweight="bold",va="center",zorder=4)
    ax.text(12.5,70,titulo,color=TX,fontsize=31,fontweight="bold",va="top",zorder=4,linespacing=1.05)
    ax.text(12.5,52,subtitulo,color=MUT,fontsize=12,va="top",zorder=4,linespacing=1.3)
    ax.text(8,9,"ADAPTA FAMILY OFFICE",color=GOLD,fontsize=8.2,fontweight="bold",va="center",zorder=4)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()

def panel_persona(path, nombre, salud, arq_code, prof):
    """Portada-heroe oscura del perfil individual: nombre, arquetipo, salud gigante, fortaleza/foco."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
    BG="#0E1018"; CARD="#161A24"; GOLD="#E8C861"; TX="#EDEAE2"; MUT="#8A93A6"
    nota=_sal100(salud)
    arq=ARQ_META.get(arq_code) if arq_code else None
    arqcol=arq.get("color",GOLD) if arq else GOLD
    scol="#5FB98E" if nota>=70 else ("#E8C861" if nota>=45 else "#D9755B")
    orden=sorted([c for c in CAPAS if c in prof],key=lambda c:prof[c]["score"])
    fuerte=_SHORT12.get(orden[0],CAPAS[orden[0]]["nombre"]) if orden else "—"
    foco=_SHORT12.get(orden[-1],CAPAS[orden[-1]]["nombre"]) if orden else "—"
    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,141.6); ax.axis("off")
    ax.add_patch(Rectangle((0,0),100,141.6,color=BG,zorder=0))
    ax.add_patch(Rectangle((0,131.5),100,0.4,color=GOLD,zorder=2))
    ax.text(8,123,"PERFIL INDIVIDUAL",color=GOLD,fontsize=13,fontweight="bold",va="center",zorder=3)
    ax.text(7.4,111,str(nombre).upper(),color=TX,fontsize=44,fontweight="bold",va="center",zorder=3)
    if arq:
        ax.add_patch(Circle((9.0,101.5),1.05,color=arqcol,zorder=4))
        ax.text(11.6,101.5,arq["nombre"].upper(),color=arqcol,fontsize=15,fontweight="bold",va="center",zorder=4)
        ax.text(8,95.5,arq.get("lema",""),color=MUT,fontsize=11.5,style="italic",va="center",zorder=4)
    ax.text(7.6,70,str(nota),color=scol,fontsize=104,fontweight="bold",va="center",zorder=4)
    ax.text(8,52.5,"/ 100   ·   SALUD PSICOFINANCIERA",color=MUT,fontsize=12.5,fontweight="bold",va="center",zorder=4)
    ax.text(8,47,"Cómo vive el dinero por dentro. 100 = en paz; 0 = en tensión constante.",color=MUT,fontsize=9.5,va="center",zorder=4)
    ax.add_patch(FancyBboxPatch((8,26),40,14,boxstyle="round,pad=0.6,rounding_size=2",fc=CARD,ec="#2A3140",lw=1,zorder=3))
    ax.text(10.6,36,"SU MAYOR FORTALEZA",color="#5FB98E",fontsize=8.4,fontweight="bold",va="center",zorder=4)
    ax.text(10.6,30.5,fuerte,color=TX,fontsize=13,fontweight="bold",va="center",zorder=4)
    ax.add_patch(FancyBboxPatch((52,26),40,14,boxstyle="round,pad=0.6,rounding_size=2",fc=CARD,ec="#2A3140",lw=1,zorder=3))
    ax.text(54.6,36,"SU FOCO PRINCIPAL",color="#D9755B",fontsize=8.4,fontweight="bold",va="center",zorder=4)
    ax.text(54.6,30.5,foco,color=TX,fontsize=13,fontweight="bold",va="center",zorder=4)
    ax.text(8,9,"ADAPTA FAMILY OFFICE",color=GOLD,fontsize=8.2,fontweight="bold",va="center",zorder=4)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()

_SHORT12={"C1":"Agotamiento","C2":"Libertad FI","C3":"Resistencia","C4":"Estilo de vida","C5":"Protección","C6":"Estatus","C7":"Concentración","C8":"Antifragilidad","C9":"Flujo de caja","C10":"Salud deuda","C11":"Crecimiento","C12":"Inversión"}

def panel_capas(path, p, titulo="TUS 12 DIMENSIONES",
                subtitulo="Una mirada a cada palanca de tu vida financiera. El verde sostiene; el rojo pide acción."):
    """Pagina a sangre: las 12 dimensiones en diales (vista de un vistazo)."""
    import matplotlib.pyplot as plt, numpy as np
    from matplotlib.patches import Rectangle
    BG="#0E1018"; CARD="#161A24"; GOLD="#E8C861"; TX="#EDEAE2"; MUT="#8A93A6"; TRACK="#2A3140"
    SHORT=_SHORT12
    codes=[c for c in CAPAS if c in p]
    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(0,141.6); ax.axis("off")
    ax.add_patch(Rectangle((0,0),100,141.6,color=BG,zorder=0))
    ax.add_patch(Rectangle((0,128.5),100,13.1,color=CARD,zorder=1))
    ax.add_patch(Rectangle((0,128.3),100,0.35,color=GOLD,zorder=2))
    ax.text(8,135.6,titulo,color=GOLD,fontsize=22,fontweight="bold",va="center",zorder=3)
    ax.text(8,131.4,subtitulo,color=MUT,fontsize=10.5,va="center",zorder=3)
    cols=[14,38,62,86]; rows=[107,72,37]; R=10.0
    for idx,code in enumerate(codes[:12]):
        cxp=cols[idx%4]; cyp=rows[idx//4]
        sc=float(p[code]["score"]); nota=_sal100(sc); col=_sevcol(sc)
        th=np.linspace(np.pi,0,90)
        ax.plot(cxp+R*np.cos(th), cyp+R*np.sin(th), color=TRACK, lw=5.2, solid_capstyle="round", zorder=3)
        frac=nota/100.0
        th2=np.linspace(np.pi, np.pi*(1-frac), 90)
        ax.plot(cxp+R*np.cos(th2), cyp+R*np.sin(th2), color=col, lw=5.2, solid_capstyle="round", zorder=4)
        ax.text(cxp, cyp+1.0, "%d"%nota, color=col, fontsize=18, fontweight="bold", ha="center", va="center", zorder=5)
        ax.text(cxp, cyp-5.0, SHORT.get(code,code), color=TX, fontsize=8.6, ha="center", va="center", zorder=5)
    ax.text(8,6.5,"ADAPTA FAMILY OFFICE",color=GOLD,fontsize=8.2,fontweight="bold",va="center",zorder=4)
    ax.text(92,6.5,"0 = crítico   ·   100 = sólido",color=MUT,fontsize=8,ha="right",va="center",zorder=4)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()

def panel_proyeccion(path, datos, titulo="EL MAPA DE TU FUTURO",
                     subtitulo="Tres caminos parten del mismo punto. La distancia entre ellos es lo que decides hoy.",
                     brecha_cap=None):
    """Pagina cinematografica a sangre: tres caminos del patrimonio + LA BRECHA + hito de libertad."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle
    BG="#0E1018"; CARD="#161A24"; PANEL="#1B2030"; GOLD="#E8C861"; RED="#D9755B"; GREEN="#5FB98E"; BLUE="#6FA8DC"; TX="#EDEAE2"; MUT="#8A93A6"
    edad=int(datos.get("edad",40)); meta_edad=max(EDAD_JUBILACION, edad+5); anos=max(meta_edad-edad,1)
    pat=datos.get("patrimonio",0) or 0; aho=(datos.get("ahorro_mensual",0) or 0)*12
    ing=datos.get("ingreso_mensual",0) or 0; gas=datos.get("gasto_mensual",0) or 0
    superavit=max(0,(ing-gas))*12; inv=datos.get("inversiones_liquidas"); colch=datos.get("colchon_liquido") or 0
    xs=list(range(edad,meta_edad+1))
    _rr=(datos.get("rentabilidad_actual") or 0)/100.0
    if _rr<=0:_rr=0.015
    _r2=max(0.05,_rr)
    def grow(c0,ap,rr):
        v=float(c0);out=[v]
        for _ in range(anos):v=v*(1+rr)+ap;out.append(v)
        return out
    if inv is not None:
        inv=inv or 0; parado=max(0,colch-gas*6); aport_opt=max(aho,superavit)
        e1=[v+parado for v in grow(inv,aho,_rr)]
        _ig=ing*12.0;_gs=gas*12.0;_cap=float(inv+parado);e3=[_cap]
        for _y in range(anos):
            if _y<10:_ig*=1.10
            if _y==0:_gs*=0.90
            _ahy=max(0.0,_ig-_gs);_cap=_cap*1.10+_ahy;e3.append(_cap)
        e2=grow(inv+parado,aport_opt,_r2)
        series=[("Inacción · como hoy",e1,RED,"-"),("Invertir bien",e2,GOLD,"--"),("Ejecutar el plan 10×10",e3,GREEN,"-")]
        lo,hi=e1[-1],e3[-1]
    else:
        e1=grow(pat,aho,0.05); e3=grow(pat,aho+0.05*ing*12,0.05)
        series=[("Si sigues igual",e1,BLUE,"-"),("Si ahorras 5 puntos más",e3,GREEN,"--")]
        lo,hi=e1[-1],e3[-1]
    brecha=hi-lo
    objetivo=gas*12*25 if gas>0 else None   # regla del 4%: patrimonio que cubre tu vida
    edad_libre=None
    if objetivo:
        for i,v in enumerate(e3):
            if v>=objetivo: edad_libre=edad+i; break

    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    bg=fig.add_axes([0,0,1,1]); bg.set_xlim(0,100); bg.set_ylim(0,141.6); bg.axis("off")
    bg.add_patch(Rectangle((0,0),100,141.6,color=BG,zorder=0))
    # banda superior
    bg.add_patch(Rectangle((0,128.5),100,13.1,color=CARD,zorder=1))
    bg.add_patch(Rectangle((0,128.3),100,0.35,color=GOLD,zorder=2))
    bg.text(8,135.6,titulo,color=GOLD,fontsize=22,fontweight="bold",va="center",zorder=3)
    bg.text(8,131.4,subtitulo,color=MUT,fontsize=10.5,va="center",zorder=3)
    # --- chart inset ---
    cx=fig.add_axes([0.085,0.355,0.85,0.475]); cx.set_facecolor("none")
    allv=[v for _,s,_,_ in series for v in s]; ymax=max(allv)*1.08; ymin=0
    # banda de la brecha entre inaccion y plan
    cx.fill_between(xs,e1,e3,color=GREEN,alpha=0.10,zorder=1)
    for nombre,s,col,ls in series:
        cx.plot(xs,s,color=col,lw=2.8 if ls=="-" else 2.2,ls=ls,zorder=4,solid_capstyle="round")
        cx.scatter([xs[-1]],[s[-1]],s=46,color=col,zorder=6,edgecolor=BG,linewidth=1.4)
    # etiquetas euro en los finales
    cx.annotate(_eur(hi),(xs[-1],hi),xytext=(-4,6),textcoords="offset points",ha="right",va="bottom",color=GREEN,fontsize=12,fontweight="bold",zorder=7)
    cx.annotate(_eur(lo),(xs[-1],lo),xytext=(-4,-4),textcoords="offset points",ha="right",va="top",color=RED,fontsize=11,fontweight="bold",zorder=7)
    # linea objetivo de libertad
    if objetivo and objetivo<=ymax:
        cx.axhline(objetivo,color=GOLD,lw=1.0,ls=(0,(4,3)),alpha=0.55,zorder=3)
        cx.annotate("Libertad financiera  "+_eur(objetivo),(xs[0],objetivo),xytext=(2,4),textcoords="offset points",ha="left",va="bottom",color=GOLD,fontsize=8.5,alpha=0.9,zorder=7)
        if edad_libre:
            iy=e3[edad_libre-edad]
            cx.scatter([edad_libre],[iy],s=120,facecolor=GOLD,edgecolor=BG,linewidth=1.6,zorder=8,marker="*")
            cx.annotate("a los %d"%edad_libre,(edad_libre,iy),xytext=(0,10),textcoords="offset points",ha="center",va="bottom",color=GOLD,fontsize=8.5,fontweight="bold",zorder=8)
    cx.set_xlim(xs[0],xs[-1]); cx.set_ylim(ymin,ymax)
    cx.set_xlabel("Tu edad",color=MUT,fontsize=9)
    for sp in ["top","right"]: cx.spines[sp].set_visible(False)
    for sp in ["left","bottom"]: cx.spines[sp].set_color("#39414F")
    cx.tick_params(colors=MUT,labelsize=8)
    import matplotlib.ticker as mtick
    cx.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v,_: ("%.0fk"%(v/1000)) if v<1e6 else ("%.1fM"%(v/1e6))))
    cx.grid(axis="y",color="#262C3A",lw=0.6,zorder=0)
    # leyenda manual
    lx=6.5; ly=44.5
    for nombre,s,col,ls in series:
        bg.plot([lx,lx+2.6],[ly,ly],color=col,lw=3,solid_capstyle="round",zorder=5)
        bg.text(lx+3.4,ly,nombre,color=TX,fontsize=8.4,va="center",zorder=5); lx+=3.4+len(nombre)*1.15+4
    # --- LA BRECHA: callout grande ---
    bg.add_patch(FancyBboxPatch((7,17.5),53,20,boxstyle="round,pad=0.6,rounding_size=2.2",fc=PANEL,ec=GREEN,lw=1.3,zorder=3))
    bg.text(10.5,33.5,"LA BRECHA",color=MUT,fontsize=11,fontweight="bold",va="center",zorder=4)
    bg.text(10.5,26.5,_eur(brecha),color=GREEN,fontsize=30,fontweight="bold",va="center",zorder=4)
    bg.text(10.5,20.6,(brecha_cap or "Lo que separa actuar de no actuar, a los %d años.")%meta_edad,color=MUT,fontsize=8.6,va="center",zorder=4)
    # caja derecha: coste de un anio perdido
    coste_ano=brecha/anos if anos else 0
    bg.add_patch(FancyBboxPatch((63,17.5),30,20,boxstyle="round,pad=0.6,rounding_size=2.2",fc=CARD,ec="#39414F",lw=1.0,zorder=3))
    bg.text(64.8,33.5,"CADA AÑO QUE ESPERAS",color=MUT,fontsize=8.4,fontweight="bold",va="center",zorder=4)
    bg.text(64.8,27.2,"−"+_eur(coste_ano),color=RED,fontsize=18,fontweight="bold",va="center",zorder=4)
    bg.text(64.8,21.2,"de patrimonio futuro,\nde media.",color=MUT,fontsize=8.2,va="center",zorder=4,linespacing=1.25)
    # pie
    bg.text(8,9.2,"Proyección orientativa, no una promesa. Interés compuesto sobre tu liquidez invertible.",color="#5C6470",fontsize=7.6,va="center",zorder=4)
    bg.text(8,5.6,"ADAPTA FAMILY OFFICE",color=GOLD,fontsize=8.2,fontweight="bold",va="center",zorder=4)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()
    return brecha, edad_libre

def proyeccion_chart(datos, path, r=0.05, titulo_override=None):
    import matplotlib.pyplot as plt
    edad=int(datos.get("edad",40)); meta_edad=max(EDAD_JUBILACION, edad+5); anos=max(meta_edad-edad,1)
    pat=datos.get("patrimonio",0) or 0; aho=(datos.get("ahorro_mensual",0) or 0)*12
    ing=datos.get("ingreso_mensual",0) or 0; gas=datos.get("gasto_mensual",0) or 0
    superavit=max(0,(ing-gas))*12; inv=datos.get("inversiones_liquidas"); colch=datos.get("colchon_liquido") or 0
    xs=list(range(edad,meta_edad+1))
    def grow(cap0,aport,rr=r):
        v=cap0; out=[v]
        for _ in range(anos): v=v*(1+rr)+aport; out.append(v)
        return out
    _rr=(datos.get("rentabilidad_actual") or 0)/100.0     # rentabilidad REAL que declara el cliente
    if _rr<=0: _rr=0.015                                   # si no invierte o no la sabe: ~parado, apenas crece
    _r2=max(0.05,_rr)                                      # invertir bien: nunca peor que tu realidad actual
    fig,ax=plt.subplots(figsize=(6.4,3.2))
    if inv is not None:
        inv=inv or 0; parado=max(0,colch-gas*6)
        aport_opt=max(aho,superavit)
        e1=[v+parado for v in grow(inv,aho,_rr)]          # Inaccion: TU rentabilidad real actual
        e2=grow(inv+parado,aport_opt,_r2)                 # Invertir bien: todo trabajando, a mercado
        # Ejecutar el plan (Acelerador 10x10): ingresos +10%/anio los primeros ~10 anios (fase de construccion),
        # gasto -10% una vez y luego plano, rentabilidad 10% -> el patrimonio compone al 10%.
        _ig=ing*12.0; _gs=gas*12.0; _cap=float(inv+parado); e3=[_cap]
        for _y in range(anos):
            if _y<10: _ig*=1.10
            if _y==0: _gs*=0.90
            _ahy=max(0.0,_ig-_gs)
            _cap=_cap*1.10+_ahy
            e3.append(_cap)
        ax.plot(xs,e1,color="#9A3B2E",lw=2.0,label="Inacción (como hoy, al %g%%)"%round(_rr*100))
        ax.plot(xs,e2,color="#B8860B",lw=2.0,ls="--",label="Invertir bien (al %g%%)"%round(_r2*100))
        ax.plot(xs,e3,color="#1D6F42",lw=2.4,label="Ejecutar el plan (10×10)")
        ax.fill_between(xs,e1,e3,color="#1D6F42",alpha=0.06)
        for ser,col,va in [(e1,"#9A3B2E","top"),(e3,"#1D6F42","bottom")]:
            ax.scatter([meta_edad],[ser[-1]],color=col,zorder=5)
            ax.annotate(_eur(ser[-1]),(meta_edad,ser[-1]),ha="right",va=va,size=8,color=col,weight="bold")
        lo,mid,hi,modo=e1[-1],e2[-1],e3[-1],"3"
        titulo="Tres caminos para tu patrimonio (sobre tu liquidez invertible)"
    else:
        base=grow(pat,aho); mejora=grow(pat,aho+0.05*ing*12)  # ahorro ACTUAL + 5 puntos extra (no sustituir)
        ax.plot(xs,base,color="#0284C7",lw=2.2,label="Si sigues igual")
        ax.plot(xs,mejora,color="#1D6F42",lw=2.2,ls="--",label="Si ahorras 5 puntos más")
        ax.fill_between(xs,base,mejora,color="#1D6F42",alpha=0.08)
        for ser,col,va in [(base,"#0284C7","top"),(mejora,"#1D6F42","bottom")]:
            ax.scatter([meta_edad],[ser[-1]],color=col,zorder=5)
            ax.annotate(_eur(ser[-1]),(meta_edad,ser[-1]),ha="right",va=va,size=8,color=col,weight="bold")
        lo,mid,hi,modo=base[-1],None,mejora[-1],"2"
        titulo="Tu patrimonio proyectado a la jubilación (estimación al 5%/año)"
    ax.set_xlabel("Edad",size=8,color="#5C6470"); ax.tick_params(labelsize=7,colors="#9CA3AF")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBC6B6"); ax.spines["bottom"].set_color("#CBC6B6"); ax.grid(False)
    ax.legend(fontsize=8,frameon=False,loc="upper left",labelcolor="#2C313A")
    if titulo_override: titulo=titulo_override
    ax.set_title(titulo,size=10,color="#17181C",weight="bold",pad=8)
    plt.tight_layout(); fig.savefig(path,dpi=200,transparent=True); plt.close(fig); gc.collect()
    return lo,mid,hi,meta_edad,modo

def donut_asignacion(asig, path):
    """Donut HONESTO de asignacion del patrimonio: solo lo que el cliente declara (NUM-13)."""
    import matplotlib.pyplot as plt
    pares=[("Líquido parado", asig.get("parado",0), "#C2710C"),
           ("Invertido y realizable", asig.get("realizable_invertido",0), "#0F766E"),
           ("Resto (vivienda, negocio, ilíquido)", asig.get("resto",0), "#9CA3AF")]
    pares=[(l,max(0,v),c) for l,v,c in pares if v and v>0]
    if not pares: return False
    tot=sum(v for _,v,_ in pares)
    fig,ax=plt.subplots(figsize=(6.0,2.9))
    ax.pie([v for _,v,_ in pares],colors=[c for _,_,c in pares],startangle=90,counterclock=False,
           wedgeprops=dict(width=0.40,edgecolor="white",linewidth=2))
    ax.text(0,0,_eur(tot),ha="center",va="center",fontsize=11.5,weight="bold",color="#17181C")
    ax.legend([f"{l}  ·  {_eur(v)}  ({v/tot*100:.0f}%)" for l,v,_ in pares],
              loc="center left",bbox_to_anchor=(1.0,0.5),frameon=False,fontsize=8.6,labelcolor="#2C313A")
    ax.set(aspect="equal"); plt.tight_layout()
    fig.savefig(path,dpi=200,transparent=True,bbox_inches="tight"); plt.close(fig); gc.collect()
    return True

def panel_distribucion(path, datos, extras=None, fecha=""):
    """Dos paginas-heroe amplias: (1) de donde viene y a donde va (ingresos/gastos);
    (2) lo que has construido (cartera/deudas/patrimonio neto). Donuts grandes + leyenda
    lateral para muchas partidas. Devuelve [path, path_b]."""
    from matplotlib.patches import FancyBboxPatch, Rectangle
    def _de(n):
        try: return ("%s €"%format(float(n),",.0f")).replace(",",".")
        except Exception: return "—"
    BG="#0E1018"; GOLD="#E8C861"; TX="#F4F1E8"; GR="#8A93A6"
    GREEN="#2FB36B"; RED="#D8674F"; SLATE="#3A4150"; AM="#FDD731"
    _PALD=["#2FB36B","#E8C861","#6FA8DC","#D8674F","#9B8CCB","#C2710C","#5FB98E","#E0653B","#7C8696"]
    d=datos or {}; ex=extras or {}
    g=lambda k: float(d.get(k) or 0)
    def _detparts(campo, fb):
        det=d.get(campo+"_detalle")
        if isinstance(det,list):
            out=[]
            for _i,_r in enumerate(det):
                try: _v=float((_r or {}).get("v") or 0)
                except Exception: _v=0
                _c=str((_r or {}).get("c") or "").strip() or "Otros"
                if _v>0: out.append((_c,_v,_PALD[_i%len(_PALD)]))
            if out: return out
        return fb
    ing=g("ingreso_mensual"); gas=g("gasto_mensual"); pas=g("renta_pasiva"); act=max(0.0,ing-pas)
    pgf=d.get("pct_gasto_fijo")
    try: pgf=max(0.0,min(100.0,float(pgf))) if pgf is not None else None
    except Exception: pgf=None
    fijo=(min(gas,g("coste_vivienda")+g("cuota_deuda")) if pgf is None else gas*pgf/100.0); fijo=min(fijo,gas)
    var=max(0.0,gas-fijo)
    deu=g("deuda_total"); cuota=g("cuota_deuda")
    pat=g("patrimonio"); inv=g("inversiones_liquidas"); colch=g("colchon_liquido")
    liquido=inv+colch; iliquido=max(0.0,pat-liquido); neto=pat-deu
    asig=(ex.get("fuentes") or {}).get("asignacion") if ex else None
    def _newpage(titulo,subt):
        fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
        axbg=fig.add_axes([0,0,1,1]); axbg.axis("off"); axbg.set_xlim(0,100); axbg.set_ylim(0,141.6)
        axbg.add_patch(Rectangle((0,128),100,13.6,fc="#141A28",zorder=1))
        axbg.text(8,134,"ADAPTA",fontsize=13,color=GOLD,fontweight="bold",family="DejaVu Sans",zorder=5)
        axbg.text(24.2,134.2,"FAMILY OFFICE",fontsize=7,color=GR,family="DejaVu Sans",zorder=5)
        axbg.plot([8,92],[131.4,131.4],color="#262C3A",lw=1,zorder=3)
        axbg.text(8,122,titulo,fontsize=10,color=GOLD,fontweight="bold",family="DejaVu Sans",zorder=5)
        axbg.text(8,114.5,subt,fontsize=16,color=TX,fontweight="bold",family="DejaVu Sans",zorder=5)
        axbg.plot([8,92],[7,7],color="#262C3A",lw=1,zorder=3)
        axbg.text(8,4.3,"DOCUMENTO CONFIDENCIAL · ADAPTA FAMILY OFFICE · %s"%fecha,fontsize=6.2,color=GR,family="DejaVu Sans",zorder=5)
        return fig,axbg
    def band(fig,axbg,don_b,titulo_base,partes):
        l,b,w,h=0.06,don_b,0.30,0.205
        ty=(b+h)*141.6+1.0
        partes=[(pl,max(0.0,pv),pc) for pl,pv,pc in partes if pv and pv>0]
        cyc=(b+h/2)*141.6
        if not partes:
            axbg.text(8,ty,titulo_base,fontsize=11,color=GOLD,fontweight="bold",family="DejaVu Sans",zorder=5)
            axbg.text(46,cyc,"— sin dato —",fontsize=11,color=GR,ha="left",va="center",family="DejaVu Sans",zorder=5); return
        if len(partes)>8:
            partes=sorted(partes,key=lambda z:-z[1]); _r=sum(z[1] for z in partes[7:]); partes=partes[:7]+[("Otros",_r,"#7C8696")]
        tot=sum(pv for _,pv,_ in partes) or 1
        axbg.text(8,ty,"%s — %s"%(titulo_base,_de(tot)),fontsize=11,color=GOLD,fontweight="bold",family="DejaVu Sans",zorder=5)
        ax=fig.add_axes([l,b,w,h]); ax.set_facecolor("none")
        ax.pie([pv for _,pv,_ in partes],colors=[pc for _,_,pc in partes],startangle=90,counterclock=False,wedgeprops=dict(width=0.40,edgecolor=BG,linewidth=2))
        ax.text(0,0,_de(tot),ha="center",va="center",fontsize=12.5,weight="bold",color=TX); ax.set(aspect="equal")
        n=len(partes); step=min(5.6,(h*141.6*0.96)/n); top=cyc+(n-1)*step/2
        for k,(pl,pv,pc) in enumerate(partes):
            yy=top-k*step
            axbg.add_patch(FancyBboxPatch((45.5,yy-1.1),2.2,2.2,boxstyle="round,pad=0,rounding_size=0.5",fc=pc,ec=pc,zorder=5))
            axbg.text(49.5,yy,str(pl),fontsize=9.2,color=TX,ha="left",va="center",family="DejaVu Sans",zorder=5)
            axbg.text(92,yy,"%s · %.0f%%"%(_de(pv),100*pv/tot),fontsize=9.2,color=GR,ha="right",va="center",family="DejaVu Sans",zorder=5)
    fig,axbg=_newpage("LA DISTRIBUCIÓN DE TU DINERO","De dónde viene tu dinero, y a dónde va")
    band(fig,axbg,0.55,"INGRESOS / mes",_detparts("ingreso_mensual",[("Activo (por tu tiempo)",act,SLATE),("Pasivo (te libera)",pas,GREEN)]))
    band(fig,axbg,0.20,"GASTOS / mes",_detparts("gasto_mensual",[("Fijo (te ata)",fijo,RED),("Variable (flexible)",var,GOLD)]))
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()
    p2=(path[:-4]+"_b.png") if path.lower().endswith(".png") else (path+"_b.png")
    fig,axbg=_newpage("LO QUE HAS CONSTRUIDO","Tu cartera y tu balance patrimonial")
    _cart_fb=([("Líquido parado",asig.get("parado",0),AM),("Invertido",asig.get("realizable_invertido",0),GREEN)] if asig
              else [("Invertido en mercados",inv,GREEN),("Liquidez / colchón",colch,AM)])
    band(fig,axbg,0.58,"TU CARTERA",_detparts("inversiones_liquidas",_cart_fb))
    # ===== BALANCE PATRIMONIAL: activos | pasivos | diferencia =====
    activos=_detparts("patrimonio",[("Inversiones / liquidez",liquido,GREEN),("Vivienda / ilíquido",iliquido,SLATE)])
    pasivos=(_detparts("deuda_total",[("Deuda total",deu,RED)]) if deu>0 else [])
    if len(activos)>8:
        activos=sorted(activos,key=lambda z:-z[1]); _ra=sum(z[1] for z in activos[7:]); activos=activos[:7]+[("Otros",_ra,"#7C8696")]
    if len(pasivos)>8:
        pasivos=sorted(pasivos,key=lambda z:-z[1]); _rp=sum(z[1] for z in pasivos[7:]); pasivos=pasivos[:7]+[("Otros",_rp,"#7C8696")]
    tot_a=sum(v for _,v,_ in activos); tot_p=sum(v for _,v,_ in pasivos); _neto=tot_a-tot_p
    axbg.text(8,53,"TU BALANCE PATRIMONIAL",fontsize=11,color=GOLD,fontweight="bold",family="DejaVu Sans",zorder=5)
    axbg.text(8,48,"ACTIVOS — lo que tienes",fontsize=9,color=GREEN,fontweight="bold",family="DejaVu Sans",zorder=5)
    axbg.text(52,48,"PASIVOS — lo que debes",fontsize=9,color=RED,fontweight="bold",family="DejaVu Sans",zorder=5)
    axbg.plot([50,50],[16.5,46],color="#262C3A",lw=1,zorder=3)
    def _coldraw(parts,x0,xv):
        y=44.0
        for (l,v,c) in parts:
            axbg.add_patch(FancyBboxPatch((x0,y-0.9),1.8,1.8,boxstyle="round,pad=0,rounding_size=0.4",fc=c,ec=c,zorder=5))
            axbg.text(x0+3,y,str(l),fontsize=8.2,color=TX,va="center",family="DejaVu Sans",zorder=5)
            axbg.text(xv,y,_de(v),fontsize=8.2,color=GR,ha="right",va="center",family="DejaVu Sans",zorder=5)
            y-=3.05
    _coldraw(activos,8,47)
    if pasivos: _coldraw(pasivos,52,91)
    else: axbg.text(54,40,"Sin deudas · 100% tuyo",fontsize=9,color=GREEN,fontweight="bold",va="center",family="DejaVu Sans",zorder=5)
    axbg.plot([8,47],[18,18],color="#2A3140",lw=0.8,zorder=4)
    axbg.text(8,16,"Total activos",fontsize=8.5,color=TX,fontweight="bold",family="DejaVu Sans",zorder=5)
    axbg.text(47,16,_de(tot_a),fontsize=9.5,color=GREEN,fontweight="bold",ha="right",family="DejaVu Sans",zorder=5)
    axbg.plot([52,91],[18,18],color="#2A3140",lw=0.8,zorder=4)
    axbg.text(52,16,"Total pasivos",fontsize=8.5,color=TX,fontweight="bold",family="DejaVu Sans",zorder=5)
    axbg.text(91,16,_de(tot_p),fontsize=9.5,color=RED,fontweight="bold",ha="right",family="DejaVu Sans",zorder=5)
    axbg.add_patch(FancyBboxPatch((8,8.5),84,5.2,boxstyle="round,pad=0,rounding_size=1.0",fc="#161A24",ec="#262C3A",lw=1,zorder=4))
    axbg.text(11,11.1,"DIFERENCIA  =  PATRIMONIO NETO",fontsize=9,color=GR,fontweight="bold",va="center",family="DejaVu Sans",zorder=6)
    axbg.text(89,10.9,_de(_neto),fontsize=13.5,color=(GOLD if _neto>=0 else RED),fontweight="bold",ha="right",va="center",family="DejaVu Sans",zorder=6)
    fig.savefig(p2,dpi=200,facecolor=BG); plt.close(fig); gc.collect()
    return [path,p2]

def tapon_coste(datos, real=0.025):
    """Coste de oportunidad de la liquidez parada por encima de un colchon de 6 meses.
    Usa el COLCHON LIQUIDO declarado, nunca el patrimonio neto (que puede estar invertido
    o ser iliquido). Asumir que el patrimonio es efectivo es justo el bug que destruye credibilidad."""
    gas=datos.get("gasto_mensual",0); colch=datos.get("colchon_liquido")
    if not colch or not gas: return None
    sano=gas*6
    exceso=max(colch-sano,0)
    if exceso < 5000: return None
    return exceso, exceso*real

def foda(p):
    orden=sorted(CAPAS,key=lambda c:p[c]["score"])
    fort=[(c,CAPAS[c]["nombre"]) for c in orden[:3]]
    debi=[(c,CAPAS[c]["nombre"]) for c in orden[-3:][::-1]]
    oport=[OPORTUNIDAD[c] for c,_ in debi[:2]]
    amen=[RIESGO[c] for c,_ in debi[:2]]
    return fort,debi,oport,amen

def _box(parras, fondo, barra, ancho=76*mm):
    return Table([[parras]],colWidths=[ancho],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(fondo)),
          ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
          ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
          ("LINEBEFORE",(0,0),(0,-1),3,colors.HexColor(barra)),("VALIGN",(0,0),(-1,-1),"TOP")]))

# --- Sellos de rating estilo agencia (A / BBB / C) sobre métricas clave ---
# Mapea valor->nota con la gama institucional (verde bosque / bronce / terracota), NO semáforo puro.
_RATING_COL={"A":("#1D6F42","#EAF4ED"),"AA":("#1D6F42","#EAF4ED"),"BBB":("#9A7B1F","#FBF4E4"),
             "BB":("#9A7B1F","#FBF4E4"),"C":("#9A3B2E","#FBEDEC"),"CCC":("#9A3B2E","#FBEDEC")}
def _rating_ahorro(t):
    try: t=float(t)
    except Exception: return None
    return "A" if t>=20 else ("BBB" if t>=10 else "C")
def _rating_dti(d):
    try: d=float(d)
    except Exception: return None
    return "A" if d<20 else ("BBB" if d<=35 else "C")
def _rating_cobertura(pct):
    try: pct=float(pct)
    except Exception: return None
    return "A" if pct>=60 else ("BBB" if pct>=30 else "C")
def _sello(nota):
    """Pequeño sello de rating para la esquina de un bloque. Devuelve un Flowable Table compacto."""
    if not nota: return None
    fg,bg=_RATING_COL.get(nota,("#5C6470","#F1EFE8"))
    return Table([[Paragraph("<b>%s</b>"%nota,St("slr",fontSize=12.5,leading=14,textColor=colors.HexColor(fg),fontName=FB,alignment=TA_CENTER)),],
                  [Paragraph("RATING",St("slx",fontSize=4.6,leading=6,textColor=colors.HexColor(fg),fontName=FB,alignment=TA_CENTER))]],
                 colWidths=[15*mm],
                 style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(bg)),("BOX",(0,0),(-1,-1),0.8,colors.HexColor(fg)),
                   ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1),("LEFTPADDING",(0,0),(-1,-1),1),
                   ("RIGHTPADDING",(0,0),(-1,-1),1),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
def _box_sello(parras, fondo, barra, nota=None, ancho=160*mm):
    """_box con un sello de rating en la esquina superior derecha. Failsafe: si nota es None, _box normal."""
    sl=_sello(nota)
    if sl is None: return _box(parras, fondo, barra, ancho=ancho)
    cont=Table([[parras]],colWidths=[ancho-18*mm],
        style=TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
          ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"TOP")]))
    return Table([[cont, sl]],colWidths=[ancho-18*mm,18*mm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(fondo)),
          ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),6),
          ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
          ("LINEBEFORE",(0,0),(0,-1),3,colors.HexColor(barra)),("VALIGN",(0,0),(0,-1),"TOP"),
          ("VALIGN",(1,0),(1,-1),"TOP")]))

def _lineas(n=3, ancho=160*mm, alto=7*mm):
    rows=[[""] for _ in range(n)]
    return Table(rows,colWidths=[ancho],rowHeights=[alto]*n,
        style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.5,colors.HexColor("#E7E3D8")),
          ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))

def report_id(nombre, fecha):
    import hashlib
    ini=''.join([w[0] for w in (nombre or 'X').split()[:2]]).upper() or 'X'
    h=hashlib.sha1((str(nombre)+str(fecha)).encode('utf-8')).hexdigest()[:5].upper()
    return f"AFO-{ini}-{h}"

def valor_hora(datos):
    return max(datos.get("ingreso_mensual",0),0)/160.0

def seccion_ratio_vida(extras):
    """Ratio de Vida (Índice de Riqueza Integral): fusiona Salud, Dinero, Tiempo y Felicidad."""
    rv=extras.get("ratio_vida") if extras else None
    if not rv: return []
    _iri=rv["iri"]; _bd=rv["banda"]
    _bcol="#1D6F42" if _iri>=85 else ("#B8860B" if _iri>=60 else ("#C2710C" if _iri>=40 else "#9A3B2E"))
    out=[PageBreak(), Paragraph("Tu Ratio de Vida",h_sec),
         Paragraph("Tu verdadera riqueza no es solo dinero. Es el cruce de cuatro cosas: <b>salud</b> para disfrutarla, "
                   "<b>tiempo</b> que controlas, <b>dinero</b> que respalda y una vida con <b>sentido</b>. Este número las "
                   "fusiona en uno — y, como la vida real, castiga sin piedad el pilar que descuidas.",body),
         Table([[Paragraph(f"<font size=44 color='{_bcol}'><b>{_iri}</b></font><font size=13 color='#6B7280'>/100</font>",St("rvb",fontSize=44,leading=48)),
                 Paragraph(f"<b>{_bd}</b><br/><font size=8 color='#6B7280'>Índice de Riqueza Integral · media geométrica de tus 4 pilares "
                           f"(un pilar bajo arrastra a todos)</font>",body)]],
               colWidths=[42*mm,118*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)])]
    _rh=St("rvh",fontSize=8,leading=11,textColor=colors.HexColor("#FDD731"),fontName=FB)
    rows=[[Paragraph("PILAR",_rh),Paragraph("TU NOTA /100",_rh),Paragraph("ESTADO",_rh)]]
    for k in ["Salud","Dinero","Tiempo","Felicidad"]:
        v=rv["dims"].get(k,0)
        _c="#1D6F42" if v>=60 else ("#E08A00" if v>=40 else "#C0392B")
        _e="Sólido" if v>=60 else ("A vigilar" if v>=40 else "Frágil")
        rows.append([Paragraph(k,small),Paragraph("<b>%d</b>"%v,small),
                     Paragraph(f"<font color='{_c}'>&#9679;</font>  <font color='{_c}'><b>{_e}</b></font>",small)])
    tab=Table(rows,colWidths=[78*mm,42*mm,40*mm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#101113")),
            ("LINEBELOW",(0,1),(-1,-1),0.4,colors.HexColor("#E7E3D8")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]))
    out+=[Spacer(1,3*mm),tab,Spacer(1,3*mm),
          _box([Paragraph(f"<b>Tu eslabón más débil: {rv['weakest']} ({rv['weakest_val']}/100).</b> En una media geométrica, un "
                "solo pilar bajo arrastra a todos los demás: puedes tener dinero de sobra, pero si tu tiempo o tu salud están "
                "por los suelos, tu riqueza real se desploma. El verdadero rico no es quien más tiene, sino quien tiene los "
                "cuatro en equilibrio. Por eso tu mayor palanca de riqueza está en tu pilar más flojo — y casi nunca es la financiera.",
                St("rvi",fontSize=10.5,leading=15,textColor=INK))],"#FBF4E4","#B45309",ancho=160*mm)]
    # --- Mapa de Tensiones: el coste matemático del desequilibrio (todo medido) ---
    _imp=rv.get("impuesto",0); _pot=rv.get("iri_potencial",_iri); _ten=rv.get("tension","")
    _str=rv.get("strongest"); _strv=rv.get("strongest_val",0); _wv=rv.get("weakest_val",0); _brecha=_strv-_wv
    _lbl=St("rvl",fontSize=9,leading=12,textColor=colors.HexColor("#6B7280"))
    _n1=St("rvn1",fontSize=26,leading=30,textColor=colors.HexColor("#1D6F42"),fontName=FB)
    _n2=St("rvn2",fontSize=26,leading=30,textColor=colors.HexColor("#9A3B2E"),fontName=FB)
    out+=[Spacer(1,6*mm),
          Paragraph("El coste de tu desequilibrio",St("rvt",fontSize=13,leading=16,textColor=INK,fontName=FB))]
    if _brecha>=15:
        _cell=lambda lab,num,sty:[Paragraph(lab,_lbl),Paragraph("<b>%s</b>"%num,sty)]
        out+=[Paragraph(f"Entre tu pilar más fuerte (<b>{_str}</b>, {_strv}) y el más débil (<b>{rv['weakest']}</b>, {_wv}) "
                        f"hay una distancia. Esa distancia tiene un nombre y un precio.",body),
              Spacer(1,3*mm),
              Table([[_cell("Pilar más fuerte",_strv,_n1),_cell("Pilar más débil",_wv,_n2),_cell("Brecha",_brecha,_n2)]],
                     colWidths=[53*mm,53*mm,54*mm],
                     style=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),
                            ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),0)]),
              Spacer(1,3*mm),
              _box([Paragraph((f"<b>{_ten}</b> " if _ten else "")+
                    f"Entre tu pilar más fuerte y el más débil hay <b>{_brecha} puntos</b>. En una media geométrica esa brecha "
                    f"actúa como un techo invisible: te cuesta {_imp} puntos de Ratio real hoy, y no los pierdes por tener poco "
                    f"&mdash; los pierdes por tenerlo casi todo menos una cosa. Y aquí está lo demoledor: si subes "
                    f"<b>{rv['weakest']}</b> al nivel del resto, sin tocar nada más, tu Ratio de Vida salta de "
                    f"<b>{_iri} a {_pot}</b>. Tu mayor retorno no está en ganar más, sino en dejar de descuidar lo que ya tienes.",
                    St("rvx",fontSize=10.5,leading=15,textColor=INK))],"#FBF4E4","#9A3B2E",ancho=160*mm)]
    else:
        out+=[_box([Paragraph("Tus cuatro pilares están prácticamente en equilibrio — y esa es exactamente la forma que tiene "
                    "la riqueza real. La mayoría sobreinvierte en uno y deja que los otros tres se desangren; tú no. "
                    "Tu trabajo ahora no es corregir, es <b>proteger</b> ese equilibrio cuando la vida empuje para romperlo.",
                    St("rvx",fontSize=10.5,leading=15,textColor=INK))],"#EAF3EC","#1D6F42",ancho=160*mm)]
    out+=[PageBreak()]
    return out

def seccion_nudo(extras):
    """El Nudo: las 2-3 tensiones vitales mas agudas, cruzando dinero/salud/tiempo/familia/relaciones."""
    nd = extras.get("nudo") if extras else None
    if not nd:
        return []
    _hr = Table([[""]], colWidths=[160*mm],
        style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.5,colors.HexColor("#E7E3D8")),
            ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    out = [PageBreak(), Paragraph("El nudo: lo que aparece al cruzar tu vida", h_sec),
           Paragraph("Has respondido cada área por separado. Pero tú no vives por separado. Cuando cruzamos "
                     "tus respuestas — dinero, salud, tiempo, familia, relaciones — aparecen las tensiones que "
                     "ningún número aislado puede ver. Estas son las tuyas, de la más aguda a la menos.", body),
           Spacer(1, 5*mm)]
    n = len(nd["tensiones"])
    for i, t in enumerate(nd["tensiones"]):
        out += [Paragraph(f"<font color='#B8860B'><b>{t['dom']}</b></font>",
                    St("nd%d"%i, fontSize=8, leading=11, spaceAfter=2)),
                Paragraph(f"<b>{t['tit']}</b>",
                    St("ndt%d"%i, fontSize=12.5, leading=16, textColor=INK, fontName=FB, spaceAfter=3)),
                Paragraph(t["txt"], St("ndx%d"%i, fontSize=10.5, leading=15, textColor=INK, spaceAfter=8))]
        if i < n-1:
            out += [_hr, Spacer(1, 5*mm)]
    out += [Spacer(1, 4*mm),
            _box([Paragraph("Estas no son cifras: son la trama de tu vida. Y todas se anudan en el mismo sitio. "
                  "Por eso el resto de este libro no va de dinero — va de recuperar lo que el dinero, mal usado, "
                  "te está quitando.", St("ndc", fontSize=10.5, leading=15, textColor=INK))],
                 "#FBF4E4", "#9A3B2E", ancho=160*mm),
            PageBreak()]
    return out

def seccion_conclusion(extras):
    """Cierre del libro: por que levantarte del sofa. Sintetiza nudo principal + palanca IRI + primer paso."""
    if not extras:
        return []
    nd = extras.get("nudo"); rv = extras.get("ratio_vida"); acc = extras.get("accion_unica")
    out = [PageBreak(), Paragraph("¿Por qué levantarte del sofá?", h_sec),
           Paragraph("Has llegado al final. La mayoría no lo hace. Pero leer no cambia nada — y este "
                     "diagnóstico no vale por lo que te ha contado, sino por lo que hagas en los próximos diez "
                     "minutos. Antes de cerrarlo, quédate solo con esto:", body),
           Spacer(1, 5*mm)]
    if nd and nd.get("principal"):
        pr = nd["principal"]
        out += [Paragraph("<font color='#9A3B2E'><b>TU TENSIÓN PRINCIPAL</b></font>",
                    St("cc1", fontSize=8, leading=11, spaceAfter=2)),
                Paragraph(f"<b>{pr['tit']}.</b> {pr['txt']}",
                    St("cc1x", fontSize=11, leading=16, textColor=INK, spaceAfter=10))]
    if rv:
        _p = rv.get("iri_potencial", rv["iri"])
        out += [_box([Paragraph(f"Tu Ratio de Vida hoy es <b>{rv['iri']}</b> — la medida de cuánto de tu vida "
                    f"estás viviendo de verdad. Y lo más importante de todo este libro cabe en una frase: si dejas "
                    f"de descuidar <b>{rv['weakest']}</b>, sube a <b>{_p}</b>, sin ganar un euro más. Tu mayor "
                    f"retorno no está en tener más, sino en reequilibrar lo que ya tienes.",
                    St("cc2", fontSize=10.5, leading=15, textColor=INK))], "#FBF4E4", "#B45309", ancho=160*mm),
                Spacer(1, 5*mm)]
    out += [Paragraph("<font color='#1D6F42'><b>EL PRIMER PASO — EN LAS PRÓXIMAS 48 HORAS</b></font>",
                St("cc3", fontSize=8, leading=11, spaceAfter=2)),
            Paragraph(acc if isinstance(acc, str) and acc else
                "Empieza por el primer movimiento de tu plan y no pases al siguiente hasta tenerlo en marcha.",
                St("cc3x", fontSize=11, leading=16, textColor=INK, spaceAfter=2)),
            Spacer(1, 6*mm),
            _box([Paragraph("El sofá es cómodo. Por eso es peligroso.",
                    St("cc4a", fontSize=14, leading=18, textColor=colors.white, fontName=FB, spaceAfter=5)),
                  Paragraph("La distancia entre quien cambia su vida y quien solo lee sobre ella no es el talento "
                    "ni la suerte: es lo que hace en los diez minutos siguientes a un momento como este. Ya sabes "
                    "cuál es tu nudo, cuánto te cuesta y cuál es tu primer paso. Lo único que falta eres tú, "
                    "de pie.", St("cc4b", fontSize=10.5, leading=15, textColor=colors.white))],
                 "#1A1A17", "#B8860B", ancho=160*mm),
            PageBreak()]
    return out


def seccion_cuatro_caminos(datos, fi, extras=None):
    """Las 4 vias para llegar al numero de libertad (neto de pension): ahorrar mas,
    rentar mejor, ajustar el objetivo, o el plan recomendado. Brutalmente accionable.
    Usa el mismo numero neto de pension que el resto del libro. Se salta sin datos."""
    try:
        import motor_financiero_v3 as mfv3
    except Exception:
        return []
    d=datos or {}
    _ideal=d.get("coste_vida_ideal")
    try: _ideal=float(_ideal) if _ideal not in (None,"") else 0.0
    except Exception: _ideal=0.0
    _gm=float(d.get("gasto_mensual") or 0)
    gasto=_ideal if _ideal>0 else _gm; pension=float(d.get("pension_estimada") or 0)
    capital=float(d.get("inversiones_liquidas") or 0)+float(d.get("colchon_liquido") or 0)
    ahorro=float(d.get("ahorro_mensual") or 0)
    try: edad=int(float(d.get("edad") or 0))
    except Exception: edad=0
    horizonte=max(1, 67-edad) if 0<edad<67 else 15
    rent_real=5.0
    try:
        exp=mfv3.analizar_expectativas(gasto, pension, capital, ahorro, horizonte, rent_real)
    except Exception:
        return []
    if not exp or not exp.get("numero_libertad"):
        return []
    N=exp["numero_libertad"]; pct=exp.get("pct_cubierto",0); falta=exp.get("brecha_renta",0)
    out=[PageBreak(), Paragraph("Tu n\u00famero, y las 4 v\u00edas para llegar a \u00e9l",h_sec)]
    if pension>0:
        _vida=("la vida que <b>quieres</b>" if _ideal>0 else "tu vida")
        out.append(Paragraph("Este es el capital que necesitas para vivir de %s sin depender de un sueldo, ya <b>neto de "
                             "tu pensi\u00f3n p\u00fablica</b> (la mayor\u00eda de los test la ignoran; nosotros la descontamos)."%_vida,body))
    else:
        out.append(Paragraph("Este es el capital que, invertido, cubre tu vida para siempre (regla 25\u00d7).",body))
    out.append(Paragraph('<font size=30 color="#17181C"><b>%s</b></font>'%_eur(N),St("c4n",fontSize=30,leading=34,spaceBefore=2,spaceAfter=2)))
    out.append(Paragraph("Hoy lo tienes cubierto al <b>%s%%</b>%s."%(pct, (" \u00b7 te falta <b>%s</b>"%_eur(falta)) if falta and falta>0 else ""),body))
    # MATIZ FISCAL ESPANA: la regla del 4% es BRUTA (origen USA). En Espana las rentas del
    # ahorro tributan ~21%, asi que vivir de rentas NETAS exige ~30% mas capital. Diferenciador.
    try:
        _Nf=round(float(N)/0.79)
        out.append(_box([Paragraph("<b>Matiz fiscal (Espa\u00f1a).</b> Esta cifra sigue la regla del 4%% \u2014de origen "
                  "estadounidense y por tanto <b>bruta</b>\u2014. En Espa\u00f1a las rentas del ahorro tributan al ~21%%, "
                  "as\u00ed que para vivir de rentas <b>netas</b> de esa vida necesitar\u00edas del orden de <b>%s</b>. "
                  "La mayor\u00eda de las calculadoras copian la regla americana y lo ignoran; nosotros te lo decimos."%_eur(_Nf),
                  St("c4f",fontSize=10,leading=14))],"#FBF6E6","#C9962B",ancho=160*mm))
    except Exception:
        pass
    if exp.get("pension_cubre"):
        out.append(_box([Paragraph("<b>Tu pensi\u00f3n estimada ya cubre la vida que describes.</b> Tu reto no es llegar: es "
                  "proteger ese colch\u00f3n y optimizar lo que ya tienes. Una posici\u00f3n poco com\u00fan \u2014 cu\u00eddala.",St("c4p",fontSize=10.5,leading=15))],
                  "#EEF7F0","#1D6F42",ancho=160*mm))
        out.append(PageBreak()); return out
    cm=exp.get("caminos") or {}
    def via(tag,cifra,desc,barra,bg):
        return _box([Paragraph("<font color='%s'><b>%s</b></font>"%(barra,tag),St("c4t",fontSize=9.5,leading=12,fontName=FB,spaceAfter=1)),
                     Paragraph("<b>%s</b>"%cifra,St("c4c",fontSize=15,leading=18,textColor=INK,spaceAfter=1)),
                     Paragraph(desc,St("c4d",fontSize=9,leading=12,textColor=colors.HexColor("#6B7280")))],
                    bg,barra,ancho=160*mm)
    ax=cm.get("ahorro_extra",0)
    out+=[Spacer(1,2*mm),
          via("CAMINO 1 \u00b7 Ahorra m\u00e1s",
              ("Ya ahorras suficiente para tu plazo" if ax<=0 else "+%s/mes"%_eur(ax)),
              "Sobre lo que ya ahorras, para llegar a tu n\u00famero en %d a\u00f1os."%horizonte,"#0F766E","#EAF4F1")]
    rn=cm.get("rentabilidad_necesaria")
    out+=[Spacer(1,2*mm),
          via("CAMINO 2 \u00b7 Haz rentar mejor",
              ("Con tu ahorro actual no basta solo con rentabilidad" if rn is None else "%s%% anual"%rn),
              "Manteniendo tu ahorro de hoy, esta es la rentabilidad que tu capital necesita.","#B45309","#FBF1E3")]
    out+=[Spacer(1,2*mm),
          via("CAMINO 3 \u00b7 Ajusta el objetivo",
              "%s/mes"%_eur(cm.get("objetivo_alcanzable",0)),
              "La vida que <b>s\u00ed</b> es sostenible con lo que haces hoy, sin cambiar nada m\u00e1s.","#6B7280","#F3F4F6")]
    pr=cm.get("plan_recomendado") or {}
    rec=("Mant\u00e9n el rumbo: a tu ritmo ya llegas" if pr.get("ya_llega")
         else "Ahorra +%s/mes y apunta a una vida de %s/mes"%(_eur(pr.get("extra",0)),_eur(pr.get("objetivo",0))))
    out+=[Spacer(1,2*mm),
          via("\u2605 CAMINO 4 \u00b7 El plan que recomendamos", rec,
              "La mezcla realista \u2014 ni n\u00fameros m\u00e1gicos ni renuncias dram\u00e1ticas. Es lo que dise\u00f1ar\u00edamos contigo.","#9A3412","#FBF4E4")]
    out+=[PageBreak()]
    return out



def seccion_rentabilidad_alquiler(datos, extras=None):
    """Rentabilidad REAL del ladrillo: lo que de verdad renta un alquiler tras gastos e IRPF,
    frente a lo que el cliente cree. Solo si declara alquiler + valor de los inmuebles."""
    d=datos or {}
    try:
        rent=float(d.get("ing_alquiler") or 0); valor=float(d.get("valor_inmuebles") or 0)
    except Exception:
        return []
    if rent<=0:
        pl=(d.get("perfil_laboral") or "")
        pl=" ".join(pl) if isinstance(pl,list) else str(pl)
        if "entista" in pl: rent=float(d.get("renta_pasiva") or 0)
    if rent<=0 or valor<=0:
        return []
    renta_anual=rent*12.0
    neta=renta_anual/valor*100.0          # ing_alquiler ya es LIMPIO (gastos + IRPF) -> esta es la rentabilidad real
    col="#1D6F42" if neta>=4 else ("#B45309" if neta>=2.5 else "#9A3B2E")
    out=[PageBreak(), Paragraph("Tu ladrillo: la rentabilidad que crees vs la real",h_sec),
         Paragraph("La mayor\u00eda de propietarios calculan la renta sobre lo que pagaron por el piso, y olvidan los "
                   "gastos y los impuestos. Esta es tu rentabilidad <b>real</b> \u2014 lo que de verdad te queda, ya neto "
                   "de gastos e IRPF \u2014 sobre el valor de mercado de hoy.",body),
         Paragraph('<font size=32 color="%s"><b>%.1f%%</b></font><font size=12 color="#6B7280"> neta real, despu\u00e9s de gastos e impuestos</font>'%(col,neta),
                   St("ralq1",fontSize=32,leading=36,spaceBefore=2,spaceAfter=2)),
         Paragraph("Sobre un valor de mercado de <b>%s</b> y una renta limpia de <b>%s/mes</b> (%s/a\u00f1o)."%(_eur(valor),_eur(rent),_eur(renta_anual)),body),
         _box([Paragraph("<b>Lo que esto significa:</b> tu ladrillo te renta de verdad un <b>%.1f%%</b> anual, no el 5-6%% "
                  "que sale de dividir la renta entre lo que pagaste. Es el n\u00famero con el que de verdad se decide si "
                  "concentrar o diversificar \u2014 no la rentabilidad \u00abde folleto\u00bb."%neta,
                  St("ralq2",fontSize=10.5,leading=15))],"#FBF4E4","#B45309",ancho=160*mm),
         Paragraph("<font size=9.3 color='#6B7280'>Para comparar: una cartera global diversificada ha rentado de media en "
                   "torno al 7% nominal a largo plazo, es l\u00edquida y no depende de un solo inquilino. Tu inmueble "
                   "concentra patrimonio en un \u00fanico activo poco l\u00edquido. No es bueno ni malo en s\u00ed: es una "
                   "decisi\u00f3n que conviene tomar con el n\u00famero real delante, no con el que se intuye.</font>",
                   St("ralq3",fontSize=9.3,leading=13,spaceBefore=4))]
    # Diferenciar inmueble de RENTA (alquiler -> rentabilidad, ya calculada arriba) de inmueble de USO
    # (segunda vivienda -> activo patrimonial sin yield). Aditivo y a prueba de fallos.
    try:
        _segunda=0.0
        _pd=d.get("patrimonio_detalle")
        if isinstance(_pd,list):
            for r in _pd:
                _c=str((r or {}).get("c","")).strip().lower()
                if "segunda vivienda" in _c:
                    try: _segunda+=max(0.0,float((r or {}).get("v") or 0))
                    except Exception: pass
        if _segunda>0:
            out.append(Paragraph("Nota: este c\u00e1lculo solo cubre tus inmuebles <b>en alquiler</b> (los que generan renta). "
                      "Tu <b>segunda vivienda</b> \u2014 valorada en torno a <b>%s</b> \u2014 es un activo de <b>uso</b>, no de "
                      "renta: no entra en esta rentabilidad porque no produce yield. Cuenta como patrimonio y como "
                      "disfrute, pero no como inversi\u00f3n que rinda."%_eur(_segunda),
                      St("ralq4",fontSize=9.3,leading=13,spaceBefore=4)))
    except Exception:
        pass
    out.append(PageBreak())
    return out


def seccion_familia(datos, extras=None):
    """La linea temporal de la familia y la proteccion recomendada. Solo si hay dependientes."""
    d=datos or {}
    dep=(d.get("dependientes") or "")
    dep=" ".join(dep) if isinstance(dep,list) else str(dep)
    dl=dep.lower()
    if not ("hijo" in dl or "varios" in dl):
        return []
    try: edad=int(float(d.get("edad_hijo_menor"))) if d.get("edad_hijo_menor") not in (None,"") else None
    except Exception: edad=None
    COSTE_ANUAL=7200.0
    try: nh=max(1,min(6,int(float(d.get("n_hijos"))))) if d.get("n_hijos") not in (None,"") else 1
    except Exception: nh=1
    out=[PageBreak(), Paragraph("La l\u00ednea de tu familia, y tu protecci\u00f3n",h_sec)]
    if edad is not None and 0<=edad<24:
        anios_indep=max(0,24-edad); anios_uni=max(0,18-edad)
        proteccion=anios_indep*COSTE_ANUAL*nh
        out.append(Paragraph("Si te faltaras hoy, sostener a los tuyos hasta su independencia \u2014 cubrir su vida unos "
                  "<b>%d a\u00f1os</b> m\u00e1s \u2014 costar\u00eda del orden de <b>%s</b>. Es la cifra que un seguro de vida "
                  "o un patrimonio l\u00edquido deber\u00edan poder cubrir. La pregunta no es agradable, pero tenerla "
                  "resuelta a tiempo es el mayor acto de cuidado que existe."%(anios_indep,_eur(proteccion)),body))
        if anios_uni>0:
            out.append(Paragraph("Pr\u00f3ximo gran hito: la <b>universidad, en %d a\u00f1os</b>. Empezar a apartar una "
                      "cantidad peque\u00f1a hoy convierte ese golpe futuro en un plan tranquilo."%anios_uni,body))
        out.append(Paragraph("Y cuando el menor se independice, dentro de <b>%d a\u00f1os</b>, recuperar\u00e1s una "
                  "capacidad de ahorro importante: conviene tenerlo ya en el plan, para que ese aire no se diluya en "
                  "gasto."%anios_indep,body))
        out.append(Paragraph("Un matiz honesto: la <b>emancipación rara vez es limpia</b>. Muchos hijos necesitan un "
                  "empujón final —una entrada para su primera vivienda, los primeros meses fuera de casa—. Lo sensato "
                  "es reservar para ese último tramo y, a la vez, tener ya asignado en tu plan el ahorro que liberas "
                  "cuando se independizan, para que ese aire no se evapore en gasto nuevo.",body))
    else:
        out.append(Paragraph("Tienes personas que dependen econ\u00f3micamente de ti. La conversaci\u00f3n de protecci\u00f3n "
                  "\u2014 un seguro de vida suficiente y un patrimonio l\u00edquido que cubra su sost\u00e9n si t\u00fa faltaras \u2014 "
                  "es la que m\u00e1s tranquilidad da tenerla resuelta a tiempo. Es banca privada en su sentido m\u00e1s "
                  "humano: proteger a los tuyos del peor de los escenarios.",body))
    # --- Liberacion de gasto por hijo, cuando el cliente dio la edad de cada uno (edades_hijos) ---
    # Aditivo y conservador: estima cuando cada hijo alcanza ~24 (independencia tipica en Espana) y, por tanto,
    # cuando se libera el gasto que hoy consume. No inventa edades: solo usa las que el cliente conoce.
    try:
        _eh=d.get("edades_hijos")
        if isinstance(_eh,list):
            _con=sorted([int(float(x)) for x in _eh if x not in (None,"") and 0<=int(float(x))<=30])
            if len(_con)>=1:
                INDEP=24
                _pend=[a for a in _con if a<INDEP]        # aun lejos de la independencia: liberacion futura
                _trans=[a for a in _con if a>=INDEP]      # en/superada la independencia: fase de transicion (clamp: nunca anios negativos)
                if _pend:
                    _libera_eur=COSTE_ANUAL*len(_pend)
                    # El PRIMERO en independizarse es el mayor de los pendientes; el ULTIMO, el mas joven.
                    # clamp: anios_para_liberacion = max(0, INDEP - edad). Nunca un numero negativo en el PDF.
                    _anios_primero=max(0,INDEP-max(_pend))
                    _anios_ultimo=max(0,INDEP-min(_pend))
                    out.append(Paragraph("<b>Tu calendario de liberaci\u00f3n de gasto.</b> Con las edades que nos has dado, "
                              "el primero de tus hijos a\u00fan en casa se independizar\u00eda en torno a <b>%d a\u00f1o(s)</b> y el "
                              "m\u00e1s peque\u00f1o en torno a <b>%d a\u00f1o(s)</b>. A medida que cada uno vuele, recuperar\u00e1s "
                              "capacidad de ahorro \u2014 del orden de <b>%s al a\u00f1o</b> por hijo, una estimaci\u00f3n prudente. "
                              "El acto inteligente es decidir HOY ad\u00f3nde ir\u00e1 ese aire (inversi\u00f3n, plan de pensiones, "
                              "tu propia libertad) antes de que se diluya en gasto nuevo."%(_anios_primero,_anios_ultimo,_eur(_libera_eur)),body))
                    out.append(Paragraph("Y un apunte honesto sobre el \u00faltimo tramo: la emancipaci\u00f3n rara vez es limpia. "
                              "Reservar para ese empuj\u00f3n final \u2014 una entrada, los primeros meses fuera \u2014 evita que el "
                              "salto les pille (y te pille) sin colch\u00f3n.",body))
                    if _trans:
                        # Hijos mayores que conviven con los pendientes: fase de transicion, sin numero negativo.
                        out.append(Paragraph("Adem\u00e1s, %s de tus hijos ya ronda o supera la edad de independencia: est\u00e1 en "
                                  "<b>fase de transici\u00f3n</b>, con la emancipaci\u00f3n inminente. Ah\u00ed el gasto que liberas no es "
                                  "futuro, es de ahora: en cuanto d\u00e9 el salto, ese aire vuelve a tu plan. Lo sano es ponerle "
                                  "horizonte e importe al apoyo, para que no se vuelva indefinido."%("alguno" if len(_trans)>1 else "uno"),body))
                elif _trans:
                    # TODOS en/superada la independencia: emancipacion inminente, nunca "en -2 anios liberaras".
                    out.append(Paragraph("Por las edades que nos has dado, tus hijos ya rondan o superan la edad de independencia: "
                              "est\u00e1n en <b>fase de transici\u00f3n, con la emancipaci\u00f3n inminente</b>. No hay un calendario futuro "
                              "que esperar \u2014 el gasto se libera ahora, a medida que cada uno da el salto. Si a\u00fan apoyas a alguno, "
                              "lo sano es ponerle un horizonte y un importe: el apoyo indefinido sin l\u00edmite es el que m\u00e1s erosiona "
                              "un patrimonio sin que se note. Y reservar para ese \u00faltimo empuj\u00f3n \u2014 una entrada, los primeros "
                              "meses fuera \u2014 evita que el salto les pille (y te pille) sin colch\u00f3n.",body))
    except Exception:
        pass
    out.append(PageBreak())
    return out


def seccion_fuentes(extras):
    """Mapa de fuentes de ingreso: cuántas, cuánto rinde cada una y a qué precio de tiempo (€/hora)."""
    f=extras.get("fuentes") if extras else None
    if not f: return []
    out=[Paragraph("Tu mapa de fuentes de ingreso",h_sec),
         Paragraph("Depender de una sola fuente es la mayor fragilidad financiera que existe: el día que falla, lo "
                   "pierdes todo a la vez. Aquí está la tuya, fuente por fuente, con lo que de verdad importa — cuánto "
                   "te renta cada una y a qué precio de tu tiempo.",body)]
    _fh=St("fh",fontSize=8,leading=11,textColor=colors.HexColor("#FDD731"),fontName=FB)
    rows=[[Paragraph("FUENTE",_fh),Paragraph("€/MES",_fh),Paragraph("H/SEM",_fh),Paragraph("€/HORA",_fh),Paragraph("TIPO",_fh)]]
    for it in f["fuentes"]:
        _hrs=("%g"%it["horas"]) if it["horas"] is not None else "—"
        _eh="— (sin tu tiempo)" if it["eur_hora"] is None else _eur(it["eur_hora"])
        _tipo="Pasiva" if it["pasiva"] else "Activa"; _tc="#1D6F42" if it["pasiva"] else "#9A3B2E"
        rows.append([Paragraph(it["nombre"],small),Paragraph(_eur(it["ingreso"]),small),Paragraph(_hrs,small),
                     Paragraph(_eh,small),Paragraph(f"<font color='{_tc}'><b>{_tipo}</b></font>",small)])
    tab=Table(rows,colWidths=[54*mm,26*mm,24*mm,30*mm,24*mm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#101113")),
            ("LINEBELOW",(0,1),(-1,-1),0.4,colors.HexColor("#E7E3D8")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]))
    out+=[Spacer(1,3*mm),tab,Spacer(1,4*mm)]
    n=f["n"]; conc=f["concentracion"]
    if n==1:
        _d=("<b>Hoy toda tu vida financiera cuelga de un solo hilo.</b> El 100% de lo que entra viene de una única "
            "fuente: el día que falle —un despido, un cliente que se va, una baja— tu ingreso no baja, desaparece. No es "
            "alarmismo, es estructura. La primera prioridad de tu plan no es ganar más en esa fuente: es abrir una segunda."); _dc="#9A3B2E"; _db="#FBECE8"
    elif conc>=70:
        _d=(f"<b>Tienes {n} fuentes, pero una sola concentra el {conc}% de lo que entra.</b> Sobre el papel estás "
            f"diversificado; en la práctica, casi todo sigue dependiendo de una pieza. Diversificar de verdad es que "
            f"ninguna fuente pueda hundirte ella sola."); _dc="#B45309"; _db="#FBF4E4"
    else:
        _d=(f"<b>Tienes {n} fuentes de ingreso, y eso es una fortaleza real.</b> Cuantos más pilares sostienen tu "
            f"economía, menos te afecta que uno falle. Tu trabajo ahora es que cada uno rinda y que el peso no se "
            f"concentre en uno solo."); _dc="#1D6F42"; _db="#EAF5EE"
    out.append(_box([Paragraph(_d,St("fd1",fontSize=10.5,leading=15,textColor=INK))],_db,_dc,ancho=160*mm))
    peor=f.get("peor_activa")
    if peor and peor.get("eur_hora"):
        out.append(Paragraph(f"<b>El precio de tu tiempo:</b> tu fuente «{peor['nombre']}» te renta unos "
                             f"<b>{_eur(peor['eur_hora'])}/hora</b>. Esa es la pregunta incómoda: ¿es el mejor uso de esas horas, "
                             f"o podrías subir su valor —o sustituirla— y liberar tiempo para algo que rinda más? No se trata de "
                             f"trabajar más horas: se trata de que cada hora valga más.",
                             St("fd2",fontSize=9.7,leading=14,spaceBefore=6)))
    if not f["tiene_pasiva"]:
        out.append(Paragraph("<b>Hoy ni un euro entra sin tu tiempo.</b> Todas tus fuentes exigen tus horas. Quienes llegan "
                             "lejos comparten una cosa: construyeron al menos una fuente que trabaja sin ellos —un alquiler, "
                             "dividendos, un negocio sistematizado—. La primera es la que más cuesta y la que más libera: es el "
                             "salto que cambia el juego.",St("fd3",fontSize=9.7,leading=14,spaceBefore=4)))
    else:
        out.append(Paragraph(f"<b>Ya tienes {f['n_pasivas']} fuente(s) que no dependen de tu tiempo.</b> Eso es justo lo que "
                             f"construye libertad: dinero que entra mientras vives. Protégelas, reinvierte lo que generan y haz que "
                             f"crezcan hasta que un día cubran tu coste de vida. Ahí es donde trabajar pasa a ser elección.",
                             St("fd4",fontSize=9.7,leading=14,spaceBefore=4)))
    out.append(Spacer(1,3*mm))
    return out

def cuadro_financiero(p, datos, fi):
    """FODA + cash flow + proyeccion + tapon. Devuelve flowables."""
    out=[Paragraph("Tu cuadro financiero",h_sec),
         Paragraph("Antes de pasar a la acción, esta es tu fotografía objetiva en una sola página: tus fuerzas y "
                   "frentes, por dónde se mueve tu dinero y hacia dónde te lleva si no cambias nada.",body),
         Paragraph("FODA financiero",h_sub)]
    fort,debi,oport,amen=foda(p)
    F=[Paragraph("<b><font color='#1D6F42'>Fortalezas</font></b>",small)]+[Paragraph("&#8226; "+n,small) for _,n in fort]
    D=[Paragraph("<b><font color='#9A3B2E'>Debilidades</font></b>",small)]+[Paragraph("&#8226; "+n,small) for _,n in debi]
    O=[Paragraph("<b><font color='#0284C7'>Oportunidades</font></b>",small)]+[Paragraph("&#8226; "+t,small) for t in oport]
    A=[Paragraph("<b><font color='#B45309'>Amenazas</font></b>",small)]+[Paragraph("&#8226; "+t,small) for t in amen]
    out.append(Table([[F,O],[D,A]],colWidths=[80*mm,80*mm],
        style=TableStyle([("BACKGROUND",(0,0),(0,0),colors.HexColor("#EAF5EE")),
          ("BACKGROUND",(1,0),(1,0),colors.HexColor("#EAF1FB")),
          ("BACKGROUND",(0,1),(0,1),colors.HexColor("#FBECE8")),
          ("BACKGROUND",(1,1),(1,1),colors.HexColor("#FBF4E4")),
          ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
          ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
          ("LINEBELOW",(0,0),(-1,0),3,PAGEBG),("LINEAFTER",(0,0),(0,-1),3,PAGEBG)])))
    out.append(PageBreak())
    cashflow_waterfall(datos,"_cash.png")
    out+=[KeepTogether([Paragraph("Tu flujo de caja",h_sub),
          Image("_cash.png",width=160*mm,height=75*mm,hAlign="CENTER")])]
    # Anatomia del flujo: deficit real (dinamico, solo si gasta mas de lo que ingresa)
    _ingm=max(datos.get("ingreso_mensual",0),0); _gasm=datos.get("gasto_mensual",0) or 0; _defm=_gasm-_ingm
    if _defm>0:
        out.append(_box([
            Paragraph("<font color='#9A3B2E'><b>Brecha negativa: %s/mes</b></font>"%_eur(_defm),St("brnh",fontSize=11,leading=15)),
            Paragraph("<font size=9.5>Gastas <b>%s/mes</b> e ingresas <b>%s/mes</b>: operas en déficit de <b>%s al mes</b> (unos <b>%s al año</b>). Ese hueco no se evapora — se cubre consumiendo tu colchón o con deuda invisible (tarjetas, aplazamientos). En banca privada se llama <i>pérdida latente por descontrol de costes fijos</i>. La palanca no es ganar más: es ver, al euro, a dónde va tu dinero.</font>"%(_eur(_gasm),_eur(_ingm),_eur(_defm),_eur(_defm*12)),St("brnx",fontSize=9.5,leading=14,spaceBefore=3))],
            "#FBECE8","#9A3B2E",ancho=160*mm))
        out.append(Paragraph("<font color='#6B6B62'><i>Dictamen de dirección patrimonial: la libertad no se alcanza subiendo los ingresos al infinito, sino optimizando la estructura que sostiene cada euro que ya generas.</i></font>",St("dic",fontSize=9.5,leading=14,spaceBefore=5)))
    elif _ingm>=2500 and _defm<0 and (-_defm)/_ingm<0.12:
        _mrg=-_defm; _mrp=_mrg/_ingm*100
        out.append(_box([Paragraph(f"<font color='#B45309'><b>Ley de Parkinson: tus gastos han subido con tus ingresos</b></font><br/>"
            f"<font size=9.5>Ingresas <b>{_eur(_ingm)}/mes</b> y te queda un margen de apenas <b>{_eur(_mrg)}</b> "
            f"(un {_mrp:.0f}% de lo que entra). No es que ganes poco: tu estilo de vida ha crecido casi al ritmo de tus "
            f"ingresos. Es la Ley de Parkinson aplicada al dinero — el gasto se expande hasta llenar lo que entra; el dinero "
            f"no se evapora, se acomoda. Cada euro de esa subida que recuperes va directo a tu libertad, sin trabajar un "
            f"minuto más.</font>",St("park",fontSize=10.5,leading=15))],"#FBF4E4","#B45309",ancho=160*mm))
    tap=tapon_coste(datos)
    if tap:
        exceso,coste=tap
        vnh=valor_hora(datos)
        horas=(coste/12)/vnh if vnh>0 else 0
        coste10=exceso*(1-(1/(1.03**10)))  # poder adquisitivo erosionado en 10 años al 3%
        out.append(_box([Paragraph(f"<font color='#B45309'><b>El impuesto silencioso por inacción</b></font><br/>"
            f"<font size=9.5>Tienes unos <b>{_eur(exceso)}</b> de liquidez por encima de un colchón sano de 6 meses. "
            f"Parada y sin invertir, no te cuesta {_eur(coste)} hoy: te cuesta el tiempo. Proyectado a diez años, "
            f"esa cifra pierde alrededor de <b>{_eur(coste10)} de poder adquisitivo</b> si la inflación ronda el 3% anual. "
            f"No es prudencia: es un peaje invisible que pagas por no decidir. Mover una parte a algo que al menos "
            f"preserve su valor es de las decisiones más rentables y menos arriesgadas que tienes sobre la mesa.</font>",
            St("tp",fontSize=10.5,leading=15))],"#FBF4E4","#B45309",ancho=160*mm))
    out.append(PageBreak())
    try:
        panel_proyeccion("_proypanel.png", datos)
        out += [FullBleedImage("_proypanel.png"), PageBreak()]
    except Exception:
        pass
    f65,mid65,m65,medad,modo=proyeccion_chart(datos,"_proy.png")
    if modo=="3" and f65<1000 and mid65<1000:
        # Sin liquidez invertible las dos primeras vias salen ~0 EUR y parecen un error: reencuadre honesto al plan
        narr=(f"Hoy tu liquidez invertible es casi cero, así que las dos primeras vías —seguir igual o solo invertir "
              f"mejor— apenas mueven la aguja: sin capital que crezca, el interés compuesto no tiene de dónde partir. "
              f"Lo que de verdad cambia tu futuro es <b>construir ese capital cada mes</b>: ejecutando el plan (ahorro "
              f"sistemático, ingresos +10%/año los primeros años y un 10% —media histórica del mercado—), a los {medad} "
              f"podrías rondar los <b>{_eur(m65)}</b>. La palabra clave es empezar: el primer euro invertido es el que "
              f"pone en marcha todo lo demás. Orientativo, no una promesa.")
    elif modo=="3":
        _rc=datos.get("rentabilidad_actual") or 0
        _rctxt=("tu rentabilidad real, ~%g%%"%_rc) if _rc>0 else "tu dinero casi parado"
        narr=(f"Tres caminos, a los {medad}. <b>1 · Inacción</b> (como hoy, con {_rctxt}): <b>{_eur(f65)}</b>. "
              f"<b>2 · Invertir bien</b>: <b>{_eur(mid65)}</b>. "
              f"<b>3 · Ejecutar el plan completo</b>: <b>{_eur(m65)}</b> — <b>{_eur(m65-f65)}</b> más que sin hacer nada. "
              f"La lección es brutal: invertir mejor ayuda, pero lo que multiplica tu patrimonio es <b>ejecutar el plan</b>. "
              f"Eso no es suerte ni mercado: es el coste de no decidir. (Inacción: tu rentabilidad declarada. Plan: ingresos "
              f"+10%/año los primeros años, estilo de vida contenido y un 10% —media histórica del mercado—. Orientativo, no "
              f"una promesa.)")
    else:
        narr=(f"Si mantienes tu ritmo actual, a los {medad} rondarías los <b>{_eur(f65)}</b>. Subiendo tu ahorro cinco "
              f"puntos, esa cifra sube a <b>{_eur(m65)}</b>: la diferencia entre ambas líneas es, literalmente, el precio de "
              f"no decidir. (Estimación a un 5% anual; orientativa, no una promesa de rentabilidad.)")
    out.append(Paragraph("Hacia dónde vas",h_sub))   # el grafico va en la pagina oscura "El mapa de tu futuro"; aqui solo numeros + narrativa
    _cl=St("cmL",fontSize=8.5,leading=11,textColor=colors.HexColor("#6B7280"))
    def _cn(lab,val,col):
        return [Paragraph(lab,_cl),
                Paragraph("<b>%s</b>"%_eur(val),St("cmN"+col,fontSize=18,leading=22,textColor=colors.HexColor(col),fontName=FB))]
    if modo=="3":
        out+=[Spacer(1,3*mm),
              Table([[_cn("Sin hacer nada",f65,"#9A3B2E"),_cn("Invirtiendo bien",mid65,"#B8860B"),
                      _cn("Ejecutando tu plan",m65,"#1D6F42")]],colWidths=[53*mm,53*mm,54*mm],
                    style=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),
                           ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),0)]),
              Spacer(1,2*mm),
              Paragraph(f"La distancia entre quedarte quieto y ejecutar tu plan es <b>{_eur(m65-f65)}</b>{_tt(m65-f65,datos,' — o, en lo unico que no se recupera, <b>≈%s</b>')}. No la decide "
                        f"el mercado ni la suerte: la decides tú, cada mes que empiezas — o que aplazas.",
                        St("cmg",fontSize=10.5,leading=15,textColor=INK)),
              Spacer(1,3*mm)]
    elif mid65 is not None:
        out+=[Spacer(1,3*mm),
              Table([[_cn("Si sigues igual",f65,"#0284C7"),_cn("Si ahorras 5 puntos más",m65,"#1D6F42")]],
                    colWidths=[80*mm,80*mm],style=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),
                           ("TOPPADDING",(0,0),(-1,-1),2)]),
              Spacer(1,2*mm),
              Paragraph(f"Esos <b>{_eur(m65-f65)}</b> de diferencia son, literalmente, el precio de no decidir.",
                        St("cmg2",fontSize=10.5,leading=15,textColor=INK)),
              Spacer(1,3*mm)]
    out+=[Paragraph(narr,body), PageBreak()]
    return out

def laboratorio_individual(p, datos, fi, salud, resp):
    out=[Paragraph("Tu cuaderno de trabajo",h_sec),
         Paragraph("Aquí termina el análisis y empiezas tú. Estos ejercicios están pensados para hacerse con boli, "
                   "impresos o en pantalla, esta misma semana. Un informe que se lee se olvida; uno que se rellena, cambia algo.",body)]
    # 1. Valor de tu hora
    vnh=valor_hora(datos)
    if vnh>0:
        tap=tapon_coste(datos); extra=""
        if tap:
            horas=(tap[1]/12)/vnh
            extra=(f" Con tu liquidez parada perdiendo valor, estás regalando el equivalente a unas "
                   f"<b>{horas:.0f} horas de tu trabajo cada mes</b> en coste de oportunidad.")
        _c1=p.get("C1",{}).get("score",50)
        _desg=max(0.0,min(0.40,(100-_c1)/100.0*0.5))   # mas estres (C1 bajo) -> mas descuento, tope 40%
        _desg_p=""
        if _desg>=0.05:
            _desg_p=(f" Pero esa es tu hora en bruto. Tu capa de estrés financiero está en <b>{_c1:.0f}/100</b>: "
                     f"al descontar ese desgaste —el peso que el dinero te lleva a casa, las horas que no descansas— "
                     f"tu hora real cae a <b>{_eur(vnh*(1-_desg))}</b>, un <b>{_desg*100:.0f}% menos</b>. No es una "
                     f"medición clínica, es una lente para decidir: cuando tu hora vale eso, delegar y soltar deja de ser un lujo.")
        out+=[Paragraph("1 · El valor de tu hora",h_sub),
              Paragraph(f"Tu hora de vida trabajada vale aproximadamente <b>{_eur(vnh)}</b> (ingreso neto ÷ 160 h). "
                        f"Deja de pensar en euros y empieza a pensar en horas de vida.{_desg_p}{extra}",body),
              Paragraph("Apunta un gasto o una ineficiencia que quieras revisar y tradúcelo a horas de tu vida:",small),
              _lineas(2),Spacer(1,4*mm)]
    # 2. FODA de arbitraje
    fort,debi,_,_=foda(p)
    out+=[Paragraph("2 · Tu arbitraje del fin de semana",h_sub),
          Paragraph(f"Tu mayor fortaleza es <b>{fort[0][1]}</b>. Tu mayor freno es <b>{debi[0][1]}</b>. El ejercicio "
                    f"no es teórico: usa la primera para atacar el segundo. Escribe la <b>única</b> acción concreta "
                    f"que harás este fin de semana para mover ese freno — y ponle fecha y hora:",body),
          _lineas(2),Spacer(1,4*mm)]
    # 3. El guion del dinero
    out+=[Paragraph("3 · El guion del dinero",h_sub),
          Paragraph("Casi ninguna decisión de dinero es racional: repetimos el guion que aprendimos de niños. "
                    "Escribe las tres frases sobre el dinero que más oías en tu casa de pequeño "
                    "(p. ej. «el dinero no cae de los árboles», «hay que guardar por si acaso»):",body),
          _lineas(3),
          Paragraph("Ahora une cada frase con un comportamiento tuyo de hoy. ¿Cuál te está ayudando y cuál te está frenando?",small),
          _lineas(2),Spacer(1,4*mm)]
    # 4. Compromiso firmado
    plan_top=plan(p)
    palanca=plan_top[0][2] if plan_top else "tu primer foco del plan"
    out+=[Paragraph("4 · Tu compromiso",h_sub),
          _box([Paragraph(f"<b>Me comprometo</b>, antes de 30 días, a dar un primer paso sobre: "
                f"<b>{palanca}</b>.",St("cm",fontSize=10.5,leading=15)),
                Spacer(1,8*mm),
                Table([["Firma","Fecha"]],colWidths=[95*mm,55*mm],
                  style=TableStyle([("LINEABOVE",(0,0),(-1,0),0.6,colors.HexColor("#9CA3AF")),
                    ("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#9CA3AF")),("FONTSIZE",(0,0),(-1,0),8),
                    ("TOPPADDING",(0,0),(-1,0),3)]))],"#EEF2F8","#0284C7",ancho=160*mm),
          PageBreak()]
    return out

def glosario(p, datos, fi):
    """Glosario dinamico: solo terminos activados por las respuestas del usuario."""
    g=[]
    # Nucleo siempre presente
    g.append(("Número de libertad financiera",
        "El patrimonio que, invertido, cubre tus gastos para siempre (regla práctica: gasto anual × 25).",
        (f"El tuyo ronda los {_eur(fi[0])}; hoy lo tienes cubierto en torno a un {fi[1]:.0f}%." if fi[1]<100 else f"El tuyo ronda los {_eur(fi[0])}, y hoy ya lo superas (cobertura ~{fi[1]:.0f}%): por patrimonio, estás en libertad financiera."),
        "Es tu meta-marco: cada decisión acerca o aleja esa cifra. Tenerla puesta cambia cómo priorizas."))
    g.append(("Tasa de ahorro",
        "El porcentaje de lo que ingresas que consigues retener cada mes.",
        f"La tuya es de un {fi[2]:.0f}%. Es, con diferencia, la palanca que más mueve tu libertad.",
        "Subirla cinco puntos pesa más en tu futuro que casi cualquier decisión de inversión."))
    # Coste de oportunidad / tapon
    tap=tapon_coste(datos)
    if tap:
        g.append(("Coste de oportunidad de la liquidez",
            "El rendimiento que dejas de ganar por tener dinero parado en lugar de trabajando.",
            f"Tienes ~{_eur(tap[0])} por encima de un colchón sano; parado, deja de ganar unos {_eur(tap[1])} al año.",
            "No es prudencia: es un peaje silencioso. Mover una parte a algo que preserve valor es de lo más rentable y seguro que tienes."))
        g.append(("Arbitraje de pasivos",
            "Usar el excedente parado para amortizar deuda en lugar de dejarlo al 0%.",
            "Aplicado a tu deuda más cara, equivale a una rentabilidad garantizada y libre de impuestos igual a ese interés.",
            "Es el movimiento que une cabeza y tranquilidad: rentas tu dinero y bajas el estrés a la vez."))
    # Deuda
    if p["C10"]["score"]>=45:
        g.append(("Deuda de alto interés (deuda mala)",
            "Financiación al consumo —tarjetas revolving, microcréditos— que en España se mueven en el entorno del 20% TAE.",
            "Tu capa de deuda muestra tensión. Si arrastras revolving, esto no admite matices: amortizarla es tu prioridad absoluta, por delante de cualquier inversión.",
            "Ninguna cartera te renta de forma fiable un 20% neto; cancelar esa deuda sí. Es la rentabilidad más alta, segura y libre de impuestos a tu alcance — ejecútala primero."))
    # Resiliencia / emergencia
    if p["C3"]["score"]>=45:
        g.append(("Fondo de resiliencia",
            "Dinero líquido e intocable para imprevistos; idealmente 3-6 meses de gastos.",
            "Tu capa de resiliencia muestra holgura escasa: reforzar este colchón va antes que invertir.",
            "No se mide en euros, sino en meses de libertad: es lo que te deja decir «no» sin miedo."))
    # Lifestyle creep
    if p["C4"]["score"]>=50:
        g.append(("Deriva del nivel de vida",
            "La tendencia a gastar más cuando ingresas más, sin apenas notarlo.",
            "Tu índice de eficiencia del estilo de vida sugiere que parte de tu subida de ingresos se evapora.",
            "Es el enemigo silencioso del ahorro: cada mejora de sueldo se diluye si no la fijas antes de gastar."))
    # Concentracion de ingresos
    if p["C7"]["score"]>=50:
        g.append(("Concentración de ingresos",
            "Cuánto depende tu economía de una sola fuente de ingresos.",
            "Tu capa de concentración está elevada: una parte grande de tu seguridad cuelga de un hilo.",
            "A más concentración, más riesgo oculto. Diversificar ingresos es blindaje, no lujo."))
    # Blindaje legal
    if p["C5"]["score"]>=50:
        g.append(("Blindaje patrimonial",
            "El conjunto de medidas legales —testamento, seguros, poderes— que protegen lo tuyo y a los tuyos.",
            "Tu checklist de herencia y blindaje tiene huecos: es de lo que más tranquilidad da cerrar.",
            "Barato de resolver, caragísimo de ignorar. El día que hace falta, ya no hay margen."))
    return g[:8]

EDAD_JUBILACION = 67  # referencia ordinaria (2026: 66a10m si <38a3m cotizados, 65 si mas; 67 objetivo 2027)

def _edad_txt(datos):
    try: e = int(float(datos.get("edad") or 0))
    except Exception: e = 0
    if e <= 0: return "Tu perfil"
    aj = max(0, EDAD_JUBILACION - e)
    return ("%d años  ·  a %d de la edad ordinaria de jubilación" % (e, aj)) if aj > 0 else "%d años" % e

def cohorte_txt(cli, datos):
    """Texto de cohorte por sexo y edad para los percentiles."""
    try: edad = int(datos.get("edad", 0) or 0)
    except Exception: edad = 0
    sx = (cli.get("sexo") or "").strip().lower()
    if sx.startswith("h"): grupo = "hombres"
    elif sx.startswith("m"): grupo = "mujeres"
    else: grupo = "personas"
    if edad <= 0: rango = "de tu edad"
    elif edad < 30: rango = "menores de 30"
    elif edad < 40: rango = "de 30 a 39 a\u00f1os"
    elif edad < 50: rango = "de 40 a 49 a\u00f1os"
    elif edad < 60: rango = "de 50 a 59 a\u00f1os"
    else: rango = "de 60 o m\u00e1s"
    return "%s %s" % (grupo, rango)

def citas_capa(code, resp, k=2, min_score=50):
    """Devuelve las opciones que el cliente eligio con mayor disfuncion y frase diagnostica,
    para que el informe cite su conducta real en vez de texto generico de banda."""
    capa=CAPAS[code]; out=[]
    for it in capa["items"]:
        if it["tipo"]!="escala": continue
        idx=resp.get(it["id"])
        if idx is None: continue
        op=it["opciones"][idx]; tag=op.get("tag_narrativo") or op.get("texto")
        if tag and op["score"]>=min_score:
            out.append((op["score"], it["texto"], tag))
    out.sort(key=lambda x:-x[0])
    return out[:k]

def seccion_extras(extras, datos=None):
    """Secciones v2: brecha vital, palancas de crecimiento y contradicciones. Devuelve flowables."""
    if not extras: return []
    br=extras.get("brecha"); pal=extras.get("palancas") or []; con=extras.get("contradicciones") or []
    out=[PageBreak(), Paragraph("Tu brecha y tus palancas de crecimiento",h_sec),
         Paragraph("Hasta aquí, tu foto. Ahora la pregunta que de verdad mueve un patrimonio: "
                   "¿cuánto te separa de la vida que dijiste querer, y qué palancas la acortan?",body)]
    if br and extras.get("crisis"):
        out+=[Spacer(1,3*mm),
              Paragraph("Una nota antes de seguir: hoy no toca medir la distancia hasta tu vida ideal ni tu número de "
                        "libertad a décadas — eso, ahora, solo añadiría peso. Cuando recuperes el control del mes "
                        "(colchón, deuda, calma), esta brecha será una conversación útil y hasta motivadora. Hoy tu única "
                        "meta es estabilizar; lo demás llegará desde tierra firme.",
                        St("brc",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=8))]
    elif br:
        ci=_eur(br["coste_ideal_mes"])
        if br.get("sin_ingreso"):
            rc=_eur(br.get("renta_capital_mes",0))
            if br.get("ingreso_cubre_ideal"):
                linea=(f"No tienes un ingreso recurrente: tu vida la sostiene tu capital. Al 4% prudente, tu patrimonio "
                       f"rinde unos <b>{rc}/mes</b> y tu vida ideal pide <b>{ci}/mes</b>: el capital te cubre. "
                       f"El trabajo ahora es que rente de forma ordenada y no se erosione.")
            else:
                linea=(f"No tienes ingreso recurrente: hoy vives de tu capital. Al 4% prudente rendiría unos "
                       f"<b>{rc}/mes</b>, pero tu vida ideal pide <b>{ci}/mes</b> — faltan <b>{_eur(br['brecha_mes'])}/mes</b>. "
                       f"A este ritmo consumes principal: el patrimonio mengua en lugar de sostenerte.")
        else:
            ing=_eur(br["ingreso_mes"])
            if br["brecha_mes"]>0:
                linea=(f"La vida que describes como ideal cuesta <b>{ci}/mes</b>. Hoy ingresas <b>{ing}/mes</b>. "
                       f"La brecha es de <b>{_eur(br['brecha_mes'])} al mes</b> ({_eur(br['brecha_anual'])} al año): "
                       f"justo lo que tu modelo actual todavía no genera.")
            else:
                linea=(f"Tu vida ideal cuesta <b>{ci}/mes</b> y ya ingresas <b>{ing}/mes</b>: el flujo te da. "
                       f"La pregunta deja de ser cuánto ganas y pasa a ser a qué velocidad conviertes ese margen en capital.")
        _na=(f" Para tu vida actual: {_eur(br['numero_actual'])}." if br.get("numero_actual") else "")
        out+=[Spacer(1,3*mm),
              _box([Paragraph(linea,St("brx",fontSize=10.5,leading=15)),
                    Paragraph(f"Tu número de libertad para <b>esa</b> vida (regla 25×): <b>{_eur(br['numero_ideal'])}</b>{_tt(br['numero_ideal'],datos,' — <b>≈%s</b>')}.{_na}",
                              St("brx2",fontSize=9.6,leading=14,textColor=GREY,spaceBefore=4))],
                   "#FBF4E4","#B45309",ancho=160*mm)]
        mapr={"en rumbo":"Y tú mismo lo lees así: <b>en rumbo</b>. Las matemáticas te acompañan; el trabajo es no desviarte.",
              "espejismo":"Y tú mismo lo nombras: <b>espejismo</b>. Vives bien el presente mientras el futuro se aleja en silencio.",
              "vía muerta":"Y tú mismo lo reconoces: <b>vía muerta</b>. Sin cambiar de modelo, esa vida es matemáticamente inviable con tu estructura de ingresos actual. La buena noticia: el modelo se cambia."}
        if br.get("reconocimiento") in mapr:
            out.append(Paragraph(mapr[br["reconocimiento"]],St("brr",fontSize=10,leading=14,spaceBefore=4)))
    if pal:
        out+=[Spacer(1,4*mm), Paragraph("Tus palancas de crecimiento",h_sub),
              Paragraph("No son consejos genéricos: salen de tus propios números. En orden de impacto.",small)]
        for ti,tx in pal:
            out.append(Paragraph(f"<font color='#0F766E'>&#9656;</font>  <b>{ti}</b>",St("plt",fontSize=10.5,leading=14,spaceBefore=5)))
            out.append(Paragraph(tx,St("plx",fontSize=9.7,leading=14,leftIndent=12,spaceAfter=3)))
    if con:
        out+=[Spacer(1,4*mm), Paragraph("Disonancias estructurales — lo que no te cuadra",h_sub),
              Paragraph("Las grietas más caras de un plan viven en la distancia entre lo que dices, lo que sientes y lo que miden tus números. Estas son las tuyas:",small)]
        for ti,tx in con:
            out.append(Paragraph(f"<font color='#9A3B2E'>&#9656;</font>  <b>{ti}</b>",St("cot",fontSize=10.5,leading=14,spaceBefore=5)))
            out.append(Paragraph(tx,St("cox",fontSize=9.7,leading=14,leftIndent=12,spaceAfter=3)))
    rt=extras.get("ratios") or []
    if rt:
        _RC={"verde":"#1D6F42","ambar":"#B8860B","rojo":"#9A3B2E","info":"#7A7A72"}
        out+=[Spacer(1,5*mm), Paragraph("Tu matriz de resiliencia financiera",h_sub),
              Paragraph("Las cifras que un buen asesor mira primero. Cada una con su umbral y qué hacer si se cruza. El color es el semáforo: verde sano, ámbar a vigilar, rojo a actuar.",small)]
        _rows=[]
        for r in rt:
            _rows.append([Paragraph("<b>%s</b>"%r["nombre"],small),
                          Paragraph("<font color='%s'><b>%s</b></font>"%(_RC.get(r["estado"],"#7A7A72"),r["valor"]),small),
                          Paragraph("<font color='#6B7280'>%s</font>"%r["accion"],small)])
        _rt=Table(_rows,colWidths=[50*mm,38*mm,72*mm])
        _rt.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),0.3,LINE),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),6)]))
        out+=[_rt]
    fnt=extras.get("fortuna_neta")
    if fnt:
        cm=(" &#183; colchón de <b>%g meses</b> de gastos" % fnt["colchon_meses"]) if fnt.get("colchon_meses") else ""
        out+=[Spacer(1,5*mm), Paragraph("Tu fortuna neta hoy",h_sub),
              Paragraph("El número maestro: lo que de verdad es tuyo cuando restas todo lo que debes. Es la cifra que conviene recalcular cada seis meses.",small),
              Spacer(1,2*mm),
              _box([Paragraph("Activos <b>%s</b> &#8722; Deuda <b>%s</b> = Fortuna neta <b>%s</b>%s"%(_eur(fnt["activos"]),_eur(fnt["pasivos"]),_eur(fnt["neta"]),cm),
                              St("fnt",fontSize=10.5,leading=15))],"#EEF2F8","#0F766E",ancho=160*mm)]
        if fnt.get("asignacion") and donut_asignacion(fnt["asignacion"],"_donut.png"):
            out+=[Spacer(1,4*mm), Paragraph("Cómo está repartido tu patrimonio",h_sub),
                  Paragraph("Solo con lo que has declarado, sin suponer nada:",small),
                  Image("_donut.png",width=152*mm,height=60*mm,hAlign="CENTER")]
            if fnt.get("resistencia_meses"):
                out.append(Paragraph("Tu <b>músculo de resistencia</b> —colchón inmediato más lo que rescatarías en días— cubre <b>%g meses</b> de gastos. No estás desprotegido; lo que conviene ajustar es cuánto tienes en líquido inmediato." % fnt["resistencia_meses"], St("mr",fontSize=9.7,leading=14,spaceBefore=3)))
    dt=extras.get("deuda_tipo")
    if dt:
        out+=[Spacer(1,5*mm), Paragraph(dt[0],h_sub), Spacer(1,2*mm),
              Paragraph(dt[1],St("dtx",fontSize=10,leading=14,textColor=INK,backColor=LIGHT,borderPadding=7,spaceBefore=0,spaceAfter=0))]
    pr=extras.get("presupuesto")
    if pr:
        out+=[Spacer(1,5*mm), Paragraph("Tu presupuesto: el marco",h_sub),
              Paragraph("No te pedimos las cuarenta categorías de tu vida — ese cuadro de mando lo construimos contigo en Adapta. Esto es el marco desde tus cifras: dónde está tu dinero y dónde debería estar.",small)]
        lin="De tus <b>%s/mes</b> de gasto: vivienda <b>%s</b>"%(_eur(pr["gasto"]),_eur(pr["vivienda"]))
        if pr["deuda"]: lin+=", deuda <b>%s</b>"%_eur(pr["deuda"])
        lin+=", y el resto de tu vida <b>%s</b>."%_eur(pr["resto"])
        out.append(Paragraph(lin,St("prl",fontSize=9.7,leading=14,spaceBefore=3)))
        if pr.get("recomendado"):
            rc=pr["recomendado"]
            out.append(Paragraph("Marco de referencia 50/30/20 sobre tus ingresos: necesidades ~<b>%s</b>, deseos ~<b>%s</b>, y a construir patrimonio ~<b>%s</b>/mes. Una brújula, no una jaula."%(_eur(rc["necesidades"]),_eur(rc["deseos"]),_eur(rc["ahorro"])),St("prr",fontSize=9.7,leading=14,spaceBefore=3)))
        if pr.get("empresario"):
            out.append(Paragraph("<font color='#B45309'>&#9656;</font>  <b>Síndrome del cortocircuito patrimonial: separa familia y negocio.</b> Tu cuota de autónomos, tus tributos y la gestoría <b>no son gasto de vida familiar</b>: mezclarlos distorsiona tu coste de vida real y tu verdadera capacidad de ahorro. Tu negocio no debe financiar tu vida ni tu vida absorber los golpes del negocio. Dos cuentas, dos presupuestos, siempre.",St("pre",fontSize=9.7,leading=14,spaceBefore=4,leftIndent=4)))
            out.append(Spacer(1,3*mm))
            out.append(_box([
                Paragraph("<font color='#1F6FB2'><b>Nota de dirección patrimonial: el registro contable no es arquitectura financiera</b></font>",St("dp1",fontSize=10.6,leading=15)),
                Paragraph("Tu <b>gestoría</b> mira hacia atrás: registra lo que ya pasó y liquida tus impuestos. Es necesaria, pero no diseña tu futuro. La <b>dirección patrimonial</b> mira hacia delante: ordena la estructura de tus activos, tu vehículo societario y la pasarela entre tu empresa y tu patrimonio personal <i>antes</i> de que cierre el año fiscal. El gestor rellena el formulario; la estrategia decide qué debe decir ese formulario.",St("dp2",fontSize=9.4,leading=14,textColor=colors.HexColor('#2C313A'),spaceBefore=3))],
                "#EAF1FB","#0284C7",ancho=160*mm))
    vi=extras.get("vivienda")
    if vi and vi.get("modo"):
        _sevc={"alta":"#9A3B2E","media":"#B45309","baja":"#0F766E"}.get(vi.get("severidad"),"#B45309")
        _fnd={"alta":"#FBECE8","media":"#FBF4E4","baja":"#EEF2F8"}.get(vi.get("severidad"),"#FBF4E4")
        _items=[Paragraph("<font color='%s'><b>%s</b></font>"%(_sevc,_limpiar_txt(vi["titulo"])),
                          St("vivt",fontSize=10.8,leading=15,spaceAfter=4))]
        for _i,_p in enumerate(vi.get("parrafos",[])):
            _items.append(Paragraph(_limpiar_txt(_p),St("vivp%d"%_i,fontSize=10,leading=14.5,spaceAfter=3)))
        out+=[Spacer(1,5*mm), Paragraph("Tu vivienda",h_sub),
              Paragraph("Tu mayor gasto fijo y, según el caso, tu mayor riesgo oculto o tu mayor tranquilidad. "
                        "Lo que tu respuesta revela:",small),
              Spacer(1,2*mm), _box(_items,_fnd,_sevc,ancho=160*mm)]
    out+=[Spacer(1,5*mm), Paragraph("Tu marco de inversión",h_sub),
          Paragraph("Principios, no productos. Qué recomendar en concreto es trabajo de tu asesor en Adapta — y depende de tu situación. Lo que no cambia son las reglas:",small)]
    for _pp in ["Primero el colchón, después invertir: nunca inviertas el dinero que podrías necesitar en 6 meses.",
                "Aporta de forma periódica y automática: la constancia bate al cronómetro (nadie acierta el momento exacto).",
                "Diversifica por clases de activo: no dependas de una sola pieza, por buena que parezca hoy.",
                "Vigila las comisiones: un punto al año, compuesto a 20 años, se come cerca de un tercio de lo que habrías acumulado.",
                "Piensa en décadas y no vendas por miedo: el peor enemigo de tu rentabilidad eres tú en un mal día."]:
        out.append(Paragraph("<font color='#0F766E'>&#9656;</font>  %s"%_pp,St("miv",fontSize=9.6,leading=13,leftIndent=10,spaceAfter=2)))
    for blk in (extras.get("energia"), extras.get("conciliacion"), extras.get("asesor"), extras.get("herencia")):
        if blk:
            ti,tx=blk
            out+=[Spacer(1,5*mm), Paragraph(ti,h_sub), Spacer(1,3*mm),
                  Paragraph(tx,St("axh",fontSize=10,leading=14,textColor=INK,backColor=LIGHT,borderPadding=7,spaceBefore=0,spaceAfter=0))]
    pa=extras.get("preguntas_asesor")
    if pa:
        out+=[Spacer(1,3*mm), Paragraph("Llévale esto a tu próxima reunión con tu asesor",h_sub),
              Paragraph("Tres preguntas para convertir una cita de papeleo en una de estrategia:",small)]
        for q in pa:
            out.append(Paragraph("<font color='#0F766E'>&#9656;</font>  «%s»"%q,St("pqa",fontSize=9.6,leading=13,leftIndent=10,spaceAfter=3)))
        out.append(Paragraph("Y si esas preguntas le quedan grandes, no es un fallo tuyo: una gestoría tramita, no "
                             "diseña estrategia patrimonial. Lo que de verdad necesitas es una capa de asesoramiento "
                             "<b>integral</b> —que mire a la vez tu fiscalidad, tus inversiones y tus inmuebles como un solo "
                             "patrimonio—. Es otro oficio, el de un family office, y es el que mueve la aguja.",
                             St("pqz",fontSize=9.7,leading=14,textColor=GREY,spaceBefore=6)))
    return out

def seccion_compromiso(extras):
    """Cierre: protocolo de revisión a 6 meses + Contrato contigo mismo (firma presente/futuro)."""
    if not extras: return []
    cmp=extras.get("compromiso")
    out=[PageBreak()]   # "revision a 6 meses" eliminada (compresion); el contrato sigue debajo
    if cmp:
        if cmp.get("crisis"):
            out+=[Spacer(1,7*mm), Paragraph("Tu compromiso: primero, recuperar el aire",h_sec),
                  Paragraph("Hoy no toca firmar grandes cifras ni horizontes a décadas. Toca estabilizar. Este es tu compromiso —tres pasos, ni uno más— para volver a tener el control y la calma. El resto llegará cuando estés en tierra firme.",body)]
            inner=[Paragraph("<b>YO, HOY, DECIDO</b> dejar de exigirme y empezar a sostenerme: recuperar el control de mi mes y mi descanso, antes que cualquier meta lejana.",St("c0",fontSize=10.5,leading=15))]
        else:
            out+=[Spacer(1,7*mm), Paragraph("Contrato contigo mismo",h_sec),
                  Paragraph("Un diagnóstico cambia algo solo cuando se vuelve decisión. Esto no es un deseo: es un compromiso, escrito con tus propios números.",body)]
            inner=[Paragraph("<b>YO, HOY, DECIDO</b> que mi libertad financiera no será fruto del azar, sino de disciplina, estrategia y visión a largo plazo.",St("c0",fontSize=10.5,leading=15))]
        metas=[]
        if cmp.get("objetivo_ingresos"): metas.append("Mis ingresos medios serán, como mínimo, de <b>%s/mes</b>."%_eur(cmp["objetivo_ingresos"]))
        if cmp.get("numero_libertad"):
            pl=(" — mi horizonte: <b>%d años</b>"%cmp["plazo_anios"]) if cmp.get("plazo_anios") else ""
            metas.append("Mi número de libertad <b>para la vida que quiero</b> es <b>%s</b>%s. Cada decisión me acerca o me aleja de él."%(_eur(cmp["numero_libertad"]),pl))
        if metas:
            inner.append(Paragraph("<font color='#B45309'><b>MIS OBJETIVOS IRRENUNCIABLES</b></font>",St("c1",fontSize=9.8,leading=14,spaceBefore=7)))
            for m in metas: inner.append(Paragraph("&#9656;  %s"%m,St("c2",fontSize=9.7,leading=14,leftIndent=8,spaceAfter=1)))
        inner.append(Paragraph("<font color='#B45309'><b>%s</b></font>"%("MIS TRES PASOS" if cmp.get("crisis") else "MIS REGLAS NO NEGOCIABLES"),St("c3",fontSize=9.8,leading=14,spaceBefore=7)))
        for r in (cmp.get("reglas") or []):
            inner.append(Paragraph("&#9656;  %s"%r,St("c4",fontSize=9.7,leading=14,leftIndent=8,spaceAfter=1)))
        inner.append(Paragraph(("Un paso cada vez. No se trata de hacerlo perfecto, sino de no rendirme: sostener estos tres, hoy, es suficiente." if cmp.get("crisis") else "No habrá excusas. Mi futuro dependerá de mis decisiones presentes. La disciplina de hoy es la libertad de mañana."),St("c5",fontSize=9.7,leading=14,spaceBefore=7)))
        out+=[Spacer(1,3*mm), _box(inner,"#FBF4E4","#B45309",ancho=164*mm)]
        firmas=Table([[Paragraph("________________________<br/><font size=8 color='#6B7280'>MI YO PRESENTE</font>",small),
                       Paragraph("________________________<br/><font size=8 color='#6B7280'>MI YO FUTURO</font>",small)]],colWidths=[80*mm,80*mm])
        firmas.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),14),("ALIGN",(0,0),(-1,-1),"CENTER")]))
        out+=[Spacer(1,6*mm),firmas]
    return out


def seccion_coste_inaccion(extras):
    """Cierre de alto impacto: cuantifica el coste de no actuar con numeros REALES del cliente."""
    if not extras: return []
    br=extras.get("brecha"); items=[]
    if br and (br.get("brecha_mes") or 0)>0:
        items.append("Cada mes en tu modelo actual, la vida que dijiste querer se aleja <b>%s</b> — son <b>%s al año</b> que tu trayectoria todavía no genera." % (_eur(br["brecha_mes"]), _eur(br["brecha_anual"])))
    if extras.get("herencia"):
        items.append("Una sucesión sin planificar puede dejar a los tuyos una factura fiscal que <b>hoy todavía es evitable</b>; cuanto más tarde se mira, menos margen queda.")
    if extras.get("asesor"):
        a=extras["asesor"][0].lower()
        if "gestoría" in a or "sin red" in a:
            items.append("Cada trimestre con asesoría que solo hace papeleo es optimización que se queda sin hacer: dinero que se va en impuestos o comisiones por falta de un plan, no de capacidad.")
    if extras.get("conciliacion"):
        items.append("Y el coste que no aparece en ninguna cuenta: cada semana sin cambiar el sistema es tiempo de presencia con los tuyos — el único capital que no se reconstruye.")
    if not items: return []
    out=[PageBreak(), Paragraph("El coste de no hacer nada",h_sec),
         Paragraph("Un diagnóstico sin acción es solo información cara. Esto es lo que te cuesta, en concreto, cada mes que el cuadro sigue igual:",body)]
    for it in items:
        out.append(Paragraph("<font color='#9A3B2E'>&#9656;</font>  "+it,St("ci",fontSize=10.5,leading=15,leftIndent=6,spaceAfter=7)))
    out.append(Paragraph("Cada una de estas cifras es reversible — y ninguna depende del mercado ni de la suerte, sino "
               "de ti. No se trata de hacerlo todo de golpe: se trata de hacer <b>UNA</b> cosa —la primera de tu plan— "
               "antes de que termine el día. Porque quien lee esto y mañana sigue exactamente igual no ha pagado por un "
               "diagnóstico: ha pagado por una excusa más cara. La diferencia entre los dos no está en la página "
               "siguiente — está en si te levantas de la silla <b>ahora</b>.",
               St("cic",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=10,spaceBefore=4)))
    return out

def seccion_numero_realista(datos, extras):
    """Art. 7: no se da una meta inalcanzable sin decir que la haria alcanzable. Si a su ritmo de
    ahorro el numero son decadas, se nombra: no se llega ahorrando, sino cambiando de fase de ingresos.
    Solo aparece cuando aplica. Failsafe."""
    d=datos or {}; ex=extras or {}
    N=(ex.get("brecha") or {}).get("numero_canonico")
    try:
        N=float(N); aho=float(d.get("ahorro_mensual") or 0); pat=float(d.get("patrimonio") or 0)
    except Exception:
        return []
    if not N or N<=0 or aho<=0:
        return []
    falta=max(0.0,N-pat)
    anios=falta/(aho*12.0)
    if anios<40:
        return []
    return [Spacer(1,3*mm),
            _box([Paragraph("UN NÚMERO HONESTO",St("nr0",fontSize=8.5,leading=11,textColor=colors.HexColor("#9A3B2E"),fontName=FB)),
                  Paragraph("Tu número de libertad es real, pero conviene decirlo sin rodeos: a tu ritmo de ahorro de hoy "
                            "(<b>%s/mes</b>), llegar a él tomaría del orden de <b>%d años</b>. Eso significa que <b>no se "
                            "alcanza ahorrando</b> —ningún recorte de gastos cierra esa distancia—: se alcanza <b>cambiando "
                            "de fase de ingresos</b>: subir lo que generas, poner a trabajar tu patrimonio, o crear una "
                            "fuente que no dependa de tu tiempo. Ese, y no apretarte el cinturón, es el verdadero trabajo."
                            %(_eur(aho), int(round(anios))),St("nr1",fontSize=10.5,leading=15,textColor=colors.HexColor("#2C313A"),spaceBefore=3))],
                 "#FBEDEC","#9A3B2E",ancho=160*mm),
            Spacer(1,3*mm)]


def seccion_alertas_perfil(datos):
    """Consume las preguntas nuevas (cotizacion, venta de empresa, perfil de riesgo, testamento)
    y emite SOLO las alertas que apliquen a este cliente. Aditivo y failsafe."""
    d=datos or {}
    out=[]
    def _alerta(titulo, texto, bg="#FBF6E6", borde="#C9962B"):
        out.append(Spacer(1,3*mm))
        out.append(_box([Paragraph(titulo,St("ap_h%d"%len(out),fontSize=12.5,leading=16,textColor=colors.HexColor("#1A1A17"),fontName=FB)),
                         Paragraph(texto,St("ap_t%d"%len(out),fontSize=10.5,leading=15,textColor=colors.HexColor("#2C313A"),spaceBefore=3))],
                        bg,borde,ancho=160*mm))
    try:
        bc=str(d.get("base_cotizacion") or "")
        if "mínima" in bc.lower() or "minima" in bc.lower():
            _alerta("Cotizas al mínimo. Tu yo de mañana paga la factura.",
                    "Cotizar al mínimo abarata tu cuota de hoy y vacía tu pensión de mañana. Al jubilarte, tus "
                    "ingresos pueden caer <b>más del 50%</b> de golpe. La pensión es un suelo, no un plan: el "
                    "complemento lo construyes tú, y cuanto antes empieces, menos esfuerzo te costará.","#FBEDEC","#9A3B2E")
        iv=str(d.get("intencion_venta") or "")
        if "próximos años" in iv.lower() or "proximos años" in iv.lower() or "largo plazo" in iv.lower():
            _alerta("Vas a vender tu empresa. Eso se prepara antes, no después.",
                    "El mayor riesgo tras una venta no es invertir mal: es no tener un plan listo cuando llega el "
                    "dinero. La fiscalidad de la operación, los objetivos y la inversión por fases <b>se deciden "
                    "antes de firmar</b> — el día del ingreso ya es tarde para optimizar.")
        pr=str(d.get("perfil_riesgo") or "").lower()
        if "conservador" in pr:
            _alerta("Tu perfil es conservador. Conviene que sea una elección, no un miedo.",
                    "Priorizar no perder es legítimo, pero tiene un coste silencioso: a largo plazo, un perfil muy "
                    "conservador suele <b>perder poder adquisitivo frente a la inflación</b>. Si el horizonte es largo, "
                    "merece la pena revisar si ese perfil te protege de verdad o solo te protege del susto a corto.")
        elif "no lo tengo claro" in pr or "no me lo he planteado" in pr:
            _alerta("No tienes definido tu perfil de inversión. Ese vacío decide por ti.",
                    "Sin un perfil claro, las decisiones se toman por impulso — comprar en la euforia, vender en el "
                    "pánico. Definir tu perfil (cuánto vaivén toleras a cambio de cuánta rentabilidad esperada) es "
                    "el primer paso para que tu dinero trabaje según tu plan, no según el titular del día.")
        tt=str(d.get("testamento") or "")
        if "no tengo" in tt.lower():
            _alerta("No tienes testamento. Hoy decide la ley, no tú.",
                    "Sin testamento, el reparto de lo que has construido lo marca el Código Civil, no tu voluntad. "
                    "Es la decisión patrimonial <b>más barata y la más aplazada</b> — y con hijos, la que más "
                    "tranquilidad compra por menos dinero.","#FBEDEC","#9A3B2E")
    except Exception:
        return out
    if out: out.append(Spacer(1,2*mm))
    return out


def seccion_incapacidad(datos):
    """Consume la pregunta nueva seguro_incapacidad: para un profesional liberal sin cobertura,
    nombra su mayor riesgo. Solo aparece si aplica. Failsafe."""
    d=datos or {}
    pl=str(d.get("perfil_laboral") or "")
    seg=str(d.get("seguro_incapacidad") or "")
    es_liberal=("Autónomo" in pl) or ("empresa propia" in pl) or ("SL" in pl)
    sin_cobertura=("No tengo nada" in seg) or ("Solo lo público" in seg) or ("mutualidad" in seg.lower())
    if not (es_liberal and sin_cobertura):
        return []
    _det=("solo cuentas con la cobertura pública (mutualidad o Seguridad Social), que cubre poco"
          if "público" in seg.lower() or "mutualidad" in seg.lower() else "no tienes ningún seguro específico")
    return [Spacer(1,3*mm),
            _box([Paragraph("TU MAYOR RIESGO, HOY SIN CUBRIR",St("inc0",fontSize=8.5,leading=11,textColor=colors.HexColor("#9A3B2E"),fontName=FB)),
                  Paragraph("Tu patrimonio depende de una sola cosa: que puedas seguir ejerciendo.",St("inc1",fontSize=13,leading=17,textColor=colors.HexColor("#1A1A17"),fontName=FB,spaceBefore=2)),
                  Paragraph("Si mañana una enfermedad o un accidente te lo impidieran, <b>%s</b>. Para un profesional "
                            "liberal ese es el riesgo número uno —y de los más baratos de cerrar antes de que llegue—. "
                            "No es urgente porque duela hoy; es urgente porque el día que importe, ya será tarde para contratarlo."%_det,
                            St("inc2",fontSize=10.5,leading=15,textColor=colors.HexColor("#2C313A"),spaceBefore=4))],
                 "#FBEDEC","#9A3B2E",ancho=160*mm),
            Spacer(1,3*mm)]


def seccion_como_medimos(extras):
    """Art. 3 de la Constitución: declara EN VOZ ALTA el marco único de medición, una vez y visible.
    Autoridad = elegir el patrón y decirlo, no oscilar. Failsafe."""
    ex=extras or {}
    br=ex.get("brecha") or {}
    ci=br.get("coste_ideal_mes")
    try: _ci=("%s/mes"%_eur(ci)) if ci else "tu vida ideal declarada"
    except Exception: _ci="tu vida ideal declarada"
    reglas=[
        ("Escenario", "planificamos sobre <b>la vida que quieres</b> (%s), no sobre tu gasto de hoy." % _ci),
        ("Unidad", "todas las cifras en <b>euros de hoy</b>; si alguna es a futuro, se etiqueta."),
        ("Colchón objetivo", "<b>6 meses</b> de gasto. Una sola definición en todo el documento."),
        ("Regla de libertad", "<b>4% = regla 25×</b> (son lo mismo), ajustada por la fiscalidad española."),
        ("Valor de tu hora", "una sola base de cálculo, coherente en todas las páginas."),
    ]
    filas=[Paragraph("<b>%s:</b> %s"%(k,v),St("cm%d"%i,fontSize=10,leading=14,spaceBefore=2)) for i,(k,v) in enumerate(reglas)]
    return [Spacer(1,3*mm),
            _box([Paragraph("CÓMO MEDIMOS",St("cmh",fontSize=9,leading=12,textColor=colors.HexColor("#0284C7"),fontName=FB)),
                  Paragraph("Para que confíes en cada número, estas son nuestras reglas — las mismas en todo el informe:",
                            St("cmi",fontSize=10,leading=14,spaceBefore=2,spaceAfter=2))]+filas,
                 "#F4F8FB","#0284C7",ancho=160*mm),
            Spacer(1,3*mm)]


def seccion_paradoja(extras):
    """EL HALLAZGO ESTRELLA (multi-área): cada punto donde el dato dice una cosa y la emoción
    la contraria. El motor devuelve una LISTA; las renderizamos todas. Failsafe."""
    pars=(extras or {}).get("paradoja")
    if isinstance(pars, dict): pars=[pars]          # compatibilidad con versión anterior
    if not pars: return []
    out=[Spacer(1,4*mm),
         Paragraph("Donde tu dinero y tu cabeza no dicen lo mismo", h_sec),
         Paragraph("El hallazgo más valioso de tu diagnóstico no es una cifra: es la distancia entre lo que "
                   "tienes y lo que sientes. Un banco solo mira el número; nosotros miramos a la persona entera.", body),
         Spacer(1,3*mm)]
    for par in pars:
        out.append(_box([Paragraph(par.get("titulo",""),St("parx1",fontSize=13,leading=17,textColor=colors.HexColor("#1A1A17"),fontName=FB)),
                         Paragraph(par.get("texto",""),St("parx2",fontSize=10.5,leading=15,textColor=colors.HexColor("#2C313A"),spaceBefore=4))],
                        "#FBF6E6","#C9962B",ancho=160*mm))
        out.append(Spacer(1,3*mm))
    return out


def seccion_resumen_ejecutivo(extras, datos):
    """Resumen ejecutivo de 1 pagina tras la portada: cifras clave + foco + primer paso + puente Adapta."""
    if not extras: return []
    rv=extras.get("ratio_vida"); nudo=extras.get("nudo"); res=extras.get("resiliencia"); acc=extras.get("accion_unica")
    out=[PageBreak(), Paragraph("Tu diagnóstico en una página", h_sec),
         Paragraph("Si solo lees esto, ya sabrás lo esencial. El resto del libro es el porqué, el cuánto y el cómo.", body),
         Spacer(1,5*mm)]
    _lbl=St("relbl",fontSize=9,leading=12,textColor=colors.HexColor("#6B7280"))
    cells=[]
    if rv:
        _bc="#1D6F42" if rv["iri"]>=60 else ("#C2710C" if rv["iri"]>=40 else "#9A3B2E")
        cells.append([Paragraph("Tu Ratio de Vida",_lbl),Paragraph("<b>%d</b><font size=11 color='#6B7280'>/100</font>"%rv["iri"],St("ren1",fontSize=26,leading=30,textColor=colors.HexColor(_bc),fontName=FB))])
    if res and res.get("meses_libertad") is not None:
        _m=res["meses_libertad"]; _mt=("%.0f meses"%_m) if _m<24 else ("%.1f años"%(_m/12.0))
        cells.append([Paragraph("Meses de libertad",_lbl),Paragraph("<b>%s</b>"%_mt,St("ren2",fontSize=20,leading=26,textColor=INK,fontName=FB))])
    if rv:
        cells.append([Paragraph("Tu eslabón más débil",_lbl),Paragraph("<b>%s</b>"%rv["weakest"],St("ren3",fontSize=20,leading=26,textColor=colors.HexColor("#9A3B2E"),fontName=FB))])
    if cells:
        w=160.0/len(cells)
        out+=[Table([cells],colWidths=[w*mm]*len(cells),style=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),2)]),Spacer(1,5*mm)]
    if nudo and nudo.get("principal"):
        pr=nudo["principal"]
        out+=[_box([Paragraph("<font color='#9A3B2E'><b>TU FOCO PRINCIPAL</b></font>  "+pr["tit"]+".",St("ref",fontSize=11,leading=16,textColor=INK))],"#FBF4E4","#9A3B2E",ancho=160*mm),Spacer(1,3*mm)]
    if acc and isinstance(acc,str):
        out+=[_box([Paragraph("<font color='#1D6F42'><b>TU PRIMER PASO</b></font>  "+acc,St("rea",fontSize=11,leading=16,textColor=INK))],"#EAF3EC","#1D6F42",ancho=160*mm)]
    _foco = (nudo and nudo.get("principal") and nudo["principal"].get("tit")) or (rv and rv.get("weakest"))
    if _foco:
        out+=[Spacer(1,4*mm),
              Paragraph("En tu sesión con <b>Adapta</b> empezaríamos justo por aquí: convertir este foco en un plan concreto, con números y fechas. El diagnóstico te dice <i>qué</i>; nosotros lo recorremos <i>contigo</i>.",
                        St("reb",fontSize=10,leading=14,textColor=GREY))]
    out+=[PageBreak()]
    return out

def seccion_fiabilidad(extras):
    """Escala de validez: cuanto fiarse del retrato. Banda + indice 0-100.
    Devuelve [] si no hay dato (nunca rompe)."""
    v=(extras or {}).get("validez")
    if not v: return []
    pal={"alta":("#EAF3EC","#1D6F42"),"media":("#FBF4E4","#C2710C"),
         "revisar":("#FBECE8","#9A3B2E"),"parcial":("#F3F4F6","#6B7280")}
    bg,col=pal.get(v.get("banda"),pal["media"])
    et=v.get("etiqueta",""); idx=v.get("indice")
    cab="<font color='%s'><b>LA FIABILIDAD DE TU DIAGNÓSTICO</b></font>"%col
    if et: cab+="  ·  <font color='%s'><b>%s</b></font>"%(col,et.upper())
    if idx is not None: cab+="  ·  <font color='#6B7280'>%d/100</font>"%idx
    parr=[Paragraph(cab,St("fi0",fontSize=9.5,leading=13)),
          Paragraph("<b>%s.</b>  %s"%(v.get("titulo","").rstrip("."), v.get("texto","")),
                    St("fi1",fontSize=10.5,leading=15,textColor=INK,spaceBefore=3))]
    return [_box(parr,bg,col,ancho=160*mm), PageBreak()]

def _realidad(p, datos):
    """Guardarrail de coherencia: si la realidad numerica dura contradice la nota de la escala, la capa.
    Solo se activa en casos inequivocos (no afecta a perfiles normales)."""
    try:
        ing=float(datos.get("ingreso_mensual") or 0); gas=float(datos.get("gasto_mensual") or 0)
        if ing>0 and (ing-gas)/ing<=0.0 and "C4" in p and p["C4"]["score"]<55:
            p["C4"]["score"]=55; bi,bl=banda(CAPAS["C4"],55); p["C4"]["bi"]=bi; p["C4"]["banda"]=bl
        invl=datos.get("inversiones_liquidas"); pat=float(datos.get("patrimonio") or 0)
        aho=float(datos.get("ahorro_mensual") or 0)
        if invl is not None and float(invl)<=0 and pat>0 and "C2" in p:
            fac=p["C2"].get("facetas") or {}
            if fac.get("inversion",0)<55: fac["inversion"]=55
            if p["C2"]["score"]<50:
                p["C2"]["score"]=50; bi,bl=banda(CAPAS["C2"],50); p["C2"]["bi"]=bi; p["C2"]["banda"]=bl
        # C12 Disciplina de Inversion: sin nada invertido en mercados (RV/RF) no hay disciplina inversora probada.
        # inversiones_liquidas ya solo cuenta lo invertido de verdad (no c/c ni depositos -> esos van a colchon_liquido).
        if "C12" in p and float(invl or 0)<=0 and p["C12"]["score"]<50:
            p["C12"]["score"]=50; bi,bl=banda(CAPAS["C12"],50); p["C12"]["bi"]=bi; p["C12"]["banda"]=bl
        # C9 Gobierno del Flujo de Caja: gastar todo lo que entra contradice un gobierno de flujo perfecto
        if ing>0 and (ing-gas)/ing<=0.0 and "C9" in p and p["C9"]["score"]<50:
            p["C9"]["score"]=50; bi,bl=banda(CAPAS["C9"],50); p["C9"]["bi"]=bi; p["C9"]["banda"]=bl
    except Exception:
        pass
    return p

def seccion_salud_porcentajes(datos):
    """Juicio de salud sobre los porcentajes que el motor DERIVA del desglose (no de una pregunta cualitativa):
    peso de suscripciones sobre el gasto y concentracion de ingresos sobre la fuente dominante.
    Vivienda, DTI, concentracion patrimonial e ingresos pasivos ya se comentan en el cuadro financiero,
    asi que aqui solo se anade lo que NO esta cubierto. Aditivo y failsafe."""
    d=datos or {}
    out=[]
    def _g(k):
        try: return float(d.get(k))
        except Exception: return None
    def _caja(titulo,texto,bg,borde):
        out.append(Spacer(1,3*mm))
        out.append(_box([Paragraph(titulo,St("sp_h%d"%len(out),fontSize=12,leading=15,textColor=colors.HexColor("#1A1A17"),fontName=FB)),
                         Paragraph(texto,St("sp_t%d"%len(out),fontSize=10.5,leading=15,textColor=colors.HexColor("#2C313A"),spaceBefore=3))],
                        bg,borde,ancho=160*mm))
    # Suscripciones: peso de la categoria del desglose de gasto. <5% sano; 5-10% vigilar; >10% goteo serio.
    sus_pct=_g("suscripciones_pct"); sus_eur=_g("suscripciones_eur")
    if sus_pct is not None and sus_eur and sus_eur>0:
        _anual=_eur(sus_eur*12)
        if sus_pct>=10:
            _caja("Tus suscripciones pesan más de lo que crees",
                  "Las suscripciones y servicios recurrentes se llevan el <b>%.0f%%</b> de tu gasto mensual — del orden de "
                  "<b>%s al año</b>. El problema no es el importe de cada una, es que se renuevan solas y dejas de "
                  "notarlas. Audita la lista de una sentada y cancela todo lo que no hayas usado este mes: ese euro "
                  "recurrente, invertido, trabaja para ti en vez de para otros."%(sus_pct,_anual),"#FBEDEC","#9A3B2E")
        elif sus_pct>=5:
            _caja("Vigila el goteo de tus suscripciones",
                  "Tus suscripciones suman el <b>%.0f%%</b> de tu gasto (unos <b>%s al año</b>). No es alarmante, pero es "
                  "la clase de gasto que crece sin que lo decidas. Una revisión anual de la lista basta para mantenerlo a "
                  "raya."%(sus_pct,_anual),"#FBF6E6","#C9962B")
    # Concentracion de ingresos: peso de la fuente dominante (derivado del desglose de ingresos).
    # Complementa el mapa de fuentes con el dato exacto de cuanto cuelga de un solo hilo.
    conc=_g("concentracion_ingresos"); nf=_g("n_fuentes_ingreso")
    if conc is not None and nf is not None and nf>=2 and conc>=65:
        _caja("Tienes varias fuentes, pero una manda demasiado",
              "Sobre el papel diversificas, pero una sola fuente concentra el <b>%.0f%%</b> de lo que ingresas. "
              "Diversificar de verdad no es tener varias fuentes: es que ninguna pueda hundirte ella sola. "
              "El siguiente paso es engordar la segunda, no abrir una décima."%conc,"#FBF6E6","#C9962B")
    if out: out.append(Spacer(1,2*mm))
    return out

def _secsafe(fn, *a, **k):
    """Red de seguridad: si una seccion falla, se salta y se registra — nunca tumba el PDF entero."""
    try:
        return fn(*a, **k) or []
    except Exception as _e:
        import sys, traceback
        sys.stderr.write("[secsafe] seccion %s fallo (se omite): %s\n" % (getattr(fn,"__name__","?"), _e))
        traceback.print_exc()
        return []

def seccion_dictamen_comportamiento(resp):
    """Convierte el test (preguntas de comportamiento) en DICTAMEN ejecutivo: encabezado + etiqueta
    de diagnóstico en bronce + prosa de consultor. No sustituye el anexo de transparencia: lo precede
    con la lectura, no con el formulario. Aditivo y failsafe.
    Etiquetas por puntuación de la respuesta elegida (score 0-100, mayor=peor):
      <=35 [SÓLIDA] · 36-60 [A VIGILAR] · >60 etiqueta crítica específica."""
    # Robusto a v1/v2: se busca por PALABRAS CLAVE en el texto de la pregunta (los IDs cambian entre
    # instrumentos). Cada foco: (keywords_obligatorias, encabezado, etiqueta crítica, dictamen).
    FOCO=[
      (("constancia","inviert"),"Frecuencia de inversión","INACTIVA",
       "El perfil denota ausencia de aportaciones recurrentes. Sin una cadencia fija, el interés compuesto —el único motor que construye patrimonio sin esfuerzo adicional— no llega a activarse: cada mes sin aportar es crecimiento que no se recupera."),
      (("plan","horizonte"),"Plan de inversión","SIN RUMBO",
       "Las decisiones de inversión carecen de un marco definido de plazo y riesgo. Sin plan, la cartera la dirige el titular del día: se compra en la euforia y se vende en el pánico, justo al revés de lo que construye valor."),
      (("invertido","parado"),"Capital puesto a trabajar","PARADO",
       "Una parte del capital que no necesitas a corto plazo permanece ocioso. Dinero quieto pierde poder adquisitivo cada año frente a la inflación: no es prudencia, es un coste silencioso."),
      (("sistema","repartir"),"Arquitectura de cuentas","DIFUSA",
       "No existe una separación operativa del dinero (operativa, contingencia, inversión). Cuando todo convive en una cuenta, el excedente se diluye en el gasto antes de poder asignarse con intención."),
      (("escapa","mes"),"Control del flujo","CON FUGAS",
       "Hay un margen mensual que no cuadra. Lo que no se mide, no se gobierna: esa fuga, sostenida, es de los primeros frenos a corregir porque no exige ganar más, solo ver mejor."),
      (("relación con la deuda",),"Relación con la deuda","TENSIONADA",
       "La deuda convive con cierta tensión. Mientras exista financiación cara, amortizarla rinde más —y con certeza— que casi cualquier inversión: es la prioridad técnica antes de crecer."),
    ]
    try:
        items=[]
        for capa in INST["capas"]:
            if capa.get("code") not in ("C9","C10","C11","C12"): continue
            for it in capa["items"]:
                if it.get("tipo")=="escala" and not it.get("atencion"):
                    items.append(it)
    except Exception:
        return []
    def _match(kws):
        for it in items:
            tx=(it.get("texto") or "").lower()
            if all(k in tx for k in kws): return it
        return None
    filas=[]; _vistos=set()
    for kws,titulo,etiq_crit,dict_crit in FOCO:
        it=_match(kws)
        if not it or it["id"] in _vistos: continue
        idx=resp.get(it["id"])
        if idx is None: continue
        try: sc=it["opciones"][idx]["score"]
        except Exception: continue
        if sc<=35: continue   # fortaleza: no la convertimos en alarma
        _vistos.add(it["id"])
        if sc<=60: etiq="A VIGILAR"; col="#9A7B1F"
        else: etiq=etiq_crit; col="#9A3B2E"
        filas.append((titulo,etiq,col,dict_crit))
    if not filas: return []
    out=[PageBreak(), Paragraph("El dictamen de tu comportamiento financiero", h_sec),
         Paragraph("Tus respuestas no son un test con nota: son la radiografía de tus hábitos. Esto es lo que dicen, "
                   "leídas como las leería tu consultor — sin rodeos y por orden de impacto.", body),
         Spacer(1,4*mm)]
    for titulo,etiq,col,txt in filas:
        out.append(Table([[Paragraph("<b>%s</b>"%titulo,St("dcb_t%d"%len(out),fontSize=12,leading=15,textColor=ACCDK,fontName=FB)),
                           Paragraph("[%s]"%etiq,St("dcb_e%d"%len(out),fontSize=9,leading=12,textColor=colors.HexColor(col),fontName=FB,alignment=TA_LEFT))]],
                  colWidths=[110*mm,50*mm],
                  style=TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),
                    ("BOTTOMPADDING",(0,0),(-1,-1),1)])))
        out.append(Paragraph(txt,St("dcb_x%d"%len(out),fontSize=10,leading=14,textColor=INK,spaceBefore=1,spaceAfter=6)))
        out.append(Table([[""]],colWidths=[160*mm],style=[("LINEBELOW",(0,0),(-1,-1),0.4,LINE)]))
        out.append(Spacer(1,3*mm))
    return out

def seccion_coste_inflacion(datos):
    """Cuantifica en € lo que pierde el capital ocioso cada año contra la inflación, y nombra la
    optimización fiscal como palanca. Solo aparece si hay liquidez parada relevante. Aditivo y failsafe."""
    d=datos or {}
    try:
        tap=tapon_coste(d)
    except Exception:
        tap=None
    if not tap: return []
    exceso, _ = tap
    INFL=0.03
    perdida=exceso*INFL
    return [Spacer(1,3*mm),
            _box_sello([Paragraph("El coste de tu capital ocioso",St("cinf_h",fontSize=12,leading=15,textColor=ACCDK,fontName=FB)),
                  Paragraph("Tienes alrededor de <b>%s</b> en liquidez por encima de un colchón sano. A una inflación del 3%%, "
                            "ese dinero pierde del orden de <b>%s al año</b> de poder de compra solo por estar parado — sin que "
                            "nada malo ocurra. No es una pérdida que veas en el extracto; es una que descubres cuando lo que antes "
                            "comprabas con esa cifra ya no lo cubre."%(_eur(exceso),_eur(perdida)),
                            St("cinf_t",fontSize=10,leading=14,textColor=INK,spaceBefore=3)),
                  Paragraph("<b>Dos palancas, no una:</b> poner ese excedente a rentar al menos lo que sube la vida, y revisar la "
                            "<b>capa fiscal</b> de cómo lo haces (vehículo, diferimiento, traspasos). La rentabilidad financiera y "
                            "la eficiencia fiscal se suman: ignorar la segunda regala cada año una parte de la primera a Hacienda.",
                            St("cinf_f",fontSize=10,leading=14,textColor=INK,spaceBefore=4))],
                 "#FBF4E4","#B45309",nota="C",ancho=160*mm),
            Spacer(1,2*mm)]

def build(cli,resp,datos,out,depth="completo",baremo=None,sintesis=None,extras=None,arq_override=None):
    p,tr,salud=perfil(resp); p=_realidad(p,datos)
    salud=round(statistics.mean([v["score"] for v in p.values()]),1)
    fi=fi_metrics(datos); radar_png(p,"_radar.png")
    _cohorte=cohorte_txt(cli,datos)
    if baremo and baremo.get("pct") is not None:
        _pct_frase="mejor que el %d%% de %s" % (round(baremo["pct"]), _cohorte)
        _pct_nota=" \u00b7 muestra real: %d diagn\u00f3sticos" % baremo["n"]
    else:
        _pct_frase="una lectura objetiva de tu relaci\u00f3n con el dinero a trav\u00e9s de 12 dimensiones psicofinancieras"
        _pct_nota=""
    bi,bl=banda(CAPAS["C1"],salud); S=[]
    coh=coherencia(salud,fi,datos)
    arq_code = arq_override if arq_override is not None else arquetipo(resp)[0]
    # cover + apertura cinematográfica (Legado: navy + azul eléctrico, datos reales)
    _hero=None
    try:
        if _LEGADO_OK and extras: _hero=_legado_pages.hero_open(cli,datos,extras,p,depth=depth,arq_meta=ARQ_META.get(arq_code))
    except Exception:
        _hero=None
    if _hero:
        for _pg in _hero: S+=[FullBleedImage(_pg), PageBreak()]
    if not _hero: S+=[Spacer(1,34*mm),
        Paragraph("TU LIBRO FINANCIERO",St("cv0",fontSize=12,textColor=GREY,fontName=FB)),
        Spacer(1,3*mm),
        Paragraph("Diagnóstico<br/>Patrimonial",St("cv1",fontSize=40,leading=44,textColor=INK,fontName=FB)),
        Spacer(1,5*mm),
        Table([[""]],colWidths=[60*mm],style=[("LINEBELOW",(0,0),(-1,-1),4,AMARILLO)]),
        Spacer(1,7*mm),
        Paragraph("Una lectura honesta de tu relación con el dinero, capa por capa.",St("cv2",fontSize=12,textColor=ACCDK)),
        Spacer(1,40*mm),
        Paragraph(f"Perfil  \u00b7  <b>{_edad_txt(datos)}</b>",St("cvn",fontSize=12)),
        Paragraph(cli["email"],small), Paragraph(cli["fecha"],small),
        Spacer(1,3*mm), Paragraph(("Diagnóstico Rápido · Tier 1" if depth=="esencial" else "Informe Avanzado · Tier 2"),St("cvt",fontSize=9.5,textColor=ACC,fontName=FB)),
        Spacer(1,16*mm),
        Paragraph(f"DOCUMENTO CONFIDENCIAL · REF {report_id(cli.get('email') or 'ITAP',cli['fecha'])} · USO PRIVADO",
                  St("cvr",fontSize=7.5,textColor=GREY,fontName="Helvetica")),
        PageBreak()]
    # carta de apertura
    S+=[Paragraph("Antes de empezar",h_sec),
        _box([Paragraph("<font color='#234E70'><b>&#9656;  Eres de los primeros — y lo afinamos contigo</b></font>",St("fbk1",fontSize=11,leading=15,fontName=FB)),
              Paragraph("Respaldamos cada cifra de este informe. Y como eres de nuestros primeros clientes, lo construimos también contigo: si al leerlo ves algún número o conclusión que no te encaje, escríbenos a <font color='#234E70'><b>info@adaptafamilyoffice.com</b></font>. Lo revisamos al momento, lo corregimos y te reenviamos tu informe actualizado, sin coste. Tu mirada lo hace mejor — para ti y para quienes vengan detrás.",St("fbk2",fontSize=10,leading=15,spaceBefore=2,textColor=INK))],
             "#EEF2F6","#234E70",ancho=160*mm),
        Spacer(1,4*mm),
        Paragraph("Este libro no es un cuestionario más ni una sentencia. "
                  "Es un espejo. Cada página nace de tus propias respuestas y las ordena para que veas, sin ruido, "
                  "dónde tu dinero te sostiene y dónde te pesa.",body),
        Paragraph("Lo hemos escrito como un libro, no como una ficha, porque tu vida financiera no se entiende con "
                  "un solo número. Se entiende como una historia con capítulos: tu salud emocional con el dinero, tu "
                  "libertad, tu resistencia a los golpes, tu deuda, tu manera de gastar y de protegerte. Cada capítulo "
                  "te dice qué mide, qué ha salido, qué significa para ti y cuál es tu siguiente paso.",body),
        Paragraph("No se trata de aprobar o suspender: esto fija la línea de base de tu eficiencia patrimonial, el punto desde el que se construye. Léelo con calma, en orden. Al final "
                  "tendrás un mapa y un plan.",body),
        Spacer(1,4*mm),
        Paragraph("Una nota de cuidado: este libro es una herramienta de autoconocimiento, no asesoramiento "
                  "individualizado ni atención psicológica. Si el dinero te genera un malestar que te desborda, "
                  "apóyate también en un profesional de confianza.",small),
        PageBreak()]
    # === PANEL FINANCIERO ===
    try:
        _inv=float(datos.get("inversiones_liquidas") or 0); _par=float(datos.get("colchon_liquido") or 0)
        _pat=float(datos.get("patrimonio") or 0); _ili=max(0.0,_pat-_inv-_par)
        _ing=float(datos.get("ingreso_mensual") or 0); _ipas=min(float(datos.get("renta_pasiva") or 0),_ing); _iact=max(0.0,_ing-_ipas)
        _gas=float(datos.get("gasto_mensual") or 0); _pf=float(datos.get("pct_gasto_fijo") or 0)
        _gfij=min(_gas,(_gas*_pf/100.0) if _pf>0 else (float(datos.get("coste_vivienda") or 0)+float(datos.get("cuota_deuda") or 0))); _gvar=max(0.0,_gas-_gfij)
        panel_dashboard("_panel.png", 100-salud, bl, fi[0], fi[1] or 0, fi[2] or 0, _inv,_par,_ili, _iact,_ipas, _gfij,_gvar, _ili, cli.get("fecha",""))
        S+=[FullBleedImage("_panel.png"), PageBreak()]
        try:
            _dp=panel_distribucion("_distrib.png", datos, extras, cli.get("fecha",""))
            for _pg in (_dp if isinstance(_dp,list) else ["_distrib.png"]):
                S+=[FullBleedImage(_pg), PageBreak()]
        except Exception as _ed:
            import sys; sys.stderr.write("[distrib] omitida: %s\n"%_ed)
        if depth!="esencial":
            panel_capas("_capas.png", p)
            S+=[FullBleedImage("_capas.png"), PageBreak()]
    except Exception:
        pass
    # === Indice: el mapa de los 5 actos ===
    _ix=[("APERTURA","Portada · carta de bienvenida"),
         ("ACTO 1 · DIAGNÓSTICO","Tu foto de hoy: radar, las 12 capas y tu síntesis financiera"),
         ("ACTO 2 · LA BRECHA","Vida ideal vs actual · palancas · el coste de no hacer nada"),
         ("ACTO 3 · EL PLAN","Tu Constitución financiera: hoja de ruta a 72 h / 30 / 90 días"),
         ("ACTO 4 · ADAPTA","El siguiente paso: ejecución con tu family office"),
         ("ANEXOS","Glosario · tus respuestas · metodología")]
    S+=[Paragraph("El mapa de tu libro",h_sec),
        Paragraph("Seis tramos, un solo recorrido: del diagnóstico a la acción. Léelo en orden.",body),Spacer(1,5*mm)]
    for _t,_d in _ix:
        S.append(Table([[Paragraph("<b>%s</b>"%_t,St("ixt",fontSize=11,leading=14,textColor=ACCDK,fontName=FB)),
                         Paragraph(_d,St("ixd",fontSize=9.6,leading=13,textColor=GREY))]],
                 colWidths=[54*mm,106*mm],
                 style=[("LINEBELOW",(0,0),(-1,-1),0.5,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                        ("LINEBEFORE",(0,0),(0,-1),2.6,AMARILLO),("LEFTPADDING",(0,0),(0,-1),10),
                        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)]))
    S+=[PageBreak()]
    if extras: S+=_secsafe(seccion_resumen_ejecutivo,extras,datos)
    if extras: S+=_secsafe(seccion_como_medimos,extras)
    if extras: S+=_secsafe(seccion_paradoja,extras)
    S+=_secsafe(seccion_incapacidad,datos)
    S+=_secsafe(seccion_alertas_perfil,datos)
    S+=_secsafe(seccion_salud_porcentajes,datos)
    S+=_secsafe(seccion_coste_inflacion,datos)
    if extras: S+=_secsafe(seccion_numero_realista,datos,extras)
    if extras: S+=_secsafe(seccion_fiabilidad,extras)
    # resumen + radar
    if depth!="esencial":
        try:
            portadilla("_pa_t2_1.png", "Acto 1", 'TU FOTO\nDE HOY', 'El diagnóstico completo: radar, las 12 capas y tu cuadro financiero.')
            S+=[PageBreak(), FullBleedImage("_pa_t2_1.png")]
        except Exception:
            pass
    S+=[Paragraph("El mapa completo",h_sec)]
    if extras and extras.get("crisis"):
        S+=[_box([Paragraph("<font color='#7A5A00'><b>&#9656;  Primero, lo primero</b></font>",St("cri1",fontSize=11,leading=15,fontName=FB)),
                  Paragraph("Tus respuestas dicen que ahora mismo el dinero te pesa de verdad —en el sueño, en la cabeza, en el día a día. Este informe no va a sumarte presión: antes de cualquier plan a años vista, su único objetivo es ayudarte a recuperar el aire y el control del mes. Un paso cada vez.",St("cri2",fontSize=10,leading=15,spaceBefore=2,textColor=INK))],
                 "#FBF4E4","#B45309",ancho=160*mm), Spacer(1,3*mm)]
    S+=[Table([[Paragraph(f"<font size=42 color='#1A1A17'><b>{_sal100(salud)}</b></font>"
                          f"<font size=13 color='#6B7280'>/100</font>",St("bignum",fontSize=42,leading=46)),
                Paragraph(f"<b>{bl}</b><br/><font size=8 color='#6B7280'>Salud psicofinanciera global · "
                          f"{_pct_frase}</font>",body)]],
              colWidths=[42*mm,118*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
        *([Spacer(1,5*mm),Paragraph(coh[0],h_sub),Spacer(1,3*mm),Paragraph(coh[1],St("coh",fontSize=10,leading=14,backColor=LIGHT,borderPadding=8,textColor=INK,spaceBefore=0,spaceAfter=0))] if coh else []),
        *([Spacer(1,4*mm),
           Paragraph(f"Tu arquetipo del dinero: {ARQ_META[arq_code]['nombre']}",h_sub),
           Paragraph(f"<i>{ARQ_META[arq_code]['lema']}</i> {ARQ_META[arq_code]['desc']}",body),
           Paragraph(f"<font color='#1D6F42'><b>Lo que te aporta:</b></font> {ARQ_META[arq_code]['luz']}  "
                     f"<font color='#9A3B2E'><b>Tu punto ciego:</b></font> {ARQ_META[arq_code]['sombra']}",
                     St("aq",fontSize=9.2,leading=13,textColor=GREY,spaceAfter=4))] if arq_code else []),
        Spacer(1,2*mm),
        *([_box([Paragraph("<font color='#9A6A00'><b>&#9656;  Tu siguiente mejor acción</b></font>",St("sau1",fontSize=11.5,leading=15,fontName=FB)),
                 Paragraph(extras["accion_unica"],St("sau2",fontSize=10.5,leading=15,spaceBefore=2,textColor=INK))],
                "#FBF4E4","#B45309",ancho=160*mm), Spacer(1,4*mm)] if (extras and extras.get("accion_unica")) else []),
        Paragraph("Cuanto más llena y hacia el borde está cada capa, más sana. El anillo verde exterior es el "
                  "territorio saludable. Antes de entrar capítulo a capítulo, esta es tu silueta completa:",body),
        Image("_radar.png",width=122*mm,height=122*mm,hAlign="CENTER"),
        PageBreak()]
    # === Tabla semaforo: las 12 areas, ordenadas de peor a mejor ===
    _NOM11={"C1":"Salud emocional","C2":"Libertad financiera","C3":"Resistencia ante shocks","C4":"Control del gasto",
            "C5":"Protección patrimonial","C6":"Gasto con sentido","C7":"Diversificación de ingresos","C8":"Antifragilidad",
            "C9":"Eficiencia del flujo","C10":"Salud de la deuda","C11":"Palanca de crecimiento","C12":"Disciplina de inversión"}
    _semfh=St("semfh",fontSize=8,leading=11,textColor=colors.HexColor("#FDD731"),fontName=FB)
    _fil=sorted(((_sal100(p[c]["score"]),c) for c in p), key=lambda x:x[0])
    _sr=[[Paragraph("#",_semfh),Paragraph("ÁREA",_semfh),Paragraph("NOTA /100",_semfh),Paragraph("ESTADO",_semfh)]]
    for _i,(_sal,_c) in enumerate(_fil,1):
        if _sal<40: _col,_est="#C0392B","Prioritario"
        elif _sal<60: _col,_est="#E08A00","A vigilar"
        else: _col,_est="#1D6F42","Sano"
        _sr.append([Paragraph("%d"%_i,small),Paragraph(_NOM11.get(_c,_c),small),
                    Paragraph("<b>%d</b>"%_sal,small),
                    Paragraph(f"<font color='{_col}'>&#9679;</font>  <font color='{_col}'><b>{_est}</b></font>",small)])
    _semtab=Table(_sr,colWidths=[10*mm,82*mm,28*mm,40*mm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#101113")),
            ("LINEBELOW",(0,1),(-1,-1),0.4,colors.HexColor("#E7E3D8")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]))
    if depth=="esencial":
      S+=[Paragraph("Tus 12 áreas, de peor a mejor",h_sec),
        Paragraph("La misma silueta del radar, pero en cifras y ordenada: arriba, lo que más pide atención; abajo, lo que "
                  "ya te sostiene. Tu plan empieza por la primera fila.",body),
        Spacer(1,3*mm), _semtab, Spacer(1,3*mm),
        Paragraph("<font color='#C0392B'>&#9679;</font> Prioritario (menos de 40) &#160;·&#160; "
                  "<font color='#E08A00'>&#9679;</font> A vigilar (40–59) &#160;·&#160; "
                  "<font color='#1D6F42'>&#9679;</font> Sano (60+). La nota es tu salud en cada área: 100 = óptimo.",small),
        PageBreak()]
    if extras: S+=_secsafe(seccion_ratio_vida,extras)
    if extras: S+=_secsafe(seccion_nudo,extras)
    if depth=="esencial":  # resumen (vistazo) solo en T1 (T2 ya lo cubren diales + capitulos)
        orden=sorted(CAPAS,key=lambda c:p[c]["score"])
        fort=orden[:3]; foco=orden[-3:][::-1]
        S+=[Paragraph("Tu lectura de un vistazo",h_sec),
            Paragraph("Antes del detalle capa por capa, esto es lo esencial: d\u00f3nde te apoyas y d\u00f3nde conviene "
                      "poner el foco. El resto del libro desarrolla cada punto.",body),
            Paragraph("Tus tres fortalezas",h_sub)]
        for c in fort:
            S.append(Paragraph(f"&#8226;  <b>{CAPAS[c]['nombre']}</b> ({_sal100(p[c]['score'])}/100). {OPORTUNIDAD[c]}",
                     St("ef",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
            _frf=(extras or {}).get("frases",{}).get(c) if extras else None
            if _frf: S.append(Paragraph("<font color='#B45309'>&#9656;</font> <i>"+_frf+"</i>",St("eff",fontSize=9.3,leading=12.5,leftIndent=14,spaceAfter=6,textColor=GREY)))
        S.append(Paragraph("Tus tres focos",h_sub))
        for c in foco:
            S.append(Paragraph(f"&#8226;  <b>{CAPAS[c]['nombre']}</b> ({_sal100(p[c]['score'])}/100). {RIESGO[c]}",
                     St("ec",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
            _frc=(extras or {}).get("frases",{}).get(c) if extras else None
            if _frc: S.append(Paragraph("<font color='#B45309'>&#9656;</font> <i>"+_frc+"</i>",St("ecf",fontSize=9.3,leading=12.5,leftIndent=14,spaceAfter=6,textColor=GREY)))
        S+=[Spacer(1,3*mm),
            Paragraph(f"En una frase: tu salud psicofinanciera global es de <b>{_sal100(salud)}/100</b>"
                      f"({_pct_frase}{_pct_nota}). No es una condena ni un trofeo: es tu punto "
                      "de partida, y se mueve.",body),
            PageBreak()]
    # capítulos por capa
    _rent=bool(extras and extras.get("rentista"))
    _RENT_RIESGO={
        "C2":"Tu riesgo ya no es no llegar: llegaste. Es el contrario — que la inflación erosione en silencio lo que hoy te sostiene, o que una tasa de retiro demasiado alta consuma el principal sin que lo notes hasta que es tarde.",
        "C7":"Para ti, depender de una sola fuente de rentas —un único inmueble, un único pagador, una única clase de activo— es el riesgo silencioso: el día que esa fuente falla o renta menos, tu tren de vida tiembla entero."}
    _RENT_OPORT={
        "C2":"Tu número ya no es una meta que alcanzar, sino un nivel que defender. La oportunidad está en blindarlo: que el capital rente, crezca al menos con la inflación y dure más que tú.",
        "C7":"Diversificar tus fuentes de renta no es crecer por crecer: es que ninguna caída individual pueda con tu tranquilidad. Varias rentas pequeñas e independientes sostienen mejor que una sola grande."}
    if _rent:
        S+=[_box([Paragraph("<b>Cómo leer tus capítulos</b>",St("rlt",fontSize=10.8,leading=15,spaceAfter=4)),
                  Paragraph("Este informe está escrito, por defecto, para quien aún construye su patrimonio. Tú ya lo "
                            "tienes: vives de tus rentas. Lee cada capítulo con esta traducción — donde el texto hable de "
                            "«crecer», «ahorrar más» o «acumular», tu versión es «preservar, hacer sostenible y que dure». "
                            "Tu objetivo no es llegar a la cima: es no bajar de ella. Hemos adaptado a esa realidad tus "
                            "palancas, tu contrato y los capítulos clave.",
                            St("rlx",fontSize=10,leading=14.5))],"#EEF2F8","#0F766E",ancho=160*mm),
            Spacer(1,4*mm)]
    for n,code in (list(enumerate(CAPAS,1)) if depth!="esencial" else []):
        pc=p[code]
        cab=[Paragraph(f"CAP\u00cdTULO {n}",cap_kicker),
             Paragraph(pc["nombre"],h_book),
             Table([[""]],colWidths=[40*mm],style=[("LINEBELOW",(0,0),(-1,-1),1.5,ACC)]),
             Spacer(1,3*mm),
             Paragraph("Qu\u00e9 mide",h_sub),
             Paragraph(f"Este cap\u00edtulo mide {QMIDE[code]}",body),
             Paragraph("Tu resultado",h_sub),
             Table([[Paragraph(f"<b>{_sal100(pc['score'])}</b>/100",body),
                     Chip(pc["banda"],BANDC[pc["bi"]],w=96,h=14)]],
                   colWidths=[60*mm,40*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
             Bar(pc["score"],w=160*mm/1),
             Spacer(1,3*mm),
             Paragraph("Qu\u00e9 significa para ti",h_sub),
             Paragraph(interpretar(pc["nombre"],pc["score"],pc["banda"],pc["bi"],pc["peor"],code),body)]
        _frp=(extras or {}).get("frases",{}).get(code) if extras else None
        if _frp:
            cab.append(_box([Paragraph("<b>Tu caso, en números:</b> "+_frp,St("tcn",fontSize=10.5,leading=15,textColor=INK))],"#FBF4E4","#B45309",ancho=160*mm))
            cab.append(Spacer(1,2*mm))
        _cit=citas_capa(code,resp)
        if _cit:
            cab.append(Paragraph("Lo que reconociste",h_sub))
            _qs=St("cq",fontSize=9,leading=12,textColor=GREY,fontName=FR)
            _ts=St("ct",fontSize=10.5,leading=14,textColor=ACCDK,fontName=FB,spaceBefore=1)
            for _sc,_q,_tag in _cit:
                _inner=[Paragraph(f"<i>\u00ab{_q}\u00bb</i>",_qs),Paragraph(_tag,_ts)]
                cab.append(Table([[_inner]],colWidths=[156*mm],
                    style=[("LINEBEFORE",(0,0),(0,-1),2.6,AMARILLO),("BACKGROUND",(0,0),(-1,-1),LIGHT),
                           ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
                           ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
                cab.append(Spacer(1,2*mm))
        if depth=="esencial":
            cab+=[Paragraph("Tu siguiente paso",h_sub),
                  Paragraph(f"&#8226;  {ACCIONES[code][0]}",St("ps",fontSize=10,leading=14,textColor=INK,leftIndent=4,backColor=LIGHT,borderPadding=6,spaceBefore=2)),
                  Spacer(1,6*mm)]
            S.append(KeepTogether(cab))
        else:
            cab+=[Paragraph("Desglose por faceta",h_sub)]
            facs=CAPAS[code]["facetas"]
            for f,sc in pc["facetas"].items():
                cab.append(Table([[Paragraph(f"<b>{facs.get(f,f)}</b>",small),Bar(sc,w=46*mm),
                                    Paragraph(f"<font color='{_sevcol(sc)}'><b>{_sal100(sc)}</b> \u00b7 {faceta_lectura(sc)}</font>",small)]],
                                 colWidths=[66*mm,48*mm,42*mm],
                                 style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,-1),0),
                                        ("LEFTPADDING",(1,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
            cab+=[Spacer(1,2*mm),
                  Paragraph(segundo_parrafo(pc["bi"],code),body),
                  Paragraph("El riesgo si no act\u00faas",h_sub),
                  Paragraph((_RENT_RIESGO.get(code) if _rent else None) or RIESGO[code],body),
                  Paragraph("La oportunidad",h_sub),
                  Paragraph((_RENT_OPORT.get(code) if _rent else None) or OPORTUNIDAD[code],body),
                  Paragraph("Tu plan de acci\u00f3n",h_sub),
                  Paragraph("Tres pasos, en orden. Empieza por el primero y no pases al siguiente hasta tenerlo en marcha:",small)]
            for a in ACCIONES[code]:
                cab.append(Paragraph(f"<font face='Helvetica'>[   ]</font>  {a}",St("pa",fontSize=10,leading=14,textColor=INK,leftIndent=6,spaceAfter=4)))
            cab+=[Spacer(1,2*mm),
                  Paragraph(f"\u201c{PRINCIPIO[code]}\u201d",St("pr",fontSize=10.5,leading=14,textColor=ACCDK,
                            fontName="Helvetica-Oblique",backColor=LIGHT,borderPadding=8,spaceBefore=2)),
                  Spacer(1,2*mm),
                  Paragraph("Para reflexionar",h_sub),
                  Paragraph(REFLEX[code],St("rf",fontSize=10,leading=14,textColor=INK,fontName="Helvetica-Oblique"))]
            S.extend(cab); S.append(PageBreak())
    # transversales
    if depth!="esencial": S+=[Paragraph("Lo que cruza todas las capas",h_sec),
        Paragraph("Hay tres corrientes que no viven en un solo capítulo: recorren todo tu perfil. Verlas juntas "
                  "explica patrones que ninguna capa aislada revela.",body)]
    desc={"PSIQUE":("Carga psicológica","el peso emocional del dinero: negación, identidad, rumiación."),
          "LIQUIDEZ":("Liquidez","la holgura de colchón disponible en el conjunto de tu vida."),
          "VINCULO":("Vínculo","la tensión y la transparencia con tu pareja o tu familia.")}
    qhacer={"PSIQUE":"Trabajar la cabeza \u2014tus creencias y tu relaci\u00f3n emocional con el dinero\u2014 multiplica el efecto de cualquier cambio pr\u00e1ctico que hagas.",
            "LIQUIDEZ":"Reforzar tu colch\u00f3n l\u00edquido es la mejora m\u00e1s transversal de todas: da aire, a la vez, a casi todas las dem\u00e1s \u00e1reas de tu vida.",
            "VINCULO":"Hablar el dinero con quien compartes tu vida desactiva conflictos antes de que existan. El silencio es lo \u00fanico que de verdad cuesta caro."}
    def _lect(v):
        if v is None: return "no tenemos datos suficientes para puntuarlo."
        if v<30: return "es un punto fuerte: no te est\u00e1 pasando factura."
        if v<51: return "est\u00e1 en zona razonable, con margen de mejora."
        if v<76: return "empieza a pesar y conviene atenderlo pronto."
        return "es un foco importante que cruza varias \u00e1reas a la vez."
    for t in ("PSIQUE","LIQUIDEZ","VINCULO"):
        val=tr[t]; tt,dd=desc[t]
        vtxt=("%s"%_sal100(val)) if val is not None else "\u2014"
        S+=[Paragraph(tt,h_sub),
            Table([[Paragraph(f"<b>{vtxt}</b>/100",body),Bar(val or 0,w=120*mm)]],
                  colWidths=[28*mm,124*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
            Paragraph(f"Mide {dd} En tu caso, {_lect(val)}",body),
            Paragraph(qhacer[t],St("qh",fontSize=9.6,leading=13,textColor=INK,leftIndent=4,backColor=LIGHT,borderPadding=6,spaceAfter=8))]
    S+=[PageBreak()]
    # insights
    S+=[Paragraph("Lo que tus respuestas revelan",h_sec),
        Paragraph("Estos hallazgos surgen de cruzar tus respuestas entre sí. Son las frases que un buen asesor te "
                  "diría tras leerte entero:",body)]
    for ti,tx in insights(p,tr,fi):
        S+=[Paragraph(f"<font color='#0284C7'>&#8226;</font>  <b>{ti}</b>",body),
            Paragraph(tx,St("ix",fontSize=9.6,leading=14,leftIndent=12,spaceAfter=9))]
    S+=[PageBreak()]
    # retrato en tus palabras (sintesis IA de las preguntas abiertas)
    if sintesis and str(sintesis).strip():
        S+=[Paragraph("Tu retrato, en tus palabras",h_sec),
            Paragraph("Esta lectura nace de lo que tú mismo escribiste en tus respuestas abiertas, cruzado con lo que dicen tus números.",small),
            Spacer(1,2*mm)]
        import re as _re_md
        for _par in [x for x in str(sintesis).replace("\r","").split("\n") if x.strip()]:
            _e=_par.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            _e=_re_md.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", _e)   # markdown negrita -> <b> (evita ** literales)
            S.append(Paragraph(_e,body))
        S+=[PageBreak()]
    # === ACTO 1 (cierre): sintesis financiera (FODA + flujo + proyeccion) ANTES de planificar ===
    S+=_secsafe(cuadro_financiero,p,datos,fi)
    S+=_secsafe(seccion_cuatro_caminos,datos,fi,extras)
    S+=_secsafe(seccion_rentabilidad_alquiler,datos)
    S+=_secsafe(seccion_familia,datos)
    # === ACTO 1: Meses de Libertad Financiera — la cifra objetiva que de verdad te mide ===
    _res=(extras or {}).get("resiliencia")
    if _res:
        _ml_p=_res["meses_libertad"]; _an_p=_res["anios_libertad"]; _mliq=_res["meses_liquido"]
        _niv=_res["nivel"]; _ilq=_res["iliquido"]
        if _niv=="libertad":
            _h1=f"<b>Tu patrimonio cubre {_an_p:g} años de tu vida.</b>"
            _h2=("Has cruzado la línea que casi nadie cruza: si tus ingresos se cortaran hoy, tu patrimonio sostendría tu vida "
                 "durante décadas. Trabajar ha dejado de ser obligación para ser elección. Tu reto ya no es ganar más, sino que "
                 "ese capital rente y no pierda poder de compra contra la inflación.")
        elif _niv=="solido":
            _h1=f"<b>Tu patrimonio compra {_ml_p:g} meses —cerca de {_an_p:g} años— de libertad.</b>"
            _h2=("Tienes un respaldo que muy pocos tienen. La pregunta deja de ser «¿aguantaría un golpe?» —lo aguantas— y pasa a "
                 "ser «¿está trabajando mi capital o duerme?». Tu palanca ya no es el sueldo: es la eficiencia de tu patrimonio.")
        elif _niv=="construccion":
            _h1=f"<b>Tu patrimonio cubre {_ml_p:g} meses de tu vida.</b>"
            _h2=("Estás construyendo respaldo real. El siguiente hito es claro: llegar a 24 meses cubiertos, el punto donde un "
                 "imprevisto deja de ser una amenaza y pasa a ser una incomodidad. A partir de ahí, el dinero empieza a trabajar para ti.")
        elif _niv=="ajustado":
            _h1=f"<b>Tu patrimonio cubre {_ml_p:g} meses de tu vida.</b>"
            _h2=("Es una base, pero todavía fina: un shock serio —un paro, una avería grande, un mal año— te obligaría a decisiones "
                 "duras. La prioridad no es la rentabilidad todavía; es engrosar ese colchón hasta 6-12 meses. Eso es lo que compra calma.")
        else:
            _h1=f"<b>Tu patrimonio cubre apenas {_ml_p:g} meses de tu vida.</b>"
            _h2=("Hoy tu libertad depende casi por completo de que el ingreso no falle. Y esto es lo importante: no es cuestión de "
                 "cuánto ganas —se puede ganar bien y estar igual de expuesto—. Aquí todavía no se construye libertad: se construye "
                 "red. Antes que cualquier inversión, meses de respaldo.")
        _parr=[Paragraph("LO QUE DE VERDAD TE MIDE",St("mlh0",fontSize=9,leading=12,textColor=colors.HexColor("#B45309"),fontName=FB)),
               Paragraph(_h1+" "+_h2,St("mlh1",fontSize=11,leading=16,textColor=INK,spaceBefore=3)),
               Paragraph("No es tu sueldo el que mide tu libertad, es tu patrimonio: los meses que vivirías si tus ingresos se "
                         "cortaran hoy. Un buen sueldo con poco respaldo es más frágil que un patrimonio sólido con un mal mes.",
                         St("mlh2",fontSize=9.4,leading=13,textColor=GREY,spaceBefore=5))]
        if _ilq:
            _parr.append(Paragraph(f"<b>Matiz honesto:</b> buena parte de tu patrimonio no es caja inmediata. En líquido disponible "
                                   f"tienes solo <b>{_mliq:g} meses</b>. Tu casa o tu negocio valen, pero no pagan el súper del mes que "
                                   f"viene: conviene tener una parte realizable en días.",
                                   St("mlh3",fontSize=9.4,leading=13,textColor=colors.HexColor("#9A3B2E"),spaceBefore=5)))
        if _niv=="libertad":
            _parr.append(Paragraph("<b>¿Y si vives más de 100 años?</b> Tu patrimonio ya es perpetuo: al 4% renta más de lo que "
                                   "gastas, así que no se agota con los años. Vivas hasta los 90 o los 110, te cubre — el escenario de "
                                   "longevidad que casi nadie contempla, tú ya lo tienes resuelto.",
                                   St("mlon",fontSize=9.4,leading=13,textColor=colors.HexColor("#0F766E"),spaceBefore=5)))
        else:
            _parr.append(Paragraph(("<b>¿Y si vives más de 100 años?</b> Hoy, sin ingresos, tu patrimonio cubre unos %g años de vida. "
                                    "Blindar la longevidad —que no se agote vivas lo que vivas— es justo para lo que sirve cruzar tu número "
                                    "de libertad: a partir de ahí, la renta al 4%% cubre tu vida para siempre.") % _an_p,
                                    St("mlon",fontSize=9.4,leading=13,textColor=GREY,spaceBefore=5)))
        S+=[_box(_parr,"#FBF9EC","#C9962B",ancho=160*mm), Spacer(1,4*mm)]
    # === ACTO 1: Ratio de Esclavitud Temporal (dinamico y honesto, derivado del flujo real) ===
    _ingm_e=max(datos.get("ingreso_mensual",0),0); _ahom_e=datos.get("ahorro_mensual",0) or 0
    _gasm_e=datos.get("gasto_mensual",0) or 0
    if _ingm_e>0:
        _s_e=max(0.0,min(1.0,_ahom_e/_ingm_e)); _escl=max(0.0,min(1.0,1.0-_s_e))
        _ml=round(12*_s_e,1); _mi=round(12*_escl)
        _ya_libre=bool(_res and _res.get("nivel") in ("libertad","solido"))
        if _ya_libre:
            _txt_e=(f"<b>En puro flujo, tu mes se parece al de todos: el {_escl*100:.0f}% de lo que trabajas se va en sostener tu "
                    f"vida.</b> Pero en ti esa cifra engaña, y mucho. Tu patrimonio ya ha comprado tu libertad: no cambias tiempo "
                    f"por dinero para sobrevivir —ya no dependes de ello—, lo haces porque quieres. Tu palanca no es liberar horas; "
                    f"es que tu capital trabaje tan duro como trabajaste tú para construirlo.")
            S+=[_box([Paragraph(_txt_e,St("escl",fontSize=10.5,leading=15,textColor=INK))],
                     "#EEF2F8","#2C5C8A",ancho=160*mm),
                Spacer(1,3*mm)]
        else:
            if _ahom_e>0:
                _esf=_gasm_e/_ahom_e if _ahom_e>0 else 0
                _txt_e=(f"<b>Tu Ratio de Esclavitud Temporal es del {_escl*100:.0f}%.</b> Traducido a tiempo: de cada 12 meses "
                        f"que trabajas, <b>unos {_mi:.0f} se van enteros en pagar la vida que ya tienes</b> y apenas "
                        f"<b>{_ml:.0f} en construir la que quieres</b>. Y este es el dato que duele: al ritmo de hoy, "
                        f"<b>comprar un solo mes de libertad te cuesta {_esf:g} meses de trabajo</b>. El problema no es "
                        f"cuánto ganas: es lo poco de tu esfuerzo que se queda contigo.")
            else:
                _txt_e=("<b>Tu Ratio de Esclavitud Temporal roza el 100%.</b> Ahora mismo casi todo lo que trabajas se "
                        "consume en sostener tu vida actual: apenas queda año destinado a construir tu libertad. "
                        "El primer objetivo no es ganar más; es abrir una rendija de excedente.")
            S+=[_box([Paragraph(_txt_e,St("escl",fontSize=10.5,leading=15,textColor=INK)),
                      Paragraph("Ese tiempo «ocupado» —tu jornada, los desplazamientos, todo lo que haces para generar ingresos— "
                                "es el que tu plan busca encoger. Su objetivo de fondo es uno: convertir horas ocupadas en horas "
                                "libres, las que eliges tú.",St("escl2",fontSize=9.6,leading=14,textColor=GREY,spaceBefore=4))],
                     "#FBF4E4","#B45309",ancho=160*mm),
                Spacer(1,3*mm)]
    # === ACTO 1: mapa de fuentes de ingreso (diversificacion + €/hora por fuente) ===
    if extras: S+=_secsafe(seccion_fuentes,extras)
    # === TRANSICION ACTO 1 -> ACTO 2: el golpe de realidad (dinamico segun perfil) ===
    _ingm_h=max(datos.get("ingreso_mensual",0),0); _gasm_h=datos.get("gasto_mensual",0) or 0
    _tasa_h=fi[2] if (len(fi)>2 and fi[2] is not None) else 0
    _ya_libre_h=bool(_res and _res.get("nivel") in ("libertad","solido"))
    if _gasm_h>_ingm_h and _ya_libre_h:
        _hostia=("Acabas de ver tu foto de hoy. Gastas más de lo que ingresas — pero en tu caso eso no es una fuga, es una "
                 "decisión: vives, en parte, del patrimonio que ya construiste. Lo que antes fue acumular ahora es administrar el "
                 "desembalse. El riesgo cambia de cara: ya no es llegar a fin de mes, es que tu capital se agote antes de tiempo o "
                 "no rente lo suficiente para sostener el ritmo. Eso se planifica, no se improvisa.")
    elif _gasm_h>_ingm_h:
        _hostia=("Acabas de ver tu foto de hoy. Tu estructura no está rota, pero está en rojo: tienes un motor que "
                 "genera dinero y un sistema que lo evapora más rápido de lo que entra. No es falta de ingresos — "
                 "es una fuga de diseño. Y lo que se diseña, se corrige.")
    elif _tasa_h<10:
        _hostia=("Acabas de ver tu foto de hoy. Tu estructura no está rota, pero está en pausa: tienes un motor que "
                 "genera dinero y un sistema que apenas retiene lo que produce. El problema no es cuánto ganas; "
                 "es cuánto se queda contigo.")
    else:
        _hostia=("Acabas de ver tu foto de hoy. Tu estructura funciona, pero rinde por debajo de su potencial: "
                 "generas y retienes, y ahora cada euro tiene que trabajar con intención, no por inercia.")
    S+=[Spacer(1,3*mm),
        Paragraph(_hostia,St("hostia",fontSize=13,leading=19,textColor=ACCDK,fontName=FB,spaceBefore=4,spaceAfter=5)),
        Table([[""]],colWidths=[62*mm],style=[("LINEBELOW",(0,0),(-1,-1),3,AMARILLO)]),
        Spacer(1,9*mm)]
    if depth!="esencial":
        try:
            portadilla("_pa_t2_2.png", "Acto 2", 'LA BRECHA', 'Tu vida ideal frente a la real, tus palancas, y el coste de no hacer nada.')
            S+=[PageBreak(), FullBleedImage("_pa_t2_2.png")]
        except Exception:
            pass
    # === ACTO 2: la brecha y las palancas (vida ideal vs actual + coste de no hacer nada) ===
    if extras: S+=_secsafe(seccion_extras,extras,datos)
    if extras and depth!="esencial": S+=_secsafe(seccion_coste_inaccion,extras)
    if depth!="esencial":
        # Diagnostico condicional: Gasto Anestesico (solo si estres alto Y gasto sin sentido alto)
        _c1s=p.get("C1",{}).get("score",0) or 0; _c6s=p.get("C6",{}).get("score",0) or 0
        if _c1s>=55 and _c6s>=55:
            S+=[_box([Paragraph("<b>Patrón detectado: Gasto Anestésico</b>",St("ga1",fontSize=11.5,leading=15,textColor=ACCDK,fontName=FB)),
                      Paragraph("Tus respuestas cruzan dos señales que rara vez se miran juntas: una carga de estrés financiero alta "
                                "y un gasto que no te devuelve bienestar. Es el patrón del gasto de evasión — usar el flujo de caja para "
                                "comprar alivio inmediato frente a la tensión. Matemáticamente, financias el propio bucle: trabajas bajo "
                                "presión para ganar, y gastas parte de eso en anestesiar la presión de trabajar. Romperlo no es gastar "
                                "menos por fuerza de voluntad: es sustituir el consumo de evasión por la tranquilidad del control estructural.",
                                St("ga2",fontSize=10,leading=14,textColor=INK,spaceBefore=3))],
                    "#FBECE8","#9A3B2E",ancho=160*mm), Spacer(1,4*mm)]
        # Diagnostico condicional: Indice de Fragilidad Familiar (solo si dependientes Y colchon < 6 meses)
        _cm=(extras.get("fortuna_neta") or {}).get("colchon_meses") if extras else None
        if extras and extras.get("conciliacion") and _cm is not None and _cm<6:
            _dias=int(round(_cm*30))
            S+=[_box([Paragraph("<b>ESTRUCTURA EXPUESTA</b>",St("ff1",fontSize=11.5,leading=15,textColor=colors.HexColor("#9A3B2E"),fontName=FB)),
                      Paragraph(("Tienes personas que dependen de ti económicamente y un colchón por debajo de seis meses. Si tu "
                                "principal fuente de ingresos se detuviera, tu familia tendría unos <b>%d días</b> de autonomía antes de "
                                "tener que recortar su nivel de vida o malvender activos. Esto no es un problema de dinero: es de "
                                "seguridad. Blindar el colchón y ordenar la protección patrimonial es la prioridad que va por delante "
                                "de cualquier estrategia de crecimiento.") % _dias,
                                St("ff2",fontSize=10,leading=14,textColor=INK,spaceBefore=3))],
                    "#FBECE8","#9A3B2E",ancho=160*mm), Spacer(1,4*mm)]
        # Diagnostico condicional: La jaula de oro (% de gasto fijo inamovible por contrato)
        _pgf=datos.get("pct_gasto_fijo")
        try: _pgf=max(0.0,min(100.0,float(_pgf))) if _pgf is not None else None
        except Exception: _pgf=None
        if _pgf is not None and _pgf>=60:
            _gm_j=datos.get("gasto_mensual") or 0
            _fijo_txt=(" (unos %s al mes)" % _eur(round(_gm_j*_pgf/100.0))) if _gm_j else ""
            S+=[_box([Paragraph("<b>Tu jaula de oro</b>",St("jo1",fontSize=11.5,leading=15,textColor=colors.HexColor("#9A3B2E"),fontName=FB)),
                      Paragraph(("Crees que tienes flexibilidad, pero el <b>%g%%</b> de tu gasto%s está atado por contrato —alquiler, "
                                "hipoteca, colegios, permanencias— y no lo podrías recortar en 24 horas. Si mañana se cortaran tus "
                                "ingresos, esa parte seguiría saliendo sí o sí. No estás en una casa con muchas puertas: estás en una "
                                "jaula de oro. Bajar ese porcentaje —renegociar, eliminar permanencias, flexibilizar lo fijo— es lo que "
                                "convierte una crisis en un susto, en vez de en una espiral.") % (_pgf,_fijo_txt),
                                St("jo2",fontSize=10,leading=14,textColor=INK,spaceBefore=3))],
                    "#FBECE8","#9A3B2E",ancho=160*mm), Spacer(1,4*mm)]
        # Diagnostico condicional: Devaluacion silenciosa del perfil (IA/automatizacion)
        _dev=((extras.get("perfil_in") or {}).get("devaluacion_perfil","") or "").lower() if extras else ""
        if "menos" in _dev:
            S+=[_box([Paragraph("<b>La devaluación silenciosa de tu esfuerzo</b>",St("dv1",fontSize=11.5,leading=15,textColor=colors.HexColor("#B45309"),fontName=FB)),
                      Paragraph("Lo has reconocido tú: tu perfil profesional vale hoy menos que hace cinco años. Y ese es el riesgo que "
                                "nadie mete en una hoja de cálculo, porque tu mayor activo no es tu casa ni tu cartera — es tu capacidad de "
                                "generar ingresos. Si esa capacidad se devalúa con la automatización y la IA mientras tú miras solo tus "
                                "gastos, todo lo demás se tambalea. La inversión más rentable que tienes ahora no es financiera: es "
                                "actualizar tu habilidad más difícil de automatizar, antes de que el mercado decida por ti.",
                                St("dv2",fontSize=10,leading=14,textColor=INK,spaceBefore=3))],
                    "#FBF4E4","#B45309",ancho=160*mm), Spacer(1,4*mm)]
    # === ACTO 3: el plan ===
    if depth!="esencial":
        try:
            portadilla("_pa_t2_3.png", "Acto 3", 'TU PLAN', 'De la foto a los hechos: tu constitución financiera y hoja de ruta.')
            S+=[PageBreak(), FullBleedImage("_pa_t2_3.png")]
        except Exception:
            pass
    S+=[Paragraph("Tu plan de acción",h_sec),
        Paragraph("Ordenado por impacto: si solo pudieras mover una palanca esta semana, empieza por la primera.",body)]
    _plan=(extras or {}).get("plan_maestro") if extras else None
    if _plan:
        S.append(Spacer(1,2*mm))
        for mv in _plan:
            _es="TU PRIMER MOVIMIENTO" if mv["orden"]==1 else ("MOVIMIENTO %d"%mv["orden"])
            _pc="#B45309" if mv["orden"]==1 else "#6B7280"
            _pbg="#FBF4E4" if mv["orden"]==1 else "#F6F4EC"
            _pin=[Paragraph("<font color='%s'><b>%s</b></font>  &#183;  <b>%s</b>"%(_pc,_es,mv["titulo"]),St("pm0",fontSize=11.5,leading=15,textColor=ACCDK,fontName=FB)),
                  Paragraph("<b>Por qué:</b> "+mv["porque"],St("pm1",fontSize=9.8,leading=14,textColor=INK,spaceBefore=3)),
                  Paragraph("<font color='%s'><b>&#9656; Esta semana:</b></font> %s"%(_pc,mv["accion"]),St("pm2",fontSize=9.8,leading=14,textColor=INK,spaceBefore=2)),
                  Paragraph("<b>En 12 meses ganas:</b> <i>%s</i>"%mv["gana"],St("pm3",fontSize=9.5,leading=13,textColor=GREY,spaceBefore=2))]
            S.append(_box(_pin,_pbg,_pc,ancho=160*mm)); S.append(Spacer(1,3*mm))
        S.append(Paragraph("Haz el primero hasta tenerlo en marcha — no pases al siguiente antes. Una palanca movida vale más que diez planeadas.",St("pmf",fontSize=9.5,leading=13,textColor=GREY,fontName="Helvetica-Oblique",spaceAfter=3)))
    # Lineas Rojas: no-negociables de tu Constitucion (derivados de tu situacion real)
    _lr=[]
    if tapon_coste(datos): _lr.append("No mantener más de 3 meses de gasto en cuentas al 0%: el excedente parado pierde valor cada mes.")
    if _gasm_e>_ingm_e: _lr.append("No tapar el déficit con deuda de consumo ni aplazamientos: primero se cierra la fuga.")
    else: _lr.append("No dejar tu excedente sin destino: cada mes, lo que sobra va a su sitio antes del día 5.")
    _lr.append("No postergar el blindaje de lo que ya has construido: proteger va siempre antes que crecer.")
    _lrp=[Paragraph("<b>Tus líneas rojas — los no-negociables de tu Constitución</b>",St("lr0",fontSize=11,leading=15,textColor=ACCDK,fontName=FB))]
    for _x in _lr: _lrp.append(Paragraph("&#9656;  "+_x,St("lrx",fontSize=10,leading=14,textColor=INK,leftIndent=4,spaceBefore=2)))
    S+=[_box(_lrp,"#FBF9EC","#C9962B",ancho=160*mm), Spacer(1,4*mm)]
    rows=[[Paragraph("<b>#</b>",small),Paragraph("<b>Área de impacto</b>",small),Paragraph("<b>Tu siguiente acción</b>",small),Paragraph("<b>Severidad</b>",small)]]
    _AREA={"C1":"Bienestar financiero","C2":"Libertad financiera","C3":"Resistencia ante shocks","C4":"Control del gasto","C5":"Protección patrimonial","C6":"Gasto con sentido","C7":"Diversificación de ingresos","C8":"Antifragilidad","C9":"Gobierno del flujo","C10":"Salud de la deuda","C11":"Palanca de crecimiento","C12":"Disciplina de inversión"}
    _vistos=set(); _i=0
    for val,code,d in plan(p):
        if code in _vistos: continue
        _vistos.add(code); _i+=1
        _acc=ACCIONES.get(code,["",d]); _acc=_acc[1] if len(_acc)>1 else d
        rows.append([Paragraph(str(_i),small),Paragraph(f"<b>{_AREA.get(code,code)}</b>",small),
                     Paragraph(_acc,small),
                     Chip(f"{val:.0f}/100","#9A3B2E" if val>=75 else "#EA580C",w=46,h=13)])
    pt=Table(rows,colWidths=[8*mm,40*mm,82*mm,30*mm]); pt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),LIGHT),("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    _pens=float(datos.get("pension_estimada") or 0); _gm_lib=float(datos.get("gasto_mensual") or 0)
    _num_aj=max(0.0,(_gm_lib-_pens))*12*25
    S+=[pt,Spacer(1,5*mm),Paragraph("Tus números de libertad",h_sub),
        Table([["Número de libertad financiera (regla 25×)",f"{fi[0]:,.0f} €".replace(",",".")],
               ["En tiempo de tu trabajo actual",(_en_tiempo(fi[0],datos) or "—")],
               ["Progreso hacia la libertad",f"{fi[1]} %"],
               ["Tasa de ahorro actual",f"{fi[2]} %"],
               ["Años estimados a la libertad","más de 100" if fi[3] is None else ("+40 años (a este ritmo)" if fi[3]>40 else f"{fi[3]:.0f} años")]],
              colWidths=[105*mm,55*mm],style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
              ("FONTNAME",(1,0),(1,-1),FB),("TEXTCOLOR",(1,0),(1,-1),ACCDK),
              ("ALIGN",(1,0),(1,-1),"RIGHT"),
              ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))]
    # --- Foto del patrimonio: invertido / parado / iliquido ---
    _f_inv=float(datos.get("inversiones_liquidas") or 0); _f_par=float(datos.get("colchon_liquido") or 0)
    _f_pat=float(datos.get("patrimonio") or 0); _f_ili=max(0.0,_f_pat-_f_inv-_f_par)
    _f_tot=_f_inv+_f_par+_f_ili
    if _f_tot>0:
        def _pcf(v): return "%.0f%%"%(100*v/_f_tot)
        _trab=100*_f_inv/_f_tot; _duerme=100-_trab
        S+=[Spacer(1,4*mm),Paragraph("Tu foto patrimonial: qué trabaja y qué duerme",h_sub),
            Paragraph("No es lo mismo tener patrimonio que tener renta. En <font color='#1D6F42'><b>verde</b></font>, el dinero que <b>trabaja</b> para ti (invertido, generando renta). En <font color='#C9A227'><b>ámbar</b></font> y <font color='#9CA3AF'><b>gris</b></font>, el que <b>no trabaja</b>: parado en el banco o atrapado en ladrillo y negocio.",body),
            Spacer(1,2*mm),
            FotoPatrimonio(_f_inv,_f_par,_f_ili,w=160,h=13),
            Spacer(1,1.5*mm),
            Table([[Paragraph("<font color='#1D6F42'>●</font> <b>%.0f%% TRABAJA</b> para ti"%_trab,St("ft1",fontSize=10,leading=13)),
                    Paragraph("<font color='#9CA3AF'>●</font> <b>%.0f%% DUERME</b> (parado + ilíquido)"%_duerme,St("ft2",fontSize=10,leading=13,alignment=2))]],
                   colWidths=[80*mm,80*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]),
            Spacer(1,2*mm),
            Table([[Paragraph("<font color='#1D6F42'>●</font> <b>Invertido</b> (mercados) — <font color='#1D6F42'>trabaja</font>: %s · %s"%(_eur(_f_inv),_pcf(_f_inv)),small),
                    Paragraph("<font color='#C9A227'>●</font> <b>Parado</b> (c/c, depósitos) — no trabaja: %s · %s"%(_eur(_f_par),_pcf(_f_par)),small),
                    Paragraph("<font color='#9CA3AF'>●</font> <b>Ilíquido</b> (vivienda, negocio) — no renta: %s · %s"%(_eur(_f_ili),_pcf(_f_ili)),small)]],
                   colWidths=[54*mm,53*mm,53*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),2)]),
            Spacer(1,3*mm)]
    # --- Foto del flujo: ingresos (activo/pasivo) vs gastos (fijo/variable) ---
    _x_ing=float(datos.get("ingreso_mensual") or 0); _x_gas=float(datos.get("gasto_mensual") or 0)
    _x_pas=min(float(datos.get("renta_pasiva") or 0),_x_ing)
    _x_it=datos.get("ing_trabajo")
    _x_act=float(_x_it) if (_x_it and float(_x_it)>0) else max(0.0,_x_ing-_x_pas)
    _x_pf=min(100.0,max(0.0,float(datos.get("pct_gasto_fijo") or 0)))
    _x_fij=_x_gas*_x_pf/100.0 if _x_pf>0 else min(_x_gas,float(datos.get("coste_vivienda") or 0)+float(datos.get("cuota_deuda") or 0))
    _x_fij=min(_x_fij,_x_gas); _x_var=max(0.0,_x_gas-_x_fij)
    if _x_ing>0 and _x_gas>0:
        _pp_pas=100*_x_pas/_x_ing if _x_ing else 0; _pp_fij=100*_x_fij/_x_gas if _x_gas else 0
        S+=[Spacer(1,2*mm),Paragraph("Tu foto del flujo: de dónde viene y a dónde va",h_sub),
            Paragraph("Cada mes entra dinero y sale dinero. En <font color='#1D6F42'><b>verde</b></font>, el ingreso <b>pasivo</b> (el que te libera, no depende de tu tiempo). En <font color='#C65C4E'><b>rojo</b></font>, el gasto <b>fijo</b> (el que te ata pase lo que pase). Cuanto más verde arriba y menos rojo abajo, más libre eres.",body),
            Spacer(1,1.5*mm),
            FlujoEstructura(_x_act,_x_pas,_x_fij,_x_var,w=160,h=12),
            Spacer(1,2*mm),
            Table([[Paragraph("<font color='#6B7280'>●</font> Ingreso <b>activo</b> (tu tiempo): %s"%_eur(_x_act),small),
                    Paragraph("<font color='#1D6F42'>●</font> Ingreso <b>pasivo</b> (te libera): %s · %.0f%%"%(_eur(_x_pas),_pp_pas),small)]],
                   colWidths=[80*mm,80*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"TOP")]),
            Table([[Paragraph("<font color='#C65C4E'>●</font> Gasto <b>fijo</b> (te ata): %s · %.0f%%"%(_eur(_x_fij),_pp_fij),small),
                    Paragraph("<font color='#C9A227'>●</font> Gasto <b>variable</b> (flexible): %s"%_eur(_x_var),small)]],
                   colWidths=[80*mm,80*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),2)]),
            Spacer(1,3*mm)]
    _inv_lib=float(datos.get("inversiones_liquidas") or 0)+float(datos.get("colchon_liquido") or 0)
    _pat_lib=float(datos.get("patrimonio") or 0)
    if _pat_lib > _inv_lib*1.5 + 20000:
        _cob_pot=round(100*_pat_lib/fi[0]) if fi[0] else 0      # potencial movilizando TODO el patrimonio (incluida la vivienda, llegado el momento de simplificar)
        _libre_txt=" — con eso quedarías en <b>libertad financiera</b>" if _cob_pot>=100 else ""
        S+=[Paragraph("<b>Patrimonio no es lo mismo que renta — y ahí está tu mayor oportunidad:</b> tu patrimonio total ronda los %s, pero hoy solo unos %s están invertidos o líquidos generando renta (la cobertura del %s%% de arriba). El resto vive en ladrillo o en tu negocio: es patrimonio, pero no dinero que puedas gastar cada mes." % (_eur(_pat_lib),_eur(_inv_lib),("%.0f"%fi[1])),St("plib2",fontSize=9.3,leading=13,textColor=INK,spaceBefore=5)),
            Paragraph("<b>Y si lo movilizaras:</b> si convirtieras en líquido y pusieras a rentar ese patrimonio ilíquido —rentabilizando lo que está parado y, llegado el momento de simplificar, vendiendo o reduciendo la vivienda que ya no necesites—, tu cobertura pasaría del <b>%s%%</b> de hoy al <b>%s%%</b>%s. Convertir patrimonio dormido en renta es, justamente, donde más mueve la aguja un family office: no se trata solo de ganar más, sino de poner a trabajar lo que ya tienes." % (("%.0f"%fi[1]),("%.0f"%_cob_pot),_libre_txt),St("plib3",fontSize=9.3,leading=13,textColor=INK,spaceBefore=4))]
    if _pens>0 and _gm_lib>0:
        S+=[Paragraph("<b>Ajustado por tu pensión:</b> si cobrarás ~<b>%s</b>/mes de pensión pública, esa renta ya cubrirá parte de tu vida al jubilarte. El capital PROPIO que necesitarías para el resto baja de %s a <b>%s</b>. (El número 25× de arriba asume que te financias el 100%%; este lo ajusta a tu pensión.)" % (_eur(_pens),_eur(fi[0]),_eur(_num_aj)),St("plib",fontSize=9.3,leading=13,textColor=INK,spaceBefore=5))]
    # Alerta de jubilacion: a este ritmo, ¿llegaras a tu libertad antes de los 67?
    try:
        _edad_j=int(float(datos.get("edad") or 0)); _y0_j=fi[3]; _JUB=67
        if _edad_j>0 and (_y0_j is None or (_edad_j+_y0_j)>_JUB):
            if _y0_j is None or (_edad_j+_y0_j)>95:
                _mj="<b>Aviso — a este ritmo, trabajarás más allá de tu jubilación.</b> Con tu ahorro y rentabilidad de hoy, tu patrimonio no alcanza tu libertad financiera. Al llegar a los 67 dependerías solo de tu pensión pública y, muy probablemente, tendrías que seguir generando ingresos despues de la edad de jubilacion. No es destino: acelerar el ahorro o poner a trabajar tu capital cambia esta foto."
            else:
                _desp=int(round(_edad_j+_y0_j-_JUB)); _lleg=int(round(_edad_j+_y0_j))
                _mj=("<b>Aviso — a este ritmo, trabajarás más allá de tu jubilación.</b> A tu ritmo actual alcanzarías tu libertad hacia los <b>%d años</b>: unos <b>%d años después</b> de la edad de jubilacion (67). Es decir, al jubilarte no podrias dejar de depender de tus ingresos. Cada punto que subas tu ahorro o tu rentabilidad adelanta esa fecha. En la p\u00e1gina siguiente tienes las 4 v\u00edas exactas \u2014 cu\u00e1nto subir el ahorro o la rentabilidad \u2014 para adelantarla.") % (_lleg,_desp)
            _mj += " Y no es solo dinero: cada ano de mas atado al trabajo es salud que no vuelve, tiempo con los tuyos, relaciones y aficiones que no se recuperan. Tu libertad financiera es, en el fondo, libertad de vida."
            S+=[Spacer(1,3*mm),_box([Paragraph(_mj,St("jub1",fontSize=10,leading=14,textColor=INK))],"#FBF4E4","#B45309",ancho=160*mm)]
    except Exception:
        pass
    # Fase patrimonial (construccion vs gestion) + palanca del 20% (solo en construccion)
    _rentista_f=bool(extras and extras.get("rentista"))
    _prog_f=fi[1] if (fi and len(fi)>1 and fi[1] is not None) else None
    _gestion=_rentista_f or (_prog_f is not None and _prog_f>=90)
    _tasa_f=fi[2] if (fi and len(fi)>2 and fi[2] is not None) else None
    S+=[Spacer(1,4*mm),Paragraph("Tu fase patrimonial: <b>%s</b>"%("Gestión y preservación" if _gestion else "Construcción de patrimonio"),St("fase",fontSize=10.5,leading=15,textColor=INK))]
    if not _gestion:
        S+=[Paragraph("<i>La fórmula no es «Ingresos − Ahorro = Gastos». Es <b>Ingresos − Estilo de vida = Inversión</b>: "
                      "defines el estilo de vida que quieres, inviertes el resto antes de gastarlo, y trabajas para ensanchar "
                      "esa diferencia subiendo ingresos.</i>",St("formula",fontSize=9.8,leading=14,textColor=GREY,spaceBefore=3,spaceAfter=2))]
    if (not _gestion) and _tasa_f is not None and _tasa_f<10:
        # DICTAMEN firme (banca privada): por debajo del 10% el modelo es estructuralmente vulnerable.
        # Mantiene el guardarrail Adapta (sin catastrofismo) pero con firmeza técnica de consultor.
        S+=[Spacer(1,2*mm),_box_sello([Paragraph("<b>Dictamen: tu modelo es financieramente vulnerable</b>",St("p10a",fontSize=11.5,leading=15,textColor=colors.HexColor("#9A3B2E"),fontName=FB)),
              Paragraph("Con una tasa de ahorro del <b>%.0f%%</b>, tu economía depende de que nada se tuerza: un solo imprevisto severo "
                        "—una baja, una reparación grande, un mes sin ingresos— bastaría para desestabilizarla. No es una opinión, es "
                        "estructura: a este ritmo no se construye colchón ni capital, solo se sobrevive al mes. Requiere intervención "
                        "inmediata sobre tus gastos fijos: la prioridad no es invertir mejor, es liberar margen. Recuperar capacidad de "
                        "ahorro es, hoy, la única decisión que cambia tu trayectoria."%_tasa_f,
                        St("p10b",fontSize=10,leading=14,textColor=INK,spaceBefore=3))],
              "#FBEDEC","#9A3B2E",nota=_rating_ahorro(_tasa_f),ancho=160*mm)]
    elif (not _gestion) and _tasa_f is not None and _tasa_f<20:
        S+=[Spacer(1,2*mm),_box_sello([Paragraph("<b>Tu palanca número uno: la tasa de ahorro</b>",St("p20a",fontSize=11,leading=15,textColor=ACCDK,fontName=FB)),
              Paragraph("Estás en fase de construcción de patrimonio y tu tasa de ahorro es del <b>%.0f%%</b>. Por debajo del 20%%, "
                        "el capital crece despacio y tu libertad se aleja años. El 20%% no es una cifra arbitraria: es el umbral donde "
                        "el interés compuesto empieza a trabajar de verdad a tu favor en lugar de en tu contra. Llevar tu ahorro hacia "
                        "ese nivel es, con diferencia, la decisión de mayor impacto que tienes ahora sobre la mesa."%_tasa_f,
                        St("p20b",fontSize=10,leading=14,textColor=INK,spaceBefore=3))],
              "#FBF4E4","#B45309",nota=_rating_ahorro(_tasa_f),ancho=160*mm)]
    _pat_h=datos.get("patrimonio")
    if (not _gestion) and _pat_h is not None and _pat_h<100000:
        S+=[Spacer(1,2*mm),_box([Paragraph("<b>Tu primer hito no es la libertad total: son los primeros 100.000 €.</b>",St("h100a",fontSize=10.8,leading=15,textColor=ACCDK,fontName=FB)),
              Paragraph("Reunir ese primer capital invertible desde cero es el tramo más difícil del camino —pura constancia—, "
                        "pero también el que más cambia las reglas a tu favor: superado ese punto, tu mentalidad ya es otra, se "
                        "abren mejores opciones y el interés compuesto empieza a hacer el trabajo pesado. Pon ahí tu foco antes "
                        "que en la meta final.",St("h100b",fontSize=9.8,leading=14,textColor=INK,spaceBefore=3))],
              "#EEF2F8","#0F766E",ancho=160*mm)]
    if _gestion:
        S+=[Spacer(1,2*mm),_box([Paragraph("<b>Cambian las reglas: ya no acumulas, preservas.</b>",St("gst1",fontSize=10.8,leading=15,textColor=ACCDK,fontName=FB)),
              Paragraph("Acumular y desacumular son juegos opuestos con las mismas piezas. Mientras construías, el tiempo y los "
                        "vaivenes del mercado jugaban a tu favor. Ahora tu reto es distinto: que el capital dure y rente sin "
                        "sobresaltos. La protección del principal y la liquidez pesan más que exprimir el crecimiento, y un error "
                        "en esta fase se corrige mucho peor que en la de construcción.",St("gst2",fontSize=9.8,leading=14,textColor=INK,spaceBefore=3))],
              "#EEF2F8","#0F766E",ancho=160*mm)]
    S+=[PageBreak()]
    if depth!="esencial":
        _seen=[]
        for _v,_c,_d in plan(p):
            if _c not in _seen: _seen.append(_c)
        for _c in sorted(CAPAS,key=lambda c:p[c]["score"],reverse=True):
            if _c not in _seen: _seen.append(_c)
        def _acc(i):
            return ACCIONES[_seen[i]][0] if i<len(_seen) else None
        S+=[Paragraph("Tu hoja de ruta a 90 d\u00edas",h_sec),
            Paragraph("No es una lista de buenos prop\u00f3sitos: es un tablero de operaciones por fases de urgencia. "
                      "Marca cada casilla cuando lo hagas. Empieza por arriba \u2014 el orden importa.",body)]
        fases=[("#0F766E","Fase 1 \u00b7 Pr\u00f3ximas 72 horas","Cortafuegos: frenar el estr\u00e9s y las fugas",[_acc(0),_acc(1)]),
               ("#B45309","Fase 2 \u00b7 D\u00edas 4-30","Estructura: automatizar y ordenar",[_acc(2),_acc(3)]),
               ("#0284C7","Fase 3 \u00b7 D\u00edas 31-90","Expansi\u00f3n: construir patrimonio",[_acc(4),"Repite el diagn\u00f3stico y compara: ver\u00e1s el movimiento."])]
        rt=[]
        for col,fase,lema,accs in fases:
            rt.append([Paragraph(f"<font color='white'><b>{fase}</b>  \u00b7  {lema}</font>",
                       St("rf",fontSize=9.5,leading=12,textColor=colors.white)),""])
            for a in accs:
                if a: rt.append([Paragraph(a,St("ra",fontSize=9.6,leading=13)),""])
        rtab=Table(rt,colWidths=[148*mm,12*mm])
        sty=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
             ("LEFTPADDING",(0,0),(-1,-1),9),("LINEBELOW",(0,0),(-1,-1),0.4,LINE)]
        ri=0
        for col,fase,lema,accs in fases:
            sty.append(("BACKGROUND",(0,ri),(-1,ri),colors.HexColor(col)))
            sty.append(("SPAN",(0,ri),(0,ri)))
            for a in accs:
                if a:
                    ri+=1
                    sty.append(("BOX",(1,ri),(1,ri),0.8,colors.HexColor("#9CA3AF")))
            ri+=1
        rtab.setStyle(TableStyle(sty))
        S+=[rtab, Spacer(1,5*mm)]
        # === Tu plan, en cifras: cuantificado y gated sobre datos reales ===
        _cif=[]
        _gm=datos.get("gasto_mensual") or 0; _im=max(datos.get("ingreso_mensual",0),0); _pt=datos.get("patrimonio") or 0
        _colobj=round(_gm*3) if _gm else 0
        if _colobj:
            _cif.append("<b>Tu colchón objetivo: %s</b> (3 meses de tus gastos reales). Ábrelo en una cuenta remunerada, separada del día a día, y aliméntalo con una transferencia automática el día 1 de cada mes." % _eur(_colobj))
        if _pt and _colobj and _pt>_colobj:
            _cif.append("Divide tu patrimonio de hoy: <b>%s</b> congelados como fondo intocable de resiliencia y <b>%s</b> como base operativa para invertir o amortizar." % (_eur(_colobj),_eur(_pt-_colobj)))
        _rec=(extras.get("presupuesto") or {}).get("recomendado") if extras else None
        if _rec and _im:
            _cif.append("Págate primero: el día 1, reparte tus <b>%s</b> en cuentas separadas — Necesidades <b>%s</b>, Deseos <b>%s</b>, Construcción <b>%s</b>. Ahorrar lo que sobra no funciona; forzar el reparto, sí." % (_eur(_im),_eur(_rec.get("necesidades",0)),_eur(_rec.get("deseos",0)),_eur(_rec.get("ahorro",0))))
        _dt=extras.get("deuda_tipo") if extras else None
        if _dt and isinstance(_dt,(list,tuple)) and len(_dt)>0 and "freno" in str(_dt[0]).lower():
            _cif.append("Tienes deuda que te resta: lístala con su TAE exacta y amortiza primero la más cara. Eliminar deuda de consumo a tipo alto es la rentabilidad más segura que existe.")
        if extras and (extras.get("presupuesto") or {}).get("empresario"):
            _cif.append("Antes del día 90, audita con tu asesor el mix óptimo entre nómina y dividendos de tu sociedad: extraer por costumbre deja en Hacienda dinero que podría ir a tu patrimonio.")
        if _cif:
            _cp=[Paragraph("<b>Tu plan, en cifras</b>",St("cif0",fontSize=11,leading=15,textColor=ACCDK,fontName=FB))]
            for _x in _cif: _cp.append(Paragraph("<font color='#B45309'>&#9656;</font>  "+_x,St("cifx",fontSize=9.8,leading=14,textColor=INK,leftIndent=4,spaceBefore=3)))
            S+=[_box(_cp,"#FBF4E4","#B45309",ancho=160*mm), Spacer(1,4*mm)]
        S+=[_box([Paragraph("<b>No haces esto solo.</b>",St("ej1",fontSize=11,leading=15,textColor=ACCDK,fontName=FB)),
                  Paragraph("Las tareas de hábito y decisión son tuyas. Pero el trabajo pesado —mover el capital a vehículos "
                            "eficientes, ordenar la fiscalidad, redactar el blindaje legal— lo ejecuta el equipo de Adapta por ti. "
                            "Tú decides; nosotros operamos.",St("ej2",fontSize=10,leading=14,textColor=INK,spaceBefore=3))],
                "#FBF9EC","#C9962B",ancho=160*mm), Spacer(1,4*mm)]
        # Regla de contingencia (kill-switch sano)
        col6=datos.get("gasto_mensual",0)*6
        S+=[_box([Paragraph("<font color='#B45309'><b>Tu regla de contingencia</b></font><br/>"
                f"<font size=9.5>Todo plan necesita un freno de emergencia. El tuyo: si tu fondo l\u00edquido baja de "
                f"<b>{_eur(col6)}</b> (seis meses de gastos) o llega un imprevisto grande, <b>pausa las fases 2 y 3</b> "
                f"y vuelca todo el excedente a reconstruir ese colch\u00f3n antes de seguir. Proteger la base va siempre "
                f"primero; crecer puede esperar unas semanas.</font>",St("kc",fontSize=10.5,leading=15))],
                "#FBF4E4","#B45309",ancho=160*mm)]
        S+=[PageBreak(),
            Paragraph("Tu glosario, a tu medida",h_sec),
            Paragraph("No es un diccionario gen\u00e9rico: hemos incluido solo los conceptos que tus respuestas han activado. "
                      "Cada uno en tres capas \u2014 qu\u00e9 es, qu\u00e9 significa en tu caso y por qu\u00e9 te importa.",body)]
        for t,defn,prati,impacto in glosario(p,datos,fi):
            S.append(KeepTogether([
                Paragraph(f"<b>{t}</b>",St("gt",fontSize=11,leading=14,textColor=ACC,spaceBefore=4)),
                Paragraph(f"<font color='#6B7280'>{defn}</font>",St("gd",fontSize=9.4,leading=13)),
                Paragraph(f"<b>En tu caso:</b> {prati}",St("gp",fontSize=9.6,leading=13)),
                Paragraph(f"<b>Por qu\u00e9 importa:</b> {impacto}",St("gi",fontSize=9.6,leading=13,textColor=colors.HexColor("#9A3412"),spaceAfter=7))]))
        S+=[PageBreak()]
    if depth!="esencial":
        pass  # cuaderno de trabajo eliminado (compresion)
    # cierre
    S+=[Paragraph("Cómo seguir",h_sec),
        Paragraph("Este libro es una foto de hoy, no una condena. La mayoría de las cifras que más te incomodan "
                  "se mueven con uno o dos hábitos bien elegidos. Empieza por el primer punto de tu plan, dale un "
                  "mes, y vuelve a hacer el diagnóstico: verás el movimiento en negro sobre blanco.",body),
        Paragraph("Si compartes tu vida económica con otra persona, el informe de pareja cruza vuestros dos libros "
                  "y señala exactamente dónde divergís — el origen de la mayoría de los conflictos silenciosos por dinero.",body),
        Spacer(1,5*mm),
        Paragraph("Metodología y límites",h_sub),
        Paragraph("Instrumento de 12 capas con dimensiones psicométricas de polaridad consistente. Los percentiles "
                  "se calibran empíricamente frente a la cohorte real de respondentes; mientras la muestra de tu grupo crece, se indican como provisionales. Herramienta "
                  "de autoconocimiento; no sustituye asesoramiento profesional individualizado.",small),
        Paragraph("Modelo de diagnóstico <b>v2.1</b> · válido a la fecha de emisión · recalcula cada 6 meses: "
                  "tu patrimonio y tu vida cambian, y este informe con ellos.",small)]
    if extras and depth!="esencial": S+=_secsafe(seccion_compromiso,extras)
    # === PUENTE ACTO 3 -> ACTO 4: el plan da el QUE; Adapta, el COMO (el siguiente nivel) ===
    if depth!="esencial":
        S+=[_box([Paragraph("<b>Ya tienes el qué. Falta el cómo.</b>",St("pte1",fontSize=12.5,leading=16,textColor=ACCDK,fontName=FB)),
                  Paragraph("Lo que acabas de leer es tu Constitución financiera: la ley por la que se rigen tus decisiones de aquí "
                            "en adelante. Tenerla escrita es la mitad del trabajo. La otra mitad —ejecutar el blindaje y el "
                            "desacoplamiento sin cometer los errores caros que no se ven hasta años después— es exactamente lo que "
                            "un family office hace por ti. Lo que viene no es un anuncio: es el siguiente nivel lógico de tu plan.",
                            St("pte2",fontSize=10.5,leading=15,textColor=INK,spaceBefore=3))],
                "#FBF9EC","#C9962B",ancho=160*mm), Spacer(1,4*mm)]
    if depth!="esencial":
        try:
            portadilla("_pa_t2_4.png", "Acto 4", 'EL SIGUIENTE\nPASO', 'Ejecutar el plan, contigo, con tu family office.')
            S+=[PageBreak(), FullBleedImage("_pa_t2_4.png")]
        except Exception:
            pass
    S+=_secsafe(seccion_adapta,p,datos)
    # === ACTO 4 (cierre): Matriz de Decision Bifurcada (Inaccion vs Adapta), cifras reales ===
    if False:  # "Dos caminos desde aqui" eliminado (compresion)
        _ba=(extras.get("brecha") or {}).get("brecha_anual"); _nl=fi[0] if (fi and fi[0]) else None
        _izq=[]
        if _ba and _ba>0: _izq.append("Sigues dejando escapar unos <b>%s al año</b> que tu trayectoria aún no genera." % _eur(_ba))
        _izq+=["La misma inercia que arrastras, sin revisar.","Rumiación y descontrol: el coste que no aparece en ninguna cuenta, pero lo pagas en sueño y en cabeza."]
        _der=["Activas tu Constitución financiera: reglas claras, decisiones sin ruido.",
              "Trasladas la carga operativa a un family office: el trabajo pesado lo hacemos nosotros.",
              "Blindas tu colchón y pones cada euro a trabajar con intención."]
        if _nl: _der.append("Avanzas, con método, hacia tu número de libertad (<b>%s</b>)." % _eur(_nl))
        _filas=[[Paragraph("<font color='white'><b>Si no haces nada</b></font>",St("mzi",fontSize=11,leading=14,textColor=colors.white,fontName=FB)),
                 Paragraph("<font color='white'><b>El siguiente paso con Adapta</b></font>",St("mzd",fontSize=11,leading=14,textColor=colors.white,fontName=FB))]]
        for i in range(max(len(_izq),len(_der))):
            _filas.append([Paragraph(("&#9656;  "+_izq[i]) if i<len(_izq) else "",small),
                           Paragraph(("&#9656;  "+_der[i]) if i<len(_der) else "",small)])
        _mz=Table(_filas,colWidths=[80*mm,80*mm])
        _mz.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),colors.HexColor("#9A3B2E")),("BACKGROUND",(1,0),(1,0),colors.HexColor("#1D6F42")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
            ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("BACKGROUND",(0,1),(0,-1),colors.HexColor("#FBECE8")),("BACKGROUND",(1,1),(1,-1),colors.HexColor("#EAF5EE")),
            ("LINEBELOW",(0,0),(-1,-1),0.4,LINE)]))
        _fecha_h=cli.get("fecha","hoy")
        _urg=("Este diagnóstico retrata tu estructura a día de <b>%s</b>. " % _fecha_h)
        if _ba and _ba>0: _urg+=("Cada mes que el cuadro sigue igual, ese coste de oportunidad de <b>%s al año</b> no se detiene: corre en tu contra. " % _eur(_ba))
        _urg+="Tu ventana ideal de actuación empieza en las próximas 72 horas."
        S+=[PageBreak(), Paragraph("Dos caminos desde aquí",h_sec),
            Paragraph(_urg,St("urg",fontSize=10.5,leading=15,textColor=INK,spaceAfter=4)),
            Paragraph("El diagnóstico ya está hecho. Lo único que queda es elegir desde dónde sigues:",body),
            Spacer(1,3*mm), _mz]
    # === Manifiesto de cierre: Tus deberes (principios, voz Adapta) ===
    if False:  # "Tus deberes" eliminado (compresion)
        _deb=["Mide.","Corrige.","No hagas ceros.","Mejora cada día un poco.","Comprométete a lograrlo.",
              "Haz más cosas que funcionen.","Elimina lo que no te acerque a tus objetivos.","Define tu estilo de vida y cómo sufragarlo.",
              "Piensa en tu peor escenario.","Detecta oportunidades.","Rentabiliza tu dinero.","Ahorra para invertir.",
              "Valora tu tiempo.","Pasa a la acción.","Asesórate."]
        _dp=[Paragraph("Tus deberes",h_sec),
             Paragraph("Si te quedas con una sola página de todo este libro, que sea esta. No es teoría: es la disciplina "
                       "que separa a quien sueña su libertad de quien la construye. Léela cada mes.",body),Spacer(1,3*mm)]
        for _d in _deb:
            _dp.append(Paragraph("<font color='#B8860B'>&#9670;</font>  <b>%s</b>"%_d,St("deb",fontSize=11.5,leading=17,leftIndent=6,spaceAfter=1)))
        _dp+=[Spacer(1,4*mm),Paragraph("No esperes una solución mágica. La aplicación honesta de esta lista —tan lejos como "
              "quieras llevarla— es lo que cambia la realidad de tus finanzas, de tu tiempo y, con ellos, de tu vida.",
              St("debc",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=10,spaceBefore=2))]
        S+=[PageBreak()]+_dp
    if extras: S+=_secsafe(seccion_conclusion,extras)
    # DICTAMEN de comportamiento (convierte el test en prosa ejecutiva, antes del anexo crudo)
    S+=_secsafe(seccion_dictamen_comportamiento,resp)
    # ANEXO: respuestas del cliente (transparencia; sin mostrar scores)
    NUM_MAP={"C2-1":"gasto_mensual","C2-2":"ingreso_mensual","C2-3":"ahorro_mensual","C2-4":"patrimonio","C2-5":"edad"}
    S+=[PageBreak(), Paragraph("Anexo \u2014 Tus respuestas",h_sec),
        Paragraph("Para total transparencia: estas son las preguntas que respondiste y lo que elegiste. "
                  "Tu diagn\u00f3stico se basa exactamente en esto, ni m\u00e1s ni menos.",body)]
    for capa in INST["capas"]:
        rows=[[Paragraph("<b>Pregunta</b>",small),Paragraph("<b>Tu respuesta</b>",small)]]
        bgs=[]; ri=1
        for it in capa["items"]:
            if it.get("atencion"): continue   # control de atencion: fuera del anexo
            sc=None; na=False
            if it["tipo"]=="escala":
                idx=resp.get(it["id"])
                if idx is not None:
                    ans=it["opciones"][idx]["texto"]; sc=it["opciones"][idx]["score"]
                else: ans=""; na=True
            else:
                v=datos.get(NUM_MAP.get(it["id"],"")); na=(v is None); ans=("%s %s"%(v,it.get("unidad",""))).strip() if v is not None else ""
            if na: continue   # purga premium: no mostramos preguntas que el cliente no respondio
            rows.append([Paragraph("<font color='#33415C'>%s</font>"%_limpiar_txt(it["texto"]),small),Paragraph("<i>%s</i>"%_limpiar_txt(ans),small)])
            if ri%2==0:
                bgs.append(("BACKGROUND",(0,ri),(-1,ri),colors.HexColor("#EEF2F8")))
            ri+=1
        if len(rows)<=1: continue   # capa sin respuestas reales: no imprimir tabla vacia
        t=Table(rows,colWidths=[104*mm,52*mm],repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),LIGHT),("LINEBELOW",(0,0),(-1,0),0.6,LINE),
            ("LINEBELOW",(0,1),(-1,-1),0.3,LINE),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("FONTNAME",(0,0),(-1,0),FB)]+bgs))
        S+=[Paragraph("%s \u00b7 %s"%(capa["code"],capa["nombre"]),h_sub), t]
    _const=None
    try:
        if _LEGADO_OK and extras: _const=_legado_pages.hero_close(extras,depth=depth)
    except Exception:
        _const=None
    if _const: S+=[PageBreak(), FullBleedImage(_const)]
    S+=[PageBreak(), DarkPage(titulo="ADAPTA  ·  family office",
        sub="Tu Libro Financiero · Documento confidencial",
        legal="Adapta Family Office · Herramienta de autoconocimiento financiero; no constituye asesoramiento personalizado regulado. Las estimaciones son orientativas. © 2026.")]
    global CLIENTE_NOMBRE; CLIENTE_NOMBRE=(cli.get("nombre") or "")
    # --- saneador: colapsa PageBreaks consecutivos (evita paginas en blanco) ---
    _clean=[]
    for _f in S:
        if isinstance(_f, PageBreak) and _clean and isinstance(_clean[-1], PageBreak):
            continue
        _clean.append(_f)
    while _clean and isinstance(_clean[-1], PageBreak):
        _clean.pop()
    S=_clean
    doc=SimpleDocTemplate(out,pagesize=A4,topMargin=22*mm,bottomMargin=20*mm,leftMargin=22*mm,rightMargin=22*mm,
                          title="Tu Libro Financiero — ITAP")
    doc._cliente=(cli.get("nombre") or "")
    if NumberedCanvas: doc.build(S,onFirstPage=deco,onLaterPages=deco,canvasmaker=NumberedCanvas)
    else: doc.build(S,onFirstPage=deco,onLaterPages=deco)
    print("PDF OK ->",out)

def build_book(resp, datos, cli, outpath, depth="completo", baremo=None, sintesis=None, extras=None, arq_override=None):
    """API entrypoint: genera el libro PDF en outpath."""
    build(cli, resp, datos, outpath, depth, baremo, sintesis=sintesis, extras=extras, arq_override=arq_override)
    return outpath

# ---------- v2: libro sobre el instrumento adaptativo ----------
_INST_V2=None
def _cargar_v2():
    global _INST_V2
    if _INST_V2 is None:
        _INST_V2=json.load(open("itap_v2.json",encoding="utf-8"))
        _FAC_FIX={"Alto interes":"Alto interés","Concentración geografica":"Concentración geográfica",
            "Exito":"Éxito","Fuente unica":"Fuente única","Polvora seca":"Pólvora seca","Colchon":"Colchón",
            "Anticiclico":"Anticíclico","Creep ingreso":"Inflación del estilo de vida","Número fi":"Tu cifra de libertad",
            "Plan b":"Plan B","Plan b crisis":"Plan B de crisis","Sistema cajas":"Sistema de cuentas",
            "Anticipa grandes":"Anticipa gastos grandes","Carga cuota":"Carga de la cuota","Relación deuda":"Relación deuda/ingresos",
            "Conoce gasto":"Conoces tu gasto","Tijera":"Tijera de ahorro","Oculto":"Gasto oculto","Fuga":"Fuga de caja",
            "Coste de tu inversión":"Comisiones de inversión","Expectativa rentab.":"Expectativa de rentabilidad",
            "Amenaza sector":"Amenaza del sector","Comparación circulo":"Comparación con tu círculo",
            "Techo ingresos":"Techo de ingresos","Deuda imagen":"Deuda por imagen"}
        for _c in _INST_V2.get("capas",[]):
            _fd=_c.get("facetas")
            if isinstance(_fd,dict):
                for _k in list(_fd.keys()):
                    _fd[_k]=_FAC_FIX.get(_fd[_k],_fd[_k])
    return _INST_V2

def build_book_v2(resp, datos, cli, outpath, perfil_in=None, depth="completo", baremo=None, sintesis=None, extras=None, arq_override=None):
    """Genera el libro usando el instrumento v2 (12 capas adaptativas) + secciones brecha/palancas."""
    global INST, CAPAS
    inst_v2=_cargar_v2()
    _bak_inst, _bak_capas = INST, CAPAS
    INST=inst_v2; CAPAS={c["code"]:c for c in inst_v2["capas"]}
    try:
        if arq_override is None and perfil_in:
            try:
                import score_v2 as _sv
                arq_override=_sv.arq_desde_perfil(perfil_in)
            except Exception:
                arq_override=None
        build(cli, resp, datos, outpath, depth, baremo, sintesis=sintesis, extras=extras, arq_override=arq_override)
    finally:
        INST=_bak_inst; CAPAS=_bak_capas
    return outpath
