/**
 * Settings › Integration › Mail (0.12 M1, D418–D422; 0.13 MS): how the engine sends mail (an SMTP
 * server, or Microsoft 365 through Graph), a test message that says what failed, and the outbox. The
 * password, client secret and certificate key are written once and never shown. Messages wait in the outbox and the background worker sends them, so saving never
 * waits for the mail server; a message left unsent for 24 hours fails and says why.
 */

import { useEffect, useRef, useState, type FormEvent } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { mail } from "@/api/mailClient";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useAddressTab } from "@/lib/hooks/useAddressTab";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type {
  MailCredential,
  MailIdentityMode,
  MailMessage,
  MailMethod,
  MailSecurity,
  MailSettings,
  MailStatus,
} from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { FormField } from "@/ui/FormField";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { FilterChip, LogFoot, LogTotals, SettingsEmpty, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { useToast } from "@/ui/Toast";
import {
  failureTitle,
  MAIL_SECURITY,
  MESSAGE_STATE,
  messageKind,
  portFor,
  SIGN_IN,
  SIGN_IN_ORDER,
  signInOf,
  type SignIn,
} from "./mailText";
import { settingsHead } from "@/ui/settingsNavigation";

export function MailPage() {
  const [settings, setSettings] = useState<MailSettings>();
  const [error, setError] = useState("");
  // Bumped whenever the outbox may have changed, so the list and the counts are read again.
  const [refresh, setRefresh] = useState(0);

  function load() {
    mail.settings().then(
      (loaded) => {
        setSettings(loaded);
        setError("");
      },
      (cause) => setError(errorMessage(cause)),
    );
  }
  useEffect(load, [refresh]);
  const [tab, setTab] = useAddressTab(["server", "messages"]);

  return (
    <SettingsLayout
      {...settingsHead("mail")}
      title="Mail"
      description="The mail server, or Microsoft 365, the application sends through: the links of a new person and of a password reset. Messages wait in an outbox and are sent in the background, so a slow mail server never holds anyone up. A message that cannot be sent for 24 hours fails, and says why."
    >
      {error ? (
        <InlineError message={error} onRetry={load} />
      ) : !settings ? (
        <Skeleton label="Loading mail settings" lines={4} />
      ) : (
        <>
          {!settings.configured && (
            <Notice tone="info" title="Mail is not set up">
              Nothing is sent until a server is saved. Everything else works as it does without mail: links are shown
              once for an administrator to pass on.
            </Notice>
          )}
          <Tabs
            label="Mail"
            selected={tab}
            onChange={setTab}
            tabs={[
              {
                id: "server",
                label: "Server",
                content: (
                  <>
                    <ServerSection
                      key={settings.version ?? 0}
                      settings={settings}
                      onSaved={setSettings}
                      onChanged={load}
                    />
                    <TestSection configured={settings.configured} />
                  </>
                ),
              },
              {
                id: "messages",
                label: "Messages",
                content: (
                  <MessagesSection settings={settings} refresh={refresh} onRefresh={() => setRefresh((n) => n + 1)} />
                ),
              },
            ]}
          />
        </>
      )}
    </SettingsLayout>
  );
}

function ServerSection({
  settings,
  onSaved,
  onChanged,
}: {
  settings: MailSettings;
  onSaved: (settings: MailSettings) => void;
  onChanged: () => void;
}) {
  const [method, setMethod] = useState<MailMethod>(settings.method ?? "smtp");
  const [host, setHost] = useState(settings.host ?? "");
  const [security, setSecurity] = useState<MailSecurity>(settings.security ?? "starttls");
  const [port, setPort] = useState(String(settings.port ?? portFor(security)));
  const [username, setUsername] = useState(settings.username ?? "");
  const [password, setPassword] = useState("");
  const [tenant, setTenant] = useState(settings.tenantId ?? "");
  const [client, setClient] = useState(settings.clientId ?? "");
  const [signIn, setSignIn] = useState<SignIn>(signInOf(settings));
  const [identityClient, setIdentityClient] = useState(settings.identityClientId ?? "");
  const [secret, setSecret] = useState("");
  const [certificate, setCertificate] = useState("");
  const [authority, setAuthority] = useState(settings.authorityUrl ?? "");
  const [graph, setGraph] = useState(settings.graphUrl ?? "");
  const [from, setFrom] = useState(settings.fromAddress ?? "");
  const [url, setUrl] = useState(settings.applicationUrlIsDefault ? "" : settings.applicationUrl);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [removing, setRemoving] = useState(false);
  const removeRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  const saved = {
    method: settings.method ?? "smtp",
    host: settings.host ?? "",
    security: settings.security ?? "starttls",
    port: String(settings.port ?? portFor(settings.security ?? "starttls")),
    username: settings.username ?? "",
    signIn: signInOf(settings),
    identityClient: settings.identityClientId ?? "",
    tenant: settings.tenantId ?? "",
    client: settings.clientId ?? "",
    authority: settings.authorityUrl ?? "",
    graph: settings.graphUrl ?? "",
    from: settings.fromAddress ?? "",
    url: settings.applicationUrlIsDefault ? "" : settings.applicationUrl,
  };
  const microsoft = method === "microsoft365";
  const credential: MailCredential = signIn === "secret" || signIn === "certificate" ? signIn : "managedIdentity";
  const identityMode: MailIdentityMode = signIn === "federated" ? "federated" : "direct";
  const identity = credential === "managedIdentity";
  const direct = identity && identityMode === "direct";
  const newCredential = credential === "secret" ? !!secret : credential === "certificate" && !!certificate.trim();
  const dirty =
    !settings.configured ||
    method !== saved.method ||
    host.trim() !== saved.host ||
    security !== saved.security ||
    port.trim() !== saved.port ||
    username.trim() !== saved.username ||
    !!password ||
    tenant.trim() !== saved.tenant ||
    client.trim() !== saved.client ||
    newCredential ||
    (microsoft && (signIn !== saved.signIn || (identity && identityClient.trim() !== saved.identityClient))) ||
    authority.trim() !== saved.authority ||
    graph.trim() !== saved.graph ||
    from.trim() !== saved.from ||
    url.trim() !== saved.url;
  const login = username.trim() !== "";
  const insecureLogin = !microsoft && security === "none" && login;
  const needsPassword = !microsoft && login && !password && !(settings.passwordSet && settings.username);
  // A saved credential is kept only for the same tenant, application and token address.
  const keepsCredential =
    settings.method === "microsoft365" &&
    settings.credential === credential &&
    (settings.clientSecretSet || !!settings.certificateThumbprint) &&
    tenant.trim() === saved.tenant &&
    client.trim() === saved.client &&
    (authority.trim() || DEFAULT_AUTHORITY) === (saved.authority || DEFAULT_AUTHORITY);
  const needsCredential = microsoft && !identity && !newCredential && !keepsCredential;
  const complete = microsoft
    ? identity
      ? direct || (!!identityClient.trim() && !!tenant.trim() && !!client.trim())
      : !!tenant.trim() && !!client.trim()
    : !!host.trim() && !!port;

  function chooseSecurity(next: MailSecurity) {
    // The port follows the choice until someone has typed one of their own.
    if (port === String(portFor(security))) setPort(String(portFor(next)));
    setSecurity(next);
  }

  function reset() {
    setMethod(saved.method);
    setHost(saved.host);
    setSecurity(saved.security);
    setPort(saved.port);
    setUsername(saved.username);
    setPassword("");
    setTenant(saved.tenant);
    setClient(saved.client);
    setSignIn(saved.signIn);
    setIdentityClient(saved.identityClient);
    setSecret("");
    setCertificate("");
    setAuthority(saved.authority);
    setGraph(saved.graph);
    setFrom(saved.from);
    setUrl(saved.url);
    setError("");
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const common = {
        ...(settings.version !== null && { expectedVersion: settings.version }),
        fromAddress: from.trim(),
        applicationUrl: url.trim() || null,
      };
      const saved = await mail.saveSettings(
        microsoft
          ? {
              ...common,
              method: "microsoft365",
              ...(!direct && { tenantId: tenant.trim(), clientId: client.trim() }),
              ...(identity && {
                identityMode,
                ...(identityClient.trim() && { identityClientId: identityClient.trim() }),
              }),
              ...(credential === "secret" && secret && { clientSecret: secret }),
              ...(credential === "certificate" && certificate.trim() && { certificate: certificate.trim() }),
              ...(authority.trim() && { authorityUrl: authority.trim() }),
              ...(graph.trim() && { graphUrl: graph.trim() }),
            }
          : {
              ...common,
              method: "smtp",
              host: host.trim(),
              port: Number(port),
              security,
              username: login ? username.trim() : null,
              ...(login && password && { password }),
            },
      );
      onSaved(saved);
      toast("Mail settings saved. Send a test message to try them.");
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT")) onChanged();
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    setPending(true);
    setError("");
    try {
      await mail.removeSettings();
      setRemoving(false);
      onChanged();
      toast("Mail settings removed. No mail is sent.");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const foot = (
    <>
      {settings.configured && (
        <button
          ref={removeRef}
          type="button"
          className="danger-ghost"
          disabled={pending}
          onClick={() => setRemoving(true)}
        >
          Remove settings…
        </button>
      )}
      <span className="settings-panel-state">{dirty && settings.configured ? "Changed, not saved" : ""}</span>
      <button type="button" className="ghost" disabled={pending || !dirty || !settings.configured} onClick={reset}>
        Cancel
      </button>
      <button
        className="primary"
        disabled={pending || !dirty || insecureLogin || needsPassword || needsCredential || !complete || !from.trim()}
      >
        {pending ? "Saving…" : "Save"}
      </button>
    </>
  );

  return (
    <SettingsGroup
      title="Mail server"
      description="How the application sends mail. The password, client secret and certificate are kept sealed and never shown again."
    >
      <form noValidate onSubmit={(event) => void save(event)}>
        <SettingsPanel foot={foot}>
          <div className="settings-fields">
            <FormField
              className="full"
              label="Send mail through"
              help={
                microsoft
                  ? "Microsoft 365 sends through Microsoft Graph as one mailbox. Saving it replaces the SMTP settings."
                  : "An SMTP server. Choosing Microsoft 365 replaces these settings when saved."
              }
            >
              {(control) => (
                <select {...control} value={method} onChange={(e) => setMethod(e.target.value as MailMethod)}>
                  <option value="smtp">SMTP server</option>
                  <option value="microsoft365">Microsoft 365</option>
                </select>
              )}
            </FormField>
            {microsoft ? (
              <MicrosoftFields
                settings={settings}
                signIn={signIn}
                onSignIn={setSignIn}
                tenant={tenant}
                onTenant={setTenant}
                client={client}
                onClient={setClient}
                identityClient={identityClient}
                onIdentityClient={setIdentityClient}
                secret={secret}
                onSecret={setSecret}
                certificate={certificate}
                onCertificate={setCertificate}
                keepsCredential={keepsCredential}
              />
            ) : (
              <>
                <>
                  <FormField label="Server" help="The SMTP host name.">
                    {(control) => (
                      <input
                        {...control}
                        className="mono"
                        required
                        maxLength={255}
                        autoComplete="off"
                        value={host}
                        onChange={(e) => setHost(e.target.value)}
                      />
                    )}
                  </FormField>
                  <FormField label="Port">
                    {(control) => (
                      <input
                        {...control}
                        className="mono"
                        required
                        inputMode="numeric"
                        value={port}
                        onChange={(e) => setPort(e.target.value.replace(/\D/g, ""))}
                      />
                    )}
                  </FormField>
                </>
                <FormField
                  className="full"
                  label="Connection"
                  help="STARTTLS and TLS both encrypt the connection. A login is only sent over one of them."
                >
                  {(control) => (
                    <select
                      {...control}
                      value={security}
                      onChange={(e) => chooseSecurity(e.target.value as MailSecurity)}
                    >
                      {MAIL_SECURITY.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  )}
                </FormField>
                <>
                  <FormField
                    label="User name"
                    help="Empty: the server needs no login."
                    error={
                      insecureLogin
                        ? "A login is not sent over an unencrypted connection. Choose STARTTLS or TLS."
                        : undefined
                    }
                  >
                    {(control) => (
                      <input
                        {...control}
                        maxLength={255}
                        autoComplete="off"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                      />
                    )}
                  </FormField>
                  <FormField label="Password" help="Kept sealed; it is never shown again.">
                    {(control) => (
                      <input
                        {...control}
                        type="password"
                        autoComplete="new-password"
                        disabled={!login}
                        placeholder={settings.passwordSet && login ? "Saved · type a new one to replace it" : ""}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                      />
                    )}
                  </FormField>
                </>
              </>
            )}
            <FormField
              className="full"
              label={microsoft ? "Sending mailbox" : "From address"}
              help={
                microsoft
                  ? "The mailbox mail is sent as and comes from. Bounces and replies arrive in this mailbox; the application does not read them."
                  : "The address mail comes from."
              }
            >
              {(control) => (
                <input
                  {...control}
                  required
                  inputMode="email"
                  maxLength={320}
                  autoComplete="off"
                  value={from}
                  onChange={(e) => setFrom(e.target.value)}
                />
              )}
            </FormField>
            {microsoft && (
              <MicrosoftNotes
                signIn={signIn}
                authority={authority}
                onAuthority={setAuthority}
                graph={graph}
                onGraph={setGraph}
                initiallyOpen={
                  (!!saved.authority && saved.authority !== DEFAULT_AUTHORITY) ||
                  (!!saved.graph && saved.graph !== DEFAULT_GRAPH)
                }
              />
            )}
            <FormField
              className="full"
              label="Application address"
              help={
                <>
                  Links in mail point here. Empty: <span className="mono">{settings.applicationUrl}</span>, the first
                  address the application is allowed to be reached at.
                </>
              }
            >
              {(control) => (
                <input
                  {...control}
                  className="mono"
                  maxLength={2000}
                  autoComplete="off"
                  placeholder={settings.applicationUrl}
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
              )}
            </FormField>
            {error && (
              <Notice tone="error" title="The settings were not saved">
                {error}
              </Notice>
            )}
          </div>
        </SettingsPanel>
      </form>
      {removing && (
        <ConfirmDialog
          title="Remove the mail settings?"
          confirmLabel="Remove them"
          pending={pending}
          error={error}
          onCancel={() => {
            setRemoving(false);
            setError("");
            removeRef.current?.focus();
          }}
          onConfirm={() => void remove()}
        >
          <p>
            No mail is sent. Messages already waiting stay in the outbox and fail after 24 hours unless mail is set up
            again by then. The saved password, client secret or certificate is deleted.
          </p>
        </ConfirmDialog>
      )}
    </SettingsGroup>
  );
}

const DEFAULT_AUTHORITY = "https://login.microsoftonline.com";
const DEFAULT_GRAPH = "https://graph.microsoft.com";

/** The Microsoft 365 fields of the chosen way to sign in; nothing else is shown. */
function MicrosoftFields(props: {
  settings: MailSettings;
  signIn: SignIn;
  onSignIn: (value: SignIn) => void;
  tenant: string;
  onTenant: (value: string) => void;
  client: string;
  onClient: (value: string) => void;
  identityClient: string;
  onIdentityClient: (value: string) => void;
  secret: string;
  onSecret: (value: string) => void;
  certificate: string;
  onCertificate: (value: string) => void;
  keepsCredential: boolean;
}) {
  const { settings, signIn } = props;
  const savedSecret = props.keepsCredential && settings.clientSecretSet;
  const savedCertificate = props.keepsCredential && !!settings.certificateThumbprint;
  const azureNote = (
    <p className="admin-hint full">
      A managed identity works only when refiroo runs in Azure (App Service, Container Apps or a virtual machine). No
      secret is stored.
    </p>
  );
  return (
    <>
      <FormField className="full" label="Sign in with" help={SIGN_IN[signIn].description}>
        {(control) => (
          <select {...control} value={signIn} onChange={(e) => props.onSignIn(e.target.value as SignIn)}>
            {SIGN_IN_ORDER.map((entry) => (
              <option key={entry} value={entry}>
                {SIGN_IN[entry].label}
              </option>
            ))}
          </select>
        )}
      </FormField>
      {signIn === "direct" && (
        <>
          <FormField
            className="full"
            label="Identity client ID"
            help="The user-assigned identity's client ID. Empty: the identity of the host itself (system-assigned)."
          >
            {(control) => (
              <input
                {...control}
                className="mono"
                maxLength={200}
                autoComplete="off"
                value={props.identityClient}
                onChange={(e) => props.onIdentityClient(e.target.value)}
              />
            )}
          </FormField>
          {azureNote}
        </>
      )}
      {signIn !== "direct" && (
        <>
          <FormField
            label="Tenant ID"
            help={
              signIn === "federated"
                ? "The customer's directory (tenant) ID, or its domain name."
                : "The directory (tenant) ID, or the tenant's domain name."
            }
          >
            {(control) => (
              <input
                {...control}
                className="mono"
                required
                maxLength={200}
                autoComplete="off"
                value={props.tenant}
                onChange={(e) => props.onTenant(e.target.value)}
              />
            )}
          </FormField>
          <FormField
            label="Application (client) ID"
            help={signIn === "federated" ? "The multitenant app registration that trusts the identity." : undefined}
          >
            {(control) => (
              <input
                {...control}
                className="mono"
                required
                maxLength={200}
                autoComplete="off"
                value={props.client}
                onChange={(e) => props.onClient(e.target.value)}
              />
            )}
          </FormField>
        </>
      )}
      {signIn === "federated" && (
        <>
          <FormField
            className="full"
            label="Identity client ID"
            help="The user-assigned identity's client ID. Required: only a user-assigned identity can be a federated credential."
          >
            {(control) => (
              <input
                {...control}
                className="mono"
                required
                maxLength={200}
                autoComplete="off"
                value={props.identityClient}
                onChange={(e) => props.onIdentityClient(e.target.value)}
              />
            )}
          </FormField>
          {azureNote}
        </>
      )}
      {signIn === "secret" && (
        <FormField
          className="full"
          label="Client secret"
          help="The secret's value. Kept sealed; it is never shown again."
        >
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="new-password"
              placeholder={savedSecret ? "Saved · type a new one to replace it" : ""}
              value={props.secret}
              onChange={(e) => props.onSecret(e.target.value)}
            />
          )}
        </FormField>
      )}
      {signIn === "certificate" && (
        <FormField
          className="full"
          label="Certificate"
          help={
            savedCertificate && settings.certificateExpiresAt ? (
              <>
                Saved: thumbprint <span className="mono">{settings.certificateThumbprint}</span>, expires{" "}
                {formatServerDayTime(settings.certificateExpiresAt)}. Paste a new one to replace it. Upload the
                certificate (without the key) to the app registration.
              </>
            ) : (
              "Paste the private key (not password-protected) and the certificate, in PEM form. The key is kept sealed and never shown again. Upload the certificate (without the key) to the app registration."
            )
          }
        >
          {(control) => (
            <textarea
              {...control}
              className="mono"
              rows={6}
              spellCheck={false}
              autoComplete="off"
              placeholder={savedCertificate ? "Saved · paste a new one to replace it" : "-----BEGIN PRIVATE KEY-----"}
              value={props.certificate}
              onChange={(e) => props.onCertificate(e.target.value)}
            />
          )}
        </FormField>
      )}
    </>
  );
}

/** Below the sending mailbox: what to set up in Entra for the chosen entry, and the addresses of other clouds. */
function MicrosoftNotes(props: {
  signIn: SignIn;
  authority: string;
  onAuthority: (value: string) => void;
  graph: string;
  onGraph: (value: string) => void;
  initiallyOpen: boolean;
}) {
  const [cloudsOpen, setCloudsOpen] = useState(props.initiallyOpen);
  return (
    <>
      <details className="settings-fold full">
        <summary>What to set up in Microsoft Entra</summary>
        <div className="settings-fold-body">
          <EntraChecklist signIn={props.signIn} />
        </div>
      </details>
      <details className="settings-fold full" open={cloudsOpen} onToggle={(e) => setCloudsOpen(e.currentTarget.open)}>
        <summary>Other Microsoft clouds (token and Graph addresses)</summary>
        <div className="settings-fold-body">
          <div className="dialog-pair">
            <FormField label="Token address" help="Where Microsoft issues tokens. Empty: the global service.">
              {(control) => (
                <input
                  {...control}
                  className="mono"
                  maxLength={2000}
                  autoComplete="off"
                  placeholder={DEFAULT_AUTHORITY}
                  value={props.authority}
                  onChange={(e) => props.onAuthority(e.target.value)}
                />
              )}
            </FormField>
            <FormField label="Graph address" help="Change both for a national cloud.">
              {(control) => (
                <input
                  {...control}
                  className="mono"
                  maxLength={2000}
                  autoComplete="off"
                  placeholder={DEFAULT_GRAPH}
                  value={props.graph}
                  onChange={(e) => props.onGraph(e.target.value)}
                />
              )}
            </FormField>
          </div>
        </div>
      </details>
    </>
  );
}

/** The steps of the chosen way to sign in, by entry. */
function EntraChecklist({ signIn }: { signIn: SignIn }) {
  const mailSend = <span className="mono">Mail.Send</span>;
  const policy =
    "Limit it to the sending mailbox with an application access policy (or RBAC for Applications). Without one, it can send as any mailbox in the tenant.";
  if (signIn === "direct")
    return (
      <ol>
        <li>Run refiroo on Azure (App Service, Container Apps or a virtual machine) with a managed identity.</li>
        <li>
          Give the identity's service principal the Microsoft Graph {mailSend} app role (Entra has no button for it: the
          operator guide has the command). Admin consent is not asked for.
        </li>
        <li>{policy} Name the identity's client ID.</li>
      </ol>
    );
  if (signIn === "federated")
    return (
      <ol>
        <li>
          Run refiroo on Azure with a user-assigned managed identity. In the hosting tenant, make a multitenant app
          registration and add a federated credential for the identity (issuer, subject = the identity's principal ID,
          audience).
        </li>
        <li>The organisation's administrator grants the app admin consent in their tenant.</li>
        <li>
          In their tenant, the {mailSend} permission is granted to the app and an application access policy limits it to
          the sending mailbox.
        </li>
      </ol>
    );
  return (
    <ol>
      <li>Register an application (an app registration) and copy its tenant ID and application (client) ID.</li>
      <li>Give it a client secret, or upload a certificate to it.</li>
      <li>Add the {mailSend} application permission to Microsoft Graph and grant admin consent.</li>
      <li>
        Limit the application to the sending mailbox with an application access policy (or RBAC for Applications).
        Without one, it can send as any mailbox in the tenant.
      </li>
    </ol>
  );
}

function TestSection({ configured }: { configured: boolean }) {
  const [to, setTo] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<{ ok: true; to: string } | { ok: false; title: string; message: string }>();

  async function send(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setResult(undefined);
    try {
      const sent = await mail.sendTest(to.trim());
      setResult({ ok: true, to: sent.sentTo });
    } catch (cause) {
      const details = isApiError(cause) ? (cause.details as { kind?: unknown } | undefined) : undefined;
      setResult({ ok: false, title: failureTitle(details?.kind), message: errorMessage(cause) });
    } finally {
      setPending(false);
    }
  }

  return (
    <SettingsGroup
      title="Test message"
      description="Sent at once through the saved settings. It shows the address links will point to."
    >
      <form noValidate onSubmit={(event) => void send(event)}>
        <SettingsPanel
          foot={
            <button className="secondary" disabled={pending || !configured || !to.trim()}>
              {pending ? "Sending…" : "Send test message"}
            </button>
          }
        >
          <div className="settings-fields">
            <FormField className="full" label="Send to">
              {(control) => (
                <input
                  {...control}
                  required
                  inputMode="email"
                  autoComplete="email"
                  disabled={!configured}
                  value={to}
                  onChange={(e) => setTo(e.target.value)}
                />
              )}
            </FormField>
          </div>
        </SettingsPanel>
      </form>
      {result &&
        (result.ok ? (
          <Notice tone="success" title="Sent">
            The server accepted the message for {result.to}. Open the mailbox to see it arrive.
          </Notice>
        ) : (
          <Notice tone="error" title={result.title}>
            {result.message}
          </Notice>
        ))}
    </SettingsGroup>
  );
}

function MessagesSection({
  settings,
  refresh,
  onRefresh,
}: {
  settings: MailSettings;
  refresh: number;
  onRefresh: () => void;
}) {
  const [status, setStatus] = useState<MailStatus | "">("");
  const feed = useCursorFeed((cursor) => mail.messages({ status: status || undefined, cursor }), [status, refresh]);
  const counts = settings.outbox;
  const [stopping, setStopping] = useState<MailMessage>();
  const [stopError, setStopError] = useState("");
  const [stopPending, setStopPending] = useState(false);

  async function stop() {
    if (!stopping) return;
    setStopPending(true);
    setStopError("");
    try {
      const updated = await mail.stopMessage(stopping.id);
      feed.setItems((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setStopping(undefined);
      onRefresh();
    } catch (cause) {
      if (isApiError(cause, "MESSAGE_NOT_WAITING")) {
        // It was sent, or gave up, before the request reached it: show where it ended.
        setStopping(undefined);
        onRefresh();
      } else {
        setStopError(errorMessage(cause));
      }
    } finally {
      setStopPending(false);
    }
  }

  const states: { value: MailStatus | ""; label: string }[] = [
    { value: "", label: "All" },
    { value: "pending", label: "Waiting" },
    { value: "sent", label: "Sent" },
    { value: "failed", label: "Failed" },
  ];
  const total = status ? counts[status] : counts.pending + counts.sent + counts.failed;

  return (
    <>
      <LogTotals
        label="Outbox"
        totals={[
          { key: "pending", value: counts.pending.toLocaleString(), name: "waiting", hue: 3 },
          { key: "sent", value: counts.sent.toLocaleString(), name: "sent", hue: 5 },
          { key: "failed", value: counts.failed.toLocaleString(), name: "failed", bad: true },
        ]}
      />
      <SettingsGroup
        stacked
        title="Messages"
        description="What the application asked to send. A message's text is never shown here; it holds a one-time link and is erased once sent."
        tools={
          <>
            <span className="filter-chips" role="group" aria-label="State">
              {states.map((item) => (
                <FilterChip key={item.value} selected={status === item.value} onSelect={() => setStatus(item.value)}>
                  {item.label}
                </FilterChip>
              ))}
            </span>
            <button type="button" className="secondary" disabled={feed.loading} onClick={onRefresh}>
              Refresh
            </button>
          </>
        }
      >
        <SettingsPanel>
          {feed.error ? (
            <InlineError message={feed.error} onRetry={feed.retry} />
          ) : feed.loading && !feed.items.length ? (
            <Skeleton label="Loading messages" lines={5} />
          ) : !feed.items.length ? (
            <SettingsEmpty icon="mail" hue={settingsHead("mail").hue}>
              {status
                ? "No message is in this state."
                : "No messages yet. A new person's link and a password reset appear here when they are sent."}
            </SettingsEmpty>
          ) : (
            <>
              <SettingsTable
                label="Messages"
                columns={["Queued", "To", "Message", "State", { num: "Tries" }, "Last problem", { hidden: "Actions" }]}
              >
                {feed.items.map((message) => {
                  const state = MESSAGE_STATE[message.status];
                  return (
                    <tr key={message.id}>
                      <th scope="row" className="when" title={formatServerTime(message.createdAt)}>
                        {formatServerDayTime(message.createdAt)}
                      </th>
                      <td data-label="To">{message.to}</td>
                      <td data-label="Message">{messageKind(message)}</td>
                      <td data-label="State">
                        <StatusPill tone={state.tone}>{state.label}</StatusPill>
                        {message.status === "pending" && message.nextAttemptAt && (
                          <span className="why">Next try {formatServerDayTime(message.nextAttemptAt)}</span>
                        )}
                        {message.status !== "pending" && message.finishedAt && (
                          <span className="why">{formatServerDayTime(message.finishedAt)}</span>
                        )}
                      </td>
                      <td data-label="Tries" className="num">
                        {message.attempts.toLocaleString()}
                      </td>
                      <td data-label="Last problem">{message.lastError ?? "—"}</td>
                      <td data-label="Actions">
                        {message.status === "pending" && (
                          <button type="button" className="secondary" onClick={() => setStopping(message)}>
                            Stop sending
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </SettingsTable>
              <LogFoot
                shown={feed.items.length}
                total={feed.hasMore ? total : feed.items.length}
                noun="messages"
                onMore={feed.hasMore && !feed.error ? feed.loadMore : undefined}
                loading={feed.loading}
              />
            </>
          )}
        </SettingsPanel>
        {stopping && (
          <ConfirmDialog
            title="Stop sending this message?"
            confirmLabel="Stop sending"
            dismissLabel="Keep trying"
            pending={stopPending}
            error={stopError}
            onCancel={() => {
              setStopping(undefined);
              setStopError("");
            }}
            onConfirm={() => void stop()}
          >
            <p>
              The message to {stopping.to} will not be sent, now or on a later try. It is marked failed, and its text is
              erased. The link in it keeps working until it expires; make a new link to send another.
            </p>
          </ConfirmDialog>
        )}
      </SettingsGroup>
    </>
  );
}
