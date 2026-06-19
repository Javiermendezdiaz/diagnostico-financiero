# -*- coding: utf-8 -*-
"""ITAP — Generador del 'Libro Financiero' (informe PDF narrativo, Tier 2)."""
import json, math, statistics
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
# --- Piel Legado OSCURA (cuerpo coherente con portada/cierre) ---
INK=colors.HexColor("#E7ECF5"); ACC=colors.HexColor("#F2F6FC"); ACCDK=colors.HexColor("#FFFFFF")
GREY=colors.HexColor("#93A2BC"); LIGHT=colors.HexColor("#13243F"); LINE=colors.HexColor("#2A3A5C")
AMARILLO=colors.HexColor("#FDD731"); NEGRO=colors.HexColor("#020203")
PAPER=colors.HexColor("#0B1A33"); BANDC=["#2FAE6E","#D4A53A","#E08C42","#E5675C"]
PAGEBG=colors.HexColor("#0A1830")  # fondo navy del cuerpo
BLUEACC=colors.HexColor("#3D7DFF")

# ---------- scoring ----------
def phi(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def pctil(s): return round(100*(1-phi((s-45.0)/17.0)))
def peso(it): return 0.5 if "metacognición" in it.get("dimensiones","") else 1.0
def banda(capa,s):
    for i,b in enumerate(capa["bandas"]):
        if b["min"]<=s<=b["max"]: return i,b["etiqueta"]
    return 3,capa["bandas"][-1]["etiqueta"]
def score_capa(capa,resp):
    fac={}
    for it in capa["items"]:
        if it["tipo"]!="escala": continue
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
            idx=resp.get(it["id"])
            if idx is None: continue
            for t in [x for x in it.get("dimensiones","").split("·") if x in TRANS]:
                tr[t].append(it["opciones"][idx]["score"])
    trans={t:(round(statistics.mean(v),1) if v else None) for t,v in tr.items()}
    return out,trans,round(statistics.mean([v["score"] for v in out.values()]),1)
def fi_metrics(d):
    gasto=d.get("gasto_mensual") or 0; ingreso=d.get("ingreso_mensual") or 0
    pat=d.get("patrimonio") or 0; aho=d.get("ahorro_mensual") or 0
    fi=gasto*12*25; pct=round(100*pat/fi,1) if fi else 0.0
    tasa=round(100*aho/ingreso,1) if ingreso else 0.0
    r,pv,m,n=0.05/12,pat,aho,0
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
 "C11":"si tu dinero solo se defiende o además construye: tu capacidad real de hacer crecer lo que ya tienes y de acercar la vida que quieres."}
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
 "C11":"elige una palanca de crecimiento —una segunda fuente o poner a trabajar tu excedente— y da el primer paso esta semana."}

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
 "C11":"Un patrimonio que solo se defiende se queda quieto mientras la vida que quieres se encarece. Sin una palanca de crecimiento, el esfuerzo de hoy no compra el futuro que imaginas: solo sostiene el presente."}
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
 "C11":"Pasar de defender a construir cambia el juego: cuando el excedente y el patrimonio trabajan por ti, el tiempo deja de ser tu enemigo y se convierte en tu mayor aliado."}
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
 "C11":[PASO["C11"],"Pon a trabajar el excedente y el patrimonio dormido con un plan a años vista, no en cuentas a la vista.","Define tu brecha exacta hacia la vida ideal y elige la palanca —ingresos o eficiencia— que más la acorte."]}

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
 "C11":"Defender protege lo que tienes; construir es lo único que te acerca a lo que quieres."}

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
 "C11":"\u00bfTu dinero est\u00e1 hoy construyendo la vida que quieres, o solo defendiendo la que ya tienes?"}

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
 "C3":"Tu defensa flojea por diseño, no por falta de medios: monta el colchón antes que cualquier inversión.",
 "C4":"El gasto no se controla con fuerza de voluntad, sino con topes automáticos: ponlos y olvídate.",
 "C5":"Aquí el riesgo es de papeles, no de dinero: ordena la protección y dormirás distinto.",
 "C6":"El impulso de aparentar se doma con reglas, no con culpa: 72 horas de pausa antes de comprar.",
 "C7":"No dependas de tu voluntad para diversificar: fíjate un objetivo de % por fuente y muévelo.",
 "C8":"La antifragilidad se construye con pequeñas apuestas, no con un gran salto: empieza por una.",
 "C9":"Aquí el problema no es de capacidad, es de sistema: automatiza el destino del dinero el día 1.",
 "C10":"La deuda no se vence con un sacrificio puntual, sino con un plan de amortización que no dependa de ti.",
 "C11":"Tu palanca no necesita esfuerzo extra, necesita una decisión: elige una y actívala este trimestre."}
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
 "C11":"Tienes potencia sin usar: activarla ahora es lo que más cambia tu trayectoria."}
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
 "C11":"tu mayor palanca sigue sin activar: cada mes que no la tocas es crecimiento que no llega."}
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
 "C11":"tienes capacidad de sobra sin usar; activarla ahora es lo que más te cambia el cuadro."}

