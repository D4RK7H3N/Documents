from django.core.management.base import BaseCommand
from django.utils import timezone
from students.models import Student
from datetime import datetime

class Command(BaseCommand):
    help = 'Automatically update student grades at the end of school year'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )
        parser.add_argument(
            '--month',
            type=int,
            default=3,
            help='Month to run auto-update (default: 3 for March/end of SY)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        current_month = timezone.now().month
        target_month = options['month']

        # Check if current month matches target month
        if current_month != target_month:
            self.stdout.write(
                self.style.WARNING(
                    f'Current month ({current_month}) does not match target month ({target_month}). '
                    f'No updates performed.'
                )
            )
            return

        # Find SHS Grade 11 students
        grade_11_students = Student.objects.filter(
            level_type='SHS',
            shs_grade='11',
            enrollment_status__in=['New', 'Continuing']
        )

        updated_count = 0
        skipped_count = 0

        self.stdout.write(
            self.style.SUCCESS(
                f'Found {grade_11_students.count()} SHS Grade 11 students to update'
            )
        )

        for student in grade_11_students:
            try:
                if dry_run:
                    self.stdout.write(
                        f'[DRY-RUN] Would update: {student.lrn} - {student.first_name} {student.last_name} '
                        f'(Grade {student.shs_grade} → Grade 12)'
                    )
                else:
                    student.shs_grade = '12'
                    student.enrollment_status = 'Continuing'
                    student.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Updated: {student.lrn} - {student.first_name} {student.last_name} '
                            f'(Grade 11 → Grade 12)'
                        )
                    )
                updated_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error updating {student.lrn}: {str(e)}'
                    )
                )
                skipped_count += 1

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count} students'))
        self.stdout.write(self.style.SUCCESS(f'  Skipped: {skipped_count} students'))
        if dry_run:
            self.stdout.write(
                self.style.WARNING('  (DRY-RUN MODE - No changes were actually saved)')
            )
        self.stdout.write(self.style.SUCCESS('='*60))