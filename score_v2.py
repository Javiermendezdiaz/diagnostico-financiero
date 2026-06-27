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
            if it.get("atencion"):   # control de atencion: no puntua ninguna faceta
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
    # NUMERO CANONICO UNICO: para que TODO el informe cite UN solo "tu numero de libertad"
    # con su marco etiquetado. Por defecto planificamos para la VIDA QUE QUIERES (ideal),
    # que es la promesa del producto; la vida de hoy queda como referencia explicita.
    # AJUSTE FISCAL ESPANA: la regla del 4% (Trinity, USA) es BRUTA. En Espana las rentas
    # del ahorro tributan ~19-28%; para vivir de rentas NETAS hace falta mas capital.
    # numero_neto = coste_anual / (0.04 * (1 - t)). Con t~0.21 sale ~x31.6 (no x25).
    _T_AHORRO_ES = 0.21
    numero_neto_es = round(coste_ideal * 12 / (0.04 * (1 - _T_AHORRO_ES)))
    base_out = {"coste_ideal_mes": coste_ideal, "numero_ideal": numero_ideal,
                "numero_actual": numero_actual, "ahorro_mes": ahorro, "arq": arq,
                "reconocimiento": recon_txt, "patrimonio": patrimonio,
                "numero_canonico": numero_ideal, "marco_canonico": "vida ideal",
                "numero_hoy": numero_actual, "marco_hoy": "vida de hoy",
                "numero_neto_es": numero_neto_es, "tipo_ahorro_es": int(_T_AHORRO_ES * 100)}
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


def validez(resp, datos, perfil_in, p, contradicciones=None, inst=None):
    """Indice de fiabilidad del diagnostico (escala de validez, estilo psicometrico).

    No es un juicio moral: mide CUANTO fiarse del retrato, combinando cuatro senales
    que la literatura usa para detectar respuesta poco informativa, sin una sola
    pregunta extra. Las opciones ya se barajan en pantalla por sesion, asi que estas
    senales se leen sobre la estructura real de respuesta:

      1) Cobertura      -> cuantos dominios se respondieron (mas datos, mas nitidez).
      2) Diferenciacion -> dispersion de los 12 dominios (un perfil real varia; una
                           linea plana sugiere responder en piloto automatico).
      3) Respuesta extrema -> exceso de respuestas en los polos (todo blanco o negro).
      4) Coherencia     -> contradicciones sensacion-vs-dato ya detectadas por el motor.

    Devuelve dict {banda, etiqueta, titulo, texto, indice, factores} o None.
    Blindada: cualquier error devuelve None y el informe sigue sin la caja."""
    try:
        import statistics as _stx
        pp = p or {}
        # --- scores por dominio y por item (desde las facetas ya puntuadas) ---
        dominios = []
        item_scores = []
        for v in pp.values():
            if not isinstance(v, dict):
                continue
            fac = v.get("facetas") or {}
            if fac:
                dominios.append(v.get("score", 0))
                item_scores += [s for s in fac.values() if isinstance(s, (int, float))]
        n_dom = len(dominios)
        n_items = len(item_scores)
        if n_items == 0:
            return None

        # 1) cobertura
        cobertura_baja = n_items < 12

        # 2) diferenciacion entre dominios
        disp = _stx.pstdev(dominios) if n_dom >= 3 else None
        sin_relieve = (disp is not None and disp < 7.5 and n_items >= 24)

        # 3) respuesta extrema (polos 0/100 vs intermedios)
        extremos = sum(1 for s in item_scores if s <= 10 or s >= 90)
        frac_ext = extremos / n_items if n_items else 0.0
        todo_polos = (frac_ext >= 0.92 and n_items >= 20)

        # 4) coherencia sensacion-vs-dato
        n_contra = len(contradicciones or [])

        # 5) control de atencion (instructed-response) + 6) coherencia de gemelos
        #    Senales psicometricas dedicadas que NO dependen del barajado de opciones,
        #    porque comparan la RESPUESTA real (indice -> score), no la posicion en pantalla.
        fallo_atencion = False
        pares_incoh = 0
        try:
            if inst:
                _by_id = {}
                for _c in inst.get("capas", []):
                    for _it in _c.get("items", []):
                        _by_id[_it.get("id")] = _it

                def _score_de(_id):
                    _it = _by_id.get(_id)
                    if not _it:
                        return None
                    _ix = (resp or {}).get(_id)
                    if not isinstance(_ix, int):
                        return None
                    try:
                        return _it["opciones"][_ix]["score"]
                    except Exception:
                        return None

                for _id, _it in _by_id.items():
                    if _it.get("atencion"):
                        _ix = (resp or {}).get(_id)
                        if isinstance(_ix, int) and _ix != _it.get("opcion_correcta"):
                            fallo_atencion = True
                    _par = _it.get("par_consistencia")
                    if _par:
                        _a = _score_de(_id)
                        _b = _score_de(_par)
                        if _a is not None and _b is not None and abs(_a - _b) >= 60:
                            pares_incoh += 1
        except Exception:
            fallo_atencion = False
            pares_incoh = 0

        # --- puntuacion de riesgo (conservadora: por defecto, fiabilidad alta) ---
        r = 0
        factores = []
        if fallo_atencion:
            r += 2; factores.append("una pregunta de control de lectura no encaja con el resto")
        if pares_incoh >= 2:
            r += 2; factores.append("respuestas que se contradicen entre preguntas equivalentes")
        elif pares_incoh == 1:
            r += 1; factores.append("alguna respuesta que no cuadra con su pregunta equivalente")
        if sin_relieve:
            r += 2; factores.append("respuestas muy parejas entre areas")
        if todo_polos:
            r += 2; factores.append("casi todo respondido en los extremos")
        if n_contra >= 4:
            r += 2; factores.append("varias tensiones entre lo que sientes y lo que dicen tus numeros")
        elif n_contra >= 2:
            r += 1; factores.append("alguna tension entre sensacion y dato")

        indice = max(40, 100 - r * 14 - (8 if cobertura_baja else 0))

        if cobertura_baja:
            return {
                "banda": "parcial", "etiqueta": "Base parcial", "indice": indice,
                "factores": factores,
                "titulo": "Un retrato sobre una base parcial",
                "texto": "Respondiste una parte del cuestionario. Lo que ves es valido, pero gana nitidez "
                         "cuando completas el resto: cada dominio que dejas en blanco es un trazo que le falta "
                         "al retrato.",
            }
        if r >= 3:
            return {
                "banda": "revisar", "etiqueta": "Para releer con calma", "indice": indice,
                "factores": factores,
                "titulo": "Una lectura para releer con calma",
                "texto": "Algunas de tus respuestas tiran en direcciones opuestas. No es un error: casi siempre "
                         "marca el punto exacto donde tu sensacion y tus numeros aun no se han puesto de acuerdo "
                         "— y ese desajuste suele ser lo mas valioso de mirar. Relee tu diagnostico despacio: "
                         "donde notes que algo no te cuadra del todo, probablemente este la palanca.",
            }
        if r >= 1:
            return {
                "banda": "media", "etiqueta": "Fiable, con un matiz", "indice": indice,
                "factores": factores,
                "titulo": "Tu diagnostico es fiable, con un matiz",
                "texto": "El retrato es solido. Solo un apunte para afinarlo: hay algun punto donde lo que sientes "
                         "y lo que dicen tus datos no van del todo a la par. Leelo no como una contradiccion, "
                         "sino como una pista de por donde empezar.",
            }
        return {
            "banda": "alta", "etiqueta": "Muy fiable", "indice": indice,
            "factores": factores,
            "titulo": "Tu diagnostico es muy fiable",
            "texto": "Respondiste con matices —distinguiendo entre areas y sin refugiarte en los extremos faciles—. "
                     "Eso le da a este retrato una solidez alta: puedes tomarlo como un espejo honesto, no como una "
                     "foto movida. Lo que leas aqui, te lo puedes creer.",
        }
    except Exception:
        return None


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
                "coste no son los impuestos: es decidir sin un sistema que valide la jugada antes de moverla. Y no se "
                "resuelve con una gestoría que te lleve el papeleo: lo que necesitas es asesoramiento integral —financiero, "
                "inmobiliario y fiscal bajo un mismo techo—, que mire tu patrimonio como un todo. Es justo lo que hoy no tienes.")
    if "papeleo" in al or "impuestos" in al:
        return ("Tu cobertura asesora: gestoría, no estrategia",
                "Tienes una gestoría, no un estratega. Cumplir con Hacienda es obligatorio, pero no hace crecer tu "
                "patrimonio. Que sientas que vas a ciegas teniendo asesor es la señal: pagas por estar en regla, no "
                "por claridad sobre a dónde vas. Y seamos claros: pedirle estrategia patrimonial a una gestoría es pedirle "
                "peras al olmo —no es su oficio—. Lo que te falta no es cambiar de gestor, es sumar una capa de asesoramiento "
                "integral, que mire a la vez tu fiscalidad, tus inversiones y tus inmuebles como un solo patrimonio. Ese es el "
                "servicio que mueve la aguja, y es el de un family office.")
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
 "C9":"el gobierno de mi flujo de caja","C10":"mi salud de deuda","C11":"mi palanca de crecimiento","C12":"mi disciplina de inversión"}

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
            "Asfixia inmobiliaria: por encima del 30% tu techo te quita músculo para invertir. Revisa refinanciación, condiciones o tamaño." if cv >= 30 else "En zona sana: por debajo del 30% de tus ingresos.")
    if cuota is not None and ing:
        dti = 100 * cuota / ing
        add("Carga de deuda (DTI)", "%.0f%% de tus ingresos" % dti, "verde" if dti < 30 else ("ambar" if dti < 35 else "rojo"),
            "DTI = de cada 100 € que ingresas, cuánto se va a deuda. Por encima del 35% aprieta: plan de amortización, ataca primero la deuda más cara." if dti >= 35 else "DTI = qué parte de tu ingreso se va a deuda. El tuyo está bajo control.")
    if deuda is not None and pat > 0:
        ap = 100 * deuda / pat
        add("Apalancamiento", "%.0f%% de tu patrimonio" % ap, "verde" if ap < 50 else ("ambar" if ap < 80 else "rojo"),
            "Prioriza reducir la deuda cara antes de asumir más riesgo." if ap >= 50 else "Equilibrado.")
    if pctv is not None and pat > 0:
        add("Concentración patrimonial", "%.0f%% en un solo activo" % pctv, "verde" if pctv < 40 else ("ambar" if pctv < 60 else "rojo"),
            "Plan de diversificación por clases de activo: no dependas de una sola pieza." if pctv >= 50 else "Razonable.")
    if pat > 0 and gasto:
        ac = pat / (gasto * 12)
        _val_if = ("%.1f años (~%.0f meses) de vida cubiertos" % (ac, ac*12)) if ac < 2 else ("%.1f años de vida cubiertos" % ac)
        add("Independencia financiera", _val_if, "verde" if ac >= 25 else ("ambar" if ac >= 10 else "rojo"),
            "Ponle número y fecha a tu libertad: fija tu objetivo (25 veces tu gasto anual) y dirige cada mes tu excedente a acercarlo, con tu patrimonio rentando. Es lo que convierte tu trabajo en una elección, no una obligación.")
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
                "Es lo que separa tu coste de vida (%s) de tu pensión pública estimada (%s): un plan de pensiones o inversión periódica lo cierra antes de jubilarte." % (_eur(gasto), _eur(pension)))
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


