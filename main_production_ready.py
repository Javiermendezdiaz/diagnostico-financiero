#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ITAP Tier System — Backend Profesional FastAPI
Motor adaptativo de 500 preguntas + análisis PDF
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
import os
import json
import stripe
from dotenv import load_dotenv
import hashlib

load_dotenv()

# ==================== CONFIG ====================
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./itap.db')
STRIPE_KEY = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = STRIPE_KEY

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI(title="ITAP Backend", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STRIPE_LINKS = {
    1: "https://buy.stripe.com/6oUbJ0dyd38Tgyw7ndfAc01",
    2: "https://buy.stripe.com/eVqfZg79P6l55TS9vlfAc02",
    3: "https://buy.stripe.com/eVq8wO9hXaBl2HGePFfAc00"
}

TIER_CONFIG = {
    1: {"name": "Diagnóstico Rápido", "questions": 100, "open": 20, "price": 19},
    2: {"name": "Informe Avanzado", "questions": 200, "open": 20, "price": 39},
    3: {"name": "Análisis Supremo Pareja", "questions": 200, "open": 20, "price": 54}
}

# ==================== MODELOS ORM ====================
class EvaluationModel(Base):
    __tablename__ = 'evaluations'
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    tier = Column(Integer, nullable=False)
    session_id = Column(String, unique=True, nullable=False)
    answers = Column(JSON, default={})
    open_answers = Column(JSON, default={})
    score = Column(Integer, default=0)
    profile = Column(String, default="")
    is_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== SCHEMAS ====================
class StartEvaluationRequest(BaseModel):
    email: str
    tier: int

class AnswerRequest(BaseModel):
    session_id: str
    question_id: int
    answer_value: int

class OpenAnswerRequest(BaseModel):
    session_id: str
    question_id: int
    answer_text: str

class CompleteEvaluationRequest(BaseModel):
    session_id: str

# ==================== BANCO DE 500 PREGUNTAS REALES ====================
PREGUNTAS_CERRADAS = [
  {
    "id": 1,
    "categoria": "burnout",
    "pregunta": "¿Cómo te sientes físicamente al revisar tu cuenta bancaria?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tranquilidad, todo bajo control",
        "score": 0
      },
      {
        "texto": "Neutral, es solo una herramienta",
        "score": 25
      },
      {
        "texto": "Cierta ansiedad o incomodidad",
        "score": 50
      },
      {
        "texto": "Pánico, evito mirar",
        "score": 100
      }
    ]
  },
  {
    "id": 2,
    "categoria": "burnout",
    "pregunta": "En una escala del 1-10, ¿cuánto miedo te da una crisis económica repentina?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "1-3: No me preocupa",
        "score": 0
      },
      {
        "texto": "4-5: Algo de inquietud",
        "score": 35
      },
      {
        "texto": "6-7: Bastante miedo",
        "score": 65
      },
      {
        "texto": "8-10: Terror absoluto",
        "score": 100
      }
    ]
  },
  {
    "id": 3,
    "categoria": "burnout",
    "pregunta": "¿Cuántas veces por semana te despiertas con ansiedad relacionada con dinero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "1-2 veces",
        "score": 25
      },
      {
        "texto": "3-4 veces",
        "score": 50
      },
      {
        "texto": "Todos los días",
        "score": 100
      }
    ]
  },
  {
    "id": 4,
    "categoria": "burnout",
    "pregunta": "¿Discutes dinero frecuentemente con tu pareja/familia de forma tensa?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca, comunicación sana",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 30
      },
      {
        "texto": "Regularmente",
        "score": 65
      },
      {
        "texto": "Es fuente constante de conflicto",
        "score": 100
      }
    ]
  },
  {
    "id": 5,
    "categoria": "burnout",
    "pregunta": "¿Sientes que trabajas solo para pagar deudas y gastos, sin libertad?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, disfruto mi trabajo y tengo control",
        "score": 0
      },
      {
        "texto": "A veces siento presión",
        "score": 35
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Siempre, es una prisión",
        "score": 100
      }
    ]
  },
  {
    "id": 6,
    "categoria": "burnout",
    "pregunta": "¿Has postergado decisiones financieras importantes por miedo o incertidumbre?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Rara vez, tomo decisiones",
        "score": 0
      },
      {
        "texto": "A veces",
        "score": 25
      },
      {
        "texto": "Frecuentemente",
        "score": 60
      },
      {
        "texto": "Constantemente, estoy paralizado",
        "score": 100
      }
    ]
  },
  {
    "id": 7,
    "categoria": "burnout",
    "pregunta": "¿Cuánto tiempo al mes dedicas a pensar/preocuparte por dinero de forma improductiva?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-2 horas",
        "score": 0
      },
      {
        "texto": "3-8 horas",
        "score": 30
      },
      {
        "texto": "9-20 horas",
        "score": 65
      },
      {
        "texto": "Más de 20 horas (pensamiento invasivo)",
        "score": 100
      }
    ]
  },
  {
    "id": 8,
    "categoria": "burnout",
    "pregunta": "¿Evitas hablar de temas financieros o ahorros en reuniones sociales?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, hablo naturalmente",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 20
      },
      {
        "texto": "Frecuentemente",
        "score": 55
      },
      {
        "texto": "Siempre, me avergüenza",
        "score": 100
      }
    ]
  },
  {
    "id": 9,
    "categoria": "burnout",
    "pregunta": "¿Tu salud física ha empeorado relacionada con estrés financiero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, mi salud es buena",
        "score": 0
      },
      {
        "texto": "Leve impacto",
        "score": 30
      },
      {
        "texto": "Impacto notable",
        "score": 65
      },
      {
        "texto": "Problema serio",
        "score": 100
      }
    ]
  },
  {
    "id": 10,
    "categoria": "burnout",
    "pregunta": "Si heredaras 100.000 € mañana, ¿qué sentirías primero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Alegría y oportunidad",
        "score": 0
      },
      {
        "texto": "Alivio",
        "score": 25
      },
      {
        "texto": "Pánico sobre qué hacer",
        "score": 60
      },
      {
        "texto": "Miedo de perderlo o que sea una trampa",
        "score": 100
      }
    ]
  },
  {
    "id": 11,
    "categoria": "burnout",
    "pregunta": "¿Has considerado abandonar tu trabajo en los últimos 6 meses por dinero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 30
      },
      {
        "texto": "Regularmente lo pienso",
        "score": 70
      },
      {
        "texto": "Es mi obsesión",
        "score": 100
      }
    ]
  },
  {
    "id": 12,
    "categoria": "burnout",
    "pregunta": "¿Sacrificas sueño, ejercicio o relaciones por dinero/trabajo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, protejo esas áreas",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 35
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Es el precio que pago",
        "score": 100
      }
    ]
  },
  {
    "id": 13,
    "categoria": "burnout",
    "pregunta": "¿Te genera culpa gastar dinero en ti mismo aunque puedas permitirlo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, disfruto sin culpa",
        "score": 0
      },
      {
        "texto": "A veces siento culpa",
        "score": 35
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Siempre",
        "score": 100
      }
    ]
  },
  {
    "id": 14,
    "categoria": "burnout",
    "pregunta": "¿Has mentido sobre tu situación financiera a alguien cercano?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Raramente",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 30
      },
      {
        "texto": "Regularmente",
        "score": 65
      },
      {
        "texto": "Es una costumbre",
        "score": 100
      }
    ]
  },
  {
    "id": 15,
    "categoria": "burnout",
    "pregunta": "¿Has sufrido ataques de pánico o ansiedad severa por dinero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Una o dos veces",
        "score": 40
      },
      {
        "texto": "Varios episodios",
        "score": 75
      },
      {
        "texto": "Regularmente",
        "score": 100
      }
    ]
  },
  {
    "id": 16,
    "categoria": "burnout",
    "pregunta": "¿Tu relación con dinero es reactiva (crisis) o proactiva (plan)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Proactiva, planeo",
        "score": 0
      },
      {
        "texto": "Mayormente proactiva",
        "score": 25
      },
      {
        "texto": "Mitad y mitad",
        "score": 50
      },
      {
        "texto": "Completamente reactiva",
        "score": 100
      }
    ]
  },
  {
    "id": 17,
    "categoria": "burnout",
    "pregunta": "¿Tu valor como persona está conectado a tu dinero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, son independientes",
        "score": 0
      },
      {
        "texto": "Algo conectado",
        "score": 35
      },
      {
        "texto": "Bastante conectado",
        "score": 70
      },
      {
        "texto": "Completamente",
        "score": 100
      }
    ]
  },
  {
    "id": 18,
    "categoria": "burnout",
    "pregunta": "¿Cada mes es una lucha o está resuelto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Resuelto, respiro fácil",
        "score": 0
      },
      {
        "texto": "Más o menos, con sustos",
        "score": 35
      },
      {
        "texto": "Lucha constante",
        "score": 70
      },
      {
        "texto": "Caos total",
        "score": 100
      }
    ]
  },
  {
    "id": 19,
    "categoria": "burnout",
    "pregunta": "¿Has considerado terapia por estrés financiero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Ya estoy en terapia",
        "score": 100
      },
      {
        "texto": "Lo he considerado",
        "score": 60
      },
      {
        "texto": "Nunca lo consideré",
        "score": 20
      },
      {
        "texto": "No lo necesito",
        "score": 0
      }
    ]
  },
  {
    "id": 20,
    "categoria": "burnout",
    "pregunta": "¿Tienes fondo de emergencia de 3-6 meses?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, bien financiado",
        "score": 100
      },
      {
        "texto": "Parcialmente",
        "score": 60
      },
      {
        "texto": "Muy poco",
        "score": 25
      },
      {
        "texto": "No tengo",
        "score": 0
      }
    ]
  },
  {
    "id": 21,
    "categoria": "burnout",
    "pregunta": "¿Evitas revisar facturas o correos bancarios?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, los abro todos",
        "score": 0
      },
      {
        "texto": "A veces",
        "score": 35
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Siempre",
        "score": 100
      }
    ]
  },
  {
    "id": 22,
    "categoria": "burnout",
    "pregunta": "¿Sientes que nunca mejorará tu situación?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo esperanza",
        "score": 0
      },
      {
        "texto": "A veces pienso eso",
        "score": 35
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Es una conclusión",
        "score": 100
      }
    ]
  },
  {
    "id": 23,
    "categoria": "burnout",
    "pregunta": "¿Compartes dinero con pareja/familia causando conflicto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No hay conflicto",
        "score": 0
      },
      {
        "texto": "Ocasional tensión",
        "score": 35
      },
      {
        "texto": "Conflicto frecuente",
        "score": 70
      },
      {
        "texto": "Es destructivo",
        "score": 100
      }
    ]
  },
  {
    "id": 24,
    "categoria": "burnout",
    "pregunta": "¿Cuándo fue la última vez que revisaste voluntariamente tus gastos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Esta semana",
        "score": 0
      },
      {
        "texto": "Este mes",
        "score": 20
      },
      {
        "texto": "Hace 3-6 meses",
        "score": 50
      },
      {
        "texto": "Más de un año",
        "score": 100
      }
    ]
  },
  {
    "id": 25,
    "categoria": "burnout",
    "pregunta": "¿Tu edad vs ahorros está en línea con lo 'normal'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, bien para mi edad",
        "score": 100
      },
      {
        "texto": "Más o menos",
        "score": 60
      },
      {
        "texto": "Por debajo",
        "score": 25
      },
      {
        "texto": "Muy por debajo",
        "score": 0
      }
    ]
  },
  {
    "id": 26,
    "categoria": "burnout",
    "pregunta": "¿Hablabas de dinero con tus padres? ¿Era tabú?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Abierto y sano",
        "score": 0
      },
      {
        "texto": "Se hablaba ocasionalmente",
        "score": 30
      },
      {
        "texto": "Era incómodo",
        "score": 65
      },
      {
        "texto": "Era absoluto tabú",
        "score": 100
      }
    ]
  },
  {
    "id": 27,
    "categoria": "burnout",
    "pregunta": "¿Trabajas extra horas solo por dinero, no por pasión?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, trabajo me apasiona",
        "score": 0
      },
      {
        "texto": "Trabajo es sustancia, pasión es secundaria",
        "score": 40
      },
      {
        "texto": "Puro dinero, ninguna pasión",
        "score": 80
      },
      {
        "texto": "Odio mi trabajo pero necesito dinero",
        "score": 100
      }
    ]
  },
  {
    "id": 28,
    "categoria": "burnout",
    "pregunta": "¿Has tenido deuda de consumo que no podías pagar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Una vez, hace años",
        "score": 30
      },
      {
        "texto": "Varias veces",
        "score": 70
      },
      {
        "texto": "Actualmente",
        "score": 100
      }
    ]
  },
  {
    "id": 29,
    "categoria": "burnout",
    "pregunta": "¿Gastar dinero en ti causa automáticamente culpa?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, es natural",
        "score": 0
      },
      {
        "texto": "A veces",
        "score": 25
      },
      {
        "texto": "Casi siempre",
        "score": 70
      },
      {
        "texto": "Siempre",
        "score": 100
      }
    ]
  },
  {
    "id": 30,
    "categoria": "burnout",
    "pregunta": "¿Qué score darías a tu salud mental financiera (1-10)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "1-3",
        "score": 0
      },
      {
        "texto": "4-5",
        "score": 25
      },
      {
        "texto": "6-7",
        "score": 50
      },
      {
        "texto": "8-10",
        "score": 100
      }
    ]
  },
  {
    "id": 31,
    "categoria": "burnout",
    "pregunta": "¿Has omitido gastos importantes por negación?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 30
      },
      {
        "texto": "Regularmente",
        "score": 70
      },
      {
        "texto": "Es mi patrón",
        "score": 100
      }
    ]
  },
  {
    "id": 32,
    "categoria": "burnout",
    "pregunta": "¿Te avergüenza tu situación financiera actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, la acepto",
        "score": 0
      },
      {
        "texto": "Un poco",
        "score": 30
      },
      {
        "texto": "Bastante",
        "score": 70
      },
      {
        "texto": "Profundamente",
        "score": 100
      }
    ]
  },
  {
    "id": 33,
    "categoria": "burnout",
    "pregunta": "¿Familia/pareja saben verdad sobre tus finanzas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente transparente",
        "score": 0
      },
      {
        "texto": "Mayoría saben",
        "score": 25
      },
      {
        "texto": "Pocos saben",
        "score": 70
      },
      {
        "texto": "Nadie sabe",
        "score": 100
      }
    ]
  },
  {
    "id": 34,
    "categoria": "burnout",
    "pregunta": "¿Dinero te quita sueño literal (insomnio)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 25
      },
      {
        "texto": "Regularmente",
        "score": 70
      },
      {
        "texto": "Casi cada noche",
        "score": 100
      }
    ]
  },
  {
    "id": 35,
    "categoria": "burnout",
    "pregunta": "¿Tu estrés financiero afecta tu salud física?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No noto conexión",
        "score": 0
      },
      {
        "texto": "Algo de tensión",
        "score": 25
      },
      {
        "texto": "Síntomas claros",
        "score": 70
      },
      {
        "texto": "Afecciones serias",
        "score": 100
      }
    ]
  },
  {
    "id": 36,
    "categoria": "burnout",
    "pregunta": "¿Comparas tu riqueza con otros obsesivamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Rara vez pienso en ello",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 25
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Constantemente",
        "score": 100
      }
    ]
  },
  {
    "id": 37,
    "categoria": "burnout",
    "pregunta": "¿Dinero causa ansiedad social (evitas eventos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, voy libremente",
        "score": 0
      },
      {
        "texto": "A veces evito",
        "score": 30
      },
      {
        "texto": "Frecuentemente evito",
        "score": 70
      },
      {
        "texto": "Evito la mayoría",
        "score": 100
      }
    ]
  },
  {
    "id": 38,
    "categoria": "burnout",
    "pregunta": "¿Has usado drogas/alcohol para escapar estrés financiero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 40
      },
      {
        "texto": "Regularmente",
        "score": 75
      },
      {
        "texto": "Es mi mecanismo",
        "score": 100
      }
    ]
  },
  {
    "id": 39,
    "categoria": "burnout",
    "pregunta": "¿Eres procrastinador activo con asuntos financieros?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, los atiendo rápido",
        "score": 0
      },
      {
        "texto": "A veces demoro",
        "score": 25
      },
      {
        "texto": "Regularmente demoro",
        "score": 70
      },
      {
        "texto": "Siempre demoro",
        "score": 100
      }
    ]
  },
  {
    "id": 40,
    "categoria": "burnout",
    "pregunta": "¿Te sientes atrapado sin salida?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Veo opciones y esperanza",
        "score": 0
      },
      {
        "texto": "Hay algún camino",
        "score": 30
      },
      {
        "texto": "Pocas opciones",
        "score": 70
      },
      {
        "texto": "Completamente atrapado",
        "score": 100
      }
    ]
  },
  {
    "id": 41,
    "categoria": "burnout",
    "pregunta": "¿Has hablado con un terapeuta/coach sobre dinero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, regularmente",
        "score": 100
      },
      {
        "texto": "Sí, ocasionalmente",
        "score": 60
      },
      {
        "texto": "Nunca",
        "score": 25
      },
      {
        "texto": "Nunca y no quiero",
        "score": 0
      }
    ]
  },
  {
    "id": 42,
    "categoria": "burnout",
    "pregunta": "¿Tu pareja/familia comparte tus preocupaciones financieras?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, conectamos bien",
        "score": 100
      },
      {
        "texto": "Más o menos",
        "score": 60
      },
      {
        "texto": "No mucho",
        "score": 25
      },
      {
        "texto": "No, evito el tema",
        "score": 0
      }
    ]
  },
  {
    "id": 43,
    "categoria": "burnout",
    "pregunta": "¿Tienes amigos con situación financiera similar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, muchos",
        "score": 100
      },
      {
        "texto": "Algunos",
        "score": 60
      },
      {
        "texto": "Pocos",
        "score": 25
      },
      {
        "texto": "Ninguno",
        "score": 0
      }
    ]
  },
  {
    "id": 44,
    "categoria": "burnout",
    "pregunta": "¿Sientes validación si tienes más dinero que otros?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, validación viene de dentro",
        "score": 0
      },
      {
        "texto": "Un poco",
        "score": 30
      },
      {
        "texto": "Bastante",
        "score": 70
      },
      {
        "texto": "Totalmente",
        "score": 100
      }
    ]
  },
  {
    "id": 45,
    "categoria": "burnout",
    "pregunta": "¿Necesitas dinero para sentirte sexy/atractivo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, es independiente",
        "score": 0
      },
      {
        "texto": "Ayuda un poco",
        "score": 25
      },
      {
        "texto": "Bastante",
        "score": 70
      },
      {
        "texto": "Totalmente",
        "score": 100
      }
    ]
  },
  {
    "id": 46,
    "categoria": "burnout",
    "pregunta": "¿Si perdieras dinero mañana, quién serías?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Yo mismo, dinero no define",
        "score": 0
      },
      {
        "texto": "Algo diferente pero resiliente",
        "score": 30
      },
      {
        "texto": "Bastante diferente",
        "score": 70
      },
      {
        "texto": "Nadie, sería el fin",
        "score": 100
      }
    ]
  },
  {
    "id": 47,
    "categoria": "burnout",
    "pregunta": "¿Dinero es temas 1 en discusiones con pareja?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, hay otros temas",
        "score": 0
      },
      {
        "texto": "A veces",
        "score": 25
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Siempre",
        "score": 100
      }
    ]
  },
  {
    "id": 48,
    "categoria": "burnout",
    "pregunta": "¿Tu ansiedad financiera ha aumentado últimamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, está estable",
        "score": 0
      },
      {
        "texto": "Un poco",
        "score": 25
      },
      {
        "texto": "Bastante",
        "score": 70
      },
      {
        "texto": "Dramáticamente",
        "score": 100
      }
    ]
  },
  {
    "id": 49,
    "categoria": "burnout",
    "pregunta": "¿Dinero controla tus decisiones de vida importantes?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, decido libremente",
        "score": 0
      },
      {
        "texto": "Influye algo",
        "score": 30
      },
      {
        "texto": "Influye bastante",
        "score": 70
      },
      {
        "texto": "Controla todo",
        "score": 100
      }
    ]
  },
  {
    "id": 50,
    "categoria": "burnout",
    "pregunta": "¿Qué harías si tuvieras dinero infinito?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Seguiría como ahora (vida es buena)",
        "score": 0
      },
      {
        "texto": "Cambiaría poco",
        "score": 25
      },
      {
        "texto": "Cambiaría bastante",
        "score": 70
      },
      {
        "texto": "Sería completamente diferente",
        "score": 100
      }
    ]
  },
  {
    "id": 51,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es tu gasto mensual MÍNIMO para vivir (sin lujos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 0
      },
      {
        "texto": "N/A",
        "score": 20
      },
      {
        "texto": "N/A",
        "score": 40
      },
      {
        "texto": "N/A",
        "score": 60
      }
    ]
  },
  {
    "id": 52,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es tu ingreso mensual neto actual (después de impuestos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 0
      },
      {
        "texto": "N/A",
        "score": 20
      },
      {
        "texto": "N/A",
        "score": 40
      },
      {
        "texto": "N/A",
        "score": 60
      }
    ]
  },
  {
    "id": 53,
    "categoria": "numero_fi",
    "pregunta": "¿Cuánto logras ahorrar mensualmente de forma realista?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 0
      },
      {
        "texto": "N/A",
        "score": 25
      },
      {
        "texto": "N/A",
        "score": 50
      },
      {
        "texto": "N/A",
        "score": 75
      }
    ]
  },
  {
    "id": 54,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es el patrimonio que tienes acumulado AHORA (todo incluido)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 0
      },
      {
        "texto": "N/A",
        "score": 20
      },
      {
        "texto": "N/A",
        "score": 40
      },
      {
        "texto": "N/A",
        "score": 60
      }
    ]
  },
  {
    "id": 55,
    "categoria": "numero_fi",
    "pregunta": "¿A qué rentabilidad anual esperas que crezca tu dinero si lo inviertes?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-2% (cuentas seguras)",
        "score": 0
      },
      {
        "texto": "3-5% (bonos/mixto)",
        "score": 25
      },
      {
        "texto": "6-8% (histórico bolsa)",
        "score": 60
      },
      {
        "texto": "9%+ (muy optimista)",
        "score": 100
      }
    ]
  },
  {
    "id": 56,
    "categoria": "numero_fi",
    "pregunta": "¿En cuántos años te gustaría lograr la libertad financiera?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "5 años o menos",
        "score": 100
      },
      {
        "texto": "10 años",
        "score": 75
      },
      {
        "texto": "20 años",
        "score": 50
      },
      {
        "texto": "30+ años",
        "score": 0
      }
    ]
  },
  {
    "id": 57,
    "categoria": "numero_fi",
    "pregunta": "¿Tienes ingresos pasivos o alternativos además de tu trabajo principal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, solo nómina",
        "score": 0
      },
      {
        "texto": "Pequeño ingreso pasivo (<10% total)",
        "score": 30
      },
      {
        "texto": "Ingreso moderado (10-30% total)",
        "score": 60
      },
      {
        "texto": "Ingresos significativos (>30% total)",
        "score": 100
      }
    ]
  },
  {
    "id": 58,
    "categoria": "numero_fi",
    "pregunta": "Si tu ingreso se redujera un 50%, ¿podrías mantener tu estilo de vida actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin problema",
        "score": 100
      },
      {
        "texto": "Con ajustes menores",
        "score": 60
      },
      {
        "texto": "Tendría que cambiar significativamente",
        "score": 25
      },
      {
        "texto": "Sería una crisis",
        "score": 0
      }
    ]
  },
  {
    "id": 59,
    "categoria": "numero_fi",
    "pregunta": "¿Conoces exactamente cuánto necesitas para jubilarte cómodamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, he hecho cálculos",
        "score": 100
      },
      {
        "texto": "Tengo una idea aproximada",
        "score": 50
      },
      {
        "texto": "No sé, pero me preocupa",
        "score": 25
      },
      {
        "texto": "No tengo ni idea",
        "score": 0
      }
    ]
  },
  {
    "id": 60,
    "categoria": "numero_fi",
    "pregunta": "¿Qué edad tienes?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "20-30 años",
        "score": 100
      },
      {
        "texto": "31-40 años",
        "score": 80
      },
      {
        "texto": "41-50 años",
        "score": 60
      },
      {
        "texto": "51-60 años",
        "score": 30
      }
    ]
  },
  {
    "id": 61,
    "categoria": "numero_fi",
    "pregunta": "¿Tienes un número exacto de tu patrimonio neto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, actualizado",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 60
      },
      {
        "texto": "Idea vaga",
        "score": 25
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 62,
    "categoria": "numero_fi",
    "pregunta": "¿Sabes tu FI number (dinero necesario para retirarte)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Exacto",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 60
      },
      {
        "texto": "Vagamente",
        "score": 25
      },
      {
        "texto": "No lo sé",
        "score": 0
      }
    ]
  },
  {
    "id": 63,
    "categoria": "numero_fi",
    "pregunta": "¿A qué edad quieres retirarte?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo plan claro",
        "score": 100
      },
      {
        "texto": "Idea general",
        "score": 60
      },
      {
        "texto": "No lo sé",
        "score": 25
      },
      {
        "texto": "Nunca voy a retirarme",
        "score": 0
      }
    ]
  },
  {
    "id": 64,
    "categoria": "numero_fi",
    "pregunta": "¿Cuántas veces por año revisa tu patrimonio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mensualmente",
        "score": 100
      },
      {
        "texto": "Trimestralmente",
        "score": 75
      },
      {
        "texto": "Anualmente",
        "score": 40
      },
      {
        "texto": "Nunca",
        "score": 0
      }
    ]
  },
  {
    "id": 65,
    "categoria": "numero_fi",
    "pregunta": "¿Conoces tu SWR (tasa de retiro seguro)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, la aplico",
        "score": 100
      },
      {
        "texto": "La conozco",
        "score": 60
      },
      {
        "texto": "He oído",
        "score": 25
      },
      {
        "texto": "No sé qué es",
        "score": 0
      }
    ]
  },
  {
    "id": 66,
    "categoria": "numero_fi",
    "pregunta": "¿Cuánto ahorras mensualmente en %?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Más del 30%",
        "score": 100
      },
      {
        "texto": "20-30%",
        "score": 75
      },
      {
        "texto": "10-20%",
        "score": 40
      },
      {
        "texto": "Menos del 10%",
        "score": 0
      }
    ]
  },
  {
    "id": 67,
    "categoria": "numero_fi",
    "pregunta": "¿Cuántos años hasta FI si mantienes velocidad actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-5 años",
        "score": 100
      },
      {
        "texto": "5-10 años",
        "score": 75
      },
      {
        "texto": "10-20 años",
        "score": 40
      },
      {
        "texto": "Más de 20 años o nunca",
        "score": 0
      }
    ]
  },
  {
    "id": 68,
    "categoria": "numero_fi",
    "pregunta": "¿Sabes tu expense ratio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Exacto",
        "score": 100
      },
      {
        "texto": "Aproximado",
        "score": 60
      },
      {
        "texto": "Idea vaga",
        "score": 25
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 69,
    "categoria": "numero_fi",
    "pregunta": "¿Has modelado scenarios (recesión, desempleo)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, regularmente",
        "score": 100
      },
      {
        "texto": "Ocasionalmente",
        "score": 60
      },
      {
        "texto": "Una vez",
        "score": 25
      },
      {
        "texto": "Nunca",
        "score": 0
      }
    ]
  },
  {
    "id": 70,
    "categoria": "numero_fi",
    "pregunta": "¿Confías en tus números financieros?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente",
        "score": 100
      },
      {
        "texto": "Mayormente",
        "score": 70
      },
      {
        "texto": "Algo",
        "score": 35
      },
      {
        "texto": "No confío",
        "score": 0
      }
    ]
  },
  {
    "id": 71,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es tu asset allocation (stocks/bonds/cash)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo estrategia clara",
        "score": 100
      },
      {
        "texto": "Tengo idea",
        "score": 60
      },
      {
        "texto": "No lo sé",
        "score": 25
      },
      {
        "texto": "No tengo activos",
        "score": 0
      }
    ]
  },
  {
    "id": 72,
    "categoria": "numero_fi",
    "pregunta": "¿Sabes tu inflation-adjusted FI number?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, lo ajusto anualmente",
        "score": 100
      },
      {
        "texto": "Lo he calculado",
        "score": 60
      },
      {
        "texto": "Vagamente",
        "score": 25
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 73,
    "categoria": "numero_fi",
    "pregunta": "¿Cuántos meses de expenses tienes en cash?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "6+ meses",
        "score": 100
      },
      {
        "texto": "3-6 meses",
        "score": 75
      },
      {
        "texto": "1-3 meses",
        "score": 40
      },
      {
        "texto": "Menos de 1 mes",
        "score": 0
      }
    ]
  },
  {
    "id": 74,
    "categoria": "numero_fi",
    "pregunta": "¿Qué % de ingresos va a impuestos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sé exacto",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 60
      },
      {
        "texto": "Idea vaga",
        "score": 25
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 75,
    "categoria": "numero_fi",
    "pregunta": "¿Tienes plan de reducción de impuestos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sofisticado",
        "score": 100
      },
      {
        "texto": "Sí, básico",
        "score": 60
      },
      {
        "texto": "Ninguno",
        "score": 0
      },
      {
        "texto": "Tengo miedo de IRS",
        "score": 0
      }
    ]
  },
  {
    "id": 76,
    "categoria": "numero_fi",
    "pregunta": "¿Cuándo alcanzarás FI si todo va bien?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo fecha exacta",
        "score": 100
      },
      {
        "texto": "Tengo rango",
        "score": 60
      },
      {
        "texto": "Esperanza vagas",
        "score": 25
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 77,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es tu FI %? (patrimonio/gastos anuales x 25)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Más del 80%",
        "score": 100
      },
      {
        "texto": "50-80%",
        "score": 75
      },
      {
        "texto": "20-50%",
        "score": 40
      },
      {
        "texto": "Menos del 20%",
        "score": 0
      }
    ]
  },
  {
    "id": 78,
    "categoria": "numero_fi",
    "pregunta": "¿Conoces tu FIRE ratio (ahorros/gastos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, lo tracking",
        "score": 100
      },
      {
        "texto": "Lo conozco",
        "score": 60
      },
      {
        "texto": "Lo he calculado",
        "score": 25
      },
      {
        "texto": "No lo sé",
        "score": 0
      }
    ]
  },
  {
    "id": 79,
    "categoria": "numero_fi",
    "pregunta": "¿Tienes plan de ingresos pasivos post-retiro?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, detallado",
        "score": 100
      },
      {
        "texto": "Idea general",
        "score": 60
      },
      {
        "texto": "Confío en inversiones",
        "score": 35
      },
      {
        "texto": "No tengo plan",
        "score": 0
      }
    ]
  },
  {
    "id": 80,
    "categoria": "numero_fi",
    "pregunta": "¿Cuánto tiempo retienes datos financieros?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Años, bien archivado",
        "score": 100
      },
      {
        "texto": "Algún tiempo",
        "score": 60
      },
      {
        "texto": "Recuerdos vagos",
        "score": 25
      },
      {
        "texto": "No lo guardo",
        "score": 0
      }
    ]
  },
  {
    "id": 81,
    "categoria": "numero_fi",
    "pregunta": "¿Has calculado tu coast FI number?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí y la aplico",
        "score": 100
      },
      {
        "texto": "La conozco",
        "score": 60
      },
      {
        "texto": "He oído",
        "score": 25
      },
      {
        "texto": "Qué es eso?",
        "score": 0
      }
    ]
  },
  {
    "id": 82,
    "categoria": "numero_fi",
    "pregunta": "¿Sabes exactamente qué pasaría con tus inversiones en recesión?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, lo he modelado",
        "score": 100
      },
      {
        "texto": "Tengo idea",
        "score": 60
      },
      {
        "texto": "Esperanza",
        "score": 25
      },
      {
        "texto": "No lo sé",
        "score": 0
      }
    ]
  },
  {
    "id": 83,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es tu income / FI number ratio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sé el número exacto",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 60
      },
      {
        "texto": "Idea vaga",
        "score": 25
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 84,
    "categoria": "numero_fi",
    "pregunta": "¿Revisas inversiones más de 4x al año?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca reviso (buy & hold)",
        "score": 100
      },
      {
        "texto": "1-2 veces año",
        "score": 75
      },
      {
        "texto": "4-12 veces año",
        "score": 40
      },
      {
        "texto": "Diariamente",
        "score": 0
      }
    ]
  },
  {
    "id": 85,
    "categoria": "numero_fi",
    "pregunta": "¿Sabes tu withdrawal rate si retiraras hoy?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Exacto",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 60
      },
      {
        "texto": "No lo he calculado",
        "score": 0
      },
      {
        "texto": "No tengo patrimonio",
        "score": 0
      }
    ]
  },
  {
    "id": 86,
    "categoria": "numero_fi",
    "pregunta": "¿Dinero está en lugares alineados con FI plan?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente alineado",
        "score": 100
      },
      {
        "texto": "Mayoría alineado",
        "score": 70
      },
      {
        "texto": "Parcialmente",
        "score": 35
      },
      {
        "texto": "Caótico",
        "score": 0
      }
    ]
  },
  {
    "id": 87,
    "categoria": "numero_fi",
    "pregunta": "¿Tienes índices de retorno esperado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, ajustado a inflation",
        "score": 100
      },
      {
        "texto": "Tengo números",
        "score": 60
      },
      {
        "texto": "Vago",
        "score": 25
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 88,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es tu spending pattern? (mensual/anual)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Perfectamente predecible",
        "score": 100
      },
      {
        "texto": "Mayormente predecible",
        "score": 70
      },
      {
        "texto": "Bastante variable",
        "score": 35
      },
      {
        "texto": "Caótico",
        "score": 0
      }
    ]
  },
  {
    "id": 89,
    "categoria": "numero_fi",
    "pregunta": "¿Cuándo fue última revisión seria de números?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Este mes",
        "score": 100
      },
      {
        "texto": "Este trimestre",
        "score": 75
      },
      {
        "texto": "Este año",
        "score": 40
      },
      {
        "texto": "Hace años / nunca",
        "score": 0
      }
    ]
  },
  {
    "id": 90,
    "categoria": "numero_fi",
    "pregunta": "¿Tu FI plan es flexible o rígido?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Flexible, adapto constantemente",
        "score": 100
      },
      {
        "texto": "Bastante flexible",
        "score": 70
      },
      {
        "texto": "Algo rígido",
        "score": 35
      },
      {
        "texto": "Totalmente rígido",
        "score": 0
      }
    ]
  },
  {
    "id": 91,
    "categoria": "numero_fi",
    "pregunta": "¿Sabes el P/E ratio de tu cartera?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, lo monitoreo",
        "score": 100
      },
      {
        "texto": "Lo conozco",
        "score": 60
      },
      {
        "texto": "Vago",
        "score": 25
      },
      {
        "texto": "Qué es?",
        "score": 0
      }
    ]
  },
  {
    "id": 92,
    "categoria": "numero_fi",
    "pregunta": "¿Dinero en acciones % total patrimonio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sé exacto",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 60
      },
      {
        "texto": "Idea vaga",
        "score": 25
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 93,
    "categoria": "numero_fi",
    "pregunta": "¿Confías que alcanzarás FI en plan?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente",
        "score": 100
      },
      {
        "texto": "Mayormente",
        "score": 70
      },
      {
        "texto": "Algo escéptico",
        "score": 35
      },
      {
        "texto": "No creo",
        "score": 0
      }
    ]
  },
  {
    "id": 94,
    "categoria": "numero_fi",
    "pregunta": "¿Cambiarías estrategia si matemática no cuadrara?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, serían realista",
        "score": 100
      },
      {
        "texto": "Probablemente",
        "score": 70
      },
      {
        "texto": "Quizás",
        "score": 35
      },
      {
        "texto": "Esperaría milagro",
        "score": 0
      }
    ]
  },
  {
    "id": 95,
    "categoria": "numero_fi",
    "pregunta": "¿Tus números soportan los deseos de vida?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Perfectamente",
        "score": 100
      },
      {
        "texto": "Mayormente",
        "score": 70
      },
      {
        "texto": "Parcialmente",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 96,
    "categoria": "numero_fi",
    "pregunta": "¿Cuál es tu compound annual growth rate (CAGR)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sé exacto",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 60
      },
      {
        "texto": "Idea vaga",
        "score": 25
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 97,
    "categoria": "numero_fi",
    "pregunta": "¿Números reflejan reality o fantasía?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Reality check continuo",
        "score": 100
      },
      {
        "texto": "Bastante realista",
        "score": 70
      },
      {
        "texto": "Algo optimista",
        "score": 35
      },
      {
        "texto": "Pure fantasy",
        "score": 0
      }
    ]
  },
  {
    "id": 98,
    "categoria": "numero_fi",
    "pregunta": "¿Has backtested tu plan en mercados pasados?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, profundamente",
        "score": 100
      },
      {
        "texto": "Sí, superficialmente",
        "score": 60
      },
      {
        "texto": "No",
        "score": 25
      },
      {
        "texto": "No sé qué es eso",
        "score": 0
      }
    ]
  },
  {
    "id": 99,
    "categoria": "numero_fi",
    "pregunta": "¿Cada número tiene un propósito claro?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Todos conectados",
        "score": 100
      },
      {
        "texto": "Mayoría conectados",
        "score": 70
      },
      {
        "texto": "Algunos sueltos",
        "score": 35
      },
      {
        "texto": "Caótico",
        "score": 0
      }
    ]
  },
  {
    "id": 100,
    "categoria": "numero_fi",
    "pregunta": "¿Calidad de números es suficiente para decisiones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, confío totalmente",
        "score": 100
      },
      {
        "texto": "Mayormente",
        "score": 70
      },
      {
        "texto": "Algo inseguro",
        "score": 35
      },
      {
        "texto": "No confío",
        "score": 0
      }
    ]
  },
  {
    "id": 101,
    "categoria": "stress_test",
    "pregunta": "Escenario A: Te quedas sin trabajo mañana. ¿Cuántos meses sobrevives sin ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-1 mes (crisis inmediata)",
        "score": 100
      },
      {
        "texto": "2-3 meses",
        "score": 70
      },
      {
        "texto": "4-6 meses",
        "score": 50
      },
      {
        "texto": "7-12 meses",
        "score": 30
      }
    ]
  },
  {
    "id": 102,
    "categoria": "stress_test",
    "pregunta": "Escenario B: Tu hipoteca/alquiler sube un 20%. ¿Cómo reaccionarías?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Crisis, no puedo asumir",
        "score": 100
      },
      {
        "texto": "Difícil, tendría que ajustar gastos",
        "score": 60
      },
      {
        "texto": "Complicado pero viable",
        "score": 35
      },
      {
        "texto": "Sin problema",
        "score": 0
      }
    ]
  },
  {
    "id": 103,
    "categoria": "stress_test",
    "pregunta": "Escenario C: Urgencia médica de 5.000 €. ¿De dónde saldrían?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo, sería deuda",
        "score": 100
      },
      {
        "texto": "Tarjeta de crédito",
        "score": 80
      },
      {
        "texto": "Ahorro disponible",
        "score": 40
      },
      {
        "texto": "Sin impacto, tengo fondo de emergencia",
        "score": 0
      }
    ]
  },
  {
    "id": 104,
    "categoria": "stress_test",
    "pregunta": "¿Tienes un fondo de emergencia separado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 100
      },
      {
        "texto": "Sí, pero menos de 1 mes",
        "score": 75
      },
      {
        "texto": "1-3 meses de gastos",
        "score": 50
      },
      {
        "texto": "3-6 meses",
        "score": 25
      }
    ]
  },
  {
    "id": 105,
    "categoria": "stress_test",
    "pregunta": "¿Cómo reaccionarías si la inflación se dispara un 10%?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Pánico, no sé qué hacer",
        "score": 100
      },
      {
        "texto": "Preocupación moderada",
        "score": 60
      },
      {
        "texto": "Ajustaría presupuesto",
        "score": 35
      },
      {
        "texto": "Tengo inversiones inflacionarias",
        "score": 0
      }
    ]
  },
  {
    "id": 106,
    "categoria": "stress_test",
    "pregunta": "¿Tienes dependientes económicos (hijos, padres)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, 1 persona",
        "score": 30
      },
      {
        "texto": "Sí, 2 personas",
        "score": 60
      },
      {
        "texto": "Sí, 3 o más",
        "score": 100
      }
    ]
  },
  {
    "id": 107,
    "categoria": "stress_test",
    "pregunta": "¿Si pierdes fuente de ingresos, tus dependientes quedarían sin educación/vivienda?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, tiene cobertura",
        "score": 0
      },
      {
        "texto": "Parcialmente cubierto",
        "score": 40
      },
      {
        "texto": "Quedarían muy afectados",
        "score": 80
      },
      {
        "texto": "Sería catastrófico",
        "score": 100
      }
    ]
  },
  {
    "id": 108,
    "categoria": "stress_test",
    "pregunta": "¿Tendrías que endeudarte inmediatamente en una crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, tengo ahorros",
        "score": 0
      },
      {
        "texto": "Posiblemente línea de crédito",
        "score": 50
      },
      {
        "texto": "Sí, probablemente",
        "score": 85
      },
      {
        "texto": "Sí, con certeza",
        "score": 100
      }
    ]
  },
  {
    "id": 109,
    "categoria": "stress_test",
    "pregunta": "¿Cómo están diversificadas tus inversiones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Diversificado (acciones, bonos, inmuebles)",
        "score": 0
      },
      {
        "texto": "Parcialmente diversificado",
        "score": 40
      },
      {
        "texto": "Concentrado en 1-2 áreas",
        "score": 70
      },
      {
        "texto": "Todo en un sitio (efectivo o un activo)",
        "score": 100
      }
    ]
  },
  {
    "id": 110,
    "categoria": "stress_test",
    "pregunta": "¿Qué tan probable es que tu fuente actual de ingresos desaparezca?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy improbable (empleado público, sector estable)",
        "score": 0
      },
      {
        "texto": "Poco probable",
        "score": 30
      },
      {
        "texto": "Posible",
        "score": 65
      },
      {
        "texto": "Muy probable (freelance, startup, economía informal)",
        "score": 100
      }
    ]
  },
  {
    "id": 111,
    "categoria": "stress_test",
    "pregunta": "¿Podrías vivir 12 meses sin ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin problema",
        "score": 100
      },
      {
        "texto": "Sí, con ajustes",
        "score": 70
      },
      {
        "texto": "Apretado",
        "score": 35
      },
      {
        "texto": "Imposible",
        "score": 0
      }
    ]
  },
  {
    "id": 112,
    "categoria": "stress_test",
    "pregunta": "¿Qué pasaría si pierdes 50% ingresos mañana?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Manejable con ajustes",
        "score": 100
      },
      {
        "texto": "Complicado pero viable",
        "score": 70
      },
      {
        "texto": "Crisis inmediata",
        "score": 35
      },
      {
        "texto": "Catastrofe",
        "score": 0
      }
    ]
  },
  {
    "id": 113,
    "categoria": "stress_test",
    "pregunta": "¿Tienes ingresos alternativos (skills, network)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Múltiples opciones",
        "score": 100
      },
      {
        "texto": "Algunas opciones",
        "score": 70
      },
      {
        "texto": "Una opción",
        "score": 35
      },
      {
        "texto": "Ninguna",
        "score": 0
      }
    ]
  },
  {
    "id": 114,
    "categoria": "stress_test",
    "pregunta": "¿Cuántos meses sobrevives con emergencia?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "6+ meses",
        "score": 100
      },
      {
        "texto": "3-6 meses",
        "score": 70
      },
      {
        "texto": "1-3 meses",
        "score": 35
      },
      {
        "texto": "Menos de 1",
        "score": 0
      }
    ]
  },
  {
    "id": 115,
    "categoria": "stress_test",
    "pregunta": "¿Podrías reducir gastos en 50% si necesario?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fácilmente",
        "score": 100
      },
      {
        "texto": "Sí, con dolor",
        "score": 70
      },
      {
        "texto": "Algo",
        "score": 35
      },
      {
        "texto": "No podría",
        "score": 0
      }
    ]
  },
  {
    "id": 116,
    "categoria": "stress_test",
    "pregunta": "¿Deuda o obligaciones fijas son factor de riesgo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo",
        "score": 100
      },
      {
        "texto": "Manejable",
        "score": 70
      },
      {
        "texto": "Apretado",
        "score": 35
      },
      {
        "texto": "Riesgo serio",
        "score": 0
      }
    ]
  },
  {
    "id": 117,
    "categoria": "stress_test",
    "pregunta": "¿Cuál sería tu escape plan en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo plan B/C/D claro",
        "score": 100
      },
      {
        "texto": "Tengo idea",
        "score": 70
      },
      {
        "texto": "Algo vago",
        "score": 35
      },
      {
        "texto": "Ningún plan",
        "score": 0
      }
    ]
  },
  {
    "id": 118,
    "categoria": "stress_test",
    "pregunta": "¿Qué score darías a resiliencia financiera (1-10)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "1-3",
        "score": 0
      },
      {
        "texto": "4-5",
        "score": 35
      },
      {
        "texto": "6-7",
        "score": 70
      },
      {
        "texto": "8-10",
        "score": 100
      }
    ]
  },
  {
    "id": 119,
    "categoria": "stress_test",
    "pregunta": "¿Familia puede ayudarte en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin hesitación",
        "score": 100
      },
      {
        "texto": "Quizás",
        "score": 70
      },
      {
        "texto": "Dudoso",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 120,
    "categoria": "stress_test",
    "pregunta": "¿Podrías vivir en lugar más barato rápidamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, facilmente",
        "score": 100
      },
      {
        "texto": "Sí, con esfuerzo",
        "score": 70
      },
      {
        "texto": "Sí, pero lento",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 121,
    "categoria": "stress_test",
    "pregunta": "¿Has experimentado desempleo o crisis antes?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, superé fácilmente",
        "score": 100
      },
      {
        "texto": "Sí, fue difícil",
        "score": 70
      },
      {
        "texto": "Sí, fue catastrófico",
        "score": 35
      },
      {
        "texto": "Nunca",
        "score": 0
      }
    ]
  },
  {
    "id": 122,
    "categoria": "stress_test",
    "pregunta": "¿Tienes relaciones/network que apoyen en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Red fuerte",
        "score": 100
      },
      {
        "texto": "Algo de red",
        "score": 70
      },
      {
        "texto": "Pocas personas",
        "score": 35
      },
      {
        "texto": "Solo",
        "score": 0
      }
    ]
  },
  {
    "id": 123,
    "categoria": "stress_test",
    "pregunta": "¿Tu salud permite trabajar intensamente si necesario?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, excelente",
        "score": 100
      },
      {
        "texto": "Sí, bien",
        "score": 70
      },
      {
        "texto": "Algo limitado",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 124,
    "categoria": "stress_test",
    "pregunta": "¿Podrías conseguir trabajo 'cualquiera' en 2 semanas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, probablemente",
        "score": 100
      },
      {
        "texto": "Quizás",
        "score": 70
      },
      {
        "texto": "Difícil",
        "score": 35
      },
      {
        "texto": "Imposible",
        "score": 0
      }
    ]
  },
  {
    "id": 125,
    "categoria": "stress_test",
    "pregunta": "¿Tienes skills valiosas en mercado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Múltiples, demandadas",
        "score": 100
      },
      {
        "texto": "Algunas",
        "score": 70
      },
      {
        "texto": "Básicas",
        "score": 35
      },
      {
        "texto": "Ninguna",
        "score": 0
      }
    ]
  },
  {
    "id": 126,
    "categoria": "stress_test",
    "pregunta": "¿Liquidez en inversiones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Acceso inmediato",
        "score": 100
      },
      {
        "texto": "Dentro de semanas",
        "score": 70
      },
      {
        "texto": "Meses",
        "score": 35
      },
      {
        "texto": "Ilíquido",
        "score": 0
      }
    ]
  },
  {
    "id": 127,
    "categoria": "stress_test",
    "pregunta": "¿Podrías pausar contribuciones a retiro 2 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin crisis",
        "score": 100
      },
      {
        "texto": "Sí, incómodo",
        "score": 70
      },
      {
        "texto": "No podría",
        "score": 0
      },
      {
        "texto": "No tengo",
        "score": 0
      }
    ]
  },
  {
    "id": 128,
    "categoria": "stress_test",
    "pregunta": "¿Podrías monetizar habilidades secundarias?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, rápidamente",
        "score": 100
      },
      {
        "texto": "Sí, lentamente",
        "score": 70
      },
      {
        "texto": "Quizás",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 129,
    "categoria": "stress_test",
    "pregunta": "¿Tarjetas de crédito disponibles en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, límites grandes",
        "score": 100
      },
      {
        "texto": "Sí, moderados",
        "score": 70
      },
      {
        "texto": "Pequeños",
        "score": 35
      },
      {
        "texto": "No tengo",
        "score": 0
      }
    ]
  },
  {
    "id": 130,
    "categoria": "stress_test",
    "pregunta": "¿Psicológicamente resiliente a adversidad?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, muy",
        "score": 100
      },
      {
        "texto": "Bastante",
        "score": 70
      },
      {
        "texto": "Algo",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 131,
    "categoria": "stress_test",
    "pregunta": "¿Plan B es viable o fantasía?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente viable",
        "score": 100
      },
      {
        "texto": "Probablemente",
        "score": 70
      },
      {
        "texto": "Incierto",
        "score": 35
      },
      {
        "texto": "Fantasy",
        "score": 0
      }
    ]
  },
  {
    "id": 132,
    "categoria": "stress_test",
    "pregunta": "¿Deudas son problema en stress scenario?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo",
        "score": 100
      },
      {
        "texto": "Manejable",
        "score": 70
      },
      {
        "texto": "Problemático",
        "score": 35
      },
      {
        "texto": "Ruinoso",
        "score": 0
      }
    ]
  },
  {
    "id": 133,
    "categoria": "stress_test",
    "pregunta": "¿Puedes vivir sin coche/lujos 12 meses?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin problema",
        "score": 100
      },
      {
        "texto": "Sí, incómodo",
        "score": 70
      },
      {
        "texto": "Difícil",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 134,
    "categoria": "stress_test",
    "pregunta": "¿Housing es riesgo si pierdes ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, tengo opciones",
        "score": 100
      },
      {
        "texto": "Apretado pero manejable",
        "score": 70
      },
      {
        "texto": "Problemático",
        "score": 35
      },
      {
        "texto": "Podría perder casa",
        "score": 0
      }
    ]
  },
  {
    "id": 135,
    "categoria": "stress_test",
    "pregunta": "¿Tu network tiene conexiones influyentes?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, conexiones fuertes",
        "score": 100
      },
      {
        "texto": "Algunas",
        "score": 70
      },
      {
        "texto": "Pocas",
        "score": 35
      },
      {
        "texto": "Ninguna",
        "score": 0
      }
    ]
  },
  {
    "id": 136,
    "categoria": "stress_test",
    "pregunta": "¿Ahorros en moneda estable o diversificado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Diversificado inteligentemente",
        "score": 100
      },
      {
        "texto": "Algo diversificado",
        "score": 70
      },
      {
        "texto": "Todo en una moneda",
        "score": 35
      },
      {
        "texto": "No sé",
        "score": 0
      }
    ]
  },
  {
    "id": 137,
    "categoria": "stress_test",
    "pregunta": "¿Podrías mudarte a country más barato?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, con visa disponible",
        "score": 100
      },
      {
        "texto": "Quizás",
        "score": 70
      },
      {
        "texto": "Sería complicado",
        "score": 35
      },
      {
        "texto": "No podría",
        "score": 0
      }
    ]
  },
  {
    "id": 138,
    "categoria": "stress_test",
    "pregunta": "¿Tus obligaciones son reducibles?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mayoría reducibles",
        "score": 100
      },
      {
        "texto": "Algunas",
        "score": 70
      },
      {
        "texto": "Pocas",
        "score": 35
      },
      {
        "texto": "Ninguna",
        "score": 0
      }
    ]
  },
  {
    "id": 139,
    "categoria": "stress_test",
    "pregunta": "¿Cuál es tu worst-case scenario clarity?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy claro, he pensado",
        "score": 100
      },
      {
        "texto": "Algo claro",
        "score": 70
      },
      {
        "texto": "Vago",
        "score": 35
      },
      {
        "texto": "No lo sé",
        "score": 0
      }
    ]
  },
  {
    "id": 140,
    "categoria": "stress_test",
    "pregunta": "¿Podrías reducir social spending en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Fácilmente",
        "score": 100
      },
      {
        "texto": "Con dificultad social",
        "score": 70
      },
      {
        "texto": "Sería muy difícil",
        "score": 35
      },
      {
        "texto": "No podría",
        "score": 0
      }
    ]
  },
  {
    "id": 141,
    "categoria": "stress_test",
    "pregunta": "¿Tienes 'survival mode' presupuesto calculado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, exacto",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 70
      },
      {
        "texto": "Idea vaga",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 142,
    "categoria": "stress_test",
    "pregunta": "¿Tienes seguros de desempleo/invalidez?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, buena cobertura",
        "score": 100
      },
      {
        "texto": "Algo de cobertura",
        "score": 70
      },
      {
        "texto": "Mínimo",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 143,
    "categoria": "stress_test",
    "pregunta": "¿Podrías conseguir préstamo de emergencia?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fácilmente",
        "score": 100
      },
      {
        "texto": "Quizás",
        "score": 70
      },
      {
        "texto": "Difícil",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 144,
    "categoria": "stress_test",
    "pregunta": "¿Ingresos tienen seasonal volatility alto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy estable",
        "score": 100
      },
      {
        "texto": "Algo variable",
        "score": 70
      },
      {
        "texto": "Bastante variable",
        "score": 35
      },
      {
        "texto": "Extremadamente volátil",
        "score": 0
      }
    ]
  },
  {
    "id": 145,
    "categoria": "stress_test",
    "pregunta": "¿Has testeado presupuesto de crisis realmente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, la viví",
        "score": 100
      },
      {
        "texto": "Sí, lo simulé",
        "score": 70
      },
      {
        "texto": "No lo he hecho",
        "score": 0
      },
      {
        "texto": "No sé cómo",
        "score": 0
      }
    ]
  },
  {
    "id": 146,
    "categoria": "stress_test",
    "pregunta": "¿Podrías vivir sin internet/tech gadgets?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin problema",
        "score": 100
      },
      {
        "texto": "Sí, incómodo",
        "score": 70
      },
      {
        "texto": "Sería muy difícil",
        "score": 35
      },
      {
        "texto": "No podría",
        "score": 0
      }
    ]
  },
  {
    "id": 147,
    "categoria": "stress_test",
    "pregunta": "¿Propiedades/activos son líquidos en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, muy",
        "score": 100
      },
      {
        "texto": "Algo",
        "score": 70
      },
      {
        "texto": "Difícil",
        "score": 35
      },
      {
        "texto": "Ilíquido",
        "score": 0
      }
    ]
  },
  {
    "id": 148,
    "categoria": "stress_test",
    "pregunta": "¿Podrías hacer trabajo remoto desde otro país?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fácilmente",
        "score": 100
      },
      {
        "texto": "Probablemente",
        "score": 70
      },
      {
        "texto": "Difícil",
        "score": 35
      },
      {
        "texto": "No",
        "score": 0
      }
    ]
  },
  {
    "id": 149,
    "categoria": "stress_test",
    "pregunta": "¿Stress escenarios te mantienen despierto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, estoy tranquilo",
        "score": 100
      },
      {
        "texto": "A veces pienso",
        "score": 70
      },
      {
        "texto": "Frecuentemente",
        "score": 35
      },
      {
        "texto": "Constantemente",
        "score": 0
      }
    ]
  },
  {
    "id": 150,
    "categoria": "stress_test",
    "pregunta": "¿Cuál es tu stress resilience score final (1-10)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "1-3",
        "score": 0
      },
      {
        "texto": "4-5",
        "score": 35
      },
      {
        "texto": "6-7",
        "score": 70
      },
      {
        "texto": "8-10",
        "score": 100
      }
    ]
  },
  {
    "id": 151,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuánto ganabas hace 3 años vs. ahora?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Similar o menos",
        "score": 0
      },
      {
        "texto": "10-25% más",
        "score": 25
      },
      {
        "texto": "25-50% más",
        "score": 60
      },
      {
        "texto": "50%+ más",
        "score": 100
      }
    ]
  },
  {
    "id": 152,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuánto ahorrabas hace 3 años vs. ahora (en % de ingresos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Ahorro igual o mayor",
        "score": 100
      },
      {
        "texto": "Ahorro algo menor (10-20%)",
        "score": 60
      },
      {
        "texto": "Ahorro mucho menor (20-50%)",
        "score": 30
      },
      {
        "texto": "Ahora ahorro menos o nada",
        "score": 0
      }
    ]
  },
  {
    "id": 153,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Dónde fue el dinero de tus últimas 3 subidas de sueldo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mayormente a ahorros/inversiones",
        "score": 100
      },
      {
        "texto": "Mitad y mitad",
        "score": 60
      },
      {
        "texto": "Mayormente a gastos",
        "score": 25
      },
      {
        "texto": "Todo a gastos/lujos",
        "score": 0
      }
    ]
  },
  {
    "id": 154,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu alquiler/hipoteca es mayor que hace 3 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, igual o menor",
        "score": 0
      },
      {
        "texto": "Sí, 10-25% más",
        "score": 30
      },
      {
        "texto": "Sí, 25-50% más",
        "score": 65
      },
      {
        "texto": "Sí, 50%+ más caro",
        "score": 100
      }
    ]
  },
  {
    "id": 155,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Has aumentado suscripciones, membresías o servicios en 3 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, igual o menos",
        "score": 0
      },
      {
        "texto": "Sí, 1-2 nuevos",
        "score": 25
      },
      {
        "texto": "Sí, 3-5 nuevos",
        "score": 60
      },
      {
        "texto": "Sí, muchos (6+)",
        "score": 100
      }
    ]
  },
  {
    "id": 156,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu coche/transporte es más caro que hace 3 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, mantengo similar gasto",
        "score": 25
      },
      {
        "texto": "Sí, gasto 50-100% más",
        "score": 65
      },
      {
        "texto": "Sí, gasto 100%+ más",
        "score": 100
      }
    ]
  },
  {
    "id": 157,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Pagas más en comidas/entretenimiento que hace 3 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, igual presupuesto",
        "score": 0
      },
      {
        "texto": "Sí, moderadamente más",
        "score": 35
      },
      {
        "texto": "Sí, significativamente más",
        "score": 70
      },
      {
        "texto": "Sí, gasto el doble o más",
        "score": 100
      }
    ]
  },
  {
    "id": 158,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Si tu sueldo se redujera mañana, podrías vivir con tu antiguo presupuesto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fácilmente",
        "score": 100
      },
      {
        "texto": "Probablemente",
        "score": 60
      },
      {
        "texto": "Con dificultad",
        "score": 30
      },
      {
        "texto": "No, sería imposible",
        "score": 0
      }
    ]
  },
  {
    "id": 159,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Trabajas más horas/intensidad para mantener tu estilo de vida?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, trabajo igual",
        "score": 100
      },
      {
        "texto": "Un poco más",
        "score": 60
      },
      {
        "texto": "Bastante más",
        "score": 35
      },
      {
        "texto": "Mucho más, es agotador",
        "score": 0
      }
    ]
  },
  {
    "id": 160,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Sientes que controlas tu gasto o que tu gasto te controla?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo control total",
        "score": 100
      },
      {
        "texto": "Control moderado",
        "score": 60
      },
      {
        "texto": "Poco control",
        "score": 30
      },
      {
        "texto": "Ningún control, solo gasto",
        "score": 0
      }
    ]
  },
  {
    "id": 161,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuál era tu gasto mensual hace 5 años vs ahora? ¿Se debió a aumento en ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Gasto igual, ingresos subieron",
        "score": 0
      },
      {
        "texto": "Gasto creció 5-10%",
        "score": 25
      },
      {
        "texto": "Gasto creció 20-40%",
        "score": 65
      },
      {
        "texto": "Se duplicó o más",
        "score": 100
      }
    ]
  },
  {
    "id": 162,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Puedes listar sin pensarlo tus 5 gastos mensuales más grandes? ¿Cuáles son realmente",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, claros: 4-5 son esenciales",
        "score": 0
      },
      {
        "texto": "Sí, pero 2-3 son discutibles",
        "score": 30
      },
      {
        "texto": "Sí, pero la mitad son lujo disfrazado",
        "score": 70
      },
      {
        "texto": "No tengo claridad",
        "score": 100
      }
    ]
  },
  {
    "id": 163,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuándo fue la última vez que reduciste voluntariamente un gasto porque no podías más?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Este mes",
        "score": 0
      },
      {
        "texto": "Hace 6-12 meses",
        "score": 25
      },
      {
        "texto": "Hace más de 2 años",
        "score": 70
      },
      {
        "texto": "Nunca he reducido voluntariamente",
        "score": 100
      }
    ]
  },
  {
    "id": 164,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué porcentaje de tus amigos gasta más que tú? ¿Eso influye en tus decisiones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "30% gasta más, no me influye",
        "score": 0
      },
      {
        "texto": "50% gasta más, algo me influye",
        "score": 35
      },
      {
        "texto": "Mayoría gasta más, sí me influye",
        "score": 70
      },
      {
        "texto": "Todos gastan más, presión constante",
        "score": 100
      }
    ]
  },
  {
    "id": 165,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuál fue tu peor decisión de gasto en los últimos 2 años? ¿Por qué la hiciste?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Inversión fallida, pero aprendí",
        "score": 0
      },
      {
        "texto": "Compra impulsiva, me arrepiento",
        "score": 40
      },
      {
        "texto": "Gasto recurrente innecesario aún activo",
        "score": 70
      },
      {
        "texto": "Deuda de lujo que aún pago",
        "score": 100
      }
    ]
  },
  {
    "id": 166,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tienes suscripciones que no usas? ¿Cuántas? ¿Cuánto mes cuesta?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Cero suscripciones innecesarias",
        "score": 0
      },
      {
        "texto": "1-2, menos de $20/mes",
        "score": 15
      },
      {
        "texto": "3-5, entre $30-60/mes",
        "score": 50
      },
      {
        "texto": "Más de 5, más de $100/mes",
        "score": 100
      }
    ]
  },
  {
    "id": 167,
    "categoria": "lifestyle_creep",
    "pregunta": "Si mañana perdieras el 30% de ingresos, ¿cuánto tardarías en adaptar gasto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Inmediato, tengo plan",
        "score": 0
      },
      {
        "texto": "1-2 meses de ajuste",
        "score": 30
      },
      {
        "texto": "3-6 meses, dolería",
        "score": 65
      },
      {
        "texto": "No sé cómo lo haría",
        "score": 100
      }
    ]
  },
  {
    "id": 168,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué compras para sentirte mejor emocionalmente? ¿Cuánto cuesta mensualmente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nada significativo",
        "score": 0
      },
      {
        "texto": "$20-50, consciente de ello",
        "score": 30
      },
      {
        "texto": "$100-300, pero lo necesito",
        "score": 70
      },
      {
        "texto": "No sé, pero bastante",
        "score": 100
      }
    ]
  },
  {
    "id": 169,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu actual estilo de vida sería sostenible si tus ingresos bajaran 50%?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, completamente",
        "score": 0
      },
      {
        "texto": "Sí, con ajustes menores",
        "score": 25
      },
      {
        "texto": "Apenas, seria estrés",
        "score": 65
      },
      {
        "texto": "No, colapso total",
        "score": 100
      }
    ]
  },
  {
    "id": 170,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuándo fue la última vez que preguntaste 'necesito esto' vs 'quiero esto'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Siempre lo hago",
        "score": 0
      },
      {
        "texto": "Frecuentemente, 70%",
        "score": 25
      },
      {
        "texto": "A veces, 40%",
        "score": 65
      },
      {
        "texto": "Raramente",
        "score": 100
      }
    ]
  },
  {
    "id": 171,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Has sentido que 'te mereces' cierto lujo después de trabajar duro?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, pero planeo y presupuesto",
        "score": 0
      },
      {
        "texto": "Sí, y a veces lo hago sin plan",
        "score": 40
      },
      {
        "texto": "Sí, frecuentemente sin control",
        "score": 75
      },
      {
        "texto": "Es mi principal justificación para gastar",
        "score": 100
      }
    ]
  },
  {
    "id": 172,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué porcentaje de tus ingresos va a cosas que no existían en tu vida hace 3 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Menos de 5%",
        "score": 0
      },
      {
        "texto": "5-15%",
        "score": 30
      },
      {
        "texto": "15-30%",
        "score": 65
      },
      {
        "texto": "Más de 30%",
        "score": 100
      }
    ]
  },
  {
    "id": 173,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Evitas ciertos lugares o actividades por su costo? ¿Cuánto te impacta esto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, presupuesto para todo lo importante",
        "score": 0
      },
      {
        "texto": "A veces, decisiones racionales",
        "score": 25
      },
      {
        "texto": "Frecuentemente, es frustrante",
        "score": 70
      },
      {
        "texto": "Constantemente, genera resentimiento",
        "score": 100
      }
    ]
  },
  {
    "id": 174,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Sabes cuál es tu 'punto de quiebre' de gasto? ¿Cuándo dirías 'basta'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Claramente definido, respetado",
        "score": 0
      },
      {
        "texto": "Aproximado, lo cruzo a veces",
        "score": 35
      },
      {
        "texto": "Vago, lo cruzo frecuentemente",
        "score": 70
      },
      {
        "texto": "No existe",
        "score": 100
      }
    ]
  },
  {
    "id": 175,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu pareja/familia tiene diferentes visiones sobre 'lujo' vs 'necesario'? ¿Causa conflicto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Alineados completamente",
        "score": 0
      },
      {
        "texto": "Diferencias menores, las manejamos",
        "score": 30
      },
      {
        "texto": "Diferencias importantes, causa tensión",
        "score": 70
      },
      {
        "texto": "Completamente opuestos, es un problema",
        "score": 100
      }
    ]
  },
  {
    "id": 176,
    "categoria": "lifestyle_creep",
    "pregunta": "Si no tuvieras Instagram/redes, ¿cuánto reducirías tu gasto estimadamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0%, gasto por razones propias",
        "score": 0
      },
      {
        "texto": "5-10%, algo de influencia",
        "score": 25
      },
      {
        "texto": "20-30%, influyente en decisiones",
        "score": 65
      },
      {
        "texto": "40%+, es un driver importante",
        "score": 100
      }
    ]
  },
  {
    "id": 177,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuál es la línea clara entre 'invertir en tu calidad de vida' y 'lifestyle creep'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo criterios claros",
        "score": 0
      },
      {
        "texto": "Sé cuándo lo cruzo",
        "score": 30
      },
      {
        "texto": "Es ambiguo, varía",
        "score": 70
      },
      {
        "texto": "No existe línea para mí",
        "score": 100
      }
    ]
  },
  {
    "id": 178,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Gastaste más el mes pasado que hace 12 meses? ¿Tus ingresos también subieron?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, gasto estable o redujo",
        "score": 0
      },
      {
        "texto": "Sí, pero ingresos subieron igual",
        "score": 20
      },
      {
        "texto": "Sí, más que aumento de ingresos",
        "score": 65
      },
      {
        "texto": "Mucho más, sin aumento de ingresos",
        "score": 100
      }
    ]
  },
  {
    "id": 179,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué compra pequeña ($10-50) haces mensualmente sin pensar? ¿Suma significante?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Raramente, menos de $30/mes",
        "score": 0
      },
      {
        "texto": "A veces, $50-100/mes",
        "score": 30
      },
      {
        "texto": "Frecuentemente, $150-300/mes",
        "score": 70
      },
      {
        "texto": "Constantemente, más de $300/mes",
        "score": 100
      }
    ]
  },
  {
    "id": 180,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Has 'negociado contigo mismo' reducir gastos y luego incumplido?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca, disciplina total",
        "score": 0
      },
      {
        "texto": "Rara vez, 1-2 veces al año",
        "score": 25
      },
      {
        "texto": "Frecuentemente, muy pendular",
        "score": 70
      },
      {
        "texto": "Constantemente, sin control real",
        "score": 100
      }
    ]
  },
  {
    "id": 181,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuál es el gasto que, si lo revelaras, la gente te juzgaría?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No hay ninguno, transparente",
        "score": 0
      },
      {
        "texto": "Hay algunos, pero racionales",
        "score": 30
      },
      {
        "texto": "Sí, varios, me avergüenza",
        "score": 70
      },
      {
        "texto": "Muchos, prefiero ocultarlos",
        "score": 100
      }
    ]
  },
  {
    "id": 182,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu gasto mensual en 'experiencias' (viajes, restaurantes) es proporcional a tu riqueza?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, muy alineado",
        "score": 0
      },
      {
        "texto": "Aproximadamente",
        "score": 25
      },
      {
        "texto": "Significativamente más",
        "score": 65
      },
      {
        "texto": "Desproporcionado, insostenible",
        "score": 100
      }
    ]
  },
  {
    "id": 183,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tienes 'gastos de status' (coche, casa, ropa marca) que financian tu identidad?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, elijo basado en función",
        "score": 0
      },
      {
        "texto": "Algunos, pero consciente",
        "score": 35
      },
      {
        "texto": "Sí, varios, es importante para mí",
        "score": 70
      },
      {
        "texto": "Es central a mi autoimagen",
        "score": 100
      }
    ]
  },
  {
    "id": 184,
    "categoria": "lifestyle_creep",
    "pregunta": "Si no tuvieras que impresionar a nadie, ¿qué cambiarías de tu gasto actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nada importante, gasto por mí",
        "score": 0
      },
      {
        "texto": "Ajustes menores, $50-100/mes",
        "score": 25
      },
      {
        "texto": "Cambios significativos, $300+/mes",
        "score": 65
      },
      {
        "texto": "Reduciría radicalmente",
        "score": 100
      }
    ]
  },
  {
    "id": 185,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuántas veces al mes cenas/tomas algo gastando sin plan previo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Raramente, 0-1 veces",
        "score": 0
      },
      {
        "texto": "A veces, 2-4 veces",
        "score": 30
      },
      {
        "texto": "Frecuentemente, 5-8 veces",
        "score": 70
      },
      {
        "texto": "Constantemente, múltiples veces",
        "score": 100
      }
    ]
  },
  {
    "id": 186,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Sientes que 'merecerías' vivir de forma más lujosa de la que actualmente vives?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, soy realista",
        "score": 0
      },
      {
        "texto": "A veces lo pienso",
        "score": 35
      },
      {
        "texto": "Sí, me falta poder vivir mejor",
        "score": 70
      },
      {
        "texto": "Constantemente, es una frustración",
        "score": 100
      }
    ]
  },
  {
    "id": 187,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Has entrado en 'deuda de gasto' (deuda de consumo) alguna vez por lifestyle creep?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Una vez, aprendí",
        "score": 30
      },
      {
        "texto": "Varias veces, es patrón",
        "score": 70
      },
      {
        "texto": "Constantemente, ciclo de deuda",
        "score": 100
      }
    ]
  },
  {
    "id": 188,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué te frena más: presupuesto real o miedo al juicio social?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Presupuesto real, claro",
        "score": 0
      },
      {
        "texto": "Presupuesto, algo de juicio",
        "score": 25
      },
      {
        "texto": "Miedo social importante",
        "score": 70
      },
      {
        "texto": "El juicio es lo que me frena",
        "score": 100
      }
    ]
  },
  {
    "id": 189,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuando suben tus ingresos, ¿gastos suben automáticamente o controlas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Controlo, aumenta ahorros",
        "score": 0
      },
      {
        "texto": "Suben parcialmente, balance",
        "score": 25
      },
      {
        "texto": "Suben casi todo el aumento",
        "score": 70
      },
      {
        "texto": "Suben más que el aumento",
        "score": 100
      }
    ]
  },
  {
    "id": 190,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Podrías vivir confortablemente con el 50% de tus ingresos actuales?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fácilmente",
        "score": 0
      },
      {
        "texto": "Sí, con ajustes",
        "score": 25
      },
      {
        "texto": "Apenas, sería muy incómodo",
        "score": 70
      },
      {
        "texto": "No, imposible mantener estilo actual",
        "score": 100
      }
    ]
  },
  {
    "id": 191,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué 'norma de gasto' adoptaste de tu familia de origen?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Consciente y deliberadamente revisada",
        "score": 0
      },
      {
        "texto": "La sigo sin muchos cambios",
        "score": 30
      },
      {
        "texto": "Reaccioné siendo más gastador",
        "score": 70
      },
      {
        "texto": "Reaccioné siendo mucho más gastador",
        "score": 100
      }
    ]
  },
  {
    "id": 192,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu actual lifestyle es el que elegiste o el que 'pasó a serlo'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Completamente elegido",
        "score": 0
      },
      {
        "texto": "Mayormente elegido, algo emergió",
        "score": 25
      },
      {
        "texto": "Mitad y mitad",
        "score": 65
      },
      {
        "texto": "Principalmente emergió sin plan",
        "score": 100
      }
    ]
  },
  {
    "id": 193,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuál es tu mayor gasto mensual que contribuye a tu identidad social?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No hay ninguno relacionado a identidad",
        "score": 0
      },
      {
        "texto": "Algo, pero es inversión real",
        "score": 30
      },
      {
        "texto": "Bastante, es importante",
        "score": 70
      },
      {
        "texto": "Muy significante, casi es todo",
        "score": 100
      }
    ]
  },
  {
    "id": 194,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué 'no' difícil dejaste de decir y ahora gastas en ello regularmente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mantengo mis límites",
        "score": 0
      },
      {
        "texto": "Alguno pequeño que no duele",
        "score": 25
      },
      {
        "texto": "Varios importantes, fuerte creep",
        "score": 65
      },
      {
        "texto": "Dije sí a casi todo",
        "score": 100
      }
    ]
  },
  {
    "id": 195,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tus amigos cercanos gastan similar o muy diferente a ti? ¿Cómo te hace sentir?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Similar, confortable",
        "score": 0
      },
      {
        "texto": "Algo diferente, no importa",
        "score": 25
      },
      {
        "texto": "Muy diferente, me siento extraño",
        "score": 70
      },
      {
        "texto": "Ellos gastan mucho más, es doloroso",
        "score": 100
      }
    ]
  },
  {
    "id": 196,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Qué compra reciente hiciste que, honestamente, fue por necesidad vs ego?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Últimas 5 fueron necesarias",
        "score": 0
      },
      {
        "texto": "3 necesarias, 2 ego",
        "score": 35
      },
      {
        "texto": "2 necesarias, 3 ego",
        "score": 70
      },
      {
        "texto": "La mayoría fueron por ego",
        "score": 100
      }
    ]
  },
  {
    "id": 197,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu actual gasto en 'lujo' se parece al de la persona que querías ser hace 10 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No coincide, soy diferente",
        "score": 0
      },
      {
        "texto": "Parcialmente, algo cambió",
        "score": 30
      },
      {
        "texto": "Bastante similar, siguen siendo prioridades",
        "score": 65
      },
      {
        "texto": "Es exactamente lo que quería",
        "score": 100
      }
    ]
  },
  {
    "id": 198,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Cuándo fue la última vez que deliberadamente redujiste algo para ahorrar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Este mes",
        "score": 0
      },
      {
        "texto": "Últimos 3 meses",
        "score": 25
      },
      {
        "texto": "Últimos 12 meses",
        "score": 60
      },
      {
        "texto": "No recuerdo o nunca lo hice",
        "score": 100
      }
    ]
  },
  {
    "id": 199,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Sinceramente, si tuvieras $1M hoy, ¿gastarías radicalmente más?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No significativamente",
        "score": 0
      },
      {
        "texto": "Sí, 20-30% más de gasto",
        "score": 35
      },
      {
        "texto": "Sí, 50%+ más de gasto",
        "score": 70
      },
      {
        "texto": "Sí, gastaría muchísimo más",
        "score": 100
      }
    ]
  },
  {
    "id": 200,
    "categoria": "lifestyle_creep",
    "pregunta": "¿Tu gasto actual refleja tus valores reales o la versión de ti que quieres ser?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente mis valores reales",
        "score": 0
      },
      {
        "texto": "Mayormente valores, algo aspiracional",
        "score": 25
      },
      {
        "texto": "Mitad valores, mitad aspiración",
        "score": 65
      },
      {
        "texto": "Principalmente la versión que quiero ser",
        "score": 100
      }
    ]
  },
  {
    "id": 201,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes testamento actualizado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, hecho en últimos 2 años",
        "score": 0
      },
      {
        "texto": "Sí, pero antiguo (3-5 años)",
        "score": 40
      },
      {
        "texto": "Sí, muy antiguo (5+ años)",
        "score": 70
      },
      {
        "texto": "No tengo testamento",
        "score": 100
      }
    ]
  },
  {
    "id": 202,
    "categoria": "blindaje_legal",
    "pregunta": "¿Vives en pareja de hecho (sin casarte legalmente)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, y está formalizado en testamento",
        "score": 25
      },
      {
        "texto": "Sí, sin ninguna formalización",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 203,
    "categoria": "blindaje_legal",
    "pregunta": "¿Designaste beneficiarios explícitos en cuentas/seguros?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, en todas las cuentas",
        "score": 0
      },
      {
        "texto": "En algunas",
        "score": 40
      },
      {
        "texto": "No, en ninguna",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 204,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes poder notarial preventivo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, actualizado",
        "score": 0
      },
      {
        "texto": "Sí, antiguo",
        "score": 50
      },
      {
        "texto": "No",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 205,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes seguro de vida con cobertura adecuada?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, cobertura es 5-10x mi salario anual",
        "score": 0
      },
      {
        "texto": "Sí, pero baja cobertura",
        "score": 40
      },
      {
        "texto": "No, no tengo",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 206,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes deuda conjunta con alguien?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, pero está formalizada",
        "score": 30
      },
      {
        "texto": "Sí, informal o mal documentada",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 207,
    "categoria": "blindaje_legal",
    "pregunta": "¿Optimizas fiscalmente tu situación (desgravaciones, inversiones)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, con asesor fiscal",
        "score": 100
      },
      {
        "texto": "Parcialmente",
        "score": 50
      },
      {
        "texto": "No, pago lo que toca",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 208,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes documentado quién se encarga de tus cuentas si algo te pasa?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, está claro y formalizado",
        "score": 100
      },
      {
        "texto": "Aproximadamente, en mi cabeza",
        "score": 30
      },
      {
        "texto": "No sé, nadie lo sabe",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 209,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tus herederos/familia conoce dónde están tus activos/documentos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, hay un documento de referencia",
        "score": 100
      },
      {
        "texto": "Vagamente",
        "score": 40
      },
      {
        "texto": "No, es un misterio",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 210,
    "categoria": "blindaje_legal",
    "pregunta": "¿Has consultado con asesor legal/fiscal en últimos 2 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, regularmente",
        "score": 100
      },
      {
        "texto": "Sí, una vez",
        "score": 50
      },
      {
        "texto": "No, nunca",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 211,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes un testamento actualizado, poder notarial y beneficiarios designados?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, todo actualizado hace <1 año",
        "score": 0
      },
      {
        "texto": "Sí, pero hace 2+ años",
        "score": 25
      },
      {
        "texto": "Parcialmente, falta algo",
        "score": 65
      },
      {
        "texto": "No tengo nada",
        "score": 100
      }
    ]
  },
  {
    "id": 212,
    "categoria": "blindaje_legal",
    "pregunta": "¿Sabes qué tipo de seguros tienes y cuál es su cobertura exacta?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, todos documentados, revisados anualmente",
        "score": 0
      },
      {
        "texto": "Sí, pero hace años que no reviso",
        "score": 30
      },
      {
        "texto": "Vagamente, los tengo pero no sé detalles",
        "score": 70
      },
      {
        "texto": "No sé qué tengo exactamente",
        "score": 100
      }
    ]
  },
  {
    "id": 213,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes una estrategia legal documentada para proteger tu patrimonio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, revisada por abogado profesional",
        "score": 0
      },
      {
        "texto": "Tengo algo, pero básico",
        "score": 35
      },
      {
        "texto": "Vagamente, sin estructura clara",
        "score": 70
      },
      {
        "texto": "No tengo ninguna",
        "score": 100
      }
    ]
  },
  {
    "id": 214,
    "categoria": "blindaje_legal",
    "pregunta": "¿Si morías hoy, ¿tu familia sabría cómo acceder a tus activos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, todo documentado y comunicado",
        "score": 0
      },
      {
        "texto": "Sí, saben dónde está la documentación",
        "score": 20
      },
      {
        "texto": "Parcialmente, hay lagunas",
        "score": 70
      },
      {
        "texto": "No, estaría perdido",
        "score": 100
      }
    ]
  },
  {
    "id": 215,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes seguro de responsabilidad civil que cubra demandas por accidentes?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, cobertura amplia y actualizada",
        "score": 0
      },
      {
        "texto": "Sí, cobertura básica",
        "score": 25
      },
      {
        "texto": "Parcial, solo auto/casa",
        "score": 65
      },
      {
        "texto": "No tengo",
        "score": 100
      }
    ]
  },
  {
    "id": 216,
    "categoria": "blindaje_legal",
    "pregunta": "¿Has revisado tu contrato de trabajo por cláusulas peligrosas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, con abogado",
        "score": 0
      },
      {
        "texto": "Sí, por mi cuenta",
        "score": 25
      },
      {
        "texto": "No, pero debería",
        "score": 70
      },
      {
        "texto": "Nunca, no lo he visto",
        "score": 100
      }
    ]
  },
  {
    "id": 217,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes un 'inventario de activos' documentado con ubicaciones y accesos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, completo y seguro",
        "score": 0
      },
      {
        "texto": "Parcialmente documentado",
        "score": 35
      },
      {
        "texto": "En mi cabeza, no documentado",
        "score": 70
      },
      {
        "texto": "No sé dónde está todo",
        "score": 100
      }
    ]
  },
  {
    "id": 218,
    "categoria": "blindaje_legal",
    "pregunta": "¿Separaste legalmente bienes personales de bienes compartidos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, documentado formalmente",
        "score": 0
      },
      {
        "texto": "Parcialmente, en proceso",
        "score": 30
      },
      {
        "texto": "No, está mixto",
        "score": 70
      },
      {
        "texto": "No relevante o no sé",
        "score": 100
      }
    ]
  },
  {
    "id": 219,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tu seguro de vida cubre el monto que tu familia necesitaría?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sobra cobertura",
        "score": 0
      },
      {
        "texto": "Sí, cubre lo necesario",
        "score": 20
      },
      {
        "texto": "Parcialmente, hay brecha",
        "score": 70
      },
      {
        "texto": "No tengo o es insuficiente",
        "score": 100
      }
    ]
  },
  {
    "id": 220,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes cuentas de emergencia a nombre de tus hijos o herederos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, estructura legal completa",
        "score": 0
      },
      {
        "texto": "Parcial, algunas cuentas",
        "score": 30
      },
      {
        "texto": "Planeo hacerlo",
        "score": 70
      },
      {
        "texto": "No tengo plan",
        "score": 100
      }
    ]
  },
  {
    "id": 221,
    "categoria": "blindaje_legal",
    "pregunta": "¿Si perdiera la capacidad legal, quién tomaría decisiones financieras por ti?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Designé legalmente a alguien",
        "score": 0
      },
      {
        "texto": "Tengo a alguien en mente",
        "score": 25
      },
      {
        "texto": "No lo he pensado",
        "score": 70
      },
      {
        "texto": "No sé qué pasaría",
        "score": 100
      }
    ]
  },
  {
    "id": 222,
    "categoria": "blindaje_legal",
    "pregunta": "¿Proteges legalmente tu nombre de dominio, marca o propiedad intelectual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, registrado y protegido",
        "score": 0
      },
      {
        "texto": "Parcialmente registrado",
        "score": 35
      },
      {
        "texto": "Tengo activos intelectuales sin protección",
        "score": 70
      },
      {
        "texto": "No tengo propiedad intelectual",
        "score": 100
      }
    ]
  },
  {
    "id": 223,
    "categoria": "blindaje_legal",
    "pregunta": "¿Revisaste si tu casa está registrada correctamente a tu nombre?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, registros actualizados",
        "score": 0
      },
      {
        "texto": "Sí, pero nunca lo revisé",
        "score": 20
      },
      {
        "texto": "Supongo que sí, nunca verifiqué",
        "score": 70
      },
      {
        "texto": "No, puede haber problemas",
        "score": 100
      }
    ]
  },
  {
    "id": 224,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes un acuerdo prenupcial o documento similar si aplica?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, formalizado legalmente",
        "score": 0
      },
      {
        "texto": "Planeo hacerlo",
        "score": 30
      },
      {
        "texto": "Nunca lo consideré",
        "score": 70
      },
      {
        "texto": "No tengo pareja o no aplica",
        "score": 50
      }
    ]
  },
  {
    "id": 225,
    "categoria": "blindaje_legal",
    "pregunta": "¿Conoces las implicaciones fiscales de tus inversiones y heredencias?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, con asesor fiscal profesional",
        "score": 0
      },
      {
        "texto": "Parcialmente, investigué algo",
        "score": 35
      },
      {
        "texto": "Vagamente, no sé bien",
        "score": 70
      },
      {
        "texto": "No tengo idea",
        "score": 100
      }
    ]
  },
  {
    "id": 226,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes protección legal contra demandas laborales o de terceros?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, seguro y cobertura completa",
        "score": 0
      },
      {
        "texto": "Sí, cobertura básica",
        "score": 25
      },
      {
        "texto": "No sé si estoy protegido",
        "score": 70
      },
      {
        "texto": "No tengo protección",
        "score": 100
      }
    ]
  },
  {
    "id": 227,
    "categoria": "blindaje_legal",
    "pregunta": "¿Si te demandaran mañana, ¿tendrías dinero para defensa legal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, seguro y fondos",
        "score": 0
      },
      {
        "texto": "Sí, podría hacerlo",
        "score": 25
      },
      {
        "texto": "Sería difícil, stressful",
        "score": 70
      },
      {
        "texto": "No, endeudamiento total",
        "score": 100
      }
    ]
  },
  {
    "id": 228,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tu estructura empresarial o laboral minimiza riesgo legal y fiscal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, optimizada profesionalmente",
        "score": 0
      },
      {
        "texto": "Parcialmente, hay mejoras posibles",
        "score": 35
      },
      {
        "texto": "Básica, no optimizada",
        "score": 70
      },
      {
        "texto": "No tengo estructura",
        "score": 100
      }
    ]
  },
  {
    "id": 229,
    "categoria": "blindaje_legal",
    "pregunta": "¿Conoces las leyes que podrían afectar tu patrimonio en caso de crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, asesorado legalmente",
        "score": 0
      },
      {
        "texto": "Parcialmente, investigué",
        "score": 30
      },
      {
        "texto": "No, pero tendría que",
        "score": 70
      },
      {
        "texto": "No tengo idea",
        "score": 100
      }
    ]
  },
  {
    "id": 230,
    "categoria": "blindaje_legal",
    "pregunta": "¿Documentaste quién hereda cada activo específico?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, completamente documentado",
        "score": 0
      },
      {
        "texto": "Parcialmente documentado",
        "score": 25
      },
      {
        "texto": "Vagamente en testamento",
        "score": 65
      },
      {
        "texto": "No, es vago",
        "score": 100
      }
    ]
  },
  {
    "id": 231,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes acceso a abogado confiable si surgiera crisis legal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, relación establecida",
        "score": 0
      },
      {
        "texto": "Sé a quién llamar",
        "score": 20
      },
      {
        "texto": "Tendría que buscar",
        "score": 70
      },
      {
        "texto": "No tengo contacto",
        "score": 100
      }
    ]
  },
  {
    "id": 232,
    "categoria": "blindaje_legal",
    "pregunta": "¿Proteges legalmente a tus empleados o contratistas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, contratos y cobertura completa",
        "score": 0
      },
      {
        "texto": "Parcialmente, faltan detalles",
        "score": 35
      },
      {
        "texto": "Básicamente, sin optimización",
        "score": 70
      },
      {
        "texto": "No tengo empleados",
        "score": 50
      }
    ]
  },
  {
    "id": 233,
    "categoria": "blindaje_legal",
    "pregunta": "¿Revisaste términos de servicio de plataformas donde guardas dinero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, múltiples veces",
        "score": 0
      },
      {
        "texto": "Sí, una vez",
        "score": 20
      },
      {
        "texto": "Nunca completamente",
        "score": 70
      },
      {
        "texto": "No, confío y listo",
        "score": 100
      }
    ]
  },
  {
    "id": 234,
    "categoria": "blindaje_legal",
    "pregunta": "¿Sabes qué pasaría legalmente con tus deudas si murieras?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, documentado y aclarado",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 30
      },
      {
        "texto": "No sé bien",
        "score": 70
      },
      {
        "texto": "No tengo idea",
        "score": 100
      }
    ]
  },
  {
    "id": 235,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes cuentas bancarias en múltiples instituciones por seguridad legal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, diversificado intencionalmente",
        "score": 0
      },
      {
        "texto": "Sí, pero por otras razones",
        "score": 20
      },
      {
        "texto": "Tengo una o dos",
        "score": 60
      },
      {
        "texto": "Todo en una institución",
        "score": 100
      }
    ]
  },
  {
    "id": 236,
    "categoria": "blindaje_legal",
    "pregunta": "¿Documentaste y asegurastes tus objetos de valor?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fotos, tasaciones, seguro",
        "score": 0
      },
      {
        "texto": "Parcialmente documentado",
        "score": 30
      },
      {
        "texto": "Vagamente",
        "score": 70
      },
      {
        "texto": "No, en riesgo",
        "score": 100
      }
    ]
  },
  {
    "id": 237,
    "categoria": "blindaje_legal",
    "pregunta": "¿Si entraras en litigio, ¿cuál sería el impacto en tu patrimonio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mínimo, protegido legalmente",
        "score": 0
      },
      {
        "texto": "Algo, pero manejable",
        "score": 30
      },
      {
        "texto": "Significante, preocupante",
        "score": 70
      },
      {
        "texto": "Devastador, pérdida total posible",
        "score": 100
      }
    ]
  },
  {
    "id": 238,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes un plan para mantener privacidad financiera si es necesario?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, documentado y estructurado",
        "score": 0
      },
      {
        "texto": "Parcial, algunas medidas",
        "score": 30
      },
      {
        "texto": "No, pero lo consideraría",
        "score": 70
      },
      {
        "texto": "No, transparencia total",
        "score": 50
      }
    ]
  },
  {
    "id": 239,
    "categoria": "blindaje_legal",
    "pregunta": "¿Revisaste regulaciones financieras que te afecten directamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, actualizado profesionalmente",
        "score": 0
      },
      {
        "texto": "Parcialmente, algo investigué",
        "score": 35
      },
      {
        "texto": "No, probablemente debería",
        "score": 70
      },
      {
        "texto": "No, ignoro completamente",
        "score": 100
      }
    ]
  },
  {
    "id": 240,
    "categoria": "blindaje_legal",
    "pregunta": "¿Podrías explicar tu estructura legal de patrimonio a tu familia sin confusión?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, claramente documentado",
        "score": 0
      },
      {
        "texto": "Sí, pero es complicado",
        "score": 25
      },
      {
        "texto": "Parcialmente, hay confusión",
        "score": 70
      },
      {
        "texto": "No, es caos total",
        "score": 100
      }
    ]
  },
  {
    "id": 241,
    "categoria": "blindaje_legal",
    "pregunta": "¿Revisaste si tus herederos tendrían facilidad accediendo a tus activos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, proceso optimizado",
        "score": 0
      },
      {
        "texto": "Sí, proceso normal",
        "score": 25
      },
      {
        "texto": "Parcialmente, habría fricción",
        "score": 70
      },
      {
        "texto": "No, sería caótico",
        "score": 100
      }
    ]
  },
  {
    "id": 242,
    "categoria": "blindaje_legal",
    "pregunta": "¿Si perdiera la capacidad mental, ¿quién manejaría tus finanzas correctamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, persona de confianza designada",
        "score": 0
      },
      {
        "texto": "Tal vez, pero no oficial",
        "score": 35
      },
      {
        "texto": "Incierto, sería problema",
        "score": 70
      },
      {
        "texto": "No sé, preocupación seria",
        "score": 100
      }
    ]
  },
  {
    "id": 243,
    "categoria": "blindaje_legal",
    "pregunta": "¿Proteges tus cuentas digitales y acceso con herencia digital?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, documentado para herederos",
        "score": 0
      },
      {
        "texto": "Parcialmente, algunos documentos",
        "score": 30
      },
      {
        "texto": "No, sería problema accesar",
        "score": 70
      },
      {
        "texto": "No sé cómo hacerlo",
        "score": 100
      }
    ]
  },
  {
    "id": 244,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes seguro de invalidez que cubriría pérdida de ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, cobertura completa",
        "score": 0
      },
      {
        "texto": "Sí, cobertura parcial",
        "score": 25
      },
      {
        "texto": "Poca o nada",
        "score": 75
      },
      {
        "texto": "No tengo",
        "score": 100
      }
    ]
  },
  {
    "id": 245,
    "categoria": "blindaje_legal",
    "pregunta": "¿Documentaste instrucciones para cierre de negocios o cuentas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, completo y actualizado",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 30
      },
      {
        "texto": "Vagamente",
        "score": 70
      },
      {
        "texto": "No, sería caos",
        "score": 100
      }
    ]
  },
  {
    "id": 246,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tienes acceso a caja de seguridad para documentos críticos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, documentos seguros guardados",
        "score": 0
      },
      {
        "texto": "Sí, pero incompleto",
        "score": 20
      },
      {
        "texto": "No, en casa",
        "score": 70
      },
      {
        "texto": "No, desorganizado",
        "score": 100
      }
    ]
  },
  {
    "id": 247,
    "categoria": "blindaje_legal",
    "pregunta": "¿Conoces tus derechos legales como inversor y consumidor?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, bastante informado",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 35
      },
      {
        "texto": "Vagamente",
        "score": 70
      },
      {
        "texto": "No, desconocimiento total",
        "score": 100
      }
    ]
  },
  {
    "id": 248,
    "categoria": "blindaje_legal",
    "pregunta": "¿Revisaste si tienes exposición legal innecesaria en tu trabajo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, minimizada legalmente",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 30
      },
      {
        "texto": "No mucho",
        "score": 70
      },
      {
        "texto": "No, probablemente exposición alta",
        "score": 100
      }
    ]
  },
  {
    "id": 249,
    "categoria": "blindaje_legal",
    "pregunta": "¿Podrías perder activos por deuda imprevista sin protección legal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, assets protegidos",
        "score": 0
      },
      {
        "texto": "Parcialmente protegido",
        "score": 35
      },
      {
        "texto": "Significante exposición",
        "score": 70
      },
      {
        "texto": "Vulnerable totalmente",
        "score": 100
      }
    ]
  },
  {
    "id": 250,
    "categoria": "blindaje_legal",
    "pregunta": "¿Tu estructura legal actual reduce riesgos o creas nuevos accidentalmente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "La reduce significativamente",
        "score": 0
      },
      {
        "texto": "Algunos riesgos reducidos",
        "score": 30
      },
      {
        "texto": "Neutral, sin impacto claro",
        "score": 60
      },
      {
        "texto": "Crea nuevos problemas",
        "score": 100
      }
    ]
  },
  {
    "id": 251,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuál es el precio de tu coche?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sin coche o transporte público",
        "score": 0
      },
      {
        "texto": "0-15.000 €",
        "score": 10
      },
      {
        "texto": "15.001-35.000 €",
        "score": 35
      },
      {
        "texto": "35.001-70.000 €",
        "score": 60
      }
    ]
  },
  {
    "id": 252,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuánto gastas mensualmente en ropa/marcas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-50 €",
        "score": 0
      },
      {
        "texto": "51-150 €",
        "score": 25
      },
      {
        "texto": "151-400 €",
        "score": 50
      },
      {
        "texto": "401-800 €",
        "score": 80
      }
    ]
  },
  {
    "id": 253,
    "categoria": "precio_estatus",
    "pregunta": "¿Vives en un barrio 'premium' de tu ciudad?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, zona estándar",
        "score": 0
      },
      {
        "texto": "Ligeramente premium",
        "score": 25
      },
      {
        "texto": "Claramente premium",
        "score": 60
      },
      {
        "texto": "Ultra-premium/lujo",
        "score": 100
      }
    ]
  },
  {
    "id": 254,
    "categoria": "precio_estatus",
    "pregunta": "¿Tus hijos van a colegio privado/internacional?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, educación pública",
        "score": 0
      },
      {
        "texto": "Privado estándar",
        "score": 40
      },
      {
        "texto": "Privado premium",
        "score": 70
      },
      {
        "texto": "Internacional",
        "score": 100
      }
    ]
  },
  {
    "id": 255,
    "categoria": "precio_estatus",
    "pregunta": "¿Tienes membresía/suscripción a clubs (golf, privado, gym elite)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Un club básico",
        "score": 30
      },
      {
        "texto": "Uno premium",
        "score": 60
      },
      {
        "texto": "Múltiples clubs premium",
        "score": 100
      }
    ]
  },
  {
    "id": 256,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuánto inviertes en experiencias 'de status' (viajes, cenas, eventos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Poco, 0-2% ingresos",
        "score": 0
      },
      {
        "texto": "Moderado, 2-5%",
        "score": 30
      },
      {
        "texto": "Significativo, 5-10%",
        "score": 65
      },
      {
        "texto": "Mucho, 10%+",
        "score": 100
      }
    ]
  },
  {
    "id": 257,
    "categoria": "precio_estatus",
    "pregunta": "¿Compras marcas caras sin necesidad funcional (iPhone, ropa designer)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, busco valor",
        "score": 0
      },
      {
        "texto": "Ocasionalmente",
        "score": 35
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Siempre, es mi estándar",
        "score": 100
      }
    ]
  },
  {
    "id": 258,
    "categoria": "precio_estatus",
    "pregunta": "¿Si tu salario se redujera, qué ajustarías PRIMERO?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Primero corto coche/vivienda/lujos",
        "score": 100
      },
      {
        "texto": "Ajustaría paulatinamente",
        "score": 50
      },
      {
        "texto": "Mantendría estilo de vida, usaría deuda",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 259,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuánto % de tu ingreso TOTAL va a 'validación/estatus'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-15%",
        "score": 0
      },
      {
        "texto": "15-30%",
        "score": 35
      },
      {
        "texto": "30-50%",
        "score": 70
      },
      {
        "texto": "50%+ (mayoría del sueldo)",
        "score": 100
      }
    ]
  },
  {
    "id": 260,
    "categoria": "precio_estatus",
    "pregunta": "¿Te arrepientes de compras status pasadas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, todas fueron buenas decisiones",
        "score": 0
      },
      {
        "texto": "Algunas",
        "score": 40
      },
      {
        "texto": "Muchas",
        "score": 80
      },
      {
        "texto": "Sí, casi todas fueron un error",
        "score": 100
      }
    ]
  },
  {
    "id": 261,
    "categoria": "precio_estatus",
    "pregunta": "¿Puedes justificar el precio premium de 3 cosas que posees vs su alternativa barata?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, justificación funcional clara",
        "score": 0
      },
      {
        "texto": "Sí, mezcla función y ego",
        "score": 30
      },
      {
        "texto": "Difícil justificar, mayormente ego",
        "score": 70
      },
      {
        "texto": "No puedo, es puro status",
        "score": 100
      }
    ]
  },
  {
    "id": 262,
    "categoria": "precio_estatus",
    "pregunta": "¿El logo o marca de lo que usas importa más que su funcionalidad?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Funcionalidad es 100% el factor",
        "score": 0
      },
      {
        "texto": "Marca es 20-30% del factor",
        "score": 30
      },
      {
        "texto": "Marca es 50-50 con función",
        "score": 65
      },
      {
        "texto": "Marca es más importante",
        "score": 100
      }
    ]
  },
  {
    "id": 263,
    "categoria": "precio_estatus",
    "pregunta": "¿Cambiarías tus marcas favoritas si solo usaras cosas 'en privado'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, amo las marcas genuinamente",
        "score": 0
      },
      {
        "texto": "Pocas cambiarían",
        "score": 25
      },
      {
        "texto": "Muchas cambiarían",
        "score": 70
      },
      {
        "texto": "Cambiaría casi todo",
        "score": 100
      }
    ]
  },
  {
    "id": 264,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuánto pagas extra por algo que crees que 'no se vería bien' si fuera barato?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No pago extra por eso",
        "score": 0
      },
      {
        "texto": "10-20% extra algunas veces",
        "score": 30
      },
      {
        "texto": "20-50% extra frecuentemente",
        "score": 70
      },
      {
        "texto": "Pago lo que sea necesario",
        "score": 100
      }
    ]
  },
  {
    "id": 265,
    "categoria": "precio_estatus",
    "pregunta": "¿Si nadie lo supiera, ¿comprarías la versión de $100 vs la de $500?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "La de $100, función es igual",
        "score": 0
      },
      {
        "texto": "La de $100, ahorro es racional",
        "score": 20
      },
      {
        "texto": "Me costría la de $500 de todas formas",
        "score": 70
      },
      {
        "texto": "La de $500, independiente de quién sepa",
        "score": 100
      }
    ]
  },
  {
    "id": 266,
    "categoria": "precio_estatus",
    "pregunta": "¿Tus amigos conocen las marcas que usas? ¿Les importa saberlo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No sé, no lo dicen",
        "score": 0
      },
      {
        "texto": "A algunos les importa",
        "score": 25
      },
      {
        "texto": "A muchos les importa",
        "score": 65
      },
      {
        "texto": "Es un tema de conversación importante",
        "score": 100
      }
    ]
  },
  {
    "id": 267,
    "categoria": "precio_estatus",
    "pregunta": "¿Has rechazado algo por ser 'demasiado barato' o no se vería bien?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca, función es lo importante",
        "score": 0
      },
      {
        "texto": "Rara vez, precio ultra bajo",
        "score": 25
      },
      {
        "texto": "Sí, varias veces",
        "score": 70
      },
      {
        "texto": "Frecuentemente",
        "score": 100
      }
    ]
  },
  {
    "id": 268,
    "categoria": "precio_estatus",
    "pregunta": "¿La gente 'lee' tu estatus por lo que usas/vistes? ¿Te importa qué leen?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí leen, no me importa",
        "score": 0
      },
      {
        "texto": "Sí leen, intento mandar buen mensaje",
        "score": 35
      },
      {
        "texto": "Sí leen, prefiero que subestimen",
        "score": 50
      },
      {
        "texto": "Sí leen, quiero que vean riqueza",
        "score": 100
      }
    ]
  },
  {
    "id": 269,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuál es el % de tu gasto que va a cosas que otros ven (vs privado)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Menos de 20%, gasto personal",
        "score": 0
      },
      {
        "texto": "20-40%, algo visible",
        "score": 25
      },
      {
        "texto": "40-70%, bastante visible",
        "score": 65
      },
      {
        "texto": "70%+, mayormente visible",
        "score": 100
      }
    ]
  },
  {
    "id": 270,
    "categoria": "precio_estatus",
    "pregunta": "¿Sientes ansiedad comprando marcas 'no conocidas' aunque sean buenas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, función es función",
        "score": 0
      },
      {
        "texto": "Un poco, prefiero conocidas",
        "score": 30
      },
      {
        "texto": "Sí, necesito que sea reconocida",
        "score": 70
      },
      {
        "texto": "Mucha, compro solo premium brands",
        "score": 100
      }
    ]
  },
  {
    "id": 271,
    "categoria": "precio_estatus",
    "pregunta": "¿Has comprado algo caro específicamente para 'encajar' en cierto círculo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca, me importa poco",
        "score": 0
      },
      {
        "texto": "Rara vez, pero reconozco",
        "score": 35
      },
      {
        "texto": "Sí, varias veces",
        "score": 70
      },
      {
        "texto": "Frecuentemente",
        "score": 100
      }
    ]
  },
  {
    "id": 272,
    "categoria": "precio_estatus",
    "pregunta": "¿Tu coche, casa, ropa definen cómo quieres que otros te vean?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, elijo por función/gusto",
        "score": 0
      },
      {
        "texto": "Algo, pero es secundario",
        "score": 30
      },
      {
        "texto": "Bastante, es importante",
        "score": 70
      },
      {
        "texto": "Sí, es central a mi identidad",
        "score": 100
      }
    ]
  },
  {
    "id": 273,
    "categoria": "precio_estatus",
    "pregunta": "¿Si ganaras más dinero, cambiarías hacia marcas más caras?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, elijo por función",
        "score": 0
      },
      {
        "texto": "Sí, algo",
        "score": 30
      },
      {
        "texto": "Sí, significativamente",
        "score": 70
      },
      {
        "texto": "Totalmente, a premium everything",
        "score": 100
      }
    ]
  },
  {
    "id": 274,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuánta tensión hay entre lo que 'pareces' y lo que 'eres' financieramente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Ninguna, muy alineado",
        "score": 0
      },
      {
        "texto": "Algo, pero manejable",
        "score": 30
      },
      {
        "texto": "Bastante, es incómodo",
        "score": 70
      },
      {
        "texto": "Mucha, es una mentira",
        "score": 100
      }
    ]
  },
  {
    "id": 275,
    "categoria": "precio_estatus",
    "pregunta": "¿Usarías una marca desconocida si es funcional pero 'se vería cheap'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, función > apariencia",
        "score": 0
      },
      {
        "texto": "Tal vez, depende del contexto",
        "score": 30
      },
      {
        "texto": "No, hay apariencia de cheap",
        "score": 70
      },
      {
        "texto": "No, jamás",
        "score": 100
      }
    ]
  },
  {
    "id": 276,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuál es el gasto 'de status puro' que no podrías dejar ir?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo ninguno",
        "score": 0
      },
      {
        "texto": "Pequeño, <$50/mes",
        "score": 25
      },
      {
        "texto": "Significante, $100-300/mes",
        "score": 65
      },
      {
        "texto": "Mayor, $500+/mes",
        "score": 100
      }
    ]
  },
  {
    "id": 277,
    "categoria": "precio_estatus",
    "pregunta": "¿Tu familia/pareja comparte tu visión de precio vs status?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, totalmente alineados",
        "score": 0
      },
      {
        "texto": "Sí, pero yo soy más que ellos",
        "score": 30
      },
      {
        "texto": "No, ellos son más que yo",
        "score": 50
      },
      {
        "texto": "Conflicto constante",
        "score": 100
      }
    ]
  },
  {
    "id": 278,
    "categoria": "precio_estatus",
    "pregunta": "¿Si fueras anónimo, cambiarías radicalmente qué compras?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, compraría igual",
        "score": 0
      },
      {
        "texto": "Poco cambiaría",
        "score": 25
      },
      {
        "texto": "Bastante cambiaría",
        "score": 65
      },
      {
        "texto": "Radicalmente diferente",
        "score": 100
      }
    ]
  },
  {
    "id": 279,
    "categoria": "precio_estatus",
    "pregunta": "¿Sientes presión para mantener cierto 'nivel' de marcas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, flexible",
        "score": 0
      },
      {
        "texto": "Un poco, interna",
        "score": 30
      },
      {
        "texto": "Bastante, de círculo social",
        "score": 70
      },
      {
        "texto": "Mucha, constante",
        "score": 100
      }
    ]
  },
  {
    "id": 280,
    "categoria": "precio_estatus",
    "pregunta": "¿Qué precio pagarías por 'no parecer pobre' comparado a función?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No hay diferencia, lo mismo",
        "score": 0
      },
      {
        "texto": "10-20% extra",
        "score": 25
      },
      {
        "texto": "30-50% extra",
        "score": 65
      },
      {
        "texto": "Lo que sea necesario",
        "score": 100
      }
    ]
  },
  {
    "id": 281,
    "categoria": "precio_estatus",
    "pregunta": "¿Tu ropa/accesorios son inversiones de calidad o performance social?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Inversión de calidad real",
        "score": 0
      },
      {
        "texto": "Mezcla, 60/40",
        "score": 30
      },
      {
        "texto": "Mayormente performance social",
        "score": 70
      },
      {
        "texto": "100% performance social",
        "score": 100
      }
    ]
  },
  {
    "id": 282,
    "categoria": "precio_estatus",
    "pregunta": "¿Conoces la diferencia real entre la marca premium y su alternativa?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, funcional y visible",
        "score": 0
      },
      {
        "texto": "Sí, pero pequeña",
        "score": 25
      },
      {
        "texto": "Honestamente, no sé",
        "score": 70
      },
      {
        "texto": "No, es marketing puro",
        "score": 100
      }
    ]
  },
  {
    "id": 283,
    "categoria": "precio_estatus",
    "pregunta": "¿Qué compras 'barato' porque nadie las ve?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Pocas cosas, compro calidad igual",
        "score": 0
      },
      {
        "texto": "Algunas, ropa interior, sábanas",
        "score": 30
      },
      {
        "texto": "Varias categorías completas",
        "score": 70
      },
      {
        "texto": "Mayoría de lo 'invisible'",
        "score": 100
      }
    ]
  },
  {
    "id": 284,
    "categoria": "precio_estatus",
    "pregunta": "¿Si tus ingresos bajaran, qué sería lo último que sacrificarías?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Gasto de status, primero va",
        "score": 0
      },
      {
        "texto": "Lo último, después de todo",
        "score": 35
      },
      {
        "texto": "Ataría las dos cosas",
        "score": 70
      },
      {
        "texto": "No podría sacrificarlo",
        "score": 100
      }
    ]
  },
  {
    "id": 285,
    "categoria": "precio_estatus",
    "pregunta": "¿Tu profesión requiere 'verse de cierta forma'? ¿Cuánto cuesta eso?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No requiere, flexible",
        "score": 0
      },
      {
        "texto": "Un poco, pero razonable",
        "score": 25
      },
      {
        "texto": "Bastante, presupuesto significante",
        "score": 65
      },
      {
        "texto": "Mucho, es costo laboral serio",
        "score": 100
      }
    ]
  },
  {
    "id": 286,
    "categoria": "precio_estatus",
    "pregunta": "¿Publicarías una foto tuya comprando en mercadillo o tienda outlet?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin problema",
        "score": 0
      },
      {
        "texto": "Sí, pero sin mencionar",
        "score": 20
      },
      {
        "texto": "No, algo incómodo",
        "score": 70
      },
      {
        "texto": "Absolutamente no",
        "score": 100
      }
    ]
  },
  {
    "id": 287,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuánto 'vale' tu autoestima vs presupuesto en gasto de status?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No está relacionado",
        "score": 0
      },
      {
        "texto": "Un poco, es motivador",
        "score": 30
      },
      {
        "texto": "Bastante, es importante",
        "score": 70
      },
      {
        "texto": "Es totalmente dependiente",
        "score": 100
      }
    ]
  },
  {
    "id": 288,
    "categoria": "precio_estatus",
    "pregunta": "¿Tu vida social giraría si cambiaras a marcas menos conocidas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, amigos por quién soy",
        "score": 0
      },
      {
        "texto": "Poco, pero algo notarían",
        "score": 30
      },
      {
        "texto": "Bastante, algunos se alejarían",
        "score": 70
      },
      {
        "texto": "Totalmente, perdería círculo",
        "score": 100
      }
    ]
  },
  {
    "id": 289,
    "categoria": "precio_estatus",
    "pregunta": "¿Mientes sobre el precio de lo que tienes cuando preguntan?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, soy honesto",
        "score": 0
      },
      {
        "texto": "Rara vez, detalles",
        "score": 25
      },
      {
        "texto": "A menudo, digo menos",
        "score": 70
      },
      {
        "texto": "Frecuentemente",
        "score": 100
      }
    ]
  },
  {
    "id": 290,
    "categoria": "precio_estatus",
    "pregunta": "¿Sientes vergüenza usando versiones 'barato' en público?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, función es lo importante",
        "score": 0
      },
      {
        "texto": "Un poco, pero lo compro igual",
        "score": 30
      },
      {
        "texto": "Sí, intento evitar",
        "score": 70
      },
      {
        "texto": "Mucha, jamás en público",
        "score": 100
      }
    ]
  },
  {
    "id": 291,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuál es la 'marca inferior' que nunca usarías aunque fuera idéntica?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo",
        "score": 0
      },
      {
        "texto": "Hay algunas por reputación",
        "score": 25
      },
      {
        "texto": "Bastantes que evito",
        "score": 70
      },
      {
        "texto": "Muchas, tengo lista negra",
        "score": 100
      }
    ]
  },
  {
    "id": 292,
    "categoria": "precio_estatus",
    "pregunta": "¿Tu pareja/familia critica tu gasto de status?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, respetan mis elecciones",
        "score": 0
      },
      {
        "texto": "A veces, pero leve",
        "score": 25
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Constantemente, es conflicto",
        "score": 100
      }
    ]
  },
  {
    "id": 293,
    "categoria": "precio_estatus",
    "pregunta": "¿Si un amigo rico llevara ropa de mercadillo, ¿lo juzgarías menos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, respeto su elección",
        "score": 0
      },
      {
        "texto": "Un poco, algo extraño",
        "score": 30
      },
      {
        "texto": "Sí, perdería status en mi mente",
        "score": 70
      },
      {
        "texto": "Bastante, sería raro",
        "score": 100
      }
    ]
  },
  {
    "id": 294,
    "categoria": "precio_estatus",
    "pregunta": "¿Es tu gasto de status 'inversión de imagen' o 'compulsión de inseguridad'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Inversión deliberada, controlada",
        "score": 0
      },
      {
        "texto": "Mezcla",
        "score": 40
      },
      {
        "texto": "Mayormente compulsión",
        "score": 70
      },
      {
        "texto": "100% inseguridad",
        "score": 100
      }
    ]
  },
  {
    "id": 295,
    "categoria": "precio_estatus",
    "pregunta": "¿Cuánto gastarías en 'parecer más rico' si tuvieras dinero infinito?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Lo mismo, me importa poco",
        "score": 0
      },
      {
        "texto": "50% más",
        "score": 30
      },
      {
        "texto": "100%+ más",
        "score": 70
      },
      {
        "texto": "Mucho más, tendría vida lujosa",
        "score": 100
      }
    ]
  },
  {
    "id": 296,
    "categoria": "precio_estatus",
    "pregunta": "¿Qué tan importante es que tu casa/auto 'se vea bien' vs sea funcional?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Función 100%, apariencia secundaria",
        "score": 0
      },
      {
        "texto": "60/40 función/apariencia",
        "score": 30
      },
      {
        "texto": "50/50",
        "score": 65
      },
      {
        "texto": "Apariencia es lo principal",
        "score": 100
      }
    ]
  },
  {
    "id": 297,
    "categoria": "precio_estatus",
    "pregunta": "¿Te comparas constantemente con gente que vive 'mejor' que tú?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, no me importa",
        "score": 0
      },
      {
        "texto": "A veces",
        "score": 30
      },
      {
        "texto": "Frecuentemente",
        "score": 70
      },
      {
        "texto": "Constantemente, es obsesión",
        "score": 100
      }
    ]
  },
  {
    "id": 298,
    "categoria": "precio_estatus",
    "pregunta": "¿Si alguien descubriera cuánto realmente gastas en status, ¿te avergonzaría?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, me importa poco",
        "score": 0
      },
      {
        "texto": "Un poco",
        "score": 25
      },
      {
        "texto": "Sí, bastante",
        "score": 70
      },
      {
        "texto": "Totalmente",
        "score": 100
      }
    ]
  },
  {
    "id": 299,
    "categoria": "precio_estatus",
    "pregunta": "¿Reconoces cómo el marketing te hace 'necesitar' status?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, consciente",
        "score": 0
      },
      {
        "texto": "Sí, pero aún caigo",
        "score": 30
      },
      {
        "texto": "Parcialmente",
        "score": 70
      },
      {
        "texto": "No, creo que es mi elección real",
        "score": 100
      }
    ]
  },
  {
    "id": 300,
    "categoria": "precio_estatus",
    "pregunta": "¿Qué costaría reducir tu gasto de status a la mitad?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Poco, sería fácil",
        "score": 0
      },
      {
        "texto": "Moderado, algo de ajuste",
        "score": 30
      },
      {
        "texto": "Mucho, estrés significante",
        "score": 70
      },
      {
        "texto": "Imposible sin crisis",
        "score": 100
      }
    ]
  },
  {
    "id": 301,
    "categoria": "hhi",
    "pregunta": "¿Cuál es tu ÚNICO ingreso mensual (nómina principal)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 20
      },
      {
        "texto": "N/A",
        "score": 40
      },
      {
        "texto": "N/A",
        "score": 60
      },
      {
        "texto": "N/A",
        "score": 80
      }
    ]
  },
  {
    "id": 302,
    "categoria": "hhi",
    "pregunta": "¿Qué % de tus ingresos viene de tu empleo principal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "100% (una sola fuente)",
        "score": 100
      },
      {
        "texto": "90-95%",
        "score": 80
      },
      {
        "texto": "75-89%",
        "score": 60
      },
      {
        "texto": "50-74%",
        "score": 35
      }
    ]
  },
  {
    "id": 303,
    "categoria": "hhi",
    "pregunta": "¿Tienes ingresos por rentas/propiedades?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, menos de 10% total",
        "score": 25
      },
      {
        "texto": "Sí, 10-20% total",
        "score": 50
      },
      {
        "texto": "Sí, más de 20% total",
        "score": 75
      }
    ]
  },
  {
    "id": 304,
    "categoria": "hhi",
    "pregunta": "¿Tienes ingresos por dividendos/inversiones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, muy pequeños (<1%)",
        "score": 20
      },
      {
        "texto": "Sí, 1-5% de ingresos",
        "score": 40
      },
      {
        "texto": "Sí, 5%+ de ingresos",
        "score": 70
      }
    ]
  },
  {
    "id": 305,
    "categoria": "hhi",
    "pregunta": "¿Tienes negocio/freelance paralelo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, hobby/ingresos mínimos",
        "score": 15
      },
      {
        "texto": "Sí, ingreso moderado (5-15%)",
        "score": 40
      },
      {
        "texto": "Sí, ingreso significativo (15%+)",
        "score": 75
      }
    ]
  },
  {
    "id": 306,
    "categoria": "hhi",
    "pregunta": "¿Dependerías de tu actual trabajo 5 años más sin poder cambiar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, me cambiaría de inmediato",
        "score": 100
      },
      {
        "texto": "Sí, pero con cierta libertad",
        "score": 60
      },
      {
        "texto": "Completamente dependiente",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 307,
    "categoria": "hhi",
    "pregunta": "¿Qué tan seguro es tu empleo actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy seguro (empleado público/gran empresa)",
        "score": 0
      },
      {
        "texto": "Relativamente seguro",
        "score": 30
      },
      {
        "texto": "Inseguro (startup/sector volátil)",
        "score": 70
      },
      {
        "texto": "Muy inseguro (contract/gig economy)",
        "score": 100
      }
    ]
  },
  {
    "id": 308,
    "categoria": "hhi",
    "pregunta": "Si pierdes tu empleo, ¿cuántos meses podrías vivir con otros ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0 meses (dependo 100% nómina)",
        "score": 100
      },
      {
        "texto": "1-3 meses",
        "score": 70
      },
      {
        "texto": "3-6 meses",
        "score": 40
      },
      {
        "texto": "6+ meses",
        "score": 10
      }
    ]
  },
  {
    "id": 309,
    "categoria": "hhi",
    "pregunta": "¿Tienes plan para crear fuentes alternas en próximos 2 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, con plan concreto",
        "score": 100
      },
      {
        "texto": "Sí, vago/eventual",
        "score": 50
      },
      {
        "texto": "No, pero me gustaría",
        "score": 25
      },
      {
        "texto": "No, ni lo he pensado",
        "score": 0
      }
    ]
  },
  {
    "id": 310,
    "categoria": "hhi",
    "pregunta": "¿Cuál es tu 'riesgo de cliente único'? (¿una empresa podría causar colapso?)",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Bajo (múltiples clientes/empleadores)",
        "score": 0
      },
      {
        "texto": "Moderado (2-3 clientes principales)",
        "score": 40
      },
      {
        "texto": "Alto (1-2 clientes = 80%+ ingresos)",
        "score": 80
      },
      {
        "texto": "Crítico (un cliente = 100% ingresos)",
        "score": 100
      }
    ]
  },
  {
    "id": 311,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Qué % de tus ingresos viene de tu empleo actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Menos de 50%",
        "score": 0
      },
      {
        "texto": "50-75%",
        "score": 25
      },
      {
        "texto": "75-95%",
        "score": 65
      },
      {
        "texto": "Más de 95%",
        "score": 100
      }
    ]
  },
  {
    "id": 312,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes más de 2 fuentes de ingresos regulares?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, 3+ fuentes diversificadas",
        "score": 0
      },
      {
        "texto": "Sí, 2 fuentes",
        "score": 30
      },
      {
        "texto": "Parcialmente, 1 principal",
        "score": 70
      },
      {
        "texto": "No, una fuente única",
        "score": 100
      }
    ]
  },
  {
    "id": 313,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Si perdieras tu trabajo mañana, ¿cuánto tiempo podrías mantener gastos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "6+ meses sin ingresos",
        "score": 0
      },
      {
        "texto": "3-6 meses",
        "score": 25
      },
      {
        "texto": "1-3 meses",
        "score": 70
      },
      {
        "texto": "Menos de 1 mes",
        "score": 100
      }
    ]
  },
  {
    "id": 314,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Has estado 3+ meses sin empleo? ¿Cuánto te mató financieramente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca, siempre empleado",
        "score": 0
      },
      {
        "texto": "Sí, fue stressful pero sobreviví",
        "score": 35
      },
      {
        "texto": "Sí, usé ahorros significativos",
        "score": 70
      },
      {
        "texto": "Sí, caí en deuda",
        "score": 100
      }
    ]
  },
  {
    "id": 315,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu industria es 'cíclica' o 'vulnerable a automatización'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, industria estable",
        "score": 0
      },
      {
        "texto": "Algo, riesgo moderado",
        "score": 30
      },
      {
        "texto": "Sí, bastante cíclica/vulnerable",
        "score": 70
      },
      {
        "texto": "Muy vulnerable, precupante",
        "score": 100
      }
    ]
  },
  {
    "id": 316,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes habilidades para monetizar fuera de tu empleo actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, podría generar ingresos fácil",
        "score": 0
      },
      {
        "texto": "Sí, tomaría tiempo pero lo haría",
        "score": 25
      },
      {
        "texto": "Parcialmente, sería difícil",
        "score": 70
      },
      {
        "texto": "No, dependo del empleo formal",
        "score": 100
      }
    ]
  },
  {
    "id": 317,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Cuándo fue la última vez que ganaste dinero fuera de tu empleo principal?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Este mes",
        "score": 0
      },
      {
        "texto": "Últimos 3 meses",
        "score": 20
      },
      {
        "texto": "Últimos 12 meses",
        "score": 60
      },
      {
        "texto": "No recuerdo o nunca",
        "score": 100
      }
    ]
  },
  {
    "id": 318,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Dependes de 'bonus', 'comisiones' o ingresos variables?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, sueldo fijo confiable",
        "score": 0
      },
      {
        "texto": "Parcialmente, algo variable",
        "score": 25
      },
      {
        "texto": "Significativamente variable",
        "score": 65
      },
      {
        "texto": "Mayoría es variable",
        "score": 100
      }
    ]
  },
  {
    "id": 319,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tus ingresos crecieron en los últimos 2 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, 20%+ crecimiento",
        "score": 0
      },
      {
        "texto": "Sí, 10-20%",
        "score": 25
      },
      {
        "texto": "Poco o nada",
        "score": 65
      },
      {
        "texto": "Bajaron",
        "score": 100
      }
    ]
  },
  {
    "id": 320,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu empleador es 'too big to fail' o 'podría quebrar'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy estable, multinacional",
        "score": 0
      },
      {
        "texto": "Estable, pero podría cerrar",
        "score": 30
      },
      {
        "texto": "Riesgo moderado",
        "score": 70
      },
      {
        "texto": "Alto riesgo, inestable",
        "score": 100
      }
    ]
  },
  {
    "id": 321,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Si tu sector colapsara, ¿tus habilidades son transferibles?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente, muy demandado",
        "score": 0
      },
      {
        "texto": "Bastante, tendría opciones",
        "score": 25
      },
      {
        "texto": "Parcialmente, sería difícil",
        "score": 70
      },
      {
        "texto": "No, muy específico",
        "score": 100
      }
    ]
  },
  {
    "id": 322,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes ahorros para sustentar crecimiento de ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, reinvierto constantemente",
        "score": 0
      },
      {
        "texto": "Sí, aunque mínimo",
        "score": 25
      },
      {
        "texto": "No, pero debería",
        "score": 70
      },
      {
        "texto": "No, vivo al límite",
        "score": 100
      }
    ]
  },
  {
    "id": 323,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Qué tan 'reemplazable' eres en tu posición actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Difícil, tengo rol único",
        "score": 0
      },
      {
        "texto": "Moderadamente, tengo especialidad",
        "score": 25
      },
      {
        "texto": "Fácil, hay muchos como yo",
        "score": 70
      },
      {
        "texto": "Muy fácil, podría ser cualquiera",
        "score": 100
      }
    ]
  },
  {
    "id": 324,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Cuál sería el impacto de una reducción 20% en tus ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Manejable, reducción de ahorro",
        "score": 0
      },
      {
        "texto": "Algo stressful, ajustes necesarios",
        "score": 30
      },
      {
        "texto": "Muy stressful, difícil vivir",
        "score": 70
      },
      {
        "texto": "Devastador, insostenible",
        "score": 100
      }
    ]
  },
  {
    "id": 325,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes una 'red de seguridad' si pierdes ingresos (familia, ahorros)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, múltiples",
        "score": 0
      },
      {
        "texto": "Sí, ahorros principalmente",
        "score": 25
      },
      {
        "texto": "Parcial, algo limitado",
        "score": 70
      },
      {
        "texto": "No, solo ingresos",
        "score": 100
      }
    ]
  },
  {
    "id": 326,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Negociarías mejor si supieras que tenías otra opción de ingreso?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No cambiaría, soy honesto",
        "score": 0
      },
      {
        "texto": "Sí, sería más valiente",
        "score": 30
      },
      {
        "texto": "Sí, mucho más fuerte",
        "score": 70
      },
      {
        "texto": "Totalmente diferente",
        "score": 100
      }
    ]
  },
  {
    "id": 327,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu contrato tiene 'no compete' que limita tus opciones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, flexible",
        "score": 0
      },
      {
        "texto": "Sí, pero razonable",
        "score": 25
      },
      {
        "texto": "Sí, bastante restricción",
        "score": 70
      },
      {
        "texto": "Sí, muy restrictivo",
        "score": 100
      }
    ]
  },
  {
    "id": 328,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes 'skill debt'? Habilidades que no desarrollaste para diversificar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, siempre me capacito",
        "score": 0
      },
      {
        "texto": "Un poco, debería aprender",
        "score": 30
      },
      {
        "texto": "Bastante, estoy atrapado",
        "score": 70
      },
      {
        "texto": "Mucho, no sé cómo empezar",
        "score": 100
      }
    ]
  },
  {
    "id": 329,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Podrías vivir con 70% de tus ingresos actuales indefinidamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fácil",
        "score": 0
      },
      {
        "texto": "Sí, con ajustes menores",
        "score": 25
      },
      {
        "texto": "Barely, sería muy incómodo",
        "score": 70
      },
      {
        "texto": "No, imposible",
        "score": 100
      }
    ]
  },
  {
    "id": 330,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tus ingresos son 'activos' (te representan) o 'pasivos' (sin ti no existen)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Pasivos, dinero en automático",
        "score": 0
      },
      {
        "texto": "Mezcla, algo automático",
        "score": 25
      },
      {
        "texto": "Mayoría activo, yo genero",
        "score": 65
      },
      {
        "texto": "100% activo, dependo",
        "score": 100
      }
    ]
  },
  {
    "id": 331,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Has planificado una 'salida' de tu empleo actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, con plan claro",
        "score": 0
      },
      {
        "texto": "Sí, vagamente",
        "score": 25
      },
      {
        "texto": "No, pero lo pienso",
        "score": 70
      },
      {
        "texto": "No, atrapad",
        "score": 100
      }
    ]
  },
  {
    "id": 332,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Cuánto 'vale tu marca' fuera de tu empleador actual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mucho, soy reconocido en industria",
        "score": 0
      },
      {
        "texto": "Algo, tengo reputación",
        "score": 25
      },
      {
        "texto": "Poco, principalmente empleado",
        "score": 70
      },
      {
        "texto": "Nada, dependo del nombre de empresa",
        "score": 100
      }
    ]
  },
  {
    "id": 333,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Si tuvieras que buscar empleo ahora, ¿cuánto tardarías?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "1-2 meses",
        "score": 0
      },
      {
        "texto": "3-4 meses",
        "score": 25
      },
      {
        "texto": "6+ meses",
        "score": 70
      },
      {
        "texto": "No sé, sería muy difícil",
        "score": 100
      }
    ]
  },
  {
    "id": 334,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu empleador es 'mercado competitivo' o 'monopolio control'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy competitivo, elijo",
        "score": 0
      },
      {
        "texto": "Competitivo",
        "score": 20
      },
      {
        "texto": "Poco competitivo",
        "score": 70
      },
      {
        "texto": "Monopolio, sin opciones",
        "score": 100
      }
    ]
  },
  {
    "id": 335,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Inviertes en tu desarrollo vs vives consumiendo salario?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Invierte constantemente",
        "score": 0
      },
      {
        "texto": "A veces, algo limitado",
        "score": 30
      },
      {
        "texto": "Raramente",
        "score": 70
      },
      {
        "texto": "No, gasto todo",
        "score": 100
      }
    ]
  },
  {
    "id": 336,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu empleo tiene 'growth cap' (no hay arriba)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, hay muchos escalones",
        "score": 0
      },
      {
        "texto": "Sí, pero puedo crecer 5+ años",
        "score": 25
      },
      {
        "texto": "Sí, límite en 3-5 años",
        "score": 70
      },
      {
        "texto": "Sí, límite inmediato",
        "score": 100
      }
    ]
  },
  {
    "id": 337,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Qué porcentaje de tiempo dedicas a 'futura-proof' tus ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "10%+, muy proactivo",
        "score": 0
      },
      {
        "texto": "5-10%",
        "score": 25
      },
      {
        "texto": "1-5%",
        "score": 70
      },
      {
        "texto": "0%, no pienso en ello",
        "score": 100
      }
    ]
  },
  {
    "id": 338,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes 'lock-in effects' que te mantienen atrapado (deuda, familia)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, soy flexible",
        "score": 0
      },
      {
        "texto": "Algo, pero manejable",
        "score": 30
      },
      {
        "texto": "Bastante, limitado",
        "score": 70
      },
      {
        "texto": "Muy mucho, atrapado",
        "score": 100
      }
    ]
  },
  {
    "id": 339,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Cuál sería tu ingreso objetivo si pudieras reinventar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Igual o menos, estoy bien",
        "score": 0
      },
      {
        "texto": "10-50% más",
        "score": 30
      },
      {
        "texto": "2-5x más",
        "score": 70
      },
      {
        "texto": "Mucho más, estoy limitado",
        "score": 100
      }
    ]
  },
  {
    "id": 340,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tus colegas tienen ingresos similares o hay brecha?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Similares, equidad",
        "score": 0
      },
      {
        "texto": "Algunos ganan más",
        "score": 25
      },
      {
        "texto": "Muchos ganan bastante más",
        "score": 70
      },
      {
        "texto": "Estoy en los últimos",
        "score": 100
      }
    ]
  },
  {
    "id": 341,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Si ganaras el doble, ¿gastarías todo o ahorraría?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Ahorraría mayoría",
        "score": 0
      },
      {
        "texto": "Ahorraría algo, gastaría algo",
        "score": 30
      },
      {
        "texto": "Gastaría mayoría",
        "score": 70
      },
      {
        "texto": "Gastaría todo",
        "score": 100
      }
    ]
  },
  {
    "id": 342,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes ingresos 'soñados' o aceptaste tu techo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo objetivo claro y voy por él",
        "score": 0
      },
      {
        "texto": "Tengo aspiración vaga",
        "score": 30
      },
      {
        "texto": "He aceptado mi nivel",
        "score": 70
      },
      {
        "texto": "No pienso en crecer",
        "score": 100
      }
    ]
  },
  {
    "id": 343,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu ingreso actual es 'máximo' de tu categoría?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, hay mucho arriba",
        "score": 0
      },
      {
        "texto": "Estoy en top 25%",
        "score": 20
      },
      {
        "texto": "Estoy en top 10%",
        "score": 60
      },
      {
        "texto": "Estoy al tope",
        "score": 100
      }
    ]
  },
  {
    "id": 344,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Qué% de tu ingreso podría reemplazar rápidamente con otros ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "100%, fácil",
        "score": 0
      },
      {
        "texto": "50-100%",
        "score": 25
      },
      {
        "texto": "25-50%",
        "score": 70
      },
      {
        "texto": "0-25%, muy difícil",
        "score": 100
      }
    ]
  },
  {
    "id": 345,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tienes 'portabilidad' de ingresos o estás 'atado'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy portátil, puedo llevar",
        "score": 0
      },
      {
        "texto": "Parcialmente portátil",
        "score": 30
      },
      {
        "texto": "Poco portátil",
        "score": 70
      },
      {
        "texto": "No portátil, atado aquí",
        "score": 100
      }
    ]
  },
  {
    "id": 346,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu jefe/empleador sabe tu valor real?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, somos honestos",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 25
      },
      {
        "texto": "No mucho",
        "score": 70
      },
      {
        "texto": "No, pago muy poco",
        "score": 100
      }
    ]
  },
  {
    "id": 347,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Podrías ganar tu salario actual en 2 trabajos part-time?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, fácil",
        "score": 0
      },
      {
        "texto": "Sí, pero sería difícil",
        "score": 30
      },
      {
        "texto": "No, tomaría demasiado tiempo",
        "score": 70
      },
      {
        "texto": "No, imposible",
        "score": 100
      }
    ]
  },
  {
    "id": 348,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Cuándo fue la última vez que preguntaste aumento?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Hace menos de 6 meses",
        "score": 0
      },
      {
        "texto": "6-12 meses",
        "score": 25
      },
      {
        "texto": "1-2 años",
        "score": 70
      },
      {
        "texto": "No recuerdo o nunca",
        "score": 100
      }
    ]
  },
  {
    "id": 349,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu estabilidad depende 100% del empleador o tienes red?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Tengo red, no dependo",
        "score": 0
      },
      {
        "texto": "Tengo algo de alternativa",
        "score": 25
      },
      {
        "texto": "Dependo bastante",
        "score": 70
      },
      {
        "texto": "100% dependencia",
        "score": 100
      }
    ]
  },
  {
    "id": 350,
    "categoria": "hhi_ingresos",
    "pregunta": "¿Tu ingreso actual te permite libertad o vives al límite?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mucha libertad, bajo gasto",
        "score": 0
      },
      {
        "texto": "Algo de libertad",
        "score": 25
      },
      {
        "texto": "Poco, vivimos muy justo",
        "score": 70
      },
      {
        "texto": "Ninguna, cada centavo cuenta",
        "score": 100
      }
    ]
  },
  {
    "id": 351,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuánto efectivo/liquidez tienes disponible AHORA?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-5.000 €",
        "score": 0
      },
      {
        "texto": "5.001-15.000 €",
        "score": 25
      },
      {
        "texto": "15.001-50.000 €",
        "score": 50
      },
      {
        "texto": "50.001-100.000 €",
        "score": 75
      }
    ]
  },
  {
    "id": 352,
    "categoria": "antifragilidad",
    "pregunta": "¿Si la bolsa cae 50%, podrías COMPRAR activos baratos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, tengo efectivo para aprovechar",
        "score": 100
      },
      {
        "texto": "Parcialmente",
        "score": 50
      },
      {
        "texto": "No, estaría en pánico",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 353,
    "categoria": "antifragilidad",
    "pregunta": "¿Qué % de tu dinero está en activos que SUBEN en crisis? (oro, bonos, opciones)",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0% (todo acciones/volátil)",
        "score": 0
      },
      {
        "texto": "5-15%",
        "score": 25
      },
      {
        "texto": "15-30%",
        "score": 60
      },
      {
        "texto": "30%+ (hedged/protegido)",
        "score": 100
      }
    ]
  },
  {
    "id": 354,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes conocimientos/habilidades que aumentan valor en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, mi habilidad es situacional",
        "score": 0
      },
      {
        "texto": "Algo (tech, finanzas, health)",
        "score": 40
      },
      {
        "texto": "Sí, muy demandado en crisis",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 355,
    "categoria": "antifragilidad",
    "pregunta": "¿Cómo reaccionaría tu plan financiero ante sorpresas negativas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Se colapsa",
        "score": 0
      },
      {
        "texto": "Soporta con dificultad",
        "score": 35
      },
      {
        "texto": "Resiste bien",
        "score": 70
      },
      {
        "texto": "Mejora (gana con volatilidad)",
        "score": 100
      }
    ]
  },
  {
    "id": 356,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes opciones (calls/puts) o derivados para especular en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, pequeña posición",
        "score": 50
      },
      {
        "texto": "Sí, posición significativa",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 357,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu ingreso AUMENTA o se ESTABILIZA en recesiones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Disminuye significativamente",
        "score": 0
      },
      {
        "texto": "Se mantiene estable",
        "score": 60
      },
      {
        "texto": "Aumenta (contraciclical)",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 358,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuánta deuda tienes a tipo fijo (te beneficia inflación)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo deuda",
        "score": 25
      },
      {
        "texto": "Poca deuda",
        "score": 50
      },
      {
        "texto": "Deuda moderada a tipo fijo",
        "score": 80
      },
      {
        "texto": "Mucha deuda a tipo fijo (ventaja inflación)",
        "score": 100
      }
    ]
  },
  {
    "id": 359,
    "categoria": "antifragilidad",
    "pregunta": "¿Podrías vivir de forma 'primitiva' si fuera necesario?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, dependo de servicios caros",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 40
      },
      {
        "texto": "Sí, tengo flexibilidad",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 360,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu mentalidad es aprovechar crisis o temerlasúnicamente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Solo tengo miedo",
        "score": 0
      },
      {
        "texto": "Mezcla de miedo y oportunidad",
        "score": 50
      },
      {
        "texto": "Veo las crisis como oportunidades de oro",
        "score": 100
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 361,
    "categoria": "antifragilidad",
    "pregunta": "¿Si tuviera crisis económica, ¿podrías beneficiarte?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, tengo opciones largas",
        "score": 0
      },
      {
        "texto": "Tal vez, tengo algo",
        "score": 30
      },
      {
        "texto": "No, sería perjudicado",
        "score": 70
      },
      {
        "texto": "Devastado, pérdida total",
        "score": 100
      }
    ]
  },
  {
    "id": 362,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'optionality' en tu vida (múltiples caminos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mucha, caminos abiertos",
        "score": 0
      },
      {
        "texto": "Alguna, pero limitado",
        "score": 30
      },
      {
        "texto": "Poca, bastante lineal",
        "score": 70
      },
      {
        "texto": "Ninguna, camino único",
        "score": 100
      }
    ]
  },
  {
    "id": 363,
    "categoria": "antifragilidad",
    "pregunta": "¿Qué cambios en el mundo te beneficiarían financieramente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muchos cambios me benefician",
        "score": 0
      },
      {
        "texto": "Algunos cambios me ayudan",
        "score": 25
      },
      {
        "texto": "Pocos cambios me ayudan",
        "score": 70
      },
      {
        "texto": "Ninguno, cambios me perjudican",
        "score": 100
      }
    ]
  },
  {
    "id": 364,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu portafolio tiene 'opciones' (upside sin downside)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, varias posiciones especulativas",
        "score": 0
      },
      {
        "texto": "Alguna, limitada",
        "score": 25
      },
      {
        "texto": "Ninguna, todo es conservador",
        "score": 70
      },
      {
        "texto": "Nada, todo es fijo",
        "score": 100
      }
    ]
  },
  {
    "id": 365,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'pequeñas apuestas' que podrían dar grande?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, varias en marcha",
        "score": 0
      },
      {
        "texto": "Sí, una o dos",
        "score": 25
      },
      {
        "texto": "No, pero debería",
        "score": 70
      },
      {
        "texto": "No, no juego",
        "score": 100
      }
    ]
  },
  {
    "id": 366,
    "categoria": "antifragilidad",
    "pregunta": "¿Qué tipo de 'choques' (cambios de mercado) te favorecerían?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Volatilidad, recesión, cambios",
        "score": 0
      },
      {
        "texto": "Algunos escenarios",
        "score": 25
      },
      {
        "texto": "Ninguno realmente",
        "score": 70
      },
      {
        "texto": "Todo me perjudicaría",
        "score": 100
      }
    ]
  },
  {
    "id": 367,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu estructura de vida mejora o empeora con estrés?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mejora, soy creativo bajo presión",
        "score": 0
      },
      {
        "texto": "Neutral, me adapto",
        "score": 30
      },
      {
        "texto": "Empeora, necesito estabilidad",
        "score": 70
      },
      {
        "texto": "Colapsa, no manejo estrés",
        "score": 100
      }
    ]
  },
  {
    "id": 368,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'apalancamiento' en tus oportunidades?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, dinero/influencia/red",
        "score": 0
      },
      {
        "texto": "Algo, pero limitado",
        "score": 30
      },
      {
        "texto": "Poco, no tengo palanca",
        "score": 70
      },
      {
        "texto": "Ninguno, bootstrapping",
        "score": 100
      }
    ]
  },
  {
    "id": 369,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuánto de tu portafolio es 'no correlacionado'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "100%, completamente diverso",
        "score": 0
      },
      {
        "texto": "Algo diverso, ~50%",
        "score": 25
      },
      {
        "texto": "Poco, altamente correlacionado",
        "score": 70
      },
      {
        "texto": "Todo correlacionado",
        "score": 100
      }
    ]
  },
  {
    "id": 370,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'barbell strategy' (seguro + apuestas)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, balance claro",
        "score": 0
      },
      {
        "texto": "Algo, parcial",
        "score": 30
      },
      {
        "texto": "No, voy por todo",
        "score": 70
      },
      {
        "texto": "No, muy conservador",
        "score": 100
      }
    ]
  },
  {
    "id": 371,
    "categoria": "antifragilidad",
    "pregunta": "¿Si tuvieras que empezar de cero, ¿sería más o menos fácil?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mucho más fácil, aprendería",
        "score": 0
      },
      {
        "texto": "Similar, repito",
        "score": 25
      },
      {
        "texto": "Más difícil, perdería ventaja",
        "score": 70
      },
      {
        "texto": "Devastador, no sé cómo empezar",
        "score": 100
      }
    ]
  },
  {
    "id": 372,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'skills leverage' (conocimiento que vale dinero)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, mucho valor",
        "score": 0
      },
      {
        "texto": "Algo, valor medio",
        "score": 25
      },
      {
        "texto": "Poco, específico",
        "score": 70
      },
      {
        "texto": "Ninguno, solo empleado",
        "score": 100
      }
    ]
  },
  {
    "id": 373,
    "categoria": "antifragilidad",
    "pregunta": "¿Qué tan 'listo' estás para 'movidas' inesperadas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy listo, tengo plan B",
        "score": 0
      },
      {
        "texto": "Algo listo, pensaría",
        "score": 30
      },
      {
        "texto": "No muy listo, sería caos",
        "score": 70
      },
      {
        "texto": "Completamente desprevenido",
        "score": 100
      }
    ]
  },
  {
    "id": 374,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu fortuna es 'resultado de suerte' o 'acumulación deliberada'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "100% deliberado, planeado",
        "score": 0
      },
      {
        "texto": "Mayoría deliberado",
        "score": 25
      },
      {
        "texto": "Mitad y mitad",
        "score": 70
      },
      {
        "texto": "Principalmente suerte",
        "score": 100
      }
    ]
  },
  {
    "id": 375,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuántos 'shots on goal' tienes activamente (proyectos, búsquedas)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "5+ intentos activos",
        "score": 0
      },
      {
        "texto": "2-4 intentos",
        "score": 25
      },
      {
        "texto": "1 intento",
        "score": 70
      },
      {
        "texto": "Ninguno, solo espero",
        "score": 100
      }
    ]
  },
  {
    "id": 376,
    "categoria": "antifragilidad",
    "pregunta": "¿Si se abriera 'gran oportunidad' hoy, ¿podrías saltar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, inmediato",
        "score": 0
      },
      {
        "texto": "Sí, con 1-2 meses",
        "score": 25
      },
      {
        "texto": "Parcialmente, comprometido",
        "score": 70
      },
      {
        "texto": "No, atrapado",
        "score": 100
      }
    ]
  },
  {
    "id": 377,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'convexity' en tu vida (benefits from volatility)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, claramente",
        "score": 0
      },
      {
        "texto": "Algo, parcial",
        "score": 30
      },
      {
        "texto": "No mucho",
        "score": 70
      },
      {
        "texto": "Tengo 'concavity' (harm from volatility)",
        "score": 100
      }
    ]
  },
  {
    "id": 378,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuál es tu 'optionality window' (tiempo de cambio)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Años, mucho tiempo",
        "score": 0
      },
      {
        "texto": "1-2 años",
        "score": 25
      },
      {
        "texto": "Meses",
        "score": 70
      },
      {
        "texto": "Weeks, crisis",
        "score": 100
      }
    ]
  },
  {
    "id": 379,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'pequeñas posiciones' en cosas especulativas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, 5%+ de portafolio",
        "score": 0
      },
      {
        "texto": "Sí, 1-5%",
        "score": 25
      },
      {
        "texto": "Mínimo, <1%",
        "score": 70
      },
      {
        "texto": "Ninguno",
        "score": 100
      }
    ]
  },
  {
    "id": 380,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu 'risk tolerance' es baja (necesitas dormir) o alta (disfrutas volatilidad)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Baja, necesito estabilidad",
        "score": 0
      },
      {
        "texto": "Moderada, balance",
        "score": 30
      },
      {
        "texto": "Alta, disfrutu riesgo",
        "score": 70
      },
      {
        "texto": "Muy alta, quiero volatilidad",
        "score": 100
      }
    ]
  },
  {
    "id": 381,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuántos 'degrees of freedom' tienes en decisiones?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muchos, muy flexible",
        "score": 0
      },
      {
        "texto": "Algunos, limitado",
        "score": 30
      },
      {
        "texto": "Pocos, constrained",
        "score": 70
      },
      {
        "texto": "Ninguno, fijo",
        "score": 100
      }
    ]
  },
  {
    "id": 382,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu decisiones te dan 'asymmetric payoff' (win big vs lose little)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, siempre",
        "score": 0
      },
      {
        "texto": "A veces",
        "score": 30
      },
      {
        "texto": "Raramente",
        "score": 70
      },
      {
        "texto": "Simétrico o negativo",
        "score": 100
      }
    ]
  },
  {
    "id": 383,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'second, third order' thinking en oportunidades?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, siempre pienso adelante",
        "score": 0
      },
      {
        "texto": "A veces, parcial",
        "score": 30
      },
      {
        "texto": "Raro, enfocado en hoy",
        "score": 70
      },
      {
        "texto": "No, reacciono",
        "score": 100
      }
    ]
  },
  {
    "id": 384,
    "categoria": "antifragilidad",
    "pregunta": "¿Qué % de tu decisiones son basadas en 'optionality'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Alto, 70%+",
        "score": 0
      },
      {
        "texto": "Moderado, 40-70%",
        "score": 25
      },
      {
        "texto": "Bajo, 10-40%",
        "score": 70
      },
      {
        "texto": "Ninguno",
        "score": 100
      }
    ]
  },
  {
    "id": 385,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'redundancy' en tu vida (backups, plans B)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, muchos backups",
        "score": 0
      },
      {
        "texto": "Algunos",
        "score": 25
      },
      {
        "texto": "Poco",
        "score": 70
      },
      {
        "texto": "No, single point of failure",
        "score": 100
      }
    ]
  },
  {
    "id": 386,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuántos 'bets' pequeños tienes en marcha?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "5+, portfolio",
        "score": 0
      },
      {
        "texto": "2-4",
        "score": 25
      },
      {
        "texto": "1",
        "score": 70
      },
      {
        "texto": "0, nada",
        "score": 100
      }
    ]
  },
  {
    "id": 387,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu vida mejora con 'randomness' o sufre?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mejora, busco sorpresas",
        "score": 0
      },
      {
        "texto": "Neutral, me adapto",
        "score": 30
      },
      {
        "texto": "Sufre, necesito control",
        "score": 70
      },
      {
        "texto": "Colapsa, volatility kills",
        "score": 100
      }
    ]
  },
  {
    "id": 388,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'edge' en algo (ventaja injusta)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, clara ventaja",
        "score": 0
      },
      {
        "texto": "Algo, pequeño edge",
        "score": 30
      },
      {
        "texto": "No mucho",
        "score": 70
      },
      {
        "texto": "Ninguno, fair game",
        "score": 100
      }
    ]
  },
  {
    "id": 389,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu portafolio es 'barbell' (safe + speculative) o concentrated?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Barbell claro",
        "score": 0
      },
      {
        "texto": "Algo de barbell",
        "score": 25
      },
      {
        "texto": "Poco",
        "score": 70
      },
      {
        "texto": "No, todo concentrado",
        "score": 100
      }
    ]
  },
  {
    "id": 390,
    "categoria": "antifragilidad",
    "pregunta": "¿Si 10x opportunity apareciera, ¿estarías listo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, totalmente",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 30
      },
      {
        "texto": "No, sería caos",
        "score": 70
      },
      {
        "texto": "No sabría qué hacer",
        "score": 100
      }
    ]
  },
  {
    "id": 391,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuál es tu 'worst case scenario' financiero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Manejable, recuperable",
        "score": 0
      },
      {
        "texto": "Difícil, pero posible",
        "score": 30
      },
      {
        "texto": "Grave, tomaría años",
        "score": 70
      },
      {
        "texto": "Devastador, game over",
        "score": 100
      }
    ]
  },
  {
    "id": 392,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'irrational bets' (cosas que pueden perder pero tienen upside)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, varias",
        "score": 0
      },
      {
        "texto": "Alguna",
        "score": 25
      },
      {
        "texto": "Ninguna",
        "score": 70
      },
      {
        "texto": "Demasiadas",
        "score": 100
      }
    ]
  },
  {
    "id": 393,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu 'margin of safety' es amplio o ajustado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy amplio, cómodo",
        "score": 0
      },
      {
        "texto": "Moderado",
        "score": 25
      },
      {
        "texto": "Ajustado",
        "score": 70
      },
      {
        "texto": "Ninguno, al borde",
        "score": 100
      }
    ]
  },
  {
    "id": 394,
    "categoria": "antifragilidad",
    "pregunta": "¿Aprendes de 'negative outcomes' o repites errores?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Aprendo siempre",
        "score": 0
      },
      {
        "texto": "A veces",
        "score": 30
      },
      {
        "texto": "Raro",
        "score": 70
      },
      {
        "texto": "Repito constantemente",
        "score": 100
      }
    ]
  },
  {
    "id": 395,
    "categoria": "antifragilidad",
    "pregunta": "¿Cuánto de tu dinero es 'locked' (no disponible)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Poco, muy flexible",
        "score": 0
      },
      {
        "texto": "Algo, retirement accounts",
        "score": 25
      },
      {
        "texto": "Bastante, inversiones",
        "score": 70
      },
      {
        "texto": "Todo, cash tied up",
        "score": 100
      }
    ]
  },
  {
    "id": 396,
    "categoria": "antifragilidad",
    "pregunta": "¿Tienes 'small positions in tail risks' (insurance)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, varias",
        "score": 0
      },
      {
        "texto": "Alguna",
        "score": 25
      },
      {
        "texto": "Ninguna",
        "score": 70
      },
      {
        "texto": "No creo en seguros",
        "score": 100
      }
    ]
  },
  {
    "id": 397,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu vida es más 'lineal' (predictable) o 'stochastic' (randomness)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Lineal, puedo predecir",
        "score": 0
      },
      {
        "texto": "Algo de sorpresas",
        "score": 30
      },
      {
        "texto": "Bastante aleatorio",
        "score": 70
      },
      {
        "texto": "Completamente impredecible",
        "score": 100
      }
    ]
  },
  {
    "id": 398,
    "categoria": "antifragilidad",
    "pregunta": "¿Podrías decir 'sí' a una oportunidad grande mañana?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin problemas",
        "score": 0
      },
      {
        "texto": "Sí, con 1-2 meses",
        "score": 25
      },
      {
        "texto": "Difícil, tomaría tiempo",
        "score": 70
      },
      {
        "texto": "No, imposible",
        "score": 100
      }
    ]
  },
  {
    "id": 399,
    "categoria": "antifragilidad",
    "pregunta": "¿Tu mejor oportunidad vino de 'plan' o 'accidente'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Plan deliberado",
        "score": 0
      },
      {
        "texto": "Mitad plan, mitad suerte",
        "score": 30
      },
      {
        "texto": "Principalmente suerte",
        "score": 70
      },
      {
        "texto": "Accidente puro",
        "score": 100
      }
    ]
  },
  {
    "id": 400,
    "categoria": "antifragilidad",
    "pregunta": "¿Cómo lidarías con 'scenario inversion' (lo opuesto que esperas)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Bien, tengo plan B",
        "score": 0
      },
      {
        "texto": "Razonablemente",
        "score": 30
      },
      {
        "texto": "Mal, perdería",
        "score": 70
      },
      {
        "texto": "Catastrófico",
        "score": 100
      }
    ]
  },
  {
    "id": 401,
    "categoria": "flujo_caja",
    "pregunta": "¿Puedes desglosar exactamente tus gastos mensuales sin dudas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, al céntimo (con sistema de tracking)",
        "score": 100
      },
      {
        "texto": "Aproximadamente",
        "score": 50
      },
      {
        "texto": "Vaguedad total, 'se va el dinero'",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 402,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuáles son tus GASTOS FIJOS mensuales (hipoteca/alquiler, servicios)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 0
      },
      {
        "texto": "N/A",
        "score": 30
      },
      {
        "texto": "N/A",
        "score": 60
      },
      {
        "texto": "N/A",
        "score": 90
      }
    ]
  },
  {
    "id": 403,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuáles son tus GASTOS VARIABLES mensuales aproximados (comida, ocio)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 0
      },
      {
        "texto": "N/A",
        "score": 30
      },
      {
        "texto": "N/A",
        "score": 60
      },
      {
        "texto": "N/A",
        "score": 90
      }
    ]
  },
  {
    "id": 404,
    "categoria": "flujo_caja",
    "pregunta": "¿Tienes suscripciones 'fantasma' que pagas sin usar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 100
      },
      {
        "texto": "Sí, 1-2",
        "score": 60
      },
      {
        "texto": "Sí, 3-5",
        "score": 30
      },
      {
        "texto": "Sí, 6+",
        "score": 0
      }
    ]
  },
  {
    "id": 405,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuánto dinero desaparece mensualmente sin saber dónde?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0-100 € (bajo)",
        "score": 100
      },
      {
        "texto": "101-300 € (moderado)",
        "score": 60
      },
      {
        "texto": "301-800 € (significativo)",
        "score": 30
      },
      {
        "texto": "800+ € (crisis)",
        "score": 0
      }
    ]
  },
  {
    "id": 406,
    "categoria": "flujo_caja",
    "pregunta": "¿Tienes presupuesto mensual formalizado?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, actualizado mensualmente",
        "score": 100
      },
      {
        "texto": "Sí, pero desactualizado",
        "score": 50
      },
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 407,
    "categoria": "flujo_caja",
    "pregunta": "¿Qué % de tu ingreso se va en impuestos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "10-20% (bajo)",
        "score": 0
      },
      {
        "texto": "20-35% (normal)",
        "score": 30
      },
      {
        "texto": "35-45% (alto)",
        "score": 60
      },
      {
        "texto": "45%+ (muy alto)",
        "score": 100
      }
    ]
  },
  {
    "id": 408,
    "categoria": "flujo_caja",
    "pregunta": "¿Usas automático para aborros o lo haces 'cuando puedo'?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Automático en salario (disciplina 100%)",
        "score": 100
      },
      {
        "texto": "Semi-automático",
        "score": 60
      },
      {
        "texto": "Manual",
        "score": 30
      },
      {
        "texto": "No ahorro",
        "score": 0
      }
    ]
  },
  {
    "id": 409,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuántas cuentas bancarias tienes y por qué?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "1 (simple pero desorganizado)",
        "score": 20
      },
      {
        "texto": "2-3 (segregado: gasto/ahorro)",
        "score": 80
      },
      {
        "texto": "4+ (sobre-organización)",
        "score": 50
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 410,
    "categoria": "flujo_caja",
    "pregunta": "¿Qué % de tu salario destinas a ahorro?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0% (gasto todo)",
        "score": 0
      },
      {
        "texto": "1-10% (bajo)",
        "score": 20
      },
      {
        "texto": "10-20% (moderado)",
        "score": 60
      },
      {
        "texto": "20%+ (agresivo)",
        "score": 100
      }
    ]
  },
  {
    "id": 411,
    "categoria": "flujo_caja",
    "pregunta": "¿Puedes predecir con precisión tus ingresos en 3 meses?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo idea",
        "score": 0
      },
      {
        "texto": "Rango muy amplio de variación",
        "score": 33
      },
      {
        "texto": "Rango moderado, bastante predecible",
        "score": 67
      },
      {
        "texto": "Muy predecible, margen de error menor al 10%",
        "score": 100
      }
    ]
  },
  {
    "id": 412,
    "categoria": "flujo_caja",
    "pregunta": "¿Qué % de tus ingresos necesitas para vivir cómodo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Más del 120% (gasto más de lo que gano)",
        "score": 0
      },
      {
        "texto": "100-120% (muy ajustado)",
        "score": 33
      },
      {
        "texto": "70-100% (manejable)",
        "score": 67
      },
      {
        "texto": "Menos del 70% (amplísimo colchón)",
        "score": 100
      }
    ]
  },
  {
    "id": 413,
    "categoria": "flujo_caja",
    "pregunta": "¿Tienes un sistema de control de gastos vigente (no teórico)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, no sé a dónde va mi dinero",
        "score": 0
      },
      {
        "texto": "Idea vaga de categorías principales",
        "score": 33
      },
      {
        "texto": "Clasifico gastos pero sin análisis",
        "score": 67
      },
      {
        "texto": "Sistema completo con análisis y alertas",
        "score": 100
      }
    ]
  },
  {
    "id": 414,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu ratio de gastos fijos vs variables mensuales?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No lo sé",
        "score": 0
      },
      {
        "texto": "Muy impreciso, dominan variables",
        "score": 33
      },
      {
        "texto": "Aproximadamente 50-50 o claro el predominio",
        "score": 67
      },
      {
        "texto": "Exacto y optimizado, variables <30%",
        "score": 100
      }
    ]
  },
  {
    "id": 415,
    "categoria": "flujo_caja",
    "pregunta": "¿Has conseguido reducir un gasto recurrente en los últimos 6 meses?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, no lo he intentado",
        "score": 0
      },
      {
        "texto": "Sí, marginal (<5% de mi presupuesto)",
        "score": 33
      },
      {
        "texto": "Sí, moderado (5-15% de cambio)",
        "score": 67
      },
      {
        "texto": "Sí, significativo, he monetizado el ahorro",
        "score": 100
      }
    ]
  },
  {
    "id": 416,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuántos meses de gastos tienes en efectivo o equivalente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Cero o negativo (endeudado)",
        "score": 0
      },
      {
        "texto": "Menos de 1 mes",
        "score": 33
      },
      {
        "texto": "1-3 meses",
        "score": 67
      },
      {
        "texto": "Más de 6 meses",
        "score": 100
      }
    ]
  },
  {
    "id": 417,
    "categoria": "flujo_caja",
    "pregunta": "¿Apartan algo de cada ingreso para gastos discretos anuales?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, me sorprenden cada vez",
        "score": 0
      },
      {
        "texto": "A veces, irregular",
        "score": 33
      },
      {
        "texto": "Sí, pero no el monto suficiente",
        "score": 67
      },
      {
        "texto": "Sí, provisión exacta, automatizada",
        "score": 100
      }
    ]
  },
  {
    "id": 418,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál fue tu mayor gasto sorpresa en los últimos 12 meses?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Más del 30% de mis ingresos mensuales",
        "score": 0
      },
      {
        "texto": "15-30% de ingresos mensuales",
        "score": 33
      },
      {
        "texto": "5-15% de ingresos mensuales",
        "score": 67
      },
      {
        "texto": "Menos del 5%, todo planificado",
        "score": 100
      }
    ]
  },
  {
    "id": 419,
    "categoria": "flujo_caja",
    "pregunta": "¿Distingues entre liquidez y rentabilidad en tu dinero?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No entiendo la distinción",
        "score": 0
      },
      {
        "texto": "Idea vaga, no lo aplico",
        "score": 33
      },
      {
        "texto": "Lo entiendo, aplicación parcial",
        "score": 67
      },
      {
        "texto": "Uso estratégico deliberado de ambos",
        "score": 100
      }
    ]
  },
  {
    "id": 420,
    "categoria": "flujo_caja",
    "pregunta": "¿Has modelado un escenario de pérdida de ingreso a 0?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, me asusta pensarlo",
        "score": 0
      },
      {
        "texto": "Brevemente, es angustioso",
        "score": 33
      },
      {
        "texto": "Sí, pero mis números no cierran bien",
        "score": 67
      },
      {
        "texto": "Sí, he modelado y ajustado plan",
        "score": 100
      }
    ]
  },
  {
    "id": 421,
    "categoria": "flujo_caja",
    "pregunta": "¿Qué porcentaje de tu flujo mensual está comprometido por deudas?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Más del 50% (muy endeudado)",
        "score": 0
      },
      {
        "texto": "30-50% (comprometido)",
        "score": 33
      },
      {
        "texto": "10-30% (manejable)",
        "score": 67
      },
      {
        "texto": "Menos del 10% o sin deudas",
        "score": 100
      }
    ]
  },
  {
    "id": 422,
    "categoria": "flujo_caja",
    "pregunta": "¿Tu flujo de caja es más fuerte en qué trimestre del año?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy variable, sin patrón claro",
        "score": 0
      },
      {
        "texto": "Hay variación, pero la controlo",
        "score": 33
      },
      {
        "texto": "Patrón claro, lo anticipé",
        "score": 67
      },
      {
        "texto": "Optimizado: invierto la estacionalidad",
        "score": 100
      }
    ]
  },
  {
    "id": 423,
    "categoria": "flujo_caja",
    "pregunta": "¿Has refinanciado una deuda para mejorar tu flujo mensual?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca, no me lo planteé",
        "score": 0
      },
      {
        "texto": "Pensé en ello pero no lo hice",
        "score": 33
      },
      {
        "texto": "Sí, logré reducción modesta",
        "score": 67
      },
      {
        "texto": "Sí, estrategia deliberada, buen resultado",
        "score": 100
      }
    ]
  },
  {
    "id": 424,
    "categoria": "flujo_caja",
    "pregunta": "¿Usas herramientas automáticas para gestionar tu flujo (apps, etc)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, todo manual o intuición",
        "score": 0
      },
      {
        "texto": "Herramientas básicas sin integración",
        "score": 33
      },
      {
        "texto": "Varias herramientas, parcialmente integradas",
        "score": 67
      },
      {
        "texto": "Sistema automatizado completo",
        "score": 100
      }
    ]
  },
  {
    "id": 425,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu velocidad de conversión: venta a cobro?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No lo sé o es irregular",
        "score": 0
      },
      {
        "texto": "Semanas, hay retrasos frecuentes",
        "score": 33
      },
      {
        "texto": "Días, algún retraso ocasional",
        "score": 67
      },
      {
        "texto": "Inmediato o pre-acuerdo de términos",
        "score": 100
      }
    ]
  },
  {
    "id": 426,
    "categoria": "flujo_caja",
    "pregunta": "¿Inviertes el excedente de flujo o lo dejas en cuenta corriente?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Lo dejo en cuenta corriente",
        "score": 0
      },
      {
        "texto": "Invierto ocasionalmente",
        "score": 33
      },
      {
        "texto": "Invierto la mayoría, mantengo colchón",
        "score": 67
      },
      {
        "texto": "Sistema automático: invierto excedentes",
        "score": 100
      }
    ]
  },
  {
    "id": 427,
    "categoria": "flujo_caja",
    "pregunta": "¿Has tenido una crisis de flujo de caja en los últimos 3 años?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, varias veces y sin resolución clara",
        "score": 0
      },
      {
        "texto": "Sí, pero conseguí resolverla",
        "score": 33
      },
      {
        "texto": "Sí, una sola vez, y he preparado defensa",
        "score": 67
      },
      {
        "texto": "No, y tengo buffer suficiente",
        "score": 100
      }
    ]
  },
  {
    "id": 428,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu margen de error antes del insolvencia?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Menos de 1 semana sin ingreso",
        "score": 0
      },
      {
        "texto": "1-2 semanas sin ingreso",
        "score": 33
      },
      {
        "texto": "1-3 meses sin ingreso",
        "score": 67
      },
      {
        "texto": "Más de 6 meses, muy robusto",
        "score": 100
      }
    ]
  },
  {
    "id": 429,
    "categoria": "flujo_caja",
    "pregunta": "¿Tienes métricas de flujo: días de caja, ratios de cobertura?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, idea vaga",
        "score": 0
      },
      {
        "texto": "Idea aproximada, sin cálculo",
        "score": 33
      },
      {
        "texto": "Algunas métricas, no todas",
        "score": 67
      },
      {
        "texto": "Dashboard completo de KPIs",
        "score": 100
      }
    ]
  },
  {
    "id": 430,
    "categoria": "flujo_caja",
    "pregunta": "¿Has negociado plazos de pago con proveedores o clientes?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca, asumo los términos dados",
        "score": 0
      },
      {
        "texto": "Ocasionalmente, con poco éxito",
        "score": 33
      },
      {
        "texto": "Sí, logro mejoras moderadas",
        "score": 67
      },
      {
        "texto": "Estrategia sistemática, optimizada",
        "score": 100
      }
    ]
  },
  {
    "id": 431,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu exposición a un gasto de emergencia de 5k€?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sería una crisis, no puedo pagarlo",
        "score": 0
      },
      {
        "texto": "Tendría que usar crédito o aplazamiento",
        "score": 33
      },
      {
        "texto": "Puedo pagarlo pero impacta mi plan",
        "score": 67
      },
      {
        "texto": "Fácil, no altero ningún plan",
        "score": 100
      }
    ]
  },
  {
    "id": 432,
    "categoria": "flujo_caja",
    "pregunta": "¿Tienes visibilidad de flujo más allá de 30 días?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, opero mes a mes",
        "score": 0
      },
      {
        "texto": "Idea vaga a 60 días",
        "score": 33
      },
      {
        "texto": "Proyección clara a 90 días",
        "score": 67
      },
      {
        "texto": "Modelo de 12 meses con escenarios",
        "score": 100
      }
    ]
  },
  {
    "id": 433,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuánto tiempo tardas en movilizar dinero si necesitas liquidez?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Días, bloqueado en inversiones ilíquidas",
        "score": 0
      },
      {
        "texto": "Algunas horas, con costos",
        "score": 33
      },
      {
        "texto": "Minutos, pequeño costo o sin costo",
        "score": 67
      },
      {
        "texto": "Instantáneo, múltiples líneas de crédito",
        "score": 100
      }
    ]
  },
  {
    "id": 434,
    "categoria": "flujo_caja",
    "pregunta": "¿Has construido un fondo de oportunidad o inversión discrecional?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, no me sobra dinero",
        "score": 0
      },
      {
        "texto": "Intento ahorrar pero es irregular",
        "score": 33
      },
      {
        "texto": "Sí, pero pequeño e inconsistente",
        "score": 67
      },
      {
        "texto": "Sí, fondo robusto, bien capitalizados",
        "score": 100
      }
    ]
  },
  {
    "id": 435,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál fue tu mayor error de predicción de flujo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Deuda de dinero que no me anticipé",
        "score": 0
      },
      {
        "texto": "Desviación de >20% respecto a plan",
        "score": 33
      },
      {
        "texto": "Desviación de 5-20%, corregible",
        "score": 67
      },
      {
        "texto": "Desviación <5%, controlable",
        "score": 100
      }
    ]
  },
  {
    "id": 436,
    "categoria": "flujo_caja",
    "pregunta": "¿Has auditado tu propio flujo con alguien externo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca",
        "score": 0
      },
      {
        "texto": "Vagamente, conversación informal",
        "score": 33
      },
      {
        "texto": "Sí, asesor me revisó números",
        "score": 67
      },
      {
        "texto": "Sí, auditoría formal y plan de mejora",
        "score": 100
      }
    ]
  },
  {
    "id": 437,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu seasonal swing de ingresos? (mín a máx)",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mayor que el 100% (muy volátil)",
        "score": 0
      },
      {
        "texto": "50-100% (significativamente volátil)",
        "score": 33
      },
      {
        "texto": "20-50% (moderadamente predecible)",
        "score": 67
      },
      {
        "texto": "Menos del 20% (muy estable)",
        "score": 100
      }
    ]
  },
  {
    "id": 438,
    "categoria": "flujo_caja",
    "pregunta": "¿Qué pasaría si perdieras tu principal fuente de ingresos hoy?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Inmediata crisis, sin opción",
        "score": 0
      },
      {
        "texto": "Podría aguantar 1-2 meses",
        "score": 33
      },
      {
        "texto": "Podría aguantar 3-6 meses",
        "score": 67
      },
      {
        "texto": "Sin problema, ingresos alternativos",
        "score": 100
      }
    ]
  },
  {
    "id": 439,
    "categoria": "flujo_caja",
    "pregunta": "¿Tienes separadas cuentas: operativa, contingencia, inversión?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, todo mezclado en una cuenta",
        "score": 0
      },
      {
        "texto": "Una o dos cuentas, poco segregado",
        "score": 33
      },
      {
        "texto": "Dos cuentas, segregación básica",
        "score": 67
      },
      {
        "texto": "Tres o más, con lógica y automatización",
        "score": 100
      }
    ]
  },
  {
    "id": 440,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es la diferencia entre tu flujo neto ideal y real?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No sé cuál es mi ideal",
        "score": 0
      },
      {
        "texto": "Diferencia mayor al 30%",
        "score": 33
      },
      {
        "texto": "Diferencia de 10-30%",
        "score": 67
      },
      {
        "texto": "Menos del 10%, muy cerca del plan",
        "score": 100
      }
    ]
  },
  {
    "id": 441,
    "categoria": "flujo_caja",
    "pregunta": "¿Has estructurado tu flujo para minimizar impuestos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No lo he considerado",
        "score": 0
      },
      {
        "texto": "Idea vaga, sin implementar",
        "score": 33
      },
      {
        "texto": "Sí, con asesor, logro moderado",
        "score": 67
      },
      {
        "texto": "Sí, estrategia integral, máximo aprovechamiento",
        "score": 100
      }
    ]
  },
  {
    "id": 442,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu velocidad de reacción ante cambio en ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Lento, me entero después",
        "score": 0
      },
      {
        "texto": "Semanas, reacción retrasada",
        "score": 33
      },
      {
        "texto": "Días, ajusto sin demora",
        "score": 67
      },
      {
        "texto": "Instantáneo, alertas automáticas",
        "score": 100
      }
    ]
  },
  {
    "id": 443,
    "categoria": "flujo_caja",
    "pregunta": "¿Has modelado impacto de inflación en tu flujo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, no lo he pensado",
        "score": 0
      },
      {
        "texto": "Brevemente, pero sin acción",
        "score": 33
      },
      {
        "texto": "Sí, ajusto ingresos anualmente",
        "score": 67
      },
      {
        "texto": "Sí, estrategia proactiva de cobertura",
        "score": 100
      }
    ]
  },
  {
    "id": 444,
    "categoria": "flujo_caja",
    "pregunta": "¿Tu flujo mejora o empeora year-over-year?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Empeorando, presión creciente",
        "score": 0
      },
      {
        "texto": "Estancado, sin mejora clara",
        "score": 33
      },
      {
        "texto": "Mejorando modestamente",
        "score": 67
      },
      {
        "texto": "Mejorando significativamente, trayectoria clara",
        "score": 100
      }
    ]
  },
  {
    "id": 445,
    "categoria": "flujo_caja",
    "pregunta": "¿Tienes acuerdos con familia sobre flujo compartido?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, vago o conflictivo",
        "score": 0
      },
      {
        "texto": "Sí, pero frecuentes malentendidos",
        "score": 33
      },
      {
        "texto": "Sí, acuerdo claro, parcialmente cumplido",
        "score": 67
      },
      {
        "texto": "Sí, muy estructurado y cumplido",
        "score": 100
      }
    ]
  },
  {
    "id": 446,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu mayor ineficiencia de flujo hoy?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No lo sé, no he analizado",
        "score": 0
      },
      {
        "texto": "Sé qué es pero no actúo",
        "score": 33
      },
      {
        "texto": "Lo sé y estoy mejorando",
        "score": 67
      },
      {
        "texto": "Lo he eliminado o está optimizado",
        "score": 100
      }
    ]
  },
  {
    "id": 447,
    "categoria": "flujo_caja",
    "pregunta": "¿Usas deuda estratégicamente para mejorar tu flujo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, la veo como problema",
        "score": 0
      },
      {
        "texto": "Idea vaga, no la aplico",
        "score": 33
      },
      {
        "texto": "Sí, uso limitado y controlado",
        "score": 67
      },
      {
        "texto": "Sí, estrategia sofisticada de apalancamiento",
        "score": 100
      }
    ]
  },
  {
    "id": 448,
    "categoria": "flujo_caja",
    "pregunta": "¿Cuál es tu costo de mantener la liquidez?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No lo sé",
        "score": 0
      },
      {
        "texto": "Idea vaga (rentabilidad baja)",
        "score": 33
      },
      {
        "texto": "Lo sé, aceptable vs riesgo",
        "score": 67
      },
      {
        "texto": "Optimizado: mínimo costo, máxima disponibilidad",
        "score": 100
      }
    ]
  },
  {
    "id": 449,
    "categoria": "flujo_caja",
    "pregunta": "¿Has diversificado tus canales de ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, una sola fuente",
        "score": 0
      },
      {
        "texto": "Sí, pero secundaria es muy pequeña",
        "score": 33
      },
      {
        "texto": "Sí, dos o tres fuentes significativas",
        "score": 67
      },
      {
        "texto": "Sí, varias fuentes equilibradas",
        "score": 100
      }
    ]
  },
  {
    "id": 450,
    "categoria": "flujo_caja",
    "pregunta": "¿Tu flujo es sostenible en 5 años sin cambios?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, va a colapsar",
        "score": 0
      },
      {
        "texto": "Dudoso, tendría que cambiar",
        "score": 33
      },
      {
        "texto": "Probablemente, con ajustes menores",
        "score": 67
      },
      {
        "texto": "Claramente sostenible, muy confiado",
        "score": 100
      }
    ]
  },
  {
    "id": 451,
    "categoria": "resiliencia",
    "pregunta": "¿Cuál es tu deuda TOTAL (hipoteca, créditos, tarjetas)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 0
      },
      {
        "texto": "N/A",
        "score": 30
      },
      {
        "texto": "N/A",
        "score": 60
      },
      {
        "texto": "N/A",
        "score": 100
      }
    ]
  },
  {
    "id": 452,
    "categoria": "resiliencia",
    "pregunta": "¿Cuál es tu RATIO de deuda vs. patrimonio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sin deuda",
        "score": 100
      },
      {
        "texto": "0-50% (saludable)",
        "score": 70
      },
      {
        "texto": "50-100% (moderado)",
        "score": 40
      },
      {
        "texto": "100%+ (peligroso)",
        "score": 0
      }
    ]
  },
  {
    "id": 453,
    "categoria": "resiliencia",
    "pregunta": "¿Cuánto pagas mensualmente en intereses de deuda?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "N/A",
        "score": 100
      },
      {
        "texto": "N/A",
        "score": 60
      },
      {
        "texto": "N/A",
        "score": 25
      },
      {
        "texto": "N/A",
        "score": 0
      }
    ]
  },
  {
    "id": 454,
    "categoria": "resiliencia",
    "pregunta": "¿Tienes deuda de alto interés (tarjetas revolving, microcréditos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 100
      },
      {
        "texto": "Sí, pequeña cantidad",
        "score": 50
      },
      {
        "texto": "Sí, significativa",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 455,
    "categoria": "resiliencia",
    "pregunta": "¿Podrías pagar tu deuda en emergencia si te obligan?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, sin problema",
        "score": 100
      },
      {
        "texto": "Parcialmente",
        "score": 50
      },
      {
        "texto": "No, imposible",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 456,
    "categoria": "resiliencia",
    "pregunta": "¿Tu hipoteca es a tipo fijo o variable?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo hipoteca",
        "score": 50
      },
      {
        "texto": "Tipo fijo (protegido)",
        "score": 100
      },
      {
        "texto": "Tipo variable (riesgo)",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 457,
    "categoria": "resiliencia",
    "pregunta": "¿La deuda está creciendo o disminuyendo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Disminuyendo (buen camino)",
        "score": 100
      },
      {
        "texto": "Estancada",
        "score": 50
      },
      {
        "texto": "Creciendo (peligro)",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 458,
    "categoria": "resiliencia",
    "pregunta": "¿Cuál es tu fondo de emergencia en meses de gastos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "0 meses (crisis)",
        "score": 0
      },
      {
        "texto": "0-1 mes",
        "score": 15
      },
      {
        "texto": "1-3 meses",
        "score": 50
      },
      {
        "texto": "3-6 meses",
        "score": 85
      }
    ]
  },
  {
    "id": 459,
    "categoria": "resiliencia",
    "pregunta": "¿Dónde está tu fondo de emergencia?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Bajo colchón (acceso inmediato pero riesgo)",
        "score": 40
      },
      {
        "texto": "Cuenta corriente (cómodo)",
        "score": 70
      },
      {
        "texto": "Cuenta ahorros 0% (seguro)",
        "score": 85
      },
      {
        "texto": "Inversión (riesgo pero rentabilidad)",
        "score": 50
      }
    ]
  },
  {
    "id": 460,
    "categoria": "resiliencia",
    "pregunta": "¿Podrías negociar/reducir tu deuda en crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, hay margen",
        "score": 80
      },
      {
        "texto": "Quizás",
        "score": 50
      },
      {
        "texto": "No, obligaciones rígidas",
        "score": 0
      },
      {
        "texto": "Opción 4",
        "score": 75
      }
    ]
  },
  {
    "id": 461,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es tu ratio de deuda total vs patrimonio neto?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mayor que 1 (endeudado neto)",
        "score": 0
      },
      {
        "texto": "0.5 a 1 (moderadamente apalancado)",
        "score": 33
      },
      {
        "texto": "0.2 a 0.5 (conservador)",
        "score": 67
      },
      {
        "texto": "Menor que 0.2 o sin deuda",
        "score": 100
      }
    ]
  },
  {
    "id": 462,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es tu mayor deuda individual y su propósito?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Deuda de consumo (tarjeta, personal)",
        "score": 0
      },
      {
        "texto": "Deuda productiva débil (rendimiento < costo)",
        "score": 33
      },
      {
        "texto": "Deuda productiva (hipoteca, negocio), rentable",
        "score": 67
      },
      {
        "texto": "Sin deuda significativa o inversión en activos",
        "score": 100
      }
    ]
  },
  {
    "id": 463,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Puedes refinanciar tu deuda si suben los tipos de interés?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, estoy atrapado",
        "score": 0
      },
      {
        "texto": "Difícil, mala posición crediticia",
        "score": 33
      },
      {
        "texto": "Probablemente sí, con costos moderados",
        "score": 67
      },
      {
        "texto": "Fácil, muy buena posición",
        "score": 100
      }
    ]
  },
  {
    "id": 464,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes acceso a crédito si necesitas dinero hoy?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, me rechazarían",
        "score": 0
      },
      {
        "texto": "Sí, pero caro (tasa muy alta)",
        "score": 33
      },
      {
        "texto": "Sí, condiciones razonables",
        "score": 67
      },
      {
        "texto": "Sí, líneas múltiples a tasas bajas",
        "score": 100
      }
    ]
  },
  {
    "id": 465,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has reestructurado deuda alguna vez?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, nunca lo he considerado",
        "score": 0
      },
      {
        "texto": "Pensé en ello pero no lo hice",
        "score": 33
      },
      {
        "texto": "Sí, una vez, resultó bien",
        "score": 67
      },
      {
        "texto": "Sí, múltiples veces, estrategia sistemática",
        "score": 100
      }
    ]
  },
  {
    "id": 466,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es la cobertura de tu deuda (ingresos / pagos)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Menos de 1.2x (muy ajustado)",
        "score": 0
      },
      {
        "texto": "1.2x a 1.5x (ajustado)",
        "score": 33
      },
      {
        "texto": "1.5x a 2x (cómodo)",
        "score": 67
      },
      {
        "texto": "Mayor que 2x (muy robusto)",
        "score": 100
      }
    ]
  },
  {
    "id": 467,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has fijado la tasa de interés en tu deuda variable?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, está variable al 100%",
        "score": 0
      },
      {
        "texto": "Parcialmente, algo de variable",
        "score": 33
      },
      {
        "texto": "Mayormente fijo, pequeña exposición",
        "score": 67
      },
      {
        "texto": "100% fijo o cobertura de riesgo",
        "score": 100
      }
    ]
  },
  {
    "id": 468,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál sería el impacto de subida de tasas del 2%?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Crisis inmediata",
        "score": 0
      },
      {
        "texto": "Impacto severo en flujo",
        "score": 33
      },
      {
        "texto": "Incómodo pero manejable",
        "score": 67
      },
      {
        "texto": "Casi imperceptible",
        "score": 100
      }
    ]
  },
  {
    "id": 469,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes plazo suficiente en tu deuda (amortización)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Muy corto, pago alto inmediato",
        "score": 0
      },
      {
        "texto": "Corto, 2-5 años",
        "score": 33
      },
      {
        "texto": "Moderado, 5-15 años",
        "score": 67
      },
      {
        "texto": "Largo, mayor a 15 años",
        "score": 100
      }
    ]
  },
  {
    "id": 470,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Sabes qué accionistas o acreedores te podrían impugnar?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, no lo he pensado",
        "score": 0
      },
      {
        "texto": "Idea vaga",
        "score": 33
      },
      {
        "texto": "Sí, he identificado riesgos",
        "score": 67
      },
      {
        "texto": "Sí, tengo defensa estructurada",
        "score": 100
      }
    ]
  },
  {
    "id": 471,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es el máximo plazo de deuda que has asumido?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No tengo deuda",
        "score": 100
      },
      {
        "texto": "Menos de 5 años",
        "score": 33
      },
      {
        "texto": "5-15 años",
        "score": 67
      },
      {
        "texto": "Más de 15 años",
        "score": 67
      }
    ]
  },
  {
    "id": 472,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes cláusulas de aceleración en tu deuda (prepago)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, penalizadas o sin opción",
        "score": 0
      },
      {
        "texto": "Sí, pero con penalización",
        "score": 33
      },
      {
        "texto": "Sí, sin penalización moderada",
        "score": 67
      },
      {
        "texto": "Sí, prepago sin costo",
        "score": 100
      }
    ]
  },
  {
    "id": 473,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es el vencimiento promedio de tu deuda?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Menos de 1 año (concentrado)",
        "score": 0
      },
      {
        "texto": "1-3 años",
        "score": 33
      },
      {
        "texto": "3-7 años",
        "score": 67
      },
      {
        "texto": "Más de 7 años (bien distribuido)",
        "score": 100
      }
    ]
  },
  {
    "id": 474,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has negociado covenant (convenios) con acreedores?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, me dictan términos",
        "score": 0
      },
      {
        "texto": "Intenté, con poco éxito",
        "score": 33
      },
      {
        "texto": "Sí, algunos ajustes",
        "score": 67
      },
      {
        "texto": "Sí, términos bien negociados",
        "score": 100
      }
    ]
  },
  {
    "id": 475,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tu deuda es recourse (personal) o non-recourse?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Totalmente recourse",
        "score": 0
      },
      {
        "texto": "Mayormente recourse",
        "score": 33
      },
      {
        "texto": "Mixta",
        "score": 67
      },
      {
        "texto": "Non-recourse o garantizada por activos",
        "score": 100
      }
    ]
  },
  {
    "id": 476,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has modelado escenario de bancarrota?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, me asusta",
        "score": 0
      },
      {
        "texto": "Brevemente, no tengo plan",
        "score": 33
      },
      {
        "texto": "Sí, conozco opciones",
        "score": 67
      },
      {
        "texto": "Sí, tengo estrategia definida",
        "score": 100
      }
    ]
  },
  {
    "id": 477,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tu deuda está en moneda extranjera?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, 100% en divisa extranjera",
        "score": 0
      },
      {
        "texto": "Parcialmente, riesgo de cambio",
        "score": 33
      },
      {
        "texto": "No, está en moneda local",
        "score": 100
      },
      {
        "texto": "No tengo deuda",
        "score": 100
      }
    ]
  },
  {
    "id": 478,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes seguro de desempleo o invalidez?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, completamente desprotegido",
        "score": 0
      },
      {
        "texto": "Sí, pero cobertura baja",
        "score": 33
      },
      {
        "texto": "Sí, cobertura decente",
        "score": 67
      },
      {
        "texto": "Sí, cobertura completa",
        "score": 100
      }
    ]
  },
  {
    "id": 479,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has declarado tu patrimonio en una crisis?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, nunca",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 33
      },
      {
        "texto": "Sí, de manera incompleta",
        "score": 67
      },
      {
        "texto": "Sí, completa y verificada",
        "score": 100
      }
    ]
  },
  {
    "id": 480,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es tu tasa promedio ponderada de deuda?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No lo sé",
        "score": 0
      },
      {
        "texto": "Idea vaga",
        "score": 33
      },
      {
        "texto": "Lo sé, tasa promedio",
        "score": 67
      },
      {
        "texto": "Lo sé exactamente, optimizada",
        "score": 100
      }
    ]
  },
  {
    "id": 481,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has comparado tu deuda con benchmarks?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Vagamente",
        "score": 33
      },
      {
        "texto": "Sí, contra pares",
        "score": 67
      },
      {
        "texto": "Sí, contra benchmark formal",
        "score": 100
      }
    ]
  },
  {
    "id": 482,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes diversidad en tus acreedores?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, uno o dos",
        "score": 0
      },
      {
        "texto": "Parcialmente diverso",
        "score": 33
      },
      {
        "texto": "Bien diverso",
        "score": 67
      },
      {
        "texto": "Muy diverso, poco riesgo de concentración",
        "score": 100
      }
    ]
  },
  {
    "id": 483,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál fue tu peor crisis de deuda y cómo la resolviste?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No recuerdo o fue muy grave",
        "score": 0
      },
      {
        "texto": "Recuerdo, fue difícil",
        "score": 33
      },
      {
        "texto": "Recuerdo, la manejé bien",
        "score": 67
      },
      {
        "texto": "La convertí en oportunidad",
        "score": 100
      }
    ]
  },
  {
    "id": 484,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has renegociado tasa con un acreedor?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Nunca lo intenté",
        "score": 0
      },
      {
        "texto": "Lo intenté sin éxito",
        "score": 33
      },
      {
        "texto": "Sí, conseguí reducción modesta",
        "score": 67
      },
      {
        "texto": "Sí, renegociación estratégica exitosa",
        "score": 100
      }
    ]
  },
  {
    "id": 485,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tu deuda es senior o subordinada?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Subordinada, último lugar",
        "score": 0
      },
      {
        "texto": "Mixta",
        "score": 33
      },
      {
        "texto": "Mayormente senior",
        "score": 67
      },
      {
        "texto": "Senior o garantizada plenamente",
        "score": 100
      }
    ]
  },
  {
    "id": 486,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has asegurado tus acreedores principales?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, sin protección",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 33
      },
      {
        "texto": "Sí, básicamente",
        "score": 67
      },
      {
        "texto": "Sí, completamente asegurado",
        "score": 100
      }
    ]
  },
  {
    "id": 487,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es el LTV (ratio préstamo/valor) de tu deuda?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No lo sé",
        "score": 0
      },
      {
        "texto": "Mayor que 80%",
        "score": 33
      },
      {
        "texto": "60-80%",
        "score": 67
      },
      {
        "texto": "Menor que 60% o sin colateral",
        "score": 100
      }
    ]
  },
  {
    "id": 488,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has estructurado deuda con opciones de conversión?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Idea vaga",
        "score": 33
      },
      {
        "texto": "Sí, parcialmente",
        "score": 67
      },
      {
        "texto": "Sí, estrategia deliberada",
        "score": 100
      }
    ]
  },
  {
    "id": 489,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tu deuda tiene correlación con tu flujo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, positiva (ambos caen)",
        "score": 0
      },
      {
        "texto": "Parcialmente correlada",
        "score": 33
      },
      {
        "texto": "Poco correlada",
        "score": 67
      },
      {
        "texto": "Negativa (se compensan)",
        "score": 100
      }
    ]
  },
  {
    "id": 490,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has proyectado cero deuda? ¿Cuándo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, nunca",
        "score": 0
      },
      {
        "texto": "Idea vaga, sin timeline",
        "score": 33
      },
      {
        "texto": "Sí, en 10+ años",
        "score": 67
      },
      {
        "texto": "Sí, en menos de 5 años o sin deuda",
        "score": 100
      }
    ]
  },
  {
    "id": 491,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes contrato de deuda escrito?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, informal",
        "score": 0
      },
      {
        "texto": "Sí, pero básico",
        "score": 33
      },
      {
        "texto": "Sí, documento formal",
        "score": 67
      },
      {
        "texto": "Sí, abogado, bien estructurado",
        "score": 100
      }
    ]
  },
  {
    "id": 492,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Cuál es tu línea de crédito no utilizada?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Cero o muy pequeña",
        "score": 0
      },
      {
        "texto": "Menor a 1 mes de gasto",
        "score": 33
      },
      {
        "texto": "1-3 meses de gasto",
        "score": 67
      },
      {
        "texto": "Mayor a 6 meses de gasto",
        "score": 100
      }
    ]
  },
  {
    "id": 493,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tu deuda es transparente con tu pareja/familia?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, oculta",
        "score": 0
      },
      {
        "texto": "Parcialmente conocida",
        "score": 33
      },
      {
        "texto": "Sí, conocida pero no acordada",
        "score": 67
      },
      {
        "texto": "Sí, totalmente transparente y acordada",
        "score": 100
      }
    ]
  },
  {
    "id": 494,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has considerado restructuring preventivo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Sí, pero es complicado",
        "score": 33
      },
      {
        "texto": "Sí, lo he modelado",
        "score": 67
      },
      {
        "texto": "Sí, es parte de mi plan",
        "score": 100
      }
    ]
  },
  {
    "id": 495,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Qué % de deuda es de corto plazo?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Mayor al 50%",
        "score": 0
      },
      {
        "texto": "30-50%",
        "score": 33
      },
      {
        "texto": "10-30%",
        "score": 67
      },
      {
        "texto": "Menor al 10%",
        "score": 100
      }
    ]
  },
  {
    "id": 496,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes acreedor que podría causar pánico de banco?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, muy probable",
        "score": 0
      },
      {
        "texto": "Sí, posible",
        "score": 33
      },
      {
        "texto": "Poco probable",
        "score": 67
      },
      {
        "texto": "No, estructura resiliente",
        "score": 100
      }
    ]
  },
  {
    "id": 497,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tu deuda tiene cláusula de tasa base (floor)?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, expuesto completamente",
        "score": 0
      },
      {
        "texto": "Parcialmente",
        "score": 33
      },
      {
        "texto": "Sí, some protection",
        "score": 67
      },
      {
        "texto": "Sí, full protection or fixed",
        "score": 100
      }
    ]
  },
  {
    "id": 498,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Has calculado tu debt service coverage ratio?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No",
        "score": 0
      },
      {
        "texto": "Idea vaga",
        "score": 33
      },
      {
        "texto": "Sí, lo conozco",
        "score": 67
      },
      {
        "texto": "Sí, lo monitorizoactivmente",
        "score": 100
      }
    ]
  },
  {
    "id": 499,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tienes deuda relacionada con personas familiares?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "Sí, significativa y sin contrato",
        "score": 0
      },
      {
        "texto": "Sí, pero parcialmente formalizada",
        "score": 33
      },
      {
        "texto": "Sí, formalizada legalmente",
        "score": 67
      },
      {
        "texto": "No o completamente formalizada",
        "score": 100
      }
    ]
  },
  {
    "id": 500,
    "categoria": "resiliencia_deuda",
    "pregunta": "¿Tu deuda es resiliente a crisis del -30% en ingresos?",
    "tipo": "escala",
    "opciones": [
      {
        "texto": "No, sería insolvencia",
        "score": 0
      },
      {
        "texto": "Difícil, requeriría ajustes drásticos",
        "score": 33
      },
      {
        "texto": "Manejable con cierto esfuerzo",
        "score": 67
      },
      {
        "texto": "Fácil, todavía cubierto",
        "score": 100
      }
    ]
  }
]

