# Security design — backend hiding threat model

## Why same-origin

The browser talks **only** to `https://sms.darkzhub.asia/api/*`. A single
origin means:
- no CORS surface (`Access-Control-Allow-Origin` is no longer needed for the
  SPA; `CORS_ALLOWED_ORIGINS` is reduced to the public origin),
- no alternate backend hostname in bundles/API bodies/headers that attackers
  could target directly,
- one place to enforce HSTS/CSP and to observe traffic,
- cookies/tokens are never sent to a second host.

Threats addressed:
- **Origin discovery** from minified JS / pagination links / media URLs —
  removed (see `tools/verification-output.txt` §1).
- **Direct-to-origin attacks** — origin listens on `127.0.0.1:8000`; the plan is
  to firewall it to Cloudflare CIDRs only (`school_pos/cloudflare-tunnel/`).
- **Fingerprinting** — `Server`/`X-Powered-By`/`Via` stripped by the Django
  middleware and the Worker (the edge's own `Server: cloudflare` remains).
- **Clickjacking / MIME confusion / XSS** — `X-Frame-Options: DENY`, `nosniff`,
  strict SPA CSP; inline loader script extracted so `script-src 'self'` works.
- **CDN supply chain** — SRI on Bootstrap/Font Awesome in the staff portal.
- **Tunnel blips** — read-only retries (3×, 400/800 ms) in the proxy Worker;
  writes are never retried (a lost payment response must not double-charge).

## Architecture

```
Browser / Electron ──HTTPS──> sms.darkzhub.asia
                                ├─ /             static Worker sms-3 (SPA + CSP/HSTS)
                                └─ /api,/media,/releases
                                      proxy Worker sms-api-proxy
                                        │ Host: <origin>, X-Forwarded-Host/Proto
                                        ▼
                                  backend origin (127.0.0.1:8000, Django/Waitress)
                                        ▲
                                Cloudflare Tunnel (only ingress; firewall)
```

## Data classification

Student records (PII) are unchanged: every `/api/students/*` endpoint still
requires `IsAuthenticated`; the public endpoints remain `/api/health/` and
`/api/school-config/current/` (school-wide branding only). The CSRF login at
`/staff/login/` and token login at `/api/auth/login/` are unchanged.

## Residual risks (see risk note)

`docs/security/backend-hiding-risk-note.md` records everything that could not
be fully hidden or verified in this environment.
