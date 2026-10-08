/**
 * A webhook's Deliveries tab (Track U U5a): the events the subscription delivered or is delivering,
 * newest first (`GET /consumer-subscriptions/{id}/deliveries`), one row per event. Rows of one
 * request share its status, attempts, answer and time.
 * An event opens at its own address, in a dialog: its facts, the next attempt while one is due,
 * every attempt, and the request and response bodies as formatted JSON. **Resend** sends it again
 * by hand, as it was sent (C-D129–C-D131); a delivered one only after a confirmation.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { routePath } from "@/routing/routes";
import type {
  ConsumerApiDefinition,
  DeliveryAttempt,
  DeliveryDetail,
  DeliveryRow,
  DeliveryStatus,
  EngineModel,
  RouteState,
  SettingsRoute,
  Subscription,
} from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { JsonView } from "@/ui/JsonView";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill, type StatusTone } from "@/ui/StatusPill";
import { count } from "./limits";

type WebhooksRoute = Extract<SettingsRoute, { page: "webhooks" }>;

export const DELIVERY_STATUS: Record<DeliveryStatus, { label: string; tone: StatusTone }> = {
  queued: { label: "Queued", tone: "draft" },
  sending: { label: "Sending", tone: "draft" },
  retrying: { label: "Retrying", tone: "warning" },
  succeeded: { label: "Succeeded", tone: "success" },
  failed: { label: "Failed", tone: "error" },
  dropped: { label: "Dropped", tone: "neutral" },
};

/** An ID too long for a table cell: its first characters, the whole in a tooltip. */
const short = (id: string) => (id.length > 13 ? `${id.slice(0, 8)}…` : id);

const answer = (status: number | null) => (status === null ? "No answer" : String(status));

const duration = (ms: number | null) =>
  ms === null ? "Still sending" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;

/**
 * Where an event's record opens: its type found by the public name the consumer API gives it, in
 * the first application that shows that type, in the webhook's workspace. None for a deleted
 * record or a type the active model no longer exposes.
 */
function recordRoute(
  model: EngineModel,
  definition: ConsumerApiDefinition | undefined,
  subscription: Subscription,
  event: { objectType: string; objectId: string; change: string },
): RouteState | undefined {
  if (event.change === "deleted") return undefined;
  const objectTypeKey = Object.entries(definition?.publicNames ?? {}).find(
    ([, publicName]) => publicName === event.objectType,
  )?.[0];
  const application = objectTypeKey && model.applications.find((item) => item.objectTypeKeys.includes(objectTypeKey));
  if (!objectTypeKey || !application) return undefined;
  return {
    kind: "detail",
    applicationKey: application.key,
    objectTypeKey,
    objectId: event.objectId,
    workspaceKey: subscription.workspaceKey,
  };
}

/** The object's ID, linked to its record where it has one to open. */
function ObjectLink({
  id,
  to,
  onNavigate,
  short: shorten = false,
}: {
  id: string;
  to?: RouteState;
  onNavigate: (route: RouteState) => void;
  short?: boolean;
}) {
  const text = <code title={id}>{shorten ? short(id) : id}</code>;
  if (!to) return text;
  return (
    <RouteLink href={routePath(to)} onNavigate={() => onNavigate(to)} aria-label={`Open record ${id}`}>
      {text}
    </RouteLink>
  );
}

function DeliveryState({ status }: { status: DeliveryStatus }) {
  const state = DELIVERY_STATUS[status];
  return <StatusPill tone={state.tone}>{state.label}</StatusPill>;
}

