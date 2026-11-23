# Release v1.1.0 — Security, Promotion & Bug Fixes

## Security Fixes

- **Row locking for tuition balance** — All four tuition balance read-and-update sites now use `transaction.atomic()` with `select_for_update()`, preventing double-deduction race conditions when concurrent payment requests arrive.
- **Frontend re-entrancy guards** — All 33 async handlers across 15 pages now check a loading flag at entry and return early if already in progress, preventing double-submit on payment, enrollment, and save buttons.
- **`@login_required` on `sale_receipt`** — The only missing auth decorator in `students/views.py` is now added. All 28 views in the file require authentication.

## Features

- **Promotion Management** — New `/promotion` page with stat cards, per-group promotion previews, and "Promote All" buttons for SHS Grade 11→12, Grade 12→Graduate, Bundled Year 1→2, Year 2→Graduate.
- **SOA Promote Button** — Statement of Account modal now has a "Promote & Update Tuition" / "Mark Graduated" button that auto-adds tuition (₱11K / ₱16K) for payee students on grade change.
- **Seed Data Command** — `seed_sample_students` management command creates 15 students with varied tuition states, auto-creating tracks/strands.

## Bug Fixes

### Backend
- `custom_tuition_fee` is now used consistently across all endpoints (was silently saving to nonexistent `tuition_fee` field — tuition data was lost).
- `records` endpoint: wraps optional `Student` fields with `getattr()`, removes references to nonexistent `.grade` and `.tuition_fee` fields, falls back to `tuition_balance + amount_paid` when `custom_tuition_fee` is zero.
- `SECURE_SSL_REDIRECT` hardcoded to `False` — Railway's SSL edge proxy handles this; the env var was incorrectly overriding to `True`.
- Migration 0004 conditionally adds the `reference_number` column for existing deployments.
- Cashier student search now uses the backend `?search=` param instead of client-side filtering, so students beyond page 1 are found.

### Frontend
- `ITEMS_PER_PAGE` increased from 10 to 20 on TuitionPage and StudentsPage.
- `gradeLevels` corrected to `['Grade 11', 'Grade 12', 'College 1st Year', 'College 2nd Year']`.
- Receipt print CSS: `position: absolute` → `position: fixed` so print layout doesn't break.
- `generateReceiptNo` reads `receiptCounter` directly (avoids stale closure risk).

## Deployment

- **Railway (Railpack 0.30+):** Migrated from Dockerfile to `"provider": "python"` with `start.sh` (gunicorn). Old `railway.json` `"builder"` field is ignored by Railpack 0.30.
- **CORS:** `*.up.railway.app` added to `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` for Railway frontend deployment.

---

**Full changelog:** `git log v1.0.0..HEAD`
