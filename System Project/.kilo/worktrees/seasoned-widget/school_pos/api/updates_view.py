import os
from pathlib import PurePath

from django.http import FileResponse, Http404, HttpResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

UPDATES_DIR = settings.BASE_DIR / "updates"
# Allowed extensions for Electron auto-updater files
ALLOWED_EXTENSIONS = {"exe", "yml", "blockmap"}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def serve_update_file(request, filename):
    """Serve update files for Electron auto-updater.

    Security:
    - Requires authentication.
    - Filename is sanitized to prevent path traversal.
    - Only known safe extensions are served.
    """
    # Sanitize filename: reject any path separators or parent-directory tricks
    safe_name = PurePath(filename).name
    if not safe_name or safe_name != filename:
        raise Http404("Invalid filename")

    # Validate extension
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise Http404("File type not allowed")

    file_path = UPDATES_DIR / safe_name

    # Defensive: ensure resolved path is still inside UPDATES_DIR
    try:
        file_path.resolve().relative_to(UPDATES_DIR.resolve())
    except ValueError:
        raise Http404("Invalid path")

    if not file_path.exists():
        raise Http404(f"Update file '{safe_name}' not found")

    # For YAML files, return as text
    if ext == "yml":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HttpResponse(content, content_type="text/yaml")

    # For binary files, serve with correct headers
    response = FileResponse(
        open(file_path, "rb"),
        content_type="application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    response["Content-Length"] = os.path.getsize(file_path)
    return response
