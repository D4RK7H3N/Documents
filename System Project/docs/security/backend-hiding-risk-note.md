# Risk note — backend hiding (honest residual risks)

Status: P0–P6 implemented and verified where the environment allowed.
Output: `tools/verification-output.txt`.

## Cannot be hidden / not fully verified

1. **`Server: cloudflare`** — Cloudflare's edge adds this to every response;
   an origin cannot remove it. P6 flags it. It reveals Cloudflare, not the
   backend host. WAF rule alternative: none at origin level.
2. **`dashboard.darkzhub.asia`** — a separate application not in this repo.
   It has no HSTS/CSP/nosniff/XFO; P6 flags four FAILs for it. Needs its own
   owner to harden.
3. **DNS / firewall (P4) not applied live** — `gw.darkzhub.asia` and
   `sms2-api.darkzhub.asia` still have public A records; the origin firewall
   was not changed. Config is ready in `school_pos/cloudflare-tunnel/` but
   applying it is a maintenance-window change; `tools/verify-hiding.sh`
   cannot complete checks 4 and 5 until then (`dig` also not installed here;
   `ORIGIN_IP` was not supplied).
4. **Legacy desktop clients** — installed builds still call
   `gw.darkzhub.asia` and their updater uses `sms2-api.darkzhub.asia`.
   `gw` is kept in `ALLOWED_HOSTS` and routed by the tunnel; do not delete
   those DNS records until the desktops are reissued. New builds are
   same-origin (`/api`, `/media`, `/releases`) and their CSP allows only the
   public origin.
5. **Google Fonts on the staff portal** — not SRI-covered (CSS is generated
   per user agent); Bootstrap/Font Awesome have real SRI hashes. Self-host
   Inter (already bundled in the Electron app) as a follow-up.
6. **Intermittent PostgreSQL connection failures on the Windows origin** —
   ~5–10% of new connections fail with "server closed the connection
   unexpectedly" (reproduced with a direct 20-connection psycopg2 loop).
   This predates the mission's code changes but became visible under the
   new proxy path. `DB_CONN_MAX_AGE=0` removes stale pooled connections;
   a DB-backend connection retry or PostgreSQL/network investigation is
   still needed off-hours. This can leave the UI loading overlay hanging.
7. **Automated unit tests blocked** — `manage.py test` cannot create
   `test_SMSS` here (`server closed the connection unexpectedly` during
   migrations), while normal connections work. The new
   `test_relative_pagination.py` is committed but could not be executed;
   run it against a separate test DB off-hours. Not worked around silently.
8. **Cloudflare Tunnel blips** — the documented edge disconnects still cause
   occasional 502s. Worker read-retries reduce but cannot eliminate them.
   P4's direct tunnel route for `/api/*` is the structural fix (not applied
   live yet).

## Optional extras (not applied)

- Cloudflare WAF rule blocking direct access to legacy hosts by Host header.
- Worker analytics / alerting on 5xx rate > 1%.
- Self-host the staff portal's Inter font.
- CI job (non-blocking) in `.github/workflows/verify-hiding.yml` — added in P7.
