-- ============================================================================
-- MIGRACIÓN FASE 2: SPRINT 7 + SPRINT 9 + SPRINT 11
-- BD: Agregar 11 campos a CoupleSession + tabla AnalyticsEvent
-- Fecha: 2026-06-03
-- ============================================================================

-- SPRINT 7: Timer urgency fields
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS session_urgency_started_at TIMESTAMP NULL;
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS session_urgency_expires_at TIMESTAMP NULL;
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS urgency_status VARCHAR(20) DEFAULT 'inactive';

-- SPRINT 7: Social proof fields
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS social_proof_city VARCHAR(50) NULL;
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS social_proof_generated_at TIMESTAMP NULL;

-- SPRINT 7: FOMO fields (decremental spots)
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS tier_spots_available_basic INTEGER DEFAULT 2;
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS tier_spots_available_professional INTEGER DEFAULT 1;
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS tier_spots_available_pareja INTEGER DEFAULT 3;
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS fomo_last_update_at TIMESTAMP NULL;

-- SPRINT 9: A/B Testing fields
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS ab_cohort VARCHAR(20) DEFAULT 'unknown';
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS ab_assigned_at TIMESTAMP NULL;
ALTER TABLE couple_sessions ADD COLUMN IF NOT EXISTS ab_variant_active BOOLEAN DEFAULT TRUE;

-- ============================================================================
-- SPRINT 11: AnalyticsEvent table — Registra eventos granulares
-- ============================================================================
CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    couple_session_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    ab_cohort VARCHAR(20) NOT NULL DEFAULT 'unknown',
    event_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (couple_session_id),
    INDEX idx_created_at (created_at)
);