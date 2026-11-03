from pathlib import Path
from datetime import datetime
root=Path(__file__).resolve().parents[3]
def steering():
 p=root/'_waves/steer/C6-INTEGRATE.md'
 if p.exists():
  print(p.read_text())
  if 'Consumer APIs must be explained' not in p.read_text(): raise SystemExit('New steering needs explicit review.')
def finish(paths,summary):
 with (root/'_waves/progress/C6-INTEGRATE.md').open('a') as f:
  f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — '+', '.join(f'`{p}`' for p in paths)+f': {summary} Steering: applied the consumer-API explanation and full-example correction where relevant; management operation schemas remain in the reference.\n')
