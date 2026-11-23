from django.core.management.base import BaseCommand
import openpyxl
from students.models import Student
from tracks.models import Track, Strand
from datetime import datetime
from django.utils import timezone

class Command(BaseCommand):
    help = 'Import students from an Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        self.stdout.write(f'Importing students from {file_path}...')

        try:
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading file: {e}'))
            return

        # Skip header row
        rows = list(ws.rows)
        header_row = rows[0]
        data_rows = rows[1:]

        created_count = 0
        updated_count = 0
        errors = []

        for row_idx, row in enumerate(data_rows, 2):
            try:
                # Helper to get value
                def get_val(col_idx):
                    val = row[col_idx].value
                    return str(val).strip() if val is not None else None

                lrn = get_val(0)
                if not lrn:
                    continue  # Skip empty rows

                # Personal Info
                first_name = get_val(1)
                middle_name = get_val(2)
                last_name = get_val(3)

                dob_raw = row[4].value
                date_of_birth = None
                if dob_raw:
                    if isinstance(dob_raw, datetime):
                        date_of_birth = dob_raw.date()
                    elif isinstance(dob_raw, str):
                        try:
                            date_of_birth = datetime.strptime(dob_raw, '%Y-%m-%d').date()
                        except ValueError:
                            pass # Keep as None if invalid format

                gender = get_val(5)
                nationality = get_val(6)
                address = get_val(7)
                contact_number = get_val(8)
                email = get_val(9)

                # Guardian Info
                guardian_name = get_val(10)
                guardian_relationship = get_val(11)
                guardian_contact = get_val(12)

                # Academic Info
                level_type = get_val(13)
                grade_level_raw = get_val(14)
                track_course_code = get_val(15)
                section = get_val(16)

                enrollment_status = get_val(17) or 'New'

                # Process Academic Info
                shs_grade = None
                college_year = None
                current_grade_level = None
                strand = None
                course = None

                if level_type == 'SHS':
                    shs_grade = grade_level_raw
                    current_grade_level = f"Grade {shs_grade}"

                    # Try to find strand by code
                    if track_course_code:
                        try:
                            strand = Strand.objects.get(code=track_course_code)
                        except Strand.DoesNotExist:
                            errors.append(f"Row {row_idx}: Strand code '{track_course_code}' not found")

                elif level_type == 'COL':
                    college_year = grade_level_raw
                    current_grade_level = f"College {college_year} Year"  # e.g., "College 1st Year" - needs conversion maybe

                    # Convert simple numbers to ordinal strings?
                    # Model expects: "1st Year", "2nd Year", "3rd Year", "4th Year" in choices
                    # But the field stores "1", "2", "3", "4" for `college_year`

                    year_map = {"1": "1st Year", "2": "2nd Year", "3": "3rd Year", "4": "4th Year"}
                    if college_year in year_map:
                         current_grade_level = f"College {year_map[college_year]}"

                    # Try to find strand (as course) or just set course name
                    if track_course_code:
                        # Try finding a strand/course matching the code
                        course = track_course_code # Default to using the code as course name

                        # Use code to lookup specific college strands if they are modeled that way
                        # In our updated setup, we have strands for college too (BSCS, BSA)
                        # So let's try to lookup strand first
                        try:
                            found_strand = Strand.objects.filter(code=track_course_code).first()
                            if found_strand:
                                strand = found_strand
                                course = found_strand.name # Use strand name as course name
                        except:
                            pass

                # Prepare student data
                student_data = {
                    'first_name': first_name,
                    'middle_name': middle_name,
                    'last_name': last_name,
                    'date_of_birth': date_of_birth,
                    'gender': gender,
                    'nationality': nationality,
                    'address': address,
                    'contact_number': contact_number,
                    'email': email,
                    'guardian_name': guardian_name,
                    'guardian_relationship': guardian_relationship,
                    'guardian_contact': guardian_contact,
                    'level_type': level_type,
                    'shs_grade': shs_grade,
                    'college_year': college_year,
                    'current_grade_level': current_grade_level,
                    'strand': strand,
                    'section': section,
                    'course': course,
                    'enrollment_status': enrollment_status,
                }

                # Update or Create
                student, created = Student.objects.update_or_create(
                    lrn=lrn,
                    defaults=student_data
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                errors.append(f"Row {row_idx}: Error processing - {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'Import completed.'))
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')

        if errors:
            self.stdout.write(self.style.WARNING(f'Errors encountered ({len(errors)}):'))
            for error in errors:
                self.stdout.write(error)
