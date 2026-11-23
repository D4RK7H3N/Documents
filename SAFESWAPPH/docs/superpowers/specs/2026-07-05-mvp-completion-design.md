# SafeSwap PH — MVP Completion Design

Date: 2026-07-05

## Purpose

Take the SafeSwap PH codebase (Django + DRF backend, Flutter mobile client) from its current "backend-done / app-scaffolded-only" state to a polished, end-to-end runnable MVP that a real user could onboard into.

## What's there now

**Backend (Django + DRF)** — substantial, ~1250 LOC of views, full model layer, 50+ endpoints, JWT auth, phone OTP, KYC, chat, disputes, escrows, payments, admin (Jazzmin), WebSockets via Channels, FCM device tokens, honeypot traps, security logging. Migrations exist (0001–0003). Models include: `CustomUser`, `Listing`, `Trade`, `Escrow`, `Commission`, `Dispute`, `Blacklist`, `PlatformConfig`, `KYCVerification`, `Conversation`, `Message`, `MessageReport`, `DeviceToken`, `InAppNotification`, `TermsOfService`, `TraderAgreement`, `TradeCompletionAcknowledgment`, `PaymentIntent`, `MiddleMan`, `PhoneOTP`.

**Flutter app** — only `flutter_app/lib/main.dart` exists (~190 LOC). It imports ~17 screens, 2 providers, and a notifications service — **none of which exist**. `pubspec.yaml` declares: provider, http, flutter_secure_storage, image_picker, dotted_border, cached_network_image, intl, google_fonts, web_socket_channel, firebase_core, firebase_messaging.

**Known unfinished backend items** — `core/views.py:1179, 1182, 1199` (payment gateway stubs and webhook signature verification).

**Migrations** — 0001–0003 exist but `TradeCompletionAcknowledgment` model uses a `transaction` field name that **shadows the Django `transaction` module** used in views.py (e.g. `from django.db import transaction`). This is a latent bug waiting to be hit on import inside `atomic()` blocks.

## What's an "MVP" here?

Three concrete capabilities, all wired end-to-end:

1. **New user can register, verify phone, onboard, submit KYC, browse listings, open a chat with a seller, and start a trade.**
2. **Authenticated buyer can pay into escrow by picking GCash or Maya, get a checkout URL, and have the backend flip the trade to `active` on webhook.**
3. **An admin can use the Django admin (Jazzmin) to review KYC, resolve disputes, ban users, and adjust the commission config.**

Everything else (push notifications via FCM, WebSocket channels, polished empty states, animations, ratings/reviews, appeals workflow, etc.) is **out of scope** for this spec — stub it where missing, don't build it.

## Architecture

Two clean concerns, **strictly separated**:

### Backend
- **No shape changes to existing models or endpoints.** Why: 50+ endpoints, serialised payloads already used by the Flutter imports. Changing them breaks the app re-build below for no MVP value. Only fix is the `TradeCompletionAcknowledgment.transaction` → `trade` rename to avoid shadowing `django.db.transaction`.
- **Add `core/services/payments.py`** for GCash/Maya stub integration. Each provider exposes `create_checkout(amount, ref) -> url` and `verify_webhook(payload, signature) -> bool`. Stubs use deterministic fake checkout URLs but persist `PaymentIntent` rows with `provider_reference` so the webhook flow exercises real DB writes.
- **Add `core/services/storage.py`** for R2 presigned URL generation (the `upload-url` endpoint already exists but currently just returns the bucket name — needs to return a real presigned PUT URL).
- **Webhook signature verification** — implement HMAC-SHA256 with a config secret. If `MAYA_WEBHOOK_SECRET` (or `GCASH_WEBHOOK_SECRET`) not set, fall through with a security log warning so dev still works.

### Flutter app
- **Layered, isolated, testable.** Every screen is a `StatelessWidget` calling a `Provider`. Providers depend on services. Services depend only on `http`, `flutter_secure_storage`, and the FCM packages.
- **No business logic in widgets.** A screen that decides whether the user can press "Pay" is wrong. Compute that in a `Provider` and expose a `bool get canPay`.

```
lib/
  main.dart                              (exists, untouched)
  app.dart                               (extract SafeSwapApp → its own file)
  core/
    api_client.dart                      http wrapper, JWT inject, 401→logout
    env.dart                             base url, build flavor switches
    result.dart                          Result<T> for typed success/failure
  models/
    user.dart, listing.dart, trade.dart,
    message.dart, conversation.dart,
    notification.dart, kyc.dart, payment.dart
  services/
    auth_service.dart                    register / verify-otp / token / refresh / logout
    listing_service.dart                 list, get, create
    chat_service.dart                    conversations, messages, send, websocket
    trade_service.dart                   start, confirm, dispute, ack
    kyc_service.dart                     submit, status
    payment_service.dart                 create intent
    notification_service.dart            list, mark read, unread count
    device_service.dart                  register FCM token
    storage_service.dart                 secure_storage wrapper
  providers/
    auth_provider.dart                   existing
    kyc_provider.dart                    existing
    chat_provider.dart                   NEW
    trade_provider.dart                  NEW
    listing_provider.dart                NEW
    notification_provider.dart           NEW
  screens/
    splash_screen.dart                   existing (will write)
    welcome_screen.dart                  "
    register_screen.dart                 "
    login_screen.dart                    "
    otp_screen.dart                      "
    onboarding_screen.dart               "
    tos_screen.dart                      "
    kyc_required_screen.dart             "
    kyc_screen.dart                      "
    home_screen.dart                     "
    listing_detail_screen.dart           "
    create_listing_screen.dart           "
    chat_screen.dart                     "
    payment_screen.dart                  "
    profile_screen.dart                  "
  widgets/                                shared, reusable primitives
    primary_button.dart, screenshot_grid.dart,
    empty_state.dart, error_banner.dart,
    loading_view.dart, otp_input.dart
```

