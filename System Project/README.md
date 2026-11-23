# ðŸ« School Management System

[![Electron](https://img.shields.io/badge/Electron-42.2.0-47848F?style=flat&logo=electron)](https://www.electronjs.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react)](https://react.dev/)
[![Django](https://img.shields.io/badge/Django-REST-092E20?style=flat&logo=django)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat&logo=nodedotjs)](https://nodejs.org/)
[![License](https://img.shields.io/badge/License-Proprietary-darkred?style=flat)](./LICENSE)

---

> A full-stack school management system delivered as a Windows desktop application via Electron. Handles student enrollment, academic tracking, financial transactions, and administrative reporting.

**Electron Compatibility:** v42.2.0 (compatible with Windows 7+)

---

## Project Overview

| Aspect | Value |
|--------|-------|
| **App Name** | School Management System |
| **App ID** | `com.sms.schoolmanagementsystem` |
| **Default School Name** | My School |
| **Default Short Name** | SMS |
| **Default Tagline** | School Management System |
| **Electron Version** | 42.2.0 |
| **Theme** | Light only (no dark mode) |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django REST Framework |
| **Database** | PostgreSQL |
| | User: `postgres` / Password: `darkzhen` / DB: `SMSS` |
| **Frontend** | React 18 + Vite + Tailwind CSS |
| **Desktop Shell** | Electron v42.2.0 |
| **Icons** | Lucide React |
| **Authentication** | Token-based (DRF `authtoken`) |
| **Admin Theme** | Django Jazzmin |

---

## Repository Structure

```
System Project/
â”œâ”€â”€ README.md                  <- this file
â”œâ”€â”€ frontend/                  <- React + Vite + Electron app
â”‚   â”œâ”€â”€ electron/
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ components/
â”‚   â”‚   â”œâ”€â”€ contexts/         <- AuthContext, SchoolConfigContext
â”‚   â”‚   â”œâ”€â”€ layouts/
â”‚   â”‚   â”œâ”€â”€ pages/            <- 18 page components
â”‚   â”‚   â”œâ”€â”€ services/         <- api.js (Django REST client)
â”‚   â”‚   â”œâ”€â”€ App.jsx
â”‚   â”‚   â””â”€â”€ index.jsx
â”‚   â”œâ”€â”€ dist/                 <- Built output (gitignored)
â”‚   â”œâ”€â”€ package.json
â”‚   â””â”€â”€ README.md
â””â”€â”€ school_pos/               <- Django backend
    â”œâ”€â”€ manage.py
    â”œâ”€â”€ school_pos/           <- Project settings (incl. JAZZMIN_SETTINGS)
    â”œâ”€â”€ school_config/        <- Singleton school configuration app
    â”‚   â”œâ”€â”€ models.py         <- SchoolConfiguration
    â”‚   â”œâ”€â”€ views.py          <- SchoolConfigView (GET/PUT/PATCH)
    â”‚   â”œâ”€â”€ serializers.py
    â”‚   â”œâ”€â”€ urls.py           <- /api/school-config/current/
    â”‚   â”œâ”€â”€ admin.py          <- SchoolConfigurationAdmin
    â”‚   â”œâ”€â”€ context_processors.py  <- exposes school_name to templates
    â”‚   â”œâ”€â”€ templates/admin/  <- Custom admin branding
    â”‚   â””â”€â”€ management/commands/reset_school_config.py
    â”œâ”€â”€ students/             <- Student management
    â”œâ”€â”€ finance/              <- Payments, tuition, revenue
    â”œâ”€â”€ academic/             <- Sections, tracks, courses
    â”œâ”€â”€ facilities/           <- Dormitory
    â”œâ”€â”€ staff/                <- Staff portal
    â””â”€â”€ .venv/                <- Python virtual environment
```

---

## Backend Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 13+
- Node.js 18+ (for frontend)

### Database
Create the PostgreSQL database:
```sql
CREATE DATABASE "SMSS" WITH OWNER postgres ENCODING 'UTF8';
```

### Install & Run
```bash
cd "C:\Users\DarkZhen\Documents\System Project\school_pos"
.venv\Scripts\activate

pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the dev server
python manage.py runserver 0.0.0.0:8000
```

### School Configuration Commands
```bash
# Reset school config to generic defaults (My School / SMS)
python manage.py reset_school_config

# Create a new migration after model changes
python manage.py makemigrations school_config
python manage.py migrate school_config
```

---

## Frontend Setup

### Install
```bash
cd "C:\Users\DarkZhen\Documents\System Project\frontend"
npm install
```

### Development
```bash
npm run dev
# Opens at http://localhost:5173
```

### Production Build (Web only)
```bash
npm run build
# Output: frontend/dist/
```

### Electron Build (Windows)
```bash
npm run build:win
# Output: frontend/dist/
#   - School Management System Setup 1.0.0.exe  (NSIS installer)
#   - win-unpacked/                                  (x64)
#   - win-ia32-unpacked/                             (ia32)
```

> Note: All branding has been updated to generic `School Management System`. The `package.json` name is `school-management-system`, `electron-builder.yml` uses `com.sms.schoolmanagementsystem`, and all USAT/Sagay City College references have been removed.

---

## Backend API

- **Base URL:** `http://localhost:8000/api/`
- **Auth:** Token-based (`Authorization: Token <token>`)
- **Token storage:** `localStorage.authToken` (axios interceptor)

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/auth/login/` | Login, returns token |
| `/api/students/` | Student CRUD |
| `/api/sections/`, `/api/tracks/`, `/api/courses/` | Academic structure |
| `/api/tuition-payments/` | Tuition records |
| `/api/payments/` | Walk-in & general payments |
| `/api/revenue/` | Revenue reports |
| `/api/school-config/current/` | School configuration (singleton) |

---

## Core Features

### 1. Student Management
- Student enrollment with LRN tracking (12-digit validation)
- Student profiles with personal & guardian information
- Sections, Tracks (strands), and Courses management
- Student assessments and grading
- Dropout tracking with reinstatement flow
- Graduation event management
- Dormitory room assignments
- School tour scheduling and enrollments

### 2. Finance & Cashier
The Cashier is the main financial transaction hub:

- **Walk-in Customer Support** - Parents, guardians, or authorized payers can make payments without being a student
- **Multiple Payment Types:** Tuition, Miscellaneous, Laboratory, Assessment, Other
- **Payment Methods:** Cash, GCash, Bank Transfer, Card, Check
- **Receipt Generation** showing school name/address, payer, itemized description, payment method, reference number, timestamp
- **Searchable Transaction History** - Search by payer name, reference number
- **Pending Payments Tracking** - Monitor outstanding balances
- **Quick Payment Form** with Student/Walk-in toggle
- **Cash change calculation** for cash payments

### 3. Revenue Reports
- Financial summary: Total Income, General Payments, Total Expenses, Collection Rate
- Revenue breakdown by category (Tuition, Miscellaneous, Laboratory, Assessment, Dorm, Tour, Graduation, POS, Other)
- Top paying students listing with medal indicators
- Print-friendly A4 landscape reports
- Date-range, type, and method filters
- CSV export functionality

### 4. Sales
- Product sales tracking
- Revenue from non-tuition sources

---

## School Configuration (Singleton)

The system uses a **singleton** configuration model (`SchoolConfiguration`, `pk=1`) to manage school-wide branding exposed globally to both Django templates and the React frontend.

### Django Templates
A `school_config` context processor exposes `school_name`, `school_logo_url`, and `school_short_name` to all templates. Custom `templates/admin/base_site.html` and `templates/admin/login.html` override the Jazzmin default branding.

### React Frontend
A `SchoolConfigContext` (`src/contexts/SchoolConfigContext.jsx`) provides:
- `schoolName` (default: "My School")
- `schoolShortName` (default: "SMS")
- `schoolLogo`
- `schoolTagline`

These are used in the sidebar, page titles, receipts, and the `TitleUpdater` component that sets `document.title` per route.

### Update via API
```
PATCH /api/school-config/current/
Content-Type: application/json  (or multipart/form-data for logo upload)
```

To change the school name, logo, contact info, etc. at runtime, use the **School Config** page in the application or call the API directly.

---

## Navigation Structure

| Section | Pages |
|---------|-------|
| **STUDENT** | Students, Sections, Tracks, Courses, Enroll, Dropouts |
| **FINANCE** | Cashier, Tuition, Revenue, Pending Payments, Sales |
| **ACADEMICS** | Assessments, Graduation, Tours |
| **FACILITIES** | Dorm |
| **SYSTEM** | Settings, School Config, Profile |

---

## UI/UX Decisions

### Light-Only Theme
- All `dark:` Tailwind variants removed
- `darkMode` removed from `tailwind.config.js`
- `ThemeContext` returns a stub `{ isDark: false, toggleTheme: () => {} }`
- `<html>` is force-stripped of the `dark` class on load
- No theme toggle in the Settings page
- Light palette: `bg-white` (cards), `bg-gray-50` (page), `border-gray-200`, `text-gray-900` primary, `text-gray-500` muted

### Layout
- Stat cards: horizontal flex row, icon top-left, bold value, muted label below
- Tables: rounded `rounded-2xl` containers, compact padding, hover states, empty states with icons
- Modals: backdrop blur, sticky headers, X close buttons
- Toast notifications: slide-up animation, success (gray-800) / error (red-600), 3.5s auto-dismiss

### Print Formats
- **80mm thermal receipt** for cashier transactions
- **A4 official receipt** for accounting
- **A4 enrollment form** (long bond paper) for student registration

---

## Pages (18 total)

| Route | Page |
|-------|------|
| `/login` | LoginPage |
| `/` | DashboardPage |
| `/students` | StudentsPage |
| `/sections` | SectionsPage |
| `/tracks` | TracksPage |
| `/courses` | CoursesPage |
| `/enroll` | EnrollPage |
| `/dropouts` | DropoutsPage |
| `/cashier` | CashierPage |
| `/tuition` | TuitionPage |
| `/revenue` | RevenuePage |
| `/pending-payments` | PendingPaymentsPage |
| `/sales` | SalesPage |
| `/assessments` | AssessmentsPage |
| `/graduation` | GraduationPage |
| `/tours` | ToursPage |
| `/dorm` | DormPage |
| `/settings` | SettingsPage |
| `/school-config` | SchoolConfigPage |
| `/profile` | ProfilePage |

---

## Known Notes

> [!NOTE]
> **ThemeContext** is a stub kept for API compatibility â€” all pages render in light mode.

> [!NOTE]
> **SchoolConfiguration** is a singleton (`pk=1`). Use `python manage.py reset_school_config` to revert to defaults.

> [!NOTE]
> **NSIS installer** requires admin rights to install (Windows per-machine symlinks).

> [!IMPORTANT]
> **Payment method values** are case-sensitive: `Cash`, `GCash`,

> [!NOTE]
> All branding has been updated to generic `School Management System`. The `package.json` name is `school-management-system`, `electron-builder.yml` uses `com.sms.schoolmanagementsystem`, and all USAT/Sagay City College references have been removed.

---

## Development Status

| Feature | Status |
|---------|--------|
| Light-only theme across all 18 pages | âœ… Done |
| School configuration singleton (frontend + backend) | âœ… Done |
| School branding in admin (Django + Jazzmin) and cashier receipts | âœ… Done |
| Walk-in customer support in Cashier | âœ… Done |
| Receipt shows school name and item correctly | âœ… Done |
| Revenue reports with horizontal stat layout | âœ… Done |
| Electron production build (x64 + ia32) with `app.getAppPath()` fix | âœ… Done |
| Migrations applied and school config reset to generic defaults | âœ… Done |
| NSIS installer built successfully | âœ… Done |

---

## License

**Proprietary - © 2026 USAT College Sagay City, Inc. All rights reserved.**

This software belongs to the School and is licensed for its own internal use.
It may not be copied, published, mirrored, uploaded or redistributed - in
source or compiled form - without the School's written permission. See
[LICENSE](./LICENSE) for the full terms.

---

*Made with â¤ï¸ for schools everywhere*
