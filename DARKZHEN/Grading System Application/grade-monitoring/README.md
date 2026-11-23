# Grade Monitoring System

Student Grade Monitoring Application for Sagay National High School – Grade 12 STEM (Lovelace).

Three-tier architecture per `docs/architecture.md` (extracted from `Grade_Monitoring_System_Architecture.docx`):

- **backend/** – Django REST Framework API; the only component that touches the database and computes grades
- **web/** – React + Vite + Tailwind portal for teachers and administrators
- **mobile/** – Flutter student app (read-only grade viewing)
- **deploy/** – Docker Compose (Nginx + Django API + PostgreSQL), backup script, env template
- **docs/** – architecture reference

## Backend (local dev)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`seed_demo` prints one-time temporary passwords for teachers/students; the admin account is `admin` / `adminpass123` (dev only).

Run the test suite (engine + API + security cases):

```powershell
python manage.py test tests
```

## Web portal

```powershell
cd web
npm install
npm run dev
```

Open http://localhost:5173 (the dev server proxies `/api` to the Django server on port 8000). Production build: `npm run build`.

## Mobile app

See `mobile/README.md` (needs the Flutter SDK, then `flutter create . --org ph.sagaynhs --project-name grade_monitoring_mobile`).

## Deployment

```powershell
cd deploy
copy .env.example .env
# fill in SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build
```

Nginx (port 80) serves the portal and proxies `/api` to the API container; PostgreSQL data persists in a named volume. Schedule `backup.sh` with cron for daily `pg_dump` backups with 14-day retention.

## school_pos integration

The Management System (`school_pos`) pushes learners to this system. On the school_pos machine:

```powershell
cd C:\Users\DarkZhen\Documents\System Project\school_pos
.\.venv\Scripts\python.exe .\manage.py push_to_grade_monitor --url http://127.0.0.1:8020 --key <INTEGRATION_KEY>
```

- Only SHS learners are pushed; grade levels ("11"/"12" variants) are normalized and bundled into sections.
- Matches by LRN: existing learners get name/section updates, new learners get accounts with one-time temporary passwords.
- Every change is audit-logged. For automatic daily sync, register a Windows scheduled task that runs the command above (wrap it in a `.cmd` with `cd /d` into the school_pos folder first).
- The key must match `INTEGRATION_KEY` in `backend/.env`.

## Grading engine

`backend/grading/engine.py` contains pure functions (no database access) implementing
DepEd Order No. 8, s. 2015 computation: Percentage Score → Weighted Score → Initial Grade →
transmutation table → Quarterly Grade → Semester Final Grade → General Average, using exact
`Decimal` arithmetic. Weights and the transmutation table are stored as data (`GradingConfig`)
and editable by an administrator; any change recomputes every grade and writes an audit entry.
The engine is covered by unit tests built from the worked examples in the architecture document.
