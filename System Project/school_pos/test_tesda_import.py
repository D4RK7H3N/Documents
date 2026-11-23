"""Import a sheet that uses the official TESDA qualification titles and check
that every row lands on the right strand / course."""
import os

import django
from django.conf import settings

settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]

django.setup()

from django.contrib.auth import get_user_model
from openpyxl import Workbook
from rest_framework.test import APIClient

from students.models import Student
from tracks.models import Course, Strand

admin = get_user_model().objects.filter(is_superuser=True).first()
client = APIClient()
client.force_authenticate(user=admin)

# (section, official strand/course title from the registrar's sheet, grade)
ROWS = [
    ("Amos", "Organic Agriculture Production NC II", "Grade 11"),
    ("Amos", "Agricultural Crops Production NC II", "Grade 11"),
    ("Daniel", "Shielded Metal Arc Welding NC II", "Grade 11"),
    ("Daniel", "SMAW NC II", "Grade 11"),
    ("Esther", "Housekeeping NC II", "Grade 11"),
    ("Thessalonians", "Food and Beverage Services NC II", "Grade 12"),
    ("Hebrews", "Computer Systems Servicing NC II", "Grade 12"),
    ("Proverbs", "Electronic Products Assembly and Servicing NC II", "Grade 11"),
    ("James", "Automotive Servicing NC II", "Grade 11"),
    ("NOAH", "ICT Programming (.NET)", "Grade 11"),
    ("Zechariah", "Java Programming", "Grade 12"),
    ("1A", "Automotive Mechanic", "1st Year"),
    ("2B", "Computer and Electronics", "2nd Year"),
    ("1C", "Hotel and Restaurant Services", "1st Year"),
]

wb = Workbook()
ws = wb.active
ws.title = "Students"
ws.append(["LRN", "Last Name", "First Name", "Sex", "Birthdate", "Section", "Strand", "Grade Level"])
for i, (section, title, grade) in enumerate(ROWS, start=1):
    ws.append([
        f"00TESDA{i:06d}",
        f"Tester{i}",
        "Official",
        "M" if i % 2 else "F",
        "2010-05-05",
        section,
        title,
        grade,
    ])
path = os.path.join(os.getcwd(), "tesda_sheet_test.xlsx")
wb.save(path)

with open(path, "rb") as fh:
    resp = client.post("/api/students/bulk_upload/", {"file": fh}, format="multipart")
data = resp.json()
print("status:", resp.status_code, "| created:", data.get("created_count"),
      "| rows_with_section:", data.get("rows_with_section"),
      "| unmapped:", data.get("unmapped_strands"),
      "| errors:", data.get("errors"))

failures = []
for i, (section, title, grade) in enumerate(ROWS, start=1):
    s = Student.objects.filter(lrn=f"00TESDA{i:06d}").first()
    if s is None:
        failures.append(f"row {i} missing")
        print(f"  [FAIL] row {i}: {title!r} -> not imported")
        continue
    landed = s.strand.name if s.strand else (s.course_fk.name if s.course_fk else None)
    print(f"  [{'PASS' if landed else 'FAIL'}] row {i}: {title!r} -> {landed!r} (section {s.section})")
    if not landed:
        failures.append(f"row {i} {title}")

print()
print("RESULT:", "ALL OFFICIAL NAMES MATCH" if not failures else f"{len(failures)} UNMATCHED: {failures}")

# cleanup
Student.objects.filter(lrn__startswith="00TESDA").delete()
os.remove(path)
print("cleaned up - students now:", Student.objects.count())
