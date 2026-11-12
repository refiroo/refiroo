import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fixedWindow } from "@/lib/hooks/useCursorWindow";
import { DataTable, columnsToFold } from "@/ui/DataTable";
import { EditInPlaceCell } from "@/ui/EditInPlace";

interface Row {
  id: string;
  name: string;
}

const rows: Row[] = [
  { id: "a", name: "Alpha" },
  { id: "b", name: "Bravo" },
  { id: "c", name: "Charlie" },
];

function table() {
  return render(
    <DataTable<Row>
      columns={[
        {
          key: "name",
          label: "Name",
          cell: (row) => (
            <EditInPlaceCell name="Name" record={row.name} onEdit={vi.fn()} onRemove={vi.fn()}>
              {row.name}
            </EditInPlaceCell>
          ),
        },
      ]}
      list={fixedWindow(rows)}
      rowKey={(row) => row.id}
      rowAttributes={() => ({ tabIndex: -1 })}
      label="Rows"
      noun={["row", "rows"]}
      pageSize={20}
      emptyMessage="None"
    />,
  );
}

const editButtons = () =>
  screen.queryAllByRole("button", { name: /^Edit Name of / }).map((button) => button.getAttribute("aria-label"));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const hoverScreen = () =>
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query === "(hover: hover)",
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));

describe("edit controls in a table (0.11 X6)", () => {
  it("are drawn in the row the pointer is over or that holds focus, and keep their room elsewhere", () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query === "(hover: hover)",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    const { container } = table();
    expect(editButtons()).toEqual([]);
    expect(container.querySelectorAll(".cell-edit-actions-kept[data-icons='2']")).toHaveLength(3);

    const bravo = screen.getByText("Bravo").closest("tr")!;
    act(() => {
      fireEvent.pointerOver(bravo);
    });
    expect(editButtons()).toEqual(["Edit Name of Bravo"]);

    const charlie = screen.getByText("Charlie").closest("tr")!;
    act(() => charlie.focus());
    expect(editButtons()).toEqual(["Edit Name of Bravo", "Edit Name of Charlie"]);

    act(() => {
      fireEvent.pointerLeave(bravo.closest("tbody")!);
    });
    expect(editButtons()).toEqual(["Edit Name of Charlie"]);
  });

  it("are drawn in every row on a screen without hover, as before", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
    table();
    expect(editButtons()).toEqual(["Edit Name of Alpha", "Edit Name of Bravo", "Edit Name of Charlie"]);
  });
});

describe("rows drawn once (0.12 LS1, D373)", () => {
  it("draws no row again when the table draws again with the same rows; pointing draws only the row pointed at", () => {
    hoverScreen();
    const cell = vi.fn((row: Row) => row.name);
    const columns = [{ key: "name", label: "Name", cell }];
    const list = fixedWindow(rows);
    const rowKey = (row: Row) => row.id;
    const element = (
      <DataTable<Row>
        columns={columns}
        list={list}
        rowKey={rowKey}
        label="Rows"
        noun={["row", "rows"]}
        pageSize={20}
        emptyMessage="None"
      />
    );
    const { rerender } = render(element);
    const drawn = cell.mock.calls.length;
    expect(drawn).toBeGreaterThan(0);
    rerender(element);
    const cut = screen.getByText("Bravo").closest("td")!;
    Object.defineProperty(cut, "scrollWidth", { configurable: true, value: 600 });
    Object.defineProperty(cut, "clientWidth", { configurable: true, value: 200 });
    act(() => {
      fireEvent.pointerOver(cut, { pointerType: "mouse" });
    });
    expect(document.querySelector(".cell-reveal")?.textContent).toBe("Bravo");
    // The row under the pointer draws its edit controls; the cell's whole value draws nothing.
    expect(cell.mock.calls.slice(drawn).map(([row]) => row.name)).toEqual(["Bravo"]);
  });

  it("draws no edit controls in rows passing under a still pointer while the list scrolls", () => {
    hoverScreen();
    table();
    const bravo = screen.getByText("Bravo").closest("tr")!;
    act(() => {
      fireEvent.scroll(window);
      fireEvent.pointerOver(bravo);
    });
    expect(editButtons()).toEqual([]);
    const later = performance.now() + 1000;
    vi.spyOn(performance, "now").mockReturnValue(later);
    act(() => {
      fireEvent.pointerMove(bravo);
    });
    expect(editButtons()).toEqual(["Edit Name of Bravo"]);
  });
});

describe("columnsToFold (0.17 SH1)", () => {
  const columns = [
    { key: "name", pinned: true },
    { key: "code", pinned: false },
    { key: "kind", pinned: false },
    { key: "state", pinned: false },
  ];
  // The actions column is the last width; nothing leads here.
  const widths = [300, 120, 120, 120, 48];

  it("folds nothing when the columns fit", () => {
    expect(columnsToFold(columns, widths, 900, 0)).toEqual([]);
  });

  it("folds from the right until what is left fits, and never the name", () => {
    expect(columnsToFold(columns, widths, 600, 0)).toEqual(["state"]);
    expect(columnsToFold(columns, widths, 500, 0)).toEqual(["state", "kind"]);
    expect(columnsToFold(columns, widths, 100, 0)).toEqual(["state", "kind", "code"]);
  });

  it("counts a leading selection column's place", () => {
    expect(columnsToFold(columns, [40, 300, 120, 120, 120, 48], 600, 1)).toEqual(["state", "kind"]);
  });

  it("keeps a narrow column that fits after a wide one that does not", () => {
    const wide = [
      { key: "name", pinned: true },
      { key: "id", pinned: false },
      { key: "code", pinned: false },
      { key: "state", pinned: false },
    ];
    // 280 + 340 + 110 + 90 = 820 in 500: the id cannot stay, the code and the state can.
    expect(columnsToFold(wide, [280, 340, 110, 90], 500, 0)).toEqual(["id"]);
  });
});
