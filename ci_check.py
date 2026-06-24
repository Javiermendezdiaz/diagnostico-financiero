#!/usr/bin/env python3
"""Inspector de calidad PRE-DESPLIEGUE. Falla (exit 1) si algo romperia produccion:
  1) pyflakes  -> nombres no definidos / sintaxis (la clase del bug 'datos')
  2) linter del instrumento -> preguntas coherentes
  3) smoke build T1/T2/T3 con perfiles limite -> el PDF se genera sin reventar
Uso local:  python ci_check.py    (verde = seguro desplegar)"""
import sys, os, subprocess, random
os.environ.setdefault("MPLBACKEND", "Agg")
FAILS = []
PYFILES = ["app.py","report_book.py","report_couple.py","score_v2.py","ai_sintesis.py",
           "legado_design.py","legado_pages.py","validar_instrumento.py"]

def chk_pyflakes():
    print("== 1) pyflakes (nombres no definidos / sintaxis) ==")
    files = [f for f in PYFILES if os.path.exists(f)]
    try:
        out = subprocess.run([sys.executable, "-m", "pyflakes"] + files, capture_output=True, text=True)
    except Exception as e:
        FAILS.append("pyflakes no ejecutable: %s" % e); return
    graves = [l for l in (out.stdout + out.stderr).splitlines()
              if ("undefined name" in l) or ("invalid syntax" in l)
              or ("syntax" in l.lower() and "error" in l.lower())]
    for l in graves:
        print("  X", l)
    if graves:
        FAILS.append("pyflakes: %d problema(s) grave(s)" % len(graves))
    else:
        print("  OK (sin nombres no definidos)")

def chk_linter():
    print("== 2) linter del instrumento ==")
    try:
        import validar_instrumento as vi
        e, w = vi.lint()
        for x in e:
            print("  X", x)
        if e:
            FAILS.append("instrumento: %d error(es)" % len(e))
        else:
            print("  OK (%d avisos)" % len(w))
    except Exception as ex:
        FAILS.append("linter no ejecutable: %s" % ex)

def _mkresp(iv2, seed, pat):
    random.seed(seed); r = {}
    for capa in iv2["capas"]:
        for it in capa.get("items", []):
            if it.get("tipo") != "escala":
                continue
            n = len(it["opciones"])
            r[it["id"]] = 0 if pat == "min" else (n - 1 if pat == "max" else random.randint(0, n - 1))
    return r

def chk_builds():
    print("== 3) smoke build T1/T2/T3 ==")
    import report_book as rb, report_couple as rc, score_v2 as sv
    iv2 = rb._cargar_v2(); rb.INST = iv2; rb.CAPAS = {c["code"]: c for c in iv2["capas"]}
    out = "/tmp/ci_out.pdf" if os.name != "nt" else "ci_out.pdf"
    perfiles = [
        ("vacio", {}, "rand"),
        ("ceros", {"ingreso_mensual":0,"gasto_mensual":0,"patrimonio":0,"edad":30}, "min"),
        ("vida_ideal", {"ingreso_mensual":2500,"gasto_mensual":2000,"ahorro_mensual":300,"patrimonio":40000,
                        "edad":42,"coste_vida_ideal":4500,"colchon_liquido":4000,"inversiones_liquidas":3000,
                        "gasto_estatus":400,"deuda_total":12000,"cuota_deuda":250}, "rand"),
    ]
    for nombre, d, pat in perfiles:
        for tier, depth in ((1, "esencial"), (2, "completo")):
            try:
                r = _mkresp(iv2, abs(hash((nombre, tier))) % 9999, pat)
                try: ex = sv.computar_extras(r, dict(d), {}, iv2)
                except Exception: ex = None
                if os.path.exists(out): os.remove(out)
                rb.build_book_v2(r, dict(d), {"nombre":"CI","email":"ci@x.com","fecha":"01/01"}, out,
                                 perfil_in={}, depth=depth, extras=ex)
                sz = os.path.getsize(out) if os.path.exists(out) else 0
                if sz < 10000:
                    raise RuntimeError("PDF vacio/pequeno (%d bytes)" % sz)
                print("  OK T%d %-11s (%d KB)" % (tier, nombre, sz // 1024))
            except Exception as e:
                import traceback; traceback.print_exc()
                FAILS.append("build T%d %s: %s" % (tier, nombre, e))
    try:
        rA = _mkresp(iv2, 1, "rand"); rB = _mkresp(iv2, 2, "rand")
        dA = {"ingreso_mensual":2600,"gasto_mensual":2100,"patrimonio":50000,"edad":40,"coste_vida_ideal":4000}
        dB = {"ingreso_mensual":2000,"gasto_mensual":1700,"patrimonio":20000,"edad":38}
        if os.path.exists(out): os.remove(out)
        rc.build_couple(rA, dA, {"nombre":"Ana","email":"a@x.com","fecha":"01/01"},
                        rB, dB, {"nombre":"Beto","email":"b@x.com","fecha":"01/01"}, out,
                        perfilA={"aportacion_modelo":"50/50"}, perfilB={"aportacion_modelo":"50/50"})
        sz = os.path.getsize(out) if os.path.exists(out) else 0
        if sz < 10000:
            raise RuntimeError("PDF pareja vacio")
        print("  OK T3 pareja      (%d KB)" % (sz // 1024))
    except Exception as e:
        import traceback; traceback.print_exc()
        FAILS.append("build T3: %s" % e)

if __name__ == "__main__":
    chk_pyflakes(); chk_linter(); chk_builds()
    print("\n==================== RESULTADO ====================")
    if FAILS:
        print("ROJO -- %d problema(s), NO desplegar:" % len(FAILS))
        for f in FAILS:
            print("  X", f)
        sys.exit(1)
    print("VERDE -- todo pasa, seguro para desplegar.")
    sys.exit(0)
