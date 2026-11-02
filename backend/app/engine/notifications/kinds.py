"""The kinds of inbox notice, each with a plain label (Product 0.12 M2 follow-up, D434).

One home for the list: a person chooses by kind which notices reach them by mail, the page shows
these labels, and the mail names the kind in the same words. The kinds are those the engine makes:
a change set submitted, approved or sent back (``engine/change_sets/announcements.py``) and a job
that finished, failed or waits for confirmation (the ``jobs_inbox`` trigger), and a change set
published in a workspace the person follows (``notifications/following.py``, 0.16 AO3).
"""

# (kind, label) in the order a person sees them.
NOTICE_KINDS: tuple[tuple[str, str], ...] = (
    ("change-set.submitted", "A change set is waiting for your approval"),
    ("change-set.approved", "A change set you submitted was approved"),
    ("change-set.sent-back", "A change set you submitted was sent back"),
    ("job.completed", "A job you started has finished"),
    ("job.failed", "A job you started has failed"),
    ("job.awaiting-confirmation", "A job you started is waiting for your confirmation"),
    ("change-set.published", "A change set was published in a workspace you follow"),
)

LABELS: dict[str, str] = dict(NOTICE_KINDS)
