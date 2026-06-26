#!/usr/bin/env python3
"""Linter del instrumento ITAP: garantiza que las preguntas son siempre las oportunas.
Comprueba IDs unicos, wording no duplicado, cobertura por capa, numericas sanas y campos esperados.
Uso: python3 validar_instrumento.py   (sale 0 si OK, 1 si hay errores)."""
import json, sys, re, unicodedata

def norm(s):
    s=(s or "").lower().strip()
    s="".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
    return re.sub(r"[^a-z0-9 ]"," ", s)

def lint(path="itap_v2.json"):
    j=json.load(open(path,encoding="utf-8"))
    err=[]; warn=[]
    capas=j.get("capas",[]); nfin=j.get("numericas_financieras",[])
    # 1) 12 capas
    if len(capas)!=12: err.append("Se esperan 12 capas, hay %d"%len(capas))
    # 2) IDs unicos (items + numericas)
    ids={}
    def reg(_id, where):
        if not _id: err.append("ID vacio en %s"%where); return
        if _id in ids: err.append("ID DUPLICADO '%s' (en %s y %s)"%(_id,ids[_id],where))
        else: ids[_id]=where
    # 3) wording duplicado
    textos={}
    for c in capas:
        items=[it for it in c.get("items",[]) if it.get("tipo")=="escala"]
        if len(items)<6: warn.append("Capa %s tiene solo %d items escala (<6)"%(c.get("code"),len(items)))
        for it in items:
            reg(it.get("id"),"capa %s"%c.get("code"))
            t=norm(it.get("texto") or it.get("pregunta") or it.get("label"))
            if len(t)>12:
                if t in textos: err.append("PREGUNTA DUPLICADA: '%s' en %s y %s"%(t[:45],textos[t],it.get("id")))
                else: textos[t]=it.get("id")
            ops=it.get("opciones") or []
            if len(ops)<2: err.append("Item %s con <2 opciones"%it.get("id"))
    # 4) numericas: campo unico, presente
    campos={}
    CAMPOS_VALIDOS={"ingreso_mensual","gasto_mensual","ahorro_mensual","renta_pasiva","coste_vivienda",
      "cuota_deuda","patrimonio","colchon_liquido","deuda_total","pct_vivienda","pension_estimada",
      "horas_semana","ing_trabajo","h_trabajo","ing_inversion","h_inversion","ing_alquiler","h_alquiler",
      "ing_otros","h_otros","inversiones_liquidas","rentabilidad_actual","pct_gasto_fijo","gasto_estatus",
      "edad_hijo_menor","gastos_comunes","coste_vida_ideal","gastos_anuales","valor_inmuebles"}
    for n in nfin:
        reg(n.get("id"),"numerica")
        ca=n.get("campo")
        if not ca: err.append("Numerica %s sin campo"%n.get("id"))
        elif ca in campos: err.append("CAMPO numerico DUPLICADO '%s'"%ca)
        else:
            campos[ca]=n.get("id")
            if ca not in CAMPOS_VALIDOS: warn.append("Campo numerico no catalogado: %s"%ca)
    # 5) campos financieros nucleo presentes
    NUCLEO={"ingreso_mensual","gasto_mensual","ahorro_mensual","patrimonio","colchon_liquido","deuda_total"}
    faltan=NUCLEO-set(campos)
    if faltan: err.append("Faltan campos financieros NUCLEO: %s"%", ".join(sorted(faltan)))
    return err,warn

if __name__=="__main__":
    e,w=lint()
    print("== LINTER INSTRUMENTO ITAP ==")
    print("ERRORES (%d):"%len(e))
    for x in e: print("  X", x)
    print("AVISOS (%d):"%len(w))
    for x in w: print("  !", x)
    print("RESULTADO:", "OK" if not e else "FALLO")
    sys.exit(1 if e else 0)
