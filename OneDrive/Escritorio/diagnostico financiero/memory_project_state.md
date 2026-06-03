# MEMORIA: Proyecto Diagnóstico Financiero

**Última actualización:** 2026-05-29 | **Estado:** Tasks #1-31 creadas, roadmap completo mapeado

## Estado Crítico
- **Platform:** Diagnóstico Financiero (Quiz → Payment → PDF → Referral → Dashboard → Certificate)
- **Compliance:** RGPD España STRICT, zero AEPD risk, siempre consentimiento explícito
- **Arquitectura:** FastAPI + React 18 + PostgreSQL + Puppeteer + Bizum
- **Scope total:** 55 horas dev + testing + auditoría legal externa 2-3 weeks

---

## Tareas Completadas (1-31)

| Rango | Bloque | Estado | Horas |
|-------|--------|--------|-------|
| #1-20 | Frontend componentes core | ✅ Especificadas | ~12 |
| #21-28 | **RGPD Foundation** (crítica) | ✅ Creadas | ~25 |
| #29-31 | Bloque 1: PDF Generation | ✅ Creadas | ~6 |

**RGPD Foundation tareas (#21-28):**
- DataProcessingRecord ORM + LegalBasis enum
- Encryption layer (PBKDF2 + Fernet per-user keys)
- ConsentManagement (give/withdraw endpoints)
- User Rights (access/deletion/portability)
- Third Party Processor DPA management
- Breach Notification protocol (<72h AEPD)
- Privacy Policy UI component
- Retention policy + auto-cleanup cron

---

## Tareas Pendientes (32-49)

| Bloque | Tasks | Horas | Paralela |
|--------|-------|-------|----------|
| **Bloque 2** (FE Hooks) | #32-34 | ~5 | Con auditoría |
| **Bloque 2.5** (OG Preview) | #35-37 | ~4.5 | Con auditoría |
| **Bloque 4** (Dashboard+Cert) | #38-42 | ~8.5 | Con auditoría |
| **Bloque 3** (E2E Testing) | #43-49 | ~6 | Final |
| **Auditoría Externa** | Legal/RGPD/CNMV | 2-3 weeks | **PARALELA** |

---

## Decisión Pendiente MAÑANA

**Opción recomendada: RGPD-First**
1. Implementar Tareas #21-28 (RGPD Foundation) — bloquea todo lo demás
2. Implementar Tareas #29-31 (PDF core) — integra RGPD guards
3. Paralelo: Iniciar auditoría externa (Deloitte/KPMG)
4. Luego: Bloques 2, 2.5, 4 mientras auditoría se ejecuta

---

## Notas Clave

- **User:** Javier, Adapta Family Office (mendezconsultoria.com)
- **Preferencia:** "MUY PROFESIONAL, CONCISA E IMPACTANTE. 1% del conocimiento"
- **Critical directive:** "la app debe regirse por la rgpd española lo mas estrictamente posible evitando cualquier tipo de sancion y siemmpre con el consentimiento del cliente. este punto es critico"
- **Removed:** BookOpen component (énfasis: "el libro no por favor, eliminar seguro")
- **Lead Gen:** Anonimizado (uuid4 internal), tier-based PDF mutation, CNMV compliance
- **Próximo step:** Confirmar orden implementación, iniciar Task #21 (DataProcessingRecord ORM)
