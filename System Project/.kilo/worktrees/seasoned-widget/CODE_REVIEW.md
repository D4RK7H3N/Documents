# SMS-2 — Full Code Review

**Date:** 2026-08-13
**Scope:** Django backend (`school_pos/`), React frontend (`frontend/`), Cloudflare Worker (`school_pos/cloudflare-worker/`), deployment workflow
**Method:** Static analysis + architectural review across all modules

---

## 1. Executive Summary

The SMS-2 School Management System is a mature 3-tier monolith-plus-edge stack: a Django REST backend (18 apps, ~3,700-line central `api/views.py`), a React 18 / Vite / Tailwind frontend (~11,300 lines across 21 pages), and a new Cloudflare Worker + D1 backend being introduced as a parallel deployment. The Django backend has been hardened substantially (auth throttling, explicit serializer whitelists, CORS whitelist, row-locked tuition writes), and the frontend is feature-complete with good print/receipt support.

**However, several P0 issues remain**, mostly leftover defaults and scaffolding rather than business-logic defects:

1. Hardcoded `SECRET_KEY` and DB password fallbacks in `settings.py`
2. `X_FRAME_OPTIONS = "ALLOWALL"` — an invalid value that disables clickjacking protection
3. Unauthenticated, path-traversal-prone update-file streaming (`api/updates_view.py`)
4. Cloudflare Worker ships with committed placeholder `JWT_SECRET` + fabricated seeded admin hash
5. CF Worker `nextORNumber` is non-atomic → duplicate OR numbers under concurrency (Django side already fixed the same class of bug)

**Verdict:** Deployable for LAN/school use, but the P0 items should be fixed before any public/internet exposure. No automated tests exist anywhere — highest-leverage improvement would be adding them.

---

## 2. Architecture Overview

### 2.1 Monorepo Layout

```
System Project/                    (repo root, git: master)
├── school_pos/                    ← Django backend (repo root of SMS-2 subtree)
│   ├── 18 Django apps (accounts, api, assessment, cashier, dorm, dropouts,
│   │   graduation, payments, products, revenue, sales, school_config, staff,
│   │   students, tours, tracks, tuition + project package school_pos/)
│   ├── cloudflare-worker/         ← new CF Worker backend (D1 + R2 + jose)
│   ├── requirements.txt, manage.py
├── frontend/                      ← React 18 + Vite + Tailwind + Electron
│   ├── src/ (21 pages, components, contexts, services)
├── docs/audit/                    ← prior security/frontend audits (2025-06-30)
├── RELEASE_NOTES.md, CORS_CONFIG.md
└── AGENTS.md                      ← project working memory / constraints
```

### 2.2 Backend — Django REST Framework

| Layer | Detail |
|---|---|
| Database | PostgreSQL (`SMSS`), env-driven (`DATABASE_URL` override) |
| Auth | DRF `TokenAuthentication` + `SessionAuthentication`; custom `CaseInsensitiveAuthBackend` + `StaffAuthenticationMiddleware` |
| API surface | `/api/` DefaultRouter (~25 resources) + per-app session routes (`/students/`, `/cashier/`, `/tours/`, `/dorm/`, ...) |
| Admin | Jazzmin-themed Django admin |

Key design decision: the central `api` app holds **no models** — all models live in their feature apps, and `api/views.py` aggregates them into ~22 viewsets. This works but produces a god-file (see §3.4).

### 2.3 Frontend — React + Vite + Electron

- `HashRouter` (Electron `file://` compatibility), lazy-loaded pages, v7 future flags
- Axios (`services/api.js`) with token interceptor, 15s timeout, 401 handling
- `AuthContext` + `SchoolConfigContext` (localStorage-cached branding)
- Print flows via `react-to-print`: 80mm thermal receipts, A4 SOA, section reports
- Capacitor 8 present (web/native storage abstraction), Electron 42 with NSIS packaging

### 2.4 Cloudflare Worker