def _interp(x, pts):
    """Interpolacion lineal por tramos. pts = lista ordenada de (x, y)."""
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0) if x1 != x0 else 0
            return y0 + t * (y1 - y0)
    return pts[-1][1]


def calcular_resiliencia(datos):
    """Resiliencia financiera OBJETIVA: los meses de libertad que tu patrimonio compra.

    Es la cifra que mide de verdad lo bien o mal que estas: el patrimonio neto
    convertible en liquidez dividido por tu coste de vida. Alguien con mucho patrimonio
    y deficit mensual esta objetivamente mucho mas libre que alguien que ahorra poco
    sobre un patrimonio minimo. Devuelve None si faltan datos para calcularla.

    Polaridad de 'fragilidad': 0 = solido/libre, 100 = al limite (igual que el resto del motor).
    """
    gasto = _num(datos, "gasto_mensual")
    if not gasto:
        return None
    pat = _num(datos, "patrimonio") or 0.0          # patrimonio NETO (activos - pasivos)
    colch = _num(datos, "colchon_liquido") or 0.0
    inv = _num0(datos, "inversiones_liquidas") or 0.0
    liq = colch + inv                               # convertible en dias (rapido)
    meses_pat = pat / gasto                          # libertad total (incluye activos lentos: vivienda, negocio)
    meses_liq = liq / gasto                           # resistencia inmediata
    anios_pat = meses_pat / 12.0
    # Fragilidad objetiva: el patrimonio total manda (clave de la libertad),
    # pero la liquidez inmediata pondera para no llamar 'libre' a quien no tiene caja.
    frag_total = _interp(meses_pat, [(0, 100), (6, 80), (24, 55), (60, 35), (120, 20), (300, 3)])
    frag_liq = _interp(meses_liq, [(0, 100), (1, 90), (3, 70), (6, 45), (12, 25), (24, 10)])
    fragilidad = round(0.60 * frag_total + 0.40 * frag_liq)
    # Salud objetiva (0 fragil -> 100 solido), para mostrar como % positivo.
    resiliencia = 100 - fragilidad
    if anios_pat >= 25:
        nivel = "libertad"          # el patrimonio ya cubre la vida (regla 25x)
    elif meses_pat >= 60:
        nivel = "solido"
    elif meses_pat >= 24:
        nivel = "construccion"
    elif meses_pat >= 6:
        nivel = "ajustado"
    else:
        nivel = "expuesto"
    # Riesgo de caja: mucho patrimonio pero poca liquidez inmediata.
    iliquido = bool(meses_pat >= 24 and meses_liq < 3)
    return {
        "meses_libertad": round(meses_pat, 1),
        "anios_libertad": round(anios_pat, 1),
        "meses_liquido": round(meses_liq, 1),
        "patrimonio": pat,
        "liquido_inmediato": liq,
        "fragilidad": fragilidad,
        "resiliencia": resiliencia,
        "nivel": nivel,
        "iliquido": iliquido,
    }


