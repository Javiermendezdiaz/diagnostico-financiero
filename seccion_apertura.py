# -*- coding: utf-8 -*-
"""APERTURA EJECUTIVA del libro Adapta — las cuatro primeras paginas.

POR QUE EXISTE
--------------
El informe tiene 84 paginas y abre explicando el metodo. El lector decide en
los primeros 20 segundos si esto vale lo que ha pagado, y en esos 20 segundos
no le hemos ensenado todavia ni un euro.

Esta seccion pone el dinero delante. No calcula NADA nuevo: todas las cifras
ya existen en el motor y en `extras`. Lo unico que hace es sacarlas del
parrafo donde estaban enterradas y ponerlas en grande al principio.

LAS CUATRO PAGINAS
------------------
  1. LA CIFRA      — lo que se te escapa al ano, y lo que suma en 10.
  2. EL CUADRO     — semaforo de tus 12 dimensiones. Se lee de un vistazo.
  3. LAS PALANCAS  — las 3 decisiones que mas mueven tu numero, en euros.
  4. EL FOCO       — tu eslabon debil, tu primer paso, y el puente a Adapta.

PRINCIPIOS DE MAQUETA (deliberados)
-----------------------------------
  · Tres niveles de jerarquia y solo tres: titular / cifra grande / explicacion.
  · Una idea por bloque, maximo cuatro lineas de texto seguidas.
  · Los numeros nunca dentro del parrafo: siempre en cuerpo grande y aislados.
  · Aire. El vacio es lo que separa un informe premium de un documento.

DISENO DEL MODULO
-----------------
Modulo separado a proposito. `report_book.py` solo necesita dos lineas (un
import y una llamada), asi que la mejora se puede reaplicar sobre cualquier
version del libro sin riesgo de pisar otros cambios.

Failsafe total: si falta cualquier dato, la pieza correspondiente se omite;
si falla todo, devuelve [] y el libro sale exactamente como hoy.
"""

VERSION = "1.1"

# Paleta semaforo, alineada con _sevcol() de report_book (score alto = peor).
VERDE, OCRE, AMBAR, ROJO = "#1D6F42", "#B8860B", "#C2710C", "#9A3B2E"


# ------------------------------------------------------------------ MOTOR
def datos_expectativas(datos):
    """Ejecuta el motor con los MISMOS inputs que usa el resto del libro.

    Es la UNICA fuente del Numero de Libertad. Antes habia dos rutas de
    calculo (esta y un gasto*12*25 en fi_metrics) que daban cifras distintas
    al mismo cliente en paginas distintas del mismo informe.

    test_numeros.py comprueba que fi_metrics y esta funcion coinciden: si
    alguien vuelve a separarlas, salta en rojo.
    """
    try:
        import motor_financiero_v3 as mfv3
    except Exception:
        return None
    d = datos or {}

    def _f(k, defecto=0.0):
        v = d.get(k)
        try:
            return float(v) if v not in (None, "") else defecto
        except Exception:
            return defecto

    ideal = _f("coste_vida_ideal")
    gasto = ideal if ideal > 0 else _f("gasto_mensual")
    if gasto <= 0:
        return None
    pension = _f("pension_estimada")
    capital = _f("inversiones_liquidas") + _f("colchon_liquido")
    ahorro = _f("ahorro_mensual")
    try:
        edad = int(_f("edad"))
    except Exception:
        edad = 0
    try:
        er = int(_f("edad_retiro_ideal")) or None
    except Exception:
        er = None
    if er and 0 < edad < er:
        horizonte = max(1, er - edad)
    else:
        horizonte = max(1, 67 - edad) if 0 < edad < 67 else 15
    try:
        return mfv3.analizar_expectativas(gasto, pension, capital, ahorro,
                                          horizonte, 5.0,
                                          edad=(edad if 0 < edad < 100 else None))
    except Exception:
        return None


def tres_palancas(exp):
    """Las 3 decisiones que MAS bajan el numero, ordenadas por euros.

    Sale de `exp["escenarios"]`, que el motor ya calcula. Descarta el escenario
    base (delta 0) y devuelve como mucho 3, de mayor a menor impacto.
    """
    escenarios = (exp or {}).get("escenarios") or []
    reales = []
    for e in escenarios:
        try:
            delta = float(e.get("delta") or 0)
        except Exception:
            continue
        if delta < 0:                      # solo lo que ACERCA la meta
            reales.append((delta, e))
    reales.sort(key=lambda x: x[0])        # mas negativo primero
    return [e for _, e in reales[:3]]


