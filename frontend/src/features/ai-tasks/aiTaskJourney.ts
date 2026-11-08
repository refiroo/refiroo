/**
 * The assistant's load of a workbook as a user journey (the journey bar): its steps with where the
 * person is, the one sentence of what to do now and the action that does it. Derived from the task
 * alone, so every page of the journey (the task, the model editor, the change set) shows the same.
 */

import type { AiTask } from "@/types";
import { changesModel, proposalRefusal } from "./aiTaskDesign";
import { isDesignCheck, plural, waitingText } from "./aiTaskText";

export type StepStatus = "done" | "current" | "todo" | "failed";

export interface JourneyStep {
  key: string;
  label: string;
  status: StepStatus;
}

/** What the primary button does; the page decides how (navigate, scroll, open a dialog). */
export type JourneyAction =
  "openEditor" | "questions" | "load" | "acceptModel" | "openChangeSet" | "restart" | "openTask" | "tell";

export interface TaskJourney {
  steps: JourneyStep[];
  sentence: string;
  primary?: { label: string; action: JourneyAction };
  /** Whether a job is running that the person may stop. */
  stoppable: boolean;
}

/** The questions the person has not answered yet (an assumed answer is not an answer). */
export const unansweredQuestions = (task: AiTask) =>
  (task.design?.questions ?? []).filter((question) => task.design?.answers[question.text] === undefined).length;

/** The application a task's records belong to, the way into its change set. */
export const taskApplicationKey = (task: AiTask): string | undefined =>
  task.reading?.tables.find((table) => table.applicationKey)?.applicationKey ??
  task.design?.profile?.sources.find((source) => source.applicationKey)?.applicationKey ??
  undefined;

const refusedRows = (task: AiTask) =>
  task.check ? (isDesignCheck(task.check) ? task.check.summary.refused : (task.check.summary?.refused ?? 0)) : 0;

