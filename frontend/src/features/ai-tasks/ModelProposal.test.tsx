import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AiTask } from "@/types";
import { ModelProposal } from "./ModelProposal";
import { designTask } from "./designFixture";
import { taskJourney } from "./aiTaskJourney";

const proposal = (): AiTask => {
  const task = designTask();
  task.check = null;
  task.design = {
    ...task.design!,
    stage: "model",
    questions: [],
    outline: [{ objectTypeKey: "timetable", text: "is one booked visit, with its start time." }],
    checks: [
      { id: "c1", kind: "reuse", text: "Reuse: Categories are the workspace’s own", open: false },
      {
        id: "c2",
        kind: "grouping",
        text: "Grouping: Status has 3 values shared by many timetables",
        open: true,
        explanation: "A list would keep them the same everywhere.",
      },
    ],
    corrections: ["Visits belong to operators"],
  };
  return task;
};

const render_ = (task: AiTask, extra: Partial<Parameters<typeof ModelProposal>[0]> = {}) => {
  const handlers = { onAnswer: vi.fn(), onCorrect: vi.fn(), onAccept: vi.fn() };
  render(<ModelProposal task={task} pending={false} {...handlers} {...extra} />);
  return handlers;
};

describe("ModelProposal", () => {
  it("shows the outline, the checks and the earlier corrections", () => {
    render_(proposal());
    expect(screen.getByText(/is one booked visit/)).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByText("A list would keep them the same everywhere.")).toBeInTheDocument();
    expect(screen.getByText(/Categories are the workspace’s own/)).toBeInTheDocument();
    expect(screen.getByLabelText("Checked")).toBeInTheDocument();
    expect(screen.getByText("You asked: Visits belong to operators")).toBeInTheDocument();
  });

  it("sends the words only when there are some", () => {
    const { onCorrect } = render_(proposal());
    const send = screen.getByRole("button", { name: "Send to the assistant" });
    expect(send).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Tell the assistant what to change"), { target: { value: " Use operators " } });
    fireEvent.click(send);
    expect(onCorrect).toHaveBeenCalledWith("Use operators");
  });

  it("accepts the model", () => {
    const { onAccept } = render_(proposal());
    fireEvent.click(within(document.body).getByRole("button", { name: "Accept the model" }));
    expect(onAccept).toHaveBeenCalledTimes(1);
  });
});

describe("the journey while the model is proposed", () => {
  it("makes the proposal current, the later steps todo, and done once the load stage starts", () => {
    const task = proposal();
    const journey = taskJourney(task);
    const status = Object.fromEntries(journey.steps.map((step) => [step.key, step.status]));
    expect(status).toMatchObject({ designs: "done", proposal: "current", check: "todo", load: "todo" });
    expect(journey.primary).toEqual({ label: "Accept the model", action: "acceptModel" });
    const loading = { ...task, design: { ...task.design!, stage: "load" as const } };
    expect(Object.fromEntries(taskJourney(loading).steps.map((step) => [step.key, step.status])).proposal).toBe("done");
  });

  it("offers no acceptance of a proposal the engine refused, and says why", () => {
    const task = proposal();
    task.design!.outcome = { modelOperations: { refused: { message: "'operator' already binds 'operator-code'" } } } as never;
    render_(task);
    expect(screen.queryByRole("button", { name: "Accept the model" })).not.toBeInTheDocument();
    expect(screen.getByText(/already binds/)).toBeInTheDocument();
    expect(taskJourney(task).primary).toBeUndefined();
  });
});
