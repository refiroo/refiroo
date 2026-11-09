import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AiTask } from "@/types";
import { ModelProposal } from "./ModelProposal";
import { designTask } from "./designFixture";
import { taskJourney } from "./aiTaskJourney";
import { wordsTaskName } from "./aiTaskText";

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
  it("names who can load instead of showing Accept without Work in change sets, and keeps the words box (AP13)", () => {
    render_(proposal(), { canLoad: false, workspaceLabel: "West" });
    expect(screen.queryByRole("button", { name: "Accept the model" })).not.toBeInTheDocument();
    expect(screen.getByText(/Loading needs Work in change sets in West/)).toBeInTheDocument();
    expect(screen.getByLabelText("Tell the assistant what to change")).toBeInTheDocument();
  });

  it("leaves the words box out when the assistant cannot be told (AP13)", () => {
    render_({ ...proposal(), canTell: false });
    expect(screen.queryByLabelText("Tell the assistant what to change")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept the model" })).toBeInTheDocument();
  });

  it("shows a type the workspace's model does not have yet by the name the engine gave", () => {
    const task = proposal();
    task.design!.outline = [{ objectTypeKey: "pc-offer", name: "Offer", text: "New type, 5 attributes, 12 records" }];
    render_(task);
    expect(screen.getByText("Offer")).toBeInTheDocument();
    expect(screen.queryByText("pc-offer")).not.toBeInTheDocument();
  });

  it("says what happens to the records of the types it turns into others, from the engine's counts (AP-D47)", () => {
    const task = proposal();
    task.design!.moves = [
      { from: "supplier", fromName: "Suppliers", to: "partner", toName: "Partners", records: 1420 },
      { from: "vendor", fromName: "Vendors", to: "partner", toName: "Partners", records: 720 },
    ];
    render_(task);
    const table = screen.getByRole("group", { name: "Types that become others" });
    expect(within(table).getByText("Suppliers")).toBeInTheDocument();
    expect(within(table).getByText("1,420")).toBeInTheDocument();
    expect(within(table).getByText("720")).toBeInTheDocument();
    expect(screen.getByText(/2,140 records keep their IDs, history and relationships/)).toBeInTheDocument();
    expect(screen.getByText(/no record moves before you confirm the migration/)).toBeInTheDocument();
  });

  it("says types that keep their key and change application move there, with the records", () => {
    const task = proposal();
    task.design!.moves = [
      {
        from: "a",
        fromName: "A",
        to: "a",
        toName: "A",
        records: 6,
        toApplication: "ref",
        toApplicationName: "Reference lists",
      },
      {
        from: "b",
        fromName: "B",
        to: "b",
        toName: "B",
        records: 4,
        toApplication: "ref",
        toApplicationName: "Reference lists",
      },
    ];
    render_(task);
    expect(screen.getByText(/2 types move to Reference lists, 10 records/)).toBeInTheDocument();
    expect(screen.getAllByText("A, in Reference lists")).toHaveLength(1);
  });

  it("says what the migration would lose of each moved type, from the engine's counts", () => {
    const task = proposal();
    task.design!.moves = [
      {
        from: "supplier",
        fromName: "Suppliers",
        to: "partner",
        toName: "Partners",
        records: 3,
        lost: { values: 2, relationships: 1 },
      },
      { from: "vendor", fromName: "Vendors", to: "partner", toName: "Partners", records: 2, lost: {} },
    ];
    render_(task);
    expect(screen.getByText("Suppliers: 2 values, 1 relationship would be lost.")).toBeInTheDocument();
    expect(screen.queryByText(/Vendors:.*would be lost/)).not.toBeInTheDocument();
  });

  it("says which consumer APIs the proposal raises, from the engine's account", () => {
    const task = proposal();
    task.design!.consumerChanges = [
      { api: "rdm", name: "RDM", from: 2, to: 3, changes: ["no longer exposes object type 'duration'"] },
    ];
    render_(task);
    expect(screen.getByText(/Consumer API RDM: version 2 → 3/)).toBeInTheDocument();
    expect(screen.getByText(/no longer exposes object type 'duration'/)).toBeInTheDocument();
  });

  it("shows no table of moves when it moves no whole type", () => {
    render_(proposal());
    expect(screen.queryByText("What happens to the records")).not.toBeInTheDocument();
  });

  it("shows the outline, the checks and the earlier corrections", () => {
    render_(proposal());
    expect(screen.getByText(/is one booked visit/)).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByText("A list would keep them the same everywhere.")).toBeInTheDocument();
    expect(screen.getByText(/Categories are the workspace’s own/)).toBeInTheDocument();
    expect(screen.getByLabelText("Checked")).toBeInTheDocument();
    expect(screen.getByText("You asked: Visits belong to operators")).toBeInTheDocument();
  });

  it("warns of new records beside the held ones, and Accept stays available (AP-D42)", () => {
    const task = proposal();
    task.design!.checks = [
      {
        id: "beside-held-product",
        kind: "besideHeld",
        text: "667 new Products beside the 667 held. If this is an update, the rows did not find their records.",
        open: true,
      },
    ];
    const { onAccept } = render_(task);
    expect(screen.getByText(/667 new Products beside the 667 held/)).toBeInTheDocument();
    expect(screen.getByText("Needs attention")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Accept the model" }));
    expect(onAccept).toHaveBeenCalled();
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

describe("a proposal of a words task whose model does not change", () => {
  const unchanged = (): AiTask => {
    const task = proposal();
    task.draftId = null;
    task.check = null;
    task.design = {
      ...task.design!,
      summary: "Set the Abbreviation of the stop Chur Wiesental to C10-REVIEW.",
      operations: [],
      outline: [],
      checks: [],
      corrections: [],
      modelUnchanged: true,
    };
    return task;
  };

  it("shows the summary, says the model does not change and offers Accept, with no model editor", () => {
    const { onAccept } = render_(unchanged());
    expect(screen.getByText(/Chur Wiesental to C10-REVIEW/)).toBeInTheDocument();
    expect(screen.getByText("No change to the model.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open in the model editor" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show the model change" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(taskJourney(unchanged()).primary).toEqual({ label: "Accept", action: "acceptModel" });
  });
});

describe("a model-only proposal that changes only views", () => {
  const viewsOnly = (): AiTask => {
    const task = proposal();
    task.fileName = "";
    task.design = { ...task.design!, operations: [], summary: "Add a review table view to the stops." };
    return task;
  };

  it("does not say a workbook fits the model, and points to the draft where the views are (DOC11 F9)", () => {
    render_(viewsOnly(), { onOpenEditor: vi.fn() });
    fireEvent.click(screen.getByRole("button", { name: "Show the model change" }));
    expect(screen.queryByText(/the workbook fits it/)).not.toBeInTheDocument();
    expect(screen.getByText(/No type, attribute or relationship changes/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open in the model editor" }).length).toBeGreaterThan(0);
  });

  it("is named by what it is, and a records-only words task is not a model change (DOC11 F7)", () => {
    expect(wordsTaskName(viewsOnly())).toBe("Change this model");
    const records = viewsOnly();
    records.design = { ...records.design!, modelUnchanged: true };
    expect(wordsTaskName(records)).toBe("Change records");
    expect(wordsTaskName({ design: null, draftId: null })).toBe("Change with the assistant");
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
