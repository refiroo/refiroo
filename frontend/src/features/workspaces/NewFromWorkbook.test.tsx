import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import * as fromWorkbook from "@/features/workspaces/fromWorkbook";
import { NewFromWorkbook } from "@/features/workspaces/NewFromWorkbook";
import type { DryRun, Job, ModelDraft } from "@/types";

vi.mock("@/features/workspaces/fromWorkbook", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/workspaces/fromWorkbook")>()),
  lookAtWorkbook: vi.fn(),
}));

const draft = { id: "d1", name: "Office supplies", version: 7 } as ModelDraft;
const dryRun = {
  state: "completed",
  summary: {
    coverage: "complete",
    rows: { total: 12, run: 12 },
    sources: [
      {
        source: 0,
        sheet: "Items",
        objectTypeKey: "item",
        rows: 12,
        skippedRows: 0,
        rejections: [{ code: "MISSING_RECORD_KEY", rows: 2 }],
      },
    ],
    difference: null,
    previousJobId: null,
    ranAt: "",
  },
} as unknown as DryRun;

const book = new File(["x"], "office-supplies.xlsx");

function open() {
  const props = {
    onClose: vi.fn(),
    onCreated: vi.fn(),
    onNavigate: vi.fn(),
    onOtherWays: vi.fn(),
  };
  render(<NewFromWorkbook {...props} />);
  return props;
}

async function readTheWorkbook() {
  vi.mocked(fromWorkbook.lookAtWorkbook).mockResolvedValue({
    draft,
    dryRun,
    reasons: { MISSING_RECORD_KEY: "The row has no key" },
    typeNames: { item: "Item" },
  });
  const field = screen.getByLabelText(/Workbook/);
  fireEvent.change(field, { target: { files: [book] } });
  fireEvent.click(screen.getByRole("button", { name: "Read the workbook" }));
  await screen.findByText("What refiroo found");
}

describe("NewFromWorkbook", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.mocked(fromWorkbook.lookAtWorkbook).mockReset();
  });

  it("starts with the file and a name taken from the file's name", () => {
    open();
    expect(screen.getByRole("button", { name: "Read the workbook" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Workbook/), { target: { files: [book] } });
    expect(screen.getByLabelText("Name")).toHaveValue("Office supplies");
    expect(screen.getByRole("button", { name: "Read the workbook" })).toBeEnabled();
  });

  it("says what it found, row by row, with why rows do not load", async () => {
    open();
    await readTheWorkbook();
    expect(screen.getByText(/12 rows checked, every one: 2 do not load\./)).toBeInTheDocument();
    expect(screen.getByText("Item")).toBeInTheDocument();
    expect(screen.getByText(/10 rows load/)).toBeInTheDocument();
    expect(screen.getByText(/2 rows do not load: The row has no key/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create workspace" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Adjust" })).toBeInTheDocument();
  });

  it("creates the workspace in one step and lands on it", async () => {
    const created = vi.spyOn(api, "createWorkspaceFromWorkbook").mockResolvedValue({
      workspace: { key: "office-supplies" },
      job: { id: "j1" } as Job,
    } as never);
    const props = open();
    await readTheWorkbook();
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));
    await waitFor(() => expect(props.onCreated).toHaveBeenCalledWith("office-supplies"));
    expect(created).toHaveBeenCalledWith({ draftId: "d1", expectedVersion: 7, name: "Office supplies" });
    expect(fromWorkbook.workspaceLoadOf("office-supplies")).toEqual({ jobId: "j1", file: "office-supplies.xlsx" });
  });

  it("shows the draft's problems when the engine refuses it", async () => {
    vi.spyOn(api, "createWorkspaceFromWorkbook").mockRejectedValue(
      new ApiError(422, "INVALID_MODEL", "Model draft is invalid and cannot be installed", [
        { message: "Type 'item' has no key attribute", path: "/objectTypes/0" },
      ]),
    );
    open();
    await readTheWorkbook();
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));
    expect(await screen.findByText(/Model draft is invalid/)).toBeInTheDocument();
    expect(screen.getByText("Type 'item' has no key attribute (/objectTypes/0)")).toBeInTheDocument();
  });

  it("opens the draft's workbook canvas on Adjust", async () => {
    const props = open();
    await readTheWorkbook();
    fireEvent.click(screen.getByRole("button", { name: "Adjust" }));
    expect(props.onNavigate).toHaveBeenCalledWith({
      kind: "settings",
      page: "model",
      draftId: "d1",
      editor: { show: "canvas" },
    });
  });

  it("removes the draft on Cancel and keeps today's way folded under More ways to start", async () => {
    const removed = vi.spyOn(api, "deleteModelDraft").mockResolvedValue(undefined as never);
    const props = open();
    expect(screen.queryByRole("button", { name: "New workspace on an installed model" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /More ways to start/ }));
    fireEvent.click(screen.getByRole("button", { name: "New workspace on an installed model" }));
    expect(props.onOtherWays).toHaveBeenCalled();
    props.onClose.mockClear();
    await readTheWorkbook();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(props.onClose).toHaveBeenCalled());
    expect(removed).toHaveBeenCalledWith("d1", 7);
  });

  it("with no list found says so, makes Adjust the one way on and does not show Create workspace", async () => {
    open();
    vi.mocked(fromWorkbook.lookAtWorkbook).mockResolvedValue({ draft, reasons: {}, typeNames: {} });
    fireEvent.change(screen.getByLabelText(/Workbook/), { target: { files: [book] } });
    fireEvent.click(screen.getByRole("button", { name: "Read the workbook" }));
    await screen.findByText("What refiroo found");
    expect(screen.getByText(/found no list in this workbook by itself/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Adjust" })).toHaveClass("primary");
    expect(screen.queryByRole("button", { name: "Create workspace" })).not.toBeInTheDocument();
  });
});
