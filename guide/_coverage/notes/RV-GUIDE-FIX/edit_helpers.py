from pathlib import Path
from datetime import datetime
ROOT=Path('guide/src/content/docs')
def start(page):
 p=Path('guide/_waves/steer/RV-GUIDE-FIX.md')
 if p.exists():
  print(p.read_text())
  raise SystemExit('Read and apply steering before continuing')
 return (ROOT/page).read_text()
def save(page,text,note):
 (ROOT/page).write_text(text)
 with Path('guide/_waves/progress/RV-GUIDE-FIX.md').open('a') as f:
  f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `{page}`: {note} No steering file exists.\n')
 print(page)
