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
import { counted } from "@/lib/count";
import { objectTypeFor } from "@/model/lookup";
import type { Navigate } from "@/state/openWorkspace";
import { formatServerAgo, formatServerDayTime } from "@/lib/dates";
import { applicationHue } from "@/model/hues";
import type { EngineModel, Grant, Me, SignInSession, Workspace } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { NameMark, SettingRow, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { permissionsSummary, PermissionsBody, type AppInfo, type AppsByName } from "./AccountPermissions";
import { browserName, onPhone } from "./browserName";
import { settingsHead } from "@/ui/settingsNavigation";
import { PasskeysPanel } from "./PasskeysPanel";
import { SecondFactorPanel } from "./SecondFactorPanel";
import { useSettingsRead } from "@/state/useSystem";
import { allWorkspaces } from "@/api/allWorkspaces";
import { SIGN_OUT_EVERYWHERE } from "@/lib/words";

const SIGNED_IN_WITH: Record<string, string> = {
  password: "Signed in with your password",
  passkey: "Signed in with a passkey",
};
// The production rule (D252); the engine's refusal is what counts where a deployment sets another.
const LONG_ENOUGH = 15;

export function AccountPage({ onNavigate }: { onNavigate?: Navigate }) {
  const { data: me, error, retry } = useSettingsRead<Me>(api.me);
  return (
    <SettingsLayout
      {...settingsHead("account")}
      title="Account"
      description="Who you are signed in as, how you sign in, and what your roles let you do."
    >
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !me ? (
        <Skeleton label="Loading your account" lines={4} />
      ) : (
        <>
          <Profile me={me} />
          {me.signInManaged ? (
            <ManagedSignIn />
          ) : (
            <>
              {me.signedInWith === "password" && <PasswordPanel />}
              {(me.signedInWith === "password" || me.signedInWith === "passkey") && <PasskeysPanel />}
              {(me.signedInWith === "password" || me.signedInWith === "passkey") && <SecondFactorPanel />}
              <Sessions />
            </>
          )}
          <Permissions onNavigate={onNavigate} />
        </>
      )}
    </SettingsLayout>
  );
}

function Profile({ me }: { me: Me }) {
  return (
    <SettingsGroup title="You" description="Who this browser is signed in as.">
      <SettingsPanel>
        <SettingRow lead={<NameMark name={me.name} size={64} />} name={me.name} help={me.email}>
          <button type="button" className="secondary" onClick={() => void signOut()}>
            Sign out
          </button>
        </SettingRow>
        {(me.signedInWith || me.lastSignInAt) && (
          <SettingRow fact name="Signed in">
            <span className="account-signed-in">
              {me.signedInWith && (
                <StatusPill tone="success">
                  {SIGNED_IN_WITH[me.signedInWith] ?? `Signed in with ${me.signInProvider?.name ?? me.signedInWith}`}
                </StatusPill>
              )}
              {me.lastSignInAt && <StatusPill tone="neutral">Since {formatServerDayTime(me.lastSignInAt)}</StatusPill>}
            </span>
          </SettingRow>
        )}
      </SettingsPanel>
    </SettingsGroup>
  );
}

/** Stands where the password, passkeys, second factor and other sessions would be: an administrator
 * keeps them (0.17 SA1). Hidden, not disabled (Z5, D323). */
