/**
 * Settings › Security › Agent access (0.16 AG1): the address assistants connect to, the agent clients
 * (systems whose assistant asks for a token), the assistants people sign in with and every tool call
 * made. Whether assistants can reach the instance is set in the server's environment (MCP_ENABLED)
 * and read at start; nothing here turns it on.
 */

import { useEffect, useRef, useState } from "react";
import { agentAccess } from "@/api/agentAccessClient";
import { errorMessage } from "@/api/errors";
import { count, plural } from "@/lib/count";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useAddressTab } from "@/lib/hooks/useAddressTab";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { routePath } from "@/routing/routes";
import type { Hue } from "@/model/hues";
import type { AgentAccessStatus, AgentApplication, AgentCall, AgentClient, RouteState } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { CopyValue } from "@/ui/CopyValue";
import { FormField } from "@/ui/FormField";
import { InlineError } from "@/ui/InlineError";
import { CancelButton, Modal } from "@/ui/Modal";
import { ActionNotices } from "@/ui/ActionNotices";
import { Notice } from "@/ui/Notice";
import { useGuardedWrite } from "@/ui/useGuardedWrite";
import { RouteLink } from "@/ui/RouteLink";
import { SettingsLayout } from "@/ui/SettingsLayout";
import {
  LogFoot,
  NameMark,
  SettingRow,
  SettingsEmpty,
  SettingsGroup,
  SettingsPanel,
  SettingsTile,
} from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill, type StatusTone } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { useToast } from "@/ui/Toast";
import { NewClientDialog, SecretDialog, type Made } from "@/features/security/ClientsPage";
import { clientAccessLine } from "@/features/security/securityText";
import { settingsHead } from "@/ui/settingsNavigation";

/** The outcome of a call in a person's words. */
export const OUTCOME: Record<AgentCall["outcome"], string> = {
  answered: "Answered",
  refused: "Refused",
  limited: "Limit reached",
  failed: "Failed",
};

const OUTCOME_TONE: Record<AgentCall["outcome"], StatusTone> = {
  answered: "success",
  refused: "neutral",
  limited: "warning",
  failed: "error",
};

export function AgentAccessPage({ onNavigate }: { onNavigate: (route: RouteState) => void }) {
  const [status, setStatus] = useState<AgentAccessStatus>();
  const [error, setError] = useState("");
  const [tab, setTab] = useAddressTab(["access", "calls"]);
  // The page's one primary is in its header, so the agent client it makes is handled here.
  const [creating, setCreating] = useState(false);
  const [made, setMade] = useState<Made>();
  const [clientsVersion, setClientsVersion] = useState(0);
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const head = settingsHead("agent-access");

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
      {...head}
      title="Agent access"
      description={
        status?.enabled
          ? "Assistants that speak MCP can reach this instance. They read and prepare changes within what their person or client may do. They never approve or publish."
          : undefined
      }
      actions={
        status?.enabled ? (
          <button ref={newButtonRef} type="button" className="primary" onClick={() => setCreating(true)}>
            New agent client
          </button>
        ) : undefined
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
          <Tabs
            label="Agent access"
            selected={tab}
            onChange={setTab}
            tabs={[
              {
                id: "access",
                label: "Access",
                content: (
                  <>
                    <ConnectSection status={status} hue={head.hue} />
                    <ClientsSection version={clientsVersion} onNavigate={onNavigate} />
                    <ApplicationsSection hue={head.hue} />
                  </>
                ),
              },
              { id: "calls", label: "Calls", content: <CallsSection /> },
            ]}
          />
          {creating && (
            <NewClientDialog
              kind="agent"
              onClose={() => {
                setCreating(false);
                newButtonRef.current?.focus();
              }}
              onCreated={(client) => {
                setCreating(false);
                setClientsVersion((value) => value + 1);
                setMade({ client, created: true });
              }}
            />
          )}
          {made && <SecretDialog {...made} onClose={() => setMade(undefined)} />}
        </>
      )}
    </SettingsLayout>
  );
}

