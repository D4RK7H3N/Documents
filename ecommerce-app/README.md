# ClickBound

A full-stack e-commerce storefront: product catalog, JWT auth with TOTP, cart, Stripe checkout, order history, and an admin panel. Built with Next.js 16 (App Router) + TypeScript, Prisma + Postgres, and hardened with a focus on security.

## Features

- **Auth** — register/login with bcrypt-hashed passwords, httpOnly JWT cookies, refresh-token rotation with reuse detection, email + SMS OTP verification, TOTP 2FA, account recovery, rate-limited login/register
- **Catalog** — searchable product grid, categories, reviews, wishlists, sale pricing
- **Commerce** — stock-aware cart, race-safe checkout (conditional stock reservation), Stripe checkout + webhook fulfillment, order history + invoice downloads
- **Admin** — products, categories, orders, reviews, users, wishlists; CSV export and bulk operations
- **Contact & newsletter** — contact form, rate-limited newsletter signup with signed unsubscribe links
- **Responsive UI** — Tailwind 4 + Motion

## Tech stack

| Layer | Tech |
|---|---|
| Framework | Next.js 16 (App Router, Turbopack, Server Actions-free API routes) |
| Language | TypeScript (strict) |
| Database | PostgreSQL + Prisma 6 |
| Auth | JWT (jsonwebtoken) + bcryptjs + OTP/TOTP (speakeasy-style via otplib pattern) |
| Payments | Stripe (test mode) |
| Email | Nodemailer (SMTP — Brevo/Gmail), mock mode for dev |
| UI | Tailwind CSS 4, Motion |

## Security highlights

- Refresh-token rotation + replay detection (reuse revokes all sessions)
- Email change requires OTP proof; mass-assignment protected (role cannot be set via API)
- Checkout oversell race eliminated (atomic conditional stock decrement)
- Per-client rate limits on login, register, OTP send, newsletter
- Strict Content-Security-Policy with per-request nonces (`proxy.ts`), X-Frame-Options DENY, nosniff
- JWT secrets validated at runtime (alg/exp/weak-secret checks), admin routes enforced

Full audit log: [`SECURITY_AUDIT.md`](./SECURITY_AUDIT.md)

## Run locally

Requirements: Node 20+, PostgreSQL (local, or Neon/Supabase free tier).

```bash
npm install
cp .env.example .env    # set DATABASE_URL, JWT_SECRET, Stripe keys (optional)
npx prisma migrate dev  # create schema
npm run dev             # http://localhost:3000
```

Email: with `SMTP_*` unset, OTP codes and newsletter links print to the dev console and appear in the login/account dev panels. Addresses ending in `@clickbound.com` always use mock delivery.

Stripe checkout: without `STRIPE_SECRET_KEY` the checkout API completes orders in dev mode (`sessionUrl: null`). For full flows, add test keys from the Stripe dashboard and run `stripe listen --forward-to localhost:3000/api/stripe/webhook`.

## Demo accounts

Admin bootstrap: register a user, then promote to `ADMIN` in the database (`npx prisma studio` → `User` → set `role = "ADMIN"`).

## Project layout

```
app/api/        API routes (auth, products, cart, checkout, orders, admin, otp, newsletter, stripe)
app/            Pages: /, /products/[id], /cart, /checkout, /orders, /account, /login, /admin, ...
lib/            auth helpers, OTP/proof tokens, rate limiting, email/SMS channels, Prisma client
prisma/         schema + seed
proxy.ts        Security headers + nonce CSP (Next.js proxy)
```

## Notes

- Phone OTP is mock-only (no SMS provider wired yet).
- The DB must be reachable from the machine running the app.
