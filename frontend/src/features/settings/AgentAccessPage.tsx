/**
 * Settings › Security › Agent access (0.16 AG1): the address assistants connect to, the agent clients
 * (systems whose assistant asks for a token), the assistants people sign in with and every tool call
 * made. Whether assistants can reach the instance is set in the server's environment (MCP_ENABLED)
 * and read at start; nothing here turns it on.
 */

import { useEffect, useRef, useState } from "react";
import { agentAccess } from "@/api/agentAccessClient";
import { errorMessage } from "@/api/errors";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { routePath } from "@/routing/routes";
import type { AgentAccessStatus, AgentApplication, AgentCall, AgentClient, RouteState } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { CopyValue } from "@/ui/CopyValue";
import { DescriptionList } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { FormField } from "@/ui/FormField";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { NewClientDialog, SecretDialog, type Made } from "@/features/security/ClientsPage";
import { clientAccessLine } from "@/features/security/securityText";

const number = (value: number) => value.toLocaleString("en");

/** The outcome of a call in a person's words. */
export const OUTCOME: Record<AgentCall["outcome"], string> = {
  answered: "Answered",
  refused: "Refused",
  limited: "Limit reached",
  failed: "Failed",
};

export function AgentAccessPage({ onNavigate }: { onNavigate: (route: RouteState) => void }) {
  const [status, setStatus] = useState<AgentAccessStatus>();
  const [error, setError] = useState("");

  function load() {
    agentAccess.status().then(
      (loaded) => {
        setStatus(loaded);
        setError("");
      },
      (cause) => setError(errorMessage(cause)),
    );
  }
  useEffect(load, []);

  return (
    <SettingsLayout
      eyebrow="Security"
      title="Agent access"
      description={
        status?.enabled
          ? "Assistants that speak MCP can reach this instance. They read and prepare changes within what their person or client may do. They never approve or publish."
          : undefined
      }
    >
      {error ? (
        <InlineError message={error} onRetry={load} />
      ) : !status ? (
        <Skeleton label="Loading agent access" lines={6} />
      ) : !status.enabled ? (
        <Notice tone="info" title="Agent access is off">
          No assistant can reach this instance. To turn it on, set <code>MCP_ENABLED=true</code> in the server&apos;s
          environment and restart it.
        </Notice>
      ) : (
        <>
          <ConnectSection status={status} />
          <ClientsSection onNavigate={onNavigate} />
          <ApplicationsSection />
          <CallsSection />
        </>
      )}
    </SettingsLayout>
  );
}

function ConnectSection({ status }: { status: AgentAccessStatus }) {
  return (
    <Section title="How to connect">
      <DescriptionList
        items={[
          { term: "Address", value: <CopyValue label="Address" value={status.url} labelled={false} /> },
          {
            term: "A person's assistant",
            value:
              "Add the address in the assistant. It opens this instance's sign-in page; the assistant then works as that person.",
          },
          {
            term: "A system's assistant",
            value: (
              <>
                Create an agent client below and give it access. It asks for a token with <code>scope=agent</code>.
              </>
            ),
          },
          { term: "Limit", value: `${number(status.ratePerMinute)} calls a minute for each person or client` },
        ]}
      />
      <pre className="mono agent-command" tabIndex={0} aria-label="Command line for Claude Code">
        {`claude mcp add --transport http refiroo ${status.url}`}
      </pre>
    </Section>
  );
}