def interpretar(nombre,s,bl,bi,peor,code=None):
    nl=nombre.lower()
    if bi==0: return (f"En {nl} estás en terreno sólido (salud {100-s:.0f}/100, «{bl}»). Es una de tus fortalezas. "
                      f"No la des por garantizada: lo que hoy va bien también se cuida.")
    if bi==1: return (f"En {nl} vas bien, con margen (salud {100-s:.0f}/100, «{bl}»). El punto que más pesa ahora es "
                      f"«{peor}»; ahí tienes la mejora más fácil y rentable.")
    if bi==2:
        c=CIERRE2.get(code,"todavía no duele, pero ya te está restando margen sin que lo notes.")
        return (f"{nombre} muestra sobrecarga (salud {100-s:.0f}/100, «{bl}»), sobre todo en «{peor}»: {c}")
    c=CIERRE3.get(code,"no admite más demora: cada mes que pasa, el agujero se ensancha solo.")
    return (f"{nombre} está en zona crítica (salud {100-s:.0f}/100, «{bl}»), en especial en «{peor}»: {c}")

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
        o.append(("Estás financiando una imagen","Gasto de estatus más deriva de estilo de vida: parte de tu esfuerzo se va en aparentar. Aquí hay margen rápido y silencioso."))
    if tr["VINCULO"] is not None and tr["VINCULO"]>=50:
        o.append(("El dinero tensa tu vínculo","Hay fricción o falta de transparencia con tu pareja o familia: un multiplicador de todo lo demás. El informe de pareja lo aborda de frente."))
    if not o: o.append(("Un perfil equilibrado","No tienes focos críticos. Tu trabajo es de optimización fina, no de contención: pulir una maquinaria que ya funciona."))
    return o
def plan(p):
    d=[]
    for code,capa in CAPAS.items():
        for f,val in p[code]["facetas"].items():
            if val>=60: d.append((val,code,capa["facetas"][f]))
    d.sort(reverse=True); return d[:6]

# ---------- radar ----------
def radar_png(p,path):
    SHORT={"C1":"Salud emocional","C2":"Libertad","C3":"Resistencia","C4":"Control del gasto","C5":"Protección","C6":"Gasto con sentido","C7":"Diversificación","C8":"Antifragilidad","C9":"Eficiencia de flujo","C10":"Salud de deuda","C11":"Crecimiento"}
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
        ax.plot(th,[r]*len(th),color="#E4E1D5",linewidth=0.8,zorder=1)
    # radios suaves
    for a in ang[:-1]:
        ax.plot([a,a],[0,100],color="#EEEBE0",linewidth=0.7,zorder=1)
    # nucleo saludable
    ax.fill_between(th,70,100,color="#1D6F42",alpha=0.06,zorder=1)
    ax.set_yticks([25,50,75]); ax.set_yticklabels(["25","50","75"],color="#B9B5A6",size=7.5)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels,size=8,color="#C9D2E0")
    ax.tick_params(axis='x',pad=9)
    # silueta de referencia tenue (salud 50) para que SIEMPRE haya forma legible, aun en perfiles muy bajos
    ref=[50]*len(ang)
    ax.plot(ang,ref,color="#C9C4B4",linewidth=0.9,linestyle=(0,(4,3)),zorder=2)
    # poligono: doble relleno para profundidad + linea grafito + vertices
    ax.fill(ang,v,color=fill,alpha=0.16,zorder=3)
    ax.fill(ang,v,color=fill,alpha=0.40,zorder=4)
    ax.plot(ang,v,color="#E7ECF5",linewidth=2.4,zorder=5)
    ax.scatter(ang[:-1],vsal,s=30,color="#E7ECF5",zorder=6,edgecolors="white",linewidths=1.1)
    plt.tight_layout(); fig.savefig(path,dpi=160,transparent=True); plt.close(fig)

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
        c=s.canv; W=s.w; c.setFillColor(colors.HexColor("#16263F")); c.roundRect(0,0,W,s.h,2,fill=1,stroke=0)
        h=100-s.v  # se dibuja SALUD (alto=bien): barra llena y verde = sano
        col=BANDC[0] if h>=75 else BANDC[1] if h>=50 else BANDC[2] if h>=25 else BANDC[3]
        c.setFillColor(colors.HexColor(col)); c.roundRect(0,0,max(3,W*h/100),s.h,2,fill=1,stroke=0)

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
        c.setFillColor(colors.HexColor("#0F1E33")); c.rect(-22*mm, -20*mm, A4[0], A4[1], fill=1, stroke=0)
        cx=self.w/2.0
        if self.numero:
            c.setFillColor(colors.HexColor("#1C3257")); c.setFont(FB,150)
            c.drawCentredString(cx, self.h-150*mm, self.numero)
        c.setFillColor(colors.HexColor("#FDD731")); c.setFont(FB,22)
        c.drawCentredString(cx, self.h/2.0+6*mm, self.titulo or "ADAPTA")
        if self.sub:
            c.setFillColor(colors.HexColor("#C9D2E0")); c.setFont(FR,11)
            c.drawCentredString(cx, self.h/2.0-6*mm, self.sub)
        if self.legal:
            c.setFillColor(colors.HexColor("#6B7A92")); c.setFont(FR,7.5)
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
    # Fondo navy Legado (cuerpo coherente con portada y cierre)
    cv.setFillColor(PAGEBG); cv.rect(0,0,A4[0],A4[1],fill=1,stroke=0)
    # Cabecera editorial (desde la pagina 2): cliente | firma
    if doc.page>1:
        cv.setFillColor(GREY); cv.setFont(FR,7)
        cv.drawString(22*mm,A4[1]-12*mm,((getattr(doc,"_cliente",None) or CLIENTE_NOMBRE or "Tu Libro Financiero")[:42]).upper())
        cv.drawRightString(A4[0]-22*mm,A4[1]-12*mm,"ADAPTA FAMILY OFFICE")
        cv.setStrokeColor(LINE); cv.setLineWidth(0.4); cv.line(22*mm,A4[1]-14*mm,A4[0]-22*mm,A4[1]-14*mm)
    # Pie: nota confidencial (el numero de pagina lo pone NumberedCanvas)
    cv.setFillColor(GREY); cv.setFont(FR,7)
    cv.drawCentredString(A4[0]/2,12*mm,"Documento confidencial · Adapta Family Office")
    cv.setStrokeColor(LINE); cv.setLineWidth(0.5); cv.line(22*mm,16*mm,A4[0]-22*mm,16*mm)
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
 "C11":("Estrategia de crecimiento patrimonial","Ponemos a trabajar tu excedente y tu patrimonio con un plan a a\u00f1os vista \u2014 para que tu dinero deje de defenderse y empiece a construir la vida que quieres.","https://www.adaptafamilyoffice.com/casos/banca-privada")}

