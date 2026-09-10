#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exporta paginas sueltas del informe a PNG para poder MIRARLAS.

Sin esto la maquetacion se corrige a ciegas: el PDF compila, pero nadie ve si
un bloque se parte, si un titulo choca con una tabla o si una pagina queda vacia.

Uso:  python ver_paginas.py [fichero.pdf] [paginas]
      python ver_paginas.py INFORME-PRUEBA.pdf 1-10
"""
import sys
import os

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Falta PyMuPDF. Instalando...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pymupdf"], check=False)
    import fitz

pdf = sys.argv[1] if len(sys.argv) > 1 else "INFORME-PRUEBA.pdf"
rango = sys.argv[2] if len(sys.argv) > 2 else "1-8"

if not os.path.exists(pdf):
    print("No existe %s" % pdf)
    sys.exit(1)

if "-" in rango:
    ini, fin = rango.split("-")
    paginas = range(int(ini), int(fin) + 1)
else:
    paginas = [int(rango)]

doc = fitz.open(pdf)
total = len(doc)
print("%s tiene %d paginas." % (pdf, total))

destino = "PAGINAS"
os.makedirs(destino, exist_ok=True)
# limpiar exportaciones anteriores para no mirar una version vieja por error
for viejo in os.listdir(destino):
    if viejo.lower().endswith(".png"):
        try:
            os.remove(os.path.join(destino, viejo))
        except Exception:
            pass

zoom = fitz.Matrix(1.35, 1.35)
for n in paginas:
    if n < 1 or n > total:
        continue
    pag = doc[n - 1]
    pix = pag.get_pixmap(matrix=zoom)
    ruta = os.path.join(destino, "pag-%02d.png" % n)
    pix.save(ruta)
    print("  ->", ruta)

doc.close()
print("Listo.")
