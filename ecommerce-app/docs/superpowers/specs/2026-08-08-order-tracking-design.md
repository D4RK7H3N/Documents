# Order Shipment Tracking — Design

Date: 2026-08-08
Status: Approved

## Goal

Customers can see a full tracking timeline for each order. Admins assign tracking
numbers and advance order status. No carrier integration, no email notifications —
status is advanced manually by admins, matching the pre-payment flow.

## Data model

- `Order.trackingNumber String?` — set when an order ships.
- New `OrderEvent` model: `id` (cuid), `orderId`, `status` (OrderStatus), `note String?`,
  `createdAt`. One row per status change, forming the timeline.
- Checkout transaction also creates the initial `PENDING` event.
- Migration backfills a `PENDING` event (createdAt = order.createdAt) for existing orders.

## API

- `GET /api/orders/[id]` — accessible by the order owner or an admin (owner-checked 404
  otherwise). Returns order with items + product and events ascending.
- `PATCH /api/orders/[id]` — admin-only, body `{ status?, trackingNumber?, note? }`.
  - No backwards transitions. Canonical order: `PENDING → PAID → SHIPPED → DELIVERED`,
    `CANCELLED` allowed from `PENDING` or `PAID`. Violation → 409.
  - `SHIPPED` requires a tracking number (existing or new) → 400 otherwise.
  - Every status change appends an `OrderEvent` with the optional note.
  - Returns the updated order with events.

## Pages

- `app/orders/[id]/page.tsx` (server component) — customer view:
  - Auth via cookie JWT; redirect `/login` if unauthenticated, `/orders` if the order
    doesn't belong to the user.
  - Header: mono order id (cyan), status badge, mono total.
  - Vertical timeline: one dot per event (colored by status), connecting line, status
    label in display font, mono date, optional note.
  - Tracking number shown as a cyan mono chip once the order is SHIPPED or later.
  - Items list with thumbnails, quantities, line totals; shipping address.
- `app/orders/page.tsx` — cards become links to `/orders/[id]` (hover styling).
- `app/admin/orders/page.tsx` (server component) — admin table: order id, customer
  email, date, status badge, total, Manage link.
- `app/admin/orders/[id]/page.tsx` (client component) — status select, tracking number
  input, note input; PATCHes the API; inline errors; redirects to `/admin/orders` on
  success. Same fetch pattern as the admin product edit page.
- Small tabs row ("Products" | "Orders") on `/admin/products` and `/admin/orders`.

## Status → color mapping

PENDING cyan, PAID success green, SHIPPED purple, DELIVERED pink, CANCELLED danger —
matching the existing badges on `/orders`.
