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


def _num0(d, k):
    """Como _num pero admite 0 como valor legítimo (p.ej. rentas pasivas = 0)."""
    try:
        x = float(d.get(k))
        return x if x >= 0 else None
    except (TypeError, ValueError):
        return None


def _perfil_laboral_txt(perfil_in):
    pl = (perfil_in or {}).get("perfil_laboral")
    return " ".join(pl) if isinstance(pl, list) else (pl or "")


def _es_empresario(perfil_in):
    t = _perfil_laboral_txt(perfil_in).lower()
    return ("empresa" in t) or ("utónom" in t) or ("autonom" in t)


def _es_rentista(perfil_in):
    """Vive del rendimiento de su capital (NO pensión, NO trabajo activo). Si además trabaja, no es rentista puro."""
    t = _perfil_laboral_txt(perfil_in).lower()
    rent = ("rentista" in t) or ("vivo de las rentas" in t)
    activo = ("empleado" in t) or ("utónom" in t) or ("autonom" in t) or ("empresa" in t)
    return rent and not activo


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


def _palancas_rentista(datos, p, perfil_in, resp=None):
    """Lente del rentista: el problema no es crecer ingresos, es que el capital dure, rente y resista la inflación."""
    pat = _num(datos, "patrimonio") or 0.0
    gasto = _num(datos, "gasto_mensual")
    out = []
    if pat > 0 and gasto:
        retiro = 100 * (gasto * 12) / pat
        if retiro > 4.5:
            out.append(("Estás consumiendo tu capital, no solo sus frutos",
                        "Tu coste de vida (%s/año) es un %g%% de tu patrimonio. Por encima del 4%% sostenido no vives de las "
                        "rentas: te comes el principal, y a este ritmo el capital mengua. La prioridad no es crecer, es ajustar "
                        "el retiro o hacer que tu capital rente más." % (_eur(gasto * 12), round(retiro, 1))))
        elif retiro < 3:
            out.append(("Tu capital aguanta de sobra: la pregunta es si trabaja",
                        "Vives con holgura sobre tu patrimonio (un %g%% de retiro al año, por debajo del 4%% prudente). El riesgo "
                        "ya no es quedarte corto: es que ese capital rente poco o pierda contra la inflación. Tu palanca es la "
                        "eficiencia, no el ahorro." % round(retiro, 1)))
        else:
            out.append(("Vives de tus rentas, justo en el filo del 4%",
                        "Tu retiro ronda el 4%% de tu patrimonio: el límite clásico de sostenibilidad. Funciona, pero sin margen "
                        "— un mal año de mercado o un repunte de inflación puede romperlo. Conviene un colchón y reglas de retiro flexibles."))
    out.append(("Tu mayor enemigo no es el mercado: es la inflación",
                "Para quien vive de rentas, el riesgo silencioso es que tus ingresos compren cada año un poco menos. Una renta "
                "que no se actualiza pierde poder de compra sin que se note. Asegúrate de que parte de tu capital crezca con la "
                "inflación, no solo de que rente hoy."))
    if p.get("C7", {}).get("score", 0) >= 50:
        out.append(("Tus rentas dependen de pocas piezas",
                    "Si tu patrimonio renta a través de uno o dos activos —un alquiler, un solo fondo—, un problema en cualquiera "
                    "(un inquilino que falla, un sector que cae) te toca el sustento entero. Diversificar las fuentes de renta es, "
                    "para un rentista, lo que diversificar ingresos es para quien trabaja."))
    out.append(("La fiscalidad de tus rentas es tu palanca silenciosa",
                "Vivir del capital tiene un margen fiscal que casi nadie aprovecha: cómo y cuándo materializas rentas, la "
                "estructura desde la que cobras, el orden en que vendes. Optimizarlo puede valer más que un punto de "
                "rentabilidad — y es justo el terreno de un family office."))
    return out