def seccion_adapta(p):
    out=[PageBreak(), Paragraph("El siguiente paso con Adapta",h_sec),
         Paragraph("Este libro es un mapa. <b>Adapta Family Office</b> es quien lo recorre contigo: 25 a\u00f1os "
                   "cuidando patrimonios familiares, con visi\u00f3n integral y sin productos propios ni conflictos de inter\u00e9s.",body),
         Paragraph("Por lo que dice tu diagn\u00f3stico, esto es lo que m\u00e1s te conviene ahora mismo:",body)]
    peores=sorted(CAPAS,key=lambda c:p[c]["score"],reverse=True)[:2]
    for code in peores:
        ti,de,url=ADAPTA[code]
        out.append(Paragraph(f"<font color='#0284C7'><b>&#9656; #8226; {ti}</b></font>",St("ad1",fontSize=11,leading=14,spaceBefore=6,spaceAfter=2)))
        out.append(Paragraph(de,St("ad2",fontSize=10,leading=14,leftIndent=8,spaceAfter=2)))
        out.append(Paragraph(f"<a href='{url}'><font color='#1A1A17'>Ver c\u00f3mo lo trabajamos &#8594;</font></a>",St("ad3",fontSize=9.5,leading=13,leftIndent=8,spaceAfter=8)))
    out+=[Spacer(1,3*mm),
          Paragraph("Por d\u00f3nde empezamos",h_sub),
          Paragraph("Como en todo lo que hacemos en Adapta: una conversaci\u00f3n inicial, sin compromiso. Te escuchamos "
                    "primero, te proponemos despu\u00e9s. Como debe ser.",
                    St("cta",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=10,spaceBefore=2)),
          Spacer(1,2*mm),
          Paragraph("<b>Reserva tu conversaci\u00f3n:</b> <a href='https://www.adaptafamilyoffice.com/informe'><font color='#0284C7'>adaptafamilyoffice.com</font></a>  &#183;  "
                    "<b>WhatsApp:</b> <a href='https://wa.me/34683343531'><font color='#0284C7'>+34 683 34 35 31</font></a>  &#183;  info@adaptafamilyoffice.com",
                    St("cta2",fontSize=9.5,leading=14))]
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
    ax.set_xticks(range(4)); ax.set_xticklabels(labels,size=9,color="#C9D2E0")
    ax.annotate(_eur(ing),(0,ing),ha="center",va="bottom",size=8.5,color="#0F766E",weight="bold")
    ax.annotate(_eur(gas),(1,ing-gas/2),ha="center",va="center",size=8.5,color="white",weight="bold")
    ax.annotate(_eur(aho),(2,ing-gas-aho/2),ha="center",va="center",size=8.5,color="white",weight="bold")
    ax.annotate(_eur(abs(libre)),(3,abs(libre)),ha="center",va="bottom",size=8.5,
                color="#C9D2E0" if libre>=0 else "#9A3B2E",weight="bold")
    ax.set_ylim(0,ing*1.15); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#3A4F75"); ax.tick_params(axis="y",labelsize=7,colors="#9CA3AF")
    ax.set_title("De cada euro que entra, a dónde va",size=10,color="#EAF0FA",weight="bold",pad=8)
    plt.tight_layout(); fig.savefig(path,dpi=150,transparent=True); plt.close(fig)
    return libre

