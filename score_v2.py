# -*- coding: utf-8 -*-
"""ITAP v2 — Motor de extras: brecha vital, palancas de crecimiento y contradicciones.

Funciona sobre el esquema adaptativo (itap_v2.json). NO depende de reportlab ni de
report_book, de modo que se puede testear de forma aislada. Devuelve un dict 'extras'
que report_book inyecta en el libro, mas el arquetipo derivado de la vision ideal.

Polaridad de scores: 0 = sano, 100 = disfuncion (igual que el resto del instrumento).
Todo numero que aqui se computa sale de datos REALES del cliente; no se inventa nada.
"""
import os, json, statistics

_HERE = os.path.dirname(os.path.abspath(__file__))


def cargar_inst(path=None):
    p = path or os.path.join(_HERE, "itap_v2.json")
    return json.load(open(p, encoding="utf-8"))


def _peso(it):
    return 0.5 if "metacognición" in (it.get("dimensiones", "") or "") else 1.0


def perfil_scores(resp, capas):
    """Replica fiel de report_book.perfil: por capa, media de facetas (con peso);
    score capa = media de las facetas respondidas (denominador flotante)."""
    out = {}
    for capa in capas:
        fac = {}
        for it in capa["items"]:
            if it.get("tipo") != "escala":
                continue
            idx = resp.get(it["id"])
            if idx is None:
                continue
            try:
                sc = it["opciones"][idx]["score"]
            except (IndexError, KeyError, TypeError):
                continue
            fac.setdefault(it["faceta"], []).append((sc, _peso(it)))
        facetas = {f: round(sum(v * w for v, w in l) / sum(w for _, w in l), 1)
                   for f, l in fac.items() if l}
        score = round(statistics.mean(list(facetas.values())), 1) if facetas else 0.0
        out[capa["code"]] = {"score": score, "facetas": facetas, "nombre": capa["nombre"]}
    return out


# VIS arq -> codigo de arquetipo del dinero de report_book.ARQ_META
ARQ_MAP = {"TIEMPO": "LIB", "ESTATUS": "EST", "SEGURIDAD": "SEG"}


def arq_desde_perfil(perfil_in):
    v = (perfil_in or {}).get("vida_ideal_arq")
    return ARQ_MAP.get(v)


def _eur(n):
    try:
        return ("%s" % format(int(round(n)), ",d")).replace(",", ".") + " €"
    except Exception:
        return "—"


def _num(d, k):
    try:
        x = float(d.get(k))
        return x if x and x > 0 else None
    except (TypeError, ValueError):
        return None


def calcular_brecha(datos, resp, perfil_in):
    """Brecha vital: lo que cuesta la vida ideal frente a lo que hoy ingresas/acumulas."""
    ingreso = _num(datos, "ingreso_mensual")
    gasto = _num(datos, "gasto_mensual")
    coste_ideal = _num(datos, "coste_vida_ideal")
    ahorro = _num(datos, "ahorro_mensual") or 0.0
    patrimonio = _num(datos, "patrimonio") or 0.0
    if not coste_ideal:
        return None
    numero_ideal = coste_ideal * 12 * 25         # regla 25x sobre la vida que QUIERES
    base = gasto or ingreso
    numero_actual = base * 12 * 25 if base else None
    arq = (perfil_in or {}).get("vida_ideal_arq")
    # reconocimiento del propio cliente (VIS-03): 0 en rumbo, 1 espejismo, 2 via muerta
    recon = resp.get("VIS-03")
    recon_txt = {0: "en rumbo", 1: "espejismo", 2: "vía muerta"}.get(recon)
    base_out = {"coste_ideal_mes": coste_ideal, "numero_ideal": numero_ideal,
                "numero_actual": numero_actual, "ahorro_mes": ahorro, "arq": arq,
                "reconocimiento": recon_txt, "patrimonio": patrimonio}
    if not ingreso:
        # Sin ingreso recurrente: la vida la sostiene (o no) el capital. Renta prudente al 4%.
        renta_cap = round(patrimonio * 0.04 / 12)
        brecha_mes = coste_ideal - renta_cap
        base_out.update({"sin_ingreso": True, "ingreso_mes": 0, "renta_capital_mes": renta_cap,
                         "brecha_mes": brecha_mes, "brecha_anual": brecha_mes * 12,
                         "ingreso_cubre_ideal": renta_cap >= coste_ideal})
        return base_out
    brecha_mes = coste_ideal - ingreso          # >0 = la vida ideal cuesta mas de lo que ingresas
    base_out.update({"sin_ingreso": False, "ingreso_mes": ingreso, "brecha_mes": brecha_mes,
                     "brecha_anual": brecha_mes * 12, "ingreso_cubre_ideal": brecha_mes <= 0})
    return base_out


