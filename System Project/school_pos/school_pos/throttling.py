from rest_framework.throttling import AnonRateThrottle


class CloudflareAwareAnonRateThrottle(AnonRateThrottle):
    """Anonymous throttle that keys by the real client IP.

    Behind the Cloudflare tunnel every request arrives from 127.0.0.1, so the
    default REMOTE_ADDR keying puts ALL users into one shared bucket — a few
    failed logins would lock out the entire school. Only when the request
    comes from the loopback tunnel do we trust the edge-computed
    CF-Connecting-IP; on a plain LAN install REMOTE_ADDR is already the real
    client and cannot be spoofed.
    """

    def get_ident(self, request):
        remote = request.META.get("REMOTE_ADDR", "")
        if remote in ("127.0.0.1", "::1"):
            cf_ip = (request.META.get("HTTP_CF_CONNECTING_IP") or "").strip()
            if cf_ip:
                return cf_ip
        return super().get_ident(request)


class LoginRateThrottle(CloudflareAwareAnonRateThrottle):
    rate = "10/hour"
