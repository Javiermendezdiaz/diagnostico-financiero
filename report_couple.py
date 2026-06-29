# -*- coding: utf-8 -*-
"""ITAP — Libro de Pareja (Tier 3). Cruza dos perfiles y mapea el conflicto financiero."""
import json, statistics, gc
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
    plt.tight_layout(); fig.savefig(path,dpi=200,transparent=True); plt.close(fig); gc.collect()

def _resp_op(it, r):
    """(score, texto) de una respuesta de escala, sea indice unico o LISTA (multi-respuesta ACT_LAT).
    Devuelve None si no resoluble (sin seleccion, indices invalidos u otro tipo). Multi -> media de scores."""
    ops = it.get("opciones") or []
    try:
        if isinstance(r, bool):
            return None
        if isinstance(r, list):
            idxs = [i for i in r if isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(ops)]
            if not idxs:
                return None
            sc = sum(ops[i]["score"] for i in idxs) / len(idxs)
            tx = "; ".join(ops[i]["texto"] for i in idxs)
            return (sc, tx)
        if isinstance(r, int) and 0 <= r < len(ops):
            return (ops[r]["score"], ops[r]["texto"])
    except Exception:
        return None
    return None

def divergencias_item(rA,rB):
    out=[]
    for capa in INST["capas"]:
        for it in capa["items"]:
            if it["tipo"]!="escala": continue
            if it.get("atencion"): continue
            a,b=rA.get(it["id"]),rB.get(it["id"])
            if a is None or b is None: continue
            _ra=_resp_op(it,a); _rb=_resp_op(it,b)
            if _ra is None or _rb is None: continue   # multi-respuesta/indice no resoluble: se omite del cruce
            sa,ta=_ra; sb,tb=_rb
            vinc="VINCULO" in it.get("dimensiones","")
            if abs(sa-sb)>=66 or (vinc and abs(sa-sb)>=33):
                out.append({"capa":capa["code"],"texto":it["texto"],
                    "A":ta,"B":tb,
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
        return (f"{nm} es terreno firme para los dos ({rb._sal100(a)} y {rb._sal100(b)}). Es de vuestras fortalezas compartidas: "
                f"apoyaos aqu\u00ed cuando otras \u00e1reas aprieten.")
    if a>=51 and b>=51:
        return SOMBRA.get(code, f"{nm} os pesa a los dos a la vez: es un frente compartido, no un desencuentro. Atajadlo juntos, no esperéis a que el otro mejore.")
    if g>=30:
        return CHOQUE.get(code, "{debil} lo vive con más tensión que {fuerte}. Esa diferencia, hablada, se convierte en complemento; callada, en reproche silencioso.").format(fuerte=fuerte,debil=debil)
    return (f"{nm} est\u00e1 bastante equilibrado entre vosotros ({rb._sal100(a)} y {rb._sal100(b)}): diferencias peque\u00f1as que se "
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

def _gasto_hogar(dAf, dBf):
    """Gasto mensual REAL del hogar, neteando el solape de gastos compartidos.
    Cada miembro declara su gasto 'todo incluido', que suele incluir la MISMA bolsa
    comun (alquiler, luz, comida). Sumarlos sin mas duplicaria esa parte e inflaria el
    Numero de Libertad conjunto. Restamos como mucho UNA copia de la bolsa comun declarada
    (gastos_comunes), con suelo en el mayor componente para no quedarnos cortos."""
    gA = dAf.get("gasto_mensual") or 0
    gB = dBf.get("gasto_mensual") or 0
    gc = max((dAf.get("gastos_comunes") or 0), (dBf.get("gastos_comunes") or 0))
    neto = (gA + gB) - min(gc, gA, gB)   # netea a lo sumo una copia de la bolsa comun
    return max(neto, gA, gB, gc)         # nunca por debajo del mayor componente real

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

def seccion_acelerador_hogar(dA, dB, tmp="/tmp/_lp_"):
    a=_fill(dA); b=_fill(dB)
    ing=a["ingreso_mensual"]+b["ingreso_mensual"]; gas=_gasto_hogar(a,b)
    pat=a["patrimonio"]+b["patrimonio"]; num=(gas*12.0/0.04) if gas>0 else 0
    if ing<=0 or num<=0: return []
    try:
        import legado_design as LD
        img=LD.acelerador_tabla(tmp+"acelhog.png", ing, gas, pat, num, vos=True)
        return [rb.FullBleedImage(img), PageBreak()]
    except Exception:
        return []

def seccion_dinero_trabaja(dA, dB):
    a=_fill(dA); b=_fill(dB)
    ing=a["ingreso_mensual"]+b["ingreso_mensual"]
    pasivo=(a.get("renta_pasiva") or 0)+(b.get("renta_pasiva") or 0)
    if ing<=0: return []
    pasivo=min(pasivo,ing); activo=ing-pasivo
    ppa=round(activo/ing*100); ppp=100-ppa
    _totbar=154.0
    wA=_totbar*activo/ing; wP=_totbar*pasivo/ing
    wA=max(0.5,wA); wP=max(0.5,wP)
    if wA+wP>_totbar:                       # nunca exceder el ancho de pagina (evita ancho negativo -> crash)
        _f=_totbar/(wA+wP); wA*=_f; wP*=_f
    out=[PageBreak(), Paragraph("¿Trabajáis vosotros, o trabaja vuestro dinero?",h_sec),
         Paragraph("De cada euro que entra en casa: cuánto exige vuestro tiempo (trabajo activo) y cuánto trabaja sin vosotros "
                   "(rentas, dividendos, alquileres). Toda economía que aspira a la libertad busca lo mismo: que esa segunda barra crezca.",body),
         Spacer(1,6*mm),
         Table([[Paragraph(f"<font color='white'><b>{ppa}%</b></font>",small) if wA>16 else Paragraph("",small),
                 Paragraph(f"<font color='white'><b>{ppp}%</b></font>",small) if wP>14 else Paragraph("",small)]],
               colWidths=[wA*mm,wP*mm],rowHeights=[13*mm],
               style=[("BACKGROUND",(0,0),(0,0),colors.HexColor("#C65C4E")),("BACKGROUND",(1,0),(1,0),colors.HexColor("#E3B341")),
                      ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(0,0),(-1,-1),"CENTER"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]),
         Spacer(1,2*mm),
         Table([[Paragraph("<font color='#C65C4E'>●</font>  Depende de vuestro esfuerzo",small),
                 Paragraph("<font color='#E3B341'>●</font>  Trabaja sin vosotros",small)]],colWidths=[80*mm,80*mm],
               style=[("LEFTPADDING",(0,0),(-1,-1),0)]),
         Spacer(1,5*mm),
         Paragraph((f"Hoy <b>{ppa}%</b> de lo que entra depende de que sigáis trabajando. La libertad financiera llega "
                    f"cuando la barra dorada sostiene vuestra vida sin que tengáis que estar — ese es el objetivo conjunto.") if ppp<50 else
                   (f"Ya <b>{ppp}%</b> de vuestros ingresos trabaja sin vosotros: vais por el buen camino hacia que el dinero "
                    f"os mantenga a vosotros, y no al revés."), body),
         PageBreak()]
    return out

def seccion_caminos_hogar(dA, dB):
    a=_fill(dA); b=_fill(dB)
    hog={"edad":int(round((a["edad"]+b["edad"])/2)),
         "patrimonio":a["patrimonio"]+b["patrimonio"],
         "ahorro_mensual":a["ahorro_mensual"]+b["ahorro_mensual"],
         "ingreso_mensual":a["ingreso_mensual"]+b["ingreso_mensual"],
         "gasto_mensual":_gasto_hogar(a,b),
         "inversiones_liquidas":(a.get("inversiones_liquidas") or 0)+(b.get("inversiones_liquidas") or 0),
         "colchon_liquido":(a.get("colchon_liquido") or 0)+(b.get("colchon_liquido") or 0),
         "rentabilidad_actual":max(a.get("rentabilidad_actual") or 0, b.get("rentabilidad_actual") or 0)}
    try:
        f65,mid65,m65,medad,modo=rb.proyeccion_chart(hog,"_proyhogar.png",titulo_override="Tres caminos para vuestro patrimonio (sobre vuestra liquidez invertible)")
    except Exception:
        return []
    out=[]
    try:
        rb.panel_proyeccion("_proyhogarpanel.png", hog,
            titulo="EL MAPA DE VUESTRO FUTURO",
            subtitulo="Tres caminos parten del mismo punto. La distancia la decidís vosotros, cada mes.",
            brecha_cap="Lo que separa actuar de no hacerlo, juntos, a los %d años.")
        out += [PageBreak(), rb.FullBleedImage("_proyhogarpanel.png")]
    except Exception:
        pass
    out += [PageBreak(), Paragraph("Vuestros tres caminos",h_sec),
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
    out=[]
    try:
        _ac,_,_=rb.arquetipo(resp or {})
        rb.panel_persona(radar_path+".hero.png", pn, salud, _ac, prof)
        out += [rb.FullBleedImage(radar_path+".hero.png"), PageBreak()]
    except Exception:
        pass
    out += [Paragraph("PERFIL INDIVIDUAL",kick), Paragraph(nombre,h_sec),
         Paragraph(f"Antes de cruzaros, esta es la foto psicol\u00f3gica de {pn}: c\u00f3mo vive el dinero por dentro. Las cifras del hogar son comunes (las ver\u00e9is juntas); lo que cambia de uno a otro es la percepci\u00f3n, el miedo y la prioridad.",body),
         Image(radar_path,width=112*mm,height=112*mm,hAlign="CENTER"),
         Paragraph(f"<b>{rb._sal100(salud)}</b>/100 \u2014 salud psicofinanciera global de {pn} (100 = \u00f3ptimo).",body)]
    coh=rb.coherencia(salud, rb.fi_metrics(_fill(datos)), _fill(datos))
    if coh:
        out+=[Spacer(1,3*mm), _callout(coh[0], coh[1], "#1A1A17", "#FBF6E0")]
    est=_compartimento(prof, resp or {})
    if est:
        out+=[Spacer(1,3*mm), _callout(est[0], est[1], "#B45309", "#FBF3E8")]
    try:
        _dialp = radar_path + ".dials.png"
        rb.panel_capas(_dialp, prof, titulo=("%s · SUS 12 DIMENSIONES" % pn).upper(),
                       subtitulo="Cómo vive %s cada palanca del dinero. El verde sostiene; el rojo pide acción." % pn)
        out += [PageBreak(), rb.FullBleedImage(_dialp)]
    except Exception:
        pass
    out+=[PageBreak(), Paragraph(f"{pn}: fortalezas y focos",h_sub)]
    orden=sorted(rb.CAPAS,key=lambda c:prof[c]["score"])
    out.append(Paragraph("<b>Tus tres fortalezas</b>",small))
    for c in orden[:3]:
        out.append(Paragraph(f"&#8226;  <b>{rb.CAPAS[c]['nombre']}</b> ({rb._sal100(prof[c]['score'])}/100). {rb.OPORTUNIDAD[c]}",St("if1",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
    out.append(Paragraph("<b>Tus tres focos</b>",small))
    for c in orden[-3:][::-1]:
        out.append(Paragraph(f"&#8226;  <b>{rb.CAPAS[c]['nombre']}</b> ({rb._sal100(prof[c]['score'])}/100). {rb.RIESGO[c]}",St("if2",fontSize=10,leading=14,leftIndent=6,spaceAfter=4)))
    out.append(Paragraph(f"{pn}: patrones transversales",h_sub))
    # PSIQUE -> Termometro de Estres ; LIQUIDEZ -> Indice de Vulnerabilidad: gauge velocimetro
    # (mismo patron y failsafe que el libro individual). VINCULO se queda en barra.
    _GLBL={"PSIQUE":"Termometro de estres","LIQUIDEZ":"Indice de vulnerabilidad"}
    _ptok="".join(ch for ch in str(pn).lower() if ch.isalnum())[:8] or "x"
    for t in ("PSIQUE","LIQUIDEZ","VINCULO"):
        v=trans[t]; vt=("%s"%rb._sal100(v)) if v is not None else "\u2014"
        _viz=None
        if t in _GLBL and v is not None:
            try:
                _gp="_gauge_par_%s_%s.png"%(_ptok,t.lower())
                rb.gauge_png(v,_GLBL[t],_gp)
                _viz=Image(_gp,width=66*mm,height=45*mm,hAlign="CENTER")
            except Exception as _eg:
                import sys; sys.stderr.write("[gauge-par] %s cae a barra: %s\n"%(t,_eg)); _viz=None
        if _viz is None:
            _viz=Table([[Paragraph(f"<b>{t.capitalize()}</b>  {vt}/100",small),rb.Bar(v or 0,w=110*mm)]],
                         colWidths=[42*mm,114*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),5)])
        out.append(_viz)
    out.append(Paragraph(f"{pn}: lo que revelan tus respuestas",h_sub))
    for ti,tx in rb.insights(prof,trans,fi_hogar):
        out.append(Paragraph(f"<font color='#1A1A17'>&#8226;</font>  <b>{ti}</b>",small))
        out.append(Paragraph(tx,St("ii",fontSize=9.6,leading=13,leftIndent=10,spaceAfter=6)))
    if extras:
        try: out += rb.seccion_ratio_vida(extras) + rb.seccion_nudo(extras) + rb.seccion_coste_inaccion(extras)
        except Exception: pass
        # --- Matiz colchón social ante pérdida de empleo (solo si el perfil tiene derecho) ---
        try:
            _res=(extras or {}).get("resiliencia") or {}
            _cs=_res.get("colchon_social") if isinstance(_res,dict) else None
            _mlp=_res.get("meses_liquido_paro"); _mliq=_res.get("meses_liquido")
            if _cs and _cs.get("aplica") and _mlp is not None and _mliq is not None:
                if _cs.get("perfil")=="empleado":
                    _tcs=(f"<b>Sobre tu resistencia si perdieras el empleo:</b> este número ya contempla un colchón social "
                          f"estimado. La prestación por desempleo (la asumimos prudente en ~60% de tu ingreso durante un máximo "
                          f"de ~12 meses) y el finiquito amortiguan la caída antes de tocar tu ahorro: con ese colchón tu liquidez "
                          f"individual aguantaría del orden de <b>{_mlp:g} meses</b> en vez de {_mliq:g}. Es una estimación "
                          f"conservadora; aun así, en un hogar lo que de verdad cuenta es que no falléis los dos a la vez.")
                else:
                    _tcs=(f"<b>Sobre tu resistencia si perdieras tu actividad:</b> como autónomo o empresario tu red es mucho más "
                          f"fina que la de un asalariado. Modelamos un amortiguador prudente (~40% durante hasta ~4 meses) que "
                          f"estira tu liquidez de {_mliq:g} a unos <b>{_mlp:g} meses</b>. No es una prestación garantizada: tu "
                          f"mejor seguro sigue siendo el colchón del hogar.")
                out += [Spacer(1,3*mm), _callout("Colchón social estimado", _tcs, "#2C5C8A", "#EEF2F8")]
        except Exception: pass
    out.append(PageBreak())
    out.append(Paragraph(f"{pn}: tus doce capas, una a una",h_sub))
    out.append(Paragraph("Tu lectura individual, capa por capa — las que más te pesan, primero. El cruce con tu pareja viene después.",small))
    _facmap=rb.CAPAS
    for _c in sorted(rb.CAPAS,key=lambda c:prof[c]["score"],reverse=True):
        _sc=prof[_c]["score"]
        _ps=rb.PASO[_c]; _ps=_ps[0] if isinstance(_ps,(list,tuple)) else _ps
        _blk=[Table([[Paragraph("<b>%s</b>  <font color='#6B7280'>%.0f/100</font>"%(rb.CAPAS[_c]["nombre"],rb._sal100(_sc)),small),
                      rb.Chip(prof[_c]["banda"],BANDC[prof[_c]["bi"]],w=84,h=13)]],
                     colWidths=[118*mm,40*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(0,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),3)]),
              Paragraph("<b>Qué mide en ti:</b> "+rb.QMIDE[_c],St("dxq",fontSize=9.4,leading=13,leftIndent=4))]
        _fr=(extras or {}).get("frases",{}).get(_c) if extras else None
        if _fr:
            _blk.append(rb._box([Paragraph("<b>Tu caso, en números:</b> "+_fr,St("dxtcn",fontSize=9.2,leading=12.5,textColor=INK))],"#FBF4E4","#B45309",ancho=160*mm))
        _facd=(_facmap[_c].get("facetas",{}) if isinstance(_facmap[_c],dict) else {})
        _fr=[]
        for _fk,_fv in prof[_c]["facetas"].items():
            _fr.append([Paragraph(_facd.get(_fk,_fk),St("dxfl",fontSize=8.4,leading=11)),
                        rb.Bar(_fv,w=66*mm),
                        Paragraph("<font color='#6B7280'>%.0f</font>"%(rb._sal100(_fv)),St("dxfn",fontSize=8.4,leading=11))])
        if _fr:
            _blk.append(Table(_fr,colWidths=[58*mm,72*mm,12*mm],
                              style=[("LEFTPADDING",(0,0),(0,-1),8),("LEFTPADDING",(1,0),(-1,-1),5),
                                     ("BOTTOMPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),2),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
        if _sc>=50:
            _blk.append(Paragraph("<font color='#9A3B2E'><b>Tu foco:</b></font> "+rb.RIESGO[_c],St("dxr",fontSize=9.4,leading=13,leftIndent=4)))
            _blk.append(Paragraph("<font color='%s'><b>Tu paso:</b></font> "%A_COL+_ps,St("dxp",fontSize=9.4,leading=13,leftIndent=4)))
        else:
            _blk.append(Paragraph("<font color='#1D6F42'><b>Tu fortaleza:</b></font> "+rb.OPORTUNIDAD[_c],St("dxo",fontSize=9.4,leading=13,leftIndent=4)))
        _blk.append(Paragraph("<i>Para pensar:</i> "+rb.REFLEX[_c],St("dxrf",fontSize=8.9,leading=12,leftIndent=4,textColor=INK)))
        _blk.append(Paragraph("“%s”"%rb.PRINCIPIO[_c],St("dxpr",fontSize=9,leading=12,leftIndent=4,textColor=GREY,fontName="Helvetica-Oblique",spaceAfter=8)))
        out.append(KeepTogether(_blk))
    out.append(PageBreak())
    out.append(Paragraph(f"{pn}: resumen capa por capa",h_sub))
    rows=[[Paragraph("<b>Capa</b>",small),Paragraph("<b>Score</b>",small),Paragraph("<b>Banda</b>",small)]]
    for c in rb.CAPAS:
        rows.append([Paragraph(rb.CAPAS[c]["nombre"],small),Paragraph("%.0f"%(rb._sal100(prof[c]["score"])),small),
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
    try:
        rb.cierre_cta("_cierre_par.png", "VUESTRO\nSIGUIENTE PASO",
                      "Este libro es vuestro mapa. Adapta Family Office es quien lo recorre con vosotros, juntos o por separado.",
                      ["Una conversación inicial, sin compromiso, los dos.",
                       "Visión integral del patrimonio del hogar: sin productos propios ni conflictos.",
                       "Os escuchamos primero, os proponemos después. Sin llamadas de presión."],
                      "adaptafamilyoffice.com    ·    WhatsApp +34 683 34 35 31    ·    info@adaptafamilyoffice.com")
        out += [PageBreak(), rb.FullBleedImage("_cierre_par.png")]
    except Exception:
        pass
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

# ---------------------------------------------------------------------------
# Enriquecimiento Tier 3: día a día, trampa y micro-acuerdo por capa (voz pareja)
# ---------------------------------------------------------------------------
DIADIA={
 "C1":"En las noches en que uno no duerme por una factura y el otro ni se entera; en el silencio tenso cuando llega un cargo inesperado.",
 "C2":"Cuando habláis del futuro y cada uno imagina una jubilación distinta, sin una fecha ni una cifra común sobre la mesa.",
 "C3":"En el nivel de alarma —muy distinto— con que cada uno reacciona ante un imprevisto de mil euros.",
 "C4":"En esa sensación de que el dinero entra pero no se sabe a dónde va, y en las pequeñas compras que uno justifica y el otro no entiende.",
 "C5":"En todo lo que dais por hecho que «ya está resuelto» sin haberlo hablado: seguros, testamento, accesos a las cuentas.",
 "C6":"En las cenas, la ropa, el coche o el viaje que para uno son normales y para el otro un exceso.",
 "C7":"En la calma o el vértigo con que cada uno vive el depender de un solo sueldo.",
 "C8":"En cómo reaccionaría cada uno si mañana llegara una crisis — o una gran oportunidad.",
 "C9":"En quién mira las cuentas y quién no; en ese reparto invisible de la «fontanería» del dinero.",
 "C10":"En cómo pesa la deuda sobre el ánimo de cada uno, aunque sea exactamente la misma deuda.",
 "C11":"En quién propone mover el dinero y poner segundas fuentes en marcha, y quién prefiere no tocar nada.",
 "C12":"En la inversión que uno ve como crecimiento y el otro como riesgo; en el ahorro parado que uno quiere mover y el otro dejar quieto.",
}
TRAMPA={
 "C1":"Que el que más se preocupa cargue solo con la alerta de toda la casa. El estrés no hablado no protege: solo desgasta a uno de los dos.",
 "C2":"Posponer fijar el número común «hasta que tengamos más». Sin meta, cualquier cantidad parece insuficiente y nunca llega el momento.",
 "C3":"Confundir tener ingresos con tener red. Sin colchón, hasta un buen sueldo se evapora al primer golpe.",
 "C4":"Dejar que cada subida de ingreso se convierta en gasto fijo. Lo que sube callado, no baja.",
 "C5":"Aplazar el blindaje legal «porque da mal rollo». El día que hace falta, ya no se puede improvisar.",
 "C6":"Discutir la compra concreta en vez del significado que hay detrás. La cena nunca es el problema.",
 "C7":"Sentirse seguro porque hoy el sueldo llega. La dependencia de una sola fuente solo se ve cuando ya ha fallado.",
 "C8":"Paralizarse esperando el momento perfecto. En una crisis, no decidir también es una decisión — la peor.",
 "C9":"Que uno lleve las cuentas en la cabeza y el otro las ignore. Lo que nadie mira, lo decide la inercia.",
 "C10":"Esconder o minimizar una deuda «para no preocupar». El secreto acaba costando más que los propios intereses.",
 "C11":"Esperar a «tener tiempo» para poner el dinero a trabajar. El tiempo no aparece; se reserva.",
 "C12":"Dejar el ahorro parado «hasta decidir». La indecisión también es una decisión: la de perder contra la inflación.",
}
MICROACUERDO={
 "C1":"Una vez por semana, cinco minutos: cada uno dice en voz alta su mayor preocupación de dinero. Solo escuchar, sin resolver.",
 "C2":"Acordad esta semana UN número de libertad común y la edad a la que lo queréis. Escribidlo y ponedlo donde lo veáis.",
 "C3":"Fijad el tamaño del colchón del hogar (3-6 meses de gastos) y quién aporta cuánto cada mes.",
 "C4":"Elegid juntos un gasto fijo que ninguno defendería ante el otro y dadlo de baja este mes.",
 "C5":"Reservad una tarde para responder: si faltara uno, ¿el otro tiene accesos, liquidez y un testamento? Apuntad qué falta.",
 "C6":"Daos cada uno una «caja de autonomía» mensual sin explicaciones; fuera de ella, las decisiones son de los dos.",
 "C7":"Calculad qué % del hogar depende de un solo ingreso y nombrad una segunda fuente posible a explorar.",
 "C8":"Escribid en un folio qué haríais juntos si mañana llegara una crisis — y qué, si llegara una oportunidad.",
 "C9":"Montad un presupuesto de tres cajas y poned una cita fija mensual de 20 min para revisarlo los dos.",
 "C10":"Poned toda la deuda sobre la mesa, sin secretos, con su TAE, y haced un único plan de amortización.",
 "C11":"Elegid UNA palanca de crecimiento para este año y repartíos por escrito quién la lidera.",
 "C12":"Decidid un % fijo del ahorro que se invierte automáticamente cada mes, pactado entre los dos.",
}

def seccion_constitucion_hogar(pA,pB,nA,nB,hogar,fi_h,divs):
    """Plan conjunto 72h/30/90 + cifras del hogar + contingencia + pacto firmado."""
    comb=sorted(CAPAS,key=lambda c:(pA[c]["score"]+pB[c]["score"]),reverse=True)
    confl=sorted([c for c in CAPAS if abs(pA[c]["score"]-pB[c]["score"])>=30],
                 key=lambda c:-abs(pA[c]["score"]-pB[c]["score"]))
    pasos=[]; seen=set()
    for c in confl+comb:
        if c in seen: continue
        p=paso_pareja(c)
        if p: pasos.append(p); seen.add(c)
        if len(pasos)>=5: break
    def _p(i): return pasos[i] if i<len(pasos) else None
    out=[PageBreak(), Paragraph("Vuestra Constitución del Hogar",h_sec),
         Paragraph("Esto no es una lista de buenos propósitos: es la ley por la que se regirán vuestras decisiones de "
                   "dinero a partir de hoy. Está construida desde donde más flojeáis juntos y donde más divergís. "
                   "Empezad por arriba — el orden importa.",body),
         Spacer(1,3*mm)]
    fases=[("#0F766E","Fase 1 · Próximas 72 horas","Cortafuegos: parar la fuga y el silencio",[_p(0),_p(1)]),
           ("#B45309","Fase 2 · Días 4-30","Estructura: montar el sistema del hogar",[_p(2),_p(3)]),
           ("#0284C7","Fase 3 · Días 31-90","Construir: poner el patrimonio a trabajar",
            [_p(4),"Repetid el diagnóstico por separado y comparad: veréis cuánto se han acortado vuestras distancias."])]
    rt=[]
    for col,fase,lema,accs in fases:
        rt.append([Paragraph(f"<font color='white'><b>{fase}</b>  ·  {lema}</font>",
                   St("rf",fontSize=9.5,leading=12,textColor=colors.white)),""])
        for a in accs:
            if a: rt.append([Paragraph(a,St("ra",fontSize=9.6,leading=13)),""])
    rtab=Table(rt,colWidths=[148*mm,12*mm])
    sty=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
         ("LEFTPADDING",(0,0),(-1,-1),9),("LINEBELOW",(0,0),(-1,-1),0.4,LINE)]
    ri=0
    for col,fase,lema,accs in fases:
        sty.append(("BACKGROUND",(0,ri),(-1,ri),colors.HexColor(col))); sty.append(("SPAN",(0,ri),(0,ri)))
        for a in accs:
            if a: ri+=1; sty.append(("BOX",(1,ri),(1,ri),0.8,colors.HexColor("#9CA3AF")))
        ri+=1
    rtab.setStyle(TableStyle(sty))
    out+=[rtab, Spacer(1,5*mm)]
    gm=hogar.get("gasto_mensual") or 0; pat=hogar.get("patrimonio") or 0
    colobj=round(gm*3) if gm else 0
    cif=[]
    if colobj:
        cif.append("<b>Vuestro colchón objetivo: %s</b> (3 meses de gastos del hogar). Abridlo en una cuenta remunerada aparte y "
                   "alimentadlo con una transferencia automática el día 1, repartida entre los dos." % rb._eur(colobj))
    if pat and colobj and pat>colobj:
        cif.append("Dividid vuestro patrimonio: <b>%s</b> congelados como fondo intocable de la pareja y <b>%s</b> como base "
                   "para invertir o amortizar, con mando compartido." % (rb._eur(colobj),rb._eur(pat-colobj)))
    cif.append("Pagaos primero, como hogar: el día 1, antes de gastar, sale el ahorro conjunto a una cuenta separada. "
               "Ahorrar lo que sobra no funciona; forzar el reparto, sí.")
    cp=[Paragraph("<b>Vuestro plan, en cifras</b>",St("cif0",fontSize=11,leading=15,textColor=ACCDK,fontName="Helvetica-Bold"))]
    for x in cif: cp.append(Paragraph("<font color='#B45309'>&#9656;</font>  "+x,St("cifx",fontSize=9.8,leading=14,textColor=INK,leftIndent=4,spaceBefore=3)))
    out+=[rb._box(cp,"#FBF4E4","#B45309",ancho=160*mm), Spacer(1,4*mm)]
    col6=gm*6
    out+=[rb._box([Paragraph("<font color='#B45309'><b>Vuestra regla de contingencia</b></font><br/>"
            f"<font size=9.5>Todo plan necesita un freno de emergencia. El vuestro: si el fondo líquido del hogar baja de "
            f"<b>{rb._eur(col6)}</b> (seis meses de gastos) o llega un imprevisto grande, <b>pausad las fases 2 y 3</b> y "
            f"volcad todo el excedente a reconstruir el colchón antes de seguir. Proteger la base va siempre primero.</font>",
            St("kc",fontSize=10.5,leading=15))],"#FBF4E4","#B45309",ancho=160*mm), Spacer(1,4*mm),
          Paragraph("Vuestro pacto",h_sub),
          rb._box([Paragraph(f"<b>{nA} y {nB} nos comprometemos</b>, antes de 30 días, a dar juntos el primer paso de la Fase 1 "
                f"y a reservar una cita mensual de 20 minutos para revisar las cuentas del hogar. Firmamos:",
                St("pac",fontSize=10.5,leading=15)),
                Spacer(1,8*mm),
                Table([["Firma "+nA,"Firma "+nB]],colWidths=[78*mm,78*mm],
                  style=TableStyle([("LINEABOVE",(0,0),(-1,0),0.6,colors.HexColor("#9CA3AF")),
                    ("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#9CA3AF")),("FONTSIZE",(0,0),(-1,0),8),
                    ("TOPPADDING",(0,0),(-1,0),3)]))],"#FBF6E0","#1A1A17",ancho=160*mm),
          PageBreak()]
    return out

def seccion_coste_no_hablarlo(pA,pB,nA,nB,hogar,fi_h,divs):
    """Coste de inacción conjunto: en dinero y en relación, + matriz dos caminos."""
    pat=float(hogar.get("patrimonio") or 0)
    inv=float(hogar.get("inversiones_liquidas") or 0)+float(hogar.get("colchon_liquido") or 0)
    dormido=max(0.0,pat-inv)
    nconf=len([c for c in CAPAS if abs(pA[c]["score"]-pB[c]["score"])>=30])
    nfric=len(divs)
    out=[PageBreak(), Paragraph("El coste de no hablarlo",h_sec),
         Paragraph("Una conversación que no ocurre también tiene precio. No aparece en ninguna cuenta, pero lo pagáis "
                   "—en dinero parado, en decisiones aplazadas y en distancia que se acumula mes a mes.",body)]
    fin=[]
    if dormido>20000:
        fin.append("<b>%s</b> de vuestro patrimonio está hoy parado o ilíquido, sin generar renta. Cada año que sigue "
                   "dormido es rentabilidad que no vuelve." % rb._eur(dormido))
    if fi_h and fi_h[1] is not None and fi_h[1]<100:
        fin.append("Estáis al <b>%.0f%%</b> de vuestro número de libertad. Sin un plan común, ese porcentaje se mueve "
                   "despacio — o no se mueve." % fi_h[1])
    if fin:
        cp=[Paragraph("<b>Lo que cuesta en dinero</b>",St("cn0",fontSize=10.5,leading=14,fontName="Helvetica-Bold"))]
        for x in fin: cp.append(Paragraph("<font color='#9A3B2E'>&#9656;</font>  "+x,St("cnx",fontSize=9.8,leading=14,leftIndent=4,spaceBefore=3)))
        out+=[rb._box(cp,"#FBECE8","#9A3B2E",ancho=160*mm), Spacer(1,3*mm)]
    if nconf or nfric:
        rel=("Tenéis <b>%d</b> %s de conflicto y <b>%d</b> %s de fricción concretos sin resolver. Cada uno, callado, "
             "se repite en decenas de pequeñas decisiones al mes y se convierte, con el tiempo, en reproche. "
             "Hablados, se desactivan." % (nconf,"zona" if nconf==1 else "zonas",nfric,"punto" if nfric==1 else "puntos"))
        out+=[rb._box([Paragraph("<b>Lo que cuesta en la relación</b>",St("cr0",fontSize=10.5,leading=14,fontName="Helvetica-Bold")),
                       Paragraph(rel,St("cr1",fontSize=9.8,leading=14,spaceBefore=2))],"#FBF3E8","#B45309",ancho=160*mm),
              Spacer(1,4*mm)]
    out+=[PageBreak()]   # matriz "Dos caminos desde aqui" eliminada (redundante con "Vuestros tres caminos")
    return out

def seccion_hoja_ruta_12m(pA,pB,nA,nB,hogar):
    """Hoja de ruta trimestral a 12 meses del hogar."""
    q=[("T1 · Meses 1-3","Cimientos","Colchón del hogar completo y un único plan de deuda sobre la mesa."),
       ("T2 · Meses 4-6","Sistema","Presupuesto de tres cajas funcionando y caja de autonomía para cada uno."),
       ("T3 · Meses 7-9","Crecer","Primera palanca de crecimiento en marcha: una segunda fuente o el ahorro ya invertido."),
       ("T4 · Meses 10-12","Blindar","Blindaje legal resuelto y revisión conjunta: repetir el diagnóstico y medir el avance.")]
    out=[PageBreak(), Paragraph("Vuestra hoja de ruta a 12 meses",h_sec),
         Paragraph("El plan de 90 días, estirado a un año. No para hacerlo todo ya, sino para saber siempre cuál es el "
                   "siguiente paso del hogar.",body),Spacer(1,3*mm)]
    try:
        _ph=sv.plan_hogar(hogar)
    except Exception:
        _ph=[]
    if _ph:
        out.append(Paragraph("Vuestros tres movimientos prioritarios",h_sub))
        for mv in _ph:
            _es="VUESTRO PRIMER MOVIMIENTO" if mv["orden"]==1 else ("MOVIMIENTO %d"%mv["orden"])
            _pc="#B45309" if mv["orden"]==1 else "#6B7280"
            _pbg="#FBF4E4" if mv["orden"]==1 else "#F6F4EC"
            _pin=[Paragraph("<font color='%s'><b>%s</b></font>  &#183;  <b>%s</b>"%(_pc,_es,mv["titulo"]),St("ph0",fontSize=11.3,leading=15,textColor=INK)),
                  Paragraph("<b>Por qué:</b> "+mv["porque"],St("ph1",fontSize=9.6,leading=13.5,textColor=INK,spaceBefore=3)),
                  Paragraph("<font color='%s'><b>&#9656; Esta semana:</b></font> %s"%(_pc,mv["accion"]),St("ph2",fontSize=9.6,leading=13.5,textColor=INK,spaceBefore=2)),
                  Paragraph("<b>En 12 meses ganáis:</b> <i>%s</i>"%mv["gana"],St("ph3",fontSize=9.4,leading=13,textColor=GREY,spaceBefore=2))]
            out.append(rb._box(_pin,_pbg,_pc,ancho=160*mm)); out.append(Spacer(1,3*mm))
        out.append(Paragraph("Haced el primero hasta tenerlo en marcha — juntos. Una palanca movida vale más que diez planeadas.",St("phf",fontSize=9.4,leading=13,textColor=GREY,fontName="Helvetica-Oblique",spaceAfter=4)))
    rows=[]
    for tit,lema,desc in q:
        rows.append([Paragraph(f"<font color='#1A1A17'><b>{tit}</b></font><br/><font color='{A_COL}' size=8><b>{lema.upper()}</b></font>",small),
                     Paragraph(desc,small)])
    out+=[Table(rows,colWidths=[46*mm,114*mm],style=TableStyle([("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LEFTPADDING",(0,0),(-1,-1),8),("BACKGROUND",(0,0),(0,-1),LIGHT)])),PageBreak()]
    return out

def mapa_relacion(path, capas, compat, nA, nB):
    from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
    BG="#0E1018"; PANEL="#161A24"; GOLD="#E8C861"; TXC="#F4F1E8"; GRC="#8A93A6"; GREEN="#2FB36B"; RED="#D8674F"; AMB="#E0A93B"; BLUE="#5B8DEF"
    fig=plt.figure(figsize=(8.27,11.69),dpi=200); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.axis("off"); ax.set_xlim(0,100); ax.set_ylim(0,141.6)
    def T(x,y,ss,sz,c=TXC,w="normal",ha="left"): ax.text(x,y,ss,fontsize=sz,color=c,ha=ha,fontweight=w,family="DejaVu Sans",zorder=6)
    def bx(x,y,w,h,fc,r=1.4,ec=None,lw=0): ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0,rounding_size=%s"%r,fc=fc,ec=ec or fc,lw=lw,zorder=2))
    ax.add_patch(Rectangle((0,128),100,13.6,fc="#141A28",zorder=1))
    T(8,134,"ADAPTA",13,GOLD,"bold"); T(24.2,134.2,"FAMILY OFFICE",7,GRC)
    ax.plot([8,92],[131.4,131.4],color="#262C3A",lw=1,zorder=3)
    T(8,123,"EL MAPA DE VUESTRA RELACIÓN CON EL DINERO",9.5,GOLD,"bold")
    T(8,116.8,"Dónde os encontráis y dónde chocáis",18,TXC,"bold")
    bx(8,108,26,5.6,PANEL,1.4); T(10.5,109.9,"COMPATIBILIDAD",6.6,GRC,"bold"); T(31.5,109.4,"%d/100"%compat,12,GOLD,"bold",ha="right")
    ax.add_patch(Circle((40,110.8),0.9,color=GOLD,zorder=6)); T(42,110.2,(nA or "")[:14],8,TXC,"bold")
    ax.add_patch(Circle((54,110.8),0.9,color=BLUE,zorder=6)); T(56,110.2,(nB or "")[:14],8,TXC,"bold")
    T(73,110.2,"línea corta = alineados",7,GRC)
    x0,x1=40,90; n=len(capas); top=103; bot=33; step=(top-bot)/max(1,n-1)
    def mx(v): return x0+(x1-x0)*max(0,min(100,v))/100.0
    for i,(nm,a,b) in enumerate(capas):
        va,vb=100-a,100-b; g=abs(va-vb); y=top-i*step
        col=RED if g>=30 else (AMB if g>=18 else GREEN)
        ax.plot([x0,x1],[y,y],color="#1E2430",lw=0.8,zorder=2)
        ax.plot([mx(va),mx(vb)],[y,y],color=col,lw=2.6,zorder=4,solid_capstyle="round")
        ax.add_patch(Circle((mx(va),y),0.95,color=GOLD,ec="#0E1018",lw=0.8,zorder=5))
        ax.add_patch(Circle((mx(vb),y),0.95,color=BLUE,ec="#0E1018",lw=0.8,zorder=5))
        T(8,y-0.9,(nm or "")[:22],7.6,(TXC if g<30 else "#F2C9BE"),("bold" if g>=30 else "normal"))
    fuerte=sorted(capas,key=lambda t:-(((100-t[1])+(100-t[2]))/2))[0]
    fric=sorted(capas,key=lambda t:-abs(t[1]-t[2]))[0]
    bx(8,20,40,8.2,"#1C2433",1.6,ec=RED,lw=1.1); T(11,25.4,"VUESTRA MAYOR FRICCIÓN",6.6,RED,"bold"); T(11,22,(fric[0] or "")[:26],9.5,TXC,"bold")
    bx(52,20,40,8.2,"#16241C",1.6,ec=GREEN,lw=1.1); T(55,25.4,"VUESTRA MAYOR FUERZA",6.6,GREEN,"bold"); T(55,22,(fuerte[0] or "")[:26],9.5,TXC,"bold")
    T(8,14,"Cada línea es una conversación pendiente. Las rojas, las que más os cuesta tener — y las que más os unen al tenerlas.",7,GRC)
    ax.plot([8,92],[6.5,6.5],color="#262C3A",lw=1)
    T(8,4,"DOCUMENTO CONFIDENCIAL · ADAPTA FAMILY OFFICE",6.2,GRC)
    fig.savefig(path,dpi=200,facecolor=BG); plt.close(fig); gc.collect()

def seccion_sociedad_conyugal(hogar, nA, nB):
    """El Tercer Actor Financiero: la pareja como UNA entidad económica con patrimonio consolidado.
    Solo cifra real (patrimonio conjunto); el resto, afirmaciones cualitativas defendibles."""
    pat = float((hogar or {}).get("patrimonio") or 0)
    if pat <= 0:
        return []
    out = [Paragraph("La sociedad conyugal", h_sec),
           Paragraph("Hasta aquí os hemos leído como dos personas. Pero hay una tercera que también decide, "
                     "aunque no aparezca en ninguna cuenta a su nombre.", body),
           rb._box([
                Paragraph("<b>Vuestro tercer actor económico</b>", St("scy0", fontSize=11, leading=15, textColor=ACCDK, fontName="Helvetica-Bold")),
                Paragraph("Más allá de vuestras cuentas individuales existe una tercera entidad: <b>vuestra sociedad "
                          "conyugal</b>. No es la suma de %s más %s — es un único patrimonio con criterio común. Hoy "
                          "asciende a <b>%s</b>." % (nA, nB, rb._eur(pat)),
                          St("scy1", fontSize=10, leading=14.5, textColor=INK, spaceBefore=4)),
                Paragraph("La banca privada y las mejores oportunidades de inversión no negocian con dos carteras "
                          "pequeñas y dispersas, sino con un patrimonio unificado que sabe lo que quiere. Ahí es donde "
                          "una pareja alineada gana una capacidad que, por separado, ninguno de los dos tendría: peso "
                          "para negociar, escala para diversificar y una sola estrategia que rema en la misma dirección.",
                          St("scy2", fontSize=10, leading=14.5, textColor=INK, spaceBefore=4)),
                Paragraph("Dejar de pensar «lo mío y lo tuyo» para empezar a gobernar «lo nuestro» no os quita "
                          "autonomía: os da músculo. Vuestro patrimonio ya es uno; vuestra estrategia debería serlo también.",
                          St("scy3", fontSize=10, leading=14.5, textColor=INK, spaceBefore=4))],
               "#FBF6E0", "#B8860B", ancho=160*mm),
           Spacer(1, 4*mm)]
    return out

def seccion_asimetria_inversora(dAf, dBf, pA, pB, nA, nB):
    """Detecta divergencia clara en cultura inversora entre A y B. Si la hay, emite dictamen.
    Si no, devuelve [] (no imprime nada). Defensiva ante datos ausentes."""
    def _ratio_invertido(d):
        """Fracción del patrimonio líquido que está invertido (trabajando) vs parado. None si no hay base."""
        try:
            inv = float((d or {}).get("inversiones_liquidas") or 0)
            par = float((d or {}).get("colchon_liquido") or 0)
            base = inv + par
            if base <= 0:
                return None
            return inv / base
        except Exception:
            return None
    rA = _ratio_invertido(dAf); rB = _ratio_invertido(dBf)
    # Señal secundaria: score de la capa de inversión (C12). Más alto = peor (más capital dormido).
    try:
        cA = float(pA["C12"]["score"]); cB = float(pB["C12"]["score"])
    except Exception:
        cA = cB = None
    activo = quieto = None
    # 1) Señal primaria: ratio de capital invertido vs parado (uno tracciona, otro lo deja quieto)
    if rA is not None and rB is not None and abs(rA - rB) >= 0.40:
        if rA >= rB:
            activo, quieto = nA, nB
        else:
            activo, quieto = nB, nA
    # 2) Señal de respaldo: divergencia clara en la capa de inversión
    elif cA is not None and cB is not None and abs(cA - cB) >= 30:
        # score alto = capital dormido -> ese es el "quieto"
        if cA >= cB:
            quieto, activo = nA, nB
        else:
            quieto, activo = nB, nA
    if not activo or not quieto:
        return []
    out = [Paragraph("Asimetría de cultura inversora", h_sec),
           rb._box([
                Paragraph("<b>Dos relojes distintos frente al mercado</b>", St("aci0", fontSize=11, leading=15, textColor=ACCDK, fontName="Helvetica-Bold")),
                Paragraph("Existe entre vosotros una asimetría de cultura inversora: mientras <b>%s</b> mantiene el "
                          "capital quieto —sufriendo en silencio el coste de la inflación—, <b>%s</b> empuja hacia el "
                          "mercado. No es un defecto de ninguno de los dos: es una palanca que aún no habéis acoplado." % (quieto, activo),
                          St("aci1", fontSize=10, leading=14.5, textColor=INK, spaceBefore=4)),
                Paragraph("El riesgo no es que penséis distinto, sino que cada uno gobierne su mitad por libre: la "
                          "prudencia de %s frena el crecimiento de ambos, y el impulso de %s puede exponer de más al "
                          "hogar. Unificad <b>un único perfil ponderado</b> y un <b>vehículo común</b> —por ejemplo, una "
                          "cartera indexada conjunta— para que el miedo de uno no paralice y el empuje del otro no "
                          "desequilibre." % (quieto, activo),
                          St("aci2", fontSize=10, leading=14.5, textColor=INK, spaceBefore=4))],
               "#FBF4E4", "#B45309", ancho=160*mm),
           Spacer(1, 4*mm)]
    return out

def _kpi_celda_par(rotulo, valor, color="#1A1A17", nota=""):
    parr=[Paragraph(rotulo,St("opp_l_%s"%rotulo[:6],fontSize=8.5,leading=11,textColor=colors.HexColor("#6B7280"),fontName="Helvetica-Bold")),
          Paragraph("<b>%s</b>"%valor,St("opp_v_%s"%rotulo[:6],fontSize=20,leading=24,textColor=colors.HexColor(color),fontName="Helvetica-Bold",spaceBefore=1))]
    if nota: parr.append(Paragraph(nota,St("opp_n_%s"%rotulo[:6],fontSize=7.5,leading=10,textColor=colors.HexColor("#8A8472"))))
    return parr

def seccion_one_pager(nA, nB, dA, dB, compat, saludA, saludB):
    """ÍTEM 1 — Resumen ejecutivo de pareja 'de un vistazo' tras la portada. KPIs YA derivados de
    datos reales del hogar (no recalcula scoring). Failsafe: omite cualquier KPI sin dato."""
    try:
        a=_fill(dA); b=_fill(dB)
        hog={"gasto_mensual":_gasto_hogar(a,b),
             "ingreso_mensual":a["ingreso_mensual"]+b["ingreso_mensual"],
             "ahorro_mensual":a["ahorro_mensual"]+b["ahorro_mensual"],
             "patrimonio":a["patrimonio"]+b["patrimonio"],
             "inversiones_liquidas":(a.get("inversiones_liquidas") or 0)+(b.get("inversiones_liquidas") or 0),
             "colchon_liquido":(a.get("colchon_liquido") or 0)+(b.get("colchon_liquido") or 0)}
        fih=rb.fi_metrics(hog)
        cells=[]
        try:
            ccol="#1D6F42" if compat>=60 else ("#C2710C" if compat>=40 else "#9A3B2E")
            cells.append(_kpi_celda_par("COMPATIBILIDAD","%d<font size=10 color='#6B7280'>/100</font>"%int(compat),ccol,"Cómo de parecido vivís el dinero"))
        except Exception: pass
        try:
            nlib=float(fih[0]) if fih and fih[0] else 0
            if nlib>0: cells.append(_kpi_celda_par("NÚMERO DE LIBERTAD",rb._eur(nlib),"#1A1A17","Vuestro capital objetivo (gasto × 25)"))
        except Exception: pass
        try:
            prog=float(fih[1]) if fih and fih[1] is not None else None
            if prog is not None: cells.append(_kpi_celda_par("PROGRESO","%.0f%%"%prog,"#1A1A17","Hacia vuestra libertad"))
        except Exception: pass
        try:
            pat=float(hog.get("patrimonio") or 0)
            if pat>0: cells.append(_kpi_celda_par("FORTUNA NETA",rb._eur(pat),"#1A1A17","Lo que ya es vuestro hoy"))
        except Exception: pass
        try:
            tasa=float(fih[2]) if fih and fih[2] is not None else None
            if tasa is not None:
                tcol="#1D6F42" if tasa>=20 else ("#C2710C" if tasa>=10 else "#9A3B2E")
                cells.append(_kpi_celda_par("TASA DE AHORRO","%.0f%%"%tasa,tcol,"De cada euro que entra al hogar"))
        except Exception: pass
        try:
            cells.append(_kpi_celda_par("SALUD MEDIA","%d<font size=10 color='#6B7280'>/100</font>"%round((rb._sal100(saludA)+rb._sal100(saludB))/2),"#1A1A17","Vuestra media psicofinanciera"))
        except Exception: pass
        if not cells: return []
        out=[Paragraph("Vuestro diagnóstico de un vistazo",h_sec),
             Paragraph("Las cifras que mandan en vuestra economía de hogar, en una sola página. El resto del libro es el porqué y el cómo.",body),
             Spacer(1,5*mm)]
        for i in range(0,len(cells),3):
            fila=cells[i:i+3]
            while len(fila)<3: fila.append([Paragraph("",small)])
            out.append(Table([fila],colWidths=[53*mm,53*mm,54*mm],
                style=[("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),6),
                       ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
                       ("LINEBELOW",(0,0),(-1,-1),0.4,LINE)]))
        out+=[Spacer(1,3*mm),
              Paragraph("Estas cifras son conjuntas y nacen de vuestras propias respuestas. Donde de verdad diferís es en cómo las vive cada uno por dentro — eso lo recorre el libro.",small),
              PageBreak()]
        return out
    except Exception:
        return []

def seccion_impuesto_friccion(dAf, dBf, pA, pB, nA, nB):
    """ÍTEM 3 — 'Impuesto de la Fricción' en €: SI hay capital parado Y asimetría inversora real
    (misma señal que seccion_asimetria_inversora), estima el coste anual de oportunidad de forma
    HONESTA: capital_parado × rentabilidad prudente. Si falta cualquier dato → []. Cero invención."""
    R_PRUDENTE=3.0   # % prudente, dicho explícitamente al cliente
    def _ratio_inv(d):
        try:
            inv=float((d or {}).get("inversiones_liquidas") or 0); par=float((d or {}).get("colchon_liquido") or 0)
            base=inv+par
            if base<=0: return None
            return inv/base
        except Exception:
            return None
    try:
        rA=_ratio_inv(dAf); rB=_ratio_inv(dBf)
        # capital parado real del hogar = suma de colchones líquidos no invertidos
        cap_parado=float((dAf or {}).get("colchon_liquido") or 0)+float((dBf or {}).get("colchon_liquido") or 0)
        # Señal de asimetría (réplica de seccion_asimetria_inversora)
        asimetria=False
        if rA is not None and rB is not None and abs(rA-rB)>=0.40:
            asimetria=True
        else:
            try:
                cA=float(pA["C12"]["score"]); cB=float(pB["C12"]["score"])
                if abs(cA-cB)>=30: asimetria=True
            except Exception:
                pass
        if not asimetria or cap_parado<=0:
            return []
        coste=cap_parado*(R_PRUDENTE/100.0)
        if coste<=0: return []
        return [Paragraph("El impuesto de vuestra fricción, en euros", h_sec),
                rb._box([
                    Paragraph("<b>Lo que la parálisis os cuesta cada año</b>",St("if0",fontSize=11,leading=15,textColor=ACCDK,fontName="Helvetica-Bold")),
                    Paragraph("Vuestra parálisis conyugal mantiene <b>~%s</b> parados; a un <b>%.0f%% prudente</b>, eso son "
                              "<b>~%s al año</b> en rendimiento no capturado. No es una pérdida contable —el dinero sigue ahí— "
                              "pero es crecimiento que no llega: cada año que el desacuerdo deja el capital quieto, la inflación "
                              "le resta valor y el interés compuesto no se activa." % (rb._eur(cap_parado), R_PRUDENTE, rb._eur(coste)),
                              St("if1",fontSize=10,leading=14.5,textColor=INK,spaceBefore=4)),
                    Paragraph("Es una cifra deliberadamente conservadora: a una rentabilidad de mercado más alta, el coste sería "
                              "mayor. La buena noticia es que es enteramente reversible — y no depende del mercado, sino de poneros "
                              "de acuerdo.",
                              St("if2",fontSize=9.5,leading=14,textColor=GREY,spaceBefore=4))],
                    "#FBF4E4","#B45309",ancho=160*mm),
                Spacer(1,4*mm)]
    except Exception:
        return []

def seccion_perfil_inversor(rA_resp, rB_resp, dAf, dBf, pA, pB, nA, nB):
    """ÍTEM 4 — Scatter de cuadrantes del perfil inversor de la pareja. Ejes DERIVADOS de datos reales:
      X = apetito de riesgo (conservador→agresivo) := % del capital líquido puesto en mercado (ratio invertido).
      Y = constancia inversora (inactivo→recurrente) := 100 - score C12 (Disciplina de Inversión).
    Un punto por miembro + un punto ponderado (media). Si no se pueden derivar AMBOS ejes con datos
    reales para AMBOS → [] (no inventa posiciones). Figura ligera; cierra fig + gc en finally."""
    def _ratio_inv(d):
        try:
            inv=float((d or {}).get("inversiones_liquidas") or 0); par=float((d or {}).get("colchon_liquido") or 0)
            base=inv+par
            if base<=0: return None
            return inv/base
        except Exception:
            return None
    # X: apetito de riesgo real (0-100)
    xa=_ratio_inv(dAf); xb=_ratio_inv(dBf)
    if xa is None or xb is None: return []
    xa*=100.0; xb*=100.0
    # Y: constancia inversora real (0-100) desde C12 (score alto = capital dormido -> menos constancia)
    try:
        ya=100.0-float(pA["C12"]["score"]); yb=100.0-float(pB["C12"]["score"])
    except Exception:
        return []
    ya=max(0.0,min(100.0,ya)); yb=max(0.0,min(100.0,yb))
    xw=(xa+xb)/2.0; yw=(ya+yb)/2.0
    path="_perfilinv_par.png"; fig=None
    try:
        fig=plt.figure(figsize=(5.0,4.0),dpi=140); fig.patch.set_facecolor("#FCFAF2")
        ax=fig.add_axes([0.13,0.13,0.80,0.80]); ax.set_facecolor("#FCFAF2")
        ax.set_xlim(0,100); ax.set_ylim(0,100)
        ax.axhline(50,color="#D9D3C2",lw=1.0,zorder=1); ax.axvline(50,color="#D9D3C2",lw=1.0,zorder=1)
        for sp in ax.spines.values(): sp.set_color("#D9D3C2")
        ax.set_xticks([0,50,100]); ax.set_yticks([0,50,100])
        ax.set_xticklabels(["Conservador","","Agresivo"],fontsize=8,color="#6B7280")
        ax.set_yticklabels(["Inactivo","","Recurrente"],fontsize=8,color="#6B7280",rotation=90,va="center")
        ax.set_xlabel("Apetito de riesgo",fontsize=9,color="#1F2937")
        ax.set_ylabel("Constancia inversora",fontsize=9,color="#1F2937")
        ax.scatter([xw],[yw],s=120,color="#9CA3AF",edgecolors="#5C6470",linewidths=1.2,zorder=4,marker="D")
        ax.annotate("Ponderado",(xw,yw),textcoords="offset points",xytext=(8,-12),fontsize=7.5,color="#5C6470")
        ax.scatter([xa],[ya],s=150,color=A_COL,edgecolors="white",linewidths=1.4,zorder=5)
        ax.scatter([xb],[yb],s=150,color=B_COL,edgecolors="white",linewidths=1.4,zorder=5)
        ax.annotate(nA,(xa,ya),textcoords="offset points",xytext=(8,6),fontsize=8.5,color=A_COL,weight="bold")
        ax.annotate(nB,(xb,yb),textcoords="offset points",xytext=(8,6),fontsize=8.5,color=B_COL,weight="bold")
        fig.savefig(path,dpi=140,facecolor="#FCFAF2")
    except Exception:
        return []
    finally:
        try:
            if fig is not None: plt.close(fig)
        except Exception:
            pass
        gc.collect()
    # Lectura honesta del gráfico (cualitativa cuando no hay número que añada)
    dx=abs(xa-xb); dy=abs(ya-yb)
    if dx>=30 or dy>=30:
        lectura=("Estáis en cuadrantes distintos: uno tira hacia el mercado o hacia la constancia donde el otro frena. "
                 "El punto gris marca vuestro <b>perfil ponderado</b> — es ahí, en el centro de gravedad de los dos, donde conviene "
                 "converger: un único plan que ni paralice por el miedo de uno ni exponga de más por el impulso del otro.")
    else:
        lectura=("Vuestros puntos están cerca: compartís un perfil inversor parecido. El punto gris (perfil ponderado) confirma que "
                 "podéis decidir con un único criterio común, sin grandes cesiones de ninguno.")
    out=[Paragraph("Vuestro mapa de perfil inversor", h_sec),
         Paragraph("Cada eje sale de vuestros datos reales: cuánto de vuestro capital líquido está puesto en mercado (apetito de "
                   "riesgo) y cuánta disciplina inversora mostráis (constancia). No es un test de personalidad: es dónde os coloca "
                   "vuestro dinero hoy.",body),
         Spacer(1,2*mm),
         Image(path,width=128*mm,height=102*mm,hAlign="CENTER"),
         Spacer(1,2*mm),
         Paragraph(lectura,St("piL",fontSize=10,leading=14.5,textColor=INK)),
         Spacer(1,3*mm),
         ]
    # NOTA: NO borrar el PNG aqui: reportlab abre la imagen en doc.build(), que ocurre
    # despues de esta funcion. El _GEN_LOCK serializa la generacion, asi que el nombre fijo
    # es seguro (se sobrescribe en el siguiente build, igual que los demas graficos del libro).
    return out

def seccion_timeline_friccion(divs, nA, nB):
    """ÍTEM 5 — Eje/timeline de fricción: eje vertical fino color bronce con las divergencias a un
    lado y otro (A | eje | B), marcando los choques de mayor gap con un nodo. ReportLab puro.
    Failsafe: si no hay divergencias resolubles → []."""
    if not divs: return []
    BRONCE="#B45309"
    try:
        filas=[]
        for d in divs[:6]:
            es_vinc=bool(d.get("vinc")); gap=d.get("gap",0)
            nodo_col = "#9A3B2E" if (es_vinc or gap>=66) else BRONCE
            tag = "VÍNCULO" if es_vinc else ("Δ %.0f"%gap)
            nm = CAPAS.get(d["capa"],{}).get("nombre",d.get("capa",""))
            celA=[Paragraph("<font color='%s'>● %s</font>"%(A_COL,nA),small),
                  Paragraph("<i>%s</i>"%d.get("A",""),St("tlA_%d"%len(filas),fontSize=9,leading=12,textColor=INK,alignment=2))]
            celB=[Paragraph("<font color='%s'>● %s</font>"%(B_COL,nB),small),
                  Paragraph("<i>%s</i>"%d.get("B",""),St("tlB_%d"%len(filas),fontSize=9,leading=12,textColor=INK))]
            # nodo central: punto + etiqueta corta de capa
            nodo=[Paragraph("<font color='%s' size=15>●</font>"%nodo_col,St("tlN_%d"%len(filas),fontSize=15,leading=16,alignment=1)),
                  Paragraph("<font color='%s'><b>%s</b></font><br/><font size=6.5 color='#8A8472'>%s</font>"%(nodo_col,tag,nm),
                            St("tlNt_%d"%len(filas),fontSize=7.5,leading=9,alignment=1))]
            filas.append([celA, nodo, celB])
        t=Table(filas,colWidths=[64*mm,32*mm,64*mm],
            style=TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LINEAFTER",(0,0),(0,-1),1.4,colors.HexColor(BRONCE)),   # eje vertical bronce A|centro
                ("LINEBEFORE",(2,0),(2,-1),1.4,colors.HexColor(BRONCE)),  # eje vertical bronce centro|B
                ("ALIGN",(0,0),(0,-1),"RIGHT"),("ALIGN",(1,0),(1,-1),"CENTER"),("ALIGN",(2,0),(2,-1),"LEFT"),
                ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
                ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
                ("LINEBELOW",(0,0),(-1,-1),0.3,LINE)]))
        return [Paragraph("La línea de vuestros choques", h_sec),
                Paragraph("Vuestras divergencias, ordenadas en un solo eje. A la izquierda, lo que respondió <b>%s</b>; a la "
                          "derecha, <b>%s</b>. Los nodos en <font color='#9A3B2E'>rojo</font> marcan los choques de mayor distancia "
                          "—y los de vínculo y transparencia—: son por donde conviene empezar a hablar." % (nA,nB),body),
                Spacer(1,3*mm), t, PageBreak()]
    except Exception:
        return []

def seccion_glosario():
    """ÍTEM 2b — Glosario ejecutivo de pareja (cierre del libro): 8-12 términos clave, voz de pareja. Failsafe."""
    terminos=[
        ("Número de Libertad","El capital que, invertido a una retirada prudente, cubriría vuestro gasto sin volver a depender del trabajo de ninguno. Se estima como vuestro gasto anual del hogar multiplicado por 25 (regla 25×)."),
        ("Regla 25×","Atajo para fijar la meta común: ahorrad 25 veces vuestro gasto anual. Equivale a poder retirar ~4% al año del patrimonio invertido sin agotarlo."),
        ("Compatibilidad financiera","Cuánto de parecido vivís el dinero los dos. No es bueno ni malo en sí: las diferencias bien habladas suman; las calladas, erosionan."),
        ("Tasa de ahorro","Qué porción de lo que ingresa el hogar conseguís no gastar. La palanca que más controláis juntos."),
        ("DTI (deuda/ingreso)","Cuánto de vuestro ingreso mensual se va en cuotas de deuda. Por debajo del 20% es holgado; por encima del 35%, tensión."),
        ("Colchón de resistencia","Los meses que podríais sostener vuestra vida con la liquidez del hogar si dejarais de ingresar. Vuestro primer escudo ante un imprevisto."),
        ("Renta pasiva","Ingreso que no depende de vuestro tiempo: alquileres, dividendos, intereses. Cuanto mayor, menos atados estáis al trabajo."),
        ("Fortuna neta","Todo lo que poseéis menos todo lo que debéis. La foto de lo que de verdad es vuestro hoy."),
        ("Capital invertible","La parte de vuestro patrimonio líquida y disponible para hacer crecer (mercados y liquidez), sin contar la vivienda ni el negocio ilíquido."),
        ("Impuesto de la fricción","El rendimiento que dejáis de capturar cada año por mantener capital parado mientras no os ponéis de acuerdo. Es reversible y no depende del mercado."),
        ("Interés compuesto","El efecto de que vuestros rendimientos generen, a su vez, nuevos rendimientos. El motor que construye patrimonio con el tiempo, si el dinero está puesto a trabajar."),
    ]
    rows=[]
    for t,d in terminos:
        rows.append([Paragraph("<b>%s</b>"%t,St("glp_t_%s"%t[:5],fontSize=9.5,leading=13,textColor=ACCDK,fontName="Helvetica-Bold")),
                     Paragraph(d,St("glp_d_%s"%t[:5],fontSize=9,leading=12.5,textColor=INK))])
    tabla=Table(rows,colWidths=[40*mm,116*mm],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),0.4,LINE),
            ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),6),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    return [PageBreak(), Paragraph("Glosario ejecutivo",h_sec),
            Paragraph("Los términos que usa este libro, en una frase cada uno. Para que ningún concepto se interponga entre vosotros y vuestro plan.",body),
            Spacer(1,4*mm), tabla, Spacer(1,3*mm)]

# ---------------------------------------------------------------------------
# ÍNDICE DE FRICCIÓN CONYUGAL (Fase 1) — sin preguntas nuevas: todo se deriva
# de las divergencias que el motor ya cruza. Polaridad INVERTIDA: alto = malo.
# ---------------------------------------------------------------------------
def indice_friccion(rA, rB):
    """Devuelve (idx, n, n_conf). idx 0-100 = media ponderada del gap entre A y B
    sobre los ítems de escala (no atención), VÍNCULO ×1.5. n = ítems válidos;
    n_conf = ítems con gap>=50. Defensiva total: nunca lanza; sin datos -> (0,0,0)."""
    try:
        capas = (INST or {}).get("capas") or []
    except Exception:
        return (0, 0, 0)
    suma_pond = 0.0
    suma_peso = 0.0
    n = 0
    n_conf = 0
    for capa in capas:
        try:
            items = capa.get("items") or []
        except Exception:
            continue
        for it in items:
            try:
                if it.get("tipo") != "escala":
                    continue
                if it.get("atencion"):
                    continue
                _ra = _resp_op(it, (rA or {}).get(it.get("id")))
                _rb = _resp_op(it, (rB or {}).get(it.get("id")))
                if _ra is None or _rb is None:
                    continue
                sa = float(_ra[0]); sb = float(_rb[0])
                gap = abs(sa - sb)
                peso = 1.5 if ("VINCULO" in (it.get("dimensiones") or "")) else 1.0
                suma_pond += gap * peso
                suma_peso += peso
                n += 1
                if gap >= 50:
                    n_conf += 1
            except Exception:
                continue
    if n == 0 or suma_peso <= 0:
        return (0, 0, 0)
    try:
        idx = int(round(max(0.0, min(100.0, suma_pond / suma_peso))))
    except Exception:
        return (0, 0, 0)
    return (idx, n, n_conf)

def dial_friccion(path, idx):
    """Arco semicircular tipo velocímetro: verde (baja fricción, izq) -> ámbar -> terracota
    (alta fricción, der). Aguja en idx. Polaridad INVERTIDA (alto = malo). Figura ligera.
    Cierra la figura + gc en finally. Devuelve True/False. Defensiva."""
    fig = None
    try:
        try:
            v = max(0.0, min(100.0, float(idx)))
        except Exception:
            v = 0.0
        import numpy as _np
        from matplotlib.collections import LineCollection
        # Gradiente verde -> ámbar -> terracota (izquierda baja fricción, derecha alta)
        _STOPS = [(0.0, (29, 111, 66)), (0.5, (224, 169, 59)), (1.0, (198, 92, 78))]
        def _col(t):
            t = max(0.0, min(1.0, t))
            for i in range(len(_STOPS) - 1):
                t0, c0 = _STOPS[i]; t1, c1 = _STOPS[i + 1]
                if t0 <= t <= t1:
                    f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
                    return tuple((c0[k] + (c1[k] - c0[k]) * f) / 255.0 for k in range(3))
            return tuple(c / 255.0 for c in _STOPS[-1][1])
        INKG = "#2A2622"; MUTG = "#8A8472"; crema = "#FBF6E0"
        fig = plt.figure(figsize=(5.0, 3.0), dpi=140); fig.patch.set_facecolor(crema)
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(-1.25, 1.25); ax.set_ylim(-0.45, 1.32)
        ax.axis("off"); ax.set_aspect("equal")
        N = 240; th = _np.linspace(_np.pi, 0, N); R = 1.0
        ax.plot(_np.cos(th) * R, _np.sin(th) * R, color="#E2DBC9", lw=17, solid_capstyle="round", zorder=2)
        pts = _np.array([_np.cos(th) * R, _np.sin(th) * R]).T.reshape(-1, 1, 2)
        segs = _np.concatenate([pts[:-1], pts[1:]], axis=1)
        cols = [_col(t) for t in _np.linspace(0, 1, N - 1)]
        ax.add_collection(LineCollection(segs, colors=cols, linewidth=15, capstyle="round", zorder=3))
        for tk in (0, 25, 50, 75, 100):
            a = _np.pi * (1 - tk / 100.0)
            ax.plot([_np.cos(a) * (R - 0.11), _np.cos(a) * (R + 0.01)],
                    [_np.sin(a) * (R - 0.11), _np.sin(a) * (R + 0.01)],
                    color="#CFC7B2", lw=1.0, zorder=4)
        a = _np.pi * (1 - v / 100.0)
        ax.plot([0, _np.cos(a) * (R - 0.06)], [0, _np.sin(a) * (R - 0.06)],
                color=INKG, lw=2.4, solid_capstyle="round", zorder=6)
        ax.add_patch(plt.Circle((0, 0), 0.055, color=INKG, zorder=7))
        ax.add_patch(plt.Circle((0, 0), 0.022, color=crema, zorder=8))
        ax.text(0, -0.30, "%d" % round(v), color=INKG, fontsize=34, fontweight="bold", ha="center", va="center", zorder=9)
        ax.text(-1.02, -0.12, "baja", color=MUTG, fontsize=8.5, ha="center", va="center", zorder=9)
        ax.text(1.02, -0.12, "alta", color=MUTG, fontsize=8.5, ha="center", va="center", zorder=9)
        ax.text(0, 1.20, "ÍNDICE DE FRICCIÓN", color=MUTG, fontsize=9.5, fontweight="bold", ha="center", va="center", zorder=9)
        fig.savefig(path, dpi=140, facecolor=crema)
        return True
    except Exception:
        return False
    finally:
        try:
            if fig is not None:
                plt.close(fig)
        except Exception:
            pass
        gc.collect()

def seccion_indice_friccion(rA, rB, nA, nB):
    """Sección Fase 1: temperatura de fricción (dial con polaridad invertida) +
    tarjetas de contraste lateral (efecto espejo) sobre las top divergencias.
    Todo defensivo; siempre devuelve list. Sin datos válidos -> []."""
    try:
        idx, n, nc = indice_friccion(rA, rB)
    except Exception:
        return []
    if n == 0:
        return []
    if idx <= 33:
        banda = "Alineados"; bcol = "#1D6F42"; bfondo = "#EAF3EC"
    elif idx <= 66:
        banda = "Fricción moderada"; bcol = "#B45309"; bfondo = "#FBF4E4"
    else:
        banda = "Fricción estructural"; bcol = "#9A3B2E"; bfondo = "#FBECE8"
    out = [Paragraph("Vuestra temperatura de fricción financiera", h_sec),
           Paragraph(f"<font size=40 color='{bcol}'><b>{idx}</b></font>"
                     f"<font size=13 color='#6B7280'>/100</font>  "
                     f"<font color='{bcol}'><b>· {banda}</b></font>",
                     St("ifr_t", fontSize=11, leading=44, textColor=INK))]
    # Dial (failsafe: si no se genera, seguimos con número + banda)
    _dp = "_dial_friccion.png"
    _dial_ok = False
    try:
        _dial_ok = bool(dial_friccion(_dp, idx))
    except Exception:
        _dial_ok = False
    if _dial_ok:
        try:
            out.append(Image(_dp, width=96*mm, height=58*mm, hAlign="CENTER"))
        except Exception:
            pass
        # NO borrar el PNG aqui: reportlab lo abre en doc.build() (despues de esta funcion).
        # Nombre fijo seguro porque _GEN_LOCK serializa la generacion.
    # Lectura del número (sin alarmismo, sin € inventados)
    _choca = ("ninguno choca de frente" if nc == 0 else
              ("1 choca de frente" if nc == 1 else f"{nc} chocan de frente"))
    out += [Spacer(1, 2*mm),
            Paragraph(f"Este número resume, de los <b>{n}</b> puntos donde os hemos comparado, cuánta distancia "
                      f"hay entre cómo vivís el dinero cada uno — y, de ellos, {_choca}. No mide quién acierta: "
                      f"mide cuánto tenéis por hablar. La fricción no se cura sola ni con cifras; se gestiona "
                      f"poniéndola en palabras. Cada punto que baje será una conversación que ya habréis tenido.",
                      body),
            Spacer(1, 3*mm)]
    # Tarjetas de Contraste Lateral (efecto espejo) sobre las top divergencias
    try:
        divs = divergencias_item(rA, rB)
    except Exception:
        divs = []
    if divs:
        BRONCE = "#B45309"
        GRIS_AZ = "#EEF2F6"; CREMA_T = "#FBF4E4"
        out.append(Paragraph("El efecto espejo: lo que respondió cada uno", h_sub))
        for d in divs[:5]:
            try:
                es_vinc = bool(d.get("vinc")); gap = d.get("gap", 0)
                resalta = es_vinc or gap >= 66
                concepto = d.get("texto", "")
                celdaA = [Paragraph(f"<font color='{A_COL}'><b>● {nA}</b></font>", small),
                          Paragraph("<i>%s</i>" % d.get("A", ""),
                                    St("ifrA_%d" % gap, fontSize=9.2, leading=12.5, textColor=INK))]
                celdaB = [Paragraph(f"<font color='{B_COL}'><b>● {nB}</b></font>", small),
                          Paragraph("<i>%s</i>" % d.get("B", ""),
                                    St("ifrB_%d" % gap, fontSize=9.2, leading=12.5, textColor=INK))]
                cab = Paragraph(f"<b>{concepto}</b>",
                                St("ifrC_%d" % gap, fontSize=9.8, leading=13, textColor=ACCDK))
                cuerpo = Table([[celdaA, celdaB]], colWidths=[78*mm, 78*mm],
                               style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(GRIS_AZ)),
                                   ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(CREMA_T)),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                   ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
                sty = [("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                       ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
                if resalta:
                    sty.append(("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor(BRONCE)))
                tarjeta = Table([[cab], [cuerpo]], colWidths=[156*mm], style=TableStyle(sty))
                out.append(KeepTogether([tarjeta, Spacer(1, 3*mm)]))
            except Exception:
                continue
    out.append(PageBreak())
    return out

def seccion_asfixia_relativa(dAf, dBf, rA, rB, nA, nB):
    """Coste de equidad de un reparto al 50% cuando hay asimetría salarial real.
    Solo dispara si AMBOS declaran (o alguno declara) el modelo '50% exacto' Y la
    diferencia de ingresos es >=1.5x. Cifras 100% reales (ingresos + bolsa común).
    Defensiva total: ante datos ausentes o sin asimetría -> []. Siempre devuelve list."""
    try:
        iA = float((dAf or {}).get("ingreso_mensual") or 0)
        iB = float((dBf or {}).get("ingreso_mensual") or 0)
    except Exception:
        return []
    if iA <= 0 or iB <= 0:
        return []

    # --- localizar el item reparto_hogar en el instrumento (por id/campo) ---
    def _item_reparto():
        try:
            for sec in (INST.values() if isinstance(INST, dict) else []):
                if not isinstance(sec, list):
                    continue
                for it in sec:
                    if isinstance(it, dict) and (it.get("campo") == "reparto_hogar" or it.get("id") == "SD-27"):
                        return it
        except Exception:
            return None
        return None

    def _modelo(resp, it):
        """Texto de la opción elegida por un miembro para reparto_hogar. None si no resoluble."""
        if not it or not isinstance(resp, dict):
            return None
        idx = resp.get(it.get("id"))
        ops = it.get("opciones") or []
        try:
            if isinstance(idx, list):
                idx = idx[0] if idx else None
            if not isinstance(idx, int) or isinstance(idx, bool):
                return None
            if 0 <= idx < len(ops):
                op = ops[idx]
                return op if isinstance(op, str) else (op.get("texto") if isinstance(op, dict) else None)
        except Exception:
            return None
        return None

    it = _item_reparto()
    mA = _modelo(rA, it)
    mB = _modelo(rB, it)

    def _es_50(m):
        return bool(m) and ("50%" in m or "50 %" in m.replace(" ", " "))

    decl_50 = _es_50(mA) or _es_50(mB)
    if not decl_50:
        return []

    # --- asimetría salarial real ---
    rds = max(iA, iB) / min(iA, iB)
    if rds < 1.5:
        return []

    # --- coste de equidad con cifras reales ---
    try:
        bolsa = max(float((dAf or {}).get("gastos_comunes") or 0),
                    float((dBf or {}).get("gastos_comunes") or 0))
    except Exception:
        return []
    if bolsa <= 0:
        return []
    cuota = bolsa / 2.0
    ing_menor = min(iA, iB); ing_mayor = max(iA, iB)
    carga_menor = cuota / ing_menor
    carga_mayor = cuota / ing_mayor
    quien_menos = nA if iA < iB else nB
    quien_mas   = nA if iA >= iB else nB

    # ¿declaran modelos distintos? eso ES fricción; se menciona de pasada.
    nota_div = ""
    if mA and mB and mA != mB:
        nota_div = (" Conviene además notar que cada uno describe el reparto de una forma distinta: "
                    "ya esa diferencia de relato es, en sí misma, una fuente de fricción.")

    txt = (u"Con vuestro reparto al 50% y una diferencia de ingresos real ({rds:.1f}×), la mitad de los "
           u"gastos comunes supone el {cm:.0%} del sueldo de {qmenos} frente al {cM:.0%} del de {qmas}: "
           u"una asfixia que limita su capacidad de ahorro. Adapta recomienda mutar a un reparto proporcional "
           u"a los ingresos para proteger la cohesión de la sociedad conyugal.").format(
                rds=rds, cm=carga_menor, qmenos=quien_menos, cM=carga_mayor, qmas=quien_mas) + nota_div

    return [Paragraph(u"La asfixia del reparto al 50%", h_sec),
            Paragraph(u"Un reparto que parece justo sobre el papel puede repartir el esfuerzo de forma muy "
                      u"desigual cuando los sueldos no son iguales. Esto es lo que dicen vuestros números:", body),
            _callout(u"El coste oculto de la «equidad»", txt, A_COL, "#FBF6E0"),
            Spacer(1, 4*mm)]

def seccion_transparencia(rA, rB, nA, nB):
    """Transparencia financiera mutua a partir de 'opacidad_financiera' (SD-28).
    Mapea el indice elegido por A y por B al texto de la opcion. Indice >=2 = opaco,
    <=1 = transparente. Tres dictamenes (ambos opacos / asimetria / ambos transparentes).
    Sin cifras inventadas: solo el mapeo de respuestas + texto. Defensiva total:
    ante datos ausentes, item ausente o indices invalidos -> []. Siempre devuelve list."""
    # --- localizar el item opacidad_financiera en el instrumento (por campo/id) ---
    def _item_opac():
        try:
            for sec in (INST.values() if isinstance(INST, dict) else []):
                if not isinstance(sec, list):
                    continue
                for it in sec:
                    if isinstance(it, dict) and (it.get("campo") == "opacidad_financiera" or it.get("id") == "SD-28"):
                        return it
        except Exception:
            return None
        return None

    def _idx(resp, it):
        """Indice (int) elegido por un miembro para opacidad_financiera. None si no resoluble."""
        if not it or not isinstance(resp, dict):
            return None
        idx = resp.get(it.get("id"))
        ops = it.get("opciones") or []
        try:
            if isinstance(idx, list):
                idx = idx[0] if idx else None
            if not isinstance(idx, int) or isinstance(idx, bool):
                return None
            if 0 <= idx < len(ops):
                return idx
        except Exception:
            return None
        return None

    it = _item_opac()
    iA = _idx(rA, it)
    iB = _idx(rB, it)
    if iA is None or iB is None:
        return []

    ops = it.get("opciones") or []
    def _txt(i):
        try:
            op = ops[i]
            return op if isinstance(op, str) else (op.get("texto") if isinstance(op, dict) else None)
        except Exception:
            return None
    tA = _txt(iA); tB = _txt(iB)
    if tA is None or tB is None:
        return []

    opacA = iA >= 2
    opacB = iB >= 2

    if opacA and opacB:
        titulo = u"La opacidad mutua: terreno fértil para la desconfianza"
        txt = (u"Los dos reconocéis zonas que el otro no ve. Esa opacidad compartida no es un fallo moral, pero sí "
               u"es el caldo de cultivo de la desconfianza y de lo que llaman «infidelidad financiera»: pequeños "
               u"gastos o deudas que se callan y que, el día que afloran, pesan más por el silencio que por la cifra. "
               u"La solución no es vigilaros el uno al otro —eso solo añade tensión—, sino crear un espacio de "
               u"soberanía privada regulado: una bolsa común proporcional a lo que gana cada uno para todo lo de la "
               u"casa, y una cuenta personal para cada uno donde gastar lo discrecional sin pedir permiso ni rendir "
               u"cuentas. Lo privado deja de ser opaco cuando está pactado.")
    elif opacA != opacB:
        nClaro = nA if not opacA else nB
        nOpaco = nA if opacA else nB
        titulo = u"Una asimetría de transparencia"
        txt = (u"Aquí hay un desajuste que conviene nombrar: {nClaro} juega con las cartas sobre la mesa, mientras "
               u"que en {nOpaco} hay zonas que prefiere no compartir. Esa asimetría desgasta por los dos lados: uno "
               u"puede sentirse fiscalizado, el otro puede sentirse a ciegas. Ninguno tiene por qué tener razón; lo "
               u"que falta es una regla común. Acordad un «umbral de libertad»: una cifra por debajo de la cual cada "
               u"uno gasta lo suyo sin consultar, y por encima de la cual se habla. Así la transparencia deja de ser "
               u"una exigencia personal y pasa a ser un acuerdo de los dos.").format(nClaro=nClaro, nOpaco=nOpaco)
    else:
        titulo = u"Vuestra transparencia es un activo poco común"
        txt = (u"Los dos sabéis, en lo esencial, en qué gasta el otro. Eso es más raro de lo que parece y es un "
               u"verdadero activo de cohesión: la mayoría de las parejas arrastran zonas opacas que tarde o temprano "
               u"erosionan la confianza. Vuestro trabajo no es mejorar la transparencia, sino protegerla para que no "
               u"derive en control. Aseguraos de que cada uno conserva un espacio de gasto personal propio: la "
               u"claridad solo se sostiene en el tiempo cuando convive con un margen de libertad individual.")

    nota = (u" Esta dinámica de transparencia pesa, además, en vuestros focos de fricción del día a día.")

    return [Paragraph(u"Lo que sabéis (y lo que no) el uno del otro", h_sec),
            Paragraph(u"Os preguntamos por separado qué parte de los gastos personales del otro conocéis de verdad. "
                      u"Esto es lo que cada uno respondió:", body),
            _callout(nA, tA, A_COL, "#FBF6E0"),
            Spacer(1, 2*mm),
            _callout(nB, tB, B_COL, "#F4F4F2"),
            Spacer(1, 3*mm),
            _callout(titulo, txt + nota, A_COL, "#FBF3E8"),
            Spacer(1, 4*mm)]

def seccion_horizonte_retiro(rA, rB, nA, nB):
    """Convergencia de horizontes de retiro a partir de 'edad_retiro_ideal' (SD-29).
    Las opciones son ordinales (antes -> mas tarde); la brecha se mide en tramos.
    Tres dictamenes segun brecha (>=2 desalineados / ==1 matiz / ==0 refuerzo).
    Solo dictamen de texto aditivo: NO toca el Numero de Libertad ni nada del motor.
    Sin cifras inventadas: solo el mapeo de respuestas + texto. Defensiva total:
    ante datos ausentes, item ausente o indices invalidos -> []. Siempre devuelve list."""
    # --- localizar el item edad_retiro_ideal en el instrumento (por campo/id) ---
    def _item_ret():
        try:
            for sec in (INST.values() if isinstance(INST, dict) else []):
                if not isinstance(sec, list):
                    continue
                for it in sec:
                    if isinstance(it, dict) and (it.get("campo") == "edad_retiro_ideal" or it.get("id") == "SD-29"):
                        return it
        except Exception:
            return None
        return None

    def _idx(resp, it):
        """Indice (int) elegido por un miembro para edad_retiro_ideal. None si no resoluble."""
        if not it or not isinstance(resp, dict):
            return None
        idx = resp.get(it.get("id"))
        ops = it.get("opciones") or []
        try:
            if isinstance(idx, list):
                idx = idx[0] if idx else None
            if not isinstance(idx, int) or isinstance(idx, bool):
                return None
            if 0 <= idx < len(ops):
                return idx
        except Exception:
            return None
        return None

    it = _item_ret()
    iA = _idx(rA, it)
    iB = _idx(rB, it)
    if iA is None or iB is None:
        return []

    ops = it.get("opciones") or []
    def _txt(i):
        try:
            op = ops[i]
            return op if isinstance(op, str) else (op.get("texto") if isinstance(op, dict) else None)
        except Exception:
            return None
    tA = _txt(iA); tB = _txt(iB)
    if tA is None or tB is None:
        return []

    brecha = abs(iA - iB)

    if brecha >= 2:
        titulo = u"Horizontes de retiro desalineados"
        txt = (u"Aqui los dos no mirais al mismo punto del calendario: uno quiere soltar amarras bastante antes y el "
               u"otro se imagina dejandolo mucho mas tarde. No hay que unificar la meta a la fuerza —forzar un unico "
               u"horizonte suele generar mas tension que la propia diferencia—. Lo sano es proyectar el plan conjunto "
               u"por fases: primero liberar al que quiere parar antes, mientras el otro mantiene ingresos por eleccion "
               u"y no por obligacion; despues, el retiro total de ambos cuando toque. Lo importante no es coincidir en "
               u"la edad, sino decidir juntos —y dejarlo por escrito— como encajais los dos ritmos en un mismo plan.")
    elif brecha == 1:
        titulo = u"Horizontes casi alineados"
        txt = (u"Estais practicamente en la misma pagina: uno se ve soltando amarras solo un peldano antes que el "
               u"otro. Es un matiz menor, mas de ritmo que de rumbo. Vale la pena nombrarlo para que el que quiere "
               u"parar un poco antes no se sienta arrastrado, pero no condiciona la planificacion: el horizonte comun "
               u"esta, en lo esencial, compartido.")
    else:
        titulo = u"Mismo horizonte: una gran ventaja para planificar"
        txt = (u"Los dos os imaginais dejando de depender del sueldo en el mismo tramo de edad. Eso es mas valioso de "
               u"lo que parece: cuando la pareja comparte horizonte, cada decision de ahorro, inversion y gasto rema "
               u"en la misma direccion, sin tira y afloja sobre el «cuando». Vuestro trabajo no es negociar la meta, "
               u"sino blindarla: ponerla por escrito y revisar juntos, cada cierto tiempo, que el plan sigue "
               u"apuntando a ese horizonte comun.")

    return [Paragraph(u"Vuestro horizonte para soltar amarras", h_sec),
            Paragraph(u"Os preguntamos por separado a que edad os gustaria poder dejar de depender del sueldo. "
                      u"Esto es lo que cada uno respondio:", body),
            _callout(nA, tA, A_COL, "#FBF6E0"),
            Spacer(1, 2*mm),
            _callout(nB, tB, B_COL, "#F4F4F2"),
            Spacer(1, 3*mm),
            _callout(titulo, txt, A_COL, "#FBF3E8"),
            Spacer(1, 4*mm)]

def seccion_ansiedad_liquidez(rA, rB, nA, nB):
    """Ansiedad de liquidez a partir de 'colchon_ideal_meses' (SD-30).
    Las opciones son ordinales (menos -> mas colchon); la brecha se mide en tramos.
    Tres dictamenes segun brecha (>=2 paralisis / ==1 matiz / ==0 refuerzo).
    Solo dictamen de texto aditivo: NO toca el Numero de Libertad ni nada del motor.
    Sin cifras inventadas: solo el mapeo de respuestas + texto. Defensiva total:
    ante datos ausentes, item ausente o indices invalidos -> []. Siempre devuelve list."""
    # --- localizar el item colchon_ideal_meses en el instrumento (por campo/id) ---
    def _item_col():
        try:
            for sec in (INST.values() if isinstance(INST, dict) else []):
                if not isinstance(sec, list):
                    continue
                for it in sec:
                    if isinstance(it, dict) and (it.get("campo") == "colchon_ideal_meses" or it.get("id") == "SD-30"):
                        return it
        except Exception:
            return None
        return None

    def _idx(resp, it):
        """Indice (int) elegido por un miembro para colchon_ideal_meses. None si no resoluble."""
        if not it or not isinstance(resp, dict):
            return None
        idx = resp.get(it.get("id"))
        ops = it.get("opciones") or []
        try:
            if isinstance(idx, list):
                idx = idx[0] if idx else None
            if not isinstance(idx, int) or isinstance(idx, bool):
                return None
            if 0 <= idx < len(ops):
                return idx
        except Exception:
            return None
        return None

    it = _item_col()
    iA = _idx(rA, it)
    iB = _idx(rB, it)
    if iA is None or iB is None:
        return []

    ops = it.get("opciones") or []
    def _txt(i):
        try:
            op = ops[i]
            return op if isinstance(op, str) else (op.get("texto") if isinstance(op, dict) else None)
        except Exception:
            return None
    tA = _txt(iA); tB = _txt(iB)
    if tA is None or tB is None:
        return []

    brecha = abs(iA - iB)

    if brecha >= 2:
        titulo = u"Parálisis por ansiedad de liquidez"
        txt = (u"Aquí los dos vivís el efectivo de forma muy distinta: uno necesita una montaña de dinero guardado para "
               u"dormir tranquilo, mientras el otro ve ese mismo dinero como capital ocioso que la inflación devora "
               u"poco a poco. Esa diferencia, si no se gestiona, bloquea cualquier estrategia conjunta de crecimiento: "
               u"el miedo de uno frena el impulso del otro y nadie avanza. La solución no es forzar al prudente a "
               u"invertir contra su instinto, sino la estrategia de los «dos cubos». El primero, el Cubo de la Paz: "
               u"blindar el colchón que el miembro más precavido necesita para estar tranquilo, en una cuenta segura y "
               u"a su nombre, intocable. Y solo el excedente que quede por encima de ese colchón alimenta el segundo, "
               u"el Cubo del Crecimiento: invertir de forma sistemática y sin sobresaltos. Así el miedo de uno deja de "
               u"frenar el crecimiento de ambos, porque la seguridad y el crecimiento dejan de competir por el mismo "
               u"euro. Vale la pena nombrarlo en voz alta: uno de vosotros respondió «" + tA + u"» y el otro «" + tB +
               u"»; ese es exactamente el espacio que los dos cubos vienen a ordenar.")
    elif brecha == 1:
        titulo = u"Casi alineados en vuestra prudencia"
        txt = (u"Estáis prácticamente en la misma página sobre cuánto efectivo necesitáis para dormir tranquilos: uno "
               u"quiere un colchón solo un peldaño mayor que el otro. Es un matiz menor, más de temperamento que de "
               u"rumbo. Merece la pena nombrarlo para que quien necesita un poco más de margen no se sienta empujado, "
               u"pero no condiciona la estrategia: el tamaño del colchón común es fácil de acordar.")
    else:
        titulo = u"Mismo umbral de tranquilidad: fácil de acordar"
        txt = (u"Los dos coincidís en cuánto efectivo necesitáis guardado para estar tranquilos. Eso es más valioso de "
               u"lo que parece: cuando la pareja comparte el mismo umbral de prudencia, fijar el tamaño del colchón "
               u"común no genera tensión y el excedente puede ponerse a trabajar sin discusiones. Vuestro trabajo no "
               u"es negociar cuánto guardar, sino dejarlo por escrito y revisar juntos, cada cierto tiempo, que ese "
               u"colchón sigue ajustado a vuestra realidad.")

    return [Paragraph(u"Cuánto efectivo necesitáis para dormir tranquilos", h_sec),
            Paragraph(u"Os preguntamos por separado cuánto dinero en efectivo necesitáis tener guardado para dormir "
                      u"tranquilos. Esto es lo que cada uno respondió:", body),
            _callout(nA, tA, A_COL, "#FBF6E0"),
            Spacer(1, 2*mm),
            _callout(nB, tB, B_COL, "#F4F4F2"),
            Spacer(1, 3*mm),
            _callout(titulo, txt, A_COL, "#FBF3E8"),
            Spacer(1, 4*mm)]

def seccion_asimetria_pasivo(rA, rB, nA, nB):
    """Asimetria en la gestion del pasivo a partir de 'tolerancia_deuda' (SD-31).
    Las opciones son ordinales (aversion -> comodidad con la deuda); la brecha se mide en tramos.
    Tres dictamenes segun brecha (>=2 asimetria / ==1 matiz / ==0 refuerzo).
    Solo dictamen de texto aditivo: NO toca el Numero de Libertad ni nada del motor.
    Sin cifras inventadas: solo el mapeo de respuestas + texto. Defensiva total:
    ante datos ausentes, item ausente o indices invalidos -> []. Siempre devuelve list."""
    # --- localizar el item tolerancia_deuda en el instrumento (por campo/id) ---
    def _item_col():
        try:
            for sec in (INST.values() if isinstance(INST, dict) else []):
                if not isinstance(sec, list):
                    continue
                for it in sec:
                    if isinstance(it, dict) and (it.get("campo") == "tolerancia_deuda" or it.get("id") == "SD-31"):
                        return it
        except Exception:
            return None
        return None

    def _idx(resp, it):
        """Indice (int) elegido por un miembro para tolerancia_deuda. None si no resoluble."""
        if not it or not isinstance(resp, dict):
            return None
        idx = resp.get(it.get("id"))
        ops = it.get("opciones") or []
        try:
            if isinstance(idx, list):
                idx = idx[0] if idx else None
            if not isinstance(idx, int) or isinstance(idx, bool):
                return None
            if 0 <= idx < len(ops):
                return idx
        except Exception:
            return None
        return None

    it = _item_col()
    iA = _idx(rA, it)
    iB = _idx(rB, it)
    if iA is None or iB is None:
        return []

    ops = it.get("opciones") or []
    def _txt(i):
        try:
            op = ops[i]
            return op if isinstance(op, str) else (op.get("texto") if isinstance(op, dict) else None)
        except Exception:
            return None
    tA = _txt(iA); tB = _txt(iB)
    if tA is None or tB is None:
        return []

    brecha = abs(iA - iB)

    if brecha >= 2:
        titulo = u"Asimetría en la gestión del pasivo"
        txt = (u"Aquí los dos vivís la deuda de consumo de forma muy distinta: para uno de vosotros financiar a plazos "
               u"el coche, un viaje o una reforma es una carga psicológica casi inasumible, mientras el otro la "
               u"normaliza como una herramienta más del día a día. Esa diferencia no solo drena vuestro flujo libre "
               u"con intereses; es, sobre todo, un foco latente de desconfianza conyugal, porque cada compra a plazos "
               u"reabre en silencio la misma discusión. La solución no es que uno ceda al criterio del otro, sino "
               u"acordar juntos una política de deuda del hogar, por escrito: decidir entre los dos qué deudas son "
               u"aceptables —por ejemplo, solo la hipoteca, o deuda que compre activos que se pagan solos— y cuáles "
               u"preferís evitar. Así deja de ser una discusión que vuelve una y otra vez y pasa a ser una regla "
               u"compartida, conocida de antemano por ambos. Vale la pena nombrarlo en voz alta: uno de vosotros "
               u"respondió «" + tA + u"» y el otro «" + tB + u"»; esa distancia es exactamente lo que una política de "
               u"deuda común viene a ordenar.")
    elif brecha == 1:
        titulo = u"Criterios cercanos sobre la deuda"
        txt = (u"Estáis prácticamente en la misma página sobre cuánta financiación de consumo os resulta cómoda: uno se "
               u"sitúa solo un peldaño por encima del otro. Es un matiz menor, más de temperamento que de rumbo. Merece "
               u"la pena nombrarlo para que quien es algo más prudente no se sienta arrastrado, pero no condiciona "
               u"vuestra estrategia: acordar qué deudas aceptáis y cuáles no os resultará sencillo.")
    else:
        titulo = u"Misma filosofía de deuda: una fuente menos de conflicto"
        txt = (u"Los dos coincidís en cómo lleváis la financiación de consumo. Eso es más valioso de lo que parece: "
               u"cuando la pareja comparte la misma filosofía de deuda, las compras a plazos dejan de ser terreno de "
               u"discusión y se convierten en una decisión tranquila. Vuestro trabajo no es negociar cuánta deuda "
               u"asumir, sino dejar por escrito esa política común de deuda y revisar juntos, cada cierto tiempo, que "
               u"sigue encajando con vuestra realidad.")

    return [Paragraph(u"Cómo lleváis la deuda de consumo", h_sec),
            Paragraph(u"Os preguntamos por separado cómo lleváis el uso de financiación o préstamos para consumo. "
                      u"Esto es lo que cada uno respondió:", body),
            _callout(nA, tA, A_COL, "#FBF6E0"),
            Spacer(1, 2*mm),
            _callout(nB, tB, B_COL, "#F4F4F2"),
            Spacer(1, 3*mm),
            _callout(titulo, txt, A_COL, "#FBF3E8"),
            Spacer(1, 4*mm)]

def build_couple(rA,dA,cliA,rB,dB,cliB,out,sintesis=None,perfilA=None,perfilB=None):
    global INST, CAPAS
    _iv2=rb._cargar_v2(); _c2={c["code"]:c for c in _iv2["capas"]}
    rb.INST=_iv2; rb.CAPAS=_c2; INST=_iv2; CAPAS=_c2          # el libro de pareja se puntúa sobre el instrumento v2
    nA=(cliA["nombre"].split()[0] if (cliA.get("nombre") or "").strip() else "Persona A")
    nB=(cliB["nombre"].split()[0] if (cliB.get("nombre") or "").strip() else "Persona B")
    rb.CLIENTE_NOMBRE="%s & %s"%(nA,nB)                       # evita que se filtre el nombre de un informe anterior
    pA,trA,saludA=rb.perfil(rA); pB,trB,saludB=rb.perfil(rB)
    pA=rb._realidad(pA,_fill(dA)); pB=rb._realidad(pB,_fill(dB))   # guardarrail de realidad tambien en pareja
    saludA=round(statistics.mean([v["score"] for v in pA.values()]),1)
    saludB=round(statistics.mean([v["score"] for v in pB.values()]),1)
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
            _hog={"gasto_mensual":_gasto_hogar(_dAf,_dBf),"ingreso_mensual":_dAf["ingreso_mensual"]+_dBf["ingreso_mensual"],"ahorro_mensual":_dAf["ahorro_mensual"]+_dBf["ahorro_mensual"],"patrimonio":_dAf["patrimonio"]+_dBf["patrimonio"],"edad":(_dAf["edad"]+_dBf["edad"])/2}
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
        rb._box([Paragraph("<font color='#234E70'><b>&#9656;  Sois de los primeros — y lo afinamos con vosotros</b></font>",body),
                 Paragraph("Respaldamos cada cifra de este informe. Y como sois de nuestros primeros clientes, lo construimos también con vosotros: si al leerlo veis algún número o conclusión que no os encaje, escribidnos a <font color='#234E70'><b>info@adaptafamilyoffice.com</b></font>. Lo revisamos al momento, lo corregimos y os reenviamos vuestro informe actualizado, sin coste. Vuestra mirada lo hace mejor — para vosotros y para quienes vengan detrás.",body)],
                "#EEF2F6","#234E70",ancho=160*mm),
        Spacer(1,4*mm),
        Paragraph(f"{nA} y {nB}: el dinero es una de las causas más citadas de ruptura en las parejas — y casi "
                  "nunca por cuánto hay, sino porque cada uno lo vive distinto y no se habla. La grieta no la abre "
                  "la falta de dinero: la abre la diferencia callada. Este libro pone esas diferencias sobre la "
                  "mesa, sin juicio, para que dejen de operar en silencio.",body),
        Paragraph("No mide quién lo hace mejor. Mide dónde estáis alineados (vuestra fuerza conjunta) y dónde "
                  "divergís (vuestros focos de fricción). Al final encontraréis un guion para hablarlo.",body),
        Paragraph("Leedlo juntos. Esa es la mitad del valor.",body),
        PageBreak()]
    # === ÍTEM 1 · ONE-PAGER EJECUTIVO DE PAREJA (justo tras la portada) ===
    S+=rb._secsafe(seccion_one_pager,nA,nB,dA,dB,compat,saludA,saludB)
    S+=rb._secsafe(seccion_arquetipos,rA,rB,nA,nB)
    # compatibilidad + radar
    dAf=_fill(dA); dBf=_fill(dB)
    _gA=dAf["gasto_mensual"]; _gB=dBf["gasto_mensual"]; _gh=_gasto_hogar(dAf,dBf)
    _pfh=(((dAf.get("pct_gasto_fijo") or 0)*_gA+(dBf.get("pct_gasto_fijo") or 0)*_gB)/(_gA+_gB)) if (_gA+_gB)>0 else 0
    hogar={"gasto_mensual":_gh,
           "ingreso_mensual":dAf["ingreso_mensual"]+dBf["ingreso_mensual"],
           "ahorro_mensual":dAf["ahorro_mensual"]+dBf["ahorro_mensual"],
           "patrimonio":dAf["patrimonio"]+dBf["patrimonio"],
           "inversiones_liquidas":(dAf.get("inversiones_liquidas") or 0)+(dBf.get("inversiones_liquidas") or 0),
           "colchon_liquido":(dAf.get("colchon_liquido") or 0)+(dBf.get("colchon_liquido") or 0),
           "renta_pasiva":(dAf.get("renta_pasiva") or 0)+(dBf.get("renta_pasiva") or 0),
           "coste_vivienda":(dAf.get("coste_vivienda") or 0)+(dBf.get("coste_vivienda") or 0),
           "cuota_deuda":(dAf.get("cuota_deuda") or 0)+(dBf.get("cuota_deuda") or 0),
           "pension_estimada":(dAf.get("pension_estimada") or 0)+(dBf.get("pension_estimada") or 0),
           "pct_gasto_fijo":_pfh,
           "edad":(dAf["edad"]+dBf["edad"])/2}
    fi_h=rb.fi_metrics(hogar)
    try:
        rb.panel_compat("_compat.png", compat, nA, nB, 100-saludA, 100-saludB)
        S+=[rb.FullBleedImage("_compat.png"), PageBreak()]
    except Exception:
        pass
    S+=[Paragraph("Vuestro mapa conjunto",h_sec),
        Table([[Paragraph(f"<font size=40 color='#1A1A17'><b>{compat}</b></font><font size=13 color='#6B7280'>/100</font>",body),
                Paragraph(f"<b>Compatibilidad financiera</b><br/><font size=8 color='#6B7280'>Cuanto más alto, más "
                          f"parecida es vuestra forma de vivir el dinero. No es bueno ni malo en sí: las diferencias "
                          f"bien habladas suman.</font>",body)]],
              colWidths=[42*mm,118*mm],style=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0)]),
        Spacer(1,1*mm),
        Table([[Paragraph(f"<font color='{A_COL}'>●</font> {cliA['nombre']}: <b>{rb._sal100(saludA)}</b>/100",small),
                Paragraph(f"<font color='{B_COL}'>●</font> {cliB['nombre']}: <b>{rb._sal100(saludB)}</b>/100",small)]],
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
    # --- Foto patrimonial del hogar (invertido/parado/iliquido) ---
    _h_inv=float(hogar["inversiones_liquidas"]); _h_par=float(hogar["colchon_liquido"]); _h_pat=float(hogar["patrimonio"])
    _h_ili=max(0.0,_h_pat-_h_inv-_h_par); _h_tot=_h_inv+_h_par+_h_ili
    if _h_tot>0:
        _pf=lambda v:"%.0f%%"%(100*v/_h_tot); _trab=100*_h_inv/_h_tot
        S+=[Spacer(1,3*mm),Paragraph("Vuestra foto patrimonial: qué trabaja y qué duerme",h_sub),
            Paragraph("En <font color='#1D6F42'><b>verde</b></font>, el dinero invertido que trabaja para vosotros; en <font color='#C9A227'><b>ámbar</b></font> y <font color='#9CA3AF'><b>gris</b></font>, el que no: parado en el banco o atrapado en ladrillo y negocio.",small),
            Spacer(1,1.5*mm),
            rb.FotoPatrimonio(_h_inv,_h_par,_h_ili,w=160,h=13),
            Spacer(1,1.5*mm),
            Table([[Paragraph("<font color='#1D6F42'>●</font> <b>%.0f%% TRABAJA</b> para vosotros"%_trab,small),
                    Paragraph("<font color='#9CA3AF'>●</font> <b>%.0f%% DUERME</b> (parado + ilíquido)"%(100-_trab),small)]],
                   colWidths=[80*mm,80*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0)]),
            Table([[Paragraph("<font color='#1D6F42'>●</font> Invertido: %s · %s"%(rb._eur(_h_inv),_pf(_h_inv)),small),
                    Paragraph("<font color='#C9A227'>●</font> Parado: %s · %s"%(rb._eur(_h_par),_pf(_h_par)),small),
                    Paragraph("<font color='#9CA3AF'>●</font> Ilíquido: %s · %s"%(rb._eur(_h_ili),_pf(_h_ili)),small)]],
                   colWidths=[54*mm,53*mm,53*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0),("VALIGN",(0,0),(-1,-1),"TOP")]),
            Spacer(1,2*mm)]
        if _h_pat > (_h_inv+_h_par)*1.5+20000:
            _cobp=round(100*_h_pat/fi_h[0]) if fi_h[0] else 0   # potencial movilizando todo (incluida la vivienda, llegado el momento)
            _lt=" — con eso quedaríais en <b>libertad financiera</b>" if _cobp>=100 else ""
            S+=[Paragraph("<b>Patrimonio no es renta — y es vuestra mayor oportunidad:</b> tenéis %s de patrimonio, pero hoy solo %s está invertido o líquido generando renta (la cobertura del %s%% de arriba). Si movilizarais lo ilíquido —rentabilizando lo parado y, llegado el momento de simplificar, vendiendo o reduciendo la vivienda que ya no necesitéis—, vuestra cobertura pasaría del %s%% al <b>%s%%</b>%s. Convertir patrimonio dormido en renta es donde más mueve la aguja un family office."%(rb._eur(_h_pat),rb._eur(_h_inv+_h_par),("%.0f"%fi_h[1]),("%.0f"%fi_h[1]),("%.0f"%_cobp),_lt),small),Spacer(1,2*mm)]
    # --- Coste de la inflación sobre el capital ocioso del hogar (aditivo, failsafe) ---
    try:
        _tapH=rb.tapon_coste(hogar)
        if _tapH:
            _excH,_=_tapH; _perdH=_excH*0.03
            S+=[Spacer(1,3*mm),
                rb._box_sello([Paragraph("El coste de vuestro capital ocioso",St("cinfh_h",fontSize=12,leading=15,textColor=ACCDK,fontName=rb.FB)),
                      Paragraph("Tenéis alrededor de <b>%s</b> en liquidez por encima de un colchón sano. A una inflación del 3%%, ese dinero "
                                "pierde del orden de <b>%s al año</b> de poder de compra solo por estar parado. No lo veis en el extracto: lo "
                                "notáis cuando lo que antes comprabais con esa cifra ya no lo cubre."%(rb._eur(_excH),rb._eur(_perdH)),
                                St("cinfh_t",fontSize=10,leading=14,textColor=INK,spaceBefore=3)),
                      Paragraph("<b>Dos palancas, no una:</b> poner ese excedente a rentar al menos lo que sube la vida, y revisar la <b>capa "
                                "fiscal</b> de cómo lo hacéis (vehículo, diferimiento, traspasos). Rentabilidad y eficiencia fiscal se suman.",
                                St("cinfh_f",fontSize=10,leading=14,textColor=INK,spaceBefore=4))],
                     "#FBF4E4","#B45309",nota="C",ancho=160*mm),
                Spacer(1,2*mm)]
    except Exception:
        pass
    # --- Foto del flujo del hogar (activo/pasivo, fijo/variable) ---
    _x_ing=float(hogar["ingreso_mensual"]); _x_gas=float(hogar["gasto_mensual"])
    _x_pas=min(float(hogar["renta_pasiva"]),_x_ing); _x_act=max(0.0,_x_ing-_x_pas)
    _x_pf=min(100.0,max(0.0,float(hogar.get("pct_gasto_fijo") or 0)))
    _x_fij=min(_x_gas,(_x_gas*_x_pf/100.0) if _x_pf>0 else (float(hogar["coste_vivienda"])+float(hogar["cuota_deuda"]))); _x_var=max(0.0,_x_gas-_x_fij)
    if _x_ing>0 and _x_gas>0:
        S+=[Paragraph("Vuestra foto del flujo: de dónde viene y a dónde va",h_sub),
            Paragraph("En <font color='#1D6F42'><b>verde</b></font>, el ingreso <b>pasivo</b> (os libera); en <font color='#C65C4E'><b>rojo</b></font>, el gasto <b>fijo</b> (os ata). Más verde arriba y menos rojo abajo, más libres sois.",small),
            Spacer(1,1.5*mm),
            rb.FlujoEstructura(_x_act,_x_pas,_x_fij,_x_var,w=160,h=12),
            Spacer(1,2*mm),
            Table([[Paragraph("<font color='#6B7280'>●</font> Ingreso <b>activo</b>: %s"%rb._eur(_x_act),small),
                    Paragraph("<font color='#1D6F42'>●</font> Ingreso <b>pasivo</b> (libera): %s · %.0f%%"%(rb._eur(_x_pas),(100*_x_pas/_x_ing if _x_ing else 0)),small)]],
                   colWidths=[80*mm,80*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0)]),
            Table([[Paragraph("<font color='#C65C4E'>●</font> Gasto <b>fijo</b> (ata): %s · %.0f%%"%(rb._eur(_x_fij),(100*_x_fij/_x_gas if _x_gas else 0)),small),
                    Paragraph("<font color='#C9A227'>●</font> Gasto <b>variable</b>: %s"%rb._eur(_x_var),small)]],
                   colWidths=[80*mm,80*mm],style=[("LEFTPADDING",(0,0),(-1,-1),0)]),
            Spacer(1,3*mm)]
    rb.cashflow_waterfall(hogar,"_cashH.png")
    S+=[KeepTogether([Paragraph("Vuestro flujo de caja conjunto",h_sub),
        Image("_cashH.png",width=158*mm,height=74*mm,hAlign="CENTER"),
        Paragraph("De cada euro que entra en casa, esto es lo que se queda y lo que se va. Si la barra «sin asignar» "
                  "es grande, no es libertad: es dinero esperando una decisión que aún no habéis tomado juntos.",small)]),
        PageBreak()]
    # === MAPA DE LA RELACIÓN ===
    try:
        _short={"C1":"Estrés con el dinero","C2":"Libertad","C3":"Resistencia","C4":"Estilo de vida","C5":"Protección legal","C6":"Gasto de imagen","C7":"Dependencia de ingresos","C8":"Antifragilidad","C9":"Control del flujo","C10":"Salud de la deuda","C11":"Crecimiento","C12":"Inversión"}
        _caps=[(_short.get(c, CAPAS[c]["nombre"]), pA[c]["score"], pB[c]["score"]) for c in CAPAS]
        mapa_relacion("_relmap.png", _caps, compat, nA, nB)
        S+=[rb.FullBleedImage("_relmap.png"), PageBreak()]
    except Exception:
        pass
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
        rows.append([Paragraph(f"{c} · {CAPAS[c]['nombre']}",small),Paragraph(f"{rb._sal100(a)}",small),
                     Paragraph(f"{rb._sal100(b)}",small),Paragraph(f"{g:.0f}",small),
                     rb.Chip(zona,zc,w=64,h=13)])
    S+=[tbl(rows,[78*mm,15*mm,15*mm,20*mm,32*mm]),PageBreak()]
    S+=rb._secsafe(seccion_dafo_pareja,pA,pB,nA,nB)
    S+=rb._secsafe(seccion_caminos_hogar,dA,dB)
    S+=rb._secsafe(seccion_dinero_trabaja,dA,dB)
    S+=rb._secsafe(seccion_acelerador_hogar,dA,dB)
    rb.radar_png(pA,"_radarA.png"); rb.radar_png(pB,"_radarB.png")
    try: _exA=sv.computar_extras(rA,_fill(dA),perfilA or {},_iv2)
    except Exception: _exA=None
    try: _exB=sv.computar_extras(rB,_fill(dB),perfilB or {},_iv2)
    except Exception: _exB=None
    try:
        rb.portadilla("_pa_indiv.png", "Acto 2", 'VOSOTROS DOS,\nPOR DENTRO', 'La foto psicológica de cada uno antes de cruzaros: cómo vive el dinero por dentro.')
        S+=[PageBreak(), rb.FullBleedImage("_pa_indiv.png")]
    except Exception:
        pass
    S+=rb._secsafe(seccion_individual,cliA["nombre"] or nA,pA,trA,saludA,dA,"_radarA.png",fi_h,rA,extras=_exA)
    S+=rb._secsafe(rb.seccion_fiabilidad,_exA)
    S+=rb._secsafe(seccion_individual,cliB["nombre"] or nB,pB,trB,saludB,dB,"_radarB.png",fi_h,rB,extras=_exB)
    S+=rb._secsafe(rb.seccion_fiabilidad,_exB)
    # capitulos comparativos por capa
    try:
        rb.portadilla("_pa_cruce.png", "Acto 3", 'DÓNDE CHOCÁIS\nY DÓNDE ENCAJÁIS', 'Las doce capas, enfrentadas. Dónde os sostenéis y dónde salta la fricción.')
        S+=[PageBreak(), rb.FullBleedImage("_pa_cruce.png")]
    except Exception:
        pass
    S+=[Paragraph("Capa por capa, los dos",h_sec),
        Paragraph("El corazon de vuestro libro: las doce dimensiones, leidas en pareja. La barra dorada es "
                  f"{nA}; la gris, {nB}. Mas corta = mas sano.",body),PageBreak()]
    for n,code in enumerate(CAPAS,1):
        a,b=pA[code]["score"],pB[code]["score"]
        bloque=[Paragraph(f"CAPÍTULO {n}",kick),
                Paragraph(CAPAS[code]["nombre"],St("cb",fontSize=15,leading=19,textColor=ACCDK,fontName="Helvetica-Bold")),
                Table([[""]],colWidths=[40*mm],style=[("LINEBELOW",(0,0),(-1,-1),1.5,colors.HexColor(A_COL))]),
                Spacer(1,3*mm),
                Paragraph("Qué mide",h_sub),
                Paragraph("Esta capa mide "+QMIDE_PAREJA.get(code, CAP_QMIDE[code]),body),
                Paragraph("Vuestros resultados",h_sub),
                Table([[Paragraph(f"<font color='{A_COL}'>●</font> {nA}: <b>{rb._sal100(a)}</b>/100",small),
                        Paragraph(f"<font color='{B_COL}'>●</font> {nB}: <b>{rb._sal100(b)}</b>/100",small)],
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
                Paragraph("Cómo se nota en vuestro día a día",h_sub),
                Paragraph(DIADIA.get(code,""),body),
                Paragraph("El riesgo para vuestra econom\u00eda",h_sub),
                Paragraph(rb.RIESGO[code],body),
                Paragraph("La oportunidad si lo trabaj\u00e1is juntos",h_sub),
                Paragraph(rb.OPORTUNIDAD[code],body),
                Paragraph("La trampa que evitar",h_sub),
                Paragraph("<font color='#9A3B2E'><b>&#9888;</b></font>  "+TRAMPA.get(code,""),
                          St("tr",fontSize=10,leading=14,leftIndent=4)),
                Paragraph("Vuestro siguiente paso",h_sub),
                Paragraph(f"<font color='{A_COL}'><b>&bull;</b></font>  "+paso_pareja(code),
                          St("pp",fontSize=10,leading=14,leftIndent=4,backColor=LIGHT,borderPadding=6)),
                Paragraph("Vuestro micro-acuerdo de este mes",h_sub),
                rb._box([Paragraph(MICROACUERDO.get(code,""),St("ma",fontSize=10,leading=14))],
                        "#EEF2F6","#234E70",ancho=156*mm),
                Spacer(1,2*mm),
                Paragraph(f"\u201c{rb.PRINCIPIO[code]}\u201d",St("pr2",fontSize=10.5,leading=14,textColor=ACCDK,
                          fontName="Helvetica-Oblique")),
                Paragraph("Para hablar entre vosotros: "+rb.REFLEX[code],St("rf2",fontSize=10,leading=14,
                          textColor=INK,fontName="Helvetica-Oblique",spaceBefore=3))]
        S.append(KeepTogether(bloque)); S.append(PageBreak())
    # === ÍNDICE DE FRICCIÓN CONYUGAL (Fase 1) — corona el Mapa de Fricción ===
    S+=rb._secsafe(seccion_indice_friccion, rA, rB, nA, nB)
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
    # === ÍTEM 5 · EJE/TIMELINE DE FRICCIÓN (mejora visual del mapa de fricción) ===
    S+=rb._secsafe(seccion_timeline_friccion,divs,nA,nB)
    S+=rb._secsafe(seccion_coste_no_hablarlo,pA,pB,nA,nB,hogar,fi_h,divs)
    S+=rb._secsafe(seccion_sociedad_conyugal,hogar,nA,nB)
    S+=rb._secsafe(seccion_asfixia_relativa, dAf, dBf, rA, rB, nA, nB)
    # === TRANSPARENCIA FINANCIERA MUTUA (opacidad_financiera / SD-28) ===
    S+=rb._secsafe(seccion_transparencia, rA, rB, nA, nB)
    # === CONVERGENCIA DE HORIZONTES DE RETIRO (edad_retiro_ideal / SD-29) ===
    S+=rb._secsafe(seccion_horizonte_retiro, rA, rB, nA, nB)
    # === ANSIEDAD DE LIQUIDEZ (colchon_ideal_meses / SD-30) ===
    S+=rb._secsafe(seccion_ansiedad_liquidez, rA, rB, nA, nB)
    # === ASIMETRÍA EN LA GESTIÓN DEL PASIVO (tolerancia_deuda / SD-31) ===
    S+=rb._secsafe(seccion_asimetria_pasivo, rA, rB, nA, nB)
    S+=rb._secsafe(seccion_asimetria_inversora,dAf,dBf,pA,pB,nA,nB)
    # === ÍTEM 3 · IMPUESTO DE LA FRICCIÓN (€) ===
    S+=rb._secsafe(seccion_impuesto_friccion,dAf,dBf,pA,pB,nA,nB)
    # === ÍTEM 4 · SCATTER DE PERFIL INVERSOR DE LA PAREJA ===
    S+=rb._secsafe(seccion_perfil_inversor,rA,rB,dAf,dBf,pA,pB,nA,nB)
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
    # calendario de cuatro conversaciones (sobre los temas más divergentes / más débiles)
    _temas=[]
    for c in sorted(CAPAS,key=lambda c:abs(pA[c]["score"]-pB[c]["score"]),reverse=True):
        if abs(pA[c]["score"]-pB[c]["score"])>=18 or (pA[c]["score"]+pB[c]["score"])/2>=55:
            _temas.append(c)
        if len(_temas)>=4: break
    for c in sorted(CAPAS,key=lambda c:(pA[c]["score"]+pB[c]["score"]),reverse=True):
        if len(_temas)>=4: break
        if c not in _temas: _temas.append(c)
    S+=[Spacer(1,3*mm),Paragraph("Vuestro calendario de cuatro conversaciones",h_sub),
        Paragraph("Una conversación por semana, no todas de golpe. Cada una sobre un tema concreto, con su pequeño "
                  "acuerdo al final. En cuatro semanas habréis hablado de lo que muchas parejas no hablan en años.",body)]
    _crows=[[Paragraph("<b>Semana</b>",small),Paragraph("<b>De qué habláis</b>",small),Paragraph("<b>Acuerdo a cerrar</b>",small)]]
    for _i,_c in enumerate(_temas,1):
        _crows.append([Paragraph(f"<b>{_i}</b>",small),Paragraph(rb.CAPAS[_c]["nombre"],small),
                       Paragraph(MICROACUERDO.get(_c,paso_pareja(_c)),small)])
    S+=[tbl(_crows,[20*mm,52*mm,88*mm]),PageBreak()]
    try:
        rb.portadilla("_pa_plan.png", "Acto 4", 'VUESTRO PLAN,\nEN MARCHA', 'De la conversación a los hechos: constitución, hoja de ruta y vuestro laboratorio.')
        S+=[PageBreak(), rb.FullBleedImage("_pa_plan.png")]
    except Exception:
        pass
    S+=rb._secsafe(seccion_constitucion_hogar,pA,pB,nA,nB,hogar,fi_h,divs)
    S+=rb._secsafe(seccion_hoja_ruta_12m,pA,pB,nA,nB,hogar)
    pass  # laboratorio_pareja eliminado (cuaderno de trabajo redundante)
    S+=[Spacer(1,4*mm),   # "Como seguir / repetid el diagnostico" eliminado; queda solo el descargo
        Paragraph("Este libro es una herramienta de autoconocimiento; no sustituye asesoramiento profesional ni "
                  "terapia de pareja.",small)]
    S+=rb._secsafe(seccion_adapta_pareja,pA,pB,nA,nB)
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
            if it.get("atencion"): continue
            sa=sb=None; na_a=na_b=False
            if it["tipo"]=="escala":
                ia=rA.get(it["id"]); ib=rB.get(it["id"])
                _ra=_resp_op(it,ia); _rb=_resp_op(it,ib)
                if _ra is not None: va=_ra[1]; sa=_ra[0]
                else: va=""; na_a=True
                if _rb is not None: vb=_rb[1]; sb=_rb[0]
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
    # === \u00cdTEM 2b \u00b7 GLOSARIO EJECUTIVO (cierre de anexos) ===
    S+=rb._secsafe(seccion_glosario)
    # --- saneador: colapsa PageBreaks consecutivos (elimina paginas en blanco) ---
    _clean=[]
    for _f in S:
        if isinstance(_f, PageBreak) and _clean and isinstance(_clean[-1], PageBreak):
            continue
        _clean.append(_f)
    while _clean and isinstance(_clean[-1], PageBreak):
        _clean.pop()
    S=_clean
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
