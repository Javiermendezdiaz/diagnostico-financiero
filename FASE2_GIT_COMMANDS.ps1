# ============================================================================
# FASE 2 DEPLOYMENT — Comandos PowerShell Secuenciales
# EJECUTAR UNO A UNO (sin usar &&)
# ============================================================================

# PASO 1: Verificar estado del repositorio
git status

# PASO 2: Agregar archivos modificados + nuevas migraciones
git add app_couple_endpoints.py
git add migrations_FASE2_SPRINT7_9_11.sql
git add psychology_backend_service.py
git add analytics_events_service.py
git add couple_management.py
git add sprint9_ab_testing_adapter.py
git add FASE2_ENDPOINTS_READY.py

# PASO 3: Verificar que todos los archivos estén staged
git status

# PASO 4: Hacer commit con mensaje descriptivo
git commit -m "FASE 2 INYECCIÓN: Endpoints DB-integrados (SPRINT 7+9+11) - Timer urgency + Social proof + FOMO + A/B testing + Analytics"

# PASO 5: Verificar que el commit se creó
git log --oneline -5

# PASO 6: Push a main (Render detecta automáticamente)
git push origin main

# PASO 7: Verificar que push fue exitoso
git status

# ============================================================================
# DESPUÉS DEL PUSH:
# ============================================================================
# 1. Esperar a que Render recompile (3-5 minutos en Render dashboard)
# 2. Verificar logs en Render para errores de DB migration
# 3. Ejecutar scripts de migración SQL si Render no lo detecta automático:
#    - psql $DATABASE_URL < migrations_FASE2_SPRINT7_9_11.sql
# 4. Testear endpoints en Postman:
#    POST /api/v1/sessions/create (debe asignar ab_cohort)
#    GET /api/v1/sessions/{id}/urgency (debe loguear evento)
#    POST /api/v1/tiers/basic/click (debe decrementar FOMO spot)

# ============================================================================
# COMANDO ALTERNATIVO: Si Render falla con migración SQL
# ============================================================================
# Ejecutar en terminal Render (uno a uno):
# heroku pg:psql --app <app-name> < migrations_FASE2_SPRINT7_9_11.sql
# O acceder a BD directamente:
# psql -h <db-host> -U <user> -d <dbname> < migrations_FASE2_SPRINT7_9_11.sql
