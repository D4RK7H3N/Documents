# Admin Data Browser — Design

**Date:** 2026-08-08
**Status:** Approved

## Goal

Give admins an in-app alternative to Prisma Studio: browse and manage all records (users, reviews, wishlists) with full CRUD, in the existing synthwave admin panel.

## Navigation

New `AdminTabs` component (`components/AdminTabs.tsx`): Dashboard, Products, Orders, Categories, Users, Reviews, Wishlists. Replaces the duplicated tab rows on `/admin`, `/admin/products`, `/admin/orders`, `/admin/categories`.

## Pages (all admin-gated, force-dynamic)

- `/admin/users` — table: name/email, role badge, order count, review count, joined; row actions:
  - Edit → modal (name, email, role)
  - Delete → guarded: blocked with message if user has orders (order history is never deletable); blocked on self
- `/admin/reviews` — product, user, stars, comment, date; delete (safe, cascades)
- `/admin/wishlists` — user, product, saved date; delete (safe, cascades)

## APIs (admin-only via token role check, Zod-validated)

- `GET /api/admin/users` — list with `_count`
- `PATCH/DELETE /api/admin/users/[id]` — edit name/email/role (409 duplicate email, block self-edit) ; delete guarded by order count
- `GET /api/admin/reviews`, `DELETE /api/admin/reviews/[id]`
- `GET /api/admin/wishlists`, `DELETE /api/admin/wishlists/[id]`

## Extras

- Admin order page now edits `shippingAddr` and `phone` (PATCH `/api/orders/[id]` extended).
- Product delete still guarded by cart/order references (the 409 explains the reason).

## Out of Scope

- Deleting order history or users with orders.
- Pagination on tables (small datasets).