import { describe, expect, it } from "vitest";
import type { AiTask } from "@/types";
import { designTask } from "./designFixture";
import { taskJourney } from "./aiTaskJourney";

const statuses = (task: AiTask, modelReviewed = false) =>
  Object.fromEntries(taskJourney(task, { modelReviewed }).steps.map((step) => [step.key, step.status]));

describe("the assistant load as a journey", () => {
  it("starts with the assistant designing and can be stopped", () => {
    const task = { ...designTask(), state: "reading" as const, phase: "designing" as const, check: null };
    const journey = taskJourney(task);
    expect(statuses(task)).toMatchObject({ file: "done", designs: "current", check: "todo", load: "todo" });
    expect(journey.stoppable).toBe(true);
  });

  it("says a queued task waits, and how many tasks are ahead (AQ)", () => {
    const base = { ...designTask(), state: "checking" as const, phase: "checking" as const };
    expect(taskJourney({ ...base, ahead: 2 }).sentence).toBe(
      "Waiting for the assistant: 2 tasks ahead. You can leave this page.",
    );
    expect(taskJourney({ ...base, ahead: 1 }).sentence).toBe(
      "Waiting for the assistant: 1 task ahead. You can leave this page.",
    );
    expect(taskJourney({ ...base, ahead: 0 }).sentence).toBe("Starting… You can leave this page.");
    expect(taskJourney({ ...base, ahead: null }).sentence).toBe(
      "Checking every row of the file. You can leave this page.",
    );
  });

  it("checks every row, then asks the open questions first", () => {
    const checking = { ...designTask(), state: "checking" as const, phase: "checking" as const };
    expect(statuses(checking)).toMatchObject({ designs: "done", check: "current" });
    const checked = designTask();
    const journey = taskJourney(checked);
    // One of the two questions is answered in the fixture.
    expect(statuses(checked)).toMatchObject({ questions: "current", check: "done", load: "todo" });
    expect(journey.sentence).toBe("Answer 1 question, then the assistant designs again.");
    expect(journey.primary?.action).toBe("questions");
  });

  it("sends the person to the model editor before the load, and names refused rows", () => {
    const task = designTask();
    task.design!.answers["Is a visit one timetable?"] = "Yes";
    const review = taskJourney(task);
    expect(statuses(task)).toMatchObject({ model: "current", questions: "done", load: "todo" });
    expect(review.sentence).toBe("Review the model change in the editor, then come back here.");
    expect(review.primary).toEqual({ label: "Open in the model editor", action: "openEditor" });
    const load = taskJourney(task, { modelReviewed: true });
    expect(statuses(task, true)).toMatchObject({ model: "done", load: "current" });
    expect(load.primary?.action).toBe("load");
    expect(load.sentence).toContain("2 rows will be refused");
  });

  it("leaves out the steps a design does not need", () => {
    const task = designTask();
    task.design = { ...task.design!, operations: [], questions: [] };
    expect(taskJourney(task).steps.map((step) => step.key)).toEqual(["file", "designs", "check", "load", "review"]);
  });

  it("ends in the change set once loaded, and can start again after a failure", () => {
    const loaded = {
      ...designTask(),
      state: "loaded" as const,
      result: { changeSetId: "cs-1" },
    };
    const done = taskJourney(loaded, { modelReviewed: true });
    expect(statuses(loaded, true)).toMatchObject({ load: "done", review: "current" });
    expect(done.sentence).toContain("nothing is live until it is published");
    expect(done.primary).toEqual({ label: "Open the change set", action: "openChangeSet" });
    const failed = { ...designTask(), state: "failed" as const, check: null };
    const again = taskJourney(failed);
    expect(statuses(failed)).toMatchObject({ designs: "failed", check: "todo" });
    expect(again.primary).toEqual({ label: "Start again", action: "restart" });
    expect(again.stoppable).toBe(false);
  });

  it("points a task that stopped to the words box, a stopped load to Stop, and a published one onward (AP13)", () => {
    const failed = { ...designTask(), state: "failed" as const, check: null, canTell: true };
    const told = taskJourney(failed);
    expect(told.primary).toEqual({ label: "Tell the assistant", action: "tell" });
    expect(told.sentence).toContain("Tell it how to go on");
    const stopped = { ...designTask(), state: "stopped" as const, check: null, canTell: true };
    expect(statuses(stopped)).toMatchObject({ designs: "current" });
    expect(taskJourney(stopped).sentence).toContain("You stopped the assistant");
    const discarded = { ...designTask(), state: "cancelled" as const, check: null };
    expect(taskJourney(discarded).primary).toEqual({ label: "Start again", action: "restart" });
    expect(taskJourney({ ...designTask(), state: "loading" as const }).stoppable).toBe(true);
    const published = {
      ...designTask(),
      state: "loaded" as const,
      result: { changeSetId: "cs-1", published: true },
    };
    expect(statuses(published, true)).toMatchObject({ review: "done" });
    expect(taskJourney(published, { modelReviewed: true }).sentence).toContain("Published.");
  });

  it("offers no Accept or Load to a person without Work in change sets, and says who can", () => {
    const proposal = { ...designTask(), check: null };
    proposal.design = { ...proposal.design!, stage: "model" as const };
    const told = taskJourney(proposal, { canLoad: false });
    expect(told.primary).toBeUndefined();
    expect(told.sentence).toContain("Someone who does can accept and load from this page");
    expect(taskJourney(proposal).primary).toEqual({ label: "Accept the model", action: "acceptModel" });
    const ready = designTask();
    ready.design = { ...ready.design!, questions: [] };
    expect(taskJourney(ready, { modelReviewed: true, canLoad: false }).primary).toBeUndefined();
  });

  it("ends a whole-type move on the task, where the migration is previewed and confirmed (AP12)", () => {
    const moved = {
      ...designTask(),
      state: "loaded" as const,
      result: { migration: { releaseId: "rel-1", typeMappings: [] } },
    };
    const plan = taskJourney(moved, { modelReviewed: true });
    expect(plan.steps.find((step) => step.key === "review")).toMatchObject({
      label: "Confirm the migration",
      status: "current",
    });
    expect(plan.sentence).toContain("no record has moved");
    expect(plan.primary).toEqual({ label: "Open the steps", action: "openTask" });
  });
});
