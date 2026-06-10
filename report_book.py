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
    cv.drawCentredString(A4[0]/2,12*mm,f"Tu Libro Financiero · ITAP — Méndez Consultoría   ·   {doc.page}")
    cv.setStrokeColor(LINE); cv.setLineWidth(0.5); cv.line(22*mm,16*mm,A4[0]-22*mm,16*mm); cv.restoreState()

def build(cli,resp,datos,out):
    p,tr,salud=perfil(resp); fi=fi_metrics(datos); radar_png(p,"_radar.png")
    bi,bl=banda(CAPAS["C1"],salud); S=[]
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
        Spacer(1,2*mm),
        Paragraph("Cuanto más cerca del centro está cada capa en este mapa, más sana. La zona verde central es el "
                  "territorio saludable. Antes de entrar capítulo a capítulo, esta es tu silueta completa:",body),
        Image("_radar.png",width=122*mm,height=122*mm,hAlign="CENTER"),
        PageBreak()]
    # capítulos por capa
    for n,code in enumerate(CAPAS,1):
        pc=p[code]
        bloque=[Paragraph(f"CAPÍTULO {n}",cap_kicker),
                Paragraph(pc["nombre"],h_book),
                Table([[""]],colWidths=[40*mm],style=[("LINEBELOW",(0,0),(-1,-1),1.5,ACC)]),
                Spacer(1,3*mm),
                Paragraph("Qué mide",h_sub),
                Paragraph(f"Este capítulo mide {QMIDE[code]}",body),
                Paragraph("Tu resultado",h_sub),
                Table([[Paragraph(f"<b>{pc['score']:.0f}</b>/100  ·  percentil {pc['pct']:.0f}",body),
                        Chip(pc["banda"],BANDC[pc["bi"]],w=96,h=14)]],
                      colWidths=[60*mm,40*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
                Bar(pc["score"],w=160*mm/1),
                Spacer(1,3*mm),
                Paragraph("Qué significa para ti",h_sub),
                Paragraph(interpretar(pc["nombre"],pc["score"],pc["banda"],pc["bi"],pc["peor"]),body),
                Paragraph("Tu siguiente paso",h_sub),
                Paragraph(f"&#8226;  {PASO[code]}",St("ps",fontSize=10,leading=14,textColor=INK,leftIndent=4,backColor=LIGHT,
                          borderPadding=6,spaceBefore=2))]
        S.append(KeepTogether(bloque)); S.append(PageBreak())
    # transversales
    S+=[Paragraph("Lo que cruza todas las capas",h_sec),
        Paragraph("Hay tres corrientes que no viven en un solo capítulo: recorren todo tu perfil. Verlas juntas "
                  "explica patrones que ninguna capa aislada revela.",body)]
    desc={"PSIQUE":("Carga psicológica","el peso emocional del dinero: negación, identidad, rumiación."),
          "LIQUIDEZ":("Liquidez","la holgura de colchón disponible en el conjunto de tu vida."),
          "VINCULO":("Vínculo","la tensión y la transparencia con tu pareja o tu familia.")}
    for t in ("PSIQUE","LIQUIDEZ","VINCULO"):
        val=tr[t]; tt,dd=desc[t]
        S+=[Paragraph(tt,h_sub),
            Table([[Paragraph(f"<b>{val if val is not None else '—'}</b>/100",body),Bar(val or 0,w=120*mm)]],
                  colWidths=[28*mm,124*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
            Paragraph(f"Mide {dd}",small)]
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
    doc=SimpleDocTemplate(out,pagesize=A4,topMargin=20*mm,bottomMargin=20*mm,leftMargin=22*mm,rightMargin=22*mm,
                          title="Tu Libro Financiero — ITAP")
    doc.build(S,onFirstPage=deco,onLaterPages=deco); print("PDF OK ->",out)

def build_book(resp, datos, cli, outpath):
    """API entrypoint: genera el libro PDF en outpath."""
    build(cli, resp, datos, outpath)
    return outpath
