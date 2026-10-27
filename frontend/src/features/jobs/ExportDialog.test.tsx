import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { testModel, testWorkspaceModel, testAvailability } from "@/test/fixtures";
import type { EngineModel, Job } from "@/types";
import { ExportDialog, type ExportStart } from "./ExportDialog";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { createExport: vi.fn(), workspaces: vi.fn(), objects: vi.fn() },
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
    // The parent search of columns per parent (0.9 J6a) reads records.
    vi.mocked(api.objects).mockResolvedValue({ items: [], nextCursor: null, prevCursor: null } as never);
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
        {
          key: "east",
          label: "East",
          status: "active",
          version: 1,
          createdAt: "",
          updatedAt: "",
          model: testWorkspaceModel,
          availability: testAvailability,
        },
        {
          key: "west",
          label: "West",
          status: "active",
          version: 1,
          createdAt: "",
          updatedAt: "",
          model: testWorkspaceModel,
          availability: testAvailability,
        },
      ],
      nextCursor: null,
    });
    open({ objectTypeKeys: ["domain", "codelist"], selected: [] });
    const workspace = await screen.findByRole("combobox", { name: "Workspace" });
    await waitFor(() => expect(workspace).toHaveValue("east"));
    expect(screen.getByRole("button", { name: "Start export" })).toBeDisabled();
  });

  describe("a workbook for people (0.9 J6)", () => {
    // The test model with a relationship a table can show as a column.
    const model: EngineModel = {
      ...testModel,
      relationTypes: [
        ...testModel.relationTypes,
        {
          key: "domain-tags-codelist",
          reverseKey: "codelist-tags-domain",
          name: "Tags",
          reverseName: "Tagged by",
          isOriented: true,
          features: {},
        },
      ],
      objectTypeRelations: [
        ...testModel.objectTypeRelations,
        {
          relationTypeKey: "domain-tags-codelist",
          fromObjectTypeKey: "domain",
          toObjectTypeKey: "codelist",
          cardinality: "many-to-many",
        },
      ],
    };
    const fromTable: ExportStart = {
      ...fromCollection,
      columns: { shown: ["name", "related:domain-tags-codelist", "code"], hidden: ["active"] },
    };
    const openTable = (start = fromTable) =>
      render(<ExportDialog model={model} start={start} onClose={vi.fn()} onStarted={vi.fn()} />);

    it("stays technical until chosen, and is offered only from a collection", () => {
      openTable();
      expect(screen.getByRole("radio", { name: "Technical" })).toBeChecked();
      expect(screen.getByText("Record types")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Start export" }));
      expect(vi.mocked(api.createExport).mock.calls[0][0]).not.toHaveProperty("layout");
    });

    it("sends the table's columns in their order, a column's field and the sheets chosen in Advanced", async () => {
      openTable();
      fireEvent.click(screen.getByRole("radio", { name: "For people" }));
      expect(screen.queryByText("Record types")).not.toBeInTheDocument();
      expect(screen.queryByRole("radio", { name: "CSV" })).not.toBeInTheDocument();
      fireEvent.click(screen.getByText("Advanced: columns and sheets"));
      // The relationship the table shows as a column has a sheet of its own by default.
      const sheets = screen.getByRole("group", { name: "Relationships with a sheet of their own" });
      const sheet = within(sheets).getByRole("checkbox", { name: "Tags" });
      expect(sheet).toBeChecked();
      fireEvent.click(sheet);
      const columns = screen.getByRole("group", { name: "Columns of the main sheet" });
      fireEvent.click(within(columns).getByRole("checkbox", { name: "Active" }));
      fireEvent.click(screen.getByRole("button", { name: "Move Code up" }));
      fireEvent.change(screen.getByRole("combobox", { name: "Tags shows" }), { target: { value: "code" } });
      fireEvent.click(screen.getByRole("button", { name: "Start export" }));
      await waitFor(() => expect(api.createExport).toHaveBeenCalled());
      const body = vi.mocked(api.createExport).mock.calls[0][0];
      expect(body.format).toBe("xlsx");
      expect(body.layout).toBe("people");
      expect(body.scope.types.map((item) => item.objectTypeKey)).toEqual(["domain"]);
      expect(body.people).toEqual({
        columns: ["name", "code", "related:domain-tags-codelist", "active"],
        sheets: [],
        columnFields: { "related:domain-tags-codelist": "code" },
      });
    });

    it("shows a layout refusal in the workbook's section", async () => {
      vi.mocked(api.createExport).mockRejectedValue(
        new ApiError(422, "INVALID_EXPORT_LAYOUT", "Column 'gone' is no column", { path: "/people/columns/1" }),
      );
      openTable();
      fireEvent.click(screen.getByRole("radio", { name: "For people" }));
      fireEvent.click(screen.getByRole("button", { name: "Start export" }));
      expect(await screen.findByText("Column 'gone' is no column")).toBeInTheDocument();
      expect(screen.getByText("The workbook cannot be made this way")).toBeInTheDocument();
    });
  });

  describe("columns per parent and lists (0.9 J6a)", () => {
    // A relationship that owns its records: one binding, from the type, required.
    const model: EngineModel = {
      ...testModel,
      relationTypes: [
        ...testModel.relationTypes,
        {
          key: "domain-labels-codelist",
          reverseKey: "codelist-labels-domain",
          name: "Labels",
          reverseName: "Labelled",
          isOriented: true,
          features: {},
        },
      ],
      objectTypeRelations: [
        ...testModel.objectTypeRelations,
        {
          relationTypeKey: "domain-labels-codelist",
          fromObjectTypeKey: "domain",
          toObjectTypeKey: "codelist",
          cardinality: "one-to-many",
          required: true,
        },
      ],
    };
    const start: ExportStart = {
      ...fromCollection,
      columns: { shown: ["name", "related:domain-labels-codelist"], hidden: [] },
    };

    it("lays an owned relationship out as columns per parent with its fields, and turns lists off", async () => {
      render(<ExportDialog model={model} start={start} onClose={vi.fn()} onStarted={vi.fn()} />);
      fireEvent.click(screen.getByRole("radio", { name: "For people" }));
      fireEvent.click(screen.getByText("Advanced: columns and sheets"));
      fireEvent.click(screen.getByRole("radio", { name: "Columns per parent" }));
      const fields = screen.getByRole("group", { name: "Labels: fields per parent" });
      expect(within(fields).getByRole("checkbox", { name: "Code" })).toBeChecked();
      fireEvent.click(within(fields).getByRole("checkbox", { name: "Active" }));
      fireEvent.click(within(fields).getByRole("checkbox", { name: "Name" }));
      fireEvent.click(screen.getByRole("checkbox", { name: /offer a list to choose from/ }));
      fireEvent.click(screen.getByRole("button", { name: "Start export" }));
      await waitFor(() => expect(api.createExport).toHaveBeenCalled());
      const body = vi.mocked(api.createExport).mock.calls[0][0];
      expect(body.people?.sheets).toEqual(["domain-labels-codelist"]);
      expect(body.people?.ownedColumns).toEqual({
        "domain-labels-codelist": { parents: [], fields: ["name", "code"] },
      });
      expect(body.people?.referenceLists).toEqual([]);
    });

    it("keeps rows and every list by default", async () => {
      render(<ExportDialog model={model} start={start} onClose={vi.fn()} onStarted={vi.fn()} />);
      fireEvent.click(screen.getByRole("radio", { name: "For people" }));
      fireEvent.click(screen.getByRole("button", { name: "Start export" }));
      await waitFor(() => expect(api.createExport).toHaveBeenCalled());
      const body = vi.mocked(api.createExport).mock.calls[0][0];
      expect(body.people).not.toHaveProperty("ownedColumns");
      expect(body.people).not.toHaveProperty("referenceLists");
    });
  });
});
