import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MissingRecords } from "@/features/model-editor/MissingRecords";
import { outlineFixture } from "@/test/draftOutline";
import type { ProfileSource } from "@/types";

const outline = outlineFixture();
const type = outline.objectTypes[0]!;
const source = (extra: Partial<ProfileSource> = {}): ProfileSource => ({
  id: "items",
  sheet: "Lists",
  headerRow: 1,
  applicationKey: null,
  objectTypeKey: type.key,
  key: { field: "name" },
  columns: [],
  ...extra,
});

describe("MissingRecords on a source's panel (PP-D82)", () => {
  it("shows Report as the choice, and Report is sent where it stands, without a question", () => {
    const run = vi.fn();
    render(<MissingRecords source={source({ missing: "delete" })} outline={outline} run={run} />);
    expect((screen.getByRole("radio", { name: "Delete them" }) as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("radio", { name: "Report them" }));
    expect(run).toHaveBeenCalledWith([{ kind: "setMissing", source: "items", missing: "report" }]);
  });

  it("asks once before Delete, saying what a load will then delete, and sends nothing on Cancel", () => {
    const run = vi.fn();
    render(<MissingRecords source={source()} outline={outline} run={run} />);
    expect((screen.getByRole("radio", { name: "Report them" }) as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("radio", { name: "Delete them" }));
    const question = screen.getByRole("alertdialog", { name: "Delete the records no row names?" });
    expect(question.textContent).toContain("no row of the file names");
    expect(question.textContent).toContain("change set");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(run).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("radio", { name: "Delete them" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete them on load" }));
    expect(run).toHaveBeenCalledWith([{ kind: "setMissing", source: "items", missing: "delete" }]);
  });

  it("is hidden for a source with no key or one that loads no records of its own", () => {
    const { container, rerender } = render(
      <MissingRecords source={source({ key: null })} outline={outline} run={vi.fn()} />,
    );
    expect(container.textContent).toBe("");
    rerender(<MissingRecords source={source({ record: "existing" })} outline={outline} run={vi.fn()} />);
    expect(container.textContent).toBe("");
  });
});
