from django.core.management.base import BaseCommand
from students.models import Student
from django.utils import timezone
from decimal import Decimal

SHS_TUITION = Decimal("10000")
BUN_TUITION = Decimal("15000")

SAMPLE_STUDENTS = [
    # SHS - Grade 11
    {"lrn": "123456000001", "first_name": "Juan", "last_name": "Dela Cruz", "level_type": "SHS", "shs_grade": "11", "current_grade_level": "Grade 11", "section": "St. Augustine", "strand_code": "STEM", "tuition": SHS_TUITION, "paid": SHS_TUITION},
    {"lrn": "123456000002", "first_name": "Maria", "last_name": "Santos", "level_type": "SHS", "shs_grade": "11", "current_grade_level": "Grade 11", "section": "St. Augustine", "strand_code": "STEM", "tuition": SHS_TUITION, "paid": SHS_TUITION // 2},
    {"lrn": "123456000003", "first_name": "Jose", "last_name": "Reyes", "level_type": "SHS", "shs_grade": "11", "current_grade_level": "Grade 11", "section": "St. Monica", "strand_code": "ABM", "tuition": SHS_TUITION, "paid": 0},
    {"lrn": "123456000004", "first_name": "Ana", "last_name": "Gonzales", "level_type": "SHS", "shs_grade": "11", "current_grade_level": "Grade 11", "section": "St. Monica", "strand_code": "ABM", "tuition": SHS_TUITION, "paid": SHS_TUITION},
    {"lrn": "123456000005", "first_name": "Pedro", "last_name": "Villanueva", "level_type": "SHS", "shs_grade": "11", "current_grade_level": "Grade 11", "section": "St. Jerome", "strand_code": "HUMSS", "tuition": SHS_TUITION, "paid": 0},
    # SHS - Grade 12
    {"lrn": "123456000006", "first_name": "Luisa", "last_name": "Mendoza", "level_type": "SHS", "shs_grade": "12", "current_grade_level": "Grade 12", "section": "St. Thomas", "strand_code": "STEM", "tuition": SHS_TUITION, "paid": SHS_TUITION},
    {"lrn": "123456000007", "first_name": "Carlos", "last_name": "Fernandez", "level_type": "SHS", "shs_grade": "12", "current_grade_level": "Grade 12", "section": "St. Thomas", "strand_code": "STEM", "tuition": SHS_TUITION, "paid": SHS_TUITION * 3 // 4},
    {"lrn": "123456000008", "first_name": "Sofia", "last_name": "Lopez", "level_type": "SHS", "shs_grade": "12", "current_grade_level": "Grade 12", "section": "St. Francis", "strand_code": "ABM", "tuition": SHS_TUITION, "paid": SHS_TUITION // 2},
    {"lrn": "123456000009", "first_name": "Miguel", "last_name": "Torres", "level_type": "SHS", "shs_grade": "12", "current_grade_level": "Grade 12", "section": "St. Francis", "strand_code": "ABM", "tuition": SHS_TUITION, "paid": 0},
    {"lrn": "123456000010", "first_name": "Isabella", "last_name": "Ramos", "level_type": "SHS", "shs_grade": "12", "current_grade_level": "Grade 12", "section": "St. Dominic", "strand_code": "HUMSS", "tuition": SHS_TUITION, "paid": Decimal("500")},
    # Bundled - 1st Year
    {"lrn": "123456000011", "first_name": "Andres", "last_name": "Bonifacio", "level_type": "BUN", "college_year": "1", "current_grade_level": "College 1st Year", "section": "Pasko", "course": "BSCS", "tuition": BUN_TUITION, "paid": BUN_TUITION},
    {"lrn": "123456000012", "first_name": "Emilio", "last_name": "Aguinaldo", "level_type": "BUN", "college_year": "1", "current_grade_level": "College 1st Year", "section": "Pasko", "course": "BSCS", "tuition": BUN_TUITION, "paid": BUN_TUITION // 4},
    {"lrn": "123456000013", "first_name": "Gabriela", "last_name": "Silang", "level_type": "BUN", "college_year": "1", "current_grade_level": "College 1st Year", "section": "Masarap", "course": "BSBA", "tuition": BUN_TUITION, "paid": 0},
    # Bundled - 2nd Year
    {"lrn": "123456000014", "first_name": "Jose", "last_name": "Rizal", "level_type": "BUN", "college_year": "2", "current_grade_level": "College 2nd Year", "section": "Taal", "course": "BSCS", "tuition": BUN_TUITION, "paid": BUN_TUITION},
    {"lrn": "123456000015", "first_name": "Marcelo", "last_name": "Del Pilar", "level_type": "BUN", "college_year": "2", "current_grade_level": "College 2nd Year", "section": "Taal", "course": "BSCS", "tuition": BUN_TUITION, "paid": BUN_TUITION // 2},
]


class Command(BaseCommand):
    help = "Seed 15 sample students (SHS Grade 11/12 + Bundled 1st/2nd Year)"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete all existing students first")

    def handle(self, *args, **options):
        from tracks.models import Strand, Track
        from tuition.models import TuitionPayment
        from datetime import date

        # Auto-create tracks and strands if missing
        for code, name in [("STEM", "Science, Technology, Engineering, and Mathematics"), ("ABM", "Accountancy, Business, and Management"), ("HUMSS", "Humanities and Social Sciences"), ("BSCS", "Bachelor of Science in Computer Science"), ("BSBA", "Bachelor of Science in Business Administration")]:
            track, _ = Track.objects.get_or_create(name="Senior High School" if code in ("STEM", "ABM", "HUMSS") else "Bundled College", defaults={"code": "SHS" if code in ("STEM", "ABM", "HUMSS") else "BUN"})
            Strand.objects.get_or_create(code=code, defaults={"name": name, "track": track})

        if options["clear"]:
            confirm = input("Delete ALL existing students? (yes/no): ")
            if confirm.lower() == "yes":
                TuitionPayment.objects.all().delete()
                Student.objects.all().delete()
                self.stdout.write(self.style.WARNING("Deleted all students and payments"))
            else:
                self.stdout.write("Skipped deletion")

        created = 0
        skipped = 0

        for data in SAMPLE_STUDENTS:
            lrn = data["lrn"]
            if Student.objects.filter(lrn=lrn).exists():
                self.stdout.write(f"  SKIP LRN {lrn} — already exists")
                skipped += 1
                continue

            tuition = data.pop("tuition", Decimal("0"))
            paid = data.pop("paid", Decimal("0"))
            strand_code = data.pop("strand_code", None)
            strand = None
            if strand_code:
                strand = Strand.objects.filter(code=strand_code).first()

            student = Student.objects.create(
                lrn=lrn,
                first_name=data["first_name"],
                middle_name="",
                last_name=data["last_name"],
                level_type=data["level_type"],
                shs_grade=data.get("shs_grade"),
                college_year=data.get("college_year"),
                current_grade_level=data["current_grade_level"],
                section=data["section"],
                strand=strand,
                course=data.get("course", ""),
                custom_tuition_fee=tuition,
                tuition_balance=tuition - paid,
                enrollment_status="New",
                status="Active",
                student_type="Payee",
                date_of_enrollment=timezone.now().date(),
            )

            # Create payment record if initial payment > 0
            if paid > 0:
                from django.db import connection
                has_ref_col = "reference_number" in [c.name for c in TuitionPayment._meta.get_fields()]
                pay_kwargs = {
                    "student": student,
                    "amount": paid,
                    "method": "Cash",
                    "payment_date": date.today(),
                    "payment_method": "Cash",
                    "remarks": "Initial payment upon enrollment",
                }
                if has_ref_col:
                    pay_kwargs["reference_number"] = f"RCT-{timezone.now().strftime('%Y%m%d')}-{created + 1:04d}"
                TuitionPayment.objects.create(**pay_kwargs)

            created += 1
            self.stdout.write(f"  OK   LRN {lrn} — {student.first_name} {student.last_name} (₱{tuition} / paid ₱{paid})")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Created: {created}, Skipped: {skipped}"))