def calcular_palancas(datos, p, perfil_in, resp=None):
    """Palancas ofensivas, todas derivadas de datos reales. Devuelve lista de (titulo, texto)."""
    ingreso = _num(datos, "ingreso_mensual")
    gasto = _num(datos, "gasto_mensual")
    ahorro = _num(datos, "ahorro_mensual") or 0.0
    patrimonio = _num(datos, "patrimonio") or 0.0
    coste_ideal = _num(datos, "coste_vida_ideal")
    invierte = (perfil_in or {}).get("invierte", "")
    out = []

    # 1) Tasa de ahorro y la tijera ingreso-gasto
    if ingreso:
        tasa = round(100 * ahorro / ingreso, 1)
        tijera = ingreso - (gasto or 0)
        if tasa < 10:
            out.append(("Tu tijera de ahorro está casi cerrada",
                        "Ahorras un %s%% de lo que ingresas (%s al mes). Es la palanca de mayor impacto: "
                        "cada punto que la subas adelanta tu libertad años, no meses. Antes de buscar más "
                        "rentabilidad, ensancha esta tijera." % (("%g" % tasa), _eur(ahorro))))
        else:
            out.append(("Tu tijera de ahorro ya trabaja a tu favor",
                        "Ahorras un %s%% de tus ingresos (%s/mes). Mantén ese hábito y dirige el excedente a "
                        "que el dinero genere dinero: el siguiente salto es de eficiencia, no de esfuerzo." % (("%g" % tasa), _eur(ahorro))))

    # 2) Coste de oportunidad del patrimonio parado
    if patrimonio >= 10000 and ("No, nada" in invierte or invierte == "" or "nada invertido" in invierte.lower()):
        coste_op = patrimonio * 0.04
        out.append(("Tienes patrimonio dormido",
                    "Manejas un patrimonio de %s que, por lo que indicas, no está trabajando. A una rentabilidad "
                    "real prudente del 4%%, el coste de oportunidad ronda %s al año: dinero que dejas de ganar por "
                    "tenerlo quieto. No es urgencia de invertir por invertir; es dejar de regalar ese margen." % (_eur(patrimonio), _eur(coste_op))))

    # 3) Brecha de ingresos hacia la vida ideal
    if coste_ideal and ingreso and coste_ideal > ingreso:
        falta = coste_ideal - ingreso
        out.append(("La vida que quieres pide más músculo de ingresos",
                    "Tu vida ideal cuesta %s/mes y hoy ingresas %s: faltan %s al mes. Cerrar esa brecha rara vez "
                    "sale del gasto; sale de una segunda fuente o de subir el valor de lo que ya haces. Esa es la "
                    "palanca ofensiva que más mueve tu horizonte." % (_eur(coste_ideal), _eur(ingreso), _eur(falta))))

    # 4) Concentración de ingresos como freno al crecimiento
    if p.get("C7", {}).get("score", 0) >= 55:
        out.append(("Tu motor de ingresos depende de una sola pieza",
                    "Tu mayor riesgo —y a la vez tu mayor palanca— es que casi todo tu ingreso viene de una sola "
                    "fuente. Diversificarlo no solo te protege: abre la vía de crecimiento que hoy no existe."))

    # 5) Precio-hora: el tiempo malvendido (solo si declara horas y tiene ingreso)
    horas = _num(datos, "horas_semana")
    if horas and ingreso:
        ph = ingreso / (horas * 4.33)
        if ph < 25 and horas >= 40:
            out.append(("Tu hora vale menos de lo que crees",
                        "Dedicas unas %.0f horas a la semana para ingresar %s al mes: tu hora sale a unos %s. A ese "
                        "precio, la palanca no es meter más horas — es subir el valor de cada una: precio, "
                        "posicionamiento o delegar lo que no rinde." % (horas, _eur(ingreso), _eur(ph))))

    # 6) Dinero atrapado en la sociedad (S.L.)
    if resp and resp.get("C11-11") == 2:
        out.append(("Tienes patrimonio secuestrado en tu sociedad",
                    "El dinero que genera tu empresa se queda dentro sin un plan para llegar a tu patrimonio personal. "
                    "Es capital tuyo que ni trabaja para ti ni te da tranquilidad: ordenar la salida —vía dividendos, "
                    "nómina o estructura, con criterio fiscal— es de las palancas más rentables que tienes."))

    # 7) Comisiones de inversión que erosionan la rentabilidad en silencio
    if resp and resp.get("C2-14") == 2 and patrimonio >= 10000:
        coste = patrimonio * 0.015
        out.append(("Tus comisiones te comen la rentabilidad en silencio",
                    "No saber qué pagas casi siempre significa pagar de más. Sobre tu patrimonio, una comisión típica "
                    "de banco (~1,5%%) son unos %s al año — y a 20 años, por interés compuesto, puede costarte cerca "
                    "de un tercio de lo que habrías acumulado. Saber el dato y bajarlo es rentabilidad garantizada." % _eur(coste)))

    if not out:
        out.append(("Tu base permite pasar a la ofensiva",
                    "No detectamos fugas graves ni dependencia crítica. Tu trabajo ahora no es defender, sino "
                    "construir: poner a trabajar el excedente y el patrimonio con un plan a años vista."))
    return out


