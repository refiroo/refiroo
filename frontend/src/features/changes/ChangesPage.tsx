/**
 * One person's or client's changes across workspaces (0.12 Z6, D340–D345; drawn from the Settings family's parts
 * since 0.17 ST1, with a way back as its first line): their name, three
 * filters (a workspace, a kind of change, a period) and their changes newest first as a timeline
 * grouped by day, 50 at a time. Each title opens what it changed while it exists. Outside any
 * workspace, as Home is: each entry is named from its own workspace's model by the server.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { TopBar } from "@/app/TopBar";
import { ShellFrame } from "@/app/ShellFrame";
import { useMe } from "@/state/useMe";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { emptyModel } from "@/model/emptyModel";
import type { Hue } from "@/model/hues";
import { HOME } from "@/routing/routes";
import type {
  ChangeEntry,
  ChangeEntryKind,
  ChangePeriod,
  ChangesRoute,
  EngineModel,
  OwnWorkspace,
  RouteState,
} from "@/types";
import { InlineError } from "@/ui/InlineError";
import { ChangeTitle } from "@/ui/ChangeTitle";
import { SettingsLayout } from "@/ui/SettingsLayout";
import {
  hueOf,
  ItemHeader,
  LogFoot,
  NameMark,
  SettingsEmpty,
  SettingsGroup,
  SettingsPanel,
  SettingsTile,
} from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { Timeline } from "@/ui/Timeline";
import { Trail } from "@/ui/Trail";
import { WorkspaceField } from "@/ui/WorkspaceField";
import {
  KIND_LABELS,
  PERIOD_LABELS,
  byDay,
  changeSummary,
  changeWhere,
  changesHeading,
  draftStepsTitle,
  groupDraftSteps,
  changesSubtitle,
  periodSince,
} from "@/ui/changeText";

type Navigate = (route: RouteState) => void;

/** The colour of each kind of change, on its marker in the line (0.17 ST1, PP-D67). */
const KIND_HUES: Record<ChangeEntryKind, Hue> = {
  record: 2,
  relationship: 3,
  "change-set": 5,
  publication: 7,
  model: 1,
};

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
  const hue = name ? hueOf(name) : undefined;

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
      <div className="changes-page">
        <SettingsLayout
          trail={
            <Trail
              back={{
                label: "Back",
                onClick: () => (window.history.length > 1 ? window.history.back() : onNavigate(HOME)),
              }}
            />
          }
          header={
            <ItemHeader
              hue={hue}
              lead={name ? <NameMark name={name} size={64} /> : <SettingsTile icon="activity" hue={hue} size={48} />}
              title={<h1 id="changes-title">{changesHeading(self, name)}</h1>}
              meta={changesSubtitle(self, kind)}
            />
          }
        >
          <SettingsGroup
            stacked
            title="Changes"
            description="Each line opens what it changed while that exists. The marker's colour is the kind of change."
            tools={
              <div className="changes-filters" role="group" aria-label="Filter the changes">
                <WorkspaceField
                  toolbar
                  items={workspaces}
                  allOption="All workspaces"
                  value={route.inWorkspace ?? ""}
                  onChange={(key) => filter({ inWorkspace: key || undefined })}
                />
                <label className="toolbar-field">
                  What
                  <select
                    value={route.what ?? ""}
                    onChange={(event) =>
                      filter({ what: (event.target.value || undefined) as ChangeEntryKind | undefined })
                    }
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
                    onChange={(event) =>
                      filter({ period: (event.target.value || undefined) as ChangePeriod | undefined })
                    }
                  >
                    {Object.entries(PERIOD_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            }
          >
            {feed.error ? (
              <InlineError message={feed.error} onRetry={feed.retry} />
            ) : feed.loading && !feed.items.length ? (
              <Skeleton label="Loading the changes" lines={6} />
            ) : !feed.items.length ? (
              <SettingsPanel>
                <SettingsEmpty icon="activity" hue={hue}>
                  {narrowed
                    ? "No change matches these filters."
                    : self
                      ? "You have not changed anything in the workspaces you can read yet."
                      : `No changes by ${name ?? "them"} in the workspaces you can read. Changes in other workspaces are shown to the people who can read them.`}
                </SettingsEmpty>
              </SettingsPanel>
            ) : (
              <>
                {byDay(feed.items).map((day) => (
                  <section key={day.day} className="settings-panel changes-day-panel" aria-label={day.day}>
                    <h2 className="changes-day">{day.day}</h2>
                    <Timeline
                      entries={groupDraftSteps(day.entries).map((item) => {
                        if (item.kind === "entry") return timelineEntry(item.entry, firstApplication, onNavigate);
                        const newest = item.entries[0];
                        return {
                          key: item.key,
                          title: draftStepsTitle(item.entries.length, item.name),
                          at: newest.occurredAt,
                          hue: KIND_HUES.model,
                          after: changeWhere(newest).map((part) => ` · ${part}`),
                          details: (
                            <Timeline
                              label="The steps on the draft"
                              entries={item.entries.map((entry) => timelineEntry(entry, firstApplication, onNavigate))}
                            />
                          ),
                        };
                      })}
                    />
                  </section>
                ))}
                <SettingsPanel>
                  <LogFoot
                    shown={feed.items.length}
                    noun="changes"
                    onMore={feed.hasMore ? feed.loadMore : undefined}
                    loading={feed.loading}
                  />
                </SettingsPanel>
              </>
            )}
          </SettingsGroup>
        </SettingsLayout>
      </div>
    </ShellFrame>
  );
}

/** One step as a timeline line: its title (a link where it can be opened), summary, time and place. */
function timelineEntry(
  entry: ChangeEntry,
  firstApplication: ReadonlyMap<string, string | undefined>,
  onNavigate: Navigate,
) {
  return {
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
    hue: KIND_HUES[entry.kind],
    after: changeWhere(entry).map((part) => ` · ${part}`),
  };
}
