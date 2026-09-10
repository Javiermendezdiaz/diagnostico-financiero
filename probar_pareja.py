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

    dA = {"ingreso_mensual": 3200, "gasto_mensual": 2400, "patrimonio": 90000,
          "edad": 43, "coste_vida_ideal": 3400, "ahorro_mensual": 600,
          "inversiones_liquidas": 30000, "colchon_liquido": 9000,
          "pension_estimada": 1300}
    dB = {"ingreso_mensual": 2400, "gasto_mensual": 1900, "patrimonio": 35000,
          "edad": 41, "ahorro_mensual": 350, "inversiones_liquidas": 12000,
          "colchon_liquido": 5000, "pension_estimada": 1050}

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

# ---------------------------------------------------- resultado
print("\n" + "=" * 58)
if fallos:
    print("ROJO - %d problema(s):" % len(fallos))
    for f in fallos:
        print("  X", f)
    sys.exit(1)
print("VERDE - el informe de pareja esta correcto.")
sys.exit(0)
