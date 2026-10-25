"""The engine's own pages: signing in and setting a password (Product 0.12 I2, I3, U8, D275).

Plain HTML built here with every value escaped: no template library and no script, so nothing on
the page can read a password. The colours are the app's tokens (``frontend/src/styles/tokens.css``),
light or dark by the device. Every page is sent with a policy that allows no script, no framing and
form posts to the engine alone, redirecting to the browser's origins (D267).
"""

from html import escape
from urllib.parse import urlsplit

from fastapi.responses import HTMLResponse

_STYLE = """
:root{--surface-sunken:#f6f5f2;--surface-raised:#fff;--text-primary:#1d1c1a;--text-secondary:#55524c;
--text-tertiary:#69655e;--text-on-action:#fff;--border-subtle:#e4e2dc;--border-control:#8a867d;
--action:#3346c9;--action-soft:#eceefc;--focus:#3346c9;--warn-s:#fff6e3;--warn-t:#6f3d06;
--err-s:#fdf0ee;--err-t:#7a1f17;--err-m:#b42318;--ok-s:#e5f3ea;--ok-t:#1b5e3a;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--surface-sunken:#1f1f23;--surface-raised:#18181b;
--text-primary:#ececee;--text-secondary:#b4b3ba;--text-tertiary:#9a99a1;--text-on-action:#10153d;
--border-subtle:#2c2c31;--border-control:#74737c;--action:#8e9bff;--action-soft:#23284a;
--focus:#8e9bff;--warn-s:#2e2312;--warn-t:#f3cf8a;--err-s:#311816;--err-t:#ffb4a8;--err-m:#ff8a7a;
--ok-s:#16291f;--ok-t:#9fdcb7;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:var(--surface-sunken);color:var(--text-primary);
font:14px/1.45 "Instrument Sans Variable","Instrument Sans",ui-sans-serif,system-ui,sans-serif;
display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;padding:24px 16px}
.brand{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:600}
main{width:100%;max-width:400px;background:var(--surface-raised);border:1px solid var(--border-subtle);
border-radius:12px;padding:32px;display:flex;flex-direction:column;gap:18px}
h1{margin:0;font-size:22px;font-weight:600}
form{display:flex;flex-direction:column;gap:14px;margin:0}
label{display:block;font-size:13px;font-weight:500;margin-bottom:6px}
input{height:40px;width:100%;border:1px solid var(--border-control);border-radius:6px;padding:0 12px;
background:var(--surface-raised);color:var(--text-primary);font:inherit}
input[aria-invalid=true]{border-color:var(--err-m)}
button{height:40px;width:100%;border-radius:6px;border:1px solid var(--action);background:var(--action);
color:var(--text-on-action);font:inherit;font-weight:500;cursor:pointer}
a.button{display:flex;align-items:center;justify-content:center;height:40px;border-radius:6px;
border:1px solid var(--border-control);background:var(--surface-raised);color:var(--text-primary);
font-weight:500;text-decoration:none}
a.button.primary{background:var(--action);border-color:var(--action);color:var(--text-on-action)}
.or{display:flex;align-items:center;gap:10px;color:var(--text-tertiary);font-size:12px}
.or::before,.or::after{content:"";flex:1;height:1px;background:var(--border-subtle)}
input:focus-visible,button:focus-visible,a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.note{margin:0;padding:10px 12px;border-radius:8px;font-size:13px}
.note.info{background:var(--action-soft)}.note.error{background:var(--err-s);color:var(--err-t)}
.note.warn{background:var(--warn-s);color:var(--warn-t)}.note.ok{background:var(--ok-s);color:var(--ok-t)}
.hint{display:block;margin-top:6px;font-size:12px;color:var(--text-tertiary)}
.aside{margin:0;font-size:13px;color:var(--text-secondary)}
a{color:var(--action)}a:hover{color:var(--text-primary)}
@media (max-width:480px){body{justify-content:flex-start;background:var(--surface-raised);padding-top:48px}
main{border:0;padding:0}}
"""

