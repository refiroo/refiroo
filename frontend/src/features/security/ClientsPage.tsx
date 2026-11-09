/**
 * Settings › Security › Clients (0.12 SP2, U8): the systems that call the API beside the selected
 * client (U-D10's list and detail), searched by name, active or deactivated, each with its access
 * and last token (D348). A client's page renames it, rotates its secret with an overlap (D352),
 * ends a previous secret (D351), deactivates or restores it (never deletes, D237), and lists its
 * secrets by their last four characters (D350), its access (roles and consumer APIs, D354), the
 * webhooks it created (D353) and its recent activity. A new secret is shown once.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { security } from "@/api/securityClient";
import { formatServerDate, formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Client, ClientWithSecret, RouteState, SettingsRoute } from "@/types";
import { ActorName } from "@/ui/ActorName";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { CatalogueWindow } from "@/ui/CatalogueWindow";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { CopyValue } from "@/ui/CopyValue";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RotateOverlapDialog } from "@/ui/RotateOverlapDialog";
import { RouteLink } from "@/ui/RouteLink";
import { SearchField } from "@/ui/SearchField";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { ShownOnceDialog } from "@/ui/ShownOnceDialog";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { readsChanges } from "@/features/changes/changeText";
import { GrantsSection, useWorkspaceLabels } from "./GrantsSection";
import { useCapabilities } from "@/features/settings/useSystem";
import { useHeldAnywhere } from "./permissions";
import { RecentActivity } from "./RecentActivity";
import { clientAccessLine, clientUseLine } from "./securityText";

type ClientsRoute = Extract<SettingsRoute, { page: "clients" }>;

const CLIENTS: ClientsRoute = { kind: "settings", page: "clients" };

/** A new secret, and whether it came with a new client or replaced earlier ones. */
export type Made = { client: ClientWithSecret; created: boolean; overlapHours?: number };

/** Clients read in a page of this size. */
const CATALOGUE_PAGE = 50;

export function ClientsPage({ route, onNavigate }: { route: ClientsRoute; onNavigate: (route: RouteState) => void }) {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(true);
  const [counts, setCounts] = useState<{ active?: number; deactivated?: number }>({});
  const [creating, setCreating] = useState(false);
  const [made, setMade] = useState<Made>();
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const q = useDebouncedValue(search.trim());
  const list = useCursorWindow<Client>(
    (selector) => security.clientPage({ q, active, ...selector, pageSize: CATALOGUE_PAGE }),
    [q, active],
  );
  const [countToken, setCountToken] = useState(0);

  useEffect(() => {
    let current = true;
    Promise.all([
      security.clientPage({ active: true, pageSize: 1, includeTotal: true }),
      security.clientPage({ active: false, pageSize: 1, includeTotal: true }),
    ]).then(
      ([on, off]) => current && setCounts({ active: on.totalCount, deactivated: off.totalCount }),
      () => undefined,
    );
    return () => {
      current = false;
    };
  }, [countToken]);

  function changed() {
    list.reload();
    setCountToken((token) => token + 1);
  }

  const catalogue = (
    <nav className="model-catalogue security-catalogue" aria-label="Clients">
      <section>
        <SearchField label="Search clients" placeholder="Name" value={search} onChange={setSearch} clearOnEscape />
        <div className="security-filters" role="group" aria-label="Show">
          <button type="button" className="security-filter" aria-pressed={active} onClick={() => setActive(true)}>
            Active{counts.active !== undefined && <span>{counts.active}</span>}
          </button>
          <button type="button" className="security-filter" aria-pressed={!active} onClick={() => setActive(false)}>
            Deactivated{counts.deactivated !== undefined && <span>{counts.deactivated}</span>}
          </button>
        </div>
        <CatalogueWindow
          list={list}
          label="Clients"
          noun={["client", "clients"]}
          pageSize={CATALOGUE_PAGE}
          loadingText="Loading clients…"
          emptyText={
            q
              ? `No ${active ? "active" : "deactivated"} client matches “${q}”.`
              : `No ${active ? "active" : "deactivated"} clients.`
          }
          entry={(client) => (
            <CatalogueEntry
              icon="api"
              title={client.name}
              pill={
                client.kind === "agent" ? (
                  <StatusPill tone="neutral" marker={false}>
                    Agent
                  </StatusPill>
                ) : undefined
              }
              subtitle={
                <>
                  {clientAccessLine(client)}
                  <span className="security-entry-use">{clientUseLine(client)}</span>
                </>
              }
              current={route.clientId === client.id}
              onSelect={() => onNavigate({ ...CLIENTS, clientId: client.id })}
            />
          )}
        />
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Security"
      title="Clients"
      description="The systems that call the API with a client ID and secret, what they may use and when they last obtained a token. A client is deactivated, never deleted, so history keeps its name."
      actions={
        <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
          <Icon name="plus" /> New client
        </button>
      }
    >
      <CatalogueLayout
        catalogue={catalogue}
        hasSelection={!!route.clientId}
        backLabel="All clients"
        onBack={() => onNavigate(CLIENTS)}
      >
        {route.clientId ? (
          <ClientDetail
            key={route.clientId}
            clientId={route.clientId}
            onNavigate={onNavigate}
            onChanged={changed}
            onSecret={(client, overlapHours) => setMade({ client, created: false, overlapHours })}
          />
        ) : (
          <div className="panel-state">Choose a client.</div>
        )}
      </CatalogueLayout>
      {creating && (
        <NewClientDialog
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(client) => {
            setCreating(false);
            list.reload();
            setCountToken((token) => token + 1);
            onNavigate({ ...CLIENTS, clientId: client.id });
            setMade({ client, created: true });
          }}
        />
      )}
      {made && <SecretDialog {...made} onClose={() => setMade(undefined)} />}
    </SettingsLayout>
  );
}

