-- ============================================================================
-- ITAP TIER 2: MIGRACIÓN DE SEGMENTACIÓN DE PLANES
-- Patrón Expand & Contract: Zero-Downtime Migration
-- ============================================================================

-- Fase 1: Expansion (Agregar columnas con defaults para backward compatibility)
ALTER TABLE drafts
  ADD COLUMN max_closed_questions INT DEFAULT 100 NOT NULL,
  ADD COLUMN max_open_questions INT DEFAULT 20 NOT NULL,
  ADD COLUMN closed_answered_count INT DEFAULT 0 NOT NULL,
  ADD COLUMN open_answered_count INT DEFAULT 0 NOT NULL,
  ADD COLUMN is_finalized BOOLEAN DEFAULT FALSE NOT NULL;

-- Índice concurrente para queries de estado sin bloqueos de tabla
CREATE INDEX CONCURRENTLY idx_drafts_finalized
  ON drafts(is_finalized)
  WHERE is_finalized = TRUE;

-- Índice de búsqueda para sesiones activas (no finalizadas)
CREATE INDEX CONCURRENTLY idx_drafts_active
  ON drafts(id, is_finalized)
  WHERE is_finalized = FALSE;

-- ============================================================================
-- BLOQUE CRÍTICO DE IDEMPOTENCIA: Protección contra reintentos de red
-- ============================================================================
-- Garantizar que un borrador solo pueda tener UNA respuesta por cada pregunta
-- Si el frontend reintenta enviar la misma respuesta por parpadeo de red,
-- PostgreSQL la rechazará limpiamente con UNIQUE CONSTRAINT violation
ALTER TABLE draft_responses
  ADD CONSTRAINT unique_draft_question UNIQUE (draft_id, question_id);

-- Índice optimizado para resolver conflictos de duplicados de forma ultra veloz (Upsert ready)
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_unique_draft_question
  ON draft_responses (draft_id, question_id);

-- Verificación de integridad: confirmar que todos los drafts existentes hereden defaults correctos
-- (Este comando es idempotente si ya existen los valores por defecto)
UPDATE drafts
  SET max_closed_questions = CASE
        WHEN plan = 1 THEN 100
        WHEN plan = 2 THEN 200
        WHEN plan = 3 THEN 200
        ELSE 100
      END,
      max_open_questions = 20,
      closed_answered_count = 0,
      open_answered_count = 0,
      is_finalized = FALSE
  WHERE max_closed_questions IS NULL;

-- Confirmación
SELECT 'Migración ITAP Tier 2 completada exitosamente' AS status;
