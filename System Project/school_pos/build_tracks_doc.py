r"""Build the Track / Strand / Course reference document.

One source of truth (docs/tracks_courses_data.json) -> both a .docx
(python-docx) and an .html that Chromium prints to PDF.

    .venv\Scripts\python.exe build_tracks_doc.py
"""
import os
import json
import datetime

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, "..", "docs"))
DATA = os.path.join(DOCS, "tracks_courses_data.json")

with open(DATA, encoding="utf-8") as fh:
    D = json.load(fh)

SCHOOL = "USAT College Sagay City, Inc."
TITLE = "Track, Strand & Course Reference"
TODAY = datetime.date.today().strftime("%d %B %Y")

# --------------------------------------------------------------------------
# the reference material that is not in the database but belongs with it
# --------------------------------------------------------------------------
OFFICIAL_TITLES = [
    ("SMAW NC I / NC II", "Shielded Metal Arc Welding (NCI & NCII)", "Strand SMAW"),
    ("Electronic Products Assembly and Servicing NC II",
     "Electronic Product Assembly and Servicing (NCII)", "Strand EPAS"),
    ("Computer Systems Servicing NC II", "Computer Service System", "Strand ICT-CSS"),
    ("Food and Beverage Services NC II", "Food and Beverage Servicing (NC II)", "Strand FBS"),
    ("Housekeeping NC II", "House Keeping", "Strand HK"),
    ("Organic Agriculture Production NC II", "Agricultural Crops Production", "Strand ACP"),
    ("Automotive Mechanic (2024 revised title)",
     "Automotive Mechanic", "Course AM - 1st / 2nd Year Bundled"),
    ("Computer and Electronics (2024 revised title)",
     "Computer and Electronics", "Course COMP-E - 1st / 2nd Year Bundled"),
    ("Hotel and Restaurant Services (2024 revised title)",
     "Hotel and Restaurant Services", "Course HRS - 1st / 2nd Year Bundled"),
]

CLUSTERS = [
    ("Industrial Technologies", "welding + electronics + ICT programming",
     "resolved from the student's section - it is a cluster, not one strand"),
    ("Industrial Arts", "SMAW, EPAS, Automotive Servicing", "resolved from the section"),
    ("Home Economics", "Food and Beverage Servicing, House Keeping, Bartending",
     "resolved from the section"),
    ("Agri-Fishery Arts", "Agricultural Crops Production", "resolved from the section"),
    ("Information and Communication Technology",
     "ICT-CSS, ICT (.NET), ICT (JAVA)", "resolved from the section"),
]

IMPORT_RULES = [
    "A strand is matched by its name, its code or any of its aliases - the "
    "school sheet may spell it in the official DepEd / TESDA wording.",
    "A course is matched the same way, by name, code or alias.",
    "A cluster or programme-group name (Industrial Technologies, Home "
    "Economics, Agri-Fishery Arts, ICT) is not a strand. The student inherits "
    "the strand of their SECTION, and the importer says so in its report "
    "(strands_inherited_from_section).",
    "A section is the authority: when a student is moved to a section, they "
    "take that section's strand and year level with them.",
    "A Senior High row carries the strand; a Bundled row carries the course.",
    "Students are matched by LRN, so re-importing the same file updates the "
    "students instead of creating duplicates.",
    "The sheet's own wording for the track is kept as text; the strand itself "
    "comes from the record above.",
]

REFERENCE_NOTES = [
    "The school is a private Senior High institution - DepEd school id "
    "406005 - and is 100 % TVL in the current school year, which matches the "
    "data: one track (TVL), ten strands, and every Senior High section a TVL "
    "specialisation.",
    "The six TESDA-registered programmes that map onto the school's strands "
    "are SMAW, Computer Systems Servicing, Electronic Products Assembly and "
    "Servicing, Food and Beverage Services, Housekeeping and Organic "
    "Agriculture Production.",
    "The three Bundled courses use the 2024 revised TESDA qualification "
    "titles: Automotive Mechanic, Computer and Electronics, and Hotel and "
    "Restaurant Services.",
    "The strands are grouped under the four TVL strands: Industrial Arts "
    "(SMAW, EPAS, Automotive Servicing), ICT (ICT-CSS, ICT (.NET), ICT "
    "(JAVA)), Home Economics (FBS, HK, Bartending) and Agri-Fishery Arts "
    "(ACP).",
    "DepEd Memorandum No. 012, s. 2026 replaces the strand system with the "
    "Strengthened SHS Curriculum (two tracks: Academic and "
    "Technical-Professional, with electives instead of strands). The incoming "
    "Grade 11 falls under it; the Grade 12s stay on the old strands.",
]


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hexcolor)
    tcPr.append(el)


