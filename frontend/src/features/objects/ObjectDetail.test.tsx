import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { ObjectDetail } from "@/features/objects/ObjectDetail";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("ObjectDetail lifecycle controls", () => {
  it.each([domainObject, codelistObject])(
    "resizes $objectTypeKey properties while preserving inline input",
    async (object) => {
      const stored = new Map<string, string>();
      vi.stubGlobal("localStorage", {
        getItem: (key: string) => stored.get(key) ?? null,
        setItem: (key: string, value: string) => stored.set(key, value),
        removeItem: (key: string) => stored.delete(key),
      });
      vi.spyOn(api, "object").mockResolvedValue(object);
      vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "objects").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
      render(
        <ObjectDetail
          model={testModel}
          application={testModel.applications[0]}
          objectTypeKey={object.objectTypeKey}
          objectId={object.id}
          workspaceKey="default"
          onOpen={vi.fn()}
          onBack={vi.fn()}
          readOnly={false}
        />,
      );
      const divider = await screen.findByRole("separator", { name: "Resize record properties" });
      fireEvent.click(screen.getAllByRole("button", { name: "Edit" })[0]);
      const input = screen.getByLabelText("Code");
      fireEvent.change(input, { target: { value: "unsaved" } });
      fireEvent.keyDown(divider, { key: "ArrowLeft" });
      expect(divider).toHaveAttribute("aria-valuenow", "310");
      expect(input).toHaveValue("unsaved");
      const key = `rdm:layout:properties-width:v1:${object.applicationKey}:${object.objectTypeKey}`;
      expect(stored.get(key)).toBe("310");
      fireEvent.doubleClick(divider);
      expect(divider).toHaveAttribute("aria-valuenow", "300");
      expect(stored.has(key)).toBe(false);
      expect(input).toHaveValue("unsaved");
    },
  );
  it("follows a record whose type changed to its current type (D42)", async () => {
    const read = vi.spyOn(api, "object").mockRejectedValue(
      new ApiError(409, "OBJECT_TYPE_CHANGED", "The record is a domain in this change set.", {
        objectId: codelistObject.id,
        objectTypeKey: "domain",
        requestedObjectTypeKey: "codelist",
      }),
    );
    const onTypeChanged = vi.fn();
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey="codelist"
        objectId={codelistObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
        onTypeChanged={onTypeChanged}
      />,
    );
    await waitFor(() => expect(onTypeChanged).toHaveBeenCalledWith("domain"));
    expect(read).toHaveBeenCalledWith("codelist", codelistObject.id, "default");
    expect(screen.queryByText("Object unavailable")).not.toBeInTheDocument();
  });

  it.each([domainObject, codelistObject])("retries $objectTypeKey in the selected workspace", async (object) => {
    const read = vi
      .spyOn(api, "object")
      .mockRejectedValueOnce(new Error("Record temporarily unavailable"))
      .mockResolvedValueOnce({ ...object, workspaceKey: "west" });
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey={object.objectTypeKey}
        objectId={object.id}
        workspaceKey="west"
        onOpen={vi.fn()}
        onBack={vi.fn()}
        showBackToList={false}
      />,
    );
    expect(await screen.findByText("Record temporarily unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to list" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: object.name })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to list" })).not.toBeInTheDocument();
    expect(read).toHaveBeenNthCalledWith(1, object.objectTypeKey, object.id, "west");
    expect(read).toHaveBeenNthCalledWith(2, object.objectTypeKey, object.id, "west");
  });

  it("renders model-derived child collections and relationships when detail configuration is absent", async () => {
    vi.spyOn(api, "object").mockResolvedValue(domainObject);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    const children = vi.spyOn(api, "objects").mockResolvedValue({ items: [codelistObject], nextCursor: null });
    const relations = vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
    render(
      <ObjectDetail
        model={testModel}
        application={{ ...testModel.applications[0], details: [] }}
        objectTypeKey={domainObject.objectTypeKey}
        objectId={domainObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Relationships" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: codelistObject.name })).toBeInTheDocument();
    expect(children).toHaveBeenCalledWith("codelist", expect.objectContaining({ parentObjectId: domainObject.id }));
    expect(relations).toHaveBeenCalledWith(domainObject.id, expect.objectContaining({ direction: "both" }));
  });

  it("does not expose object retirement controls or call a retirement API", async () => {
    vi.spyOn(api, "object").mockResolvedValue(domainObject);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey="domain"
        objectId={domainObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Connections" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retire object" })).not.toBeInTheDocument();
    expect(screen.queryByText(/retir/i)).not.toBeInTheDocument();
  });
  it.each([domainObject, codelistObject])(
    "exposes live authoring and removes it when read-only for $objectTypeKey",
    async (object) => {
      vi.spyOn(api, "object").mockResolvedValue(object);
      vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "objects").mockResolvedValue({ items: [], nextCursor: null });
      vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
      const props = {
        model: testModel,
        application: testModel.applications[0],
        objectTypeKey: object.objectTypeKey,
        objectId: object.id,
        workspaceKey: "default",
        onOpen: vi.fn(),
        onBack: vi.fn(),
      };
      const { rerender } = render(<ObjectDetail {...props} readOnly={false} />);
      fireEvent.click(await screen.findByRole("button", { name: "Record actions" }));
      fireEvent.click(await screen.findByRole("menuitem", { name: "Edit all fields" }));
      expect(screen.getByLabelText("Name")).toHaveValue(object.name);
      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
      rerender(<ObjectDetail {...props} readOnly />);
      fireEvent.click(screen.getByRole("button", { name: "Record actions" }));
      expect(await screen.findByRole("menuitem", { name: "Copy link" })).toBeInTheDocument();
      expect(screen.queryByRole("menuitem", { name: "Edit all fields" })).not.toBeInTheDocument();
      expect(screen.queryByRole("menuitem", { name: "Delete record" })).not.toBeInTheDocument();
    },
  );
});
