# -*- coding: utf-8 -*-
"""Motor financiero v3 — Adapta Family Office.

Consume el payload canonico del cuestionario adaptativo nuevo (empezar3.html) y
produce los hallazgos de banca privada que alimentan el PDF: precio/hora, fuga,
esfuerzo de deuda, numero de libertad NETO de pension (y herencia), patrimonio
productivo vs dormido, los 4 caminos a la meta, proteccion familiar y el
agregador global con renormalizacion.

AISLADO: sin dependencias de report_book ni del motor v2. Solo Python estandar.
Es la UNICA fuente de verdad del scoring financiero nuevo; el cliente solo captura
actividad e importe, aqui se deriva todo. Todo blindado: cualquier dato ausente
degrada con elegancia, nunca lanza.

Pendiente de cablear a score_v2/report_book cuando el sandbox sincronice. No se
ha podido testear por bash (mount de OneDrive desincronizado); escrito con la
herramienta de archivo, a verificar antes de cualquier despliegue.
"""

# ---------- catalogos (espejo de los modulos JS; aqui mandan) ----------
ING_POLO = {  # polo y peso de calidad del ingreso pasivo
    "nomina": ("activo", 1.00), "autonomo": ("activo", 1.00), "extras": ("activo", 1.00),
    "alquiler": ("pasivo", 0.65), "dividendos": ("pasivo", 0.90), "intereses": ("pasivo", 0.85),
    "pension": ("pasivo", 1.00), "royalties": ("pasivo", 0.85),
    "otros_act": ("activo", 1.00), "otros_pas": ("pasivo", 0.80),
}
GAS_POLO = {  # rigido / discrecional
    "vivienda": "rigido", "suministros": "rigido", "comida": "rigido", "transporte": "rigido",
    "seguros": "rigido", "cuotas": "rigido", "hijos": "rigido",
    "ocio": "discrecional", "subs": "discrecional", "caprichos": "discrecional",
    "viajes": "discrecional", "otros": "discrecional",
}
DEU_TIER = {  # interes por defecto y nivel de coste
    "hipoteca": (3.0, "v"), "hipoteca_inv": (3.5, "v"), "familiar": (0.0, "v"),
    "coche": (7.0, "a"), "personal": (8.5, "a"), "consumo": (12.0, "r"),
    "revolving": (20.0, "r"), "otros": (9.0, "a"),
}
RV_POR_PERFIL = {1: 10, 2: 30, 3: 50, 4: 70, 5: 85}
RENT_REAL_POR_PERFIL = {1: 2.5, 2: 4.0, 3: 5.5, 4: 7.0, 5: 8.5}
UNIV, INDEP, COSTE_HIJO = 18, 24, 7200


def _f(x, d=0.0):
    try:
        return float(x)
    except Exception:
        return d


# ---------- INGRESOS: precio/hora, ratio pasivo, concentracion ----------
def analizar_ingresos(fuentes):
    """fuentes: [{tipo, importe, horas?}]. Devuelve dict de hallazgos."""
    try:
        fs = [f for f in (fuentes or []) if _f(f.get("importe")) > 0]
        total = sum(_f(f["importe"]) for f in fs)
        if total <= 0:
            return {}
        pasivo = sum(_f(f["importe"]) for f in fs if ING_POLO.get(f.get("tipo"), ("activo", 1))[0] == "pasivo")
        pasivo_cal = sum(_f(f["importe"]) * ING_POLO.get(f.get("tipo"), ("activo", 1.0))[1]
                         for f in fs if ING_POLO.get(f.get("tipo"), ("activo", 1))[0] == "pasivo")
        # concentracion (HHI 0-1) y mayor dependencia
        hhi = sum((_f(f["importe"]) / total) ** 2 for f in fs)
        top = max(fs, key=lambda f: _f(f["importe"]))
        # precio/hora por fuente activa (importe mensual -> anual / horas anuales)
        ph = []
        for f in fs:
            if ING_POLO.get(f.get("tipo"), ("activo", 1))[0] == "activo" and _f(f.get("horas")) > 0:
                eur_hora = (_f(f["importe"]) * 12.0) / (_f(f["horas"]) * 52.0)
                ph.append({"tipo": f.get("tipo"), "eur_hora": round(eur_hora, 1)})
        ph_global = None
        h_tot = sum(_f(f.get("horas")) for f in fs if ING_POLO.get(f.get("tipo"), ("activo", 1))[0] == "activo")
        act_tot = sum(_f(f["importe"]) for f in fs if ING_POLO.get(f.get("tipo"), ("activo", 1))[0] == "activo")
        if h_tot > 0:
            ph_global = round((act_tot * 12.0) / (h_tot * 52.0), 1)
        return {
            "ingreso_mensual": round(total),
            "renta_pasiva": round(pasivo),
            "ratio_pasivo_calidad": round(100 * pasivo_cal / total),
            "concentracion_pct": round(100 * max(_f(f["importe"]) for f in fs) / total),
            "hhi": round(hhi, 3),
            "fuente_dominante": top.get("tipo"),
            "precio_hora_fuentes": ph,
            "precio_hora_global": ph_global,
        }
    except Exception:
        return {}


