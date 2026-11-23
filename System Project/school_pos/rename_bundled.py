"""Rename the bundled sections to the school's own class names and drop the
students the first import brought in (they were placed with the old code).

The school calls its bundled classes:
  ATS 1A / ATS 1B   - Automotive & Small Engine Technologies
  COE1              - Computer & Electronics
  HRS 1A / HRS 1B   - Hotel and Restaurant Services
The app still had the sample names (1A / 1B / 1C).
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from tracks.models import Course, Section  # noqa: E402
from students.models import Student  # noqa: E402
from tuition.models import TuitionPayment  # noqa: E402

am = Course.objects.filter(code="AM").first()
comp = Course.objects.filter(code="COMP-E").first()
hrs = Course.objects.filter(code="HRS").first()

# old name -> (new name, course)
RENAMES = [
    ("1A", "ATS 1A", am),
    ("1B", "ATS 1B", am),
    ("1C", "COE1", comp),
    # 1C became COE1, so HRS 1A takes the freed slot
    ("2A", "ATS 2A", am),
    ("2B", "COE2", comp),
    ("2C", "HRS 2C", hrs),
]

# the school has HRS 1A and HRS 1B - 1B is new, so create it
if not Section.objects.filter(name="HRS 1A").exists():
    Section.objects.create(
        name="HRS 1A",
        level_type="BUN",
        grade_year="1st Year",
        course=hrs,
    )
    print("created section HRS 1A")

if not Section.objects.filter(name="HRS 1B").exists():
    Section.objects.create(
        name="HRS 1B",
        level_type="BUN",
        grade_year="1st Year",
        course=hrs,
    )
    print("created section HRS 1B")

for old, new, course in RENAMES:
    section = Section.objects.filter(name=old).first()
    if not section:
        continue
    if Section.objects.filter(name=new).exclude(id=section.id).exists():
        print("skipped", old, "->", new, "(the name is taken)")
        continue
    section.name = new
    if course is not None and old in ("1A", "1B", "1C"):
        section.course = course
    section.save()
    print("renamed", old, "->", new)

# The first import placed the students with the old code - start clean.
count = Student.objects.count()
if count:
    TuitionPayment.objects.all().delete()
    Student.objects.all().delete()
    print("removed", count, "students from the first import")

print("")
print("sections now:")
for s in Section.objects.order_by("grade_year", "name"):
    print(
        "   %-14s %-14s strand=%-42s course=%s"
        % (
            s.grade_year,
            s.name,
            (s.strand.name if s.strand_id else "-"),
            (s.course.name if s.course_id else "-"),
        )
    )
