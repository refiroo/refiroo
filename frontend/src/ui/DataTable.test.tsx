import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fixedWindow } from "@/lib/hooks/useCursorWindow";
import { DataTable } from "@/ui/DataTable";
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

afterEach(() => vi.unstubAllGlobals());

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