# ---------- GASTOS: fuga y rigidez ----------
def analizar_gastos(ancla, detalle):
    try:
        fs = [g for g in (detalle or []) if _f(g.get("importe")) > 0]
        suma = sum(_f(g["importe"]) for g in fs)
        rig = sum(_f(g["importe"]) for g in fs if GAS_POLO.get(g.get("tipo"), "discrecional") == "rigido")
        ancla = _f(ancla)
        gasto = max(ancla, suma)
        if gasto <= 0:
            return {}
        return {
            "gasto_mensual": round(gasto),
            "pct_gasto_fijo": round(100 * rig / suma) if suma > 0 else None,
            "fuga_no_consciente": round(max(0.0, ancla - suma)),
            "fuga_anual": round(max(0.0, ancla - suma) * 12),
        }
    except Exception:
        return {}


# ---------- DEUDA: esfuerzo, coste medio, avalancha ----------
def analizar_deuda(deudas, ingreso_mensual):
    try:
        ds = [d for d in (deudas or []) if _f(d.get("saldo")) > 0 or _f(d.get("cuota")) > 0]
        saldo = sum(_f(d.get("saldo")) for d in ds)
        cuota = sum(_f(d.get("cuota")) for d in ds)
        con_saldo = [d for d in ds if _f(d.get("saldo")) > 0]
        coste = (sum(_f(d["saldo"]) * DEU_TIER.get(d.get("tipo"), (9.0, "a"))[0] for d in con_saldo) / saldo) if saldo > 0 else 0.0
        cara = sum(_f(d["saldo"]) for d in con_saldo if DEU_TIER.get(d.get("tipo"), (9.0, "a"))[1] == "r")
        avalancha = None
        if con_saldo:
            top = max(con_saldo, key=lambda d: DEU_TIER.get(d.get("tipo"), (9.0, "a"))[0])
            avalancha = {"tipo": top.get("tipo"), "interes": DEU_TIER.get(top.get("tipo"), (9.0, "a"))[0]}
        ing = _f(ingreso_mensual)
        return {
            "deuda_total": round(saldo),
            "cuota_deuda": round(cuota),
            "coste_medio_deuda": round(coste, 1),
            "deuda_cara": round(cara),
            "esfuerzo_financiero": round(100 * cuota / ing) if ing > 0 else None,
            "avalancha": avalancha,
            "tiene_revolving": any(d.get("tipo") == "revolving" and _f(d.get("saldo")) > 0 for d in ds),
        }
    except Exception:
        return {}