_FUENTE_DEFS = [
    ("Mi trabajo activo (empleo, autónomo)", "ing_trabajo", "h_trabajo", "Trabajo activo"),
    ("Inversiones (dividendos, intereses, fondos)", "ing_inversion", "h_inversion", "Inversiones"),
    ("Alquileres de inmuebles", "ing_alquiler", "h_alquiler", "Alquileres"),
    ("Otras fuentes (un negocio que funciona sin mí, royalties…)", "ing_otros", "h_otros", "Otras fuentes"),
]


def calcular_fuentes(datos, perfil_in):
    """Mapa de fuentes de ingreso: cuántas, cuánto rinde cada una y a qué precio de tiempo (€/hora).
    La tesis: depender de una sola fuente es la mayor fragilidad financiera que existe.
    Solo se calcula sobre las fuentes que el cliente declara; nada se inventa."""
    sel = (perfil_in or {}).get("fuentes_ingreso")
    if not sel:
        return None
    if isinstance(sel, str):
        sel = [sel]
    fuentes = []
    total = 0.0
    for label, fing, fhrs, nombre in _FUENTE_DEFS:
        if label not in sel:
            continue
        ing = _num0(datos, fing) or 0.0
        hrs = _num0(datos, fhrs)
        item = {"nombre": nombre, "ingreso": ing, "horas": hrs}
        if hrs is not None and hrs > 0:
            item["eur_hora"] = round(ing / (hrs * 4.33), 1) if ing else 0.0
            item["pasiva"] = hrs <= 1
        else:
            item["eur_hora"] = None          # sin tiempo declarado: renta pura
            item["pasiva"] = True
        fuentes.append(item)
        total += ing
    n = len(fuentes)
    if n == 0:
        return None
    for it in fuentes:
        it["pct"] = round(100 * it["ingreso"] / total) if total else 0
    n_pasivas = sum(1 for it in fuentes if it["pasiva"])
    mayor = max(fuentes, key=lambda x: x["ingreso"]) if total else fuentes[0]
    activas = [it for it in fuentes if not it["pasiva"] and it.get("eur_hora")]
    peor = min(activas, key=lambda x: x["eur_hora"]) if activas else None
    return {
        "fuentes": fuentes, "n": n, "n_pasivas": n_pasivas, "n_activas": n - n_pasivas,
        "total": total, "concentracion": mayor["pct"], "mayor": mayor["nombre"],
        "peor_activa": peor, "tiene_pasiva": n_pasivas > 0,
    }


_RV_FIRST = {"casi nunca": 0, "a veces": 1, "normal": 2, "casi siempre": 3, "siempre": 4,
             "nada": 0, "poco": 1, "lo justo": 2, "a medias": 2, "bastante": 3, "del todo": 4}


def calcular_ratio_vida(perfil_in):
    """Índice de Riqueza Integral (Ratio de Vida): fusiona Salud, Dinero, Tiempo y Felicidad
    con una MEDIA GEOMÉTRICA (no una media simple). El producto castiga los extremos: un pilar
    por los suelos arrastra a todos los demás, igual que en la vida real. Devuelve 0-100 + banda.
    Requiere las 4 respuestas; si falta alguna, devuelve None."""
    nm = [("rv_salud", "Salud"), ("rv_dinero", "Dinero"), ("rv_tiempo", "Tiempo"), ("rv_felicidad", "Felicidad")]
    vals = {}
    for campo, nombre in nm:
        sel = ((perfil_in or {}).get(campo, "") or "")
        key = sel.split(":")[0].strip().lower()
        if key in _RV_FIRST:
            vals[nombre] = (_RV_FIRST[key] + 1) / 5.0     # 1..5 -> 0.2..1.0 (nunca 0: la media geométrica no se anula)
    if len(vals) < 4:
        return None
    prod = 1.0
    for v in vals.values():
        prod *= v
    iri = int(round((prod ** 0.25) * 100))
    weakest = min(vals, key=vals.get)
    strongest = max(vals, key=vals.get)
    if iri >= 85:
        banda = "El Santo Grial"
    elif iri >= 60:
        banda = "Equilibrio inestable"
    elif iri >= 40:
        banda = "Modo supervivencia"
    else:
        banda = "Alerta roja"
    # --- Mapa de Tensiones: el coste matemático del desequilibrio (todo medido, nada inventado) ---
    media_simple = sum(vals.values()) / 4.0
    impuesto = int(round((media_simple - (prod ** 0.25)) * 100))   # media aritmética - geométrica = "impuesto del desequilibrio"
    # Palanca: ¿y si subes tu pilar más flojo al nivel medio de los otros tres? (resto igual)
    otros = [v for k, v in vals.items() if k != weakest]
    objetivo = min(1.0, sum(otros) / 3.0)
    if objetivo > vals[weakest]:
        vp = dict(vals); vp[weakest] = objetivo
        prodp = 1.0
        for v in vp.values():
            prodp *= v
        iri_potencial = int(round((prodp ** 0.25) * 100))
    else:
        iri_potencial = iri
    _TENS = {
        "Tiempo":    "Rindes y generas, pero no tienes vida para disfrutar de lo que generas.",
        "Dinero":    "Vives bien hoy, pero sin el respaldo que sostenga el mañana.",
        "Salud":     "Estás construyendo tu vida sobre un cuerpo que has dejado de cuidar.",
        "Felicidad": "Tienes los medios, pero se te está escapando el sentido.",
    }
    tension = _TENS.get(weakest, "")
    return {"dims": {k: int(round(v * 100)) for k, v in vals.items()}, "iri": iri, "banda": banda,
            "weakest": weakest, "weakest_val": int(round(vals[weakest] * 100)),
            "strongest": strongest, "strongest_val": int(round(vals[strongest] * 100)),
            "media_simple": int(round(media_simple * 100)), "impuesto": impuesto,
            "iri_potencial": iri_potencial, "tension": tension}


