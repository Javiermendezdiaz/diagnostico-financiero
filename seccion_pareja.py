# -*- coding: utf-8 -*-
"""PARTE 1 · LO ESENCIAL del libro de pareja: cinco paginas que se leen solas.

  1. VUESTRA CIFRA      — lo que os separa de no depender de un sueldo (hogar), frente a hogares de vuestra edad.
  2. LA FRICCION        — vuestra temperatura y las tres preguntas donde mas chocais.
  3. EL ESFUERZO        — (pagina-imagen) a quien le cuesta mas el reparto (la pone build_couple).
  4. VUESTROS LUNES     — el mismo lenguaje de la web, con las cifras del hogar.
  5. POR DONDE EMPEZAR  — vuestra primera conversacion, vuestra primera decision y la sesion con Adapta.

Todas las cifras salen del MISMO motor que el informe individual (seccion_apertura).
Failsafe: si algo falla, devuelve [] y el libro sale como antes.
"""
import seccion_apertura as sa

VERDE, AMBAR, ROJO = sa.VERDE, sa.AMBAR, sa.ROJO


_PLURAL = (("Tu plan de hoy", "Vuestro plan de hoy"), ("Recortas", "Recortáis"), ("recortas", "recortáis"),
           ("Ahorras", "Ahorráis"), ("ahorras", "ahorráis"), ("Paras", "Paráis"), ("paras", "paráis"))


def plural(t):
    """Las etiquetas del motor hablan de tu; el libro de pareja habla de vosotros."""
    for a, b in _PLURAL:
        t = t.replace(a, b)
    return t


def apertura_pareja(nA, nB, dA, dB, hogar, rA, rB, compat, divs, friccion, esfuerzo_img=None):
    try:
        return _apertura_pareja(nA, nB, dA, dB, hogar, rA, rB, compat, divs, friccion, esfuerzo_img)
    except Exception as e:
        import sys
        sys.stderr.write("[apertura pareja] omitida: %s\n" % e)
        return []


