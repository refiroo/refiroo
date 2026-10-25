/**
 * Settings › Security › Sign-in (0.12 I3, U8): how people prove who they are. Local accounts first,
 * on or off (D365), then the OpenID Connect providers beside the selected one (U-D10's list and
 * detail). A provider's page gives the address to register with it, edits its settings in place
 * (the secret is never shown, only replaced; an enabled provider is read when saved, D366), and
 * enables, disables or deletes it (delete only while nobody has signed in with it). Local sign-in
 * is turned off only once a provider has signed someone in, keeping the administrators made on the
 * server.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { security } from "@/api/securityClient";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { LocalSignIn, RouteState, SettingsRoute, SignInProvider, SignInProviderCreate } from "@/types";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { CopyValue } from "@/ui/CopyValue";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
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

  const catalogue = (
    <nav className="model-catalogue security-catalogue" aria-label="Sign-in">
      <section>
        <CatalogueEntry
          icon="lock"
          title="Local accounts"
          subtitle={local ? localSignInLine(local) : localError || "Loading…"}
          pill={
            local && (
              <StatusPill tone={local.enabled ? "success" : "neutral"}>{local.enabled ? "On" : "Off"}</StatusPill>
            )
          }
          current={route.providerKey === LOCAL}
          onSelect={() => onNavigate({ ...SIGN_IN, providerKey: LOCAL })}
        />
      </section>
      <section>
        <h2 className="nav-label">Providers</h2>
        {feed.items.map((provider) => (
          <CatalogueEntry
            key={provider.key}
            icon="globe"
            title={provider.name}
            subtitle={providerUseLine(provider)}
            pill={
              <StatusPill tone={provider.enabled ? "success" : "neutral"}>
                {provider.enabled ? "Enabled" : "Disabled"}
              </StatusPill>
            }
            current={route.providerKey === provider.key}
            onSelect={() => onNavigate({ ...SIGN_IN, providerKey: provider.key })}
          />
        ))}
        {feed.loading && !feed.items.length && <p className="explorer-empty">Loading providers…</p>}
        {!feed.loading && !feed.error && !feed.items.length && (
          <p className="explorer-empty">No provider yet: people sign in with a password.</p>
        )}
        {feed.error && (
          <div className="catalogue-error">
            <InlineError message={feed.error} onRetry={feed.retry} />
          </div>
        )}
        {feed.hasMore && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more providers
          </button>
        )}
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Security"
      title="Sign-in"
      description="How people prove who they are: a username and password, or the organisation's sign-in provider (OpenID Connect) with its own multi-factor sign-in. The engine starts its own session either way."
      actions={
        <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
          <Icon name="plus" /> New provider
        </button>
      }
    >
      <CatalogueLayout
        catalogue={catalogue}
        hasSelection={!!route.providerKey}
        backLabel="Sign-in"
        onBack={() => onNavigate(SIGN_IN)}
      >
        {route.providerKey === LOCAL ? (
          local ? (
            <LocalDetail local={local} providers={feed.items} onChanged={setLocal} />
          ) : localError ? (
            <InlineError message={localError} onRetry={loadLocal} />
          ) : (
            <div className="panel-state">Loading local accounts…</div>
          )
        ) : route.providerKey ? (
          <ProviderDetail
            key={route.providerKey}
            providerKey={route.providerKey}
            onChanged={changed}
            onDeleted={() => {
              feed.reload();
              onNavigate(SIGN_IN);
            }}
          />
        ) : (
          <div className="panel-state">Choose local accounts or a provider.</div>
        )}
      </CatalogueLayout>
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
    </SettingsLayout>
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
      eyebrow="Security"
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
          label="Groups claim"
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
            {pending ? "Checking and saving…" : "Save provider"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ProviderDetail({
  providerKey,
  onChanged,
  onDeleted,
}: {
  providerKey: string;
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

  if (loadError) return <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />;
  if (!provider) return <div className="panel-state">Loading provider…</div>;

  return (
    <div className="model-editor-stack security-detail">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Sign-in provider</p>
          <h2>{provider.name}</h2>
          <div className="security-pills">
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
          </div>
        </div>
      </header>
      {actionError && (
        <Notice tone="error" title="Not saved" focusOnMount>
          {actionError}
        </Notice>
      )}
      <div className="model-actions">
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
      </div>
      <Section
        title="Address to register with the provider"
        description="Add it as the redirect address of the application you registered for the engine at the provider."
      >
        <p className="webhook-secret">
          <CopyValue label="Redirect address" value={provider.redirectUri} />
        </p>
      </Section>
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
    </div>
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
    <Section title="Settings">
      <form
        noValidate
        className="security-settings-form"
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
        <div className="dialog-pair">
          <FormField label="Name on the sign-in button" help={`The button reads “Continue with ${name || "…"}”.`}>
            {(control) => (
              <input {...control} required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} />
            )}
          </FormField>
          <FormField label="Key" help="In the address above; fixed once saved.">
            {(control) => <input {...control} className="mono" value={provider.key} readOnly />}
          </FormField>
        </div>
        <FormField label="Issuer">
          {(control) => (
            <input {...control} className="mono" required value={issuer} onChange={(e) => setIssuer(e.target.value)} />
          )}
        </FormField>
        <div className="dialog-pair">
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
        </div>
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
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending || !dirty} onClick={reset}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !dirty}>
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Section>
  );
}

function LocalDetail({
  local,
  providers,
  onChanged,
}: {
  local: LocalSignIn;
  providers: readonly SignInProvider[];
  onChanged: (local: LocalSignIn) => void;
}) {
  const [confirming, setConfirming] = useState(false);
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

  return (
    <div className="model-editor-stack security-detail">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Sign-in</p>
          <h2>Local accounts</h2>
          <div className="security-pills">
            <StatusPill tone={local.enabled ? "success" : "neutral"}>{local.enabled ? "On" : "Off"}</StatusPill>
          </div>
        </div>
      </header>
      <p>
        {local.enabled
          ? "People sign in with a username and password. Passwords have no second factor: a provider brings the organisation's multi-factor sign-in."
          : `Only the ${local.keptPeople === 1 ? "administrator" : `${local.keptPeople} administrators`} made on the server sign in with a password, from the link on the sign-in page. Everyone else signs in with a provider.`}
      </p>
      {error && !confirming && (
        <Notice tone="error" title="Not changed">
          {error}
        </Notice>
      )}
      <div className="model-actions">
        {local.enabled ? (
          working.length > 0 && (
            <button ref={offRef} className="danger-ghost" disabled={pending} onClick={() => setConfirming(true)}>
              Turn off…
            </button>
          )
        ) : (
          <button className="secondary" disabled={pending} onClick={() => void turn(true)}>
            Turn on
          </button>
        )}
      </div>
      {local.enabled && !working.length && (
        <p className="admin-hint">
          Local sign-in can be turned off once a provider is enabled and has signed someone in, so nobody is locked out.
        </p>
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
    </div>
  );
}
