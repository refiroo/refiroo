/**
 * Settings › Account (0.12 I2, U8; reworked from the user's mock-up of 2026-10-23): who is signed
 * in, as a profile card; the password, changed in place; where they are signed in, with sign out per
 * browser and everywhere; and what they can do: their roles, where each applies, what it narrows and
 * whether it comes through a group (Z1).
 */

import { useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { signOut } from "@/api/session";
import { initials } from "@/app/useMe";
import { grantHeld } from "@/features/security/securityText";
import { formatServerAgo, formatServerDayTime } from "@/lib/dates";
import type { Grant, Me, SignInSession, WorkspacePage } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { useToast } from "@/ui/Toast";
import { browserName, onPhone } from "./browserName";
import { useSettingsRead } from "./useSystem";

const SIGNED_IN_WITH: Record<string, string> = { password: "Signed in with your password" };
// The production rule (D252); the engine's refusal is what counts where a deployment sets another.
const LONG_ENOUGH = 15;

export function AccountPage() {
  const { data: me, error, retry } = useSettingsRead<Me>(api.me);
  return (
    <SettingsLayout eyebrow="General" title="Account">
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !me ? (
        <Skeleton label="Loading your account" lines={4} />
      ) : (
        <div className="account-page">
          <Profile me={me} />
          {me.signedInWith === "password" && <PasswordPanel />}
          <Sessions />
          <Permissions />
        </div>
      )}
    </SettingsLayout>
  );
}

function Profile({ me }: { me: Me }) {
  return (
    <section className="account-panel account-profile" aria-label="You">
      <span className="account-profile-avatar" aria-hidden="true">
        {initials(me.name)}
      </span>
      <div className="account-profile-text">
        <p className="account-profile-name">{me.name}</p>
        <p className="account-muted">
          {me.username && <span>@{me.username}</span>}
          {me.username && me.email && <span aria-hidden="true"> · </span>}
          {me.email && <span>{me.email}</span>}
        </p>
        <p className="account-pills">
          {me.signedInWith && (
            <span className="account-pill success">
              <span className="account-dot" aria-hidden="true" />
              {SIGNED_IN_WITH[me.signedInWith] ?? `Signed in with ${me.signInProvider?.name ?? me.signedInWith}`}
            </span>
          )}
          {me.lastSignInAt && <span className="account-pill">Since {formatServerDayTime(me.lastSignInAt)}</span>}
        </p>
      </div>
      <button type="button" className="secondary" onClick={() => void signOut()}>
        Sign out
      </button>
    </section>
  );
}

function PasswordInput({
  control,
  name,
  value,
  onChange,
  autoComplete,
}: {
  control: { id: string; "aria-describedby"?: string; "aria-invalid"?: true };
  /** Which password, for the reveal button's name: "current", "new". */
  name: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
}) {
  const [shown, setShown] = useState(false);
  return (
    <span className="account-password-field">
      <input
        {...control}
        type={shown ? "text" : "password"}
        autoComplete={autoComplete}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <button
        type="button"
        className="account-reveal"
        aria-label={`${shown ? "Hide" : "Show"} ${name} password`}
        aria-pressed={shown}
        onClick={() => setShown((value) => !value)}
      >
        <Icon name={shown ? "eye-off" : "eye"} />
      </button>
    </span>
  );
}

