# Instrucciones E2E Testing — Diagnóstico Financiero

## Estado Actual
- ✓ Servidor FastAPI configurado en `app_standalone.py`
- ✓ Frontend React compilado en carpeta `dist/`
- ✓ HTML con carga de React desde CDN
- ✓ Endpoints API funcionales (/api/v1/schema, /api/v1/diagnose)
- ⏳ **ACCIÓN MANUAL REQUERIDA**: Iniciar servidor en Windows

## Paso 1: Iniciar Servidor (REQUERIDO)

### Opción A: Doble-click (Recomendado)
1. Abre la carpeta: `C:\Users\javie\OneDrive\Escritorio\diagnostico financiero`
2. Busca el archivo: `start-server.bat`
3. Doble-click para ejecutar
4. Verás una ventana de terminal con logs del servidor
5. Espera hasta ver: "Uvicorn running on http://0.0.0.0:8000"

### Opción B: PowerShell Manual
```powershell
cd "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"
python app_standalone.py
```

## Paso 2: Verificar Servidor

Una vez iniciado, el servidor responderá en:
- **Frontend**: http://localhost:8000
- **API Schema**: http://localhost:8000/api/v1/schema
- **API Diagnose**: http://localhost:8000/api/v1/diagnose (POST)

## Test Cases (E2E Suite)

### TC-1: Health Check ✓ PASSED
```
GET http://localhost:8000/health
Esperado: {"status":"ok"} 200 OK
```

### TC-2: Cuestionario Completo + PDF (PENDIENTE)
1. Navega a http://localhost:8000
2. Verás pregunta 1 de 500
3. Selecciona una respuesta
4. Haz click "Siguiente" 
5. Continúa hasta pregunta 500
6. Haz click "Generar Reporte"
7. Se descargará PDF con diagnóstico

### TC-3: Validación de Errores (PENDIENTE)
- Intenta enviar respuestas inválidas
- Verifica que API rechaza datos incorrectos

### TC-4: Navegación y Estado (PENDIENTE)
- Usa botón "Anterior" para volver a preguntas previas
- Verifica que las respuestas se guardan

### TC-5: Performance (PENDIENTE)
- Mide tiempo de carga del schema
- Mide tiempo de generación de PDF

### TC-6: Stress Test (PENDIENTE)
- Realiza 5+ requests concurrentes a /api/v1/diagnose
- Verifica que el servidor maneja la carga

## Logs y Debugging

Los logs se mostrarán en la terminal donde ejecutaste el servidor. Errores comunes:

- **Port already in use**: Otro proceso usa puerto 8000
  - Solución: Cierra la ventana anterior o cambia puerto en app_standalone.py

- **Module not found**: Dependencias no instaladas
  - Solución: `pip install -r requirements.txt`

- **React no renderiza en navegador**: 
  - Verifica que http://localhost:8000/api/v1/schema devuelve JSON
  - Abre DevTools (F12) y revisa consola para errores
  - Recarga página con Ctrl+Shift+R (hard refresh)

## Archivos Clave

- `app_standalone.py` - Servidor FastAPI
- `dist/index.html` - Frontend React + CDN loader
- `data-schema-500.json` - 500 preguntas del diagnóstico
- `start-server.bat` - Script para iniciar servidor (Windows)

## Próximas Acciones

Una vez el servidor esté corriendo:
1. Ejecutar TC-2: Completar cuestionario + generar PDF
2. Ejecutar TC-3 a TC-6: Tests restantes
3. Generar reporte de E2E testing

---
**Fecha creación**: 2026-05-29
**Versión**: Bloque 3 - E2E Testing
