# SafeSwap PH

## Overview

Escrow trading app for Roblox accounts in the Philippine market. Django REST
backend (monolithic `core` app) + Flutter mobile client. Payments target
GCash/Maya, SMS OTP via Semaphore, Firebase Cloud Messaging, Asia/Manila
timezone.

**Path:** `C:\Users\DarkZhen\Documents\SAFESWAPPH` (no git repo at root)

**Tech stack:** Django 5 / DRF + SimpleJWT (token blacklist), PostgreSQL,
Channels (WebSockets - InMemory layer), Firebase Admin, Pillow, boto3 (R2),
Gunicorn, Jazzmin admin; Flutter (provider, http, flutter_secure_storage,
image_picker, web_socket_channel, firebase_core/messaging)

## Status

**Active at MVP level** - backend feature-complete with documented stubs
(payment gateways, signature verification). Flutter app is UI-first: auth/OTP/
KYC/listing/chat/uploads are wired to the API; marketplace data, trade actions,
and notifications are still mock/no-op.

## Backend (Django)

### Key models (18)

CustomUser (phone_number unique `+63...`, role buyer/seller/middleman/
administrator, is_banned, strike_count), PhoneOTP (hashed, 5 min), MiddleMan,
Listing, Trade (`pending -> active -> completed/disputed`), Escrow (1:1 trade),
Commission (20 = 10 creator + 7 middleman + 3 reserve, configurable via
PlatformConfig), Dispute, Blacklist (GCash numbers), PlatformConfig,
KYCVerification (PhilSys/DR license/passport/UMID/SSS/Voter's ID, selfie,
review workflow), Conversation/Message/MessageReport (off-platform contact
flagging), DeviceToken (FCM), InAppNotification, TermsOfService/TraderAgreement/
TradeCompletionAcknowledgment, PaymentIntent (gcash/maya, pending/paid/failed/
refunded, checkout_url).

### API areas (all under `/api/`)

- **Auth:** register (PH phone validation), verify-otp, token, token/refresh
  (SimpleJWT, access 6h / refresh 7d, rotation + blacklist)
- **Users:** /users/me/
- **Listings:** CRUD
- **Trade lifecycle:** start (assigns least-loaded verified middleman, creates
  Trade + Escrow atomically; 503 if none), confirm (split_commission +
  payout stub + escrow released + conversation locked + notifications),
  dispute, acknowledge
- **Disputes:** resolve (middleman only - buyer_wins = full refund,
  seller_wins = escrow minus commission)
- **Admin:** ban (also blacklists GCash + security-logged), config,
  kyc/review, kyc/pending
- **KYC:** submit (sellers only), status
- **Uploads:** /upload-url/ (R2 presigned PUT, 5 min, images only,
  `kyc/{user_id}/{uuid}`)
- **Chat:** conversations (+history 50/page), messages/send, messages/report;
  **WebSockets** `ws/chat/{id}/` (typing, read receipts, flagging, lock) and
  `ws/escrow/{id}/` (live status) - JWT via `?token=`
- **Payments:** create (stub checkouts: GCash -> Xendit-style URL, Maya ->
  PayMongo-style URL), webhook (no signature verification - TODO)
- **Notifications:** list/read/unread-count
- **TOS:** current/accept/check
- **Honeypots:** /api/admin/ and /api/wp-admin/ return 404 + security log

### Throttling & security

anon 30/hr, user 500/hr, otp 3/min, login 5/min, register 10/hr; SSL redirect,
HSTS 1yr, X-Frame-Options DENY, secure cookies, security logger to
`logs/security.log`.

### Env vars (see `.env.example`)

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DB_*` (PostgreSQL),
`SEMAPHORE_API_KEY`/`SEMAPHORE_SENDER_NAME` (SMS, empty = skipped),
`MAYA_API_KEY`/`MAYA_API_SECRET`/`MAYA_BASE_URL`, `FIREBASE_*` (push, empty =
disabled), `DEEPSEEK_API_KEY` (declared, unused). Settings-only: `SECURE_SSL_REDIRECT`,
`CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` (default `https://darkz.isroot.in`),
`R2_*` (required for uploads).

## Flutter app

- **Screens (15):** splash, welcome, register, login, otp, onboarding, tos,
  kyc_required, kyc, home (Marketplace/My Trades/Profile tabs), listing_detail,
  create_listing, chat, payment, profile
- **Providers:** auth_provider (token storage in flutter_secure_storage),
  kyc_provider. **Services:** upload_service (presigned URL -> PUT to R2)
- **Backend URL:** hardcoded `http://10.0.2.2:8000/api` in every file (Android
  emulator loopback) - no centralized api_client/env config yet
- **Wired to API:** auth, OTP, KYC, TOS check/accept, listing creation, chat
  (REST + WS), payment intent creation, uploads
- **Not wired:** trade start/confirm/dispute (no trade_service), marketplace
  (home uses hardcoded sample cards), notifications/device tokens, listing
  detail buttons are no-ops

## Workflow

### Backend

1. `pip install -r requirements.txt` (venv at `venv/`)
2. Copy `.env.example` to `.env`, fill DB + secrets
3. `python manage.py migrate`
4. `python manage.py runserver` (dev, uses ASGI for WS) - or
   `daphne`/`gunicorn` for production `[TBD - deployment target]`
5. Admin at `/admin/` (Jazzmin themed)
6. Uploads require `R2_*` env vars (endpoint errors if unset)

### Flutter

1. `cd flutter_app`, `flutter pub get`, `flutter run`
2. Test on Android emulator (10.0.2.2 = host loopback); physical device needs
   the PC's LAN IP + `ALLOWED_HOSTS`/CORS updates
3. Build: `flutter build apk`

### Test flows

- **Onboarding:** Splash -> Register (PH phone) -> OTP verify (Semaphore; dev
  logs code in plaintext) -> Onboarding carousel -> TOS accept -> KYC gate
  (sellers) -> Home
- **Trade happy path:** Browse listing -> Start Trade (middleman assigned +
  escrow created) -> Pay (stub checkout URL) -> webhook -> trade `active` ->
  locked chat -> buyer confirms -> commission split + payout stub -> `completed`
  -> acknowledgment + notifications
- **Dispute:** buyer opens -> middleman resolves -> refund or release
- **Admin:** KYC review/approve, ban (GCash blacklist), disputes, commission
  config - via Jazzmin or /api/

## Known issues / next steps

- Payment create/webhook are stubs (no signature verification, TODO docstrings).
- `TradeCompletionAcknowledgment.transaction` field shadows
  `django.db.transaction` - migration 0004 rename planned, not present.
- `.env` is committed to the folder - move to `.env.example` only.
- DeepSeek API key declared but unused.
- Flutter: no url_launcher (checkout URLs can't open), no centralized API base
  URL, trade + marketplace + notifications not wired.
- Design spec: `docs/superpowers/specs/2026-07-05-mvp-completion-design.md`.