function ConnectSection({ status, hue }: { status: AgentAccessStatus; hue: Hue }) {
  return (
    <SettingsGroup title="How to connect">
      <SettingsPanel>
        <SettingRow fact name="Address">
          <CopyValue label="Address" value={status.url} labelled={false} />
        </SettingRow>
        <SettingRow
          name="A person's assistant"
          help="Add the address in the assistant. It opens this instance's sign-in page; the assistant then works as that person."
        />
        <SettingRow
          name="A system's assistant"
          help={
            <>
              Create an agent client below and give it access. It asks for a token with <code>scope=agent</code>.
            </>
          }
        />
        <SettingRow fact name="Limit">
          {`${count(status.ratePerMinute)} calls a minute for each person or client`}
        </SettingRow>
        <SettingRow
          under
          lead={<SettingsTile icon="bot" hue={hue} />}
          name="Command line for Claude Code"
          help="Run it once where Claude Code is installed."
        >
          <CopyValue
            label="Command line for Claude Code"
            labelled={false}
            value={`claude mcp add --transport http refiroo ${status.url}`}
          />
        </SettingRow>
      </SettingsPanel>
    </SettingsGroup>
  );
}

function ClientsSection({ version, onNavigate }: { version: number; onNavigate: (route: RouteState) => void }) {
  const feed = useCursorFeed((cursor) => agentAccess.clients(cursor), [version]);

  return (
    <SettingsGroup
      stacked
      title="Agent clients"
      description="Systems whose assistant asks for a token. Make one with New agent client."
    >
      <SettingsPanel>
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && !feed.items.length ? (
          <Skeleton label="Loading agent clients" lines={3} />
        ) : !feed.items.length ? (
          <SettingsEmpty icon="api" hue={settingsHead("agent-access").hue}>
            No agent client yet. Create one for a system whose assistant should reach this instance.
          </SettingsEmpty>
        ) : (
          <>
            <SettingsTable label="Agent clients" columns={["Name", "Access", "Last used", { num: "Calls, 30 days" }]}>
              {feed.items.map((client) => (
                <ClientRow key={client.id} client={client} onNavigate={onNavigate} />
              ))}
            </SettingsTable>
            <LogFoot
              shown={feed.items.length}
              noun="agent clients"
              onMore={feed.hasMore && !feed.error ? feed.loadMore : undefined}
              loading={feed.loading}
            />
          </>
        )}
      </SettingsPanel>
    </SettingsGroup>
  );
}

function ClientRow({ client, onNavigate }: { client: AgentClient; onNavigate: (route: RouteState) => void }) {
  const route: RouteState = { kind: "settings", page: "clients", clientId: client.id };
  return (
    <tr>
      <th scope="row">
        <span className="settings-name-cell">
          <NameMark name={client.name} size={36} />
          <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
            {client.name}
          </RouteLink>
        </span>
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
      <td data-label="Last used" className="when" title={client.lastCallAt ? formatServerTime(client.lastCallAt) : ""}>
        {client.lastCallAt ? formatServerDayTime(client.lastCallAt) : "Never"}
      </td>
      <td data-label="Calls, 30 days" className="num">
        {count(client.calls30Days)}
      </td>
    </tr>
  );
}

