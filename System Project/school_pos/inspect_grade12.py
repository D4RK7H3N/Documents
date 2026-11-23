"""Dump the structure of the Grade 12 workbook (sheets, headers, first rows)."""
import sys
import datetime

PATH = r"C:\Users\DarkZhen\Documents\System Project\USAT\Grade 12 First Semester S.Y. 2026-2027.xlsx"

try:
    import openpyxl
except ImportError:
    print("openpyxl NOT available")
    sys.exit(2)

wb = openpyxl.load_workbook(PATH, data_only=True)
print("sheets:", wb.sheetnames)
for ws in wb.worksheets:
    print("=" * 70)
    print(f"sheet: {ws.title!r}  dims={ws.dimensions}  max_row={ws.max_row} max_col={ws.max_column}")
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=min(8, ws.max_row), values_only=True), start=1):
        cells = []
        for v in row:
            if isinstance(v, (datetime.datetime, datetime.date)):
                v = v.isoformat()
            cells.append("" if v is None else str(v))
        print(f"  row {i}: {cells}")
