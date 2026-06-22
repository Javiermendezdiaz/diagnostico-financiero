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
import score_v2 as sv

INST=rb.INST; CAPAS=rb.CAPAS
INK=colors.HexColor("#262620"); A_COL="#B8860B"; B_COL="#3F3F46"
ACCDK=colors.HexColor("#1A1A17"); GREY=colors.HexColor("#7A7A72")
LIGHT=colors.HexColor("#FBF6E0"); LINE=colors.HexColor("#E4E1D5"); BANDC=rb.BANDC

def St(n,**k): k.setdefault("fontName","Helvetica"); k.setdefault("textColor",INK); return ParagraphStyle(n,**k)
h_sec=St("hs",fontSize=20,leading=24,textColor=ACCDK,fontName=rb.SB,spaceAfter=8)
h_sub=St("hu",fontSize=10.5,leading=13,textColor=colors.HexColor("#1A1A17"),fontName="Helvetica-Bold",spaceBefore=7,spaceAfter=3)
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
        v=[100-prof[c]["score"] for c in CAPAS]; v+=v[:1]
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
# Voz de PAREJA para "Qué mide" (plural/género correcto; evita el "tu" singular del libro individual)
QMIDE_PAREJA={
 "C1":"cómo vivís cada uno la relación con el dinero por dentro: el estrés, el sueño, la ansiedad y la culpa.",
 "C2":"cuánto os separa de la libertad financiera real y si tenéis un plan que la sostenga.",
 "C3":"cuánto aguantaríais un golpe —un paro, un gasto inesperado— sin que vuestra vida se derrumbe.",
 "C4":"si vuestro estilo de vida crece con sentido o se infla en silencio y se come vuestros ingresos.",
 "C5":"si vuestro patrimonio y vuestra familia están protegidos legalmente ante lo inesperado.",
 "C6":"cuánto de vuestro gasto financia una imagen en lugar de vuestra vida real.",
 "C7":"cuánto dependéis de una sola fuente de ingresos: vuestro mayor riesgo oculto.",
 "C8":"si un golpe os hunde o podéis salir reforzados de él.",
 "C9":"si gobernáis el dinero que entra y sale, o se os escapa sin saber a dónde.",
 "C10":"el peso y la salud de vuestra deuda, y si resistiría una caída de ingresos.",
 "C11":"si vuestro dinero solo se defiende o además construye: vuestra capacidad real de hacer crecer lo que ya tenéis.",
 "C12":"si canalizáis vuestro ahorro hacia la inversión —la única palanca que hace crecer el patrimonio de forma exponencial— o lo dejáis parado perdiendo valor contra la inflación.",
}
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
 "C10":"La deuda os pesa distinto: {debil} la siente encima, {fuerte} la lleva ligera. Si quien convive con la tensi\u00f3n es quien menos margen tiene, cualquier inversi\u00f3n que proponga {fuerte} chocar\u00e1 con un freno que ni siquiera entiende.",
 "C11":"{fuerte} ve la palanca de crecer \u2014segundas fuentes, poner el dinero a trabajar\u2014 como algo natural; {debil}, como un riesgo que prefiere no tocar. Si uno empuja para construir y el otro frena por miedo, la casa se queda quieta justo donde m\u00e1s podr\u00eda avanzar. No es que uno tenga raz\u00f3n: es que el acelerador y el freno a\u00fan no se han puesto de acuerdo."}
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
 "C10":"La deuda os pesa a ambos. Sin un plan com\u00fan, cada uno la gestiona a ciegas y el conjunto se tensa. Ponedla toda sobre la mesa, sin secretos, y haced un \u00fanico plan.",
 "C11":"A ninguno de los dos le sobra energ\u00eda para construir: ambos est\u00e1is en modo defensa, no ataque. No es un choque, es un techo compartido \u2014 mientras los dos solo protej\u00e1is, nadie pondr\u00e1 el patrimonio a crecer. La palanca est\u00e1 sin tocar en las dos manos."}

def comparar_capa(code,a,b,nA,nB):
    nm=CAPAS[code]["nombre"]; g=abs(a-b)
    fuerte,debil=(nA,nB) if a<b else (nB,nA)
    if a<30 and b<30:
        return (f"{nm} es terreno firme para los dos ({100-a:.0f} y {100-b:.0f}). Es de vuestras fortalezas compartidas: "
                f"apoyaos aqu\u00ed cuando otras \u00e1reas aprieten.")
    if a>=51 and b>=51:
        return SOMBRA.get(code, f"{nm} os pesa a los dos a la vez: es un frente compartido, no un desencuentro. Atajadlo juntos, no esperéis a que el otro mejore.")
    if g>=30:
        return CHOQUE.get(code, "{debil} lo vive con más tensión que {fuerte}. Esa diferencia, hablada, se convierte en complemento; callada, en reproche silencioso.").format(fuerte=fuerte,debil=debil)
    return (f"{nm} est\u00e1 bastante equilibrado entre vosotros ({100-a:.0f} y {100-b:.0f}): diferencias peque\u00f1as que se "
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
     "C10":"poned toda la deuda de ambos sobre la mesa, sin secretos, y haced un único plan.",
     "C11":"elegid juntos UNA palanca de crecimiento para este año —una segunda fuente, poner a trabajar un ahorro parado— y repartíos quién la lidera."}.get(code,"")

def _fill(d):
    d=dict(d or {}); d.setdefault("gasto_mensual",2000); d.setdefault("ingreso_mensual",3000)
    d.setdefault("ahorro_mensual",300); d.setdefault("patrimonio",30000); d.setdefault("edad",40); return d

