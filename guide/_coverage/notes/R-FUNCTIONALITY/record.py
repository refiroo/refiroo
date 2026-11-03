from pathlib import Path
from datetime import datetime
root = Path(__file__).resolve().parents[3]
def steer():
    p=root/'_waves/steer/R-FUNCTIONALITY.md'
    return p.read_text() if p.exists() else 'No steering file present.'
def record(source, heading, facts, locations, outcome, counts='0 added, 0 corrected, 0 expanded'):
    ledger=root/'_waves/reconcile/R-FUNCTIONALITY.md'
    if not ledger.exists():
        ledger.write_text('# Functionality reconciliation\n\nCounts refer to separately described reader facts, not words or paragraphs. Source evidence links and delivery history are not reader facts. Other-reader destinations are handoffs, not assertions that those pages were reconciled.\n\n| Source heading | Facts found | Page and heading / handoff | Result |\n| --- | --- | --- | --- |\n')
    with ledger.open('a') as f:
        f.write(f'| {source}: {heading} | {facts} | {locations} | {outcome} |\n')
    with (root/'_waves/progress/R-FUNCTIONALITY.md').open('a') as f:
        f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — {source}, {heading}: {locations}. {outcome} ({counts}). Steering: {steer().strip()}\n')
