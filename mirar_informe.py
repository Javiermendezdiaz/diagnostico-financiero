#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""COMPROBACION DE COHERENCIA + INFORME DE PRUEBA.

Para Javier: ejecuta esto y no tienes que interpretar nada.

  1) Comprueba que el Numero de Libertad es EL MISMO por todas las rutas del
     informe (era el fallo grave: hasta 248.000 EUR de diferencia entre paginas).
  2) Genera un informe T2 real en INFORME-PRUEBA.pdf para que lo mires con
     tus propios ojos.

Uso:   python mirar_informe.py
"""
import os
import sys

os.environ.setdefault("MPLBACKEND", "Agg")

SALIDA = "INFORME-PRUEBA.pdf"

# Perfil de prueba realista: 44 anos, pension estimada, algo invertido.
# Con pension > 0 y edad < 67 es el caso que destapaba la incoherencia.
DATOS = {
    "edad": 44,
    "ingreso_mensual": 3800,
    "gasto_mensual": 2900,
    "ahorro_mensual": 700,
    "patrimonio": 210000,
    "inversiones_liquidas": 45000,
    "colchon_liquido": 12000,
    "pension_estimada": 1250,
    "coste_vida_ideal": 3900,
    "renta_pasiva": 150,
    "deuda_total": 68000,
    "cuota_deuda": 420,
    "gasto_estatus": 300,
    "pct_gasto_fijo": 62,
}

problemas = []


def titulo(t):
    print("\n" + "=" * 62)
    print(" " + t)
    print("=" * 62)


def eur(v):
    try:
        return ("%s EUR" % format(round(float(v)), ",d")).replace(",", ".")
    except Exception:
        return str(v)


# ------------------------------------------------------- 1. COHERENCIA
titulo("1) UN SOLO NUMERO EN TODO EL INFORME")
try:
    import report_book as rb
    import seccion_apertura as ap

    n_informe = rb.fi_metrics(DATOS)[0]
    n_motor = (ap.datos_expectativas(DATOS) or {}).get("numero_libertad")

    print("  Ruta del one-pager / tabla / panel :", eur(n_informe))
    print("  Ruta del motor ('las 4 vias')      :", eur(n_motor))

    if not n_motor:
        problemas.append("El motor no ha devuelto numero para el perfil de prueba.")
    elif abs(n_informe - n_motor) > 1:
        print("\n  X FALLO: siguen siendo cifras DISTINTAS.")
        print("    Diferencia:", eur(abs(n_informe - n_motor)))
        problemas.append("fi_metrics y el motor no coinciden.")
    else:
        print("\n  OK - las dos rutas dan la misma cifra, al euro.")

    # El grafico de proyeccion dibujaba su propia meta con otro x25.
    try:
        import inspect
        src = inspect.getsource(rb.panel_proyeccion)
        if "fi_metrics(datos)" in src:
            print("  OK - el grafico de proyeccion usa la cifra canonica.")
        else:
            problemas.append("panel_proyeccion sigue calculando su propia meta.")
            print("  X FALLO: el grafico de proyeccion no usa la cifra canonica.")
    except Exception:
        pass
except Exception as e:
    import traceback
    traceback.print_exc()
    problemas.append("No se ha podido comprobar la coherencia: %s" % e)


# ------------------------------------------------------- 2. RASTRO DE "25x"
titulo("2) NO DEBE QUEDAR NINGUN '25x' EN EL TEXTO")
try:
    restos = []
    for fichero in ("report_book.py", "report_couple.py"):
        if not os.path.exists(fichero):
            continue
        for i, linea in enumerate(open(fichero, encoding="utf-8", errors="replace"), 1):
            if linea.lstrip().startswith("#"):
                continue                      # los comentarios pueden mencionarlo
            for marca in ("regla 25", "25×", "× 25", "por 25"):
                if marca in linea:
                    restos.append("%s:%d" % (fichero, i))
                    break
    if restos:
        print("  X Quedan referencias visibles al cliente:")
        for r in restos:
            print("     -", r)
        problemas.append("Quedan %d referencias a la regla 25x." % len(restos))
    else:
        print("  OK - ninguna referencia visible al cliente.")
except Exception as e:
    problemas.append("No se ha podido revisar el texto: %s" % e)


# ------------------------------------------------------- 3. INFORME REAL
titulo("3) GENERANDO UN INFORME T2 DE VERDAD")
try:
    import report_book as rb
    import score_v2 as sv
    import random

    iv2 = rb._cargar_v2()
    rb.INST = iv2
    rb.CAPAS = {c["code"]: c for c in iv2["capas"]}

    random.seed(7)
    resp = {}
    for capa in iv2["capas"]:
        for it in capa.get("items", []):
            if it.get("tipo") == "escala":
                resp[it["id"]] = random.randint(0, len(it["opciones"]) - 1)

    try:
        extras = sv.computar_extras(resp, dict(DATOS), {}, iv2)
    except Exception:
        extras = None

    if os.path.exists(SALIDA):
        os.remove(SALIDA)
    rb.build_book_v2(resp, dict(DATOS),
                     {"nombre": "PRUEBA", "email": "prueba@adapta.com", "fecha": "10/09/2026"},
                     SALIDA, perfil_in={}, depth="completo", extras=extras)

    tam = os.path.getsize(SALIDA) if os.path.exists(SALIDA) else 0
    if tam < 10000:
        problemas.append("El PDF ha salido vacio o diminuto.")
        print("  X El PDF pesa solo %d bytes." % tam)
    else:
        print("  OK - generado %s (%d KB)" % (SALIDA, tam // 1024))
except Exception as e:
    import traceback
    traceback.print_exc()
    problemas.append("El informe no se ha generado: %s" % e)


# ------------------------------------------------------- RESULTADO
titulo("RESULTADO")
if problemas:
    print("  ROJO - NO subas nada todavia. %d problema(s):\n" % len(problemas))
    for p in problemas:
        print("   X", p)
    print("\n  Copia todo esto y pasamelo.")
    sys.exit(1)

print("  VERDE - las comprobaciones automaticas pasan.\n")
print("  Ahora abre " + SALIDA + " y mira con tus ojos:")
print("   [ ] La apertura son 4 paginas y empieza con una cifra grande.")
print("   [ ] El semaforo lista las 12 dimensiones, de peor a mejor.")
print("   [ ] El Numero de Libertad es IDENTICO en todas las paginas donde salga.")
print("   [ ] No hay dos paginas seguidas repitiendo los mismos indicadores.")
print("   [ ] Salen 'El orden importa mas que la media' y 'Como sacas el dinero'.")
sys.exit(0)
