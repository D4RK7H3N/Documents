# School Management System - Frontend

A React + Vite + Tailwind CSS frontend for the School Management System, wrapped in Electron for Windows desktop deployment.

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI Framework |
| Vite | 8.x | Build Tool |
| Tailwind CSS | 3.x | Styling (light-only) |
| React Router | 6.x | Navigation |
| Lucide React | 0.263.x | Icons |
| react-to-print | 3.x | Print handling |
| Electron | 42.x | Desktop App |
| electron-builder | 26.x | NSIS installer |

## Project Structure

```
frontend/
├── electron/
│   ├── main.js           # Electron main process
│   ├── preload.js        # Context bridge
│   └── splash.html       # Animated splash screen
├── scripts/
│   └── generate-icons.cjs # Icon generation
├── src/
│   ├── components/
│   │   ├── ActionButton.jsx
│   │   ├── AvatarUpload.jsx
│   │   ├── EnrollmentForm.jsx
│   │   ├── ErrorMessage.jsx
│   │   ├── LoadingSpinner.jsx
│   │   ├── PageHeader.jsx
│   │   ├── PesoSign.jsx
│   │   ├── Receipt.jsx
│   │   ├── StatusBadge.jsx
│   │   ├── StudentCard.jsx
│   │   ├── StudentPaymentModal.jsx
│   │   ├── StudentSectionReport.jsx
│   │   ├── ThemeToggle.jsx
│   │   └── Toast.jsx
│   ├── context/
│   │   ├── AuthContext.jsx        # Token auth state
│   │   ├── NotificationContext.jsx # Toast notifications
│   │   └── ThemeContext.jsx       # Theme stub (light-only)
│   ├── contexts/
│   │   └── SchoolConfigContext.jsx # School name + logo (global)
│   ├── layouts/
│   │   └── MainLayout.jsx         # Sidebar + header
│   ├── pages/                     # Route pages
│   │   ├── LoginPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── StudentsPage.jsx
│   │   ├── SectionsPage.jsx
│   │   ├── TracksPage.jsx
│   │   ├── CoursesPage.jsx
│   │   ├── EnrollPage.jsx
│   │   ├── DropoutsPage.jsx
│   │   ├── PromotionPage.jsx
│   │   ├── CashierPage.jsx
│   │   ├── TuitionPage.jsx
│   │   ├── RevenuePage.jsx
│   │   ├── PaymentsPage.jsx
│   │   ├── PendingPaymentsPage.jsx
│   │   ├── SalesPage.jsx
│   │   ├── ProductsPage.jsx
│   │   ├── AssessmentsPage.jsx
│   │   ├── GraduationPage.jsx
│   │   ├── ToursPage.jsx
│   │   ├── DormPage.jsx
│   │   ├── SettingsPage.jsx
│   │   ├── SchoolConfigPage.jsx
│   │   ├── OnboardingPage.jsx
│   │   └── ProfilePage.jsx
│   ├── services/
│   │   └── api.js                 # Django REST client (axios)
│   ├── utils/
│   │   ├── cache.js
│   │   └── logo.js
│   ├── App.jsx                    # Routes + TitleUpdater
│   ├── index.css                  # Global styles + print
│   └── index.jsx                  # Entry point
├── build/                         # App icons (icon.ico, icon.png)
├── dist/                          # Build output
├── release/                       # electron-builder output
├── electron-builder.yml
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
└── vite.config.js
```

## Installation

```bash
npm install
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server at `http://localhost:5173` |
| `npm run build` | Generate icons + build frontend to `dist/` |
| `npm run preview` | Preview the production build |
| `npm run electron` | Launch Electron (loads dist/) |
| `npm start` | Run Vite + Electron together |
| `npm run build:win` | Build Windows installer (x64 + ia32) |
| `npm run build:win:x64` | Build Windows installer (x64) |
| `npm run build:win:x86` | Build Windows installer (ia32) |
| `npm run dist` | Build Windows installer via electron-builder |
| `npm run pack` | Build unpacked Electron app (no installer) |
| `npm run gen-icons` | Generate app icons from `scripts/generate-icons.cjs` |

## Environment

The frontend expects the Django backend at `http://localhost:8000/api/`. Update the base URL in `src/services/api.js` if the backend runs elsewhere. Copy `.env.example` to `.env` to configure environment variables (`.env` is gitignored).

## API Service Layer

All HTTP calls go through `src/services/api.js`, which exposes typed modules:

```js
import { studentsAPI, academicAPI, financeAPI, activitiesAPI, facilitiesAPI, configAPI, authAPI, settingsAPI } from '../services/api'

// Each module exposes methods like:
await studentsAPI.getAll()
await studentsAPI.create({...})
await studentsAPI.patch(id, {...})
await academicAPI.getSections()
await financeAPI.createPayment({...})
await configAPI.updateConfig({...})
```

Axios interceptors handle:

- Automatic `Authorization: Token <token>` header from `localStorage.authToken`
- 401 responses auto-redirect to `/login`
- JSON and multipart/form-data Content-Type switching for logo uploads

## School Branding

The frontend reads school branding from `SchoolConfigContext` (`src/contexts/SchoolConfigContext.jsx`):

```js
import { useSchoolConfig } from '../contexts/SchoolConfigContext'

const { schoolName, schoolShortName, schoolLogo, schoolTagline } = useSchoolConfig()
```

Defaults:

- `schoolName` = "My School"
- `schoolShortName` = "SMS"
- `schoolTagline` = "School Management System"

The `TitleUpdater` component sets `document.title` per route (e.g. `Dashboard | My School`).

## Light-Only Theme

This project is light-only:

- `tailwind.config.js` does **not** include `darkMode: 'class'`
- `ThemeContext` is a stub returning `{ isDark: false, toggleTheme: () => {} }`
- `<html>` is force-stripped of any `dark` class on load
- All Tailwind dark variants have been removed from JSX

To re-enable dark mode, set `darkMode: 'class'` in `tailwind.config.js` and reintroduce the `dark:` variants per page.

## Print Formats

| Format | Use Case | Component |
|--------|----------|-----------|
| 80mm thermal receipt | Cashier transactions | `Receipt type="receipt"` |
| A4 official receipt | Official transactions | `Receipt type="official"` |
| A4 enrollment form | Student registration | `EnrollmentForm` |
| A4 section report | Section listing | `StudentSectionReport` |

## Browser / OS Support

- Chrome 90+, Firefox 88+, Edge 90+, Safari 14+ (web mode)
- Windows 7, 10, 11 (Electron mode)