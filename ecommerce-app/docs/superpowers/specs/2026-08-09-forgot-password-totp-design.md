# Forgot Password + TOTP Authenticator — Design

Date: 2026-08-09
Status: Approved by user (design)

## Problem

Users have no way to recover a forgotten password, and the only 2FA is email/phone OTP, which is
interceptable. Add: an email-verified password reset, and RFC 6238 TOTP (authenticator app) with
recovery codes.

## Decisions (user-approved)

1. Forgot password identifies the account by **email only**.
2. When TOTP is enabled, it **replaces** the email/phone OTP login step, and the trusted-device
   bypass is **disabled** for that user (every login requires the app code).
3. A password reset **kills all sessions**: every `RefreshToken` is revoked and the user's
   `sessionEpoch` is bumped, invalidating all `trusted_device` cookies.
4. TOTP enrollment issues **10 recovery codes** (shown once, hashed at rest).

## Schema changes

- `User`: add `totpSecret String?`, `totpEnabledAt DateTime?`, `sessionEpoch Int @default(0)`.
- New model `RecoveryCode`: `id`, `userId`, `codeHash`, `usedAt DateTime?`, `createdAt`,
  `user` relation, `@@index([userId])`. Exactly 10 rows per enrolled user.

## lib/totp.ts (new)

- `generateTotpSecret()` — 20 random bytes, base32.
- `totpUri(secret, email)` — `otpauth://totp/Clickbound:{email}?secret=..&issuer=Clickbound&algorithm=SHA1&digits=6&period=30`.
- `verifyTotpCode(code, secret)` — RFC 6238, 30s steps, ±1 window, HMAC-SHA1 truncation,
  constant-time compare (`crypto.timingSafeEqual`), replay guard via in-memory `userId → lastStep`.
- `encryptSecret(secret)` / `decryptSecret(payload)` — AES-256-GCM; key = sha256(JWT_SECRET);
  stored as `base64(iv):base64(tag):base64(ciphertext)`. No new env vars.
- `generateRecoveryCodes()` — 10 × `XXXX-XXXX` (base32-ish chars); `hashRecoveryCode()` (bcrypt),
  `verifyRecoveryCode(code, hash)`.

## API routes

| Route | Auth | Behavior |
| --- | --- | --- |
| `POST /api/auth/forgot` | none | Rate-limited (5/15min, `rateLimitKey`). Looks up email; ALWAYS returns the same response (no account-existence leak). If found: `issueOtpCode(email, EMAIL, userId)`. Resend = call this again (same cooldowns). |
| `POST /api/auth/forgot/verify` | none | `{ email, code, newPassword }` → `verifyOtpCode(email, EMAIL, code)` → bcrypt-12 rehash → update password, `sessionEpoch += 1`, revoke all open refresh tokens, delete the user's OTP records. Does NOT auto-login. |
| `GET /api/account/totp/setup` | user | Generate secret, encrypt+store it (`totpEnabledAt` stays null), return `{ secret, uri, qr }` (QR dataURL via `qrcode`). |
| `POST /api/account/totp/verify` | user | `{ code }` → verify against the stored secret → set `totpEnabledAt`, insert 10 recovery codes → return them once. |
| `POST /api/account/totp/disable` | user | `{ code }` → verify current TOTP → clear secret/enabled, delete recovery codes. |

## Login flow changes

- `lib/auth.ts` — `trustedDeviceToken(userId, epoch)` includes an `epoch` claim;
  `verifyTrustedDevice(token, userId, expectedEpoch)` requires it to match.
- `POST /api/auth/login` — after valid password: if `user.totpEnabledAt` → return
  `{ requireTotp: true, challenge: challengeToken(id, "TOTP", email, "totp-challenge") }` and skip
  the trusted-device bypass entirely. Otherwise unchanged (trusted bypass / email-phone challenge).
- `lib/otp.ts` — `challengeToken` gains a `kind` param (default `"login-challenge"`); verifyChallenge
  returns it. TOTP challenges use kind `"totp-challenge"`.
- `POST /api/auth/otp` — for a totp challenge: 6-digit code → TOTP verify; `XXXX-XXXX` → recovery
  code verify (mark used, reject reuse). Both proceed to the existing session issuance.

## UI

- `app/forgot-password/page.tsx` + `components/ForgotPasswordForm.tsx` — wizard: email → code
  (CodeInput) → new password + confirm (strength meter) → success (link back to login).
- `components/LoginForm.tsx` — "Forgot your password?" link under the password field; new TOTP step:
  CodeInput + "Use a recovery code instead" toggle (plain input, `XXXX-XXXX`).
- `components/AccountSecurity.tsx` — Authenticator section: enable (QR + secret + verify input),
  one-time recovery codes screen, disable (current code required).
- `app/api/me/route.ts` — include `totpEnabledAt` in the response so the security page knows state.

## Testing

HTTP QA script (existing pattern): enable TOTP → login with app code → wrong code 401 →
recovery-code login marks code used → second use rejected → forgot-password reset revokes refresh
token + trusted device (login again required) → `tsc --noEmit` + `eslint .` clean.

## Files touched

`schema.prisma`, `lib/totp.ts` (new), `lib/auth.ts`, `lib/otp.ts`, `app/api/auth/forgot/route.ts`,
`app/api/auth/forgot/verify/route.ts`, `app/api/account/totp/{setup,verify,disable}/route.ts`,
`app/api/auth/login/route.ts`, `app/api/auth/otp/route.ts`, `app/api/me/route.ts`,
`app/forgot-password/page.tsx`, `components/ForgotPasswordForm.tsx`, `components/LoginForm.tsx`,
`components/AccountSecurity.tsx`, `package.json` (+`qrcode`, `@types/qrcode`), migration.
