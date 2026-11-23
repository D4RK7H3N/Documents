# School POS

## Overview

School Point-of-Sale / student management backend (Django). Covers POS sales,
tuition, assessments, dormitories, educational tours, graduation, students,
sections/tracks, staff, and revenue dashboards. Ships as a Windows LAN server
(POS terminals hit `http://SERVER_IP:8000`) plus Docker/Railway deployment, and
serves an Electron auto-updater (installer EXE) for the desktop client. A
React frontend lives in `System Project\Darkzhen-project`.

**Path:** `C:\Users\DarkZhen\Documents\System Project\school_pos` (part of the
`System Project` git repo; AGENTS.md at repo root documents the frontend
project memory)

**Tech stack:** Django 5.2.6, DRF 3.16.1, PostgreSQL, Gunicorn, Whitenoise,
Jazzmin admin, Docker, Nginx, Railway, reportlab/openpyxl/python-docx,
qrcode/pyzbar, opencv; Cloudflare Worker frontend (`sms-2-api`, D1 + R2)

## Status

**Active** - last activity 2026-08-13.

| Date | Commit |
|---|---|
| 2026-08-13 | security: fix P0/P1 issues from CODE_REVIEW.md |
| 2026-07-14 | Add edit/delete functionality to TracksPage - working edit dialog and delete confirmation |
| 2026-07-14 | Remove Status column from StudentSectionReport print report |
| 2026-07-14 | Rewrite SectionsPage: fetch students, group by section, unassigned section group, clickable cards with student view dialog, section assignment editing |

## Apps & responsibilities

| App | Purpose |
|---|---|
| `api` | Central DRF API: auth, students, dorm, products, sales, payments, tuition, assessments, tours, graduation, revenue, tracks, dropouts, health, update-file serving |
| `accounts` | Placeholder (empty models) |
| `assessment` | Extra fees - AssessmentType (NC II/Lab/Misc/Cert/Exam), StudentAssessment, AssessmentPayment, AssessmentBatch (bulk assign) |
| `cashier` | TuitionPayment + web POS: dashboard, checkout, receipts (HTML) |
| `dorm` | DormBuilding (gender-restricted), DormRoom (capacity/rates), DormAssignment, DormPayment |
| `dropouts` | Dropout records + ViewSet |
| `graduation` | GraduationEvent (package fee, slots), StudentGraduation (balance, honors), GraduationPayment, bulk enroll |
| `payments` | Generic Payment ledger (sale or student, method/status/type, walk-in) |
| `products` | Product (name, price, stock, tuition_type quarter/semester/other) |
| `revenue` | Aggregated dashboard across POS, tuition, assessment, dorm, tour, graduation, general |
| `sales` | POS transactions - Sale (student/walk-in, GCash refs) + SaleItem |
| `school_config` | Singleton branding: name, logos, address, receipts header/footer, student ID prefix, academic year (cached) |
| `staff` | StaffProfile (department, position, avatar) + web login/dashboard |
| `students` | Student records (personal/guardian/academic/health/enrollment/tuition), StudentDocument (13 types, verification workflow), Excel bulk upload, auto-promotion, sectioning, printable sections |
| `tracks` | Track/Strand/Course/Section + 4 ModelViewSets |
| `tuition` | TuitionFeeStructure, TuitionBreakdown (quarterly), TuitionPayment (GCash) |
| `tours` | EducationalTour, TourEnrollment (consent, clearance), TourPayment, bulk enroll |
| `updates` | Electron auto-update artifacts folder served by `api/updates_view.py` (exe/yml/blockmap, auth + sanitized) |

## API areas (`/api/`)

- `auth/` - login (case-insensitive, 10/hr), profile, update_profile,
  change_password (email change requires old password)
- `students/` CRUD + `upload_document`, `bulk_upload` (Excel, header aliases)
- `documents/`, `dorm/buildings|rooms|assignments|payments`,
  `products/`, `sales/`, `payments/`, `tuition-payments/`
- `assessment-types/`, `student-assessments/` (+bulk_enroll),
  `assessment-payments/`
- `tours/`, `tour-enrollments/` (+bulk_enroll), `tour-payments/`
- `graduation-events/`, `graduation-enrollments/` (+bulk_enroll),
  `graduation-payments/`
- `revenue/`, `tracks/`, `strands/`, `courses/`, `sections/`, `dropouts/`
- `health/` - unauthenticated DB check; `school-config/current/`
- `updates/<filename>` - Electron updater files (auth, path-traversal safe)

Legacy HTML areas also exist: `/students/`, `/products/`, `/sales/`,
`/revenue/`, `/payments/`, `/cashier/`, `/dorm/`, `/tours/`, `/assessment/`,
`/graduation/`, `/staff/`.

## Workflow

### Local (Windows LAN server)

1. Prereqs: PostgreSQL (password `postgres`, port 5432) + Python 3.9+ on PATH.
2. `install.bat` - installs deps, migrates, collectstatic, optional
   createsuperuser, prompts for server IP, writes `.env` (DB_NAME=SMSS),
   regenerates `start.bat`, optional Windows service, launches.
   (`setup.bat` = same without the IP prompt; auto-detects IPv4.)
3. `start.bat` -> `gunicorn school_pos.wsgi --bind 0.0.0.0:8000 --workers 3 --reload`
4. `add_startup.bat` - Startup-folder shortcut for boot auto-start.
5. Terminals connect to `http://YOUR_SERVER_IP:8000`, admin at `/admin/`.
6. `scripts/` extras: `start_all.bat` (firewall rule for TCP 8000 + 5 workers),
   `firewall_setup.bat`/`.sh`, `school-pos-gunicorn.service` (systemd),
   `setup_server.bat` (venv + deps + firewall + 5 workers).

### Deploy (Docker/Railway)

- `Dockerfile`: python:3.11-slim, collectstatic + migrate, gunicorn on :8080.
- `railway.json`: builder DOCKERFILE.
- `nginx.conf`: reverse proxy :80 -> 127.0.0.1:8000, gzip, /health/ plain text,
  static/media aliases with 30d cache.
- `settings.py`: ALLOWED_HOSTS = SERVER_IP + `sms2-api.darkzhub.asia`,
  `www.darkzhub.asia`, localhost; `DATABASE_URL` override via dj_database_url;
  CORS whitelist includes Railway/ngrok/Cloudflare Worker.
- Cloudflare Worker (`cloudflare-worker/`): "sms-2-api" frontend, D1 DB
  `sms2-db`, R2 storage, JWT 8h, OR receipt prefix, route `api.darkzhub.asia`.

### Test

- Manual web/API testing; flows: sales POS + receipt, tuition + SOA, bulk
  student Excel upload (`student_upload_template.xlsx`, sheet "Student Data
  Enrollment"), sectioning + auto-promotion, print reports (StudentSectionReport
  etc., receipt numbering `OR-YYYY-NNNNN`), revenue dashboard filters
  (search/type/method/date), health endpoint.
- Security: keep `CODE_REVIEW.md` findings fixed; review passes before deploys
  touching payments/auth. Throttling: anon 20/hr, user 1000/hr, login 10/hr.

## Notes

- `setup-arch-bb.sh` at root is unrelated (leftover bug-bounty toolchain).
- `CORS_CONFIG.md` documents the CORS whitelist rationale.
- Electron desktop client: `System Project\Darkzhen-project` (landing page,
  React frontend `school_pos_frontend`, auto-update via `/api/updates/`).
