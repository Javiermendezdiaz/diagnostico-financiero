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

INST=json.load(open("itap_instrumento.json",encoding="utf-8"))
CAPAS={c["code"]:c for c in INST["capas"]}
TRANS={"PSIQUE","LIQUIDEZ","VINCULO"}
INK=colors.HexColor("#1F2937"); ACC=colors.HexColor("#0284C7"); ACCDK=colors.HexColor("#075985")
GREY=colors.HexColor("#6B7280"); LIGHT=colors.HexColor("#EAF4FB"); LINE=colors.HexColor("#D5DBE3")
PAPER=colors.HexColor("#FBFCFD"); BANDC=["#15803D","#CA8A04","#EA580C","#B91C1C"]

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
    fi=d["gasto_mensual"]*12*25; pct=round(100*d["patrimonio"]/fi,1)
    tasa=round(100*d["ahorro_mensual"]/d["ingreso_mensual"],1)
    r,pv,m,n=0.05/12,d["patrimonio"],d["ahorro_mensual"],0
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
 "C10":"el peso y la salud de tu deuda, y si resistiría una caída de ingresos."}
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
 "C10":"ordena tus deudas por tipo de interés y ataca primero la más cara."}

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
 "C10":"La deuda mal gestionada crece en silencio con cada subida de tipos. Lo que hoy pagas con holgura, mañana puede asfixiarte."}
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
 "C10":"Una deuda sana libera flujo y tranquilidad. Pagar lo caro primero es la inversión con mejor rentabilidad garantizada que existe."}
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
 "C10":[PASO["C10"],"Renegocia o refinancia tu deuda más cara este mes.","Ponle fecha a tu día sin deuda mala y calcula cuánto pagar al mes para llegar."]}

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
 "C10":"La deuda barata es una herramienta; la cara, una trampa."}

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
 "C10":"\u00bfQu\u00e9 deuda llevas arrastrando que, en el fondo, sabes que deber\u00edas atacar ya?"}

def faceta_lectura(score):
    if score<30: return "es una base firme."
    if score<51: return "va bien, con recorrido de mejora."
    if score<76: return "empieza a pesar; conviene atenderla."
    return "es un punto crítico de esta área."
def segundo_parrafo(bi):
    return {0:"Mantén lo que funciona: revisa esta área de vez en cuando para que no se deteriore sin avisar. La fortaleza descuidada se oxida.",
            1:"Tienes una base buena. Un pequeño ajuste sostenido aquí te lleva al nivel más alto sin grandes sacrificios: es de las mejoras más rentables que puedes hacer.",
            2:"No hace falta una revolución, sino constancia: un hábito bien elegido, repetido tres meses, mueve esta cifra de forma visible. Empieza pequeño, pero empieza.",
            3:"Esta es de las áreas a las que dar prioridad. El coste de no actuar crece con el tiempo; el de actuar, se paga una vez. Conviértelo en tu primer frente."}[bi]


def interpretar(nombre,s,bl,bi,peor):
    nl=nombre.lower()
    if bi==0: return (f"En {nl} estás en terreno sólido (score {s:.0f}, «{bl}»). Es una de tus fortalezas. "
                      f"No la des por garantizada: lo que hoy va bien también se cuida.")
    if bi==1: return (f"En {nl} vas bien, con margen (score {s:.0f}, «{bl}»). El punto que más pesa ahora es "
                      f"«{peor}»; ahí tienes la mejora más fácil y rentable.")
    if bi==2: return (f"{nombre} muestra sobrecarga (score {s:.0f}, «{bl}»), sobre todo en «{peor}». No es "
                      f"catastrófico, pero si no lo atiendes va erosionando todo lo demás poco a poco.")
    return (f"{nombre} está en zona crítica (score {s:.0f}, «{bl}»), en especial en «{peor}». Es uno de los "
            f"primeros frentes donde intervenir: el retorno de actuar aquí es inmediato.")

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
    labels=[c for c in CAPAS]; vals=[p[c]["score"] for c in CAPAS]
    N=len(labels); ang=np.linspace(0,2*np.pi,N,endpoint=False).tolist(); ang+=ang[:1]; v=vals+vals[:1]
    fig,ax=plt.subplots(figsize=(5.6,5.6),subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1); ax.set_ylim(0,100)
    ax.set_yticks([25,50,75]); ax.set_yticklabels(["25","50","75"],color="#9CA3AF",size=8)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels,size=10,color="#1F2937",weight="bold")
    ax.fill_between(np.linspace(0,2*np.pi,200),0,30,color="#15803D",alpha=0.07)
    ax.plot(ang,v,color="#0284C7",linewidth=2.3); ax.fill(ang,v,color="#0284C7",alpha=0.20)
    ax.spines["polar"].set_color("#D5DBE3"); ax.grid(color="#E5E7EB")
    plt.tight_layout(); fig.savefig(path,dpi=150,transparent=True); plt.close(fig)

