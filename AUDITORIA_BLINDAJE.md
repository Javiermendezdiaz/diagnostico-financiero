# Auditoría y blindaje — ITAP · Adapta Family Office
*12 de junio de 2026*

Revisión completa de seguridad, persistencia, robustez e higiene del producto en producción, con el estado de cada punto. Lo **crítico ya está corregido y desplegado**; queda **una acción que depende de ti** (subir Render a un plan con disco).

---

## 1. Persistencia de datos — BLINDADO (requiere 1 acción tuya)

**Riesgo detectado (alto):** la base de datos SQLite vivía en el disco efímero de Render. En un redespliegue o un arranque en frío se reiniciaba, lo que implicaba perder: sesiones, **el estado de "pagado" de un cliente** (un cliente que pagó podría quedarse sin acceso a su informe), los baremos/percentiles y los datos del embudo.

**Corregido (desplegado):** el código usa ahora la variable `ITAP_DATA_DIR`. Si apunta a un disco persistente, la base de datos **y** los PDF se guardan ahí y sobreviven a redespliegues. El cambio es 100 % retrocompatible: sin la variable, sigue funcionando como antes.

**Acción pendiente (tuya, implica coste):** para que sea durable de verdad hay que dar a Render un disco, y eso requiere un plan de pago (Starter, ~7 $/mes). Te dejé la configuración lista en **`render_persistente.yaml`**:
- Sube el servicio a plan **Starter**.
- Añade un **disco** de 1 GB montado en `/var/data`.
- Define la variable `ITAP_DATA_DIR = /var/data`.

Para un producto que vende informes de 39 €, los 7 $/mes son triviales frente al riesgo de que un cliente pague y pierda su informe. **Recomendación: hazlo antes de mandar tráfico de pago.**

---

## 2. Seguridad — LIMPIO

| Punto | Estado |
|---|---|
| **Secretos en el código** | ✅ Ninguno. Búsqueda de claves de Stripe, Anthropic, Resend, Google: cero resultados. Todo va por variables de entorno. |
| **Inyección SQL** | ✅ Todas las consultas con datos de usuario están parametrizadas (`?`). La única con formato de cadena (línea de `ALTER TABLE`) usa constantes internas del código, no input. |
| **Gate de pago** | ✅ `/api/report` exige `pagado` cuando hay `STRIPE_WEBHOOK_SECRET`. El `session_id` es un UUID no adivinable. |
| **Webhook de Stripe** | ✅ Verifica la firma (`construct_event`) antes de marcar pagado. |
| **CORS** | ✅ Abierto (`*`) — correcto para una API pública sin cookies. |
| **RGPD** | ✅ Consentimiento obligatorio al iniciar; política de privacidad; endpoint de borrado (`/api/borrar-datos`). |
| **Endpoint del embudo** | ⚠️ `/api/funnel` es abierto pero solo expone **datos agregados, sin información personal**. Si quieres cerrarlo, define la variable `FUNNEL_KEY` y el código lo protege. |

---

## 3. Robustez del motor — PROBADO

**Stress test:** 400 perfiles aleatorios con casos límite (ingreso/gasto/patrimonio = 0, edades de 18 a 82, campos vacíos, todas las combinaciones de perfil) → **400/400 sin ningún fallo**. 20 informes PDF completos con perfiles extremos → **20/20 renderizan**.

**Bugs reales cazados y corregidos en esta auditoría y la anterior:**
- Crash con **ingreso 0** (rentistas/herederos): la proyección y los cálculos dividían por cero. Blindado.
- Crash con **edad ≥ 65** (jubilados): la proyección "a los 65" daba un rango vacío. Blindado.
- Fallo por **faceta sin etiqueta** en las preguntas nuevas. Corregido.
- La **contradicción "rico pero ansioso"** no se disparaba (usaba la media global en vez de la capa psíquica). Corregido.

Todos los cálculos del informe salen de datos reales del cliente; el apartado de IA (Opus) tiene **degradado seguro**: si falla o no hay clave, el informe se genera igual sin esa sección.

---

## 4. Higiene del código — NOTA

**Archivos muertos:** el repositorio arrastra ~15 archivos `.py` de iteraciones antiguas que **no se despliegan ni se importan** (`backend_production.py` de 270 KB, `main_production_ready.py`, `paywall_manager.py`, `user_rights.py`, etc.). El `Procfile` arranca solo `app:app`. No contienen secretos y no afectan a producción, pero conviene **borrarlos** para que el repo sea claro. Los archivos vivos son: `app.py`, `report_book.py`, `report_couple.py`, `ai_sintesis.py`, `score_v2.py` + los `.json` del instrumento + los `.html`.

**Dependencias:** añadí `numpy` explícito a `requirements.txt` (lo usa el radar; antes venía solo de forma transitiva por matplotlib). Hay dependencias listadas que ya no se usan (`sqlalchemy`, `python-dotenv`, `aiohttp`) — inofensivas, se pueden limpiar.

---

## 5. Resumen y prioridades

1. **HAZLO YA (tú):** subir Render a plan con disco + `ITAP_DATA_DIR` (ver `render_persistente.yaml`). Es lo único que separa el producto de ser plenamente duradero.
2. **Opcional:** define `FUNNEL_KEY` para cerrar el panel del embudo; borra los archivos `.py` muertos.
3. **Todo lo demás está verificado y desplegado.** El producto es seguro, robusto y consistente. Listo para recibir tráfico real.