/** The secret just made, shown once with the client ID it goes with (D350, D352). */
export function SecretDialog({ client, created, overlapHours, onClose }: Made & { onClose: () => void }) {
  const previous = client.secrets.find((secret) => secret.id !== client.secretId && secret.expiresAt);
  return (
    <ShownOnceDialog
      title={created ? "Copy the client's secret" : `New secret for ${client.name}`}
      eyebrow={created ? `${client.name} was created` : "Client secret"}
      label="Client secret"
      value={client.secret}
      confirmLabel="I have copied it"
      onClose={onClose}
    >
      {{
        before: (
          <>
            <p>
              Copy it now. It is shown only once; afterwards only its last four characters are kept. The system using
              this client asks for tokens with the client ID and this secret.
            </p>
            <p className="webhook-secret">
              <CopyValue label="Client ID" value={client.id} />
            </p>
          </>
        ),
        after: !created && (
          <p className="admin-hint">
            {overlapHours === 0 || !previous?.expiresAt
              ? "The earlier secret stopped working now: the system using it is refused until it has this one."
              : `The previous secret keeps working until ${formatServerDayTime(previous.expiresAt)}, so the system using it can switch without a gap. End it sooner from the Secrets table.`}
          </p>
        ),
      }}
    </ShownOnceDialog>
  );
}

