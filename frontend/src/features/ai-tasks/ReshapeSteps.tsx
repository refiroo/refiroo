/**
 * What is left to the person after an assistant task that moved records between types (0.16 AP12, boards 3
 * and 4). Whole types become others by one migration, which the existing migration page previews and the
 * person confirms. Part of a type goes in three steps: activate the release holding both shapes, review and
 * publish the change set, and activate the final release, which removes the emptied types. Each step is
 * shown as something to do only when it can be done; a person without Model release is told who can.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { count } from "@/features/settings/limits";
import type { AiTask, ChangeSet, RouteState, WorkspaceModel } from "@/types";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { StatusPill } from "@/ui/StatusPill";

/** The steps of a part-of-a-type reshaping, from what the workspace runs and whether the change set is open. */
export type StepState = "done" | "next" | "later";

export function reshapeStates(
  workspace: Pick<WorkspaceModel, "releaseId"> | undefined,
  changeSet: Pick<ChangeSet, "modelReleaseId"> | null | undefined,
  finalReleaseId: string,
): [StepState, StepState, StepState] {
  if (!workspace || changeSet === undefined) return ["later", "later", "later"];
  const finished = workspace.releaseId === finalReleaseId;
  // A published change set is gone; it could only be published on the release holding both.
  const published = changeSet === null;
  const added = finished || published || workspace.releaseId === changeSet?.modelReleaseId;
  return [
    added ? "done" : "next",
    finished || published ? "done" : added ? "next" : "later",
    finished ? "done" : published ? "next" : "later",
  ];
}

function State({ state }: { state: StepState }) {
  return state === "done" ? (
    <StatusPill tone="success">Done</StatusPill>
  ) : state === "next" ? (
    <StatusPill tone="draft">Next</StatusPill>
  ) : null;
}