def calcular_palancas(datos, p, perfil_in, resp=None):
    """Palancas ofensivas, todas derivadas de datos reales. Devuelve lista de (titulo, texto)."""
    if _es_rentista(perfil_in):
        return _palancas_rentista(datos, p, perfil_in, resp)
    ingreso = _num(datos, "ingreso_mensual")
    gasto = _num(datos, "gasto_mensual")
    ahorro = _num(datos, "ahorro_mensual") or 0.0
    patrimonio = _num(datos, "patrimonio") or 0.0
    coste_ideal = _num(datos, "coste_vida_ideal")
    invierte = (perfil_in or {}).get("invierte", "")
    out = []

    # 1) Flujo de caja: tasa real vs consciente y el excedente sin destino
    if ingreso:
        superavit = ingreso - (gasto or 0)
        gap = max(0.0, superavit - ahorro)
        tasa_real = round(100 * max(0.0, superavit) / ingreso)
        tasa_consc = round(100 * ahorro / ingreso)
        if gap >= max(200, ingreso * 0.08):
            out.append(("Tus números dicen que sobra dinero cada mes: ¿dónde está?",
                        "Según lo que has declarado, entran %s más de lo que gastas, y solo %s tiene un destino fijo: tu tasa "
                        "de ahorro podría ser del %d%%, no el %d%% que parece. Pero seamos honestos: si no ves ese excedente, "
                        "no asumas que sobra — casi siempre se va en lo que el presupuesto mensual no recoge (impuestos "
                        "trimestrales, imprevistos, gastos sueltos). El trabajo no es recortar, es hacer visible a dónde va "
                        "cada euro y decidir tú su destino." % (_eur(superavit), _eur(ahorro), tasa_real, tasa_consc)))
        elif tasa_consc < 10:
            out.append(("Tu tijera de ahorro está casi cerrada",
                        "Ahorras un %d%% de lo que ingresas (%s al mes) y tu gasto se come casi todo el ingreso. Es la "
                        "palanca de mayor impacto: cada punto que la subas adelanta tu libertad años, no meses. Antes de "
                        "buscar más rentabilidad, ensancha esta tijera." % (tasa_consc, _eur(ahorro))))
        else:
            out.append(("Tu tijera de ahorro ya trabaja a tu favor",
                        "Ahorras un %d%% de tus ingresos (%s/mes) y lo diriges a un destino. Mantén ese hábito y haz que "
                        "ese excedente genere dinero: el siguiente salto es de eficiencia, no de esfuerzo." % (tasa_consc, _eur(ahorro))))

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

    # 6) Eficiencia de flujos societarios (S.L.) — SOLO empresarios reales (defensa: nunca a un asalariado)
    if resp and resp.get("C11-11") == 2 and _es_empresario(perfil_in):
        out.append(("Tu palanca no es un sueldo: es la eficiencia de tu sociedad",
                    "El motor que genera tu excedente se queda atrapado dentro de la empresa por el miedo al impacto "
                    "fiscal del reparto. Tu reto no es 'ganar más', sino diseñar una pasarela eficiente entre tu sociedad "
                    "y tu patrimonio personal: optimizar el Impuesto de Sociedades y planificar extracciones —dividendos, "
                    "nómina, estructura— que maximicen tu liquidez neta sin regalar dinero a Hacienda. Es de las palancas "
                    "más rentables que existen, y solo está al alcance de quien tiene empresa, como tú."))

    # 7) Comisiones de inversión que erosionan la rentabilidad en silencio
    invertible_com = _num0(datos, "inversiones_liquidas") or 0
    if resp and resp.get("C2-14") == 2 and invertible_com >= 10000:
        coste = invertible_com * 0.015
        out.append(("Tus comisiones te comen la rentabilidad en silencio",
                    "No saber qué pagas casi siempre significa pagar de más. Sobre tu cartera invertida, una comisión típica "
                    "de banco (~1,5%%) son unos %s al año — y a 20 años, por interés compuesto, puede costarte cerca "
                    "de un tercio de lo que habrías acumulado. Saber el dato y bajarlo es rentabilidad garantizada." % _eur(coste)))

    # 8) Rentas pasivas: subir ingresos sin vender más tiempo
    rp = _num0(datos, "renta_pasiva")
    if ingreso and rp is not None:
        pp = 100 * rp / ingreso
        if rp == 0:
            out.append(("Hoy no tienes ni un euro que entre sin tu tiempo",
                        "Todo tu ingreso depende de que tú estés presente. Quienes llegan lejos casi siempre comparten una "
                        "cosa: dejaron de depender de una sola fuente —una renta de alquiler, dividendos, intereses o un "
                        "ingreso que no exige sus horas. No hace falta empezar grande; hace falta empezar. La primera "
                        "fuente pasiva es la que más cuesta y la que más libera."))
        elif pp < 30:
            out.append(("Tus rentas pasivas ya empujan: ahora amplíalas",
                        "Un %s%% de lo que ingresas ya no depende de tu tiempo (%s/mes). Esa es la palanca correcta: "
                        "reinvierte lo que generan para que crezcan solas, hasta que un día cubran tu coste de vida. "
                        "Ese es el punto exacto donde el trabajo deja de ser obligatorio y pasa a ser elección." % (("%g" % round(pp, 1)), _eur(rp))))

    # 9) Vas con retraso respecto a tu meta y eres conservador: el coste de la prudencia excesiva (gobernado por el horizonte)
    edad = _num(datos, "edad")
    detras = bool(coste_ideal and ingreso and coste_ideal > ingreso)
    conservador = ("nada" in invierte.lower()) or (invierte == "")
    if detras and conservador:
        if edad and edad >= 55:
            out.append(("Vas con retraso y el margen de tiempo se acorta",
                        "Tu meta pide más de lo que hoy generas y tu horizonte ya no es largo. Aquí la respuesta NO es "
                        "asumir más riesgo para recuperar — cerca de la meta es justo cuando más se pierde. Tus palancas "
                        "reales son tres: subir lo que aportas, ajustar la meta a lo posible y rentabilizar tu ahorro "
                        "con prudencia, sin exponerlo a un susto que no te daría tiempo a recuperar."))
        else:
            out.append(("Ir con retraso y ser conservador no caben juntos",
                        "Tu vida ideal pide más de lo que hoy generas y tu dinero no está invertido. Cuando vas por "
                        "detrás de tu meta y tienes años por delante, el mayor riesgo deja de ser el mercado y pasa a "
                        "ser la inacción: el dinero parado no recupera el terreno perdido. No es licencia para apostar "
                        "—es poner tu ahorro a trabajar con un plan acorde a tu plazo—, pero a tu horizonte el exceso de "
                        "prudencia es el riesgo más caro que corres."))

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
    inv_liq = _num0(datos, "inversiones_liquidas")
    if colchon is not None and gasto:
        m = colchon / gasto
        add("Fondo de emergencia", "%.1f meses en líquido inmediato" % m, "verde" if m >= 6 else ("ambar" if m >= 3 else "rojo"),
            "Construye tu colchón hasta 3-6 meses de gastos en una cuenta remunerada antes de invertir." if m < 3 else
            ("Llévalo hacia los 6 meses: es lo que te da poder para decir que no." if m < 6 else "Sólido. No dejes parado más de lo necesario."))
        if inv_liq is not None and inv_liq > 0:
            mr = (colchon + inv_liq) / gasto
            add("Músculo de resistencia total", "%.0f meses realizables" % mr,
                "verde" if mr >= 12 else ("ambar" if mr >= 6 else "rojo"),
                ("Sumando lo que rescatarías en días, tu resistencia real es muy superior a tu colchón inmediato: no estás desprotegido, solo tienes poco en líquido inmediato." if m < 3
                 else "Tu colchón inmediato más lo realizable te dan un margen amplio ante cualquier imprevisto."))
    if ing:
        sup = max(0.0, ing - (gasto or 0))
        t_real = 100 * sup / ing
        t_consc = 100 * ahorro / ing
        gap = max(0.0, sup - ahorro)
        if gap >= max(200, ing * 0.08):
            add("Tasa de ahorro", "%.0f%% real · %.0f%% con destino" % (t_real, t_consc),
                "verde" if t_real >= 20 else ("ambar" if t_real >= 10 else "rojo"),
                "Tu capacidad es alta; el problema es que %s/mes no tienen destino. Automatiza ese excedente el día 1, no recortes." % _eur(gap))
        else:
            add("Tasa de ahorro", "%.0f%%" % t_consc, "verde" if t_consc >= 20 else ("ambar" if t_consc >= 10 else "rojo"),
                "Automatiza el ahorro el día de cobro y audita tus tres mayores gastos fijos." if t_consc < 20 else "Gran ritmo; dirige el excedente a que el dinero genere dinero.")
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
    rp = _num0(datos, "renta_pasiva")
    if rp is not None and ing:
        pp = 100 * rp / ing
        add("Ingresos pasivos", "%.0f%% de tus ingresos" % pp,
            "verde" if pp >= 30 else ("ambar" if pp >= 10 else "info"),
            "Hoy casi todo lo que ingresas depende de tu tiempo. Tu siguiente frontera es construir una fuente que trabaje sin ti." if pp < 10 else
            ("Ya tienes rentas que no dependen de tu tiempo: el objetivo es ampliarlas hasta que cubran tu coste de vida." if pp < 30 else
             "Tus rentas pasivas ya sostienen una parte real de tu vida. Protégelas y sigue componiendo."))
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


