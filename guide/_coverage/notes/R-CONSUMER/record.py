from pathlib import Path
from datetime import datetime
ROOT = Path('guide')
def row(source, heading, facts, home, action):
    p = ROOT/'_waves/reconcile/R-CONSUMER.md'
    if not p.exists():
        p.write_text('# R-CONSUMER reconciliation\n\nCounts count distinct reader facts changed, not words or source mentions. Repeated facts are counted once, at the first change. Existing worked examples are retained unless corrected.\n\n| Source | Heading | Reader facts | Home (page: heading) | Result |\n| --- | --- | --- | --- | --- |\n')
    with p.open('a') as f:
        f.write('| '+ ' | '.join(x.replace('|',' / ').replace('\n',' ') for x in (source,heading,facts,home,action))+' |\n')
def progress(page, text):
    p=ROOT/'_waves/progress/R-CONSUMER.md'
    with p.open('a') as f:
        f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — {page}: {text} Steering file checked; none present.\n')
