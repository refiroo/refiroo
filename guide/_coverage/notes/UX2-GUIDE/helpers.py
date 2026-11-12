from pathlib import Path
from datetime import datetime

def update(name, changes, summary, uncertainty='None.'):
    steer=Path('guide/_waves/steer/UX2-GUIDE.md')
    if steer.exists():
        raise SystemExit('Read and apply steering before continuing: '+steer.read_text())
    p=Path('guide/src/content/docs')/name
    s=p.read_text()
    for a,b in changes:
        assert a in s,(name,a)
        s=s.replace(a,b,1)
    p.write_text(s)
    with Path('guide/_waves/progress/UX2-GUIDE.md').open('a') as f:
        f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `{p}`: {summary} No steer file exists. Uncertainties: {uncertainty}\n')
