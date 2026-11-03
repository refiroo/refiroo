from pathlib import Path
from datetime import datetime
import re
ROOT=Path('guide')
progress=ROOT/'_waves/progress/C2-USE.md'
steering=ROOT/'_waves/steer/C2-USE.md'
def steer():
    if steering.exists():
        print(steering.read_text())
        raise SystemExit('New steering exists; read and incorporate before running this reconciliation.')
def link(slug):
    return f'[{slug}](../../src/content/docs/{slug}.md)'
manual={
 'C0190':'use/account', 'C0197':'use/account',
 'C0307':'use/lists-and-filters', 'C0444':'use/change-sets',
 'C0626':'guide/use/load-the-next-version-of-a-workbook',
 'C0630':'use/home', 'C0644':'use/jobs','C0645':'use/jobs','C0646':'use/jobs','C0649':'use/jobs',
 'C0651':'use/records','C0653':'use/publications','C0717':'use/appearance-and-devices',
 'C0724':'use/history', 'C0745':'use/notifications-settings',
 'C0789':'use/records','C0796':'guide/use/replace-a-records-related-records',
 'C0835':'use/changing-many-records','C0836':'use/changing-many-records','C0837':'use/changing-many-records',
 'C0854':'guide/use/delete-many-records','C0861':'guide/use/stop-offering-a-value',
 'C0862':'use/appearance-and-devices','C0863':'use/appearance-and-devices',
 'C0865':'use/records','C0868':'use/history','C0870':'use/relationships',
 'C0919':'use/workspaces','C0920':'use/applications','C0921':'use/appearance-and-devices',
 'C0922':'use/appearance-and-devices','C0924':'use/appearance-and-devices',
 'C0951':'use/importing-and-exporting','C0991':'use/records',
 'C1010':'use/inbox-and-approvals','C1036':'use/inbox-and-approvals',
 'C1048':'use/jobs','C1056':'guide/use/delete-many-records',
 'C1071':'guide/use/change-values-of-many-records','C1074':'use/records',
 'C1173':'guide/use/change-relationships-of-many-records','C1174':'guide/use/delete-many-records',
 'C1175':'use/changing-many-records','C1181':'use/changing-many-records',
 'C1184':'use/lists-and-filters','C1189':'use/mapping-grids','C1193':'use/mapping-grids',
 'C1196':'guide/use/replace-a-records-related-records','C1203':'guide/use/change-relationships-of-many-records',
 'C1267':'use/history','C1268':'use/history','C1269':'use/lists-and-filters',
 'C1296':'use/applications','C1300':'use/appearance-and-devices',
 'C1309':'use/workspaces','C1310':'use/workspaces','C1314':'use/workspaces','C1315':'use/workspaces',
 'C3986':'use/records','C3997':'use/jobs','C4004':'use/lists-and-filters',
 'C4024':'use/notifications-settings','C4052':'use/notifications-settings','C4053':'use/notifications-settings',
}
ai_extra={'C0227','C0716','C0788','C0790'}
internal={'C0652':'routing inventory for model editors and deferred assistant pages; no steward task'}
path=ROOT/'_waves/coverage/use.md'
lines=path.read_text().splitlines()
changes=[]; handoffs=[]; deferred=[]
new=[]
for line in lines:
    if not line.startswith('| C'):
        new.append(line); continue
    cells=line.split('|'); ident=cells[1].strip(); old=cells[-2].strip()
    if 'after 0.16' in old:
        new.append(line); continue
    if 'partly' not in old and 'uncovered' not in old:
        new.append(line.replace('](../src/content/docs/','](../../src/content/docs/')); continue
    steer()
    if 'reconcile the cited release evidence' in old or ident in ai_extra:
        covered='after 0.16 — AI feature; deferred by COMPLETE-COMMON.md.'
        deferred.append(ident)
    elif ident in internal:
        covered='not for readers: '+internal[ident]
    else:
        use_targets=re.findall(r'(?:→ |\[)((?:guide/)?use/[\w-]+)',old)
        target=manual.get(ident) or (use_targets[0] if use_targets else None)
        others=list(dict.fromkeys(re.findall(r'(?:→ |\[)((?:guide/)?(?:model|administer|integrate|about|run)/[\w-]+)',old)))
        if target:
            page=ROOT/'src/content/docs'/f'{target}.md'
            assert page.exists(), (ident,target)
            covered=link(target)
            if target.startswith('guide/use/'):
                # Task pages link to the capability; the register can name both when already listed.
                pass
            if ident=='C0190': covered+=' — renewal is described; the token-reuse recovery interval is not a browser control.'
            if ident=='C0197': covered+=' — the signed-in browser account is covered here; API-console token use belongs to Integrate.'
            if ident in {'C1309','C1310','C1314','C1315'}:
                covered+='; '+link('model/managing-workspaces')+' (administration task; linked from Use)'
        else:
            assert others,(ident,old)
            covered='; '.join(link(slug) for slug in others)+' (other-reader handoff; outside C2-USE edit scope)'
            handoffs.append((ident,'; '.join(others),cells[2].strip()))
        if target and others:
            covered+='; other readers: '+ '; '.join(link(slug) for slug in others)+' (owned by their section waves)'
    cells[-2]=' '+covered+' '
    new.append('|'.join(cells))
    changes.append((ident,covered))
path.write_text('\n'.join(new)+'\n')
notes=ROOT/'_coverage/notes/C2-USE/coverage-resolution.md'
notes.write_text('# Coverage reconciliation\n\nThe saved pages predate this continuation. Each formerly open row was read from the register.\nTask rows now name their saved task; capability rows name the capability page. Misassigned\nrows (record failures under notifications, cell editing under jobs, ordinary ancestor filters\nunder AI) now name their actual reader-facing home. Sources and row item text are preserved.\nExisting AI deferrals are unchanged. Additional unreconciled assistant/AI release-evidence\nrows are explicitly deferred, without inventing browser instructions. Other-reader entries\nare handoffs, not claims that another wave has finished its writing.\n\n## Other-reader-only handoffs\n\n'+''.join(f'- {i}: {t} — {item}\n' for i,t,item in handoffs)+'\n## Newly recognised AI deferrals\n\n'+', '.join(deferred)+'\n\n## Resolved rows and destinations\n\n'+''.join(f'- {i}: {c}\n' for i,c in changes if i not in deferred))
with progress.open('a') as f:
    f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")} — `guide/_waves/coverage/use.md`. Reconciled {len(changes)} formerly open rows against the saved and completed pages; recognised {len(deferred)} additional AI deferrals and recorded {len(handoffs)} other-reader-only handoffs in working notes. Corrected the register\'s relative page links. Steering: none present.\n')
print(f'Reconciled {len(changes)} rows; {len(deferred)} newly marked AI deferrals; {len(handoffs)} other-reader-only handoffs.')
