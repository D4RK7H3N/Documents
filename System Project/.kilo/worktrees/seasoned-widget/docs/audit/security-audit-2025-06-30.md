# Security & Bug Audit Report — 2025-06-30

Audited the Django REST Framework backend (`school_pos/`) and React/Electron frontend (`frontend/`).

---

## AUTHENTICATION & AUTHORIZATION

### 1. [CRITICAL] No Role-Based Access Control

All 21 API ViewSets use only `IsAuthenticated` — no custom permissions, no `IsAdminUser`, no group/role checks anywhere.

- **File:** `api/views.py` — every ViewSet (StudentViewSet :221, SaleViewSet :1286, TuitionPaymentViewSet :1420, RevenueViewSet :2836, etc.)
- **Risk:** Any authenticated user — student, front-desk, or janitor — can access cashier, revenue, tuition, graduation, dormitory, and all other endpoints. The RevenueViewSet exposes `/api/revenue/` (total school revenue) to every logged-in user. TuitionPaymentViewSet's `create` lets any user modify tuition balances.

---

### 2. [CRITICAL] Static Token Auth — Tokens Never Expire

DRF `TokenAuthentication` uses persistent DB tokens with no expiry, no refresh, no rotation.

- **File:** `api/views.py:87-88` — `Token.objects.get_or_create(user=user)`
- **Risk:** If a token leaks (logged in console, captured in transit, XSS), it is valid indefinitely. The frontend stores it in `localStorage` (`api.js:33`) — accessible to any JS on the same origin.
- **Note:** The 401 interceptor (`api.js:51`) clears the token on client-side 401, but the backend never issues 401 based on token age.

---

### 3. [HIGH] `sale_receipt` View Has No Authentication

- **File:** `students/views.py:236` — `def sale_receipt(request, sale_id):`
- **Risk:** No `@login_required` decorator. Any unauthenticated user can view any sale receipt by enumerating `sale_id`. Exposes item names, prices, customer names, payment status.
- **Context:** The other 27 views in this file all have `@login_required` — this one was clearly missed.

---

### 4. [HIGH] Race Condition in Tuition Payment Flow

No `select_for_update()` on the student row inside the payment transaction. Two concurrent payments can both read the same `tuition_balance`, deduct, and write — double-spending the balance.

- **File:** `api/views.py:1501` — `TuitionPaymentViewSet.create()`
- **Also:** `students/views.py:148` (`tuition_payment`), `:441` (`edit_tuition_payment`), `:484` (`delete_tuition_payment`)
- **Example:** Two payments both read `balance=5000`, both deduct `5000`, both write `balance=0`. Student gains ₱5000, school loses ₱5000.

---

## CONFIGURATION & SECRETS

### 5. [HIGH] `DEBUG=True` by Default

- **File:** `settings.py:31` — `DEBUG = os.getenv("DEBUG", "True").lower() in ["true", "1", "yes"]`
- **Risk:** If the `DEBUG` env var is unset in production, DEBUG defaults to `True` — exposing stack traces, env variables, and source code snippets on errors.

---

### 6. [HIGH] Hardcoded Fallback `SECRET_KEY`

- **File:** `settings.py:26-28`
- **Risk:** The fallback `"django-insecure-^4oe2d!..."` is a known Django-generated dev key committed to GitLab. If `SECRET_KEY` env var is missing in production, an attacker can forge session cookies, CSRF tokens, and signed data.

---

### 7. [HIGH] Hardcoded Fallback Database Password

- **File:** `settings.py:213` — `"PASSWORD": os.getenv("DB_PASSWORD", "darkzhen")`
- **Risk:** The password `"darkzhen"` is in plain text in the codebase (committed to GitLab). Anyone with repo access knows it. If the env var is missing in production, the DB is wide open.

---

### 8. [HIGH] Clickjacking Protection Disabled

- **File:** `settings.py:342` — `X_FRAME_OPTIONS = "ALLOWALL"`
- **Risk:** Site can be embedded in `<iframe>` on any external domain. Attackers can overlay invisible iframes to trick clicks (clickjacking).

---

### 9. [HIGH] No Content Security Policy

- **File:** `settings.py:341` — `SECURE_CONTENT_SECURITY_POLICY = False`
- **Risk:** No defense against XSS via inline scripts. No restriction on external resource loading.

---

## DATA EXPOSURE

### 10. [HIGH] StudentDetailSerializer Exposes Sensitive Personal Data

- **File:** `api/serializers.py:563-586`
- **Exposed to any authenticated user via `GET /api/students/{id}/`:**
  - `photo`, `medical_conditions`, `blood_type`, `immunization_records`
  - `preferred_hospital`, `health_insurance`
  - `guardian_name`, `guardian_phone`, `guardian_address`, `guardian_occupation`, `guardian_relationship`
  - `emergency_contact_name`, `emergency_contact_number`, `emergency_contact_relationship`
  - `form_137_submitted`, `psa_submitted`, `good_moral_submitted`, `report_card_submitted`, `photos_submitted`
  - `academic_records`, `extracurricular`, `notes`
