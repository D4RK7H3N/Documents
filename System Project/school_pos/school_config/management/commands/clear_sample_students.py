"""
Remove the sample students again.

The sample LRNs all start with "00" (a real LRN never does), so the whole
sample set can be taken out in one go - together with their tuition
payments.

    python manage.py clear_sample_students

To empty the roster completely - every student, whatever the LRN - use

    python manage.py clear_sample_students --all
"""
from django.core.management.base import BaseCommand

from students.models import Student


class Command(BaseCommand):
    help = "Delete the sample students (LRN starting with 00) and their payments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be removed.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Remove EVERY student, not only the ones whose LRN starts with 00.",
        )
        parser.add_argument(
            "--ids-file",
            default="",
            help="Remove exactly the students whose id is in this JSON file "
                 "(a list of ids). Used by the end-to-end test teardown, which "
                 "must not touch the students that were already enrolled.",
        )

    def handle(self, *args, **options):
        if options["ids_file"]:
            return self._remove_by_ids(options["ids_file"])

        if options["all"]:
            sample = Student.objects.all()
            label = "every student"
        else:
            sample = Student.objects.filter(lrn__startswith="00")
            label = "sample students"

        count = sample.count()
        payments = sum(s.tuition_payments.count() for s in sample)
        sections = sorted({s.section for s in sample if s.section})

        if options["dry_run"]:
            self.stdout.write(f"{count} {label}, {payments} payments")
            self.stdout.write(f"sections: {', '.join(sections)}")
            return

        if not count:
            self.stdout.write(f"No {label} found.")
            return

        sample.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {count} {label} and their {payments} tuition payments."
            )
        )

    def _remove_by_ids(self, ids_file):
        """Remove exactly the students whose id is listed in the file.

        The end-to-end test imports students and has to take them out again.
        It cannot use the LRN rule: the school's own enrolment sheets may use
        LRNs that start with "00" too, and those must never be touched.
        """
        import json
        import os

        if not os.path.exists(ids_file):
            self.stdout.write(f"No id file at {ids_file} - nothing to remove.")
            return

        try:
            with open(ids_file, encoding="utf-8") as fh:
                ids = json.load(fh)
        except (ValueError, OSError) as err:
            self.stdout.write(f"Could not read {ids_file}: {err}")
            return

        ids = [int(i) for i in ids if str(i).isdigit()]
        if not ids:
            self.stdout.write("The id file is empty - nothing to remove.")
            return

        students = Student.objects.filter(id__in=ids)
        count = students.count()
        payments = sum(s.tuition_payments.count() for s in students)
        students.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {count} students (by id) and their {payments} tuition payments."
            )
        )
