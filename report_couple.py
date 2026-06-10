# -*- coding: utf-8 -*-
"""ITAP — Libro de Pareja (Tier 3). Cruza dos perfiles y mapea el conflicto financiero."""
import json, statistics
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, Flowable, KeepTogether)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
import report_book as rb

INST=rb.INST; CAPAS=rb.CAPAS
INK=colors.HexColor("#1F2937"); A_COL="#0284C7"; B_COL="#9333EA"
ACCDK=colors.HexColor("#075985"); GREY=colors.HexColor("#6B7280")
LIGHT=colors.HexColor("#EAF4FB"); LINE=colors.HexColor("#D5DBE3"); BANDC=rb.BANDC

def St(n,**k): k.setdefault("fontName","Helvetica"); k.setdefault("textColor",INK); return ParagraphStyle(n,**k)
h_sec=St("hs",fontSize=17,leading=21,textColor=ACCDK,fontName="Helvetica-Bold",spaceAfter=8)
h_sub=St("hu",fontSize=10.5,leading=13,textColor=colors.HexColor("#0284C7"),fontName="Helvetica-Bold",spaceBefore=7,spaceAfter=3)
body=St("bd",fontSize=10,leading=15,spaceAfter=7,alignment=TA_JUSTIFY)
small=St("sm",fontSize=8,leading=11,textColor=GREY)
kick=St("ck",fontSize=8.5,leading=11,textColor=GREY,fontName="Helvetica-Bold")

def cell(t,w,fill=None,bold=False,color=INK,align=0,size=9):
    return rb.Table  # placeholder not used

class Bar2(Flowable):
    """Dos barras superpuestas: A y B."""
    def __init__(s,a,b,w=120): s.a=a; s.b=b; s.w=w; s.h=20; Flowable.__init__(s)
    def wrap(s,*x): return (s.w,s.h)
    def draw(s):
        c=s.canv; W=s.w
        for i,(val,col) in enumerate([(s.a,A_COL),(s.b,B_COL)]):
            y=s.h-9-(i*9)
            c.setFillColor(colors.HexColor("#EEF2F6")); c.roundRect(0,y,W,7,2,fill=1,stroke=0)
            c.setFillColor(colors.HexColor(col)); c.roundRect(0,y,max(3,W*val/100),7,2,fill=1,stroke=0)

def dual_radar(pA,pB,path):
    labels=[c for c in CAPAS]
    N=len(labels); ang=np.linspace(0,2*np.pi,N,endpoint=False).tolist(); ang+=ang[:1]
    fig,ax=plt.subplots(figsize=(5.8,5.8),subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1); ax.set_ylim(0,100)
    ax.set_yticks([25,50,75]); ax.set_yticklabels(["25","50","75"],color="#9CA3AF",size=8)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels,size=10,color="#1F2937",weight="bold")
    for prof,col,lab in [(pA,A_COL,"Persona A"),(pB,B_COL,"Persona B")]:
        v=[prof[c]["score"] for c in CAPAS]; v+=v[:1]
        ax.plot(ang,v,color=col,linewidth=2.2,label=lab); ax.fill(ang,v,color=col,alpha=0.14)
    ax.spines["polar"].set_color("#D5DBE3"); ax.grid(color="#E5E7EB")
    ax.legend(loc="upper right",bbox_to_anchor=(1.18,1.12),fontsize=9,frameon=False)
    plt.tight_layout(); fig.savefig(path,dpi=150,transparent=True); plt.close(fig)

def divergencias_item(rA,rB):
    out=[]
    for capa in INST["capas"]:
        for it in capa["items"]:
            if it["tipo"]!="escala": continue
            a,b=rA.get(it["id"]),rB.get(it["id"])
            if a is None or b is None: continue
            sa,sb=it["opciones"][a]["score"],it["opciones"][b]["score"]
            vinc="VINCULO" in it.get("dimensiones","")
            if abs(sa-sb)>=66 or (vinc and abs(sa-sb)>=33):
                out.append({"capa":capa["code"],"texto":it["texto"],
                    "A":it["opciones"][a]["texto"],"B":it["opciones"][b]["texto"],
                    "gap":abs(sa-sb),"vinc":vinc})
    out.sort(key=lambda d:(-d["vinc"],-d["gap"])); return out