def calcular_contradicciones(datos, resp, perfil_in, p):
    """Disonancias entre lo que el cliente dice, siente y mide. Lista de (titulo, texto)."""
    out = []
    invierte = (perfil_in or {}).get("invierte", "")
    ingreso = _num(datos, "ingreso_mensual")
    ahorro = _num(datos, "ahorro_mensual") or 0.0
    patrimonio = _num(datos, "patrimonio") or 0.0
    coste_ideal = _num(datos, "coste_vida_ideal")
    tasa = (100 * ahorro / ingreso) if ingreso else 0

    # 1) Dice invertir pero reacciona con pánico ante caídas (C1-01)
    reac = resp.get("C1-01")
    if invierte and "No, nada" not in invierte and reac == 2:
        out.append(("Inviertes, pero tu cabeza aún no",
                    "Declaras tener una parte invertida y, sin embargo, ante una caída tu primer impulso es vender "
                    "para frenar el golpe. Ese reflejo es justo el que convierte una bajada temporal en una pérdida "
                    "permanente: el riesgo no está en el mercado, está en la reacción."))

    # 2) Quiere una vida más cara pero no genera margen
    if coste_ideal and ingreso and coste_ideal > ingreso * 1.2 and tasa < 10:
        out.append(("Aspiras a más vida de la que hoy financias",
                    "La vida que describes como ideal cuesta bastante más de lo que ingresas, pero tu ahorro actual "
                    "(%s%%) no construye el capital que esa vida exige. El sueño y el ritmo van, ahora mismo, en "
                    "direcciones distintas: o sube el motor de ingresos, o se ajusta la meta." % ("%g" % round(tasa, 1))))

    # 3) Reconoce 'en rumbo' pero los números no acompañan
    if resp.get("VIS-03") == 0 and tasa < 8 and coste_ideal and ingreso and coste_ideal > ingreso:
        out.append(("Te ves 'en rumbo', pero las matemáticas piden una segunda lectura",
                    "Sientes que tu trayectoria te lleva a tu vida ideal, y a la vez tu tasa de ahorro y la brecha "
                    "de ingresos dicen lo contrario. Esa distancia entre la sensación y el dato es, casi siempre, "
                    "lo más caro de un plan: se corrige antes mirándolo que esperando."))

    # 4) Patrimonio sólido con tensión PSÍQUICA (distorsión de seguridad).
    #    Se lee la capa de agotamiento/psique (C1), no la media global: un patrimonio sano
    #    diluye la media y enmascararía justo el "rico pero en alerta".
    psique = p.get("C1", {}).get("score", 0)
    if patrimonio >= 80000 and psique >= 50:
        out.append(("Tienes el respaldo, pero no la calma",
                    "Tus números objetivos son sólidos —un patrimonio de %s— y aun así tu relación con el dinero "
                    "vive en alerta. El problema a resolver no es financiero, es de percepción: tienes la red, "
                    "falta permitirte confiar en ella." % _eur(patrimonio)))

    # 5) Deuda declarada 'controlada' (SEED) pero C10 tensionada
    seed = resp.get("SEED-DEUDA")
    if seed in (0, 1) and p.get("C10", {}).get("score", 0) >= 55:
        out.append(("Tu deuda pesa más de lo que admites",
                    "Marcaste tu relación con la deuda como llevadera, pero tus respuestas sobre su coste y su peso "
                    "dibujan una tensión real. Reconocer el tamaño exacto del problema es el primer movimiento para "
                    "desactivarlo."))

    return out