# ---------- CARTERA: perfil implicito, cash drag, infraexposicion ----------
def analizar_cartera(cartera, gasto_mensual, horizonte, perfil_declarado):
    try:
        c = cartera or {}
        liq, rf, rv, alt = _f(c.get("liquidez")), _f(c.get("rf")), _f(c.get("rv")), _f(c.get("alt"))
        suma = liq + rf + rv + alt
        if suma <= 0:
            return {}
        rv_pct = round(100 * rv / suma)
        impl = "prud" if rv_pct < 20 else ("equi" if rv_pct < 55 else "agr")
        colchon = _f(gasto_mensual) * 6
        exceso = max(0.0, liq - colchon) if _f(gasto_mensual) > 0 else 0.0
        cash_drag = round(exceso * 0.025)
        infra = (_f(horizonte) >= 10 and rv_pct < 40)
        return {
            "inversiones_liquidas": round(suma),
            "pct_rv": rv_pct,
            "perfil_implicito": impl,
            "perfil_declarado": perfil_declarado,
            "mismatch_perfil": bool(perfil_declarado and perfil_declarado != impl),
            "cash_drag_anual": cash_drag,
            "infraexposicion_rv": infra,
        }
    except Exception:
        return {}


# ---------- PATRIMONIO: vivienda dormida, productivo vs muerto ----------
def analizar_patrimonio(vivienda, otros, hipoteca_vivienda, inversiones, deuda_total):
    try:
        viv = _f(vivienda)
        equity = max(0.0, viv - _f(hipoteca_vivienda))
        gross = viv + _f(otros) + _f(inversiones)
        neto = gross - _f(deuda_total)
        # base "tu parte": vivienda por equity, resto a mercado
        base = equity + _f(otros) + _f(inversiones)
        productivo = _f(inversiones) + _f(otros) * 0.5  # otros: mitad productivo (aprox)
        return {
            "patrimonio": round(neto),
            "activos_total": round(gross),
            "equity_vivienda": round(equity),
            "pct_productivo": round(100 * productivo / base) if base > 0 else None,
            "pct_vivienda": round(100 * equity / base) if base > 0 else None,
        }
    except Exception:
        return {}


# ---------- FAMILIA: proteccion, hitos ----------
def analizar_familia(edades):
    try:
        l = [int(_f(e)) for e in (edades or []) if _f(e) >= 0]
        if not l:
            return {"n_dependientes": 0}
        crianza = sum(max(0, INDEP - e) * COSTE_HIJO for e in l)
        prox_uni = min((UNIV - e for e in l if e < UNIV), default=None)
        libera = max((INDEP - e for e in l), default=0)
        return {
            "n_dependientes": len(l),
            "menores": sum(1 for e in l if e < UNIV),
            "proteccion_recomendada": round(crianza),
            "proximo_hito_uni_anios": prox_uni,
            "anio_libera_flujo": libera,
        }
    except Exception:
        return {"n_dependientes": 0}


# ---------- EXPECTATIVAS: numero neto de pension/herencia + 4 caminos ----------
def _fv(P, A, r, n):
    if r <= 0:
        return P + A * n
    g = (1 + r) ** n
    return P * g + A * (g - 1) / r


