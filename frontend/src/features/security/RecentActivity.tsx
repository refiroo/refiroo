/**
 * What was done to or by a person or client in Security, newest first (0.12 Z4, D319; SP2): their
 * record changes stay in the workspaces' history, since a Security administrator holds no data.
 */

import { security } from "@/api/securityClient";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { ActorName } from "@/ui/ActorName";
import { InlineError } from "@/ui/InlineError";
import { Section } from "@/ui/Section";
import { Timeline } from "@/ui/Timeline";
import { useWorkspaceLabels } from "./GrantsSection";
import { securityEventTitle } from "./securityText";

export function RecentActivity({ principal }: { principal: { id: string; name: string; version: number } }) {
  const feed = useCursorFeed(
    (cursor) => security.securityEvents(principal.id, cursor),
    [principal.id, principal.version],
  );
  const labels = useWorkspaceLabels();
  return (
    <Section title="Recent activity">
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : !feed.items.length ? (
        <p className="admin-hint">{feed.loading ? "Loading activity…" : "No activity recorded yet."}</p>
      ) : (
        <Timeline
          label={`${principal.name}'s recent activity`}
          entries={feed.items.map((event) => ({
            key: event.id,
            title: securityEventTitle(event, labels),
            at: event.occurredAt,
            after: event.actor && (
              <>
                {" "}
                · <ActorName actor={event.actor} />
              </>
            ),
          }))}
        />
      )}
      {feed.hasMore && !feed.error && (
        <button type="button" className="load-more inline history-more" disabled={feed.loading} onClick={feed.loadMore}>
          {feed.loading ? "Loading…" : "Load more"}
        </button>
      )}
    </Section>
  );
}
