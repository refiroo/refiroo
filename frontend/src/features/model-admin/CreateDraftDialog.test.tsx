import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { CreateDraftDialog } from "@/features/model-admin/CreateDraftDialog";
import { takeWaitingProposal } from "@/model/proposing";
import type { ModelDraft } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

describe("New from a workbook (0.10 A6b)", () => {
  it("proposes a new model in a draft that starts empty, without the active model (the user, 2026-10-14)", async () => {
    vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.system).mockResolvedValue({ schemaLanguages: ["0.9", "0.10"] } as Awaited<
      ReturnType<typeof api.system>
    >);
    vi.mocked(api.createModelDraft).mockResolvedValue({ id: "d1", name: "Catalogue" } as ModelDraft);
    vi.mocked(api.uploadSourceFile).mockResolvedValue({} as never);
    const onCreated = vi.fn();
    render(
      <CreateDraftDialog
        releases={[]}
        seed={{ name: "Catalogue", releaseId: "r1", workbook: true }}
        onClose={() => {}}
        onCreated={onCreated}
      />,
    );
    const file = new File(["k"], "office-supplies.xlsx");
    fireEvent.change(screen.getByLabelText("Workbook"), { target: { files: [file] } });
    expect(screen.getByLabelText("Starting document")).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: /A new model/ }));
    expect(screen.queryByLabelText("Starting document")).toBeNull();
    expect((screen.getByLabelText("Application name") as HTMLInputElement).value).toBe("Office supplies");
    fireEvent.click(screen.getByRole("button", { name: "Create and propose" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    const [body] = vi.mocked(api.createModelDraft).mock.calls[0];
    expect(body.baseReleaseId).toBeUndefined();
    expect(body.model).toMatchObject({ schemaVersion: "0.10", applications: [], objectTypes: [] });
    expect(api.modelRelease).not.toHaveBeenCalled();
    expect(takeWaitingProposal("d1")).toEqual({ mode: "newApplication", applicationName: "Office supplies" });
  });
});
