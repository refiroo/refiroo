/**
 * Settings › Security › Clients (0.12 SP2, U8; 0.17 ST1): the systems that call the API as a full-width
 * list, searched by name, active or deactivated, each with its access and last token (D348); a row opens
 * the client as a page of its own (PP-D61). A client's page renames it in place, rotates its secret with an overlap (D352),
 * ends a previous secret (D351), deactivates or restores it (never deletes, D237), and lists its
 * secrets by their last four characters (D350), its access (roles and consumer APIs, D354), the
 * webhooks it created (D353) and its recent activity. A new secret is shown once.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { security } from "@/api/securityClient";
import { formatServerDate, formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Hue } from "@/model/hues";
import type { Client, ClientWithSecret, RouteState, SettingsRoute } from "@/types";
import { ActorName } from "@/ui/ActorName";
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
import { EntityList } from "@/ui/EntityList";
import { SettingsLayout } from "@/ui/SettingsLayout";
import {
  FilterChip,
  hueOf,
  ItemHeader,
  LogFoot,
  NameMark,
  SettingsEmpty,
  SettingsGroup,
  SettingsPanel,
  SettingsTools,
} from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { ShownOnceDialog } from "@/ui/ShownOnceDialog";
import { StatusPill } from "@/ui/StatusPill";
import { TextInPlace } from "@/ui/TextInPlace";
import { useToast } from "@/ui/Toast";
import { Trail } from "@/ui/Trail";
import { ActionMenu, type ActionMenuItem } from "@/ui/ActionMenu";
import { settingsHead } from "@/ui/settingsNavigation";
import { readsChanges } from "@/ui/changeText";
import { GrantsSection, useWorkspaceLabels } from "./GrantsSection";
import { useCapabilities } from "@/state/useSystem";
import { useHeldAnywhere } from "@/state/permissions";
import { RecentActivity } from "./RecentActivity";
import { clientAccessLine, clientUseLine } from "./securityText";

type ClientsRoute = Extract<SettingsRoute, { page: "clients" }>;

const CLIENTS: ClientsRoute = { kind: "settings", page: "clients" };

/** A new secret, and whether it came with a new client or replaced earlier ones. */
export type Made = { client: ClientWithSecret; created: boolean; overlapHours?: number };

/** Clients read in a page of this size. */
const LIST_PAGE = 50;

export function ClientsPage({ route, onNavigate }: { route: ClientsRoute; onNavigate: (route: RouteState) => void }) {
  const [creating, setCreating] = useState(false);
  const [made, setMade] = useState<Made>();
  const newButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <>
      {route.clientId ? (
        <ClientDetail
          key={route.clientId}
          clientId={route.clientId}
          onNavigate={onNavigate}
          onSecret={(client, overlapHours) => setMade({ client, created: false, overlapHours })}
        />
      ) : (
        <ClientList newButtonRef={newButtonRef} onNew={() => setCreating(true)} onNavigate={onNavigate} />
      )}
      {creating && (
        <NewClientDialog
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(client) => {
            setCreating(false);
            onNavigate({ ...CLIENTS, clientId: client.id });
            setMade({ client, created: true });
          }}
        />
      )}
      {made && <SecretDialog {...made} onClose={() => setMade(undefined)} />}
    </>
  );
}

