/**
 * The data-context band at the top of the content (ADR-039, Track U U2): which workspace and
 * application the page is in, and which data it reads and edits. Live is a soft green strip with
 * the Live pill and a one-line explanation (ADR-040). A change set is the same strip in amber and a
 * publication in violet, each with its own line saying what an edit does there, and the band then
 * carries that context's own bar (`contextActions`: the change set's name, Review, Validate and
 * Publish, or the publication's way back). The Live / Change sets / Publications switch stays at
 * its right end in every context, a dot of each context's colour on its switch; its Live is the
 * way back from a change set. The change set and publication lists are about a context rather
 * than in one, so their band is neutral.
 *
 * The band stays visible while the page scrolls (CSS); what its actions report is placed below it
 * through `BelowContextBand`.
 *
 * On a phone (0.10 N1) the band is one line whose three parts each open their choice: the
 * workspace (the workspace selector), the application, in its tile (the applications the top bar
 * otherwise lists), and the data context (the same switch, with the line saying what an edit does).
 * The top bar's tabs and the drawer's workspace selector are then left out.
 */

import { useLayoutEffect, useState, type ReactNode } from "react";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { applicationHue } from "@/model/hues";
import { routeChangeSetId, routePublicationId, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, ApplicationRoute, EngineModel, RouteState } from "@/types";
import { ControlPopover } from "@/ui/ControlPopover";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { StatusPill } from "@/ui/StatusPill";
import { ApplicationButtons } from "./TopBar";

export function DataContextBand({
  model,
  application,
  route,
  workspaceLabel,
  contextActions,
  onNavigate,
  onSelectApplication,
  onChangeWorkspace,
  onManageWorkspaces,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  route: ApplicationRoute;
  workspaceLabel: string;
  contextActions?: ReactNode;
  onNavigate: (route: RouteState) => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onChangeWorkspace: (workspaceKey: string) => void;
  /** Offered where the deployment allows workspace administration. */
  onManageWorkspaces?: () => void;
}) {
  const phone = useMediaQuery(PHONE_WIDTH);
  const [band, setBand] = useState<HTMLDivElement | null>(null);
  useLayoutEffect(() => (band ? publishBandHeight(band) : undefined), [band]);
  const { changeSet, publication } = useWorkspaceData();
  const changeSetId = routeChangeSetId(route);
  const publicationId = routePublicationId(route);
  // The change set and publication lists are pages about a context, not in one.
  const listing = route.kind === "changeSets" || route.kind === "publications";
  const tone = changeSetId ? "changeSet" : publicationId ? "publication" : "live";
  // The pill names the context; a change set's name is its bar's heading, so it is not said twice.
  const status = changeSetId
    ? "Change set"
    : publicationId
      ? publication
        ? `Publication ${publication.publicationNumber}`
        : "Publication"
      : "Live";
  const note =
    tone === "live"
      ? "Edits apply immediately in this workspace."
      : tone === "changeSet"
        ? changeSet
          ? "Edits stay in this change set until it is published."
          : undefined
        : "Read-only. A publication's records never change.";
  const live = () => onNavigate(viewRoute(application, application.defaultView, route.workspaceKey));

  const switcher = (close?: () => void) => (
    <nav className="data-context-switch" aria-label="Workspace data context">
      <button
        aria-current={!listing && tone === "live" ? "page" : undefined}
        onClick={() => {
          close?.();
          live();
        }}
      >
        Live
      </button>
      <button
        aria-current={route.kind === "changeSets" || changeSetId ? "page" : undefined}
        onClick={() => {
          close?.();
          onNavigate({ kind: "changeSets", applicationKey: application.key, workspaceKey: route.workspaceKey });
        }}
      >
        <span className="context-dot context-dot-change-set" aria-hidden="true" />
        Change sets
      </button>
      <button
        aria-current={route.kind === "publications" || publicationId ? "page" : undefined}
        onClick={() => {
          close?.();
          onNavigate({ kind: "publications", applicationKey: application.key, workspaceKey: route.workspaceKey });
        }}
      >
        <span className="context-dot context-dot-publication" aria-hidden="true" />
        Publications
      </button>
    </nav>
  );
  const contextName = listing ? (route.kind === "changeSets" ? "Change sets" : "Publications") : status;

  return (
    <div
      ref={setBand}
      className={`data-context-band band-${listing ? "neutral" : tone === "changeSet" ? "change-set" : tone}`}
    >
      {phone ? (
        <div role="group" className="band-context band-compact" aria-label="Current context">
          <ControlPopover
            label={`Workspace: ${workspaceLabel}`}
            trigger={
              <>
                <span className="band-choice-text">{workspaceLabel}</span>
                <Icon name="chevron-down" size={13} />
              </>
            }
            triggerClassName="band-choice"
            placement="bottom start"
            className="band-popover"
          >
            {(close) => (
              <WorkspaceSelector
                workspaceKey={route.workspaceKey}
                onChange={(key) => {
                  close();
                  onChangeWorkspace(key);
                }}
                onManage={
                  onManageWorkspaces
                    ? () => {
                        close();
                        onManageWorkspaces();
                      }
                    : undefined
                }
              />
            )}
          </ControlPopover>
          <span aria-hidden="true" className="band-separator">
            /
          </span>
          <ControlPopover
            label={`Application: ${application.name}`}
            trigger={
              <>
                <HueTile hue={applicationHue(model, application.key)} icon={application.icon} size={18} />
                <span className="band-choice-text">{application.name}</span>
                <Icon name="chevron-down" size={13} />
              </>
            }
            triggerClassName="band-choice"
            placement="bottom start"
            className="band-popover"
          >
            {(close) => (
              <nav className="band-applications" aria-label="Applications">
                <ApplicationButtons
                  model={model}
                  currentApplicationKey={application.key}
                  onSelectApplication={(item) => {
                    close();
                    onSelectApplication(item);
                  }}
                />
              </nav>
            )}
          </ControlPopover>
          <ControlPopover
            label={`Data: ${contextName}`}
            trigger={
              <>
                {listing ? (
                  <span className="band-choice-text">{contextName}</span>
                ) : (
                  <StatusPill tone={tone}>{status}</StatusPill>
                )}
                <Icon name="chevron-down" size={13} />
              </>
            }
            triggerClassName="band-choice band-choice-context"
            placement="bottom end"
            className="band-popover"
          >
            {(close) => (
              <>
                {!listing && note && <p className="band-note">{note}</p>}
                {switcher(close)}
              </>
            )}
          </ControlPopover>
        </div>
      ) : (
        <div className="band-context">
          <div role="group" className="shell-context" aria-label="Current context">
            <span>{workspaceLabel}</span>
            <span aria-hidden="true"> / </span>
            <span>{application.name}</span>
            {!listing && <StatusPill tone={tone}>{status}</StatusPill>}
          </div>
          {!listing && note && <span className="band-note">{note}</span>}
          {switcher()}
        </div>
      )}
      {contextActions && <div className="band-actions">{contextActions}</div>}
    </div>
  );
}

/**
 * Keeps the band's height in `--band-height` on the page while it is shown: what it covers at the
 * top once the page scrolls, which a list's height leaves room for (`ui/ScrollWindow`).
 */
function publishBandHeight(band: HTMLElement) {
  const root = document.documentElement;
  const publish = () => root.style.setProperty("--band-height", `${Math.round(band.getBoundingClientRect().height)}px`);
  publish();
  const observer = typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(publish);
  observer?.observe(band);
  return () => {
    observer?.disconnect();
    root.style.removeProperty("--band-height");
  };
}