def calcular_fortuna_neta(datos):
    """Foto de fortuna neta: patrimonio (ya neto) = activos - pasivos, y colchón en meses.
    El cuadro de mando semestral vivo es de Adapta; aquí damos solo la foto y el hábito."""
    pat = _num(datos, "patrimonio")
    if pat is None:
        return None
    deuda = _num(datos, "deuda_total") or 0
    gasto = _num(datos, "gasto_mensual")
    colch = _num(datos, "colchon_liquido")
    inv_liq = _num0(datos, "inversiones_liquidas")
    meses = round(colch / gasto, 1) if (colch and gasto) else None
    out = {"neta": pat, "activos": pat + deuda, "pasivos": deuda, "colchon_meses": meses}
    # Musculo de resistencia TOTAL: colchon liquido + inversiones realizables en dias.
    # Resuelve el falso "estas desprotegido" cuando hay patrimonio realizable.
    if inv_liq is not None:
        realizable = (colch or 0) + inv_liq
        out["realizable"] = realizable
        out["resistencia_meses"] = round(realizable / gasto, 1) if gasto else None
        # Asignacion para el donut (sin suposiciones: solo lo declarado)
        parado = colch or 0
        resto = max(0.0, pat - parado - inv_liq)  # vivienda, negocio, inmuebles, iliquido
        out["asignacion"] = {"parado": parado, "realizable_invertido": inv_liq, "resto": resto}
    return out