def proyeccion_chart(datos, path, r=0.05):
    import matplotlib.pyplot as plt
    edad=int(datos.get("edad",40)); meta_edad=max(EDAD_JUBILACION, edad+5); anos=max(meta_edad-edad,1)
    pat=datos.get("patrimonio",0) or 0; aho=(datos.get("ahorro_mensual",0) or 0)*12
    ing=datos.get("ingreso_mensual",0) or 0; gas=datos.get("gasto_mensual",0) or 0
    superavit=max(0,(ing-gas))*12; inv=datos.get("inversiones_liquidas"); colch=datos.get("colchon_liquido") or 0
    xs=list(range(edad,meta_edad+1))
    def grow(cap0,aport):
        v=cap0; out=[v]
        for _ in range(anos): v=v*(1+r)+aport; out.append(v)
        return out
    fig,ax=plt.subplots(figsize=(6.4,3.2))
    if inv is not None:
        inv=inv or 0; parado=max(0,colch-gas*6)
        e1=[v+parado for v in grow(inv,aho)]          # Inaccion: solo lo invertido trabaja; parado plano
        e2=[v+parado for v in grow(inv,superavit)]     # Optimizar flujo: invierte el superavit real
        e3=grow(inv+parado,superavit)                  # Completa: tambien pone a trabajar lo parado
        ax.plot(xs,e1,color="#9A3B2E",lw=2.0,label="Inacción (como hoy)")
        ax.plot(xs,e2,color="#B8860B",lw=2.0,ls="--",label="Optimizar tu flujo")
        ax.plot(xs,e3,color="#1D6F42",lw=2.4,label="Estrategia completa")
        ax.fill_between(xs,e1,e3,color="#1D6F42",alpha=0.06)
        for ser,col,va in [(e1,"#9A3B2E","top"),(e3,"#1D6F42","bottom")]:
            ax.scatter([meta_edad],[ser[-1]],color=col,zorder=5)
            ax.annotate(_eur(ser[-1]),(meta_edad,ser[-1]),ha="right",va=va,size=8,color=col,weight="bold")
        lo,hi,modo=e1[-1],e3[-1],"3"
        titulo="Tres caminos para tu patrimonio (sobre tu liquidez invertible, al 5%/año)"
    else:
        base=grow(pat,aho); mejora=grow(pat,aho+0.05*ing*12)  # ahorro ACTUAL + 5 puntos extra (no sustituir)
        ax.plot(xs,base,color="#0284C7",lw=2.2,label="Si sigues igual")
        ax.plot(xs,mejora,color="#1D6F42",lw=2.2,ls="--",label="Si ahorras 5 puntos más")
        ax.fill_between(xs,base,mejora,color="#1D6F42",alpha=0.08)
        for ser,col,va in [(base,"#0284C7","top"),(mejora,"#1D6F42","bottom")]:
            ax.scatter([meta_edad],[ser[-1]],color=col,zorder=5)
            ax.annotate(_eur(ser[-1]),(meta_edad,ser[-1]),ha="right",va=va,size=8,color=col,weight="bold")
        lo,hi,modo=base[-1],mejora[-1],"2"
        titulo="Tu patrimonio proyectado a la jubilación (estimación al 5%/año)"
    ax.set_xlabel("Edad",size=8,color="#9FB0C9"); ax.tick_params(labelsize=7,colors="#9CA3AF")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#3A4F75"); ax.spines["bottom"].set_color("#3A4F75"); ax.grid(False)
    ax.legend(fontsize=8,frameon=False,loc="upper left",labelcolor="#C9D2E0")
    ax.set_title(titulo,size=10,color="#EAF0FA",weight="bold",pad=8)
    plt.tight_layout(); fig.savefig(path,dpi=150,transparent=True); plt.close(fig)
    return lo,hi,meta_edad,modo

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
    ax.text(0,0,_eur(tot),ha="center",va="center",fontsize=11.5,weight="bold",color="#E7ECF5")
    ax.legend([f"{l}  ·  {_eur(v)}  ({v/tot*100:.0f}%)" for l,v,_ in pares],
              loc="center left",bbox_to_anchor=(1.0,0.5),frameon=False,fontsize=8.6,labelcolor="#C9D2E0")
    ax.set(aspect="equal"); plt.tight_layout()
    fig.savefig(path,dpi=150,transparent=True,bbox_inches="tight"); plt.close(fig)
    return True

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

def _lineas(n=3, ancho=160*mm, alto=7*mm):
    rows=[[""] for _ in range(n)]
    return Table(rows,colWidths=[ancho],rowHeights=[alto]*n,
        style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.5,colors.HexColor("#2A3A5C")),
          ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))

def report_id(nombre, fecha):
    import hashlib
    ini=''.join([w[0] for w in (nombre or 'X').split()[:2]]).upper() or 'X'
    h=hashlib.sha1((str(nombre)+str(fecha)).encode('utf-8')).hexdigest()[:5].upper()
    return f"ITAP-{ini}-{h}"

