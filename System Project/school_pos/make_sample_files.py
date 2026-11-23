"""
Write sample students to FILES (not to the database) so they can be imported
through the app: one workbook per section, plus a combined workbook and CSV.

Every section the school has is filled with students, in the class sizes the
school uses: 35 for the SHS sections, 25 for the bundled (TESDA) ones. That
is 17 x 35 + 6 x 25 = 745 students.

The columns are the ones the importer understands:

    LRN | Last Name | First Name | Middle Name | Sex | Birthdate | Address |
    Contact Number | Guardian Name | Contact Number | Section | Strand |
    Grade Level | School Year | Tuition | Amount Paid | Payment Method

(The two "Contact Number" columns are the student's and the guardian's -
that is how the school's own sheet is laid out, and the importer picks them
apart by position.)

The class size follows what the school says: 35 for the SHS sections, 25 for
the bundled (TESDA) ones. The bundled sections carry their course in the
Strand column, because they have no strand.

Files are written to the sample_data folder next to the project.
"""
import csv
import datetime
import os
import random

from openpyxl import Workbook

import django

django.setup()

from tracks.models import Section

TOTAL = 200
CLASS_SIZE = {"SHS": 35, "BUN": 25, "COL": 35}
SCHOOL_YEAR = "2026-2027"

FEES = {
    "Grade 11": 12000,
    "Grade 12": 11000,
    "1st Year": 9000,
    "2nd Year": 9500,
}

HEADERS = [
    "LRN",
    "Last Name",
    "First Name",
    "Middle Name",
    "Sex",
    "Birthdate",
    "Address",
    "Contact Number",
    "Guardian Name",
    "Contact Number",
    "Section",
    "Strand",
    "Grade Level",
    "School Year",
    "Tuition",
    "Amount Paid",
    "Payment Method",
]

MALE_FIRST = [
    "Juan", "Jose", "Mark", "John Paul", "Carlo", "Mark Anthony", "Christian",
    "Jayson", "Jason", "Joshua", "Paul", "Patrick", "Angelo", "Arnel", "Renz",
    "Rodrigo", "Miguel", "Francis", "Jay", "Alden", "Noel", "Ramon", "Efren",
    "Jerome", "Kevin", "Brian", "Dennis", "Oscar", "Ricky", "Daryl", "Gerald",
    "Michael", "Jomar", "Ivan", "Ralph", "Wendell", "Lloyd", "Ferdinand",
    "Adrian", "Emmanuel", "Alfonso", "Crisanto", "Danilo", "Artemio",
    "Benigno", "Norberto", "Teodoro", "Roderick", "Salvador", "Virgilio",
]
FEMALE_FIRST = [
    "Maria", "Angel", "Kristine", "Nicole", "Grace", "Jennylyn", "Juvy",
    "Jenna", "Jhesica", "Joy", "Kyla", "Kim", "Camille", "Bea", "Rhea",
    "Angela", "Shaira", "Trisha", "Charmaine", "Lea", "Diana", "Veronica",
    "Jasmine", "Marilou", "Rowena", "Analyn", "Aiko", "Cecilia", "Ferdie",
    "Hazel", "Katrina", "Lovely", "Ma. Elena", "Nerissa", "Odette", "Pamela",
    "Rachelle", "Sheila", "Tiffany", "Vanessa", "Yara", "Zsa Zsa", "Richelle",
    "Mary Joy", "Krystel", "Claudine", "Danica", "Eliza", "Irish", "Jolina",
]
MIDDLE = [
    "Santos", "Reyes", "Cruz", "Bautista", "Villanueva", "Ramos", "Mendoza",
    "Garcia", "Aquino", "Torres", "Castillo", "Flores", "Gonzales",
    "Mercado", "Salazar", "Domingo", "Pascual", "Aguilar",
]
LAST = [
    "Dela Cruz", "Dela Rosa", "Santos", "Reyes", "Cruz", "Bautista",
    "Villanueva", "Ramos", "Mendoza", "Garcia", "Aquino", "Torres",
    "Castillo", "Flores", "Gonzales", "Mercado", "Salazar", "Domingo",
    "Pascual", "Aguilar", "Bumanglag", "Canedo", "Decutor", "Endriga",
    "Fabella", "Gabato", "Hondrade", "Iznares", "Jamora", "Kinagat",
    "Lacorte", "Magsaysay", "Natividad", "Oclarit", "Pangilinan", "Quiambao",
    "Roxas", "Sumad", "Tabotabo", "Uy", "Villaflor", "Yabores", "Zamora",
    "Bacsain", "Cagoco", "Dacoy", "Galinato", "Heredia", "Lanuza", "Macalit",
    "Nepomuceno", "Orbeta",
]
BARANGAYS = [
    "Old Sagay", "Poblacion 1", "Poblacion 2", "Bacong", "Bato", "Payapa",
    "Hinulaman", "Buala", "Magtulis", "San Isidro", "Santo Niño", "Mabini",
    "Tanza", "Lagtala", "Cagay-og", "Guiljuran",
]
STREETS = [
    "Rizal Street", "Bonifacio Street", "Mabini Street", "Del Pilar Street",
    "Luna Street", "Araullo Street", "P. Burgos Street", "Sampaguita",
]

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # run through exec() without a file context
    HERE = os.getcwd()
