# Leak Inventory — School Management System (P0 — recon & risk acceptance)

**Date:** 2026-11-19 (Vietnamese: 19 novembre 2026)
**Branch:** `security/hide-backend` (to be created when work starts)

## 0. Scope & identity verification

| Question | Answer |
|---|---|
| Is the API in another repo? | **No.** The Django backend (`school_pos/`) is served on `gw.darkzhub.asia` and `sms2-api.darkzhub.asia` via `school_pos/nginx.conf` (lines 12, 26: `server_name gw.darkzhub.asia sms2-api.darkzhub.asia sms.darkzhub.asia`). The web SPA lives in the same repo in `frontend/`. The Cloudflare account is `reperiajames@gmail.com` (user id `c61023bb47f9d71242fe23c9fdd1456d`). |
| Which hosts answer today? | `sms2-api.darkzhub.asia` → 302 `/staff/login/` (Django). `gw.darkzhub.asia` → 302 `/staff/login/` (Django). `sms.darkzhub.asia` → 200 (SPA via Worker sms-3). `dashboard.darkzhub.asia` → 200 (separate dashboard app). |

## 1. Current DNS (A records)

All four hosts are proxied by Cloudflare; **no public A records exist yet** for
`gw.darkzhub.asia` / `sms2-api.darkzhub.asia` beyond Cloudflare IPs:

```
sms2-api.darkzhub.asia : 104.21.86.217, 172.67.137.60, 2a06:4700:3036::ac43:893c, 2a06:4700:3036::6815:56d9
gw.darkzhub.asia       : 104.21.86.217, 172.67.137.60, 2a06:4700:3036::ac43:893c, 2a06:4700:3036::6815:56d9
sms.darkzhub.asia      : 104.21.86.217, 172.67.137.60, 2a06:4700:3036::ac43:893c, 2a06:4700:3036::6815:56d9
dashboard.darkzhub.asia: 104.21.86.217, 172.67.137.60, 2a06:4700:3036::ac43:893c, 2a06:4700:3036::6815:56d9
```

(`dig`/`nslookup` on this box go through the local resolver `RTK_GW.bbrouter`;
the answers are the public Cloudflare anycast IPs.)

## 2. Response headers — P0 baseline (tools/baseline/headers-*.txt)

- `sms2-api.darkzhub.asia` (tools/baseline/headers-sms2-api.txt): **no HSTS, no CSP, no
  X-Frame-Options denial on API responses; `Server: cloudflare`**; CORS allow-headers
  visible on 302 responses.
- `gw.darkzhub.asia` (headers-gw.txt): same — no HSTS/CSP; has
  `Access-Control-Allow-Headers/Methods/Max-Age` (Django CORS on the gateway responses).
- `sms.darkzhub.asia` (headers-sms.txt): no HSTS, no CSP; `Server: cloudflare`.
- `dashboard.darkzhub.asia` (headers-dashboard.txt): no HSTS, no CSP; `Server: cloudflare`.

## 3. Baseline API responses (staging, tools/baseline/)

- Unauthenticated: `GET /api/students/?page_size=2` → 401 `{"detail":"Authentication
  credentials were not provided."}`; same for `/api/payments/?page_size=2` (401).
- Authenticated (e2e token, `frontend/e2e/.auth/token.txt`):
  - `GET /api/students/?page_size=2` → 200, `count: 494`,
    `"next":"http://sms2-api.darkzhub.asia/api/students/?page=2&page_size=2"` ← **leak #1**
  - `GET /api/students/?page_size=2&page=2` → 200,
    `"next":"http://sms2-api.darkzhub.asia/api/students/?page=3&page_size=2"`,
    `"previous":"http://sms2-api.darkzhub.asia/api/students/?page_size=2"` ← **leak #1**
  - `GET /api/payments/?page_size=2` → 200, `count: 0`, `next/previous: null`.

## 4. Leak inventory — frontend (JS-visible)