_NUDO_SALUD={"casi nunca":0,"a veces":1,"normal":2,"casi siempre":3,"siempre":4}
def calcular_nudo(perfil_in, datos):
    """El Nudo: cruza dinero, tiempo, salud, familia y relaciones (datos reales, nada inventado)
    y emite las 2-3 tensiones vitales mas agudas. Cada tension conecta >=2 dominios de vida."""
    rv = calcular_ratio_vida(perfil_in)
    if not rv:
        return None
    dims = rv["dims"]; S=dims["Salud"]; D=dims["Dinero"]; T=dims["Tiempo"]; F=dims["Felicidad"]
    p = (perfil_in or {})
    def has(campo, *subs):
        v = (p.get(campo, "") or "").lower()
        return any(s in v for s in subs)
    dep = (p.get("dependientes", "") or "")
    tiene_dep = dep.strip().lower().startswith("s")
    try:
        res = calcular_resiliencia(datos) or {}
    except Exception:
        res = {}
    meses = res.get("meses_libertad")
    L = []
    if D >= 58 and T <= 45:
        L.append({"sev": (D-T)+(12 if tiene_dep else 0), "dom": "DINERO · TIEMPO",
            "tit": "Estás comprando tu patrimonio con tu tiempo",
            "txt": "Generas dinero y vives a contrarreloj. Estás financiando lo que construyes con la única "
                   "moneda que no cotiza y no se devuelve: tu tiempo. Cada euro que sumas hoy lo pagas con una hora "
                   "que no vuelve mañana."})
    if D >= 55 and T <= 50 and tiene_dep and has("conciliacion", "presencia física", "presencia fisica", "ausencia"):
        L.append({"sev": 95 + (50-T), "dom": "DINERO · TIEMPO · FAMILIA",
            "tit": "La factura de tu éxito la firma tu familia",
            "txt": "Y esa factura no la pagas solo tú. Tienes a quien depende de ti — y tu propia respuesta lo "
                   "confirma: estás presente en cuerpo y ausente en lo que de verdad cuenta. El dinero que ganas "
                   "PARA ellos te está costando estar CON ellos. Ningún patrimonio recompra una infancia."})
    if S <= 45 and (D >= 52 or T <= 45):
        L.append({"sev": (60-S)+28, "dom": "SALUD · DINERO",
            "tit": "Construyes sobre un cuerpo que ya no mantienes",
            "txt": "Levantas tu vida sobre el único activo que el dinero no recompra: tu salud. Es el cimiento "
                   "que, el día que cede, hace que el saldo de tu cuenta deje de importar en una sola llamada de "
                   "teléfono."})
    if F <= 45 and D >= 52:
        L.append({"sev": (60-F)+22, "dom": "FELICIDAD · RELACIONES · DINERO",
            "tit": "Rico de medios, pobre de sentido",
            "txt": "Tienes los medios, pero se te escapa el para qué y la gente con la que disfrutarlo. Nadie, en "
                   "la última página de su vida, ha deseado más patrimonio y menos personas a su alrededor."})
    if has("conciliacion", "ausencia total"):
        L.append({"sev": 100, "dom": "DINERO · FAMILIA",
            "tit": "Tu forma de ganar dinero te está costando los tuyos",
            "txt": "Lo dijiste tú: tu situación financiera y laboral te hace perderte los momentos. El dinero mal "
                   "gobernado no compra paz en casa — la consume, en silencio, cada día. Y ese coste no aparece en "
                   "ninguna cuenta hasta que ya es irreversible."})
    if has("energia", "quemado"):
        L.append({"sev": 62 + (45-S if S < 45 else 0), "dom": "SALUD · TIEMPO · DINERO",
            "tit": "No tienes un trabajo: tienes una trampa que paga bien",
            "txt": "Demasiadas horas en lo que odias, sin un sistema que funcione sin ti. Eso cobra caro y tarde: "
                   "primero la energía, luego la salud, y un día la cuenta llega entera. Un patrimonio que te exige "
                   "seguir quemándote no es libertad: es una condena con nómina."})
    if has("carga_familiar", "yo, bastante m", "yo, algo m") and T <= 52:
        L.append({"sev": 56, "dom": "FAMILIA · TIEMPO",
            "tit": "Sostienes la casa y la cuenta a la vez",
            "txt": "Llevas el día a día del hogar por encima de tu pareja Y el peso económico. Esa doble jornada "
                   "no figura en ninguna nómina, pero la pagas en los dos activos que ya tienes en rojo: tu tiempo "
                   "y tu energía."})
    if tiene_dep and meses is not None and meses < 12:
        L.append({"sev": 68 + int((12-meses)*2), "dom": "DINERO · FAMILIA",
            "tit": "Tu libertad es la red que sostiene a los tuyos",
            "txt": "Si mañana faltaras tú, los que dependen de ti aguantarían unos %d meses con lo que hay. Tu "
                   "libertad financiera no es un capricho personal: es la red que protege a tu familia el día que "
                   "tú no puedas. Construirla es el acto menos egoísta que existe." % int(round(meses))})
    if not L:
        return None
    L.sort(key=lambda x: -x["sev"])
    top = L[:3]
    return {"tensiones": top, "n": len(top), "principal": top[0]}


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
                "con para qué la usas. Y si la sientes más pesada de lo que dicen los números, esa tensión también "
                "decide por ti: ponerle cifra exacta —cuánto pagas y a qué interés— es lo que disuelve el peso que notas.")
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
    # Coherencia: vivienda + deuda no pueden exceder el gasto declarado. Si el cliente se contradice,
    # mostramos un desglose que cuadra en lugar de cifras imposibles (la DTI real se mide aparte).
    viv = min(viv, gasto)
    cuota = min(cuota, max(0.0, gasto - viv))
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



