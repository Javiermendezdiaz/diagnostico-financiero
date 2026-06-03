# Quick Start — 5 Minutes to Running

## 1️⃣ Bootstrap (30 seconds)
```bash
cd gdpr-app
./bootstrap.sh    # Automated setup
```

**What it does:**
- ✓ Validates Node.js v18+
- ✓ Copies `.env` from template
- ✓ Installs all dependencies (~4 min)
- ✓ Shows next steps

## 2️⃣ Start Application (10 seconds)
```bash
npm run dev
```

**Automatic startup:**
- Backend: `http://localhost:3001` (Express, JWT auth)
- Frontend: `http://localhost:3000` (Next.js)

## 3️⃣ Login (30 seconds)
Open **`http://localhost:3000`** and use:
- **Email**: `user@example.com`
- **Password**: `user123`

## 4️⃣ Test Features (3 minutes)

### Dashboard
- View 3 mock GDPR requests
- Filter by status (pending, processing, completed)
- Click any request to view details

### Create New Request
- Click "New Request" button
- Fill multi-section form
- Submit

### Download Data
- Click on completed request (REQ-2026-003)
- Click "Download Data"
- Receive ZIP with GDPR-compliant data package

## ⚡ Available Commands

| Command | Purpose |
|---------|---------|
| `npm run dev` | Full-stack dev (both servers) |
| `npm run dev:backend` | Backend only (port 3001) |
| `npm run dev:frontend` | Frontend only (port 3000) |
| `npm run build` | Production build |
| `npm run type-check` | TypeScript validation |

## 🔧 Troubleshooting

**Port already in use?**
```bash
PORT=3002 npm run dev:backend    # Different port
```

**API not connecting?**
```bash
curl http://localhost:3001/api/health    # Check backend
```

**Dependencies error?**
```bash
rm -rf node_modules package-lock.json
npm install
```

## 📖 Full Documentation

- **Setup Guide**: See `SETUP.md` for detailed instructions
- **API Docs**: See `README.md` for complete API reference
- **Feature Details**: See `README.md` for architecture & tech stack

---

**Status**: ✅ Ready to run  
**Time to first login**: ~5 minutes (including npm install)
