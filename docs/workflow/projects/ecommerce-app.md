# ClickBound (ecommerce-app)

## Overview

**ClickBound** - a full-stack e-commerce storefront: product catalog, JWT auth
with email/SMS OTP + TOTP 2FA, stock-aware cart, Stripe checkout with webhook
fulfillment, order history + invoice downloads, and a full admin panel. Heavy
security hardening focus (see audit below). Neon-synthwave glassmorphism UI.

**Path:** `C:\Users\DarkZhen\Documents\ecommerce-app` (git repo)

**Tech stack:** Next.js 16 (App Router, Turbopack, API-routes only - no server
actions), TypeScript strict, PostgreSQL + Prisma 6 (14 migrations), JWT +
bcryptjs, OTP/TOTP (RFC 6238, implemented from scratch), Stripe (test mode),
Nodemailer SMTP (Brevo) with mock mode, Tailwind 4 + Motion, Zod

## Status

**Active** - first commit 2026-08-12 (single `first commit`). Security audit
dated 2026-08-10, high-severity findings fixed and verified.

## Features

- **Auth:** register/login with bcrypt (cost 12), httpOnly JWT cookies,
  refresh-token rotation with replay detection, email + phone OTP verification,
  TOTP 2FA + 10 recovery codes, trusted-device bypass, account recovery,
  rate-limited login (10/5min, lockout after 5 fails), no account-existence leak
- **Catalog:** searchable product grid, categories, reviews (one per user),
  wishlist, flash sales (salePrice/saleEndsAt + countdown)
- **Commerce:** stock-aware cart, race-safe checkout (atomic conditional stock
  decrement in transaction), Stripe Checkout + webhook fulfillment, order
  history with OrderEvent timeline, printable admin invoices, cancel with
  Stripe refunds + stock restore, CSV exports + bulk ops
- **Admin:** products, categories, orders, reviews, users, wishlists CRUD;
  CSV export and bulk operations; dashboard with revenue/charts/best sellers
- **Contact & newsletter:** rate-limited signup, signed unsubscribe links,
  welcome email, contact form notifying admins
- **Security:** strict CSP with per-request nonces (`proxy.ts`), X-Frame-Options
  DENY, nosniff, mass-assignment protection, email change requires OTP proof,
  OTP brute-force lockout (5 attempts), per-client rate limits, JWT secrets
  validated at startup

## Data models (prisma/schema.prisma)

User (role CUSTOMER/ADMIN, lockout fields, totpSecret encrypted),
RefreshToken (hashed, 30d, rotation), RecoveryCode (10, hashed), OtpCode
(hash, 10min TTL, 5 attempts), Category, Product (price in cents, stock,
salePrice), Cart/CartItem, Order (status enum, Stripe intent id, tracking),
OrderEvent (timeline), OrderItem (price snapshot), Review (unique per
user+product), WishlistItem, Notification, NewsletterSubscriber,
ContactMessage.

## Workflow

### Local setup

1. Node 20+, PostgreSQL running (`.env.example` uses port 5433).
2. `npm install`
3. `Copy-Item .env.example .env` and fill `DATABASE_URL` + `JWT_SECRET`
   (required - template default crashes the app at startup).
4. `npx prisma migrate dev` (14 migrations already applied)
5. Seed: `npx prisma db seed` (prisma.seed = `node prisma/seed.ts`) - creates
   QA users `otp@clickbound.com` / `legacy@clickbound.com` and 10 products in
   4 categories (idempotent for products).
6. `npm run dev` -> http://localhost:3000

### Daily dev loop

- `npm run dev` - dev server (Turbopack).
- `npm run lint` - ESLint (Next config).
- `npm run build` && `npm start` - production (verified clean, 26 routes).
- DB inspection: `npx prisma studio`. Admin bootstrap: promote a user to ADMIN
  via the role column there.

### Payments & email (optional)

- Stripe: set `STRIPE_SECRET_KEY`; unset = dev mode (`sessionUrl: null`).
  Full flow: `stripe listen --forward-to localhost:3000/api/stripe/webhook`.
- Email: `SMTP_HOST/PORT/USER/PASS/FROM/SECURE` (Brevo `smtp-relay.brevo.com:587`,
  STARTTLS). Unset SMTP or `@clickbound.com` addresses = mock delivery (codes
  print to console/dev panel). Phone OTP is mock-only - no SMS provider wired.
- `TRUST_PROXY=1` only behind a trusted proxy (else single rate-limit bucket).

### Test

Manual (no test framework present): auth flows, OTP/TOTP/recovery, checkout
race (curl: one 201 + one 409), webhook (stripe CLI), admin CRUD, invoice.
Note in-memory rate limits/OTP cooldowns persist ~15 min after QA runs.

### Agent workflow (important)

`AGENTS.md` warns Next.js 16 is "not the Next.js you know" - read the guides in
`node_modules/next/dist/docs/` before writing code. Don't remove the AGENTS.md
block (`next dev` regenerates it). `CLAUDE.md` just imports it.

## Design history

8 specs in `docs/superpowers/specs/` (2026-08-08/09): OTP 2FA, email delivery
(channels seam), forgot-password + TOTP, auth redesign, profile contact info,
order tracking, glassify UI, admin data browser. Consult before touching those
areas.

## Known issues / notes

- In-memory rate limiter must be replaced with Redis/Upstash before
  multi-instance/serverless deploy.
- QA users remain in DB; test orders/events were cleaned up.
- Docs to read before working: `SECURITY_AUDIT.md`, `AGENTS.md`.