def tbl(rows,widths,head=True):
    t=Table(rows,colWidths=widths)
    sty=[("LINEBELOW",(0,0),(-1,-1),0.4,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
         ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
         ("LEFTPADDING",(0,0),(-1,-1),8)]
    if head: sty+=[("BACKGROUND",(0,0),(-1,0),LIGHT),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]
    t.setStyle(TableStyle(sty)); return t

CAP_QMIDE=rb.QMIDE
CHOQUE={
 "C1":"{debil} carga en solitario el peso emocional del dinero mientras {fuerte} lo vive con calma. El riesgo no son las cifras: es que {debil} somatice la alerta de toda la casa sin que {fuerte} lo perciba. La tranquilidad de {fuerte} se est\u00e1 financiando, en silencio, con el desgaste de {debil}.",
 "C2":"Ten\u00e9is horizontes de libertad desalineados: {debil} ve la meta lejos y {fuerte} la siente al alcance. Sin un \u00fanico n\u00famero com\u00fan, cada uno rema hacia una orilla distinta y el barco gira en c\u00edrculos.",
 "C3":"Ante un golpe, {fuerte} se siente con red y {debil} en el alambre. Esa asimetr\u00eda hace que {debil} frene decisiones que {fuerte} ve seguras \u2014 no por tacañer\u00eda, sino por puro instinto de supervivencia.",
 "C4":"{debil} percibe el estilo de vida como una deriva que aprieta; {fuerte}, como algo bajo control. Lo que para uno es \u00abdisfrutar lo ganado\u00bb, para el otro es \u00abver c\u00f3mo se escapa el futuro\u00bb.",
 "C5":"Esta distancia es delicada: habla de la ausencia, de qu\u00e9 pasar\u00eda si uno falta y del compromiso a largo plazo. {debil} ya lo ha mirado de frente; {fuerte}, a\u00fan no. No es burocracia: es cu\u00e1nto hab\u00e9is proyectado de verdad un \u00abpara siempre\u00bb.",
 "C6":"El gasto de imagen os divide: para {fuerte} es leg\u00edtimo, para {debil} inc\u00f3modo. Detr\u00e1s suele haber dos educaciones distintas sobre el dinero y dos necesidades distintas de aprobaci\u00f3n. No discut\u00eds por una cena: discut\u00eds por lo que significa.",
 "C7":"{debil} siente el riesgo de depender de una sola fuente; {fuerte} lo minimiza. Si el ingreso principal lo aporta quien menos lo teme, la casa puede estar m\u00e1s expuesta de lo que cree.",
 "C8":"{fuerte} ve oportunidad donde {debil} ve amenaza. En una crisis, esa diferencia de temperamento puede ser vuestra mayor fuerza \u2014uno protege, otro aprovecha\u2014 o vuestra peor pelea, si no os repart\u00eds los roles a prop\u00f3sito.",
 "C9":"{fuerte} cree tener el flujo bajo control; {debil} no. Cuando uno gobierna el dinero y el otro lo padece, el que no mira acaba dependiendo de la vigilancia del que s\u00ed: un reparto injusto que termina pasando factura.",
 "C10":"La deuda os pesa distinto: {debil} la siente encima, {fuerte} la lleva ligera. Si quien convive con la tensi\u00f3n es quien menos margen tiene, cualquier inversi\u00f3n que proponga {fuerte} chocar\u00e1 con un freno que ni siquiera entiende."}
SOMBRA={
 "C1":"Los dos llev\u00e1is el dinero con tensi\u00f3n a la vez. El problema no es de compatibilidad: es que cuando ambos os agot\u00e1is en lo mismo, no queda nadie sereno que sostenga la casa. Hay que romper el bucle entre los dos, no esperar a que el otro mejore.",
 "C2":"Ninguno tiene a\u00fan un rumbo claro hacia la libertad. No es un choque, es un vac\u00edo compartido: nadie est\u00e1 poniendo el destino. Vuestra tarea no es negociar, es decidir juntos a d\u00f3nde vais.",
 "C3":"Vuestra resiliencia es fr\u00e1gil por los dos lados. Un imprevisto os pillar\u00eda a ambos sin red, y nadie compensa a nadie. Es vuestra prioridad n\u00ba1, por encima de cualquier inversi\u00f3n.",
 "C4":"El estilo de vida se os infla a ambos. Sin freno en ninguno, cada subida de ingreso se evapora. Necesit\u00e1is un pacto com\u00fan, porque por separado os arrastr\u00e1is mutuamente.",
 "C5":"Aqu\u00ed ten\u00e9is una zona de sombra peligrosa: ninguno de los dos est\u00e1 protegido legalmente. No es un problema de pareja, es de desprotecci\u00f3n mutua. Vuestra sincron\u00eda en la inacci\u00f3n os deja expuestos ante el primer imprevisto serio.",
 "C6":"Los dos ced\u00e9is al gasto de imagen. Sin un ancla en ninguno, aliment\u00e1is juntos una rueda cara. Re\u00edr de ello juntos es el primer paso para soltarlo.",
 "C7":"Ambos depend\u00e9is en exceso de pocas fuentes. La casa entera se sostiene sobre patas fr\u00e1giles y ninguno diversifica. Es un riesgo estructural que solo se ve cuando ya ha fallado.",
 "C8":"Ninguno est\u00e1 preparado para aprovechar una crisis; ambos solo podr\u00edais sufrirla. Convertir eso en una ventaja conjunta es de las palancas m\u00e1s rentables que ten\u00e9is.",
 "C9":"A los dos se os escapa el control del flujo. Si nadie mira a d\u00f3nde va el dinero, decide la inercia por vosotros. Montar el sistema juntos es urgente.",
 "C10":"La deuda os pesa a ambos. Sin un plan com\u00fan, cada uno la gestiona a ciegas y el conjunto se tensa. Ponedla toda sobre la mesa, sin secretos, y haced un \u00fanico plan."}

def comparar_capa(code,a,b,nA,nB):
    nm=CAPAS[code]["nombre"]; g=abs(a-b)
    fuerte,debil=(nA,nB) if a<b else (nB,nA)
    if a<30 and b<30:
        return (f"{nm} es terreno firme para los dos ({a:.0f} y {b:.0f}). Es de vuestras fortalezas compartidas: "
                f"apoyaos aqu\u00ed cuando otras \u00e1reas aprieten.")
    if a>=51 and b>=51:
        return SOMBRA[code]
    if g>=30:
        return CHOQUE[code].format(fuerte=fuerte,debil=debil)
    return (f"{nm} est\u00e1 bastante equilibrado entre vosotros ({a:.0f} y {b:.0f}): diferencias peque\u00f1as que se "
            f"resuelven hablando, sin necesidad de un gran acuerdo.")

def paso_pareja(code):
    return {
     "C1":"compartid una cosa que el dinero os quita el sueño a cada uno. Nombrarlo en voz alta ya alivia.",
     "C2":"acordad UN numero comun de libertad y a qué edad lo querríais. Tener una meta compartida cambia todo.",
     "C3":"decidid juntos el tamano del colchon de emergencia de la casa y quién lo alimenta.",
     "C4":"elegid un gasto de estilo de vida que ninguno de los dos defendería ante el otro, y recortadlo.",
     "C5":"revisad si, faltando uno, el otro tendría acceso y protección. Es el regalo más grande que os podéis hacer.",
     "C6":"contaos sin juicio en qué gasta cada uno por imagen. Reír juntos de ello lo desactiva.",
     "C7":"mirad cuánto depende la casa de un solo sueldo y si eso os deja tranquilos.",
     "C8":"definid qué haríais juntos si llegara una gran oportunidad mañana.",
     "C9":"montad un presupuesto de hogar de tres cajas y revisadlo una vez al mes, los dos.",
     "C10":"poned toda la deuda de ambos sobre la mesa, sin secretos, y haced un único plan."}.get(code,"")

def _fill(d):
    d=dict(d or {}); d.setdefault("gasto_mensual",2000); d.setdefault("ingreso_mensual",3000)
    d.setdefault("ahorro_mensual",300); d.setdefault("patrimonio",30000); d.setdefault("edad",40); return d

def seccion_individual(nombre, prof, trans, salud, datos, radar_path, fi_hogar):
    pn=nombre.split()[0]
    bi_g,bl_g=rb.banda(rb.CAPAS["C1"],salud)
    out=[Paragraph("PERFIL INDIVIDUAL",kick), Paragraph(nombre,h_sec),
         Paragraph(f"Antes de cruzaros, esta es la foto psicol\u00f3gica de {pn}: c\u00f3mo vive el dinero por dentro. Las cifras del hogar son comunes (las ver\u00e9is juntas); lo que cambia de uno a otro es la percepci\u00f3n, el miedo y la prioridad.",body),
         Image(radar_path,width=112*mm,height=112*mm,hAlign="CENTER"),
         Paragraph(f"<b>{salud:.0f}</b>/100 \u2014 salud psicofinanciera global de {pn} (mejor que el {rb.pctil(salud):.0f}% de la cohorte).",body),
         PageBreak(), Paragraph(f"{pn}: fortalezas y focos",h_sub)]
    orden=sorted(rb.CAPAS,key=lambda c:prof[c]["score"])
    out.append(Paragraph("<b>Sus tres fortalezas</b>",small))
    for c in orden[:3]:
        out.append(Paragraph(f"&#8226;  <b>{rb.CAPAS[c]['nombre']}</b> ({prof[c]['score']:.0f}). {rb.OPORTUNIDAD[c]}",St("if1",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
    out.append(Paragraph("<b>Sus tres focos</b>",small))
    for c in orden[-3:][::-1]:
        out.append(Paragraph(f"&#8226;  <b>{rb.CAPAS[c]['nombre']}</b> ({prof[c]['score']:.0f}). {rb.RIESGO[c]}",St("if2",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
    out.append(Paragraph(f"{pn}: patrones transversales",h_sub))
    for t in ("PSIQUE","LIQUIDEZ","VINCULO"):
        v=trans[t]; vt=("%s"%v) if v is not None else "\u2014"
        out.append(Table([[Paragraph(f"<b>{t.capitalize()}</b>  {vt}/100",small),rb.Bar(v or 0,w=110*mm)]],
                         colWidths=[42*mm,114*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    out.append(Paragraph(f"{pn}: lo que revelan sus respuestas",h_sub))
    for ti,tx in rb.insights(prof,trans,fi_hogar):
        out.append(Paragraph(f"<font color='#0284C7'>&#8226;</font>  <b>{ti}</b>",small))
        out.append(Paragraph(tx,St("ii",fontSize=9.6,leading=13,leftIndent=10,spaceAfter=6)))
    out.append(PageBreak())
    out.append(Paragraph(f"{pn}: resumen capa por capa",h_sub))
    rows=[[Paragraph("<b>Capa</b>",small),Paragraph("<b>Score</b>",small),Paragraph("<b>Banda</b>",small)]]
    for c in rb.CAPAS:
        rows.append([Paragraph(rb.CAPAS[c]["nombre"],small),Paragraph("%.0f"%prof[c]["score"],small),
                     rb.Chip(prof[c]["banda"],BANDC[prof[c]["bi"]],w=84,h=13)])
    out.append(Table(rows,colWidths=[96*mm,20*mm,40*mm],style=TableStyle([("BACKGROUND",(0,0),(-1,0),LIGHT),
               ("LINEBELOW",(0,0),(-1,-1),0.3,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
               ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),6)])))
    out.append(PageBreak())
    return out

def seccion_adapta_pareja(pA,pB,nA,nB):
    comb={c:(pA[c]["score"]+pB[c]["score"])/2 for c in CAPAS}
    peores=sorted(comb,key=lambda c:comb[c],reverse=True)[:2]
    out=[PageBreak(), Paragraph("El siguiente paso con Adapta",h_sec),
         Paragraph("Este libro es vuestro mapa. <b>Adapta Family Office</b> es quien lo recorre con vosotros: 25 a\u00f1os "
                   "cuidando patrimonios familiares, con visi\u00f3n integral y sin productos propios ni conflictos de inter\u00e9s. "
                   "Y con experiencia espec\u00edfica acompa\u00f1ando a parejas \u2014 juntas o por separado \u2014 en sus decisiones de dinero.",body),
         Paragraph("Por vuestro diagn\u00f3stico conjunto, esto es lo que m\u00e1s os conviene:",body)]
    for code in peores:
        ti,de,url=rb.ADAPTA[code]
        out.append(Paragraph(f"<font color='{A_COL}'><b>&#8226; {ti}</b></font>",St("pad1",fontSize=11,leading=14,spaceBefore=6,spaceAfter=2)))
        out.append(Paragraph(de,St("pad2",fontSize=10,leading=14,leftIndent=8,spaceAfter=2)))
        out.append(Paragraph(f"<a href='{url}'><font color='#075985'>Ver c\u00f3mo lo trabajamos &#8594;</font></a>",St("pad3",fontSize=9.5,leading=13,leftIndent=8,spaceAfter=8)))
    out+=[Spacer(1,3*mm),
          Paragraph("Por d\u00f3nde empezamos",h_sub),
          Paragraph("Una conversaci\u00f3n inicial, sin compromiso, los dos. Os escuchamos primero, os proponemos despu\u00e9s.",
                    St("pcta",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=10,spaceBefore=2)),
          Spacer(1,2*mm),
          Paragraph("<b>Reserva vuestra conversaci\u00f3n:</b> <a href='https://www.adaptafamilyoffice.com/informe'><font color='#0284C7'>adaptafamilyoffice.com</font></a>  &#183;  "
                    "<b>WhatsApp:</b> <a href='https://wa.me/34683343531'><font color='#0284C7'>+34 683 34 35 31</font></a>  &#183;  info@adaptafamilyoffice.com",
                    St("pcta2",fontSize=9.5,leading=14))]
    return out

def build_couple(rA,dA,cliA,rB,dB,cliB,out):
    pA,trA,saludA=rb.perfil(rA); pB,trB,saludB=rb.perfil(rB)
    nA,nB=cliA["nombre"].split()[0], cliB["nombre"].split()[0]
    gaps=[abs(pA[c]["score"]-pB[c]["score"]) for c in CAPAS]
    compat=max(0,round(100-statistics.mean(gaps)))
    divs=divergencias_item(rA,rB)
    dual_radar(pA,pB,"_dualradar.png")
    S=[]
    # cover
    S+=[Spacer(1,32*mm),
        Paragraph("VUESTRO LIBRO FINANCIERO",St("c0",fontSize=12,textColor=GREY,fontName="Helvetica-Bold")),
        Spacer(1,3*mm),
        Paragraph("Diagnóstico<br/>de Pareja",St("c1",fontSize=40,leading=44,fontName="Helvetica-Bold")),
        Spacer(1,5*mm),
        Table([[""]],colWidths=[58*mm],style=[("LINEBELOW",(0,0),(-1,-1),2.5,colors.HexColor(A_COL))]),
        Spacer(1,7*mm),
        Paragraph("Dos vidas, una economía. Dónde os sostenéis y dónde chocáis.",St("c2",fontSize=12,textColor=ACCDK)),
        Spacer(1,38*mm),
        Paragraph(f"Escrito para  <b>{cliA['nombre']}</b>  &amp;  <b>{cliB['nombre']}</b>",St("cn",fontSize=12)),
        Paragraph(cliA["fecha"],small),
        Spacer(1,3*mm), Paragraph("Edición de Pareja · Tier 3",St("ct",fontSize=9.5,textColor=colors.HexColor(A_COL),fontName="Helvetica-Bold")),
        PageBreak()]
    # apertura
    S+=[Paragraph("Antes de empezar",h_sec),
        Paragraph(f"{nA} y {nB}: el dinero es la primera causa de conflicto en las parejas, y casi nunca porque "
                  "falte —sino porque cada uno lo vive distinto y no se habla. Este libro pone esas diferencias "
                  "sobre la mesa, sin juicio, para que dejen de operar en silencio.",body),
        Paragraph("No mide quién lo hace mejor. Mide dónde estáis alineados (vuestra fuerza conjunta) y dónde "
                  "divergís (vuestros focos de fricción). Al final encontraréis un guion para hablarlo.",body),
        Paragraph("Leedlo juntos. Esa es la mitad del valor.",body),
        PageBreak()]
    # compatibilidad + radar
    dAf=_fill(dA); dBf=_fill(dB)
    hogar={"gasto_mensual":dAf["gasto_mensual"]+dBf["gasto_mensual"],
           "ingreso_mensual":dAf["ingreso_mensual"]+dBf["ingreso_mensual"],
           "ahorro_mensual":dAf["ahorro_mensual"]+dBf["ahorro_mensual"],
           "patrimonio":dAf["patrimonio"]+dBf["patrimonio"],
           "edad":(dAf["edad"]+dBf["edad"])/2}
    fi_h=rb.fi_metrics(hogar)
    S+=[Paragraph("Vuestro mapa conjunto",h_sec),
        Table([[Paragraph(f"<font size=40 color='#075985'><b>{compat}</b></font><font size=13 color='#6B7280'>/100</font>",body),
                Paragraph(f"<b>Compatibilidad financiera</b><br/><font size=8 color='#6B7280'>Cuanto más alto, más "
                          f"parecida es vuestra forma de vivir el dinero. No es bueno ni malo en sí: las diferencias "
                          f"bien habladas suman.</font>",body)]],
              colWidths=[42*mm,118*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
        Spacer(1,1*mm),
        Table([[Paragraph(f"<font color='{A_COL}'>●</font> {cliA['nombre']}: <b>{saludA:.0f}</b>/100",small),
                Paragraph(f"<font color='{B_COL}'>●</font> {cliB['nombre']}: <b>{saludB:.0f}</b>/100",small)]],
              colWidths=[80*mm,80*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0)]),
        Image("_dualradar.png",width=125*mm,height=125*mm,hAlign="CENTER"),
        Spacer(1,2*mm),
        Paragraph("Vuestros n\u00fameros del hogar",h_sub),
        Paragraph("Estas cifras son <b>conjuntas</b>: describen vuestra econom\u00eda como hogar, no a uno ni a otro por "
                  "separado. Donde de verdad difer\u00eds es en c\u00f3mo las vive cada uno por dentro.",small),
        Table([["N\u00famero de libertad del hogar (regla 25\u00d7)",("%s \u20ac"%format(fi_h[0],",.0f")).replace(",",".")],
               ["Progreso hacia la libertad","%s %%"%fi_h[1]],
               ["Tasa de ahorro conjunta","%s %%"%fi_h[2]],
               ["A\u00f1os a la libertad","m\u00e1s de 100" if fi_h[3] is None else "%s a\u00f1os"%fi_h[3]]],
              colWidths=[105*mm,51*mm],style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
              ("FONTNAME",(1,0),(1,-1),"Helvetica-Bold"),("TEXTCOLOR",(1,0),(1,-1),ACCDK),
              ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)])),
        PageBreak()]
    # mapa de divergencias por capa
    S+=[Paragraph("Dónde coincidís y dónde no",h_sec),
        Paragraph("Capa por capa: vuestras dos puntuaciones y la distancia entre ambas. En rojo, las zonas que "
                  "conviene hablar.",body)]
    rows=[[Paragraph("<b>Capa</b>",small),Paragraph(f"<b>{nA}</b>",small),Paragraph(f"<b>{nB}</b>",small),
           Paragraph("<b>Distancia</b>",small),Paragraph("<b>Zona</b>",small)]]
    for c in CAPAS:
        a,b=pA[c]["score"],pB[c]["score"]; g=abs(a-b)
        zona = "Conflicto" if g>=30 else ("A revisar" if g>=18 else "Alineados")
        zc = "#B91C1C" if g>=30 else ("#EA580C" if g>=18 else "#15803D")
        rows.append([Paragraph(f"{c} · {CAPAS[c]['nombre']}",small),Paragraph(f"{a:.0f}",small),
                     Paragraph(f"{b:.0f}",small),Paragraph(f"{g:.0f}",small),
                     rb.Chip(zona,zc,w=64,h=13)])
    S+=[tbl(rows,[78*mm,15*mm,15*mm,20*mm,32*mm]),PageBreak()]
    rb.radar_png(pA,"_radarA.png"); rb.radar_png(pB,"_radarB.png")
    S+=seccion_individual(cliA["nombre"],pA,trA,saludA,dA,"_radarA.png",fi_h)
    S+=seccion_individual(cliB["nombre"],pB,trB,saludB,dB,"_radarB.png",fi_h)
    # capitulos comparativos por capa
    S+=[Paragraph("Capa por capa, los dos",h_sec),
        Paragraph("El corazon de vuestro libro: las diez dimensiones, leidas en pareja. La barra azul es "
                  f"{nA}; la morada, {nB}. Mas corta = mas sano.",body),PageBreak()]
    for n,code in enumerate(CAPAS,1):
        a,b=pA[code]["score"],pB[code]["score"]
        bloque=[Paragraph(f"CAPÍTULO {n}",kick),
                Paragraph(CAPAS[code]["nombre"],St("cb",fontSize=15,leading=19,textColor=ACCDK,fontName="Helvetica-Bold")),
                Table([[""]],colWidths=[40*mm],style=[("LINEBELOW",(0,0),(-1,-1),1.5,colors.HexColor(A_COL))]),
                Spacer(1,3*mm),
                Paragraph("Qué mide",h_sub),
                Paragraph("Esta capa mide "+CAP_QMIDE[code],body),
                Paragraph("Vuestros resultados",h_sub),
                Table([[Paragraph(f"<font color='{A_COL}'>●</font> {nA}: <b>{a:.0f}</b>/100",small),
                        Paragraph(f"<font color='{B_COL}'>●</font> {nB}: <b>{b:.0f}</b>/100",small)],
                       [Bar2(a,b,w=150*mm),""]],
                      colWidths=[80*mm,80*mm],style=[("SPAN",(0,1),(1,1)),("LEFTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,1),(0,1),4)]),
                Spacer(1,2*mm),
                Paragraph("Faceta por faceta",h_sub)]
        facs=CAPAS[code]["facetas"]
        for f in pA[code]["facetas"]:
            fa=pA[code]["facetas"].get(f,0); fb=pB[code]["facetas"].get(f,0)
            bloque.append(Table([[Paragraph("<b>%s</b>"%facs.get(f,f),small),Bar2(fa,fb,w=92),
                                  Paragraph(f"<font color='{A_COL}'>{fa:.0f}</font> / <font color='{B_COL}'>{fb:.0f}</font>",small)]],
                                 colWidths=[70*mm,40*mm,46*mm],
                                 style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,-1),0),
                                        ("LEFTPADDING",(1,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        bloque+=[Spacer(1,2*mm),
                Paragraph("Qué significa para vosotros",h_sub),
                Paragraph(comparar_capa(code,a,b,nA,nB),body),
                Paragraph("El riesgo para vuestra econom\u00eda",h_sub),
                Paragraph(rb.RIESGO[code],body),
                Paragraph("La oportunidad si lo trabaj\u00e1is juntos",h_sub),
                Paragraph(rb.OPORTUNIDAD[code],body),
                Paragraph("Vuestro siguiente paso",h_sub),
                Paragraph(f"<font color='{A_COL}'><b>&bull;</b></font>  "+paso_pareja(code),
                          St("pp",fontSize=10,leading=14,leftIndent=4,backColor=LIGHT,borderPadding=6)),
                Spacer(1,2*mm),
                Paragraph(f"\u201c{rb.PRINCIPIO[code]}\u201d",St("pr2",fontSize=10.5,leading=14,textColor=ACCDK,
                          fontName="Helvetica-Oblique")),
                Paragraph("Para hablar entre vosotros: "+rb.REFLEX[code],St("rf2",fontSize=10,leading=14,
                          textColor=INK,fontName="Helvetica-Oblique",spaceBefore=3))]
        S.append(KeepTogether(bloque)); S.append(PageBreak())
    # focos de friccion (item-level)
    S+=[Paragraph("Vuestros focos de fricción",h_sec),
        Paragraph("Las preguntas concretas donde respondisteis casi en extremos opuestos. Aquí es donde el dinero "
                  "se convierte en discusión sin que sepáis por qué. Priorizamos las de vínculo y transparencia.",body)]
    if not divs:
        S+=[Paragraph("Apenas hay divergencias marcadas: vuestra forma de ver el dinero está muy alineada. "
                      "Vuestro trabajo es de afinación, no de reconciliación.",body)]
    for d in divs[:6]:
        tag = "VÍNCULO" if d["vinc"] else f"Δ {d['gap']:.0f}"
        card=[Paragraph(f"<font color='{A_COL}'><b>{tag}</b></font>  ·  {CAPAS[d['capa']]['nombre']}",small),
              Paragraph(d["texto"],St("dt",fontSize=10,leading=14,fontName="Helvetica-Bold",spaceBefore=2,spaceAfter=3)),
              Table([[Paragraph(f"<font color='{A_COL}'>● {nA}</font>",small),Paragraph(d["A"],small)],
                     [Paragraph(f"<font color='{B_COL}'>● {nB}</font>",small),Paragraph(d["B"],small)]],
                    colWidths=[26*mm,130*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),3),("VALIGN",(0,0),(-1,-1),"TOP")])]
        S.append(KeepTogether(card)); S.append(Spacer(1,4*mm))
    S+=[PageBreak()]
    # guion de conversacion
    S+=[Paragraph("Vuestro guion de conversación",h_sec),
        Paragraph("Sentaos sin móviles, treinta minutos. Recorred estas preguntas por turnos: primero uno explica "
                  "su «por qué», luego el otro, sin interrumpir. El objetivo no es ganar, es entender.",body)]
    base_qs=[]
    for d in divs[:4]:
        base_qs.append(f"Sobre «{d['texto']}» — {nA} respondió «{d['A']}» y {nB} «{d['B']}». "
                       f"¿De dónde viene esa diferencia? ¿Qué historia familiar hay detrás?")
    if not base_qs:
        base_qs=[f"¿Qué significa para cada uno «estar tranquilo» con el dinero?",
                 f"Si llegara un imprevisto grande mañana, ¿cómo lo afrontaríais juntos?"]
    base_qs+=[ "¿Qué decisión financiera de los próximos 12 meses os da más miedo, y cuál más ilusión?",
               "¿Qué necesitáis del otro para sentir que vais en el mismo barco?"]
    for i,qq in enumerate(base_qs,1):
        S+=[Paragraph(f"<font color='{A_COL}'><b>{i}.</b></font>  {qq}",St("g",fontSize=10,leading=14,spaceAfter=8,leftIndent=2))]
    S+=[Spacer(1,4*mm),
        Paragraph("Cómo seguir",h_sub),
        Paragraph("Repetid el diagnóstico por separado dentro de unos meses: veréis cómo vuestras distancias se "
                  "acortan a medida que habláis. Eso es, exactamente, construir patrimonio en pareja.",body),
        Paragraph("Este libro es una herramienta de autoconocimiento; no sustituye asesoramiento profesional ni "
                  "terapia de pareja.",small)]
    S+=seccion_adapta_pareja(pA,pB,nA,nB)
    # ANEXO: respuestas de ambos (sin scores)
    NUM_MAP={"C2-1":"gasto_mensual","C2-2":"ingreso_mensual","C2-3":"ahorro_mensual","C2-4":"patrimonio","C2-5":"edad"}
    S+=[PageBreak(), Paragraph("Anexo \u2014 Vuestras respuestas",h_sec),
        Paragraph("Para total transparencia: lo que respondi\u00f3 cada uno, una al lado de la otra. "
                  "Leer esta tabla juntos ya abre conversaciones.",body)]
    for capa in INST["capas"]:
        rows=[[Paragraph("<b>Pregunta</b>",small),Paragraph("<b>%s</b>"%nA,small),Paragraph("<b>%s</b>"%nB,small)]]
        for it in capa["items"]:
            if it["tipo"]=="escala":
                ia=rA.get(it["id"]); ib=rB.get(it["id"])
                va=it["opciones"][ia]["texto"] if ia is not None else "\u2014"
                vb=it["opciones"][ib]["texto"] if ib is not None else "\u2014"
            else:
                va=str(dA.get(NUM_MAP.get(it["id"],""),"\u2014")); vb=str(dB.get(NUM_MAP.get(it["id"],""),"\u2014"))
            rows.append([Paragraph(it["texto"],small),Paragraph(va,small),Paragraph(vb,small)])
        t=Table(rows,colWidths=[86*mm,35*mm,35*mm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),LIGHT),("LINEBELOW",(0,0),(-1,-1),0.3,LINE),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",(0,0),(-1,-1),6),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]))
        S+=[Paragraph("%s \u00b7 %s"%(capa["code"],capa["nombre"]),h_sub), t]
    doc=SimpleDocTemplate(out,pagesize=A4,topMargin=20*mm,bottomMargin=20*mm,leftMargin=22*mm,rightMargin=22*mm,
                          title="Vuestro Libro Financiero — ITAP")
    doc.build(S,onFirstPage=rb.deco,onLaterPages=rb.deco); print("PDF PAREJA OK ->",out)

if __name__=="__main__":
    sevA={"C1":0.40,"C2":0.72,"C3":0.66,"C4":0.58,"C5":0.50,"C6":0.62,"C7":0.70,"C8":0.55,"C9":0.55,"C10":0.68}
    sevB={"C1":0.22,"C2":0.30,"C3":0.40,"C4":0.30,"C5":0.45,"C6":0.25,"C7":0.45,"C8":0.35,"C9":0.30,"C10":0.40}
    def mk(sev):
        r={}
        for capa in INST["capas"]:
            s=sev[capa["code"]]
            for it in capa["items"]:
                if it["tipo"]!="escala": continue
                n=len(it["opciones"]); r[it["id"]]=max(0,min(n-1,round(s*(n-1))))
        return r
    rA=mk(sevA); rB=mk(sevB)
    d={"gasto_mensual":2200,"ingreso_mensual":3200,"ahorro_mensual":300,"patrimonio":48000,"edad":41}
    build_couple(rA,d,{"nombre":"Laura Martín","email":"laura@x.com","fecha":"10/06/2026"},
                 rB,d,{"nombre":"Diego Ruiz","email":"diego@x.com","fecha":"10/06/2026"},
                 "ITAP_Libro_Pareja_demo.pdf")
