# Gravity — Implementation Status

Last updated: 2026-10-03

## Current phase
Phase 02 — Frontend Foundation

## Completed
- Phase 00 - Repository & Specification Lock
- Phase 01 - Backend Foundation
  - Created Python virtual environment.
  - Installed Django 5.2.17, DRF, Channels, psycopg, and Redis dependencies.
  - Initialized Django project `config` and `accounts` app.
  - Set up PostGIS database `gravity`.
  - Created custom `User` model with `PrivacyMode`.
  - Ran initial migrations.
  - Created `admin` superuser.
  - Verified PostGIS and Redis connectivity.
  - Added and passed basic foundation tests.

## In progress
- None

## Known issues
- None

## Deferred
- See `GRAVITY_BUILD_PHASES.md`.

## Setup / migration commands
```bash
# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt # (To be added later)
python manage.py migrate

# Create DB (if starting fresh)
sudo -u postgres psql -c "CREATE DATABASE gravity;"
sudo -u postgres psql -c "CREATE USER gravity_user WITH PASSWORD 'gravity_pass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE gravity TO gravity_user;"
sudo -u postgres psql -d gravity -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -d gravity -c "ALTER SCHEMA public OWNER TO gravity_user;"
```

## Next recommended task
Begin Phase 02: Create mobile-first React application using Vite.