- Router-based single-entry Worker (`src/index.js`), 15 endpoints
- D1 binding `DB`, R2 binding `STORAGE` (declared, unused)
- JWT via `jose` (HS256), PBKDF2-SHA256 password hashing via Web Crypto
- Money stored as **INTEGER centavos** (consistent, exact)

### 2.5 Git Remote Topology

| Remote | URL | Branch |
|---|---|---|
| `origin` | https://gitlab.com/D4RK7H3N/SMS.git | master (tagged v1.0.0/releases) |
| `github` | https://github.com/D4RK7H3N/SMS.git | master |
| `sms2` | https://github.com/D4RK7H3N/SMS-2.git | master (school_pos subtree only) |

---

## 3. Backend (Django) Findings

### 3.1 P0 — Critical

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| B1 | **Hardcoded SECRET_KEY fallback** | `school_pos/settings.py:26` — `os.getenv("SECRET_KEY", "django-insecure-^4oe2d!y*7^$wm6a!...")` | Publicly-known key signs sessions if env unset → session forgery on any misconfigured deployment | Remove fallback; fail hard: `os.environ["SECRET_KEY"]` or generate per-deploy |
| B2 | **Hardcoded DB password fallback** | `school_pos/settings.py:216` — `os.getenv("DB_PASSWORD", "darkzhen")` | Production DB password in source; commits to GitLab/SMS-2 permanently | Remove fallback (require env); move to `.env`/secret store |
| B3 | **Unauthenticated update-file streaming** | `api/updates_view.py:11` — `@permission_classes([AllowAny])`; `file_path = UPDATES_DIR / filename` | Publicly streams `.exe`/`.yml` from `updates/`; **no path traversal check** (`../` in filename resolves outside `updates/`) | Restrict to auth+role, sanitize filename (`PurePath(...).name`), validate extension, or move behind authenticated endpoint |

