from pathlib import Path
from datetime import datetime
import json
base=Path('guide')
def finish(rel, changes=(), summary='Checked the page against the Settings changes; no correction needed.'):
 steer=base/'_waves/steer/ST1-GUIDE.md'
 if steer.exists():
  current=steer.read_text()
  known=base/'_coverage/notes/ST1-GUIDE/steer-read.txt'
  if not known.exists() or current!=known.read_text():
   print(current); raise RuntimeError('Read and acknowledge new steering before continuing')
 p=base/'src/content/docs'/rel
 text=p.read_text()
 for old,new in changes:
  assert old in text,(rel,old)
  text=text.replace(old,new)
 if changes: p.write_text(text)
 progress=base/'_waves/progress/ST1-GUIDE.md'; progress.parent.mkdir(parents=True,exist_ok=True)
 with progress.open('a') as f:
  f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `{p}`: {summary} No steering file was present.\n')
 print(rel, 'changed' if changes else 'no change')