class Chip(Flowable):
    def __init__(s,t,c,w=92,h=14): s.t=t; s.c=colors.HexColor(c); s.w=w; s.h=h; Flowable.__init__(s)
    def wrap(s,*a): return (s.w,s.h)
    def draw(s):
        c=s.canv; c.setFillColor(s.c); c.roundRect(0,0,s.w,s.h,3,fill=1,stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold",7.5); c.drawCentredString(s.w/2,s.h/2-2.6,s.t)
class Bar(Flowable):
    def __init__(s,val,w=160,h=9): s.v=val; s.w=w; s.h=h; Flowable.__init__(s)
    def wrap(s,*a): return (s.w*mm if s.w<10 else s.w,s.h)
    def draw(s):
        c=s.canv; W=s.w; c.setFillColor(colors.HexColor("#EEF2F6")); c.roundRect(0,0,W,s.h,2,fill=1,stroke=0)
        col=BANDC[3] if s.v>=76 else BANDC[2] if s.v>=51 else BANDC[1] if s.v>=26 else BANDC[0]
        c.setFillColor(colors.HexColor(col)); c.roundRect(0,0,max(3,W*s.v/100),s.h,2,fill=1,stroke=0)

def St(n,**k): k.setdefault("fontName","Helvetica"); k.setdefault("textColor",INK); return ParagraphStyle(n,**k)
h_book=St("hb",fontSize=15,leading=19,textColor=ACCDK,fontName="Helvetica-Bold",spaceAfter=2)
h_sec=St("hs",fontSize=17,leading=21,textColor=ACCDK,fontName="Helvetica-Bold",spaceAfter=8)
h_sub=St("hu",fontSize=10.5,leading=13,textColor=ACC,fontName="Helvetica-Bold",spaceBefore=7,spaceAfter=3)
body=St("bd",fontSize=10,leading=15,spaceAfter=7,alignment=TA_JUSTIFY)
small=St("sm",fontSize=8,leading=11,textColor=GREY)
cap_kicker=St("ck",fontSize=8.5,leading=11,textColor=GREY,fontName="Helvetica-Bold")

def deco(cv,doc):
    cv.saveState(); cv.setFillColor(GREY); cv.setFont("Helvetica",7)
    cv.drawCentredString(A4[0]/2,12*mm,f"Tu Libro Financiero · Adapta Family Office   ·   {doc.page}")
    cv.setStrokeColor(LINE); cv.setLineWidth(0.5); cv.line(22*mm,16*mm,A4[0]-22*mm,16*mm); cv.restoreState()

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
 "C10":("Planificaci\u00f3n y reestructuraci\u00f3n de hipoteca","Renegociaci\u00f3n, subrogaci\u00f3n y las mejores condiciones que tu perfil permite \u2014 para que la deuda deje de pesar.","https://www.adaptafamilyoffice.com/casos/planificacion-hipoteca")}

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
        out.append(Paragraph(f"<a href='{url}'><font color='#075985'>Ver c\u00f3mo lo trabajamos &#8594;</font></a>",St("ad3",fontSize=9.5,leading=13,leftIndent=8,spaceAfter=8)))
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
    labels=["Ingreso","Gastos","Ahorro","Sin asignar"]
    # ingreso
    ax.bar(0,ing,color="#0F766E",width=0.6)
    ax.bar(1,gas,bottom=ing-gas,color="#C2710C",width=0.6)
    ax.bar(2,aho,bottom=ing-gas-aho,color="#1D6F42",width=0.6)
    libre=ing-gas-aho
    ax.bar(3,abs(libre),bottom=min(libre,0),color="#94A3B8" if libre>=0 else "#B91C1C",width=0.6)
    for i,(lab,val) in enumerate(zip(labels,[ing,gas,aho,abs(libre)])):
        ax.text(i,val if i==0 else 0,"",ha="center")
    ax.set_xticks(range(4)); ax.set_xticklabels(labels,size=9,color="#374151")
    ax.annotate(_eur(ing),(0,ing),ha="center",va="bottom",size=8.5,color="#0F766E",weight="bold")
    ax.annotate(_eur(gas),(1,ing-gas/2),ha="center",va="center",size=8.5,color="white",weight="bold")
    ax.annotate(_eur(aho),(2,ing-gas-aho/2),ha="center",va="center",size=8.5,color="white",weight="bold")
    ax.annotate(_eur(abs(libre)),(3,abs(libre)),ha="center",va="bottom",size=8.5,
                color="#475569" if libre>=0 else "#B91C1C",weight="bold")
    ax.set_ylim(0,ing*1.15); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#D5DBE3"); ax.tick_params(axis="y",labelsize=7,colors="#9CA3AF")
    ax.set_title("De cada euro que entra, a dónde va",size=10,color="#1F2937",weight="bold",pad=8)
    plt.tight_layout(); fig.savefig(path,dpi=150,transparent=True); plt.close(fig)
    return libre

