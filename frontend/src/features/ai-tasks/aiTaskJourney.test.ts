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
});
