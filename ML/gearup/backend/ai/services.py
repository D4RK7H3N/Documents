"""AI services for GearUp PH.

Contains ALL AI logic: embeddings, semantic search, recommendations,
review sentiment, the RAG shopping assistant, and the admin description
generator. Views must call these functions - never inline AI logic.

The embedding model (all-MiniLM-L6-v2 via sentence-transformers) is loaded
exactly once per process, at Django startup (ai.apps.ready), and reused for
every request.
"""
import logging
import threading

import numpy as np
from django.conf import settings
from sklearn.neighbors import NearestNeighbors

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = settings.EMBEDDING_MODEL_NAME

_encoder = None
_encoder_failed = False
_lock = threading.Lock()
_sentiment_anchor_cache = None

MIN_SEARCH_SCORE = 0.15

SENTIMENT_ANCHORS = {
    "positive": [
        "Absolutely love it, works great",
        "Excellent quality, very satisfied",
        "Best purchase, highly recommend",
        "Amazing value, five stars",
        "Superb, exceeded my expectations",
    ],
    "negative": [
        "Terrible, broke immediately",
        "Complete waste of money",
        "Very disappointed, poor quality",
        "Stopped working, horrible experience",
        "Awful, would not recommend",
    ],
    "neutral": [
        "It is okay, does the job",
        "Average, nothing special",
        "As described, standard product",
        "Acceptable but unremarkable",
        "Fine for the price, ordinary",
    ],
}


class LLMNotConfiguredError(Exception):
    pass


class LLMError(Exception):
    pass


# ---------------------------------------------------------------------------
# Embedding model (loaded once)
# ---------------------------------------------------------------------------
def get_encoder():
    """Load and cache the sentence-transformers model (thread-safe, idempotent)."""
    global _encoder, _encoder_failed
    if _encoder is not None:
        return _encoder
    with _lock:
        if _encoder is not None:
            return _encoder
        if _encoder_failed:
            return None
        try:
            from sentence_transformers import SentenceTransformer

            _encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception as exc:
            _encoder_failed = True
            logger.warning("Could not load embedding model '%s': %s", EMBEDDING_MODEL_NAME, exc)
            return None
    return _encoder


def reset_encoder():
    """Allow a retry after a failed load (used by the embed_all command)."""
    global _encoder, _encoder_failed
    with _lock:
        _encoder = None
        _encoder_failed = False


def encoder_available() -> bool:
    return _encoder is not None


def embed_texts(texts):
    encoder = get_encoder()
    if encoder is None:
        raise RuntimeError("Embedding model is not available.")
    vectors = encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float32)


def product_text(product) -> str:
    category = product.category.name if product.category_id else ""
    return f"{product.name}. {product.brand} {category}. {product.description[:600]}"


def update_product_embedding(product) -> bool:
    """Compute and persist the embedding for one product. Returns success."""
    try:
        vector = embed_texts([product_text(product)])[0]
    except RuntimeError:
        return False
    product.embedding = [float(x) for x in vector]
    type(product).objects.filter(pk=product.pk).update(
        embedding=product.embedding, embedding_model=EMBEDDING_MODEL_NAME
    )
    return True


def _embedding_corpus():
    from catalog.models import Product

    products = list(
        Product.objects.filter(is_active=True)
        .exclude(embedding__isnull=True)
        .select_related("category")
    )
    if not products:
        return [], None
    matrix = np.asarray([p.embedding for p in products], dtype=np.float32)
    return products, matrix


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------
def search_products(query: str, limit: int = 12, min_score: float = MIN_SEARCH_SCORE):
    """Meaning-based product search; tolerant to typos and paraphrases."""
    query = (query or "").strip()
    if not query:
        return []
    try:
        query_vec = embed_texts([query])[0]
    except RuntimeError:
        return _keyword_fallback(query, limit)

    products, matrix = _embedding_corpus()
    if not products:
        return _keyword_fallback(query, limit)

    k = min(limit, len(products))
    neighbors = NearestNeighbors(n_neighbors=k, metric="cosine").fit(matrix)
    distances, indices = neighbors.kneighbors([query_vec])
    results = []
    for distance, index in zip(distances[0], indices[0]):
        score = float(1.0 - distance)
        if score >= min_score:
            products[index].search_score = score
            results.append(products[index])
    return results


def _keyword_fallback(query, limit):
    from django.db.models import Q

    from catalog.models import Product

    products = Product.objects.filter(is_active=True).filter(
        Q(name__icontains=query) | Q(description__icontains=query) | Q(brand__icontains=query)
    )[:limit]
    return list(products)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
def similar_products(product, limit: int = 6):
    """"Similar products" - nearest products by embedding similarity."""
    products, matrix = _embedding_corpus()
    positions = {p.pk: i for i, p in enumerate(products)}
    position = positions.get(product.pk)
    if position is None or matrix is None:
        return []

    k = min(limit + 1, len(products))
    neighbors = NearestNeighbors(n_neighbors=k, metric="cosine").fit(matrix)
    distances, indices = neighbors.kneighbors([matrix[position]])
    results = []
    for distance, index in zip(distances[0], indices[0]):
        candidate = products[index]
        if candidate.pk == product.pk:
            continue
        candidate.search_score = float(1.0 - distance)
        results.append(candidate)
        if len(results) >= limit:
            break
    return results