export function WebhookDeliveries({
  route,
  model,
  definition,
  subscription,
  retentionDays,
  onNavigate,
}: {
  route: WebhooksRoute & { subscriptionId: string };
  model: EngineModel;
  /** The subscription's consumer API, expanded (C18); none when the active release lacks it. */
  definition?: ConsumerApiDefinition;
  subscription: Subscription;
  retentionDays?: number;
  onNavigate: (route: RouteState) => void;
}) {
  const { subscriptionId } = route;
  const [status, setStatus] = useState<DeliveryStatus | "">("");
  const feed = useCursorFeed(
    (cursor) => api.deliveries(subscriptionId, { cursor, status: status || undefined }),
    [subscriptionId, status],
  );
  const tab: WebhooksRoute = { kind: "settings", page: "webhooks", subscriptionId, tab: "deliveries" };
  const opened = (row: DeliveryRow): WebhooksRoute => ({
    ...tab,
    deliveryId: row.deliveryId,
    eventId: row.eventId,
  });
  const kept = retentionDays ? ` Deliveries are kept for ${count(retentionDays)} days.` : "";

  return (
    <div className="webhook-deliveries">
      <div className="webhook-deliveries-bar">
        <label className="toolbar-field">
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as DeliveryStatus | "")}>
            <option value="">All</option>
            {Object.entries(DELIVERY_STATUS).map(([value, state]) => (
              <option key={value} value={value}>
                {state.label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="secondary" disabled={feed.loading} onClick={feed.reload}>
          Refresh
        </button>
      </div>
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : feed.loading && feed.items.length === 0 ? (
        <Skeleton label="Loading deliveries" lines={5} />
      ) : feed.items.length === 0 ? (
        <EmptyState>
          {status ? "No delivery has this status." : "Nothing delivered yet: events appear here once they are sent."}
          {kept}
        </EmptyState>
      ) : (
        <>
          <SettingsTable
            label="Deliveries"
            columns={["Event ID", "Event", "Object ID", "Status", "Attempts", "Response", "Sent"]}
          >
            {feed.items.map((row) => (
              <tr key={`${row.deliveryId}:${row.eventId}`}>
                <th scope="row">
                  <RouteLink
                    href={routePath(opened(row))}
                    onNavigate={() => onNavigate(opened(row))}
                    title={row.eventId}
                  >
                    <code>{short(row.eventId)}</code>
                  </RouteLink>
                </th>
                <td data-label="Event">
                  <code>{row.event}</code>
                  <span className="webhook-change"> {row.change}</span>
                  {row.resendOf && <span className="webhook-change"> · resent</span>}
                </td>
                <td data-label="Object ID">
                  <ObjectLink
                    id={row.objectId}
                    to={recordRoute(model, definition, subscription, row)}
                    onNavigate={onNavigate}
                    short
                  />
                </td>
                <td data-label="Status">
                  <DeliveryState status={row.status} />
                </td>
                <td data-label="Attempts">{count(row.attempts)}</td>
                <td data-label="Response">{row.attempts ? answer(row.responseStatus) : "—"}</td>
                <td data-label="Sent">{row.sentAt ? formatServerTime(row.sentAt) : "Not yet"}</td>
              </tr>
            ))}
          </SettingsTable>
          {feed.hasMore && (
            <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
              Load more deliveries
            </button>
          )}
          <p className="admin-hint">Events sent in one request share its status, attempts and answer.{kept}</p>
        </>
      )}
      {route.deliveryId && (
        <DeliveryDialog
          key={`${route.deliveryId}:${route.eventId ?? ""}`}
          subscriptionId={subscriptionId}
          deliveryId={route.deliveryId}
          eventId={route.eventId}
          onResent={feed.reload}
          recordOf={(event) => recordRoute(model, definition, subscription, event)}
          onNavigate={onNavigate}
          onOpen={(resent) =>
            onNavigate({
              ...tab,
              deliveryId: resent.deliveryId,
              ...(resent.events[0] ? { eventId: resent.events[0].eventId } : {}),
            })
          }
          onClose={() => onNavigate(tab)}
        />
      )}
    </div>
  );
}

/** One event's delivery: its facts, its request's attempts and both bodies. */
function DeliveryDialog({
  subscriptionId,
  deliveryId,
  eventId,
  onResent,
  onOpen,
  recordOf,
  onNavigate,
  onClose,
}: {
  subscriptionId: string;
  deliveryId: string;
  eventId?: string;
  /** A resend was logged: the list reloads. */
  onResent: () => void;
  /** Open a resend's own delivery. */
  onOpen: (resent: DeliveryDetail) => void;
  recordOf: (event: DeliveryDetail["events"][number]) => RouteState | undefined;
  onNavigate: (route: RouteState) => void;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<DeliveryDetail>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState<number>();
  const [token, setToken] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState<DeliveryDetail>();
  const [resendError, setResendError] = useState("");

  async function resend() {
    const shownEvent = detail?.events.find((item) => item.eventId === eventId) ?? detail?.events[0];
    if (!shownEvent) return;
    setResending(true);
    setResendError("");
    try {
      const sent = await api.resendDelivery(subscriptionId, deliveryId, shownEvent.eventId);
      setResent(sent);
      setConfirming(false);
      onResent();
    } catch (cause) {
      setResendError(errorMessage(cause));
    } finally {
      setResending(false);
    }
  }

  useEffect(() => {
    let active = true;
    api
      .delivery(subscriptionId, deliveryId)
      .then((found) => {
        if (!active) return;
        setDetail(found);
        setAttempt(found.attempts.at(-1)?.number);
        setError("");
      })
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [subscriptionId, deliveryId, token]);

  const event = detail?.events.find((item) => item.eventId === eventId) ?? detail?.events[0];
  const shown: DeliveryAttempt | undefined = detail?.attempts.find((item) => item.number === attempt);
  const last = detail?.attempts.at(-1);
  const facts: DescriptionItem[] =
    detail && event
      ? [
          { term: "Event ID", value: <code>{event.eventId}</code> },
          {
            term: "Event",
            value: (
              <>
                <code>{event.event}</code> · {event.change}
              </>
            ),
          },
          {
            term: "Object",
            value: (
              <>
                <ObjectLink id={event.objectId} to={recordOf(event)} onNavigate={onNavigate} /> · {event.objectType}
              </>
            ),
          },
          { term: "Feed position", value: count(event.position) },
          { term: "Status", value: <DeliveryState status={detail.status} /> },
          { term: "Attempts", value: count(detail.attempts.length) },
          { term: "Response", value: last ? answer(last.responseStatus) : "—" },
          { term: "Sent", value: last ? formatServerTime(last.startedAt) : "Not yet" },
          ...(detail.nextAttemptAt ? [{ term: "Next attempt", value: formatServerTime(detail.nextAttemptAt) }] : []),
          { term: "Delivery ID", value: <code>{detail.deliveryId}</code> },
          ...(detail.resendOf ? [{ term: "Resend of", value: <code>{detail.resendOf}</code> }] : []),
          {
            term: "Request",
            value: `${count(detail.events.length)} ${detail.events.length === 1 ? "event" : "events"}${detail.requestBytes ? `, ${count(detail.requestBytes)} bytes` : ""}`,
          },
        ]
      : [];

  return (
    <Modal title={event ? event.event : "Delivery"} eyebrow="Delivered event" size="wide" onClose={onClose}>
      <div className="delivery-detail">
        {error ? (
          <InlineError message={error} onRetry={() => setToken((value) => value + 1)} />
        ) : !detail ? (
          <Skeleton label="Loading the delivery" lines={6} />
        ) : (
          <>
            <div className="delivery-actions">
              <button
                type="button"
                className="secondary"
                disabled={resending || detail.requestBody === null}
                aria-describedby={detail.requestBody === null ? "delivery-not-sent" : undefined}
                onClick={() => {
                  setResent(undefined);
                  setResendError("");
                  if (detail.status === "succeeded") setConfirming(true);
                  else void resend();
                }}
              >
                {resending && !confirming ? "Resending…" : "Resend"}
              </button>
              {detail.requestBody === null && (
                <span id="delivery-not-sent" className="admin-hint">
                  Never sent, so there is nothing to resend yet.
                </span>
              )}
            </div>
            {resent && (
              <Notice
                tone={resent.status === "succeeded" ? "success" : "warning"}
                title={resent.status === "succeeded" ? "Resent" : "Resent, but the receiver did not accept it"}
                actions={
                  <button type="button" className="secondary" onClick={() => onOpen(resent)}>
                    Open the resend
                  </button>
                }
              >
                {resent.attempts[0]?.error
                  ? resent.attempts[0].error.message
                  : `The receiver answered ${answer(resent.attempts[0]?.responseStatus ?? null)}.`}{" "}
                It went as a new delivery with the same event ID and <code>RDM-Redelivery: manual</code>; it is not
                retried.
              </Notice>
            )}
            {resendError && !confirming && (
              <Notice tone="error" title="The event was not resent">
                {resendError}
              </Notice>
            )}
            <DescriptionList className="compact" items={facts} />
            <section aria-labelledby="delivery-attempts">
              <h3 id="delivery-attempts">Attempts</h3>
              {detail.attempts.length === 0 ? (
                <p className="admin-hint">Not sent yet.</p>
              ) : (
                <SettingsTable label="Attempts" columns={["Attempt", "Started", "Duration", "Answer"]}>
                  {detail.attempts.map((item) => (
                    <tr key={item.number} className={item.number === attempt ? "selected" : undefined}>
                      <th scope="row">
                        <button
                          type="button"
                          className="link-button"
                          aria-pressed={item.number === attempt}
                          onClick={() => setAttempt(item.number)}
                        >
                          Attempt {item.number}
                        </button>
                      </th>
                      <td data-label="Started">{formatServerTime(item.startedAt)}</td>
                      <td data-label="Duration">{duration(item.durationMs)}</td>
                      <td data-label="Answer">{item.error ? item.error.message : answer(item.responseStatus)}</td>
                    </tr>
                  ))}
                </SettingsTable>
              )}
            </section>
            <div className="delivery-bodies">
              <section aria-labelledby="delivery-request">
                <h3 id="delivery-request">Request body</h3>
                {detail.requestBody === null ? (
                  <p className="admin-hint">Not sent yet.</p>
                ) : (
                  <JsonView label="Request body" value={detail.requestBody} />
                )}
              </section>
              <section aria-labelledby="delivery-response">
                <h3 id="delivery-response">
                  Response body{shown && detail.attempts.length > 1 ? ` · attempt ${shown.number}` : ""}
                </h3>
                {!shown ? (
                  <p className="admin-hint">No attempt yet.</p>
                ) : shown.responseBody ? (
                  <JsonView label="Response body" value={shown.responseBody} />
                ) : (
                  <p className="admin-hint">
                    {shown.responseStatus === null ? "The receiver did not answer." : "The answer had no body."}
                  </p>
                )}
              </section>
            </div>
          </>
        )}
      </div>
      {confirming && detail && (
        <ConfirmDialog
          title="Resend a delivered event?"
          confirmLabel="Resend event"
          dismissLabel="Don't resend"
          pending={resending}
          error={resendError}
          onCancel={() => {
            setConfirming(false);
            setResendError("");
          }}
          onConfirm={() => void resend()}
        >
          <p>
            The receiver already acknowledged this event. It is sent again as it was, with the same event ID and{" "}
            <code>RDM-Redelivery: manual</code>, so the receiver may process it a second time.
          </p>
        </ConfirmDialog>
      )}
    </Modal>
  );
}
