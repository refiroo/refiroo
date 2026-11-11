"""The engine's own pages: signing in and setting a password (Product 0.12 I2, I3, U8, D275).

Plain HTML built here with every value escaped: no template library, so nothing on the page can
read a password. The colours are the app's tokens (``frontend/src/styles/tokens.css``), light or
dark by the device. A page is sent with a policy that allows no script, no framing and form posts to
the engine alone, redirecting to the browser's origins (D267). Only a page that offers a passkey
(I4c, D390) loads a script, the engine's own ``/oauth/passkey.js`` and no other: ``script-src
'self'``, nothing inline.
"""

from html import escape
from urllib.parse import urlsplit

from fastapi.responses import HTMLResponse

from ..common.brand import is_default_product_name

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
.brand img{display:block;height:36px;width:auto}.brand img.wordmark{height:20px}
.brand strong{padding-left:12px;border-left:1px solid var(--border-subtle);font-weight:600}
@media (prefers-color-scheme:dark){.brand img.wordmark{filter:brightness(0) invert(.93)}}
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
input.code{font-family:ui-monospace,"JetBrains Mono",monospace;font-size:18px;letter-spacing:6px}
.mono{font-family:ui-monospace,"JetBrains Mono",monospace;font-size:13px}
form.inline{display:inline;margin:0}
button.link{display:inline;width:auto;height:auto;padding:0;border:0;background:none;color:var(--action);
font:inherit;text-decoration:underline;cursor:pointer}
button.link:hover{color:var(--text-primary)}
button.button{display:flex;align-items:center;justify-content:center;gap:8px}
.qr{display:flex;gap:16px;align-items:center}.qr svg{width:132px;height:132px;flex:none;border-radius:4px}
.qr code{display:block;margin-top:6px;color:var(--text-primary);overflow-wrap:break-word}
.codes{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;padding:12px;border-radius:8px;
background:var(--surface-sunken)}
.welcome{margin:-12px 0 0;max-width:400px;text-align:center;color:var(--text-secondary)}
.welcome strong{display:block;font-size:16px;font-weight:600;color:var(--text-primary)}
@media (max-width:480px){body{justify-content:flex-start;background:var(--surface-raised);padding-top:48px}
main{border:0;padding:0}}
"""


def _mark(product: str) -> str:
    """The refiroo mascot and wordmark; a model's own product name stands beside them."""
    instance = "" if is_default_product_name(product) else f"<strong>{escape(product)}</strong>"
    return (
        '<img src="/brand/refiroo-mascot.png" alt="" width="36" height="36">'
        '<img class="wordmark" src="/brand/refiroo-wordmark.png" alt="refiroo" height="20">'
        + instance
    )


_WELCOME = (
    '<p class="welcome"><strong>Reference data that stays in step.</strong>'
    "Every code, category and mapping, kept tidy so everything else can trust it.</p>"
)


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _headers(
    issuer: str, redirect_origins: tuple[str, ...], script: bool = False
) -> dict[str, str]:
    targets = " ".join(dict.fromkeys(["'self'", _origin(issuer), *redirect_origins]))
    scripts = "script-src 'self'; connect-src 'self'; " if script else ""
    return {
        "Content-Security-Policy": (
            f"default-src 'none'; {scripts}style-src 'unsafe-inline'; img-src 'self'; "
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
    script: bool = False,
    welcome: bool = False,
) -> HTMLResponse:
    loaded = '<script src="/oauth/passkey.js" defer></script>' if script else ""
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)} · refiroo</title>"
        '<link rel="icon" href="/brand/favicon.png">'
        f"<style>{_STYLE}</style></head><body>"
        f'<header class="brand">{_mark(product)}</header>'
        f"{_WELCOME if welcome else ''}"
        f"<main>{body}</main>{loaded}</body></html>"
    )
    return HTMLResponse(
        html,
        status_code=status,
        headers={**_headers(issuer, redirect_origins, script), **(headers or {})},
    )


_PASSKEY_ICON = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="9" cy="8" r="4">'
    '</circle><path d="M2 21c0-4 3-6 7-6 1.5 0 2.8.3 3.9.8"></path><circle cx="18" cy="15" r="2.5">'
    '</circle><path d="M18 17.5V22M18 20h2"></path></svg>'
)
_PASSKEY_NOTE = '<p id="passkey-note" class="note error" role="alert" hidden></p>'


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


