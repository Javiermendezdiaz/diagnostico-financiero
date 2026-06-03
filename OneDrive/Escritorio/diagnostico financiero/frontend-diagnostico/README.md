# Diagnóstico Financiero — Frontend Next.js

Interfaz premium para diagnóstico financiero adaptativo. 100 preguntas distribuidas en 3 fases, generación de PDF personalizado de 4 secciones.

## Arquitectura

```
Frontend (Next.js 14 + TypeScript + Zustand)
    ↓
API Routes (/app/api/*)
    ↓
Python Backend (FastAPI)
    ↓
Motor Adaptativo (motor_adaptativo_100p.py)
Generador PDF (generador_pdf_simple.py)
```

## Stack

- **Next.js 14** — React 19, App Router, Server Components
- **TypeScript** — Type safety end-to-end
- **Zustand** — Lightweight state management (DiagnosticoState)
- **Framer Motion** — Animations & transitions
- **Tailwind CSS** — Styling (yellow #FDD731 primary accent)
- **canvas-confetti** — Gamification celebrations

## Fases

### Phase 1 — Cimientos (25 preguntas)
Perfil financiero base: ingresos, gastos, deudas, patrimonio, situación psicológica.
- Backend detecta perfil (ej: "endeudado", "conservador", "emprendedor")
- Retorna 50 preguntas dinámicas basadas en perfil

### Phase 2 — Dinámico (50 preguntas adaptativas)
Preguntas personalizadas según respuestas Phase 1.
- Cruza situación financiera + perfil
- Genera 25 preguntas Phase 3 basadas en patrón psicológico detectado

### Phase 3 — Psicología (25 preguntas)
Creencias, patrones, disposición al cambio.
- Genera PDF con 4 secciones:
  - Diagnóstico (números + análisis)
  - Psicología (patrones limitantes)
  - Stress Tests (escenarios críticos)
  - Plan 90 Días (acción concreta)

## Instalación

```bash
# Clonar repo
git clone <repo>
cd frontend-diagnostico

# Instalar dependencias
npm install

# Crear .env.local desde .env.example
cp .env.example .env.local
# Editar .env.local con credenciales reales
```

## Configuración

### Variables de entorno (.env.local)

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000  # Backend API base URL
NEXT_PUBLIC_BIZUM_MERCHANT_ID=xxx              # Bizum merchant ID (opcional)
BIZUM_API_KEY=yyy                              # Bizum API key (secreto)
NEXT_PUBLIC_GA_ID=zzz                          # Google Analytics ID (opcional)
NEXT_PUBLIC_REPORT_PRICE_EUR=29                # Precio del PDF en euros
```

## Desarrollo

```bash
# Iniciar dev server
npm run dev

# El frontend se ejecuta en http://localhost:3000
# El backend debe estar corriendo en http://localhost:8000
```

### Estructura de componentes

```
components/
├── questions/
│   ├── SliderQuestion.tsx       (input de rango 0-100)
│   ├── ScaleQuestion.tsx        (escala 1-10 con emoji)
│   ├── ToggleGridQuestion.tsx   (selección múltiple)
│   └── ComparativeQuestion.tsx  (binary left/right)
├── insights/
│   ├── InsightCard.tsx          (feedback contextual)
│   ├── TransitionCard.tsx       (celebración entre fases)
│   └── ProgressVisualization.tsx (barra de progreso 3 fases)
├── phases/
│   ├── Phase1.tsx               (25 preguntas cimientos)
│   ├── Phase2.tsx               (50 preguntas dinámicas)
│   ├── Phase3.tsx               (25 preguntas psicología)
│   └── QuestionnaireFlow.tsx    (orquestador principal)
└── results/
    └── ResultPage.tsx           (descarga PDF + repetir)
```

### Flujo de datos (Zustand)

```typescript
interface DiagnosticoState {
  fase: 1 | 2 | 3 | 'resultado';
  respuestas: Record<string, any>;
  perfil: string | null;
  fase2Preguntas: any[];
  fase3Preguntas: any[];
  pdfUrl: string | null;
  
  // Actions
  setRespuesta(id: string, valor: any): void;
  avanzarFase(): void;
  setPerfil(perfil: string): void;
  setFase2Preguntas(preguntas: any[]): void;
  setFase3Preguntas(preguntas: any[]): void;
  setPdfUrl(url: string): void;
  reset(): void;
}
```

### API Routes

#### POST /api/motor/generar-fase2
Recibe respuestas Phase 1 → Detecta perfil → Retorna 50 preguntas Phase 2

**Request:**
```json
{
  "respuestas": {
    "ingresos_netos": 3000,
    "gastos_totales": 2500,
    ...
  }
}
```

**Response:**
```json
{
  "perfil": "endeudado_moderado",
  "fase2_preguntas": [
    {
      "id": "q_2_1",
      "type": "slider|scale|toggle|comparative",
      "title": "...",
      ...
    },
    ...
  ]
}
```

#### POST /api/motor/generar-fase3
Recibe respuestas Phase 1+2 → Genera 25 preguntas Phase 3 personalizadas

**Response:**
```json
{
  "fase3_preguntas": [...]
}
```

#### POST /api/pdf/generar
Recibe todas las respuestas → Genera PDF → Retorna URL descargable

**Response:**
```json
{
  "pdfUrl": "https://storage.example.com/diagnostico-javier-2026-05-28.pdf"
}
```

## Despliegue

### Railway (recomendado)
1. Conectar repo GitHub
2. Configurar variables de entorno en Railway dashboard
3. Deploy automático en cada push

### Vercel
```bash
vercel deploy
```

### Self-hosted
```bash
npm run build
npm start
```

## Testing

```bash
# Unit tests (jest)
npm run test

# E2E tests (playwright) — próximamente
npm run test:e2e
```

## Integración con Python Backend

El backend debe exponer estos endpoints:

- `POST /api/motor/generar-fase2` — Detecta perfil + genera Phase 2
- `POST /api/motor/generar-fase3` — Genera Phase 3 personalizado
- `POST /api/pdf/generar` — Genera PDF desde respuestas

Documentación del backend: [Ver backend README]

## Performance

- **Lazy loading** de fases (no se cargan todas upfront)
- **AnimatePresence** para transiciones smooth de preguntas
- **Image optimization** con next/image
- **State persistence** en Zustand (localStorage opcional)

## Seguridad

- ✅ API routes como proxy (no expone backend directamente)
- ✅ CORS habilitado solo para orígenes autorizados
- ✅ Rate limiting en API routes (próximamente)
- ✅ Validación de entrada en backend
- ⚠️ Agregar autenticación si es multi-user

## Troubleshooting

### "Failed to generate Phase 2"
→ Verificar que backend está corriendo en `NEXT_PUBLIC_BACKEND_URL`

### Preguntas no cargan
→ Revisar respuestas en DevTools → Application → Zustand store

### PDF no se descarga
→ Verificar que `pdfUrl` es accesible públicamente desde browser

## Próximos pasos

- [ ] Integración Bizum para pago de PDF
- [ ] Google Analytics para tracking de funnel
- [ ] Email automation (enviar PDF descargado)
- [ ] Dashboard de admin (analytics, respuestas agregadas)
- [ ] Localization (EN, FR, DE)
- [ ] Mobile app (React Native)

## Licencia

Propietario — Adapta Family Office

## Contacto

javier@mendezconsultoria.com
