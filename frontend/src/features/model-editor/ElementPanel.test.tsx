import { createEvent, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ElementPanel } from "@/features/model-editor/ElementPanel";
import { outlineFixture } from "@/test/draftOutline";
import type { EditorSelection, ModelDraftOutline } from "@/types";

/** Shop keeps Bin's records; Archive lists Bin for a matrix, in its group "Lists", and has two groups. */
function outline(): ModelDraftOutline {
  const result = outlineFixture();
  const shop = result.applications[0]!;
  result.applications.push({
    ...shop,
    key: "archive",
    name: "Archive",
    objectTypeKeys: ["bin"],
    ownTypes: [],
    ownTree: [],
    borrowed: [
      {
        objectType: "bin",
        home: "shop",
        uses: [
          {
            view: "bins-by-shelf",
            viewName: "Bins by shelf",
            viewType: "relationMatrix",
            role: "rows",
            relationType: "stores",
            relationName: "Stores",
          },
        ],
      },
    ],
    borrowedTree: [{ objectType: "bin", children: [] }],
    unused: [],
    navigation: {
      groups: [
        {
          key: "lists",
          label: "Lists",
          collapsed: false,
          collections: ["bin"],
          entries: [{ collection: "bin" }],
          mark: "new",
        },
        { key: "more", label: "More", collapsed: true, collections: [], entries: [], mark: "new" },
      ],
      ungrouped: [],
      opens: {},
    },
    views: [],
  });
  const bin = result.objectTypes.find((type) => type.key === "bin")!;
  bin.home = "shop";
  bin.ownIn = ["shop"];
  bin.borrowedIn = [{ application: "archive", uses: result.applications[1]!.borrowed[0]!.uses }];
  return result;
}

function renderPanel(
  selection: EditorSelection,
  run = vi.fn().mockResolvedValue("applied"),
  onSelect = vi.fn(),
  adjust?: (outline: ModelDraftOutline) => void,
) {
  const shown = outline();
  adjust?.(shown);
  render(
    <ElementPanel
      outline={shown}
      selection={selection}
      tab="attributes"
      onTab={vi.fn()}
      menuOpen={false}
      onMenuOpenChange={vi.fn()}
      canDrag={false}
      onOperation={vi.fn()}
      onSelect={onSelect}
      run={run}
      onPreview={vi.fn()}
    />,
  );
  return { run, onSelect };
}

describe("a type's page", () => {
  it("says where the type is maintained and which view of another application borrows it", () => {
    const { onSelect } = renderPanel({ show: "type", key: "bin" });
    expect(screen.getByText("Maintained in Shop")).toBeTruthy();
    expect(screen.getByText(/Also in/).parentElement?.textContent).toContain(
      "Archive — relation matrix Bins by shelf, rows · relation Stores · group Lists",
    );
    fireEvent.click(screen.getByRole("button", { name: "Bins by shelf" }));
    expect(onSelect).toHaveBeenCalledWith({ show: "group", application: "archive", key: "lists" });
  });
});

describe("an application's types", () => {
  const archive: EditorSelection = { show: "application", key: "archive" };
  const rowsOf = (name: string) => screen.getByRole("table", { name }).querySelectorAll("tr[data-row-key]");

  it("splits the held types, the types from other applications and the unused ones into three tables", () => {
    renderPanel(archive, undefined, undefined, (o) => {
      const app = o.applications[1]!;
      app.objectTypeKeys = ["bin", "area", "shelf"];
      app.ownTypes = ["shelf"];
      app.unused = ["area"];
      app.unlistable = ["area"];
    });
    expect(rowsOf("Object types of Archive")).toHaveLength(1);
    expect(screen.getByRole("heading", { name: /From other applications/ }).textContent).toContain("1");
    expect(screen.getByRole("heading", { name: /Listed, used by no view here/ }).textContent).toContain("1");
    expect(rowsOf("Types of Archive used by no view")[0]!.textContent).toContain("Can be unlisted");
  });

  it("omits the sections that are empty", () => {
    renderPanel({ show: "application", key: "shop" });
    expect(screen.queryByRole("heading", { name: /From other applications/ })).toBeNull();
    expect(screen.queryByRole("heading", { name: /Listed, used by no view here/ })).toBeNull();
  });

  it("says where a borrowed type comes from, which view uses it and by which relation, and opens it on its home", () => {
    const { onSelect } = renderPanel(archive);
    const row = rowsOf("Types of Archive from other applications")[0]!;
    expect(row.textContent).toContain("Shop");
    expect(row.textContent).toContain("matrix");
    expect(row.textContent).toContain("Bins by shelf · rows");
    expect(row.textContent).toContain("Stores");
    expect(row.textContent).toContain("Lists");
    fireEvent.click(row.querySelector("button.type-link")!);
    expect(onSelect).toHaveBeenCalledWith({ show: "type", key: "bin", application: "shop" });
  });
});

