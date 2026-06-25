# Los 16 Arquetipos del Dinero — Adapta Family Office

**El "MBTI del dinero".** Cuatro ejes binarios de la relación con el dinero. Cada persona cae en un polo de cada eje → un **código de 4 letras** → uno de **16 arquetipos**. El código es identidad pura y comparable ("yo soy A-L-M-O, ¿y tú?"), y da 16 piezas de contenido compartible.

> Borrador para revisión de marca. Los nombres son lo que más se postea: cámbialos a tu gusto.

---

## Los 4 ejes

| Eje | Polo izquierdo | Polo derecho | Qué mide | Se lee de (capas) |
|---|---|---|---|---|
| **1 · Riesgo** | **S** — Seguridad | **A** — Audacia | ¿El dinero es escudo o palanca? | C3 Resistencia · C8 Antifragilidad · C12 Inversión · C2 Libertad |
| **2 · Tiempo** | **P** — Presente | **L** — Legado | ¿Disfrutar hoy o construir mañana? | C4 Estilo de vida · C6 Estatus · C2 Horizonte · C5 Herencia |
| **3 · Decisión** | **M** — Método | **I** — Instinto | ¿Sistema y datos, o intuición? | C9 Flujo · C4 Presupuesto · C2 Conocimiento |
| **4 · Esfera** | **O** — Solo | **T** — Tribu | ¿En solitario o en relación/equipo? | C1 Vínculo · C5 Protección de los tuyos · C11 Red |

**Cómo se calcula (sin apenas preguntas nuevas):** cada eje se decide por la inclinación neta de sus capas/ítems. Si el peso cae a un lado, esa letra; si queda en el filo, desempata una pregunta del bloque de arquetipo (que ya existe y ampliaríamos a 4 ejes). Resultado: 4 letras, 16 tipos.

---

## Los 16 arquetipos

| # | Código | Arquetipo | Lema | Tu luz | Tu sombra |
|---|---|---|---|---|---|
| 1 | **S·P·M·O** | El Centinela | "Vigilo lo mío, sin sobresaltos." | Orden y serenidad; nada se te escapa. | Dinero parado por miedo a moverlo. |
| 2 | **S·P·M·T** | El Guardián | "Protejo a los míos, con un plan." | Red de seguridad para tu familia. | Cargas tú solo con toda la tensión. |
| 3 | **S·P·I·O** | El Prudente | "Voy a lo seguro, a mi manera." | Instinto de conservación afinado. | Decides sin mirar los números. |
| 4 | **S·P·I·T** | El Anfitrión | "Disfruto la vida, y la comparto." | Sabes celebrar y cuidar a los tuyos hoy. | Poco colchón para el mañana. |
| 5 | **S·L·M·O** | El Estratega | "Construyo despacio y seguro." | Paciencia y estructura impecables. | Exceso de control; rigidez. |
| 6 | **S·L·M·T** | El Patriarca | "Dejo un legado blindado." | Proteges a varias generaciones. | Controlas demasiado a los tuyos. |
| 7 | **S·L·I·O** | El Previsor | "Guardo para mañana, por si acaso." | Disciplina de ahorro envidiable. | Te privas más de lo necesario. |
| 8 | **S·L·I·T** | El Protector | "Mi futuro es el de los míos." | Generosidad previsora con los tuyos. | Descuidas lo tuyo por los demás. |
| 9 | **A·P·M·O** | El Cazador | "Arriesgo, pero con cabeza y hoy." | Oportunismo calculado, sangre fría. | El riesgo puede volverse adicción. |
| 10 | **A·P·M·T** | El Emprendedor | "Construyo ahora, con mi gente." | Energía y red que mueven proyectos. | Quemas la caja por crecer rápido. |
| 11 | **A·P·I·O** | El Aventurero | "Me lanzo, ya veré." | Valentía pura; no te paraliza el miedo. | Impulsividad sin red de seguridad. |
| 12 | **A·P·I·T** | El Magnético | "La vida es ahora, y en grande." | Carisma; arrastras a la gente. | Apariencia y deuda para sostenerla. |
| 13 | **A·L·M·O** | El Arquitecto | "Convierto recursos en más recursos." | Visión de largo plazo + ejecución. | Workaholic; el plan te come la vida. |
| 14 | **A·L·M·T** | El Magnate | "Construyo algo que dure, con los míos." | Liderazgo patrimonial de raza. | El dinero por encima de todo. |
| 15 | **A·L·I·O** | El Pionero | "Veo lo que otros no, y voy." | Intuición visionaria; abres caminos. | Apuestas grandes sin cobertura. |
| 16 | **A·L·I·T** | El Visionario | "Inspiro y construyo el mañana." | Inspiras a otros a soñar en grande. | Sueños sin números que los sostengan. |

---

## Colores de marca (acento por arquetipo)

Cuatro familias por cuadrante de los dos ejes principales (Riesgo × Tiempo), con variación por matiz:

- **Seguridad + Presente** → verdes/teal (calma, prudencia): #1D6F42, #0E8A6E, #2E8B57, #B45309*
- **Seguridad + Legado** → azules profundos (solidez, futuro): #1E5BA8, #2563EB, #0284C7, #3B5BA5
- **Audacia + Presente** → ámbar/coral (energía, ahora): #C2410C, #E0701A, #DC2626, #B45309
- **Audacia + Legado** → morados (visión, construcción): #7C3AED, #6D28D9, #8B5CF6, #5B21B6

*(Asignación final de los 16 hex en la implementación.)*

---

## Plan de construcción (por fases, sin romper lo vivo)

1. **Cerrar los 16 nombres** (este documento) — tu criterio manda.
2. **Motor de ejes** en `score_v2`: calcular las 4 letras desde las capas; función `arquetipo16(resp, p, perfil)` que devuelve código + meta.
3. **Tarjeta premium** adaptada al código de 4 letras + nombre (el diseño ya está listo).
4. **Informe**: sustituir "El Explorador" por el tipo de 16 donde aparece el arquetipo.
5. **Test viral** (`test-arquetipo.html`) al modelo de 16 + tarjeta compartible.

El sistema de 4 actual (Guardián/Explorador/Vividor/Constructor) sigue funcionando mientras construyo el de 16. Cero downtime.
