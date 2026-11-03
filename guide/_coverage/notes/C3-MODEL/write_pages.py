from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path('guide')
def page(slug,title,description,body,summary,uncertainty='None identified in this unit.'):
    steer=ROOT/'_waves/steer/C3-MODEL.md'
    if steer.exists() and steer.read_text().strip():
        raise RuntimeError('Read and apply steering before continuing: '+str(steer))
    path=ROOT/'src/content/docs'/f'{slug}.md'
    path.write_text(f'---\ntitle: {title}\ndescription: {description}\nreader: model-admin\n---\n\n'+body.strip()+'\n')
    log=ROOT/'_waves/progress/C3-MODEL.md'
    with log.open('a') as f:
        f.write(f'\n- {datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")} — `{path}`. {summary} Uncertainty: {uncertainty} Steering: no corrections file with content was present.\n')
    print(path)
def append(slug,body,summary):
    p=ROOT/'src/content/docs'/f'{slug}.md'
    text=p.read_text(); front,rest=text[4:].split('\n---\n',1)
    vals=dict(line.split(': ',1) for line in front.splitlines())
    page(slug,vals['title'],vals['description'],rest.rstrip()+'\n\n'+body,summary)
