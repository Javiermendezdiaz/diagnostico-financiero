# Auditoría de informes Adapta · Las 6 lentes
**Antes de enviar cualquier diagnóstico a un cliente.** 20 minutos. El humano se cansa en la página 40; esta checklist no.

> El 90% de los fallos viven en **las costuras**: entre dos páginas, entre el dato y la emoción, entre lo que el informe dice y lo que calla. Por eso no se ven leyendo de corrido. Se ven leyendo **en cruz**.

---

## Lente 1 · CRUCE — ¿esta cifra aparece igual en todos los sitios?
Mecánica pura. No hace falta saber de finanzas, solo comparar.

- [ ] Lista las cifras clave (número de libertad, colchón, valor hora, líquido, patrimonio neto, tasa de ahorro).
- [ ] Busca cada una en TODO el documento. *Toda cifra que aparece dos veces debe ser idéntica.*
- [ ] Bandera roja: el mismo concepto con dos valores → fallo seguro.

*Pillaría:* número de libertad 750k / 75k / 540k · colchón 3 / 6 / 11 meses · hora 9 / 10 / 12 €.

## Lente 2 · IDENTIDAD — ¿puedo reconstruir el número con una calculadora?
Cada cifra derivada sale de una cuenta. Si no, está mal o es inventada.

- [ ] Número de libertad = gasto anual × 25. ¿Cuadra?
- [ ] Patrimonio neto = activos − deudas. ¿Cuadra?
- [ ] Coge cada cifra "estimada" y pregunta: *¿de qué respuesta del cuestionario sale?* Si de ninguna → inventada, fuera.

*Pillaría:* el "75k", el donut que pierde 9.000 €, el gap de pensión de 1.400 € que nadie preguntó.

## Lente 3 · DATO vs PERCEPCIÓN — ¿es un hecho o un sentimiento?
El hallazgo más valioso de Adapta vive aquí.

- [ ] Subraya cada *hecho* (colchón en meses, DTI, patrimonio) en un color.
- [ ] Subraya cada *sentimiento* ("aguantaría poco", "me asfixia") en otro.
- [ ] Busca el mismo tema con un hecho Y un sentimiento que **apunten en direcciones opuestas**.
- [ ] Cuando diverjan: NO es un bug. Es el diagnóstico estrella → **nómbralo**: "objetivamente X, pero lo vives como Y; ahí está el verdadero trabajo."

*Pillaría:* colchón sano + pánico · DTI bajo + "me asfixia" · "no estás desprotegido" + "resistencia crítica". El problema de Benito no es su dinero, es su confianza en él.

## Lente 4 · AFIRMAR Y NEGAR — ¿el informe se desmiente a sí mismo?
Caza los juicios contradictorios sobre la misma cosa.

- [ ] Subraya los adjetivos de juicio: equilibrado, sano, crítico, bajo control, expuesto, funciona.
- [ ] Por cada uno, busca la *misma cosa* descrita en otra página.
- [ ] Bandera roja: dos juicios opuestos sobre el mismo dato.

*Pillaría:* "apalancamiento equilibrado" (p48) vs "esa deuda es lo primero a eliminar" (p49) · "tu estructura funciona" vs "tu ahorro es insuficiente".

## Lente 5 · LECTOR HOSTIL — ¿qué preguntaría quien quiere pillarme?
Imagina a tu cliente más exigente: un estadístico, un abogado, un médico.

- [ ] "¿Contra cuántas personas calculáis mi percentil?" → si la respuesta hunde la cifra, quítala o etiquétala "provisional".
- [ ] "¿Por qué usáis la regla americana del 4% en España, con mi fiscalidad?" → si no hay respuesta, error técnico.
- [ ] "¿Esta proyección es en euros de hoy o de 2046?" → si el informe mezcla, ninguna es comparable.
- [ ] El lector hostil encuentra lo que el lector amable perdona.

## Lente 6 · AUSENCIA — ¿qué debería estar y no está?
La más difícil: buscas lo que NO ves. Pregúntate qué incluiría un experto.

- [ ] ¿Índice navegable en un documento largo?
- [ ] ¿El informe "exclusivo para ti" sabe tu edad, tu familia, tu vivienda?
- [ ] ¿Prueba social (reseñas, libros) en el momento de máxima tensión?
- [ ] ¿Una acción que el cliente pueda completar HOY, en 10 minutos, sin Adapta?
- [ ] ¿Fecha de caducidad y versión del modelo?

---

## Regla de oro
Lee **en cruz, no en línea**. Salta entre páginas que hablan de lo mismo y compáralas. Cada página parece bien en sí misma; el fallo solo aparece al cruzarlas.

## Lo que NO depende de esta checklist
Las lentes **1, 2 y 4** ya están automatizadas en el motor (`qa_coherencia.py` — el guardián de coherencia — y el gate en `app.py`): corren solas en cada informe antes de imprimir, en modo aviso-por-log. Esta hoja es para lo que aún necesita ojo humano: **lentes 3, 5 y 6** — el criterio, lo hostil y lo ausente. Eso, de momento, no lo hace una máquina.

*Adapta Family Office — uso interno. Hablar de dinero es de buena educación.*
