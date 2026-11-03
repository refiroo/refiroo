from pathlib import Path
from collections import Counter
import json
from datetime import datetime
root = Path(__file__).resolve().parents[3]
ledger = root / '_waves/coverage/run.md'
def link(page, anchor=''):
    return f'[{page}{anchor}](../../src/content/docs/{page}.md{anchor})'
updates = {}
def setrows(ids, page, anchor=''):
    for row in ids.split(): updates[row] = link(page, anchor)
setrows('C2600 C2601 C2610 C2616 C2735 C2838', 'run/sign-in-and-mail-setup')
setrows('C2580 C2615 C2618 C4003', 'run/background-jobs')
setrows('C2602 C2604 C2629 C2630 C2709 C2711 C2713 C2736 C2788 C2789 C2799 C2806 C2866 C2923 C2924', 'run/configure')
setrows('C2622 C2624 C2759 C2768 C2795 C2800 C2801 C2807', 'run/monitoring')
setrows('C2623 C2758 C2770 C2802', 'run/backup-and-restore')
setrows('C2715 C2732 C2808 C2835 C2836 C2837', 'run/several-processes')
setrows('C2613 C2707 C2714 C2734 C2925 C2926 C2936 C3963', 'run/webhook-delivery')
setrows('C2779 C3928 C4001', 'run/troubleshooting')
setrows('C2790', 'run/licence-and-source')
setrows('C4030 C4002', 'run/health-and-startup-checks')
setrows('C2796', 'run/overview')
setrows('C2819 C2824 C2825', 'run/configure')
setrows('C2820 C2821', 'run/monitoring')
setrows('C2755', 'run/model-releases-and-rollback')
setrows('C2574 C2575 C2576 C2577 C2578 C2579 C2581 C2583 C2584 C2722 C2723', 'run/configure', '#batch-file-and-retention-limits')
updates['C4001'] += '; integrator: ' + link('integrate/identifiers-paging-and-errors') + '; lease recovery: ' + link('run/several-processes')
updates['C4003'] += '; integrator: ' + link('integrate/jobs')
updates['C4030'] += '; model administrator: ' + link('model/model-language-versions') + '; steward: ' + link('use/workspaces')
updates['C2714'] += '; integration sequence: ' + link('guide/integrate/subscribe-a-webhook-and-verify-it')
updates['C2796'] += '; integrator: ' + link('integrate/files-imports-and-exports') + ', ' + link('integrate/following-changes')
deferred = {
 'C2607':'AI call history; explicitly ai-later in the screen inventory.',
 'C2608':'AI provider/assistant screen; explicitly ai-later in the screen inventory.',
 'C2679':'AI summary language rule AO-D8; not an operator environment setting.',
 'C2748':'AI summary fact aggregation AO-D3; no separate database task for an operator.',
 'C2797':'AI setup notice; explicitly ai-later in the screen inventory.',
 'C2798':'AI provider test; explicitly ai-later in the screen inventory.',
 'C2871':'Assistant whole-type proposal checks AP12; not an application upgrade procedure.',
 'C2872':'Assistant whole-type proposal checks AP12; not an application upgrade procedure.',
 'C2906':'AI proposal provenance AP2; its database migration uses the ordinary upgrade procedure.',
 'C2919':'Assistant choice of model migration versus per-record restructuring AP12.',
}
for row in deferred: updates[row]='after 0.16'
updates['C2747']='not for readers: AI-summary test strategy and fake-provider evidence, not an operator action or setting.'
lines=[]
counts=Counter()
for line in ledger.read_text().splitlines():
    if line.startswith('| C'):
        cells = [part.strip() for part in line.split('|')[1:-1]]
        cells[-1] = updates.get(cells[0], cells[-1]).replace('(../src/', '(../../src/')
        assert 'uncovered' not in cells[-1] and 'partly:' not in cells[-1], cells[0]
        assert cells[-1]
        counts['deferred' if cells[-1]=='after 0.16' else 'not for readers' if cells[-1].startswith('not for readers:') else 'covered']+=1
        line='| '+' | '.join(cells)+' |'
    lines.append(line)
ledger.write_text('\n'.join(lines)+'\n')
(root/'_coverage/notes/C5-RUN/coverage-resolution.json').write_text(json.dumps({'counts':dict(counts),'updates':updates,'additional_ai_deferrals':deferred},indent=2)+'\n')
with (root/'_waves/progress/C5-RUN.md').open('a') as f:
    f.write(f'\n- {datetime.now().astimezone().isoformat(timespec="seconds")}: Finished `_waves/coverage/run.md`: {dict(counts)}. Every non-deferred reader row has a concrete page; corrected relative links and removed stale partial/uncovered labels. Ten misrouted AI rows are deferred with source-based reasons in the working notes; one AI test-strategy row is internal. No steering file present.\n')
print(dict(counts))
