import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from students.models import Student  # noqa: E402
from tuition.models import TuitionPayment  # noqa: E402
from payments.models import Payment  # noqa: E402
from assessment.models import AssessmentPayment  # noqa: E402
from sales.models import Sale, Disbursement  # noqa: E402
from tracks.models import Section  # noqa: E402

print("students          :", Student.objects.count())
print("tuition payments  :", TuitionPayment.objects.count())
print("general payments  :", Payment.objects.count())
print("assessment pays   :", AssessmentPayment.objects.count())
print("sales             :", Sale.objects.count())
print("disbursements     :", Disbursement.objects.count())
print("sections          :", Section.objects.count())

# every money row must belong to a student that still exists
from django.db.models import Sum  # noqa: E402

orphan_tuition = TuitionPayment.objects.filter(student__isnull=True).count()
orphan_general = Payment.objects.filter(student__isnull=True).count()
print("orphan tuition rows:", orphan_tuition)
print("orphan general rows:", orphan_general)
