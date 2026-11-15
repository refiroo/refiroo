/**
 * The journey bar of an assistant load, on every page that is a step of it: the task's page, the
 * model editor opened from it and the change set it loaded into. It follows the task itself (so it
 * is right on pages that do not), and its buttons run what the sentence says: open the editor with
 * the journey carried, answer the questions or load on the task's page, open the change set, stop
 * the job, or start again.
 */

import { useEffect, useState } from "react";
import { ai } from "@/api/aiClient";
import { errorMessage } from "@/api/errors";
import { JourneyBar } from "@/app/JourneyBar";
import { holds, useWorkspacePermissions } from "@/state/permissions";
import { useAssistantOfferIn } from "@/state/useWorkspaceAiOffer";
import { workspaceModel } from "@/model/workspaceModels";
import { changeReviewFor } from "@/routing/routes";
import type { JourneyRef, RouteState } from "@/types";
import { LoadWorkbookDialog } from "./LoadWorkbookDialog";
import { taskApplicationKey, taskJourney, type JourneyAction } from "./aiTaskJourney";
import { wordsTaskName } from "./aiTaskText";
import { useAiTask } from "./useAiTask";
import { readLocalPreference, removeLocalPreference, writeLocalPreference } from "@/lib/localPreference";

/** Where the bar is: the journey's home (the task), the model editor or the change set. */
export type JourneyPlace = "task" | "editor" | "changeSet";

const reviewedKey = (taskId: string) => `rdm:journey:model-reviewed:${taskId}`;

/** Whether the person has opened the model change in the editor (kept in this browser). */
// The mark is the number 1, which is `"1"` as stored: what this browser already holds stays valid.
function modelReviewed(taskId: string): boolean {
  return readLocalPreference<number>(reviewedKey(taskId), 0, (value): value is number => value === 1) === 1;
}

/** Without storage the model step stays current: the person can still load from the task's page. */
export function rememberModelReviewed(taskId: string) {
  writeLocalPreference(reviewedKey(taskId), 1);
}

/** Drops the mark once the task can no longer be at the model step: it is kept per task and would stay for good. */
function forgetModelReviewed(taskId: string) {
  removeLocalPreference(reviewedKey(taskId));
}

/** Scrolls to a part of the task's page and puts the focus in it (its button when it has one). */
function scrollToAndFocus(id: string) {
  const target = document.getElementById(id);
  if (!target) return;
  target.scrollIntoView?.({ block: "start" });
  // The first of these that exists, in this order: a querySelector with all four would take the first
  // in the page, which on a proposal is "Open in the model editor", not the Accept beside it.
  const first = ["textarea", "button.primary", "button", "input"]
    .map((selector) => target.querySelector<HTMLElement>(selector))
    .find((found) => found !== null);
  (first ?? target).focus({ preventScroll: true });
}

export function AiTaskJourneyBar({
  journey,
  place,
  onNavigate,
}: {
  journey: Extract<JourneyRef, { kind: "aiTask" }>;
  place: JourneyPlace;
  onNavigate: (route: RouteState) => void;
}) {
  const { taskId } = journey;
  const followed = useAiTask(taskId);
  const { task } = followed;
  const permissions = useWorkspacePermissions(task?.workspaceKey);
  const offer = useAssistantOfferIn(task?.workspaceKey, permissions);
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState(false);
  const [restarting, setRestarting] = useState(false);
  useEffect(() => {
    if (place !== "editor") return;
    rememberModelReviewed(taskId);
  }, [place, taskId]);
  // A loaded or cancelled task never returns to the model step (`taskJourney` reads the mark only while it is checked).
  const finished = task?.state === "loaded" || task?.state === "cancelled";
  useEffect(() => {
    if (finished) forgetModelReviewed(taskId);
  }, [finished, taskId]);
  if (!task) return null;

  const plan = taskJourney(task, {
    modelReviewed: place === "editor" ? false : modelReviewed(taskId),
    canLoad: holds(permissions, "change-sets"),
  });
  const toTask: RouteState = { kind: "settings", page: "ai-tasks", taskId };

  async function openChangeSet() {
    const changeSetId = task?.result?.changeSetId;
    if (!task || !changeSetId) return;
    let applicationKey = taskApplicationKey(task);
    if (!applicationKey) {
      try {
        applicationKey = (await workspaceModel(task.workspaceKey)).applications[0]?.key;
      } catch (cause) {
        setProblem(errorMessage(cause));
        return;
      }
    }
    if (applicationKey) onNavigate({ ...changeReviewFor(applicationKey, task.workspaceKey, changeSetId), journey });
  }

  const run: Record<JourneyAction, (() => void) | undefined> = {
    openEditor: task.draftId
      ? () => {
          rememberModelReviewed(taskId);
          onNavigate({ kind: "settings", page: "model", draftId: task.draftId!, editor: {}, journey });
        }
      : undefined,
    questions: place === "task" ? () => scrollToAndFocus("journey-questions") : undefined,
    acceptModel: place === "task" ? () => scrollToAndFocus("journey-accept") : undefined,
    load: place === "task" ? () => scrollToAndFocus("journey-load") : undefined,
    tell: place === "task" ? () => scrollToAndFocus("journey-tell") : undefined,
    openChangeSet: place === "changeSet" ? undefined : () => void openChangeSet(),
    restart: offer?.assistant ? () => setRestarting(true) : undefined,
    openTask: place === "task" ? undefined : () => onNavigate(toTask),
  };
  const onClick = plan.primary && run[plan.primary.action];

  async function stop() {
    setPending(true);
    setProblem("");
    try {
      followed.set(await ai.cancelTask(taskId));
    } catch (cause) {
      setProblem(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <JourneyBar
        label={task.fileName ? "Import with the assistant" : wordsTaskName(task)}
        steps={plan.steps}
        sentence={problem || plan.sentence}
        primary={plan.primary && onClick ? { label: plan.primary.label, onClick } : undefined}
        back={
          place === "task"
            ? undefined
            : {
                label: task.fileName ? "Back to the import" : "Back to the proposal",
                onClick: () => onNavigate(toTask),
              }
        }
        stop={plan.stoppable ? { label: "Stop", onClick: () => void stop(), disabled: pending } : undefined}
      />
      {restarting && offer?.assistant && (
        <LoadWorkbookDialog
          start={{ workspaceKey: task.workspaceKey, ...(task.words ? { words: task.words } : {}) }}
          onClose={() => setRestarting(false)}
          onStarted={(started) => {
            setRestarting(false);
            onNavigate({ kind: "settings", page: "ai-tasks", taskId: started.id });
          }}
        />
      )}
    </>
  );
}
