# Constitución del Diagnóstico Adapta
### La voz única que gobierna el motor, el prompt y la plantilla · modelo v2.1

> Un informe pierde autoridad cuando tiene varios autores invisibles que no se hablan. Esta constitución es el árbitro: cuando dos partes del sistema chocan, aquí se decide quién gana. El motor, la narrativa y la maqueta **se someten a ella**. No es una guía de estilo: es la cadena de mando de la verdad.

---

## Artículo 1 · La jerarquía de la verdad
Cuando dos afirmaciones del informe chocan, este es el orden de quién manda.

1. **El dato objetivo manda sobre la percepción.** Si el colchón cubre 11 meses, el cliente está protegido. La percepción ("no aguanto") no rebaja el hecho: lo acompaña como hallazgo separado (Art. 4). Ninguna página declara "crítico" lo que el dato declara "sano" sin nombrar la divergencia.
2. **El cálculo canónico manda sobre cualquier narrativa.** Toda cifra nace una sola vez en el motor (`score_v2.py`). La narrativa **cita**, nunca recalcula. Si el texto y el motor difieren, gana el motor.
3. **El diagnóstico manda sobre la venta.** La recomendación de servicio se deriva del estado real del cliente, no al revés. Si lo que conviene es no contratar, eso se dice.

## Artículo 2 · Una cifra, un dueño
- Cada número tiene **un único punto de cálculo** (`score_v2.computar_extras`) y se propaga; ninguna página lo reconstruye.
- **Toda cifra que aparece dos veces es idéntica**, mismo redondeo, misma unidad.
- Lo que no nace del motor, no se escribe.

## Artículo 3 · Un solo marco, declarado en voz alta
El informe declara, una vez y de forma visible, sus reglas de medición:
- **Escenario:** se planifica sobre la **vida ideal declarada** (`numero_canonico`), no el gasto actual.
- **Unidad temporal:** todas las proyecciones en **euros de hoy**; lo nominal se etiqueta.
- **Colchón objetivo:** **6 meses** de gasto. Una sola definición.
- **Regla de retiro:** **4% = regla 25×** (ajustada por fiscalidad ES, ver `numero_neto_es`).
- **Base horaria:** una sola.

## Artículo 4 · Dato y percepción nunca se pisan — se nombran juntos
Cada área con un hecho Y un sentimiento (colchón, deuda, resistencia) se presenta en dos capas; cuando **divergen**, el informe lo nombra como el hallazgo que es:
> "Tu dinero está mejor que tu cabeza. Tienes 11 meses de colchón — mejor que la mayoría — pero lo vives como si no aguantaras nada. Tu trabajo no es ahorrar más: es confiar en lo que ya has construido."

## Artículo 5 · Honestidad calibrada
1. **Lo medido se separa de lo inferido**; cada inferencia lleva su supuesto.
2. **Lo que no se sabe, se admite**: sin muestra, no hay percentil (provisional); lo no preguntado no se estima como hecho.
3. **Al menos una recomendación que no nos beneficia** ("esto puedes hacerlo tú solo").

## Artículo 6 · El cuidado de la persona está por encima del gancho comercial
- Para perfiles con malestar declarado, el tono no es catastrofista: firmeza es claridad, no miedo.
- La venta no se repite tres veces seguidas. Un gancho, en el momento justo.
- La nota de cuidado se respeta con el tono de todo el documento, no solo en la letra pequeña.

## Artículo 7 · El informe es una foto fechada, no una sentencia
- Cada informe lleva **fecha de validez y versión** ("válido a fecha X · modelo v2.1 · recalcular en 6 meses").
- Se guarda el snapshot de `facts` con timestamp para que el siguiente diagnóstico diga "esto es lo que has movido".
- El número de libertad irreal a ritmo actual se **contextualiza**: solo se alcanza cambiando de fase de ingresos.

---

## Cómo se aplica — y qué está YA vivo (modelo v2.1)

| Capa | Se somete a | Verificado por | Estado |
|------|-------------|----------------|--------|
| Motor de scoring | Art. 2, 3, 5 | `qa_coherencia.py` (guardián) | ✅ desplegado |
| Número canónico + marco | Art. 2, 3 | `score_v2.calcular_brecha` (`numero_canonico`, `numero_neto_es`) | ✅ desplegado |
| Dato vs percepción | Art. 4 | `score_v2.detectar_paradoja` + `seccion_paradoja` | ✅ desplegado |
| Anti-alucinación narrativa | Art. 1.2, 5 | `ai_sintesis` (guardrail + defensa de citas) | ✅ desplegado |
| Selección de servicio | Art. 1.3 | `seccion_adapta` (upsell por patrimonio) | ✅ desplegado |
| Sello de versión | Art. 7 | nota metodológica `report_book` | ✅ desplegado |
| Percentil provisional | Art. 5.2 | nota metodológica | ✅ desplegado |
| **Tono / cuidado** | **Art. 6** | revisión + prompt | ⏳ pendiente (decisión: "cliente primero") |
| **Caja "Cómo medimos"** | **Art. 3** | plantilla | ⏳ pendiente |
| **Snapshot temporal de facts** | **Art. 7** | persistencia | ⏳ pendiente |
| **"Esto puedes hacerlo tú solo"** | **Art. 5.3** | narrativa | ⏳ pendiente |

> Cuando alguien en Adapta dude de si una frase, una cifra o una oferta "encaja", la pregunta no es de gusto: es **"¿qué artículo de la constitución aplica aquí?"**. Esa es la voz única que faltaba.

*Adapta Family Office · documento de gobierno · hablar de dinero es de buena educación.*
