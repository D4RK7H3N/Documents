# Profile Contact Info — Design

**Date:** 2026-08-08
**Status:** Approved

## Goal

Give users a way to store their phone number and structured shipping address on their profile, used to prefill checkout and snapshot onto orders for courier/tracking purposes.

## Data Model

- `User` gains optional fields:
  - `addressLine String?`
  - `city String?`
  - `zipCode String?`
  - `phone String?`
- `Order` gains `phone String?` — snapshot at checkout, like the existing `shippingAddr`.
- Migration: `add_user_contact_info`.

## API

`/api/me`:

- `GET` — return the new fields alongside existing ones.
- `PATCH` — accept `addressLine`, `city`, `zipCode`, `phone` (all optional, trimmed, max 200 chars; phone loose validation 7–20 chars). Profile fields are always optional.

`/api/checkout`:

- `POST` body gains `phone` — required (Zod: trimmed, min 7, max 20). Stored on the order.
- Address remains a single free-text `shippingAddr` on the order (joined from profile fields at checkout).

## UI

**Account page** (`components/AccountForm.tsx`): add a "CONTACT INFO" section inside the profile form with four inputs — Phone, Address line, City, ZIP — saved with the same `/api/me` PATCH flow.

**Checkout** (`app/checkout/page.tsx`): on load, fetch `/api/me` (in addition to cart). Prefill:
- shipping address textarea = `addressLine, city, zipCode` joined (only when non-empty)
- new required **Phone** input, prefilled from profile

**Order detail** (`app/orders/[id]/page.tsx`): show the order's phone next to the shipping address block.

**Invoice** (`app/admin/orders/[id]/invoice/page.tsx`): show phone in the billing section.

## Out of Scope

- Saving checkout edits back to the profile (explicitly declined).
- Address book / multiple addresses.
- Phone display on the public storefront.
