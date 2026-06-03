# 🚀 DEPLOY A RENDER — INSTRUCCIONES RÁPIDAS

## Paso 1: Preparar GitHub (2 min)

```bash
# En tu carpeta local con los archivos:
git init
git add .
git commit -m "Initial commit: GDPR diagnostic system production-ready"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/diagnostico-financiero.git
git push -u origin main
```

**O si ya tienes repo:**
```bash
git add requirements.txt render.yaml .env.example app_standalone_FINAL.py
git commit -m "Add deployment configuration for Render"
git push
```

---

## Paso 2: Conectar Render (3 min)

1. Ve a **render.com** (login con GitHub)
2. Click en **"New +"** → **"Web Service"**
3. Selecciona tu repo `diagnostico-financiero`
4. Render detecta `render.yaml` automáticamente ✓
5. Click **"Deploy"**

---

## Paso 3: Esperar deploy (5 min)

- Render instala dependencias
- Inicia uvicorn
- Te genera URL pública automáticamente

**Ejemplo resultado:** `https://gdpr-diagnostic-api.onrender.com`

---

## Paso 4: Probar (1 min)

Una vez que Render dice "Live":

```bash
curl https://gdpr-diagnostic-api.onrender.com/health
# Response: {"status":"ok"}
```

O abre en navegador:
```
https://gdpr-diagnostic-api.onrender.com/health
```

---

## URLs de tu API en Render:

- ✓ Health: `https://gdpr-diagnostic-api.onrender.com/health`
- ✓ Schema: `https://gdpr-diagnostic-api.onrender.com/api/v1/schema`
- ✓ Consent init: `POST https://gdpr-diagnostic-api.onrender.com/api/v1/consent/init`
- ✓ Tests: ejecutar contra la URL base

---

## Troubleshooting Rápido

**"No encuentra requirements.txt"**
→ Render necesita que esté en root del repo. Verificar.

**"Module not found: app_standalone_FINAL"**
→ Verificar que `app_standalone_FINAL.py` esté en root.

**"Port already in use"**
→ Render usa variable `$PORT`. Verificar `startCommand` en render.yaml.

**SQLite: "disk I/O error"**
→ Normal en free tier. App recrea DB en cada deploy. OK para testing.

---

## ¿Listo?

Cuando tengas URL, pásala aquí y ejecuto los 8 tests contra ella. 🎯
