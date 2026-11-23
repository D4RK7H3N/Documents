from django.core.management.base import BaseCommand
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

class Command(BaseCommand):
    help = 'Generates an Excel template for bulk student upload'

    def handle(self, *args, **kwargs):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student Data Enrollment"

        # Define headers
        headers = [
            # Personal Information
            "LRN", "First Name", "Middle Name", "Last Name",
            "Date of Birth (YYYY-MM-DD)", "Gender", "Nationality",
            "Address", "Contact Number", "Email",

            # Guardian Information
            "Guardian Name", "Guardian Relationship", "Guardian Contact",

            # Academic Information
            "Level Type (SHS/BUN)", "Grade/Year Level",
            "Track/Course Code", "Section",

            # Financial Information
            "Tuition Fee (leave blank for 0; assign manually)",

            # Other
            "Enrollment Status"
        ]

        # Write headers
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # Adjust column width based on header length
            ws.column_dimensions[get_column_letter(col_num)].width = len(header) + 5

        # Add Data Validation for Gender
        gender_dv = DataValidation(type="list", formula1='"Male,Female"', allow_blank=True)
        ws.add_data_validation(gender_dv)
        gender_dv.add('F2:F1000')

        # Add Data Validation for Level Type
        level_dv = DataValidation(type="list", formula1='"SHS,BUN"', allow_blank=True)
        ws.add_data_validation(level_dv)
        level_dv.add('N2:N1000')

        # Add Data Validation for Enrollment Status
        status_dv = DataValidation(type="list", formula1='"New,Continuing,Transferee,ALS Graduate"', allow_blank=True)
        ws.add_data_validation(status_dv)
        status_dv.add('R2:R1000')

        # Add sample rows with different scenarios
        sample_data = [
            # Grade 11 students with tuition
            [
                "123456789012", "Juan", "Moreno", "Dela Cruz",
                "2005-05-15", "Male", "Filipino",
                "123 Sample St., Manila", "09171234567", "juan@example.com",
                "Maria Dela Cruz", "Mother", "09181234567",
                "SHS", "11", "STEM", "Einstein",
                "",  # Tuition for Grade 11
                "New"
            ],
            [
                "123456789016", "Carlos", "Antonio", "Lopez",
                "2005-08-20", "Male", "Filipino",
                "234 Main St., Pasig", "09171234571", "carlos@example.com",
                "Elena Lopez", "Mother", "09181234571",
                "SHS", "11", "STEM", "Einstein",
                "",
                "New"
            ],
            [
                "123456789017", "Sofia", "Marie", "Alvarez",
                "2005-02-14", "Female", "Filipino",
                "345 Oak Ave., Makati", "09171234572", "sofia@example.com",
                "Roberto Alvarez", "Father", "09181234572",
                "SHS", "11", "ABM", "Galileo",
                "",
                "Continuing"
            ],
            [
                "123456789018", "Miguel", "Jose", "Rodriguez",
                "2005-11-30", "Male", "Filipino",
                "456 Pine Rd., Taguig", "09171234573", "miguel@example.com",
                "Carmen Rodriguez", "Mother", "09181234573",
                "SHS", "11", "HUMSS", "Newton",
                "",
                "Transferee"
            ],
            [
                "123456789019", "Isabella", "Grace", "Torres",
                "2005-06-18", "Female", "Filipino",
                "567 Elm St., Paranaque", "09171234574", "isabella@example.com",
                "Fernando Torres", "Father", "09181234574",
                "SHS", "11", "GAS", "Darwin",
                "",
                "New"
            ],
            # Grade 12 students with tuition
            [
                "123456789013", "Maria", "Santos", "Garcia",
                "2004-03-20", "Female", "Filipino",
                "456 Sample Ave., Quezon City", "09181234568", "maria@example.com",
                "Jose Garcia", "Father", "09191234568",
                "SHS", "12", "HUMSS", "Newton",
                "",  # Tuition for Grade 12
                "Continuing"
            ],
            [
                "123456789020", "Diego", "Luis", "Fernandez",
                "2004-09-12", "Male", "Filipino",
                "678 Maple Dr., Mandaluyong", "09171234575", "diego@example.com",
                "Patricia Fernandez", "Mother", "09181234575",
                "SHS", "12", "STEM", "Einstein",
                "",
                "Continuing"
            ],
            [
                "123456789021", "Gabriela", "Isabel", "Mendoza",
                "2004-04-05", "Female", "Filipino",
                "789 Cedar Ln., Pasay", "09171234576", "gabriela@example.com",
                "Ricardo Mendoza", "Father", "09181234576",
                "SHS", "12", "ABM", "Galileo",
                "",
                "Continuing"
            ],
            [
                "123456789022", "Lucas", "Gabriel", "Castillo",
                "2004-12-22", "Male", "Filipino",
                "890 Birch Ave., San Juan", "09171234577", "lucas@example.com",
                "Victoria Castillo", "Mother", "09181234577",
                "SHS", "12", "TVL", "Edison",
                "",
                "ALS Graduate"
            ],
            [
                "123456789023", "Valentina", "Rosa", "Morales",
                "2004-07-08", "Female", "Filipino",
                "901 Willow St., Marikina", "09171234578", "valentina@example.com",
                "Javier Morales", "Father", "09181234578",
                "SHS", "12", "HUMSS", "Newton",
                "",
                "Continuing"
            ],
            # Bundled program students with tuition (16,000)
            [
                "123456789015", "Ana", "Cruz", "Ramos",
                "2004-11-25", "Female", "Filipino",
                "321 University Rd., Makati", "09221234570", "ana@example.com",
                "Carlos Ramos", "Father", "09231234570",
                "BUN", "1", "BUNDLE", "Edison",
                "",  # Tuition for bundled
                "New"
            ],
            [
                "123456789028", "Daniel", "Rafael", "Ortiz",
                "2004-08-16", "Male", "Filipino",
                "456 Bridge Rd., Caloocan", "09171234583", "daniel@example.com",
                "Mercedes Ortiz", "Mother", "09181234583",
                "BUN", "1", "BUNDLE", "Edison",
                "",
                "New"
            ],
            [
                "123456789029", "Emma", "Lucia", "Ruiz",
                "2003-12-03", "Female", "Filipino",
                "567 Highway Ave., Valenzuela", "09171234584", "emma@example.com",
                "Francisco Ruiz", "Father", "09181234584",
                "BUN", "2", "BUNDLE", "Edison",
                "",
                "Continuing"
            ],
            [
                "123456789030", "Adrian", "Carlos", "Herrera",
                "2004-02-28", "Male", "Filipino",
                "678 Central St., Malabon", "09171234585", "adrian@example.com",
                "Teresa Herrera", "Mother", "09181234585",
                "BUN", "1", "BUNDLE", "Edison",
                "",
                "Transferee"
            ],
            [
                "123456789031", "Pedro", "Miguel", "Santos",
                "2004-06-10", "Male", "Filipino",
                "789 College St., Manila", "09201234569", "pedro@example.com",
                "Ana Santos", "Mother", "09211234569",
                "BUN", "1", "BUNDLE", "Edison",
                "",
                "New"
            ],
            [
                "123456789032", "Andrea", "Nicole", "Jimenez",
                "2003-01-15", "Female", "Filipino",
                "012 University Blvd., BGC", "09171234579", "andrea@example.com",
                "Manuel Jimenez", "Father", "09181234579",
                "BUN", "2", "BUNDLE", "Edison",
                "",
                "Continuing"
            ],
            [
                "123456789033", "Sebastian", "Miguel", "Navarro",
                "2004-10-28", "Male", "Filipino",
                "123 Campus Dr., Ortigas", "09171234580", "sebastian@example.com",
                "Laura Navarro", "Mother", "09181234580",
                "BUN", "1", "BUNDLE", "Edison",
                "",
                "New"
            ]
        ]

        for row_num, row_data in enumerate(sample_data, 2):
            for col_num, value in enumerate(row_data, 1):
                ws.cell(row=row_num, column=col_num).value = value

        # Add Instructions sheet
        instructions_ws = wb.create_sheet("Instructions", 0)
        instructions_ws.column_dimensions['A'].width = 80

        instructions = [
            ("STUDENT UPLOAD TEMPLATE INSTRUCTIONS", Font(size=16, bold=True, color="FFFFFF")),
            ("", None),
            ("IMPORTANT NOTES:", Font(size=12, bold=True)),
            ("", None),
            ("1. TUITION FEE RULES:", Font(size=11, bold=True)),
            ("   - Grade 11 and Grade 12 students: 11,000 tuition", None),
            ("   - Bundled (BUN) program students: 16,000 tuition", None),
            ("   - College (COL) students: NOT INCLUDED (system doesn't support COL)", None),
            ("   - Standard tuition: SHS = 11,000 | BUN = 16,000", None),
            ("", None),
            ("2. REQUIRED FIELDS:", Font(size=11, bold=True)),
            ("   - LRN (12 digits)", None),
            ("   - First Name, Last Name", None),
            ("   - Date of Birth (format: YYYY-MM-DD, example: 2005-05-15)", None),
            ("   - Gender (Male/Female)", None),
            ("   - Level Type (SHS/COL/BUN)", None),
            ("   - Grade/Year Level (11, 12 for SHS; 1, 2, 3, 4 for COL/BUN)", None),
            ("   - Section", None),
            ("   - Enrollment Status (New/Continuing/Transferee/ALS Graduate)", None),
            ("", None),
            ("3. LEVEL TYPES:", Font(size=11, bold=True)),
            ("   - SHS: Senior High School (Grades 11-12) - Tuition: 11,000", None),
            ("   - BUN: Bundled Program (Years 1-2) - Tuition: 16,000", None),
            ("   - Note: COL (College) is not included in this template", None),
            ("", None),
            ("4. SAMPLE DATA:", Font(size=11, bold=True)),
            ("   - See 'Student Data Enrollment' sheet for sample students", None),
            ("   - Grade 11 students: Tuition = 11,000", None),
            ("   - Grade 12 students: Tuition = 11,000", None),
            ("   - Bundled program students: Tuition = 16,000", None),
            ("   - Examples include New, Continuing, Transferee, and ALS Graduate students", None),
            ("", None),
            ("5. DATA VALIDATION:", Font(size=11, bold=True)),
            ("   - Gender, Level Type, and Enrollment Status fields have dropdown menus", None),
            ("   - Use the dropdown to select valid values", None),
        ]

        for row_num, (text, font) in enumerate(instructions, 1):
            cell = instructions_ws.cell(row=row_num, column=1)
            cell.value = text
            if font:
                cell.font = font
            if row_num == 1:
                cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # Save file
        filename = "student_upload_template.xlsx"
        wb.save(filename)

        self.stdout.write(self.style.SUCCESS(f'Successfully generated template: {filename}'))
        self.stdout.write(self.style.SUCCESS('Template includes:'))
        self.stdout.write(self.style.SUCCESS('  - Instructions sheet with tuition rules'))
        self.stdout.write(self.style.SUCCESS('  - Sample data for Grade 11, Grade 12, College, and Bundled students'))
        self.stdout.write(self.style.SUCCESS('  - Data validation for dropdown fields'))
