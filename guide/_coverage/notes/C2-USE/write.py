from pathlib import Path
from datetime import datetime
ROOT=Path('guide')
def steer():
 p=ROOT/'_waves/steer/C2-USE.md'
 if p.exists(): print('STEERING:',p.read_text())
def page(slug,title,description,body,screen=None,state=None):
 steer()
 p=ROOT/'src/content/docs'/f'{slug}.md'
 p.write_text(f'---\ntitle: {title}\ndescription: {description}\nreader: steward\n---\n\n'+body.strip()+'\n')
 if screen:
  with p.open('a') as f: f.write(f'\n![{state}](/docs/screens/{screen}.png)\n')
  with (ROOT/'_waves/screens-wanted/C2-USE.md').open('a') as f: f.write(f'| {screen}.png | {slug} | {state} |\n')
 with (ROOT/'_waves/progress/C2-USE.md').open('a') as f:
  f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `{p}`. {description} Checked against the topic sources recorded in working notes. Steering: '+('read; applied where relevant.' if (ROOT/'_waves/steer/C2-USE.md').exists() else 'none present.')+'\n')
def append(slug,body,summary):
 steer()
 p=ROOT/'src/content/docs'/f'{slug}.md'
 with p.open('a') as f:f.write('\n'+body.strip()+'\n')
 with (ROOT/'_waves/progress/C2-USE.md').open('a') as f:f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `{p}`. {summary} Steering: '+('read; applied where relevant.' if (ROOT/'_waves/steer/C2-USE.md').exists() else 'none present.')+'\n')
