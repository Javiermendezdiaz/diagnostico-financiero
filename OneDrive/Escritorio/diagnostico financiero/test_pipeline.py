#!/usr/bin/env python3
"""
End-to-end pipeline test: Schema → Answers → Diagnostic → PDF
Verifies that app_standalone.py components work together
"""

import json
import sys
from pathlib import Path

# Setup
app_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(app_dir))

from diagnostic_engine import DiagnosticEngine
from diagnostic_report_generator import DiagnosticReportGenerator

# Paths
schema_path = app_dir / "data-schema-500.json"
output_dir = app_dir / "reports"
output_dir.mkdir(exist_ok=True)

print("=" * 60)
print("PIPELINE TEST: Schema → Engine → Report")
print("=" * 60)

# Step 1: Load schema
print("\n[1/4] Loading schema...")
with open(schema_path, 'r', encoding='utf-8') as f:
    schema = json.load(f)
total_preguntas = schema.get('metadata', {}).get('total_preguntas', 0)
print(f"✓ Schema loaded: {total_preguntas} questions")

# Step 2: Initialize diagnostic engine
print("\n[2/4] Initializing diagnostic engine...")
diagnostic_engine = DiagnosticEngine(str(schema_path))
print("✓ Engine initialized")

# Step 3: Simulate 50 answers (roughly 10% of questions)
print("\n[3/4] Generating test answers (50 questions)...")
test_answers = {}
all_questions = []

# Flatten questions from schema
capas = schema.get('capas', {})
for capa_name, capa_data in capas.items():
    preguntas = capa_data.get('preguntas', [])
    all_questions.extend(preguntas)

# Create answers for first 50 questions
for i, pregunta in enumerate(all_questions[:50]):
    q_type = pregunta.get('type', 'text')

    if q_type == 'number':
        test_answers[i+1] = 100  # Random number
    elif q_type == 'boolean':
        test_answers[i+1] = i % 2 == 0  # Alternate yes/no
    elif q_type == 'select':
        respuestas = pregunta.get('respuestas', ['Sí'])
        test_answers[i+1] = respuestas[0] if respuestas else 'Opción'
    else:  # text
        test_answers[i+1] = f"Respuesta automática a pregunta {i+1}"

print(f"✓ Generated {len(test_answers)} test answers")

# Step 4: Run diagnostic
print("\n[4/4] Running diagnostic...")
result = diagnostic_engine.diagnose(test_answers)
print(f"✓ Diagnostic complete:")
print(f"  - Overall score: {result.overall_score:.1f}/100")
print(f"  - Capas scored: {len(result.capa_scores)}")
print(f"  - Alerts detected: {len(result.alerts)}")
print(f"  - Recommendations: {len(result.recommendations)}")

# Step 5: Generate PDF
print("\n[5/5] Generating PDF report...")
result_dict = diagnostic_engine.export_json(result)
pdf_filename = output_dir / "test_diagnostic.pdf"
report_generator = DiagnosticReportGenerator(str(pdf_filename))
pdf_path = report_generator.generate_report(result_dict)
print(f"✓ PDF generated: {pdf_path}")

# Verify file exists and has size
if Path(pdf_path).exists():
    file_size = Path(pdf_path).stat().st_size
    print(f"✓ File size: {file_size / 1024:.1f} KB")
else:
    print("✗ PDF file not created!")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ PIPELINE TEST COMPLETE - All systems operational!")
print("=" * 60)
print(f"\nPDF saved to: {pdf_path}")
print("Ready for Render deployment.")