PREGUNTAS_ABIERTAS = [
  "Si no existiera el dinero, ¿cómo sería tu vida ideal?",
  "¿Cuál es la peor pesadilla financiera que te mantiene despierto?",
  "Describe la conversación sobre dinero más incómoda que has tenido",
  "¿Qué te gustaría que tu dinero te permitiera hacer en 5 años?",
  "¿Quién en tu familia te enseñó (bien o mal) sobre el dinero?",
  "Si tuvieras €100.000 ahora, ¿en qué lo gastarías primero y por qué?",
  "¿Cuál es el mayor conflicto financiero en tu relación de pareja?",
  "¿Qué creencia sobre el dinero heredaste que te limita hoy?",
  "Describe un momento en que el dinero te hizo sentir poderoso o humillado",
  "¿Qué evitas admitir sobre tu situación financiera actual?",
  "Si pudieras cambiar UNA cosa de tu vida financiera, ¿cuál sería?",
  "¿A quién le pides consejo sobre dinero y por qué (o por qué no)?",
  "¿Cuál es tu mayor miedo al invertir o hacer crecer tu dinero?",
  "Describe cómo el estrés financiero afecta tu salud y relaciones",
  "¿Qué te hace sentir que no mereces dinero o éxito?",
  "¿Cuál es tu mayor fortaleza financiera no reconocida?",
  "Si no tuvieras responsabilidades, ¿qué harías con tu vida profesional?",
  "¿Qué consejo sobre dinero darías a tu yo de 10 años atrás?",
  "Describe el impacto que ha tenido el dinero (o su falta) en tu autoestima",
  "¿Cuál es tu plan real para los próximos 2 años y qué lo bloquea?"
]

