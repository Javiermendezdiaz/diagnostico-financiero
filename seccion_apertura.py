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


def numero_libertad(datos, coste_mensual=None):
    """Numero de Libertad CANONICO para un coste de vida dado (por defecto, el del cliente).

    Todo el libro debe pedir el numero aqui. Antes varias piezas hacian
    `coste*12*25` por su cuenta (sin pension y con la regla del 4% bruta) y el
    mismo informe ensenaba 909.480, 870.000 y 1.170.000 al mismo cliente.
    Devuelve None solo si el motor no puede calcular (datos incompletos).
    """
    d = dict(datos or {})
    if coste_mensual is not None:
        d["coste_vida_ideal"] = coste_mensual
    exp = datos_expectativas(d)
    try:
        v = (exp or {}).get("numero_libertad")
        return None if v is None else round(float(v))
    except Exception:
        return None


def tres_palancas(exp):
    """Hasta 3 decisiones DISTINTAS, sin repetir cifra.

    Hay dos maneras de mejorar, y no son la misma:
      · BAJAR la meta   -> recortar el gasto reduce el capital que necesitas.
      · ACERCAR la fecha -> ahorrar mas o parar mas tarde no cambia la meta,
                            pero llegas antes.

    Antes se listaban los escenarios solo por delta, y salian dos con el MISMO
    numero — porque "las tres cosas a la vez" incluye el recorte de gasto. El
    lector veia dos decisiones diferentes con una cifra identica y parecia un
    error de calculo. Ahora cada una se presenta por lo que de verdad mejora.
    """
    escenarios = (exp or {}).get("escenarios") or []
    if len(escenarios) < 2:
        return []
    base = escenarios[0]
    try:
        base_num = round(float(base.get("numero") or 0))
    except Exception:
        return []
    base_anios = base.get("anios")

    bajan, acercan, vistos = [], [], set()
    for e in escenarios[1:]:
        try:
            num = round(float(e.get("numero") or 0))
        except Exception:
            continue
        anios = e.get("anios")
        gana = (base_anios - anios) if (base_anios is not None and anios is not None) else None
        if num < base_num - 1 and num not in vistos:
            vistos.add(num)
            e2 = dict(e); e2["_tipo"] = "baja"; e2["_gana"] = gana
            bajan.append(e2)
        elif gana is not None and gana >= 0.5:
            e2 = dict(e); e2["_tipo"] = "acerca"; e2["_gana"] = gana
            # Distingue "no baja la meta" (ahorrar mas) de "la baja lo mismo que
            # otra decision ya listada" (el combinado incluye el recorte de gasto).
            # Decir "no baja tu meta" cuando SI la baja es falso, y se nota.
            e2["_baja_igual"] = (num < base_num - 1)
            acercan.append(e2)

    bajan.sort(key=lambda e: float(e.get("delta") or 0))
    acercan.sort(key=lambda e: -(e.get("_gana") or 0))
    return (bajan + acercan)[:3]


def _estado(score):
    """(etiqueta, color) para el semaforo. Score alto = peor.

    Sin simbolos: la tipografia serif del informe no tiene ● ni ▲ y se comian
    silenciosamente, dejando una sangria rara delante de cada estado. El color
    mas la palabra ya comunican el nivel, y la palabra funciona tambien para
    quien no distingue bien los colores.
    """
    try:
        s = float(score)
    except Exception:
        return ("—", "#6B7280")
    if s < 30:
        return ("Sólido", VERDE)
    if s < 51:
        return ("Con margen", OCRE)
    if s < 76:
        return ("A vigilar", AMBAR)
    return ("Crítico", ROJO)



# ------------------------------------------------------------------ SESION CON ADAPTA
import urllib.parse as _up
WA_URL = ("https://wa.me/34683343531?text=" +
          _up.quote("Hola, he recibido mi diagnóstico y quiero reservar mi sesión estratégica de 30 minutos"))


def qr_flowable(url=WA_URL, lado_mm=24):
    """Codigo QR vectorial (sin dependencias nuevas: viene con ReportLab)."""
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.units import mm
    w = QrCodeWidget(url)
    w.barBorder = 0
    b = w.getBounds()
    bw, bh = b[2] - b[0], b[3] - b[1]
    lado = lado_mm * mm
    d = Drawing(lado, lado, transform=[lado / bw, 0, 0, lado / bh, 0, 0])
    d.add(w)
    return d