/** The New client dialog; an agent client (0.16 AG1) is made from Agent access and starts with no access too. */
export function NewClientDialog({
  kind = "api",
  onClose,
  onCreated,
}: {
  kind?: "api" | "agent";
  onClose: () => void;
  onCreated: (client: ClientWithSecret) => void;
}) {
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function create() {
    setPending(true);
    setError("");
    try {
      onCreated(await security.createClient({ name: name.trim(), kind }));
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal
      title={kind === "agent" ? "New agent client" : "New client"}
      eyebrow="Security"
      size="compact"
      busy={pending}
      dirty={!!name}
      onClose={onClose}
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <FormField
          label="Name"
          help={
            kind === "agent"
              ? "The system whose assistant will connect, as people will recognise it."
              : "The system that will call the API, as people will recognise it."
          }
        >
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
        <p className="admin-hint">
          It starts with no access: grant it {kind === "agent" ? "the Agent role" : "a role"} or a consumer API on its
          page.
        </p>
        {error && (
          <Notice tone="error" title="The client was not created">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !name.trim()}>
            {pending ? "Creating…" : "Create and show its secret"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ClientDetail({
  clientId,
  onNavigate,
  onChanged,
  onSecret,
}: {
  clientId: string;
  onNavigate: (route: RouteState) => void;
  onChanged: (client: Client) => void;
  onSecret: (client: ClientWithSecret, overlapHours: number) => void;
}) {
  const [client, setClient] = useState<Client>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [dialog, setDialog] = useState<"rename" | "rotate" | "deactivate">();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const renameRef = useRef<HTMLButtonElement>(null);
  const rotateRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();
  const held = useHeldAnywhere();

  useEffect(() => {
    let current = true;
    security.client(clientId).then(
      (loaded) => {
        if (!current) return;
        setClient(loaded);
        setLoadError("");
      },
      (cause) => current && setLoadError(errorMessage(cause)),
    );
    return () => {
      current = false;
    };
  }, [clientId, loadToken]);

  function stored(updated: Client, text?: string) {
    setClient(updated);
    onChanged(updated);
    if (text) toast(text);
  }

  /** A write; a stale version reloads and says so, any other refusal is shown as worded. */
  async function write(action: () => Promise<void>) {
    setPending(true);
    setActionError("");
    setConflict("");
    try {
      await action();
      setDialog(undefined);
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        setDialog(undefined);
        const current = await security.client(clientId).catch(() => undefined);
        if (current) stored(current);
        setConflict("This client changed while the page was open. It is shown as it is now; choose again.");
      } else {
        setActionError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  const { capabilities } = useCapabilities();

  if (loadError) return <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />;
  if (!client) return <div className="panel-state">Loading client…</div>;

  // What it changed in the workspaces this administrator reads (0.12 Z6, D345).
  const changes: RouteState = { kind: "changes", actorId: client.id, actorName: client.name };
  const webhooks =
    held?.some((group) => group.key === "integration-admin") && capabilities?.consumerSubscriptions.manageSubscriptions;

  return (
    <div className="model-editor-stack security-detail">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Client</p>
          <h2>{client.name}</h2>
          <p className="security-client-id">
            Client ID <CopyValue label="Client ID" value={client.id} labelled={false} />
          </p>
          <p>
            Created{" "}
            {client.createdBy && (
              <>
                <ActorName actor={client.createdBy} />{" "}
              </>
            )}
            {formatServerDate(client.createdAt)}
          </p>
          <div className="security-pills">
            {client.active ? (
              <StatusPill tone="success">Active</StatusPill>
            ) : (
              <StatusPill tone="neutral">Deactivated</StatusPill>
            )}
            {client.kind === "agent" && (
              <StatusPill tone="neutral" marker={false}>
                Agent
              </StatusPill>
            )}
            <StatusPill tone="neutral" marker={false}>
              {client.lastUsedAt ? `Last token ${formatServerDayTime(client.lastUsedAt)}` : "No token yet"}
            </StatusPill>
          </div>
        </div>
      </header>
      {conflict && (
        <Notice tone="warning" title="Not saved" focusOnMount>
          {conflict}
        </Notice>
      )}
      {actionError && !dialog && (
        <Notice tone="error" title="The action could not be completed">
          {actionError}
        </Notice>
      )}
      <div className="model-actions">
        <button ref={renameRef} className="secondary" disabled={pending} onClick={() => setDialog("rename")}>
          Rename…
        </button>
        <button ref={rotateRef} className="secondary" disabled={pending} onClick={() => setDialog("rotate")}>
          Rotate secret…
        </button>
        {client.active ? (
          <button className="danger-ghost" disabled={pending} onClick={() => setDialog("deactivate")}>
            Deactivate
          </button>
        ) : (
          <button
            className="secondary"
            disabled={pending}
            onClick={() =>
              void write(async () =>
                stored(
                  await security.updateClient(client.id, { expectedVersion: client.version, active: true }),
                  `${client.name} was restored and can obtain tokens again.`,
                ),
              )
            }
          >
            Restore
          </button>
        )}
        {readsChanges(held) && (
          <RouteLink className="secondary" href={routePath(changes)} onNavigate={() => onNavigate(changes)}>
            See changes
          </RouteLink>
        )}
      </div>
      <Secrets
        client={client}
        pending={pending}
        onEnd={(secretId) =>
          void write(async () =>
            stored(
              await security.endSecret(client.id, secretId),
              "The secret was ended. Only the newer one works now.",
            ),
          )
        }
      />
      <GrantsSection
        subject={{ principal: { kind: "client", id: client.id, name: client.name } }}
        title="Access"
        description="Roles let it use the management API; a consumer API grant lets it read that API in one workspace."
        load={(cursor) => security.grantsOf(client.id, cursor)}
        deps={[client.id]}
        onNavigate={onNavigate}
        onChanged={() =>
          void security.client(client.id).then(
            (current) => stored(current),
            () => undefined,
          )
        }
      />
      {webhooks && <ClientWebhooks client={client} onNavigate={onNavigate} />}
      <RecentActivity principal={client} />
      {dialog === "rename" && (
        <RenameDialog
          client={client}
          onClose={() => {
            setDialog(undefined);
            renameRef.current?.focus();
          }}
          onSaved={(updated) => {
            setDialog(undefined);
            stored(updated, "Renamed.");
            renameRef.current?.focus();
          }}
          onConflict={(current) => stored(current)}
        />
      )}
      {dialog === "rotate" && (
        <RotateOverlapDialog
          title={`Rotate the secret of ${client.name}`}
          eyebrow="Security"
          lead={
            client.active ? (
              "A new secret is made and shown once. Until the system using this client switches to it, the current secret keeps working for:"
            ) : (
              <>
                A new secret is made and shown once. {client.name} is deactivated, so the new secret takes effect when
                you restore it. The current secret keeps working after that only for the time chosen here, counted from
                now:
              </>
            )
          }
          stopNowHint="For a secret that leaked: the system using it is refused until it has the new one."
          submitLabel="Make a new secret"
          pendingLabel="Making…"
          errorTitle="No new secret was made"
          pending={pending}
          error={actionError}
          onClose={() => {
            setDialog(undefined);
            setActionError("");
            rotateRef.current?.focus();
          }}
          onRotate={(overlapHours) =>
            void write(async () => {
              const rotated = await security.rotateSecret(client.id, {
                expectedVersion: client.version,
                overlapHours,
              });
              stored(rotated);
              onSecret(rotated, overlapHours);
            })
          }
        />
      )}
      {dialog === "deactivate" && (
        <ConfirmDialog
          title={`Deactivate ${client.name}?`}
          confirmLabel="Deactivate"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setDialog(undefined);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () =>
              stored(
                await security.updateClient(client.id, { expectedVersion: client.version, active: false }),
                `${client.name} was deactivated. Its tokens are refused from their next request.`,
              ),
            )
          }
        >
          <p>
            {client.name} obtains no more tokens, and the tokens it holds are refused from their next request. Its
            access and secrets stay, and history keeps its name. You can restore it later.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

/** The client's valid secrets by their last four characters; End now on one with an end (D351). */
function Secrets({ client, pending, onEnd }: { client: Client; pending: boolean; onEnd: (secretId: string) => void }) {
  const newest = client.secrets.length ? client.secrets[client.secrets.length - 1] : undefined;
  return (
    <Section title="Secrets">
      {!client.secrets.length ? (
        <p className="admin-hint">No valid secret: rotate to make one.</p>
      ) : (
        <SettingsTable
          label="Secrets"
          columns={["Secret", "Created", "Valid until", "Last used", { hidden: "Actions" }]}
        >
          {[...client.secrets].reverse().map((secret) => (
            <tr key={secret.id}>
              <th scope="row" className="mono">
                {secret.hint ? `…${secret.hint}` : "—"}
              </th>
              <td data-label="Created">{formatServerDayTime(secret.createdAt)}</td>
              <td data-label="Valid until">
                {secret.expiresAt ? (
                  <StatusPill tone="warning" marker={false}>
                    {formatServerDayTime(secret.expiresAt)}
                  </StatusPill>
                ) : (
                  "No end"
                )}
              </td>
              <td data-label="Last used">{secret.lastUsedAt ? formatServerDayTime(secret.lastUsedAt) : "Not yet"}</td>
              <td className="grant-action">
                {secret.expiresAt && secret.id !== newest?.id && (
                  <button
                    type="button"
                    className="ghost"
                    disabled={pending}
                    aria-label={`End the secret ending ${secret.hint ?? ""} now`}
                    onClick={() => onEnd(secret.id)}
                  >
                    End now
                  </button>
                )}
              </td>
            </tr>
          ))}
        </SettingsTable>
      )}
    </Section>
  );
}

function RenameDialog({
  client,
  onClose,
  onSaved,
  onConflict,
}: {
  client: Client;
  onClose: () => void;
  onSaved: (client: Client) => void;
  onConflict: (current: Client) => void;
}) {
  const [name, setName] = useState(client.name);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const changed = name.trim() !== client.name;

  async function save() {
    setPending(true);
    setError("");
    try {
      onSaved(await security.updateClient(client.id, { expectedVersion: client.version, name: name.trim() }));
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        const current = await security.client(client.id).catch(() => undefined);
        if (current) onConflict(current);
        setError("Someone changed this client while you were editing. Save again to replace their change with yours.");
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={`Rename ${client.name}`}
      eyebrow="Client"
      size="compact"
      busy={pending}
      dirty={changed}
      onClose={onClose}
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <FormField label="Name">
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
        <p className="admin-hint">The client ID does not change, so the system using it needs nothing new.</p>
        {error && (
          <Notice tone="error" title="Not saved">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !changed || !name.trim()}>
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** The webhooks the client created, in the workspaces the caller administers (D353). */
function ClientWebhooks({ client, onNavigate }: { client: Client; onNavigate: (route: RouteState) => void }) {
  const feed = useCursorFeed((cursor) => security.subscriptionsOf(client.id, cursor), [client.id]);
  const labels = useWorkspaceLabels();
  return (
    <Section title="Webhooks it created">
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : !feed.items.length ? (
        <p className="admin-hint">{feed.loading ? "Loading webhooks…" : "It created no webhook you administer."}</p>
      ) : (
        <SettingsTable label="Webhooks it created" columns={["Webhook", "Workspace", "Consumer API", "State"]}>
          {feed.items.map((subscription) => {
            const route: SettingsRoute = { kind: "settings", page: "webhooks", subscriptionId: subscription.id };
            return (
              <tr key={subscription.id}>
                <th scope="row">
                  <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
                    {subscription.name}
                  </RouteLink>
                </th>
                <td data-label="Workspace">{labels.get(subscription.workspaceKey) ?? subscription.workspaceKey}</td>
                <td data-label="Consumer API">{subscription.consumerApi}</td>
                <td data-label="State">
                  <StatusPill tone={subscription.status === "active" ? "success" : "warning"}>
                    {subscription.status === "active" ? "Active" : "Suspended"}
                  </StatusPill>
                </td>
              </tr>
            );
          })}
        </SettingsTable>
      )}
      {feed.hasMore && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more webhooks
        </button>
      )}
    </Section>
  );
}
