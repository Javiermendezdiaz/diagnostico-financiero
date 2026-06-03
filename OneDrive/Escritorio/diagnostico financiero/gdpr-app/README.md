# GDPR Data Request Application

Aplicación full-stack para gestionar solicitudes de acceso a datos personales bajo GDPR (Artículo 15). Los usuarios se registran, crean solicitudes especificando categorías de datos, y descargan sus datos comprimidos cuando estén listos.

## Características

**Autenticación JWT**: Registro y login con tokens de 7 días. Contraseñas hasheadas PBKDF2 (100k iteraciones).

**Gestión de solicitudes GDPR**: 8 categorías de datos predefinidas, período de validez de 30 días, descarga como ZIP comprimido.

**Protección de rutas**: Middleware Next.js + checks client-side. Redirección automática a login si token expira.

**API client transparente**: Inyección automática de headers Authorization, manejo de 401, generación de tipos TypeScript.

**Base de datos**: PostgreSQL con esquema normalizado, índices en búsquedas frecuentes, auditoría de solicitudes.

**Rate limiting**: 100 requests / 15 minutos por IP.

## Stack Tecnológico

**Backend:**
- Express.js 4.18 + TypeScript
- PostgreSQL 14+
- JWT (jsonwebtoken)
- PBKDF2 (crypto nativo de Node)
- Multer (file uploads)
- Cors, helmet, express-rate-limit

**Frontend:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS 3
- React hooks (useState, useEffect, useRouter)
- Cliente API custom con localStorage

## Instalación

### Backend

```bash
cd gdpr-app/backend
npm install

# Crear archivo .env
cat > .env << EOC
DATABASE_URL=postgresql://user:password@localhost:5432/gdpr_db
JWT_SECRET=tu-clave-secreta-aqui
PORT=3001
NODE_ENV=development
EOC

# Crear base de datos
npm run migrate:up

# Iniciar servidor
npm run dev  # desarrollo con nodemon
npm start    # producción
```

### Frontend

```bash
cd gdpr-app/frontend
npm install

# Crear archivo .env.local
cat > .env.local << EOC
NEXT_PUBLIC_API_URL=http://localhost:3001
EOC

# Iniciar cliente de desarrollo
npm run dev  # http://localhost:3000
```

## Estructura del Proyecto

```
gdpr-app/
├── backend/
│   ├── src/
│   │   ├── index.ts              # Servidor Express
│   │   ├── db.ts                 # Conexión PostgreSQL
│   │   ├── middleware/
│   │   │   ├── auth.ts           # Verificación JWT
│   │   │   ├── errorHandler.ts   # Manejo global de errores
│   │   │   └── rateLimiter.ts    # Rate limiting
│   │   ├── routes/
│   │   │   ├── auth.ts           # POST /register, /login
│   │   │   └── requests.ts       # CRUD /requests
│   │   ├── utils/
│   │   │   ├── crypto.ts         # Hash PBKDF2
│   │   │   ├── jwt.ts            # Sign/verify JWT
│   │   │   └── zip.ts            # Generación de ZIP
│   │   └── migrations/
│   │       └── init.sql          # Schema inicial
│   ├── tsconfig.json
│   ├── .env.example
│   └── package.json
├── frontend/
│   ├── app/
│   │   ├── layout.tsx            # Root layout
│   │   ├── page.tsx              # Landing / home
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── register/
│   │   │   └── page.tsx
│   │   ├── requests/
│   │   │   ├── page.tsx          # Lista de solicitudes
│   │   │   ├── new/
│   │   │   │   └── page.tsx      # Crear solicitud
│   │   │   └── [id]/
│   │   │       └── page.tsx      # Detalle + descargar
│   │   ├── globals.css
│   │   └── middleware.ts         # Route protection
│   ├── components/
│   │   └── RequestForm.tsx       # Form reutilizable
│   ├── lib/
│   │   └── api.ts                # Cliente API
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── .env.example
│   └── package.json
└── README.md
```

## Flujo de Autenticación

1. **Registro** → POST `/api/auth/register` con email/password/nombre
2. **Hash** → PBKDF2 con salt aleatorio (100k iteraciones)
3. **Login** → POST `/api/auth/login`, retorna JWT válido 7 días
4. **Token storage** → localStorage `gdpr_auth_token` y user data
5. **Headers automáticos** → Cliente inyecta `Authorization: Bearer {token}`
6. **Expiración** → 401 redirige a login automáticamente
7. **Logout** → Limpia localStorage

## Endpoints API

### Autenticación

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "micontraseña123",
  "fullName": "Juan Pérez"
}