describe("a group's entries", () => {
  it("say whether each is a list or a borrowed list, and which view it opens on", () => {
    renderPanel({ show: "group", application: "archive", key: "lists" }, undefined, undefined, (o) => {
      const archive = o.applications[1]!;
      archive.views = [
        {
          key: "bins-by-shelf",
          name: "Bins by shelf",
          type: "relationMatrix",
          collection: "bin",
          shows: ["bin"],
          mark: "new",
        },
      ];
      archive.navigation.groups[0]!.entries = [{ collection: "bin" }, { view: "bins-by-shelf" }];
    });
    const rows = screen.getByRole("table", { name: "Entries of Lists" }).querySelectorAll("tr[data-row-key]");
    expect(rows[0]!.textContent).toContain("Borrowed list");
    expect(rows[0]!.textContent).toContain("relation matrix · Bins by shelf");
    expect(rows[1]!.textContent).toContain("Relation matrix");
    expect(rows[1]!.textContent).toContain("relation matrix · Bins by shelf");
  });

  it("call a type the application holds a list", () => {
    renderPanel({ show: "group", application: "shop", key: "lists" }, undefined, undefined, (o) => {
      o.applications[0]!.views[0]!.collection = "bin";
    });
    const row = screen.getByRole("table", { name: "Entries of Lists" }).querySelector("tr[data-row-key]")!;
    expect(row.textContent).toContain("List");
    expect(row.textContent).not.toContain("Borrowed");
    expect(row.textContent).toContain("table · Bins");
  });

  it("are reordered by dragging, sending the placement the Move up item sends", () => {
    const { run } = renderPanel({ show: "group", application: "shop", key: "lists" }, undefined, undefined, (o) => {
      const group = o.applications[0]!.navigation.groups[0]!;
      group.collections = ["bin", "shelf"];
      group.entries = [{ collection: "bin" }, { collection: "shelf" }];
    });
    const rows = screen.getByRole("table", { name: "Entries of Lists" }).querySelectorAll("tr[data-row-key]");
    const transfer = { setData: vi.fn(), effectAllowed: "" };
    fireEvent.dragStart(rows[1]!, { dataTransfer: transfer });
    fireEvent.dragOver(rows[0]!, { dataTransfer: transfer });
    fireEvent.drop(rows[0]!, { dataTransfer: transfer });
    expect(run).toHaveBeenCalledWith([
      { kind: "placeCollection", applicationKey: "shop", collection: "shelf", group: "lists", position: 0 },
    ]);
  });
});

describe("an application's navigation groups", () => {
  const archive: EditorSelection = { show: "application", key: "archive" };

  it("flips Starts folded in one click and sends the step", async () => {
    const { run } = renderPanel(archive);
    const box = screen.getByRole("checkbox", { name: "Starts folded: Lists" });
    expect((box as HTMLInputElement).checked).toBe(false);
    fireEvent.click(box);
    await waitFor(() =>
      expect(run).toHaveBeenCalledWith([
        { kind: "setNavigationGroup", applicationKey: "archive", group: "lists", collapsed: true },
      ]),
    );
    expect(await screen.findByText("Saved")).toBeTruthy();
  });

  /** A drag over a row at a height: jsdom's boxes are empty, so any height above 0 is the row's lower half. */
  function drag(from: Element, onto: Element, clientY: number) {
    const transfer = { setData: vi.fn(), effectAllowed: "" };
    fireEvent.dragStart(from, { dataTransfer: transfer });
    for (const type of ["dragOver", "drop"] as const) {
      const event = createEvent[type](onto, { dataTransfer: transfer });
      Object.defineProperty(event, "clientY", { value: clientY });
      fireEvent(onto, event);
    }
  }
  const groupRows = () =>
    screen.getByRole("table", { name: "Navigation groups of Archive" }).querySelectorAll("tr[data-row-key]");

  it("moves a group dropped before another to that place, as Move up does", () => {
    const { run } = renderPanel(archive);
    const rows = groupRows();
    drag(rows[1]!, rows[0]!, 0);
    expect(run).toHaveBeenCalledWith([
      { kind: "setNavigationGroup", applicationKey: "archive", group: "more", position: 0 },
    ]);
  });

  it("moves a group dropped after the next one to that one's index, as Move down does", () => {
    const { run } = renderPanel(archive);
    const rows = groupRows();
    drag(rows[0]!, rows[1]!, 1);
    expect(run).toHaveBeenCalledWith([
      { kind: "setNavigationGroup", applicationKey: "archive", group: "lists", position: 1 },
    ]);
  });

  it("does nothing for a drop that leaves the row where it is", () => {
    const { run } = renderPanel(archive);
    const rows = groupRows();
    drag(rows[0]!, rows[0]!, 0);
    expect(run).not.toHaveBeenCalled();
  });
});