def calcular_asesor(perfil_in):
    """Lectura segmentada segun la cobertura asesora declarada. Devuelve (titulo, texto) o None."""
    a = (perfil_in or {}).get("asesor", "") or ""
    if not a:
        return None
    al = a.lower()
    if "no tengo" in al:
        return ("Tu cobertura asesora: vas sin red",
                "Lo llevas todo tú: tiene mérito y te da control, pero también un punto ciego estructural. Nadie "
                "audita tus decisiones con ojos externos, y los sesgos propios no se ven desde dentro. Tu mayor "
                "coste no son los impuestos: es decidir sin un sistema que valide la jugada antes de moverla.")
    if "papeleo" in al or "impuestos" in al:
        return ("Tu cobertura asesora: gestoría, no estrategia",
                "Tienes una gestoría, no un estratega. Cumplir con Hacienda es obligatorio, pero no hace crecer tu "
                "patrimonio. Que sientas que vas a ciegas teniendo asesor es la señal: pagas por estar en regla, no "
                "por claridad sobre a dónde vas. Son dos servicios distintos, y el segundo es el que mueve la aguja.")
    if "confianza" in al:
        return ("Tu cobertura asesora: un activo que conviene exprimir",
                "Tener un asesor de confianza es un activo enorme; no lo sueltes. Este informe no compite con él: te "
                "da munición. Lleva a tu próxima reunión las métricas y preguntas que este diagnóstico ha destapado "
                "—tu brecha, tus palancas, tus puntos ciegos— y conviértelas en una conversación de estrategia, no de papeleo.")
    return None


def calcular_energia(perfil_in):
    """Relacion energia-tiempo declarada -> diagnostico. (titulo, texto) o None (estado sano)."""
    e = (perfil_in or {}).get("energia", "") or ""
    el = e.lower()
    if "opero por inercia" in el or "me falta sistema" in el:
        return ("Tu energía y tu tiempo: apasionado, pero atado",
                "Disfrutar de tu trabajo es tu mayor activo, pero lo has convertido en tu prisión. Si tu presencia es "
                "obligatoria para que entre el dinero, no tienes un negocio ni un sistema patrimonial: tienes un trabajo "
                "muy bien pagado. El objetivo no es que trabajes menos, es que pases de operar a dirigir.")
    if "quemado" in el:
        return ("Tu energía y tu tiempo: en zona de agotamiento",
                "Tu falta de tiempo libre no es un problema de agenda, es de diseño: cada hora apagando fuegos operativos "
                "es una hora que le robas a la estrategia — y eso se paga caro. La prioridad no es aguantar más, es soltar "
                "y delegar lo que te quema, para que tu negocio deje de depender de tu desgaste.")
    if "no lo disfruto" in el or "desconectar me da culpa" in el:
        return ("Tu energía y tu tiempo: tienes el tiempo, no la calma",
                "No disfrutas de desconectar porque no confías en tu estructura: cuando no miras los números, asumes que "
                "se desmoronan. La solución no es vigilar más, es un cuadro de mando que te deje cerrar el portátil "
                "sabiendo, con certeza, que todo sigue en su sitio. La tranquilidad se construye con sistema, no con vigilancia.")
    return None


def calcular_conciliacion(perfil_in):
    """Impacto en conciliacion familiar (solo si hay dependientes). (titulo, texto) o None."""
    c = (perfil_in or {}).get("conciliacion", "") or ""
    cl = c.lower()
    if "ausencia mental" in cl:
        return ("Tu conciliación: presente de cuerpo, ausente de cabeza",
                "Caes en el error del proveedor absoluto: crees que cumplir con el dinero justifica estar ausente con "
                "la cabeza. Cenar con tus hijos mientras revisas el correo o le das vueltas a un problema de dinero es "
                "el peor de los dos mundos: ni produces ni generas recuerdos. Tu desorden de sistema no te cuesta solo "
                "euros — te cuesta presencia. Un primer paso medible: bloquea una tarde esta semana, sin móvil de trabajo.")
    if "ausencia total" in cl:
        return ("Tu conciliación: en números rojos donde más duele",
                "Estás cambiando los años que no vuelven por apagar fuegos que un buen sistema resolvería sin ti. Tu "
                "negocio debería trabajar para tu familia, no tu familia pagar el precio de tu negocio. La prioridad de "
                "tu plan no es facturar más: es recuperar horas para los tuyos, porque ese es el patrimonio que no se reconstruye.")
    if "equilibrio" in cl:
        return ("Tu conciliación: has blindado lo importante",
                "Has protegido lo que de verdad importa. Este informe no toca ese equilibrio: se enfoca en optimizar tus "
                "ingresos y proteger tu patrimonio —fiscalidad, herencia— para que ese espacio que has construido con tu "
                "familia no lo amenace nunca un imprevisto financiero.")
    return None


