/**
 * What was done to or by a person or client in Security, newest first (0.12 Z4, D319; SP2): their
 * record changes stay in the workspaces' history, since a Security administrator holds no data.
 *
 * As a record's history reads (0.12 RA1, after RH1): under a heading for each day, one line each;
 * filtered by kind in the API (its `aggregateType`); the 10 newest, then 20 more, and Show fewer.
 * Since 0.17 ST1 (PP-D67) it is a stacked group of the page: the kinds are filter chips wearing their
 * markers' colours, the day-by-day Timeline stands in one panel.
 */

import { useState } from "react";
import { security } from "@/api/securityClient";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { SecurityEvent } from "@/types";
import { ActorName } from "@/ui/ActorName";
import type { Hue } from "@/model/hues";
import { InlineError } from "@/ui/InlineError";
import { FilterChip, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { Timeline } from "@/ui/Timeline";
import { TIMELINE_FIRST, TIMELINE_MORE, TimelinePaging, useTimelineLimit } from "@/ui/TimelinePaging";
import { useWorkspaceLabels } from "./GrantsSection";
import { securityEventTitle } from "./securityText";

type ActivityKind = "all" | "signin" | "access" | "account";

/** Each kind with the hue of its marker on the Timeline (`styles/components.css`, `.history-line-marker`). */
const KINDS: readonly (readonly [ActivityKind, string, Hue | undefined])[] = [
  ["all", "All", undefined],
  ["signin", "Signing in", 2],
  ["access", "Roles and groups", 1],
  ["account", "Account", 3],
];

/** The events each kind keeps; All asks for every kind, so changes to keys and providers too. */
const AGGREGATES: Record<ActivityKind, readonly SecurityEvent["aggregateType"][]> = {
  all: [],
  signin: ["sign-in"],
  access: ["grant", "group", "role"],
  account: ["user", "client"],
};

const TONES: Partial<Record<SecurityEvent["aggregateType"], string>> = {
  "sign-in": "signin",
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
    <SettingsGroup
      stacked
      title="Recent activity"
      description="Sign-ins and every change to this account, its roles and groups, newest first."
      tools={
        <span className="filter-chips" role="group" aria-label="Kind of activity">
          {KINDS.map(([value, label, hue]) => (
            <FilterChip
              key={value}
              hue={hue}
              selected={kind === value}
              onSelect={() => {
                setKind(value);
                reset();
              }}
            >
              {label}
            </FilterChip>
          ))}
        </span>
      }
    >
      <SettingsPanel>
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : !feed.items.length ? (
          feed.loading ? (
            <Skeleton label="Loading activity" lines={3} />
          ) : (
            <p className="settings-panel-note">
              {kind === "all" ? "No activity recorded yet." : "No activity of this kind."}
            </p>
          )
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
      </SettingsPanel>
    </SettingsGroup>
  );
}
