import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { ObjectTable } from "@/ui/ObjectTable";
import { staticWindow } from "@/test/cursorWindow";
import { SortMenu, useTableSort } from "@/ui/TableSort";
import { attributeName } from "@/model/fields";
import { objectTypeHue } from "@/model/hues";
import type { EngineModel } from "@/types";

describe("ObjectTable", () => {
  it("renders model-derived column headers and values for one object type", () => {
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([domainObject])}
        pageSize={20}
        onOpen={() => {}}
      />,
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Code")).toBeInTheDocument();
    expect(screen.getByText("Connections")).toBeInTheDocument();
    expect(screen.getByText("CONNECTIONS")).toBeInTheDocument();
  });

  it("renders the same generic columns for a different object type", () => {
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "objectType"]}
        list={staticWindow([codelistObject])}
        pageSize={20}
        onOpen={() => {}}
      />,
    );
    expect(screen.getByText("Means of transport")).toBeInTheDocument();
    expect(screen.getByText("Codelist")).toBeInTheDocument();
  });

  it("resizes configured data columns by keyboard without resizing the actions column", () => {
    const onColumnWidths = vi.fn();
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([domainObject])}
        pageSize={20}
        onOpen={() => {}}
        onColumnWidths={onColumnWidths}
        renderActions={() => <button>Actions</button>}
      />,
    );
    fireEvent.keyDown(screen.getByRole("separator", { name: "Resize Name column" }), { key: "ArrowRight" });
    // The first resize keeps every other column at the width it was drawn with.
    expect(onColumnWidths).toHaveBeenCalledWith({ name: 190, code: 180 });
    expect(screen.getAllByRole("separator")).toHaveLength(2);
    // A header is named by its label alone; its handle stands outside it (UA7).
    expect(screen.getByRole("columnheader", { name: "Name" })).not.toContainElement(
      screen.getByRole("separator", { name: "Resize Name column" }),
    );
  });

  it("sizes a column narrower than its content once widths are set (UA4 revision)", () => {
    const onColumnWidths = vi.fn();
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([domainObject])}
        pageSize={20}
        onOpen={() => {}}
        columnWidths={{ name: 60, code: 200 }}
        onColumnWidths={onColumnWidths}
      />,
    );
    const table = screen.getByRole("table");
    expect(table).toHaveClass("sized-columns");
    expect(screen.getByRole("columnheader", { name: /Name/ }).style.getPropertyValue("--column-width")).toBe("60px");
    fireEvent.keyDown(screen.getByRole("separator", { name: "Resize Name column" }), { key: "Home" });
    expect(onColumnWidths).toHaveBeenCalledWith({ name: 48, code: 200 });
  });

  describe("sorting (S4R3)", () => {
    function SortedTable({
      columns,
      sortFields,
      initial = "name",
      onSort = () => {},
    }: {
      columns: string[];
      sortFields: string[];
      initial?: string;
      onSort?: (sort: string) => void;
    }) {
      const [sort, setSort] = useState(initial);
      const sorting = useTableSort({
        sort,
        fields: sortFields,
        onSort: (next) => {
          onSort(next);
          setSort(next);
        },
        labelFor: (field) => attributeName(testModel, field),
      });
      return (
        <>
          {/* The caller's toolbar carries the Sort menu, as the lens and panels do. */}
          <SortMenu sorting={sorting} />
          <ObjectTable
            model={testModel}
            columns={columns}
            sorting={sorting}
            list={staticWindow([domainObject])}
            pageSize={20}
            onOpen={() => {}}
          />
        </>
      );
    }

    it("shows header states and toggles the order from the header", () => {
      const onSort = vi.fn();
      render(<SortedTable columns={["name", "code", "objectType"]} sortFields={["name", "code"]} onSort={onSort} />);
      const name = screen.getByRole("columnheader", { name: /Name/ });
      expect(name).toHaveAttribute("aria-sort", "ascending");
      expect(screen.getByRole("columnheader", { name: "Code" })).not.toHaveAttribute("aria-sort");
      // A column outside the declared sort fields is a plain header.
      expect(within(screen.getByRole("columnheader", { name: "Type" })).queryByRole("button")).toBeNull();

      const nameButton = screen.getByRole("button", { name: "Name, sorted ascending" });
      expect(nameButton).toHaveAttribute("type", "button");
      fireEvent.click(nameButton);
      expect(onSort).toHaveBeenLastCalledWith("-name");
      expect(name).toHaveAttribute("aria-sort", "descending");
      expect(screen.getByText("Sorted by Name, descending")).toHaveAttribute("role", "status");
      fireEvent.click(screen.getByRole("button", { name: "Name, sorted descending" }));
      expect(onSort).toHaveBeenLastCalledWith("name");

      fireEvent.click(screen.getByRole("button", { name: "Code" }));
      expect(onSort).toHaveBeenLastCalledWith("code");
      expect(screen.getByRole("columnheader", { name: /Code/ })).toHaveAttribute("aria-sort", "ascending");
      expect(screen.getByRole("columnheader", { name: "Name" })).not.toHaveAttribute("aria-sort");
      expect(screen.getByText("Sorted by Code, ascending")).toHaveAttribute("role", "status");
    });

    it("always offers the sort menu while the list has sort fields", () => {
      render(<SortedTable columns={["name", "code"]} sortFields={["name", "code"]} />);
      expect(screen.getByRole("button", { name: "Sort: Name, ascending" })).toBeInTheDocument();
    });

    it("offers no sort menu without sort fields", () => {
      render(<SortedTable columns={["name", "code"]} sortFields={[]} />);
      expect(screen.queryByRole("button", { name: /^Sort/ })).not.toBeInTheDocument();
    });

    it("offers a sort menu for a field without a header, by keyboard", async () => {
      const onSort = vi.fn();
      render(<SortedTable columns={["name"]} sortFields={["name", "code"]} onSort={onSort} />);
      const trigger = screen.getByRole("button", { name: "Sort: Name, ascending" });
      fireEvent.keyDown(trigger, { key: "Enter" });
      fireEvent.keyUp(trigger, { key: "Enter" });
      const menu = await screen.findByRole("menu", { name: "Sort: Name, ascending" });
      expect(within(menu).getByRole("menuitemradio", { name: "Name" })).toHaveAttribute("aria-checked", "true");
      expect(within(menu).getByRole("menuitemradio", { name: "Ascending" })).toHaveAttribute("aria-checked", "true");
      fireEvent.click(within(menu).getByRole("menuitemradio", { name: "Code" }));
      expect(onSort).toHaveBeenLastCalledWith("code");

      fireEvent.click(screen.getByRole("button", { name: "Sort: Code, ascending" }));
      fireEvent.click(await screen.findByRole("menuitemradio", { name: "Descending" }));
      expect(onSort).toHaveBeenLastCalledWith("-code");
      expect(screen.getByRole("button", { name: "Sort: Code, descending" })).toBeInTheDocument();
    });

    it("keeps the column toggle free of sort controls at narrow widths", () => {
      render(<SortedTable columns={["name", "active", "objectType", "code"]} sortFields={["name", "code"]} />);
      const controls = screen.getByRole("button", { name: "Show all 4 columns" }).closest(".table-controls")!;
      expect(within(controls as HTMLElement).queryByRole("button", { name: /^Sort/ })).toBeNull();
      // The toolbar's menu reaches the collapsed Code column instead.
      expect(screen.getAllByRole("button", { name: /^Sort/ })).toHaveLength(1);
    });

    it("renders plain headers without a sort", () => {
      render(
        <ObjectTable
          model={testModel}
          columns={["name"]}
          list={staticWindow([domainObject])}
          pageSize={20}
          onOpen={() => {}}
        />,
      );
      expect(screen.getByRole("columnheader", { name: "Name" })).not.toHaveAttribute("aria-sort");
      expect(screen.queryByRole("button", { name: /Sort|Name/ })).not.toBeInTheDocument();
    });
  });

  describe("colour for kinds of record (ADR-040, UA3)", () => {
    // The same table in two model configurations: the type order, and so each type's hue, differs.
    const reordered: EngineModel = { ...testModel, objectTypes: [...testModel.objectTypes].reverse() };

    it.each([
      ["the fixture model", testModel],
      ["the same types in the other order", reordered],
    ])(
      "shows a parent column as a chip in the parent's type colour and the selected row in its own (%s)",
      (_, model) => {
        const [parent, own] = [codelistObject.path[0].objectTypeKey, codelistObject.objectTypeKey];
        render(
          <ObjectTable
            model={model}
            columns={["name", `ancestor:${parent}`, "active"]}
            list={staticWindow([codelistObject])}
            pageSize={20}
            selectedId={codelistObject.id}
            onOpen={() => {}}
          />,
        );
        const chip = screen.getByText(codelistObject.path[0].name).closest(".record-chip");
        expect(chip).toHaveAttribute("data-hue", String(objectTypeHue(model, parent)));
        const row = screen.getByRole("button", { name: codelistObject.name }).closest("tr");
        expect(row).toHaveClass("selected-record");
        expect(row).toHaveAttribute("data-hue", String(objectTypeHue(model, own)));
        expect(objectTypeHue(model, parent)).not.toBe(objectTypeHue(model, own));
        // A value is plain text, not a pill (ADR-039).
        expect(within(row as HTMLElement).getByText("No")).not.toHaveClass("pill");
      },
    );

    it("shows a dash where the record has no parent of the column's type", () => {
      render(
        <ObjectTable
          model={testModel}
          columns={["name", `ancestor:${codelistObject.objectTypeKey}`]}
          list={staticWindow([domainObject])}
          pageSize={20}
          onOpen={() => {}}
        />,
      );
      expect(document.querySelector(".record-chip")).toBeNull();
      expect(screen.getByText("—")).toBeInTheDocument();
    });
  });

  it("loads in rows of the table's shape, announced once", () => {
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([], { loading: true })}
        pageSize={20}
        onOpen={() => {}}
      />,
    );
    const loading = screen.getAllByRole("status").filter((status) => status.textContent === "Loading records…");
    expect(loading).toHaveLength(1);
    expect(document.querySelectorAll("tbody tr.loading-row")).toHaveLength(6);
  });

  it("shows the empty state with its icon and the action that fills the list", () => {
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([])}
        pageSize={20}
        onOpen={() => {}}
        emptyMessage="No domains yet"
        emptyIcon={<span data-testid="tile" />}
        emptyAction={<button>Add Domain</button>}
      />,
    );
    expect(screen.getByText("No domains yet")).toBeInTheDocument();
    expect(screen.getByTestId("tile").closest(".empty-message-icon")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("button", { name: "Add Domain" })).toBeInTheDocument();
  });

  describe("selection (0.9 K1)", () => {
    const rows = ["Alpha", "Beta", "Gamma"].map((name, index) => ({
      ...domainObject,
      id: `id-${index}`,
      name,
      version: index + 1,
    }));

    function Selecting({ onOpen = () => {} }: { onOpen?: () => void }) {
      const [selected, setSelected] = useState<string[]>([]);
      const [anchor, setAnchor] = useState<string>();
      const loaded = selected.length === rows.length ? "all" : selected.length ? "some" : "none";
      return (
        <ObjectTable
          model={testModel}
          columns={["name"]}
          list={staticWindow(rows)}
          pageSize={20}
          onOpen={onOpen}
          selection={{
            isSelected: (id) => selected.includes(id),
            loaded,
            onToggle: (item, extend) => {
              const from = rows.findIndex((row) => row.id === anchor);
              const to = rows.findIndex((row) => row.id === item.id);
              const ids =
                extend && from >= 0
                  ? rows.slice(Math.min(from, to), Math.max(from, to) + 1).map((row) => row.id)
                  : [item.id];
              setSelected((current) =>
                current.includes(item.id)
                  ? current.filter((id) => !ids.includes(id))
                  : [...new Set([...current, ...ids])],
              );
              setAnchor(item.id);
            },
            onToggleLoaded: () => setSelected(loaded === "all" ? [] : rows.map((row) => row.id)),
          }}
        />
      );
    }

    it("shows the header checkbox checked, partly checked or unchecked over the rows", () => {
      render(<Selecting />);
      const header = screen.getByRole("checkbox", { name: "Select the records shown" });
      expect(header).not.toBeChecked();
      expect((header as HTMLInputElement).indeterminate).toBe(false);
      fireEvent.click(screen.getByRole("checkbox", { name: "Select Beta" }));
      expect((header as HTMLInputElement).indeterminate).toBe(true);
      fireEvent.click(header);
      expect(header).toBeChecked();
      expect((header as HTMLInputElement).indeterminate).toBe(false);
      expect(screen.getAllByRole("checkbox", { checked: true })).toHaveLength(4);
      fireEvent.click(header);
      expect(screen.queryAllByRole("checkbox", { checked: true })).toHaveLength(0);
    });

    it("toggles a focused row with Space and extends the range with Shift+Space", () => {
      render(<Selecting />);
      const alpha = screen.getByRole("checkbox", { name: "Select Alpha" });
      alpha.focus();
      fireEvent.keyDown(alpha, { key: " " });
      expect(alpha).toBeChecked();
      fireEvent.keyDown(screen.getByRole("checkbox", { name: "Select Gamma" }), { key: " ", shiftKey: true });
      expect(screen.getByRole("checkbox", { name: "Select Beta" })).toBeChecked();
      expect(screen.getByRole("checkbox", { name: "Select Gamma" })).toBeChecked();
      expect(screen.getByRole("row", { name: /Beta/ })).toHaveClass("checked-row");
    });

    it("still opens the record from the row outside its checkbox", () => {
      const onOpen = vi.fn();
      render(<Selecting onOpen={onOpen} />);
      fireEvent.click(screen.getByRole("checkbox", { name: "Select Alpha" }));
      expect(onOpen).not.toHaveBeenCalled();
      fireEvent.click(screen.getByRole("row", { name: /Alpha/ }).querySelectorAll("td")[1]);
      expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ name: "Alpha" }));
    });

    it("has no selection column without a selection", () => {
      render(
        <ObjectTable model={testModel} columns={["name"]} list={staticWindow(rows)} pageSize={20} onOpen={() => {}} />,
      );
      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    });
  });
});