function ApplicationsSection({ hue }: { hue: Hue }) {
  const feed = useCursorFeed((cursor) => agentAccess.applications(cursor), []);
  const [registering, setRegistering] = useState(false);
  const [blocking, setBlocking] = useState<AgentApplication>();
  const guard = useGuardedWrite();
  const { pending, error, setError } = guard;
  const registerRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  function change(application: AgentApplication, action: "block" | "restore") {
    return guard.run(async () => {
      await agentAccess[action](application.id);
      setBlocking(undefined);
      feed.reload();
      toast(
        action === "block"
          ? `${application.name} was blocked. Its sessions end on their next call.`
          : `${application.name} was restored. People may sign in with it again.`,
      );
    }, {});
  }

  return (
    <SettingsGroup
      stacked
      title="Assistants people sign in with"
      description="The name is what the assistant says about itself. Blocking ends its sessions on their next call."
      action={
        <button ref={registerRef} type="button" className="secondary" onClick={() => setRegistering(true)}>
          New assistant
        </button>
      }
    >
      <ActionNotices guard={guard} hideError={Boolean(blocking)} />
      <SettingsPanel>
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && !feed.items.length ? (
          <Skeleton label="Loading assistants" lines={3} />
        ) : !feed.items.length ? (
          <SettingsEmpty icon="bot" hue={hue}>
            No assistant has signed anyone in yet. One appears here when a person adds the address in their assistant,
            or when you register it.
          </SettingsEmpty>
        ) : (
          <>
            <SettingsTable
              label="Assistants people sign in with"
              columns={["Assistant", "Returns to", "Signed in now", "Last used", { hidden: "Actions" }]}
            >
              {feed.items.map((application) => (
                <tr key={application.id}>
                  <th scope="row">
                    <span className="settings-name-cell">
                      <SettingsTile icon="bot" hue={hue} size={32} />
                      {application.name}
                    </span>
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
                    {count(application.signedIn)} {plural(application.signedIn, "person", "people")}
                  </td>
                  <td
                    data-label="Last used"
                    className="when"
                    title={application.lastUsedAt ? formatServerTime(application.lastUsedAt) : ""}
                  >
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
            <LogFoot
              shown={feed.items.length}
              noun="assistants"
              onMore={feed.hasMore && !feed.error ? feed.loadMore : undefined}
              loading={feed.loading}
            />
          </>
        )}
      </SettingsPanel>
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
            No one can sign in with {blocking.name} any more, and its {count(blocking.signedIn)}{" "}
            {plural(blocking.signedIn, "session ends", "sessions end")} on the next call. You can restore it later; the
            sessions that ended stay ended.
          </p>
        </ConfirmDialog>
      )}
    </SettingsGroup>
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
      title="New assistant"
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
          <CancelButton disabled={pending} />
          <button className="primary" disabled={pending || !name.trim() || !redirectUris.length}>
            {pending ? "Adding…" : "Add assistant"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CallsSection() {
  const feed = useCursorFeed((cursor) => agentAccess.calls(cursor), []);
  return (
    <SettingsGroup
      stacked
      title="Calls"
      description="Every tool call an assistant made, newest first. Argument names are kept, never their values."
    >
      <SettingsPanel>
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && !feed.items.length ? (
          <Skeleton label="Loading calls" lines={4} />
        ) : !feed.items.length ? (
          <SettingsEmpty icon="bot" hue={settingsHead("agent-access").hue}>
            No call has been made yet.
          </SettingsEmpty>
        ) : (
          <>
            <SettingsTable label="Calls" columns={["When", "Who", "Through", "Tool", "Arguments", "Outcome"]}>
              {feed.items.map((call) => (
                <tr key={call.id}>
                  <th scope="row" className="when" title={formatServerTime(call.occurredAt)}>
                    {formatServerDayTime(call.occurredAt)}
                  </th>
                  <td data-label="Who">{call.principal}</td>
                  <td data-label="Through">{call.application ?? "Its own client"}</td>
                  <td data-label="Tool">
                    <code>{call.tool}</code>
                  </td>
                  <td data-label="Arguments">{call.arguments.length ? call.arguments.join(", ") : "None"}</td>
                  <td data-label="Outcome">
                    <StatusPill tone={OUTCOME_TONE[call.outcome] ?? "neutral"}>
                      {OUTCOME[call.outcome] ?? call.outcome}
                    </StatusPill>
                  </td>
                </tr>
              ))}
            </SettingsTable>
            <LogFoot
              shown={feed.items.length}
              noun="calls"
              onMore={feed.hasMore && !feed.error ? feed.loadMore : undefined}
              loading={feed.loading}
            />
          </>
        )}
      </SettingsPanel>
    </SettingsGroup>
  );
}
