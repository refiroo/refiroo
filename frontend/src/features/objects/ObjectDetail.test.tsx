import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { ObjectDetail } from "@/features/objects/ObjectDetail";

afterEach(() => vi.restoreAllMocks());

describe("ObjectDetail lifecycle controls", () => {
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
      />,
    );
    expect(await screen.findByText("Record temporarily unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: object.name })).toBeInTheDocument();
    expect(read).toHaveBeenNthCalledWith(1, object.objectTypeKey, object.id, "west");
    expect(read).toHaveBeenNthCalledWith(2, object.objectTypeKey, object.id, "west");
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
      expect(await screen.findByRole("button", { name: "Edit object" })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Edit object" }));
      expect(screen.getByLabelText("Name")).toHaveValue(object.name);
      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
      rerender(<ObjectDetail {...props} readOnly />);
      expect(screen.queryByRole("button", { name: "Edit object" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Delete object" })).not.toBeInTheDocument();
    },
  );
});
