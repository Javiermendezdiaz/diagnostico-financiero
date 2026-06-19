# -*- coding: utf-8 -*-
"""ITAP — Síntesis narrativa con IA (Claude) de las preguntas abiertas.

Modelo híbrido: las preguntas CERRADAS alimentan el scoring determinista (radar,
percentiles, baremos); estas funciones leen las pocas respuestas ABIERTAS del
cliente y devuelven un retrato en prosa para inyectar en el PDF.

Diseño a prueba de fallos: si no hay ANTHROPIC_API_KEY, no hay respuestas con
texto, o la API falla por cualquier motivo, las funciones devuelven None y el
informe se genera con normalidad SIN la sección de IA. Nunca lanzan excepción.
"""
import os, re

MODELO = os.environ.get("ITAP_AI_MODEL", "claude-opus-4-8")
MAX_TOKENS = int(os.environ.get("ITAP_AI_MAX_TOKENS", "750"))

_GUARDRAIL = (
    "Eres un socio sénior de un family office suizo y psicólogo patrimonial. Escribes con autoridad clínica, "
    "incisiva y sofisticada: nombras con precisión el mecanismo de defensa, el sesgo cognitivo o la disonancia "
    "que delata el cliente, y lo conectas con su coste real —de oportunidad, de tranquilidad, de tiempo—. "
    "Reglas innegociables: "
    "(1) usa SIEMPRE las palabras del cliente, citándolo, y desmonta la racionalización que esconden; "
    "(2) cruza lo que SIENTE (sus textos) con lo que MIDEN sus números, exponiendo coherencias y disonancias; "
    "(3) PROHIBIDO inventar cifras, porcentajes o datos que no se te hayan dado; "
    "(4) PROHIBIDOS los clichés de autoayuda o de finanzas modernas ('sana tu relación con el dinero', "
    "'es importante que...', 'recuerda que...', 'el primer paso es...'): hablas como un diagnóstico, no como un coach; "
    "(5) eres implacable con el PATRÓN, nunca cruel con la PERSONA: si el cliente revela un dolor real, trátalo con "
    "seriedad clínica, sin frialdad ni dramatismo gratuito; "
    "(6) cierras con una sola observación o pregunta quirúrgica, no con una lista ni con consuelo de manual. "
    "Español de España, segunda persona (tú). Registro de referencia (NO lo copies, solo calibra el nivel): "
    "«Racionalizas el estancamiento de tu capital como prudencia; es, en realidad, una parálisis por aversión "
    "a la pérdida que cada año te cuesta en coste de oportunidad lo que no te atreves a mirar.»"
)


def _texto_abiertas(abiertas):
    """abiertas: dict {pregunta: respuesta}. Devuelve bloque legible o '' si vacío."""
    if not abiertas:
        return ""
    bloques = []
    for q, r in abiertas.items():
        if r and str(r).strip():
            bloques.append("P: %s\nR: %s" % (str(q).strip(), str(r).strip()))
    return "\n\n".join(bloques)


def _client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except Exception:
        return None


def _extraer(texto, tag):
    m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), texto, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None


def sintetizar_individual(abiertas, contexto=None):
    """Devuelve {'retrato': str} o None. contexto: dict opcional con salud, focos, arquetipo, cohorte."""
    bloque = _texto_abiertas(abiertas)
    if not bloque:
        return None
    cli = _client()
    if cli is None:
        return None
    ctx = contexto or {}
    metr = []
    if ctx.get("salud") is not None: metr.append("Salud psicofinanciera global: %s/100 (0=sano, 100=disfunción)." % ctx["salud"])
    if ctx.get("arquetipo"): metr.append("Arquetipo del dinero: %s." % ctx["arquetipo"])
    if ctx.get("focos"): metr.append("Capas más tensionadas: %s." % ", ".join(ctx["focos"]))
    if ctx.get("cohorte"): metr.append("Perfil: %s." % ctx["cohorte"])
    metr_txt = "\n".join(metr) if metr else "(sin métricas adicionales)"
    user = (
        "<metricas_del_cliente>\n%s\n</metricas_del_cliente>\n\n"
        "<respuestas_abiertas_del_cliente>\n%s\n</respuestas_abiertas_del_cliente>\n\n"
        "Redacta el apartado del informe titulado «Tu retrato, en tus palabras»: un texto de 150 a 220 "
        "palabras que reinterprete lo que el cliente ha escrito, lo conecte con sus métricas y le devuelva "
        "una lectura honesta y precisa de su relación con el dinero. Tono de estratega patrimonial: "
        "directo y empático, nunca burlón ni condescendiente; no te rías de cómo escribe ni de sus palabras "
        "—interpreta lo que revelan, no las ridiculices. No uses markdown ni asteriscos, escribe en prosa limpia. "
        "Devuélvelo entre etiquetas <retrato>...</retrato>, sin nada más fuera de ellas." % (metr_txt, bloque)
    )
    try:
        msg = cli.messages.create(model=MODELO, max_tokens=MAX_TOKENS,
                                  system=_GUARDRAIL, messages=[{"role": "user", "content": user}])
        out = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        retrato = _extraer(out, "retrato") or out.strip()
        return {"retrato": retrato} if retrato else None
    except Exception:
        return None


def sintetizar_pareja(abiertas_a, abiertas_b, nombres=None, contexto=None):
    """Cruza las abiertas de ambos miembros. Devuelve {'friccion': str} o None."""
    ba = _texto_abiertas(abiertas_a)
    bb = _texto_abiertas(abiertas_b)
    if not ba and not bb:
        return None
    cli = _client()
    if cli is None:
        return None
    nA = (nombres or {}).get("a") or "Persona A"
    nB = (nombres or {}).get("b") or "Persona B"
    ctx = contexto or {}
    extra = ("Compatibilidad estimada por scoring: %s." % ctx["compat"]) if ctx.get("compat") else ""
    user = (
        "<respuestas_de_%s>\n%s\n</respuestas_de_%s>\n\n"
        "<respuestas_de_%s>\n%s\n</respuestas_de_%s>\n\n%s\n\n"
        "Analiza el cruce semántico de ambos textos: dónde sus relatos coinciden, dónde chocan, y qué "
        "fricción silenciosa por dinero revelan (reproches latentes, asimetría de ambición o de miedo, "
        "conversaciones evitadas). Si uno describe el miedo del otro, contrástalo con lo que el otro dijo de sí mismo. "
        "Redacta el apartado «Dónde está vuestra fricción real» en 180 a 250 palabras, honesto y sin dramatizar. "
        "Devuélvelo entre etiquetas <friccion>...</friccion>, sin nada más fuera." % (nA, ba or "(sin respuestas)", nA, nB, bb or "(sin respuestas)", nB, extra)
    )
    try:
        msg = cli.messages.create(model=MODELO, max_tokens=MAX_TOKENS + 150,
                                  system=_GUARDRAIL, messages=[{"role": "user", "content": user}])
        out = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        fric = _extraer(out, "friccion") or out.strip()
        return {"friccion": fric} if fric else None
    except Exception:
        return None


if __name__ == "__main__":
    # Smoke test de la lógica sin clave (debe devolver None limpiamente)
    print("sin clave/sin texto ->", sintetizar_individual({}))
    print("parser <retrato> ->", _extraer("ruido <retrato>Texto de prueba.</retrato> ruido", "retrato"))
