"""Read every student file in the USAT folder and report what the school
actually uses: the headers, the strand/track wording and the row counts."""
import os
import csv
import glob
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

try:
    import openpyxl
except ImportError:
    openpyxl = None

USAT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "USAT")
)


def read_csv(path):
    rows = []
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, newline="", encoding=encoding) as fh:
                return list(csv.reader(fh))
        except UnicodeDecodeError:
            continue
    return rows


def read_xlsx(path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            rows.append(list(row))
    wb.close()
    return rows


def read_xls(path):
    try:
        import pandas as pd

        df = pd.read_excel(path, header=None, dtype=str)
        return df.fillna("").values.tolist()
    except Exception as exc:
        return [["<cannot read .xls: %s>" % exc]]


def cell_text(value):
    if value is None:
        return ""
    return str(value).strip()


def headers_of(rows):
    """Find the header row: the first row with the most filled cells."""
    best = 0
    best_index = 0
    for i, row in enumerate(rows[:12]):
        filled = sum(1 for c in row if cell_text(c))
        if filled > best:
            best = filled
            best_index = i
    return best_index, [cell_text(c) for c in rows[best_index]]


for path in sorted(glob.glob(os.path.join(USAT, "**", "*"), recursive=True)):
    if os.path.isdir(path) or path.lower().endswith((".txt", ".md")):
        continue
    name = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        rows = read_csv(path)
    elif ext == ".xlsx":
        rows = read_xlsx(path)
    elif ext == ".xls":
        rows = read_xls(path)
    else:
        continue

    hi, headers = headers_of(rows)
    print("")
    print("=" * 78)
    print("%s" % os.path.relpath(path, USAT))
    print("  rows: %d   header row: %d" % (max(0, len(rows) - hi - 1), hi + 1))
    print("  headers: %s" % " | ".join(h for h in headers if h))
    # the columns that look like a strand / track / programme
    for i, h in enumerate(headers):
        low = h.lower()
        if any(k in low for k in ("strand", "track", "program", "course", "special")):
            values = []
            for row in rows[hi + 1 : hi + 1 + 400]:
                if i < len(row):
                    v = cell_text(row[i])
                    if v and v not in values:
                        values.append(v)
            print("  [%s] -> %s" % (h, values[:12]))
