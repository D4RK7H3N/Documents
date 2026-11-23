# Editable Profiles Design

**Date:** 2026-11-20
**Status:** Approved in conversation (backend and UX sections), pending written spec review
**Scope:** Self-service editable profiles for teachers/admins (React web) and students (Flutter mobile), backed by one shared Django REST API.

## Overview

Today there is no personal profile page for teachers/admins on the web — only the forced password-change screen — and the student mobile profile is view-only. This feature adds a shared self-service profile API and profile UI on both platforms, using the powder-blue design system from `2026-11-19-professional-ui-refresh-design.md`.

Selected approach: **one shared `/me/` API** (PATCH for details, multipart avatar endpoint) reused by both platforms. Split staff/student APIs and local-only profiles were considered and rejected (duplication; no cross-device persistence).

## Goals

- Teachers/admins edit first/last name, email, phone, and profile photo on the web.
- Students edit email, phone, and profile photo on mobile; their display name stays school-managed.
- All roles see their profile photo and details reflected immediately after saving and across devices.

## Non-goals

- Changing usernames/LRNs, roles, sections, or passwords through profile endpoints (password change keeps its existing endpoint and screens).
- Admin management of other users' profiles (existing admin user screens are unchanged).
- Student name editing by students themselves (official records stay school-managed).

## Data model

`accounts.User` gains two fields; one migration:

| Field | Type | Notes |
|---|---|---|
| `phone` | `CharField(max_length=32, blank=True, default="")` | Optional, free-form contact number |
| `avatar` | `FileField(upload_to=...)` | Stored under `media/avatars/` with randomized (UUID) filenames to prevent collisions and enumeration |

`first_name`, `last_name`, and `email` reuse existing `AbstractUser` fields. The existing read-only `display_name` property (student profile name for students, `"last_name, first_name"` for staff) remains the display source everywhere.

**Dependency:** Pillow is added to backend requirements for real image decoding/verification.

## API contract

All endpoints require authentication (any role) and never accept `username`, `role`, or password fields.

### `GET /api/v1/me/` (extended response)

Existing fields (`id`, `username`, `role`, `must_change_password`, `name`, `display_name`) plus:

```json
{
  "email": "",
  "phone": "",
  "first_name": "",
  "last_name": "",
  "avatar_url": null
}
```

`avatar_url` is the media URL or `null`. For students, `first_name`/`last_name` are informational only (empty unless set by staff).

### `PATCH /api/v1/me/` (JSON)

- Staff (teacher/admin): `first_name`, `last_name`, `email`, `phone`.
- Students: `email`, `phone` only; a request containing `first_name` or `last_name` returns **400** with a clear "names are managed by the school" error.
- Partial updates; omitted fields unchanged. Empty strings clear optional fields. `email` must be a valid email address when non-empty. `phone` max 32 chars.
- Response: the full extended `/me/` representation.

### `POST /api/v1/me/avatar/` (multipart)

- Form field: `avatar`.
- Allowed extensions: `.png`, `.jpg`, `.jpeg`, `.webp` (no SVG for avatars). Max **2 MiB**.
- The file is verified by decoding with Pillow, not just extension/MIME inspection; invalid or corrupt images return **400**.
- On success the previous avatar file is deleted and the response is `{"avatar_url": "..."}`.

### `DELETE /api/v1/me/avatar/`

- Removes the avatar and deletes the stored file; returns `{"avatar_url": null}`.

### Audit logging

Each successful change calls `record_audit`:

- Details: `action="profile.update"`, `entity="user"`, `entity_id=<id>`, `old_values`/`new_values` containing only the changed fields.
- Avatar: `action="profile.avatar"`, old/new values contain the storage path only (never binary data).

### Media serving

Avatars use the existing `MEDIA_URL`/`MEDIA_ROOT` setup: Django static helper in DEBUG, nginx `/media/` proxy in production (`deploy/nginx.conf`). No new infrastructure.

## Web experience (teachers/admins)

- New route `/profile` available to all authenticated web roles; added to `App.jsx` inside the protected layout.
- The header user chip and the mobile drawer's user section link to `/profile`.
- Page sections using the refreshed design system (`Card`, `SectionCard`, `Btn`, `inputClass`):
  1. **Account card** — avatar (photo or initials fallback), username and role read-only, upload/remove photo buttons with local preview and client-side type/size checks.
  2. **Personal details** — first/last name (staff), email, phone; save button with pending state and inline error banner on failure.
  3. **Security** — short explanation and a link/button to the existing change-password screen.
- Upload uses `fetch` + `FormData` with the stored bearer token, following the existing `Settings.jsx` logo-upload pattern (the shared `api()` helper stays JSON-only).
- After any save, `refreshUser()` from `AuthContext` updates the header name/avatar without a page reload.
- Layout is responsive: single column on phones, 44px minimum touch targets, visible focus states.

## Mobile experience (students)

- `ProfileScreen` shows the uploaded photo in the avatar (`Image.network` with the existing person-icon fallback), keeps name/LRN/role read-only, and adds an **Edit profile** action.
- A dedicated **Edit profile screen** (pushed route, not a bottom sheet): email and phone fields with validation, plus photo pick/upload/remove using the device photo picker (`image_picker` package; no extra Android permissions needed for the photo picker).
- `ApiClient` gains a multipart upload helper using `dart:io` with the bearer token and JSON content-type only for JSON calls (the existing 415 fix is preserved).
- `AppUser` gains `email`, `phone`, `avatarUrl`; `AppState` persists updated user JSON through `TokenStorage` so edits survive restarts. Bootstrap still restores the cached user; no forced refetch behavior change.
- Success/error feedback uses the existing snackbar pattern; network failures leave local state unchanged.

## Security and permissions

- All endpoints are authenticated; users can only ever modify their own record.
- Students cannot change names via the API (enforced server-side, not just hidden in UI).
- Avatar validation: extension allowlist + 2 MiB cap + Pillow decode verification; randomized filenames; old files deleted on replacement/removal.
- No credentials, tokens, or password material is included in audit entries or API responses.

## Testing

- **Backend:** API tests for PATCH success per role, student name-change rejection, invalid email, avatar type/size rejection, successful upload/replace/remove, audit entries written.
- **Web:** production build; browser verification of the profile page at desktop (1440px) and phone (390px) widths, including upload preview, save, and header refresh.
- **Mobile:** `flutter analyze lib` clean; debug build installed on the connected Android device; profile view/edit exercised against the local backend.
- The paused UI-refresh browser/device validation resumes after this feature is implemented.

## Out of scope (pre-existing, unchanged)

The previously documented functional defects stay out of this feature: missing `/admin/class-records` route, admin My Classes 403, and the misleading inherited permission message.
