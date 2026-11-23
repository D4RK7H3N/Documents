"""Where are the stray apostrophes still left in the roster?"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from students.models import Student  # noqa: E402

FIELDS = [
    "lrn",
    "first_name",
    "middle_name",
    "last_name",
    "track_strand",
    "section",
    "course",
    "address",
    "guardian_name",
    "guardian_address",
    "contact_number",
    "guardian_contact",
]

for field in FIELDS:
    hits = Student.objects.filter(**{"%s__contains" % field: "'"})
    count = hits.count()
    if not count:
        continue
    print("%-18s %d" % (field, count))
    for student in hits[:5]:
        print("    %s" % getattr(student, field))
