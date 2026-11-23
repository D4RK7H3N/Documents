# Deployment runbook — hide the Django backend (backend-hiding)

Branch: `security/hide-backend`. Nothing in this runbook is applied
automatically; the live changes already made are listed in §1.

## 1. What is already live (this session)

| Change | Artifact | Verification |
|---|---|---|
| Frontend same-origin API | `frontend/src/services/api.js` (`VITE_API_BASE`, default empty) | deployed in `sms-3` Worker `de05c6b3`; deployed JS contains no `gw`/`sms2-api` strings |
| Reverse proxy Worker | `frontend/proxy-worker.js`, `wrangler.proxy.jsonc` (routes `/api/*`, `/media/*`, `/releases/*`; read-only retry on 502/503/504) | Worker `1c9e474f`; `curl https://sms.darkzhub.asia/api/health/` → 200 |
| Deep-link redirect | `frontend/worker.js` (`/login/`, `/auth/login/` → `/#/login`) | 302 `Location: https://sms.darkzhub.asia/#/login` |
| Relative pagination | `school_pos/school_pos/pagination.py` (`RelativePagination`) | `next: "/api/students/?page=2&page_size=2"` |
| No backend host in API responses | `PUBLIC_ORIGIN=https://sms.darkzhub.asia` (env), `logo` serialized as relative media path | `tools/verification-output.txt` §1 all PASS |
| Security headers | SPA Worker CSP/HSTS/nosniff/XFO; Django middleware strips `Server`/`X-Powered-By`/`Via` and sets staff CSP + HSTS | `tools/verification-output.txt` §2 PASS for sms/sms2-api/gw |
| Dev/Electron compatibility | `VITE_API_BASE=` in all `.env*`; Vite proxies `/api` locally; `gw` kept in `ALLOWED_HOSTS`; `/media`,`/releases` proxied | Electron dev shell uses `localhost:5173/api/*` |
| DB stability mitigation | `DB_CONN_MAX_AGE=0` in `school_pos/.env` | see risk note — residual intermittent PG connection failures |

## 2. Order of operations for a fresh deployment

1. **Backend first** (Django): apply settings/middleware/serializer/pagination
   changes, then `Restart-Service -Name DarkZSMS-Backend`. Verify
   `GET /api/health/` on `127.0.0.1:8000` and `GET /api/students/?page_size=2`
   with a token (relative `next`).
2. **Proxy Worker**: `npx wrangler deploy --config wrangler.proxy.jsonc`.
   Set the secret with `npx wrangler secret put ORIGIN --config
   wrangler.proxy.jsonc` (value: the backend origin HTTPS URL). Verify all
   three routes.
3. **Static Worker / SPA**: `npx wrangler deploy --config wrangler.jsonc`
   (runs `npm run build`). Verify:
   - `GET /` → new asset hash, no absolute backend hosts in JS
   - `GET /login/` → 302 → `/#/login`
   - `GET /initial-loader.js` → 200 JavaScript
4. **Headers**: `bash tools/verify-hiding.sh` with `SMS_TEST_TOKEN` set.
5. **Only then** P4 infra: create the tunnel (`school_pos/cloudflare-tunnel/`),
   add `gw`/`dashboard` CNAMEs, apply the firewall allow-list from the Cloudflare
   `/ips` endpoint, and remove the legacy public A records in that order.
6. Re-run `tools/verify-hiding.sh` + `firewall-state-check.sh`.

## 3. Rollback (<10 minutes)

1. DNS: restore the A/AAAA records for `gw.darkzhub.asia` and
   `sms2-api.darkzhub.asia` (old values in the change ticket).
2. Firewall: remove the CF-only allow rules / restore the previous ruleset.
3. Worker bypass: remove the routes from `wrangler.proxy.jsonc` and re-deploy,
   or delete the Worker route in the Cloudflare dashboard. The static `sms-3`
   Worker and its deep-link redirect can stay.
4. Django: `git revert` the phase commits, then `Restart-Service -Name
   DarkZSMS-Backend` (this also clears the in-memory login throttle).
5. `git push` the revert.

## 4. Incident: "backend leaked"

- Confirm the symptom: `curl -s https://sms.darkzhub.asia/api/students/
  ?page_size=2 -H "Authorization: Token …" | grep sms2-api` must be empty.
- If `next` is absolute again: the Django service is running an older
  `pagination.py` → restart it.
- If `logo` is absolute again: check `PUBLIC_ORIGIN` in `school_pos/.env` and
  the serializer `logo` method field.
- If the bundle contains a host string: rebuild + re-deploy `sms-3`.
- If `gw.darkzhub.asia` resolves to a non-Cloudflare IP: restore the tunnel
  CNAME and remove the A record immediately.
- Run `bash tools/verify-hiding.sh` after every corrective action.
