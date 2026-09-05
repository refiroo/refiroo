import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { domainObject, testModel } from "../test/fixtures";
import { ObjectFormDialog } from "./ObjectFormDialog";

vi.mock("../api/client", () => ({ api: { createObject: vi.fn(), updateObject: vi.fn(), objects: vi.fn(), object: vi.fn() } }));

describe("ObjectFormDialog", () => {
  beforeEach(() => {
    vi.mocked(api.createObject).mockResolvedValue(domainObject);
    vi.mocked(api.updateObject).mockResolvedValue({ ...domainObject, name: "Updated", state: "draft", version: 2 });
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
    vi.mocked(api.object).mockResolvedValue({ ...domainObject, version: 2 });
  });

  it("creates an object with typed model attributes", async () => {
    render(<ObjectFormDialog model={testModel} applicationKey="test-app" workspaceKey="west" objectType={testModel.objectTypes[0]} onClose={vi.fn()} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Connections" } });
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "CONNECTIONS" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(api.createObject).toHaveBeenCalledWith("domain", expect.objectContaining({ applicationKey: "test-app", workspaceKey: "west", name: "Connections", attributes: [{ attributeTypeKey: "code", value: "CONNECTIONS" }, { attributeTypeKey: "active", value: true }] })));
  });

  it("preserves false for an optional boolean without a default", async () => {
    const enabled = {
      key: "enabled",
      name: "Enabled",
      valueType: "boolean" as const,
      features: {},
      validation: {},
      ui: {},
    };
    const objectType = {
      ...testModel.objectTypes[0],
      attributes: [
        ...testModel.objectTypes[0].attributes,
        { attributeTypeKey: "enabled", required: false, readOnly: false, order: 30, ui: {} },
      ],
    };
    const model = {
      ...testModel,
      attributeTypes: [...testModel.attributeTypes, enabled],
      objectTypes: [objectType, ...testModel.objectTypes.slice(1)],
    };
    render(<ObjectFormDialog model={model} applicationKey="test-app" objectType={objectType} onClose={vi.fn()} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Connections" } });
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "CONNECTIONS" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(api.createObject).toHaveBeenCalledWith(
      "domain",
      expect.objectContaining({
        attributes: expect.arrayContaining([{ attributeTypeKey: "enabled", value: false }]),
      }),
    ));
  });

  it("edits only changed core fields with the current version", async () => {
    render(<ObjectFormDialog model={testModel} applicationKey="test-app" objectType={testModel.objectTypes[0]} object={domainObject} onClose={vi.fn()} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Updated" } });
    fireEvent.change(screen.getByLabelText("State"), { target: { value: "draft" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(api.updateObject).toHaveBeenCalledWith("domain", domainObject.id, { expectedVersion: 1, name: "Updated", state: "draft" }));
  });

  it("refreshes a conflicting version without discarding entered values", async () => {
    vi.mocked(api.updateObject).mockRejectedValueOnce(Object.assign(new Error("Stale version"), { code: "version_conflict" })).mockResolvedValueOnce({ ...domainObject, name: "Kept edit", version: 3 });
    render(<ObjectFormDialog model={testModel} applicationKey="test-app" objectType={testModel.objectTypes[0]} object={domainObject} onClose={vi.fn()} onSaved={vi.fn()} />);
    const name = screen.getByLabelText("Name");
    fireEvent.change(name, { target: { value: "Kept edit" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(/your edits are preserved/i)).toBeInTheDocument();
    expect(name).toHaveValue("Kept edit");
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(api.updateObject).toHaveBeenLastCalledWith("domain", domainObject.id, expect.objectContaining({ expectedVersion: 2, name: "Kept edit" })));
  });

  it("creates a required target relationship atomically with a new object", async () => {
    const translationType = {
      ...testModel.objectTypes[0],
      key: "translation",
      name: "Translation",
      pluralName: "Translations",
      features: { rootCreatable: false },
      behavior: {},
    };
    const model = {
      ...testModel,
      objectTypes: [...testModel.objectTypes, translationType],
      relationTypes: [
        ...testModel.relationTypes,
        { key: "object-has-translation", reverseKey: "translation-translates-object", name: "Has translation", reverseName: "Translates object", isOriented: true, features: {} },
      ],
      objectTypeRelations: [
        ...testModel.objectTypeRelations,
        { relationTypeKey: "object-has-translation", fromObjectTypeKey: "domain", toObjectTypeKey: "translation", cardinality: "one-to-many" as const, required: true },
      ],
    };

    render(<ObjectFormDialog model={model} applicationKey="test-app" objectType={translationType} parentObjectId="group-id" onClose={vi.fn()} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Czech connections" } });
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "CS_CONNECTIONS" } });
    await waitFor(() => expect(api.objects).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText("Select object"), { target: { value: domainObject.id } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(api.createObject).toHaveBeenCalledWith("translation", expect.objectContaining({
      parentObjectId: "group-id",
      initialRelations: [{ relationTypeKey: "object-has-translation", direction: "incoming", otherObjectId: domainObject.id, attributes: {} }],
    })));
  });
});