def _apertura_pareja(nA, nB, dA, dB, hogar, rA, rB, compat, divs, friccion, esfuerzo_img):
    import report_book as rb
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, PageBreak, Flowable as _Fl
    St, box, eur = rb.St, rb._box, rb._eur
    INK, GREY, FB = rb.INK, rb.GREY, rb.FB
    _n = [0]

    def _id(p):
        _n[0] += 1
        return "apj%s%d" % (p, _n[0])

    def texto(t, tam=10.5, color=None):
        return Paragraph(t, St(_id("t"), fontSize=tam, leading=tam + 4.5, textColor=(color or INK)))

    def rotulo(t, color=GREY):
        col = colors.HexColor(color) if isinstance(color, str) else color
        return Paragraph(t, St(_id("r"), fontSize=8.5, leading=11, textColor=col, fontName=FB))

    def cifra(t, color=ROJO, tam=56):
        return Paragraph('<font size=%d color="%s"><b>%s</b></font>' % (tam, color, t),
                         St(_id("c"), fontSize=tam, leading=tam + 5, spaceBefore=2, spaceAfter=2))

    H1 = St(_id("h1"), fontSize=24, leading=29, textColor=INK, fontName="Lora-Bold", spaceAfter=6)

    class _Progreso(_Fl):
        def __init__(self, pct, izq, der, ancho=160 * mm, alto=9 * mm):
            _Fl.__init__(self); self.pct = max(0.0, min(100.0, float(pct or 0)))
            self.izq, self.der, self.w, self.h = izq, der, ancho, alto
        def wrap(self, aw, ah): return self.w, self.h + 11 * mm
        def draw(self):
            c = self.canv; y0 = 8 * mm
            c.setFillColor(colors.HexColor("#ECE7DA")); c.roundRect(0, y0, self.w, self.h, self.h / 2, fill=1, stroke=0)
            fw = max(self.h, self.w * self.pct / 100.0)
            c.setFillColor(colors.HexColor("#C9962B")); c.roundRect(0, y0, fw, self.h, self.h / 2, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#1A1A17")); c.setFont("Poppins-Bold", 10)
            c.drawString(fw + 3 * mm, y0 + self.h / 2 - 3.5, "%d%%" % round(self.pct))
            c.setFont("Poppins", 8.5); c.setFillColor(colors.HexColor("#6B7280"))
            c.drawString(0, 1.5 * mm, self.izq); c.drawRightString(self.w, 1.5 * mm, self.der)

    def kpis(celdas):
        fila = [[Paragraph(r_, St(_id("kr"), fontSize=8.5, leading=11, textColor=colors.HexColor("#6B7280"), fontName=FB)),
                 Paragraph("<b>%s</b>" % v_, St(_id("kv"), fontSize=22, leading=27, textColor=colors.HexColor(c_), fontName=FB, spaceBefore=3))]
                for r_, v_, c_ in celdas]
        w = 160.0 / len(fila)
        return Table([fila], colWidths=[w * mm] * len(fila),
                     style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3EFE4")),
                            ("LINEBEFORE", (1, 0), (-1, -1), 5, rb.PAGEBG),
                            ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 11),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 13), ("LINEABOVE", (0, 0), (-1, 0), 2.2, rb.AMARILLO)])

    out = []
    exp = sa.datos_expectativas(hogar)
    if not exp or not exp.get("numero_libertad"):
        return []
    N = float(exp["numero_libertad"])
    cap = float(hogar.get("inversiones_liquidas") or 0) + float(hogar.get("colchon_liquido") or 0)
    falta = max(0.0, N - cap)
    pct = exp.get("pct_cubierto", 0)
    lunes_ok = bool(sa.bloque_lunes(hogar, exp, vosotros=True))
    n_pag = 5 if (esfuerzo_img and lunes_ok) else (4 if (esfuerzo_img or lunes_ok) else 3)
    _n_txt = {3: "TRES", 4: "CUATRO", 5: "CINCO"}[n_pag]

    # ================================================== 1 · VUESTRA CIFRA
    out += [Spacer(1, 8 * mm),
            Paragraph("LO ESENCIAL · VUESTRO DIAGNÓSTICO EN %s PÁGINAS" % _n_txt,
                      St(_id("eb"), fontSize=8.5, leading=11, textColor=rb.ACC, fontName=FB, spaceAfter=3)),
            Paragraph("Esto es lo que os separa de no depender de un sueldo", H1),
            Spacer(1, 3 * mm),
            cifra(eur(falta) if falta > 0 else "Ya habéis llegado", ROJO if falta > 0 else VERDE, 56),
            Spacer(1, 2 * mm),
            texto("El Número de Libertad de vuestro hogar es <b>%s</b>: el capital que sostiene la vida de los dos sin "
                  "depender de ningún sueldo (ya descuenta vuestras pensiones). Hoy tenéis <b>%s</b> entre lo invertido y lo "
                  "líquido. Lo tenéis cubierto al <b>%s%%</b>." % (eur(N), eur(cap), pct), 12),
            Spacer(1, 6 * mm),
            _Progreso(pct, "Hoy · %s" % eur(cap), "Vuestra libertad · %s" % eur(N)),
            Spacer(1, 5 * mm),
            kpis([("COMPATIBILIDAD", "%d<font size=10 color='#6B7280'>/100</font>" % compat, "#1A1A17"),
                  ("NÚMERO DE LIBERTAD", eur(N), "#1A1A17"),
                  ("YA CUBIERTO", "%s%%" % pct, "#1A1A17")])]
    try:
        _ed = max(float(dA.get("edad") or 0), float(dB.get("edad") or 0))
        _fe = sa.frente_a_tu_edad({"edad": _ed, "patrimonio": hogar.get("patrimonio")})
    except Exception:
        _fe = None
    if _fe:
        if _fe["encima"]:
            _ft = ("<b>Frente a los hogares como el vuestro:</b> vuestro patrimonio neto (%s) es <b>%s veces</b> el del "
                   "hogar típico de %s (%s). Más de la mitad de esos hogares tiene menos que vosotros."
                   % (eur(_fe["pat"]), ("%.1f" % _fe["ratio"]).replace(".", ","), _fe["tramo"], eur(_fe["mediana"])))
        else:
            _ft = ("<b>Frente a los hogares como el vuestro:</b> vuestro patrimonio neto (%s) está por debajo del hogar "
                   "típico de %s (%s). Es justo la distancia que vuestro plan está pensado para cerrar."
                   % (eur(_fe["pat"]), _fe["tramo"], eur(_fe["mediana"])))
        out += [Spacer(1, 4 * mm), texto(_ft, 10, INK),
                Paragraph("Fuente: " + sa.EFF_FUENTE + ". Edad de referencia: la del mayor de los dos.",
                          St(_id("ef"), fontSize=7.8, leading=10, textColor=GREY, spaceBefore=2))]
    out += [Spacer(1, 6 * mm),
            sa.cta_sesion("¿Queréis bajar esta cifra con alguien al lado?" if falta > 0 else "¿Y ahora, qué hacéis con lo conseguido?",
                          ("En 30 minutos convertimos vuestro diagnóstico en vuestras primeras decisiones, con números, "
                           "fechas y un reparto que os parezca justo a los dos." if falta > 0 else
                           "En 30 minutos vemos cómo protegerlo, repartirlo con justicia y decidir qué hacer con lo que sobra.")
                          + " Os descontamos el importe íntegro de este informe.",
                          qr_mm=18, rotulo="VUESTRA SESIÓN CON ADAPTA"),
            PageBreak()]

    # ================================================== 2 · LA FRICCION
    idx, n_tot, n_conf = friccion if friccion else (0, 0, 0)
    etq = "Fricción baja" if idx < 25 else ("Fricción moderada" if idx < 50 else "Fricción alta")
    col = VERDE if idx < 25 else (AMBAR if idx < 50 else ROJO)
    out += [Spacer(1, 8 * mm),
            Paragraph("Dónde no estáis de acuerdo (aunque no lo sepáis)", H1),
            texto("El dinero rara vez rompe por cuánto hay. Rompe por cómo lo vive cada uno, y no se habla. "
                  "Esto es lo que vuestras respuestas, cruzadas, ponen sobre la mesa.", 12),
            Spacer(1, 5 * mm),
            kpis([("VUESTRA TEMPERATURA", "%d<font size=10 color='#6B7280'>/100</font>" % idx, col),
                  ("PUNTOS COMPARADOS", "%d" % n_tot, "#1A1A17"),
                  ("CHOCAN DE FRENTE", "%d" % n_conf, ROJO if n_conf else VERDE)]),
            Spacer(1, 2 * mm),
            texto("<b>%s.</b> No mide quién tiene razón: mide cuánto tenéis por hablar." % etq, 10.5, GREY),
            Spacer(1, 4 * mm)]
    if divs:
        out += [rotulo("LAS TRES PREGUNTAS DONDE MÁS CHOCÁIS"), Spacer(1, 2 * mm)]
        for d in divs[:3]:
            fil = Table([[Paragraph("<b>%s</b>" % nA, St(_id("na"), fontSize=10, leading=13, textColor=colors.HexColor("#B8860B"), fontName=FB)),
                          Paragraph(d["A"], St(_id("ra"), fontSize=10, leading=13.5, textColor=INK))],
                         [Paragraph("<b>%s</b>" % nB, St(_id("nb"), fontSize=10, leading=13, textColor=colors.HexColor("#3F3F46"), fontName=FB)),
                          Paragraph(d["B"], St(_id("rb"), fontSize=10, leading=13.5, textColor=INK))]],
                        colWidths=[24 * mm, 126 * mm],
                        style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("VALIGN", (0, 0), (-1, -1), "TOP")])
            out += [box([Paragraph(d["texto"], St(_id("q"), fontSize=11, leading=14.5, textColor=INK, fontName=FB, spaceAfter=4)), fil],
                        "#FBF4E4", "#B45309", ancho=160 * mm), Spacer(1, 3 * mm)]
        out += [texto("En la Parte 2 tenéis todos vuestros focos, el coste de no hablarlos y un guion para hacerlo sin discutir.", 10.5, GREY)]
    else:
        out += [box([texto("Apenas hay divergencias marcadas: vuestra forma de ver el dinero está muy alineada. "
                            "Vuestro trabajo es de afinación, no de reconciliación.", 11.5, INK)], "#EAF3EC", VERDE, ancho=160 * mm)]
    out += [PageBreak()]

    # ================================================== 3 · EL ESFUERZO (pagina-imagen)
    if esfuerzo_img:
        out += [rb.FullBleedImage(rb._claro(esfuerzo_img)), PageBreak()]

    # ================================================== 4 · VUESTROS LUNES
    if lunes_ok:
        out += sa.bloque_lunes(hogar, exp, vosotros=True)

    # ================================================== 5 · POR DONDE EMPEZAR
    pal = sa.tres_palancas(exp) if falta > 0 else []
    out += [Spacer(1, 8 * mm), Paragraph("Por dónde empezar", H1),
            texto("Tenéis todo el detalle en las páginas que siguen. Pero si esta semana solo hacéis dos cosas, que sean estas.", 12),
            Spacer(1, 5 * mm)]
    if divs:
        d = divs[0]
        out += [box([rotulo("1 · VUESTRA PRIMERA CONVERSACIÓN", ROJO),
                     Paragraph("Treinta minutos, sin móviles. Sobre esto: «%s»" % d["texto"],
                               St(_id("p1"), fontSize=13, leading=18, textColor=INK, spaceBefore=4)),
                     texto("%s respondió «%s» y %s, «%s». Primero uno explica su porqué y luego el otro, sin interrumpir. "
                           "No se trata de ganar, sino de entender." % (nA, d["A"].rstrip("."), nB, d["B"].rstrip(".")), 10.5, GREY)],
                    "#FBEDEC", ROJO, ancho=160 * mm), Spacer(1, 3 * mm)]
    if pal:
        filas = []
        for i, e in enumerate(pal, 1):
            try:
                if e.get("_tipo") == "acerca":
                    _g = float(e.get("_gana") or 0)
                    _q = "llegáis %s antes" % (("%d años" % round(_g)) if round(_g) != 1 else "1 año")
                else:
                    _q = "%s menos de capital necesario" % eur(abs(float(e.get("delta") or 0)))
            except Exception:
                _q = ""
            filas.append(Paragraph("<b>%s.</b> %s%s" % (i, plural(e.get("escenario", "")), (" · <font color='%s'><b>%s</b></font>" % (VERDE, _q)) if _q else ""),
                                   St(_id("p2"), fontSize=11.5 if i == 1 else 10.5, leading=16 if i == 1 else 14.5, textColor=INK, spaceBefore=3)))
        out += [box([rotulo("2 · VUESTRAS DECISIONES DE DINERO, POR ORDEN DE IMPACTO", VERDE)] + filas +
                    [texto("Empezad por la primera: es la que más mueve vuestra libertad.", 10, GREY)],
                    "#EAF3EC", VERDE, ancho=160 * mm)]
    elif falta <= 0:
        out += [box([rotulo("2 · VUESTRA PRIMERA DECISIÓN DE DINERO", VERDE),
                     Paragraph("<b>Proteger lo que ya habéis conseguido.</b>",
                               St(_id("p2b"), fontSize=13, leading=18, textColor=INK, spaceBefore=4)),
                     texto("Vuestro capital y vuestras pensiones ya cubren la vida de los dos. Lo que queda es que siga siendo así "
                           "pase lo que pase a uno de los dos: a nombre de quién está cada cosa, qué ocurre si uno falta y qué hacéis "
                           "con lo que sobra. Lo tenéis en las páginas que siguen.", 10.5, GREY)],
                    "#EAF3EC", VERDE, ancho=160 * mm)]
    out += [Spacer(1, 8 * mm),
            sa.cta_sesion("Si queréis ir más rápido y sin discutir",
                          "En una <b>sesión estratégica de 30 minutos</b> con los dos convertimos este diagnóstico en un sistema "
                          "de reparto, vuestras tres cuentas y vuestras primeras decisiones. Os descontamos el importe íntegro de este informe.",
                          qr_mm=28, rotulo="VUESTRA SESIÓN CON ADAPTA"),
            PageBreak()]
    return out
