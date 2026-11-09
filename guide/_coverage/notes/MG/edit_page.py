from pathlib import Path
from datetime import datetime

def finish(page, replacements, summary, uncertainty='None.', kept=''):
    steer = Path('guide/_waves/steer/MG.md')
    if steer.exists():
        raise SystemExit('Steering exists: read and apply before continuing: ' + steer.read_text())
    path = Path('guide/src/content/docs') / page
    content = path.read_text()
    for old, new in replacements:
        if old not in content:
            raise SystemExit(f'Passage not found in {page}: {old[:80]}')
        content = content.replace(old, new, 1)
    path.write_text(content)
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    with Path('guide/_waves/progress/MG.md').open('a') as log:
        log.write(f'\n- {now} — Finished `src/content/docs/{page}`. {summary} Uncertainties: {uncertainty} Steering: no steer file present.\n')
    with Path('guide/_coverage/notes/MG/review.md').open('a') as log:
        log.write(f'\n## {page}\nChanged: {summary}\nChecked and retained: {kept}\nUncertainties: {uncertainty}\n')
    print('Finished ' + page)