def calcular_herencia(perfil_in):
    """Alerta de planificacion sucesoria segun lo declarado. (titulo, texto) o None. Honesto: el ISD varia por CCAA."""
    h = (perfil_in or {}).get("herencia", "") or ""
    hl = h.lower()
    if hl.startswith("no") or "solo de mis ingresos" in hl:
        return None
    if "prefiero no contar" in hl or "probable" in hl:
        return ("Tu herencia futura: prudente no depender, caro no planificar",
                "Haces bien en no construir tu plan sobre una herencia. Pero «ignorarla» tiene un coste oculto: una "
                "sucesión sin preparar puede dejar, según tu comunidad autónoma y el parentesco, desde casi nada hasta "
                "una mordida muy seria. No depender de ella es sano; no planificarla es lo caro. Son cosas distintas.")
    if "pilar" in hl or "cuento con" in hl:
        return ("Tu herencia futura: si es un pilar, blíndalo hoy",
                "Cuentas con ese patrimonio futuro como pilar — razón de más para protegerlo antes de tiempo. La "
                "sucesión es de las pocas cosas que se deciden ANTES o se pagan caro DESPUÉS: según tu comunidad "
                "autónoma y el parentesco, la diferencia entre planificar y no hacerlo puede ser enorme. Anticiparlo "
                "es proteger el esfuerzo de quien te lo deja.")
    return None


_FOCO_NOM={"C1":"mi relación emocional con el dinero","C2":"mi camino a la libertad financiera",
 "C3":"mi resistencia ante un imprevisto","C4":"la eficiencia de mi gasto","C5":"la protección de mi patrimonio y la herencia",
 "C6":"mi gasto de estatus","C7":"la concentración de mis ingresos","C8":"mi antifragilidad",
 "C9":"el gobierno de mi flujo de caja","C10":"mi salud de deuda","C11":"mi palanca de crecimiento"}

def calcular_preguntas_asesor(perfil_in, p):
    """Si el cliente TIENE asesor (papeleo o de confianza), le damos 3 preguntas para exigir estrategia. Lista o None."""
    a=((perfil_in or {}).get("asesor","") or "").lower()
    if "papeleo" not in a and "impuestos" not in a and "confianza" not in a:
        return None
    focos=[_FOCO_NOM.get(c,c) for c in sorted(p,key=lambda c:p[c]["score"],reverse=True)[:2]] if p else ["mi estructura","mi fiscalidad"]
    qs=["Mi diagnóstico señala como frentes principales %s y %s. ¿Qué plan concreto tenemos para cada uno este trimestre, más allá del papeleo?" % (focos[0], focos[1]),
        "¿Cuánto pago al año, en total, entre comisiones y gastos de gestión, y cómo lo bajamos?"]
    h=((perfil_in or {}).get("herencia","") or "").lower()
    if h and not h.startswith("no"):
        qs.append("¿Qué hacemos hoy para que una sucesión futura no se lleve en impuestos una parte que aún es evitable?")
    return qs


