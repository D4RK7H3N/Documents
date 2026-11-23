# School Management System (SMS)

A school management platform for a private Filipino college, covering the full student
lifecycle — enrollment, records, promotion, dropout, and graduation — together with the
finance and operations functions that run alongside it: tuition, cashiering, dormitory,
tours, and assessments.

Delivered as a Windows desktop application (Electron) and a web application (React),
both talking to the same Django REST API.

---

## Table of Contents

- [At a Glance](#at-a-glance)
- [Features](#features)
- [Screens](#screens)
- [Architecture](#architecture)
- [Data Model](#data-model)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Development](#development)
- [Known Limitations](#known-limitations)

---

## At a Glance

| | |
|---|---|
| **Frontend** | React 18, Vite, React Router (hash routing), axios, Tailwind-style utility CSS |
| **Desktop shell** | Electron 42 (Windows, x64 + ia32) |
| **Backend** | Django 5.2, Django REST Framework, PostgreSQL |
| **Auth** | DRF token authentication with per-user throttling |
| **Deployment** | Cloudflare Worker (frontend) + Cloudflare Tunnel → Django (backend) |
| **Version** | 1.1.0 |

The desktop and web builds share one codebase and behave identically — there are no
build-time feature flags, so a change in one is a change in both.

---

## Features

### Student Records

- **Enrollment** — LRN-based student creation, track/strand and section assignment,
  level and grade-level selection (SHS Grade 11–12, Bundled 1st/2nd Year)
- **Bulk import** — Excel upload of student rosters with per-row validation and
  error reporting
- **Student documents** — attachments and printable student records
- **Promotion** — advance students between year levels; graduation eligibility is
  derived from actual `StudentGraduation` records rather than a status field
- **Dropout** — record a departure with date, reason, notes, and the grade level and
  section the student was in at the time
- **Sections** — CRUD plus a transactional **Bulk Assign Section** tool with
  cohort filters, cascading Track → Strand dropdowns, and a per-student preview
  before applying

### Finance

- **Tuition** — per-student balance, payment recording, and a printable
  **Statement of Account** with full payment history and a running remaining balance
- **Overpayment handling** — payments exceeding tuition are reported as a held credit
  rather than silently clamped to a zero balance
- **Cashier / POS** — collect payments across tuition, assessments, dormitory, tours,
  graduation, and general items, with printable receipts on 80mm roll
- **Pending payments** — combined view of owed tuition and outstanding item charges
- **Revenue** — consolidated reporting across all payment types, with printable
  reports on letterhead

### Academics

- **Assessments** — per-student assessment tracking with payments and balances
- **Tours** — educational tours with enrolments, fees, and payments
- **Tracks and strands** — academic track/strand catalogue used by enrollment,
  sectioning, and bulk assignment

### Facilities

- **Dormitory** — buildings, rooms, and student assignments

### Administration

- **Users and roles** — staff accounts with superuser/staff distinction
- **School configuration** — identity, contact details, logo, receipt wording,
  academic year, and print layout settings
- **Settings** — application preferences

---

## Screens

| Route | Purpose |
|---|---|
| `/` | Dashboard — revenue, pending payments, student statistics |
| `/students` | Student roster, enrollment, Excel import |
| `/enroll` | Enrollment flow |
| `/sections` | Sections and bulk assignment |
| `/tracks` | Academic tracks and strands |
| `/courses` | Courses |
| `/tuition` | Tuition records, SOA, payments |
| `/cashier` | Point of sale and collections |
| `/pending-payments` | Outstanding balances |
| `/revenue` | Revenue reports |
| `/sales` | Sales records |
| `/promotion` | Year-level promotion |
| `/dropouts` | Dropout records |
| `/assessments` | Student assessments |
| `/tours` | Educational tours |
| `/dorm` | Dormitory management |
| `/school-config` | School configuration (admin) |
| `/settings` | Application settings |
| `/profile` | User profile |

> `GraduationPage.jsx` and `ProductsPage.jsx` still exist in `src/pages/` but are not
> routed — graduation became a Cashier payment type, and the products catalogue is
> currently served through Sales.

---

## Architecture

```
┌──────────────────────┐      ┌──────────────────────┐
│  Electron (Windows)  │      │  Web (browser)       │
│  React SPA           │      │  React SPA           │
└──────────┬───────────┘      └──────────┬───────────┘
           │                             │
           └────────────┬────────────────┘
                        │  HTTPS (token auth)
                        ▼
             ┌─────────────────────┐
             │  Cloudflare Worker  │  static assets
             │  (frontend hosting) │
             └─────────────────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │  Cloudflare Tunnel  │
             └──────────┬──────────┘
                        ▼
             ┌─────────────────────┐
             │  Django REST API    │
             │  (NSSM service)     │
             └──────────┬──────────┘
                        ▼
             ┌─────────────────────┐
             │  PostgreSQL         │
             └─────────────────────┘
```

**Why a Worker plus a tunnel rather than a single host:** the static frontend is served
from the edge for low latency, while the API stays on the local network behind a
tunnel, so no inbound firewall rule is required.

### Backend apps

18 Django apps: `accounts` · `api` · `assessment` · `cashier` · `dorm` · `dropouts` ·
`graduation` · `payments` · `products` · `revenue` · `sales` · `school_config` · `staff` ·
`students` · `tours` · `tracks` · `tuition`

### Frontend structure

```
src/
├── components/     shared UI (ActionButton, PageHeader, PesoSign, Receipt, ...)
├── contexts/       SchoolConfigContext
├── pages/          one file per route
├── services/       api.js (axios client + per-domain API modules)
├── utils/          cache.js (request dedupe + TTL cache)
└── layouts/        MainLayout (sidebar, auth guard)
```

`PesoSign` is a custom SVG component used in place of a currency icon, since the
Philippine peso sign is not in the icon set.

---

## Data Model

33 models across 14 apps. The core relationships:

- **Student** — the central record: LRN, personal details, level, grade level, section,
  track/strand, enrollment status, and financial fields
- **TuitionPayment** — payments against a student's tuition, each with a reference
  number and running balance
- **StudentCharge** — item charges (uniform, graduation fee, etc.) with their own
  partial-payment and settlement state
- **Payment** — cashier/POS transactions, optionally linked to a student or sale
- **Dropout** — one-to-one with Student; captures date, reason, notes, and the last
  grade level and section
- **StudentGraduation** — graduation eligibility, used by promotion logic
- **Section** — academic section, scoped to a level type and grade year
- **SchoolConfiguration** — singleton holding school identity and print settings

---

## Configuration

### School Config → Student List Print

The signature block printed at the bottom of student and section lists is fully
configurable and has no hardcoded defaults:

| Setting | Behaviour |
|---|---|
| **Signatories** | Up to 8 rows, each with a role label, an optional printed name, and a section assignment |
| **Section assignment** | A signatory scoped to a section appears only on that section's list. Left on *All sections*, they appear on every list. Matching is case- and whitespace-insensitive. |
| **Signature caption** | Text shown under each line when no name is filled in |
| **Show signature block** | Toggle the block off entirely |
| **Show generated timestamp** | Toggle the "Document generated on ..." line |

A blank name prints an empty signature line for a handwritten signature. With nothing
configured, no signature block is printed.

### Print behaviour

Paper size and orientation are pinned per document type so the print dialog opens with
the right defaults:

| Document | Layout |
|---|---|
| Statement of Account | A4 portrait |
| Official / cashier receipt | 80mm roll, portrait |
| Section List report | A4 landscape, table header repeats per page |
| Revenue report | A4 landscape |

> **Note:** Electron does not implement Chromium's print preview, so the preview pane in
> the desktop print dialog is blank by design. Printing itself works normally.

---

## Deployment

**Frontend** — built to `dist/`, deployed to a Cloudflare Worker with the HTML entry
document set to `no-store` and content-hashed assets set to `immutable` for one year.
Both the browser and Cloudflare's edge cache are controlled explicitly via
`Cache-Control` and `Cloudflare-CDN-Cache-Control`. A missing file under `/assets/`
returns a real `404` rather than being masked as `text/html` by the SPA fallback.

**Backend** — Django served by a Windows NSSM service on `127.0.0.1:8000`, exposed
through a Cloudflare Tunnel.

**Desktop** — `npm run build:win` produces a dual-architecture NSIS installer plus
portable builds in `release/win-unpacked` and `release/win-ia32-unpacked`.

---

## Development

```bash
# Backend
school_pos/.venv/Scripts/python.exe manage.py runserver 0.0.0.0:8000

# Frontend (dev server)
npm run dev

# Desktop
npm start          # vite + electron together
npm run electron   # electron against an already-running dev server

# Build
npm run build      # frontend bundle
npm run build:win  # Windows installer
npm run pack       # portable, no installer
npm run deploy     # build + wrangler deploy
```

---

## Known Limitations

Honest list of what is not finished:

- **`student.tuition_balance` is not synchronised on payment write.** The Statement of
  Account computes the balance correctly from `custom_tuition_fee` and actual payments,
  but the denormalised field on the student record goes stale when a tuition payment is
  recorded or removed. Promotion recomputes it; the payment path does not.
- **The tuition SOA counts only `TuitionPayment` records.** A payment taken at the
  cashier is not reflected in a student's tuition statement.
- **A Django template server runs alongside the API.** Several views in `students/`,
  `tours/`, and `assessment/` render templates whose directories are empty in this
  repository and would raise `TemplateDoesNotExist`. The live UI is the React app; these
  routes are legacy.
- **No fee schedule.** Tuition is set per student — explicitly at enrollment or via the
  `Tuition` column on bulk upload. Nothing is inferred from level type.
- **Capacitor is present** for Android packaging but no Android build is configured in
  this repository.
- **Unsigned code signing.** Installers are built with `signtool` but not certified, so
  Windows SmartScreen will warn on first run.