def proyeccion_chart(datos, path, r=0.05):
    edad=int(datos.get("edad",40)); meta_edad=65
    anos=max(meta_edad-edad,1)
    pat=datos.get("patrimonio",0); aho=datos.get("ahorro_mensual",0)*12
    import matplotlib.pyplot as plt
    xs=list(range(edad,meta_edad+1))
    def proy(extra):
        v=pat; out=[v]
        for _ in range(anos):
            v=v*(1+r)+aho+extra; out.append(v)
        return out
    base=proy(0); mejora=proy(0.05*datos.get("ingreso_mensual",0)*12)  # +5pp del ingreso anual
    fig,ax=plt.subplots(figsize=(6.4,3.0))
    ax.plot(xs,base,color="#0284C7",linewidth=2.2,label="Si sigues igual")
    ax.plot(xs,mejora,color="#1D6F42",linewidth=2.2,linestyle="--",label="Si ahorras 5 puntos más")
    ax.fill_between(xs,base,mejora,color="#1D6F42",alpha=0.08)
    ax.scatter([meta_edad],[base[-1]],color="#0284C7",zorder=5)
    ax.scatter([meta_edad],[mejora[-1]],color="#1D6F42",zorder=5)
    ax.annotate(_eur(base[-1]),(meta_edad,base[-1]),ha="right",va="top",size=8,color="#0284C7",weight="bold")
    ax.annotate(_eur(mejora[-1]),(meta_edad,mejora[-1]),ha="right",va="bottom",size=8,color="#1D6F42",weight="bold")
    ax.set_xlabel("Edad",size=8,color="#6B7280"); ax.tick_params(labelsize=7,colors="#9CA3AF")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.spines["left"].set_color("#D5DBE3")
    ax.spines["bottom"].set_color("#D5DBE3")
    ax.legend(fontsize=8,frameon=False,loc="upper left")
    ax.set_title("Tu patrimonio proyectado a los 65 (estimación al 5%/año)",size=10,color="#1F2937",weight="bold",pad=8)
    plt.tight_layout(); fig.savefig(path,dpi=150,transparent=True); plt.close(fig)
    return base[-1],mejora[-1],meta_edad