def _assistant_note(assistant: tuple[str, str]) -> str:
    name, returns_to = assistant
    return (
        '<div class="note info" role="note"><p><strong>An assistant asks to work as you.</strong> '
        f"It calls itself <strong>{escape(name)}</strong>. After you sign in it returns to "
        f"<strong>{escape(returns_to)}</strong>.</p><p>It can read what you can read and prepare "
        "changes for approval. It can't approve or publish. If you didn't start this, close this "
        "page.</p></div>"
    )


def sign_in(
    product: str,
    request_fields: dict[str, str],
    *,
    issuer: str,
    redirect_origins: tuple[str, ...],
    email: str = "",
    ended: bool = False,
    wrong: bool = False,
    wait_seconds: int = 0,
    status: int = 200,
    providers: tuple[tuple[str, str], ...] = (),
    local: bool = True,
    local_link: str | None = None,
    passkey: bool = False,
    assistant: tuple[str, str] | None = None,
) -> HTMLResponse:
    """The sign-in page: the authorization request's fields travel in the form, hidden. With
    ``assistant`` (the name it claims, where it returns) the page says who asks and signing in is
    the consent (0.16 AG-D13). With
    ``passkey`` it offers **Sign in with a passkey** above the form (I4c) and loads the engine's
    script. Each of
    ``providers`` (name, start address) is a "Continue with" button below the form (I3). With local
    sign-in off the page shows the buttons and a link to ``local_link``, where the form is shown
    with ``local`` false for the administrators who keep it (D365)."""
    allow = " and allow" if assistant else ""
    buttons = "".join(
        f'<a class="button" href="{escape(url)}">Continue with {escape(name)}{allow}</a>'
        for name, url in providers
    )
    asking = _assistant_note(assistant) if assistant else ""
    if local_link is not None:
        ended_note = (
            _note("info", "Your session ended. Sign in again to return to where you were.")
            if ended
            else ""
        )
        body = (
            "<h1>Sign in</h1>"
            + asking
            + ended_note
            + buttons.replace('class="button"', 'class="button primary"')
            + f'<p class="aside"><a href="{escape(local_link)}">Sign in with a local administrator '
            + "account</a></p>"
        )
        return _page(
            "Sign in",
            product,
            body,
            issuer=issuer,
            redirect_origins=redirect_origins,
            status=status,
            welcome=True,
        )
    notes = []
    if ended:
        notes.append(
            _note("info", "Your session ended. Sign in again to return to where you were.")
        )
    if wrong:
        notes.append(
            _note("error", "The e-mail address or password is not right. Check both and try again.")
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
    offer = (
        '<button type="button" class="button primary" data-passkey="login">'
        f"{_PASSKEY_ICON}Sign in with a passkey{allow}</button>"
        + _PASSKEY_NOTE
        + '<p class="or">or with a password</p>'
        if passkey
        else ""
    )
    body = (
        "<h1>Sign in</h1>"
        + asking
        + "".join(notes)
        + offer
        + '<form method="post" action="/oauth/authorize">'
        + _hidden(request_fields)
        + '<div><label for="email">E-mail address</label>'
        + f'<input id="email" name="email" value="{escape(email)}" '
        + 'autocomplete="username" autocapitalize="none" spellcheck="false" required'
        + ("" if email else " autofocus")
        + "></div>"
        + '<div><label for="password">Password</label>'
        + '<input id="password" name="password" type="password" '
        + f'autocomplete="current-password" required{invalid}'
        + (" autofocus" if email else "")
        + "></div>"
        + f'<button type="submit">Sign in{allow}</button></form>'
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
        script=passkey,
        welcome=True,
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
    retry = (
        f'<a class="button primary" href="{escape(retry_url)}">Try again</a>' if retry_url else ""
    )
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
    email: str,
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
        + f'<p class="aside">For <strong>{escape(email)}</strong>.</p>'
        + note
        + '<form method="post" action="/oauth/password">'
        + _hidden({"token": token})
        + f'<input type="hidden" name="email" value="{escape(email)}" '
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
        + _note("ok", "Sign in with your e-mail address and the new password.")
        + link
    )
    return _page("Password set", product, body, issuer=issuer, redirect_origins=redirect_origins)


def _recovery_form(step: str, *, wrong: bool, wait_seconds: int) -> str:
    """The recovery code step: one field, the code as it was written down."""
    notes = _factor_notes(wrong, wait_seconds)
    invalid = ' aria-invalid="true" aria-describedby="code-problem"' if wrong else ""
    return (
        "<h1>Use a recovery code</h1>"
        '<p class="aside">One of the ten codes you kept when you set up the authenticator app. '
        "Each works once.</p>"
        + notes
        + '<form method="post" action="/oauth/second-factor">'
        + _hidden({"step": step})
        + '<div><label for="recovery">Recovery code</label>'
        + '<input id="recovery" name="recovery" class="mono" autocomplete="off" '
        + f'autocapitalize="none" spellcheck="false" required autofocus{invalid}></div>'
        + '<button type="submit">Sign in</button></form>'
    )


def _factor_notes(wrong: bool, wait_seconds: int) -> str:
    notes = ""
    if wrong:
        notes += _note(
            "error",
            "That code is not right, or was already used. Wait for the next one and try again.",
        ).replace("<p ", '<p id="code-problem" ', 1)
    if wait_seconds:
        notes += _note(
            "warn",
            "Too many wrong codes for this account or from this address. You can try again in "
            f"{wait_text(wait_seconds)}. An administrator can reset the second factor.",
        )
    return notes


def _link_button(step: str, view: str, text: str) -> str:
    return (
        '<form method="post" action="/oauth/second-factor" class="inline">'
        + _hidden({"step": step})
        + f'<button type="submit" class="link" name="view" value="{view}">{escape(text)}</button>'
        "</form>"
    )


def second_factor_code(
    product: str,
    step: str,
    email: str,
    *,
    start_again: str,
    issuer: str,
    redirect_origins: tuple[str, ...],
    recovery: bool = False,
    wrong: bool = False,
    wait_seconds: int = 0,
    status: int = 200,
    app: bool = True,
    passkey: bool = False,
) -> HTMLResponse:
    """The second step after the right password: a code from the authenticator app, a recovery code,
    or, with ``passkey`` (I4c), one of the person's passkeys, which loads the engine's script. A
    person with only passkeys (``app`` false) sees no code field. The step's token is the form's
    only state."""
    if recovery and app:
        body = (
            _recovery_form(step, wrong=wrong, wait_seconds=wait_seconds)
            + '<p class="aside">Lost the codes too? A security administrator can remove your '
            "second factor.</p>"
            + '<div class="aside">'
            + _link_button(step, "code", "Use the app's code")
            + "</div>"
        )
        title = "Use a recovery code"
    else:
        invalid = ' aria-invalid="true" aria-describedby="code-problem"' if wrong else ""
        who = f'<p class="aside">Signing in as <strong>{escape(email)}</strong>. '
        if passkey:
            heading = "Confirm it is you"
            intro = who + (
                "Use one of your passkeys, or the code from your authenticator app.</p>"
                if app
                else "Use one of your passkeys.</p>"
            )
        else:
            heading = "Enter your code"
            intro = who + (
                "Open your authenticator app and type the six-digit code for "
                f"{escape(product)}.</p>"
            )
        offer = (
            f'<button type="button" class="button primary" data-passkey="second" '
            f'data-step="{escape(step)}">{_PASSKEY_ICON}Use a passkey</button>' + _PASSKEY_NOTE
            if passkey
            else ""
        )
        divider = '<p class="or">or</p>' if passkey and app else ""
        code_form = (
            '<form method="post" action="/oauth/second-factor">'
            + _hidden({"step": step})
            + '<div><label for="code">'
            + ("Code from the app" if passkey else "Code")
            + "</label>"
            + '<input id="code" name="code" class="code" inputmode="numeric" '
            + 'autocomplete="one-time-code" required'
            + (" autofocus" if not passkey else "")
            + f"{invalid}></div>"
            + '<button type="submit">'
            + ("Sign in with the code" if passkey else "Sign in")
            + "</button></form>"
            if app
            else ""
        )
        body = (
            f"<h1>{heading}</h1>"
            + intro
            + _factor_notes(wrong, wait_seconds)
            + offer
            + divider
            + code_form
            + '<div class="aside">'
            + (_link_button(step, "recovery", "Use a recovery code instead") + " · " if app else "")
            + f'<a href="{escape(start_again)}">Start again</a></div>'
        )
        title = heading
    headers = {"Retry-After": str(wait_seconds)} if wait_seconds else None
    return _page(
        title, product, body, issuer=issuer, redirect_origins=redirect_origins, status=status,
        headers=headers, script=passkey and not recovery,
    )  # fmt: skip


def passkey_add(
    product: str,
    email: str,
    return_to: str,
    *,
    issuer: str,
    redirect_origins: tuple[str, ...],
) -> HTMLResponse:
    """The engine's own page for adding a passkey: the person's session is the page's, the name is
    asked, and the engine's script runs the browser's prompt (I4c, D392). Where the relying party's
    host is the engine's, a passkey made here works on the sign-in page."""
    body = (
        "<h1>Add a passkey</h1>"
        f'<p class="aside">For <strong>{escape(email)}</strong>. Your browser will ask you to '
        "confirm with your fingerprint, face, device PIN or security key.</p>"
        + _PASSKEY_NOTE
        + '<div><label for="passkey-name">Name it</label>'
        + '<input id="passkey-name" name="name" maxlength="100" value="Passkey" '
        + 'autocomplete="off" aria-describedby="passkey-name-help">'
        + '<small id="passkey-name-help" class="hint">So you can tell your passkeys apart on '
        + "Account.</small></div>"
        + '<div><label for="passkey-proof">Your password, or a code from your app</label>'
        + '<input id="passkey-proof" name="proof" type="password" autocomplete="current-password" '
        + 'required aria-describedby="passkey-proof-help">'
        + '<small id="passkey-proof-help" class="hint">Asked again because a passkey signs you in '
        + "without a password.</small></div>"
        + f'<button type="button" data-passkey="register" data-return="{escape(return_to)}">'
        + "Create passkey</button>"
        + f'<p class="aside"><a href="{escape(return_to)}">Back to Account</a></p>'
    )
    return _page(
        "Add a passkey", product, body, issuer=issuer, redirect_origins=redirect_origins,
        script=True,
    )  # fmt: skip


def second_factor_setup(
    product: str,
    step: str,
    *,
    secret: str,
    svg: str,
    issuer: str,
    redirect_origins: tuple[str, ...],
    wrong: bool = False,
    wait_seconds: int = 0,
    status: int = 200,
) -> HTMLResponse:
    """The set-up step, shown when the instance requires a second factor and the person has none: a
    QR code drawn here (no script), the key to type, and a code to confirm (I4b, D386, D388)."""
    key = " ".join(secret[i : i + 4] for i in range(0, len(secret), 4))
    invalid = ' aria-invalid="true" aria-describedby="code-problem"' if wrong else ""
    body = (
        "<h1>Set up a second factor</h1>"
        '<p class="aside">This instance asks for a code from an authenticator app with every '
        "password. Scan the code with the app, then type the six digits it shows.</p>"
        + _factor_notes(wrong, wait_seconds)
        + f'<div class="qr">{svg}<div class="aside">Cannot scan? Type this key into the app:'
        + f'<code id="key" class="mono">{escape(key)}</code></div></div>'
        + '<form method="post" action="/oauth/second-factor">'
        + _hidden({"step": step})
        + '<div><label for="code">Code from the app</label>'
        + '<input id="code" name="code" class="code" inputmode="numeric" '
        + 'autocomplete="one-time-code" placeholder="000 000" required autofocus'
        + f"{invalid}></div>"
        + '<button type="submit">Confirm and continue</button></form>'
    )
    headers = {"Retry-After": str(wait_seconds)} if wait_seconds else None
    return _page(
        "Set up a second factor", product, body, issuer=issuer,
        redirect_origins=redirect_origins, status=status, headers=headers,
    )  # fmt: skip


def recovery_codes(
    product: str, step: str, codes: list[str], *, issuer: str, redirect_origins: tuple[str, ...]
) -> HTMLResponse:
    """The recovery codes, shown once, before the sign-in goes on (I4b, D385)."""
    listed = "".join(f"<span>{escape(code)}</span>" for code in codes)
    body = (
        "<h1>Keep your recovery codes</h1>"
        '<p class="aside">If you lose your phone, each code signs you in once. They are shown only '
        "now: save them in a password manager or print them.</p>"
        f'<div class="codes mono">{listed}</div>'
        '<form method="post" action="/oauth/second-factor">'
        + _hidden({"step": step, "continue": "1"})
        + '<button type="submit">I have kept them; continue</button></form>'
    )
    return _page("Recovery codes", product, body, issuer=issuer, redirect_origins=redirect_origins)
