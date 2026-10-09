import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { testModel } from "@/test/fixtures";
import type { Job } from "@/types";
import { ExportDialog, type ExportStart } from "./ExportDialog";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { createExport: vi.fn(), workspaces: vi.fn() },
}));

const queued = { id: "j1", kind: "export", state: "queued" } as Job;

const fromCollection: ExportStart = {
  workspaceKey: "west",
  changeSetId: "cs1",
  objectTypeKeys: ["domain", "codelist"],
  selected: ["domain"],
  filters: {
    objectTypeKey: "domain",
    filters: [
      { field: "code", operator: "startsWith", value: "CL" },
      { field: "active", operator: "eq", value: "true" },
    ],
  },
  search: "station",
  parentObjectId: "p1",
};

function open(start: ExportStart, onStarted = vi.fn()) {
  render(<ExportDialog model={testModel} start={start} onClose={vi.fn()} onStarted={onStarted} />);
  return onStarted;
}

describe("ExportDialog (0.9 J1u)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.createExport).mockResolvedValue(queued);
  });

  it("exports what the collection shows: its type, context, filters as criteria and scope, not its search", async () => {
    const onStarted = open(fromCollection);
    expect(screen.getByText(/search “station” is not applied/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start export" }));
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(queued));
    expect(api.createExport).toHaveBeenCalledWith({
      workspaceKey: "west",
      context: { changeSetId: "cs1", publicationId: null },
      scope: {
        types: [
          {
            objectTypeKey: "domain",
            where: [
              { field: "code", op: "startsWith", value: "CL" },
              { field: "active", op: "eq", value: true },
              { field: "parentObjectId", op: "eq", value: "p1" },
            ],
          },
        ],
        parentObjectId: null,
        asOf: null,
      },
      include: { relations: "withinScope" },
      format: "xlsx",
    });
  });

  it("drops the page's scope when unticked and sends the chosen relationships and format", async () => {
    open(fromCollection);
    fireEvent.click(screen.getByRole("checkbox", { name: /narrowed to/ }));
    fireEvent.click(screen.getByRole("radio", { name: "None" }));
    fireEvent.click(screen.getByRole("radio", { name: "CSV" }));
    fireEvent.click(screen.getByRole("button", { name: "Start export" }));
    await waitFor(() => expect(api.createExport).toHaveBeenCalled());
    const body = vi.mocked(api.createExport).mock.calls[0][0];
    expect(body.scope.types[0].where.map((item) => ("field" in item ? item.field : "related"))).toEqual([
      "code",
      "active",
    ]);
    expect(body.include.relations).toBe("none");
    expect(body.format).toBe("csv");
  });

  it("shows a refusal at the field its pointer names", async () => {
    vi.mocked(api.createExport).mockRejectedValue(
      new ApiError(422, "INVALID_QUERY", "Unknown field 'code'", { path: "/scope/types/0/where/0/field" }),
    );
    open(fromCollection);
    fireEvent.click(screen.getByRole("button", { name: "Start export" }));
    const field = await screen.findByText("Unknown field 'code'");
    expect(field.closest(".form-field")).toHaveTextContent("Record types");
    expect(screen.queryByText("The export was not started")).not.toBeInTheDocument();
  });

  it("from Jobs, chooses a workspace and starts with no type", async () => {
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [
        { key: "east", label: "East", status: "active", version: 1, createdAt: "", updatedAt: "" },
        { key: "west", label: "West", status: "active", version: 1, createdAt: "", updatedAt: "" },
      ],
      nextCursor: null,
    });
    open({ objectTypeKeys: ["domain", "codelist"], selected: [] });
    const workspace = await screen.findByRole("combobox", { name: "Workspace" });
    await waitFor(() => expect(workspace).toHaveValue("east"));
    expect(screen.getByRole("button", { name: "Start export" })).toBeDisabled();
  });
});
