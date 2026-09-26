import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { ObjectTable } from "@/ui/ObjectTable";
import { staticWindow } from "@/test/cursorWindow";
import { SortMenu, useTableSort } from "@/ui/TableSort";
import { attributeName } from "@/model/fields";

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
    expect(screen.getByText("Timetable types")).toBeInTheDocument();
    expect(screen.getByText("Codelist")).toBeInTheDocument();
  });

  it("resizes configured data columns by keyboard without resizing the actions column", () => {
    const onColumnWidth = vi.fn();
    render(
      <ObjectTable
        model={testModel}
        columns={["name", "code"]}
        list={staticWindow([domainObject])}
        pageSize={20}
        onOpen={() => {}}
        onColumnWidth={onColumnWidth}
        renderActions={() => <button>Actions</button>}
      />,
    );
    fireEvent.keyDown(screen.getByRole("separator", { name: "Resize Name column" }), { key: "ArrowRight" });
    expect(onColumnWidth).toHaveBeenCalledWith("name", 190);
    expect(screen.getAllByRole("separator")).toHaveLength(2);
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
});
