import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { domainObject, testModel } from "@/test/fixtures";
import { ObjectDeleteDialog } from "@/features/objects/ObjectDeleteDialog";

afterEach(() => vi.restoreAllMocks());
const impact = {
  objectsToDelete: [{ id: "child", name: "Owned child", objectTypeKey: "codelist" }],
  relationshipsToRemove: [],
  objectCount: 2,
  relationshipCount: 1,
  retainedAssociationCount: 1,
  deletionPreviewToken: "signed-first",
};

it("keeps cancellation side-effect free and sends only the displayed signed preview", async () => {
  const remove = vi
    .spyOn(api, "deleteObject")
    .mockRejectedValueOnce(new ApiError(409, "object_has_dependants", "Impact", impact))
    .mockResolvedValueOnce();
  const close = vi.fn();
  const done = vi.fn();
  render(<ObjectDeleteDialog model={testModel} object={domainObject} onClose={close} onDeleted={done} />);
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Cancel" }));
  expect(remove).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Delete" }));
  expect(await screen.findByText(/Owned child/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(close).toHaveBeenCalledOnce();
  expect(remove).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Confirm deletion" }));
  await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(remove).toHaveBeenLastCalledWith("domain", domainObject.id, 1, {
    cascade: true,
    deletionPreviewToken: "signed-first",
  });
});

it("refuses a stale preview and requires a fresh displayed impact before confirmation", async () => {
  const remove = vi
    .spyOn(api, "deleteObject")
    .mockRejectedValueOnce(new ApiError(409, "object_has_dependants", "Impact", impact))
    .mockRejectedValueOnce(new ApiError(409, "deletion_preview_changed", "Please retry."))
    .mockRejectedValueOnce(
      new ApiError(409, "object_has_dependants", "Impact", { ...impact, deletionPreviewToken: "signed-second" }),
    )
    .mockResolvedValueOnce();
  vi.spyOn(api, "object").mockResolvedValue({ ...domainObject, version: 2 });
  const done = vi.fn();
  render(<ObjectDeleteDialog model={testModel} object={domainObject} onClose={vi.fn()} onDeleted={done} />);
  fireEvent.click(screen.getByRole("button", { name: "Delete" }));
  fireEvent.click(await screen.findByRole("button", { name: "Confirm deletion" }));
  expect(await screen.findByText("Please retry.")).toBeInTheDocument();
  expect(done).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
  fireEvent.click(await screen.findByRole("button", { name: "Confirm deletion" }));
  await waitFor(() => expect(done).toHaveBeenCalledOnce());
  expect(remove).toHaveBeenLastCalledWith("domain", domainObject.id, 2, {
    cascade: true,
    deletionPreviewToken: "signed-second",
  });
});
