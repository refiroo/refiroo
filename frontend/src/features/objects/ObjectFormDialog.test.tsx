import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { allowNavigation } from "@/routing/navigationGuard";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { domainObject, testModel } from "@/test/fixtures";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";

vi.mock("@/api/client", () => ({
  api: { createObject: vi.fn(), updateObject: vi.fn(), objects: vi.fn(), object: vi.fn() },
}));

describe("ObjectFormDialog", () => {
  afterEach(() => vi.restoreAllMocks());
  beforeEach(() => {
    vi.mocked(api.createObject).mockResolvedValue(domainObject);
    vi.mocked(api.updateObject).mockResolvedValue({ ...domainObject, name: "Updated", version: 2 });
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
    vi.mocked(api.object).mockResolvedValue({ ...domainObject, version: 2 });
  });

  it("preserves edits on refused navigation and failed save, then permits navigation from successful save", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const onClose = vi.fn();
    const onSaved = vi.fn(() => expect(allowNavigation()).toBe(true));
    vi.mocked(api.updateObject).mockRejectedValueOnce(new Error("Temporarily unavailable"));
    render(
      <ObjectFormDialog
        model={testModel}
        applicationKey="test-app"
        workspaceKey="default"
        objectType={testModel.objectTypes[0]}
        object={domainObject}
        onClose={onClose}
        onSaved={onSaved}
      />,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Retained" } });
    expect(allowNavigation()).toBe(false);
    expect(screen.getByLabelText("Name")).toHaveValue("Retained");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("Temporarily unavailable");
    expect(allowNavigation()).toBe(false);
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Name")).toHaveValue("Retained");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(confirm).toHaveBeenCalledTimes(2);
  });

  it("closes on Escape and keeps focus on the field the form opened with", () => {
    const onClose = vi.fn();
    render(
      <ObjectFormDialog
        model={testModel}
        applicationKey="test-app"
        workspaceKey="west"
        objectType={testModel.objectTypes[0]}
        onClose={onClose}
        onSaved={vi.fn()}
      />,
    );

    // The dialog autofocuses Name, so the shared modal must not pull focus to itself.
    expect(document.activeElement).toBe(screen.getByLabelText("Name"));

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("creates an object with typed model attributes", async () => {
    render(
      <ObjectFormDialog
        model={testModel}
        applicationKey="test-app"
        workspaceKey="west"
        objectType={testModel.objectTypes[0]}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Connections" } });
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "CONNECTIONS" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Domain" }));
    await waitFor(() =>
      expect(api.createObject).toHaveBeenCalledWith(
        "domain",
        expect.objectContaining({
          applicationKey: "test-app",
          workspaceKey: "west",
          name: "Connections",
          attributes: [
            { attributeTypeKey: "code", value: "CONNECTIONS" },
            { attributeTypeKey: "active", value: true },
          ],
        }),
      ),
    );
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
    render(
      <ObjectFormDialog
        model={model}
        applicationKey="test-app"
        objectType={objectType}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Connections" } });
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "CONNECTIONS" } });
    fireEvent.click(screen.getByRole("button", { name: "Add Domain" }));

    await waitFor(() =>
      expect(api.createObject).toHaveBeenCalledWith(
        "domain",
        expect.objectContaining({
          attributes: expect.arrayContaining([{ attributeTypeKey: "enabled", value: false }]),
        }),
      ),
    );
  });

  it("edits only changed core fields with the current version", async () => {
    render(
      <ObjectFormDialog
        model={testModel}
        applicationKey="test-app"
        objectType={testModel.objectTypes[0]}
        object={domainObject}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Updated" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.updateObject).toHaveBeenCalledWith("domain", domainObject.id, {
        expectedVersion: 1,
        name: "Updated",
      }),
    );
  });

  it("refreshes a conflicting version without discarding entered values", async () => {
    vi.mocked(api.updateObject)
      .mockRejectedValueOnce(new ApiError(409, "VERSION_CONFLICT", "Stale version"))
      .mockResolvedValueOnce({ ...domainObject, name: "Kept edit", version: 3 });
    vi.mocked(api.object).mockResolvedValueOnce({ ...domainObject, name: "Someone else", version: 2 });
    render(
      <ObjectFormDialog
        model={testModel}
        applicationKey="test-app"
        objectType={testModel.objectTypes[0]}
        object={domainObject}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    const name = screen.getByLabelText("Name");
    fireEvent.change(name, { target: { value: "Kept edit" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/your edits are preserved/i)).toBeInTheDocument();
    expect(name).toHaveValue("Kept edit");
    fireEvent.change(name, { target: { value: domainObject.name } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.updateObject).toHaveBeenLastCalledWith(
        "domain",
        domainObject.id,
        expect.objectContaining({ expectedVersion: 2, name: domainObject.name }),
      ),
    );
  });

  it("confirms before dismissing a dirty complete-object form", () => {
    const onClose = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    render(
      <ObjectFormDialog
        model={testModel}
        applicationKey="test-app"
        objectType={testModel.objectTypes[0]}
        object={domainObject}
        onClose={onClose}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Unsaved" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(confirm).toHaveBeenCalledTimes(2);
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
        {
          key: "object-has-translation",
          reverseKey: "translation-translates-object",
          name: "Has translation",
          reverseName: "Translates object",
          isOriented: true,
          features: {},
        },
      ],
      objectTypeRelations: [
        ...testModel.objectTypeRelations,
        {
          relationTypeKey: "object-has-translation",
          fromObjectTypeKey: "domain",
          toObjectTypeKey: "translation",
          cardinality: "one-to-many" as const,
          required: true,
        },
      ],
    };

    render(
      <ObjectFormDialog
        model={model}
        applicationKey="test-app"
        objectType={translationType}
        parentObjectId="group-id"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Czech connections" } });
    fireEvent.change(screen.getByLabelText("Code"), { target: { value: "CS_CONNECTIONS" } });
    await waitFor(() => expect(api.objects).toHaveBeenCalled());
    fireEvent.click(await screen.findByRole("option", { name: /Connections/ }));
    fireEvent.click(screen.getByRole("button", { name: "Add Translation" }));

    await waitFor(() =>
      expect(api.createObject).toHaveBeenCalledWith(
        "translation",
        expect.objectContaining({
          parentObjectId: "group-id",
          initialRelations: [
            {
              relationTypeKey: "object-has-translation",
              direction: "incoming",
              otherObjectId: domainObject.id,
              attributes: {},
            },
          ],
        }),
      ),
    );
  });
  it("saves zero and false with core changes while showing current content on a conflict", async () => {
    const count = { key: "count", name: "Count", valueType: "integer" as const, features: {}, validation: {}, ui: {} };
    const type = {
      ...testModel.objectTypes[0],
      attributes: [
        ...testModel.objectTypes[0].attributes,
        { attributeTypeKey: "count", required: false, readOnly: false, order: 30, ui: {} },
      ],
    };
    const model = {
      ...testModel,
      attributeTypes: [...testModel.attributeTypes, count],
      objectTypes: [type, ...testModel.objectTypes.slice(1)],
    };
    vi.mocked(api.updateObject).mockRejectedValueOnce(new ApiError(409, "VERSION_CONFLICT", "Stale"));
    vi.mocked(api.object).mockResolvedValueOnce({
      ...domainObject,
      name: "Other steward",
      version: 2,
      attributes: [
        ...domainObject.attributes,
        { id: "count", attributeTypeKey: "count", name: "Count", valueType: "integer", value: 7 },
      ],
    });
    render(
      <ObjectFormDialog
        model={model}
        applicationKey="test-app"
        objectType={type}
        object={domainObject}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("Count"), { target: { value: "0" } });
    fireEvent.click(screen.getByLabelText("Active"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Other steward")).toBeInTheDocument();
    expect(screen.getByLabelText("Count")).toHaveValue(0);
    expect(screen.getByLabelText("Active")).not.toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.updateObject).toHaveBeenLastCalledWith("domain", domainObject.id, {
        expectedVersion: 2,
        attributes: [
          { attributeTypeKey: "active", value: false },
          { attributeTypeKey: "count", value: 0 },
        ],
      }),
    );
  });

  describe("plain add (0.17 PL2)", () => {
    const codelist = testModel.objectTypes[1];
    beforeEach(() => vi.mocked(api.createObject).mockClear());
    function open(props: Partial<Parameters<typeof ObjectFormDialog>[0]> = {}) {
      const onSaved = vi.fn();
      render(
        <ObjectFormDialog
          model={testModel}
          applicationKey="test-app"
          workspaceKey="west"
          objectType={codelist}
          onClose={vi.fn()}
          onSaved={onSaved}
          {...props}
        />,
      );
      return { onSaved };
    }

    it("names the collection above the title, and adds with the type's name", () => {
      open({ collectionName: "Codelists of Connections" });
      const dialog = screen.getByRole("dialog", { name: "New Codelist" });
      expect(dialog).toHaveTextContent("Codelists of Connections");
      expect(dialog).not.toHaveTextContent("Create in context");
      expect(within(dialog).getByRole("button", { name: "Add Codelist" })).toHaveClass("primary");
    });

    it("says a known parent instead of asking, and asks again behind Change", async () => {
      const { onSaved } = open({
        parentObjectId: domainObject.id,
        parentObjectTypeKey: "domain",
        parentName: "Connections",
      });
      expect(screen.getByText("In")).toBeVisible();
      expect(screen.getByText("Connections")).toBeVisible();
      expect(screen.queryByRole("combobox", { name: "Search: Parent" })).not.toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Statuses" } });
      fireEvent.change(screen.getByLabelText("Code"), { target: { value: "STATUS" } });
      fireEvent.click(screen.getByRole("button", { name: "Add Codelist" }));
      await waitFor(() => expect(onSaved).toHaveBeenCalled());
      expect(api.createObject).toHaveBeenCalledWith(
        "codelist",
        expect.objectContaining({ parentObjectId: domainObject.id }),
      );
    });

    it("shows the parent picker on Change, and where no parent is known", () => {
      const { unmount } = render(
        <ObjectFormDialog
          model={testModel}
          applicationKey="test-app"
          objectType={codelist}
          parentObjectId={domainObject.id}
          parentName="Connections"
          onClose={vi.fn()}
          onSaved={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: "Change" }));
      expect(screen.getByRole("combobox", { name: "Search: Parent" })).toBeVisible();
      expect(screen.queryByText("In")).not.toBeInTheDocument();
      unmount();
      open();
      expect(screen.getByRole("combobox", { name: "Search: Parent" })).toBeVisible();
      expect(screen.queryByRole("button", { name: "Change" })).not.toBeInTheDocument();
    });

    it("puts required fields first and marked, and the optional ones under More fields (n)", () => {
      open({ parentObjectId: domainObject.id, parentName: "Connections" });
      const labels = Array.from(document.querySelectorAll("form label")).map((label) => label.textContent);
      expect(labels[0]).toMatch(/^Name\*/);
      expect(labels[1]).toMatch(/^Code\*/);
      expect(labels[2]).toMatch(/^Active\(optional\)/);
      const more = screen.getByRole("button", { name: "More fields (1)" });
      expect(more).toHaveAttribute("aria-expanded", "false");
      expect(screen.getByLabelText("Active")).not.toBeVisible();
      fireEvent.click(more);
      expect(more).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByLabelText("Active")).toBeVisible();
    });

    it("remembers More fields for the type in this browser, and works where storage is blocked", () => {
      const stored = new Map<string, string>();
      vi.stubGlobal("localStorage", {
        getItem: (key: string) => stored.get(key) ?? null,
        setItem: (key: string, value: string) => stored.set(key, value),
        removeItem: (key: string) => stored.delete(key),
      });
      const { unmount } = render(
        <ObjectFormDialog
          model={testModel}
          applicationKey="test-app"
          objectType={codelist}
          onClose={vi.fn()}
          onSaved={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: "More fields (1)" }));
      expect(stored.get("rdm.moreFields.codelist")).toBe("true");
      unmount();
      open();
      expect(screen.getByRole("button", { name: "More fields (1)" })).toHaveAttribute("aria-expanded", "true");
      vi.unstubAllGlobals();
    });

    it("keeps working where browser storage is blocked", () => {
      vi.stubGlobal("localStorage", {
        getItem: () => {
          throw new Error("blocked");
        },
        setItem: () => {
          throw new Error("blocked");
        },
      });
      open();
      fireEvent.click(screen.getByRole("button", { name: "More fields (1)" }));
      expect(screen.getByRole("button", { name: "More fields (1)" })).toHaveAttribute("aria-expanded", "true");
      vi.unstubAllGlobals();
    });

    it("says a missing required value under its field, in words, and adds nothing", async () => {
      open({ parentObjectId: domainObject.id, parentName: "Connections" });
      const form = screen.getByRole("dialog").querySelector("form")!;
      expect(form).toHaveAttribute("novalidate");
      fireEvent.click(screen.getByRole("button", { name: "Add Codelist" }));
      expect(await screen.findByText("Enter a name.")).toBeVisible();
      expect(screen.getByText("Code is required.")).toBeVisible();
      expect(screen.getByLabelText("Name")).toHaveAttribute("aria-invalid", "true");
      expect(api.createObject).not.toHaveBeenCalled();
      fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Statuses" } });
      expect(screen.queryByText("Enter a name.")).not.toBeInTheDocument();
    });

    it("says a wrong type of value in words and opens More fields to show it", async () => {
      const count = {
        key: "count",
        name: "Count",
        valueType: "integer" as const,
        features: {},
        validation: {},
        ui: {},
      };
      const type = {
        ...codelist,
        attributes: [
          ...codelist.attributes,
          { attributeTypeKey: "count", required: false, readOnly: false, order: 30, ui: {} },
        ],
      };
      const model = {
        ...testModel,
        attributeTypes: [...testModel.attributeTypes, count],
        objectTypes: [testModel.objectTypes[0], type],
      };
      render(
        <ObjectFormDialog
          model={model}
          applicationKey="test-app"
          objectType={type}
          parentObjectId={domainObject.id}
          parentName="Connections"
          onClose={vi.fn()}
          onSaved={vi.fn()}
        />,
      );
      fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Statuses" } });
      fireEvent.change(screen.getByLabelText("Code"), { target: { value: "STATUS" } });
      fireEvent.change(screen.getByLabelText("Count"), { target: { value: "1.5" } });
      fireEvent.click(screen.getByRole("button", { name: "Add Codelist" }));
      expect(await screen.findByText("Enter a whole number.")).toBeVisible();
      expect(screen.getByRole("button", { name: "More fields (2)" })).toHaveAttribute("aria-expanded", "true");
      expect(api.createObject).not.toHaveBeenCalled();
    });
  });
});
