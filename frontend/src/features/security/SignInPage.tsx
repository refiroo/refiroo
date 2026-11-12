/**
 * Settings › Security › Sign-in (0.12 I3, U8; 0.17 ST1): how people prove who they are. A list with local
 * accounts first, on or off (D365), then the OpenID Connect providers; a row opens its own page (PP-D61).
 * A provider's page gives the address to register with it, edits its settings in place
 * (the secret is never shown, only replaced; an enabled provider is read when saved, D366), and
 * enables, disables or deletes it (delete only while nobody has signed in with it). Local sign-in
 * is turned off only once a provider has signed someone in, keeping the administrators made on the
 * server.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { security } from "@/api/securityClient";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { LocalSignIn, RouteState, SettingsRoute, SignInProvider, SignInProviderCreate } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { CopyValue } from "@/ui/CopyValue";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { EntityList } from "@/ui/EntityList";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { ItemHeader, SettingRow, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Switch } from "@/ui/Switch";
import { useToast } from "@/ui/Toast";
import { Trail } from "@/ui/Trail";
import { settingsHead } from "@/features/settings/navigation";
import { routePath } from "@/routing/routes";
import { localSignInLine, providerUseLine, turnOffSentence } from "./securityText";

type SignInRoute = Extract<SettingsRoute, { page: "sign-in" }>;

const SIGN_IN: SignInRoute = { kind: "settings", page: "sign-in" };
const LOCAL = "local";

export function SignInPage({ route, onNavigate }: { route: SignInRoute; onNavigate: (route: RouteState) => void }) {
  const feed = useCursorFeed((cursor) => security.signInProviders(cursor), []);
  const [local, setLocal] = useState<LocalSignIn>();
  const [localError, setLocalError] = useState("");
  const [creating, setCreating] = useState(false);
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const head = settingsHead("sign-in");

  function loadLocal() {
    security.localSignIn().then(
      (state) => {
        setLocal(state);
        setLocalError("");
      },
      (cause) => setLocalError(errorMessage(cause)),
    );
  }
  useEffect(loadLocal, []);

  function changed(provider: SignInProvider) {
    feed.setItems((items) => items.map((item) => (item.key === provider.key ? provider : item)));
  }

  const trail = <Trail back={{ label: "Sign-in", onClick: () => onNavigate(SIGN_IN), href: routePath(SIGN_IN) }} />;
  const listed = !route.providerKey;
  return (
    <>
      {route.providerKey === LOCAL ? (
        local ? (
          <LocalDetail local={local} providers={feed.items} trail={trail} onChanged={setLocal} />
        ) : (
          <SettingsLayout trail={trail} title="Local accounts">
            {localError ? (
              <InlineError message={localError} onRetry={loadLocal} />
            ) : (
              <Skeleton label="Loading local accounts" lines={3} />
            )}
          </SettingsLayout>
        )
      ) : route.providerKey ? (
        <ProviderDetail
          key={route.providerKey}
          providerKey={route.providerKey}
          trail={trail}
          onChanged={changed}
          onDeleted={() => {
            feed.reload();
            onNavigate(SIGN_IN);
          }}
        />
      ) : null}
      {listed && (
        <SettingsLayout
          {...head}
          title="Sign-in"
          description="How people prove who they are: an e-mail address and password, or the organisation's sign-in provider (OpenID Connect) with its own multi-factor sign-in. The engine starts its own session either way."
          actions={
            <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
              <Icon name="plus" /> New provider
            </button>
          }
        >
          <SettingsPanel>
            <EntityList
              label="sign-in methods"
              statusTrack="6rem"
              groups={[
                {
                  key: "local",
                  title: "Local accounts",
                  count: local ? 1 : "…",
                  loading: !local && !localError,
                  error: localError || undefined,
                  onRetry: loadLocal,
                  rows: local
                    ? [
                        {
                          key: LOCAL,
                          title: "Local accounts",
                          subtitle: localSignInLine(local),
                          lead: <SettingsTile icon="lock" hue={head.hue} />,
                          pill: (
                            <StatusPill tone={local.enabled ? "success" : "neutral"}>
                              {local.enabled ? "On" : "Off"}
                            </StatusPill>
                          ),
                          onOpen: () => onNavigate({ ...SIGN_IN, providerKey: LOCAL }),
                        },
                      ]
                    : [],
                },
                {
                  key: "providers",
                  title: "Providers",
                  count: `${feed.items.length}${feed.hasMore ? "+" : ""}`,
                  loading: feed.loading && !feed.items.length,
                  error: feed.error && !feed.items.length ? feed.error : undefined,
                  onRetry: feed.retry,
                  onEnd: feed.hasMore ? feed.loadMore : undefined,
                  loadingMore: feed.loading && feed.items.length > 0,
                  rows: feed.items.map((provider) => ({
                    key: provider.key,
                    title: provider.name,
                    subtitle: providerUseLine(provider),
                    lead: <SettingsTile icon="globe" hue={head.hue} />,
                    pill: (
                      <StatusPill tone={provider.enabled ? "success" : "neutral"}>
                        {provider.enabled ? "Enabled" : "Disabled"}
                      </StatusPill>
                    ),
                    onOpen: () => onNavigate({ ...SIGN_IN, providerKey: provider.key }),
                  })),
                },
              ]}
              empty=""
            />
            {!feed.loading && !feed.error && !feed.items.length && (
              <p className="settings-panel-note">No provider yet: people sign in with a password.</p>
            )}
          </SettingsPanel>
        </SettingsLayout>
      )}
      {creating && (
        <NewProviderDialog
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(provider) => {
            setCreating(false);
            feed.reload();
            onNavigate({ ...SIGN_IN, providerKey: provider.key });
          }}
        />
      )}
    </>
  );
}

/** A key from a name: lower case, words joined by hyphens, as the API accepts it. */
export function providerKeyFrom(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^[^a-z]+/, "")
    .replace(/-+$/, "")
    .slice(0, 63);
}

function NewProviderDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (provider: SignInProvider) => void;
}) {
  const [values, setValues] = useState<SignInProviderCreate>({
    key: "",
    name: "",
    issuer: "",
    clientId: "",
    clientSecret: "",
    groupsClaim: "",
    enabled: true,
  });
  const [keyEdited, setKeyEdited] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const set = (field: keyof SignInProviderCreate, value: string | boolean) =>
    setValues((current) => ({ ...current, [field]: value }));
  const ready =
    values.key && values.name.trim() && values.issuer.trim() && values.clientId.trim() && values.clientSecret;

  async function create() {
    setPending(true);
    setError("");
    try {
      onCreated(
        await security.createSignInProvider({
          ...values,
          name: values.name.trim(),
          issuer: values.issuer.trim(),
          clientId: values.clientId.trim(),
          groupsClaim: values.groupsClaim?.trim() || null,
        }),
      );
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal
      title="New sign-in provider"
      eyebrow="People and access"
      busy={pending}
      dirty={!!(values.name || values.issuer || values.clientId || values.clientSecret)}
      onClose={onClose}
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <div className="dialog-pair">
          <FormField label="Name on the sign-in button" help="The button reads “Continue with” and this name.">
            {(control) => (
              <input
                {...control}
                autoFocus
                required
                maxLength={200}
                value={values.name}
                onChange={(event) => {
                  set("name", event.target.value);
                  if (!keyEdited) set("key", providerKeyFrom(event.target.value));
                }}
              />
            )}
          </FormField>
          <FormField label="Key" help="In the address you register with the provider; it cannot change once saved.">
            {(control) => (
              <input
                {...control}
                className="mono"
                required
                maxLength={63}
                value={values.key}
                onChange={(event) => {
                  setKeyEdited(true);
                  set("key", event.target.value);
                }}
              />
            )}
          </FormField>
        </div>
        <FormField
          label="Issuer"
          help="Exactly as the provider states it, for example https://login.microsoftonline.com/<tenant>/v2.0."
        >
          {(control) => (
            <input
              {...control}
              className="mono"
              required
              value={values.issuer}
              onChange={(event) => set("issuer", event.target.value)}
            />
          )}
        </FormField>
        <div className="dialog-pair">
          <FormField label="Client ID">
            {(control) => (
              <input
                {...control}
                className="mono"
                required
                value={values.clientId}
                onChange={(event) => set("clientId", event.target.value)}
              />
            )}
          </FormField>
          <FormField label="Client secret" help="Kept sealed; it is never shown again.">
            {(control) => (
              <input
                {...control}
                type="password"
                autoComplete="off"
                required
                value={values.clientSecret}
                onChange={(event) => set("clientSecret", event.target.value)}
              />
            )}
          </FormField>
        </div>
        <FormField
          label="Groups claim (optional)"
          help="The ID token claim with the person's groups, often “groups”. Empty: groups are not used."
        >
          {(control) => (
            <input
              {...control}
              className="mono"
              maxLength={200}
              value={values.groupsClaim ?? ""}
              onChange={(event) => set("groupsClaim", event.target.value)}
            />
          )}
        </FormField>
        <label className="checkbox">
          <input type="checkbox" checked={values.enabled} onChange={(event) => set("enabled", event.target.checked)} />
          Offer it on the sign-in page now
        </label>
        <p className="admin-hint">
          An enabled provider is checked when saved. The address to register with it is on its page.
        </p>
        {error && (
          <Notice tone="error" title="The provider was not saved">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !ready}>
            {pending ? "Checking and adding…" : "Add provider"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ProviderDetail({
  providerKey,
  trail,
  onChanged,
  onDeleted,
}: {
  providerKey: string;
  trail: ReactNode;
  onChanged: (provider: SignInProvider) => void;
  onDeleted: () => void;
}) {
  const [provider, setProvider] = useState<SignInProvider>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const deleteRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  useEffect(() => {
    let current = true;
    security.signInProvider(providerKey).then(
      (loaded) => {
        if (!current) return;
        setProvider(loaded);
        setLoadError("");
      },
      (cause) => current && setLoadError(errorMessage(cause)),
    );
    return () => {
      current = false;
    };
  }, [providerKey, loadToken]);

  async function write(action: () => Promise<void>): Promise<boolean> {
    setPending(true);
    setActionError("");
    try {
      await action();
      return true;
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        setLoadToken((token) => token + 1);
        setActionError("This provider changed while the page was open. It is shown as it is now; try again.");
      } else {
        setActionError(errorMessage(cause));
      }
      return false;
    } finally {
      setPending(false);
    }
  }

  function stored(updated: SignInProvider, text: string) {
    setProvider(updated);
    onChanged(updated);
    toast(text);
  }

  const head = settingsHead("sign-in");
  if (loadError)
    return (
      <SettingsLayout trail={trail} title="Sign-in provider">
        <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />
      </SettingsLayout>
    );
  if (!provider)
    return (
      <SettingsLayout trail={trail} title="Sign-in provider">
        <Skeleton label="Loading provider" lines={4} />
      </SettingsLayout>
    );

  return (
    <SettingsLayout
      trail={trail}
      header={
        <ItemHeader
          hue={head.hue}
          lead={<SettingsTile icon="globe" hue={head.hue} size={48} />}
          title={<h1>{provider.name}</h1>}
          meta={
            <>
              <StatusPill tone={provider.enabled ? "success" : "neutral"}>
                {provider.enabled ? "Enabled" : "Disabled"}
              </StatusPill>
              <StatusPill tone="neutral" marker={false}>
                {provider.people === 1 ? "1 person has" : `${provider.people} people have`} signed in with it
              </StatusPill>
              {provider.lastSignInAt && (
                <StatusPill tone="neutral" marker={false}>
                  Last sign-in {formatServerDayTime(provider.lastSignInAt)}
                </StatusPill>
              )}
            </>
          }
          actions={
            <>
              <button
                className="secondary"
                disabled={pending}
                onClick={() =>
                  void write(async () =>
                    stored(
                      await security.updateSignInProvider(provider.key, {
                        expectedVersion: provider.version,
                        enabled: !provider.enabled,
                      }),
                      provider.enabled
                        ? `${provider.name} is no longer offered; the sessions it started have ended.`
                        : `${provider.name} is offered on the sign-in page.`,
                    ),
                  )
                }
              >
                {provider.enabled ? "Disable" : "Enable"}
              </button>
              {provider.people === 0 && (
                <button ref={deleteRef} className="danger-ghost" disabled={pending} onClick={() => setDeleting(true)}>
                  Delete
                </button>
              )}
            </>
          }
        />
      }
    >
      {actionError && (
        <Notice tone="error" title="Not saved" focusOnMount>
          {actionError}
        </Notice>
      )}
      <SettingsGroup
        title="Address to register with the provider"
        description="Add it as the redirect address of the application you registered for the engine at the provider."
      >
        <SettingsPanel>
          <SettingRow under name="Redirect address">
            <CopyValue label="Redirect address" value={provider.redirectUri} />
          </SettingRow>
        </SettingsPanel>
      </SettingsGroup>
      <ProviderSignOut
        key={`sign-out-${provider.version}`}
        provider={provider}
        pending={pending}
        onSave={(body) =>
          write(async () =>
            stored(
              await security.updateSignInProvider(provider.key, body),
              body.signOutOfProvider ? `People who sign in with ${provider.name} are signed out of it too.` : "Saved.",
            ),
          )
        }
      />
      <ProviderSettings
        key={provider.version}
        provider={provider}
        pending={pending}
        onSave={(body) => write(async () => stored(await security.updateSignInProvider(provider.key, body), "Saved."))}
      />
      {deleting && (
        <ConfirmDialog
          title={`Delete ${provider.name}?`}
          confirmLabel="Delete provider"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setDeleting(false);
            setActionError("");
            deleteRef.current?.focus();
          }}
          onConfirm={() =>
            void write(async () => {
              await security.deleteSignInProvider(provider.key);
              setDeleting(false);
              toast(`${provider.name} was deleted.`);
              onDeleted();
            })
          }
        >
          <p>
            Nobody has signed in with it. Its button leaves the sign-in page, and the groups made ahead for it are
            deleted with their roles.
          </p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}

/** Whether signing out of the engine signs the person out of the provider too (I4a, D379). */
function ProviderSignOut({
  provider,
  pending,
  onSave,
}: {
  provider: SignInProvider;
  pending: boolean;
  onSave: (body: { expectedVersion: number; signOutOfProvider: boolean }) => Promise<boolean>;
}) {
  const [on, setOn] = useState(provider.signOutOfProvider);
  const dirty = on !== provider.signOutOfProvider;
  return (
    <SettingsGroup title="Signing out" description="Whether signing out of the engine reaches the provider too.">
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void onSave({ expectedVersion: provider.version, signOutOfProvider: on });
        }}
      >
        <SettingsPanel
          foot={
            <>
              <span className="settings-panel-state">{dirty ? "Changed, not saved" : ""}</span>
              <button
                type="button"
                className="ghost"
                disabled={pending || !dirty}
                onClick={() => setOn(provider.signOutOfProvider)}
              >
                Cancel
              </button>
              <button className="primary" disabled={pending || !dirty}>
                {pending ? "Saving…" : "Save"}
              </button>
            </>
          }
        >
          <SettingRow
            keep
            name={`Sign people out of ${provider.name} too`}
            help={`Signing out of the engine also signs the person out of ${provider.name}, and so of every application of the organisation that uses it in this browser: useful on shared computers. Off: they stay signed in to ${provider.name} and come back without typing a password.`}
          >
            <Switch label={`Sign people out of ${provider.name} too`} checked={on} onChange={setOn} />
          </SettingRow>
          {on && (
            <SettingRow under name="Sign-out address to register (post-logout redirect)">
              <CopyValue label="Sign-out address" value={provider.signedOutUri} />
            </SettingRow>
          )}
          <div className="settings-panel-pad">
            <Notice tone="warning" title="Only this browser">
              Sign out everywhere, and an administrator signing a person out, end the engine's sessions only: another
              browser cannot be sent to {provider.name}.
            </Notice>
          </div>
        </SettingsPanel>
      </form>
    </SettingsGroup>
  );
}

/** A provider's settings edited in place; a new secret replaces the saved one. */
function ProviderSettings({
  provider,
  pending,
  onSave,
}: {
  provider: SignInProvider;
  pending: boolean;
  onSave: (body: { expectedVersion: number } & Partial<SignInProviderCreate>) => Promise<boolean>;
}) {
  const [name, setName] = useState(provider.name);
  const [issuer, setIssuer] = useState(provider.issuer);
  const [clientId, setClientId] = useState(provider.clientId);
  const [secret, setSecret] = useState("");
  const [claim, setClaim] = useState(provider.groupsClaim ?? "");
  const dirty =
    name !== provider.name ||
    issuer !== provider.issuer ||
    clientId !== provider.clientId ||
    !!secret ||
    claim !== (provider.groupsClaim ?? "");

  function reset() {
    setName(provider.name);
    setIssuer(provider.issuer);
    setClientId(provider.clientId);
    setSecret("");
    setClaim(provider.groupsClaim ?? "");
  }

  return (
    <SettingsGroup title="Settings" description="What the engine uses to sign people in with this provider.">
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void onSave({
            expectedVersion: provider.version,
            ...(name.trim() !== provider.name && { name: name.trim() }),
            ...(issuer.trim() !== provider.issuer && { issuer: issuer.trim() }),
            ...(clientId.trim() !== provider.clientId && { clientId: clientId.trim() }),
            ...(secret && { clientSecret: secret }),
            ...(claim.trim() !== (provider.groupsClaim ?? "") && { groupsClaim: claim.trim() || null }),
          });
        }}
      >
        <SettingsPanel
          foot={
            <>
              <span className="settings-panel-state">{dirty ? "Changed, not saved" : ""}</span>
              <button type="button" className="ghost" disabled={pending || !dirty} onClick={reset}>
                Cancel
              </button>
              <button className="primary" disabled={pending || !dirty}>
                {pending ? "Saving…" : "Save"}
              </button>
            </>
          }
        >
          <div className="settings-fields">
            <FormField label="Name on the sign-in button" help={`The button reads “Continue with ${name || "…"}”.`}>
              {(control) => (
                <input {...control} required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
              )}
            </FormField>
            <FormField label="Key" help="In the address above; fixed once saved.">
              {(control) => <input {...control} className="mono" value={provider.key} readOnly />}
            </FormField>
            <div className="full">
              <FormField label="Issuer">
                {(control) => (
                  <input
                    {...control}
                    className="mono"
                    required
                    value={issuer}
                    onChange={(e) => setIssuer(e.target.value)}
                  />
                )}
              </FormField>
            </div>
            <FormField label="Client ID">
              {(control) => (
                <input
                  {...control}
                  className="mono"
                  required
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                />
              )}
            </FormField>
            <FormField label="Client secret">
              {(control) => (
                <input
                  {...control}
                  type="password"
                  autoComplete="off"
                  placeholder={provider.clientSecretSet ? "Saved · type a new one to replace it" : ""}
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                />
              )}
            </FormField>
            <div className="full">
              <FormField label="Groups claim" help="Empty: the provider's groups are not used.">
                {(control) => (
                  <input
                    {...control}
                    className="mono"
                    maxLength={200}
                    value={claim}
                    onChange={(e) => setClaim(e.target.value)}
                  />
                )}
              </FormField>
            </div>
          </div>
        </SettingsPanel>
      </form>
    </SettingsGroup>
  );
}

function LocalDetail({
  local,
  providers,
  trail,
  onChanged,
}: {
  local: LocalSignIn;
  providers: readonly SignInProvider[];
  trail: ReactNode;
  onChanged: (local: LocalSignIn) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [requiring, setRequiring] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const offRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();
  const working = providers.filter((provider) => provider.enabled && provider.lastSignInAt);
  const offered = providers.filter((provider) => provider.enabled).map((provider) => provider.name);

  async function turn(enabled: boolean) {
    setPending(true);
    setError("");
    try {
      onChanged(await security.setLocalSignIn({ expectedVersion: local.version, enabled }));
      setConfirming(false);
      toast(enabled ? "People sign in with a password again." : "Local sign-in is off.");
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT")) void security.localSignIn().then(onChanged, () => undefined);
    } finally {
      setPending(false);
    }
  }

  async function require(required: boolean) {
    setPending(true);
    setError("");
    try {
      onChanged(await security.setLocalSignIn({ expectedVersion: local.version, secondFactorRequired: required }));
      setRequiring(false);
      toast(
        required
          ? "A password now needs a code from an authenticator app."
          : "A second factor is no longer required with a password.",
      );
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT")) void security.localSignIn().then(onChanged, () => undefined);
    } finally {
      setPending(false);
    }
  }

  const head = settingsHead("sign-in");
  return (
    <SettingsLayout
      trail={trail}
      header={
        <ItemHeader
          hue={head.hue}
          lead={<SettingsTile icon="lock" hue={head.hue} size={48} />}
          title={<h1>Local accounts</h1>}
          meta={<StatusPill tone={local.enabled ? "success" : "neutral"}>{local.enabled ? "On" : "Off"}</StatusPill>}
          actions={
            local.enabled ? (
              working.length > 0 && (
                <button ref={offRef} className="danger-ghost" disabled={pending} onClick={() => setConfirming(true)}>
                  Turn off…
                </button>
              )
            ) : (
              <button className="secondary" disabled={pending} onClick={() => void turn(true)}>
                Turn on
              </button>
            )
          }
        />
      }
    >
      {error && !confirming && (
        <Notice tone="error" title="Not changed">
          {error}
        </Notice>
      )}
      <SettingsGroup
        title="Password sign-in"
        description={
          local.enabled
            ? "People sign in with an e-mail address and password; each may add an authenticator app on their Account page, and you can require it below. A provider brings the organisation's own multi-factor sign-in."
            : `Only the ${local.keptPeople === 1 ? "administrator" : `${local.keptPeople} administrators`} made on the server sign in with a password, from the link on the sign-in page. Everyone else signs in with a provider.`
        }
      >
        <SettingsPanel
          note={
            local.enabled && !working.length
              ? "Local sign-in can be turned off once a provider is enabled and has signed someone in, so nobody is locked out."
              : undefined
          }
        >
          <SettingRow
            keep
            name="Require a second factor with a password"
            help="A password alone no longer signs anyone in: a person with neither an authenticator app nor a passkey sets an app up on the sign-in page first. People signing in with a provider are not asked; the provider's own factor applies."
          >
            <Switch
              label="Require a second factor with a password"
              checked={local.secondFactorRequired}
              disabled={pending}
              onChange={(next) => (next ? setRequiring(true) : void require(false))}
            />
          </SettingRow>
        </SettingsPanel>
      </SettingsGroup>
      {requiring && (
        <ConfirmDialog
          title="Require a second factor?"
          confirmLabel="Require it"
          tone="plain"
          pending={pending}
          error={error}
          onCancel={() => {
            setRequiring(false);
            setError("");
          }}
          onConfirm={() => void require(true)}
        >
          <p>
            From now on, a password signs nobody in by itself. Each person types a code from an authenticator app, and
            one without an app sets it up on the sign-in page, with its recovery codes, before their session starts.
            That includes the administrators made on the server. People signing in with a provider are not asked.
          </p>
        </ConfirmDialog>
      )}
      {confirming && (
        <ConfirmDialog
          title="Turn local sign-in off?"
          confirmLabel="Turn off"
          pending={pending}
          error={error}
          onCancel={() => {
            setConfirming(false);
            setError("");
            offRef.current?.focus();
          }}
          onConfirm={() => void turn(false)}
        >
          <p>{turnOffSentence(offered, local.keptPeople)}</p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}
