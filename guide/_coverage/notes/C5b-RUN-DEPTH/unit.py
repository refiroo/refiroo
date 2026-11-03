from pathlib import Path
from datetime import datetime
root=Path('guide')
def finish(name, text, summary):
    steer=root/'_waves/steer/C5b-RUN-DEPTH.md'
    steering=steer.read_text() if steer.exists() else None
    if steering: print('STEERING:',steering); raise SystemExit('Read steering before writing this unit')
    p=root/'src/content/docs/run'/name
    p.write_text(p.read_text().rstrip()+'\n\n'+text.strip()+'\n')
    with (root/'_waves/progress/C5b-RUN-DEPTH.md').open('a') as out:
        out.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `guide/src/content/docs/run/{name}`. {summary} No steering file present.\n')
