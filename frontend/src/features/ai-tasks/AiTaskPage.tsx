/**
 * One assistant task's page (0.16 AP6a, `/settings/ai-tasks/{id}`): loading a workbook with the AI
 * assistant. It follows the task while a job runs (reading, checking, loading), shows the proposed
 * model, what the load would do per sheet after one check of every row, and where the load went. Live
 * data is never changed from here; the load lands in a change set. A task recorded by an older
 * version that rests in a state this page no longer draws reads as stopped.
 */

import { useEffect, useRef, useState } from "react";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { useWorkspacePermissions, holds } from "@/features/security/permissions";
import { changeReviewFor, routePath } from "@/routing/routes";
import type { AiTask, EngineModel, JourneyRef, RouteState } from "@/types";
import { Breadcrumbs } from "@/ui/Breadcrumbs";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { DesignCheckView } from "./DesignCheckView";
import { DesignView } from "./DesignView";
import type { LoadChoice } from "./LoadFoot";
import { ModelProposal } from "./ModelProposal";
import { SessionProgress } from "./SessionProgress";
import { LoadedView } from "./LoadedView";
import { taskApplicationKey } from "./aiTaskJourney";
import { rememberModelReviewed } from "./AiTaskJourneyBar";
import { isDesignCheck, runningText, taskTitle } from "./aiTaskText";
import { useAiTask } from "./useAiTask";

const CONFLICT = "The task changed while you were working, so the page shows its latest state. Check it and try again.";