def valor_hora(datos):
    return max(datos.get("ingreso_mensual",0),0)/160.0

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
        style=TableStyle([("BACKGROUND",(0,0),(0,0),colors.HexColor("#102619")),
          ("BACKGROUND",(1,0),(1,0),colors.HexColor("#0E2236")),
          ("BACKGROUND",(0,1),(0,1),colors.HexColor("#2A1414")),
          ("BACKGROUND",(1,1),(1,1),colors.HexColor("#2A2010")),
          ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
          ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
          ("LINEBELOW",(0,0),(-1,0),3,PAGEBG),("LINEAFTER",(0,0),(0,-1),3,PAGEBG)])))
    out.append(PageBreak())
    cashflow_waterfall(datos,"_cash.png")
    out+=[KeepTogether([Paragraph("Tu flujo de caja",h_sub),
          Image("_cash.png",width=160*mm,height=75*mm,hAlign="CENTER")])]
    tap=tapon_coste(datos)
    if tap:
        exceso,coste=tap
        vnh=valor_hora(datos)
        horas=(coste/12)/vnh if vnh>0 else 0
        coste10=exceso*(1-(1/(1.03**10)))  # poder adquisitivo erosionado en 10 años al 3%
        out.append(_box([Paragraph(f"<font color='#B45309'><b>La auditoría del tapón</b></font><br/>"
            f"<font size=9.5>Tienes unos <b>{_eur(exceso)}</b> de liquidez por encima de un colchón sano de 6 meses. "
            f"Parada y sin invertir, no te cuesta {_eur(coste)} hoy: te cuesta el tiempo. Proyectado a diez años, "
            f"esa cifra pierde alrededor de <b>{_eur(coste10)} de poder adquisitivo</b> si la inflación ronda el 3% anual. "
            f"No es prudencia: es un peaje invisible que pagas por no decidir. Mover una parte a algo que al menos "
            f"preserve su valor es de las decisiones más rentables y menos arriesgadas que tienes sobre la mesa.</font>",
            St("tp",fontSize=10.5,leading=15))],"#2A2010","#B45309",ancho=160*mm))
    out.append(PageBreak())
    f65,m65,medad,modo=proyeccion_chart(datos,"_proy.png")
    if modo=="3":
        narr=(f"Si dejas tu dinero como hoy, a los {medad} rondarías los <b>{_eur(f65)}</b>. Poniendo a trabajar tu "
              f"liquidez ociosa e invirtiendo tu excedente real, llegarías a <b>{_eur(m65)}</b>. Esa diferencia "
              f"—<b>{_eur(m65-f65)}</b>— no es suerte ni mercado: es el coste de no decidir. (Estimación al 5% anual sobre "
              f"tu liquidez invertible, sin contar tu vivienda; orientativa, no una promesa.)")
    else:
        narr=(f"Si mantienes tu ritmo actual, a los {medad} rondarías los <b>{_eur(f65)}</b>. Subiendo tu ahorro cinco "
              f"puntos, esa cifra sube a <b>{_eur(m65)}</b>: la diferencia entre ambas líneas es, literalmente, el precio de "
              f"no decidir. (Estimación a un 5% anual; orientativa, no una promesa de rentabilidad.)")
    out+=[KeepTogether([Paragraph("Hacia dónde vas",h_sub),
          Image("_proy.png",width=160*mm,height=75*mm,hAlign="CENTER")]),
          Paragraph(narr,body), PageBreak()]
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
        out+=[Paragraph("1 · El valor de tu hora",h_sub),
              Paragraph(f"Tu hora de vida trabajada vale aproximadamente <b>{_eur(vnh)}</b> (ingreso neto ÷ 160 h). "
                        f"Deja de pensar en euros y empieza a pensar en horas de vida.{extra}",body),
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
                    ("TOPPADDING",(0,0),(-1,0),3)]))],"#15243C","#0284C7",ancho=160*mm),
          PageBreak()]
    return out

def glosario(p, datos, fi):
    """Glosario dinamico: solo terminos activados por las respuestas del usuario."""
    g=[]
    # Nucleo siempre presente
    g.append(("Número de libertad financiera",
        "El patrimonio que, invertido, cubre tus gastos para siempre (regla práctica: gasto anual × 25).",
        f"El tuyo ronda los {_eur(fi[0])}; hoy lo tienes cubierto en torno a un {fi[1]:.0f}%.",
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
            "Financiación al consumo —tarjetas revolving, microcréditos— a tasas de doble dígito.",
            "Tu capa de deuda puntuó alto: si arrastras alguna de este tipo, es tu prioridad absoluta.",
            "El interés compuesto jugando en tu contra. Atacar la más cara primero es la mejor inversión que existe."))
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

def seccion_extras(extras):
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
                    Paragraph(f"Tu número de libertad para <b>esa</b> vida (regla 25×): <b>{_eur(br['numero_ideal'])}</b>.{_na}",
                              St("brx2",fontSize=9.6,leading=14,textColor=GREY,spaceBefore=4))],
                   "#23200F","#B45309",ancho=160*mm)]
        mapr={"en rumbo":"Y tú mismo lo lees así: <b>en rumbo</b>. Las matemáticas te acompañan; el trabajo es no desviarte.",
              "espejismo":"Y tú mismo lo nombras: <b>espejismo</b>. Vives bien el presente mientras el futuro se aleja en silencio.",
              "vía muerta":"Y tú mismo lo reconoces: <b>vía muerta</b>. Sin cambiar de modelo, esa vida seguirá siendo una fantasía. La buena noticia: el modelo se cambia."}
        if br.get("reconocimiento") in mapr:
            out.append(Paragraph(mapr[br["reconocimiento"]],St("brr",fontSize=10,leading=14,spaceBefore=4)))
    if pal:
        out+=[Spacer(1,4*mm), Paragraph("Tus palancas de crecimiento",h_sub),
              Paragraph("No son consejos genéricos: salen de tus propios números. En orden de impacto.",small)]
        for ti,tx in pal:
            out.append(Paragraph(f"<font color='#0F766E'>&#9656;</font>  <b>{ti}</b>",St("plt",fontSize=10.5,leading=14,spaceBefore=5)))
            out.append(Paragraph(tx,St("plx",fontSize=9.7,leading=14,leftIndent=12,spaceAfter=3)))
    if con:
        out+=[Spacer(1,4*mm), Paragraph("Lo que no te cuadra (y conviene mirar)",h_sub),
              Paragraph("Las grietas más caras de un plan viven en la distancia entre lo que dices, lo que sientes y lo que miden tus números. Estas son las tuyas:",small)]
        for ti,tx in con:
            out.append(Paragraph(f"<font color='#9A3B2E'>&#9656;</font>  <b>{ti}</b>",St("cot",fontSize=10.5,leading=14,spaceBefore=5)))
            out.append(Paragraph(tx,St("cox",fontSize=9.7,leading=14,leftIndent=12,spaceAfter=3)))
    rt=extras.get("ratios") or []
    if rt:
        _RC={"verde":"#1D6F42","ambar":"#B8860B","rojo":"#9A3B2E","info":"#7A7A72"}
        out+=[Spacer(1,5*mm), Paragraph("Tus ratios financieros",h_sub),
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
                              St("fnt",fontSize=10.5,leading=15))],"#15243C","#0F766E",ancho=160*mm)]
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
            out.append(Paragraph("<font color='#B45309'>&#9656;</font>  <b>Separa familia y negocio.</b> Tu cuota de autónomos, tus tributos y la gestoría <b>no son gasto de vida familiar</b>: mezclarlos distorsiona tu coste de vida real y tu verdadera capacidad de ahorro. Dos cuentas, dos presupuestos, siempre.",St("pre",fontSize=9.7,leading=14,spaceBefore=4,leftIndent=4)))
    vi=extras.get("vivienda")
    if vi and vi.get("modo"):
        _sevc={"alta":"#9A3B2E","media":"#B45309","baja":"#0F766E"}.get(vi.get("severidad"),"#B45309")
        _fnd={"alta":"#2A1414","media":"#23200F","baja":"#15243C"}.get(vi.get("severidad"),"#23200F")
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
    return out