def _estado(score):
    """(etiqueta, color, simbolo) para el semaforo. Score alto = peor."""
    try:
        s = float(score)
    except Exception:
        return ("—", "#6B7280", "–")
    if s < 30:
        return ("Sólido", VERDE, "●")
    if s < 51:
        return ("Con margen", OCRE, "●")
    if s < 76:
        return ("A vigilar", AMBAR, "▲")
    return ("Crítico", ROJO, "▲")


# ------------------------------------------------------------------ SECCION
def apertura(salud, fi, datos, extras=None, p=None):
    """Devuelve los flowables de las paginas de apertura. [] si no hay datos."""
    try:
        return _apertura(salud, fi, datos, extras, p)
    except Exception as err:
        import sys
        sys.stderr.write("[apertura] omitida: %s\n" % err)
        return []


def _apertura(salud, fi, datos, extras, p):
    import report_book as rb                    # import tardio: evita el ciclo
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, PageBreak

    St, box, eur = rb.St, rb._box, rb._eur
    INK, GREY, FB = rb.INK, rb.GREY, rb.FB
    d = datos or {}
    ex = extras or {}
    exp = datos_expectativas(d)
    out = []
    _n = [0]

    def _id(pre):
        _n[0] += 1
        return "%s%d" % (pre, _n[0])

    # ---------------------------------------------------- ladrillos de maqueta
    def cifra(txt, color=ROJO, tam=44):
        """Nivel 2 de la jerarquia: el numero, aislado y grande."""
        return Paragraph('<font size=%d color="%s"><b>%s</b></font>' % (tam, color, txt),
                         St(_id("apc"), fontSize=tam, leading=tam + 5,
                            spaceBefore=2, spaceAfter=2))

    def rotulo(txt, color=GREY):
        """Nivel 1: el rotulo pequeno en versalitas que da contexto al numero."""
        col = colors.HexColor(color) if isinstance(color, str) else color
        return Paragraph(txt, St(_id("apr"), fontSize=8.5, leading=11,
                                 textColor=col, fontName=FB))

    def texto(txt, tam=10.5, color=None):
        """Nivel 3: la explicacion. Corta. Nunca mas de cuatro lineas."""
        return Paragraph(txt, St(_id("apt"), fontSize=tam, leading=tam + 4.5,
                                 textColor=(color or INK)))

    def regla(ancho=40):
        return Table([[""]], colWidths=[ancho * mm],
                     style=[("LINEBELOW", (0, 0), (-1, -1), 2.5, rb.AMARILLO)])

    # =========================================================== PAGINA 1
    out.append(Paragraph("TU DIAGNÓSTICO EN CUATRO PÁGINAS",
                         St("ap_eyebrow", fontSize=8.5, leading=11, textColor=rb.ACC,
                            fontName=FB, spaceAfter=3)))

    brecha = ex.get("brecha") or {}
    try:
        br_mes = float(brecha.get("brecha_mes") or 0)
        br_anual = float(brecha.get("brecha_anual") or 0)
    except Exception:
        br_mes = br_anual = 0.0

    if br_anual > 0:
        # EL TITULAR ES EL DINERO. No el metodo, no la bienvenida.
        out += [Paragraph("Esto es lo que te separa, cada año, de la vida que dijiste querer",
                          rb.h_sec),
                cifra(eur(br_anual)),
                texto("Son <b>%s al mes</b> de distancia entre la vida que tienes y la que "
                      "describiste en tus respuestas. Sale de tus propios números." % eur(br_mes)),
                Spacer(1, 6 * mm),
                box([rotulo("SI DENTRO DE DIEZ AÑOS EL CUADRO SIGUE IGUAL", ROJO),
                     cifra(eur(br_anual * 10), ROJO, 30),
                     texto("Acumulado sobre tu brecha actual, sin capitalizar. "
                           "Es el precio de aplazarlo.", 8.5, GREY)],
                    "#FBEDEC", ROJO, ancho=160 * mm)]
    elif exp and exp.get("numero_libertad"):
        N = float(exp["numero_libertad"])
        try:
            pat = float(d.get("patrimonio") or 0)
        except Exception:
            pat = 0.0
        falta = max(0.0, N - pat)
        out += [Paragraph("Esto es lo que te separa de no depender de un sueldo", rb.h_sec),
                cifra(eur(falta) if falta > 0 else "Ya has llegado",
                      ROJO if falta > 0 else VERDE),
                texto("Tu Número de Libertad es <b>%s</b> y hoy tienes <b>%s</b>. "
                      "Lo tienes cubierto al <b>%s%%</b>."
                      % (eur(N), eur(pat), exp.get("pct_cubierto", 0)))]
    else:
        return []      # sin cifra que ensenar, no abrimos con humo

    # --- tira de indicadores: la foto entera en una linea
    kpis = []
    try:
        sv = rb._sal100(salud)
        col = VERDE if sv >= 60 else (AMBAR if sv >= 40 else ROJO)
        kpis.append(("TU NOTA", "%d<font size=10 color='#6B7280'>/100</font>" % sv, col))
    except Exception:
        pass
    if exp and exp.get("numero_libertad"):
        kpis.append(("NÚMERO DE LIBERTAD", eur(exp["numero_libertad"]), "#1A1A17"))
        kpis.append(("YA CUBIERTO", "%s%%" % exp.get("pct_cubierto", 0), "#1A1A17"))
    try:
        tasa = float(fi[2]) if fi and fi[2] is not None else None
        if tasa is not None and len(kpis) < 3:
            kpis.append(("TASA DE AHORRO", "%.0f%%" % tasa,
                         VERDE if tasa >= 20 else (AMBAR if tasa >= 10 else ROJO)))
    except Exception:
        pass

    if kpis:
        fila = []
        for rot, val, col in kpis[:3]:
            fila.append([Paragraph(rot, St(_id("apkl"), fontSize=8, leading=10,
                                           textColor=colors.HexColor("#6B7280"), fontName=FB)),
                         Paragraph("<b>%s</b>" % val,
                                   St(_id("apkv"), fontSize=19, leading=23,
                                      textColor=colors.HexColor(col), fontName=FB, spaceBefore=1))])
        while len(fila) < 3:
            fila.append([Paragraph("", rb.small)])
        out += [Spacer(1, 8 * mm),
                Table([fila], colWidths=[53 * mm, 53 * mm, 54 * mm],
                      style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 2),
                             ("TOPPADDING", (0, 0), (-1, -1), 9),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                             ("LINEABOVE", (0, 0), (-1, 0), 0.5, rb.LINE),
                             ("LINEBELOW", (0, 0), (-1, -1), 0.5, rb.LINE)])]
    out.append(PageBreak())

    # =========================================================== PAGINA 2
    # EL CUADRO: las 12 dimensiones como scorecard. Se lee sin leer.
    if isinstance(p, dict) and p:
        filas = [[Paragraph("<b>ÁREA</b>", St("ap_th1", fontSize=8, leading=10,
                                              textColor=colors.HexColor("#6B7280"), fontName=FB)),
                  Paragraph("<b>ESTADO</b>", St("ap_th2", fontSize=8, leading=10,
                                                textColor=colors.HexColor("#6B7280"), fontName=FB)),
                  Paragraph("<b>PUNTO MÁS FRÁGIL</b>", St("ap_th3", fontSize=8, leading=10,
                                                          textColor=colors.HexColor("#6B7280"), fontName=FB))]]
        estilo = [("LINEBELOW", (0, 0), (-1, -1), 0.4, rb.LINE),
                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("TOPPADDING", (0, 0), (-1, -1), 7),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                  ("LEFTPADDING", (0, 0), (-1, -1), 8)]
        # Orden: lo peor arriba. Un informe que decide no ordena por numero de capa.
        capas = sorted(p.items(), key=lambda kv: -(kv[1].get("score") or 0))
        for i, (code, v) in enumerate(capas, 1):
            etq, col, sim = _estado(v.get("score"))
            filas.append([
                Paragraph(v.get("nombre", code),
                          St(_id("apsn"), fontSize=9.5, leading=12.5, textColor=INK)),
                Paragraph('<font color="%s">%s</font>  <font color="%s"><b>%s</b></font>'
                          % (col, sim, col, etq),
                          St(_id("apse"), fontSize=9.5, leading=12.5)),
                Paragraph(v.get("peor") or "—",
                          St(_id("apsp"), fontSize=9, leading=12, textColor=GREY))])
            if etq == "Crítico":
                estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FBEDEC")))
        criticas = sum(1 for _, v in capas if _estado(v.get("score"))[0] == "Crítico")
        solidas = sum(1 for _, v in capas if _estado(v.get("score"))[0] == "Sólido")
        out += [Paragraph("Tu cuadro completo, de un vistazo", rb.h_sec),
                texto("Doce dimensiones medidas. Ordenadas de la más frágil a la más sólida — "
                      "no por orden de capítulo."),
                Spacer(1, 5 * mm),
                Table(filas, colWidths=[62 * mm, 44 * mm, 54 * mm], style=estilo),
                Spacer(1, 5 * mm),
                texto("<b>%d</b> en estado crítico · <b>%d</b> sólidas. "
                      "Las dos primeras filas son las que sostienen a todas las demás: "
                      "por ahí se empieza." % (criticas, solidas), 10, GREY),
                PageBreak()]

    # =========================================================== PAGINA 3
    palancas = tres_palancas(exp)
    if palancas:
        out += [Paragraph("Las tres decisiones que más mueven tu número", rb.h_sec),
                texto("Tu cifra no está grabada en piedra. De todo lo que podrías hacer, estas "
                      "tres son las que más la acercan — ordenadas por euros, no por lo que "
                      "suena mejor."),
                Spacer(1, 5 * mm)]
        for i, e in enumerate(palancas, 1):
            try:
                delta = abs(float(e.get("delta") or 0))
            except Exception:
                delta = 0
            anios = e.get("anios")
            out += [box([Paragraph("<font color='%s'><b>DECISIÓN %d</b></font>   %s"
                                   % (VERDE, i, e.get("escenario", "")),
                                   St(_id("apdt"), fontSize=10.5, leading=14, textColor=INK)),
                         Paragraph('<font size=22 color="%s"><b>−%s</b></font>'
                                   '<font size=10 color="#6B7280">  sobre tu número</font>'
                                   % (VERDE, eur(delta)),
                                   St(_id("apdc"), fontSize=22, leading=26, spaceBefore=3)),
                         Paragraph("Tu número pasaría a <b>%s</b>%s."
                                   % (eur(e.get("numero", 0)),
                                      (" · llegarías en <b>%s años</b>" % anios)
                                      if anios is not None
                                      else " · aun así no llegarías al ritmo de hoy"),
                                   St(_id("apdd"), fontSize=9.5, leading=13, textColor=GREY))],
                        "#F3F7F4", VERDE, ancho=160 * mm),
                    Spacer(1, 3 * mm)]
        out += [Spacer(1, 3 * mm),
                texto("Fíjate en el orden: <b>recortar el gasto baja el número mucho más que "
                      "ahorrar más</b>, porque reduce el capital que necesitas <i>para siempre</i>. "
                      "Ahorrar más no cambia la meta: te acerca antes a ella. La mayoría de la "
                      "gente hace justo lo contrario.", 10, GREY),
                PageBreak()]

    # =========================================================== PAGINA 4
    rv = ex.get("ratio_vida") or {}
    nudo = (ex.get("nudo") or {}).get("principal") or {}
    accion = ex.get("accion_unica")
    foco = nudo.get("tit") or rv.get("weakest")

    if foco or accion:
        out += [Paragraph("Por dónde empezar", rb.h_sec),
                texto("Tienes doce dimensiones medidas y ochenta páginas de detalle detrás. "
                      "Pero si esta semana solo cambias una cosa, que sea esta.")]
        if foco:
            out += [Spacer(1, 5 * mm),
                    box([rotulo("TU ESLABÓN MÁS DÉBIL", ROJO),
                         Paragraph("<b>%s</b>" % foco,
                                   St("ap_foco", fontSize=20, leading=25,
                                      textColor=colors.HexColor(ROJO), fontName=FB, spaceBefore=2)),
                         Paragraph("Es el punto donde tu sistema cede primero. No el más grave "
                                   "en euros: el que sostiene a los demás.",
                                   St("ap_focod", fontSize=9.5, leading=13, textColor=GREY))],
                        "#FBEDEC", ROJO, ancho=160 * mm)]
        if accion and isinstance(accion, str):
            out += [Spacer(1, 3 * mm),
                    box([rotulo("TU PRIMER PASO", VERDE),
                         Paragraph(accion, St("ap_paso", fontSize=11.5, leading=16,
                                              textColor=INK, spaceBefore=2))],
                        "#EAF3EC", VERDE, ancho=160 * mm)]

        # --- puente a Adapta. UNA linea. Sin venta blanda.
        out += [Spacer(1, 9 * mm),
                regla(),
                Spacer(1, 5 * mm),
                Paragraph("Tienes el diagnóstico. Ejecutarlo sin errores es otra conversación.",
                          St("ap_cierre", fontSize=15, leading=20, textColor=INK, fontName=FB)),
                Paragraph("Las páginas que siguen son el porqué, el cuánto y el cómo de todo lo "
                          "que acabas de leer: tus doce dimensiones una a una, tu mapa a 72 horas, "
                          "30 y 90 días, y la metodología completa. Léelas en orden.",
                          St("ap_cierre2", fontSize=10, leading=14, textColor=GREY, spaceBefore=5)),
                PageBreak()]

    return out
