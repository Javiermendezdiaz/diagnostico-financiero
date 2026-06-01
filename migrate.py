#!/usr/bin/env python3
"""
MIGRATE — Espejo Fantasma BD migration script
Crea tablas de ORM en PostgreSQL production
TOP 1% MUNDIAL
"""

import os
import logging
from sqlalchemy import create_engine
from couple_management import Base

logger = logging.getLogger(__name__)

def migrate():
    """Crear todas las tablas en BD"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL no está configurada")
    
    logger.info(f"Conectando a: {database_url}")
    
    engine = create_engine(database_url, echo=False)
    
    # Crear todas las tablas
    logger.info("Creando tablas...")
    Base.metadata.create_all(engine)
    
    logger.info("✅ Migración completada exitosamente")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate()