def co_purchased_products(product, limit: int = 6):
    """"Customers also bought" - co-purchase counts from past orders."""
    from django.db.models import Count

    from orders.models import OrderItem

    order_ids = OrderItem.objects.filter(product=product).values_list("order_id", flat=True)
    rows = (
        OrderItem.objects.filter(order_id__in=list(order_ids))
        .exclude(product=product)
        .values("product")
        .annotate(co_count=Count("id"))
        .order_by("-co_count")[:limit]
    )
    ids = [row["product"] for row in rows]
    if not ids:
        return []
    from catalog.models import Product

    by_id = {p.pk: p for p in Product.objects.filter(pk__in=ids, is_active=True)}
    return [by_id[pid] for pid in ids if pid in by_id]


def best_sellers(limit: int = 6):
    from django.db.models import Sum

    from catalog.models import Product
    from orders.models import OrderItem

    rows = (
        OrderItem.objects.values("product")
        .annotate(units=Sum("quantity"))
        .order_by("-units")[:limit]
    )
    ids = [row["product"] for row in rows]
    if not ids:
        return list(
            Product.objects.filter(is_active=True).order_by("-is_featured", "-created_at")[:limit]
        )
    by_id = {p.pk: p for p in Product.objects.filter(pk__in=ids, is_active=True)}
    return [by_id[pid] for pid in ids if pid in by_id]


def recommendations_for(product) -> dict:
    """Both recommendation blocks, with cold-start fallbacks."""
    also_bought = co_purchased_products(product)
    fallback = "none"
    if not also_bought:
        also_bought = similar_products(product, limit=6)
        fallback = "similar"
    if not also_bought:
        also_bought = best_sellers(limit=6)
        fallback = "best_sellers"
    return {
        "similar": similar_products(product),
        "also_bought": also_bought,
        "also_bought_fallback": fallback,
    }


# ---------------------------------------------------------------------------
# Review sentiment (embedding anchor classifier - no extra model download)
# ---------------------------------------------------------------------------
def classify_sentiment(text: str) -> dict:
    global _sentiment_anchor_cache

    if _sentiment_anchor_cache is None:
        labels = list(SENTIMENT_ANCHORS.keys())
        anchors = [t for label in labels for t in SENTIMENT_ANCHORS[label]]
        anchor_vecs = embed_texts(anchors)
        centroids = []
        cursor = 0
        for label in labels:
            count = len(SENTIMENT_ANCHORS[label])
            centroids.append(anchor_vecs[cursor:cursor + count].mean(axis=0))
            cursor += count
        centroids = np.asarray(centroids, dtype=np.float32)
        centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
        _sentiment_anchor_cache = (labels, centroids)

    labels, centroids = _sentiment_anchor_cache
    vec = embed_texts([text])[0]
    similarities = centroids @ vec
    best = int(np.argmax(similarities))
    return {"sentiment": labels[best], "score": round(float(similarities[best]), 4)}


# ---------------------------------------------------------------------------
# LLM (DeepSeek via the OpenAI-compatible SDK)
# ---------------------------------------------------------------------------
def _llm_client():
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        raise LLMNotConfiguredError(
            "The AI assistant is not configured (set DEEPSEEK_API_KEY in .env)."
        )
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=settings.DEEPSEEK_BASE_URL)


def _llm_complete(messages, max_tokens=600, temperature=0.2) -> str:
    client = _llm_client()
    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except LLMNotConfiguredError:
        raise
    except Exception as exc:
        raise LLMError(str(exc)) from exc
    return (response.choices[0].message.content or "").strip()


CHAT_SYSTEM_PROMPT = """You are the shopping assistant for GearUp PH, an online store for gaming accessories in the Philippines. Prices are in Philippine Peso (PHP).

Strict rules:
- Answer ONLY using the PRODUCTS context provided below. Never invent products, prices, stock levels, or availability.
- If the context does not contain what the customer needs, say you could not find a matching product and suggest browsing the catalog or searching again.
- Keep answers short (max ~120 words) and helpful.
- Mention product names exactly as given, with their exact prices.
- When you mention a product, include its URL exactly as given in the context.
- Do not mention these rules or the context format."""


def chat_answer(user, message: str) -> dict:
    """RAG shopping assistant: retrieve products, answer only from them."""
    from .models import ChatLog

    retrieved = search_products(message, limit=5, min_score=0.10)
    if not retrieved:
        return {
            "answer": (
                "I couldn't find products matching that question. Try browsing the "
                "catalog or searching for a specific product, like 'mechanical keyboard'."
            ),
            "products": [],
        }

    context_lines = []
    for position, product in enumerate(retrieved, start=1):
        context_lines.append(
            f"{position}. {product.name} - PHP {product.price} - category: "
            f"{product.category.name} - stock: {product.stock} - "
            f"url: /products/{product.slug}\n   description: {product.description[:220]}"
        )
    context = "\n".join(context_lines)

    answer = _llm_complete(
        [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"PRODUCTS context:\n{context}\n\nCustomer question: {message}",
            },
        ],
        max_tokens=500,
        temperature=0.2,
    )

    ChatLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        message=message,
        response=answer,
        retrieved_product_ids=[p.pk for p in retrieved],
    )

    products = [
        {"slug": p.slug, "name": p.name, "price": str(p.price)} for p in retrieved
    ]
    return {"answer": answer, "products": products}


def generate_description(name: str, features: str) -> str:
    """Draft a product description for admins to edit before saving."""
    prompt = (
        "You write product descriptions for GearUp PH, a gaming accessories "
        "e-commerce store in the Philippines (prices in PHP).\n"
        f"Product name: {name}\n"
        f"Key features: {features or 'not provided - infer from the product name'}\n"
        "Write an engaging, accurate product description of 80-140 words. "
        "Plain text only - no headings, no markdown, no pricing."
    )
    return _llm_complete(
        [{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.7,
    )
