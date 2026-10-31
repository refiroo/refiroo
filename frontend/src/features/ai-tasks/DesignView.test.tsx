import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { EngineModel } from "@/types";
import { DesignView } from "./DesignView";
import { designTask } from "./designFixture";

const activeModel = {
  objectTypes: [{ key: "codelist", name: "Codelist", pluralName: "Codelists" }],
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
    expect(within(model).getByText(/Timetable → Codelist \(many to one\)/)).toBeInTheDocument();
    fireEvent.click(within(model).getByRole("button", { name: "Open in the model editor" }));
    expect(onOpenEditor).toHaveBeenCalledWith("draft-1");
    const records = screen.getByRole("region", { name: "Records the structure needs" });
    expect(within(records).getByText(/Timetable categories/)).toBeInTheDocument();
    const sheets = screen.getByRole("region", { name: "Where each sheet goes" });
    expect(within(sheets).getByText("Adds to Codelists")).toBeInTheDocument();
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

  it("says when the model does not change and shows no questions", () => {
    const task = designTask();
    task.design = { ...task.design!, operations: [{ kind: "setRelease", name: "x" }], questions: [] };
    render(<DesignView task={task} pending={false} onAnswer={vi.fn()} />);
    expect(screen.getByText("No change to the model: the workbook fits it as it is.")).toBeInTheDocument();
    expect(screen.queryByText("Proposed")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Answer and design again" })).not.toBeInTheDocument();
  });

  it("lists the relationships to make as sentences and shows a refused rule's reason", () => {
    const task = designTask();
    task.design = {
      ...task.design!,
      outcome: {
        links: [
          { rule: {} as never, from: 3, to: 1, pairs: 3 },
          { rule: {} as never, refused: "The rule makes 200,000 relationships, more than 100,000: narrow it" },
        ],
      },
      links: [
        ...task.design!.links!,
        { relationTypeKey: "has-category", from: { objectTypeKey: "timetable" }, to: { objectTypeKey: "codelist" } },
      ],
    };
    render(<DesignView task={task} pending={false} model={activeModel} onAnswer={vi.fn()} />);
    const links = screen.getByRole("region", { name: "Relationships to make" });
    expect(
      within(links).getByText(
        "Has category: every Timetable whose Name contains “Visit”, with every Codelist (3 pairs).",
      ),
    ).toBeInTheDocument();
    expect(within(links).getByText("Every visit is categorised.")).toBeInTheDocument();
    expect(within(links).getByText(/more than 100,000: narrow it/)).toBeInTheDocument();
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

  it("shows no relationships card without rules", () => {
    const task = designTask();
    task.design = { ...task.design!, links: [] };
    render(<DesignView task={task} pending={false} onAnswer={vi.fn()} />);
    expect(screen.queryByRole("region", { name: "Relationships to make" })).not.toBeInTheDocument();
  });
});
