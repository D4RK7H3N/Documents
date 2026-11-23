# Auth Page Redesign (Login / Sign Up)

Date: 2026-08-09
Status: Approved by user (sections 1-3); implementation in progress

## Objective

Replace the single-card login/register toggle on `/login` with a split-screen auth page that matches the neon-synthwave aesthetic, adds inline validation, sign-up extras, and better error handling.

## Layout (section 1 — approved)

- **Left brand panel** (`hidden lg:flex`, full height): "Clickbound" wordmark, tagline, animated ambience blobs + grid overlay, category chips (from DB), stat strip (product count / category count). No interaction.
- **Right panel**: form card (`glass-panel`, glow accent, rounded-2xl, `max-w-md`).
- **Mobile**: panel hidden; card fills viewport over ambient background.

## Form behavior (section 2 — approved, demo accounts dropped by user)

- Segmented LOG IN / SIGN UP tabs; switching clears inline errors, keeps email.
- Login: email + password with show/hide toggle.
- Sign up: Name, Email, Phone (optional), Password with live 4-segment strength bar (rose→amber→lime→cyan; length/mixed-case/digit/symbol), Confirm password, Terms checkbox gating submit.
- Inline validation on blur (email format; password ≥ 8; confirm match; phone loose format 8-20 chars; terms checked). Rose error text + rose border per field, cleared when fixed.
- Server errors in a red glass banner above submit (uses existing `formErrors` shape). Success → toast + redirect `/`.

## Data & API (section 3 — approved)

- `POST /api/auth/register`: add optional `phone` (trimmed, max 30) to zod schema, persist on User. `User.phone` already exists in schema (no migration).
- No demo accounts; no changes to login API or seed.
- `app/login/page.tsx` (server): fetch categories + product count, pass to client form. Redirect logged-in users (unchanged).

## Files

- `components/LoginForm.tsx` (rewrite; self-contained with validation/strength helpers)
- `app/api/auth/register/route.ts` (phone)
- `app/login/page.tsx` (brand data props)
- `app/globals.css` (auth utility classes)

## Verification

- tsc + eslint clean
- Headless browser: guest render, inline error cases, tabs, mobile panel hidden, register → redirect, login → redirect, clean console
