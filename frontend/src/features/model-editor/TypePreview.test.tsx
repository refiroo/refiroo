import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { TypePreview } from "@/features/model-editor/TypePreview";
import { ToastProvider } from "@/ui/Toast";
import { domainObject, testModel } from "@/test/fixtures";
import type { EngineModel } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return {
    ...actual,
    api: Object.fromEntries(
      Object.keys(actual.api).map((key) => [
        key,
        vi.fn(async () => ({ items: [], nextCursor: null, prevCursor: null })),
      ]),
    ),
  };
});

// Domains are listed in two applications; only "shelf-app" has a table view for them, and the workspace's
// records belong to it (the user's draft shape: records in the application with the table views).
const base = testModel.applications[0]!;
const model: EngineModel = {
  ...testModel,
  applications: [
    { ...base, key: "first-app", name: "First app", views: [], defaultView: "" },
    { ...base, key: "shelf-app", name: "Shelf app" },
  ],
};
const record = { ...domainObject, applicationKey: "shelf-app" };

function show(applicationKey?: string) {
  return render(
    <ToastProvider>
      <TypePreview
        mode="preview"
        draftId="d1"
        version={1}
        objectTypeKey="domain"
        applicationKey={applicationKey}
        activeModel={model}
        workspaceKey="default"
        send={vi.fn()}
        onDialog={vi.fn()}
        onShowIssues={vi.fn()}
        actions={null}
      />
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.modelDraftModel).mockResolvedValue({
    version: 1,
    valid: true,
    diagnostics: [],
    model,
    placements: model.placements,
  });
  vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.model).mockResolvedValue(model);
  vi.mocked(api.object).mockResolvedValue(record);
  vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.relations).mockResolvedValue({ items: [], nextCursor: null, prevCursor: null });
  vi.mocked(api.objects).mockImplementation(async (_type, query) => ({
    items: !query?.applicationKey || query.applicationKey === "shelf-app" ? [record] : [],
    nextCursor: null,
    prevCursor: null,
  }));
});

describe("TypePreview application", () => {
  it("shows the application that owns the workspace's records and reads records for it", async () => {
    show();
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith("domain", expect.objectContaining({ applicationKey: "shelf-app" })),
    );
    expect(vi.mocked(api.objects).mock.calls.some(([, query]) => query?.applicationKey === "first-app")).toBe(false);
    expect(await screen.findByRole("button", { name: "Application: Shelf app" })).toBeTruthy();
  });

  it("names the application that holds the records when the one named has none, and reads for the one named", async () => {
    show("first-app");
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith("domain", expect.objectContaining({ applicationKey: "first-app" })),
    );
    expect(await screen.findByText(/are in Shelf app/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Show Shelf app" })).toBeTruthy();
  });
});
