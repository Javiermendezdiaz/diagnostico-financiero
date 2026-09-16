#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compila SOLO el informe de pareja y comprueba las barras de comparacion.

Por que existe: se detectaron DOS sitios donde las barras se dibujaban con la
puntuacion cruda mientras la etiqueta de al lado usaba la escala invertida, asi
que las barras contradecian al numero impreso justo encima. Estaba corregido en
GitHub y la copia local iba por detras. Esto verifica que no vuelve a pasar.
"""
import os
import re
import sys

os.environ.setdefault("MPLBACKEND", "Agg")

fallos = []

# ---------------------------------------------------- 1. las dos lineas criticas
print("== 1) LAS BARRAS DEBEN USAR LA MISMA ESCALA QUE EL NUMERO ==")
try:
    src = open("report_couple.py", encoding="utf-8", errors="replace").read()
    esperado = [
        ("comparacion global", r"Bar2\(rb\._sal100\(a\)\s*,\s*rb\._sal100\(b\)"),
        ("faceta por faceta", r"Bar2\(100-fa\s*,\s*100-fb"),
    ]
    for nombre, patron in esperado:
        if re.search(patron, src):
            print("  OK - %s usa la escala correcta." % nombre)
        else:
            print("  X  %s NO usa la escala correcta." % nombre)
            fallos.append("Barras invertidas en: %s" % nombre)
    # Y que no queden las versiones crudas
    for nombre, malo in (("comparacion global", r"Bar2\(a\s*,\s*b\s*,"),
                         ("faceta por faceta", r"Bar2\(fa\s*,\s*fb\s*,")):
        if re.search(malo, src):
            print("  X  queda la version cruda en %s" % nombre)
            fallos.append("Version cruda presente en: %s" % nombre)
except Exception as e:
    fallos.append("No se ha podido revisar report_couple.py: %s" % e)

# ---------------------------------------------------- 2. compilar el de pareja
print("\n== 2) COMPILANDO EL INFORME DE PAREJA ==")
try:
    import random
    import report_book as rb
    import report_couple as rc

    iv2 = rb._cargar_v2()
    rb.INST = iv2
    rb.CAPAS = {c["code"]: c for c in iv2["capas"]}

    def respuestas(semilla):
        random.seed(semilla)
        r = {}
        for capa in iv2["capas"]:
            for it in capa.get("items", []):
                if it.get("tipo") == "escala":
                    r[it["id"]] = random.randint(0, len(it["opciones"]) - 1)
        return r

    # Perfiles elegidos A PROPOSITO para disparar la seccion del reparto justo:
    #   · asimetria salarial fuerte (5.000 vs 2.000 = 2,5x)  -> coste de oportunidad
    #   · la que MENOS gana tiene MAS patrimonio (herencia)   -> flujo vs stock
    #   · niveles de vida ideales muy distintos               -> quien sube el liston
    #   · horas de trabajo pagado desiguales                  -> carga no retribuida
    dA = {"ingreso_mensual": 5000, "gasto_mensual": 2400, "patrimonio": 60000,
          "edad": 43, "coste_vida_ideal": 2400, "ahorro_mensual": 900,
          "inversiones_liquidas": 25000, "colchon_liquido": 9000,
          "pension_estimada": 1300, "gastos_comunes": 2000, "h_trabajo": 45}
    dB = {"ingreso_mensual": 2000, "gasto_mensual": 1900, "patrimonio": 400000,
          "edad": 41, "coste_vida_ideal": 1200, "ahorro_mensual": 250,
          "inversiones_liquidas": 100000, "colchon_liquido": 5000,
          "pension_estimada": 1050, "gastos_comunes": 2000, "h_trabajo": 22}

    salida = "INFORME-PAREJA-PRUEBA.pdf"
    if os.path.exists(salida):
        os.remove(salida)
    rc.build_couple(respuestas(11), dA, {"nombre": "Ana", "email": "a@x.com", "fecha": "10/09/2026"},
                    respuestas(22), dB, {"nombre": "Beto", "email": "b@x.com", "fecha": "10/09/2026"},
                    salida,
                    perfilA={"aportacion_modelo": "50/50"},
                    perfilB={"aportacion_modelo": "50/50"})
    tam = os.path.getsize(salida) if os.path.exists(salida) else 0
    if tam < 10000:
        fallos.append("El informe de pareja ha salido vacio.")
        print("  X  solo %d bytes." % tam)
    else:
        print("  OK - generado %s (%d KB)" % (salida, tam // 1024))
except Exception as e:
    import traceback
    traceback.print_exc()
    fallos.append("El informe de pareja no se ha generado: %s" % e)

# ---------------------------------------------------- utilidad de lectura
def _texto(fl, prof=0):
    """Texto de un flowable, ENTRANDO dentro de las tablas.

    Los callouts y los cuadros de este informe son Table, no Paragraph: si solo
    se mira .text, las comprobaciones dan falso negativo sobre texto que si esta
    en el PDF. Por eso se recorre tambien el contenido de las celdas.
    """
    if prof > 8 or fl is None:
        return ""
    if isinstance(fl, (list, tuple)):
        return "".join(_texto(x, prof + 1) for x in fl)
    t = getattr(fl, "text", None)
    if isinstance(t, str):
        return t + " "
    out = ""
    # KeepTogether guarda sus hijos en _content: los callouts de este informe son
    # KeepTogether([Table([[Paragraph(...)]])]). Sin esta rama, el lector no ve
    # NADA de lo que hay dentro de un callout y da falso negativo.
    for attr in ("_content", "_cellvalues"):
        hijos = getattr(fl, attr, None)
        if not hijos:
            continue
        for h in hijos:
            out += _texto(h, prof + 1)
    return out


# ---------------------------------------------------- 3. la seccion nueva
print("\n== 3) EL REPARTO JUSTO (cuatro varas) ==")
try:
    import report_couple as rc2
    sec = rc2.seccion_reparto_justo(dA, dB, respuestas(11), respuestas(22), "Ana", "Beto")
    if not sec:
        fallos.append("La seccion del reparto justo no se ha generado con datos que deberian dispararla.")
        print("  X  no se ha generado.")
    else:
        texto = "".join(_texto(p) for p in sec)
        comprobar = [
            ("sale la tabla de las cuatro varas", "cuatro varas" in texto),
            ("mide patrimonio, no solo nomina", "stock" in texto),
            ("cuantifica el coste de oportunidad", "En diez anos" in texto or "En diez a" in texto),
            ("nombra quien sube el nivel de vida", "quien se gasta" in texto.lower() or "decide cu" in texto.lower()),
            ("cierra con la idea de no tener politica", "ninguna" in texto),
        ]
        for nombre, ok in comprobar:
            if ok:
                print("  OK - %s" % nombre)
            else:
                print("  X  - %s" % nombre)
                fallos.append("Reparto justo: falta -> %s" % nombre)
except Exception as e:
    import traceback
    traceback.print_exc()
    fallos.append("La seccion del reparto justo ha reventado: %s" % e)

# ---------------------------------------------------- 4. el sistema recomendado
print("\n== 4) EL SISTEMA QUE OS RECOMENDAMOS ==")
try:
    import report_couple as rc3
    sec4 = rc3.seccion_sistema_hogar(dA, dB, respuestas(11), respuestas(22), "Ana", "Beto")
    if not sec4:
        fallos.append("La seccion del sistema recomendado no se ha generado.")
        print("  X  no se ha generado.")
    else:
        t4 = "".join(_texto(p) for p in sec4)
        comprobar4 = [
            ("recomienda un modelo concreto", "Vuestro modelo:" in t4),
            ("el modelo encaja con 2,5x de asimetria",
             ("proporcional" in t4.lower()) or ("caja com" in t4.lower())),
            ("sale la cuenta del proyecto comun", "PROYECTO COM" in t4),
            ("sale la cuenta de patrimonio", "PATRIMONIO" in t4),
            ("sale la cuenta de autonomia", "AUTONOM" in t4),
            ("salen las cinco preguntas", "cinco preguntas" in t4.lower()),
            ("pide fecha de revision", "revisi" in t4.lower()),
        ]
        for nombre, ok in comprobar4:
            if ok:
                print("  OK - %s" % nombre)
            else:
                print("  X  - %s" % nombre)
                fallos.append("Sistema recomendado: falta -> %s" % nombre)
except Exception as e:
    import traceback
    traceback.print_exc()
    fallos.append("La seccion del sistema recomendado ha reventado: %s" % e)

# ---------------------------------------------------- resultado
print("\n" + "=" * 58)
if fallos:
    print("ROJO - %d problema(s):" % len(fallos))
    for f in fallos:
        print("  X", f)
    sys.exit(1)
print("VERDE - el informe de pareja esta correcto.")
sys.exit(0)
