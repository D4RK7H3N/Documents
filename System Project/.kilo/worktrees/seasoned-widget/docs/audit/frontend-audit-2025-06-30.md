# Frontend Security & Bug Audit Report — 2025-06-30

Audited React (Vite) frontend at `frontend/src/` (24 pages, 12 components) and Electron main process (`frontend/electron/`).

---

## TOKEN & AUTH HANDLING

### 1. [HIGH] Auth Token Stored in `localStorage` with No HttpOnly Protection

- **Files:**
  - `LoginPage.jsx:25` — `localStorage.setItem('authToken', data.token)`
  - `api.js:7-14` — `storage.get/set/remove` wraps `localStorage` calls
  - `AuthContext.jsx:24,45,88,111` — multiple reads/writes
  - `SchoolConfigContext.jsx:28,56` — reads token from localStorage
- **Risk:** `localStorage` is accessible to any JavaScript running on the same origin. If an XSS vulnerability exists anywhere in the frontend, an attacker can steal the token directly. Unlike `HttpOnly` cookies, there is no way to mark `localStorage` data as inaccessible to JavaScript.
- **Note:** This is a standard trade-off for SPAs using token auth, but worth noting since there's no CSRF protection for the token (it's sent in an `Authorization` header, not a cookie).

---

### 2. [MEDIUM] Token Has No Expiry — Valid Until Manual Logout or Deletion

- **File:** `api.js:31-39` — request interceptor attaches token to every request
- **Risk:** The token is stored in `localStorage` and used until explicitly removed. There is no token expiry check on the frontend. The `AuthContext.checkAuth()` (`AuthContext.jsx:23`) validates the token by calling `authAPI.getProfile()` on mount, but if the backend token is leaked, it works indefinitely.

---

### 3. [MEDIUM] Inconsistent Logout — `localStorage.clear()` Destroys Everything

- **File:** `AuthContext.jsx:111` — `localStorage.clear()`
- **Risk:** `localStorage.clear()` removes ALL keys, including `schoolConfig` (cached school configuration), `notificationSettings`, `cashierReceiptCounter`, and any other non-auth data stored by the app. This can cause data loss (e.g., receipt counter resets to 1). A targeted removal (`removeItem('authToken')` and `removeItem('user')`) would be safer.

---

### 4. [MEDIUM] Fallback to Stale Cached User on API Failure

- **File:** `AuthContext.jsx:46-63` — If `getProfile()` fails but `localStorage` has a cached user, auth is considered valid
- **Risk:** If the backend token is revoked or the user's permissions change, the stale cached user allows continued access until `localStorage` is cleared. The frontend would show the user as authenticated even though their token is invalid — they'd get 401 errors on every API call but not be redirected to login.

---

## ELECTRON-SPECIFIC RISKS

### 5. [GOOD] Electron Security — Properly Configured

- **File:** `electron/main.js:161-167`
- **Settings:** `contextIsolation: true`, `nodeIntegration: false`, `webSecurity: true`
- **Preload:** `electron/preload.js` uses `contextBridge.exposeInMainWorld` — only exposes `platform`, `versions`, `openExternal`, `minimize`, `maximize`, `close`, `getAppVersion`
- **Navigation guard:** `main.js:201-209` blocks all navigation except `localhost:5173` and `file://`
- **Window open handler:** `main.js:211-216` — denies all new window creation, opens URLs in external browser
- **Assessment:** Electron security is **well-configured**. No remote module usage, no sandbox disable, no `nodeIntegration` in any window. Splash window is also properly isolated (`main.js:129-131`).

### 6. [LOW] DevTools Accessible via F12 / Ctrl+Shift+I in Production

- **File:** `electron/main.js:218-226` — `before-input-event` handler toggles DevTools on F12/Ctrl+Shift+I even in production builds
- **Risk:** In a deployed Electron app, a user could open DevTools and inspect network requests, view stored `localStorage` tokens, and examine source code. While this is expected for a local desktop app, it does mean users can trivially view API tokens and backend URL structure.
- **Mitigation:** Since this is a local school management app (not a public SaaS), the risk is low — an attacker with local access already has significant privileges.

---

## INPUT & RENDERING

### 7. [GOOD] No XSS via `dangerouslySetInnerHTML`

