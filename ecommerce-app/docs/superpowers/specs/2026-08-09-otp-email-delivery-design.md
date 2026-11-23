# OTP Delivery via SMTP — Design

Date: 2026-08-09
Status: Approved (design) — pending spec review

## Problem

OTP codes are currently only "delivered" to a mock/dev channel: `deliverOtpCode` logs to the server console, and the client shows the code in a dev panel because the API returns `debugCode` in non-production builds. There is no real email delivery.

## Goals

1. Send OTP emails through a generic SMTP provider (nodemailer), configured purely via env vars.
2. Phone (SMS) channel stays mock for now — no SMS provider this pass.
3. Keep dev ergonomics: no SMTP configured → codes still appear in the dev panel. QA addresses (`*@clickbound.com`) always stay in mock mode even when SMTP is configured, so seeded test accounts keep working.
4. When a real email is sent, the client must NOT receive the code — the UI shows "check your inbox" instead of the panel.

## Non-goals

- SMS/WhatsApp delivery (future: `PHONE` branch of `deliverOtpCode` is the single seam to extend)
- Refresh/access token changes, schema changes, route changes
- Email template design beyond a minimal plain-text + HTML body

## Architecture

Single delivery seam already exists: `deliverOtpCode(info)` in `lib/channels.ts`, called by `issueOtpCode()` in `lib/otp.ts`. All callers (login, `/api/otp/send`, `/api/otp/resend`, `/api/auth/otp`, verify-account flows) route through `issueOtpCode`, so only two lib files and one component change.

### lib/channels.ts (rewritten core)

- `isEmailConfigured()` → `Boolean(process.env.SMTP_HOST)`
- `isMockDelivery(channel, target)`:
  - EMAIL: `!isEmailConfigured() || target.toLowerCase().endsWith("@clickbound.com")`
  - PHONE: `true` (always mock this pass)
- `deliverOtpCode({ channel, target, code })`:
  - EMAIL non-mock: lazily-created nodemailer transport (`smtpTransport()` singleton), send:
    - from `SMTP_FROM` (default: `SMTP_USER` — see env table)
    - to `target`
    - subject: "Clickbound verification code"
    - plain text + minimal HTML with the 6-digit code and 10-minute expiry note
    - throws on failure (caller handles)
  - EMAIL mock / PHONE: `console.log` (current behavior, keeps QA working)
- Env vars:
  - `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` (default: `SMTP_USER`), `SMTP_SECURE` (default false → STARTTLS)
- Comment marks the PHONE branch as the future Twilio/REST insertion point.

### lib/otp.ts (small changes)

- `issueOtpCode`:
  - Wrap `deliverOtpCode` in try/catch → on error return `{ ok: false, error: "Couldn't send the code — please try again." }` (callers already handle `!ok` with a friendly message).
  - `debugCode` gating: `isDev() && isMockDelivery(channel, target) ? code : undefined`. Mock + dev → code present; real SMTP or production → code never leaves the server.
  - `recordSend` stays before delivery (anti-spam cooldown protects even on failed sends).

### components/LoginForm.tsx (panel visibility)

- Dev panel (dashed box) renders only when the most recent OTP response contained `debugCode`.
- When a real email is sent, the step already shows the masked target; add a fallback line "Code sent — check your inbox" if no debug code was returned and delivery was real.

## Data flow

```
POST /api/auth/login (valid password, untrusted device)
  -> issueOtpCode(target, "EMAIL", userId)
     -> checkRateLimit (cooldown + hourly cap)          [unchanged]
     -> persist OtpCode row (bcrypt-hashed)             [unchanged]
     -> recordSend                                      [unchanged]
     -> deliverOtpCode: SMTP send OR mock console.log   [CHANGED]
        - SMTP failure -> { ok: false } -> route 502
  -> challenge + targetMasked + (debugCode only if mock+dev)
```

## Testing

- No SMTP env → login for `otp@clickbound.com` still returns `debugCode`, panel works (existing QA flow unchanged).
- SMTP env set with unreachable host → `/api/auth/login` returns a delivery error (502 family), no crash.
- SMTP env set + reachable (wire-up later) → code present in the email body, absent from the API response, panel hidden.
- `tsc --noEmit` + `eslint .` clean.

## Files touched

| File | Change |
| --- | --- |
| `lib/channels.ts` | SMTP transport + mock routing + `isMockDelivery` |
| `lib/otp.ts` | `debugCode` gate, delivery error catch |
| `components/LoginForm.tsx` | panel visibility + inbox note |
| `package.json` | add `nodemailer`, `@types/nodemailer` |
| `.env.example` | commented `SMTP_*` vars |