def validar_finanzas(datos):
    """Cruza los numeros que da el cliente, deriva magnitudes y detecta incoherencias.
    Devuelve {derivados, alertas:[{campo,nivel,mensaje}], confirmacion}. Tolerante (sin falsos positivos)."""
    g=lambda k:(_num0(datos,k) or 0)
    ing=g("ingreso_mensual"); gas=g("gasto_mensual"); aho=g("ahorro_mensual"); rp=g("renta_pasiva")
    cv=g("coste_vivienda"); cd=g("cuota_deuda"); pat=g("patrimonio"); col=g("colchon_liquido")
    deu=g("deuda_total"); inv=g("inversiones_liquidas"); pen=g("pension_estimada"); ge=g("gasto_estatus")
    ift=g("ing_trabajo"); iiv=g("ing_inversion"); ial=g("ing_alquiler"); iot=g("ing_otros")
    superavit=ing-gas
    liquido=col+inv
    activos=pat+deu                      # patrimonio es NETO -> activos brutos = neto + deuda
    tasa=round(100*aho/ing,1) if ing>0 else None
    col_meses=round(col/gas,1) if gas>0 else None
    a=[]   # alertas
    def flag(campo,nivel,msg): a.append({"campo":campo,"nivel":nivel,"mensaje":msg})
    tol=lambda base:max(50.0,0.12*abs(base))   # 12% o 50€, lo que sea mayor
    # 1) ahorro no puede superar el superavit real
    if ing>0 and gas>0 and aho>0 and aho>superavit+tol(ing):
        flag("ahorro_mensual","alta","Dices que ahorras %s/mes, pero con tus ingresos (%s) menos gastos (%s) quedan %s. ¿El ahorro sale de otro sitio o revisamos alguna cifra?"%(_eur(aho),_eur(ing),_eur(gas),_eur(superavit)))
    # 2) vivienda + cuota de deuda no pueden exceder el gasto total
    if gas>0 and (cv+cd)>gas+tol(gas):
        flag("gasto_mensual","alta","Vivienda (%s) + cuota de deuda (%s) ya suman %s, mas que tu gasto total declarado (%s). ¿El gasto total es mayor?"%(_eur(cv),_eur(cd),_eur(cv+cd),_eur(gas)))
    # 3) liquido + invertido no puede superar los activos brutos
    if pat>0 and liquido>activos+tol(activos):
        flag("patrimonio","alta","Tu dinero liquido + invertido (%s) supera tus activos totales (%s). ¿Falta sumar algun activo (vivienda, inmuebles) al patrimonio?"%(_eur(liquido),_eur(activos)))
    # 4) la renta pasiva no puede superar el ingreso total (que ya la incluye)
    if ing>0 and rp>ing+tol(ing):
        flag("renta_pasiva","media","Tu renta pasiva (%s) supera tu ingreso total (%s). El ingreso total deberia incluirla — revisemoslo."%(_eur(rp),_eur(ing)))
    # 5) las fuentes por separado deberian cuadrar con el ingreso total
    sf=ift+iiv+ial+iot
    if ing>0 and sf>0 and abs(sf-ing)>max(150.0,0.20*ing):
        flag("ingreso_mensual","media","La suma de tus fuentes (%s) no cuadra con tu ingreso mensual (%s). ¿Falta alguna fuente o sobra?"%(_eur(sf),_eur(ing)))
    # 6) gasto de estatus dentro del gasto total
    if gas>0 and ge>gas+tol(gas):
        flag("gasto_estatus","media","Tu gasto de imagen/estatus (%s) supera tu gasto total (%s). ¿Es parte del gasto o adicional?"%(_eur(ge),_eur(gas)))
    # 7) deuda con cuota cero (aviso suave)
    if deu>5000 and cd==0:
        flag("cuota_deuda","baja","Tienes %s de deuda pero 0 de cuota mensual. ¿Esta en carencia o sin cuota fija ahora mismo?"%_eur(deu))
    # 8) pension estimada implausible frente al ingreso
    if ing>0 and pen>ing*1.6:
        flag("pension_estimada","baja","La pension que estimas (%s) es bastante mayor que tu ingreso actual (%s). ¿La revisamos?"%(_eur(pen),_eur(ing)))
    der={"superavit":superavit,"patrimonio_neto":pat,"activos_brutos":activos,"liquido":liquido,
         "tasa_ahorro_pct":tasa,"colchon_meses":col_meses,"renta_pasiva":rp}
    # confirmacion en lenguaje claro
    partes=[]
    if ing>0: partes.append("ingresas %s/mes"%_eur(ing))
    if gas>0: partes.append("gastas %s"%_eur(gas))
    if aho>0: partes.append("ahorras %s%s"%(_eur(aho),(" (%s%% de tus ingresos)"%tasa) if tasa is not None else ""))
    if pat>0: partes.append("tu patrimonio neto es %s"%_eur(pat))
    confirmacion=("Esto es lo que hemos entendido: "+", ".join(partes)+".") if partes else ""
    return {"derivados":der,"alertas":a,"confirmacion":confirmacion}


def frase_capa(code, datos, p=None):
    """Frase de 'tu caso, en numeros' por capa, tejida con las cifras REALES del cliente.
    Devuelve '' si faltan datos para esa capa. Tono neutral (vale para score alto o bajo)."""
    g = lambda k: (_num0(datos, k) or 0)
    ing, gas, aho = g("ingreso_mensual"), g("gasto_mensual"), g("ahorro_mensual")
    pat, col, inv = g("patrimonio"), g("colchon_liquido"), g("inversiones_liquidas")
    deu, cuo, rp = g("deuda_total"), g("cuota_deuda"), g("renta_pasiva")
    ge, viv, horas = g("gasto_estatus"), g("coste_vivienda"), g("horas_semana")
    superavit = ing - gas
    liquido = col + inv
    e = _eur
    meses = (lambda x: ("%.1f" % x).rstrip("0").rstrip("."))
    def mcol(): return (col / gas) if gas > 0 else None
    def mresist(): return (liquido / gas) if gas > 0 else None
    f = ""
    if code == "C1":   # agotamiento
        if ing > 0 and gas > 0:
            if superavit < 0:
                f = "Cada mes gastas %s mas de lo que ingresas: ese numero en rojo es parte del ruido que te pesa en la cabeza." % e(-superavit)
            else:
                _m = round(superavit / ing * 100)
                f = "Cada mes te queda un margen de %s (%d%% de lo que entra). %s" % (e(superavit), _m,
                    "Poco aire deja poco descanso mental." if _m < 10 else "Ese colchon de maniobra juega a favor de tu calma.")
    elif code == "C2":  # libertad financiera
        if gas > 0:
            num = gas * 12 * 25
            cob_pat = round(pat / num * 100) if num > 0 else 0
            cob_liq = round((col + inv) / num * 100) if num > 0 else 0
            f = "Tu vida cuesta %s/ano, asi que tu numero de libertad (regla del 4%%) es %s. De ese objetivo, tu patrimonio total cubre el %d%%, pero solo el %d%% esta liquido o invertido trabajando de verdad hacia el (el resto sigue en activos que aun no rentan)." % (e(gas * 12), e(num), cob_pat, cob_liq)
    elif code == "C3":  # resistencia / stress-test
        mr = mresist()
        if mr is not None:
            f = "Si tus ingresos se cortaran manana, aguantarias %s meses con lo que tienes liquido y realizable (%s). %s" % (meses(mr), e(liquido),
                "Por debajo de 3 meses, cualquier golpe te obliga a decidir con prisa." if mr < 3 else "Es un margen que te deja decidir sin panico.")
    elif code == "C4":  # estilo de vida
        if ing > 0 and gas > 0:
            tasa = round(aho / ing * 100) if aho > 0 else round(max(0, superavit) / ing * 100)
            f = "De cada 100 EUR que entran, %d se quedan contigo y %d se van en tu estilo de vida." % (tasa, 100 - tasa)
    elif code == "C5":  # proteccion / herencia
        if pat > 0:
            f = "Tienes un patrimonio neto de %s%s. La pregunta no es cuanto, sino quien lo recibiria y como, si tu faltaras manana." % (e(pat), (" y %s de deuda asociada" % e(deu)) if deu > 0 else "")
    elif code == "C6":  # estatus
        if gas > 0 and ge > 0:
            f = "Declaras %s/mes de gasto de imagen o estatus: son %s al ano, el %d%% de todo lo que gastas." % (e(ge), e(ge * 12), round(ge / gas * 100))
    elif code == "C7":  # concentracion de ingresos
        if ing > 0:
            act = round((1 - min(rp, ing) / ing) * 100)
            f = "El %d%% de lo que entra en tu casa depende de tu trabajo activo; solo el %d%% (%s/mes) llega sin cambiar tu tiempo por dinero." % (act, 100 - act, e(min(rp, ing)))
    elif code == "C8":  # antifragilidad
        mr = mresist()
        if mr is not None:
            f = "Ante un imprevisto, tu musculo real es de %s meses (%s entre colchon e inversiones realizables). Eso es lo que te separa de tener que improvisar." % (meses(mr), e(liquido))
    elif code == "C9":  # flujo de caja
        if ing > 0 and gas > 0:
            f = "Tu flujo: entran %s, salen %s, te quedan %s al mes. %s" % (e(ing), e(gas), e(superavit),
                "El sistema gotea: hay que cerrar la fuga." if superavit < 0 else "Ese superavit es la materia prima de todo lo demas.")
    elif code == "C10":  # salud de deuda
        if deu > 0:
            apal = round(deu / pat * 100) if pat > 0 else None
            _ap = (" Tu deuda equivale al %d%% de tu patrimonio neto." % apal) if apal is not None else ""
            _cu = (" La cuota (%s/mes) se lleva el %d%% de tus ingresos." % (e(cuo), round(cuo / ing * 100))) if (cuo > 0 and ing > 0) else ""
            f = "Debes %s en total.%s%s" % (e(deu), _ap, _cu)
        elif ing > 0:
            f = "Hoy no declaras deuda: empiezas cada mes sin que nadie haya cobrado antes que tu. Es una ventaja real."
    elif code == "C11":  # crecimiento / palanca
        if ing > 0:
            vh = ing / 160.0
            f = "Tu hora vale hoy unos %s (sobre tus ingresos y una jornada estandar). Crecer es subir ese numero o que el dinero trabaje sin ti." % e(vh)
    elif code == "C12":  # inversion / disciplina
        if pat > 0:
            dormido = max(0.0, pat - inv - col)
            if inv > 0 or col > 0:
                f = "De tu patrimonio, %s esta invertido y trabajando, %s parado en liquido, y unos %s en activos que no rentan (vivienda, ilíquido). El dinero dormido es tu mayor oportunidad silenciosa." % (e(inv), e(col), e(dormido))
            else:
                f = "Con %s de patrimonio, la pregunta es cuanto esta de verdad trabajando para ti hoy y cuanto solo espera."
                f = f % e(pat)
    return f or ""