function ManagedSignIn() {
  return (
    <SettingsGroup title="Sign-in" description="How you sign in to this account.">
      <SettingsPanel>
        <SettingRow
          lead={<SettingsTile icon="lock" hue={settingsHead("account").hue} />}
          name="An administrator manages the sign-in of this account."
        />
      </SettingsPanel>
    </SettingsGroup>
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
    <SettingsGroup title="Password" description="Sign in with a password only you know.">
      {open ? (
        <form onSubmit={(event) => void submit(event)}>
          <SettingsPanel
            foot={
              <>
                <button type="button" className="ghost" onClick={close}>
                  Cancel
                </button>
                <button type="submit" className="primary" disabled={pending}>
                  {pending ? "Saving…" : "Save"}
                </button>
              </>
            }
          >
            <div className="settings-fields">
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
            </div>
          </SettingsPanel>
        </form>
      ) : (
        <SettingsPanel>
          <SettingRow
            lead={<SettingsTile icon="lock" hue={settingsHead("account").hue} />}
            name="Your password"
            help="Changing it signs you out of your other browsers."
          >
            <button type="button" className="secondary" onClick={() => setOpen(true)}>
              Change password
            </button>
          </SettingRow>
        </SettingsPanel>
      )}
    </SettingsGroup>
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
    <SettingsGroup
      title="Where you’re signed in"
      description={
        <>
          <p>Every browser, and every assistant, signed in as you.</p>
          {sessions && <p>{counted(sessions.length, "browser")}</p>}
        </>
      }
    >
      {failure && <Notice tone="error">{failure}</Notice>}
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !sessions ? (
        <Skeleton label="Loading where you are signed in" lines={2} />
      ) : (
        <>
          <SettingsPanel>
            <ul className="account-list" aria-label="Where you’re signed in">
              {sessions.map((session) => {
                const name = session.application
                  ? `${session.application} (assistant)`
                  : browserName(session.userAgent);
                return (
                  <li key={session.id}>
                    <SettingRow
                      lead={
                        <SettingsTile
                          icon={onPhone(session.userAgent) ? "phone" : "laptop"}
                          hue={settingsHead("account").hue}
                        />
                      }
                      name={
                        <span className="account-row-title">
                          <strong>{name}</strong>
                          {session.current && <StatusPill tone="success">This browser</StatusPill>}
                        </span>
                      }
                      help={`${session.current ? "Active now" : `Last active ${formatServerAgo(session.lastUsedAt)}`} · signed in ${formatServerDayTime(session.createdAt)}`}
                    >
                      <button
                        type="button"
                        className="ghost"
                        disabled={pending !== undefined}
                        aria-label={`Sign out ${name}${session.current ? ", this browser" : ""}`}
                        onClick={() => void end(session)}
                      >
                        Sign out
                      </button>
                    </SettingRow>
                  </li>
                );
              })}
            </ul>
          </SettingsPanel>
          <SettingsPanel>
            <SettingRow
              name={SIGN_OUT_EVERYWHERE}
              help="Lost a device, or signed in somewhere you shouldn’t have? Sign out of every browser at once, this one included."
            >
              <button type="button" className="danger-ghost" onClick={() => setConfirming(true)}>
                {SIGN_OUT_EVERYWHERE}
              </button>
            </SettingRow>
          </SettingsPanel>
        </>
      )}
      {confirming && (
        <ConfirmDialog
          title={`${SIGN_OUT_EVERYWHERE}?`}
          confirmLabel={SIGN_OUT_EVERYWHERE}
          pending={pending === "all"}
          onCancel={() => setConfirming(false)}
          onConfirm={() => void endAll()}
        >
          Every browser where you are signed in, this one included, is signed out at its next request.
        </ConfirmDialog>
      )}
    </SettingsGroup>
  );
}

/** The action groups each grant gives, read from the person's permissions in every workspace (Z1). */
async function grantsAndGroups(): Promise<
  [Grant[], Workspace[], ReadonlyMap<string, ReadonlySet<string>>, ReadonlyMap<string, AppsByName>]
> {
  const [grants, workspaces] = await Promise.all([api.myGrants(), allWorkspaces()]);
  const [read, models] = await Promise.all([
    Promise.all(workspaces.map((workspace) => api.myPermissions(workspace.key).catch(() => null))),
    Promise.all(workspaces.map((workspace) => api.model({ workspaceKey: workspace.key }).catch(() => null))),
  ]);
  const groups = new Map<string, Set<string>>();
  for (const permissions of read)
    for (const group of permissions?.actionGroups ?? [])
      for (const source of group.sources) {
        const held = groups.get(source.grantId) ?? new Set<string>();
        groups.set(source.grantId, held.add(group.key));
      }
  // Each application's hue is the one the rest of the app gives it: its place in its workspace's model.
  const hues = new Map<string, AppsByName>();
  workspaces.forEach((workspace, index) => hues.set(workspace.key, applicationHues(models[index])));
  return [grants, workspaces, groups, hues];
}

/** Application name to its hue, address and record types, for a grant that names applications. */
function applicationHues(model: EngineModel | null): AppsByName {
  const found = new Map<string, AppInfo>();
  for (const application of model?.applications ?? [])
    found.set(application.name, {
      key: application.key,
      defaultView: application.defaultView,
      hue: applicationHue(model!, application.key),
      recordTypes: application.objectTypeKeys.flatMap((key) => objectTypeFor(model!, key)?.name ?? []),
    });
  return found;
}

/** The person's roles: a row per workspace with what each allows, the instance's roles below (Z1). */
function Permissions({ onNavigate }: { onNavigate?: Navigate }) {
  const { data, error, retry } = useSettingsRead<Awaited<ReturnType<typeof grantsAndGroups>>>(grantsAndGroups);
  const grants = data?.[0];
  const labels = new Map(data?.[1].map((workspace) => [workspace.key, workspace.label]));
  return (
    <SettingsGroup
      stacked
      title="What you can do"
      description={
        <>
          <p>Your roles, where each applies and what it covers.</p>
          {grants && grants.length > 0 && <p>{permissionsSummary(grants, labels, data![2])}</p>}
        </>
      }
    >
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !grants ? (
        <Skeleton label="Loading your roles" lines={2} />
      ) : (
        <PermissionsBody grants={grants} labels={labels} groups={data![2]} apps={data![3]} onNavigate={onNavigate} />
      )}
    </SettingsGroup>
  );
}
