from pathlib import Path
from datetime import datetime
BASE=Path('guide/src/content/docs')
def edit(page, replacements, summary):
    steer=Path('guide/_waves/steer/UX1-GUIDE.md')
    steering = steer.read_text() if steer.exists() else ''
    path=BASE/page
    text=path.read_text()
    for old,new in replacements:
        if old not in text: raise ValueError(f'{page}: missing {old[:90]}')
        text=text.replace(old,new)
    path.write_text(text)
    with Path('guide/_waves/progress/UX1-GUIDE.md').open('a') as f:
        f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `{path}`. {summary} {('Steering read: 04:37 deletion, Home order, file drop and pin corrections considered; applied where relevant.' if steering else 'No steering file present.')}\n')
