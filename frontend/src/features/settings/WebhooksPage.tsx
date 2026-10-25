/**
 * Settings › Integration › Webhooks (Track U U5): webhook subscriptions to a consumer API's events,
 * newest first, beside the selected one (U-D10's list and detail). The detail says whether delivery
 * is going, why a subscription is suspended and what fixes it, and edits, suspends, resumes and
 * deletes it; a new subscription's signing key is shown once. Every write carries the version it
 * was based on; a conflict reloads and says so. With subscriptions off (`CONSUMER_SUBSCRIPTIONS_ENABLED`)
 * every route answers 404, so the page reads nothing else and says how to turn them on.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { routePath } from "@/routing/routes";
import type {
  ConsumerApiDefinition,
  DeliveryError,
  EngineModel,
  RouteState,
  SettingsRoute,
  Subscription,
  SubscriptionFinding,
} from "@/types";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { CopyValue } from "@/ui/CopyValue";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { ShownOnceDialog } from "@/ui/ShownOnceDialog";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { useToast } from "@/ui/Toast";
import { count } from "./limits";
import { useCapabilities } from "./useSystem";
import { useHeldAnywhere } from "@/features/security/permissions";
import { WebhookDeliveries } from "./WebhookDeliveries";
import { WebhookDialog } from "./WebhookDialog";
import { subscribable, useConsumerDefinitions } from "./consumerDefinitions";
import {
  CONTENT,
  FIX,
  FORMAT,
  REASON,
  deliveryErrorText,
  eventDeclaration,
  requestsLabel,
  subscriptionState,
  urlName,
} from "./webhookText";

type WebhooksRoute = Extract<SettingsRoute, { page: "webhooks" }>;

const WEBHOOKS: WebhooksRoute = { kind: "settings", page: "webhooks" };

export function WebhooksPage({
  route,
  model,
  onNavigate,
}: {
  route: WebhooksRoute;
  model: EngineModel;
  onNavigate: (route: RouteState) => void;
}) {
  const { capabilities, error: capabilitiesError, retry: retryCapabilities } = useCapabilities();
  const consumer = useConsumerDefinitions(model);
  const subscriptions = capabilities?.consumerSubscriptions;
  const [creating, setCreating] = useState(false);
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const canCreate = subscribable(consumer.definitions ?? []).length > 0;
  const error = capabilitiesError || consumer.error;
  const retry = capabilitiesError ? retryCapabilities : consumer.retry;

  return (
    <SettingsLayout
      eyebrow="Integration"
      title="Webhooks"
      description="Subscriptions that send a consumer API's events to a receiver's URL as they happen, signed with a key shown once when the subscription is created."
      actions={
        subscriptions?.manageSubscriptions && (
          <button ref={newButtonRef} className="primary" disabled={!canCreate} onClick={() => setCreating(true)}>
            <Icon name="plus" /> New webhook
          </button>
        )
      }
    >
      {error ? (
        <InlineError message={error} onRetry={retry} />
      ) : !subscriptions || !consumer.definitions ? (
        <Skeleton label="Loading webhooks" lines={6} />
      ) : !subscriptions.manageSubscriptions ? (
        <EmptyState
          action={
            <button
              type="button"
              className="secondary"
              onClick={() => onNavigate({ kind: "settings", page: "deployment" })}
            >
              Open Deployment
            </button>
          }
        >
          Webhooks are off in this deployment. The operator turns them on with <code>{subscriptions.setting}=true</code>
          , which also needs <code>CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY</code>, and restarts the engine.
        </EmptyState>
      ) : (
        <Subscriptions
          route={route}
          model={model}
          definitions={consumer.definitions}
          retentionDays={subscriptions.logRetentionDays}
          batchLimit={subscriptions.delivery.maxEventsPerBatch}
          canCreate={canCreate}
          creating={creating}
          onCreateClosed={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onNavigate={onNavigate}
        />
      )}
    </SettingsLayout>
  );
}

function Subscriptions({
  route,
  model,
  definitions,
  retentionDays,
  batchLimit,
  canCreate,
  creating,
  onCreateClosed,
  onNavigate,
}: {
  route: WebhooksRoute;
  model: EngineModel;
  definitions: ConsumerApiDefinition[];
  retentionDays: number;
  /** The most events a subscription may batch (capabilities). */
  batchLimit: number;
  canCreate: boolean;
  creating: boolean;
  onCreateClosed: () => void;
  onNavigate: (route: RouteState) => void;
}) {
  const feed = useCursorFeed((cursor) => api.subscriptions({ cursor }), []);
  const toast = useToast();
  const [created, setCreated] = useState<Subscription>();
  const select = (id: string) => onNavigate({ ...WEBHOOKS, subscriptionId: id });

  const catalogue = (
    <nav className="model-catalogue" aria-label="Webhook catalogue">
      <section>
        <h2 className="nav-label">
          Subscriptions <span>{feed.items.length}</span>
        </h2>
        {feed.items.map((subscription) => {
          const state = subscriptionState(subscription);
          return (
            <CatalogueEntry
              key={subscription.id}
              icon="webhook"
              title={subscription.name}
              subtitle={<Breakable text={urlName(subscription.url)} />}
              current={route.subscriptionId === subscription.id}
              onSelect={() => select(subscription.id)}
              pill={<StatusPill tone={state.tone}>{state.label}</StatusPill>}
            />
          );
        })}
        {feed.loading && !feed.items.length && <p className="explorer-empty">Loading subscriptions…</p>}
        {feed.error && (
          <div className="catalogue-error">
            <InlineError message={feed.error} onRetry={feed.retry} />
          </div>
        )}
        {feed.hasMore && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more subscriptions
          </button>
        )}
      </section>
    </nav>
  );

  const empty = !feed.loading && !feed.error && feed.items.length === 0;

  return (
    <>
      {!canCreate && (
        <Notice>
          The active model release declares no consumer API with events, so there is nothing to subscribe to. Events are
          declared in the model, on a consumer API.
        </Notice>
      )}
      {empty && !route.subscriptionId ? (
        <EmptyState>
          No webhooks yet. A webhook sends a consumer API's events to a receiver; create one with New webhook, or with{" "}
          <code>POST /api/v1/consumer-subscriptions</code>.
        </EmptyState>
      ) : (
        <CatalogueLayout
          catalogue={catalogue}
          hasSelection={!!route.subscriptionId}
          backLabel="All webhooks"
          onBack={() => onNavigate(WEBHOOKS)}
        >
          {route.subscriptionId ? (
            <SubscriptionDetail
              key={route.subscriptionId}
              route={{ ...route, subscriptionId: route.subscriptionId }}
              model={model}
              definitions={definitions}
              retentionDays={retentionDays}
              batchLimit={batchLimit}
              onNavigate={onNavigate}
              onChanged={(subscription) =>
                feed.setItems((items) => items.map((item) => (item.id === subscription.id ? subscription : item)))
              }
              onDeleted={(subscription) => {
                toast(`The webhook ${subscription.name} was deleted.`);
                feed.reload();
                onNavigate(WEBHOOKS);
              }}
            />
          ) : (
            <div className="panel-state">Choose a subscription.</div>
          )}
        </CatalogueLayout>
      )}
      {creating && (
        <WebhookDialog
          model={model}
          definitions={definitions}
          batchLimit={batchLimit}
          onClose={onCreateClosed}
          onSaved={(subscription) => {
            onCreateClosed();
            setCreated(subscription);
            feed.reload();
            select(subscription.id);
          }}
        />
      )}
      {created?.signingSecret && <SigningKeyDialog subscription={created} onClose={() => setCreated(undefined)} />}
    </>
  );
}

