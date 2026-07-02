# -*- coding: utf-8 -*-
"""Motor de los 16 Arquetipos del Dinero — Adapta Family Office.

Cuatro ejes binarios -> codigo de 4 letras -> 1 de 16 arquetipos.
  Eje 1 Riesgo:    S Seguridad  / A Audacia
  Eje 2 Tiempo:    P Presente   / L Legado
  Eje 3 Decision:  M Metodo     / I Instinto
  Eje 4 Esfera:    O Solo       / T Tribu

Aislado y sin dependencias del resto del motor. Degradado seguro.
"""

# --- 8 preguntas de eje (eleccion directa entre los dos polos) ---
# Cada opcion lleva su polo. 2 preguntas por eje; el orden de opciones se baraja en cliente.
AXIS_Q = [
    {"id": "AX1-1", "eje": 1, "texto": "El dinero que no necesitas ahora mismo, ¿qué prefieres?",
     "opciones": [{"texto": "Que esté a salvo, aunque crezca despacio.", "polo": "S"},
                  {"texto": "Que crezca de verdad, aunque dé algún susto.", "polo": "A"}]},
    {"id": "AX2-1", "eje": 2, "texto": "Te cae un dinero extra inesperado. ¿Qué te pide el cuerpo?",
     "opciones": [{"texto": "Dártelo: un gusto, un viaje, vivirlo.", "polo": "P"},
                  {"texto": "Ponerlo a trabajar para el mañana.", "polo": "L"}]},
    {"id": "AX3-1", "eje": 3, "texto": "Una decisión de dinero importante. ¿De qué te fías más?",
     "opciones": [{"texto": "De los números y un plan.", "polo": "M"},
                  {"texto": "De mi olfato y mi experiencia.", "polo": "I"}]},
    {"id": "AX4-1", "eje": 4, "texto": "Las decisiones sobre tu dinero, prefieres…",
     "opciones": [{"texto": "Tomarlas por tu cuenta, a tu ritmo.", "polo": "O"},
                  {"texto": "Tomarlas en equipo, con los tuyos.", "polo": "T"}]},
    {"id": "AX1-2", "eje": 1, "texto": "El mercado cae con fuerza de golpe. Tu primer impulso:",
     "opciones": [{"texto": "Poner a salvo lo que queda.", "polo": "S"},
                  {"texto": "Buscar qué se ha puesto barato.", "polo": "A"}]},
    {"id": "AX2-2", "eje": 2, "texto": "Cuando piensas en tu dinero, ¿qué pesa más?",
     "opciones": [{"texto": "Vivir bien el presente.", "polo": "P"},
                  {"texto": "Construir para el futuro.", "polo": "L"}]},
    {"id": "AX3-2", "eje": 3, "texto": "Tus cuentas, ¿cómo las llevas?",
     "opciones": [{"texto": "Con orden: las reviso y las controlo.", "polo": "M"},
                  {"texto": "A grandes rasgos; ya sé por dónde voy.", "polo": "I"}]},
    {"id": "AX4-2", "eje": 4, "texto": "Lo que más valoras que te dé el dinero:",
     "opciones": [{"texto": "Tu independencia y tu libertad.", "polo": "O"},
                  {"texto": "Tranquilidad para los tuyos y para ti.", "polo": "T"}]},
    {"id": "AX1-3", "eje": 1, "texto": "Una oportunidad con buen potencial, pero que puede bajar bastante:",
     "opciones": [{"texto": "Entro: quien no arriesga, no gana.", "polo": "A"},
                  {"texto": "Paso: duermo mejor sin sobresaltos.", "polo": "S"}]},
    {"id": "AX2-3", "eje": 2, "texto": "Tu idea de hacerlo bien con el dinero es…",
     "opciones": [{"texto": "Disfrutar el camino, no solo la meta.", "polo": "P"},
                  {"texto": "Dejar algo que perdure.", "polo": "L"}]},
    {"id": "AX3-3", "eje": 3, "texto": "Ante una oportunidad, sueles decidir…",
     "opciones": [{"texto": "Rápido: si lo siento, voy.", "polo": "I"},
                  {"texto": "Con calma: primero lo analizo.", "polo": "M"}]},
    {"id": "AX4-3", "eje": 4, "texto": "Cuando ganas o pierdes con el dinero, lo vives…",
     "opciones": [{"texto": "Como algo tuyo, personal.", "polo": "O"},
                  {"texto": "Como algo del grupo, compartido.", "polo": "T"}]}
]

# Polo por defecto si un eje queda empatado (1-1): el mas comun/conservador.
_DEFAULT = {1: "S", 2: "L", 3: "M", 4: "T"}
_OPP = {"S": "A", "A": "S", "P": "L", "L": "P", "M": "I", "I": "M", "O": "T", "T": "O"}

