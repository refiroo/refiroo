import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { domainObject, testModel } from "../test/fixtures";
import { CollectionView } from "./CollectionView";

vi.mock("../api/client", () => ({
  ApiError: class ApiError extends Error {},
  api: { objects: vi.fn(), deleteObject: vi.fn(), object: vi.fn() },
}));

describe("CollectionView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
  });

  it("uses one generic component with workspace and URL-derived query state", async () => {
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{ search: "station", states: ["active", "draft"], sort: "-updatedAt", pageSize: 50 }}
        onQueryChange={vi.fn()}
        onOpen={vi.fn()}
        onChanged={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith(
        "domain",
        expect.objectContaining({
          applicationKey: "test-app",
          workspaceKey: "west",
          search: "station",
          state: ["active", "draft"],
          sort: "-updatedAt",
          pageSize: 50,
        }),
      ),
    );
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("keeps a failed request distinct and retries it", async () => {
    vi.mocked(api.objects)
      .mockRejectedValueOnce(new Error("Collection unavailable"))
      .mockResolvedValueOnce({ items: [domainObject], nextCursor: null });
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{ search: "", states: [], sort: "name", pageSize: 20 }}
        onQueryChange={vi.fn()}
        onOpen={vi.fn()}
        onChanged={vi.fn()}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Connections")).toBeInTheDocument();
    expect(api.objects).toHaveBeenCalledTimes(2);
  });
});
