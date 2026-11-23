"""Bring the sections back from the off-site backup.

Only the sections are restored - the rest of the live database (the API
tokens, the sessions and the students) must not be touched.
"""
import os
import json
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from tracks.models import Section, Strand, Course, Adviser  # noqa: E402

DUMP = r"C:\SMS-Backup\repo\db.json"

with open(DUMP, encoding="utf-8") as fh:
    data = json.load(fh)

if isinstance(data, dict):
    rows = data.get("objects") or data.get("data") or []
else:
    rows = data

sections = [r for r in rows if r.get("model") == "tracks.section"]
print("section rows in the backup:", len(sections))
if not sections:
    models = sorted({r.get("model") for r in rows})
    print("models in the dump:", models[:40])
    raise SystemExit(1)

# what the strand / course / adviser ids mean
strands = {s.id: s.name for s in Strand.objects.all()}
courses = {c.id: c.name for c in Course.objects.all()}
advisers = {a.id: a.full_name for a in Adviser.objects.all()}

created = 0
for row in sections:
    f = row["fields"]
    name = f.get("name")
    if not name or Section.objects.filter(name=name).exists():
        continue
    strand_id = f.get("strand")
    course_id = f.get("course")
    adviser_id = f.get("adviser")
    Section.objects.create(
        name=name,
        level_type=f.get("level_type") or "SHS",
        grade_year=f.get("grade_year") or "",
        strand_id=strand_id if strand_id in strands else None,
        course_id=course_id if course_id in courses else None,
        adviser_id=adviser_id if adviser_id in advisers else None,
        is_active=f.get("is_active", True),
    )
    created += 1

print("sections restored:", created)
print("sections now    :", Section.objects.count())
for s in Section.objects.order_by("grade_year", "name"):
    print(
        "   %-14s %-14s strand=%-44s course=%-28s adviser=%s"
        % (
            s.grade_year,
            s.name,
            s.strand.name if s.strand_id else "-",
            s.course.name if s.course_id else "-",
            s.adviser.full_name if s.adviser_id else "-",
        )
    )
