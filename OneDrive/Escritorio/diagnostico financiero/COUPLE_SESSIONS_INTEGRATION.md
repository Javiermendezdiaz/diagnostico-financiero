# Couple Sessions — Guía de Integración

## Arquitectura de flujo

```
Usuario 1 (Diagnóstico completo) 
    ↓
Usuario 2 (Diagnóstico completo + marca session as "couple")
    ↓
Backend: Genera DiagnosticResult para ambos + coupple_chapter.json
    ↓
Frontend: Carga MirrorContrastDisplay con ambos datos
```

## Backend: Marcar sesión como "couple"

En `diagnostic_report_generator.py`, agregar flag:

```python
diagnostic_result.metadata = {
    "session_type": "couple",  # o "individual"
    "partner_user_id": partner_id,
    "couple_session_id": uuid.uuid4()
}
```

## Frontend: Integrar MirrorContrastDisplay

### Paso 1: Importar en componente de reporte

```jsx
// En ReportViewer.jsx o similar
import MirrorContrastDisplay from './MirrorContrastDisplay';

export default function ReportViewer({ diagnosticResult, couppleSessionData }) {
  // Detectar si es couple session
  const isCoupleSession = diagnosticResult.metadata?.session_type === 'couple';

  return (
    <div className="space-y-8">
      {/* Reportes individuales */}
      <IndividualReportChapter9 data={diagnosticResult} />

      {/* SI es couple session, mostrar vista comparativa */}
      {isCoupleSession && couppleSessionData?.partner_data && (
        <MirrorContrastDisplay
          userSessionData={diagnosticResult}
          partnerSessionData={couppleSessionData.partner_data}
          couppleChapterContent={couppleSessionData.chapter_content}
        />
      )}
    </div>
  );
}
```

### Paso 2: Backend endpoint para recuperar partner data

```python
# FastAPI endpoint
@app.post("/api/v1/couple-session/{couple_session_id}")
async def get_couple_session(couple_session_id: str):
    """Recupera datos de ambos partners para comparativa"""
    couple_data = db.query(CoupleSession).filter_by(id=couple_session_id).first()
    
    return {
        "user_data": couple_data.user_diagnostic,
        "partner_data": couple_data.partner_diagnostic,
        "chapter_content": couple_data.chapter_9_json,
        "alignment_score": couple_data.computed_alignment_score
    }
```

### Paso 3: Flujo de usuario

1. **Usuario 1** completa diagnóstico → descarga PDF individual
2. **Usuario 2** completa diagnóstico → se le pregunta: "¿Quieres compararte con tu partner?"
3. Si sí → entra a **couple_session_id** → ambos datos se cargan en MirrorContrastDisplay
4. Toggle Modo Oscuro para comparación visual
5. Opción: descargar PDF con ambas perspectivas

## Props de MirrorContrastDisplay

```typescript
interface MirrorContrastDisplayProps {
  userSessionData: DiagnosticResult;  // Tu diagnóstico
  partnerSessionData: DiagnosticResult;  // Diagnóstico del partner
  couppleChapterContent?: object;  // Metadatos adicionales (opcional)
}
```

## Datos esperados en DiagnosticResult

```json
{
  "alignment_score": 68,
  "friction_zones": [
    {
      "name": "Tolerancia ante riesgo",
      "description": "Estilos de inversión divergentes",
      "severity": "high"  // "low" | "medium" | "high"
    },
    {
      "name": "Gasto presente",
      "description": "Diferencias en consumo mensual",
      "severity": "medium"
    }
  ]
}
```

## CSS personalización (opcional)

Si quieres customizar colores, edita `MirrorContrastDisplay.jsx`:

```jsx
const SEVERITY_COLORS = {
  low: '#4caf50',      // Verde
  medium: '#ffa726',   // Naranja
  high: '#ef5350'      // Rojo
};
```

## Testing

**Datos mock para testing**:

```javascript
const mockUserData = {
  alignment_score: 72,
  friction_zones: [
    { name: "Aversión al riesgo", description: "Usuario conservador", severity: "medium" }
  ]
};

const mockPartnerData = {
  alignment_score: 58,
  friction_zones: [
    { name: "Aversión al riesgo", description: "Partner agresivo", severity: "low" },
    { name: "Gasto presente", description: "Diferencia en consumo", severity: "high" }
  ]
};

<MirrorContrastDisplay
  userSessionData={mockUserData}
  partnerSessionData={mockPartnerData}
/>
```

## Próximos pasos

- [ ] Crear endpoint `/api/v1/couple-session/{id}` en backend
- [ ] Integrar MirrorContrastDisplay en ReportViewer
- [ ] Testing A/B: comparativa vs. reporte individual
- [ ] Agregar exportación PDF con vista comparativa
- [ ] Opción: comparativa en LinkedIn (carrusel "Alineación de pareja")

---

## Notas técnicas

- **Performance**: MirrorContrastDisplay usa React.memo para ambas AlignmentScoreCard y FrictionZonesCard
- **Accesibilidad**: Colores invertidos en dark mode mantienen contraste WCAG AA
- **Mobile**: Grid responde a 2 columnas en desktop, 1 en mobile (apila verticamente)
- **Estado**: contrastMode es local al componente, no global (cada visión independiente)

