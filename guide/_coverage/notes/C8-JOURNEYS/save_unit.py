from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import re
ROOT = Path('guide')
def save(slug, title, description, reader, body, mapping, summary, unsure='None.', steer='No steering file was present before this unit.'):
    p = ROOT / f'src/content/docs/journeys/{slug}.md'
    p.write_text(f'---\ntitle: {title}\ndescription: {description}\nreader: {reader}\n---\n\n{body.strip()}\n')
    coverage = ROOT / '_waves/coverage/journeys.md'
    rows = coverage.read_text().splitlines()
    for i, row in enumerate(rows):
        for jid, anchor in mapping.items():
            if f'({jid})' in row.split('|')[2] if row.startswith('| C') else False:
                cells = row.split('|')
                cells[-2] = f' [journeys/{slug}#{anchor}](../../src/content/docs/journeys/{slug}.md#{anchor}) '
                rows[i] = '|'.join(cells)
    coverage.write_text('\n'.join(rows)+'\n')
    progress = ROOT / '_waves/progress/C8-JOURNEYS.md'
    with progress.open('a') as out:
        out.write(f'\n- {datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")} — `{p}`. {summary} Uncertainties: {unsure} Steering: {steer}\n')
