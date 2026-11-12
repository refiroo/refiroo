import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { AttributesPanelDefinition } from "@/types";
import { AttributesPanel } from "@/features/objects/panels/AttributesPanel";
import { ToastProvider } from "@/ui/Toast";
import { EDIT_HINT_STORAGE_KEY } from "@/lib/editHint";

const panel: AttributesPanelDefinition = {
  key: "attributes",
  title: "Attributes",
  type: "attributes",
  region: "main",
  order: 1,
  visible: true,
  config: { fields: ["code", "active"] },
};

describe("AttributesPanel", () => {
  it.each([
    ["domain", domainObject, "Yes"],
    ["codelist", codelistObject, "No"],
  ])("uses the same stored-value actions for %s", (_name, object, booleanLabel) => {
    render(
      <AttributesPanel model={testModel} object={object} panel={panel} onObjectChanged={vi.fn()} onReload={vi.fn()} />,
    );
    expect(screen.getByText(booleanLabel)).toBeInTheDocument();
    // The text field is edited by its value; the yes/no field is a checkbox that saves on change.
    expect(screen.getAllByRole("button", { name: /^Edit / })).toHaveLength(1);
    expect(screen.getByRole("checkbox", { name: `Active of ${object.name}` })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Add / })).not.toBeInTheDocument();
  });

  // UA4 revision: the value is the edit control; a plus on an empty field adds; an icon removes.
  it.each([
    ["domain", domainObject, "CONNECTIONS"],
    ["codelist", codelistObject, "MOT"],
  ])("edits a %s field by its value and returns focus to it", (_name, object, code) => {
    render(
      <AttributesPanel model={testModel} object={object} panel={panel} onObjectChanged={vi.fn()} onReload={vi.fn()} />,
    );
    const value = screen.getByRole("button", { name: `Edit Code: ${code}` });
    fireEvent.click(value);
    const editor = screen.getByRole("form", { name: "Edit Code" });
    fireEvent.keyDown(editor, { key: "Escape" });
    expect(screen.queryByRole("form", { name: "Edit Code" })).not.toBeInTheDocument();
    return new Promise<void>((done) =>
      requestAnimationFrame(() => {
        expect(screen.getByRole("button", { name: `Edit Code: ${code}` })).toHaveFocus();
        done();
      }),
    );
  });

  it("adds a value to an empty field by clicking it", () => {
    const object = {
      ...domainObject,
      attributes: domainObject.attributes.filter((item) => item.attributeTypeKey !== "code"),
    };
    render(
      <AttributesPanel model={testModel} object={object} panel={panel} onObjectChanged={vi.fn()} onReload={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Add Code: Not set" }));
    expect(screen.getByRole("form", { name: "Edit Code" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove Code" })).not.toBeInTheDocument();
  });

  it("shows a yes/no field as a checkbox that saves on change, against the record's version", async () => {
    const update = vi.spyOn(api, "updateAttribute").mockResolvedValue({ ...domainObject, version: 2 });
    const onObjectChanged = vi.fn();
    render(
      <AttributesPanel
        model={testModel}
        object={domainObject}
        panel={panel}
        onObjectChanged={onObjectChanged}
        onReload={vi.fn()}
      />,
    );
    const flag = screen.getByRole("checkbox", { name: "Active of Connections" });
    expect(flag).toBeChecked();
    fireEvent.click(flag);
    await waitFor(() =>
      expect(update).toHaveBeenCalledWith(domainObject.objectTypeKey, domainObject.id, "active", false, 1),
    );
    await waitFor(() => expect(onObjectChanged).toHaveBeenCalled());
    update.mockRestore();
  });

  it("removes only an optional field, at once, and offers Undo", async () => {
    const remove = vi.spyOn(api, "deleteAttribute").mockResolvedValue();
    const reload = vi.fn().mockResolvedValue(undefined);
    vi.spyOn(api, "object").mockResolvedValue({ ...domainObject, version: 2 });
    const create = vi.spyOn(api, "createAttribute").mockResolvedValue(domainObject);
    render(
      <ToastProvider>
        <AttributesPanel
          model={testModel}
          object={domainObject}
          panel={panel}
          onObjectChanged={vi.fn()}
          onReload={reload}
        />
      </ToastProvider>,
    );
    expect(screen.queryByRole("button", { name: "Remove Code" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove Active" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    await waitFor(() => expect(remove).toHaveBeenCalledWith("domain", domainObject.id, "active", domainObject.version));
    await waitFor(() => expect(reload).toHaveBeenCalled());
    expect(await screen.findByText("Active removed")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith("domain", domainObject.id, "active", true, 2));
  });

  it("leaves a click that selected the value's text for copying", () => {
    render(
      <AttributesPanel
        model={testModel}
        object={domainObject}
        panel={panel}
        onObjectChanged={vi.fn()}
        onReload={vi.fn()}
      />,
    );
    const value = screen.getByRole("button", { name: "Edit Code: CONNECTIONS" });
    const range = document.createRange();
    range.selectNodeContents(screen.getByText("CONNECTIONS"));
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    fireEvent.click(value);
    expect(screen.queryByRole("form", { name: "Edit Code" })).not.toBeInTheDocument();
    window.getSelection()?.removeAllRanges();
    fireEvent.click(value);
    expect(screen.getByRole("form", { name: "Edit Code" })).toBeInTheDocument();
  });

  it("shows the pencil as chosen on Settings › Appearance", () => {
    const stored = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
    try {
      const props = { model: testModel, object: domainObject, panel, onObjectChanged: vi.fn(), onReload: vi.fn() };
      const first = render(<AttributesPanel {...props} />);
      expect(first.container.querySelector(".attribute-grid")).toHaveAttribute("data-edit-hint", "hover");
      first.unmount();
      stored.set(EDIT_HINT_STORAGE_KEY, JSON.stringify("always"));
      const second = render(<AttributesPanel {...props} />);
      expect(second.container.querySelector(".attribute-grid")).toHaveAttribute("data-edit-hint", "always");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("does not offer mutations for a read-only binding", () => {
    const model = {
      ...testModel,
      objectTypes: testModel.objectTypes.map((type, index) =>
        index ? type : { ...type, attributes: type.attributes.map((binding) => ({ ...binding, readOnly: true })) },
      ),
    };
    render(
      <AttributesPanel
        model={model}
        object={domainObject}
        panel={panel}
        onObjectChanged={vi.fn()}
        onReload={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