def _callout(titulo, texto, barra, fondo):
    return KeepTogether([Table([[Paragraph(
        f"<font color='{barra}'><b>{titulo}</b></font><br/>"
        f"<font size=9.5>{texto}</font>",
        St("co",fontSize=10.5,leading=15))]], colWidths=[156*mm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(fondo)),
          ("LEFTPADDING",(0,0),(-1,-1),11),("RIGHTPADDING",(0,0),(-1,-1),11),
          ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
          ("LINEBEFORE",(0,0),(0,-1),3,colors.HexColor(barra))]))])

def _opt_score(resp, iid):
    for capa in INST["capas"]:
        for it in capa["items"]:
            if it["id"]==iid and it["tipo"]=="escala":
                idx=resp.get(iid)
                if idx is None: return None
                try: return it["opciones"][idx]["score"]
                except (IndexError,TypeError): return None
    return None

def _compartimento(prof, resp):
    """Compartimento estanco: opacidad de deuda + deuda familiar con tension."""
    transp=_opt_score(resp,"C10-9")   # >=66: solo en parte / la oculto
    famil=_opt_score(resp,"C10-10")   # >=66: deuda familiar con tension
    if transp is not None and famil is not None and transp>=66 and famil>=66:
        return ("Un compartimento estanco en la pareja",
                "Hay aquí un patrón que conviene mirar de frente: parte de la deuda no es del todo transparente "
                "y, a la vez, existe un vínculo financiero con la familia de origen que genera tensión. Cuando esas dos "
                "cosas coinciden, no suele ser un olvido: es un mecanismo de protección. El problema es que un anclaje "
                "que se vive como secreto frena, de forma inconsciente, cualquier plan a largo plazo — porque destaparlo "
                "deja las cartas al descubierto. El patrimonio no se desbloquea con técnica, sino poniendo esto sobre la mesa.")
    return None

def seccion_caminos_hogar(dA, dB):
    a=_fill(dA); b=_fill(dB)
    hog={"edad":int(round((a["edad"]+b["edad"])/2)),
         "patrimonio":a["patrimonio"]+b["patrimonio"],
         "ahorro_mensual":a["ahorro_mensual"]+b["ahorro_mensual"],
         "ingreso_mensual":a["ingreso_mensual"]+b["ingreso_mensual"],
         "gasto_mensual":a["gasto_mensual"]+b["gasto_mensual"],
         "inversiones_liquidas":(a.get("inversiones_liquidas") or 0)+(b.get("inversiones_liquidas") or 0),
         "colchon_liquido":(a.get("colchon_liquido") or 0)+(b.get("colchon_liquido") or 0),
         "rentabilidad_actual":max(a.get("rentabilidad_actual") or 0, b.get("rentabilidad_actual") or 0)}
    try:
        f65,mid65,m65,medad,modo=rb.proyeccion_chart(hog,"_proyhogar.png")
    except Exception:
        return []
    out=[PageBreak(), Paragraph("Vuestros tres caminos",h_sec),
         Paragraph("El patrimonio del hogar a la jubilación, según lo que decidáis juntos: dejarlo como está, invertirlo "
                   "bien, o ejecutar vuestro plan conjunto. La distancia entre las líneas no la decide el mercado — la decidís vosotros.",body),
         Image("_proyhogar.png",width=160*mm,height=75*mm,hAlign="CENTER")]
    if modo=="3":
        _cl=St("chl",fontSize=8.5,leading=11,textColor=colors.HexColor("#6B7280"))
        def cn(lab,val,col):
            return [Paragraph(lab,_cl),Paragraph("<b>%s</b>"%rb._eur(val),St("cnh"+col,fontSize=18,leading=22,textColor=colors.HexColor(col),fontName=rb.FB))]
        out+=[Spacer(1,3*mm),
              Table([[cn("Sin hacer nada",f65,"#9A3B2E"),cn("Invirtiendo bien",mid65,"#B8860B"),cn("Ejecutando vuestro plan",m65,"#1D6F42")]],
                    colWidths=[53*mm,53*mm,54*mm],style=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),2)]),
              Spacer(1,2*mm),
              Paragraph(f"Entre quedaros quietos y ejecutar vuestro plan hay <b>{rb._eur(m65-f65)}</b>. Esa cifra es vuestra "
                        f"decisión conjunta, repetida cada mes que empezáis — o que aplazáis.",St("chg",fontSize=10.5,leading=15,textColor=INK))]
    out+=[PageBreak()]
    return out