/** An address that wraps only after a slash or a dot, never inside a word. */
/** Who created a webhook (0.12 Z3, D310; SP2, D353): a link to their Security page, or the name. */
function WebhookOwner({
  owner,
  linked,
  onNavigate,
}: {
  owner: Subscription["owner"];
  linked: boolean;
  onNavigate: (route: RouteState) => void;
}) {
  if (!owner) return <>—</>;
  if (!linked) return <>{owner.name}</>;
  const route: RouteState =
    owner.kind === "user"
      ? { kind: "settings", page: "people", userId: owner.id }
      : { kind: "settings", page: "clients", clientId: owner.id };
  return (
    <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
      {owner.name}
    </RouteLink>
  );
}

function Breakable({ text }: { text: string }) {
  return text.split(/(?<=[/.])/).map((part, index) => (
    <span key={index}>
      {index > 0 && <wbr />}
      {part}
    </span>
  ));
}

/** The signing key, once: no read returns it again. */
function SigningKeyDialog({ subscription, onClose }: { subscription: Subscription; onClose: () => void }) {
  return (
    <ShownOnceDialog
      title="Keep the signing key"
      eyebrow="Webhook created"
      label="Signing key"
      value={subscription.signingSecret ?? ""}
      confirmLabel="I have stored the key"
      onClose={onClose}
    >
      {{
        before: (
          <p>
            Every delivery to <code>{subscription.url}</code> is signed with this key (<code>RDM-Signature</code>).
            Store it with the receiver now: it is not shown again.
          </p>
        ),
      }}
    </ShownOnceDialog>
  );
}

