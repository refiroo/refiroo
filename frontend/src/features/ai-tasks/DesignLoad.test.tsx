import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AiTask, AiTaskLoad } from "@/types";
import { DesignLoad } from "./DesignLoad";
import { ModelProposal } from "./ModelProposal";
import { designTask } from "./designFixture";
import { modelNames } from "./aiTaskDesign";

const load: AiTaskLoad = {
  mode: "items",
  jobId: "job-1",
  draftId: "draft-1",
  draftVersion: 3,
  workspaceKey: "west",
  items: 7,
  figures: {
    recordsNew: 1699,
    recordsMatched: 237,
    recordsChanged: 0,
    recordsRemoved: 0,
    relationshipsNew: 2633,
    relationshipsMatched: 0,
    refused: 0,
    rowsRead: 333,
  },
  types: [
    {
      objectTypeKey: "country",
      new: 0,
      matched: 237,
      changed: 0,
      removed: 0,
      refused: 0,
      linkedTo: ["iso-country"],
      examples: [
        {
          index: 1,
          ref: "Person!N32:P32",
          objectTypeKey: "country",
          action: "unchanged",
          name: "Brazil",
          id: "c-1",
          values: [{ attributeTypeKey: "code", value: "BR" }],
          links: [{ relationTypeKey: "has-iso", direction: "outgoing", objectTypeKey: "iso-country", name: "BR" }],
          error: null,
        },
      ],
    },
    {
      objectTypeKey: "person-subtype",
      new: 17,
      matched: 0,
      changed: 0,
      removed: 0,
      refused: 0,
      linkedTo: [],
      examples: [],
    },
  ],
  relationships: [{ relationTypeKey: "has-iso", new: 2633, matched: 0, refused: 0 }],
  sheets: [
    { sheet: "Person", rows: 300 },
    { sheet: "Country ISO", rows: 33 },
  ],
  parts: [
    {
      sheet: "Person",
      firstColumn: "N",
      lastColumn: "P",
      firstRow: 8,
      lastRow: 247,
      objectTypeKey: "country",
      relationTypeKey: null,
      items: 237,
    },
  ],
  partsTotal: 1,
  findings: [
    {
      kind: "nameTwice",
      objectTypeKey: "person-subtype",
      name: "Driver",
      count: 2,
      parents: [
        { id: "p-1", name: "Affiliate", objectTypeKey: "person-type" },
        { id: "p-2", name: "Employee", objectTypeKey: "person-type" },
      ],
    },
  ],
  refused: [],
  refusedByCode: [],
  ranAt: "2026-11-09T10:00:00Z",
};

const names = modelNames(undefined, [
  { kind: "addObjectType", key: "country", name: "Country", pluralName: "Countries" },
  { kind: "addObjectType", key: "iso-country", name: "ISO country", pluralName: "ISO countries" },
  { kind: "addObjectType", key: "person-subtype", name: "Person subtype", pluralName: "Person subtypes" },
  { kind: "addAttributeType", key: "code", name: "Code" },
  { kind: "addRelationType", key: "has-iso", name: "has ISO entry", reverseName: "is the ISO entry of" },
]);

