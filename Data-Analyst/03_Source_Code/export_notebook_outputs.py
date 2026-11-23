"""Export executed notebook outputs to a plain-text evidence file.

Usage: python export_notebook_outputs.py <notebook.ipynb> <output.txt>
"""

import sys
from pathlib import Path

import nbformat

notebook_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

notebook = nbformat.read(notebook_path, as_version=4)
chunks = []

for index, cell in enumerate(notebook.cells):
    if cell.cell_type != "code":
        continue
    for output in cell.get("outputs", []):
        if output.output_type == "error":
            raise SystemExit(f"Error in code cell {index}: {output.get('ename')}")
        if output.output_type == "stream":
            chunks.append(output.get("text", ""))
        elif output.output_type in ("execute_result", "display_data"):
            text = output.get("data", {}).get("text/plain")
            if text:
                chunks.append(text)

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text("\n".join(chunks), encoding="utf-8")
print(f"Exported outputs from {notebook_path} to {output_path}")
