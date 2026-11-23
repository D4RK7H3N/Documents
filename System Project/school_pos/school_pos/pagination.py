from urllib.parse import urlsplit

from rest_framework.pagination import PageNumberPagination


class SmsPageNumberPagination(PageNumberPagination):
    """Page size can be raised by the client up to a sane ceiling.

    Screens that need the whole roster (the cashier's lookup, the sections
    page, the students list) used to walk ten pages of 50 to build their
    lookups. Letting them ask for a bigger page turns that into one request,
    while the ceiling stops anyone from dumping the whole database in one go.
    """

    page_size_query_param = "page_size"
    max_page_size = 1000


class RelativePagination(SmsPageNumberPagination):
    """Mission P3 - `next`/`previous` are root-relative paths+queries - never
    absolute backend URLs (sms2-api.darkzhub.asia / gw.darkzhub.asia).

    DRF builds absolute links from the request's Host header, which is
    attacker-controllable behind the Cloudflare proxy, and the API must no
    longer advertise the backend host at all. Page-size semantics are
    inherited unchanged from SmsPageNumberPagination.
    """

    def _relative(self, url):
        if not url:
            return None
        parts = urlsplit(url)
        if not parts.scheme and not parts.netloc:
            return url
        path = parts.path or "/"
        return f"{path}?{parts.query}" if parts.query else path

    def get_next_link(self):
        return self._relative(super().get_next_link())

    def get_previous_link(self):
        return self._relative(super().get_previous_link())