function SubscriptionDetail({
  route,
  model,
  definitions,
  retentionDays,
  batchLimit,
  onNavigate,
  onChanged,
  onDeleted,
}: {
  route: WebhooksRoute & { subscriptionId: string };
  model: EngineModel;
  definitions: ConsumerApiDefinition[];
  retentionDays?: number;
  batchLimit?: number;
  onNavigate: (route: RouteState) => void;
  onChanged: (subscription: Subscription) => void;
  onDeleted: (subscription: Subscription) => void;
}) {
  const { subscriptionId } = route;
  const [subscription, setSubscription] = useState<Subscription>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [editing, setEditing] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const toast = useToast();
  // A webhook's owner links to their Security page for whoever may open it (D353).
  const securityAdmin = useHeldAnywhere()?.some((group) => group.key === "security-admin");
  const editRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let active = true;
    api
      .subscription(subscriptionId)
      .then((item) => {
        if (!active) return;
        setSubscription(item);
        setLoadError("");
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [subscriptionId, loadToken]);

  async function reload() {
    const current = await api.subscription(subscriptionId);
    setSubscription(current);
    onChanged(current);
    return current;
  }

  function stored(updated: Subscription, text: string) {
    setSubscription(updated);
    onChanged(updated);
    toast(text);
  }

  /** A write with the version read; a stale one reloads and says so. */
  async function write(action: () => Promise<void>) {
    setPending(true);
    setActionError("");
    setConflict("");
    try {
      await action();
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        setDeleting(false);
        setResuming(false);
        await reload().catch(() => undefined);
        setConflict(
          "This subscription changed while the page was open. It is shown as it is now; review it and choose again.",
        );
      } else {
        setActionError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  if (loadError) return <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />;
  if (!subscription) return <div className="panel-state">Loading subscription…</div>;
  const state = subscriptionState(subscription);
  const definition = definitions.find((item) => item.key === subscription.consumerApi);
  const consumerApisRoute: SettingsRoute = { kind: "settings", page: "consumer-apis" };
  const pendingDelivery = subscription.delivery.pending;

  const deliveryItems: DescriptionItem[] = [
    {
      term: "Last delivered",
      value: subscription.delivery.lastDeliveredAt
        ? formatServerTime(subscription.delivery.lastDeliveredAt)
        : "Not yet",
    },
    { term: "Acknowledged through", value: `Feed position ${count(subscription.acknowledgedThrough)}` },
  ];
  if (pendingDelivery)
    deliveryItems.push(
      { term: "Failing since", value: formatServerTime(pendingDelivery.failingSince) },
      { term: "Attempts", value: count(pendingDelivery.attempts) },
      { term: "Last error", value: deliveryErrorText(pendingDelivery.lastError) },
      { term: "Last attempt", value: formatServerTime(pendingDelivery.lastAttemptAt) },
      {
        term: "Next attempt",
        value: pendingDelivery.nextAttemptAt ? formatServerTime(pendingDelivery.nextAttemptAt) : "None scheduled",
      },
      { term: "Delivery ID", value: <code>{pendingDelivery.deliveryId}</code> },
    );

  const filters = Object.entries(subscription.filters);
  const items: DescriptionItem[] = [
    { term: "Name", value: subscription.name },
    { term: "URL", value: <CopyValue label="URL" value={subscription.url} labelled={false} /> },
    {
      term: "Consumer API",
      value: (
        <RouteLink href={routePath(consumerApisRoute)} onNavigate={() => onNavigate(consumerApisRoute)}>
          {definition?.name ?? subscription.consumerApi} · v{subscription.contractVersion}
        </RouteLink>
      ),
    },
    { term: "Workspace", value: <code>{subscription.workspaceKey}</code> },
    {
      term: "Events",
      value: (
        <ul className="webhook-event-list">
          {subscription.events.map((key) => {
            const event = definition?.operations.events?.custom.find((item) => item.key === key);
            return (
              <li key={key}>
                <code>{key}</code>
                <small>{event ? eventDeclaration(model, event) : "Not declared by the active release."}</small>
              </li>
            );
          })}
        </ul>
      ),
    },
    {
      term: "Filters",
      value: filters.length ? (
        <ul className="webhook-event-list">
          {filters.map(([name, list]) => (
            <li key={name}>
              <code>{name}</code> {list.join(", ")}
            </li>
          ))}
        </ul>
      ) : (
        "None: every event of the subscribed kinds"
      ),
    },
    { term: "Requests", value: requestsLabel(subscription.maxEventsPerBatch) },
    { term: "Content", value: CONTENT[subscription.payload] },
    { term: "Format", value: FORMAT[subscription.format] },
    { term: "Signing key created", value: formatServerTime(subscription.signingKeyCreatedAt) },
    { term: "Created", value: formatServerTime(subscription.createdAt) },
    {
      term: "Created by",
      value: <WebhookOwner owner={subscription.owner} linked={!!securityAdmin} onNavigate={onNavigate} />,
    },
    { term: "Last changed", value: formatServerTime(subscription.updatedAt) },
    { term: "ID", value: <CopyValue label="Subscription ID" value={subscription.id} labelled={false} /> },
  ];

  const header = (
    <div className="webhook-head">
      <header className="model-detail-header">
        <div>
          <h2>{subscription.name}</h2>
          <p>
            <Breakable text={urlName(subscription.url)} /> · {definition?.name ?? subscription.consumerApi} ·{" "}
            {subscription.workspaceKey}
          </p>
        </div>
        <StatusPill tone={state.tone}>{state.label}</StatusPill>
      </header>
      {subscription.suspension && <SuspensionNotice suspension={subscription.suspension} />}
    </div>
  );

  const configuration = (
    <div className="model-editor-stack webhook-panel">
      {conflict && (
        <Notice tone="warning" title="Not saved" focusOnMount>
          {conflict}
        </Notice>
      )}
      {actionError && !resuming && !deleting && (
        <Notice tone="error" title="The action could not be completed">
          {actionError}
        </Notice>
      )}
      <div className="model-actions">
        <button ref={editRef} className="secondary" disabled={pending} onClick={() => setEditing(true)}>
          Edit…
        </button>
        {subscription.status === "active" ? (
          <button
            className="secondary"
            disabled={pending}
            onClick={() =>
              void write(async () =>
                stored(
                  await api.suspendSubscription(subscription.id, subscription.version),
                  "Webhook suspended. Nothing is sent until it is resumed.",
                ),
              )
            }
          >
            Suspend
          </button>
        ) : (
          <button
            className="secondary"
            disabled={pending}
            onClick={() => {
              setActionError("");
              setResuming(true);
            }}
          >
            Resume…
          </button>
        )}
        <button
          className="danger-ghost"
          disabled={pending}
          onClick={() => {
            setActionError("");
            setDeleting(true);
          }}
        >
          Delete…
        </button>
      </div>
      <section className="webhook-section" aria-labelledby="webhook-delivery">
        <h3 id="webhook-delivery">Delivery</h3>
        {pendingDelivery && (
          <p className="admin-hint">
            A batch is failing and is retried with backoff until the receiver acknowledges it, or for 24 hours from its
            first failure; then the subscription is suspended.
          </p>
        )}
        <DescriptionList className="compact" items={deliveryItems} />
      </section>
      <section className="webhook-section" aria-labelledby="webhook-subscription">
        <h3 id="webhook-subscription">Subscription</h3>
        <DescriptionList className="compact" items={items} />
      </section>
    </div>
  );

  return (
    <div className="webhook-detail">
      <Tabs
        label={`Webhook ${subscription.name}`}
        selected={route.tab ?? "configuration"}
        onChange={(id) =>
          onNavigate({ ...WEBHOOKS, subscriptionId, ...(id === "deliveries" ? { tab: "deliveries" as const } : {}) })
        }
        header={header}
        tabs={[
          { id: "configuration", label: "Configuration", content: configuration },
          {
            id: "deliveries",
            label: "Deliveries",
            content: (
              <WebhookDeliveries
                route={route}
                model={model}
                definition={definition}
                subscription={subscription}
                retentionDays={retentionDays}
                onNavigate={onNavigate}
              />
            ),
          },
        ]}
      />
      {editing && (
        <WebhookDialog
          model={model}
          definitions={definitions}
          batchLimit={batchLimit}
          subscription={subscription}
          onConflict={reload}
          onClose={() => {
            setEditing(false);
            editRef.current?.focus();
          }}
          onSaved={(updated) => {
            setEditing(false);
            stored(
              updated,
              updated.status === "suspended"
                ? "Webhook saved. It stays suspended until it is resumed."
                : "Webhook saved.",
            );
          }}
        />
      )}
      {resuming && (
        <ResumeDialog
          subscription={subscription}
          onCancel={() => setResuming(false)}
          onResumed={(updated, reset) => {
            setResuming(false);
            stored(
              updated,
              reset
                ? "Webhook resumed after the feed's head. Re-sync the receiver now."
                : "Webhook resumed. Delivery continues from the first event not acknowledged.",
            );
          }}
          onConflict={async () => {
            setResuming(false);
            await reload().catch(() => undefined);
            setConflict(
              "This subscription changed while the page was open. It is shown as it is now; review it and choose again.",
            );
          }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title="Delete this webhook?"
          confirmLabel="Delete webhook"
          dismissLabel="Keep the webhook"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setDeleting(false);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () => {
              await api.deleteSubscription(subscription.id, subscription.version);
              setDeleting(false);
              onDeleted(subscription);
            })
          }
        >
          <p>
            Nothing more is sent to <code>{subscription.url}</code>. Its signing key is discarded, and a new
            subscription gets a new one.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

const asText = (value: unknown) => (value === undefined || value === null ? "" : String(value));

/** Why the subscription is suspended, its details as the reason gives them, and the fix. */
function SuspensionNotice({ suspension }: { suspension: NonNullable<Subscription["suspension"]> }) {
  const details = suspension.details ?? {};
  const facts: DescriptionItem[] = [{ term: "Since", value: formatServerTime(suspension.suspendedAt) }];
  const findings = (details.errors as SubscriptionFinding[] | undefined) ?? [];
  switch (suspension.reason) {
    case "CONTRACT_VERSION_CHANGED":
      facts.push(
        { term: "Accepted", value: `v${asText(details.contractVersion)}` },
        { term: "Served now", value: `v${asText(details.servedContractVersion)}` },
      );
      break;
    case "DELIVERY_FAILED":
      facts.push(
        { term: "Attempts", value: asText(details.attempts) },
        { term: "Failing since", value: details.failingSince ? formatServerTime(String(details.failingSince)) : "" },
      );
      if (details.lastError)
        facts.push({ term: "Last error", value: deliveryErrorText(details.lastError as DeliveryError) });
      break;
    case "FILTER_MATCHES_NOTHING":
      facts.push(
        { term: "Filter", value: <code>{asText(details.parameter)}</code> },
        { term: "Values", value: ((details.values as string[] | undefined) ?? []).join(", ") },
      );
      break;
    case "EVENTS_EXPIRED": {
      const publication = details.publication as { id: string; eventSequence: number } | null | undefined;
      facts.push(
        { term: "Lost positions", value: `${asText(details.fromPosition)} to ${asText(details.toPosition)}` },
        {
          term: "Re-sync from",
          value: publication ? (
            <>
              Publication <code>{publication.id}</code> (feed position {publication.eventSequence})
            </>
          ) : (
            "The workspace has no publication: re-read its live data"
          ),
        },
      );
      break;
    }
    case "WORKSPACE_RETIRED":
      if (details.workspaceKey) facts.push({ term: "Workspace", value: <code>{asText(details.workspaceKey)}</code> });
      break;
  }
  return (
    <Notice tone={suspension.reason === "SUSPENDED_BY_USER" ? "info" : "warning"} title={REASON[suspension.reason]}>
      <p>{suspension.message}</p>
      <DescriptionList className="compact" items={facts} />
      <FindingList findings={findings} />
      <p>{FIX[suspension.reason]}</p>
    </Notice>
  );
}

function FindingList({ findings }: { findings: SubscriptionFinding[] }) {
  if (!findings.length) return null;
  return (
    <ul className="webhook-findings">
      {findings.map((finding, index) => (
        <li key={`${finding.pointer ?? ""}-${index}`}>
          {finding.message}
          {finding.pointer && (
            <>
              {" "}
              <code>{finding.pointer}</code>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

/**
 * Resume: from the first event not acknowledged, or with `reset` after the feed's head. A refusal
 * that names what to edit, or events that expired, is shown here; expired events offer the reset.
 */
function ResumeDialog({
  subscription,
  onCancel,
  onResumed,
  onConflict,
}: {
  subscription: Subscription;
  onCancel: () => void;
  onResumed: (subscription: Subscription, reset: boolean) => void;
  onConflict: () => Promise<void>;
}) {
  const [reset, setReset] = useState(subscription.suspension?.reason === "EVENTS_EXPIRED");
  const [pending, setPending] = useState(false);
  const [refusal, setRefusal] = useState<{ message: string; findings: SubscriptionFinding[]; expired: boolean }>();

  async function resume() {
    setPending(true);
    setRefusal(undefined);
    try {
      onResumed(await api.resumeSubscription(subscription.id, subscription.version, reset), reset);
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        await onConflict();
        return;
      }
      const details = isApiError(cause) ? (cause.details as { errors?: SubscriptionFinding[] } | undefined) : undefined;
      const expired = isApiError(cause, "EVENTS_EXPIRED");
      if (expired) setReset(true);
      setRefusal({ message: errorMessage(cause), findings: details?.errors ?? [], expired });
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal title="Resume this webhook?" eyebrow="Webhook" size="compact" busy={pending} onClose={onCancel}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void resume();
        }}
      >
        <p>The subscription is checked again against the active model release and its workspace.</p>
        <fieldset className="form-field">
          <legend>Continue from</legend>
          <div className="webhook-events">
            <label>
              <input type="radio" name="webhook-resume" checked={!reset} onChange={() => setReset(false)} />
              <span>
                The first event not acknowledged
                <small>
                  Nothing is missed: delivery continues after feed position {count(subscription.acknowledgedThrough)}.
                  Refused if those events have expired.
                </small>
              </span>
            </label>
            <label>
              <input type="radio" name="webhook-resume" checked={reset} onChange={() => setReset(true)} />
              <span>
                Now, with reset
                <small>
                  Delivery starts after the feed's head, skipping what happened meanwhile. Reset first, then re-sync the
                  receiver from a publication's lists, so nothing falls between.
                </small>
              </span>
            </label>
          </div>
        </fieldset>
        {refusal && (
          <Notice tone="error" title="The webhook was not resumed">
            <p>{refusal.message}</p>
            <FindingList findings={refusal.findings} />
            {refusal.findings.length > 0 && <p>Edit the subscription to fix these, then resume.</p>}
            {refusal.expired && <p>Reset is now chosen: resume with it, then re-sync the receiver.</p>}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
          <button className="primary" disabled={pending}>
            {pending ? "Resuming…" : reset ? "Reset and resume" : "Resume"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
