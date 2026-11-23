from django.core.management.base import BaseCommand
from assessment.models import AssessmentType
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate initial assessment types (NC II certifications, fees, etc.)'

    def handle(self, *args, **options):
        assessment_types = [
            # NC II Certifications
            {
                'name': 'Bartending NC II',
                'code': 'BART',
                'category': 'NCII',
                'description': 'National Certificate II in Bartending',
                'amount': Decimal('5000.00'),
                'applicable_to': 'SHS',
                'applicable_tracks': 'Home Economics',
                'is_required': True,
            },
            {
                'name': 'Automotive Servicing NC II',
                'code': 'AUTO',
                'category': 'NCII',
                'description': 'National Certificate II in Automotive Servicing',
                'amount': Decimal('5000.00'),
                'applicable_to': 'SHS',
                'applicable_tracks': 'Industrial',
                'is_required': True,
            },
            {
                'name': 'Computer Systems Servicing NC II',
                'code': 'CSS',
                'category': 'NCII',
                'description': 'National Certificate II in Computer Systems Servicing',
                'amount': Decimal('5000.00'),
                'applicable_to': 'SHS',
                'applicable_tracks': 'ICT',
                'is_required': True,
            },
            {
                'name': 'Certificate of Enrollment',
                'code': 'COE',
                'category': 'CERT',
                'description': 'Official Certificate of Enrollment',
                'amount': Decimal('100.00'),
                'applicable_to': 'ALL',
                'applicable_tracks': '',
                'is_required': False,
            },
            # Lab Fees
            {
                'name': 'Computer Laboratory Fee',
                'code': 'COMPLAB',
                'category': 'LAB',
                'description': 'Semester computer laboratory usage fee',
                'amount': Decimal('1500.00'),
                'applicable_to': 'ALL',
                'applicable_tracks': 'ICT',
                'is_required': True,
            },
            {
                'name': 'Science Laboratory Fee',
                'code': 'SCILAB',
                'category': 'LAB',
                'description': 'Science laboratory materials and equipment fee',
                'amount': Decimal('1000.00'),
                'applicable_to': 'SHS',
                'applicable_tracks': 'Academic',
                'is_required': True,
            },
            # Bundled College Assessments
            {
                'name': 'Bundled College Assessment',
                'code': 'BUN-ASSESS',
                'category': 'MISC',
                'description': 'Special assessment for bundled college students',
                'amount': Decimal('3000.00'),
                'applicable_to': 'BUN',
                'applicable_tracks': '',
                'is_required': False,
            },
            # Miscellaneous
            {
                'name': 'ID Card',
                'code': 'IDCARD',
                'category': 'MISC',
                'description': 'Student identification card',
                'amount': Decimal('150.00'),
                'applicable_to': 'ALL',
                'applicable_tracks': '',
                'is_required': True,
            },
            {
                'name': 'Uniform',
                'code': 'UNIFORM',
                'category': 'MISC',
                'description': 'School uniform (complete set)',
                'amount': Decimal('2500.00'),
                'applicable_to': 'ALL',
                'applicable_tracks': '',
                'is_required': False,
            },
            {
                'name': 'PE Uniform',
                'code': 'PE-UNIFORM',
                'category': 'MISC',
                'description': 'Physical Education uniform',
                'amount': Decimal('800.00'),
                'applicable_to': 'ALL',
                'applicable_tracks': '',
                'is_required': True,
            },
            # Examination Fees
            {
                'name': 'Entrance Examination',
                'code': 'ENTRANCE',
                'category': 'EXAM',
                'description': 'Entrance examination fee',
                'amount': Decimal('500.00'),
                'applicable_to': 'ALL',
                'applicable_tracks': '',
                'is_required': False,
            },
            {
                'name': 'TESDA Assessment Fee',
                'code': 'TESDA',
                'category': 'EXAM',
                'description': 'TESDA Competency Assessment fee',
                'amount': Decimal('2000.00'),
                'applicable_to': 'SHS',
                'applicable_tracks': 'Industrial, Home Economics, ICT',
                'is_required': True,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for data in assessment_types:
            assessment_type, created = AssessmentType.objects.update_or_create(
                code=data['code'],
                defaults=data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {assessment_type.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated: {assessment_type.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Total: {created_count} created, {updated_count} updated'
            )
        )