def analizar_expectativas(gasto_objetivo, pension, capital, ahorro_mensual, horizonte,
                          rent_real_pct, rent_esperada_pct=None, herencia_importe=0):
    try:
        go, pen, cap = _f(gasto_objetivo), _f(pension), _f(capital)
        aho, hor = _f(ahorro_mensual), _f(horizonte)
        rr = _f(rent_real_pct) / 100.0 / 12.0
        gp = max(0.0, go - pen)
        N = gp * 12 * 25
        # la herencia esperada reduce el capital que tienes que generar
        cap_efectivo = cap + _f(herencia_importe)
        falta = max(0.0, N - cap_efectivo)
        pct = min(100, round(100 * cap_efectivo / N)) if N > 0 else 100
        out = {"numero_libertad": round(N), "gasto_propio": round(gp),
               "pct_cubierto": pct, "brecha_renta": round(falta)}
        if go <= pen:
            out["pension_cubre"] = True
            return out
        # anos reales al ritmo actual
        nreal = None
        if N > cap_efectivo:
            for m in range(1, 12 * 80 + 1):
                if _fv(cap_efectivo, aho, rr, m) >= N:
                    nreal = round(m / 12.0); break
        else:
            nreal = 0
        out["anios_reales"] = nreal
        if rent_esperada_pct is not None:
            out["expectativa_magica"] = (_f(rent_esperada_pct) - _f(rent_real_pct) >= 3)
        # 4 caminos (si hay horizonte)
        if hor > 0 and rr >= 0:
            Hm = int(hor * 12)
            g = (1 + rr) ** Hm
            base = cap_efectivo * g
            a_need = 0.0 if base >= N else ((N - base) / Hm if rr <= 0 else (N - base) * rr / (g - 1))
            # rentabilidad necesaria (busqueda binaria)
            r_need = None
            lo, hi = 0.0, 0.30
            if _fv(cap_efectivo, aho, hi / 12.0, Hm) >= N:
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if _fv(cap_efectivo, aho, mid / 12.0, Hm) >= N:
                        hi = mid
                    else:
                        lo = mid
                r_need = round(hi * 100, 1)
            obj_cap = _fv(cap_efectivo, aho, rr, Hm)
            obj_vida = round(obj_cap / 25 / 12 + pen)
            obj_mid = min(go, round((go + obj_vida) / 2))
            N_mid = max(0.0, (obj_mid - pen)) * 12 * 25
            base_mid = cap_efectivo * g
            a_plan = 0.0 if base_mid >= N_mid else ((N_mid - base_mid) / Hm if rr <= 0 else (N_mid - base_mid) * rr / (g - 1))
            out["caminos"] = {
                "ahorro_necesario": round(a_need),
                "ahorro_extra": round(max(0.0, a_need - aho)),
                "rentabilidad_necesaria": r_need,
                "objetivo_alcanzable": obj_vida,
                "plan_recomendado": {"ahorro": round(a_plan), "extra": round(max(0.0, a_plan - aho)),
                                     "objetivo": obj_mid, "ya_llega": obj_vida >= go},
            }
        return out
    except Exception:
        return {}


# ---------- AGREGADOR: salud global con renormalizacion + alertas ----------
_PESOS = {"ingresos": 0.20, "gastos": 0.22, "deuda": 0.22, "cartera": 0.18, "patrimonio": 0.18}


def _clamp(x, lo=5, hi=95):
    return max(lo, min(hi, round(x)))


def agregar(ing, gas, deu, car, pat, fam, exp, gateway):
    """Compone la salud global (renormalizada) y las 3 alertas prioritarias."""
    try:
        gw = gateway or {}
        dims = {}
        if ing.get("ingreso_mensual"):
            pas = ing.get("ratio_pasivo_calidad", 0)
            conc = ing.get("concentracion_pct", 100)
            dims["ingresos"] = _clamp(55 + pas * 0.45 - (20 if conc > 85 else 0))
        if gas.get("gasto_mensual") and ing.get("ingreso_mensual"):
            tasa = (ing["ingreso_mensual"] - gas["gasto_mensual"]) / ing["ingreso_mensual"]
            dims["gastos"] = _clamp(50 + tasa * 120 - (12 if (gas.get("fuga_no_consciente") or 0) > 150 else 0))
        if gw.get("deudas") is False:
            dims["deuda"] = 92
        elif gw.get("deudas"):
            esf = deu.get("esfuerzo_financiero") or 0
            dims["deuda"] = 90 if (deu.get("deuda_total") or 0) == 0 else _clamp(90 - esf * 1.5 - (15 if (deu.get("coste_medio_deuda") or 0) > 10 else 0))
        if gw.get("ahorros"):
            cd = 12 if (car.get("cash_drag_anual") or 0) > 100 else 0
            dims["cartera"] = _clamp(48 + (car.get("pct_rv") or 0) * 0.35 - cd)
        if pat.get("pct_productivo") is not None:
            dims["patrimonio"] = _clamp(pat["pct_productivo"])
        num = den = 0.0
        for k, w in _PESOS.items():
            if dims.get(k) is not None:
                num += dims[k] * w; den += w
        if den > 0:
            g = round(num / den)
            banda = "Solido" if g >= 70 else ("Con margen" if g >= 50 else ("Sobrecarga" if g >= 38 else "Critico"))
        else:
            g = 0; banda = "Datos insuficientes"  # envio sin datos: no etiquetar como Critico

        # ---- alertas (severidad 3>2>1) ----
        A = []
        if (pat.get("patrimonio") or 0) < 0 and (pat.get("activos_total") or 0) > 0:
            A.append((3, "Patrimonio neto negativo", "Debes mas de lo que tienes: prioridad nº1, reducir deuda."))
        if deu.get("tiene_revolving"):
            A.append((3, "Tarjeta revolving", "El credito mas caro que existe. Amortizarla es la mejor inversion posible."))
        if (deu.get("esfuerzo_financiero") or 0) >= 35:
            A.append((3, "Esfuerzo de deuda alto", "Mas del 35%% de tu ingreso se va en cuotas: vives sin aire."))
        if gw.get("hijos") and fam.get("proteccion_recomendada", 0) > 0:
            A.append((3, "Familia sin proteccion clara", "Hay un sosten pendiente para los tuyos. Conviene cubrirlo a tiempo."))
        if (pat.get("pct_vivienda") or 0) >= 70:
            A.append((2, "Patrimonio dormido en la vivienda", "La mayor parte de tu patrimonio no renta ni es liquido."))
        if (gas.get("fuga_no_consciente") or 0) >= 150:
            A.append((2, "Fuga no consciente", "Se te va dinero cada mes sin saber en que: gasto hormiga."))
        if (ing.get("concentracion_pct") or 0) >= 80:
            A.append((2, "Ingresos concentrados", "Casi todo depende de una sola fuente: tu riesgo mas subestimado."))
        if exp.get("expectativa_magica"):
            A.append((2, "Expectativa de rentabilidad magica", "Esperas mas de lo que tu perfil aguanta."))
        if (car.get("cash_drag_anual") or 0) >= 300:
            A.append((1, "Liquidez ociosa", "Dinero parado perdiendo contra la inflacion."))
        if car.get("infraexposicion_rv"):
            A.append((1, "Infraexposicion a bolsa", "Plazo largo y poca renta variable: coste de oportunidad."))
        A.sort(key=lambda x: -x[0])
        alertas = [{"severidad": s, "titulo": t, "detalle": d} for s, t, d in A[:3]]
        return {"salud_global": g, "banda": banda, "dimensiones": dims, "alertas": alertas}
    except Exception:
        return {"salud_global": 0, "banda": "—", "dimensiones": {}, "alertas": []}


