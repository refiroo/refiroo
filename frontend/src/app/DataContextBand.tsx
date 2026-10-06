/**
 * The data-context band at the top of the content (ADR-039, Track U U2): which workspace and
 * application the page is in, and which data it reads and edits. Live is a green pill with a
 * one-line explanation. A change set turns the band amber and a publication violet, and the band
 * then carries that context's own bar (`contextActions`: the change set's Review, Validate and
 * Publish, or the publication's way back). The Live / Change sets / Publications switch stays at
 * its right end in every context; its Live is the way back from a change set.
 *
 * The band stays visible while the page scrolls (CSS); what its actions report is placed below it
 * through `BelowContextBand`.
 */

import type { ReactNode } from "react";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { routeChangeSetId, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, ApplicationRoute, RouteState } from "@/types";
import { StatusPill } from "@/ui/StatusPill";

export function DataContextBand({
  application,
  route,
  workspaceLabel,
  contextActions,
  onNavigate,
}: {
  application: ApplicationDefinition;
  route: ApplicationRoute;
  workspaceLabel: string;
  contextActions?: ReactNode;
  onNavigate: (route: RouteState) => void;
}) {
  const { changeSet, publication } = useWorkspaceData();
  const changeSetId = routeChangeSetId(route);
  const publicationId = route.kind === "list" || route.kind === "detail" ? route.publicationId : undefined;
  // The change set and publication lists are pages about a context, not in one.
  const listing = route.kind === "changeSets" || route.kind === "publications";
  const tone = changeSetId ? "changeSet" : publicationId ? "publication" : "live";
  const status = changeSetId
    ? `Change set · ${changeSet?.name || "Untitled change set"}`
    : publicationId
      ? publication
        ? `Publication ${publication.publicationNumber}`
        : "Publication"
      : "Live";
  const live = () => onNavigate(viewRoute(application, application.defaultView, route.workspaceKey));

  return (
    <div className={`data-context-band band-${tone === "changeSet" ? "change-set" : tone}`}>
      <div className="band-context">
        <div role="group" className="shell-context" aria-label="Current context">
          <span>{workspaceLabel}</span>
          <span aria-hidden="true"> / </span>
          <span>{application.name}</span>
          {!listing && <StatusPill tone={tone}>{status}</StatusPill>}
        </div>
        {tone === "live" && !listing && <span className="band-note">Edits apply immediately in this workspace.</span>}
        <nav className="data-context-switch" aria-label="Workspace data context">
          <button aria-current={!listing && tone === "live" ? "page" : undefined} onClick={live}>
            Live
          </button>
          <button
            aria-current={route.kind === "changeSets" || changeSetId ? "page" : undefined}
            onClick={() =>
              onNavigate({ kind: "changeSets", applicationKey: application.key, workspaceKey: route.workspaceKey })
            }
          >
            Change sets
          </button>
          <button
            aria-current={route.kind === "publications" || publicationId ? "page" : undefined}
            onClick={() =>
              onNavigate({ kind: "publications", applicationKey: application.key, workspaceKey: route.workspaceKey })
            }
          >
            Publications
          </button>
        </nav>
      </div>
      {contextActions && <div className="band-actions">{contextActions}</div>}
    </div>
  );
}