function PasswordPanel() {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [currentError, setCurrentError] = useState("");
  const [nextError, setNextError] = useState("");
  const [failure, setFailure] = useState("");
  const [pending, setPending] = useState(false);

  function close() {
    setOpen(false);
    setCurrent("");
    setNext("");
    setCurrentError("");
    setNextError("");
    setFailure("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setCurrentError("");
    setNextError("");
    setFailure("");
    setPending(true);
    try {
      await api.changePassword(current, next);
      close();
      toast("Your password is changed. You are signed out in your other browsers.");
    } catch (cause) {
      if (isApiError(cause) && cause.code === "PASSWORD_INCORRECT") setCurrentError(errorMessage(cause));
      else if (isApiError(cause) && cause.code === "PASSWORD_REJECTED") setNextError(errorMessage(cause));
      else setFailure(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const filled = Math.min(4, Math.ceil((next.length / LONG_ENOUGH) * 4));
  return (
    <Section title="Password">
      <div className="account-panel">
        <div className="account-row">
          <span className="account-tile current" aria-hidden="true">
            <Icon name="lock" size={20} />
          </span>
          <div className="account-row-text">
            <strong>Your password</strong>
            <span className="account-muted">Changing it signs you out of your other browsers.</span>
          </div>
          {!open && (
            <button type="button" className="secondary" onClick={() => setOpen(true)}>
              Change password
            </button>
          )}
        </div>
        {open && (
          <form className="account-row account-password" onSubmit={(event) => void submit(event)}>
            <FormField label="Current password" error={currentError || undefined}>
              {(control) => (
                <PasswordInput
                  control={control}
                  name="current"
                  value={current}
                  onChange={setCurrent}
                  autoComplete="current-password"
                />
              )}
            </FormField>
            <FormField
              label="New password"
              help={
                next.length >= LONG_ENOUGH
                  ? "Long enough. A phrase of several words is easiest to remember."
                  : "A phrase of several words is easiest to remember and hardest to guess."
              }
              error={nextError || undefined}
            >
              {(control) => (
                <>
                  <PasswordInput
                    control={control}
                    name="new"
                    value={next}
                    onChange={setNext}
                    autoComplete="new-password"
                  />
                  <span className="account-meter" aria-hidden="true">
                    {[0, 1, 2, 3].map((step) => (
                      <span key={step} className={step < filled ? "filled" : undefined} />
                    ))}
                  </span>
                </>
              )}
            </FormField>
            {failure && <Notice tone="error">{failure}</Notice>}
            <div className="account-actions">
              <button type="submit" className="primary" disabled={pending}>
                {pending ? "Saving…" : "Save new password"}
              </button>
              <button type="button" className="ghost" onClick={close}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </Section>
  );
}

function Sessions() {
  const { data: sessions, error, retry } = useSettingsRead<SignInSession[]>(api.mySessions);
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState<string>();
  const [failure, setFailure] = useState("");

  async function end(session: SignInSession) {
    setFailure("");
    if (session.current) return signOut();
    setPending(session.id);
    try {
      await api.endMySession(session.id);
      retry();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setPending(undefined);
    }
  }

  async function endAll() {
    setPending("all");
    try {
      await api.endAllMySessions();
      await signOut();
    } catch (cause) {
      setFailure(errorMessage(cause));
      setPending(undefined);
    }
  }

  return (
    <Section
      title="Where you’re signed in"
      actions={
        sessions && (
          <span className="account-muted">
            {sessions.length} browser{sessions.length === 1 ? "" : "s"}
          </span>
        )
      }
    >
      {failure && <Notice tone="error">{failure}</Notice>}
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !sessions ? (
        <Skeleton label="Loading where you are signed in" lines={2} />
      ) : (
        <div className="account-panel">
          <ul className="account-list" aria-label="Where you’re signed in">
            {sessions.map((session) => {
              const name = browserName(session.userAgent);
              return (
                <li key={session.id} className="account-row">
                  <span className={session.current ? "account-tile current" : "account-tile"} aria-hidden="true">
                    <Icon name={onPhone(session.userAgent) ? "phone" : "laptop"} size={20} />
                  </span>
                  <div className="account-row-text">
                    <span className="account-row-title">
                      <strong>{name}</strong>
                      {session.current && (
                        <span className="account-pill success">
                          <span className="account-dot" aria-hidden="true" />
                          This browser
                        </span>
                      )}
                    </span>
                    <span className="account-muted">
                      {session.current ? "Active now" : `Last active ${formatServerAgo(session.lastUsedAt)}`} · signed
                      in {formatServerDayTime(session.createdAt)}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="ghost"
                    disabled={pending !== undefined}
                    aria-label={`Sign out ${name}${session.current ? ", this browser" : ""}`}
                    onClick={() => void end(session)}
                  >
                    Sign out
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="account-row account-footer">
            <span className="account-muted">
              Lost a device, or signed in somewhere you shouldn’t have? Sign out of every browser at once, this one
              included.
            </span>
            <button type="button" className="danger-ghost" onClick={() => setConfirming(true)}>
              Sign out everywhere
            </button>
          </div>
        </div>
      )}
      {confirming && (
        <ConfirmDialog
          title="Sign out everywhere?"
          confirmLabel="Sign out everywhere"
          pending={pending === "all"}
          onCancel={() => setConfirming(false)}
          onConfirm={() => void endAll()}
        >
          Every browser where you are signed in, this one included, is signed out at its next request.
        </ConfirmDialog>
      )}
    </Section>
  );
}

/** The person's roles: per grant, where it applies, the role, what it narrows and where it comes from (Z1). */
function Permissions() {
  const { data, error, retry } = useSettingsRead<[Grant[], WorkspacePage]>(grantsAndWorkspaces);
  const labels = new Map(data?.[1].items.map((workspace) => [workspace.key, workspace.label]));
  const grants = data?.[0];
  return (
    <Section
      title="What you can do"
      actions={
        grants && (
          <span className="account-muted">
            {grants.length} role{grants.length === 1 ? "" : "s"}
          </span>
        )
      }
    >
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !grants ? (
        <Skeleton label="Loading your roles" lines={2} />
      ) : (
        <div className="account-panel">
          {grants.length > 0 && (
            <ul className="account-list" aria-label="What you can do">
              {grants.map((grant) => (
                <li key={grant.id} className="account-row">
                  <span className="account-tile" aria-hidden="true">
                    <Icon name={grant.scope.instance ? "globe" : "workspace"} size={20} />
                  </span>
                  <div className="account-row-text">
                    <strong>
                      {grant.scope.instance
                        ? "Every workspace"
                        : (labels.get(grant.scope.workspaceKey ?? "") ?? grant.scope.workspaceKey)}
                    </strong>
                    <span className="account-muted">{grantDetail(grant)}</span>
                  </div>
                  <span className="account-pill role">{grantHeld(grant)}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="account-row account-footer">
            <span className="account-muted">
              {grants.length === 0
                ? "You have no roles yet. Ask a security administrator to give you one."
                : "A security administrator gives and removes roles. Reading a workspace is never narrowed; a narrowing limits what you may change."}
            </span>
          </div>
        </div>
      )}
    </Section>
  );
}

const grantsAndWorkspaces = () => Promise.all([api.myGrants(), api.workspaces()]);

/** "Changes narrowed to Specimen, Determination · directly", "Through the group Curators". */
export function grantDetail(grant: Grant): string {
  const narrowed = [...grant.scope.applicationNames, ...grant.scope.recordTypeNames];
  const where = grant.scope.instance
    ? "The whole instance"
    : narrowed.length
      ? `Changes narrowed to ${narrowed.join(", ")}`
      : "";
  const how = grant.principal.kind === "group" ? `through the group ${grant.principal.name}` : "directly";
  return where ? `${where} · ${how}` : how[0].toUpperCase() + how.slice(1);
}
