import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from django.db.models import Count  # noqa: E402

from students.models import Student  # noqa: E402

print("TOTAL:", Student.objects.count())
print(
    "no section:",
    Student.objects.filter(section__isnull=True).count()
    + Student.objects.filter(section="").count(),
)
print("LRNs with a stray quote:", Student.objects.filter(lrn__contains="'").count())
print("placeholder lrns:", Student.objects.filter(lrn__startswith="0").count())
print()
rows = (
    Student.objects.values("section", "level_type", "track_strand", "course")
    .annotate(c=Count("id"))
    .order_by("section")
)
for row in rows:
    print(
        "%-14s %-5s %-44s %-32s %d"
        % (
            row["section"],
            row["level_type"],
            row["track_strand"] or "-",
            row["course"] or "-",
            row["c"],
        )
    )
