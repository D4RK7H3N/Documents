"""Package the complete project into a single distributable zip file."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT.parent / "ArgeLonggakit_StudentAcademicPerformanceAnalysis.zip"

EXCLUDED_PARTS = {".venv", "__pycache__", ".ipynb_checkpoints", ".git"}
EXCLUDED_SUFFIXES = {".pyc", ".zip", ".tmp"}

files = sorted(
    path
    for path in ROOT.rglob("*")
    if path.is_file()
    and not any(part in EXCLUDED_PARTS for part in path.parts)
    and path.suffix.lower() not in EXCLUDED_SUFFIXES
)

with ZipFile(TARGET, "w", compression=ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, arcname=path.relative_to(ROOT).as_posix())

print(f"Created {TARGET}")
print(f"Files: {len(files)}")
print(f"Size: {TARGET.stat().st_size / 1024 / 1024:.2f} MiB")
top_level = sorted({p.relative_to(ROOT).as_posix().split("/")[0] for p in files})
print("Top level:", ", ".join(top_level))
