from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).resolve().parents[3]
def steering():
    p = ROOT / '_waves/steer/R-MODEL.md'
    if p.exists():
        text = p.read_text()
        seen = ROOT / '_coverage/notes/R-MODEL/steer-read.txt'
        if not seen.exists() or seen.read_text() != text:
            raise RuntimeError('Read new steering before next unit: ' + text)
def record(source, heading, facts, where, result):
    steering()
    ledger = ROOT / '_waves/reconcile/R-MODEL.md'
    if not ledger.exists():
        ledger.write_text('# R-MODEL reconciliation\n\nCounts refer to independently actionable facts changed, not words or repeated links. Skipped implementation details and historical plans are not counted. Consumer-API definitions are outside this wave; their destinations are references only.\n\n| Source heading | Reader facts | Destination | Result |\n| --- | --- | --- | --- |\n')
    with ledger.open('a') as f:
        f.write('| ' + ' | '.join(x.replace('|', '/') .replace('\n', ' ') for x in (source + ' — ' + heading, facts, where, result)) + ' |\n')
    progress = ROOT / '_waves/progress/R-MODEL.md'
    if not progress.exists():
        progress.write_text('# R-MODEL progress\n\n')
    with progress.open('a') as f:
        f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")}: {source} / {heading}. {where}. {result}. Steering: checked; none pending.\n')
