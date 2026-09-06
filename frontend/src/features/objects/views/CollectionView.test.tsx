import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";

vi.mock("@/api/client", () => ({
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
        query={{
          search: "station",
          states: ["active", "draft"],
          sort: "-code",
          pageSize: 50,
          filters: [{ field: "code", operator: "startsWith", value: "CLI" }],
        }}
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
          sort: "-code",
          filters: [{ field: "code", operator: "startsWith", value: "CLI" }],
          pageSize: 50,
        }),
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: `More actions for ${domainObject.name}` }));
    expect(await screen.findByRole("menuitem", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Delete" })).toBeInTheDocument();
  });

  it("renders only model-declared typed filters and sorts", () => {
    const onQueryChange = vi.fn();
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{ search: "", states: [], sort: "name", pageSize: 20, filters: [] }}
        onQueryChange={onQueryChange}
        onOpen={vi.fn()}
        onChanged={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Code operator" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Active value" })).toBeInTheDocument();
    expect(screen.queryByLabelText("States")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Code operator" }), {
      target: { value: "startsWith" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Code value" }), { target: { value: "CLI" } });
    fireEvent.blur(screen.getByRole("textbox", { name: "Code value" }));
    expect(onQueryChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ filters: [{ field: "code", operator: "startsWith", value: "CLI" }] }),
    );
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
        query={{ search: "", states: [], sort: "name", pageSize: 20, filters: [] }}
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
