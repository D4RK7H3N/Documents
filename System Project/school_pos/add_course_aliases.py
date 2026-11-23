"""Add the aliases the school's own sheets use for the bundled courses.

The bundled class lists name the qualification the way the school writes it
("Hotel and Restaurant Services 1 - A"), so the course has to know that
wording. Run it after a new sheet shows up with a name the importer could
not match.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from tracks.models import Course, Strand  # noqa: E402

COURSE_ALIASES = {
    "Hotel and Restaurant Services": [
        "Hotel and Restaurant Services 1 - A",
        "Hotel and Restaurant Services 1 - B",
        "Hotel and Restaurant Services 1",
        "HRS1",
    ],
    "Automotive Mechanic": [
        "Automotive & Small Engine Technologies",
        "Automotive and Small Engine Technologies",
    ],
    "Computer and Electronics": [
        "Computer Electronics 1 (COE1)",
        "Computer Electronics 1",
        "COE1",
    ],
}


def main():
    for course_name, aliases in COURSE_ALIASES.items():
        course = Course.objects.filter(name=course_name).first()
        if not course:
            print("course not found:", course_name)
            continue
        existing = [
            a.strip()
            for a in (course.aliases or "").split(",")
            if a.strip()
        ]
        added = [a for a in aliases if a not in existing]
        if not added:
            print("%-34s ok" % course_name)
            continue
        course.aliases = ", ".join(existing + added)
        course.save(update_fields=["aliases"])
        print("%-34s + %s" % (course_name, ", ".join(added)))


if __name__ == "__main__":
    main()
