"""Add the school's Track / Strand / Course reference to the student import
template, so the registrar uses wording the importer actually matches.

The file keeps its "Student Data Enrollment" sheet and gains:
  - "Strands & Courses" - every strand and course, the wording to type in the
    Strand column, and the other names it answers to
  - "Sections" - each section with the strand or course it teaches
"""
import os
import shutil

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from tracks.models import Track, Strand, Course, Section  # noqa: E402
from students.models import Student  # noqa: E402

TEMPLATE = r"C:\Users\DarkZhen\Downloads\student_import_template.xlsx"
BACKUP = TEMPLATE.replace(".xlsx", "-backup-before-strands.xlsx")

if not os.path.exists(BACKUP):
    shutil.copy2(TEMPLATE, BACKUP)
    print("backup:", BACKUP)

wb = openpyxl.load_workbook(TEMPLATE)

for name in ("Strands & Courses", "Sections"):
    if name in wb.sheetnames:
        del wb[name]

BLUE = PatternFill("solid", fgColor="1D4ED8")
LIGHT = PatternFill("solid", fgColor="EFF6FF")
WHITE = Font(bold=True, color="FFFFFF", size=10)
BOLD = Font(bold=True, size=10)
THIN = Border(*[Side(style="thin", color="D1D5DB")] * 4)

# ---------------------------------------------------------------- strands ---
ws = wb.create_sheet("Strands & Courses")
ws["A1"] = "USAT COLLEGE SAGAY CITY, INC."
ws["A1"].font = Font(bold=True, size=13, color="1D4ED8")
ws["A2"] = (
    "Track: %s. Type the strand exactly as written in the Strand column - the "
    "import also accepts the names in the third column."
    % ", ".join(t.name for t in Track.objects.all())
)
ws["A2"].font = Font(size=9, italic=True, color="4B5563")

headers = [
    "Type",
    "Type this in the Strand column",
    "Also accepted (aliases)",
    "Code",
    "Sections",
    "Enrolled",
]
row = 4
for i, h in enumerate(headers, start=1):
    cell = ws.cell(row, i, h)
    cell.font = WHITE
    cell.fill = BLUE
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    cell.border = THIN
row += 1

for s in Strand.objects.all().order_by("name"):
    sections = Section.objects.filter(strand=s).order_by("grade_year", "name")
    ws.cell(row, 1, "Strand")
    ws.cell(row, 2, s.name)
    ws.cell(row, 3, ", ".join(s.aliases.split(",")) if s.aliases else "-")
    ws.cell(row, 4, s.code)
    ws.cell(row, 5, ", ".join(x.name for x in sections) or "-")
    ws.cell(row, 6, Student.objects.filter(strand=s).count())
    row += 1

for c in Course.objects.all().order_by("name"):
    sections = Section.objects.filter(course=c).order_by("grade_year", "name")
    ws.cell(row, 1, "Course")
    ws.cell(row, 2, c.name)
    ws.cell(row, 3, ", ".join(c.aliases.split(",")) if c.aliases else "-")
    ws.cell(row, 4, c.code)
    ws.cell(row, 5, ", ".join(x.name for x in sections) or "-")
    ws.cell(row, 6, Student.objects.filter(course_fk=c).count())
    row += 1

for r in range(5, row):
    for c in range(1, len(headers) + 1):
        cell = ws.cell(r, c)
        cell.border = THIN
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        if r > 5:
            cell.font = Font(size=9)

for col, width in zip("ABCDEF", (10, 42, 62, 12, 34, 10)):
    ws.column_dimensions[col].width = width
ws.freeze_panes = "A5"

# --------------------------------------------------------------- sections ---
ss = wb.create_sheet("Sections")
ss["A1"] = "Sections and the strand / course each one teaches"
ss["A1"].font = Font(bold=True, size=12, color="1D4ED8")
ss["A2"] = "A student is placed in the section whose strand matches the strand written on their sheet."
ss["A2"].font = Font(size=9, italic=True, color="4B5563")

sheaders = ["Section", "Year level", "Strand", "Course", "Enrolled"]
for i, h in enumerate(sheaders, start=1):
    cell = ss.cell(4, i, h)
    cell.font = WHITE
    cell.fill = BLUE
    cell.border = THIN

r = 5
for sec in Section.objects.all().order_by("level_type", "grade_year", "name"):
    ss.cell(r, 1, sec.name)
    ss.cell(r, 2, sec.grade_year or "-")
    ss.cell(r, 3, sec.strand.name if sec.strand_id else "-")
    ss.cell(r, 4, sec.course.name if sec.course_id else "-")
    ss.cell(r, 5, Student.objects.filter(section=sec.name).count())
    for c in range(1, 6):
        cell = ss.cell(r, c)
        cell.border = THIN
        cell.font = Font(size=9)
        if r % 2 == 0:
            cell.fill = PatternFill("solid", fgColor="F8FAFC")
    r += 1

for col, width in zip("ABCDE", (14, 16, 42, 34, 12)):
    ss.column_dimensions[col].width = width
ss.freeze_panes = "A5"

# keep the enrollment sheet first
wb.move_sheet("Strands & Courses", offset=1)
wb.save(TEMPLATE)
print("updated:", TEMPLATE)
print("sheets:", wb.sheetnames)
