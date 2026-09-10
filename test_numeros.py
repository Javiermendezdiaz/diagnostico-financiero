#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RED DE SEGURIDAD DE LAS CIFRAS del diagnostico Adapta.

Por que existe: el CI comprueba que el PDF se genera, pero NO que los numeros
sean correctos. Un informe puede compilar perfectamente y decirle al cliente una
cifra equivocada. En un producto donde el numero ES el producto, eso es lo unico
que no nos podemos permitir.

Que hace:
  1) CASOS DE ORO: perfiles reales con su resultado esperado. Si alguien toca el
     motor y una cifra cambia, esto se pone rojo y dice exactamente cual.
  2) INVARIANTES: reglas que deben cumplirse SIEMPRE, con cualquier dato
     (monotonias, coherencias, no-negatividad). Cazan errores en casos que a
     nadie se le ocurrio probar.

Uso:  python test_numeros.py      (verde = las cifras siguen siendo las correctas)
Si un cambio es intencionado, actualiza el valor esperado y deja constancia.
"""
import sys

import motor_financiero_v3 as m

FALLOS = []
OK = 0


def _chk(nombre, obtenido, esperado, tol=1):
    global OK
    if isinstance(esperado, (int, float)) and isinstance(obtenido, (int, float)):
        bien = abs(obtenido - esperado) <= tol
    else:
        bien = obtenido == esperado
    if bien:
        OK += 1
    else:
        FALLOS.append("%s -> esperado %s, obtenido %s" % (nombre, esperado, obtenido))


def _exp(gasto, pension, capital, ahorro, horizonte, edad=None, rent=5.5):
    return m.analizar_expectativas(gasto, pension, capital, ahorro, horizonte, rent,
                                   None, 0, edad=edad)


# ---------------------------------------------------------------- CASOS DE ORO
def casos_de_oro():
    """Perfiles concretos con cifras verificadas a mano. Cambiar solo a proposito."""
    print("== 1) CASOS DE ORO (cifras verificadas) ==")

    # A. Jubilacion ordinaria: para a los 67, sin puente. Tasa 3,5% -> 28,6x
    a = _exp(3000, 1100, 50000, 300, 15, edad=52)
    _chk("A. edad ordinaria - numero", a["numero_libertad"], 652080, tol=200)
    _chk("A. edad ordinaria - tasa", a["tasa_retirada_pct"], 3.5, tol=0.01)
    _chk("A. edad ordinaria - sin puente", a["puente_anios"], 0)

    # B. Retiro anticipado a los 60: 7 anos sin pension -> capital de puente
    b = _exp(3000, 1100, 50000, 300, 15, edad=45)
    _chk("B. para a los 60 - edad parada", b["edad_parada"], 60)
    _chk("B. para a los 60 - puente", b["puente_anios"], 7)
    _chk("B. para a los 60 - numero", b["numero_libertad"], 738037, tol=300)

    # C. Retiro muy temprano a los 45: 22 anos de puente
    c = _exp(3000, 1100, 50000, 300, 15, edad=30)
    _chk("C. para a los 45 - puente", c["puente_anios"], 22)
    _chk("C. para a los 45 - tasa minima", c["tasa_retirada_pct"], 3.0, tol=0.01)
    _chk("C. para a los 45 - numero", c["numero_libertad"], 914045, tol=400)

    # D. La pension cubre el gasto -> no hay numero que alcanzar
    d = _exp(1000, 1100, 50000, 300, 15, edad=52)
    _chk("D. pension cubre - marca", d.get("pension_cubre"), True)
    _chk("D. pension cubre - numero", d["numero_libertad"], 0)

    # E. Sin edad -> se asume edad ordinaria (comportamiento por defecto estable)
    e = _exp(3000, 1100, 50000, 300, 15)
    _chk("E. sin edad - numero", e["numero_libertad"], 652080, tol=200)
    _chk("E. sin edad - sin puente", e["puente_anios"], 0)

    # F. Sin pension declarada -> la cartera carga con todo
    f = _exp(2000, 0, 20000, 200, 20, edad=47)
    _chk("F. sin pension - gasto propio", f["gasto_propio"], 2000)
    _chk("F. sin pension - numero", f["numero_libertad"], 686400, tol=300)

    # G. Escenarios: recortar gasto baja el numero; ahorrar mas NO lo cambia
    g = _exp(3000, 1100, 50000, 300, 15, edad=45)
    esc = {x["escenario"]: x for x in g.get("escenarios", [])}
    _chk("G. hay 5 escenarios", len(esc), 5)
    _chk("G. ahorrar mas no cambia la meta",
         esc["Ahorras 200 € más al mes"]["numero"], g["numero_libertad"], tol=1)
    _chk("G. recortar gasto SI baja la meta",
         esc["Recortas el gasto un 10%"]["numero"] < g["numero_libertad"], True)


# ---------------------------------------------------------------- INVARIANTES
def invariantes():
    """Reglas que deben cumplirse con CUALQUIER dato. Cazan lo que nadie probo."""
    print("== 2) INVARIANTES (deben cumplirse siempre) ==")

    # I1. Cuanto antes paras, mas capital necesitas (monotonia estricta)
    nums = [_exp(3000, 1100, 50000, 300, 0, edad=e)["numero_libertad"]
            for e in (67, 62, 57, 52, 47)]
    _chk("I1. parar antes exige mas capital", all(a < b for a, b in zip(nums, nums[1:])), True)

    # I2. Mas pension -> menos capital propio necesario
    n1 = _exp(3000, 800, 50000, 300, 15, edad=52)["numero_libertad"]
    n2 = _exp(3000, 1400, 50000, 300, 15, edad=52)["numero_libertad"]
    _chk("I2. mas pension baja el numero", n2 < n1, True)

    # I3. La tasa siempre dentro del rango calibrado
    tasas = [_exp(3000, 1100, 50000, 300, 0, edad=e)["tasa_retirada_pct"]
             for e in range(30, 70, 3)]
    _chk("I3. tasa entre 3,0% y 3,5%", all(3.0 - 1e-9 <= t <= 3.5 + 1e-9 for t in tasas), True)

    # I4. Nunca cifras negativas ni absurdas
    malos = []
    for edad in (25, 40, 55, 70):
        for gasto in (800, 3000, 9000):
            for pen in (0, 900, 2500):
                r = _exp(gasto, pen, 10000, 100, 10, edad=edad)
                if r.get("numero_libertad", 0) < 0 or r.get("puente_capital", 0) < 0:
                    malos.append((edad, gasto, pen))
                if r.get("pct_cubierto", 0) > 100:
                    malos.append(("pct>100", edad, gasto, pen))
    _chk("I4. sin negativos ni pct>100", malos, [])

    # I5. Robustez: basura de entrada no debe reventar el motor
    try:
        for mala in (None, "", "abc", -5000):
            m.analizar_expectativas(mala, mala, mala, mala, mala, 5.5)
        _chk("I5. tolera datos corruptos", True, True)
    except Exception as e:
        _chk("I5. tolera datos corruptos", "excepcion: %s" % e, True)

    # I6. El puente solo existe si para antes de la edad ordinaria
    for edad, hor, debe in ((30, 10, True), (52, 15, False), (60, 10, False)):
        r = _exp(3000, 1100, 50000, 300, hor, edad=edad)
        _chk("I6. puente coherente (para a los %s)" % r["edad_parada"],
             r["puente_anios"] > 0, debe)

    # I8. COHERENCIA DEL TEXTO: el multiplo que se imprime debe reproducir el numero.
    # (Fallo real detectado: con puente, el multiplo declarado no cuadraba con la cifra
    #  y un cliente que multiplicara encontraba 155.000 EUR de desfase.)
    descuadres = []
    for edad in (30, 35, 40, 45, 52, 60):
        r = _exp(3000, 1100, 50000, 300, 15, edad=edad)
        gp_anual = r.get("gasto_propio", 0) * 12
        mef = r.get("multiplo_efectivo") or 0
        if gp_anual and abs(gp_anual * mef - r["numero_libertad"]) > gp_anual * 0.05:
            descuadres.append((edad, gp_anual * mef, r["numero_libertad"]))
    _chk("I8. el multiplo impreso reproduce el numero", descuadres, [])

    # I7. Los parametros se cargan y quedan a la vista para el informe
    _chk("I7. vigencia de parametros presente",
         bool(_exp(3000, 1100, 50000, 300, 15, edad=52).get("vigencia_parametros")), True)

    # I9. UN SOLO NUMERO EN TODO EL INFORME.
    # (Fallo real: fi_metrics calculaba gasto*12*25 e ignoraba la pension, mientras
    #  el motor calculaba 28,6x-33,3x neto de pension. El mismo cliente veia 900.000 EUR
    #  en la pagina 2 y 652.080 EUR en la pagina 40. El desfase llegaba a 248.000 EUR
    #  y cambiaba de signo segun el perfil, asi que ni siquiera era conservador.)
    try:
        import report_book as rb
        import seccion_apertura as ap
        perfiles = [
            {"gasto_mensual": 3000, "pension_estimada": 1100, "inversiones_liquidas": 50000,
             "colchon_liquido": 0, "ahorro_mensual": 300, "ingreso_mensual": 3300, "edad": 52},
            {"gasto_mensual": 2000, "pension_estimada": 0, "inversiones_liquidas": 20000,
             "colchon_liquido": 0, "ahorro_mensual": 200, "ingreso_mensual": 2200, "edad": 47},
            {"gasto_mensual": 3000, "pension_estimada": 1100, "inversiones_liquidas": 50000,
             "colchon_liquido": 0, "ahorro_mensual": 300, "ingreso_mensual": 3300, "edad": 30},
            {"gasto_mensual": 4500, "pension_estimada": 1800, "inversiones_liquidas": 120000,
             "colchon_liquido": 15000, "ahorro_mensual": 900, "ingreso_mensual": 5400, "edad": 41},
        ]
        desfases = []
        for d in perfiles:
            n_informe = rb.fi_metrics(d)[0]
            n_motor = (ap.datos_expectativas(d) or {}).get("numero_libertad")
            if n_motor and abs(n_informe - n_motor) > 1:
                desfases.append((d["edad"], round(n_informe), round(n_motor)))
        _chk("I9. fi_metrics y el motor dan EL MISMO numero", desfases, [])
    except Exception as e:
        _chk("I9. fi_metrics y el motor dan EL MISMO numero", "excepcion: %s" % e, [])


def main():
    print("=" * 62)
    print(" RED DE SEGURIDAD DE LAS CIFRAS - Diagnostico Adapta")
    print("=" * 62)
    casos_de_oro()
    invariantes()
    print("-" * 62)
    if FALLOS:
        print("X %d COMPROBACION(ES) FALLIDA(S) de %d:" % (len(FALLOS), len(FALLOS) + OK))
        for f in FALLOS:
            print("   X", f)
        print("\nSi el cambio es INTENCIONADO, actualiza el valor esperado en este fichero.")
        return 1
    print("OK - las %d comprobaciones pasan: las cifras siguen siendo las correctas." % OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
