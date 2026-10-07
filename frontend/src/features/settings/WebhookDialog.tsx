/**
 * New webhook and Edit webhook (Track U U5, rebuilt in U5a): what a subscription asks for, checked
 * by the server as it is saved, in sections: the webhook (its name and URL), its source (consumer
 * API and workspace), its events, its filters and how it is delivered. A consumer API may declare
 * many events and parameters, so events are all of them or a chosen few shown as chips, and a filter
 * is added from a searchable menu only when needed, its values as chips. Delivery is three
 * independent choices (C17): one event per request or batched up to a size, each event with its
 * object or the notification only, and RDM JSON or CloudEvents. A refusal at a field (its
 * `pointer`) is shown at that field. An edit sends only what changed, with the version it was based
 * on; the consumer API and workspace are not edited (the API keeps them).
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type {
  ConsumerApiDeclaration,
  EngineModel,
  Subscription,
  SubscriptionSettings,
  SubscriptionUpdate,
  Workspace,
} from "@/types";
import { Choice } from "@/ui/Choice";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { Modal } from "@/ui/Modal";
import { MultiSelect, type PickOption } from "@/ui/MultiSelect";
import { Notice } from "@/ui/Notice";
import { SearchMenu } from "@/ui/SearchMenu";
import { TokenField } from "@/ui/TokenField";
import { CONTENT, FORMAT, eventDeclaration } from "./webhookText";

/** The batch size offered when an operator first chooses to batch. */
const DEFAULT_BATCH = 100;
/** The most a subscription may batch, when the capabilities have not said. */
const BATCH_LIMIT = 1000;

interface Draft {
  name: string;
  consumerApi: string;
  workspaceKey: string;
  /** Every declared event, or the chosen ones. */
  allEvents: boolean;
  events: string[];
  /** The filters added, in the order they were added, each with its values. */
  filters: [string, string[]][];
  url: string;
  /** One event per request, or batched up to `batchSize`. */
  batched: boolean;
  batchSize: string;
  payload: Subscription["payload"];
  format: Subscription["format"];
}

/** The definitions a subscription can name: those of the active release that declare events. */
export const subscribable = (model: EngineModel) => (model.consumerApis ?? []).filter((item) => item.events?.length);

const declaredEvents = (definition?: ConsumerApiDeclaration) => definition?.events?.map((event) => event.key) ?? [];

function settingsOf(draft: Draft, definition?: ConsumerApiDeclaration): SubscriptionSettings {
  return {
    name: draft.name.trim(),
    events: draft.allEvents ? declaredEvents(definition) : draft.events,
    filters: Object.fromEntries(draft.filters.filter(([, list]) => list.length)),
    url: draft.url.trim(),
    maxEventsPerBatch: draft.batched ? Number(draft.batchSize) : 1,
    payload: draft.payload,
    format: draft.format,
  };
}

const sameList = (a: string[], b: string[]) => a.length === b.length && a.every((item, index) => item === b[index]);

/** The fields of `next` that differ from the subscription, for `PATCH`. */
function changes(subscription: Subscription, next: SubscriptionSettings): Omit<SubscriptionUpdate, "expectedVersion"> {
  const update: Omit<SubscriptionUpdate, "expectedVersion"> = {};
  if (subscription.name !== next.name) update.name = next.name;
  if (!sameList([...subscription.events].sort(), [...next.events].sort())) update.events = next.events;
  const names = new Set([...Object.keys(subscription.filters), ...Object.keys(next.filters)]);
  if ([...names].some((name) => !sameList(subscription.filters[name] ?? [], next.filters[name] ?? [])))
    update.filters = next.filters;
  if (subscription.url !== next.url) update.url = next.url;
  if (subscription.maxEventsPerBatch !== next.maxEventsPerBatch) update.maxEventsPerBatch = next.maxEventsPerBatch;
  if (subscription.payload !== next.payload) update.payload = next.payload;
  if (subscription.format !== next.format) update.format = next.format;
  return update;
}