- **Result:** Zero matches across all 36 scanned files.
- **Assessment:** All user data is rendered through React's JSX expression syntax (`{student.name}`), which auto-escapes HTML. This is the correct approach.

### 8. [GOOD] No `eval()`, `Function()`, or String `setTimeout`/`setInterval`

- **Result:** Zero matches across all 36 scanned files.

---

## API & NETWORK

### 9. [GOOD] No Hardcoded API Keys, Credentials, or Production URLs

- **Result:** Zero matches. All API calls go through `api.js` which reads `VITE_API_URL` from `.env` (`api.js:3`). The only fallback is `'http://localhost:8000'` for local development.

---

## ERROR HANDLING — Backend Error Details Leaked to UI

### 10. [HIGH] `EnrollmentForm.jsx:117` — Entire Backend Response Object Leaked

- **File:** `components/EnrollmentForm.jsx:117` — `setError(err?.response?.data || 'Save failed')`
- **Risk:** Passes the **entire backend response body** to the UI state. If the backend returns a verbose error with stack traces, field-level validation errors, or internal data, all of it is displayed directly to the user. This is the most severe instance of this pattern.

### 11. [MEDIUM] 23 Additional Locations Leak Raw Backend Error Messages

- **Summary:** Across 14 other files, raw `error.response?.data?.error`, `error.response?.data?.detail`, and field-level errors (e.g., `err?.response?.data?.lrn?.[0]`) are passed directly to `showToast()` or `setError()` state.

| File | Line | Pattern |
|------|------|---------|
| `AssessmentsPage.jsx` | 287 | `setErrors({ submit: error.response?.data?.error \|\| error.response?.data?.detail ... })` |
| `AssessmentsPage.jsx` | 315 | `setErrors({ submit: error.response?.data?.error \|\| error.response?.data?.detail ... })` |
| `CashierPage.jsx` | 323-327 | `showToast(err?.response?.data?.error \|\| err?.response?.data?.detail ...)` |
| `DormPage.jsx` | 209 | `setBuildingError(err?.response?.data?.error \|\| err?.response?.data?.name?.[0] ...)` |
| `DormPage.jsx` | 287 | `setRoomError(err?.response?.data?.error \|\| err?.response?.data?.room_number?.[0] ...)` |
| `DormPage.jsx` | 335 | `setAssignError(err?.response?.data?.error \|\| err?.response?.data?.student?.[0] ...)` |
| `DropoutsPage.jsx` | 221 | `setFormError(err?.response?.data?.error \|\| ...)` |
| `EnrollPage.jsx` | 146 | `setFormError(err?.response?.data?.error \|\| err?.response?.data?.detail ...)` |
| `EnrollPage.jsx` | 191-192 | `msg = err?.response?.data?.lrn?.[0] \|\| err?.response?.data?.error ...` |
| `GraduationPage.jsx` | 135 | `setEventError(err?.response?.data?.error \|\| err?.response?.data?.name?.[0] ...)` |
| `LoginPage.jsx` | 62-65 | `setError(err.response?.data?.error \|\| err.response?.data?.detail ...)` |
| `PendingPaymentsPage.jsx` | 233 | `setPaymentError(err?.response?.data?.error \|\| ...)` |
| `ProfilePage.jsx` | 71 | `message: error?.response?.data?.detail \|\| error.message ...` |
| `PromotionPage.jsx` | 43 | `showToast(err.response?.data?.error \|\| 'Promotion failed', 'error')` |
| `SchoolConfigPage.jsx` | 115-120 | `showToast(error?.response?.data?.detail \|\| error?.response?.data?.error ...)` |
| `StudentsPage.jsx` | 241 | `msg = err?.response?.data?.lrn?.[0] \|\| err?.response?.data?.error ...` |
| `StudentsPage.jsx` | 304 | `showToast(err?.response?.data?.error \|\| ...)` |
| `ToursPage.jsx` | 412 | `setTourError(err?.response?.data?.error \|\| err?.response?.data?.name?.[0] ...)` |
| `TuitionPage.jsx` | 269 | `setFormError(err?.response?.data?.error \|\| err?.response?.data?.detail ...)` |
| `TuitionPage.jsx` | 373 | `showToast(err.response?.data?.detail \|\| ...)` |
| `StudentPaymentModal.jsx` | 61 | `setError(err?.response?.data?.error \|\| err?.response?.data?.detail ...)` |
| `SettingsPage.jsx` | 92 | `JSON.parse(localStorage.getItem('schoolConfig')` — error not caught if malformed |

