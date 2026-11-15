/**
 * One assistant task's page (0.16 AP6a, `/settings/ai-tasks/{id}`): loading a workbook with the AI
 * assistant. It follows the task while a job runs (reading, checking, loading), shows the proposed
 * model, what the load would do per sheet after one check of every row, and where the load went. Live
 * data is never changed from here; the load lands in a change set. A task recorded by an older
 * version that rests in a state this page no longer draws reads as stopped.
 */

import { ActionNotices } from "@/ui/ActionNotices";
import { changedWhileOpen, useGuardedWrite } from "@/ui/useGuardedWrite";
import { JobProgress } from "@/ui/JobProgress";
import { useEffect, useRef, useState } from "react";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { workspaceModel } from "@/model/workspaceModels";
import { useHeldAnywhere, useWorkspacePermissions, holds } from "@/state/permissions";
import { changeReviewFor, routePath } from "@/routing/routes";
import type { AiTask, EngineModel, JourneyRef, RouteState } from "@/types";
import { Trail } from "@/ui/Trail";
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
import { NoTask } from "./NoTask";
import { ReshapeSteps } from "./ReshapeSteps";
import { TaskEnd } from "./TaskEnd";
import { taskApplicationKey } from "./aiTaskJourney";
import { rememberModelReviewed } from "./AiTaskJourneyBar";
import { runningText, taskTitle, waitingText, wordsTaskName } from "./aiTaskText";
import { useAiTask } from "./useAiTask";
import { useAssistantOffers } from "./useAssistantOffers";

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
  const heldAnywhere = useHeldAnywhere();
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
  const [status, setStatus] = useState<string>();
  const offers = useAssistantOffers(task?.workspaceKey, status);
  const guard = useGuardedWrite();
  const { pending } = guard;
  // The design shows the model's names for types and attributes, never their keys.
  const [model, setModel] = useState<EngineModel>();

  const workspaceKey = task?.workspaceKey;
  useEffect(() => {
    if (!workspaceKey) return;
    let current = true;
    api
      .workspace(workspaceKey)
      .then((workspace) => {
        if (!current) return;
        setLabel(workspace.label);
        setStatus(workspace.status);
      })
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [workspaceKey]);

  useEffect(() => {
    if (!workspaceKey) return;
    let current = true;
    workspaceModel(workspaceKey)
      .then((loaded) => current && setModel(loaded))
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [workspaceKey]);

  const workspace: RouteState | undefined = workspaceKey
    ? { kind: "settings", page: "workspaces", workspaceKey }
    : undefined;
  const trail = (
    <Trail
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
        { key: "page", content: task && !task.fileName ? wordsTaskName(task) : "Load a workbook", current: true },
      ]}
    />
  );

  function write(action: () => Promise<AiTask>) {
    return guard.run(async () => followed.set(await action()), {
      onConflict: async () => {
        await followed.reload();
        return changedWhileOpen("task");
      },
    });
  }

  if (!task) {
    return (
      <SettingsLayout trail={trail} title="Load a workbook">
        {followed.notFound ? (
          <NoTask onWorkspaces={() => onNavigate({ kind: "settings", page: "workspaces" })} />
        ) : followed.error ? (
          <InlineError message={followed.error} onRetry={followed.retry} />
        ) : (
          <Skeleton label="Loading the task" />
        )}
      </SettingsLayout>
    );
  }

  const journey: JourneyRef = { kind: "aiTask", taskId: task.id };
  const application = taskApplicationKey(task) ?? ownApplication ?? model?.applications[0]?.key;
  // The change set opens with the journey carried, so its bar shows there.
  const review =
    task.result?.changeSetId && application
      ? { ...changeReviewFor(application, task.workspaceKey, task.result.changeSetId), journey }
      : undefined;
  const design = task.design;
  const designCheck = task.check ?? undefined;
  const run = (choice: LoadChoice) =>
    void write(() => ai.runTask(task.id, { expectedVersion: task.version, ...choice }));
  const answer = (answers: Record<string, string>) =>
    void write(() => ai.answerTask(task.id, { expectedVersion: task.version, answers }));
  const openEditor = (draftId: string) => {
    rememberModelReviewed(task.id);
    onNavigate({ kind: "settings", page: "model", draftId, editor: {}, journey });
  };
  const designView = design && (
    <DesignView task={task} pending={pending} model={model} onOpenEditor={openEditor} onAnswer={answer} />
  );
  const stop = () => void write(() => ai.cancelTask(task.id));
  const canLoad = holds(permissions, "change-sets");
  // A proposal that moves whole types loads no change set and needs none (as the engine decides).
  const canAccept = (task.design?.moves?.length ?? 0) > 0 || canLoad;
  // Installing and activating a model needs the group in the workspace and at the instance.
  const canRelease =
    holds(permissions, "model-release") &&
    Boolean(heldAnywhere?.some((item) => item.key === "model-release" && item.instance));
  const tell = (words: string) =>
    void write(() => ai.correctModel(task.id, { expectedVersion: task.version, correction: words }));
  const goOn = () => void write(() => ai.retryTask(task.id, { expectedVersion: task.version }));
  const publications: RouteState | undefined = application
    ? { kind: "publications", applicationKey: application, workspaceKey: task.workspaceKey }
    : undefined;

  return (
    <SettingsLayout
      trail={trail}
      title={taskTitle(task)}
      description={task.words && task.fileName ? `“${task.words}”` : undefined}
    >
      <ActionNotices guard={guard} errorTitle="That did not work" focusError />
      {followed.error && <InlineError message={followed.error} onRetry={followed.retry} />}
      {task.state === "reading" || task.state === "checking" || task.state === "loading" ? (
        <>
          <Section title={task.state === "loading" ? "Loading" : "Working on it"}>
            <JobProgress role="text">
              {waitingText(task.ahead) ?? design?.progress?.now ?? runningText(task)}
            </JobProgress>
            {design?.progress && <SessionProgress progress={design.progress} />}
            <p className="admin-hint">
              Editing is not possible while this runs. You can leave this page: you are told when the reading is ready.
            </p>
            <div className="task-actions">
              <button type="button" className="secondary" disabled={pending} onClick={stop}>
                Stop
              </button>
            </div>
          </Section>
          {task.state === "checking" && !design?.agentSession && designView}
        </>
      ) : design && task.state === "checked" && design.stage === "model" ? (
        <ModelProposal
          task={task}
          pending={pending}
          model={model}
          canLoad={canAccept}
          workspaceLabel={label ?? task.workspaceKey}
          onOpenEditor={openEditor}
          onAnswer={answer}
          onCorrect={tell}
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
          {designCheck ? (
            <DesignCheckView
              task={task}
              check={designCheck}
              workspaceLabel={label ?? task.workspaceKey}
              pending={pending}
              canLoad={canLoad}
              canRelease={canRelease}
              onLoad={run}
              onTell={tell}
              onBack={() => void write(() => ai.reopenProposal(task.id, { expectedVersion: task.version }))}
            />
          ) : (
            !design.agentSession && (
              <Section title="The saved layout does not fit this file">
                <p>Nothing was loaded. The assistant can read this file with the layout as a start.</p>
                <div className="task-actions">
                  {task.canTell && (
                    <button type="button" className="primary" disabled={pending} onClick={goOn}>
                      Read it with the assistant
                    </button>
                  )}
                  <button type="button" className="secondary" onClick={() => onOpenWorkspace(task.workspaceKey)}>
                    Back to the workspace
                  </button>
                </div>
              </Section>
            )
          )}
        </>
      ) : task.state === "loaded" ? (
        <>
          {task.result?.changeSetId ? (
            <LoadedView
              task={task}
              // A reshaping reviews its change set at its own step, after the first.
              review={task.result.thenReleaseId ? undefined : review}
              workspaceLabel={label ?? task.workspaceKey}
              pending={pending}
              canChange={canLoad}
              offers={offers}
              publications={publications}
              onNavigate={onNavigate}
              onClose={() => onOpenWorkspace(task.workspaceKey)}
              onTell={tell}
              onDiscard={() => void write(() => ai.discardTask(task.id))}
            />
          ) : (
            <Section title="The new model is ready">
              <Notice tone="success">
                The assistant installed the model you accepted. Nothing has moved yet: live data is as it was.
              </Notice>
              <div className="task-actions">
                <button type="button" className="secondary" onClick={() => onOpenWorkspace(task.workspaceKey)}>
                  Close
                </button>
              </div>
            </Section>
          )}
          <ReshapeSteps
            task={task}
            workspaceLabel={label ?? task.workspaceKey}
            canRelease={canRelease}
            review={review}
            pending={pending}
            onNavigate={onNavigate}
            onTell={tell}
          />
        </>
      ) : (
        <TaskEnd
          task={task}
          pending={pending}
          onTell={tell}
          onGoOn={goOn}
          onDiscard={() => void write(() => ai.discardTask(task.id))}
          onOpenEditor={openEditor}
          onBack={() => onOpenWorkspace(task.workspaceKey)}
          review={review}
          onNavigate={onNavigate}
        />
      )}
    </SettingsLayout>
  );
}