def plan_hogar(hogar):
    """Los 3 movimientos prioritarios del HOGAR, en plural, cuantificados. Para el libro de pareja."""
    g = lambda k: (_num0(hogar, k) or 0)
    ing, gas, aho = g("ingreso_mensual"), g("gasto_mensual"), g("ahorro_mensual")
    col, inv, pat = g("colchon_liquido"), g("inversiones_liquidas"), g("patrimonio")
    deu, cuo, rp = g("deuda_total"), g("cuota_deuda"), g("renta_pasiva")
    pen = g("pension_estimada")
    e = _eur; sup = max(0.0, ing - gas)
    m1 = lambda x: ("%.1f" % x).rstrip("0").rstrip(".")
    cand = []
    def add(pal, niv, ti, pq, ac, ga): cand.append((pal, niv, ti, pq, ac, ga))
    if gas > 0:
        m = col / gas
        if m < 3:
            obj = gas * 3; ap = round(max(0.0, obj - col) / 12)
            add(1, "rojo", "Construid vuestro suelo de seguridad",
                "Como hogar aguantariais %s meses con vuestro colchon liquido. Por debajo de 3, un imprevisto os obliga a malvender o endeudaros." % m1(m),
                "Abrid UNA cuenta remunerada conjunta, separada del dia a dia, y automatizad %s/mes el dia de cobro." % e(ap or round(gas*0.1)),
                "En 12 meses pasais de %s a 3 meses de colchon: de vulnerables a a prueba de sustos." % m1(m))
    if ing > 0 and cuo > 0 and (100 * cuo / ing) >= 35:
        add(2, "rojo", "Desactivad la deuda que os asfixia",
            "Vuestras cuotas de deuda (%s/mes) se llevan el %d%% de lo que entra en casa." % (e(cuo), round(100*cuo/ing)),
            "Listad TODAS vuestras deudas con su TAE y volcad el excedente del hogar a amortizar la mas cara primero (metodo avalancha).",
            "Cada deuda cara que liquidais os devuelve su cuota al bolsillo comun, libre, para siempre.")
    elif pat > 0 and deu > 0 and (100 * deu / pat) >= 80:
        add(2, "rojo", "Bajad vuestro apalancamiento",
            "Vuestra deuda equivale al %d%% del patrimonio neto del hogar. Es mucho peso ante cualquier viento en contra." % round(100*deu/pat),
            "Antes de asumir mas riesgo, dirigid el excedente conjunto a reducir la deuda mas cara.",
            "Menos deuda compartida = mas margen y menos intereses para los dos.")
    if ing > 0 and gas > 0:
        tasa = (aho / ing * 100) if aho > 0 else (sup / ing * 100)
        if tasa < 20:
            gap = max(0.0, sup - aho)
            ac = ("Automatizad %s/mes el dia 1 a una cuenta de inversion conjunta — ese excedente ya lo teneis, solo no tiene destino." % e(round(gap))) if gap > 50 else ("Subid vuestro ahorro automatico hasta el 20%% de los ingresos del hogar (%s/mes)." % e(round(0.20*ing)))
            add(3, "ambar", "Llevad vuestro ahorro al 20%",
                "Hoy el hogar guarda el %d%% de lo que entra. El 20%% es el umbral donde el interes compuesto empieza a trabajar de verdad." % round(tasa),
                ac,
                "Cada punto que subis son ~%s mas invertidos al ano. Llegar al 20%% adelanta vuestra libertad varios anos." % e(round(0.01*ing*12)))
    if gas > 0:
        exceso = max(0.0, col - gas * 6)
        if exceso >= 5000 and inv <= exceso:
            add(5, "ambar", "Despertad vuestro dinero dormido",
                "Teneis unos %s parados por encima de un colchon sano de 6 meses. Quietos, pierden valor cada ano contra la inflacion." % e(round(exceso)),
                "Moved una parte a una cartera diversificada de bajo coste y automatizad aportaciones conjuntas.",
                "Solo preservar su valor frente a una inflacion del 3%% son ~%s/ano que hoy regalais." % e(round(exceso*0.03)))
    if ing > 0:
        pp = 100 * min(rp, ing) / ing
        if pp < 10:
            add(6, "ambar", "Cread una renta que no dependa de vuestro tiempo",
                "El %d%% de lo que entra en casa depende de que sigais trabajando. Una sola fuente es vuestro mayor riesgo silencioso." % round(100 - pp),
                "Elegid UNA via juntos (dividendos, alquiler, un proyecto) y dad un primer paso este mes — no las tres a la vez.",
                "150 EUR/mes de renta nueva son 1.800 EUR/ano que entran sin cambiar vuestro tiempo por dinero.")
    if gas > 0 and pen > 0 and (gas - pen) > 0:
        gp = gas - pen
        add(7, "ambar", "Cerrad vuestra brecha de pension",
            "Vuestro coste de vida (%s) supera la pension publica estimada conjunta (%s): faltan %s/mes el dia que dejeis de trabajar." % (e(gas), e(pen), e(round(gp))),
            "Abrid un plan de pensiones o inversion periodica y automatizad una aportacion mensual desde ya.",
            "Empezar 10 anos antes puede multiplicar por 2-3 el capital final. Cada ano cuenta.")
    orden_niv = {"rojo": 0, "ambar": 1}
    cand.sort(key=lambda x: (orden_niv.get(x[1], 2), x[0]))
    return [{"orden": i, "titulo": t, "porque": pq, "accion": ac, "gana": ga, "nivel": niv}
            for i, (pal, niv, t, pq, ac, ga) in enumerate(cand[:3], 1)]

