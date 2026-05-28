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
    report_generator = DiagnosticReportGenerator(str(output_dir))
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

        # Generate PDF report
        import time
        user_id = f"user_{int(time.time())}"
        report_filename = f"{user_id}_diagnostic.pdf"
        pdf_path = report_generator.generate_report(result, report_filename)

        # Return result
        result_dict = result if isinstance(result, dict) else result.__dict__
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

# Mount static files LAST to serve everything else (SPA fallback)
# This serves index.html and all static assets from the current directory
app.mount("/", StaticFiles(directory=app_dir, html=True), name="static")

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
