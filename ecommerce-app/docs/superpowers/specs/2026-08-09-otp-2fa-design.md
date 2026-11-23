# OTP Verification: Sign-up Email/Phone + Login 2FA

Date: 2026-08-09
Status: Approved (sections 1-3)

## Objective

Verify email and phone with OTP codes during sign-up, add OTP 2FA at login (phone-first, email fallback), with a remembered-device shortcut. Codes are delivered via a dev/mock channel (console + dev-only debug panel) behind a single channel module.

## Data model

- `OtpCode`: `target` (email/phone string), `channel` (EMAIL|PHONE), `codeHash` (bcrypt), `userId?`, `expiresAt` (10 min), `attempts` (max 5), `createdAt`. Row deleted on successful verify (single-use); deleted+recreated on resend.
- `User`: add `emailVerifiedAt DateTime?`, `phoneVerifiedAt DateTime?`.
- Evidence tokens (signed JWTs, 15 min): `email-proof` (email), `phone-proof` (phone) issued after each verify step; register requires both matching the submitted fields.
- Login: password OK → no session cookie yet; short-lived (5 min) `challenge` JWT (userId + channel) + code sent. Valid `trusted_device` cookie (30 d) skips the OTP step. OTP redeem sets `token` cookie (+ `trusted_device` if remembered).
- Channel decision at login: verified phone → PHONE; else EMAIL, which also marks `emailVerifiedAt` (first-time fallback for legacy users).
- Rate limiting (in-memory): 60 s resend cooldown, 6 codes/hour per target+channel, 5 failed attempts invalidate the code.

## Endpoints

- `POST /api/otp/send` — `{ channel, target, forSignup?: true }`; preflight duplicate-email/phone check when forSignup; sends code; returns `{ ok, expiresInSec, debugCode? }` (debug only when NODE_ENV !== production).
- `POST /api/otp/verify` — `{ channel, target, code }` → on success: `{ ok, proof }` (email-proof or phone-proof JWT).
- `POST /api/otp/verify-account` — authenticated; re-verifies own email/phone (with optional phone update) and sets the VerifiedAt flags directly.
- `POST /api/auth/register` — now requires `emailProof` + `phoneProof` matching submitted email/phone; creates user with flags set; existing cookie/login flow.
- `POST /api/auth/login` — password gate; trusted-device shortcut OR challenge: `{ requireOtp: true, challenge, channel, targetMasked, rememberMe: true, debugCode? }`.
- `POST /api/auth/otp` — `{ challenge, code, remember }` → validates code (atomic row delete), sets session (+ trusted_device) or 401 with attempts-left.
- `POST /api/auth/otp/resend` — `{ challenge, emailInstead? }` → new challenge + code (60 s cooldown), supports channel switch to email.

## UI (components/LoginForm.tsx rework + new CodeInput / AccountSecurity)

- Sign-up after fields: step 1 email → code screen (6-digit, numeric, auto-submit at 6) → checkmark → 2 phone → register. Back button, resend countdown, inline attempts-left errors. Dev-only code panel (last sent codes, dev builds only).
- Login: password OK → code screen with masked target, "Use email instead" when phone, "Remember this device" checkbox (default on), resend 60 s cooldown.
- Account settings: Security card — verified status badges, editable phone, "Verify email/phone" with the same mini flow (`/api/otp/send` + `/api/otp/verify-account`).
- Logout clears `token` and `trusted_device`.

## Files

`prisma/schema.prisma` + migration `add_otp`, `lib/otp.ts`, `lib/channels.ts`, `lib/auth.ts` (+trusted-device helpers), `app/api/otp/{send,verify,verify-account}/route.ts`, `app/api/auth/{login,otp,otp/resend,register}/route.ts`, `components/LoginForm.tsx`, `components/CodeInput.tsx`, `components/AccountSecurity.tsx`, `app/account/page.tsx`, `prisma/seed.ts` (verified account for QA).

## Verification

tsc/eslint; migrate+generate (kill server first); headless browser: sign-up via dev codes, login shortcut (trusted), full login code, email fallback (legacy user), 5-attempt lockout, resend cooldown, account-settings verify, error-free console.