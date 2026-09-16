#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muestra QUE cambia en los ficheros divergentes, no solo cuantas lineas.

Solo lee. Escribe DIFERENCIAS.txt.

Lineas '-' = lo PUBLICADO en GitHub
Lineas '+' = lo que hay en TU ORDENADOR
"""
import subprocess
import difflib

FICHEROS = ["funnel.html", "planes.html", "privacidad.html", "simulador.html",
            "arquetipos.html", "empezar.html", "test-arquetipo.html",
            "indice.html", "inicio.html"]

SALIDA = "DIFERENCIAS.txt"


def github(ruta):
    r = subprocess.run(["git", "show", "origin/main:%s" % ruta], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace").splitlines()


def local(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except Exception:
        return None


subprocess.run(["git", "fetch"], capture_output=True)

with open(SALIDA, "w", encoding="utf-8") as o:
    o.write("QUE CAMBIA EN CADA FICHERO DIVERGENTE\n")
    o.write("=" * 62 + "\n")
    o.write("'-' = publicado en GitHub   |   '+' = en tu ordenador\n")
    for ruta in FICHEROS:
        g, l = github(ruta), local(ruta)
        o.write("\n\n" + "#" * 62 + "\n# %s\n" % ruta + "#" * 62 + "\n")
        if g is None:
            o.write(">> no existe en GitHub\n"); continue
        if l is None:
            o.write(">> no existe en tu ordenador\n"); continue
        dif = list(difflib.unified_diff(g, l, "GITHUB", "TU-EQUIPO", lineterm="", n=1))
        if not dif:
            o.write(">> identicos\n"); continue
        # inicio.html es enorme: solo el resumen, no 1.182 lineas de ruido.
        limite = 60 if ruta != "inicio.html" else 24
        for i, ln in enumerate(dif):
            if i >= limite:
                o.write("\n   ... (recortado; hay muchas mas diferencias)\n")
                break
            o.write(ln + "\n")

print("Escrito %s" % SALIDA)
