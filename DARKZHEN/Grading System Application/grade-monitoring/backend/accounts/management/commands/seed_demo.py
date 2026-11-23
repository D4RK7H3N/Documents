from django.core.management.base import BaseCommand

from academics.models import ClassAssignment, Section, StudentProfile, Subject
from academics.serializers import create_student
from accounts.models import User
from grading import engine
from grading.models import GradingConfig


class Command(BaseCommand):
    help = "Create demo data for local development and evaluation."

    def handle(self, *args, **options):
        if User.objects.filter(username="admin").exists():
            self.stdout.write(self.style.WARNING("Demo data already exists. Skipping."))
            return

        GradingConfig.objects.get_or_create(
            is_active=True,
            defaults={
                "name": "DepEd Order 8, s. 2015",
                "weights": engine.DEFAULT_WEIGHTS,
                "transmutation_table": engine.DEPED_TRANSMUTATION_TABLE,
            },
        )

        admin = User.objects.create_user(username="admin", password="adminpass123", role="admin")
        admin.must_change_password = False
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        section = Section.objects.create(name="Lovelace", school_year="2026-2027")
        subjects_data = [
            ("General Physics 1", "core"),
            ("General Chemistry 1", "core"),
            ("General Biology 1", "core"),
        ]
        teachers = {}
        temp_passwords = []
        for username in ("teacher1", "teacher2", "teacher3"):
            teacher = User.objects.create_user(username=username, role="teacher")
            password = teacher.set_temporary_password()
            teachers[username] = teacher
            temp_passwords.append((username, password))
        for index, (subject_name, subject_type) in enumerate(subjects_data):
            subject = Subject.objects.create(name=subject_name, subject_type=subject_type)
            teacher = teachers[f"teacher{index + 1}"]
            ClassAssignment.objects.create(
                subject=subject, section=section, teacher=teacher, school_year="2026-2027"
            )

        student_names = [
            "Juan Miguel Dela Cruz",
            "Maria Isabel Santos",
            "Pedro Rafael Ramos",
            "Ana Lorraine Flores",
            "Jose Antonio Reyes",
            "Krizzia Mae Bautista",
            "Daniel Patrick Gonzales",
            "Sophia Elaine Villanueva",
        ]
        student_passwords = []
        for i, full_name in enumerate(student_names, start=1):
            lrn = f"13600000000{i:02d}"
            profile, password = create_student(
                lrn=lrn,
                full_name=full_name,
                section_id=section.id,
                created_by=admin,
            )
            student_passwords.append((profile.lrn, profile.full_name, password))

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write("Admin login: admin / adminpass123 (change this in production)")
        self.stdout.write("Teacher and student temporary passwords (change at first login):")
        for username, password in temp_passwords:
            self.stdout.write(f"  teacher {username}: {password}")
        for lrn, name, password in student_passwords:
            self.stdout.write(f"  student {lrn} ({name}): {password}")
        self.stdout.write(f"Students created: {StudentProfile.objects.count()}")
