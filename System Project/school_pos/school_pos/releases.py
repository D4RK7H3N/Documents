"""
Self-hosted release feed for the Electron app's auto-updater.

The installers used to live only on GitHub Releases. A 200 MB upload to GitHub
is slow and occasionally drops, and it puts the school's update channel in the
hands of a third party. The files are now stored on the school's own server
(this machine) and served from here; GitHub Releases is kept as a mirror for
the clients that were built before this switch.

    GET /releases/latest.yml
    GET /releases/School-Management-System-Setup-1.1.5.exe
    GET /releases/School-Management-System-Setup-1.1.5.exe.blockmap

Range requests are honoured, which is what electron-updater needs for its
differential (blockmap) downloads.
"""
import mimetypes
import os
import re

from django.conf import settings
from django.http import Http404, HttpResponse, StreamingHttpResponse

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")

# A file being written by the publish script is copied in under a temporary
# name and renamed into place, so a half-written file is never served.
ALLOWED_SUFFIXES = (".exe", ".blockmap", ".yml")


def _release_dir():
    return getattr(settings, "RELEASES_ROOT", os.path.join(settings.BASE_DIR, "releases"))


def _safe_path(filename):
    """Resolve a requested file inside the release directory.

    Rejects any path that tries to escape the directory.
    """
    if os.path.basename(filename) != filename:
        raise Http404("Not found")
    root = os.path.abspath(_release_dir())
    full = os.path.abspath(os.path.join(root, filename))
    if os.path.commonpath([root, full]) != root:
        raise Http404("Not found")
    if not full.lower().endswith(ALLOWED_SUFFIXES):
        raise Http404("Not found")
    if not os.path.isfile(full):
        raise Http404("Not found")
    return full


def serve_release(request, filename):
    """Serve an installer, blockmap or manifest with range support."""
    full = _safe_path(filename)
    size = os.path.getsize(full)
    content_type = mimetypes.guess_type(full)[0] or "application/octet-stream"

    range_header = request.META.get("HTTP_RANGE", "")
    match = RANGE_RE.match(range_header) if range_header else None

    if match:
        start_raw, end_raw = match.groups()
        if start_raw:
            start = int(start_raw)
            end = int(end_raw) if end_raw else size - 1
        else:
            # Suffix range: the last N bytes.
            length = int(end_raw or 0)
            start = max(0, size - length)
            end = size - 1
        if start >= size or start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        end = min(end, size - 1)
        length = end - start + 1

        def stream():
            with open(full, "rb") as fh:
                fh.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = fh.read(min(1024 * 256, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        response = StreamingHttpResponse(stream(), status=206, content_type=content_type)
        response["Content-Length"] = str(length)
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
        response["Accept-Ranges"] = "bytes"
    else:
        response = StreamingHttpResponse(
            open(full, "rb"), content_type=content_type
        )
        response["Content-Length"] = str(size)
        response["Accept-Ranges"] = "bytes"

    # The manifest must never be cached, or a client keeps asking for a build
    # that is already superseded. The installer may be cached hard: it is
    # immutable per version and the file name carries the version.
    if filename.endswith(".yml"):
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Cloudflare-CDN-Cache-Control"] = "no-store"
    else:
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        response["Cloudflare-CDN-Cache-Control"] = "public, max-age=31536000, immutable"

    response["X-Content-Type-Options"] = "nosniff"
    return response