def plan_maestro(datos, p=None, perfil_in=None):
    """Los 3 movimientos que mas mueven la aguja, SECUENCIADOS y cuantificados.
    Devuelve [{orden,frente,titulo,porque,accion,gana,nivel}] (1 = primer movimiento)."""
    g = lambda k: (_num0(datos, k) or 0)
    ing, gas, aho = g("ingreso_mensual"), g("gasto_mensual"), g("ahorro_mensual")
    col, inv, pat = g("colchon_liquido"), g("inversiones_liquidas"), g("patrimonio")
    deu, cuo, rp = g("deuda_total"), g("cuota_deuda"), g("renta_pasiva")
    cvm, pen = g("coste_vivienda"), g("pension_estimada")
    e = _eur
    sup = max(0.0, ing - gas)
    cand = []   # (prioridad_palanca, nivel, frente, titulo, porque, accion, gana)
    def add(pal, niv, fr, ti, pq, ac, ga): cand.append((pal, niv, fr, ti, pq, ac, ga))
    # 1) COLCHON / supervivencia (la base de todo)
    if gas > 0:
        m = col / gas
        if m < 3:
            obj = gas * 3; falta = max(0.0, obj - col); ap = round(falta / 12) if falta else 0
            add(1, "rojo", "Colchon", "Construye tu suelo de seguridad",
                "Hoy aguantarias %s meses con tu colchon liquido. Por debajo de 3, cualquier imprevisto te obliga a malvender o pedir prestado." % (("%.1f" % m).rstrip("0").rstrip(".")),
                "Abre una cuenta remunerada SEPARADA del dia a dia y automatiza %s/mes el dia de cobro." % e(ap or round(gas*0.1)),
                "En 12 meses pasas de %s a 3 meses de colchon: de vulnerable a a prueba de sustos." % (("%.1f" % m).rstrip("0").rstrip(".")))
    # 2) DEUDA cara
    if ing > 0 and cuo > 0 and (100 * cuo / ing) >= 35:
        add(2, "rojo", "Deuda", "Desactiva la deuda que te asfixia",
            "Tu cuota de deuda (%s/mes) se lleva el %d%% de lo que ingresas. Por encima del 35%%, cada mes empiezas cuesta arriba." % (e(cuo), round(100*cuo/ing)),
            "Lista tus deudas con su TAE real y vuelca todo el excedente a amortizar la MAS CARA primero (metodo avalancha).",
            "Cada %s de deuda cara que liquidas te devuelve su cuota al bolsillo, libre, para siempre." % e(round(deu*0.1) if deu else 1000))
    elif pat > 0 and deu > 0 and (100 * deu / pat) >= 80:
        add(2, "rojo", "Deuda", "Baja tu apalancamiento",
            "Tu deuda equivale al %d%% de tu patrimonio neto. Es mucho peso para cualquier viento en contra." % round(100*deu/pat),
            "Antes de asumir mas riesgo, dirige tu excedente a reducir la deuda mas cara hasta bajar de ese umbral.",
            "Menos deuda = mas margen y menos intereses: la rentabilidad mas segura que existe.")
    # 3) TASA DE AHORRO < 20%
    if ing > 0 and gas > 0:
        tasa = (aho / ing * 100) if aho > 0 else (sup / ing * 100)
        if tasa < 20:
            extra = max(0.0, 0.20 * ing - max(aho, 0)); anual = round(extra * 12)
            gap = max(0.0, sup - aho)
            ac = ("Automatiza %s/mes el dia 1 hacia una cuenta de inversion — ese excedente ya lo tienes, solo no tiene destino." % e(round(gap))) if gap > 50 else ("Sube tu ahorro automatico hasta el 20%% de tus ingresos (%s/mes) y auditalo desde tus 3 mayores gastos fijos." % e(round(0.20*ing)))
            add(3, "ambar", "Ahorro", "Lleva tu ahorro al 20%",
                "Hoy guardas el %d%% de lo que entra. El 20%% es el umbral donde el interes compuesto empieza a trabajar de verdad a tu favor." % round(tasa),
                ac,
                "Cada punto que subes son ~%s mas invertidos al ano. Llegar al 20%% adelanta tu libertad varios anos." % e(round(0.01*ing*12)))
    # 4) DINERO DORMIDO (liquido parado por encima de un colchon sano)
    if gas > 0:
        exceso = max(0.0, col - gas * 6)
        if exceso >= 5000 and inv <= exceso:
            add(5, "ambar", "Inversion", "Despierta tu dinero dormido",
                "Tienes unos %s parados por encima de un colchon sano de 6 meses. Quietos, pierden valor cada ano contra la inflacion." % e(round(exceso)),
                "Mueve una parte a una cartera diversificada de bajo coste (fondos indexados); empieza pequeno y automatiza aportaciones.",
                "Solo preservar su valor frente a una inflacion del 3%% son ~%s/ano que hoy regalas." % e(round(exceso * 0.03)))
    # 5) CONCENTRACION DE INGRESOS (casi todo activo)
    if ing > 0:
        pp = 100 * min(rp, ing) / ing
        if pp < 10:
            add(6, "ambar", "Diversificacion", "Crea tu primera renta que no dependa de ti",
                "El %d%% de lo que entra en tu casa depende de que tu sigas trabajando. Una sola fuente es tu mayor riesgo silencioso." % round(100 - pp),
                "Elige UNA via (dividendos, alquiler, un proyecto digital) y dale un primer paso concreto este mes — no las tres a la vez.",
                "150 EUR/mes de renta nueva son 1.800 EUR/ano que entran sin cambiar tu tiempo por dinero. Y solo es el principio.")
    # 6) GAP DE PENSION
    if gas > 0 and pen > 0 and (gas - pen) > 0:
        gpen = gas - pen
        add(7, "ambar", "Jubilacion", "Cierra tu brecha de pension",
            "Tu coste de vida (%s) supera tu pension publica estimada (%s): faltan %s/mes el dia que dejes de trabajar." % (e(gas), e(pen), e(round(gpen))),
            "Abre un plan de pensiones o una inversion periodica y automatiza una aportacion mensual desde ya — el tiempo es tu mayor aliado aqui.",
            "Empezar 10 anos antes puede multiplicar por 2-3 el capital final, por el interes compuesto. Cada ano cuenta.")
    # ordenar: rojo antes que ambar (un rojo nunca se entierra), luego LO QUE EL CLIENTE
    # DIJO QUE LE IMPORTA (saliencia), luego por palanca; quedarnos con 3
    prio = set((perfil_in or {}).get("prioridades") or [])
    FRENTE2CAPA = {"Colchon": "Prueba de Resistencia Familiar", "Deuda": "Tu Salud de Deuda",
                   "Ahorro": "Eficiencia de tu Estilo de Vida", "Inversion": "Tu Disciplina de Inversión",
                   "Diversificacion": "Concentración de tus Ingresos", "Jubilacion": "Tu Número de Libertad Financiera"}
    def _sal(fr): return 0 if (prio and FRENTE2CAPA.get(fr) in prio) else 1
    orden_niv = {"rojo": 0, "ambar": 1}
    cand.sort(key=lambda x: (orden_niv.get(x[1], 2), _sal(x[2]), x[0]))
    out = []
    for i, (pal, niv, fr, ti, pq, ac, ga) in enumerate(cand[:3], 1):
        out.append({"orden": i, "frente": fr, "titulo": ti, "porque": pq, "accion": ac, "gana": ga, "nivel": niv})
    return out

