# FIXIT POS — Deployment Guide

## Architecture Overview

```
User Browser
    │
    ├── https://pos.fixitsoluciones.com ──┐
    │                                     │
    ▼                                     ▼
Cloudflare (DNS + WAF + SSL) ───► Vercel (Next.js Frontend)
    │
    ├── https://api-pos.fixitsoluciones.com ──┐
    │                                          │
    ▼                                          ▼
Cloudflare (DNS + WAF + SSL) ───► Render (FastAPI Backend)
                                        │
                                        ▼
                                  PostgreSQL 16
```

---

## Domain Map

| Service      | Domain                              | Hosting      | Stack            |
|-------------|--------------------------------------|--------------|------------------|
| Frontend    | `pos.fixitsoluciones.com`           | Vercel       | Next.js 14       |
| Backend API | `api-pos.fixitsoluciones.com`       | Render       | FastAPI + Uvicorn|
| Staging     | `staging-pos.fixitsoluciones.com`   | VPS or Render| Frontend + Backend|
| Database    | Internal Render URI                 | Render       | PostgreSQL 16    |

---

## 1. Vercel — Frontend Deployment

### Prerequisites

- Vercel account connected to GitHub repository
- Cloudflare DNS configured (see `deploy/cloudflare-dns.md`)

### Steps

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Login
vercel login

# 3. Link project
cd frontend
vercel link

# 4. Set environment variables
vercel env add NEXT_PUBLIC_API_URL production
# Value: https://api-pos.fixitsoluciones.com

vercel env add NEXT_PUBLIC_API_URL staging
# Value: https://staging-pos.fixitsoluciones.com

# 5. Add custom domain
vercel domains add pos.fixitsoluciones.com
vercel domains add staging-pos.fixitsoluciones.com --json

# 6. Deploy
vercel --prod
```

### Vercel Dashboard Settings

| Setting                    | Value                          |
|----------------------------|--------------------------------|
| Framework                  | Next.js                        |
| Build Command              | `npm run build`                |
| Output Directory           | `.next`                        |
| Install Command            | `npm ci`                       |
| Node Version               | 20.x                           |
| Region                     | Washington, D.C. (iad1)       |
| Auto Expose System Env     | No                             |

---

## 2. Render — Backend Deployment

### Prerequisites

- Render account connected to GitHub repository
- Cloudflare DNS configured

### Steps

```bash
# 1. Push code to GitHub
git push origin main

# 2. In Render Dashboard:
#    - New → Blueprint
#    - Connect repository
#    - Render reads render.yaml automatically

# 3. Set sensitive env vars manually:
#    - JWT_SECRET_KEY (generate with: openssl rand -hex 64)
```

### Manual Setup (if not using render.yaml)

1. **Web Service**
   - Name: `fixit-pos-api`
   - Runtime: Python 3.12
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-config app/logging.conf`
   - Health Check Path: `/health`
   - Domain: `api-pos.fixitsoluciones.com`

2. **PostgreSQL Database**
   - Name: `fixit-pos-db`
   - Plan: Starter
   - Region: Ohio (US East)

3. **Environment Variables**
   - Copy from `deploy/environments/backend.production.env`
   - Set `JWT_SECRET_KEY` manually (never commit to repo)
   - Set `DATABASE_URL` from Render PostgreSQL connection string

---

## 3. Staging Deployment

### Option A: Render (recommended)

Create a separate Render Web Service + Database for staging:
- Web Service: `fixit-pos-api-staging`
- Database: `fixit-pos-db-staging`
- Domain: `staging-pos.fixitsoluciones.com`
- Env: Copy `deploy/environments/backend.staging.env`

### Option B: VPS (Docker)

```bash
# 1. Clone on staging server
git clone https://github.com/your-org/fixit-pos.git /opt/fixit-pos
cd /opt/fixit-pos

# 2. Configure environment
cp deploy/environments/backend.staging.env backend/.env
cp deploy/environments/frontend.staging.env frontend/.env.staging

# 3. Generate staging passwords
openssl rand -hex 64  # → JWT_SECRET_KEY
openssl rand -hex 16  # → POSTGRES_PASSWORD

# 4. Deploy with Docker
docker compose -f docker-compose.prod.yml up -d

# 5. Run migrations
docker compose exec backend alembic upgrade head

# 6. Verify
curl https://staging-pos.fixitsoluciones.com/health
```

---

## 4. Database Migrations

```bash
# Production
docker compose exec backend alembic upgrade head

# Staging
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Rollback (if needed)
docker compose exec backend alembic downgrade -1

# View history
docker compose exec backend alembic history

# Generate new migration
docker compose exec backend alembic revision --autogenerate -m "description"
```

---

## 5. SSL Certificates

### Option A: Cloudflare (recommended — already proxied)

If Cloudflare proxy is ON (orange cloud):
- Go to Cloudflare Dashboard → SSL/TLS → **Full (strict)**
- No additional certificates needed on Vercel/Render

### Option B: Self-hosted (staging only)

