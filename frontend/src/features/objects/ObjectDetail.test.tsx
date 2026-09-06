import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { RetirementImpact } from "@/types";
import { ObjectDetail } from "@/features/objects/ObjectDetail";

afterEach(() => vi.restoreAllMocks());

describe("ObjectDetail retirement", () => {
  it("previews dependencies before sending a confirmed cascade", async () => {
    const impact: RetirementImpact = {
      rootObjectId: domainObject.id,
      objectsToRetire: [
        {
          id: codelistObject.id,
          name: codelistObject.name,
          objectTypeKey: codelistObject.objectTypeKey,
          reason: "containment",
        },
      ],
      objectCount: 2,
      retainedAssociationCount: 1,
    };
    vi.spyOn(api, "object").mockResolvedValue(domainObject);
    vi.spyOn(api, "objectHistory").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "retireObject")
      .mockRejectedValueOnce(new ApiError(409, "object_has_dependants", "Confirmation required", impact))
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

    fireEvent.click(await screen.findByRole("button", { name: "Retire object" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Retire object" }).at(-1)!);
    expect(await screen.findByText("Nothing has been retired yet.")).toBeInTheDocument();
    expect(screen.getByText("Timetable types")).toBeInTheDocument();
    expect(screen.getByText("1 independent association is retained as history.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Confirm retirement" }));
    await waitFor(() =>
      expect(api.retireObject).toHaveBeenLastCalledWith("domain", domainObject.id, domainObject.activeRevisionId, true),
    );
    expect(onDeleted).toHaveBeenCalledOnce();
  });
});