OUT_DIR = os.path.join(os.path.dirname(HERE), "sample_data")


def order_sections():
    """Grade 11, Grade 12, 1st Year and 2nd Year are taken in turn, so the
    sample data shows every year level."""
    by_grade = {}
    for s in Section.objects.all():
        by_grade.setdefault((s.level_type, s.grade_year), []).append(s)

    groups = []
    for level_type in ("SHS", "BUN", "COL"):
        for grade in ("Grade 11", "Grade 12", "1st Year", "2nd Year"):
            groups.append(by_grade.get((level_type, grade), []))

    ordered = []
    longest = max((len(g) for g in groups), default=0)
    for index in range(longest):
        for group in groups:
            if index < len(group):
                ordered.append(group[index])
    return ordered


def birthdate(rng, level_type, grade):
    today = datetime.date.today()
    if level_type == "SHS":
        age = 17 if grade == "Grade 12" else 16
    else:
        age = 20 if grade == "2nd Year" else 19
    return today - datetime.timedelta(days=age * 365 + rng.randint(0, 364))


def make_rows(sections, rng, used_lrn):
    """One list of rows per section. Every section is filled to its class
    size - the school asked for all of them to have students."""
    first_names = MALE_FIRST + FEMALE_FIRST
    used_names = set()
    per_section = {}
    total = 0

    for section in sections:
        size = CLASS_SIZE.get(section.level_type, 35)
        grade = section.grade_year or ""
        fee = FEES.get(grade, 9000)
        strand = section.strand.name if section.strand else (
            section.course.name if section.course else ""
        )
        rows = []

        for _ in range(size):
            while True:
                first = rng.choice(first_names)
                middle = rng.choice(MIDDLE)
                last = rng.choice(LAST)
                if (first, middle, last) not in used_names:
                    used_names.add((first, middle, last))
                    break
            while True:
                value = "00" + "".join(rng.choice("0123456789") for _ in range(10))
                if value not in used_lrn:
                    used_lrn.add(value)
                    break

            # Some of them have tuition paid: some in full, some in part.
            roll = rng.random()
            if roll < 0.35:
                paid = fee
            elif roll < 0.60:
                paid = int(fee * rng.randint(25, 75) / 100)
            else:
                paid = 0

            contact = f"09{rng.randint(10, 99)}{rng.randint(1000000, 9999999)}"
            guardian_contact = f"09{rng.randint(10, 99)}{rng.randint(1000000, 9999999)}"
            rows.append([
                value,
                last,
                first,
                middle,
                "M" if first in MALE_FIRST else "F",
                birthdate(rng, section.level_type, grade).isoformat(),
                f"{rng.choice(STREETS)}, Brgy. {rng.choice(BARANGAYS)}, Sagay City, Negros Occidental",
                contact,
                f"{rng.choice(first_names)} {last}",
                guardian_contact,
                section.name,
                strand,
                grade,
                SCHOOL_YEAR,
                fee,
                paid,
                rng.choice(["Cash", "GCash", "Bank Transfer"]) if paid else "",
            ])
        per_section[section.name] = rows
        total += len(rows)
    return per_section, total


def write_workbook(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)
    widths = [14, 20, 16, 18, 6, 13, 52, 16, 22, 16, 14, 40, 13, 13, 11, 13, 16]
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=index).column_letter].width = width
    ws.freeze_panes = "A2"
    wb.save(path)


def main():
    rng = random.Random(20261110)
    os.makedirs(OUT_DIR, exist_ok=True)

    sections = order_sections()
    if not sections:
        print("No sections found - create the classes first.")
        return

    per_section, total = make_rows(sections, rng, set())

    for name, rows in per_section.items():
        path = os.path.join(OUT_DIR, f"{name}.xlsx")
        write_workbook(path, rows)
        print(f"  {name:16} {len(rows):3} students -> {os.path.basename(path)}")

    everything = [row for rows in per_section.values() for row in rows]
    combined = os.path.join(OUT_DIR, "ALL-SAMPLE-STUDENTS.xlsx")
    write_workbook(combined, everything)
    csv_path = os.path.join(OUT_DIR, "ALL-SAMPLE-STUDENTS.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADERS)
        writer.writerows(everything)

    print()
    print(f"total: {total} students")
    print(f"  {len(per_section)} sections, one file each -> {OUT_DIR}")
    print(f"  {os.path.basename(combined)} and {os.path.basename(csv_path)} (everything)")


if __name__ == "__main__":
    main()