function draftOf(subscription: Subscription, definition?: ConsumerApiDeclaration): Draft {
  const declared = declaredEvents(definition);
  return {
    name: subscription.name,
    consumerApi: subscription.consumerApi,
    workspaceKey: subscription.workspaceKey,
    allEvents: declared.length > 0 && sameList([...declared].sort(), [...subscription.events].sort()),
    events: subscription.events,
    filters: Object.entries(subscription.filters),
    url: subscription.url,
    batched: subscription.maxEventsPerBatch > 1,
    batchSize: String(subscription.maxEventsPerBatch > 1 ? subscription.maxEventsPerBatch : DEFAULT_BATCH),
    payload: subscription.payload,
    format: subscription.format,
  };
}

/** Where a refusal belongs: a field named by its pointer, or the form as a whole. */
function fieldOf(cause: unknown) {
  const pointer = isApiError(cause) ? (cause.details as { pointer?: unknown } | undefined)?.pointer : undefined;
  if (typeof pointer !== "string") return "form";
  if (pointer.startsWith("/filters/")) return `filter:${decodeURIComponent(pointer.slice("/filters/".length))}`;
  return pointer.split("/")[1] || "form";
}

export function WebhookDialog({
  model,
  batchLimit = BATCH_LIMIT,
  subscription,
  onClose,
  onSaved,
  onConflict,
}: {
  model: EngineModel;
  /** The most events a subscription may batch (capabilities). */
  batchLimit?: number;
  /** The subscription to edit; without it the dialog creates one. */
  subscription?: Subscription;
  onClose: () => void;
  onSaved: (saved: Subscription) => void;
  /** Reload the subscription after a stale edit; the dialog stays open on the current version. */
  onConflict?: () => Promise<Subscription>;
}) {
  const definitions = subscribable(model);
  const editing = !!subscription;
  const [draft, setDraft] = useState<Draft>(() =>
    subscription
      ? draftOf(
          subscription,
          definitions.find((item) => item.key === subscription.consumerApi),
        )
      : {
          name: "",
          consumerApi: definitions[0]?.key ?? "",
          workspaceKey: "",
          allEvents: true,
          events: [],
          filters: [],
          url: "",
          batched: false,
          batchSize: String(DEFAULT_BATCH),
          payload: "full",
          format: "rdm",
        },
  );
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ field: string; message: string }>();
  const [conflict, setConflict] = useState("");
  const definition = definitions.find((item) => item.key === draft.consumerApi);
  const parameters = definition?.parameters ?? {};
  const next = settingsOf(draft, definition);
  const update = subscription ? changes(subscription, next) : undefined;
  const dirty = editing ? Object.keys(update ?? {}).length > 0 : !!(draft.url || draft.name);
  const eventOptions: PickOption[] =
    definition?.events?.map((event) => ({
      id: event.key,
      label: event.key,
      description: eventDeclaration(model, event),
    })) ?? [];
  const unusedParameters: PickOption[] = Object.entries(parameters)
    .filter(([name]) => !draft.filters.some(([added]) => added === name))
    .map(([name, parameter]) => ({
      id: name,
      label: name,
      description: parameter.matchFields ? `Matches ${parameter.matchFields.join(", ")}` : undefined,
    }));

  useEffect(() => {
    if (editing) return;
    let active = true;
    Promise.all([api.workspaces({ status: "active", pageSize: 100 }), api.workspaceRuntimeState()])
      .then(([page, runtime]) => {
        if (!active) return;
        // The default first, as a subscription without a workspace would take it.
        const items = [...page.items].sort(
          (a, b) => Number(b.key === runtime.defaultWorkspaceKey) - Number(a.key === runtime.defaultWorkspaceKey),
        );
        setWorkspaces(items);
        setDraft((current) => ({ ...current, workspaceKey: current.workspaceKey || items[0]?.key || "" }));
      })
      .catch((cause) => active && setError({ field: "form", message: errorMessage(cause) }));
    return () => {
      active = false;
    };
  }, [editing]);

  const set = (patch: Partial<Draft>) => setDraft((current) => ({ ...current, ...patch }));
  const setFilter = (name: string, list: string[]) =>
    set({ filters: draft.filters.map(([added, values]) => [added, added === name ? list : values]) });
  const fieldError = (field: string) => (error?.field === field ? error.message : undefined);

  async function save() {
    setPending(true);
    setError(undefined);
    setConflict("");
    try {
      onSaved(
        subscription
          ? await api.updateSubscription(subscription.id, { expectedVersion: subscription.version, ...update })
          : await api.createSubscription({ ...next, consumerApi: draft.consumerApi, workspaceKey: draft.workspaceKey }),
      );
    } catch (cause) {
      if (subscription && onConflict && isApiError(cause, "VERSION_CONFLICT")) {
        try {
          await onConflict();
          setConflict(
            "Someone changed this subscription while you were editing. It is shown behind this dialog as it is now; save again to apply your changes to it.",
          );
        } catch (reloadCause) {
          setError({ field: "form", message: errorMessage(reloadCause) });
        }
      } else {
        const field = fieldOf(cause);
        const known = ["name", "url", "events", "workspaceKey", "consumerApi", "maxEventsPerBatch"].includes(field);
        setError({
          field: known || field.startsWith("filter:") ? field : "form",
          message: errorMessage(cause),
        });
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={editing ? "Edit webhook" : "New webhook"}
      eyebrow="Webhooks"
      size="wide"
      busy={pending}
      dirty={dirty}
      onClose={onClose}
    >
      <form
        className="dialog-form"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <section className="dialog-form-section" aria-labelledby="dialog-form-webhook">
          <h3 id="dialog-form-webhook">Webhook</h3>
          <div className="dialog-form-grid">
            <FormField label="Name" help="What the receiver is, for people." error={fieldError("name")}>
              {(control) => (
                <input
                  {...control}
                  required
                  autoFocus
                  maxLength={200}
                  placeholder="Billing system"
                  value={draft.name}
                  onChange={(event) => set({ name: event.target.value })}
                />
              )}
            </FormField>
            <FormField label="URL" help="HTTPS on any host; plain HTTP only to localhost." error={fieldError("url")}>
              {(control) => (
                <input
                  {...control}
                  type="url"
                  required
                  placeholder="https://receiver.example.com/hooks/rdm"
                  value={draft.url}
                  onChange={(event) => set({ url: event.target.value })}
                />
              )}
            </FormField>
          </div>
        </section>

        <section className="dialog-form-section" aria-labelledby="dialog-form-source">
          <h3 id="dialog-form-source">Source</h3>
          {editing ? (
            <p className="admin-hint">
              {definition ? `${definition.name} · v${subscription.contractVersion}` : subscription.consumerApi},
              workspace <code>{subscription.workspaceKey}</code>. The consumer API and the workspace are not edited:
              delete the subscription and create another to change them.
            </p>
          ) : (
            <div className="dialog-form-grid">
              <FormField label="Consumer API" error={fieldError("consumerApi")}>
                {(control) => (
                  <select
                    {...control}
                    value={draft.consumerApi}
                    onChange={(event) =>
                      set({ consumerApi: event.target.value, allEvents: true, events: [], filters: [] })
                    }
                  >
                    {definitions.map((item) => (
                      <option key={item.key} value={item.key}>
                        {item.name} · v{item.contractVersion}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
              <FormField
                label="Workspace"
                help="Changes to its live data are delivered."
                error={fieldError("workspaceKey")}
              >
                {(control) => (
                  <select
                    {...control}
                    value={draft.workspaceKey}
                    disabled={!workspaces}
                    onChange={(event) => set({ workspaceKey: event.target.value })}
                  >
                    {!workspaces && <option value="">Loading workspaces…</option>}
                    {workspaces?.map((workspace) => (
                      <option key={workspace.key} value={workspace.key}>
                        {workspace.label} ({workspace.key})
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
            </div>
          )}
        </section>

        <section className="dialog-form-section" aria-labelledby="dialog-form-events">
          <h3 id="dialog-form-events">Events</h3>
          <Choice
            name="webhook-events"
            value={draft.allEvents ? "all" : "some"}
            options={[
              ["all", `All events (${eventOptions.length})`],
              ["some", "Chosen events"],
            ]}
            onChange={(value) =>
              set(
                value === "all"
                  ? { allEvents: true }
                  : { allEvents: false, events: draft.events.length ? draft.events : [] },
              )
            }
          />
          {!draft.allEvents && (
            <MultiSelect
              label="Events"
              options={eventOptions}
              selected={draft.events}
              onChange={(events) => set({ events })}
              addLabel="Choose events"
              emptyLabel="No event chosen yet."
            />
          )}
          {fieldError("events") && <small className="field-error">{fieldError("events")}</small>}
        </section>

        <section className="dialog-form-section" aria-labelledby="dialog-form-filters">
          <div className="dialog-form-heading">
            <h3 id="dialog-form-filters">Filters</h3>
            <SearchMenu
              label="Add filter"
              items={unusedParameters}
              onSelect={(name) => set({ filters: [...draft.filters, [name, []]] })}
            />
          </div>
          {draft.filters.length === 0 ? (
            <p className="admin-hint">
              {Object.keys(parameters).length
                ? "None: every event of the chosen kinds is delivered. Add a filter to deliver only those of matching records."
                : "This consumer API declares no parameter to filter by."}
            </p>
          ) : (
            <ul className="webhook-filters">
              {draft.filters.map(([name, list]) => (
                <li key={name}>
                  <FormField
                    label={name}
                    help={
                      parameters[name]?.matchFields
                        ? `Each value matches a record's ${parameters[name].matchFields.join(", ")}; several are alternatives.`
                        : "Several values are alternatives."
                    }
                    error={fieldError(`filter:${name}`)}
                  >
                    {(control) => (
                      <TokenField
                        control={control}
                        label={name}
                        values={list}
                        onChange={(values) => setFilter(name, values)}
                        placeholder="Type a value, then Enter"
                      />
                    )}
                  </FormField>
                  <button
                    type="button"
                    className="icon-button"
                    aria-label={`Remove filter ${name}`}
                    onClick={() => set({ filters: draft.filters.filter(([added]) => added !== name) })}
                  >
                    <Icon name="trash" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="dialog-form-section" aria-labelledby="dialog-form-delivery">
          <h3 id="dialog-form-delivery">Delivery</h3>
          <FormField
            label="Requests"
            group
            help={
              draft.batched
                ? "Each request holds the events waiting, up to this many and 1 MiB; it never waits to fill up."
                : "Each change is a request of its own, sent one at a time in order. For bulk changes, batch them."
            }
          >
            {() => (
              <Choice
                name="webhook-requests"
                value={draft.batched ? "batched" : "single"}
                options={[
                  ["single", "One event per request"],
                  ["batched", "Batched"],
                ]}
                onChange={(choice) => set({ batched: choice === "batched" })}
              />
            )}
          </FormField>
          {draft.batched && (
            <FormField
              label="Up to (events)"
              help={`From 2 to ${batchLimit.toLocaleString()}.`}
              error={fieldError("maxEventsPerBatch")}
            >
              {(control) => (
                <input
                  {...control}
                  className="webhook-wait"
                  type="number"
                  min={2}
                  max={batchLimit}
                  required
                  value={draft.batchSize}
                  onChange={(event) => set({ batchSize: event.target.value })}
                />
              )}
            </FormField>
          )}
          <div className="dialog-form-grid">
            <FormField
              label="Content"
              group
              help={
                draft.payload === "full"
                  ? "Each event carries the object as it is when sent."
                  : "Each event names the change and the object; the receiver reads what it needs."
              }
            >
              {() => (
                <Choice
                  name="webhook-payload"
                  value={draft.payload}
                  options={[
                    ["full", CONTENT.full],
                    ["identity", CONTENT.identity],
                  ]}
                  onChange={(payload) => set({ payload })}
                />
              )}
            </FormField>
            <FormField
              label="Format"
              group
              help={
                draft.format === "rdm"
                  ? "The engine's envelope with its events."
                  : draft.batched
                    ? "A JSON array of structured CloudEvents (application/cloudevents-batch+json)."
                    : "One structured CloudEvent (application/cloudevents+json)."
              }
            >
              {() => (
                <Choice
                  name="dialog-format"
                  value={draft.format}
                  options={[
                    ["rdm", FORMAT.rdm],
                    ["cloudevents", FORMAT.cloudevents],
                  ]}
                  onChange={(format) => set({ format })}
                />
              )}
            </FormField>
          </div>
        </section>

        {conflict && (
          <Notice tone="warning" title="Not saved">
            {conflict}
          </Notice>
        )}
        {error?.field === "form" && (
          <Notice tone="error" title={editing ? "The webhook was not saved" : "The webhook was not created"}>
            {error.message}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={
              pending || !next.events.length || !next.url || !next.name || (editing ? !dirty : !draft.workspaceKey)
            }
          >
            {pending ? "Saving…" : editing ? "Save changes" : "Create webhook"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
