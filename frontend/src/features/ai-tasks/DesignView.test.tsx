import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EngineModel } from "@/types";
import { DesignView } from "./DesignView";
import { designTask } from "./designFixture";

const activeModel = {
  objectTypes: [{ key: "category", name: "Category", pluralName: "Categories" }],
  attributeTypes: [],
  relationTypes: [],
} as unknown as EngineModel;

describe("DesignView", () => {
  it("shows the summary, the model change, the records and where each sheet goes", () => {
    const onOpenEditor = vi.fn();
    render(
      <DesignView
        task={designTask()}
        pending={false}
        model={activeModel}
        onOpenEditor={onOpenEditor}
        onAnswer={vi.fn()}
      />,
    );
    expect(screen.getByText(/The model gets a Scheduling application/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing is written until you confirm/)).toBeInTheDocument();
    const model = screen.getByRole("region", { name: /The model: what changes/ });
    expect(within(model).getByText("Proposed")).toBeInTheDocument();
    expect(within(model).getByText("New application")).toBeInTheDocument();
    expect(within(model).getByText(/Starts \(required\)/)).toBeInTheDocument();
    expect(within(model).getByText(/Timetable → Category \(many to one\)/)).toBeInTheDocument();
    fireEvent.click(within(model).getByRole("button", { name: "Open in the model editor" }));
    expect(onOpenEditor).toHaveBeenCalledWith("draft-1");
    const sheets = screen.getByRole("region", { name: "Where each sheet goes" });
    expect(within(sheets).getByText("Adds to Categories")).toBeInTheDocument();
    expect(screen.queryByText("Note → Left out")).not.toBeInTheDocument();
    fireEvent.click(within(sheets).getByRole("button", { name: "Show what each column fills" }));
    expect(within(sheets).getByText("Note → Left out")).toBeInTheDocument();
    expect(within(sheets).getByText("Starts → its attribute")).toBeInTheDocument();
    expect(within(sheets).getByText("German → Name")).toBeInTheDocument();
    expect(within(sheets).getByRole("button", { name: "Hide what each column fills" })).toBeInTheDocument();
  });

  it("posts the chosen option of every question, the assumed or given one preselected", () => {
    const onAnswer = vi.fn();
    render(<DesignView task={designTask()} pending={false} onAnswer={onAnswer} />);
    expect(screen.getByRole("radio", { name: "Yes" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Drop" })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: "No" }));
    fireEvent.click(screen.getByRole("button", { name: "Answer and design again" }));
    expect(onAnswer).toHaveBeenCalledWith({ "Is a visit one timetable?": "No", "Keep walk-ins?": "Drop" });
  });

  it("offers no design round while every choice is the assumed one the draft is built on", () => {
    const task = designTask();
    task.design = {
      ...task.design!,
      questions: task.design!.questions.map((q) => ({ ...q, assumed: q.options[0] })),
      answers: {},
    };
    render(<DesignView task={task} pending={false} onAnswer={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Answer and design again" })).not.toBeInTheDocument();
    expect(screen.getByText(/The draft is already built on these answers/)).toBeInTheDocument();
    const other = task.design!.questions[0].options[1];
    fireEvent.click(screen.getByRole("radio", { name: other }));
    expect(screen.getByRole("button", { name: "Answer and design again" })).toBeInTheDocument();
  });

  it("says when the model does not change and shows no questions", () => {
    const task = designTask();
    task.design = { ...task.design!, operations: [{ kind: "setRelease", name: "x" }], questions: [] };
    render(<DesignView task={task} pending={false} onAnswer={vi.fn()} />);
    expect(screen.getByText("No change to the model: the workbook fits it as it is.")).toBeInTheDocument();
    expect(screen.queryByText("Proposed")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Answer and design again" })).not.toBeInTheDocument();
  });

  it("reports the engine's problems when the design stands, not while the assistant still works", () => {
    const task = designTask();
    task.design = {
      ...task.design!,
      outcome: { profileProblems: [{ code: "NO_PROFILE", message: "No profile was given" }] } as never,
    };
    const { rerender } = render(<DesignView task={task} pending={false} onAnswer={vi.fn()} />);
    expect(screen.getByText(/No profile was given/)).toBeInTheDocument();
    rerender(<DesignView task={{ ...task, state: "checking" }} pending={false} onAnswer={vi.fn()} />);
    expect(screen.queryByText(/No profile was given/)).not.toBeInTheDocument();
  });
});