def calcular_deuda_tipo(resp, datos):
    """Lee C10-07 (¿la deuda te quita o te da dinero?) y la nombra palanca/neutra/freno."""
    v = resp.get("C10-07")
    if v is None:
        return None
    if v == 0:
        return ("Tu deuda, hoy, es una palanca",
                "En conjunto tu deuda te da dinero: financia activos que rinden más de lo que te cuesta. Bien usada, "
                "la deuda barata es una herramienta de crecimiento, no un peso. Tu tarea es de vigilancia: que su coste "
                "siga por debajo de lo que renta, y no confundirla nunca con la deuda de consumo.")
    if v == 1:
        return ("Tu deuda, hoy, es neutra: tú decides su dirección",
                "Ni te hunde ni te impulsa. Ese es justo el punto de bifurcación: puedes convertirla en palanca —que "
                "financie algo que rinde— o dejar que derive en freno. La diferencia no la marca la deuda, la marcas tú "
                "con para qué la usas.")
    return ("Tu deuda, hoy, es un freno",
            "Tu deuda te quita dinero: es consumo que pagas con intereses, sin nada que rinda detrás. Es lo primero que "
            "hay que desactivar, empezando por la más cara, porque cada euro de intereses es un euro que no construye tu "
            "libertad. No es una cuestión moral: es la rentabilidad más segura que existe.")