function ClientsSection({ onNavigate }: { onNavigate: (route: RouteState) => void }) {
  const feed = useCursorFeed((cursor) => agentAccess.clients(cursor), []);
  const [creating, setCreating] = useState(false);
  const [made, setMade] = useState<Made>();
  const newButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <Section
      title="Agent clients"
      actions={
        <button ref={newButtonRef} type="button" className="primary" onClick={() => setCreating(true)}>
          New agent client
        </button>
      }
    >
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <Skeleton label="Loading agent clients" lines={3} />
      ) : !feed.items.length ? (
        <EmptyState>
          No agent client yet. Create one for a system whose assistant should reach this instance.
        </EmptyState>
      ) : (
        <SettingsTable label="Agent clients" columns={["Name", "Access", "Last used", "Calls, 30 days"]}>
          {feed.items.map((client) => (
            <ClientRow key={client.id} client={client} onNavigate={onNavigate} />
          ))}
        </SettingsTable>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more agent clients
        </button>
      )}
      {creating && (
        <NewClientDialog
          kind="agent"
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(client) => {
            setCreating(false);
            feed.reload();
            setMade({ client, created: true });
          }}
        />
      )}
      {made && <SecretDialog {...made} onClose={() => setMade(undefined)} />}
    </Section>
  );
}

function ClientRow({ client, onNavigate }: { client: AgentClient; onNavigate: (route: RouteState) => void }) {
  const route: RouteState = { kind: "settings", page: "clients", clientId: client.id };
  return (
    <tr>
      <th scope="row">
        <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
          {client.name}
        </RouteLink>
        {!client.active && (
          <>
            {" "}
            <StatusPill tone="neutral" marker={false}>
              Deactivated
            </StatusPill>
          </>
        )}
      </th>
      <td data-label="Access">{clientAccessLine(client)}</td>
      <td data-label="Last used">{client.lastCallAt ? formatServerDayTime(client.lastCallAt) : "Never"}</td>
      <td data-label="Calls, 30 days">{number(client.calls30Days)}</td>
    </tr>
  );
}

function ApplicationsSection() {
  const feed = useCursorFeed((cursor) => agentAccess.applications(cursor), []);
  const [registering, setRegistering] = useState(false);
  const [blocking, setBlocking] = useState<AgentApplication>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const registerRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  async function change(application: AgentApplication, action: "block" | "restore") {
    setPending(true);
    setError("");
    try {
      await agentAccess[action](application.id);
      setBlocking(undefined);
      feed.reload();
      toast(
        action === "block"
          ? `${application.name} was blocked. Its sessions end on their next call.`
          : `${application.name} was restored. People may sign in with it again.`,
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Section
      title="Assistants people sign in with"
      actions={
        <button ref={registerRef} type="button" className="secondary" onClick={() => setRegistering(true)}>
          Register an assistant
        </button>
      }
    >
      {error && !blocking && (
        <Notice tone="error" title="The action could not be completed">
          {error}
        </Notice>
      )}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <Skeleton label="Loading assistants" lines={3} />
      ) : !feed.items.length ? (
        <EmptyState>
          No assistant has signed anyone in yet. One appears here when a person adds the address in their assistant, or
          when you register it.
        </EmptyState>
      ) : (
        <SettingsTable
          label="Assistants people sign in with"
          columns={["Assistant", "Returns to", "Signed in now", "Last used", { hidden: "Actions" }]}
        >
          {feed.items.map((application) => (
            <tr key={application.id}>
              <th scope="row">
                {application.name}
                {application.blocked && (
                  <>
                    {" "}
                    <StatusPill tone="neutral" marker={false}>
                      Blocked
                    </StatusPill>
                  </>
                )}
              </th>
              <td data-label="Returns to">{application.returnsTo.join(", ")}</td>
              <td data-label="Signed in now">
                {number(application.signedIn)} {application.signedIn === 1 ? "person" : "people"}
              </td>
              <td data-label="Last used">
                {application.lastUsedAt ? formatServerDayTime(application.lastUsedAt) : "Never"}
              </td>
              <td className="grant-action">
                {application.blocked ? (
                  <button
                    type="button"
                    className="ghost"
                    disabled={pending}
                    aria-label={`Restore ${application.name}`}
                    onClick={() => void change(application, "restore")}
                  >
                    Restore
                  </button>
                ) : (
                  <button
                    type="button"
                    className="ghost"
                    disabled={pending}
                    aria-label={`Block ${application.name}`}
                    onClick={() => {
                      setError("");
                      setBlocking(application);
                    }}
                  >
                    Block
                  </button>
                )}
              </td>
            </tr>
          ))}
        </SettingsTable>
      )}
      <p className="section-description">
        The name is what the assistant says about itself. Blocking ends its sessions on their next call.
      </p>
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more assistants
        </button>
      )}
      {registering && (
        <RegisterDialog
          onClose={() => {
            setRegistering(false);
            registerRef.current?.focus();
          }}
          onRegistered={(application) => {
            setRegistering(false);
            feed.reload();
            toast(`${application.name} was registered. People may sign in with it.`);
          }}
        />
      )}
      {blocking && (
        <ConfirmDialog
          title={`Block ${blocking.name}?`}
          confirmLabel="Block"
          pending={pending}
          error={error}
          onCancel={() => {
            setBlocking(undefined);
            setError("");
          }}
          onConfirm={() => void change(blocking, "block")}
        >
          <p>
            No one can sign in with {blocking.name} any more, and its {number(blocking.signedIn)}{" "}
            {blocking.signedIn === 1 ? "session ends" : "sessions end"} on the next call. You can restore it later; the
            sessions that ended stay ended.
          </p>
        </ConfirmDialog>
      )}
    </Section>
  );
}

