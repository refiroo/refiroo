import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { DeleteImpact } from "@/types";
import { ObjectDetail } from "@/features/objects/ObjectDetail";

afterEach(() => vi.restoreAllMocks());

describe("ObjectDetail deletion", () => {
  it("previews dependencies before sending a confirmed cascade", async () => {
    const externalObject = {
      id: "77777777-7777-4777-8777-777777777777",
      name: "External value",
      objectTypeKey: "codelist",
      applicationKey: "other-app",
      parentObjectId: null,
    };
    const impact: DeleteImpact = {
      rootObject: { ...domainObject, parentObjectId: null },
      objectsToDelete: [{ ...codelistObject, reason: "child", viaObjectId: domainObject.id }],
      relationshipsToRemove: [
        {
          id: "relationship",
          relationTypeKey: "links",
          fromObject: { ...domainObject, parentObjectId: null },
          toObject: externalObject,
          fkPk: false,
          relatedObjectWillBeDeleted: false,
        },
      ],
      objectCount: 2,
      relationshipCount: 2,
    };
    vi.spyOn(api, "object").mockResolvedValue(domainObject);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "deleteObject")
      .mockRejectedValueOnce(new ApiError(409, "object_has_dependents", "Confirmation required", impact))
      .mockResolvedValueOnce(undefined);
    const onDeleted = vi.fn();
    render(
      <ObjectDetail
        model={testModel}
        application={testModel.applications[0]}
        objectTypeKey="domain"
        objectId={domainObject.id}
        workspaceKey="default"
        onOpen={vi.fn()}
        onBack={vi.fn()}
        onDeleted={onDeleted}
        onChanged={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Delete object" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Delete object" }).at(-1)!);
    expect(await screen.findByText("Nothing has been deleted yet.")).toBeInTheDocument();
    expect(screen.getByText("Timetable types")).toBeInTheDocument();
    expect(screen.getByText("The object at the other endpoint is preserved")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cascade delete" }));
    await waitFor(() => expect(api.deleteObject).toHaveBeenLastCalledWith("domain", domainObject.id, 1, true));
    expect(onDeleted).toHaveBeenCalledOnce();
  });
});
