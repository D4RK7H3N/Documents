# Project Working Memory

## Goal
Continue improving the School Management System — shipping UI consistency, enrollment/tuition fixes, security hardening, and GitLab deployment.

## Constraints & Preferences
- All `DollarSign` icon usages replaced with custom `PesoSign` SVG component across all frontend pages
- Only SHS (Grade 11, Grade 12) and Bundled Tesda Accredited (1st Year, 2nd Year) grade levels — Grade 7–10 removed entirely
- Graduation year levels: Grade 12 + 2nd Year Bundled Student
- Tours grade levels: `SHS - Grade 11` / `Bundled - 1st Year Tesda Accredited`
- Light-only theme only — all broken dark mode Tailwind variants removed
- Cashier print receipt: `no-print` class moved off modal wrapper to header/footer only; receipt numbers auto-generated as `OR-YYYY-NNNNN` with `localStorage` persistence
- Backend API base URL must not have trailing slash; axios timeout 15s; localStorage calls wrapped in try/catch
- `CORS_ALLOWED_ORIGINS` explicitly whitelisted — no wildcard `*`

## Progress
### Done
- **TuitionPage**: Added alphabetical sort (`filtered.sort((a,b) => a.studentName.localeCompare(b.studentName))`) in `applyFilters`
- **SectionsPage**: Stat cards → colored bg (`rounded-2xl p-4 border border-transparent`), search card → `rounded-2xl border-gray-100`, modal → backdrop blur + sticky header + `rounded-2xl shadow-2xl`; toast notifications added
- **CoursesPage**: Stat cards with colored bg, search/filter card with Reset button, modal updated to ToursPage pattern; toast notifications added
- **TracksPage**: Stat cards, search bar, modal all updated to ToursPage pattern; toast added
- **api.js fixes**: BASE_URL strips trailing slash with `.replace(/\/$/, '')`; `timeout: 15000` on `axios.create`; 401 interceptor no longer calls `/api/auth/logout/` (just clears storage + redirects); network error check `if (!error.response)` at top of response error handler; all `localStorage` calls wrapped in `storage` helper (`get`/`set`/`remove` with try/catch); `configAPI.updateConfig` FormData header set to `undefined` not `'multipart/form-data'`
- **GitLab push**: Remote `https://gitlab.com/D4RK7H3N/SMS.git` added; root `.gitignore` created (excludes node_modules, .venv, dist, .env, __pycache__, etc.); `school_pos/.gitignore` updated to exclude `updates/`; 328 files committed and pushed to `master`
- **Release v1.0.0**: Tagged and pushed; GitLab release created with notes
- **TuitionPage SOA**: View modal replaced with full Statement of Account modal — school header from `SchoolConfigContext`, student info, tuition summary cards (Total/Paid/Balance), **payment history** table fetched from payments API with running balance column, **Print** button with `@media print` CSS (hides all UI except SOA), **Settle Balance** button (sets `amount_paid = total_tuition`), `no-print` class on header/footer
- **Backend enrollment tuition fix**: `TuitionPaymentViewSet.create()` in `api/views.py` now accepts `total_tuition` + `amount_paid` (initial tuition setup mode) in addition to `amount` (normal payment mode). Setting a student's initial tuition no longer fails.
- **`.env` fix**: Was `VITE_API_URL=VITE_API_URL=https://.../api/` (duplicated variable name + trailing path) — corrected to `VITE_API_URL=https://grafting-demote-cruelly.ngrok-free.dev`
- **React Router warnings**: `future={{ v7_startTransition: true, v7_relativeSplatPath: true }}` added to `HashRouter` in `index.jsx`
- **Favicon**: `public/favicon.svg` created (blue square + white "S"), linked in `index.html`
- **Security fixes applied across backend (`school_pos/`):**
  - `api/views.py` — `update_profile` now requires `old_password` to change email; `LoginViewSet` gains `LoginRateThrottle` (10/hour)
  - `students/views.py` — `@login_required` added to `tuition_payment`, `tuition_receipt`, `enroll_student`, `tuition_payment_search`
  - `api/serializers.py` — replaced all `fields = "__all__"` with explicit whitelists; added `date_of_birth = DateField(required=False, allow_null=True, allow_blank=True)` to fix 400 on empty string
  - `settings.py` — `ALLOWED_HOSTS`: removed wildcard `"*"` and subnet wildcard; `REST_FRAMEWORK`: removed `BasicAuthentication`, added `DEFAULT_THROTTLE_CLASSES` + `DEFAULT_THROTTLE_RATES` (`anon: 20/hour`, `user: 1000/hour`); `DEBUG` default changed to `False`
  - CORS: `CORS_ALLOW_ALL_ORIGINS = False`, explicit `CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:8000", "https://grafting-demote-cruelly.ngrok-free.dev"]`
  - `Vary: origin` header confirmed on responses; unauthorized origin (`evil-site.com`) returns no `Access-Control-Allow-Origin` header — CORS blocks it