| # | File:line | Ref | Severity | Status |
|---|---|---|---|---|
| F1 | `frontend/.env.production:1` | `VITE_API_URL=https://gw.darkzhub.asia` | **High** | P1 |
| F2 | `frontend/.env.example:2` | `VITE_API_URL=https://gw.darkzhub.asia` | High | P1 |
| F3 | `frontend/electron/main.js:361` | `connect-src 'self' https://gw.darkzhub.asia https://sms2-api.darkzhub.asia` | High (electron CSP) | P1 |
| F4 | `frontend/package.json:110` | updater `url: https://sms2-api.darkzhub.asia/releases/` | Medium | P4 (release feed — server side by design, but the URL itself is the backend host) |
| F5 | `frontend/e2e/dashboard.spec.js:19`; `e2e/import.spec.js:13`; `e2e/global-teardown.js:11` | `https://sms2-api.darkzhub.asia` (E2E_API default) | Medium (CI/scripts, not shipped to browser) | P1 |
| F6 | `frontend/import_usat.cjs:32`; `frontend/import_one_file.cjs:21` | `host: 'sms2-api.darkzhub.asia'` | Medium | P1 |
| F7 | `frontend/check_sections.cjs:18` | `page.goto('https://sms.darkzhub.asia/…')` | Low (public origin — fine) | informational |
| F8 | `frontend/src/contexts/SchoolConfigContext.jsx:117-121` | comments about absolute `https://sms2-api…` URLs + dev-only rewrite logic | Medium (dead logic in prod) | P1 |
| F9 | `frontend/src/services/api.js:5-12, 143` | comments only | Low | P1 |
| F10 | `frontend/.env.development:4` | comment | Low | P1 |

## 5. Leak inventory — backend (P0)

| # | File:line | Ref | Severity | Status |
|---|---|---|---|---|
| B1 | `school_pos/school_pos/settings.py:59-62` | `ALLOWED_HOSTS` includes `gw.darkzhub.asia`, `sms2-api.darkzhub.asia` | **High** | P3 |
| B2 | `school_pos/school_pos/settings.py:316` | `PUBLIC_ORIGIN` default `https://sms2-api.darkzhub.asia` | Medium | P3 |
| B3 | `school_pos/school_pos/settings.py:362-368` | `CORS_ALLOWED_ORIGINS` includes backend hosts + `https://sms-2-production.up.railway.app` | Medium | P3 |
| B4 | `school_pos/templates/base.html:10,12,14,532` | Bootstrap (jsdelivr), Font Awesome (cdnjs.cloudflare.com), Inter (fonts.googleapis.com) — **staff portal CDN deps** | Medium | P5 |
| B5 | `school_pos/staff/templates/login.html:8,9,10,180` | same CDN trio on the staff login page | Medium | P5 |
| B6 | `school_pos/nginx.conf:12,26` | `server_name gw.darkzhub.asia sms2-api.darkzhub.asia sms.darkzhub.asia` | High | P4/P5 |
| B7 | `school_pos/scripts/tunnel_watchdog.ps1:11` | `checkUrl = 'https://sms2-api.darkzhub.asia/api/sections/'` | Medium | P4 |
| B8 | `school_pos/api/views.py:629` + baseline files | `PageNumberPagination.next/previous` are **absolute `http://sms2-api.darkzhub.asia` URLs** (confirmed: `tools/baseline/api-students-page2-auth.json` line 1: `"next":"http://sms2-api.darkzhub.asia/api/students/?page=2&page_size=2"`) | **High** | P3 |

## 6. Risk acceptance notes

- **Leak F8/B8 are the biggest functional risks**: the SPA will keep sending
  browser traffic to the backend host until P1 changes `api.js`; the API will
  keep emitting absolute backend URLs until P3 changes pagination. Both are
  invisible until the CORS/HSTS stage is in place (P5).
- **B4/B5** (public CDNs on the staff portal): breaks offline school labs;
  bundle them locally (or with SRI) in P5.
- **B2 (`PUBLIC_ORIGIN`)** is by design the *canonical* public origin — it
  should be re-pointed from `sms2-api` to `sms` in P3. The name is fine; the
  value must not remain a "backend host" from the user's point of view...
  actually `PUBLIC_ORIGIN` is used to build media URLs (`/media/...`), so it
  should become `https://sms.darkzhub.asia` so logos/images point at the public
  origin.
- **Acceptance to proceed:** P1 (frontend same-origin), then P2 (Worker proxy),
  P3 (backend host-leak elimination), P4 (tunnel + firewall), P5 (hardening),
  P6 (tests + verification), P7 (docs).

## 7. Rollback at P0

Nothing to roll back (read-only).
