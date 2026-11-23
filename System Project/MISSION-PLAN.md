# Mission — Hide the Django backend entirely behind a single public origin

Repo: System Project (workspace; origin: GitLab D4RK7H3N/SMS)
Public origin target: **https://sms.darkzhub.asia/api/***

## Phases

### P0 — Recon & risk acceptance (lecture seule) — DONE
- `tools/leak-inventory.md` (inventaire complet: hôtes, DNS, headers baselines, fuites F1-F10 / B1-B8)
- User sign-off: yes

### P1 — Same-origin API (frontend repo, branche `security/hide-backend`) — DONE
- `frontend/src/services/api.js` — BASE_URL → `VITE_API_BASE || ''` (baseURL same-origin `/api/*` en prod)
- `frontend/.env` / `.env.development` (dev default `https://gw.darkzhub.asia`) / `.env.example` / `.env.production` (default vide)
- `frontend/vite.config.js` — `build.sourcemap: false`
- `frontend/electron/main.js` — CSP électron → `connect-src 'self' https://sms.darkzhub.asia`
- `frontend/import_usat.cjs`, `import_one_file.cjs` — `host: 'sms.darkzhub.asia'`
- `frontend/e2e/{dashboard,import,global-teardown}.spec.js` — URLs → `https://sms.darkzhub.asia/api/*`
- `frontend/package.json` — `publish[0].url` → `https://sms.darkzhub.asia/releases/`
- Acceptance: `npx vite build` → aucune chaîne gw/sms2-api dans `dist/`; spot-checks API (401 unauth / 200 count=494 / detail 200 / payments 200) inchangées

### P2 — Reverse proxy via Cloudflare Worker — DONE
- `frontend/proxy-worker.js` — Worker : `/api/*` → `ORIGIN` (env secret), sets `Host: <origin>`, `X-Forwarded-Host: sms.darkzhub.asia`, `X-Forwarded-Proto: https`; allowlist headers pass-through; strips `Server`/`X-Powered-By`/`Via`
- `frontend/wrangler.proxy.jsonc` — name `sms-api-proxy`, route `sms.darkzhub.asia/api/*`
- Deploy : `npx wrangler deploy --config wrangler.proxy.jsonc` → Deployed, route activée
- Secret : `npx wrangler secret put ORIGIN --config wrangler.proxy.jsonc` → value `https://sms2-api.darkzhub.asia`
- Test : `curl https://sms.darkzhub.asia/api/students/?page_size=2` → 401 == origine, body identique, pas de nom d'origine dans headers

### P3 — Django: eliminate host leakage (à faire)
1. `school_pos/pagination.py` : ajouter `RelativePagination` (PageNumberPagination) → next/previous = path + query only
2. `school_pos/school_pos/settings.py` : `REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']` → `school_pos.pagination.RelativePagination`
3. Grepp : `sms2-api`, `gw.darkzhub`, absolute URLs dans serializers / views / email templates / media URL helpers ; ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS → public origin(s)
4. Test automatisé : aucune réponse paginée ne contient `http://` ou `sms2-api` (ajouter test)
5. Acceptance : test PASS + suite unitaire existante PASS

### P4 — Cloudflare Tunnel + firewall lockdown (à faire)
1. Créer le tunnel (Cloudflare API), routes : `gw.darkzhub.asia` → backend, `dashboard.darkzhub.asia` → backend, `sms.darkzhub.asia` → backend
2. DNS : supprimer les A records publics de `sms2-api.darkzhub.asia` et `gw.darkzhub.asia`
   - Attention : l'ORIGIN du proxy Worker (`https://sms2-api.darkzhub.asia`) devra être repointé vers le nouvel ingress tunnelé (ex. `https://dashboard.darkzhub.asia` ou l'URL publique du tunnel)
   - Guard : mis à jour dans `frontend/wrangler.proxy.jsonc` + secret `ORIGIN` + P2 retest
3. Firewall : commandes ufw + `school_pos/scripts/firewall-state-check.sh` (autoriser CF IPs → port 8000, défaut refusé)
4. config.yml + README du tunnel
5. Acceptance : `dig +short gw.darkzhub.asia` → vide ; port 8000 inatteignable depuis IP non-CF

### P5 — Django production hardening + headers (à faire)
1. Settings : DEBUG=False, SECURE_PROXY_SSL_HEADER, SECURE_SSL_REDIRECT, SESSION/CSRF COOKIE_SECURE, HSTS 31536000 + SUBDOMAINS, nosniff, X_FRAME_OPTIONS='DENY', CSRF_TRUSTED_ORIGINS, ALLOWED_HOSTS publics
2. Middleware : strip Server/X-Powered-By/Via + CSP (`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`)
3. Staff portal : Bootstrap/Font Awesome/Inter sur CDN → locaux (vendor/) + SRI
4. Acceptance : curl public origin : HSTS + CSP + nosniff + X-Frame-Options=DENY sur les 4 hôtes

### P6 — Tests, vérification, smoke (à faire)
1. Backend : suite unitaire + nouveau test RelativePagination
2. Frontend : build + grep dist
3. `tools/verify-hiding.sh` (PASS/FAIL par check) + sortie sauvée
4. Smoke : login `/api/auth/login/` (test1/test2), `/api/students/?page_size=5`, endpoints payment + assessment
5. Sign-off final

### P7 — Documentation (à faire)
1. `docs/deployment/backend-hiding.md` — runbook (route worker, tunnel, firewall, ordre DNS, rollback, incident "backend leaked")
2. `docs/security/backend-hiding-threat-model.md`
3. CI : étape non-blocking du verification script dans les PRs
4. Note de risque finale : ce qui ne peut pas être caché + extras (WAF, monitoring)

### ROLLBACK (backout < 10 min)
- `git revert security/hide-backend` (branche)
- Worker → bypass / route retirée
- Ré-ajouter les A records DNS (gw, sms2-api)
- Repousser le firewall allow (CF ranges)
- Restaurer ORIGIN secret si modifié
- `git push` revert

## FINAL STATUS (end of session)
- P0–P7 implemented. P1/P2/P3/P5 changes are live; P4 infra (tunnel/DNS/firewall)
  is config-as-code only, pending a maintenance window.
- Verification: `tools/verification-output.txt` (sections 1–2 PASS for all
  controlled hosts; residual FAILs documented in the risk note).
- Docs: `docs/deployment/backend-hiding.md`,
  `docs/security/backend-hiding-threat-model.md`,
  `docs/security/backend-hiding-risk-note.md`,
  `school_pos/cloudflare-tunnel/{config.yml,README.md}`.
- No commits made — awaiting user diff review as required.
- Residual risks: Cloudflare edge `Server` header, separate dashboard app,
  DNS/firewall not applied, legacy desktop clients, intermittent local PG
  connection failures, unit tests blocked by test-DB creation.
