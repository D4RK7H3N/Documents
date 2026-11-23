"""Check a few students by name."""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from students.models import Student  # noqa: E402


def main():
    for needle in sys.argv[1:]:
        print("== %s ==" % needle)
        for student in Student.objects.filter(
            last_name__icontains=needle
        ) | Student.objects.filter(first_name__icontains=needle):
            print(
                "  id=%-6s lrn=%-16s %-12s %-14s %-14s sec=%-14s dob=%s"
                % (
                    student.id,
                    student.lrn,
                    student.first_name,
                    student.middle_name or "",
                    student.last_name,
                    student.section,
                    student.date_of_birth,
                )
            )


if __name__ == "__main__":
    main()