describe("DesignLoad", () => {
  it("shows the figures, a table per type, the engine's finding and the parts of the file", () => {
    render(<DesignLoad load={load} names={names} />);
    const card = screen.getByRole("region", { name: "What the load does" });
    const figures = within(card).getByRole("list", { name: "The load in figures" });
    expect(within(figures).getByText("1,699")).toBeInTheDocument();
    expect(within(figures).getByText("existing records matched")).toBeInTheDocument();
    expect(within(figures).getByText("rows read from 2 sheets")).toBeInTheDocument();
    const table = within(card).getByRole("group", { name: "What the load does to each type" });
    expect(within(table).getByRole("row", { name: /Country: 0 new records, 237 matched$/ })).toBeInTheDocument();
    expect(within(table).getByText("ISO country")).toBeInTheDocument();
    expect(within(card).getByText("One name twice in one type")).toBeInTheDocument();
    expect(
      within(card).getByText("“Driver” is 2 Person subtypes: one under Affiliate, one under Employee."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Person!N8:P247")).not.toBeInTheDocument();
    fireEvent.click(within(card).getByRole("button", { name: "Where each part of the file goes" }));
    expect(within(card).getByText("Person!N8:P247")).toBeInTheDocument();
  });

  it("counts the links of new records to their parents in the relationships and says so (DOC11 F2)", () => {
    const parented: AiTaskLoad = { ...load, figures: { ...load.figures, relationshipsNew: 354, parentLinksNew: 190 } };
    render(<DesignLoad load={parented} names={names} />);
    const figures = screen.getByRole("list", { name: "The load in figures" });
    expect(within(figures).getByText("354")).toBeInTheDocument();
    expect(within(figures).getByText("relationships new, with the links to parents")).toBeInTheDocument();
    expect(screen.getByText(/190 links of new records to their parents/)).toBeInTheDocument();
  });

  it("opens a type to its example records with the keyboard, each with the cells it came from", () => {
    render(<DesignLoad load={load} names={names} />);
    const row = screen.getByRole("row", { name: /Country: 0 new records/ });
    expect(row).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Brazil")).not.toBeInTheDocument();
    fireEvent.keyDown(row, { key: "Enter" });
    expect(row).toHaveAttribute("aria-expanded", "true");
    const examples = screen.getByRole("list", { name: "Examples of Country" });
    expect(within(examples).getByText("Brazil")).toBeInTheDocument();
    expect(within(examples).getByText(/Code: BR/)).toBeInTheDocument();
    expect(within(examples).getByText(/→ has ISO entry BR/)).toBeInTheDocument();
    expect(within(examples).getByText("Person!N32:P32")).toBeInTheDocument();
    fireEvent.keyDown(row, { key: " " });
    expect(row).toHaveAttribute("aria-expanded", "false");
    // A type with no example has nothing to open.
    expect(screen.getByRole("row", { name: /Person subtype/ })).not.toHaveAttribute("aria-expanded");
  });

  it("lists what is refused with its cells and warns when the draft changed after the check", () => {
    const refused: AiTaskLoad = {
      ...load,
      figures: { ...load.figures, refused: 1 },
      refused: [
        { index: 4, ref: "Person!A9", key: "country", code: "UNKNOWN_ATTRIBUTES", message: "No such attribute" },
      ],
    };
    render(<DesignLoad load={refused} names={names} stale />);
    expect(screen.getByText("1 item refused")).toBeInTheDocument();
    expect(screen.getByText("Person!A9")).toBeInTheDocument();
    expect(screen.getByText(/The draft changed after this check/)).toBeInTheDocument();
  });
});

describe("ModelProposal with a load", () => {
  const proposal = (): AiTask => {
    const task = designTask();
    task.check = null;
    task.design = {
      ...task.design!,
      stage: "model",
      questions: [],
      load,
      itemsLoad: true,
    };
    return task;
  };

  it("replaces the model's accept with Accept and load to change set, which says the engine loads exactly the records above", () => {
    const onAccept = vi.fn();
    render(
      <ModelProposal task={proposal()} pending={false} onAnswer={vi.fn()} onCorrect={vi.fn()} onAccept={onAccept} />,
    );
    expect(screen.queryByRole("button", { name: "Accept the model" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "What the load does" })).toBeInTheDocument();
    expect(screen.getByText(/loads exactly the records above into a new change set/)).toBeInTheDocument();
    expect(screen.getByText(/No assistant turn, nothing published/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Accept and load to change set" }));
    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Give the assistant other words" })).toBeInTheDocument();
  });

  it("keeps one Accept the model, with the journey id, when a load comes with moves, and does not promise the load (R13-F21)", () => {
    const onAccept = vi.fn();
    const task = proposal();
    task.design!.moves = [{ from: "supplier", fromName: "Suppliers", to: "partner", toName: "Partners", records: 12 }];
    task.design!.itemsLoad = false;
    const { container } = render(
      <ModelProposal task={task} pending={false} onAnswer={vi.fn()} onCorrect={vi.fn()} onAccept={onAccept} />,
    );
    const accept = screen.getByRole("button", { name: "Accept the model" });
    expect(accept.closest("#journey-accept")).not.toBeNull();
    expect(container.querySelectorAll("#journey-accept")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Accept and load to change set" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Accepting loads exactly this/)).not.toBeInTheDocument();
    expect(screen.getByText(/Accepting loads none of it/)).toBeInTheDocument();
    fireEvent.click(accept);
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("offers no accept to someone who may not load", () => {
    render(
      <ModelProposal
        task={proposal()}
        pending={false}
        canLoad={false}
        onAnswer={vi.fn()}
        onCorrect={vi.fn()}
        onAccept={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Accept and load to change set" })).not.toBeInTheDocument();
  });
});
