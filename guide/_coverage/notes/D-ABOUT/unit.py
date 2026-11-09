from pathlib import Path
from datetime import datetime
ROOT=Path('guide')
def start():
    steer=ROOT/'_waves/steer/D-ABOUT.md'
    if steer.exists() and steer.read_text().strip():
        raise SystemExit('Read and apply new steering before continuing: '+steer.read_text())

def done(path, summary, depth):
    stamp=datetime.now().astimezone().isoformat(timespec='minutes')
    with (ROOT/'_waves/progress/D-ABOUT.md').open('a') as f:
        f.write(f'\n## {stamp} — {path}\n{summary} No D-ABOUT steering file was present.\n')
    with (ROOT/'_coverage/notes/D-ABOUT/depth.md').open('a') as f:
        f.write(f'\n## {path}\n{depth}\n')

def append(path, content, summary, depth):
    start(); p=ROOT/path; p.write_text(p.read_text().rstrip()+'\n\n'+content.strip()+'\n'); done(path,summary,depth)
