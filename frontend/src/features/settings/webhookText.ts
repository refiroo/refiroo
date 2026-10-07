/**
 * How the Webhooks page words a subscription: its state, why it is suspended and what fixes it
 * (API.md, "Suspension reasons"), how its requests are made, a failed attempt, and an event's
 * declaration from the model.
 */

import type { ConsumerEventDeclaration, DeliveryError, EngineModel, Subscription, SuspensionReason } from "@/types";
import type { StatusTone } from "@/ui/StatusPill";

/** The state a person reads first: delivering, retrying a failing batch, or suspended. */
export function subscriptionState(subscription: Subscription): { label: string; tone: StatusTone } {
  if (subscription.status === "suspended") return { label: "Suspended", tone: "error" };
  if (subscription.delivery.pending) return { label: "Retrying", tone: "warning" };
  return { label: "Active", tone: "success" };
}

/** How many events a request carries: one, or up to the subscription's batch size. */
export const requestsLabel = (maxEventsPerBatch: number) =>
  maxEventsPerBatch === 1 ? "One event per request" : `Batched, up to ${maxEventsPerBatch.toLocaleString()} events`;

export const CONTENT: Record<Subscription["payload"], string> = {
  full: "With the object",
  identity: "Notification only",
};

export const FORMAT: Record<Subscription["format"], string> = {
  rdm: "RDM JSON",
  cloudevents: "CloudEvents 1.0",
};

export const REASON: Record<SuspensionReason, string> = {
  SUSPENDED_BY_USER: "Suspended by a user",
  MODEL_CHANGED: "The model changed",
  CONTRACT_VERSION_CHANGED: "The contract version changed",
  WORKSPACE_RETIRED: "The workspace was retired",
  DELIVERY_FAILED: "Delivery failed",
  FILTER_MATCHES_NOTHING: "A filter matches nothing",
  EVENTS_EXPIRED: "Events expired",
};

/** What brings a subscription back, for each reason. */
export const FIX: Record<SuspensionReason, string> = {
  SUSPENDED_BY_USER: "Resume it to continue from the first event not acknowledged.",
  MODEL_CHANGED:
    "The active model release no longer declares what the subscription names. Edit it to fix the findings below, then resume.",
  CONTRACT_VERSION_CHANGED:
    "The active release serves another contract version. Check that the receiver reads it, then resume: resuming accepts the version served.",
  WORKSPACE_RETIRED: "Reactivate the workspace in Settings › Workspaces, then resume; or delete the subscription.",
  DELIVERY_FAILED:
    "The receiver did not acknowledge a batch for the whole retry window. Fix the receiver, then resume: the batch is sent again at once.",
  FILTER_MATCHES_NOTHING: "A filter value no longer matches a record. Edit the filter, then resume.",
  EVENTS_EXPIRED:
    "Events the receiver had not acknowledged expired before they were delivered. Resume with reset, then re-sync the receiver from the publication named below.",
};

const ERROR_KIND: Record<DeliveryError["kind"], string> = {
  status: "The receiver answered with an error",
  redirect: "The receiver redirected (not followed)",
  timeout: "No answer in time",
  connection: "Could not connect",
  tls: "TLS failed",
  address: "The address was refused",
};

/** A failed attempt: the engine's message, which names the status, host or cause, or the kind alone. */
export function deliveryErrorText(error: DeliveryError) {
  if (!error.message) return ERROR_KIND[error.kind];
  return error.kind === "status" ? `The receiver answered ${error.message}` : error.message;
}

const CHANGE: Record<ConsumerEventDeclaration["changes"][number], string> = {
  created: "created",
  updated: "updated",
  deleted: "deleted",
};

/** An event's declaration in words: the types, the changes, and what an update watches. */
export function eventDeclaration(model: EngineModel, event: ConsumerEventDeclaration) {
  const types = event.objectTypes
    .map((key) => model.objectTypes.find((type) => type.key === key)?.pluralName ?? key)
    .join(", ");
  const changes = event.changes.map((change) => CHANGE[change]).join(", ");
  const watched = [...(event.watch?.fields ?? []), ...(event.watch?.projections ?? [])];
  return `${types}: ${changes}. ${watched.length ? `An update counts when ${watched.join(", ")} change.` : "Any change to the output counts."}`;
}

/** The URL as a catalogue names it: its host and path. */
export function urlName(url: string) {
  try {
    const parsed = new URL(url);
    return `${parsed.host}${parsed.pathname === "/" ? "" : parsed.pathname}`;
  } catch {
    return url;
  }
}