def calcular_ratios(datos, perfil_in):
    """Ratios financieros con umbral y semaforo. Cada uno solo aparece si hay datos para calcularlo."""
    ing = _num(datos, "ingreso_mensual"); gasto = _num(datos, "gasto_mensual"); pat = _num(datos, "patrimonio") or 0
    ahorro = _num(datos, "ahorro_mensual") or 0
    colchon = _num(datos, "colchon_liquido"); cuota = _num(datos, "cuota_deuda"); cvm = _num(datos, "coste_vivienda")
    deuda = _num(datos, "deuda_total"); pctv = _num(datos, "pct_vivienda"); pension = _num(datos, "pension_estimada")
    R = []
    def add(n, v, e, a): R.append({"nombre": n, "valor": v, "estado": e, "accion": a})
    if colchon is not None and gasto:
        m = colchon / gasto
        add("Fondo de emergencia", "%.1f meses" % m, "verde" if m >= 6 else ("ambar" if m >= 3 else "rojo"),
            "Construye tu colchón hasta 3-6 meses de gastos en una cuenta remunerada antes de invertir." if m < 3 else
            ("Llévalo hacia los 6 meses: es lo que te da poder para decir que no." if m < 6 else "Sólido. No dejes parado más de lo necesario."))
    if ing:
        t = 100 * ahorro / ing
        add("Tasa de ahorro", "%.0f%%" % t, "verde" if t >= 20 else ("ambar" if t >= 10 else "rojo"),
            "Automatiza el ahorro el día de cobro y audita tus tres mayores gastos fijos." if t < 20 else "Gran ritmo; dirige el excedente a que el dinero genere dinero.")
    if cvm is not None and ing:
        cv = 100 * cvm / ing
        add("Carga de vivienda", "%.0f%% de tus ingresos" % cv, "verde" if cv < 30 else ("ambar" if cv < 40 else "rojo"),
            "Tu techo pesa demasiado; revisa refinanciación, condiciones o tamaño." if cv >= 30 else "En zona sana.")
    if cuota is not None and ing:
        dti = 100 * cuota / ing
        add("Carga de deuda (DTI)", "%.0f%% de tus ingresos" % dti, "verde" if dti < 30 else ("ambar" if dti < 35 else "rojo"),
            "Plan de amortización o reestructuración: ataca primero la deuda más cara." if dti >= 35 else "Bajo control.")
    if deuda is not None and pat > 0:
        ap = 100 * deuda / pat
        add("Apalancamiento", "%.0f%% de tu patrimonio" % ap, "verde" if ap < 50 else ("ambar" if ap < 80 else "rojo"),
            "Prioriza reducir la deuda cara antes de asumir más riesgo." if ap >= 50 else "Equilibrado.")
    if pctv is not None and pat > 0:
        add("Concentración patrimonial", "%.0f%% en un solo activo" % pctv, "verde" if pctv < 40 else ("ambar" if pctv < 60 else "rojo"),
            "Plan de diversificación por clases de activo: no dependas de una sola pieza." if pctv >= 50 else "Razonable.")
    if pat > 0 and gasto:
        ac = pat / (gasto * 12)
        add("Independencia financiera", "%.1f años de vida cubiertos" % ac, "verde" if ac >= 25 else ("ambar" if ac >= 10 else "rojo"),
            "Proyecta tu hito de libertad y las palancas que lo acercan.")
    if pension is not None and pension > 0 and gasto:
        gap = gasto - pension
        if gap > 0:
            add("Gap de pensión", "faltan %s/mes" % _eur(gap), "rojo" if gap > gasto * 0.5 else "ambar",
                "Plan de pensiones o inversión periódica para cerrar la brecha antes de jubilarte.")
        else:
            add("Gap de pensión", "cubierto", "verde", "Tu pensión estimada cubre tu coste de vida.")
    return R


def calcular_accion_unica(ratios, p):
    """La UNA siguiente mejor acción: el frente más urgente, nombrado sin ambigüedad."""
    for r in ratios:
        if r["estado"] == "rojo":
            return r["accion"]
    for r in ratios:
        if r["estado"] == "ambar":
            return r["accion"]
    if p:
        return ("Tu base está sólida: no hay incendios. El siguiente salto ya no es defender, es construir — "
                "pon a trabajar tu excedente y tu patrimonio con un plan a años vista.")
    return "Empieza por el primer movimiento de tu plan de acción y no pases al siguiente hasta tenerlo en marcha."


def computar_extras(resp, datos, perfil_in, inst=None):
    """Punto de entrada unico. Devuelve dict listo para report_book + arq_code."""
    inst = inst or cargar_inst()
    p = perfil_scores(resp, inst["capas"])
    ratios = calcular_ratios(datos, perfil_in)
    return {
        "brecha": calcular_brecha(datos, resp, perfil_in),
        "ratios": ratios,
        "accion_unica": calcular_accion_unica(ratios, p),
        "palancas": calcular_palancas(datos, p, perfil_in, resp),
        "contradicciones": calcular_contradicciones(datos, resp, perfil_in, p),
        "energia": calcular_energia(perfil_in),
        "conciliacion": calcular_conciliacion(perfil_in),
        "preguntas_asesor": calcular_preguntas_asesor(perfil_in, p),
        "asesor": calcular_asesor(perfil_in),
        "herencia": calcular_herencia(perfil_in),
        "arq_code": arq_desde_perfil(perfil_in),
        "_p": p,
    }


if __name__ == "__main__":
    inst = cargar_inst()
    print("capas:", [c["code"] for c in inst["capas"]])
