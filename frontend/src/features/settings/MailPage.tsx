/**
 * Settings › Integration › Mail (0.12 M1, D418–D422): the SMTP server the engine sends mail
 * through, a test message that says what failed, and the outbox. The password is written once and
 * never shown. Messages wait in the outbox and the background worker sends them, so saving never
 * waits for the mail server; a message left unsent for 24 hours fails and says why.
 */

import { useEffect, useRef, useState, type FormEvent } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { mail } from "@/api/mailClient";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { MailSecurity, MailSettings, MailStatus } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { EmptyState } from "@/ui/EmptyState";
import { FormField } from "@/ui/FormField";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { failureTitle, MAIL_SECURITY, MESSAGE_STATE, messageKind, portFor } from "./mailText";

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

  return (
    <SettingsLayout
      eyebrow="Integration"
      title="Mail"
      description="The mail server the application sends through: the links of a new person and of a password reset. Messages wait in an outbox and are sent in the background, so a slow mail server never holds anyone up. A message that cannot be sent for 24 hours fails, and says why."
    >
      {error ? (
        <InlineError message={error} onRetry={load} />
      ) : !settings ? (
        <p className="admin-hint">Loading mail settings…</p>
      ) : (
        <>
          {!settings.configured && (
            <Notice tone="info" title="Mail is not set up">
              Nothing is sent until a server is saved. Everything else works as it does without mail: links are shown
              once for an administrator to pass on.
            </Notice>
          )}
          <ServerSection key={settings.version ?? 0} settings={settings} onSaved={setSettings} onChanged={load} />
          <TestSection configured={settings.configured} />
          <MessagesSection settings={settings} refresh={refresh} onRefresh={() => setRefresh((n) => n + 1)} />
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
  const [host, setHost] = useState(settings.host ?? "");
  const [security, setSecurity] = useState<MailSecurity>(settings.security ?? "starttls");
  const [port, setPort] = useState(String(settings.port ?? portFor(security)));
  const [username, setUsername] = useState(settings.username ?? "");
  const [password, setPassword] = useState("");
  const [from, setFrom] = useState(settings.fromAddress ?? "");
  const [url, setUrl] = useState(settings.applicationUrlIsDefault ? "" : settings.applicationUrl);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [removing, setRemoving] = useState(false);
  const removeRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  const saved = {
    host: settings.host ?? "",
    security: settings.security ?? "starttls",
    port: String(settings.port ?? portFor(settings.security ?? "starttls")),
    username: settings.username ?? "",
    from: settings.fromAddress ?? "",
    url: settings.applicationUrlIsDefault ? "" : settings.applicationUrl,
  };
  const dirty =
    !settings.configured ||
    host.trim() !== saved.host ||
    security !== saved.security ||
    port.trim() !== saved.port ||
    username.trim() !== saved.username ||
    !!password ||
    from.trim() !== saved.from ||
    url.trim() !== saved.url;
  const login = username.trim() !== "";
  const insecureLogin = security === "none" && login;
  const needsPassword = login && !password && !(settings.passwordSet && settings.username);

  function chooseSecurity(next: MailSecurity) {
    // The port follows the choice until someone has typed one of their own.
    if (port === String(portFor(security))) setPort(String(portFor(next)));
    setSecurity(next);
  }

  function reset() {
    setHost(saved.host);
    setSecurity(saved.security);
    setPort(saved.port);
    setUsername(saved.username);
    setPassword("");
    setFrom(saved.from);
    setUrl(saved.url);
    setError("");
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const saved = await mail.saveSettings({
        ...(settings.version !== null && { expectedVersion: settings.version }),
        host: host.trim(),
        port: Number(port),
        security,
        username: login ? username.trim() : null,
        ...(login && password && { password }),
        fromAddress: from.trim(),
        applicationUrl: url.trim() || null,
      });
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

  return (
    <Section title="Mail server">
      <form noValidate className="security-settings-form" onSubmit={(event) => void save(event)}>
        <div className="dialog-pair">
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
        </div>
        <FormField
          label="Connection"
          help="STARTTLS and TLS both encrypt the connection. A login is only sent over one of them."
        >
          {(control) => (
            <select {...control} value={security} onChange={(e) => chooseSecurity(e.target.value as MailSecurity)}>
              {MAIL_SECURITY.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          )}
        </FormField>
        <div className="dialog-pair">
          <FormField
            label="User name"
            help="Empty: the server needs no login."
            error={
              insecureLogin ? "A login is not sent over an unencrypted connection. Choose STARTTLS or TLS." : undefined
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
        </div>
        <FormField label="From address" help="The address mail comes from.">
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
        <FormField
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
        <div className="dialog-actions">
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
          <button
            type="button"
            className="secondary"
            disabled={pending || !dirty || !settings.configured}
            onClick={reset}
          >
            Cancel
          </button>
          <button
            className="primary"
            disabled={pending || !dirty || insecureLogin || needsPassword || !host.trim() || !port || !from.trim()}
          >
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
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
            No mail is sent. Messages already waiting stay in the outbox and fail after 24 hours unless a server is
            saved again by then. The saved password is deleted.
          </p>
        </ConfirmDialog>
      )}
    </Section>
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
    <Section
      title="Test message"
      description="Sent at once through the saved settings. It shows the address links will point to."
    >
      <form noValidate className="security-settings-form" onSubmit={(event) => void send(event)}>
        <FormField label="Send to">
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
        <div className="dialog-actions">
          <button className="secondary" disabled={pending || !configured || !to.trim()}>
            {pending ? "Sending…" : "Send test message"}
          </button>
        </div>
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
    </Section>
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

  return (
    <Section
      title="Messages"
      description="What the application asked to send. A message's text is never shown here; it holds a one-time link and is erased once sent."
    >
      <div className="settings-filter-bar">
        <label className="toolbar-field">
          State
          <select value={status} onChange={(event) => setStatus(event.target.value as MailStatus | "")}>
            <option value="">All</option>
            <option value="pending">Waiting ({counts.pending})</option>
            <option value="sent">Sent ({counts.sent})</option>
            <option value="failed">Failed ({counts.failed})</option>
          </select>
        </label>
        <button type="button" className="secondary" disabled={feed.loading} onClick={onRefresh}>
          Refresh
        </button>
      </div>
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <Skeleton label="Loading messages" lines={5} />
      ) : !feed.items.length ? (
        <EmptyState>
          {status
            ? "No message is in this state."
            : "No messages yet. A new person's link and a password reset appear here when they are sent."}
        </EmptyState>
      ) : (
        <SettingsTable label="Messages" columns={["To", "Message", "State", "Tries", "Last problem", "Queued"]}>
          {feed.items.map((message) => {
            const state = MESSAGE_STATE[message.status];
            return (
              <tr key={message.id}>
                <th scope="row">{message.to}</th>
                <td data-label="Message">{messageKind(message)}</td>
                <td data-label="State">
                  <StatusPill tone={state.tone}>{state.label}</StatusPill>
                  {message.status === "pending" && message.nextAttemptAt && (
                    <div className="admin-hint">Next try {formatServerDayTime(message.nextAttemptAt)}</div>
                  )}
                  {message.status !== "pending" && message.finishedAt && (
                    <div className="admin-hint">{formatServerDayTime(message.finishedAt)}</div>
                  )}
                </td>
                <td data-label="Tries">{message.attempts}</td>
                <td data-label="Last problem">{message.lastError ?? "—"}</td>
                <td data-label="Queued">{formatServerDayTime(message.createdAt)}</td>
              </tr>
            );
          })}
        </SettingsTable>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more messages
        </button>
      )}
    </Section>
  );
}