def construir_payload_narrativo(agregado, perfil_riesgo=None):
    """Veredicto ya cocinado para la API: el narrador decide QUE; la IA solo COMO."""
    return {
        "system": ("Eres Adapta Family Office. Escribe el informe en segunda persona, cercano y directo, "
                   "con rigor de banca privada y calidez. NO inventes cifras: usa solo las del veredicto. "
                   "Respeta el orden de prioridad de las alertas."),
        "veredicto": {
            "salud_global": agregado.get("salud_global"),
            "banda": agregado.get("banda"),
            "dimensiones": agregado.get("dimensiones"),
            "perfil_riesgo": perfil_riesgo,
            "alertas": agregado.get("alertas"),
        },
    }


if __name__ == "__main__":
    # humo basico (cuando el sandbox sincronice se ejecuta y valida)
    ing = analizar_ingresos([{"tipo": "nomina", "importe": 2500, "horas": 45},
                             {"tipo": "alquiler", "importe": 400, "horas": 0}])
    gas = analizar_gastos(2000, [{"tipo": "vivienda", "importe": 800}, {"tipo": "ocio", "importe": 300}])
    deu = analizar_deuda([{"tipo": "revolving", "saldo": 4000, "cuota": 180}], ing.get("ingreso_mensual"))
    car = analizar_cartera({"liquidez": 30000, "rv": 5000}, gas.get("gasto_mensual"), 20, "agr")
    pat = analizar_patrimonio(300000, 0, 200000, car.get("inversiones_liquidas", 0), deu.get("deuda_total", 0))
    fam = analizar_familia([4, 16])
    exp = analizar_expectativas(3000, 1100, car.get("inversiones_liquidas", 0), 200, 15, 5.5, 8, 0)
    ag = agregar(ing, gas, deu, car, pat, fam, exp, {"deudas": True, "ahorros": True, "hijos": True})
    print("ingresos:", ing)
    print("expectativas:", exp.get("caminos"))
    print("agregado:", ag)