_MARK = (
    '<svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><rect x="2" y="2" '
    'width="24" height="24" rx="6" fill="none" stroke="currentColor" stroke-width="2"></rect>'
    '<path d="M9 10h10M9 14h10M9 18h6" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round"></path></svg>'
)


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _headers(issuer: str, redirect_origins: tuple[str, ...]) -> dict[str, str]:
    targets = " ".join(dict.fromkeys(["'self'", _origin(issuer), *redirect_origins]))
    return {
        "Content-Security-Policy": (
            "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; "
            f"form-action {targets}; frame-ancestors 'none'; base-uri 'none'"
        ),
        "X-Frame-Options": "DENY",
        "Cache-Control": "no-store",
        "Referrer-Policy": "same-origin",
        "X-Content-Type-Options": "nosniff",
    }


def _page(
    title: str,
    product: str,
    body: str,
    *,
    issuer: str,
    redirect_origins: tuple[str, ...],
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)} · {escape(product)}</title><style>{_STYLE}</style></head><body>"
        f'<header class="brand">{_MARK}<span>{escape(product)}</span></header>'
        f"<main>{body}</main></body></html>"
    )
    return HTMLResponse(
        html,
        status_code=status,
        headers={**_headers(issuer, redirect_origins), **(headers or {})},
    )


def _note(kind: str, text: str) -> str:
    role = ' role="alert"' if kind in ("error", "warn") else ""
    return f'<p class="note {kind}"{role}>{escape(text)}</p>'


def _hidden(fields: dict[str, str]) -> str:
    return "".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in fields.items()
    )


