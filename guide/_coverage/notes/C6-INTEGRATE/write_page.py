from pathlib import Path
from datetime import datetime
import sys
root=Path(__file__).resolve().parents[3]
steer=root/'_waves/steer/C6-INTEGRATE.md'
if steer.exists():
    print('STEERING:',steer.read_text())
slug,title,description,summary=sys.argv[1:]
body=sys.stdin.read()
p=root/'src/content/docs'/f'{slug}.md'
p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(f'---\ntitle: {title}\ndescription: {description}\nreader: integrator\n---\n\n'+body)
with (root/'_waves/progress/C6-INTEGRATE.md').open('a') as f:
    f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `src/content/docs/{slug}.md`: {summary} Steering: '+('read; see applied corrections in subsequent entries.' if steer.exists() else 'no steering file present.')+'\n')
print('Wrote',slug)