# --- Los 16 arquetipos ---
ARQ16 = {
 "SPMO": {"n": "El Centinela", "lema": "Vigilo lo mío, sin sobresaltos.", "color": "#0E8A6E",
          "luz": "Orden y serenidad; nada se te escapa.", "sombra": "Dinero parado por miedo a moverlo."},
 "SPMT": {"n": "El Guardián", "lema": "Protejo a los míos, con un plan.", "color": "#12A085",
          "luz": "Red de seguridad para tu familia.", "sombra": "Cargas tú solo con toda la tensión."},
 "SPIO": {"n": "El Prudente", "lema": "Voy a lo seguro, a mi manera.", "color": "#2E8B57",
          "luz": "Instinto de conservación afinado.", "sombra": "Decides sin mirar los números."},
 "SPIT": {"n": "El Anfitrión", "lema": "Disfruto la vida, y la comparto.", "color": "#15B79E",
          "luz": "Sabes celebrar y cuidar a los tuyos hoy.", "sombra": "Poco colchón para el mañana."},
 "SLMO": {"n": "El Estratega", "lema": "Construyo despacio y seguro.", "color": "#1E5BA8",
          "luz": "Paciencia y estructura impecables.", "sombra": "Exceso de control; rigidez."},
 "SLMT": {"n": "El Patriarca", "lema": "Dejo un legado blindado.", "color": "#2563EB",
          "luz": "Proteges a varias generaciones.", "sombra": "Controlas demasiado a los tuyos."},
 "SLIO": {"n": "El Previsor", "lema": "Guardo para mañana, por si acaso.", "color": "#0284C7",
          "luz": "Disciplina de ahorro envidiable.", "sombra": "Te privas más de lo necesario."},
 "SLIT": {"n": "El Protector", "lema": "Mi futuro es el de los míos.", "color": "#3B5BA5",
          "luz": "Generosidad previsora con los tuyos.", "sombra": "Descuidas lo tuyo por los demás."},
 "APMO": {"n": "El Cazador", "lema": "Arriesgo, pero con cabeza y hoy.", "color": "#C2410C",
          "luz": "Oportunismo calculado, sangre fría.", "sombra": "El riesgo puede volverse adicción."},
 "APMT": {"n": "El Emprendedor", "lema": "Construyo ahora, con mi gente.", "color": "#E0701A",
          "luz": "Energía y red que mueven proyectos.", "sombra": "Quemas la caja por crecer rápido."},
 "APIO": {"n": "El Aventurero", "lema": "Me lanzo, ya veré.", "color": "#DC2626",
          "luz": "Valentía pura; no te paraliza el miedo.", "sombra": "Impulsividad sin red de seguridad."},
 "APIT": {"n": "El Magnético", "lema": "La vida es ahora, y en grande.", "color": "#EA580C",
          "luz": "Carisma; arrastras a la gente.", "sombra": "Apariencia y deuda para sostenerla."},
 "ALMO": {"n": "El Arquitecto", "lema": "Convierto recursos en más recursos.", "color": "#7C3AED",
          "luz": "Visión de largo plazo + ejecución.", "sombra": "Workaholic; el plan te come la vida."},
 "ALMT": {"n": "El Magnate", "lema": "Construyo algo que dure, con los míos.", "color": "#6D28D9",
          "luz": "Liderazgo patrimonial de raza.", "sombra": "El dinero por encima de todo."},
 "ALIO": {"n": "El Pionero", "lema": "Veo lo que otros no, y voy.", "color": "#8B5CF6",
          "luz": "Intuición visionaria; abres caminos.", "sombra": "Apuestas grandes sin cobertura."},
 "ALIT": {"n": "El Visionario", "lema": "Inspiro y construyo el mañana.", "color": "#5B21B6",
          "luz": "Inspiras a otros a soñar en grande.", "sombra": "Sueños sin números que los sostengan."},
}

# Etiquetas legibles de cada polo (para el informe / la tarjeta)
POLO_NOMBRE = {"S": "Seguridad", "A": "Audacia", "P": "Presente", "L": "Legado",
               "M": "Método", "I": "Instinto", "O": "Solo", "T": "Tribu"}


def arquetipo16(respuestas):
    """respuestas: dict {AX..: polo_elegido}. Devuelve (codigo, meta) o (None, None).
    Cada eje: mayoria de sus 2 polos; empate -> default. Blindado: nunca lanza."""
    try:
        tally = {1: {}, 2: {}, 3: {}, 4: {}}
        for q in AXIS_Q:
            p = (respuestas or {}).get(q["id"])
            if p in ("S", "A", "P", "L", "M", "I", "O", "T"):
                tally[q["eje"]][p] = tally[q["eje"]].get(p, 0) + 1
        code = ""
        for eje in (1, 2, 3, 4):
            t = tally[eje]
            if not t:
                code += _DEFAULT[eje]
            else:
                a = max(t, key=t.get)
                b_others = [k for k in t if k != a and t[k] == t[a]]
                code += _DEFAULT[eje] if b_others else a   # empate -> default
        if code not in ARQ16:
            return (None, None)
        return (code, ARQ16[code])
    except Exception:
        return (None, None)


def desglose(codigo):
    """Devuelve los 4 polos legibles de un codigo, p.ej. 'A·L·M·O' -> lista de (eje, nombre)."""
    try:
        return [POLO_NOMBRE.get(c, c) for c in codigo]
    except Exception:
        return []


if __name__ == "__main__":
    # Verificacion: las 16 combinaciones deben resolver a su tipo, con nombre.
    import itertools
    faltan = []
    for combo in itertools.product("SA", "PL", "MI", "OT"):
        code = "".join(combo)
        # construir respuestas que fuercen ese codigo (2 votos por polo)
        resp = {}
        for q in AXIS_Q:
            polo_eje = code[q["eje"] - 1]
            # marcar la opcion cuyo polo coincide
            resp[q["id"]] = polo_eje
        got, meta = arquetipo16(resp)
        ok = (got == code and meta)
        if not ok:
            faltan.append(code)
        print("%-4s -> %-4s  %s" % (code, got, meta["n"] if meta else "??"))
    print("\nTotal tipos:", len(ARQ16), "| fallos:", faltan or "NINGUNO")
    # empate
    e = {"AX1-1": "S", "AX1-2": "A", "AX2-1": "P", "AX2-2": "P", "AX3-1": "M", "AX3-2": "M", "AX4-1": "O", "AX4-2": "O"}
    print("Empate eje1 (S vs A) ->", arquetipo16(e)[0], "(default S esperado en eje1)")
