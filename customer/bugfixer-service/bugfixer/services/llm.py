import requests
from django.conf import settings


def llm_enabled():
    return bool(settings.LLM_API_KEY)


def chat_completion(messages, model=None, max_tokens=500):
    response = requests.post(
        settings.LLM_BASE_URL.rstrip("/") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model or settings.LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
        },
        timeout=settings.LLM_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"].get("content") or ""