function RegisterDialog({
  onClose,
  onRegistered,
}: {
  onClose: () => void;
  onRegistered: (application: AgentApplication) => void;
}) {
  const [name, setName] = useState("");
  const [addresses, setAddresses] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const redirectUris = addresses
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  async function register() {
    setPending(true);
    setError("");
    try {
      onRegistered(await agentAccess.register({ name: name.trim(), redirectUris }));
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal
      title="Register an assistant"
      eyebrow="Agent access"
      size="compact"
      busy={pending}
      dirty={!!name || !!addresses}
      onClose={onClose}
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void register();
        }}
      >
        <FormField label="Name" help="What people see on the sign-in page.">
          {(control) => (
            <input
              {...control}
              autoFocus
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          )}
        </FormField>
        <FormField
          label="Return addresses"
          help="One per line. Exact HTTPS addresses, or a loopback address (localhost) on any port."
        >
          {(control) => (
            <textarea
              {...control}
              required
              rows={3}
              value={addresses}
              onChange={(event) => setAddresses(event.target.value)}
            />
          )}
        </FormField>
        {error && (
          <Notice tone="error" title="The assistant was not registered">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !name.trim() || !redirectUris.length}>
            {pending ? "Registering…" : "Register"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CallsSection() {
  const feed = useCursorFeed((cursor) => agentAccess.calls(cursor), []);
  return (
    <Section
      title="Calls"
      description="Every tool call an assistant made, newest first. Argument names are kept, never their values."
    >
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && !feed.items.length ? (
        <Skeleton label="Loading calls" lines={4} />
      ) : !feed.items.length ? (
        <EmptyState>No call has been made yet.</EmptyState>
      ) : (
        <SettingsTable label="Calls" columns={["When", "Who", "Through", "Tool", "Arguments", "Outcome"]}>
          {feed.items.map((call) => (
            <tr key={call.id}>
              <th scope="row">{formatServerDayTime(call.occurredAt)}</th>
              <td data-label="Who">{call.principal}</td>
              <td data-label="Through">{call.application ?? "Its own client"}</td>
              <td data-label="Tool">
                <code>{call.tool}</code>
              </td>
              <td data-label="Arguments">{call.arguments.length ? call.arguments.join(", ") : "None"}</td>
              <td data-label="Outcome">{OUTCOME[call.outcome] ?? call.outcome}</td>
            </tr>
          ))}
        </SettingsTable>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more
        </button>
      )}
    </Section>
  );
}
