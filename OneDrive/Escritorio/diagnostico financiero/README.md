# Diagnóstico Financiero - Sistema Completo

Sistema integral de diagnóstico financiero con cuestionario de 500 preguntas, motor de análisis Python, generación de reportes PDF y despliegue en Render.

## Stack Tecnológico

- **Frontend**: React 18 + Vite + Tailwind CSS
- **Backend**: FastAPI + Python 3.11
- **Reporte**: ReportLab (PDF)
- **Despliegue**: Render.com (single dyno, all-in-one)

## Estructura del Proyecto

```
diagnostico-financiero/
├── src/                           # React app source
│   ├── main.jsx                   # Entry point
│   ├── App.jsx                    # Root component
│   ├── components/
│   │   └── QuestionnaireFlow.jsx  # Repaired component (memory leak fixes)
│   └── index.css                  # Tailwind styles
├── dist/                          # Built React app (Vite output)
├── package.json                   # NPM dependencies
├── vite.config.js                 # Vite bundler config
├── tailwind.config.js             # Tailwind CSS config
├── postcss.config.js              # PostCSS config
├── app_standalone.py              # FastAPI server (mounts dist/ as static)
├── diagnostic_engine.py           # Scoring & analysis
├── diagnostic_report_generator.py # PDF generation
├── data-schema-500.json           # Question definitions (500 preguntas)
├── requirements.txt               # Python dependencies
├── build.sh                       # Build script (npm + pip)
├── render.yaml                    # Render.com deployment config
└── README.md                      # This file
```

## Quick Start

### Local Development

```bash
# 1. Install dependencies
npm install
pip install -r requirements.txt

# 2. Build React app
npm run build

# 3. Run FastAPI server
python app_standalone.py

# 4. Open http://localhost:8000
```

### Building for Production

```bash
npm run build  # Creates dist/ folder with optimized React app
python app_standalone.py  # FastAPI serves dist/ + API
```

## Deployment to Render

The `render.yaml` and `build.sh` are already configured for Render.com:

1. Connect your GitHub repo to Render
2. Render auto-detects `render.yaml` and follows the build/start commands
3. Build process:
   - `npm install` → Install Node dependencies
   - `npm run build` → Create optimized dist/ folder
   - `pip install -r requirements.txt` → Install Python dependencies
4. Start process:
   - `python app_standalone.py` → Launch FastAPI on PORT env var

## Key Features

### Componente React Reparado (QuestionnaireFlow.jsx)

Fixed 5 memory leaks:
1. **Event listener accumulation** → useCallback for all handlers
2. **O(n) lookups** → Memoized Map (O(1)) for 500 questions
3. **Concurrent clicks** → isAnswering guard + 100ms debounce
4. **Cascade re-renders** → React.memo on child components
5. **Missing back button** → questionHistory array tracking

### API Endpoints

- `GET /health` - Health check
- `GET /api/v1/schema` - Get all 500 questions
- `POST /api/v1/diagnose` - Submit answers, get PDF report
- `/ (SPA fallback)` - Serve React app from dist/

### Static Files

- React app served from `dist/` (built by Vite)
- PDFs saved to `reports/` directory
- Automatic fallback to index.html for SPA routing

## Performance Notes

- React component optimized for 500 questions
- Vite builds optimized bundles (minified, tree-shaken)
- FastAPI serves prebuilt static files (no runtime React compilation)
- Memory footprint: ~50-100MB (Python + FastAPI)

## Troubleshooting

### Port Already in Use
```bash
# Change port (Render sets PORT env var automatically)
PORT=3000 python app_standalone.py
```

### Build Fails on Render
- Check build.sh permissions: `chmod +x build.sh`
- Check requirements.txt syntax
- Check package.json syntax

### React App Not Loading
- Verify `dist/` exists after `npm run build`
- Check browser console for errors
- Check FastAPI logs for 404 errors

## Next Steps

1. Test end-to-end: Answer all 500 questions → Get PDF report
2. Customize styling via `tailwind.config.js`
3. Add authentication if needed
4. Monitor on Render dashboard
