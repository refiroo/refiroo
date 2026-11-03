# MAIL-HTML: the mail page after branded messages

Every message refiroo sends (activation, password reset, the test message, an inbox notice, a digest) is now
multipart: the same plain text as before, plus a branded HTML version with the refiroo mascot and wordmark
embedded in the message (nothing is loaded from the server when it is opened). A model that names its own
product shows that name beside the wordmark. The content rules are unchanged: no record, change set,
workspace or person content. Source: `backend/app/engine/mail/html.py`, `smtp.py` (`build`), `templates.py`.

## Task

`administer/mail.md` says "Immediate notices are plain text". Correct that sentence to the facts above, and
add at most one or two plain sentences where the page describes the messages, if it has such a place. Change
nothing else.

## Files you may edit
- `src/content/docs/administer/mail.md`

## Report
The sentences you changed or added, before and after.