**Boundary rules:**
- Screens ↔ Providers only (never Services directly).
- Providers ↔ Services only (never `http` directly).
- Services own all network/storage/FCM side effects.
- Models are dumb data with `fromJson` / `toJson` only.

This keeps every layer small, makes mocking trivial, and means a screen change can't accidentally break auth.

## Data flow

End-to-end "happy path":

1. **Splash** → calls `GET /api/users/me/` with stored access token.
   - If 200 + `kyc.status == 'approved'` → home.
   - If 200 + KYC pending/missing → KYC gate.
   - If 401 → welcome.
   - If `has_seen_onboarding` is false → onboarding carousel first.
   - If TOS not yet accepted for `current` version → TOS screen.

2. **Register** → `POST /api/register/` → `POST /api/verify-otp/` → login → tokens stored in secure storage → splash → onboarding/TOS/KYC gate → home.

3. **Home** → `GET /api/listings/` → grid of cards (cached_network_image screenshots, price, seller name). Tap → listing detail.

4. **Listing detail** → `POST /api/trade/start/` with `listing_id` → backend creates Trade (pending), auto-creates Escrow + Commission. Response includes `payment_intent_required: true` → app navigates to Payment screen.

5. **Payment** → user picks GCash or Maya → `POST /api/payment/create/` → backend calls `services.payments.create_checkout()` → returns `checkout_url`. App opens URL in `url_launcher` (will add to pubspec) and registers a callback listener, OR (simpler MVP) — backend immediately flips a local button to "I've paid" that posts a stubbed `payment_webhook` payload to itself for demo. Mark this clearly in code as demo-only.

6. **Chat** → `GET /api/conversations/` → list. Tap → `GET /api/conversations/{id}/` + open WebSocket via `web_socket_channel` to `ws://host/ws/chat/{conversation_id}/`. Send → `POST /api/messages/send/`.

This is the full core loop. Disputes, KYC review, admin actions are secondary flows; they need to compile and navigate, but their submit/?review UX can be minimal.

## Components

### Backend (files to add/modify)

**Add:**
- `core/services/__init__.py`
- `core/services/payments.py` — `GcashProvider`, `MayaProvider`, factory `get_provider(name)`. HMAC verify helpers.
- `core/services/storage.py` — `presign_upload(filename, content_type) -> dict {url, fields, public_url}` using `boto3`. Falls back to returning a stub URL if R2 not configured (dev only).

**Modify:**
- `core/views.py` — finish TODOs at lines 1179, 1182, 1199. Add HMAC verification on webhook.
- `core/views.py` — implement `get_upload_url_view` to actually presign via the new storage service.
- `core/migrations/0004_*.py` — autogenerated to rename `transaction` → `trade` on `TradeCompletionAcknowledgment` and `InAppNotification`.

### Flutter (new files only, listed above)

Roughly 35 files. Most screens are <200 LOC because they're just `Scaffold` + Providers + the shared widgets.

## Error handling

- **HTTP errors** are caught at `api_client.dart` and converted to `Result<T>` with `Failure(code, message, cause)`. Default 401 triggers logout + clear storage + route to `/welcome`. Default 5xx surfaces a non-blocking `ErrorBanner` widget at the top of any screen.
- **OTP failures** show inline form errors (rate-limited, expired, wrong code).
- **Payment webhook** — failed signature returns 401 and **logs to security logger** (already wired in settings).
- **Network offline** — `api_client` exposes a typed `NetworkFailure`; screens that depend on data show an `EmptyState` with a retry button. No silent reties.

## Testing

- **Backend** — add `core/tests/` with at minimum:
  - `test_register_otp.py` (happy path + invalid OTP)
  - `test_trade_flow.py` (list → start → payment intent → webhook → active)
  - `test_kyc_review.py` (pending → approved → user.can_trade == true)
  - `test_honeypot.py` (returns 404, logs to security logger)
  - `test_payment_webhook_signature.py` (rejects bad signature)
  Use Django's `TestCase` + DRF's `APIClient`. No live Postgres required — SQLite for tests via a `DATABASES` override in test settings.

- **Flutter** — one widget test per screen proves it renders + one golden-ish smoke ("HomeScreen shows loading shimmer when listings are empty"). Don't aim high; the goal is "doesn't break on launch".

## Out of scope (explicit YAGNI)

- Push notifications (FCM init is wrapped in try/catch already, leave it).
- Real GCash/Maya API calls (stubs are honest about it).
- Real R2 upload wiring beyond presigned URL generation.
- Rating/review, appeals workflow, in-app currency conversion.
- Polish: animations beyond the existing `_SlideRoute`, iOS-icon, splash logo.
- Admin dashboard charts.

These belong in follow-up specs.

## Open questions / risks

- **`pubspec.yaml` may need `url_launcher`** added for opening payment checkout URL — confirm during implementation.
- **Flutter SDK version** in pubspec: `>=3.0.0 <4.0.0` is loose; actual installed version may differ. `flutter pub get` after the new files are written will surface any.
- **`.env` file is committed** — that's a security issue (real DB password etc.). Not fixing in this spec but should be flagged to user.
- **Firebase config** — `google-services.json` / `GoogleService-Info.plist` not present; app already handles missing Firebase gracefully.
