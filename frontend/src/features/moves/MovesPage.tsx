/**
 * Settings › Data operations › Moves (0.11 X4, D138): the mappings saved between two models, each
 * opening the move editor for two workspaces running them, and the recent moves, each naming its
 * workspaces, copy or move, its state and the change sets it opened. New move… chooses the two
 * workspaces and a mapping, or proposes a new one (D139). Without background jobs or model
 * administration the mappings are listed read-only (D146).
 */

import { useState } from "react";
import { api } from "@/api/client";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { routePath } from "@/routing/routes";
import type { Job, ModelMappingSummary, RouteState, Workspace } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { LogFoot, SettingsEmpty, SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { STATE } from "@/ui/jobText";
import { settingsHead } from "@/ui/settingsNavigation";
import { useCapabilities } from "@/state/useSystem";
import { DeleteAction } from "@/ui/DeleteAction";
import { useHoldsGroup } from "@/app/useMe";
import { NewMoveDialog } from "@/ui/NewMoveDialog";
import { moveAbility } from "@/lib/moveAbility";

const label = (workspaces: Workspace[], key: string) => workspaces.find((item) => item.key === key)?.label ?? key;

/** Two active workspaces running a mapping's two models, the first of each in key order. */
function workspacesFor(mapping: ModelMappingSummary, workspaces: Workspace[]) {
  const from = workspaces.find((item) => item.model.releaseKey === mapping.sourceModelKey);
  const to = workspaces.find((item) => item.model.releaseKey === mapping.targetModelKey && item.key !== from?.key);
  return from && to ? { from: from.key, to: to.key } : undefined;
}

export function MovesPage({ onNavigate }: { onNavigate: (route: RouteState) => void }) {
  const mappings = useCursorFeed((cursor) => api.modelMappings({ cursor }), []);
  const moves = useCursorFeed((cursor) => api.moveJobs(cursor), []);
  const workspaceFeed = useCursorFeed((cursor) => api.workspaces({ cursor }), []);
  const workspaces = workspaceFeed.items;
  const { capabilities } = useCapabilities();
  const ability = moveAbility(capabilities);
  // A mapping is deleted by those who copy and move records; others are not offered it.
  const canDelete = useHoldsGroup("copy-move") === true;
  const [creating, setCreating] = useState(false);
  // Each step of the editor replaces its dry run; the cancelled ones say nothing (D140).
  const listed = moves.items.filter((job) => job.state !== "cancelled" && job.state !== "expired");

  const editor = (mappingKey: string, from: string, to: string, jobId?: string): RouteState => ({
    kind: "settings",
    page: "moves",
    move: { mappingKey, from, to, ...(jobId ? { jobId } : {}) },
  });
  const link = (route: RouteState) => ({ href: routePath(route), onNavigate: () => onNavigate(route) });

  const head = settingsHead("moves");

  return (
    <SettingsLayout
      {...head}
      title="Copy and move"
      description="Records of one workspace copied or moved into a workspace whose model differs, through a mapping from one model to the other. Every move is a dry run of every item first, and loads into a change set of the target for review; nothing reaches either workspace until a change set is published."
      actions={
        ability.canMap && (
          <button type="button" className="primary" onClick={() => setCreating(true)}>
            New copy or move…
          </button>
        )
      }
    >
      {!ability.canMap && capabilities && (
        <Notice tone="info" title="Copying and moving are read-only here">
          {ability.reason}
        </Notice>
      )}
      <SettingsGroup
        stacked
        title="Mappings"
        description="Each mapping says what the records of one model become in another."
      >
        <SettingsPanel>
          {mappings.error ? (
            <InlineError message={mappings.error} onRetry={mappings.retry} />
          ) : mappings.loading && mappings.items.length === 0 ? (
            <Skeleton label="Loading the mappings" lines={3} />
          ) : mappings.items.length === 0 ? (
            <SettingsEmpty icon="swap" hue={head.hue}>
              No mapping yet. New copy or move… proposes one between the models of two workspaces.
            </SettingsEmpty>
          ) : (
            <SettingsTable
              label="Mappings"
              columns={[
                "Mapping",
                "From model",
                "To model",
                { num: "Version" },
                "Updated",
                ...(canDelete ? ["Actions"] : []),
              ]}
            >
              {mappings.items.map((mapping) => {
                const pair = workspacesFor(mapping, workspaces);
                return (
                  <tr key={mapping.key}>
                    <th scope="row" data-label="Mapping">
                      {pair ? (
                        <RouteLink {...link(editor(mapping.key, pair.from, pair.to))}>{mapping.name}</RouteLink>
                      ) : (
                        mapping.name
                      )}
                      <div className="muted mono">{mapping.key}</div>
                    </th>
                    <td data-label="From model">{mapping.sourceModelKey}</td>
                    <td data-label="To model">{mapping.targetModelKey}</td>
                    <td data-label="Version" className="num">
                      {mapping.version}
                    </td>
                    <td data-label="Updated" className="when" title={formatServerTime(mapping.updatedAt)}>
                      {formatServerDayTime(mapping.updatedAt)}
                    </td>
                    {canDelete && (
                      <td data-label="Actions">
                        <DeleteAction
                          label="Delete…"
                          title={`Delete the mapping ${mapping.name}?`}
                          confirmLabel="Delete the mapping"
                          onDelete={async () => {
                            await api.deleteModelMapping(mapping.key, mapping.version);
                            mappings.setItems((items) => items.filter((item) => item.key !== mapping.key));
                          }}
                        >
                          The mapping from {mapping.sourceModelKey} to {mapping.targetModelKey} is deleted with its
                          history and proposals. Copies and moves already made stay as they are; a new one needs a new
                          mapping.
                        </DeleteAction>
                      </td>
                    )}
                  </tr>
                );
              })}
            </SettingsTable>
          )}
          {mappings.items.length > 0 && !mappings.error && (
            <LogFoot
              shown={mappings.items.length}
              noun="mappings"
              onMore={mappings.hasMore ? mappings.loadMore : undefined}
              loading={mappings.loading}
            />
          )}
        </SettingsPanel>
      </SettingsGroup>
      <SettingsGroup
        stacked
        title="Recent copies and moves"
        description="Copies, moves and dry runs waiting to start, of every workspace, newest first. A dry run the editor replaced after a step is not listed."
      >
        <SettingsPanel>
          {moves.error ? (
            <InlineError message={moves.error} onRetry={moves.retry} />
          ) : moves.loading && moves.items.length === 0 ? (
            <Skeleton label="Loading copies and moves" lines={3} />
          ) : listed.length === 0 ? (
            <SettingsEmpty icon="swap" hue={head.hue}>
              Nothing copied or moved yet.
            </SettingsEmpty>
          ) : (
            <SettingsTable
              label="Recent copies and moves"
              columns={["Workspaces", "Operation", "State", "Change sets", "Created"]}
            >
              {listed.map((job) => (
                <MoveJobRow key={job.id} job={job} workspaces={workspaces} link={link} editor={editor} />
              ))}
            </SettingsTable>
          )}
          {listed.length > 0 && !moves.error && (
            <LogFoot
              shown={listed.length}
              noun="copies and moves"
              onMore={moves.hasMore ? moves.loadMore : undefined}
              loading={moves.loading}
            />
          )}
        </SettingsPanel>
      </SettingsGroup>
      {creating && (
        <NewMoveDialog
          onClose={() => setCreating(false)}
          onOpened={(mappingKey, from, to) => {
            setCreating(false);
            onNavigate(editor(mappingKey, from, to));
          }}
        />
      )}
    </SettingsLayout>
  );
}

function MoveJobRow({
  job,
  workspaces,
  link,
  editor,
}: {
  job: Job;
  workspaces: Workspace[];
  link: (route: RouteState) => { href: string; onNavigate: () => void };
  editor: (mappingKey: string, from: string, to: string, jobId?: string) => RouteState;
}) {
  const from = String(job.parameters.sourceWorkspaceKey ?? "");
  const to = String(job.parameters.targetWorkspaceKey ?? job.workspaceKey);
  const mappingKey = String(job.parameters.mappingKey ?? "");
  const state = STATE[job.state];
  const opened = [job.move?.targetChangeSetId, job.move?.sourceChangeSetId].filter(Boolean).length;
  const title = `${label(workspaces, from)} → ${label(workspaces, to)}`;
  return (
    <tr>
      <th scope="row" data-label="Workspaces">
        {job.state === "awaiting_confirmation" && mappingKey ? (
          <RouteLink {...link(editor(mappingKey, from, to, job.id))}>{title}</RouteLink>
        ) : (
          <RouteLink {...link({ kind: "settings", page: "jobs", jobId: job.id })}>{title}</RouteLink>
        )}
      </th>
      <td data-label="Operation">{job.parameters.mode === "move" ? "Move" : "Copy"}</td>
      <td data-label="State">
        <StatusPill tone={state.tone}>
          {job.state === "awaiting_confirmation" ? "Dry run, not started" : state.label}
        </StatusPill>
      </td>
      <td data-label="Change sets">{opened ? `${opened} opened` : "None"}</td>
      <td data-label="Created" className="when" title={formatServerTime(job.createdAt)}>
        {formatServerDayTime(job.createdAt)}
      </td>
    </tr>
  );
}
