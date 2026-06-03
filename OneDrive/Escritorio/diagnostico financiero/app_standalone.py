#!/usr/bin/env python3
"""
Diagnóstico Financiero - FastAPI Backend + Static Frontend
Single port, all-in-one deployment for Render
"""

import sys
import json
import os
import logging
from pathlib import Path

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# App dir
app_dir = Path(__file__).parent.absolute()
os.chdir(app_dir)

# Create reports dir
output_dir = app_dir / "reports"
output_dir.mkdir(exist_ok=True)

# Import FastAPI
try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    sys.exit(1)

# Import diagnostic modules
try:
    from diagnostic_engine import DiagnosticEngine
    from diagnostic_report_generator import DiagnosticReportGenerator
except ImportError as e:
    logger.error(f"Module import error: {e}")
    sys.exit(1)

# Load schema
schema_path = app_dir / "data-schema-500.json"
try:
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    total_preguntas = schema.get('metadata', {}).get('total_preguntas', 500)
    logger.info(f"Schema loaded: {total_preguntas} questions")
except FileNotFoundError:
    logger.error(f"Schema not found: {schema_path}")
    sys.exit(1)

# Create diagnostic engine
try:
    diagnostic_engine = DiagnosticEngine(str(schema_path))
    logger.info("Diagnostic engine initialized")
except Exception as e:
    logger.error(f"Engine initialization error: {e}")
    sys.exit(1)

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ API ENDPOINTS ============

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/api/v1/schema")
def get_schema():
    """Return all 500 questions in flat array format"""
    questions = []
    question_id = 1

    capas = schema.get('capas', {})
    for capa_name, capa_data in capas.items():
        preguntas = capa_data.get('preguntas', [])
        for pregunta_data in preguntas:
            respuestas_list = pregunta_data.get('respuestas', [])
            pesos = pregunta_data.get('pesos', {})

            questions.append({
                "id": question_id,
                "capa": capa_name,
                "pregunta": pregunta_data.get('pregunta', ''),
                "respuestas": respuestas_list,
                "pesos": pesos
            })
            question_id += 1

    return {"questions": questions, "metadata": schema.get('metadata', {})}

@app.post("/api/v1/diagnose")
async def diagnose(request: Request):
    """Process diagnostic answers and generate report"""
    try:
        data = await request.json()
        answers = data.get("answers", {})

        # Run diagnostic
        result = diagnostic_engine.diagnose(answers)

        # Export to JSON-serializable dict
        result_dict = diagnostic_engine.export_json(result)

        # Generate PDF report
        import time
        user_id = f"user_{int(time.time())}"
        report_filename = f"{user_id}_diagnostic.pdf"
        pdf_filepath = output_dir / report_filename

        # Create fresh report generator for this request with full file path
        report_generator = DiagnosticReportGenerator(str(pdf_filepath))
        pdf_path = report_generator.generate_report(result_dict)

        # Return result
        return {
            "success": True,
            "results": result_dict,
            "report_path": str(pdf_path)
        }
    except Exception as e:
        logger.error(f"Diagnose error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ============ STATIC FILES ============

# Mount dist directory for Vite-built React app
dist_dir = app_dir / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
    logger.info(f"Serving React app from: {dist_dir}")
else:
    logger.warning(f"dist directory not found: {dist_dir}")
    # Fallback: serve index.html from root for development
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        Serve static files or fallback to index.html for single-page app routing.
        This is a fallback for development mode when dist/ is not built.
        """
        from fastapi.responses import FileResponse, HTMLResponse
        from fastapi.exceptions import HTTPException

        # Try to serve the actual file if it exists
        file_path = app_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # For CSS, JS, and other assets, return 404 if they don't exist
        if any(full_path.endswith(ext) for ext in ['.css', '.js', '.json', '.png', '.jpg', '.ico', '.svg', '.woff', '.woff2']):
            raise HTTPException(status_code=404, detail="Asset not found")

        # For other requests, serve index.html (SPA fallback)
        index_html = app_dir / "index.html"
        if index_html.exists():
            with open(str(index_html), 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())

        raise HTTPException(status_code=404, detail="Not found")

# ============ MAIN ============

if __name__ == "__main__":
    # Get port from environment (Render sets PORT env var)
    port = int(os.getenv("PORT", 8000))

    logger.info(f"Starting Diagnóstico Financiero on port {port}")
    logger.info(f"Frontend: http://localhost:{port}/")
    logger.info(f"API: http://localhost:{port}/api/v1/schema")

    # Run uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
