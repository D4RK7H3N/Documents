# SafeSwap PH — Database & System Architecture Design

> **Stack:** Django REST Framework + PostgreSQL | Django Channels | Flutter | PayMongo/Xendit | FCM | Cloudflare R2  
> **Date:** 2026-08-18  
> **Status:** Architecture Blueprint — assumptions flagged inline with ⚠️

---

## Table of Contents

1. [Core Design Principles](#1-core-design-principles)
2. [Entity-Relationship Diagram (ERD)](#2-entity-relationship-diagram-erd)
3. [Entity Specifications](#3-entity-specifications)
4. [Trade/Escrow State Machine](#4-tradeescrow-state-machine)
5. [Security & Data Sensitivity](#5-security--data-sensitivity)
6. [Scalability & Performance](#6-scalability--performance)
7. [Django Model Skeletons](#7-django-model-skeletons)
8. [Business Rule Assumptions to Confirm](#8-business-rule-assumptions-to-confirm)

---

## 1. Core Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Immutable ledger** | All wallet movements recorded in `ledger_entries`; wallet balance is a materialized view with nightly reconciliation. |
| **Double-entry bookkeeping** | Every financial movement has a debit and credit leg (even platform fees). |
| **Event-sourced trades** | `TradeEvent` table captures every state transition with actor, timestamp, and reason. |
| **Idempotent payments** | All PayMongo/Xendit calls carry idempotency keys stored in `payment_records`. |
| **Row-level security via claims** | JWT carries `kyc_tier`, `roles`, and `roblox_verified` — DRF permission classes enforce. |
| **Soft deletes** | All user-facing entities use `deleted_at` (not `DELETE`) to preserve audit trails. |

---

## 2. Entity-Relationship Diagram (ERD)

```text
┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│       users         │       │  kyc_verifications  │       │  roblox_accounts    │
├─────────────────────┤       ├─────────────────────┤       ├─────────────────────┤
│ PK id (UUID)        │◄──────┤ PK id (UUID)        │       │ PK id (UUID)        │
│ username            │       │ FK user_id          │       │ FK user_id          │
│ email (unique)      │       │ status (enum)       │       │ roblox_user_id      │
│ phone               │       │ tier (enum)         │       │ roblox_username     │
│ password_hash       │       │ id_doc_type         │       │ is_verified         │
│ roles (jsonb)       │       │ id_doc_number       │       │ verification_code   │
│ kyc_tier            │       │ selfie_url (R2)     │       │ account_age_days    │
│ is_active           │       │ id_front_url (R2)   │       │ trust_score         │
│ created_at          │       │ id_back_url (R2)    │       │ created_at          │
│ updated_at          │       │ submitted_at        │       └─────────────────────┘
│ deleted_at          │       │ reviewed_at         │                │
└─────────────────────┘       │ reviewer_id         │                │
         │                    └─────────────────────┘                │
         │                                                           │
         │         ┌─────────────────────┐                          │
         │         │      wallets        │                          │
         │         ├─────────────────────┤                          │
         │         │ PK id (UUID)        │                          │
         └────────►│ FK user_id (unique) │◄─────────────────────────┘
                   │ balance (decimal)   │         ┌─────────────────────┐
                   │ hold_balance        │         │   listings          │
                   │ currency (PHP)      │         ├─────────────────────┤
                   │ created_at          │         │ PK id (UUID)        │
                   │ updated_at          │         │ FK seller_id        │
                   └─────────────────────┘         │ FK roblox_account_id│
                            │                      │ trade_type (enum)   │
                            │                      │ item_type (enum)    │
                            │                      │ item_name           │
                            │                      │ description         │
                            │                      │ price (decimal)     │
                            │                      │ quantity            │
                            │                      │ status (enum)       │
                            │                      │ created_at          │
                            │                      │ updated_at          │
                            │                      └─────────────────────┘
                            │                               │
                            │                               │
                   ┌────────▼────────┐              ┌───────▼────────┐
                   │  ledger_entries │              │     trades     │
                   ├─────────────────┤              ├────────────────┤
                   │ PK id (BIGSERIAL│              │ PK id (UUID)   │
                   │ FK wallet_id    │              │ FK listing_id  │
                   │ entry_type (en) │              │ FK buyer_id    │
                   │ amount (decimal)│              │ FK seller_id   │
                   │ balance_after   │              │ status (enum)  │
                   │ trade_id (FK)   │              │ amount (dec)   │
                   │ payment_id (FK) │              │ platform_fee   │
                   │ description     │              │ net_amount     │
                   │ created_at      │              │ started_at     │
                   └─────────────────┘              │ completed_at   │
                            │                       │ disputed_at    │
                            │                       │ resolved_at    │
                            │                       │ created_at     │
                            │                       └────────────────┘
                            │                               │
                   ┌────────▼────────┐              ┌───────▼────────┐
                   │ payment_records │              │  trade_events  │
                   ├─────────────────┤              ├────────────────┤
                   │ PK id (UUID)    │              │ PK id (BIGSER) │
                   │ FK trade_id     │              │ FK trade_id    │
                   │ provider (enum) │              │ actor_id       │
                   │ provider_ref    │              │ event_type     │
                   │ amount (dec)    │              │ from_status    │
                   │ status (enum)   │              │ to_status      │
                   │ idempotency_key │              │ metadata (json)│
                   │ webhook_payload │              │ created_at     │
                   │ created_at      │              └────────────────┘
                   │ updated_at      │
                   └─────────────────┘
                            │
                   ┌────────▼────────┐
                   │    disputes     │
                   ├─────────────────┤
                   │ PK id (UUID)    │
                   │ FK trade_id(unq)│
                   │ FK raised_by    │
                   │ reason (enum)   │
                   │ status (enum)   │
                   │ resolution_note │
                   │ resolved_by     │
                   │ created_at      │
                   │ resolved_at     │
                   └─────────────────┘
                            │
                   ┌────────▼────────┐
                   │dispute_evidences│
                   ├─────────────────┤
                   │ PK id (UUID)    │
                   │ FK dispute_id   │
                   │ FK uploaded_by  │
                   │ file_url (R2)   │
                   │ description     │
                   │ created_at      │
                   └─────────────────┘

┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│     chat_rooms      │       │      messages       │       │  media_attachments  │
├─────────────────────┤       ├─────────────────────┤       ├─────────────────────┤
│ PK id (UUID)        │◄──────┤ PK id (BIGSERIAL)   │       │ PK id (UUID)        │
│ FK trade_id (unique)│       │ FK room_id          │       │ FK owner_id         │
│ created_at          │       │ FK sender_id        │       │ file_type (enum)    │
│ is_active           │       │ content (text)      │       │ r2_key              │
│                     │       │ message_type        │       │ r2_bucket           │
│                     │       │ is_deleted (soft)   │       │ file_size           │
│                     │       │ created_at          │       │ mime_type           │
│                     │       └─────────────────────┘       │ metadata (jsonb)    │
│                     │                                     │ created_at          │
│                     │                                     └─────────────────────┘
│                     │
│                     │              ┌─────────────────────┐
│                     │              │    notifications    │
│                     │              ├─────────────────────┤
│                     │              │ PK id (BIGSERIAL)   │
│                     │              │ FK user_id          │
│                     │              │ fcm_token           │
│                     │              │ title               │
│                     │              │ body                │
│                     │              │ payload (jsonb)     │
│                     │              │ is_read             │
│                     │              │ sent_at             │
│                     │              │ delivered_at        │
│                     │              └─────────────────────┘
│                     │
│                     │              ┌─────────────────────┐
│                     │              │      ratings        │
│                     │              ├─────────────────────┤
│                     │              │ PK id (UUID)        │
│                     │              │ FK trade_id (unique)│
│                     └─────────────►│ FK rater_id         │
│                                    │ FK ratee_id         │
│                                    │ score (1-5)         │
│                                    │ comment             │
│                                    │ created_at          │
│                                    └─────────────────────┘
```

---

## 3. Entity Specifications

### 3.1 `users`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK, default=gen_random_uuid() | Use UUIDs everywhere for security-through-obscurity on URLs |
| `username` | VARCHAR(50) | NOT NULL, unique | Display name |
| `email` | VARCHAR(255) | NOT NULL, unique, indexed | Login credential |
| `phone` | VARCHAR(20) | nullable, unique | PH format (+63...); optional but required for KYC Tier 2+ |
| `password_hash` | VARCHAR(255) | NOT NULL | Django default PBKDF2 or Argon2 |
| `roles` | JSONB | NOT NULL, default=["trader"] | `["trader"]`, `["trader","support"]`, `["admin"]` |
| `kyc_tier` | SMALLINT | NOT NULL, default=0, check 0-3 | 0=unverified, 1=basic, 2=verified, 3=trusted |
| `is_active` | BOOLEAN | NOT NULL, default=true | Soft-disable flag |
| `email_verified` | BOOLEAN | NOT NULL, default=false | |
| `phone_verified` | BOOLEAN | NOT NULL, default=false | |
| `created_at` | TIMESTAMPTZ | NOT NULL, default=now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, auto_now | |
| `deleted_at` | TIMESTAMPTZ | nullable | Soft delete |

**PostgreSQL indexes:** `email` (unique), `username` (unique), `kyc_tier` + `is_active` (composite, for listing queries)

---

### 3.2 `kyc_verifications`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK→users.id, CASCADE, unique (one active per user) | |
| `status` | VARCHAR(20) | NOT NULL, check IN (...) | `pending`, `under_review`, `approved`, `rejected`, `expired` |
| `tier` | SMALLINT | NOT NULL | Target tier being applied for |
| `id_doc_type` | VARCHAR(20) | nullable | `passport`, `drivers_license`, `umid`, `national_id` |
| `id_doc_number_hash` | VARCHAR(255) | nullable | **Hashed** — store only HMAC, never plaintext |
| `id_doc_number_enc` | BYTEA | nullable | **Encrypted at rest** — AES-256 for recovery/review |
| `selfie_r2_key` | VARCHAR(500) | nullable | R2 key to selfie photo |
| `id_front_r2_key` | VARCHAR(500) | nullable | R2 key to ID front |
| `id_back_r2_key` | VARCHAR(500) | nullable | R2 key to ID back |
| `submitted_at` | TIMESTAMPTZ | nullable | |
| `reviewed_at` | TIMESTAMPTZ | nullable | |
| `reviewer_id` | UUID | FK→users.id, SET NULL | Admin who reviewed |
| `rejection_reason` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**Security:** `id_doc_number_enc` encrypted with Django's `Fernet` (key from `settings.KYC_ENCRYPTION_KEY`). R2 keys for docs should use **pre-signed URLs** with short expiry, not public buckets.

---

### 3.3 `roblox_accounts`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK→users.id, CASCADE | |
| `roblox_user_id` | BIGINT | NOT NULL, unique | Roblox's own numeric ID |
| `roblox_username` | VARCHAR(50) | NOT NULL | Denormalized; updates via API sync |
| `is_verified` | BOOLEAN | NOT NULL, default=false | Ownership verified via profile code |
| `verification_code` | VARCHAR(50) | nullable | Code user must place in profile bio |
| `account_age_days` | INTEGER | nullable | Fetched from Roblox API |
| `trust_score` | SMALLINT | nullable, check 0-100 | Computed: age + past trades + ratings |
| `last_synced_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**Index:** `roblox_user_id` (unique), `user_id` (one-to-many if multiple alts allowed)

⚠️ **ASSUMPTION:** Users can link multiple Roblox accounts. If only one allowed, add `unique_together = ['user_id', 'is_verified']` or a partial unique index.

---

### 3.4 `wallets`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `user_id` | UUID | FK→users.id, CASCADE, **unique** | One wallet per user |
| `balance` | DECIMAL(15,2) | NOT NULL, default=0, check >=0 | **Materialized** — must reconcile with ledger |
| `hold_balance` | DECIMAL(15,2) | NOT NULL, default=0, check >=0 | Funds locked in active trades |
| `currency` | VARCHAR(3) | NOT NULL, default='PHP' | |
| `last_reconciled_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**Scalability note:** `balance` is materialized for fast reads. A nightly Celery job reconciles: `balance = SUM(ledger_entries.amount WHERE wallet_id=X AND entry_type='credit') - SUM(...debit...)`. Discrepancy triggers admin alert.

---

### 3.5 `ledger_entries` (Immutable Audit Trail)
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BIGSERIAL | PK | BigInt for volume |
| `wallet_id` | UUID | FK→wallets.id, PROTECT | Never allow wallet delete if ledger exists |
| `entry_type` | VARCHAR(10) | NOT NULL, check IN ('debit','credit') | |
| `amount` | DECIMAL(15,2) | NOT NULL, check >0 | Always positive; sign from entry_type |
| `balance_after` | DECIMAL(15,2) | NOT NULL | Running balance snapshot |
| `trade_id` | UUID | FK→trades.id, SET NULL, nullable | |
| `payment_id` | UUID | FK→payment_records.id, SET NULL, nullable | |
| `description` | VARCHAR(255) | NOT NULL | Human-readable |
| `metadata` | JSONB | nullable | Flexible: fee breakdown, exchange rate, etc. |
| `created_at` | TIMESTAMPTZ | NOT NULL, default=now() | |

**PostgreSQL:** Partition by `created_at` (monthly) when volume >1M rows/month. Index `wallet_id` + `created_at` (composite).

---

### 3.6 `listings`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `seller_id` | UUID | FK→users.id, CASCADE | |
| `roblox_account_id` | UUID | FK→roblox_accounts.id, SET NULL, nullable | Which Roblox account holds the item |
| `trade_type` | VARCHAR(20) | NOT NULL | `sell` (item→PHP), `buy` (PHP→item), `trade` (item↔item) |
| `item_type` | VARCHAR(30) | NOT NULL | `robux`, `limited_item`, `gamepass`, `other` |
| `item_name` | VARCHAR(255) | NOT NULL | |
| `item_roblox_asset_id` | BIGINT | nullable | Roblox asset ID if applicable |
| `description` | TEXT | nullable | |
| `price` | DECIMAL(15,2) | NOT NULL, check >=0 | In PHP |
| `quantity` | INTEGER | NOT NULL, default=1, check >=1 | |
| `status` | VARCHAR(20) | NOT NULL, default='active' | `active`, `paused`, `sold`, `expired`, `deleted` |
| `expires_at` | TIMESTAMPTZ | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |
| `deleted_at` | TIMESTAMPTZ | nullable | Soft delete |

**Index:** `status` + `item_type` + `price` (for marketplace filtering), `seller_id` + `status` (for seller dashboard).

⚠️ **ASSUMPTION:** Listings are seller-posted offers. If buyers post "want to buy" listings, the same table works with `trade_type='buy'`.

---

### 3.7 `trades` (Escrow State Machine)
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `listing_id` | UUID | FK→listings.id, PROTECT | Preserve reference even if listing deleted |
| `buyer_id` | UUID | FK→users.id, PROTECT | |
| `seller_id` | UUID | FK→users.id, PROTECT | |
| `status` | VARCHAR(20) | NOT NULL, default='initiated' | See state machine §4 |
| `amount` | DECIMAL(15,2) | NOT NULL | Trade value |
| `platform_fee` | DECIMAL(15,2) | NOT NULL, default=0 | ⚠️ **ASSUMPTION:** Flat % fee, e.g., 5% |
| `net_amount` | DECIMAL(15,2) | NOT NULL | `amount - platform_fee` (what seller receives) |
| `buyer_confirmed` | BOOLEAN | NOT NULL, default=false | |
| `seller_confirmed` | BOOLEAN | NOT NULL, default=false | |
| `buyer_confirmed_at` | TIMESTAMPTZ | nullable | |
| `seller_confirmed_at` | TIMESTAMPTZ | nullable | |
| `started_at` | TIMESTAMPTZ | nullable | When status→funded |
| `completed_at` | TIMESTAMPTZ | nullable | When status→completed |
| `disputed_at` | TIMESTAMPTZ | nullable | |
| `resolved_at` | TIMESTAMPTZ | nullable | |
| `expires_at` | TIMESTAMPTZ | nullable | Auto-cancel if no funding |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**Index:** `status` (for escrow worker queries), `buyer_id` + `status`, `seller_id` + `status`.

---

### 3.8 `trade_events` (Event Sourcing / Audit)
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `trade_id` | UUID | FK→trades.id, CASCADE | |
| `actor_id` | UUID | FK→users.id, SET NULL | Who triggered; null for system |
| `event_type` | VARCHAR(30) | NOT NULL | `status_change`, `payment_received`, `dispute_opened`, `admin_override`, etc. |
| `from_status` | VARCHAR(20) | nullable | For status changes |
| `to_status` | VARCHAR(20) | nullable | For status changes |
| `metadata` | JSONB | nullable | Arbitrary context |
| `created_at` | TIMESTAMPTZ | NOT NULL, default=now() | |

**Index:** `trade_id` + `created_at` (composite, DESC). Partition by month at scale.

---

### 3.9 `payment_records`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `trade_id` | UUID | FK→trades.id, CASCADE | |
| `provider` | VARCHAR(20) | NOT NULL | `paymongo`, `xendit`, `internal_wallet` |
| `provider_ref` | VARCHAR(255) | nullable | PayMongo payment_intent.id or Xendit invoice ID |
| `provider_charge_id` | VARCHAR(255) | nullable | For refunds/lookups |
| `amount` | DECIMAL(15,2) | NOT NULL | |
| `fee` | DECIMAL(15,2) | NOT NULL, default=0 | Provider fee |
| `status` | VARCHAR(20) | NOT NULL | `pending`, `processing`, `paid`, `failed`, `refunded`, `cancelled` |
| `idempotency_key` | UUID | NOT NULL, unique | Generated by us; sent to provider |
| `webhook_payload` | JSONB | nullable | Raw webhook body for audit |
| `processed_at` | TIMESTAMPTZ | nullable | When webhook confirmed |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**Security:** `provider_ref` is not highly sensitive but treat as PII-adjacent. `webhook_payload` may contain PII — restrict access.

---

### 3.10 `disputes`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `trade_id` | UUID | FK→trades.id, PROTECT, **unique** | One dispute per trade |
| `raised_by_id` | UUID | FK→users.id, PROTECT | Who opened it |
| `reason` | VARCHAR(50) | NOT NULL | `item_not_received`, `item_not_as_described`, `seller_not_responding`, `fraud`, `other` |
| `description` | TEXT | NOT NULL | |
| `status` | VARCHAR(20) | NOT NULL, default='open' | `open`, `under_review`, `resolved_buyer`, `resolved_seller`, `resolved_split`, `closed_no_action` |
| `resolution_note` | TEXT | nullable | Admin explanation |
| `resolved_by_id` | UUID | FK→users.id, SET NULL | Admin |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `resolved_at` | TIMESTAMPTZ | nullable | |

---

### 3.11 `dispute_evidences`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `dispute_id` | UUID | FK→disputes.id, CASCADE | |
| `uploaded_by_id` | UUID | FK→users.id, PROTECT | |
| `file_r2_key` | VARCHAR(500) | NOT NULL | |
| `file_type` | VARCHAR(20) | NOT NULL | `screenshot`, `video`, `chat_export`, `receipt`, `other` |
| `description` | TEXT | nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

### 3.12 `chat_rooms`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `trade_id` | UUID | FK→trades.id, CASCADE, **unique** | One room per trade |
| `is_active` | BOOLEAN | NOT NULL, default=true | Lock after trade complete |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

### 3.13 `messages`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `room_id` | UUID | FK→chat_rooms.id, CASCADE | |
| `sender_id` | UUID | FK→users.id, SET NULL | Null if system message |
| `content` | TEXT | NOT NULL | |
| `message_type` | VARCHAR(20) | NOT NULL, default='text' | `text`, `image`, `system`, `trade_update` |
| `is_deleted` | BOOLEAN | NOT NULL, default=false | Soft delete |
| `created_at` | TIMESTAMPTZ | NOT NULL, default=now() | |

**PostgreSQL:** Partition by `room_id` hash or `created_at` monthly at scale. Index `room_id` + `created_at` (composite, DESC) for chat history.

---

### 3.14 `notifications`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | BIGSERIAL | PK | |
| `user_id` | UUID | FK→users.id, CASCADE | |
| `fcm_token` | VARCHAR(255) | nullable | Snapshot at send time |
| `title` | VARCHAR(255) | NOT NULL | |
| `body` | TEXT | NOT NULL | |
| `payload` | JSONB | nullable | Deep-link data |
| `category` | VARCHAR(30) | NOT NULL | `trade_update`, `payment`, `dispute`, `chat`, `system` |
| `is_read` | BOOLEAN | NOT NULL, default=false | |
| `sent_at` | TIMESTAMPTZ | nullable | When FCM accepted |
| `delivered_at` | TIMESTAMPTZ | nullable | When device acked (if implemented) |
| `error_info` | JSONB | nullable | FCM error response |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**Index:** `user_id` + `is_read` + `created_at` DESC (inbox query).

---

### 3.15 `ratings`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `trade_id` | UUID | FK→trades.id, PROTECT, **unique** | One rating per trade |
| `rater_id` | UUID | FK→users.id, PROTECT | Who gave rating |
| `ratee_id` | UUID | FK→users.id, PROTECT | Who was rated |
| `score` | SMALLINT | NOT NULL, check 1-5 | |
| `comment` | TEXT | nullable, check length <=500 | |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

⚠️ **ASSUMPTION:** Only the buyer rates the seller after trade completion. If mutual ratings desired, remove `unique` on `trade_id` and add `unique_together = ['trade_id', 'rater_id']`.

---

### 3.16 `media_attachments`
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `owner_id` | UUID | FK→users.id, CASCADE | |
| `file_type` | VARCHAR(20) | NOT NULL | `kyc_doc`, `listing_image`, `dispute_evidence`, `chat_media` |
| `r2_key` | VARCHAR(500) | NOT NULL, unique | |
| `r2_bucket` | VARCHAR(100) | NOT NULL | |
| `file_size` | BIGINT | NOT NULL | Bytes |
| `mime_type` | VARCHAR(100) | NOT NULL | |
| `checksum` | VARCHAR(64) | nullable | SHA-256 for integrity |
| `metadata` | JSONB | nullable | Dimensions, duration, etc. |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

---

## 4. Trade/Escrow State Machine

### States
```
INITIATED      — Buyer accepted listing / trade created
    ↓ [buyer funds via payment webhook]
FUNDED         — Escrow holds buyer's PHP (wallet or external payment)
    ↓ [seller confirms they will deliver]
IN_PROGRESS    — Seller has committed to deliver
    ↓ [seller marks delivered + provides evidence]
DELIVERED      — Seller claims Roblox item transferred
    ↓ [buyer confirms receipt]
CONFIRMED      — Buyer verified they received item
    ↓ [system releases funds]
RELEASED       — Funds moved from hold to seller wallet
    ↓ [system finalizes]
COMPLETED      — Trade closed, ratings unlocked
```

### Alternate / Exception Paths
```
From any of: INITIATED, FUNDED, IN_PROGRESS, DELIVERED
    ↓ [either party raises dispute, or auto-timeout fires]
DISPUTED       — Locked for admin review
    ↓ [admin resolves]
RESOLVED       → RELEASED (if seller wins) or REFUNDED (if buyer wins)
    ↓ [system processes]
REFUNDED       — Funds returned to buyer wallet
    ↓ [system finalizes]
CANCELLED      — Trade closed (expired, buyer cancelled before funding)
```

### Transition Matrix

| From | To | Trigger | Actor | Requires Webhook |
|------|-----|---------|-------|-----------------|
| `initiated` | `funded` | Payment confirmed | System (webhook) | **YES** |
| `initiated` | `cancelled` | Buyer cancels / expires | Buyer / System | No |
| `funded` | `in_progress` | Seller accepts trade | Seller | No |
| `funded` | `cancelled` | Seller declines / refund | Seller / System | **YES** (refund) |
| `in_progress` | `delivered` | Seller marks delivered | Seller | No |
| `in_progress` | `disputed` | Buyer/seller raises dispute | Either | No |
| `delivered` | `confirmed` | Buyer confirms receipt | Buyer | No |
| `delivered` | `disputed` | Buyer claims non-receipt | Buyer | No |
| `confirmed` | `released` | System releases escrow | System | No (internal ledger) |
| `released` | `completed` | System finalizes | System | No |
| `disputed` | `resolved` | Admin decides seller wins | Admin | No |
| `disputed` | `refunded` | Admin decides buyer wins | Admin | **YES** (if external refund) |

### ⚠️ ASSUMPTIONS TO CONFIRM:
1. **Auto-release:** Should `delivered` auto-transition to `confirmed` after N hours (e.g., 24h) if buyer doesn't respond? ⚠️
2. **Auto-cancel:** Should `initiated` auto-cancel after N minutes if not funded? ⚠️
3. **Dispute time window:** How long after trade completion can a dispute be raised? ⚠️
4. **Fee on refund:** If trade is refunded, does platform still charge fee or reverse it? ⚠️

---

## 5. Security & Data Sensitivity

### 5.1 Encryption at Rest

| Data | Method | Key Management |
|------|--------|---------------|
| KYC document numbers (`id_doc_number_enc`) | Django Fernet (AES-128-CBC + HMAC) | `settings.KYC_ENCRYPTION_KEY` from env |
| Payment provider API keys | Environment variables only | Never in DB; use Django-environ |
| FCM tokens | Plaintext OK | Low sensitivity; rotate on logout |
| Roblox verification codes | Plaintext OK | Temporary; deleted after use |
| Chat messages | Plaintext | Consider TLS-only; no DB encryption needed unless regulatory |

### 5.2 Access Control Matrix

| Role | KYC Docs | Other User Wallets | Admin Actions | Dispute Resolution |
|------|----------|-------------------|---------------|-------------------|
| Trader (own data) | Read own only | Read own only | None | Can create |
| Trader (others) | None | None | None | None |
| Support | View for review | None | View trades | Can mediate (limited) |
| Admin | Full access | Full access (read) | Full | Full |

### 5.3 JWT Claims Structure

```json
{
  "sub": "user-uuid",
  "username": "trader123",
  "roles": ["trader"],
  "kyc_tier": 2,
  "kyc_status": "approved",
  "roblox_verified": true,
  "iat": 1692345678,
  "exp": 1692349278,
  "jti": "refresh-token-uuid",
  "type": "access"
}
```

| Claim | Permission Gate |
|-------|----------------|
| `kyc_tier >= 1` | Can create listings |
| `kyc_tier >= 2` | Can trade >PHP 5,000 ⚠️ (threshold TBC) |
| `roblox_verified == true` | Can link items to Roblox account |
| `"admin" in roles` | Admin endpoints |
| `"support" in roles` | Dispute dashboard |

**Token hardening:**
- Access token: 15-minute TTL
- Refresh token: 7-day TTL, single-use with rotation
- Blacklist: Redis SET with `jti` of revoked tokens (logout, password change, role change)
- Refresh token family: If reused token detected → revoke entire family (theft detection)

### 5.4 R2 / Media Security

- **Bucket policy:** Private. Never public-read.
- **URL generation:** Pre-signed URLs via Cloudflare API, 15-minute expiry.
- **KYC docs:** Additional IP restriction if possible (backend-only generation).
- **Chat media:** Virus scan on upload (ClamAV or Cloudflare scanning if available).

---

## 6. Scalability & Performance

### 6.1 Denormalization / Caching Strategy

| Computed Value | Strategy | Invalidation |
|----------------|----------|--------------|
| Wallet `balance` | Materialized column | Updated within `atomic()` ledger write transaction |
| User `trust_score` | Materialized on `users` | Celery task recalculates on trade complete/rating |
| Listing search/filter | PostgreSQL GIN index on `item_name` (trigram) or pg_bigm | N/A |
| Seller rating average | Materialized field on `users` | Triggered on new `ratings` row |
| Active trade counts | Redis counter | Incr/decr on status change |

### 6.2 Partitioning Strategy

| Table | Partition Key | When to Enable |
|-------|--------------|----------------|
| `ledger_entries` | `created_at` (monthly) | >500K rows/month |
| `trade_events` | `created_at` (monthly) | >1M rows/month |
| `messages` | `created_at` (monthly) or HASH(`room_id`) | >1M rows/month |
| `notifications` | `created_at` (monthly) | >2M rows/month |

### 6.3 Read Replicas

| Query Pattern | Replica? | Notes |
|--------------|----------|-------|
| Listing marketplace browse | **Yes** | Heavy filtering/sorting; eventual consistency OK |
| Trade history (user dashboard) | **Yes** | Slight delay acceptable |
| Wallet balance / ledger | **No** | Must be primary for consistency |
| Payment webhook processing | **No** | Must be primary |
| Admin dispute dashboard | Optional | Can tolerate slight delay |

### 6.4 Django Channels Scaling

| Layer | Self-hosted Option |
|-------|-------------------|
| Channel layer | Redis (`channels_redis`) |
| WebSocket workers | Run 4-8 `daphne`/`uvicorn` workers behind Nginx |
| Group routing | One group per `chat_rooms.id` + one per `users.id` for presence |

**Presence:** Track user online status in Redis (TTL 60s); broadcast to trade chat room on join/leave.

---

## 7. Django Model Skeletons

See `safeswapph_models.py` for the complete Django model code skeleton.

---

## 8. Business Rule Assumptions to Confirm

| # | Assumption | Impact if Wrong |
|---|-----------|-----------------|
| 1 | Users can link **multiple** Roblox accounts | Schema allows N:1; if 1:1 only, add unique constraint |
| 2 | Platform fee is **percentage of trade** (e.g., 5%) | If flat fee or tiered, `platform_fee` calc changes |
| 3 | **Only sellers** post listings (buyer browses) | If buyers post WTB, `trade_type='buy'` logic needs review |
| 4 | **One rating per trade** (buyer→seller only) | If mutual, change `ratings` unique constraint |
| 5 | **PHP-only** currency | If multi-currency, add `currency` to listings/trades |
| 6 | KYC **Tier 0** = can browse only; **Tier 1+** = can trade | Governs permission logic; confirm thresholds |
| 7 | Auto-release after 24h of `delivered` without buyer action | If no auto-release, state machine stays in `delivered` forever |
| 8 | Auto-cancel `initiated` after 30 min without funding | Prevents stale trades; confirm timeout |
| 9 | Dispute window = **7 days** after trade completion | Governs when `ratings` locked vs dispute allowed |
| 10 | Wallet withdrawals are **out of scope** (trade balance only) | If withdrawals to GCash/bank needed, add withdrawal flow |
| 11 | Roblox item transfer is **manual** (seller to buyer in-game) | If API-automated, add Roblox API integration layer |
| 12 | Platform holds **PHP in wallet**, not crypto/Robux | Escrow is fiat PHP; Roblox items never touch platform |