export function AiTaskPage({
  taskId,
  onNavigate,
  onOpenWorkspace,
  onActiveModelChange,
}: {
  taskId: string;
  onNavigate: (route: RouteState) => void;
  onOpenWorkspace: (workspaceKey: string) => void;
  /** The load activated a new release in the task's workspace: the shown model is read again. */
  onActiveModelChange?: (workspaceKey: string) => void;
}) {
  const followed = useAiTask(taskId);
  const { task } = followed;
  const releaseId = task?.result?.releaseId;
  const announced = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (!task || !releaseId || announced.current === releaseId) return;
    announced.current = releaseId;
    onActiveModelChange?.(task.workspaceKey);
  }, [task, releaseId, onActiveModelChange]);
  const permissions = useWorkspacePermissions(task?.workspaceKey);
  // A load onto a release not active yet: the change set's own model says which application shows it.
  const [ownApplication, setOwnApplication] = useState<string>();
  const loadedChangeSet = task?.result?.changeSetId;
  useEffect(() => {
    if (!task || !loadedChangeSet || taskApplicationKey(task)) return;
    let active = true;
    api
      .model({ workspaceKey: task.workspaceKey, changeSetId: loadedChangeSet })
      .then((pinned) => active && setOwnApplication(pinned.applications[0]?.key))
      .catch(() => undefined);
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadedChangeSet, task?.workspaceKey]);
  const [label, setLabel] = useState<string>();
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState("");
  const [conflict, setConflict] = useState(false);
  const [jobError, setJobError] = useState("");
  // The design shows the model's names for types and attributes, never their keys.
  const [model, setModel] = useState<EngineModel>();

  const workspaceKey = task?.workspaceKey;
  useEffect(() => {
    if (!workspaceKey) return;
    let current = true;
    api
      .workspace(workspaceKey)
      .then((workspace) => current && setLabel(workspace.label))
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [workspaceKey]);

  useEffect(() => {
    if (!workspaceKey) return;
    let current = true;
    api
      .model({ workspaceKey })
      .then((loaded) => current && setModel(loaded))
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [workspaceKey]);

  // A failed or cancelled task says why: the job's own error.
  const ended = task && (task.state === "failed" || task.state === "cancelled") ? task : undefined;
  useEffect(() => {
    if (!ended?.jobId) return;
    let current = true;
    api
      .job(ended.jobId)
      .then((job) => current && setJobError(job.error?.message ?? ""))
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [ended?.jobId]);

  const workspace: RouteState | undefined = workspaceKey
    ? { kind: "settings", page: "workspaces", workspaceKey }
    : undefined;
  const trail = (
    <Breadcrumbs
      items={[
        !!workspace &&
          !!workspaceKey && {
            key: "workspace",
            content: (
              <RouteLink href={routePath(workspace)} onNavigate={() => onNavigate(workspace)}>
                {label ?? workspaceKey}
              </RouteLink>
            ),
          },
        { key: "page", content: "Load a workbook", current: true },
      ]}
    />
  );

  async function write(action: () => Promise<AiTask>) {
    setPending(true);
    setProblem("");
    setConflict(false);
    try {
      followed.set(await action());
    } catch (cause) {
      if (isApiError(cause, "AI_TASK_VERSION_CONFLICT")) {
        setConflict(true);
        await followed.reload();
      } else setProblem(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  if (!task) {
    return (
      <SettingsLayout trail={trail} title="Load a workbook">
        {followed.error ? (
          <InlineError message={followed.error} onRetry={followed.retry} />
        ) : (
          <Skeleton label="Loading the task" />
        )}
      </SettingsLayout>
    );
  }

  const journey: JourneyRef = { kind: "aiTask", taskId: task.id };
  const application = taskApplicationKey(task) ?? ownApplication;
  // The change set opens with the journey carried, so its bar shows there.
  const review =
    task.result && application
      ? { ...changeReviewFor(application, task.workspaceKey, task.result.changeSetId), journey }
      : undefined;
  const design = task.design;
  const designCheck = isDesignCheck(task.check) ? task.check : undefined;
  const run = (choice: LoadChoice) =>
    void write(() => ai.runTask(task.id, { expectedVersion: task.version, ...choice }));
  const answer = (answers: Record<string, string>) =>
    void write(() => ai.answerTask(task.id, { expectedVersion: task.version, answers }));
  const designView = design && (
    <DesignView
      task={task}
      pending={pending}
      model={model}
      onOpenEditor={(draftId) => {
        rememberModelReviewed(task.id);
        onNavigate({ kind: "settings", page: "model", draftId, editor: {}, journey });
      }}
      onAnswer={answer}
    />
  );
  const stop = () => void write(() => ai.cancelTask(task.id));

  return (
    <SettingsLayout
      trail={trail}
      title={taskTitle(task)}
      description={task.words && task.fileName ? `“${task.words}”` : undefined}
    >
      {conflict && (
        <Notice tone="warning" focusOnMount>
          {CONFLICT}
        </Notice>
      )}
      {problem && (
        <Notice tone="error" title="That did not work" focusOnMount>
          {problem}
        </Notice>
      )}
      {followed.error && <InlineError message={followed.error} onRetry={followed.retry} />}
      {task.state === "reading" || task.state === "checking" || task.state === "loading" ? (
        <>
          <Section title={task.state === "loading" ? "Loading" : "Working on it"}>
            <div className="job-progress">
              <progress aria-label="Progress" />
              <span role="status">{design?.progress?.now ?? runningText(task)}</span>
            </div>
            {design?.progress && <SessionProgress progress={design.progress} />}
            <p className="admin-hint">
              Editing is not possible while this runs. You can leave this page: you are told when the reading is ready.
            </p>
            {task.state !== "loading" && (
              <div className="task-actions">
                <button type="button" className="secondary" disabled={pending} onClick={stop}>
                  Stop
                </button>
              </div>
            )}
          </Section>
          {task.state === "checking" && !design?.agentSession && designView}
        </>
      ) : design && task.state === "checked" && design.stage === "model" ? (
        <ModelProposal
          task={task}
          pending={pending}
          model={model}
          onOpenEditor={(draftId) => {
            rememberModelReviewed(task.id);
            onNavigate({ kind: "settings", page: "model", draftId, editor: {}, journey });
          }}
          onAnswer={answer}
          onCorrect={(correction) =>
            void write(() => ai.correctModel(task.id, { expectedVersion: task.version, correction }))
          }
          onAccept={() => void write(() => ai.acceptModel(task.id, { expectedVersion: task.version }))}
          onClose={() => onOpenWorkspace(task.workspaceKey)}
          onDiscard={() =>
            void write(async () => {
              const discarded = await ai.discardTask(task.id);
              onOpenWorkspace(task.workspaceKey);
              return discarded;
            })
          }
        />
      ) : design && task.state === "checked" ? (
        <>
          {designView}
          {designCheck && (
            <DesignCheckView
              task={task}
              check={designCheck}
              workspaceLabel={label ?? task.workspaceKey}
              pending={pending}
              canLoad={holds(permissions, "change-sets")}
              canRelease={holds(permissions, "model-release")}
              onLoad={run}
            />
          )}
        </>
      ) : task.state === "loaded" ? (
        <LoadedView
          task={task}
          review={review}
          workspaceLabel={label ?? task.workspaceKey}
          onNavigate={onNavigate}
          onClose={() => onOpenWorkspace(task.workspaceKey)}
        />
      ) : (
        <Section title={task.state === "failed" ? "The reading failed" : "The reading was stopped"}>
          <Notice tone={task.state === "failed" ? "error" : "info"}>
            {jobError || (task.state === "failed" ? "The assistant could not finish." : "Nothing was changed.")}
          </Notice>
          <div className="task-actions">
            {task.state === "failed" && design?.agentSession && (
              <button
                type="button"
                className="primary"
                disabled={pending}
                onClick={() => void write(() => ai.retryTask(task.id, { expectedVersion: task.version }))}
              >
                Try again
              </button>
            )}
            <button type="button" className="secondary" onClick={() => onOpenWorkspace(task.workspaceKey)}>
              Back to the workspace
            </button>
          </div>
        </Section>
      )}
    </SettingsLayout>
  );
}
