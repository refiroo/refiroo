import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RelationGridChangeDialog } from "@/features/objects/RelationGridChangeDialog";
import type { AttributeTypeDefinition } from "@/types";

const relationGridChange = vi.hoisted(() => vi.fn());
vi.mock("@/features/workspaces/WorkspaceDataContext", () => ({ useDataApi: () => ({ relationGridChange }) }));

const attributes = [
  { key: "note", name: "Note", valueType: "json" },
  { key: "role", name: "Role", valueType: "text" },
] as unknown as AttributeTypeDefinition[];

function open() {
  render(
    <RelationGridChangeDialog
      applicationKey="app"
      viewKey="grid"
      workspaceKey="west"
      noun={["person", "people"]}
      toNoun={["site", "sites"]}
      attributes={attributes}
      columns={[{ id: "c1", label: "North" }] as never}
      selection={{ mode: "ids", ids: new Map([["p1", { id: "p1", name: "Ann" }]]) } as never}
      selected={1}
      search=""
      filters={[]}
      onClose={() => undefined}
      onApplied={() => undefined}
    />,
  );
}

describe("RelationGridChangeDialog (R13-F23)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    relationGridChange.mockResolvedValue({ change: 1, same: 0, missing: 0, refused: [] });
  });

  it("drops the invalid-value error once Clear is chosen, and previews the clearing", async () => {
    open();
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "{not json" } });
    expect(await screen.findByText("That is not a valid value.")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Clear"));
    expect(screen.queryByText("That is not a valid value.")).toBeNull();
    await waitFor(() => expect(relationGridChange).toHaveBeenCalledWith(expect.objectContaining({ value: null })));
    await waitFor(() =>
      expect((screen.getByRole("button", { name: "Save" }) as HTMLButtonElement).disabled).toBe(false),
    );
  });

  it("forgets the invalid value when another attribute is chosen", async () => {
    open();
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "{not json" } });
    expect(await screen.findByText("That is not a valid value.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Attribute of the relationship"), { target: { value: "role" } });
    expect(screen.queryByText("That is not a valid value.")).toBeNull();
  });
});
