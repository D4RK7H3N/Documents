"""Convert Markdown deliverables to the PDF/PPTX formats required for submission."""

import re
import shutil
import textwrap
from pathlib import Path

from fpdf import FPDF
from pptx import Presentation
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FONT = Path("C:/Windows/Fonts/arial.ttf")
BOLD_FONT = Path("C:/Windows/Fonts/arialbd.ttf")
PREFIX = "ArgeLonggakit_StudentAcademicPerformanceAnalysis"

REPLACEMENTS = {
    "→": "->", "≤": "<=", "≥": ">=", "×": "x", "−": "-",
    "–": "-", "—": "-", "η": "eta", "²": "2", "≠": "!=",
    "‘": "'", "’": "'", "“": '"', "”": '"', "•": "-",
}


def clean(text):
    text = text.replace("**", "").replace("`", "")
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def markdown_to_pdf(source, target):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("AU", fname=str(FONT))
    use_bold = BOLD_FONT.exists()
    if use_bold:
        pdf.add_font("AU", style="B", fname=str(BOLD_FONT))

    def emit(text, height, size, bold=False, width=100):
        pdf.set_font("AU", style="B" if (bold and use_bold) else "", size=size)
        wrapped = textwrap.fill(
            clean(text), width=width, break_long_words=True, break_on_hyphens=True
        )
        pdf.multi_cell(0, height, wrapped, new_x="LMARGIN", new_y="NEXT")

    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("### "):
            emit(line[4:], 7, 12, bold=True)
            pdf.ln(1)
        elif line.startswith("## "):
            emit(line[3:], 9, 14, bold=True)
            pdf.ln(1.5)
        elif line.startswith("# "):
            emit(line[2:], 10, 17, bold=True)
            pdf.ln(2)
        elif line.startswith("|") and not re.fullmatch(r"\|[\s\-:|]+\|", line):
            emit(line, 4.2, 8, width=120)
        elif line.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", line):
            emit("  " + line, 5.5, 10)
        elif line.startswith("> "):
            emit(line, 5.5, 10)
        elif line in ("---", ""):
            pdf.ln(2)
        else:
            emit(line, 5.5, 10)

    pdf.output(str(target))
    return target


def add_slide(prs, title, lines, font_size=12):
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = clean(title)
    frame = slide.placeholders[1].text_frame
    frame.word_wrap = True
    for index, item in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = clean(item)
        for run in paragraph.runs:
            run.font.size = Pt(font_size)
    return slide


def markdown_to_pptx(source, target):
    lines = source.read_text(encoding="utf-8").splitlines()
    presentation = Presentation()
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)

    sections = []
    current = None
    for raw in lines:
        if raw.startswith("### Slide "):
            current = {"title": raw[4:].strip(), "body": []}
            sections.append(current)
        elif raw.startswith("## Ten likely"):
            current = None
        elif current is not None and raw.strip() and raw.strip() != "---":
            current["body"].append(raw.strip())

    for index, section in enumerate(sections):
        title = "Student Academic Performance Analysis" if index == 0 else section["title"]
        add_slide(presentation, title, section["body"])

    qa = []
    current = None
    in_qa = False
    for raw in lines:
        if raw.startswith("## Ten likely"):
            in_qa = True
            continue
        if not in_qa:
            continue
        if re.match(r"^\*\*Q\d+", raw):
            current = {"title": raw.replace("**", "").strip(), "body": []}
            qa.append(current)
        elif current is not None and raw.strip() and not raw.startswith("**Evidence"):
            current["body"].append(raw.strip())

    for item in qa:
        add_slide(presentation, item["title"], item["body"], font_size=11)

    presentation.save(str(target))
    return target, len(sections) + len(qa)


markdown_files = sorted(
    path for path in ROOT.rglob("*.md")
    if ".venv" not in path.parts and not path.name.startswith(PREFIX)
)

outputs = []
for source in markdown_files:
    outputs.append(markdown_to_pdf(source, source.with_suffix(".pdf")))

slides_md = ROOT / "06_Presentation" / "slide_outline.md"
pptx_path, slide_count = markdown_to_pptx(slides_md, ROOT / "06_Presentation" / "Final_Presentation.pptx")
outputs.append(pptx_path)

for path in list(outputs):
    named = path.with_name(f"{PREFIX}_{path.stem}{path.suffix}")
    shutil.copy2(path, named)
    outputs.append(named)

evidence = ROOT / "05_Documentation" / "phase6_submission_formats.txt"
evidence.write_text(
    "PHASE 6 - SUBMISSION FORMAT EXPORT (executed)\n"
    + "\n".join(
        f"{path.relative_to(ROOT)} ({path.stat().st_size} bytes)" for path in outputs
    )
    + f"\nSlide count (including defense Q&A): {slide_count}\n",
    encoding="utf-8",
)
print(f"Exported {len(outputs)} files; {slide_count} slides; evidence: {evidence.relative_to(ROOT)}")
