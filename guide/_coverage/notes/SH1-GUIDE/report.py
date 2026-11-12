from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,re,difflib
notes=Path('guide/_coverage/notes/SH1-GUIDE')
baseline=json.loads((notes/'baseline.json').read_text())
progress=Path('guide/_waves/progress/SH1-GUIDE.md')
changed=[];unchanged=[]
for name,old in baseline.items():
 new=Path(name).read_text()
 assert old.split('---',2)[:2]==new.split('---',2)[:2], f'Front matter changed: {name}'
 assert re.findall(r'/docs/screens/[^\s)]+',old)==re.findall(r'/docs/screens/[^\s)]+',new), f'Screenshot reference changed: {name}'
 assert re.findall(r'^#{1,6} .+$',old,re.M)==re.findall(r'^#{1,6} .+$',new,re.M), f'Page headings changed: {name}'
 (unchanged if old==new else changed).append(name)
for name in unchanged:
 steer=Path('guide/_waves/steer/SH1-GUIDE.md')
 if steer.exists() and steer.read_text().strip():raise SystemExit('Read steering: '+steer.read_text())
 with progress.open('a') as f:f.write(f'\n- {datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")} — `{name}`: No change after reviewing the SH1 navigation/frame search hits; this page has no affected instruction, or the existing instruction remains correct. No steering file.\n')
report=[f'# SH1-GUIDE report\n\nReviewed {len(baseline)} assigned pages: {len(changed)} changed, {len(unchanged)} no change. Only SH1 wording was changed; front matter, section structure and screenshot filenames are preserved.\n\n## Per-page old and new text\n\nPassages below reproduce the changed sentences with their surrounding paragraph where needed to keep the context exact. Unchanged sentences within a quoted paragraph are retained for context. Paths are relative to the repository root.\n']
for name,old in baseline.items():
 new=Path(name).read_text()
 report.append(f'### `{name}`\n')
 if old==new:report.append('No change.\n');continue
 before=old.split('\n\n');after=new.split('\n\n')
 for tag,a,b,c,d in difflib.SequenceMatcher(None,before,after,autojunk=False).get_opcodes():
  if tag=='equal':continue
  report.extend(['Old:\n\n```markdown\n'+'\n\n'.join(before[a:b])+'\n```\n','New:\n\n```markdown\n'+'\n\n'.join(after[c:d])+'\n```\n'])
screens=sorted({n for old in baseline.values() for n in re.findall(r'/docs/screens/([^\s)]+)',old)})
report.append(f'## Screenshots with the outdated frame\n\nAll {len(screens)} referenced screenshots retain the earlier top bar and/or Settings navigation, data band, record trail or header. The six contact sheets in this notes directory were visually inspected for the frame; this is not a new browser acceptance run. Dialog captures also include the earlier frame in their backgrounds. The screenshot files and every screenshot reference were left unchanged.\n\nFor replacement captures, retain each page’s existing screen and data state, with the current frame visible: workspace-wide search and folded Browse records on application pages; one context row and Details in a change set; the list/ancestor trail and Details on records; task groups and the workspace return link in Settings; one-line roles on Home.\n')
report.extend('- `'+name+'`' for name in screens)
report.append('''
## Facts checked against code, exceptions and limits

- Fact 1 describes search groups as lists. `WorkspaceSearch.tsx`, `groupByType`, groups by record type and uses its plural name; a view-defined list is not the grouping key. The guide says record type. Paths show the application and ancestors.
- Fact 6 says there is no separate Back to list button. This holds on a loaded record page. `ObjectDetail.tsx` retains that button in the **Object unavailable** error state, so the recovery instruction in `use/records.md` remains correct.
- The comparison page is **Changes in this change set** and its return action is **See the data with these changes**. **Review changes** remains the button in the change-set band and in publication confirmation; those button instructions were retained.
- Workspace-wide search opens a detail route without a change-set or publication identifier (`TopBar.tsx` and `WorkspacePage.tsx`), so it opens Live. The new search instructions explain this. Collection search is the way to keep a snapshot context.
- The full tree view still has **Find a record** (`TreeView.tsx`); the sidebar tree does not (`Explorer.tsx`). The tree-view guide remains unchanged.
- The model preview retains its own application chooser in a band (`TypePreview.tsx`). Its preview instruction remains unchanged. This is separate from the application’s data-context band.
- `SettingsLayout.tsx` accepts an optional trail; the Settings index has a header without one. The guide describes the workspace return link without asserting that every Settings page has a trail.
- **Breadcrumbs start with the application** is no longer offered in the model editor (`layout.ts`). The stored compatibility setting remains but draws nothing. Both affected editor explanations were corrected.
- iOS **Settings › General › About › Certificate Trust Settings** in `run/developer-instance.md` is an operating-system path, not a refiroo Settings path; it remains unchanged. GitHub repository Settings and literal command output were likewise retained.
- No unrelated product defect was investigated or changed. No live reference-instance browser journey was run; existing screenshot review and source inspection establish only the documentation corrections. A contact-sheet attempt through Chrome was refused by the local execution environment; the inspected sheets were then generated locally with AppKit without changing source screenshots.

## Validation

- `GUIDE_OUT=_build/SH1-GUIDE npm run build` in `guide/`: passes; final run recorded in `build-final.log`.
- The build reports a `/404` route conflict warning. It still exits successfully; no route configuration was changed in this wave.
- `git diff --check -- guide/src/content/docs`: passes.
- All 218 assigned pages retain their front matter and section headings. Every screenshot URL and its order are identical to the pre-edit snapshot.
- No code, test, screenshot, other wave file, or application configuration was edited; no commit or state-changing git command was run.
''')
(notes/'report.md').write_text('\n\n'.join(report))
(notes/'changes.diff').write_text(''.join(''.join(difflib.unified_diff(old.splitlines(True),Path(name).read_text().splitlines(True),fromfile=name+' (before wave)',tofile=name)) for name,old in baseline.items() if old!=Path(name).read_text()))
print(f'{len(changed)} changed; {len(unchanged)} no change; {len(screens)} screenshots. Report saved. Invariants passed.')
