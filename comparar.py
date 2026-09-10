#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compara cada fichero LOCAL con la version publicada en GitHub (origin/main).

Por que: la copia local NO es un reflejo limpio de lo publicado. Algunos ficheros
estan sin seguimiento en git y otros van por detras de GitHub. Subir la copia local
a ciegas puede DESHACER correcciones que ya estaban publicadas.

Escribe COMPARACION.txt con las diferencias exactas, linea a linea.
"""
import subprocess
import difflib
import os

FICHEROS = [
    "report_book.py",
    "report_couple.py",
    "test_numeros.py",
    "qa_coherencia.py",
    "motor_financiero_v3.py",
    "parametros.json",
    "ci_check.py",
]

SALIDA = "COMPARACION.txt"


def version_publicada(ruta):
    """Contenido del fichero tal y como esta en GitHub, o None si no existe alli."""
    try:
        r = subprocess.run(["git", "show", "origin/main:%s" % ruta],
                           capture_output=True)
        if r.returncode != 0:
            return None
        return r.stdout.decode("utf-8", errors="replace").splitlines()
    except Exception:
        return None


def version_local(ruta):
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


with open(SALIDA, "w", encoding="utf-8") as out:
    out.write("COMPARACION LOCAL vs GITHUB (origin/main)\n")
    out.write("=" * 62 + "\n")
    out.write("Lineas '-' = lo que hay PUBLICADO en GitHub\n")
    out.write("Lineas '+' = lo que hay en TU ORDENADOR\n")
    out.write("=" * 62 + "\n")

    for ruta in FICHEROS:
        pub = version_publicada(ruta)
        loc = version_local(ruta)
        out.write("\n\n" + "#" * 62 + "\n")
        out.write("# %s\n" % ruta)
        out.write("#" * 62 + "\n")

        if loc is None:
            out.write(">> NO EXISTE en tu ordenador.\n")
            continue
        if pub is None:
            out.write(">> NO EXISTE en GitHub todavia (fichero nuevo).\n")
            continue
        if pub == loc:
            out.write(">> IDENTICOS. Nada que revisar.\n")
            continue

        dif = list(difflib.unified_diff(pub, loc, "GITHUB", "TU-ORDENADOR",
                                        lineterm="", n=2))
        cambios = sum(1 for l in dif if l[:1] in "+-" and l[:3] not in ("+++", "---"))
        out.write(">> %d lineas distintas.\n\n" % cambios)
        for l in dif:
            out.write(l + "\n")

print("Escrito %s" % SALIDA)