def calcular_presupuesto(datos, perfil_in):
    """Marco de presupuesto a partir de lo conocido. Para empresarios, separa familia/negocio.
    El dashboard vivo (casa/negocio, fijo/variable) es deliverable de Adapta; aquí, el marco."""
    gasto = _num(datos, "gasto_mensual")
    if not gasto:
        return None
    ing = _num(datos, "ingreso_mensual")
    viv = _num(datos, "coste_vivienda") or 0
    cuota = _num(datos, "cuota_deuda") or 0
    resto = max(0.0, gasto - viv - cuota)
    rec = None
    if ing:
        rec = {"necesidades": round(ing * 0.50), "deseos": round(ing * 0.30), "ahorro": round(ing * 0.20)}
    return {"gasto": gasto, "ingreso": ing, "vivienda": viv, "deuda": cuota, "resto": resto,
            "empresario": _es_empresario(perfil_in), "recomendado": rec}


def calcular_compromiso(datos, perfil_in, brecha, p):
    """Contrato contigo mismo: objetivos con los propios números del cliente + reglas a su medida."""
    coste_ideal = _num(datos, "coste_vida_ideal")
    ingreso = _num(datos, "ingreso_mensual")
    edad = _num(datos, "edad") or _num(perfil_in or {}, "edad")
    # MODO CRISIS: agotamiento clínico (C1 alto) + presión financiera real -> estabilizar, no exigir cifras.
    gasto = _num(datos, "gasto_mensual"); colch = _num(datos, "colchon_liquido")
    cuota = _num(datos, "cuota_deuda"); ahorro_m = _num0(datos, "ahorro_mensual") or 0
    inv_liq = _num0(datos, "inversiones_liquidas")
    c1 = (p or {}).get("C1", {}).get("score", 0)
    meses = (colch / gasto) if (colch and gasto) else None
    realizable_meses = (((colch or 0) + (inv_liq or 0)) / gasto) if gasto else None
    tasa = (100 * ahorro_m / ingreso) if ingreso else 100
    dti = (100 * cuota / ingreso) if (cuota and ingreso) else 0
    presion = ((meses is not None and meses < 3) or (tasa < 10) or (dti >= 35)
               or bool(ingreso and gasto and gasto >= ingreso * 0.95))
    tiene_recursos = (realizable_meses is not None and realizable_meses >= 6)  # puede realizar 6+ meses: no es crisis de recursos
    if (c1 >= 65) and presion and not tiene_recursos:
        return {"crisis": True, "objetivo_ingresos": None, "numero_libertad": None, "plazo_anios": None, "edad": edad,
                "reglas": [
                    "Voy a frenar la bola de la deuda más cara antes que ninguna otra cosa.",
                    "Voy a separar mi dinero en tres cajas —lo justo para vivir, un colchón mínimo y el resto— para recuperar el control del mes.",
                    "Voy a cuidar mi descanso y mi cabeza: ningún plan funciona sobre el agotamiento, y mi salud es parte del plan.",
                    "Voy a revisar estos tres pasos cada mes, sin exigirme cifras que hoy no me corresponden."]}
    if _es_rentista(perfil_in):
        return {"crisis": False, "rentista": True, "objetivo_ingresos": None, "numero_libertad": None,
                "plazo_anios": None, "edad": edad,
                "reglas": [
                    "Mantener mi tasa de retiro en torno al 4% para no consumir el principal.",
                    "Asegurar que parte de mi capital crezca con la inflación, no solo que rente hoy.",
                    "Diversificar mis fuentes de renta para no depender de un solo activo.",
                    "Optimizar la fiscalidad y el orden en que materializo mis rentas.",
                    "Revisar mi patrimonio y mi tasa de retiro cada seis meses, sin excepciones."]}
    objetivo_ing = coste_ideal or (round(ingreso * 1.3) if ingreso else None)
    numero = (brecha or {}).get("numero_ideal") if brecha else None
    if not numero and coste_ideal:
        numero = coste_ideal * 12 * 25
    reglas = ["Construir activos que generen ingresos recurrentes, no solo cambiar mi tiempo por dinero.",
              "Revisar mi fortuna neta, mis ingresos y mis gastos cada 6 meses, sin excepciones ni autoengaños."]
    rp = _num0(datos, "renta_pasiva")
    if ingreso and (rp is None or (100 * rp / ingreso) < 30):
        reglas.append("Crear o ampliar al menos una fuente de ingresos que no dependa de mi tiempo.")
    ahorro = _num(datos, "ahorro_mensual") or 0
    if ingreso and (100 * ahorro / ingreso) < 20:
        reglas.append("Automatizar mi ahorro el día de cobro, antes de gastar.")
    invierte = (perfil_in or {}).get("invierte", "") or ""
    if "nada" in invierte.lower() or invierte == "":
        reglas.append("Poner mi patrimonio a trabajar con un plan, en lugar de dejarlo parado.")
    else:
        reglas.append("Invertir de forma constante, reinvertir los beneficios y no vender por miedo.")
    if _es_empresario(perfil_in):
        reglas.append("Separar siempre las cuentas de mi familia y las de mi negocio.")
    reglas.append("Pensar en décadas, no en meses: la disciplina de hoy es la libertad de mañana.")
    plazo = int(max(5, 65 - edad)) if edad else None
    return {"crisis": False, "objetivo_ingresos": objetivo_ing, "numero_libertad": numero,
            "plazo_anios": plazo, "edad": edad, "reglas": reglas[:6]}


