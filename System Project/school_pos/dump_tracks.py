"""Dump the Track / Strand / Course data (plus the sections that use them)
to JSON so the document can be generated from one source of truth."""
import os
import json

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from tracks.models import Track, Strand, Course, Section  # noqa: E402
from students.models import Student  # noqa: E402

payload = {
    "tracks": [],
    "strands": [],
    "courses": [],
    "sections": [],
    "students": {},
}

for t in Track.objects.all().order_by("name"):
    payload["tracks"].append({
        "name": t.name,
        "code": t.code,
        "level_type": t.level_type,
        "description": t.description or "",
        "is_active": t.is_active,
        "strand_count": t.strands.count(),
    })

for s in Strand.objects.all().order_by("track__name", "name"):
    payload["strands"].append({
        "name": s.name,
        "code": s.code,
        "track": s.track.name if s.track_id else "",
        "description": s.description or "",
        "aliases": [a.strip() for a in (s.aliases or "").split(",") if a.strip()],
        "is_active": s.is_active,
        "sections": list(
            Section.objects.filter(strand=s).order_by("grade_year", "name").values_list("name", flat=True)
        ),
        "students": Student.objects.filter(strand=s).count(),
    })

for c in Course.objects.all().order_by("name"):
    payload["courses"].append({
        "name": c.name,
        "code": c.code,
        "abbreviation": c.abbreviation or "",
        "description": c.description or "",
        "aliases": [a.strip() for a in (c.aliases or "").split(",") if a.strip()],
        "level_type": c.level_type,
        "duration_years": c.duration_years,
        "is_active": c.is_active,
        "sections": list(
            Section.objects.filter(course=c).order_by("grade_year", "name").values_list("name", flat=True)
        ),
        "students": Student.objects.filter(course_fk=c).count(),
    })

for sec in Section.objects.all().order_by("level_type", "grade_year", "name"):
    payload["sections"].append({
        "name": sec.name,
        "level_type": sec.level_type,
        "grade_year": sec.grade_year,
        "strand": sec.strand.name if sec.strand_id else "",
        "course": sec.course.name if sec.course_id else "",
        "adviser": sec.adviser.full_name if sec.adviser_id else "",
        "students": Student.objects.filter(section=sec.name).count(),
    })

# grade levels in use
payload["grade_years"] = sorted(
    {s["grade_year"] for s in payload["sections"] if s["grade_year"]}
)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "tracks_courses_data.json")
out = os.path.normpath(out)
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, ensure_ascii=False)

print("tracks :", len(payload["tracks"]))
print("strands:", len(payload["strands"]))
print("courses:", len(payload["courses"]))
print("sections:", len(payload["sections"]))
print("grade years:", payload["grade_years"])
print("->", out)