def cta_sesion(titulo, texto, fondo="#FBF9EC", barra="#C9962B", qr_mm=26, rotulo="TU SESIÓN CON ADAPTA"):
    """Caja de llamada a la sesion: texto + boton (enlace a WhatsApp) + QR para el movil."""
    import report_book as rb
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table
    St = rb.St
    boton = Table([[Paragraph("<a href='%s'><font color='#FDD731'><b>Reservar mi sesión por WhatsApp &#8594;</b></font></a>" % WA_URL,
                              St("cta_btn", fontSize=10.5, leading=13, fontName=rb.FB))]],
                  style=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A1A17")),
                         ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                         ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)])
    boton.hAlign = "LEFT"
    izq = [Paragraph(rotulo, St("cta_r", fontSize=8.2, leading=10.5, textColor=colors.HexColor(barra), fontName=rb.FB)),
           Paragraph(titulo, St("cta_t", fontSize=13.5, leading=17.5, textColor=rb.INK, fontName="Lora-Bold", spaceBefore=3)),
           Paragraph(texto, St("cta_x", fontSize=9.8, leading=13.8, textColor=rb.INK, spaceBefore=3, spaceAfter=7)),
           boton]
    der = [qr_flowable(WA_URL, qr_mm),
           Paragraph("Escanéalo con el móvil", St("cta_q", fontSize=7.2, leading=9, textColor=rb.GREY, alignment=1, spaceBefore=2))]
    t = Table([[izq, der]], colWidths=[(160 - qr_mm - 12) * mm, (qr_mm + 12) * mm],
              style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                     ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fondo)),
                     ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(barra)),
                     ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                     ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)])
    t.hAlign = "LEFT"
    return t


# ------------------------------------------------------------------ LUNES Y AÑOS
def lunes_y_rango(datos, exp):
    """Lunes de trabajo que te quedan hasta que tu dinero sostenga tu vida, hoy y con tus 3 decisiones,
    y el rango de edad segun los mercados. Usa el MISMO motor y los mismos escenarios del libro."""
    try:
        import motor_financiero_v3 as mfv3
    except Exception:
        return None
    if not exp or not exp.get("numero_libertad"):
        return None
    d = datos or {}
    def _f(k):
        try:
            return float(d.get(k) or 0)
        except Exception:
            return 0.0
    esc = exp.get("escenarios") or []
    if not esc:
        return None
    a0 = esc[0].get("anios")
    comb = None
    for e in esc:
        lbl = (e.get("escenario") or "").lower()
        if "recortas" in lbl and "ahorras" in lbl:
            comb = e
    if comb is None and len(esc) > 1:
        comb = min((e for e in esc[1:] if e.get("anios") is not None), key=lambda e: e.get("anios"), default=None)
    a1 = comb.get("anios") if comb else None
    edad = int(_f("edad")) if 0 < _f("edad") < 100 else 0
    N = float(exp["numero_libertad"])
    cap = _f("inversiones_liquidas") + _f("colchon_liquido")
    aho = _f("ahorro_mensual")
    rango = []
    for r in (3.5, 5.0, 6.5):
        try:
            rango.append(mfv3._anios_hasta(N, cap, aho, r / 100.0 / 12.0))
        except Exception:
            rango.append(None)
    return {"a0": a0, "a1": a1, "edad": edad, "rango": rango,
            "lunes0": (a0 * 52) if a0 is not None else None,
            "lunes1": (a1 * 52) if a1 is not None else None}


def costes_por_area(datos):
    """Lo que algunas areas te cuestan HOY al año, en euros y en lunes de trabajo.
    Solo donde tus propios numeros lo sostienen: si no hay dato, no se inventa."""
    d = datos or {}
    def _f(k):
        try:
            return float(d.get(k) or 0)
        except Exception:
            return 0.0
    ing = _f("ingreso_mensual")
    semana = ing * 12 / 52.0 if ing > 0 else 0
    def _l(eur):
        return int(round(eur / semana)) if semana > 0 else None
    out = {}
    ge = _f("gasto_estatus")
    if ge > 0:
        out["C6"] = (ge * 12, _l(ge * 12), "en imagen y estatus")
    gas, aho = _f("gasto_mensual"), d.get("ahorro_mensual")
    try:
        aho = float(aho)
    except Exception:
        aho = None
    if ing > 0 and gas > 0 and aho is not None and aho >= 0:
        sin = ing - gas - aho
        if sin > max(50.0, ing * 0.05):
            out["C9"] = (sin * 12, _l(sin * 12), "sin destino decidido")
    try:
        import report_book as rb
        t = rb.tapon_coste(d)
        if t:
            out["C11"] = (t[1], _l(t[1]), "de rentabilidad que no cobras")
    except Exception:
        pass
    return out