def wait_text(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    minutes = (seconds + 59) // 60
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def sign_in(
    product: str,
    request_fields: dict[str, str],
    *,
    issuer: str,
    redirect_origins: tuple[str, ...],
    username: str = "",
    ended: bool = False,
    wrong: bool = False,
    wait_seconds: int = 0,
    status: int = 200,
    providers: tuple[tuple[str, str], ...] = (),
    local: bool = True,
    local_link: str | None = None,
) -> HTMLResponse:
    """The sign-in page: the authorization request's fields travel in the form, hidden. Each of
    ``providers`` (name, start address) is a "Continue with" button below the form (I3). With local
    sign-in off the page shows the buttons and a link to ``local_link``, where the form is shown
    with ``local`` false for the administrators who keep it (D365)."""
    buttons = "".join(
        f'<a class="button" href="{escape(url)}">Continue with {escape(name)}</a>'
        for name, url in providers
    )
    if local_link is not None:
        ended_note = (
            _note("info", "Your session ended. Sign in again to return to where you were.")
            if ended
            else ""
        )
        body = (
            "<h1>Sign in</h1>"
            + ended_note
            + buttons.replace('class="button"', 'class="button primary"')
            + f'<p class="aside"><a href="{escape(local_link)}">Sign in with a local administrator '
            + "account</a></p>"
        )
        return _page(
            "Sign in", product, body, issuer=issuer, redirect_origins=redirect_origins, status=status
        )
    notes = []
    if ended:
        notes.append(
            _note("info", "Your session ended. Sign in again to return to where you were.")
        )
    if wrong:
        notes.append(
            _note("error", "The username or password is not right. Check both and try again.")
        )
    if wait_seconds:
        notes.append(
            _note(
                "warn",
                "Too many attempts for this account or from this address. You can try again in "
                f"{wait_text(wait_seconds)}. An administrator can reset the password.",
            )
        )
    invalid = ' aria-invalid="true" aria-describedby="sign-in-problem"' if wrong else ""
    if wrong:
        notes[-1] = notes[-1].replace("<p ", '<p id="sign-in-problem" ', 1)
    body = (
        "<h1>Sign in</h1>"
        + "".join(notes)
        + '<form method="post" action="/oauth/authorize">'
        + _hidden(request_fields)
        + '<div><label for="username">Username</label>'
        + f'<input id="username" name="username" value="{escape(username)}" '
        + 'autocomplete="username" autocapitalize="none" spellcheck="false" required'
        + ("" if username else " autofocus")
        + "></div>"
        + '<div><label for="password">Password</label>'
        + '<input id="password" name="password" type="password" '
        + f'autocomplete="current-password" required{invalid}'
        + (" autofocus" if username else "")
        + "></div>"
        + '<button type="submit">Sign in</button></form>'
        + (
            ""
            if local
            else '<p class="aside">Only administrators made on the server sign in with a password '
            "here.</p>"
        )
        + (f'<p class="or">or</p>{buttons}' if buttons else "")
        + (
            '<p class="aside">Forgotten your password? Ask a security administrator for a reset '
            "link.</p>"
            if local
            else ""
        )
    )
    headers = {"Retry-After": str(wait_seconds)} if wait_seconds else None
    return _page(
        "Sign in",
        product,
        body,
        issuer=issuer,
        redirect_origins=redirect_origins,
        status=status,
        headers=headers,
    )


def problem(
    product: str, text: str, *, issuer: str, redirect_origins: tuple[str, ...], status: int = 400
) -> HTMLResponse:
    """A request the page cannot serve, explained; nothing is redirected."""
    body = "<h1>This sign-in cannot go on</h1>" + _note("error", text)
    return _page(
        "Sign in",
        product,
        body,
        issuer=issuer,
        redirect_origins=redirect_origins,
        status=status,
    )


def provider_problem(
    product: str,
    provider_name: str,
    text: str,
    *,
    retry_url: str | None,
    issuer: str,
    redirect_origins: tuple[str, ...],
    status: int = 400,
) -> HTMLResponse:
    """A provider sign-in that cannot finish, with the reason and a way to start again (D368)."""
    retry = f'<a class="button primary" href="{escape(retry_url)}">Try again</a>' if retry_url else ""
    body = f"<h1>{escape(provider_name)} could not sign you in</h1>" + _note("error", text) + retry
    return _page(
        "Sign in", product, body, issuer=issuer, redirect_origins=redirect_origins, status=status
    )


def password(
    product: str,
    token: str,
    *,
    issuer: str,
    redirect_origins: tuple[str, ...],
    username: str,
    min_length: int,
    message: str | None = None,
    status: int = 200,
) -> HTMLResponse:
    """The reset link's page: a new password, twice."""
    note = _note("error", message) if message else ""
    invalid = ' aria-invalid="true" aria-describedby="password-problem"' if message else ""
    if message:
        note = note.replace("<p ", '<p id="password-problem" ', 1)
    body = (
        "<h1>Set your password</h1>"
        + f'<p class="aside">For <strong>{escape(username)}</strong>.</p>'
        + note
        + '<form method="post" action="/oauth/password">'
        + _hidden({"token": token})
        + f'<input type="hidden" name="username" value="{escape(username)}" '
        + 'autocomplete="username">'
        + '<div><label for="new-password">New password</label>'
        + '<input id="new-password" name="password" type="password" autocomplete="new-password" '
        + f'aria-describedby="password-rule" required autofocus{invalid}>'
        + f'<small id="password-rule" class="hint">At least {min_length} characters. A phrase of '
        + "several words is easiest to remember.</small></div>"
        + '<div><label for="repeat-password">Repeat the password</label>'
        + '<input id="repeat-password" name="repeat" type="password" autocomplete="new-password" '
        + "required></div>"
        + '<button type="submit">Set password</button></form>'
    )
    return _page(
        "Set your password",
        product,
        body,
        issuer=issuer,
        redirect_origins=redirect_origins,
        status=status,
    )


def password_set(
    product: str, *, app_url: str | None, issuer: str, redirect_origins: tuple[str, ...]
) -> HTMLResponse:
    """The password is set; the person goes on to sign in."""
    link = (
        f'<p class="aside"><a href="{escape(app_url)}">Go to {escape(product)} and sign in</a></p>'
        if app_url
        else ""
    )
    body = (
        "<h1>Your password is set</h1>"
        + _note("ok", "Sign in with your username and the new password.")
        + link
    )
    return _page("Password set", product, body, issuer=issuer, redirect_origins=redirect_origins)