### 3.2 P1 — High

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| B4 | **`X_FRAME_OPTIONS = "ALLOWALL"`** | `settings.py:359` | Not a valid Django value — invalid values **disable** clickjacking protection entirely (comment claims Electron needs it, but Electron doesn't use iframes for API calls) | Remove the setting (default `DENY`), or scope framing exceptions per-view with decorators |
| B5 | **Debug endpoint `test_upload`** | `api/views.py:1016` | Returns raw uploaded Excel contents/headers to any authenticated user; leftover | Delete or gate behind `DEBUG`/superuser |
| B6 | **Broad ALLOWED_HOSTS wildcards** | `settings.py:52–53` — `".ngrok-free.dev"`, `".railway.app"` (+ `.vercel.app` previously) | Accepts any subdomain of these hosts; with `DEBUG=False` risk is low but violates host-header hygiene | Keep only exact production FQDNs + localhost |
| B7 | **No HTTPS enforcement + secure-cookie conflict** | `settings.py:338` `SECURE_SSL_REDIRECT = False`; `SESSION_COOKIE_SECURE = not DEBUG` | On plain-HTTP LAN, secure cookies are silently dropped → users can't log in; production relies on reverse proxy | Set `SECURE_SSL_REDIRECT` via env (True on hosted deploys), keep False for LAN; decouple cookie security from DEBUG |
| B8 | **No automated tests** | all `tests.py` are 2-line stubs | Zero regression protection for 3,700-line views file; latent bugs ship (e.g. tx duplicate, grade sync) | Priority: smoke tests for auth + tuition payment math + enrollment |

### 3.3 P2 — Medium / Hygiene

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| B9 | Dead duplicate model files | `cashier/models22.py`, `students/models223.py` | Confuse tooling; `cashier/models.py` redefines `TuitionPayment` shadowing real `tuition.TuitionPayment` | Delete; consolidate into `tuition` app |
| B10 | Empty `accounts` app | `accounts/` (no models/migrations) but in INSTALLED_APPS | Dead weight | Remove from INSTALLED_APPS or implement |
| B11 | Non-matching CORS wildcards | `settings.py` — `"https://*.up.railway.app"`, `"https://*.vercel.app"` | django-cors-headers does exact matching — these never match; misleading | Remove wildcard-looking entries, keep exact FQDNs |
| B12 | God-file views | `api/views.py` 3,736 ln; `students/views.py` 1,370 ln; `StudentViewSet` ~930 ln | Unmaintainable; merge conflicts; review difficulty | Split viewsets by domain (finance/students/academics...) |
| B13 | Blanket `except:` + silent passes | `api/views.py` tuition create (~1585, ~1615) | Parsing errors swallowed → confusing 500s | Catch specific exceptions, log, re-raise as 400 |
| B14 | In-function imports peppered | `api/views.py` (`from django.db import transaction` inside methods) | Hurts readability | Hoist to module top |
| B15 | Heavy/incidental dependencies | `requirements.txt`: opencv-python, matplotlib, pyzbar, reportlab, qrcode | Slow installs, broken builds (opencv needs system libs) | Audit & trim; keep only used |
| B16 | Stub admin/tests across apps | most `admin.py` files empty | Admin UX inconsistent with Jazzmin setup | Populate via generated admin or drop DJANGO admin for API-first |
| B17 | Stale CORS doc | `CORS_CONFIG.md` still shows `CORS_ALLOW_ALL_ORIGINS = True` | Misleads future maintainers | Update to reflect whitelist |

### 3.4 Strengths (Django)

- Login throttled (`LoginRateThrottle` 10/hr) + global `anon: 20/hr, user: 1000/hr`
- All serializer whitelists explicit — **no `fields = "__all__"` anywhere**
- Tuition payment writes wrapped in `transaction.atomic()` + `select_for_update()` (row-locked, 4 sites)
- Email change requires `old_password`; `change_password` rotates token
- Explicit CORS whitelist, no BasicAuthentication, DRF auth packages tidy
- `@login_required` on all session-facing student views
- `CaseInsensitiveAuthBackend` does dummy-hash on miss (timing-attack defense)

---

## 4. Frontend (React) Findings

### 4.1 P1 — High

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| F1 | **`axios` not declared in `package.json`** | `frontend/package.json` — runtime deps lack `axios` (1.16.1 imported everywhere) | Transitive dep today; `npm ci --omit=dev` or a dependency bump can silently break build/runtime | `npm i axios` — declare it |
| F2 | **Orphaned `PaymentsPage.jsx`** (246 ln) | `src/pages/PaymentsPage.jsx` — no route in `App.jsx`, no imports | Dead code that looks like a feature | Wire to a route or delete |
| F3 | **Raw localStorage bypassing `storage` helper** | `SchoolConfigContext.jsx:18/43/67`, `Receipt.jsx:10`, `CashierPage.jsx:33/409`, `EnrollPage.jsx:17/26`, `SettingsPage.jsx` | `storage.js` wrapper (try/catch, Capacitor-aware) exists precisely for this; raw calls break on native and can throw on private mode | Route all through `services/storage.js` |

### 4.2 P2 — Medium / Hygiene

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| F4 | Duplicate API namespaces | `services/api.js` — `academicAPI` vs `trackAPI`/`courseAPI`; `activitiesAPI` vs `tourAPI`/`graduationAPI`; `facilitiesAPI` vs `dormAPI`; `financeAPI` vs `tuitionAPI`/`revenueAPI`/`salesAPI`/`productAPI` | ~150 lines of redundant wrappers; drift risk | Consolidate to canonical namespaces |
| F5 | Inconsistent context dirs | `src/context/` vs `src/contexts/` | Import confusion | Merge into one `src/contexts/` |
| F6 | 4x duplicated tuition upsert | StudentsPage, TuitionPage, CashierPage, PendingPaymentsPage each implement `getTuitionByStudent → update-or-create` | Diverged copy-paste bugs (fixed in one page, not others) | Extract shared `useTuitionUpsert` hook |
| F7 | Repeated error-string chain | `err?.response?.data?.error || err?.response?.data?.detail` in ~10 places | Inconsistency | Shared `extractErrorMessage(err)` util |
| F8 | Error swallowing | many fetches `.catch(() => [])` with console-only logging | Silent failures on production | At minimum toast on network errors |
| F9 | Service-layer bypass | `CashierPage.jsx:103,213` calls raw `apiClient.get('/api/students/')` | Bypasses interceptors/namespaces; hard to audit | Use `studentsAPI.getAll` |
| F10 | Module-level mutable state | `LoadingContext.jsx` (counters/listeners outside React) | Non-idiomatic; hard to test | `useSyncExternalStore` or context state |
| F11 | No eslint/prettier/test framework | `package.json` devDeps | Style drift; zero unit tests (existing audits score LOW) | Add eslint + vitest smoke tests |
| F12 | `utils/cache.js` global Map w/ 30s TTL only used by DashboardPage | no invalidation on mutation | Stale dashboard data after edits | Invalidate on data-changing actions or drop cache |

### 4.3 Strengths (Frontend)

- 401 interceptor with `_retry` guard, targeted storage removal (no `localStorage.clear()` data loss)
- Route guards (`ProtectedRoute`/`PublicRoute`) + lazy loading with Suspense
- Electron configured well (contextIsolation, no nodeIntegration, navigation guard, window-open block)
- Print CSS correctly scoped per modal (80mm thermal / A4 SOA)
- `PesoSign` custom SVG component everywhere (no DollarSign leftovers)
- Consistent toast pattern via NotificationContext

---

## 5. Cloudflare Worker Findings

### 5.1 P0 — Critical

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| C1 | **Committed placeholder JWT_SECRET** | `wrangler.toml` `[vars]` — `"your-jwt-secret-change-in-production-min-32-chars"` | If not overridden via `wrangler secret put`, anyone knowing the repo can forge HS256 tokens | Move to `[secrets]`/`wrangler secret put JWT_SECRET`; never in toml |
| C2 | **Fabricated seeded admin hash** | `schema.sql` seed INSERT — hex pattern `a1b2c3...` is not a real PBKDF2 hash of `admin123` nor anything else | Seeded admin **cannot log in** on a fresh D1 DB | Generate a real hash (run `hashPassword('...')` via a script once) or require `createsuperuser`-style CLI |

### 5.2 P1 — High

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| C3 | **Non-atomic `nextORNumber`** | `src/db.js` — SELECT then INSERT, no transaction/lock | Concurrent payments → duplicate OR numbers; `UNIQUE` constraint makes one insert fail with 500 | Wrap in D1 transaction/batch; or use single `INSERT ... ON CONFLICT DO UPDATE RETURNING` |
| C4 | **Payment flow not transactional** | `src/routes/tuition.js` `recordPayment` — tuition insert + payment insert + balance update are 3 separate queries | Partial failure = paid money with wrong balance | D1 batch/transaction wrapper in db.js |
| C5 | **`parseInt(amount, 10)` money trap** | `src/routes/tuition.js` — amount assumed centavos | Client sending pesos ("1500.50") becomes ₱15.00 — 100x mispricing, silently | Migrate to `parsePHP()` (handles both) or validate with explicit units in the API contract |
| C6 | **CORS `*` wildcard** | `src/middleware.js` — `Access-Control-Allow-Origin: '*'` | Contradicts the project's explicit-whitelist posture; bearer tokens over public custom domain | Whitelist exact origins (mirror Django list), add `Vary: Origin` |
| C7 | **No login rate limiting** | `src/index.js` login handler | Brute-forceable (Django has 10/hr; worker has none) | Simple in-D1 or KV-based failed-attempt counter |
| C8 | **Role checks missing on money routes** | `src/index.js` — only dorm checkin/checkout use `requireRole`; tuition payment, enrollment, revenue are auth-only | Any logged-in role (cashier, dorm_manager) can record/modify payments | Apply `requireRole('admin','cashier')` to tuition/enrollment writes |
| C9 | Placeholder `database_id` | `wrangler.toml` — `"your-d1-database-id-here"` | Deploy fails until replaced | Fill after `wrangler d1 create sms2-db` |

### 5.3 P2 — Medium

| # | Finding | Location | Impact | Fix |
|---|---|---|---|---|
| C10 | Stub logout / no revocation | `src/index.js` — logout returns "discard your token" | Tokens valid full 8h; refresh has no rotation/`jti` | Accept for v1; document; add token-blacklist later |
| C11 | `migrations/` dir missing but script expects it | `package.json` `"migrate": "wrangler d1 migrations apply sms2-db"` | Script fails; schema.sql must be applied via `d1 execute` | Rename script or convert schema.sql to a migration |
| C12 | Daily-report dead code | `src/routes/tuition.js` `dailyReport` — groups by non-selected `p.student_course`, recomputes via 2nd query | Confusing; first `byCourse` always 'Unknown' | Delete first grouping loop |
| C13 | Login leak | `src/index.js` — distinct `403 "Account is disabled"` | Username enumeration | Uniform message ("Invalid username or password") |
| C14 | Trailing-slash 404s | `src/middleware.js` `matchRoute` segment matcher | `/api/tuition/5/` → 404 | Strip trailing slash in router |
| C15 | Minor: unused imports/helpers, no security headers, R2 binding unused | `index.js` (`withCORS`), `middleware.js` (`parseQuery`), absence of `X-Content-Type-Options` | Hygiene | Clean + add headers |

### 5.4 Strengths (Worker)

- PBKDF2-SHA256 (100k iter, 16B salt) via Web Crypto — correct, Workers-native
- Money = INTEGER centavos with `formatPHP`/`parsePHP` helpers — exact by design
- `jose` JWT HS256 with env secret; generic error envelope (no stack leakage)
- Role middleware exists and is composable; router clean and small

---

## 6. Workflow Documentation

> NOTE: This section codifies what is currently **only implicit** (git config + habits). Nothing in the repo documents the SMS-2 push pattern — it lives in AGENTS.md only partially.

### 6.1 Git Remotes

```
origin  → https://gitlab.com/D4RK7H3N/SMS.git      (canonical repo, releases)
github  → https://github.com/D4RK7H3N/SMS.git      (mirror)
sms2    → https://github.com/D4RK7H3N/SMS-2.git    (school_pos subtree only)
```

### 6.2 SMS-2 Push Pattern (subtree)

Because SMS-2 must contain **only** `school_pos/`, pushes use `git subtree`:

```powershell
# After committing changes involving school_pos/:
git commit -m "feat: ..."   # normal commit on master

# Standard fast path:
git subtree push --prefix school_pos sms2 master

# When remote diverged (rejected non-fast-forward), use split + force:
git subtree split --prefix school_pos -b sms2-staging
git push sms2 sms2-staging:master --force
git branch -D sms2-staging
```

Notes learned in practice:
- `--squash` pull fails ("was never added") — use plain `git subtree pull --prefix school_pos sms2 master` and resolve conflicts manually
- Force-push to SMS-2 master is the accepted recovery path when remote diverged
- The full repo (`frontend/` etc.) goes to GitLab/GitHub, not SMS-2
- Vercel was attached to SMS-2 (commit email must match a GitHub account — `reperiajames@gmail.com`); all Vercel files have since been **removed** (back to Railway only)

### 6.3 Build Flow

```powershell
# Frontend
cd frontend
npm install
npm run dev            # dev server :5173
npx vite build         # → dist/ (verification build; must pass before pushing)
npm run build:win      # Electron NSIS installer → release/ (x64+ia32)

# Backend (LAN/Dev)
cd school_pos
.venv\Scripts\python.exe manage.py makemigrations
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_sample_students   # optional sample data
.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

There is **no CI config** in the repo — "build passes" is verified manually via `npx vite build`.

### 6.4 Deployments

| Target | Method | Status |
|---|---|---|
| Railway (backend) | Railpack 0.30+ `"provider": "python"` + `start.sh` (gunicorn); Dockerfile deprecated | **Blocked** — migration 0004 not applied (DB password auth error); existing students have `custom_tuition_fee = NULL` until re-entered |
| Ngrok (dev tunnel) | `https://grafting-demote-cruelly.ngrok-free.dev` → local runserver | Active |
| Electron | NSIS installer, `release/` | v1.0.0 shipped; v1.0.1 rebuild pending |
| Cloudflare Worker | `wrangler deploy` → `api.darkzhub.asia` (custom domain) | Scaffolded; deploy blocked on placeholder D1 id/secret (see C1, C9) |
| Vercel | ~~removed~~ | Removed 2026-08-13 (404 issues, static file complexity) |

### 6.5 Release Process

1. Verify `npx vite build` passes
2. Bump version in `RELEASE_NOTES.md` (currently v1.1.0)
3. Tag: `git tag vX.Y.Z` and push: `git push origin master --tags`
4. Create GitLab release with notes (done for v1.0.0)
5. Rebuild Electron installer for the tag and ship `release/` artifact
6. Update `AGENTS.md` Progress/Done section to match actual state

### 6.6 Key Runtime Facts (from AGENTS.md)

- Backend: `school_pos\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000`
- DB: PostgreSQL `SMSS` (user `postgres`) — password must come from env in prod (see B2)
- Frontend `.env`: `VITE_API_URL` must be bare base URL — **no trailing slash** (axios interceptor also strips it)
- axios timeout 15s; localStorage wrapped in try/catch via `storage` helper
- Print: cashier receipt 80mm thermal; SOA A4 portrait; `no-print` only on modal header/footer
- Grade levels: SHS Grade 11/12 + Bundled 1st/2nd Year only; graduation = Grade 12 + 2nd Year

---

## 7. Prioritized Fix Recommendations

### Do first — P0 (security, 1–2 days)

1. `settings.py`: remove SECRET_KEY + DB_PASSWORD fallbacks (B1, B2)
2. Set `SECRET_KEY`, `DATABASE_URL` in Railway env; wire to secrets
3. Harden `api/updates_view.py`: auth + filename sanitization (+ optional path check) (B3)
4. CF Worker: move JWT_SECRET to `wrangler secret`, fill D1 `database_id`, generate a real admin hash (C1, C2, C9)

### Do next — P1 (correctness, 2–3 days)

5. CF Worker: `nextORNumber` + payment flow in a D1 transaction/batch; `parsePHP` money parsing; CORS whitelist; login rate limit; role checks on money routes (C3–C8)
6. Django: fix `X_FRAME_OPTIONS`, delete `test_upload`, trim ALLOWED_HOSTS wildcards, fix secure-cookie/SSL split (B4–B7)
7. Frontend: declare `axios`, delete/route `PaymentsPage`, route all localStorage through `storage` helper (F1–F3)
8. Apply migration 0004 on Railway once DB access works; re-enter tuition for existing students via Settle Balance

### Later — P2 (hygiene)

9. Split god-file viewsets; delete dead model files; empty accounts app; trim requirements.txt (B9–B15)
10. Consolidate API namespaces; unify context dirs; shared tuition upsert hook; error util (F4–F8)
11. Populate Django admin or drop it; add vitest smoke tests + Django pytest smoke suite (B16, F11)
12. Update stale docs: CORS_CONFIG.md, AGENTS.md progress (B17)
13. Optionally move SMS-2 push pattern into `docs/WORKFLOW.md` or AGENTS.md so it's no longer tribal knowledge

---

### Coverage Summary

| Area | Lines reviewed (approx) | P0 | P1 | P2 |
|---|---|---|---|---|
| Django backend | ~13,000 (py) | 3 | 5 | 9 |
| React frontend | ~11,300 (jsx) | 0 | 3 | 9 |
| Cloudflare Worker | ~1,500 (js + sql + toml) | 2 | 7 | 6 |
| **Total** | **~25,800** | **5** | **15** | **24** |