# ------------------------------------------------------------------ TU FRENTE A LOS DEMAS
# Banco de España, Encuesta Financiera de las Familias 2024 (Documento Ocasional 2610, cuadro 1.B):
# riqueza neta MEDIANA de los hogares por edad del cabeza de familia, en euros de 2024.
EFF2024_RIQUEZA_MEDIANA = [(0, 34, "menos de 35 años", 22900), (35, 44, "35 a 44 años", 80200),
                           (45, 54, "45 a 54 años", 145900), (55, 64, "55 a 64 años", 214500),
                           (65, 74, "65 a 74 años", 249200), (75, 200, "más de 74 años", 214500)]
EFF_FUENTE = "Banco de España, Encuesta Financiera de las Familias 2024 (riqueza neta mediana por edad)"


def frente_a_tu_edad(datos):
    """Tu patrimonio neto frente al del hogar típico (mediana) de tu edad. Solo afirma lo que la mediana permite."""
    d = datos or {}
    try:
        edad = int(float(d.get("edad") or 0)); pat = float(d.get("patrimonio") or 0)
    except Exception:
        return None
    if not (18 <= edad < 100) or pat <= 0:
        return None
    for lo, hi, tramo, med in EFF2024_RIQUEZA_MEDIANA:
        if lo <= edad <= hi:
            return {"tramo": tramo, "mediana": med, "pat": pat, "ratio": pat / med, "encima": pat >= med}
    return None