export function taskJourney(task: AiTask, options: { modelReviewed?: boolean; canLoad?: boolean } = {}): TaskJourney {
  const canLoad = options.canLoad ?? true;
  const { state } = task;
  const design = task.design ?? null;
  // A task of an older version may rest in a state this one no longer has (`read`): it reads as discarded.
  const ended = !(["reading", "checking", "checked", "loading", "loaded"] as string[]).includes(state);
  const checked = state === "checked";
  const proposing = checked && design?.stage === "model";
  const designing = state === "reading" || (state === "checking" && task.phase !== "checking");
  const checking = state === "checking" && task.phase === "checking";
  const unanswered = checked && !proposing ? unansweredQuestions(task) : 0;
  const modelStep = !!design && changesModel(design);
  const questionStep = !!design && design.questions.length > 0;
  const reviewModel = checked && !proposing && modelStep && !options.modelReviewed && unanswered === 0;
  const loadNow = checked && !proposing && !reviewModel && unanswered === 0;
  // After a failure the earlier steps stand and the step it failed in shows it; one that never
  // checked failed while the assistant designed.
  const failedAt = state === "failed" ? (task.check ? "load" : "designs") : undefined;
  const published = !!task.result?.published;

  const past = state === "loading" || state === "loaded";
  const status = (key: string, current: boolean, done: boolean): StepStatus =>
    failedAt === key ? "failed" : current ? "current" : done ? "done" : "todo";

  const steps: JourneyStep[] = [
    { key: "file", label: "File and words", status: "done" },
    {
      key: "designs",
      label: "The assistant designs",
      status: status("designs", designing || state === "stopped", !designing && !failedAt && state !== "stopped"),
    },
    ...(design?.stage
      ? [
          {
            key: "proposal",
            label: "Model proposal",
            status: status("proposal", proposing, !proposing && !designing && !failedAt),
          },
        ]
      : []),
    ...(modelStep
      ? [
          {
            key: "model",
            label: "Model change",
            status: status("model", reviewModel, past || (checked && !proposing && !reviewModel)),
          },
        ]
      : []),
    ...(questionStep
      ? [
          {
            key: "questions",
            label: "Questions",
            status: status("questions", unanswered > 0, (checked && !proposing && unanswered === 0) || past),
          },
        ]
      : []),
    { key: "check", label: "Check", status: status("check", checking, (checked && !proposing) || past) },
    { key: "load", label: "Load", status: status("load", loadNow || state === "loading", state === "loaded") },
    {
      key: "review",
      label: task.result?.migration ? "Confirm the migration" : "Review and publish",
      status: status("review", state === "loaded" && !published, published),
    },
  ];
  // A step before the one that failed is done unless it never ran.
  if (failedAt === "load")
    for (const step of steps) if (step.key !== "load" && step.key !== "review") step.status = "done";

  const refused = refusedRows(task);
  const base = { steps, stoppable: state === "reading" || state === "checking" || state === "loading" };

  if (ended) {
    if (state === "failed" || state === "stopped")
      return {
        ...base,
        sentence: task.canTell
          ? `${state === "failed" ? "The assistant stopped" : "You stopped the assistant"}, and nothing was changed. Tell it how to go on, or discard the task.`
          : "The assistant could not finish, and nothing was changed. Start again, perhaps with other words.",
        primary: task.canTell
          ? { label: "Tell the assistant", action: "tell" }
          : { label: "Start again", action: "restart" },
      };
    return {
      ...base,
      sentence: "The task was discarded, and nothing was changed. Start again when you are ready.",
      primary: { label: "Start again", action: "restart" },
    };
  }
  if (designing || checking)
    return {
      ...base,
      sentence:
        waitingText(task.ahead) !== null
          ? `${waitingText(task.ahead)}${task.ahead === 0 ? "" : "."} You can leave this page.`
          : checking
            ? "Checking every row of the file. You can leave this page."
            : "The assistant is designing the load. You can leave this page.",
      primary: { label: "Show progress", action: "openTask" },
    };
  if ((proposing || (checked && !design?.questions.length && !reviewModel)) && !canLoad)
    return {
      ...base,
      sentence:
        "Loading needs Work in change sets, which you do not hold. Someone who does can accept and load from this page.",
    };
  if (proposing)
    return proposalRefusal(task)
      ? { ...base, sentence: "The engine could not apply this proposal. Tell the assistant what to change." }
      : {
          ...base,
          sentence: design?.modelUnchanged
            ? "Read the proposed change. Correct it in words, or accept it; nothing is loaded before."
            : "Read the proposed model. Correct it in words, or accept it; nothing is loaded before.",
          primary: { label: design?.modelUnchanged ? "Accept" : "Accept the model", action: "acceptModel" },
        };
  if (checked && unanswered > 0)
    return {
      ...base,
      sentence: `Answer ${plural(unanswered, "question")}, then the assistant designs again.`,
      primary: { label: `Answer ${plural(unanswered, "question")}`, action: "questions" },
    };
  if (reviewModel)
    return {
      ...base,
      sentence: "Review the model change in the editor, then come back here.",
      primary: { label: "Open in the model editor", action: "openEditor" },
    };
  if (checked)
    return {
      ...base,
      sentence:
        refused > 0
          ? `Every row is checked; ${plural(refused, "row")} will be refused and not loaded. Load the rest into a change set. Nothing is live until it is published.`
          : "Every row is checked. Load it into a change set. Nothing is live until it is published.",
      primary: { label: "Load into a change set", action: "load" },
    };
  if (state === "loading")
    return { ...base, sentence: "Loading into the change set. You can leave this page, or stop it." };
  if (!task.result?.changeSetId)
    return {
      ...base,
      sentence: "The new model is installed and no record has moved. Preview the migration and confirm it on the task.",
      primary: { label: "Open the steps", action: "openTask" },
    };
  if (published)
    return {
      ...base,
      sentence: "Published. Something not right? Change the model, or ask about the records, from the task.",
      primary: { label: "Open the task", action: "openTask" },
    };
  return {
    ...base,
    sentence: task.result.thenReleaseId
      ? "Moved into a change set; nothing is live until it is published. Three steps are yours, shown on the task."
      : "Loaded into a change set; nothing is live until it is published. Not what you wanted? Tell the assistant on the task, or discard the change set.",
    primary: { label: "Open the change set", action: "openChangeSet" },
  };
}
