# FRAGMENTO CORREGIDO - Reemplazar el endpoint GET /question/first en main_production_ready.py

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

# ============================================================================
# ENDPOINT CORREGIDO - Devuelve la SIGUIENTE pregunta sin responder
# ============================================================================

@app.get("/{draft_id}/question/first")
def get_next_question(draft_id: str, db: Session = Depends(get_db)):
    """
    Devuelve la SIGUIENTE pregunta sin responder basada en el progreso real del usuario.

    Lógica:
    1. Obtiene todas las respuestas guardadas para este draft
    2. Calcula el máximo order respondido
    3. Devuelve la pregunta con order = máximo + 1
    """
    try:
        # Validar que el borrador existe
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail="Borrador no encontrado")

        # PASO 1: Obtener el MÁXIMO order que ya fue respondido
        max_order_answered = db.query(func.max(DraftResponse.order)).filter(
            DraftResponse.draft_id == draft_id
        ).scalar()

        # PASO 2: Calcular el siguiente order
        if max_order_answered is None:
            # Nada respondido aún → devolver pregunta 1
            next_order = 1
        else:
            # Ya respondió algo → siguiente pregunta
            next_order = max_order_answered + 1

        # PASO 3: Obtener la pregunta del siguiente order
        question = db.query(Question).filter(
            Question.plan_id == draft.plan,
            Question.order == next_order
        ).first()

        # PASO 4: Si no hay más preguntas, cuestionario completado
        if not question:
            return {
                "isComplete": True,
                "session_token": draft.session_token,
                "total": db.query(func.count(Question.id)).filter(
                    Question.plan_id == draft.plan
                ).scalar()
            }

        # PASO 5: Devolver la siguiente pregunta
        return {
            "question": {
                "id": question.id,
                "text": question.text,
                "type": question.type,
                "order": question.order,
                "required": True
            },
            "session_token": draft.session_token,
            "total": db.query(func.count(Question.id)).filter(
                Question.plan_id == draft.plan
            ).scalar()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en GET /question/first: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================================================
# INSTRUCCIONES DE ACTUALIZACIÓN:
# ============================================================================
# 1. Abre main_production_ready.py en Render
# 2. Busca el endpoint @app.get("/{draft_id}/question/first")
# 3. Reemplaza TODO ese función por el código de arriba
# 4. Guarda
# 5. Render se redeploya automáticamente
# ============================================================================
