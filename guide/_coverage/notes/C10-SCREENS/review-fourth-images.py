from pathlib import Path
from datetime import datetime
b=Path('guide');d=b/'src/content/docs'
changes={
'administer/ai.md': [('AI settings showing both switches, the send level and available features','AI settings showing the assistant and provider on, the send level and available features'),('AI calls with outcomes, token counts, costs and a failure reason','Answered AI provider calls with token counts, duration and unreported costs')],
'run/ai.md':[('AI settings showing both switches and the permitted send level','AI settings showing the assistant and provider on and the permitted send level')]
}
for rel,replacements in changes.items():
 p=d/rel;t=p.read_text()
 for old,new in replacements:t=t.replace(old,new)
 p.write_text(t)
(b/'_coverage/notes/C10-SCREENS/fourth-capture-image-review.md').write_text('''# Fourth capture: ten attached images reviewed

| Image | Page comparison and finding |
| --- | --- |
| admin-ai-settings | Accepted. Assistant/provider are status rows, not switches. Corrected administer/ai.md caption. Provider claude-code, model sonnet, values allowed, content not kept, 60-second timeout. Calls empty at this initial capture. No key value displayed. |
| run-ai-settings | Accepted. Same configuration; corrected run/ai.md caption from switches to statuses. |
| use-record-history-explained | Accepted. Chur Wiesental History has inclusive Oct 1–Nov 3 dates, four AI statements with citations, 8 engine facts and Show it/Show them. Lower facts continue below the image; caption does not claim all are visible. |
| model-account-before-request | Accepted. Activation review is incompatible, with sending disclosure and Explain this change. No activation performed by the recipe. |
| model-account-facts | Accepted. Activation review has statements/citations and 183 facts, first ten visible plus Show the other 173. It is not an Apply dialog. Existing captions match. Footer is below the viewport; cancellation is supported by the ok log, not visible in this image. |
| admin-ai-test-answered | Accepted. Answered by sonnet in 3,348 ms, Test request row, tokens and unreported cost. No failure visible. |
| run-ai-provider-calls | Accepted. Same test result and log reused without another test. |
| admin-ai-calls | Accepted for provider calls. Four calls, all answered; visible Test request, mapping targets and model-change account. Costs are dashes and no failure reason/assistant turn appears. Corrected caption accordingly. |
| model-assistant-change-dialog | Accepted. Workspace, empty What should change?, optional workbook and disclosure visible. Ask the assistant disabled while empty. Existing caption matches. |
| use-assistant-workbook | Accepted. Workbook chosen, Into Graubünden, optional words and sending note, Read the workbook and Import without the assistant… visible. Existing caption matches. |

No failed-image appearance was supplied except the mapping result, which must be inspected separately from its local file. No new image was generated or edited. These ten images do not establish the success of the failed recipes.
''')
with (b/'_waves/progress/C10-SCREENS.md').open('a') as f:f.write('\n## '+datetime.now().astimezone().isoformat(timespec='seconds')+' — fourth-capture image review\n\nReviewed all ten attached images against their pages; corrected `administer/ai.md` and `run/ai.md` captions to status rows and answered calls with unreported cost. Saved per-image evidence in `fourth-capture-image-review.md`; steering reread, and the latest user instruction supplies the new wait timeout.\n')