# ==================== ENDPOINT CORREGIDO ====================
@app.get("/api/questions/{tier}")
async def get_questions(tier: int):
    """Devuelve preguntas según tier (100, 200, 500 cerradas + 20 abiertas)"""
    if tier == 1:
        limite = 100
    elif tier == 2:
        limite = 200
    elif tier == 3:
        limite = 500
    else:
        raise HTTPException(status_code=400, detail="Tier inválido")
    
    # Filtrar preguntas por límite del tier
    questions_filtered = [q for q in PREGUNTAS_CERRADAS if q["id"] <= limite]
    
    return {
        "tier_solicitado": tier,
        "total_preguntas": len(questions_filtered) + len(PREGUNTAS_ABIERTAS),
        "total_cerradas": len(questions_filtered),
        "total_abiertas": len(PREGUNTAS_ABIERTAS),
        "questions": questions_filtered,
        "open_questions": PREGUNTAS_ABIERTAS
    }


@app.get("/api/questions/{tier}")
def get_questions(tier: int, db: Session = Depends(get_db)):
    """Devuelve preguntas según tier"""
    if tier not in TIER_CONFIG:
        raise HTTPException(status_code=400, detail="Tier inválido")

    count = TIER_CONFIG[tier]["questions"]
    return {
        "tier": tier,
        "questions": PREGUNTAS_BASE[:count],
        "open_questions": PREGUNTAS_ABIERTAS
    }