export function ReshapeSteps({
  task,
  workspaceLabel,
  canRelease,
  review,
  onNavigate,
}: {
  task: AiTask;
  workspaceLabel: string;
  /** Model release in the task's workspace: the person who may activate and migrate. */
  canRelease: boolean;
  /** The change set's review, when an application to show it in is known. */
  review?: RouteState;
  onNavigate: (route: RouteState) => void;
}) {
  const result = task.result;
  const [workspace, setWorkspace] = useState<WorkspaceModel>();
  const [changeSet, setChangeSet] = useState<ChangeSet | null>();
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState(false);
  const changeSetId = result?.changeSetId ?? undefined;
  const workspaceKey = task.workspaceKey;

  const load = useCallback(
    () =>
      Promise.all([
        api.workspaceModel(workspaceKey),
        changeSetId
          ? api.changeSet(changeSetId).catch((cause: unknown) => {
              // Published or discarded: the change set is gone.
              if (isApiError(cause, "CHANGE_SET_NOT_FOUND")) return null;
              throw cause;
            })
          : Promise.resolve(undefined),
      ]),
    [workspaceKey, changeSetId],
  );

  const reshaped = !!result?.migration || !!result?.thenReleaseId;
  useEffect(() => {
    if (!reshaped) return;
    let active = true;
    const read = () =>
      load()
        .then(([model, held]) => {
          if (!active) return;
          setWorkspace(model);
          setChangeSet(held);
        })
        .catch((cause: unknown) => active && setProblem(errorMessage(cause)));
    void read();
    // The steps are done on other pages: the page reads again when the person comes back to it.
    window.addEventListener("focus", read);
    return () => {
      active = false;
      window.removeEventListener("focus", read);
    };
  }, [load, reshaped]);

  if (!result) return null;
  const migration = result.migration;
  const moves = task.design?.moves ?? [];

  if (migration) {
    const finished = workspace?.releaseId === migration.releaseId;
    const preview = async () => {
      setPending(true);
      setProblem("");
      try {
        const current = await api.workspaceModel(workspaceKey);
        const job = await api.startWorkspaceMigration(workspaceKey, {
          targetReleaseId: migration.releaseId,
          expectedVersion: current.version,
          typeMappings: migration.typeMappings,
        });
        onNavigate({
          kind: "settings",
          page: "model",
          migrationJobId: job.id,
          forWorkspace: workspaceKey,
          journey: { kind: "aiTask", taskId: task.id },
        });
      } catch (cause) {
        setProblem(errorMessage(cause));
        setPending(false);
      }
    };
    return (
      <Section title="Move the records to the new model">
        {finished ? (
          <Notice tone="success">
            {workspaceLabel} runs the new model, and its records are under their new types.
          </Notice>
        ) : (
          <p>
            Nothing has changed yet. The migration moves every record to its new type, keeping its ID, values,
            relationships and history. It goes live when you confirm, with no change set to review: each change is in
            the records&apos; history.
          </p>
        )}
        {moves.length > 0 && (
          <ul className="task-next" aria-label="What becomes what">
            {moves.map((move) => (
              <li key={move.from}>
                {move.fromName} becomes <strong>{move.toName}</strong> ({count(move.records)}{" "}
                {move.records === 1 ? "record" : "records"})
              </li>
            ))}
          </ul>
        )}
        {problem && <Notice tone="error">{problem}</Notice>}
        {!finished &&
          (canRelease ? (
            <div className="task-actions">
              <button type="button" className="primary" disabled={pending} onClick={() => void preview()}>
                Preview the migration
              </button>
            </div>
          ) : (
            <p className="admin-hint">
              Someone who holds Model release in {workspaceLabel} previews and confirms the migration from Settings ›
              Model.
            </p>
          ))}
      </Section>
    );
  }

  const finalReleaseId = result.thenReleaseId;
  if (!finalReleaseId) return null;
  const [added, published, removed] = reshapeStates(workspace, changeSet, finalReleaseId);
  const bothReleaseId = changeSet?.modelReleaseId;
  const records = result.counts?.applied;
  const openRelease = (releaseId: string) =>
    canRelease ? (
      <div className="task-actions">
        <button
          type="button"
          className="primary"
          onClick={() => onNavigate({ kind: "settings", page: "model", releaseId })}
        >
          Open the release
        </button>
      </div>
    ) : (
      <p className="admin-hint">Someone who holds Model release in {workspaceLabel} does this step.</p>
    );
  return (
    <Section
      title="Three steps are yours"
      description="The assistant prepared the move in a change set. Each step is shown when it can be done."
    >
      {problem && <Notice tone="error">{problem}</Notice>}
      <Section
        title={
          <>
            1. Add the new types to the workspace <State state={added} />
          </>
        }
        headingLevel={3}
      >
        <p>
          {added === "done"
            ? `${workspaceLabel} runs a release that has the new types beside the old.`
            : `Activate the release that holds both shapes in ${workspaceLabel}. No record moves.`}
        </p>
        {added === "next" && bothReleaseId && openRelease(bothReleaseId)}
      </Section>
      <Section
        title={
          <>
            2. Review and publish the change set <State state={published} />
          </>
        }
        headingLevel={3}
      >
        <p>
          {records !== undefined ? `${count(records)} records change type and keep their IDs. ` : ""}
          Live data is unchanged until it is published, with the workspace&apos;s approval rules as usual.
        </p>
        {published === "next" && review && (
          <div className="task-actions">
            <button type="button" className="primary" disabled={pending} onClick={() => onNavigate(review)}>
              Review the change set
            </button>
          </div>
        )}
      </Section>
      <Section
        title={
          <>
            3. Remove the emptied types <State state={removed} />
          </>
        }
        headingLevel={3}
      >
        <p>
          {removed === "done"
            ? `${workspaceLabel} runs the release you accepted.`
            : `After publishing, activate the release you accepted: the old types go once they hold no record. A record added to one meanwhile stops this, and names the record.`}
        </p>
        {removed === "next" && openRelease(finalReleaseId)}
      </Section>
    </Section>
  );
}