def set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def add_table(doc, headers, rows, widths=None, font=8.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0]
    set_repeat_header(hdr)
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(font)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(cell, "1D4ED8")
    for r in rows:
        cells = t.add_row().cells
        for i, value in enumerate(r):
            cells[i].text = ""
            para = cells[i].paragraphs[0]
            para.paragraph_format.space_after = Pt(1)
            run = para.add_run("" if value is None else str(value))
            run.font.size = Pt(font)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    return t


def h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)
        run.font.name = "Calibri"
    return p


def para(doc, text, size=9.5, italic=False, space=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.italic = italic
    return p


def bullet(doc, text, size=9.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.font.size = Pt(size)
    return p


def build_docx(path):
    doc = Document()
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(1.4)
        section.right_margin = Cm(1.4)
        section.top_margin = Cm(1.4)
        section.bottom_margin = Cm(1.4)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(9.5)

    # ---- cover -----------------------------------------------------------
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(SCHOOL)
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(TITLE)
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = meta.add_run(
        "Track TVL  |  %d strands  |  %d bundled courses  |  %d sections  |  %s"
        % (len(D["strands"]), len(D["courses"]), len(D["sections"]), TODAY)
    )
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)

    doc.add_paragraph()

    # ---- 1. the model ----------------------------------------------------
    h(doc, "1.  How the school is organised", 1)
    para(doc, "Every programme in the school hangs from one of two places:")
    bullet(doc, "A TRACK is the curriculum family. The school has one: "
                "TVL (Technical-Vocational-Livelihood), which is the track "
                "DepEd lists for the school year.")
    bullet(doc, "A STRAND is the specialisation a Senior High student takes "
                "in that track (Shielded Metal Arc Welding, Food and Beverage "
                "Servicing, ...). There are %d." % len(D["strands"]))
    bullet(doc, "A COURSE is the programme a Bundled student takes for the "
                "one or two years of the TESDA track (Automotive Mechanic, "
                "Computer and Electronics, ...). There are %d." % len(D["courses"]))
    bullet(doc, "A SECTION is a class in one year level, and it points at the "
                "strand or course it teaches.")
    para(doc, "The year levels in use: " + ", ".join(D["grade_years"]) + ".",
         italic=True)

    # ---- 2. tracks -------------------------------------------------------
    h(doc, "2.  Tracks", 1)
    add_table(
        doc,
        ["Track", "Code", "Level", "Strands", "Description"],
        [[t["name"], t["code"], t["level_type"], t["strand_count"],
          t["description"] or "-"] for t in D["tracks"]],
        widths=[3.4, 2.0, 2.0, 1.8, 9.0],
    )

    # ---- 3. strands ------------------------------------------------------
    h(doc, "3.  Strands (Senior High)", 1)
    para(doc, "The school uses %d strands, all under the TVL track. The "
              "“Official / alias names” column lists every wording the "
              "registrar's sheets and the DepEd / TESDA lists may use - the "
              "import matches a strand by its name, its code or any of these "
              "aliases." % len(D["strands"]))
    add_table(
        doc,
        ["#", "Strand", "Code", "Official / alias names", "Sections", "Students"],
        [[i + 1, s["name"], s["code"],
          "\n".join(s["aliases"]) if s["aliases"] else "-",
          ", ".join(s["sections"]) if s["sections"] else "-",
          s["students"]] for i, s in enumerate(D["strands"])],
        widths=[0.8, 4.2, 2.0, 7.4, 2.4, 1.6],
        font=8,
    )

    # ---- 4. courses ------------------------------------------------------
    h(doc, "4.  Courses (Bundled / TESDA track)", 1)
    add_table(
        doc,
        ["#", "Course", "Code", "Level", "Official / alias names", "Sections", "Students"],
        [[i + 1, c["name"], c["code"], c["level_type"],
          "\n".join(c["aliases"]) if c["aliases"] else "-",
          ", ".join(c["sections"]) if c["sections"] else "-",
          c["students"]] for i, c in enumerate(D["courses"])],
        widths=[0.8, 3.6, 1.8, 1.6, 7.0, 2.0, 1.6],
        font=8,
    )

    # ---- 5. official titles ---------------------------------------------
    h(doc, "5.  Official titles mapped to the school's records", 1)
    para(doc, "The school's strands and courses against the official "
              "programme titles, so a registrar can see what a sheet's "
              "wording means.")
    add_table(
        doc,
        ["Official programme title", "The school's record", "Where it lives"],
        [[a, b, c] for a, b, c in OFFICIAL_TITLES],
        widths=[6.4, 5.6, 6.4],
    )

    h(doc, "5.1  Cluster and programme-group names", 2)
    para(doc, "These names appear on the official sheets but are not strands "
              "of their own - they are groups. The importer never matches "
              "them to a strand; the student takes the strand of their "
              "section instead.")
    add_table(
        doc,
        ["Name on the sheet", "What it covers", "How it is resolved"],
        [[a, b, c] for a, b, c in CLUSTERS],
        widths=[5.0, 6.2, 7.2],
    )

    # ---- 6. sections -----------------------------------------------------
    h(doc, "6.  Sections", 1)
    add_table(
        doc,
        ["Section", "Year level", "Strand", "Course", "Adviser", "Students"],
        [[s["name"], s["grade_year"], s["strand"] or "-", s["course"] or "-",
          s["adviser"] or "-", s["students"]] for s in D["sections"]],
        widths=[2.6, 2.4, 5.4, 3.6, 3.0, 1.6],
        font=8,
    )

    # ---- 7. import rules -------------------------------------------------
    h(doc, "7.  How an enrolment sheet is read", 1)
    for rule in IMPORT_RULES:
        bullet(doc, rule)

    # ---- 8. reference ----------------------------------------------------
    h(doc, "8.  Reference notes", 1)
    for note in REFERENCE_NOTES:
        bullet(doc, note)

    # ---- 9. data notes ---------------------------------------------------
    h(doc, "9.  Notes on the data as it stands", 1)
    odd = [s for s in D["sections"] if s["strand"] and s["course"]]
    bullet(doc, "%d section(s) carry both a strand and a course: %s. The "
                "strand is the one that counts for a Senior High section."
           % (len(odd), ", ".join(s["name"] for s in odd) or "-"))
    bullet(doc, "One strand name is missing its closing bracket "
                "(“Automotive Servicing (NCI & NCII”). The aliases cover "
                "every spelling, so imports still land correctly.")
    no_adv = [s for s in D["sections"] if not s["adviser"]]
    bullet(doc, "%d section(s) have no adviser set yet - they are filled in "
                "from School Config → Advisers." % len(no_adv))
    bullet(doc, "Student counts are the current enrolment in each strand, "
                "course and section.")

    doc.save(path)
    return path


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_html(path):
    def table(headers, rows, cls=""):
        head = "".join("<th>%s</th>" % esc(x) for x in headers)
        body = ""
        for r in rows:
            body += "<tr>" + "".join(
                "<td>%s</td>" % (esc(c).replace("\n", "<br>") if c is not None else "")
                for c in r) + "</tr>"
        return "<table class='%s'><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
            cls, head, body)

    odd = [s for s in D["sections"] if s["strand"] and s["course"]]

    parts = []
    parts.append("""<!doctype html><html><head><meta charset='utf-8'>
<style>
  @page { size: A4; margin: 14mm; }
  * { box-sizing: border-box; }
  body { font-family: "Segoe UI", Calibri, Arial, sans-serif; color: #111827;
         font-size: 10px; margin: 0; }
  .cover { text-align: center; padding-top: 30mm; }
  .school { color: #1d4ed8; font-weight: 700; font-size: 15px; letter-spacing: .3px; }
  h1 { font-size: 30px; margin: 6px 0 4px; color: #111827; }
  .meta { color: #4b5563; font-size: 11px; }
  h2 { font-size: 15px; color: #1d4ed8; margin: 16px 0 6px;
       border-bottom: 1px solid #dbeafe; padding-bottom: 3px; }
  h3 { font-size: 12px; color: #374151; margin: 12px 0 4px; }
  p { margin: 4px 0; line-height: 1.45; }
  ul { margin: 4px 0 6px 16px; padding: 0; }
  li { margin: 2px 0; line-height: 1.45; }
  table { width: 100%; border-collapse: collapse; margin: 6px 0 10px;
          page-break-inside: auto; }
  th { background: #1d4ed8; color: #fff; text-align: left; padding: 4px 5px;
       font-size: 9px; }
  td { border: 1px solid #e5e7eb; padding: 3px 5px; vertical-align: top;
       font-size: 8.5px; }
  tr:nth-child(even) td { background: #f8fafc; }
  .page-break { page-break-before: always; }
  .note { background: #f8fafc; border-left: 3px solid #1d4ed8; padding: 6px 9px;
          margin: 6px 0; }
</style></head><body>""")

    parts.append(
        "<div class='cover'>"
        "<div class='school'>%s</div>"
        "<h1>%s</h1>"
        "<div class='meta'>Track TVL &nbsp;|&nbsp; %d strands &nbsp;|&nbsp; "
        "%d bundled courses &nbsp;|&nbsp; %d sections &nbsp;|&nbsp; %s</div>"
        "</div><div class='page-break'></div>"
        % (esc(SCHOOL), esc(TITLE), len(D["strands"]), len(D["courses"]),
           len(D["sections"]), esc(TODAY))
    )

    parts.append("<h2>1. How the school is organised</h2><ul>")
    parts.append("<li><b>A TRACK</b> is the curriculum family. The school has "
                 "one: TVL (Technical-Vocational-Livelihood).</li>")
    parts.append("<li><b>A STRAND</b> is the specialisation a Senior High "
                 "student takes in that track. There are %d.</li>"
                 % len(D["strands"]))
    parts.append("<li><b>A COURSE</b> is the programme a Bundled student takes "
                 "for the one or two years of the TESDA track. There are %d.</li>"
                 % len(D["courses"]))
    parts.append("<li><b>A SECTION</b> is a class in one year level, and it "
                 "points at the strand or course it teaches.</li>")
    parts.append("</ul><p><i>The year levels in use: %s.</i></p>"
                 % esc(", ".join(D["grade_years"])))

    parts.append("<h2>2. Tracks</h2>")
    parts.append(table(["Track", "Code", "Level", "Strands", "Description"],
                       [[t["name"], t["code"], t["level_type"],
                         t["strand_count"], t["description"] or "-"]
                        for t in D["tracks"]]))

    parts.append("<h2>3. Strands (Senior High)</h2>")
    parts.append("<p>The school uses %d strands, all under the TVL track. The "
                 "“Official / alias names” column lists every wording the "
                 "registrar's sheets and the DepEd / TESDA lists may use - the "
                 "import matches a strand by its name, its code or any of these "
                 "aliases.</p>" % len(D["strands"]))
    parts.append(table(["#", "Strand", "Code", "Official / alias names",
                         "Sections", "Students"],
                        [[i + 1, s["name"], s["code"],
                          "\n".join(s["aliases"]) if s["aliases"] else "-",
                          ", ".join(s["sections"]) if s["sections"] else "-",
                          s["students"]] for i, s in enumerate(D["strands"])]))

    parts.append("<h2>4. Courses (Bundled / TESDA track)</h2>")
    parts.append(table(["#", "Course", "Code", "Level", "Official / alias names",
                         "Sections", "Students"],
                        [[i + 1, c["name"], c["code"], c["level_type"],
                          "\n".join(c["aliases"]) if c["aliases"] else "-",
                          ", ".join(c["sections"]) if c["sections"] else "-",
                          c["students"]] for i, c in enumerate(D["courses"])]))

    parts.append("<h2>5. Official titles mapped to the school's records</h2>")
    parts.append("<p>The school's strands and courses against the official "
                 "programme titles, so a registrar can see what a sheet's "
                 "wording means.</p>")
    parts.append(table(["Official programme title", "The school's record",
                         "Where it lives"], OFFICIAL_TITLES))

    parts.append("<h3>5.1 Cluster and programme-group names</h3>")
    parts.append("<p>These names appear on the official sheets but are not "
                 "strands of their own - they are groups. The importer never "
                 "matches them to a strand; the student takes the strand of "
                 "their section instead.</p>")
    parts.append(table(["Name on the sheet", "What it covers",
                         "How it is resolved"], CLUSTERS))

    parts.append("<h2>6. Sections</h2>")
    parts.append(table(["Section", "Year level", "Strand", "Course", "Adviser",
                         "Students"],
                        [[s["name"], s["grade_year"], s["strand"] or "-",
                          s["course"] or "-", s["adviser"] or "-", s["students"]]
                         for s in D["sections"]]))

    parts.append("<h2>7. How an enrolment sheet is read</h2><ul>")
    for rule in IMPORT_RULES:
        parts.append("<li>%s</li>" % esc(rule))
    parts.append("</ul>")

    parts.append("<h2>8. Reference notes</h2><ul>")
    for note in REFERENCE_NOTES:
        parts.append("<li>%s</li>" % esc(note))
    parts.append("</ul>")

    parts.append("<h2>9. Notes on the data as it stands</h2><ul>")
    parts.append("<li>%d section(s) carry both a strand and a course: %s. The "
                 "strand is the one that counts for a Senior High section.</li>"
                 % (len(odd), esc(", ".join(s["name"] for s in odd) or "-")))
    parts.append("<li>One strand name is missing its closing bracket "
                 "(“Automotive Servicing (NCI &amp; NCII”). The aliases cover "
                 "every spelling, so imports still land correctly.</li>")
    parts.append("<li>Section advisers are filled in from School Config → "
                 "Advisers.</li>")
    parts.append("<li>Student counts are the current enrolment in each strand, "
                 "course and section.</li>")
    parts.append("</ul>")

    parts.append("</body></html>")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(parts))
    return path


if __name__ == "__main__":
    docx_path = os.path.join(DOCS, "USAT-Track-Strand-and-Course-Reference.docx")
    html_path = os.path.join(DOCS, "USAT-Track-Strand-and-Course-Reference.html")
    print("docx:", build_docx(docx_path))
    print("html:", build_html(html_path))
