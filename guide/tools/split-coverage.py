"""Split _waves/COVERAGE.md into _waves/coverage/<section>.md, one per section, so parallel waves each
edit their own file. The header of COVERAGE.md and the table head are repeated in each file.
Usage: python3 guide/tools/split-coverage.py
"""

from collections import defaultdict
from pathlib import Path

WAVES = Path(__file__).resolve().parent.parent / "_waves"
src = (WAVES / "COVERAGE.md").read_text().splitlines()

head = next(i for i, line in enumerate(src) if line.startswith("| ID |"))
cols = [c.strip() for c in src[head].strip("|").split("|")]
section_col = cols.index("Section")
rows = defaultdict(list)
for line in src[head + 2 :]:
    if not line.startswith("| C"):
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    rows[cells[section_col]].append(line)

out = WAVES / "coverage"
out.mkdir(exist_ok=True)
for section, lines in sorted(rows.items()):
    text = [
        f"# Coverage: {section}",
        "",
        f"Split from `_waves/COVERAGE.md` ({len(lines)} rows). The wave writing this section keeps it up to date;",
        "other waves read it only.",
        "",
        src[head],
        src[head + 1],
        *lines,
        "",
    ]
    (out / f"{section}.md").write_text("\n".join(text))
    print(f"{section}: {len(lines)}")
