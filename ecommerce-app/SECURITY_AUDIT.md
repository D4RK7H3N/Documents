# Clickbound — Security Audit & Remediation Log

Date: 2026-08-10
Scope: e-commerce app (Next.js 16.3 / Turbopack, Prisma + Postgres, JWT auth, Stripe checkout)

---

## 1. High-severity fixes

### 1.1 Checkout oversell race — `app/api/checkout/route.ts`
Stock was decremented after order creation with a blind `update`, so two concurrent checkouts could both pass the `stock > 0` check and oversell.

Fix:
- Added `StockShortageError`.
- Stock is now reserved inside the interactive transaction **before** order creation via a conditional decrement:
  `tx.product.updateMany({ where: { id, stock: { gte: qty } } })` → `count === 0` means shortage.
- Shortfall returns `409` with the offending items.

Verification (curl race test, stock = 3, two concurrent qty-2 checkouts):
- Exactly one `201`, one `409`; exactly one order created; stock never went negative.
- Empty cart → `400`.

### 1.2 Email change without verification — `app/api/me/route.ts`
Account email could be changed without proof of ownership (email is a login identifier + password-reset target).

Fix:
- `emailProof` added to the update schema.
- Changing email now requires `verifyProof(emailProof, "email-proof")` whose payload `.email` must equal the new (lowercased) address; otherwise `400 "Verify your new email first to change it"`.
- New email lowercased; already-taken → `409`.
- Fixed re-issued cookie `maxAge` to use `ACCESS_TOKEN_MAX_AGE_SECONDS`.

Client — `components/AccountForm.tsx`:
- Submitting with a changed email auto-sends an OTP (`forSignup: true`), shows an inline code entry panel, verifies it, then auto-submits with the proof.
- Dev-mode code hint panel mirrors `LoginForm`.

Verification: no proof → `400`; with valid proof → `200` and email changed.

### 1.3 Refresh token rotation — `app/api/auth/refresh/route.ts`
Refresh tokens were reusable forever once stolen.

Fix:
- Rotation with reuse detection: each refresh mints a new token (stored hashed) and revokes the old one in a `$transaction`.
- Missing/invalid/expired → `401` + cookie clear.
- Replay of an already-rotated (revoked) token → **all** of the user's refresh tokens are revoked (stolen-token containment).

Verification: token rotates on refresh; replaying the old token → `401` and the new token is also dead.

---

## 2. Security crawl (curl) — verified already-safe

| Check | Result |
|---|---|
| JWT `alg: none` | Rejected |
| 9 weak HS256 secrets | Rejected |
| Missing `exp` | Rejected |
| IDOR: orders / invoice / cancel by other users | 404 / 403 / 404 |
| Notifications + mark-read userId scoping | Scoped |
| Mass assignment `role: "ADMIN"` | Ignored |
| Cart negative/zero quantity | 400 |
| OTP brute force | Locked after 5 attempts |
| Customer token on `/api/admin/*` | 403 |
| `X-Frame-Options`, `nosniff` | Present |

---

## 3. Findings & fixes

### 3.1 OTP flood DoS (Medium) — `app/api/otp/send/route.ts`
Per-target limits existed, but an attacker could rotate targets to burn server CPU (bcrypt cost-10 per code).

Fix: per-client cap `otp-send:<client>` — 10 codes / 5 min, `429` + `Retry-After`.
Verification: 10× `200` then `429` (`Retry-After: 297`).

### 3.2 Newsletter (Low) — `app/api/newsletter/route.ts`, `app/api/newsletter/unsubscribe/route.ts`
No rate limit; no unsubscribe; welcome email sent but not provable.

Fix:
- Rate limit `newsletter:<client>` — 5 / 15 min.
- Welcome email now delivered via `deliverNewsletterWelcome` (`lib/channels.ts`, same SMTP/mock seam) with a signed unsubscribe URL.
- New unsubscribe endpoint: POST (JSON) and GET (email link); token is a signed `newsletter-unsub` JWT (`lib/otp.ts`); row already gone → `400`.

Verification: 5× `201` then `429`; unsubscribe link `200` + row deleted; reuse `400`; token bound to its email.

### 3.3 No Content-Security-Policy (Low) — `proxy.ts`, `app/layout.tsx`
Fix: per-request nonce (`crypto.randomUUID()` → base64) attached as `x-nonce` request header + CSP response header. Root layout is `force-dynamic`, so the nonce is injected into every rendered script/style.

Policy (prod): `default-src 'self'; script-src 'self' 'nonce-…' 'strict-dynamic'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests`
Dev adds `'unsafe-eval'` (React tooling).

Verification:
- Dev: `200` + CSP header, nonce matches the 30 script nonces per page render.
- Prod (`next start`): `200`, same policy **without** `unsafe-eval`.
- `npm run build` passes; 26 routes; TypeScript + ESLint clean.

### 3.4 Stripe webhook 500 when unconfigured (Info) — `app/api/stripe/webhook/route.ts`
Now returns `503` instead of a stack-trace `500`. Verified.

---

## 4. Email delivery (Brevo SMTP)

- `.env` uses Brevo relay: `smtp-relay.brevo.com:587` (STARTTLS, `SMTP_SECURE` unset → `secure: false`).
- Failure was `525 5.7.1 Unauthorized IP address` — Brevo rejects the client IP because "Blocking unauthorized IP addresses" was **activated** for SMTP keys.
- Fix (dashboard): authorize the public IP (`Settings → Security → Authorized IPs`) or deactivate the restriction for SMTP keys (recommended on machines with dynamic IPs).
- Verified end-to-end: live OTP send via real SMTP (`POST /api/otp/send 200`, 4.4 s SMTP round-trip, no error, no mock log).

Dev/mock behavior (`lib/channels.ts`): `@clickbound.com` addresses and unset `SMTP_*` fall back to console logging + client dev-code panel. PHONE is mock-only (no SMS provider yet).

---

## 5. Remaining notes / cleanup

- QA users from testing remain in the DB (`qacart…@clickbound.com`, etc.).
- Test orders, events, and newsletter subscribers were deleted; product `cmskhea2t0001tvb467maj0pu` ("Grid Runner Sling") stock restored to 26.
- QA rate-limit buckets (OTP/newsletter) can be `429` for up to 15 min after test runs; they reset on their own or on dev-server restart.
- Dev server on `:3000`; logs in the temp dir (`dev-out.log` / `dev-err.log`).
