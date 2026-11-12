import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { domainObject, testModel } from "@/test/fixtures";
import { ObjectDeleteDialog } from "@/features/objects/ObjectDeleteDialog";

afterEach(() => vi.restoreAllMocks());
const impact = {
  objectsToDelete: [{ id: "child", name: "Owned child", objectTypeKey: "codelist", reason: "child" }],
  relationshipsToRemove: [],
  objectCount: 2,
  relationshipCount: 4,
  ownRelationshipCount: 3,
  retainedAssociationCount: 1,
  requiresCascade: true,
  deletionPreviewToken: "signed-first",
};
const alone = {
  objectsToDelete: [],
  relationshipsToRemove: [],
  objectCount: 1,
  relationshipCount: 0,
  ownRelationshipCount: 0,
  retainedAssociationCount: 0,
  requiresCascade: false,
  deletionPreviewToken: "signed-alone",
};

function open(onClose = vi.fn(), onDeleted = vi.fn()) {
  render(<ObjectDeleteDialog model={testModel} object={domainObject} onClose={onClose} onDeleted={onDeleted} />);
  return { onClose, onDeleted };
}

it("shows nothing to delete with until the impact is read, then one confirmation that names what is lost", async () => {
  let read: (value: typeof impact) => void = () => {};
  vi.spyOn(api, "objectDeletionImpact").mockReturnValue(new Promise((resolve) => (read = resolve)));
  const remove = vi.spyOn(api, "deleteObject").mockResolvedValue();
  const { onClose, onDeleted } = open();
  expect(screen.getByText("Delete Connections?")).toBeInTheDocument();
  expect(screen.getByText(/Checking what deleting it would take/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /^(Delete|Retry|Working)/ })).not.toBeInTheDocument();
  read(impact);
  expect(await screen.findByText(/Deletes Connections and its 3 relationships\./)).toBeInTheDocument();
  expect(
    screen.getByText(/1 record under it is deleted too\. 1 relationship of those records is removed too\./),
  ).toBeInTheDocument();
  expect(screen.getByText(/Owned child/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Delete 2 records" })).toBeInTheDocument();
  expect(remove).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(onClose).toHaveBeenCalledOnce();
  expect(remove).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Delete 2 records" }));
  await waitFor(() => expect(onDeleted).toHaveBeenCalledOnce());
  expect(remove).toHaveBeenCalledExactlyOnceWith("domain", domainObject.id, 1, {
    cascade: true,
    deletionPreviewToken: "signed-first",
  });
});

it("says nothing else is deleted for a record that takes nothing with it", async () => {
  vi.spyOn(api, "objectDeletionImpact").mockResolvedValue(alone);
  const remove = vi.spyOn(api, "deleteObject").mockResolvedValue();
  const { onDeleted } = open();
  expect(await screen.findByText("Deletes Connections. Nothing else is deleted.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Delete Domain" }));
  await waitFor(() => expect(onDeleted).toHaveBeenCalledOnce());
  expect(remove).toHaveBeenCalledWith("domain", domainObject.id, 1, {
    cascade: true,
    deletionPreviewToken: "signed-alone",
  });
});

it("shows the fresh impact once when it changed after it was shown, and asks again", async () => {
  vi.spyOn(api, "objectDeletionImpact")
    .mockResolvedValueOnce(impact)
    .mockResolvedValueOnce({ ...impact, deletionPreviewToken: "signed-second" });
  const remove = vi
    .spyOn(api, "deleteObject")
    .mockRejectedValueOnce(new ApiError(409, "DELETION_PREVIEW_CHANGED", "Please retry."))
    .mockResolvedValueOnce();
  vi.spyOn(api, "object").mockResolvedValue({ ...domainObject, version: 2 });
  const { onDeleted } = open();
  fireEvent.click(await screen.findByRole("button", { name: "Delete 2 records" }));
  expect(await screen.findByText(/The record changed after this was shown/)).toBeInTheDocument();
  expect(onDeleted).not.toHaveBeenCalled();
  expect(remove).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Delete 2 records" }));
  await waitFor(() => expect(onDeleted).toHaveBeenCalledOnce());
  expect(remove).toHaveBeenLastCalledWith("domain", domainObject.id, 2, {
    cascade: true,
    deletionPreviewToken: "signed-second",
  });
});

it("says the impact could not be read, offers Retry and deletes nothing without having shown it", async () => {
  const read = vi
    .spyOn(api, "objectDeletionImpact")
    .mockRejectedValueOnce(new ApiError(500, "INTERNAL_ERROR", "The service is unavailable."))
    .mockResolvedValueOnce(alone);
  const remove = vi.spyOn(api, "deleteObject").mockResolvedValue();
  open();
  expect(await screen.findByText(/could not be read, so nothing was deleted/)).toBeInTheDocument();
  expect(screen.getByText("The service is unavailable.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /^Delete/ })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("button", { name: "Delete Domain" })).toBeInTheDocument();
  expect(read).toHaveBeenCalledTimes(2);
  expect(remove).not.toHaveBeenCalled();
});