def tapon_coste(datos, real=0.025):
    """Coste de oportunidad estimado de la liquidez parada por encima de un colchon de 6 meses."""
    gas=datos.get("gasto_mensual",0); pat=datos.get("patrimonio",0)
    colchon=gas*6
    exceso=max(pat-colchon,0)
    if exceso < 5000: return None
    coste=exceso*real
    return exceso, coste

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
        style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.5,colors.HexColor("#C7CFDA")),
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
    D=[Paragraph("<b><font color='#B91C1C'>Debilidades</font></b>",small)]+[Paragraph("&#8226; "+n,small) for _,n in debi]
    O=[Paragraph("<b><font color='#0284C7'>Oportunidades</font></b>",small)]+[Paragraph("&#8226; "+t,small) for t in oport]
    A=[Paragraph("<b><font color='#B45309'>Amenazas</font></b>",small)]+[Paragraph("&#8226; "+t,small) for t in amen]
    out.append(Table([[F,O],[D,A]],colWidths=[80*mm,80*mm],
        style=TableStyle([("BACKGROUND",(0,0),(0,0),colors.HexColor("#EEF7F0")),
          ("BACKGROUND",(1,0),(1,0),colors.HexColor("#EAF4FB")),
          ("BACKGROUND",(0,1),(0,1),colors.HexColor("#FBECEC")),
          ("BACKGROUND",(1,1),(1,1),colors.HexColor("#FBF3E8")),
          ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
          ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
          ("LINEBELOW",(0,0),(-1,0),3,colors.white),("LINEAFTER",(0,0),(0,-1),3,colors.white)])))
    out.append(PageBreak())
    cashflow_waterfall(datos,"_cash.png")
    out+=[KeepTogether([Paragraph("Tu flujo de caja",h_sub),
          Image("_cash.png",width=160*mm,height=75*mm,hAlign="CENTER")])]
    tap=tapon_coste(datos)
    if tap:
        exceso,coste=tap
        vnh=valor_hora(datos)
        horas=(coste/12)/vnh if vnh>0 else 0
        out.append(_box([Paragraph(f"<font color='#B45309'><b>La auditoría del tapón</b></font><br/>"
            f"<font size=9.5>Tienes unos <b>{_eur(exceso)}</b> de liquidez por encima de un colchón sano de 6 meses. "
            f"Parada y sin invertir, esa cifra deja de ganar alrededor de <b>{_eur(coste)} al año</b> solo en coste de "
            f"oportunidad frente a la inflación. No es prudencia: es un peaje invisible. Mover una parte a algo que "
            f"al menos preserve su valor es de las decisiones más rentables y menos arriesgadas que tienes sobre la mesa.</font>",
            St("tp",fontSize=10.5,leading=15))],"#FBF3E8","#B45309",ancho=160*mm))
    out.append(PageBreak())
    f65,m65,_=proyeccion_chart(datos,"_proy.png")
    out+=[KeepTogether([Paragraph("Hacia dónde vas",h_sub),
          Image("_proy.png",width=160*mm,height=75*mm,hAlign="CENTER")]),
          Paragraph(f"Si mantienes tu ritmo actual, a los 65 rondarías los <b>{_eur(f65)}</b>. Subiendo tu ahorro "
                    f"cinco puntos, esa cifra sube a <b>{_eur(m65)}</b>: la diferencia entre ambas líneas es, literalmente, "
                    f"el precio de no decidir. (Estimación a un 5% anual; orientativa, no una promesa de rentabilidad.)",body),
          PageBreak()]
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
                    ("TOPPADDING",(0,0),(-1,0),3)]))],"#F4F7FA","#0284C7",ancho=160*mm),
          PageBreak()]
    return out

