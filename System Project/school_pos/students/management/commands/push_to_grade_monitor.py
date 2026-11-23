import json
import os
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand

from students.models import Student

BATCH_SIZE = 200


class Command(BaseCommand):
    help = "Push learners from this system to the Grade Monitoring System ingest API."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=os.environ.get("GRADE_MONITOR_URL", ""))
        parser.add_argument("--key", default=os.environ.get("GRADE_MONITOR_KEY", ""))
        parser.add_argument("--include-unsectioned", action="store_true")

    def handle(self, *args, **options):
        base_url = (options["url"] or "").rstrip("/")
        key = options["key"] or ""
        if not base_url or not key:
            self.stderr.write(
                "Provide --url and --key (or set GRADE_MONITOR_URL and GRADE_MONITOR_KEY)."
            )
            return

        queryset = Student.objects.filter(level_type="SHS").order_by("id")
        if not options["include_unsectioned"]:
            queryset = queryset.exclude(section__isnull=True).exclude(section="")

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No learners to push."))
            return

        self.stdout.write(f"Pushing {total} learners to {base_url} ...")
        created = updated = skipped = sent = 0
        batch = []

        def flush(items):
            nonlocal created, updated, skipped, sent
            if not items:
                return
            body = json.dumps({"students": items}).encode("utf-8")
            request = urllib.request.Request(
                f"{base_url}/api/v1/integration/ingest/",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Integration-Key": key,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    report = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:300]
                self.stderr.write(f"HTTP {exc.code} from Grade Monitor: {detail}")
                raise SystemExit(1)
            except urllib.error.URLError as exc:
                self.stderr.write(f"Could not reach Grade Monitor: {exc.reason}")
                raise SystemExit(1)
            created += len(report.get("created", []))
            updated += len(report.get("updated", []))
            skipped += len(report.get("skipped", []))
            sent += len(items)
            self.stdout.write(f"  pushed {sent}/{total}")

        for student in queryset.iterator(chunk_size=BATCH_SIZE):
            raw_level = (student.shs_grade or student.current_grade_level or "").strip().lower()
            if raw_level in ("11", "g11", "grade11", "grade-11", "grade 11"):
                grade_level = "Grade 11"
            elif raw_level in ("12", "g12", "grade12", "grade-12", "grade 12"):
                grade_level = "Grade 12"
            else:
                grade_level = ""
            batch.append(
                {
                    "lrn": student.lrn,
                    "first_name": student.first_name,
                    "middle_name": student.middle_name or "",
                    "last_name": student.last_name,
                    "section": student.section or "",
                    "grade_level": grade_level,
                }
            )
            if len(batch) >= BATCH_SIZE:
                flush(batch)
                batch = []
        flush(batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created} updated={updated} skipped={skipped}"
            )
        )
