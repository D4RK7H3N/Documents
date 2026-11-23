from django.conf import settings


def get_client_ip(request):
    """Real client IP: CF-Connecting-IP only when proxy headers are trusted."""
    if settings.TRUST_CLOUDFLARE_HEADERS:
        forwarded = request.META.get("HTTP_CF_CONNECTING_IP", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "")
