exec(open('guide/_coverage/notes/C10-SCREENS/prepare-fourth-admin.py').read().split("add('admin-ai-settings'")[0])
add('notification-email-digest','Notification email and digest choices as actually saved for the reference administrator. Read only: do not enable email, alter preferences, follow a workspace, or send mail to an unverified address. An account email address is required to expose the controls. The master switch, mixed choices, saved zone/next digest and followed workspace from the original request are not guaranteed; review this image before claiming them.',[goto('/settings/notifications'),wait('Notification email'),wait('The digest')],['Notification email','Email me when something arrives in my inbox','How each kind reaches me','At once','Digest','Off','The digest','Workspaces I follow'],height=1500)
add('admin-agent-calls','Read the Agent access Calls section. Populated audit rows require existing real MCP calls, which the built-in assistant does not establish. No client, registration, grant or synthetic call is created for this picture; report empty Calls as an unmet prerequisite.',[goto('/settings/agent-access'),{'scrollTo':{'role':'heading','name':'Calls','exact':True}},wait('Arguments')],['Calls','When','Who','Through','Tool','Arguments','Outcome'],height=1100)
p=ROOT/'src/content/docs/use/notifications-settings.md';t=p.read_text();marker='## Follow publication in a workspace'
if '/docs/screens/notification-email-digest.png' not in t:
 t=t.replace(marker,'![Notification email delivery choices and the digest schedule options](/docs/screens/notification-email-digest.png)\n\n'+marker)
 p.write_text(t)
with (ROOT/'_waves/C10.data-changes.md').open('a') as f:f.write('''
## Resumed fourth-round preparation: mail and MCP reads (not executed)

`notification-email-digest` reads the current reference administrator's notification preferences. It does not turn on email, change the recipient, create a digest schedule, follow a workspace or send a test/digest. Mail being enabled does not establish that this account has its own configured address or the originally requested digest preferences. Capture the saved state if available and review the caption afterwards; otherwise report the missing account prerequisite. No address is invented.

`admin-agent-calls` reads existing MCP audit rows only. The built-in assistant's provider calls are a different log and cannot supply these rows. No external assistant is connected and no access/security setup is changed. A populated MCP call log is a capture prerequisite.
''')
save('mail and agent-call recipes','Applied fourth-round steering: restored `use/notifications-settings.md` with a caption for the actual saved choices and appended read-only mail/MCP-call recipes. No mail is sent or preference changed; account email, saved digest state and existing MCP rows remain external-capture prerequisites. C10-LATER removals are handed off because that file is outside this wave’s allowed files.')