@app.post("/api/answer")
def submit_answer(req: AnswerRequest, db: Session = Depends(get_db)):
    """Guarda una respuesta"""
    eval_obj = db.query(EvaluationModel).filter_by(session_id=req.session_id).first()
    if not eval_obj:
        raise HTTPException(status_code=404, detail="Session no encontrada")

    answers = eval_obj.answers or {}
    answers[str(req.question_id)] = req.answer_value
    eval_obj.answers = answers
    db.commit()

    return {"ok": True}

@app.post("/api/open-answer")
def submit_open_answer(req: OpenAnswerRequest, db: Session = Depends(get_db)):
    """Guarda una respuesta abierta"""
    eval_obj = db.query(EvaluationModel).filter_by(session_id=req.session_id).first()
    if not eval_obj:
        raise HTTPException(status_code=404, detail="Session no encontrada")

    open_ans = eval_obj.open_answers or {}
    open_ans[str(req.question_id)] = req.answer_text
    eval_obj.open_answers = open_ans
    db.commit()

    return {"ok": True}

@app.post("/api/complete")
def complete_evaluation(req: CompleteEvaluationRequest, db: Session = Depends(get_db)):
    """Completa evaluación y genera PDF"""
    eval_obj = db.query(EvaluationModel).filter_by(session_id=req.session_id).first()
    if not eval_obj:
        raise HTTPException(status_code=404, detail="Session no encontrada")

    # Calcula score
    answers = eval_obj.answers or {}
    score = sum(int(v) for v in answers.values()) if answers else 0
    max_score = len(answers) * 5
    score_pct = (score / max_score * 100) if max_score > 0 else 0

    # Detecta perfil
    if score_pct < 30:
        profile = "RESILIENTE"
    elif score_pct < 60:
        profile = "EQUILIBRADO"
    else:
        profile = "ESTRESADO"

    eval_obj.score = score
    eval_obj.profile = profile
    eval_obj.is_complete = True
    eval_obj.completed_at = datetime.utcnow()
    db.commit()

    # Genera PDF
    pdf_bytes = generate_pdf(eval_obj)

    return {
        "session_id": req.session_id,
        "score": score,
        "score_pct": round(score_pct, 1),
        "profile": profile,
        "pdf_ready": True,
        "stripe_link": STRIPE_LINKS[eval_obj.tier]
    }

