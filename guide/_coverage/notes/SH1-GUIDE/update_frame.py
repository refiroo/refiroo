from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
changes={
'use/applications.md':[
('several views, shown as tabs.','several views, shown as tabs under the list’s title.'),
('**Browse records** offers another route to individual records through their hierarchy.','**Browse records** offers another route to individual records through their hierarchy. Open it to browse; it starts folded and remembers your choice in this browser.'),
('Open an application to reach the records and views you need in the current workspace.','Open an application to reach the records and views you need in the current workspace.\nChoose a workspace’s name or tile on Home to open its page: it offers record search, applications,\nyour waiting change sets and the five latest changes. **Edit model** and the workspace’s **⋯**\nmenu offer the actions and Settings pages your access allows.'),
('to **Home**, and the gear opens **Settings**.','to **Home**, and the gear opens **Settings**. Applications that do not fit are under **More**.\nSettings opens an index grouped by task. Inside Settings, **← Back to** followed by the workspace’s\nname returns to its page; each Settings page has one trail above its title.'),
('**Find a record**, under **Browse records**, searches records instead. The group page\'s','**Find any record** in the top bar searches record names across the workspace instead. Results\nare grouped by list and show each record’s place. Use the arrow keys to choose a result and\nEnter to open it. **Browse records** has no search box of its own. The group page\'s'),
],
'use/records.md':[
('records. The heading shows its ID and version.','records. This earlier view shows the ID and version directly in the heading; open **Details**\nin the current header to see them.'),
('The version beside a record\'s heading protects it from being overwritten by an older edit.','The version under **Details** in a record’s header protects it from being overwritten by an older edit.'),
('The header also has the record\'s ID with a copy button.','Open **Details** in the header for the record’s ID, its copy button and version.\n**Copy ID** is also in the record’s **⋯** menu.'),
('The path on a record\'s page shows its ancestors.','The line above a record’s title starts with **←** and the list’s name when you opened it from\na list, followed by its ancestors where the model shows them. Choose the list’s name to return.'),
('continue your newest change set. The band names it and its change count and says who publishes.','continue your newest change set. The band names it, its change count and state. Open **Details**\nfor who started it, when, its version and model.'),
],
'use/lists-and-filters.md':[
('position, including when you return with **Back to list**.','position, including when you return using **←** and the list’s name above a record’s title.'),
('The record heading takes focus when the page opens. **Back to list** returns to the saved\nconditions and position.','The record heading takes focus when the page opens. Choose **←** and the list’s name above\nthe title to return to the saved conditions and position.'),
('search page. The explorer\'s search can find records across its types; a collection\'s search\nstays within that collection.','search page. **Find any record** in the top bar searches record names across the workspace;\na collection’s search stays within that collection.'),
('fits. Rows stay on one line; an ellipsis marks a cut value.','fits. The name column stays whole; columns that do not fit fold behind **Columns · n of m**.\nChoose it to show all columns, scrolling sideways if needed. Other values stay on one line; an ellipsis marks a cut value.'),
],
'use/hierarchies.md':[
('workspace. The sidebar\'s **Browse records** tree is another route to records.','workspace. The sidebar’s **Browse records** tree is another route to records. Open its folded\nheading to browse; your choice is remembered in this browser. Use **Find any record** in the\ntop bar to search names across the workspace.'),
('A table record instead offers\n**Back to list**.','A table record instead offers\n**←** and the list’s name in the line above its title, followed by its parents where shown.'),
],
'use/change-sets.md':[
('its name, version and model release.','its name, version and model release in the change-set list; inside it, open **Details** in the\nband to read its source, creator, creation time, version and model.'),
('The orange **Change set** banner names the change set and says **Edits stay in this change set\nuntil it is published**.','The orange **Change set** band shows its name, number of changes and state in one row on a\ncomputer. Edits stay in this change set until it is published.'),
('**Review changes** compares the change set with its starting data.','Opening a change set from the list opens **Changes in this change set**, which compares it\nwith its starting data. Choose **See the data with these changes** to browse or edit its lists.\nA newly created change set, or your own open change set from Home’s **Continue where you left off**,\nopens on the data. From there, **Review changes** in the band opens the comparison.'),
],
'use/history.md':[
('Where your access opens workspace management, choose **Settings**, **Workspaces**, the workspace,','The workspace’s page shows its five **Latest changes**. For more activity, where your access\nopens workspace management, choose **Settings**, **Workspaces**, the workspace,'),
],
'use/inbox-and-approvals.md':[
('The banner shows\n**Waiting for approval**, the submitter, version and comment.','The band says **waits for approval**. Open **Details** for the submitter and submitted version,\nand the review’s **Decision** panel for the comment.'),
],
'guide/use/open-an-application.md':[
('2. Choose an application button on that card. Its default view opens in that workspace.\n   The application names come from the model.','2. Choose the workspace’s name or tile to open its page, then choose an application. Its\n   default view opens in that workspace. The application names come from the model. An\n   application link on the Home card opens that application directly.'),
('1. Select an application in the top bar. Read its sidebar collections; switching applications','1. Select an application in the top bar, using **More** if it does not fit. On a phone,\n   choose it in the band beneath the top bar. Read its sidebar collections; switching applications'),
],
'guide/use/continue-a-long-list.md':[
('Use **Back to list** to return with your search, filters, sort and position.','Choose **←** and the list’s name above the title to return with your search, filters, sort and position.'),
],
'guide/use/find-records.md':[
('1. On Home, find the workspace you need under **Your workspaces**. Choose an application on\n   its card. The application opens with that workspace selected.','1. On Home, find the workspace you need under **Your workspaces**. Choose its name or tile\n   to open its page, then choose an application. An application link on its card opens it directly.'),
('1. Type all or part of the record\'s name in the search box above the list.','1. To search names across the workspace, use **Find any record** in the top bar or **Find a\n   record** on the workspace’s page. Check the list and path beside a result; use the arrow\n   keys and Enter to open one. To search just this collection, type all or part of the record’s name in the search box above the list.'),
('4. Choose **Back to list** when finished.','4. Choose **←** and the list’s name above the title when finished.'),
('in full on hover, focus or long press. Return with **Back to list** after inspecting a record;','in full on hover, focus or long press. If columns have folded, choose **Columns · n of m**\n   to show them all. Return using **←** and the list’s name above the title after inspecting a record;'),
],
'guide/use/switch-workspace.md':[
('3. Choose an application button on that card. Check the sidebar and banner in the page that opens.','3. Choose the workspace’s name or tile to open its page, then choose an application.\n   Check the sidebar and banner in the application that opens.'),
],
'guide/use/correct-a-record.md':[
('1. Open the **…** menu beside the record version in the heading and choose **Edit record**.','1. Open the **…** menu in the record’s header and choose **Edit record**.\n   The record’s ID and version are under **Details**.'),
],
'guide/use/prepare-and-publish-a-change-set.md':[
('2. To continue existing work, find its name and choose **Open change set**. Check the name in\n   the banner before editing. Opening a change set does not publish it.','2. To continue existing work, find its name and choose **Open change set**. **Changes in this\n   change set** opens first. Choose **See the data with these changes** to reach its lists,\n   and check the name in the band before editing. Opening a change set does not publish it.'),
('1. Check the orange **Change set** banner. It must name the intended set and say **Edits stay in\n   this change set until it is published**. If the banner says **Live**, open your change set','1. Check the orange **Change set** band. It names the intended set, its number of changes\n   and state. Open **Details** for its creator, creation time, version and model. If the band\n   says **Live**, open your change set'),
('3. Choose **Back to change set** to correct anything unexpected.','3. Choose **See the data with these changes** to correct anything unexpected.'),
],
'guide/use/review-what-a-change-set-changes.md':[
('1. Open the change set and choose **Review changes** in its amber strip. Confirm the name\n   and source.','1. From **Change sets**, choose **Open change set** to open **Changes in this change set**.\n   If you are already browsing its data, choose **Review changes** in the amber band. Confirm\n   its name; open **Details** for its source.'),
('5. Return to editing for corrections, then choose **Validate change set**.','5. Choose **See the data with these changes** to return to editing for corrections, then\n   choose **Validate change set**.'),
],
'guide/use/approve-a-change-set.md':[
('workspace, name and version in the banner. Review the proposed records and relationships.','workspace and name in the band; open **Details** for its version. Review the proposed records and relationships.'),
('4. Check that the banner now says **Waiting for approval** and shows the submitted version,\n   your name and your comment.','4. Check that the band now says **waits for approval**. Open **Details** for the submitted\n   version and your name; read your comment in the review’s **Decision** panel.'),
],
'guide/model/edit-a-record-page.md':[
('3. Choose **Show the type’s name in the header** as needed. Set **Breadcrumbs start with the\n   application**, **Breadcrumbs name the type** and **Breadcrumbs name the records above it**\n   independently. These change this page’s context, not a record’s parent or name.','3. Choose **Show the type’s name in the header** as needed. **Breadcrumbs name the type**\n   also shows the type in the header; **Breadcrumbs name the records above it** shows parents\n   in the line above the title. That line starts with the list link when opened from a list,\n   without an application entry. These choices do not change a record’s parent or name.'),
],
'model/record-pages-and-tables.md':[
('subtitle field can supply other context. Breadcrumbs can include the application, type and\nancestors. In **Record page**, choose **Header and breadcrumbs…** to set the title, optional\nline under it, type label and each breadcrumb part.','subtitle field can supply other context. The line above the title holds the list link, when\nopened from a list, and the ancestors the model shows; it has no application entry. In **Record\npage**, choose **Header and breadcrumbs…** to set the title, optional line under it, type label\nand whether ancestors appear. Either type-name choice places the type in the header.'),
],
}
base=Path('guide/src/content/docs');log=Path('guide/_waves/progress/SH1-GUIDE.md')
for name,pairs in changes.items():
 steer=Path('guide/_waves/steer/SH1-GUIDE.md')
 if steer.exists() and steer.read_text().strip():raise SystemExit('Review steering: '+steer.read_text())
 p=base/name;text=p.read_text()
 for old,new in pairs:
  if old not in text:raise SystemExit(f'Missing exact text in {p}: {old}')
  text=text.replace(old,new)
 p.write_text(text)
 with log.open('a') as f:f.write(f'\n- {datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")} — `{p}`: Corrected the affected frame and navigation instructions against the implementation; retained structure and screenshot filenames. No steering file. Error-screen Back to list and model-preview application band remain where applicable.\n')
 print(p)
