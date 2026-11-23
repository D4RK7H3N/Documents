"""Align the app's strands and courses with the wording the school's own
student files use (the USAT folder).

What the files say:
  11 JAMES-ID.xlsx / JOHN DATA ID 2.xlsx -> Automotive, Automotive & Small
      Engine Technologies
  11-NOAH-programming.csv / G-11-SOLOMON-CSS.csv -> ICT Support and Computer
      Programming Technologies (one name for the whole ICT strand)
  Daniel.xlsx / Student-DATA-11-DAVID.csv -> Construction & Building
      Technology
  G-11-THESSALONIANS-FBS.csv -> Hospitality and Tourism
  G11- PROVERBS AMOS.xlsx -> Agri-Fishery Business and Food Innovation (and
      "Industrial Technologies", which is a cluster)
  Ats_1B_bundle_ -> AUTOMOTIVE & SMALL ENGINE TECHNOLOGIES (course)
  COE1.csv -> Computer Electronics 1 (COE1) (course)
  HRS1B.csv -> Hotel and Restaurant Services 1 - B (course)

Two strands the school teaches have no record yet: Construction & Building
Technology and Hospitality and Tourism. They are added, the wording is
added as aliases so every sheet lands, and the sections are pointed at the
strand their own file names.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from tracks.models import Strand, Course, Section  # noqa: E402


def add_alias(obj, extra):
    """Append alias names to a strand or course (comma separated)."""
    current = [a.strip() for a in (obj.aliases or "").split(",") if a.strip()]
    added = []
    for name in extra:
        if name.strip().lower() not in [c.lower() for c in current]:
            current.append(name.strip())
            added.append(name.strip())
    obj.aliases = ", ".join(current)
    obj.save()
    return added


def strand(name, code, aliases):
    obj, created = Strand.objects.get_or_create(
        code=code, defaults={"name": name, "track": Strand.objects.first().track}
    )
    if not created:
        obj.name = name
        obj.save()
    added = add_alias(obj, aliases)
    print("  %s strand %-42s code %-10s aliases +%s" % ("NEW " if created else "UPD ", obj.name, obj.code, added))
    return obj


def course(name, code, aliases):
    obj = Course.objects.filter(code=code).first() or Course.objects.filter(name=name).first()
    if not obj:
        print("  !! no course with code %s" % code)
        return None
    added = add_alias(obj, aliases)
    print("  UPD  course %-40s aliases +%s" % (obj.name, added))
    return obj


print("=== strands ===")
automotive = strand(
    "Automotive Servicing (NCI & NCII)", "Automotive",
    ["Automotive", "Automotive & Small Engine Technologies",
     "Automotive and Small Engine Technologies"],
)
construction = strand(
    "Construction & Building Technology", "CBT",
    ["Construction & Building Technology", "Construction and Building Technology"],
)
tourism = strand(
    "Hospitality and Tourism", "HOT",
    ["Hospitality and Tourism", "Hospitality And Tourism"],
)

# The NCII strand that the school's own files call Hospitality and Tourism
fbs = Strand.objects.filter(code="FBS").first()
if fbs:
    add_alias(fbs, ["Hospitality and Tourism", "Hospitality And Tourism"])
    print("  UPD  strand %-42s aliases +Hospitality and Tourism" % fbs.name)

print("=== courses ===")
course(
    "Automotive Mechanic", "AM",
    ["Automotive & Small Engine Technologies",
     "AUTOMOTIVE & SMALL ENGINE TECHNOLOGIES"],
)
course(
    "Computer and Electronics", "COMP-E",
    ["Computer Electronics 1 (COE1)", "Computer Electronics 1", "COE1"],
)
course(
    "Hotel and Restaurant Services", "HRS",
    ["Hotel and Restaurant Services 1 - B", "Hotel and Restaurant Services 1", "HRS1"],
)

print("=== sections pointed at the strand their own file names ===")
fixes = [
    ("Daniel", construction),
    ("David", construction),
    ("Thessalonians", tourism),
]
for name, target in fixes:
    section = Section.objects.filter(name=name).first()
    if not section:
        print("  no section named %s" % name)
        continue
    if section.strand_id != target.id:
        print("  %-14s %-42s -> %s" % (name, section.strand.name if section.strand_id else "-", target.name))
        section.strand = target
        section.save()

# Solomon is in the school's files but has no section yet
if not Section.objects.filter(name="Solomon").exists():
    css = Strand.objects.filter(code="ICT-CSS").first()
    Section.objects.create(
        name="Solomon",
        level_type="SHS",
        grade_year="Grade 11",
        strand=css,
    )
    print("  NEW  section Solomon (Grade 11, %s)" % (css.name if css else "-"))

# the bundled sheet for 1B is the automotive one
am = Course.objects.filter(code="AM").first()
one_b = Section.objects.filter(name="1B").first()
if one_b and am and one_b.course_id != am.id:
    print("  1B course %s -> %s" % (one_b.course.name if one_b.course_id else "-", am.name))
    one_b.course = am
    one_b.save()

print("")
print("strands:", Strand.objects.count(), "| courses:", Course.objects.count(), "| sections:", Section.objects.count())
for s in Strand.objects.order_by("name"):
    print("  %-44s %-10s sections: %s" % (s.name, s.code, ", ".join(
        Section.objects.filter(strand=s).order_by("grade_year", "name").values_list("name", flat=True)) or "-"))
