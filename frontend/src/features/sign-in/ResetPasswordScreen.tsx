/**
 * The pages that give a person back their password (0.12 I6, D420, D422), at `/reset-password`:
 * without a token they ask for a link by e-mail address (and are told the same whoever
 * they name); with the token of a link that was mailed or made for them they choose a new password.
 * The engine decides everything (`/oauth/sign-in/reset*`); these pages draw what it answers inside
 * the sign-in screen's frame. They work without a session: the person has none.
 */

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { requestReset, resetPage, setPasswordWithLink, type ResetPage, type ResetRefused } from "@/api/signInClient";
import { API_URL } from "@/api/address";
import { FormField } from "@/ui/FormField";
import { Notice } from "@/ui/Notice";
import { SignInFrame } from "./SignInFrame";

const BACK = <a href="/">Back to sign in</a>;

/** The words for a refusal: the engine's own, as the sign-in screen shows them, so a wording is never kept twice. */
function refusalText(refused: ResetRefused): string {
  return refused.message;
}

/**
 * The token of the link this page was opened with, taken out of the address: read from `?token=`,
 * then the address is replaced by the bare path so the token is in neither the address bar nor the
 * history. It is kept in this entry's history state, so a reload of the page (before the password
 * is set) still finds it; a page opened without one is the "ask for a link" page.
 */
export function takeResetToken(): string {
  const fromAddress = new URLSearchParams(window.location.search).get("token");
  if (fromAddress !== null) {
    window.history.replaceState(
      { ...(window.history.state ?? {}), resetToken: fromAddress },
      "",
      window.location.pathname,
    );
    return fromAddress;
  }
  const kept = (window.history.state as { resetToken?: unknown } | null)?.resetToken;
  return typeof kept === "string" ? kept : "";
}

/** The link is spent or refused: this entry no longer keeps its token, so the page is the ask page again. */
function forgetResetToken() {
  window.history.replaceState(null, "");
}

export function ResetPasswordScreen({ token }: { token: string }) {
  const [page, setPage] = useState<ResetPage>();
  const [loadError, setLoadError] = useState("");
  useEffect(() => {
    let current = true;
    resetPage(token)
      .then((answer) => {
        if (!current) return;
        if (!answer.ok && answer.error === "link_gone") forgetResetToken();
        setPage(answer);
      })
      .catch(() => current && setLoadError(`The engine at ${API_URL} did not answer. Check that it is running.`));
    return () => {
      current = false;
    };
  }, [token]);

  const product = page && "product" in page ? page.product : "refiroo";
  const gone = page && !page.ok && page.error === "link_gone";
  const title = token ? (gone ? "This link no longer works" : "Choose a new password") : "Forgotten your password?";
  return (
    <SignInFrame product={product} named={!!page || !!loadError} busy={!page && !loadError} title={title}>
      {loadError ? (
        <Notice tone="error" title="This is not possible right now">
          {loadError}
        </Notice>
      ) : !page ? (
        <p className="sign-in-aside">Loading…</p>
      ) : !page.ok ? (
        <>
          <Notice tone="error">{refusalText(page)}</Notice>
          {gone ? <a href="/reset-password">Ask for a new link</a> : null}
          {BACK}
        </>
      ) : "email" in page ? (
        <NewPassword token={token} email={page.email} minLength={page.minLength} />
      ) : page.available ? (
        <Ask />
      ) : (
        <>
          <Notice tone="info">
            A new password cannot be asked for by e-mail here. Ask a security administrator for a reset link.
          </Notice>
          {BACK}
        </>
      )}
    </SignInFrame>
  );
}

function Ask() {
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<{ text: string; slowed: boolean }>();
  const [asked, setAsked] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setNotice(undefined);
    try {
      const answer = await requestReset(email.trim());
      if (answer.ok) setAsked(answer.message);
      else setNotice({ text: refusalText(answer), slowed: answer.error === "slowed" });
    } catch {
      setNotice({ text: `The engine at ${API_URL} did not answer. Try again.`, slowed: false });
    } finally {
      setPending(false);
    }
  }

  if (asked)
    return (
      <>
        <Notice tone="info">{asked}</Notice>
        <p className="sign-in-aside">
          The link works once and for a limited time. Nothing arrived after a few minutes? Check the spam folder, or ask
          a security administrator.
        </p>
        {BACK}
      </>
    );
  return (
    <>
      <p className="sign-in-aside">Type your e-mail address and we will mail you a link to choose a new one.</p>
      {notice && <Notice tone={notice.slowed ? "warning" : "error"}>{notice.text}</Notice>}
      <form className="sign-in-form" noValidate onSubmit={(event) => void submit(event)}>
        <FormField label="E-mail address">
          {(control) => (
            <input
              {...control}
              autoFocus
              required
              type="email"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          )}
        </FormField>
        <button type="submit" className="primary" disabled={pending || !email.trim()}>
          {pending ? "Sending…" : "Mail me a link"}
        </button>
      </form>
      {BACK}
    </>
  );
}

function NewPassword({ token, email, minLength }: { token: string; email: string; minLength: number }) {
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [done, setDone] = useState(false);
  const [gone, setGone] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setMessage("");
    try {
      const answer = await setPasswordWithLink(token, password, repeat);
      if (answer.ok) {
        forgetResetToken();
        setDone(true);
      } else if (answer.error === "link_gone") {
        forgetResetToken();
        setGone(true);
      } else setMessage(refusalText(answer));
    } catch {
      setMessage(`The engine at ${API_URL} did not answer. Try again.`);
    } finally {
      setPending(false);
    }
  }

  if (done)
    return (
      <>
        <Notice tone="success">Your password is set. You were signed out everywhere.</Notice>
        <a href="/">Sign in</a>
      </>
    );
  if (gone)
    return (
      <>
        <Notice tone="error">This link has been used, replaced by a newer one, or has expired.</Notice>
        <a href="/reset-password">Ask for a new link</a>
        {BACK}
      </>
    );
  return (
    <>
      <p className="sign-in-aside">
        A new password for <strong>{email}</strong>. At least {minLength} characters, and not your e-mail address or a
        very common password.
      </p>
      {message && <Notice tone="error">{message}</Notice>}
      <form className="sign-in-form" noValidate onSubmit={(event) => void submit(event)}>
        <FormField label="New password">
          {(control) => (
            <input
              {...control}
              autoFocus
              required
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          )}
        </FormField>
        <FormField label="Type it again">
          {(control) => (
            <input
              {...control}
              required
              type="password"
              autoComplete="new-password"
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
            />
          )}
        </FormField>
        <button type="submit" className="primary" disabled={pending || !password || !repeat}>
          {pending ? "Saving…" : "Set password"}
        </button>
      </form>
    </>
  );
}
