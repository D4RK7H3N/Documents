"""Look for broken characters in every section.

A sheet that was written in the school's own encoding (Windows-1252) and
read as UTF-8 leaves a "?" behind - and a sheet that was read with the
wrong encoding leaves "Ã" and "Â" behind. Both are caught here.
"""

import os
import unicodedata

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from django.db.models import Count  # noqa: E402

from students.models import Student  # noqa: E402

FIELDS = [
    "lrn",
    "first_name",
    "middle_name",
    "last_name",
    "address",
    "guardian_name",
    "guardian_address",
    "contact_number",
    "guardian_contact",
    "track_strand",
    "section",
    "course",
    "email",
    "nationality",
    "previous_school",
]

SUSPECT = {"\ufffd", "\u00c3", "\u00c2", "\u00e2\u0080"}


def suspicious(value):
    """True when the text carries a character that is clearly a mistake."""
    text = str(value or "")
    if not text:
        return False
    for char in text:
        if char in SUSPECT:
            return True
        if ord(char) > 127:
            # A letter with an accent is fine; a control or private-use
            # character is not.
            category = unicodedata.category(char)
            if category in ("Cc", "Cf", "Co", "Cs", "Cn"):
                return True
    return False


def main():
    sections = (
        Student.objects.values("section")
        .annotate(total=Count("id"))
        .order_by("section")
    )
    found = 0
    for row in sections:
        students = Student.objects.filter(section=row["section"])
        broken = []
        for student in students:
            for field in FIELDS:
                value = getattr(student, field)
                if suspicious(value):
                    broken.append((student, field, str(value)))
        if not broken:
            continue
        found += len(broken)
        print("== %s (%d students)" % (row["section"], row["total"]))
        for student, field, value in broken:
            print(
                "   id=%-6s %-10s %-16s %-14s %s"
                % (
                    student.id,
                    field,
                    student.last_name,
                    student.first_name,
                    value[:70],
                )
            )
    print("")
    print("broken values found: %d" % found)


if __name__ == "__main__":
    main()
