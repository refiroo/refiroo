from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[3]
def write_page(slug, title, description, body):
    path = ROOT / 'src/content/docs' / (slug + '.md')
    path.write_text(f'---\ntitle: {title}\ndescription: {description}\nreader: access-admin\n---\n\n' + body.strip() + '\n')
def progress(paths, summary, uncertainty='None.'):
    path = ROOT / '_waves/progress/C4-ADMIN.md'
    if not path.exists(): path.write_text('# C4-ADMIN progress\n\n')
    with path.open('a') as f:
        f.write(f'\n- {datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")} — {paths}. {summary} Uncertainty: {uncertainty} Steering: no steering file present.\n')
def screen(name, page, state):
    path = ROOT / '_waves/screens-wanted/C4-ADMIN.md'
    if not path.exists(): path.write_text('# Screens wanted: C4-ADMIN\n\nScreens below are requested; no captures were made by this wave.\n\n| File | Page | Screen, state and required visible details |\n| --- | --- | --- |\n')
    with path.open('a') as f: f.write(f'| {name}.png | {page} | {state} |\n')
