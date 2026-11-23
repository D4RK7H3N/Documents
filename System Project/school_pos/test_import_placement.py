"""Dry run of the enrollment import: no data is kept.

Every file in the USAT folder is uploaded to the import endpoint inside a
transaction that is rolled back afterwards, so the placement can be checked
without touching the roster. The report shows, per file, where the students
would land.
"""

import io
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from django.test import override_settings  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

from students.models import Student  # noqa: E402
from django.db.models import Count  # noqa: E402

USAT = r"C:\Users\DarkZhen\Documents\System Project\USAT"


def files():
    found = []
    for base, _dirs, names in os.walk(USAT):
        for name in sorted(names):
            if name.lower().endswith((".xlsx", ".xls", ".csv")):
                found.append(os.path.join(base, name))
    return sorted(found)


def main():
    user = get_user_model().objects.filter(is_superuser=True).first()
    if not user:
        print("no superuser")
        return 1
    client = APIClient()
    client.force_authenticate(user=user)

    from django.conf import settings

    hosts = list(settings.ALLOWED_HOSTS) + ["testserver"]

    for path in files():
        name = os.path.basename(path)
        with open(path, "rb") as handle:
            payload = handle.read()
        upload = SimpleUploadedFile(
            name, payload, content_type="application/octet-stream"
        )
        try:
            with override_settings(ALLOWED_HOSTS=hosts):
                with transaction.atomic():
                    response = client.post(
                        "/api/students/bulk_upload/", {"file": upload}
                    )
                    body = response.data if hasattr(response, "data") else {}
                    counts = list(
                        Student.objects.values("section")
                        .annotate(c=Count("id"))
                        .order_by("-c")
                    )
                    raise RuntimeError("rollback")
        except RuntimeError:
            pass
        except Exception as error:  # pragma: no cover - diagnostics only
            print("%-46s FAILED %s" % (name, error))
            continue

        print("=" * 100)
        print(
            "%s  status=%s created=%s updated=%s skipped=%s errors=%s"
            % (
                name,
                response.status_code,
                body.get("created_count"),
                body.get("updated_count"),
                body.get("skipped_count"),
                len(body.get("errors") or []),
            )
        )
        print(
            "   named in file: %-24s placed by file=%-4s by strand=%-4s "
            "placeholder lrns=%-4s inherited=%s"
            % (
                body.get("sections_named_in_file"),
                body.get("rows_placed_by_file"),
                body.get("rows_placed_by_strand"),
                body.get("rows_with_placeholder_lrn"),
                body.get("strands_inherited_from_section"),
            )
        )
        print("   sections: %s" % counts[:14])
        if body.get("unmapped_strands"):
            print("   unmapped: %s" % body["unmapped_strands"])
        for error in (body.get("errors") or [])[:3]:
            print("   ! %s" % error)
        for warning in (body.get("warnings") or [])[:3]:
            print("   ~ %s" % warning)
    return 0


if __name__ == "__main__":
    sys.exit(main())