/** The list a client is chosen from: search, Active or Deactivated with their counts, and the rows. */
function ClientList({
  newButtonRef,
  onNew,
  onNavigate,
}: {
  newButtonRef: React.RefObject<HTMLButtonElement | null>;
  onNew: () => void;
  onNavigate: (route: RouteState) => void;
}) {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(true);
  const [counts, setCounts] = useState<{ active?: number; deactivated?: number }>({});
  const q = useDebouncedValue(search.trim());
  const feed = useCursorFeed<Client>(
    (cursor) => security.clientPage({ q, active, cursor, pageSize: LIST_PAGE }),
    [q, active],
  );
  const head = settingsHead("clients");

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
  }, []);

  const total = q ? undefined : active ? counts.active : counts.deactivated;
  const shown = feed.items.length;
  const count = total ?? shown;
  return (
    <SettingsLayout
      {...head}
      title="Clients"
      description="The systems that call the API with a client ID and secret, what they may use and when they last obtained a token. A client is deactivated, never deleted, so history keeps its name."
      actions={
        <button ref={newButtonRef} className="primary" onClick={onNew}>
          <Icon name="plus" /> New client
        </button>
      }
    >
      <SettingsTools
        count={
          feed.loading && !shown
            ? undefined
            : `${count}${total === undefined && feed.hasMore ? "+" : ""} ${count === 1 ? "client" : "clients"}`
        }
      >
        <SearchField label="Search clients" placeholder="Name" value={search} onChange={setSearch} clearOnEscape />
        <span className="filter-chips" role="group" aria-label="Show">
          <FilterChip selected={active} onSelect={() => setActive(true)}>
            Active{counts.active !== undefined && ` · ${counts.active}`}
          </FilterChip>
          <FilterChip selected={!active} onSelect={() => setActive(false)}>
            Deactivated{counts.deactivated !== undefined && ` · ${counts.deactivated}`}
          </FilterChip>
        </span>
      </SettingsTools>
      <SettingsPanel>
        <EntityList
          label="clients"
          statusTrack="6rem"
          groups={[
            {
              key: "clients",
              title: active ? "Active clients" : "Deactivated clients",
              count,
              loading: feed.loading && !shown,
              error: feed.error && !shown ? feed.error : undefined,
              onRetry: feed.retry,
              onEnd: feed.hasMore ? feed.loadMore : undefined,
              loadingMore: feed.loading && shown > 0,
              rows: feed.items.map((client) => ({
                key: client.id,
                title: client.name,
                subtitle: clientUseLine(client),
                lead: <NameMark name={client.name} />,
                facts: [{ label: "Access", value: clientAccessLine(client), width: 46 }],
                pill:
                  client.kind === "agent" ? (
                    <StatusPill tone="neutral" marker={false}>
                      Agent
                    </StatusPill>
                  ) : undefined,
                onOpen: () => onNavigate({ ...CLIENTS, clientId: client.id }),
              })),
            },
          ]}
          empty={
            q
              ? `No ${active ? "active" : "deactivated"} client matches “${q}”.`
              : `No ${active ? "active" : "deactivated"} clients.`
          }
        />
      </SettingsPanel>
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
      eyebrow="Connections"
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
            {pending ? "Adding…" : kind === "agent" ? "Add agent client" : "Add client"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ClientDetail({
  clientId,
  onNavigate,
  onSecret,
}: {
  clientId: string;
  onNavigate: (route: RouteState) => void;
  onSecret: (client: ClientWithSecret, overlapHours: number) => void;
}) {
  const [client, setClient] = useState<Client>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [dialog, setDialog] = useState<"rotate" | "deactivate">();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
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
    if (text) toast(text);
  }

  /** The name changed in place: a stale version reloads and says so; Undo puts the old name back against the new version. */
  async function renameClient(name: string) {
    if (!client) return;
    try {
      const updated = await security.updateClient(client.id, { expectedVersion: client.version, name });
      stored(updated);
      return async () => {
        stored(await security.updateClient(updated.id, { expectedVersion: updated.version, name: client.name }));
      };
    } catch (cause) {
      if (!isApiError(cause, "VERSION_CONFLICT")) throw cause;
      const current = await security.client(client.id).catch(() => undefined);
      if (current) stored(current);
      throw new Error(
        "Someone changed this client while you were editing. It is shown as it is now; change it again.",
        {
          cause,
        },
      );
    }
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

  const head = settingsHead("clients");
  const trail = <Trail back={{ label: "Clients", onClick: () => onNavigate(CLIENTS), href: routePath(CLIENTS) }} />;
  if (loadError)
    return (
      <SettingsLayout trail={trail} title="Client">
        <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />
      </SettingsLayout>
    );
  if (!client)
    return (
      <SettingsLayout trail={trail} title="Client">
        <Skeleton label="Loading client" lines={4} />
      </SettingsLayout>
    );

  // What it changed in the workspaces this administrator reads (0.12 Z6, D345).
  const changes: RouteState = { kind: "changes", actorId: client.id, actorName: client.name };
  const webhooks =
    held?.some((group) => group.key === "integration-admin") && capabilities?.consumerSubscriptions.manageSubscriptions;

  function restore(target: Client) {
    void write(async () =>
      stored(
        await security.updateClient(target.id, { expectedVersion: target.version, active: true }),
        `${target.name} was restored and can obtain tokens again.`,
      ),
    );
  }

  // Two actions show; the rest are in the ⋯ menu, what cannot be undone last (PP-D63).
  const menu: ActionMenuItem[] = [
    ...(readsChanges(held)
      ? [{ id: "changes", label: "See changes", onAction: () => onNavigate(changes) } satisfies ActionMenuItem]
      : []),
    ...(client.active
      ? [
          {
            id: "deactivate",
            label: "Deactivate",
            tone: "danger",
            disabled: pending,
            onAction: () => setDialog("deactivate"),
          } satisfies ActionMenuItem,
        ]
      : []),
  ];

  return (
    <SettingsLayout
      trail={trail}
      header={
        <ItemHeader
          hue={hueOf(client.name)}
          lead={<NameMark name={client.name} size={64} />}
          title={
            <TextInPlace
              heading
              headingLevel={1}
              value={client.name}
              label="Name"
              maxLength={200}
              savedText="Renamed."
              onSave={renameClient}
            />
          }
          meta={
            <>
              <span className="security-client-id">
                Client ID <CopyValue label="Client ID" value={client.id} labelled={false} />
              </span>
              <span>
                Created{" "}
                {client.createdBy && (
                  <>
                    <ActorName actor={client.createdBy} />{" "}
                  </>
                )}
                {formatServerDate(client.createdAt)}
              </span>
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
            </>
          }
          actions={
            <>
              <button ref={rotateRef} className="secondary" disabled={pending} onClick={() => setDialog("rotate")}>
                Rotate secret…
              </button>
              {!client.active && (
                <button className="secondary" disabled={pending} onClick={() => restore(client)}>
                  Restore
                </button>
              )}
              {menu.length > 0 && <ActionMenu label="More actions" items={menu} />}
            </>
          }
        />
      }
    >
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
      <Secrets
        client={client}
        hue={head.hue}
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
        hue={head.hue}
        onChanged={() =>
          void security.client(client.id).then(
            (current) => stored(current),
            () => undefined,
          )
        }
      />
      {webhooks && <ClientWebhooks client={client} hue={head.hue} onNavigate={onNavigate} />}
      <RecentActivity principal={client} />
      {dialog === "rotate" && (
        <RotateOverlapDialog
          title={`Rotate the secret of ${client.name}`}
          eyebrow="Connections"
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
          submitLabel="Rotate secret"
          pendingLabel="Rotating…"
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
    </SettingsLayout>
  );
}

/** The client's valid secrets by their last four characters; End now on one with an end (D351). */
function Secrets({
  client,
  hue,
  pending,
  onEnd,
}: {
  client: Client;
  hue: Hue;
  pending: boolean;
  onEnd: (secretId: string) => void;
}) {
  const newest = client.secrets.length ? client.secrets[client.secrets.length - 1] : undefined;
  return (
    <SettingsGroup
      stacked
      title="Secrets"
      description="The valid secrets by their last four characters. A secret is shown once, when it is made."
    >
      <SettingsPanel>
        {!client.secrets.length ? (
          <SettingsEmpty icon="key" hue={hue}>
            No valid secret: rotate to make one.
          </SettingsEmpty>
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
                <td className="when" data-label="Created" title={formatServerTime(secret.createdAt)}>
                  {formatServerDayTime(secret.createdAt)}
                </td>
                <td data-label="Valid until">
                  {secret.expiresAt ? (
                    <StatusPill tone="warning" marker={false}>
                      {formatServerDayTime(secret.expiresAt)}
                    </StatusPill>
                  ) : (
                    "No end"
                  )}
                </td>
                <td
                  className="when"
                  data-label="Last used"
                  title={secret.lastUsedAt ? formatServerTime(secret.lastUsedAt) : undefined}
                >
                  {secret.lastUsedAt ? formatServerDayTime(secret.lastUsedAt) : "Not yet"}
                </td>
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
      </SettingsPanel>
    </SettingsGroup>
  );
}

/** The webhooks the client created, in the workspaces the caller administers (D353). */
function ClientWebhooks({
  client,
  hue,
  onNavigate,
}: {
  client: Client;
  hue: Hue;
  onNavigate: (route: RouteState) => void;
}) {
  const feed = useCursorFeed((cursor) => security.subscriptionsOf(client.id, cursor), [client.id]);
  const labels = useWorkspaceLabels();
  return (
    <SettingsGroup
      stacked
      title="Webhooks it created"
      description="The webhooks this client made, in the workspaces you administer."
    >
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : !feed.items.length ? (
        feed.loading ? (
          <Skeleton label="Loading webhooks" lines={2} />
        ) : (
          <SettingsPanel>
            <SettingsEmpty icon="webhook" hue={hue}>
              It created no webhook you administer.
            </SettingsEmpty>
          </SettingsPanel>
        )
      ) : (
        <SettingsPanel>
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
          {feed.hasMore && (
            <LogFoot shown={feed.items.length} noun="webhooks" onMore={feed.loadMore} loading={feed.loading} />
          )}
        </SettingsPanel>
      )}
    </SettingsGroup>
  );
}
