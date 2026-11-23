"""Clear the roster and every transaction that belongs with it.

Used when the school wants a clean slate before the real enrolment starts.
Sections, strands, courses and the school configuration are kept - only the
students and their money rows go.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from students.models import Student  # noqa: E402
from tuition.models import TuitionPayment  # noqa: E402
from payments.models import Payment, StudentCharge  # noqa: E402
from assessment.models import AssessmentType, StudentAssessment, AssessmentPayment  # noqa: E402
from sales.models import Sale, SaleItem, Disbursement, DailyCashReport  # noqa: E402
from dorm.models import DormAssignment, DormPayment  # noqa: E402
from tours.models import TourEnrollment, TourPayment  # noqa: E402
from graduation.models import StudentGraduation, GraduationPayment  # noqa: E402
from tracks.models import Section  # noqa: E402

dry = "--dry-run" in os.sys.argv

models = [
    ("students", Student.objects.all()),
    ("tuition payments", TuitionPayment.objects.all()),
    ("general payments", Payment.objects.all()),
    ("student charges", StudentCharge.objects.all()),
    ("assessment payments", AssessmentPayment.objects.all()),
    ("student assessments", StudentAssessment.objects.all()),
    ("sales", Sale.objects.all()),
    ("sale items", SaleItem.objects.all()),
    ("disbursements", Disbursement.objects.all()),
    ("daily cash reports", DailyCashReport.objects.all()),
    ("dorm payments", DormPayment.objects.all()),
    ("dorm assignments", DormAssignment.objects.all()),
    ("tour payments", TourPayment.objects.all()),
    ("tour enrollments", TourEnrollment.objects.all()),
    ("graduation payments", GraduationPayment.objects.all()),
    ("graduations", StudentGraduation.objects.all()),
]

try:
    from django.contrib.sessions.models import Session

    models.append(("sessions", Session.objects.all()))
except Exception:  # pragma: no cover - sessions app may be off
    pass

total = 0
for label, rows in models:
    count = rows.count()
    total += count
    print("%-22s: %d" % (label, count))
    if not dry and count:
        rows.delete()

print("")
print("%s %d rows in total" % ("would remove" if dry else "removed", total))
print("sections left          : %d" % Section.objects.count())
