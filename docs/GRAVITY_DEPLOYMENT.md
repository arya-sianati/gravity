# Gravity — Production Deployment & Operations Guide

Canonical Production URL: `https://gravity.college`  
Alternative Hostname: `https://www.gravity.college` (301 Permanent Redirect to canonical apex)

---

## Live Production Architecture & Service Layout

| Component | Technology | Binding / Path | Service / Unit |
| :--- | :--- | :--- | :--- |
| **Reverse Proxy / TLS** | Nginx 1.22 | `0.0.0.0:80`, `0.0.0.0:443` | `nginx.service` |
| **ASGI Application** | Daphne + Django 5.2 | `127.0.0.1:8000` | `gravity.service` |
| **Frontend PWA** | React 19 + Vite | `/home/mule/gravity/frontend/dist` | Served by Nginx |
| **Static Assets** | Django Staticfiles | `/home/mule/gravity/backend/staticfiles` | Served by Nginx (`/static/`) |
| **Database** | PostgreSQL 15 + PostGIS 3.3 | `127.0.0.1:5432/gravity` | `postgresql.service` |
| **Channel Layer** | Redis 7 | `127.0.0.1:6379/0` | `redis-server.service` |
| **TLS Certificates** | Let's Encrypt / Certbot | `/etc/letsencrypt/live/gravity.college/` | `certbot.timer` |

### Key Paths & Configuration Files
- Nginx Site Config: `/etc/nginx/sites-available/gravity.college` (source copy in `deploy/nginx-gravity.conf`)
- Daphne Systemd Unit: `/etc/systemd/system/gravity.service` (source copy in `deploy/gravity.service`)
- Backend Environment File: `/home/mule/gravity/backend/.env` (mode `0600`, outside Git)
- Automated Redeployment Script: `/home/mule/gravity/scripts/deploy.sh`

### Service Management Commands
```bash
# Check service statuses
systemctl status nginx gravity postgresql redis-server --no-pager

# Restart application service
sudo systemctl restart gravity.service

# Reload web server
sudo systemctl reload nginx

# Quick redeployment
/home/mule/gravity/scripts/deploy.sh
```

---

# 1. Production Components

Install/run on server:

- Nginx
- PostgreSQL
- PostGIS
- Redis
- Python virtual environment
- Django backend
- ASGI server
- frontend production build

No Firebase/Supabase/hosted auth is required.

---

# 2. Suggested Domain Layout

Preferred same-origin deployment:

```text
https://gravity.example.com/
https://gravity.example.com/api/
https://gravity.example.com/admin/
wss://gravity.example.com/ws/
```

Benefits:

- simple cookies,
- simple CSRF,
- fewer CORS problems,
- QR links easy to share.

---

# 3. DNS

Create DNS record:

```text
gravity.example.com -> server public IP
```

Wait for propagation before TLS issuance.

---

# 4. Database

Create PostgreSQL database and user.

Enable PostGIS extension.

Conceptually:

```sql
CREATE DATABASE gravity;
CREATE USER gravity_user WITH PASSWORD '...';
\c gravity
CREATE EXTENSION postgis;
```

Use least privilege appropriate for Django migrations.

---

# 5. Redis

Run Redis locally.

Bind safely.

Do not expose Redis publicly to the internet.

---

# 6. Backend Environment

Example production env:

```text
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=gravity.example.com
CSRF_TRUSTED_ORIGINS=https://gravity.example.com
DATABASE_URL=...
REDIS_URL=redis://127.0.0.1:6379/0
PUBLIC_BASE_URL=https://gravity.example.com
```

---

# 7. Static Files

Run Django static collection for Admin assets.

Frontend:

```text
npm run build
```

Serve Vite build through Nginx.

Django `/static/` can be served by Nginx.

---

# 8. ASGI

Use a production-capable ASGI server compatible with Django Channels.

Exact server should be chosen based on verified current recommendations.

Run it as a systemd service.

Example conceptual service:

```text
WorkingDirectory=/srv/gravity/backend
EnvironmentFile=/srv/gravity/.env
ExecStart=/srv/gravity/venv/bin/<asgi-server> config.asgi:application
Restart=always
```

---

# 9. Nginx

Responsibilities:

- TLS termination
- frontend static files
- `/api/` proxy to Django
- `/admin/` proxy to Django
- `/ws/` WebSocket proxy
- Django static/media paths if needed

WebSocket proxy must forward upgrade headers.

---

# 10. HTTPS

HTTPS is required for:

- secure auth,
- geolocation behavior,
- camera/QR behavior,
- secure WebSockets,
- PWA installability.

Use Let's Encrypt/Certbot or equivalent.

---

# 11. Deployment Order

1. Clone repo.
2. Configure `.env`.
3. Create virtual environment.
4. Install backend dependencies.
5. Configure PostgreSQL/PostGIS.
6. Run migrations.
7. Create superuser.
8. Seed Gravity data.
9. Build frontend.
10. Configure ASGI service.
11. Configure Nginx.
12. Issue TLS certificate.
13. Verify `https`.
14. Verify `wss`.
15. Test QR on second device.

---

# 12. Production Verification Checklist

## Backend
- `/admin/` loads
- login works
- migrations current
- API auth works
- PostGIS query works
- Redis reachable locally

## Frontend
- no dev URLs
- map tiles load
- API requests use production origin
- mobile view correct

## Realtime
- WebSocket connection successful
- participant join propagates
- map heat updates

## Device features
- geolocation works
- QR scanning works
- shared QR URL opens

## Privacy
- hidden user does not expose exact location
- blurred mode does not expose residence coordinate

---

# 13. Backups

Hackathon minimum:

- dump PostgreSQL before major migration/refactor,
- keep Git pushed,
- keep `.env` securely outside repo.

Example conceptual DB backup:

```text
pg_dump ...
```

---

# 14. Rollback

Before risky deployment:

- tag/commit known-good version,
- backup DB,
- record migration state.

Avoid destructive schema changes late in the hackathon.

---

# 15. Demo Reliability

Before judging:

- restart services,
- verify domain,
- verify TLS,
- verify map,
- verify Redis,
- verify WebSocket,
- keep admin logged in on separate device,
- keep QR demo tested,
- have seeded data available if live participation is low.

The live product should be the primary demo; seeded data is fallback, not deception.