```bash
# Using Certbot (Let's Encrypt)
sudo certbot --nginx -d staging-pos.fixitsoluciones.com

# Using Caddy (automatic HTTPS)
# Caddy handles certificates automatically — see deploy/caddy/Caddyfile
```

---

## 6. Environment Matrix

| Variable               | Development                    | Staging                                   | Production                                |
|------------------------|-------------------------------|-------------------------------------------|-------------------------------------------|
| `APP_NAME`             | FIXIT POS API (DEV)           | FIXIT POS API (STAGING)                   | FIXIT POS API                             |
| `DEBUG`                | `true`                        | `true`                                    | `false`                                   |
| `DATABASE_URL`         | Local PostgreSQL              | Staging Render PostgreSQL                 | Production Render PostgreSQL              |
| `JWT_SECRET_KEY`       | `dev-secret-key`              | Random 64-char hex                        | Random 64-char hex                        |
| `JWT_EXPIRATION_HOURS` | 24                            | 24                                        | 8                                         |
| `BCRYPT_ROUNDS`        | 10                            | 10                                        | 12                                        |
| `MAX_LOGIN_ATTEMPTS`   | 10                            | 10                                        | 5                                         |
| `LOGIN_LOCKOUT_MINUTES`| 5                             | 5                                         | 15                                        |
| `CORS_ORIGINS`         | `http://localhost:3000`       | `https://staging-pos...`, `localhost:3000`| `https://pos.fixitsoluciones.com`         |
| `LOG_LEVEL`            | `DEBUG`                       | `DEBUG`                                   | `INFO`                                    |
| `NEXT_PUBLIC_API_URL`  | `http://localhost:8000`       | `https://staging-pos.fixitsoluciones.com` | `https://api-pos.fixitsoluciones.com`     |

---

## 7. Deployment Checklist

### Pre-deploy

- [ ] All tests pass: `cd backend && python -m pytest tests/`
- [ ] Alembic migration generates cleanly: `alembic upgrade head`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] No lint errors: `ruff check backend/app/`
- [ ] TypeScript compiles: `cd frontend && npx tsc --noEmit`
- [ ] Docker images build: `docker compose build`

### Deploy

- [ ] Frontend deployed to Vercel
- [ ] Backend deployed to Render
- [ ] Database migration run
- [ ] Health check passes: `curl https://api-pos.fixitsoluciones.com/health`
- [ ] CORS verified: browser test from frontend domain
- [ ] Cloudflare proxy ON for all domains

### Post-deploy

- [ ] Login flow works end-to-end
- [ ] POS page loads without errors
- [ ] Product search returns results
- [ ] Sale creation succeeds
- [ ] Receipt printing works (via QZ Tray)
- [ ] Cash register open/close works
- [ ] Backup runs: `docker compose exec backup /backup.sh`
- [ ] Monitoring dashboard accessible

---

## 8. Rollback Procedure

### Frontend (Vercel)

```bash
# List previous deployments
vercel list

# Rollback to specific deployment
vercel rollback <deployment-url>
```

### Backend (Render)

1. Go to Render Dashboard → fixit-pos-api → Deploys
2. Click "..." on previous successful deploy
3. Select "Rollback"

### Database

```bash
# Alembic downgrade
docker compose exec backend alembic downgrade -1

# Or restore from backup (see scripts/restore/README.md)
```

---

## 9. Monitoring

| System        | URL                                          |
|---------------|----------------------------------------------|
| Vercel Dashboard | `https://vercel.com/your-team/fixit-pos`  |
| Render Dashboard | `https://dashboard.render.com`             |
| API Health    | `https://api-pos.fixitsoluciones.com/health` |
| Cloudflare    | `https://dash.cloudflare.com`               |

### Logs

```bash
# Backend logs (Render)
# Render Dashboard → fixit-pos-api → Logs

# Backend logs (Docker)
docker compose logs -f backend

# Nginx access logs
tail -f /var/log/nginx/api-pos.fixitsoluciones.com.access.log
```

---

## 10. Security Architecture

```
Client Browser
    │
    ├── HTTPS (TLS 1.2/1.3)
    ├── Cloudflare WAF
    │   ├── Rate limiting
    │   ├── Bot mitigation
    │   └── IP filtering
    │
    ├── Vercel Edge Network
    │   ├── DDoS protection
    │   └── Global CDN
    │
    ├── Next.js Frontend
    │   ├── XSS prevention (CSP)
    │   ├── CSRF protection
    │   ├── HttpOnly cookies
    │   └── Input sanitization
    │
    ├── FastAPI Backend (api-pos.fixitsoluciones.com)
    │   ├── JWT authentication (Bearer)
    │   ├── RBAC (3 roles)
    │   ├── PIN + bcrypt hashing
    │   ├── Rate limiting
    │   ├── CORS (whitelist only)
    │   ├── Correlation IDs
    │   ├── Input validation (Pydantic)
    │   └── Structured JSON logging
    │
    └── PostgreSQL
        ├── RLS (Row-Level Security)
        ├── Parameterized queries
        ├── CHECK constraints
        └── Encrypted at rest (Render)
```