def bloque_lunes(d, exp, vosotros=False):
    """Pagina "Tus lunes": muro de lunes, cuadricula de años y rango. Reutilizable (individual y pareja)."""
    import report_book as rb
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, PageBreak, Flowable as _Fl
    St, box = rb.St, rb._box
    INK, GREY, FB = rb.INK, rb.GREY, rb.FB
    _n = [0]
    def _id(pre):
        _n[0] += 1
        return "bl%s%d" % (pre, _n[0])
    def texto(txt, tam=10.5, color=None):
        return Paragraph(txt, St(_id("t"), fontSize=tam, leading=tam + 4.5, textColor=(color or INK)))
    def rotulo(txt, color=GREY):
        col = colors.HexColor(color) if isinstance(color, str) else color
        return Paragraph(txt, St(_id("r"), fontSize=8.5, leading=11, textColor=col, fontName=FB))
    H1 = St(_id("h1"), fontSize=24, leading=29, textColor=INK, fontName="Lora-Bold", spaceAfter=6)
    T = ({"h1": "Vuestros lunes, con y sin vuestras decisiones",
          "intro": "Cada punto es un lunes de trabajo que os queda hasta que vuestro dinero pueda sostener la vida de los dos. "
                   "Los verdes son los que os quitáis si aplicáis vuestras 3 decisiones.",
          "hoy": "HOY, A VUESTRO RITMO", "nollega": "No llegáis", "con": "CON VUESTRAS 3 DECISIONES", "quitas": "OS QUITÁIS",
          "anios": "VUESTROS PRÓXIMOS AÑOS, DE HOY A LOS 95", "recuperas": "los que recuperáis con vuestras decisiones",
          "tuyos": "años vuestros", "llegas": "llegáis", "nollegarias": "no llegaríais",
          "mueven": "Vuestras decisiones mueven esta edad mucho más que los mercados."} if vosotros else
         {"h1": "Tus lunes, con y sin tus decisiones",
          "intro": "Cada punto es un lunes de trabajo que te queda hasta que tu dinero pueda sostener tu vida. "
                   "Los verdes son los que te quitas si aplicas tus 3 decisiones.",
          "hoy": "HOY, A TU RITMO", "nollega": "No llegas", "con": "CON TUS 3 DECISIONES", "quitas": "TE QUITAS",
          "anios": "TUS PRÓXIMOS AÑOS, DE HOY A LOS 95", "recuperas": "los que recuperas con tus decisiones",
          "tuyos": "años tuyos", "llegas": "llegas", "nollegarias": "no llegarías",
          "mueven": "Tus decisiones mueven esta edad mucho más que los mercados."})
    lr = lunes_y_rango(d, exp)
    if not (lr and ((lr.get("a0") or 0) > 0 or (lr.get("a0") is None and lr.get("a1")))):
        return []
    out = []
    class _Muro(_Fl):
        """Un punto por lunes. Negros: los que siguen. Verdes: los que te quitas con tus 3 decisiones."""
        def __init__(self, total, quitas, ancho=160 * mm):
            _Fl.__init__(self); self.t = int(total); self.q = max(0, int(quitas)); self.w = ancho
            self.cols = max(52, -(-self.t // 24)); self.gap = 0.7 * mm if self.cols <= 60 else 0.45 * mm
            self.dd = (self.w - self.gap * (self.cols - 1)) / self.cols
            self.filas = max(1, -(-self.t // self.cols))
            self.h = self.filas * (self.dd + self.gap)
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            for i in range(self.t):
                x = (i % self.cols) * (self.dd + self.gap)
                y = self.h - (i // self.cols + 1) * (self.dd + self.gap)
                c.setFillColor(colors.HexColor(VERDE) if i >= self.t - self.q else colors.HexColor("#1A1A17"))
                c.circle(x + self.dd / 2, y + self.dd / 2, self.dd / 2 * 0.86, fill=1, stroke=0)

    class _Anios(_Fl):
        """Tus proximos años, de hoy a los 95: rojo trabajando, verde los que recuperas, amarillo libres."""
        def __init__(self, edad, llega0, llega1, ancho=160 * mm):
            _Fl.__init__(self); self.e = edad; self.l0 = llega0; self.l1 = llega1; self.w = ancho
            self.n = max(1, 95 - edad); self.cols = min(self.n, 30); self.gap = 1.1 * mm
            self.dd = (self.w - self.gap * (self.cols - 1)) / self.cols
            self.filas = -(-self.n // self.cols); self.h = self.filas * (self.dd + self.gap) + 5 * mm
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            for k in range(self.n):
                y_ed = self.e + k
                x = (k % self.cols) * (self.dd + self.gap)
                y = self.h - 5 * mm - (k // self.cols + 1) * (self.dd + self.gap)
                if self.l1 is not None and y_ed < self.l1:
                    col = ROJO
                elif self.l0 is None or y_ed < self.l0:
                    col = VERDE if self.l1 is not None else ROJO
                else:
                    col = "#C9962B"
                c.setFillColor(colors.HexColor(col)); c.roundRect(x, y, self.dd, self.dd, 1.2, fill=1, stroke=0)
                if k % 10 == 0 or k == 0:
                    c.setFillColor(colors.HexColor("#6B7280")); c.setFont("Poppins", 6.5)
                    c.drawString(x, y + self.dd + 1.2 * mm, str(y_ed))

    def _f1(n):
        return ("{:,.0f}".format(n)).replace(",", ".")
    l0, l1 = lr.get("lunes0"), lr.get("lunes1")
    a0, a1, ed = lr.get("a0"), lr.get("a1"), lr.get("edad")
    out += [Spacer(1, 8 * mm), Paragraph(T["h1"], H1),
            texto(T["intro"], 12)]
    celdas = []
    if l0:
        celdas.append((T["hoy"], "%s lunes" % _f1(l0), "#1A1A17"))
    else:
        celdas.append((T["hoy"], T["nollega"], ROJO))
    if l1:
        celdas.append((T["con"], "%s lunes" % _f1(l1), "#1A1A17"))
    if l0 and l1 and l0 > l1:
        celdas.append((T["quitas"], "%s lunes" % _f1(l0 - l1), VERDE))
    fila = [[Paragraph(r_, St(_id("lnr"), fontSize=8.2, leading=10.5, textColor=colors.HexColor("#6B7280"), fontName=FB)),
             Paragraph("<b>%s</b>" % v_, St(_id("lnv"), fontSize=21, leading=26, textColor=colors.HexColor(c_), fontName=FB, spaceBefore=3))]
            for r_, v_, c_ in celdas]
    _cw = 160.0 / len(fila)
    out += [Spacer(1, 6 * mm),
            Table([fila], colWidths=[_cw * mm] * len(fila),
                  style=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3EFE4")),
                         ("LINEBEFORE", (1, 0), (-1, -1), 5, rb.PAGEBG),
                         ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10),
                         ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("LINEABOVE", (0, 0), (-1, 0), 2.2, rb.AMARILLO)]),
            Spacer(1, 6 * mm)]
    _tot = l0 if l0 else l1
    if _tot and _tot <= 3000:
        out += [_Muro(_tot, (l0 - l1) if (l0 and l1 and l0 > l1) else 0), Spacer(1, 6 * mm)]
    if ed:
        out += [rotulo(T["anios"]), Spacer(1, 2 * mm),
                _Anios(ed, (ed + a0) if a0 is not None else None, (ed + a1) if a1 is not None else None),
                Paragraph(('<font color="%s"><b>Rojo</b></font>: trabajando por dinero &nbsp;·&nbsp; <font color="%s"><b>Verde</b></font>: ' % (ROJO, VERDE))
                          + T["recuperas"] + ' &nbsp;·&nbsp; <font color="#C9962B"><b>Dorado</b></font>: ' + T["tuyos"],
                          St(_id("leg"), fontSize=8.5, leading=11, textColor=GREY, spaceBefore=3))]
    _rg = lr.get("rango") or []
    if ed and len(_rg) == 3 and _rg[1] is not None:
        _lo = _rg[2]; _hi = _rg[0]
        _txt = ("<b>Un rango, no una promesa.</b> Con una rentabilidad real del 5 % " + T["llegas"] + (" a los <b>%d</b>. " % (ed + _rg[1])))
        if _lo is not None and _hi is not None:
            _txt += ("Si los mercados van mejor (6,5 %%), a los %d; si van peor (3,5 %%), a los %d. "
                     % (ed + _lo, ed + _hi))
        elif _lo is not None:
            _txt += ("Si los mercados van mejor (6,5 %%), a los %d; si van peor (3,5 %%), " + T["nollegarias"] + " antes de los 95. ") % (ed + _lo)
        _txt += T["mueven"]
        out += [Spacer(1, 6 * mm), box([texto(_txt, 10.5, INK)], "#F3EFE4", "#C9962B", ancho=160 * mm)]
    out += [PageBreak()]

    return out

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
        # hAlign LEFT explicito: ReportLab centra por defecto las tablas de una celda,
        # y la regla salia centrada mientras el resto de la pagina va a la izquierda.
        t = Table([[""]], colWidths=[ancho * mm],
                  style=[("LINEBELOW", (0, 0), (-1, -1), 2.5, rb.AMARILLO)])
        t.hAlign = "LEFT"
        return t

    from reportlab.platypus import Flowable as _Fl

    class _Progreso(_Fl):
        """Barra de camino: de lo que tienes hoy a tu Numero de Libertad. Se entiende sin leer."""
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

    # =========================================================== PAGINA 1
    out.append(Spacer(1, 8 * mm))
    lr = lunes_y_rango(d, exp)
    _hay_lunes = bool(lr and ((lr.get("a0") or 0) > 0 or (lr.get("a0") is None and lr.get("a1"))))
    out.append(Paragraph("LO ESENCIAL · TU DIAGNÓSTICO EN %s PÁGINAS" % ("CINCO" if _hay_lunes else "CUATRO"),
                         St("ap_eyebrow", fontSize=8.5, leading=11, textColor=rb.ACC,
                            fontName=FB, spaceAfter=3)))

    brecha = ex.get("brecha") or {}
    try:
        br_mes = float(brecha.get("brecha_mes") or 0)
        br_anual = float(brecha.get("brecha_anual") or 0)
    except Exception:
        br_mes = br_anual = 0.0

    # EL TITULAR ES LO QUE TE SEPARA DE LA LIBERTAD, medido sobre el capital que de verdad rinde
    # (invertido + liquido), el mismo del "ya cubierto". Antes abria con la brecha de ingresos
    # (100 €/mes en el perfil de prueba) y trivializaba un informe que luego habla de 850.000 €.
    if exp and exp.get("numero_libertad"):
        N = float(exp["numero_libertad"])
        try:
            cap = float(d.get("inversiones_liquidas") or 0) + float(d.get("colchon_liquido") or 0)
        except Exception:
            cap = 0.0
        falta = max(0.0, N - cap)
        out += [Paragraph("Esto es lo que te separa de no depender de un sueldo",
                          St("ap_h1", fontSize=24, leading=29, textColor=INK, fontName="Lora-Bold", spaceAfter=6)),
                Spacer(1, 3 * mm),
                cifra(eur(falta) if falta > 0 else "Ya has llegado",
                      ROJO if falta > 0 else VERDE, 62),
                Spacer(1, 2 * mm),
                texto("Tu Número de Libertad es <b>%s</b> y hoy tienes <b>%s</b> entre lo invertido y lo líquido "
                      "(tu vivienda no cuenta: no paga tus gastos). "
                      "Lo tienes cubierto al <b>%s%%</b>."
                      % (eur(N), eur(cap), exp.get("pct_cubierto", 0)), 12.5),
                Spacer(1, 7 * mm),
                _Progreso(exp.get("pct_cubierto", 0), "Hoy · %s" % eur(cap), "Tu libertad · %s" % eur(N))]
        if br_anual > 0:
            out += [Spacer(1, 5 * mm),
                    box([rotulo("Y LA VIDA QUE DIJISTE QUERER", ROJO),
                         texto("Pide <b>%s al mes</b> más de lo que hoy ingresas: <b>%s al año</b>. "
                               "Es la otra distancia que hay que cerrar, y sale de tus propios números."
                               % (eur(br_mes), eur(br_anual)), 11.5, rb.INK)],
                        "#FBEDEC", ROJO, ancho=160 * mm)]
    elif br_anual > 0:
        out += [Paragraph("Esto es lo que te separa, cada año, de la vida que dijiste querer",
                          rb.h_sec),
                cifra(eur(br_anual)),
                texto("Son <b>%s al mes</b> de distancia entre la vida que tienes y la que "
                      "describiste en tus respuestas. Sale de tus propios números." % eur(br_mes))]
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
            fila.append([Paragraph(rot, St(_id("apkl"), fontSize=8.5, leading=11,
                                           textColor=colors.HexColor("#6B7280"), fontName=FB)),
                         Paragraph("<b>%s</b>" % val,
                                   St(_id("apkv"), fontSize=24, leading=29,
                                      textColor=colors.HexColor(col), fontName=FB, spaceBefore=3))])
        while len(fila) < 3:
            fila.append([Paragraph("", rb.small)])
        out += [Spacer(1, 6 * mm),
                Table([fila], colWidths=[53 * mm, 53 * mm, 54 * mm],
                      style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3EFE4")),
                             ("LINEBEFORE", (1, 0), (-1, -1), 5, rb.PAGEBG),
                             ("LEFTPADDING", (0, 0), (-1, -1), 12),
                             ("TOPPADDING", (0, 0), (-1, -1), 12),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                             ("LINEABOVE", (0, 0), (-1, 0), 2.2, rb.AMARILLO)])]
    _fe = frente_a_tu_edad(d)
    if _fe:
        if _fe["encima"]:
            _ft = ("<b>Frente a los hogares de tu edad:</b> tu patrimonio neto (%s) es <b>%s veces</b> el del hogar típico "
                   "de %s (%s). Más de la mitad de esos hogares tiene menos que tú."
                   % (eur(_fe["pat"]), ("%.1f" % _fe["ratio"]).replace(".", ","), _fe["tramo"], eur(_fe["mediana"])))
        else:
            _ft = ("<b>Frente a los hogares de tu edad:</b> tu patrimonio neto (%s) está por debajo del hogar típico "
                   "de %s (%s). Es justo la distancia que tu plan está pensado para cerrar."
                   % (eur(_fe["pat"]), _fe["tramo"], eur(_fe["mediana"])))
        out += [Spacer(1, 3.5 * mm), texto(_ft, 10, INK),
                Paragraph("Fuente: " + EFF_FUENTE + ". Datos por hogar: si compartes patrimonio en pareja, compara el del hogar.",
                          St("ap_eff", fontSize=7.8, leading=10, textColor=GREY, spaceBefore=2))]
    out += [Spacer(1, 5 * mm),
            cta_sesion("¿Quieres bajar esta cifra con alguien al lado?",
                       "En 30 minutos convertimos tu diagnóstico en tus primeras decisiones, con números y fechas. "
                       "Te descontamos el importe íntegro de este informe.", qr_mm=18),
            PageBreak()]

    H1 = St("ap_h1g", fontSize=24, leading=29, textColor=INK, fontName="Lora-Bold", spaceAfter=6)
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
                  ("TOPPADDING", (0, 0), (-1, -1), 5.5),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
                  ("LEFTPADDING", (0, 0), (-1, -1), 10)]
        # Orden: lo peor arriba. Un informe que decide no ordena por numero de capa.
        capas = sorted(p.items(), key=lambda kv: -(kv[1].get("score") or 0))
        _cost = costes_por_area(d)
        if _cost:
            filas[0][2] = Paragraph("<b>PUNTO MÁS FRÁGIL · LO QUE TE CUESTA</b>", St("ap_th3b", fontSize=8, leading=10,
                                    textColor=colors.HexColor("#6B7280"), fontName=FB))
        for i, (code, v) in enumerate(capas, 1):
            etq, col = _estado(v.get("score"))
            _c = _cost.get(code)
            _tercera = (Paragraph('<font color="%s"><b>%s/año</b></font>%s<br/><font color="#6B7280">%s</font>'
                                  % (ROJO, eur(_c[0]), (" · <b>%d lunes</b>" % _c[1]) if _c[1] else "", _c[2]),
                                  St(_id("apsc"), fontSize=9.5, leading=12.5, textColor=INK))
                        if _c else Paragraph(v.get("peor") or "—",
                                             St(_id("apsp"), fontSize=9.5, leading=12.5, textColor=GREY)))
            filas.append([
                Paragraph(v.get("nombre", code),
                          St(_id("apsn"), fontSize=10.5, leading=13.5, textColor=INK)),
                Paragraph('<font color="%s"><b>%s</b></font>' % (col, etq),
                          St(_id("apse"), fontSize=10.5, leading=13.5)),
                _tercera])
            # filete de color a la izquierda: el semaforo se lee sin leer
            estilo.append(("LINEBEFORE", (0, i), (0, i), 3.2, colors.HexColor(col)))
            if etq == "Crítico":
                estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FBEDEC")))
        criticas = sum(1 for _, v in capas if _estado(v.get("score"))[0] == "Crítico")
        solidas = sum(1 for _, v in capas if _estado(v.get("score"))[0] == "Sólido")
        # Concordancia de numero y un cierre que DIGA algo distinto segun el cuadro.
        # Antes salia "1 solidas" y una frase generica aunque no hubiera nada critico.
        def _pl(n, sing, plur):
            return "<b>%d</b> %s" % (n, sing if n == 1 else plur)
        _peor = capas[0][1].get("nombre", "") if capas else ""
        if criticas:
            _cierre = ("%s y %s. La que más pide atención es <b>%s</b>: es la que está "
                       "tirando del resto hacia abajo."
                       % (_pl(criticas, "dimensión en estado crítico", "dimensiones en estado crítico"),
                          _pl(solidas, "sólida", "sólidas"), _peor))
        elif solidas >= 6:
            _cierre = ("Ninguna en estado crítico y %s. Tu cuadro es bueno: lo que toca "
                       "no es apagar fuegos, es que <b>%s</b> deje de ser la más frágil."
                       % (_pl(solidas, "sólida", "sólidas"), _peor))
        else:
            _cierre = ("Ninguna en estado crítico, pero %s. No hay urgencias; hay margen "
                       "de mejora casi en todo. La que más pide atención es <b>%s</b>, la primera de la lista."
                       % (_pl(solidas, "sólida", "sólidas"), _peor))
        _cnt = {}
        for _, v in capas:
            _e = _estado(v.get("score")); _cnt[_e] = _cnt.get(_e, 0) + 1
        _tira = []
        for (_et, _co), _nn in sorted(_cnt.items(), key=lambda kv: ["Crítico","A vigilar","Con margen","Sólido"].index(kv[0][0]) if kv[0][0] in ["Crítico","A vigilar","Con margen","Sólido"] else 9):
            _tira.append([Paragraph("<b>%d</b>" % _nn, St(_id("apcn"), fontSize=26, leading=30, textColor=colors.HexColor(_co), fontName=FB)),
                          Paragraph(_et.upper(), St(_id("apcl"), fontSize=8.5, leading=11, textColor=GREY, fontName=FB))])
        _tw = 160.0 / max(1, len(_tira))
        out += [Spacer(1, 8 * mm), Paragraph("Tu cuadro completo, de un vistazo", H1),
                texto("Doce dimensiones medidas. Ordenadas de la más frágil a la más sólida — "
                      "no por orden de capítulo." + (" <font color='%s'><b>En rojo</b></font>, lo que algunas te cuestan hoy al año, en euros y en lunes de trabajo." % ROJO if costes_por_area(d) else ""), 12),
                Spacer(1, 6 * mm),
                Table([_tira], colWidths=[_tw * mm] * len(_tira),
                      style=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3EFE4")),
                             ("LINEBEFORE", (1, 0), (-1, -1), 5, rb.PAGEBG),
                             ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 9),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]),
                Spacer(1, 4 * mm),
                Table(filas, colWidths=[64 * mm, 40 * mm, 56 * mm], style=estilo),
                Spacer(1, 4 * mm),
                texto(_cierre, 11.5, INK),
                PageBreak()]

    # =========================================================== PAGINA 3
    palancas = tres_palancas(exp)
    if palancas:
        try:
            _a0 = (exp.get("escenarios") or [{}])[0].get("anios")
        except Exception:
            _a0 = None
        out += [Spacer(1, 8 * mm), Paragraph("Las tres decisiones que más mueven tu número", H1),
                texto("Tu cifra no está grabada en piedra. De todo lo que podrías hacer, estas "
                      "tres son las que más la acercan — ordenadas por euros, no por lo que "
                      "suena mejor.", 12)]
        if _a0 is not None:
            out += [Spacer(1, 4 * mm),
                    texto("<b>Hoy, a tu ritmo:</b> %s en <b>%s años</b>. Mira lo que cambia con cada decisión:"
                          % (eur(exp.get("numero_libertad", 0)), _a0), 11.5, INK)]
        out += [Spacer(1, 5 * mm)]
        def _anios(n):
            if n is None:
                return None
            n = float(n)
            return ("%d" % round(n)) if abs(n - round(n)) < 0.1 else ("%.1f" % n).replace(".", ",")

        for i, e in enumerate(palancas, 1):
            anios = e.get("anios")
            gana = e.get("_gana")
            if e.get("_tipo") == "acerca":
                # No baja la meta: adelanta la fecha. Decirlo asi evita que dos
                # decisiones parezcan la misma por compartir cifra.
                cifra = ('<font size=28 color="%s"><b>%s años antes</b></font>'
                         '<font size=11 color="#6B7280">  de llegar</font>'
                         % (VERDE, _anios(gana)))
                _antes = _anios((anios or 0) + (gana or 0))
                if e.get("_baja_igual"):
                    detalle = ("Deja tu meta en <b>%s</b>, igual que la decisión anterior, "
                               "pero llegarías a ella en <b>%s años</b> en vez de %s."
                               % (eur(e.get("numero", 0)), _anios(anios), _antes))
                else:
                    detalle = ("No baja tu meta —sigue en <b>%s</b>— pero llegarías a ella "
                               "en <b>%s años</b> en vez de %s."
                               % (eur(e.get("numero", 0)), _anios(anios), _antes))
            else:
                try:
                    delta = abs(float(e.get("delta") or 0))
                except Exception:
                    delta = 0
                cifra = ('<font size=28 color="%s"><b>−%s</b></font>'
                         '<font size=11 color="#6B7280">  sobre tu número</font>'
                         % (VERDE, eur(delta)))
                detalle = ("Tu número pasaría a <b>%s</b>%s."
                           % (eur(e.get("numero", 0)),
                              (" · llegarías en <b>%s años</b>" % _anios(anios))
                              if anios is not None
                              else " · aun así no llegarías al ritmo de hoy"))
            out += [box([Paragraph("<font color='%s'><b>DECISIÓN %d</b></font>   %s"
                                   % (VERDE, i, e.get("escenario", "")),
                                   St(_id("apdt"), fontSize=11.5, leading=15, textColor=INK)),
                         Paragraph(cifra, St(_id("apdc"), fontSize=28, leading=34, spaceBefore=5)),
                         Paragraph(detalle,
                                   St(_id("apdd"), fontSize=10.5, leading=14.5, textColor=GREY, spaceBefore=2))],
                        "#F3F7F4", VERDE, ancho=160 * mm),
                    Spacer(1, 5 * mm)]
        out += [Spacer(1, 3 * mm),
                texto("Fíjate en la diferencia: <b>recortar el gasto baja tu número para siempre</b>, porque reduce "
                      "el capital que necesitas. Ahorrar más no cambia la meta: te acerca antes a ella. "
                      "Las dos juntas son las que más años te devuelven.", 11, GREY),
                PageBreak()]

    # =========================================================== PAGINA 4 · TUS LUNES
    # El mismo lenguaje de la web: un punto por cada lunes de trabajo que te queda.
    if _hay_lunes:
        out += bloque_lunes(d, exp)


    # =========================================================== PAGINA 4
    rv = ex.get("ratio_vida") or {}
    nudo = (ex.get("nudo") or {}).get("principal") or {}
    accion = ex.get("accion_unica")
    foco = nudo.get("tit") or rv.get("weakest")

    if foco or accion:
        out += [Spacer(1, 8 * mm), Paragraph("Por dónde empezar", H1),
                texto("Tienes doce dimensiones medidas y todo el detalle en las páginas que siguen. "
                      "Pero si esta semana solo cambias una cosa, que sea esta.", 12)]
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
                         Paragraph(accion, St("ap_paso", fontSize=14, leading=20,
                                              textColor=INK, spaceBefore=4))],
                        "#EAF3EC", VERDE, ancho=160 * mm)]

        # --- puente a Adapta. UNA linea. Sin venta blanda.
        out += [Spacer(1, 9 * mm),
                regla(),
                Spacer(1, 5 * mm),
                Paragraph("Tienes el diagnóstico. Ejecutarlo sin errores es otra conversación.",
                          St("ap_cierre", fontSize=20, leading=26, textColor=INK, fontName="Lora-Bold")),
                Paragraph("Las páginas que siguen son el porqué, el cuánto y el cómo de todo lo "
                          "que acabas de leer: tus doce dimensiones una a una, tu mapa a 72 horas, "
                          "30 y 90 días, y la metodología completa. Léelas en orden.",
                          St("ap_cierre2", fontSize=11, leading=15.5, textColor=GREY, spaceBefore=6)),
                Spacer(1, 6 * mm),
                cta_sesion("Si quieres ir más rápido y sin errores",
                           "En una <b>sesión estratégica de 30 minutos</b> convertimos este diagnóstico en tus "
                           "primeras decisiones, con números y fechas. Y te descontamos de ella el importe "
                           "íntegro de este informe.", qr_mm=28),
                PageBreak()]

    return out
