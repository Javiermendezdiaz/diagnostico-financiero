# Rediseño del cuestionario ITAP · auditoría accionable
### Objetivo: rigor, orden y cero redundancia. Cada dato se pregunta UNA vez.

> Regla maestra (de la Constitución, Art. 2): **una cifra, un dueño**. Un total no se pregunta si se puede derivar de sus partes. Una percepción y su dato pueden coexistir (es la paradoja), pero dos preguntas que miden *lo mismo* se fusionan.

---

## A · DEDUPLICACIÓN (lo que sobra)

### A1 · Totales que deben derivarse, no preguntarse
| Se pregunta hoy | Solapa con | Decisión |
|---|---|---|
| `ingreso_mensual` (total) | `ing_trabajo + ing_inversion + ing_alquiler + ing_otros` | **Derivar el total de las partes.** Si el cliente desglosa fuentes, `ingreso_mensual = Σ fuentes` (no se vuelve a preguntar). |
| `horas_semana` (total) | `h_trabajo + h_inversion + h_alquiler + h_otros` | **Derivar.** Elimina el bug del "valor hora ×4": una sola base horaria = Σ horas por fuente. |
| `renta_pasiva` (total) | `ing_inversion + ing_alquiler + ing_otros` (las pasivas) | **Derivar.** La renta pasiva es la suma de las fuentes no-trabajo. |

> **Impacto técnico (lockstep obligatorio):** estos tres campos los consumen `score_v2.calcular_fuentes`, `motor_financiero_v3.analizar_ingresos` y el teaser de `app.py`. La poda **no se despliega sin** actualizar esos consumidores para que lean el derivado. *Por eso no se toca a ciegas — se hace en una pasada verificada con render E2E.*

### A2 · Facetas duplicadas (mismo concepto en dos capas)
| Duplicado | Capas | Decisión |
|---|---|---|
| `plan_b` / `plan_b_crisis` | C7 / C3 | Conservar **una**: el plan B de ingresos vive en C7; C3 mide solo el colchón. |
| `comparacion` / `comparacion_circulo` | C1 / C6 | Fusionar en C6 (estatus); C1 mide ansiedad, no comparación. |
| `diversificacion` / `diversificacion_cartera` | C2 / C12 | Conservar en C12 (cartera); C2 se queda con "número y plan". |
| `trayectoria` (mismo nombre) | C2 y C10 | Renombrar para que no colisionen: `trayectoria_fi` (C2) y `trayectoria_deuda` (C10). |
| `optimizacion_fiscal` / SD-19 `fiscalidad_nivel` | C5 / SD | SD-19 mide *conocimiento general*; C5 mide *acción sucesoria*. Acotar SD-19 a "lo sé / no lo sé" y dejar la acción en C5. |

### A3 · Equilibrio de capas (falsa precisión)
C1 tiene **16 ítems**, C2 quince, C11 catorce; C12 solo **6**, C6 y C10 siete. Un score 0-100 desde 6 ítems no tiene la resolución de uno desde 16.
**Decisión:** banda objetivo **8–10 ítems por capa**. Podar C1/C2/C11 a sus facetas con más carga diagnóstica; reforzar C12 con 2 ítems (horizonte real y coste de comisiones ya están; añadir tolerancia al riesgo).

---

## B · LO QUE FALTA (huecos, alineados con tu marketing)

Tus carruseles venden incapacidad del profesional liberal, gap de pensión del autónomo y venta de empresa. El cuestionario debe capturar ese dato:

| Nuevo campo | Pregunta | Se muestra si | Por qué |
|---|---|---|---|
| `seguro_incapacidad` | Si una enfermedad/accidente te impidiera trabajar mañana, ¿tienes un seguro que cubra tu pérdida de ingresos? | perfil ∈ {autónomo, empresa, liberal} | Es el riesgo nº1 de tu carrusel "200.000€ que dependen de ti". |
| `base_cotizacion` | Como autónomo, ¿por qué base cotizas? | perfil = autónomo | Aterriza el gap de pensión sin inventarlo. |
| `intencion_venta` | Tu empresa, ¿entra en tus planes venderla algún día? | perfil = empresa propia | Habilita el ángulo "4 millones en la cuenta". |
| `perfil_riesgo` | Si tu inversión cayera un 20% en un mal año, ¿qué harías? | siempre (si invierte) | Perfil de riesgo explícito, estándar en banca privada. |
| `testamento` | ¿Tienes testamento hecho y actualizado? | patrimonio ≥ 100k o tiene hijos | Dato factual de sucesión (hoy solo se mide la percepción en C5). |

---

## C · ORDEN FINAL DEL CUESTIONARIO (sin repeticiones)
1. **Sociodemográfico** (SD-1 sexo → perfil laboral → vivienda → pareja/dependientes → fiscalidad/conciliación) **+ los 3 nuevos condicionales** (incapacidad, cotización, venta).
2. **Números de tu economía** — primero los totales que NO se derivan (gasto, patrimonio, deuda, colchón); el desglose por fuente solo si el cliente lo activa, y de él se derivan ingreso/horas/renta pasiva.
3. **Las 12 capas** (C1–C12), equilibradas a 8–10 ítems, facetas sin duplicar.
4. **Perfil de riesgo + testamento** (los dos nuevos transversales).
5. **Vida ideal y brecha** → **Prioridades** (cierre).

---

## D · QUÉ EJECUTO YA (seguro) vs QUÉ NECESITA PASE VERIFICADO
- **Ahora, sin riesgo (aditivo):** las 5 preguntas nuevas del bloque B, condicionadas, desplegadas y validadas por CI. No tocan el scoring existente.
- **Pase verificado (lockstep):** la deduplicación A1/A2/A3, porque toca campos que el motor consume; se hace con render E2E delante para no romper producción. Aquí queda especificado al detalle, listo para ejecutar en cuanto el entorno permita verificar el render.

*Adapta Family Office · documento de ingeniería de instrumento · v2.1*
