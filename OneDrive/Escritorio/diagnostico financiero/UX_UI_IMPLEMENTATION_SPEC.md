# UX/UI Implementation Roadmap — Diagnóstico Financiero

## FASE 1: Emotional Contextual Keyboard ✓ COMPLETADO

**Status**: Implementado y lista para testing  
**Archivo**: `src/components/EmotionalInput.jsx`  
**Integración**: QuestionnaireFlow.jsx — detección automática de escala 1-5

### Especificación técnica
- **Trigger**: Pregunta con `min=1, max=5`
- **Componente**: EmotionalInput (React.memo, optimizado)
- **Mapeo emoji ↔ valor**:
  - 😟 (1) = Muy en desacuerdo
  - 😐 (2) = En desacuerdo
  - 😊 (3) = Neutral
  - 😄 (4) = De acuerdo
  - 😁 (5) = Muy de acuerdo

### Comportamiento
1. Click emoji → selección visual inmediata (scale-110, ring)
2. Descripción contextual debajo → refuerzo emocional
3. Botón "Confirmar y continuar" → feedback antes de transición
4. Fallback automático a NumberInput para otros rangos

### Métricas esperadas
- Reducción fricción: 40% menos tiempo en Likert
- Intención reflexiva: mayor conexión emocional con respuesta
- Drop-off: reducción del 15-20% en abandono

### Next: Testing A/B
Ejecutar 100 sesiones con/sin Emotional Keyboard. Medir:
- Tiempo promedio por pregunta Likert
- Tasa de abandono por pregunta
- Score de satisfacción post-diagnóstico

---

## FASE 2: Mirror Contrast Mode — Couple Sessions

**Objetivo**: Visualizar datos de ambos partners simultáneamente sin navegación  
**Target Component**: Couple Chapter 9 viewer (PDF → React viewer)

### Especificación
```
Componente: <MirrorContrastDisplay />
├── State: contrastMode (light|dark)
├── Props: 
│   ├── userSessionData (datos del usuario actual)
│   ├── partnerSessionData (datos del partner)
│   └── couppleChapterContent (JSON con Chapter 9)
└── Lógica: En dark mode, invertir paleta de partnerData

CSS Strategy:
- Light mode: Usuario izquierda (normal) | Partner derecha (normal)
- Dark mode: Usuario izquierda (normal) | Partner derecha (HSL invert)
  ejemplo: color: hsl(calc(360deg - hue), calc(100% - sat), calc(100% - light))
```

### Interfaz
```jsx
<div className="grid grid-cols-2 gap-4">
  <div className="bg-white">
    {/* User data: normal */}
    <AlignmentScore data={userSessionData} />
    <FrictionZones data={userSessionData} />
  </div>
  <div className={contrastMode === 'dark' ? 'mirror-invert' : ''}>
    {/* Partner data: normal o invertido */}
    <AlignmentScore data={partnerSessionData} />
    <FrictionZones data={partnerSessionData} />
  </div>
</div>

<button onClick={() => setContrastMode(contrastMode === 'light' ? 'dark' : 'light')}>
  Toggle: {contrastMode === 'light' ? '🌙 Modo oscuro' : '☀️ Modo claro'}
</button>
```

### Beneficio UX
- Comparación inmediata (no swipes)
- Modo oscuro para Partner = metáfora visual de "diferencia"
- Accesible: mantiene legibilidad en ambos lados

---

## FASE 3: Invisible Gesture Interface (Mobile)

**Scope**: Swipe navigation + double-tap to save  
**Target**: Mobile questionnaire flow (<768px)

### Gestures
| Gesto | Acción | Contexto |
|-------|--------|----------|
| Swipe Right (→) | Pregunta siguiente | Durante cuestionario |
| Swipe Left (←) | Pregunta anterior | Durante cuestionario |
| Double-tap | Guardar progreso | Any question |
| Long-press (hold 2s) | Bookmark pregunta | For later review |

### Implementación
```bash
npm install @use-gesture/react @react-use/gesture
```

**Componente wrapper**:
```jsx
const GestureQuestionnaireFlow = ({ children }) => {
  const bind = useGesture({
    onSwipe: ({ direction }) => {
      if (direction[0] === 1) handleNext(); // → right
      if (direction[0] === -1) handlePrev(); // ← left
    },
    onDoubleTap: () => saveProgress()
  });
  return <div {...bind()}>{children}</div>;
};
```

---

## FASE 4: Semantic Bubble Interactions (Deferred)

**Status**: Requiere modelo ML previo — diferido a post-MVP  
**Descripción**: Burbujas contextuales que exploten/se contraigan según modelo de comprensión

---

## Orden de implementación recomendado

✓ FASE 1: Emotional Keyboard (completado)  
→ FASE 2: Mirror Contrast Mode (próximo, 4h dev)  
→ FASE 3: Gesture Interface (3h dev, mobile-first)  
→ FASE 4: Semantic Bubbles (post-MVP, requiere modelo)

---

## Testing strategy

**Pre-deploy para cada fase**:
1. Unit tests: componentes individuales
2. Integration: flujo completo (questionnaire → PDF)
3. A/B testing: 100+ sesiones, métricas de engagement
4. Accessibility audit: WCAG 2.1 AA

**Métricas clave**:
- Time per question (↓ 40% target)
- Completion rate (↑ 15% target)
- Satisfaction score (↑ 1 punto NPS)
- Mobile engagement (↑ 25% en mobile-only)

---

## Technical debt / Optimization

- [ ] Memoize EMOTIONAL_SCALE (constant fuera del componente)
- [ ] Lazy-load EmotionalInput (code-splitting)
- [ ] Gesture events: debounce/throttle para evitar double-triggers
- [ ] CSS-in-JS → Tailwind config variables (dark mode nativo)
- [ ] Mirror invert: cache calculated values en React Context