- **Risk:** No field-level permissions. Any user can view any student's medical history, family contacts, and document status.

---

### 11. [MEDIUM] Tuition Records Visible to All Authenticated Users

- **File:** `api/serializers.py:937-952` — `GET /api/tuition-payments/records/`
- **Risk:** Any authenticated user can see which students paid, how much, and their outstanding balances.

---

## INPUT HANDLING & INJECTION

### 12. [MEDIUM] No File Content-Type Validation on Uploads

- **File:** `api/views.py:327` (upload_document), `students/views.py:506` (upload_students)
- **Risk:** Only file extension is checked via `FileExtensionValidator`. A `.pdf` file could contain executable code. Excel `.xlsx` files could carry XXE payloads. No magic-byte verification.

---

### 13. [MEDIUM] `test_upload` Debug Endpoint Exposes File Structure

- **File:** `api/views.py:971`
- **Risk:** Accepts any Excel file and returns sheet names, column headers, and first data row. Could be used to probe upload structure or leak data from templates.

---

## GENERAL BUGS

### 14. [MEDIUM] REST API Enrollment Doesn't Set Initial Tuition

- **File:** `api/views.py` — `StudentViewSet`
- **Risk:** `StudentSerializer.create()` only processes strand/section/course — it never sets `tuition_balance` or `custom_tuition_fee`. Students created via API always have `balance=0`. But `students/views.py:260` (`enroll_student`) has detailed tuition logic (New=₱0, Continuing=SHS=₱11K/BUN=₱16K, Transferee=70%). Two enrollment paths with inconsistent behavior.

---

### 15. [MEDIUM] SessionAuth + TokenAuth Both Enabled

- **File:** `settings.py:270-273`
- **Risk:** If a user logs into Django admin, their session can be used to call API endpoints with full privileges. CSRF becomes relevant for API calls.

---

### 16. [MEDIUM] Wide `ALLOWED_HOSTS` — Wildcard Subdomains

- **File:** `settings.py:50-51` — `".ngrok-free.dev"`, `".railway.app"`
- **Risk:** Any ngrok/railway subdomain can serve requests with session cookies attached. An attacker pointing a subdomain to your server would be accepted.

---

### 17. [LOW] N+1 Query in `records` Endpoint

- **File:** `api/views.py:1441`
- **Risk:** Performance — per-student queries for payment aggregation. No `prefetch_related`.

---

### 18. [LOW] Low Throttle Limit (100/hr) May Lock Out Admins

- **File:** `settings.py:283` — `"user": "100/hour"`
- **Risk:** ~1 request per 36 seconds. A page loading multiple records can exhaust the limit, locking the user out for the rest of the hour.

---

## Summary

| # | Severity | Category | Finding | File:Line |
|---|----------|----------|---------|-----------|
| 1 | CRITICAL | Auth | No role-based access control | `api/views.py` (all) |
| 2 | CRITICAL | Auth | Static tokens never expire, stored in localStorage | `api/views.py:88`, `api.js:33` |
| 3 | HIGH | Auth | `sale_receipt` view has no auth decorator | `students/views.py:236` |
| 4 | HIGH | Bug | Race condition in tuition payment — no `select_for_update()` | `api/views.py:1501` |
| 5 | HIGH | Config | `DEBUG=True` by default | `settings.py:31` |
| 6 | HIGH | Secrets | Hardcoded fallback `SECRET_KEY` | `settings.py:27` |
| 7 | HIGH | Secrets | Hardcoded fallback DB password | `settings.py:213` |
| 8 | HIGH | Config | Clickjacking disabled (`ALLOWALL`) | `settings.py:342` |
| 9 | HIGH | Config | No CSP headers | `settings.py:341` |
| 10 | HIGH | Data | StudentDetailSerializer exposes medical/family data | `serializers.py:563` |
| 11 | MEDIUM | Data | Tuition records visible to all users | `serializers.py:952` |
| 12 | MEDIUM | Input | No file content-type validation | `api/views.py:327` |
| 13 | MEDIUM | Input | `test_upload` endpoint leaks file structure | `api/views.py:971` |
| 14 | MEDIUM | Bug | REST API enrollment doesn't set initial tuition | `api/views.py` |
| 15 | MEDIUM | Config | SessionAuth + TokenAuth both enabled | `settings.py:270-273` |
| 16 | MEDIUM | Config | Wildcard subdomains in ALLOWED_HOSTS | `settings.py:50-51` |
| 17 | LOW | Bug | N+1 query in `records` endpoint | `api/views.py:1441` |
| 18 | LOW | Config | Low throttle limit (100/hr) | `settings.py:283` |
