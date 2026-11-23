"""Read the two .xls files in the USAT folder (no pandas here) and report
their strand/course wording."""
import os
import re

USAT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "USAT")
)

FILES = [
    os.path.join(USAT, "college bundle", "ATS 1-Anew.xls"),
    os.path.join(USAT, "college bundle", "STUDENT DATA (HRS 1A).xls"),
]

for path in FILES:
    print("=" * 78)
    print(os.path.basename(path))
    with open(path, "rb") as fh:
        head = fh.read(400)
    print("  magic:", head[:8])
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        print("  -> a real BIFF .xls (needs xlrd)")
        try:
            import xlrd

            book = xlrd.open_workbook(path)
            sheet = book.sheet_by_index(0)
            print("  sheet:", sheet.name, "rows:", sheet.nrows, "cols:", sheet.ncols)
            for r in range(min(4, sheet.nrows)):
                print("   ", [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)])
            # the strand / course column
            headers = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
            for i, h in enumerate(headers):
                if re.search(r"strand|track|course|program", h, re.I):
                    values = []
                    for r in range(1, sheet.nrows):
                        v = str(sheet.cell_value(r, i)).strip()
                        if v and v not in values:
                            values.append(v)
                    print("  [%s] -> %s" % (h, values[:10]))
        except ImportError:
            print("  xlrd is not installed")
    else:
        # it is probably an HTML or CSV file with an .xls name
        text = head.decode("utf-8", "replace")
        print("  -> readable as text, first 200 chars:")
        print("   ", " ".join(text.split())[:200])