def generate_pdf(eval_obj: EvaluationModel) -> bytes:
    """Genera PDF profesional con análisis"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0284c7'),
        spaceAfter=12,
        alignment=1
    )
    story.append(Paragraph("Evaluación Patrimonial Personalizada", title_style))
    story.append(Spacer(1, 0.3*inch))

    # Info general
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=10)
    story.append(Paragraph(f"<b>Email:</b> {eval_obj.email}", info_style))
    story.append(Paragraph(f"<b>Tier:</b> {TIER_CONFIG[eval_obj.tier]['name']}", info_style))
    story.append(Paragraph(f"<b>Fecha:</b> {eval_obj.completed_at.strftime('%Y-%m-%d %H:%M')}", info_style))
    story.append(Spacer(1, 0.3*inch))

    # Resultados
    story.append(Paragraph("<b>Resultados de tu Evaluación</b>", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))

    # Score visual
    score_pct = (eval_obj.score / (len(eval_obj.answers) * 5) * 100) if eval_obj.answers else 0
    story.append(Paragraph(f"<b>Score Global:</b> {round(score_pct, 1)}%", info_style))
    story.append(Paragraph(f"<b>Perfil:</b> {eval_obj.profile}", info_style))
    story.append(Spacer(1, 0.3*inch))

    # Análisis
    story.append(Paragraph("<b>Análisis Personalizado</b>", styles['Heading2']))

    if eval_obj.profile == "RESILIENTE":
        analysis = "Tu gestión financiera muestra estabilidad. Continúa manteniendo tus buenos hábitos y considera optimizar tu estrategia de inversión a largo plazo."
    elif eval_obj.profile == "EQUILIBRADO":
        analysis = "Tu relación con el dinero es equilibrada. Hay oportunidades para mejorar: enfócate en aumentar tus ahorros y revisar tu estructura de gastos."
    else:
        analysis = "Detectamos estrés financiero significativo. Te recomendamos urgentemente consultar con un asesor para crear un plan de acción concreto."

    story.append(Paragraph(analysis, info_style))
    story.append(Spacer(1, 0.3*inch))

    # Respuestas abiertas
    if eval_obj.open_answers:
        story.append(PageBreak())
        story.append(Paragraph("<b>Tus Respuestas Detalladas</b>", styles['Heading2']))
        story.append(Spacer(1, 0.2*inch))

        for q_id, answer in eval_obj.open_answers.items():
            question = PREGUNTAS_ABIERTAS[int(q_id)] if int(q_id) < len(PREGUNTAS_ABIERTAS) else "Pregunta"
            story.append(Paragraph(f"<b>P:</b> {question}", info_style))
            story.append(Paragraph(f"<b>R:</b> {answer}", info_style))
            story.append(Spacer(1, 0.15*inch))

    # Footer
    story.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    story.append(Paragraph("Este informe fue generado por ITAP Financial Strategy. Confidencial.", footer_style))

    doc.build(story)
    return buffer.getvalue()

@app.get("/api/pdf/{session_id}")
def download_pdf(session_id: str, db: Session = Depends(get_db)):
    """Descarga PDF de la evaluación"""
    eval_obj = db.query(EvaluationModel).filter_by(session_id=session_id).first()
    if not eval_obj or not eval_obj.is_complete:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    pdf_bytes = generate_pdf(eval_obj)
    return FileResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        filename=f"ITAP_Evaluation_{session_id}.pdf"
    )

@app.get("/api/draft/{session_id}/pdf")
def download_pdf_alias(session_id: str, db: Session = Depends(get_db)):
    """Alias para compatibilidad con Stripe (redirige a /api/pdf/)"""
    return download_pdf(session_id, db)

class FallbackRequest(BaseModel):
    email: str

@app.post("/api/report/request-fallback")
def report_fallback(req: FallbackRequest, db: Session = Depends(get_db)):
    """Endpoint de contingencia: busca usuario por email y devuelve session_id"""
    eval_obj = db.query(EvaluationModel).filter_by(email=req.email).order_by(EvaluationModel.created_at.desc()).first()

    if not eval_obj or not eval_obj.is_complete:
        raise HTTPException(status_code=404, detail="No encontrado")

    return {
        "status": "found",
        "session_id": eval_obj.session_id,
        "email": eval_obj.email,
        "message": "Tu informe ha sido enviado a tu email"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