- **Risk:** Backend Django REST Framework validation errors often include internal field names (e.g., `lrn`, `custom_tuition_fee`), model structure hints, and sometimes full stack traces in DEBUG mode. Displaying these directly to users leaks implementation details that aid attackers.

---

## GENERAL BUGS

### 12. [HIGH] 33 Async Handlers Missing Re-Entrancy Guards (Double-Submit)

- **Finding:** Every async handler that sets a `saving`/`processing`/`deleting`/`promoting` state does so WITHOUT first checking whether the operation is already in progress. The standard guard pattern `if (loading) return` is absent everywhere.
- **Files affected:** 14 files, 33 handlers
- **Examples:**

| File | Handler | Line | Guard? |
|------|---------|------|--------|
| `CashierPage.jsx` | `handleSubmitPayment` | 211 | Sets `setProcessing(true)` at 213, no guard |
| `TuitionPage.jsx` | `handleSettleBalance` | 308 | Sets `setSaving(true)` at 310, no guard |
| `TuitionPage.jsx` | `handlePromoteStudent` | 349 | Sets `setPromoting(true)` at 364, no guard |
| `EnrollPage.jsx` | `handleEnrollExisting` | 117 | Sets `setSaving(true)` at 119, no guard |
| `EnrollPage.jsx` | `handleEnrollNew` | 152 | Sets `setSaving(true)` at 159, no guard |
| `StudentsPage.jsx` | `handleSaveAddEdit` | 221 | Sets `setSaving(true)` at 224, no guard |
| `DormPage.jsx` | `handleSaveBuilding` | 178 | Sets `setSavingBuilding(true)` at 189, no guard |
| `DropoutsPage.jsx` | `handleSaveDropout` | 198 | Sets `setSaving(true)` at 200, no guard |
| `AssessmentsPage.jsx` | `handleSubmit` | 240 | Sets `setSubmitting(true)` at 244, no guard |
| `GraduationPage.jsx` | `handleSaveEvent` | 95 | Sets `setSavingEvent(true)` at 109, no guard |
| `ToursPage.jsx` | `handleSaveTour` | 364 | Sets `setSavingTour(true)` at 373, no guard |
| `SectionsPage.jsx` | `handleSave` | 59 | No loading state at all |
| `TracksPage.jsx` | `handleSave` | 60 | No loading state at all |
| `CoursesPage.jsx` | `handleSave` | 70 | No loading state at all |
| `AssessmentsPage.jsx` | `handleDelete` | 322 | No loading state at all |
| *(+ 19 more across all listed files)* | | | |

- **Risk:** If a user double-clicks a button, presses Enter twice, or React re-renders before the state update propagates, the handler runs twice concurrently. For payment handlers (`handleSubmitPayment`, `handleSettleBalance`), this could result in:
  - Duplicate payment records
  - Tuition balance deducted twice (with `select_for_update()` missing on the backend)
  - Duplicate student enrollment records
  - Multiple toast notifications

### 13. [MEDIUM] Stale Closure in `CashierPage.generateReceiptNo()` — Reads Stale `receiptCounter` State

- **File:** `CashierPage.jsx:35-39`
  ```js
  const generateReceiptNo = () => {
    const year = new Date().getFullYear()
    const num = String(receiptCounter).padStart(5, '0')
    return `OR-${year}-${num}`
  }
  ```
- **Risk:** `generateReceiptNo` is a regular function that closes over the `receiptCounter` state value from the render cycle it was defined in. If called inside an async handler after state has updated (e.g., via a second invocation), it could read a stale counter value. Two concurrent payments could receive the same receipt number.
- **Note:** The counter is incremented at line 340 (`setReceiptCounter(next)` and `localStorage.setItem(...)`) but `generateReceiptNo` uses the closure value, not a ref.

### 14. [MEDIUM] Stale State Closures in Critical Payment Handlers

- **Files and handlers that close over state without `useRef`:**