def seccion_compromiso(extras):
    """Cierre: protocolo de revisión a 6 meses + Contrato contigo mismo (firma presente/futuro)."""
    if not extras: return []
    cmp=extras.get("compromiso")
    out=[PageBreak(), Paragraph("Tu revisión a 6 meses",h_sec),
         Paragraph("Un patrimonio no se gestiona una vez: se revisa. Cada seis meses, sin excepciones, "
                   "siéntate treinta minutos y recalcula. Esto es lo que se mira:",body), Spacer(1,2*mm)]
    for t in ["Tu fortuna neta: activos menos deudas. ¿Subió o bajó respecto a hace seis meses?",
              "Tus ingresos y tus gastos: cuánto entró, cuánto salió y cuánto convertiste en patrimonio.",
              "El desarrollo de tus inversiones: ¿hacen lo que esperabas? ¿Qué comisiones pagaste?",
              "Tus objetivos: ¿siguen siendo los mismos o la vida pide ajustarlos?",
              "Tu tasa de cumplimiento: del plan que te marcaste, ¿qué porcentaje hiciste de verdad?"]:
        out.append(Paragraph("<font face='Helvetica'>[   ]</font>  %s"%t,St("rv6",fontSize=9.8,leading=14,leftIndent=8,spaceAfter=3)))
    out.append(Paragraph("Lo que no se mide, no se gobierna. Lo que no se revisa, se deteriora en silencio.",St("rv6n",fontSize=9.5,leading=13,textColor=GREY,spaceBefore=3)))
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
            metas.append("Mi número de libertad es <b>%s</b>%s. Cada decisión me acerca o me aleja de él."%(_eur(cmp["numero_libertad"]),pl))
        if metas:
            inner.append(Paragraph("<font color='#B45309'><b>MIS OBJETIVOS IRRENUNCIABLES</b></font>",St("c1",fontSize=9.8,leading=14,spaceBefore=7)))
            for m in metas: inner.append(Paragraph("&#9656;  %s"%m,St("c2",fontSize=9.7,leading=14,leftIndent=8,spaceAfter=1)))
        inner.append(Paragraph("<font color='#B45309'><b>%s</b></font>"%("MIS TRES PASOS" if cmp.get("crisis") else "MIS REGLAS NO NEGOCIABLES"),St("c3",fontSize=9.8,leading=14,spaceBefore=7)))
        for r in (cmp.get("reglas") or []):
            inner.append(Paragraph("&#9656;  %s"%r,St("c4",fontSize=9.7,leading=14,leftIndent=8,spaceAfter=1)))
        inner.append(Paragraph(("Un paso cada vez. No se trata de hacerlo perfecto, sino de no rendirme: sostener estos tres, hoy, es suficiente." if cmp.get("crisis") else "No habrá excusas. Mi futuro dependerá de mis decisiones presentes. La disciplina de hoy es la libertad de mañana."),St("c5",fontSize=9.7,leading=14,spaceBefore=7)))
        out+=[Spacer(1,3*mm), _box(inner,"#23200F","#B45309",ancho=164*mm)]
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
    out.append(Paragraph("La buena noticia: nada de esto es una condena. Se mueve con las decisiones ordenadas que tienes en las páginas anteriores — no con suerte, con método. El primer paso es hoy.",
               St("cic",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=10,spaceBefore=4)))
    return out

