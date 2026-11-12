/**
 * The data-context band at the top of the content (ADR-039, Track U U2): which data the page reads
 * and edits. On desktop it no longer names the workspace and the application, which the sidebar and
 * the top bar already say (0.17 SH1, PP-D33): it is one row, the context's pill, its one sentence
 * and the switch at the right end. A change set's row holds its name, its change count and state
 * (`contextActions`) in place of the sentence. Live is a soft green strip with
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

import { useCallback, useLayoutEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
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
import type { ActionMenuItem } from "@/ui/ActionMenu";
import { ApplicationButtons } from "./TopBar";

/** Said wherever a retired workspace is shown: its records can be read, not changed. */
export const RETIRED_WORKSPACE_TEXT =
  "This workspace is retired. Runtime data and history remain available, but changes are disabled.";

/** The band's own short line for a retired workspace; the notice below it says the rest. */
export const RETIRED_BAND_TEXT = "Retired: read only.";

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
  workspaceActions = [],
  permissionNote,
  ownChangeSet,
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
  /** The workspace's ⋯ menu, in the workspace choice on a phone (0.16 WM1). */
  workspaceActions?: readonly ActionMenuItem[];
  /** What the person may do here, in place of the line about edits (0.12 Z5, D322). */
  permissionNote?: string;
  /** The way into the person's own change set from live data (D324). */
  ownChangeSet?: ReactNode;
}) {
  const phone = useMediaQuery(PHONE_WIDTH);
  const [band, setBand] = useState<HTMLDivElement | null>(null);
  // The context's actions are mounted once, in a holder of their own that is moved into the row a wide window
  // draws them in or the line a phone does: a dialog they have open stays open when the window crosses the
  // phone width (two mounting places closed it).
  const [actionsHolder] = useState(() => {
    const holder = document.createElement("div");
    holder.style.display = "contents";
    return holder;
  });
  const placeActions = useCallback(
    (element: HTMLDivElement | null) => {
      if (element) element.appendChild(actionsHolder);
    },
    [actionsHolder],
  );
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
    permissionNote ??
    (tone === "live"
      ? "Edits apply immediately in this workspace."
      : tone === "changeSet"
        ? changeSet
          ? "Edits stay in this change set until it is published."
          : undefined
        : "Read-only. A publication's records never change.");
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
                actions={workspaceActions.map((item) => ({
                  ...item,
                  onAction: () => {
                    close();
                    item.onAction();
                  },
                }))}
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
            {listing ? <span>{contextName}</span> : <StatusPill tone={tone}>{status}</StatusPill>}
          </div>
          {/* A change set's own bar says its name and count in place of the sentence (PP-D33). */}
          {!listing && note && !(tone === "changeSet" && contextActions) && <span className="band-note">{note}</span>}
          {/* The context's own bar is part of the one row: a change set's name, count and actions. */}
          {(contextActions || ownChangeSet) && <div className="band-actions band-actions-inline" ref={placeActions} />}
          {switcher()}
        </div>
      )}
      {phone && (contextActions || ownChangeSet) && <div className="band-actions" ref={placeActions} />}
      {(contextActions || ownChangeSet) &&
        createPortal(
          <>
            {contextActions}
            {ownChangeSet}
          </>,
          actionsHolder,
        )}
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
