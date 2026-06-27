# -*- coding: utf-8 -*-
"""ITAP — Guardián de coherencia (fuente única de verdad).

Lee las cifras YA calculadas por el motor determinista (score_v2.computar_extras)
y comprueba IDENTIDADES CRUZADAS entre ellas. No recalcula nada con fórmulas
propias: solo verifica que los números que el informe va a imprimir cuadran entre sí.

Filosofía: el motor calcula cada cifra una vez; este guardián confirma que esas
cifras no se contradicen antes de que el LLM/PDF las use. Mapea uno a uno los bugs
sistémicos detectados en la auditoría (magnitud ×10, vivienda contradictoria,
patrimonio descuadrado, cifras imposibles).

A prueba de fallos: NUNCA lanza excepción. Si algo falta, omite esa regla.
Devuelve una lista de hallazgos; cada uno: {severidad, regla, mensaje, valores}.
Severidades: "critico" (no debe imprimirse así), "alto", "aviso".
"""


def _f(x):
    """Coacciona a float o None de forma segura."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v


def _g(d, *path, default=None):
    """Navega dicts anidados con seguridad: _g(extras, 'resiliencia', 'patrimonio')."""
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def revisar_coherencia(datos, extras):
    """Devuelve lista de hallazgos de incoherencia. datos: dict cliente; extras: salida de computar_extras."""
    h = []
    datos = datos or {}
    extras = extras or {}
    try:
        gasto_m = _f(datos.get("gasto_mensual"))
        ingreso_m = _f(datos.get("ingreso_mensual"))
        coste_viv = _f(datos.get("coste_vivienda"))
        pct_viv = _f(datos.get("pct_vivienda"))
        renta_pasiva = _f(datos.get("renta_pasiva"))

        # ------------------------------------------------------------------
        # R1 · MAGNITUD DEL NÚMERO DE LIBERTAD (bug 75k -> 750k)
        # La regla del 4% (×25 sobre el gasto ANUAL) sitúa el número en una
        # banda plausible de ~20-50 veces el gasto anual. Un número que solo es
        # ~2-3× el gasto anual delata un error de magnitud (gasto mensual ×25
        # en vez de anual ×25 = le falta el ×12).
        # ------------------------------------------------------------------
        candidatos = {
            "compromiso.numero_libertad": _g(extras, "compromiso", "numero_libertad"),
            "brecha.numero_ideal": _g(extras, "brecha", "numero_ideal"),
            "brecha.numero_actual": _g(extras, "brecha", "numero_actual"),
        }
        if gasto_m and gasto_m > 0:
            gasto_anual = gasto_m * 12.0
            for nombre, val in candidatos.items():
                v = _f(val)
                if v is None or v <= 0:
                    continue
                ratio = v / gasto_anual
                if ratio < 10:
                    h.append({
                        "severidad": "critico", "regla": "R1-MAGNITUD",
                        "mensaje": ("El número de libertad '%s' = %s es solo %.1f× tu gasto anual "
                                    "(%s). La regla del 4%% exige ~25×. Posible error de magnitud "
                                    "(¿falta un ×12?): el correcto rondaría %s."
                                    % (nombre, _eur(v), ratio, _eur(gasto_anual), _eur(gasto_anual * 25))),
                        "valores": {"citado": v, "esperado_25x": gasto_anual * 25, "ratio": round(ratio, 2)},
                    })
                elif ratio > 60:
                    h.append({
                        "severidad": "alto", "regla": "R1-MAGNITUD",
                        "mensaje": ("El número de libertad '%s' = %s es %.0f× tu gasto anual: "
                                    "inusualmente alto para la regla del 4%%."
                                    % (nombre, _eur(v), ratio)),
                        "valores": {"citado": v, "ratio": round(ratio, 2)},
                    })

        # ------------------------------------------------------------------
        # R2 · VIVIENDA CONTRADICTORIA (carga >0% pero coste 0, o viceversa)
        # ------------------------------------------------------------------
        carga = _f(_g(extras, "vivienda", "carga"))
        if carga is None:
            carga = pct_viv
        if carga is not None and coste_viv is not None:
            if carga > 5 and coste_viv <= 0:
                h.append({
                    "severidad": "critico", "regla": "R2-VIVIENDA",
                    "mensaje": ("Contradicción de vivienda: la carga declarada es %.0f%% del ingreso "
                                "pero el coste de vivienda es 0 €. O paga vivienda o no la paga." % carga),
                    "valores": {"carga_pct": carga, "coste_vivienda": coste_viv},
                })
            elif carga <= 0 and coste_viv > 0:
                h.append({
                    "severidad": "alto", "regla": "R2-VIVIENDA",
                    "mensaje": ("Contradicción de vivienda: el coste de vivienda es %s pero la carga "
                                "calculada es 0%%." % _eur(coste_viv)),
                    "valores": {"carga_pct": carga, "coste_vivienda": coste_viv},
                })

        # ------------------------------------------------------------------
        # R3 · PATRIMONIO DESCUADRADO (neto != líquido + ilíquido)
        # El donut de composición no puede decir "100% líquido" si hay ilíquido.
        # ------------------------------------------------------------------
        pat = _f(_g(extras, "resiliencia", "patrimonio"))
        liq = _f(_g(extras, "resiliencia", "liquido_inmediato"))
        ili = _f(_g(extras, "resiliencia", "iliquido"))
        if pat is not None and liq is not None and ili is not None and pat > 0:
            suma = liq + ili
            desv = abs(suma - pat) / pat
            if desv > 0.02:  # >2% de descuadre
                h.append({
                    "severidad": "alto", "regla": "R3-PATRIMONIO",
                    "mensaje": ("El patrimonio (%s) no cuadra con su composición: líquido %s + ilíquido %s "
                                "= %s (descuadre %.0f%%). Hay activos sin explicar en el desglose."
                                % (_eur(pat), _eur(liq), _eur(ili), _eur(suma), desv * 100)),
                    "valores": {"patrimonio": pat, "liquido": liq, "iliquido": ili, "suma": suma},
                })

        # ------------------------------------------------------------------
        # R4 · CIFRAS IMPOSIBLES (rentas pasivas > ingreso total, negativos)
        # ------------------------------------------------------------------
        if renta_pasiva is not None and ingreso_m is not None and ingreso_m > 0:
            if renta_pasiva > ingreso_m * 1.001:
                h.append({
                    "severidad": "alto", "regla": "R4-IMPOSIBLE",
                    "mensaje": ("La renta pasiva (%s/mes) supera el ingreso total (%s/mes): imposible."
                                % (_eur(renta_pasiva), _eur(ingreso_m))),
                    "valores": {"renta_pasiva": renta_pasiva, "ingreso": ingreso_m},
                })
        for campo in ("gasto_mensual", "ingreso_mensual", "patrimonio", "coste_vivienda"):
            v = _f(datos.get(campo))
            if v is not None and v < 0:
                h.append({
                    "severidad": "critico", "regla": "R4-IMPOSIBLE",
                    "mensaje": "El campo '%s' es negativo (%s): dato imposible." % (campo, _eur(v)),
                    "valores": {campo: v},
                })

    except Exception as e:  # guardián jamás rompe la generación
        h.append({"severidad": "aviso", "regla": "R0-INTERNO",
                  "mensaje": "El guardián de coherencia falló internamente: %s" % e, "valores": {}})
    return h


def _eur(n):
    try:
        return "{:,.0f} €".format(float(n)).replace(",", ".")
    except Exception:
        return str(n)


def hay_critico(hallazgos):
    return any(x.get("severidad") == "critico" for x in (hallazgos or []))


def resumen_log(hallazgos):
    """Línea(s) compactas para los logs del servidor (no se muestran al cliente)."""
    if not hallazgos:
        return "QA-COHERENCIA: OK (sin incoherencias)"
    partes = ["QA-COHERENCIA: %d hallazgo(s)" % len(hallazgos)]
    for x in hallazgos:
        partes.append("  [%s/%s] %s" % (x.get("severidad", "?").upper(), x.get("regla", "?"), x.get("mensaje", "")))
    return "\n".join(partes)


if __name__ == "__main__":
    # Caso Benito (bugs reales): número 75k para 2.500€/mes, vivienda contradictoria, patrimonio descuadrado.
    datos = {"gasto_mensual": 2500, "ingreso_mensual": 3000, "coste_vivienda": 0,
             "pct_vivienda": 30, "renta_pasiva": 10}
    extras = {
        "compromiso": {"numero_libertad": 75000},   # BUG: debería ser 750.000
        "brecha": {"numero_ideal": 750000, "numero_actual": 540000},
        "resiliencia": {"patrimonio": 29000, "liquido_inmediato": 20000, "iliquido": 0},  # BUG: 9.000 sin explicar
        "vivienda": {"carga": 30},
    }
    res = revisar_coherencia(datos, extras)
    print(resumen_log(res))
    print("\nBLOQUEARÍA (hay crítico):", hay_critico(res))
    # Caso limpio: debe pasar sin hallazgos críticos.
    datos2 = {"gasto_mensual": 2500, "ingreso_mensual": 3000, "coste_vivienda": 600, "pct_vivienda": 24}
    extras2 = {"compromiso": {"numero_libertad": 750000},
               "resiliencia": {"patrimonio": 29000, "liquido_inmediato": 20000, "iliquido": 9000},
               "vivienda": {"carga": 24}}
    print("\n--- Caso limpio ---")
    print(resumen_log(revisar_coherencia(datos2, extras2)))
