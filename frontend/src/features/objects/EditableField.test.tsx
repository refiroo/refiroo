import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { EditableField } from "@/features/objects/EditableField";
import type { ObjectItem } from "@/types";

afterEach(() => vi.restoreAllMocks());

/** One field of one record, edited in place as a parent holding the record would (UA8, U-D18). */
function Held({
  start,
  field,
  layout = "title",
  readOnly = false,
  onConflict = async () => undefined,
}: {
  start: ObjectItem;
  field: string;
  layout?: "row" | "title" | "subtitle";
  readOnly?: boolean;
  onConflict?: () => Promise<void>;
}) {
  const [object, setObject] = useState(start);
  const [editing, setEditing] = useState(false);
  return (
    <EditableField
      model={testModel}
      object={object}
      field={field}
      layout={layout}
      readOnly={readOnly}
      editing={editing}
      onEdit={() => setEditing(true)}
      onClose={() => setEditing(false)}
      onSaved={(saved) => {
        setObject(saved);
        setEditing(false);
      }}
      onConflict={onConflict}
    />
  );
}

describe.each([domainObject, codelistObject])("a field edited in place (UA8), $objectTypeKey", (record) => {
  it("saves the name through the record update with its version, and shows the new name", async () => {
    const update = vi.spyOn(api, "updateObject").mockResolvedValue({ ...record, name: "Renamed", version: 2 });
    render(<Held start={record} field="name" />);
    fireEvent.click(screen.getByRole("button", { name: `Edit Name: ${record.name}` }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Renamed" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(update).toHaveBeenCalledWith(record.objectTypeKey, record.id, {
        name: "Renamed",
        expectedVersion: record.version,
      }),
    );
    expect(await screen.findByRole("button", { name: "Edit Name: Renamed" })).toBeInTheDocument();
  });

  it("saves an attribute through its own route", async () => {
    const update = vi.spyOn(api, "updateAttribute").mockResolvedValue({ ...record, version: 2 });
    render(<Held start={record} field="code" layout="subtitle" />);
    fireEvent.click(screen.getByRole("button", { name: /^Edit Code:/ }));
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "NEW" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(update).toHaveBeenCalledWith(record.objectTypeKey, record.id, "code", "NEW", record.version),
    );
  });

  it("cancels with Escape and returns focus to the value", async () => {
    render(<Held start={record} field="name" />);
    fireEvent.click(screen.getByRole("button", { name: `Edit Name: ${record.name}` }));
    fireEvent.keyDown(screen.getByLabelText("Name"), { key: "Escape" });
    await waitFor(() => expect(screen.getByRole("button", { name: `Edit Name: ${record.name}` })).toHaveFocus());
  });

  it("reloads on a conflict and says so", async () => {
    vi.spyOn(api, "updateObject").mockRejectedValue(
      new ApiError(409, "VERSION_CONFLICT", "The record changed", undefined),
    );
    const onConflict = vi.fn().mockResolvedValue(undefined);
    render(<Held start={record} field="name" onConflict={onConflict} />);
    fireEvent.click(screen.getByRole("button", { name: `Edit Name: ${record.name}` }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/Your input is preserved/)).toBeInTheDocument();
    expect(onConflict).toHaveBeenCalled();
  });

  it("shows a field it cannot edit as plain text: a built-in field, and any field when read-only", () => {
    const { unmount } = render(<Held start={record} field="id" layout="subtitle" />);
    expect(screen.getByText(record.id)).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
    unmount();
    render(<Held start={record} field="name" readOnly />);
    expect(screen.getByText(record.name)).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("offers Add where an editable header field is empty", () => {
    render(<Held start={{ ...record, attributes: [] }} field="code" layout="subtitle" />);
    expect(screen.getByRole("button", { name: /^Add Code/ })).toBeInTheDocument();
  });
});