def calcular_vivienda(datos, perfil_in):
    """La 'ola de vivienda': UNA pregunta (tenencia) desbloquea tres diagnÃ³sticos
    -hipoteca variable, alquiler forzoso, vivienda pagada- con los nÃºmeros reales del cliente."""
    ten = ((perfil_in or {}).get("vivienda_tenencia", "") or "").strip()
    if not ten:
        return {"modo": None}
    t = ten.lower()
    coste = _num(datos, "coste_vivienda")
    ingreso = _num(datos, "ingreso_mensual")
    ahorro = _num0(datos, "ahorro_mensual") or 0
    pct_viv = _num0(datos, "pct_vivienda")
    carga = (100.0 * coste / ingreso) if (coste and ingreso) else None
    tasa = (100.0 * ahorro / ingreso) if ingreso else None

    def fmt(n):
        try:
            return f"{int(round(n)):,}".replace(",", ".") + " €"
        except Exception:
            return "—"

    # --- Hipoteca a tipo VARIABLE: el riesgo que no aparece en las cuentas de hoy ---
    if "variable" in t:
        parr = ["Tu cuota de hoy no es tu cuota de siempre. Es la única gran factura de tu vida que "
                "puede subir sin que tú decidas nada: basta con que suban los tipos de interés."]
        golpe = coste * 0.30 if coste else None
        severidad = "media"
        if coste:
            nueva = coste + golpe
            linea = (f"Hoy pagas {fmt(coste)} al mes. Si tu cuota subiera un 30% —lo que miles de "
                     f"familias vivieron entre 2022 y 2023— pasarías a {fmt(nueva)}: {fmt(golpe)} más cada mes.")
            if ahorro and golpe > ahorro:
                linea += (f" Ese golpe se comería entero lo que hoy ahorras ({fmt(ahorro)}) y aún faltaría. "
                          "No es una hipótesis lejana: es tu punto más frágil.")
                severidad = "alta"
            elif ahorro:
                linea += (f" Ese golpe se llevaría buena parte de lo que hoy ahorras ({fmt(ahorro)}). "
                          "Conviene tenerlo medido antes de que ocurra, no después.")
            parr.append(linea)
        if carga is not None and carga >= 35:
            severidad = "alta"
        parr.append("No se trata de pasarte a tipo fijo a cualquier precio, sino de saber tu número: "
                    "cuánto puede subir tu cuota antes de que tu mes deje de cuadrar. Tenlo calculado hoy, "
                    "con calma, y no el día que llegue la carta del banco.")
        return {"modo": "variable", "titulo": "Tu hipoteca a tipo variable: el riesgo que no está en tus cuentas de hoy",
                "etiqueta": "riesgo oculto", "parrafos": parr, "severidad": severidad}

    # --- ALQUILER: forzoso (sin culpa, sin falsa esperanza) vs. flexible ---
    if "alquiler" in t:
        forzoso = (carga is not None and carga >= 40) and (tasa is not None and tasa < 10)
        if forzoso:
            parr = ["Con tus números, el alquiler se lleva una parte muy grande de lo que entra y apenas "
                    "queda margen para ahorrar. Quiero ser claro contigo: eso no te convierte en alguien que "
                    "«tira el dinero». El alquiler es, hoy, lo que tu situación permite, y pagar tu "
                    "techo es exactamente lo que debes hacer.",
                    "La trampa sería fijarte la compra de una vivienda como el objetivo de este año. Con esta "
                    "carga, no lo es, y forzarlo solo añadiría angustia. El objetivo real es más cercano y más "
                    "poderoso: recuperar aire en el mes y construir un primer colchón, aunque empiece siendo pequeño.",
                    "Y un aviso honesto: el alquiler es el único gasto que puede subir de golpe sin tu permiso, "
                    "el día que toca renovar. Por eso tu colchón no es un lujo: es tu defensa frente a esa subida."]
            return {"modo": "alquiler_forzoso", "titulo": "El alquiler no es tirar el dinero: es lo que hoy puedes",
                    "etiqueta": "sin culpa", "parrafos": parr, "severidad": "alta"}
        parr = ["Vivir de alquiler no es un fracaso financiero: es flexibilidad. No tienes capital inmovilizado "
                "en ladrillo ni dependes de los tipos de interés. Tu reto no es comprar por comprar.",
                "Pero esa ventaja solo cuenta si el dinero que no inmovilizas trabaja. Si el alquiler te deja "
                "margen y ese margen se evapora en gasto, entonces sí estás perdiendo: no por alquilar, sino por "
                "no poner a trabajar lo que ahorras.",
                "Vigila la renovación: el alquiler puede subir sin que tú decidas. Un colchón de varios meses es "
                "lo que convierte esa flexibilidad en libertad, y no en vértigo."]
        return {"modo": "alquiler", "titulo": "Tu alquiler: flexibilidad hoy, decisión consciente mañana",
                "etiqueta": "flexibilidad", "parrafos": parr, "severidad": "media"}

    # --- Vivienda YA PAGADA: la mayor red de seguridad ---
    if "pagada" in t:
        parr = ["Tienes algo que muy pocos consiguen: un techo que ya es tuyo. Tu suelo de gasto baja, ningún "
                "tipo de interés te afecta y, pase lo que pase, tienes dónde vivir. Es la base sobre la que se "
                "construye todo lo demás."]
        if pct_viv and pct_viv >= 70:
            parr.append("El riesgo contrario también existe, y en tu caso conviene mirarlo: mucho patrimonio "
                        "dormido en ladrillo y poca liquidez disponible. Tu casa vale, pero no paga la compra del "
                        "súper. Asegúrate de tener también capital líquido que trabaje.")
        else:
            parr.append("El siguiente paso es que el ahorro que ya no se va en vivienda no se diluya en gasto, "
                        "sino que se convierta en activos que generen renta.")
        return {"modo": "pagada", "titulo": "Tu vivienda pagada: tu mayor red de seguridad",
                "etiqueta": "fortaleza", "parrafos": parr, "severidad": "baja"}

    # --- Hipoteca a tipo FIJO: compro certeza ---
    if "fijo" in t:
        parr = ["Hiciste algo más valioso de lo que parece: fijaste tu cuota. Aunque los tipos se disparen, tu "
                "mes no se mueve. Esa certeza es un activo: te protege del riesgo que hoy quita el sueño a quien "
                "tiene hipoteca variable.",
                "Aprovéchala. Sabes exactamente cuánto pagas durante años, así que el resto de tu dinero puede "
                "trabajar con un plan, sin el sobresalto de una cuota que cambia."]
        return {"modo": "fijo", "titulo": "Tu hipoteca a tipo fijo: compraste certeza",
                "etiqueta": "estabilidad", "parrafos": parr, "severidad": "baja"}

    # --- Cedida / familiares: ventaja enorme y temporal ---
    if "familiares" in t or "cedida" in t:
        parr = ["Hoy el mayor gasto de casi todo el mundo —el techo— es prácticamente cero para ti. Es "
                "una ventaja brutal. Pero es temporal: en algún momento tendrás que pagar por vivir, y el salto "
                "será grande.",
                "La pregunta que decide tu futuro es qué haces hoy con ese margen. Si lo conviertes en colchón y "
                "en activos, llegarás a ese salto preparado. Si se diluye en gasto, el día que llegue te pillará "
                "empezando de cero."]
        return {"modo": "cedida", "titulo": "Vives sin coste de vivienda: una ventaja enorme y temporal",
                "etiqueta": "oportunidad", "parrafos": parr, "severidad": "media"}

    return {"modo": None}


