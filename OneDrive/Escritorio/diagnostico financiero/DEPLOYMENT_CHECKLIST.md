# 🚀 Deployment Checklist — Render.com

**Status: PRODUCTION READY**

Validación completada: ✅ Node.js v22, Python 3.10, todos los archivos presentes, build scripts ejecutables.

---

## PASO 1: Git & GitHub (Tu máquina local)

Ejecuta en terminal desde `C:\Users\javie\OneDrive\Escritorio\diagnostico financiero`:

```bash
# Init repo
git init
git config user.email "javier@mendezconsultoria.com"
git config user.name "Javier Mendez"
git add .
git commit -m "Production-ready: React 18 + Vite + FastAPI + Render deployment"
git branch -M main

# Create GitHub repo
# 1. Open https://github.com/new
# 2. Repository name: diagnostico-financiero
# 3. Set to PUBLIC (Render needs read access)
# 4. Click Create

# Connect & push (replace USUARIO con tu GitHub username)
git remote add origin https://github.com/USUARIO/diagnostico-financiero.git
git push -u origin main
```

---

## PASO 2: Render Setup

1. **Login**: https://dashboard.render.com
2. **New Service**
   - Click: "New" → "Web Service"
   - Select: `diagnostico-financiero` repository
   - Render auto-detects `render.yaml`

3. **Confirm Settings**
   - ✅ Name: `diagnostico-financiero-v6`
   - ✅ Runtime: `Python 3.11`
   - ✅ Build Command: `./build.sh`
   - ✅ Start Command: `python app_standalone.py`
   - ✅ NODE_ENV: `production`

4. **Deploy**
   - Click "Create Web Service"
   - Wait for build (3-5 minutes)
   - Render will show you the live URL

---

## PASO 3: Post-Deployment Validation

Once Render finishes (check dashboard for "Live"):

```bash
# Copy YOUR_URL from Render dashboard (e.g., diagnostico-financiero-v6.onrender.com)

# Test health
curl https://YOUR_URL/health

# Test API schema
curl https://YOUR_URL/api/v1/schema | head -50

# Test in browser
# 1. Open https://YOUR_URL
# 2. Answer 10+ questions
# 3. Submit
# 4. Verify PDF downloads
```

---

## PASO 4: Full Flow Test

In browser at `https://YOUR_URL`:

- ✅ Load questionnaire (should fetch 500 questions from `/api/v1/schema`)
- ✅ Answer 10+ questions
- ✅ Use Back button (verify history tracking)
- ✅ Submit
- ✅ Download PDF (verify report generation)
- ✅ Check Render logs for no errors

---

## What's Deployed

```
├── Frontend (React 18)
│   ├── 500-question questionnaire
│   ├── Memory leak fixes (useCallback, React.memo, O(1) lookups)
│   ├── Navigation with history tracking
│   └── PDF download capability
│
├── Backend (FastAPI)
│   ├── GET /health → Health check
│   ├── GET /api/v1/schema → 500 questions + metadata
│   ├── POST /api/v1/diagnose → Score answers + generate PDF
│   └── StaticFiles mount (dist/) → Serve React SPA
│
└── Build Pipeline
    ├── npm install + npm run build (React optimized)
    ├── pip install requirements.txt (Python deps)
    └── Single Python process (all-in-one dyno)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check Render build logs for npm/pip errors |
| App won't load | Verify `/api/v1/schema` in browser console (F12 → Network) |
| PDF generation fails | Check Render logs for reportlab errors |
| Slow response | Normal for first request; Render spins down idle dynos |
| Port binding error | Render assigns PORT env var; app_standalone.py reads it ✅ |

---

## Quick Links

- **Render Dashboard**: https://dashboard.render.com
- **GitHub Repo**: https://github.com/USUARIO/diagnostico-financiero
- **Live URL**: https://diagnostico-financiero-v6.onrender.com (once deployed)

---

**Next Action**: Execute PASO 1 commands from your terminal.  
**ETA**: ~8 minutes total (git + GitHub + Render build + validation).
