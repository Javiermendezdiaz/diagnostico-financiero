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
    numero_ideal = coste_ideal * 12 * 25
    base = gasto or ingreso
    numero_actual = base * 12 * 25 if base else None
    arq = (perfil_in or {}).get("vida_ideal_arq")
    recon = resp.get("VIS-03")
    recon_txt = {0: "en rumbo", 1: "espejismo", 2: "vía muerta"}.get(recon)
    base_out = {"coste_ideal_mes": coste_ideal, "numero_ideal": numero_ideal,
                "numero_actual": numero_actual, "ahorro_mes": ahorro, "arq": arq,
                "reconocimiento": recon_txt, "patrimonio": patrimonio}
    if not ingreso:
        renta_cap = round(patrimonio * 0.04 / 12)
        brecha_mes = coste_ideal - renta_cap
        base_out.update({"sin_ingreso": True, "ingreso_mes": 0, "renta_capital_mes": renta_cap,
                         "brecha_mes": brecha_mes, "brecha_anual": brecha_mes * 12,
                         "ingreso_cubre_ideal": renta_cap >= coste_ideal})
        return base_out
    brecha_mes = coste_ideal - ingreso
    base_out.update({"sin_ingreso": False, "ingreso_mes": ingreso, "brecha_mes": brecha_mes,
                     "brecha_anual": brecha_mes * 12, "ingreso_cubre_ideal": brecha_mes <= 0})
    return base_out


def calcular_palancas(datos, p, perfil_in):
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

    # 4) Patrimonio sólido con salud psicofinanciera tensionada (distorsión de seguridad)
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


def computar_extras(resp, datos, perfil_in, inst=None):
    """Punto de entrada unico. Devuelve dict listo para report_book + arq_code."""
    inst = inst or cargar_inst()
    p = perfil_scores(resp, inst["capas"])
    return {
        "brecha": calcular_brecha(datos, resp, perfil_in),
        "palancas": calcular_palancas(datos, p, perfil_in),
        "contradicciones": calcular_contradicciones(datos, resp, perfil_in, p),
        "arq_code": arq_desde_perfil(perfil_in),
        "_p": p,
    }


if __name__ == "__main__":
    inst = cargar_inst()
    print("capas:", [c["code"] for c in inst["capas"]])
