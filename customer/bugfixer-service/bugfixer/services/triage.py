from django.conf import settings

from .llm import chat_completion, llm_enabled

LABELS = ("bug", "feature_request", "question")


def classify(message):
    """Return one of bug / feature_request / question. Fail safe to 'bug'."""
    if not llm_enabled():
        return "bug"
    prompt = (
        "Classify the following user report into exactly one category: "
        "bug, feature_request, or question. "
        "Reply with only the category name.\n\n"
        f"Report: {message[:1500]}"
    )
    try:
        answer = chat_completion([{"role": "user", "content": prompt}], model=settings.TRIAGE_MODEL, max_tokens=10)
    except Exception:
        return "bug"
    answer = answer.strip().lower()
    for label in LABELS:
        if label in answer:
            return label
    return "bug"