def computar_extras(resp, datos, perfil_in, inst=None):
    """Punto de entrada unico. Devuelve dict listo para report_book + arq_code."""
    inst = inst or cargar_inst()
    p = perfil_scores(resp, inst["capas"])
    ratios = calcular_ratios(datos, perfil_in)
    brecha = calcular_brecha(datos, resp, perfil_in)
    compromiso = calcular_compromiso(datos, perfil_in, brecha, p)
    return {
        "crisis": bool(compromiso.get("crisis")),
        "rentista": bool(compromiso.get("rentista")) or _es_rentista(perfil_in),
        "brecha": brecha,
        "ratios": ratios,
        "accion_unica": calcular_accion_unica(ratios, p),
        "palancas": calcular_palancas(datos, p, perfil_in, resp),
        "contradicciones": calcular_contradicciones(datos, resp, perfil_in, p),
        "energia": calcular_energia(perfil_in),
        "conciliacion": calcular_conciliacion(perfil_in),
        "preguntas_asesor": calcular_preguntas_asesor(perfil_in, p),
        "asesor": calcular_asesor(perfil_in),
        "herencia": calcular_herencia(perfil_in),
        "fortuna_neta": calcular_fortuna_neta(datos),
        "deuda_tipo": calcular_deuda_tipo(resp, datos),
        "presupuesto": calcular_presupuesto(datos, perfil_in),
        "vivienda": calcular_vivienda(datos, perfil_in),
        "compromiso": compromiso,
        "arq_code": arq_desde_perfil(perfil_in),
        "perfil_in": perfil_in,
        "_p": p,
    }


if __name__ == "__main__":
    inst = cargar_inst()
    print("capas:", [c["code"] for c in inst["capas"]])