→ 201 { token, user: { id, email, fullName } }
```

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "micontraseña123"
}

→ 200 { token, user: { id, email, fullName } }
```

### Solicitudes GDPR

```http
POST /api/requests
Authorization: Bearer {token}
Content-Type: application/json

{
  "dataCategories": ["Información Personal", "Información Financiera"],
  "notes": "Necesito acceso a todas mis transacciones"
}

→ 201 { id, userId, status: "pending", dataCategories, requestedAt, expiresAt }
```

```http
GET /api/requests
Authorization: Bearer {token}

→ 200 [{ id, status, dataCategories, requestedAt, expiresAt }, ...]
```

```http
GET /api/requests/:id
Authorization: Bearer {token}

→ 200 { id, userId, status, dataCategories, requestedAt, expiresAt, completedAt, notes }
```

```http
GET /api/requests/:id/download
Authorization: Bearer {token}

→ 200 application/zip (GDPR_Data_{id}.zip)
```

```http
PATCH /api/requests/:id/status
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "processing",
  "notes": "Recopilando datos"
}

→ 200 { id, status: "processing", updatedAt }
```

## Categorías de Datos GDPR

1. **Información Personal** — Nombre, DOB, género, nacionalidad
2. **Información de Contacto** — Email, teléfono, dirección
3. **Información Financiera** — Ingresos, impuestos, cuentas bancarias
4. **Historial de Transacciones** — Compras, pagos, transferencias
5. **Registros de Comunicación** — Emails, mensajes, tickets de soporte
6. **Datos de Ubicación** — GPS, IP, direcciones visitadas
7. **Información del Dispositivo** — User agent, OS, navegador
8. **Historial de Navegación** — Páginas visitadas, búsquedas

Cada solicitud puede incluir 1 o múltiples categorías.

## Ciclo de Vida de una Solicitud

```
pending (recibida)
    ↓
processing (recopilando)
    ↓
ready (disponible para descargar, 7 días)
    ↓
completed (descargada o expirada)

O en caso de error:
    ↓
rejected (no procesable)
```

**Validez**: 30 días desde creación. Descarga disponible 7 días desde cambio a "ready".

## Variables de Entorno

### Backend `.env`

```
DATABASE_URL=postgresql://user:password@localhost:5432/gdpr_db
DATABASE_POOL_SIZE=20
JWT_SECRET=clave-muy-larga-y-aleatoria-aca
JWT_EXPIRY=7d
PORT=3001
NODE_ENV=development
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASS=tu-app-password
SMTP_FROM=noreply@gdpr-app.com
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
```

### Frontend `.env.local`

```
NEXT_PUBLIC_API_URL=http://localhost:3001
```

## Características de Seguridad

✅ **HTTPS/TLS** — Comunicación encriptada
✅ **JWT con secreto fuerte** — 7 días de validez
✅ **PBKDF2** — 100k iteraciones
✅ **CORS** — Origen específico en producción
✅ **Rate limiting** — 100 req/15 min por IP
✅ **HELMET** — Headers de seguridad HTTP
✅ **Input validation** — Email, contraseña mínimo 8 caracteres
✅ **SQL injection prevention** — Prepared statements
✅ **Auditoría GDPR** — Todos los cambios logged

## Scripts disponibles

**Backend:**
```bash
npm run dev          # nodemon + TypeScript watch
npm start            # producción
npm run migrate:up   # ejecutar migraciones
npm run migrate:down # rollback
npm run build        # compilar TypeScript
npm run lint         # ESLint
```

**Frontend:**
```bash
npm run dev          # Next.js dev server
npm run build        # next build
npm start            # next start
npm run lint         # ESLint
npm run type-check   # TypeScript check
```

## Deployment

**Requisitos:**
- Node.js 18+
- PostgreSQL 14+
- HTTPS certificate (Let's Encrypt)
- Nginx como reverse proxy

**Checklist:**
- NODE_ENV=production
- JWT_SECRET único y fuerte
- Base de datos con backups diarios
- HTTPS en ambos backend y frontend
- CORS configurado
- Rate limiting ajustado
- Monitoreo y logs centralizados
- Email notifications
- Tests E2E automatizados

## Próximos pasos

1. Email notifications — Notificar cambios de estado
2. Admin dashboard — Interfaz para procesar solicitudes
3. Export formats — CSV, PDF, JSON
4. 2FA — Autenticación de dos factores
5. Audit trail UI — Historial de acceso
6. CI/CD — GitHub Actions

---
Privada. Adapta Family Office.