def build(cli,resp,datos,out,depth="completo"):
    p,tr,salud=perfil(resp); fi=fi_metrics(datos); radar_png(p,"_radar.png")
    bi,bl=banda(CAPAS["C1"],salud); S=[]
    coh=coherencia(salud,fi,datos)
    arq_code,_,_=arquetipo(resp)
    # cover
    S+=[Spacer(1,34*mm),
        Paragraph("TU LIBRO FINANCIERO",St("cv0",fontSize=12,textColor=GREY,fontName="Helvetica-Bold")),
        Spacer(1,3*mm),
        Paragraph("Diagnóstico<br/>Patrimonial",St("cv1",fontSize=40,leading=44,textColor=INK,fontName="Helvetica-Bold")),
        Spacer(1,5*mm),
        Table([[""]],colWidths=[55*mm],style=[("LINEBELOW",(0,0),(-1,-1),2.5,ACC)]),
        Spacer(1,7*mm),
        Paragraph("Una lectura honesta de tu relación con el dinero, capa por capa.",St("cv2",fontSize=12,textColor=ACCDK)),
        Spacer(1,40*mm),
        Paragraph(f"Escrito para  <b>{cli['nombre']}</b>",St("cvn",fontSize=12)),
        Paragraph(cli["email"],small), Paragraph(cli["fecha"],small),
        Spacer(1,3*mm), Paragraph("Edición Avanzada · Tier 2",St("cvt",fontSize=9.5,textColor=ACC,fontName="Helvetica-Bold")),
        Spacer(1,16*mm),
        Paragraph(f"DOCUMENTO CONFIDENCIAL · REF {report_id(cli['nombre'],cli['fecha'])} · USO PRIVADO",
                  St("cvr",fontSize=7.5,textColor=GREY,fontName="Helvetica")),
        PageBreak()]
    # carta de apertura
    S+=[Paragraph("Antes de empezar",h_sec),
        Paragraph(f"{cli['nombre'].split()[0] if cli['nombre'] else 'Hola'}, este libro no es un test ni una sentencia. "
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
    S+=[Paragraph("El mapa completo",h_sec),
        Table([[Paragraph(f"<font size=42 color='#075985'><b>{salud:.0f}</b></font>"
                          f"<font size=13 color='#6B7280'>/100</font>",body),
                Paragraph(f"<b>{bl}</b><br/><font size=8 color='#6B7280'>Salud psicofinanciera global · "
                          f"mejor que el {pctil(salud):.0f}% de la cohorte de referencia</font>",body)]],
              colWidths=[42*mm,118*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
        *([Spacer(1,4*mm),Paragraph(coh[0],h_sub),Paragraph(coh[1],St("coh",fontSize=10,leading=14,backColor=LIGHT,borderPadding=10,textColor=INK,spaceBefore=4,spaceAfter=4))] if coh else []),
        *([Spacer(1,4*mm),
           Paragraph(f"Tu arquetipo del dinero: {ARQ_META[arq_code]['nombre']}",h_sub),
           Paragraph(f"<i>{ARQ_META[arq_code]['lema']}</i> {ARQ_META[arq_code]['desc']}",body),
           Paragraph(f"<font color='#1D6F42'><b>Lo que te aporta:</b></font> {ARQ_META[arq_code]['luz']}  "
                     f"<font color='#B91C1C'><b>Tu punto ciego:</b></font> {ARQ_META[arq_code]['sombra']}",
                     St("aq",fontSize=9.2,leading=13,textColor=GREY,spaceAfter=4))] if arq_code else []),
        Spacer(1,2*mm),
        Paragraph("Cuanto más cerca del centro está cada capa en este mapa, más sana. La zona verde central es el "
                  "territorio saludable. Antes de entrar capítulo a capítulo, esta es tu silueta completa:",body),
        Image("_radar.png",width=122*mm,height=122*mm,hAlign="CENTER"),
        PageBreak()]
    if depth!="esencial":
        orden=sorted(CAPAS,key=lambda c:p[c]["score"])
        fort=orden[:3]; foco=orden[-3:][::-1]
        S+=[Paragraph("Tu lectura de un vistazo",h_sec),
            Paragraph("Antes del detalle capa por capa, esto es lo esencial: d\u00f3nde te apoyas y d\u00f3nde conviene "
                      "poner el foco. El resto del libro desarrolla cada punto.",body),
            Paragraph("Tus tres fortalezas",h_sub)]
        for c in fort:
            S.append(Paragraph(f"&#8226;  <b>{CAPAS[c]['nombre']}</b> ({p[c]['score']:.0f}/100). {OPORTUNIDAD[c]}",
                     St("ef",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
        S.append(Paragraph("Tus tres focos",h_sub))
        for c in foco:
            S.append(Paragraph(f"&#8226;  <b>{CAPAS[c]['nombre']}</b> ({p[c]['score']:.0f}/100). {RIESGO[c]}",
                     St("ec",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
        S+=[Spacer(1,3*mm),
            Paragraph(f"En una frase: tu salud psicofinanciera global es de <b>{salud:.0f}/100</b> ("
                      f"mejor que el {pctil(salud):.0f}% de la cohorte). No es una condena ni un trofeo: es tu punto "
                      "de partida, y se mueve.",body),
            PageBreak()]
    # capítulos por capa
    for n,code in enumerate(CAPAS,1):
        pc=p[code]
        cab=[Paragraph(f"CAP\u00cdTULO {n}",cap_kicker),
             Paragraph(pc["nombre"],h_book),
             Table([[""]],colWidths=[40*mm],style=[("LINEBELOW",(0,0),(-1,-1),1.5,ACC)]),
             Spacer(1,3*mm),
             Paragraph("Qu\u00e9 mide",h_sub),
             Paragraph(f"Este cap\u00edtulo mide {QMIDE[code]}",body),
             Paragraph("Tu resultado",h_sub),
             Table([[Paragraph(f"<b>{pc['score']:.0f}</b>/100  \u00b7  percentil {pc['pct']:.0f}",body),
                     Chip(pc["banda"],BANDC[pc["bi"]],w=96,h=14)]],
                   colWidths=[60*mm,40*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
             Bar(pc["score"],w=160*mm/1),
             Spacer(1,3*mm),
             Paragraph("Qu\u00e9 significa para ti",h_sub),
             Paragraph(interpretar(pc["nombre"],pc["score"],pc["banda"],pc["bi"],pc["peor"]),body)]
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
                                    Paragraph(f"<font color='#6B7280'>{sc:.0f} \u00b7 {faceta_lectura(sc)}</font>",small)]],
                                 colWidths=[66*mm,48*mm,42*mm],
                                 style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,-1),0),
                                        ("LEFTPADDING",(1,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
            cab+=[Spacer(1,2*mm),
                  Paragraph(segundo_parrafo(pc["bi"]),body),
                  Paragraph("El riesgo si no act\u00faas",h_sub),
                  Paragraph(RIESGO[code],body),
                  Paragraph("La oportunidad",h_sub),
                  Paragraph(OPORTUNIDAD[code],body),
                  Paragraph("Tu plan de acci\u00f3n",h_sub),
                  Paragraph("Tres pasos, en orden. Empieza por el primero y no pases al siguiente hasta tenerlo en marcha:",small)]
            for a in ACCIONES[code]:
                cab.append(Paragraph(f"&#8226;  {a}",St("pa",fontSize=10,leading=14,textColor=INK,leftIndent=6,spaceAfter=4)))
            cab+=[Spacer(1,2*mm),
                  Paragraph(f"\u201c{PRINCIPIO[code]}\u201d",St("pr",fontSize=10.5,leading=14,textColor=ACCDK,
                            fontName="Helvetica-Oblique",backColor=LIGHT,borderPadding=8,spaceBefore=2)),
                  Spacer(1,2*mm),
                  Paragraph("Para reflexionar",h_sub),
                  Paragraph(REFLEX[code],St("rf",fontSize=10,leading=14,textColor=INK,fontName="Helvetica-Oblique"))]
            S.extend(cab); S.append(PageBreak())
    # transversales
    S+=[Paragraph("Lo que cruza todas las capas",h_sec),
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
        vtxt=("%s"%val) if val is not None else "\u2014"
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
    # plan
    S+=[Paragraph("Tu plan de acción",h_sec),
        Paragraph("Ordenado por impacto: si solo pudieras mover una palanca esta semana, empieza por la primera.",body)]
    rows=[[Paragraph("<b>#</b>",small),Paragraph("<b>Foco</b>",small),Paragraph("<b>Severidad</b>",small)]]
    for i,(val,code,d) in enumerate(plan(p),1):
        rows.append([Paragraph(str(i),small),Paragraph(f"[{code}] {d}",small),
                     Chip(f"{val:.0f}/100","#B91C1C" if val>=75 else "#EA580C",w=46,h=13)])
    pt=Table(rows,colWidths=[10*mm,120*mm,30*mm]); pt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),LIGHT),("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    S+=[pt,Spacer(1,5*mm),Paragraph("Tus números de libertad",h_sub),
        Table([["Número de libertad financiera (regla 25×)",f"{fi[0]:,.0f} €".replace(",",".")],
               ["Progreso hacia la libertad",f"{fi[1]} %"],
               ["Tasa de ahorro actual",f"{fi[2]} %"],
               ["Años estimados a la libertad","más de 100" if fi[3] is None else f"{fi[3]} años"]],
              colWidths=[105*mm,55*mm],style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
              ("FONTNAME",(1,0),(1,-1),"Helvetica-Bold"),("TEXTCOLOR",(1,0),(1,-1),ACCDK),
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
                "#FBF3E8","#B45309",ancho=160*mm)]
        S+=[PageBreak(),
            Paragraph("Conceptos clave",h_sec),
            Paragraph("El vocabulario que de verdad necesitas para gobernar tu dinero, sin jerga:",body)]
        glos=[("N\u00famero de libertad financiera","El patrimonio que, invertido, cubre tus gastos para siempre. Regla pr\u00e1ctica: gasto anual \u00d7 25."),
              ("Tasa de ahorro","Qu\u00e9 porcentaje de lo que ingresas consigues guardar. Es la palanca m\u00e1s potente hacia la libertad."),
              ("Fondo de emergencia","Dinero l\u00edquido, intocable, para imprevistos. Tu primer escudo: idealmente 3-6 meses de gastos."),
              ("Lifestyle creep (deriva)","La tendencia a gastar m\u00e1s cuando ingresas m\u00e1s, sin notarlo. El enemigo silencioso del ahorro."),
              ("Antifragilidad","La capacidad no solo de resistir una crisis, sino de salir reforzado de ella."),
              ("Concentraci\u00f3n de ingresos","Cu\u00e1nto dependes de una sola fuente. A m\u00e1s concentraci\u00f3n, m\u00e1s riesgo oculto."),
              ("Blindaje patrimonial","El conjunto de medidas legales (testamento, seguros, poderes) que protegen lo tuyo y a los tuyos.")]
        for t,d2 in glos:
            S.append(Paragraph(f"<b>{t}.</b> {d2}",St("gl",fontSize=10,leading=14,spaceAfter=5)))
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
                  "son provisionales y se afinan con datos reales conforme crece la base de respondentes. Herramienta "
                  "de autoconocimiento; no sustituye asesoramiento profesional individualizado.",small)]
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
            sc=None
            if it["tipo"]=="escala":
                idx=resp.get(it["id"])
                if idx is not None:
                    ans=it["opciones"][idx]["texto"]; sc=it["opciones"][idx]["score"]
                else: ans="\u2014"
            else:
                v=datos.get(NUM_MAP.get(it["id"],""),"\u2014"); ans=("%s %s"%(v,it.get("unidad",""))).strip()
            rows.append([Paragraph(it["texto"],small),Paragraph(ans,small)])
            if sc is not None:
                col="#E7F6EC" if sc<=25 else ("#FEF9E7" if sc<=50 else ("#FDEBD0" if sc<=75 else "#FAE3E3"))
                bgs.append(("BACKGROUND",(1,ri),(1,ri),colors.HexColor(col)))
            ri+=1
        t=Table(rows,colWidths=[104*mm,52*mm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),LIGHT),("LINEBELOW",(0,0),(-1,-1),0.3,LINE),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",(0,0),(-1,-1),6),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]+bgs))
        S+=[Paragraph("%s \u00b7 %s"%(capa["code"],capa["nombre"]),h_sub), t]
    doc=SimpleDocTemplate(out,pagesize=A4,topMargin=20*mm,bottomMargin=20*mm,leftMargin=22*mm,rightMargin=22*mm,
                          title="Tu Libro Financiero — ITAP")
    doc.build(S,onFirstPage=deco,onLaterPages=deco); print("PDF OK ->",out)

def build_book(resp, datos, cli, outpath, depth="completo"):
    """API entrypoint: genera el libro PDF en outpath."""
    build(cli, resp, datos, outpath, depth)
    return outpath