def seccion_dafo_pareja(pA,pB,nA,nB):
    sc=lambda c,pp:pp[c]["score"]; capas=list(rb.CAPAS); nom=lambda c:rb.CAPAS[c]["nombre"]
    fuertes=sorted([c for c in capas if max(sc(c,pA),sc(c,pB))<=40], key=lambda c:sc(c,pA)+sc(c,pB))[:3]
    debiles=sorted([c for c in capas if min(sc(c,pA),sc(c,pB))>=55], key=lambda c:-(sc(c,pA)+sc(c,pB)))[:3]
    compl=sorted([c for c in capas if abs(sc(c,pA)-sc(c,pB))>=40], key=lambda c:-abs(sc(c,pA)-sc(c,pB)))[:3]
    def lst(cs,vacio):
        return [Paragraph("&#8226;  "+nom(c),small) for c in cs] or [Paragraph("<font color='#6B7280'>&#8226;  "+vacio+"</font>",small)]
    out=[PageBreak(), Paragraph("Vuestro DAFO de hogar",h_sec),
         Paragraph("Una pareja no es la suma de dos economías: es un sistema. Aquí, de un vistazo, dónde sois fuertes juntos, "
                   "dónde flojeáis los dos a la vez y —lo más valioso— dónde el uno puede cubrir al otro.",body),
         Spacer(1,4*mm)]
    F=rb._box([Paragraph("<font color='#1D6F42'><b>FORTALEZAS COMPARTIDAS</b></font>",small)]+lst(fuertes,"Aún sin fortaleza común clara."),"#EAF3EC","#1D6F42",ancho=78*mm)
    D=rb._box([Paragraph("<font color='#9A3B2E'><b>DEBILIDADES DEL HOGAR</b></font>",small)]+lst(debiles,"Sin debilidad compartida grave."),"#FBF4E4","#9A3B2E",ancho=78*mm)
    out+=[Table([[F,D]],colWidths=[80*mm,80*mm],style=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(0,0),4)]),Spacer(1,5*mm)]
    if compl:
        rows=[Paragraph("Vuestra complementariedad — la ventaja real de ser dos",h_sub)]
        for c in compl:
            fuerte,debil=(nA,nB) if sc(c,pA)<sc(c,pB) else (nB,nA)
            rows.append(Paragraph(f"&#8226;  En <b>{nom(c)}</b>, <b>{fuerte}</b> está más entero y puede sostener a <b>{debil}</b>. "
                                  f"Repartíos el rol aquí: que lidere quien lo tiene resuelto, en vez de fallar los dos por igual.",
                                  St("dc",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
        out+=rows
    else:
        out+=[Paragraph("Hoy no hay complementariedad clara: en casi todo estáis al mismo nivel. Las áreas flojas las tendréis "
                        "que levantar juntos, sin que uno pueda tirar del otro — más razón para hacerlo en equipo.",body)]
    out+=[PageBreak()]
    return out

def seccion_individual(nombre, prof, trans, salud, datos, radar_path, fi_hogar, resp=None, extras=None):
    pn=(nombre.split()[0] if (nombre or "").strip() else "esta persona")
    bi_g,bl_g=rb.banda(rb.CAPAS["C1"],salud)
    out=[Paragraph("PERFIL INDIVIDUAL",kick), Paragraph(nombre,h_sec),
         Paragraph(f"Antes de cruzaros, esta es la foto psicol\u00f3gica de {pn}: c\u00f3mo vive el dinero por dentro. Las cifras del hogar son comunes (las ver\u00e9is juntas); lo que cambia de uno a otro es la percepci\u00f3n, el miedo y la prioridad.",body),
         Image(radar_path,width=112*mm,height=112*mm,hAlign="CENTER"),
         Paragraph(f"<b>{100-salud:.0f}</b>/100 \u2014 salud psicofinanciera global de {pn} (100 = \u00f3ptimo).",body)]
    coh=rb.coherencia(salud, rb.fi_metrics(_fill(datos)), _fill(datos))
    if coh:
        out+=[Spacer(1,3*mm), _callout(coh[0], coh[1], "#1A1A17", "#FBF6E0")]
    est=_compartimento(prof, resp or {})
    if est:
        out+=[Spacer(1,3*mm), _callout(est[0], est[1], "#B45309", "#FBF3E8")]
    out+=[PageBreak(), Paragraph(f"{pn}: fortalezas y focos",h_sub)]
    orden=sorted(rb.CAPAS,key=lambda c:prof[c]["score"])
    out.append(Paragraph("<b>Tus tres fortalezas</b>",small))
    for c in orden[:3]:
        out.append(Paragraph(f"&#8226;  <b>{rb.CAPAS[c]['nombre']}</b> ({100-prof[c]['score']:.0f}/100). {rb.OPORTUNIDAD[c]}",St("if1",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
    out.append(Paragraph("<b>Tus tres focos</b>",small))
    for c in orden[-3:][::-1]:
        out.append(Paragraph(f"&#8226;  <b>{rb.CAPAS[c]['nombre']}</b> ({100-prof[c]['score']:.0f}/100). {rb.RIESGO[c]}",St("if2",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
    out.append(Paragraph(f"{pn}: patrones transversales",h_sub))
    for t in ("PSIQUE","LIQUIDEZ","VINCULO"):
        v=trans[t]; vt=("%s"%v) if v is not None else "\u2014"
        out.append(Table([[Paragraph(f"<b>{t.capitalize()}</b>  {vt}/100",small),rb.Bar(v or 0,w=110*mm)]],
                         colWidths=[42*mm,114*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    out.append(Paragraph(f"{pn}: lo que revelan tus respuestas",h_sub))
    for ti,tx in rb.insights(prof,trans,fi_hogar):
        out.append(Paragraph(f"<font color='#1A1A17'>&#8226;</font>  <b>{ti}</b>",small))
        out.append(Paragraph(tx,St("ii",fontSize=9.6,leading=13,leftIndent=10,spaceAfter=6)))
    if extras:
        try: out += rb.seccion_ratio_vida(extras) + rb.seccion_nudo(extras)
        except Exception: pass
    out.append(PageBreak())
    out.append(Paragraph(f"{pn}: resumen capa por capa",h_sub))
    rows=[[Paragraph("<b>Capa</b>",small),Paragraph("<b>Score</b>",small),Paragraph("<b>Banda</b>",small)]]
    for c in rb.CAPAS:
        rows.append([Paragraph(rb.CAPAS[c]["nombre"],small),Paragraph("%.0f"%(100-prof[c]["score"]),small),
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
        out.append(Paragraph(f"<a href='{url}'><font color='#1A1A17'>Ver c\u00f3mo lo trabajamos &#8594;</font></a>",St("pad3",fontSize=9.5,leading=13,leftIndent=8,spaceAfter=8)))
    out+=[Spacer(1,3*mm),
          Paragraph("Por d\u00f3nde empezamos",h_sub),
          Paragraph("Una conversaci\u00f3n inicial, sin compromiso, los dos. Os escuchamos primero, os proponemos despu\u00e9s.",
                    St("pcta",fontSize=10.5,leading=15,textColor=INK,backColor=LIGHT,borderPadding=10,spaceBefore=2)),
          Spacer(1,2*mm),
          Paragraph("<b>Reserva vuestra conversaci\u00f3n:</b> <a href='https://www.adaptafamilyoffice.com/informe'><font color='#1A1A17'>adaptafamilyoffice.com</font></a>  &#183;  "
                    "<b>WhatsApp:</b> <a href='https://wa.me/34683343531'><font color='#1A1A17'>+34 683 34 35 31</font></a>  &#183;  info@adaptafamilyoffice.com",
                    St("pcta2",fontSize=9.5,leading=14))]
    return out

CHOQUE_ARQ = {
 ("EST","EST"):("Los dos vivís el dinero en presente: disfrutáis hoy y os cuesta aplazar. Es una pareja que sabe gozar lo que gana —y eso une—, pero sin un guardián en casa el nivel de vida se come el futuro sin que nadie dé la alarma.",
   "Poneos juntos un límite de gasto y automatizad el ahorro ANTES de disfrutar: que el sistema haga de guardián por vosotros."),
 ("EST","LIB"):("Uno quiere vivir bien hoy; el otro, comprar libertad para mañana. No es el mismo dinero gastado de forma distinta: son dos relojes distintos. El Vividor mira el presente, el Explorador el futuro abierto.",
   "Repartid el excedente en dos sobres explícitos: uno para disfrute ahora, otro para libertad futura. Así ninguno siente que el otro le roba su sentido del dinero."),
 ("EST","MUL"):("El Constructor quiere reinvertir y multiplicar; el Vividor quiere cosechar y disfrutar. La tensión clásica: '¿para qué tanto crecer si no vivimos?' frente a '¿cómo gastas lo que aún no hemos hecho crecer?'.",
   "Fijad un porcentaje fijo que SIEMPRE se reinvierte y otro que SIEMPRE se disfruta. Sin ese pacto, cada euro es una pequeña negociación que desgasta."),
 ("EST","SEG"):("El Guardián protege; el Vividor disfruta. Para uno, gastar es vivir; para el otro, una grieta en el muro. Cada compra puede sentirse como un pequeño abandono del pacto de seguridad, aunque nadie lo diga en voz alta.",
   "Acordad un 'presupuesto de disfrute' intocable: el Vividor gasta sin culpa dentro de él, y el Guardián no vigila por debajo de esa línea."),
 ("LIB","LIB"):("Los dos buscáis autonomía y odiáis sentiros atados. Gran sintonía de valores —el dinero es tiempo, no estatus—, pero con un riesgo: si ninguno quiere ocuparse de la 'fontanería' (presupuesto, planes), la libertad se queda en deseo sin estructura.",
   "Turnaos la gestión por trimestres: la libertad necesita un sistema detrás, y compartir el trabajo aburrido evita que recaiga en uno solo."),
 ("LIB","MUL"):("Sois una pareja de crecimiento: uno construye patrimonio, el otro persigue autonomía. Os entendéis en el riesgo, pero podéis chocar en el destino: el Constructor quiere más capital; el Explorador, salir antes a vivir.",
   "Definid juntos vuestro 'número de libertad' y la fecha. Le da al Constructor una meta concreta y al Explorador la certeza de que crecer tiene un final."),
 ("LIB","SEG"):("El Explorador quiere soltar amarras; el Guardián, asegurarlas. Lo que para uno es 'por fin libre', para el otro es 'expuesto'. Esta es de las combinaciones que más fricción genera ante decisiones grandes (dejar un empleo, mudarse, emprender).",
   "Antes de cada salto, acordad de antemano el colchón mínimo que tranquiliza al Guardián. Con esa red puesta, el Explorador puede volar sin pelea."),
 ("MUL","MUL"):("Los dos pensáis en sistemas y multiplicación: ambiciosos, cómodos con el riesgo. Es un motor potente, pero con dos aceleradores y ningún freno la casa puede quedar sobreexpuesta —todo invertido, poca liquidez— justo cuando más se necesita.",
   "Nombrad por escrito vuestro colchón de seguridad intocable. Dos constructores necesitan, a propósito, fabricarse un guardián."),
 ("MUL","SEG"):("El Constructor quiere mover el dinero; el Guardián, protegerlo. Es la pareja clásica del 'invirtámoslo' contra el 'dejémoslo seguro'. Bien resuelta, es oro: uno empuja, otro frena en el momento justo. Mal resuelta, cada propuesta de inversión es una discusión.",
   "Dividid el patrimonio en dos cubos: uno blindado (manda el Guardián) y otro de crecimiento (manda el Constructor). Cada uno reina en el suyo y la guerra se acaba."),
 ("SEG","SEG"):("Los dos buscáis seguridad por encima de todo. Hay una paz enorme en eso —os entendéis sin explicaros—, pero también un riesgo silencioso: con dos guardianes y ningún constructor, el patrimonio puede quedarse dormido, perdiendo valor frente a la inflación por exceso de prudencia.",
   "Acordad una pequeña parte —aunque sea el 10%— que os deis permiso para hacer crecer. Dos guardianes necesitan, juntos, atreverse un poco."),
}

def seccion_arquetipos(rA,rB,nA,nB):
    aA,_,_=rb.arquetipo(rA); aB,_,_=rb.arquetipo(rB)
    if not aA and not aB: return []
    out=[PageBreak(), Paragraph("Vuestros arquetipos del dinero",h_sec),
         Paragraph("Antes que los números está el significado: qué <b>es</b> el dinero para cada uno. "
                   "No hay arquetipos mejores ni peores —cada uno aporta algo—, pero cuando dos personas "
                   "operan desde significados distintos, el mismo euro puede querer decir cosas opuestas. Aquí está "
                   "el código de fondo de vuestras decisiones.",body)]
    def col_arquetipo(nombre,code):
        if not code:
            return [Paragraph(f"<b>{nombre}</b> no completó las preguntas de arquetipo.",small)]
        m=rb.ARQ_META[code]
        return [
            Table([[Paragraph(f"<font color='{m['color']}'><b>{nombre}</b><br/>{m['nombre']}</font><br/>"
                              f"<font color='#7A7A72' size=8>{m['lema']}</font>",St("at",fontSize=10.5,leading=13))]],
                  colWidths=[74*mm],
                  style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#FBF6E0")),
                    ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
                    ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
                    ("LINEBEFORE",(0,0),(0,-1),3,colors.HexColor(m['color']))])),
            Spacer(1,2*mm),
            Paragraph(m['desc'],St("ad",fontSize=9.3,leading=13,alignment=TA_JUSTIFY)),
            Paragraph(f"<font color='#1D6F42'><b>Aporta:</b></font> {m['luz']}",St("al",fontSize=8.6,leading=11.5,textColor=GREY)),
            Paragraph(f"<font color='#B91C1C'><b>Punto ciego:</b></font> {m['sombra']}",St("aj",fontSize=8.6,leading=11.5,textColor=GREY))]
    out.append(Table([[col_arquetipo(nA,aA), col_arquetipo(nB,aB)]],colWidths=[78*mm,78*mm],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(0,-1),0),
          ("LEFTPADDING",(1,0),(1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0)])))
    out.append(Spacer(1,4*mm))
    if aA and aB:
        key=tuple(sorted([aA,aB])); texto,regla=CHOQUE_ARQ[key]
        if aA==aB:
            titulo=f"Los dos sois <b>{rb.ARQ_META[aA]['nombre']}</b>"
        else:
            titulo=f"<b>{rb.ARQ_META[aA]['nombre']}</b> + <b>{rb.ARQ_META[aB]['nombre']}</b>"
        out+=[Paragraph("Vuestra combinación",h_sub),
              Paragraph(titulo,St("ac",fontSize=11,leading=14,textColor=ACCDK,fontName="Helvetica-Bold",spaceAfter=4)),
              Paragraph(texto,body),
              KeepTogether([Table([[Paragraph(f"<b>Vuestra regla de oro:</b> {regla}",
                    St("rg",fontSize=10,leading=14,textColor=colors.HexColor("#7A5C00")))]],
                  colWidths=[156*mm],
                  style=TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#FEF9E7")),
                    ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
                    ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
                    ("BOX",(0,0),(-1,-1),0.6,colors.HexColor("#E9C46A"))]))])]
    return out

def laboratorio_pareja(rA,rB,pA,pB,nA,nB,dA,dB,hogar,divs):
    out=[PageBreak(), Paragraph("Vuestro laboratorio de pareja",h_sec),
         Paragraph("Lo que sigue no se lee, se hace. Son tres ejercicios para esta semana. Imprimid esta página, "
                   "coged un boli y rellenadla juntos. Vale más quince minutos haciendo esto que releer todo el libro.",body)]
    # Ej 1: Caja de autonomia
    libre=max(hogar.get("ingreso_mensual",0)-hogar.get("gasto_mensual",0)-hogar.get("ahorro_mensual",0),0)
    sug=int(round(max(libre*0.15,50)/10.0))*10
    out+=[Paragraph("1 · La caja de autonomía",h_sub),
          Paragraph("La mayoría de los conflictos de dinero en pareja no son por las cifras grandes, sino por sentirse "
                    "fiscalizado en las pequeñas. La solución no es discutir cada gasto: es acordar una cantidad mensual "
                    "para cada uno —su <b>caja de autonomía</b>— en la que el otro <b>no opina, no pregunta, no juzga</b>.",body),
          rb._box([Paragraph(f"<b>Nuestro pacto:</b> cada mes, {nA} y {nB} dispondrán de una caja personal de "
                f"<b>__________ €</b> cada uno (orientativo para vuestro excedente: unos {rb._eur(sug)}). "
                f"Sobre ese dinero no se piden explicaciones. Firmamos:",St("p1",fontSize=10.5,leading=15)),
                Spacer(1,7*mm),
                Table([["Firma "+nA,"Firma "+nB]],colWidths=[78*mm,78*mm],
                  style=TableStyle([("LINEABOVE",(0,0),(-1,0),0.6,colors.HexColor("#9CA3AF")),
                    ("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#9CA3AF")),("FONTSIZE",(0,0),(-1,0),8),
                    ("TOPPADDING",(0,0),(-1,0),3)]))],"#FBF6E0","#1A1A17",ancho=158*mm),
          Spacer(1,4*mm)]
    # Ej 2: rol cruzado (solo si arquetipos distintos)
    aA,_,_=rb.arquetipo(rA); aB,_,_=rb.arquetipo(rB)
    if aA and aB and aA!=aB:
        out+=[Paragraph("2 · Veinte minutos en la piel del otro",h_sub),
              Paragraph(f"{nA} vive el dinero como <b>{rb.ARQ_META[aA]['nombre']}</b>; {nB}, como "
                        f"<b>{rb.ARQ_META[aB]['nombre']}</b>. Este fin de semana, intercambiad los papeles durante veinte "
                        f"minutos: {nA} defiende con todas sus fuerzas la postura de {nB}, y al revés. No vale usar tus "
                        f"propios argumentos. El objetivo no es ganar: es sentir, aunque sea un rato, por qué el otro "
                        f"decide como decide. Apuntad aquí qué descubristeis al poneros en su lugar:",body),
              rb._lineas(2,ancho=158*mm),Spacer(1,4*mm)]
        n3="3"
    else:
        n3="2"
    # Ej 3: preparacion legal humana (si C5 debil en alguno)
    if pA["C5"]["score"]>=50 or pB["C5"]["score"]>=50:
        out+=[Paragraph(f"{n3} · La conversación que nadie quiere tener (y que más protege)",h_sub),
              Paragraph("Vuestro blindaje legal tiene huecos. No hace falta ir al notario hoy, pero sí responder juntos "
                        "a tres preguntas que, el día que hagan falta, lo cambian todo. Hacedlo con calma, como un acto "
                        "de cuidado mutuo, no de miedo:",body),
              Paragraph("&#8226; Si uno faltara, ¿el otro sabe dónde están las cuentas, claves y documentos clave?",small),
              Paragraph("&#8226; ¿Tiene cada uno liquidez a su nombre para el primer mes, si una cuenta conjunta se bloqueara?",small),
              Paragraph("&#8226; Sin testamento, ¿sabéis quién heredaría qué? ¿Es lo que querríais?",small),
              rb._lineas(2,ancho=158*mm),
              Paragraph("Si a más de una respondéis «no sé», vuestro paso de esta semana no es un presupuesto: es una "
                        "llamada a la notaría. Apuntad aquí el día que la haréis: ______________.",small),
              Spacer(1,4*mm)]
    # Reparto de roles asimetrico (responsable claro, nada de "ambos")
    ejec, guard = (nA, nB) if pA["C9"]["score"]<=pB["C9"]["score"] else (nB, nA)
    out+=[Paragraph("Vuestro reparto de roles",h_sub),
          Paragraph("«Ambos» es la palabra que mata los planes: si es de los dos, no es de nadie. Por eso cada tarea "
                    "tiene un dueño. No es jerarquía, es eficacia:",body),
          Paragraph(f"&#8226; <b>{ejec} \u2014 Ejecución.</b> Por tu mayor control del flujo de caja, te encargas de montar "
                    f"las transferencias automáticas, abrir las cuentas y llamar a la notaría. Tú mueves las piezas.",small),
          Paragraph(f"&#8226; <b>{guard} \u2014 Guardián del colchón.</b> Por tu instinto de protección, velas por que el "
                    f"fondo de seguridad no se toque y das el visto bueno antes de cualquier inversión. {ejec} ejecuta, "
                    f"pero {guard} firma la conformidad.",small),
          Spacer(1,3*mm)]
    return out

def build_couple(rA,dA,cliA,rB,dB,cliB,out,sintesis=None,perfilA=None,perfilB=None):
    global INST, CAPAS
    _iv2=rb._cargar_v2(); _c2={c["code"]:c for c in _iv2["capas"]}
    rb.INST=_iv2; rb.CAPAS=_c2; INST=_iv2; CAPAS=_c2          # el libro de pareja se puntúa sobre el instrumento v2
    nA=(cliA["nombre"].split()[0] if (cliA.get("nombre") or "").strip() else "Persona A")
    nB=(cliB["nombre"].split()[0] if (cliB.get("nombre") or "").strip() else "Persona B")
    rb.CLIENTE_NOMBRE="%s & %s"%(nA,nB)                       # evita que se filtre el nombre de un informe anterior
    pA,trA,saludA=rb.perfil(rA); pB,trB,saludB=rb.perfil(rB)
    gaps=[abs(pA[c]["score"]-pB[c]["score"]) for c in CAPAS]
    compat=max(0,round(100-statistics.mean(gaps)))
    divs=divergencias_item(rA,rB)
    dual_radar(pA,pB,"_dualradar.png")
    S=[]
    _hero_done=False
    try:
        if getattr(rb,"_LEGADO_OK",False):
            import legado_pages as _lp
            _dAf=_fill(dA); _dBf=_fill(dB)
            _hog={"gasto_mensual":_dAf["gasto_mensual"]+_dBf["gasto_mensual"],"ingreso_mensual":_dAf["ingreso_mensual"]+_dBf["ingreso_mensual"],"ahorro_mensual":_dAf["ahorro_mensual"]+_dBf["ahorro_mensual"],"patrimonio":_dAf["patrimonio"]+_dBf["patrimonio"],"edad":(_dAf["edad"]+_dBf["edad"])/2}
            _hn=rb.fi_metrics(_hog)[0]
            for _pg in _lp.pareja_hero(nA,nB,cliA,dA,dB,pA,pB,_hn,cliA.get("fecha",""),perfilA=perfilA,perfilB=perfilB):
                S+=[rb.FullBleedImage(_pg), PageBreak()]
            _hero_done=True
    except Exception:
        _hero_done=False
    # cover (fallback si no hay Legado)
    if not _hero_done: S+=[Spacer(1,32*mm),
        Paragraph("VUESTRO LIBRO FINANCIERO",St("c0",fontSize=12,textColor=GREY,fontName="Helvetica-Bold")),
        Spacer(1,3*mm),
        Paragraph("Diagnóstico<br/>de Pareja",St("c1",fontSize=40,leading=44,fontName="Helvetica-Bold")),
        Spacer(1,5*mm),
        Table([[""]],colWidths=[60*mm],style=[("LINEBELOW",(0,0),(-1,-1),4,colors.HexColor("#FDD731"))]),
        Spacer(1,7*mm),
        Paragraph("Dos vidas, una economía. Dónde os sostenéis y dónde chocáis.",St("c2",fontSize=12,textColor=ACCDK)),
        Spacer(1,38*mm),
        Paragraph(f"Escrito para  <b>{cliA['nombre']}</b>  &amp;  <b>{cliB['nombre']}</b>",St("cn",fontSize=12)),
        Paragraph(cliA["fecha"],small),
        Spacer(1,3*mm), Paragraph("Edición de Pareja · Tier 3",St("ct",fontSize=9.5,textColor=colors.HexColor(A_COL),fontName="Helvetica-Bold")),
        Spacer(1,16*mm),
        Paragraph(f"DOCUMENTO CONFIDENCIAL · REF {rb.report_id(cliA['nombre']+cliB['nombre'],cliA['fecha'])} · USO PRIVADO",
                  St("cr",fontSize=7.5,textColor=GREY,fontName="Helvetica")),
        PageBreak()]
    # apertura
    S+=[Paragraph("Antes de empezar",h_sec),
        Paragraph(f"{nA} y {nB}: el dinero es una de las causas más citadas de ruptura en las parejas — y casi "
                  "nunca por cuánto hay, sino porque cada uno lo vive distinto y no se habla. La grieta no la abre "
                  "la falta de dinero: la abre la diferencia callada. Este libro pone esas diferencias sobre la "
                  "mesa, sin juicio, para que dejen de operar en silencio.",body),
        Paragraph("No mide quién lo hace mejor. Mide dónde estáis alineados (vuestra fuerza conjunta) y dónde "
                  "divergís (vuestros focos de fricción). Al final encontraréis un guion para hablarlo.",body),
        Paragraph("Leedlo juntos. Esa es la mitad del valor.",body),
        PageBreak()]
    S+=seccion_arquetipos(rA,rB,nA,nB)
    # compatibilidad + radar
    dAf=_fill(dA); dBf=_fill(dB)
    hogar={"gasto_mensual":dAf["gasto_mensual"]+dBf["gasto_mensual"],
           "ingreso_mensual":dAf["ingreso_mensual"]+dBf["ingreso_mensual"],
           "ahorro_mensual":dAf["ahorro_mensual"]+dBf["ahorro_mensual"],
           "patrimonio":dAf["patrimonio"]+dBf["patrimonio"],
           "edad":(dAf["edad"]+dBf["edad"])/2}
    fi_h=rb.fi_metrics(hogar)
    S+=[Paragraph("Vuestro mapa conjunto",h_sec),
        Table([[Paragraph(f"<font size=40 color='#1A1A17'><b>{compat}</b></font><font size=13 color='#6B7280'>/100</font>",body),
                Paragraph(f"<b>Compatibilidad financiera</b><br/><font size=8 color='#6B7280'>Cuanto más alto, más "
                          f"parecida es vuestra forma de vivir el dinero. No es bueno ni malo en sí: las diferencias "
                          f"bien habladas suman.</font>",body)]],
              colWidths=[42*mm,118*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
        Spacer(1,1*mm),
        Table([[Paragraph(f"<font color='{A_COL}'>●</font> {cliA['nombre']}: <b>{100-saludA:.0f}</b>/100",small),
                Paragraph(f"<font color='{B_COL}'>●</font> {cliB['nombre']}: <b>{100-saludB:.0f}</b>/100",small)]],
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
              ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))]
    rb.cashflow_waterfall(hogar,"_cashH.png")
    S+=[KeepTogether([Paragraph("Vuestro flujo de caja conjunto",h_sub),
        Image("_cashH.png",width=158*mm,height=74*mm,hAlign="CENTER"),
        Paragraph("De cada euro que entra en casa, esto es lo que se queda y lo que se va. Si la barra «sin asignar» "
                  "es grande, no es libertad: es dinero esperando una decisión que aún no habéis tomado juntos.",small)]),
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
        rows.append([Paragraph(f"{c} · {CAPAS[c]['nombre']}",small),Paragraph(f"{100-a:.0f}",small),
                     Paragraph(f"{100-b:.0f}",small),Paragraph(f"{g:.0f}",small),
                     rb.Chip(zona,zc,w=64,h=13)])
    S+=[tbl(rows,[78*mm,15*mm,15*mm,20*mm,32*mm]),PageBreak()]
    S+=seccion_dafo_pareja(pA,pB,nA,nB)
    S+=seccion_caminos_hogar(dA,dB)
    rb.radar_png(pA,"_radarA.png"); rb.radar_png(pB,"_radarB.png")
    try: _exA=sv.computar_extras(rA,_fill(dA),perfilA or {},_iv2)
    except Exception: _exA=None
    try: _exB=sv.computar_extras(rB,_fill(dB),perfilB or {},_iv2)
    except Exception: _exB=None
    S+=seccion_individual(cliA["nombre"] or nA,pA,trA,saludA,dA,"_radarA.png",fi_h,rA,extras=_exA)
    S+=seccion_individual(cliB["nombre"] or nB,pB,trB,saludB,dB,"_radarB.png",fi_h,rB,extras=_exB)
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
                Paragraph("Esta capa mide "+QMIDE_PAREJA.get(code, CAP_QMIDE[code]),body),
                Paragraph("Vuestros resultados",h_sub),
                Table([[Paragraph(f"<font color='{A_COL}'>●</font> {nA}: <b>{100-a:.0f}</b>/100",small),
                        Paragraph(f"<font color='{B_COL}'>●</font> {nB}: <b>{100-b:.0f}</b>/100",small)],
                       [Bar2(a,b,w=150*mm),""]],
                      colWidths=[80*mm,80*mm],style=[("SPAN",(0,1),(1,1)),("LEFTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,1),(0,1),4)]),
                Spacer(1,2*mm),
                Paragraph("Faceta por faceta",h_sub)]
        facs=CAPAS[code]["facetas"]
        for f in pA[code]["facetas"]:
            fa=pA[code]["facetas"].get(f,0); fb=pB[code]["facetas"].get(f,0)
            bloque.append(Table([[Paragraph("<b>%s</b>"%facs.get(f,f),small),Bar2(fa,fb,w=92),
                                  Paragraph(f"<font color='{A_COL}'>{100-fa:.0f}</font> / <font color='{B_COL}'>{100-fb:.0f}</font>",small)]],
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
                  "se convierte en discusión sin que sepáis por qué. Priorizamos las de vínculo y transparencia.",body),
        Paragraph("Cada una de estas diferencias, callada, erosiona; nombrada y entendida, se desactiva. No son "
                  "amenazas: son las conversaciones que aún no habéis tenido — y tenerlas es, justamente, la vacuna.",body)]
    S+=[Spacer(1,2*mm), rb._box([
        Paragraph("<b>Por qué el dinero rompe parejas</b>",St("mec0",fontSize=10.5,leading=14,fontName="Helvetica-Bold")),
        Paragraph("Casi nunca es una gran pelea. Es una diferencia pequeña que no se habla —cómo se gasta, cuánto se guarda, "
                  "qué da miedo— y que se repite cada mes en mil decisiones minúsculas. Cada vez, uno cede y el otro ni se "
                  "entera. Esa cesión callada se vuelve reproche; el reproche, distancia; y la distancia, «ya no hablamos de "
                  "dinero». El dinero no es la causa: es el escenario donde se representa todo lo demás. Por eso ponerlo en "
                  "palabras hoy vale más que cualquier cifra.",St("mec1",fontSize=9.7,leading=14,spaceBefore=2,textColor=INK))],
        "#FBF3E8","#B45309",ancho=160*mm), Spacer(1,3*mm)]
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
    # cruce semantico de pareja (sintesis IA de las abiertas)
    if sintesis and str(sintesis).strip():
        S+=[Paragraph("Análisis de asimetría y brecha de comunicación",h_sec),
            Paragraph("Esta lectura cruza lo que cada uno escribió en sus respuestas abiertas: dónde vuestros relatos "
                      "coinciden, dónde chocan, y qué revela eso de la conversación que tenéis pendiente.",small),
            Spacer(1,2*mm)]
        for _par in [x for x in str(sintesis).replace("\r","").split("\n") if x.strip()]:
            _e=_par.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            S.append(Paragraph(_e,body))
        S+=[PageBreak()]
    # guion de conversacion
    S+=[Paragraph("Vuestro guion de conversación",h_sec),
        Paragraph("Sentaos sin móviles, treinta minutos. Recorred estas preguntas por turnos: primero uno explica "
                  "su «por qué», luego el otro, sin interrumpir. El objetivo no es ganar, es entender.",body),
        rb._box([Paragraph("<b>Reglas de juego:</b> prohibidas las palabras «capricho», «controlar» y «ya lo veremos» "
                "(cierran la conversación del otro). Turnos de tres minutos sin interrumpir. Si el tono sube, se cierra "
                "el cuaderno y se retoma en 24 horas. No se decide nada con enfado.",St("rg",fontSize=9.8,leading=14))],
                "#FEF9E7","#B45309",ancho=158*mm),
        Spacer(1,3*mm)]
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
    S+=laboratorio_pareja(rA,rB,pA,pB,nA,nB,dA,dB,hogar,divs)
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
                  "Leer esta tabla juntos ya abre conversaciones. <font color=\'#B91C1C\'><b>En rojo</b></font>, "
                  "donde respondisteis en extremos opuestos (vuestros campos de minas); "
                  "<font color=\'#B45309\'>en \u00e1mbar</font>, divergencias moderadas; en blanco, donde est\u00e1is alineados.",body)]
    def _na(txt, na):
        return Paragraph("<font color='#B5B3A6'>N/A</font>", small) if na else Paragraph(txt, small)
    for capa in INST["capas"]:
        rows=[[Paragraph("<b>Pregunta</b>",small),Paragraph("<b>%s</b>"%nA,small),Paragraph("<b>%s</b>"%nB,small)]]
        bgs=[]; ri=1
        for it in capa["items"]:
            sa=sb=None; na_a=na_b=False
            if it["tipo"]=="escala":
                ia=rA.get(it["id"]); ib=rB.get(it["id"])
                if ia is not None: va=it["opciones"][ia]["texto"]; sa=it["opciones"][ia]["score"]
                else: va=""; na_a=True
                if ib is not None: vb=it["opciones"][ib]["texto"]; sb=it["opciones"][ib]["score"]
                else: vb=""; na_b=True
            else:
                ga=dA.get(NUM_MAP.get(it["id"],"")); va=str(ga) if ga is not None else ""; na_a=(ga is None)
                gb=dB.get(NUM_MAP.get(it["id"],"")); vb=str(gb) if gb is not None else ""; na_b=(gb is None)
            rows.append([Paragraph(it["texto"],small),_na(va,na_a),_na(vb,na_b)])
            if sa is not None and sb is not None:
                gap=abs(sa-sb)
                fill="#F6D7D7" if gap>=66 else ("#FBEEDB" if gap>=33 else None)
                if fill: bgs.append(("BACKGROUND",(0,ri),(-1,ri),colors.HexColor(fill)))
                if gap>=66: bgs.append(("FONTNAME",(0,ri),(0,ri),"Helvetica-Bold"))
            ri+=1
        t=Table(rows,colWidths=[86*mm,35*mm,35*mm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),LIGHT),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#FAF8EF")]),
            ("LINEBELOW",(0,0),(-1,0),0.6,LINE),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold")]+bgs))
        S+=[Paragraph("%s \u00b7 %s"%(capa["code"],capa["nombre"]),h_sub), t]
    doc=SimpleDocTemplate(out,pagesize=A4,topMargin=22*mm,bottomMargin=20*mm,leftMargin=22*mm,rightMargin=22*mm,
                          title="Vuestro Libro Financiero — ITAP")
    doc._cliente="%s & %s"%(nA,nB)
    if getattr(rb,"NumberedCanvas",None): doc.build(S,onFirstPage=rb.deco,onLaterPages=rb.deco,canvasmaker=rb.NumberedCanvas)
    else: doc.build(S,onFirstPage=rb.deco,onLaterPages=rb.deco)
    print("PDF PAREJA OK ->",out)

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
