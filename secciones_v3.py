# -*- coding: utf-8 -*-
"""Secciones financieras v3 del PDF — Adapta Family Office.

Construye los 7 hallazgos nuevos como flowables ReportLab a partir de la salida de
motor_financiero_v3. AISLADO: no toca report_book.py (se cablea con un import + una
llamada cuando el sandbox sincronice). Estilos propios, ligeros y armonizables luego
con la piel "Legado" clara del libro. Todo blindado: dato ausente -> sección vacía.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle

INK   = colors.HexColor("#1A1A17")
GR    = colors.HexColor("#6B7280")
GOLD  = colors.HexColor("#B8860B")
VERDE = colors.HexColor("#1D6F42")
ROJO  = colors.HexColor("#9A3B2E")
AMBAR = colors.HexColor("#B45309")
CREMA = colors.HexColor("#FBF4E4")
LINEA = colors.HexColor("#E5E0D5")

def _eur(n):
    try: return "{:,.0f}".format(round(float(n))).replace(",", ".")
    except Exception: return "0"

H   = ParagraphStyle("v3h", fontName="Helvetica-Bold", fontSize=16, textColor=INK, leading=20, spaceBefore=6, spaceAfter=2)
EYE = ParagraphStyle("v3eye", fontName="Helvetica-Bold", fontSize=8.5, textColor=GOLD, leading=12, spaceAfter=3)
BODY= ParagraphStyle("v3b", fontName="Helvetica", fontSize=10, textColor=INK, leading=15, spaceAfter=4)
SM  = ParagraphStyle("v3sm", fontName="Helvetica", fontSize=8.5, textColor=GR, leading=12)
BIG = ParagraphStyle("v3big", fontName="Helvetica-Bold", fontSize=34, textColor=INK, leading=38)

def _box(flow, bg=CREMA, brd="#E2D9BF", w=160*mm):
    t = Table([[flow]], colWidths=[w])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("BOX",(0,0),(-1,-1),0.8,colors.HexColor(brd)),
                           ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
                           ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),("ROUNDEDCORNERS",[8,8,8,8])]))
    return t

def _eyebrow(t): return Paragraph(t.upper(), EYE)

# ---------- 1. Cuánto vale tu hora ----------
def seccion_precio_hora(ing):
    if not ing or ing.get("precio_hora_global") is None: return []
    S=[_eyebrow("Tu tiempo, en euros"), Paragraph("Cuánto vale tu hora", H),
       Paragraph("Si divides lo que ganas por las horas <b>reales</b> que le dedicas, esto vale tu hora hoy. No es un juicio: es la cifra que más reordena prioridades.", BODY),
       Paragraph('<font size=30 color="#1A1A17"><b>%s €</b></font><font size=12 color="#6B7280"> / hora trabajada</font>' % _eur(ing["precio_hora_global"]), BODY)]
    ph=ing.get("precio_hora_fuentes") or []
    if len(ph)>1:
        rows=[[Paragraph("<b>Fuente</b>",SM),Paragraph("<b>€/hora</b>",SM)]]
        for x in ph: rows.append([Paragraph(str(x.get("tipo","")),SM),Paragraph("<b>%s €</b>"%_eur(x.get("eur_hora")),SM)])
        t=Table(rows,colWidths=[110*mm,46*mm]); t.setStyle(TableStyle([("LINEBELOW",(0,0),(-1,-1),0.4,LINEA),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        S.append(Spacer(1,4)); S.append(t)
    return [KeepTogether(S), Spacer(1,10*mm)]

# ---------- 2. Tu fuga no consciente ----------
def seccion_fuga(gas):
    if not gas or gas.get("fuga_no_consciente",0)<=0: return []
    fuga=gas["fuga_no_consciente"]
    inner=[Paragraph("Tu fuga no consciente", H),
           Paragraph('<font size=30 color="#9A3B2E"><b>%s €</b></font><font size=12 color="#6B7280"> al mes · %s €/año</font>'%(_eur(fuga),_eur(gas.get("fuga_anual",fuga*12))), BODY),
           Paragraph("Es la diferencia entre lo que crees gastar y lo que sumaste por categorías: el gasto hormiga, las suscripciones zombi, lo que se escapa sin nombre. El número que más sorprende en una reunión — y el más fácil de recuperar.", BODY)]
    return [_eyebrow("Lo que se escapa sin nombre"), _box(inner,bg=colors.HexColor("#FBECE6"),brd="#E3C5B8"), Spacer(1,10*mm)]

# ---------- 3. Tu número y los 4 caminos ----------
def seccion_numero_caminos(exp):
    if not exp or not exp.get("numero_libertad"): return []
    S=[_eyebrow("Lo que quieres vs lo que tu dinero permite"), Paragraph("Tu número, y cómo llegar a él", H)]
    pen = exp.get("gasto_propio") is not None
    S.append(Paragraph('<font size=30 color="#1A1A17"><b>%s €</b></font>'%_eur(exp["numero_libertad"]), BODY))
    S.append(Paragraph("El capital que necesitas para vivir de rentas, <b>neto de tu pensión</b>. Lo tienes cubierto al <b>%s%%</b>%s." % (
        exp.get("pct_cubierto",0), (" · te falta %s €"%_eur(exp.get("brecha_renta"))) if exp.get("brecha_renta",0)>0 else ""), BODY))
    if exp.get("pension_cubre"):
        S.append(Paragraph("<b>Tu pensión ya cubre la vida que quieres.</b> El trabajo no es llegar: es proteger y optimizar.", BODY))
        return [KeepTogether(S), Spacer(1,10*mm)]
    cm=exp.get("caminos")
    if cm:
        def via(t,b,d): return _box([Paragraph("<b>%s</b>"%t,ParagraphStyle("vt",fontName="Helvetica-Bold",fontSize=9,textColor=GOLD,spaceAfter=2)),
                                     Paragraph(b,ParagraphStyle("vb",fontName="Helvetica-Bold",fontSize=14,textColor=INK,spaceAfter=2)),
                                     Paragraph(d,SM)],bg=colors.white,brd="#E5E0D5")
        S.append(Spacer(1,4))
        S.append(via("Camino 1 · Ahorra más", ("Ya ahorras suficiente" if cm.get("ahorro_extra",0)<=0 else "+%s €/mes"%_eur(cm["ahorro_extra"])), "Sobre lo que ya ahorras, para llegar en tu plazo."))
        S.append(Spacer(1,5))
        rn=cm.get("rentabilidad_necesaria")
        S.append(via("Camino 2 · Haz rentar mejor", ("No basta con rentabilidad" if rn is None else "%s%% anual"%rn), "Manteniendo tu ahorro actual."))
        S.append(Spacer(1,5))
        S.append(via("Camino 3 · Ajusta el objetivo", "%s €/mes"%_eur(cm.get("objetivo_alcanzable")), "La vida que SÍ es sostenible con lo que haces hoy."))
        S.append(Spacer(1,5))
        pr=cm.get("plan_recomendado",{})
        rec = "Mantén el rumbo: ya llegas" if pr.get("ya_llega") else "Ahorra +%s €/mes · objetivo %s €/mes"%(_eur(pr.get("extra")),_eur(pr.get("objetivo")))
        S.append(via("★ Camino 4 · El plan que recomendamos", rec, "La mezcla realista, sin números mágicos. Es lo que diseñamos contigo."))
    return [KeepTogether(S[:4]), Spacer(1,3*mm)]+S[4:]+[Spacer(1,10*mm)]

# ---------- 4. Patrimonio productivo vs dormido ----------
def seccion_patrimonio(pat):
    if not pat or pat.get("pct_productivo") is None: return []
    prod=pat["pct_productivo"]; dorm=100-prod
    inner=[Paragraph("Tu patrimonio: ¿trabaja o duerme?", H),
           Paragraph('<font size=26 color="#1D6F42"><b>%s%%</b></font><font size=11 color="#6B7280"> produce o crece</font>  ·  <font size=18 color="#6B7280"><b>%s%%</b> peso muerto</font>'%(prod,dorm), BODY)]
    if pat.get("equity_vivienda",0)>0 and pat.get("pct_vivienda",0)>=50:
        inner.append(Paragraph("Tu capital propio en la vivienda (ya neto de hipoteca) es <b>%s €</b> y está dormido: no renta, no se vende a trozos y cuesta mantener. Es la enfermedad patrimonial española — y la conversación es cómo despertarlo." % _eur(pat["equity_vivienda"]), BODY))
    return [_eyebrow("Cuánto de lo que tienes trabaja para ti"), _box(inner), Spacer(1,10*mm)]

# ---------- 5. Esfuerzo financiero y avalancha ----------
def seccion_esfuerzo(deu):
    if not deu or not deu.get("deuda_total"): return []
    esf=deu.get("esfuerzo_financiero")
    colhex = "#9A3B2E" if (esf or 0)>=35 else ("#B45309" if (esf or 0)>=20 else "#1D6F42")
    inner=[Paragraph("Tu deuda: esfuerzo y por dónde empezar", H)]
    if esf is not None:
        inner.append(Paragraph('Esfuerzo financiero: <font color="%s"><b>%s%%</b></font> de tu ingreso en cuotas <font size=8 color="#6B7280">(sano &lt;20%%, riesgo &gt;35%%)</font>'%(colhex, esf), BODY))
    inner.append(Paragraph("Coste medio de tu deuda: <b>%s%%</b>."%deu.get("coste_medio_deuda",0), BODY))
    av=deu.get("avalancha")
    if av: inner.append(Paragraph("Empieza por aquí (método avalancha): <b>%s</b> al %s%%."%(av.get("tipo"),av.get("interes")), BODY))
    if deu.get("tiene_revolving"):
        inner.append(Paragraph('<font color="#9A3B2E"><b>Tienes una tarjeta revolving</b></font> — el crédito más caro que existe. Amortizarla es la mejor inversión posible: ningún fondo da ese retorno garantizado.', BODY))
    return [_eyebrow("Munición para tu deuda"), _box(inner), Spacer(1,10*mm)]

# ---------- 6. Familia y protección ----------
def seccion_familia(fam):
    if not fam or not fam.get("n_dependientes"): return []
    inner=[Paragraph("Tu familia, en la línea del tiempo", H)]
    if fam.get("proteccion_recomendada",0)>0:
        inner.append(Paragraph("Si te faltaras hoy, sostener a los tuyos hasta su independencia cuesta ~<b>%s €</b>. ¿Está cubierto con seguro o patrimonio líquido? Es la conversación de protección que más tranquilidad da tenerla a tiempo."%_eur(fam["proteccion_recomendada"]), BODY))
    if fam.get("proximo_hito_uni_anios") is not None:
        inner.append(Paragraph("Próximo gran hito: la universidad, en <b>%s años</b>. Empezar a apartar hoy convierte un golpe en un plan."%fam["proximo_hito_uni_anios"], BODY))
    if fam.get("anio_libera_flujo",0)>0:
        inner.append(Paragraph("En <b>%s años</b>, cuando el menor se independice, recuperas capacidad de ahorro: tenlo en el plan."%fam["anio_libera_flujo"], BODY))
    return [_eyebrow("Quién depende de ti"), _box(inner), Spacer(1,10*mm)]

# ---------- 7. Perfil de riesgo ----------
_PLAB={1:"Muy conservador",2:"Conservador",3:"Equilibrado",4:"Dinámico",5:"Muy dinámico"}
def seccion_perfil(perfil_riesgo, rv_sugerido=None):
    if not perfil_riesgo: return []
    inner=[Paragraph("Tu perfil de riesgo", H),
           Paragraph('Te corresponde un perfil <b>%s</b> (nivel %s de 5)%s. Lo calculamos con la regla prudente: el <b>mínimo</b> entre lo que toleras emocionalmente y lo que tu situación te permite — porque invertir por encima de lo que puedes perder es lo que arruina.'%(
               _PLAB.get(perfil_riesgo,""), perfil_riesgo, (", con una exposición a bolsa orientativa del <b>%s%%</b>"%rv_sugerido) if rv_sugerido else ""), BODY)]
    return [_eyebrow("Cuánto riesgo te conviene"), _box(inner), Spacer(1,10*mm)]


def secciones_financieras_v3(res):
    """res = dict del endpoint /api/diag-v3 (ingresos, gastos, deuda, cartera, patrimonio, familia, expectativas, agregado).
    Devuelve la lista de flowables de las 7 secciones (las que tengan datos)."""
    out=[]
    out += seccion_precio_hora(res.get("ingresos",{}))
    out += seccion_fuga(res.get("gastos",{}))
    out += seccion_numero_caminos(res.get("expectativas",{}))
    out += seccion_patrimonio(res.get("patrimonio",{}))
    out += seccion_esfuerzo(res.get("deuda",{}))
    out += seccion_familia(res.get("familia",{}))
    pr=(res.get("agregado",{}).get("veredicto",{}) or {}).get("perfil_riesgo") or res.get("perfil_riesgo")
    out += seccion_perfil(pr)
    return out


if __name__ == "__main__":
    import motor_financiero_v3 as m
    from reportlab.platypus import SimpleDocTemplate
    ing=m.analizar_ingresos([{"tipo":"nomina","importe":2500,"horas":45},{"tipo":"alquiler","importe":400}])
    gas=m.analizar_gastos(2200,[{"tipo":"vivienda","importe":800},{"tipo":"ocio","importe":300}])
    deu=m.analizar_deuda([{"tipo":"revolving","saldo":4000,"cuota":180},{"tipo":"hipoteca","saldo":150000,"cuota":650}], ing.get("ingreso_mensual"))
    car=m.analizar_cartera({"liquidez":30000,"rv":8000}, gas.get("gasto_mensual"),20,"agr")
    pat=m.analizar_patrimonio(300000,0,150000,car.get("inversiones_liquidas",0),deu.get("deuda_total",0))
    fam=m.analizar_familia([4,16])
    exp=m.analizar_expectativas(3000,1100,car.get("inversiones_liquidas",0),300,15,5.5,8,0)
    res={"ingresos":ing,"gastos":gas,"deuda":deu,"cartera":car,"patrimonio":pat,"familia":fam,"expectativas":exp,"perfil_riesgo":3}
    doc=SimpleDocTemplate("/tmp/secciones_v3_demo.pdf",pagesize=A4,topMargin=18*mm,bottomMargin=18*mm,leftMargin=25*mm,rightMargin=25*mm)
    doc.build(secciones_financieras_v3(res))
    import os; print("PDF demo:", os.path.getsize("/tmp/secciones_v3_demo.pdf"), "bytes,", "secciones:", len(secciones_financieras_v3(res)))
