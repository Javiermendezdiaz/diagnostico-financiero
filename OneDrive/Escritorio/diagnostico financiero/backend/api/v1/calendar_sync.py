"""
calendar_sync.py

Inyecta eventos del Plan de Acción a 90 días directamente en el calendario 
nativo del usuario (iOS Apple Calendar / Android Google Calendar).

Endpoint: POST /api/v1/calendar-sync/generate-ical
Retorna: iCal (.ics) file listo para sincronizar con calendario nativo.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import uuid

router = APIRouter()


def generate_action_plan_calendar(diagnostic_id: str, user_id: str) -> str:
    """
    Genera un archivo iCal (.ics) con los hitos del Plan de Acción a 90 días.
    
    Eventos base (adaptables según Score del usuario):
    - Día 7: "Tus 15 minutos de Saneamiento" (revisión de facturas)
    - Día 30: "Día de Blindaje" (protección patrimonial)
    - Día 60: "Checkpoint de Progreso" (medición de avances)
    - Día 90: "Tu Nuevo Score Financiero" (recalculación + reporte de impacto)
    """
    
    base_date = datetime.now()
    
    events = [
        {
            "title": "🧹 Tus 15 minutos de Saneamiento",
            "description": "Revisa tus últimas facturas. Busca 1-2 suscritos olvidados. Elimina lo innecesario.",
            "date": base_date + timedelta(days=7),
            "time": "19:00",
        },
        {
            "title": "🛡️ Día de Blindaje",
            "description": "Protege tu patrimonio: revisa seguros, documenta inversiones, asegura herencia.",
            "date": base_date + timedelta(days=30),
            "time": "10:00",
        },
        {
            "title": "📊 Checkpoint de Progreso",
            "description": "Midamos el impacto: recalcula tu Score, verifica movimientos de Fugas, reajusta tu Plan.",
            "date": base_date + timedelta(days=60),
            "time": "18:00",
        },
        {
            "title": "🎯 Tu Nuevo Score Financiero",
            "description": "Eres una versión mejorada de ti. Descubre cuánto has avanzado en 90 días.",
            "date": base_date + timedelta(days=90),
            "time": "15:00",
        },
    ]
    
    # Generar iCal format
    ical = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Diagnóstico Financiero//ES
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Plan de Acción - Diagnóstico Financiero
X-WR-TIMEZONE:Europe/Madrid

"""
    
    for i, event in enumerate(events):
        event_uid = f"{diagnostic_id}-action-{i}-{uuid.uuid4()}"
        event_datetime = event["date"].replace(hour=int(event["time"].split(":")[0]), minute=int(event["time"].split(":")[1]))
        
        ical += f"""BEGIN:VEVENT
UID:{event_uid}
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{event_datetime.strftime('%Y%m%dT%H%M%S')}
DTEND:{(event_datetime + timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')}
SUMMARY:{event['title']}
DESCRIPTION:{event['description']}
LOCATION:Tu vida financiera
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT

"""
    
    ical += """END:VCALENDAR"""
    
    return ical


@router.post("/generate-ical")
async def generate_ical_for_calendar(payload: dict):
    """
    POST /api/v1/calendar-sync/generate-ical
    
    Request:
    {
        "diagnostic_id": "uuid-string",
        "user_id": "uuid-string" (optional)
    }
    
    Response:
    {
        "ical_url": "data:text/calendar;charset=utf-8,BEGIN:VCALENDAR...",
        "file_name": "plan_accion_90dias.ics"
    }
    """
    
    diagnostic_id = payload.get("diagnostic_id")
    user_id = payload.get("user_id", "unknown")
    
    if not diagnostic_id:
        raise HTTPException(status_code=400, detail="diagnostic_id required")
    
    # Generar iCal
    ical_content = generate_action_plan_calendar(diagnostic_id, user_id)
    
    # Codificar como data URL para descarga automática
    ical_encoded = ical_content.replace("\n", "%0A")
    ical_url = f"data:text/calendar;charset=utf-8,{ical_encoded}"
    
    return {
        "ical_url": ical_url,
        "file_name": "plan_accion_90dias.ics",
        "events_count": 4,
        "message": "Tu Plan de Acción está listo. Abre en tu calendario para sincronizar."
    }


@router.get("/download/{diagnostic_id}")
async def download_ical(diagnostic_id: str):
    """
    GET /api/v1/calendar-sync/download/{diagnostic_id}
    
    Descarga directa del archivo .ics (alternativa a data URL si falla).
    """
    
    ical_content = generate_action_plan_calendar(diagnostic_id, "")
    
    return {
        "content": ical_content,
        "headers": {
            "Content-Type": "text/calendar; charset=utf-8",
            "Content-Disposition": f'attachment; filename="plan_accion_{diagnostic_id}.ics"'
        }
    }