- **date_of_birth 400 fix**: `StudentsPage.jsx:231` — empty DOB converted to `null` before PUT payload; `serializers.py` — added `allow_blank=True` on DateField for resilience
- **Logout data loss fix**: `AuthContext.jsx:111` — replaced `localStorage.clear()` with targeted `removeItem('authToken')` + `removeItem('user')` — preserves cached config/notification/receipt data
- **Error leakage fix**: `EnrollmentForm.jsx:117` — replaced `setError(err?.response?.data)` (whole backend response) with safe string extraction
- **SettingsPage crash fix**: `SettingsPage.jsx:93` — wrapped `JSON.parse` in try/catch for malformed `schoolConfig`

### In Progress
- (none) — awaiting verification

### Blocked
- Railway migration 0004 not yet applied (DB password auth error)
- Existing students on Railway have `custom_tuition_fee = NULL` — SOA shows 0 tuition until re-entered

## Key Decisions
- SOA replaces the old View modal — adds printable formal statement with payment history + running balance
- Enrollment tuition is set via a two-step flow (student create/patch → `createTuition` with `total_tuition`) — backend now accepts both initial setup and normal payment in the same endpoint
- Security throttling set to 20/hr anonymous, 100/hr authenticated — prevents brute-force on login/change_password without impacting legitimate use
- CORS hardened from `AllowAll` to explicit whitelist after confirming ngrok works with specific origins
- Email change now requires password re-entry — prevents token-only account takeover

## Next Steps
- Test enrollment flow end-to-end (create student with initial tuition)
- Verify SOA prints correctly and Settle Balance works
- Rebuild the Electron installer with all changes for v1.0.1
- Consider adding `EmailField` validation + confirmation for email changes
- Apply migration 0004 on Railway once DB connection is fixed
- Re-enter tuition for existing Railway students via Settle Balance

## Critical Context
- Backend: `school_pos/.venv/Scripts/python.exe manage.py runserver 0.0.0.0:8000`
- **SECURITY: never put credentials, API tokens, or passwords in this file.** It is
  tracked in git and pushed to public GitHub/GitLab remotes. Values that used to
  live here (the DB password and a live DRF API token) were disclosed publicly
  and had to be rotated. Keep secrets only in the untracked `school_pos/.env`
  and `.env` files, or a secret manager.
- Production API origin: `https://sms2-api.darkzhub.asia` (behind Cloudflare
  Tunnel -> Django). Frontend: `https://sms.darkzhub.asia`. Public gateway
  Worker: `gw.darkzhub.asia` (Worker `nexus-bridge`).
- Gateway admin endpoints (`/__gateway/*`) require header `X-Gateway-Token`
  (stored as the Worker secret `GATEWAY_TOKEN`); without it they return 404.
- Frontend `.env`: `VITE_API_URL=https://gw.darkzhub.asia`
- Build passes: `npx vite build` succeeds with no errors
- GitLab: `https://gitlab.com/D4RK7H3N/SMS` — `master` branch, `v1.0.0` tag

## Relevant Files
- `frontend/src/pages/TuitionPage.jsx`: alphabetical sort; full SOA modal (school header, payment history table, print CSS, Settle Balance)
- `frontend/src/pages/SectionsPage.jsx`: UI matched to ToursPage — colored stat cards, new search card, backdrop-blur modal, toasts
- `frontend/src/pages/CoursesPage.jsx`: stat cards, filter card with Reset, ToursPage modal, toasts
- `frontend/src/pages/TracksPage.jsx`: stat cards, search card, ToursPage modal, toasts
- `frontend/src/services/api.js`: trailing slash stripped, 15s timeout, storage helper, no logout call on 401, network error check, FormData header `undefined`
- `frontend/.env`: `VITE_API_URL=https://grafting-demote-cruelly.ngrok-free.dev` (was duplicated + had `/api/` suffix)
- `frontend/src/index.jsx`: `HashRouter future={{...}}` flags added
- `frontend/index.html` + `frontend/public/favicon.svg`: favicon added
- `school_pos/api/views.py` — `TuitionPaymentViewSet.create()`: accepts `total_tuition`/`amount_paid` for initial setup; `update_profile`: requires `old_password` for email change; `LoginRateThrottle` (10/hr) on login
- `school_pos/students/views.py` — `@login_required` on `tuition_payment`, `tuition_receipt`, `enroll_student`, `tuition_payment_search`
- `school_pos/api/serializers.py` — all `fields = "__all__"` replaced with explicit whitelists
- `school_pos/school_pos/settings.py` — `ALLOWED_HOSTS`: removed `"*"`; `REST_FRAMEWORK`: removed `BasicAuthentication`, added throttling; `CORS`: explicit origins, no wildcard