| File | Handler | Stale variable(s) | Risk |
|------|---------|-------------------|------|
| `CashierPage.jsx:211` | `handleSubmitPayment` | `paymentData`, `paymentType`, `isCashPayment`, `receiptCounter` | Double-submit reads stale `paymentData` |
| `TuitionPage.jsx:308` | `handleSettleBalance` | `soaRecord` | SOA record may change between renders |
| `EnrollPage.jsx:117` | `handleEnrollExisting` | `enrollForm`, `selectedStudent` | Form data stale on re-entry |
| `EnrollPage.jsx:152` | `handleEnrollNew` | `newStudentForm`, `enrollForm` | Form data stale on re-entry |
| `PendingPaymentsPage.jsx:204` | `handleSubmitPayment` | `paymentForm`, `selectedPayment` | Payment data stale on re-entry |

### 15. [LOW] `SettingsPage.jsx:92` — Unsafe `JSON.parse` Without Try/Catch

- **File:** `SettingsPage.jsx:92` — `JSON.parse(localStorage.getItem('schoolConfig') || '{}')`
- **Risk:** Unlike `AuthContext.jsx` and `api.js` which wrap `localStorage` access in try/catch, this `JSON.parse` is unprotected. If the stored `schoolConfig` value is malformed (e.g., corrupted by `localStorage.clear()` partial write), this throws an uncaught exception that crashes the page.

### 16. [LOW] Direct DOM Manipulation for CSV Downloads (9 Files)

- **Files:** `DormPage.jsx:397`, `DropoutsPage.jsx:279`, `PaymentsPage.jsx:84`, `PendingPaymentsPage.jsx:259`, `RevenuePage.jsx:265`, `SettingsPage.jsx:96`, `StudentsPage.jsx:335`, `ToursPage.jsx:449`, `TuitionPage.jsx:394`
- **Pattern:** `document.createElement('a')`, `a.click()`, `URL.createObjectURL()` / `URL.revokeObjectURL()`
- **Risk:** Bypasses React's rendering pipeline. Minor risk — these are ephemeral download triggers, not persistent DOM mutations. The pattern is functionally correct, just non-idiomatic.

---

## Summary Table

| # | Severity | Category | Finding | File(s) |
|---|----------|----------|---------|---------|
| 1 | HIGH | Token | Auth token in `localStorage` — accessible to JS (XSS) | `LoginPage.jsx:25`, `api.js:7` |
| 2 | MEDIUM | Token | No frontend token expiry check | `AuthContext.jsx:23` |
| 3 | MEDIUM | Token | `localStorage.clear()` on logout destroys all app data | `AuthContext.jsx:111` |
| 4 | MEDIUM | Token | Stale cached user used when API fails | `AuthContext.jsx:46-63` |
| 5 | **GOOD** | Electron | Electron security is properly configured | `electron/main.js:161-167` |
| 6 | LOW | Electron | DevTools accessible via F12 in production | `electron/main.js:218-226` |
| 7 | **GOOD** | XSS | No `dangerouslySetInnerHTML` anywhere | *(all files)* |
| 8 | **GOOD** | Injection | No `eval()` or string `setTimeout` | *(all files)* |
| 9 | **GOOD** | Secrets | No hardcoded credentials or production URLs | *(all files)* |
| 10 | HIGH | Errors | `EnrollmentForm.jsx` leaks entire backend response object | `EnrollmentForm.jsx:117` |
| 11 | MEDIUM | Errors | 23 locations leak raw backend error details to UI | *(14 files, see section 11)* |
| 12 | HIGH | Bugs | 33 async handlers missing re-entrancy guards (double-submit) | *(14 files, see section 12)* |
| 13 | MEDIUM | Bugs | Stale closure in `generateReceiptNo()` — duplicate receipt # risk | `CashierPage.jsx:35-39` |
| 14 | MEDIUM | Bugs | Stale state closures in 5 payment/enrollment handlers | `CashierPage.jsx`, `TuitionPage.jsx`, etc. |
| 15 | LOW | Bugs | `SettingsPage.jsx:92` — unsafe `JSON.parse` without try/catch | `SettingsPage.jsx:92` |
| 16 | LOW | Bugs | Direct DOM manipulation for CSV downloads (9 files) | *(9 files)* |
