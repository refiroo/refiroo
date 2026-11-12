import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ColumnReadings, ListReadings, ReadingMarks } from "@/features/model-editor/ReadingEntries";
import { outlineFixture } from "@/test/draftOutline";
import type { DraftProfileDocument, ProfileSource, SourceColumn } from "@/types/sources";

const outline = outlineFixture();
const rowType = outline.objectTypes[0]!.key;

const owner: ProfileSource = {
  id: "items",
  sheet: "Sales",
  headerRow: 1,
  applicationKey: null,
  objectTypeKey: rowType,
  columns: [{ column: "Item", field: "name" }],
};
const column = (header: string): SourceColumn =>
  ({ sheet: "Sales", header, letter: "A", block: 0, valueTypes: { text: 3 }, placeholders: [] }) as never;
const columns = ["Item", "2023", "2024"].map(column);
const headers = ["Item", "2023", "2024"];
const profileOf = (source: ProfileSource): DraftProfileDocument => ({
  key: "p",
  name: "p",
  sources: [source],
  valueMaps: {},
});

function common(source: ProfileSource, run = vi.fn()) {
  return { profile: profileOf(source), outline, columns, sheet: "Sales", busy: false, run };
}

describe("the readings in the editor's column and list panels (CE1, PP-D77)", () => {
  it("fills blanks from the cell above as one setFillDown request, and offers the Stop entry once on", () => {
    const run = vi.fn();
    const { unmount } = render(
      <ColumnReadings {...common(owner, run)} owner={owner} header="Item" headers={headers} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Fill blanks from the cell above" }));
    expect(run).toHaveBeenCalledWith([{ kind: "setFillDown", source: "items", columns: ["Item"] }]);
    unmount();
    const on = { ...owner, fillDown: ["Item"] };
    render(<ColumnReadings {...common(on, run)} owner={on} header="Item" headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Stop filling blanks from the cell above" }));
    expect(run).toHaveBeenLastCalledWith([{ kind: "clearFillDown", source: "items" }]);
  });

  it("asks the heading column's name and parent, then sends the heading rows with the parent binding", () => {
    const run = vi.fn();
    render(<ColumnReadings {...common(owner, run)} owner={owner} header="Item" headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Rows holding only this column are headings…" }));
    expect(screen.getByText("Rows holding only Item are headings")).toBeInTheDocument();
    expect(screen.getByLabelText("The heading goes in a new column called")).toHaveValue("Item heading");
    fireEvent.click(screen.getByRole("button", { name: "Read headings" }));
    const operations = run.mock.calls[0]![0] as { kind: string }[];
    expect(operations[0]).toEqual({ kind: "setHeadingRows", source: "items", column: "Item", into: "Item heading" });
    expect(operations.at(-1)).toMatchObject({ kind: "mapColumn", column: "Item heading" });
  });

  it("stops reading headings", () => {
    const run = vi.fn();
    const on = { ...owner, headings: { column: "Item", into: "Group" } };
    render(<ColumnReadings {...common(on, run)} owner={on} header="Item" headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Stop reading rows holding only this column as headings" }));
    expect(run).toHaveBeenCalledWith([{ kind: "clearHeadingRows", source: "items" }]);
  });

  it("reads chosen columns as rows: the columns are ticked, the two names asked, one request sent", () => {
    const run = vi.fn();
    render(<ColumnReadings {...common(owner, run)} owner={owner} header="2023" headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Read these columns as rows…" }));
    expect(screen.getByRole("checkbox", { name: "2023" })).toBeChecked();
    // One column is not enough to read as rows.
    expect(screen.getByRole("button", { name: "Read as rows" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: "2024" }));
    expect(screen.getByLabelText("The column's header goes in")).toHaveValue("Year");
    fireEvent.click(screen.getByRole("button", { name: "Read as rows" }));
    const operations = run.mock.calls[0]![0] as { kind: string }[];
    expect(operations).toContainEqual({
      kind: "setUnpivot",
      source: "items",
      columns: ["2023", "2024"],
      nameColumn: "Year",
      valueColumn: "Value",
    });
    expect(operations.filter((item) => item.kind === "mapColumn")).toHaveLength(2);
  });

  it("offers Stop on a column that is read as rows, and from the list", () => {
    const run = vi.fn();
    const on = { ...owner, unpivot: { columns: ["2023", "2024"], nameColumn: "Year", valueColumn: "Value" } };
    const { unmount } = render(<ColumnReadings {...common(on, run)} owner={on} header="2023" headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Stop reading these columns as rows" }));
    expect(run).toHaveBeenLastCalledWith([{ kind: "clearUnpivot", source: "items" }]);
    unmount();
    render(<ListReadings {...common(on, run)} owner={on} headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Stop reading these columns as rows" }));
    expect(run).toHaveBeenCalledTimes(2);
  });

  it("asks which of the list's columns to read as rows", () => {
    const run = vi.fn();
    render(<ListReadings {...common(owner, run)} owner={owner} headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Read these columns as rows…" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "2023" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "2024" }));
    fireEvent.click(screen.getByRole("button", { name: "Read as rows" }));
    expect(run.mock.calls[0]![0]).toContainEqual(
      expect.objectContaining({ kind: "setUnpivot", columns: ["2023", "2024"] }),
    );
  });

  it("lands the new columns on the list's own object type, or on the one chosen in the question", () => {
    const other = outline.objectTypes.find((item) => item.key !== rowType)!;
    const run = vi.fn();
    const { unmount } = render(<ListReadings {...common(owner, run)} owner={owner} headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Read these columns as rows…" }));
    const select = screen.getByLabelText("The new columns are added to");
    expect(select).toHaveValue(rowType);
    fireEvent.click(screen.getByRole("checkbox", { name: "2023" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "2024" }));
    fireEvent.click(screen.getByRole("button", { name: "Read as rows" }));
    expect(run.mock.calls[0]![0]).toContainEqual(expect.objectContaining({ kind: "setUnpivot", source: "items" }));
    unmount();
    render(<ListReadings {...common(owner, run)} owner={owner} headers={headers} />);
    fireEvent.click(screen.getByRole("button", { name: "Read these columns as rows…" }));
    fireEvent.change(screen.getByLabelText("The new columns are added to"), { target: { value: other.key } });
    fireEvent.click(screen.getByRole("checkbox", { name: "2023" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "2024" }));
    fireEvent.click(screen.getByRole("button", { name: "Read as rows" }));
    const operations = run.mock.calls[1]![0] as { kind: string; objectType?: string; source?: string }[];
    expect(operations[0]).toMatchObject({ kind: "addSource", objectType: other.key });
    expect(operations).toContainEqual(expect.objectContaining({ kind: "setUnpivot", columns: ["2023", "2024"] }));
  });

  it("marks the columns a reading is on", () => {
    const on = { ...owner, fillDown: ["Item"] };
    render(<ReadingMarks profile={profileOf(on)} sheet="Sales" header="Item" />);
    expect(screen.getByText("blanks filled from above")).toBeInTheDocument();
  });
});
