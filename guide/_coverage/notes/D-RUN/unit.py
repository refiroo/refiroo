from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[3]
def begin():
    p=ROOT/'_waves/steer/D-RUN.md'
    print(p.read_text() if p.exists() else 'No D-RUN steering file.')
def finish(page, summary, evidence, unresolved='None beyond unexecuted deployment commands.'):
    with (ROOT/'_coverage/notes/D-RUN/depth.md').open('a') as f:
        f.write(f'\n## {page}\n\n{summary}\n\nSources: {evidence}\n\nOpen: {unresolved}\n')
    with (ROOT/'_waves/progress/D-RUN.md').open('a') as f:
        f.write('\n'+datetime.now().astimezone().isoformat(timespec='seconds')+f' — Finished `{page}`: {summary} Uncertain: {unresolved} Steering: '+('read and applied where relevant.' if (ROOT/'_waves/steer/D-RUN.md').exists() else 'none present.')+'\n')
