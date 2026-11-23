# GearUp PH - AI-Powered Gaming Accessories Shop

Full-stack e-commerce shop with AI semantic search, recommendations, a RAG shopping
assistant (DeepSeek), an admin description generator, and review sentiment analysis.

- **Backend:** Django + Django REST Framework + PostgreSQL (JWT auth)
- **Frontend:** React (Vite) + Tailwind CSS (dark theme)
- **ML:** sentence-transformers (`all-MiniLM-L6-v2`), scikit-learn
- **Payments:** PayMongo (test mode) + Cash on delivery
- **Currency:** PHP

## Features

1. **Catalog** - categories, products with images, stock, and purchasable variants
   (per-variant price/stock), filters and sorting.
2. **Cart / checkout / orders** - JWT-authenticated cart; transactional checkout that
   validates stock and decrements it atomically (no overselling); server-recomputed
   prices; order status tracking (pending -> paid -> processing -> shipped -> delivered).
3. **Semantic search** - `GET /api/search/?q=` embeds the query and matches products by
   meaning ("cheap gift for a gamer") and tolerates typos ("gaming keybord").
4. **Recommendations** - "Customers also bought" from co-purchase counts, "Similar
   products" from embedding similarity, with best-seller fallback (cold start).
5. **AI shopping assistant** - floating chat widget; RAG over the product catalog via
   DeepSeek (OpenAI-compatible SDK). Answers ONLY from retrieved products and links
   to their pages. Logged to `ChatLog`.
6. **Admin AI description generator** - button on the product admin page drafts a
   description with the LLM; admin edits before saving.
7. **Review sentiment** - every review is auto-classified positive/neutral/negative
   (embedding anchor classifier); summary shown on the product page.

## Project structure

```
gearup/
├── backend/
│   ├── config/            # Django project (settings, urls)
│   ├── users/             # register / login (JWT) / profile
│   ├── catalog/           # Category, Product, ProductVariant, ProductImage, Review
│   │   └── management/commands/seed_shop.py
│   ├── orders/            # Cart, CartItem, Order, OrderItem, checkout, PayMongo + webhook
│   ├── ai/                # ALL AI logic in services.py; search, recommendations, chat
│   │   └── management/commands/embed_all.py
│   ├── media/             # product images (generated SVGs from seed)
│   └── requirements.txt
├── data/
│   └── products_seed.json # sample catalog used by `seed_shop`
└── frontend/              # React + Vite + Tailwind
```

## Setup

### Prerequisites
- Python 3.10+ (tested on 3.14), Node.js 18+
- PostgreSQL 14+ — *or* set `DB_ENGINE=sqlite3` in `backend/.env` for a quick test
  without Postgres

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate              # Windows
# source venv/bin/activate         # macOS/Linux

pip install -r requirements.txt
copy .env.example .env             # Windows
# cp .env.example .env             # macOS/Linux
```

Edit `backend/.env`:
- PostgreSQL credentials (create the DB first: `CREATE DATABASE gearup;`),
  or set `DB_ENGINE=sqlite3` for a dependency-free local test.
- `DEEPSEEK_API_KEY` - required for the chat assistant and the admin description
  generator (the rest of the shop works without it).
- `PAYMONGO_SECRET_KEY` / `PAYMONGO_WEBHOOK_SECRET` - only needed for the card/GCash
  payment flow (COD works without them).

Then:

```bash
python manage.py migrate
python manage.py seed_shop         # categories, 20 products, users, sample orders
python manage.py embed_all         # first run downloads all-MiniLM-L6-v2 (~90 MB)
python manage.py runserver 127.0.0.1:8010
```

> The embedding model is loaded **once at server startup**; first boot takes a few
> extra seconds. Port 8010 is used here because 8000 was occupied on the dev machine -
> use any free port and keep `VITE_API_URL` in sync.

Seeded accounts:
- Admin: `admin` / `admin1234` (from `backend/.env` - change before deploying!)
- Demo customer: `demo@gearup.test` / `demo1234`

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env             # set VITE_API_URL to match the backend port
npm run dev
```

Open http://localhost:5173

### Retraining embeddings

Embeddings update automatically whenever a product is saved (post-save signal).
To backfill or refresh everything:

```bash
python manage.py embed_all         # add --force to recompute all
```

## Testing the API with curl

