#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INVENTARIO COMPLETO: tu carpeta frente a lo publicado en GitHub.

Por que existe: la copia local lleva meses actualizandose a mano, asi que git
ya no sabe que version es cada fichero. Antes de tocar nada hay que MEDIR:
cuantos ficheros divergen, cuales, y en que direccion.

SOLO LEE. No modifica, no borra, no sube. Escribe INVENTARIO.txt.

Cuatro categorias:
  IDENTICO      - tu copia y GitHub coinciden. Nada que hacer.
  SOLO LOCAL    - esta en tu ordenador pero no en GitHub (herramientas, temporales).
  SOLO GITHUB   - esta publicado pero no lo tienes. Tu copia esta incompleta.
  DIVERGENTE    - existe en los dos y son distintos. ESTOS son los que importan.
"""
import os
import subprocess
import hashlib

# Lo que de verdad importa: codigo y paginas. Lo demas (PNG temporales, PDFs de
# prueba, logs) es ruido generado y no tiene por que coincidir.
EXTENSIONES = (".py", ".html", ".json", ".txt", ".yaml", ".yml", ".md")
IGNORAR_DIR = {".git", "__pycache__", "PAGINAS", "PAGINAS-PAREJA", "SUBIR-A-GITHUB",
               "itap-final", "OneDrive", ".github", "fonts", "static"}
IGNORAR_FICH = {"RESULTADO.txt", "RESULTADO2.txt", "RESULTADO-FINAL.txt",
                "RESULTADO-CIERRE.txt", "RESULTADO-SUBIR.txt", "RESULTADO-MIRAR.txt",
                "RESULTADO-VER.txt", "RESULTADO-PAREJA.txt", "COMPARACION.txt",
                "DIFF.txt", "INVENTARIO.txt"}

SALIDA = "INVENTARIO.txt"


def _h(b):
    return hashlib.sha1(b).hexdigest()


def publicados():
    """Ficheros que hay en GitHub (rama main), con su contenido."""
    try:
        r = subprocess.run(["git", "ls-tree", "-r", "--name-only", "origin/main"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return None


def contenido_github(ruta):
    try:
        r = subprocess.run(["git", "show", "origin/main:%s" % ruta], capture_output=True)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def locales():
    out = []
    for raiz, dirs, fichs in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIR and not d.startswith(".")]
        for f in fichs:
            if not f.lower().endswith(EXTENSIONES):
                continue
            if f in IGNORAR_FICH:
                continue
            rel = os.path.relpath(os.path.join(raiz, f), ".").replace("\\", "/")
            out.append(rel)
    return sorted(out)


print("Actualizando la referencia de GitHub...")
subprocess.run(["git", "fetch"], capture_output=True)

pub = publicados()
if pub is None:
    print("X No se ha podido leer GitHub (git no disponible o sin conexion).")
    raise SystemExit(1)
pub_set = set(p for p in pub if p.lower().endswith(EXTENSIONES))
loc = locales()
loc_set = set(loc)

identicos, divergentes, solo_local, solo_github = [], [], [], []

for ruta in sorted(loc_set | pub_set):
    en_local = ruta in loc_set
    en_pub = ruta in pub_set
    if en_local and not en_pub:
        solo_local.append(ruta)
        continue
    if en_pub and not en_local:
        solo_github.append(ruta)
        continue
    try:
        with open(ruta, "rb") as f:
            a = f.read()
    except Exception:
        solo_github.append(ruta)
        continue
    b = contenido_github(ruta)
    if b is None:
        solo_local.append(ruta)
    elif _h(a) == _h(b):
        identicos.append(ruta)
    else:
        # Cuantas lineas difieren, para saber si es un retoque o un abismo.
        try:
            la = a.decode("utf-8", "replace").splitlines()
            lb = b.decode("utf-8", "replace").splitlines()
            import difflib
            n = sum(1 for l in difflib.unified_diff(lb, la, lineterm="", n=0)
                    if l[:1] in "+-" and l[:3] not in ("+++", "---"))
        except Exception:
            n = -1
        divergentes.append((ruta, n))

with open(SALIDA, "w", encoding="utf-8") as o:
    o.write("INVENTARIO: tu carpeta frente a GitHub\n")
    o.write("=" * 62 + "\n")
    o.write("Solo lectura. No se ha modificado nada.\n\n")
    o.write("RESUMEN\n")
    o.write("  Identicos ......... %d\n" % len(identicos))
    o.write("  DIVERGENTES ....... %d   <-- los que importan\n" % len(divergentes))
    o.write("  Solo en tu equipo . %d\n" % len(solo_local))
    o.write("  Solo en GitHub .... %d\n" % len(solo_github))

    o.write("\n\n### DIVERGENTES (existen en los dos y son distintos)\n")
    if divergentes:
        for ruta, n in sorted(divergentes, key=lambda x: -x[1]):
            o.write("  %-42s %s lineas distintas\n" % (ruta, n if n >= 0 else "?"))
    else:
        o.write("  Ninguno. Tu copia coincide con lo publicado.\n")

    o.write("\n\n### SOLO EN GITHUB (te faltan en tu carpeta)\n")
    for r in solo_github or ["  (ninguno)"]:
        o.write("  %s\n" % r)

    o.write("\n\n### SOLO EN TU EQUIPO (no estan publicados)\n")
    for r in solo_local or ["  (ninguno)"]:
        o.write("  %s\n" % r)

    o.write("\n\n### IDENTICOS\n")
    for r in identicos or ["  (ninguno)"]:
        o.write("  %s\n" % r)

print("\nRESUMEN")
print("  Identicos ......... %d" % len(identicos))
print("  DIVERGENTES ....... %d" % len(divergentes))
print("  Solo en tu equipo . %d" % len(solo_local))
print("  Solo en GitHub .... %d" % len(solo_github))
print("\nDetalle en %s" % SALIDA)