def build(cli,resp,datos,out,depth="completo",baremo=None,sintesis=None,extras=None,arq_override=None):
    p,tr,salud=perfil(resp); fi=fi_metrics(datos); radar_png(p,"_radar.png")
    _cohorte=cohorte_txt(cli,datos)
    if baremo and baremo.get("pct") is not None:
        _pct_frase="mejor que el %d%% de %s" % (round(baremo["pct"]), _cohorte)
        _pct_nota=" \u00b7 muestra real: %d diagn\u00f3sticos" % baremo["n"]
    else:
        _pct_frase="tu percentil se est\u00e1 calibrando contra nuestra muestra de referencia, que crece con cada diagn\u00f3stico"
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
        Paragraph("Este libro no es un test ni una sentencia. "
                  "Es un espejo. Cada página nace de tus propias respuestas y las ordena para que veas, sin ruido, "
                  "dónde tu dinero te sostiene y dónde te pesa.",body),
        Paragraph("Lo hemos escrito como un libro, no como una ficha, porque tu vida financiera no se entiende con "
                  "un solo número. Se entiende como una historia con capítulos: tu salud emocional con el dinero, tu "
                  "libertad, tu resistencia a los golpes, tu deuda, tu manera de gastar y de protegerte. Cada capítulo "
                  "te dice qué mide, qué ha salido, qué significa para ti y cuál es tu siguiente paso.",body),
        Paragraph("No hay respuestas buenas o malas: hay puntos de partida. Léelo con calma, en orden. Al final "
                  "tendrás un mapa y un plan.",body),
        Spacer(1,4*mm),
        Paragraph("Una nota de cuidado: este libro es una herramienta de autoconocimiento, no asesoramiento "
                  "individualizado ni atención psicológica. Si el dinero te genera un malestar que te desborda, "
                  "apóyate también en un profesional de confianza.",small),
        PageBreak()]
    # resumen + radar
    S+=[Paragraph("El mapa completo",h_sec)]
    if extras and extras.get("crisis"):
        S+=[_box([Paragraph("<font color='#7A5A00'><b>&#9656;  Primero, lo primero</b></font>",St("cri1",fontSize=11,leading=15,fontName=FB)),
                  Paragraph("Tus respuestas dicen que ahora mismo el dinero te pesa de verdad —en el sueño, en la cabeza, en el día a día. Este informe no va a sumarte presión: antes de cualquier plan a años vista, su único objetivo es ayudarte a recuperar el aire y el control del mes. Un paso cada vez.",St("cri2",fontSize=10,leading=15,spaceBefore=2,textColor=INK))],
                 "#2A2010","#B45309",ancho=160*mm), Spacer(1,3*mm)]
    S+=[Table([[Paragraph(f"<font size=42 color='#1A1A17'><b>{100-salud:.0f}</b></font>"
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
                "#23200F","#B45309",ancho=160*mm), Spacer(1,4*mm)] if (extras and extras.get("accion_unica")) else []),
        Paragraph("Cuanto más llena y hacia el borde está cada capa, más sana. El anillo verde exterior es el "
                  "territorio saludable. Antes de entrar capítulo a capítulo, esta es tu silueta completa:",body),
        Image("_radar.png",width=122*mm,height=122*mm,hAlign="CENTER"),
        PageBreak()]
    if True:  # resumen (vistazo) en ambos tiers
        orden=sorted(CAPAS,key=lambda c:p[c]["score"])
        fort=orden[:3]; foco=orden[-3:][::-1]
        S+=[Paragraph("Tu lectura de un vistazo",h_sec),
            Paragraph("Antes del detalle capa por capa, esto es lo esencial: d\u00f3nde te apoyas y d\u00f3nde conviene "
                      "poner el foco. El resto del libro desarrolla cada punto.",body),
            Paragraph("Tus tres fortalezas",h_sub)]
        for c in fort:
            S.append(Paragraph(f"&#8226;  <b>{CAPAS[c]['nombre']}</b> ({100-p[c]['score']:.0f}/100). {OPORTUNIDAD[c]}",
                     St("ef",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
        S.append(Paragraph("Tus tres focos",h_sub))
        for c in foco:
            S.append(Paragraph(f"&#8226;  <b>{CAPAS[c]['nombre']}</b> ({100-p[c]['score']:.0f}/100). {RIESGO[c]}",
                     St("ec",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
        S+=[Spacer(1,3*mm),
            Paragraph(f"En una frase: tu salud psicofinanciera global es de <b>{100-salud:.0f}/100</b>"
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
                            St("rlx",fontSize=10,leading=14.5))],"#15243C","#0F766E",ancho=160*mm),
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
             Table([[Paragraph(f"<b>{100-pc['score']:.0f}</b>/100",body),
                     Chip(pc["banda"],BANDC[pc["bi"]],w=96,h=14)]],
                   colWidths=[60*mm,40*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
             Bar(pc["score"],w=160*mm/1),
             Spacer(1,3*mm),
             Paragraph("Qu\u00e9 significa para ti",h_sub),
             Paragraph(interpretar(pc["nombre"],pc["score"],pc["banda"],pc["bi"],pc["peor"],code),body)]
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
                                    Paragraph(f"<font color='{_sevcol(sc)}'><b>{100-sc:.0f}</b> \u00b7 {faceta_lectura(sc)}</font>",small)]],
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
    if extras: S+=seccion_extras(extras)
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
        vtxt=("%s"%round(100-val)) if val is not None else "\u2014"
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
        for _par in [x for x in str(sintesis).replace("\r","").split("\n") if x.strip()]:
            _e=_par.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            S.append(Paragraph(_e,body))
        S+=[PageBreak()]
    # plan
    S+=[Paragraph("Tu plan de acción",h_sec),
        Paragraph("Ordenado por impacto: si solo pudieras mover una palanca esta semana, empieza por la primera.",body)]
    rows=[[Paragraph("<b>#</b>",small),Paragraph("<b>Área de impacto</b>",small),Paragraph("<b>Tu siguiente acción</b>",small),Paragraph("<b>Severidad</b>",small)]]
    _AREA={"C1":"Bienestar financiero","C2":"Libertad financiera","C3":"Resistencia ante shocks","C4":"Control del gasto","C5":"Protección patrimonial","C6":"Gasto con sentido","C7":"Diversificación de ingresos","C8":"Antifragilidad","C9":"Gobierno del flujo","C10":"Salud de la deuda","C11":"Palanca de crecimiento"}
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
    S+=[pt,Spacer(1,5*mm),Paragraph("Tus números de libertad",h_sub),
        Table([["Número de libertad financiera (regla 25×)",f"{fi[0]:,.0f} €".replace(",",".")],
               ["Progreso hacia la libertad",f"{fi[1]} %"],
               ["Tasa de ahorro actual",f"{fi[2]} %"],
               ["Años estimados a la libertad","más de 100" if fi[3] is None else f"{fi[3]} años"]],
              colWidths=[105*mm,55*mm],style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
              ("FONTNAME",(1,0),(1,-1),FB),("TEXTCOLOR",(1,0),(1,-1),ACCDK),
              ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)])),
        PageBreak()]
    S+=cuadro_financiero(p,datos,fi)
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
        # Regla de contingencia (kill-switch sano)
        col6=datos.get("gasto_mensual",0)*6
        S+=[_box([Paragraph("<font color='#B45309'><b>Tu regla de contingencia</b></font><br/>"
                f"<font size=9.5>Todo plan necesita un freno de emergencia. El tuyo: si tu fondo l\u00edquido baja de "
                f"<b>{_eur(col6)}</b> (seis meses de gastos) o llega un imprevisto grande, <b>pausa las fases 2 y 3</b> "
                f"y vuelca todo el excedente a reconstruir ese col\u00f3n antes de seguir. Proteger la base va siempre "
                f"primero; crecer puede esperar unas semanas.</font>",St("kc",fontSize=10.5,leading=15))],
                "#2A2010","#B45309",ancho=160*mm)]
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
        S+=laboratorio_individual(p,datos,fi,salud,resp)
    # cierre
    S+=[Paragraph("Cómo seguir",h_sec),
        Paragraph("Este libro es una foto de hoy, no una condena. La mayoría de las cifras que más te incomodan "
                  "se mueven con uno o dos hábitos bien elegidos. Empieza por el primer punto de tu plan, dale un "
                  "mes, y vuelve a hacer el diagnóstico: verás el movimiento en negro sobre blanco.",body),
        Paragraph("Si compartes tu vida económica con otra persona, el informe de pareja cruza vuestros dos libros "
                  "y señala exactamente dónde divergís — el origen de la mayoría de los conflictos silenciosos por dinero.",body),
        Spacer(1,5*mm),
        Paragraph("Metodología y límites",h_sub),
        Paragraph("Instrumento de 10 capas con dimensiones psicométricas de polaridad consistente. Los percentiles "
                  "se calibran empíricamente frente a la cohorte real de respondentes; mientras la muestra de tu grupo crece, se indican como provisionales. Herramienta "
                  "de autoconocimiento; no sustituye asesoramiento profesional individualizado.",small)]
    if extras and depth!="esencial": S+=seccion_coste_inaccion(extras)
    if extras and depth!="esencial": S+=seccion_compromiso(extras)
    S+=seccion_adapta(p)
    # ANEXO: respuestas del cliente (transparencia; sin mostrar scores)
    NUM_MAP={"C2-1":"gasto_mensual","C2-2":"ingreso_mensual","C2-3":"ahorro_mensual","C2-4":"patrimonio","C2-5":"edad"}
    S+=[PageBreak(), Paragraph("Anexo \u2014 Tus respuestas",h_sec),
        Paragraph("Para total transparencia: estas son las preguntas que respondiste y lo que elegiste. "
                  "Tu diagn\u00f3stico se basa exactamente en esto, ni m\u00e1s ni menos.",body)]
    for capa in INST["capas"]:
        rows=[[Paragraph("<b>Pregunta</b>",small),Paragraph("<b>Tu respuesta</b>",small)]]
        bgs=[]; ri=1
        for it in capa["items"]:
            sc=None; na=False
            if it["tipo"]=="escala":
                idx=resp.get(it["id"])
                if idx is not None:
                    ans=it["opciones"][idx]["texto"]; sc=it["opciones"][idx]["score"]
                else: ans=""; na=True
            else:
                v=datos.get(NUM_MAP.get(it["id"],"")); na=(v is None); ans=("%s %s"%(v,it.get("unidad",""))).strip() if v is not None else ""
            ans_p=Paragraph("<font color='#B5B3A6'>N/A</font>",small) if na else Paragraph("<i>%s</i>"%_limpiar_txt(ans),small)
            rows.append([Paragraph("<font color='#33415C'>%s</font>"%_limpiar_txt(it["texto"]),small),ans_p])
            if ri%2==0:
                bgs.append(("BACKGROUND",(0,ri),(-1,ri),colors.HexColor("#15243C")))
            ri+=1
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
    return _INST_V2

def build_book_v2(resp, datos, cli, outpath, perfil_in=None, depth="completo", baremo=None, sintesis=None, extras=None, arq_override=None):
    """Genera el libro usando el instrumento v2 (11 capas adaptativas) + secciones brecha/palancas."""
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