```bash
# 1. Semantic search (meaning-based, typo tolerant)
curl "http://127.0.0.1:8010/api/search/?q=cheap%20gift%20for%20a%20gamer"
curl "http://127.0.0.1:8010/api/search/?q=gaming%20keybord"

# 2. AI shopping assistant (requires DEEPSEEK_API_KEY in backend/.env)
curl -X POST http://127.0.0.1:8010/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "best wireless mouse under 2000?"}'

# 3. Checkout (requires a JWT token)
#    a. get a token (username or email)
curl -X POST http://127.0.0.1:8010/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo@gearup.test", "password": "demo1234"}'

#    b. add to cart
curl -X POST http://127.0.0.1:8010/api/cart/items/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"product": "apexstrike-k87-mechanical-keyboard", "variant": 1, "quantity": 1}'

#    c. checkout (COD). With PAYMONGO_SECRET_KEY set, use "paymongo" to get a
#       checkout_url to redirect to.
curl -X POST http://127.0.0.1:8010/api/checkout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"payment_method": "cod", "shipping_name": "Juan dela Cruz",
       "shipping_phone": "09171234567", "shipping_address": "123 Rizal St",
       "shipping_city": "Quezon City", "shipping_postal_code": "1100"}'
```

PowerShell users: `curl` is aliased to Invoke-WebRequest - use `curl.exe` and escape
quotes (`-d "{\"message\": \"...\"}"`), or use `Invoke-RestMethod`.

### Webhook (payment confirmation)

PayMongo signs webhooks with the `PayMongo-Signature` header
(`t=<timestamp>,te=<hmac>` where `hmac = HMAC-SHA256(webhook_secret, "{t}.{raw_body}")`).
The endpoint verifies the signature, then marks the matching order paid.
You can simulate it locally by computing that HMAC for a test payload with your
`PAYMONGO_WEBHOOK_SECRET`.

## API overview

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register/ | - | create account (returns JWT) |
| POST | /api/auth/token/ | - | login (username or email) |
| POST | /api/auth/token/refresh/ | - | refresh access token |
| GET/PATCH | /api/auth/me/ | JWT | profile |
| GET | /api/categories/ | - | category list |
| GET | /api/products/ | - | list + filters (`category`, `q`, `min_price`, `max_price`, `in_stock`, `featured`, `sort`) |
| GET | /api/products/{slug}/ | - | product detail |
| GET/POST | /api/products/{slug}/reviews/ | POST: JWT | reviews (auto sentiment) |
| GET | /api/search/?q= | - | semantic search (throttled 60/min) |
| GET | /api/recommendations/{slug}/ | - | similar + also-bought |
| GET | /api/cart/ | JWT | cart |
| POST | /api/cart/items/ | JWT | add to cart |
| PATCH/DELETE | /api/cart/items/{id}/ | JWT | update/remove |
| POST | /api/checkout/ | JWT | transactional checkout |
| GET | /api/orders/ , /api/orders/{number}/ | JWT | order history / tracking |
| POST | /api/payments/webhook/ | signature | PayMongo webhook |
| POST | /api/chat/ | - (throttled 10/min) | RAG assistant |
| POST | /api/ai/describe/ | admin | LLM description draft |

## Assumptions, security notes, and improvements

**Assumptions**
- Port 8010 for the backend on this machine (8000 occupied); PostgreSQL credentials
  were unavailable, so verification ran with `DB_ENGINE=sqlite3` - the shipped
  `.env.example` defaults to PostgreSQL.
- Embeddings are stored as JSON on the product row and searched with scikit-learn
  cosine NN (the spec's allowed alternative to pgvector).
- Review sentiment uses an embedding anchor classifier (no extra model download);
  PayMongo webhook payload parsing is defensive since exact event shapes vary.
- Product images are generated SVG placeholders; no guest checkout (JWT required).

**Security notes**
- Development defaults are insecure: change `DJANGO_SECRET_KEY`, `DEBUG=False`,
  the seeded admin password, and use a real DB before deploying. Add HTTPS/TLS.
- CORS is limited to the Vite dev origins; JWTs live in localStorage (XSS-sensitive) -
  consider httpOnly cookie storage with CSRF protection for production.
- PayMongo webhook signature verification rejects unsigned/invalid requests; keep
  `PAYMONGO_WEBHOOK_SECRET` secret. Admin endpoints require `is_staff`.
- Throttles: anonymous 240/min, search 60/min, chat 10/min (tune per traffic).

**Improving the recommendations**
- Move to pgvector with an IVFFlat/HNSW index for large catalogs.
- Hybrid ranking: blend co-purchase counts, embedding similarity, recency, and
  popularity decay; weight by rating.
- Session-based / sequence models (e.g. SASRec) or implicit-ALS on the full order
  matrix instead of direct co-counts.
- Use real order data per-user (currently co-purchase is global); add "frequently
  bought together" bundles from association rules (Apriori/FP-Growth).
