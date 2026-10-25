/**
 * What was done to or by a person or client in Security, newest first (0.12 Z4, D319; SP2): their
 * record changes stay in the workspaces' history, since a Security administrator holds no data.
 *
 * As a record's history reads (0.12 RA1, after RH1): under a heading for each day, one line each;
 * filtered by kind in the API (its `aggregateType`); the 10 newest, then 20 more, and Show fewer.
 */

import { useState } from "react";
import { security } from "@/api/securityClient";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { SecurityEvent } from "@/types";
import { ActorName } from "@/ui/ActorName";
import { Choice } from "@/ui/Choice";
import { InlineError } from "@/ui/InlineError";
import { Section } from "@/ui/Section";
import { Timeline } from "@/ui/Timeline";
import { TIMELINE_FIRST, TIMELINE_MORE, TimelinePaging, useTimelineLimit } from "@/ui/TimelinePaging";
import { useWorkspaceLabels } from "./GrantsSection";
import { securityEventTitle } from "./securityText";

type ActivityKind = "all" | "signin" | "access" | "account";

const KINDS = [
  ["all", "All"],
  ["signin", "Signing in"],
  ["access", "Roles and groups"],
  ["account", "Account"],
] as const;

/** The events each kind keeps; All asks for every kind, so changes to keys and providers too. */
const AGGREGATES: Record<ActivityKind, readonly SecurityEvent["aggregateType"][]> = {
  all: [],
  signin: ["sign-in"],
  access: ["grant", "group", "role"],
  account: ["user", "client"],
};

const TONES: Partial<Record<SecurityEvent["aggregateType"], string>> = {
  grant: "relationships",
  group: "relationships",
  role: "relationships",
  user: "structure",
  client: "structure",
};

export function RecentActivity({ principal }: { principal: { id: string; name: string; version: number } }) {
  const [kind, setKind] = useState<ActivityKind>("all");
  const { limit, reset, more } = useTimelineLimit();
  const feed = useCursorFeed(
    (cursor) =>
      security.securityEvents(principal.id, cursor, cursor ? TIMELINE_MORE : TIMELINE_FIRST, AGGREGATES[kind]),
    [principal.id, principal.version, kind],
  );
  const labels = useWorkspaceLabels();
  const shown = feed.items.slice(0, limit);
  return (
    <Section title="Recent activity">
      <div className="activity-kinds">
        <Choice
          name={`activity-kind-${principal.id}`}
          value={kind}
          options={KINDS}
          onChange={(next) => {
            setKind(next);
            reset();
          }}
        />
      </div>
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : !feed.items.length ? (
        <p className="admin-hint">
          {feed.loading
            ? "Loading activity…"
            : kind === "all"
              ? "No activity recorded yet."
              : "No activity of this kind."}
        </p>
      ) : (
        <Timeline
          byDay
          label={`${principal.name}'s recent activity`}
          entries={shown.map((event) => ({
            key: event.id,
            title: securityEventTitle(event, labels),
            at: event.occurredAt,
            tone: TONES[event.aggregateType],
            after: event.actor && (
              <>
                {" "}
                · <ActorName actor={event.actor} />
              </>
            ),
          }))}
        />
      )}
      <TimelinePaging
        limit={limit}
        loaded={feed.items.length}
        hasMore={feed.hasMore}
        loading={feed.loading}
        failed={Boolean(feed.error)}
        moreLabel="Load more"
        noun={["entry", "entries"]}
        onMore={more}
        onLoad={feed.loadMore}
        onFewer={reset}
      />
    </Section>
  );
}
