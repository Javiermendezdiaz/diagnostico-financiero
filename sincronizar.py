#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pone al dia las paginas web desfasadas: trae de GitHub la version publicada.

POR QUE
-------
La carpeta local lleva meses actualizandose a mano. El inventario demostro que
TODO el codigo Python coincide con GitHub, pero varias paginas .html se quedaron
en una version anterior. En concreto, la correccion de RGPD (servir las
tipografias desde tu propio servidor en vez de Google Fonts) esta publicada pero
NO en la copia local.

Lo publicado es lo correcto. Esto solo sustituye lo viejo por lo bueno.

SEGURIDAD
---------
  1. Antes de tocar nada, copia TODOS los ficheros afectados a COPIA-SEGURIDAD\\
     con la fecha en el nombre. Si algo no cuadra, se recuperan de ahi.
  2. Si un fichero ya coincide con GitHub, no se toca.
  3. inicio.html NO se toca: tiene 1.182 lineas de diferencia y es la pagina
     principal. Esa decision se toma mirandola, no a ciegas.
"""
import os
import shutil
import subprocess
import datetime

# Paginas donde lo publicado manda.
# inicio.html entra ahora: al mirarlo se confirmo que la copia local era la HOME
# ANTIGUA (titular "Tu dinero ya sabe la verdad sobre ti" y "Desde 19 EUR" en la
# descripcion), anterior al redisenio que quito los precios de la portada. Tenerla
# en la carpeta era el riesgo de volver a publicarla por error, cosa que ya paso.
PAGINAS = ["funnel.html", "planes.html", "privacidad.html", "simulador.html",
           "arquetipos.html", "empezar.html", "test-arquetipo.html", "indice.html",
           "inicio.html"]

BACKUP = "COPIA-SEGURIDAD"


def github(ruta):
    r = subprocess.run(["git", "show", "origin/main:%s" % ruta], capture_output=True)
    return r.stdout if r.returncode == 0 else None


print("Actualizando la referencia de GitHub...")
subprocess.run(["git", "fetch"], capture_output=True)

sello = datetime.datetime.now().strftime("%Y%m%d-%H%M")
destino = os.path.join(BACKUP, sello)
os.makedirs(destino, exist_ok=True)
print("Copia de seguridad en: %s\n" % destino)

cambiados, iguales, fallos = [], [], []

for pag in PAGINAS:
    pub = github(pag)
    if pub is None:
        fallos.append("%s (no esta en GitHub)" % pag)
        print("  ?  %-24s no esta en GitHub, lo dejo como esta" % pag)
        continue
    if not os.path.exists(pag):
        fallos.append("%s (no esta en tu carpeta)" % pag)
        print("  ?  %-24s no esta en tu carpeta" % pag)
        continue
    with open(pag, "rb") as f:
        act = f.read()
    if act == pub:
        iguales.append(pag)
        print("  =  %-24s ya coincide, no lo toco" % pag)
        continue
    # 1) copia de seguridad ANTES de escribir
    shutil.copy2(pag, os.path.join(destino, pag))
    # 2) escritura atomica: si algo falla a medias, el original sigue intacto
    tmp = pag + ".nuevo"
    with open(tmp, "wb") as f:
        f.write(pub)
    os.replace(tmp, pag)
    cambiados.append(pag)
    print("  ->  %-24s actualizado desde GitHub" % pag)

print("\n" + "=" * 58)
print("Actualizados .... %d" % len(cambiados))
print("Ya coincidian ... %d" % len(iguales))
if fallos:
    print("Sin tocar ....... %d" % len(fallos))
    for f in fallos:
        print("   ?", f)
if cambiados:
    print("\nTus versiones anteriores estan guardadas en:")
    print("   %s" % os.path.abspath(destino))
    print("Para deshacer: copia esos ficheros de vuelta a la carpeta.")
print("\nCuando acabe, tu carpeta y GitHub dicen lo mismo en todas las paginas.")