def detectar_paradoja(datos, p, resiliencia):
    """EL HALLAZGO ESTRELLA, multi-área. Detecta CADA punto donde un DATO OBJETIVO y la
    PERCEPCIÓN del cliente divergen (colchón vs miedo, deuda vs asfixia, resistencia vs pánico).
    No es un error del motor: el número mide el dinero, el cuestionario mide la emoción. Nombrarlo
    convierte cada contradicción en un hallazgo de asesor — el posicionamiento de un family office
    frente a un robo-advisor. Devuelve una LISTA de paradojas (puede ir vacía). A prueba de fallos."""
    out = []
    try:
        d = datos or {}
        res = resiliencia or {}
        pp = p or {}
        def _f(x):
            try: return float(x)
            except Exception: return None
        meses = res.get("meses_liquido")
        c3 = pp.get("C3", {}).get("score", 0)   # percepción de resistencia (alto = más miedo)
        c10 = pp.get("C10", {}).get("score", 0)  # percepción de la deuda (alto = la vive como carga)
        ing = _f(d.get("ingreso_mensual")); cuota = _f(d.get("cuota_deuda")); deuda = _f(d.get("deuda_total"))

        # (1) COLCHÓN / RESISTENCIA: objetivamente protegido, subjetivamente aterrado.
        if meses is not None and meses >= 6 and c3 >= 50:
            _m = ("%.1f" % meses).rstrip("0").rstrip(".")
            out.append({"tipo": "colchon", "titulo": "Tu colchón está bien. Tu cabeza aún no lo sabe.",
                "texto": ("Tienes <b>%s meses</b> de vida cubiertos en líquido —mejor que la mayoría—, pero "
                          "tus respuestas dicen que sientes que no aguantarías nada. <b>Tu problema aquí no es "
                          "tu dinero: es que no confías en él.</b> No se arregla ahorrando más; se arregla "
                          "mirando el dato real cada vez que la cabeza te diga que no llegas." % _m)})
        # (2) DEUDA: el bolsillo la soporta, la cabeza no.
        if ing and ing > 0 and cuota is not None and deuda and deuda > 0:
            dti = 100.0 * cuota / ing
            if dti < 15 and c10 >= 50:
                out.append({"tipo": "deuda", "titulo": "Tu deuda no te ahoga el bolsillo. Te ahoga la cabeza.",
                    "texto": ("Tu cuota es solo el <b>%d%%</b> de lo que ingresas —objetivamente, está bajo "
                              "control—, y aun así la vives como una asfixia. <b>El peso de esa deuda es más "
                              "mental que financiero.</b> Saberlo cambia el plan: no es una emergencia de números, "
                              "es una cuenta pendiente con tu tranquilidad." % round(dti))})
        # (3) Inverso del colchón: se cree tranquilo pero está expuesto.
        if meses is not None and meses < 3 and c3 <= 25:
            _m = ("%.1f" % meses).rstrip("0").rstrip(".")
            out.append({"tipo": "tranquilo_expuesto", "titulo": "Te sientes tranquilo. Los números piden prudencia.",
                "texto": ("Tus respuestas transmiten calma, pero en líquido solo tienes <b>%s meses</b> de margen. "
                          "La tranquilidad es buena; conviene que se apoye en un colchón, no solo en el optimismo." % _m)})
    except Exception:
        return []
    return out


def computar_extras(resp, datos, perfil_in, inst=None):
    """Punto de entrada unico. Devuelve dict listo para report_book + arq_code."""
    inst = inst or cargar_inst()
    p = perfil_scores(resp, inst["capas"])
    ratios = calcular_ratios(datos, perfil_in)
    brecha = calcular_brecha(datos, resp, perfil_in)
    compromiso = calcular_compromiso(datos, perfil_in, brecha, p)
    contras = calcular_contradicciones(datos, resp, perfil_in, p)
    return {
        "crisis": bool(compromiso.get("crisis")),
        "rentista": bool(compromiso.get("rentista")) or _es_rentista(perfil_in),
        "brecha": brecha,
        "ratios": ratios,
        "accion_unica": calcular_accion_unica(ratios, p),
        "palancas": calcular_palancas(datos, p, perfil_in, resp),
        "contradicciones": contras,
        "validez": validez(resp, datos, perfil_in, p, contras, inst),
        "coherencia": validar_finanzas(datos),
        "frases": {c["code"]: frase_capa(c["code"], datos, p) for c in inst["capas"]},
        "plan_maestro": plan_maestro(datos, p, perfil_in),
        "energia": calcular_energia(perfil_in),
        "conciliacion": calcular_conciliacion(perfil_in),
        "preguntas_asesor": calcular_preguntas_asesor(perfil_in, p),
        "asesor": calcular_asesor(perfil_in),
        "herencia": calcular_herencia(perfil_in),
        "fortuna_neta": calcular_fortuna_neta(datos),
        "resiliencia": calcular_resiliencia(datos),
        "paradoja": detectar_paradoja(datos, p, calcular_resiliencia(datos)),
        "fuentes": calcular_fuentes(datos, perfil_in),
        "ratio_vida": calcular_ratio_vida(perfil_in),
        "nudo": calcular_nudo(perfil_in, datos),
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
