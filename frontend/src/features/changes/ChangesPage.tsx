/**
 * One person's or client's changes across workspaces (0.12 Z6, D340–D345): their name, three
 * filters (a workspace, a kind of change, a period) and their changes newest first as a timeline
 * grouped by day, 50 at a time. Each title opens what it changed while it exists. Outside any
 * workspace, as Home is: each entry is named from its own workspace's model by the server.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { TopBar } from "@/app/TopBar";
import { ShellFrame } from "@/app/ShellFrame";
import { useMe } from "@/app/useMe";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { emptyModel } from "@/model/emptyModel";
import { HOME, routePath } from "@/routing/routes";
import type {
  ChangeEntry,
  ChangeEntryKind,
  ChangePeriod,
  ChangesRoute,
  EngineModel,
  OwnWorkspace,
  RouteState,
} from "@/types";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { RouteLink } from "@/ui/RouteLink";
import { Skeleton } from "@/ui/Skeleton";
import { Timeline } from "@/ui/Timeline";
import {
  KIND_LABELS,
  PERIOD_LABELS,
  byDay,
  changeSummary,
  changeTarget,
  changeTitle,
  changeWhere,
  changesHeading,
  changesSubtitle,
  periodSince,
} from "./changeText";

type Navigate = (route: RouteState) => void;

export function ChangesPage({
  model,
  route,
  onNavigate,
}: {
  model: EngineModel;
  route: ChangesRoute;
  onNavigate: Navigate;
}) {
  const me = useMe();
  const [workspaces, setWorkspaces] = useState<OwnWorkspace[]>([]);
  useEffect(() => {
    let active = true;
    api.myWorkspaces().then(
      (loaded) => active && setWorkspaces(loaded),
      () => undefined,
    );
    return () => {
      active = false;
    };
  }, []);
  // The period's start is fixed when it is chosen: every page of one list asks the same `since`,
  // or the next page's cursor would not match its filters.
  const since = useMemo(() => periodSince(route.period), [route.period]);
  const feed = useCursorFeed<ChangeEntry>(
    (cursor) =>
      api.changes({
        actorId: route.actorId,
        workspaceKey: route.inWorkspace,
        kinds: route.what ? [route.what] : undefined,
        since,
        cursor,
      }),
    [route.actorId, route.inWorkspace, route.what, since],
  );
  const self = me?.id === route.actorId;
  const actor = feed.items.find((item) => item.actor && item.actor.kind !== "engine")?.actor;
  const name = actor && actor.kind !== "engine" ? actor.name : route.actorName;
  const kind = actor && actor.kind !== "engine" ? actor.kind : undefined;
  const firstApplication = new Map(workspaces.map((item) => [item.key, item.applications[0]?.key]));
  const filter = (change: Partial<ChangesRoute>) => onNavigate({ ...route, ...change });
  const narrowed = Boolean(route.inWorkspace || route.what || route.period);
  const bar = { ...emptyModel(), product: model.product };

  return (
    <ShellFrame
      topBar={
        <TopBar
          model={bar}
          onHome={() => onNavigate(HOME)}
          onSelectApplication={() => undefined}
          onNavigate={onNavigate}
        />
      }
      main={{ className: "home" }}
    >
      <div className="home-page changes-page">
        <section className="account-panel home-welcome changes-hero" aria-labelledby="changes-title">
          <p className="home-eyebrow">Changes</p>
          <h1 id="changes-title">{changesHeading(self, name)}</h1>
          <p className="home-summary">{changesSubtitle(self, kind)}</p>
        </section>
        <div className="changes-filters" role="group" aria-label="Filter the changes">
          <label className="toolbar-field">
            Workspace
            <select
              value={route.inWorkspace ?? ""}
              onChange={(event) => filter({ inWorkspace: event.target.value || undefined })}
            >
              <option value="">All workspaces</option>
              {workspaces.map((workspace) => (
                <option key={workspace.key} value={workspace.key}>
                  {workspace.label}
                </option>
              ))}
            </select>
          </label>
          <label className="toolbar-field">
            What
            <select
              value={route.what ?? ""}
              onChange={(event) => filter({ what: (event.target.value || undefined) as ChangeEntryKind | undefined })}
            >
              {Object.entries(KIND_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="toolbar-field">
            Period
            <select
              value={route.period ?? ""}
              onChange={(event) => filter({ period: (event.target.value || undefined) as ChangePeriod | undefined })}
            >
              {Object.entries(PERIOD_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && !feed.items.length ? (
          <Skeleton label="Loading the changes" lines={6} />
        ) : !feed.items.length ? (
          <EmptyState>
            {narrowed
              ? "No change matches these filters."
              : self
                ? "You have not changed anything in the workspaces you can read yet."
                : `No changes by ${name ?? "them"} in the workspaces you can read. Changes in other workspaces are shown to the people who can read them.`}
          </EmptyState>
        ) : (
          <>
            {byDay(feed.items).map((day) => (
              <section key={day.day} className="home-section" aria-label={day.day}>
                <h2 className="changes-day">{day.day}</h2>
                <div className="account-panel">
                  <Timeline
                    entries={day.entries.map((entry) => ({
                      key: entry.id,
                      title: (
                        <ChangeTitle
                          entry={entry}
                          application={entry.workspace ? firstApplication.get(entry.workspace.key) : undefined}
                          onNavigate={onNavigate}
                        />
                      ),
                      summary: changeSummary(entry) || undefined,
                      at: entry.occurredAt,
                      after: changeWhere(entry).map((part) => ` · ${part}`),
                    }))}
                  />
                </div>
              </section>
            ))}
            {feed.hasMore && (
              <div>
                <button type="button" className="secondary" disabled={feed.loading} onClick={feed.loadMore}>
                  {feed.loading ? "Loading…" : "Load more"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </ShellFrame>
  );
}

/** An entry's title, a link to what it changed while that can be opened. */
export function ChangeTitle({
  entry,
  application,
  onNavigate,
}: {
  entry: ChangeEntry;
  application: string | undefined;
  onNavigate: Navigate;
}) {
  const title = changeTitle(entry);
  const target = changeTarget(entry, application);
  if (!target) return <>{title}</>;
  return (
    <RouteLink className="changes-link" href={routePath(target)} onNavigate={() => onNavigate(target)}>
      {title}
    </RouteLink>
  );
}
