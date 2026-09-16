#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba los endpoints de RESCATE sin tocar el servidor de produccion.

Levanta la aplicacion en memoria con una base de datos de prueba, crea una
sesion completa SIN PAGAR (el caso de Maiten) y comprueba que:

  1. Sin clave no se puede entrar (falla cerrado).
  2. Con clave, la busqueda por email encuentra la sesion sin pagar.
  3. El PDF se genera y se descarga aunque `pagado` sea 0.
  4. El rescate NO modifica nada: la sesion sigue marcada como no pagada.
"""
import os
import sys
import json
import tempfile

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ["ADMIN_KEY"] = "CLAVE-DE-PRUEBA"
# Base de datos y carpeta de informes aisladas: no tocamos nada real.
_tmp = tempfile.mkdtemp(prefix="rescate_")
os.environ["DB_PATH"] = os.path.join(_tmp, "prueba.db")
os.environ["REPORTS_DIR"] = os.path.join(_tmp, "informes")

fallos = []


def chk(nombre, ok, detalle=""):
    if ok:
        print("  OK  - %s" % nombre)
    else:
        print("  X   - %s %s" % (nombre, detalle))
        fallos.append(nombre)


try:
    from fastapi.testclient import TestClient
    import app as A
except Exception as e:
    print("No se ha podido cargar la aplicacion: %s" % e)
    sys.exit(1)

cli = TestClient(A.app)

# ---------------------------------------------------------------- preparar
print("== Preparando una sesion COMPLETA y SIN PAGAR ==")
EMAIL = "clienta.prueba@ejemplo.com"
try:
    iv2 = A.rb._cargar_v2()
    A.rb.INST = iv2
    A.rb.CAPAS = {c["code"]: c for c in iv2["capas"]}
    import random
    random.seed(5)
    resp = {}
    for capa in iv2["capas"]:
        for it in capa.get("items", []):
            if it.get("tipo") == "escala":
                resp[it["id"]] = random.randint(0, len(it["opciones"]) - 1)
    datos = {"edad": 44, "ingreso_mensual": 3800, "gasto_mensual": 2900,
             "ahorro_mensual": 700, "patrimonio": 210000, "inversiones_liquidas": 45000,
             "colchon_liquido": 12000, "pension_estimada": 1250, "coste_vida_ideal": 3900}
    SID = "sesion-de-prueba-rescate"
    with A.db() as c:
        c.execute("INSERT INTO sesiones (id,email,nombre,tier,respuestas,datos,pagado) "
                  "VALUES (?,?,?,?,?,?,0)",
                  (SID, EMAIL, "Clienta Prueba", 2, json.dumps(resp), json.dumps(datos)))
    print("  sesion creada: %s (pagado=0)" % SID)
except Exception as e:
    import traceback
    traceback.print_exc()
    print("No se ha podido preparar la sesion: %s" % e)
    sys.exit(1)

# ---------------------------------------------------------------- pruebas
print("\n== 1) SIN CLAVE NO SE ENTRA ==")
r = cli.get("/api/rescate", params={"email": EMAIL})
chk("busqueda sin clave -> 403", r.status_code == 403, "(dio %s)" % r.status_code)
r = cli.get("/api/rescate/pdf", params={"sid": SID})
chk("descarga sin clave -> 403", r.status_code == 403, "(dio %s)" % r.status_code)
r = cli.get("/api/rescate", params={"key": "clave-incorrecta", "email": EMAIL})
chk("clave incorrecta -> 403", r.status_code == 403, "(dio %s)" % r.status_code)

print("\n== 2) CON CLAVE, ENCUENTRA LA SESION SIN PAGAR ==")
r = cli.get("/api/rescate", params={"key": "CLAVE-DE-PRUEBA", "email": EMAIL})
chk("busqueda -> 200", r.status_code == 200, "(dio %s)" % r.status_code)
chk("aparece el cliente", "Clienta Prueba" in r.text)
chk("aparece el enlace de descarga", "/api/rescate/pdf" in r.text)
chk("se ve que NO ha pagado", ">NO<" in r.text.replace(" ", ""))

print("\n== 3) EL PDF SE DESCARGA AUNQUE NO HAYA PAGADO ==")
r = cli.get("/api/rescate/pdf", params={"key": "CLAVE-DE-PRUEBA", "sid": SID})
chk("descarga -> 200", r.status_code == 200, "(dio %s)" % r.status_code)
chk("es un PDF de verdad", r.content[:4] == b"%PDF", "(empieza por %r)" % r.content[:8])
chk("pesa lo que debe (>500 KB)", len(r.content) > 500000, "(%d bytes)" % len(r.content))

print("\n== 4) EL RESCATE NO MODIFICA NADA ==")
with A.db() as c:
    row = c.execute("SELECT pagado,notificado FROM sesiones WHERE id=?", (SID,)).fetchone()
chk("sigue sin marcar como pagado", row["pagado"] in (0, None), "(pagado=%s)" % row["pagado"])
chk("no se ha marcado como notificado", row["notificado"] in (0, None), "(notificado=%s)" % row["notificado"])

print("\n== 5) SESION INEXISTENTE ==")
r = cli.get("/api/rescate/pdf", params={"key": "CLAVE-DE-PRUEBA", "sid": "no-existe"})
chk("sesion inexistente -> 404", r.status_code == 404, "(dio %s)" % r.status_code)

print("\n" + "=" * 58)
if fallos:
    print("ROJO - %d fallo(s):" % len(fallos))
    for f in fallos:
        print("   X", f)
    sys.exit(1)
print("VERDE - el rescate funciona y no toca nada.")
sys.exit(0)
